"""Install hosting-environment dependencies into the project venv."""

from __future__ import annotations

import subprocess
from pathlib import Path

from aishipbox.core.venv import python_executable, require_uv, VenvError


HOSTING_DEPS = [
    "numpy",
    "pandas",
    "scipy",
    "scikit-learn",
    "requests",
    "flask",
    "opencv-python",
    "pillow",
    "pyyaml",
    "pydantic",
    "aiohttp",
    "openpyxl",
    "lxml",
]


def execute(path: str = ".") -> int:
    project_dir = Path(path).resolve()
    try:
        py = python_executable(project_dir)
        uv = require_uv()
    except VenvError as e:
        print(str(e))
        return 1

    print("安装托管环境常用依赖...")
    print(f"  包：{', '.join(HOSTING_DEPS)}\n")

    cmd = [uv, "pip", "install", "--python", str(py)] + HOSTING_DEPS
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print("\n错误：部分依赖安装失败")
        return 1

    print("\n完成：托管环境依赖已安装到项目 .venv/。")
    return 0
