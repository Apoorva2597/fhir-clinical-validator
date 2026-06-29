# FHIR Clinical Data Validator

A validation layer that checks whether a patient's structured clinical data is trustworthy enough for an AI agent to act on. It takes raw HL7 v2 messages or FHIR bundles, runs a set of clinical and structural checks, and produces a plain trust report that flags problems before an agent ever sees the data.

## Why this exists

Most clinical AI right now is agent-shaped. Scribes, schedulers, intake bots, prior-auth bots, and chart-prep tools all read a patient's structured record and act on it. The quiet assumption underneath all of them is that the data they read is complete and consistent.

It often is not.

Existing safeguards were built for a human in the loop. When a doctor prescribes a drug, the EHR fires an allergy alert. When a pharmacist dispenses it, they check again. Those safeguards work, but they protect a person at the moment of prescribing. They do not protect an autonomous agent that is summarizing a chart, recommending a next step, or prepping a visit, because there is no human in that loop to catch a gap.

So the question this project asks is different from "will the EHR warn the doctor." It asks "is this record internally consistent and complete enough for an agent to act on safely." That is an emerging gap, not the solved prescribing-alert problem.

There is also a business reason. If an AI vendor deploys an agent into a practice and the agent acts on bad data, the vendor does not want to be blamed later for a practice's missing or wrong records. Running independent quality checks on the data before the agent touches it is a way for the vendor to earn the practice's trust and to draw a clear line around what the agent is responsible for. Validation is as much a trust-and-liability mechanism between vendor and practice as it is a safety feature.

## What it does

The tool runs four checks on a FHIR bundle and prints a trust report with a verdict.

**1. Medication-allergy conflict**
Flags an active medication that conflicts with a documented allergy. Instead of a hardcoded list of drug-allergy pairs, it resolves each drug to its class using the NLM's RxNorm data (via the RxNav API), so it knows on its own that amoxicillin is a penicillin and conflicts with a penicillin allergy. The report explains the match (for example, "matched on: Penicillins with extended spectrum") rather than just raising a flag.

**2. Duplicate active medications**
Flags the same drug appearing as active more than once. This is a common medication-reconciliation problem and a sign the record was not cleaned up across encounters.

**3. Incomplete medication dosage**
Flags active medications with no dosage instruction. An agent reasoning over a medication with no dose is working with a hole in the data, which is unsafe to act on.

**4. Missing allergy list (confidence-lowering)**
If a patient has active medications but no allergy information at all, the tool does not assume they have no allergies. It flags that medication safety cannot be verified and that confidence in any medication-related AI recommendation should be lowered. This is the difference between "the data is wrong" and "the data is incomplete in a way the agent should account for."

Each check is a different way structured data can be untrustworthy for an agent: a clinical conflict, a reconciliation error, a missing field, and an incompleteness that should lower confidence.

## How it is built

The pipeline mirrors how real interoperability work flows, from raw hospital messages to validated FHIR.

```
HL7 v2 message  ->  parse  ->  map to FHIR  ->  bundle  ->  validate  ->  trust report
                                                  ^
Synthea synthetic FHIR  ------------------------- |
```

- **HL7 parsing.** Parses HL7 v2 ADT messages (patient demographics and allergies) using hl7apy.
- **HL7 to FHIR mapping.** Maps PID and AL1 segments into FHIR R4 Patient and AllergyIntolerance resources, including the small real-world fixes that come up: reformatting dates from YYYYMMDD to YYYY-MM-DD, mapping sex codes to FHIR gender values, and stripping component separators out of allergen names. The mapped FHIR matches the shape Synthea produces, so the same validation checks run on both paths.
- **Synthetic data.** Uses Synthea to generate realistic synthetic FHIR patients. No real patient data is used anywhere in this project.
- **FHIR server.** Loads bundles into a local HAPI FHIR server (run in Docker) in the correct dependency order, so the data can be queried back like a real FHIR repository.
- **Validation.** Runs the four checks on any bundle, whether it came from Synthea or from the HL7 mapper.

## Design decisions and tradeoffs

These are the real-world constraints I reasoned through, and where I drew the lines on scope.

**Structured validation is cheaper and earlier, but blind to the narrative.**
Checking structured FHIR resources is far lighter than running NLP over free-text notes. The tradeoff is that the most important detail is sometimes only in the note (the reason a medication was switched, a symptom mentioned verbally). So this is a complement to notes-based validation, not a replacement. It catches a different and more tractable class of problem, earlier and more cheaply.

**The allergy check started as a static map, then moved to real terminology.**
The first version used a small hardcoded cross-reactivity map to prove the logic. The current version resolves drug classes through RxNorm, which is how production systems actually do this. The static map is the wrong long-term answer because it does not scale to thousands of drugs; the RxNorm version derives the relationships from authoritative data. I have UMLS access as well, which would be the next step for bridging across vocabularies (for example, matching a drug to a SNOMED-coded allergy concept).

**Validation is stateless by design.**
Every check runs on a single bundle with no stored history. This matters because it works on the very first patient, with no prior data and no storage cost. A stateful version (comparing a record to its own past to catch, for example, a medication that changed without reconciliation) is a natural extension, but it requires a persistent longitudinal record. Production systems already maintain that record for the agent itself, so a stateful validator would read from it rather than introduce new storage. I scoped that out on purpose and noted it here rather than half-building it.

**History is costly to pull, so it is scoped to the workflow.**
Pulling a patient's full history on every agent call is expensive. In production you would pull only what the workflow needs. Here, working with synthetic data, cost is not a constraint, but the design assumes selective history in a real deployment.

**What existing safeguards already cover.**
EHR prescriber alerts and pharmacist checks already handle medication-allergy conflicts when the allergy is documented in structured data and a human is in the loop. This project is not trying to replace those. It addresses the cases they do not reach: when the allergy was never captured as structured data, when it did not flow across systems, and when an autonomous agent consumes the record with no human to catch the gap.

## Running it

```
# generate synthetic patients
java -jar synthea-with-dependencies.jar -p 10

# (optional) run a local FHIR server
docker run -p 8080:8080 hapiproject/hapi:latest

# parse and map an HL7 message to FHIR
python hl7_to_fhir.py

# run the validator on real bundles
python validator.py
```

The validator prints a trust report per patient, with each check, the specific findings, and a verdict line indicating whether the record is clean enough for an agent to act on or needs review first.

## What I would build next

- Bridge drug and allergy codes across vocabularies using UMLS, so the check works on SNOMED-coded allergies, not just text.
- Add the stateful longitudinal check, reading from a persistent patient record rather than stored bundles.
- Add a notes-based layer to catch what structured validation cannot see, making the two complementary in one tool.

## Note on data

Everything here runs on synthetic data only, generated by Synthea or hand-built for testing. No real patient information is used at any point.
