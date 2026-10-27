# Participant/Serve image: JupyterLab on 7860; the MCP server stays internal on 8000.
# Build for SciLifeLab Serve from this folder:
#   docker build --platform linux/amd64 \
#     -t ghcr.io/<org>/ai-agents-workshop-session2:<unique-tag> .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USER=workshop \
    HOME=/home/workshop \
    LITREVIEW_MODE=cache \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_URL=http://127.0.0.1:8000/mcp \
    JUPYTER_PORT=7860

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 workshop
WORKDIR /home/workshop/session-2-mcp

COPY requirements.txt .
COPY 3-bonus-one-server-many-hosts/requirements-demo.txt ./3-bonus-one-server-many-hosts/requirements-demo.txt
RUN pip install --no-cache-dir \
    -r requirements.txt \
    -r 3-bonus-one-server-many-hosts/requirements-demo.txt

COPY --chown=1000:1000 . .
# Serve requires a startup script in WORKDIR and a non-root process with UID 1000.
RUN chmod +x ./start-script.sh \
    && mkdir -p work fixtures/cache \
    && chown -R 1000:1000 /home/workshop/session-2-mcp
USER 1000

# Serve routes only this port. Container-to-container MCP access remains on internal port 8000.
EXPOSE 7860
HEALTHCHECK --interval=15s --timeout=6s --start-period=60s --retries=3 \
  CMD ["python", "scripts/workshop_healthcheck.py"]
STOPSIGNAL SIGTERM
ENTRYPOINT ["./start-script.sh"]
