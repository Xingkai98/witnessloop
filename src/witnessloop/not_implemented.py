"""提交 A 的占位实现：命令尚未接线时给出**明确报错**，绝不静默通过。

后续提交会逐个替换为真正的 ``initcmd`` / ``uninitcmd`` / ``checkcmd``。
"""

from __future__ import annotations

import argparse
import sys

from witnessloop.constants import EXIT_FAIL


def _stub(name: str, args: argparse.Namespace) -> int:
    print(
        f"witnessloop {name}: 尚未实现（骨架阶段占位）",
        file=sys.stderr,
    )
    return EXIT_FAIL


def run_init(args: argparse.Namespace) -> int:
    return _stub("init", args)


def run_uninit(args: argparse.Namespace) -> int:
    return _stub("uninit", args)


def run_check(args: argparse.Namespace) -> int:
    return _stub("check", args)
