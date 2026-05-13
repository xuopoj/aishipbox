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
    print("已生成 .vscode/launch.json")
    return 0
