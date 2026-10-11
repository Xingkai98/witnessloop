# Grill: grill-evidence-gate 设计追问

> 独立零记忆审阅者产出。算法与产物格式依据 `templates/grill.md`（第 3–5 步）。
> 本文件只做设计求完备：能由代码/规格判定的**自行定案**，真正需要人取舍的留成 Open Questions。
> **不做**第 6 步（停轮）与第 7 步（整合 design）。第 5 步的**独立对抗验证报告**（`grill-adversarial.md`）
> 由**再另起一个 run** 产出——本次的证伪尝试已尽量内联进下面各条（每条都是「先试推翻、推不动才确认」），
> 但**另一次独立证伪仍是必要下游步骤**，别把它省掉。

## Reviewer

- run id: `grill-reviewer-grill-evidence-gate-2026-10-11`
- 时间: 2026-10-11T11:36:44Z
- 读到的只读事实源：本仓 `src/witnessloop/*.py`、`templates/grill.md`、`plugin/`、`tests/`、
  `openspec/changes/dogfood-bootstrap/reviews/grill-review.md`、`docs/gate.md`、`docs/design.md`，
  以及 **asterwynd 真身源码**（`/home/happy/my-agent/scripts/workflow_guard.py`、`scripts/check_openspec_artifacts.py`）
  与 Claude Code 官方 hooks 文档。**asterwynd 本 workspace 里确实没有，但在 `~/.` 之外的本机找到了真身**——
  design 的移植断言因此**可以核实**（结论见 CD3/CRQ1，其中一条被证伪）。

## Confirmed Decisions

> 逐条**先证伪再确认**。每条给出「核到了什么」，不是复述设计。

- **决策（D1 判据成立，且已有测试在钉）**：`## Confirmed Decisions` ≥3 条、每条带 `来源:` 是**既有硬门槛**，
  不是本 change 新造——`templates/grill.md:101-102` 与 `:116`、`:201` 明写，且
  `tests/test_templates.py:158-162`（`test_grill_evidence_has_a_hard_format_threshold`）断言模板里含
  `3 条` 与 `来源:`。⇒ D1 的判据 1 有出处、可移植。
  理由（证伪尝试）：本 change 若把判据写成别的东西就会与模板/测试漂移；核到模板与测试都锚在「3 条 + 来源:」，
  故 D1「落到 witnessloop 的措辞」是**收敛到既有口径**，不是发明。来源: `grill-reviewer-grill-evidence-gate-2026-10-11`
- **决策（#2 属实）**：`check` **确实完全不读报告正文**——`contract.validate_review_manifests`（`contract.py:121-149`）
  只做「manifest 存在 / hash 绑定 / reviewer≠author / 孤儿绑定」；报告的唯一消费点是 `_check_hashes`（`contract.py:355-394`），
  它对 `report_path` 只算 `sha256_tree(report_path)`（`:371`），**从不解析小节**。`Confirmed Decisions` /
  `Open Questions` 两串在 `src/` 为 0 命中；`来源` 虽在 `contract.py:62`（docstring）与 `initcmd.py:125` 出现，
  但那是**文本巧合**，`check` 从不**消费** `来源` 语义——结论成立，措辞已校正（对抗验证 #5）。
  ⇒ 一个空 `grill-review.md` 只要被 manifest 绑上就过门禁——`#2` 成立。来源: `grill-reviewer-grill-evidence-gate-2026-10-11`
- **决策（D2 事实成立，但行号错、且比设计说的更脆）**：`--stage` 值域**任意**（`cli.py:90` 只给 help「如 grill / building」，
  无 `choices`），`manifest build` 把 `args.stage` **原样**写进 manifest——**但字段在 `manifestcmd.py:137`，不是设计所写的 `:136`**。
  更关键：`stage` **不在** `REVIEW_MANIFEST_REQUIRED_FIELDS`（`constants.py:61-70`）——即 `check` **今日根本不校验 `stage`**。
  ⇒ D2 依赖的定位键是「**写而不校**」的自由字段（历史/手写 manifest 可缺 `stage` 或值任意）。来源: `grill-reviewer-grill-evidence-gate-2026-10-11`
