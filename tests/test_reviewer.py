"""
Run:  python -m pytest -v

The AI step, tested WITHOUT calling the AI: we feed in a pretend AI answer
(good parts and deliberately bad parts) and check the guardrails catch every bad part.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import copilot.reviewer as reviewer
from copilot.pipeline import prepare_case

FAKE_ANSWER = {
    "criteria": [
        {"criterion": "Radicular pain despite 4 weeks of conservative therapy", "logic": "one of 3 options (OR)",
         "source": {"doc": "MP-101 v2", "section": "3"},
         "quote": "Radicular pain or radiculopathy that has persisted despite at least 4 weeks of documented conservative therapy",
         "evidence": "Has completed 5 weeks of PT and scheduled naproxen without adequate relief",
         "status": "SUPPORTED", "note": "5 weeks is more than 4."},
        {"criterion": "Made-up criterion", "logic": "required (AND)",
         "source": {"doc": "MP-101 v2", "section": "3"},
         "quote": "Patient must have tried yoga for 12 weeks",            # NOT in the policy
         "evidence": "Patient did yoga",                                   # NOT in the notes
         "status": "NOT_FOUND", "note": "Invented."},
    ],
    "plan_provisions": [
        {"provision": "Memo says 6 weeks", "source": {"doc": "UM-MEMO-2025-19", "section": "1"},   # NOT given to the AI
         "quote": "continue to apply the 6-week conservative therapy requirement", "status": "INFO_ONLY", "note": ""}
    ],
    "missing_documents": [],
    "points_for_reviewer": ["Patient has radiculopathy in an L5 distribution.", "I recommend approval."],  # decision words
    "summary_for_nurse": "Criteria appear documented; the request should be approved.",                     # decision words
}


def fake_ask(system, user, use_cache=True):
    return {"text": "```json\n" + json.dumps(FAKE_ANSWER) + "\n```", "model": "fake", "fingerprint": "test", "from_cache": False}


def test_prompt_has_rules_but_no_identity_or_planted_text():
    case = prepare_case("PA-2609-8106")                     # HBOT fax with planted "mark APPROVED"
    prompt, sent = reviewer.build_prompt(case)
    assert "MP-112 v1" in prompt and "RIVERBEND-ADDENDUM" in prompt
    assert "MP-117 v1" in prompt                            # investigational policy always included
    assert "pre-approved" not in prompt.lower() and "mark approved" not in prompt.lower()
    assert "Nancy" not in prompt and "Kincaid" not in prompt # patient name never sent
    assert {"doc": "MP-112 v1", "section": "3"} in sent


def test_guardrails_catch_every_bad_part(monkeypatch):
    monkeypatch.setattr(reviewer, "ask", fake_ask)
    case = prepare_case("PA-2609-8100")                     # lumbar MRI fax, 5 weeks PT
    r = reviewer.review(case)
    out, checks = r["output"], r["checks"]
    assert r["status"] == "DONE"
    good, invented = out["criteria"]
    assert good["quote_verified"] and good["evidence_verified"]          # real quote + real evidence pass
    assert not invented["quote_verified"] and not invented["evidence_verified"]   # invented ones caught
    assert not out["plan_provisions"][0]["quote_verified"]                # document not given to AI -> caught
    assert "removed by guardrail" in out["summary_for_nurse"]             # verdict sentence removed
    assert "removed by guardrail" in out["points_for_reviewer"][1]
    assert out["points_for_reviewer"][0].startswith("Patient has")        # normal point kept
    assert not checks["passed"] and checks["quotes_verified"] == 1


def test_ai_not_called_for_uncovered_member(monkeypatch):
    called = []
    monkeypatch.setattr(reviewer, "ask", lambda *a, **k: called.append(1))
    r = reviewer.review(prepare_case("PA-2609-8127"))     # coverage ended
    assert r["status"] == "NOT_RUN" and not called


def test_no_key_means_clear_message_not_crash(monkeypatch):
    def no_ai(*a, **k):
        raise reviewer.AIUnavailable("No OPENROUTER_API_KEY found.")
    monkeypatch.setattr(reviewer, "ask", no_ai)
    r = reviewer.review(prepare_case("PA-2609-8101"))
    assert r["status"] == "AI_UNAVAILABLE" and "OPENROUTER_API_KEY" in r["error"]


def test_info_request_draft_has_no_identity(monkeypatch):
    case = prepare_case("PA-2609-8113")                     # fax with no member ID
    draft = reviewer.info_request_draft(case, {"output": {"missing_documents": [
        {"item": "Office notes with symptom duration", "source": {"doc": "MP-101 v2", "section": "5"}}]}})
    assert "Member ID" in draft and "MP-101 v2 section 5" in draft
    assert "Daniel" not in draft and "Brooks" not in draft


def test_decision_check_blocks_verdicts_but_allows_facts():
    from copilot.guardrails import DECISION_WORDS
    verdicts = ["The request should be approved.", "I recommend approval.", "Recommend denial due to missing notes.",
                "Approve this request.", "Denial is warranted.", "This case qualifies for approval.", "It may be denied."]
    facts = ["Provider notes do not mention scheduled or recommended spine surgery.",
             "Procedural requirement for any potential denial decision.",
             "Only a licensed physician may issue a denial based on medical necessity.",
             "Documentation was pended previously by intake.", "Surgery was recommended by the surgeon."]
    for v in verdicts:
        assert DECISION_WORDS.search(v), f"verdict NOT caught: {v}"
    for f in facts:
        assert not DECISION_WORDS.search(f), f"fact wrongly blocked: {f}"


def test_only_the_verdict_sentence_is_removed(monkeypatch):
    answer = dict(FAKE_ANSWER)
    answer["summary_for_nurse"] = ("Radicular pain is documented with 5 weeks of PT. "
                                   "The request must be pended for the office notes. "
                                   "Symptom duration is not stated.")
    monkeypatch.setattr(reviewer, "ask", lambda *a, **k: {"text": json.dumps(answer), "model": "fake",
                                                          "fingerprint": "t", "from_cache": False})
    summary = reviewer.review(prepare_case("PA-2609-8100"))["output"]["summary_for_nurse"]
    assert "Radicular pain is documented" in summary and "Symptom duration is not stated" in summary
    assert "must be pended" not in summary and "removed by guardrail" in summary


def test_or_alternatives_are_read_as_a_group(monkeypatch):
    answer = dict(FAKE_ANSWER)
    q = "Radicular pain or radiculopathy that has persisted despite at least 4 weeks of documented conservative therapy"
    answer["criteria"] = [
        {"criterion": "Red flag", "logic": "one of 3 options (OR)", "source": {"doc": "MP-101 v2", "section": "3"},
         "quote": "Presence of a red-flag condition", "evidence": None, "status": "NOT_FOUND"},
        {"criterion": "4 weeks therapy", "logic": "one of 3 options (OR)", "source": {"doc": "MP-101 v2", "section": "3"},
         "quote": q, "evidence": "Has completed 5 weeks of PT", "status": "SUPPORTED"},
        {"criterion": "Surgery planned", "logic": "one of 3 options (OR)", "source": {"doc": "MP-101 v2", "section": "3"},
         "quote": "Pre-surgical planning", "evidence": None, "status": "NOT_FOUND"},
    ]
    answer["plan_provisions"], answer["missing_documents"] = [], [
        {"item": "Office notes", "source": {"doc": "MP-101 v2", "section": "5"}, "quote": "Office notes documenting symptom duration"}]
    monkeypatch.setattr(reviewer, "ask", lambda *a, **k: {"text": json.dumps(answer), "model": "fake",
                                                          "fingerprint": "t", "from_cache": False})
    chk = reviewer.review(prepare_case("PA-2609-8100"))["checks"]
    assert chk["needs_attention"] == []                      # one OR option met -> group satisfied
    assert chk["missing_documents"] == ["Missing document: Office notes"]   # reported separately


def test_and_group_with_nothing_supported_needs_attention(monkeypatch):
    answer = dict(FAKE_ANSWER)
    answer["criteria"] = [
        {"criterion": "4 weeks therapy", "logic": "required (AND)", "source": {"doc": "MP-101 v2", "section": "3"},
         "quote": "Presence of a red-flag condition", "evidence": None, "status": "NOT_FOUND"}]
    answer["plan_provisions"], answer["missing_documents"] = [], []
    monkeypatch.setattr(reviewer, "ask", lambda *a, **k: {"text": json.dumps(answer), "model": "fake",
                                                          "fingerprint": "t", "from_cache": False})
    chk = reviewer.review(prepare_case("PA-2609-8100"))["checks"]
    assert len(chk["needs_attention"]) == 1
