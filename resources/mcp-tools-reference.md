# MCP Server — Tools Reference

All tools are registered in `mcp-server/server.py` using the `@mcp.tool()` decorator.
The **docstring** of each function becomes the tool description that the LLM reads.

---

## Tool 1 — `get_destinations`

**Description**
> Get all available travel destinations.
> Returns a list of cities with country, description, best travel season, and average daily budget in USD.

**Parameters**
None.

**Example output**
```
Paris, France
  The city of light, famous for the Eiffel Tower, world-class cuisine and art.
  Best season: Apr–Jun | Avg daily budget: $180

Tokyo, Japan
  A dazzling mix of ultra-modern and traditional, with incredible food and transport.
  Best season: Mar–May | Avg daily budget: $120

New York, USA
  The city that never sleeps — iconic skyline, Broadway, and endless neighbourhoods.
  Best season: Sep–Nov | Avg daily budget: $200
```

---

## Tool 2 — `get_weather`

**Description**
> Get the current weather for a travel destination city.
> Returns temperature, conditions, humidity, and packing advice.

**Parameters**
| Name | Type | Required | Description |
|---|---|---|---|
| `city` | `str` | ✅ | City name, e.g. `Paris`, `Tokyo`, `Bangkok` |

**Example output**
```
Tokyo — Current weather
  Temperature : 22°C
  Condition   : Sunny
  Humidity    : 60%
  Advice      : Great weather — perfect for sightseeing.
```

**Error case**
```
No weather data available for 'Atlantis'.
```

---

## Tool 3 — `search_hotels`

**Description**
> Search for hotels in a city, optionally filtered by maximum price per night.
> Returns hotel name, type (budget / mid-range / luxury), price, and rating.

**Parameters**
| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `city` | `str` | ✅ | — | City name, e.g. `Paris`, `Tokyo`, `Dubai` |
| `max_price_per_night` | `int` | ❌ | `10000` | Maximum price in USD per night |

**Example output**
```
Hotels in Paris (max $200/night):

  Hotel Lumière
    Type   : budget
    Price  : $89/night
    Rating : 4.1/5.0

  Le Marais Boutique
    Type   : mid-range
    Price  : $175/night
    Rating : 4.5/5.0
```

**Error case**
```
No hotels found in 'Paris' under $30/night.
```

---

## Tool 4 — `get_currency_rate`

**Description**
> Get the exchange rate between two currencies.
> Useful for helping travellers understand local costs.

**Parameters**
| Name | Type | Required | Description |
|---|---|---|---|
| `from_currency` | `str` | ✅ | Source currency code, e.g. `USD` |
| `to_currency` | `str` | ✅ | Target currency code, e.g. `JPY` |

**Supported currencies**
`USD` · `EUR` · `GBP` · `JPY` · `AUD` · `THB` · `AED`

**Example output**
```
Exchange rate: 1 USD = 149.5 JPY
  Example: 100 USD = 14950.00 JPY
```

**Error case**
```
Currency 'BTC' not supported. Supported: ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'THB', 'AED']
```

---

## Best Practices (from V3.5)

| Rule | Why |
|---|---|
| **Docstring is the description** | The LLM reads the docstring to decide when and how to call the tool — write it for the model, not for humans |
| **Explicit typed parameters** | Typed params generate a JSON schema automatically — the model knows exactly what to pass |
| **Return plain text** | LLMs process text; avoid returning dicts or lists directly |
| **Never raise exceptions** | Catch errors and return a descriptive string — a crash in a tool crashes the agent turn |
| **Single responsibility** | One tool = one thing; a tool that does too much confuses the model's routing logic |
