"""aishipbox CLI entry point — dispatch to algo or op subcommand groups."""

from __future__ import annotations

import sys
from typing import List, Optional

from aishipbox import __version__


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)

    if not argv:
        _print_usage()
        sys.exit(2)

    first = argv[0]
    if first in ("-h", "--help"):
        _print_usage()
        sys.exit(0)

    if first in ("-v", "--version"):
        print(f"aishipbox {__version__}")
        sys.exit(0)

    if first == "algo":
        from aishipbox import algo
        return algo.dispatch(argv[1:])
    if first == "op":
        from aishipbox import op
        return op.dispatch(argv[1:])

    print(f"未知子命令：{first}", file=sys.stderr)
    _print_usage(file=sys.stderr)
    return 2


def _print_usage(file=None) -> None:
    print(
        "aishipbox - JAC PanguLM 算法服务与自定义算子开发 CLI\n\n"
        "用法：\n"
        "  aishipbox algo <命令> [参数...]     管理算法服务项目\n"
        "  aishipbox op   <命令> [参数...]     管理自定义算子项目\n"
        "  aishipbox --version                 显示版本\n"
        "  aishipbox --help                    显示此帮助\n",
        file=file if file is not None else sys.stdout,
    )


if __name__ == "__main__":
    sys.exit(main())
