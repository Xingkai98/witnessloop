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
test_renaming_with_an_event_is_allowed` 1 条）；甲 的 17 条里含 `test_orphan_reports.py` **8 条**
（⚠️ 原稿写「6 条」**漏算** `test_build_then_check_agree_on_noncanonical_report_paths` 的 **4 个参数化项**
——grill 实测订正）、`test_manifest_build.py` / `test_acceptance.py` 等。
⚠️ 原稿那句「实测清单见 tasks B3 的实测记录」是**悬空引用**（`tasks.md` 的「实测记录（实现期）」当时为空），
已删——清单**不在这两份文件里维护**，权威出处是 `reviews/grill-adversarial.md` 的 **N-1**
（`grill-review.md` 的「事实 1–3」只覆盖其中 9 条，**不足以**当权威出处——这正是对抗轮 R1 的阻塞项 B-1）。

⚠️ **甲 还有一条原稿没写全的代价（grill 实测发现，对抗轮 R1 订正措辞）**：甲会让
`tests/test_building_gate.py::test_not_required_when_only_the_change_dir_changed` 变红——它钉的正是
「提案期 / 纯 change 目录改动**不误伤**」。
**但甲不是「技术上做不到」**（对抗轮实测）：给它补一份**空正文**的 `grill-adversarial` 证据即可转绿
（空报告合法，见 D3 的诚实边界）。⇒ 准确的说法是：**甲的触发面没有「不触发」这个分支，于是这条门在
「只动 change 目录」的场景下只能被「空气」满足**——门形同虚设。而乙保留了「提案期不受这道门约束」这一**可表达**的语义。
（这一措辞是给用户拍板 Q1 用的，别用「甲必须重写这条语义钉子 ⇒ 不可接受」的说法。）

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
- 乙的代价（grill 实测，**比原稿的估计更重**）：5 份历史报告共 **16 轮**——**轮头两级**
  （`# 第 N 轮（RN）` 3 份 / `## 第 N 轮对抗验证` 2 份）且**第 1 轮 5 份全无轮头**；
  **裁定载体两种**（`## Verdict` 小节 3 份 / `- 裁定:` bullet 2 份）；**裁定文本三种**写法；
  且 **5 份的中间轮都含 `CHANGES_REQUESTED`**（最终轮才 `PASS`）⇒「最终裁定 = `PASS`」得先定义
  **轮序**、再定义**载体**，两者都**没有**统一形态。
- ⚠️ **回填的隐藏代价（原稿没写 · grill 实测）**：改**别的** change 的历史报告会让那份 manifest 的
  `report_hash` 不匹配 ⇒ 动了某 change 的对抗报告之后，任何**触及该 change 目录**的 PR 都会红
  `report_hash 不匹配`。「回填 5 份」不是免费文案，而是给 5 个既有 change **各埋一颗地雷**。
- 还要给 `templates/grill.md:131` 的「到顶交人判断」找一条出路（否则等于取消该条款）。

**诚实边界（必须写进 README / spec / PR 正文）**：选甲 ⇒ 「**跑一轮、拿到 `CHANGES_REQUESTED`、
什么都不修**」也**能过**（文件存在即满足）。理由：非 PASS 收尾本身是**规定行为**（轮数封顶 → 交人判断），
机械区分不了「封顶后交人」与「跑一轮就收工」。这是本门禁的**已知上限**，不是实现缺陷。

⚠️ **再加一条（对抗轮 R1 实测发现，原稿三条边界都没写）**：判据是 `verify_body=False` ⇒
**报告正文**不校验——**零字节 / 只有空白的 `reviews/grill-adversarial.md` 同样合格**（实测 + 合法 manifest ⇒ `check` 退 **0**）。
不写清这句，README 的「证据存在即满足」会被读成「至少有一份**有内容**的报告」。

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
事件文件、`archive/**`）⇒ 收敛后再改 `design.md` 会让该 change 的**每一份** manifest 各报一条 stale
（三份证据时实测 **3 条**「审阅的是旧 revision」；原稿写「两份」不精确）。
⚠️ **条数 ≡ 该 change 目录里 manifest 的份数**（对抗轮 R1 做了 1/2/3 三组对照：1 份 ⇒ 1 条、2 份 ⇒ 2 条、
3 份 ⇒ 3 条）——`_check_git_span` 是**逐 manifest** 判的，别把 3 当常量。
⚠️ 但**只对落在 manifest 的 `head_sha` 之后**的改动成立——改动落在 `head_sha` **之前**（而对抗轮跑在更早）
则**完全无痕**（见 R4）。

