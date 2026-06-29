from hl7apy.parser import parse_message

# Read the raw HL7 message from the file
with open("hl7_samples/sample_adt.hl7", "r") as f:
    raw = f.read().strip()

# HL7 messages use \r (carriage return) as segment separators.
# Notepad saves with \r\n, so normalize to \r for hl7apy.
raw = raw.replace("\n", "\r")

# Parse the message
msg = parse_message(raw)

# Pull patient info from the PID segment
pid = msg.pid
last_name = pid.patient_name.family_name.value
first_name = pid.patient_name.given_name.value
dob = pid.date_time_of_birth.value
sex = pid.administrative_sex.value
mrn = pid.patient_identifier_list.id_number.value

print("=== PATIENT ===")
print(f"Name: {first_name} {last_name}")
print(f"MRN: {mrn}")
print(f"DOB: {dob}")
print(f"Sex: {sex}")

# Pull allergies from the AL1 segments (there can be several)
print("\n=== ALLERGIES ===")
for al1 in msg.al1:
    allergen = al1.allergen_code_mnemonic_description.value
    print(f"- {allergen}")