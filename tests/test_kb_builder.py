"""
Run:  python -m pytest -v

What happens to messy Library files? They must go to NEEDS REVIEW, never into the index.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import KB_SOURCE_DIR
from copilot.kb_builder import build


def test_messy_library_files_go_to_needs_review(tmp_path):
    src = tmp_path / "03_knowledge_base"
    (src / "medical_policies").mkdir(parents=True)
    (src / "misc").mkdir()
    real_policy = KB_SOURCE_DIR / "medical_policies" / "MP-103_v2.pdf"
    shutil.copy(real_policy, src / "medical_policies" / "MP-103_v2.pdf")
    shutil.copy(real_policy, src / "medical_policies" / "MP-103 final.pdf")            # duplicate copy
    shutil.copy(KB_SOURCE_DIR / "memos_and_governance" / "GOV-01_Clinical_Policy_Governance.pdf",
                src / "medical_policies" / "MP-999 draft.pdf")                          # no policy header
    shutil.copy(KB_SOURCE_DIR / "memos_and_governance" / "UM-MEMO-2025-19.pdf",
                src / "misc" / "lumbar notes.pdf")                                      # unknown type

    out = build(src, tmp_path / "out")

    assert [d["key"] for d in out["index"]] == ["MP-103 v2"]          # only ONE good copy indexed
    reasons = " ".join(r["reason"] for r in out["needs_review"])
    assert "Duplicate" in reasons
    assert "Header could not be read" in reasons
    assert "Document type unknown" in reasons
