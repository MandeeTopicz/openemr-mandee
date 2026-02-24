"""
CareTopicz Agent Service - LLM reasoning node.

Calls Claude to generate a response from the conversation messages.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage

from app.agent.prompts.system import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.config import settings


def create_model():
    """Create Claude model instance."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is required. Set it in .env or environment.")
    return ChatAnthropic(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        temperature=0,
    )


def reasoning_node(state: AgentState) -> dict:
    """
    Reasoning node: call Claude with messages, return assistant response.
    """
    model = create_model()
    messages = list(state.get("messages", []))

    # Prepend system prompt
    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    response = model.invoke(full_messages)
    return {"messages": [response]}
