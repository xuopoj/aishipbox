import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "aishipbox", *args],
        cwd=cwd, capture_output=True, text=True,
    )


def test_algo_new_then_pack(tmp_path, require_python):
    require_python("3.9")
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run("algo", "new", "my_algo", "--dir", str(tmp_path), "-t", "basic", "--yes")
    assert r.returncode == 0, r.stderr

    project = tmp_path / "my_algo"
    assert (project / "main.py").exists()
    assert (project / ".venv").exists()
    assert (project / ".aishipbox.toml").exists()
    assert (project / "AGENTS.md").exists()

    r = _run("algo", "pack", cwd=project)
    assert r.returncode == 0, r.stderr
    tar_path = Path(project / "my_algo.tar.gz")
    assert tar_path.exists() or any(project.glob("*.tar.gz"))
