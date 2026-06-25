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


def _setup_algo(tmp_path):
    (tmp_path / "main.py").write_text("")
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))
    py = tmp_path / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("")
    py.chmod(0o755)


def test_run_debug_ensures_debugpy_in_project_venv(tmp_path, monkeypatch):
    _setup_algo(tmp_path)
    ensured = []
    monkeypatch.setattr(
        "aishipbox.algo.commands.run.ensure_package",
        lambda project_dir, mod, spec, note="": ensured.append((mod, spec)),
    )
    monkeypatch.setattr("aishipbox.algo.commands.run.subprocess.run",
                        lambda cmd, env, cwd: type("R", (), {"returncode": 0})())

    rc = run_cmd.execute(str(tmp_path), host="127.0.0.1", port=8080, debug=True, debug_port=5678)
    assert rc == 0
    assert ensured == [("debugpy", "debugpy>=1.8.0")]


def test_run_no_debug_does_not_touch_debugpy(tmp_path, monkeypatch):
    _setup_algo(tmp_path)
    ensured = []
    monkeypatch.setattr(
        "aishipbox.algo.commands.run.ensure_package",
        lambda project_dir, mod, spec, note="": ensured.append((mod, spec)),
    )
    monkeypatch.setattr("aishipbox.algo.commands.run.subprocess.run",
                        lambda cmd, env, cwd: type("R", (), {"returncode": 0})())

    rc = run_cmd.execute(str(tmp_path), host="127.0.0.1", port=8080, debug=False, debug_port=5678)
    assert rc == 0
    assert ensured == []
