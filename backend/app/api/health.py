"""Health Check Endpoint"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI Knowledge Copilot", "version": "1.0.0"}
