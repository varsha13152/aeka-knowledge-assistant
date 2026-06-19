"""MCP (Model Context Protocol) Server for AEKA.

Exposes domain tools that AI agents can invoke:
- document_search: Search the knowledge base
- database_query: Query structured data
- get_document_info: Get metadata about a specific document
- schedule_review: Add an item to the HITL review queue

This server can be used standalone or integrated into the LangGraph agents.
"""

import json
import uuid
from dataclasses import dataclass
from typing import Any

from app.db.session import async_session_factory
from app.services.embedding import embedding_service
from app.services.retrieval import hybrid_search


@dataclass
class ToolDefinition:
    """MCP tool definition following the protocol specification."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolResult:
    """Result from executing an MCP tool."""

    content: str
    is_error: bool = False
    metadata: dict | None = None


# ─── Tool Definitions ───────────────────────────────────────────────────────

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="document_search",
        description=(
            "Search the enterprise knowledge base using hybrid search (semantic + keyword). "
            "Returns relevant document chunks ranked by relevance. Use this when you need to "
            "find information from uploaded documents."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query — can be a question or keywords",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                },
                "semantic_weight": {
                    "type": "number",
                    "description": "Weight for semantic search (0-1, default 0.7)",
                    "default": 0.7,
                },
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="get_document_info",
        description=(
            "Get metadata about a specific document including filename, size, "
            "chunk count, and processing status."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "UUID of the document to look up",
                },
            },
            "required": ["document_id"],
        },
    ),
    ToolDefinition(
        name="list_documents",
        description="List all available documents in the knowledge base with their metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max documents to return (default: 20)",
                    "default": 20,
                },
            },
        },
    ),
    ToolDefinition(
        name="schedule_review",
        description=(
            "Schedule a response for human review. Use when you're not confident "
            "in your answer or the query is sensitive."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The original user query"},
                "answer": {"type": "string", "description": "The generated answer to review"},
                "confidence": {
                    "type": "number",
                    "description": "Your confidence score (0-1)",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this needs review",
                },
            },
            "required": ["query", "answer", "confidence", "reason"],
        },
    ),
]


# ─── Tool Execution ─────────────────────────────────────────────────────────


async def execute_tool(name: str, arguments: dict) -> ToolResult:
    """Execute an MCP tool by name with the given arguments."""
    from jsonschema import ValidationError, validate

    handlers = {
        "document_search": _handle_document_search,
        "get_document_info": _handle_get_document_info,
        "list_documents": _handle_list_documents,
        "schedule_review": _handle_schedule_review,
    }

    handler = handlers.get(name)
    if not handler:
        return ToolResult(content=f"Unknown tool: {name}", is_error=True)

    # Validate arguments against the tool's input_schema
    tool_def = next((t for t in TOOLS if t.name == name), None)
    if tool_def and tool_def.input_schema:
        try:
            validate(instance=arguments, schema=tool_def.input_schema)
        except ValidationError as e:
            return ToolResult(content=f"Invalid arguments: {e.message}", is_error=True)

    try:
        return await handler(arguments)
    except Exception as e:
        return ToolResult(content="Tool execution error", is_error=True)


async def _handle_document_search(args: dict) -> ToolResult:
    """Search documents using hybrid retrieval."""
    query = args["query"]
    top_k = args.get("top_k", 5)
    semantic_weight = args.get("semantic_weight", 0.7)

    async with async_session_factory() as db:
        results = await hybrid_search(
            db=db,
            query=query,
            top_k=top_k,
            semantic_weight=semantic_weight,
            keyword_weight=1 - semantic_weight,
        )

    if not results:
        return ToolResult(content="No relevant documents found for this query.")

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[Result {i}] (score: {r.fused_score:.3f})\n"
            f"Document: {r.document_id}\n"
            f"Content: {r.content[:500]}\n"
        )

    return ToolResult(
        content="\n---\n".join(formatted),
        metadata={"result_count": len(results), "top_score": results[0].fused_score},
    )


async def _handle_get_document_info(args: dict) -> ToolResult:
    """Get document metadata by ID."""
    from sqlalchemy import select
    from app.models.document import Document

    doc_id = args["document_id"]

    async with async_session_factory() as db:
        result = await db.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))
        doc = result.scalar_one_or_none()

    if not doc:
        return ToolResult(content=f"Document not found: {doc_id}", is_error=True)

    info = {
        "id": str(doc.id),
        "filename": doc.filename,
        "content_type": doc.content_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
    }
    return ToolResult(content=json.dumps(info, indent=2))


async def _handle_list_documents(args: dict) -> ToolResult:
    """List all documents."""
    from sqlalchemy import select
    from app.models.document import Document

    limit = args.get("limit", 20)

    async with async_session_factory() as db:
        result = await db.execute(
            select(Document).order_by(Document.created_at.desc()).limit(limit)
        )
        docs = result.scalars().all()

    if not docs:
        return ToolResult(content="No documents in the knowledge base.")

    formatted = [
        f"- {doc.filename} ({doc.status}, {doc.chunk_count} chunks, {doc.file_size} bytes)"
        for doc in docs
    ]
    return ToolResult(
        content=f"Found {len(docs)} documents:\n" + "\n".join(formatted),
        metadata={"count": len(docs)},
    )


async def _handle_schedule_review(args: dict) -> ToolResult:
    """Create a HITL review item."""
    from app.models.document import HITLReviewItem

    async with async_session_factory() as db:
        item = HITLReviewItem(
            message_id=uuid.uuid4(),
            query=args["query"],
            generated_answer=args["answer"],
            confidence_score=args["confidence"],
            reason=args["reason"],
            status="pending",
        )
        db.add(item)
        await db.commit()

    return ToolResult(
        content=f"Review scheduled. Item ID: {item.id}. A human reviewer will be notified.",
        metadata={"review_id": str(item.id)},
    )


# ─── MCP Protocol Handlers ─────────────────────────────────────────────────


def get_tool_definitions() -> list[dict]:
    """Return tool definitions in MCP protocol format."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in TOOLS
    ]
