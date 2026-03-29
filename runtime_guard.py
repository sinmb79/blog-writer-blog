"""
Lightweight runtime helpers for the standalone blog app.
"""
from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"


def project_python_path() -> Path:
    return Path(sys.executable)


def missing_distributions(distributions: list[str]) -> list[str]:
    missing: list[str] = []
    for name in distributions:
        try:
            importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
    return missing


def ensure_project_runtime(
    entrypoint: str,
    required_distributions: list[str] | None = None,
) -> None:
    missing = missing_distributions(required_distributions or [])
    if missing:
        raise RuntimeError(
            f"{entrypoint} is missing required packages: {', '.join(missing)}.\n"
            f"Install them with: {project_python_path()} -m pip install -r {REQUIREMENTS_FILE}"
        )


def run_with_project_python(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    cmd = [str(project_python_path()), *args]
    return subprocess.run(cmd, **kwargs)


def project_python_cmd(args: list[str]) -> list[str]:
    return [str(project_python_path()), *args]
