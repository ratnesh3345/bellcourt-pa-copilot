"""
Run:  python -m pytest -v

Each test is one trap we found in the data pack. If a test fails, the rule
finder would show a nurse the wrong source.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # so "import config" works

from copilot.rules import find_rules


def keys(result):
    return [g["key"] for g in result["governing"]]


def flag_codes(result):
    return [f["code"] for f in result["flags"]]


def test_version_follows_date_of_service_2026():
    # MP-101 v2 (4 weeks) is effective from 2026-01-01
    assert "MP-101 v2" in keys(find_rules("BHA-IMG-0721", "RB-MA", "2026-03-10", "AZ"))


def test_version_follows_date_of_service_2025():
    # Same service, earlier date: v1 must be used, NOT the newest version
    r = find_rules("BHA-IMG-0721", "RB-MA", "2025-11-10", "AZ")
    assert "MP-101 v1" in keys(r) and "MP-101 v2" not in keys(r)


def test_memo_is_never_governing():
    # UM-MEMO-2025-19 (6 weeks) is shown only as lower authority
    r = find_rules("BHA-IMG-0721", "RB-MA", "2026-10-02", "AZ")
    assert "UM-MEMO-2025-19" not in keys(r)
    assert "UM-MEMO-2025-19" in [m["key"] for m in r["lower_authority"]]


def test_kestrel_amendment_overrides_exclusion():
    # SPD-KESTREL 6.4 says "excluded" but Amendment 3 deletes it from 2026-01-01
    r = find_rules("BHA-SURG-4310", "KESTREL", "2026-09-29")
    spd = next(g for g in r["governing"] if g["key"] == "SPD-KESTREL")
    assert "6.4" not in [s["section"] for s in spd["sections"]]
    assert "8" in [s["section"] for s in spd["sections"]]
    assert "PLAN_AMENDED" in flag_codes(r)


def test_harlan_bariatric_exclusion_shown():
    r = find_rules("BHA-SURG-4310", "HARLAN", "2026-10-08")
    spd = next(g for g in r["governing"] if g["key"] == "SPD-HARLAN")
    assert "6.4" in [s["section"] for s in spd["sections"]]


def test_brightwater_centers_of_excellence_shown():
    r = find_rules("BHA-SURG-4310", "BRIGHT", "2026-10-18")
    spd = next(g for g in r["governing"] if g["key"] == "SPD-BRIGHT")
    assert "5.3" in [s["section"] for s in spd["sections"]]


def test_pt_visit_limit_from_client_plan():
    r = find_rules("BHA-REH-9711", "HARLAN", "2026-10-18")
    spd = next(g for g in r["governing"] if g["key"] == "SPD-HARLAN")
    assert "4.2" in [s["section"] for s in spd["sections"]]


def test_ma_cgm_uses_medicare_criteria():
    r = find_rules("BHA-DME-2103", "RB-MA", "2026-10-17", "AZ")
    assert "MEDICARE_CRITERIA" in flag_codes(r)


def test_az_and_tx_flags():
    assert "AZ_MD_SIGNOFF" in flag_codes(find_rules("BHA-IMG-0721", "RB-MA", "2026-10-02", "AZ"))
    assert "TX_AI_DISCLOSURE" in flag_codes(find_rules("BHA-IMG-0721", "RB-MA", "2026-10-02", "TX"))


def test_az_signoff_not_before_july_2026():
    assert "AZ_MD_SIGNOFF" not in flag_codes(find_rules("BHA-IMG-0721", "RB-MA", "2026-03-01", "AZ"))


def test_unknown_service_stops():
    assert find_rules("BHA-XXX-0000", "HARLAN", "2026-10-01")["status"] == "STOP"


def test_missing_date_stops():
    assert find_rules("BHA-IMG-0721", "HARLAN", None)["status"] == "STOP"


def test_unrelated_amendment_not_flagged():
    # Kestrel's amendment is about bariatric surgery; it must not appear on a Kestrel MRI case
    r = find_rules("BHA-IMG-0721", "KESTREL", "2026-10-17")
    assert "PLAN_AMENDED" not in flag_codes(r)
