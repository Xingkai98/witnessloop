# Grill 对抗验证: building-review-gate

## Reviewer
- run id: grill-adversarial-reviewer-building-review-gate-2026-10-12
- 时间: 2026-10-12T07:10:29Z
- 方式: 独立零记忆审阅者，**默认上一轮（grill）结论有错**，逐条证伪。所有 `文件:行号` 自己打开；
  能实测的在本 worktree 打补丁跑（**已还原**：`git status --porcelain` = 0 行，未 commit），
  其余在 `/tmp` 造副本。

## Verdict
CHANGES_REQUESTED

阻塞项**只有一条**，且很小：design D1 **明文要求**「在 spec 里加 Scenario 把多 change 边界钉死」，
而 `specs/building-evidence/spec.md` **没有这条 Scenario**，同时 tasks B9 要求为这条边界写用例
⇒ design（已收敛的定案）与 spec（规范增量）不一致，grill 自评**最高**的风险（R-new-1「高」）
**在规范件里没有被钉住**。change 的**技术核心是站得住的**（见下）：自伤面 0 条**独立复现成功**、
无自锁、门禁真的接进了判定路径、回归红线成立。

## 逐条对抗结论

### 1. grill D-D「自伤面 0 条」→ **站得住**（我独立复现，未能证伪）
这条是本 change 最关键的经验事实（design D6、tasks C 段全押在它上面），我按 design §3 **自己写了一份补丁**
（不是复用它的），并**先证明它真的把 building 接进了 `checkcmd` 的判定路径**（不是只改常量）：

- 接线证明（e2e，真跑 CLI）：改 `src/app.py` + 只有 grill 证据 ⇒ **exit 1**，文案
  `openspec/changes/add-x：无 stage=building 的 manifest（现有 stage：grill）`；补上 building 证据 ⇒ **exit 0**；
  `--stage buildings` ⇒ **exit 1** 且点名 `现有 stage：buildings, grill`；只改 `docs/` `tests/` ⇒ **exit 0**。
- 全量测试：**404 passed**，与基线 **404 passed** 逐条同数，**0 条新增失败**。

⇒ 我尝试证伪而失败。**grill 的 D-D 与 design D6/R1 的改写是可信的**；
tasks C1 缩为「确认无需改动」是对的，原稿「一批既有用例会变红」确属高估。
（附注：`/home/happy/.local/bin/witnessloop` 是本机**另一个 uv-tool 安装**，**不含** worktree 的补丁。
若用手工 CLI 复现，必须走 `uv run witnessloop` / `uv run pytest`，否则量到的永远是**未打补丁**的行为——
我第一轮就踩了这个坑，S5 假绿。）

### 2. grill Q2 的定案 → **部分被证伪**（前提不成立 + 误伤属实）
**(a) 「一 PR 一 change」在本仓**并未**已经成立**（实测 `multi2.py`）：单一内容提交
（`impl-a` 的 `src/**` + `b-doc` 的 change 目录）+ 单一证据提交 ⇒ **未打补丁时 `check` exit=0（绿）**。
所以多 change 同 PR **今天是可行的**。design D1 把该前提说成「与既有的『内容/证据分属两提交、
单提交 PR 不被支持』（`docs/gate.md:172-177`）**同族**」**不准确**：既有约束约束的是**提交顺序**，
D1 新引入的约束是**变更数量**，两者不同族。⇒ 这是本 change **新造**的约束，不是「把既有前提显式化」。

**(b) 确会误伤真实工作流**（实测 `multi2.py`，同一场景打上补丁）：`check` ⇒ **exit 1**，唯一 finding =
`openspec/changes/b-doc：无 stage=building 的 manifest（现有 stage：grill）`。
即「一个 PR 改代码 + 顺带一个纯文档 change」**从绿变红**。这是**除**「改了代码没跑 review-loop」之外
**第二条**对**接入方**的行为变更——而 tasks D3 / design D5 的「行为变更」声明**只覆盖第一条**。
（另测 `multi.py`：若两个 change 的证据**交错**提交，未打补丁时**已经** exit=1（`_check_git_span` 判 stale），
补丁后只是**多一条** b-doc；说明「同 PR 多 change」在交错提交下**今天就已经被既有机制挡住**。）

**(c) 更好的第三条路**：grill 已考虑 `building_exempt_changes` 并因「新绕过面」否决，**我同意**——
witnessloop 无 change↔code 映射，任何「这段代码属于哪个 change」的判据都要么**新造第二套
「什么算代码」的口径**（正是本仓忌惮的），要么退回**自声明**（`_tasks_all_complete` 那一类，
design D1 已正确否决）。⇒ Q2 的**方向对**，**缺的只是把边界写进 spec**（见「必须修改」1）。

### 3. Q1 的推荐（甲）是否回应 issue #13 → **站得住**（比任务书的框架更贴合 issue 原文）
我去读了 issue #13 原文（`gh issue view 13`）。它的标题是
**「「实现后独立审阅」不是硬门：跳过 review-loop 的 PR 照样绿」**——**不是**「PASS 不是硬门」；
需求节逐字写：「本次 diff **落了实现**（触及 `policy.require_change_for` 下的路径）时，
被触及的 change **必须**有一份 `stage=building` 的审阅证据（manifest + 其绑定的报告），否则 `check` 红」。
⇒ 甲（只机械「跑没跑」、**不解析** verdict 文本）**正是 issue #13 的字面需求**，严格说**不是「部分修复」**。
issue 自己还明写：「『要不要机械判 PASS 文本』是本 change 的一个 **Open Question**」——即 issue **有意**
把该问题留给停轮，design Q1 正是接住了它。

