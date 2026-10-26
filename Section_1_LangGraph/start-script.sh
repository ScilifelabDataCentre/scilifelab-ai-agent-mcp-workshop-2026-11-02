#!/bin/bash
set -e

ENV_FILE=/home/workshop/app/.env

# Build .env from environment variables provided at runtime.
# The SciLifeLab pilot LLM service is used by default; OpenAI is the fallback.
: > "$ENV_FILE"

# SciLifeLab pilot service key (default LLM). Only written if provided
# at runtime via -e PILOT_API_KEY="sk-...".
if [ -n "$OPENLLM_API_KEY" ]; then
    echo "OPENLLM_API_KEY=\"$OPENLLM_API_KEY\"" >> "$ENV_FILE"
    echo "✓ OPENLLM_API_KEY written to .env"
else
    echo "⚠  No OPENLLM_API_KEY set (SciLifeLab pilot service will be unavailable)."
fi

echo ""
echo "============================================================"
echo "  Developing AI Agents in Life Sciences, Hands-on Session 1:"
echo "  Developing AI agents with LangGraph & ReAct"
echo "  2026-03-05"
echo "  Open: http://localhost:8888"
echo "  Then open: Section_1_LangGraph/langgraph_lab.ipynb"
echo "============================================================"
echo ""

python -m jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --NotebookApp.token='' \
    --NotebookApp.password='' \
    --notebook-dir=/home/workshop/app