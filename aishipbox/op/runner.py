"""op runner — invoked by `aishipbox op run` inside the project venv.

Emulates the platform framework's call order: PreProcess -> Process -> PostProcess.

Classes are instantiated once per run (Process.__init__ may load models /
allocate state). The PreProcess/Process/PostProcess chain is then invoked
once per input file in Mode 1 — per the spec, "每个文件调用一次算子".

Mode 1 (auto-data-loading=true):
  For each file under AISHIPBOX_OBS_INPUT, builds a per-file DataFrame whose
  shape depends on the extension:
    * .jsonl   → pd.read_json(lines=True);  columns = file's own fields
    * .csv     → pd.read_csv;               columns = file's own fields
    * .parquet → pd.read_parquet + system file_path/file_name columns injected
    * other    → 1-row DataFrame with `file_path` + `file_name`
  Runs each through the chain, then concats and writes to
  AISHIPBOX_OBS_OUTPUT/result.<ext> as a mock-only sink, where <ext> mirrors
  the input type (csv→csv, parquet→parquet, else jsonl). The platform decides
  the real output location and format.

Mode 2 (auto-data-loading=false):
  Calls each class once with an empty DataFrame. Classes do their own OBS I/O.
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
RECORD_EXTS = frozenset({".jsonl", ".csv", ".parquet"})


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

    instances = {}
    for cls_name in CLASS_ORDER:
        cls = getattr(module, cls_name, None)
        if cls is not None:
            instances[cls_name] = cls(args)

    if auto:
        try:
            file_dfs = _build_input_file_dfs(pd)
        except ValueError as e:
            logger.error("%s", e)
            return 1
        logger.info("发现 %d 个输入文件，将逐个调用算子链", len(file_dfs))
        # 输出格式对齐输入格式：record 类输入已由 _check_input_uniformity 保证扩展名一致。
        input_ext = Path(file_dfs[0][0]).suffix.lower() if file_dfs else ""
        results = []
        for file_name, file_df in file_dfs:
            df = file_df
            for cls_name in CLASS_ORDER:
                inst = instances.get(cls_name)
                if inst is None:
                    continue
                logger.info("→ %s [%s]", cls_name, file_name)
                result = inst(df)
                if isinstance(result, pd.DataFrame):
                    df = result
                else:
                    logger.warning(
                        "%s [%s] 返回了非 DataFrame (%s)，沿用上一阶段的 DataFrame",
                        cls_name, file_name, type(result).__name__,
                    )
            results.append(df)
        final_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
        _write_output_df(pd, final_df, input_ext)
    else:
        df = pd.DataFrame()
        for cls_name in CLASS_ORDER:
            inst = instances.get(cls_name)
            if inst is None:
                continue
            logger.info("→ %s", cls_name)
            inst(df)

    return 0


def _build_input_file_dfs(pd):
    obs_input = os.environ.get("AISHIPBOX_OBS_INPUT")
    if not obs_input:
        logger.warning("AISHIPBOX_OBS_INPUT 未设置")
        return []

    root = Path(obs_input)
    if not root.is_dir():
        logger.warning("输入目录不存在：%s", root)
        return []

    files = [p for p in sorted(root.rglob("*")) if p.is_file()]
    _check_input_uniformity(files)

    pairs = []
    for p in files:
        df = _read_file_as_df(pd, p, root)
        if df is not None:
            pairs.append((str(p.relative_to(root)), df))
    return pairs


def _check_input_uniformity(files) -> None:
    exts = {p.suffix.lower() for p in files}
    record_exts_used = exts & RECORD_EXTS
    if record_exts_used and len(exts) > 1:
        raise ValueError(
            f"输入目录混合了不同类型的文件 ({sorted(exts)})。当存在 JSONL/CSV/Parquet 时，"
            "所有文件必须为同一类型，否则各文件返回的 DataFrame schema 不一致会破坏结果。"
            "如需多模态输入，请在 manifest 中设置 auto-data-loading=false 并自行读取 OBS 数据。"
        )


def _read_file_as_df(pd, p, root):
    ext = p.suffix.lower()
    if ext == ".jsonl":
        try:
            return pd.read_json(p, lines=True)
        except ValueError as e:
            logger.warning("读取 jsonl 失败 %s：%s", p, e)
            return None
    if ext == ".csv":
        try:
            return pd.read_csv(p)
        except Exception as e:
            logger.warning("读取 csv 失败 %s：%s", p, e)
            return None
    if ext == ".parquet":
        try:
            df = pd.read_parquet(p)
        except ImportError:
            logger.error(
                "读取 parquet 需要 pyarrow，请在项目中执行 `uv add pyarrow` 或更新 "
                "program_package/dependency/requirements.txt"
            )
            return None
        except Exception as e:
            logger.warning("读取 parquet 失败 %s：%s", p, e)
            return None
        df["file_path"] = str(p.resolve())
        df["file_name"] = str(p.relative_to(root))
        return df
    return pd.DataFrame(
        [{"file_path": str(p.resolve()), "file_name": str(p.relative_to(root))}],
        columns=["file_path", "file_name"],
    )


def _write_output_df(pd, df, input_ext="") -> None:
    if not isinstance(df, pd.DataFrame):
        return
    obs_output = os.environ.get("AISHIPBOX_OBS_OUTPUT")
    if not obs_output:
        return
    out_dir = Path(obs_output)
    out_dir.mkdir(parents=True, exist_ok=True)
    # 本地 mock 输出格式对齐输入：csv→csv、parquet→parquet，其余（jsonl 及非 record 输入）→jsonl。
    ext = input_ext if input_ext in (".csv", ".parquet") else ".jsonl"
    out_path = out_dir / f"result{ext}"
    if ext == ".csv":
        df.to_csv(out_path, index=False)
    elif ext == ".parquet":
        df.to_parquet(out_path, index=False)
    else:
        df.to_json(out_path, orient="records", lines=True, force_ascii=False)
    logger.info("已写入 %s（%d 行）", out_path, len(df))


if __name__ == "__main__":
    sys.exit(main())
