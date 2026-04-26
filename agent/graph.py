from langgraph.graph import StateGraph, END

from state import AgentState
from nodes import classify_node, llm_node

# ── Main agent graph ──────────────────────────────────────────────────────────
# Section 5 graph: classify -> llm -> END
# Tool calling is added in Section 6 once MCP integration is in place.
# The MCP client will supply tool specs dynamically — no hardcoding needed.

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("llm",      llm_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "llm")
    graph.add_edge("llm", END)

    return graph.compile()


# Compiled graph — imported by main.py
agent = build_graph()
