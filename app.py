"""
PA Copilot - the screen intake coordinators and nurses use.
Run:  streamlit run app.py      (opens in your browser)

Left: the queue, most urgent first.  Right: three tabs for the selected case:
  1 Intake        what was read, deadline, eligibility, missing items, planted-text warnings, draft info request
  2 Nurse review  governing rules + flags; AI criteria checklist with verified quotes
  3 Audit record  exactly what the tool saw and produced (Riverbend Addendum 5)
The tool never approves, denies, pends or delays. Humans decide, in PACE.
"""
import json

import streamlit as st

from config import LLM_MODEL, OPEN_CASES_DIR, OPENROUTER_API_KEY
from copilot.audit import write_audit
from copilot.intake import all_case_ids
from copilot.pipeline import prepare_case
from copilot.reviewer import info_request_draft, review
from copilot.rules import load_index

TITLES = {d["service_codes"][0]: d["title"] for d in load_index() if d["doc_type"] == "POLICY" and d["service_codes"]}

st.set_page_config(page_title="PA Copilot", layout="wide")


@st.cache_data(show_spinner="Reading the 30 open cases...")
def load_queue():
    cases = [prepare_case(cid) for cid in all_case_ids()]
    return sorted(cases, key=lambda c: c["deadline"]["hours_left"])


ICON = {"READY": "🟢", "CHECK": "🟠", "STOP": "🔴"}
CRIT_ICON = {"SUPPORTED": "✅", "CONTRADICTED": "❌", "NOT_FOUND": "❓", "NOT_APPLICABLE": "➖"}
PROV_ICON = {"SATISFIED": "✅", "NOT_SATISFIED": "❌", "UNCLEAR": "❓", "INFO_ONLY": "ℹ️"}

st.title("PA Copilot")
st.caption("Assistive tool for Bellcourt UM. **It never approves, denies, pends or delays a request. "
           "Staff decide and record the decision in PACE.** Only physicians may deny.")

cases = load_queue()

# ------------------------------------------------------------------ sidebar: queue
with st.sidebar:
    st.header("Queue (most urgent first)")
    st.caption("Hours left counted from **receipt** (Riverbend Addendum 3), as of the queue snapshot.")
    labels = [f"{ICON[c['queue_status'].split()[0]]} {c['deadline']['hours_left']:>6.1f} h | {c['case_id']} | {c['client_id']}"
              for c in cases]
    pick = st.radio("Select a case", range(len(cases)), format_func=lambda i: labels[i], label_visibility="collapsed")
    st.divider()
    st.caption(f"AI model: `{LLM_MODEL}`  \nAI key: {'loaded' if OPENROUTER_API_KEY else 'not set: saved AI answers only'}  \n"
               "Saved answers (llm_cache/) are reused: no cost, same result.")

case = cases[pick]
d, e, r = case["deadline"], case["eligibility"], case["rules"]

st.subheader(f"{case['case_id']} · {TITLES.get(case['service_code']) or case.get('service_requested') or 'service not recognised'}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Status", case["queue_status"].split(" - ")[0])
c2.metric("Hours left", f"{d['hours_left']}", help=f"Due {d['due']} ({d['sla_hours']} h from receipt {d['received']})")
c3.metric("Client", f"{case['client_id']} ({case['product']})")
c4.metric("Eligibility", e["status"], help=f"State {e['member_state']}; coverage {e['coverage']}")

tab1, tab2, tab3 = st.tabs(["1 · Intake", "2 · Nurse review", "3 · Audit record"])

# ------------------------------------------------------------------ tab 1: intake
with tab1:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"**Source:** {case['source']}  \n**Channel:** {case['channel']} · **Urgency:** {case['urgency']}")
        st.table({
            "Field": ["Member ID", "Date of service", "Service code", "Requesting provider", "Patient age on DOS"],
            "Value": [str(case["member_id"]), str(case["date_of_service"]), str(case["service_code"]),
                      str(case["requesting_provider"]), str(case["for_ai"]["age_at_service"])],
        })
        if case.get("service_match"):
            st.caption("Service matched from the fax text: " + case["service_match"])

        st.markdown("#### Intake issues")
        if case["intake_issues"]:
            for i in case["intake_issues"]:
                st.warning(i["message"])
        else:
            st.success("No intake issues: complete on receipt.")

        st.markdown("#### Untrusted text check")
        if case["untrusted_flags"]:
            st.error("Instructions found inside the provider's text. They are **ignored** by the tool and "
                     "**removed** from what the AI sees. Do not act on them.")
            for u in case["untrusted_flags"]:
                st.caption(f"⚠️ {u['why']}: {u['excerpt']}")
        else:
            st.success("Nothing suspicious found.")

        st.markdown("#### Request for missing information (draft)")
        rv = st.session_state.get(case["case_id"])
        draft = info_request_draft(case, rv)
        if draft:
            st.text_area("Review and send it yourself. The tool does not send anything.", draft, height=200)
            if not rv:
                st.caption("Run the AI review (tab 2) to add missing clinical documents from the policy.")
        else:
            st.caption("Nothing missing found yet. Run the AI review (tab 2) to check the policy's documentation list.")
    with right:
        if case["channel"] == "FAX":
            raw = json.loads((OPEN_CASES_DIR / f"{case['case_id']}.json").read_text(encoding="utf-8"))
            st.image(str(OPEN_CASES_DIR / raw["fax_image"]), caption="Original fax image")
        else:
            st.markdown("**Clinical notes as received**")
            st.write(case["clinical_notes"])

