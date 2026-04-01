"""Service layer for the Cornerstone AI Agent web integration.

Supports multiple AI providers (Anthropic, OpenAI, Google), streaming responses,
audit logging, approval workflows, and usage tracking.
"""

from __future__ import annotations

import os
import subprocess
import time
import uuid
import json
from typing import Any, Generator

import anthropic
import openai

from app.core.config import ANTHROPIC_API_KEY, OPENAI_API_KEY

# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------

WORKSPACE: str = os.path.abspath(
    os.getenv("AGENT_WORKSPACE", os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

DEFAULT_SYSTEM_PROMPT = (
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

MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "anthropic": {
        "default_model": "claude-sonnet-4-20250514",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
        "max_tokens": 4096,
    },
    "openai": {
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "max_tokens": 4096,
    },
    "google": {
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
        "max_tokens": 4096,
    },
}

BLOCKED_PATTERNS: list[str] = [
    "rm -rf /", "rm -r -f /", "rm -rf /*", "format c:",
    "del /f /s /q c:\\", "shutdown", "reboot", "halt",
    "drop database", "drop table", "truncate table",
    ":(){:|:&};:", "mkfs", "dd if=", "> /dev/sda",
    "chmod -r 777 /", "curl | bash", "curl | sh",
    "wget | bash", "wget | sh",
]


def _is_blocked(command: str) -> bool:
    cmd_lower = command.lower().strip()
    return any(b.lower() in cmd_lower for b in BLOCKED_PATTERNS)


DESTRUCTIVE_TOOLS = {"write_file", "delete_file", "run_command", "create_directory"}
SAFE_TOOLS = {"read_file", "list_files", "search_in_files", "git_status"}


def _resolve_safe(path: str) -> str:
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
        return f"Error: file not found - {filepath}"
    with open(full, "r", encoding="utf-8") as fh:
        return fh.read()


def _list_files(directory: str = ".") -> str:
    full = _resolve_safe(directory)
    if not os.path.isdir(full):
        return f"Error: directory not found - {directory}"
    files: list[str] = []
    for root, _dirs, filenames in os.walk(full):
        for name in filenames:
            rel = os.path.relpath(os.path.join(root, name), WORKSPACE)
            files.append(rel)
    files.sort()
    return "\n".join(files[:200]) if files else "(empty directory)"


def _run_command(command: str) -> str:
    if _is_blocked(command):
        return f"BLOCKED: \'{command}\' matches a dangerous pattern."
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
        return f"Error: file not found - {filepath}"
    os.remove(full)
    return f"Successfully deleted {filepath}"


def _create_directory(directory: str) -> str:
    full = _resolve_safe(directory)
    os.makedirs(full, exist_ok=True)
    return f"Successfully created directory {directory}"


def _search_in_files(pattern: str, directory: str = ".") -> str:
    full = _resolve_safe(directory)
    if not os.path.isdir(full):
        return f"Error: directory not found - {directory}"
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
        "description": "Read and return a file\'s contents.",
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
                "directory": {"type": "string", "description": "Directory path (default: \'.\').", "default": "."},
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
                "directory": {"type": "string", "description": "Directory to search (default: \'.\').", "default": "."},
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

OPENAI_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": td["name"],
            "description": td["description"],
            "parameters": td["input_schema"],
        },
    }
    for td in TOOL_DEFINITIONS
]


def _execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    func = _TOOL_MAP.get(tool_name)
    if func is None:
        return f"Error: unknown tool \'{tool_name}\'"
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


def get_available_providers() -> list[dict[str, Any]]:
    providers = []
    if ANTHROPIC_API_KEY:
        providers.append({
            "id": "anthropic",
            "name": "Anthropic (Claude)",
            "models": MODEL_CONFIGS["anthropic"]["models"],
            "default_model": MODEL_CONFIGS["anthropic"]["default_model"],
        })
    if OPENAI_API_KEY:
        providers.append({
            "id": "openai",
            "name": "OpenAI (GPT-4)",
            "models": MODEL_CONFIGS["openai"]["models"],
            "default_model": MODEL_CONFIGS["openai"]["default_model"],
        })
    if GOOGLE_API_KEY:
        providers.append({
            "id": "google",
            "name": "Google (Gemini)",
            "models": MODEL_CONFIGS["google"]["models"],
            "default_model": MODEL_CONFIGS["google"]["default_model"],
        })
    return providers


