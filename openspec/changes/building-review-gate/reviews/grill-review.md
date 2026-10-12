# Grill: building-review-gate 设计追问

## Reviewer
- run id: `grill-reviewer-building-review-gate-2026-10-12`
- 时间: 2026-10-12T04:45:13Z
- 方式: 独立零记忆审阅者。逐条打开 design 引用的 `文件:行号` 自核；能实测的在本 worktree 的 `/tmp` 副本上按 design 真打补丁跑全量测试（副本已删，本仓 `git status` 干净、不 commit）。**挑战而非确认。**

## Confirmed Decisions

- **决策（D-A）**：触发条件选 `policy.require_change_for`（客观 git 事实）而非 asterwynd 的 `_tasks_all_complete`（自声明），**是对的**。理由：asterwynd 的 `_tasks_all_complete` 判据是 `checked > 0 and unchecked == 0`（`scripts/check_openspec_artifacts.py:1014-1040`），**不勾选即绕过**；`require_change_for` 来自 `git diff --name-status base...head`（`gitutil.changed_files`，`src/witnessloop/gitutil.py:99-111`），agent 改不掉。
  来源: `grill-reviewer-building-review-gate-2026-10-12`

- **决策（D-B）**：「审阅须发生在最终实现之后」这一半**已经存在**，design「只补存在性那一半」成立。理由：`contract._check_git_span`（`src/witnessloop/contract.py:272-352`）对**每一份** manifest 判 stale（`contract.validate_review_manifests` 逐份调用，`contract.py:139-140`），与 stage 无关。**实测复现**（`/tmp` 副本，S1b）：造 change + `stage=grill`+`stage=building` 两份 manifest，之后只改一行 `src/app.py` 并提交 ⇒ `check` 退出 1，两条 finding 分别点名两份 manifest「审阅的是旧 revision：head_sha=… 之后又改动了非证据文件：src/app.py」。
  来源: `grill-reviewer-building-review-gate-2026-10-12`

- **决策（D-C）**：§1 的「verdict / 轮次记法」表**属实**，逐份打开确认。理由：`dogfood-bootstrap`（顶层 `## Verdict` = CHANGES_REQUESTED，`reviews/building-review.md:13-15`；`## 第 2 轮审阅` + `- 裁定: **PASS**`，`:124-127`；`## 第 3 轮审阅` + `- 裁定: **PASS**`，`:179-182`）、`grill-evidence-gate`（顶层 CHANGES_REQUESTED，`:8-10`；`## 第 2 轮审阅` + `- 裁定: **PASS**`，`:158-161`）、`guard-crash-exit`（顶层 PASS，`:9-10`；`# 第 2 轮（R2）`，`:113`；`## Verdict` + `**PASS**（无阻塞项）`，`:121-122`）。⇒ 顶层 Verdict **常是第 1 轮**的、轮次记法**三种并存**——任何「读顶层 Verdict」的机械判据都会误伤本仓历史。
  来源: `grill-reviewer-building-review-gate-2026-10-12`

- **决策（D-D）**：**自伤面实测 ≈ 0**；design D6/R1 的「一批既有用例会变红」**不成立**（被证伪）。理由：在 `/tmp` 副本按 design §3 真打补丁（`constants.DEFAULT_BUILDING_STAGE` / `policy.evidence.building_stage` / 参数化 `evidence` 助手 / `checkcmd` 循环接入）后跑全量 = **404 passed**，与基线 **404 passed** 逐条相同（**0 条新增失败**）。根因：D1 触发条件 = diff 触及 `require_change_for`；既有用例里凡触及 `src/**` 的（`commit_content(spec_writes=...)`、`write_artifact("src/...")`）**都已**写了 building 证据（`commit_evidence` 默认 `stages=("grill","building")`，`tests/helpers.py:214`；`write_review` 默认 `stage="building"`，`helpers.py:116`）；只写 `stage="grill"` 的用例（`test_check_grill_evidence.py`、`test_orphan_reports.py` 等）**只动 change 目录**，不触及 `require_change_for` ⇒ **不触发**。tasks.md C1「逐条修既有用例的期望」因此会**空转**。
  来源: `grill-reviewer-building-review-gate-2026-10-12`

