"""A deterministic permission gate for agent tool calls (Checkpoint 5).

The gate runs before every tool call. It decides from the tool name and the arguments alone,
so it holds whatever the model was persuaded to do. Tool descriptions, annotations and tool
results inform the agent; they never grant permissions.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Iterable

# The literature tools an agent may use by default. build_evidence_table is left out on purpose:
# it asks the user a question (elicitation), which a plain agent loop cannot answer.
APPROVED_TOOLS = frozenset({"search_literature", "get_paper", "find_citing_papers"})

_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_SUSPICIOUS_PHRASES = (
    "ignore previous instructions",
    "ignore all previous",
    "note to ai",
    "system prompt",
    "exfiltrate",
)


class PolicyViolation(PermissionError):
    """A proposed tool call is not allowed, whatever the model intended."""


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _strings(item)


def policy_gate(
    tool_name: str,
    args: dict | None,
    *,
    approved_tools: Iterable[str] = APPROVED_TOOLS,
    approved_hosts: Iterable[str] = (),
) -> None:
    """Raise PolicyViolation unless the tool is approved and every URL in the arguments
    points to an approved host."""
    tools = set(approved_tools)
    hosts = {host.lower() for host in approved_hosts}
    if tool_name not in tools:
        raise PolicyViolation(f"tool '{tool_name}' is not approved for this run")
    for text in _strings(args or {}):
        for url in _URL_RE.findall(text):
            host = (urllib.parse.urlparse(url).hostname or "").lower()
            if host not in hosts:
                raise PolicyViolation(f"destination '{host or url}' is not approved")


def naive_injection_filter(text: str) -> bool:
    """A keyword filter, included only to show why keyword filters are not a security boundary."""
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in _SUSPICIOUS_PHRASES)


def make_policy_middleware(
    denied: list,
    *,
    approved_tools: Iterable[str] = APPROVED_TOOLS,
    approved_hosts: Iterable[str] = (),
):
    """LangChain agent middleware that applies policy_gate to every tool call.

    Denied calls never run: the agent receives an error message instead, and the denial is
    appended to `denied`, which becomes part of the run record.
    """
    from langchain.agents.middleware import AgentMiddleware
    from langchain_core.messages import ToolMessage

    tools, hosts = set(approved_tools), set(approved_hosts)

    class PolicyMiddleware(AgentMiddleware):
        def _denial(self, request):
            call = request.tool_call
            try:
                policy_gate(call["name"], call.get("args"), approved_tools=tools, approved_hosts=hosts)
            except PolicyViolation as exc:
                denied.append({"tool": call["name"], "args": call.get("args"), "reason": str(exc)})
                return ToolMessage(
                    content=f"Denied by policy: {exc}",
                    tool_call_id=call["id"],
                    name=call["name"],
                    status="error",
                )
            return None

        def wrap_tool_call(self, request, handler):
            denial = self._denial(request)
            return denial if denial is not None else handler(request)

        async def awrap_tool_call(self, request, handler):
            denial = self._denial(request)
            return denial if denial is not None else await handler(request)

    return PolicyMiddleware()
