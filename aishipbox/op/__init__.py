"""op subcommand group dispatch."""

from __future__ import annotations

import argparse
from typing import Any, Dict, List


def _str2bool(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "y")


def dispatch(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="aishipbox op", description="自定义算子项目管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="新建算子项目")
    p_new.add_argument("name")
    p_new.add_argument("-d", "--dir", default=".")
    p_new.add_argument("--id")
    p_new.add_argument("--op-name", dest="op_name")
    p_new.add_argument("--description", default="")
    p_new.add_argument("--author", default="")
    p_new.add_argument("--version")
    p_new.add_argument("--category", default=None)
    p_new.add_argument("--modal", action="append", default=None)
    p_new.add_argument("--format", action="append", default=None)
    p_new.add_argument("--language", action="append", default=None)
    p_new.add_argument("--cpu-arch", action="append", default=None)
    p_new.add_argument("--xpu-device", dest="xpu_devices", action="append", default=None)
    p_new.add_argument("--cpu", type=int)
    p_new.add_argument("--memory", type=int)
    p_new.add_argument("--npu", type=int)
    p_new.add_argument("--auto-data-loading", type=_str2bool, default=None)
    p_new.add_argument("--skeleton", choices=["blank", "transform"])
    p_new.add_argument("--yes", action="store_true")

    p_run = sub.add_parser("run", help="本地运行算子")
    p_run.add_argument("path", nargs="?", default=".")
    p_run.add_argument("--obs", action="store_true")
    p_run.add_argument("--debug", action="store_true")
    p_run.add_argument("--debug-port", type=int, default=5678)

    p_pack = sub.add_parser("pack", help="打包算子")
    p_pack.add_argument("path", nargs="?", default=".")
    p_pack.add_argument("-o", "--output")
    p_pack.add_argument("--force", action="store_true")

    p_debug = sub.add_parser("debug", help="生成 VS Code 调试配置")
    p_debug.add_argument("path", nargs="?", default=".")

    p_download = sub.add_parser("download", help="下载依赖 wheel 并写入 requirements.txt")
    p_download.add_argument("package")
    p_download.add_argument("path", nargs="?", default=".")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    from aishipbox.op.commands import new, run, pack, debug, dep

    if args.cmd == "new":
        flags: Dict[str, Any] = {}
        if args.id is not None: flags["id"] = args.id
        if args.op_name is not None: flags["name"] = args.op_name
        if args.description: flags["description"] = args.description
        if args.author: flags["author"] = args.author
        if args.version is not None: flags["version"] = args.version
        if args.category is not None: flags["category"] = args.category
        if args.modal is not None: flags["modal"] = args.modal
        if args.format is not None: flags["format"] = args.format
        if args.language is not None: flags["language"] = args.language
        if args.cpu_arch is not None: flags["cpu_arch"] = args.cpu_arch
        if args.xpu_devices is not None: flags["xpu_devices"] = args.xpu_devices
        if args.cpu is not None: flags["cpu"] = args.cpu
        if args.memory is not None: flags["memory"] = args.memory
        if args.npu is not None: flags["npu"] = args.npu
        if args.auto_data_loading is not None: flags["auto_data_loading"] = args.auto_data_loading
        if args.skeleton is not None: flags["skeleton"] = args.skeleton
        return new.execute(args.name, args.dir, flags=flags, yes=args.yes)

    if args.cmd == "run":
        return run.execute(args.path, obs=args.obs, debug=args.debug, debug_port=args.debug_port)
    if args.cmd == "pack":
        return pack.execute(args.path, output=args.output, force=args.force)
    if args.cmd == "debug":
        return debug.execute(args.path)
    if args.cmd == "download":
        return dep.execute(args.path, args.package)
    return 2
