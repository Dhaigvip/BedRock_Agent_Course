# AI Agent with LangGraph, MCP Server & AWS Bedrock
### Build a Production-Ready AI Travel Concierge from Scratch

**52 videos · ~6 hours · Python + React + AWS**

---

## Section Summary

| # | Section | Videos | Time |
|---|---|---|---|
| 1 | Introduction | 3 | 15 min |
| 2 | MCP Concepts | 2 | 13 min |
| 3 | Build the MCP Server | 7 | 54 min |
| 4 | AWS Bedrock Introduction | 3 | 22 min |
| 5 | Agent I — LangGraph + Bedrock | 7 | 48 min |
| 6 | Agent II — MCP Integration | 5 | 35 min |
| 7 | RAG Deep Dive | 6 | 42 min |
| 8 | Agent III — Memory + Guardrails + Traceability | 5 | 37 min |
| 9 | React UI + WebSocket Streaming | 5 | 38 min |
| 10 | Deployment to AWS | 9 | 56 min |
| **Total** | | **52 videos** | **~6 hours** |

---

## Section 1 — Introduction
*3 videos · 15 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 1.1 | Welcome & What You'll Build | Talking head | 3 min |
| 1.2 | Agents, MCP, and Bedrock — The Big Picture | Slides | 6 min |
| 1.3 | Full Architecture Walkthrough | Diagram | 6 min |

**V1.1 — Welcome & What You'll Build**
- Hook: show the finished app — streaming chat, live tool calls, memory across sessions
- What you will build: AI Travel Concierge — trip planning, hotels, weather, currency, visa guides
- Tech stack overview: Python · LangGraph · MCP · AWS Bedrock · React
- Prerequisites and section roadmap

**V1.2 — Agents, MCP, and Bedrock — The Big Picture**
- Traditional software vs agent loop: perceive → reason → act → observe
- LangGraph's role: makes the loop explicit, inspectable, and controllable
- What MCP adds: standardised tool layer — swap tools without changing the agent
- AWS Bedrock: managed LLM API with Knowledge Bases, Guardrails, and model variety
- Why these three together: LangGraph (orchestration) + MCP (tools) + Bedrock (LLM)

**V1.3 — Full Architecture Walkthrough**
- Outer shell: React UI → FastAPI WebSocket → LangGraph StateGraph
- Agent internals: classify node → llm node → tool node
- MCP layer: agent ↔ MCP client ↔ MCP server ↔ Travel Data API
- Bedrock layer: Nova Micro/Lite + Knowledge Base (S3 + vectors) + Guardrails
- End-to-end data flow: user question → streamed token-by-token answer

---

## Section 2 — MCP Concepts
*2 videos · 13 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 2.1 | What is MCP + Architecture | Slides | 7 min |
| 2.2 | Transports + Server-Client Lifecycle | Slides | 6 min |

**V2.1 — What is MCP + Architecture**
- Problem before MCP: every tool needs custom wiring per application
- MCP = "USB port for AI tools" — one protocol, any host
- Three roles: Host (Claude/VS Code), Client (inside host), Server (your tools)
- Three capability types: Tools (do things), Prompts (templates), Resources (read data)
- JSON-RPC protocol: request → response, method names, lifecycle

**V2.2 — Transports + Server-Client Lifecycle**
- Server: exposes capabilities, runs as a process
- Client: connects, lists capabilities, calls tools, passes results back to LLM
- stdio transport: subprocess pipe — local dev, what we use in this course
- HTTP + SSE transport: network, multi-client, production use
- Decision guide: stdio for dev and course, HTTP for production deployment

---

## Section 3 — Build the MCP Server
*7 videos · 54 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 3.1 | Project Setup | Coding | 7 min |
| 3.2 | Build the Travel Data API | Coding | 10 min |
| 3.3 | Create MCP Server + First Tool | Coding | 8 min |
| 3.4 | Add More Tools | Coding | 9 min |
| 3.5 | MCP Tool Best Practices | Slides + Code | 6 min |
| 3.6 | Test with MCP Inspector | Demo | 8 min |
| 3.7 | MCP Prompts | Coding | 6 min |

