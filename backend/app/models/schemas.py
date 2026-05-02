"""
Pydantic Models for API Request/Response Schemas
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# Chat Models
# ============================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    role: str = Field(default="general", pattern="^(general|hr|engineer|manager|executive)$")
    stream: bool = False


class SourceReference(BaseModel):
    content: str
    filename: str = ""
    page: Optional[int] = None
    source: str = ""
    score: float = 0.0
    rank: int = 0


class ChatResponse(BaseModel):
    message: str
    session_id: str
    sources: List[SourceReference] = []
    confidence_score: float = 0.0
    follow_up_questions: List[str] = []
    action_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]] = []
    title: str = "New Chat"
    role: str = "general"
    created_at: str = ""


# ============================================
# Document Models
# ============================================

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int = 0
    source: str = "upload"
    status: str = "processing"
    chunk_count: int = 0
    created_at: str = ""


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int = 0


class DocumentSummaryRequest(BaseModel):
    document_id: str
    max_length: int = 500


class DocumentSummaryResponse(BaseModel):
    document_id: str
    summary: str
    key_topics: List[str] = []


# ============================================
# SQL Query Models
# ============================================

class SQLQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)


class SQLQueryResponse(BaseModel):
    status: str
    sql: str = ""
    results: List[Dict[str, Any]] = []
    explanation: str = ""
    row_count: int = 0


# ============================================
# Analytics Models
# ============================================

class AnalyticsResponse(BaseModel):
    total_queries: int = 0
    total_documents: int = 0
    total_sessions: int = 0
    avg_confidence: float = 0.0
    queries_today: int = 0
    top_sources: List[Dict[str, Any]] = []
    recent_queries: List[Dict[str, Any]] = []
    usage_over_time: List[Dict[str, Any]] = []


# ============================================
# Action Models
# ============================================

class ActionRequest(BaseModel):
    action_type: str
    parameters: Dict[str, Any] = {}


class ActionResponse(BaseModel):
    status: str
    action: str
    result: Dict[str, Any] = {}
    message: str = ""


# ============================================
# Session Models
# ============================================

class SessionListResponse(BaseModel):
    sessions: List[Dict[str, Any]] = []


class CreateSessionRequest(BaseModel):
    title: str = "New Chat"
    role: str = "general"
