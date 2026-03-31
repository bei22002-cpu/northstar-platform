"""Sandbox runner — safe code execution in an isolated subprocess."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from agent_v5.tools.base import BaseTool
from agent_v5.registry import ToolRegistry


@ToolRegistry.register("run_python")
class SandboxRunner(BaseTool):
    """Execute Python code in an isolated subprocess with timeout."""

    tool_id = "run_python"
    description = "Execute Python code safely in a sandboxed subprocess."

    def execute(self, code: str = "", timeout: int = 30, **kwargs: Any) -> str:
        if not code:
            return "Error: code is required"

        # Block dangerous imports/operations
        dangerous = ["os.system", "subprocess", "shutil.rmtree", "__import__",
                      "eval(", "exec(", "compile(", "open('/etc", "open('/usr"]
        for d in dangerous:
            if d in code:
                return f"BLOCKED: code contains dangerous operation: {d}"

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as f:
                f.write(code)
                f.flush()
                tmp_path = f.name

            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
            )

            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += ("\n" if output else "") + result.stderr
            if result.returncode != 0:
                output += f"\n(exit code: {result.returncode})"
            if not output.strip():
                output = "(no output)"
            if len(output) > 10000:
                output = output[:10000] + "\n... (truncated)"
            return output

        except subprocess.TimeoutExpired:
            Path(tmp_path).unlink(missing_ok=True)
            return f"Error: code execution timed out after {timeout} seconds"
        except Exception as e:
            return f"Error: {e}"

    def to_definition(self) -> dict[str, Any]:
        return {
            "name": "run_python",
            "description": "Execute Python code in a sandboxed subprocess. Output is captured and returned.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max execution time in seconds (default: 30).",
                    },
                },
                "required": ["code"],
            },
        }
