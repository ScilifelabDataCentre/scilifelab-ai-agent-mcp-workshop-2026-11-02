"""A minimal Python executor tool for the introductory CodeAct exercise.

This is intentionally simple — it runs code in a single shared namespace so
state persists between calls (variables defined in one call are visible in
the next). Captured stdout is returned along with the value of the last
expression, if any. This is *not* a security sandbox; only use it in trusted
educational settings.
"""
from __future__ import annotations

import ast
import io
import traceback
from contextlib import redirect_stdout

from langchain.tools import tool

# Shared namespace so variables persist across executions within a session.
_NAMESPACE: dict = {"__name__": "codeact"}


@tool
def python_executor(code: str) -> str:
    """Execute a snippet of Python code and return its stdout plus final value.

    Variables defined here persist across calls within the same session, so
    you can build up a small workflow (import a library, define a function,
    then call it) over several steps.

    Args:
        code: The Python source code to execute.

    Returns:
        A string containing any printed output and the value of the last
        expression (or the error traceback if execution failed).
    """
    buf = io.StringIO()
    try:
        tree = ast.parse(code, mode="exec")
        # Split off the trailing expression (if any) so we can return its value.
        last_value = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = ast.Expression(body=tree.body.pop().value)
            with redirect_stdout(buf):
                exec(compile(tree, "<codeact>", "exec"), _NAMESPACE)
                last_value = eval(compile(last_expr, "<codeact>", "eval"), _NAMESPACE)
        else:
            with redirect_stdout(buf):
                exec(compile(tree, "<codeact>", "exec"), _NAMESPACE)
    except Exception:
        return f"ERROR:\n{traceback.format_exc()}"

    output = buf.getvalue()
    if last_value is not None:
        output += f"\n=> {last_value!r}"
    return output.strip() or "(no output)"


@tool
def reset_python_state() -> str:
    """Clear all variables from the python_executor session."""
    _NAMESPACE.clear()
    _NAMESPACE["__name__"] = "codeact"
    return "Python state reset."
