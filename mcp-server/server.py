import os
import httpx
from mcp.server.fastmcp import FastMCP

# ── Server ────────────────────────────────────────────────────────────────────

mcp = FastMCP("travel-mcp-server")

TRAVEL_API = os.getenv("TRAVEL_API_URL", "http://localhost:9000")

# USD exchange rates (mock — updated periodically for the course)
EXCHANGE_RATES: dict[str, float] = {
    "USD": 1.00,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.50,
    "AUD": 1.53,
    "THB": 35.20,
    "AED": 3.67,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get(path: str, params: dict = {}) -> dict | list:
    """Make a GET request to the Travel API."""
    response = httpx.get(f"{TRAVEL_API}{path}", params=params, timeout=10)
    response.raise_for_status()
    return response.json()


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_destinations() -> str:
    """
    Get all available travel destinations.
    Returns a list of cities with country, description, best travel season,
    and average daily budget in USD.
    """
    destinations = get("/destinations")
    lines = []
    for d in destinations:
        lines.append(
            f"{d['city']}, {d['country']}\n"
            f"  {d['description']}\n"
            f"  Best season: {d['best_season']} | Avg daily budget: ${d['avg_daily_budget_usd']}"
        )
    return "\n\n".join(lines)


@mcp.tool()
def get_weather(city: str) -> str:
    """
    Get the current weather for a travel destination city.
    Returns temperature, conditions, humidity, and packing advice.

    Args:
        city: City name, e.g. 'Paris', 'Tokyo', 'Bangkok'
    """
    try:
        w = get(f"/weather/{city}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"No weather data available for '{city}'."
        raise

    return (
        f"{w['city']} — Current weather\n"
        f"  Temperature : {w['temperature_c']}°C\n"
        f"  Condition   : {w['condition']}\n"
        f"  Humidity    : {w['humidity_percent']}%\n"
        f"  Advice      : {w['advice']}"
    )


@mcp.tool()
def search_hotels(city: str, max_price_per_night: int = 10000) -> str:
    """
    Search for hotels in a city, optionally filtered by maximum price per night.
    Returns hotel name, type (budget / mid-range / luxury), price, and rating.

    Args:
        city: City name, e.g. 'Paris', 'Tokyo', 'Dubai'
        max_price_per_night: Maximum price in USD per night (default: no limit)
    """
    try:
        hotels = get(f"/hotels/{city}", params={"max_price": max_price_per_night})
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"No hotels found in '{city}' under ${max_price_per_night}/night."
        raise

    lines = [f"Hotels in {city} (max ${max_price_per_night}/night):\n"]
    for h in hotels:
        lines.append(
            f"  {h['name']}\n"
            f"    Type   : {h['type']}\n"
            f"    Price  : ${h['price_per_night_usd']}/night\n"
            f"    Rating : {h['rating']}/5.0"
        )
    return "\n\n".join(lines)


@mcp.tool()
def get_currency_rate(from_currency: str, to_currency: str) -> str:
    """
    Get the exchange rate between two currencies.
    Useful for helping travellers understand local costs.
    Supported currencies: USD, EUR, GBP, JPY, AUD, THB, AED.

    Args:
        from_currency: Source currency code, e.g. 'USD'
        to_currency:   Target currency code, e.g. 'JPY'
    """
    src = from_currency.upper()
    tgt = to_currency.upper()

    if src not in EXCHANGE_RATES:
        return f"Currency '{src}' not supported. Supported: {', '.join(EXCHANGE_RATES)}"
    if tgt not in EXCHANGE_RATES:
        return f"Currency '{tgt}' not supported. Supported: {', '.join(EXCHANGE_RATES)}"

    # Convert via USD as the base
    rate = EXCHANGE_RATES[tgt] / EXCHANGE_RATES[src]
    return (
        f"Exchange rate: 1 {src} = {rate:.4f} {tgt}\n"
        f"  Example: $100 {src} = {100 * rate:.2f} {tgt}"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
