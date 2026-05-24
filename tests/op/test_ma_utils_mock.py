import logging
import sys
from pathlib import Path


def test_file_logger_returns_stdlib_logger(monkeypatch):
    mock_root = Path(__file__).resolve().parents[2] / "aishipbox" / "op" / "ma_utils_mock"
    monkeypatch.syspath_prepend(str(mock_root))
    for k in ("ma_utils",):
        sys.modules.pop(k, None)

    import ma_utils as utils

    logger = utils.FileLogger.get_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.handlers, "logger should have at least one handler installed"

    # Repeated calls don't keep stacking handlers.
    n = len(logger.handlers)
    utils.FileLogger.get_logger()
    assert len(logger.handlers) == n


def test_file_logger_custom_name(monkeypatch):
    mock_root = Path(__file__).resolve().parents[2] / "aishipbox" / "op" / "ma_utils_mock"
    monkeypatch.syspath_prepend(str(mock_root))
    for k in ("ma_utils",):
        sys.modules.pop(k, None)

    import ma_utils as utils

    a = utils.FileLogger.get_logger("alpha")
    b = utils.FileLogger.get_logger("beta")
    assert a.name == "alpha"
    assert b.name == "beta"
    assert a is not b
