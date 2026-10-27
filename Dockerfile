# Combined workshop image: one JupyterLab, two workshop directories, internal MCP.
# Build from the repository root for linux/amd64 or linux/arm64, not from a workshop subdirectory.
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    USER=workshop \
    HOME=/home/workshop \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LITREVIEW_MODE=cache \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_URL=http://127.0.0.1:8000/mcp \
    JUPYTER_PORT=7860

# Keep Section 1's native/runtime libraries and add Supervisor for MCP recovery.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 "$USER"
WORKDIR $HOME/app

# This root file deliberately harmonizes shared dependencies from both sections.
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Jupyter's root contains exactly these two workshop content directories.
COPY --chown=1000:1000 Section_1_LangGraph ./Section_1_LangGraph
COPY --chown=1000:1000 Section_2_MCP ./Section_2_MCP
COPY --chown=1000:1000 scripts ./scripts
COPY --chown=1000:1000 start-script.sh ./start-script.sh


RUN chmod +x ./start-script.sh ./scripts/*.sh \
    && mkdir -p work Section_2_MCP/work \
    && chown -R 1000:1000 "$HOME/app"

USER 1000
EXPOSE 7860
HEALTHCHECK --interval=15s --timeout=6s --start-period=90s --retries=3 \
  CMD ["python", "scripts/workshop_healthcheck.py"]
STOPSIGNAL SIGTERM
ENTRYPOINT ["./start-script.sh"]
