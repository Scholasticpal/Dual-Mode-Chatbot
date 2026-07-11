import ast
import json
import os
from typing import AsyncGenerator, Any

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import create_react_agent

from app.tools import search_policies, query_orders

load_dotenv()

SYSTEM_PROMPT = (
    "The current operational timeline context is exactly 15 June 2026.\n\n"
    "If a request falls outside the boundaries of the provided schemas "
    "or corporate policies, you must return the exact string: "
    "'I don't have that information' "
    "with zero structural or content hallucination."
)

llm = ChatGoogleGenerativeAI(
    model="gemini-1.0-pro",
    temperature=0
)

tools = [search_policies, query_orders]

agent = create_react_agent(
    model=llm,
    tools=tools,
    messages_modifier=SYSTEM_PROMPT
)

def _extract_tool_content(output: Any) -> Any:
    if isinstance(output, ToolMessage):
        return output.content
    return output

async def run_agent(query: str) -> AsyncGenerator[str, None]:
    async for event in agent.astream_events(
        {"messages": [("user", query)]},
        version="v2"
    ):
        kind = event.get("event")
        
        if kind == "on_chat_model_stream":
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
