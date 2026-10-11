# Design: guard-crash-exit

> 状态：**草稿**（待设计 grill + 对抗验证收敛 → 停轮用户确认）。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。
> 关联 issue：witnessloop **#9**（低、非阻塞）。

## 0. 一句话

让 `guard` 的「**拦**」成为**只由「拦」自己产生**的退出码——**未预期异常绝不落进这个码**
（fail-open），并把该不变量钉成回归测试。

## 1. 现状（实测，带 `文件:行号`）

- **崩溃路径**：`cli.main`（`cli.py:136-173`）不 catch 任何异常；`__main__.py:6` 只做 `sys.exit(main())`。
  任何从 `guardcmd.run` 冒出的未捕获异常 ⇒ CPython 以 **status 1** 结束。
- **宿主映射**：`plugin/hooks/guard.sh:38-41` —— `if [ "$status" -eq 1 ]; then exit 2; fi; exit 0`。
  **1 → CC 的 2（block）**。
- ⇒ **崩溃 = 误拦**。真实触发例：`evidence.py:216`
  `return grill_evidence_findings(report.read_text(encoding="utf-8"), …)` ——
  报告是**非法 UTF-8** 时抛 `UnicodeDecodeError` ⇒ 冒泡 ⇒ 退 1 ⇒ CC 当 block ⇒ **每个 `Write|Edit` 被拦**。
- **「拦」= 1 的由来**：`guardcmd.py:129` `return C.EXIT_FAIL`（`constants.py:81`）。
  改这个值的动机是**避开** argparse 的 **2**（`cli.py:19-23`，`_Parser.error → EXIT_USAGE`）——
  见 change `grill-evidence-gate` D5 / 回归审阅 **Issue 3**（旧版 CLI 不认识 `guard` ⇒ argparse 退 2 ⇒
  直传被当 block）。**代价**：1 与 Python 崩溃码同值 ⇒ 本 issue。
- **`check` 侧同崩溃点**：`checkcmd` 也调 `grill_evidence_findings_in_change` ⇒ 同样会崩；
  但 `check` 崩溃退 1 = 「**未通过**」（`constants.py:81`）= **fail-closed，语义正确**（CI 锚本就该 fail-closed）。
  ⇒ 本 change **不改 `check` 语义**（仅报错难看，属可读性）。
- **退出码今日占用**：`0/1/2/3`（`constants.py:80-83`）；**4 空闲**（`grep EXIT_` 全树 0 命中 4）。

## 2. 决策

### D1 根因与方向：选 **A（顶层兜底，`block` 保持 1）**，**否 B（专用 block 码）**

- **两个方向**（issue #9 原列）：
  - **A**：`guard` 加顶层兜底——未预期异常 → 一行诊断 → 退**非 1**（fail-open）。
  - **B**：把「拦」挪到**专用码**（如 4），让崩溃退 1 天然**非** block。
- **为什么否 B ——版本偏斜（决定性）**：CLI 与 shim **分开分发**（CLI 在 `PATH`，shim 随 plugin 落盘），
  两者版本**可以不一致**：
  - **旧 shim（映射 1→2）+ 新 CLI（拦=4）** ⇒ 4 不被任何分支命中 ⇒ `exit 0` ⇒ 守卫**静默永不拦**
    （fail-open 回归——比崩溃误拦更糟，因为它**无声**）。
  - 若让**新 shim 兼映射 {1,4}→2** 以兼容旧 CLI，则**新 CLI 的崩溃（退 1）又落进 2** ⇒ **原 bug 复活**。
  - ⇒ B 只能二选一：**破坏兼容**或**复活 bug**。
- **A 对版本偏斜免疫**：不动 `block=1`。矩阵：
  | shim \ CLI | 旧 CLI | 新 CLI |
  |---|---|---|
  | 旧 shim（1→2） | 拦✓ 崩✗ | **拦✓ 崩✓**（崩溃退 4 ≠ 1 ⇒ 放行） |
  | 新 shim（1→2，**不变**） | 拦✓ 崩✗ | 拦✓ 崩✓ |
  （「崩✗」= 旧 CLI 与本 change 无关，本来就有此 bug；本 change 修的是**新 CLI** 侧。）
- **A 的语义代价**：「1」保持双重来源（显式 block / 无兜底时的崩溃）——
  **由 D2+D3 消除**：兜底后，「1」**只**由 `return C.EXIT_FAIL` 产生。

### D2 崩溃的退出码：新增 `EXIT_INTERNAL = 4`（fail-open，**绝不等于 1**）

- 语义：`4 = guard 内部错误（fail-open，不拦）`。
- **为什么不是 0**：0 与「正常放行」混淆——日志里看不出**发生过崩溃**（诊断性丢失）。
  4 落在 1 之外、可诊断、且 shim **无需认识它**（shim 只认 1；其余一律放行）。
