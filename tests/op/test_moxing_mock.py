import sys
from pathlib import Path


def test_moxing_mock_file_ops(tmp_path, monkeypatch):
    monkeypatch.setenv("AISHIPBOX_OBS_INPUT", str(tmp_path / "in"))
    monkeypatch.setenv("AISHIPBOX_OBS_OUTPUT", str(tmp_path / "out"))
    (tmp_path / "in").mkdir()
    (tmp_path / "out").mkdir()
    (tmp_path / "in" / "a.jpg").write_bytes(b"x")
    (tmp_path / "in" / "a.json").write_bytes(b"{}")

    mock_root = Path(__file__).resolve().parents[2] / "aishipbox" / "op" / "moxing_mock"
    monkeypatch.syspath_prepend(str(mock_root))
    for k in ("moxing", "moxing.file"):
        sys.modules.pop(k, None)

    import moxing as mox

    files = list(mox.file.list_directory("obs://input/", recursive=False))
    assert sorted(files) == ["a.jpg", "a.json"]

    mox.file.copy("obs://input/a.jpg", "obs://output/copy.jpg")
    assert (tmp_path / "out" / "copy.jpg").exists()
