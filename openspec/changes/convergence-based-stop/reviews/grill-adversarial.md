# 设计对抗验证: convergence-based-stop

## Verdict
**PASS**（第 1 轮 I1–I12 全部已修好；第 2 次开批为空）

## 第 1 轮对抗验证

- 被检 revision: `bad76d8`（审阅开始时工作树 clean；本报告是唯一改动）；基线 `origin/main` `46e45b4`。
- 审阅方式: **零记忆、只读**。除本报告外，未改 change 文档、模板、适配器、测试或生产代码；未 commit。所有结论用 `nl -ba` / `grep -n` / `sed -n` 亲自核对；实际跑全量测试；实际读
  `src/witnessloop/{evidence,checkcmd,contract}.py` 与 `.witnessloop/policy.json`。
  `uv` 不在当前 shell 的 `PATH`，测试用绝对路径 `/home/happy/.local/bin/uv` 执行。
- 轮次状态: 本轮为设计对抗环**第 1 轮的开批**；批次非空，故计为 1 轮。批次在本报告后冻结；作者修复后
  **只做逐条验证**，同一轮不另计；验证期新问题只进 deferred（`design.md:72-84`）。`CHANGES_REQUESTED`
  是轮内状态，不是出口（`design.md:134`、`spec.md:171-173`）。
- 本报告覆盖 2026-10-15 的旧模型 `grill-adversarial.md`；旧内容不保留，仅可于 git 历史 `9acdf2b` /
  `20f1089` 查（`design.md:246-256`、`tasks.md:19-23`）。

### 第 1 轮 · 批次（medium+，必须全修）

| id | severity | 锚点 | 问题摘要 |
|---|---|---|---|
| I1 | 高 | `tasks.md:32-33` | B2 仍写「跑到收敛（无轮数上限）」，与设计环 20 上限直接矛盾 |
| I2 | 高 | `design.md:91-93`、`spec.md:127-129` | 「第 20 轮自身未收口」的规范触发过宽，和同轮重试规则冲突 |
| I3 | 中 | `design.md:75-77`、`spec.md:29-30` | R2 终止点（「再次」+「新的可验证修复方案」）不可复核 |
| I4 | 高 | `design.md:303-304`、`tasks.md:46` | 反断言词表漏掉已知旧措辞（裸「封顶」、「N 轮封顶」） |
| I5 | 中 | `design.md:295-302`、`tasks.md:47-52` | 扫描面与排除名单两种口径并存，不可直接实现 |
| I6 | 中 | `plugin/commands/review-loop.md:22-23`、`templates/review-loop.md:150` | 适配器仍写「步骤 1–6」；两处「三态」未进落点表 |
| I7 | 中 | `design.md:232-239`、`spec.md:231-239` | 机械门禁诚实边界写错：`grill` 阶段实际会解析报告正文 |
| I8 | 中 | `design.md:61,169-170,179`、`spec.md:189-190,193` | 零轮 PASS 与第 20 轮收口确认后的 id/小节编号未定义 |
| I9 | 中 | `design.md:80-81,161-163`、`spec.md:66-68,186` | deferred「延后理由」的范围不一致，且报告表没有该列 |
| I10 | 中 | `design.md:150,169-173`、`spec.md:182-191` | 报告 schema 把「轮内 verdict」与「终结出口」混为一谈 |
| I11 | 中 | `design.md:71,158,223-224`、`spec.md:25,185,210-214` | 设计环没有定义「能变红的回归测试」的对应物，同构不完整 |
| I12 | 中 | `design.md:225-227`、`spec.md:212-214`、`tasks.md:37` | 设计环修复面只写 `design.md` / `grill-design.md`，漏 proposal/spec/tasks |

### 第 1 轮 · 验证

本轮开批时的状态；以下各项已由 `6a8deee` 修复，逐条验证见 `## 第 2 轮 · 验证`。验证时只核对这批
「是否修好」，不扫描/不追加新问题（新问题进 deferred）。

| id | 结果 | 修复提交 | 回归测试 |
|---|---|---|---|
| I1 | 待验证 | — | 待定 |
| I2 | 待验证 | — | 待定 |
| I3 | 待验证 | — | 待定 |
| I4 | 待验证 | — | 待定 |
| I5 | 待验证 | — | 待定 |
| I6 | 待验证 | — | 待定 |
| I7 | 待验证 | — | 待定 |
| I8 | 待验证 | — | 待定 |
| I9 | 待验证 | — | 待定 |
| I10 | 待验证 | — | 待定 |
| I11 | 待验证 | — | 待定 |
| I12 | 待验证 | — | 待定 |

### 第 1 轮 · 下一批（deferred）

（无。本轮尚未进入验证；按新模型，验证期发现的新问题才进本表，且不得扩当前批次。）

### low / nit 登记

| id | severity | 处置 | 理由 |
|---|---|---|---|
| L1 | low | 登记不修（建议随 I2 修） | `proposal.md:91` 的「只补超上限这一成因」与 R2/R3 新增成因不一致；不改不影响 spec 的可执行性 |
| L2 | low | 登记不修（建议顺手修） | `docs/gate.md:715-716` 的「PASS / CHANGES_REQUESTED 都合格」是机械口径；落点表只列 `:716`，读者仍可能把 `CHANGES_REQUESTED` 当出口 |
| L3 | low | 登记不修 | 「逐项链接到首次登记的轮次小节」没有规定 `文件#锚点` 格式；靠 id `R<n>-<k>` 仍可人工追，但第三方复核成本偏高 |
| L4 | low | 登记不修 | 变异验证写死「1 failed」偏脆；同一变异可能触发多条正向/反向断言。应改为「新守卫至少 1 failed」并指定目标测试 |
| L5 | low | 登记不修 | R5 已写「`BLOCKED` + 成因 + 用户明确裁决继续」，但没有规定用户裁决记录在哪（建议 `grill-design.md` 的 `## User Confirmation`） |
| L6 | low | 登记不修 | `spec.md:248-251` 的「只改模板/适配器/自述/测试，不碰 src/」易被读成「无 code_hits」；实际 `templates/**`、`plugin/**` 在 `require_change_for` 内（`.witnessloop/policy.json:8-12`），改动前后都会要求同一批 stage manifest |
| L7 | low | 登记不修 | 「已结束的轮」与「已收口的轮」未严格区分（`design.md:91`、`spec.md:123`）；定义「轮 = 完整闭环」已隐含收口，但建议把计数口径写成「已收口」以免把 BLOCKED 终结误算进 20 |

> 作者在 `6a8deee` 中顺手修了 L1–L7（见 `design.md:444-466` 的 Pre-Implementation Review 与第 2 轮验证）；本表保留第 1 轮开批时的登记状态。

### 第 1 轮后 · 收口确认

> 第 1 轮开批时的状态；第 2 轮验证后本轮已收口，下一次开批为空 ⇒ `PASS`（见下）。

**不适用：本轮未收口。** 按 I10，报告 schema 必须允许轮内报告；本报告不伪造一个空的「收口确认」。
`CHANGES_REQUESTED` 只是轮内状态，不是出口（`design.md:134`、`spec.md:171-173`）。

### 第 1 轮 · 出口（历史）

**未定（第 1 轮开批时的轮内状态）。** 作者修复并全部验证通过后，本轮才收口；第 2 轮验证后已收口并
`PASS`（见下）。

---

## 第 2 轮 · 验证（第 1 轮批次 I1–I12 的修复验证；按新模型仍是第 1 轮，不是新开批）

- **验证对象**: `bad76d8` → `6a8deee` 的修复差异；工作树 `HEAD 6a8deee`，审阅开始时
  `git status --porcelain` 为空。
- **修复提交**: `6a8deee`（作者整合 I1–I12 的单一提交）。
  `git diff --stat bad76d8..HEAD -- openspec/changes/convergence-based-stop/` 显示
  design / proposal / tasks / spec 与报告变更；`reviews/grill-design.md` 自 `bad76d8` 起未改
  （`git diff --stat` 为空）。
