import requests
import validator  # reuses your existing validate() and all four checks

FHIR_SERVER = "http://localhost:8080/fhir"

def fetch_patient_bundle(patient_id):
    """Pull a patient's full record from the FHIR server using $everything."""
    url = f"{FHIR_SERVER}/Patient/{patient_id}/$everything"
    # ask for a generous page size so we get meds + allergies in one go
    resp = requests.get(url, params={"_count": 200}, timeout=30)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    patient_id = "2014"
    print(f"Fetching patient {patient_id} from {FHIR_SERVER} ...\n")

    bundle = fetch_patient_bundle(patient_id)

    n = len(bundle.get("entry", []))
    print(f"Server returned a bundle with {n} resources.\n")

    # feed the server-returned bundle straight into the existing validator
    validator.validate(bundle, label=f"Patient/{patient_id} (from FHIR server)")