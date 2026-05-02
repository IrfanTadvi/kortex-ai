"""
SQL Query Generation Agent
Converts natural language questions to SQL queries for the real application database.
Uses rule-based NL-to-SQL for safe, instant execution.
"""

from typing import Dict, Any, List
import re
import sqlite3
from loguru import logger


# Real database schema
REAL_SCHEMA = """
Database Schema (SQLite):
- documents (id, filename, file_type, file_size, source, status, chunk_count, doc_metadata, created_at, updated_at)
- chat_sessions (id, title, role, created_at, updated_at)
- chat_messages (id, session_id, role, content, sources, confidence_score, msg_metadata, created_at)
- query_logs (id, session_id, query, rewritten_query, retrieval_method, num_chunks_retrieved, confidence_score, latency_ms, feedback, created_at)
- action_logs (id, session_id, action_type, payload, status, result, created_at)
"""

DB_PATH = "data/knowledge_copilot.db"


class SQLGeneratorAgent:
    """
    Converts natural language queries to SQL and executes against the real app database.
    Only SELECT queries are allowed for safety.
    """

    def __init__(self):
        self.schema = REAL_SCHEMA

    async def process(self, query: str) -> Dict[str, Any]:
        """Process a natural language query into SQL and execute it."""
        query_lower = query.lower()

        # Generate SQL from natural language
        sql = self._generate_sql(query_lower)

        # Validate
        if not self._validate_sql(sql):
            return {
                "status": "error",
                "sql": sql,
                "results": [],
                "explanation": "Query failed safety validation. Only SELECT queries are allowed.",
                "row_count": 0,
            }

        # Execute against real database
        try:
            results = self._execute(sql)
            explanation = self._explain(query, results, sql)
            return {
                "status": "success",
                "sql": sql,
                "results": results,
                "explanation": explanation,
                "row_count": len(results),
            }
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return {
                "status": "error",
                "sql": sql,
                "results": [],
                "explanation": f"Execution error: {str(e)[:200]}",
                "row_count": 0,
            }

    def _generate_sql(self, query_lower: str) -> str:
        """Rule-based natural language to SQL conversion."""

        # Document queries
        if any(w in query_lower for w in ["document", "file", "upload", "pdf"]):
            if "how many" in query_lower or "count" in query_lower:
                return "SELECT COUNT(*) as total_documents, status FROM documents GROUP BY status"
            if "recent" in query_lower or "latest" in query_lower:
                return "SELECT filename, file_type, file_size, status, chunk_count, created_at FROM documents ORDER BY created_at DESC LIMIT 10"
            if "size" in query_lower or "largest" in query_lower:
                return "SELECT filename, file_size, chunk_count FROM documents ORDER BY file_size DESC LIMIT 10"
            return "SELECT filename, file_type, file_size, status, chunk_count, created_at FROM documents ORDER BY created_at DESC"

        # Chat/session queries
        if any(w in query_lower for w in ["chat", "session", "conversation"]):
            if "how many" in query_lower or "count" in query_lower:
                return "SELECT COUNT(*) as total_sessions, role FROM chat_sessions GROUP BY role"
            if "recent" in query_lower or "latest" in query_lower:
                return "SELECT id, title, role, created_at FROM chat_sessions ORDER BY created_at DESC LIMIT 10"
            if "message" in query_lower:
                return "SELECT cm.role, substr(cm.content, 1, 100) as content_preview, cm.confidence_score, cm.created_at FROM chat_messages cm ORDER BY cm.created_at DESC LIMIT 20"
            return "SELECT id, title, role, created_at FROM chat_sessions ORDER BY created_at DESC LIMIT 10"

        # Query/analytics queries
        if any(w in query_lower for w in ["query", "search", "analytics", "log"]):
            if "slow" in query_lower or "latency" in query_lower or "performance" in query_lower:
                return "SELECT query, latency_ms, confidence_score, created_at FROM query_logs ORDER BY latency_ms DESC LIMIT 10"
            if "confidence" in query_lower or "accurate" in query_lower:
                return "SELECT query, confidence_score, num_chunks_retrieved, created_at FROM query_logs ORDER BY confidence_score DESC LIMIT 10"
            if "how many" in query_lower or "count" in query_lower:
                return "SELECT COUNT(*) as total_queries, AVG(latency_ms) as avg_latency_ms, AVG(confidence_score) as avg_confidence FROM query_logs"
            if "recent" in query_lower or "latest" in query_lower:
                return "SELECT query, confidence_score, latency_ms, created_at FROM query_logs ORDER BY created_at DESC LIMIT 10"
            return "SELECT query, confidence_score, latency_ms, num_chunks_retrieved, created_at FROM query_logs ORDER BY created_at DESC LIMIT 10"

        # Action queries
        if any(w in query_lower for w in ["action", "activity"]):
            return "SELECT action_type, status, created_at FROM action_logs ORDER BY created_at DESC LIMIT 10"

        # Stats/summary queries
        if any(w in query_lower for w in ["stat", "summary", "overview", "dashboard"]):
            return """SELECT 
                (SELECT COUNT(*) FROM documents) as total_documents,
                (SELECT COUNT(*) FROM chat_sessions) as total_sessions,
                (SELECT COUNT(*) FROM chat_messages) as total_messages,
                (SELECT COUNT(*) FROM query_logs) as total_queries,
                (SELECT ROUND(AVG(latency_ms), 0) FROM query_logs) as avg_latency_ms,
                (SELECT ROUND(AVG(confidence_score)*100, 1) FROM query_logs) as avg_confidence_pct"""

        # Default: show overview
        return """SELECT 
            (SELECT COUNT(*) FROM documents) as total_documents,
            (SELECT COUNT(*) FROM chat_sessions) as total_sessions,
            (SELECT COUNT(*) FROM chat_messages) as total_messages,
            (SELECT COUNT(*) FROM query_logs) as total_queries,
            (SELECT ROUND(AVG(latency_ms), 0) FROM query_logs) as avg_latency_ms,
            (SELECT ROUND(AVG(confidence_score)*100, 1) FROM query_logs) as avg_confidence_pct"""

    def _validate_sql(self, sql: str) -> bool:
        """Validate SQL query for safety."""
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "EXEC"]
        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        if not sql_upper.strip().startswith("SELECT"):
            return False
        return True

    def _execute(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL against the real SQLite database."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            return results
        finally:
            conn.close()

    def _explain(self, query: str, results: List[Dict], sql: str) -> str:
        """Generate a simple explanation of the results."""
        count = len(results)
        if count == 0:
            return "No records found matching your query."
        if count == 1 and len(results[0]) > 3:
            # Summary/stats query
            return "Here's a summary of your knowledge base stats."
        return f"Found {count} records matching your query."