**V3.1 — Project Setup**
- Two sub-projects: `travel-api/` (FastAPI data service) and `mcp-server/`
- Create folders, virtual envs with `uv`, install `fastapi uvicorn mcp[cli] httpx`
- Final folder structure and what goes where

**V3.2 — Build the Travel Data API**
- Why a separate API: realistic architecture, MCP server calls real services
- FastAPI app with in-memory data: destinations, hotels, weather, exchange rates
- Endpoints: `/destinations`, `/weather/{city}`, `/hotels`, `/currency`
- Run with `uv run uvicorn main:app`, test via Swagger at `/docs`

**V3.3 — Create MCP Server + First Tool**
- FastMCP: `from mcp.server.fastmcp import FastMCP`, `@mcp.tool()` decorator
- First tool: `get_destinations` — typed params, docstring as description, httpx call to Travel API
- Run with `mcp run server.py`, explain startup output
- Decorator → description → JSON Schema → handler — the full chain

**V3.4 — Add More Tools**
- Add `get_weather(city)`, `search_hotels(city, max_price)`, `get_currency_rate(from, to)`
- Each tool: typed params, httpx call to Travel API, return plain string
- Add `search_travel_guides(query)` — RAG tool calling Bedrock Knowledge Base (graceful fallback if no KB)

**V3.5 — MCP Tool Best Practices**
- Docstrings are everything — the LLM reads them to decide when and how to call the tool
- Parameter naming: be explicit, use clear names, annotate types
- Return format: always plain text, never raise exceptions — return error strings instead
- Single responsibility: one tool = one thing
- Review our 5 tools against these rules

**V3.6 — Test with MCP Inspector**
- Launch: `uv run mcp dev server.py` → Inspector at `http://localhost:6274`
- List tools, call `search_hotels`, inspect request and response JSON
- What the agent will see: tool schema format

**V3.7 — MCP Prompts**
- What are prompts: reusable message templates the agent or user can trigger
- Register `trip_planner_prompt(destination, budget)` and `budget_breakdown_prompt`
- Test in Inspector: call with args, see rendered messages
- Difference between prompts and tools: templates vs actions

---

## Section 4 — AWS Bedrock Introduction
*3 videos · 22 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 4.1 | Why Bedrock? Not OpenAI or the Claude API? | Slides | 7 min |
| 4.2 | Models + Cost | Slides | 7 min |
| 4.3 | AWS Local Dev Setup | Demo | 8 min |

**V4.1 — Why Bedrock? Not OpenAI or the Claude API?**
- The obvious question: Anthropic has a direct API, OpenAI exists — why go via Bedrock?
- Bedrock advantages: AWS IAM auth (no API keys in code), VPC isolation, data stays in AWS, compliance
- Unified API: swap Nova → Claude → Llama with one line change, no SDK change
- Extras only on Bedrock: Knowledge Bases, Guardrails — all AWS-native
- When to use the direct API instead: prototyping, non-AWS stack, latest model features first

**V4.2 — Models + Cost**
- Nova family: Micro (cheapest/fastest) · Lite (balanced) · Pro (complex reasoning)
- Claude 3.5 / 3.7 on Bedrock: when to prefer over Nova
- Token pricing: input vs output; the classifier trick — route cheap model first to save cost
- Model ID format: `amazon.nova-micro-v1:0` — how to reference in code

**V4.3 — AWS Local Dev Setup**
- IAM → Users → Create user
  - User name: `bedrock`
  - Attach policies directly: `AmazonBedrockFullAccess`
  - Create user → open user → Security credentials → Create access key
  - Use case: CLI → create → download CSV (keep safe)
- Enable model access in Bedrock console: Nova Micro + Nova Lite
  - Bedrock → Model access → Modify model access → enable both → Save
- `aws configure`: paste access key, secret key, region `us-east-1`, output `json`
- Test: boto3 one-liner to Nova Micro, confirm response in terminal
- Note: this user will need additional permissions in Section 10 (ECR + ECS + Secrets Manager)

---

