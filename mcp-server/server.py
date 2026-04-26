import os
import httpx
from mcp.server.fastmcp import FastMCP

# ── Server ────────────────────────────────────────────────────────────────────

mcp = FastMCP("travel-mcp-server")

TRAVEL_API = os.getenv("TRAVEL_API_URL", "http://localhost:9000")


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


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
