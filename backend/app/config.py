"""
Application Configuration
Centralized configuration management using Pydantic Settings.
Supports .env file loading and environment variable overrides.
"""

from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM Configuration
    openai_api_key: str = ""
    openai_base_url: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"

    # Embedding Configuration
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"

    # Vector Database
    vector_db_type: str = "faiss"
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "knowledge-copilot"

    # Database
    database_url: str = "sqlite:///./data/knowledge_copilot.db"

    # Server Configuration
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    cors_origins: List[str] = ["http://localhost:3000"]

    # Security
    secret_key: str = "change-me-in-production"
    api_key_header: str = "X-API-Key"

    # Chunking Configuration
    chunk_size: int = 512
    chunk_overlap: int = 50
    semantic_chunking: bool = True

    # Retrieval Configuration
    top_k_results: int = 5
    rerank_top_k: int = 3
    hybrid_search_alpha: float = 0.7

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
