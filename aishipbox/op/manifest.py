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


class ManifestError(Exception):
    pass


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
    cpu: int
    memory: int
    npu: int
    auto_data_loading: bool
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    xpu_devices: List[str] = field(default_factory=list)

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
        if self.npu > 0 and not self.xpu_devices:
            errs.append("npu > 0 时 xpu-devices 必填（例如 SNT9B）")
        if self.cpu < 1:
            errs.append("cpu 至少为 1")
        if self.memory < 1:
            errs.append("memory 至少为 1 MB")
        if errs:
            raise ManifestError("\n  - ".join(["manifest 校验失败："] + errs))


def render_manifest(m: Manifest) -> str:
    runtime: Dict[str, Any] = {
        "cpu-arch": m.cpu_arch,
    }
    if m.xpu_devices:
        runtime["xpu-devices"] = m.xpu_devices
    runtime["resources"] = [{"cpu": m.cpu, "memory": m.memory, "npu": m.npu}]
    runtime["environment"] = "python"
    runtime["entrypoint"] = "process.py"
    runtime["auto-data-loading"] = m.auto_data_loading

    doc = {
        "id": m.id,
        "name": m.name,
        "description": m.description,
        "author": m.author,
        "version": m.version,
        "tags": {
            "language": m.language,
            "format": m.format,
            "category": m.category,
            "modal": m.modal,
        },
        "runtime": runtime,
        "arguments": m.arguments,
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False)


def parse_manifest(text: str) -> Manifest:
    doc = yaml.safe_load(text)
    tags = doc.get("tags", {})
    rt = doc.get("runtime", {})
    res = (rt.get("resources") or [{}])[0]
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
        cpu=int(res.get("cpu", 1)),
        memory=int(res.get("memory", 2048)),
        npu=int(res.get("npu", 0)),
        auto_data_loading=bool(rt.get("auto-data-loading", False)),
        arguments=list(doc.get("arguments") or []),
    )


def load_manifest(project_dir: Path) -> Manifest:
    text = (Path(project_dir) / "manifest.yml").read_text(encoding="utf-8")
    return parse_manifest(text)
