import requests
import glob
import os

def upload(path):
    with open(path, "r", encoding="utf-8") as f:
        bundle = f.read()
    resp = requests.post(
        "http://localhost:8080/fhir",
        headers={"Content-Type": "application/fhir+json"},
        data=bundle.encode("utf-8"),
    )
    name = os.path.basename(path)
    status = "OK" if resp.status_code in (200, 201) else f"FAILED ({resp.status_code})"
    print(f"{status}: {name}")
    if resp.status_code not in (200, 201):
        print("   " + resp.text[:300])

all_files = glob.glob("output/fhir/*.json")

# Upload reference data FIRST (hospitals, practitioners), then patients
ref_files = [f for f in all_files if os.path.basename(f).startswith(("hospitalInformation", "practitionerInformation"))]
patient_files = [f for f in all_files if f not in ref_files]

print("=== Uploading reference data ===")
for f in ref_files:
    upload(f)

print("\n=== Uploading patients ===")
for f in patient_files[:3]:   # just the first 3 patients to start
    upload(f)