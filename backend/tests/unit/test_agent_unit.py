"""Unit tests for agent helper functions and prompt integrity."""

import pytest
from langchain_core.messages import ToolMessage


@pytest.mark.unit
class TestExtractToolContent:
    """Tests for the _extract_tool_content helper."""

    def test_extracts_from_tool_message(self):
        from app.agent import _extract_tool_content

        msg = ToolMessage(content="Policy text here", tool_call_id="abc123")
        assert _extract_tool_content(msg) == "Policy text here"

    def test_returns_raw_string(self):
        from app.agent import _extract_tool_content

        assert _extract_tool_content("raw string") == "raw string"

    def test_returns_raw_dict(self):
        from app.agent import _extract_tool_content

        data = {"result": "some data", "executed_sql": "SELECT 1"}
        assert _extract_tool_content(data) == data

    def test_returns_none(self):
        from app.agent import _extract_tool_content

        assert _extract_tool_content(None) is None


@pytest.mark.unit
class TestSystemPrompt:
    """Tests that the SYSTEM_PROMPT contains critical routing keywords."""

    def test_prompt_contains_dual_mode(self):
        from app.agent import SYSTEM_PROMPT

        assert "dual-mode" in SYSTEM_PROMPT.lower()

    def test_prompt_contains_date_anchor(self):
        from app.agent import SYSTEM_PROMPT

        assert "15 June 2026" in SYSTEM_PROMPT

    def test_prompt_contains_tool_restriction(self):
        from app.agent import SYSTEM_PROMPT

        assert "ONCE" in SYSTEM_PROMPT

    def test_prompt_contains_hallucination_guard(self):
        from app.agent import SYSTEM_PROMPT

        assert "I don't have that information" in SYSTEM_PROMPT

    def test_prompt_contains_persona_guard(self):
        from app.agent import SYSTEM_PROMPT

        lower = SYSTEM_PROMPT.lower()
        assert "act as a lawyer" in lower or "write a poem" in lower
