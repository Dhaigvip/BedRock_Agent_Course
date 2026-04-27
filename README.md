# AI Travel Concierge — LangGraph + MCP + AWS Bedrock

Course project for **AI Agent with LangGraph, MCP Server & AWS Bedrock**.

The agent answers travel questions using real data. It classifies each question to pick the cheapest model, calls tools through an MCP server, and keeps the full conversation in state across turns.

---

## Architecture

```
You
 │
 ▼
Agent (LangGraph StateGraph)
 ├── classify_node  — Nova Micro decides: simple or complex?
 ├── llm_node       — Nova Micro / Nova Lite answers or requests a tool
 └── tool_node      — forwards tool calls through MCP
                           │
                           │  stdio (local dev)  /  HTTP/SSE (Docker + AWS)
                           ▼
                     MCP Server (FastMCP · port 8200)
                      ├── get_destinations
                      ├── get_weather
                      ├── search_hotels
                      ├── get_currency_rate
                      └── search_travel_guides  ← Bedrock Knowledge Base (Section 7)
                           │
                           ▼
                     Travel Data API (FastAPI · port 9000)
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| uv | latest | `pip install uv` |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| AWS account | — | [aws.amazon.com](https://aws.amazon.com) |

> **AWS CLI** is only needed in **Section 10 (Deployment)** for pushing Docker images to ECR.
> You do not need it for Sections 1–9. Install instructions are in `deploy/DEPLOYMENT_GUIDE.md`.

---

## Project structure

```
BedRock_Agent_Course/
├── travel-api/       FastAPI data service (port 9000)
├── mcp-server/       MCP server — tools + prompts
├── agent/            LangGraph agent + Bedrock client
└── resources/        Student reference docs (downloadable)
```

---

## 1 — AWS setup

### Create an IAM user

> Skip this if you already have an IAM user with programmatic access.

1. Open **IAM → Users → Create user**
2. **User name:** `bedrock` → **Next**
3. **Permissions:** Attach policies directly → search for and select `AmazonBedrockFullAccess` → **Next**
4. → **Create user**

Now generate an access key:

5. Open the `bedrock` user → **Security credentials** tab
6. **Access keys → Create access key**
7. Use case: **Command Line Interface (CLI)** → tick the confirmation → **Next**
8. → **Create access key**
9. **Copy both the Access Key ID and Secret Access Key** — the secret is only shown once.

> **Deployment note:** Section 10 (AWS deployment) needs additional permissions beyond
> `AmazonBedrockFullAccess`. Step 0 of the Deployment Guide covers this — you will
> attach ECR, ECS, and Secrets Manager policies to this same user before deploying.

---

---

## 2 — Environment file

**Mac / Linux**
```bash
cp agent/.env.example agent/.env
```

**Windows (PowerShell)**
```powershell
copy agent\.env.example agent\.env
```

Open `agent/.env` and paste in the keys you just created:

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
TRAVEL_API_URL=http://localhost:9000
...
```

The remaining values (`BEDROCK_KB_ID`, `S3_BUCKET_NAME`, etc.) are filled in
later as you work through each section — leave them as-is for now.

> **`MCP_TRANSPORT`** controls how the agent connects to the MCP server:
> - `stdio` (default) — agent spawns it as a subprocess. No separate terminal needed. Use this for `uv run` local dev (Sections 1–9).
> - `http` — MCP server runs as its own container. Used automatically by Docker Compose and ECS (Section 10).

> **Section 10 — Deployment:** `aws configure` is needed in that section so
> the AWS CLI can push Docker images to ECR. The AWS CLI install instructions
> are in the Prerequisites section above.

---

## 3 — Install dependencies

Each sub-project is independent and can be installed and run on its own.
To install all three at once, run the setup script from the repo root:

**Mac / Linux**
```bash
bash setup.sh
```

**Windows**
```bat
setup.bat
```

Or install each one individually:

**Mac / Linux (bash)**
```bash
cd travel-api  && uv sync && cd ..
cd mcp-server  && uv sync && cd ..
cd agent       && uv sync && cd ..
cd ui          && npm install && cd ..
```

**Windows (PowerShell)**
```powershell
cd travel-api;  uv sync; cd ..
cd mcp-server;  uv sync; cd ..
cd agent;       uv sync; cd ..
cd ui;          npm install; cd ..
```

---

## 4 — Run the stack

Two ways to run locally — **uv (recommended for development)** or **Docker**.

---

### Option A — uv (fast, no Docker required)

Open **four terminals** — one per service.
Each service uses its own `.venv` inside its own folder.

> **Windows note:** PowerShell 5.1 does not support `&&`.
> Use `;` to chain commands, or run each command on its own line.

#### Terminal 1 — Travel Data API

```powershell
cd travel-api
uv run python main.py
# Serving on http://localhost:9000
```

Verify:
```powershell
Invoke-RestMethod http://localhost:9000/health
# status : ok
```

#### Terminal 2 — MCP Inspector (optional — Section 3 only)

```powershell
cd mcp-server
uv run mcp dev server.py
# Inspector at http://localhost:6274
```

#### Terminal 3 — Agent CLI (Sections 1–8) or WebSocket API (Section 9+)

```powershell
cd agent

# Interactive CLI — used in Sections 1–8
uv run python main.py

# WebSocket API — used in Section 9+
uv run python api.py
# WebSocket ready at ws://localhost:8100/ws/chat
```

> With `MCP_TRANSPORT=stdio` (the default), the MCP server starts automatically
> as a subprocess — you do **not** need a separate terminal for it.

#### Terminal 4 — React UI (Section 9+)

```powershell
cd ui
npm run dev
# http://localhost:5173
```

---

### Option B — Docker Compose (mirrors the production stack)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.
All four services start in containers with inter-service networking wired automatically.

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| React UI | http://localhost:8080 |
| Agent WebSocket | ws://localhost:8100/ws/chat |
| MCP Server | http://localhost:8200/sse (internal) |
| Travel API | http://localhost:9000 (internal) |

```bash
docker compose down   # stop and remove containers
```

You should see:

```
============================================================
  Travel Concierge Agent
  Connecting to MCP server...
[mcp] 4 tools loaded: ['get_destinations', 'get_weather', 'search_hotels', 'get_currency_rate']
  Type 'quit' to exit
============================================================

You: 
```

---

## 5 — Try it out

```
You: What is the weather in Tokyo?
You: Find me hotels in Paris under $150 a night
You: I have 500 USD — how much is that in Thai Baht?
You: Plan a 5-day trip to Bangkok on a $1500 budget
You: quit
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Connection refused` on port 9000 | Start the Travel API first (Terminal 1) |
| `Could not connect to Bedrock` | Run `aws configure` and check region is `us-east-1` |
| `ResourceNotFoundException` | Check `AWS_REGION=us-east-1` in `.env` — Nova models are only available in that region |
| `UnicodeEncodeError` on Windows | Set terminal encoding: `chcp 65001` |
| MCP server subprocess fails to start | Make sure `uv` is on your PATH; check `mcp-server/pyproject.toml` deps installed |

---

## Resources (student downloads)

| File | Contents |
|------|----------|
| `resources/mcp-tools-reference.md` | All 4 MCP tools — params, examples, best practices |
| `resources/mcp-prompts-reference.md` | Both MCP prompts with rendered message examples |
| `resources/agent-prompts-reference.md` | Agent system prompt guide + Bedrock message format rules |
