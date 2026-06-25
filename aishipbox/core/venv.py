"""Venv provisioning and interpreter discovery via uv."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from aishipbox.core import strings


def _run_uv(cmd: List[str]) -> Tuple[int, str]:
    """Run a uv command, streaming its stderr live to the terminal while also
    capturing it. uv writes progress bars and errors to stderr; streaming keeps
    the user informed during slow downloads, capturing lets callers inspect the
    failure reason. Returns (returncode, captured_stderr)."""
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
    lines = []
    for line in proc.stderr:
        sys.stderr.write(line)
        sys.stderr.flush()
        lines.append(line)
    proc.wait()
    return proc.returncode, "".join(lines).strip()


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


_TLS_DOWNLOAD_MARKERS = (
    "invalid peer certificate",
    "UnknownIssuer",
    "Failed to download",
    "error sending request",
)


# Hosts uv reaches when downloading a managed CPython interpreter.
_INTERPRETER_DOWNLOAD_HOSTS = ("github.com", "objects.githubusercontent.com", "astral.sh")


def provision_venv(project_dir: Path, python_version: str,
                   native_tls: bool = False, insecure: bool = False) -> Path:
    uv = require_uv()
    venv_dir = Path(project_dir) / ".venv"
    cmd = [uv, "venv", "--python", python_version]
    if native_tls:
        cmd.append("--native-tls")
    if insecure:
        for host in _INTERPRETER_DOWNLOAD_HOSTS:
            cmd += ["--allow-insecure-host", host]
    cmd.append(str(venv_dir))
    returncode, detail = _run_uv(cmd)
    if returncode != 0:
        # uv's stderr already streamed live above; surface a concise summary
        # (TLS detection still inspects the captured detail).
        if not (native_tls or insecure) and any(m in detail for m in _TLS_DOWNLOAD_MARKERS):
            raise VenvError(strings.VENV_DOWNLOAD_TLS_FAILED.format(version=python_version))
        raise VenvError("uv venv 失败（详见上方 uv 输出）。")
    return venv_dir


def _module_available(project_dir: Path, module: str) -> bool:
    py = python_executable(project_dir)
    result = subprocess.run([str(py), "-c", f"import {module}"], capture_output=True)
    return result.returncode == 0


def ensure_package(project_dir: Path, module: str, pip_spec: str, note: str = "") -> None:
    """Install pip_spec into the project venv if `module` isn't importable there.
    Prints `note` once, only when an install is actually needed."""
    if _module_available(project_dir, module):
        return
    if note:
        print(note)
    pip_install(project_dir, pip_spec)


def pip_install(project_dir: Path, *packages: str) -> None:
    uv = require_uv()
    returncode, _ = _run_uv(
        [uv, "pip", "install", "--python", str(python_executable(project_dir)), *packages]
    )
    if returncode != 0:
        raise VenvError("uv pip install 失败（详见上方 uv 输出）。")
