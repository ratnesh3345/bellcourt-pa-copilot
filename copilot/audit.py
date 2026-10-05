"""
audit.py - STEP 7: one JSON record per AI review (Riverbend Addendum 5: inputs and outputs
of any automated tool must be producible on audit).

What is stored: case number, what the rules engine chose, exactly which document sections the AI saw,
the privacy-safe notes the AI saw, the model, the raw AI answer, the checked answer, and the guardrail result.
What is NOT stored: patient name, date of birth, phone, MRN (minimum necessary).
"""
import json
from datetime import datetime

from config import AUDIT_DIR, TOOL_VERSION


def write_audit(case: dict, review_result: dict) -> str:
    AUDIT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    record = {
        "tool_version": TOOL_VERSION,
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "case_id": case["case_id"],
        "inputs": {
            "client_id": case["client_id"], "product": case["product"], "service_code": case["service_code"],
            "date_of_service": case["date_of_service"], "urgency": case["urgency"],
            "member_state": case["eligibility"]["member_state"], "eligibility": case["eligibility"]["status"],
            "notes_sent_to_ai": case["for_ai"]["clinical_notes"], "age_sent_to_ai": case["for_ai"]["age_at_service"],
            "identity_removed": case["for_ai"]["removed"],
        },
        "intake_issues": case["intake_issues"],
        "untrusted_text_flags": case["untrusted_flags"],
        "rules": {
            "status": case["rules"]["status"],
            "governing": [{"doc": g["key"], "sections": [s["section"] for s in g["sections"]]} for g in case["rules"]["governing"]],
            "not_used": case["rules"]["not_used"], "flags": [f["code"] for f in case["rules"]["flags"]],
        },
        "ai": {
            "status": review_result["status"], "error": review_result["error"], "llm": review_result["llm"],
            "documents_sent": review_result["sent_docs"], "raw_answer": review_result.get("raw_text"),
            "checked_answer": review_result["output"], "guardrail_checks": review_result["checks"],
        },
        "decision": "NONE - the tool does not make decisions. Decision is recorded by staff in PACE.",
    }
    path = AUDIT_DIR / f"{case['case_id']}_{stamp}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return str(path)
