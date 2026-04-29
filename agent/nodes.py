import os
import time
from langgraph.types import RunnableConfig
from state import AgentState
from bedrock import call_bedrock, MODELS
from prompts import build_classifier_prompt
from tracer import log_event, new_execution_id, elapsed_ms

GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID") or None

# ── Node: classify ────────────────────────────────────────────────────────────
# Uses Nova Micro (cheapest model) to decide which model handles the real question.
# Simple questions stay on Nova Micro. Complex ones get routed to Nova Lite.

def classify_node(state: AgentState) -> dict:
    exec_id = new_execution_id()
    t0 = time.time()

    # Extract the text of the latest user message
    last_message = state["messages"][-1]
    user_text = " ".join(
        block["text"]
        for block in last_message.get("content", [])
        if "text" in block
    )

    log_event(exec_id, "classify_start", {"user_text": user_text[:120]})

    response = call_bedrock(
        messages=[build_classifier_prompt(user_text)],
        model_id=MODELS["simple"],   # always use cheapest model for classification
    )

    classification = response["content"][0]["text"].strip().lower()
    model_id = MODELS["complex"] if classification == "complex" else MODELS["simple"]

    log_event(exec_id, "classify_end", {
        "result": classification,
        "model_id": model_id,
        "latency_ms": elapsed_ms(t0),
    })

    print(f"[classifier] '{user_text[:60]}' -> {classification} -> {model_id}")
    return {"model_id": model_id, "execution_id": exec_id}


# ── Node: llm ─────────────────────────────────────────────────────────────────
# Calls Bedrock with the full conversation history.
# Tool specs come from state["tools"] — fetched from MCP at startup,
# so the agent never needs to know what tools exist in advance.

def llm_node(state: AgentState) -> dict:
    exec_id = state.get("execution_id", "unknown")
    t0 = time.time()
    msg_count = len(state["messages"])

    log_event(exec_id, "llm_start", {
        "model_id": state["model_id"],
        "message_count": msg_count,
    })

    print(f"[llm] calling {state['model_id']} ({msg_count} messages in history)")

    response = call_bedrock(
        messages=state["messages"],
        tools=state.get("tools", []),
        model_id=state["model_id"],
        guardrail_id=GUARDRAIL_ID,
    )

    content = response.get("content", [])
    if any("toolUse" in block for block in content):
        tool_names = [b["toolUse"]["name"] for b in content if "toolUse" in b]
        log_event(exec_id, "llm_end", {
            "stop_reason": "tool_use",
            "tool_names": tool_names,
            "latency_ms": elapsed_ms(t0),
        })
        print(f"[llm] tool call(s) requested: {tool_names}")
    else:
        text_preview = next((b["text"][:80] for b in content if "text" in b), "")
        log_event(exec_id, "llm_end", {
            "stop_reason": "end_turn",
            "answer_preview": text_preview,
            "latency_ms": elapsed_ms(t0),
        })
        print(f"[llm] direct answer: {text_preview!r}")

    return {"messages": [response]}


# ── Node: tool ────────────────────────────────────────────────────────────────
# Async node — forwards every toolUse block through MCPClient.
# The MCP server handles the actual Travel API call; this node just relays.
# mcp_client is injected via LangGraph config["configurable"]["mcp_client"].

async def tool_node(state: AgentState, config: RunnableConfig) -> dict:
    mcp = config["configurable"]["mcp_client"]
    exec_id = state.get("execution_id", "unknown")

    last = state["messages"][-1]
    tool_results = []

    for block in last.get("content", []):
        if "toolUse" not in block:
            continue
        tool_use = block["toolUse"]
        name     = tool_use["name"]
        inputs   = tool_use.get("input", {})
        use_id   = tool_use["toolUseId"]

        t0 = time.time()
        log_event(exec_id, "tool_call", {"tool_name": name, "inputs": inputs})

        # Forward through MCP — no Travel API knowledge in the agent
        result_text = await mcp.call_tool(name, inputs)

        log_event(exec_id, "tool_result", {
            "tool_name": name,
            "result_preview": result_text[:120],
            "latency_ms": elapsed_ms(t0),
        })

        tool_results.append({
            "toolResult": {
                "toolUseId": use_id,
                "content":   [{"text": result_text}],
            }
        })

    tool_message = {"role": "user", "content": tool_results}
    return {"messages": [tool_message]}
