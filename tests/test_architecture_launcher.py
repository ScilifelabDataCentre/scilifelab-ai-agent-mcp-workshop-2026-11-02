from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/start_combined_docker.sh"


class ArchitectureLauncherTests(unittest.TestCase):
    def run_launcher(self, host_arch: str, platform: str | None = None) -> tuple[subprocess.CompletedProcess, str]:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            log_file = Path(tmp) / "docker-calls"
            fake_docker = bin_dir / "docker"
            fake_docker.write_text(
                """#!/usr/bin/env bash
set -eu
case "${1:-}" in
  info)
    if [[ "${2:-}" == "--format" ]]; then printf '%s\\n' "$FAKE_DOCKER_ARCH"; fi
    ;;
  build)
    printf 'build' >> "$DOCKER_CALL_LOG"
    printf ' %s' "$@" >> "$DOCKER_CALL_LOG"
    printf '\\n' >> "$DOCKER_CALL_LOG"
    ;;
  container)
    # An existing running container lets the launcher finish without a real runtime.
    exit 0
    ;;
  inspect)
    printf 'true\\n'
    ;;
  exec)
    exit 0
    ;;
  port)
    printf '127.0.0.1:49152\\n'
    ;;
  run|pull)
    printf '%s' "$1" >> "$DOCKER_CALL_LOG"
    printf ' %s' "$@" >> "$DOCKER_CALL_LOG"
    printf '\\n' >> "$DOCKER_CALL_LOG"
    ;;
  *) ;;
esac
""",
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            env = os.environ.copy()
            env.update({
                "PATH": f"{bin_dir}:{env['PATH']}",
                "FAKE_DOCKER_ARCH": host_arch,
                "DOCKER_CALL_LOG": str(log_file),
            })
            env.pop("WORKSHOP_PLATFORM", None)
            if platform is not None:
                env["WORKSHOP_PLATFORM"] = platform
            result = subprocess.run(
                ["bash", str(LAUNCHER), "--build"], cwd=ROOT, env=env,
                capture_output=True, text=True, timeout=15,
            )
            calls = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
            return result, calls

    def test_amd64_host_is_detected(self) -> None:
        result, calls = self.run_launcher("x86_64")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("build --platform linux/amd64", calls)
        self.assertIn("Using container platform linux/amd64", result.stdout)

    def test_arm64_host_is_detected(self) -> None:
        result, calls = self.run_launcher("aarch64")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("build --platform linux/arm64", calls)
        self.assertIn("Using container platform linux/arm64", result.stdout)

    def test_explicit_platform_override(self) -> None:
        result, calls = self.run_launcher("x86_64", "linux/arm64")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("build --platform linux/arm64", calls)

    def test_invalid_platform_is_rejected(self) -> None:
        result, calls = self.run_launcher("x86_64", "linux/ppc64le")
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be linux/amd64 or linux/arm64", result.stderr)
        self.assertNotIn("build --platform", calls)


if __name__ == "__main__":
    unittest.main()
