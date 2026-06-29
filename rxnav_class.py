import requests

BASE = "https://rxnav.nlm.nih.gov/REST"

def get_rxcui(drug_name):
    r = requests.get(f"{BASE}/rxcui.json", params={"name": drug_name})
    ids = r.json().get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None

def get_drug_classes(rxcui):
    """Return the drug classes for a given rxcui (e.g. amoxicillin -> Penicillins)."""
    r = requests.get(
        f"{BASE}/rxclass/class/byRxcui.json",
        params={"rxcui": rxcui, "relaSource": "ATC"}
    )
    classes = []
    for item in r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
        cls = item.get("rxclassMinConceptItem", {})
        name = cls.get("className")
        if name and name not in classes:
            classes.append(name)
    return classes

for name in ["amoxicillin", "lisinopril", "aspirin"]:
    rxcui = get_rxcui(name)
    classes = get_drug_classes(rxcui)
    print(f"{name} (RxCUI {rxcui}):")
    for c in classes:
        print(f"   - {c}")
    print()