**明确判断：这一条不阻塞。** 但相对**任务书**「PASS 不是硬门」这个（超出 issue 原文的）框架，
甲确实**只机械化了「跑没跑」、不保证结论是 PASS**：实测一份正文只有 `PASS\n\n审阅通过。` 的 building
报告即可通过（因为 design D2 明写「**不**额外要求报告正文结构」；对 building 而言**连 grill 式的正文校验都没有**）。
⇒ 建议 proposal「验收」节 + 关 issue 的说明**显式写明**这条边界，别让读者以为 PASS 变硬门了。
design D3（甲案「**诚实边界**」）与 R6 已写明，**proposal 尚未**。

### 4. R6「兜底路径下 `reviewer_run_id ≠ author_run_id` 结构性恒真」→ **站得住**
- 文档属实：`docs/gate.md:121-123` 逐字就是那条边界（「兜底路径下两角色 id 结构性不同…**不**等于
  『挡忘了另开 run』；也**不挡蓄意伪造**」）。
- 实现属实：`agentenv.generate_run_id`（`agentenv.py:58-63`）= `<stage>-<role>-<anchor>`，**role 编进 id**；
  `manifestcmd.py:122-124` 只在两值**相等**时拒。实测（无环境变量）：`building-reviewer-<change>-<sha>`
  vs `building-author-<change>-<sha>`，**相等？False** ⇒ 一个 agent 自造 manifest **确能**过这道校验。
- **影响评估未被低估**：这与 `contract.py:255-264`、`docs/gate.md §7` 的仓库级边界
  （防漂移不防伪造，由 `test_acceptance.py::test_f2_handwritten_allow_event_is_not_blocked` 钉成契约）一致；
  真锚是 branch protection + required check，design 也说清了。
- **补一点 grill 未强调的**：**building 这一 stage 连正文都不校验**，所以「自造」在 building 上比在
  grill 上**更省事**（grill 至少还要一份格式合格的决策记录）。这不改变结论，只说明本 change 的卖点
  应表述为「**编排**机械化」——design D2/R6 已如此表述，**估价合理**。

### 5. spec 可验证性 → **一处阻塞**（见「必须修改」1）
- 现存 7 条 Scenario 中，判据基本都能被 tasks 的用例钉住，且我**实测**钉住了这些：
  R1 触发 + 点名现有 stage（B4/B6）、R1「纯文档不误伤」（B5）、R2 stale（B7）、
  R3「`guard` 不受影响」（C3；`guardcmd.py:112` **只**调 grill 那条，**无** span、**无** building）、
  R4「building 不要求 grill 式正文」（实测：正文只有 `PASS` 的 building 报告仍通过）。
  R1 的「SHALL **不**由 tasks.md 是否勾选触发」也**实测成立**（我的 e2e 里 tasks.md 是 `- [ ] x` **未勾选**，
  门禁照样触发）。
- **但**：design D1 **明文要求**「并在 spec 里**加 Scenario 把多 change 边界钉死**」，
  而 `spec.md` **根本没有这条 Scenario**（`grep "^### Scenario"` 只有 7 条，无「多 change」字样；
  全文只有一处「每个」，在「提案期 / 纯文档改动不误伤」的 Then 里，是另一回事）；
  与此同时 **tasks B9 要求**为这条边界写用例。⇒ **design ↔ spec 不一致**，且 grill 自评**最高**的
  风险（R-new-1「高」）**在规范件里没有被钉住**。
- **更糟**：现存 Scenario「提案期 / 纯文档改动不误伤」的 Given 括注写「（只改文档**或**只动 change 目录）」，
  读者极易把它推广成「**文档改动一律豁免**」——而多 change 同 PR 时**恰恰不豁免**（实测 `multi2.py`）。
  严格说这**不算**自相矛盾（该 Scenario 的 Given 是「本次 diff **未**触及 `require_change_for`」，
  多 change 场景下为**假**，故不适用），但它**正是 design 要补的那条 Scenario 所消歧的东西**——
  缺了它，规范件在读法上会**指向错的方向**。

### 6. 新洞（自锁 / 误伤 / 自相矛盾）→ **无自锁**
我推演并**实测**了本 change **自己**走完整流程（design E0 时序，`selflock.py`）：

| 步 | 状态 | `check` |
|---|---|---|
| a | 提案期：只有 change 目录（无 grill manifest） | exit 1（既有行为；**不**要求 building——D1 未触发 ✓） |
| b | 有 grill 证据、**尚无**实现 | **exit 0** ✓ |
| c | 落了 `src/**` 但 grill manifest 未重跑 | exit 1（grill manifest **stale** + 缺 building，两条）✓ |
| d | **重跑 grill manifest + 建 building manifest** | **exit 0** ✓ |
| e | 审阅后再改一行 `src/**` | exit 1（**两条** manifest 均 stale）✓ |

