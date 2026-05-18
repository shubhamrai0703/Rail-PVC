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


# Winsock needs SystemRoot to load its providers; Python's asyncio imports
# `_overlapped` at startup, which initialises Winsock. Stripping SystemRoot
# from the subprocess env causes WinError 10106 before our test code runs.
# The Linux equivalent has no such requirement.
_BASE_ENV: dict[str, str] = {"PATH": os.environ.get("PATH", "")}
if sys.platform == "win32":
    _BASE_ENV["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")


def test_engine_imports_in_clean_subprocess():
    out = subprocess.run(
        [sys.executable, "-c", "import engine; from engine import calculate_pvc; print(engine.__file__)"],
        capture_output=True, text=True, env=_BASE_ENV, check=False,
    )
    assert out.returncode == 0, f"clean import failed: {out.stderr}"
    assert "engine/__init__.py" in out.stdout or "engine\\__init__.py" in out.stdout


def test_main_app_imports_without_pythonpath():
    # Provide a dummy DATABASE_URL so module-level imports don't trip; the
    # async engine is created lazily so this is enough for import.
    env = {**_BASE_ENV, "DATABASE_URL": "postgresql://stub:stub@localhost:5432/stub"}
    out = subprocess.run(
        [sys.executable, "-c", "from main import app; print(len(app.routes))"],
        capture_output=True, text=True, env=env, check=False,
    )
    assert out.returncode == 0, f"main import failed: {out.stderr}"
    # TEST-03 (L-2 from PR #4 review): pin the route count so a forgotten
    # router include — or a stray duplicate registration — fails the test
    # rather than silently changing the surface area. 28 = the 4 P3-BF
    # endpoints + the prior 21 + /health + the FastAPI built-ins.
    assert int(out.stdout.strip()) == 28, (
        f"unexpected route count: {out.stdout.strip()} (expected 28). "
        f"If you added/removed a route, update this assertion in the same diff."
    )
