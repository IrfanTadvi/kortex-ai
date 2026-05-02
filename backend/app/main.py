"""
AI Knowledge Copilot - FastAPI Application Entry Point
Production-grade RAG system with multi-agent architecture.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import get_settings
from app.api import router as api_router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management - startup and shutdown."""
    settings = get_settings()

    # Configure logging
    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="7 days",
        level=settings.log_level,
    )
    logger.info("Starting AI Knowledge Copilot...")

    # Ensure required directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("data/vectors", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("Database initialized.")

    # Initialize vector store
    from app.core.vector_store import VectorStoreManager
    vector_manager = VectorStoreManager()
    await vector_manager.initialize()
    app.state.vector_store = vector_manager
    logger.info("Vector store initialized.")

    # Initialize embedding model (and preload it)
    from app.core.embeddings import EmbeddingManager
    embedding_manager = EmbeddingManager()
    embedding_manager._load_model()  # Preload to avoid first-query delay
    app.state.embeddings = embedding_manager
    logger.info("Embedding model loaded.")

    # Preload cross-encoder re-ranking model
    from app.core.retrieval import CrossEncoderReranker
    reranker = CrossEncoderReranker()
    reranker._load_model()
    app.state.reranker = reranker
    logger.info("Cross-encoder model loaded.")

    yield

    # Cleanup
    logger.info("Shutting down AI Knowledge Copilot...")


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AI Knowledge Copilot",
        description="Enterprise-grade RAG system with multi-agent architecture",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
