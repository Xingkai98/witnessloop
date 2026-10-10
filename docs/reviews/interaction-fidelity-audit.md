# 交互层保真度审计（M2 MUST-FIX）

> 独立审计判定：M2 的交互层**抓对了骨架，但把三条循环拍扁成单趟**，保真度约 65%。
> 本文记录逐项回填的内容、判据、以及变异证据。
> 回填后：`templates/{grill,review-loop}.md` 恢复多轮语义，`plugin/commands/*.md`
> 同步接线；host 中立性、物理分离、只读无状态三条约束**未被破坏**。

## 参照真身

| 参照 | 说明 |
|---|---|
| asterwynd `grill` 命令（`.claude/commands/grill.md`） | 7 个 grill 维度、决策记录格式（`## Reviewer` / `## Confirmed Decisions` ≥3 条带 `来源:` / `## 风险`）、「整合回 design.md」、护栏 |
| asterwynd `review-loop` 命令（`.claude/commands/review-loop.md`） | 8 个审阅维度、verdict 三态、批次 aware、审阅基线、修复要同步改文档并提交、轮数封顶 |
| asterwynd `grilling` skill（`~/.claude/skills/grilling/SKILL.md`） | **frontier 多轮循环**：决策树 / 每轮抛整条 frontier + 推荐答案 / 停下等答复 / 重算 frontier / 完成条件 = frontier 为空 / 事实派 subagent 查（含「**不要阻塞**」：探查中的事实是未决前置，只有它下游的问题等它） |

### ⚠️ G3 / G4 的出处不在命令文件里（别据此判为「自创」）

**对抗验证（G3）与 Code-Resolved Questions（G4）的真身在 asterwynd 的
规格与变更设计里，不在 `.claude/commands/grill.md`。** 只拿命令文件当基准会误判
这两条是 witnessloop 自创的——它们是**规格化的既有语义**，出处如下（均已实地核对）：

| 项 | 出处 | 关键原文 |
|---|---|---|
| G3 对抗验证闭环 | `openspec/changes/archive/2026-10-07-grill-flow-hardening/design.md:53` | 「形态（对齐 `/review-loop`）：spawn 独立零记忆审阅 subagent → **对抗分析（默认设计有错、逐条尝试证伪 Confirmed Decisions 与设计假设）** → 出 verdict（`PASS` / `CHANGES_REQUESTED`）→ `CHANGES_REQUESTED` 则修 → **再审，直到 `PASS` 或轮数封顶**」 |
| G3 产物与命名 | 同上 `design.md:49,55` | 产物 `reviews/grill-adversarial.md`；「与 `building-review.md` 平行」；该闭环**与实现后 review-loop 同构** |
| G3 规格化 | `openspec/specs/change-documentation/spec.md:48,53` | 「…SHALL produce a structured record at `openspec/changes/<id>/reviews/grill-adversarial.md`. This loop is **isomorphic to the implementation-phase `/review-loop`**」 |
| G4 Code-Resolved | `.../design.md:54` | 「该闭环内，对每条 Open Question——**能由代码判定的**，由审阅者**带证据（`文件:行号`）直接答出**，**移出停轮队列**（见 D4）；只有真正的用户取舍才留在 `## Open Questions` 交停轮」 |
| G4 规格化 | `openspec/specs/change-documentation/spec.md:59,62` | 「**Code-decidable** Open Questions SHALL be answered with evidence (`file:line`), recorded under a **`## Code-Resolved Questions`** section…and SHALL NOT be carried into `## Open Questions` or the stop-turn queue」 |
| G3 + G4 维护口径 | `AGENTS.md:18` | 「设计阶段审阅闭环（grill-flow-hardening / issue #298）：grill 产出后、**停轮前**，必须再跑一个与…**同构**但**审设计而非代码**的闭环，产出 `…/reviews/grill-adversarial.md`…该闭环内**能由代码判定的 Open Question 用代码给出带证据（`文件:行号`）的答案**、移出 `## Open Questions`（记入 `## Code-Resolved Questions`）、**不停轮**」 |

同一条还解释了 G5（`AGENTS.md:18`：「artifact checker 对完成 change 验证证据存在
且 **≥3 条决策**」）与「每条 Open Question 必须配一个**具体例子/场景**讲解」的出处。
**教训**：审计交互层保真度时，基准面至少要有**命令文件 + 该流程的规格/设计 +
`AGENTS.md` 维护口径**三层——只看命令文件会把规格化的语义当成不存在。

### 有意的不一致（不是缺陷，别「修」回去）

