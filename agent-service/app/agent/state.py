"""
CareTopicz Agent Service - Agent state schema for LangGraph.

Defines the shared state passed between graph nodes.
"""

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict, total=False):
    """State schema for the agent graph."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    patient_context: dict
    selected_tools: list[str]
    tool_results: list[dict]
    verification_status: str
    confidence_score: float
    citations: list[dict]
    retry_count: int
