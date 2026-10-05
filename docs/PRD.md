# PRD — PA Copilot (Bellcourt Health Administrators)

*Owner: Ratnesh Singhaniya · Version 0.2 · 4 Oct 2026 · Status: Draft for build*

**Source key:** "LP p.X" = page X of `Bellcourt_Complete_Learner_Pack.pdf`. File paths are inside `Bellcourt_Data_Pack/`.

---

## 1. Background

### 1.1 The business

| Fact | Value | Source |
|---|---|---|
| What Bellcourt is | Third-party administrator (TPA) for self-funded employers, plus delegated prior authorization for Riverbend Health Plan | `01_company/company_fact_sheet.md` (LP p.11) |
| Clients | 38 self-funded employers (~453K lives); Riverbend MA (~92,400 members, AZ/TX) and Marketplace (~61,300, GA) | LP p.11 |
| Prior authorization volume | ~310,000 requests a year | LP p.11 |
| Revenue (FY2025) | $112.2M; UM fees $13.9M, forecast to fall to $13.1M in FY2026 | `01_company/financials_fy2023_2026_usd_millions.csv` (LP p.13) |
| Operating margin | 14.0% (FY2023) → 8.0% forecast (FY2026) | LP p.11 |
| Service credits to Riverbend | $0 (FY2023–25) → $1.9M (FY2026 forecast) | LP p.13 |
| Riverbend contract | Ends 31 Dec 2026; CAP opened July 2026 | `RIVERBEND-ADDENDUM` §7 (LP p.97); `02_process/02_sla_and_contract_commitments.md` (LP p.20) |

### 1.2 How prior authorization works today

| Step | What happens | Pain point | Source |
|---|---|---|---|
| 1. Intake | Fax 46%, portal 31%, phone 15%, electronic 8%. ~640 faxes/day retyped into 14 PACE fields | PACE starts the clock **at keying**; Riverbend counts from **receipt** | LP p.18; Marcus (LP p.26) |
| 2. Completeness | Incomplete requests pended; provider contacted | 22.7% of all requests and 32.3% of faxes incomplete on receipt | LP p.18 |
| 3. Nurse review | Nurse finds the right plan document + policy version, then reviews | 14.2 of 38 min per case spent locating and reading rules; Library has ~1,100 files, no metadata, file-name search only | LP p.18–19, p.21; Anita (LP p.25); Paul (LP p.30) |
| 4. Physician review | Only physicians can deny; AZ MA denials need an AZ-licensed MD (from 1 Jul 2026) | Only 2 of 6 staff medical directors hold AZ licenses | LP p.19 |
| 5. Status | Providers call for status | ~2,400 calls/day, 57% status checks, 20% abandoned | LP p.19 |

---

## 2. Problem (what the data shows)

| # | Root cause | Evidence | Business impact |
|---|---|---|---|
| 1 | **Nurses review against the wrong source**: a memo instead of the policy, an old policy version instead of the one effective on the date of service, or a Bellcourt policy instead of the employer's own plan rule | `04_operational_data/qa_audit_sample_2026.csv`: **39 of 120** cases (memo conflict 18, outdated version 14, client rule missed 7). Why: GOV-01 (LP p.102); UM-MEMO-2025-19 (LP p.103); UM-MEMO-2026-04 (LP p.104); EMAIL-Kestrel-Amendment (LP p.105); Anita (LP p.25); Paul (LP p.30) | RB-MA audit sample **~72% accurate vs 95% standard**; MA appeal overturn **~56% vs 30%** review trigger (Addendum §6, LP p.97; Linda, LP p.27). Riverbend can terminate for cause if the CAP isn't met within 120 days (Addendum §7) |
| 2 | **Incomplete requests are caught late and sit pending** | `04_operational_data/pa_requests_2025_2026.csv`: **66 of 67** late RB-MA cases were incomplete on receipt; late cases average **~120 h** pending for info vs **~12 h** for on-time cases | Timeliness drives service credits: 4% of quarterly fees per point below 97% (Addendum §6); ~$1.9M in FY2026 (LP p.13) |
| ✗ | Staffing is **not** the main cause of lateness | `nurse_staffing_weekly.csv` joined to `pa_requests_2025_2026.csv`: RB-MA on-time ~91% at every weekly nurse-FTE level | Hiring 20 nurses would not fix root causes 1 or 2 (VP Ops claim, LP p.24) |

