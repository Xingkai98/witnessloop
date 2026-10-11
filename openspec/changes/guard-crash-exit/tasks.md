# Tasks: guard-crash-exit

> 依据 `design.md`（**待收敛**——Q1/Q2/Q3 未确认前不得动实现代码）。
> 原则：**测试先行（TDD）**——每个能力先写失败测试再实现。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/guard-exit-codes/spec.md`）；两段提交须在其齐备后才开始。

## A. 退出码常量（D2）—— 待实现

- [ ] A1 单测：`C.EXIT_INTERNAL == 4` 且 `!= C.EXIT_FAIL`（漂移守卫，先红）
- [ ] A2 实现：`constants.py` 新增 `EXIT_INTERNAL = 4` + 注释（为何 4 / 只 `guard` 用 / ≠1）

## B. 崩溃兜底（D1/D3）—— 待实现

- [ ] B1 单测（先红）：非法 UTF-8 的 `stage=grill` 报告 ⇒ `guard --path src/x.py` 退 **非 1**（`EXIT_INTERNAL`）+ 诊断
- [ ] B2 单测（先红）：monkeypatch `evidence.grill_evidence_findings_in_change` 抛 `RuntimeError` ⇒ 同上（通用路径）
- [ ] B3 单测（先红）：`from witnessloop import guardcmd` 的 `ImportError`（`sys.modules[...]=None`）⇒ 退 `EXIT_INTERNAL`（import 缺口）
- [ ] B4 实现：`cli.py` 的 `guard` 分支包 `try/except Exception`（含 import）；`guardcmd.py` docstring 补安全网出处

## C. shim（D5）—— 待验证（预期零改动）

- [ ] C1 单测（先红）：`_run_shim(cli_exit=C.EXIT_INTERNAL) == 0`（放行）
- [ ] C2 回归：`_run_shim(cli_exit=C.EXIT_FAIL) == 2`（拦仍映射到 block）**仍绿**
- [ ] C3 结论：`plugin/hooks/guard.sh` **零改动**（只认 1，其余放行）

## D. 回归（语义未动）—— 待验证

- [ ] D1 既有 `guard` 三态用例（拦=1 / 放=0 / 未接入=3 / skip）**仍绿**
- [ ] D2 本仓 `dogfood-bootstrap` 与 `grill-evidence-gate` 的 `check` **仍绿**（未改 `check`）

## E. 文档（D6）—— 待实现

- [ ] E1 `docs/gate.md §6`：`guard` 表加行 `4 | 内部错误（fail-open，不拦）`；注补「仅 `guard` 产出 4」
- [ ] E2 `docs/gate.md §8`：`guard` 段补「崩溃/内部错误 ⇒ 放行」（fail-open）
- [ ] E3 grep 并同步 `README.md` / `docs/design.md` 里相关 `guard` 退出码叙述（若有）

## F. 证据链与收尾

- [ ] F1 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] F2 两段提交 + `manifest build` ×（grill / grill-adversarial / building）+ `check` 绿
- [ ] F3 PR（本仓 branch protection 已开：require PR + required check `gate / check`）→ 合入 → 关 issue #9

## 明确不做（本 change）

改 `check` 的退出码语义 · 逐点 try（改为顶层兜底） · shim 改动 · 签名/防伪造 · 私有仓（#6）。
（`evidence.py` 读点是否硬化 = **Q2**，未定则不做。）
