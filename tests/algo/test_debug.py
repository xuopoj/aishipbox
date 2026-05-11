import json

from aishipbox.algo.commands import debug as debug_cmd


def test_debug_writes_launch_json(tmp_path):
    rc = debug_cmd.execute(str(tmp_path))
    assert rc == 0
    launch = tmp_path / ".vscode" / "launch.json"
    assert launch.exists()
    cfg = json.loads(launch.read_text())
    names = [c["name"] for c in cfg["configurations"]]
    assert any("Algo" in n for n in names)
