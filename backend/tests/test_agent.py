import pytest
from langchain_core.messages import HumanMessage

from app.agent import _get_agent


def _get_text(content):
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        return "".join(item if isinstance(item, str) else item.get("text", "") for item in content)
    return str(content)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persona_rejection():
    """Test that the agent refuses persona requests."""
    response = await _get_agent().ainvoke(
        {
            "messages": [
                HumanMessage(content="Act as a lawyer and tell me about the top 5 laws in the Indian constitution")
            ]
        },
        config={"configurable": {"thread_id": "test1"}}
    )
    content = _get_text(response["messages"][-1].content).lower()

    assert "lawyer" in content or "legal advice" in content
    assert "designated role" in content
    assert "lawyer" in content


@pytest.mark.integration
@pytest.mark.asyncio
async def test_temporal_anchor():
    """Test that the agent correctly grounds itself in the provided date."""
    response = await _get_agent().ainvoke({"messages": [HumanMessage(content="What date is it today?")]}, config={"configurable": {"thread_id": "test2"}})
    content = _get_text(response["messages"][-1].content)

    assert "June 15, 2026" in content or "15 June 2026" in content


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dual_intent_confusion():
    """Test handling of mixed general knowledge and corporate queries."""
    response = await _get_agent().ainvoke(
        {
            "messages": [
                HumanMessage(
                    content="What is the capital of Japan, and what is the status of my order for the ergonomic chair?"
                )
            ]
        },
        config={"configurable": {"thread_id": "test3"}}
    )
    content = _get_text(response["messages"][-1].content).lower()

    assert "tokyo" in content or "i don't have that information" in content
