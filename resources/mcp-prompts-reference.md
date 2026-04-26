# MCP Server — Prompts Reference

Prompts are registered in `mcp-server/server.py` using the `@mcp.prompt()` decorator.
They return pre-built message lists that **prime the conversation** before the user types anything.

---

## Prompts vs Tools

| | Tool | Prompt |
|---|---|---|
| **When used** | Mid-conversation, by the agent, to fetch data | At conversation start, by the host, to set context |
| **Who calls it** | The LLM (automatically, based on need) | The host application (explicitly, before first message) |
| **Returns** | Data / action result | A list of pre-built messages |
| **Purpose** | Do something | Prime the model with context |

---

## Prompt 1 — `trip_planner_prompt`

**Description**
> A reusable prompt template for planning a complete trip.
> Primes the model with traveller context before the conversation starts.

**Parameters**
| Name | Type | Required | Description |
|---|---|---|---|
| `destination` | `str` | ✅ | City to travel to, e.g. `Tokyo` |
| `budget_usd` | `int` | ✅ | Total trip budget in USD |
| `duration_days` | `int` | ✅ | Length of the trip in days |

**Messages returned**

*[user]*
```
I am planning a 7-day trip to Tokyo with a total budget of $3000 USD.

Please help me with the following:
1. Best areas to stay within my budget
2. Must-see attractions and estimated costs
3. Daily budget breakdown (accommodation, food, transport, activities)
4. Any travel tips or warnings I should know about

Use the available tools to check current hotel prices and weather.
```

*[assistant]*
```
I'd be happy to help plan your 7-day trip to Tokyo!
Let me look up the latest hotel options and weather for you.
```

**Why the assistant message?**
Pre-seeding an assistant reply signals to the LLM that it should immediately start using tools (search hotels, check weather) rather than asking clarifying questions first.

---

## Prompt 2 — `budget_breakdown_prompt`

**Description**
> A prompt template that asks for a detailed daily budget breakdown.

**Parameters**
| Name | Type | Required | Description |
|---|---|---|---|
| `destination` | `str` | ✅ | City to travel to |
| `total_budget_usd` | `int` | ✅ | Total available budget in USD |
| `duration_days` | `int` | ✅ | Number of days travelling |

**Messages returned** *(example: Paris, $2000, 5 days → $400/day)*

*[user]*
```
My total budget for Paris is $2000 USD over 5 days ($400/day).

Please give me a realistic daily budget breakdown showing how to
allocate the $400/day across:
- Accommodation
- Food & drinks
- Local transport
- Activities & entrance fees
- Miscellaneous / buffer

Flag if the budget is too tight and suggest adjustments.
```

**Note:** The per-day amount (`$400`) is calculated automatically from `total_budget_usd ÷ duration_days`.

---

## How to Test Prompts in MCP Inspector

1. Start the Travel API: `cd travel-api && uv run python main.py`
2. Launch Inspector: `cd mcp-server && uv run mcp dev server.py`
3. Open **http://localhost:6274** in your browser
4. Click the **Prompts** tab
5. Select a prompt, fill in the arguments, click **Get Prompt**
6. Inspect the rendered messages — this is exactly what the LLM will receive