去掉 issue 号、去掉 `.claude/` 路径、改写为 host 中立措辞、把 CLI 调用换成本仓的
`witnessloop manifest build`——这些是 design §5.2「重写，不回收」的要求。
（上表的出处行里保留了 issue 号与原始路径，那是在**记录参照物**，不是模板内容。）

## 审计结论：哪些是真的丢了

| # | 项 | 审计判定 | 严重度 |
|---|---|---|---|
| G1 | frontier 多轮循环被拍扁成「列一遍决策点」的单趟 | 丢失 | 高 |
| G2 | 「必须修改整合回 design.md」整条丢失 | 丢失 | 高 |
| G3 | `grill-adversarial`（对抗验证）整条丢失 | 丢失 | 高 |
| G4 | Code-Resolved Questions（能查代码的自行定案） | 丢失 | 中 |
| G5 | `Confirmed Decisions` ≥3 条 + `来源:` 硬门槛 | 丢失 | 中 |
| G6 | 报告结构缺 `## Reviewer` / `## 风险` | 丢失 | 中 |
| G7 | grill 7 维（含「触发与门禁」）被压成笼统一句 | 丢失 | 中 |
| R1 | verdict 从三态退化成两态（丢 `BLOCKED`） | 丢失 | 高 |
| R2 | 审阅维度（含「任务逐项验证」）被压成笼统一句 | 丢失 | 中 |
| R3 | 批次 aware（「后续批」的 `[ ]` 不算缺陷） | 丢失 | 中 |
| R4 | `CHANGES_REQUESTED` 处置缺「同步更新 change 文档 + 提交修复」 | 丢失 | 低-中 |
| R5 | 审阅基线（merge-base / 落后先 rebase） | 丢失 | 低 |

## 回填对照

### `templates/grill.md`

| 项 | 回填内容 |
|---|---|
| G1 | 新增「多轮 frontier 循环」一步，写明 ①frontier 定义 ②每轮整条抛出（编号 + 推荐答案 + 具体例子/场景）③抛完停下等答复 ④答复后重算 frontier、依赖未决项的归下一轮 ⑤完成条件 = frontier 为空 ⑥事实另起 run 去查、不问用户 |
| G2 | 新增「整合回 design.md」一步：必须修改项落进 Decision、更新 `## Pre-Implementation Review`、阻塞性缺陷停下报告 |
| G3 | 新增「对抗验证」一步：另起独立零记忆审阅者**默认结论有错、逐条证伪**、能实测就实测、verdict → 修 → 到 PASS 或封顶、产物 `grill-adversarial.md` |
| G4 | frontier 段落里写明 Code-Resolved Questions：带 `文件:行号` 证据自行定案、**不进 frontier、不停轮** |
| G5 | 决策记录格式里写明 `## Confirmed Decisions` **至少 3 条**、每条 `来源: <run id>`，并说明下游检查器按此格式解析 |
| G6 | 报告结构补 `## Reviewer`（run id + 时间）与 `## 风险` |
| G7 | 新增「Grill 维度（逐项追问）」7 条，含**触发与门禁**（改门禁的 change 自身会不会死锁误伤） |

### `templates/review-loop.md`

| 项 | 回填内容 |
|---|---|
| R1 | verdict 恢复三态表（`PASS` / `CHANGES_REQUESTED` / **`BLOCKED`**），判定规则写明 BLOCKED = 核心功能缺失 / 安全漏洞 / 测试大面积失败；闭环步骤里 BLOCKED **停下报告、不自行修复** |
| R2 | 新增「审阅维度」8 条，第 1 条就是**任务逐项验证**（每个 `[x]` 读代码确认真实存在，不是看文件名/import/信 `[x]`），另含 Spec 对齐、安全性、CI 完整性等 |
| R3 | 审阅者交代里写明**批次 aware**：标「后续批」的 `[ ]` 不算缺陷，别据此打 CHANGES_REQUESTED |
| R4 | 修复步骤补：**在 `tasks.md` 追加「审阅修复」节**（注明问题与对应修复）+ 跑测试 + **提交修复** |
| R5 | 新增「确定审阅基线」一步：`git merge-base` 取 base、确认审阅提交范围、**落后主干先 rebase 再审** |

### `plugin/commands/*.md`（行为落在适配器上的部分）

适配器仍是「只接线、不内联」：只补**host 侧必须知道的机制**，算法正文仍在模板里。

