"""Auto test generation (#4).

After the agent writes code, this module can generate and run unit tests
automatically using pytest. It generates test files, runs them, and
reports results back to the agent.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from typing import Any

from agent_v4.config import WORKSPACE


def generate_test_for_file(filepath: str) -> str:
    """Generate a basic test file for a Python module.

    Reads the source file, extracts function/class signatures, and
    creates a test skeleton with pytest.
    """
    full_path = os.path.join(WORKSPACE, filepath)
    if not os.path.isfile(full_path):
        return f"Error: File not found: {filepath}"

    try:
        with open(full_path, encoding="utf-8") as f:
            source = f.read()
    except OSError as exc:
        return f"Error reading file: {exc}"

    # Extract function and class names
    functions: list[str] = []
    classes: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("def ") and not stripped.startswith("def _"):
            name = stripped.split("(")[0].replace("def ", "").strip()
            functions.append(name)
        elif stripped.startswith("class "):
            name = stripped.split("(")[0].split(":")[0].replace("class ", "").strip()
            classes.append(name)

    if not functions and not classes:
        return "No public functions or classes found to test."

    # Build module import path
    module_path = filepath.replace("/", ".").replace("\\", ".")
    if module_path.endswith(".py"):
        module_path = module_path[:-3]

    # Generate test code
    test_lines = [
        '"""Auto-generated tests for ' + filepath + '."""',
        "",
        "import pytest",
        "",
    ]

    if functions:
        test_lines.append(f"from {module_path} import {', '.join(functions)}")
        test_lines.append("")
        for func in functions:
            test_lines.extend([
                f"def test_{func}_exists():",
                f'    """Verify {func} is callable."""',
                f"    assert callable({func})",
                "",
                f"def test_{func}_runs():",
                f'    """Verify {func} can be called (may need args)."""',
                f"    # TODO: Add appropriate arguments",
                f"    # result = {func}(...)",
                f"    pass",
                "",
            ])

    if classes:
        for cls in classes:
            test_lines.extend([
                f"from {module_path} import {cls}",
                "",
                f"class Test{cls}:",
                f'    """Tests for {cls}."""',
                "",
                f"    def test_{cls.lower()}_instantiable(self):",
                f'        """Verify {cls} can be instantiated."""',
                f"        # TODO: Add constructor args if needed",
                f"        # obj = {cls}(...)",
                f"        pass",
                "",
            ])

    test_content = "\n".join(test_lines)

    # Determine test file path
    test_dir = os.path.join(WORKSPACE, "tests")
    os.makedirs(test_dir, exist_ok=True)
    test_filename = f"test_{os.path.basename(filepath)}"
    test_path = os.path.join(test_dir, test_filename)

    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_content)

    rel_test_path = os.path.relpath(test_path, WORKSPACE)
    return f"Generated test file: {rel_test_path}\n\n{test_content}"


def run_tests(test_path: str = "") -> str:
    """Run pytest and return the results.

    If test_path is empty, runs all tests in the workspace.
    """
    cmd = "python -m pytest"
    if test_path:
        cmd += f" {test_path}"
    cmd += " -v --tb=short --no-header -q"

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=120, cwd=WORKSPACE,
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += "\n" + result.stderr.strip()
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Tests timed out after 120 seconds."
    except Exception as exc:
        return f"Error running tests: {exc}"


# ---------------------------------------------------------------------------
# Tool definitions for the agent
# ---------------------------------------------------------------------------

TEST_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "generate_tests",
        "description": (
            "Generate a unit test file for a Python source file. "
            "Creates test skeletons with pytest for all public functions and classes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the Python file to generate tests for (relative to workspace)",
                },
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "run_tests",
        "description": (
            "Run pytest on the workspace. Optionally specify a test file path. "
            "Returns test results including pass/fail counts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "test_path": {
                    "type": "string",
                    "description": "Specific test file to run (optional, runs all if empty)",
                    "default": "",
                },
            },
            "required": [],
        },
    },
]

TEST_TOOLS: dict[str, Any] = {
    "generate_tests": lambda filepath: generate_test_for_file(filepath),
    "run_tests": lambda test_path="": run_tests(test_path),
}
