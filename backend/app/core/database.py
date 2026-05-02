"""
Database Layer
SQLAlchemy async setup for metadata storage, chat history, and analytics.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Text, Float, Integer, JSON, Boolean
from datetime import datetime, timezone
import uuid

from app.config import get_settings


class Base(DeclarativeBase):
    pass


# ============================================
# Database Models
# ============================================

class Document(Base):
    """Stores metadata about ingested documents."""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    source = Column(String, default="upload")  # upload, slack, notion, api
    status = Column(String, default="processing")  # processing, ready, error
    chunk_count = Column(Integer, default=0)
    doc_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatSession(Base):
    """Chat session with memory support."""
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, default="New Chat")
    role = Column(String, default="general")  # general, hr, engineer, manager
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatMessage(Base):
    """Individual messages within a chat session."""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)  # Retrieved source references
    confidence_score = Column(Float, default=0.0)
    msg_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class QueryLog(Base):
    """Analytics and evaluation logging."""
    __tablename__ = "query_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=True)
    query = Column(Text, nullable=False)
    rewritten_query = Column(Text, nullable=True)
    retrieval_method = Column(String, default="hybrid")
    num_chunks_retrieved = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    feedback = Column(String, nullable=True)  # positive, negative
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ActionLog(Base):
    """Logs actions performed by the action layer."""
    __tablename__ = "action_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=True)
    action_type = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    status = Column(String, default="completed")
    result = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================
# Database Engine & Session Management
# ============================================

_engine = None
_session_factory = None


def _get_async_url(url: str) -> str:
    """Convert sync database URL to async."""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


async def init_db():
    """Initialize database and create tables."""
    global _engine, _session_factory
    settings = get_settings()

    _engine = create_async_engine(
        _get_async_url(settings.database_url),
        echo=False,
    )
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency injection for database sessions."""
    async with _session_factory() as session:
        yield session
