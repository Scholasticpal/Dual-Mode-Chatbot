import asyncio
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool

load_dotenv()

@tool
def get_weather(location: str) -> str:
    """Get the current weather in a given location."""
    return f"The weather in {location} is sunny and 75 degrees."

async def test_model(model_name: str):
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0, api_version="v1", max_retries=0)
    llm_with_tools = llm.bind_tools([get_weather])
    print(f"\n--- Testing {model_name} (v1) ---")
    try:
        response = await llm_with_tools.ainvoke("What is the weather in Tokyo?")
        print(f"SUCCESS: {model_name} -> Tool Calls: {response.tool_calls}")
    except Exception as e:
        print(f"FAILED: {model_name} -> {type(e).__name__}: {e}")

async def main():
    await test_model("gemini-2.5-flash")
    await test_model("gemini-1.5-flash-8b")

if __name__ == "__main__":
    asyncio.run(main())
