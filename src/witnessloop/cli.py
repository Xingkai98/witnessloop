"""`witnessloop` 单二进制的子命令路由。

动词面刻意很小：``init`` / ``uninit`` / ``check``（design §5.1）+
``manifest build``（证据产出，design §5.2 的交互层收尾调它）。
其余动词（gate/event/status/policy upgrade）刻意不存在——
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
        default=None,
        help=f"caller workflow 引用的 reusable workflow；缺省时：已接入的仓沿用台账里的值，"
        f"否则用出厂默认 {DEFAULT_GATE_REF}",
    )
    p_init.add_argument(
        "--policy",
        default=None,
        help="用给定 JSON 文件的内容作为 policy（替换出厂默认）；缺省用出厂默认 policy。"
        "轻校验（仅要求可解析为 JSON 对象），语义合法性由 `check` 兜底",
    )

    p_uninit = sub.add_parser(
        "uninit", help="依 init-manifest.json 精确回滚 witnessloop 的接入"
    )
    p_uninit.add_argument("--root", default=".", help="目标仓根（默认当前目录）")

    p_guard = sub.add_parser(
        "guard",
        help="写代码前缺 grill 证据就拦（本地守卫；由 host 的 PreToolUse hook 调用）",
    )
    p_guard.add_argument("--root", default=".", help="目标仓根（默认当前目录）")
    p_guard.add_argument(
        "--path",
        action="append",
        default=[],
        help="写目标路径（可重复）；命中 require_change_for 才可能被拦",
    )
    p_guard.add_argument(
        "--change",
        default=None,
        help="当前 change id；缺省从 WITNESSLOOP_CHANGE / 分支名首段推（且须命中现存 change 目录）",
    )

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

    p_manifest = sub.add_parser("manifest", help="review manifest 操作（证据产出）")
    manifest_sub = p_manifest.add_subparsers(
        dest="manifest_command", metavar="<子命令>"
    )
    p_build = manifest_sub.add_parser(
        "build",
        help="产出 check 认的 review manifest（固定 base 与 revision 时幂等；"
        "不 auto-commit）",
    )
    p_build.add_argument("--root", default=".", help="目标仓根（默认当前目录）")
    p_build.add_argument(
        "--change",
        required=True,
        help="change id——`changes/<id>/` 的**单段**目录名，不能含 `/`",
    )
    p_build.add_argument("--stage", required=True, help="审阅阶段名（如 grill / building）")
    p_build.add_argument(
        "--report",
        required=True,
        help="change 目录内的报告路径，如 reviews/building-review.md（必须在 reviews/ 下）",
    )
    p_build.add_argument(
        "--reviewer-run-id",
        default=None,
        help="审阅者的 run id；缺省走 agentenv 的策略（WITNESSLOOP_REVIEWER_RUN_ID → "
        "WITNESSLOOP_RUN_ID → **确定性兜底**）。兜底同样幂等（固定 base 与 revision 时），"
        "只是那个 id 是「审阅目标的指纹」、不代表真实 run 身份",
    )
    p_build.add_argument(
        "--author-run-id",
        default=None,
        help="作者的 run id；缺省同上（..._AUTHOR_RUN_ID → WITNESSLOOP_RUN_ID → "
        "确定性兜底）",
    )
    p_build.add_argument(
        "--base",
        default=None,
        help="base ref；缺省时与 check 用同一套解析（WITNESSLOOP_BASE_REF / "
        "GITHUB_BASE_REF / 主干）",
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
    if args.command == "guard":
        from witnessloop import guardcmd

        return guardcmd.run(args)
    if args.command == "check":
        from witnessloop import checkcmd

        return checkcmd.run(args)
    if args.command == "manifest":
        if args.manifest_command == "build":
            from witnessloop import manifestcmd

            return manifestcmd.run_build(args)
        print(
            "witnessloop manifest：需要子命令。目前只有 `manifest build`。",
            file=sys.stderr,
        )
        return EXIT_USAGE

    parser.error(f"未知命令：{args.command}")  # pragma: no cover
    return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