- **为什么不是 3**：3 = 未接入（`EXIT_NOT_ONBOARDED`，`guardcmd.py:95`），语义已占。
- **仅 `guard` 使用**：`check` 不返回 4（其崩溃仍退 1 = 未通过，见 §1）。文档须写明这处非对称。

### D3 落点：`cli.main` 的 **`guard` 分支**兜底（覆盖 **import + run**）

- 形态：`cli.py` 里
  ```python
  if args.command == "guard":
      try:
          from witnessloop import guardcmd
          return guardcmd.run(args)
      except Exception as exc:      # SystemExit/KeyboardInterrupt 是 BaseException，不受影响
          print(f"guard：内部错误（{type(exc).__name__}: {exc}）——按放行处理（fail-open）。",
                file=sys.stderr)
          return EXIT_INTERNAL
  ```
- **为什么在 `cli.main` 而不只在 `guardcmd.run` 内**：`from witnessloop import guardcmd`
  的 **ImportError**（半装/坏装/版本偏斜导致 `evidence` 等缺失）**同样是「崩溃退 1」这一类**——
  放在 **dispatch 边界**才能一并兜住（与 `_Parser.error` 在边界修 usage 错误同构）。
  只在 `run` 内兜会漏掉 import 缺口。
- **不动 `check`/`init`/`uninit` 分支**：它们的崩溃退 1 = fail(-closed)，语义正确（D1 / §1）。
- **不 catch `BaseException`**：`KeyboardInterrupt` / `SystemExit` 应照常传播
  （`argparse` 的 `--help`/用法错误都是 `SystemExit`，且发生在 dispatch **之前**）。

### D4 触发例的归宿：非法 UTF-8 ⇒ **放行（fail-open）**，且**不在本 change 硬化**

- 非法 UTF-8 报告 ⇒ `UnicodeDecodeError` ⇒ 兜底 ⇒ **退 4 ⇒ 放行**。
- **这是有意的**：报告读不出 = 「**无法判定**」⇒ 本地守卫 fail-open（与 D8「防遗忘不防对抗」一致；
  锚仍是 CI 的 `check`——它读同一份会崩 → 退 1 = **红**）。
- **是否顺带「硬化」`evidence.py:216` 的读点**（捕 `UnicodeDecodeError` → 产出一条
  「报告无法解码」Finding）——见 **Open Question Q2**：
  - 硬化后 **`check` 变干净的红**（而非 traceback）；但 **`guard` 转为「拦」**（证据不可判定 = 不完备）。
  - 这与 D2/D1 的「崩溃 ⇒ 放行」**方向相反**——两种都自洽，取决于「**报告存在但读不出**」算不算
    「证据不完备」。**属语义裁定 ⇒ 交用户**。

### D5 shim **不改**

- `plugin/hooks/guard.sh:38-41` 现有逻辑「**只把 1 映射成 block，其余一律 0**」
  对新增的 4 **天然正确**（4 ≠ 1 ⇒ 落 `exit 0`）⇒ **零改动**。
- 这也正是 D1 选 A 的收益之一：**shim 与 CLI 之间没有新增耦合**。

### D6 文档 + 漂移守卫

- `docs/gate.md §6`：`guard` 表加一行 `4 | 内部错误（fail-open，**不拦**）`；
  §6 的注补一句「4 只用 `check` 不产出，仅 `guard`」；§8 `guard` 段补「崩溃/内部错误 ⇒ 放行」。
- `docs/design.md`：grep 确认是否有 `guard` 退出码叙述需同步（§5.1）。
- `README.md`：grep 是否有 `guard` 退出码叙述需同步。
- **新增漂移守卫**（`tests/test_guard.py` 或 `test_docs.py`）：钉「`guard` 的 block 码 = 1 且
  **内部错误码 4 ≠ 1**」——防日后有人把 4 改回 1（那会**静默复活本 bug**）。
  当前**无任何测试**约束 4 的取值 ⇒ 漏改不会红（同 `grill-evidence-gate` 的 D7 教训）。

### D7 自伤面：**无既有测试变红**

- 不改 CLI **动词面**（只加一个退出码常量）⇒ `tests/test_cli.py:50-54`（动词集恰 5 个）**不红**。
- 不改 **plugin 文件清单**（shim 零改动）⇒ `tests/test_plugin.py:64-71`（恰 N 文件）**不红**。
- `guard` 既有用例断言 `code == BLOCKED`（=1）与 `code == C.EXIT_PASS`——**语义不变，仍绿**。
- `src/**` 在 `require_change_for` 中，但本 change 目录在场 ⇒ **不自锁**（同 B 的 R11）。

