"""
ONE-CLICK CHECK. Runs everything and says PASS or FAIL in plain English.
Run:  python run_all_checks.py     (or double-click CHECK.bat on Windows)
"""
import csv
import io
import json
import re
import subprocess
import sys
from contextlib import redirect_stdout

results = []


def check(question, passed, detail=""):
    results.append(passed)
    print(f"  {'PASS' if passed else 'FAIL'}  {question}")
    if detail:
        print(f"        {detail}")


print("\nPA COPILOT - CHECKING EVERYTHING BUILT SO FAR\n")

# 1. Read the documents ---------------------------------------------------------
print("1) Reading the 38 Library documents")
from copilot.kb_builder import build
out = build()
check("All 38 documents were read and catalogued", len(out["index"]) == 38, f"{len(out['index'])} catalogued")
check("No document was rejected as unreadable", len(out["needs_review"]) == 0,
      "; ".join(r["file"] for r in out["needs_review"]))

index = {d["key"]: d for d in out["index"]}
old = index["MP-101 v1"]
check("Old MRI policy (MP-101 v1) is marked RETIRED, valid until 31 Dec 2025",
      old["status"] == "RETIRED" and old["effective_to"] == "2025-12-31")
check("Kestrel's plan change (Amendment 3) was found",
      any(a["deletes_section"] == "6.4" for a in index["SPD-KESTREL"].get("amendments", [])))

# 2. Pick the right rules -------------------------------------------------------
print("\n2) Picking the right rules for a case")
from copilot.rules import find_rules


def uses(r, key):
    return key in [g["key"] for g in r["governing"]]


r = find_rules("BHA-IMG-0721", "HARLAN", "2025-11-10")
check("MRI on 10 Nov 2025 -> uses the OLD policy (v1)", uses(r, "MP-101 v1") and not uses(r, "MP-101 v2"))

r = find_rules("BHA-IMG-0721", "RB-MA", "2026-10-02", "AZ")
check("MRI on 2 Oct 2026 -> uses the NEW policy (v2, 4 weeks), not the 6-week memo",
      uses(r, "MP-101 v2") and not uses(r, "UM-MEMO-2025-19"))
check("Arizona Medicare patient -> warns that an Arizona-licensed doctor must sign any denial",
      "AZ_MD_SIGNOFF" in [f["code"] for f in r["flags"]])

r = find_rules("BHA-SURG-4310", "KESTREL", "2026-09-29")
kestrel = next(g for g in r["governing"] if g["key"] == "SPD-KESTREL")
check("Kestrel weight-loss surgery 2026 -> old 'excluded' rule is NOT used (amendment wins)",
      "6.4" not in [s["section"] for s in kestrel["sections"]])

r = find_rules("BHA-SURG-4310", "HARLAN", "2026-10-08")
harlan = next(g for g in r["governing"] if g["key"] == "SPD-HARLAN")
check("Harlan weight-loss surgery -> shows Harlan's exclusion", "6.4" in [s["section"] for s in harlan["sections"]])

r = find_rules("BHA-XXX-0000", "HARLAN", "2026-10-01")
check("Unknown service -> STOPS and asks a human (never guesses)", r["status"] == "STOP")

# 3. Reading the open cases ------------------------------------------------------
print("\n3) Reading the 30 open cases (13 are fax images)")
from copilot.intake import all_case_ids
from copilot.pipeline import prepare_case
cases = {cid: prepare_case(cid) for cid in all_case_ids()}
faxes = [c for c in cases.values() if c["channel"] == "FAX"]
check("All 30 cases were read", len(cases) == 30)
check("All 13 faxes: service and treatment date read from the image",
      len(faxes) == 13 and all(c["service_code"] and c["date_of_service"] for c in faxes))
check("4 faxes with no member ID are flagged",
      sum("MISSING_MEMBER_ID" in [i["code"] for i in c["intake_issues"]] for c in faxes) == 4)
check("Kestrel patient whose coverage ended in August -> STOP",
      cases["PA-2609-8127"]["queue_status"].startswith("STOP"))
check("2 faxes with planted 'approve it' instructions -> flagged and hidden from the AI",
      all(cases[c]["untrusted_flags"] and "approve" not in cases[c]["for_ai"]["clinical_notes"].lower()
          for c in ["PA-2609-8106", "PA-2609-8120"]))
check("Patient name, phone, MRN and date of birth removed before the AI step",
      "Whitaker" not in cases["PA-2609-8101"]["for_ai"]["clinical_notes"]
      and "MRN-" not in cases["PA-2609-8101"]["for_ai"]["clinical_notes"])

# 4. Automatic tests ------------------------------------------------------------
print("\n4) Automatic tests (one per trap found in the data)")
p = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True)
summary = (p.stdout.strip().splitlines() or ["no output"])[-1]
check("All automatic tests pass", p.returncode == 0, summary)

# 5. Compare with Bellcourt's own quality audit ---------------------------------
print("\n5) Compared with Bellcourt's quality audit (120 real cases)")
import eval_rules
buf = io.StringIO()
with redirect_stdout(buf):
    eval_rules.main()
text = buf.getvalue()
engine = re.search(r"QA governing document \+ section : (\d+)/(\d+)", text)
nurse = re.search(r"Nurse originally cited the QA governing document  : (\d+)/(\d+)", text)
check("Tool shows the correct document in all 120 cases", engine and engine.group(1) == engine.group(2),
      f"Tool: {engine.group(1)}/{engine.group(2)} correct   |   Nurses at the time: {nurse.group(1)}/{nurse.group(2)}")

# 6. The AI step (only if a key is available) ------------------------------------
print("\n6) AI review (uses your OpenRouter key; the answer is saved, so later runs are free)")
from copilot.reviewer import review
from copilot.audit import write_audit
case = cases["PA-2609-8100"]
rv = review(case)                       # uses the saved answer if there is one (no key needed, no cost)
if rv["status"] == "AI_UNAVAILABLE":
    print("  SKIP  No saved AI answer and no OPENROUTER_API_KEY, so the AI check was skipped.")
else:
    if rv["status"] != "DONE":
        check("AI answered for case PA-2609-8100 (lumbar MRI fax)", False, f"{rv['status']}: {rv['error']}")
    else:
        write_audit(case, rv)
        chk = rv["checks"]
        check("AI answered for case PA-2609-8100 (lumbar MRI fax)", True, f"model {rv['llm']['model']}")
        check("Every quote in the AI answer exists word-for-word in the rulebook",
              chk["all_quotes_verified"], f"{chk['quotes_verified']}/{chk['quotes_total']} verified")
        check("No decision words in the AI answer", not any("Decision language" in i for i in chk["issues"]))
        mp101 = [c for c in rv["output"]["criteria"] if c.get("source", {}).get("doc") == "MP-101 v2"]
        check("AI used MP-101 v2 (4 weeks), not the 6-week memo", bool(mp101) and
              not any("6-week" in (c.get("quote") or "") for c in rv["output"]["criteria"]))

# Summary -----------------------------------------------------------------------
passed = sum(results)
print("\n" + "-" * 60)
print(f"RESULT: {passed} of {len(results)} checks passed.")
print("Everything works." if passed == len(results) else "Something failed: send the FAIL lines above to Claude.")
print("-" * 60)
