import pytest

from aishipbox.op.manifest import Manifest, ManifestError, Resource, parse_manifest, render_manifest


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
        resources=[Resource(cpu=1, memory=2048, npu=0)],
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
    m = _minimal(resources=[Resource(cpu=24, memory=196608, npu=1)], xpu_devices=["SNT9B"])
    text = render_manifest(m)
    assert "xpu-devices" in text
    assert "SNT9B" in text


def test_render_multiple_resources():
    m = _minimal(
        resources=[
            Resource(cpu=1, memory=2048, npu=0),
            Resource(cpu=24, memory=196608, npu=1),
        ],
        xpu_devices=["SNT9B"],
    )
    text = render_manifest(m)
    assert text.count("cpu:") == 2


def test_render_with_custom_tags():
    text = render_manifest(_minimal(custom=["数据增强", "预标注"]))
    assert "custom:" in text
    assert "数据增强" in text


def test_render_without_custom_tags_omits_key():
    text = render_manifest(_minimal())
    assert "custom:" not in text


def test_roundtrip():
    m = _minimal(
        author="a",
        arguments=[{"key": "n", "name": "n", "type": "STRING", "tips": "d"}],
        custom=["数据增强"],
        resources=[
            Resource(cpu=1, memory=2048, npu=0),
            Resource(cpu=24, memory=196608, npu=1),
        ],
        xpu_devices=["SNT9B"],
        labels=[{"key": "k", "name": "n", "type": "STRING"}],
    )
    parsed = parse_manifest(render_manifest(m))
    assert parsed.id == "my_op"
    assert parsed.category == "数据转换"
    assert parsed.cpu_arch == ["ARM"]
    assert parsed.arguments[0]["name"] == "n"
    assert parsed.custom == ["数据增强"]
    assert len(parsed.resources) == 2
    assert parsed.resources[1].npu == 1
    assert parsed.labels[0]["key"] == "k"


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
        _minimal(resources=[Resource(cpu=24, memory=196608, npu=1)], xpu_devices=[]).validate()


def test_validate_bad_xpu_device_rejects():
    with pytest.raises(ManifestError):
        _minimal(resources=[Resource(cpu=24, memory=196608, npu=1)], xpu_devices=["BOGUS"]).validate()


def test_validate_npu_with_snt9b_ok():
    _minimal(resources=[Resource(cpu=24, memory=196608, npu=1)], xpu_devices=["SNT9B"]).validate()


def test_validate_empty_resources_rejects():
    with pytest.raises(ManifestError):
        _minimal(resources=[]).validate()


def test_validate_long_custom_tag_rejects():
    with pytest.raises(ManifestError):
        _minimal(custom=["x" * 33]).validate()


def test_validate_label_string_ok():
    _minimal(labels=[{"key": "k", "name": "n", "type": "STRING"}]).validate()


def test_validate_label_numeric_requires_min_max():
    with pytest.raises(ManifestError):
        _minimal(labels=[{"key": "k", "name": "n", "type": "NUMERIC"}]).validate()
    _minimal(labels=[{"key": "k", "name": "n", "type": "NUMERIC", "min": 0, "max": 100}]).validate()


def test_validate_label_enum_requires_items():
    with pytest.raises(ManifestError):
        _minimal(labels=[{"key": "k", "name": "n", "type": "ENUM"}]).validate()
    _minimal(labels=[{
        "key": "k", "name": "n", "type": "ENUM",
        "items": [{"name": "a", "value": "A"}],
    }]).validate()


def test_validate_label_object_requires_dimensions():
    with pytest.raises(ManifestError):
        _minimal(labels=[{"key": "k", "name": "n", "type": "OBJECT"}]).validate()
    _minimal(labels=[{
        "key": "k", "name": "n", "type": "OBJECT",
        "dimensions": [{"key": "dk", "name": "dn", "type": "STRING"}],
    }]).validate()


def test_validate_bad_label_type_rejects():
    with pytest.raises(ManifestError):
        _minimal(labels=[{"key": "k", "name": "n", "type": "BOGUS"}]).validate()


