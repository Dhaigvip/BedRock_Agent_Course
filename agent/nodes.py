from state import AgentState
from bedrock import call_bedrock, MODELS

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
# Calls Bedrock with the full conversation history.
# No tools yet — tools are added in Section 6 via MCP integration.
# The model answers directly from its training knowledge.

def llm_node(state: AgentState) -> dict:
    print(f"[llm] calling {state['model_id']} ({len(state['messages'])} messages in history)")

    response = call_bedrock(
        messages=state["messages"],
        model_id=state["model_id"],
    )

    content = response.get("content", [])
    text_preview = next((b["text"][:80] for b in content if "text" in b), "")
    print(f"[llm] answer: {text_preview!r}")

    # Append the assistant message to conversation history
    return {"messages": [response]}
