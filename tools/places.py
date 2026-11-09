"""Tool: find_place. Checks that a place really exists."""

import re
import unicodedata

from .common import GeoapifyError, distance_km, geoapify_get
from .geocoding import geocode

VAGUE_RESULT_TYPES = ("city", "suburb", "district", "postcode", "county", "state", "country")

NAME_MATCH_MIN = 0.6 
STOPWORDS = {"of", "the", "de", "da", "do", "dos", "das", "del", "la", "le", "el", "and"}
GENERIC_WORDS = {
    "museu", "museum", "nacional", "national", "church", "igreja", "cathedral", "castelo", "castle",
    "palace", "palacio", "mosteiro", "monastery", "convento", "convent", "torre", "tower", "square",
    "praca", "plaza", "largo", "jardim", "garden", "park", "parque", "restaurante", "restaurant",
    "cafe", "mercado", "market", "bridge", "ponte", "miradouro", "viewpoint", "rua", "street",
    "avenida", "avenue", "hotel", "house", "casa",
}

def tokens(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z0-9]+", text) if w not in STOPWORDS}

def name_match(query, found):
    wanted = tokens(query)
    if not wanted:
        return 1.0
    present = tokens(found)
    overall = len(wanted & present) / len(wanted)
    distinctive = wanted - GENERIC_WORDS or wanted
    return min(overall, len(distinctive & present) / len(distinctive))


def find_place(name: str, city: str) -> dict:
    geo = geocode(city)
    if "error" in geo:
        return geo

    try:
        data = geoapify_get("/v1/geocode/search", {
            "text": f"{name}, {city}",
            "limit": 1,
            "lang": "en",
            "format": "json",
            "bias": f"proximity:{geo['longitude']},{geo['latitude']}",
        })
    except GeoapifyError as e:
        return {"error": str(e)}

    results = data.get("results") or []
    if not results:
        return {"found": False, "note": f"'{name}' was not found in {city}. It may not exist."}

    r = results[0]
    distance = distance_km(geo["latitude"], geo["longitude"], r["lat"], r["lon"])
    candidate = {
        "name": r.get("name") or name,
        "address": r.get("formatted", ""),
        "latitude": r["lat"],
        "longitude": r["lon"],
        "distance_from_city_km": round(distance, 1),
    }

    if name_match(name, r.get("formatted", "")) < NAME_MATCH_MIN:
        return {
            "found": False,
            "note": f"No place with a name close to '{name}' was found in {city}. "
                    "The closest result is below; use it only if it is clearly the same "
                    "place under another name or language.",
            "closest_match": candidate,
        }

    result = {"found": True, **candidate}
    if r.get("result_type") in VAGUE_RESULT_TYPES:
        result["warning"] = "Only the area was found, not this exact place. Check the name."
    elif distance > 50:
        result["warning"] = "The match is more than 50 km from the city. Check that it is the right place."
    return result