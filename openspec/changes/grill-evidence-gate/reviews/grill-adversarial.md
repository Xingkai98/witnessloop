# Grill 对抗验证：grill-evidence-gate

> 依据 `templates/grill.md` **第 5 步「设计阶段对抗验证 loop」**。默认立场：`grill-review.md`
> 的 7 条 Confirmed Decisions 与 5 条 Code-Resolved 结论**有错**，逐条证伪；能实测的已实测。
> 本报告只读——除本文件外未改任何 design/proposal/代码，未 commit。

## Reviewer

- run id: `grill-adversarial-reviewer-grill-evidence-gate-2026-10-11`
- 时间: 2026-10-11T11:42:47Z
- 被检 revision: `16815c5`（分支 `grill-evidence-gate/2026-10-11`）
- 只读事实源：本仓 `src/witnessloop/*.py`、`templates/grill.md`、`plugin/`、`tests/`、
  `.witnessloop/policy.json`、`docs/{design,gate}.md`、`README.md`、
  `openspec/changes/{dogfood-bootstrap,grill-evidence-gate}/**`；
  asterwynd 真身 `/home/happy/my-agent/scripts/{workflow_guard.py,check_openspec_artifacts.py}`；
  **本机 CC 官方 plugin 与 hook 文档**（`~/.claude/plugins/marketplaces/claude-plugins-official/plugins/*/hooks/hooks.json`
  与 `…/plugin-dev/skills/hook-development/SKILL.md`）——CD5 因此**可凭只读核验**（不必记为未证实）。

## Verdict

**CHANGES_REQUESTED**

7 条 Confirmed Decisions 的**实质结论全部成立**（任务点名的 5 条「若错则结论塌」的承重结论，经实测**无一崩塌**），
但存在 **6 处证据/行号不实或夸大**：一处是「照抄会误导实现者」的 hook schema 取值错误（`defer`）、
两处明确的行号错引、一处与自身括号自相矛盾的措辞、一处红数过计、一处「grep 空」不实。
这些都不改判定方向，但本仓全部立论价值建立在 `文件:行号` 的**机械可信**上
（`templates/grill.md:116`：「下游的检查器按这个格式解析」），证据不实必须在**停轮之前**修回。
**无需回写任何 Decision 的结论**；只需校正引用与两处措辞（清单见 `## 对抗结论`）。

## 逐条对抗

### Confirmed Decisions

**1. CD1（D1 判据成立且已有测试在钉）** → **成立**（未推翻）。
证据：`templates/grill.md:101-102`（`- **决策**：…；来源: <run id>` /「**至少 3 条**」）、
`:116`（「**至少 3 条**、每条附 `来源:`…**硬门槛**」）、`:201`（「`≥3 条且每条带 来源:`」）；
`tests/test_templates.py:158-162`（`assert "3 条" in text` / `assert "来源:" in text`）。
边界（非推翻）：CD1 只说**语义口径**有出处；**逐字 entry-matcher** 恰是 CRQ1 的移植陷阱——
CD1 与 CRQ1 不矛盾，但须并读，别把 CD1 读成「格式可直接照抄」。

**2. CD2（`check` 完全不读报告正文，#2 属实）** → **结论成立，但证据夸大（「grep 空」不实）**。
结论侧（复核通过）：`contract.validate_review_manifests`（`contract.py:121-149`）只做 manifest 结构校验；
报告唯一消费点是 `_check_hashes`（`contract.py:355-394`），对 `report_path` 只算
`sha256_tree(report_path)`（`contract.py:371`），从不解析小节。
**但**「整份 `contract.py` 无 …`来源`…任何字面量（grep 空）」**是假的**：`来源` 出现在
**`contract.py:62`**（docstring「来源是那个已经搬走的」），另有 `initcmd.py:125`。
`Confirmed Decisions` / `Open Questions` 两串在 `src/` 确为 0 命中，但 `来源` 不是 0——
实测 `grep -rn "来源" src/` → 2 命中。⇒ 结论保留，**「grep 空」须删或改成「不消费 `来源` 语义」**。

