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


def test_non_interactive_without_template_errors_without_prompting(tmp_path, monkeypatch, capsys):
    # No template, no --yes, non-TTY: must error with guidance, never prompt.
    monkeypatch.setattr("aishipbox.algo.commands.new.stdin_is_interactive", lambda: False)
    monkeypatch.setattr(
        "aishipbox.algo.commands.new._prompt_template",
        lambda: (_ for _ in ()).throw(AssertionError("prompt must not run in non-TTY")),
    )

    rc = new_cmd.execute("my_algo", str(tmp_path), template=None, yes=False)
    assert rc == 2
    out = capsys.readouterr().out
    assert "非交互" in out
    assert "--yes" in out
    assert not (tmp_path / "my_algo").exists()


def test_interactive_tty_runs_template_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr("aishipbox.algo.commands.new.stdin_is_interactive", lambda: True)
    monkeypatch.setattr("aishipbox.algo.commands.new._provision_and_install", lambda *a, **k: None)
    called = {}

    def fake_prompt():
        called["ran"] = True
        return "basic"
    monkeypatch.setattr("aishipbox.algo.commands.new._prompt_template", fake_prompt)

    rc = new_cmd.execute("my_algo", str(tmp_path), template=None, yes=False)
    assert rc == 0
    assert called.get("ran") is True
