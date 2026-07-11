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
async def test_document_question():
    """Test RAG document question handling."""
    response = await _get_agent().ainvoke({"messages": [HumanMessage(content="What is the refund window?")]}, config={"configurable": {"thread_id": "test_doc"}})
    content = _get_text(response["messages"][-1].content).lower()
    assert "i don't have that information" not in content
    assert len(content) > 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_question():
    """Test SQL data question handling."""
    response = await _get_agent().ainvoke({"messages": [HumanMessage(content="How many orders are pending?")]}, config={"configurable": {"thread_id": "test_data"}})
    content = _get_text(response["messages"][-1].content).lower()
    assert "i don't have that information" not in content
    assert len(content) > 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mixed_question():
    """Test Mixed question handling."""
    response = await _get_agent().ainvoke({"messages": [HumanMessage(content="Our policy allows 30-day returns; did order ORD-011 qualify?")]}, config={"configurable": {"thread_id": "test_mixed"}})
    content = _get_text(response["messages"][-1].content).lower()
    assert "i don't have that information" not in content
    assert len(content) > 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_out_of_scope_question():
    """Test Fallback out of scope question handling."""
    response = await _get_agent().ainvoke({"messages": [HumanMessage(content="What is the capital of Japan?")]}, config={"configurable": {"thread_id": "test_out"}})
    content = _get_text(response["messages"][-1].content).lower()
    assert "i don't have that information" in content