**3. CD3（D2 事实成立、行号错、比设计说的更脆）** → **成立**（未推翻）。
证据：`cli.py:90` 的 `--stage` 只给 help「如 grill / building」、无 `choices`；
`manifestcmd.py:137`（`"stage": args.stage,`）——设计 `design.md:16` 写 `:136` **数字错**，review 校正为 `:137` **正确**；
`stage` 不在 `REVIEW_MANIFEST_REQUIRED_FIELDS`（`constants.py:61-70`）。三项全对。

**4. CD4（D4 死锁规避成立，对 witnessloop 自身 policy）** → **成立**（未推翻）。
证据：`.witnessloop/policy.json:8-12` 恰为 `["src/**","templates/**","plugin/**"]`；
`check._require_change`（`checkcmd.py:98`）与 guard 触发面同源；
asterwynd 同款豁免 `_is_change_doc_write`（`workflow_guard.py:517-531`，放行 change 目录内
`proposal/design/tasks/specs/reviews`）。写 `reviews/**`、`openspec/changes/**`、`docs/**`、`tests/**`
均不命中 `require_change_for` ⇒ 产证据的写操作不被拦。**成立**。

**5. CD5（D6 的 CC hooks schema 今日已可定案）** → **基本成立，但一处取值错误（`defer` 不实）**。
可核（本机 CC 官方 plugin 即证，**不必记为未证实**）：
- `plugin/hooks/hooks.json` 形态 ✓（`…/security-guidance/hooks/hooks.json`、`hookify/…` 均此布局，可选顶层 `description`）；
- 结构 = 事件→matcher 组→handlers，`{"matcher":"Write|Edit","hooks":[{"type":"command","command":"…"}]}` ✓
  （`hookify/hooks/hooks.json` 的 PreToolUse + `security-guidance` 的 `"matcher":"Edit|Write|MultiEdit|NotebookEdit"`；SKILL.md 示例逐字 `"matcher": "Write|Edit"`）；
- `${CLAUDE_PLUGIN_ROOT}` 占位符 ✓；PreToolUse stdin JSON 含 `cwd`（公共字段）+ `tool_name`/`tool_input`/`tool_result`（事件字段）✓（SKILL.md「Hook Input Format」）；
- block 二选一：exit **2** + stderr 作理由 ✓（SKILL.md「2 - Blocking error (stderr fed back to Claude)」）；
  exit 0 + `hookSpecificOutput.permissionDecision` ✓（`…/examples/validate-write.sh`、`validate-bash.sh`、`read-settings-hook.sh` 实证 `deny`/`ask`）。
**错误**：review 写「另有 `ask`/`defer`」。**`defer` 不存在**——SKILL.md 明列 `"permissionDecision": "allow|deny|ask"`
（`SKILL.md:148`）；全树 grep `"defer"` **0 命中**，第三值是 **`allow`**（另有 `ask`），**无 `defer`**。
⇒ 方向（exit 2 或 `permissionDecision:"deny"`）成立、D6「⚠️ 待核实」可降级为已定案**成立**；
但 `defer` 这个取值**须删**，否则实现者会照抄一个不存在的枚举。

**6. CD6（D9 回归红线可满足——仅当不照搬 asterwynd 解析）** → **成立**（本轮实证加固）。
证据：`openspec/changes/dogfood-bootstrap/reviews/grill-review.md` 实测 **6 条** `## Confirmed Decisions`
（`:16,24,28,36,41,45`，均 `- **决策（Dn）**：…` 形态、每条的**续行尾**带 `来源:`）、
Q1–Q6 六条 `## Open Questions`（`:88-121`）、Q1–Q6 六条 `## User Confirmation`（`:162-167`，`用户答复：…；确认时间: 2026-10-11`）。
按 D1 语义三条判据 = **合格**。且我**执行了 asterwynd 的 `_extract_grill_decisions` 逻辑**于该文件
→ **命中 0 条**（见 CRQ1）⇒「仅当 evaluator 不照搬 asterwynd 解析」这半句被实证**坐实**。**成立**。

**7. CD7（D7 反转在文档侧需动，且无测试兜底）** → **成立**（未推翻）。
四处引证**逐条核对全对**：`docs/design.md:27`（§2 点 6「agent hooks 只作提醒」）、
`docs/design.md:145`（§9 风险 4「强制只在 CI 一层」）、`README.md:108`（「agent hooks 只作辅助提醒」）、
`docs/reviews/grill-design.md:19`（「强制落 CI required check，hooks 只作提醒」）。
`tests/test_docs.py` 只钉三类（`VERB_SURFACE_DOCS:18` / `STALE_CLAIMS:20` / `RUN_ID_DOCS:51` / `IDEMPOTENCY_DOCS:114`），
**确无**钉「hooks 只作提醒」的守卫 ⇒ 漏改不会红。**成立**。