def test_validate_argument_string_ok():
    _minimal(arguments=[{"key": "kw", "name": "关键词", "type": "STRING"}]).validate()


def test_validate_argument_missing_key():
    with pytest.raises(ManifestError):
        _minimal(arguments=[{"name": "n", "type": "STRING"}]).validate()


def test_validate_argument_missing_name():
    with pytest.raises(ManifestError):
        _minimal(arguments=[{"key": "k", "type": "STRING"}]).validate()


def test_validate_argument_bad_type():
    with pytest.raises(ManifestError):
        _minimal(arguments=[{"key": "k", "name": "n", "type": "BOGUS"}]).validate()


def test_validate_argument_duplicate_keys():
    with pytest.raises(ManifestError):
        _minimal(arguments=[
            {"key": "k", "name": "a", "type": "STRING"},
            {"key": "k", "name": "b", "type": "STRING"},
        ]).validate()


def test_validate_argument_int_requires_between():
    with pytest.raises(ManifestError):
        _minimal(arguments=[{"key": "k", "name": "n", "type": "INT", "min": 1, "max": 10}]).validate()
    _minimal(arguments=[{"key": "k", "name": "n", "type": "INT", "between": False, "default": 5}]).validate()


def test_validate_argument_float_range_default_format():
    with pytest.raises(ManifestError):
        _minimal(arguments=[{
            "key": "k", "name": "n", "type": "FLOAT", "between": True,
            "min": 1.0, "max": 100.0, "default": "50",
        }]).validate()
    _minimal(arguments=[{
        "key": "k", "name": "n", "type": "FLOAT", "between": True,
        "min": 1.0, "max": 100.0, "default": "10;50",
    }]).validate()


def test_validate_argument_enum_requires_items():
    with pytest.raises(ManifestError):
        _minimal(arguments=[{"key": "k", "name": "n", "type": "ENUM"}]).validate()
    _minimal(arguments=[{
        "key": "k", "name": "n", "type": "ENUM",
        "items": [{"name": "a", "value": "A"}],
    }]).validate()


def test_validate_argument_list_item_missing_value():
    with pytest.raises(ManifestError):
        _minimal(arguments=[{
            "key": "k", "name": "n", "type": "LIST",
            "items": [{"name": "no-value"}],
        }]).validate()


def test_validate_argument_invisible_required_needs_default():
    with pytest.raises(ManifestError):
        _minimal(arguments=[{
            "key": "k", "name": "n", "type": "STRING",
            "visible": False, "required": True,
        }]).validate()
    _minimal(arguments=[{
        "key": "k", "name": "n", "type": "STRING",
        "visible": False, "required": True, "default": "x",
    }]).validate()


def test_validate_argument_boolean_ok():
    _minimal(arguments=[{
        "key": "k", "name": "n", "type": "BOOLEAN",
        "items": [{"name": "是", "value": True}, {"name": "否", "value": False}],
        "default": False,
    }]).validate()


def test_validate_argument_boolean_without_items_rejects():
    with pytest.raises(ManifestError, match="items"):
        _minimal(arguments=[{
            "key": "k", "name": "n", "type": "BOOLEAN",
            "default": False,
        }]).validate()


def test_validate_argument_boolean_items_missing_value_rejects():
    with pytest.raises(ManifestError, match="name 和 value"):
        _minimal(arguments=[{
            "key": "k", "name": "n", "type": "BOOLEAN",
            "items": [{"name": "是"}, {"name": "否", "value": False}],
            "default": False,
        }]).validate()


def test_validate_argument_obs_ok():
    _minimal(arguments=[{
        "key": "k", "name": "n", "type": "OBS",
        "tips": "OBS 路径", "default": "path/file.csv",
    }]).validate()


def test_validate_id_bad_charset_rejects():
    with pytest.raises(ManifestError):
        _minimal(id="1bad-start").validate()
    with pytest.raises(ManifestError):
        _minimal(id="has space").validate()


def test_validate_id_too_long_rejects():
    with pytest.raises(ManifestError):
        _minimal(id="a" * 129).validate()
