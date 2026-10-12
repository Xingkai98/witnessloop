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