⇒ design E0「必须先 build grill 放行 `src/**`、内容提交后**必须重跑覆盖**」**属实且可通过**，**无自锁**。
（注意步 a 证明 D1 对**提案期** change **不**误伤——design D1 那条边界在单 change 时成立。）
另确认本 change **不会踩自己的受保护写入**：它的 spec delta 落在 `openspec/changes/**/specs/`
（**不是** `openspec/specs/**`；本仓甚至没有 `openspec/specs/` 目录），且**不改** `.witnessloop/policy.json`
（`building_stage` 走缺省回落）⇒ 无需解释事件，非鸡生蛋。

顺带**实测复现 R5**（grill 由低升中）**属实**：`require_change_for: []` + 改 `src/` + 只有 grill 证据
⇒ `check` **exit=0**——关掉的是**整条代码门禁**，不只 building。

### 7. grill 的 asterwynd 跨仓引用 → **站得住**（本机可核验，我逐条核了）
asterwynd 就在本机：`/home/happy/my-agent/scripts/check_openspec_artifacts.py`。

- `_check_review_manifests` 在 **`:1111`**（grill 说 `:1110-1145` ✓；design 原稿的 `:1009-1048` **确已漂移** ✓）。
- `requires_building_review` 在 `:1129-1134`，与 design/proposal 的引文**逐字一致**（`not archived and
  change_type.primary != "docs" and _changed_capabilities(...) and _tasks_all_complete(...)`）。
- `_tasks_all_complete` 在 `:1016`，末行确为 `return checked > 0 and unchecked == 0`（`:1040`），
  docstring 明写「无 checkbox 行 = incomplete」⇒「**不勾选就能绕过**」属实。
- 全文件 `verdict|PASS` 命中 **6 处、全是注释/文案**，**无解析逻辑** ⇒「不解析 verdict 文本」属实。
- 「post-PASS tasks edits」在 **`:1716`**（grill 说 `:1716` ✓；design 原稿 `:1409` 漂移 ✓）。

⇒ design §1 改成**按函数名引用**是**对的修正**；「与先例对比」的实质结论成立。

## 必须修改
1. **（阻塞）`specs/building-evidence/spec.md` 补上 design D1 明文要求的那条「多 change 边界」Scenario。**
   位置：Requirement「落了实现就必须有实现后审阅证据」下；内容须与 design D1 的定案**逐字一致**，例如：

   ```
   ### Scenario: 多 change 同 PR（「一 PR 一 change」前提）
   - **Given** 本次 diff 触及 `require_change_for` 下的路径，且本 PR 同时触及 change A（含实现）
     与 change B（只动 change 目录、无实现）
   - **When** 运行 `check`
   - **Then** **每个**被触及的 change（含 B）都要有 `stage=<building_stage>` 的审阅证据；
     要免除就把 change 拆到单独 PR
   ```

   同时把现存 Scenario「提案期 / 纯文档改动不误伤」的 Given 括注改精确——现「（只改文档**或**只动
   change 目录）」会被读成「文档改动一律豁免」（多 change 同 PR 时不成立，实测 `multi2.py`）。
2. **（与 1 同批，成本极低）tasks D3 / design D5 的「对**接入方**是行为变更」声明补上第二类**：
   现只写了「改了代码没跑 review-loop 的 PR 从绿变红」；**「一个 PR 改代码 + 顺带一个纯文档 change
   ⇒ 那个文档 change 也被要求 building 证据」同样是既有绿→红**（实测 `multi2.py`），须一并写明，
   否则接入方只会被预警第一类。

## 新发现的风险
- **R-new-7（低）**：`_code_hits` 若照我那样直接内联，会把「什么算代码」的匹配表达式在本仓变成
  **第三份**拷贝（`checkcmd._require_change:101-108`、`guardcmd._code_paths:71-79` 已各一份）。
  design §3 只要求「同一个字段与同一个匹配」（字面已满足），未要求抽共用助手。建议 B8 顺手把 hit 计算
  抽成一个共用函数（`_require_change` 与新触发点共用），与本 change 自己主张的「不两边各写一套」一致。
- **R-new-8（低）**：proposal 的「验收」节未写明 Q1 甲案的边界（只机械「跑没跑」、**不**保证结论 PASS）。
  design D3/R6 已写明；建议 proposal + 关 issue 的说明同步，避免 issue #13 被读成「PASS 变硬门」。
- **R-new-9（低）**：若接入方把 `evidence.building_stage` 配成与 `grill_stage` 同值，building 那条会
  退化成复查 grill manifest（无害但失去意义）。tasks D2 的 `docs/gate.md §8` 小节可加一句提醒。

## 我实测复现的
1. **基线**：`uv run pytest -q` → `404 passed in 129.64s`。
2. **自伤面独立复现（最关键）**：自写 design §3 补丁（`constants.DEFAULT_BUILDING_STAGE` /
   `policy.evidence.building_stage`（含 `default_policy_doc`）/ `evidence` 抽出参数化
   `stage_manifest_findings_in_change(..., verify_body=False)` + grill 包装 / `checkcmd` 循环里
   `requires_building = bool(_code_hits(pol, changes))` 后加 building 那条）→ `uv run pytest -q`
   → **`404 passed`**，与基线**逐条同数**，**0 条新增失败**。**grill 的自伤面结论成立。**
3. **接线证明**（证「补丁真的接进了判定路径，不是只改常量」）：改 `src/**` + 只有 grill 证据 ⇒
   **exit 1** 且文案点名 `无 stage=building 的 manifest（现有 stage：grill）`；补 building 证据 ⇒
   **exit 0**；`--stage buildings` ⇒ **exit 1** 点名 `现有 stage：buildings, grill`；只改 `docs/`+`tests/`
   ⇒ **exit 0**。
