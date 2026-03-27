"""API router for the Cornerstone AI Agent web interface."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import ANTHROPIC_API_KEY
from app.models.user import User
from app.services.agent_service import run_agent_chat, WORKSPACE

router = APIRouter(prefix="/agent", tags=["Cornerstone AI Agent"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AgentChatRequest(BaseModel):
    message: str
    history: Optional[list[dict[str, Any]]] = None


class ToolAction(BaseModel):
    tool: str
    input: dict[str, Any]
    output: str


class AgentChatResponse(BaseModel):
    response: str
    tool_actions: list[ToolAction]
    history: list[dict[str, Any]]


class AgentInfoResponse(BaseModel):
    name: str
    description: str
    workspace: str
    tools: list[str]
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(
    payload: AgentChatRequest,
    current_user: User = Depends(get_current_user),
) -> AgentChatResponse:
    """Send a message to the Cornerstone AI Agent and receive a response.

    The agent can read/write files, run commands, search code, and manage
    the project workspace autonomously.  Conversation history can be passed
    back on subsequent requests to maintain context.
    """
    result = run_agent_chat(
        user_message=payload.message,
        history=payload.history,
    )
    return AgentChatResponse(
        response=result["response"],
        tool_actions=[ToolAction(**ta) for ta in result["tool_actions"]],
        history=result["history"],
    )


@router.get("/info", response_model=AgentInfoResponse)
def agent_info(
    current_user: User = Depends(get_current_user),
) -> AgentInfoResponse:
    """Return metadata about the Cornerstone AI Agent."""
    return AgentInfoResponse(
        name="Cornerstone AI Agent",
        description=(
            "An autonomous AI agent powered by Claude that can read, write, "
            "edit, and manage files and run terminal commands inside the "
            "Cornerstone project workspace."
        ),
        workspace=WORKSPACE,
        tools=[
            "write_file",
            "read_file",
            "list_files",
            "run_command",
            "delete_file",
            "create_directory",
            "search_in_files",
            "git_status",
        ],
        status="online" if ANTHROPIC_API_KEY else "unconfigured",
    )
