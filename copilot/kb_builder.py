"""
kb_builder.py - read every PDF in the UM Library and build kb/index.json.

For each document we record WHAT it is (type, ID, version), WHEN it applies
(effective dates), WHO it applies to (clients), and its sections.
This is the metadata the UM Library is missing today (Paul, IT: "no effective
dates, no client tags").

No AI is used. Every field comes from the document's own header text.
"""
import json
import re
from datetime import datetime
from pathlib import Path

from config import KB_SOURCE_DIR, KB_DIR, KB_INDEX
from copilot.textutil import pdf_to_text, split_sections

# GOV-01 section 1: the order of authority. Lower number = stronger.
RANK = {"REGULATION": 1, "ADDENDUM": 2, "SPD": 2, "POLICY": 3, "MEMO": 4, "EMAIL": 4, "GOVERNANCE": 0}
RANK_LABEL = {
    0: "Governance standard (defines the ranking itself)",
    1: "Level 1: law and regulation",
    2: "Level 2: client plan document / delegation agreement",
    3: "Level 3: Bellcourt medical policy (version effective on date of service)",
    4: "Level 4: memo / email (cannot change clinical criteria)",
}

MONTHS_DATE_RE = r"(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}"


def flatten(text: str) -> str:
    """One long line, table pipes removed. Makes header fields easy to search."""
    return " ".join(text.replace(" | ", " ").split())


def to_iso(date_text: str) -> str:
    """'January 1, 2026' -> '2026-01-01'."""
    return datetime.strptime(date_text, "%B %d, %Y").strftime("%Y-%m-%d")


def doc_type_for(path: Path) -> str:
    folder, name = path.parent.name, path.name
    if folder == "medical_policies":
        return "POLICY"
    if folder == "plan_documents":
        return "SPD"
    if folder == "health_plan_delegation":
        return "ADDENDUM"
    if folder == "regulatory":
        return "REGULATION"
    if name.startswith("GOV-"):
        return "GOVERNANCE"
    if name.startswith("EMAIL"):
        return "EMAIL"
    if name.startswith("UM-MEMO"):
        return "MEMO"
    return "UNKNOWN"          # we do not guess: a person must classify it


# ---------------------------------------------------------------- per-type parsers

def parse_policy(text: str) -> dict:
    """Medical policy header -> id, version, title, status, effective dates, service codes."""
    flat = flatten(text)
    policy_id = re.search(r"Policy number (MP-\d{3})", flat).group(1)
    version = re.search(r"Version (v\d+)", flat).group(1)
    title = re.search(rf"{policy_id}: (.+?) Bellcourt Medical Policy", flat).group(1)
    status = re.search(r"Status: (ACTIVE|RETIRED)", flat).group(1)
    eff = re.search(r"Effective for dates of service (\d{4}-\d{2}-\d{2}) (?:through (\d{4}-\d{2}-\d{2})|until superseded)", flat)
    code_text = re.search(r"Service code\(s\) (.+?) Applies to", flat).group(1)
    codes = re.findall(r"BHA-[A-Z]+-\d{4}", code_text)
    if not codes and "applies across services" in code_text:
        codes = ["*"]          # e.g. MP-117 Experimental and Investigational: not tied to one service
    return {
        "doc_id": policy_id, "version": version, "title": title, "status": status,
        "effective_from": eff.group(1), "effective_to": eff.group(2),   # None = still in force
        "service_codes": codes, "clients": ["*"],                         # policies apply to all clients
    }


def parse_spd(text: str) -> dict:
    """Plan document -> client, plan year, and any amendments that delete a section."""
    flat = flatten(text)
    doc_id = re.search(r"Document ID (SPD-[A-Z]+)", flat).group(1)
    year = re.search(r"Plan year (\d{4})", flat).group(1)
    sponsor_m = re.search(r"Introduction (.+?) \(the 'Plan Sponsor'\)", flat)
    sponsor = sponsor_m.group(1) if sponsor_m else doc_id

    # Example: "Amendment No. 3, effective January 1, 2026. Section 6.4 (...) is deleted in its entirety."
    amendments = []
    for m in re.finditer(rf"Amendment No\. (\d+), effective ({MONTHS_DATE_RE})\. Section ([\d.]+) \((.+?)\) is deleted", flat):
        amendments.append({
            "amendment_no": m.group(1),
            "effective_from": to_iso(m.group(2)),
            "deletes_section": m.group(4),
            "deleted_title": m.group(5),
        })
    return {
        "doc_id": doc_id, "version": None, "title": f"{sponsor} plan document (SPD), plan year {year}",
        "status": "ACTIVE", "effective_from": f"{year}-01-01", "effective_to": f"{year}-12-31",
        "service_codes": [], "clients": [doc_id.replace("SPD-", "")], "amendments": amendments,
    }


