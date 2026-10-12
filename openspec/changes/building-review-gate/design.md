# Design: building-review-gate

> 状态：**草稿**（待设计 grill + 对抗验证收敛 → 停轮用户确认）。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。
> 先例调研见 §1「与 asterwynd 的先例对比」（已读源码）。

## 0. 一句话

把「实现后独立审阅」那一半补成**硬门**：本次 diff 落了实现 ⇒ 该 change **必须**有一份 `stage=building`
的审阅证据，且它必须**审在最终 revision 上**（后者复用既有的 `base_sha`/`head_sha` span 判定）。

## 1. 现状（实测，带 `文件:行号`）

**`check` 今天判什么**（`checkcmd.py:71-89`，逐条读）：

| 判定 | 位置 | 要求 |
|---|---|---|
| change 契约 | `contract.validate_change_dir`（`contract.py:89-100`） | `proposal.md`/`design.md`/`tasks.md`/`specs`/`reviews` 齐备 |
| 有 manifest | `contract.validate_review_manifests`（`contract.py:121-149`） | **至少一份** `reviews/*.manifest.json`；每份过 hash/revision/reviewer≠author；**孤儿报告**不许有 |
| grill 证据 | `evidence.grill_evidence_findings_in_change`（`checkcmd.py:78-84`） | **必须有 `stage=grill` 的 manifest**，且其报告正文合格 |
| 代码必须挂 change | `checkcmd._require_change`（`checkcmd.py:92-120`） | 改了 `require_change_for` 路径 ⇒ 必须有 change 目录 |
| 受保护写入 | `checkcmd._protected_writes`（`checkcmd.py:122-180`） | 需 `workflow-events.jsonl` 解释事件 |

⇒ **`building` 这个 stage 在 `src/` 里 0 命中**（全树 grep）——**跳过 review-loop 的 PR 照样绿**。

**已有的一半（很关键）**：`contract._check_git_span`（`contract.py:272-352`）要求 manifest 的 `head_sha`
是**被检 head 的祖先**、且 `head_sha..被检 head` 之间的改动**只许是证据文件**。⇒
**审阅之后再改任何非证据文件 ⇒ 该 manifest 判 stale ⇒ 红**。所以「审完又改代码」**已经**被堵住了；
本 change 只补「**必须存在**」这一半。

**与 asterwynd 的先例对比**（`scripts/check_openspec_artifacts.py:1009-1048`，已读）：

```python
requires_building_review = (
    not archived and change_type.primary != "docs"
    and _changed_capabilities(change_dir) and _tasks_all_complete(change_dir)
)
if requires_building_review and not review_report.exists():
    return ["building-review.md missing — 独立 subagent 审阅未运行。"]
```

三点结论：
1. **它要求存在，不解析 verdict 文本**（全文件无 verdict/PASS 解析；注释里的 “produced a PASS manifest” 指
   **被 manifest 绑定的那份证据**）。⇒ 「PASS 硬门」的实质是「**闭环必须跑过**」。
2. 它的触发条件含 `_tasks_all_complete`（**tasks.md 全部勾选**）——**这是自声明**：**不勾选就能绕过**
   （asterwynd 自己也为此写了「post-PASS tasks edits」的应对，见其 `:1409`）。**witnessloop 不宜照抄。**
3. 它另有 `change_type != "docs"` / `_changed_capabilities`（有 spec delta）两个豁免面——witnessloop 的 change
   契约**本就**要求 `specs/` 齐备，没有 `ChangeType` 概念，故这两条在本仓**不存在对应物**。

**既有报告是「多轮」结构**（三个 active change 实测）：

| change | 顶层 `## Verdict` | 后续轮 |
|---|---|---|
| `dogfood-bootstrap` | **CHANGES_REQUESTED** | `## 第 2 轮审阅`（裁定 PASS）、`## 第 3 轮审阅`（PASS） |
| `grill-evidence-gate` | **CHANGES_REQUESTED** | `## 第 2 轮审阅`（PASS） |
| `guard-crash-exit` | **PASS** | `# 第 2 轮（R2）`（PASS） |