- **决策（D4 死锁规避成立，对 witnessloop 自身 policy）**：guard 的触发面 = `policy.require_change_for`，
  本仓该值为 `["src/**","templates/**","plugin/**"]`（`.witnessloop/policy.json:8-12`），且与 `check._require_change`
  **同源同字段**（`checkcmd.py:98`）。写 `reviews/**`、`openspec/changes/**`、`docs/**`、`tests/**` **都不命中**
  ⇒ 产证据的写操作（写报告、跑 `manifest build` 写 manifest）**永不被拦**，不存在「写不出证据」的死锁。
  asterwynd 同款豁免见 `workflow_guard.py:517-531`（`_is_change_doc_write` 放行 change 目录内 `proposal/design/tasks/specs/reviews`）。
  来源: `grill-reviewer-grill-evidence-gate-2026-10-11`
- **决策（D6 的 schema 今日已可定案，不必留到实现期）**：CC plugin 的 hooks **就是** `plugin/hooks/hooks.json`
  （官方文档：插件启用时其 hooks 与用户/项目 hooks 合并；可选顶层 `description`）+ `${CLAUDE_PLUGIN_ROOT}` 占位符。
  结构 = 事件 → matcher 组 → handlers，例：`{"hooks":{"PreToolUse":[{"matcher":"Write|Edit","hooks":[{"type":"command","command":"…"}]}]}}`。
  PreToolUse stdin 是 JSON，含 `tool_name` / `tool_input` / `cwd`；**block 二选一**：(a) exit **2** + stderr 作理由；
  (b) exit 0 + `hookSpecificOutput.permissionDecision`（取值集 **`allow|deny|ask`**，**无 `defer`**——对抗验证 #2 校正）。⇒ D5 选 exit 2 与 D6 的「极薄 shim」方向**成立**；
  D6 的「⚠️ 待核实」可降级为**已定案**（但仍有 R7/R8 两个未覆盖点）。
  来源: `grill-reviewer-grill-evidence-gate-2026-10-11`
- **决策（D9 回归红线可满足——但**仅当 evaluator 不照搬 asterwynd 的解析**）**：本仓 `dogfood-bootstrap/reviews/grill-review.md`
  实测有 **6 条** `## Confirmed Decisions`（每条形如 `- **决策（Dn）**：…；来源: <run>`，6 条全带 `来源:`）
  与 Q1–Q6 六条 `## Open Questions`，且 `## User Confirmation` 有 Q1–Q6 六条 `…用户答复：…；确认时间: 2026-10-11`。
  ⇒ 按 D1 的三条判据判它 = **合格**，D9 的「必须仍绿」可满足（**驳回**「用 asterwynd 原样解析」的省事做法，见 CD3 与 CRQ1）。
  来源: `grill-reviewer-grill-evidence-gate-2026-10-11`
- **决策（D7 的「反转」在文档侧确实需要动，且无测试自动兜底）**：「hooks 只作 advisory/提醒」写在
  `docs/design.md:27`（§2 点 6）、`:145`（§9 风险 4）、`README.md:108` 与 `docs/reviews/grill-design.md:19`。
  反转后**没有任何漂移守卫测试**钉这处措辞（`test_docs.py` 只钉动词面 / run-id / 幂等三类，见 `test_docs.py:18,20,51,114`），
  ⇒ 漏改**不会**被 CI 抓住，只会留下一份「本仓卖点（文档不漂移）自我打脸」的文档。D7「须记 ADR」是对的，
  但**更紧要的是逐处同步 + 加一条守卫**。来源: `grill-reviewer-grill-evidence-gate-2026-10-11`

## Code-Resolved Questions

