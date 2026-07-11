"""Unit tests for the tool logic (SQL extraction, RAG formatting) with mocked externals."""

import pytest

from app.tools import extract_sql_query, format_rag_results


@pytest.mark.unit
class TestSQLExtraction:
    """Tests for the SQL query extraction/sanitization logic."""

    def test_clean_query_passes_through(self, mock_sql_chain_output_clean):
        result = extract_sql_query(mock_sql_chain_output_clean)
        assert result == "SELECT * FROM orders WHERE customer = 'Arjun Desai'"

    def test_extracts_from_question_prefix(self, mock_sql_chain_output_with_prefix):
        result = extract_sql_query(mock_sql_chain_output_with_prefix)
        assert result.startswith("SELECT")
        assert "Arjun Desai" in result
        assert "Question:" not in result

    def test_strips_markdown_code_blocks(self, mock_sql_chain_output_with_markdown):
        result = extract_sql_query(mock_sql_chain_output_with_markdown)
        assert "```" not in result
        assert result.startswith("SELECT")

    def test_handles_empty_string(self):
        result = extract_sql_query("")
        assert result == ""

    def test_handles_no_select(self):
        result = extract_sql_query("INSERT INTO orders VALUES (1, 'test')")
        assert "INSERT" in result

    def test_injection_attempt_produces_select(self):
        raw = "SQLQuery: SELECT * FROM orders WHERE customer = 'Robert''); DROP TABLE orders;--'"
        result = extract_sql_query(raw)
        assert result.startswith("SELECT")


@pytest.mark.unit
class TestRAGFormatting:
    """Tests for the RAG result formatting logic."""

    def test_formats_results_correctly(self, mock_supabase_rpc_response):
        result = format_rag_results(mock_supabase_rpc_response)
        assert "Source: hr_leave_policy.pdf" in result
        assert "21 days" in result
        assert "---" in result

    def test_empty_results_return_fallback(self, mock_empty_supabase_response):
        result = format_rag_results(mock_empty_supabase_response)
        assert result == "No relevant policy documents found."

    def test_missing_source_uses_fallback(self):
        data = [{"content": "Some policy text"}]
        result = format_rag_results(data)
        assert "Unknown Source" in result

    def test_multiple_results_separated(self, mock_supabase_rpc_response):
        result = format_rag_results(mock_supabase_rpc_response)
        sections = result.split("---")
        assert len(sections) >= 2
