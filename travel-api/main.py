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
    type: str          # budget | mid-range | luxury


class Weather(BaseModel):
    city: str
    temperature_c: int
    condition: str
    humidity_percent: int
    advice: str


# ── Data ──────────────────────────────────────────────────────────────────────

DESTINATIONS: list[Destination] = [
    Destination(city="Paris",     country="France",      description="The city of light, famous for the Eiffel Tower, world-class cuisine and art.",         best_season="Apr–Jun",  avg_daily_budget_usd=180),
    Destination(city="Tokyo",     country="Japan",       description="A dazzling mix of ultra-modern and traditional, with incredible food and transport.",   best_season="Mar–May",  avg_daily_budget_usd=120),
    Destination(city="New York",  country="USA",         description="The city that never sleeps — iconic skyline, Broadway, and endless neighbourhoods.",    best_season="Sep–Nov",  avg_daily_budget_usd=200),
    Destination(city="Sydney",    country="Australia",   description="Stunning harbour city with world-famous beaches, great food and friendly locals.",      best_season="Sep–Nov",  avg_daily_budget_usd=150),
    Destination(city="Rome",      country="Italy",       description="The Eternal City, packed with ancient history, incredible food and beautiful piazzas.", best_season="Apr–Jun",  avg_daily_budget_usd=130),
    Destination(city="Bangkok",   country="Thailand",    description="Vibrant street food capital with ornate temples, buzzing nightlife and great value.",   best_season="Nov–Feb",  avg_daily_budget_usd=60),
    Destination(city="Barcelona", country="Spain",       description="Gaudí architecture, golden beaches, tapas and a lively arts scene.",                   best_season="May–Jun",  avg_daily_budget_usd=130),
    Destination(city="Dubai",     country="UAE",         description="Futuristic skyline, luxury shopping, desert safaris and year-round sunshine.",          best_season="Nov–Mar",  avg_daily_budget_usd=220),
]

HOTELS: list[Hotel] = [
    # Paris
    Hotel(name="Hotel Lumière",         city="Paris",     price_per_night_usd=89,  rating=4.1, type="budget"),
    Hotel(name="Le Marais Boutique",    city="Paris",     price_per_night_usd=175, rating=4.5, type="mid-range"),
    Hotel(name="Ritz Paris",            city="Paris",     price_per_night_usd=650, rating=4.9, type="luxury"),
    # Tokyo
    Hotel(name="Shinjuku Capsule Inn",  city="Tokyo",     price_per_night_usd=45,  rating=3.9, type="budget"),
    Hotel(name="Shibuya Excel Hotel",   city="Tokyo",     price_per_night_usd=130, rating=4.3, type="mid-range"),
    Hotel(name="Park Hyatt Tokyo",      city="Tokyo",     price_per_night_usd=480, rating=4.8, type="luxury"),
    # New York
    Hotel(name="The Pod Hotel",         city="New York",  price_per_night_usd=99,  rating=4.0, type="budget"),
    Hotel(name="citizenM Times Square", city="New York",  price_per_night_usd=189, rating=4.5, type="mid-range"),
    Hotel(name="The Plaza",             city="New York",  price_per_night_usd=595, rating=4.7, type="luxury"),
    # Sydney
    Hotel(name="Wake Up! Sydney",       city="Sydney",    price_per_night_usd=75,  rating=4.0, type="budget"),
    Hotel(name="Adina Apartment Hotel", city="Sydney",    price_per_night_usd=155, rating=4.4, type="mid-range"),
    Hotel(name="Park Hyatt Sydney",     city="Sydney",    price_per_night_usd=520, rating=4.8, type="luxury"),
    # Rome
    Hotel(name="The Yellow Hostel",     city="Rome",      price_per_night_usd=55,  rating=4.2, type="budget"),
    Hotel(name="Hotel Artemide",        city="Rome",      price_per_night_usd=145, rating=4.4, type="mid-range"),
    Hotel(name="Hotel Eden",            city="Rome",      price_per_night_usd=580, rating=4.9, type="luxury"),
    # Bangkok
    Hotel(name="Lub d Bangkok",         city="Bangkok",   price_per_night_usd=30,  rating=4.1, type="budget"),
    Hotel(name="Riva Arun Bangkok",     city="Bangkok",   price_per_night_usd=95,  rating=4.5, type="mid-range"),
    Hotel(name="Mandarin Oriental",     city="Bangkok",   price_per_night_usd=380, rating=4.9, type="luxury"),
    # Barcelona
    Hotel(name="TOC Hostel Barcelona",  city="Barcelona", price_per_night_usd=50,  rating=4.2, type="budget"),
    Hotel(name="Hotel Arts Barcelona",  city="Barcelona", price_per_night_usd=160, rating=4.6, type="mid-range"),
    Hotel(name="W Barcelona",           city="Barcelona", price_per_night_usd=420, rating=4.7, type="luxury"),
    # Dubai
    Hotel(name="Dubai Youth Hostel",    city="Dubai",     price_per_night_usd=40,  rating=3.8, type="budget"),
    Hotel(name="Rove Downtown Dubai",   city="Dubai",     price_per_night_usd=110, rating=4.4, type="mid-range"),
    Hotel(name="Burj Al Arab",          city="Dubai",     price_per_night_usd=1200,rating=4.9, type="luxury"),
]

WEATHER: dict[str, Weather] = {
    "paris":     Weather(city="Paris",     temperature_c=17, condition="Partly cloudy", humidity_percent=72, advice="Pack a light jacket."),
    "tokyo":     Weather(city="Tokyo",     temperature_c=22, condition="Sunny",         humidity_percent=60, advice="Great weather — perfect for sightseeing."),
    "new york":  Weather(city="New York",  temperature_c=14, condition="Overcast",      humidity_percent=65, advice="Bring an umbrella just in case."),
    "sydney":    Weather(city="Sydney",    temperature_c=24, condition="Sunny",         humidity_percent=55, advice="Sunscreen recommended."),
    "rome":      Weather(city="Rome",      temperature_c=20, condition="Clear",         humidity_percent=50, advice="Ideal weather for exploring on foot."),
    "bangkok":   Weather(city="Bangkok",   temperature_c=33, condition="Hot and humid", humidity_percent=85, advice="Stay hydrated and wear light clothing."),
    "barcelona": Weather(city="Barcelona", temperature_c=21, condition="Sunny",         humidity_percent=58, advice="Perfect beach weather."),
    "dubai":     Weather(city="Dubai",     temperature_c=38, condition="Sunny and dry", humidity_percent=30, advice="Very hot — limit outdoor activity midday."),
}


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
