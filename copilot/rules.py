"""
rules.py - the RULE FINDER. Given a case, pick the documents that govern it.

Plain code, no AI. It applies GOV-01 the same way every time:
  Level 1  law / regulation           -> shown as FLAGS (AZ sign-off, TX disclosure, Medicare criteria)
  Level 2  client plan (SPD) or Riverbend Addendum
  Level 3  Bellcourt medical policy, version EFFECTIVE ON THE DATE OF SERVICE
  Level 4  memos / emails             -> shown, but marked "cannot change clinical criteria"

Input : service_code, client_id, date_of_service (YYYY-MM-DD), member_state (optional)
Output: a dict you can print, save to the audit log, or show in the UI.
"""
import json
import re
from functools import lru_cache

from config import KB_INDEX, product_for
from copilot.service_catalog import SERVICE_KEYWORDS, GENERIC_SPD_SECTIONS

# Addendum 2.1: services where Riverbend has confirmed Medicare criteria for MA members.
# Kept as a small table so it is easy to check against the Addendum by eye.
ADDENDUM_21_SERVICES = {
    "BHA-DME-2103": "Medicare criteria differ from Bellcourt policy: diabetes AND (insulin of any type/frequency OR documented problematic hypoglycemia). Applies to all dates of service.",
    "BHA-DME-0601": "Same as MP-118.",
    "BHA-THER-1830": "Same as MP-112.",
    "BHA-HH-0550": "Same as MP-116.",
}

# REG-02 / Addendum section 4: state rules for adverse decisions (insured Riverbend products only).
STATE_RULES = [
    # (product, state, effective_from, flag_code, message, source)
    ("MA", "AZ", "2026-07-01", "AZ_MD_SIGNOFF",
     "Arizona MA member: any medical-necessity denial must be personally reviewed and signed by an Arizona-licensed medical director.",
     "RIVERBEND-ADDENDUM 4; REG-02"),
    ("MA", "TX", "2026-01-01", "TX_AI_DISCLOSURE",
     "Texas MA member: if this tool was used, the decision notice must disclose AI-assisted review.",
     "RIVERBEND-ADDENDUM 4; REG-02"),
    ("ACA", "GA", "2027-01-01", "GA_HUMAN_REVIEW",
     "Georgia Marketplace member: coverage decisions may not be based solely on AI; human clinical review before denial.",
     "REG-02"),
]


@lru_cache(maxsize=1)
def load_index() -> list:
    """Load kb/index.json once (run build_kb.py first)."""
    if not KB_INDEX.exists():
        raise FileNotFoundError("kb/index.json not found. Run:  python build_kb.py")
    return json.loads(KB_INDEX.read_text(encoding="utf-8"))


def mentions_service(text: str, service_code: str) -> bool:
    """True if any keyword for this service appears in the text (word-start match, any case)."""
    for kw in SERVICE_KEYWORDS.get(service_code, []):
        if re.search(r"\b" + re.escape(kw), text, flags=re.IGNORECASE):
            return True
    return False


def in_effect(doc: dict, dos: str) -> bool:
    """Is the document in force on the date of service? (ISO dates compare correctly as text.)"""
    start, end = doc.get("effective_from"), doc.get("effective_to")
    return (start is None or start <= dos) and (end is None or dos <= end)


