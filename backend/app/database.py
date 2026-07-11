"""Lazy-initialized database clients for Supabase and PostgreSQL.

All connections are deferred until first use, allowing the module to be
imported safely during test collection without live credentials.
"""

import os

from dotenv import load_dotenv

load_dotenv()

_supabase_client = None
_sql_db_instance = None


def get_supabase_client():
    """Return the Supabase client, creating it on first call."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("Missing Supabase credentials in environment variables.")
        _supabase_client = create_client(url, key)
    return _supabase_client


def get_sql_db():
    """Return the LangChain SQLDatabase wrapper, creating it on first call."""
    global _sql_db_instance
    if _sql_db_instance is None:
        from langchain_community.utilities import SQLDatabase
        from sqlalchemy import create_engine

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("Missing DATABASE_URL in environment variables.")
        engine = create_engine(database_url)
        _sql_db_instance = SQLDatabase(engine)
    return _sql_db_instance