**Supporting fact:** nurses spend **14.2 of 38 minutes** per case on "locating and reading the applicable plan provisions and policy criteria". *Source: time-and-motion study, UM Operations, May 2026, 212 observed reviews: `02_process/01_prior_authorization_current_state.md` §3 (LP p.18–19).*

---

## 3. Goal and solution

**Goal:** make Bellcourt's prior authorization decisions **more accurate, faster and easier to defend**, without replacing PACE and without the tool making any decision.

**Solution:** one rules engine that finds the governing documents for each case, then:
- shows **intake** what documents are missing, on day 1, and how many hours are left on the deadline;
- shows the **nurse** the correct, cited criteria and any conflicts.

Humans make every decision.

---

## 4. Users and user stories

| User | User story | Source of the need |
|---|---|---|
| Intake coordinator | "When a request arrives, I want to see what's missing so I can ask the provider the same day." | Marcus (LP p.26); Tasha (LP p.29) |
| Intake coordinator | "I want to see the real deadline from **receipt**, not from keying." | LP p.20; Marcus (LP p.26) |
| Nurse reviewer | "I want the right policy version and client rules in front of me, with the exact text, so I stop hunting." | Anita (LP p.25) |
| Nurse reviewer | "I want to be warned when a memo conflicts with policy." | GOV-01 (LP p.102); QA audit |
| Medical director | "I want to know when a denial needs an AZ-licensed signature or a Texas AI disclosure." | Addendum §4 (LP p.97); REG-02 (LP p.99) |
| QA / Riverbend auditor | "I want to see exactly what the tool showed for any case." | Addendum §5; Linda (LP p.27) |

---

## 5. Today vs with PA Copilot

| Step | Today | With PA Copilot |
|---|---|---|
| Fax arrives | Waits in a queue; retyped by hand; clock hidden until keyed | Read by local OCR; fields shown for the coordinator to confirm; deadline counted from receipt |
| Missing information | Often found when the nurse opens the case, days later | Checklist from the policy's "Documentation requirements" shown at intake |
| Finding the rules | Nurse searches ~1,100 files by name; PACE screens months behind | Correct client rules + policy version selected by code and shown with citations |
| Memo vs policy conflict | Nurse follows the memo | Memo shown as "lower authority, cannot override policy" |
| Untrusted text in faxes | Relies on staff noticing | Flagged and ignored |
| Audit | Free-text PACE note | Full input/output log per case |

---

## 6. Scope

### In scope (v1, the demo)

| ID | Feature |
|---|---|
| F1 | **Intake reader:** read case JSON; read fax images with local OCR; extract key fields; show deadline from receipt time |
| F2 | **Eligibility check:** is the member found, active on the date of service, and in which state? |
| F3 | **Rule finder** (no AI): pick governing documents by service code, client/product and date of service; rank by GOV-01; always include plan amendments; flag conflicting memos |
| F4 | **Completeness check:** compare the policy's documentation requirements with the case notes → list what's missing |
| F5 | **Criteria view:** each criterion quoted from the governing document, with the matching evidence from the notes, or "not found" |
| F6 | **Guardrails:** PHI removed before any AI call; instructions inside faxes and notes flagged and ignored; the tool never outputs approve/deny/pend; every quote must exist in its source |
| F7 | **Audit log:** one JSON record per case run |
| F8 | **Streamlit screen** with two tabs: Intake view, Nurse view |

### Out of scope (and why)

| Not building | Reason |
|---|---|
| Any automated approve, deny, pend or delay | Addendum §5; REG-02; CEO (LP p.23) |
| Replacing or writing to PACE | Brief constraint; Paul (LP p.30) |
| Electronic PA API (Jan 2027) | Separate project; listed as a risk |
| Provider status portal / call-center fixes | Good next step; not the highest-value fix |
| Harlan reporting dashboard | Next step; the audit log can feed it later |

---

## 7. Success metrics

**A. Does it work? (proved in the demo)**

| Metric | Target |
|---|---|
| Right governing source picked, tested on the 120 QA-audited cases | ≥ 95% |
| Missing documents flagged at intake, on test cases | ≥ 90% |
| Planted instructions in faxes/notes | 100% flagged, 0 followed |
| Decisions made by the tool | 0 (by design) |

**B. Does it help? (measured in the 90-day pilot)**

| Metric | Today | Target | Source of "today" |
|---|---|---|---|
| RB-MA decisions on time | ~90% | ≥ 97% | LP p.7; Linda (LP p.27) |
| RB-MA decision accuracy | ~72% (QA sample) | ≥ 95% | QA audit; Addendum §6 |
| MA appeal overturn rate | ~56% | < 30% | Linda (LP p.27); Addendum §6 |
| Minutes locating and reading rules per case | 14.2 | Lower (re-measured) | LP p.18–19 |