### Code-Resolved Questions

**CRQ1（asterwynd `_grill_evidence_missing` / `_extract_grill_decisions` 能否照搬）** → **结论成立，但两处行号不实**。
成立侧（**实证**）：`check_openspec_artifacts.py:883` `_extract_grill_decisions` 只认前缀字面
`- **决策**：` / `- **决策**:`（`:896-899`）、**不查 `来源:`**；本仓 dogfood 用 `- **决策（D1）**：`
（`决策` 与 `**` 之间夹 `（D1）`）⇒ 我**逐行跑该判定于 dogfood 文件，命中数 = 0**；
`_grill_evidence_missing` 定义在 `workflow_guard.py:364`（设计写 `:363`，差 1 行）——
这三条**全对**。设计 `design.md:18-19` 说 asterwynd「事后判：…每条带 `来源:`」**是对 asterwynd 的误述**
（真身不查 `来源:`），review 纠正**正确**。
**行号错引（须修）**：
- review 写「读**硬编码** `reviews/grill-design.md`（`:381`）」——**实为 `workflow_guard.py:391`**
  （`:381` 是 `text = proposal.read_text(...)`）。差 **10 行**。
- review 写「先跳 docs-only 与无 `specs/*/spec.md`（`:373-380`）」——docs-only 在 **`:379-383`**、
  无 spec 在 **`:385-389`**，`:373` 还在 docstring 里。区间不实。
- 正确项（未错）：`check_openspec_artifacts.py:739`（设计写 `:716-752`，实为 `:739-797`）✓；
  `_extract_grill_decisions:883` ✓；`workflow_guard.py:517-531`（`_is_change_doc_write`）✓。

**CRQ2（Open Question↔User Confirmation 配对机制 / 本仓满足否）** → **结论成立，但一处行号不实**。
成立侧：配对 = Q 编号，验收形态 `- **Qn**…：…用户答复：<非占位>；确认时间:…`
（`check_openspec_artifacts.py:874` `_unconfirmed_open_questions` + `workflow_guard.py:459-475` `_extract_user_confirmation_indexes`），
dogfood 六条逐条符合 ⇒ 配对通过。**成立**。
**行号错引（须修）**：review 写两张占位表在 `workflow_guard.py:435-441`——**实为 `:409-417`**
（`:435-441` 落在 `_extract_open_question_indexes` 内部）。`check_openspec_artifacts.py` 两张表 review 写 `:145-152`，
实为 `:143-151`（近，但也不精确）。

**CRQ3（D2 与 D9 是否自洽）** → **部分成立**（结论方向对，措辞「不能同真/必须二选一」略夸大）。
`design.md:43`（D2）确写「stage 拼错（`grills`）⇒ 判定会**静默失效**」；`design.md:94-95`（D9）确写
「要求**存在** `stage=grill` 的 manifest…缺则新增一条红」。二者若都实现，**净可观测行为是红（响亮）**，
故 D2 那句「静默失效」与 D9 的净结果**确有出入**——但 D2 **已自指**「→ 见 D9 与 Open Question Q3」，
更自然的读法是「D2 的脆弱点是 D9 的动机」。⇒ 真问题是**措辞需与 D9 对齐**，而不是「两个决策互斥、必须二选一」。
裁定：**部分成立**——值得定案（review 的 OQ3 推荐 fail-closed = 红，方向正确、保留），
但报告「**不能同真**」的断言**应下调为「措辞不自洽，须统一」**。

**CRQ4（本 change 自己的 change 目录合契约否）** → **成立**（实证）。
`find openspec/changes/grill-evidence-gate`：只有 `proposal.md`/`design.md`（+ `reviews/grill-review.md`）；
**`specs/` 为空目录（`find … /specs -mindepth 1` = 0 项）**、**无 `tasks.md`**。
对照 `required_artifacts`（`.witnessloop/policy.json:13-19`）与 `HASHED_ARTIFACTS`
（`constants.py:55-58`，硬要求 `tasks.md`+`specs`），`check`/`manifest build` 均当场判红。**成立**。

