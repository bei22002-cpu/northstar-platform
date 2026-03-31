"""Tool primitive — extensible tools with registry pattern."""

from agent_v5.tools.base import BaseTool
from agent_v5.tools.filesystem import (
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
    DeleteFileTool,
    SearchFilesTool,
)
from agent_v5.tools.terminal import RunCommandTool
from agent_v5.tools.web import WebSearchTool
from agent_v5.tools.calculator import CalculatorTool

__all__ = [
    "BaseTool",
    "ListFilesTool",
    "ReadFileTool",
    "WriteFileTool",
    "DeleteFileTool",
    "SearchFilesTool",
    "RunCommandTool",
    "WebSearchTool",
    "CalculatorTool",
]


def get_all_tools(workspace: str = ".") -> list[BaseTool]:
    """Return instances of all built-in tools."""
    return [
        ListFilesTool(workspace),
        ReadFileTool(workspace),
        WriteFileTool(workspace),
        DeleteFileTool(workspace),
        SearchFilesTool(workspace),
        RunCommandTool(workspace),
        WebSearchTool(),
        CalculatorTool(),
    ]
