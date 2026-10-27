"""Evidence helpers: a numbered evidence table, and a check that every citation is grounded."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

_PMID_IN_TEXT = re.compile(r"\bPMID[:\s#]*(\d{4,9})\b", re.IGNORECASE)
_PMCID_IN_TEXT = re.compile(r"\b(PMC\d{4,9})\b", re.IGNORECASE)
_DOI_IN_TEXT = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>\]\)]+)")
_FIELDS = {
    "pmid": re.compile(r'"pmid"\s*:\s*"(\d{1,9})"'),
    "pmcid": re.compile(r'"pmcid"\s*:\s*"(PMC\d{1,9})"', re.IGNORECASE),
    "doi": re.compile(r'"doi"\s*:\s*"([^"]+)"'),
}
KINDS = ("pmid", "pmcid", "doi")


def _norm(kind: str, value: str) -> str:
    value = value.strip()
    if kind == "doi":
        return value.rstrip(".,;:").lower()
    if kind == "pmcid":
        return value.upper()
    return value


def empty_ids() -> dict[str, set[str]]:
    return {kind: set() for kind in KINDS}


def ids_in_text(text: str) -> dict[str, set[str]]:
    """Identifiers that a free-text answer mentions (PMID 123..., PMC123..., 10.xxxx/...)."""
    text = text or ""
    return {
        "pmid": {_norm("pmid", v) for v in _PMID_IN_TEXT.findall(text)},
        "pmcid": {_norm("pmcid", v) for v in _PMCID_IN_TEXT.findall(text)},
        "doi": {_norm("doi", v) for v in _DOI_IN_TEXT.findall(text)},
    }


def ids_in_papers(papers: Iterable[dict]) -> dict[str, set[str]]:
    ids = empty_ids()
    for paper in papers:
        for kind in KINDS:
            if paper.get(kind):
                ids[kind].add(_norm(kind, str(paper[kind])))
    return ids


def ids_in_tool_output(text: str) -> dict[str, set[str]]:
    """Identifiers in a JSON tool result ("pmid": "123", "doi": "10....")."""
    ids = empty_ids()
    for kind, pattern in _FIELDS.items():
        ids[kind].update(_norm(kind, v) for v in pattern.findall(text or ""))
    return ids


def message_text(message: Any) -> str:
    """Plain text of a LangChain message, whatever shape its content has."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(getattr(block, "text", "")))
        return "\n".join(parts)
    return str(content or "")


def ids_in_tool_messages(messages: Iterable[Any]) -> dict[str, set[str]]:
    """Every identifier that any tool returned during an agent run."""
    ids = empty_ids()
    for message in messages or []:
        if getattr(message, "type", None) != "tool":
            continue
        texts = [message_text(message)]
        artifact = getattr(message, "artifact", None)
        if artifact is not None:
            texts.append(json.dumps(artifact, default=str))
        for text in texts:
            found = ids_in_tool_output(text)
            for kind in KINDS:
                ids[kind] |= found[kind]
    return ids


def unsupported_citations(
    cited: dict[str, set[str]], returned: dict[str, set[str]]
) -> dict[str, list[str]]:
    """Identifiers that were cited but never returned by a tool, per kind."""
    report = {}
    for kind, values in cited.items():
        missing = values - returned.get(kind, set())
        if missing:
            report[kind] = sorted(missing)
    return report


def citation_string(paper: dict) -> str:
    authors = (paper.get("authors") or "").strip()
    first = authors.split(",")[0].strip() if authors else "Unknown author"
    if "," in authors:
        first += " et al."
    year = paper.get("year") or "n.d."
    journal = f" {paper['journal']}." if paper.get("journal") else ""
    if paper.get("pmid"):
        ident = f" PMID {paper['pmid']}."
    elif paper.get("doi"):
        ident = f" doi:{paper['doi']}."
    else:
        ident = f" {paper.get('id', '')}."
    return f"{first} ({year}). {paper.get('title', '').rstrip('.')}.{journal}{ident}"


def evidence_rows(papers: list[dict], snippet_chars: int = 300) -> list[dict]:
    """Numbered rows for an evidence table: retrieved records, not conclusions."""
    rows = []
    for ref, paper in enumerate(papers, start=1):
        abstract = paper.get("abstract") or ""
        snippet = abstract[:snippet_chars].rstrip() + ("\u2026" if len(abstract) > snippet_chars else "")
        rows.append(
            {
                "ref": ref,
                "citation": citation_string(paper),
                "title": paper.get("title") or "(untitled record)",
                "year": paper.get("year"),
                "journal": paper.get("journal"),
                "pmid": paper.get("pmid"),
                "doi": paper.get("doi"),
                "cited_by": paper.get("cited_by"),
                "open_access": paper.get("open_access"),
                "snippet": snippet or None,
                "url": paper.get("url") or "",
            }
        )
    return rows
