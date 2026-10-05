# Submission comment (copy everything below the line into the GitHub Discussions post)

Replace the two values in square brackets (your GitHub username and cohort) before posting.

---

## 📥 Submission: Ratnesh Singhaniya

- 🐙 **GitHub:** @[your-github-username] · 🎓 **Cohort:** [C1 or C2]
- 🔗 **Submission:** https://github.com/[your-github-username]/bellcourt-pa-copilot
- ▶️ **Demo:** run locally, see README (`python -m streamlit run app.py`; works without an API key using saved AI answers). No-setup preview: open `demo/index.html` in a browser
- 🔍 **Problems I found:**
  1. **Wrong source, not wrong judgement:** 39/120 QA-audited decisions used a memo, an outdated policy version, or Bellcourt policy instead of the employer's plan. MA denials citing an outdated policy or the memo were overturned 18/21 times.
  2. **Incomplete requests found too late:** 66 of the 67 late Riverbend MA cases were incomplete on receipt (≈120 h pending vs 12 h), and PACE starts the clock at keying, not receipt.
  3. **Not a headcount problem:** on-time stays ≈91% at every weekly nurse-staffing level.
- 🎯 **What I built:** PA Copilot puts the correct, cited rules in front of the nurse and catches missing information on day 1, using **RAG** (rule-based retrieval: code applies GOV-01 and picks the policy version by date of service; the AI checks the notes against criteria with exact quotes; code verifies every quote; humans make every decision). Built with **Python, pdfplumber, Tesseract OCR, Claude Sonnet 4.5 via OpenRouter (Azure OpenAI in production), Streamlit and pytest**. Results: correct document shown in 120/120 audit cases (nurses at the time: 66/120) · AI checklist agrees with QA in 29/30 · 193/193 quotes verified · both planted-instruction faxes caught · 34 tests.