- **验证方式**: **只核对 I1–I12 是否修好**；不扫描新问题、不扩批。逐条用 `nl -ba` / `grep -n`
  核对当前文本；用 `git diff bad76d8..HEAD -- openspec/changes/convergence-based-stop/` 看差异；
  重跑全量测试。
- **范围注意**: C/D 批次（模板/适配器/测试实现）尚未执行；I4/I5/I6 按其**计划/测试策略**验收——
  只看 design/proposal/tasks 是否写死，不要求 `tests/test_convergence_stop.py`、
  `plugin/commands/review-loop.md` 等已经改好。

### I1–I12 逐条结果

| id | 结果 | 当前证据（HEAD `6a8deee`） | 修复提交 |
|---|---|---|---|
| I1 | **已修好** | `tasks.md:32-36` B2 已改为批次模型 + 20 上限 + 第 20 轮超上限 `BLOCKED` + `CHANGES_REQUESTED` 轮内；`tasks.md:107-110` V5c | `6a8deee` |
| I2 | **已修好** | `design.md:78-84` 终止点定义；`design.md:101-106` 第 20 轮自身终止点 + 收口确认前状态；`design.md:146` 出口表；`spec.md:35-41,140-144,158-167,169-173`（含「第一次未修好但有新方案 ⇒ 同轮继续」Scenario） | `6a8deee` |
| I3 | **已修好** | `design.md:78-84` 定义「再次（第二次及以后）」与「新的、可验证的修复方案」；`design.md:227-228` D2；`spec.md:35-41` | `6a8deee` |
| I4 | **已修好** | `design.md:349-354` 补 `N 轮封顶` / `或封顶` / `**封顶**` + 裸 `封顶` 行级规则与 5 行已知漏网点；`tasks.md:51-53`；`proposal.md:149` | `6a8deee` |
| I5 | **已修好** | `design.md:341-344` 明确「显式 allowlist，不做全仓减排除」；`design.md:355-359` 七要素→文件映射；`tasks.md:54-61` | `6a8deee` |
| I6 | **已修好** | `design.md:310-311` 限定 `templates/review-loop.md:150`；`design.md:331-333` 适配器 `:22` 改 1–8、`:23`/`:63` 限定；`proposal.md:113-115`；`tasks.md:60` 适配器守卫（实际文件属 C 批） | `6a8deee` |
| I7 | **已修好** | `design.md:264-279` D6 改为「不新增正文解析」并列出 `stage=grill` 既有正文判据；`design.md:378-380`；`spec.md:274-290`；`proposal.md:80-88,141-142`；`tasks.md:4` | `6a8deee` |
| I8 | **已修好** | `design.md:62` 初次开批记作收口确认；`design.md:107-110` 初次开批 `R0-*`、第 20 轮后 `C-*`；`design.md:197-202`；`spec.md:17-18,145-148,180-183,227-228` | `6a8deee` |
| I9 | **已修好** | `design.md:85-89` 所有 deferred medium+ 写延后理由、安全项额外写；`design.md:181` 表加「延后理由」；`design.md:222-224`；`spec.md:78-80,217` | `6a8deee` |
| I10 | **已修好** | `design.md:149-150` 轮内 verdict / 闭环出口分开；`design.md:168-194` 报告模板含两者与 BLOCKED 不伪造收口确认；`spec.md:211-225,203-207` | `6a8deee` |
| I11 | **已修好** | `design.md:203-204` 设计环对应物三选一；`design.md:258-259` D5；`spec.md:30-32,251-253,268-272` | `6a8deee` |
| I12 | **已修好** | `design.md:254-257` 修复面含 design/proposal/spec/tasks/grill-design；`spec.md:247-250`；`tasks.md:39-41` B4 | `6a8deee` |

**L1–L7 抽查**：作者在 `6a8deee` 中顺手修了 `proposal.md:94-95`（`BLOCKED` 新成因）、
`design.md:336-337`（`docs/gate.md:715-716` 机械接受≠出口）、`design.md:184`（累积登记链接格式）、
`design.md:363-364`（变异「至少 1 failed」）、`design.md:322-323`（用户裁决记录位）、
`design.md:386-388` + `spec.md:304-306`（`code_hits`）、`design.md:63,99`（已收口）。
与第 1 轮登记一致；均为 low，不阻塞。

### 验证用的命令 / 证据

```text
$ git status --porcelain=v1
$ git rev-parse HEAD
6a8deeeb02827c4660d397ec40dee9cc9b49dc2d
$ git rev-parse origin/main
46e45b446ca92ea84838490e535a41c529994526

$ git diff --stat bad76d8..HEAD -- openspec/changes/convergence-based-stop/
 design.md                            | 229 +++++++++----
 proposal.md                          |  33 ++-
 reviews/grill-adversarial.md         | 1464 ++++++++------------
 specs/review-termination/spec.md     | 127 +++++---
 tasks.md                             |  48 ++-
 5 files changed, 848 insertions(+), 1053 deletions(-)

$ git diff --stat bad76d8..HEAD -- openspec/changes/convergence-based-stop/reviews/grill-design.md
（空：grill 决策记录未改）

$ nl -ba openspec/changes/convergence-based-stop/design.md | sed -n '62p;78,89p;99,114p;146,150p;168,204p;227,228p;254,259p;264,279p;310,311p;331,333p;341,354p;355,359p;378,380p'
$ nl -ba openspec/changes/convergence-based-stop/specs/review-termination/spec.md | sed -n '17,18p;35,41p;78,80p;140,148p;158,173p;180,183p;203,228p;247,253p;268,272p;274,290p;304,306p'
$ nl -ba openspec/changes/convergence-based-stop/tasks.md | sed -n '32,42p;50,61p;68p;107,110p'
$ nl -ba openspec/changes/convergence-based-stop/proposal.md | sed -n '80,88p;94,95p;113,115p;141,142p;148,149p'
$ grep -n '无轮数上限\|已结束的轮\|非空则成为下一轮\|同一项再次\|超过 20 轮' openspec/changes/convergence-based-stop/{design.md,proposal.md,tasks.md,specs/review-termination/spec.md}
$ grep -n '封顶' openspec/changes/convergence-based-stop/specs/review-termination/spec.md
（无输出：spec 不在词表命中面）
```

全量测试（设计阶段，HEAD `6a8deee`）：

```text
$ /home/happy/.local/bin/uv run pytest -q
........................................................................ [ 69%]
........................................................................ [ 79%]
........................................................................ [ 89%]
........................................................................ [ 99%]
...                                                                      [100%]
723 passed in 72.62s (0:01:12)
```

`grill-design.md` 正文完备性（未改，复用第 1 轮证据）：

```text
$ PYTHONPATH=src .venv/bin/python -c "from pathlib import Path; from witnessloop.evidence import grill_evidence_findings; p=Path('openspec/changes/convergence-based-stop/reviews/grill-design.md'); print(grill_evidence_findings(p.read_text(encoding='utf-8'), report_path=str(p)))"
[]
```

## 第 2 轮 · 批次

**空批：0 条 medium+。** 对当前 `design.md` / `proposal.md` / `tasks.md` / `spec.md` 做完整审阅后，
未发现新的 medium+；只发现下列 low/nit。按新模型，下一次开批为空 ⇒ **`PASS`**，不消耗轮数；
这是第 1 轮后的收口确认。

## 第 2 轮 · 下一批（deferred）

（无。下一次开批未发现 medium+；新增 deferred = 0。）

## 第 2 轮 · 新增 low / nit 登记（不阻塞 PASS）

