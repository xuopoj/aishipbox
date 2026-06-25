import json

from aishipbox.op.commands import run as run_cmd
from aishipbox.core.config import ProjectConfig, write_project_config
from aishipbox.op.manifest import Manifest, Resource, render_manifest


def _write_manifest(tmp_path, auto_data_loading: bool, arguments=None):
    m = Manifest(
        id="my_op", name="x", description="", author="", version="0.0.1",
        category="数据转换", modal=["IMAGE"], format=[], language=["zh"],
        cpu_arch=["ARM"], resources=[Resource(cpu=1, memory=2048, npu=0)],
        auto_data_loading=auto_data_loading, arguments=arguments or [],
    )
    (tmp_path / "manifest.yml").write_text(render_manifest(m), encoding="utf-8")


def _setup_op_project(tmp_path, auto_data_loading: bool = False, arguments=None):
    write_project_config(tmp_path, ProjectConfig(type="op", runtime="3.10"))
    (tmp_path / "program_package").mkdir()
    (tmp_path / "program_package" / "process.py").write_text("class Process: pass")
    (tmp_path / "obs_input").mkdir()
    (tmp_path / "obs_output").mkdir()
    _write_manifest(tmp_path, auto_data_loading, arguments=arguments)
    py_bin = tmp_path / ".venv" / "bin"
    py_bin.mkdir(parents=True)
    py = py_bin / "python"
    py.write_text("")
    py.chmod(0o755)
    return tmp_path


def test_run_mock_sets_env(tmp_path, monkeypatch):
    project = _setup_op_project(tmp_path)
    captured = {}

    def fake_run(cmd, env, cwd):
        captured.update(env=env, cmd=cmd)
        class R: returncode = 0
        return R()
    monkeypatch.setattr("aishipbox.op.commands.run.subprocess.run", fake_run)

    rc = run_cmd.execute(str(project), obs=False, debug=False)
    assert rc == 0
    assert captured["env"]["AISHIPBOX_OBS_INPUT"] == str(project / "obs_input")
    assert captured["env"]["AISHIPBOX_OBS_OUTPUT"] == str(project / "obs_output")
    assert "moxing_mock" in captured["env"]["PYTHONPATH"]
    assert "--auto-data-loading" in captured["cmd"]
    idx = captured["cmd"].index("--auto-data-loading")
    assert captured["cmd"][idx + 1] == "false"


def test_run_passes_auto_data_loading_true(tmp_path, monkeypatch):
    project = _setup_op_project(tmp_path, auto_data_loading=True)
    captured = {}

    def fake_run(cmd, env, cwd):
        captured.update(cmd=cmd)
        class R: returncode = 0
        return R()
    monkeypatch.setattr("aishipbox.op.commands.run.subprocess.run", fake_run)

    rc = run_cmd.execute(str(project), obs=False, debug=False)
    assert rc == 0
    idx = captured["cmd"].index("--auto-data-loading")
    assert captured["cmd"][idx + 1] == "true"


def test_run_debug_ensures_debugpy_in_project_venv(tmp_path, monkeypatch):
    project = _setup_op_project(tmp_path)
    ensured = []
    monkeypatch.setattr(
        "aishipbox.op.commands.run.ensure_package",
        lambda project_dir, mod, spec, note="": ensured.append((mod, spec)),
    )
    captured = {}

    def fake_run(cmd, env, cwd):
        captured["cmd"] = cmd
        class R: returncode = 0
        return R()
    monkeypatch.setattr("aishipbox.op.commands.run.subprocess.run", fake_run)

    rc = run_cmd.execute(str(project), obs=False, debug=True)
    assert rc == 0
    assert ensured == [("debugpy", "debugpy>=1.8.0")]      # installed before launch
    assert "-m" in captured["cmd"] and "debugpy" in captured["cmd"]


def test_run_no_debug_does_not_touch_debugpy(tmp_path, monkeypatch):
    project = _setup_op_project(tmp_path)
    ensured = []
    monkeypatch.setattr(
        "aishipbox.op.commands.run.ensure_package",
        lambda project_dir, mod, spec, note="": ensured.append((mod, spec)),
    )
    monkeypatch.setattr("aishipbox.op.commands.run.subprocess.run",
                        lambda cmd, env, cwd: type("R", (), {"returncode": 0})())

    rc = run_cmd.execute(str(project), obs=False, debug=False)
    assert rc == 0
    assert ensured == []           # non-debug run never installs debugpy


def test_run_obs_missing_creds_fails(tmp_path):
    project = _setup_op_project(tmp_path)
    rc = run_cmd.execute(str(project), obs=True, debug=False)
    assert rc == 1


def test_run_passes_operator_args_from_manifest(tmp_path, monkeypatch):
    arguments = [
        {"key": "threshold", "name": "阈值", "type": "FLOAT", "between": False, "default": 0.5},
        {"key": "label", "name": "标签", "type": "STRING", "default": "默认"},
        {"key": "missing_default", "name": "无默认", "type": "STRING"},
    ]
    project = _setup_op_project(tmp_path, arguments=arguments)
    captured = {}

    def fake_run(cmd, env, cwd):
        captured.update(cmd=cmd)
        class R: returncode = 0
        return R()
    monkeypatch.setattr("aishipbox.op.commands.run.subprocess.run", fake_run)

    rc = run_cmd.execute(str(project), obs=False, debug=False)
    assert rc == 0
    assert "--operator-args" in captured["cmd"]
    idx = captured["cmd"].index("--operator-args")
    payload = json.loads(captured["cmd"][idx + 1])
    assert payload == {"threshold": 0.5, "label": "默认", "missing_default": None}


def test_run_operator_args_empty_when_no_arguments(tmp_path, monkeypatch):
    project = _setup_op_project(tmp_path)
    captured = {}

    def fake_run(cmd, env, cwd):
        captured.update(cmd=cmd)
        class R: returncode = 0
        return R()
    monkeypatch.setattr("aishipbox.op.commands.run.subprocess.run", fake_run)

    rc = run_cmd.execute(str(project), obs=False, debug=False)
    assert rc == 0
    idx = captured["cmd"].index("--operator-args")
    assert json.loads(captured["cmd"][idx + 1]) == {}
