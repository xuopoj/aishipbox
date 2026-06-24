from aishipbox.core.config import PLATFORM_PRESET_PINS
from aishipbox.op.commands import new as new_cmd


def test_new_yes_full_flags_creates_project(tmp_path, monkeypatch):
    monkeypatch.setattr("aishipbox.op.commands.new._provision_and_install", lambda *a, **k: None)

    rc = new_cmd.execute(
        name="my_op",
        parent_dir=str(tmp_path),
        flags={
            "id": "my_op",
            "name": "示例算子",
            "description": "demo",
            "author": "tester",
            "version": "0.0.1",
            "category": "数据转换",
            "modal": ["IMAGE"],
            "format": ["JPG"],
            "language": ["zh"],
            "cpu_arch": ["ARM"],
            "cpu": 1,
            "memory": 2048,
            "npu": 0,
            "auto_data_loading": False,
            "skeleton": "transform",
        },
        yes=True,
    )
    assert rc == 0
    project = tmp_path / "my_op"
    assert (project / "manifest.yml").exists()
    assert (project / "program_package" / "process.py").exists()
    assert (project / "program_package" / "dependency" / "requirements.txt").exists()
    assert not (project / "program_package" / "requirements.txt").exists()
    assert (project / "AGENTS.md").exists()
    assert (project / ".aishipbox.toml").exists()

    process_src = (project / "program_package" / "process.py").read_text(encoding="utf-8")
    assert "class Process" in process_src
    assert "PreProcess" in process_src
    assert "PostProcess" in process_src

    install_example = project / "program_package" / "install.sh.example"
    assert install_example.exists()
    assert "find-links=./dependency" in install_example.read_text(encoding="utf-8")
    assert not (project / "program_package" / "install.sh").exists()

    # The shipped requirements.txt must NOT list any platform-preinstalled
    # package. Listing them would force the platform's `pip install --no-index`
    # to look for wheels in the empty dependency/ dir and fail.
    req_text = (project / "program_package" / "dependency" / "requirements.txt").read_text(encoding="utf-8")
    req_pkgs = [
        l.strip().split("==")[0].split(">=")[0].split("<")[0]
        for l in req_text.splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    preset_names = {p.split("==")[0] for p in PLATFORM_PRESET_PINS}
    leaked = preset_names & set(req_pkgs)
    assert not leaked, f"platform-preinstalled packages leaked into shipped requirements.txt: {leaked}"


def test_new_yes_missing_required_errors(tmp_path):
    rc = new_cmd.execute(
        name="my_op",
        parent_dir=str(tmp_path),
        flags={"id": "my_op"},
        yes=True,
    )
    assert rc == 2


def test_new_non_interactive_without_yes_errors_without_prompting(tmp_path, monkeypatch, capsys):
    # No --yes and a non-TTY environment: must error with guidance, never prompt.
    monkeypatch.setattr("aishipbox.op.commands.new.stdin_is_interactive", lambda: False)
    monkeypatch.setattr(
        "aishipbox.op.commands.new.wizard.run_wizard",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("wizard must not run in non-TTY")),
    )

    rc = new_cmd.execute(name="my_op", parent_dir=str(tmp_path), flags={}, yes=False)
    assert rc == 2
    out = capsys.readouterr().out
    assert "非交互" in out
    assert "--yes" in out
    assert not (tmp_path / "my_op").exists()


def test_new_interactive_tty_runs_wizard(tmp_path, monkeypatch):
    # TTY + no --yes: wizard runs as before.
    monkeypatch.setattr("aishipbox.op.commands.new.stdin_is_interactive", lambda: True)
    monkeypatch.setattr("aishipbox.op.commands.new._provision_and_install", lambda *a, **k: None)
    called = {}

    def fake_wizard(default_id):
        called["ran"] = True
        return {
            "id": "my_op", "name": "示例", "version": "0.0.1",
            "category": "数据转换", "modal": ["IMAGE"], "format": [], "language": ["zh"],
            "cpu_arch": ["ARM"], "cpu": 1, "memory": 2048, "npu": 0,
            "auto_data_loading": False, "skeleton": "transform",
        }
    monkeypatch.setattr("aishipbox.op.commands.new.wizard.run_wizard", fake_wizard)

    rc = new_cmd.execute(name="my_op", parent_dir=str(tmp_path), flags={}, yes=False)
    assert rc == 0
    assert called.get("ran") is True
