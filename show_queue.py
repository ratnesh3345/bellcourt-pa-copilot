"""
Run:  python show_queue.py

All 30 open cases in one table, most urgent first: the intake coordinator's morning view.
"""
from copilot.intake import all_case_ids
from copilot.pipeline import prepare_case

if __name__ == "__main__":
    cases = [prepare_case(cid) for cid in all_case_ids()]
    cases.sort(key=lambda c: c["deadline"]["hours_left"])
    print(f"\n{'CASE':14}{'CLIENT':9}{'CHANNEL':11}{'HRS LEFT':>9}  {'STATUS':28}ISSUES / WARNINGS")
    for c in cases:
        notes = [i["code"] for i in c["intake_issues"]] + (["SUSPICIOUS_TEXT"] if c["untrusted_flags"] else [])
        print(f"{c['case_id']:14}{c['client_id']:9}{c['channel']:11}{c['deadline']['hours_left']:>9}  "
              f"{c['queue_status']:28}{', '.join(notes) or '-'}")
    counts = {}
    for c in cases:
        key = c["queue_status"].split(" ")[0]
        counts[key] = counts.get(key, 0) + 1
    print(f"\n{len(cases)} cases: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
