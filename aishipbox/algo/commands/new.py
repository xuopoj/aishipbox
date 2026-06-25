"""algo new: create a new algorithm service project."""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path
from string import Template
from typing import Optional

from aishipbox import __version__
from aishipbox.core import strings
from aishipbox.core.config import HOSTED_RUNTIMES, ProjectConfig, write_project_config
from aishipbox.core.ui import stdin_is_interactive
from aishipbox.core.venv import provision_venv, pip_install, VenvError


TEMPLATES = ("basic", "predict", "cv")
TEMPLATE_DEPS = {
    "basic": ["requests"],
    "predict": ["pandas", "requests"],
    "cv": ["opencv-python", "numpy", "requests"],
}


def execute(name: str, parent_dir: str, template: Optional[str] = None, yes: bool = False,
            native_tls: bool = False, insecure: bool = False) -> int:
    if "-" in name:
        print(f"项目名不允许包含连字符：{name}，请改用下划线 {name.replace('-', '_')}")
        return 1

    parent = Path(parent_dir).resolve()
    project_dir = parent / name
    if project_dir.exists():
        print(strings.TARGET_DIR_EXISTS.format(path=project_dir))
        return 1

    if template is None:
        if yes:
            template = "basic"
        elif not stdin_is_interactive():
            print(strings.NON_INTERACTIVE_NO_WIZARD.format(
                example=f"aishipbox algo new {name} --yes -t basic"
            ))
            return 2
        else:
            template = _prompt_template()
    if template not in TEMPLATES:
        print(f"未知模板：{template}")
        return 1

    project_dir.mkdir(parents=True)

    template_pkg = resources.files(f"aishipbox.algo.templates.{template}")
    for item in template_pkg.iterdir():
        if item.is_file() and not item.name.startswith("__"):
            content = item.read_text(encoding="utf-8").replace("${name}", name)
            (project_dir / item.name).write_text(content, encoding="utf-8")

    agents_tmpl = resources.files("aishipbox.algo.templates").joinpath("AGENTS.md.tmpl").read_text(encoding="utf-8")
    (project_dir / "AGENTS.md").write_text(
        Template(agents_tmpl).safe_substitute(aishipbox_version=__version__),
        encoding="utf-8",
    )

    write_project_config(project_dir, ProjectConfig(type="algo", runtime=HOSTED_RUNTIMES["algo"]))

    if insecure:
        print(strings.VENV_INSECURE_WARNING)
    try:
        _provision_and_install(project_dir, template, native_tls=native_tls, insecure=insecure)
    except VenvError as e:
        shutil.rmtree(project_dir, ignore_errors=True)
        print(strings.VENV_PROVISION_FAILED.format(path=project_dir, detail=e))
        return 1

    print(f"\n项目已创建：{project_dir}")
    print(f"\n{strings.NEXT_STEPS_HEADER}")
    print(f"  1. cd {name}")
    print(f"  2. cp .env.example .env  # 如存在")
    print(f"  3. 编辑 main.py 实现算法")
    print(f"  4. aishipbox algo run")
    print(f"  5. aishipbox algo pack")
    return 0


def _prompt_template() -> str:
    print(strings.ALGO_SELECT_TEMPLATE)
    print(f"  1. {strings.ALGO_TEMPLATE_BASIC}")
    print(f"  2. {strings.ALGO_TEMPLATE_PREDICT}")
    print(f"  3. {strings.ALGO_TEMPLATE_CV}")
    while True:
        choice = input("请输入编号或名称 [1]：").strip() or "1"
        mapping = {"1": "basic", "2": "predict", "3": "cv",
                   "basic": "basic", "predict": "predict", "cv": "cv"}
        if choice in mapping:
            return mapping[choice]
        print(f"无效选择：{choice}")


def _provision_and_install(project_dir: Path, template: str,
                           native_tls: bool = False, insecure: bool = False) -> None:
    provision_venv(project_dir, HOSTED_RUNTIMES["algo"], native_tls=native_tls, insecure=insecure)
    deps = TEMPLATE_DEPS.get(template, [])
    if deps:
        pip_install(project_dir, *deps)
