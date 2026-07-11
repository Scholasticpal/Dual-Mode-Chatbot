"""Unit tests for the FastAPI application endpoints."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.unit
class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    async def test_health_returns_ok(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.unit
class TestChatEndpoint:
    """Tests for the /api/chat endpoint."""

    async def test_chat_returns_streaming_response(self):
        """Verify the endpoint returns an SSE stream with correct content type."""

        async def mock_agent(query):
            yield json.dumps({"type": "token", "content": "Hello"}) + "\n"

        with patch("app.main.run_agent", side_effect=mock_agent):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/chat",
                    json={"message": "hi"},
                )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            assert "data: " in response.text

    async def test_chat_rejects_empty_message(self):
        """Verify the endpoint rejects a request with no message field."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/chat", json={})
        assert response.status_code == 422

    async def test_chat_handles_agent_exception(self):
        """Verify the endpoint returns an error payload if the agent crashes."""

        async def mock_agent_crash(query):
            raise RuntimeError("LLM quota exceeded")
            yield  # noqa: unreachable — required to make this an async generator

        with patch("app.main.run_agent", side_effect=mock_agent_crash):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/chat",
                    json={"message": "test"},
                )
            assert response.status_code == 200
            assert "error" in response.text

    async def test_chat_sse_format(self):
        """Verify each line follows the SSE 'data: {...}' format."""

        async def mock_agent(query):
            yield json.dumps({"type": "token", "content": "Word1"}) + "\n"
            yield json.dumps({"type": "token", "content": "Word2"}) + "\n"

        with patch("app.main.run_agent", side_effect=mock_agent):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/chat",
                    json={"message": "test"},
                )
            lines = [line for line in response.text.strip().split("\n") if line.strip()]
            for line in lines:
                assert line.startswith("data: "), f"Line does not follow SSE format: {line}"
