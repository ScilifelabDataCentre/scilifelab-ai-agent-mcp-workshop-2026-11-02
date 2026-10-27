# Developing AI Agents in Life Sciences: Combined Workshop Image

One Docker image for both hands-on sessions, with one JupyterLab interface and two workshop directories:

```text
Repository root
├── Dockerfile                 # The only Dockerfile used for the combined image
├── requirements.txt           # Harmonized dependencies for both sessions
├── start-script.sh            # SciLifeLab Serve/container entrypoint
├── Section_1_LangGraph/       # LangGraph and ReAct workshop
├── Section_2_MCP/             # Model Context Protocol workshop
├── scripts/                   # Startup, health, recovery, and validation helpers
├── .github/workflows/         # CI/CD, including combined-image.yml
└── RUNBOOK.md                 # Detailed operation and Serve deployment guide
```

The section-level Dockerfiles remain as historical references. **Build only from the repository root.** CI/CD and Serve use the root `Dockerfile` and root `requirements.txt`.

## What runs inside the image

- **JupyterLab:** `0.0.0.0:7860`, showing both workshop directories.
- **MCP server:** `0.0.0.0:8000` inside the container, available to notebooks at `http://127.0.0.1:8000/mcp`.
- **Supervisor:** starts both processes, waits for real MCP discovery before starting JupyterLab, and restarts failed processes.
- **Runtime user:** non-root UID `1000`, as expected by the Serve custom-application pattern.
- **Architectures:** native `linux/amd64` and `linux/arm64` images, published under one multi-architecture tag.

Jupyter authentication is enabled by default. The local launcher alone enables token-free mode and publishes Jupyter only on `127.0.0.1`.

## Quick start on your computer

### 1. Prepare optional model settings

Model-backed notebook cells need an OpenLLM key. MCP-only and non-model exercises do not.

```bash
cp .env.example .env
```

Edit `.env` locally and add your own `OPENLLM_API_KEY`. Never commit this file. If you skip this step, the workshops still start, but model-backed cells remain unavailable.

### 2. Build and start the combined image

From the repository root:

```bash
bash scripts/start_combined_docker.sh --build
```

The launcher detects the Docker host, builds `ai-agents-workshop:local` for native `linux/amd64` or `linux/arm64`, starts the container, waits for both services, and prints a loopback JupyterLab URL. Docker selects a free host port automatically.

To override detection explicitly:

```bash
WORKSHOP_PLATFORM=linux/arm64 bash scripts/start_combined_docker.sh --build --recreate
# Use linux/amd64 on Intel/AMD hosts.
```

### 3. Open a workshop notebook

- Session 1: `Section_1_LangGraph/langgraph_lab.ipynb`
- Session 2: `Section_2_MCP/1-mcp-hands-on/mcp_literature_review_lab.ipynb`

Save files you want to keep in the top-level `work/` directory. That directory is mounted from your computer and survives container replacement.

### 4. Stop or recover

```bash
docker stop ai-agents-workshop
bash scripts/start_combined_docker.sh --restart
bash scripts/start_combined_docker.sh --restart-mcp
bash scripts/start_combined_docker.sh --status
```

After changing code, dependencies, or `.env`, recreate the container:

```bash
bash scripts/start_combined_docker.sh --build --recreate
```

## Manual Docker alternative

```bash
docker build -t ai-agents-workshop:local .  # Uses the host's native architecture
docker run -d --name ai-agents-workshop \
  --env-file .env \
  -p 127.0.0.1::7860 \
  -v "$PWD/work:/home/workshop/app/work" \
  ai-agents-workshop:local

docker port ai-agents-workshop 7860/tcp
docker logs ai-agents-workshop
```

This manual command keeps Jupyter authentication enabled. Use the generated token from the logs when opening the printed address. Do not set `WORKSHOP_LOCAL_NO_AUTH=1` outside a loopback-only local deployment.

## Change code and publish a new image

The included `.github/workflows/combined-image.yml` workflow provides the complete build path:

