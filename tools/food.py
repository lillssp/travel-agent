"""Tool: find_food_nearby. Real restaurants, cafes and bars near a point."""

from .common import GeoapifyError, geoapify_get

FOOD_KINDS = {
    "restaurant": "catering.restaurant",
    "cafe": "catering.cafe",
    "bar": "catering.bar",
    "fast_food": "catering.fast_food",
}

def find_food_nearby(latitude: float, longitude: float, kind: str = "restaurant",
                     radius_m: int = 700, limit: int = 6) -> dict:
    if kind not in FOOD_KINDS:
        return {"error": f"kind must be one of: {', '.join(FOOD_KINDS)}."}
    radius_m, limit = int(radius_m), int(limit) 

    try:
        data = geoapify_get("/v2/places", {
            "categories": FOOD_KINDS[kind],
            "conditions": "named",
            "filter": f"circle:{longitude},{latitude},{radius_m}",
            "bias": f"proximity:{longitude},{latitude}",
            "limit": 20,
            "lang": "en",
        })
    except GeoapifyError as e:
        return {"error": str(e)}

    places = []
    seen = set()  
    for feature in data.get("features", []):
        props = feature["properties"]
        if not props.get("name") or props["name"] in seen:
            continue
        seen.add(props["name"])
        places.append({
            "name": props["name"],
            "cuisine": props.get("catering", {}).get("cuisine", ""),
            "address": props.get("address_line2", ""),
            "distance_m": props.get("distance"),
            "opening_hours": props.get("opening_hours", ""),
            "website": props.get("website", ""),
            "latitude": props.get("lat"),
            "longitude": props.get("lon"),
        })

    if not places:
        return {"error": f"No {kind} places found within {radius_m} m."}
    return {"kind": kind, "radius_m": radius_m, "places": places[:limit]}