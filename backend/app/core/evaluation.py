"""
Evaluation Module
Basic RAG evaluation with accuracy scoring and response quality metrics.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class EvaluationResult:
    """Evaluation metrics for a single query-response pair."""
    query: str
    response: str
    context_relevance: float  # How relevant retrieved context is to query
    answer_relevance: float   # How relevant the answer is to the query
    faithfulness: float       # How grounded the answer is in the context
    overall_score: float      # Composite score


class RAGEvaluator:
    """
    Evaluates RAG pipeline quality using automated metrics.
    
    Metrics:
    - Context Relevance: Are the retrieved chunks relevant to the query?
    - Answer Relevance: Does the answer address the query?
    - Faithfulness: Is the answer grounded in the retrieved context?
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def evaluate(
        self,
        query: str,
        response: str,
        retrieved_contexts: List[str],
    ) -> EvaluationResult:
        """Run full evaluation on a query-response pair."""
        context_relevance = await self._score_context_relevance(query, retrieved_contexts)
        answer_relevance = await self._score_answer_relevance(query, response)
        faithfulness = await self._score_faithfulness(response, retrieved_contexts)

        overall = (context_relevance + answer_relevance + faithfulness) / 3

        return EvaluationResult(
            query=query,
            response=response,
            context_relevance=context_relevance,
            answer_relevance=answer_relevance,
            faithfulness=faithfulness,
            overall_score=overall,
        )

    async def _score_context_relevance(self, query: str, contexts: List[str]) -> float:
        """Score how relevant the retrieved contexts are to the query."""
        if not contexts:
            return 0.0

        if not self.llm_client:
            # Heuristic: keyword overlap
            query_words = set(query.lower().split())
            scores = []
            for ctx in contexts:
                ctx_words = set(ctx.lower().split())
                overlap = len(query_words & ctx_words) / max(len(query_words), 1)
                scores.append(min(overlap * 3, 1.0))  # Scale up
            return sum(scores) / len(scores)

        # LLM-based scoring
        try:
            context_text = "\n".join(contexts[:3])
            messages = [{
                "role": "user",
                "content": f"Rate 0-1 how relevant this context is to the query.\nQuery: {query}\nContext: {context_text}\nScore (just the number):",
            }]
            result = await self.llm_client.generate(messages, max_tokens=10)
            return float(result.strip())
        except Exception:
            return 0.5

    async def _score_answer_relevance(self, query: str, answer: str) -> float:
        """Score how relevant the answer is to the query."""
        if not answer:
            return 0.0

        if not self.llm_client:
            # Heuristic: answer contains query keywords
            query_words = set(query.lower().split())
            answer_words = set(answer.lower().split())
            overlap = len(query_words & answer_words) / max(len(query_words), 1)
            return min(overlap * 2, 1.0)

        try:
            messages = [{
                "role": "user",
                "content": f"Rate 0-1 how well this answer addresses the query.\nQuery: {query}\nAnswer: {answer[:500]}\nScore (just the number):",
            }]
            result = await self.llm_client.generate(messages, max_tokens=10)
            return float(result.strip())
        except Exception:
            return 0.5

    async def _score_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """Score how grounded the answer is in the provided context."""
        if not answer or not contexts:
            return 0.0

        if not self.llm_client:
            # Heuristic: n-gram overlap between answer and context
            context_text = " ".join(contexts)
            answer_words = answer.lower().split()
            context_words = set(context_text.lower().split())
            grounded = sum(1 for w in answer_words if w in context_words)
            return min(grounded / max(len(answer_words), 1), 1.0)

        try:
            context_text = "\n".join(contexts[:3])
            messages = [{
                "role": "user",
                "content": f"Rate 0-1 how well the answer is supported by the context (faithfulness).\nContext: {context_text}\nAnswer: {answer[:500]}\nScore (just the number):",
            }]
            result = await self.llm_client.generate(messages, max_tokens=10)
            return float(result.strip())
        except Exception:
            return 0.5


def calculate_confidence_score(
    retrieval_scores: List[float],
    num_relevant_chunks: int,
    total_chunks_searched: int,
) -> float:
    """
    Calculate a confidence score based on retrieval quality signals.
    
    Factors:
    - Average retrieval score
    - Number of relevant chunks found
    - Score distribution (high variance = less confident)
    """
    if not retrieval_scores:
        return 0.0

    avg_score = sum(retrieval_scores) / len(retrieval_scores)
    coverage = num_relevant_chunks / max(total_chunks_searched, 1)

    # Score variance penalty
    if len(retrieval_scores) > 1:
        variance = sum((s - avg_score) ** 2 for s in retrieval_scores) / len(retrieval_scores)
        variance_penalty = min(variance * 2, 0.3)
    else:
        variance_penalty = 0.1

    confidence = (avg_score * 0.6 + coverage * 0.2 + (1 - variance_penalty) * 0.2)
    return max(0.0, min(1.0, confidence))