# ------------------------------------------------------------------ tab 2: nurse review
with tab2:
    if r["status"] != "OK":
        st.error("Rules engine stopped: " + "; ".join(r["stop_reasons"]))
    for f in r["flags"]:
        st.info(f"**{f['code']}** · {f['message']}  \n_Source: {f['source']}_")

    st.markdown("#### Governing documents (picked by rules, strongest first)")
    for g in r["governing"]:
        with st.expander(f"{g['key']} · {g['rank_label']}"):
            st.caption(g["why"])
            for s in g["sections"]:
                st.markdown(f"**Section {s['section']} - {s['title']}**  \n_{s['note']}_")
                st.text(s["text"])
    for m in r["lower_authority"]:
        st.caption(f"⚠️ {m['key']} ({m['date']}): {m['warning']}")
    if r["not_used"]:
        with st.expander("Considered but NOT used (and why)"):
            for n in r["not_used"]:
                st.markdown(f"- **{n['key']}**: {n['reason']}")

    st.divider()
    st.markdown("#### AI criteria check")
    st.caption("The AI receives only: the sections above, MP-117 (investigational), and the notes with identity "
               "and planted instructions removed. Every quote is checked word-for-word by code.")
    colA, colB = st.columns([1, 3])
    fresh = colB.checkbox("Ask the AI again (ignore the saved answer)")
    if colA.button("Run AI review", type="primary"):
        with st.spinner("Asking the AI and checking its answer..."):
            rv = review(case, use_cache=not fresh)
            if rv["status"] != "NOT_RUN":
                rv["audit_file"] = write_audit(case, rv)
            st.session_state[case["case_id"]] = rv

    rv = st.session_state.get(case["case_id"])
    if rv:
        if rv["status"] != "DONE":
            st.error(f"{rv['status']}: {rv['error']}")
        else:
            out, chk = rv["output"], rv["checks"]
            if chk["passed"]:
                st.success(f"Guardrails passed: {chk['quotes_verified']}/{chk['quotes_total']} quotes found word-for-word; "
                           f"no decision language.  ({rv['llm']['model']}{', saved answer' if rv['llm']['from_cache'] else ''})")
            else:
                st.warning(f"Guardrails found {len(chk['issues'])} issue(s); affected lines are marked ⚠️. "
                           f"Quotes verified: {chk['quotes_verified']}/{chk['quotes_total']}.")
                for i in chk["issues"]:
                    st.caption("⚠️ " + i)

            st.markdown("**Summary (facts only):** " + out["summary_for_nurse"])
            if chk["needs_attention"]:
                st.markdown("**Look at these before deciding (criteria / plan provisions):**")
                for a in chk["needs_attention"]:
                    st.markdown(f"- {a}")
            else:
                st.markdown("**Criteria:** every required group has supporting evidence in the notes. "
                            "The decision is still yours.")

            st.markdown("##### Coverage criteria")
            for c in out["criteria"]:
                src = c.get("source", {})
                ok = "" if c.get("quote_verified") else " ⚠️ quote not verified"
                with st.container(border=True):
                    st.markdown(f"{CRIT_ICON.get(c['status'], '')} **{c['status']}** · {c.get('criterion')}  "
                                f"_(group {c.get('group', '?')}: {c.get('logic', '')})_")
                    st.markdown(f"> {c.get('quote')}  \n— {src.get('doc')} §{src.get('section')}{ok}")
                    ev = c.get("evidence")
                    st.markdown(f"**Evidence in notes:** {ev if ev else '_none found_'}"
                                f"{'' if (not ev or c.get('evidence_verified')) else ' ⚠️ not found in notes'}")
                    if c.get("note"):
                        st.caption(c["note"])

            if out["plan_provisions"]:
                st.markdown("##### Plan / contract provisions")
                for p in out["plan_provisions"]:
                    src = p.get("source", {})
                    ok = "" if p.get("quote_verified") else " ⚠️ quote not verified"
                    st.markdown(f"{PROV_ICON.get(p['status'], '')} **{p['status']}** · {p.get('provision')}  \n"
                                f"> {p.get('quote')}  \n— {src.get('doc')} §{src.get('section')}{ok}  \n_{p.get('note') or ''}_")

            if out["missing_documents"]:
                st.markdown("##### Missing documents (see draft request in tab 1)")
                for m in out["missing_documents"]:
                    src = m.get("source", {})
                    st.markdown(f"- {m.get('item')} — _{src.get('doc')} §{src.get('section')}_")

            if out["points_for_reviewer"]:
                st.markdown("##### Points for the reviewer")
                for p in out["points_for_reviewer"]:
                    st.markdown(f"- {p}")
            st.caption(f"Audit record saved: {rv.get('audit_file')}")

# ------------------------------------------------------------------ tab 3: audit
with tab3:
    rv = st.session_state.get(case["case_id"])
    if rv and rv.get("audit_file"):
        st.caption(rv["audit_file"])
        st.json(json.loads(open(rv["audit_file"], encoding="utf-8").read()), expanded=False)
    else:
        st.caption("Run the AI review to create an audit record. It stores what the AI saw and said, "
                   "the guardrail results, and no patient identity.")
