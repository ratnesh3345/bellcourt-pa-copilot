"""
redact.py - STEP 3: remove patient identity before ANY text goes to the AI.

The AI needs clinical facts ("BMI 44, diabetic, 6 months of program"), not who the patient is.
We remove: patient name, date of birth, phone numbers, MRN, member ID.
We KEEP the age (computed by code), because some rules depend on it (e.g. proton therapy
"excluded except for members under age 21" in SPD-BRIGHT 6.7).
"""
import re
from datetime import date


PATTERNS = [
    ("PHONE", re.compile(r"(?:ph\.?\s*)?\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}")),
    ("MRN", re.compile(r"MRN[-\s:]*\d+", re.I)),
    ("MEMBER_ID", re.compile(r"\b(?:RB[MA]|BHA)\d{8}\b")),
    ("DOB", re.compile(r"\bDOB\s*[:\s]*\d{1,2}/\d{1,2}/\d{4}", re.I)),
    ("DATE_OF_BIRTH", re.compile(r"\b\d{1,2}/\d{1,2}/(?:19|20)\d{2}\b")),
]


def age_on(dob_iso: str, on_iso: str):
    if not dob_iso or not on_iso:
        return None
    b, d = date.fromisoformat(dob_iso), date.fromisoformat(on_iso)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def redact(text: str, patient_name: str = None) -> tuple:
    """Returns (redacted_text, {"NAME": 1, "PHONE": 1, ...})."""
    if not text:
        return text, {}
    removed = {}
    if patient_name:
        for part in [patient_name] + patient_name.replace(".", " ").split():
            if len(part) >= 3:
                text, n = re.subn(re.escape(part), "[NAME]", text, flags=re.I)
                if n:
                    removed["NAME"] = removed.get("NAME", 0) + n
    for label, rx in PATTERNS:
        text, n = rx.subn(f"[{label}]", text)
        if n:
            removed[label] = removed.get(label, 0) + n
    text = re.sub(r"(\[NAME\]\s*)+", "[NAME] ", text)          # "John Smith" -> one [NAME]
    return text.strip(), removed
