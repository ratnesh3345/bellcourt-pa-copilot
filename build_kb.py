"""
Run:  python build_kb.py

Reads every PDF in the knowledge base and writes kb/index.json + kb/text/*.txt.
Run it again whenever the Library changes.
"""
from copilot.kb_builder import build

if __name__ == "__main__":
    out = build()
    index, review = out["index"], out["needs_review"]
    print(f"Indexed {len(index)} documents into kb/index.json")
    print(f"Needs review (NOT used by the rule finder): {len(review)}  -> kb/needs_review.json\n")
    print(f"{'KEY':22} {'TYPE':11} {'STATUS':8} {'EFFECTIVE FROM':15} {'EFFECTIVE TO':13} CLIENTS / SERVICE CODES")
    for d in index:
        extra = ",".join(d["service_codes"]) or ",".join(d["clients"])
        print(f"{d['key']:22} {d['doc_type']:11} {d['status']:8} {str(d['effective_from']):15} {str(d['effective_to']):13} {extra}")
        for a in d.get("amendments", []):
            print(f"{'':22} -> Amendment {a['amendment_no']} from {a['effective_from']} deletes section {a['deletes_section']} ({a['deleted_title']})")

    for r in review:
        print(f"NEEDS REVIEW: {r['file']}  -  {r['reason']}")
