from langgraph.graph import StateGraph, END

from state import AgentState
from nodes import classify_node, llm_node, tool_node

# ── Routing helper ────────────────────────────────────────────────────────────
# After llm responds, check whether it requested a tool call.
# If yes -> route to tool_node to execute via MCP, then loop back to llm.
# If no  -> direct answer, we're done.

def _should_use_tool(state: AgentState) -> str:
    last = state["messages"][-1]
    content = last.get("content", [])
    if any("toolUse" in block for block in content):
        return "tool"
    return "end"


# ── Main agent graph ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("llm",      llm_node)
    graph.add_node("tool",     tool_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "llm")

    # After llm: call a tool or finish
    graph.add_conditional_edges(
        "llm",
        _should_use_tool,
        {"tool": "tool", "end": END},
    )

    # After tool execution: back to llm so it can use the result
    graph.add_edge("tool", "llm")

    return graph.compile()


# Compiled graph — imported by main.py
agent = build_graph()
