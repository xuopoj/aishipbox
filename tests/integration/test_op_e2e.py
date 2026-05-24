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


def test_op_manifest_arguments_reach_process(tmp_path, require_python):
    """manifest.arguments defaults reach Process via args.<key>."""
    require_python("3.10")
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run(
        "op", "new", "args_op",
        "--dir", str(tmp_path),
        "--yes",
        "--id", "args_op",
        "--op-name", "args_op",
        "--version", "0.0.1",
        "--category", "数据转换",
        "--modal", "IMAGE",
        "--cpu-arch", "ARM",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=true",
        "--skeleton", "blank",
    )
    assert r.returncode == 0, r.stderr

    project = tmp_path / "args_op"
    import yaml
    manifest_path = project / "manifest.yml"
    doc = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    doc["arguments"] = [
        {"key": "threshold", "name": "阈值", "type": "FLOAT", "between": False, "default": 0.5},
        {"key": "label", "name": "标签", "type": "STRING", "default": "hello"},
    ]
    manifest_path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    (project / "program_package" / "process.py").write_text(
        "import json\n"
        "import os\n"
        "import pandas as pd\n"
        "\n"
        "class Process:\n"
        "    def __init__(self, args):\n"
        "        self.args = args\n"
        "    def __call__(self, df):\n"
        "        out = pd.DataFrame([{\n"
        "            'threshold': self.args.threshold,\n"
        "            'label': self.args.label,\n"
        "        }])\n"
        "        return out\n",
        encoding="utf-8",
    )
    (project / "obs_input" / "x.txt").write_bytes(b"x")

    r = _run("op", "run", cwd=project)
    assert r.returncode == 0, r.stderr

    result = project / "obs_output" / "result.jsonl"
    assert result.exists(), r.stdout + r.stderr
    import json as _json
    rows = [_json.loads(l) for l in result.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert rows == [{"threshold": 0.5, "label": "hello"}]


def test_op_mode1_per_file_invocation(tmp_path, require_python):
    """auto-data-loading=true: chain runs once per input file with a 1-row
    DataFrame. Operator asserts len(df) == 1; would fail under bulk invocation."""
    require_python("3.10")
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run(
        "op", "new", "perfile_op",
        "--dir", str(tmp_path),
        "--yes",
        "--id", "perfile_op",
        "--op-name", "perfile",
        "--version", "0.0.1",
        "--category", "数据转换",
        "--modal", "IMAGE",
        "--cpu-arch", "ARM",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=true",
        "--skeleton", "blank",
    )
    assert r.returncode == 0, r.stderr

    project = tmp_path / "perfile_op"
    (project / "program_package" / "process.py").write_text(
        "class Process:\n"
        "    def __init__(self, args):\n"
        "        self.call_count = 0\n"
        "    def __call__(self, df):\n"
        "        assert len(df) == 1, f'expected per-file df, got {len(df)} rows'\n"
        "        self.call_count += 1\n"
        "        df = df.copy(); df['n'] = self.call_count; return df\n",
        encoding="utf-8",
    )
    (project / "obs_input" / "a.txt").write_bytes(b"a")
    (project / "obs_input" / "b.txt").write_bytes(b"b")
    (project / "obs_input" / "c.txt").write_bytes(b"c")

    r = _run("op", "run", cwd=project)
    assert r.returncode == 0, r.stderr

    import json as _json
    result = project / "obs_output" / "result.jsonl"
    rows = [_json.loads(l) for l in result.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) == 3
    # Process instance is reused across files → call_count increments 1, 2, 3.
    assert [r["n"] for r in rows] == [1, 2, 3]


def test_op_mode1_jsonl_input_exposes_file_columns(tmp_path, require_python):
    """JSONL inputs: framework passes each file's records as the DataFrame
    with the file's own columns (not file_path/file_name)."""
    require_python("3.10")
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run(
        "op", "new", "jsonl_op",
        "--dir", str(tmp_path),
        "--yes",
        "--id", "jsonl_op", "--op-name", "jsonl", "--version", "0.0.1",
        "--category", "数据转换", "--modal", "TEXT", "--cpu-arch", "ARM",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=true", "--skeleton", "blank",
    )
    assert r.returncode == 0, r.stderr

    project = tmp_path / "jsonl_op"
    (project / "program_package" / "process.py").write_text(
        "class Process:\n"
        "    def __init__(self, args): pass\n"
        "    def __call__(self, df):\n"
        "        assert list(df.columns) == ['id', 'text'], f'got {list(df.columns)}'\n"
        "        df = df.copy(); df['n_chars'] = df['text'].str.len(); return df\n",
        encoding="utf-8",
    )
    (project / "obs_input" / "samples.jsonl").write_text(
        '{"id": 1, "text": "hello"}\n{"id": 2, "text": "world!"}\n',
        encoding="utf-8",
    )

    r = _run("op", "run", cwd=project)
    assert r.returncode == 0, r.stderr

    import json as _json
    rows = [_json.loads(l) for l in (project / "obs_output" / "result.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert rows == [
        {"id": 1, "text": "hello", "n_chars": 5},
        {"id": 2, "text": "world!", "n_chars": 6},
    ]


def test_op_mode1_csv_input_exposes_file_columns(tmp_path, require_python):
    """CSV inputs: same per-file shape as JSONL — file's own columns."""
    require_python("3.10")
    if not shutil.which("uv"):
        pytest.skip("uv not available")

    r = _run(
        "op", "new", "csv_op",
        "--dir", str(tmp_path),
        "--yes",
        "--id", "csv_op", "--op-name", "csv", "--version", "0.0.1",
        "--category", "数据转换", "--modal", "TEXT", "--cpu-arch", "ARM",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=true", "--skeleton", "blank",
    )
    assert r.returncode == 0, r.stderr

    project = tmp_path / "csv_op"
    (project / "program_package" / "process.py").write_text(
        "class Process:\n"
        "    def __init__(self, args): pass\n"
        "    def __call__(self, df):\n"
        "        assert list(df.columns) == ['name', 'score'], f'got {list(df.columns)}'\n"
        "        df = df.copy(); df['rank'] = df['score'].rank(ascending=False).astype(int); return df\n",
        encoding="utf-8",
    )
    (project / "obs_input" / "scores.csv").write_text(
        "name,score\nalice,90\nbob,75\n",
        encoding="utf-8",
    )

    r = _run("op", "run", cwd=project)
    assert r.returncode == 0, r.stderr

    import json as _json
    rows = [_json.loads(l) for l in (project / "obs_output" / "result.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert rows == [
        {"name": "alice", "score": 90, "rank": 1},
        {"name": "bob", "score": 75, "rank": 2},
    ]


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