def find_rules(service_code: str, client_id: str, date_of_service: str, member_state: str = None) -> dict:
    index = load_index()
    product = product_for(client_id)
    result = {
        "inputs": {"service_code": service_code, "client_id": client_id, "product": product,
                   "date_of_service": date_of_service, "member_state": member_state},
        "status": "OK",          # OK = rules found; STOP = a human must sort something out first
        "stop_reasons": [],
        "governing": [],         # documents that apply, strongest first
        "lower_authority": [],   # memos / emails: shown for awareness only
        "not_used": [],          # documents considered and rejected, with the reason (for transparency)
        "flags": [],
    }

    # --- Safety checks: never guess -------------------------------------------------
    if not date_of_service:
        result["stop_reasons"].append("No date of service: cannot pick the policy version (GOV-01 2).")
    if not service_code or service_code not in SERVICE_KEYWORDS:
        result["stop_reasons"].append(f"Unknown service code '{service_code}': no Bellcourt policy matched.")
    if result["stop_reasons"]:
        result["status"] = "STOP"
        return result

    # --- Level 3: medical policy, version effective on the date of service ----------
    policy_versions = [d for d in index if d["doc_type"] == "POLICY" and service_code in d["service_codes"]]
    chosen_policy = None
    for d in policy_versions:
        if in_effect(d, date_of_service):
            chosen_policy = d
        else:
            result["not_used"].append({
                "key": d["key"],
                "reason": f"Effective {d['effective_from']} to {d['effective_to'] or 'now'}; "
                          f"date of service {date_of_service} is outside that range (GOV-01 2).",
            })
    if chosen_policy is None:
        result["status"] = "STOP"
        result["stop_reasons"].append(f"No version of the policy for {service_code} is in effect on {date_of_service}.")
        return result

    # --- Level 2: client layer -------------------------------------------------------
    if product in ("MA", "ACA"):
        addendum = next(d for d in index if d["doc_type"] == "ADDENDUM")
        sections = []
        if product == "MA" and service_code in ADDENDUM_21_SERVICES:
            sections.append(_section(addendum, "2.1", note=ADDENDUM_21_SERVICES[service_code]))
            result["flags"].append({
                "code": "MEDICARE_CRITERIA",
                "message": "Medicare coverage criteria apply to this MA member and Bellcourt criteria may not be stricter. "
                           + ADDENDUM_21_SERVICES[service_code],
                "source": "RIVERBEND-ADDENDUM 2.1",
            })
        elif product == "ACA":
            sections.append(_section(addendum, "2.2", note="Bellcourt medical policies apply without modification."))
        else:
            sections.append(_section(addendum, "2", note="No Medicare override listed for this service; apply the Bellcourt policy."))
        sections.append(_section(addendum, "4", note="Rules for adverse determinations."))
        result["governing"].append(_entry(addendum, sections, why=f"{client_id} is a Riverbend delegated product."))
    else:
        spds = [d for d in index if d["doc_type"] == "SPD" and client_id in d["clients"]]
        spd = next((d for d in spds if in_effect(d, date_of_service)), None)
        if spd is None:
            result["flags"].append({
                "code": "NO_PLAN_DOCUMENT",
                "message": f"No plan document on file for {client_id} in force on {date_of_service}. "
                           "Client plan rules come first (GOV-01 1): get the SPD before deciding.",
                "source": "GOV-01 1",
            })
        else:
            result["governing"].append(_entry(spd, _spd_sections(spd, service_code, date_of_service, result),
                                              why=f"{client_id} is a self-funded employer; its plan controls over Bellcourt policy (SPD 5.1)."))

    result["governing"].append(_entry(chosen_policy, [
        _section(chosen_policy, "3", note="Coverage criteria."),
        _section(chosen_policy, "4", note="Not medically necessary / limitations."),
        _section(chosen_policy, "5", note="Documentation requirements: what intake must check."),
    ], why=f"Version in effect on the date of service {date_of_service}."))

    # --- Level 4: memos and emails that mention this service -------------------------
    for d in index:
        if d["doc_type"] in ("MEMO", "EMAIL") and mentions_service(d["sections"]["header"]["text"] + _all_text(d), service_code):
            if "*" in d["clients"] or client_id in d["clients"]:
                result["lower_authority"].append({
                    "key": d["key"], "rank_label": d["rank_label"], "date": d["effective_from"],
                    "warning": "Level 4 document: it can explain process but CANNOT change clinical criteria. "
                               "If it conflicts with the policy or plan above, it is void to that extent (GOV-01 1).",
                    "text": _all_text(d),
                })

    # --- PACE screen warning (UM-MEMO-2026-04 lists screens that still show old criteria) ----
    for d in index:
        if d["doc_type"] != "MEMO":
            continue
        # Table rows look like: "Lumbar MRI (MP-101) | v2, effective 2026-01-01 | Q3 2026"
        for m in re.finditer(r"\((MP-\d{3})\)\s*\|?\s*(v\d+), effective (\d{4}-\d{2}-\d{2})\s*\|?\s*(.+)", _all_text(d)):
            pid, ver, eff, planned = m.groups()
            if pid == chosen_policy["doc_id"] and ver == chosen_policy["version"]:
                result["flags"].append({
                    "code": "PACE_SCREEN_OUTDATED",
                    "message": f"The PACE criteria screen for {pid} may still show the previous version "
                               f"(planned update: {planned.strip()}). Use the {pid} {ver} text shown here, not the PACE screen.",
                    "source": d["key"],
                })

    # --- Level 1: state law flags -------------------------------------------------------
    if product in ("MA", "ACA"):
        if not member_state:
            result["flags"].append({"code": "STATE_UNKNOWN",
                                    "message": "Member state unknown: check eligibility before any adverse decision (AZ/TX rules differ).",
                                    "source": "REG-02"})
        for prod, state, start, code, msg, src in STATE_RULES:
            if product == prod and member_state == state and date_of_service >= start:
                result["flags"].append({"code": code, "message": msg, "source": src})

    result["governing"].sort(key=lambda g: g["rank"])
    return result


