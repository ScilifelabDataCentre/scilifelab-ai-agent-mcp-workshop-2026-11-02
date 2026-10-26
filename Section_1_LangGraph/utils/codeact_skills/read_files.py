from __future__ import annotations

from pathlib import Path

from langchain.tools import tool

SKILLS_DIR = Path(__file__).parent / "skills"


@tool
def read_skill(name: str) -> str:
    """Read the full SKILL.md for the named skill.

    Args:
        name: The skill name (the folder name under skills/), e.g. "chemistry".

    Returns:
        The full Markdown contents — description plus example code that you
        can adapt and run via `python_executor`.
    """
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        available = ", ".join(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())
        return f"Skill '{name}' not found. Available: {available}"
    return path.read_text()
