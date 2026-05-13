"""op pack: package the operator into program_package/<id>.tar."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from aishipbox.core import strings
from aishipbox.core.packaging import DEFAULT_EXCLUDES, build_tar
from aishipbox.op.manifest import ManifestError, load_manifest


OP_EXCLUDES = (DEFAULT_EXCLUDES | {"obs_input", "obs_output", "AGENTS.md", ".aishipbox.toml"}) - {".env"}


def execute(path: str, output: Optional[str] = None, force: bool = False) -> int:
    project = Path(path).resolve()

    try:
        manifest = load_manifest(project)
        manifest.validate()
    except FileNotFoundError:
        print(f"manifest.yml 不存在：{project}")
        return 1
    except ManifestError as e:
        print(str(e))
        return 1

    process_py = project / "program_package" / "process.py"
    if not process_py.exists():
        print(f"program_package/process.py 不存在：{project}")
        return 1
    if "class Process" not in process_py.read_text(encoding="utf-8"):
        print("process.py 中找不到 Process 类")
        return 1

    out_path = Path(output) if output else project / "program_package" / f"{manifest.id}.tar"
    if out_path.exists() and not force:
        print(strings.PACK_OUTPUT_EXISTS.format(path=out_path))
        return 1

    with tempfile.TemporaryDirectory() as stage_str:
        stage = Path(stage_str)
        op_root = stage / manifest.id
        pkg_dir = op_root / "program_package"
        pkg_dir.mkdir(parents=True)
        for item in (project / "program_package").iterdir():
            if item.name.endswith(".tar") or item.name.endswith(".example"):
                continue
            if item.is_dir():
                shutil.copytree(item, pkg_dir / item.name)
            else:
                shutil.copy2(item, pkg_dir / item.name)
        shutil.copy2(project / "manifest.yml", op_root / "manifest.yml")

        build_tar(stage, out_path, excludes=OP_EXCLUDES, gzip=False)

    print(f"已生成：{out_path}")
    return 0
