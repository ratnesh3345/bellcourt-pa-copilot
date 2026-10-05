"""
PLAYGROUND 1 - copilot/textutil.py
Run:  python playground/p1_textutil.py

Shows: PDF -> clean text (tables as rows) -> numbered sections.
Check it yourself: open the same PDF and compare.
"""
import _setup
from config import KB_SOURCE_DIR
from copilot.textutil import pdf_to_text, split_sections

pdf = KB_SOURCE_DIR / "plan_documents" / "SPD-KESTREL.pdf"

_setup.title(f"STEP 1  pdf_to_text('{pdf.name}')  - first 25 lines")
text = pdf_to_text(pdf)
print("\n".join(text.splitlines()[:25]))
print(f"... ({len(text.splitlines())} lines in total)")

_setup.title("STEP 2  split_sections(text)  - the sections it found")
sections = split_sections(text)
for sec_id, sec in sections.items():
    print(f"  {sec_id:7} {sec['title'][:60]}")

_setup.title("STEP 3  One table section: 6.4  (a table row, kept on one line)")
print(sections["6.4"]["text"])

_setup.title("STEP 4  The Amendments section: 8")
print(sections["8"]["text"])

print("\nCHECK: open Bellcourt_Complete_Learner_Pack.pdf p.87-89 (SPD-KESTREL). Same sections? Same words?")
