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
| 受保护写入 | `checkcmd._protected_writes`（`checkcmd.py:123-180`） | 需 `workflow-events.jsonl` 解释事件 |

⇒ **`building` 这个 stage 在 `src/` 里 0 处功能性命中**（`grep -rn building src/` 只命中 `cli.py:107,111` 的 `--help` 文案；grill 实测纠正——原稿写"0 命中"字面不成立）——**跳过 review-loop 的 PR 照样绿**。

**已有的一半（很关键）**：`contract._check_git_span`（`contract.py:272-352`）要求 manifest 的 `head_sha`
是**被检 head 的祖先**、且 `head_sha..被检 head` 之间的改动**只许是证据文件**。⇒
**审阅之后再改任何非证据文件 ⇒ 该 manifest 判 stale ⇒ 红**。所以「审完又改代码」**已经**被堵住了；
本 change 只补「**必须存在**」这一半。

**与 asterwynd 的先例对比**（**按函数名定位** `_check_review_manifests`；实测在 `scripts/check_openspec_artifacts.py:1110-1145`——
⚠️ **不按行号引用**：跨仓行号随对方 git 漂移即失效，grill 实测原稿引的 `:1009-1048` 已漂）：



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
   （asterwynd 自己也为此写了「post-PASS tasks edits」的应对——**按函数名**定位，实测在其 `:1716`）。**witnessloop 不宜照抄。**
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
- ⚠️ **多 change 同 PR 的边界（grill Q2 / R-new-1，高；原稿只覆盖单 change）**：触发是**全局**的
  （只看「本次 diff 有没有触及 `require_change_for`」），而要求施加在**每个** `change_id` 上
  ⇒ **一个 PR 改了代码 + 顺带新增另一个纯文档 change，那个文档 change 也会被要求 building 证据**（grill 实测 S2′ 复现）。
  **定案**：**不**去猜「代码属于哪个 change」（witnessloop 无此概念，硬做会引入第二套「什么算代码」的口径）。
  改为**显式化流程约束**：「**一个 PR 推进一个 change**」是前提。
  ⚠️ **对抗验证纠正**：原稿说它与既有的「内容/证据分属两提交、单提交 PR 不被支持」（`docs/gate.md:172-177`）**同族**——
  **不准确**：那条约束的是**提交顺序**，这条约束的是 **change 数量**，是**本 change 新造**的（实测：多 change PR 未打补丁 `exit 0`、打补丁后 `exit 1`）
  ⇒ 它本身就是**一条新的对外行为变更**，须与 D5 那条一并写进 README（原稿只在 tasks D3 记了另一条）。
  spec 里**加 Scenario 把多 change 边界钉死**：
  「本 PR 触及 `require_change_for` ⇒ 本 PR 触及的**每个** change 都要 building 证据；要免除就把 change 拆到单独 PR」。
  **不加** `building_exempt_changes` 豁免名单——豁免名单是**新的绕过面**。

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

### D3.1 **必须显式声明**：「PASS 不成为硬门」（对抗验证 Q1 的建议）

若 Q1 选**甲**，则**必须在 `proposal.md` 与 PR 正文里写明**：本 change 让「**闭环必须跑过**」成为机械门，
但 **verdict 文本（PASS/CHANGES_REQUESTED）不参与判定** ⇒ 「**PASS 不是硬门**」这一点**没有被本 change 改变**。
不写清，读者会把 issue #13 的标题（「**PASS** 不是硬门」）误读成「本 change 之后 PASS 变硬门了」。
（对抗验证的判读：issue #13 的 *需求* 段本就写的是「要求**证据存在**」，并把「是否机械判 PASS 文本」列为待定 Open Question
⇒ 甲**满足 issue 原文**，只是需要把这层边界讲明白。）

### D4 **不改 `guard`**

写码**之前**不可能有「实现后」的审阅 ⇒ `guard` 仍只查 grill 证据。若强加，会**自锁**（永远写不了码）。
`spec` 须写明这条边界。

### D5 文档 / 行为变更

- `docs/gate.md §6`（`check` 的红项清单加「缺 building 审阅证据」）+ `§8`（新增一小节：building 门禁的触发与判据）。
- `README.md`：**对**接入方**是两条行为变更**（**都要写明**，口径同 `grill-evidence-gate` 那次）：
  ① 「改了代码但没跑 review-loop」的 PR 从**绿变红**；② **多 change 同 PR** 时**每个** change 都要 building 证据
  （原本可以「一个 PR 捎带一个纯文档 change」，现在会被红——对抗验证实测 `exit 0 → exit 1`）。
- `templates/review-loop.md`：若选**乙**，须在此规定多轮报告的最终裁定形态；选**甲**则补一句「本门禁只要求证据存在，
  结论由人/流程负责」。

### D6 回归红线（**原稿的风险评估被 grill 实测证伪**）

本仓三个 active change **都有** `building.manifest.json`（实测）⇒ 接上后不得把它们的证据判红。

