"""Local-FS shim for huawei moxing.file used during `aishipbox op run` mock mode.

Covers the documented mox.file surface from the HuaweiCloud ModelArts docs:
- listing/inspection: list_directory, exists, is_directory, get_size, stat,
  glob, walk, scan_dir
- create/write:      make_dirs, mk_dir, write, append, File
- copy/move/delete:  copy, copy_parallel, rename, remove, read

All obs:// paths are resolved to local paths under AISHIPBOX_OBS_INPUT or
AISHIPBOX_OBS_OUTPUT (see _local).
"""

from __future__ import annotations

import glob as _glob
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Tuple, Union


_OBS_PREFIX = "obs://"
_BUCKETS = {"input": "AISHIPBOX_OBS_INPUT", "output": "AISHIPBOX_OBS_OUTPUT"}


def _local(path: str) -> Path:
    if not path.startswith(_OBS_PREFIX):
        return Path(path)
    rest = path[len(_OBS_PREFIX):]
    bucket, _, rel = rest.partition("/")
    env_var = _BUCKETS.get(bucket)
    if env_var is None:
        raise ValueError(
            f"moxing_mock 只支持 obs://input/ 和 obs://output/，未识别的 bucket：obs://{bucket}/"
        )
    return Path(os.environ[env_var]) / rel


# ---- listing / inspection ---------------------------------------------------

def list_directory(path: str, recursive: bool = False) -> List[str]:
    p = _local(path)
    if not p.exists():
        return []
    if recursive:
        return sorted(str(x.relative_to(p)) for x in p.rglob("*") if x.is_file())
    return sorted(x.name for x in p.iterdir() if x.is_file())


def exists(path: str) -> bool:
    return _local(path).exists()


def is_directory(path: str) -> bool:
    return _local(path).is_dir()


def get_size(path: str, recursive: bool = False) -> int:
    p = _local(path)
    if p.is_file():
        return p.stat().st_size
    if p.is_dir():
        if not recursive:
            return 0
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return 0


@dataclass
class _Stat:
    length: int
    mtime_nsec: int
    is_directory: bool


def stat(path: str) -> _Stat:
    p = _local(path)
    st = p.stat()
    return _Stat(length=st.st_size, mtime_nsec=st.st_mtime_ns, is_directory=p.is_dir())


def glob(pattern: str) -> List[str]:
    p = _local(pattern)
    return sorted(_glob.glob(str(p)))


def walk(path: str, topdown: bool = True) -> Iterator[Tuple[str, List[str], List[str]]]:
    p = _local(path)
    yield from os.walk(p, topdown=topdown)


def scan_dir(path: str) -> Iterator[os.DirEntry]:
    p = _local(path)
    with os.scandir(p) as it:
        yield from list(it)


# ---- create / write ---------------------------------------------------------

def make_dirs(path: str) -> None:
    _local(path).mkdir(parents=True, exist_ok=True)


def mk_dir(path: str) -> None:
    _local(path).mkdir(parents=False, exist_ok=False)


def write(path: str, content: Union[str, bytes]) -> None:
    p = _local(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content)


def append(path: str, content: Union[str, bytes]) -> None:
    p = _local(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "ab" if isinstance(content, bytes) else "a"
    with open(p, mode) as f:
        f.write(content)


def File(path: str, mode: str = "r"):
    p = _local(path)
    if any(m in mode for m in ("w", "a", "x", "+")):
        p.parent.mkdir(parents=True, exist_ok=True)
    return open(p, mode)


# ---- copy / move / delete / read --------------------------------------------

def copy(src: str, dst: str) -> None:
    src_p = _local(src)
    dst_p = _local(dst)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_p, dst_p)


def copy_parallel(src: str, dst: str) -> None:
    src_p = _local(src)
    dst_p = _local(dst)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_p, dst_p, dirs_exist_ok=True)


def rename(src: str, dst: str) -> None:
    src_p = _local(src)
    dst_p = _local(dst)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dst_p))


def remove(path: str, recursive: bool = False) -> None:
    p = _local(path)
    if not p.exists():
        return
    if p.is_dir():
        if recursive:
            shutil.rmtree(p)
        else:
            p.rmdir()
    else:
        p.unlink()


def read(path: str, binary: bool = False) -> Union[str, bytes]:
    p = _local(path)
    return p.read_bytes() if binary else p.read_text()
