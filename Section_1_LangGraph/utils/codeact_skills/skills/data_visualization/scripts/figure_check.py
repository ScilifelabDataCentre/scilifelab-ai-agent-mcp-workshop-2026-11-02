"""Vision-LLM figure reviewer for the data_visualization skill.

Sends a saved figure to a vision-capable OpenAI model and returns five short
critiques covering Readability, Panel Arrangement, Axis Labels, Legend, and
Color. Designed to be called from `python_executor` inside the CodeAct agent.

Usage:
    from utils.codeact_skills.skills.data_visualization.scripts.figure_check import figure_check
    feedback = figure_check("my_plot.png")
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, model_validator

FIGURE_EVALUATION_SYSTEM_PROMPT = """You are a senior figure reviewer for a peer-reviewed life-sciences journal.
Evaluate the supplied figure against publication standards and return critical, actionable feedback on five dimensions:

  1. Readability       — font sizes, text overlap, contrast, ink economy.
  2. Panel Arrangement — panel ordering, spacing, sizing, panel labels (A/B/C).
  3. Axis Labels       — clarity, units in parentheses, tick legibility, presence of top/right spines.
  4. Legend            — placement, frame, font size, redundancy.
  5. Color             — colorblind safety (Wong 2011), colormap appropriateness, colorbar labels.

For each dimension write one or two concise sentences. If the figure is already correct on that dimension, say so briefly.

Respond with a SINGLE JSON object and nothing else, using exactly these keys:
{
  "Readability": "...",
  "Panel Arrangement": "...",
  "Axis Labels": "...",
  "Legend": "...",
  "Color": "..."
}
"""


class FigureFeedback(BaseModel):
    """Structured output from the figure-evaluation LLM."""

    Readability: str = Field(default="No feedback provided.")
    Panel_Arrangement: str = Field(default="No feedback provided.", alias="Panel Arrangement")
    Axis_Labels: str = Field(default="No feedback provided.", alias="Axis Labels")
    Legend: str = Field(default="No feedback provided.")
    Color: str = Field(default="No feedback provided.")

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def _fill_blanks(cls, values: dict) -> dict:
        fallback = "No feedback provided."
        return {
            k: (v if isinstance(v, str) and v.strip() else fallback)
            for k, v in values.items()
        }

    def to_dict(self) -> dict[str, str]:
        return {
            "Readability": self.Readability,
            "Panel Arrangement": self.Panel_Arrangement,
            "Axis Labels": self.Axis_Labels,
            "Legend": self.Legend,
            "Color": self.Color,
        }


_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


PILOT_BASE_URL = "https://open-llm.scilifelab.se/api"
PILOT_MODEL = "qwen3"        # or "gemma3-27b"
OPENAI_MODEL = "gpt-5.4"     # fallback model
def get_llm(temperature: float = 0, **kwargs) -> ChatOpenAI:
    """Return a chat model, preferring the SciLifeLab pilot service.

    Order of preference:
      1. SciLifeLab pilot LLM (`PILOT_MODEL`) — used by default.
      2. OpenAI (`OPENAI_MODEL`) — fallback if the pilot service can't be
         reached during the session, or if no `PILOT_API_KEY` is set.
    """
    pilot_key = os.getenv("PILOT_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # 1) Try the pilot service first
    if pilot_key:
        pilot_llm = ChatOpenAI(
            model=PILOT_MODEL,
            base_url=PILOT_BASE_URL,
            api_key=pilot_key,
            temperature=temperature,
            extra_body = {"chat_template_kwargs": {"enable_thinking": False}},
            **kwargs,
        )
        try:
            pilot_llm.invoke("ping")  # lightweight connectivity check
            print(f"✓ Using SciLifeLab pilot LLM ({PILOT_MODEL})")
            return pilot_llm
        except Exception as e:
            print(f"⚠ Pilot LLM unavailable ({type(e).__name__}: {e}). Falling back to OpenAI.")
    else:
        print("⚠ PILOT_API_KEY not set — falling back to OpenAI.")

    # 2) Fall back to OpenAI
    if not openai_key:
        raise RuntimeError(
            "No usable LLM: the pilot service failed and OPENAI_API_KEY is not set. "
            "Set PILOT_API_KEY and/or OPENAI_API_KEY in your .env file."
        )
    print(f"✓ Using OpenAI fallback ({OPENAI_MODEL})")
    return ChatOpenAI(model=OPENAI_MODEL, temperature=temperature, **kwargs)


def _encode_image(path: Path) -> tuple[str, str]:
    media_type = _MEDIA_TYPES.get(path.suffix.lower(), "image/png")
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return data, media_type


def _parse(raw: str) -> FigureFeedback:
    """Tolerant JSON parser — strips code fences, falls back to brace slice."""
    clean = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    data: dict = {}
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        start, end = clean.find("{"), clean.rfind("}")
        if 0 <= start < end:
            try:
                data = json.loads(clean[start:end + 1])
            except json.JSONDecodeError:
                data = {}
    return FigureFeedback.model_validate(data)


def figure_check(figure_path: str, model: str = "gpt-5") -> dict[str, str]:
    """Evaluate a saved figure on five publication-quality dimensions.

    Args:
        figure_path: Path to a PNG/JPG/SVG/etc. figure file.
        model: Vision-capable OpenAI model name.

    Returns:
        A dict with keys: "Readability", "Panel Arrangement",
        "Axis Labels", "Legend", "Color". Each value is a short critique.
    """
    path = Path(figure_path)
    if not path.exists():
        raise FileNotFoundError(f"Figure not found: {figure_path}")

    image_data, media_type = _encode_image(path)

    llm = get_llm(temperature=0)
    messages = [
        SystemMessage(content=FIGURE_EVALUATION_SYSTEM_PROMPT),
        HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_data}",
                    "detail": "high",
                },
            },
            {
                "type": "text",
                "text": "Evaluate this figure against the publication standards in the system prompt. Return ONLY the JSON object.",
            },
        ]),
    ]
    raw = llm.invoke(messages).content
    return _parse(raw).to_dict()
