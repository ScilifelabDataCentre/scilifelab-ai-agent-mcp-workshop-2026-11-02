"""Workshop configuration. Every value can be overridden with an environment variable."""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent
WORKSHOP_ROOT = REPO_DIR.parent
ENV_FILE = WORKSHOP_ROOT / ".env"

# Both sections share only the combined root .env. Runtime environment variables
# always take precedence, and no section-level .env file is loaded.
if ENV_FILE.is_file():
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)  # Existing environment variables take precedence.

# The participant's own input always wins. These defaults are used when nothing is provided.
DEFAULT_QUESTION = os.environ.get(
    "LITREVIEW_DEFAULT_QUESTION",
    "Which subgroups of type 2 diabetes have been proposed, and how do they differ "
    "in outcomes or treatment response?",
)
DEFAULT_QUERY = os.environ.get(
    "LITREVIEW_DEFAULT_QUERY",
    '"type 2 diabetes" AND (subgroups OR clusters OR subtypes)',
)

EUROPEPMC_BASE_URL = os.environ.get(
    "EUROPEPMC_BASE_URL", "https://www.ebi.ac.uk/europepmc/webservices/rest"
)
HTTP_TIMEOUT_S = float(os.environ.get("LITREVIEW_HTTP_TIMEOUT", "20"))
USER_AGENT = os.environ.get(
    "LITREVIEW_USER_AGENT", "scilifelab-mcp-workshop/2026.11 (open-llm@scilifelab.se)"
)

# Limits enforced by the server, whatever the schema or the prompt says.
MAX_RESULTS_LIMIT = int(os.environ.get("LITREVIEW_MAX_RESULTS", "25"))
MAX_QUERY_CHARS = int(os.environ.get("LITREVIEW_MAX_QUERY_CHARS", "400"))
SNIPPET_CHARS = int(os.environ.get("LITREVIEW_SNIPPET_CHARS", "600"))
FULL_ABSTRACT_CHARS = int(os.environ.get("LITREVIEW_FULL_ABSTRACT_CHARS", "6000"))

# live:    always ask Europe PMC, and refresh the cache
# cache:   use a cached response when there is one, otherwise ask Europe PMC and store it (default)
# offline: cached responses only; fail clearly when a response is missing
MODE = os.environ.get("LITREVIEW_MODE", "cache").lower()
CACHE_DIR = Path(os.environ.get("LITREVIEW_CACHE_DIR", str(REPO_DIR / "fixtures" / "cache")))
