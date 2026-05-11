# aishipbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single Python CLI `aishipbox` that supports `new / run / debug / pack` for two project types — MAS algorithm services (`algo`) and PanguLM custom operators (`op`) — with Chinese UI, per-project venvs via `uv`, and AGENTS.md generated into every new project.

**Architecture:** Parallel subpackages (`aishipbox/algo/`, `aishipbox/op/`) on top of a shared `aishipbox/core/`. Absorb mas-algo-cli's source into `aishipbox/algo/`; build `op/` from scratch on top of the same core. Distributed via PyPI; users install with `uv tool install aishipbox`.

**Tech Stack:** Python 3.10+, hatchling build backend, `questionary` (TUI), `pyyaml` (manifest), `tomli`/`tomllib` (.aishipbox.toml), `debugpy` (debug mode), `uv` (venv provisioning). Tests: `pytest`.

**Spec:** `docs/superpowers/specs/2026-05-11-aishipbox-design.md`

**Source for absorb:** `resources/mas-algo-cli/` (existing PyPI package, MIT licensed).

---

## Phase 0: Project skeleton & tooling

### Task 0.1: Restructure repo and configure pyproject

**Files:**
- Modify: `pyproject.toml`
- Create: `aishipbox/__init__.py`
- Create: `aishipbox/__main__.py`
- Create: `aishipbox/cli.py`
- Delete: `main.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`

- [ ] **Step 1: Replace pyproject.toml**

```toml
[project]
name = "aishipbox"
version = "0.1.0"
description = "JAC PanguLM 算法服务与自定义算子开发 CLI"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
    "questionary>=2.0.0",
    "pyyaml>=6.0",
    "debugpy>=1.8.0",
    "tomli>=2.0.0; python_version < '3.11'",
]

[project.scripts]
aishipbox = "aishipbox.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["aishipbox"]

[tool.hatch.build.targets.wheel.force-include]
"aishipbox/algo/templates" = "aishipbox/algo/templates"
"aishipbox/algo/stubs"     = "aishipbox/algo/stubs"
"aishipbox/op/templates"   = "aishipbox/op/templates"
"aishipbox/op/moxing_mock" = "aishipbox/op/moxing_mock"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.10",
]
```

- [ ] **Step 2: Remove the placeholder main.py and create package skeleton**

```bash
rm main.py
mkdir -p aishipbox tests
```

Write `aishipbox/__init__.py`:
```python
"""aishipbox CLI package."""

__version__ = "0.1.0"
```

Write `aishipbox/__main__.py`:
```python
from aishipbox.cli import main

if __name__ == "__main__":
    main()
```

Write `aishipbox/cli.py` (minimal stub — fleshed out in Task 1.7):
```python
"""aishipbox CLI entry point."""

import sys


def main() -> int:
    print("aishipbox CLI 尚未实现", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Create test infra**

`tests/__init__.py`: empty file.

`tests/conftest.py`:
```python
"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def tmp_project_dir(tmp_path):
    """A fresh tmp directory for filesystem tests."""
    return tmp_path
```

- [ ] **Step 4: Add .gitignore**

```gitignore
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.pytest_cache/
.venv/
.env
*.tar.gz
*.tar
dist/
build/
.coverage
.DS_Store
```

- [ ] **Step 5: Sync deps and smoke test**

```bash
uv sync
uv run python -c "import aishipbox; print(aishipbox.__version__)"
```

Expected: `0.1.0`

```bash
uv run aishipbox
```

Expected: prints `aishipbox CLI 尚未实现` to stderr, exits 1.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml aishipbox/ tests/ .gitignore
git rm main.py
git commit -m "feat: scaffold aishipbox package layout"
```

---

## Phase 1: Core infrastructure

### Task 1.1: Chinese string constants

**Files:**
- Create: `aishipbox/core/__init__.py`
- Create: `aishipbox/core/strings.py`
- Test: `tests/core/test_strings.py`

- [ ] **Step 1: Create core package init**

`aishipbox/core/__init__.py`: empty.

`mkdir -p tests/core` and `tests/core/__init__.py`: empty.

- [ ] **Step 2: Write the failing test**

`tests/core/test_strings.py`:
```python
from aishipbox.core import strings


def test_required_keys_exist():
    required = [
        "UV_NOT_FOUND",
        "PROJECT_NOT_FOUND",
        "PROJECT_TYPE_MISMATCH",
        "TARGET_DIR_EXISTS",
        "MISSING_FLAGS_FOR_YES",
        "MANIFEST_INVALID",
        "OBS_CREDS_MISSING",
        "PACK_OUTPUT_EXISTS",
        "UNEXPECTED_ERROR",
        "NEXT_STEPS_HEADER",
    ]
    for key in required:
        assert hasattr(strings, key), f"missing string {key}"
        assert isinstance(getattr(strings, key), str)


def test_strings_are_chinese():
    """Spot-check that strings contain at least one CJK character."""
    sample = strings.UV_NOT_FOUND
    assert any("一" <= ch <= "鿿" for ch in sample), (
        f"expected Chinese characters in: {sample}"
    )
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/core/test_strings.py -v
```

Expected: FAIL (`AttributeError: module 'aishipbox.core' has no attribute 'strings'` or similar).

- [ ] **Step 4: Implement strings module**

`aishipbox/core/strings.py`:
```python
"""User-facing strings (Chinese). Single source for future i18n."""

UV_NOT_FOUND = "未找到 uv 命令，请先安装 uv：https://github.com/astral-sh/uv"
PROJECT_NOT_FOUND = "当前目录不是 aishipbox 项目（找不到 .aishipbox.toml）。请先运行 `aishipbox <op|algo> new`。"
PROJECT_TYPE_MISMATCH = "项目类型不匹配：检测到 {detected}，但当前命令需要 {expected}。"
TARGET_DIR_EXISTS = "目标目录已存在：{path}"
MISSING_FLAGS_FOR_YES = "使用 --yes 时缺少以下字段：{fields}"
MANIFEST_INVALID = "manifest.yml 校验失败："
OBS_CREDS_MISSING = "缺少 OBS 配置，请在 .env 中设置：{fields}"
PACK_OUTPUT_EXISTS = "输出文件已存在：{path}，使用 --force 覆盖。"
UNEXPECTED_ERROR = "发生未预期错误，设置 AISHIPBOX_DEBUG=1 查看完整堆栈。"
NEXT_STEPS_HEADER = "后续步骤："

# Algo
ALGO_TEMPLATE_BASIC = "basic   - 最简服务骨架"
ALGO_TEMPLATE_PREDICT = "predict - 预测/机器学习（pandas）"
ALGO_TEMPLATE_CV = "cv      - 计算机视觉（OpenCV/Pillow）"
ALGO_SELECT_TEMPLATE = "请选择模板："

# Op wizard
OP_WIZARD_TITLE = "新建自定义算子"
OP_FIELD_ID = "算子 ID"
OP_FIELD_NAME = "算子名称"
OP_FIELD_DESCRIPTION = "算子描述"
OP_FIELD_AUTHOR = "作者"
OP_FIELD_VERSION = "版本（x.y.z）"
OP_FIELD_CATEGORY = "类别（可多选）"
OP_FIELD_MODAL = "数据模态（可多选）"
OP_FIELD_FORMAT = "数据格式（如 JPG, PNG）"
OP_FIELD_LANGUAGE = "语言标签"
OP_FIELD_CPU_ARCH = "CPU 架构"
OP_FIELD_CPU = "CPU 核数"
OP_FIELD_MEMORY = "内存 (MB)"
OP_FIELD_NPU = "NPU 数量"
OP_FIELD_AUTO_DATA_LOADING = "是否自动加载数据"
OP_FIELD_SKELETON = "代码骨架"
OP_SKELETON_BLANK = "blank      - 空白骨架"
OP_SKELETON_TRANSFORM = "transform  - 含 moxing 数据转换示例"

OP_CATEGORIES = ["数据提取", "数据抽样", "数据转换", "数据过滤", "数据去重", "数据打标", "其他"]
OP_MODALS = ["TEXT", "IMAGE", "VIDEO", "AUDIO", "OTHER"]
OP_CPU_ARCHES = ["arm", "x86"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/core/test_strings.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add aishipbox/core/ tests/core/
git commit -m "feat(core): Chinese user-facing strings module"
```

---

### Task 1.2: ProjectConfig (.aishipbox.toml read/write)

**Files:**
- Create: `aishipbox/core/config.py`
- Test: `tests/core/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/core/test_config.py`:
```python
import pytest
from pathlib import Path

from aishipbox.core.config import (
    HOSTED_RUNTIMES,
    SCHEMA_VERSION,
    ProjectConfig,
    find_project_root,
    write_project_config,
)


def test_hosted_runtimes_defined():
    assert HOSTED_RUNTIMES["algo"] == "3.9"
    assert HOSTED_RUNTIMES["op"] == "3.10"


def test_write_and_read_roundtrip(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="op", runtime="3.10"))

    config_file = tmp_path / ".aishipbox.toml"
    assert config_file.exists()

    loaded = ProjectConfig.from_path(tmp_path)
    assert loaded.type == "op"
    assert loaded.runtime == "3.10"
    assert loaded.schema_version == SCHEMA_VERSION


def test_find_project_root_walks_up(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)

    assert find_project_root(nested) == tmp_path


def test_find_project_root_returns_none_when_missing(tmp_path):
    assert find_project_root(tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/test_config.py -v
```

Expected: FAIL (module not found).

- [ ] **Step 3: Implement config module**

