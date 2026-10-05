"""
Run:  python -m pytest -v

Step 1 checks: reading cases and faxes, eligibility, deadlines, privacy, planted instructions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from copilot.intake import all_case_ids, load_case
from copilot.pipeline import prepare_case

FAXES = ["PA-2609-8100", "PA-2609-8102", "PA-2609-8104", "PA-2609-8106", "PA-2609-8108", "PA-2609-8111",
         "PA-2609-8113", "PA-2609-8115", "PA-2609-8117", "PA-2609-8120", "PA-2609-8123", "PA-2609-8125",
         "PA-2609-8128"]


def codes(case):
    return [i["code"] for i in case["intake_issues"]]


def test_all_30_cases_load():
    assert len(all_case_ids()) == 30
    for cid in all_case_ids():
        assert load_case(cid)["case_id"] == cid


def test_every_fax_gives_service_and_date():
    for cid in FAXES:
        c = load_case(cid)
        assert c["service_code"], f"{cid}: service not recognised"
        assert c["date_of_service"], f"{cid}: date of service not read"


def test_fax_fields_read_correctly():
    c = load_case("PA-2609-8100")
    assert c["member_id"] == "RBM96929364"
    assert c["date_of_service"] == "2026-10-02"
    assert c["service_code"] == "BHA-IMG-0721"          # lumbar MRI
    assert "5 weeks of PT" in c["clinical_notes"]


def test_missing_member_id_is_flagged():
    for cid in ["PA-2609-8113", "PA-2609-8123", "PA-2609-8125", "PA-2609-8128"]:
        assert "MISSING_MEMBER_ID" in codes(load_case(cid)), cid


def test_urgency_mismatch_uses_stricter_deadline():
    c = load_case("PA-2609-8113")                       # form ticks Urgent, system says Standard
    assert "URGENCY_MISMATCH" in codes(c)
    assert c["urgency"] == "URGENT" and c["deadline"]["sla_hours"] == 72


def test_deadline_counts_from_receipt():
    c = load_case("PA-2609-8101")                       # MA standard, received 2026-09-23 05:30
    assert c["deadline"]["sla_hours"] == 168
    assert c["deadline"]["due"] == "2026-09-30 05:30"


def test_coverage_ended_is_stopped():
    c = prepare_case("PA-2609-8127")                    # Kestrel member, coverage ended 2026-08-31
    assert c["eligibility"]["status"] == "NOT_ELIGIBLE"
    assert c["queue_status"].startswith("STOP")


def test_state_comes_from_eligibility():
    assert prepare_case("PA-2609-8101")["eligibility"]["member_state"] == "AZ"
    assert prepare_case("PA-2609-8124")["eligibility"]["member_state"] == "TX"


def test_planted_instructions_flagged_and_hidden_from_ai():
    for cid in ["PA-2609-8106", "PA-2609-8120"]:
        c = prepare_case(cid)
        assert c["untrusted_flags"], f"{cid}: planted instruction not detected"
        ai_text = c["for_ai"]["clinical_notes"].lower()
        assert "approve" not in ai_text and "disregard" not in ai_text, f"{cid}: instruction reached the AI text"


def test_identity_removed_clinical_facts_kept():
    c = prepare_case("PA-2609-8101")
    ai = c["for_ai"]["clinical_notes"]
    assert "Whitaker" not in ai and "MRN-" not in ai and "495-8284" not in ai and "04/24/1991" not in ai
    assert "A1c 8.9%" in ai and "insulin glargine" in ai
    assert c["for_ai"]["age_at_service"] == 35


def test_age_mismatch_flagged():
    assert "AGE_MISMATCH" in codes(prepare_case("PA-2609-8125"))   # notes say 8 y/o, DOB says 26
