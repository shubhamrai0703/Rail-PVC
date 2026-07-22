"""Regression coverage for cwd-independent backend dotenv loading."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_main_loads_dotenv_relative_to_backend_directory() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"
    script = f"""
import dotenv
import sys

loaded_paths = []
dotenv.load_dotenv = lambda dotenv_path=None, **kwargs: loaded_paths.append(dotenv_path)
sys.path.insert(0, {str(backend_dir)!r})

import main  # noqa: F401

print(loaded_paths[0])
"""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "DATABASE_URL": "postgresql://stub:stub@localhost:5432/stub",
    }
    if sys.platform == "win32":
        env["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == backend_dir / ".env"


def test_alembic_loads_dotenv_relative_to_backend_directory() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"
    migration_env = backend_dir / "migrations" / "env.py"
    script = f"""
from contextlib import nullcontext
import os
import runpy
from types import SimpleNamespace

import dotenv
from alembic import context

loaded_calls = []
dotenv.load_dotenv = lambda dotenv_path=None, **kwargs: loaded_calls.append((dotenv_path, kwargs))
context.config = SimpleNamespace(config_file_name=None)
context.is_offline_mode = lambda: True
context.configure = lambda **kwargs: None
context.begin_transaction = nullcontext
context.run_migrations = lambda: None
os.environ["DATABASE_URL"] = "postgresql://stub:stub@localhost:5432/stub"

runpy.run_path({str(migration_env)!r}, run_name="migration_env_under_test")

print(loaded_calls[0][0])
print(loaded_calls[0][1].get("override"))
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env={"PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    loaded_path, override = result.stdout.splitlines()
    assert Path(loaded_path) == backend_dir / ".env"
    assert override == "True"
