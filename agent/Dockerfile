# ── Agent WebSocket API — Docker image ───────────────────────────────────────
#
# IMPORTANT: build context must be the repo root (not the agent/ folder),
# because the agent spawns the MCP server as a subprocess and needs both
# agent/ and mcp-server/ to be present in the image.
#
# Build (from repo root):
#   docker build -f agent/Dockerfile -t agent-service .
#
# Run (local):
#   docker run -p 8100:8100 --env-file agent/.env agent-service
#
# In the container the layout mirrors the repo:
#   /app/
#   ├── agent/       <- agent code + venv
#   └── mcp-server/  <- MCP server code + venv  (spawned as subprocess)
#
# MCPClient uses stdio transport:
#   uv run python /app/mcp-server/server.py
# This works because each directory has its own pyproject.toml + .venv.

FROM python:3.11-slim

# Install uv
RUN pip install --no-cache-dir uv

# ── Layer: MCP server dependencies ───────────────────────────────────────────
WORKDIR /app/mcp-server
COPY mcp-server/pyproject.toml .
RUN uv sync --no-dev

# Copy MCP server source (separate layer — code changes more often than deps)
COPY mcp-server/ .

# ── Layer: Agent dependencies ─────────────────────────────────────────────────
WORKDIR /app/agent
COPY agent/pyproject.toml .
RUN uv sync --no-dev

# Copy agent source
COPY agent/ .

EXPOSE 8100

# uv run resolves the venv from the CWD's pyproject.toml (/app/agent)
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8100"]
