# ── Agent WebSocket API — Docker image ───────────────────────────────────────
#
# Build context is the agent/ folder.
# The MCP server runs as a separate container connected via HTTP (streamable-http).
#
# Build (from the agent/ folder):
#   docker build -t agent-service .

FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependencies layer (cached unless pyproject.toml changes)
COPY pyproject.toml .
RUN uv sync --no-dev

# Source layer
COPY . .

EXPOSE 8100

CMD ["uv", "run", "python", "api.py"]
