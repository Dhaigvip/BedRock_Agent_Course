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
                           ▼
                     MCP Server (FastMCP)
                      ├── get_destinations
                      ├── get_weather
                      ├── search_hotels
                      └── get_currency_rate
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
| AWS account | — | [aws.amazon.com](https://aws.amazon.com) |
| AWS CLI | v2 | [docs.aws.amazon.com/cli](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) |

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

### Enable Bedrock model access

1. Open the [AWS Console → Bedrock → Model access](https://console.aws.amazon.com/bedrock/home#/modelaccess)
2. Enable **Amazon Nova Micro** and **Amazon Nova Lite**
3. Region: `us-east-1` (default)

### Configure credentials

```bash
aws configure
# AWS Access Key ID:     <your key>
# AWS Secret Access Key: <your secret>
# Default region:        us-east-1
# Output format:         json
```

---

## 2 — Environment file

```bash
cp agent/.env.example agent/.env
```

Edit `agent/.env`:

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
TRAVEL_API_URL=http://localhost:9000
```

> If you configured `aws configure` above, you can leave the key fields
> blank — boto3 will pick up credentials from `~/.aws/credentials`.

---

## 3 — Install dependencies

Each sub-project is a standalone `uv` project.

```bash
# Travel API
cd travel-api && uv sync && cd ..

# MCP Server
cd mcp-server && uv sync && cd ..

# Agent
cd agent && uv sync && cd ..
```

---

## 4 — Run the stack

Open **three terminals** — one per service.

### Terminal 1 — Travel Data API

```bash
cd travel-api
uv run python main.py
# Serving on http://localhost:9000
```

Verify:
```bash
curl http://localhost:9000/health
# {"status":"ok"}
```

### Terminal 2 — MCP Inspector (optional, for testing tools)

```bash
cd mcp-server
uv run mcp dev server.py
# Inspector at http://localhost:6274
```

> Skip this terminal once you're past Section 3.

### Terminal 3 — Agent

```bash
cd agent
uv run python main.py
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
| `ResourceNotFoundException` | Enable Nova Micro + Nova Lite in Bedrock console model access |
| `UnicodeEncodeError` on Windows | Set terminal encoding: `chcp 65001` |
| MCP server subprocess fails to start | Make sure `uv` is on your PATH; check `mcp-server/pyproject.toml` deps installed |

---

## Resources (student downloads)

| File | Contents |
|------|----------|
| `resources/mcp-tools-reference.md` | All 4 MCP tools — params, examples, best practices |
| `resources/mcp-prompts-reference.md` | Both MCP prompts with rendered message examples |
| `resources/agent-prompts-reference.md` | Agent system prompt guide + Bedrock message format rules |
