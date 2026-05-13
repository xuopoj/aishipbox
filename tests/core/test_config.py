import pytest
from pathlib import Path

from aishipbox.core.config import (
    HOSTED_RUNTIMES,
    SCHEMA_VERSION,
    ProjectConfig,
    find_project_root,
    write_project_config,
)


def test_hosted_runtimes_defined():
    assert HOSTED_RUNTIMES["algo"] == "3.9"
    assert HOSTED_RUNTIMES["op"] == "3.10"


def test_write_and_read_roundtrip(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="op", runtime="3.10"))

    config_file = tmp_path / ".aishipbox.toml"
    assert config_file.exists()

    loaded = ProjectConfig.from_path(tmp_path)
    assert loaded.type == "op"
    assert loaded.runtime == "3.10"
    assert loaded.schema_version == SCHEMA_VERSION


def test_find_project_root_walks_up(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)

    assert find_project_root(nested) == tmp_path


def test_find_project_root_returns_none_when_missing(tmp_path):
    assert find_project_root(tmp_path) is None
