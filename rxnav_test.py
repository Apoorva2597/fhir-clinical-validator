import requests

BASE = "https://rxnav.nlm.nih.gov/REST"

def get_rxcui(drug_name):
    """Resolve a drug name to its RxCUI (RxNorm concept id)."""
    r = requests.get(f"{BASE}/rxcui.json", params={"name": drug_name})
    ids = r.json().get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None

def get_ingredients(rxcui):
    """Get the base ingredient(s) for a drug rxcui."""
    r = requests.get(f"{BASE}/rxcui/{rxcui}/related.json", params={"tty": "IN"})
    groups = r.json().get("relatedGroup", {}).get("conceptGroup", [])
    ingredients = []
    for g in groups:
        for c in g.get("conceptProperties", []):
            ingredients.append(c.get("name"))
    return ingredients

# Test with a clean drug name
name = "amoxicillin"
rxcui = get_rxcui(name)
print(f"Drug: {name}")
print(f"RxCUI: {rxcui}")
print(f"Ingredients: {get_ingredients(rxcui)}")