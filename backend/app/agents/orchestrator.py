"""
Multi-Agent Architecture
Implements Retriever, Reasoning, and Answer Generator agents
that work together to produce high-quality, grounded responses.
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from loguru import logger
import time

from app.core.llm_client import LLMClient
from app.core.retrieval import (
    HybridRetriever,
    CrossEncoderReranker,
    QueryRewriter,
    ContextCompressor,
    RetrievalResult,
)
from app.config import get_settings


@dataclass
class AgentResponse:
    """Structured response from the agent pipeline."""
    answer: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    follow_up_questions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    rewritten_query: str = ""


class RetrieverAgent:
    """
    Agent responsible for finding the most relevant information.
    
    Capabilities:
    - Query analysis and rewriting
    - Hybrid search execution
    - Cross-encoder re-ranking
    - Context compression
    """

    def __init__(self, vector_store, embedding_manager, reranker=None):
        self.settings = get_settings()
        self.llm = LLMClient()
        self.retriever = HybridRetriever(vector_store, embedding_manager)
        self.reranker = reranker or CrossEncoderReranker()
        self.query_rewriter = QueryRewriter(self.llm)
        self.compressor = ContextCompressor(max_tokens=1200)

    async def retrieve(
        self, query: str, chat_history: List[Dict] = None, top_k: int = None
    ) -> tuple[List[RetrievalResult], str]:
        """
        Full retrieval pipeline:
        1. Rewrite query for better retrieval
        2. Hybrid search (BM25 + Vector)
        3. Cross-encoder re-ranking
        4. Return top results
        """
        if top_k is None:
            top_k = self.settings.rerank_top_k

        # Step 1: Query rewriting
        rewritten_query = await self.query_rewriter.rewrite(query, chat_history)
        logger.info(f"Query rewritten: '{query}' -> '{rewritten_query}'")

        # Step 2: Hybrid retrieval
        results = await self.retriever.retrieve(
            rewritten_query,
            top_k=self.settings.top_k_results,
        )

        if not results:
            return [], rewritten_query

        # Step 3: Re-ranking
        reranked = await self.reranker.rerank(rewritten_query, results, top_k=top_k)

        return reranked, rewritten_query

    def build_search_index(self, texts: List[str]):
        """Build BM25 index for hybrid search."""
        self.retriever.build_bm25_index(texts)


class ReasoningAgent:
    """
    Agent responsible for analyzing retrieved context and planning the answer.
    
    Capabilities:
    - Assess relevance of retrieved chunks
    - Identify information gaps
    - Plan answer structure
    - Detect when information is insufficient
    """

    def __init__(self):
        self.llm = LLMClient()

    async def analyze(
        self, query: str, results: List[RetrievalResult], role: str = "general"
    ) -> Dict[str, Any]:
        """
        Analyze retrieved context and plan the response.
        Returns analysis with confidence and answer plan.
        """
        if not results:
            return {
                "has_relevant_info": False,
                "confidence": 0.0,
                "answer_plan": "No relevant information found in knowledge base.",
                "gaps": ["No matching documents found for this query."],
            }

        context_summary = "\n".join([
            f"[Chunk {i+1}, Score: {r.score:.3f}]: {r.content[:200]}..."
            for i, r in enumerate(results[:5])
        ])

        system_prompt = f"""You are a reasoning agent analyzing retrieval results.
Your role context: {role}

Analyze the retrieved chunks and determine:
1. Whether they contain relevant information to answer the query
2. Your confidence level (0.0-1.0) in the available information
3. A brief plan for constructing the answer
4. Any information gaps