4. **C2 回归**（对真实仓的 3 个 active change 直接调参数化助手）：`dogfood-bootstrap` /
   `grill-evidence-gate` / `guard-crash-exit` 的 `building_findings=0`、`grill_findings=0` ⇒ 回归红线成立。
5. **多 change 同 PR**（先全部内容、后全部证据）：**未打补丁 exit=0（绿）**；**打补丁 exit=1**，
   唯一 finding = `b-doc` 缺 building manifest ⇒ **前提不成立 + 新误伤**，两条都实测。
6. **多 change 交错提交**：未打补丁**已** exit=1（`_check_git_span` 判 stale），补丁后 exit=1（多一条 b-doc）。
7. **E0 自锁推演**（5 步，见 §6 表）：与 design 所述**逐步一致**，**无自锁**。
8. **R5**：`require_change_for: []` + 改 `src/` + 只有 grill ⇒ `check` **exit=0**（整条代码门禁静默失效）。
9. **R6**：`agentenv.resolve_run_id`（无环境变量）两角色 id = `building-reviewer-…` / `building-author-…`，
   **相等？False** ⇒ 自造 manifest 可过。
10. **asterwynd 跨仓**：行号（`:1111` / `:1016` / `:1716`）、谓词（`checked > 0 and unchecked == 0`）、
    「全文件无 verdict/PASS 解析」逐条核实。
11. **还原确认**：`git checkout -- .` → `git status --porcelain | wc -l` = **0**；补丁残留 grep 全 **0**；
    再跑 `uv run pytest -q` → **404 passed**。**未 commit。**

---

# 第 2 轮（R2）

## Reviewer
- run id: grill-adversarial-reviewer-building-review-gate-r2-2026-10-12
- 时间: 2026-10-12T07:19:12Z
- 方式: 独立**零记忆**审阅者（**无** R1 记忆），**默认 R1 的结论有错**，逐条开门核。
  实测在 `/tmp`（`/tmp/multi2_r2.py`，**复用本仓 `tests/helpers.py` 的原语**，**不**复用 R1 的脚本）；
  本 worktree **未打任何源补丁**，只写本文件（写前 `git status --porcelain -uall` = 0 行；未 commit）。
- **范围（作者刻意收窄）**：只核 commit `0f1f81e` 对 R1 的整合 + 确认最终 revision。

## Verdict
**CHANGES_REQUESTED** —— 阻塞项**只有 1 条，一行改完**（`tasks.md` D3）。

R1 的阻塞项**确已消解**（那条 Scenario 在 `spec.md:29`，且与 design D1、tasks B9 **三方对得上**）；
框定纠正、D3.1、§7 记账三处**全部到位**。**但 R1「必须修改」第 2 条只做了一半**：
design D5 写明了**两条**行为变更，而**产出 README 的那条任务**（`tasks.md:36` D3）仍只有**一条** ⇒
实现者照 tasks 逐条勾选会**漏发**一条对**接入方**的绿→红预警。change 的**技术核心仍站得住**
（我独立复现了它依赖的前提：多 change 同 PR **今天确实绿**）。

## 逐条核验（R1 要求 → 本轮实测落点）
| # | R1 的要求 | 落在哪 | 核验 |
|---|---|---|---|
| 1 | **（阻塞）** spec 补「多 change 边界」Scenario | `spec.md:29-33` | ✅ **到位**。规范性内容与 design D1 的定案（`design.md:82-83`）**同义**，且**操作句逐字相同**（「要免除就把 change 拆到单独 PR」「不提供 `building_exempt_changes` 之类的豁免名单」）；Given 把「每个」具体化成了 A/B 两个 change（Scenario 必须如此），措辞非字面照抄 |
| 1b | 既有「提案期 / 纯文档」Scenario 的括注改精确 | `spec.md:24` | ⚠️ **基本到位**：限定落在**标题**「（单 change 情形）」，Given 括注原文未动（见 N3）。因紧邻其下就是覆盖它的那条 Scenario，**误读路径已封死** ⇒ 不拦 |
| 2 | D1：承认「一 PR 一 change」是**新造**约束（非同族） | `design.md:79-81` | ✅ 到位：「对抗验证纠正」段明写「那条约束的是**提交顺序**，这条约束的是 **change 数量**，是**本 change 新造**」+ 实测 `exit 0 → exit 1` |
| 2b | D5 写**两条**行为变更，且 **tasks D3 同步** | `design.md:125-127` ✅ ／ `tasks.md:36` ❌ | ❌ **tasks 那半边未做** ⇒ **本轮的阻塞项** |
| 3 | 新增 D3.1（选甲须显式声明「PASS 不成为硬门」） | `design.md:109-115` | ✅ 到位，措辞是**条件式**（「**若** Q1 选**甲**」），未写成已定案 |
| 3b | `proposal.md` 加「边界声明」 | `proposal.md:40-46` | ✅ 到位，带条件标记「（**选甲时**；见 design D3/D3.1）」⇒ 在 Q1 未裁定时**未** over-claim |
| 4 | §7 记入 R1 的结论 | `design.md:201-206` | ✅ 到位，且与 R1 原文**逐条相符**（阻塞项／自伤面 0 条独立复现／Q1 不阻塞／R6 成立／无自锁），无 over-claim |

