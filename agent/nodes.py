import os
import httpx
from state import AgentState
from bedrock import call_bedrock, MODELS

TRAVEL_API = os.getenv("TRAVEL_API_URL", "http://localhost:9000")

# ── Tool config ───────────────────────────────────────────────────────────────
# Bedrock Converse API expects tools in toolSpec format.
# Each spec mirrors the MCP tool exactly: same name, description, and parameters.

TRAVEL_TOOLS = [
    {
        "toolSpec": {
            "name": "get_destinations",
            "description": (
                "Get all available travel destinations. "
                "Returns a list of cities with country, description, "
                "best travel season, and average daily budget in USD."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_weather",
            "description": (
                "Get the current weather for a travel destination city. "
                "Returns temperature, conditions, humidity, and packing advice."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "City name, e.g. 'Paris', 'Tokyo', 'Bangkok'",
                        }
                    },
                    "required": ["city"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "search_hotels",
            "description": (
                "Search for hotels in a city, optionally filtered by maximum price per night. "
                "Returns hotel name, type (budget / mid-range / luxury), price, and rating."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "City name, e.g. 'Paris', 'Tokyo', 'Dubai'",
                        },
                        "max_price_per_night": {
                            "type": "integer",
                            "description": "Maximum price in USD per night (default: no limit)",
                        },
                    },
                    "required": ["city"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_currency_rate",
            "description": (
                "Get the exchange rate between two currencies. "
                "Useful for helping travellers understand local costs. "
                "Supported currencies: USD, EUR, GBP, JPY, AUD, THB, AED."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "from_currency": {
                            "type": "string",
                            "description": "Source currency code, e.g. 'USD'",
                        },
                        "to_currency": {
                            "type": "string",
                            "description": "Target currency code, e.g. 'JPY'",
                        },
                    },
                    "required": ["from_currency", "to_currency"],
                }
            },
        }
    },
]

# ── Node: classify ────────────────────────────────────────────────────────────
# Uses Nova Micro (cheapest model) to decide which model handles the real question.
# Simple questions stay on Nova Micro. Complex ones get routed to Nova Lite.

def classify_node(state: AgentState) -> dict:
    # Extract the text of the latest user message
    last_message = state["messages"][-1]
    user_text = " ".join(
        block["text"]
        for block in last_message.get("content", [])
        if "text" in block
    )

    prompt = (
        "Classify this travel question as either 'simple' or 'complex'.\n"
        "Simple: single fact lookup, one-step answer (e.g. weather, currency rate).\n"
        "Complex: multi-step planning, comparisons, itinerary building.\n"
        "Reply with ONE word only: simple or complex.\n\n"
        f"Question: {user_text}"
    )

    response = call_bedrock(
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        model_id=MODELS["simple"],   # always use cheapest model for classification
    )

    classification = response["content"][0]["text"].strip().lower()
    model_id = MODELS["complex"] if classification == "complex" else MODELS["simple"]

    print(f"[classifier] '{user_text[:60]}' -> {classification} -> {model_id}")
    return {"model_id": model_id}


# ── Node: llm ─────────────────────────────────────────────────────────────────
# Calls Bedrock with the full conversation history and the travel tool config.
# The model decides whether to answer directly or request a tool call.
# Either way, the assistant message is appended to state["messages"].

def llm_node(state: AgentState) -> dict:
    print(f"[llm] calling {state['model_id']} ({len(state['messages'])} messages in history)")

    response = call_bedrock(
        messages=state["messages"],
        tools=TRAVEL_TOOLS,
        model_id=state["model_id"],
    )

    stop_reason = response.get("role", "")  # "assistant"
    # Log what the model decided to do
    content = response.get("content", [])
    if any("toolUse" in block for block in content):
        tool_names = [b["toolUse"]["name"] for b in content if "toolUse" in b]
        print(f"[llm] tool call(s) requested: {tool_names}")
    else:
        text_preview = next((b["text"][:80] for b in content if "text" in b), "")
        print(f"[llm] direct answer: {text_preview!r}")

    # Append the assistant message to conversation history
    return {"messages": [response]}


# ── Node: tool ────────────────────────────────────────────────────────────────
# Executes every toolUse block the LLM returned and builds toolResult messages.
# Returns one "user" message containing all results so the LLM can continue.

def _call_travel_api(name: str, inputs: dict) -> str:
    """Dispatch a single tool call to the Travel API and return plain text."""
    try:
        if name == "get_destinations":
            r = httpx.get(f"{TRAVEL_API}/destinations", timeout=10)
            r.raise_for_status()
            rows = []
            for d in r.json():
                rows.append(
                    f"{d['city']}, {d['country']} | "
                    f"Best season: {d['best_season']} | "
                    f"Avg daily budget: ${d['avg_daily_budget_usd']}"
                )
            return "\n".join(rows)

        elif name == "get_weather":
            city = inputs["city"]
            r = httpx.get(f"{TRAVEL_API}/weather/{city}", timeout=10)
            if r.status_code == 404:
                return f"No weather data for '{city}'."
            r.raise_for_status()
            w = r.json()
            return (
                f"{w['city']} weather: {w['temperature_c']}C, "
                f"{w['condition']}, humidity {w['humidity_percent']}%. "
                f"Advice: {w['advice']}"
            )

        elif name == "search_hotels":
            city = inputs["city"]
            max_price = inputs.get("max_price_per_night", 10000)
            r = httpx.get(f"{TRAVEL_API}/hotels/{city}", params={"max_price": max_price}, timeout=10)
            if r.status_code == 404:
                return f"No hotels found in '{city}' under ${max_price}/night."
            r.raise_for_status()
            rows = []
            for h in r.json():
                rows.append(
                    f"{h['name']} ({h['type']}) — "
                    f"${h['price_per_night_usd']}/night — "
                    f"rating {h['rating']}/5"
                )
            return f"Hotels in {city}:\n" + "\n".join(rows)

        elif name == "get_currency_rate":
            r = httpx.get(
                f"{TRAVEL_API}/currency-rate",
                params={"from_currency": inputs["from_currency"], "to_currency": inputs["to_currency"]},
                timeout=10,
            )
            if r.status_code == 404:
                return r.json().get("detail", "Currency not supported.")
            r.raise_for_status()
            d = r.json()
            return f"1 {d['from_currency']} = {d['rate']} {d['to_currency']}"

        else:
            return f"Unknown tool: {name}"

    except httpx.HTTPError as exc:
        return f"Travel API error: {exc}"


def tool_node(state: AgentState) -> dict:
    # Find the last assistant message — it contains the toolUse requests
    last = state["messages"][-1]
    tool_results = []

    for block in last.get("content", []):
        if "toolUse" not in block:
            continue
        tool_use = block["toolUse"]
        name     = tool_use["name"]
        inputs   = tool_use.get("input", {})
        use_id   = tool_use["toolUseId"]

        print(f"[tool] executing {name}({inputs})")
        result_text = _call_travel_api(name, inputs)
        print(f"[tool] result preview: {result_text[:120]!r}")

        tool_results.append({
            "toolResult": {
                "toolUseId": use_id,
                "content": [{"text": result_text}],
            }
        })

    # Wrap all results in a single "user" turn (Bedrock Converse convention)
    tool_message = {"role": "user", "content": tool_results}
    return {"messages": [tool_message]}
