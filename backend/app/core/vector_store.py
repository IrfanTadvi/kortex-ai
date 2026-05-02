"""
Vector Store Manager
FAISS-based vector database with persistence and efficient similarity search.
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from app.config import get_settings
from app.core.document_processor import TextChunk


class VectorStoreManager:
    """
    FAISS Vector Store with metadata management.
    
    Architecture Decision: We use FAISS for local vector storage with
    IVF (Inverted File) indexing for scalability. The metadata is stored
    separately in a JSON sidecar for flexibility.
    
    For production at scale, this can be swapped to Pinecone/Qdrant
    via the same interface.
    """

    def __init__(self):
        self.settings = get_settings()
        self._index = None
        self._metadata: List[Dict[str, Any]] = []
        self._texts: List[str] = []
        self._index_path = "data/vectors/faiss_index.bin"
        self._metadata_path = "data/vectors/metadata.json"

    async def initialize(self):
        """Load existing index or create new one."""
        import faiss

        if os.path.exists(self._index_path) and os.path.exists(self._metadata_path):
            self._index = faiss.read_index(self._index_path)
            with open(self._metadata_path, "r") as f:
                data = json.load(f)
                self._metadata = data.get("metadata", [])
                self._texts = data.get("texts", [])
            logger.info(f"Loaded existing FAISS index with {self._index.ntotal} vectors")
        else:
            # Create new index - using IndexFlatIP for cosine similarity (with normalized vectors)
            from app.core.embeddings import EmbeddingManager
            em = EmbeddingManager()
            dimension = em.dimension
            self._index = faiss.IndexFlatIP(dimension)
            logger.info(f"Created new FAISS index with dimension {dimension}")

    async def add_chunks(self, chunks: List[TextChunk], embeddings: np.ndarray):
        """Add document chunks and their embeddings to the index."""
        import faiss

        if embeddings.shape[0] != len(chunks):
            raise ValueError("Embeddings count must match chunks count")

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Add to FAISS index
        self._index.add(embeddings)

        # Store metadata and texts
        for chunk in chunks:
            self._metadata.append(chunk.metadata)
            self._texts.append(chunk.content)

        # Persist
        await self._save()
        logger.info(f"Added {len(chunks)} chunks to vector store. Total: {self._index.ntotal}")

    async def search(
        self, query_embedding: np.ndarray, top_k: int = 10
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        """
        Perform similarity search.
        Returns list of (text, metadata, score) tuples.
        """
        import faiss

        if self._index.ntotal == 0:
            return []

        # Normalize query embedding
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self._index.search(query_embedding, min(top_k, self._index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((
                self._texts[idx],
                self._metadata[idx],
                float(score),
            ))

        return results

    async def delete_document(self, document_id: str):
        """Remove all vectors for a specific document."""
        # Find indices to keep
        indices_to_keep = []
        for i, meta in enumerate(self._metadata):
            if meta.get("document_id") != document_id:
                indices_to_keep.append(i)

        if len(indices_to_keep) == len(self._metadata):
            return  # Nothing to delete

        # Rebuild index without deleted vectors
        import faiss
        from app.core.embeddings import EmbeddingManager
        em = EmbeddingManager()

        new_metadata = [self._metadata[i] for i in indices_to_keep]
        new_texts = [self._texts[i] for i in indices_to_keep]

        # Reconstruct vectors from index
        if indices_to_keep:
            vectors = np.array([self._index.reconstruct(i) for i in indices_to_keep])
            self._index = faiss.IndexFlatIP(em.dimension)
            self._index.add(vectors)
        else:
            self._index = faiss.IndexFlatIP(em.dimension)

        self._metadata = new_metadata
        self._texts = new_texts

        await self._save()
        logger.info(f"Deleted document {document_id} from vector store")

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "total_vectors": self._index.ntotal if self._index else 0,
            "total_documents": len(set(m.get("document_id", "") for m in self._metadata)),
            "dimension": self._index.d if self._index else 0,
        }

    async def _save(self):
        """Persist index and metadata to disk."""
        import faiss

        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        faiss.write_index(self._index, self._index_path)

        with open(self._metadata_path, "w") as f:
            json.dump({
                "metadata": self._metadata,
                "texts": self._texts,
            }, f)