**CRQ5（本 change 会打红哪些既有测试）** → **部分成立：2 条硬红成立，第 3 条不成立（R3「打红三条」过计）**。
- `tests/test_cli.py:48-52`（`test_the_verb_surface_stays_small`，`assert set(sub.choices) == {"init","uninit","check","manifest"}`）
  → 加 `guard` 即红 ✓。
- `tests/test_plugin.py:64-71`（`test_plugin_file_inventory_is_exactly_expected`，`EXPECTED_FILES` 恰 4 项，`:20-25`）
  → 加 `hooks/hooks.json` + shim 即红 ✓。
- `tests/test_docs.py:42-46`（`test_docs_name_all_four_verbs`）→ **不会红**：它只 `assert verb in text`
  断言 `("init","check","uninit","manifest build")` **存在**（`:45-46`），加第五动词 `guard` 后这四串仍在 ⇒ **通过**。
  另无任何测试钉「动词数为 4/N」（`STALE_CLAIMS:20` 只抓 `3/三/2` 两种旧计数，抓不到残留的「四」）。
  ⇒ review 自身括号亦写「加 `guard` 后**仍是四个**、但措辞要同步」——**与 R3「直接打红三条」自相矛盾**。
  保留：设计 §6（`design.md:136-137`）**确实只提 `test_docs.py` 一类、漏了前两条**——这条**成立且重要**；
  但把 `test_docs.py:42-46` 列为「会红」**不实**，红数是 **2 条**。

### Open Questions（推荐答案是否被推翻）

- **Q1（合一个 change）** → 推荐**成立**。共用 evaluator 是硬理由；`constants.HASHED_ARTIFACTS:52-58`
  的「共用一张表」正是本仓踩过「两边各写一套」坑后的既有结论。
- **Q2（fail-open + 推得 id 必须命中现存 active change 目录）** → 推荐**成立**，且**有现成凭据 review 未引**：
  asterwynd `_current_change_id()`（`workflow_guard.py:332-361`）**正是**这么做的——`:348`
  `if (CHANGES_DIR / head).is_dir(): return head`。⇒ Q2 不是「新设计」，是**照搬 asterwynd 已验证行为**，更稳。
- **Q3（保留 stage 名 `grill` + 纳入必填 + 缺则 fail-closed）** → 推荐**成立**（与 CRQ3 的定案一致）；
  「只收紧必填性、不枚举值」的理由（`docs/gate.md:26`「阶段名任意」+ `--stage` 自由）
  核对 `cli.py:90` 无误。
- **Q4（保留 escape hatch + 纠正「绕过面」）** → 推荐**成立**。D8（`design.md:90`）「agent 可以设 env 绕过」
  确为**说错洞**：PreToolUse hook 是 CC 外层进程，agent 在 Bash 里 `export WITNESSLOOP_SKIP_GUARD=1`
  只改自己那个子进程的环境，**改不了 hook 进程的环境**。真绕过面 = (i) Bash 写文件
  （design `Write|Edit` matcher 不覆盖 Bash）、(ii) 不装/关 plugin。**纠正正确**。
- **Q5（git-hook 延后）** → 推荐**成立**（CI required check 已兜底，第二套安装路径收益低）。
- **Q6（钉死 evaluator 精确口径：entry=顶层 bullet 含续行 / 「带来源」=块内命中 / 占位字面集照搬）** → 推荐**成立**，
  且**本轮实测把它从「建议」升级为「必须」**：我实测 dogfood 的 `来源:` **全在续行**——
  「顶层 bullet 行内自带 `来源:`」的计数 = **0**。即任何**行级**口径（含放宽到「任顶层 bullet」）
  都会 0 命中 ⇒ 必须按**块级（bullet + 其续行）**判，否则 D9 回归照红。
- **Q7（每 change 都要 grill，含 docs-only，作为有意偏离）** → 推荐**方向成立但不完整**（见「遗漏」#1）：
  asterwynd 的**事后** grill 门除 docs-only + 无 spec 外，**还**限 `change_type.all_types & DESIGN_TYPES`
  （`check_openspec_artifacts.py:742`）——bugfix/research 亦豁免。偏离面是**三类**不是两类。

