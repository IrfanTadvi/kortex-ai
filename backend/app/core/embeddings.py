"""
Embedding Manager
Supports both sentence-transformers (local) and OpenAI embeddings.
Provides a unified interface for embedding generation.
"""

import numpy as np
from typing import List, Optional
from loguru import logger

from app.config import get_settings


class EmbeddingManager:
    """
    Unified embedding interface supporting multiple providers.
    
    Architecture Decision: We abstract the embedding layer to support
    both local (sentence-transformers) and cloud (OpenAI) models.
    Local models provide zero-cost, low-latency embeddings for development,
    while OpenAI offers higher quality for production.
    """

    def __init__(self):
        self.settings = get_settings()
        self._model = None
        self._dimension = None

    @property
    def dimension(self) -> int:
        """Return embedding dimension based on provider."""
        if self._dimension:
            return self._dimension

        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        model_name = (
            self.settings.openai_embedding_model
            if self.settings.embedding_provider == "openai"
            else self.settings.embedding_model
        )
        self._dimension = dimensions.get(model_name, 384)
        return self._dimension

    def _load_model(self):
        """Lazy load the embedding model."""
        if self._model is not None:
            return

        if self.settings.embedding_provider == "sentence-transformers":
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.settings.embedding_model)
            logger.info(f"Loaded sentence-transformer model: {self.settings.embedding_model}")
        elif self.settings.embedding_provider == "openai":
            import openai
            self._model = openai.OpenAI(api_key=self.settings.openai_api_key)
            logger.info(f"Initialized OpenAI embedding client")

    async def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        self._load_model()

        if self.settings.embedding_provider == "sentence-transformers":
            embeddings = self._model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            return np.array(embeddings, dtype=np.float32)

        elif self.settings.embedding_provider == "openai":
            response = self._model.embeddings.create(
                model=self.settings.openai_embedding_model,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings, dtype=np.float32)

        raise ValueError(f"Unknown embedding provider: {self.settings.embedding_provider}")

    async def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        embeddings = await self.embed_texts([query])
        return embeddings[0]
