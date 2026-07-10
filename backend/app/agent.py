import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
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
    model="gemini-1.5-flash",
    temperature=0
)

tools = [search_policies, query_orders]

agent = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier=SYSTEM_PROMPT
)

async def run_agent(query: str) -> AsyncGenerator[str, None]:
    """Execute the agent and yield string tokens sequentially for streaming."""
    async for event in agent.astream_events(
        {"messages": [("user", query)]},
        version="v2"
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                if isinstance(chunk.content, str):
                    yield chunk.content
                elif isinstance(chunk.content, list):
                    for item in chunk.content:
                        if isinstance(item, str):
                            yield item
                        elif isinstance(item, dict) and "text" in item:
                            yield item["text"]
