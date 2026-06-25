"""op subcommand group dispatch."""

from __future__ import annotations

import argparse
from typing import Any, Dict, List


def _str2bool(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "y")


def dispatch(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="aishipbox op",
        description="自定义算子项目管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "典型工作流：\n"
            "  1. new       新建项目（脚手架 + venv + 平台预置包）\n"
            "  2. 实现       编辑 program_package/process.py（先看项目内 AGENTS.md）\n"
            "  3. run        本地 mock 运行，结果写到 obs_output/\n"
            "  4. download   按需补充平台没有的依赖 wheel\n"
            "  5. pack       校验并打包成 program_package/<id>.tar，上传平台\n"
            "\n"
            "每条命令的完整参数与默认值见 `aishipbox op <命令> --help`；\n"
            "项目级字段规范与约束见项目自带的 AGENTS.md。"
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser(
        "new", help="新建算子项目",
        description="新建算子项目。带 --yes 进入非交互模式，未提供的字段用默认值填充；"
                    "不带 --yes 且无 TTY 时会报错而非卡住向导。",
    )
    p_new.add_argument("name", help="项目目录名（也作为 id/name 默认值）")
    p_new.add_argument("-d", "--dir", default=".", help="父目录，默认当前目录")
    p_new.add_argument("--id", help="算子 ID，英文字母开头/[A-Za-z0-9_]/≤128；默认=项目名")
    p_new.add_argument("--op-name", dest="op_name", help="算子显示名；默认=项目名")
    p_new.add_argument("--description", default="", help="算子描述")
    p_new.add_argument("--author", default="", help="作者")
    p_new.add_argument("--version", help="版本 x.y.z；默认 0.0.1")
    p_new.add_argument("--category", default=None,
                       help="类别（单选）：数据提取/数据抽样/数据转换/数据过滤/数据去重/数据打标/其他；默认 其他")
    p_new.add_argument("--modal", action="append", default=None, metavar="MODAL",
                       help="数据模态（可重复）：TEXT/IMAGE/VIDEO/AUDIO/OTHER；默认 OTHER")
    p_new.add_argument("--format", action="append", default=None,
                       help="数据格式（可重复，必填非空），如 JSONL/CSV/MP4；默认 OTHER")
    p_new.add_argument("--language", action="append", default=None, help="语言标签（可重复）；默认 zh")
    p_new.add_argument("--cpu-arch", action="append", default=None, metavar="ARCH",
                       help="CPU 架构（可重复，大小写敏感）：ARM 或 X86；默认 ARM")
    p_new.add_argument("--xpu-device", dest="xpu_devices", action="append", default=None,
                       help="XPU 设备（可重复），如 SNT9B；npu>0 时自动加")
    p_new.add_argument("--cpu", type=int, help="CPU 核数 ≥1；默认 1")
    p_new.add_argument("--memory", type=int, help="内存 MB ≥1；默认 2048")
    p_new.add_argument("--npu", type=int, help="NPU 数量 ≥0；默认 0")
    p_new.add_argument("--auto-data-loading", type=_str2bool, default=None, metavar="BOOL",
                       help="true=框架按文件构造 DataFrame 逐文件调用；false=自行 OBS I/O；默认 false")
    p_new.add_argument("--skeleton", choices=["blank", "transform"],
                       help="代码骨架：blank=空白 / transform=含 moxing 拷贝示例；默认 transform")
    p_new.add_argument("--yes", action="store_true",
                       help="非交互模式：跳过向导，未提供的字段用默认值填充")
    p_new.add_argument("--native-tls", dest="native_tls", action="store_true",
                       help="创建 venv 时让 uv 改用系统证书库；公司代理/自签名证书导致下载解释器失败时加上")
    p_new.add_argument("--insecure", action="store_true",
                       help="创建 venv 时跳过 TLS 证书校验下载解释器（不安全，有中间人风险，仅在可信网络下使用）")

    p_run = sub.add_parser(
        "run", help="本地运行算子",
        description="在项目 venv 内本地运行算子。默认 mock 模式（obs://input|output → obs_input|output/）。",
    )
    p_run.add_argument("path", nargs="?", default=".", help="项目目录，默认当前目录")
    p_run.add_argument("--obs", action="store_true", help="用真实 OBS 运行（读取 .env 凭据）")
    p_run.add_argument("--debug", action="store_true", help="启动后等 VS Code 在 debug-port 附加")
    p_run.add_argument("--debug-port", type=int, default=5678, help="debugpy 监听端口，默认 5678")

    p_pack = sub.add_parser(
        "pack", help="打包算子",
        description="校验 manifest/process.py 后打包成 program_package/<id>.tar（按 <id>/ 嵌套，未压缩）。",
    )
    p_pack.add_argument("path", nargs="?", default=".", help="项目目录，默认当前目录")
    p_pack.add_argument("-o", "--output", help="输出路径，默认 program_package/<id>.tar")
    p_pack.add_argument("--force", action="store_true", help="覆盖已存在的输出文件")

    p_debug = sub.add_parser(
        "debug", help="生成 VS Code 调试配置",
        description="生成 .vscode/launch.json（\"Attach to Op Service\"，配合 run --debug）。",
    )
    p_debug.add_argument("path", nargs="?", default=".", help="项目目录，默认当前目录")

    p_download = sub.add_parser(
        "download", help="下载依赖 wheel 并写入 requirements.txt",
        description="下载单个包的 wheel（--no-deps，不含传递依赖）到 program_package/dependency/，"
                    "按 manifest 的 cpu-arch 选 Linux+Python3.10 目标平台，并写入 requirements.txt。"
                    "平台预置包（pandas/numpy/pyarrow）会被拒绝。",
    )
    p_download.add_argument("package", help="包名，可带版本约束，如 requests 或 pillow==10.4.0")
    p_download.add_argument("path", nargs="?", default=".", help="项目目录，默认当前目录")

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
        return new.execute(args.name, args.dir, flags=flags, yes=args.yes,
                           native_tls=args.native_tls, insecure=args.insecure)

    if args.cmd == "run":
        return run.execute(args.path, obs=args.obs, debug=args.debug, debug_port=args.debug_port)
    if args.cmd == "pack":
        return pack.execute(args.path, output=args.output, force=args.force)
    if args.cmd == "debug":
        return debug.execute(args.path)
    if args.cmd == "download":
        return dep.execute(args.path, args.package)
    return 2