### D7 文档 / 行为变更

- `README.md`：**对**接入方**是行为变更**——写**具体触发条件**（含「落了实现 = 命中 `require_change_for`，
  本仓**含** `templates/**` / `plugin/**`」，见 R9）+ 缺它的红文案 + **三条诚实边界并列写死**
  （① verdict 不参与判定；② 只保证证据**存在**并绑在最终 revision，**不保证**对抗轮发生在写码之前 —— R-new-1；
  ③ **报告正文不校验——空文件亦合格** —— 对抗轮 R1 的 N-5）。
- `docs/gate.md`：§6（红项清单）、§8（读点/门禁表加一行）、§9 同族新增小节（触发面 + 判据 + **同三条边界**）。
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
4. **R4（中，诚实的机制空洞，grill 已实测）**：**无法机械证明「对抗轮发生在 grill 之后、且针对同一份 design」**。
   - `design.md` 的**内容**未被任何 manifest 哈希绑定（`constants.HASHED_ARTIFACTS` = `tasks.md` / `specs`，
     `constants.py:64-67`）。实测：**在证据提交之前**把 `design.md` 整段换掉再落证据 ⇒ `check` 退 0。
     ⚠️ **时序要写清**（对抗轮 R1 订正了 grill 原话）：同一时序下改 `specs/` **也退 0**——因为
     `write_review` 是对**当时**的 `specs` 取哈希，两侧天然一致。要看到 `spec_hash 不匹配`，必须
     **先产证据、后改** `specs/`。
   - `_check_git_span`（`contract.py:272-354`）只判「manifest 的 `head_sha` 之后没有非证据改动」，
     **两份 manifest 的先后不做比较** ⇒ 门禁保证的是「存在一份绑定在最终 revision 的对抗证据」，
     不是「对抗轮发生在写码之前」。⇒ 文案层面极易被读成「写码前必须收敛」（grill R-new-1），
     故 `docs/gate.md §9` 与 README **必须并列写死三条边界**：① verdict 不参与判定；
     ② 本门禁只保证证据**存在**并绑在最终 revision，**不保证**对抗轮发生在写码之前；
     ③ **报告正文不校验——空文件亦合格**（判据止于 `verify_body=False`，实测零字节报告 + 合法 manifest ⇒ `check` 退 0）。
   - **不**为此新增 `design_hash`（那要改 manifest schema = 另一次 change）。
     ⚠️ 代价：本 change **自己**必然踩这个洞（依 Q5 处置）。
5. **R5（低）**：`require_change_for = []`（或没覆盖真实代码路径）时，选乙 ⇒ 本门禁与 building、`_require_change`
   **一起静默失效**（#13 R5 已实测；本 change 把它从 2 条判定扩到 3 条）⇒ 在 spec / `docs/gate.md §2` 保持既有声明即可。
6. **R6（低，方向性）**：本 change **自己**落了实现 ⇒ 它的 PR 会被自己新增的门要求 `stage=grill-adversarial`
   （流程上本来就会产），且**清单文件在实现之后重跑**（E1）否则 stale——E0/E1 已按此设计，无自锁
   （grill 已做全链路模拟：乙补丁 + 实现提交 + 三份报告/三份 manifest 作证据提交 ⇒ `check` 退 **0**）。
7. **R7（低，但本次已踩到 · 实测配方）**：**worktree 的 `.git` 是文件**（`gitdir: <主仓>/.git/worktrees/<id>`）
   ⇒ `cp -a` 出的实验副本**共用原 worktree 的 gitdir 与 index**：副本里的 `git checkout -b` / `git commit`
   会**落到被审 worktree**（本次 grill 因此误切了分支、落了两个游离提交，已完整复原）。
   ⇒ 实测配方必须写明：副本里做**任何 git 操作**之前先 `rm -f .git && git init -q && git add -A && git commit -qm base`。
   ⚠️ **还要 `rm -rf .venv && uv sync`**（对抗轮 R1 踩到）：`cp -a` 会连 `.venv` 一起复制，而 editable 安装的
   `.pth` 里写的是**源副本的绝对路径** ⇒ 在副本里 `uv run pytest` 会**测到源副本的代码**
   （它第一轮四组对照因此全得 `2 failed / 418 passed`，与 churn 表完全不符）。pytest 内部用 `tmp_path` 的独立仓，不受此影响。