## 遗漏的重要事实

1. **asterwynd 事后 grill 门有「类型」豁免轴，review 的 Q7 只提了 docs-only + 无 spec。**
   `_check_design_review_task` 首行 `if not (change_type.all_types & DESIGN_TYPES): return []`
   （`check_openspec_artifacts.py:742`，`DESIGN_TYPES={feature,refactor,process}`，`:32`）。
   ⇒ witnessloop D9「每个 change 都要」相对 asterwynd 是**三重**偏离（docs-only、无 spec、非 DESIGN_TYPES）。
   witnessloop 的 `check` **不解析 proposal 的 Change Type**（`contract.py`/`checkcmd.py` 无此判定），
   所以「每 change 都要」其实是**自然结果**而非选择——这点应写明，否则会被当成移植漏洞。
2. **Q2 的推荐 = asterwynd 现成行为，review 未引为凭据**（见 Q2 条）。引上 `workflow_guard.py:348`
   能把「推荐」变成「照搬已验证实现」，说服力更强。
3. **R7 的机制本地无出处，应记为「未证实」而非断言。** `onFailure:"block"` 在
   本机 CC 官方 plugin 与 `hook-development` skill 全树 **grep 0 命中**；本地可见的 timeout 相关字段
   是 `asyncRewake`/`rewakeMessage`/`timeout`（`security-guidance/hooks/hooks.json`）。
   「timed-out hook 不阻塞」与 `onFailure:"block"` 是否成立，**本地只读核不了**——按任务口径
   应标**未证实**（不是证伪）。R8 的推理（二进制缺失 → 非 2 退出 → 非阻塞 fail-open）**有本地依据**
   （SKILL.md「Other - Non-blocking error」）——**成立**，与 R7 区别对待。
4. **R11 内部措辞自相矛盾。** 原文说改 `plugin/commands/grill.md`「但它**不在** `require_change_for`」，
   紧接着括号又写「（`.witnessloop/policy.json:8-12` 只含 `src/**`、`templates/**`、`plugin/**`——**含 `plugin/**`**）」
   ——括号直接推翻前半句。实为 `plugin/**` **在** `require_change_for`（`policy.json:10`）。
   R11 结论（改 `plugin/**` 会触发 guard）**方向对**，但「不在」二字须删。
5. **CD2 的「`来源` grep 空」不实**（见 CD2）——`contract.py:62` 有该串。属「结论对但证据夸大」。

## 对抗结论

- **7 条 Confirmed Decisions：全部成立**（结论侧无误），其中 CD2 证据夸大、CD5 含一个错误取值。**无一被推翻**。
- **5 条 Code-Resolved：CRQ1/CRQ2/CRQ4 成立、CRQ3/CRQ5 部分成立**（CRQ3 措辞夸大、CRQ5 红数过计）。
- **承重结论复核（任务点名项）**：CRQ1 移植陷阱 **实测坐实**（asterwynd 判定于 dogfood = 0 命中）；
  CD6/D9 回归红线 **实测坐实**（dogfood 6/6/6 合格）；CRQ3 D2/D9 张力 **真实存在**（需定案，方向 fail-closed 对）；
  CRQ5 自伤 **2 条硬红**（test_cli、test_plugin）；CRQ4 change 目录 **实测不合契约**（specs 空、无 tasks.md）。
  **结论无一塌方**；塌的是引用精度。
- **7 条 Open Questions 推荐答案：方向全部成立**，Q2（补 asterwynd 凭据）、Q6（升级为「必须」）、
  Q7（补「类型」豁免轴）三处需补强，其余照采纳。**无需推翻任何推荐答案。**
- **必须修改（回写 `grill-review.md`，停轮前）**——均不改判定结论：
  1. CD2：删/改「`来源` grep 空」（`contract.py:62` 有该串）；
  2. CD5：删 `defer`（正确值集 `allow|deny|ask`，本机 CC 官方来源可核）；
  3. CRQ1：`:381`→`:391`；「`:373-380`」→ docs-only `:379-383`、无 spec `:385-389`；
  4. CRQ2：`workflow_guard.py:435-441`→`:409-417`；`:145-152`→`:143-151`；
  5. R3/CRQ5：「打红三条」→「**2 条硬红**（`test_cli.py:48-52`、`test_plugin.py:64-71`）」，
     `test_docs.py:42-46` 只是「措辞须同步」、**不红**；
  6. CRQ3：把「不能同真/必须二选一」下调为「D2 措辞须与 D9 对齐（净行为=fail-closed 红）」；
  7. R7：机制标**未证实**（本地无 `onFailure` 出处）；R11：删「不在 `require_change_for`」。

