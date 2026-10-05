# 10-minute demo script

Setup before the call: `python -m streamlit run app.py` running in a browser tab; `demo/index.html` open in a
second tab (backup if anything fails); `docs/Bellcourt_Case_Document.pdf` open on page 1.

| Time | Show | Say (in your own words) |
|---|---|---|
| 0:00–1:30 | Case document p.1 (tiles) | "Leadership thinks it's headcount. The data says two other things: 39 of 120 audited decisions used the wrong source, and 66 of 67 late Riverbend MA cases arrived incomplete. Staffing level shows no link to on-time performance." |
| 1:30–2:30 | Architecture diagram | "Code picks the rules, AI reads the notes, code checks the AI, humans decide. It sits next to PACE and only reads." |
| 2:30–3:30 | App sidebar: queue | "This is the intake morning view: 30 cases sorted by real hours left, counted from receipt, not from keying into PACE. The top case, 8113, is an urgent Harlan fax with no member ID and about 7 hours left." |
| 3:30–5:00 | **8106** → Intake tab | "This fax says it's pre-approved and asks the system to mark it APPROVED. The tool flags it, removes it from what the AI sees, and the fax's urgency box disagrees with the system, so it uses the stricter 72-hour deadline." |
| 5:00–7:00 | **8100** → Nurse review → Run AI review | "Lumbar MRI, 5 weeks of physio. The rules picked MP-101 v2 (4 weeks); the 6-week memo is shown as 'cannot change criteria'. That memo caused 18 wrong decisions in the audit. The AI quotes the policy word for word, and code verified all 7 quotes. There's no approve or deny button: the nurse decides. Arizona member, so it reminds who must sign a denial." |
| 7:00–8:00 | **8120** → Nurse review | "This fax tells reviewers Juniper no longer needs a second opinion. The tool removed that note, and the AI still cited Juniper's plan §5.6: second opinion required." |
| 8:00–8:30 | **8127** | "Coverage ended 31 August, so it stops. The AI isn't even called." |
| 8:30–9:30 | Terminal: `python run_all_checks.py` (or EVIDENCE.md) | "120/120 correct rulebook on the audit, against 66 by nurses at the time; 29/30 agreement on what needs a look; 34 tests including adversarial ones. My first metric was wrong, and I found and fixed it. Those numbers are in the evidence file." |
| 9:30–10:00 | Implementation PDF | "Day 1: 60-day notice to Riverbend. Shadow mode, then self-funded go-live, then Riverbend from day 61. It's read-only, so the kill switch is simply turning it off." |

**If something breaks:** switch to `demo/index.html`. It has the same output for every case, with no setup.