`aishipbox/core/config.py`:
```python
"""Project-level and tool-level configuration."""

from __future__ import annotations

import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


HOSTED_RUNTIMES = {
    "algo": "3.9",
    "op": "3.10",
}

SCHEMA_VERSION = 1

CONFIG_FILENAME = ".aishipbox.toml"


@dataclass
class ProjectConfig:
    type: str            # "algo" or "op"
    runtime: str         # "3.9", "3.10", ...
    schema_version: int = SCHEMA_VERSION
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    @classmethod
    def from_path(cls, project_dir: Path) -> "ProjectConfig":
        with open(Path(project_dir) / CONFIG_FILENAME, "rb") as f:
            data = tomllib.load(f)
        return cls(**data)


def write_project_config(project_dir: Path, config: ProjectConfig) -> Path:
    target = Path(project_dir) / CONFIG_FILENAME
    target.write_text(_render_toml(config), encoding="utf-8")
    return target


def find_project_root(start: Path) -> Optional[Path]:
    cur = Path(start).resolve()
    while True:
        if (cur / CONFIG_FILENAME).exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def _render_toml(config: ProjectConfig) -> str:
    d = asdict(config)
    lines = [
        f'schema_version = {d["schema_version"]}',
        f'type = "{d["type"]}"',
        f'runtime = "{d["runtime"]}"',
        f'created_at = "{d["created_at"]}"',
        "",
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/test_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add aishipbox/core/config.py tests/core/test_config.py
git commit -m "feat(core): ProjectConfig + .aishipbox.toml read/write"
```

---

### Task 1.3: .env loader

**Files:**
- Create: `aishipbox/core/env.py`
- Test: `tests/core/test_env.py`

- [ ] **Step 1: Write the failing test**

`tests/core/test_env.py`:
```python
from aishipbox.core.env import load_env_file


def test_load_basic(tmp_path):
    env = tmp_path / ".env"
    env.write_text("FOO=bar\nBAZ=qux\n")
    assert load_env_file(env) == {"FOO": "bar", "BAZ": "qux"}


def test_load_skips_comments_and_blanks(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\n\nFOO=bar\n  # indented comment\nBAZ=qux\n")
    assert load_env_file(env) == {"FOO": "bar", "BAZ": "qux"}


def test_load_strips_quotes(tmp_path):
    env = tmp_path / ".env"
    env.write_text('FOO="bar baz"\nQ=\'single\'\n')
    assert load_env_file(env) == {"FOO": "bar baz", "Q": "single"}


def test_load_missing_returns_empty(tmp_path):
    assert load_env_file(tmp_path / ".env") == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/test_env.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement env module**

`aishipbox/core/env.py`:
```python
"""Minimal .env loader (no python-dotenv dependency)."""

from pathlib import Path
from typing import Dict


def load_env_file(path: Path) -> Dict[str, str]:
    path = Path(path)
    if not path.exists():
        return {}

    result: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[key] = value
    return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/test_env.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add aishipbox/core/env.py tests/core/test_env.py
git commit -m "feat(core): minimal .env file loader"
```

---

### Task 1.4: venv provisioning

**Files:**
- Create: `aishipbox/core/venv.py`
- Test: `tests/core/test_venv.py`

- [ ] **Step 1: Write the failing test**

`tests/core/test_venv.py`:
```python
import subprocess
import pytest

from aishipbox.core import venv as venv_mod


def test_python_executable_for_existing_venv(tmp_path):
    venv_dir = tmp_path / ".venv"
    (venv_dir / "bin").mkdir(parents=True)
    py = venv_dir / "bin" / "python"
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)
    assert venv_mod.python_executable(tmp_path) == py


def test_python_executable_missing_raises(tmp_path):
    with pytest.raises(venv_mod.VenvError):
        venv_mod.python_executable(tmp_path)


def test_uv_required_raises_when_missing(monkeypatch):
    monkeypatch.setattr(venv_mod.shutil, "which", lambda name: None)
    with pytest.raises(venv_mod.UvNotFound):
        venv_mod.require_uv()


