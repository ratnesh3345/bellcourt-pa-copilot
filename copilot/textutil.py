"""
textutil.py - turn a PDF into clean text, and split text into numbered sections.

No AI here. Just reading files.
"""
import re
from pathlib import Path

import pdfplumber

# Lines we throw away: the page footer, and the running header that repeats on every page.
FOOTER_RE = re.compile(r"^Bellcourt Health Administrators - fictional company")


def _inside(obj: dict, bbox) -> bool:
    """Is this character/line inside the table's rectangle?"""
    x0, top, x1, bottom = bbox
    return (obj.get("x0", -1) >= x0 - 1 and obj.get("x1", 1e9) <= x1 + 1
            and obj.get("top", -1) >= top - 1 and obj.get("bottom", 1e9) <= bottom + 1)


def _page_to_text(page, last_header: list) -> str:
    """
    One page -> text, keeping TABLES readable.

    Plain extract_text() mixes table columns together when a cell wraps onto two lines:
        "6.3 Experimental and Services considered experimental ... policy"
        "investigational services MP-117."
    So we (1) find the tables, (2) take the normal text from OUTSIDE the tables,
    (3) write each table row as  cell | cell | cell  on ONE line,
    (4) put lines and tables back in top-to-bottom order.
    """
    tables = page.find_tables()
    boxes = [t.bbox for t in tables]

    outside = page.filter(lambda obj: not any(_inside(obj, b) for b in boxes))
    items = [(line["top"], line["text"]) for line in outside.extract_text_lines()]

    for t in tables:
        rows = [[(cell or "").replace("\n", " ").strip() for cell in row] for row in t.extract()]
        if rows and rows[0] == last_header:          # header row repeated on the next page: skip it
            rows = rows[1:]
        elif rows:
            last_header[:] = rows[0]
        items.append((t.bbox[1], "\n".join(" | ".join(r) for r in rows)))

    items.sort(key=lambda it: it[0])                 # top of page first
    return "\n".join(text for _, text in items)


def pdf_to_text(pdf_path: Path) -> str:
    """Read every page of a PDF and return clean text (tables kept as rows, footers/headers removed)."""
    last_header = []
    with pdfplumber.open(pdf_path) as pdf:
        raw = "\n".join(_page_to_text(page, last_header) for page in pdf.pages)

    clean_lines = []
    running_header = None            # the first line of page 1, e.g. "SPD-KESTREL | KESTREL ..."
    for line in raw.splitlines():
        line = line.replace("(cid:127)", "•").rstrip()     # pdfplumber shows bullets as (cid:127)
        if FOOTER_RE.match(line):
            continue
        if running_header is None and line:
            running_header = line                          # keep it once
        elif line == running_header:
            continue                                       # skip the copy on page 2, 3...
        clean_lines.append(line)
    return "\n".join(clean_lines)


# A section starts with "3. Coverage criteria" (top level: number + DOT)
# or "4.2 Outpatient rehabilitation" (sub-section: number.number, no dot).
# Criteria lines like "1 BMI of 40 or greater" have no dot, so they are NOT section starts.
# Table rows like "6.4 | Bariatric surgery | ..." also start a section (the "| " is optional).
SECTION_START_RE = re.compile(r"^(?:(\d{1,2})\.|(\d{1,2}\.\d{1,2}))\s+(?:\|\s+)?([A-Z].*)$")


def split_sections(text: str) -> dict:
    """
    Split a document into sections.
    Returns {"3": {"title": "Coverage criteria", "text": "..."}, "4.2": {...}, ...}

    A sub-section's text (e.g. 4.2) is also included inside its parent ("4").
    Text before the first section is stored under "header".
    """
    sections = {"header": {"title": "Header", "text": ""}}
    current_ids = ["header"]          # which sections the current line belongs to

    for line in text.splitlines():
        m = SECTION_START_RE.match(line.strip())
        if m:
            sec_id = m.group(1) or m.group(2)
            title = m.group(3).strip()
            if sec_id not in sections:
                sections[sec_id] = {"title": title, "text": ""}
            parent = sec_id.split(".")[0]
            if "." in sec_id and parent in sections:
                current_ids = [parent, sec_id]      # inside 4.2 -> also inside 4
            else:
                current_ids = [sec_id]
        for sid in current_ids:
            sections[sid]["text"] += line + "\n"

    for s in sections.values():
        s["text"] = s["text"].strip()
    return sections
