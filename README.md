# ✈️ Travel Planner Agent
 
A chat agent that turns a short description of a trip into a day-by-day plan with weather, verified places, real restaurants nearby and a budget. The LLM decides by itself which tools to call, and uses them instead of making facts up.
 
> Example: *"Plan 3 days in Lisbon starting next Friday, budget 600 EUR, I like history and food, I'm travelling alone."*
 
## What the agent does
 
1. Asks for what is missing (destination, dates, budget and currency, interests).
2. Checks the weather for the dates and adapts the plan (indoor places on rainy days).
3. Picks sights from its own knowledge, then **checks every one of them on the map**.
4. Finds real restaurants and cafes next to the sights (never invents them).
5. Converts currencies, calculates the budget and tells how much is left.
6. After the user agrees, saves the plan as a JSON file.
## Tools
 
| Tool | What it does | Data source |
|---|---|---|
| `geocode` | Coordinates, country and time zone of a city | Open-Meteo Geocoding |
| `get_weather` | Daily forecast for the trip dates (up to 15 days ahead) | Open-Meteo |
| `convert_currency` | Current exchange rate and conversion (UAH via the National Bank of Ukraine) | Frankfurter (ECB), NBU |
| `find_place` | Checks that a place exists in the city, returns address and coordinates | Geoapify Geocoding |
| `find_food_nearby` | Restaurants, cafes, bars or fast food near given coordinates | Geoapify Places |
| `calculate_budget` | Sums the plan by category and compares it with the budget | local |
| `save_trip` | Saves the plan as a JSON file | local |
 
## How it works
 
The agent is a loop around Gemini function calling (`agent.py`):
 
1. The user message is added to the chat history.
2. Gemini answers either with text (done) or with a request to call one or more tools.
3. The tools of one step run in parallel, their results go back to Gemini, and it continues.
**Against hallucinations:** the model suggests places, but each one is verified with `find_place` (a place that is not found, or is too far from the city, is dropped; a different name on the map gives a warning). Restaurants come only from `find_food_nearby`. Weather and exchange rates come only from tools, and prices written by the model are marked as approximate.
 
## Project structure
 
```
agent.py             agent loop, tool declarations, system prompt (also runs in the terminal)
app.py               Streamlit chat interface
test_tools.py        runs every tool without an LLM
tools/
  common.py          shared helpers (HTTP requests, API key, dates, distances)
  geocoding.py  weather.py  currency.py  places.py  food.py  budget.py  trips.py
trips/               saved trips (JSON)
.streamlit/config.toml   theme
```
 
## Run locally
 
1. Get a free Gemini API key in [Google AI Studio](https://aistudio.google.com/apikey) and a free Geoapify key at [geoapify.com](https://www.geoapify.com/).
2. Install and configure:
```
python -m venv venv
venv\Scripts\activate          # Windows; on macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```
 
3. Create a `.env` file in the project folder:
```
GEOAPIFY_KEY=your_geoapify_key
```
 
4. Start the chat:
```
streamlit run app.py
```
 
The Gemini key is entered in the interface (it is never stored). To try the agent in the terminal instead: `python agent.py`. To check the tools without an LLM: `python test_tools.py`.
 
## Notes and limitations
 
- The Gemini key must be your own. Free keys have low limits (the regular Flash models: 5 requests per minute and 20 per day; Flash Lite: 15 per minute and 500 per day). One plan takes several requests, so Flash Lite is used first.
- The weather forecast is available for the next 15 days only; for later dates the agent says so.
- The map data does not know every place under every name, so a real place can occasionally fail the check. The agent then replaces it with another one.
- Prices of tickets and meals are estimates by the model and are labelled as approximate.
## Built with
 
Streamlit, Google Gemini (`google-genai`), Geoapify, Open-Meteo, Frankfurter and the National Bank of Ukraine API.
