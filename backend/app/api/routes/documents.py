"""Document upload, listing, and management endpoints."""

import asyncio
import json
import re
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.dependencies import AppSettings, DBSession
from app.models.document import Document, DocumentChunk
from app.services.embedding import embedding_service
from app.services.ingestion import ChunkStrategy, chunk_document, get_parser
from app.services.storage import storage_service

router = APIRouter(prefix="/documents", tags=["documents"])

settings = get_settings()

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Magic byte signatures for supported file types
_MAGIC_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _detect_content_type(content: bytes) -> str | None:
    """Detect content type from magic bytes. Returns None if unknown."""
    for signature, mime_type in _MAGIC_SIGNATURES.items():
        if content[:len(signature)] == signature:
            return mime_type
    # For text files, check if content is valid UTF-8
    try:
        content[:1024].decode("utf-8")
        return None  # Could be text/plain or text/markdown — trust the client header
    except UnicodeDecodeError:
        return None


def _sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and special character issues."""
    # Strip directory components
    filename = filename.rsplit("/", 1)[-1]
    filename = filename.rsplit("\\", 1)[-1]
    # Remove null bytes and control characters
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    # Keep only safe characters
    filename = re.sub(r"[^\w\s\-.]", "_", filename)
    # Collapse multiple underscores/spaces
    filename = re.sub(r"[_\s]+", "_", filename).strip("_. ")
    # Limit length
    return filename[:255] if filename else "unnamed"


# ─── Schemas ────────────────────────────────────────────────────────────────


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    status: str
    chunk_count: int
    created_at: str

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    db: DBSession,
    settings: AppSettings,
    current_user: CurrentUser,
    chunk_strategy: ChunkStrategy = ChunkStrategy.RECURSIVE,
):
    """Upload a document and trigger ingestion pipeline.

    1. Upload file to Cloudflare R2
    2. Parse document content
    3. Chunk using selected strategy
    4. Generate embeddings for each chunk
    5. Store chunks with vectors in pgvector
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    safe_filename = _sanitize_filename(file.filename)
    content = await file.read()

    # Enforce file size limit
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB",
        )

    content_type = file.content_type or "application/octet-stream"

    # Verify content-type via magic bytes (don't trust client header alone)
    detected_type = _detect_content_type(content)
    if detected_type and detected_type != content_type:
        content_type = detected_type  # Trust magic bytes over client header

    # Validate file type
    try:
        parser = get_parser(content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Upload to R2 (non-blocking)
    s3_key = f"documents/{uuid.uuid4()}/{safe_filename}"
    try:
        await storage_service.upload_object(key=s3_key, body=content, content_type=content_type)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to upload to storage")

    # Create document record (owned by the authenticated user)
    doc = Document(
        user_id=current_user.id,
        filename=safe_filename,
        content_type=content_type,
        file_size=len(content),
        s3_key=s3_key,
        status="processing",
    )
    db.add(doc)
    await db.flush()

    # Parse and chunk (CPU-bound — run in thread pool to avoid blocking event loop)
    try:
        text = await asyncio.to_thread(parser.parse, content)
        chunks = await asyncio.to_thread(chunk_document, text, strategy=chunk_strategy)

        # Generate embeddings in batch
        chunk_texts = [c.content for c in chunks]
        embeddings = await embedding_service.embed_batch(chunk_texts)

        # Store chunks with embeddings
        for chunk, embedding in zip(chunks, embeddings):
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=embedding,
                metadata_json=json.dumps(chunk.metadata),
            )
            db.add(db_chunk)

        doc.status = "ready"
        doc.chunk_count = len(chunks)

    except Exception:
        doc.status = "error"
        raise HTTPException(status_code=500, detail="Document ingestion failed")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        file_size=doc.file_size,
        status=doc.status,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat(),
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = 50,
    cursor: str | None = None,
):
    """List documents owned by the current user with cursor-based pagination.

    Pass the `created_at` value of the last item as `cursor` for the next page.
    """
    limit = min(limit, 100)  # Cap pagination
    query = (
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    if cursor:
        from datetime import datetime
        query = query.where(Document.created_at < datetime.fromisoformat(cursor))

    result = await db.execute(query)
    documents = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=d.id,
                filename=d.filename,
                content_type=d.content_type,
                file_size=d.file_size,
                status=d.status,
                chunk_count=d.chunk_count,
                created_at=d.created_at.isoformat(),
            )
            for d in documents
        ],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    """Get a single document by ID (must be owned by the current user)."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        file_size=doc.file_size,
        status=doc.status,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat(),
    )


@router.get("/{document_id}/url")
async def get_document_url(document_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    """Get a presigned URL to download the original document from R2."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    url = storage_service.generate_presigned_url(doc.s3_key)
    return {"url": url, "filename": doc.filename, "content_type": doc.content_type}


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, db: DBSession, settings: AppSettings, current_user: CurrentUser):
    """Delete a document and its chunks. Must be owned by the current user."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from R2 (non-blocking)
    try:
        await storage_service.delete_object(key=doc.s3_key)
    except Exception:
        pass  # Non-fatal: orphaned object can be cleaned up later

    await db.delete(doc)