# ---------------------------------------------------------------- helpers

def _all_text(doc: dict) -> str:
    return "\n".join(s["text"] for sid, s in doc["sections"].items() if "." not in sid)


def _section(doc: dict, sec_id: str, note: str = "") -> dict:
    sec = doc["sections"].get(sec_id, {"title": "(section not found)", "text": ""})
    return {"section": sec_id, "title": sec["title"], "note": note, "text": sec["text"]}


def _entry(doc: dict, sections: list, why: str) -> dict:
    return {"key": doc["key"], "doc_type": doc["doc_type"], "rank": doc["rank"], "rank_label": doc["rank_label"],
            "title": doc["title"], "why": why, "source_file": doc["source_file"], "sections": sections}


def _spd_sections(spd: dict, service_code: str, dos: str, result: dict) -> list:
    """Pick the SPD sections that mention this service, and apply any amendments."""
    deleted = {a["deletes_section"]: a for a in spd.get("amendments", []) if a["effective_from"] <= dos}
    picked = []
    for sec_id, sec in spd["sections"].items():
        if sec_id in GENERIC_SPD_SECTIONS or sec_id == "header" or sec_id == "8":
            continue
        if mentions_service(sec["text"], service_code):
            if sec_id in deleted:
                a = deleted[sec_id]
                result["not_used"].append({
                    "key": f"{spd['key']} section {sec_id}",
                    "reason": f"Deleted by Amendment No. {a['amendment_no']} effective {a['effective_from']} "
                              f"(see {spd['key']} section 8).",
                })
                continue
            picked.append(_section(spd, sec_id, note="Plan provision for this service. Plan controls over policy."))

    # Show the Amendments section whenever it mentions this service (the Kestrel trap).
    # An amendment about bariatric surgery is not shown on an MRI case: that would be noise.
    amend = spd["sections"].get("8", {"text": ""})["text"]
    if amend and "No amendments" not in amend and mentions_service(amend, service_code):
        picked.append(_section(spd, "8", note="Amendments: read before applying any section above."))
        result["flags"].append({"code": "PLAN_AMENDED",
                                "message": f"{spd['key']} has amendments this plan year. Check section 8.",
                                "source": f"{spd['key']} 8"})
    if not picked:
        picked.append(_section(spd, "5.1", note="No service-specific provision; plan says Bellcourt policy applies unless the plan is stricter."))
    return picked
