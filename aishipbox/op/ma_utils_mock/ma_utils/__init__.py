"""Local shim for huawei ma_utils used during `aishipbox op run` mock mode.

Mirrors the surface used by the PanguLM custom-operator skeleton:

    import ma_utils as utils
    logger = utils.FileLogger.get_logger()
"""

from __future__ import annotations

import logging
import sys


class FileLogger:
    @staticmethod
    def get_logger(name: str = "process") -> logging.Logger:
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
        return logger