def parse_addendum(text: str) -> dict:
    flat = flatten(text)
    eff = re.search(rf"effective ({MONTHS_DATE_RE})", flat).group(1)
    return {
        "doc_id": "RIVERBEND-ADDENDUM", "version": None,
        "title": "Riverbend UM Delegation Agreement - Clinical and Operational Addendum",
        "status": "ACTIVE", "effective_from": to_iso(eff), "effective_to": "2026-12-31",  # term ends 31 Dec 2026 (section 7)
        "service_codes": [], "clients": ["RB-MA", "RB-ACA"],
    }


def parse_other(text: str, path: Path) -> dict:
    """Memos, emails, regulations, governance: ID from file name, date from 'Date:' if present."""
    flat = flatten(text)
    date_m = re.search(rf"Date: ({MONTHS_DATE_RE})", flat)
    clients = ["KESTREL"] if "Kestrel" in flat else ["*"]          # client-specific correspondence
    first_lines = [l for l in text.splitlines() if l.strip()]
    return {
        "doc_id": path.stem.split("_")[0] if path.stem.startswith(("REG-", "GOV-")) else path.stem,
        "version": None, "title": first_lines[1] if len(first_lines) > 1 else path.stem,
        "status": "ACTIVE", "effective_from": to_iso(date_m.group(1)) if date_m else None,
        "effective_to": None, "service_codes": [], "clients": clients,
    }


# ---------------------------------------------------------------- main build

REQUIRED = {
    "POLICY":   ["doc_id", "version", "status", "effective_from", "service_codes"],
    "SPD":      ["doc_id", "effective_from", "effective_to", "clients"],
    "ADDENDUM": ["doc_id", "effective_from", "clients"],
}


def build(source_dir: Path = KB_SOURCE_DIR, out_dir: Path = KB_DIR) -> dict:
    """
    Build the index. Returns {"index": [...], "needs_review": [...]}.

    A document goes to NEEDS REVIEW (and is NOT used by the rule finder) when:
      - its type can't be told from its folder/name,
      - a required header field (ID, version, dates...) can't be read,
      - it is a second copy of a document already indexed ("three files called MP-103 final").
    The rule finder can only use what it can date and identify. Never guess.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "text").mkdir(exist_ok=True)
    index, needs_review, seen = [], [], {}

    for pdf in sorted(source_dir.rglob("*.pdf")):
        rel = str(pdf.relative_to(source_dir.parent)).replace("\\", "/")
        text = pdf_to_text(pdf)
        dtype = doc_type_for(pdf)

        if dtype == "UNKNOWN":
            needs_review.append({"file": rel, "reason": "Document type unknown from folder/name."})
            continue
        try:
            if dtype == "POLICY":
                meta = parse_policy(text)
            elif dtype == "SPD":
                meta = parse_spd(text)
            elif dtype == "ADDENDUM":
                meta = parse_addendum(text)
            else:
                meta = parse_other(text, pdf)
        except (AttributeError, ValueError) as err:          # a regex found nothing / bad date
            needs_review.append({"file": rel, "reason": f"Header could not be read as a {dtype}: an expected field "
                                 f"(ID, version, status or effective dates) was not found. Technical detail: {err}"})
            continue

        missing = [f for f in REQUIRED.get(dtype, []) if not meta.get(f)]
        if missing:
            needs_review.append({"file": rel, "reason": f"Missing required field(s): {', '.join(missing)}"})
            continue

        key = f"{meta['doc_id']} {meta['version']}" if meta["version"] else meta["doc_id"]
        if key in seen:
            same = (seen[key]["text"] == text)
            needs_review.append({"file": rel, "reason": (
                f"Duplicate of {seen[key]['file']} ({key}); identical text, ignored." if same else
                f"CONFLICT: same ID/version as {seen[key]['file']} ({key}) but different text. Library owner must decide.")})
            continue
        seen[key] = {"file": rel, "text": text}

        text_file = out_dir / "text" / (key.replace(" ", "_") + ".txt")
        text_file.write_text(text, encoding="utf-8")
        meta.update({
            "key": key,                                   # e.g. "MP-101 v2" or "SPD-KESTREL"
            "doc_type": dtype,
            "rank": RANK[dtype],
            "rank_label": RANK_LABEL[RANK[dtype]],
            "source_file": rel,
            "text_file": f"{out_dir.name}/text/{text_file.name}",
            "sections": split_sections(text),
        })
        index.append(meta)

    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    (out_dir / "needs_review.json").write_text(json.dumps(needs_review, indent=2), encoding="utf-8")
    return {"index": index, "needs_review": needs_review}