---

## 8. Constraints

| Constraint | Source | How the design meets it |
|---|---|---|
| No tool may deny, delay or modify a request | Addendum §5 (LP p.97) | Tool only shows information; humans act |
| 60 days' written notice to Riverbend before go-live | Addendum §5 | Built into the 90-day plan |
| Inputs and outputs producible on audit | Addendum §5 | F7 audit log |
| AZ: AZ-licensed MD signs MA medical-necessity denials | Addendum §4; REG-02 (LP p.99) | Flag in nurse view |
| TX: disclose AI use in the notice | Addendum §4; REG-02 | Flag in nurse view |
| PHI minimized and protected | Brief; Paul (LP p.30) | Redaction before AI; production on Azure OpenAI under Bellcourt's BAA (LP p.21) |
| Faxes and notes are untrusted input | Brief; Marcus (LP p.26) | F6 |
| PACE stays | Brief; Paul (LP p.30) | Read-only: fax share, portal webhook, PACE replica |
| No 20 extra nurses | Brief; CEO (LP p.23) | Solution targets the root causes, not headcount |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| AI misquotes a criterion | Code checks every quote against the source text; failures shown as errors |
| Metadata index wrong or out of date | Index built from each document's own header; a Library owner approves changes |
| OCR misreads a fax | Blank or doubtful fields highlighted for the coordinator to confirm |
| Nurses over-trust the tool | It shows sources and evidence, never a verdict |
| Demo LLM (OpenRouter) has no BAA | Synthetic data only; production uses Azure OpenAI in Bellcourt's tenant |
| Riverbend says no to the tool | Early 60-day notice; audit log and test results shared up front |

---

## 10. Dependencies and assumptions

| Item | Detail |
|---|---|
| IT access | Read-only PACE replica, fax share, portal webhook, Azure tenant: all offered by Paul (LP p.30) |
| Library owner | Someone in Clinical Policy (CMO's team) owns document metadata |
| Eligibility files | Nightly files remain available |
| Assumption | Documents keep their current header format (ID, version, status, effective dates) |

---

## 11. 90-day rollout (summary)

| Days | Work | Detail in |
|---|---|---|
| 1–30 | Send 60-day notice to Riverbend (day 1). Build KB index from the Library; connect fax share and PACE replica; run in **shadow mode** (tool runs, staff don't see it) | `docs/IMPLEMENTATION.md` |
| 31–60 | Validate against a fresh QA sample; train nurses and intake; go live for **self-funded employers** (not covered by the Riverbend notice) | same |
| 61–90 | Go live for **Riverbend** after the notice period; track the pilot metrics weekly | same |

---

## 12. Test cases found in the data

| Case | What it tests |
|---|---|
| PA-2609-8100 (fax, RB-MA lumbar MRI, 5 weeks therapy) | Memo trap: MP-101 v2 (4 weeks) applies, not the 6-week memo |
| PA-2609-8101 (RB-MA CGM) | Addendum §2.1: Medicare criteria for MA |
| PA-2609-8106 (fax, HBOT) | Instruction inside the fax aimed at the system |
| PA-2609-8120 (fax, Juniper SCS) | Note asking reviewers to skip a requirement |
| PA-2609-8113 / 8123 / 8125 / 8128 (faxes) | Missing member ID |
| PA-2609-8111 (fax, Harlan bariatric) | Plan exclusion (SPD-HARLAN §6.4) |
| PA-2609-8115 (fax, Brightwater bariatric at a non-designated facility) | Centers of Excellence rule (SPD-BRIGHT §5.3) |
| PA-2609-8116 (Kestrel bariatric) | Kestrel Amendment 3: covered from 2026 |
| PA-2609-8112 (Harlan PT, 26 visits used + 8 requested) | Client visit limit (SPD-HARLAN §4.2: 30) |
| PA-2609-8127 (Kestrel lumbar MRI, DOS 2026-10-17) | Member's coverage ended 2026-08-31 (eligibility file) |

---

## 13. Open questions

| Question | Who answers |
|---|---|
| Who owns Library metadata after go-live? | CMO / Clinical Policy Committee |
| Will Riverbend accept shadow-mode results as proof of accuracy before go-live? | Linda Cho (Riverbend) |
| Should the tool's audit log feed Harlan's reporting? | Account management |
