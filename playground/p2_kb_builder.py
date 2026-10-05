"""
PLAYGROUND 2 - copilot/kb_builder.py
Run:  python playground/p2_kb_builder.py      (run  python build_kb.py  first)

Shows: what the index knows about each document, and how one header is parsed.
"""
import json

import _setup
from config import KB_INDEX, KB_SOURCE_DIR
from copilot.kb_builder import parse_policy, parse_spd
from copilot.textutil import pdf_to_text

_setup.title("STEP 1  Parse ONE policy header by hand: MP-101 v1")
meta = parse_policy(pdf_to_text(KB_SOURCE_DIR / "medical_policies" / "MP-101_v1.pdf"))
for k, v in meta.items():
    print(f"  {k:15} {v}")
print("CHECK: Learner Pack p.32 says 'RETIRED (superseded 2025-12-31)', effective 2024-01-01 through 2025-12-31.")

_setup.title("STEP 2  Parse ONE plan document: SPD-KESTREL (look at 'amendments')")
meta = parse_spd(pdf_to_text(KB_SOURCE_DIR / "plan_documents" / "SPD-KESTREL.pdf"))
for k, v in meta.items():
    print(f"  {k:15} {v}")

_setup.title("STEP 3  The saved index (kb/index.json): every policy and its date range")
index = json.loads(KB_INDEX.read_text(encoding="utf-8"))
for d in index:
    if d["doc_type"] == "POLICY":
        print(f"  {d['key']:10} {d['status']:8} {d['effective_from']} -> {d['effective_to'] or 'now':10} {d['title'][:45]}")

_setup.title("STEP 4  Counts by GOV-01 level")
from collections import Counter
for label, n in sorted(Counter(d["rank_label"] for d in index).items()):
    print(f"  {n:3}  {label}")