- **asterwynd 的 `_grill_evidence_missing()` 真身长什么样、能不能直接移植？** → **能核对，但**判据与 witnessloop 的格式**不兼容**，**不能照搬**。
  真身：`workflow_guard.py:364`（设计写的 `:363` 差 1 行）。它 (1) 先跳 docs-only（`primary: docs`，`:379-383`）与无 `specs/*/spec.md` 的 change
  （`:385-389`），(2) 读**硬编码** `reviews/grill-design.md`（`:391`）——**不是** `grill-review.md`，(3) 用
  `_extract_open_question_indexes`/`_extract_user_confirmation_indexes` 做**Q 编号**配对。事后判在
  `check_openspec_artifacts.py:739`（`_check_design_review_task`，设计写的 `:716-752` 实为 `:739-797`），其判据
  `_extract_grill_decisions`（`:883`）**只认前缀字面 `- **决策**：` / `- **决策**:`**，**不检查 `来源:`**。
  而**本仓** dogfood 用的是 `- **决策（D1）**：`（**「决策」与 `**` 之间夹了 `（D1）`**）⇒ 照抄 `:883` 的正则，
  本仓那份证据的 Confirmed Decisions 命中数 = **0** ⇒ **D9 回归必红**。
  ⇒ evaluator 的 entry-matcher 必须按 **witnessloop 自己的格式**重定（模板 `grill.md:101` 用 `- **决策**：…；来源: …`，
  而实际产出 `dogfood` 用 `- **决策（Dn）**：…；来源: …`——**两种都要算数**），且「每条带 `来源:`」是本 change **新增**的判据
  （asterwynd 无此判据）。证据：`workflow_guard.py:364,379-391,517-531`、`check_openspec_artifacts.py:739-797,874,883`；
  本仓 `dogfood-bootstrap/reviews/grill-review.md:16-48`（6 条决策）、`:158-168`（User Confirmation）、`templates/grill.md:101-102,116,201`。
- **「每条 Open Question 都要在 `## User Confirmation` 有对应确认」——配对机制是什么？本仓文件满足吗？** → 配对 = **Q 编号**（`Q1`↔`Q1`），
  验收形态是 `- **Qn**…：…用户答复：<非占位>；确认时间:…`（asterwynd `check_openspec_artifacts.py:874` `_unconfirmed_open_questions`
  + `workflow_guard.py:459-475`）。本仓 `dogfood` 的 User Confirmation 六条逐条符合该形态 ⇒ **配对通过**。
  **但**：设计 D1 只写了「占位文本（`待确认`/`待主 agent 提交`）不算确认」，**没有**把 asterwynd 那两张占位表
  （`_UNCONFIRMED_EXACT`/`_UNCONFIRMED_STRONG`，`check_openspec_artifacts.py:143-151`；`workflow_guard.py:409-417`）
  与「≤20 字才查强占位」的启发式落进 design。⇒ 判据的**具体字面集**未定（易漂移），见 OQ6。
  证据：`dogfood-bootstrap/reviews/grill-review.md:86-121,162-167`；`check_openspec_artifacts.py:143-151,874`；`workflow_guard.py:459-475`。
- **D9 与 D2 是否自洽？** → **措辞不自洽（须统一）**——对抗验证 #6 校正：原文「不能同真 / 必须二选一」**夸大**，
  D2 已自指「→ 见 D9 与 Open Question Q3」，更自然的读法是「D2 的脆弱点是 D9 的动机」。D2 说「stage 拼错（`grills`）⇒ 判定**静默失效**」；
  D9 说「`check` 要求**存在** `stage=grill` 的 manifest，缺则新增一条**红**」——若 D9 成立，拼错 stage ⇒ 缺 `grill` manifest
  ⇒ 净行为是 **`check` 红（响亮）**，不是静默。⇒ **D2 那句「静默失效」须与 D9 对齐**（净行为 = fail-closed 红，见 OQ3）；
  否则实现者可能把「无 `stage=grill` manifest」实现成**放行**，那就把 `#2` 的洞又开回来了。
  证据：`design.md:41-44`（D2）vs `:94-95`（D9）；`constants.py:61-70`；`cli.py:90`。
- **本 change 自己的 change 目录合契约吗？** → **不合**。`find openspec/changes/grill-evidence-gate` 只有 `proposal.md`、`design.md`；
  `required_artifacts` 要求 `proposal.md/design.md/tasks.md/specs/reviews`（`.witnessloop/policy.json:13-19`），`check` 缺件即红
  （`contract.py:97-100`）；`manifest build` 更早：`HASHED_ARTIFACTS` 硬要求 `tasks.md` 与 `specs`（`constants.py:55-58`，
  `manifestcmd.py:96-99`）。⇒ 实现期**必须先补** `tasks.md` 与 `specs/<cap>/spec.md`（`specs/` 空目录 git 不跟踪——见 R1）。
