---
name: literature
description: Search PubMed for evidence with the NCBI LitSense2 semantic-search API. Returns passages from papers with their PMIDs. Use whenever an answer needs published evidence or citations, e.g. mechanism of action, resistance, clinical findings, or PK parameters to feed into a simulation.
---

# Literature search (PubMed via LitSense)

This skill wraps the **same search as the ReAct agent's `lit_search` tool** (`utils/tools/literature.py`). LitSense is a *semantic* search: a natural-language question works better than keywords joined with AND/OR.

---

## 1. Ready-made function (formatted text, like the ReAct agent sees it)

```python
from utils.tools.literature import lit_search

print(lit_search.invoke({"query": "erlotinib resistance MET amplification", "limit": 5}))
# --- Passage #1 ---
# PMID: 12345678
# Content: ...
```

---

## 2. Structured results (for filtering, de-duplicating and tables)

```python
import pandas as pd
from utils.litsense.litsense import LitSense_API

def search_literature(query: str, limit: int = 10) -> pd.DataFrame:
    """PubMed passages relevant to the query, as a table (pmid, score, section, text)."""
    results = LitSense_API().retrieve(query, limit=limit, rerank=False)
    return pd.DataFrame([{"pmid": r.pmid, "score": r.score, "section": r.section, "text": r.text} for r in results])

hits = search_literature("exenatide resistance to DPP-4 degradation half-life", limit=10)
hits[["pmid", "score", "text"]].head()
```

### Several questions at once, without duplicates

```python
queries = [
    "imatinib trough plasma concentration and molecular response in CML",
    "imatinib population pharmacokinetics clearance volume of distribution",
]
evidence = pd.concat([search_literature(q, limit=8).assign(query=q) for q in queries])
evidence = evidence.sort_values("score", ascending=False).drop_duplicates("pmid")
for _, row in evidence.head(6).iterrows():
    print(f"PMID {row.pmid} ({row.score:.2f}): {row.text[:250]}...\n")
```

### Find passages that mention numbers (e.g. PK parameters)

```python
pk_hits = search_literature("erlotinib population pharmacokinetics apparent clearance volume", limit=15)
pk_hits[pk_hits.text.str.contains(r"\d+(?:\.\d+)?\s*(?:L/h|l/h|L h|l h)", regex=True)][["pmid", "text"]]
```

---

## Tips

- One concept per query; run several focused queries rather than one long one.
- Passages are short excerpts: some are garbled or out of context. Read them before using them, and quote the sentence a number comes from.
- **Cite every claim** as `PMID: <number>`. If nothing relevant is found, say so instead of answering from memory.
- When taking PK parameters from a paper, report which population they come from (patients vs healthy volunteers) and whether they are apparent oral values (CL/F, V/F).
