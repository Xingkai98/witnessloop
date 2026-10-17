# Tasks: convergence-based-stop（有界批次 × 20 轮上限）

> 基线：`origin/main` `46e45b4`（2026-10-17 fetch）。本 change 只改**模板 / 适配器 / 自述 / 测试**，
> 不改 `src/` 生产代码（`check` 不解析报告正文，见 design D6）。
>
> **批次纪律**：本 tasks.md 按「批次」组织。每个批次的 `[x]` 都是**本批必须全修**的；
> `[ ]` 是后续批，不构成本批缺陷。审阅者验证时只验证本批 `[x]`。

## A. 文档重写（本批）

- [x] A1 重写 `proposal.md`：新模型（轮 = 批次闭环）、20 上限、medium+/low 口径、
  验证禁提新问题 + deferred、三种出口、落点表。
- [x] A2 重写 `design.md`：精确流程（开批 / 全修 / 验证 / 收口）、轮数计数（只有非空
  medium+ 批次算轮，收口确认不占轮）、超限 = 建议重开、两个环适用 + frontier 豁免、
  机械门禁零变化、诚实边界、风险。
- [x] A3 重写 `tasks.md`（本文件）：按批次组织，验收项覆盖新模型七要素。
- [x] A4 重写 `specs/review-termination/spec.md`：Requirement + Scenario；
  **不得出现**「按审阅 pass 计轮」的旧口径。
- [x] A5a 旧 `reviews/grill-design.md` 已被 2026-10-17 的新报告**覆盖**（报告内含
  「旧记录作废」节；git 历史 `9acdf2b` / `20f1089` 可查）。
- [ ] A5b 旧 `reviews/grill-adversarial.md` 必须由 B2 用新模型报告**覆盖**后再建
  `stage=grill-adversarial` manifest；或从 `reviews/` 移出（git 历史保留）。
  **禁止**为旧文件建 manifest（那会同时制造孤儿规则冲突与旧模型假证据）。

## B. 设计阶段独立验证（本批）

- [x] B1 独立零记忆 grill：审阅者只读 change 目录 + 仓库，产出 `reviews/grill-design.md`
  （7 条 Confirmed Decisions、每条 `来源:`、Code-Resolved、Open Questions 为「（无）」、
  User Confirmation 四个事项；自检 `grill_evidence_findings` = 0 findings）。
- [x] B1b 把 grill 的 R1–R13 逐条整合进 design / spec / proposal / tasks（不改用户拍板的
  三个参数）；`design.md` 的 `## Pre-Implementation Review` 记录整合清单。
- [ ] B2 独立零记忆对抗验证：另起审阅者默认结论有错、逐条证伪；`CHANGES_REQUESTED` ⇒ 修并再审，
  **跑到收敛（无轮数上限）**；产物 `reviews/grill-adversarial.md`（**覆盖**旧文件，先内容后证据，
  覆盖完成前不得为它建 manifest——见 A5b）。
- [ ] B3 停轮门：确认没有需要用户拍板的问题；`## User Confirmation` 写齐（用户已拍板的三个参数 +
  本 change 无新增 Open Questions）。
- [ ] B4 把对抗验证的必须修改整合回 `design.md`（若有）；记录到 `## Pre-Implementation Review`。

## C. TDD 实现（本批）

- [ ] C1 **先写红测试**：新增 `tests/test_convergence_stop.py`，钉住新模型七要素：
  ① 轮 = 非空 medium+ 批次闭环；② 验证期间新问题只进 deferred、不得当场提；③ 20 轮上限；
  ④ 超上限 `BLOCKED` +「建议推倒重开（revise the design）」；⑤ medium+ 全修；
  ⑥ low/nit 登记不修须写理由；⑦ 三种出口（`PASS` / `BLOCKED`+成因 / 超限 `BLOCKED`）。
  同时改 `tests/test_templates.py:257-258` 与 `tests/test_plugin.py:174-176` 的旧「封顶」断言，
  并加**反断言**：规范面不再出现 `3 轮封顶` / `三轮封顶` / `有界轮数` / `轮数封顶`。
  **扫描面**（显式）：`templates/review-loop.md`、`templates/grill.md`、
  `plugin/commands/review-loop.md`、`plugin/commands/grill.md`、`plugin/README.md`、
  `README.md`、`docs/design.md`、`docs/gate.md`、`tests/test_templates.py`、
  `tests/test_plugin.py`、本 change 的 spec。
  **排除**：`docs/tasks.md`、`docs/reviews/**`、`openspec/changes/archive/**`、
  其它 change 目录、`tests/test_grill_adversarial_gate.py:180`（夹具）。
