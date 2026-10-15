# Grill: confirm-gate-fail-closed 设计追问

> 独立零记忆审阅者产出（2026-10-15）。**READ-ONLY**：未改被审 worktree 的任何受版本控制的文件、未 commit / push、未跑 `git reset` / `checkout`。
> 全部会改状态的实验在**隔离副本**做：`git archive HEAD | tar -x -C /tmp/probe-wl`（基线树）与 `cp -r` 出的 `/tmp/probe-patched`（按本稿 spec 打的**原型**，只为验证语义，不是实现 PR）。
> **本文件即 `templates/grill.md:91` 说的那份决策记录**（`reviews/grill-review.md` ≡ `grill-design.md`）；它必须由 `stage=grill` 的 manifest 以 `report_path: reviews/grill-design.md` 绑定（否则 `contract.py:315-345` 的孤儿规则会在本 change 自己身上判红）。
> ⚠️ 本文件**没有** `## User Confirmation` 小节：那一段按流程由主流程在**用户停轮答复之后追加**（照 `archive-awareness/reviews/grill-design.md:125` 的先例，**审阅者正文一字不改**）。

## Reviewer

- run id: `grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`（确定性兜底锚 = change id + 被审 revision 短摘要；本会话未提供宿主 session id）
- 时间: 2026-10-15
- 被审 revision: `ef8b3ab73d39ae359d86589d651f855f578376cd`（= `origin/main`；change 目录**未提交**，四份文档 `sha256sum` 汇总 = `81ece0834cb6bd871fe373203ff0a3e81ab299257b0589eac2304d0f04d51b7b`）
- 方法: ① 读 `gh issue view 23 --json`、change 四份文档、`src/witnessloop/evidence.py`、`templates/grill.md`、`plugin/commands/grill.md`、`docs/gate.md §8`、`README.md`、`tests/`；② 直调真函数 `evidence._sections` / `_confirmations` / `grill_evidence_findings`（**不是模拟**）复现 E1–E4 与 §1.5；③ 在 `/tmp/proto.py` 里按 `design.md §D2` 写了**候选判定原型**，把四种语义（① 逐字 / ② 含字样 / ③ 逐字∪紧规则 / strawman 全标题）在**三份语料**上各自重算一遍；④ 在 `/tmp/probe-patched` 里把原型**接进 `evidence.py`**，跑**全量** `pytest`；⑤ 全称/计数一律 `find | wc -l` / `grep -l | wc -l`，无 `head` 截断；⑥ 逐条 `grep -n` / `sed -n` 核对立项稿点名的每个 `文件:行号`。
- 基线复核: 全量套件在本副本上 **521 passed**（`uv run pytest` 的同一份用例集；副本内直跑时 `tests/test_agentenv.py` 的 2 条 `REPO_ROOT` 用例会因 editable 安装指向原 worktree 而假失败，属**我的隔离方法**的产物，不是本 change 的问题）。

## Confirmed Decisions

- **决策：issue #23 的机制描述**逐字成立**——同一份正文、只换二级标题，判据从「红 3 项」变「绿 0 项」；我独立复现了 `design.md §1.2` 的 E1–E4，数字逐个一致。**
  理由（直调真函数，非模拟）: 取接入方那份真实报告（`/home/happy/wl-review-a/openspec/changes/archive/2026-09-30-workflow-dry-run/reviews/grill-design.md`，其 `:46` 是非逐字标题）——**原样 `findings=0`**；只把标题改成逐字、其余一字不动 `findings=0`（其 Q1/Q2/Q6 本有实质确认）；逐字标题 + 清空 `## User Confirmation` ⇒ **`findings=3`**（Q1 / Q2 / Q6 逐条「未经用户确认」）；**非逐字**标题 + 同样清空确认 ⇒ **`findings=0`**。⇒ 判据今天约束的是「标题恰好写对的人」。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`
- **决策：`design.md §1.5` 那个「空壳 + 近义标题装真问题」的洞今天**真的是绿的**，而它在 ③ 下变红、在 ① 下**仍然是绿的**——所以 D1 选 ③ 不是口味，是**被实测逼出来的唯一闭合解**。**
  理由: 同一份构造（逐字 `## Open Questions` 写 `（无）` + `## Design-Level Open Questions（已并入 design 的 Q1–Q6）` 里放 `- **Q1** 真的问题？` + 空 `## User Confirmation`）：**今天 `0` 条**；**①「只认逐字」`0` 条**（小节在、空 ⇒ `or ""` 之后的循环仍零次迭代——**① 根本没堵住这个洞**）；**③ `1` 条**（`Open Question Q1 未经用户确认`）。⇒ `design.md D1` 那张表里 ① 的「❌ 漏」是**实测**，不是推理。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`
