"""
PLAYGROUND 3 - copilot/rules.py
Run:  python playground/p3_rules.py

Shows the rule finder on 5 cases. Each one is a trap from the data pack.
Change the dates/clients below and run again to see what changes.
"""
import _setup
from copilot.rules import find_rules

CASES = [
    # (what it tests,                                   service,        client,    date,         state)
    ("Same MRI, 2025 date -> must use MP-101 v1",       "BHA-IMG-0721", "HARLAN",  "2025-11-10", None),
    ("Same MRI, 2026 date -> must use MP-101 v2",       "BHA-IMG-0721", "HARLAN",  "2026-03-10", None),
    ("Kestrel bariatric: amendment deletes 6.4",        "BHA-SURG-4310","KESTREL", "2026-09-29", None),
    ("Riverbend MA CGM in Arizona: Medicare + AZ flags","BHA-DME-2103", "RB-MA",   "2026-10-17", "AZ"),
    ("Unknown service: must STOP, never guess",         "BHA-XXX-0000", "HARLAN",  "2026-10-01", None),
]

for label, service, client, dos, state in CASES:
    r = find_rules(service, client, dos, state)
    _setup.title(f"{label}\n  input: {service} | {client} | {dos} | state={state}")
    print(f"  STATUS: {r['status']}  {r['stop_reasons'] or ''}")
    for g in r["governing"]:
        secs = ", ".join(s["section"] for s in g["sections"])
        print(f"  USE      {g['key']:20} sections {secs:12} <- {g['rank_label']}")
    for m in r["lower_authority"]:
        print(f"  CAUTION  {m['key']:20} (level 4: cannot change criteria)")
    for n in r["not_used"]:
        print(f"  NOT USED {n['key']:20} because {n['reason']}")
    for f in r["flags"]:
        print(f"  FLAG     {f['code']}")
