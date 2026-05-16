"""op runner — invoked by `aishipbox op run` inside the project venv.

Emulates the platform framework's call order: PreProcess -> Process -> PostProcess.

Mode 1 (auto-data-loading=true):
  Builds a pandas.DataFrame of files under AISHIPBOX_OBS_INPUT with columns
  `file_path` (absolute local path) and `file_name` (relative path). Feeds it
  through each class; whenever a class returns a DataFrame, that becomes the
  input to the next stage. Writes the final DataFrame to
  AISHIPBOX_OBS_OUTPUT/result.jsonl.

Mode 2 (auto-data-loading=false):
  Calls each class with an empty DataFrame. Classes do their own OBS I/O.
  No output file is written by the runner.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


CLASS_ORDER = ("PreProcess", "Process", "PostProcess")
RESERVED_ARG_KEYS = frozenset({
    "obs_input_path", "obs_output_path", "auto_data_loading", "operator_args",
})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obs-input-path", default="obs://input/")
    parser.add_argument("--obs-output-path", default="obs://output/")
    parser.add_argument("--auto-data-loading", default="false")
    parser.add_argument("--operator-args", default="{}")
    args = parser.parse_args()

    try:
        operator_args = json.loads(args.operator_args)
        if not isinstance(operator_args, dict):
            raise ValueError("operator-args 必须是 JSON 对象")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("解析 --operator-args 失败：%s", e)
        return 1

    for key, value in operator_args.items():
        if key in RESERVED_ARG_KEYS:
            logger.warning("manifest argument key 与框架保留字冲突，已忽略：%s", key)
            continue
        setattr(args, key, value)
    if operator_args:
        logger.info("算子参数：%s", operator_args)

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

    auto = str(args.auto_data_loading).lower() in ("1", "true", "yes", "y")

    try:
        import pandas as pd
    except ImportError:
        logger.error(
            "本地运行需要 pandas。请在 program_package/dependency/requirements.txt 中"
            "保留 pandas，并重建虚拟环境：rm -rf .venv && uv venv ..."
        )
        return 1

    df = _build_input_df(pd, auto)

    for cls_name in CLASS_ORDER:
        cls = getattr(module, cls_name, None)
        if cls is None:
            continue
        logger.info("→ %s", cls_name)
        instance = cls(args)
        result = instance(df)
        if isinstance(result, pd.DataFrame):
            df = result

    if auto:
        _write_output_df(pd, df)

    return 0


def _build_input_df(pd, auto: bool):
    if not auto:
        return pd.DataFrame()

    obs_input = os.environ.get("AISHIPBOX_OBS_INPUT")
    if not obs_input:
        logger.warning("AISHIPBOX_OBS_INPUT 未设置，使用空 DataFrame")
        return pd.DataFrame()

    root = Path(obs_input)
    if not root.is_dir():
        logger.warning("输入目录不存在：%s", root)
        return pd.DataFrame()

    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rows.append({
                "file_path": str(p.resolve()),
                "file_name": str(p.relative_to(root)),
            })
    logger.info("构造输入 DataFrame：%d 行 (来自 %s)", len(rows), root)
    return pd.DataFrame(rows, columns=["file_path", "file_name"])


def _write_output_df(pd, df) -> None:
    if not isinstance(df, pd.DataFrame):
        return
    obs_output = os.environ.get("AISHIPBOX_OBS_OUTPUT")
    if not obs_output:
        return
    out_dir = Path(obs_output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "result.jsonl"
    df.to_json(out_path, orient="records", lines=True, force_ascii=False)
    logger.info("已写入 %s（%d 行）", out_path, len(df))


if __name__ == "__main__":
    sys.exit(main())
