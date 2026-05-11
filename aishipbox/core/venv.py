"""Venv provisioning and interpreter discovery via uv."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

from aishipbox.core import strings


class VenvError(Exception):
    pass


class UvNotFound(VenvError):
    def __init__(self):
        super().__init__(strings.UV_NOT_FOUND)


def require_uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise UvNotFound()
    return uv


def python_executable(project_dir: Path) -> Path:
    project_dir = Path(project_dir)
    if platform.system() == "Windows":
        py = project_dir / ".venv" / "Scripts" / "python.exe"
    else:
        py = project_dir / ".venv" / "bin" / "python"
    if not py.exists():
        raise VenvError(f"找不到项目虚拟环境的 python：{py}")
    return py


def provision_venv(project_dir: Path, python_version: str) -> Path:
    uv = require_uv()
    venv_dir = Path(project_dir) / ".venv"
    result = subprocess.run(
        [uv, "venv", "--python", python_version, str(venv_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise VenvError(f"uv venv 失败：{result.stderr.strip()}")
    return venv_dir


def pip_install(project_dir: Path, *packages: str) -> None:
    uv = require_uv()
    result = subprocess.run(
        [uv, "pip", "install", "--python", str(python_executable(project_dir)), *packages],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise VenvError(f"uv pip install 失败：{result.stderr.strip()}")
