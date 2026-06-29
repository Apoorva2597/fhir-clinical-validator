import json, glob, os

# Grab the first patient bundle (skip reference files)
files = [f for f in glob.glob("output/fhir/*.json")
         if not os.path.basename(f).startswith(("hospitalInformation", "practitionerInformation"))]
path = files[0]
print(f"Inspecting: {os.path.basename(path)}\n")

with open(path, "r", encoding="utf-8") as f:
    bundle = json.load(f)

# Walk every resource in the bundle, collect allergies and medications
allergies, meds = [], []
for entry in bundle.get("entry", []):
    res = entry.get("resource", {})
    rtype = res.get("resourceType")
    if rtype == "AllergyIntolerance":
        # the allergen is usually in code.text or code.coding[].display
        code = res.get("code", {})
        text = code.get("text") or (code.get("coding", [{}])[0].get("display"))
        allergies.append(text)
    elif rtype == "MedicationRequest":
        med = res.get("medicationCodeableConcept", {})
        text = med.get("text") or (med.get("coding", [{}])[0].get("display"))
        status = res.get("status")
        meds.append((text, status))

print("=== ALLERGIES ===")
for a in allergies:
    print(f"- {a}")

print("\n=== MEDICATIONS (with status) ===")
for m, s in meds:
    print(f"- [{s}] {m}")