1. Push this repository to GitHub.
2. Open a pull request to build and smoke-test without publishing.
3. Push or merge to `main`, or run **Combined workshop image** manually with **Run workflow**, to publish to GHCR.
4. Open the workflow summary and copy the exact image reference.

CI first checks which files changed. A commit limited to root documentation or repository metadata (for example `README.md`, `RUNBOOK.md`, `CITATION.cff`, or `docs/`) skips Python tests, Docker builds, smoke tests, and publication. Changes under either workshop directory—including notebooks and section-local README files—still require a new tested image because those files are copied into it. A mixed documentation/code change runs the full checks. **Run workflow** always forces the full validation and build path.

Buildx reuses separate GitHub Actions caches for amd64 and arm64. This usually avoids reinstalling unchanged dependencies; it does not skip tests or smoke tests when image content changes.

Tags contain the UTC time, commit SHA, run number, and attempt. Each published tag is a multi-architecture manifest containing both variants, so Docker automatically selects arm64 on ARM hosts and amd64 on Intel/AMD hosts and Serve. The workflow never publishes `latest`, and it does not push an image until these checks pass:

- combined Serve preflight and MCP tests;
- separate `linux/amd64` and `linux/arm64` image builds;
- both workshop directories and notebooks present in both variants;
- runtime UID `1000` and executed architecture checks;
- authenticated Jupyter `/login`, real MCP `server/discover`, and combined health checks on both variants (arm64 runs through QEMU in CI).

Make the GHCR package **Public** if necessary so Serve can retrieve it without registry credentials.

## Deploy on SciLifeLab Serve

Create a **Custom app** with:

| Field | Value |
|---|---|
| Image | Exact multi-architecture GHCR manifest reference from the successful workflow; Serve selects its amd64 variant |
| Port | `7860` |
| Storage | `None` for disposable use, or mount `/home/workshop/app/work` for shared files |
| Source code URL | This public repository |
| Hardware | Start with the default; increase only if observed memory/CPU use requires it |
| Permission | Project/Private for temporary testing; Link/Public only for an intentionally shared demonstration |

After startup:

1. Open the Serve app's **Logs** page.
2. Find Jupyter's generated token in a URL containing `token=...`.
3. Open the app URL and paste the token into Jupyter's login page.
4. Select either workshop directory and verify a non-model notebook step.
5. Check model-backed cells only when a key has been supplied through an approved runtime secret mechanism.

**A Serve deployment is one shared JupyterLab instance, not one isolated environment per participant.** Users can run code and change shared files. Do not place personal, sensitive, patient, or private research data in the app. Do not paste a shared OpenLLM key into a shared notebook.

To update Serve, push a new change, wait for a new unique image tag, and replace the app's **Image** value. Reusing an old tag does not deploy a new build. Full instructions are in [RUNBOOK.md](RUNBOOK.md).

## Dependency policy

The two original requirement files contain different pins for shared packages. Installing both directly would produce a pip conflict. The root `requirements.txt` is therefore the authoritative combined environment:

| Shared component | Combined choice |
|---|---|
| Python | 3.12 |
| JupyterLab | 4.5.11 |
| ipykernel | 7.4.0 |
| LangChain | 1.4.6, with MCP support |
| LangChain OpenAI | 1.7.2 |
| LangGraph | 1.2.16 |
| MCP Python SDK | 2.3.0 |
| requests | 2.33.1 |
| python-dotenv | 1.2.2 |

Section 1 scientific packages and Session 2 MCP/Deep Agents packages are retained in the same root dependency resolution. After a rehearsal, generate and review a lock file if you want a fully transitive-pinned release.

## Validation commands

```bash
python scripts/preflight.py --strict
python -m unittest discover -s tests -t . -v
python -m unittest discover -s Section_2_MCP/tests -t Section_2_MCP -v
```

See [Section 1 notes](Section_1_LangGraph/README.md), [Session 2 notes](Section_2_MCP/README.md), and the [combined runbook](RUNBOOK.md) for workshop-specific details.
