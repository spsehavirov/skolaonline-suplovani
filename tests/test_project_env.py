"""Check interpreter selection in real subprocesses without downloading data."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectEnvironmentTests(unittest.TestCase):
    def probe(self, directory, *args):
        script = directory / "probe.py"
        script.write_text(
            f"import sys, json, os\nsys.path.insert(0, {str(ROOT)!r})\n"
            "from project_env import run_in_project_venv\n"
            "run_in_project_venv(__file__)\n"
            "print(json.dumps({'prefix': sys.prefix, 'args': sys.argv[1:], 'cwd': os.getcwd()}))\n"
        )
        return subprocess.run([sys._base_executable, str(script), *args], cwd=directory,
                              capture_output=True, text=True, timeout=30)

    def test_system_python_selects_project_venv_and_preserves_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / ".venv").symlink_to(Path(sys.prefix).resolve(), target_is_directory=True)
            args = ("--date", "15.10.2026", "--skip=1-3:2-4")
            result = self.probe(directory, *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(Path(data["prefix"]).resolve(), Path(sys.prefix).resolve())
            self.assertEqual(data["args"], list(args))
            self.assertEqual(Path(data["cwd"]).resolve(), directory.resolve())

    def test_existing_installation_without_project_venv_keeps_interpreter(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.probe(Path(folder))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(json.loads(result.stdout)["prefix"]).resolve(), Path(sys.base_prefix).resolve())

    def test_incomplete_project_venv_gives_install_hint(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / ".venv").mkdir()
            result = self.probe(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Run ./install", result.stderr)

    def test_entrypoints_help_works_outside_venv(self):
        for script in ("so_soap.py", "so_download.py", "suplovani.py"):
            with self.subTest(script=script):
                result = subprocess.run([sys._base_executable, str(ROOT / script), "--help"],
                                        cwd=ROOT, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)


if __name__ == "__main__":
    unittest.main()