## Section 5 — Agent I: LangGraph + Bedrock
*7 videos · 48 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 5.1 | LangGraph Core Concepts | Slides | 6 min |
| 5.2 | Project Setup + Bedrock Client | Coding | 6 min |
| 5.3 | Define Agent State | Coding | 7 min |
| 5.4 | Classifier Node | Coding | 7 min |
| 5.5 | LLM Node | Coding | 8 min |
| 5.6 | Wire the Graph | Coding | 8 min |
| 5.7 | Run + Console Output | Demo | 6 min |

**V5.1 — LangGraph Core Concepts**
- StateGraph: state flows through nodes, edges define order
- Reducers: how state fields update — `operator.add` (append) vs last-write-wins
- Conditional edges: function returns the next node name or `END`
- Why LangGraph over a while loop: inspectable, pausable, testable per-node

**V5.2 — Project Setup + Bedrock Client**
- Create `agent/` folder, `uv init`, install `langgraph boto3 python-dotenv`
- `bedrock.py`: `boto3.client("bedrock-runtime")`, `call_bedrock()` wrapper function
- Token pricing dict, `log_usage()` helper — cost visibility from day one

**V5.3 — Define Agent State**
- `TypedDict` + `Annotated` + `operator.add` for the message reducer
- `AgentState`: `messages` (append), `model_id` (replace), `tools` (replace)
- Show reducer behaviour: append two messages, confirm list grows

**V5.4 — Classifier Node**
- Why Nova Micro for classification: cheapest model, single-word answer needed
- `classify_node`: extract user text, call `build_classifier_prompt()`, parse "simple"/"complex"
- Returns `{"model_id": ...}` — how nodes update state by returning a dict
- Test with 5 questions, verify correct routing

**V5.5 — LLM Node**
- `llm_node`: reads `model_id` + `messages` + `tools` from state
- Calls `call_bedrock()`, returns assistant message
- Guardrail config: how to wire `BEDROCK_GUARDRAIL_ID` from environment
- Log tool-call requests vs direct text answers for traceability

**V5.6 — Wire the Graph**
- `_should_use_tool()`: inspect last message content for `toolUse` blocks
- `build_graph()`: add nodes, `set_entry_point`, `add_conditional_edges`, `add_edge`
- Compile with `checkpointer=None` for now
- Draw with `graph.get_graph().draw_mermaid()`

**V5.7 — Run + Console Output**
- Compile graph, run with `agent.invoke()`
- Trace state at each node: classify → llm → tool decision
- Confirm data flows correctly, preview MCP integration next

---

## Section 6 — Agent II: MCP Integration
*5 videos · 35 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 6.1 | MCP Client in Python | Coding | 8 min |
| 6.2 | Why Tool Format Conversion? MCP vs Bedrock Schemas | Slides | 5 min |
| 6.3 | Tool Mapping + Tool Node | Coding | 10 min |
| 6.4 | Centralising Agent Prompts | Coding | 5 min |
| 6.5 | Full Agent + MCP Demo | Demo | 7 min |

**V6.1 — MCP Client in Python**
- MCP Python SDK: `stdio_client`, `StdioServerParameters`, `ClientSession`
- `MCPClient` class: `connect()` async context manager, `list_tools()`, `call_tool()`
- Start MCP server as subprocess — `uv run python server.py` via `StdioServerParameters`
- Async factory pattern: `async with MCPClient.connect() as client`

**V6.2 — Why Tool Format Conversion? MCP vs Bedrock Schemas**
- The gap: MCP and Bedrock both use JSON Schema — but package it differently
- Side-by-side diff: MCP `{"name", "description", "inputSchema"}` vs Bedrock `{"toolSpec": {"name", "description", "inputSchema": {"json": {...}}}}`
- Why it exists: MCP is an open protocol, Bedrock is AWS's API — neither knows about the other
- The conversion is a one-time startup step — add a tool to MCP server and the agent picks it up automatically
- Preview: a 5-line `_mcp_tool_to_bedrock()` helper — that is all it takes

