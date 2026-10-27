"""A small Europe PMC client for literature reviews, using only the Python standard library.

Europe PMC indexes PubMed/MEDLINE, PubMed Central, preprints (bioRxiv, medRxiv and others),
patents, theses and more, so it suits researchers across the life sciences. No API key is needed.
REST documentation: https://europepmc.org/RestfulWebService

The functions return plain dictionaries; the MCP server turns them into typed results.
Every failure raises a LiteratureError subclass whose `kind` says what went wrong.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config

EUROPEPMC_SITE = "https://europepmc.org"
SOURCE_NAME = "Europe PMC"


class LiteratureError(Exception):
    """Base class for every failure; `kind` is a short machine-readable label."""

    kind = "error"


class InvalidInput(LiteratureError):
    kind = "invalid_input"


class UpstreamError(LiteratureError):
    kind = "upstream_error"


class NotInCache(UpstreamError):
    kind = "offline_cache_miss"


# Europe PMC's separate `sort=` parameter is unreliable, so sorting goes inside the query,
# the same way the rOpenSci europepmc client does it.
SORT_TERMS = {"relevance": "", "cited": " sort_cited:y", "newest": " sort_date:y"}

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_PMID_RE = re.compile(r"^\d{1,9}$")
_PMCID_RE = re.compile(r"^PMC\d{1,9}$", re.IGNORECASE)
_PPR_RE = re.compile(r"^PPR\d{1,9}$", re.IGNORECASE)
_DOI_RE = re.compile(r'^10\.\d{4,9}/[^\s"]{1,200}$')
_SOURCE_ID_RE = re.compile(
    r"^(MED|PMC|PPR|AGR|CBA|CTX|ETH|HIR|PAT):([A-Za-z0-9._-]{1,40})$", re.IGNORECASE
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value: Any, limit: int | None = None) -> str | None:
    """Strip HTML tags and entities, collapse whitespace, and optionally shorten."""
    if value in (None, ""):
        return None
    text = html.unescape(_TAG_RE.sub(" ", str(value)))
    text = _SPACE_RE.sub(" ", text).strip()
    if limit is not None and len(text) > limit:
        text = text[: max(limit - 1, 0)].rstrip() + "\u2026"
    return text or None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


# ---------------------------------------------------------------------------
# Input validation: the server enforces these limits, whatever the model sends.
# ---------------------------------------------------------------------------

def validate_query(query: str | None) -> str:
    """Use the workshop default when the query is empty; refuse very long queries."""
    text = (query or "").strip() or config.DEFAULT_QUERY
    if len(text) > config.MAX_QUERY_CHARS:
        raise InvalidInput(
            f"the query has {len(text)} characters; the limit is {config.MAX_QUERY_CHARS}"
        )
    return text


def clamp_results(max_results: Any) -> int:
    number = _to_int(max_results)
    if number is None:
        raise InvalidInput("max_results must be a whole number")
    if number < 1:
        raise InvalidInput("max_results must be at least 1")
    return min(number, config.MAX_RESULTS_LIMIT)


def validate_years(from_year: Any, to_year: Any) -> tuple[int | None, int | None]:
    latest = datetime.now(timezone.utc).year + 1
    years: list[int | None] = []
    for name, value in (("from_year", from_year), ("to_year", to_year)):
        if value in (None, ""):
            years.append(None)
            continue
        year = _to_int(value)
        if year is None or not 1800 <= year <= latest:
            raise InvalidInput(f"{name} must be a year between 1800 and {latest}")
        years.append(year)
    start, end = years
    if start and end and start > end:
        raise InvalidInput("from_year is later than to_year")
    return start, end


def normalize_id(paper_id: str) -> tuple[str, str]:
    """Return (source, id) for a PMID, PMCID, preprint id, DOI, or SOURCE:ID string."""
    text = (paper_id or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "pmid:"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    match = _SOURCE_ID_RE.match(text)
    if match:
        return match.group(1).upper(), match.group(2)
    if _PMID_RE.match(text):
        return "MED", text
    if _PMCID_RE.match(text):
        return "PMC", text.upper()
    if _PPR_RE.match(text):
        return "PPR", text.upper()
    if _DOI_RE.match(text):
        return "DOI", text
    raise InvalidInput(
        f"'{paper_id}' is not a PMID, PMCID, preprint id (PPR...), DOI, "
        "or SOURCE:ID such as MED:12345678"
    )


# ---------------------------------------------------------------------------
# Query and URL building
# ---------------------------------------------------------------------------

def build_query(
    query: str,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
    open_access_only: bool = False,
    sort: str = "relevance",
) -> str:
    """Combine the user's query with filters, using Europe PMC's in-query syntax."""
    if sort not in SORT_TERMS:
        raise InvalidInput(f"sort must be one of: {', '.join(SORT_TERMS)}")
    terms = [f"({query})"]
    if from_year or to_year:
        start = f"{from_year}-01-01" if from_year else "1800-01-01"
        end = f"{to_year}-12-31" if to_year else f"{datetime.now(timezone.utc).year + 1}-12-31"
        terms.append(f"FIRST_PDATE:[{start} TO {end}]")
    if open_access_only:
        terms.append("OPEN_ACCESS:y")
    return " AND ".join(terms) + SORT_TERMS[sort]


def search_url(full_query: str, page_size: int) -> str:
    params = {
        "query": full_query,
        "format": "json",
        "resultType": "core",
        "pageSize": str(page_size),
        "synonym": "true",
    }
    return f"{config.EUROPEPMC_BASE_URL}/search?{urllib.parse.urlencode(params)}"


def citations_url(source: str, ident: str, page_size: int) -> str:
    params = {"page": "1", "pageSize": str(page_size), "format": "json"}
    path = f"{urllib.parse.quote(source, safe='')}/{urllib.parse.quote(ident, safe='')}/citations"
    return f"{config.EUROPEPMC_BASE_URL}/{path}?{urllib.parse.urlencode(params)}"


# ---------------------------------------------------------------------------
# Fetching, with a small file cache for classroom resilience
# ---------------------------------------------------------------------------

def cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return Path(config.CACHE_DIR) / f"{digest}.json"


def fetch_json(url: str) -> tuple[dict, str, str]:
    """Return (payload, served_from, retrieved_at); served_from is 'live' or 'cache'."""
    mode = config.MODE
    if mode not in ("live", "cache", "offline"):
        raise InvalidInput(f"LITREVIEW_MODE must be live, cache or offline, not '{mode}'")
    path = cache_path(url)
    if mode in ("cache", "offline") and path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            return stored["payload"], "cache", stored.get("retrieved_at", "unknown")
        except (OSError, ValueError, KeyError):
            if mode == "offline":
                raise NotInCache(f"the cached response {path.name} is unreadable")
    if mode == "offline":
        raise NotInCache(
            "offline mode, and this request is not in the cache. Run "
            "scripts/prefetch_fixtures.py with network access first, or use LITREVIEW_MODE=cache."
        )
    payload = _http_get_json(url)
    retrieved_at = now_iso()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"url": url, "retrieved_at": retrieved_at, "payload": payload}),
            encoding="utf-8",
        )
    except OSError:
        pass  # a read-only file system must not break a live answer
    return payload, "live", retrieved_at


def _http_get_json(url: str, retries: int = 1) -> dict:
    request = urllib.request.Request(
        url, headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"}
    )
    raw = b""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=config.HTTP_TIMEOUT_S) as response:
                raw = response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or attempt == retries:
                raise UpstreamError(f"Europe PMC answered HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == retries:
                reason = getattr(exc, "reason", exc)
                raise UpstreamError(f"Europe PMC could not be reached ({reason})") from exc
        time.sleep(0.5 * (attempt + 1))
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise UpstreamError("Europe PMC returned a response that is not JSON") from exc
    if not isinstance(payload, dict):
        raise UpstreamError("Europe PMC returned an unexpected JSON shape")
    return payload


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def article_url(source: str, ident: str) -> str:
    return f"{EUROPEPMC_SITE}/article/{source}/{ident}" if ident else EUROPEPMC_SITE


def parse_paper(record: dict, abstract_chars: int | None) -> dict:
    """Normalise one Europe PMC record (core or lite result type)."""
    source = str(record.get("source") or "MED")
    ident = str(record.get("id") or record.get("pmid") or record.get("pmcid") or "")
    journal_info = record.get("journalInfo") or {}
    journal = record.get("journalTitle") or (journal_info.get("journal") or {}).get("title")
    year = record.get("pubYear") or journal_info.get("yearOfPublication")
    return {
        "id": f"{source}:{ident}" if ident else source,
        "source": source,
        "pmid": record.get("pmid"),
        "pmcid": record.get("pmcid"),
        "doi": record.get("doi"),
        "title": clean_text(record.get("title")) or "(untitled record)",
        "authors": clean_text(record.get("authorString"), 200),
        "journal": clean_text(journal),
        "year": _to_int(year),
        "cited_by": _to_int(record.get("citedByCount")),
        "open_access": str(record.get("isOpenAccess", "N")).upper() == "Y",
        "abstract": clean_text(record.get("abstractText"), abstract_chars),
        "url": article_url(source, ident),
    }


def parse_citation(record: dict) -> dict:
    """Normalise one record from the citations endpoint (less detail than a search result)."""
    source = str(record.get("source") or "MED")
    ident = str(record.get("id") or "")
    return {
        "id": f"{source}:{ident}" if ident else source,
        "source": source,
        "pmid": ident if source == "MED" and ident else None,
        "pmcid": ident if source == "PMC" and ident else None,
        "doi": record.get("doi"),
        "title": clean_text(record.get("title")) or "(untitled record)",
        "authors": clean_text(record.get("authorString"), 200),
        "journal": clean_text(record.get("journalAbbreviation")),
        "year": _to_int(record.get("pubYear")),
        "cited_by": _to_int(record.get("citedByCount")),
        "open_access": None,  # the citations endpoint does not report it
        "abstract": None,
        "url": article_url(source, ident),
    }


def _results(payload: dict) -> list[dict]:
    result_list = payload.get("resultList") or {}
    results = result_list.get("result") or []
    if not isinstance(results, list):
        raise UpstreamError("Europe PMC returned an unexpected result list")
    return [record for record in results if isinstance(record, dict)]


# ---------------------------------------------------------------------------
# Public functions used by the MCP tools
# ---------------------------------------------------------------------------

def search(
    query: str | None = None,
    *,
    max_results: Any = 10,
    sort: str = "relevance",
    from_year: Any = None,
    to_year: Any = None,
    open_access_only: bool = False,
) -> dict:
    """Search Europe PMC. An empty query searches the workshop's default topic."""
    text = validate_query(query)
    number = clamp_results(max_results)
    start, end = validate_years(from_year, to_year)
    full_query = build_query(
        text, from_year=start, to_year=end, open_access_only=bool(open_access_only), sort=sort
    )
    payload, served_from, retrieved_at = fetch_json(search_url(full_query, number))
    papers = [parse_paper(record, config.SNIPPET_CHARS) for record in _results(payload)[:number]]
    warnings = []
    requested = _to_int(max_results)
    if requested is not None and requested > number:
        warnings.append(f"max_results was reduced to {number}, the workshop limit")
    return {
        "status": "ok" if papers else "no_results",
        "query": text,
        "query_sent": full_query,
        "hit_count": _to_int(payload.get("hitCount")) or 0,
        "returned": len(papers),
        "papers": papers,
        "source": SOURCE_NAME,
        "retrieved_at": retrieved_at,
        "served_from": served_from,
        "warnings": warnings,
    }


