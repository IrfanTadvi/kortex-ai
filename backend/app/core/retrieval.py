"""
Advanced Retrieval Engine
Implements hybrid search (BM25 + Vector), cross-encoder re-ranking,
query rewriting, and context compression.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger
from rank_bm25 import BM25Okapi

from app.config import get_settings


@dataclass
class RetrievalResult:
    """A single retrieval result with metadata and scoring."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    retrieval_method: str = "hybrid"
    rank: int = 0


class HybridRetriever:
    """
    Advanced retrieval combining BM25 lexical search with vector similarity.
    
    Architecture Decision: Hybrid search significantly outperforms either
    approach alone. BM25 captures exact keyword matches while vector search
    captures semantic similarity. The fusion strategy uses Reciprocal Rank
    Fusion (RRF) for combining scores.
    """

    def __init__(self, vector_store, embedding_manager):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.settings = get_settings()
        self._bm25_index: Optional[BM25Okapi] = None
        self._corpus: List[str] = []
        self._corpus_metadata: List[Dict[str, Any]] = []

    def build_bm25_index(self, texts: List[str]):
        """Build BM25 index from corpus texts."""
        self._corpus = texts
        tokenized_corpus = [doc.lower().split() for doc in texts]
        self._bm25_index = BM25Okapi(tokenized_corpus)
        # Store metadata reference for BM25 results
        self._corpus_metadata = self.vector_store._metadata if hasattr(self.vector_store, '_metadata') else []
        logger.info(f"Built BM25 index with {len(texts)} documents")

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = None,
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval combining vector and BM25 search.
        
        Args:
            query: User query
            top_k: Number of results to return
            alpha: Weight for vector search (0-1). None uses config default.
        """
        if alpha is None:
            alpha = self.settings.hybrid_search_alpha

        # Vector search
        query_embedding = await self.embedding_manager.embed_query(query)
        vector_results = await self.vector_store.search(query_embedding, top_k=top_k * 2)

        # BM25 search
        bm25_results = self._bm25_search(query, top_k=top_k * 2)

        # Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            vector_results, bm25_results, alpha=alpha
        )

        # Return top-k
        return fused_results[:top_k]

    def _bm25_search(self, query: str, top_k: int = 20) -> List[Tuple[str, Dict[str, Any], float]]:
        """Perform BM25 lexical search."""
        if not self._bm25_index or not self._corpus:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)

        # Get top indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                meta = self._corpus_metadata[idx] if idx < len(self._corpus_metadata) else {}
                results.append((
                    self._corpus[idx],
                    meta,
                    float(scores[idx]),
                ))

        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Tuple[str, Dict[str, Any], float]],
        bm25_results: List[Tuple[str, Dict[str, Any], float]],
        alpha: float = 0.7,
        k: int = 60,
    ) -> List[RetrievalResult]:
        """
        Reciprocal Rank Fusion (RRF) for combining multiple ranked lists.
        
        RRF score = sum(1 / (k + rank_i)) for each ranking system.
        This is more robust than simple score interpolation.
        """
        doc_scores: Dict[str, float] = {}
        doc_content: Dict[str, Tuple[str, Dict[str, Any]]] = {}

        # Score from vector search (weighted by alpha)
        for rank, (text, meta, score) in enumerate(vector_results):
            doc_key = text[:100]  # Use content prefix as key
            rrf_score = alpha * (1.0 / (k + rank + 1))
            doc_scores[doc_key] = doc_scores.get(doc_key, 0) + rrf_score
            doc_content[doc_key] = (text, meta)

        # Score from BM25 search (weighted by 1-alpha)
        for rank, (text, meta, score) in enumerate(bm25_results):
            doc_key = text[:100]
            rrf_score = (1 - alpha) * (1.0 / (k + rank + 1))
            doc_scores[doc_key] = doc_scores.get(doc_key, 0) + rrf_score
            if doc_key not in doc_content:
                doc_content[doc_key] = (text, meta)

        # Sort by fused score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for rank, (doc_key, score) in enumerate(sorted_docs):
            text, meta = doc_content[doc_key]
            results.append(RetrievalResult(
                content=text,
                metadata=meta,
                score=score,
                retrieval_method="hybrid",
                rank=rank + 1,
            ))

        return results


class CrossEncoderReranker:
    """
    Cross-encoder based re-ranking for improved precision.
    
    Architecture Decision: Cross-encoders jointly encode query-document pairs,
    producing much more accurate relevance scores than bi-encoders.
    We apply this as a second stage on the top-K candidates from hybrid retrieval.
    """

    def __init__(self):
        self._model = None
        self.settings = get_settings()

    def _load_model(self):
        """Lazy load cross-encoder model."""
        if self._model is not None:
            return
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logger.info("Loaded cross-encoder re-ranking model")

    async def rerank(
        self, query: str, results: List[RetrievalResult], top_k: int = 5
    ) -> List[RetrievalResult]:
        """Re-rank results using cross-encoder."""
        if not results:
            return []

        self._load_model()

        # Create query-document pairs
        pairs = [(query, result.content) for result in results]

        # Score with cross-encoder
        scores = self._model.predict(pairs)

        # Assign new scores and sort
        for result, score in zip(results, scores):
            result.score = float(score)

        reranked = sorted(results, key=lambda x: x.score, reverse=True)

        # Update ranks
        for i, result in enumerate(reranked):
            result.rank = i + 1
            result.retrieval_method = "hybrid+reranked"

        return reranked[:top_k]


class QueryRewriter:
    """
    Query rewriting for better retrieval performance.
    
    Architecture Decision: User queries are often ambiguous or poorly formed.
    Query rewriting reformulates the query to improve retrieval,
    using techniques like HyDE (Hypothetical Document Embeddings)
    and query expansion.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def rewrite(self, query: str, chat_history: List[Dict] = None) -> str:
        """
        Rewrite query for better retrieval.
        Uses rule-based rewriting to avoid LLM hallucination and save tokens.
        """
        # Always use rule-based rewriting - LLM rewriting wastes tokens
        # and hallucinates on small models
        return self._rule_based_rewrite(query)

        # Use LLM for intelligent rewriting
        system_prompt = """You are a query rewriting assistant. Your job is to reformulate 
        user queries to be more effective for document retrieval. 
        
        Rules:
        - Make the query more specific and search-friendly
        - Expand abbreviations
        - If there's chat history context, resolve pronouns and references
        - Keep the core intent intact
        - Return ONLY the rewritten query, nothing else"""

        context = ""
        if chat_history:
            recent = chat_history[-3:]  # Last 3 messages for context
            context = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
            context = f"\nRecent conversation:\n{context}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}Original query: {query}\nRewritten query:"},
        ]

        try:
            rewritten = await self.llm_client.generate(messages, max_tokens=100)
            return rewritten.strip() if rewritten.strip() else query
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}. Using original query.")
            return query

    def _rule_based_rewrite(self, query: str) -> str:
        """Fallback rule-based query rewriting."""
        # Remove filler words
        fillers = ["please", "can you", "could you", "tell me", "i want to know", "what is"]
        rewritten = query.lower()
        for filler in fillers:
            rewritten = rewritten.replace(filler, "")
        return rewritten.strip() if rewritten.strip() else query