**V6.3 — Tool Mapping + Tool Node**
- `_mcp_tool_to_bedrock()`: wrap MCP tool schema in the Bedrock `toolSpec` envelope
- `list_tools()`: call `mcp.list_tools()`, map each through the converter
- `tool_node`: async node — filter `toolUse` blocks → `mcp.call_tool()` → `toolResult` message
- Why tool_node must be async: MCP call is async, LangGraph supports async nodes
- Wire into graph, test with "Find hotels in Paris under $150"

**V6.4 — Centralising Agent Prompts**
- Problem: prompt strings scattered across `main.py`, `api.py`, `nodes.py`, `memory.py`
- Solution: `prompts.py` — one file, four functions/constants
- `build_system_prompt(user_facts)`, `SYSTEM_ACK`, `build_classifier_prompt(text)`, `build_memory_prompt(existing, conversation)`
- Update all files to import from `prompts.py` — zero inline prompt strings remain
- Student resource: `resources/agent-prompts-reference.md` — copy-paste all 4 prompts with explanations

**V6.5 — Full Agent + MCP Demo**
- All components running: agent → Bedrock → MCP → Travel API
- Live demo: 3 travel questions, show tool calls in console logs
- Agent log + MCP server log + Travel API log side-by-side

---

## Section 7 — RAG Deep Dive
*6 videos · 42 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 7.1 | What is RAG? | Slides | 5 min |
| 7.2 | Vectors + Semantic Search | Slides | 6 min |
| 7.3 | AWS Setup + Knowledge Base | Console + Coding | 9 min |
| 7.4 | S3 Bucket Setup | Console + Coding | 6 min |
| 7.5 | Upload Content + Sync | Demo | 7 min |
| 7.6 | Model Call with RAG | Coding | 9 min |

**V7.1 — What is RAG?**
- Problem: LLMs have a knowledge cutoff date and hallucinate on domain-specific facts
- RAG pattern: retrieve relevant docs → augment prompt → grounded answer with citations
- Real-world examples: travel visa rules, hotel policies, destination guides
- Where Bedrock Knowledge Base fits in our architecture

**V7.2 — Vectors + Semantic Search**
- Embedding: text → fixed-length number array that captures meaning
- Semantic similarity: "cheap hotel" ≈ "budget accommodation" in vector space
- Cosine similarity: measuring distance, nearest-neighbour search
- Why semantic beats keyword search for travel guides

**V7.3 — AWS Setup + Knowledge Base**
- Services involved: S3 + Bedrock KB + Titan Embeddings V2 + OpenSearch Serverless
- IAM: add `BedrockKnowledgeBase` permissions, enable Titan Embeddings V2 in model access
- AWS Console: create Knowledge Base — name, IAM role, embedding model, chunking config
- Note the `BEDROCK_KB_ID` — needed in `.env`

**V7.4 — S3 Bucket Setup**
- S3 as document source: PDFs, `.txt`, HTML all supported by Bedrock
- Create bucket, block public access, add bucket policy for Bedrock read access
- Connect S3 bucket as the data source in the Knowledge Base console
- Note the `BEDROCK_DS_ID` and `S3_BUCKET_NAME` for `.env`

**V7.5 — Upload Content + Sync**
- The 5 travel guide documents in `rag-docs/`: destination facts, visa rules, packing tips
- Upload via `rag-docs/upload_docs.py` script using boto3
- Start ingestion job in Bedrock console — watch progress, explain chunking
- Test retrieval directly in KB console: query → see returned chunks

**V7.6 — Model Call with RAG**
- Two APIs: `Retrieve` (chunks only) vs `RetrieveAndGenerate` (chunks + LLM answer)
- `retrieve_and_generate()` in `bedrock.py`: `knowledgeBaseId`, `modelArn`, query, citations
- `search_travel_guides` MCP tool calling this function — graceful fallback if KB not configured
- Test via MCP Inspector and full agent: "What are the visa requirements for Japan?"

---

## Section 8 — Agent III: Memory + Guardrails + Traceability
*5 videos · 37 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 8.1 | Short-Term Memory | Coding | 8 min |
| 8.2 | Long-Term Memory | Coding | 9 min |
| 8.3 | Guardrails: Concept + Implementation | Slides + Coding | 9 min |
| 8.4 | Bedrock Invocation Logging + CloudWatch | Slides + Console + Coding | 7 min |
| 8.5 | Full Agent Demo | Demo | 6 min |

