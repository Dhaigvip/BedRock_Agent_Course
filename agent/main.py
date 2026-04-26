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

# ── REPL ──────────────────────────────────────────────────────────────────────

async def run():
    print("=" * 60)
    print("  Travel Concierge Agent")
    print("  Connecting to MCP server...")

    async with MCPClient.connect() as mcp:
        # Fetch everything from the MCP server at startup —
        # tool specs, system prompt, and opening ack message.
        # Nothing is hardcoded in the agent.
        tools      = await mcp.list_tools()
        sys_text   = await mcp.read_resource("prompts://system")
        sys_ack    = await mcp.read_resource("prompts://system-ack")

        system_prompt = {"role": "user",      "content": [{"text": sys_text}]}
        system_ack    = {"role": "assistant",  "content": [{"text": sys_ack}]}

        print("  Type 'quit' to exit")
        print("=" * 60)

        history = [system_prompt, system_ack]

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
