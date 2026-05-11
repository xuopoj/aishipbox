from aishipbox.op.commands import run as run_cmd
from aishipbox.core.config import ProjectConfig, write_project_config


def _setup_op_project(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="op", runtime="3.10"))
    (tmp_path / "program_package").mkdir()
    (tmp_path / "program_package" / "process.py").write_text("class Process: pass")
    (tmp_path / "obs_input").mkdir()
    (tmp_path / "obs_output").mkdir()
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


def test_run_obs_missing_creds_fails(tmp_path):
    project = _setup_op_project(tmp_path)
    rc = run_cmd.execute(str(project), obs=True, debug=False)
    assert rc == 1
