from aishipbox.algo.commands import new as new_cmd


def test_rejects_hyphen_in_name(tmp_path):
    rc = new_cmd.execute("my-algo", str(tmp_path), template="basic", yes=True)
    assert rc == 1


def test_rejects_existing_dir(tmp_path):
    (tmp_path / "my_algo").mkdir()
    rc = new_cmd.execute("my_algo", str(tmp_path), template="basic", yes=True)
    assert rc == 1


def test_scaffolds_files(tmp_path, monkeypatch):
    monkeypatch.setattr("aishipbox.algo.commands.new._provision_and_install", lambda *a, **k: None)

    rc = new_cmd.execute("my_algo", str(tmp_path), template="basic", yes=True)
    assert rc == 0

    project = tmp_path / "my_algo"
    assert (project / "main.py").exists()
    assert (project / "requirements.txt").exists()
    assert (project / ".aishipbox.toml").exists()
    assert (project / "AGENTS.md").exists()
