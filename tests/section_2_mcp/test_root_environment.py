"""The combined root .env is shared, and explicit runtime variables win."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from litreview import config

ROOT = Path(__file__).resolve().parents[2]


class RootEnvironmentTests(unittest.TestCase):
    def test_section_2_points_to_the_combined_root_env(self) -> None:
        self.assertEqual(config.ENV_FILE, ROOT / ".env")
        self.assertNotEqual(config.ENV_FILE, ROOT / "Section_2_MCP" / ".env")

    def test_root_env_loads_and_runtime_values_take_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            combined = Path(tmp)
            package = combined / "Section_2_MCP" / "litreview"
            package.mkdir(parents=True)
            shutil.copyfile(ROOT / "Section_2_MCP/litreview/config.py", package / "config.py")
            (package / "__init__.py").write_text("", encoding="utf-8")
            (combined / ".env").write_text(
                "LITREVIEW_DEFAULT_QUERY=from-root-file\nLITREVIEW_MODE=offline\n",
                encoding="utf-8",
            )
            code = (
                "import json, os, sys; "
                f"sys.path.insert(0, {str(combined / 'Section_2_MCP')!r}); "
                "from litreview import config; "
                "print(json.dumps({'env_file': str(config.ENV_FILE), "
                "'query': config.DEFAULT_QUERY, 'mode': config.MODE}))"
            )
            env = os.environ.copy()
            env["LITREVIEW_DEFAULT_QUERY"] = "from-runtime"
            result = subprocess.run(
                [sys.executable, "-c", code], env=env, text=True,
                capture_output=True, check=True, timeout=15,
            )
            values = json.loads(result.stdout)
            self.assertEqual(values["env_file"], str(combined / ".env"))
            self.assertEqual(values["query"], "from-runtime")
            self.assertEqual(values["mode"], "offline")


if __name__ == "__main__":
    unittest.main()
