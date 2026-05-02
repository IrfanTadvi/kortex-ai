"""
Chat API Routes
Handles conversation, streaming responses, and action detection.
"""

import json
import uuid
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger

from app.core.database import get_db, ChatSession, ChatMessage, QueryLog
from app.agents.orchestrator import AgentOrchestrator
from app.agents.actions import ActionDetector, ActionExecutor
from app.models.schemas import ChatRequest, ChatResponse, SourceReference

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a chat message through the RAG pipeline.
    Supports streaming, role-based responses, and action detection.
    """
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    session = await _get_or_create_session(db, session_id, request.role)

    # Get chat history
    chat_history = await _get_chat_history(db, session_id)

    # Check for action intent
    action_detector = ActionDetector()
    action_intent = await action_detector.detect_action(request.message)

    action_result = None
    if action_intent:
        # Execute action
        executor = ActionExecutor()
        action_result = await executor.execute(
            action_intent["action_type"], request.message
        )
        logger.info(f"Action executed: {action_intent['action_type']}")

    # RAG Pipeline
    vector_store = req.app.state.vector_store
    embedding_manager = req.app.state.embeddings
    reranker = getattr(req.app.state, 'reranker', None)
    orchestrator = AgentOrchestrator(vector_store, embedding_manager, reranker)

    # Build BM25 index from current texts
    if vector_store._texts:
        orchestrator.build_search_index(vector_store._texts)

    if request.stream:
        # Streaming response
        return StreamingResponse(
            _stream_response(
                orchestrator, request.message, chat_history,
                request.role, session_id, db, action_result
            ),
            media_type="text/event-stream",
        )

    # Non-streaming response
    response = await orchestrator.process_query(
        query=request.message,
        chat_history=chat_history,
        role=request.role,
        stream=False,
    )

    # Format sources
    sources = [
        SourceReference(
            content=s["content"][:200],
            filename=s["metadata"].get("filename", "Unknown"),
            page=s["metadata"].get("page"),
            source=s["metadata"].get("source", "upload"),
            score=s["score"],
            rank=s["rank"],
        )
        for s in response.sources
    ]

    # Save messages to database
    await _save_message(db, session_id, "user", request.message)
    await _save_message(
        db, session_id, "assistant", response.answer,
        sources=[s.model_dump() for s in sources],
        confidence=response.confidence_score,
    )

    # Auto-name session from first user message (like ChatGPT)
    await _auto_title_session(db, session_id, request.message)

    # Log query for analytics
    await _log_query(
        db, session_id, request.message, response.rewritten_query,
        len(response.sources), response.confidence_score,
        response.metadata.get("latency_ms", 0),
    )

    return ChatResponse(
        message=response.answer,
        session_id=session_id,
        sources=sources,
        confidence_score=response.confidence_score,
        follow_up_questions=response.follow_up_questions,
        action_result=action_result,
        metadata={
            "rewritten_query": response.rewritten_query,
            "latency_ms": response.metadata.get("latency_ms", 0),
        },
    )


async def _stream_response(
    orchestrator, query, chat_history, role, session_id, db, action_result
):
    """Generate Server-Sent Events for streaming."""
    full_response = ""

    # Send action result first if present
    if action_result:
        yield f"data: {json.dumps({'type': 'action', 'data': action_result})}\n\n"

    # Stream the LLM response
    try:
        stream = await orchestrator.process_query(
            query=query,
            chat_history=chat_history,
            role=role,
            stream=True,
        )

        async for token in stream:
            full_response += token
            yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"

        # Send completion event
        yield f"data: {json.dumps({'type': 'done', 'data': {'session_id': session_id}})}\n\n"

        # Save to database
        await _save_message(db, session_id, "user", query)
        await _save_message(db, session_id, "assistant", full_response)

        # Auto-name session from first user message
        await _auto_title_session(db, session_id, query)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Streaming error: {error_msg}")
        if "rate_limit" in error_msg or "429" in error_msg or "413" in error_msg:
            msg = "Sorry, the AI service is rate-limited. Please wait a few seconds and try again."
        else:
            msg = f"Error generating response: {error_msg[:200]}"
        yield "data: " + json.dumps({"type": "token", "data": msg}) + "\n\n"
        yield "data: " + json.dumps({"type": "done", "data": {"session_id": session_id}}) + "\n\n"


async def _get_or_create_session(db: AsyncSession, session_id: str, role: str) -> ChatSession:
    """Get existing session or create new one."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        session = ChatSession(id=session_id, role=role)
        db.add(session)
        await db.commit()

    return session


async def _get_chat_history(db: AsyncSession, session_id: str, limit: int = 10):
    """Retrieve recent chat history for context."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
    )
    messages = result.scalars().all()
    messages.reverse()

    return [{"role": m.role, "content": m.content} for m in messages]


async def _save_message(
    db: AsyncSession, session_id: str, role: str, content: str,
    sources: list = None, confidence: float = 0.0
):
    """Save a message to the database."""
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=sources or [],
        confidence_score=confidence,
    )
    db.add(message)
    await db.commit()


async def _log_query(
    db: AsyncSession, session_id: str, query: str, rewritten: str,
    num_chunks: int, confidence: float, latency: float
):
    """Log query for analytics and evaluation."""
    log = QueryLog(
        session_id=session_id,
        query=query,
        rewritten_query=rewritten,
        num_chunks_retrieved=num_chunks,
        confidence_score=confidence,
        latency_ms=latency,
    )
    db.add(log)
    await db.commit()


async def _auto_title_session(db: AsyncSession, session_id: str, first_message: str):
    """Auto-name session from first user message if still 'New Chat'."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if session and session.title == "New Chat":
        # Truncate to first 50 chars, clean up
        title = first_message.strip()[:50]
        if len(first_message.strip()) > 50:
            title = title.rsplit(' ', 1)[0] + '...'
        session.title = title or "New Chat"
        await db.commit()