---

> 说明：本对抗验证只读——除本文件外未改任何文件，未 commit。
> 下游（第 6 步停轮、第 7 步整合 design）属作者主 session；本报告不代做。

## 第 2 轮对抗验证

- 时间: 2026-10-11T11:46:05Z
- 被检 revision: `16815c5`（分支 `grill-evidence-gate/2026-10-11`）；被检文件 `reviews/grill-review.md`（**已修订**版）
- 裁定: **CHANGES_REQUESTED**
- 立场: 默认第 1 轮 7 条「必须修改」的**落实有错**，逐条读真身源码/测试/`awk` 实测复现。

### 逐条核验（7 条必须修改 + 3 条补强）

1. **CD2（删「`来源` grep 空」）→ 已落实且正确。** `grep -rn 来源 src/` = **2 命中**，与 review 所述一致：
   `contract.py:62`（docstring「来源是那个已经搬走的」）、`initcmd.py:125`（docstring「缺省来源」）。
   review `:32-33` 已改成「`来源` 虽在 `contract.py:62`（docstring）与 `initcmd.py:125` 出现，但那是**文本巧合**…`check` 从不**消费** `来源` 语义」——全文再无「grep 空」字样。✓

2. **CD5（删 hook 取值 `defer`）→ 已落实且正确。** `grep -n defer grill-review.md` 仅 2 命中：
   `:49`「取值集 **`allow|deny|ask`**，**无 `defer`**」（校正句本身）、`:138`「（同设计 defer）」（Q5 git-hook **延后**，英文「延迟」义，非 hook 枚举）。
   真身：本机 CC `…/plugin-dev/skills/hook-development/SKILL.md:148` 逐字 `"permissionDecision": "allow|deny|ask"`，**无** `defer`。✓

3. **CRQ1 行号（`:381`→`:391`；`:373-380` 拆 docs-only/无 spec）→ 主张部分全对，但旁证串留一处残留。**
   真身核对（`/home/happy/my-agent/scripts/workflow_guard.py`）：`:364`=`def _grill_evidence_missing`；`:391`=`evidence = change_dir / "reviews" / "grill-design.md"`（硬编码）；`:379-383`=docs-only 块（`proposal.read_text` + `"primary: docs"`）；`:385-389`=无 `specs/*/spec.md` 块。review `:66-67` 已按此四值写对。**残留**：review `:75` 的旁证串仍写 `workflow_guard.py:364,373-381,517-531`——`373-381` **未随 #3 拆正**（含 docstring 尾 + docs-only 一部分；真身相关区应为 `:379-391`）。`517-531`=`_is_change_doc_write` ✓。

4. **CRQ2 行号（`workflow_guard.py:435-441`→`:409-417`；`check_openspec_artifacts.py:145-152`→`:143-151`）→ 部分落实。**
   真身：`workflow_guard.py:409-416`=两张表（`:417`=`_UNCONFIRMED_MAX_ANSWER_LEN`），`:409-417` ✓；`check_openspec_artifacts.py:143-150`=两张表（`:151` 为阈值）。
   review **`:81`** 已改 `:143-151` ✓、`:409-417` ✓。**但 `:145-152` 未扫净**：review **`:83`**（`check_openspec_artifacts.py:145-152,874`）与 **`:146`**（Q6 推荐答案「照搬 asterwynd 两张表（…:145-152）」）**仍写 `145-152`**。

5. **CRQ5/R3 红数（三条→2 条硬红）→ 已落实且正确。** review `:94` 已写「**2 条硬红**（…原文『至少三条』**过计**）」；`:97-98` 已把 `test_docs.py:42-46` 标「**不会红**」。
   实测三测试：`test_cli.py:51` `assert set(sub.choices) == {"init","uninit","check","manifest"}`（加 `guard` 即红 ✓）；`test_plugin.py:70` `assert found == EXPECTED_FILES`（`EXPECTED_FILES` 恰 4 项，见 `test_plugin.py:20-25`，加文件即红 ✓）；`test_docs.py:45-46` 仅 `assert verb in text`（四动词**存在**，加 `guard` 后仍在 ⇒ **不红** ✓）。

