"""
CareTopicz Agent Service - LangGraph state machine.

Flow: input -> agent (LLM + tool selection) -> tools -> agent -> verifier -> output
Task 6: Verification layer (fact check, confidence, domain rules) gates responses.
"""

import time

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langsmith import traceable

from app.agent.nodes.reasoning import create_model
from app.agent.prompts.system import SYSTEM_PROMPT
from app.config import settings
from app.observability.metrics import (
    RequestMetrics,
    aggregate_token_usage,
    estimate_cost,
    update_langsmith_run_metadata,
)
from app.tools.registry import get_tools
from app.verification.verifier import verify_and_gate


def create_graph():
    """Build and compile the agent graph with tools."""
    model = create_model()
    tools = get_tools()
    model_with_tools = model.bind_tools(tools)

    graph = create_react_agent(
        model_with_tools,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
    return graph


# Singleton compiled graph
_graph = None


def get_graph():
    """Get or create the compiled graph."""
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph


def _extract_response_and_tool_results(messages: list) -> tuple[str, list[str]]:
    """Extract final AI response and tool result strings from message history."""
    response = ""
    tool_results: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            content = m.content if hasattr(m, "content") else str(m)
            if content:
                tool_results.append(content)
        elif isinstance(m, AIMessage):
            content = m.content if hasattr(m, "content") else ""
            if content and not getattr(m, "tool_calls", None):
                response = content
    return (response, tool_results)


@traceable(name="invoke_graph")
def invoke_graph(user_message: str, metrics: RequestMetrics | None = None) -> tuple[str, RequestMetrics]:
    """
    Run the graph with a user message and return the verified response plus metrics.
    Response passes through fact check, confidence scoring, and domain rules.
    """
    m = metrics or RequestMetrics()
    t_total = time.perf_counter()

    graph = get_graph()
    t_graph = time.perf_counter()
    result = graph.invoke(
        {"messages": [HumanMessage(content=user_message)]}
    )
    m.graph_ms = (time.perf_counter() - t_graph) * 1000

    messages = result.get("messages", [])
    response, tool_results = _extract_response_and_tool_results(messages)
    if not response:
        m.total_ms = (time.perf_counter() - t_total) * 1000
        return "I couldn't generate a response. Please try again.", m

    t_verif = time.perf_counter()
    verified = verify_and_gate(response, tool_results)
    m.verification_ms = (time.perf_counter() - t_verif) * 1000

    inp, out, total = aggregate_token_usage(messages)
    m.input_tokens = inp
    m.output_tokens = out
    m.total_tokens = total
    m.estimated_cost_usd = estimate_cost(
        inp, out, getattr(settings, "anthropic_model", "claude-sonnet-4-6")
    )
    m.total_ms = (time.perf_counter() - t_total) * 1000

    # Update LangSmith run metadata and capture run_id for feedback
    try:
        from langsmith.run_helpers import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree and run_tree.id:
            m.run_id = str(run_tree.id)
            update_langsmith_run_metadata(m.run_id, m.to_metadata())
    except Exception:
        pass

    return verified.response, m
