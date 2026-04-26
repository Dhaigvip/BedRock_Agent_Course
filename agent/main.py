"""
Travel Concierge Agent — entry point.

Usage:
    uv run python main.py

Starts the MCP server once, fetches tools, then runs an interactive REPL.
Type a travel question and press Enter. Type 'quit' or 'exit' to stop.
"""

import asyncio
from graph import agent
from state import AgentState
from mcp_client import MCPClient

# ── System prompt ─────────────────────────────────────────────────────────────
# Seeded as the first two messages of every conversation so the model
# knows its role and immediately starts using tools.
# See resources/agent-prompts-reference.md for the full prompt guide.

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

async def run():
    print("=" * 60)
    print("  Travel Concierge Agent")
    print("  Connecting to MCP server...")

    async with MCPClient.connect() as mcp:
        # Fetch tool specs once from MCP — no hardcoding in the agent
        tools = await mcp.list_tools()

        print("  Type 'quit' to exit")
        print("=" * 60)

        history = [SYSTEM_PROMPT, SYSTEM_ACK]

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

            # Add the new user message
            history.append({"role": "user", "content": [{"text": user_input}]})

            # Run the graph — thread MCPClient through via configurable
            initial_state: AgentState = {
                "messages": history,
                "model_id": "",
                "tools":    tools,
            }
            config = {"configurable": {"mcp_client": mcp}}
            final_state = await agent.ainvoke(initial_state, config=config)

            # Print the last assistant reply
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

            # Carry the full history forward for the next turn
            history = final_state["messages"]


if __name__ == "__main__":
    asyncio.run(run())