- **本 change 会打红哪些既有测试（自伤面）？** → **2 条硬红**（对抗验证 #5 校正：原文「至少三条」**过计**）：
  `tests/test_cli.py:48-52`（`test_the_verb_surface_stays_small`，断言 `set(sub.choices) == {"init","uninit","check","manifest"}`——加 `guard` 即红）；
  `tests/test_plugin.py:64-71`（`test_plugin_file_inventory_is_exactly_expected`，`EXPECTED_FILES` 恰为 4 个文件——加 `hooks/hooks.json` + shim 即红）。
  `tests/test_docs.py:42-46`（`test_docs_name_all_four_verbs`）**不会红**：它只断言四动词**存在**（`assert verb in text`），
  加第五动词 `guard` 后这四串仍在 ⇒ 通过；**只是措辞要同步**。
  ⇒ 设计的 §6「文档影响」**漏了前两条硬红**（这条成立且重要）。证据：`tests/test_cli.py:48-52`、`tests/test_plugin.py:20-25,64-71`、`tests/test_docs.py:42-46`。

## Open Questions

- **Q1（scope）** 本 change = `check` 正文校验（#2）+ `guard`+hook（B 轨），还是拆成两个 change？
  - ➡️ **推荐答案：合一个 change（采纳设计 Q1）。** 二者**共用同一个 evaluator**——拆开等于要么写两份判定（必然漂移，正是本仓最忌：
    `check` 与 `manifest build` 已因「两边各写一套」踩过坑，故共用 `constants.HASHED_ARTIFACTS`，见 `constants.py:52-58`），
    要么让后一个 change 依赖前一个（净增一轮证据开销）。
    **具体例子**：拆成「change-A：evaluator + 接 check」「change-B：guard + hook」。change-A 的 evaluator 落 `src/witnessloop/evidence.py`；
    change-B 要复用就得 import change-A 的产物——而 change-A 若尚未合并，change-B 的分支要么钉一个未合并的 commit、要么临时复制一份
    （漂移种子）。合一则一次落地、一次审。
- **Q2（D3 的 fail-open/fail-closed——**真问题不是「推不出」，是「推得出一个错的」**）** 分支不是 `<change-id>/<date>` 形状时怎么办？
  - ➡️ **推荐答案：fail-open 放行 + 显式提示**，**但必须补一条前置规则**：「由分支推得的 id，**必须命中一个现存的 active change 目录**
    （且不落在 `archive/**`），否则一律按『推不出』处理（fail-open）」。**理由**：设计只设想了「推不出 change id」（无 `/` 的分支），
    却漏了更常见的**「推得出但推错」**——任何形如 `feature/login`、`fix/123`、`dependabot/npm_and_yarn/x` 的分支，
    首段会被当成 change id → `openspec/changes/<首段>` 不存在 → guard 判「证据缺失」→ **误拦开发**（本地 fail-closed 的真实误伤）。
    **且这不是新设计**：asterwynd 的 `_current_change_id()`（`workflow_guard.py:332-361`）**正是**这么做的——
    `:348` `if (CHANGES_DIR / head).is_dir(): return head` ⇒ Q2 是**照搬已验证行为**，比自创更稳（对抗验证 #2 补强凭据）。
    **具体例子**：开发者开分支 `fix/login-timeout`，改 `src/auth.py`——首段 `fix` 不是 change 目录。若无「必须命中现存 change 目录」这条，
    guard 拦下，人被迫先建一个名为 `fix` 的 change 目录或设 `WITNESSLOOP_SKIP_GUARD=1`——正是 D8 想避免的「把人堵死」。
  - （次要）日期后缀：分支 `grill-evidence-gate/2026-10-11` 用「第一段」即可（change id 是单段，`manifestcmd.py:54` 禁 `/`）；
    但**别**要求「必须两段」——否则 `<change-id>` 单段分支会被误判为推不出。
- **Q3（Q3 定位用保留 stage 名还是 policy 可配；是否收紧 `--stage` 值域）** —— 且**须先解决 D2/D9 的矛盾（CRQ3）**。
  - ➡️ **推荐答案：(a) 默认保留 stage 名 `grill`，允许 policy 覆写（新增 `evidence.grill_stage`，缺省 `"grill"`）；
    (b) 把 `stage` 纳入 manifest 必填字段并做非空校验；(c) 把 CRQ3 的矛盾按「**缺 `stage=grill` manifest = 红**」定案（fail-closed）。**
    **理由**：今日 `stage` 是「写而不校」的自由字段（`constants.py:61-70` 无 `stage`），拼错 `grills` **在 check 侧要么红要么静默取决于实现**——
    必须钉死为**红**（否则 `#2` 的洞重现）；报错文案要点名「**只找到 `stage=grills` 的 manifest**」，让拼错**可诊断**而非可疑。
    **具体例子**：`manifest build --stage grills --report reviews/grill-review.md` 产出 `reviews/grills.manifest.json`；
    接入后的 `check` 找不到 `stage=grill` → 红，文案 `change <id>：无 stage=grill 的 manifest（现有 stage：grills）`。
    收紧 `--stage` **值域**（argparse `choices`）**不建议**：`building`/`grill-adversarial` 等 stage 是自由的，
    硬枚举会立刻与 `gate.md:26`「阶段名任意」和 review-loop 模板冲突——**只收紧 `stage` 的必填性，不枚举值**。
