"""Terminal tool — run shell commands in the workspace."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict

from agent_v5.tools.base import BaseTool
from agent_v5.registry import ToolRegistry
from agent_v5.safety import is_blocked


@ToolRegistry.register("run_command")
class RunCommandTool(BaseTool):
    tool_id = "run_command"
    description = "Run a shell command in the workspace directory."

    def __init__(self, workspace: str = ".") -> None:
        self._workspace = Path(workspace).resolve()

    def execute(self, command: str = "", **kwargs: Any) -> str:
        if not command:
            return "Error: command is required"

        blocked, reason = is_blocked(command)
        if blocked:
            return f"BLOCKED: {reason}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self._workspace),
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += ("\n" if output else "") + result.stderr
            if result.returncode != 0:
                output += f"\n(exit code: {result.returncode})"
            if not output.strip():
                output = "(no output)"
            # Truncate very long output
            if len(output) > 20000:
                output = output[:20000] + "\n... (truncated)"
            return output
        except subprocess.TimeoutExpired:
            return "Error: command timed out after 60 seconds"
        except Exception as e:
            return f"Error running command: {e}"

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": "run_command",
            "description": "Run a shell command in the project workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        }