**「规范件说 A、设计说 B」残留**：实质 1 处（阻塞项 2b：`design.md:125` ↔ `tasks.md:36`）+ 引用 1 处（N1：design「**不**按行号引用」↔ `proposal.md:17` 仍引**已漂移**的行号）。

## 阻塞项
**（唯一）`tasks.md` D3 缺第二类行为变更** —— 与 design 明文要求不一致，且会让实现产物漏掉一条接入方预警。

- **事实**：`design.md:125` 明写 README 要写**两条**（① 「改了代码没跑 review-loop」的 PR 绿→红；② **多 change 同 PR** 时**每个** change 都要 building 证据）；`design.md:81` 亦写这条新约束「**须与 D5 那条一并写进 README**」。
  而**唯一**产出 README 的任务 `tasks.md:36`（D3）括注里**只有 ①**（`grep -rn 行为变更` 全 change 目录：design 5 处、tasks **1 处**）。
- **为什么这是阻塞而不是措辞**：本 change 对**既有接入方**的**唯一**缓解手段**就是文档**（design §8 Q3 的定案：「**只写文档** + 明确『对接入方是行为变更』，**不加**过渡开关」）⇒ 文档漏一条 = 缓解机制缺一半；且实现者按 tasks 逐条勾选，D3 是 README 的**全部**指令来源。
- **修法（一行，与 design D5 逐字对齐）**：`tasks.md:36` 改为
  「- [ ] D3 `README.md`：写明**对**接入方**是行为变更**（①「改了代码没跑 review-loop」的 PR 从绿变红；② **多 change 同 PR** 时**每个** change 都被要求 building 证据——原本可捎带的纯文档 change 也会红）」

## 非阻塞观察（建议与阻塞项同批改，我**不**据此拦）
- **N1**：`proposal.md:17` 仍引 asterwynd 的**漂移行号** `:1009-1048`，而 design §1 / R7 已把口径改成「**按函数名**定位、**不**按行号」（`design.md:31-32`、`:196`）⇒ 同一事实**两份规范件说法不一**（R1 已实测真值 `:1110-1145`）。design 自己把 R7 定级「低」，**我同意不拦**，但顺手改掉最省。
- **N2**：`tasks.md:23`（B9）写「**Q2 裁定**「一 PR 一 change」前提」——Q2 仍是**待用户裁定**的 Open Question（`design.md:221` 只是「**推荐**」；`tasks.md:3` 自己也写「Q1/Q2/Q3 确认前不得写实现代码」）⇒「裁定」是**过头话**，建议改「Q2 **推荐**」。注意：**spec 照 design D1 的定案**把该边界钉死，是 R1 **明确要求**的（R1 判「Q2 的方向对，缺的只是把边界写进 spec」）⇒ 那一处**不算** over-claim。
- **N3**：R1 指的是改 **Given 括注**，实际限定落在**标题**（`spec.md:24`），Given（`spec.md:25`）仍是「（只改文档或只动 change 目录）」。因 `spec.md:29-33` 立即明写覆盖，**误读已基本封死**；若顺手，把 Given 改成「（**本 PR 只涉及这一个 change 时**：只改文档或只动 change 目录）」更稳。
- **N4**：`design.md:72` 的边界 bullet（「纯文档 / 纯 change 目录改动…⇒ **不要求**」）自身没有「单 change」限定，靠紧接的 ⚠️（`design.md:74-84`）兜住 ⇒ **不构成矛盾**，但与 spec 标题的限定**不对称**，可顺手加「（单 change 情形）」。
- **已核无误（不构成不一致）**：新 Scenario 与「提案期 / 纯文档不误伤」**不冲突**（两条的 Given 互斥：一条要求「**未**触及 `require_change_for`」，另一条要求「既触及代码、又触及**另一个** change 目录」）；Requirement 正文「要求**被触及的** change 存在…manifest」（`spec.md:8-10`）本就蕴含多 change 语义，与 Scenario 一致；`spec.md:12`「SHALL **不**由 tasks.md 勾选触发」与 design D1（否决 asterwynd 的 `_tasks_all_complete`）一致；D3.1 ↔ D5 ↔ proposal 边界声明**口径统一**（都是「证据**存在性**机械 / verdict 文本不参与」）。

## 我实测的
1. **基线**：`uv run pytest -q` → **`404 passed in 50.22s`**（与要求一致）。
2. **独立复现「多 change 同 PR 今天可行」**（= D5② 「原本可以…」与新 Scenario 的**前提**，也是 R1 §2(a) 的实测）：
   自写 `/tmp/multi2_r2.py`，**复用本仓 `tests/helpers.py` 原语**（`write_change` / `write_review` / `commit_all`，与既有用例走**同一条**代码路径，避免自造 manifest 引入我自己的偏差）；造仓：`init` → feature 分支 → **单一内容提交**（change `impl-a` + `src/a.py`；change `b-doc` **纯目录、无实现**）→ **单一证据提交**（`impl-a`：grill + building；`b-doc`：**只有 grill**）→ `check --base main --head HEAD`
   ⇒ **`check：通过 ✓`，exit 0**（15 个变更文件 / 2 个 change 目录：`b-doc, impl-a`）。
   ⇒ 「一个 PR 捎带一个纯文档 change」**今天确实是绿的** ⇒ design D5② 的「原本可以」**不夸大**，新 Scenario 是**真的行为变更**（而非把现状写成规范）。
   **未重跑打补丁那半**（诚实边界）：R1 已用自写补丁测到 `exit 0 → exit 1`（唯一 finding = `b-doc` 缺 building manifest），我**只核机制**——`checkcmd.py:73-84` 的循环是**逐 change**、触发（`_code_hits` / `_require_change`，`checkcmd.py:92-120`）**只看本次 diff** ⇒ 「触发全局 × 要求逐 change」必然产生该误伤，**代码结构上成立**，spec 那条 Scenario 的 Then 属实。
