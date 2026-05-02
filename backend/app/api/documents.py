"""
Document Management API Routes
Handles file upload, processing, and management.
"""

import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.core.database import get_db, Document
from app.core.document_processor import DocumentProcessor
from app.models.schemas import DocumentResponse, DocumentListResponse, DocumentSummaryRequest, DocumentSummaryResponse
from app.core.llm_client import LLMClient

router = APIRouter()

UPLOAD_DIR = "data/uploads"
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    req: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Upload and process a document."""
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB")

    # Save file
    doc_id = str(uuid.uuid4())
    filename = f"{doc_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create database record
    doc = Document(
        id=doc_id,
        filename=file.filename,
        file_type=ext,
        file_size=len(content),
        source="upload",
        status="processing",
    )
    db.add(doc)
    await db.commit()

    # Process document asynchronously
    try:
        processor = DocumentProcessor()
        chunks = await processor.process_file(file_path, doc_id)

        # Generate embeddings
        embedding_manager = req.app.state.embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = await embedding_manager.embed_texts(texts)

        # Store in vector database
        vector_store = req.app.state.vector_store
        await vector_store.add_chunks(chunks, embeddings)

        # Update document status
        doc.status = "ready"
        doc.chunk_count = len(chunks)
        await db.commit()

        logger.info(f"Document {file.filename} processed: {len(chunks)} chunks")

    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        doc.status = "error"
        await db.commit()
        raise HTTPException(500, f"Processing failed: {str(e)}")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        source=doc.source,
        status=doc.status,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all uploaded documents."""
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                source=doc.source,
                status=doc.status,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at.isoformat() if doc.created_at else "",
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its vectors."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(404, "Document not found")

    # Remove from vector store
    vector_store = req.app.state.vector_store
    await vector_store.delete_document(document_id)

    # Remove file
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}_{doc.filename}")
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove from database
    await db.delete(doc)
    await db.commit()

    return {"status": "deleted", "document_id": document_id}


@router.get("/{document_id}/view")
async def view_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Serve uploaded document file for viewing."""
    from fastapi.responses import FileResponse

    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    file_path = os.path.join(UPLOAD_DIR, f"{document_id}_{doc.filename}")
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found on disk")

    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }
    media_type = media_types.get(doc.file_type, "application/octet-stream")
    return FileResponse(file_path, media_type=media_type, filename=doc.filename)


@router.post("/summarize", response_model=DocumentSummaryResponse)
async def summarize_document(
    request: DocumentSummaryRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a summary of an uploaded document."""
    result = await db.execute(select(Document).where(Document.id == request.document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(404, "Document not found")

    # Get document chunks from vector store
    vector_store = req.app.state.vector_store
    doc_texts = [
        text for text, meta in zip(vector_store._texts, vector_store._metadata)
        if meta.get("filename") == doc.filename
    ]

    if not doc_texts:
        raise HTTPException(404, "Document content not found in vector store")

    # Generate summary using LLM
    llm = LLMClient()
    content_sample = "\n\n".join(doc_texts[:10])  # First 10 chunks

    messages = [{
        "role": "user",
        "content": f"Provide a comprehensive summary of this document in {request.max_length} words or less. Also list 3-5 key topics.\n\nDocument content:\n{content_sample}",
    }]

    summary = await llm.generate(
        messages=messages,
        system_prompt="You are a document summarization assistant. Be concise and accurate.",
        max_tokens=request.max_length * 2,
    )

    return DocumentSummaryResponse(
        document_id=request.document_id,
        summary=summary,
        key_topics=[],  # Could parse from LLM response
    )


@router.post("/ingest-mock")
async def ingest_mock_data(
    source: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Ingest mock data from simulated external sources (Slack, Notion)."""
    mock_sources = {
        "slack": {
            "messages": [
                {"user": "alice", "text": "Hey team, the new deployment pipeline is ready. Please review the documentation in Confluence.", "channel": "engineering", "ts": "2024-01-15T10:00:00Z"},
                {"user": "bob", "text": "The Q4 performance review cycle starts next week. All managers need to submit reviews by Friday.", "channel": "hr-announcements", "ts": "2024-01-14T09:00:00Z"},
                {"user": "carol", "text": "Reminder: Company all-hands meeting tomorrow at 2 PM. Topic: 2024 roadmap and OKRs.", "channel": "general", "ts": "2024-01-13T15:00:00Z"},
                {"user": "david", "text": "The new employee onboarding portal is live. New hires should complete all modules in the first week.", "channel": "hr", "ts": "2024-01-12T11:00:00Z"},
                {"user": "eve", "text": "Bug fix deployed for the authentication service. The intermittent 503 errors should be resolved now.", "channel": "engineering", "ts": "2024-01-11T16:00:00Z"},
            ]
        },
        "notion": {
            "pages": [
                {"title": "Engineering Best Practices", "content": "Our engineering team follows these core practices: 1. Code Review: All PRs require at least 2 approvals. 2. Testing: Minimum 80% code coverage. 3. Documentation: All public APIs must be documented. 4. Deployment: Use blue-green deployments for zero-downtime releases."},
                {"title": "Company PTO Policy", "content": "Employees receive 20 days of paid time off per year. PTO requests should be submitted at least 2 weeks in advance for periods longer than 3 days. Unused PTO can be carried over (max 5 days). Sick leave is separate and unlimited with documentation."},
                {"title": "Incident Response Playbook", "content": "Severity 1 (Critical): Immediate response required. Page on-call engineer. Create incident channel. Update status page within 15 minutes. Post-mortem required within 48 hours. Severity 2 (High): Response within 1 hour. Notify team lead. Track in incident management tool."},
            ]
        },
    }

    if source not in mock_sources:
        raise HTTPException(400, f"Unknown source: {source}. Available: {list(mock_sources.keys())}")

    # Process mock data
    doc_id = str(uuid.uuid4())
    processor = DocumentProcessor()
    chunks = await processor.process_mock_data(mock_sources[source], doc_id, source)

    if chunks:
        # Generate embeddings and store
        embedding_manager = req.app.state.embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = await embedding_manager.embed_texts(texts)

        vector_store = req.app.state.vector_store
        await vector_store.add_chunks(chunks, embeddings)

        # Create document record
        doc = Document(
            id=doc_id,
            filename=f"mock_{source}_data",
            file_type="mock",
            source=source,
            status="ready",
            chunk_count=len(chunks),
        )
        db.add(doc)
        await db.commit()

    return {
        "status": "success",
        "source": source,
        "chunks_ingested": len(chunks),
        "document_id": doc_id,
    }