- **Q4（Q4 escape hatch；**并纠正 D8 对「绕过面」的说法**）** `WITNESSLOOP_SKIP_GUARD` 要不要？留痕怎么做？
  - ➡️ **推荐答案：保留 escape hatch（给**人**用），且**改说辞**：把「agent 可以设 env 绕过」改成**真实的**两个绕过面——
    (i) **改用 Bash 写文件**（`Write|Edit` matcher 不覆盖 Bash，见下）；(ii) **不装/关插件**。**理由**：CC 的 PreToolUse hook 是**外层进程**跑
    `witnessloop guard`，agent 在会话内 `export WITNESSLOOP_SKIP_GUARD=1` **只影响它自己起的那个 Bash 子进程**，**改不了 hook 进程的环境**
    ——所以 env 这条「绕路」对 agent **基本不成立**，D8 拿它当诚实边界是**说错了洞**。
    **具体例子**：agent 执行 `python -c "open('src/x.py','w')"` 或 `cat > src/x.py <<'EOF'…` → 不进 Write/Edit → hook 完全不触发 → 绕过；
    而它无法让 hook 那侧读到自己的 env。⇒ 若要堵 Bash 洞，matcher 需加 `Bash` 且解析 `tool_input.command`（成本高、易误伤，见 R7 之外的取舍）。
    留痕：本地留痕意义有限（无权威），建议只在 stderr 打一行「已跳过 guard（WITNESSLOOP_SKIP_GUARD）」，**不**写任何状态文件（守 grill 模板「只读无状态」的硬约束）。
- **Q5（Q5 是否同时做 git-hook）** —— ➡️ **推荐答案：本 change 不做，延后（同设计 defer）。**
  **具体例子**：`pre-push` 钩子在**人的终端**跑、能看见要 push 的提交、且 agent 会话内**无法**绕过（除 `--no-verify`）——
  比 PreToolUse 更贴近 merge boundary。但本仓**已有** CI required check 兜底，git-hook 边际价值低、又要维护第二套安装路径（`core.hooksPath`），
  ⇒ 收益/成本不划算，延后。
- **Q6（新增：evaluator 判据的**精确口径**必须先钉死——否则 D9 回归红）** `## Confirmed Decisions` 的「一条」怎么算？「来源:」怎么匹配？
  「占位确认」的完整字面集是哪几个？
  - ➡️ **推荐答案：在 design 里显式写出三条口径**：(1) entry = `## Confirmed Decisions` 小节内的**顶层 bullet**（`- ` 开头，含多行续行），
    计数 ≥3；(2) 「带来源」= 该 bullet 块内出现 `来源:`（半/全角冒号都收）；(3) 占位确认字面集**照搬 asterwynd 两张表**
    （`UNCONFIRMED_EXACT` ∪ `UNCONFIRMED_STRONG`，`check_openspec_artifacts.py:143-151`）并**把 `≤20 字才查强占位` 的启发式一并写明**。
    **理由**：CRQ1 已证「照抄 asterwynd `- **决策**：` 前缀」会 0 命中本仓证据；不写死口径，实现者极易二选一选错，回归必红。
    **具体例子**：本仓 `dogfood` 的 `- **决策（D1）**：…` 与模板 `grill.md:101` 的 `- **决策**：…` **都要**判为合格 entry——
    以「顶层 bullet + 块内 `来源:`」为准，而不是「bullet 前缀字面」。
    **⚠️ 对抗验证 #6 已把它从「建议」升级为「必须」**：实测本仓 `dogfood` 的 `来源:` **全在续行**——
    「顶层 bullet **同行**自带 `来源:`」的计数 = **0**。即任何**行级**口径（哪怕放宽到「任顶层 bullet」）都会 0 命中 ⇒
    **必须按块级（bullet + 其续行）判**，否则 D9 回归照红。