| 适配器 | 回填内容 |
|---|---|
| `grill` | 写明**本命令跨多轮**：每轮抛完 frontier 就**结束本轮**、不自问自答；用户答复后再调用一次接着走下一轮；`frontier` 为空之前不要开始实现。另点出对抗验证与「整合回 design.md」两步的落点 |
| `review-loop` | 第 3 步补**审阅基线**（merge-base / 落后先 rebase）；第 4 步补「逐项验证 `[x]`」与「后续批不算缺陷」；第 5 步展开**三态**处置（BLOCKED 停下报告、不自行修复；CHANGES_REQUESTED 要补回归测试 + 追加「审阅修复」节 + 提交）；约束段同步 |

## 忠于原身的项（审计确认**没有**丢）

这些在 M2 里已经对，本次不动：

- **独立零记忆**：审阅者必须另起 run、不共享上下文（两个模板都写了）。
- **强制 `reviewer_run_id != author_run_id`**，且 `manifest build` 会拒相等。
- **有界轮数封顶**（默认 3 轮，到顶交人）。
- **修复必须补回归测试**（先红再绿）。
- **报告 + manifest 成对**、`manifest build` 收尾、**先内容提交后证据提交**。
- **只读、无状态**：不得持有自己的状态文件，一切以 manifest 为准。
- **grill 停轮等用户确认**、审阅者不得替用户拍板。
- 报告的 `## User Confirmation` 段。

## 验证：host 中立性 / 物理分离 / 只读无状态

回填是**在模板内部补流程步骤**，三条既有约束都**未被削弱**，测试继续成立：

- `tests/test_templates.py::test_templates_are_host_neutral`：新增内容不含
  host 专有 token，也没有 slash 命令行。
- `tests/test_plugin.py::test_adapter_does_not_inline_the_template`：适配器与同名模板
  的**最长共同段仍是 0 字符**（阈值 60）。回填过程中曾一度到 64 字符，
  已改措辞压回 0。
- `tests/test_plugin.py::test_adapter_declares_readonly_and_stateless` 等继续通过。

**因新增步骤而更新的断言**：无既有断言被删除。`test_grill_template_covers_the_algorithm`
一度因重写而丢掉「每条配具体例子」这条 M2 要求，已把「具体例子或场景」补回
frontier 的每轮格式里（与 G1② 的「推荐答案」并存，互不冲突）。

## 变异证据

对每一项，把模板/适配器里对应的标记串整体去掉 → 对应测试变红 → 还原。
（只删第一次出现不算数：这些词在文件里出现多次，替换全部才测得出。

| 变异（去掉） | 变红 |
|---|---|
| `templates/grill.md` 去掉 `frontier` | `test_grill_runs_a_multi_round_frontier_loop` |
| 去掉 `推荐答案` | `test_grill_puts_every_frontier_question_...` |
| 去掉 `下一轮` | `test_grill_deferrs_questions_that_depend_on_open_ones` |
| 去掉 `Pre-Implementation Review` | `test_grill_integrates_must_fixes_back_into_the_design` |
| 去掉 `grill-adversarial` | `test_grill_runs_an_adversarial_verification_before_stopping` |
| 去掉 `Code-Resolved` | `test_grill_resolves_code_answerable_questions_itself` |
| 去掉 `3 条` | `test_grill_evidence_has_a_hard_format_threshold` |
| 去掉 `## Reviewer` | `test_grill_report_has_reviewer_and_risk_sections` |
| 去掉 `触发与门禁` | `test_grill_covers_the_seven_dimensions` |
| 去掉 `不要阻塞`（事实探查不扣下整条 frontier） | `test_grill_does_not_block_the_frontier_on_a_fact_finding_run` |
| `templates/review-loop.md` 去掉 `BLOCKED` | `test_review_loop_verdict_has_three_states` |
| 去掉 `任务逐项验证` | `test_review_loop_covers_the_review_dimensions` |
| 去掉 `后续批` | `test_review_loop_is_batch_aware` |
| 去掉 `审阅修复` | `test_review_loop_syncs_change_docs_and_commits_the_fix` |
| 去掉 `merge-base` | `test_review_loop_establishes_a_review_baseline` |
| `plugin/commands/grill.md` 去掉 `frontier` | `test_grill_adapter_runs_the_loop_across_turns` |
| `plugin/commands/review-loop.md` 去掉 `BLOCKED` | `test_review_loop_adapter_handles_a_blocked_verdict` |
| 去掉 `后续批` | `test_review_loop_adapter_is_batch_aware_and_syncs_docs` |

全部还原后 `uv run pytest -q` → **285 passed**。