- **决策：语料计数复核——本 worktree 的数字与立项稿**完全一致**；issue 的 60/59/1 在我能拿到的**任何**检出里都复现不出来，但**结构与那一份的形态到处一致**，「新红 0」这个结论不依赖总数。**
  理由（`find | wc -l` / `grep -l | wc -l`，非 `head`）:
  - `/home/happy/wl-review-a`（`git rev-parse HEAD` = `6f75370…`，分支 `probe`；与立项稿写的一致）: `grill-design.md` **63** 份，全在 `openspec/changes/` 下（`archive/` 内 **62**；active 那份是 `witnessloop-adoption`）；逐字 `## Open Questions` **62 / 63**；含 `Open Question` 字样的二级标题 **63 / 63**；**非逐字恰好 1 份**，标题逐字等于 issue 点名的那一个。另: 逐字 `## Confirmed Decisions` 63/63、逐字 `## User Confirmation` **59/63**、`*.manifest.json` **0** 份。
  - `/home/happy/wl-dryrun`（同一接入方的另一份快照，分支 `dry` 无提交）: **62 / 61 / 1**，那一份还是同一个文件。
  - `origin/master` 的树（`git ls-tree -r --name-only`）: 同样 **63**。
  - **issue 的 60/59/1 对不上**：本机没有任何检出给出 60（我把 `/home/happy/wl-*/` 全扫了一遍，带 `grill-design.md` 的只有 62 / 63 两份语料）。差额是**同一方向、同一个 1**（62−2 = 60 / 61−2 = 59 / 1 不变）⇒ 与「issue 数的是更早的快照」这个解释**相容**，但**我无法证实**它。⇒ 立项稿把「总量对不上」归因于快照差，只能算**合理推测**；真正被三份检出一致证实的只有**结构**（63/62/1、62/61/1 都恰好 1 份非逐字，且是同一个文件、同一个标题）。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`
- **决策：「③ 之下存量新红 0」这条结论**独立复算成立**——我按 `design.md §D2` 从 spec 写了一份原型并接到 `evidence.py` 上，在接入方 63 份 + 本仓 8 份上重算: ③ 新红 **0 / 0**；① 新红 **1 / 0**；strawman「凡二级标题都算候选」新红 **4 / 1**。**
  理由: 「新红」定义为「**今天 0 条 finding、新语义下 > 0 条**」。③ 下两份语料**零新红**（复现立项稿）；① 的那 1 条正是 `2026-09-30-workflow-dry-run`；strawman 的 4 条（接入方）分别来自把 `## 风险` / `## Round 3` / `## Review Notes` / `## Code-Resolved Questions` / 甚至 `## User Confirmation` 正文里**散文提及**的 Q 编号当成待确认项——这就是「匹配放宽」的真实代价，也正是 D2 必须把边界钉死的理由。
  ⚠️ **该测量的前提必须写明**：接入方检出里 **0 份 manifest** ⇒ 那 63 份报告**今天根本不被门禁评估**。「存量新红 0」是「**假如它们都被绑定**」的模拟（这正是立项稿的用法，也是保守的用法），但它**不是**「今天跑 `check` 会怎样」的观测。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`
- **决策：立项稿点名的 `文件:行号` 我逐条核过，**全部命中、无漂移**；`tests/test_evidence.py` 确实 9 条、且 `test_missing_sections_are_flagged` **只断言非空**（无精确计数断言），`tests/test_archive_awareness.py:425` 那条 `len(findings) == 1` 的精确断言也用 `SHORT_GRILL`（三节逐字齐全）⇒ 新增判据不会把它撞红。**
  理由（`grep -n` / `sed -n`）: `evidence.py:24-26`（三个常量）、`:52-64`（`_sections`）、`:121-133`（Confirmed 两条 + 缺件）、`:140-142`（User Confirmation 缺件）、`:144-145`（`or ""` 的 fail-open）**全部逐字命中**；`templates/grill.md:107` 就是结构块里的逐字 `## Open Questions`；`plugin/commands/grill.md:7-9` / `:27` / `:29` 与 `docs/gate.md:392-393` / `README.md:172` 也与立项稿描述一致；`archive-awareness/reviews/grill-design.md:61`（非逐字）/ `:110`（逐字）、`grill-adversarial-gate/reviews/grill-adversarial.md:21`、`archive-awareness/tasks.md:143-150`（「追加逐字小节、审阅者原正文一字未改」）**全部命中**。R2 点名的 6 份 `## Code-Resolved Questions` 的 Q 编号我也逐个复算，与立项稿列的 `[1] / [2,3,4] / [1,2,3,4] / [1,2] / [1,3] / [1]` **逐条一致**（另有 2 份该小节无 Q）。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`
