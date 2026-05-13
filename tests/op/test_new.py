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
    assert (project / "AGENTS.md").exists()
    assert (project / ".aishipbox.toml").exists()


def test_new_yes_missing_required_errors(tmp_path):
    rc = new_cmd.execute(
        name="my_op",
        parent_dir=str(tmp_path),
        flags={"id": "my_op"},
        yes=True,
    )
    assert rc == 2
