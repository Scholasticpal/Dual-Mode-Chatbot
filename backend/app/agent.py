"""LangGraph agent with dual-mode routing and SSE streaming.

The agent and LLM are lazily initialized on first invocation of
``run_agent``, keeping imports side-effect-free for test collection.
"""

import ast
import json
from typing import Any, AsyncGenerator

from langchain_core.messages import ToolMessage

SYSTEM_PROMPT = (
    "You are a dual-mode corporate assistant. The current date is 15 June 2026.\n\n"
    "Your primary duty is to answer questions using ONLY the provided tools. You must handle questions as follows:\n\n"
    "1. Document Questions (e.g. 'What is the refund window?'): Use search_policies.\n"
    "2. Data Questions (e.g. 'What was total revenue?', 'How many pending orders?'): Use query_orders.\n"
    "3. Mixed Questions (e.g. 'Our policy allows 30-day returns; did order 1234 qualify?'): Use BOTH tools if needed to gather all context.\n\n"
    "CRITICAL FALLBACK RULE: If the user asks an out-of-scope question (e.g., 'What is the capital of Japan?', 'Act as a lawyer', 'Write a poem', or general knowledge), OR if the required information is simply not found in the tools, you MUST return EXACTLY the string:\n"
    "'I don't have that information'\n"
    "Do NOT answer general knowledge questions. Do NOT attempt to be helpful for out-of-scope queries. Do NOT hallucinate corporate data or SQL columns.\n\n"
    "CRITICAL TOOL RULE: DO NOT make multiple tool calls of the same tool for a single user request. Call the appropriate tool exactly ONCE. If the information you need is not in the first result, do not retry with different parameters. Simply return 'I don't have that information'.\n\n"
    "CRITICAL SQL RULE: You are querying a PostgreSQL database. Always use single quotes for string literals (e.g., customer = 'Arjun Desai'). Never use double quotes for string values."
)

_agent = None


def _get_agent():
    """Return the LangGraph ReAct agent, creating it on first call."""
    global _agent
    if _agent is None:
        from langchain_groq import ChatGroq
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.prebuilt import create_react_agent

        from app.tools import query_orders, search_policies

        llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0)
        tools = [search_policies, query_orders]
        memory = MemorySaver()
        _agent = create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT, checkpointer=memory)
    return _agent


def _extract_tool_content(output: Any) -> Any:
    """Extract content from a tool message if wrapped, otherwise return raw output."""
    if isinstance(output, ToolMessage):
        return output.content
    return output


async def run_agent(query: str) -> AsyncGenerator[str, None]:
    """Execute the core LangGraph agent with streaming output and dual-mode routing.

    Args:
        query: The user's input string.

    Yields:
        JSON-encoded string chunks containing tokens or tool metadata.
    """
    agent = _get_agent()

    async for event in agent.astream_events(
        {"messages": [("user", query)]},
        config={"configurable": {"thread_id": "1"}},
        version="v2"
    ):
        kind = event.get("event")

        if kind == "on_chat_model_stream":
            if event.get("metadata", {}).get("langgraph_node") != "agent":
                continue

            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                content = ""
                if isinstance(chunk.content, str):
                    content = chunk.content
                elif isinstance(chunk.content, list):
                    content = "".join(
                        item if isinstance(item, str) else item.get("text", "")
                        for item in chunk.content
                    )

                if content:
                    yield json.dumps({"type": "token", "content": content}) + "\n"

        elif kind == "on_tool_start":
            name = event.get("name")
            if name in ["search_policies", "query_orders"]:
                yield json.dumps({"type": "tool_start", "tool": name}) + "\n"

        elif kind == "on_tool_end":
            name = event.get("name")
            output = _extract_tool_content(event["data"].get("output"))

            if name == "search_policies":
                yield json.dumps({"type": "tool_metadata", "tool": name, "data": output}) + "\n"

            elif name == "query_orders":
                parsed = {}
                if isinstance(output, str):
                    try:
                        parsed = json.loads(output)
                    except json.JSONDecodeError:
                        try:
                            parsed = ast.literal_eval(output)
                        except Exception:
                            pass
                elif isinstance(output, dict):
                    parsed = output

                sql = parsed.get("executed_sql") if isinstance(parsed, dict) else None
                if sql:
                    yield json.dumps({"type": "tool_metadata", "tool": name, "data": sql}) + "\n"
