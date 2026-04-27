# ── MCP Server — Docker image ──────────────────────────────────────────────────
#
# Standalone container for the Travel MCP Server.
# Runs on HTTP/SSE transport so the agent can connect via HTTP.
#
# Build (from the mcp-server/ folder):
#   docker build -t mcp-server .
#
# Run (local):
#   docker run -p 8200:8200 --env-file ../agent/.env mcp-server
#
# The agent connects to this container at:
#   http://mcp-server:8200/sse  (docker-compose service name)
#   http://<private-ip>:8200/sse  (ECS Fargate private IP)

FROM python:3.11-slim

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependencies layer (cached unless pyproject.toml changes)
COPY pyproject.toml .
RUN uv sync --no-dev

# Source layer
COPY . .

# Force HTTP/SSE transport in all container environments
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8200

EXPOSE 8200

CMD ["uv", "run", "python", "server.py"]