- **决策（D-E）**：与 asterwynd 的先例对比**实质成立**（行号有漂移）。理由：`_check_review_manifests`（**实际在** `scripts/check_openspec_artifacts.py:1110-1145`，design 写的是 `:1009-1048`）= `requires_building_review = (not archived and change_type.primary != "docs" and _changed_capabilities(change_dir) and _tasks_all_complete(change_dir))` + `if requires_building_review and not review_report.exists()`，与 design 引文逐字一致；全文件 grep 无 verdict/PASS 解析逻辑，`:1122` 注释的 “produced a PASS manifest” 指**被 manifest 绑定的证据**，不是文本判据。⇒ 「PASS 硬门 = 闭环必须跑过」的解读正确。
  来源: `grill-reviewer-building-review-gate-2026-10-12`

- **决策（D-F）**：共用助手（design §3 ⚠️）的切法 = 参数化 `verify_body` 开关。理由：现存 `evidence.grill_evidence_findings_in_change`（`src/witnessloop/evidence.py:172-229`）**顺带**做了 grill 专有的正文校验（`evidence.py:229` 调 `grill_evidence_findings`），而 building **只要求存在**。切点应落在「报告**存在性**」与「正文判定」之间：抽出 `stage_manifest_findings_in_change(change_dir, *, stage, manifest_glob, label, verify_body=False)`——`verify_body=False` 时执行到「报告解析得到且 `is_file()`」为止（对应 `evidence.py:207-212` 那段）就返回；grill 分支传 `verify_body=True` 才走到 `:218-229` 的正文读点。**一处实现、两种深度**，满足 spec「共用同一实现」且**不泄漏** grill 正文判据给 building。实测：此切法下 `building` manifest 绑一份无 `## Confirmed Decisions` 的普通报告 ⇒ 通过；grill 分支行为不变（404 passed 含全部 grill 用例）。
  来源: `grill-reviewer-building-review-gate-2026-10-12`

## Code-Resolved Questions

- **D1 触发条件会不会误伤「另一个 change 只改了 `design.md`」？** → **会**（实测 S2′）。
  构造：PR 改 `src/a.py`（实现 change `impl-a`，有 building 证据）+ 新增 change `b-doc`（**完整 change 目录、无实现**）且 `b-doc` 只有 grill 证据 ⇒ `check` 退出 1，finding 之一 = `openspec/changes/b-doc：无 stage=building 的 manifest（现有 stage：grill）——本 change 需要这个 stage 的审阅证据`。机制：D1 触发是**全局**的（design D1 与 `_code_hits(pol, changes)` 只看「本次 diff 是否触及 `require_change_for`」），而 building 要求施加在**每个** `change_id` 上（design §2 D2「`check` 的 change 循环里」；`checkcmd.py:73-84` 的循环）。**这直接违反 design D1 自述的边界**（「纯文档 / 纯 change 目录改动 ⇒ 不要求」）——单 change 时该边界成立，多 change 同 PR 时**被打破**。（证据：`/tmp` 副本实测；`checkcmd.py:73-84`、`checkcmd.py:92-120`）