- **Q7（新增：`check` 是否对**每个** change 都强制 grill 证据——含 docs-only / 无 spec delta / 非 feature 类 change）**
  - ➡️ **推荐答案：witnessloop 保持「每个 change 都要」，但**在 design 里明写这是与 asterwynd 的**有意偏离**。**
    **理由**：asterwynd **事后** grill 门有**三重**豁免（对抗验证「遗漏 #1」补正——原文只提了两类）：
    (a) docs-only（`workflow_guard.py:379-383`）、(b) 无 `specs/*/spec.md`（`:385-389`）、
    (c) **change type 不含 `DESIGN_TYPES`**（`check_openspec_artifacts.py:742` `if not (change_type.all_types & DESIGN_TYPES): return []`，
    `DESIGN_TYPES={feature,refactor,process}`，`:32`）。而 witnessloop 的 change 契约**本就要求**
    `proposal/design/tasks/specs/reviews` 齐备（`constants.py:39`），且 `check` **不解析 proposal 的 Change Type**
    （`contract.py`/`checkcmd.py` 无此判定）⇒「每个 change 都要」是**自然结果**而非选择。
    **具体例子**：一个只改 `openspec/changes/<id>/design.md` 措辞、不碰 `src/` 的 change——asterwynd 豁免、witnessloop D9 仍要它给 grill 证据。
    只要明写「这是有意的更严」，就不算缺陷；否则会被当成移植漏洞。

## 风险

- **R1（阻塞级，同 dogfood R1）**：本 change 的 change 目录**当前只有 proposal+design，缺 `tasks.md`、`specs/`、`reviews/`**
  （CRQ4）。`check`/`manifest build` 都会当场判红。**且空 `specs/` 目录 git 不跟踪**——本地 `check` 可能因目录存在而**误绿**，
  CI 新检出时目录消失 ⇒ 「本地绿、CI 红」陷阱。**实现前必先补 `tasks.md` + `specs/<cap>/spec.md`。**
- **R2（高）**：**移植陷阱**——asterwynd `_extract_grill_decisions`（`check_openspec_artifacts.py:883`）只认 `- **决策**：` 前缀，
  照抄会把本仓 `dogfood` 的 `- **决策（D1）**：` 判成 **0 条** ⇒ **D9 回归必红**。实现者若「照 asterwynd 抄」就中招（CRQ1、OQ6）。
- **R3（高，自伤守卫）**：本 change 改 **CLI 动词面**与 **plugin 文件清单**，会**直接打红 2 条既有测试**——
  `tests/test_cli.py:48-52`（动词面恰为 4 个）、`tests/test_plugin.py:64-71`（plugin 恰 4 文件）；
  `tests/test_docs.py:42-46` 只断言四动词**存在**，**不红**（对抗验证 #5）。设计 §6 **漏了前两条**。
  ⇒ 实现清单须显式含「改这两个测试的期望集 + 相应文案」，否则 CI 红且修起来像「测试挡路」而非「设计漏项」。
- **R4（中）**：**D2/D9 内部矛盾未澄清**（CRQ3）——若把「无 `stage=grill` manifest」实现成**放行**，等于把 `#2` 的洞开回来。
  必须在 design 里二选一定案（OQ3 推荐 fail-closed）。
- **R5（中）**：`stage` 今日「写而不校」（`constants.py:61-70` 不含 `stage`）——D9 的**定位键自身不在必填字段里**。
  历史/手写 manifest 可缺 `stage` 或写任意值；evaluator 对「stage 缺失/非法」的处置未定义（OQ3）。
- **R6（中）**：**D7 反转缺配套守卫**：`docs/design.md:27,145`、`README.md:108` 的「hooks 只作提醒/advisory」若不同步改，
  **CI 不会红**（`test_docs.py` 无此措辞的守卫）——只会留下一份自我打脸的文档。须逐处改 + **新增一条守卫**钉住新口径；
  `docs/adr/` 目录**今日不存在**（需新建，`design.md:135`）。
