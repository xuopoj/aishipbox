"""algo subcommand group dispatch."""

from __future__ import annotations

import argparse
from typing import List


def dispatch(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="aishipbox algo", description="算法包服务项目管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="新建算法服务项目")
    p_new.add_argument("name")
    p_new.add_argument("-d", "--dir", default=".")
    p_new.add_argument("-t", "--template", choices=["basic", "predict", "cv"])
    p_new.add_argument("--yes", action="store_true")

    p_run = sub.add_parser("run", help="本地运行算法服务")
    p_run.add_argument("path", nargs="?", default=".")
    p_run.add_argument("-p", "--port", type=int, default=8080)
    p_run.add_argument("--host", default="127.0.0.1")
    p_run.add_argument("--debug", action="store_true")
    p_run.add_argument("--debug-port", type=int, default=5678)

    p_pack = sub.add_parser("pack", help="打包算法服务")
    p_pack.add_argument("path", nargs="?", default=".")
    p_pack.add_argument("-o", "--output")

    p_debug = sub.add_parser("debug", help="生成 VS Code 调试配置")
    p_debug.add_argument("path", nargs="?", default=".")

    p_stubs = sub.add_parser("stubs", help="安装 IDE 类型补全包")
    p_stubs.add_argument("path", nargs="?", default=".")

    p_deps = sub.add_parser("install-deps", help="安装托管环境常用依赖")
    p_deps.add_argument("path", nargs="?", default=".")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    from aishipbox.algo.commands import new, run, pack, debug, stubs, install_deps

    if args.cmd == "new":
        return new.execute(args.name, args.dir, args.template, args.yes)
    if args.cmd == "run":
        return run.execute(args.path, args.host, args.port, args.debug, args.debug_port)
    if args.cmd == "pack":
        return pack.execute(args.path, args.output)
    if args.cmd == "debug":
        return debug.execute(args.path)
    if args.cmd == "stubs":
        return stubs.execute(args.path)
    if args.cmd == "install-deps":
        return install_deps.execute(args.path)
    return 2
