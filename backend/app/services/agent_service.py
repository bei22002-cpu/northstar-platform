"""Service layer for the Cornerstone AI Agent web integration.

Adapts the CLI-based Cornerstone AI Agent to work via HTTP by providing
a stateless chat endpoint.  Each request runs the agent loop once and
returns the assistant's text response along with any tool actions that
were executed.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import anthropic

from app.core.config import ANTHROPIC_API_KEY

# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------

WORKSPACE: str = os.path.abspath(
    os.getenv("AGENT_WORKSPACE", os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

SYSTEM_PROMPT = (
    "You are an expert senior software engineer working on the "
    "Cornerstone Platform \u2014 a FastAPI + PostgreSQL backend project. "
    "You have direct access to the project workspace and can read, "
    "write, create, delete files, run commands, and search code.\n\n"
    "Rules:\n"
    "- Always read a file before overwriting it.\n"
    "- Never delete files unless the user explicitly requests it.\n"
    "- Always explain what you are about to do in plain English "
    "before using a tool.\n"
    "- Write clean, production-quality Python code.\n"
    "- Follow the existing project structure and conventions.\n"
    "- After completing a task, summarize what you did."
)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

# ---------------------------------------------------------------------------
# Blocked commands (safety)
# ---------------------------------------------------------------------------

BLOCKED_COMMANDS: list[str] = [
    "rm -rf /",
    "format",
    "del /f /s /q C:\\",
    "shutdown",
    "DROP DATABASE",
    "DROP TABLE",
    ":(){:|:&};:",
]


def _is_blocked(command: str) -> bool:
    cmd_lower = command.lower()
    return any(b.lower() in cmd_lower for b in BLOCKED_COMMANDS)


# ---------------------------------------------------------------------------
# Tool implementations (sandboxed to WORKSPACE)
# ---------------------------------------------------------------------------

def _resolve_safe(path: str) -> str:
    """Resolve *path* relative to WORKSPACE and verify it stays inside."""
    resolved = os.path.realpath(os.path.join(WORKSPACE, path))
    if not resolved.startswith(os.path.realpath(WORKSPACE) + os.sep) and resolved != os.path.realpath(WORKSPACE):
        raise PermissionError(f"Path escapes workspace: {path}")
    return resolved


def _write_file(filepath: str, content: str) -> str:
    full = _resolve_safe(filepath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return f"Successfully wrote {len(content)} characters to {filepath}"


def _read_file(filepath: str) -> str:
    full = _resolve_safe(filepath)
    if not os.path.isfile(full):
        return f"Error: file not found \u2014 {filepath}"
    with open(full, "r", encoding="utf-8") as fh:
        return fh.read()


def _list_files(directory: str = ".") -> str:
    full = _resolve_safe(directory)
    if not os.path.isdir(full):
        return f"Error: directory not found \u2014 {directory}"
    files: list[str] = []
    for root, _dirs, filenames in os.walk(full):
        for name in filenames:
            rel = os.path.relpath(os.path.join(root, name), WORKSPACE)
            files.append(rel)
    files.sort()
    return "\n".join(files[:200]) if files else "(empty directory)"


def _run_command(command: str) -> str:
    if _is_blocked(command):
        return f"BLOCKED: '{command}' matches a dangerous pattern."
    result = subprocess.run(
        command, shell=True, cwd=WORKSPACE,
        capture_output=True, text=True, timeout=60,
    )
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += ("\n" if output else "") + result.stderr
    return output[:5000] or "(no output)"


def _delete_file(filepath: str) -> str:
    full = _resolve_safe(filepath)
    if not os.path.isfile(full):
        return f"Error: file not found \u2014 {filepath}"
    os.remove(full)
    return f"Successfully deleted {filepath}"


def _create_directory(directory: str) -> str:
    full = _resolve_safe(directory)
    os.makedirs(full, exist_ok=True)
    return f"Successfully created directory {directory}"


def _search_in_files(pattern: str, directory: str = ".") -> str:
    full = _resolve_safe(directory)
    if not os.path.isdir(full):
        return f"Error: directory not found \u2014 {directory}"
    matches: list[str] = []
    for root, _dirs, filenames in os.walk(full):
        for name in filenames:
            fpath = os.path.join(root, name)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                    for lineno, line in enumerate(fh, start=1):
                        if pattern in line:
                            rel = os.path.relpath(fpath, WORKSPACE)
                            matches.append(f"{rel}:{lineno}: {line.rstrip()}")
                            if len(matches) >= 50:
                                matches.append("... (truncated at 50)")
                                return "\n".join(matches)
            except (OSError, UnicodeDecodeError):
                continue
    return "\n".join(matches) if matches else "No matches found."


def _git_status() -> str:
    st = subprocess.run(
        "git status", shell=True, cwd=WORKSPACE,
        capture_output=True, text=True, timeout=30,
    )
    diff = subprocess.run(
        "git diff --stat", shell=True, cwd=WORKSPACE,
        capture_output=True, text=True, timeout=30,
    )
    output = st.stdout
    if diff.stdout:
        output += "\n" + diff.stdout
    return output or "(no git output)"


# ---------------------------------------------------------------------------
# Tool schema + dispatcher
# ---------------------------------------------------------------------------

_TOOL_MAP: dict[str, Any] = {
    "write_file": _write_file,
    "read_file": _read_file,
    "list_files": _list_files,
    "run_command": _run_command,
    "delete_file": _delete_file,
    "create_directory": _create_directory,
    "search_in_files": _search_in_files,
    "git_status": _git_status,
}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": "Write content to a file relative to the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path relative to workspace."},
                "content": {"type": "string", "description": "Content to write."},
            },
            "required": ["filepath", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read and return a file's contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path relative to workspace."},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "list_files",
        "description": "Recursively list files in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory path (default: '.').", "default": "."},
            },
            "required": [],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command inside the workspace (60 s timeout).",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file relative to the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path relative to workspace."},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "create_directory",
        "description": "Create a directory (and parents) relative to the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory path to create."},
            },
            "required": ["directory"],
        },
    },
    {
        "name": "search_in_files",
        "description": "Search for a text pattern across files (max 50 results).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text pattern to search for."},
                "directory": {"type": "string", "description": "Directory to search (default: '.').", "default": "."},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "git_status",
        "description": "Run git status and git diff --stat.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def _execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    func = _TOOL_MAP.get(tool_name)
    if func is None:
        return f"Error: unknown tool '{tool_name}'"
    try:
        return func(**tool_input)
    except Exception as exc:
        return f"Error executing {tool_name}: {exc}"


def _make_serializable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_agent_chat(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run a single turn of the Cornerstone AI Agent.

    Parameters
    ----------
    user_message:
        The latest message from the user.
    history:
        Optional conversation history (list of ``{"role": ..., "content": ...}``).

    Returns
    -------
    dict with keys:
        ``response``  - the agent's text reply
        ``tool_actions`` - list of tool calls that were executed
        ``history``   - updated conversation history (for follow-up calls)
    """
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        return {
            "response": "The Cornerstone AI Agent is not configured. "
                        "Please set the ANTHROPIC_API_KEY environment variable.",
            "tool_actions": [],
            "history": history or [],
        }

    client = anthropic.Anthropic(api_key=api_key)

    messages: list[dict[str, Any]] = list(history) if history else []
    messages.append({"role": "user", "content": user_message})

    tool_actions: list[dict[str, Any]] = []
    assistant_text_parts: list[str] = []

    try:
        # Agent loop (max 10 iterations to prevent runaway loops)
        for _ in range(10):
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            serialized_content = _make_serializable(response.content)
            messages.append({"role": "assistant", "content": serialized_content})

            # Collect text blocks
            for block in response.content:
                if hasattr(block, "text"):
                    assistant_text_parts.append(block.text)

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    result = _execute_tool(block.name, block.input)
                    tool_actions.append({
                        "tool": block.name,
                        "input": block.input,
                        "output": result[:2000],
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                messages.append({"role": "user", "content": tool_results})
            else:
                break
    except anthropic.AuthenticationError:
        return {
            "response": "Authentication failed. The ANTHROPIC_API_KEY is invalid or expired. "
                        "Please check your API key and try again.",
            "tool_actions": tool_actions,
            "history": history or [],
        }
    except anthropic.APIError as exc:
        return {
            "response": f"An error occurred while communicating with the AI provider: {exc}",
            "tool_actions": tool_actions,
            "history": history or [],
        }

    return {
        "response": "\n\n".join(assistant_text_parts),
        "tool_actions": tool_actions,
        "history": messages,
    }