Respond in JSON format:
{{
    "has_relevant_info": true/false,
    "confidence": 0.0-1.0,
    "answer_plan": "brief plan",
    "gaps": ["list of gaps"],
    "key_points": ["main points to include"]
}}"""

        messages = [
            {"role": "user", "content": f"Query: {query}\n\nRetrieved Context:\n{context_summary}"}
        ]

        try:
            analysis = await self.llm.generate_structured(
                messages=messages,
                schema={
                    "has_relevant_info": "boolean",
                    "confidence": "number",
                    "answer_plan": "string",
                    "gaps": ["string"],
                    "key_points": ["string"],
                },
                system_prompt=system_prompt,
            )
            return analysis if analysis else {
                "has_relevant_info": len(results) > 0,
                "confidence": results[0].score if results else 0.0,
                "answer_plan": "Generate answer from available context.",
                "gaps": [],
                "key_points": [],
            }
        except Exception as e:
            logger.warning(f"Reasoning agent analysis failed: {e}")
            return {
                "has_relevant_info": len(results) > 0,
                "confidence": results[0].score if results else 0.0,
                "answer_plan": "Generate answer from available context.",
                "gaps": [],
                "key_points": [],
            }


class AnswerGeneratorAgent:
    """
    Agent responsible for generating the final, grounded response.
    
    Capabilities:
    - Generate source-cited answers
    - Adapt tone based on user role
    - Generate follow-up questions
    - Streaming response generation
    """

    def __init__(self):
        self.llm = LLMClient()
        self.compressor = ContextCompressor()

    def _get_system_prompt(self, role: str, analysis: Dict[str, Any]) -> str:
        """Generate role-appropriate system prompt."""
        role_instructions = {
            "general": "Provide clear, comprehensive answers suitable for any audience.",
            "hr": "Focus on HR policies, employee guidelines, and people-related topics. Use professional, empathetic language.",
            "engineer": "Provide technical, detailed answers. Include code examples or technical specifics when relevant.",
            "manager": "Focus on strategic insights, metrics, and actionable recommendations. Be concise and business-oriented.",
            "executive": "Provide high-level summaries with key metrics and strategic implications. Be extremely concise.",
        }

        role_instruction = role_instructions.get(role, role_instructions["general"])
        confidence = analysis.get("confidence", 0.5)

        return f"""You are an AI Knowledge Copilot answering from the provided context only.
Role: {role}. {role_instruction}

Rules:
- Answer ONLY from the provided context. Don't make up info.
- Cite sources as [Source: filename].
- If context is insufficient, say so clearly.
- Be concise and factual."""""

    async def generate(
        self,
        query: str,
        results: List[RetrievalResult],
        analysis: Dict[str, Any],
        chat_history: List[Dict] = None,
        role: str = "general",
    ) -> AgentResponse:
        """Generate a complete, non-streaming response."""
        system_prompt = self._get_system_prompt(role, analysis)
        context = self.compressor.compress(results, query)

        messages = []
        if chat_history:
            messages.extend(chat_history[-6:])  # Last 6 messages for context

        messages.append({
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}\n\nProvide a comprehensive answer with source citations and follow-up questions.",
        })

        answer = await self.llm.generate(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.3,
        )

        # Extract sources from results (clean UUID prefix from filenames)
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_'
        )
        sources = []
        for r in results:
            clean_meta = dict(r.metadata)
            if "filename" in clean_meta:
                clean_meta["filename"] = uuid_pattern.sub('', clean_meta["filename"])
            sources.append({
                "content": r.content[:200],
                "metadata": clean_meta,
                "score": r.score,
                "rank": r.rank,
            })

        # Generate follow-up questions (extract from answer instead of separate LLM call)
        follow_ups = self._extract_follow_ups(answer)

        return AgentResponse(
            answer=answer,
            sources=sources,
            confidence_score=analysis.get("confidence", 0.5),
            follow_up_questions=follow_ups,
            metadata={"analysis": analysis},
        )

    async def generate_stream(
        self,
        query: str,
        results: List[RetrievalResult],
        analysis: Dict[str, Any],
        chat_history: List[Dict] = None,
        role: str = "general",
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response for real-time UI updates."""
        system_prompt = self._get_system_prompt(role, analysis)
        context = self.compressor.compress(results, query)

        messages = []
        if chat_history:
            messages.extend(chat_history[-6:])

        messages.append({
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}\n\nProvide a comprehensive answer with source citations.",
        })

        async for token in self.llm.generate_stream(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.3,
        ):
            yield token

    async def _generate_follow_ups(self, query: str, answer: str) -> List[str]:
        """Generate relevant follow-up questions."""
        try:
            messages = [{
                "role": "user",
                "content": f"Based on this Q&A, suggest 3 brief follow-up questions:\nQ: {query}\nA: {answer[:500]}\n\nReturn only the questions, one per line.",
            }]

            response = await self.llm.generate(
                messages=messages,
                max_tokens=200,
                temperature=0.5,
            )

            questions = [q.strip().lstrip("0123456789.-) ") for q in response.strip().split("\n") if q.strip()]
            return questions[:3]
        except Exception:
            return []

    def _extract_follow_ups(self, answer: str) -> List[str]:
        """Extract follow-up questions from the answer if present, otherwise return defaults."""
        lines = answer.split("\n")
        follow_ups = []
        in_follow_up_section = False
        for line in lines:
            lower = line.lower().strip()
            if "follow-up" in lower or "follow up" in lower:
                in_follow_up_section = True
                continue
            if in_follow_up_section and line.strip():
                q = line.strip().lstrip("0123456789.-) •*")
                if q and len(q) > 10:
                    follow_ups.append(q)
        return follow_ups[:3]


