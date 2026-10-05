"""
Run:  python show_case.py PA-2609-8106

Shows everything the tool prepares for ONE open case, in plain English:
what was read, what's missing, eligibility, deadline, safety warnings, rules, and
the privacy-safe text that would go to the AI.
"""
import sys

from copilot.pipeline import prepare_case


def line(t=""):
    print(t)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    c = prepare_case(sys.argv[1])
    d = c["deadline"]

    line(f"\n=== {c['case_id']}  |  {c['queue_status']} ===")
    line(f"Source        : {c['source']}")
    line(f"Client        : {c['client_id']} ({c['product']})     Channel: {c['channel']}     Urgency: {c['urgency']}")
    line(f"Service       : {c['service_code']}  {c.get('service_match', c.get('service_requested') or '')}")
    line(f"Date of service: {c['date_of_service']}     Member: {c['member_id']}")
    line(f"Deadline      : due {d['due']} ({d['sla_hours']} h from receipt {d['received']}); "
         f"{d['hours_left']} h left as of {d['as_of']}")
    e = c["eligibility"]
    line(f"Eligibility   : {e['status']}   state={e['member_state']}   coverage={e['coverage']}")

    line("\nINTAKE ISSUES (fix before nurse review):")
    for i in c["intake_issues"] or [{"code": "-", "message": "none"}]:
        line(f"  - {i['message']}")

    line("\nSAFETY: suspicious instructions inside the provider's text (IGNORED by the tool):")
    for u in c["untrusted_flags"] or [{"why": "none", "excerpt": ""}]:
        line(f"  ! {u['why']}  {u['excerpt']}")

    r = c["rules"]
    line(f"\nRULES ({r['status']}):")
    for g in r["governing"]:
        line(f"  USE   {g['key']:20} sections {', '.join(s['section'] for s in g['sections'])}")
    for m in r["lower_authority"]:
        line(f"  NOTE  {m['key']:20} level 4: cannot change criteria")
    for n in r["not_used"]:
        line(f"  SKIP  {n['key']:20} {n['reason']}")
    for f in r["flags"]:
        line(f"  FLAG  {f['code']}: {f['message']}")

    a = c["for_ai"]
    line(f"\nWHAT THE AI WILL SEE (identity removed: {a['removed'] or 'nothing to remove'}; age {a['age_at_service']}):")
    line(f"  {a['clinical_notes']}")
