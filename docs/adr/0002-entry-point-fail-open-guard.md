# ADR 0002：崩溃兜底放在**进程入口**，不放在 `cli.main` 的 guard 分支

- 状态：已接受（change `guard-crash-exit` / issue #9）
- 日期：2026-10-12

## 背景

`guard` 的「拦」用退出码 **1**（见 [ADR 0001](./0001-local-guard-hook.md) 与 change `grill-evidence-gate`，
为避开 argparse 的 2）。而 **1 也是 CPython 未捕获异常的退出码**，且 `plugin/hooks/guard.sh` 把 **1 → CC 的 2（block）**
⇒ `guard` **崩溃 = 误拦每个 `Write|Edit`**。已实测的触发源：非法 UTF-8 的证据/policy 文件经 `read_text` 抛
`UnicodeDecodeError`（多处读点的 `except` 只列了 `OSError, json.JSONDecodeError`，漏了它）。

设计期 grill + 对抗验证的初版结论是：把兜底放在**`cli.main` 的 `guard` 分支**（`try/except Exception` 包住
`from witnessloop import guardcmd` + `guardcmd.run`）。对抗验证随后证伪了这个**覆盖面**：`cli.py` **自身**的
**模块级** import（`from witnessloop import __version__` / `from witnessloop.constants import …`）发生在
`main()` **之前** —— 真实 console script 就是 `from witnessloop.cli import main; sys.exit(main())`，
**不在我们任何代码的 try 内**。实测：坏 `constants.py` ⇒ `witnessloop guard` 退 **1** ⇒ 被 shim 当 block。

## 决策

**把崩溃兜底放在进程入口**：新增 `src/witnessloop/entry.py`（**刻意不 import witnessloop 任何模块**——
它存在的意义正是「witnessloop 自己 import 不起来时」仍能兜底），`pyproject.toml` 的 console script 与
`__main__.py` 都改指 `entry.main`；测试的 `cli` fixture 一并改调 `entry.main`（这样用例走的是**真实入口路径**）。

- 入口的 `try` 同时包住 **「导入 `cli`」** 与 **「跑 `cli`」** ⇒ 连 `cli.py` 自身 import 失败也覆盖。
- 只捕 `Exception`（`SystemExit` / `KeyboardInterrupt` 是 `BaseException`）⇒ `--help`(0) / 用法错误(2) 照常传播。
- 退出码按 **argv 第一词**分：`guard` ⇒ **4**（fail-open，**绝不等于 1**）；其余 ⇒ **1**
  （`check` = 未通过 = fail-closed；`init`/`uninit`/`manifest build` = 失败）。「4」只属于 `guard`。
- **单一兜底**：不再在 `cli.main` 里另设 guard 分支。`cli.main` 仍是可用的进程内 API，但兜底是**进程边界**的职责。
- `constants.EXIT_INTERNAL = 4` 与入口的字面量 `4` 必须同值 —— 由测试钉住（入口不可 import，只能用字面量）。

## 备选（与为何否）

1. **兜底放 `cli.main` 的 guard 分支**（初版设计）——否：**盖不住** `cli.py` 自身的模块级 import 失败（已实测）。
2. **把「拦」挪到专用退出码**（如 4），让崩溃退 1 天然非 block——否：CLI 与 shim **分开分发**（无版本互钉），
   偏斜下要么**静默永不拦**（旧 shim + 新 CLI），要么**复活原 bug**（新 shim 兼映射 1）。
   见 change `guard-crash-exit` 的 D1 版本偏斜矩阵。
3. **让 shim 判一个「block marker」**——否：同样引入偏斜风险（旧 CLI 无 marker ⇒ 新 shim 静默永不拦）。
4. **只收窄声明、把「安装破损」记为边界**——否：**用户裁定「修掉它」**（2026-10-12）。

## 后果

- 代价：多一个模块 + packaging 改动（console script 入口）；`cli.main` 的直接调用者（除测试外）不自带兜底。
- 收益：`guard` 的「拦」(1) 成为**唯一**由显式判定产生的退出码——**任何**崩溃（含 witnessloop 自己
  导入不起来）都不会被宿主误判成「拦」。这是 issue #9 的完整闭合。
