from pathlib import Path

from aishipbox.op.commands import dep as dep_cmd
from aishipbox.core.config import ProjectConfig, write_project_config
from aishipbox.op.manifest import Manifest, Resource, render_manifest


class _FakeCompletedProcess:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def _setup_op(tmp_path, cpu_arch=("ARM",)):
    write_project_config(tmp_path, ProjectConfig(type="op", runtime="3.10"))
    (tmp_path / "program_package" / "dependency").mkdir(parents=True)
    (tmp_path / "program_package" / "dependency" / "requirements.txt").write_text("", encoding="utf-8")
    m = Manifest(
        id="my_op", name="x", description="", author="", version="0.0.1",
        category="数据转换", modal=["IMAGE"], format=["JSONL"], language=["zh"],
        cpu_arch=list(cpu_arch), resources=[Resource(cpu=1, memory=2048, npu=0)],
        auto_data_loading=False, arguments=[],
    )
    (tmp_path / "manifest.yml").write_text(render_manifest(m), encoding="utf-8")
    return tmp_path


def test_dep_download_rejects_platform_preset_package(tmp_path):
    p = _setup_op(tmp_path)
    rc = dep_cmd.execute(str(p), "pandas")
    assert rc == 1
    req = (p / "program_package" / "dependency" / "requirements.txt").read_text(encoding="utf-8")
    assert "pandas" not in req


def test_dep_download_missing_manifest_errors(tmp_path):
    rc = dep_cmd.execute(str(tmp_path), "requests")
    assert rc == 1


def test_dep_download_writes_wheel_and_requirements(tmp_path, monkeypatch, capsys):
    p = _setup_op(tmp_path)
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(dep_cmd, "python_executable", lambda project: Path("/fake/python"))

    def fake_run(cmd, capture_output, text):
        dep_dir = Path(cmd[cmd.index("--dest") + 1])
        (dep_dir / "requests-2.34.2-py3-none-any.whl").write_bytes(b"")
        return _FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(dep_cmd.subprocess, "run", fake_run)

    rc = dep_cmd.execute(str(p), "requests")
    assert rc == 0

    dep_dir = p / "program_package" / "dependency"
    assert (dep_dir / "requests-2.34.2-py3-none-any.whl").exists()
    req = (dep_dir / "requirements.txt").read_text(encoding="utf-8")
    assert "requests==2.34.2" in req
    captured = capsys.readouterr()
    assert "requests==2.34.2" in captured.out


def test_dep_download_multi_arch_binary_wheels_succeeds(tmp_path, monkeypatch):
    p = _setup_op(tmp_path, cpu_arch=("ARM", "X86"))
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(dep_cmd, "python_executable", lambda project: Path("/fake/python"))

    def fake_run(cmd, capture_output, text):
        dep_dir = Path(cmd[cmd.index("--dest") + 1])
        platform_tag = cmd[cmd.index("--platform") + 1]
        (dep_dir / f"pillow-10.4.0-cp310-cp310-{platform_tag}.whl").write_bytes(b"")
        return _FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(dep_cmd.subprocess, "run", fake_run)

    rc = dep_cmd.execute(str(p), "pillow")
    assert rc == 0

    dep_dir = p / "program_package" / "dependency"
    assert (dep_dir / "pillow-10.4.0-cp310-cp310-manylinux2014_aarch64.whl").exists()
    assert (dep_dir / "pillow-10.4.0-cp310-cp310-manylinux2014_x86_64.whl").exists()
    req = (dep_dir / "requirements.txt").read_text(encoding="utf-8")
    assert req.count("pillow==10.4.0") == 1


def test_dep_download_multi_arch_pure_python_wheel_succeeds(tmp_path, monkeypatch):
    # A pure-Python wheel (py3-none-any) satisfies both archs, so the second
    # pip download is a no-op that writes no new file. The command must still
    # succeed and record the version, not falsely report "wheel not found".
    p = _setup_op(tmp_path, cpu_arch=("ARM", "X86"))
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(dep_cmd, "python_executable", lambda project: Path("/fake/python"))

    def fake_run(cmd, capture_output, text):
        dep_dir = Path(cmd[cmd.index("--dest") + 1])
        # identical filename regardless of --platform; second call is a no-op
        (dep_dir / "requests-2.34.2-py3-none-any.whl").write_bytes(b"")
        return _FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(dep_cmd.subprocess, "run", fake_run)

    rc = dep_cmd.execute(str(p), "requests")
    assert rc == 0

    dep_dir = p / "program_package" / "dependency"
    assert (dep_dir / "requests-2.34.2-py3-none-any.whl").exists()
    req = (dep_dir / "requirements.txt").read_text(encoding="utf-8")
    assert req.count("requests==2.34.2") == 1


