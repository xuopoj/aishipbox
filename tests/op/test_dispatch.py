from aishipbox import op


def test_dispatch_routes_to_new_with_yes(monkeypatch):
    captured = {}

    def fake_execute(name, parent_dir, flags=None, yes=False):
        captured["name"] = name
        captured["yes"] = yes
        captured["flags"] = flags
        return 0
    monkeypatch.setattr("aishipbox.op.commands.new.execute", fake_execute)

    rc = op.dispatch([
        "new", "my_op", "--yes",
        "--id", "my_op", "--op-name", "示例",
        "--version", "0.0.1",
        "--category", "数据转换",
        "--modal", "IMAGE",
        "--cpu-arch", "ARM",
        "--cpu", "1", "--memory", "2048", "--npu", "0",
        "--auto-data-loading=false",
        "--skeleton", "transform",
    ])
    assert rc == 0
    assert captured["name"] == "my_op"
    assert captured["yes"] is True
    assert captured["flags"]["category"] == "数据转换"
    assert captured["flags"]["skeleton"] == "transform"
    assert captured["flags"]["name"] == "示例"


def test_dispatch_unknown_command():
    assert op.dispatch(["bogus"]) == 2
