import json

# ---------- shared extractors ----------
def get_active_meds(bundle):
    """Return list of (name, full_resource) for active medications."""
    meds = []
    for e in bundle.get("entry", []):
        res = e.get("resource", {})
        if res.get("resourceType") == "MedicationRequest" and res.get("status") == "active":
            med = res.get("medicationCodeableConcept", {})
            name = med.get("text") or (med.get("coding", [{}])[0].get("display"))
            meds.append((name, res))
    return meds

def has_allergy_resources(bundle):
    """True if the bundle contains at least one AllergyIntolerance resource."""
    for e in bundle.get("entry", []):
        if e.get("resource", {}).get("resourceType") == "AllergyIntolerance":
            return True
    return False


# ---------- CHECK 2: duplicate active medications ----------
def check_duplicate_meds(bundle):
    meds = get_active_meds(bundle)
    seen = {}
    findings = []
    for name, _ in meds:
        if not name:
            continue
        # normalize: compare on the drug name (first word) to catch same drug, any formatting
        key = name.split()[0].lower()
        seen[key] = seen.get(key, 0) + 1
    for key, count in seen.items():
        if count > 1:
            findings.append({"drug": key, "active_count": count})
    return findings


# ---------- CHECK 3: incomplete medication dosage ----------
def check_incomplete_dosage(bundle):
    findings = []
    for name, res in get_active_meds(bundle):
        dosage = res.get("dosageInstruction")
        # flag if there's no dosage instruction at all, or it's empty
        if not dosage:
            findings.append({"med": name, "issue": "no dosage instruction"})
    return findings


# ---------- CHECK 4: missing allergy list (confidence-lowering) ----------
def check_missing_allergy_list(bundle):
    meds = get_active_meds(bundle)
    # only meaningful if the patient is actually on medications
    if meds and not has_allergy_resources(bundle):
        return {
            "issue": "No allergy information documented",
            "active_medications": len(meds),
            "impact": "Cannot verify medication safety. Confidence in any "
                      "medication-related AI recommendation should be lowered."
        }
    return None


# ---------- run all three on a test bundle ----------
if __name__ == "__main__":
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            # duplicate active lisinopril (check 2 should flag)
            {"resource": {"resourceType": "MedicationRequest", "status": "active",
                          "medicationCodeableConcept": {"text": "lisinopril 10 MG Oral Tablet"},
                          "dosageInstruction": [{"text": "1 tablet daily"}]}},
            {"resource": {"resourceType": "MedicationRequest", "status": "active",
                          "medicationCodeableConcept": {"text": "lisinopril 20 MG Oral Tablet"},
                          "dosageInstruction": [{"text": "1 tablet daily"}]}},
            # active med with NO dosage (check 3 should flag)
            {"resource": {"resourceType": "MedicationRequest", "status": "active",
                          "medicationCodeableConcept": {"text": "metformin 500 MG Oral Tablet"}}},
            # NOTE: no AllergyIntolerance resource at all (check 4 should flag)
        ]
    }

    print("=== CHECK 2: DUPLICATE ACTIVE MEDICATIONS ===")
    dups = check_duplicate_meds(bundle)
    if dups:
        for d in dups:
            print(f"⚠  '{d['drug']}' appears as active {d['active_count']} times")
    else:
        print("None found.")

    print("\n=== CHECK 3: INCOMPLETE MEDICATION DOSAGE ===")
    inc = check_incomplete_dosage(bundle)
    if inc:
        for i in inc:
            print(f"⚠  '{i['med']}' — {i['issue']}")
    else:
        print("None found.")

    print("\n=== CHECK 4: MISSING ALLERGY LIST ===")
    miss = check_missing_allergy_list(bundle)
    if miss:
        print(f"⚠  {miss['issue']} ({miss['active_medications']} active meds)")
        print(f"   {miss['impact']}")
    else:
        print("Allergy list present.")