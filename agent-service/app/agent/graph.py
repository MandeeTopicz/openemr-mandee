"""
CareTopicz Agent Service - LangGraph state machine.

Flow: input -> agent (LLM + tool selection) -> tools -> agent -> verifier -> output
Task 6: Verification layer (fact check, confidence, domain rules) gates responses.
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.agent.nodes.reasoning import create_model
from app.agent.prompts.system import SYSTEM_PROMPT
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


def invoke_graph(user_message: str) -> str:
    """
    Run the graph with a user message and return the verified response.
    Response passes through fact check, confidence scoring, and domain rules.
    """
    graph = get_graph()
    result = graph.invoke(
        {"messages": [HumanMessage(content=user_message)]}
    )
    messages = result.get("messages", [])
    response, tool_results = _extract_response_and_tool_results(messages)
    if not response:
        return "I couldn't generate a response. Please try again."
    verified = verify_and_gate(response, tool_results)
    return verified.response
