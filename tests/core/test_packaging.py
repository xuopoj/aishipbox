import tarfile
from pathlib import Path

from aishipbox.core.packaging import build_tar, DEFAULT_EXCLUDES


def test_build_tar_basic(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("print('a')")
    (src / "b.py").write_text("print('b')")

    out = tmp_path / "out.tar"
    build_tar(src, out, excludes=DEFAULT_EXCLUDES, gzip=False)

    with tarfile.open(out, "r:") as tar:
        names = sorted(tar.getnames())
    assert names == ["a.py", "b.py"]


def test_build_tar_gzip(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("a")

    out = tmp_path / "out.tar.gz"
    build_tar(src, out, excludes=DEFAULT_EXCLUDES, gzip=True)

    with tarfile.open(out, "r:gz") as tar:
        assert tar.getnames() == ["a.py"]


def test_build_tar_respects_excludes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("a")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "x.pyc").write_text("")
    (src / ".DS_Store").write_text("")

    out = tmp_path / "out.tar"
    build_tar(src, out, excludes=DEFAULT_EXCLUDES, gzip=False)

    with tarfile.open(out, "r:") as tar:
        names = tar.getnames()
    assert "a.py" in names
    assert not any("__pycache__" in n for n in names)
    assert ".DS_Store" not in names
