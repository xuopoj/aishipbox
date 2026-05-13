import pytest

from aishipbox.op.manifest import Manifest, ManifestError, parse_manifest, render_manifest


def _minimal(**overrides) -> Manifest:
    base = dict(
        id="my_op",
        name="测试算子",
        description="说明",
        author="me",
        version="0.0.1",
        category="数据转换",
        modal=["IMAGE"],
        format=["JPG"],
        language=["zh"],
        cpu_arch=["ARM"],
        cpu=1, memory=2048, npu=0,
        auto_data_loading=False,
        arguments=[],
    )
    base.update(overrides)
    return Manifest(**base)


def test_render_minimal():
    yaml_text = render_manifest(_minimal())
    assert "id: my_op" in yaml_text
    assert "测试算子" in yaml_text
    assert "category: 数据转换" in yaml_text
    assert "- ARM" in yaml_text
    assert "xpu-devices" not in yaml_text


def test_render_with_npu_emits_xpu_devices():
    m = _minimal(npu=1, xpu_devices=["SNT9B"])
    text = render_manifest(m)
    assert "xpu-devices" in text
    assert "SNT9B" in text


def test_roundtrip():
    m = _minimal(author="a", arguments=[{"name": "n", "type": "STRING", "description": "d"}])
    parsed = parse_manifest(render_manifest(m))
    assert parsed.id == "my_op"
    assert parsed.category == "数据转换"
    assert parsed.cpu_arch == ["ARM"]
    assert parsed.arguments[0]["name"] == "n"


def test_parse_legacy_list_category_takes_first():
    text = (
        "id: x\nname: x\ndescription: ''\nauthor: ''\nversion: 1.0.0\n"
        "tags:\n  language: [en]\n  format: []\n  category: [数据转换, 其他]\n  modal: [OTHER]\n"
        "runtime:\n  cpu-arch: [ARM]\n  resources: [{cpu: 1, memory: 2048, npu: 0}]\n"
        "  environment: python\n  entrypoint: process.py\n  auto-data-loading: false\n"
        "arguments: []\n"
    )
    parsed = parse_manifest(text)
    assert parsed.category == "数据转换"


def test_validate_bad_version_rejects():
    with pytest.raises(ManifestError):
        _minimal(version="1.0").validate()


def test_validate_bad_modal_rejects():
    with pytest.raises(ManifestError):
        _minimal(modal=["NOPE"]).validate()


def test_validate_bad_category_rejects():
    with pytest.raises(ManifestError):
        _minimal(category="未知类别").validate()


def test_validate_lowercase_cpu_arch_rejects():
    with pytest.raises(ManifestError):
        _minimal(cpu_arch=["arm"]).validate()


def test_validate_x86_cpu_arch_rejects():
    with pytest.raises(ManifestError):
        _minimal(cpu_arch=["x86"]).validate()


def test_validate_npu_without_xpu_rejects():
    with pytest.raises(ManifestError):
        _minimal(npu=1, xpu_devices=[]).validate()


def test_validate_bad_xpu_device_rejects():
    with pytest.raises(ManifestError):
        _minimal(npu=1, xpu_devices=["BOGUS"]).validate()


def test_validate_npu_with_snt9b_ok():
    _minimal(npu=1, xpu_devices=["SNT9B"]).validate()


def test_validate_id_bad_charset_rejects():
    with pytest.raises(ManifestError):
        _minimal(id="1bad-start").validate()
    with pytest.raises(ManifestError):
        _minimal(id="has space").validate()


def test_validate_id_too_long_rejects():
    with pytest.raises(ManifestError):
        _minimal(id="a" * 129).validate()
