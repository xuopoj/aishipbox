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
