"""algo pack: build a .tar.gz of the service for deployment."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aishipbox.core.packaging import DEFAULT_EXCLUDES, build_tar


ALGO_EXCLUDES = DEFAULT_EXCLUDES | {
    ".aishipbox.toml",
    "AGENTS.md",
    ".env.example",
    "server.py",
    "run.py",
    "pack.py",
    "test_client.py",
    "rest",
}


def execute(path: str, output: Optional[str] = None) -> int:
    service_dir = Path(path).resolve()
    if not (service_dir / "main.py").exists():
        print(f"main.py 不存在：{service_dir}")
        return 1

    out_path = Path(output) if output else Path(f"{service_dir.name}.tar.gz")
    build_tar(service_dir, out_path, excludes=ALGO_EXCLUDES, gzip=True)
    print(f"已生成：{out_path}")
    return 0
