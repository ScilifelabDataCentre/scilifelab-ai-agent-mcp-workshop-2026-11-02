"""MCP tests with imports rooted at the combined repository."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT / "Section_2_MCP", ROOT / "scripts"):
    value = str(directory)
    if value not in sys.path:
        sys.path.insert(0, value)
