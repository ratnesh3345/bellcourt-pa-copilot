"""
EVIDENCE IT WORKS (part 2): the AI step on Bellcourt's 120 QA-audited cases.

  python eval_ai.py              all 120 cases (about 120 AI calls; saved answers are reused next time)
  python eval_ai.py --limit 30   a quicker sample (spread across error types)

For each audited case the tool gets only what intake would have: client, service, date of service and
the de-identified clinical summary. The tool does NOT decide, so we can't compare "decisions".
Instead we check whether it puts the RIGHT THINGS IN FRONT OF THE NURSE:

  - QA says APPROVE              -> ideally NOTHING needs attention (every required criterion group supported,
                                    no plan provision unmet)
  - QA says DENY or PEND         -> AT LEAST ONE thing needs attention (a criterion group not supported,
                                    or a plan provision not satisfied)
  Missing DOCUMENTS are reported separately: the QA file has a 1-2 line clinical SUMMARY, not the full
  record, so the policy's document list will usually look incomplete here. That's expected.
  - every quote must be verified word-for-word; no decision language

Output: summary in the terminal + eval/ai_eval.csv
"""
import csv
import sys
from collections import Counter, defaultdict

from config import EVAL_DIR, QA_AUDIT_CSV, product_for
from copilot.guardrails import strip_suspicious
from copilot.reviewer import review
from copilot.rules import find_rules


def qa_case(row: dict) -> dict:
    notes, _ = strip_suspicious(row["clinical_summary"])
    return {
        "case_id": row["audit_id"], "client_id": row["client_id"], "product": product_for(row["client_id"]),
        "service_code": row["service_code"], "service_requested": row["service"],
        "date_of_service": row["date_of_service"], "urgency": "STANDARD",
        "rules": find_rules(row["service_code"], row["client_id"], row["date_of_service"]),
        "eligibility": {"status": "ELIGIBLE", "member_state": None},
        "for_ai": {"clinical_notes": notes, "age_at_service": None, "removed": {}},
        "intake_issues": [], "untrusted_flags": [],
    }


def pick_rows(rows, limit):
    """Spread the sample across error types so every kind of mistake is tested."""
    if not limit or limit >= len(rows):
        return rows
    by_type = defaultdict(list)
    for r in rows:
        by_type[r["error_type"]].append(r)
    picked = []
    while len(picked) < limit:
        for t in sorted(by_type):
            if by_type[t] and len(picked) < limit:
                picked.append(by_type[t].pop(0))
    return picked


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    rows = pick_rows(list(csv.DictReader(open(QA_AUDIT_CSV, encoding="utf-8"))), limit)
    EVAL_DIR.mkdir(exist_ok=True)
    out_rows, agree, n_by = [], Counter(), Counter()
    q_total = q_ok = guard_fail = errors = 0

    for i, row in enumerate(rows, 1):
        print(f"  [{i}/{len(rows)}] {row['audit_id']} {row['service'][:40]}...", end="\r")
        rv = review(qa_case(row))
        if rv["status"] != "DONE":
            errors += 1
            out_rows.append({"audit_id": row["audit_id"], "qa_decision": row["qa_correct_decision"],
                             "error_type": row["error_type"], "tool_status": rv["status"], "error": rv["error"]})
            if rv["status"] == "AI_UNAVAILABLE":
                print(f"\nAI unavailable: {rv['error']}")
                break
            continue
        chk = rv["checks"]
        q_total += chk["quotes_total"]; q_ok += chk["quotes_verified"]; guard_fail += not chk["passed"]
        needs_attention = bool(chk["needs_attention"])      # clinical criteria / plan provisions only
        expected = row["qa_correct_decision"] != "APPROVE"
        ok = needs_attention == expected
        group = "APPROVE" if not expected else "DENY/PEND"
        n_by[group] += 1; agree[group] += ok
        n_by["type:" + row["error_type"]] += 1; agree["type:" + row["error_type"]] += ok
        out_rows.append({
            "audit_id": row["audit_id"], "client_id": row["client_id"], "service": row["service"],
            "qa_decision": row["qa_correct_decision"], "error_type": row["error_type"],
            "tool_flags_something": needs_attention, "agrees_with_qa": ok,
            "attention_items": " | ".join(chk["needs_attention"]),
            "missing_documents": " | ".join(chk["missing_documents"]),
            "quotes_verified": f"{chk['quotes_verified']}/{chk['quotes_total']}",
            "guardrail_issues": " | ".join(chk["issues"]), "tool_status": "DONE", "error": "",
        })

    if out_rows:
        keys = sorted({k for r in out_rows for k in r})
        with open(EVAL_DIR / "ai_eval.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader(); w.writerows(out_rows)

    done = sum(n_by[g] for g in ("APPROVE", "DENY/PEND"))
    print("\n\nAI STEP vs QA AUDIT")
    print(f"  Cases reviewed: {done} (not reviewed: {errors})")
    for g, label in [("APPROVE", "QA says APPROVE  -> tool flags nothing"), ("DENY/PEND", "QA says DENY/PEND -> tool flags something")]:
        if n_by[g]:
            print(f"  {label:45}: {agree[g]}/{n_by[g]} = {agree[g]/n_by[g]:.0%}")
    if done:
        print(f"  Overall agreement with QA                    : {agree['APPROVE'] + agree['DENY/PEND']}/{done} = {(agree['APPROVE'] + agree['DENY/PEND'])/done:.0%}")
    print(f"  Quotes verified word-for-word                : {q_ok}/{q_total}")
    print(f"  Answers with any guardrail issue             : {guard_fail}")
    print("\n  By the error the nurse originally made:")
    for k in sorted(k for k in n_by if k.startswith("type:")):
        print(f"    {k[5:]:28} agreement {agree[k]}/{n_by[k]}")
    print("\n  NOTE: missing-document flags are not counted above (QA gives a short summary, not the full record).")
    print("\n  READ THIS: 'agreement' means the tool raised (or didn't raise) something for the nurse to look at,")
    print("  in line with QA's final answer. The tool never makes the decision. Details: eval/ai_eval.csv")


if __name__ == "__main__":
    main()