**V8.1 — Short-Term Memory**
- Checkpointer concept: `thread_id` → restore full state → agent remembers the conversation
- Add `AsyncSqliteSaver` to `build_graph()`: one-line change to `.compile(checkpointer=checkpointer)`
- `--user` flag in `main.py`: different users get separate threads
- Test: ask "Paris hotels" → follow up "What about Rome?" — context retained
- Open `memory.db` in a DB viewer, show checkpoint rows

**V8.2 — Long-Term Memory**
- Short-term vs long-term: conversation history vs curated facts across sessions
- `memory.py`: `load_facts(user_id)` reads from `user_facts` SQLite table
- `save_facts(user_id, messages)`: Nova Micro extracts preferences, merges, persists
- Inject facts into system prompt via `build_system_prompt(user_facts)`
- Demo: "I prefer budget hotels" → quit → new session → agent knows without being told

**V8.3 — Guardrails: Concept + Implementation**
- What guardrails do: content filters, topic blocks, PII masking — travel agent use cases
- AWS Console: create guardrail — `FinancialAdvice` topic block, content filters, PII anonymise
- `get_or_create_guardrail()` in `bedrock.py`: idempotent, safe to call at startup
- Wire `guardrailConfig` into `call_bedrock()` via `BEDROCK_GUARDRAIL_ID` env var
- Test: "What should I invest my savings in?" → blocked with custom message

**V8.4 — Bedrock Invocation Logging + CloudWatch**
- Why traceability matters: debugging, cost control, compliance all need invocation records
- AWS Console: enable Bedrock Invocation Logging → route to CloudWatch Logs
- What gets captured: model ID, prompt, response, token counts, latency, request ID
- `log_usage()` in `bedrock.py`: prints model + token counts + estimated cost per call
- CloudWatch Logs Insights: live queries — cost per session, error rate, most-called models

**V8.5 — Full Agent Demo**
- All features active: short-term memory + long-term memory + RAG + guardrails + tracing + MCP
- Multi-turn travel planning conversation in the terminal
- Recap everything built, preview the React UI section

---

## Section 9 — React UI + WebSocket Streaming
*5 videos · 38 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 9.1 | Project Setup + WebSocket Endpoint | Coding | 8 min |
| 9.2 | Build Chat Components | Coding | 9 min |
| 9.3 | Build the useAgent Hook | Coding | 8 min |
| 9.4 | Token-by-Token Streaming | Coding | 7 min |
| 9.5 | Local End-to-End Demo | Demo | 6 min |

**V9.1 — Project Setup + WebSocket Endpoint**
- Why WebSocket over SSE: full-duplex, persistent connection, better for multi-turn chat
- `npm create vite@latest ui -- --template react-ts`
- `call_bedrock_stream()` in `bedrock.py`: sync generator over Bedrock `converse_stream` API
  — yields `(token | tool_start | tool_input | tool_end | stop)` events
- `api.py`: FastAPI app, `@app.websocket("/ws/chat")`, CORS middleware
- Install `fastapi uvicorn[standard] websockets` into agent project

**V9.2 — Build Chat Components**
- Component tree: `App` → `ChatWindow` → `MessageList` + `ToolPanel` + `InputBar`
- `MessageList`: user bubble (right) vs assistant bubble (left), blinking cursor while streaming
- `InputBar`: auto-grow textarea, Enter to send, spinner icon while waiting
- `ToolPanel`: shows MCP tool name + input + result during each turn, hidden otherwise
- `ChatWindow`: wires all components, connection badge in header

**V9.3 — Build the useAgent Hook**
- Hook responsibilities: `messages`, `toolEvents`, `isStreaming`, `isConnected`, `sendMessage()`
- WebSocket lifecycle: `connect()`, `onopen`, `onmessage`, `onclose` with auto-reconnect
- `handleFrame()`: routes each JSON frame type to the right state update
- Token accumulation: append each token to the last assistant message for the typewriter effect
- Stable `user_id` persisted in `localStorage`