- **`require_change_for=[]` 会不会让门禁静默失效？** → **会**（实测 S4′）。用 `init --policy` 写 `require_change_for: []`，PR 改 `src/app.py` + change 只有 grill 证据 ⇒ `check` **绿**（exit 0）。机制：`policy.py:92-100`（显式 `[]` 关掉该规则）⇒ `_code_hits` 空集 ⇒ `requires_building=False`，**同时** `_require_change`（`checkcmd.py:98` `if change_ids or not pol.require_change_for: return []`）也失效 ⇒ **整条「改代码必须挂 change」的门禁连同 building 一起失效**。（证据：`/tmp` 副本实测 S4′）
- **只改 `tests/**` / `docs/**` ⇒ 不要求 building，对吗？** → **对**（实测 S3）。默认 `require_change_for` 不含二者（`constants.py:27-36`），故 building 门禁**未触发**。但注意：若在证据提交**之后**再动 `docs/`/`tests/`，仍会被 `_check_git_span` 判 stale（S3 实测 exit=1，因 `docs/note.md, tests/test_x.py` 是非证据 stray）——那是**既有**行为，非本 change 引入。（本仓自己的 `require_change_for` 另含 `templates/**`/`plugin/**`，见 `.witnessloop/policy.json`。）
- **正面验收：默认 policy + 改 `src/` + 只有 grill ⇒ 真要求 building 吗？** → **是**（实测 S5）。exit=1，文案点名 `openspec/changes/add-x：无 stage=building 的 manifest（现有 stage：grill）`。
- **抽参数化助手会不会撞既有断言？** → 不会。唯一断言阶段文案的用例是 `tests/test_check_grill_evidence.py:53`（断言 `现有 stage：grills`），参数化后仍保留。**但**：抽参后 grill 分支原本的文案 `grill 决策记录必须有对应的审阅证据`（`evidence.py:203`）会变成通用措辞（我补丁里改成「本 change 需要这个 stage 的审阅证据」）——需在实现时确认可接受，否则等于给两 stage 各写一套文案 = 变相两份实现。
- **design §1「`building` 这个 stage 在 `src/` 里 0 命中（全树 grep）」** → **字面不成立**：`grep -rn building src/` 命中 `src/witnessloop/cli.py:107`、`:111`（均为 `--help` 文案）。**实质成立**：无任何判定/逻辑 gate 在 `stage=building` 上。建议 design 改为「0 处**功能性**命中」。
- **asterwynd 跨仓行号引用** → 有漂移：design 引 `:1009-1048`，实际函数在 `:1110-1145`；引 `:1409` 的「post-PASS tasks edits」，实际在 `:1716`。建议按**函数名**引用，不按行号（跨仓行号随对方 git 漂移即失效）。
- **`docs/gate.md` 的节号** → design D5 引 `§6`（check 退出码表，`docs/gate.md:257-267`）与 `§8`（grill 证据正文校验，`docs/gate.md:302-343`）**均正确**。

## Open Questions

- **Q1（design Q1）verdict 文本是否机械判 PASS——甲（不解析）还是乙（要求最终裁定 = PASS）？**
  具体例子：本仓 3 份历史 building 报告的**最终裁定**形态**不一致**——`- 裁定: **PASS**` ×2（dogfood-bootstrap `:127`/`:182`、grill-evidence-gate `:161`）与 `## Verdict` + `**PASS**（无阻塞项）` ×1（guard-crash-exit `:121-122`）。⇒ 选乙必须先**规定**一种机器可读的最终裁定形态并**回填这 3 份**。且乙与 `templates/review-loop.md:99-100`「到第 3 轮仍 CHANGES_REQUESTED ⇒ **停下**向用户报告、升级到人判断」**直接冲突**：机械「最终裁定必须 PASS」与「人可决定照合」不可兼得，除非再加一层 `## Human Override`——而覆盖是**自由文本**，落在「防漂移不防伪造」边界外，等于又一个可手写的绕过面。
  - ➡️ **推荐答案**：选**甲**（不解析 verdict 文本）。与 asterwynd 先例一致，避开「格式规范 + 历史回填 + 覆盖机制」三笔成本，且乙的覆盖**无法机械防伪造**、收益打折。**若**最终仍要乙，我的规范建议：报告**末尾**必须有一行 `- 裁定: **PASS|CHANGES_REQUESTED|BLOCKED**`（取**最后**一处匹配，历史轮次降为子节），且「封顶交人」的出路必须是**被某份 manifest 绑定**的一份 `reviews/<stage>-override.md`（而非报告内自由文本），否则覆盖层形同虚设。

