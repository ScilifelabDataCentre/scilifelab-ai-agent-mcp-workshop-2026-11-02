#!/usr/bin/env python3
"""Validate the workshop image against its SciLifeLab Serve custom-app contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true", help="Accepted for template workflow compatibility")
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    oks: list[str] = []

    def require(condition: bool, success: str, failure: str) -> None:
        (oks if condition else errors).append(success if condition else failure)

    required = [
        "Dockerfile", "start-script.sh", "scripts/start_jupyter_when_ready.sh",
        "scripts/start_workshop_docker.sh", "scripts/supervisord.conf", "scripts/workshop_healthcheck.py",
        "requirements.txt", "requirements-server.txt", "README.md", "DEPLOY_SERVE.md",
        ".serve-template.json", ".github/workflows/preflight.yml",
        ".github/workflows/docker-image-ghcr.yml",
    ]
    for rel in required:
        require((root / rel).is_file(), f"Found {rel}", f"Missing {rel}")

    metadata = json.loads((root / ".serve-template.json").read_text(encoding="utf-8"))
    require(metadata.get("app_type") == "custom", "Custom app metadata", "app_type must be custom")
    require(metadata.get("app_port") == 7860, "Jupyter Serve port metadata", "app_port must be 7860")
    require(metadata.get("mcp_internal_port") == 8000, "Internal MCP port metadata",
            "mcp_internal_port must be 8000")
    require(metadata.get("serve_uid") == 1000, "Serve UID metadata is 1000", "serve_uid must be 1000")

    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    require("FROM python:3.12-slim" in dockerfile, "Pinned Python base image", "Expected python:3.12-slim")
    require("1000" in dockerfile, "Dockerfile establishes UID 1000", "Dockerfile must establish UID 1000")
    users = [line.strip() for line in dockerfile.splitlines() if line.strip().startswith("USER ")]
    require(bool(users) and users[-1] == "USER 1000", "Final runtime user is UID 1000", "Final USER must be 1000")
    require(re.search(r"(?m)^EXPOSE 7860$", dockerfile) is not None,
            "Dockerfile exposes Jupyter port 7860", "Dockerfile must EXPOSE 7860")
    require(not re.search(r"(?m)^EXPOSE\s+\d+\s+\d+", dockerfile),
            "Only the Serve web port is exposed", "Do not expose internal MCP as a second Serve port")
    require("WORKDIR " in dockerfile, "Dockerfile defines WORKDIR", "Dockerfile must define WORKDIR")
    require("chmod +x ./start-script.sh" in dockerfile, "Startup script is executable",
            "Dockerfile must chmod +x ./start-script.sh")
    require('ENTRYPOINT ["./start-script.sh"]' in dockerfile, "Startup-script entrypoint",
            "Dockerfile must use the startup script as ENTRYPOINT")
    require("requirements-demo.txt" in dockerfile, "Demo dependencies install at build time",
            "Dockerfile must include demo requirements")

    start = (root / "start-script.sh").read_text(encoding="utf-8")
    require("supervisord" in start, "Supervisor remains the container entrypoint",
            "Startup must launch Supervisor")
    jupyter = (root / "scripts/start_jupyter_when_ready.sh").read_text(encoding="utf-8")
    require("--ip=0.0.0.0" in jupyter, "Jupyter binds 0.0.0.0", "Jupyter must bind 0.0.0.0")
    require('WORKSHOP_LOCAL_NO_AUTH:-0' in jupyter, "Token-free mode is opt-in",
            "Token-free mode must require WORKSHOP_LOCAL_NO_AUTH=1")
    require('JUPYTER_TOKEN:-' in jupyter, "Serve can use JUPYTER_TOKEN",
            "Jupyter startup must support JUPYTER_TOKEN")
    require("generated token in the logs" in jupyter, "Default startup reports generated-token location",
            "Default startup must explain generated-token logs")
    launcher = (root / "scripts/start_workshop_docker.sh").read_text(encoding="utf-8")
    require('WORKSHOP_LOCAL_NO_AUTH=1' in launcher, "Local launcher explicitly enables local token-free mode",
            "Local launcher must opt into token-free mode")
    require('127.0.0.1::7860' in launcher, "Local Jupyter publication is loopback-only",
            "Local launcher must publish Jupyter only on 127.0.0.1")
    health = (root / "scripts/workshop_healthcheck.py").read_text(encoding="utf-8")
    require("{401, 403}" in health and "/login" in health,
            "Health check accepts authenticated Jupyter responses",
            "Health check must handle Jupyter authentication")

    for workflow in ("preflight.yml", "docker-image-ghcr.yml"):
        text = (root / ".github/workflows" / workflow).read_text(encoding="utf-8")
        require("linux/amd64" in text, f"{workflow} builds linux/amd64", f"{workflow} must build linux/amd64")
        require("scripts/workshop_healthcheck.py" in text, f"{workflow} tests both services",
                f"{workflow} must run scripts/workshop_healthcheck.py")
        require("/login" in text, f"{workflow} tests authenticated Jupyter",
                f"{workflow} must check Jupyter /login")
    publish = (root / ".github/workflows/docker-image-ghcr.yml").read_text(encoding="utf-8")
    require("packages: write" in publish, "GHCR workflow can write packages", "GHCR workflow needs packages: write")
    require("GITHUB_SHA" in publish and "date -u" in publish, "GHCR tags are unique",
            "GHCR workflow needs timestamp/SHA tags")
    require(not re.search(r"(?i)(?:-t|--tag)\s+[^\s]+:latest\b", publish),
            "GHCR workflow does not publish latest", "Do not publish latest")

    forbidden = [p for p in root.rglob("*") if p.is_file() and p.name == ".env"]
    require(not forbidden, "No .env file", "Do not package .env")
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
    print(f"Serve preflight: {len(oks)} checks passed, {len(errors)} failed")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