| id | severity | 锚点 | 处置 | 理由 |
|---|---|---|---|---|
| N1 | low | `design.md:62` | 登记不修 | 「收口确认」定义仍写「非空则成为下一轮」，未写第 20 轮例外；`design.md:111-114` 的专门规则已明确非空 ⇒ 超上限 `BLOCKED`，不改变执行 |
| N2 | low | `design.md:153-154` | 登记不修 | §2.5 的 R2 摘要仍写「同一项再次被判未修好」，未含「第一次失败 + 明确无新方案也触发」；`design.md:78-84` 与 `spec.md:35-41` 的规范句完整 |
| N3 | low | `design.md:193` | 登记不修 | 报告模板的出口标签写「超过 20 轮」，第 20 轮自身未收口不是「超过」；`design.md:146` 的触发表已正确区分 |
| N4 | low | `proposal.md:148` | 登记不修 | 「见验收的 11 个文件」是交叉引用，但验收段（`proposal.md:123-142`）没有枚举这 11 个；`design.md:345-348` 与 `tasks.md:54-57` 已枚举 |
| N5 | low | `spec.md:220` | 登记不修 | 报告 Requirement 的收口确认标题只写 `### 第 <n> 轮后 · 收口确认`；初次开批的 `### 初次开批 · 收口确认` 在 `spec.md:145-148` 与 `:180-183`，建议在 Requirement 5 也点名 |
| N6 | low | `design.md:445` | 登记不修 | Pre-Implementation Review 记了 run `grill-adversarial-reviewer-convergence-2026-10-17`，但 `grill-adversarial.md` 本身没有该 run id；manifest 应携带真实 `reviewer_run_id`，报告可补一节 |
| N7 | low | `proposal.md:3-5`、`proposal.md:132-134` | 登记不修 | proposal 的状态行/验收仍只提 R1–R13 与原始旧词表；I1–I12 与扩展词表已在 design/tasks 写死，proposal 是摘要 |
| N8 | low | `tasks.md:68` | 登记不修 | C5 写「步骤 5–7」，没有显式点名 `:22` 的 1–8 与 `:23` 的三态限定；`design.md:331-333`、`proposal.md:113-115` 与 C1 守卫已覆盖 |
| N9 | low | `spec.md:243-256` | 登记不修 | Requirement 6 未包含 R5 的「`BLOCKED` 不授予写码许可」；`design.md:321-323`、`proposal.md:109`、`tasks.md:57` 已写，属模板/流程条件 |
| N10 | low | `tasks.md:39-42` | 登记不修 | B4/B5 仍是 `[ ]`；本次 PASS 后可由作者勾选（B5 就是本轮验证），属流程记账，不是设计缺陷 |

## 第 2 轮 · 尝试证伪但未成立的方向（3 个）

1. **第 20 轮时序仍会被第一次失败提前终结？** 未成立：`design.md:101-106` 只把「达到 §2.2 第 3 步
   验证重试终止点」作为触发；`spec.md:164-167` 明确「第一次 `未修好` 但开发者提交新 commit +
   先红后绿测试 ⇒ 同轮继续」。I2 的时序漏洞已收窄。
2. **反断言仍漏已知旧措辞？** 未成立：`design.md:349-354` 的裸 `封顶` 行级规则覆盖
   `templates/grill.md:21`、`templates/review-loop.md:101`、`docs/design.md:25`、两条测试；并显式
   放行 `docs/gate.md:407/554` 与 `docs/design.md:85`。allowlist 只扫 11 个文件，不做全仓减排除
   （`design.md:341-344`）。I4/I5 的计划层面已闭合。
3. **机械门禁诚实边界仍在过度承诺？** 未成立：`design.md:264-279`、`spec.md:274-290`、
   `proposal.md:80-88` 统一为「不新增正文解析」，并列出 `stage=grill` 既有正文判据
   （`evidence.py:259-330`）与 `building`/`grill-adversarial` 只判存在（`evidence.py:373-380`）。
   代码证据与文本一致。

## 出口

**PASS**。第 1 轮 I1–I12 全部已修好；第 2 次开批为空（0 条 medium+），low/nit 不阻塞。

---

## 逐条 issue

### I1｜高｜B2 仍写「跑到收敛（无轮数上限）」

- **锚点**: `tasks.md:32-33`；对照 `design.md:221-230`（D5：两个环共用同一模型，含 20 上限）
  与 `spec.md:208-217`（Requirement 6：设计对抗环 SHALL 使用同一套轮次模型）。
- **问题**: `tasks.md:32-33` 原文为「`CHANGES_REQUESTED` ⇒ 修并再审，**跑到收敛（无轮数上限）**」。
  这仍是旧模型的「无限轮」口径；新模型明确设计对抗环与实现环共用 20 上限、deferred 与三出口。
- **为什么是问题**: 这是本 change 自己的执行清单。作者若照 B2 执行，设计对抗环可以无限跑，直接否定
  用户 2026-10-17 拍板的第 2 个参数，也让 `tasks.md:94-96` 的 V5b「两环 `BLOCKED` 映射」失去约束。
  `CHANGES_REQUESTED ⇒ 修并再审` 也仍是「再审 = 新一轮」的旧语义；新模型是「修 + 同轮逐条验证」。
- **具体收法**: 把 B2 改成：「按批次模型：开批只列 medium+；全修；同一轮逐条验证；验证期新问题
  deferred；第 20 轮自身达到验证重试终止点，或第 20 轮收口确认仍有 medium+ ⇒ **超上限 `BLOCKED` +
  建议推倒重开（revise the design）**；`CHANGES_REQUESTED` 是轮内状态，不是出口」。同时在 V5b 或 V1
  加一条反断言：`tasks.md` 不再出现「无轮数上限」「无限轮」。

### I2｜高｜「第 20 轮自身未收口」的规范触发过宽，且与同轮重试规则冲突

- **锚点**: `design.md:91-93`、`design.md:61`、`design.md:127-131`、`design.md:173`、
  `design.md:207-208`；`spec.md:127-129`、`spec.md:139-143`、`spec.md:165-169`。
- **问题**: 规范写的是「**若 `B_20` 仍有任何一项为 `未修好`**，出口 SHALL 是超上限 `BLOCKED`」。
  按字面，第 20 轮第一次验证发现某项 `未修好` 就立即触发超上限 `BLOCKED`——即使开发者拿得出新的
  可验证修复方案、且模型明确允许「没修好 ⇒ 继续修，仍是第 `n` 轮」（`design.md:74`、`spec.md:28`）。
  `spec.md:139-143` 的 Scenario 把它收窄成「验证多次仍为 `未修好`，开发者拿不出新的可验证修复方案」，
  但 Requirement 的规范句没有收窄。
- **为什么是问题**: 这是典型的时序漏洞。第 20 轮的正常状态就是「某项先判 `未修好` → 继续修 → 再验证」；
  若第一次失败就终结，20 轮上限会提前杀死本来还能收口的 change。反过来，若作者按 Requirement 1.6
  走通用 `BLOCKED`，又会丢失「建议推倒重开」这一超上限语义（`design.md:93` 明确说「不是通用
  `BLOCKED`」）。此外，`design.md:61` 对「收口确认」的定义是「非空则成为下一轮」，没有写第 20 轮后
  非空 ⇒ 超上限 `BLOCKED` 的例外；`design.md:131` 的三种出口表、`proposal.md:56` 的出口表、
  `design.md:173` 的出口标签都只写「20 轮已结束 / 超过 20 轮」，漏了「第 20 轮自身未收口」这一支。
- **具体收法**: 把规范触发改成可操作的状态机：
  「第 20 轮若达到 Requirement 1.6 的验证重试终止点（同一项再次判 `未修好` 且开发者拿不出新的、
  可验证的修复方案），或第 20 轮收口后的收口确认仍有 medium+ ⇒ **超上限 `BLOCKED`**」。在
  Requirement 1.6 后加一句交叉规则：「若上述终止点发生在第 20 轮，出口是超上限 `BLOCKED`，不是通用
  `BLOCKED`」。同步补 `design.md:61` 的例外、`design.md:131` / `proposal.md:56` / `design.md:173` 的
  表格行；并显式写出「第 20 轮收口后、收口确认前」的状态：**等待收口确认，不开启第 21 轮，不做修复**。

