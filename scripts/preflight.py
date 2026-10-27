#!/usr/bin/env python3
"""Validate the combined image, CI/CD, and SciLifeLab Serve custom-app contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true", help="Accepted for workflow consistency")
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    oks: list[str] = []

    def require(condition: bool, success: str, failure: str) -> None:
        (oks if condition else errors).append(success if condition else failure)

    required = [
        "Dockerfile", "start-script.sh", "requirements.txt", ".dockerignore", ".env.example",
        ".serve-template.json", "README.md", "RUNBOOK.md",
        "Section_1_LangGraph/langgraph_lab.ipynb", "Section_1_LangGraph/requirements.txt",
        "Section_2_MCP/server.py", "Section_2_MCP/1-mcp-hands-on/mcp_literature_review_lab.ipynb",
        "scripts/supervisord.conf", "scripts/start_jupyter_when_ready.sh",
        "scripts/start_combined_docker.sh", "scripts/mcp_health.py", "scripts/workshop_healthcheck.py",
        ".github/workflows/combined-image.yml",
    ]
    for rel in required:
        require((root / rel).is_file(), f"Found {rel}", f"Missing {rel}")

    metadata = json.loads((root / ".serve-template.json").read_text(encoding="utf-8"))
    require(metadata.get("app_type") == "custom", "Custom app metadata", "app_type must be custom")
    require(metadata.get("app_port") == 7860, "Serve port metadata is 7860", "app_port must be 7860")
    require(metadata.get("mcp_internal_port") == 8000, "MCP internal port metadata", "MCP port must be 8000")
    require(metadata.get("serve_uid") == 1000, "Serve UID metadata is 1000", "serve_uid must be 1000")
    require(metadata.get("entrypoint") == "start-script.sh", "Startup-script metadata", "entrypoint must be start-script.sh")
    require(metadata.get("image_architecture") == "linux/amd64", "amd64 Serve target metadata", "image_architecture must be linux/amd64")
    require(metadata.get("image_architectures") == ["linux/amd64", "linux/arm64"],
            "amd64 and arm64 image metadata", "image_architectures must list amd64 and arm64")
    require(metadata.get("workshop_directories") == ["Section_1_LangGraph", "Section_2_MCP"],
            "Both workshop directories in metadata", "Metadata must list both workshop directories")

    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    require("FROM python:3.12-slim" in dockerfile, "Common Python 3.12 base", "Expected python:3.12-slim")
    require("useradd --create-home --uid 1000" in dockerfile, "Dockerfile creates UID 1000", "Dockerfile must create UID 1000")
    users = [line.strip() for line in dockerfile.splitlines() if line.strip().startswith("USER ")]
    require(bool(users) and users[-1] == "USER 1000", "Final runtime user is UID 1000", "Final USER must be 1000")
    exposes = [line.strip() for line in dockerfile.splitlines() if line.strip().startswith("EXPOSE ")]
    require(exposes == ["EXPOSE 7860"], "Only Jupyter Serve port is exposed", "Dockerfile must expose only 7860")
    require("WORKDIR $HOME/app" in dockerfile, "Dockerfile defines app WORKDIR", "Expected WORKDIR $HOME/app")
    require("COPY requirements.txt ./requirements.txt" in dockerfile, "Root dependencies are copied", "Missing root requirements COPY")
    require("pip install --no-cache-dir -r requirements.txt" in dockerfile,
            "One combined dependency installation", "Dockerfile must install the root requirements")
    require("Section_1_LangGraph/requirements.txt" not in dockerfile and "Section_2_MCP/requirements" not in dockerfile,
            "Conflicting section requirements are not installed", "Install only the harmonized root requirements")
    for directory in ("Section_1_LangGraph", "Section_2_MCP"):
        require(f"COPY --chown=1000:1000 {directory} ./{directory}" in dockerfile,
                f"{directory} copied below Jupyter root", f"Missing {directory} COPY")
    require('ENTRYPOINT ["./start-script.sh"]' in dockerfile, "Startup-script entrypoint", "Dockerfile must use start-script.sh")
    require('CMD ["python", "scripts/workshop_healthcheck.py"]' in dockerfile,
            "Combined Docker health check", "Dockerfile must run the combined health check")
    require(".env" not in re.sub(r"OPENLLM_API_KEY|MCP_URL|LITREVIEW_MODE", "", dockerfile),
            "Dockerfile does not create a .env file", "Do not create or copy .env in the image")

    start = (root / "start-script.sh").read_text(encoding="utf-8")
    require(start.lstrip().startswith("#!"), "Root startup has a shebang", "Startup script needs a shebang")
    require("exec supervisord -c scripts/supervisord.conf" in start,
            "Supervisor is the container entrypoint", "Root startup must exec Supervisor")

    supervisor = (root / "scripts/supervisord.conf").read_text(encoding="utf-8")
    require("python Section_2_MCP/server.py" in supervisor, "Supervisor starts internal MCP", "Missing MCP command")
    require("bash scripts/start_jupyter_when_ready.sh" in supervisor, "Supervisor starts one JupyterLab", "Missing Jupyter command")
    require(supervisor.count("autorestart=true") == 2, "Both processes restart automatically", "Both programs need autorestart=true")

    jupyter = (root / "scripts/start_jupyter_when_ready.sh").read_text(encoding="utf-8")
    require("scripts/mcp_health.py" in jupyter, "Jupyter waits for real MCP health", "Jupyter must wait for MCP discovery")
    require("--ip=0.0.0.0" in jupyter, "Jupyter binds 0.0.0.0", "Jupyter must bind 0.0.0.0")
    require('--ServerApp.root_dir="$PWD"' in jupyter, "Jupyter root shows both directories", "Jupyter root_dir must be the repository app root")
    require('WORKSHOP_LOCAL_NO_AUTH:-0' in jupyter, "Token-free mode is opt-in", "Token-free mode must be opt-in")
    require('JUPYTER_TOKEN:-' in jupyter, "Explicit Jupyter token is supported", "Startup must support JUPYTER_TOKEN")
    require("generated token in the logs" in jupyter, "Default token location is reported", "Startup must mention generated-token logs")

    launcher = (root / "scripts/start_combined_docker.sh").read_text(encoding="utf-8")
    require("-p 127.0.0.1::7860" in launcher, "Jupyter host publication is loopback-only", "Launcher must publish Jupyter on 127.0.0.1")
    require("-p 127.0.0.1::8000" in launcher, "Optional MCP publication is loopback-only", "Launcher must publish MCP on 127.0.0.1")
    require("--env-file" in launcher, "Local .env is runtime-only", "Launcher must use Docker --env-file")
    require("WORKSHOP_LOCAL_NO_AUTH=1" in launcher, "Only local launcher disables token auth", "Local launcher must explicitly opt into no-auth mode")
    require("aarch64|arm64" in launcher and "x86_64|amd64" in launcher,
            "Launcher auto-detects amd64 and arm64", "Launcher must map both Docker host architectures")
    require('docker build --platform "$PLATFORM"' in launcher and '--platform "$PLATFORM"' in launcher,
            "Local build and run use the detected platform", "Launcher must build and run with WORKSHOP_PLATFORM")

    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    for pin in ("langchain[mcp]==1.4.6", "langchain-openai==1.7.2", "langgraph==1.2.16",
                "mcp[cli]==2.3.0", "jupyterlab==4.5.11", "rdkit==2025.9.4"):
        require(pin in requirements, f"Combined requirements include {pin}", f"Missing {pin}")

    workflow = (root / ".github/workflows/combined-image.yml").read_text(encoding="utf-8")
    require("for ARCH in amd64 arm64" in workflow and '--platform "linux/${ARCH}"' in workflow,
            "CI builds linux/amd64 and linux/arm64", "Workflow must build both architectures")
    require("setup-qemu-action" in workflow, "CI enables ARM64 smoke-test emulation", "Workflow must set up QEMU for ARM64")
    require(workflow.count("for ARCH in amd64 arm64") >= 2 and "Smoke-test both architectures" in workflow,
            "CI smoke-tests both architectures", "Workflow must smoke-test amd64 and arm64")
    require("uname -m" in workflow and "EXPECTED_MACHINE" in workflow,
            "CI verifies each runtime architecture", "Workflow must verify amd64 and arm64 execution")
    require("imagetools create" in workflow and '"${IMAGE_REF}-arm64"' in workflow,
            "CI publishes one multi-architecture manifest", "Workflow must publish an amd64/arm64 manifest")
    require("scripts/preflight.py --strict" in workflow, "CI runs Serve preflight", "Workflow must run preflight")
    require("scripts/workshop_healthcheck.py" in workflow, "CI smoke-tests MCP and Jupyter", "Workflow must run combined health check")
    require("id -u" in workflow and "1000" in workflow, "CI verifies runtime UID", "Workflow must verify UID 1000")
    require("packages: write" in workflow and "GITHUB_TOKEN" in workflow, "CI can publish to GHCR", "Workflow needs GHCR permissions and token")
    require("GITHUB_SHA" in workflow and "date -u" in workflow, "CI creates unique tags", "Workflow needs timestamp/SHA tags")
    require(not re.search(r"(?i)(?:-t|--tag)\s+[^\s]+:latest\b", workflow), "CI does not publish latest", "Do not publish latest")

    forbidden = [p for p in root.rglob("*") if p.is_file() and p.name == ".env"]
    require(not forbidden, "No .env file is packaged", "Do not package .env")
    secret_patterns = [
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(rb"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})"),
    ]
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.stat().st_size > 1_000_000:
            continue
        data = path.read_bytes()
        if any(pattern.search(data) for pattern in secret_patterns):
            findings.append(str(path.relative_to(root)))
    require(not findings, "No common credential patterns", "Possible credentials in: " + ", ".join(findings))

    for message in oks:
        print(f"OK: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    print(f"Combined Serve preflight: {len(oks)} checks passed, {len(errors)} failed")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
