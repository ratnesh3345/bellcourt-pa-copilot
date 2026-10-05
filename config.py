"""
config.py - one place for every path and setting.

If your data pack lives somewhere else, set the environment variable
BELLCOURT_DATA to that folder (the one that contains 03_knowledge_base).
"""
import os
from pathlib import Path

# Folder that contains this file (the project root: pa-copilot/)
PROJECT_ROOT = Path(__file__).resolve().parent

# The Bellcourt data pack. Default: the folder next to pa-copilot/
DATA_DIR = Path(os.environ.get("BELLCOURT_DATA", PROJECT_ROOT.parent / "Bellcourt_Data_Pack"))

KB_SOURCE_DIR = DATA_DIR / "03_knowledge_base"          # the PDFs reviewers use
OPS_DIR = DATA_DIR / "04_operational_data"              # CSVs and open cases
OPEN_CASES_DIR = OPS_DIR / "open_cases"
QA_AUDIT_CSV = OPS_DIR / "qa_audit_sample_2026.csv"
ELIGIBILITY_CSV = OPS_DIR / "member_eligibility_extract.csv"

# Where WE write things (generated, safe to delete and rebuild)
KB_DIR = PROJECT_ROOT / "kb"                 # kb/index.json + kb/text/*.txt
KB_INDEX = KB_DIR / "index.json"
EVAL_DIR = PROJECT_ROOT / "eval"             # test results
AUDIT_DIR = PROJECT_ROOT / "audit_log"       # one JSON per case run

# Which client IDs belong to which product (from 01_company/client_roster.csv)
PRODUCT_BY_CLIENT = {"RB-MA": "MA", "RB-ACA": "ACA"}   # everything else = SELF_FUNDED


def product_for(client_id: str) -> str:
    """RB-MA -> 'MA', RB-ACA -> 'ACA', any employer -> 'SELF_FUNDED'."""
    return PRODUCT_BY_CLIENT.get(client_id, "SELF_FUNDED")


# ---------------------------------------------------------------- intake settings
OCR_CACHE_DIR = PROJECT_ROOT / "ocr_cache"      # saved OCR text, used if Tesseract isn't installed

# Where Tesseract is on Windows (default installer path). Ignored if not found.
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

# "Now" for deadline countdowns. The open cases are a snapshot taken on 25 Sep 2026,
# so the demo measures time left from the moment the queue was captured.
# Set QUEUE_AS_OF="" in the environment to use the real current time instead.
QUEUE_AS_OF = os.environ.get("QUEUE_AS_OF", "2026-09-25 12:00")

# Decision deadlines in hours: (product, urgency) -> hours.  Source: 02_process/02_sla_and_contract_commitments.md
SLA_HOURS = {
    ("MA", "STANDARD"): 168, ("MA", "URGENT"): 72,
    ("ACA", "STANDARD"): 360, ("ACA", "URGENT"): 72,
    ("SELF_FUNDED", "STANDARD"): 360, ("SELF_FUNDED", "URGENT"): 72,
}


# ---------------------------------------------------------------- AI settings
# The key is read from a .env file in pa-copilot/ (or the folder above it). Never hard-code it.
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT.parent / ".env")      # also accept the .env one folder up
except ImportError:
    pass

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")   # Azure OpenAI in production
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4.5")
LLM_CACHE_DIR = PROJECT_ROOT / "llm_cache"       # saved AI answers: same input -> same answer, no extra cost
TOOL_VERSION = "pa-copilot 0.3"
