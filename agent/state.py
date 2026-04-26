import operator
from typing import Annotated
from typing_extensions import TypedDict
from bedrock import MODELS

# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Full conversation history.
    # operator.add means each update APPENDS to the list — never overwrites.
    messages: Annotated[list[dict], operator.add]

    # Which Bedrock model to use for the main LLM node.
    # No annotation = last-write-wins (the classifier sets this each turn).
    model_id: str

    # Bedrock toolSpec list fetched from MCP at startup.
    # Passed to every llm_node call so Bedrock knows what tools are available.
    # Last-write-wins — set once before the graph runs, never changes mid-turn.
    tools: list[dict]