3. **规范件形态**（会不会卡实现）：`uv run witnessloop check`（对**本仓自身**）⇒ **仅 2 条** finding，都是**预期**的「本 change 还没有 manifest」（`reviews/` 下确实只有两份 `.md`、无 `*.manifest.json`）；`validate_change_dir` **无**抱怨 ⇒ spec delta / change 目录**形态合格**，不会卡住实现。
4. **引用抽查**（自己开门核，不采信任何一侧的声明）：`contract.py:89` `validate_change_dir` ✓、`:121` `validate_review_manifests` ✓、`:272` `_check_git_span` ✓；`checkcmd.py:92` `_require_change` ✓、`:123` `_protected_writes`（design 引 `:122-180`，起点早一行，**无实质影响**）；`evidence.py:203` 逐字 = 「grill 决策记录必须有对应的审阅证据」✓；`helpers.py:116` `stage: str = "building"` ✓、`:214` `stages=("grill","building")` ✓；`docs/gate.md:121-123` 逐字含「结构性不同…不挡蓄意伪造」✓、`:172-177` 逐字含「内容与证据必须分属两个提交；单提交 PR 不被支持」✓。
5. **还原确认**：本 worktree **未打源补丁**，`git status --porcelain -uall` 在写本报告前 = **0 行**；`/tmp` 实验产物在仓外，不影响。**未 commit。**

---

# 第 3 轮（R3）

## Reviewer
- run id: grill-adversarial-reviewer-building-review-gate-r3-2026-10-12
- 时间: 2026-10-12T07:24:16Z
- 方式: 独立**零记忆**审阅者（**无** R1/R2 记忆），**默认前两轮结论有错**，逐条开门核。
  作者刻意收窄范围 ⇒ 本轮只做两件事：核 R2 的 4 项整合 + 跨 4 份文档的最终一致性扫描。
  实测在 `/tmp/r3/probe.py`（**复用本仓 `tests/helpers.py` 原语 + `conftest.git`/`commit_all`**，与既有用例走同一条代码路径）；
  本 worktree **未打任何源补丁**，只写本文件（写前 `git status --porcelain -uall` = 0 行；未 commit）。

## Verdict
**PASS** —— R2 的 4 项**全部到位**，跨文档扫描的 4 个指定靶点**无残留不一致**，**无阻塞项**。
change 的技术核心我**独立复现**了它所依赖的前提（多 change 同 PR **今天确实绿**）。

## 逐条核验（R2 那 4 项 → 本轮落点）
| # | R2 的项 | 落在哪 | 核验 |
|---|---|---|---|
| 1 | **（R2 唯一阻塞）** `tasks.md` D3 只写**一条**行为变更，design D5 要求**两条** | `tasks.md:36-38` | ✅ **到位**。现为「写明**对**接入方**是两条**行为变更（design D5 明列两条，**别只写一条**）：①「改了代码但没跑 review-loop」的 PR 从**绿变红**；② **多 change 同 PR** 时**每个** change 都要 building 证据（原本可「一个 PR 捎带一个纯文档 change」，现在会红；实测 `exit 0 → exit 1`）」——与 `design.md:125-127` **同义且逐条对应**，且与 `design.md:81`「须与 D5 那条一并写进 README」对得上。 |
| 2 | `tasks.md` B9 的「Q2 **裁定**」过头 → 应写「推荐…待裁定」 | `tasks.md:23` | ✅ **到位**：现为「（**这是刻意的**，Q2 的**推荐**口径「一 PR 一 change」前提；待用户裁定）」——「裁定」已换成「**推荐**口径…待用户裁定」，与 `design.md:221`「**推荐**」及 `tasks.md:3`「Q1/Q2/Q3 确认前不得写实现代码」自洽。 |
| 3 | `proposal.md` 去掉 asterwynd 的**漂移行号** `:1009-1048` | `proposal.md:16` | ✅ **到位**。现为「（已读源码核对；**按函数名**引用 `_check_review_manifests`，不引行号——跨仓行号会漂）」；全文件**已无**任何 asterwynd 行号（`grep -n "asterwynd"` 4 处，全是函数名/项目特有检查，无 `:NNNN`）。 |
| 4 | `design.md` 的 `checkcmd` 行号 off-by-one（`122`→`123`） | `design.md:22` | ✅ **到位**：现引 `checkcmd.py:123-180`，实测 `def _protected_writes` **确在 `:123`**（起点已修对；终点仍差一行，见 O6，无害）。 |

