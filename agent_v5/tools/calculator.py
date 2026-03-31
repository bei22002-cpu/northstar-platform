"""Calculator tool — safe math expression evaluation."""

from __future__ import annotations

import ast
import math
import operator
from typing import Any, Dict

from agent_v5.tools.base import BaseTool
from agent_v5.registry import ToolRegistry

# Allowed operators for safe evaluation
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_MATH_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}

_MATH_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
}


def _safe_eval(node: ast.AST) -> Any:
    """Recursively evaluate an AST node with only safe operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.Name):
        name = node.id
        if name in _MATH_CONSTANTS:
            return _MATH_CONSTANTS[name]
        raise ValueError(f"Unknown variable: {name}")
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _OPERATORS:
            return _OPERATORS[op_type](_safe_eval(node.operand))
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _OPERATORS:
            left = _safe_eval(node.left)
            right = _safe_eval(node.right)
            return _OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported operator: {op_type.__name__}")
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _MATH_FUNCTIONS:
            args = [_safe_eval(a) for a in node.args]
            return _MATH_FUNCTIONS[node.func.id](*args)
        raise ValueError(f"Unsupported function call")
    raise ValueError(f"Unsupported expression type: {type(node).__name__}")


@ToolRegistry.register("calculator")
class CalculatorTool(BaseTool):
    tool_id = "calculator"
    description = "Evaluate a mathematical expression safely."

    def execute(self, expression: str = "", **kwargs: Any) -> str:
        if not expression:
            return "Error: expression is required"
        try:
            tree = ast.parse(expression.strip(), mode="eval")
            result = _safe_eval(tree)
            return str(result)
        except (ValueError, TypeError, SyntaxError, ZeroDivisionError) as e:
            return f"Error: {e}"

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": "calculator",
            "description": "Evaluate a mathematical expression. Supports +, -, *, /, **, sqrt, sin, cos, tan, log, pi, e.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to evaluate (e.g. '2 + 3 * 4', 'sqrt(144)', 'sin(pi/2)').",
                    }
                },
                "required": ["expression"],
            },
        }
