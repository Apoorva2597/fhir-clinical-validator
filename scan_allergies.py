import json, glob, os

files = [f for f in glob.glob("output/fhir/*.json")
         if not os.path.basename(f).startswith(("hospitalInformation", "practitionerInformation"))]

for path in files:
    with open(path, "r", encoding="utf-8") as f:
        bundle = json.load(f)
    allergies = []
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "AllergyIntolerance":
            code = res.get("code", {})
            text = code.get("text") or (code.get("coding", [{}])[0].get("display"))
            allergies.append(text)
    if allergies:
        print(f"{os.path.basename(path)[:30]}: {allergies}")

print("Scan complete.")