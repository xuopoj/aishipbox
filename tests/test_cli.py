import pytest

from aishipbox.cli import main


def test_no_args_prints_help(capsys):
    with pytest.raises(SystemExit):
        main([])
    captured = capsys.readouterr()
    assert "aishipbox" in captured.out.lower() or "aishipbox" in captured.err.lower()


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "0.1.0" in captured.out


def test_algo_subcommand_routes(monkeypatch):
    called = {}

    def fake_dispatch(argv):
        called["algo"] = argv
        return 0

    monkeypatch.setattr("aishipbox.algo.dispatch", fake_dispatch, raising=False)
    rc = main(["algo", "new", "x"])
    assert rc == 0
    assert called["algo"] == ["new", "x"]


def test_op_subcommand_routes(monkeypatch):
    called = {}

    def fake_dispatch(argv):
        called["op"] = argv
        return 0

    monkeypatch.setattr("aishipbox.op.dispatch", fake_dispatch, raising=False)
    rc = main(["op", "new", "y"])
    assert rc == 0
    assert called["op"] == ["new", "y"]
