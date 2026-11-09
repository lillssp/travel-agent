"""Tool: save_trip. Saves the finished plan as JSON"""

import json
import os
import re

from .common import CATEGORIES, parse_date

TRIPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trips")

def save_trip(trip: dict) -> dict:
    for field in ("title", "start_date", "end_date"):
        if not trip.get(field):
            return {"error": f"Missing required field: {field}"}
    if not parse_date(trip["start_date"]) or not parse_date(trip["end_date"]):
        return {"error": "start_date and end_date must be in YYYY-MM-DD format."}

    places = []
    for p in trip.get("places", []):
        if not p.get("title"):
            return {"error": f"Every place needs a title: {p}"}
        category = p.get("category", "others")
        places.append({
            "category": category if category in CATEGORIES else "others",
            "title": p["title"],
            "description": p.get("description", ""),
            "address": p.get("address", ""),
            "link": p.get("link", ""),
            "notes": p.get("notes", ""),
            "visit_date": p.get("visit_date"),
            "visit_time": p.get("visit_time"),
            "cost": p.get("cost", 0),
        })

    data = {
        "title": trip["title"],
        "country": trip.get("country", ""),
        "city": trip.get("city", ""),
        "description": trip.get("description", ""),
        "currency": trip.get("currency", ""),
        "start_date": trip["start_date"],
        "end_date": trip["end_date"],
        "total_budget": trip.get("total_budget", 0),
        "places": places,
    }

    slug = re.sub(r"[^a-z0-9]+", "-", trip["title"].lower()).strip("-") or "trip"
    os.makedirs(TRIPS_DIR, exist_ok=True)
    path = os.path.join(TRIPS_DIR, f"{slug}_{trip['start_date']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "saved": True,
        "file": os.path.basename(path),
        "places_count": len(places),
        "total_planned_cost": round(sum(float(p["cost"] or 0) for p in places), 2),
        "trip": data,
    }