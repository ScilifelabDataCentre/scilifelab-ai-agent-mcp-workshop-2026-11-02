"""Typed results returned by the MCP server.

Each tool's return type becomes its output schema, and clients receive the values as
structured content, so hosts and agents get fields instead of free text.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Paper(BaseModel):
    id: str = Field(description="Europe PMC identifier as SOURCE:ID, for example MED:12345678")
    source: str = Field(description="MED (PubMed), PMC, PPR (preprint), and others")
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    title: str
    authors: str | None = None
    journal: str | None = None
    year: int | None = None
    cited_by: int | None = Field(default=None, description="Citations counted by Europe PMC")
    open_access: bool | None = None
    abstract: str | None = Field(default=None, description="Abstract, shortened in search results")
    url: str


class SearchResult(BaseModel):
    status: Literal["ok", "no_results"]
    query: str
    query_sent: str = Field(description="The exact query sent to Europe PMC, filters included")
    hit_count: int
    returned: int
    papers: list[Paper]
    source: str
    retrieved_at: str
    served_from: Literal["live", "cache"]
    warnings: list[str] = Field(default_factory=list)


class PaperDetails(Paper):
    keywords: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    full_text_links: list[str] = Field(default_factory=list)
    first_publication_date: str | None = None


class PaperLookup(BaseModel):
    status: Literal["ok", "not_found"]
    requested_id: str
    paper: PaperDetails | None = None
    source: str
    retrieved_at: str
    served_from: Literal["live", "cache"]


class CitingPapers(BaseModel):
    status: Literal["ok", "no_results", "not_found"]
    cited_paper: str
    hit_count: int
    returned: int
    papers: list[Paper]
    source: str
    retrieved_at: str
    served_from: Literal["live", "cache"]


class ReviewScope(BaseModel):
    """What the user confirms before an evidence table is built. Asked through elicitation,
    so the fields stay flat and simple: numbers and yes/no."""

    from_year: int = Field(default=2015, description="Earliest publication year to include")
    max_papers: int = Field(default=8, description="Number of papers in the table (3 to 25)")
    open_access_only: bool = Field(default=False, description="Only include open-access papers")


class EvidenceRow(BaseModel):
    ref: int
    citation: str
    title: str
    year: int | None = None
    journal: str | None = None
    pmid: str | None = None
    doi: str | None = None
    cited_by: int | None = None
    open_access: bool | None = None
    snippet: str | None = None
    url: str


class EvidenceTable(BaseModel):
    research_question: str
    query_sent: str
    scope: ReviewScope
    hit_count: int
    rows: list[EvidenceRow]
    source: str
    retrieved_at: str
    served_from: Literal["live", "cache"]
    note: str = "These rows are retrieved records, not conclusions. Read the papers before you cite them."
