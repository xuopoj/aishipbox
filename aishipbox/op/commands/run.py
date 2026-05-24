"""op run: launch the operator locally in mock or --obs mode."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from aishipbox.core import strings
from aishipbox.core.env import load_env_file
from aishipbox.core.venv import python_executable, VenvError
from aishipbox.op.manifest import Manifest, ManifestError, load_manifest


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
        op_pkg = Path(__file__).resolve().parent.parent
        mock_roots = [op_pkg / "moxing_mock", op_pkg / "ma_utils_mock"]
        existing = env.get("PYTHONPATH", "")
        prefix = os.pathsep.join(str(r) for r in mock_roots)
        env["PYTHONPATH"] = f"{prefix}{os.pathsep}{existing}" if existing else prefix
        env["AISHIPBOX_OBS_INPUT"] = str(project / "obs_input")
        env["AISHIPBOX_OBS_OUTPUT"] = str(project / "obs_output")
        in_path = "obs://input/"
        out_path = "obs://output/"

    runner = Path(__file__).resolve().parent.parent / "runner.py"

    auto_dl = "false"
    operator_args: Dict[str, Any] = {}
    try:
        manifest = load_manifest(project)
        auto_dl = "true" if manifest.auto_data_loading else "false"
        operator_args = _operator_args_from_manifest(manifest)
    except (FileNotFoundError, ManifestError):
        pass

    cmd = [str(py)]
    if debug:
        cmd += ["-m", "debugpy", "--listen", f"127.0.0.1:{debug_port}", "--wait-for-client"]
        print(f"调试模式：等待 VS Code 在端口 {debug_port} 附加...")
    cmd += [
        str(runner),
        "--obs-input-path", in_path,
        "--obs-output-path", out_path,
        "--auto-data-loading", auto_dl,
        "--operator-args", json.dumps(operator_args, ensure_ascii=False),
    ]

    try:
        result = subprocess.run(cmd, env=env, cwd=str(project))
        return result.returncode
    except KeyboardInterrupt:
        return 0


def _operator_args_from_manifest(manifest: Manifest) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for arg in manifest.arguments:
        key = arg.get("key")
        if not key:
            continue
        out[str(key)] = arg.get("default")
    return out
