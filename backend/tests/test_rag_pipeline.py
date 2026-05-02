"""
Tests for the RAG pipeline components.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock

# Test Document Processor
class TestDocumentProcessor:
    def test_clean_text(self):
        from app.core.document_processor import DocumentProcessor
        processor = DocumentProcessor()

        text = "  Hello   World!  \n\n  Test  "
        result = processor._clean_text(text)
        assert "  " not in result
        assert result == "Hello World! Test"

    def test_split_sentences(self):
        from app.core.document_processor import DocumentProcessor
        processor = DocumentProcessor()

        text = "First sentence. Second sentence. Third one here."
        sentences = processor._split_sentences(text)
        assert len(sentences) >= 1

    def test_semantic_chunk_basic(self):
        from app.core.document_processor import DocumentProcessor
        processor = DocumentProcessor()

        pages = ["This is a long text. " * 100]
        chunks = processor._semantic_chunk(pages, "test_doc", "upload", "test.txt")
        assert len(chunks) > 0
        assert all(chunk.document_id == "test_doc" for chunk in chunks)


# Test Retrieval
class TestHybridRetriever:
    def test_bm25_search(self):
        from app.core.retrieval import HybridRetriever

        # Create mock dependencies
        vector_store = MagicMock()
        embedding_manager = MagicMock()

        retriever = HybridRetriever(vector_store, embedding_manager)
        texts = [
            "Python is a programming language",
            "Java is used for enterprise applications",
            "Machine learning uses Python extensively",
        ]
        retriever.build_bm25_index(texts)

        results = retriever._bm25_search("Python programming", top_k=2)
        assert len(results) > 0
        # Python should be in top results
        assert "Python" in results[0][0]


# Test Evaluation
class TestEvaluation:
    def test_confidence_score(self):
        from app.core.evaluation import calculate_confidence_score

        # High confidence case
        score = calculate_confidence_score(
            retrieval_scores=[0.9, 0.85, 0.8],
            num_relevant_chunks=3,
            total_chunks_searched=5,
        )
        assert score > 0.5

        # Low confidence case
        score = calculate_confidence_score(
            retrieval_scores=[0.1, 0.05],
            num_relevant_chunks=1,
            total_chunks_searched=100,
        )
        assert score < 0.5

        # Empty case
        score = calculate_confidence_score([], 0, 0)
        assert score == 0.0


# Test SQL Validation
class TestSQLAgent:
    def test_validate_safe_query(self):
        from app.agents.sql_agent import SQLGeneratorAgent
        agent = SQLGeneratorAgent()

        assert agent._validate_sql("SELECT * FROM employees") == True
        assert agent._validate_sql("SELECT name FROM users WHERE id = 1") == True

    def test_validate_dangerous_query(self):
        from app.agents.sql_agent import SQLGeneratorAgent
        agent = SQLGeneratorAgent()

        assert agent._validate_sql("DROP TABLE users") == False
        assert agent._validate_sql("DELETE FROM employees") == False
        assert agent._validate_sql("UPDATE users SET admin = true") == False
        assert agent._validate_sql("INSERT INTO users VALUES (1, 'hack')") == False
