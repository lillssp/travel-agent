"""Quick manual check of every tool."""

import json
from datetime import date, timedelta

import tools


def show(title, result):
    print(f"\n=== {title} ===")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:1800])  


today = date.today()
start = (today + timedelta(days=1)).isoformat()
end = (today + timedelta(days=4)).isoformat()

# ---- geocode ----
show("geocode('Lisbon')", tools.geocode("Lisbon"))
show("geocode('Lviv, Ukraine')", tools.geocode("Lviv, Ukraine"))
show("geocode('asdfghjkl')  -> should be an error", tools.geocode("asdfghjkl"))

# ---- weather ----
show(f"get_weather('Lisbon', {start}, {end})", tools.get_weather("Lisbon", start, end))
show("get_weather far in the future -> should say not available",
     tools.get_weather("Lisbon", "2027-07-01", "2027-07-05"))

# ---- currency ----
show("convert_currency(100, EUR, USD)", tools.convert_currency(100, "EUR", "USD"))
show("convert_currency(100, EUR, UAH)", tools.convert_currency(100, "EUR", "UAH"))
show("convert_currency(5000, UAH, EUR)", tools.convert_currency(5000, "UAH", "EUR"))

# ---- find_place ----
place = tools.find_place("Jerónimos Monastery", "Lisbon")
show("find_place('Jerónimos Monastery', 'Lisbon')  -> real place", place)
show("find_place('Belém Tower', 'Lisbon')  -> real place", tools.find_place("Belém Tower", "Lisbon"))
show("find_place('Blorptastic Tower of Dreams', 'Lisbon')  -> invented, should be found=false or a warning",
     tools.find_place("Blorptastic Tower of Dreams", "Lisbon"))
show("find_place('Pena Palace', 'Lisbon')  -> wrong city, should be found=false",
     tools.find_place("Pena Palace", "Lisbon"))
show("find_place('Pena Palace', 'Sintra')  -> right city, should be found",
     tools.find_place("Pena Palace", "Sintra"))
show("find_place('Museu Nacional do Azulejo', 'Lisbon')  -> geocoder gives another museum, should be found=false",
     tools.find_place("Museu Nacional do Azulejo", "Lisbon"))
show("find_place('National Tile Museum', 'Lisbon')  -> should be found",
     tools.find_place("National Tile Museum", "Lisbon"))
show("find_place('Santa Justa Elevator', 'Lisbon')  -> should be found (Santa Justa Lift)",
     tools.find_place("Santa Justa Elevator", "Lisbon"))

# ---- find_food_nearby ----
if place.get("found"):
    lat, lon = place["latitude"], place["longitude"]
    show("find_food_nearby(restaurant)", tools.find_food_nearby(lat, lon, "restaurant", 700, 5))
    show("find_food_nearby(cafe)", tools.find_food_nearby(lat, lon, "cafe", 700, 5))
    show("find_food_nearby(kind='sushi') -> should be an error", tools.find_food_nearby(lat, lon, "sushi"))

# ---- budget ----
show("calculate_budget", tools.calculate_budget(
    [{"category": "food", "cost": 30}, {"category": "sightseeing", "cost": 12.5},
     {"category": "transport", "cost": 20}],
    total_budget=100,
))

# ---- save_trip ----
show("save_trip", tools.save_trip({
    "title": "Lisbon test trip",
    "country": "Portugal",
    "city": "Lisbon",
    "description": "Test plan",
    "currency": "EUR",
    "start_date": start,
    "end_date": end,
    "total_budget": 500,
    "places": [
        {"category": "sightseeing", "title": "Jerónimos Monastery", "address": place.get("address", ""),
         "visit_date": start, "visit_time": "10:00", "cost": 12},
        {"category": "food", "title": "Pasteis de nata tasting", "visit_date": start,
         "visit_time": "13:00", "cost": 5},
    ],
}))