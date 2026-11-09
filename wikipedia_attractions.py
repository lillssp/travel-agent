"""NOT USED by the agent. find_attractions built on Wikipedia, kept here just in case.

It finds the most popular Wikipedia pages near a city (ranked by page views over the
last 30 days) and filters out things that are not sights. It makes ~15 requests on
the first call per city (then it is cached), so it is slow and Wikipedia may answer 429.

Quick check:  python wikipedia_attractions.py
"""

import re
import time
from functools import lru_cache
from urllib.parse import quote

import requests

from tools import geocode

TIMEOUT = 10
# Wikimedia asks API clients to identify themselves with contact info.
# TODO: put your own GitHub link or email here before using this file.
HEADERS = {"User-Agent": "TravelPlannerAgent/1.0 (https://github.com/YOUR_USERNAME; YOUR_EMAIL@example.com)"}
WIKIPEDIA_URL = "https://en.wikipedia.org/w/api.php"

# pages whose first sentence contains one of these words are skipped
NOT_ATTRACTIONS = (
    "airport", "railway station", "metro station", "train station", "company",
    "federation", "ministry", "university", "hospital", "institute",
    "football club", "headquarters", "political party", "municipality",
    "derailment", "accident",
)
# whole words only, so that e.g. "bank" would not match "river bank" inside a landmark description
NOT_ATTRACTIONS_RE = re.compile(r"\b(" + "|".join(NOT_ATTRACTIONS) + r")\b")


def _get(url, params):
    """GET request returning JSON. If the server says 'too many requests' (429), wait and retry."""
    for attempt in range(3):
        response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        if response.status_code == 429 and attempt < 2:
            time.sleep(2 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json()


def _strip_brackets(text):
    """Remove (...) and [...] including nested ones, e.g. pronunciation in Wikipedia intros."""
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\s*[\(\[][^()\[\]]*[\)\]]", "", text)
    return text.strip()


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _pageviews(titles):
    """Wikipedia page views over the last 30 days for up to 50 titles -> {title: views}."""
    data = _get(WIKIPEDIA_URL, {
        "action": "query", "prop": "pageviews", "pvipdays": 30,
        "titles": "|".join(titles), "format": "json",
    })
    result = {}
    for page in data.get("query", {}).get("pages", {}).values():
        views = page.get("pageviews") or {}
        result[page["title"]] = sum(v for v in views.values() if v)
    return result


def _extracts(titles):
    """Short intro text for up to 20 titles -> {title: text}."""
    data = _get(WIKIPEDIA_URL, {
        "action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
        "exsentences": 2, "exlimit": "max", "titles": "|".join(titles), "format": "json",
    })
    return {p["title"]: p.get("extract", "") for p in data.get("query", {}).get("pages", {}).values()}


@lru_cache(maxsize=32)
def _popular_places(city, lat, lon):
    """Most popular Wikipedia pages near the coordinates, most popular first.

    Makes ~15 requests, so the result is cached per city. Errors are not cached.
    """
    # 1) all Wikipedia pages with coordinates within 10 km of the city center
    nearby = _get(WIKIPEDIA_URL, {
        "action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}",
        "gsradius": 10000, "gslimit": 500, "format": "json",
    })["query"]["geosearch"]
    titles = [p["title"] for p in nearby]

    # 2) rank them by popularity: landmarks have far more page views than random
    #    buildings, streets or offices. Requests go one by one, politely.
    views = {}
    for part in _chunks(titles, 50):
        views.update(_pageviews(part))
        time.sleep(0.1)
    top = sorted(titles, key=lambda t: views.get(t, 0), reverse=True)
    top = [t for t in top if t.lower() != city.lower()][:60]  # skip the city page itself

    # 3) intro text only for the most popular pages
    texts = {}
    for part in _chunks(top, 20):
        texts.update(_extracts(part))
        time.sleep(0.1)

    items = []
    for title in top:
        text = _strip_brackets(texts.get(title, ""))
        if not text:
            continue
        if NOT_ATTRACTIONS_RE.search(text[:150].lower()):
            continue
        items.append({
            "title": title,
            "description": text[:300],
            "link": "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_")),
        })
    return tuple(items)


def find_attractions(place: str, interest: str = "", limit: int = 10) -> dict:
    """Find the most popular landmarks and sights near a city, with short descriptions (from Wikipedia).

    This covers sights, museums, monuments and districts. It does NOT list restaurants
    or shops. Results that mention the user's interest are returned first.

    Args:
        place: Place name, e.g. "Lisbon".
        interest: Optional keyword to prioritise, e.g. "architecture", "museum", "park".
        limit: Maximum number of results (default 10).
    """
    geo = geocode(place)
    if "error" in geo:
        return geo

    try:
        items = list(_popular_places(geo["name"], geo["latitude"], geo["longitude"]))
    except (requests.RequestException, KeyError) as e:
        return {"error": f"Attraction search failed: {e}"}

    if interest:
        keyword = interest.lower()
        # stable sort: matching items go first, popularity order is kept inside each group
        items.sort(key=lambda i: keyword not in (i["title"] + " " + i["description"]).lower())

    if not items:
        return {"error": f"No attractions found near '{place}'."}

    return {"place": f"{geo['name']}, {geo['country']}", "attractions": items[:limit]}


if __name__ == "__main__":
    for item in find_attractions("Lisbon", "", 10).get("attractions", []):
        print("-", item["title"], "|", item["description"][:90])