8. **R8（低，可诊断性）**：`tests/helpers.py` 的 `write_review` 对 `grill-adversarial` 默认产
   `reviews/grill-adversarial-review.md`，而本仓 5 份真实证据都在 `reviews/grill-adversarial.md`（实测）
   ⇒ 不影响判定，但会让孤儿报告类用例更难读。**B1 顺手把默认报告名对齐真实约定**。
9. **R9（低，表述）**：本仓 `.witnessloop/policy.json` 的 `require_change_for` 含 `templates/**` 与 `plugin/**`
   ⇒ 乙口径下「**只改模板**」也算「落了实现」（对**本仓**这是对的：模板就是流程本体）。
   README 写触发条件时必须写明「落了实现 = 命中 `require_change_for`（本仓**含**模板 / 插件目录）」。

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
  **不要**手写 manifest（`report_hash`/`tasks_hash` 极易不一致）；`grill-adversarial` 的默认报告名
  按真实约定取 `reviews/grill-adversarial.md`（R8）。
- **配套的 spec 修订（实现前必须落地）**：`spec.md` 里**所有挂 Q1/Q2 待定标记的段落**都要按定案替换
  ——对抗轮 R1 指出「两处」是**下限不是全集**（`spec.md` 里至少 5 处挂标记）。至少含：
  1. 「未触发时不误伤」Scenario 的 `Given` 写成「本次 diff **不满足**触发条件」= **循环定义** ⇒
     定案后替换成具体条件（乙 = 只改文档 / 只动 change 目录）；
  2. `spec.md` 的**触发条件**本身（正文 + Scenario 的 `Given`）；
  3. **「多 change 同 PR」Scenario 的 `Given`**（对抗轮补充）——现写「另一个 change 自身**无实现**」，
     这在**乙**口径下**永远构造不出来**（无实现的 change 目录不可能满足 `code_hits`）⇒ 该 Scenario 现在
     编码的是**甲**的语义，须按定案重写；
  4. 若 Q2 选乙：`Requirement: verdict 文本不参与判定（选甲时）` 整节要换掉。

## 6. 文档影响

`docs/gate.md`（§6/§8/§9）、`README.md`（对**接入方**的行为变更）、`templates/grill.md`（D7）。
本 change **不改** `openspec/changes/` 下其他 change 目录的**非证据文件**（会让它们的 manifest 判 stale —— #12 的教训）。

## 7. Pre-Implementation Review

**已确认决策（grill 独立复现 · 来源 `grill-reviewer-grill-adversarial-gate-2026-10-12T141224Z`）**：
D1 证据形态走 `stage=grill-adversarial` 的 manifest（裸报告实测被**孤儿规则**判红，退 1）✅；
D2 的 churn 表**四次实测全部复现**（420 基线；甲 30→17；乙 6→4）✅；
D6「revision 绑定那一半已经在」✅（实测：三份证据齐备 `check` 退 0 → 改 `design.md` 一行 → 退 1、
**3 条** stale——⚠️ **条数 ≡ manifest 份数**，见 D6，别当常量）；
R1（0 自伤：本仓**除本 change 外的** 5 个 active change **都**有对抗轮 manifest——第 6 个是本 change 自己，
预期尚未有）与 R6（无自锁：全链路模拟 `check` 退 0）✅；
`§1.1` 表里 `checkcmd.py:83-88/91-98/125-145/148-206`、`contract.py:185-219`、`evidence.py:172-235/238-257`
**行号全对** ✅；asterwynd 先例四条（唯一检查点在 `:1629-1639`、`DESIGN_TYPES`/docs 豁免、
「存在性即可」注释、`workflow_guard.py` **0** 命中）✅。

**被 grill 证伪并已修正（回写到上文对应小节）**：
1. `test_orphan_reports.py` 的失败项是 **8**（漏算 4 个参数化项），原稿写 6 ⇒ 已订正（D2）。
2. `tests/test_invariants.py` **不该**出现在甲口径的清单里（补 helpers 后它不失败）⇒ 已从 tasks B3 删除。
3. tasks 清单**漏了** `test_building_gate.py::test_not_required_when_only_the_change_dir_changed`
   ⇒ 甲会让它变红（**「必须重写」这一措辞已被对抗轮 R1 订正**——它可以靠空正文证据转绿，见 D2/Q1）。