- [ ] C2 跑 `uv run pytest -q`，确认新测试**红**（记录原始输出到 `reviews/building-review.md` 的测试节）。
- [ ] C2b 变异验证：临时把 `templates/review-loop.md` 的一处新措辞改回旧口径，确认新测试
  1 failed；改回后复绿（变异不提交，结果记入 building 报告）。
- [ ] C3 改 `templates/review-loop.md`：目的、执行步骤（开批/全修/验证/收口/上限）、硬约束。
- [ ] C4 改 `templates/grill.md`：时序图、对抗环步骤、写码硬条件 #2、frontier 豁免。
- [ ] C5 改 `plugin/commands/review-loop.md`：front-matter、步骤 5–7、约束。
- [ ] C6 改 `plugin/commands/grill.md`：步骤 5。
- [ ] C7 改 `plugin/README.md:37`（命令说明）。
- [ ] C8 改 `README.md:306`（核心卖点句）。
- [ ] C9 改 `docs/design.md:25`（目标第 4 条）。
- [ ] C10 改 `docs/gate.md:716`（§10 诚实边界：`BLOCKED` 是规定出口，含超上限建议重开；
  机械判据仍不解析正文）。
- [ ] C11 跑 `uv run pytest -q` 全绿；运行 `grep` 核对旧口径不再出现在规范面。
- [ ] C12 全仓 grep 复核：`docs/gate.md:407/554` 的「常量封顶 / 路径深度封顶」与本规则无关，
  不误改；`docs/reviews/*`、已归档 change 不回填。

## D. 实现后独立审阅（本批）

- [ ] D1 独立零记忆 building 审阅：另起 run，逐项验证本 tasks.md 的 `[x]`（读代码/文档确认真实存在），
  跑测试，产出 `reviews/building-review.md`（Verdict / Tasks Verification / Issues / Test Results）。
- [ ] D2 `CHANGES_REQUESTED` ⇒ 按批次模型修 + 验证，直到 `PASS`；每次修复补回归测试/文档守卫。
- [ ] D3 三份 stage manifest：`grill`、`grill-adversarial`、`building` 各一份，绑定最终 revision。
- [ ] D4 `witnessloop check --base origin/main --head HEAD` 判绿（记录原始输出）。

## E. 合入与归档（本批）

- [ ] E1 开 PR，正文引用 issue #24 与本 change 的 spec；**`--merge` 合入**（用户已授权）。
- [ ] E2 合入后按仓规矩归档：纯 move 独立提交（active → `openspec/changes/archive/2026-10-17-convergence-based-stop/`）；
  manifest 用归档目录名重绑；backlog 清理（若本仓有对应条目）。
- [ ] E3 归档提交后重跑 `witnessloop check` 判绿。
- [ ] E4 issue #24 写完成说明并关闭。

## 验收清单（对应 spec）

- [ ] V1 `templates/review-loop.md` 逐条含新模型七要素。
- [ ] V2 `templates/grill.md` 的对抗环写明「与 review-loop 同构」+ 20 上限 + 三出口；
  frontier 追问轮显式豁免。
- [ ] V3 适配器（`plugin/commands/*.md`）不复制模板正文，只接线；同步新口径。
- [ ] V4 规范面（`templates/`、`plugin/`、`README.md`、`docs/design.md`、`docs/gate.md`）
  不再有 `3 轮封顶` / `三轮封顶` / `有界轮数` / `轮数封顶`。
- [ ] V5 `specs/review-termination/spec.md` 无「按审阅 pass 计轮」旧口径。
- [ ] V5b grill R1–R13 的文本落点齐全：第 20 轮自身未收口、验证重试终止点、安全漏洞例外、
  severity 冻结、deferred 传递、轮数累计、收口确认、累积 low/nit、frontier 边界、
  两环 `BLOCKED` 映射、旧 review/孤儿处置。
- [ ] V6 `uv run pytest -q` 全绿。
- [ ] V7 三份 manifest + `witnessloop check` 绿。
- [ ] V8 PR 已 `--merge` 合入；归档为纯 move；issue #24 已关闭。
