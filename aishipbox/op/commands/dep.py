"""op download: fetch a single package wheel (no transitive deps) into program_package/dependency/."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List

from aishipbox.core.config import HOSTED_RUNTIMES, PLATFORM_PRESET_PINS
from aishipbox.core.venv import VenvError, pip_install, python_executable
from aishipbox.op.manifest import ManifestError, load_manifest

_PLATFORM_TAGS = {
    "ARM": "manylinux2014_aarch64",
    "X86": "manylinux2014_x86_64",
}

_PY_VERSION_TAG = HOSTED_RUNTIMES["op"].replace(".", "")  # "3.10" -> "310"
_ABI_TAG = f"cp{_PY_VERSION_TAG}"


def _normalize(name: str) -> str:
    # PEP 503 canonical form: lowercase, runs of -_. collapsed to a single -.
    return re.sub(r"[-_.]+", "-", name).lower()


_PRESET_NAMES = {_normalize(pin.split("==")[0]) for pin in PLATFORM_PRESET_PINS}


def execute(path: str, package: str) -> int:
    project = Path(path).resolve()
    requested = _normalize(_strip_specifier(package))

    if requested in _PRESET_NAMES:
        print(f"{package} 已是平台预置依赖，不需要下载或写入 requirements.txt")
        return 1

    try:
        manifest = load_manifest(project)
        manifest.validate()
    except FileNotFoundError:
        print(f"manifest.yml 不存在：{project}")
        return 1
    except ManifestError as e:
        print(str(e))
        return 1

    if not manifest.cpu_arch:
        print("manifest.yml 的 runtime.cpu-arch 为空，无法确定下载目标平台")
        return 1

    dep_dir = project / "program_package" / "dependency"
    dep_dir.mkdir(parents=True, exist_ok=True)

    try:
        pip_install(project, "pip")
    except VenvError as e:
        print(str(e))
        return 1

    results = set()  # (canonical_name, version)
    for arch in manifest.cpu_arch:
        tag = _PLATFORM_TAGS.get(arch)
        if tag is None:
            print(f"未知 cpu-arch：{arch}")
            return 1
        try:
            results.add(_download_wheel(project, package, requested, tag, dep_dir))
        except VenvError as e:
            print(str(e))
            return 1

    versions = {v for _, v in results}
    if len(versions) > 1:
        print(f"不同 cpu-arch 解析出不同版本：{sorted(versions)}，请分开处理")
        return 1

    canonical_name, version = next(iter(results))
    _update_requirements(dep_dir / "requirements.txt", canonical_name, version)
    print(f"已下载 {canonical_name}=={version}，已写入 requirements.txt")
    return 0


def _download_wheel(project: Path, package: str, requested: str, platform_tag: str, dep_dir: Path):
    """Download one wheel; return (canonical_name, version). Idempotent: a wheel
    already present (e.g. a pure-Python wheel shared across archs, or a re-run)
    counts as success rather than a spurious 'not found'."""
    python = str(python_executable(project))
    result = subprocess.run(
        [
            python, "-m", "pip", "download", package,
            "--no-deps",
            "--dest", str(dep_dir),
            "--python-version", _PY_VERSION_TAG,
            "--implementation", "cp",
            "--abi", _ABI_TAG,
            "--platform", platform_tag,
            "--only-binary=:all:",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise VenvError(f"pip download 失败：{result.stderr.strip()}")

    matches = [
        w for w in dep_dir.glob("*.whl")
        if _normalize(w.name.split("-")[0]) == requested
    ]
    if not matches:
        raise VenvError(f"未找到下载的 wheel 文件（{platform_tag}）")
    wheel = sorted(matches)[0].name
    return _normalize(wheel.split("-")[0]), wheel.split("-")[1]


def _update_requirements(req_path: Path, name: str, version: str) -> None:
    lines: List[str] = []
    if req_path.exists():
        lines = req_path.read_text(encoding="utf-8").splitlines()

    new_line = f"{name}=={version}"
    out_lines = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and _normalize(_strip_specifier(stripped)) == name:
            out_lines.append(new_line)
            replaced = True
        else:
            out_lines.append(line)
    if not replaced:
        out_lines.append(new_line)

    req_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def _strip_specifier(requirement: str) -> str:
    for sep in ("==", ">=", "<=", "~=", "!=", ">", "<", "["):
        requirement = requirement.split(sep)[0]
    return requirement.strip()