## 跨文档一致性扫描（只扫指定的 4 个靶点）
1. **多 change 边界（design D1 ↔ spec Scenario ↔ tasks B9）→ 无残留。**
   `design.md:82-83`（「本 PR 触及 `require_change_for` ⇒ 本 PR 触及的**每个** change 都要 building 证据；要免除就把 change 拆到单独 PR」+「**不加** `building_exempt_changes` 豁免名单」）
   ↔ `spec.md:29-33`（同一条，操作句近逐字：「要免除就把 change 拆到单独 PR」「**不提供** `building_exempt_changes` 之类的豁免名单（豁免名单 = 新的绕过面）」）
   ↔ `tasks.md:22-23`（B9 用例）。三处**同一条事实、同一口径**，无 A/B 分叉。
2. **两条行为变更（design D5 ↔ tasks D3 ↔ proposal）→ 无残留。**
   `design.md:125-127` / `tasks.md:36-38` 两侧**逐条对齐**（① 改了代码没跑 review-loop；② 多 change 同 PR）。
   `proposal.md` **未**逐条列举这两条——但 design D5 只要求它们落 **README**（`design.md:183` §6 同），proposal 的职责是「为什么/目标/边界声明」，其 `:33-34` 的「目标」与 `:57` 的「验收」（只改文档/只动 change 目录 ⇒ 不要求）与两条行为变更**不冲突**（前者是机制陈述，后者是**单 change 情形**的豁免，见 O-① 的同类限定）。
3. **「PASS 不成为硬门」的**条件式**措辞（Q1 未裁定）→ 无残留（1 处措辞级，见 O1）。**
   `design.md:95`「**待用户裁定**（**Q1**，甲/乙）」、`design.md:111`「**若** Q1 选**甲**，则**必须**…」、`proposal.md:43`「（**选甲时**；见 design D3/D3.1）」、`tasks.md:51`「verdict 文本判据（**若** Q1 选甲）」——四处**都带条件标记**，**没有**任何一处把它写成已定案。spec 侧唯一相关处是 `spec.md:65` 的括注，见 O1（判**不阻塞**）。
4. **asterwynd 引用方式（全仓「按函数名」）→ 无残留。**
   `design.md:31`「**按函数名定位** `_check_review_manifests`…⚠️ **不按行号引用**」、`design.md:49`「**按函数名**定位」、`design.md:173`（R7）、`proposal.md:16`「**按函数名**引用…不引行号」——口径统一。
   我把两侧仍出现的**行号**当「实测证据」逐条**开门核了真值**（见「我实测的」4）：`_check_review_manifests` **在 `:1111`**、`requires_building_review` **`:1129-1136`**、`_tasks_all_complete` **`:1016`** 且末行 `:1040` = `return checked > 0 and unchecked == 0`、post-PASS **`:1716`**；原稿引的 `:1009-1048` 处（`sed -n '1009,1012p'`）是**无关代码** ⇒「已漂」属实。**引文块与真源码逐字一致。**

## 阻塞项
**无。**（未发现会让实现失败、或 spec 自相矛盾、或使结论站不住的问题。故本轮 **PASS**。）

## 非阻塞观察（我**不**据此拦；供作者/停轮顺手）
- **O1（措辞级 · 条件式）**：`spec.md:65` 的括注「（building 只要求证据存在）」是**无条件**写法，而 design 把同一句当**甲案**的产物——
  `design.md:92`「**不额外要求报告正文结构**（**除 D3 若选乙**）」、`design.md:128-129`「选**甲**则补一句『本门禁只要求证据存在』」。
  即：design 是「A 除非乙」，spec 写成「A」。**不判阻塞**：该括注是**理由性注解**，它注解的那条 SHALL（「**不**把 grill 专有的**报告正文**校验泄漏给 building」）在**甲/乙下都成立**（乙要的是「最终裁定 = PASS」这一条**新**判据，不是 grill 的 `## Confirmed Decisions` 正文校验）；spec 的规范句**不自相矛盾**、实现按它做**不会失败**。若作者顺手，可加「（Q1 选甲时）」或删括注。
- **O2（design 有 mandate、spec 无对应 · 判不阻塞）**：`design.md:167`（R5）「⇒ 关掉的是**整条代码门禁**…**须在 `docs/gate.md §2` 与 spec 显式声明**」、`design.md:224-225`（Q4）「**至少写进 `docs/gate.md §2` + spec」。
  - `docs/gate.md §2` 那半边**仓里早就有**：`docs/gate.md:66-68` 逐字写着「没有它时，`check` 只保证「如果你动了 change 目录/受保护路径，它要齐备」——于是最省事的绕过方式是什么都不建（**只改 `src/` 的 PR 直接放行**）」⇒ 无需新任务。
  - **spec 那半边**：`spec.md` 全文**无**「静默/失效/为空/`[]`」字样，也没有对应任务（`tasks.md` D1/D2 只覆盖 `§6`/`§8`）。
  - **为什么不拦**：这是**既有**机制的既有边界（本 change 只是**继承**它，不是新造），§2 已声明；且 Q4 本身就是**待用户裁定**的 Open Question（design 明写「是否加『为空时 warning』请用户定」）。**不构成**「实现失败 / spec 自相矛盾 / 结论站不住」。建议：Q4 定案时一并补进 spec + tasks。
