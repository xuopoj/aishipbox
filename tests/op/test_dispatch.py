from aishipbox import op


def _help_text(argv, capsys):
    # dispatch catches argparse's SystemExit and returns the exit code (0 for --help).
    op.dispatch(argv)
    return capsys.readouterr().out


def test_op_help_lists_all_subcommands(capsys):
    out = _help_text(["--help"], capsys)
    for cmd in ("new", "run", "pack", "debug", "download"):
        assert cmd in out


def test_op_help_describes_workflow(capsys):
    # Top-level help carries a workflow walkthrough so an agent grasps the
    # new -> implement -> run -> pack sequence without reading per-cmd help.
    out = _help_text(["--help"], capsys)
    assert "工作流" in out
    # within the workflow section, the numbered steps appear in order
    wf = out[out.index("工作流"):]
    assert wf.index("1. new") < wf.index("3. run") < wf.index("5. pack")
    assert "process.py" in wf           # the "implement" step is called out
    assert "AGENTS.md" in out           # points at the per-project guide


def test_op_new_help_documents_flags_and_defaults(capsys):
    out = _help_text(["new", "--help"], capsys)
    # key flags carry human-readable descriptions
    assert "ARM" in out and "X86" in out          # cpu-arch allowed values
    assert "TEXT" in out or "IMAGE" in out         # modal allowed values
    assert "默认" in out                            # defaults are shown
    assert "向导" in out or "--yes" in out          # --yes behavior documented


def test_op_download_help_documents_behavior(capsys):
    out = _help_text(["download", "--help"], capsys)
    assert "no-deps" in out or "依赖" in out


def test_dispatch_routes_to_new_with_yes(monkeypatch):
    captured = {}

    def fake_execute(name, parent_dir, flags=None, yes=False, native_tls=False, insecure=False):
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


def test_dispatch_routes_to_download(monkeypatch):
    captured = {}

    def fake_execute(path, package):
        captured["path"] = path
        captured["package"] = package
        return 0
    monkeypatch.setattr("aishipbox.op.commands.dep.execute", fake_execute)

    rc = op.dispatch(["download", "requests"])
    assert rc == 0
    assert captured["package"] == "requests"
    assert captured["path"] == "."