def test_provision_calls_uv(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0
        return R()

    monkeypatch.setattr(venv_mod.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(venv_mod, "subprocess", subprocess)

    venv_mod.provision_venv(tmp_path, "3.10")

    assert calls[0][:5] == ["/usr/bin/uv", "venv", "--python", "3.10", str(tmp_path / ".venv")]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/test_venv.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement venv module**

`aishipbox/core/venv.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/test_venv.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add aishipbox/core/venv.py tests/core/test_venv.py
git commit -m "feat(core): venv provisioning via uv"
```

---

### Task 1.5: Tar packaging helper

**Files:**
- Create: `aishipbox/core/packaging.py`
- Test: `tests/core/test_packaging.py`

- [ ] **Step 1: Write the failing test**

`tests/core/test_packaging.py`:
```python
import tarfile
from pathlib import Path

from aishipbox.core.packaging import build_tar, DEFAULT_EXCLUDES


def test_build_tar_basic(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("print('a')")
    (src / "b.py").write_text("print('b')")

    out = tmp_path / "out.tar"
    build_tar(src, out, excludes=DEFAULT_EXCLUDES, gzip=False)

    with tarfile.open(out, "r:") as tar:
        names = sorted(tar.getnames())
    assert names == ["a.py", "b.py"]


def test_build_tar_gzip(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("a")

    out = tmp_path / "out.tar.gz"
    build_tar(src, out, excludes=DEFAULT_EXCLUDES, gzip=True)

    with tarfile.open(out, "r:gz") as tar:
        assert tar.getnames() == ["a.py"]


def test_build_tar_respects_excludes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("a")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "x.pyc").write_text("")
    (src / ".DS_Store").write_text("")

    out = tmp_path / "out.tar"
    build_tar(src, out, excludes=DEFAULT_EXCLUDES, gzip=False)

    with tarfile.open(out, "r:") as tar:
        names = tar.getnames()
    assert "a.py" in names
    assert not any("__pycache__" in n for n in names)
    assert ".DS_Store" not in names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/test_packaging.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement packaging module**

`aishipbox/core/packaging.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/test_packaging.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add aishipbox/core/packaging.py tests/core/test_packaging.py
git commit -m "feat(core): tar/tar.gz builder with exclude patterns"
```

---

### Task 1.6: UI helpers (questionary wrappers + flag resolver)

**Files:**
- Create: `aishipbox/core/ui.py`
- Test: `tests/core/test_ui.py`

- [ ] **Step 1: Write the failing test**

`tests/core/test_ui.py`:
```python
import pytest

from aishipbox.core.ui import resolve_fields, MissingFieldsError


def test_resolve_fields_all_provided():
    spec = {"id": str, "cpu": int}
    result = resolve_fields(spec, flags={"id": "abc", "cpu": "2"}, yes=True)
    assert result == {"id": "abc", "cpu": 2}


def test_resolve_fields_missing_required_raises():
    spec = {"id": str, "cpu": int}
    with pytest.raises(MissingFieldsError) as exc:
        resolve_fields(spec, flags={"id": "abc"}, yes=True)
    assert "cpu" in exc.value.fields


def test_resolve_fields_uses_defaults_when_yes(monkeypatch):
    spec = {"id": str, "cpu": (int, 1)}  # (type, default)
    result = resolve_fields(spec, flags={"id": "abc"}, yes=True)
    assert result == {"id": "abc", "cpu": 1}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/test_ui.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement ui module**

`aishipbox/core/ui.py`:
```python
"""TUI helpers via questionary plus a non-interactive field resolver."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import questionary

from aishipbox.core import strings


FieldSpec = Union[type, Tuple[type, Any]]
SpecDict = Dict[str, FieldSpec]


class MissingFieldsError(Exception):
    def __init__(self, fields: List[str]):
        self.fields = fields
        super().__init__(strings.MISSING_FLAGS_FOR_YES.format(fields=", ".join(fields)))


def _unpack(spec: FieldSpec):
    if isinstance(spec, tuple):
        return spec
    return (spec, None)


def resolve_fields(
    spec: SpecDict,
    flags: Dict[str, str],
    yes: bool,
) -> Dict[str, Any]:
    """Resolve fields from flags. If yes=True, missing-required fields raise."""
    result: Dict[str, Any] = {}
    missing: List[str] = []
    for name, fspec in spec.items():
        ftype, default = _unpack(fspec)
        if name in flags and flags[name] is not None:
            result[name] = ftype(flags[name])
        elif default is not None:
            result[name] = default
        else:
            if yes:
                missing.append(name)
            # else: caller will prompt interactively for this field
    if missing:
        raise MissingFieldsError(missing)
    return result


def ask_text(message: str, default: Optional[str] = None) -> str:
    return questionary.text(message, default=default or "").ask()


def ask_select(message: str, choices: List[str], default: Optional[str] = None) -> str:
    return questionary.select(message, choices=choices, default=default).ask()


def ask_checkbox(message: str, choices: List[str]) -> List[str]:
    return questionary.checkbox(message, choices=choices).ask()


def ask_confirm(message: str, default: bool = False) -> bool:
    return questionary.confirm(message, default=default).ask()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/test_ui.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add aishipbox/core/ui.py tests/core/test_ui.py
git commit -m "feat(core): UI helpers (questionary + flag resolver)"
```

---

### Task 1.7: CLI dispatch skeleton

**Files:**
- Modify: `aishipbox/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
import subprocess
import sys
import pytest

from aishipbox.cli import main


def test_no_args_prints_help(capsys):
    with pytest.raises(SystemExit):
        main([])
    captured = capsys.readouterr()
    assert "aishipbox" in captured.out.lower() or "aishipbox" in captured.err.lower()


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "0.1.0" in captured.out


def test_algo_subcommand_routes(monkeypatch):
    called = {}

    def fake_dispatch(argv):
        called["algo"] = argv
        return 0

    monkeypatch.setattr("aishipbox.algo.dispatch", fake_dispatch, raising=False)
    rc = main(["algo", "new", "x"])
    assert rc == 0
    assert called["algo"] == ["new", "x"]


def test_op_subcommand_routes(monkeypatch):
    called = {}

    def fake_dispatch(argv):
        called["op"] = argv
        return 0

    monkeypatch.setattr("aishipbox.op.dispatch", fake_dispatch, raising=False)
    rc = main(["op", "new", "y"])
    assert rc == 0
    assert called["op"] == ["new", "y"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement cli module + algo/op dispatch stubs**

`aishipbox/cli.py`:
```python
"""aishipbox CLI entry point — dispatch to algo or op subcommand groups."""

from __future__ import annotations

import sys
from typing import List, Optional

from aishipbox import __version__


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)

    if not argv:
        _print_usage()
        sys.exit(2)

    first = argv[0]
    if first in ("-h", "--help"):
        _print_usage()
        sys.exit(0)

    if first in ("-v", "--version"):
        print(f"aishipbox {__version__}")
        sys.exit(0)

    if first == "algo":
        from aishipbox import algo
        return algo.dispatch(argv[1:])
    if first == "op":
        from aishipbox import op
        return op.dispatch(argv[1:])

    print(f"未知子命令：{first}", file=sys.stderr)
    _print_usage(file=sys.stderr)
    return 2


def _print_usage(file=sys.stdout) -> None:
    print(
        "aishipbox - JAC PanguLM 算法服务与自定义算子开发 CLI\n\n"
        "用法：\n"
        "  aishipbox algo <命令> [参数...]     管理算法服务项目\n"
        "  aishipbox op   <命令> [参数...]     管理自定义算子项目\n"
        "  aishipbox --version                 显示版本\n"
        "  aishipbox --help                    显示此帮助\n",
        file=file,
    )


if __name__ == "__main__":
    sys.exit(main())
```

Create `aishipbox/algo/__init__.py`:
```python
"""algo subcommand group."""

from typing import List


def dispatch(argv: List[str]) -> int:
    raise NotImplementedError("algo dispatch implemented in Task 2.10")
```

Create `aishipbox/op/__init__.py`:
```python
"""op subcommand group."""

from typing import List


def dispatch(argv: List[str]) -> int:
    raise NotImplementedError("op dispatch implemented in Task 3.10")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Smoke test**

```bash
uv run aishipbox --version
```
Expected: `aishipbox 0.1.0`

```bash
uv run aishipbox
```
Expected: usage text, exit 2.

- [ ] **Step 6: Commit**

```bash
git add aishipbox/cli.py aishipbox/algo/__init__.py aishipbox/op/__init__.py tests/test_cli.py
git commit -m "feat(cli): top-level dispatch routing to algo/op"
```

---

## Phase 2: Absorb mas-algo-cli into algo/

The source of truth for absorbed code is `resources/mas-algo-cli/mas_algo_cli/`. We copy file-by-file and adapt:

- replace `from . import` / `from .commands import` with paths under `aishipbox.algo`
- swap any hard-coded English UI strings for `aishipbox.core.strings` lookups (or new Chinese strings)
- replace workspace-shared venv logic (using `sys.executable`) with per-project venv (`aishipbox.core.venv.python_executable`)
- add writing of `.aishipbox.toml` + `AGENTS.md` to `new.py`

### Task 2.1: Copy algo templates verbatim and add AGENTS.md template

**Files:**
- Create: `aishipbox/algo/templates/__init__.py`
- Create: `aishipbox/algo/templates/{basic,predict,cv}/...` (verbatim from resources)
- Create: `aishipbox/algo/templates/AGENTS.md.tmpl`

- [ ] **Step 1: Copy templates**

```bash
mkdir -p aishipbox/algo/templates
cp -r resources/mas-algo-cli/mas_algo_cli/templates/* aishipbox/algo/templates/
```

Verify:
```bash
ls aishipbox/algo/templates/
```
Expected: `__init__.py basic cv predict`

- [ ] **Step 2: Add Chinese AGENTS.md template**

`aishipbox/algo/templates/AGENTS.md.tmpl`:
```markdown
# AGENTS.md

本项目类型：MAS 算法服务（algo）
托管运行时：Python 3.9
工具：aishipbox v${aishipbox_version}

## 入口
- main.py 中的 `AlgoProcessor` 类

## 常用命令
- 本地运行：    aishipbox algo run
- 启动调试：    aishipbox algo run --debug   （需配合 VS Code "Attach to Algo Service"）
- 打包：        aishipbox algo pack
- 安装托管依赖：aishipbox algo install-deps

## 关键约束
- 部署到 MAS 托管服务，结构遵循 main.py + requirements.txt + dependency/。
- requirements.txt 中可引用 dependency/ 下的离线 wheel。
- 不要修改 .aishipbox.toml 的 schema_version 与 type 字段。

## 平台参考
- 算法手册：参见 MAS 文档
```

- [ ] **Step 3: Commit**

```bash
git add aishipbox/algo/templates/
git commit -m "feat(algo): import mas-algo-cli templates + AGENTS.md template"
```

---

### Task 2.2: Copy algo stubs and runner verbatim

**Files:**
- Create: `aishipbox/algo/stubs/` (verbatim from resources)
- Create: `aishipbox/algo/runner.py` (verbatim from resources)

- [ ] **Step 1: Copy stubs and runner**

```bash
cp -r resources/mas-algo-cli/mas_algo_cli/stubs aishipbox/algo/stubs
cp resources/mas-algo-cli/mas_algo_cli/runner.py aishipbox/algo/runner.py
```

- [ ] **Step 2: Smoke test imports**

```bash
uv run python -c "from aishipbox.algo import runner; print(runner.__file__)"
```
Expected: prints path inside `aishipbox/algo/runner.py`, no errors.

- [ ] **Step 3: Commit**

```bash
git add aishipbox/algo/stubs/ aishipbox/algo/runner.py
git commit -m "feat(algo): import mas-algo-cli stubs and runner"
```

---

### Task 2.3: Port algo `new` command with per-project venv + AGENTS.md + .aishipbox.toml

**Files:**
- Create: `aishipbox/algo/commands/__init__.py`
- Create: `aishipbox/algo/commands/new.py`
- Test: `tests/algo/test_new.py`

- [ ] **Step 1: Create commands package**

`aishipbox/algo/commands/__init__.py`: empty.
`mkdir -p tests/algo` and `tests/algo/__init__.py`: empty.

- [ ] **Step 2: Write the failing test**

`tests/algo/test_new.py`:
```python
import pytest
from aishipbox.algo.commands import new as new_cmd


def test_rejects_hyphen_in_name(tmp_path, capsys):
    rc = new_cmd.execute("my-algo", str(tmp_path), template="basic", yes=True)
    assert rc == 1


def test_rejects_existing_dir(tmp_path):
    (tmp_path / "my_algo").mkdir()
    rc = new_cmd.execute("my_algo", str(tmp_path), template="basic", yes=True)
    assert rc == 1


def test_scaffolds_files(tmp_path, monkeypatch):
    # Avoid actually provisioning a venv during tests
    monkeypatch.setattr("aishipbox.algo.commands.new._provision_and_install", lambda *a, **k: None)

    rc = new_cmd.execute("my_algo", str(tmp_path), template="basic", yes=True)
    assert rc == 0

    project = tmp_path / "my_algo"
    assert (project / "main.py").exists()
    assert (project / "requirements.txt").exists()
    assert (project / ".aishipbox.toml").exists()
    assert (project / "AGENTS.md").exists()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/algo/test_new.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement algo new**

`aishipbox/algo/commands/new.py`:
```python
"""algo new: create a new algorithm service project."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from string import Template
from typing import Optional

from aishipbox import __version__
from aishipbox.core import strings
from aishipbox.core.config import HOSTED_RUNTIMES, ProjectConfig, write_project_config
from aishipbox.core.venv import provision_venv, pip_install


TEMPLATES = ("basic", "predict", "cv")
TEMPLATE_DEPS = {
    "basic": ["requests"],
    "predict": ["pandas", "requests"],
    "cv": ["opencv-python", "numpy", "requests"],
}


def execute(name: str, parent_dir: str, template: Optional[str] = None, yes: bool = False) -> int:
    if "-" in name:
        print(f"项目名不允许包含连字符：{name}，请改用下划线 {name.replace('-', '_')}")
        return 1

    parent = Path(parent_dir).resolve()
    project_dir = parent / name
    if project_dir.exists():
        print(strings.TARGET_DIR_EXISTS.format(path=project_dir))
        return 1

    if template is None:
        if yes:
            template = "basic"
        else:
            template = _prompt_template()
    if template not in TEMPLATES:
        print(f"未知模板：{template}")
        return 1

    project_dir.mkdir(parents=True)

    template_pkg = resources.files(f"aishipbox.algo.templates.{template}")
    for item in template_pkg.iterdir():
        if item.is_file():
            content = item.read_text(encoding="utf-8").replace("${name}", name)
            (project_dir / item.name).write_text(content, encoding="utf-8")

    # AGENTS.md (Chinese)
    agents_tmpl = resources.files("aishipbox.algo.templates").joinpath("AGENTS.md.tmpl").read_text(encoding="utf-8")
    (project_dir / "AGENTS.md").write_text(
        Template(agents_tmpl).safe_substitute(aishipbox_version=__version__),
        encoding="utf-8",
    )

    # Marker
    write_project_config(project_dir, ProjectConfig(type="algo", runtime=HOSTED_RUNTIMES["algo"]))

    _provision_and_install(project_dir, template)

    print(f"\n项目已创建：{project_dir}")
    print(f"\n{strings.NEXT_STEPS_HEADER}")
    print(f"  1. cd {name}")
    print(f"  2. cp .env.example .env  # 如存在")
    print(f"  3. 编辑 main.py 实现算法")
    print(f"  4. aishipbox algo run")
    print(f"  5. aishipbox algo pack")
    return 0


def _prompt_template() -> str:
    print(strings.ALGO_SELECT_TEMPLATE)
    print(f"  1. {strings.ALGO_TEMPLATE_BASIC}")
    print(f"  2. {strings.ALGO_TEMPLATE_PREDICT}")
    print(f"  3. {strings.ALGO_TEMPLATE_CV}")
    while True:
        choice = input("请输入编号或名称 [1]：").strip() or "1"
        mapping = {"1": "basic", "2": "predict", "3": "cv",
                   "basic": "basic", "predict": "predict", "cv": "cv"}
        if choice in mapping:
            return mapping[choice]
        print(f"无效选择：{choice}")


def _provision_and_install(project_dir: Path, template: str) -> None:
    provision_venv(project_dir, HOSTED_RUNTIMES["algo"])
    deps = TEMPLATE_DEPS.get(template, [])
    if deps:
        pip_install(project_dir, *deps)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/algo/test_new.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add aishipbox/algo/commands/ tests/algo/test_new.py
git commit -m "feat(algo): port new command with per-project venv + AGENTS.md"
```

---

### Task 2.4: Port algo `run` command using per-project venv

**Files:**
- Create: `aishipbox/algo/commands/run.py`
- Test: `tests/algo/test_run.py`

- [ ] **Step 1: Write the failing test**

`tests/algo/test_run.py`:
```python
from pathlib import Path

from aishipbox.algo.commands import run as run_cmd
from aishipbox.core.config import ProjectConfig, write_project_config


def test_run_missing_main_returns_error(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))
    rc = run_cmd.execute(str(tmp_path), host="127.0.0.1", port=8080, debug=False, debug_port=5678)
    assert rc == 1


def test_run_resolves_project_python(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text("")
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))
    fake_py = tmp_path / ".venv" / "bin" / "python"
    fake_py.parent.mkdir(parents=True)
    fake_py.write_text("")
    fake_py.chmod(0o755)

    calls = {}
    def fake_run(cmd, env, cwd):
        calls["cmd"] = cmd
        calls["env"] = env
        class R: returncode = 0
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)

    rc = run_cmd.execute(str(tmp_path), host="127.0.0.1", port=8080, debug=False, debug_port=5678)
    assert rc == 0
    assert str(fake_py) in calls["cmd"][0]
    assert calls["env"]["ALGO_HOST"] == "127.0.0.1"
    assert calls["env"]["ALGO_PORT"] == "8080"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/algo/test_run.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement algo run**

`aishipbox/algo/commands/run.py`:
```python
"""algo run: launch the local HTTP server using the project's venv."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from aishipbox.core.env import load_env_file
from aishipbox.core.venv import python_executable, VenvError


def execute(path: str, host: str, port: int, debug: bool, debug_port: int) -> int:
    service_dir = Path(path).resolve()
    main_file = service_dir / "main.py"
    if not main_file.exists():
        print(f"main.py 不存在：{service_dir}")
        return 1

    try:
        py = python_executable(service_dir)
    except VenvError as e:
        print(str(e))
        return 1

    env = os.environ.copy()
    env.update(load_env_file(service_dir / ".env"))
    env.update({
        "ALGO_SERVICE_DIR": str(service_dir),
        "ALGO_HOST": host,
        "ALGO_PORT": str(port),
        "ALGO_DEBUG": "1" if debug else "0",
        "ALGO_DEBUG_PORT": str(debug_port),
    })

    runner_script = Path(__file__).resolve().parent.parent / "runner.py"

    try:
        result = subprocess.run([str(py), str(runner_script)], env=env, cwd=str(service_dir.parent))
        return result.returncode
    except KeyboardInterrupt:
        return 0
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/algo/test_run.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add aishipbox/algo/commands/run.py tests/algo/test_run.py
git commit -m "feat(algo): port run command using per-project venv"
```

---

### Task 2.5: Port algo `pack` command

**Files:**
- Create: `aishipbox/algo/commands/pack.py`
- Test: `tests/algo/test_pack.py`

- [ ] **Step 1: Write the failing test**

`tests/algo/test_pack.py`:
```python
import tarfile
from pathlib import Path

from aishipbox.algo.commands import pack as pack_cmd
from aishipbox.core.config import ProjectConfig, write_project_config


def test_pack_creates_tar_gz(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')")
    (tmp_path / "requirements.txt").write_text("")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "junk").write_text("x")
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))

    out = tmp_path / "my_algo.tar.gz"
    rc = pack_cmd.execute(str(tmp_path), str(out))
    assert rc == 0
    assert out.exists()

    with tarfile.open(out, "r:gz") as tar:
        names = tar.getnames()
    assert "main.py" in names
    assert not any(".venv" in n for n in names)
    assert not any(".aishipbox.toml" in n for n in names)


