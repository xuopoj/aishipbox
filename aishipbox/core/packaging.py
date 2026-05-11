"""Tar/.tar.gz archive builder with exclude patterns."""

from __future__ import annotations

import fnmatch
import tarfile
from pathlib import Path
from typing import Iterable, Set


DEFAULT_EXCLUDES: Set[str] = {
    "__pycache__",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    ".git",
    ".pytest_cache",
    ".venv",
    ".env",
    "*.tar",
    "*.tar.gz",
}


def _matches(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def build_tar(
    source_dir: Path,
    output_file: Path,
    excludes: Iterable[str] = DEFAULT_EXCLUDES,
    gzip: bool = False,
) -> Path:
    source_dir = Path(source_dir).resolve()
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    mode = "w:gz" if gzip else "w:"
    excludes = set(excludes)

    with tarfile.open(output_file, mode) as tar:
        for path in sorted(source_dir.rglob("*")):
            rel = path.relative_to(source_dir)
            if any(_matches(part, excludes) for part in rel.parts):
                continue
            if _matches(path.name, excludes):
                continue
            if path.is_file():
                tar.add(path, arcname=str(rel))

    return output_file
