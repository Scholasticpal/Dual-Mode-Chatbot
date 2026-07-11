"""Tool definitions for the dual-mode corporate assistant.

Embeddings, LLM, and database clients are lazily initialized on first
tool invocation, keeping imports side-effect-free for test collection.
"""

import re
from typing import Any, Dict

from langchain_core.tools import tool

from app.database import get_sql_db, get_supabase_client

_embeddings = None
_llm = None


def _get_embeddings():
    """Return the Gemini embeddings model, creating it on first call."""
    global _embeddings
    if _embeddings is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            output_dimensionality=768,
        )
    return _embeddings


def _get_llm():
    """Return the Gemini LLM instance, creating it on first call."""
    global _llm
    if _llm is None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        _llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
    return _llm


def extract_sql_query(raw_output: str) -> str:
    """Extract and sanitize an SQL query from raw LLM output.

    Handles the 'Question: ... SQLQuery: ...' prefix format,
    markdown code blocks, and pass-through for clean queries.

    Args:
        raw_output: Raw string from the SQL query chain.

    Returns:
        Cleaned SQL query string.
    """
    sql_query = raw_output

    if "SQLQuery:" in sql_query:
        sql_query = sql_query.split("SQLQuery:")[-1]

    match = re.search(r"(?i)SELECT\s+.*", sql_query, re.DOTALL)
    if match:
        return match.group(0).replace("```sql", "").replace("```", "").strip()
    return sql_query.replace("```sql", "").replace("```", "").strip()


def format_rag_results(data: list[dict]) -> str:
    """Format Supabase RPC response data into a readable citation string.

    Args:
        data: List of dicts with 'content' and 'source_doc' keys.

    Returns:
        Formatted multi-section string, or a fallback message if empty.
    """
    if not data:
        return "No relevant policy documents found."

    formatted_results = []
    for item in data:
        content = item.get("content", "").strip()
        source = item.get("source_doc", "Unknown Source")
        formatted_results.append(f"Source: {source}\nContent: {content}\n---")

    return "\n".join(formatted_results)


@tool
async def search_policies(query: str) -> str:
    """Perform a semantic search across company policy documents in Supabase.

    Args:
        query: Natural language query string.

    Returns:
        Formatted string containing source document names and relevant text sections,
        or a fallback message if no relevant documents are found.
    """
    try:
        embeddings = _get_embeddings()
        db = get_supabase_client()

        query_embedding = await embeddings.aembed_query(query)

        response = db.rpc(
            "match_document_sections",
            {"query_embedding": query_embedding, "match_threshold": 0.6, "match_count": 5},
        ).execute()

        return format_rag_results(response.data)
    except Exception as e:
        return f"Error occurred while searching policies: {str(e)}"


@tool
async def query_orders(query: str) -> Dict[str, Any]:
    """Translate natural language to SQL and execute it against the orders table.

    Args:
        query: Natural language query about order status, revenue, or customer data.

    Returns:
        Dictionary containing the raw SQL execution results and the generated query string.
    """
    try:
        from langchain.chains import create_sql_query_chain

        llm = _get_llm()
        sql_db = get_sql_db()

        chain = create_sql_query_chain(llm, sql_db)
        sql_query = await chain.ainvoke({"question": query})

        clean_query = extract_sql_query(sql_query)
        result = sql_db.run(clean_query)

        return {"result": result, "executed_sql": clean_query}
    except Exception as e:
        return {
            "error": f"Error occurred while querying orders database: {str(e)}",
            "executed_sql": locals().get("clean_query", "Query not generated"),
        }
