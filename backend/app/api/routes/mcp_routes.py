"""MCP (Model Context Protocol) HTTP endpoints.

Exposes the MCP tool server over HTTP for external LLM clients:
- GET /mcp/tools — List available tools (discovery)
- POST /mcp/execute — Execute a tool by name
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.auth import AdminUser
from app.mcp.server import execute_tool, get_tool_definitions

router = APIRouter(prefix="/mcp", tags=["mcp"])


class ToolExecuteRequest(BaseModel):
    name: str
    arguments: dict = {}


class ToolExecuteResponse(BaseModel):
    content: str
    is_error: bool
    metadata: dict | None = None


@router.get("/tools")
async def list_tools(current_user: AdminUser):
    """List all available MCP tools with their schemas.

    Clients use this for tool discovery — the response follows
    the MCP protocol format for tool definitions.
    Requires admin/tutor role.
    """
    return {"tools": get_tool_definitions()}


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_mcp_tool(request: ToolExecuteRequest, current_user: AdminUser):
    """Execute an MCP tool by name with the provided arguments.

    The tool name must match one returned by GET /mcp/tools.
    Arguments are validated against the tool's input_schema.
    Requires admin/tutor role.
    """
    result = await execute_tool(request.name, request.arguments)

    if result.is_error:
        raise HTTPException(status_code=400, detail=result.content)

    return ToolExecuteResponse(
        content=result.content,
        is_error=result.is_error,
        metadata=result.metadata,
    )
