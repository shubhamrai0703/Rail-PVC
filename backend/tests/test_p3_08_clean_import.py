"""P3-08 regression: the backend imports cleanly from declared
dependencies — no PYTHONPATH hack, no repo-root injection.

The reviewed branch only worked when the repo root was injected via
PYTHONPATH because `engine` was a flat-layout package the wheel never
exposed. This test runs `python -c "import engine"` in a subprocess
with no extra env so a future regression (e.g. someone changing the
hatchling config) fails loudly.
"""
from __future__ import annotations

import os
import subprocess
import sys


def test_engine_imports_in_clean_subprocess():
    env = {
        "PATH": os.environ.get("PATH", ""),
        # Deliberately omit PYTHONPATH, even if the parent env has one set.
    }
    out = subprocess.run(
        [sys.executable, "-c", "import engine; from engine import calculate_pvc; print(engine.__file__)"],
        capture_output=True, text=True, env=env, check=False,
    )
    assert out.returncode == 0, f"clean import failed: {out.stderr}"
    assert "engine/__init__.py" in out.stdout


def test_main_app_imports_without_pythonpath():
    env = {
        "PATH": os.environ.get("PATH", ""),
        # Provide a dummy DATABASE_URL so module-level imports don't trip; the
        # async engine is created lazily so this is enough for import.
        "DATABASE_URL": "postgresql://stub:stub@localhost:5432/stub",
    }
    out = subprocess.run(
        [sys.executable, "-c", "from main import app; print(len(app.routes))"],
        capture_output=True, text=True, env=env, check=False,
    )
    assert out.returncode == 0, f"main import failed: {out.stderr}"
