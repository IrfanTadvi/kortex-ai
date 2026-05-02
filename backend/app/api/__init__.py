"""
API Router Registry
Aggregates all route modules into a single router.
"""

from fastapi import APIRouter
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.analytics import router as analytics_router
from app.api.sessions import router as sessions_router
from app.api.sql_query import router as sql_router
from app.api.health import router as health_router

router = APIRouter()

router.include_router(health_router, tags=["Health"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(documents_router, prefix="/documents", tags=["Documents"])
router.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
router.include_router(sql_router, prefix="/sql", tags=["SQL"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
