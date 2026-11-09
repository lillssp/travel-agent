import json
from datetime import date, timedelta

import streamlit as st
from google import genai

import tools
from agent import run_agent

st.set_page_config(page_title="Travel Planner Agent", page_icon="✈️")

CSS = """
<style>
.stApp {
    background: linear-gradient(135deg, #fde4f2 0%, #ece4fd 100%);
}
[data-testid="stHeader"] { background: transparent; }
h1 { color: #b04a9c !important; text-align: center; }
.subtitle { text-align: center; color: #7a5c99; margin-bottom: 1.5rem; }
button[kind="primary"], button[kind="secondary"] { border-radius: 20px; }
input, textarea { border-radius: 14px !important; }
[data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, 0.65);
    border-radius: 16px;
}
[data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, 0.65);
    border-radius: 16px;
    padding: 1rem 1.5rem 1rem 1rem;
}
</style>
"""


def describe_call(name, args, result):
    """One short line about a tool call, for the 'agent steps' log."""
    if name == "geocode":
        line = f"📍 Looking up {args.get('place')}"
    elif name == "get_weather":
        line = f"🌤️ Weather in {args.get('place')}, {args.get('start_date')} to {args.get('end_date')}"
    elif name == "convert_currency":
        line = f"💱 {args.get('amount')} {args.get('from_currency')} → {args.get('to_currency')}"
    elif name == "find_place":
        if not result.get("found"):
            icon = "❌"
        elif "warning" in result:
            icon = "⚠️"
        else:
            icon = "✅"
        line = f"{icon} Checking place: {args.get('name')} ({args.get('city')})"
    elif name == "find_food_nearby":
        line = f"🍽️ Searching {args.get('kind', 'restaurant')} near a sight: {len(result.get('places', []))} found"
    elif name == "calculate_budget":
        line = "🧮 Calculating the budget"
    elif name == "save_trip":
        line = "💾 Saving the trip"
    else:
        line = f"🔧 {name}"
    if "error" in result:
        line += f" (error: {result['error']})"
    return line


def get_client(api_key):
    """Keep the Gemini client in the session, so that it is not garbage collected and closed."""
    if st.session_state.get("client_key") != api_key:
        st.session_state.client = genai.Client(api_key=api_key)
        st.session_state.client_key = api_key
    return st.session_state.client


if "messages" not in st.session_state:
    st.session_state.messages = []  # what is shown on the screen
    st.session_state.history = []   # what the model sees (messages and tool results)

st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("✈️ Travel Planner")
    if st.button("New chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history = []
        st.rerun()
    st.markdown(
        "**Agent tools**\n"
        "- 📍 geocode: find a city\n"
        "- 🌤️ get_weather: forecast for the dates\n"
        "- 💱 convert_currency: exchange rates\n"
        "- ✅ find_place: check a place exists\n"
        "- 🍽️ find_food_nearby: real restaurants and cafes\n"
        "- 🧮 calculate_budget: costs vs. budget\n"
        "- 💾 save_trip: export the plan as JSON"
    )

# ---------------------------------------------------------------------------
# header
# ---------------------------------------------------------------------------
st.title("✈️ Travel Planner Agent")
st.markdown(
    '<p class="subtitle">Describe your trip and get a day-by-day plan with weather, verified places, '
    "real restaurants nearby and a budget. The agent decides by itself which tools to use "
    "and checks places on the map instead of making them up. Powered by Google Gemini.</p>",
    unsafe_allow_html=True,
)

api_key = st.text_input("🔑 Gemini API key", type="password", placeholder="AIza...")

if not tools.GEOAPIFY_KEY:
    st.warning("GEOAPIFY_KEY is not set: place checking and restaurant search will not work.")

if not st.session_state.messages:
    example_date = (date.today() + timedelta(days=3)).isoformat()
    st.caption(
        f"Try: *Plan 3 days in Lisbon starting {example_date}, budget 400 EUR, "
        "I love food and architecture*"
    )

# ---------------------------------------------------------------------------
# chat history
# ---------------------------------------------------------------------------
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg.get("tool_calls"):
            with st.expander(f"🔧 Agent steps ({len(msg['tool_calls'])})"):
                for line in msg["tool_calls"]:
                    st.markdown(f"- {line}")
        st.markdown(msg["content"])
        if msg.get("trip"):
            st.download_button(
                "⬇️ Download trip (JSON)",
                data=json.dumps(msg["trip"], ensure_ascii=False, indent=2),
                file_name=msg["trip_file"],
                mime="application/json",
                key=f"download_{i}",
            )

# ---------------------------------------------------------------------------
# new message
# ---------------------------------------------------------------------------
prompt = st.chat_input("Describe your trip...")
if prompt:
    if not api_key:
        st.warning("Please enter your Gemini API key above.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status = st.status("Planning...", expanded=True)
        steps = []  # lines for the log
        saved = {}  # the trip, if the agent saved one

        def on_tool_call(name, args, result):
            line = describe_call(name, args, result)
            steps.append(line)
            status.write(line)
            if name == "save_trip" and result.get("saved"):
                saved["trip"] = result["trip"]
                saved["file"] = result["file"]

        history = st.session_state.history
        size_before = len(history)
        try:
            reply = run_agent(get_client(api_key), history, prompt, on_tool_call=on_tool_call)
        except Exception as e:
            del history[size_before:]  # forget the failed turn so that the next one starts clean
            status.update(label="Something went wrong", state="error")
            st.error(f"❌ {e}")
            st.stop()
        status.update(label=f"Done ({len(steps)} steps)", state="complete", expanded=False)

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "tool_calls": steps,
        "trip": saved.get("trip"),
        "trip_file": saved.get("file"),
    })
    st.rerun()