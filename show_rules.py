"""
Run:  python show_rules.py BHA-IMG-0721 RB-MA 2026-10-02 AZ
      (service_code  client_id  date_of_service  [member_state])

Prints what the rule finder would show a nurse for one case. Use it to debug.
"""
import sys

from copilot.rules import find_rules

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    state = sys.argv[4] if len(sys.argv) > 4 else None
    r = find_rules(sys.argv[1], sys.argv[2], sys.argv[3], state)

    print(f"\nINPUTS: {r['inputs']}\nSTATUS: {r['status']}")
    for reason in r["stop_reasons"]:
        print(f"  STOP: {reason}")
    print("\nGOVERNING (strongest first):")
    for g in r["governing"]:
        print(f"  [{g['rank_label']}]  {g['key']}  - {g['why']}")
        for s in g["sections"]:
            print(f"      section {s['section']} {s['title'][:50]}  ({s['note']})")
    print("\nLOWER AUTHORITY (cannot change criteria):")
    for m in r["lower_authority"]:
        print(f"  {m['key']} ({m['date']})")
    print("\nCONSIDERED BUT NOT USED:")
    for n in r["not_used"]:
        print(f"  {n['key']}: {n['reason']}")
    print("\nFLAGS:")
    for f in r["flags"]:
        print(f"  {f['code']}: {f['message']}  [{f['source']}]")
