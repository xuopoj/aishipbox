import tarfile
from pathlib import Path

from aishipbox.algo.commands import pack as pack_cmd
from aishipbox.core.config import ProjectConfig, write_project_config


def test_pack_creates_tar_gz(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')")
    (tmp_path / "requirements.txt").write_text("")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "junk").write_text("x")
    write_project_config(tmp_path, ProjectConfig(type="algo", runtime="3.9"))

    out = tmp_path / "my_algo.tar.gz"
    rc = pack_cmd.execute(str(tmp_path), str(out))
    assert rc == 0
    assert out.exists()

    with tarfile.open(out, "r:gz") as tar:
        names = tar.getnames()
    assert "main.py" in names
    assert not any(".venv" in n for n in names)
    assert not any(".aishipbox.toml" in n for n in names)


def test_pack_missing_main(tmp_path):
    rc = pack_cmd.execute(str(tmp_path), str(tmp_path / "x.tar.gz"))
    assert rc == 1
