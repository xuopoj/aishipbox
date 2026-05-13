"""op new: create a custom-operator project."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional

from aishipbox import __version__
from aishipbox.core import strings
from aishipbox.core.config import HOSTED_RUNTIMES, ProjectConfig, write_project_config
from aishipbox.core.venv import provision_venv, pip_install
from aishipbox.op import wizard
from aishipbox.op.manifest import Manifest, ManifestError, render_manifest


REQUIRED_FIELDS = (
    "id", "name", "version", "category", "modal",
    "cpu_arch", "cpu", "memory", "npu", "auto_data_loading", "skeleton",
)


def execute(name: str, parent_dir: str, flags: Optional[Dict[str, Any]] = None, yes: bool = False) -> int:
    flags = dict(flags or {})
    project_dir = Path(parent_dir).resolve() / name
    if project_dir.exists():
        print(strings.TARGET_DIR_EXISTS.format(path=project_dir))
        return 1

    if yes:
        missing = [f for f in REQUIRED_FIELDS if f not in flags]
        if missing:
            print(strings.MISSING_FLAGS_FOR_YES.format(fields=", ".join(missing)))
            return 2
        fields = flags
    else:
        fields = wizard.run_wizard(default_id=name)
        fields.update(flags)

    npu = int(fields["npu"])
    xpu_devices = list(fields.get("xpu_devices") or ([] if npu == 0 else ["SNT9B"]))
    try:
        manifest = Manifest(
            id=fields["id"],
            name=fields["name"],
            description=fields.get("description", ""),
            author=fields.get("author", ""),
            version=fields["version"],
            category=fields["category"],
            modal=fields["modal"],
            format=fields.get("format", []),
            language=fields.get("language", ["zh"]),
            cpu_arch=fields["cpu_arch"],
            xpu_devices=xpu_devices,
            cpu=int(fields["cpu"]),
            memory=int(fields["memory"]),
            npu=npu,
            auto_data_loading=bool(fields["auto_data_loading"]),
            arguments=fields.get("arguments", []),
        )
        manifest.validate()
    except ManifestError as e:
        print(str(e))
        return 1

    project_dir.mkdir(parents=True)
    (project_dir / "program_package").mkdir()
    (project_dir / "obs_input").mkdir()
    (project_dir / "obs_output").mkdir()

    (project_dir / "manifest.yml").write_text(render_manifest(manifest), encoding="utf-8")

    tpl = resources.files("aishipbox.op.templates")
    skeleton = fields["skeleton"]
    process_tmpl = tpl.joinpath(f"process.{skeleton}.py.tmpl").read_text(encoding="utf-8")
    (project_dir / "program_package" / "process.py").write_text(process_tmpl, encoding="utf-8")
    (project_dir / "program_package" / "requirements.txt").write_text(
        tpl.joinpath("requirements.txt.tmpl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (project_dir / ".env.example").write_text(tpl.joinpath("env.example.tmpl").read_text(encoding="utf-8"), encoding="utf-8")
    (project_dir / ".gitignore").write_text(tpl.joinpath("gitignore.tmpl").read_text(encoding="utf-8"), encoding="utf-8")
    agents_tmpl = tpl.joinpath("AGENTS.md.tmpl").read_text(encoding="utf-8")
    (project_dir / "AGENTS.md").write_text(
        Template(agents_tmpl).safe_substitute(aishipbox_version=__version__),
        encoding="utf-8",
    )

    write_project_config(project_dir, ProjectConfig(type="op", runtime=HOSTED_RUNTIMES["op"]))

    _provision_and_install(project_dir)

    print(f"\n算子已创建：{project_dir}")
    print(f"\n{strings.NEXT_STEPS_HEADER}")
    print(f"  1. cd {name}")
    print(f"  2. 在 program_package/process.py 中实现算法")
    print(f"  3. 将测试数据放入 obs_input/")
    print(f"  4. aishipbox op run            # mock 模式")
    print(f"  5. aishipbox op pack")
    return 0


def _provision_and_install(project_dir: Path) -> None:
    provision_venv(project_dir, HOSTED_RUNTIMES["op"])
    req = project_dir / "program_package" / "requirements.txt"
    content = req.read_text(encoding="utf-8")
    pkgs = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
    if pkgs:
        pip_install(project_dir, *pkgs)
