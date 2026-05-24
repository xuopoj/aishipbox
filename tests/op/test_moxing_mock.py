import sys
from pathlib import Path

import pytest


@pytest.fixture
def mox(tmp_path, monkeypatch):
    monkeypatch.setenv("AISHIPBOX_OBS_INPUT", str(tmp_path / "in"))
    monkeypatch.setenv("AISHIPBOX_OBS_OUTPUT", str(tmp_path / "out"))
    (tmp_path / "in").mkdir()
    (tmp_path / "out").mkdir()

    mock_root = Path(__file__).resolve().parents[2] / "aishipbox" / "op" / "moxing_mock"
    monkeypatch.syspath_prepend(str(mock_root))
    for k in ("moxing", "moxing.file"):
        sys.modules.pop(k, None)

    import moxing as _mox
    return _mox


def test_list_directory_and_copy(tmp_path, mox):
    (tmp_path / "in" / "a.jpg").write_bytes(b"x")
    (tmp_path / "in" / "a.json").write_bytes(b"{}")

    files = list(mox.file.list_directory("obs://input/", recursive=False))
    assert sorted(files) == ["a.jpg", "a.json"]

    mox.file.copy("obs://input/a.jpg", "obs://output/copy.jpg")
    assert (tmp_path / "out" / "copy.jpg").exists()


def test_list_directory_recursive_returns_files_only(tmp_path, mox):
    (tmp_path / "in" / "sub").mkdir()
    (tmp_path / "in" / "sub" / "x.txt").write_bytes(b"x")
    (tmp_path / "in" / "y.txt").write_bytes(b"y")

    files = mox.file.list_directory("obs://input/", recursive=True)
    assert sorted(files) == ["sub/x.txt", "y.txt"]


def test_exists_and_is_directory(tmp_path, mox):
    (tmp_path / "in" / "f.txt").write_bytes(b"x")
    assert mox.file.exists("obs://input/f.txt") is True
    assert mox.file.exists("obs://input/missing") is False
    assert mox.file.is_directory("obs://input/") is True
    assert mox.file.is_directory("obs://input/f.txt") is False


def test_get_size_file_and_directory(tmp_path, mox):
    (tmp_path / "in" / "a").write_bytes(b"12345")
    (tmp_path / "in" / "sub").mkdir()
    (tmp_path / "in" / "sub" / "b").write_bytes(b"67")
    assert mox.file.get_size("obs://input/a") == 5
    assert mox.file.get_size("obs://input/") == 0
    assert mox.file.get_size("obs://input/", recursive=True) == 7


def test_stat(tmp_path, mox):
    (tmp_path / "in" / "a").write_bytes(b"hello")
    s = mox.file.stat("obs://input/a")
    assert s.length == 5
    assert s.is_directory is False
    assert isinstance(s.mtime_nsec, int)


def test_glob(tmp_path, mox):
    (tmp_path / "in" / "a.jpg").write_bytes(b"")
    (tmp_path / "in" / "b.jpg").write_bytes(b"")
    (tmp_path / "in" / "c.png").write_bytes(b"")
    matches = mox.file.glob("obs://input/*.jpg")
    assert sorted(Path(m).name for m in matches) == ["a.jpg", "b.jpg"]


def test_walk(tmp_path, mox):
    (tmp_path / "in" / "sub").mkdir()
    (tmp_path / "in" / "sub" / "x.txt").write_bytes(b"x")
    (tmp_path / "in" / "y.txt").write_bytes(b"y")
    triples = list(mox.file.walk("obs://input/"))
    all_files = sorted(f for _, _, files in triples for f in files)
    assert all_files == ["x.txt", "y.txt"]


def test_scan_dir(tmp_path, mox):
    (tmp_path / "in" / "f").write_bytes(b"")
    (tmp_path / "in" / "d").mkdir()
    entries = {e.name: e.is_dir() for e in mox.file.scan_dir("obs://input/")}
    assert entries == {"f": False, "d": True}