### I3｜中｜R2 终止点（「再次」+「新的可验证修复方案」）不可复核

- **锚点**: `design.md:75-77`、`design.md:136-137`；`spec.md:29-30`、`spec.md:168`。
- **问题**: 触发条件写作「同一项在本轮内被**再次**判 `未修好`，且开发者拿不出**新的、可验证的
  修复方案**」。两个关键点都没有定义：
  1. 「再次」是否要求至少两次验证失败？第一次失败后开发者就说「没有新方案」时，是否触发？
  2. 什么算「新的、可验证的修复方案」？没有 commit、没有回归测试、只是口头说「我会改」算不算？
- **为什么是问题**: R2 的目的正是把「同一批反复无法收口」从主观判断变成可复核的 `SHALL`。当前措辞
  仍给审阅者留下「永远可以认为还有新方案」的口子；20 轮上限约束的是轮数，不约束同一轮内的验证次数，
  所以这个口子会直接绕过用户要的「有界工作量」。报告虽然要求记录「验证次数与未通过项」
  （`design.md:76-77`），但没有规定「新方案」的可验证形态，第三方仍无法判定终止是否合规。
- **具体收法**: 定义两个词：
  - 「再次」：同一项在本轮内**第二次及以后**被判 `未修好`；若第一次判 `未修好` 时开发者就明确拿不出
    新方案，也立即触发（即「再次」不是必要条件，只是最常见路径）。
  - 「新的、可验证的修复方案」：实现环 = 新 commit + 一条在修复前红、修复后绿的回归测试（或可复现
    失败的命令）；设计环 = 具体的文本修改 + 可复现的反例 / 文档守卫（见 I11）。
  在报告中记录验证次数、每次的修复提交和测试；若开发者拒绝提供可验证方案，审阅者 SHALL `BLOCKED`。
  同步更新 `spec.md:29-30` 与 `design.md:136-137`。

### I4｜高｜反断言词表漏掉已知旧措辞

- **锚点**: `design.md:303-304`、`tasks.md:46`、`proposal.md:125-127`；未覆盖的现存旧措辞：
  `templates/grill.md:21`、`templates/review-loop.md:101`、`docs/design.md:25`、
  `tests/test_templates.py:258`、`tests/test_plugin.py:176`。
- **问题**: 反断言只列了 `3 轮封顶` / `三轮封顶` / `有界轮数` / `轮数封顶`。实际已知旧行中：
  - `templates/grill.md:21` = 「直到 PASS 或**封顶**」——裸「封顶」，不含「轮」；
  - `templates/review-loop.md:101` = 「**封顶**：到第 3 轮仍 `CHANGES_REQUESTED`」——裸「封顶」；
  - `docs/design.md:25` = 「PASS 或 **N 轮封顶**」——是「N 轮封顶」，不是 `3 轮封顶` / `轮数封顶`；
  - `tests/test_templates.py:258` / `tests/test_plugin.py:176` 都含裸「封顶」字面量。
  这 5 行都在显式扫描面内（`design.md:296-299`），但都不匹配那 4 个词条。
- **为什么是问题**: 反断言的全部价值是「作者漏改某行时测试变红」。现在作者即使漏改
  `templates/grill.md:21` 或 `docs/design.md:25`，守卫仍然全绿；change 会带着「直到 PASS 或封顶」
  和「N 轮封顶」两套旧规则合入。R7 的扫描面写得再全，词表不完整也无法兜住已知漏网点。
- **具体收法**: 二选一或并用：
  - 增加裸 `封顶` 的禁止规则，并显式允许 `docs/gate.md:407`（「常量封顶」）与 `docs/gate.md:554`
    （「路径深度封顶」）这两条与本规则无关的行；
  - 或逐条加正则：`N 轮封顶`、`或封顶`、`\*\*封顶\*\*`、以及两条测试里的裸 `封顶` 字面量。
  把 `templates/grill.md:21` 或 `docs/design.md:25` 加入变异验证的目标行；同步更新 design §4.4、
  tasks C1、proposal 验收与 V4。变异验证的期望改为「新守卫至少 1 failed」（见 L4）。

### I5｜中｜扫描面与排除名单两种口径并存，不可直接实现

- **锚点**: `design.md:295-302`、`tasks.md:47-52`、`proposal.md:128-129`、`proposal.md:140-141`。
- **问题**: 设计同时写了：
  1. **规范面清单（显式列出）** 11 个文件；
  2. **排除名单**：`docs/tasks.md`、`docs/reviews/**`、`openspec/changes/archive/**`、
     `openspec/changes/<其它 change>/**`、`tests/test_grill_adversarial_gate.py:180`。
  如果测试只扫这 11 个文件，排除名单是多余的；如果测试扫「全仓减去排除名单」，排除名单又不够：
  - 本 change 自己的 `design.md:22-36`、`proposal.md:16-22`、`tasks.md:46` 以及 `reviews/grill-design.md`
    都含旧措辞引文；本报告也会引用旧措辞。它们不在排除名单里。
  - `openspec/changes/<其它 change>/**` 不是可执行 glob（尖括号不是通配符），实现者只能猜。
  - `tests/test_grill_adversarial_gate.py:180` 是**行级**排除，但没规定实现方式（整文件排除？
    按行号排除？按内容排除？）。整文件排除会掩盖该文件其它行；按行号排除则一改行号就失效。
  - `design.md:303` 的「模板/适配器/自述含新模型七要素」没有说明**哪个文件必须含哪几个要素**；
    若按「每个文件都必须含全部七要素」实现，`docs/design.md:25` 这种一行摘要必然失败。
- **为什么是问题**: 两种口径会导致两种相反的坏结果：allowlist 实现漏掉新文件；whole-repo 实现
  被本 change 自己的旧措辞引文误伤。测试作者只能自行选一种，评审者无法判断选得对不对。
- **具体收法**: 明确选「显式 allowlist 扫描」：只扫 `design.md:296-299` 的 11 个文件，把「排除名单」
  改写为「这些路径不在扫描面内」的说明，删掉不可执行的 `<其它 change>` glob；若坚持 whole-repo，
  则把本 change 的 `design.md` / `proposal.md` / `tasks.md` / `reviews/**` 加入排除，并定义
  fixture 的行级排除机制。另加一张「七要素 → 必须出现的文件」映射表，避免对一行摘要做过度断言。

### I6｜中｜适配器仍写「步骤 1–6」；两处「三态」未进落点表

- **锚点**: `plugin/commands/review-loop.md:22`（「按 `templates/review-loop.md` 的步骤 **1–6** 执行」）、
  `plugin/commands/review-loop.md:23`（「verdict 是**三态**」）、
  `templates/review-loop.md:150`（「**verdict 三态**」）；对照 `design.md:263-267`（新模板 8 步）、
  `design.md:286-287`、`proposal.md:105-108`（落点表只列 `:2` / `:29` / `:63`）。
- **问题**: 新模板的执行步骤是 1–8（开批 / 全修 / 验证 / 收口 / 上限与三出口 / manifest），但适配器
  仍叫审阅者执行「步骤 1–6」。这会让审阅者在适配器层直接跳过第 7 步（20 上限与三出口）和第 8 步
  （manifest），新模型的核心行为在最常用的插件入口处丢失。同时，`plugin/commands/review-loop.md:23`
  和 `templates/review-loop.md:150` 仍写「verdict 三态」；新模型下三态值可以保留，但
  `CHANGES_REQUESTED` 的语义已从「出口」降为「轮内状态」，这两处必须限定，否则读者仍会按旧语义
  把三态当三种出口。落点表只列了 `templates/review-loop.md:75-81` 和
  `plugin/commands/review-loop.md:63`，没有列这两处。
