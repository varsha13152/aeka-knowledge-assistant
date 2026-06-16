"""Chat endpoint with streaming SSE responses, LangGraph agent integration, and RAG."""

import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.graph import AgentState, agent_graph
from app.core.auth import OptionalUser
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
    use_agents: bool = True  # Use multi-agent graph or direct LLM
    max_context_tokens: int = Field(default=4096, ge=512, le=16384)


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    message_id: uuid.UUID | None = None
    content: str
    sources: list[dict]
    agent_steps: list[dict]
    model: str
    latency_ms: int
    cost_usd: float


# ─── System Prompt ──────────────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """You are AEKA, an AI knowledge assistant for a primary science tuition centre. Students ask questions about their lesson materials, and you answer based on the uploaded notes.

Rules:
1. Only answer based on the provided context from tutor-uploaded notes. If the context doesn't contain relevant information, say so clearly.
2. Cite your sources using [Source N] notation.
3. Explain concepts in a way suitable for primary school students.
4. If you're uncertain about something, express your confidence level.
5. Never fabricate information not present in the context.

Context from uploaded notes:
{context}
"""

NO_RAG_SYSTEM_PROMPT = """You are AEKA, an AI knowledge assistant for a primary science tuition centre. Answer the student's question helpfully. If you don't know something, say so clearly."""


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/completions")
async def chat_completion(request: ChatRequest, db: DBSession, user: OptionalUser):
    """Generate a chat completion with optional agent orchestration.

    When use_agents=True (default):
    - Routes through LangGraph multi-agent system
    - Input guardrails → Router → Research → Validator → Output
    - Streams agent steps alongside tokens

    When use_agents=False:
    - Direct RAG: retrieve → generate (simpler, faster)
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

    if request.use_agents and request.stream:
        # ─── Agent-based streaming response ─────────────────────────────
        return StreamingResponse(
            _stream_agent_response(db, session.id, request.message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ─── Direct RAG (non-agent) path ────────────────────────────────────
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
        .limit(20)
    )
    history = history_result.scalars().all()
    messages = [{"role": msg.role, "content": msg.content} for msg in history]

    if request.stream:
        return StreamingResponse(
            _stream_direct_response(db, session.id, messages, system_prompt, sources),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        response = await llm_client.complete(messages=messages, system_prompt=system_prompt)
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
            agent_steps=[],
            model=response.model,
            latency_ms=response.latency_ms,
            cost_usd=response.cost_usd,
        )


# ─── Agent-based Streaming ──────────────────────────────────────────────────


async def _stream_agent_response(db: DBSession, session_id: uuid.UUID, query: str):
    """Stream response from the LangGraph multi-agent system.

    SSE Events:
    - event: agent_step  → Agent node completed (for visualizer)
    - event: sources     → Retrieved source chunks
    - event: token       → Content token (streamed from final answer)
    - event: done        → Final metadata
    - event: error       → Error occurred
    """
    try:
        # Invoke the agent graph — only pass input keys, LangGraph fills the rest
        initial_state = {
            "query": query,
            "session_id": str(session_id),
            "messages": [{"role": "user", "content": query}],
            "agent_steps": [],
            "total_tokens": 0,
            "total_cost": 0.0,
        }

        # Run the graph (non-streaming graph execution, stream the result)
        result = await agent_graph.ainvoke(initial_state)

        # Stream agent steps for the visualizer
        agent_steps = result.get("agent_steps", [])
        for step in agent_steps:
            yield f"event: agent_step\ndata: {json.dumps(step)}\n\n"

        # Stream sources
        sources = result.get("sources", [])
        if sources:
            yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

        # Stream the final answer token by token (simulates streaming for UX)
        final_answer = result.get("final_answer", "I couldn't generate an answer.")
        # Send in word-sized chunks for smooth rendering
        words = final_answer.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"event: token\ndata: {json.dumps({'content': chunk})}\n\n"

        # Send completion metadata
        metadata = {
            "model": "multi-agent",
            "total_tokens": result.get("total_tokens", 0),
            "cost_usd": result.get("total_cost", 0.0),
            "confidence_score": result.get("confidence_score", 0.0),
            "requires_review": result.get("requires_review", False),
        }
        yield f"event: done\ndata: {json.dumps(metadata)}\n\n"

        # Store assistant message in DB
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=final_answer,
            token_count=result.get("total_tokens"),
            model_used="langgraph-multi-agent",
            cost_usd=result.get("total_cost"),
        )
        db.add(assistant_msg)
        await db.commit()

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


# ─── Direct Streaming (non-agent) ───────────────────────────────────────────


async def _stream_direct_response(
    db: DBSession,
    session_id: uuid.UUID,
    messages: list[dict],
    system_prompt: str,
    sources: list[dict],
):
    """Stream a direct LLM response (no agent orchestration)."""
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

        yield f"event: done\ndata: {json.dumps(metadata)}\n\n"

        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_content,
            token_count=metadata.get("output_tokens"),
            model_used=metadata.get("model"),
            cost_usd=metadata.get("cost_usd"),
        )
        db.add(assistant_msg)
        await db.commit()

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


# ─── Session Management ─────────────────────────────────────────────────────


@router.get("/sessions")
async def list_sessions(db: DBSession, limit: int = 20):
    """List recent chat sessions."""
    result = await db.execute(
        select(ChatSession).order_by(ChatSession.created_at.desc()).limit(limit)
    )
    sessions = result.scalars().all()
    return [
        {"id": str(s.id), "title": s.title, "created_at": s.created_at.isoformat()}
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
