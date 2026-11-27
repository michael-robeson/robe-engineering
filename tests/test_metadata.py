from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eng_lifecycle.config import LifecycleError
from eng_lifecycle.metadata import check, parse_config, render_badge


class MetadataTest(unittest.TestCase):
    def test_badge_uses_full_declared_python_constraint(self) -> None:
        badge = json.loads(render_badge(
            '[project]\nrequires-python = ">=3.12,<3.15"\n', "pyproject.toml"
        ))
        self.assertEqual(badge["message"], ">=3.12,<3.15")
        with self.assertRaises(LifecycleError):
            render_badge('[project]\nname = "example"\n', "pyproject.toml")

    def test_check_reports_drift_without_mutating_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github").mkdir()
            (root / ".github/repository-metadata.json").write_text(json.dumps({
                "schema": 1,
                "badges": [{
                    "adapter": "python-requires",
                    "source": "pyproject.toml",
                    "output": "badge.json",
                }],
            }), encoding="utf-8")
            (root / "pyproject.toml").write_text(
                '[project]\nrequires-python = ">=3.12"\n', encoding="utf-8"
            )
            output = root / "badge.json"
            output.write_text("stale\n", encoding="utf-8")
            with self.assertRaisesRegex(LifecycleError, "out of date"):
                check(root)
            self.assertEqual(output.read_text(encoding="utf-8"), "stale\n")
            output.write_text(render_badge(
                '[project]\nrequires-python = ">=3.12"\n', "pyproject.toml"
            ), encoding="utf-8")
            check(root)

    def test_invalid_adapters_and_unsafe_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            badge = {"adapter": "future", "source": "pyproject.toml", "output": "badge.json"}
            with self.assertRaisesRegex(LifecycleError, "Unsupported"):
                parse_config(root, json.dumps({"schema": 1, "badges": [badge]}))
            badge["adapter"] = "python-requires"
            badge["output"] = "../badge.json"
            with self.assertRaisesRegex(LifecycleError, "Invalid metadata path"):
                parse_config(root, json.dumps({"schema": 1, "badges": [badge]}))
            (root / "link").symlink_to(root, target_is_directory=True)
            badge["output"] = "link/badge.json"
            with self.assertRaisesRegex(LifecycleError, "symlink"):
                parse_config(root, json.dumps({"schema": 1, "badges": [badge]}))


if __name__ == "__main__":
    unittest.main()