def test_pack_missing_main(tmp_path):
    rc = pack_cmd.execute(str(tmp_path), str(tmp_path / "x.tar.gz"))
    assert rc == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/algo/test_pack.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement algo pack**

`aishipbox/algo/commands/pack.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/algo/test_pack.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add aishipbox/algo/commands/pack.py tests/algo/test_pack.py
git commit -m "feat(algo): port pack command"
```

---

### Task 2.6: Port algo `debug`, `stubs`, `install-deps`

**Files:**
- Create: `aishipbox/algo/commands/debug.py`
- Create: `aishipbox/algo/commands/stubs.py`
- Create: `aishipbox/algo/commands/install_deps.py`
- Test: `tests/algo/test_debug.py`

These are smaller. Copy from `resources/mas-algo-cli/mas_algo_cli/commands/{debug,stubs,install_deps}.py` and update imports.

- [ ] **Step 1: Copy and adapt debug.py**

Read `resources/mas-algo-cli/mas_algo_cli/commands/debug.py`, copy its contents to `aishipbox/algo/commands/debug.py`. Replace any output strings with Chinese equivalents (e.g. "Generated launch.json" → "已生成 launch.json"). Keep behavior identical.

- [ ] **Step 2: Copy and adapt stubs.py**

Same process for `stubs.py`. Update `resources.files("mas_algo_cli.stubs")` → `resources.files("aishipbox.algo.stubs")`. Use `aishipbox.core.venv.pip_install` instead of subprocess.

- [ ] **Step 3: Copy and adapt install_deps.py**

Same process. Use `aishipbox.core.venv.pip_install`.

- [ ] **Step 4: Smoke test**

```bash
uv run python -c "from aishipbox.algo.commands import debug, stubs, install_deps"
```

Expected: no errors.

- [ ] **Step 5: Add minimal test for debug**

`tests/algo/test_debug.py`:
```python
import json
from pathlib import Path

from aishipbox.algo.commands import debug as debug_cmd


def test_debug_writes_launch_json(tmp_path):
    rc = debug_cmd.execute(str(tmp_path))
    assert rc == 0
    launch = tmp_path / ".vscode" / "launch.json"
    assert launch.exists()
    cfg = json.loads(launch.read_text())
    assert any("debugpy" in str(c).lower() for c in cfg.get("configurations", []))
```

```bash
uv run pytest tests/algo/test_debug.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add aishipbox/algo/commands/ tests/algo/test_debug.py
git commit -m "feat(algo): port debug/stubs/install-deps commands"
```

---

### Task 2.7: Wire algo into cli.py dispatch

**Files:**
- Modify: `aishipbox/algo/__init__.py`
- Test: `tests/algo/test_dispatch.py`

- [ ] **Step 1: Write the failing test**

`tests/algo/test_dispatch.py`:
```python
from aishipbox import algo


def test_dispatch_routes_to_new(monkeypatch):
    called = {}
    def fake_execute(name, parent_dir, template=None, yes=False):
        called["name"] = name
        called["template"] = template
        return 0
    monkeypatch.setattr("aishipbox.algo.commands.new.execute", fake_execute)
    rc = algo.dispatch(["new", "my_svc", "--template", "basic", "--yes"])
    assert rc == 0
    assert called == {"name": "my_svc", "template": "basic"}


def test_dispatch_unknown_command():
    rc = algo.dispatch(["bogus"])
    assert rc == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/algo/test_dispatch.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement algo dispatch**

Replace `aishipbox/algo/__init__.py`:
```python
"""algo subcommand group dispatch."""

from __future__ import annotations

import argparse
from typing import List