4. `design.md` 里「见 tasks B3 的实测记录」是**悬空引用**（该节当时为空）⇒ 已删，改指 `grill-review.md`。
5. D6 写「两份 manifest stale」不精确 ⇒ 实测 **3 条**（每份 manifest 一条，**条数 ≡ manifest 份数**），已订正。
6. D3 的「多轮记法不统一」**属实且更糟**：5 份 **16 轮**、轮头两级、第 1 轮全无轮头、载体两种、文本三种，
   且每份都含中间轮 `CHANGES_REQUESTED`；**并新发现回填的隐藏代价**（改别的 change 的历史报告 ⇒
   `report_hash` 不匹配）⇒ 已写进 D3。

**对抗验证 R1（`CHANGES_REQUESTED` → 已整合 · 来源 `adversarial-reviewer-grill-adversarial-gate-r1-2026-10-12T143037Z`）**：
- **独立复现**：基线 420；churn 四组（30/390、6/414、17/403、4/416）**逐字命中**；`test_orphan_reports` 甲下 8 项；
  stale 条数 ≡ manifest 份数；asterwynd 唯一检查点在归档点；老 policy 缺新轴 ⇒ 回落退 0；A2 加轴**无连带**（420 passed）。
- **阻塞项 B-1（本 change 的下游落地漏点）**：tasks B3 声称「再改 13 条」却只枚举 **9** 条，且它引的「权威清单」
  （`grill-review.md` 事实 1–3）也覆盖不到漏掉的 4 条 ⇒ 实现者无从发现。**已按 R1 的实测清单改写 tasks B3。**
- **阻塞项 B-2**：E0b「重跑一次对抗轮」**没规定第二份报告怎么落盘**（另起文件名 ⇒ 孤儿报告；必须**原地覆盖**），
  且「一次」不够——它是**循环**（修 → 再审，直到 PASS 或封顶）。**已改写 tasks E0b。**
- **新发现（已整合）**：空正文报告也合格（→ 第三条诚实边界）；`spec.md` 的「多 change 同 PR」Scenario 的 `Given`
  在**乙**口径下永远构造不出来（→ tasks B5 扩成三处）；「两处缺口」实为下限（→ 改成「所有挂 Q1/Q2 待定标记的段落」）；
  `.venv` 随 `cp -a` 复制会让副本测到**别的副本**的代码（→ R7 配方）。

**Code-Resolved（已定案，不进 Open Questions）**：`grep -rn "grill-adversarial" src/` = 0 命中 ✅；
R4 实测（**证据之前**整体替换 `design.md` ⇒ `check` 退 0；要看到 `spec_hash 不匹配` 必须**先产证据、后改** `specs/`）✅；
`design.md` 不在 `stale_exempt_paths` ✅；孤儿规则会先拦下裸报告 ✅；
asterwynd 无第二个检查点 ✅；`spec.md` 与 design 的 D1..D8 逐条对应，缺口清单见 §5
（**不是定数**——须替换「所有挂 Q1/Q2 待定标记的段落」）。

**对抗验证 R2（**PASS** → 已收口 · 来源 `adversarial-reviewer-grill-adversarial-gate-r1-2026-10-12T143037Z`）**：
R1 两条阻塞项**逐条复核已关掉**（B-1 的 13 条清单逐条点名完整；B-2 的 E0b 用三组机制探针证实：
**追加 + 重建 manifest ⇒ 退 0**、只追加不重建 ⇒ `report_hash 不匹配`、另起文件名 ⇒ 孤儿报告）。
R2 指出 4 条**非阻塞**遗留，全部是「`design.md` 自己的摘要/引用行没跟上它自己的新正文」
（:87 权威出处、:202 两条边界、:291 两处缺口、:202/§7 的 spec_hash 时序）——**已全部清掉**。
⚠️ 这条模式与本仓「修正只落一份 artifact」**同源，只是缩小到了同一份文件内部**，值得记住。

## 8. Open Questions（停轮待用户确认）

