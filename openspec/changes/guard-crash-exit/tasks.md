# Tasks: guard-crash-exit

> 依据 `design.md`（**已收敛**——grill + 对抗验证 R1 已整合；**Q1/Q2 未确认前不得动实现代码**）。
> 原则：**测试先行（TDD）**——每个能力先写失败测试再实现。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/guard-exit-codes/spec.md`）；两段提交须在其齐备后才开始。

## A. 退出码常量（D2）—— 待实现

- [ ] A1 单测：`C.EXIT_INTERNAL == 4` 且 `!= C.EXIT_FAIL`（漂移守卫，先红）
- [ ] A2 实现：`constants.py` 新增 `EXIT_INTERNAL = 4` + 注释（为何 4 / 只 `guard` 用 / ≠1）

## B. 崩溃兜底（D1/D3）—— 待实现

- [ ] B1 单测（先红）：monkeypatch `evidence.grill_evidence_findings_in_change` 抛 `RuntimeError` ⇒ `guard` 退 `EXIT_INTERNAL`（非 1）
- [ ] B2 单测（先红）：`from witnessloop import guardcmd` 的 `ImportError`（`sys.modules[...]=None`）⇒ 退 `EXIT_INTERNAL`
- [ ] B3 实现：`cli.py` guard 分支包 `try/except Exception`（含 lazy import）；**`cli.py:15` 的 import 必须加 `EXIT_INTERNAL`**（否则 `NameError` ⇒ 在 except 里退 1 ⇒ bug 复活）
- [ ] B4 实现：`guardcmd.py` docstring 记「兜底在 `cli.main` 的 guard 分支」+ **边界**（`cli.py` 自身 import 失败不覆盖，见 Q2）
- [ ] B5 注释声明不变量：`cli.main` guard 分支及之后，1 **只**由 `return C.EXIT_FAIL` 产生

## C. 读点归一（D4/D5）—— 待实现（**依赖 Q1 裁定**）

- [ ] C1 实现：`policy.py:129` 补 `UnicodeDecodeError` ⇒ 抛 `PolicyError`（D5，无争议）
- [ ] C2 单测（先红）：字节坏 **policy** ⇒ `guard` 退 `EXIT_PASS`（放行，与 policy 非法同归）
- [ ] C3 实现：`evidence.py:165`（`_read_json`）补捕 ⇒ 产出**可诊断** Finding「清单无法解码：<file>」（D4-2）
- [ ] C4 单测（先红）：字节坏 **manifest** ⇒ `guard` 退 **1** 且文案点名「清单无法解码」（与 JSON 坏 / 缺失一致）
- [ ] C5 实现 + 单测（**按 Q1 结果**）：报告读点（`evidence.py:216`）⇒ 甲案「拦 + 文案『报告无法解码』」/ 乙案「放」
- [ ] C6 单测（先红·补 spec 的不可验证 Scenario）：`main(["check",…])` 遇无法解码的报告**不返回 0**（仍 fail-closed）

## D. shim（D6）—— 待验证（预期零改动）

- [ ] D1 单测（先红）：`_run_shim(cli_exit=C.EXIT_INTERNAL) == 0`（放行）
- [ ] D2 回归：`_run_shim(cli_exit=C.EXIT_FAIL) == 2`（拦仍映射到 block）**仍绿**
- [ ] D3 结论：`plugin/hooks/guard.sh` **零改动**

## E. 回归（语义未动）—— 待验证

- [ ] E1 既有 `guard` 三态用例（拦=1 / 放=0 / 未接入=3 / skip）**仍绿**
- [ ] E2 本仓 `dogfood-bootstrap` 与 `grill-evidence-gate` 的 `check` **仍绿**

## F. 文档（D7）—— 待实现

- [ ] F1 `docs/gate.md §6`：`guard` 表加行 `4 | 内部错误（fail-open，不拦）`；注补「仅 `guard` 产出 4」
- [ ] F2 `docs/gate.md §8`：`guard` 段补「崩溃/内部错误 ⇒ 放行」（fail-open）+ 读点归一口径
- [ ] F3 **订正既有漂移**：`README.md:35` 与 `docs/adr/0001-local-guard-hook.md:16` 的「拦（exit 2）」⇒「CLI 退 1（shim 映射成 CC 的 2）」
- [ ] F4 写明**对**接入方**的行为变更**（甲案：损坏证据从放行变拦；若选乙案则无此变更）

## G. 证据链与收尾

- [ ] **G0**（顺序约束 · 自锁防线）：停轮拿到 Q1/Q2 答复 → 写 `grill-review.md` 的 `## User Confirmation` →
      `manifest build --stage grill`（**先放行 `src/**` 写入**）→ 内容提交后**重跑覆盖**成最终 manifest
- [ ] G1 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] G2 两段提交 + `manifest build` ×（grill / grill-adversarial / building）+ `check` 绿
- [ ] G3 PR（branch protection 已开：require PR + required check `gate / check`）→ 合入 → 关 issue #9

## 明确不做（本 change）

改 `check` 的退出码语义（只改读点归一：崩溃→干净红） · 逐点 try（改为通用兜底 + 源头归一） · shim 改动 ·
签名/防伪造 · 私有仓（#6） · **`witnessloop.cli` 自身 import 失败的兜底**（Q2，除用户要求「前移到入口」）。
