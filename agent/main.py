"""
Travel Concierge Agent — entry point.

Usage:
    uv run python main.py [--user USER_ID]

Starts the MCP server once, fetches tools, then runs an interactive REPL.
Short-term memory is stored in memory.db (SQLite) keyed by thread_id.
The same user always resumes the same conversation thread.
Type 'quit' or 'exit' to stop.
"""

import asyncio
import argparse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph import build_graph
from state import AgentState
from mcp_client import MCPClient

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = {
    "role": "user",
    "content": [
        {
            "text": (
                "You are a helpful AI Travel Concierge. "
                "You help travellers plan trips, find hotels, check weather, "
                "and understand currency exchange rates. "
                "Always use the available tools to fetch real data before answering. "
                "Be concise, friendly, and practical."
            )
        }
    ],
}

SYSTEM_ACK = {
    "role": "assistant",
    "content": [{"text": "Understood! I'm your Travel Concierge. How can I help you today?"}],
}


# ── REPL ──────────────────────────────────────────────────────────────────────

async def run(thread_id: str):
    print("=" * 60)
    print(f"  Travel Concierge Agent  [session: {thread_id}]")
    print("  Connecting to MCP server...")

    # AsyncSqliteSaver stores the full graph state after every node.
    # Same thread_id = same conversation resumed automatically.
    async with AsyncSqliteSaver.from_conn_string("memory.db") as checkpointer:
        agent = build_graph(checkpointer=checkpointer)

        async with MCPClient.connect() as mcp:
            tools = await mcp.list_tools()

            print("  Type 'quit' to exit")
            print("=" * 60)

            # Config binds this session to a thread — LangGraph restores
            # the full message history from SQLite automatically.
            config = {
                "configurable": {
                    "thread_id":  thread_id,
                    "mcp_client": mcp,
                }
            }

            # Seed the conversation only on the very first turn of a new thread.
            # If the thread already exists in SQLite, the history is restored
            # and we skip the seed to avoid duplicate system messages.
            existing = await agent.aget_state(config)
            is_new_thread = not existing.values

            if is_new_thread:
                seed_state: AgentState = {
                    "messages": [SYSTEM_PROMPT, SYSTEM_ACK],
                    "model_id": "",
                    "tools":    tools,
                }
                await agent.aupdate_state(config, seed_state)

            while True:
                try:
                    user_input = input("\nYou: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye!")
                    break

                if not user_input:
                    continue
                if user_input.lower() in {"quit", "exit"}:
                    print("Goodbye!")
                    break

                # Pass only the new user message — the checkpointer automatically
                # merges it with the full history stored in SQLite.
                turn_state: AgentState = {
                    "messages": [{"role": "user", "content": [{"text": user_input}]}],
                    "model_id": "",
                    "tools":    tools,
                }
                final_state = await agent.ainvoke(turn_state, config=config)

                for msg in reversed(final_state["messages"]):
                    if msg.get("role") == "assistant":
                        text = " ".join(
                            block["text"]
                            for block in msg.get("content", [])
                            if "text" in block
                        )
                        if text:
                            print(f"\nAgent: {text}")
                            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--user", default="default",
        help="User ID — determines which conversation thread to resume (default: 'default')"
    )
    args = parser.parse_args()
    asyncio.run(run(thread_id=args.user))
