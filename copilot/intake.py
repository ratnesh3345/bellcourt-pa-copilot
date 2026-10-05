"""
intake.py - STEP 1: read a case into one standard shape.

Two kinds of input:
  - Typed cases (portal / phone / electronic): the JSON already has the fields.
  - Faxes: the JSON only has metadata; the details are in the image.
    We read the image with OCR (Tesseract, runs locally: the image never leaves Bellcourt)
    and pick out the fields by their printed labels ("Member ID:", "Planned date of service:").

No AI. Every field records WHERE it came from, so intake can check it.
"""
import difflib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from config import (OPEN_CASES_DIR, OCR_CACHE_DIR, TESSERACT_CMD, QUEUE_AS_OF, SLA_HOURS, product_for)
from copilot.rules import load_index

MEMBER_ID_RE = re.compile(r"\b(RB[MA]\d{8}|BHA\d{8})\b")


# ---------------------------------------------------------------- OCR

def ocr_image(image_path: Path) -> tuple:
    """
    Image -> text. Returns (text, how).
    Uses Tesseract if installed; otherwise the saved copy in ocr_cache/ (so the demo runs anywhere).
    """
    cache = OCR_CACHE_DIR / (image_path.stem + ".txt")
    # Already read this exact image? Reuse the text (OCR takes ~1-2 seconds per page).
    if cache.exists() and cache.stat().st_mtime >= image_path.stat().st_mtime:
        return cache.read_text(encoding="utf-8"), "OCR (Tesseract, saved result)"
    try:
        import pytesseract
        from PIL import Image
        if Path(TESSERACT_CMD).exists():
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        text = pytesseract.image_to_string(Image.open(image_path))
        OCR_CACHE_DIR.mkdir(exist_ok=True)
        cache.write_text(text, encoding="utf-8")
        return text, "OCR (Tesseract)"
    except Exception:
        if cache.exists():
            return cache.read_text(encoding="utf-8"), "OCR (saved copy in ocr_cache/)"
        raise RuntimeError(f"Cannot read {image_path.name}: Tesseract is not installed and there is no saved copy.")


# ---------------------------------------------------------------- fax field parsing

# label -> regex. OCR is noisy ("Member JD", "Health plan:/ employer"), so the patterns are forgiving.
FAX_LABELS = {
    "patient_name":      r"Patient\s*name\s*[:;.]",
    "patient_dob":       r"Date\s*of\s*birth\s*[:;.]",
    "member_id":         r"Member\s*[IJ1l][Dd]\s*[:;.]",
    "plan_on_form":      r"Health\s*\.?\s*plan\s*[:;./ ]*\s*employer\s*[:;.]",
    "requesting_provider": r"Requesting\s*[Pp]rovider\s*[:;.]",
    "provider_npi":      r"NPI\s*[:;.]",
    "service_requested": r"Service\s*requested\s*[:;.]",
    "date_of_service":   r"Planned\s*date\s*of\s*service\s*[:;.]",
    "diagnosis":         r"Diagnosis\s*\(ICD-10\)\s*[:;.]",
}


def _clean(value: str) -> str:
    """Strip OCR junk at the ends: dots, colons, slashes, quotes."""
    return value.strip(" .:;,/'\"“”‘’|-_").strip()


def parse_fax_text(text: str) -> dict:
    lines = [l for l in text.splitlines()]
    fields = {}
    for name, label in FAX_LABELS.items():
        for line in lines:
            m = re.search(label + r"(.*)$", line, flags=re.IGNORECASE)
            if m:
                fields[name] = _clean(m.group(1)) or None
                break

    # Clinical text: everything between "Clinical information" and "Provider signature"
    m = re.search(r"Clinical\s*information[^\n]*\n(.*?)\n\s*Provider[\s-]*signature", text, flags=re.S | re.I)
    fields["clinical_notes"] = " ".join(m.group(1).split()) if m else None

    # Review type: which box has the X?  e.g. "[X] Standard [ ] Urgent"  or  "[ ] Standard [ X] Urgent"
    rt = next((l for l in lines if "Review type" in l), "")
    std = re.search(r"\[\s*[Xx]\s*[\]\)}|]?\s*\.?\s*Standard", rt)
    urg = re.search(r"\[\s*[Xx]\s*[\]\)}|]?\s*\.?\s*Urgent", rt)
    fields["urgency_on_form"] = "URGENT" if urg and not std else "STANDARD" if std and not urg else None

    # Tidy up: member ID must look like a real ID; dates to ISO
    mid = MEMBER_ID_RE.search(fields.get("member_id") or "")
    fields["member_id"] = mid.group(1) if mid else None
    fields["date_of_service"] = _to_iso(fields.get("date_of_service"))
    fields["patient_dob"] = _to_iso(fields.get("patient_dob"))
    return fields