- **为什么是问题**: `plugin/commands/review-loop.md` 是用户实际调用的命令入口；它说 1–6，审阅者就
  不会执行 7–8。即使模板改得再完整，入口层也会把新模型截断。两处未限定的「三态」则保留旧语义，
  使 `CHANGES_REQUESTED` 仍可能被当成停轮理由（DR2 正是要防这个）。
- **具体收法**: 把 `:22` 改为「步骤 1–8」或「按模板全文」；更新适配器的步骤编号与 `:23` / `:63`、
  模板 `:150` 的措辞：「三态值仍在，但只有 `PASS` / `BLOCKED` / 超上限 `BLOCKED` 是出口；
  `CHANGES_REQUESTED` 是轮内状态」。把 `templates/review-loop.md:150` 与
  `plugin/commands/review-loop.md:22-23` 加入 proposal 落点表和 design §4.3；加一条测试守卫：
  适配器不得再出现「步骤 1–6」且必须出现「1–8」（或等价表述）。

### I7｜中｜机械门禁诚实边界写错：`grill` 阶段实际会解析报告正文

- **锚点**: `design.md:232-239`、`design.md:319`、`spec.md:231-239`、`proposal.md:79-80`、
  `proposal.md:84-85`、`proposal.md:134`；代码：`src/witnessloop/evidence.py:259-330`、
  `src/witnessloop/evidence.py:334-380`、`src/witnessloop/checkcmd.py:181-187`。
- **问题**: 设计/规格/提案反复写「`check` 仍只判 manifest + 报告存在、不解析报告正文」。实际
  `check` **无条件**调用 `grill_evidence_findings_in_change`（`checkcmd.py:181-187`），后者对
  `stage=grill` 解析 `## Confirmed Decisions`（≥3 条且每条有 `来源:`）、`## Open Questions`、
  `## User Confirmation`（`evidence.py:259-330`、`:334-380`）。只有 `building` /
  `grill-adversarial` 是 `verify_body=False` 的「存在即可」（`evidence.py:346-347`、`:373-380`）。
  `design.md:375-377` 的 Code-Resolved 自己也承认「`check` 的正文判据只在 `evidence.py:259-330`」，
  与 D6 / §6 的「不解析报告正文」直接冲突。
- **为什么是问题**: 本 change 的核心卖点之一是「诚实边界：`check` 绿 ≠ 模型被执行」。现在的写法
  把 `grill` 的既有正文判据也抹掉了：读者会以为 `check` 对 grill 报告只查文件存在，而实际上它
  还会拒绝缺少 `## Open Questions` / `User Confirmation` 的报告。这不是「过度承诺」，而是**事实
  描述错误**，会让新模型的能力边界失去可信度。
- **具体收法**: 把 D6 / Requirement 7 / proposal 非目标改成「**本 change 不新增**正文解析」而不是
  「`check` 不解析正文」，并列出实际判据：
  - change 契约件存在；
  - review manifest / 报告 / revision / hash / `reviewer_run_id != author_run_id`；
  - 孤儿报告；
  - `stage=grill` 的决策记录正文完备性（既有判据，不变）；
  - `stage=grill-adversarial` / `building` 存在即可。
  再明确「不解析 verdict / 批次 / severity / 轮数 / deferred / low-nit 理由」。`spec.md:248-251`
  的 scenario 也应说明：`templates/**`、`plugin/**` 在 `require_change_for` 内
  （`.witnessloop/policy.json:8-12`），所以改动前后都会要求同一批 stage manifest；该 scenario 说的是
  「不新增 finding 类别」，不是「没有 code_hits」。

### I8｜中｜零轮 PASS 与收口确认后的 id / 小节编号未定义

- **锚点**: `design.md:61`、`design.md:68`、`design.md:169-170`、`design.md:179`；
  `spec.md:17`、`spec.md:32`、`spec.md:156-159`、`spec.md:189-190`、`spec.md:193`。
- **问题**: 新模型允许**第一次开批就为空** ⇒ `PASS`（`design.md:68`、`spec.md:32`），此时没有任何
  非空批次，也就没有「第 `n` 轮」。但报告 schema 要求 `### 第 <n> 轮后 · 收口确认`，
  `id` 规则又要求 `R<首次出现轮次>-<序号>`；首开就发现的 low/nit 没有轮次可填。类似地，第 20 轮收口后的
  收口确认若发现新的 medium+ / low-nit，也没有第 21 轮可用（`SHALL NOT` 开启第 21 轮），
  `R21-*` 会与规则矛盾。
- **为什么是问题**: 一个干净 change 完全可能首开即 `PASS`；它的报告无法同时满足「必须写收口确认」和
  「收口确认 = 第 n 轮后」两条要求。第 20 轮后的收口确认正是用户特别点名的时序状态；它发现的
  medium+ 必须进入超上限 `BLOCKED` 的「未收口列表」，但没有合法的 id / 小节编号，第三方无法稳定引用。
- **具体收法**: 增加 Scenario：
  1.「初次开批为空 ⇒ `PASS`；记录 `### 初次开批 · 收口确认`（或 `第 0 轮后 · 收口确认`），
     low/nit 用 `R0-<seq>`」；
  2.「第 20 轮收口后的收口确认发现 medium+ ⇒ 超上限 `BLOCKED`，用 `C-<seq>`（或 `R20-C<seq>`）
     标识；发现 low/nit ⇒ `PASS`，同样用 `C-<seq>`」。
  同步更新 `design.md:169-170,179` 与 `spec.md:189-190,193`。把「收口确认」的定义从「一轮结束后的
  下一次开批」扩展为「一轮结束后的下一次开批；首次开批用第 0 轮/初次开批标识」。

### I9｜中｜deferred「延后理由」范围不一致，且报告表没有该列

- **锚点**: `design.md:80-81`、`design.md:161-163`；`spec.md:66-68`、`spec.md:186`。
- **问题**: `design.md:81` 要求「否则仍进 deferred，并在 deferred 行写明『为什么可以延后一轮』」——
  按上下文，这适用于**所有** deferred 项。`spec.md:67-68` 则只要求「**其余安全漏洞**」写明延后理由。
  同时，两处报告表的 deferred 列都只有 `id / severity / 锚点 / 问题 / 来源`
  （`design.md:161-163`、`spec.md:186`），没有「延后理由」列，导致「写在 deferred 行」无字段可落。
- **为什么是问题**: R3 的安全例外依赖审阅者写清「为什么这个安全漏洞可以晚一轮修」；缺字段时，
  第三方无法区分「写了理由」和「漏了理由」，也无法复核 R3 是否被滥用。设计说所有项都要写、spec 说
  只有安全项要写，实现者不知道该按哪条验收。
- **具体收法**: 在 `design.md:161-163` 与 `spec.md:186` 的 deferred 表加一列「延后理由」；统一范围：
  建议**所有** deferred medium+ 都要写「为什么可以延后一轮」（安全项额外写「为什么晚一轮仍安全」）。
  同步更新 `spec.md:66-68` 与 `design.md:80-81`。

### I10｜中｜报告 schema 把「轮内 verdict」与「终结出口」混为一谈

- **锚点**: `design.md:150`、`design.md:169-173`、`spec.md:182-191`（尤其 `:189-191`）、
  `spec.md:174-178`；BLOCKED 报告要求见 `design.md:130`、`spec.md:168`。
- **问题**: Requirement 5 说「每一轮的审阅报告 SHALL 至少包含……5. 收口确认；6. 出口：
  `PASS` 或 `BLOCKED`（成因）或超上限 `BLOCKED`」。但同一份 spec 的 Scenario 又允许报告写
  `CHANGES_REQUESTED` 作为轮内状态，并说「出口仍是『未结束』」——「未结束」不是三种出口之一
  （`spec.md:174-178`）。另外，BLOCKED / 超上限 `BLOCKED` 终结时本轮不会收口，根本不存在
  「下一次开批」，但 Requirement 5 仍要求每份报告带收口确认。设计 §2.7 的 `## 出口` 模板也只有
  三个终结值（`design.md:172-173`），没有轮内选项。
