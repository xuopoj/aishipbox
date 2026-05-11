from aishipbox.algo.commands import run as run_cmd
from aishipbox.core.config import ProjectConfig, write_project_config


def test_run_missing_main_returns_error(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))
    rc = run_cmd.execute(str(tmp_path), host="127.0.0.1", port=8080, debug=False, debug_port=5678)
    assert rc == 1


def test_run_resolves_project_python(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text("")
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))
    fake_py = tmp_path / ".venv" / "bin" / "python"
    fake_py.parent.mkdir(parents=True)
    fake_py.write_text("")
    fake_py.chmod(0o755)

    calls = {}
    def fake_run(cmd, env, cwd):
        calls["cmd"] = cmd
        calls["env"] = env
        class R: returncode = 0
        return R()
    monkeypatch.setattr("aishipbox.algo.commands.run.subprocess.run", fake_run)

    rc = run_cmd.execute(str(tmp_path), host="127.0.0.1", port=8080, debug=False, debug_port=5678)
    assert rc == 0
    assert str(fake_py) in calls["cmd"][0]
    assert calls["env"]["ALGO_HOST"] == "127.0.0.1"
    assert calls["env"]["ALGO_PORT"] == "8080"
