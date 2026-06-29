from hl7apy.parser import parse_message
from fhir.resources.patient import Patient
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.reference import Reference
import json

# --- Read and parse the HL7 message ---
with open("hl7_samples/sample_adt.hl7", "r") as f:
    raw = f.read().strip().replace("\n", "\r")
msg = parse_message(raw)

# --- Map PID segment -> FHIR Patient ---
pid = msg.pid
mrn = pid.patient_identifier_list.id_number.value
last_name = pid.patient_name.family_name.value
first_name = pid.patient_name.given_name.value
dob_raw = pid.date_time_of_birth.value          # format: YYYYMMDD
sex = pid.administrative_sex.value               # M / F

# FHIR wants dates as YYYY-MM-DD
dob_fhir = f"{dob_raw[0:4]}-{dob_raw[4:6]}-{dob_raw[6:8]}"
# FHIR gender is lowercase words
gender_map = {"M": "male", "F": "female"}
gender = gender_map.get(sex, "unknown")

patient = Patient(
    id="patient-1",
    identifier=[Identifier(system="urn:hospital:mrn", value=mrn)],
    name=[HumanName(family=last_name, given=[first_name])],
    gender=gender,
    birthDate=dob_fhir,
)

# --- Map AL1 segments -> FHIR AllergyIntolerance resources ---
allergies = []
for i, al1 in enumerate(msg.al1, start=1):
    allergen_raw = al1.allergen_code_mnemonic_description.value
    # strip the leading "^" component separator if present
    allergen = allergen_raw.split("^")[-1]
    allergy = AllergyIntolerance(
        id=f"allergy-{i}",
        patient=Reference(reference="Patient/patient-1"),
        code=CodeableConcept(text=allergen),
    )
    allergies.append(allergy)

# --- Print the FHIR output ---
print("=== FHIR PATIENT ===")
print(patient.json(indent=2))

print("\n=== FHIR ALLERGIES ===")
for a in allergies:
    print(a.json(indent=2))