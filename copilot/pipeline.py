"""
pipeline.py - runs the steps in order for one case and returns ONE result.

  1 intake      -> read case / fax
  2 eligibility -> covered on the date of service? which state?
  3 rules       -> governing documents + flags
  4 safety scan -> instructions hidden in provider text
  5 redact      -> clinical text with identity removed (what the AI will see later)

Nothing here decides the case. It prepares what intake and the nurse need.
"""
from copilot.eligibility import check_eligibility
from copilot.guardrails import scan_untrusted, strip_suspicious
from copilot.intake import load_case
from copilot.redact import redact, age_on
from copilot.rules import find_rules


def prepare_case(case_id: str) -> dict:
    case = load_case(case_id)

    elig = check_eligibility(case["member_id"], case["client_id"], case["date_of_service"])
    case["eligibility"] = elig
    case["intake_issues"] += elig["issues"]

    case["rules"] = find_rules(case["service_code"], case["client_id"], case["date_of_service"], elig["member_state"])

    case["untrusted_flags"] = scan_untrusted(case["untrusted_text"])

    notes, removed = redact(case["clinical_notes"], case["patient_name"])
    notes, n_stripped = strip_suspicious(notes)            # the AI never sees the planted instructions
    if n_stripped:
        removed["SUSPICIOUS_INSTRUCTION"] = n_stripped
    case["for_ai"] = {
        "clinical_notes": notes,
        "age_at_service": age_on(case["patient_dob"], case["date_of_service"]),
        "removed": removed,
    }

    # Age stated in the notes vs age from date of birth (e.g. "8 y/o" but born in 2000)
    import re
    stated = re.search(r"\b(\d{1,3})\s*(?:y/?o|year[- ]old)\b", case["clinical_notes"] or "", flags=re.I)
    computed = case["for_ai"]["age_at_service"]
    if stated and computed is not None and abs(int(stated.group(1)) - computed) > 1:
        case["intake_issues"].append({"code": "AGE_MISMATCH",
            "message": f"Notes say {stated.group(1)} years old, but the date of birth gives {computed}. Confirm the patient's identity."})

    # Simple status for the queue view
    if case["rules"]["status"] == "STOP" or elig["status"] == "NOT_ELIGIBLE":
        case["queue_status"] = "STOP - human must resolve"
    elif case["untrusted_flags"] or case["intake_issues"]:
        case["queue_status"] = "CHECK - see issues"
    else:
        case["queue_status"] = "READY for nurse review"
    return case
