from aishipbox import algo


def test_dispatch_routes_to_new(monkeypatch):
    called = {}
    def fake_execute(name, parent_dir, template=None, yes=False):
        called["name"] = name
        called["template"] = template
        return 0
    monkeypatch.setattr("aishipbox.algo.commands.new.execute", fake_execute)
    rc = algo.dispatch(["new", "my_svc", "--template", "basic", "--yes"])
    assert rc == 0
    assert called["name"] == "my_svc"
    assert called["template"] == "basic"


def test_dispatch_unknown_command():
    rc = algo.dispatch(["bogus"])
    assert rc == 2
