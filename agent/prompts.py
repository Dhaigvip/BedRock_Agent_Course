"""
Agent prompts — single source of truth.

All LLM prompt strings live here so they are easy to find, tweak, and
share with students as a reference resource.

Import usage:
    from prompts import build_system_prompt, SYSTEM_ACK
    from prompts import build_classifier_prompt
    from prompts import build_memory_prompt
"""

# ── Prompt 1 — Travel Concierge persona ──────────────────────────────────────
#
# Injected as the very first user turn at session start.
# Sets the model's identity, scope, and behaviour for the whole conversation.
# Long-term facts (if any) are appended so returning users feel remembered.

_SYSTEM_PROMPT_BASE = (
    "You are a helpful AI Travel Concierge. "
    "You help travellers plan trips, find hotels, check weather, "
    "and understand currency exchange rates. "
    "Always use the available tools to fetch real data before answering. "
    "Be concise, friendly, and practical."
)


def build_system_prompt(user_facts: str = "") -> dict:
    """
    Return the system prompt as a Bedrock user-turn message dict.

    If long-term facts exist for this user they are appended so the model
    can personalise answers from the very first message.

    Returns:
        {"role": "user", "content": [{"text": "..."}]}
    """
    text = _SYSTEM_PROMPT_BASE
    if user_facts:
        text += (
            f"\n\nWhat you already know about this user:\n{user_facts}\n"
            "Use this to personalise your answers where relevant."
        )
    return {"role": "user", "content": [{"text": text}]}


# ── Prompt 2 — System acknowledgement ────────────────────────────────────────
#
# Pre-seeds the assistant's first reply so the conversation history starts in
# a valid user -> assistant alternating pattern.
# Signals to the LLM that it should move straight to helping, not ask
# clarifying questions about its own role.

SYSTEM_ACK: dict = {
    "role": "assistant",
    "content": [{"text": "Understood! I'm your Travel Concierge. How can I help you today?"}],
}


# ── Prompt 3 — Question classifier ───────────────────────────────────────────
#
# Used by classify_node (nodes.py) and the WebSocket API (api.py).
# Nova Micro answers with a single word so the agent can route to the right
# model: simple -> Nova Micro (cheap), complex -> Nova Lite (smarter).

def build_classifier_prompt(user_text: str) -> dict:
    """
    Return a one-shot classification prompt as a Bedrock user-turn message.

    The model must reply with exactly one word: "simple" or "complex".

    Simple:  single fact lookup — weather, currency rate, hotel search.
    Complex: multi-step planning, itinerary building, comparisons.

    Returns:
        {"role": "user", "content": [{"text": "..."}]}
    """
    text = (
        "Classify this travel question as either 'simple' or 'complex'.\n"
        "Simple: single fact lookup, one-step answer (e.g. weather, currency rate).\n"
        "Complex: multi-step planning, comparisons, itinerary building.\n"
        "Reply with ONE word only: simple or complex.\n\n"
        f"Question: {user_text}"
    )
    return {"role": "user", "content": [{"text": text}]}


# ── Prompt 4 — Memory extraction ─────────────────────────────────────────────
#
# Called at session end (when the user types 'quit' in the CLI, or disconnects
# from the WebSocket).  Nova Micro reads the last 20 turns and distils durable
# user preferences into a short bullet list, merging with any existing facts.

def build_memory_prompt(existing_facts: str, conversation_text: str) -> dict:
    """
    Return a memory-extraction prompt as a Bedrock user-turn message.

    The model should output ONLY a bullet-point list — no preamble, no labels.
    The list is stored verbatim in the user_facts SQLite table and injected
    into the system prompt on the next session.

    Args:
        existing_facts:    Previously stored facts string (may be empty).
        conversation_text: Last N turns formatted as "USER: ...\nASSISTANT: ..."

    Returns:
        {"role": "user", "content": [{"text": "..."}]}
    """
    text = (
        "You are a memory extractor for a travel assistant.\n"
        "Read the conversation below and extract any facts about the USER that "
        "are worth remembering for future sessions.\n"
        "Focus on: travel preferences, budget range, home city, favourite "
        "destinations, dietary needs, travel style (budget/luxury/backpacker).\n"
        "Ignore one-off questions. Only keep durable preferences.\n\n"
        f"EXISTING FACTS:\n{existing_facts or '(none yet)'}\n\n"
        f"CONVERSATION:\n{conversation_text}\n\n"
        "Output ONLY a short bullet-point list of facts to remember. "
        "Merge with existing facts — do not duplicate. "
        "If nothing new is worth remembering, return the existing facts unchanged. "
        "Max 10 bullets."
    )
    return {"role": "user", "content": [{"text": text}]}