- **Q2（design Q2 + 新发现的误伤）触发句「该 change」到底指谁？多 change 同 PR 怎么办？**
  具体例子：Q1 的 S2′——一个 PR 改了 `src/a.py` 并顺带新增了另一个（仅文档、无实现的）change `b-doc`；`b-doc` 因「本 PR 碰到了代码」而被要求 building 证据（误伤）。design 只覆盖了**单 change** 的边界（D1「纯 change 目录改动不要求」），未覆盖「**本 PR 同时**有代码改动 + 别的 change」的多 change 情形。
  - ➡️ **推荐答案**：**不要**去猜「代码属于哪个 change」（witnessloop 无此概念，硬做会引入第二套「什么算代码」的口径，正是本仓忌惮的）。改为**显式化流程约束**：把「一个 PR 推进一个 change」写成前提（与既有的「内容/证据分属两提交、单提交 PR 不被支持」同族，`docs/gate.md:172-177`），并在 spec 里**加一条 Scenario 把多 change 的边界钉死**——「本 PR 触及 `require_change_for` ⇒ 本 PR 触及的**每个** change 都要 building 证据；要免除就把 change 拆到单独 PR」。这比加 `building_exempt_changes` 豁免名单更好——豁免名单是**新的绕过面**。

- **Q3（design Q3）对既有接入方的行为变更怎么落：只写文档，还是过渡开关？**
  具体例子：某接入方已有一个只跑了 grill 的 in-flight change，接上新版本后 `check` 首次变红。
  - ➡️ **推荐答案**：**只写文档**（`README.md` + `docs/gate.md §8` 增一节「building 门禁的触发与判据」+ 明确「对**接入方**是行为变更」），**不加过渡开关**。开关=新的静默绕过面（与 R5 同族）。确有 in-flight change 就补跑 review-loop，而非关规则。口径照抄 `grill-evidence-gate` 那次的行为变更声明（`README.md:103-106`）。

- **Q4（新）R5 的严重性：`require_change_for=[]`（或未覆盖真实代码路径）让门禁静默失效——只写文档够吗？**
  具体例子：某 monorepo 接入方把 `require_change_for` 留成 `[]`、或只写 `src/**` 而其真实代码在 `services/**` ⇒ 整条「改代码必须挂 change」的门禁（**不只是 building**）连同新的 building 门禁**一起静默通过**（S4′ 实测 exit 0）。
  - ➡️ **推荐答案**：把 R5 从「低」**升为「中」**，并**至少在 `docs/gate.md §2` 与 spec 里显式声明**：`require_change_for=[]` 关掉的是**整条代码门禁**、不是仅 building。是否再加一条「`require_change_for` 为空时 `check` 报 warning」请用户定——注意这会让 `tests/test_require_change.py::test_empty_require_change_for_disables_the_rule` 从绿变红，是要**有意**改的既有契约，不是 bug。

## 风险

- **R-new-1（高，Q2 未决前）**：D1 全局触发 ⇒ 多 change 同 PR 时误伤提案期 change（S2′ 实测）。这是 design **自己边界（D1）的自相矛盾**，须在实现前定位：要么改触发，要么显式声明边界 + 「一 PR 一 change」前提。
- **R-new-2（中）**：自伤面被**高估**（D6/R1、tasks C1）。实测 0 条新红。若按「一批」投入盘改既有用例，会**误判进度、浪费修改**；C1 应缩为「确认无需改动」+ 仅新增正向/负向用例。
- **R-new-3（中）**：抽参数化助手会让 grill 分支的报错文案变通用（`evidence.py:203`）；若不接受，就只能给两 stage 各写一套文案 = **变相两份实现**，与 spec Req「共用同一实现」冲突。二选一须在实现里定。
- **R-new-4（中）**：`require_change_for=[]` / 未覆盖真实代码 ⇒ 门禁**静默失效**（R5，S4′ 实测）。非 building 独有，是**整条代码门禁**的逃生面；「机械强制」的卖点在最省事的一步配置上即可归零。
- **R-new-5（低，边界须诚实）**：building 门禁只保证「**有一份可绑定的 manifest 存在**」，**不保证**真跑了独立 run——兜底路径下 `reviewer_run_id ≠ author_run_id` **结构性恒真**（`docs/gate.md:121-123`），一个 agent 即可自造 manifest 满足它。故 proposal 的「从自觉变机械」应限定为「**证据存在性**机械、**审阅真实性**不机械」（与 grill 同一边界），别让读者以为它机器验证了「独立」。
- **R-new-6（低）**：asterwynd 跨仓引用按行号（漂移已实测）——改按函数名引用。