- **O3（口径小缺）**：`tasks.md:3` 与 `:43`（E0）只列「**Q1/Q2/Q3** 答复」，而 `design.md:216-225` 有 **Q4**（若答「加 warning」会改代码并**有意**让 `test_require_change_for.py::test_empty_require_change_for_disables_the_rule` 变红）⇒ 实现闸门少列了一个可能改代码的问号。建议 E0 改成「Q1–Q4」。
- **O4（命名）**：`tasks.md:13`（B1）把共用助手称作 **`StageRequirement`**——该名字**全 change 目录只此一处**，`design.md:150` 的切法是 `stage_manifest_findings_in_change(change_dir, *, stage, manifest_glob, label, reason, verify_body=False)`（`spec.md:60-65` 只说「一处实现」）。语义描述一致（都是「只要求存在的参数化助手」），实现者只会写一个助手 ⇒ **不拦**，但名字最好统一。
- **O5（编号同名不同指）**：`design.md:135`「原稿（**R1**/本节的旧稿）」用的是 **§4 的风险编号** R1（自伤面），而 `design.md:202`「**对抗验证 R1**」是**轮次**编号 ⇒ 同文件里 **R1 有歧义**。可把风险项写作「风险 1」。
- **O6（行号终点 off-by-one，无害）**：`design.md:22` 引 `checkcmd.py:123-180`，实测 `_protected_writes` 的 `return findings` 在 **`:181`**（起点 123 已修对）。同类：`design.md:31` 引 `:1110-1145`，实测 `def` 在 **`:1111`**——但该处**明写「不按行号引用」**、数字仅作实测证据，可留。
- **O7（排版）**：`proposal.md:65` 有一个**未闭合**的 ``` 围栏（`grep -n '^```'` = 18 / 25 / 65；18-25 已配对，65 悬空、其后无内容）。**非本轮引入**（`git show e0904e6^:…/proposal.md` 末尾同样是这个悬空围栏）。纯排版，删掉即可。

## 我实测的
1. **基线**：`uv run pytest -q` → **`404 passed in 29.62s`** ✅（与要求逐字一致）。
2. **规范件形态**（会不会卡实现）：`uv run witnessloop check`（对**本仓自身**）⇒ **仅 2 条**，都是**预期**的「本 change 还没有 manifest」（`reviews/` 下只有 2 份 `.md`、无 `*.manifest.json`）；`validate_change_dir` **无**抱怨 ⇒ spec delta / change 目录形态合格。
3. **独立复现「多 change 同 PR 今天可行」**（= `spec.md:29-33` 那条新 Scenario 的**前提**，也是 `design.md:127` / `tasks.md:38` 的「原本可以」）：
   `/tmp/r3/probe.py`——`init` → feature → **单一内容提交**（change `impl-a` + `src/a.py`；change `b-doc` **纯 change 目录、无实现**）→ **单一证据提交**（`impl-a`：grill + building；`b-doc`：**只有 grill**）→ `check --base main --head HEAD`
   ⇒ **`check：通过 ✓`，exit 0**（15 个变更文件 / 2 个 change 目录：`b-doc, impl-a`）。
   ⇒ 「一个 PR 改代码 + 捎带一个纯文档 change」**今天确实是绿的** ⇒ 新 Scenario 是**真的行为变更**（不是把现状写成规范），`design.md:80` 的「未打补丁 `exit 0`」不夸大。
   （打补丁那半我不重跑：机制上 `checkcmd.py:73-77` 的循环是**逐 change**、而触发是**全局**的（`checkcmd.py:92-120` 只看本次 diff 命中 `require_change_for`）⇒「全局触发 × 逐 change 要求」**必然**产生该误伤；R1 已实测 `exit 0 → exit 1`。）
4. **引用抽查**（自己开门核，不采信任何一侧的声明）：`checkcmd.py:71-89` 逐行（含 `:79-84` 的 grill 调用）✓；`_require_change:92-120` ✓；`_protected_writes:123-181` ✓；`contract.validate_change_dir:89` ✓；`validate_review_manifests:121` ✓；`_check_git_span:272` ✓；`evidence.grill_evidence_findings_in_change:172` 且 `:203` 逐字 = 「grill 决策记录必须有对应的审阅证据」✓；`docs/gate.md:121-123` 逐字含「结构性不同…不挡蓄意伪造」✓、`:172-177` 逐字含「内容与证据必须分属两个提交；单提交 PR 不被支持」✓；`templates/review-loop.md:99-100` 逐字含「第 3 轮仍 `CHANGES_REQUESTED`…停下…升级到人判断」✓；`manifestcmd.py:122-124` 只在两 id **相等**时拒 ✓；`grep -rn building src/` **只**命中 `cli.py:107,111` 的 `--help` 文案 ✓（`design.md:24`「0 处**功能性**命中」属实）。
5. **asterwynd 跨仓**（`/home/happy/my-agent/scripts/check_openspec_artifacts.py`，1802 行）：`_check_review_manifests` **`:1111`**、`requires_building_review` **`:1129-1136`**、`_tasks_all_complete` **`:1016`**、`return checked > 0 and unchecked == 0` **`:1040`**、post-PASS **`:1716`**；全文件 `PASS` 命中 **4 处全是注释/文案**（`:1122` `:1139` `:1623` `:1716`）、**无**解析逻辑 ⇒「不解析 verdict 文本」属实。
6. **还原确认**：本 worktree **未打源补丁**；`git status --porcelain -uall` = **0 行**；实验产物在 `/tmp/r3/`（仓外）。**未 commit。**
