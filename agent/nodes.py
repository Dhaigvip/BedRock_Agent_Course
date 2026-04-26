from state import AgentState
from bedrock import call_bedrock, MODELS

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
