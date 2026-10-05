"""
eligibility.py - STEP 2: is this person covered, by this client, on the date of service?

Reads the nightly eligibility file. No AI.
"""
import csv
from functools import lru_cache

from config import ELIGIBILITY_CSV


@lru_cache(maxsize=1)
def _members() -> dict:
    with open(ELIGIBILITY_CSV, encoding="utf-8") as f:
        return {row["member_id"]: row for row in csv.DictReader(f)}


def check_eligibility(member_id: str, client_id: str, date_of_service: str) -> dict:
    """
    Returns {"status": ELIGIBLE | NOT_ELIGIBLE | UNKNOWN, "member_state": ..., "issues": [...]}
    UNKNOWN = we can't tell; a person must check. We never assume a member is covered.
    """
    out = {"status": "UNKNOWN", "member_state": None, "coverage": None, "issues": []}
    if not member_id:
        out["issues"].append({"code": "ELIGIBILITY_UNKNOWN",
                              "message": "No member ID: search PACE by name + date of birth, or call the provider."})
        return out

    m = _members().get(member_id)
    if m is None:
        out["issues"].append({"code": "MEMBER_NOT_FOUND",
                              "message": f"Member {member_id} is not in the eligibility file."})
        return out

    out["member_state"] = m["member_state"]
    out["coverage"] = f"{m['coverage_start']} to {m['coverage_end'] or 'ongoing'}"

    if m["client_id"] != client_id:
        out["issues"].append({"code": "CLIENT_MISMATCH",
                              "message": f"Member belongs to {m['client_id']}, but the case says {client_id}."})
    if date_of_service:
        starts_ok = m["coverage_start"] <= date_of_service
        ends_ok = (not m["coverage_end"]) or date_of_service <= m["coverage_end"]
        if not (starts_ok and ends_ok):
            out["status"] = "NOT_ELIGIBLE"
            out["issues"].append({"code": "NOT_COVERED_ON_DOS",
                                  "message": f"Coverage {out['coverage']} does not include the date of service {date_of_service}."})
        elif not out["issues"]:
            out["status"] = "ELIGIBLE"
    return out