- **为什么是问题**: 报告 schema 无法表达本报告这种「开批后、修复前」的轮内报告，也无法表达
  R2 / 安全例外 / 第 20 轮自身未收口的 BLOCKED 报告。审阅者要么伪造一个空的收口确认，要么写出
  一个不在三种出口里的「出口」，两者都违反同一份 spec。用户要求「出口只有三种」，但轮内状态不是出口；
  当前文本把两者混在一个字段里。
- **具体收法**: 拆成两个字段：
  - **本轮判定 / verdict**：`PASS` / `CHANGES_REQUESTED` / `BLOCKED`（轮内可见）；
  - **闭环出口**：只有 `PASS` / `BLOCKED` / 超上限 `BLOCKED`，且仅在终结时填写；轮内写「未定」。
  收口确认改为「`PASS` 必须引用；发生过下一次开批的报告必须记录；BLOCKED / 超上限 `BLOCKED`
  改记 `终止状态 / 验证账本 / 未通过项`」。同步更新 `design.md:150,169-173` 与
  `spec.md:182-191`，并加两个 Scenario：「轮内 `CHANGES_REQUESTED` 报告」与「BLOCKED 报告无收口确认」。

### I11｜中｜设计环没有定义「能变红的回归测试」的对应物，同构不完整

- **锚点**: `design.md:71`、`design.md:158`、`design.md:223-224`；`spec.md:25`、`spec.md:185`、
  `spec.md:210-214`。
- **问题**: Requirement 1.3 要求批次每一项都附「一条**能变红的回归测试**（先红后绿）」；Requirement 6
  又说设计对抗环与实现环共用同一模型；报告验证表也有「回归测试」列（`spec.md:185`）。但设计环修的是
  design 文本，没有可执行代码测试；设计没有定义这个字段在设计环应填什么（可复现反例？文档守卫？
  逐条设计决策的检查？）。
- **为什么是问题**: 「两个环同构」是 D5 的核心声明，但这一条在同构映射上是空的。设计环的作者不知道
  该提供什么证据，审阅者也无法按同一标准验证；最终要么填 `N/A`（弱化既有模板的「每个修复都要红绿」
  要求，违反 `spec.md:25-26` 的「SHALL NOT 被静默弱化」），要么临时发明一套规则。
- **具体收法**: 给设计环定义可验证的修复证据：例如「一条可复现的反例 / 一个在修改前失败的文档守卫 /
  一段逐条对照的决策记录」；或把 Requirement 1.3 明确限定为实现环，并在 Requirement 6 增加设计环的
  对应要求。同步更新 `design.md:71,158,223-224` 与 `spec.md:25,185,210-214`，并在报告表中说明
  `回归测试` 列对设计环允许的替代值。

### I12｜中｜设计环修复面只写 `design.md` / `grill-design.md`，漏 proposal/spec/tasks

- **锚点**: `design.md:225-227`、`spec.md:212-214`、`tasks.md:37`（B4 只写「整合回 `design.md`」）。
- **问题**: D5 与 Requirement 6 把设计环的修复面写成「作者负责改 `design.md` / `grill-design.md`」；
  B4 也只说「把对抗验证的必须修改整合回 `design.md`」。但本 change 的设计制品包括
  `proposal.md`、`specs/review-termination/spec.md`、`tasks.md`；本报告的 must-fix 中 I1（tasks）、
  I2/I3/I7/I8/I9/I10/I11（spec/design）、I4/I5（tasks/design/proposal）都要求改这些文件。
- **为什么是问题**: 作者若按字面只改 `design.md` 和 `grill-design.md`，spec / proposal / tasks 会保留
  同一批缺陷；下一次开批会重新发现它们，增加轮数，甚至把本可一轮修完的问题拖成多轮。设计环的修复面
  与实现环的「代码 + 测试 + change 文档」不同构。
- **具体收法**: 把修复面写成「该 change 的设计制品：`design.md`、`proposal.md`、
  `specs/review-termination/spec.md`、`tasks.md`，以及决策记录 `grill-design.md`」；B4 改为
  「按需整合回上述文件」。在 `spec.md:212-214` 与 `design.md:225-227` 同步。

---

## low / nit 详情

### L1｜proposal 非目标与新增 BLOCKED 成因不一致

`proposal.md:91` 说「不改 `BLOCKED` 的既有语义……只补『超上限』这一成因」；但 `design.md:130`、
`design.md:136-137`、`spec.md:168` 还新增了「同一批反复无法收口」（R2）和验证期安全例外（R3）两个
`BLOCKED` 成因。建议改成「补『超上限』以及新模型需要的验证重试终止点 / 安全例外成因；`BLOCKED`
的终结态语义不变」。不影响可执行性，故登记不修；建议随 I2 一并修。

### L2｜`docs/gate.md:715-716` 的「都合格」容易与出口语义混淆

`docs/gate.md:715` 说 `PASS` / `CHANGES_REQUESTED` 都合格；`:716` 的旧理由是「轮数封顶 → 交人判断」。
落点表只列 `:716`（`proposal.md:112`、`design.md:290`）。新模型下 `CHANGES_REQUESTED` 不是出口，
但机械门禁仍然接受它；建议改 `:716` 时同时补一句「机械接受 ≠ 终结出口；`CHANGES_REQUESTED` 是轮内
状态」，避免读者把「都合格」当成「都是出口」。登记不修，建议顺手修。

### L3｜low/nit 累积链接没有格式

`design.md:165`、`spec.md:95-96`、`spec.md:188` 允许「逐项链接到首次登记的轮次小节」，但没规定
链接形态。建议写成 `[R2-3](round-2.md#第-2-轮--low--nit-登记)` 或等价格式，并要求轮次小节标题稳定。
id 已能人工追溯，故登记不修。

### L4｜变异验证的「1 failed」过脆

`design.md:305`、`tasks.md:54-55` 要求变异后「新测试 1 failed」。同一个变异可能同时触发
`tests/test_templates.py` 与 `tests/test_convergence_stop.py` 的多条断言；更重要的是，变异应选在
I4 指出的未覆盖行（`templates/grill.md:21` 或 `docs/design.md:25`），否则即使全绿也证明不了
反断言有效。建议改为「指定的新守卫至少 1 failed」，并写清目标测试名与变异行。登记不修。

### L5｜R5 的用户裁决没有记录位

`design.md:278-279` 已正确写「`PASS`，或 `BLOCKED` + 成因 + **用户已明确裁决继续**；`BLOCKED`
本身 SHALL NOT 作为写码许可」。但没有规定这个「明确裁决继续」记在哪里。建议记入
`grill-design.md` 的 `## User Confirmation`（或新增 `## Blocked Ruling`），否则硬条件 #2 仍可被
一句无出处的「用户同意了」满足。登记不修。

### L6｜「不碰 src/」不等于「无 code_hits」

`spec.md:248-251` 的 Scenario 写「只改模板/适配器/自述/测试，不碰 `src/`」，容易被读成「不会触发
代码门禁」。实际 `.witnessloop/policy.json:8-12` 的 `require_change_for` 包含 `templates/**` 与
`plugin/**`，所以本 change 改动前后都会要求同一批 `grill-adversarial` / `building` manifest。
Scenario 的结论（不新增 finding 类别/数量）仍然成立，但建议补一句「触发面相同，不是没有触发」。
登记不修。

### L7｜「已结束」与「已收口」未严格区分

`design.md:91`、`spec.md:123` 用「已结束的轮」计数；`design.md:57` 定义轮为「完整闭环」，
`design.md:133` 说 `BLOCKED` 是终结态。建议把计数口径写成「**已收口**的轮（`B_n` 全部验证通过）」，
并明确 BLOCKED / 超上限 BLOCKED 的终结不计入 20。当前语义已隐含，故登记不修。

---