def _run_anthropic_loop(
    user_message: str,
    history: list[dict[str, Any]] | None,
    model: str,
    system_prompt: str,
    max_iterations: int,
    require_approval: bool,
    tools_enabled: list[str] | None,
) -> dict[str, Any]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    messages: list[dict[str, Any]] = list(history) if history else []
    messages.append({"role": "user", "content": user_message})
    tool_actions: list[dict[str, Any]] = []
    assistant_text_parts: list[str] = []
    pending_approvals: list[dict[str, Any]] = []
    tokens_input = 0
    tokens_output = 0
    tool_defs = TOOL_DEFINITIONS
    if tools_enabled:
        tool_defs = [t for t in TOOL_DEFINITIONS if t["name"] in tools_enabled]
    try:
        for _ in range(max_iterations):
            response = client.messages.create(
                model=model,
                max_tokens=MODEL_CONFIGS["anthropic"]["max_tokens"],
                system=system_prompt,
                tools=tool_defs,
                messages=messages,
            )
            tokens_input += response.usage.input_tokens
            tokens_output += response.usage.output_tokens
            serialized_content = _make_serializable(response.content)
            messages.append({"role": "assistant", "content": serialized_content})
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
                    if require_approval and block.name in DESTRUCTIVE_TOOLS:
                        pending_approvals.append({
                            "tool": block.name, "input": block.input, "tool_use_id": block.id,
                        })
                        tool_results.append({
                            "type": "tool_result", "tool_use_id": block.id,
                            "content": "[PENDING USER APPROVAL] This action requires user confirmation.",
                        })
                        tool_actions.append({
                            "tool": block.name, "input": block.input,
                            "output": "[Pending approval]", "status": "pending_approval",
                        })
                    else:
                        result = _execute_tool(block.name, block.input)
                        tool_actions.append({
                            "tool": block.name, "input": block.input,
                            "output": result[:2000], "status": "executed",
                        })
                        tool_results.append({
                            "type": "tool_result", "tool_use_id": block.id, "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})
                if pending_approvals:
                    assistant_text_parts.append(
                        "\n\n**Approval Required:** I need your permission to execute "
                        + str(len(pending_approvals)) + " action(s) before proceeding."
                    )
                    break
            else:
                break
    except anthropic.AuthenticationError:
        return {
            "response": "Authentication failed. The ANTHROPIC_API_KEY is invalid or expired. "
                        "Please check your API key and try again.",
            "tool_actions": tool_actions, "history": history or [],
            "pending_approvals": [], "tokens_input": 0, "tokens_output": 0,
            "provider": "anthropic", "model": model,
        }
    except anthropic.APIError as exc:
        return {
            "response": "An error occurred while communicating with the AI provider: " + str(exc),
            "tool_actions": tool_actions, "history": history or [],
            "pending_approvals": [], "tokens_input": 0, "tokens_output": 0,
            "provider": "anthropic", "model": model,
        }
    return {
        "response": "\n\n".join(assistant_text_parts),
        "tool_actions": tool_actions, "history": messages,
        "pending_approvals": pending_approvals,
        "tokens_input": tokens_input, "tokens_output": tokens_output,
        "provider": "anthropic", "model": model,
    }


def _run_openai_loop(
    user_message: str,
    history: list[dict[str, Any]] | None,
    model: str,
    system_prompt: str,
    max_iterations: int,
    require_approval: bool,
    tools_enabled: list[str] | None,
) -> dict[str, Any]:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    tool_actions: list[dict[str, Any]] = []
    assistant_text_parts: list[str] = []
    pending_approvals: list[dict[str, Any]] = []
    tokens_input = 0
    tokens_output = 0
    tool_defs = OPENAI_TOOL_DEFINITIONS
    if tools_enabled:
        tool_defs = [t for t in OPENAI_TOOL_DEFINITIONS if t["function"]["name"] in tools_enabled]
    try:
        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=model,
                max_tokens=MODEL_CONFIGS["openai"]["max_tokens"],
                messages=messages,
                tools=tool_defs if tool_defs else None,
            )
            choice = response.choices[0]
            if response.usage:
                tokens_input += response.usage.prompt_tokens
                tokens_output += response.usage.completion_tokens
            if choice.message.content:
                assistant_text_parts.append(choice.message.content)
            msg_dict: dict[str, Any] = {"role": "assistant", "content": choice.message.content or ""}
            if choice.message.tool_calls:
                msg_dict["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.message.tool_calls
                ]
            messages.append(msg_dict)
            if choice.finish_reason == "stop":
                break
            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_name = tc.function.name
                    tool_input = json.loads(tc.function.arguments)
                    if require_approval and tool_name in DESTRUCTIVE_TOOLS:
                        pending_approvals.append({"tool": tool_name, "input": tool_input, "tool_use_id": tc.id})
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": "[PENDING USER APPROVAL]"})
                        tool_actions.append({"tool": tool_name, "input": tool_input, "output": "[Pending approval]", "status": "pending_approval"})
                    else:
                        result = _execute_tool(tool_name, tool_input)
                        tool_actions.append({"tool": tool_name, "input": tool_input, "output": result[:2000], "status": "executed"})
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                if pending_approvals:
                    assistant_text_parts.append(
                        "\n\n**Approval Required:** I need your permission to execute "
                        + str(len(pending_approvals)) + " action(s) before proceeding."
                    )
                    break
            else:
                break
    except openai.AuthenticationError:
        return {
            "response": "Authentication failed. The OPENAI_API_KEY is invalid or expired.",
            "tool_actions": tool_actions, "history": [], "pending_approvals": [],
            "tokens_input": 0, "tokens_output": 0, "provider": "openai", "model": model,
        }
    except openai.APIError as exc:
        return {
            "response": "An error occurred while communicating with OpenAI: " + str(exc),
            "tool_actions": tool_actions, "history": [], "pending_approvals": [],
            "tokens_input": 0, "tokens_output": 0, "provider": "openai", "model": model,
        }
    return {
        "response": "\n\n".join(assistant_text_parts),
        "tool_actions": tool_actions, "history": messages[1:],
        "pending_approvals": pending_approvals,
        "tokens_input": tokens_input, "tokens_output": tokens_output,
        "provider": "openai", "model": model,
    }


def _run_google_loop(
    user_message: str,
    history: list[dict[str, Any]] | None,
    model: str,
    system_prompt: str,
    max_iterations: int,
    require_approval: bool,
    tools_enabled: list[str] | None,
) -> dict[str, Any]:
    client = openai.OpenAI(
        api_key=GOOGLE_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    tool_actions: list[dict[str, Any]] = []
    assistant_text_parts: list[str] = []
    tokens_input = 0
    tokens_output = 0
    tool_defs = OPENAI_TOOL_DEFINITIONS
    if tools_enabled:
        tool_defs = [t for t in OPENAI_TOOL_DEFINITIONS if t["function"]["name"] in tools_enabled]
    try:
        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=model,
                max_tokens=MODEL_CONFIGS["google"]["max_tokens"],
                messages=messages,
                tools=tool_defs if tool_defs else None,
            )
            choice = response.choices[0]
            if response.usage:
                tokens_input += response.usage.prompt_tokens
                tokens_output += response.usage.completion_tokens
            if choice.message.content:
                assistant_text_parts.append(choice.message.content)
            msg_dict: dict[str, Any] = {"role": "assistant", "content": choice.message.content or ""}
            if choice.message.tool_calls:
                msg_dict["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.message.tool_calls
                ]
            messages.append(msg_dict)
            if choice.finish_reason == "stop":
                break
            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_name = tc.function.name
                    tool_input = json.loads(tc.function.arguments)
                    result = _execute_tool(tool_name, tool_input)
                    tool_actions.append({"tool": tool_name, "input": tool_input, "output": result[:2000], "status": "executed"})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            else:
                break
    except Exception as exc:
        return {
            "response": "Error communicating with Google Gemini: " + str(exc),
            "tool_actions": tool_actions, "history": [], "pending_approvals": [],
            "tokens_input": 0, "tokens_output": 0, "provider": "google", "model": model,
        }
    return {
        "response": "\n\n".join(assistant_text_parts),
        "tool_actions": tool_actions, "history": messages[1:],
        "pending_approvals": [], "tokens_input": tokens_input, "tokens_output": tokens_output,
        "provider": "google", "model": model,
    }


def stream_agent_chat_anthropic(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    model: str | None = None,
    system_prompt: str | None = None,
) -> Generator[str, None, None]:
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        yield "data: " + json.dumps({"type": "error", "content": "ANTHROPIC_API_KEY not configured"}) + "\n\n"
        return
    client = anthropic.Anthropic(api_key=api_key)
    _model = model or MODEL_CONFIGS["anthropic"]["default_model"]
    _system = system_prompt or DEFAULT_SYSTEM_PROMPT
    messages: list[dict[str, Any]] = list(history) if history else []
    messages.append({"role": "user", "content": user_message})
    tool_actions: list[dict[str, Any]] = []
    try:
        for iteration in range(10):
            yield "data: " + json.dumps({"type": "iteration_start", "iteration": iteration}) + "\n\n"
            with client.messages.stream(
                model=_model,
                max_tokens=MODEL_CONFIGS["anthropic"]["max_tokens"],
                system=_system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                current_text = ""
                for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            if hasattr(event.delta, "text"):
                                current_text += event.delta.text
                                yield "data: " + json.dumps({"type": "text_delta", "content": event.delta.text}) + "\n\n"
                response = stream.get_final_message()
            serialized_content = _make_serializable(response.content)
            messages.append({"role": "assistant", "content": serialized_content})
            if response.stop_reason == "end_turn":
                break
            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    yield "data: " + json.dumps({"type": "tool_start", "tool": block.name, "input": block.input}) + "\n\n"
                    result = _execute_tool(block.name, block.input)
                    tool_actions.append({"tool": block.name, "input": block.input, "output": result[:2000], "status": "executed"})
                    yield "data: " + json.dumps({"type": "tool_result", "tool": block.name, "output": result[:500]}) + "\n\n"
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                messages.append({"role": "user", "content": tool_results})
            else:
                break
        yield "data: " + json.dumps({"type": "done", "tool_actions": tool_actions, "history": messages}) + "\n\n"
    except anthropic.AuthenticationError:
        yield "data: " + json.dumps({"type": "error", "content": "Authentication failed. ANTHROPIC_API_KEY is invalid."}) + "\n\n"
    except anthropic.APIError as exc:
        yield "data: " + json.dumps({"type": "error", "content": "API error: " + str(exc)}) + "\n\n"


def run_agent_chat(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    provider: str = "anthropic",
    model: str | None = None,
    system_prompt: str | None = None,
    max_iterations: int = 10,
    require_approval: bool = False,
    tools_enabled: list[str] | None = None,
) -> dict[str, Any]:
    start_time = time.time()
    _system = system_prompt or DEFAULT_SYSTEM_PROMPT
    if provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            return _unconfigured_response("ANTHROPIC_API_KEY", history)
        _model = model or MODEL_CONFIGS["anthropic"]["default_model"]
        result = _run_anthropic_loop(user_message, history, _model, _system, max_iterations, require_approval, tools_enabled)
    elif provider == "openai":
        if not OPENAI_API_KEY:
            return _unconfigured_response("OPENAI_API_KEY", history)
        _model = model or MODEL_CONFIGS["openai"]["default_model"]
        result = _run_openai_loop(user_message, history, _model, _system, max_iterations, require_approval, tools_enabled)
    elif provider == "google":
        if not GOOGLE_API_KEY:
            return _unconfigured_response("GOOGLE_API_KEY", history)
        _model = model or MODEL_CONFIGS["google"]["default_model"]
        result = _run_google_loop(user_message, history, _model, _system, max_iterations, require_approval, tools_enabled)
    else:
        return {
            "response": "Unknown provider: " + provider + ". Supported: anthropic, openai, google.",
            "tool_actions": [], "history": history or [], "pending_approvals": [],
            "tokens_input": 0, "tokens_output": 0, "provider": provider, "model": "",
        }
    result["latency_ms"] = int((time.time() - start_time) * 1000)
    result["session_id"] = str(uuid.uuid4())
    return result


def _unconfigured_response(key_name: str, history: list[dict[str, Any]] | None) -> dict[str, Any]:
    return {
        "response": "The Cornerstone AI Agent is not configured. Please set the " + key_name + " environment variable.",
        "tool_actions": [], "history": history or [], "pending_approvals": [],
        "tokens_input": 0, "tokens_output": 0, "provider": "", "model": "",
    }


def execute_approved_tools(approvals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for approval in approvals:
        result = _execute_tool(approval["tool"], approval["input"])
        results.append({"tool": approval["tool"], "input": approval["input"], "output": result[:2000], "status": "executed"})
    return results