- **决策：把 spec 里的语义**真做出来**也不撞既有测试——我在副本上实现 D2 的候选判定 + D4 的两档诊断，**全量 521 passed**。**
  理由: 副本 `/tmp/probe-patched`（`PYTHONPATH` 指向副本 `src/`，确认 `witnessloop.evidence.__file__` 落在副本内）跑全量: **521 passed**，与基线一致。⇒ 立项稿 §5.2 的回归面判断（`VALID_GRILL_REPORT` / `SHORT_GRILL` / `test_evidence.py` 9 条 / 文档守卫全绿）**成立**；也说明**今天**没有任何一条测试钉住那条 fail-open 行为（否则实现后必红）——F1–F7 / N1–N7 确实是这条判据的**唯一**钉子，TDD 不能省。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`
- **决策：`_sections()` 的 `setdefault` 合并语义今天**已在被依赖**，且本 change 不碰它是对的；「同名标题 ⇒ 并集」这条我实测过。**
  理由: 两个 `## Open Questions` ⇒ 同一个 key、正文 `'- **Q1** 甲？\n\n- **Q2** 乙？'`（首尾相接）；两个 `## User Confirmation` ⇒ `_confirmations` 拿到 `{1: …., 2: ….}`（两份确认都生效）。反向也测了: 同名两节、只确认一节 ⇒ **红**（今天与 ③ 同结果，无回归）。⇒ D3「并集、绝不静默丢」与 D6「不改 `_sections()`」都有实测支撑。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`
- **决策：判据的**作用域**比立项稿说的更窄——`Q<n>` 只有出现在**候选小节正文**里才被要求确认；写在 `## Confirmed Decisions` / `## 风险` / `## Code-Resolved Questions` 等非候选小节里的 Q 编号**不产生**任何要求（我实测: 决策块里写「见 Q7 与 Q9」⇒ 0 条）。**
  理由: `evidence.py:147` 只把候选小节的正文拼成 `body`，`_open_question_indexes` 只作用于它。⇒ 三个直接后果: ① R4（散文提及）**只在候选小节内部**成立，比立项稿写得更窄，值得按此措辞；② `## Code-Resolved Questions` 不是候选（也不是 R2 担心的假红来源——**只要** D2 的 (b) 真的要求 `Open Question` 是结尾短语，单数 `Question` 天然不匹配，我验过）；③ **写报告的人**（包括本文件）在候选小节正文里提一个不存在的 `Qn`，就会被要求确认它——这条对**本 change 自己的收尾**（G3）是活的。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`
- **决策：产出方侧的「`plugin/commands/grill.md` 不改」成立；`templates/grill.md` 也**只需要加口径**（结构块已经在产出逐字标题）。**
  理由: `plugin/commands/grill.md:7-9` 明写「本适配器只做接线……不重复它的正文」，而它自己那两处 `## Open Questions` / `## User Confirmation`（`:27`、`:29`）是**行内 code span**、**不在行首**，`_HEADING_RE`（`evidence.py:31`）根本不会把它们当标题 ⇒ 它们既不能自造红、也没有可订正的第二种措辞。`templates/grill.md:107` 已经是逐字的 `## Open Questions`，`:110` 已写「可为空」⇒ E1/E2 只需把口径写死（须逐字、空也保留），**不需新增小节**。
  `来源: grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`