6. **CRQ3 措辞（下调「不能同真/必须二选一」）→ 已落实且正确。** review `:84` 已写「**措辞不自洽（须统一）**——原文『不能同真 / 必须二选一』**夸大**」；`:87` 明写净行为 = **fail-closed 红**。✓

7. **R7（标未证实）→ 已落实且正确；R11（删「不在 `require_change_for`」）→ 「不在」已删，但引入一处新行号错。**
   R7：`grep -rn onFailure` 遍历本机 CC 官方 plugin 全树 = **0 命中** ⇒「未证实」标注正确（review `:182-185`）。✓
   R11：`plugin/**` **确在** `require_change_for`（review `:196` 已删「不在」，✓）；**但引的 `.witnessloop/policy.json:10` 错**——真身 `policy.json:10`=`"templates/**"`，`"plugin/**"` 在 **`:11`**。原 R11 括号为范围 `:8-12`（第 1 轮「遗漏」#4 引作 `:8-12`），本轮改窄成单行 `:10` ⇒ **修出一处新的 off-by-one**。

8. **补强三处 → 均已并入且实测正确。**
   - **Q2**：review `:116` 已引 asterwynd 凭据 `workflow_guard.py:348`=`if (CHANGES_DIR / head).is_dir():`（`_current_change_id`）✓。
   - **Q6**：review `:150-152` 已把口径从「建议」升级为「**必须**」。实测 `openspec/changes/dogfood-bootstrap/reviews/grill-review.md`：`来源:` 共 6 处、**全在续行**，顶层 bullet **同行**自带 `来源:` 的计数 = **0** ⇒ 必须**块级**判，属实。✓
   - **Q7**：review `:156-158` 已补第三重豁免轴 `check_openspec_artifacts.py:742`=`if not (change_type.all_types & DESIGN_TYPES): return []`，`DESIGN_TYPES` 在 `:32`=`{feature,refactor,process}` ✓。

### 新问题

- **R11 引 `.witnessloop/policy.json:10` 应为 `:11`**（`plugin/**`）。`:10` 指向 `templates/**`——此为**本轮改窄引用时新引入**的指向错误行，且 R11 正文正是要论证「`plugin/**` 在 `require_change_for` 里」。
- **CRQ2 两处残留 `145-152`**（review `:83`、`:146`）未被「必须修改」#4 覆盖到，仍指不精确区间（真身 `:143-151`）。
- **CRQ1 旁证串 `373-381`**（review `:75`）未随「必须修改」#3 拆正（真身相关区 `:379-391`）。

（均为**引用精度**问题，**不改任何结论**。）

### 结论

第 1 轮 7 条「必须修改」中 **#1/#2/#5/#6 完全落实**、**#3/#4 落实但各留一处引用残留**、**#7 的 R7 完全落实而 R11 改出一处新行号错**；3 条补强（Q2/Q6/Q7）**全部并入且实测无误**。**7 条 Confirmed Decisions 与 5 条 Code-Resolved 的实质结论无一塌方**——塌的仍是引用精度，且本次含**一处指向错误行的引用**（R11 `:10`）与**两处第 1 轮已点名却未扫净的 `145-152`**。鉴于本仓全部立论建立在 `文件:行号` 的机械可信上（`templates/grill.md:116`），裁定 **CHANGES_REQUESTED**：只需改三处引用——R11 `:10`→`:11`；`:83`/`:146` 的 `145-152`→`143-151`；`:75` 的 `373-381`→`379-391`——即可转 **PASS**（无需回写任何 Decision 结论）。

## 第 3 轮对抗验证

- 时间: 2026-10-11T11:48:34Z
- 被检 revision: `16815c5`（分支 `grill-evidence-gate/2026-10-11`）；被检文件 `reviews/grill-review.md`（第 3 轮修订版）
- 立场: **默认第 2 轮点名的 3 处引用修复有错**，逐条去真身源码**实测**（`awk` 按行号打印真身 + `grep` 全量扫尾），不采信文本自述。
- 裁定: **PASS**

