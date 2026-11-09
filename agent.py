import getpass
import os
from datetime import date

from dotenv import load_dotenv
from google import genai
from google.genai import types

import tools

load_dotenv()

MODELS = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]
RETRY_ERRORS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND")

MAX_STEPS = 15 

TOOLS = {
    "geocode": tools.geocode,
    "get_weather": tools.get_weather,
    "convert_currency": tools.convert_currency,
    "find_place": tools.find_place,
    "find_food_nearby": tools.find_food_nearby,
    "calculate_budget": tools.calculate_budget,
    "save_trip": tools.save_trip,
}

CATEGORY_ENUM = list(tools.CATEGORIES)

DECLARATIONS = [
    {
        "name": "geocode",
        "description": "Find coordinates, country and timezone of a city, town or region.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "place": {"type": "STRING", "description": "Place name, e.g. 'Lisbon' or 'Lisbon, Portugal'."},
            },
            "required": ["place"],
        },
    },
    {
        "name": "get_weather",
        "description": (
            "Daily weather forecast (temperature, rain) for a place and dates. Only available for "
            "roughly the next 15 days; for later dates the tool says so and you must describe "
            "typical seasonal weather instead, clearly saying it is not a forecast."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "place": {"type": "STRING", "description": "City name, e.g. 'Lisbon'."},
                "start_date": {"type": "STRING", "description": "First day, YYYY-MM-DD."},
                "end_date": {"type": "STRING", "description": "Last day, YYYY-MM-DD."},
            },
            "required": ["place", "start_date", "end_date"],
        },
    },
    {
        "name": "convert_currency",
        "description": "Convert money between currencies at the current exchange rate.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "amount": {"type": "NUMBER"},
                "from_currency": {"type": "STRING", "description": "ISO code, e.g. 'EUR'."},
                "to_currency": {"type": "STRING", "description": "ISO code, e.g. 'USD' or 'UAH'."},
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
    },
    {
        "name": "find_place",
        "description": (
            "Check that a sight, museum, restaurant or other place really exists and get its "
            "address and coordinates. Use it for EVERY place before putting it into the plan. "
            "If found=false, the place may not exist or has another name: retry once with the "
            "local or official name, or drop the place. Use a closest_match only if it is clearly "
            "the same place."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Name of the place, e.g. 'Jerónimos Monastery'."},
                "city": {
                    "type": "STRING",
                    "description": "The city or town the place is actually in (e.g. 'Sintra' for the "
                                   "Pena Palace), not necessarily the city the user stays in.",
                },
            },
            "required": ["name", "city"],
        },
    },
    {
        "name": "find_food_nearby",
        "description": (
            "Find REAL restaurants, cafes, bars or fast food near a point, e.g. near a sight in the "
            "plan. Take the coordinates from find_place. Recommend only places returned by this tool."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "latitude": {"type": "NUMBER"},
                "longitude": {"type": "NUMBER"},
                "kind": {"type": "STRING", "enum": list(tools.FOOD_KINDS)},
                "radius_m": {"type": "INTEGER", "description": "Search radius in meters, default 700."},
                "limit": {"type": "INTEGER", "description": "Max results, default 6."},
            },
            "required": ["latitude", "longitude"],
        },
    },
    {
        "name": "calculate_budget",
        "description": "Sum up the planned costs by category and compare with the total budget.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "items": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "category": {"type": "STRING", "enum": CATEGORY_ENUM},
                            "cost": {"type": "NUMBER"},
                        },
                        "required": ["category", "cost"],
                    },
                },
                "total_budget": {"type": "NUMBER", "description": "The user's total budget, 0 if unknown."},
            },
            "required": ["items"],
        },
    },
    {
        "name": "save_trip",
        "description": (
            "Save the finished trip plan to a file. Call it only after the user agreed to save the plan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "trip": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING"},
                        "country": {"type": "STRING"},
                        "city": {"type": "STRING"},
                        "description": {"type": "STRING"},
                        "currency": {"type": "STRING", "description": "ISO code used for all costs, e.g. 'EUR'."},
                        "start_date": {"type": "STRING", "description": "YYYY-MM-DD"},
                        "end_date": {"type": "STRING", "description": "YYYY-MM-DD"},
                        "total_budget": {"type": "NUMBER"},
                        "places": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "category": {"type": "STRING", "enum": CATEGORY_ENUM},
                                    "title": {"type": "STRING"},
                                    "description": {"type": "STRING"},
                                    "address": {"type": "STRING", "description": "From find_place."},
                                    "link": {"type": "STRING"},
                                    "notes": {"type": "STRING"},
                                    "visit_date": {"type": "STRING", "description": "YYYY-MM-DD"},
                                    "visit_time": {"type": "STRING", "description": "HH:MM"},
                                    "cost": {"type": "NUMBER", "description": "Estimated cost in the trip currency."},
                                },
                                "required": ["category", "title"],
                            },
                        },
                    },
                    "required": ["title", "start_date", "end_date"],
                },
            },
            "required": ["trip"],
        },
    },
]


