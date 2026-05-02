"""
SQL Query API Routes
Natural language to SQL conversion and execution.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.agents.sql_agent import SQLGeneratorAgent
from app.models.schemas import SQLQueryRequest, SQLQueryResponse

router = APIRouter()


@router.post("/query", response_model=SQLQueryResponse)
async def execute_sql_query(
    request: SQLQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Convert natural language to SQL and execute."""
    agent = SQLGeneratorAgent()
    result = await agent.process(request.query)

    return SQLQueryResponse(
        status=result.get("status", "error"),
        sql=result.get("sql", ""),
        results=result.get("results", []),
        explanation=result.get("explanation", ""),
        row_count=result.get("row_count", 0),
    )
