import pytest

from aishipbox.op.manifest import Manifest, ManifestError, parse_manifest, render_manifest


def test_render_minimal():
    m = Manifest(
        id="my_op",
        name="测试算子",
        description="说明",
        author="me",
        version="0.0.1",
        category=["数据转换"],
        modal=["IMAGE"],
        format=["JPG"],
        language=["zh"],
        cpu_arch=["arm"],
        cpu=1, memory=2048, npu=0,
        auto_data_loading=False,
        arguments=[],
    )
    yaml_text = render_manifest(m)
    assert "id: my_op" in yaml_text
    assert "测试算子" in yaml_text


def test_roundtrip():
    m = Manifest(
        id="x", name="x", description="", author="a", version="1.0.0",
        category=["其他"], modal=["OTHER"], format=[], language=["en"],
        cpu_arch=["x86"], cpu=1, memory=2048, npu=0,
        auto_data_loading=True, arguments=[{"name": "n", "type": "string", "description": "d"}],
    )
    text = render_manifest(m)
    parsed = parse_manifest(text)
    assert parsed.id == "x"
    assert parsed.auto_data_loading is True
    assert parsed.arguments[0]["name"] == "n"


def test_validate_bad_version_rejects():
    with pytest.raises(ManifestError):
        Manifest(
            id="x", name="x", description="", author="a", version="1.0",
            category=["其他"], modal=["OTHER"], format=[], language=["en"],
            cpu_arch=["x86"], cpu=1, memory=2048, npu=0,
            auto_data_loading=False, arguments=[],
        ).validate()


def test_validate_bad_modal_rejects():
    with pytest.raises(ManifestError):
        Manifest(
            id="x", name="x", description="", author="a", version="1.0.0",
            category=["其他"], modal=["NOPE"], format=[], language=["en"],
            cpu_arch=["x86"], cpu=1, memory=2048, npu=0,
            auto_data_loading=False, arguments=[],
        ).validate()
