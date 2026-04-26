import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Travel API", version="1.0.0")


# ── Models ────────────────────────────────────────────────────────────────────

class Destination(BaseModel):
    city: str
    country: str
    description: str
    best_season: str
    avg_daily_budget_usd: int


class Hotel(BaseModel):
    name: str
    city: str
    price_per_night_usd: int
    rating: float
    type: str  # budget | mid-range | luxury


class Weather(BaseModel):
    city: str
    temperature_c: int
    condition: str
    humidity_percent: int
    advice: str


class CurrencyRate(BaseModel):
    from_currency: str
    to_currency: str
    rate: float


# ── Load data ─────────────────────────────────────────────────────────────────

_raw = json.loads(Path("data.json").read_text(encoding="utf-8"))

DESTINATIONS: list[Destination]    = [Destination(**d) for d in _raw["destinations"]]
HOTELS: list[Hotel]                = [Hotel(**h)        for h in _raw["hotels"]]
WEATHER: dict[str, Weather]        = {k: Weather(**v)   for k, v in _raw["weather"].items()}
EXCHANGE_RATES: dict[str, float]   = _raw["exchange_rates"]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/destinations", response_model=list[Destination])
def get_destinations():
    """Return all available travel destinations."""
    return DESTINATIONS


@app.get("/weather/{city}", response_model=Weather)
def get_weather(city: str):
    """Return current weather for a city."""
    key = city.lower()
    if key not in WEATHER:
        raise HTTPException(status_code=404, detail=f"No weather data for '{city}'.")
    return WEATHER[key]


@app.get("/hotels/{city}", response_model=list[Hotel])
def get_hotels(
    city: str,
    max_price: int = Query(default=10000, description="Maximum price per night in USD"),
):
    """Return hotels in a city, optionally filtered by max price per night."""
    results = [
        h for h in HOTELS
        if h.city.lower() == city.lower() and h.price_per_night_usd <= max_price
    ]
    if not results:
        raise HTTPException(status_code=404, detail=f"No hotels found in '{city}' within budget.")
    return results


@app.get("/currency-rate", response_model=CurrencyRate)
def get_currency_rate(
    from_currency: str = Query(description="Source currency code, e.g. USD"),
    to_currency: str   = Query(description="Target currency code, e.g. JPY"),
):
    """Return the exchange rate between two currencies."""
    src = from_currency.upper()
    tgt = to_currency.upper()
    supported = list(EXCHANGE_RATES.keys())

    if src not in EXCHANGE_RATES:
        raise HTTPException(status_code=404, detail=f"Currency '{src}' not supported. Supported: {supported}")
    if tgt not in EXCHANGE_RATES:
        raise HTTPException(status_code=404, detail=f"Currency '{tgt}' not supported. Supported: {supported}")

    rate = EXCHANGE_RATES[tgt] / EXCHANGE_RATES[src]
    return CurrencyRate(from_currency=src, to_currency=tgt, rate=round(rate, 4))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
