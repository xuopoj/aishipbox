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
    assert "my_op/manifest.yml" in names
    assert "my_op/program_package/process.py" in names


def test_op_mode1_dataframe_chain(tmp_path, require_python):
    """auto-data-loading=true: framework builds a DataFrame of obs_input files
    and chains it through PreProcess -> Process -> PostProcess. Each stage
    here marks the rows so we can verify the call order in the result."""
    require_python("3.10")
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run(
        "op", "new", "my_op",
        "--dir", str(tmp_path),
        "--yes",
        "--id", "my_op",
        "--op-name", "mode1",
        "--version", "0.0.1",
        "--category", "数据转换",
        "--modal", "IMAGE",
        "--cpu-arch", "ARM",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=true",
        "--skeleton", "blank",
    )
    assert r.returncode == 0, r.stderr

    project = tmp_path / "my_op"
    (project / "program_package" / "process.py").write_text(
        "import pandas as pd\n"
        "\n"
        "class PreProcess:\n"
        "    def __init__(self, args): pass\n"
        "    def __call__(self, df):\n"
        "        df = df.copy(); df['stages'] = 'pre'; return df\n"
        "\n"
        "class Process:\n"
        "    def __init__(self, args): pass\n"
        "    def __call__(self, df):\n"
        "        df = df.copy(); df['stages'] = df['stages'] + '|proc'; return df\n"
        "\n"
        "class PostProcess:\n"
        "    def __init__(self, args): pass\n"
        "    def __call__(self, df):\n"
        "        df = df.copy(); df['stages'] = df['stages'] + '|post'; return df\n",
        encoding="utf-8",
    )
    (project / "obs_input" / "a.txt").write_bytes(b"hello")
    (project / "obs_input" / "b.txt").write_bytes(b"world")

    r = _run("op", "run", cwd=project)
    assert r.returncode == 0, r.stderr

    result = project / "obs_output" / "result.jsonl"
    assert result.exists(), r.stdout + r.stderr
    lines = [l for l in result.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
    for l in lines:
        assert "pre|proc|post" in l
        assert "file_path" in l and "file_name" in l
