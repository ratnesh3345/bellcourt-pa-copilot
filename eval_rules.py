"""
Run:  python eval_rules.py

EVIDENCE IT WORKS (part 1): test the rule finder against Bellcourt's own QA audit.

For each of the 120 audited cases, the QA auditor recorded the governing source
(e.g. "MP-101 v2 Section 3" or "SPD-HARLAN Section 6.4"). We give the rule finder
ONLY what intake knows (service code, client, date of service) and check whether
it puts that exact document and section in front of the nurse.

Output: a summary in the terminal + eval/rules_eval.csv (one row per case).
"""
import csv
import re
from collections import Counter

from config import QA_AUDIT_CSV, EVAL_DIR
from copilot.rules import find_rules


def parse_governing(text: str):
    """'MP-101 v2 Section 3 (Coverage Criteria)' -> ('MP-101 v2', '3')"""
    m = re.match(r"(.+?) Section ([\d.]+)", text.strip())
    return m.group(1).strip(), m.group(2)


def engine_has(result: dict, key: str, section: str) -> bool:
    for g in result["governing"]:
        if g["key"] == key and any(s["section"] == section for s in g["sections"]):
            return True
    return False


def main():
    rows = list(csv.DictReader(open(QA_AUDIT_CSV, encoding="utf-8")))
    EVAL_DIR.mkdir(exist_ok=True)
    out_rows, by_error = [], Counter()
    engine_hits = nurse_hits = retired_shown = 0
    docs_shown = sections_shown = 0

    for r in rows:
        key, section = parse_governing(r["qa_governing_sources"])
        result = find_rules(r["service_code"], r["client_id"], r["date_of_service"])

        hit = result["status"] == "OK" and engine_has(result, key, section)
        nurse = key in r["original_criteria_cited"]          # did the nurse cite the right document?
        shown_keys = [g["key"] for g in result["governing"]]
        # Safety check: no policy version outside its effective dates is ever shown as governing
        retired_shown += sum(1 for g in result["governing"]
                             if g["doc_type"] == "POLICY" and g["key"] in [n["key"] for n in result["not_used"]])

        docs_shown += len(result["governing"])
        sections_shown += sum(len(g["sections"]) for g in result["governing"])
        engine_hits += hit
        nurse_hits += nurse
        if r["error_type"] != "NONE":
            by_error[(r["error_type"], "engine_right" if hit else "engine_wrong")] += 1

        out_rows.append({
            "audit_id": r["audit_id"], "client_id": r["client_id"], "service": r["service"],
            "date_of_service": r["date_of_service"], "qa_governing": f"{key} section {section}",
            "nurse_cited": r["original_criteria_cited"], "nurse_right_document": nurse,
            "engine_shows": " | ".join(shown_keys), "engine_right": hit, "qa_error_type": r["error_type"],
        })

    with open(EVAL_DIR / "rules_eval.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    n = len(rows)
    print("RULE FINDER vs QA AUDIT (120 cases)\n")
    print(f"  Engine shows the QA governing document + section : {engine_hits}/{n} = {engine_hits/n:.1%}")
    print(f"  Nurse originally cited the QA governing document  : {nurse_hits}/{n} = {nurse_hits/n:.1%}")
    print(f"  Out-of-date policy versions shown as governing    : {retired_shown}")
    print(f"  Average shown per case: {docs_shown/n:.1f} documents, {sections_shown/n:.1f} sections (how much the nurse must read)\n")
    print("  On the cases where QA found an error:")
    for etype in sorted({k[0] for k in by_error}):
        right, wrong = by_error[(etype, "engine_right")], by_error[(etype, "engine_wrong")]
        print(f"    {etype:28} engine right {right:>2} / {right + wrong}")
    print("\n  READ THIS BEFORE QUOTING THE NUMBER:")
    print("   - 'Right' means the correct document AND section is in front of the nurse. It does not")
    print("     mean the decision is right: CRITERIA_MISREAD cases had the right document already.")
    print("   - The keyword list (service_catalog.py) was written while reading these same documents,")
    print("     so this is not a blind test. New services need new keywords from the Library owner.")
    print(f"\n  Details per case: {EVAL_DIR / 'rules_eval.csv'}")
    misses = [o for o in out_rows if not o["engine_right"]]
    if misses:
        print("\n  MISSES:")
        for o in misses:
            print(f"    {o['audit_id']} {o['client_id']} {o['service']} -> expected {o['qa_governing']}; engine showed {o['engine_shows']}")


if __name__ == "__main__":
    main()