⚠️ **原稿（R1/本节的旧稿）声称「接上后一批既有用例会变红、须逐条改期望」——grill 在 `/tmp` 副本实测证伪**：
按本 design 真打补丁后跑全量 = **404 passed，与基线逐条相同，0 条新增失败**。根因：
D1 的触发条件是「diff 触及 `require_change_for`」，而既有用例里**凡触及 `src/**` 的都已写了 building 证据**
（`helpers.commit_evidence` 默认 `stages=("grill","building")`，`helpers.py:214`；
`write_review` 默认 `stage="building"`，`helpers.py:116`）；**只写 `stage="grill"` 的用例只动 change 目录**，
不触及 `require_change_for` ⇒ 不触发。⇒ tasks 的 C1「逐条修既有用例的期望」会**空转**，
应缩为「**确认无需改动** + 只加新增用例」（grill R-new-2）。

## 3. 接线点（实现清单）

- `src/witnessloop/policy.py`：`evidence.building_stage`（默认 `constants.DEFAULT_BUILDING_STAGE`）。
- `src/witnessloop/constants.py`：`DEFAULT_BUILDING_STAGE = "building"`。
- `src/witnessloop/evidence.py`：把「必须有 stage=X 的 manifest」抽成**参数化助手**（现有 grill 那条是硬编码 `grill_stage`），
  **两处共用**——本仓最忌「两边各写一套」（`constants.HASHED_ARTIFACTS` 就是这么来的）。
  ⚠️ **实现细节**：现有函数还**顺带**校验报告正文（grill 专有）⇒ 抽取时须让「只要求存在」的调用方**不**触发正文校验。
  **切法（grill D-F 实测可行）**：`stage_manifest_findings_in_change(change_dir, *, stage, manifest_glob, label, reason, verify_body=False)`
  ——`verify_body=False` 时执行到「报告解析得到且 `is_file()`」为止就返回；grill 分支传 `verify_body=True` 才走到正文读点。
  ⚠️ **R-new-3**：抽参后 grill 那句文案（`evidence.py:203`「grill 决策记录必须有对应的审阅证据」）若被做成**通用措辞**，
  等于削弱诊断性；故把 `reason` 做成**参数**（各 stage 传自己的那句子串）——**参数 ≠ 第二份实现**，spec 的「共用同一实现」仍成立。
- `src/witnessloop/checkcmd.py`：change 循环里加 building 那条（触发条件见 D1）。
- `tests/`：**只加**新增用例（grill 实测既有用例**无需改动**）；另加一条「多 change 同 PR」的边界用例（D1/Q2）。
- `docs/gate.md` / `README.md` / `templates/review-loop.md`（D5）。

## 4. 风险

1. ~~**R1（高，自伤面）**~~ → **已降级为「观测到 0 条」**（grill 实测 404 passed 不变，见 D6）。
   留存价值：它提醒我们「**风险要实测，不要照直觉估**」。
2. **R2（中）**：D1 的触发条件若写错（如把「change 目录被改」也算成实现）⇒ 提案期 change 被误伤。
3. **R3（中）**：D3 选乙 ⇒ 多轮格式规范 + 历史回填 + 「封顶交人」出路，三者缺一不可。
4. **R4（中）**：与 grill 那条**共用助手**若抽错（把 grill 的正文校验泄漏给 building）⇒ building 被要求写 grill 式正文。
5. **R5（**低 → 中**，grill 升级）**：`require_change_for=[]`（或没覆盖真实代码路径）的仓 ⇒ D1 永不触发 ⇒
   building 门禁**静默失效**；grill 实测更狠：它**连 `_require_change`（改代码必须挂 change）一起失效**（S4′ 实测 `check` 绿）
   ⇒ 关掉的是**整条代码门禁**，不只是 building。须在 `docs/gate.md §2` 与 spec 显式声明。
   （是否再加「`require_change_for` 为空时 warning」见 **Q4**——那会把 `tests/test_require_change.py::test_empty_require_change_for_disables_the_rule`
   从绿改红，是**有意**的契约变更。）
6. **R6（低，诚实边界 · grill R-new-5）**：本门禁只保证「**有一份可绑定的 manifest 存在**」，
   **不保证**真跑了一次独立 run——兜底路径下 `reviewer_run_id ≠ author_run_id` **结构性恒真**（`docs/gate.md:121-123`），
   一个 agent 即可自造 manifest 满足它。⇒ 对外表述须限定为「**证据存在性**机械、**审阅真实性**不机械」（与 grill 同一边界）。
7. **R7（低）**：asterwynd 跨仓引用**改按函数名**，不按行号（见 §1）。

## 5. 测试策略（TDD）

- **先红**：改了受管控代码 + 只有 grill 证据 ⇒ `check` 红、文案点名「缺 building 审阅证据」；
  改文档/只动 change 目录（无实现）⇒ 不要求；`stage` 拼错 ⇒ 点名现有 stage；审阅后再改代码 ⇒ **stale 红**（既有能力，加回归钉住）。