## 3. 接线点（实现清单）

- `src/witnessloop/constants.py`：新增 `EXIT_INTERNAL = 4` + 注释（为何 4、只 guard 用、≠1）。
- `src/witnessloop/cli.py`：`guard` 分支包 `try/except Exception`（D3）。
- `src/witnessloop/guardcmd.py`：**模块 docstring** 补一句「崩溃兜底在 `cli.main` 的 guard 分支」
  （可发现性——别让读者只读 `run` 找不到安全网）。
- `docs/gate.md` §6/§8（D6）。
- `tests/test_guard.py`：新增崩溃用例 + shim 新码用例 + 漂移守卫。

## 4. 风险

1. **R1（中，误判方向）**：若选了 B，会引入**静默 fail-open**（旧 shim + 新 CLI）或**复活 bug**（新 shim 兼映射）⇒ D1 以版本偏斜矩阵否定之。
2. **R2（中）**：`except Exception` 可能**掩盖真 bug**（本可暴露的异常被吞成「放行」）⇒ 缓解：诊断行含**异常类型 + message**，且只作用于 `guard`（不扩散到 `check`）。
3. **R3（中）**：D4 的方向反转（硬化 ⇒ 拦）与「崩溃 ⇒ 放」**并存时自相矛盾** ⇒ 由 Q2 单项裁定，**不两立**。
4. **R4（低）**：`4` 与任何宿主语义冲突？——shim 只输出 0/2 给 CC；`4` 仅出现在**直接跑 CLI** 的场景。
   CC 的 hook 约定里非 0/2 的退出码 = 「非阻塞错误」（会显示 stderr、**不拦**）——与本意图一致。
5. **R5（低）**：只改 `guard` 不改 `check` ⇒ **非对称**，须在文档写明（D2/D6）。
6. **R6（低）**：崩溃点的**清单**不完备（当前只知 `evidence.py:216` 一处）⇒ 兜底是**通用**的（不枚举），
   故新增崩溃源无需改代码——这正是选「顶层兜底」而非「逐点 try」的理由。

## 5. 测试策略（TDD）

- **先红**：
  - `test_guard_crash_is_not_a_block`：造一份 `stage=grill` 合格证据 → 把报告覆写成**非法 UTF-8**
    → `guard --path src/x.py` ⇒ 断言 `code == C.EXIT_INTERNAL`（**非 1**）+ stderr 含诊断；
    并断言 `code != BLOCKED`。
  - `test_guard_survives_an_arbitrary_internal_error`：monkeypatch
    `evidence.grill_evidence_findings_in_change` 抛 `RuntimeError` ⇒ 同断（**通用路径**）。
  - `test_guard_dispatch_survives_a_broken_import`：`monkeypatch.setitem(sys.modules,
    "witnessloop.guardcmd", None)` ⇒ `from witnessloop import guardcmd` 抛 `ImportError` ⇒ 走 `cli.main`
    guard 分支 ⇒ 退 `EXIT_INTERNAL`（**import 缺口**，D3）。
  - `test_shim_allows_the_internal_error_code`：`_run_shim(cli_exit=C.EXIT_INTERNAL) == 0`。
- **回归（不变红）**：
  - `test_shim_maps_guard_block_to_the_hosts_block_code`（1 → 2）**仍绿**。
  - 既有 `guard` 三态用例**仍绿**（语义未动）。
  - **漂移守卫**：断言 `C.EXIT_INTERNAL != C.EXIT_FAIL` 且 `C.EXIT_INTERNAL` 未被
    `check` 用作「未通过」（可用源码扫描或直接断言常量值 4）。

## 6. 文档影响

- `docs/gate.md`：§6 `guard` 表 + 注、§8 `guard` 段（D6）。
- `README.md` / `docs/design.md`：grep `guard` 退出码叙述，按需同步。
- **新漂移守卫测试**：钉 `EXIT_INTERNAL ≠ EXIT_FAIL`（D6）。

## 7. Pre-Implementation Review

> 待 grill + 对抗验证后填写（已确认决策 / 必须修改（已整合）/ Code-Resolved 结论）。

## 8. Open Questions（停轮待用户确认）

- **Q1** 方向：**A**（顶层兜底，`block` 保持 **1**）还是 **B**（把「拦」挪到专用码）？
  （每条的具体例子与推荐答案见 `reviews/grill-review.md` 的 `## Open Questions`。）
- **Q2** 是否**顺带硬化** `evidence.py:216` 的读点（非法 UTF-8 → Finding）？
  即「报告存在但**读不出**」对 `guard` 是**拦**还是**放**？
- **Q3** 崩溃退出码取值：**4**（可诊断，推荐）还是 **0**（最简）？
