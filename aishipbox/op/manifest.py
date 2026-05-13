"""Parse / serialize / validate manifest.yml for custom operators."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
ID_MAX_LEN = 128
VALID_MODALS = {"TEXT", "IMAGE", "VIDEO", "AUDIO", "OTHER"}
VALID_CPU_ARCHES = {"ARM"}
VALID_XPU_DEVICES = {"SNT9B"}
VALID_CATEGORIES = {"数据提取", "数据抽样", "数据转换", "数据过滤", "数据去重", "数据打标", "其他"}
VALID_LABEL_TYPES = {"STRING", "NUMERIC", "ENUM", "OBJECT"}
VALID_LABEL_DIM_TYPES = {"STRING", "NUMERIC", "ENUM"}
VALID_ARG_TYPES = {
    "STRING", "FLOAT", "INT", "ENUM", "LIST", "OBS", "BOOLEAN", "DYNAMIC_INPUT_LIST",
}
NUMERIC_ARG_TYPES = {"INT", "FLOAT"}
ITEMS_ARG_TYPES = {"ENUM", "LIST"}


class ManifestError(Exception):
    pass


@dataclass
class Resource:
    cpu: int
    memory: int
    npu: int = 0


@dataclass
class Manifest:
    id: str
    name: str
    description: str
    author: str
    version: str
    category: str
    modal: List[str]
    format: List[str]
    language: List[str]
    cpu_arch: List[str]
    resources: List[Resource]
    auto_data_loading: bool
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    xpu_devices: List[str] = field(default_factory=list)
    custom: List[str] = field(default_factory=list)
    labels: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def has_npu(self) -> bool:
        return any(r.npu > 0 for r in self.resources)

    def validate(self) -> None:
        errs: List[str] = []
        if not self.id:
            errs.append("id 不能为空")
        else:
            if len(self.id) > ID_MAX_LEN:
                errs.append(f"id 长度不能超过 {ID_MAX_LEN} 字符")
            if not ID_RE.match(self.id):
                errs.append("id 必须以英文字母开头，且只能包含英文字母、数字和下划线")
        if not VERSION_RE.match(self.version):
            errs.append(f"version 必须符合 x.y.z 格式：{self.version}")
        for m in self.modal:
            if m not in VALID_MODALS:
                errs.append(f"非法 modal：{m}")
        if self.category not in VALID_CATEGORIES:
            errs.append(f"非法 category：{self.category}")
        for a in self.cpu_arch:
            if a not in VALID_CPU_ARCHES:
                errs.append(f"非法 cpu-arch：{a}（仅支持 ARM）")
        for x in self.xpu_devices:
            if x not in VALID_XPU_DEVICES:
                errs.append(f"非法 xpu-device：{x}（仅支持 SNT9B）")
        for c in self.custom:
            if len(c) > 32:
                errs.append(f"custom 标签长度不能超过 32 字符：{c}")
        if not self.resources:
            errs.append("resources 不能为空")
        for i, r in enumerate(self.resources):
            if r.cpu < 1:
                errs.append(f"resources[{i}].cpu 至少为 1")
            if r.memory < 1:
                errs.append(f"resources[{i}].memory 至少为 1 MB")
            if r.npu < 0:
                errs.append(f"resources[{i}].npu 不能为负数")
        if self.has_npu and not self.xpu_devices:
            errs.append("当任一 resource 的 npu > 0 时，xpu-devices 必填（例如 SNT9B）")
        errs.extend(_validate_labels(self.labels))
        errs.extend(_validate_arguments(self.arguments))
        if errs:
            raise ManifestError("\n  - ".join(["manifest 校验失败："] + errs))


def _validate_labels(labels: List[Dict[str, Any]]) -> List[str]:
    errs: List[str] = []
    for i, lbl in enumerate(labels):
        prefix = f"labels[{i}]"
        if not lbl.get("key"):
            errs.append(f"{prefix}.key 必填")
        if not lbl.get("name"):
            errs.append(f"{prefix}.name 必填")
        ltype = lbl.get("type")
        if ltype not in VALID_LABEL_TYPES:
            errs.append(f"{prefix}.type 必须为 {sorted(VALID_LABEL_TYPES)} 之一：{ltype}")
            continue
        if ltype == "NUMERIC":
            if "min" not in lbl or "max" not in lbl:
                errs.append(f"{prefix} NUMERIC 类型必须提供 min 和 max")
        elif ltype == "ENUM":
            items = lbl.get("items") or []
            if not items:
                errs.append(f"{prefix} ENUM 类型必须提供至少一个 items 条目")
            for j, it in enumerate(items):
                if not it.get("name") or "value" not in it:
                    errs.append(f"{prefix}.items[{j}] 必须含 name 和 value")
        elif ltype == "OBJECT":
            dims = lbl.get("dimensions") or []
            if not dims:
                errs.append(f"{prefix} OBJECT 类型必须提供至少一个 dimensions 条目")
            for j, d in enumerate(dims):
                if not d.get("key") or not d.get("name"):
                    errs.append(f"{prefix}.dimensions[{j}] 必须含 key 和 name")
                dt = d.get("type")
                if dt not in VALID_LABEL_DIM_TYPES:
                    errs.append(f"{prefix}.dimensions[{j}].type 必须为 {sorted(VALID_LABEL_DIM_TYPES)} 之一：{dt}")
                if dt == "NUMERIC" and ("min" not in d or "max" not in d):
                    errs.append(f"{prefix}.dimensions[{j}] NUMERIC 类型必须提供 min 和 max")
                if dt == "ENUM" and not (d.get("items") or []):
                    errs.append(f"{prefix}.dimensions[{j}] ENUM 类型必须提供至少一个 items 条目")
    return errs


def _validate_arguments(arguments: List[Dict[str, Any]]) -> List[str]:
    errs: List[str] = []
    seen_keys: set = set()
    for i, arg in enumerate(arguments):
        prefix = f"arguments[{i}]"
        key = arg.get("key")
        if not key:
            errs.append(f"{prefix}.key 必填")
        else:
            if len(str(key)) > 128:
                errs.append(f"{prefix}.key 长度不能超过 128 字符")
            if key in seen_keys:
                errs.append(f"{prefix}.key 重复：{key}")
            seen_keys.add(key)
        if not arg.get("name"):
            errs.append(f"{prefix}.name 必填")
        atype = arg.get("type")
        if atype not in VALID_ARG_TYPES:
            errs.append(f"{prefix}.type 必须为 {sorted(VALID_ARG_TYPES)} 之一：{atype}")
            continue

        if atype in NUMERIC_ARG_TYPES:
            if "between" not in arg:
                errs.append(f"{prefix} type={atype} 必须显式设置 between (true/false)")
            for bound in ("min", "max"):
                if bound in arg and not isinstance(arg[bound], (int, float)):
                    errs.append(f"{prefix}.{bound} 必须为数字")
            if arg.get("between") and arg.get("default"):
                if not _is_range_default(arg["default"]):
                    errs.append(f"{prefix} between=true 时 default 必须为 'min;max' 格式")

        if atype in ITEMS_ARG_TYPES:
            items = arg.get("items") or []
            if not items:
                errs.append(f"{prefix} type={atype} 必须提供至少一个 items 条目")
            for j, it in enumerate(items):
                if not it.get("name") or "value" not in it:
                    errs.append(f"{prefix}.items[{j}] 必须含 name 和 value")

        if arg.get("visible") is False and arg.get("required") is True and "default" not in arg:
            errs.append(f"{prefix} visible=false 且 required=true 时必须提供 default")
    return errs


def _is_range_default(default: Any) -> bool:
    if not isinstance(default, str):
        return False
    parts = default.split(";")
    if len(parts) != 2:
        return False
    try:
        float(parts[0]); float(parts[1])
    except ValueError:
        return False
    return True


def render_manifest(m: Manifest) -> str:
    runtime: Dict[str, Any] = {
        "cpu-arch": m.cpu_arch,
    }
    if m.xpu_devices:
        runtime["xpu-devices"] = m.xpu_devices
    runtime["resources"] = [_resource_to_dict(r) for r in m.resources]
    runtime["environment"] = "python"
    runtime["entrypoint"] = "process.py"
    runtime["auto-data-loading"] = m.auto_data_loading

    tags: Dict[str, Any] = {
        "language": m.language,
        "format": m.format,
        "category": m.category,
        "modal": m.modal,
    }
    if m.custom:
        tags["custom"] = m.custom

    doc: Dict[str, Any] = {
        "id": m.id,
        "name": m.name,
        "description": m.description,
        "author": m.author,
        "version": m.version,
        "tags": tags,
    }
    if m.labels:
        doc["labels"] = m.labels
    doc["runtime"] = runtime
    doc["arguments"] = m.arguments
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False)


def _resource_to_dict(r: Resource) -> Dict[str, int]:
    d: Dict[str, int] = {"cpu": r.cpu, "memory": r.memory}
    if r.npu:
        d["npu"] = r.npu
    else:
        d["npu"] = 0
    return d


def parse_manifest(text: str) -> Manifest:
    doc = yaml.safe_load(text)
    tags = doc.get("tags", {})
    rt = doc.get("runtime", {})
    raw_resources = rt.get("resources") or []
    resources = [
        Resource(
            cpu=int(r.get("cpu", 1)),
            memory=int(r.get("memory", 2048)),
            npu=int(r.get("npu", 0)),
        )
        for r in raw_resources
    ] or [Resource(cpu=1, memory=2048, npu=0)]
    raw_category = tags.get("category", "")
    category = raw_category[0] if isinstance(raw_category, list) and raw_category else (raw_category or "")
    return Manifest(
        id=str(doc.get("id", "")),
        name=str(doc.get("name", "")),
        description=str(doc.get("description", "")),
        author=str(doc.get("author", "")),
        version=str(doc.get("version", "")),
        category=str(category),
        modal=list(tags.get("modal", [])),
        format=list(tags.get("format", [])),
        language=list(tags.get("language", [])),
        cpu_arch=list(rt.get("cpu-arch", [])),
        xpu_devices=list(rt.get("xpu-devices", [])),
        resources=resources,
        auto_data_loading=bool(rt.get("auto-data-loading", False)),
        arguments=list(doc.get("arguments") or []),
        custom=list(tags.get("custom") or []),
        labels=list(doc.get("labels") or []),
    )


def load_manifest(project_dir: Path) -> Manifest:
    text = (Path(project_dir) / "manifest.yml").read_text(encoding="utf-8")
    return parse_manifest(text)
