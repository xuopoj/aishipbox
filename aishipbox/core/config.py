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

# Packages preinstalled in the op platform's base image. Mirrored to the
# project's local .venv at `op new` time so dev parity matches what the
# operator will actually run against. These are NOT written into
# program_package/dependency/requirements.txt — that file ships to the
# platform via `op pack`, and listing already-preinstalled packages there
# either silently succeeds (when versions match) or fails to install
# (when the image drifts and no .whl is bundled). Keep this list short
# and bump whenever the platform image changes.
PLATFORM_PRESET_PINS = (
    "pandas==1.3.5",
    "numpy==1.26.4",
    "pyarrow==18.0.0",
)

SCHEMA_VERSION = 1

CONFIG_FILENAME = ".aishipbox.toml"


@dataclass
class ProjectConfig:
    type: str
    runtime: str
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