def build_system_prompt():
    return f"""You are a friendly, practical travel planning assistant. Today is {date.today().isoformat()}.
        You turn a traveler's wishes into a concrete day-by-day plan with a budget, using your tools.

        GATHERING INFORMATION
        - You need: destination, travel dates (or start date and number of days), total budget with its
        currency, and interests. Ask short questions for what is missing (several at once), but do not
        interrogate: if the user gave enough, start planning right away.

        HOW TO PLAN
        1. Check the weather for the dates with get_weather. If there is no forecast for those dates, say so
        and describe the typical weather for that season instead. Never invent a forecast.
        2. Pick sights, museums and activities that fit the interests, using your own knowledge. Group places
        that are close to each other on the same day, and do not overload a day: about 2-3 main activities
        plus meals. On rainy or stormy days prefer indoor activities (museums, churches, covered markets)
        and keep outdoor ones for dry days; suggest an umbrella when rain is expected.
        3. Verify EVERY place with find_place before it goes into the plan (pass the town the place is really
        in). Drop or replace places that cannot be verified. Do not put unverified places into the plan.
        4. For lunch and dinner, call find_food_nearby with the coordinates of the nearby sight and choose
        ONLY from the places it returns. Never invent restaurants or cafes. Mention the cuisine or opening
        hours only if the tool returned them; otherwise describe the place only by its name and type
        (restaurant, cafe), without claims like "famous for" or "traditional".
        5. Prices: you may give rough estimates for tickets, meals and transport, but always mark them as
        approximate (for example "~12 EUR"). Exchange rates must come from convert_currency. Keep all costs
        in one currency, the currency of the user's budget.
        6. Every item that costs money, including local transport (metro, tram, taxi), must appear in the
        plan as its own line, and free activities are listed with cost 0, so that the plan, the budget and
        the saved trip all match. Run calculate_budget on exactly the items shown in the plan and tell the
        user how much is left or over budget.
        7. Call independent tools together in one step instead of one by one.

        ANSWER FORMAT
        - Present the plan by day: date, expected weather, then time, place, short description, estimated
        cost. Add address for each verified place. Finish with the budget summary.
        - Be concise and friendly. Reply in the language the user writes in.
        - After showing the plan, offer to save it. Call save_trip only when the user agrees. Use the
        addresses from find_place, the verified place names, categories from the allowed list, and put
        the budget currency in the currency field. Put every item of the plan into places, also local
        transport (category transport) and free activities (cost 0).
        - If the user asks to change something, adjust the plan and re-verify only new places.
        """


def _generate(client, contents, config):
    last_error = None
    for model in MODELS:
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            last_error = str(e)
            if not any(code in last_error for code in RETRY_ERRORS):
                raise 
    raise RuntimeError(f"All models are busy right now, please try again in a minute. ({last_error})")


def run_agent(client, history, user_message, on_tool_call=None):
    config = types.GenerateContentConfig(
        system_instruction=build_system_prompt(),
        tools=[types.Tool(function_declarations=DECLARATIONS)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    history.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    for _ in range(MAX_STEPS):
        response = _generate(client, history, config)

        if not response.candidates or not response.candidates[0].content:
            return "The model returned an empty response. Please try again."
        history.append(response.candidates[0].content)

        calls = response.function_calls
        if not calls:
            return response.text or "The model returned an empty response. Please try again."

        result_parts = []
        for call in calls:
            args = dict(call.args or {})
            function = TOOLS.get(call.name)
            try:
                result = function(**args) if function else {"error": f"Unknown tool: {call.name}"}
            except Exception as e: 
                result = {"error": f"Tool {call.name} failed: {e}"}

            if on_tool_call:
                on_tool_call(call.name, args, result)

            for_model = {k: v for k, v in result.items() if k != "trip"}
            result_parts.append(types.Part.from_function_response(name=call.name, response=for_model))

        history.append(types.Content(role="user", parts=result_parts))

    return "I got stuck while planning (too many steps). Please try a simpler request."

def main():
    api_key = os.getenv("GEMINI_API_KEY") or getpass.getpass("Gemini API key: ")
    client = genai.Client(api_key=api_key)  
    history = []

    def show_tool(name, args, result):
        print(f"  [tool] {name}({args})")
        print(f"         -> {str(result)[:150]}")

    print("Travel planner. Describe your trip (empty line to quit).\n")
    while True:
        message = input("You: ").strip()
        if not message:
            break
        try:
            print("\nAgent:", run_agent(client, history, message, on_tool_call=show_tool), "\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()