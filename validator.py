import requests, json, sys, glob, os

BASE = "https://rxnav.nlm.nih.gov/REST"

# ---------- RxNav helpers (Check 1) ----------
def get_rxcui(drug_name):
    try:
        r = requests.get(f"{BASE}/rxcui.json", params={"name": drug_name}, timeout=10)
        ids = r.json().get("idGroup", {}).get("rxnormId", [])
        return ids[0] if ids else None
    except Exception:
        return None

def get_drug_classes(rxcui):
    try:
        r = requests.get(f"{BASE}/rxclass/class/byRxcui.json",
                         params={"rxcui": rxcui, "relaSource": "ATC"}, timeout=10)
        out = []
        for item in r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            name = item.get("rxclassMinConceptItem", {}).get("className")
            if name: out.append(name)
        return out
    except Exception:
        return []

# ---------- extractors ----------
def get_allergies(bundle):
    out = []
    for e in bundle.get("entry", []):
        res = e.get("resource", {})
        if res.get("resourceType") == "AllergyIntolerance":
            code = res.get("code", {})
            t = code.get("text") or (code.get("coding", [{}])[0].get("display"))
            if t: out.append(t)
    return out

def get_active_meds(bundle):
    out = []
    for e in bundle.get("entry", []):
        res = e.get("resource", {})
        if res.get("resourceType") == "MedicationRequest" and res.get("status") == "active":
            med = res.get("medicationCodeableConcept", {})
            name = med.get("text") or (med.get("coding", [{}])[0].get("display"))
            out.append((name, res))
    return out

def has_allergy_resources(bundle):
    return any(e.get("resource", {}).get("resourceType") == "AllergyIntolerance"
               for e in bundle.get("entry", []))

# ---------- the four checks ----------
def check_med_allergy(bundle):
    findings = []
    allergies = get_allergies(bundle)
    meds = get_active_meds(bundle)
    for allergy in allergies:
        a = allergy.lower()[:6]
        for name, _ in meds:
            if not name: continue
            drug = name.split()[0]
            rxcui = get_rxcui(drug)
            classes = get_drug_classes(rxcui) if rxcui else []
            matched = [c for c in classes if a in c.lower()]
            if a in drug.lower():
                matched.append(f"direct match: {drug}")
            if matched:
                findings.append({"allergy": allergy, "med": name, "matched_on": matched})
    return findings

def check_duplicate_meds(bundle):
    seen = {}
    for name, _ in get_active_meds(bundle):
        if not name: continue
        key = name.split()[0].lower()
        seen[key] = seen.get(key, 0) + 1
    return [{"drug": k, "active_count": v} for k, v in seen.items() if v > 1]

def check_incomplete_dosage(bundle):
    out = []
    for name, res in get_active_meds(bundle):
        if not res.get("dosageInstruction"):
            out.append({"med": name})
    return out

def check_missing_allergy_list(bundle):
    meds = get_active_meds(bundle)
    if meds and not has_allergy_resources(bundle):
        return {"active_medications": len(meds)}
    return None

# ---------- run the full suite ----------
def validate(bundle, label=""):
    print("=" * 60)
    print(f"TRUST REPORT{(' — ' + label) if label else ''}")
    print("=" * 60)

    issues = 0

    c1 = check_med_allergy(bundle)
    print("\n[1] Medication–Allergy Conflicts")
    if c1:
        issues += len(c1)
        for f in c1:
            print(f"  ⚠ allergic to '{f['allergy']}' but prescribed '{f['med']}'")
            print(f"     matched on: {f['matched_on']}")
    else:
        print("  ✓ none")

    c2 = check_duplicate_meds(bundle)
    print("\n[2] Duplicate Active Medications")
    if c2:
        issues += len(c2)
        for d in c2:
            print(f"  ⚠ '{d['drug']}' active {d['active_count']} times")
    else:
        print("  ✓ none")

    c3 = check_incomplete_dosage(bundle)
    print("\n[3] Incomplete Medication Dosage")
    if c3:
        issues += len(c3)
        for i in c3:
            print(f"  ⚠ '{i['med']}' has no dosage instruction")
    else:
        print("  ✓ none")

    c4 = check_missing_allergy_list(bundle)
    print("\n[4] Missing Allergy List (confidence)")
    if c4:
        issues += 1
        print(f"  ⚠ no allergy data, but {c4['active_medications']} active meds")
        print("     → lower confidence for medication-related AI recommendations")
    else:
        print("  ✓ allergy list present")

    print("\n" + "-" * 60)
    verdict = "TRUSTWORTHY for agent use" if issues == 0 else f"{issues} issue(s) — review before agent acts"
    print(f"VERDICT: {verdict}")
    print("=" * 60 + "\n")
    return issues


if __name__ == "__main__":
    # Run on real Synthea patient bundles
    files = [f for f in glob.glob("output/fhir/*.json")
             if not os.path.basename(f).startswith(("hospitalInformation", "practitionerInformation"))]

    # Validate the first 3 real patients
    for path in files[:3]:
        with open(path, "r", encoding="utf-8") as f:
            bundle = json.load(f)
        validate(bundle, label=os.path.basename(path)[:25])