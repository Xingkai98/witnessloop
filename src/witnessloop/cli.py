"""`witnessloop` 单二进制的子命令路由。

v1 只暴露 3 个动词：``init`` / ``uninit`` / ``check``（design §5.1）。
其余动词（gate/event/status/policy/manifest/upgrade）刻意不存在——
argparse 会对未知子命令给出明确的 invalid choice 报错，不会静默吞掉。
"""

from __future__ import annotations

import argparse
import sys

from witnessloop import __version__
from witnessloop.constants import DEFAULT_GATE_REF, EXIT_USAGE


class _Parser(argparse.ArgumentParser):
    """把 usage 错误固定到 EXIT_USAGE，避免与业务退出码混淆。"""

    def error(self, message: str):  # pragma: no cover - argparse plumbing
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="witnessloop",
        description="把 agent 写代码的证据绑进 CI required check（fail-closed）。",
    )
    parser.add_argument(
        "--version", action="version", version=f"witnessloop {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="<命令>")

    p_init = sub.add_parser(
        "init", help="接入目标仓：幂等 / 只增不改 / 不 auto-commit"
    )
    p_init.add_argument("--root", default=".", help="目标仓根（默认当前目录）")
    p_init.add_argument(
        "--dry-run", action="store_true", help="只打印将做的改动，不落盘"
    )
    p_init.add_argument(
        "--gate-ref",
        default=DEFAULT_GATE_REF,
        help=f"caller workflow 引用的 reusable workflow（默认 {DEFAULT_GATE_REF}）",
    )

    p_uninit = sub.add_parser(
        "uninit", help="依 init-manifest.json 精确回滚 witnessloop 的接入"
    )
    p_uninit.add_argument("--root", default=".", help="目标仓根（默认当前目录）")

    p_check = sub.add_parser(
        "check", help="CI 入口：校验 change 契约 / 审阅证据 / 受保护写入（fail-closed）"
    )
    p_check.add_argument("--root", default=".", help="目标仓根（默认当前目录）")
    p_check.add_argument(
        "--base",
        default=None,
        help="diff 的 base ref；缺省时依次取 WITNESSLOOP_BASE_REF / "
        "GITHUB_BASE_REF(→origin/<ref>) / origin/main|main",
    )
    p_check.add_argument(
        "--head", default=None, help="diff 的 head ref（默认 HEAD）"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    # 惰性 import：让骨架（提交 A）无需命令实现即可独立成立。
    if args.command == "init":
        from witnessloop import initcmd

        return initcmd.run(args)
    if args.command == "uninit":
        from witnessloop import uninitcmd

        return uninitcmd.run(args)
    if args.command == "check":
        from witnessloop import checkcmd

        return checkcmd.run(args)

    parser.error(f"未知命令：{args.command}")  # pragma: no cover
    return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
