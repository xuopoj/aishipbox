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
