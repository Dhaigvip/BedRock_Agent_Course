# ── Travel Data API — Docker image ───────────────────────────────────────────
#
# Build:
#   docker build -t travel-api ./travel-api
#
# Run (local):
#   docker run -p 9000:9000 travel-api
#
# The API has no secrets — no AWS calls, no .env needed.

FROM python:3.11-slim

# Install uv (fast Python package manager used throughout the course)
RUN pip install --no-cache-dir uv

WORKDIR /app

# ── Layer: install dependencies ───────────────────────────────────────────────
# Copy only the project manifest first so Docker can cache this layer.
# The layer is only rebuilt when pyproject.toml changes, not on code changes.
COPY pyproject.toml .
RUN uv sync --no-dev

# ── Layer: copy source ────────────────────────────────────────────────────────
COPY . .

EXPOSE 9000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
