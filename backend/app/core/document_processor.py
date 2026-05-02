"""
Document Processing Pipeline
Handles PDF, DOCX, TXT ingestion with semantic chunking.
"""

import os
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger

from app.config import get_settings


@dataclass
class TextChunk:
    """Represents a processed text chunk with metadata."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    document_id: str = ""
    chunk_index: int = 0
    page_number: Optional[int] = None
    source: str = ""
    token_count: int = 0


class DocumentProcessor:
    """
    Handles document ingestion and semantic chunking.
    
    Architecture Decision: We use semantic chunking over naive fixed-size splitting
    to preserve context boundaries (paragraphs, sections, sentences).
    This significantly improves retrieval quality.
    """

    def __init__(self):
        self.settings = get_settings()

    async def process_file(self, file_path: str, document_id: str, source: str = "upload") -> List[TextChunk]:
        """Main entry point for document processing."""
        ext = os.path.splitext(file_path)[1].lower()

        extractors = {
            ".pdf": self._extract_pdf,
            ".docx": self._extract_docx,
            ".txt": self._extract_txt,
            ".md": self._extract_txt,
        }

        extractor = extractors.get(ext)
        if not extractor:
            raise ValueError(f"Unsupported file type: {ext}")

        logger.info(f"Processing document: {file_path} (type: {ext})")

        # Extract raw text with page information
        pages = await extractor(file_path)

        # Clean and preprocess
        pages = [self._clean_text(page) for page in pages]

        # Semantic chunking
        chunks = self._semantic_chunk(pages, document_id, source, file_path)

        logger.info(f"Generated {len(chunks)} chunks from {file_path}")
        return chunks

    async def _extract_pdf(self, file_path: str) -> List[str]:
        """Extract text from PDF files page by page."""
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return pages

    async def _extract_docx(self, file_path: str) -> List[str]:
        """Extract text from DOCX files."""
        from docx import Document

        doc = Document(file_path)
        full_text = []
        current_section = []

        for para in doc.paragraphs:
            if para.style.name.startswith("Heading"):
                if current_section:
                    full_text.append("\n".join(current_section))
                    current_section = []
            current_section.append(para.text)

        if current_section:
            full_text.append("\n".join(current_section))

        return full_text if full_text else [""]

    async def _extract_txt(self, file_path: str) -> List[str]:
        """Extract text from plain text files."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Split by double newlines as "pages"
        sections = content.split("\n\n\n")
        return sections if sections else [content]

    def _clean_text(self, text: str) -> str:
        """Preprocess and clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove special characters that don't add meaning
        text = re.sub(r"[^\w\s.,;:!?'\"-/()\[\]{}@#$%&*+=<>]", "", text)
        # Normalize quotes
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        return text.strip()

    def _semantic_chunk(
        self, pages: List[str], document_id: str, source: str, file_path: str
    ) -> List[TextChunk]:
        """
        Semantic chunking strategy:
        1. Split by natural boundaries (paragraphs, sentences)
        2. Merge small chunks to meet minimum size
        3. Split large chunks while respecting sentence boundaries
        4. Add overlap for context continuity
        """
        chunks = []
        chunk_index = 0
        chunk_size = self.settings.chunk_size
        overlap = self.settings.chunk_overlap

        for page_idx, page_text in enumerate(pages):
            if not page_text.strip():
                continue

            # Split into sentences
            sentences = self._split_sentences(page_text)

            current_chunk = []
            current_length = 0

            for sentence in sentences:
                sentence_words = len(sentence.split())

                if current_length + sentence_words > chunk_size and current_chunk:
                    # Create chunk
                    chunk_text = " ".join(current_chunk)
                    chunks.append(TextChunk(
                        id=f"{document_id}_chunk_{chunk_index}",
                        content=chunk_text,
                        document_id=document_id,
                        chunk_index=chunk_index,
                        page_number=page_idx + 1,
                        source=source,
                        token_count=len(chunk_text.split()),
                        metadata={
                            "filename": os.path.basename(file_path),
                            "page": page_idx + 1,
                            "source": source,
                            "chunk_index": chunk_index,
                        },
                    ))
                    chunk_index += 1

                    # Overlap: keep last few sentences
                    overlap_sentences = max(1, overlap // 20)
                    current_chunk = current_chunk[-overlap_sentences:]
                    current_length = sum(len(s.split()) for s in current_chunk)

                current_chunk.append(sentence)
                current_length += sentence_words

            # Final chunk from this page
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text.split()) > 20:  # Min chunk size
                    chunks.append(TextChunk(
                        id=f"{document_id}_chunk_{chunk_index}",
                        content=chunk_text,
                        document_id=document_id,
                        chunk_index=chunk_index,
                        page_number=page_idx + 1,
                        source=source,
                        token_count=len(chunk_text.split()),
                        metadata={
                            "filename": os.path.basename(file_path),
                            "page": page_idx + 1,
                            "source": source,
                            "chunk_index": chunk_index,
                        },
                    ))
                    chunk_index += 1

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex-based approach."""
        # Split on sentence boundaries while handling abbreviations
        sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        sentences = sentence_endings.split(text)
        # Filter empty sentences
        return [s.strip() for s in sentences if s.strip()]

    async def process_mock_data(self, data: Dict[str, Any], document_id: str, source: str) -> List[TextChunk]:
        """Process mock data from simulated APIs (Slack, Notion)."""
        chunks = []
        chunk_index = 0

        if source == "slack":
            for message in data.get("messages", []):
                content = f"[{message.get('user', 'unknown')}]: {message.get('text', '')}"
                if len(content.split()) > 10:
                    chunks.append(TextChunk(
                        id=f"{document_id}_chunk_{chunk_index}",
                        content=content,
                        document_id=document_id,
                        chunk_index=chunk_index,
                        source="slack",
                        token_count=len(content.split()),
                        metadata={
                            "channel": message.get("channel", ""),
                            "timestamp": message.get("ts", ""),
                            "source": "slack",
                        },
                    ))
                    chunk_index += 1

        elif source == "notion":
            for page in data.get("pages", []):
                content = f"{page.get('title', '')}\n{page.get('content', '')}"
                page_chunks = self._semantic_chunk(
                    [content], document_id, "notion", page.get("title", "notion_page")
                )
                chunks.extend(page_chunks)

        return chunks
