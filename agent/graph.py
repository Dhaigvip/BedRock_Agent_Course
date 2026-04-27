from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from state import AgentState
from nodes import classify_node, llm_node, tool_node

# ── Routing helper ────────────────────────────────────────────────────────────

def _should_use_tool(state: AgentState) -> str:
    last = state["messages"][-1]
    content = last.get("content", [])
    if any("toolUse" in block for block in content):
        return "tool"
    return "end"


# ── Main agent graph ──────────────────────────────────────────────────────────

def build_graph(checkpointer=None) -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("llm",      llm_node)
    graph.add_node("tool",     tool_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "llm")

    graph.add_conditional_edges(
        "llm",
        _should_use_tool,
        {"tool": "tool", "end": END},
    )

    graph.add_edge("tool", "llm")

    # checkpointer=None → no persistence (default, backwards compatible)
    # checkpointer=AsyncSqliteSaver → full conversation memory per thread_id
    return graph.compile(checkpointer=checkpointer)
