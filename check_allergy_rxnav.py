import requests

BASE = "https://rxnav.nlm.nih.gov/REST"

def get_rxcui(drug_name):
    r = requests.get(f"{BASE}/rxcui.json", params={"name": drug_name})
    ids = r.json().get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None

def get_drug_classes(rxcui):
    r = requests.get(f"{BASE}/rxclass/class/byRxcui.json",
                     params={"rxcui": rxcui, "relaSource": "ATC"})
    classes = []
    for item in r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
        name = item.get("rxclassMinConceptItem", {}).get("className")
        if name:
            classes.append(name)
    return classes

def clean_med_name(med_text):
    """Strip dose/form so RxNav can resolve it: 'amoxicillin 250 MG Oral Tablet' -> 'amoxicillin'."""
    return med_text.split()[0] if med_text else ""

def check_conflict(allergy, med_text):
    """Return True if the med conflicts with the allergy, using RxNav drug class."""
    drug = clean_med_name(med_text)
    rxcui = get_rxcui(drug)
    if not rxcui:
        return False, []
    classes = get_drug_classes(rxcui)
    a = allergy.lower()
    matched = [c for c in classes if a[:6] in c.lower()]  # match first 6 chars of allergy in class name
    # also direct ingredient/name match
    if a[:6] in drug.lower():
        matched.append(f"(direct: {drug})")
    return (len(matched) > 0), matched


# --- TEST: penicillin allergy vs amoxicillin (should conflict) and lisinopril (should not) ---
allergy = "Penicillin"
for med in ["Amoxicillin 250 MG / Clavulanate 125 MG Oral Tablet",
            "lisinopril 10 MG Oral Tablet"]:
    conflict, why = check_conflict(allergy, med)
    if conflict:
        print(f"⚠  CONFLICT: allergic to '{allergy}', prescribed '{med}'")
        print(f"     matched on: {why}")
    else:
        print(f"OK: '{med}' — no conflict with '{allergy}' allergy")