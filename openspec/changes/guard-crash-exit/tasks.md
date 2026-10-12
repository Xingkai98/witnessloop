# Tasks: guard-crash-exit

> 依据 `design.md`（**已收敛**——对抗 R1–R5（R5=PASS）+ 用户 Q1/Q2 已答）。**实现完成**（402 passed；待 G1 独立 review-loop）。
> 原则：**测试先行（TDD）**——每个能力先写失败测试再实现。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/guard-exit-codes/spec.md`）；两段提交须在其齐备后才开始。

## A. 退出码常量（D2）—— 待实现

- [x] A1 单测：`C.EXIT_INTERNAL == 4` 且 `!= C.EXIT_FAIL`（漂移守卫，先红）
- [x] A2 实现：`constants.py` 新增 `EXIT_INTERNAL = 4` + 注释（为何 4 / 只 `guard` 用 / ≠1）

## B. 崩溃兜底（D1/D3）—— 待实现

- [x] B1 单测（先红）：monkeypatch `evidence.grill_evidence_findings_in_change` 抛 `RuntimeError`
      ⇒ `entry.main(["guard", …])` 退 `EXIT_INTERNAL`（非 1）+ 一行诊断
- [x] B2 单测（先红）：`from witnessloop import guardcmd` 的 `ImportError` ⇒ 退 `EXIT_INTERNAL`
      ——⚠️ **R3 M4**：**只** `sys.modules[...]=None` **不够**：整份 suite 里 `guardcmd` 早已被导入、且是 `witnessloop` 包的属性
      ⇒ `from witnessloop import guardcmd` 走 `getattr` **不抛**、用例不稳 ⇒ 必须**同时** `monkeypatch.delattr(witnessloop, "guardcmd", raising=False)`
- [x] **B3（⚠️ 用户 Q2）** 单测（先红）：**`cli.py` 自身 import 失败**（「安装破损」那个洞）⇒ 退 `EXIT_INTERNAL`
      （`sys.modules["witnessloop.cli"]=None` + `delattr(witnessloop, "cli")`，再调 `entry.main(["guard", …])`）
- [x] **B4（⚠️ 用户 Q2）** 单测（先红）：入口对**非 `guard`** verb 的崩溃退 **1**（fail-closed）
      （如 monkeypatch 让 `cli.main` 抛 ⇒ `entry.main(["check", …])` 返回 1，**不是** 4）
- [x] B5 实现：新建 `src/witnessloop/entry.py`（**依赖自由**、不 import witnessloop；`_EXIT_INTERNAL = 4`；argv 判 verb）
- [x] B6 实现：`pyproject.toml` 的 `[project.scripts]` 改指 `witnessloop.entry:main`；`__main__.py` 改从 `entry` 导入
- [x] B7 实现：`tests/conftest.py` 的 `cli` fixture 改调 `entry.main`（让 B 组走真实入口路径）
- [x] B8 实现：`guardcmd.py` docstring 指「崩溃兜底在进程入口 `entry.py`」
- [x] B9 注释/文档声明不变量：「拦」(1) 的唯一来源 = `guardcmd.run` 的显式 `return C.EXIT_FAIL`；
      入口只对 `guard` verb 的崩溃给 4、其余给 1
- [x] B10 守卫：`entry._EXIT_INTERNAL == C.EXIT_INTERNAL == 4`（两处字面量防漂移）
- [x] **B11（⚠️ R5）** 单测（承重性质，此前无覆盖）：`entry.main(["--help"])` / `["--version"]` ⇒ `SystemExit(0)`；
      `entry.main(["bogus"])` ⇒ `SystemExit(2)`（**不被** `except Exception` 吞）

## C. 读点归一（D4/D5）—— 待实现（**Q1 已答：甲案**）

- [x] C1 实现：`policy.py:129` 补 `UnicodeDecodeError` ⇒ 抛 `PolicyError`（D5，无争议）
- [x] C2 单测（先红）：字节坏 **policy** ⇒ `guard` 退 `EXIT_PASS`（放行，与 policy 非法同归）
- [x] C3 实现：`evidence.py:165`（`_read_json`）补捕 `UnicodeDecodeError` ⇒ **与 JSON 坏/缺失同归**（走既有「无 stage=grill…」finding）
      ——⚠️ **R3 M1**：**不要**在这里新造「清单无法解码：<file>」文案（既要求点名文件、又要求与 JSON 坏同归是**不可兼得**的）
- [x] C4 单测（先红）：字节坏 **manifest** ⇒ `guard` 退 **1**，且其结论**与「JSON 坏 manifest」逐字相同**
      （断言**两案输出相等**，而非钉某个固定字符串——这才钉得住「同归」）
- [x] C5 实现 + 单测：报告读点（`evidence.py:216`）⇒ **甲案**（已裁定）：捕 `UnicodeDecodeError` ⇒ Finding「报告无法解码：<file>」⇒ `guard` 拦 / `check` 红
- [x] C6 单测（先红·补 spec 的不可验证 Scenario）：`main(["check",…])` 遇无法解码的 evidence **不返回 0**（仍 fail-closed）
- [x] **C7（⚠️ R2 N1）** 实现：`contract.py:176`（`_bound_report`）与 `contract.py:230`（`_validate_one`）补 `UnicodeDecodeError`
      ——**`check` 的 manifest 读点在这里**（`checkcmd.py:75` 先于 `:78`），只改 `evidence.py` 不够
- [x] **C8（⚠️ R2 N1）** 单测（先红）：字节坏 **manifest** ⇒ `main(["check",…])` **不抛异常**且非 0（干净红，非 traceback），
      **且输出点名该文件**（`check` 侧的「点名」是 spec 要求，须有测试钉住；`guard` 侧**不**点名，C4 断言其输出与 JSON 坏相等）

## D. shim（D6）—— 待验证（预期零改动）

- [x] D1 单测（先红）：`_run_shim(cli_exit=C.EXIT_INTERNAL) == 0`（放行）
- [x] D2 回归：`_run_shim(cli_exit=C.EXIT_FAIL) == 2`（拦仍映射到 block）**仍绿**
- [x] D3 结论：`plugin/hooks/guard.sh` **零改动**

## E. 回归（语义未动）—— 待验证

- [x] E1 既有 `guard` 三态用例（拦=1 / 放=0 / 未接入=3 / skip）**仍绿**
- [x] E2 本仓 `dogfood-bootstrap` 与 `grill-evidence-gate` 的 `check` **仍绿**

## F. 文档（D7）—— 待实现

- [x] F1 `docs/gate.md §6`：`guard` 表加行 `4 | 内部错误（fail-open，不拦）`；注补「仅 `guard` 产出 4」
- [x] F2 `docs/gate.md §8`：`guard` 段补「崩溃/内部错误 ⇒ 放行」（fail-open）+ 读点归一口径
- [x] F3 **订正既有漂移**：`README.md:35` 与 `docs/adr/0001-local-guard-hook.md:16` 的「拦（exit 2）」⇒「CLI 退 1（shim 映射成 CC 的 2）」
- [x] F4 写明**对**接入方**的行为变更**（甲案：损坏证据从放行变拦；若选乙案则无此变更）

## G. 证据链与收尾

- [x] **G0**（顺序约束 · 自锁防线）：停轮拿到 Q1/Q2 答复 → 写 `grill-review.md` 的 `## User Confirmation` →
      `manifest build --stage grill`（**先放行 `src/**` 写入**）→ 内容提交后**必须重跑覆盖**成最终 manifest。
      ⚠️ **重跑是承重的**（R3 实测：不重跑 ⇒ `check` 判 stale 红）；且**重跑前先定稿 `tasks.md`/`specs`**（否则 hash 漂移，白跑）