## 对 grill R1–R13 的逐条复核

| 项 | 状态 | 证据 / 缺口 |
|---|---|---|
| R1 第 20 轮自身未收口 | **已整合，仍有缺口** | `design.md:91-95`、`design.md:207-208`、`spec.md:127-129`、`spec.md:139-143`；规范触发过宽，汇总表漏支（I2） |
| R2 验证重试终止点 | **已整合，仍有缺口** | `design.md:75-77,136-137`、`spec.md:29-30,168`；`SHALL` 已统一，但「再次」与「新的可验证方案」不可复核（I3） |
| R3 安全漏洞例外 | **已整合；配套缺口** | `design.md:80-81`、`spec.md:65-68`；例外已收紧为「验证失去意义 / 继续不安全」；deferred 延后理由缺列（I9） |
| R4 旧 review / 孤儿规则 | **已整合** | `design.md:246-256`、`tasks.md:19-23`；与 `src/witnessloop/contract.py:636-666` 的孤儿判据一致；本报告覆盖旧 adversarial；`20f1089` 旧文件 138/939 行已核；不得为旧文件建 manifest |
| R5 grill 写码硬条件 #2 | **已整合；spec 未写（低）** | `design.md:278-279`、`proposal.md:104`、`tasks.md:57`；`BLOCKED` 不再自动放行；建议把裁决记录位写清（L5），并考虑在 spec 补一句 |
| R6 frontier 豁免边界 | **已整合** | `design.md:228-230`、`spec.md:215-217`；仅限进入对抗环之前，批次项驱动的探索属于该轮修复 |
| R7 反断言扫描面 / 排除名单 | **已整合，仍有缺口** | `design.md:292-306`、`tasks.md:41-52`、`proposal.md:128-129`；词表漏旧措辞（I4），扫描面/排除名单口径冲突（I5） |
| R8 severity 冻结 | **已整合** | `design.md:116-118,216-217`、`spec.md:92-94`；验证期只能按原级修或 `BLOCKED`，无静默移出批次路径 |
| R9 deferred 传递 | **已整合** | `design.md:82-84,199-200`、`spec.md:70-71`；已是 Requirement 硬规则，不只是 Scenario；id 沿用 `R<首次轮次>-<序号>` |
| R10 轮数累计 | **已整合** | `design.md:103-105,205-206`、`spec.md:124-126`；按 change（且按环）累计，不得换报告重置 |
| R11 两环 `BLOCKED` 语义 | **已整合，仍有缺口** | `design.md:225-227,282`、`spec.md:210-214`；成因映射与报告节已写；设计环修复面太窄（I12），回归测试无对应物（I11） |
| R12 收口确认记录位 | **已整合，仍有缺口** | `design.md:169-170,270`、`spec.md:189-190`；记录位已加；零轮 PASS / BLOCKED 报告 / 轮内报告未定义（I8、I10） |
| R13 low/nit 累积 | **已整合；链接格式未定（低）** | `design.md:122-123,219`、`spec.md:95-96,187-188`；最终 `PASS` 带累积表或链接；建议定链接格式（L3） |

**逐条结论**：没有发现「只写在 `## Pre-Implementation Review` 清单、完全未进 design/spec/proposal/tasks
正文」的项——R1–R13 都能在正文找到落点。仍有两个层面的缺口：
1. **spec 未覆盖 R4/R5/R7**。R4（旧 review/孤儿）与 R7（测试扫描面）属流程/测试事项，可以留在
   design/tasks；R5 是行为约束（`BLOCKED` 不授予写码许可），建议在 spec Requirement 6 补一句，
   否则 spec 不是完整的规范面。
2. **R1/R2/R7/R11/R12 的正文虽在，但精确度/可复核性不足**，对应 I2/I3/I4/I5/I11/I12/I8/I10。

---

## 测试结果（原始输出）

基线全量测试（设计与实现均未开始，工作树 clean）：

```text
$ /home/happy/.local/bin/uv run pytest -q
........................................................................ [  9%]
........................................................................ [ 19%]
........................................................................ [ 29%]
........................................................................ [ 39%]
........................................................................ [ 49%]
........................................................................ [ 59%]
........................................................................ [ 69%]
........................................................................ [ 79%]
........................................................................ [ 89%]
........................................................................ [ 99%]
...                                                                      [100%]
723 passed in 69.01s (0:01:09)
```

与 `design.md:312` / `proposal.md:133` 的「基线 723 passed」一致。注意：`uv` 不在当前 shell 的
`PATH`，以上用绝对路径 `/home/happy/.local/bin/uv` 执行；CI 测试入口
`.github/witnessloop-tests.txt` 的内容是 `uv run pytest -q`，新增的
`tests/test_convergence_stop.py` 会被全量测试覆盖（前提是实现时把新测试放在 `tests/` 下，符合
`pyproject.toml` 的 `testpaths = ["tests"]`）。

`grill-design.md` 的正文完备性（B1 自检）：

```text
$ PYTHONPATH=src .venv/bin/python -c "from pathlib import Path; from witnessloop.evidence import grill_evidence_findings; p=Path('openspec/changes/convergence-based-stop/reviews/grill-design.md'); print(grill_evidence_findings(p.read_text(encoding='utf-8'), report_path=str(p)))"
[]
```

即 `grill_evidence_findings` = 0 findings，与 `tasks.md:27-29` 的 B1 自检一致。

历史轮次引用的实核：

```text
$ grep -rn '^#.*第 5 轮' openspec/changes/guard-crash-exit/reviews/grill-adversarial.md
openspec/changes/guard-crash-exit/reviews/grill-adversarial.md:593:# 第 5 轮（R5）

$ grep -rn '轮数封顶 · 最后一轮' openspec/changes/events-readpoint-fix/reviews/grill-adversarial.md
openspec/changes/events-readpoint-fix/reviews/grill-adversarial.md:489:# 第 3 轮（R3 · 轮数封顶 · 最后一轮）

$ git show 20f1089:openspec/changes/convergence-based-stop/reviews/grill-design.md | wc -l
138
$ git show 20f1089:openspec/changes/convergence-based-stop/reviews/grill-adversarial.md | wc -l
939
```

`design.md:40-42` 的 R5 / R3 历史引用属实；`design.md:255` 的旧文件行数也属实。`9acdf2b` 与
`20f1089` 均存在（`git cat-file -t` = `commit`）。

---

## 证据命令与关键输出

实际执行过的主要命令（节选）：

