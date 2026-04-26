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