class AgentOrchestrator:
    """
    Orchestrates the multi-agent pipeline.
    Coordinates Retriever -> Reasoning -> Answer Generator flow.
    """

    # Patterns that indicate small talk / greetings (no RAG needed)
    GREETING_PATTERNS = {
        "hi", "hello", "hey", "hola", "sup", "yo", "good morning",
        "good afternoon", "good evening", "what's up", "whats up",
        "how are you", "how r u", "thanks", "thank you", "bye",
        "goodbye", "ok", "okay", "cool", "nice", "great",
    }

    GREETING_RESPONSE = (
        "Hello! I'm your AI Knowledge Copilot. I can help you with:\n\n"
        "- **Answering questions** about your uploaded documents\n"
        "- **Finding specific information** from your knowledge base\n"
        "- **SQL queries** on structured data\n\n"
        "Upload a document or ask me anything about your knowledge base!"
    )

    def __init__(self, vector_store, embedding_manager, reranker=None):
        self.retriever_agent = RetrieverAgent(vector_store, embedding_manager, reranker)
        self.reasoning_agent = ReasoningAgent()
        self.answer_agent = AnswerGeneratorAgent()

    def _is_greeting(self, query: str) -> bool:
        """Detect if the query is a greeting or small talk."""
        cleaned = query.lower().strip().rstrip("!?.,:;")
        # Exact match or very short message
        if cleaned in self.GREETING_PATTERNS:
            return True
        # Check if starts with a greeting word and is short
        if len(cleaned.split()) <= 3:
            for pattern in self.GREETING_PATTERNS:
                if cleaned.startswith(pattern):
                    return True
        return False

    async def process_query(
        self,
        query: str,
        chat_history: List[Dict] = None,
        role: str = "general",
        stream: bool = False,
    ) -> "AgentResponse | AsyncGenerator[str, None]":
        """
        Full agent pipeline execution.
        
        Flow:
        1. Check if greeting (skip RAG)
        2. RetrieverAgent: Find relevant information
        3. ReasoningAgent: Analyze and plan (rule-based, no LLM)
        4. AnswerGeneratorAgent: Generate grounded response
        """
        start_time = time.time()

        # Short-circuit for greetings
        if self._is_greeting(query):
            if stream:
                async def greeting_stream():
                    yield self.GREETING_RESPONSE
                return greeting_stream()
            return AgentResponse(
                answer=self.GREETING_RESPONSE,
                sources=[],
                confidence_score=1.0,
                follow_up_questions=[
                    "What documents do you have?",
                    "How do I upload a file?",
                    "What can you help me with?",
                ],
                metadata={"latency_ms": int((time.time() - start_time) * 1000)},
            )

        # Step 1: Retrieval
        results, rewritten_query = await self.retriever_agent.retrieve(
            query, chat_history
        )

        # Step 2: Reasoning (rule-based - no LLM call to save latency)
        if results:
            top_score = results[0].score if results else 0.0
            analysis = {
                "has_relevant_info": True,
                "confidence": min(top_score, 1.0),
                "answer_plan": "Generate answer from available context.",
                "gaps": [],
                "key_points": [],
            }
        else:
            analysis = {
                "has_relevant_info": False,
                "confidence": 0.0,
                "answer_plan": "No documents in knowledge base. Answer from general knowledge.",
                "gaps": ["No documents uploaded yet."],
                "key_points": [],
            }

        # Step 3: Answer Generation
        if stream:
            return self.answer_agent.generate_stream(
                query, results, analysis, chat_history, role
            )

        response = await self.answer_agent.generate(
            query, results, analysis, chat_history, role
        )
        response.rewritten_query = rewritten_query
        response.metadata["latency_ms"] = (time.time() - start_time) * 1000

        return response

    def build_search_index(self, texts: List[str]):
        """Build search indices for the retriever."""
        self.retriever_agent.build_search_index(texts)
