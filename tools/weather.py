"""Tool: get_weather. Daily forecast from Open-Meteo."""

from datetime import date, timedelta

import requests

from .common import get_json, parse_date
from .geocoding import geocode

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_AHEAD_DAYS = 15 

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Heavy freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light rain showers", 81: "Rain showers", 82: "Violent rain showers",
    85: "Light snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}

def get_weather(place: str, start_date: str, end_date: str) -> dict:
    start, end = parse_date(start_date), parse_date(end_date)
    if not start or not end:
        return {"error": "Dates must be in YYYY-MM-DD format."}
    if end < start:
        return {"error": "end_date is earlier than start_date."}

    today = date.today()
    last_available = today + timedelta(days=FORECAST_AHEAD_DAYS)

    if end < today:
        return {"error": "These dates are in the past."}
    if start > last_available:
        return {
            "available": False,
            "note": f"A forecast is only available until {last_available}. "
                    "Use typical seasonal weather for these dates and say it is not a forecast.",
        }

    geo = geocode(place)
    if "error" in geo:
        return geo

    note = ""
    real_start, real_end = max(start, today), min(end, last_available)
    if (real_start, real_end) != (start, end):
        note = (f"Forecast covers only {real_start} to {real_end}; "
                "for the other days use typical seasonal weather.")

    try:
        data = get_json(FORECAST_URL, {
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "start_date": real_start.isoformat(),
            "end_date": real_end.isoformat(),
            "timezone": "auto",
        })
    except requests.RequestException as e:
        return {"error": f"Weather request failed: {e}"}

    daily = data["daily"]
    days = []
    for i, day in enumerate(daily["time"]):
        days.append({
            "date": day,
            "summary": WEATHER_CODES.get(daily["weathercode"][i], "Unknown"),
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "precipitation_mm": daily["precipitation_sum"][i],
        })

    return {"place": f"{geo['name']}, {geo['country']}", "days": days, "note": note}