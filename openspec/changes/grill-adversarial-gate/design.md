# Design: grill-adversarial-gate

> 状态：**草稿**（待设计 grill + 对抗验证收敛 → 停轮用户确认）。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。
> 先例调研见 §1.3（asterwynd 源码实测）。churn 数字见 §2 D2（本机实测，非估计）。

## 0. 一句话

把「设计阶段的对抗验证轮」补成**硬门**：触发条件满足时，该 change **必须**有一份 `stage=grill-adversarial`
的审阅证据——判定**复用** `building` 那条的同一实现（`evidence.stage_manifest_findings_in_change`），
revision 绑定那一半**已经在**。

## 1. 现状（实测，带 `文件:行号`）

### 1.1 `check` 今天判什么

| 判定 | 位置 | 要求 |
|---|---|---|
| change 契约 | `contract.validate_change_dir` | `proposal.md`/`design.md`/`tasks.md`/`specs`/`reviews` 齐备 |
| 有 manifest | `contract.validate_review_manifests`（`contract.py`） | ≥1 份 `reviews/*.manifest.json`；每份过 hash/revision/reviewer≠author；**孤儿报告**不许有 |
| grill 证据 | `evidence.grill_evidence_findings_in_change`（`checkcmd.py:83-88`） | **必须有 `stage=grill` manifest**，且其报告**正文**合格 |
| building 证据 | `checkcmd.py:91-98`（#13） | `code_hits` 时**必须有 `stage=building` manifest** |
| 代码必须挂 change | `checkcmd._require_change`（`checkcmd.py:125-145`） | 改了 `require_change_for` 路径 ⇒ 必须有 change 目录 |
| 受保护写入 | `checkcmd._protected_writes`（`checkcmd.py:148-206`） | 需 `workflow-events.jsonl` 解释事件 |

### 1.2 缺口

- `grep -rn "grill-adversarial" src/` = **0 命中**（实测）；`tests/` 里的命中全在「孤儿报告」与「模板文案」用例里，
  即它们把 `grill-adversarial` 当**一个任意 stage 名**用，不构成任何强制。
- `templates/grill.md:197-202` 的硬约束 #2「对抗验证已到 PASS（或轮数封顶）才可写码」**无机械检查**。
- 本仓 5 个 active change 的 `reviews/` 里**都有** `grill-adversarial.manifest.json`（实测），
  但那是**我每次都跑了**，不是门禁要求的 ⇒ 证据齐备**不构成**「有门禁」的证据。

⇒ 三态：grill **有门**、building **有门**、中间的对抗轮**没有门**。而对抗轮是**唯一**在最近 4 个 change 里
稳定抓到「设计结论错」的环节（proposal「背景」列了三类）。

### 1.3 与 asterwynd 的先例对比（实测）

| 维度 | asterwynd | witnessloop 现状 |
|---|---|---|
| 位置 | **归档点**（`_check_archived_completion_gate`，`scripts/check_openspec_artifacts.py:1565`；`called at :1685` 只对 `archive/<dir>`） | 无 archive 门禁 ⇒ 只能挂在 `check` 的 active change 判定上 |
| 触发 | `primary != "docs"` ∧ `all_types & DESIGN_TYPES` ∧ `_changed_capabilities` | 无 `ChangeType`、`specs/` 恒备 ⇒ 无对应物，须另定（Q1） |
| 证据形态 | 裸文件 `reviews/grill-adversarial.md` 存在 | **不能用裸文件**（见 D1） |
| verdict | 不解析（注释明写「存在性即可」，`:1630`） | 同（D3 甲） |
| 本地守卫 | **不管**（`grep -c adversarial scripts/workflow_guard.py` = 0） | 同（D4） |

三点结论：

1. **「只要存在、不解析 verdict」有先例**——甲不是偷懒，是**与先例同口径**。
2. **触发面必然是对先例的偏离**（它挂归档点 + 三重豁免，本仓一个都表达不了）⇒ 这条必须写清并请用户裁定，
   不能假装「照先例办」。
3. **守卫侧不要求有先例**——D4 不动 `guard` 与先例一致。

## 2. 决策

### D1 证据形态：`stage=<grill_adversarial_stage>` 的 manifest（**不是裸文件**）

- **不复刻 asterwynd 的裸文件**：本仓有**孤儿报告**规则（`contract._check_orphan_reports`）——
  `reviews/*.md` 若没有被任何 manifest 绑定 ⇒ **判红**（既有用例实测：把 `grill-adversarial.md` 晾着即被点名）。
  ⇒ 裸文件在 witnessloop 里**连绿都拿不到**，形态只能走 manifest。