- [x] G1 独立 `review-loop`（PASS 或 3 轮封顶）
- [x] G2 两段提交 + `manifest build` ×（grill / grill-adversarial / building）+ `check` 绿
- [x] G3 PR（branch protection 已开：require PR + required check `gate / check`）→ 合入 → 关 issue #9

## 明确不做（本 change）

改 `check` 的退出码语义（只改读点归一：崩溃→干净红） · 逐点 try（改为通用兜底 + 源头归一） · shim 改动 ·
签名/防伪造 · 私有仓（#6）。（`cli` 自身 import 失败的兜底**已纳入本 change**——用户 Q2 裁定。）

## 实测记录（实现期）

- **402 passed**（基线 388 + 入口 6 + 读点/check 8）；`uv build` + `uvx --from wheel witnessloop --version` 通过（CI 同款冒烟）。
- **G0 端到端**（本 worktree，非纸面）：build 前 `guard --path src/**` **exit 1（拦）**→ build 出 `stage=grill` manifest 后 **exit 0（放）**。
- **头号修复实测**：坏 `constants.py`（模拟坏发布）下，`python -m witnessloop guard` ⇒ **4**（fail-open）、`check` ⇒ **1**（fail-closed）；
  对照：旧入口 `from witnessloop.cli import main` 直接抛 ⇒ 退 1 ⇒ 会被 shim 当 block。
- **E2 回归**：`dogfood-bootstrap` / `grill-evidence-gate` 的 grill 证据仍 findings=0。
- **真实 console script** 已指向 `witnessloop.entry`（`.venv/bin/witnessloop` 实测含 `from witnessloop.entry import main`）。