def _lookup_query(source: str, ident: str) -> str:
    if source == "DOI":
        return f'DOI:"{ident}"'
    if source == "PMC":
        return f"PMCID:{ident}"
    return f"EXT_ID:{ident} AND SRC:{source}"


def get_paper(paper_id: str) -> dict:
    """Full record for one paper: abstract, keywords, MeSH terms and full-text links."""
    source, ident = normalize_id(paper_id)
    payload, served_from, retrieved_at = fetch_json(search_url(_lookup_query(source, ident), 1))
    results = _results(payload)
    base = {
        "requested_id": paper_id,
        "source": SOURCE_NAME,
        "retrieved_at": retrieved_at,
        "served_from": served_from,
    }
    if not results:
        return {"status": "not_found", "paper": None, **base}
    record = results[0]
    paper = parse_paper(record, config.FULL_ABSTRACT_CHARS)
    paper.update(
        {
            "keywords": [
                k for k in _as_list((record.get("keywordList") or {}).get("keyword"))
                if isinstance(k, str)
            ],
            "mesh_terms": [
                h.get("descriptorName")
                for h in _as_list((record.get("meshHeadingList") or {}).get("meshHeading"))
                if isinstance(h, dict) and h.get("descriptorName")
            ],
            "publication_types": [
                t for t in _as_list((record.get("pubTypeList") or {}).get("pubType"))
                if isinstance(t, str)
            ],
            "full_text_links": [
                u.get("url")
                for u in _as_list((record.get("fullTextUrlList") or {}).get("fullTextUrl"))
                if isinstance(u, dict) and u.get("url")
            ][:5],
            "first_publication_date": record.get("firstPublicationDate"),
        }
    )
    return {"status": "ok", "paper": paper, **base}


