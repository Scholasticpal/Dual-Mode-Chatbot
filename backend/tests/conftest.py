"""Shared fixtures for both unit and integration tests."""

import pytest


@pytest.fixture
def mock_supabase_rpc_response():
    """Returns a realistic Supabase RPC response for policy search."""
    return [
        {
            "content": "Employees are entitled to 21 days of annual paid leave per calendar year.",
            "source_doc": "hr_leave_policy.pdf",
            "similarity": 0.82,
        },
        {
            "content": "Unused leave may be carried forward up to a maximum of 5 days.",
            "source_doc": "hr_leave_policy.pdf",
            "similarity": 0.74,
        },
    ]


@pytest.fixture
def mock_empty_supabase_response():
    """Returns an empty Supabase RPC response."""
    return []


@pytest.fixture
def mock_sql_chain_output_clean():
    """Returns a clean SQL query string as Gemini might produce."""
    return "SELECT * FROM orders WHERE customer = 'Arjun Desai'"


@pytest.fixture
def mock_sql_chain_output_with_prefix():
    """Returns a SQL query string with the Question/SQLQuery prefix Gemini sometimes adds."""
    return (
        "Question: What are the orders for Arjun Desai?\n"
        "SQLQuery: SELECT * FROM orders WHERE customer = 'Arjun Desai'"
    )


@pytest.fixture
def mock_sql_chain_output_with_markdown():
    """Returns a SQL query wrapped in markdown code blocks."""
    return "```sql\nSELECT * FROM orders WHERE customer = 'Arjun Desai'\n```"
