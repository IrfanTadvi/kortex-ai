"""
Analytics API Routes
Provides usage metrics, query logs, and system statistics.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timezone, timedelta

from app.core.database import get_db, QueryLog, Document, ChatSession
from app.models.schemas import AnalyticsResponse

router = APIRouter()


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get system analytics and usage metrics."""
    # Total queries
    result = await db.execute(select(func.count(QueryLog.id)))
    total_queries = result.scalar() or 0

    # Total documents
    result = await db.execute(select(func.count(Document.id)))
    total_documents = result.scalar() or 0

    # Total sessions
    result = await db.execute(select(func.count(ChatSession.id)))
    total_sessions = result.scalar() or 0

    # Average confidence (exclude zero-confidence greetings/failed queries)
    result = await db.execute(
        select(func.avg(QueryLog.confidence_score)).where(QueryLog.confidence_score > 0)
    )
    avg_confidence = result.scalar() or 0.0

    # Queries today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    result = await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.created_at >= today_start)
    )
    queries_today = result.scalar() or 0

    # Recent queries
    result = await db.execute(
        select(QueryLog).order_by(desc(QueryLog.created_at)).limit(10)
    )
    recent_queries = [
        {
            "query": q.query,
            "confidence": q.confidence_score,
            "latency_ms": q.latency_ms,
            "created_at": q.created_at.isoformat() if q.created_at else "",
        }
        for q in result.scalars().all()
    ]

    # Usage over time (last 7 days) - use date() for SQLite compatibility
    usage_over_time = []
    for i in range(7):
        day = datetime.now() - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        result = await db.execute(
            select(func.count(QueryLog.id)).where(
                func.date(QueryLog.created_at) == day_str
            )
        )
        count = result.scalar() or 0
        usage_over_time.append({
            "date": day_str,
            "queries": count,
        })

    usage_over_time.reverse()

    # Vector store stats
    vector_stats = await req.app.state.vector_store.get_stats()

    return AnalyticsResponse(
        total_queries=total_queries,
        total_documents=total_documents,
        total_sessions=total_sessions,
        avg_confidence=round(avg_confidence, 3),
        queries_today=queries_today,
        top_sources=[],
        recent_queries=recent_queries,
        usage_over_time=usage_over_time,
    )


@router.post("/feedback")
async def submit_feedback(
    query_id: str,
    feedback: str,
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback for a query response (positive/negative)."""
    result = await db.execute(select(QueryLog).where(QueryLog.id == query_id))
    query_log = result.scalar_one_or_none()

    if query_log:
        query_log.feedback = feedback
        await db.commit()

    return {"status": "ok", "feedback": feedback}
