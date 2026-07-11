import asyncio

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.tools import query_orders, search_policies

load_dotenv()

async def main():
    llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0)
    memory = MemorySaver()
    agent = create_react_agent(model=llm, tools=[query_orders, search_policies], checkpointer=memory)

    config = {"configurable": {"thread_id": "1"}}

    print("Run 1")
    async for event in agent.astream_events({"messages": [("user", "Check the status of my orders (Name: Arjun Desai)")]}, config=config, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content and isinstance(chunk.content, str):
                print(chunk.content, end="", flush=True)
    print("\n")

    print("Run 2")
    async for event in agent.astream_events({"messages": [("user", "what are they?")]}, config=config, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content and isinstance(chunk.content, str):
                print(chunk.content, end="", flush=True)
    print("\n")

asyncio.run(main())
