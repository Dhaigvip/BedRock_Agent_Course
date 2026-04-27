import os
from langgraph.types import RunnableConfig
from state import AgentState
from bedrock import call_bedrock, MODELS
from prompts import build_classifier_prompt

GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID") or None

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

    response = call_bedrock(
        messages=[build_classifier_prompt(user_text)],
        model_id=MODELS["simple"],   # always use cheapest model for classification
    )

    classification = response["content"][0]["text"].strip().lower()
    model_id = MODELS["complex"] if classification == "complex" else MODELS["simple"]

    print(f"[classifier] '{user_text[:60]}' -> {classification} -> {model_id}")
    return {"model_id": model_id}


# ── Node: llm ─────────────────────────────────────────────────────────────────
# Calls Bedrock with the full conversation history.
# Tool specs come from state["tools"] — fetched from MCP at startup,
# so the agent never needs to know what tools exist in advance.

def llm_node(state: AgentState) -> dict:
    print(f"[llm] calling {state['model_id']} ({len(state['messages'])} messages in history)")

    response = call_bedrock(
        messages=state["messages"],
        tools=state.get("tools", []),
        model_id=state["model_id"],
        guardrail_id=GUARDRAIL_ID,
    )

    content = response.get("content", [])
    if any("toolUse" in block for block in content):
        tool_names = [b["toolUse"]["name"] for b in content if "toolUse" in b]
        print(f"[llm] tool call(s) requested: {tool_names}")
    else:
        text_preview = next((b["text"][:80] for b in content if "text" in b), "")
        print(f"[llm] direct answer: {text_preview!r}")

    return {"messages": [response]}


# ── Node: tool ────────────────────────────────────────────────────────────────
# Async node — forwards every toolUse block through MCPClient.
# The MCP server handles the actual Travel API call; this node just relays.
# mcp_client is injected via LangGraph config["configurable"]["mcp_client"].

async def tool_node(state: AgentState, config: RunnableConfig) -> dict:
    mcp = config["configurable"]["mcp_client"]

    last = state["messages"][-1]
    tool_results = []

    for block in last.get("content", []):
        if "toolUse" not in block:
            continue
        tool_use = block["toolUse"]
        name     = tool_use["name"]
        inputs   = tool_use.get("input", {})
        use_id   = tool_use["toolUseId"]

        # Forward through MCP — no Travel API knowledge in the agent
        result_text = await mcp.call_tool(name, inputs)

        tool_results.append({
            "toolResult": {
                "toolUseId": use_id,
                "content":   [{"text": result_text}],
            }
        })

    tool_message = {"role": "user", "content": tool_results}
    return {"messages": [tool_message]}
