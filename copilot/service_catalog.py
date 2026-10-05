"""
service_catalog.py - the words used to spot each service inside plan documents and memos.

Why this exists: an SPD never says "BHA-SURG-4310". It says "Bariatric surgery".
So for each service code we list the words that identify it.

This list is maintained by a person (the Library owner), not by AI, so it is
predictable and auditable. Matching is case-insensitive and starts at a word boundary.
"""

SERVICE_KEYWORDS = {
    "BHA-IMG-0721":  ["lumbar", "MP-101"],                                   # MRI lumbar spine
    "BHA-SURG-4310": ["bariatric", "obesity", "MP-102"],                     # bariatric surgery
    "BHA-DME-2103":  ["CGM", "glucose monitor", "MP-103"],                   # continuous glucose monitor
    "BHA-DX-9581":   ["polysomnography", "sleep stud", "MP-104"],            # in-lab sleep study
    "BHA-SURG-2988": ["arthroscop", "MP-105"],                               # knee arthroscopy
    "BHA-SURG-2744": ["knee arthroplasty", "TKA", "MP-106"],                 # total knee replacement
    "BHA-LAB-8162":  ["BRCA", "MP-107"],                                     # BRCA genetic testing
    "BHA-SURG-1582": ["blepharoplasty", "eyelid", "MP-108"],                 # eyelid surgery
    "BHA-SURG-3052": ["septoplasty", "MP-109"],                              # septoplasty
    "BHA-SURG-6350": ["spinal cord stimulat", "SCS", "MP-110"],              # SCS trial
    "BHA-VASC-3647": ["varicose", "endovenous", "MP-111"],                   # vein ablation
    "BHA-THER-1830": ["hyperbaric", "HBOT", "MP-112"],                       # hyperbaric oxygen
    "BHA-RAD-5205":  ["proton", "MP-113"],                                   # proton beam therapy
    "BHA-REH-9711":  ["outpatient rehabilitation", "physical therapy", "MP-114"],  # PT beyond 12 visits
    "BHA-IMG-7519":  ["CT angiography", "CCTA", "MP-115"],                   # coronary CTA
    "BHA-HH-0550":   ["home health", "MP-116"],                              # home health
    "BHA-DME-0601":  ["CPAP", "MP-118"],                                     # CPAP continued coverage
}

# SPD sections that list ALL services generically. Matching a keyword there tells
# the nurse nothing new, so the rule finder skips them.
GENERIC_SPD_SECTIONS = {"4", "4.1", "5", "5.2", "6"}
