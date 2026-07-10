import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains import create_sql_query_chain

from app.database import db, sql_db

load_dotenv()

try:
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        output_dimensionality=768
    )
except Exception as e:
    raise RuntimeError(f"Failed to initialize Gemini embeddings: {e}")

try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
except Exception as e:
    raise RuntimeError(f"Failed to initialize Gemini LLM: {e}")


@tool
async def search_policies(query: str) -> str:
    """Semantic search across company policies."""
    try:
        query_embedding = await embeddings.aembed_query(query)
        
        response = db.rpc(
            "match_document_sections",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.5,
                "match_count": 5
            }
        ).execute()
        
        data = response.data
        if not data:
            return "No relevant policy documents found."
        
        formatted_results = []
        for item in data:
            content = item.get("content", "").strip()
            source = item.get("source_doc", "Unknown Source")
            formatted_results.append(f"Source: {source}\nContent: {content}\n---")
            
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error occurred while searching policies: {str(e)}"

@tool
async def query_orders(query: str) -> Dict[str, Any]:
    """Translate natural language to SQL and execute against the orders table."""
    try:
        chain = create_sql_query_chain(llm, sql_db)
        sql_query = await chain.ainvoke({"question": query})
        
        clean_query = sql_query.replace("```sql", "").replace("```", "").strip()
        result = sql_db.run(clean_query)
        
        return {
            "result": result,
            "executed_sql": clean_query
        }
    except Exception as e:
        return {
            "error": f"Error occurred while querying orders database: {str(e)}",
            "executed_sql": locals().get("clean_query", "Query not generated")
        }
