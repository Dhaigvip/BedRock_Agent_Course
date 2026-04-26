# Agent Prompts — Reference

These are the prompts used inside the agent (`agent/main.py`).
They are seeded at the start of every conversation before the user types anything.

---

## Why seed a system prompt via messages?

The Bedrock Converse API does not have a dedicated `system` parameter on every model.
The standard pattern is to inject the persona as the **first user/assistant message pair**,
which every model in the Converse API understands regardless of provider.

---

## Prompt 1 — System Prompt (user turn)

**Role:** `user`

**Purpose:**
Tells the model who it is, what it knows, and how it should behave.
Loaded once at agent startup. Applies to the entire conversation.

**Text:**
```
You are a helpful AI Travel Concierge.
You help travellers plan trips, find hotels, check weather,
and understand currency exchange rates.
Always use the available tools to fetch real data before answering.
Be concise, friendly, and practical.
```

**Key rules baked in:**

| Rule | Why |
|------|-----|
| "Always use the available tools" | Prevents the model from answering from stale training data |
| "fetch real data before answering" | Enforces the tool-call loop rather than guessing |
| "Be concise, friendly, and practical" | Shapes the tone for a travel assistant use case |

---

## Prompt 2 — System Acknowledgement (assistant turn)

**Role:** `assistant`

**Purpose:**
Pre-seeds the assistant's first reply so the conversation history starts
in a valid `user → assistant` alternating pattern.
Also signals to the LLM that it should proceed directly to using tools
rather than asking clarifying questions.

**Text:**
```
Understood! I'm your Travel Concierge. How can I help you today?
```

---

## How it looks in the message history

```python
history = [
    {
        "role": "user",
        "content": [{"text": "You are a helpful AI Travel Concierge..."}]
    },
    {
        "role": "assistant",
        "content": [{"text": "Understood! I'm your Travel Concierge..."}]
    },
    # ← user questions get appended here
]
```

---

## Bedrock message format rules

- Messages must alternate `user → assistant → user → assistant …`
- Tool results are sent as a `user` turn (Bedrock Converse convention)
- There is no separate `system` role in the Converse API message list —
  use the first `user` message for persona/instructions instead