def citing_papers(paper_id: str, *, max_results: Any = 10) -> dict:
    """Papers that cite the given paper: forward citation chasing for a review."""
    source, ident = normalize_id(paper_id)
    number = clamp_results(max_results)
    if source == "DOI":
        found = get_paper(ident)
        if found["status"] != "ok":
            return {
                "status": "not_found",
                "cited_paper": paper_id,
                "hit_count": 0,
                "returned": 0,
                "papers": [],
                "source": SOURCE_NAME,
                "retrieved_at": found["retrieved_at"],
                "served_from": found["served_from"],
            }
        source, ident = found["paper"]["id"].split(":", 1)
    payload, served_from, retrieved_at = fetch_json(citations_url(source, ident, number))
    records = [
        c for c in _as_list((payload.get("citationList") or {}).get("citation"))
        if isinstance(c, dict)
    ]
    papers = [parse_citation(record) for record in records[:number]]
    return {
        "status": "ok" if papers else "no_results",
        "cited_paper": f"{source}:{ident}",
        "hit_count": _to_int(payload.get("hitCount")) or 0,
        "returned": len(papers),
        "papers": papers,
        "source": SOURCE_NAME,
        "retrieved_at": retrieved_at,
        "served_from": served_from,
    }


def strip_abstracts_in_cache() -> int:
    """Remove abstract text from every cached response, before baking the cache into a public image."""
    removed = 0
    for path in Path(config.CACHE_DIR).glob("*.json"):
        stored = json.loads(path.read_text(encoding="utf-8"))
        for record in _results(stored.get("payload") or {}):
            if record.pop("abstractText", None) is not None:
                removed += 1
        path.write_text(json.dumps(stored), encoding="utf-8")
    return removed