### 订正（立项稿里被我的实测改掉的说法）

1. **`design.md §1.6` 的 ②（宽匹配）一行自相矛盾。** 同一张表里 ② 的「存量新红」写 **0**，`design.md:117` 却把它的理由写成「**误伤面大**」并举 `grill-adversarial.md:21` 为例。我按 ② 复算: **接入方 0 / 本仓 0**（两份语料里 `## 逐条对抗（… Open Questions）` **只出现在 `stage=grill-adversarial` 的报告里**，而正文判据只作用于 `stage=grill`——`evidence.py:216-217` 的 `verify_body`）。⇒ 排除 ② 的**真理由**是「规则无法解释 / 无法写进文档」（`design.md:139` 已经说了），**不是**实测误伤；建议把 §1.6 ② 那行的措辞从「误伤面大」改成「误伤面**未实测**，但边界不可解释」。
2. **`design.md §2.5` / `spec.md:157` 的残留洞举错了例子。** 它拿 `## 悬而未决的疑问` 当「藏身处」，那是个**没人会自然写**的措辞；**真正**的藏身处是模板**自带**的 `## Code-Resolved Questions`（`templates/grill.md:104`）——把一条本该用户拍板的问题标成「能由代码定案」，挪进那个小节，逐字 `## Open Questions` 留空 ⇒ **新语义下照样绿**。这不是新洞（今天同样绿），但它是**最像真实误用**的那条路径，边界声明应当点名它。
3. **`design.md:446`（Q3 的例子）把风险说高了一档。** 「它的确认段将来少了任何一条 ⇒ 会以『Q 未经确认』红」——那份报告是被 manifest 以 `report_hash` 绑着的（`contract.py` 的 `_validate_one`），**任何**事后改写先撞 hash 不一致，根本走不到逐条确认那条判据。⇒ Q3「不改也不红」的结论更强，不是更弱。
4. **`proposal.md:87`（验收「存量影响 = 0」）没写前提。** 见上一条 Confirmed Decision 的 ⚠️：那 63 份在接入方检出里**没有 manifest**，今天不被评估；「新红 0」是**假设绑定**下的模拟。结论不变，但验收句应加一句前提，免得被读成「今天跑 check 的结果」。

## Code-Resolved Questions（**建议三条全部移出停轮队列**：都能由代码/实测带 `文件:行号` 定案）

- **Q1〔候选集合的口径〕→ 只能是「逐字 ∪ 紧规则近义（③）」——① 被实测否掉，② 只剩「边界不可解释」这一条反对理由，用户没有可拍的板。**
  证据: `src/witnessloop/evidence.py:144-145`（`sections.get(OPEN_QUESTIONS_TITLE) or ""`）；我的复现: **① 之下 §1.5 的空壳洞仍然是绿的**（`0` 条），⇒ ① 直接违背 `proposal.md:49-51` 的目标 2（「只把『缺失』判红是不够的」），不是「代价较大」而是**不闭合**；③ 与 ② 的存量代价**都是 0**（63/8 两份语料）；两者的分野只在边界：② 会把 `## 逐条对抗（… / Open Questions）` 这类标题也算成小节（`design.md:166` 已用「结尾短语」这一条把它排除）。⇒ 三条里两条被实测排除，剩下的 ③ 是本稿已经写进 `spec.md:29-40` 的那一条。
  **残余代价（要写进文档、不要拿去问用户）**：界是**启发式**——`## Open Questions 汇总` 红（但带 D4 的一步可达提示）、`## Open questions`（小写）红、`## Open  Questions`（双空格）红。这是 `design.md:169-171` 已声明的「诚实边界」，我的实测把它的**具体形态**补齐了（见 §必须修改项 M3）。
