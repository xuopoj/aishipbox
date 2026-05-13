import json
from aishipbox.op.commands import debug as debug_cmd


def test_writes_launch_json(tmp_path):
    rc = debug_cmd.execute(str(tmp_path))
    assert rc == 0
    cfg = json.loads((tmp_path / ".vscode" / "launch.json").read_text())
    names = [c["name"] for c in cfg["configurations"]]
    assert any("Op" in n for n in names)
