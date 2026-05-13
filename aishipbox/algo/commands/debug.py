"""Generate VS Code debug configuration."""

import json
from pathlib import Path

LAUNCH_CONFIG = {
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Attach to Algo Service",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "127.0.0.1",
                "port": 5678
            }
        }
    ]
}


def execute(path: str) -> int:
    project_dir = Path(path).resolve()
    vscode_dir = project_dir / ".vscode"
    launch_file = vscode_dir / "launch.json"

    vscode_dir.mkdir(exist_ok=True)

    if launch_file.exists():
        print(f"警告：{launch_file} 已存在，将覆盖")

    launch_file.write_text(json.dumps(LAUNCH_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"已生成：{launch_file}")

    print("\n调试步骤：")
    print("  1. 在代码中设置断点")
    print("  2. 运行：aishipbox algo run --debug")
    print("  3. 在 VS Code 中按 F5 附加调试器")

    return 0