```text
$ git status --porcelain=v1
$ git rev-parse HEAD && git rev-parse origin/main
bad76d87ee94e433e9f27b5ce8ec73c1269892e3
46e45b446ca92ea84838490e535a41c529994526

$ git diff --stat origin/main...HEAD
... 6 files changed, 2089 insertions(+)   # design/proposal/tasks/spec/grill-design/grill-adversarial

$ grep -rn -E '封顶|有界轮数|默认 *3 *轮|3 *轮|三轮|到顶|交人' templates/ plugin/ README.md docs/design.md docs/gate.md tests/test_templates.py tests/test_plugin.py
plugin/README.md:37: ... **轮数封顶** ...
plugin/commands/review-loop.md:2: ... 有界轮数 ...
plugin/commands/review-loop.md:29: 6. **有界轮数**（默认上限 3 轮）...
templates/review-loop.md:11: **有界轮数封顶** ...
templates/review-loop.md:90: ### 5. 修复并再审（**轮数封顶**，默认 3 轮）
templates/review-loop.md:101: **封顶**：到第 3 轮仍 `CHANGES_REQUESTED` ...
templates/review-loop.md:153: 三轮封顶时该停下交人判断 ...
templates/grill.md:21: ... 直到 PASS 或封顶
templates/grill.md:140: ... 直到 `PASS` 或**轮数封顶**（默认 3 轮，到顶交人判断）
templates/grill.md:215: ...（或轮数封顶并交人）
docs/design.md:25: ... PASS 或 N 轮封顶
docs/gate.md:716: ...（轮数封顶 → 交人判断）...
README.md:306: ... 有界轮数封顶
tests/test_templates.py:257: # 有界轮数封顶
tests/test_templates.py:258: assert "轮" in text and "封顶" in text
tests/test_plugin.py:176: assert "轮" in text and ("封顶" in text or "上限" in text)
plugin/commands/grill.md:25: ... 直到 `PASS` 或轮数封顶 ...

$ nl -ba templates/review-loop.md | sed -n '75,90p;145,157p'
# 三态表 75-81；:150 verdict 三态；:152-153 旧「三轮封顶」
$ nl -ba plugin/commands/review-loop.md | sed -n '18,31p;60,66p'
# :22 步骤 1–6；:23 verdict 三态；:29 有界轮数；:63 结论三态
$ nl -ba src/witnessloop/evidence.py | sed -n '259,270p;334,380p'
$ nl -ba src/witnessloop/checkcmd.py | sed -n '172,206p'
# checkcmd.py:181-187 无条件调用 grill_evidence_findings_in_change
# evidence.py:259-330 grill 正文判据；:334-380 verify_body=True/False 两种深度
$ nl -ba src/witnessloop/contract.py | sed -n '636,666p'
# 孤儿报告：reviews/**/*.md 每个都必须被某份 manifest 的 report_path 引用
$ cat .github/witnessloop-tests.txt
uv run pytest -q
$ nl -ba .witnessloop/policy.json | sed -n '8,12p'
# require_change_for: src/**、templates/**、plugin/**
```

`docs/gate.md:407/554` 的「常量封顶 / 路径深度封顶」已核，与本规则无关；`docs/gate.md:716` 的旧句
确实含「轮数封顶」。上述 grep 结果就是 proposal 落点表的覆盖对象；落点表本身覆盖了这些行（包括
`templates/review-loop.md:75-81` 与 `plugin/commands/review-loop.md:63`），但反断言词表没有覆盖其中
5 行（I4），落点表也没有覆盖 `plugin/commands/review-loop.md:22-23` 与 `templates/review-loop.md:150`
（I6）。

---

## 第 1 轮结论（历史；已被第 2 轮 PASS 取代）

> 以下是第 1 轮开批时的结论；I1–I12 已在 `6a8deee` 修复并经第 2 轮验证，最终结果为 `PASS`
> （见上方「第 2 轮 · 验证」与「出口」）。保留于此仅为审计历史。

### 必须修改项（12 条，medium+）

1. **I1** `tasks.md:32-33`：B2 的「无轮数上限」与设计环 20 上限直接矛盾。
2. **I2** `design.md:91-93` / `spec.md:127-129`：第 20 轮「任何一项 `未修好`」触发过宽，且与同轮重试
   规则冲突；汇总表漏「第 20 轮自身未收口」这一支。
3. **I3** `design.md:75-77` / `spec.md:29-30`：R2 终止点的「再次」与「新的可验证修复方案」不可复核。
4. **I4** `design.md:303-304` / `tasks.md:46`：反断言词表漏掉 5 行已知旧措辞（裸「封顶」、「N 轮封顶」）。
5. **I5** `design.md:295-302` / `tasks.md:47-52`：显式 allowlist 与「全仓减排除」两种扫描口径并存，
   排除名单不可执行/不完整。
6. **I6** `plugin/commands/review-loop.md:22-23` / `templates/review-loop.md:150`：适配器仍让审阅者
   执行「步骤 1–6」，跳过新模型的 7–8 步；两处「三态」未限定。
7. **I7** `design.md:232-239` / `spec.md:231-239`：`check` 的 `grill` 阶段实际解析报告正文，与
   「只判存在/不解析正文」的诚实边界冲突。
8. **I8** `design.md:61,169-170,179` / `spec.md:189-190,193`：零轮 PASS、第 20 轮收口确认后的
   id / 小节编号未定义。
9. **I9** `design.md:80-81,161-163` / `spec.md:66-68,186`：deferred 延后理由的范围不一致，报告表
   缺「延后理由」列。
10. **I10** `design.md:150,169-173` / `spec.md:182-191`：报告 schema 混淆轮内 verdict 与终结出口；
    轮内 `CHANGES_REQUESTED` 与 BLOCKED 报告无法表达。
11. **I11** `design.md:71,158,223-224` / `spec.md:25,185,210-214`：设计环没有「能变红的回归测试」的
    对应物，两环同构不完整。
12. **I12** `design.md:225-227` / `spec.md:212-214` / `tasks.md:37`：设计环修复面漏 proposal/spec/tasks。

### 已确认无问题项（尝试证伪但未成立的方向）

- **落点行号与旧措辞覆盖**：proposal 落点表覆盖了 `origin/main` 上的全部旧措辞行，包括
  `templates/review-loop.md:11,75-81,90-102,153`、`templates/grill.md:21,130-141,215`、
  `plugin/commands/*`、`plugin/README.md:37`、`README.md:306`、`docs/design.md:25`、
  `docs/gate.md:716`、两条测试；`docs/gate.md:407/554` 的「常量封顶 / 路径深度封顶」确与本规则无关。
  漏网的是**反断言词表**和**适配器 1–6 步**，不是落点表本身（I4/I6）。
- **deferred 传递与 id 沿用**：`spec.md:70-71` 把传递写成 Requirement 硬规则，不只是 Scenario；
  `spec.md:73-82,197-201` 与 `design.md:83-84,179` 的 `R3-2` 例子、id 沿用规则一致。零轮/收口确认后的
  id 是边界缺口（I8），不是主规则不一致。
- **severity 冻结**：`spec.md:92-94` 对验证期降级给出对称规则（按原级修或 `BLOCKED` 记争议），
  `spec.md:79-82` 把 low→medium 的重分类导向 deferred 而非扩批；未发现静默降级/移出批次的主路径。
- **R4 旧 review / 孤儿规则**：`design.md:246-256` 与 `src/witnessloop/contract.py:636-666` 的
  「`reviews/**/*.md` 必须被 manifest 绑定」一致；A5b 的「覆盖或移出、不得绑旧文件」写法足以避免
  「绑旧文件 = 假证据」。本报告已覆盖旧 adversarial；旧内容只在 git 历史，符合 D8。
- **R5/R6 的安全性**：`design.md:278-279` 明确 `BLOCKED` 本身不是写码许可；`design.md:228-230` /
  `spec.md:215-217` 把 frontier 限定在进入对抗环之前，批次项驱动的探索不能改标 frontier。未发现可
  直接利用的豁免口子（frontier 阶段本身不设轮数上限，是用户模型的有意选择，不是本 change 的漏洞）。
- **历史证据、基线与 grill 自检**：`guard-crash-exit` R5 `:593`、`events-readpoint-fix` R3 `:489`
  逐字命中；`20f1089` 旧文件 138/939 行；全量测试 **723 passed**（原始输出见上）；
  `grill_evidence_findings` 对 `grill-design.md` = **0 findings**；`.github/witnessloop-tests.txt`
  是 `uv run pytest -q`，新测试会被 CI 全量覆盖。

**总结**：核心模型（非空批次计轮、验证期禁提新问题、deferred、medium+ 全修、low/nit 登记、20 上限、
三出口、两环共用）已经写进 design/spec/proposal/tasks，主路径基本成立。当前不能判 `PASS` 的原因是
**可执行性与边界精确度**：B2 仍有无上限旧口径、第 20 轮触发时序过宽、反断言词表漏已知旧措辞、
机械门禁诚实边界写错、适配器跳过新步骤，以及报告 schema 无法表达轮内/BLOCKED 状态。这些都是
medium+ 可修项，不需要重开用户已拍板的三个参数。

---

> 本报告只覆盖 `openspec/changes/convergence-based-stop/reviews/grill-adversarial.md`；未修改其它文件，
> 未 commit。旧模型报告内容未保留。
