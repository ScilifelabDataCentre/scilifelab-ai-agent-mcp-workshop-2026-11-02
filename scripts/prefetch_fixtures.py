"""Fill fixtures/cache with Europe PMC responses for the workshop defaults.

Run it with network access before building the images, so the class can continue if
Europe PMC or the venue network fails:

    python scripts/prefetch_fixtures.py
    python scripts/prefetch_fixtures.py --query '"gut microbiome" AND depression'   # add your own
    python scripts/prefetch_fixtures.py --metadata-only   # drop abstracts, for images you publish
"""

import argparse
import sys
from pathlib import Path

MCP_ROOT = Path(__file__).resolve().parents[1] / "Section_2_MCP"
sys.path.insert(0, str(MCP_ROOT))

from litreview import config, europepmc  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache Europe PMC responses for the workshop")
    parser.add_argument("--query", action="append", default=[], help="another query to cache (repeatable)")
    parser.add_argument("--metadata-only", action="store_true",
                        help="remove abstracts from the cache afterwards (identifiers and titles stay)")
    args = parser.parse_args()

    config.MODE = "live"  # always ask Europe PMC and store the answers
    calls = 0
    for query in [config.DEFAULT_QUERY, *args.query]:
        for number in (1, 2, 3, 5, 10):                       # the notebook and demo calls
            europepmc.search(query, max_results=number)
            calls += 1
        for sort in ("cited", "newest"):
            europepmc.search(query, max_results=10, sort=sort)
            calls += 1
        for number in (5, 8):                                 # build_evidence_table defaults
            europepmc.search(query, max_results=number, sort="cited", from_year=2015)
            calls += 1
        top = europepmc.search(query, max_results=10)["papers"]
        for paper in top[:5]:                                 # abstracts an agent is likely to read
            europepmc.get_paper(paper["id"])
            calls += 1
        if top:
            europepmc.citing_papers(top[0]["id"], max_results=10)
            calls += 1
    print(f"Cached {calls} responses in {config.CACHE_DIR}")
    if args.metadata_only:
        print(f"Removed {europepmc.strip_abstracts_in_cache()} abstracts from the cache")


if __name__ == "__main__":
    main()
