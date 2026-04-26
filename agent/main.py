"""
Travel Concierge Agent — entry point.

Usage:
    uv run python main.py

The agent runs an interactive REPL.  Type a travel question and press Enter.
Type 'quit' or 'exit' to stop.
"""

from graph import agent
from state import AgentState

# ── System prompt ─────────────────────────────────────────────────────────────
# Injected as the first "user" turn so every conversation has the same persona.

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


def run():
    print("=" * 60)
    print("  Travel Concierge Agent")
    print("  Type 'quit' to exit")
    print("=" * 60)

    # Seed the conversation with the system persona exchange
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

        # Build the new user message and add it to history
        user_message = {"role": "user", "content": [{"text": user_input}]}
        history.append(user_message)

        # Run the graph; it returns the full updated state
        initial_state: AgentState = {"messages": history, "model_id": ""}
        final_state = agent.invoke(initial_state)

        # Extract and print the last assistant reply
        messages = final_state["messages"]
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                text = " ".join(
                    block["text"]
                    for block in msg.get("content", [])
                    if "text" in block
                )
                if text:
                    print(f"\nAgent: {text}")
                    break

        # Keep the full updated history for the next turn
        history = final_state["messages"]


if __name__ == "__main__":
    run()
