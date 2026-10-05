"""
Run the REAL AI review from the terminal.

  python run_ai.py PA-2609-8100          one case, printed in plain English
  python run_ai.py --all                 every open case the AI is allowed to see (about 29 calls)
  python run_ai.py PA-2609-8100 --fresh  ignore the saved answer and ask again

Every run writes an audit record to audit_log/. Answers are saved in llm_cache/, so
running again costs nothing and gives the same result.
"""
import sys

from copilot.audit import write_audit
from copilot.intake import all_case_ids
from copilot.pipeline import prepare_case
from copilot.reviewer import info_request_draft, review


def show(case, rv):
    print(f"\n=== {case['case_id']} | {case.get('service_requested') or case['service_code']} | {case['client_id']} ===")
    if rv["status"] != "DONE":
        print(f"  {rv['status']}: {rv['error']}")
        return
    out, chk = rv["output"], rv["checks"]
    print(f"  Guardrails: {'PASSED' if chk['passed'] else 'ISSUES FOUND'} | quotes verified "
          f"{chk['quotes_verified']}/{chk['quotes_total']} | model {rv['llm']['model']}"
          f"{' (saved answer)' if rv['llm']['from_cache'] else ''}")
    for i in chk["issues"]:
        print(f"    ! {i}")
    print(f"  Summary: {out['summary_for_nurse']}")
    print("  Criteria:")
    for c in out["criteria"]:
        mark = "" if c.get("quote_verified") else "  [QUOTE NOT VERIFIED]"
        print(f"    - [{c.get('group', '?')}] {c['status']:15} {c.get('criterion')}  ({c['source'].get('doc')} s{c['source'].get('section')}){mark}")
        if c.get("evidence"):
            print(f"        evidence: \"{c['evidence']}\"")
    for p in out["plan_provisions"]:
        print(f"  Provision: {p['status']:13} {p.get('provision')}  ({p['source'].get('doc')} s{p['source'].get('section')})")
        if p.get("note"):
            print(f"        {p['note']}")
    for m in out["missing_documents"]:
        print(f"  Missing: {m.get('item')}")
    print("  Look at before deciding (criteria / plan provisions):")
    for a in chk["needs_attention"] or ["nothing: every required criterion group has supporting evidence"]:
        print(f"    * {a}")
    draft = info_request_draft(case, rv)
    if draft:
        print("\n  Draft information request (a person reviews and sends it):\n    " + draft.replace("\n", "\n    "))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fresh = "--fresh" in sys.argv
    ids = all_case_ids() if "--all" in sys.argv else args
    if not ids:
        print(__doc__)
        sys.exit(1)
    totals = {"done": 0, "passed": 0, "q": 0, "qok": 0, "other": 0}
    for cid in ids:
        case = prepare_case(cid)
        rv = review(case, use_cache=not fresh)
        if rv["status"] != "NOT_RUN":
            write_audit(case, rv)
        show(case, rv)
        if rv["status"] == "DONE":
            totals["done"] += 1
            totals["passed"] += rv["checks"]["passed"]
            totals["q"] += rv["checks"]["quotes_total"]
            totals["qok"] += rv["checks"]["quotes_verified"]
        else:
            totals["other"] += 1
    if len(ids) > 1:
        print(f"\nSUMMARY: {totals['done']} reviewed, {totals['passed']} passed all guardrails, "
              f"quotes verified {totals['qok']}/{totals['q']}, {totals['other']} not reviewed (stopped or AI unavailable).")
