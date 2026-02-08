from __future__ import annotations

import logging
import math

from langsmith import traceable

logger = logging.getLogger(__name__)

_SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "int": int,
    "float": float,
    "sqrt": math.sqrt,
    "pow": math.pow,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
}

_SAFE_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "inf": math.inf,
    "true": True,
    "false": False,
}


def _format_result(result: object) -> str:
    """Format a numeric result for clean display."""
    if isinstance(result, float):
        if result == int(result) and abs(result) < 1e15:
            return str(int(result))
        return f"{result:.10g}"
    return str(result)


@traceable(name="calculate", run_type="tool")
async def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression.

    Supports arithmetic, comparisons, and math functions (sqrt, log, sin, etc.).
    Returns the result as a string, or an error message on failure.
    """
    try:
        from simpleeval import simple_eval, InvalidExpression

        result = simple_eval(
            expression,
            functions=_SAFE_FUNCTIONS,
            names=_SAFE_NAMES,
        )
        return _format_result(result)

    except ImportError:
        logger.warning("simpleeval not installed, using restricted fallback")
        return _fallback_calculate(expression)
    except (TypeError, ValueError, ZeroDivisionError) as e:
        return f"Calculation error: {e}"
    except Exception as e:
        return f"Calculation error: {e}"


def _fallback_calculate(expression: str) -> str:
    """Restricted fallback — only digits, operators, parentheses, decimal points."""
    import ast
    import re

    if not re.match(r"^[\d\s+\-*/().%]+$", expression):
        return "Calculation error: only basic arithmetic is supported without simpleeval installed."

    try:
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(
                node,
                (
                    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
                    ast.Pow, ast.FloorDiv, ast.USub, ast.UAdd,
                ),
            ):
                return "Calculation error: unsupported operation."

        result = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}})
        return _format_result(result)
    except Exception as e:
        return f"Calculation error: {e}"
