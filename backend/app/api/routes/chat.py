"""Chat endpoint with streaming SSE responses and RAG context injection."""

import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import DBSession
from app.models.document import ChatMessage, ChatSession
from app.services.llm import llm_client
from app.services.retrieval import build_context_window, hybrid_search

router = APIRouter(prefix="/chat", tags=["chat"])


# ─── Schemas ────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: uuid.UUID | None = None
    use_rag: bool = True
    stream: bool = True
    max_context_tokens: int = Field(default=4096, ge=512, le=16384)


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    message_id: uuid.UUID
    content: str
    sources: list[dict]
    model: str
    latency_ms: int
    cost_usd: float


# ─── System Prompt ──────────────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """You are AEKA, an enterprise knowledge assistant. Answer questions based on the provided context from uploaded documents.

Rules:
1. Only answer based on the provided context. If the context doesn't contain relevant information, say so clearly.
2. Cite your sources using [Source N] notation.
3. Be concise but thorough.
4. If you're uncertain about something, express your confidence level.
5. Never fabricate information not present in the context.

Context from documents:
{context}
"""

NO_RAG_SYSTEM_PROMPT = """You are AEKA, an enterprise knowledge assistant. Answer the user's question helpfully and concisely. If you don't know something, say so clearly."""


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/completions")
async def chat_completion(request: ChatRequest, db: DBSession):
    """Generate a chat completion with optional RAG context.

    Supports both streaming (SSE) and non-streaming responses.
    When streaming, returns Server-Sent Events with JSON data payloads.
    """
    # Get or create session
    if request.session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == request.session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = ChatSession(title=request.message[:100])
        db.add(session)
        await db.flush()

    # Store user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.flush()

    # Build RAG context if enabled
    sources = []
    if request.use_rag:
        retrieval_results = await hybrid_search(db=db, query=request.message, top_k=8)
        context, included_chunks = build_context_window(
            retrieval_results, max_tokens=request.max_context_tokens
        )
        system_prompt = RAG_SYSTEM_PROMPT.format(context=context)
        sources = [
            {
                "chunk_id": str(chunk.chunk_id),
                "document_id": str(chunk.document_id),
                "content_preview": chunk.content[:200],
                "score": chunk.fused_score,
            }
            for chunk in included_chunks
        ]
    else:
        system_prompt = NO_RAG_SYSTEM_PROMPT

    # Build message history
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .limit(20)  # Keep last 20 messages for context
    )
    history = history_result.scalars().all()
    messages = [{"role": msg.role, "content": msg.content} for msg in history]

    if request.stream:
        return StreamingResponse(
            _stream_response(db, session.id, messages, system_prompt, sources),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-streaming response
        response = await llm_client.complete(
            messages=messages,
            system_prompt=system_prompt,
        )

        # Store assistant message
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response.content,
            token_count=response.output_tokens,
            latency_ms=response.latency_ms,
            model_used=response.model,
            cost_usd=response.cost_usd,
        )
        db.add(assistant_msg)

        return ChatResponse(
            session_id=session.id,
            message_id=assistant_msg.id,
            content=response.content,
            sources=sources,
            model=response.model,
            latency_ms=response.latency_ms,
            cost_usd=response.cost_usd,
        )


async def _stream_response(
    db: DBSession,
    session_id: uuid.UUID,
    messages: list[dict],
    system_prompt: str,
    sources: list[dict],
):
    """Generate SSE stream for chat response.

    Event format:
    - event: sources   → RAG source documents
    - event: token     → Individual content tokens
    - event: done      → Final metadata (model, tokens, cost)
    - event: error     → Error information
    """
    # Send sources first
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

    full_content = ""
    metadata = {}

    try:
        async for chunk in llm_client.stream(messages=messages, system_prompt=system_prompt):
            if chunk.is_final:
                metadata = chunk.metadata or {}
            else:
                full_content += chunk.content
                yield f"event: token\ndata: {json.dumps({'content': chunk.content})}\n\n"

        # Send completion event
        yield f"event: done\ndata: {json.dumps(metadata)}\n\n"

        # Store the complete assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_content,
            token_count=metadata.get("output_tokens"),
            latency_ms=metadata.get("latency_ms"),
            model_used=metadata.get("model"),
            cost_usd=metadata.get("cost_usd"),
        )
        db.add(assistant_msg)
        await db.commit()

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.get("/sessions")
async def list_sessions(db: DBSession, limit: int = 20):
    """List recent chat sessions."""
    result = await db.execute(
        select(ChatSession).order_by(ChatSession.created_at.desc()).limit(limit)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: uuid.UUID, db: DBSession):
    """Get all messages in a chat session."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "model": m.model_used,
            "latency_ms": m.latency_ms,
            "cost_usd": m.cost_usd,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
