"""op runner — invoked by `aishipbox op run` inside the project venv."""

from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obs-input-path", default="obs://input/")
    parser.add_argument("--obs-output-path", default="obs://output/")
    args = parser.parse_args()

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

    proc = module.Process(args)
    proc(None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