- **Q1 触发条件选甲还是乙？**
  - **甲**：**每个**被触及的 change 都要（与 grill 那条同形）。
    例：你提一个 PR，只新增 `openspec/changes/foo/proposal.md`（设计还没开始 grill）——
    今天就已经红（缺 `stage=grill`）；选甲 ⇒ 此后它**还要**有 `grill-adversarial` 证据才绿。
    实测代价：**17 条**既有用例要改（含 8 个 `test_orphan_reports` 项）；**且**其中
    `test_building_gate.py::test_not_required_when_only_the_change_dir_changed` 钉的正是「提案期不误伤」
    ⇒ 甲口径下这条门在「只动 change 目录」的场景**只能被空报告满足**（对抗轮 R1 订正的措辞，见 D2）。
  - **乙（推荐）**：**本次 diff 落了实现**才要（与 building 那条同形）。
    例：同一个「只加 proposal.md」的 PR ⇒ **不受影响**；而「改了 `src/x.py` + 一个 change 目录」的 PR ⇒
    要求 `stage=grill-adversarial` 与 `stage=building` **两份**证据。实测代价：**4 条**既有用例要改。
  - **乙的绕过面（grill 实测结论）**：**不存在**「先提纯 change 的 PR、之后单独提改码的 PR」的永逸绕过——
    后一个 PR 自己的 diff 就触及 `require_change_for`，届时仍要对抗轮证据。
  - ➡️ **推荐乙**（理由 D2 四条）。
- **Q2 verdict 文本是否机械判 `PASS`？**
  - **甲（推荐）**：不解析。例：对抗报告最终写着 `CHANGES_REQUESTED`（三轮封顶后交人判断）⇒ **照样绿**
    （与 building 那条已定口径一致；asterwynd 注释明写「存在性即可」）。
  - **乙**：要求最终裁定 = `PASS`。例：同一份「三轮封顶、交人判断后照合」的报告 ⇒ **红**，
    除非再规定一种 `reviews/<stage>-override.md`（被 manifest 绑定）的人工覆盖形态。
    实测代价（比原稿估计更重）：5 份报告 **16 轮**、轮序/载体/文本**三处都不统一**，
    且**回填会撞 `report_hash`**（改别人的历史报告 ⇒ 那份 change 下次被触及就红）⇒ 给 5 个 change 各埋一颗地雷。
    **对抗轮 R1 新增一条连带后果**：选乙 ⇒ E0b 的重跑**必须重跑到 `PASS`**，而对抗轮的常态产出恰恰是
    `CHANGES_REQUESTED`（5 份历史报告**每份**都含中间轮 CR）⇒ 乙口径下**必须同时**规定
    `reviews/<stage>-override.md` 之类的人工覆盖形态，否则 `templates/grill.md:131` 的「到顶交人」被**无声取消**。
- **Q3 是否接受「本地守卫不要求对抗轮证据」这个缺口？**（D4）
  - **推荐**：接受（只改 `check`）。例：目标仓没装 CC plugin ⇒ 守卫本来就不生效，加了也拦不住；
    真正的锚是 CI required check。**grill 补了一条更硬的理由**：`guard` 只覆盖 `Write|Edit`，
    `echo > src/x.py` 或 `WITNESSLOOP_SKIP_GUARD=1` 即可绕过 ⇒ 补上这条**不会消除缺口**，
    只会在写码前多加一条可绕过、且与「停轮确认 → 才写码」时序纠缠的硬条件。
- **Q4 对**既有接入方**的行为变更怎么落？**（照 #13 Q3 的口径）
  - **推荐**：**只写文档**（README + `docs/gate.md`）+ 明确「对**接入方**是行为变更」，**不加过渡开关**（开关 = 静默绕过面）。
- **Q5（grill 新增 · 本 change 自己的流程）R4 的机制空洞在本 change 身上**必然发生**，要不要在本 change 内处置？**
  - **事实**：`templates/grill.md` 要求对抗轮在**停轮之前**跑完，而本 change 的 `design.md` / `spec.md`
    要**停轮拿到 Q1..Q4 之后**才定稿（tasks E0）⇒ 本 change 的 `grill-adversarial.md` 必然是对
    **一份后来的稿子**的证伪；manifest 在定稿后重跑 ⇒ 门禁「绿」，而报告针对的是被取代的设计。
    例：若 Q1 定案为**甲** ⇒ `spec.md` 的触发条件由乙改写为「每个被触及的 change」、
    `checkcmd.py` 的判定从 `if code_hits:` 块挪到 grill 那条旁边、`tasks.md` 的 4 条变 17 条——
    而对抗轮原稿逐条对抗的正是「乙的四条理由」（还实测验过乙的 churn）⇒ **该报告整节作废**，但 manifest 照样绿。
  - ➡️ **推荐答案**：**在 E0 与 E1 之间显式加一步**——Q1..Q4 定案、`spec.md`/`design.md` 改完之后，
    **重跑一次设计对抗轮**（可只针对被定案改动的部分），再落 `stage=grill-adversarial` 证据；
    **不**在本 change 内新增 `design_hash`（那要改 manifest schema = 另一次 change，且 R4 已声明为已知上限）。