- **Q2〔逐字小节 + 近义标题并存，要不要额外红〕→ 不红。并集已经让「漏 Q」不可能发生，而「要红」在本仓会撞上一份**不能再改**的证据。**
  证据: 本仓 `archive-awareness/reviews/grill-design.md:61`/`:110` 的真实形态，在 ③ 下**绿**（我复算: 候选 = 两节、Q 取并集 = `[1,2]`、`## User Confirmation` 有 `Q1`/`Q2` ⇒ 0 条）；该报告被 `archive-awareness/reviews/grill.manifest.json` 以 `report_hash` 绑着、且那份归档 move 已经合入 `origin/main`（`ef8b3ab`）⇒ 选「要红」等于要求改一份**已被哈希绑定、已归档**的证据（改完还要重建 manifest + 补 `protected_path_write` 事件，`archive-awareness/tasks.md:143-150` 记着这条链）。⇒ 收益为 0、代价是一条跨不过去的补救链。
- **Q3〔跨仓处置那份非逐字报告〕→ 只给医嘱、不碰别人的仓；而且它比立项稿说的更**不需要**动。**
  证据: 该报告在 ③ 下**今天就是绿的**（`/home/happy/wl-review-a/.../2026-09-30-workflow-dry-run/reviews/grill-design.md` ⇒ 0 条 finding）；该检出里 `*.manifest.json` = **0 份** ⇒ 它今天**连门禁都不进**；它若被绑定，任何事后改写先撞 `report_hash`（见「订正 3」）。⇒ 「现在改」没有任何门禁收益。

## Open Questions

> 标题**逐字**（这正是本 change 要求的那一条；上一稿我把它写成带括号的限定语，实测在**今天**的判据下会让本节**整段静默跳过**——如实记在这里，作为「产出方必须逐字」的第一个实例）。