- **R7（中，机制**未证实**——对抗验证校准）**：**hook 超时 fail-open**——本轮**本地只读核不了**该机制：
  `onFailure:"block"` 在本机 CC 官方 plugin 与 `hook-development` skill 全树 **grep 0 命中**；本地可见的 timeout 相关字段是
  `asyncRewake`/`rewakeMessage`/`timeout`（`security-guidance/hooks/hooks.json`）。「timed-out hook 不阻塞」是否成立**未证实**
  （**不是**被证伪）。仍值得实现期核实：guard 若慢/挂（大仓 `git` 慢），本地强制可能**静默失效**；若属实则 shim 应设超时/`onFailure`。
  （对比 R8：其推理**有**本地依据——SKILL.md「Other - Non-blocking error」，故 R8 成立、R7 标未证实。）
- **R8（中）**：**guard 依赖 `witnessloop` 在 PATH**——plugin 只带 `hooks/hooks.json` + shim，**不带**二进制。
  二进制缺失时 hook 命令以**非 0（非 2）**退出 → 按 CC 语义**不阻塞** → fail-open。安装文档须写明「装了 plugin **还要**装 CLI」。
- **R9（低）**：设计的 `文件:行号` **不精确**（同 dogfood R3）：`manifestcmd.py:136`（实为 `:137`）、
  `workflow_guard.py:363`（实为 `:364`）、`check_openspec_artifacts.py:716-752`（实为 `:739-797`）。
  下游若按行号解析会错位，建议校正。
- **R10（低）**：**exit 码跨动词语义冲突**：`guard` 的 `2 = 拦` 而 `check` 的 `2 = 用法错误`（`constants.py:75`），
  `guard` 的 `3 = 未接入=放行` 而 `check` 的 `3 = 未接入=不放行`（`constants.py:76`、`checkcmd.py:42`）。
  同一数字在两个动词里**语义相反**——D5 已承认，但 `docs/gate.md §6` 的退出码表须按动词分开写，否则误导。
- **R11（低）**：**追加一个自锁可能**——本 change 给 `templates/**`、`plugin/**` 加 `guard` hook 后，**开发 witnessloop 自身**时：
  改 `plugin/commands/grill.md`（交互层）会被 hook 触发——`plugin/**` **在** `require_change_for` 里（`.witnessloop/policy.json:11`）。
  ⇒ 改 `plugin/**` 会触发 guard，需该 change 的 grill 证据已齐——正常流程下证据在实现前已齐，**不自锁**；
  但**若某次只在 `plugin/` 改一行、又临时想绕过 grill**，会被拦——这是**有意**的行为，记为已知。
  （对抗验证 #7：原文「不在 `require_change_for`」与紧随的括号自相矛盾，已删。）

---

> 说明：本审阅只读——除本文件外未改任何 design/proposal/代码，未 commit。
> 第 5 步的**独立对抗验证**（另起零记忆 run → 逐条证伪 → verdict）与第 6 步停轮、第 7 步整合，属下游步骤，本文件不代做。

---

## User Confirmation

> 停轮结算：用户在对抗验证收敛（**3 轮封顶 PASS**）后**一次性**确认，答复口径「**全按推荐**」（2026-10-11）。

- **Q1**: 用户答复：合一个 change（`check` 正文校验 + `guard`+hook 同批落地，不拆）；确认时间: 2026-10-11
- **Q2**: 用户答复：**fail-open**（放行 + 提示），并补「推得的 id **必须命中现存 active change 目录**，否则按推不出处理」；确认时间: 2026-10-11
- **Q3**: 用户答复：保留 stage 名 `grill`（policy 可覆写）+ 把 `stage` **纳入 manifest 必填字段**；**不**枚举 `--stage` 值域；缺 `stage=grill` ⇒ **fail-closed 红**（文案可诊断）；确认时间: 2026-10-11
- **Q4**: 用户答复：保留 escape hatch（`WITNESSLOOP_SKIP_GUARD`），但诚实边界**改写为真实绕过面**（Bash 写文件 / 不装 plugin），**删掉**错误的「env 绕过」说法；确认时间: 2026-10-11
- **Q5**: 用户答复：git-hook 适配器**延后**，本 change 只做 CC hook；确认时间: 2026-10-11
- **Q6**: 用户答复：evaluator 按**块级**判（entry = 顶层 bullet + 续行；`来源:` 块内命中即算；占位字面集照搬 asterwynd）；确认时间: 2026-10-11
- **Q7**: 用户答复：`check` 对**每个** change 都强制 grill 证据，并**明写**这是与 asterwynd 的**有意更严**（asterwynd 有三重豁免）；确认时间: 2026-10-11
