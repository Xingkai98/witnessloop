"""进程入口兜底（change guard-crash-exit / D3，issue #9）。

**为什么兜底在这里、而不在 `cli.main`**：`guard` 的「拦」用退出码 **1**，而 1 也是 CPython 未捕获异常的
退出码；`plugin/hooks/guard.sh` 把 **1 → 宿主（CC）的 2 = block** ⇒ **崩溃 = 误拦每个 `Write|Edit`**。
而 `cli.py` **自身**的模块级 import（`from witnessloop import __version__` / `from witnessloop.constants import …`）
发生在 `main()` **之前** —— 真实 console script 就是 `from witnessloop.cli import main; sys.exit(main())`，
**不在我们任何代码的 try 内**。只有**入口**能同时包住「导入 `cli`」与「跑 `cli`」。

**刻意不 import witnessloop 任何模块**：本模块存在的意义正是「witnessloop 自己导入不起来时」仍能兜底。
为此退出码用**字面量**（与 `constants.EXIT_INTERNAL` 同值，由 `tests/test_entry.py` 钉住等值）。

**不变量**：「拦」(1) 只由 `guardcmd.run` 的显式 `return C.EXIT_FAIL` 产生；入口只对 **`guard`** verb 的
未预期异常退 `EXIT_INTERNAL`，其余 verb 退 **1**（`check` = 未通过 = fail-closed）。

**不捕 `BaseException`**：`--help`/`--version`(SystemExit 0) 与用法错误(SystemExit 2) 照常传播；
`KeyboardInterrupt` 以信号结束（shell 见 130 ≠ 1）⇒ 宿主放行。
"""

from __future__ import annotations

import sys

#: 与 `constants.EXIT_INTERNAL` 同值。此处不 import，以免「witnessloop 坏了就没法兜底」。
_EXIT_INTERNAL = 4

#: 守卫专属的 verb —— 只有它崩溃时走 fail-open（其余动词崩溃 = 失败，必须非 0 且**不是** 4 的语义）。
_GUARD_VERB = "guard"


def main(argv: list[str] | None = None) -> int:
    try:
        from witnessloop.cli import main as cli_main

        return cli_main(argv)
    except Exception as exc:  # noqa: BLE001 —— 进程边界，刻意兜住一切非 BaseException
        verb = (argv if argv is not None else sys.argv[1:])[:1]
        print(
            f"witnessloop：内部错误（{type(exc).__name__}: {exc}）",
            file=sys.stderr,
        )
        return _EXIT_INTERNAL if verb == [_GUARD_VERB] else 1
