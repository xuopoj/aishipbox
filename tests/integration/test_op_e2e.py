import shutil
import subprocess
import sys
import tarfile

import pytest

pytestmark = pytest.mark.integration


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "aishipbox", *args],
        cwd=cwd, capture_output=True, text=True,
    )


def test_op_new_run_pack(tmp_path, require_python):
    require_python("3.10")
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run(
        "op", "new", "my_op",
        "--dir", str(tmp_path),
        "--yes",
        "--id", "my_op",
        "--op-name", "测试算子",
        "--version", "0.0.1",
        "--category", "数据转换",
        "--modal", "IMAGE",
        "--cpu-arch", "ARM",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=false",
        "--skeleton", "transform",
    )
    assert r.returncode == 0, r.stderr

    project = tmp_path / "my_op"
    assert (project / "manifest.yml").exists()
    assert (project / "program_package" / "process.py").exists()
    assert (project / ".venv").exists()
    assert (project / "AGENTS.md").exists()

    (project / "obs_input" / "a.jpg").write_bytes(b"hi")

    r = _run("op", "run", cwd=project)
    assert r.returncode == 0, r.stderr
    assert (project / "obs_output" / "a.jpg").read_bytes() == b"hi"

    r = _run("op", "pack", cwd=project)
    assert r.returncode == 0, r.stderr
    tar_path = project / "program_package" / "my_op.tar"
    assert tar_path.exists()
    with tarfile.open(tar_path, "r:") as tar:
        names = tar.getnames()
    assert "manifest.yml" in names
    assert "process.py" in names
