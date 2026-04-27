import os
import boto3
import httpx
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import UserMessage, AssistantMessage

load_dotenv()

# ── Server ────────────────────────────────────────────────────────────────────

mcp = FastMCP("travel-mcp-server")

TRAVEL_API = os.getenv("TRAVEL_API_URL", "http://localhost:9000")
KB_ID      = os.getenv("BEDROCK_KB_ID", "")
REGION     = os.getenv("AWS_REGION", "us-east-1")

_bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=REGION)


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
    try:
        result = get("/currency-rate", params={"from_currency": from_currency, "to_currency": to_currency})
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return e.response.json().get("detail", "Currency not supported.")
        raise

    src, tgt, rate = result["from_currency"], result["to_currency"], result["rate"]
    return (
        f"Exchange rate: 1 {src} = {rate} {tgt}\n"
        f"  Example: 100 {src} = {100 * rate:.2f} {tgt}"
    )


# ── RAG tool ──────────────────────────────────────────────────────────────────

@mcp.tool()
def search_travel_guides(query: str) -> str:
    """
    Search the travel knowledge base for destination guides, visa requirements,
    packing tips, local customs, and practical travel advice.
    Use this tool for questions about visas, entry rules, cultural etiquette,
    or detailed destination information not covered by the other tools.

    Args:
        query: Natural language search query, e.g. 'visa requirements for Japan'
    """
    if not KB_ID:
        return (
            "Knowledge Base not configured. "
            "Set BEDROCK_KB_ID in agent/.env to enable travel guide search."
        )

    try:
        response = _bedrock_agent.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 4}
            },
        )
    except ClientError as e:
        return f"Knowledge Base search failed: {e.response['Error']['Message']}"

    results = response.get("retrievalResults", [])
    if not results:
        return f"No travel guide information found for: {query}"

    # Return the top chunks as plain text — the LLM will synthesise the answer
    chunks = []
    for r in results:
        text  = r["content"]["text"]
        score = r.get("score", 0)
        chunks.append(f"[relevance: {score:.2f}]\n{text}")

    return "\n\n---\n\n".join(chunks)


# ── Prompts ───────────────────────────────────────────────────────────────────

@mcp.prompt()
def trip_planner_prompt(destination: str, budget_usd: int, duration_days: int) -> list[UserMessage | AssistantMessage]:
    """
    A reusable prompt template for planning a complete trip.
    Primes the model with traveller context before the conversation starts.

    Args:
        destination:   City to travel to, e.g. 'Tokyo'
        budget_usd:    Total trip budget in USD
        duration_days: Length of the trip in days
    """
    return [
        UserMessage(
            content=(
                f"I am planning a {duration_days}-day trip to {destination} "
                f"with a total budget of ${budget_usd} USD.\n\n"
                f"Please help me with the following:\n"
                f"1. Best areas to stay within my budget\n"
                f"2. Must-see attractions and estimated costs\n"
                f"3. Daily budget breakdown (accommodation, food, transport, activities)\n"
                f"4. Any travel tips or warnings I should know about\n\n"
                f"Use the available tools to check current hotel prices and weather."
            )
        ),
        AssistantMessage(
            content=(
                f"I'd be happy to help plan your {duration_days}-day trip to {destination}! "
                f"Let me look up the latest hotel options and weather for you."
            )
        ),
    ]


@mcp.prompt()
def budget_breakdown_prompt(destination: str, total_budget_usd: int, duration_days: int) -> list[UserMessage]:
    """
    A prompt template that asks for a detailed daily budget breakdown.

    Args:
        destination:      City to travel to
        total_budget_usd: Total available budget in USD
        duration_days:    Number of days travelling
    """
    daily = total_budget_usd // duration_days
    return [
        UserMessage(
            content=(
                f"My total budget for {destination} is ${total_budget_usd} USD "
                f"over {duration_days} days (${daily}/day).\n\n"
                f"Please give me a realistic daily budget breakdown showing how to "
                f"allocate the ${daily}/day across:\n"
                f"- Accommodation\n"
                f"- Food & drinks\n"
                f"- Local transport\n"
                f"- Activities & entrance fees\n"
                f"- Miscellaneous / buffer\n\n"
                f"Flag if the budget is too tight and suggest adjustments."
            )
        ),
    ]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        # HTTP/SSE mode — used in Docker and ECS deployment.
        # The agent connects via sse_client("http://host:8200/sse").
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8200"))
        print(f"[mcp-server] starting SSE transport on {host}:{port}", flush=True)
        mcp.run(transport="sse", host=host, port=port)
    else:
        # stdio mode — default for local development.
        # The agent spawns this script as a subprocess.
        mcp.run()
