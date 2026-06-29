import requests, json

BASE = "https://rxnav.nlm.nih.gov/REST"

def get_rxcui(drug_name):
    r = requests.get(f"{BASE}/rxcui.json", params={"name": drug_name})
    ids = r.json().get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None

def get_drug_classes(rxcui):
    r = requests.get(f"{BASE}/rxclass/class/byRxcui.json",
                     params={"rxcui": rxcui, "relaSource": "ATC"})
    out = []
    for item in r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
        name = item.get("rxclassMinConceptItem", {}).get("className")
        if name: out.append(name)
    return out

def extract_allergies(bundle):
    out = []
    for e in bundle.get("entry", []):
        res = e.get("resource", {})
        if res.get("resourceType") == "AllergyIntolerance":
            code = res.get("code", {})
            t = code.get("text") or (code.get("coding", [{}])[0].get("display"))
            if t: out.append(t)
    return out

def extract_active_meds(bundle):
    out = []
    for e in bundle.get("entry", []):
        res = e.get("resource", {})
        if res.get("resourceType") == "MedicationRequest" and res.get("status") == "active":
            med = res.get("medicationCodeableConcept", {})
            t = med.get("text") or (med.get("coding", [{}])[0].get("display"))
            if t: out.append(t)
    return out

def check_bundle(bundle):
    allergies = extract_allergies(bundle)
    meds = extract_active_meds(bundle)
    findings = []
    for allergy in allergies:
        a = allergy.lower()[:6]
        for med in meds:
            drug = med.split()[0]
            rxcui = get_rxcui(drug)
            classes = get_drug_classes(rxcui) if rxcui else []
            matched = [c for c in classes if a in c.lower()]
            if a in drug.lower():
                matched.append(f"direct match: {drug}")
            if matched:
                findings.append({"allergy": allergy, "med": med, "matched_on": matched})
    return findings

# --- Test bundle: penicillin-allergic patient prescribed amoxicillin ---
bundle = {
    "resourceType": "Bundle",
    "entry": [
        {"resource": {"resourceType": "AllergyIntolerance", "code": {"text": "Penicillin"}}},
        {"resource": {"resourceType": "MedicationRequest", "status": "active",
                      "medicationCodeableConcept": {"text": "Amoxicillin 250 MG / Clavulanate 125 MG Oral Tablet"}}},
        {"resource": {"resourceType": "MedicationRequest", "status": "active",
                      "medicationCodeableConcept": {"text": "lisinopril 10 MG Oral Tablet"}}},
    ]
}

print("=== MED-ALLERGY VALIDATION REPORT ===\n")
findings = check_bundle(bundle)
if findings:
    for f in findings:
        print(f"⚠  CONFLICT")
        print(f"   Allergy:     {f['allergy']}")
        print(f"   Medication:  {f['med']}")
        print(f"   Matched on:  {f['matched_on']}\n")
else:
    print("No medication-allergy conflicts found.")