def _to_iso(value):
    """'10/02/2026' -> '2026-10-02'. Returns None if it doesn't look like a date."""
    if not value:
        return None
    m = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", value)
    if not m:
        m2 = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
        return m2.group(0) if m2 else None
    month, day, year = m.groups()
    try:
        return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def match_service(service_text: str) -> tuple:
    """
    'Advanced Imaging: MRI.of the Lumbar Spine' -> ('BHA-IMG-0721', 'Advanced Imaging: MRI of the Lumbar Spine', score)
    Compares letters only against every policy title in the catalogue.
    """
    if not service_text:
        return None, None, 0.0
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    best, best_score = None, 0.0
    for d in load_index():
        if d["doc_type"] == "POLICY" and d["service_codes"] and d["service_codes"][0] != "*":
            score = difflib.SequenceMatcher(None, norm(service_text), norm(d["title"])).ratio()
            if score > best_score:
                best, best_score = d, score
    if best and best_score >= 0.85:                    # high bar: below this, a human picks the service
        return best["service_codes"][0], best["title"], round(best_score, 2)
    return None, None, round(best_score, 2)


# ---------------------------------------------------------------- main entry

def load_case(case_id: str) -> dict:
    """Read one case (typed or fax) into the standard shape used by every later step."""
    raw = json.loads((OPEN_CASES_DIR / f"{case_id}.json").read_text(encoding="utf-8"))
    case = {
        "case_id": raw["case_id"], "channel": raw["channel"], "received_ts": raw["received_ts"],
        "urgency": raw["urgency"], "client_id": raw["client_id"], "product": product_for(raw["client_id"]),
        "requesting_provider": raw.get("requesting_provider"), "provider_npi": raw.get("provider_npi"),
        "member_id": raw.get("member_id"), "patient_name": raw.get("patient_name"),
        "patient_dob": _to_iso(raw.get("patient_dob")), "date_of_service": raw.get("date_of_service"),
        "service_code": raw.get("service_code"), "service_requested": raw.get("service_requested"),
        "clinical_notes": raw.get("clinical_notes"),
        "source": "Typed case (JSON)", "intake_issues": [], "untrusted_text": raw.get("clinical_notes") or "",
    }

    if raw.get("fax_image"):
        text, how = ocr_image(OPEN_CASES_DIR / raw["fax_image"])
        f = parse_fax_text(text)
        case.update({
            "source": f"Fax image read by {how}",
            "patient_name": f.get("patient_name"), "patient_dob": f.get("patient_dob"),
            "member_id": f.get("member_id"), "date_of_service": f.get("date_of_service"),
            "service_requested": f.get("service_requested"), "clinical_notes": f.get("clinical_notes"),
            "requesting_provider": f.get("requesting_provider") or case["requesting_provider"],
            "diagnosis": f.get("diagnosis"), "ocr_text": text, "untrusted_text": text,
        })
        code, title, score = match_service(f.get("service_requested"))
        case["service_code"] = code
        if code:
            case["service_match"] = f"'{f.get('service_requested')}' matched to '{title}' (similarity {score})"
        # The form's tick box vs the system's urgency: if they differ, use the STRICTER one and tell intake
        if f.get("urgency_on_form") and f["urgency_on_form"] != raw["urgency"]:
            case["intake_issues"].append({
                "code": "URGENCY_MISMATCH",
                "message": f"Fax form says {f['urgency_on_form']}, system says {raw['urgency']}. "
                           "Using URGENT (72 h) until a person confirms.",
            })
            case["urgency"] = "URGENT"

    # Missing-field checks (these are what make a request 'incomplete')
    for field, label in [("member_id", "Member ID"), ("date_of_service", "Date of service"),
                         ("service_code", "Service (could not match a Bellcourt service)"),
                         ("clinical_notes", "Clinical information")]:
        if not case.get(field):
            case["intake_issues"].append({"code": "MISSING_" + field.upper(), "message": f"Missing: {label}."})

    if raw.get("fax_image") and not case.get("diagnosis"):
        case["intake_issues"].append({"code": "MISSING_DIAGNOSIS", "message": "Missing: diagnosis code (ICD-10) on the fax."})

    case["deadline"] = deadline(case)
    return case


def deadline(case: dict) -> dict:
    """Deadline counted from RECEIPT (Riverbend Addendum 3), not from keying into PACE."""
    hours = SLA_HOURS[(case["product"], case["urgency"])]
    received = datetime.strptime(case["received_ts"], "%Y-%m-%d %H:%M")
    due = received + timedelta(hours=hours)
    now = datetime.strptime(QUEUE_AS_OF, "%Y-%m-%d %H:%M") if QUEUE_AS_OF else datetime.now()
    left = (due - now).total_seconds() / 3600
    return {"sla_hours": hours, "received": case["received_ts"], "due": due.strftime("%Y-%m-%d %H:%M"),
            "as_of": now.strftime("%Y-%m-%d %H:%M"), "hours_left": round(left, 1)}


def all_case_ids() -> list:
    return sorted(p.stem for p in OPEN_CASES_DIR.glob("PA-*.json"))
