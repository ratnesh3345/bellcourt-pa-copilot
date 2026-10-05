"""
Run:  python export_demo.py

Builds demo/index.html: ONE file that shows what PA Copilot produced for all 30 open cases,
plus the evidence. Anyone can open it in a browser: no Python, no AI key, no setup.
It uses the SAVED AI answers (llm_cache/), so it makes no new AI calls.

Patient identity (name, date of birth, member ID, phone, MRN) is NOT included.
"""
import csv
import json
import re
import subprocess
import sys
from datetime import date

from config import EVAL_DIR, PROJECT_ROOT
from copilot.intake import all_case_ids
from copilot.pipeline import prepare_case
from copilot.reviewer import info_request_draft, review
from copilot.rules import load_index

TITLES = {d["service_codes"][0]: d["title"] for d in load_index() if d["doc_type"] == "POLICY" and d["service_codes"]}

OUT = PROJECT_ROOT / "demo" / "index.html"


def case_view(cid: str) -> dict:
    c = prepare_case(cid)
    rv = review(c, use_cache=True)
    if rv["status"] == "AI_UNAVAILABLE":            # no saved answer and no network: show rules only
        rv = {"status": "NO_SAVED_ANSWER", "error": "No saved AI answer for this case.", "output": None, "checks": None}
    r = c["rules"]
    return {
        "id": c["case_id"], "channel": c["channel"], "client": c["client_id"], "product": c["product"],
        "service": TITLES.get(c["service_code"]) or c.get("service_requested") or "(service not recognised)",
        "service_code": c["service_code"],
        "dos": c["date_of_service"], "urgency": c["urgency"], "source": c["source"],
        "member_id_present": bool(c["member_id"]), "age": c["for_ai"]["age_at_service"],
        "status": c["queue_status"], "deadline": c["deadline"], "eligibility": {
            "status": c["eligibility"]["status"], "state": c["eligibility"]["member_state"]},
        "intake_issues": [i["message"] for i in c["intake_issues"]],
        "untrusted": c["untrusted_flags"], "notes_for_ai": c["for_ai"]["clinical_notes"],
        "removed": c["for_ai"]["removed"],
        "rules": {"status": r["status"], "stop": r["stop_reasons"],
                  "governing": [{"key": g["key"], "level": g["rank_label"], "why": g["why"],
                                 "sections": [{"id": s["section"], "title": s["title"], "note": s["note"], "text": s["text"]}
                                              for s in g["sections"]]} for g in r["governing"]],
                  "lower": [{"key": m["key"], "date": m["date"]} for m in r["lower_authority"]],
                  "not_used": r["not_used"], "flags": r["flags"]},
        "ai": {"status": rv["status"], "error": rv.get("error"), "output": rv.get("output"),
               "checks": rv.get("checks"), "model": (rv.get("llm") or {}).get("model")},
        "draft": info_request_draft(c, rv if rv.get("output") else None),
    }


def evidence() -> dict:
    ev = {"built": date.today().isoformat()}
    rules_csv = EVAL_DIR / "rules_eval.csv"
    if rules_csv.exists():
        rows = list(csv.DictReader(open(rules_csv, encoding="utf-8")))
        ev["rules"] = {"n": len(rows), "engine": sum(r["engine_right"] == "True" for r in rows),
                       "nurse": sum(r["nurse_right_document"] == "True" for r in rows)}
    ai_csv = EVAL_DIR / "ai_eval.csv"
    if ai_csv.exists():
        rows = [r for r in csv.DictReader(open(ai_csv, encoding="utf-8")) if r.get("tool_status") == "DONE"]
        appr = [r for r in rows if r["qa_decision"] == "APPROVE"]
        other = [r for r in rows if r["qa_decision"] != "APPROVE"]
        q = [tuple(map(int, r["quotes_verified"].split("/"))) for r in rows if r.get("quotes_verified")]
        ev["ai"] = {"n": len(rows), "agree": sum(r["agrees_with_qa"] == "True" for r in rows),
                    "approve_ok": sum(r["agrees_with_qa"] == "True" for r in appr), "approve_n": len(appr),
                    "other_ok": sum(r["agrees_with_qa"] == "True" for r in other), "other_n": len(other),
                    "quotes_ok": sum(a for a, _ in q), "quotes_n": sum(b for _, b in q)}
    p = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True, cwd=PROJECT_ROOT)
    m = re.search(r"(\d+) passed", p.stdout)
    ev["tests"] = int(m.group(1)) if m else None
    ev["tests_failed"] = "failed" in p.stdout
    return ev


TEMPLATE = (PROJECT_ROOT / "demo" / "template.html")

if __name__ == "__main__":
    cases = [case_view(cid) for cid in all_case_ids()]
    cases.sort(key=lambda c: c["deadline"]["hours_left"])
    data = {"cases": cases, "evidence": evidence()}
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", json.dumps(data).replace("</", "<\\/"))
    OUT.write_text(html, encoding="utf-8")
    done = sum(1 for c in cases if c["ai"]["status"] == "DONE")
    print(f"Wrote {OUT}  ({len(cases)} cases, {done} with a saved AI review). Open it in any browser.")