- 复用 `evidence.stage_manifest_findings_in_change`（`evidence.py:172-235`），`verify_body=False`。
  该助手已参数化（#13 的产物）：传 `stage` / `manifest_glob` / `label` / `reason`。
  **不写第二份实现**——本仓已因「两边各写一套」踩过坑（`constants.HASHED_ARTIFACTS` 就是这么来的）。
- 新增 policy 轴 `evidence.grill_adversarial_stage`（默认 `constants.DEFAULT_GRILL_ADVERSARIAL_STAGE = "grill-adversarial"`），
  与 `grill_stage` / `building_stage` 同形；写入 `default_policy_doc()`（老 policy 缺字段 → 回落到出厂默认，保护性默认）。
- `verify_body=False` 的**语义**：「manifest 存在 + 其 `report_path` 解析到存在的报告」。
  报告**正文**不校验（D3 甲）。

### D2 触发条件 —— **甲/乙 = Q1（停轮用户裁定）**

- **甲（与 grill 那条同形）**：**无条件**——每个被本次 diff 触及的 change 都要有对抗轮证据。
- **乙（与 building 那条同形）**：**`code_hits`**（本次 diff 触及 `policy.require_change_for`）时才要。

**实测 churn**（本机 `/tmp/ga-probe` = 本 worktree 的副本 @ `f77edf0`；基线 **420 passed**；
补丁 = 在 `checkcmd` 的 change 循环里加一条与 building **完全同形**、只换 `stage` 的判定）：

| 触发 | 不改 `helpers` 默认 | `commit_evidence` 默认 stages 改为 `("grill","grill-adversarial","building")` |
|---|---|---|
| **甲** 无条件 | 30 failed / 390 passed | **17 failed / 403 passed** |
| **乙** `code_hits` | 6 failed / 414 passed | **4 failed / 416 passed** |

乙 剩下的 4 条是**自造证据集**的用例（`test_building_gate.py` 3 条 + `test_check_protected.py::
test_renaming_with_an_event_is_allowed` 1 条）；甲 的 17 条里含 `test_orphan_reports.py` 6 条、
`test_manifest_build.py` / `test_acceptance.py` 等（实测清单见 tasks B3 的实测记录）。

**推荐乙**，四条理由：

1. **一个触发概念就够**：「本 PR 落了实现」已经是 building 的门槛，对抗轮只是同一时点的**另一端证据**
   （`templates/grill.md` 的硬约束说的正是「**写码前**必须收敛」）；
2. **churn 4 vs 17**（且 4 条都是夹具必须显式改、语义清晰）；
3. 与先例的**豁免面同调**：asterwynd 也**不给** docs-only / 无 spec delta / 非设计类 change 要这道证据——
   witnessloop 能表达的、最接近的客观判据就是「本次 diff 落了实现」；
4. 与 #13 已定的**多 change 同 PR** 边界**完全一致**（同一条 `code_hits` 判定），不新增对外约束。

**甲的论点（也要如实呈给用户）**：本仓两条既有 stage 门里，**grill 那条是无条件的**；`templates/grill.md`
把对抗轮写成**对每个 change 都必跑**；无条件的门**不能被「这次不写代码」绕开**。

⚠️ **两种都要写明是对先例的偏离**（先例挂归档点 + 三重豁免，本仓无对应物）——不许写「照 asterwynd 办」。

### D3 **verdict 文本不参与判定**（甲）/ 解析最终裁定 = PASS（乙）—— **Q2**

- **甲（推荐）**：只要求证据**存在**。先例同口径（asterwynd 注释明写「存在性即可」）；
  与 #13 已裁定的 building 口径**一致**（那次 Q1 也选甲）——**同一份设计不该对两个 stage 用两套口径**。
- 乙的代价（与 #13 分析同构，且**更重**——对抗报告轮次更多）：须先规定**机器可读的最终裁定形态**
  （`## 第 N 轮` / `- 裁定:` / `# 第 N 轮（RN）` 三种记法并存，实测）、**回填本仓 5 份历史
  `grill-adversarial.md`**、并给 `templates/grill.md:131` 的「到顶交人判断」找一条出路
  （否则等于取消该条款）。

**诚实边界（必须写进 README / spec / PR 正文）**：选甲 ⇒ 「**跑一轮、拿到 `CHANGES_REQUESTED`、
什么都不修**」也**能过**（文件存在即满足）。理由：非 PASS 收尾本身是**规定行为**（轮数封顶 → 交人判断），
机械区分不了「封顶后交人」与「跑一轮就收工」。这是本门禁的**已知上限**，不是实现缺陷。

### D4 **不改 `guard`**

