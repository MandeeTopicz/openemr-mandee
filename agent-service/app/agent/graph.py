"""
CareTopicz Agent Service - LangGraph state machine.

Flow: input -> agent (LLM + tool selection) -> tools [with intermediate verification] -> agent -> verifier -> output
Task 6: Verification layer (fact check, confidence, domain rules) gates responses.
Task 3: Intermediate verification runs after each tool call (schema, domain rules, retry, fallback).
"""

import time

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent, ToolNode
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
from app.verification.tool_output_verifier import verify_tool_output
from app.verification.verifier import verify_and_gate

# Fallback when tool output fails verification and retry also fails
_TOOL_VERIFICATION_FALLBACK = (
    "[Tool result could not be verified. Proceeding with caution—please confirm with a clinician if needed.]"
)


def _wrap_tool_call_verified(request, execute):
    """
    Intermediate verification after each tool call: validate schema, domain rules.
    On failure: retry once, then return fallback message so the agent can continue.
    Records per-tool latency and success for GET /metrics.
    """
    import logging

    from app.observability.metrics import record_tool_call

    tool_name = request.tool_call.get("name", "?")
    t0 = time.perf_counter()
    result = execute(request)
    duration_ms = (time.perf_counter() - t0) * 1000

    if not isinstance(result, ToolMessage):
        record_tool_call(tool_name, duration_ms, False)
        return result
    if verify_tool_output(result.content or ""):
        record_tool_call(tool_name, duration_ms, True)
        return result
    logging.getLogger(__name__).info(
        "tool_output_verification_failed tool=%s (retrying once)",
        tool_name,
    )
    # Retry once
    t1 = time.perf_counter()
    retry_result = execute(request)
    duration_ms += (time.perf_counter() - t1) * 1000
    if isinstance(retry_result, ToolMessage) and verify_tool_output(retry_result.content or ""):
        record_tool_call(tool_name, duration_ms, True)
        return retry_result
    logging.getLogger(__name__).warning(
        "tool_output_verification_fallback tool=%s",
        tool_name,
    )
    record_tool_call(tool_name, duration_ms, False)
    return ToolMessage(
        tool_call_id=result.tool_call_id,
        content=_TOOL_VERIFICATION_FALLBACK,
        name=result.name or request.tool_call.get("name", "tool"),
    )


def create_graph():
    """Build and compile the agent graph with tools and intermediate verification."""
    model = create_model()
    tools = get_tools()
    model_with_tools = model.bind_tools(tools)

    tool_node = ToolNode(
        tools,
        wrap_tool_call=_wrap_tool_call_verified,
    )
    graph = create_react_agent(
        model_with_tools,
        tools=tool_node,
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


def _extract_tools_used(messages: list, max_summary_len: int = 120) -> list[dict]:
    """
    Extract tool name and brief summary for each tool call from message history.
    Returns list of {"name": str, "summary": str} in call order.
    """
    id_to_name: dict[str, str] = {}
    for m in messages:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tid = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                tname = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "tool")
                if tid:
                    id_to_name[tid] = tname or "tool"

    tools_used: list[dict] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            content = m.content if hasattr(m, "content") else str(m)
            tid = getattr(m, "tool_call_id", None)
            name = id_to_name.get(tid, "tool") if tid else "tool"
            summary = (content or "").strip()
            if len(summary) > max_summary_len:
                summary = summary[: max_summary_len - 3] + "..."
            tools_used.append({"name": name, "summary": summary or "Completed."})
    return tools_used


@traceable(name="invoke_graph")
def invoke_graph(user_message: str, metrics: RequestMetrics | None = None, history: list | None = None) -> tuple[str, RequestMetrics]:
    """
    Run the graph with a user message and return the verified response plus metrics.
    Response passes through fact check, confidence scoring, and domain rules.
    """
    m = metrics or RequestMetrics()
    t_total = time.perf_counter()

    graph = get_graph()
    t_graph = time.perf_counter()
    msgs = []
    if history:
        msgs.extend(history)
    msgs.append(HumanMessage(content=user_message))
    result = graph.invoke(
        {"messages": msgs}
    )
    m.graph_ms = (time.perf_counter() - t_graph) * 1000

    messages = result.get("messages", [])
    response, tool_results = _extract_response_and_tool_results(messages)
    tools_used = _extract_tools_used(messages)
    if not response:
        m.total_ms = (time.perf_counter() - t_total) * 1000
        return "I couldn't generate a response. Please try again.", m, tools_used

    t_verif = time.perf_counter()
    tool_names = [t["name"] for t in tools_used] if tools_used else []
    verified = verify_and_gate(response, tool_results, tools_used=tool_names)
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

    return verified.response, m, tools_used