**V9.4 — Token-by-Token Streaming**
- Server side: `_stream_turn()` in `api.py` — the full loop
  1. Append user message to LangGraph state (`as_node="__start__"`)
  2. Stream from Bedrock → send token frames over WebSocket
  3. If tool calls: execute via MCP, send `tool_call` + `tool_result` frames, loop back
  4. Send `done` frame when LLM gives a text-only response
- `as_node` on `aupdate_state`: why it is required when the graph has multiple nodes
- Client side: token frames arrive → `useAgent` appends to last assistant message → React re-renders

**V9.5 — Local End-to-End Demo**
- Full local stack: React UI → FastAPI WebSocket → LangGraph → Bedrock → MCP → Travel API
- Live demo: "Plan a 5-day trip to Tokyo under $3000" — streaming, tool calls visible in ToolPanel
- Show terminal logs for all three services side-by-side
- Recap the full build, preview the Deployment section

---

## Section 10 — Deployment to AWS
*9 videos · 56 min*

| # | Title | Type | Duration |
|---|---|---|---|
| 10.1 | Deployment Architecture + Docker | Slides + Coding | 8 min |
| 10.2 | Local Multi-Container Test with docker-compose | Demo | 6 min |
| 10.3 | ECR — Create Repos + Push Images | Console + Terminal | 6 min |
| 10.4 | IAM — Execution Role + Task Role | Console | 6 min |
| 10.5 | Secrets Manager — Store Credentials | Console | 5 min |
| 10.6 | ECS Cluster + Deploy Travel API | Console | 7 min |
| 10.7 | ALB + Deploy Agent API (WebSocket) | Console | 8 min |
| 10.8 | Deploy React UI to S3 + CloudFront | Console + Terminal | 7 min |
| 10.9 | Production End-to-End Demo | Demo | 6 min |

**V10.1 — Deployment Architecture + Docker**
- Why ECS Fargate for the agent: WebSocket needs a persistent process — Lambda won't work
- `travel-api/Dockerfile`: `python:3.11-slim` + uv, serve on port 9000
- `agent/Dockerfile`: build context = repo root — bundles `agent/` + `mcp-server/` together
  because MCPClient spawns the MCP server as a subprocess
- `ui/Dockerfile`: two-stage build — Node builds, nginx:alpine serves (~25 MB final image)
- Dependency layer caching trick: copy `pyproject.toml` first, then source

**V10.2 — Local Multi-Container Test with docker-compose**
- `docker-compose.yml`: three services — travel-api, agent, ui
- Key lesson: inside Docker, services talk by service name not localhost
  → `TRAVEL_API_URL=http://travel-api:9000` (not `localhost:9000`)
- `docker compose up --build` — all three services in one command
- `docker compose logs -f agent` — tail live logs
- Verify: open `http://localhost:8080`, send a test message

**V10.3 — ECR — Create Repos + Push Images**
- Console: ECR → Create repository × 3 (`travel-api`, `agent-service`, `travel-ui`)
- Portal shows **View push commands** — copy the exact 4 commands per repo
- The agent build command: must add `-f agent/Dockerfile` and run from repo root
- Verify: each repo shows a `latest` tag in ECR after push

**V10.4 — IAM — Execution Role + Task Role**
- Two roles: `ecsTaskExecutionRole` (pull images, write logs) and `agentTaskRole` (call Bedrock)
- `ecsTaskExecutionRole`: attach managed policy `AmazonECSTaskExecutionRolePolicy`
- `agentTaskRole`: create inline policy — `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`,
  `bedrock-agent-runtime:RetrieveAndGenerate`, `secretsmanager:GetSecretValue`
- Principle of least privilege: resource ARNs locked to specific Nova Micro + Nova Lite models

