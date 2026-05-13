import tarfile

from aishipbox.op.commands import pack as pack_cmd
from aishipbox.core.config import ProjectConfig, write_project_config
from aishipbox.op.manifest import Manifest, render_manifest


def _setup_op(tmp_path):
    write_project_config(tmp_path, ProjectConfig(type="op", runtime="3.10"))
    (tmp_path / "program_package").mkdir()
    (tmp_path / "program_package" / "process.py").write_text("class Process:\n    pass\n")
    m = Manifest(
        id="my_op", name="x", description="", author="", version="0.0.1",
        category="数据转换", modal=["IMAGE"], format=[], language=["zh"],
        cpu_arch=["ARM"], cpu=1, memory=2048, npu=0,
        auto_data_loading=False, arguments=[],
    )
    (tmp_path / "manifest.yml").write_text(render_manifest(m), encoding="utf-8")
    return tmp_path


def test_pack_builds_tar(tmp_path):
    p = _setup_op(tmp_path)
    rc = pack_cmd.execute(str(p), output=None, force=False)
    assert rc == 0
    out = p / "program_package" / "my_op.tar"
    assert out.exists()
    with tarfile.open(out, "r:") as tar:
        names = tar.getnames()
    assert "process.py" in names
    assert "manifest.yml" in names


def test_pack_invalid_manifest(tmp_path):
    p = _setup_op(tmp_path)
    (p / "manifest.yml").write_text("id: x\nversion: 1.0\n")
    rc = pack_cmd.execute(str(p), output=None, force=False)
    assert rc == 1


def test_pack_missing_process(tmp_path):
    p = _setup_op(tmp_path)
    (p / "program_package" / "process.py").unlink()
    rc = pack_cmd.execute(str(p), output=None, force=False)
    assert rc == 1


def test_pack_refuses_existing_without_force(tmp_path):
    p = _setup_op(tmp_path)
    out = p / "program_package" / "my_op.tar"
    out.write_text("old")
    rc = pack_cmd.execute(str(p), output=None, force=False)
    assert rc == 1
    rc = pack_cmd.execute(str(p), output=None, force=True)
    assert rc == 0
