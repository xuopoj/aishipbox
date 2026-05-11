"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def tmp_project_dir(tmp_path):
    """A fresh tmp directory for filesystem tests."""
    return tmp_path
