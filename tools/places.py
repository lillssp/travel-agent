"""Tool: find_place. Finds a place on the map: address and coordinates."""

import re
import unicodedata

from .common import GeoapifyError, distance_km, geoapify_get
from .geocoding import geocode

VAGUE_RESULT_TYPES = ("city", "suburb", "district", "postcode", "county", "state", "country")

MAX_DISTANCE_KM = 50   
NAME_MATCH_MIN = 0.6 

STOPWORDS = {
    "of", "the", "de", "da", "do", "dos", "das", "del", "la", "le", "el", "and",
    "du", "des", "les", "di", "della", "dei", "von", "der", "den",
}

SYNONYMS = {
    "musee": "museum", "museu": "museum", "museo": "museum", "musei": "museum",
    "palais": "palace", "palacio": "palace", "palazzo": "palace", "palau": "palace",
    "chateau": "castle", "castelo": "castle", "castillo": "castle", "castello": "castle",
    "tour": "tower", "torre": "tower",
    "eglise": "church", "igreja": "church", "iglesia": "church", "chiesa": "church",
    "cathedrale": "cathedral", "catedral": "cathedral", "duomo": "cathedral", "se": "cathedral",
    "mosteiro": "monastery", "monastere": "monastery", "monasterio": "monastery",
    "praca": "square", "plaza": "square", "piazza": "square", "platz": "square", "place": "square",
    "jardin": "garden", "jardim": "garden", "giardino": "garden",
    "parc": "park", "parque": "park", "parco": "park",
    "marche": "market", "mercado": "market", "mercato": "market",
    "pont": "bridge", "ponte": "bridge", "puente": "bridge",
    "nacional": "national", "elevador": "elevator", "lift": "elevator",
}

GENERIC_WORDS = {
    "museum", "national", "church", "cathedral", "castle", "palace", "monastery", "convento",
    "convent", "tower", "square", "garden", "park", "restaurant", "restaurante", "cafe",
    "market", "bridge", "miradouro", "viewpoint", "rua", "street", "avenida", "avenue",
    "hotel", "house", "casa", "basilica", "old", "town", "city",
}

_city_cache = {} 


def tokens(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    words = (SYNONYMS.get(w, w) for w in re.findall(r"[a-z0-9]+", text) if w not in STOPWORDS)
    return set(words)


def name_match(query, found):
    wanted = tokens(query)
    if not wanted:
        return 1.0
    distinctive = wanted - GENERIC_WORDS or wanted
    return len(distinctive & tokens(found)) / len(distinctive)


def _geocode_city(city):
    if city not in _city_cache:
        geo = geocode(city)
        if "error" in geo:
            return geo 
        _city_cache[city] = geo
    return _city_cache[city]


def find_place(name: str, city: str) -> dict:
    geo = _geocode_city(city)
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
    similarity = name_match(name, r.get("formatted", ""))
    candidate = {
        "name": r.get("name") or name,
        "address": r.get("formatted", ""),
        "latitude": r["lat"],
        "longitude": r["lon"],
        "distance_from_city_km": round(distance, 1),
        "name_similarity": round(similarity, 2),
    }

    if r.get("result_type") in VAGUE_RESULT_TYPES:
        return {"found": False, "note": f"Only the area was found, not '{name}' itself.",
                "closest_match": candidate}
    if distance > MAX_DISTANCE_KM:
        return {"found": False, "note": f"The closest match is {round(distance)} km from {city}.",
                "closest_match": candidate}

    result = {"found": True, **candidate}
    if similarity < NAME_MATCH_MIN:
        result["warning"] = (f"The name on the map ('{candidate['name']}') differs from '{name}'. "
                             "Use this place only if it is clearly the same one; otherwise drop it.")
    return result