⇒ 报告的**最终裁定**不在固定位置（顶层往往是**第 1 轮**的），且**轮次的记法不统一**
（`## 第 N 轮审阅` / `- 裁定:` / `# 第 N 轮（RN）`）。**任何「读顶层 Verdict」的机械判据都会误伤本仓自己的历史。**

## 2. 决策

### D1 触发条件：**本次 diff 触及 `policy.require_change_for` 下的路径**（= 落了实现）

- 复用 `_require_change`（`checkcmd.py:92-120`）**同一个字段与同一个匹配**（`pathutil.matches_any`）——
  不引入第二个「什么算代码」的口径（本仓已因「两边各写一套」踩过坑）。
- **为什么不照抄 asterwynd 的 `_tasks_all_complete`**：那是**自声明**——**不勾选就绕过**。
  「改了受管控代码」是**客观事实**（来自 git diff），不可通过不勾选规避。
- 边界（须写明）：**纯文档 / 纯 change 目录改动**（提案期、还没实现）⇒ **不要求** building 证据。
  否则每个 in-flight change 都会红（asterwynd 的注释里也专门提了这点）。

### D2 判据：**必须有 `stage=building` 的 manifest**（policy 轴 `evidence.building_stage`，默认 `building`）

- 形态：与 grill 那条**并列**——`check` 的 change 循环里，若 D1 触发则要求存在该 stage 的 manifest；
  缺则**红**且**点名现有 stage**（拼错可诊断，口径与 grill 那条一致）。
- **revision 绑定不用新写**：`_check_git_span` 已经保证「manifest 的 head_sha 之后不许有非证据改动」
  ⇒ 合起来就是「**审阅必须发生在最终实现之后**」。这是本 change 最省力的地方：**补一半，另一半已在**。
- **不额外要求报告正文结构**（除 D3 若选乙）：manifest 的 `report_path` 必须解析到存在的报告
  （`contract._check_hashes` 已覆盖），孤儿规则已覆盖「报告必须被绑定」。

### D3 **verdict 文本是否机械判 PASS** —— 待用户裁定（**Q1**，甲/乙）

- **甲（推荐 · 先例一致）**：**不解析 verdict 文本**。与 asterwynd 先例一致（「闭环必须跑过」= 硬门），
  且**避开**多轮格式问题（§1 表：顶层 Verdict 常是第 1 轮的 CHANGES_REQUESTED）。
  **诚实边界**：这样「审阅结论是 CHANGES_REQUESTED」也能合入——但那**正是 review-loop 的规定行为**
  （`templates/review-loop.md:99-100` 三轮封顶后「**停下向用户报告，升级到人判断**」⇒ 人**可以**决定照合）。
- **乙（更严）**：要求报告正文的**最终裁定 = PASS**。代价与前置：
  1. 必须先**规定多轮格式**（例如：报告**末尾**必须有一行机器可读的最终裁定，或规定「顶层 Verdict 即当前裁定、
     历史轮次降为子节」）⇒ **要改 `templates/review-loop.md` + 回填本仓 3 份历史报告**；
  2. 必须**给「三轮封顶交人」一个出路**（否则等于取消了该模板条款）——最省的是**记录式的人工覆盖**
     （如报告里一节 `## Human Override`：人工决定 + 理由 + 时间），但那是**又一层**设计。
  ⇒ 乙的**收益**（堵住「跑是跑了、结论是 CHANGES_REQUESTED 也照合」）与**成本**（格式规范 + 历史回填 +
  覆盖机制）都在，**是否值得**是取舍。

### D4 **不改 `guard`**

写码**之前**不可能有「实现后」的审阅 ⇒ `guard` 仍只查 grill 证据。若强加，会**自锁**（永远写不了码）。
`spec` 须写明这条边界。

### D5 文档 / 行为变更

- `docs/gate.md §6`（`check` 的红项清单加「缺 building 审阅证据」）+ `§8`（新增一小节：building 门禁的触发与判据）。
- `README.md`：**对**接入方**是行为变更**——「改了代码但没跑 review-loop」的 PR 从**绿变红**（须写明，口径同
  `grill-evidence-gate` 那次）。
- `templates/review-loop.md`：若选**乙**，须在此规定多轮报告的最终裁定形态；选**甲**则补一句「本门禁只要求证据存在，
  结论由人/流程负责」。