**V10.5 — Secrets Manager — Store Credentials**
- Why: never bake credentials into Docker images — ECS pulls them at container start
- Console: store three secrets — `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `BEDROCK_KB_ID`
- Secret naming convention: `travel-concierge/<VAR_NAME>` for easy IAM scoping
- Copy the full ARN of each secret — needed in the task definition

**V10.6 — ECS Cluster + Deploy Travel API**
- Create cluster: ECS → Clusters → `travel-concierge` → Fargate infrastructure
- Create CloudWatch log groups: `/ecs/travel-api` and `/ecs/agent-service`
- Register travel-api task definition via the console JSON editor
- Create Fargate service: internal only (public IP OFF), security group allows port 9000 from VPC
- Note the private IP of the running task — used as `TRAVEL_API_URL` in the agent task def

**V10.7 — ALB + Deploy Agent API (WebSocket)**
- Create security groups: `agent-alb-sg` (public port 80) and `agent-service-sg` (port 8100 from ALB only)
- Create target group: IP type, port 8100, health check on `/`
- Create ALB: internet-facing, forward port 80 to target group
- **Set ALB idle timeout to 300 seconds** — default 60s drops long WebSocket conversations
- Register agent task definition: paste JSON with secret ARNs and travel-api private IP
- Create Fargate service: attach to ALB + target group (ECS registers the container IP automatically)
- Copy ALB DNS name — used to build the production UI

**V10.8 — Deploy React UI to S3 + CloudFront**
- Build with production URL: `VITE_WS_URL=ws://ALB-DNS/ws/chat npm run build`
  (`VITE_WS_URL` in the hook falls back to localhost — override at build time for production)
- Create S3 bucket: block all public access (CloudFront handles it)
- Create CloudFront distribution: OAC origin access, `index.html` as default root
- Custom error responses: 403 and 404 both return `/index.html` with HTTP 200 (SPA routing)
- Upload `dist/` via S3 drag-and-drop; set cache headers: `immutable` for assets, `no-cache` for `index.html`
- Copy bucket policy from CloudFront OAC banner → paste into S3 bucket policy

**V10.9 — Production End-to-End Demo**
- Open the CloudFront distribution URL — chat UI live on HTTPS
- Live demo: full travel planning conversation — streaming, tool calls, memory across refreshes
- Show CloudWatch logs tailing for both ECS services
- Teardown walkthrough: ordered deletion to avoid ongoing charges

---

## What You Will Learn

- Build a production AI agent using **LangGraph StateGraph** — nodes, edges, reducers, conditional routing
- Create an **MCP Server** in Python with tools and prompts; test live with the MCP Inspector
- Integrate **AWS Bedrock** (Nova Micro + Nova Lite) with model routing for cost control
- Wire the agent to the MCP server — dynamic tool discovery, tool calling, result handling
- Add **RAG** with Bedrock Knowledge Base, S3, and Titan Embeddings — grounded answers with source citations
- Add **short-term memory** (SqliteSaver checkpointer) and **long-term memory** (curated user facts across sessions)
- Apply **Bedrock Guardrails** — content filters, topic blocks, PII masking
- Enable **Bedrock Invocation Logging** — track cost, latency, and errors in CloudWatch
- Build a **React + TypeScript** streaming chat UI with real-time token rendering and live tool-call indicators
- Centralise all LLM prompts in a single `prompts.py` for easy maintenance and student reference
- **Deploy** the full stack to AWS using ECS Fargate, ALB, S3, and CloudFront — full portal walkthrough

## Requirements

- Python 3.11+
- Node.js 18+
- AWS account (free tier covers most sections; small charges for Bedrock API calls and ECS)
- Basic Python knowledge (functions, classes, async/await basics)
- Basic React knowledge (components and hooks)

## Tech Stack

| Layer | Technology |
|---|---|
| Agent + MCP Server | Python · FastMCP · LangGraph · boto3 |
| Data layer | FastAPI (Travel Data API) |
| LLM | AWS Bedrock — Amazon Nova Micro / Nova Lite |
| RAG | Bedrock Knowledge Base · S3 · Titan Embeddings V2 |
| Short-term memory | SQLite (LangGraph AsyncSqliteSaver) |
| Long-term memory | SQLite user_facts table |
| Guardrails | AWS Bedrock Guardrails |
| Streaming | Bedrock `converse_stream` API → WebSocket |
| UI | React · TypeScript · Vite |
| Deployment | Docker · ECS Fargate · ALB · S3 · CloudFront |
