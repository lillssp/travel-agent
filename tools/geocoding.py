"""Tool: geocode. Place name -> coordinates."""

import requests

from .common import get_json

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

def geocode(place: str) -> dict:
    name, _, hint = place.partition(",")
    hint = hint.strip().lower()

    try:
        data = get_json(GEOCODING_URL, {"name": name.strip(), "count": 5, "language": "en"})
    except requests.RequestException as e:
        return {"error": f"Geocoding failed: {e}"}

    results = data.get("results") or []
    if not results:
        return {"error": f"Place '{place}' was not found."}

    best = results[0]
    if hint:
        for r in results:
            if hint in r.get("country", "").lower() or hint in r.get("admin1", "").lower():
                best = r
                break

    return {
        "name": best["name"],
        "country": best.get("country", ""),
        "region": best.get("admin1", ""),
        "latitude": best["latitude"],
        "longitude": best["longitude"],
        "timezone": best.get("timezone", ""),
    }