### D6 回归红线

本仓三个 active change **都有** `building.manifest.json`（实测）⇒ 接上后不得把它们的 grill/building 证据判红。
⚠️ 直接注入的具体形态：`tests/test_*` 里造 change 的既有 helper（`helpers.write_review(stage="building")`）
**已经**会写 building 证据——但**多数既有用例只写 grill**（`commit_evidence(stages=("grill","building"))` 是默认，
`write_review(stage="grill")` 的单写也不少）⇒ **接上后一批既有用例会变红**，属**预期的自伤面**，
须**逐条改期望**（不是 bug，是行为变更的落地）。**实现清单必须含这一步。**

## 3. 接线点（实现清单）

- `src/witnessloop/policy.py`：`evidence.building_stage`（默认 `constants.DEFAULT_BUILDING_STAGE`）。
- `src/witnessloop/constants.py`：`DEFAULT_BUILDING_STAGE = "building"`。
- `src/witnessloop/evidence.py`：把「必须有 stage=X 的 manifest」抽成**参数化助手**（现有 grill 那条是硬编码 `grill_stage`），
  **两处共用**——本仓最忌「两边各写一套」（`constants.HASHED_ARTIFACTS` 就是这么来的）。
  ⚠️ **实现细节**：现有函数还**顺带**校验报告正文（grill 专有）⇒ 抽取时须让「只要求存在」的调用方**不**触发正文校验。
- `src/witnessloop/checkcmd.py`：change 循环里加 building 那条（触发条件见 D1）。
- `tests/`：新增判定用例 + **改既有受影响用例的期望**（D6 自伤面）。
- `docs/gate.md` / `README.md` / `templates/review-loop.md`（D5）。

## 4. 风险

1. **R1（高，自伤面）**：接上后**既有用例大面积变红**（很多 change fixture 只有 grill 证据）⇒ 逐条改期望（D6）。
2. **R2（中）**：D1 的触发条件若写错（如把「change 目录被改」也算成实现）⇒ 提案期 change 被误伤。
3. **R3（中）**：D3 选乙 ⇒ 多轮格式规范 + 历史回填 + 「封顶交人」出路，三者缺一不可。
4. **R4（中）**：与 grill 那条**共用助手**若抽错（把 grill 的正文校验泄漏给 building）⇒ building 被要求写 grill 式正文。
5. **R5（低）**：`require_change_for` 为空的仓（显式关掉该规则）⇒ D1 永不触发 ⇒ building 门禁**静默失效**。须写明。

## 5. 测试策略（TDD）

- **先红**：改了受管控代码 + 只有 grill 证据 ⇒ `check` 红、文案点名「缺 building 审阅证据」；
  改文档/只动 change 目录（无实现）⇒ 不要求；`stage` 拼错 ⇒ 点名现有 stage；审阅后再改代码 ⇒ **stale 红**（既有能力，加回归钉住）。
- **回归**：本仓三个 active change 的证据判合格；`guard` **不**受本 change 影响（它仍只查 grill）。

## 6. 文档影响

`docs/gate.md §6/§8`、`README.md`（对**接入方**的行为变更）、`templates/review-loop.md`（依 D3）。

## 7. Pre-Implementation Review

> 待 grill + 对抗验证后填写。

## 8. Open Questions（停轮待用户确认）

- **Q1** **verdict 文本是否机械判 PASS**？甲（不解析，与 asterwynd 先例一致，推荐）/ 乙（要求最终裁定 = PASS，
  但须先定多轮格式 + 给「三轮封顶交人」一个记录式出路 + 回填本仓 3 份历史报告）。
- **Q2** 触发条件是「**本次 diff 触及 `require_change_for`**」（推荐，客观事实）还是「**tasks.md 全部勾选**」
  （asterwynd 口径，但可被「不勾选」绕过）？
- **Q3** 对**既有接入方**的行为变更怎么落：只写文档告知，还是提供一个「过渡开关」？（我倾向**只写文档**——
  开关=绕过面。）

（每条的具体例子与推荐答案见 `reviews/grill-review.md` 的 `## Open Questions`。）