def dispatch(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="aishipbox algo", description="MAS 算法服务项目管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="新建算法服务项目")
    p_new.add_argument("name")
    p_new.add_argument("-d", "--dir", default=".")
    p_new.add_argument("-t", "--template", choices=["basic", "predict", "cv"])
    p_new.add_argument("--yes", action="store_true")

    p_run = sub.add_parser("run", help="本地运行算法服务")
    p_run.add_argument("path", nargs="?", default=".")
    p_run.add_argument("-p", "--port", type=int, default=8080)
    p_run.add_argument("--host", default="127.0.0.1")
    p_run.add_argument("--debug", action="store_true")
    p_run.add_argument("--debug-port", type=int, default=5678)

    p_pack = sub.add_parser("pack", help="打包算法服务")
    p_pack.add_argument("path", nargs="?", default=".")
    p_pack.add_argument("-o", "--output")

    p_debug = sub.add_parser("debug", help="生成 VS Code 调试配置")
    p_debug.add_argument("path", nargs="?", default=".")

    sub.add_parser("stubs", help="安装 IDE 类型补全包")
    sub.add_parser("install-deps", help="安装托管环境常用依赖")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    from aishipbox.algo.commands import new, run, pack, debug, stubs, install_deps

    if args.cmd == "new":
        return new.execute(args.name, args.dir, args.template, args.yes)
    if args.cmd == "run":
        return run.execute(args.path, args.host, args.port, args.debug, args.debug_port)
    if args.cmd == "pack":
        return pack.execute(args.path, args.output)
    if args.cmd == "debug":
        return debug.execute(args.path)
    if args.cmd == "stubs":
        return stubs.execute()
    if args.cmd == "install-deps":
        return install_deps.execute()
    return 2
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/algo/test_dispatch.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Smoke test top-level**

```bash
uv run aishipbox algo --help
```

Expected: Chinese help text listing new/run/pack/debug/stubs/install-deps.

- [ ] **Step 6: Commit**

```bash
git add aishipbox/algo/__init__.py tests/algo/test_dispatch.py
git commit -m "feat(algo): wire commands into top-level dispatch"
```

---

## Phase 3: Op support

### Task 3.1: Manifest parsing, serialization, validation

**Files:**
- Create: `aishipbox/op/manifest.py`
- Test: `tests/op/test_manifest.py`

- [ ] **Step 1: Create op package init**

`mkdir -p tests/op` and `tests/op/__init__.py`: empty.

- [ ] **Step 2: Write the failing test**

`tests/op/test_manifest.py`:
```python
import pytest

from aishipbox.op.manifest import Manifest, ManifestError, parse_manifest, render_manifest


def test_render_minimal():
    m = Manifest(
        id="my_op",
        name="测试算子",
        description="说明",
        author="me",
        version="0.0.1",
        category=["数据转换"],
        modal=["IMAGE"],
        format=["JPG"],
        language=["zh"],
        cpu_arch=["arm"],
        cpu=1, memory=2048, npu=0,
        auto_data_loading=False,
        arguments=[],
    )
    yaml_text = render_manifest(m)
    assert "id: my_op" in yaml_text
    assert "name: 测试算子" in yaml_text
    assert "arguments: []" in yaml_text


def test_roundtrip(tmp_path):
    m = Manifest(
        id="x", name="x", description="", author="a", version="1.0.0",
        category=["其他"], modal=["OTHER"], format=[], language=["en"],
        cpu_arch=["x86"], cpu=1, memory=2048, npu=0,
        auto_data_loading=True, arguments=[{"name": "n", "type": "string", "description": "d"}],
    )
    text = render_manifest(m)
    parsed = parse_manifest(text)
    assert parsed.id == "x"
    assert parsed.auto_data_loading is True
    assert parsed.arguments[0]["name"] == "n"


def test_validate_bad_version_rejects():
    with pytest.raises(ManifestError):
        Manifest(
            id="x", name="x", description="", author="a", version="1.0",  # bad
            category=["其他"], modal=["OTHER"], format=[], language=["en"],
            cpu_arch=["x86"], cpu=1, memory=2048, npu=0,
            auto_data_loading=False, arguments=[],
        ).validate()


def test_validate_bad_modal_rejects():
    with pytest.raises(ManifestError):
        Manifest(
            id="x", name="x", description="", author="a", version="1.0.0",
            category=["其他"], modal=["NOPE"], format=[], language=["en"],
            cpu_arch=["x86"], cpu=1, memory=2048, npu=0,
            auto_data_loading=False, arguments=[],
        ).validate()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/op/test_manifest.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement manifest module**

`aishipbox/op/manifest.py`:
```python
"""Parse / serialize / validate manifest.yml for custom operators."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
VALID_MODALS = {"TEXT", "IMAGE", "VIDEO", "AUDIO", "OTHER"}
VALID_CPU_ARCHES = {"arm", "x86"}
VALID_CATEGORIES = {"数据提取", "数据抽样", "数据转换", "数据过滤", "数据去重", "数据打标", "其他"}


class ManifestError(Exception):
    pass


@dataclass
class Manifest:
    id: str
    name: str
    description: str
    author: str
    version: str
    category: List[str]
    modal: List[str]
    format: List[str]
    language: List[str]
    cpu_arch: List[str]
    cpu: int
    memory: int
    npu: int
    auto_data_loading: bool
    arguments: List[Dict[str, str]] = field(default_factory=list)

    def validate(self) -> None:
        errs: List[str] = []
        if not self.id:
            errs.append("id 不能为空")
        if not VERSION_RE.match(self.version):
            errs.append(f"version 必须符合 x.y.z 格式：{self.version}")
        for m in self.modal:
            if m not in VALID_MODALS:
                errs.append(f"非法 modal：{m}")
        for c in self.category:
            if c not in VALID_CATEGORIES:
                errs.append(f"非法 category：{c}")
        for a in self.cpu_arch:
            if a not in VALID_CPU_ARCHES:
                errs.append(f"非法 cpu-arch：{a}")
        if self.cpu < 1:
            errs.append("cpu 至少为 1")
        if self.memory < 1:
            errs.append("memory 至少为 1 MB")
        if errs:
            raise ManifestError("\n  - ".join(["manifest 校验失败："] + errs))


def render_manifest(m: Manifest) -> str:
    doc = {
        "id": m.id,
        "name": m.name,
        "description": m.description,
        "author": m.author,
        "version": m.version,
        "tags": {
            "language": m.language,
            "format": m.format,
            "category": m.category,
            "modal": m.modal,
        },
        "runtime": {
            "cpu-arch": m.cpu_arch,
            "resources": [{"cpu": m.cpu, "memory": m.memory, "npu": m.npu}],
            "environment": "python",
            "entrypoint": "process.py",
            "auto-data-loading": m.auto_data_loading,
        },
        "arguments": m.arguments,
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False).replace(
        "arguments:\n", "arguments: []\n" if not m.arguments else "arguments:\n"
    )


def parse_manifest(text: str) -> Manifest:
    doc = yaml.safe_load(text)
    tags = doc.get("tags", {})
    rt = doc.get("runtime", {})
    res = (rt.get("resources") or [{}])[0]
    return Manifest(
        id=doc.get("id", ""),
        name=doc.get("name", ""),
        description=doc.get("description", ""),
        author=doc.get("author", ""),
        version=doc.get("version", ""),
        category=list(tags.get("category", [])),
        modal=list(tags.get("modal", [])),
        format=list(tags.get("format", [])),
        language=list(tags.get("language", [])),
        cpu_arch=list(rt.get("cpu-arch", [])),
        cpu=int(res.get("cpu", 1)),
        memory=int(res.get("memory", 2048)),
        npu=int(res.get("npu", 0)),
        auto_data_loading=bool(rt.get("auto-data-loading", False)),
        arguments=list(doc.get("arguments") or []),
    )


def load_manifest(project_dir: Path) -> Manifest:
    text = (Path(project_dir) / "manifest.yml").read_text(encoding="utf-8")
    return parse_manifest(text)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/op/test_manifest.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add aishipbox/op/manifest.py tests/op/__init__.py tests/op/test_manifest.py
git commit -m "feat(op): manifest parse/serialize/validate"
```

---

### Task 3.2: moxing_mock shim

**Files:**
- Create: `aishipbox/op/moxing_mock/__init__.py`
- Create: `aishipbox/op/moxing_mock/moxing/__init__.py`
- Create: `aishipbox/op/moxing_mock/moxing/file.py`
- Test: `tests/op/test_moxing_mock.py`

- [ ] **Step 1: Write the failing test**

`tests/op/test_moxing_mock.py`:
```python
import os
import sys
from pathlib import Path


def test_moxing_mock_file_ops(tmp_path, monkeypatch):
    # Configure mock to redirect obs:// paths to tmp_path
    monkeypatch.setenv("AISHIPBOX_OBS_INPUT", str(tmp_path / "in"))
    monkeypatch.setenv("AISHIPBOX_OBS_OUTPUT", str(tmp_path / "out"))
    (tmp_path / "in").mkdir()
    (tmp_path / "out").mkdir()
    (tmp_path / "in" / "a.jpg").write_bytes(b"x")
    (tmp_path / "in" / "a.json").write_bytes(b"{}")

    # Insert mock into path
    mock_root = Path(__file__).resolve().parents[2] / "aishipbox" / "op" / "moxing_mock"
    monkeypatch.syspath_prepend(str(mock_root))
    if "moxing" in sys.modules:
        del sys.modules["moxing"]
        if "moxing.file" in sys.modules:
            del sys.modules["moxing.file"]

    import moxing as mox

    files = list(mox.file.list_directory("obs://input/", recursive=False))
    assert sorted(files) == ["a.jpg", "a.json"]

    mox.file.copy("obs://input/a.jpg", "obs://output/copy.jpg")
    assert (tmp_path / "out" / "copy.jpg").exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/op/test_moxing_mock.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement moxing_mock**

`aishipbox/op/moxing_mock/__init__.py`: empty.

`aishipbox/op/moxing_mock/moxing/__init__.py`:
```python
from . import file  # noqa: F401
```

`aishipbox/op/moxing_mock/moxing/file.py`:
```python
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
        # Generic: use input root
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/op/test_moxing_mock.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add aishipbox/op/moxing_mock/ tests/op/test_moxing_mock.py
git commit -m "feat(op): moxing local-FS shim for mock-mode local debug"
```

---

### Task 3.3: Op project templates

**Files:**
- Create: `aishipbox/op/templates/__init__.py` (empty)
- Create: `aishipbox/op/templates/process.blank.py.tmpl`
- Create: `aishipbox/op/templates/process.transform.py.tmpl`
- Create: `aishipbox/op/templates/env.example.tmpl`
- Create: `aishipbox/op/templates/gitignore.tmpl`
- Create: `aishipbox/op/templates/requirements.txt.tmpl`
- Create: `aishipbox/op/templates/AGENTS.md.tmpl`

- [ ] **Step 1: Create templates**

`aishipbox/op/templates/__init__.py`: empty.

`aishipbox/op/templates/process.blank.py.tmpl`:
```python
"""Process implementation. Implement the algorithm in __call__."""

import logging
import os

import moxing as mox


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Process:
    def __init__(self, args):
        self.args = args
        self.input_dir = "input_dir"
        self.output_dir = "output_dir"
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info("Process initialized with args=%s", args)

    def __call__(self, input):
        logger.info("Run input=%s", input)
        # TODO: implement
        return {}
```

`aishipbox/op/templates/process.transform.py.tmpl`:
```python
"""Sample 'transform' operator skeleton — copy OBS input to OBS output."""

import logging
import os
from pathlib import Path

import moxing as mox


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Process:
    def __init__(self, args):
        self.args = args
        self.input_dir = "input_dir"
        self.output_dir = "output_dir"
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def __call__(self, input):
        in_obs = self.args.obs_input_path
        out_obs = self.args.obs_output_path

        for filename in mox.file.list_directory(in_obs, recursive=False):
            logger.info("download %s", filename)
            mox.file.copy(os.path.join(in_obs, filename), os.path.join(self.input_dir, filename))

        self.transform()

        for root, _dirs, files in os.walk(self.output_dir):
            for f in files:
                local = os.path.join(root, f)
                rel = os.path.relpath(local, self.output_dir)
                mox.file.copy(local, os.path.join(out_obs, rel))

    def transform(self) -> None:
        # TODO: replace with real logic
        for f in Path(self.input_dir).iterdir():
            (Path(self.output_dir) / f.name).write_bytes(f.read_bytes())
```

`aishipbox/op/templates/env.example.tmpl`:
```
# 仅在 --obs 模式下需要
OBS_AK=
OBS_SK=
OBS_ENDPOINT=
OBS_INPUT_PATH=obs://bucket/path/to/input
OBS_OUTPUT_PATH=obs://bucket/path/to/output
```

`aishipbox/op/templates/gitignore.tmpl`:
```
.venv/
__pycache__/
*.pyc
.env
obs_input/
obs_output/
.DS_Store
program_package/*.tar
```

`aishipbox/op/templates/requirements.txt.tmpl`:
```
# 算子运行所需依赖（除 moxing 外）
# 例如：
# pillow
```

`aishipbox/op/templates/AGENTS.md.tmpl`:
```markdown
# AGENTS.md

本项目类型：PanguLM 自定义算子（op）
托管运行时：Python 3.10
工具：aishipbox v${aishipbox_version}

## 入口
- program_package/process.py 中的 `Process` 类（实现 __call__）

## 常用命令
- 本地调试（mock OBS）：aishipbox op run
- 本地调试（真实 OBS）：aishipbox op run --obs
- 启动调试：           aishipbox op run --debug   （配合 VS Code "Attach to Op Service"）
- 打包：               aishipbox op pack

## 关键约束
- 算子通过 moxing 访问 OBS；本地默认 mock 到 obs_input/、obs_output/。
- 修改 manifest.yml 后请重新 pack。
- 不要修改 .aishipbox.toml 的 schema_version 与 type 字段。

## 平台参考
- 算子手册：https://support.huaweicloud.com/usermanual-pangulm/pangulm_04_0043.html
```

- [ ] **Step 2: Commit**

```bash
git add aishipbox/op/templates/
git commit -m "feat(op): project templates (process.py, manifest, AGENTS, env)"
```

---

### Task 3.4: Op `new` wizard + command

**Files:**
- Create: `aishipbox/op/wizard.py`
- Create: `aishipbox/op/commands/__init__.py`
- Create: `aishipbox/op/commands/new.py`
- Test: `tests/op/test_new.py`

- [ ] **Step 1: Write the failing test**

`tests/op/test_new.py`:
```python
import pytest

from aishipbox.op.commands import new as new_cmd


def test_new_yes_full_flags_creates_project(tmp_path, monkeypatch):
    monkeypatch.setattr("aishipbox.op.commands.new._provision_and_install", lambda *a, **k: None)

    rc = new_cmd.execute(
        name="my_op",
        parent_dir=str(tmp_path),
        flags={
            "id": "my_op",
            "name": "示例算子",
            "description": "demo",
            "author": "tester",
            "version": "0.0.1",
            "category": ["数据转换"],
            "modal": ["IMAGE"],
            "format": ["JPG"],
            "language": ["zh"],
            "cpu_arch": ["arm"],
            "cpu": 1,
            "memory": 2048,
            "npu": 0,
            "auto_data_loading": False,
            "skeleton": "transform",
        },
        yes=True,
    )
    assert rc == 0
    project = tmp_path / "my_op"
    assert (project / "manifest.yml").exists()
    assert (project / "program_package" / "process.py").exists()
    assert (project / "AGENTS.md").exists()
    assert (project / ".aishipbox.toml").exists()


def test_new_yes_missing_required_errors(tmp_path):
    rc = new_cmd.execute(
        name="my_op",
        parent_dir=str(tmp_path),
        flags={"id": "my_op"},  # missing required
        yes=True,
    )
    assert rc == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/op/test_new.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement wizard**

`aishipbox/op/wizard.py`:
```python
"""Interactive wizard for `aishipbox op new`."""

from __future__ import annotations

from typing import Any, Dict, List

from aishipbox.core import strings, ui


def run_wizard(default_id: str) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    fields["id"] = ui.ask_text(strings.OP_FIELD_ID, default=default_id)
    fields["name"] = ui.ask_text(strings.OP_FIELD_NAME, default=fields["id"])
    fields["description"] = ui.ask_text(strings.OP_FIELD_DESCRIPTION, default="")
    fields["author"] = ui.ask_text(strings.OP_FIELD_AUTHOR, default="")
    fields["version"] = ui.ask_text(strings.OP_FIELD_VERSION, default="0.0.1")
    fields["category"] = ui.ask_checkbox(strings.OP_FIELD_CATEGORY, strings.OP_CATEGORIES) or ["其他"]
    fields["modal"] = ui.ask_checkbox(strings.OP_FIELD_MODAL, strings.OP_MODALS) or ["OTHER"]
    fields["format"] = [s.strip() for s in ui.ask_text(strings.OP_FIELD_FORMAT, default="").split(",") if s.strip()]
    fields["language"] = [s.strip() for s in ui.ask_text(strings.OP_FIELD_LANGUAGE, default="zh").split(",") if s.strip()]
    fields["cpu_arch"] = [ui.ask_select(strings.OP_FIELD_CPU_ARCH, strings.OP_CPU_ARCHES, default="arm")]
    fields["cpu"] = int(ui.ask_text(strings.OP_FIELD_CPU, default="1"))
    fields["memory"] = int(ui.ask_text(strings.OP_FIELD_MEMORY, default="2048"))
    fields["npu"] = int(ui.ask_text(strings.OP_FIELD_NPU, default="0"))
    fields["auto_data_loading"] = ui.ask_confirm(strings.OP_FIELD_AUTO_DATA_LOADING, default=False)
    fields["skeleton"] = ui.ask_select(
        strings.OP_FIELD_SKELETON,
        [strings.OP_SKELETON_BLANK, strings.OP_SKELETON_TRANSFORM],
        default=strings.OP_SKELETON_TRANSFORM,
    ).split()[0]
    return fields
```

`aishipbox/op/commands/__init__.py`: empty.

`aishipbox/op/commands/new.py`:
```python
"""op new: create a custom-operator project."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional

from aishipbox import __version__
from aishipbox.core import strings
from aishipbox.core.config import HOSTED_RUNTIMES, ProjectConfig, write_project_config
from aishipbox.core.venv import provision_venv, pip_install
from aishipbox.op import wizard
from aishipbox.op.manifest import Manifest, ManifestError, render_manifest


REQUIRED_FIELDS = (
    "id", "name", "version", "category", "modal",
    "cpu_arch", "cpu", "memory", "npu", "auto_data_loading", "skeleton",
)


def execute(name: str, parent_dir: str, flags: Optional[Dict[str, Any]] = None, yes: bool = False) -> int:
    flags = dict(flags or {})
    project_dir = Path(parent_dir).resolve() / name
    if project_dir.exists():
        print(strings.TARGET_DIR_EXISTS.format(path=project_dir))
        return 1

    if yes:
        missing = [f for f in REQUIRED_FIELDS if f not in flags]
        if missing:
            print(strings.MISSING_FLAGS_FOR_YES.format(fields=", ".join(missing)))
            return 2
        fields = flags
    else:
        fields = wizard.run_wizard(default_id=name)
        fields.update(flags)  # CLI flags override interactive answers

    try:
        manifest = Manifest(
            id=fields["id"],
            name=fields["name"],
            description=fields.get("description", ""),
            author=fields.get("author", ""),
            version=fields["version"],
            category=fields["category"],
            modal=fields["modal"],
            format=fields.get("format", []),
            language=fields.get("language", ["zh"]),
            cpu_arch=fields["cpu_arch"],
            cpu=int(fields["cpu"]),
            memory=int(fields["memory"]),
            npu=int(fields["npu"]),
            auto_data_loading=bool(fields["auto_data_loading"]),
            arguments=fields.get("arguments", []),
        )
        manifest.validate()
    except ManifestError as e:
        print(str(e))
        return 1

    project_dir.mkdir(parents=True)
    (project_dir / "program_package").mkdir()
    (project_dir / "obs_input").mkdir()
    (project_dir / "obs_output").mkdir()

    (project_dir / "manifest.yml").write_text(render_manifest(manifest), encoding="utf-8")

    tpl = resources.files("aishipbox.op.templates")
    skeleton = fields["skeleton"]
    process_tmpl = tpl.joinpath(f"process.{skeleton}.py.tmpl").read_text(encoding="utf-8")
    (project_dir / "program_package" / "process.py").write_text(process_tmpl, encoding="utf-8")
    (project_dir / "program_package" / "requirements.txt").write_text(
        tpl.joinpath("requirements.txt.tmpl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (project_dir / ".env.example").write_text(tpl.joinpath("env.example.tmpl").read_text(encoding="utf-8"), encoding="utf-8")
    (project_dir / ".gitignore").write_text(tpl.joinpath("gitignore.tmpl").read_text(encoding="utf-8"), encoding="utf-8")
    agents_tmpl = tpl.joinpath("AGENTS.md.tmpl").read_text(encoding="utf-8")
    (project_dir / "AGENTS.md").write_text(
        Template(agents_tmpl).safe_substitute(aishipbox_version=__version__),
        encoding="utf-8",
    )

    write_project_config(project_dir, ProjectConfig(type="op", runtime=HOSTED_RUNTIMES["op"]))

    _provision_and_install(project_dir)

    print(f"\n算子已创建：{project_dir}")
    print(f"\n{strings.NEXT_STEPS_HEADER}")
    print(f"  1. cd {name}")
    print(f"  2. 在 program_package/process.py 中实现算法")
    print(f"  3. 将测试数据放入 obs_input/")
    print(f"  4. aishipbox op run            # mock 模式")
    print(f"  5. aishipbox op pack")
    return 0


def _provision_and_install(project_dir: Path) -> None:
    provision_venv(project_dir, HOSTED_RUNTIMES["op"])
    req = project_dir / "program_package" / "requirements.txt"
    # Skip if only comments
    content = req.read_text(encoding="utf-8")
    pkgs = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
    if pkgs:
        pip_install(project_dir, *pkgs)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/op/test_new.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add aishipbox/op/wizard.py aishipbox/op/commands/ tests/op/test_new.py
git commit -m "feat(op): new command with wizard and --yes flag mode"
```

---

### Task 3.5: Op `run` command (mock + --obs)

**Files:**
- Create: `aishipbox/op/runner.py`
- Create: `aishipbox/op/commands/run.py`
- Test: `tests/op/test_run.py`

- [ ] **Step 1: Write the failing test**

`tests/op/test_run.py`:
```python
import os
from pathlib import Path

from aishipbox.op.commands import run as run_cmd
from aishipbox.core.config import ProjectConfig, write_project_config


def _setup_op_project(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="op", runtime="3.10"))
    (tmp_path / "program_package").mkdir()
    (tmp_path / "program_package" / "process.py").write_text("class Process: pass")
    (tmp_path / "obs_input").mkdir()
    (tmp_path / "obs_output").mkdir()
    py_bin = tmp_path / ".venv" / "bin"
    py_bin.mkdir(parents=True)
    py = py_bin / "python"
    py.write_text("")
    py.chmod(0o755)
    return tmp_path


def test_run_mock_sets_env(tmp_path, monkeypatch):
    project = _setup_op_project(tmp_path)
    captured = {}

    def fake_run(cmd, env, cwd):
        captured.update(env=env, cmd=cmd)
        class R: returncode = 0
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)

    rc = run_cmd.execute(str(project), obs=False, debug=False)
    assert rc == 0
    assert captured["env"]["AISHIPBOX_OBS_INPUT"] == str(project / "obs_input")
    assert captured["env"]["AISHIPBOX_OBS_OUTPUT"] == str(project / "obs_output")
    assert "moxing_mock" in captured["env"]["PYTHONPATH"]


def test_run_obs_missing_creds_fails(tmp_path):
    project = _setup_op_project(tmp_path)
    rc = run_cmd.execute(str(project), obs=True, debug=False)
    assert rc == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/op/test_run.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement op runner.py + run command**

`aishipbox/op/runner.py`:
```python
"""op runner — invoked by `aishipbox op run` inside the project venv."""

from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obs-input-path", default="obs://input/")
    parser.add_argument("--obs-output-path", default="obs://output/")
    args = parser.parse_args()

    process_py = Path("program_package/process.py").resolve()
    if not process_py.exists():
        logger.error("找不到 program_package/process.py")
        return 1

    spec = importlib.util.spec_from_file_location("process", process_py)
    module = importlib.util.module_from_spec(spec)
    sys.modules["process"] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "Process"):
        logger.error("process.py 中没有 Process 类")
        return 1

    proc = module.Process(args)
    proc(None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`aishipbox/op/commands/run.py`:
```python
"""op run: launch the operator locally in mock or --obs mode."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from aishipbox.core import strings
from aishipbox.core.env import load_env_file
from aishipbox.core.venv import python_executable, VenvError


REQUIRED_OBS_FIELDS = ("OBS_AK", "OBS_SK", "OBS_ENDPOINT", "OBS_INPUT_PATH", "OBS_OUTPUT_PATH")


def execute(path: str, obs: bool, debug: bool, debug_port: int = 5678) -> int:
    project = Path(path).resolve()
    try:
        py = python_executable(project)
    except VenvError as e:
        print(str(e))
        return 1

    env = os.environ.copy()
    env.update(load_env_file(project / ".env"))

    if obs:
        missing = [f for f in REQUIRED_OBS_FIELDS if not env.get(f)]
        if missing:
            print(strings.OBS_CREDS_MISSING.format(fields=", ".join(missing)))
            return 1
        in_path = env["OBS_INPUT_PATH"]
        out_path = env["OBS_OUTPUT_PATH"]
    else:
        mock_root = Path(__file__).resolve().parent.parent / "moxing_mock"
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{mock_root}{os.pathsep}{existing}" if existing else str(mock_root)
        env["AISHIPBOX_OBS_INPUT"] = str(project / "obs_input")
        env["AISHIPBOX_OBS_OUTPUT"] = str(project / "obs_output")
        in_path = "obs://input/"
        out_path = "obs://output/"

    runner = Path(__file__).resolve().parent.parent / "runner.py"

    cmd = [str(py)]
    if debug:
        cmd += ["-m", "debugpy", "--listen", f"127.0.0.1:{debug_port}", "--wait-for-client"]
        print(f"调试模式：等待 VS Code 在端口 {debug_port} 附加...")
    cmd += [str(runner), "--obs-input-path", in_path, "--obs-output-path", out_path]

    try:
        result = subprocess.run(cmd, env=env, cwd=str(project))
        return result.returncode
    except KeyboardInterrupt:
        return 0
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/op/test_run.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add aishipbox/op/runner.py aishipbox/op/commands/run.py tests/op/test_run.py
git commit -m "feat(op): run command (mock and --obs modes)"
```

---

### Task 3.6: Op `pack` command

**Files:**
- Create: `aishipbox/op/commands/pack.py`
- Test: `tests/op/test_pack.py`

- [ ] **Step 1: Write the failing test**

`tests/op/test_pack.py`:
```python
import tarfile
from pathlib import Path

from aishipbox.op.commands import pack as pack_cmd
from aishipbox.core.config import ProjectConfig, write_project_config
from aishipbox.op.manifest import Manifest, render_manifest


def _setup_op(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="op", runtime="3.10"))
    (tmp_path / "program_package").mkdir()
    (tmp_path / "program_package" / "process.py").write_text("class Process:\n    pass\n")
    m = Manifest(
        id="my_op", name="x", description="", author="", version="0.0.1",
        category=["数据转换"], modal=["IMAGE"], format=[], language=["zh"],
        cpu_arch=["arm"], cpu=1, memory=2048, npu=0,
        auto_data_loading=False, arguments=[],
    )
    (tmp_path / "manifest.yml").write_text(render_manifest(m), encoding="utf-8")
    return tmp_path


def test_pack_builds_tar(tmp_path):
    p = _setup_op(tmp_path)
    rc = pack_cmd.execute(str(p), output=None, force=False)
    assert rc == 0
    out = p / "program_package" / "my_op.tar"
    assert out.exists()
    with tarfile.open(out, "r:") as tar:
        names = tar.getnames()
    assert "process.py" in names
    assert "manifest.yml" in names


def test_pack_invalid_manifest(tmp_path):
    p = _setup_op(tmp_path)
    (p / "manifest.yml").write_text("id: x\nversion: 1.0\n")  # bad version
    rc = pack_cmd.execute(str(p), output=None, force=False)
    assert rc == 1


def test_pack_missing_process(tmp_path):
    p = _setup_op(tmp_path)
    (p / "program_package" / "process.py").unlink()
    rc = pack_cmd.execute(str(p), output=None, force=False)
    assert rc == 1


def test_pack_refuses_existing_without_force(tmp_path):
    p = _setup_op(tmp_path)
    out = p / "program_package" / "my_op.tar"
    out.write_text("old")
    rc = pack_cmd.execute(str(p), output=None, force=False)
    assert rc == 1
    rc = pack_cmd.execute(str(p), output=None, force=True)
    assert rc == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/op/test_pack.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement op pack**

`aishipbox/op/commands/pack.py`:
```python
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

    # Build a staging dir = program_package/ contents + manifest.yml at root
    with tempfile.TemporaryDirectory() as stage_str:
        stage = Path(stage_str)
        # copy program_package contents (not the dir itself)
        for item in (project / "program_package").iterdir():
            if item.name.endswith(".tar"):
                continue
            if item.is_dir():
                shutil.copytree(item, stage / item.name)
            else:
                shutil.copy2(item, stage / item.name)
        shutil.copy2(project / "manifest.yml", stage / "manifest.yml")

        build_tar(stage, out_path, excludes=OP_EXCLUDES, gzip=False)

    print(f"已生成：{out_path}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/op/test_pack.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add aishipbox/op/commands/pack.py tests/op/test_pack.py
git commit -m "feat(op): pack command building program_package/<id>.tar"
```

---

### Task 3.7: Op `debug` command (launch.json)

**Files:**
- Create: `aishipbox/op/commands/debug.py`
- Test: `tests/op/test_debug.py`

- [ ] **Step 1: Write the failing test**

`tests/op/test_debug.py`:
```python
import json
from aishipbox.op.commands import debug as debug_cmd


def test_writes_launch_json(tmp_path):
    rc = debug_cmd.execute(str(tmp_path))
    assert rc == 0
    cfg = json.loads((tmp_path / ".vscode" / "launch.json").read_text())
    names = [c["name"] for c in cfg["configurations"]]
    assert any("Op" in n for n in names)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/op/test_debug.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement op debug**

`aishipbox/op/commands/debug.py`:
```python
"""op debug: write .vscode/launch.json with debugpy attach config."""

from __future__ import annotations

import json
from pathlib import Path


def execute(path: str) -> int:
    project = Path(path).resolve()
    vsc = project / ".vscode"
    vsc.mkdir(exist_ok=True)
    cfg = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Attach to Op Service",
                "type": "debugpy",
                "request": "attach",
                "connect": {"host": "127.0.0.1", "port": 5678},
                "justMyCode": False,
                "pathMappings": [{"localRoot": "${workspaceFolder}", "remoteRoot": "."}],
            }
        ],
    }
    (vsc / "launch.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"已生成 .vscode/launch.json")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/op/test_debug.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add aishipbox/op/commands/debug.py tests/op/test_debug.py
git commit -m "feat(op): debug command writes .vscode/launch.json"
```

---

### Task 3.8: Wire op into top-level dispatch

**Files:**
- Modify: `aishipbox/op/__init__.py`
- Test: `tests/op/test_dispatch.py`

- [ ] **Step 1: Write the failing test**

`tests/op/test_dispatch.py`:
```python
from aishipbox import op


def test_dispatch_routes_to_new_with_yes(monkeypatch):
    captured = {}

    def fake_execute(name, parent_dir, flags=None, yes=False):
        captured["name"] = name
        captured["yes"] = yes
        captured["flags"] = flags
        return 0
    monkeypatch.setattr("aishipbox.op.commands.new.execute", fake_execute)

    rc = op.dispatch([
        "new", "my_op", "--yes",
        "--id", "my_op", "--name", "示例",
        "--version", "0.0.1",
        "--category", "数据转换",
        "--modal", "IMAGE",
        "--cpu-arch", "arm",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=false",
        "--skeleton", "transform",
    ])
    assert rc == 0
    assert captured["name"] == "my_op"
    assert captured["yes"] is True
    assert captured["flags"]["category"] == ["数据转换"]
    assert captured["flags"]["skeleton"] == "transform"


def test_dispatch_unknown_command():
    assert op.dispatch(["bogus"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/op/test_dispatch.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement op dispatch**

`aishipbox/op/__init__.py`:
```python
"""op subcommand group dispatch."""

from __future__ import annotations

import argparse
from typing import Any, Dict, List


def _str2bool(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "y")


def dispatch(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="aishipbox op", description="自定义算子项目管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="新建算子项目")
    p_new.add_argument("name")
    p_new.add_argument("-d", "--dir", default=".")
    p_new.add_argument("--id")
    p_new.add_argument("--name", dest="op_name")
    p_new.add_argument("--description", default="")
    p_new.add_argument("--author", default="")
    p_new.add_argument("--version")
    p_new.add_argument("--category", action="append", default=None)
    p_new.add_argument("--modal", action="append", default=None)
    p_new.add_argument("--format", action="append", default=None)
    p_new.add_argument("--language", action="append", default=None)
    p_new.add_argument("--cpu-arch", action="append", default=None)
    p_new.add_argument("--cpu", type=int)
    p_new.add_argument("--memory", type=int)
    p_new.add_argument("--npu", type=int)
    p_new.add_argument("--auto-data-loading", type=_str2bool, default=None)
    p_new.add_argument("--skeleton", choices=["blank", "transform"])
    p_new.add_argument("--yes", action="store_true")

    p_run = sub.add_parser("run", help="本地运行算子")
    p_run.add_argument("path", nargs="?", default=".")
    p_run.add_argument("--obs", action="store_true")
    p_run.add_argument("--debug", action="store_true")
    p_run.add_argument("--debug-port", type=int, default=5678)

    p_pack = sub.add_parser("pack", help="打包算子")
    p_pack.add_argument("path", nargs="?", default=".")
    p_pack.add_argument("-o", "--output")
    p_pack.add_argument("--force", action="store_true")

    p_debug = sub.add_parser("debug", help="生成 VS Code 调试配置")
    p_debug.add_argument("path", nargs="?", default=".")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    from aishipbox.op.commands import new, run, pack, debug

    if args.cmd == "new":
        flags: Dict[str, Any] = {}
        if args.id is not None: flags["id"] = args.id
        if args.op_name is not None: flags["name"] = args.op_name
        if args.description: flags["description"] = args.description
        if args.author: flags["author"] = args.author
        if args.version is not None: flags["version"] = args.version
        if args.category is not None: flags["category"] = args.category
        if args.modal is not None: flags["modal"] = args.modal
        if args.format is not None: flags["format"] = args.format
        if args.language is not None: flags["language"] = args.language
        if args.cpu_arch is not None: flags["cpu_arch"] = args.cpu_arch
        if args.cpu is not None: flags["cpu"] = args.cpu
        if args.memory is not None: flags["memory"] = args.memory
        if args.npu is not None: flags["npu"] = args.npu
        if args.auto_data_loading is not None: flags["auto_data_loading"] = args.auto_data_loading
        if args.skeleton is not None: flags["skeleton"] = args.skeleton
        return new.execute(args.name, args.dir, flags=flags, yes=args.yes)

    if args.cmd == "run":
        return run.execute(args.path, obs=args.obs, debug=args.debug, debug_port=args.debug_port)
    if args.cmd == "pack":
        return pack.execute(args.path, output=args.output, force=args.force)
    if args.cmd == "debug":
        return debug.execute(args.path)
    return 2
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/op/test_dispatch.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Smoke test**

```bash
uv run aishipbox op --help
```

Expected: Chinese help text listing new/run/pack/debug.

- [ ] **Step 6: Commit**

```bash
git add aishipbox/op/__init__.py tests/op/test_dispatch.py
git commit -m "feat(op): wire commands into top-level dispatch"
```

---

## Phase 4: Integration tests + polish

### Task 4.1: End-to-end op flow (new --yes → run mock → pack)

**Files:**
- Test: `tests/integration/test_op_e2e.py`

- [ ] **Step 1: Add integration marker config**

Edit `pyproject.toml`, add:
```toml
[tool.pytest.ini_options]
markers = ["integration: end-to-end flows that touch venv and uv"]
```

Create `tests/integration/__init__.py`: empty.

- [ ] **Step 2: Write the integration test**

`tests/integration/test_op_e2e.py`:
```python
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "aishipbox", *args],
        cwd=cwd, capture_output=True, text=True,
    )


def test_op_new_run_pack(tmp_path):
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run(
        "op", "new", "my_op",
        "--dir", str(tmp_path),
        "--yes",
        "--id", "my_op",
        "--name", "测试算子",
        "--version", "0.0.1",
        "--category", "数据转换",
        "--modal", "IMAGE",
        "--cpu-arch", "arm",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=false",
        "--skeleton", "transform",
    )
    assert r.returncode == 0, r.stderr

    project = tmp_path / "my_op"
    assert (project / "manifest.yml").exists()
    assert (project / "program_package" / "process.py").exists()
    assert (project / ".venv").exists()
    assert (project / "AGENTS.md").exists()

    # drop a sample file into obs_input
    (project / "obs_input" / "a.jpg").write_bytes(b"hi")

    r = _run("op", "run", cwd=project)
    assert r.returncode == 0, r.stderr
    assert (project / "obs_output" / "a.jpg").read_bytes() == b"hi"

    r = _run("op", "pack", cwd=project)
    assert r.returncode == 0, r.stderr
    tar_path = project / "program_package" / "my_op.tar"
    assert tar_path.exists()
    with tarfile.open(tar_path, "r:") as tar:
        names = tar.getnames()
    assert "manifest.yml" in names
    assert "process.py" in names
```

- [ ] **Step 3: Run the test**

```bash
uv run pytest tests/integration/test_op_e2e.py -v -m integration
```

Expected: PASS (1 test). May skip if uv missing — should not skip in normal dev env.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tests/integration/
git commit -m "test: end-to-end op new → run → pack integration"
```

---

### Task 4.2: End-to-end algo flow

**Files:**
- Test: `tests/integration/test_algo_e2e.py`

- [ ] **Step 1: Write the integration test**

`tests/integration/test_algo_e2e.py`:
```python
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "aishipbox", *args],
        cwd=cwd, capture_output=True, text=True,
    )


def test_algo_new_then_pack(tmp_path):
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run("algo", "new", "my_algo", "--dir", str(tmp_path), "-t", "basic", "--yes")
    assert r.returncode == 0, r.stderr

    project = tmp_path / "my_algo"
    assert (project / "main.py").exists()
    assert (project / ".venv").exists()
    assert (project / ".aishipbox.toml").exists()
    assert (project / "AGENTS.md").exists()

    r = _run("algo", "pack", cwd=project)
    assert r.returncode == 0, r.stderr
    tar_path = Path(project / "my_algo.tar.gz")
    assert tar_path.exists() or any(project.glob("*.tar.gz"))
```

- [ ] **Step 2: Run the test**

```bash
uv run pytest tests/integration/test_algo_e2e.py -v -m integration
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_algo_e2e.py
git commit -m "test: end-to-end algo new → pack integration"
```

---

### Task 4.3: README + sanity sweep

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README.md**

```markdown
# aishipbox

JAC PanguLM 算法服务（algo）与自定义算子（op）开发 CLI。

## 安装

```bash
uv tool install aishipbox
```

## 快速开始

### 算法服务（algo）

```bash
aishipbox algo new my_algo -t basic
cd my_algo
aishipbox algo run
aishipbox algo pack
```

### 自定义算子（op）

```bash
aishipbox op new my_op           # 启动交互向导
cd my_op
# 把测试数据放入 obs_input/
aishipbox op run                  # 默认 mock 模式
aishipbox op run --obs            # 真实 OBS（读取 .env）
aishipbox op pack
```

非交互模式（用于脚本）：

```bash
aishipbox op new my_op --yes \
  --id my_op --name 示例 --version 0.0.1 \
  --category 数据转换 --modal IMAGE \
  --cpu-arch arm --cpu 1 --memory 2048 --npu 0 \
  --auto-data-loading=false --skeleton transform
```

## 文档

- 设计：`docs/superpowers/specs/2026-05-11-aishipbox-design.md`
- 实施计划：`docs/superpowers/plans/2026-05-11-aishipbox.md`
- 算子手册：https://support.huaweicloud.com/usermanual-pangulm/pangulm_04_0043.html
```

- [ ] **Step 2: Full-suite sanity check**

```bash
uv run pytest -v
```

Expected: All unit tests PASS. Integration tests PASS or skip (if uv missing in CI).

- [ ] **Step 3: Final commit**

```bash
git add README.md
git commit -m "docs: README quickstart for algo and op"
```

---

## Self-review checklist

- [ ] Spec coverage:
  - [ ] CLI shape `aishipbox algo|op …` — Tasks 1.7, 2.7, 3.8
  - [ ] Absorb mas-algo-cli — Tasks 2.1–2.7
  - [ ] Chinese strings — Task 1.1 + Chinese strings inline in all commands
  - [ ] Wizard with --yes — Tasks 1.6, 3.4
  - [ ] Per-project venv via uv — Tasks 1.4, 2.3, 3.4
  - [ ] .aishipbox.toml marker — Tasks 1.2, 2.3, 3.4
  - [ ] AGENTS.md generated — Tasks 2.1, 2.3, 3.3, 3.4
  - [ ] moxing_mock + --obs — Tasks 3.2, 3.5
  - [ ] Manifest validation — Task 3.1, 3.6
  - [ ] Pack output format — Tasks 2.5, 3.6
  - [ ] End-to-end coverage — Tasks 4.1, 4.2
- [ ] No "TODO" / "TBD" in steps (verified: all code shown inline).
- [ ] Type consistency:
  - `ProjectConfig.type` / `runtime` / `schema_version` — consistent across 1.2, 2.3, 3.4
  - `python_executable()` and `provision_venv()` signatures — consistent across 1.4, 2.4, 3.4, 3.5
  - `build_tar(source, output, excludes, gzip)` — consistent across 1.5, 2.5, 3.6

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-11-aishipbox.md`.

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.
