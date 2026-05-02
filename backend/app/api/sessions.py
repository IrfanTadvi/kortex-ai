"""
Session Management API Routes
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db, ChatSession, ChatMessage
from app.models.schemas import SessionListResponse, CreateSessionRequest, ChatHistoryResponse

router = APIRouter()


@router.get("", response_model=SessionListResponse)
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all chat sessions."""
    result = await db.execute(select(ChatSession).order_by(desc(ChatSession.updated_at)))
    sessions = result.scalars().all()

    return SessionListResponse(
        sessions=[
            {
                "id": s.id,
                "title": s.title,
                "role": s.role,
                "created_at": s.created_at.isoformat() if s.created_at else "",
                "updated_at": s.updated_at.isoformat() if s.updated_at else "",
            }
            for s in sessions
        ]
    )


@router.post("")
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(
        id=str(uuid.uuid4()),
        title=request.title,
        role=request.role,
    )
    db.add(session)
    await db.commit()

    return {
        "id": session.id,
        "title": session.title,
        "role": session.role,
    }


@router.get("/{session_id}", response_model=ChatHistoryResponse)
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get chat history for a session."""
    # Get session
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(404, "Session not found")

    # Get messages
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "sources": m.sources or [],
                "confidence_score": m.confidence_score,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in messages
        ],
        title=session.title,
        role=session.role,
        created_at=session.created_at.isoformat() if session.created_at else "",
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a chat session and its messages."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(404, "Session not found")

    # Delete messages
    result = await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id))
    messages = result.scalars().all()
    for msg in messages:
        await db.delete(msg)

    await db.delete(session)
    await db.commit()

    return {"status": "deleted", "session_id": session_id}