### 逐条核验（第 2 轮「只差 3 处引用」）

1. **R11 的 `require_change_for` 行号（`:10`→`:11`）→ 已落实且正确。**
   真身 `.witnessloop/policy.json`：`:10`=`"templates/**",`、**`:11`=`"plugin/**"`**、`:8-12`=整个 `require_change_for` 数组。
   review `:196` 已改为「`plugin/**` **在** `require_change_for` 里（`.witnessloop/policy.json:11`）」——指向正确行。✓

2. **`check_openspec_artifacts.py:145-152`→`:143-151`（两处）→ 已落实且正确。**
   真身 `/home/happy/my-agent/scripts/check_openspec_artifacts.py`：`:143`=`UNCONFIRMED_EXACT = {`、`:146`=`}`、`:147`=`UNCONFIRMED_STRONG = {`、`:150`=`}`、`:151`=`_UNCONFIRMED_MAX_ANSWER_LEN = 20` ⇒ 两张表+阈值 = **`:143-151`**（`:152` 起是注释/剥离表）。
   全量核：review 中 `145-152` 出现次数 = **0**；`143-151` 现于 `:81`、`:83`、`:146`——第 2 轮点名的 `:83`、`:146` **两处均已改对**。✓

3. **残余的 `workflow_guard.py:373-381`→`:379-391` → 已落实且正确。**
   真身 `/home/happy/my-agent/scripts/workflow_guard.py`，三块**各就其位**：
   (a) docs-only 跳过 `:379-383`（`:382`=`if "primary: docs" in text:`、`:383`=`return False`）；
   (b) 无 `specs/*/spec.md` 跳过 `:385-389`（`:386`=`if not specs.exists(): return False`、`:388-389`=glob 阴性 return False）；
   (c) 读**硬编码** `reviews/grill-design.md` `:391`（`evidence = change_dir / "reviews" / "grill-design.md"`）。
   review `:75` 已改为 `workflow_guard.py:364,379-391,517-531`——`379-391` 恰好覆盖上述三块。✓（`517-531`=`_is_change_doc_write` ✓；`:364`=函数 def ✓。）

### 全量扫尾（旧行号）

`grep` 扫 `grill-review.md`：`373-381`=**0**、`145-152`=**0**、`policy.json:10`=**0**；另 `373-380`、`435-441`、`:381` 亦**全 0 命中**。第 1/2 轮点名的旧串已**扫净**，无遗留。
（`defer`/`grep 空`/`不能同真`/`打红三条`/`不在 require_change_for` 等历史错句仅以「原文…（校正）」的**引用-更正**形态出现，属正确元引用，非残留。）

### 新问题（均为**非阻塞**、指向符号正确、不影响任何结论）

- **`workflow_guard.py:459-475`（review `:79`、`:83`）跨度偏短。** 真身 `_extract_user_confirmation_indexes` 为 **`:459-478`**（`:478`=`return indexes`，下一 `def` 在 `:481`），引用漏了 `:476 continue`/`:477 indexes.append(...)`/`:478 return indexes`。**非阻塞**：`:459` 正是该函数 `def` 行，读者仍被引到**正确符号**，不误导到别的符号——与第 2 轮点名的「指向错误行」（如 `policy.json:10`）**不同类**。
- **`check_openspec_artifacts.py:739-797`（review `:69`/`:75`/`:190`）尾行越 1 行。** 真身 `_check_design_review_task` 为 **`:739-796`**（`:796`=`return []`；`:797`/`:798` 为空行）。**非阻塞**：`:739` 为函数 `def` 行；且第 2 轮已明确把 `:739-797` 判为「未错」，本轮不据此翻转。

### 结论

第 2 轮点名的 **3 处引用全部落实、并经真身源码实测正确**；全文**无任何遗留旧行号**。两处跨度尾部不精（`:459-475`、`:739-797`）属**非阻塞**观察（所引符号均正确、与结论无涉、其一前轮已明判「未错」），不构成必须修改。裁定 **PASS**——7 条 Confirmed Decisions 与 5 条 Code-Resolved 的实质结论两轮均无一塌方，引用精度亦已收敛。
