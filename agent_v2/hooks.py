"""Hook system — configurable pre/post callbacks for tool execution.

Inspired by Claude Code's 13-event hook lifecycle.  Hooks are Python
callables registered by event name.  They run synchronously in order
and can modify or block tool calls.

Supported events
----------------
- ``PreToolUse``   — fires *before* a tool is executed.  Can modify
  ``tool_input`` or return ``{"block": True, "reason": "..."}`` to skip.
- ``PostToolUse``  — fires *after* a tool returns.  Receives the result
  and can modify it.
- ``UserPromptSubmit`` — fires when the user submits a message.  Can
  rewrite or reject the message.
- ``SessionStart`` — fires once when the session begins.
- ``SessionEnd``   — fires once when the session ends.
- ``PreCompact``   — fires before auto-compaction.
- ``PostCompact``  — fires after auto-compaction.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from rich.console import Console

console = Console()

# Type alias for hook callables
HookFn = Callable[..., Any]

# ---------------------------------------------------------------------------
# Hook registry
# ---------------------------------------------------------------------------

_hooks: dict[str, list[HookFn]] = {
    "PreToolUse": [],
    "PostToolUse": [],
    "UserPromptSubmit": [],
    "SessionStart": [],
    "SessionEnd": [],
    "PreCompact": [],
    "PostCompact": [],
}


def register_hook(event: str, fn: HookFn) -> None:
    """Register a hook function for *event*.

    Raises ``ValueError`` if *event* is not a known hook point.
    """
    if event not in _hooks:
        raise ValueError(
            f"Unknown hook event '{event}'. "
            f"Valid events: {', '.join(sorted(_hooks))}"
        )
    _hooks[event].append(fn)
    console.print(f"[dim]Hook registered: {event} -> {fn.__name__}[/dim]")


def clear_hooks(event: str | None = None) -> None:
    """Remove all hooks for *event*, or all hooks if *event* is ``None``."""
    if event is None:
        for lst in _hooks.values():
            lst.clear()
    elif event in _hooks:
        _hooks[event].clear()


# ---------------------------------------------------------------------------
# Hook execution
# ---------------------------------------------------------------------------

def fire_pre_tool_use(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Run all ``PreToolUse`` hooks.  Returns a dict with keys:

    - ``tool_input``: potentially modified input
    - ``blocked``: whether the call should be skipped
    - ``reason``: block reason (if blocked)
    """
    result: dict[str, Any] = {
        "tool_input": tool_input,
        "blocked": False,
        "reason": "",
    }
    for fn in _hooks["PreToolUse"]:
        try:
            rv = fn(tool_name=tool_name, tool_input=result["tool_input"])
            if isinstance(rv, dict):
                if rv.get("block"):
                    result["blocked"] = True
                    result["reason"] = rv.get("reason", "Blocked by hook")
                    return result
                if "tool_input" in rv:
                    result["tool_input"] = rv["tool_input"]
        except Exception as exc:
            console.print(f"[red]PreToolUse hook error ({fn.__name__}): {exc}[/red]")
    return result


def fire_post_tool_use(
    tool_name: str, tool_input: dict[str, Any], result: str
) -> str:
    """Run all ``PostToolUse`` hooks.  Returns the (possibly modified) result."""
    current = result
    for fn in _hooks["PostToolUse"]:
        try:
            rv = fn(tool_name=tool_name, tool_input=tool_input, result=current)
            if isinstance(rv, str):
                current = rv
        except Exception as exc:
            console.print(f"[red]PostToolUse hook error ({fn.__name__}): {exc}[/red]")
    return current


def fire_user_prompt(message: str) -> dict[str, Any]:
    """Run all ``UserPromptSubmit`` hooks.  Returns a dict with:

    - ``message``: potentially rewritten message
    - ``rejected``: whether the message should be dropped
    - ``reason``: rejection reason (if rejected)
    """
    result: dict[str, Any] = {
        "message": message,
        "rejected": False,
        "reason": "",
    }
    for fn in _hooks["UserPromptSubmit"]:
        try:
            rv = fn(message=result["message"])
            if isinstance(rv, dict):
                if rv.get("reject"):
                    result["rejected"] = True
                    result["reason"] = rv.get("reason", "Rejected by hook")
                    return result
                if "message" in rv:
                    result["message"] = rv["message"]
        except Exception as exc:
            console.print(
                f"[red]UserPromptSubmit hook error ({fn.__name__}): {exc}[/red]"
            )
    return result


def get_hook_status() -> dict[str, int]:
    """Return a dict mapping event names to the number of registered hooks."""
    return {event: len(fns) for event, fns in _hooks.items()}


def fire_simple(event: str, **kwargs: Any) -> None:
    """Fire a simple event (SessionStart, SessionEnd, PreCompact, PostCompact)."""
    for fn in _hooks.get(event, []):
        try:
            fn(**kwargs)
        except Exception as exc:
            console.print(f"[red]{event} hook error ({fn.__name__}): {exc}[/red]")


# ---------------------------------------------------------------------------
# Load hooks from config file
# ---------------------------------------------------------------------------

def load_hooks_from_config(config_path: str | None = None) -> int:
    """Load hook definitions from a JSON config file.

    Config format::

        {
          "hooks": {
            "PreToolUse": [
              {"command": "echo pre-hook fired", "timeout": 30}
            ],
            "PostToolUse": [
              {"command": "echo post-hook fired"}
            ]
          }
        }

    Shell command hooks are wrapped in a subprocess call.  Returns the
    number of hooks loaded.
    """
    if config_path is None:
        # Default: look for hooks.json next to this file
        config_path = os.path.join(os.path.dirname(__file__), "hooks.json")

    if not os.path.isfile(config_path):
        return 0

    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"[red]Failed to load hooks config: {exc}[/red]")
        return 0

    count = 0
    hooks_config = config.get("hooks", {})
    for event, hook_list in hooks_config.items():
        if event not in _hooks:
            console.print(f"[yellow]Unknown hook event in config: {event}[/yellow]")
            continue
        for hook_def in hook_list:
            cmd = hook_def.get("command")
            timeout = hook_def.get("timeout", 30)
            if cmd:
                fn = _make_shell_hook(cmd, timeout)
                register_hook(event, fn)
                count += 1

    return count


def _make_shell_hook(command: str, timeout: int) -> HookFn:
    """Create a hook function that runs a shell command."""
    import subprocess

    def shell_hook(**kwargs: Any) -> None:
        """Shell hook: {command}"""
        try:
            env = os.environ.copy()
            # Pass hook context as env vars
            for k, v in kwargs.items():
                env[f"HOOK_{k.upper()}"] = (
                    json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                )
            subprocess.run(
                command,
                shell=True,
                timeout=timeout,
                capture_output=True,
                env=env,
            )
        except subprocess.TimeoutExpired:
            console.print(f"[yellow]Shell hook timed out: {command}[/yellow]")
        except Exception as exc:
            console.print(f"[red]Shell hook error: {exc}[/red]")

    shell_hook.__name__ = f"shell_hook({command[:40]})"
    shell_hook.__doc__ = f"Shell hook: {command}"
    return shell_hook