- **Q4**: **「残留洞」的接受面**——把真问题**藏进一个不含 `Open Question` 字样的标题**（**尤其是模板自带的 `## Code-Resolved Questions`**）就仍然绿；这条边界要不要由用户明确接受（本稿推荐：**接受**，并把它按下面的措辞写进 `spec.md` 的边界声明）。
  - **具体例子（本 change 的真实场景，可直接复跑）**：取接入方那份真实报告，做**两处**改动——① 把 `:46` 那个带括号限定语的近义标题改成 `## Code-Resolved Questions`（模板 `templates/grill.md:104` **自带**的小节名，语义上「由代码定案」）；② 另起一个**逐字**的 `## Open Questions`，正文写 `（无）`。⇒ 新语义下 **0 条 finding（绿）**，尽管它原来在近义小节里声明的那几条问题**一条都没被列为「待用户拍板」**。
  - ⚠️ **这个例子的措辞本身是有意为之**：本节正文里**不能**出现 `Q` 加数字的字面（连引用原报告标题里的那串编号也不行），因为 `evidence.py:34` 的 `\bQ(\d+)\b` 会把**候选小节正文里的任何编号**变成「必须被用户确认」的要求。本文件的第一稿正是在这里引了原报告标题的编号 ⇒ 判据当场多报三条「未经用户确认」（实测输出是三条额外的「未经用户确认」，编号来自被引的那串数字），把**本节唯一那个真问题**淹在里面。⇒ 这是 R4 的一个**活样本**，也是本次评审自己踩到、又自己修掉的。
  - **为什么我推荐「接受」而不是「加判据」**：唯一能堵住它的机械办法是「**报告里任何位置的 `Q<n>` 都必须被确认**」，我**实测**了它的代价——接入方 **新红 4 份**、本仓 **新红 1 份**（`archive-awareness`），红点来自 `## 风险` / `## Round 3` / `## Review Notes` / `## Code-Resolved Questions` 里的**散文提及**（R4 放大到全篇）。⇒ 代价 > 收益，且会让「哪些编号要确认」变成不可解释的规则。
  - **如果用户不接受**：可选的收窄是「候选集合 = 逐字 ∪ 紧规则近义 ∪ **模板自带小节名**（`Code-Resolved Questions` 除外）」——即**只**把 `## Open Questions 汇总` / `## Open questions` 这类**近义但差一点**的写法也纳入候选（代价实测 0），把「换成语义无关的标题」这条**留在**洞外。这条我**不建议**默认选（它把 D2 从「可判定的紧规则」退回到「猜标题像不像」），列出来只是为了不让用户以为只有「接受 / 全篇扫 Q」两个极端。
  - ➡️ **我的推荐答案**：**接受残留洞**，并把这句写进 `spec.md` 的边界声明 2：**「本门禁保证**声明在该小节里**的问题都拿到确认；不保证**没有**被声明的问题——把问题写进别的小节（包括 `## Code-Resolved Questions`）不在机械面的覆盖内，那是流程与对抗轮的事。」**
  - ⚠️ 这一条是本审阅者**新提**的（立项稿的三条 Q 我都建议移出停轮队列）。若主流程判它「已在 `spec.md §边界声明` 里声明过、无需用户再拍」，则本 change **可以没有停轮项**——但那样也请把「Code-Resolved 是藏身处」这半句补进边界声明（立项稿只举了 `## 悬而未决的疑问`）。

## 风险

1. **R1（高·绕过面，**本 change 之外**但直接削弱它的立论）：`stage=grill` 的**正文判据只校验排序第一的那份 manifest**，加一份「排序在前」的诱饵 manifest 就能让**三条正文判据一起失效**。**
   实测（隔离副本，直调 `evidence.grill_evidence_findings_in_change`）: 一个 change 目录里放两份 `stage=grill` 的 manifest——`reviews/aaa.manifest.json` → `reviews/aaa-decoy.md`（10 行、三节逐字齐全、`## Open Questions` 写 `（无）`）、`reviews/zzz.manifest.json` → `reviews/grill-design.md`（**本 change 要修的那种报告**：非逐字标题 + `## User Confirmation` 空、正文里有 Q1）⇒ `grill_evidence_findings_in_change` 返回 **`[]`（0 条）**；把诱饵拿掉、单独校验那份真报告 ⇒ **1 条**（`Open Question Q1 未经用户确认`）。**今天与 ③ 之下都一样绿**。
   成因（`src/witnessloop/evidence.py:197-210`）：`matching` 取全部候选，但随后 `_, doc = matching[0]` 只用**排序第一份**；其它 manifest 只过 hash/绑定/孤儿（`contract.py:315-345` **逐份**校验，不禁止同 stage 重复）。⇒ 这与本仓自己写下的原则**直接冲突**（`contract.py:276-278`：「**绝不**因此跳过整条孤儿规则……原则是**宁多报不漏报**」）。
   严重性: 攻击要真绿，攻击者得会跑 `manifest build --stage grill --report reviews/aaa-decoy.md`——**这恰好是作者本人**，不是外部攻击者。⇒ **不阻塞本 change 的语义选型**（D1/D2 与它正交），但它意味着「让这条判据 fail-closed」之后，判据仍可被一份 10 行文件整体关掉。**建议本 change 顺手收掉**（见 M2）；若判为跨 scope，必须**显式**写进 spec 的边界声明并在 issue 里留痕，否则文档会声称一个不成立的性质。
