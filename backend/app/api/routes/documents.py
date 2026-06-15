"""Document upload, listing, and management endpoints."""

import uuid

import boto3
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import get_settings
from app.core.dependencies import AppSettings, DBSession
from app.models.document import Document, DocumentChunk
from app.services.embedding import embedding_service
from app.services.ingestion import ChunkStrategy, chunk_document, count_tokens, get_parser

router = APIRouter(prefix="/documents", tags=["documents"])

settings = get_settings()


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


class IngestRequest(BaseModel):
    chunk_strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    chunk_size: int = 512
    chunk_overlap: int = 64


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    db: DBSession,
    settings: AppSettings,
    chunk_strategy: ChunkStrategy = ChunkStrategy.RECURSIVE,
):
    """Upload a document and trigger ingestion pipeline.

    1. Upload file to S3/MinIO
    2. Parse document content
    3. Chunk using selected strategy
    4. Generate embeddings for each chunk
    5. Store chunks with vectors in pgvector
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Validate file type
    try:
        parser = get_parser(content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Upload to S3
    s3_key = f"documents/{uuid.uuid4()}/{file.filename}"
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.aws_region,
    )

    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to storage: {e}")

    # Create document record
    doc = Document(
        filename=file.filename,
        content_type=content_type,
        file_size=len(content),
        s3_key=s3_key,
        status="processing",
    )
    db.add(doc)
    await db.flush()

    # Parse and chunk
    try:
        text = parser.parse(content)
        chunks = chunk_document(text, strategy=chunk_strategy)

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
                metadata_json=str(chunk.metadata),
            )
            db.add(db_chunk)

        doc.status = "ready"
        doc.chunk_count = len(chunks)

    except Exception as e:
        doc.status = "error"
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

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
async def list_documents(db: DBSession, skip: int = 0, limit: int = 50):
    """List all uploaded documents with pagination."""
    query = select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()

    count_query = select(Document)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

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
async def get_document(document_id: uuid.UUID, db: DBSession):
    """Get a single document by ID."""
    result = await db.execute(select(Document).where(Document.id == document_id))
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


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, db: DBSession, settings: AppSettings):
    """Delete a document and its chunks."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from S3
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.aws_region,
        )
        s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=doc.s3_key)
    except Exception:
        pass  # Non-fatal: orphaned S3 object can be cleaned up later

    await db.delete(doc)
