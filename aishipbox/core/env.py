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