2. **R2（中·自伤面）本 change 的收尾比 `design.md R5` 说的更容易踩。** ① 它自己的 grill 报告必须含**逐字** `## Open Questions`（本文件已做到，见 `## Reviewer` 上方的方法栏）；② 报告的文件名必须在**三处**（`tasks.md:94`、`tasks.md:99`、`design.md:307`）统一，否则孤儿规则会红（见 M1）；③ 写这份报告时，**候选小节正文里提任何 `Qn` 都会被要求确认**（`evidence.py:147`）——本文件因此刻意**没有**在 `## Open Questions` 里写 `Q1`/`Q2`/`Q3` 的字面，只用「上文 Code-Resolved 三条」指代。
3. **R3（中·实现自由度）D2 的规则里有三处**未定死**，实现者各写各的就会各红各的。** 实测边界（我的原型，全角/半角括号都剥、剥多轮）: `## Open Questions (remaining)`（**半角**括号）✅ 候选；`## Open Questions（A）（B）` ✅；`## Open Questions 汇总` ❌（红 + 提示）；`## Open questions` / `## open questions` ❌（红，**且 D4 的提示也不出现**，因为提示用的是**大小写敏感**的子串 `Open Question`）；`## Open  Questions`（双空格）❌（红，同样无提示）；`## Open Questions：`（全角冒号）❌（红，**有**提示）；`## Non-Open Questions` ✅（被当成候选——fail-closed 方向，但说明 (b) 的 `(?:\S+[- ])*` 前缀比直觉宽）。⇒ 见 M3。
4. **R4（中·`_sections()` 不跳代码围栏）——**引用**会**真的**创建小节。** 实测: 一份报告把 `## User Confirmation` + `- **Q1**: 用户答复：甲；确认时间: …` 写在 ```markdown 围栏**里**（没有围栏外的那一节）⇒ `_sections()` 的 keys 里就**有** `User Confirmation`、确认**被取到**、判据 **0 条（绿）**；镜像地，围栏里贴一段含 `## Open Questions` + 示例 `Q1` 的模板片段 ⇒ 多出「Q1 必须被确认」的要求。**非本 change 引入**（`evidence.py:52-64` 从未跳过围栏），但本 change 把「必须有该小节」变成硬要求 ⇒ 值得在边界声明里写明；改 `_sections()` 属本 change 明确的非目标（D6），不建议顺手改。
5. **R5（低·`②` 的反例只会迟到不会缺席）**：本仓已经在 `grill-adversarial-gate/reviews/grill-adversarial.md:21` 出现过 `## 逐条对抗（… Open Questions）` 这种标题；今天它**不在**正文被校验的报告里（所以 ② 的误伤为 0），但**没有测试**挡住「它下次出现在 grill 报告里」。⇒ M3 的正反用例（`spec.md:51-58` 的两条 Scenario）必须**逐字**落成测试，否则下次「顺手放松一点」会静默退化（`tasks.md:18-20` 的 A3/N6 就是这个钉子）。
6. **R6（低·诊断文案）**：D4 会把**所有**含 `Open Question` 字样的标题内嵌进一行 message（去重排序）。接入方语料里最多 1 个、本仓最多 1 个，但语义无关的标题（`## 逐条对抗（…）`、`## Code-Resolved Questions` **不会**入列）会一起出现 ⇒ 文案长度可控。`design.md R6` 的判断成立；F7 钉排序是必要的（候选集合从 `dict` 的 key 派生，我实测 `_sections()` 返回的顺序是插入序）。

## 必须修改项

