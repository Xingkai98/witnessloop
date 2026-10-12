# Tasks: building-review-gate

> 依据 `design.md`（**草稿**——grill + 对抗验证收敛 + Q1/Q2/Q3 确认前不得写实现代码）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/building-evidence/spec.md`）。

## A. policy / 常量轴（D2）

- [ ] A1 实现：`constants.DEFAULT_BUILDING_STAGE = "building"`；`policy.evidence.building_stage`（缺省回落）

## B. 判定（D1/D2）—— 共用助手，避免两边各写一套

- [ ] B1 单测（先红）：`StageRequirement` 助手——**只要求存在**某 stage 的 manifest（**不**触发报告正文校验）
- [ ] B2 单测（先红）：grill 那条**行为不变**（仍校验报告正文；回归）
- [ ] B3 实现：`evidence.py` 抽出参数化助手；grill 调用改为经它（正文校验仍只在 grill 分支）
- [ ] B4 单测（先红）：改了受管控代码 + 只有 grill 证据 ⇒ `check` 红，且文案点名「缺 `stage=building` 的审阅证据」
- [ ] B5 单测（先红）：**不**触发——纯文档改动 / 只动 change 目录（无实现）⇒ 不要求 building 证据
- [ ] B6 单测（先红）：building stage 拼错（如 `buildings`）⇒ 红且**点名现有 stage**
- [ ] B7 单测（先红·回归）：**审阅后再改代码** ⇒ 既有 `_check_git_span` 判 **stale**（钉住这半边已生效）
- [ ] B8 实现：`checkcmd` 的 change 循环接入（触发条件 = 本次 diff 触及 `require_change_for`）；
      文案经 `reason` 参数传入（**参数化**，非第二份实现）
- [ ] B9 单测（先红）：**多 change 同 PR 边界**——本 PR 改代码 + 顺带新增纯文档 change
      ⇒ 该文档 change 也被要求 building 证据（**这是刻意的**，Q2 的**推荐**口径「一 PR 一 change」前提；待用户裁定）

## C. 自伤面（D6）—— **grill 实测：0 条新增失败**（原「一批会红」已被证伪）

- [ ] C1 **确认**既有用例无需改动（grill 在 `/tmp` 副本实测 404 passed 逐条相同；不投入盘改）
- [ ] C2 回归：本仓三个 active change（`dogfood-bootstrap` / `grill-evidence-gate` / `guard-crash-exit`）
      的证据仍判**合格**
- [ ] C3 回归：`guard` **不**受影响（仍只查 grill；写码前不要求 building）

## D. 文档（D5）

- [ ] D1 `docs/gate.md §6`：`check` 红项清单加「缺 building 审阅证据」
- [ ] D2 `docs/gate.md §8`：新增 building 门禁小节（触发 + 判据 + 边界）
- [ ] D3 `README.md`：写明**对**接入方**是两条**行为变更（design D5 明列两条，**别只写一条**）：
      ① 「改了代码但没跑 review-loop」的 PR 从**绿变红**；
      ② **多 change 同 PR** 时**每个** change 都要 building 证据（原本可「一个 PR 捎带一个纯文档 change」，现在会红；实测 `exit 0 → exit 1`）
- [ ] D4 `templates/review-loop.md`：依 **Q1** 结果（甲：补一句「只要求证据存在」；乙：规定多轮最终裁定形态）

## E. 证据链与收尾

- [ ] **E0**（顺序约束 · 自锁防线）：停轮拿到 Q1/Q2/Q3 答复 → 写 `## User Confirmation` →
      `manifest build --stage grill` 放行 `src/**` → 内容提交后**必须重跑**覆盖（否则 stale 红）
- [ ] E1 两段提交 + `manifest build`（grill / grill-adversarial / building）+ `check` 绿
- [ ] E2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] E3 PR（branch protection）→ 合入 → 关 issue

## 明确不做（本 change）

grill-adversarial（设计对抗轮）的门禁 · 改 `guard` · verdict 文本判据（若 Q1 选甲）· 签名/防伪造 ·
asterwynd 的项目特有检查（Impact Analysis / RIR / benchmark gate）。
