"""Local-FS shim for huawei moxing.file used during `aishipbox op run` mock mode."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List


_OBS_PREFIX = "obs://"


def _local(path: str) -> Path:
    if not path.startswith(_OBS_PREFIX):
        return Path(path)
    rest = path[len(_OBS_PREFIX):]
    if rest.startswith("input"):
        root = os.environ["AISHIPBOX_OBS_INPUT"]
        rel = rest[len("input"):].lstrip("/")
    elif rest.startswith("output"):
        root = os.environ["AISHIPBOX_OBS_OUTPUT"]
        rel = rest[len("output"):].lstrip("/")
    else:
        root = os.environ["AISHIPBOX_OBS_INPUT"]
        rel = rest
    return Path(root) / rel


def list_directory(path: str, recursive: bool = False) -> List[str]:
    p = _local(path)
    if not p.exists():
        return []
    if recursive:
        return sorted(str(x.relative_to(p)) for x in p.rglob("*") if x.is_file())
    return sorted(x.name for x in p.iterdir() if x.is_file())


def copy(src: str, dst: str) -> None:
    src_p = _local(src)
    dst_p = _local(dst)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_p, dst_p)


def exists(path: str) -> bool:
    return _local(path).exists()


def make_dirs(path: str) -> None:
    _local(path).mkdir(parents=True, exist_ok=True)