- 先例一致（asterwynd 守卫侧 0 命中）；本仓 `guard` 是「防遗忘」、可绕过，锚在 CI。
- 也**避免**把「manifest 必须在写码前产出」变成守卫条件：那会要求实现前就把 `grill-adversarial.manifest.json` 建好，
  与「停轮确认 → 才写码」的时序纠缠（本 change 的 E0/E1 已按「先放行、定稿后重跑」处理，无须再加一层）。
- ⚠️ **诚实的缺口**（须在 spec 写明，别让读者以为守卫已覆盖）：`templates/grill.md` 的硬约束 #2
  （对抗验证收敛）在**本地守卫侧仍无强制**——`guard` 只查 grill 决策记录。这是**刻意的**（守卫可绕过，投入产出不成比例），
  但**是缺口**，Q3 交用户确认是否接受。

### D5 触发面 = 「**本次 diff 触及的每个 change**」（与 #13 完全一致）

多 change 同 PR 时**每个** change 都被要求（#13 已定的「一个 PR 推进一个 change」前提），
**不加** `adversarial_exempt_changes` 之类的豁免名单（= 新的绕过面）。

### D6 revision 绑定：**不新写**

`contract._check_git_span` 已保证「manifest 的 `head_sha` 之后不许有**非证据**改动」⇒
与「必须存在」合起来就是「**对抗轮之后又改 design / code ⇒ 必须重跑**」。
`design.md` **不在** `stale_exempt_paths` 里（豁免只有 `.witnessloop/**`、`<change>/reviews/**`、
事件文件、`archive/**`）⇒ 收敛后再改 `design.md` 会让**两份** manifest 一起 stale（既有用例可复现）。

### D7 文档 / 行为变更

- `README.md`：**对**接入方**是行为变更**（依 Q1 的触发面写具体条件 + 缺它的红文案 + 「verdict 不参与判定」的诚实边界）。
- `docs/gate.md`：§6（红项清单）、§8（读点/门禁表加一行）、§9 同族新增小节（对抗轮门禁的触发与判据）。
- `templates/grill.md`：在「产物」小节后补一句「这条现在被 `check` 机械要求（触发面与豁免）」。

### D8 非目标（写进 spec 的边界声明）

不加 archive 门禁；不引入 `ChangeType`；不解析 verdict；不动 `guard`；不做「`require_change_for` 为空时 warning」
（#13 的 Q4 已裁定「不改」）；不签名 / 不防伪造。

## 3. 接线点（实现清单）

- `src/witnessloop/constants.py`：`DEFAULT_GRILL_ADVERSARIAL_STAGE = "grill-adversarial"`（与 `DEFAULT_GRILL_STAGE` /
  `DEFAULT_BUILDING_STAGE` 并列）。
- `src/witnessloop/policy.py`：`Policy.grill_adversarial_stage` + `from_doc()` 回落 + `default_policy_doc()` 写入 `evidence.grill_adversarial_stage`。
- `src/witnessloop/checkcmd.py`：change 循环里加一条（触发面见 Q1），文案点明「设计阶段对抗验证轮（grill → 停轮之前的证伪环节）」。
- `tests/`：`tests/helpers.py` 的 `commit_evidence` 默认 stages 补 `grill-adversarial`；
  新增 `tests/test_grill_adversarial_gate.py`（与 `test_building_gate.py` 同构）；
  按实测清单改 4 条自造证据集的既有用例。
- `docs/gate.md` / `README.md` / `templates/grill.md`（D7）。

## 4. 风险

1. **R1（低，已实测）**：自伤面——本仓 5 个 active change **都有**对抗轮 manifest ⇒ 0 条自伤；
   测试侧的改动量已实测（甲 17 / 乙 4）。**不写估计值**。
2. **R2（中）**：触发条件若选错（甲 无条件），**in-flight / 纯文档 change** 会被误伤（adopter 侧新红类）。
   ⇒ Q1 必须给用户**带具体场景**的两个例子。
3. **R3（中，诚实上限）**：「**有一份 manifest**」≠「**真跑了一次独立 run**」。
   兜底 id 路径下 `reviewer_run_id ≠ author_run_id` **结构性恒真**（`templates/grill.md` 的「怎么取 run id」已写明）
   ⇒ 一个 agent 自造 manifest 即可满足。与 grill / building 同一边界（**防漂移不防伪造**）。
4. **R4（中，诚实的机制空洞）**：**无法机械证明「对抗轮发生在 grill 之后、且针对同一份 design」**。
   revision 绑定只保证「两份证据都记在最终 revision 之前/之上」，而 `design.md` 的**内容**未被任何
   manifest 哈希绑定（`constants.HASHED_ARTIFACTS` 只有 `tasks.md` / `specs`）。
   ⇒ 边界写进 spec：本门禁保证的是**「该 change 存在一份可绑定的对抗轮证据」**，不是「它证伪了这份 design」。
   不为此新增 `design_hash`（那会改动 manifest schema = 另一次 change）。
