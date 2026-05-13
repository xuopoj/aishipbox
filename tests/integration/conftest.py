"""Shared helpers for integration tests."""

import shutil
import subprocess

import pytest


def _uv_can_find(python_version: str, timeout_s: int = 10) -> bool:
    """Return True if uv can locate the requested Python version locally (no download).

    Integration tests need the hosted Python interpreters (3.9, 3.10).
    In offline environments they aren't downloadable; skip rather than hang.
    """
    if not shutil.which("uv"):
        return False
    try:
        result = subprocess.run(
            ["uv", "python", "find", python_version],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={"UV_PYTHON_DOWNLOADS": "never", "PATH": shutil.os.environ.get("PATH", "")},
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture
def require_python(request):
    def _require(version: str) -> None:
        if not _uv_can_find(version):
            pytest.skip(f"Python {version} not available locally and downloads disabled")
    return _require