def test_dep_download_multi_arch_version_mismatch_errors(tmp_path, monkeypatch):
    p = _setup_op(tmp_path, cpu_arch=("ARM", "X86"))
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(dep_cmd, "python_executable", lambda project: Path("/fake/python"))

    def fake_run(cmd, capture_output, text):
        dep_dir = Path(cmd[cmd.index("--dest") + 1])
        platform_tag = cmd[cmd.index("--platform") + 1]
        version = "2.34.2" if "aarch64" in platform_tag else "2.34.1"
        (dep_dir / f"requests-{version}-py3-none-{platform_tag}.whl").write_bytes(b"")
        return _FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(dep_cmd.subprocess, "run", fake_run)

    rc = dep_cmd.execute(str(p), "requests")
    assert rc == 1


def test_dep_download_replaces_existing_requirements_line(tmp_path, monkeypatch):
    p = _setup_op(tmp_path)
    (p / "program_package" / "dependency" / "requirements.txt").write_text(
        "# comment\nrequests==2.0.0\nother==1.0.0\n", encoding="utf-8"
    )
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(dep_cmd, "python_executable", lambda project: Path("/fake/python"))

    def fake_run(cmd, capture_output, text):
        dep_dir = Path(cmd[cmd.index("--dest") + 1])
        (dep_dir / "requests-2.34.2-py3-none-any.whl").write_bytes(b"")
        return _FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(dep_cmd.subprocess, "run", fake_run)

    rc = dep_cmd.execute(str(p), "requests")
    assert rc == 0

    req = (p / "program_package" / "dependency" / "requirements.txt").read_text(encoding="utf-8")
    assert req.count("requests==") == 1
    assert "requests==2.34.2" in req
    assert "other==1.0.0" in req
    assert "# comment" in req


def test_dep_download_pip_failure_propagates_error(tmp_path, monkeypatch):
    p = _setup_op(tmp_path)
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(dep_cmd, "python_executable", lambda project: Path("/fake/python"))
    monkeypatch.setattr(
        dep_cmd.subprocess, "run",
        lambda *a, **k: _FakeCompletedProcess(returncode=1, stderr="No matching distribution"),
    )

    rc = dep_cmd.execute(str(p), "nonexistent-package-xyz")
    assert rc == 1
    req = (p / "program_package" / "dependency" / "requirements.txt").read_text(encoding="utf-8")
    assert "nonexistent" not in req


def test_dep_download_rejects_preset_package_case_insensitively(tmp_path, monkeypatch, capsys):
    # Guard against false passes: make sure rejection happens at the preset
    # check, before any venv/subprocess work. pip_install raising would also
    # return 1, so assert on the preset message specifically.
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not reach pip_install")))
    p = _setup_op(tmp_path)
    for spelling in ("Pandas", "NumPy", "PyArrow"):
        rc = dep_cmd.execute(str(p), spelling)
        assert rc == 1, f"{spelling} should be rejected as a platform preset"
        assert "预置" in capsys.readouterr().out


def test_dep_download_empty_cpu_arch_errors_cleanly(tmp_path, monkeypatch):
    p = _setup_op(tmp_path, cpu_arch=())
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(dep_cmd, "python_executable", lambda project: Path("/fake/python"))
    # no subprocess.run mock: must error before ever shelling out
    rc = dep_cmd.execute(str(p), "requests")
    assert rc == 1


def test_dep_download_normalizes_name_against_existing_line(tmp_path, monkeypatch):
    # A prior line uses the hyphenated spelling; re-downloading with the
    # underscore spelling must update that line, not add a duplicate.
    p = _setup_op(tmp_path)
    (p / "program_package" / "dependency" / "requirements.txt").write_text(
        "typing-extensions==4.0.0\n", encoding="utf-8"
    )
    monkeypatch.setattr(dep_cmd, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(dep_cmd, "python_executable", lambda project: Path("/fake/python"))

    def fake_run(cmd, capture_output, text):
        dep_dir = Path(cmd[cmd.index("--dest") + 1])
        (dep_dir / "typing_extensions-4.12.2-py3-none-any.whl").write_bytes(b"")
        return _FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(dep_cmd.subprocess, "run", fake_run)

    rc = dep_cmd.execute(str(p), "typing_extensions")
    assert rc == 0
    req = (p / "program_package" / "dependency" / "requirements.txt").read_text(encoding="utf-8")
    # exactly one line for this dist regardless of - vs _ spelling
    assert req.lower().replace("_", "-").count("typing-extensions==") == 1
    assert "4.12.2" in req
    assert "4.0.0" not in req
