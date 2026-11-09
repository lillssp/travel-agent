"""Shared helpers for all tools: settings, HTTP requests, dates, distances."""

import math
import os
import time
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()
GEOAPIFY_KEY = os.getenv("GEOAPIFY_KEY")

TIMEOUT = 10
HEADERS = {"User-Agent": "TravelPlannerAgent/1.0 (student project)"}
GEOAPIFY_URL = "https://api.geoapify.com"

CATEGORIES = ("transport", "food", "sightseeing", "entertainment", "shopping", "others")

def get_json(url, params):
    response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()

class GeoapifyError(Exception):
    """Geoapify problem with a safe message (it never contains the API key)."""

def geoapify_get(path, params):
    try:
        return get_json(GEOAPIFY_URL + path, {**params, "apiKey": GEOAPIFY_KEY})
    except requests.HTTPError as e:
        raise GeoapifyError(f"Geoapify returned HTTP {e.response.status_code}.") from None
    except requests.RequestException:
        raise GeoapifyError("Geoapify request failed.") from None

def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def distance_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))