- **M1〔中·`tasks.md:94`、`tasks.md:99`、`design.md:307`〕**：三处把本 change 自己的 grill 报告写成 `grill-review.md`，而本仓**最近一次**的产物名是 `reviews/grill-design.md`（`archive-awareness/reviews/grill.manifest.json` 的 `report_path` 就是它；本次评审的交付路径也是它）。`contract.py:315-345` 的孤儿规则要求 `reviews/**/*.md` 里**每份**报告都被某份 manifest 的 `report_path` 引用 ⇒ 若 G3 照字面去写/新建 `reviews/grill-review.md`，要么多出一份未绑定报告（红），要么把确认写进了没人绑的文件。**改法**：三处统一成 `reviews/grill-design.md`（`templates/grill.md:91` 既有的「`grill-review.md`（即 `grill-design.md`）」等价说法保留在**模板**里即可，本 change 的 tasks/design 按**实际文件名**写），并在 G1 里点名 `manifest build --report reviews/grill-design.md`。
- **M2〔中高·`src/witnessloop/evidence.py:197-210`〕**：`stage_manifest_findings_in_change` 只用**排序第一份** `stage=<stage>` 的 manifest 校验正文 ⇒ 加一份排序在前的诱饵（绑一份 10 行的合规报告）即可让 `grill` 的三条正文判据**整体失效**（我在隔离副本实测: 诱饵在场 `0` 条、拿掉诱饵 `1` 条）。**建议改法**（与本 change 同一文件、约 3 行）：对 `matching` **逐份**都跑正文判据（`reason` 文案不变），`label` 带上那份 manifest 绑定的相对路径以便定位；这与 `contract.py:276-278` 写下的「宁多报不漏报」一致。**代价实测为 0**：本仓 8 个 change 每个 stage 恰好 1 份 manifest、接入方两份语料 0 份 manifest ⇒ 不会新红任何存量。若作者判定跨 scope，则**必须**在 `specs/open-questions-gate/spec.md` 的边界声明里写明「同 stage 多份 manifest 时只校验其中一份」并立项 issue——否则 `spec.md:6` 那句「不再能被绕过」会被读成它覆盖不到的范围。
- **M3〔中·`specs/open-questions-gate/spec.md:33-40`、`design.md:154`〕**：D2 的规则写成「去掉标题**尾部的括号限定语**后匹配 `^(?:\S+[- ])*Open Questions$`」，但**括号种类 / 大小写 / 多轮括号**都没定义，实现者会各写各的。**改法**：在 spec 里补三句可判定的话 + 每句配一个例子（用我实测的形态）: ① 括号**全角 `（）` 与半角 `()` 都认**（`## Open Questions (remaining)` ⇒ 候选）；② 标题匹配**大小写敏感**（`## Open questions` ⇒ 非候选、**红**，且此时 D4 的附加提示**不出现**——提示同样大小写敏感——文案要让作者能想到是大小写问题）；③ 连续多个尾括号**全部剥掉**（`## Open Questions（A）（B）` ⇒ 候选）。这三句要同时进 N 系列否定/正例用例（`tasks.md:18-20` 的 A1 表格按同一口径扩三行）。
- **M4〔低·`specs/open-questions-gate/spec.md:150-170`（边界声明）〕**：补两条**机制性**边界（都非本 change 引入，但本 change 让它们变得要紧）: ① 「`_sections()` **不跳过代码围栏**（`evidence.py:52-64`）⇒ 报告里**引用**一段含 `## User Confirmation` 的示例会被当成真小节、引用一段含 `## Open Questions` + `Q1` 的示例会**增加**待确认项」（实测见 R4）；② 「候选小节**之外**的 `Q<n>` 不进入判据（`evidence.py:147`）⇒ `## Code-Resolved Questions` 是模板自带的、合法的『藏身处』」（见 Open Questions Q4 的例子）。两条都**不改代码**，只把「机械门保证什么」写准。

## User Confirmation

- **Q4**: 用户答复：**接受**——机械上更狠的做法（「报告里**任何位置**出现的 `Q<n>` 都必须被确认」）实测的代价是接入方新红 4 份、本仓新红 1 份，红点全是正文里的散文提及，那是**把准确率换成覆盖面**、且会让人学会无视报警；兜底不只有「模型自觉」，而是**流程强制的三层**（零记忆、专事证伪的对抗轮 ＋ 独立审阅者 ＋ 人读最终报告）；「接受」的含义就是**把这个洞写进规格的边界声明**——从「未知」变成「已知且书面声明」。；确认时间: 2026-10-15
