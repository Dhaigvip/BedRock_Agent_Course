"""
Travel Concierge Agent — entry point.

Usage:
    uv run python main.py [--user USER_ID]

Short-term memory:  SQLite checkpointer (memory.db) — full message history
                    per thread_id, restored automatically on resume.
Long-term memory:   user_facts table (memory.db) — distilled preferences
                    injected into system prompt; updated at session end.
"""

import asyncio
import argparse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph import build_graph
from state import AgentState
from mcp_client import MCPClient
from memory import load_facts, save_facts
from prompts import build_system_prompt, SYSTEM_ACK


# ── REPL ──────────────────────────────────────────────────────────────────────

async def run(thread_id: str):
    print("=" * 60)
    print(f"  Travel Concierge Agent  [session: {thread_id}]")
    print("  Connecting to MCP server...")

    async with AsyncSqliteSaver.from_conn_string("memory.db") as checkpointer:
        agent = build_graph(checkpointer=checkpointer)

        async with MCPClient.connect() as mcp:
            tools = await mcp.list_tools()

            # Load long-term facts for this user (empty string on first visit)
            user_facts = load_facts(thread_id)
            if user_facts:
                print(f"  Remembered facts loaded for '{thread_id}'")

            print("  Type 'quit' to exit")
            print("=" * 60)

            config = {
                "configurable": {
                    "thread_id":  thread_id,
                    "mcp_client": mcp,
                }
            }

            # Seed system prompt only on brand-new threads.
            # Returning threads are fully restored by the checkpointer.
            existing = await agent.aget_state(config)
            if not existing.values:
                await agent.aupdate_state(config, {
                    "messages": [build_system_prompt(user_facts), SYSTEM_ACK],
                    "model_id": "",
                    "tools":    tools,
                })

            final_state = None
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

                # Pass only the new user message — checkpointer merges it
                # with the full stored history transparently.
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

            # At session end: extract useful facts and persist for next session
            if final_state:
                save_facts(thread_id, final_state["messages"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--user", default="default",
        help="User ID — determines which conversation thread to resume (default: 'default')"
    )
    args = parser.parse_args()
    asyncio.run(run(thread_id=args.user))