class ContextCompressor:
    """
    Compresses retrieved context to fit within LLM context window
    while preserving the most relevant information.
    """

    def __init__(self, max_tokens: int = 1200):
        self.max_tokens = max_tokens

    def compress(self, results: List[RetrievalResult], query: str) -> str:
        """
        Compress and format retrieved context.
        Prioritizes higher-ranked results and removes redundancy.
        """
        compressed_parts = []
        current_tokens = 0

        for result in results:
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            estimated_tokens = len(result.content) // 4

            if current_tokens + estimated_tokens > self.max_tokens:
                # Truncate this chunk to fit
                remaining = self.max_tokens - current_tokens
                truncated = result.content[: remaining * 4]
                if truncated:
                    source_info = self._format_source(result.metadata)
                    compressed_parts.append(f"[Source: {source_info}]\n{truncated}...")
                break

            source_info = self._format_source(result.metadata)
            compressed_parts.append(f"[Source: {source_info}]\n{result.content}")
            current_tokens += estimated_tokens

        return "\n\n---\n\n".join(compressed_parts)

    def _format_source(self, metadata: Dict[str, Any]) -> str:
        """Format source metadata for citation."""
        filename = metadata.get("filename", "Unknown")
        # Strip UUID prefix if present (format: uuid_filename.ext)
        import re
        filename = re.sub(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_',
            '', filename
        )
        page = metadata.get("page", "")
        source = metadata.get("source", "")

        parts = [filename]
        if page:
            parts.append(f"Page {page}")
        if source and source != "upload":
            parts.append(f"via {source}")

        return ", ".join(parts)
