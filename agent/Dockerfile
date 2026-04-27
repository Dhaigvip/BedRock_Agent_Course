# ── Agent WebSocket API — Docker image ───────────────────────────────────────
#
# Build context is the REPO ROOT (not agent/).
# The mcp-server code is bundled inside this image so the agent can spawn it
# as a subprocess (stdio transport) — no separate container needed.
#
# Build (from repo root):
#   docker build -f agent/Dockerfile -t agent-service .
#
# docker-compose handles this automatically via context: . + dockerfile: agent/Dockerfile

FROM python:3.11-slim

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependencies layer (cached unless pyproject.toml changes)
COPY agent/pyproject.toml .
RUN uv sync --no-dev

# Copy agent source
COPY agent/ /app/

# Copy mcp-server source — spawned as stdio subprocess by the agent
COPY mcp-server/ /app/mcp-server/

EXPOSE 8100

CMD ["uv", "run", "python", "api.py"]
