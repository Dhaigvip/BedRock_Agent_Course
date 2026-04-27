"""
Travel Concierge — FastAPI WebSocket streaming server.

Run:
    uv run uvicorn api:app --host 0.0.0.0 --port 8100 --reload

WebSocket endpoint:  ws://localhost:8100/ws/chat

──────────────────────────────────────────────────────────────────────────────
Message Protocol
──────────────────────────────────────────────────────────────────────────────
Client  -> Server  (JSON text frame):
    { "message": "What's the weather in Tokyo?", "user_id": "alice" }

Server  -> Client  (stream of JSON text frames):
    { "type": "token",       "text":   "Tokyo is..."   }  # streamed word-by-word
    { "type": "tool_call",   "name":   "get_weather",
                             "input":  { "city": "Tokyo" } }
    { "type": "tool_result", "name":   "get_weather",
                             "result": "22°C, sunny..." }
    { "type": "done"                                    }  # turn complete
    { "type": "error",       "message": "..." }            # on failure

Multiple messages can be sent on the same WebSocket connection — each is an
independent agent turn sharing the same LangGraph thread (session memory).
"""

import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph import build_graph
from mcp_client import MCPClient
from memory import load_facts
from bedrock import call_bedrock, call_bedrock_stream, MODELS
from prompts import build_system_prompt, SYSTEM_ACK, build_classifier_prompt

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Travel Concierge Agent API")

# Allow the Vite dev server (port 5173) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID") or None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _classify(user_text: str) -> str:
    """
    Quick one-shot call to Nova Micro to classify the question complexity.
    Returns the Bedrock model ID to use for the main response.
    """
    response = call_bedrock(
        messages=[build_classifier_prompt(user_text)],
        model_id=MODELS["simple"],
    )
    label = response["content"][0]["text"].strip().lower()
    model_id = MODELS["complex"] if label == "complex" else MODELS["simple"]
    print(f"[classify] '{user_text[:50]}' -> {label} -> {model_id.split('/')[-1]}")
    return model_id


# ── Streaming turn ────────────────────────────────────────────────────────────

async def _stream_turn(
    ws:       WebSocket,
    agent,
    mcp:      MCPClient,
    tools:    list[dict],
    user_msg: dict,
    model_id: str,
    config:   dict,
) -> None:
    """
    Run one conversational turn, streaming tokens back over the WebSocket.

    Flow:
      1. Append the user message to the LangGraph thread state.
      2. Enter a streaming loop:
           a. Call converse_stream with full history.
           b. Forward each text token to the client immediately.
           c. Accumulate any tool-use blocks.
      3. If tool calls were requested:
           a. Execute each tool via MCP.
           b. Notify the client ("tool_call" / "tool_result" events).
           c. Append results to state and loop back to step 2.
      4. Send "done" when the LLM produces a final text response.

    State persistence:
      Every assistant message and tool-result message is appended to the
      LangGraph checkpointer so the next turn picks up the full history.
    """

    # 1. Append user message ─────────────────────────────────────────────────
    await agent.aupdate_state(config, {"messages": [user_msg], "tools": tools}, as_node="__start__")

    # ── Main streaming loop (repeats when the LLM calls tools) ───────────────
    while True:

        # Fetch full history for the Bedrock call
        state   = await agent.aget_state(config)
        history = state.values["messages"]

        # Accumulators for the current assistant turn
        text_buffer     = ""
        tool_uses       = []          # completed tool calls
        current_tool    = None        # tool call being assembled
        tool_input_buf  = []          # raw JSON fragments for current tool

        # 2. Stream from Bedrock ───────────────────────────────────────────────
        for event_type, data in call_bedrock_stream(
            history, tools, model_id, GUARDRAIL_ID
        ):
            if event_type == "token":
                text_buffer += data
                await ws.send_json({"type": "token", "text": data})

            elif event_type == "tool_start":
                current_tool   = data          # {"toolUseId": ..., "name": ...}
                tool_input_buf = []

            elif event_type == "tool_input":
                tool_input_buf.append(data)

            elif event_type == "tool_end":
                if current_tool:
                    raw = "".join(tool_input_buf)
                    try:
                        current_tool["input"] = json.loads(raw) if raw else {}
                    except json.JSONDecodeError:
                        current_tool["input"] = {}
                    tool_uses.append(current_tool)
                    current_tool   = None
                    tool_input_buf = []

            # "stop" event is just informational — we detect end-of-turn by
            # whether there are accumulated tool_uses.

        # 3. Persist assistant message ─────────────────────────────────────────
        content: list[dict] = []
        if text_buffer:
            content.append({"text": text_buffer})
        for tu in tool_uses:
            content.append({"toolUse": tu})

        assistant_msg = {"role": "assistant", "content": content}
        await agent.aupdate_state(config, {"messages": [assistant_msg]}, as_node="llm")

        # If no tool calls were made this turn, we're done
        if not tool_uses:
            break

        # 4. Execute tool calls ────────────────────────────────────────────────
        tool_results: list[dict] = []

        for tu in tool_uses:
            await ws.send_json({
                "type":  "tool_call",
                "name":  tu["name"],
                "input": tu["input"],
            })

            result_text = await mcp.call_tool(tu["name"], tu["input"])

            await ws.send_json({
                "type":   "tool_result",
                "name":   tu["name"],
                "result": result_text[:400],      # preview for the UI
            })

            tool_results.append({
                "toolResult": {
                    "toolUseId": tu["toolUseId"],
                    "content":   [{"text": result_text}],
                }
            })

        # Append tool results and loop for the next LLM call
        tool_msg = {"role": "user", "content": tool_results}
        await agent.aupdate_state(config, {"messages": [tool_msg]}, as_node="tool")

    await ws.send_json({"type": "done"})


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    """
    Single persistent WebSocket connection per browser tab.

    The client can send multiple messages on the same connection; each becomes
    an independent agent turn in the same LangGraph thread.
    """
    await websocket.accept()

    async with AsyncSqliteSaver.from_conn_string("memory.db") as checkpointer:
        agent = build_graph(checkpointer=checkpointer)

        async with MCPClient.connect() as mcp:
            tools = await mcp.list_tools()

            try:
                while True:
                    # Wait for next message from the client
                    raw  = await websocket.receive_text()
                    data = json.loads(raw)

                    user_text = data.get("message", "").strip()
                    user_id   = data.get("user_id", "default")

                    if not user_text:
                        continue

                    config = {
                        "configurable": {
                            "thread_id":  user_id,
                            "mcp_client": mcp,
                        }
                    }

                    # Seed system prompt only on brand-new threads
                    existing = await agent.aget_state(config)
                    if not existing.values:
                        user_facts = load_facts(user_id)
                        if user_facts:
                            print(f"[memory] facts loaded for '{user_id}'")
                        await agent.aupdate_state(config, {
                            "messages": [build_system_prompt(user_facts), SYSTEM_ACK],
                            "model_id": "",
                            "tools":    tools,
                        }, as_node="__start__")

                    # Classify once per user message
                    model_id = _classify(user_text)
                    user_msg = {"role": "user", "content": [{"text": user_text}]}

                    try:
                        await _stream_turn(
                            ws=websocket,
                            agent=agent,
                            mcp=mcp,
                            tools=tools,
                            user_msg=user_msg,
                            model_id=model_id,
                            config=config,
                        )
                    except Exception as exc:
                        print(f"[api] stream error: {exc}")
                        await websocket.send_json({"type": "error", "message": str(exc)})

            except WebSocketDisconnect:
                print("[api] client disconnected")