- **回归**：本仓三个 active change 的证据判合格；`guard` **不**受本 change 影响（它仍只查 grill）。

## 6. 文档影响

`docs/gate.md §6/§8`、`README.md`（对**接入方**的行为变更）、`templates/review-loop.md`（依 D3）。

## 7. Pre-Implementation Review

**已确认决策（grill 逐条自核 · 来源 `grill-reviewer-building-review-gate-2026-10-12`）**：
D-A 触发条件选 `require_change_for`（客观 git 事实）✅；D-B「审阅须在最终实现之后」这半边**已存在**
（`contract._check_git_span` 逐份判 stale，grill **实测**：审后再改一行 `src/` ⇒ 两份 manifest 都被点名 stale）✅；
D-C §1 的「多轮 / verdict 记法不统一」表**属实**（逐份打开确认）✅；D-E 与 asterwynd 的先例对比实质成立 ✅；
D-F 共用助手的切法（`verify_body` 开关）实测可行 ✅。

**被 grill 证伪并已修正**：
- **自伤面（原 R1/D6）「一批既有用例会变红」→ 实测 0 条**（404 passed 不变）⇒ 已改写 D6 + tasks C1 缩为「确认无需改动」。
- §1「`building` 在 `src/` 0 命中」**字面不成立**（`cli.py:107,111` 有 `--help` 文案）⇒ 改为「0 处**功能性**命中」。
- asterwynd 引用行号**已漂移**（原 `:1009-1048` → 实测 `:1110-1145`）⇒ 改**按函数名**引用。
- **新发现（高）**：D1 触发是**全局**的、而要求施加在**每个** change 上 ⇒ **多 change 同 PR 会误伤纯文档 change**（实测 S2′）
  ⇒ 已补 D1 边界 + Q2。
- R5 严重性**由低升中**：`require_change_for=[]` 会连 `_require_change` 一起失效（实测 `check` 绿）。

**对抗验证 R1（CHANGES_REQUESTED → 已整合）**：
- **阻塞项**：design D1 要求「在 spec 里加 Scenario 钉死多 change 边界」，但 `spec.md` **没有**那条 Scenario
  ⇒ 规范件与设计不一致（已补）；既有 Scenario 的括注「（只改文档或只动 change 目录）」会**诱导错误泛化**（已限定为「单 change 情形」）。
- **自伤面独立复现：0 条新增失败**（对抗验证**自己**写补丁、且先证明补丁**真接进了判定路径**才计数）⇒ grill 的关键经验事实**成立**。
  附一个环境坑：`/home/happy/.local/bin/witnessloop` 是**另一份 uv-tool 安装**（无补丁），用它跑会**测到未打补丁的行为**（假绿）。
- Q1 不阻塞（issue #13 的需求段本就要求「证据存在」）；R6 成立；**无自锁**（本 change 自己的 E0 序列已推演+实测）。

**Code-Resolved 结论**：`_check_git_span` 与 stage 无关、逐份判 stale；参数化助手不撞既有断言
（唯一断言 stage 文案的 `test_check_grill_evidence.py:53` 仍保留）；`docs/gate.md` 的 §6/§8 引用正确。

## 8. Open Questions（停轮待用户确认）

> 已按 grill 收敛重排（原 Q2 的「触发条件」被 grill 证伪为**表述不全**——真问题是**多 change 同 PR**；
> 新增 Q4 由 grill 提出）。

- **Q1** **verdict 文本是否机械判 PASS**？
  **甲（推荐）**：不解析——与 asterwynd 先例一致（它只要证据存在），避开「格式规范 + 历史回填 + 覆盖机制」三笔成本。
  **乙**：要求最终裁定 = PASS。代价：3 份历史报告**最终裁定形态不一致**（`- 裁定: **PASS**` ×2 与 `## Verdict` + `**PASS**（无阻塞项）` ×1）
  ⇒ 须先规范一种机器可读形态并回填；且与 `templates/review-loop.md:99-100`「三轮封顶 → 停下交人判断」**直接冲突**，
  出路得是**被 manifest 绑定**的一份 `reviews/<stage>-override.md`（而非报告内自由文本——那是新的手写绕过面）。
- **Q2** **多 change 同 PR** 怎么办？**推荐**：显式化「一个 PR 推进一个 change」前提 + spec 钉死边界
  （本 PR 触及代码 ⇒ 本 PR 触及的**每个** change 都要 building 证据；要免除就拆 PR）。**不加豁免名单**（=绕过面）。
- **Q3** 对**既有接入方**的行为变更怎么落？**推荐**：**只写文档** + 明确「对**接入方**是行为变更」，**不加过渡开关**（开关=静默绕过面）。
- **Q4**（grill 新提）`require_change_for=[]` 让**整条代码门禁**静默失效——只写文档够吗？
  **推荐**：至少写进 `docs/gate.md §2` + spec；是否加「为空时 warning」请用户定（会让一条既有用例**有意**变红）。

（每条的具体例子与推荐答案见 `reviews/grill-review.md` 的 `## Open Questions`。）
