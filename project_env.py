"""Select the repository's installed environment before third-party imports."""

import os
from pathlib import Path
import sys


def run_in_project_venv(script_file):
    environment = Path(script_file).resolve().parent / ".venv"
    if not environment.exists():
        # Preserve deployments that install dependencies in another environment.
        return
    if Path(sys.prefix).resolve() == environment.resolve():
        return
    interpreter = environment / "bin" / "python"
    if not interpreter.is_file():
        raise SystemExit("Project .venv is incomplete. Run ./install first.")
    os.execv(str(interpreter), [str(interpreter), *sys.argv])
