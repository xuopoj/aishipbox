"""Install stub packages for IDE/linting support into the project venv."""

from __future__ import annotations

import subprocess
from importlib import resources
from pathlib import Path

from aishipbox.core.venv import python_executable, require_uv, VenvError


def execute(path: str = ".") -> int:
    project_dir = Path(path).resolve()
    try:
        py = python_executable(project_dir)
        uv = require_uv()
    except VenvError as e:
        print(str(e))
        return 1

    stubs_dir = resources.files("aishipbox.algo.stubs")
    with resources.as_file(stubs_dir) as stubs_path:
        print(f"安装 rest-stubs：{stubs_path}")
        cmd = [uv, "pip", "install", "--python", str(py), str(stubs_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"错误：{result.stderr}")
            return 1
        print("已安装 rest-stubs")
        print("\n'rest.process_base' 现在可以被解析（IDE 类型提示）。")
        return 0
