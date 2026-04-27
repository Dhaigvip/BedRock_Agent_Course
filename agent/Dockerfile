# ── Agent WebSocket API — Docker image ───────────────────────────────────────
#
# Build context is the agent/ folder.
# The MCP server is a separate container connected via HTTP/SSE — it does NOT
# need to be bundled here.
#
# Build (from the agent/ folder):
#   docker build -t agent-service .
#
# Run (local, pointing at a running mcp-server container):
#   docker run -p 8100:8100 --env-file .env \
#     -e MCP_TRANSPORT=http \
#     -e MCP_SERVER_URL=http://host.docker.internal:8200/sse \
#     agent-service

FROM python:3.11-slim

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependencies layer (cached unless pyproject.toml changes)
COPY pyproject.toml .
RUN uv sync --no-dev

# Source layer
COPY . .

EXPOSE 8100

CMD ["uv", "run", "python", "api.py"]
