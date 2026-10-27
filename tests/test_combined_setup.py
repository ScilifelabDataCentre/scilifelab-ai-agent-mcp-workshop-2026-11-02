from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STARTUP = ROOT / "scripts/start_jupyter_when_ready.sh"


class CombinedSetupTests(unittest.TestCase):
    def test_strict_preflight(self) -> None:
        result = subprocess.run(
            ["python", "scripts/preflight.py", "--strict"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def run_startup(self, extra_env: dict[str, str] | None = None) -> tuple[subprocess.CompletedProcess, list[str]]:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            args_file = Path(tmp) / "jupyter-args"
            fake_python = bin_dir / "python"
            fake_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_jupyter = bin_dir / "jupyter"
            fake_jupyter.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$JUPYTER_ARGS_FILE\"\n", encoding="utf-8")
            fake_python.chmod(0o755)
            fake_jupyter.chmod(0o755)
            env = os.environ.copy()
            env.update({
                "PATH": f"{bin_dir}:{env['PATH']}",
                "JUPYTER_ARGS_FILE": str(args_file),
                "MCP_START_TIMEOUT_S": "1",
            })
            env.pop("JUPYTER_TOKEN", None)
            env.pop("WORKSHOP_LOCAL_NO_AUTH", None)
            if extra_env:
                env.update(extra_env)
            result = subprocess.run(
                ["bash", str(STARTUP)], cwd=ROOT, env=env,
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result, args_file.read_text(encoding="utf-8").splitlines()

    def test_default_authentication_generates_token(self) -> None:
        result, args = self.run_startup()
        self.assertIn("generated token in the logs", result.stdout)
        self.assertNotIn("--ServerApp.token=", args)
        self.assertNotIn("--ServerApp.password=", args)
        self.assertIn(f"--ServerApp.root_dir={ROOT}", args)

    def test_explicit_token_is_used_without_logging_it(self) -> None:
        token = secrets.token_hex(16)
        result, args = self.run_startup({"JUPYTER_TOKEN": token})
        self.assertIn(f"--ServerApp.token={token}", args)
        self.assertNotIn(token, result.stdout)
        self.assertNotIn(token, result.stderr)

    def test_individual_openllm_variables_reach_container_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            capture_file = Path(tmp) / "environment.json"
            fake_supervisord = bin_dir / "supervisord"
            fake_supervisord.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os\n"
                "with open(os.environ['ENV_CAPTURE_FILE'], 'w', encoding='utf-8') as handle:\n"
                "    json.dump({\n"
                "        'api_key_present': bool(os.environ.get('OPENLLM_API_KEY')),\n"
                "        'base_url': os.environ.get('OPENLLM_BASE_URL'),\n"
                "        'model': os.environ.get('OPENLLM_MODEL'),\n"
                "    }, handle)\n",
                encoding="utf-8",
            )
            fake_supervisord.chmod(0o755)
            env = os.environ.copy()
            env.update({
                "PATH": f"{bin_dir}:{env['PATH']}",
                "ENV_CAPTURE_FILE": str(capture_file),
                "OPENLLM_API_KEY": "dummy-test-credential",
                "OPENLLM_BASE_URL": "https://example.invalid/api",
                "OPENLLM_MODEL": "test-model",
            })
            result = subprocess.run(
                ["bash", "start-script.sh"], cwd=ROOT, env=env,
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            captured = json.loads(capture_file.read_text(encoding="utf-8"))
            self.assertEqual(captured, {
                "api_key_present": True,
                "base_url": "https://example.invalid/api",
                "model": "test-model",
            })
            self.assertNotIn("dummy-test-credential", result.stdout + result.stderr)

    def test_local_mode_is_the_only_token_free_mode(self) -> None:
        result, args = self.run_startup({"WORKSHOP_LOCAL_NO_AUTH": "1"})
        self.assertIn("Local loopback mode", result.stdout)
        self.assertIn("--ServerApp.token=", args)
        self.assertIn("--ServerApp.password=", args)


if __name__ == "__main__":
    unittest.main()
