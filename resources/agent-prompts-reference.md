# Agent Prompts — Reference

All prompts used by the Travel Concierge agent live in **`agent/prompts.py`**.
This document explains each one so you can copy-paste and customise during
your coding sessions.

---

## Why a dedicated prompts.py?

Keeping prompts in one file means:
- Easy to find and tweak without hunting through multiple files
- Single source of truth — no accidental duplicates across `main.py` and `api.py`
- Students can open one file to understand all LLM instructions at a glance

---

## Prompt 1 — Travel Concierge persona (system prompt)

**Function:** `build_system_prompt(user_facts="")`  
**Used in:** `main.py`, `api.py` — injected once at session start  
**Role:** `user` (first turn)

```
You are a helpful AI Travel Concierge.
You help travellers plan trips, find hotels, check weather,
and understand currency exchange rates.
Always use the available tools to fetch real data before answering.
Be concise, friendly, and practical.
```

When long-term facts exist for the user, this is appended automatically:

```
What you already know about this user:
• Prefers budget travel
• Home city: London
...
Use this to personalise your answers where relevant.
```

**Key rules baked in:**

| Rule | Why |
|------|-----|
| "Always use the available tools" | Prevents the model answering from stale training data |
| "fetch real data before answering" | Enforces the tool-call loop rather than guessing |
| "Be concise, friendly, and practical" | Shapes the tone for a travel assistant |

---

## Prompt 2 — System acknowledgement

**Constant:** `SYSTEM_ACK`  
**Used in:** `main.py`, `api.py` — injected immediately after Prompt 1  
**Role:** `assistant` (pre-seeded reply)

```
Understood! I'm your Travel Concierge. How can I help you today?
```

**Why it's needed:**  
The Bedrock Converse API expects messages to alternate `user → assistant → user …`.
Pre-seeding the assistant's first reply means the history is in a valid state before
the first real user message arrives.  
It also signals to the model that it should move straight to helping — not ask
clarifying questions about its own role.

---

## Prompt 3 — Question classifier

**Function:** `build_classifier_prompt(user_text)`  
**Used in:** `nodes.py` (classify_node), `api.py` (_classify)  
**Role:** `user`  
**Model:** Nova Micro (cheapest — single-word answer only)

```
Classify this travel question as either 'simple' or 'complex'.
Simple: single fact lookup, one-step answer (e.g. weather, currency rate).
Complex: multi-step planning, comparisons, itinerary building.
Reply with ONE word only: simple or complex.

Question: {user_text}
```

**Routing result:**

| Answer | Model used for main response |
|--------|------------------------------|
| `simple` | Nova Micro (`amazon.nova-micro-v1:0`) |
| `complex` | Nova Lite (`amazon.nova-lite-v1:0`) |

**Examples:**

| Question | Classification |
|----------|----------------|
| "What's the weather in Paris?" | simple |
| "How many Euros is $200?" | simple |
| "Plan a 7-day Italy trip for $2000" | complex |
| "Compare hotels in Tokyo vs Osaka" | complex |

---

## Prompt 4 — Memory extraction

**Function:** `build_memory_prompt(existing_facts, conversation_text)`  
**Used in:** `memory.py` (save_facts) — called at session end  
**Role:** `user`  
**Model:** Nova Micro

```
You are a memory extractor for a travel assistant.
Read the conversation below and extract any facts about the USER that
are worth remembering for future sessions.
Focus on: travel preferences, budget range, home city, favourite
destinations, dietary needs, travel style (budget/luxury/backpacker).
Ignore one-off questions. Only keep durable preferences.

EXISTING FACTS:
{existing_facts or "(none yet)"}

CONVERSATION:
{last 20 turns formatted as USER: ... / ASSISTANT: ...}

Output ONLY a short bullet-point list of facts to remember.
Merge with existing facts — do not duplicate.
If nothing new is worth remembering, return the existing facts unchanged.
Max 10 bullets.
```

**Example output:**

```
• Prefers budget travel (under $100/night hotels)
• Home city: Sydney, Australia
• Favourite destination: Japan
• Vegetarian diet
• Travels solo
```

This output is stored verbatim in the `user_facts` SQLite table and
injected back into Prompt 1 at the start of the user's next session.

---

## How all prompts fit together in a session

```
Session start
  │
  ├─ build_system_prompt(user_facts)   ← Prompt 1  [role: user]
  ├─ SYSTEM_ACK                        ← Prompt 2  [role: assistant]
  │
  │  ← user types their first message
  │
  ├─ build_classifier_prompt(text)     ← Prompt 3  (internal, not shown to user)
  │    └─ returns model_id to route to
  │
  ├─ LLM response (streamed to UI)
  │
  │  ... more turns ...
  │
Session end (quit / disconnect)
  │
  └─ build_memory_prompt(existing, turns)  ← Prompt 4  (internal)
       └─ extracts facts → stored in SQLite → used in next session's Prompt 1
```

---

## Bedrock message format rules

- Messages must alternate `user -> assistant -> user -> assistant …`
- Tool results are sent as a `user` turn (Bedrock Converse convention)
- There is no separate `system` role in the Converse API —
  use the first `user` message for persona/instructions instead
- The `content` field is always a list: `[{"text": "..."}]`