def test_make_dirs_and_mk_dir(tmp_path, mox):
    mox.file.make_dirs("obs://output/deep/nested/dir")
    assert (tmp_path / "out" / "deep" / "nested" / "dir").is_dir()

    mox.file.mk_dir("obs://output/single")
    assert (tmp_path / "out" / "single").is_dir()


def test_mk_dir_refuses_to_create_parents(tmp_path, mox):
    with pytest.raises(FileNotFoundError):
        mox.file.mk_dir("obs://output/no_parent/leaf")


def test_write_and_read_text(tmp_path, mox):
    mox.file.write("obs://output/a.txt", "hello")
    assert (tmp_path / "out" / "a.txt").read_text() == "hello"
    assert mox.file.read("obs://output/a.txt") == "hello"


def test_write_and_read_binary(tmp_path, mox):
    mox.file.write("obs://output/b.bin", b"\x00\x01\x02")
    assert mox.file.read("obs://output/b.bin", binary=True) == b"\x00\x01\x02"


def test_write_creates_parent_dir(tmp_path, mox):
    mox.file.write("obs://output/new/sub/f.txt", "x")
    assert (tmp_path / "out" / "new" / "sub" / "f.txt").read_text() == "x"


def test_append(tmp_path, mox):
    mox.file.write("obs://output/log.txt", "line1\n")
    mox.file.append("obs://output/log.txt", "line2\n")
    assert (tmp_path / "out" / "log.txt").read_text() == "line1\nline2\n"


def test_append_creates_file_if_missing(tmp_path, mox):
    mox.file.append("obs://output/new.txt", "first\n")
    assert (tmp_path / "out" / "new.txt").read_text() == "first\n"


def test_file_context_manager_read(tmp_path, mox):
    (tmp_path / "in" / "f.txt").write_text("hello")
    with mox.file.File("obs://input/f.txt", "r") as f:
        assert f.read() == "hello"


def test_file_context_manager_write_creates_parent(tmp_path, mox):
    with mox.file.File("obs://output/sub/f.txt", "w") as f:
        f.write("hi")
    assert (tmp_path / "out" / "sub" / "f.txt").read_text() == "hi"


def test_copy_parallel_directory(tmp_path, mox):
    src = tmp_path / "in" / "src_dir"
    src.mkdir()
    (src / "a.txt").write_bytes(b"a")
    (src / "sub").mkdir()
    (src / "sub" / "b.txt").write_bytes(b"b")

    mox.file.copy_parallel("obs://input/src_dir", "obs://output/dst_dir")
    assert (tmp_path / "out" / "dst_dir" / "a.txt").read_bytes() == b"a"
    assert (tmp_path / "out" / "dst_dir" / "sub" / "b.txt").read_bytes() == b"b"


def test_rename(tmp_path, mox):
    (tmp_path / "in" / "old.txt").write_bytes(b"x")
    mox.file.rename("obs://input/old.txt", "obs://input/new.txt")
    assert not (tmp_path / "in" / "old.txt").exists()
    assert (tmp_path / "in" / "new.txt").read_bytes() == b"x"


def test_remove_file(tmp_path, mox):
    (tmp_path / "in" / "f.txt").write_bytes(b"x")
    mox.file.remove("obs://input/f.txt")
    assert not (tmp_path / "in" / "f.txt").exists()


def test_remove_directory_requires_recursive(tmp_path, mox):
    (tmp_path / "in" / "d").mkdir()
    (tmp_path / "in" / "d" / "x").write_bytes(b"x")
    with pytest.raises(OSError):
        mox.file.remove("obs://input/d")
    mox.file.remove("obs://input/d", recursive=True)
    assert not (tmp_path / "in" / "d").exists()


def test_remove_missing_path_is_silent(tmp_path, mox):
    mox.file.remove("obs://input/never_existed")