5. **R5（低）**：`require_change_for = []`（或没覆盖真实代码路径）时，选乙 ⇒ 本门禁与 building、`_require_change`
   **一起静默失效**（#13 R5 已实测；本 change 把它从 2 条判定扩到 3 条）⇒ 在 spec / `docs/gate.md §2` 保持既有声明即可。
6. **R6（低，方向性）**：本 change **自己**落了实现 ⇒ 它的 PR 会被自己新增的门要求 `stage=grill-adversarial`
   （流程上本来就会产），且**清单文件在实现之后重跑**（E1）否则 stale——E0/E1 已按此设计，无自锁。

## 5. 测试策略（TDD）

- **先红**：
  1. 触发条件满足 + 只有 grill / building 证据 ⇒ `check` 红，文案点名 `stage=grill-adversarial`；
  2. 补齐该 stage 的 manifest（+ 报告）⇒ 绿；
  3. `stage` 拼错（如 `grill-adversariall`）⇒ 文案**点名现有 stage**；
  4. 未触发的情形（依 Q1：甲=不适用；乙=纯文档 / 只动 change 目录）⇒ **不要求**；
  5. 对抗轮之后再改 `design.md` ⇒ **stale 红**（既有能力加回归钉住，与 building 那条同构）；
  6. policy 轴可覆写（`evidence.grill_adversarial_stage`）——**必须**有用例（#13 的 M11：覆写轴无测试被变异检查逃逸）。
- **回归**：全量 `uv run pytest -q` 绿；本仓自己的 5 个 change 目录判合格。
- **配方纪律**（照 #12 的教训）：证据集用 `helpers.write_review(stage=..., report_rel=...)` 造，
  **不要**手写 manifest（`report_hash`/`tasks_hash` 极易不一致）。

## 6. 文档影响

`docs/gate.md`（§6/§8/§9）、`README.md`（对**接入方**的行为变更）、`templates/grill.md`（D7）。
本 change **不改** `openspec/changes/` 下其他 change 目录的**非证据文件**（会让它们的 manifest 判 stale —— #12 的教训）。

## 7. Pre-Implementation Review

（grill + 对抗验证收敛后回填：已确认决策 / 必须修改（已整合）/ Code-Resolved 结论。）

## 8. Open Questions（停轮待用户确认）

- **Q1 触发条件选甲还是乙？**
  - **甲**：**每个**被触及的 change 都要（与 grill 那条同形）。
    例：你提一个 PR，只新增 `openspec/changes/foo/proposal.md`（设计还没开始 grill）——
    今天就已经红（缺 `stage=grill`）；选甲 ⇒ 此后它**还要**有 `grill-adversarial` 证据才绿。
    实测代价：**17 条**既有用例要改（含 6 条孤儿报告用例）。
  - **乙（推荐）**：**本次 diff 落了实现**才要（与 building 那条同形）。
    例：同一个「只加 proposal.md」的 PR ⇒ **不受影响**；而「改了 `src/x.py` + 一个 change 目录」的 PR ⇒
    要求 `stage=grill-adversarial` 与 `stage=building` **两份**证据。实测代价：**4 条**既有用例要改。
  - ➡️ **推荐乙**（理由 D2 四条）。
- **Q2 verdict 文本是否机械判 `PASS`？**
  - **甲（推荐）**：不解析。例：对抗报告最终写着 `CHANGES_REQUESTED`（三轮封顶后交人判断）⇒ **照样绿**
    （与 building 那条已定口径一致；asterwynd 注释明写「存在性即可」）。
  - **乙**：要求最终裁定 = `PASS`。例：同一份「三轮封顶、交人判断后照合」的报告 ⇒ **红**，
    除非再规定一种 `reviews/<stage>-override.md`（被 manifest 绑定）的人工覆盖形态。
    代价：**规范多轮格式 + 回填 5 份历史报告 + 给「封顶交人」找出路**（`templates/grill.md:131` 的条款不能被无声取消）。
- **Q3 是否接受「本地守卫不要求对抗轮证据」这个缺口？**（D4）
  - **推荐**：接受（只改 `check`）。例：目标仓没装 CC plugin ⇒ 守卫本来就不生效，加了也拦不住；
    真正的锚是 CI required check。若要求守卫覆盖，`guard` 会新增一条写码前条件，须单独立项。
- **Q4 对**既有接入方**的行为变更怎么落？**（照 #13 Q3 的口径）
  - **推荐**：**只写文档**（README + `docs/gate.md`）+ 明确「对**接入方**是行为变更」，**不加过渡开关**（开关 = 静默绕过面）。
