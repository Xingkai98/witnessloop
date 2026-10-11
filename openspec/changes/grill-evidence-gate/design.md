# Design: grill-evidence-gate

> 状态：**设计已收敛**（grill + 设计阶段对抗验证 3 轮封顶 → PASS），待用户停轮确认。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。
> 审阅证据：`reviews/grill-review.md`（决策记录）、`reviews/grill-adversarial.md`（对抗验证，含 R2/R3）。

## 0. 一句话

把「grill 证据算不算齐」抽成**一个** host-agnostic 判定，接到**两处**：`check`（事后/CI）与
新的 `guard` 动词 + CC hook（事前/本地）。

## 1. 现状（实测）

- `check` **完全不读报告正文**（**#2**）：`contract.validate_review_manifests`（`contract.py:121-149`）
  只校验 manifest 存在/hash 绑定/`reviewer≠author`/孤儿绑定；报告的唯一消费点是 `_check_hashes`
  （`contract.py:355-394`），对 `report_path` 只算 `sha256_tree`（`:371`）。`Confirmed Decisions` /
  `Open Questions` 两串在 `src/` 为 0 命中。
- `manifest build` 把 `--stage` 原样写进 manifest（`manifestcmd.py:137`），**值域任意**（`cli.py:90` 只给 help、无 `choices`），
  且 `stage` **不在** `REVIEW_MANIFEST_REQUIRED_FIELDS`（`constants.py:61-70`）——**写而不校**。
- asterwynd 的对应物（**谓词可移植，文件不能照抄**）：`workflow_guard.py:364` `_grill_evidence_missing()`
  （写码前判；docs-only 跳 `:379-383`、无 spec 跳 `:385-389`、读**硬编码** `reviews/grill-design.md` `:391`；
  文档类写操作豁免 `_is_change_doc_write` `:517-531`；change id 取自分支且**必须命中现存目录** `:332-361`，`:348`）；
  事后判在 `check_openspec_artifacts.py:739-796`（`_check_design_review_task`），其 `_extract_grill_decisions`
  （`:883`）**只认前缀字面 `- **决策**：` / `- **决策**:`**（`:896-899`）、**不查 `来源:`**。
- 本仓已有：`.witnessloop/policy.json`（`require_change_for` 在 `:8-12`：`src/**`、`templates/**`、`plugin/**`）、
  branch protection（require PR + required check `gate / check`）、`plugin/` 可分发。
- **CC plugin hooks 的 schema 已定案**（本机 CC 官方 plugin 实证）：`plugin/hooks/hooks.json`（可选顶层
  `description`）+ `${CLAUDE_PLUGIN_ROOT}`；结构 = 事件→matcher 组→handlers；
  `{"matcher":"Write|Edit","hooks":[{"type":"command","command":"…"}]}`；PreToolUse stdin JSON 含
  `tool_name`/`tool_input`/`cwd`；block 二选一：exit **2** + stderr 作理由，或 exit 0 +
  `hookSpecificOutput.permissionDecision`（**取值 `allow|deny|ask`，无 `defer`**）。

## 2. 决策

### D1 共享 evaluator：新模块 `evidence.py`，**纯函数**，判据按**块级**定

- 形态：`grill_evidence_findings(report_text: str) -> list[Finding]`（输入**文本**、无 IO、`check` 与 `guard` 共用）。
- **精确口径**（**必须写死**，否则 D9 回归照红——对抗验证实测）：
  1. **entry = `## Confirmed Decisions` 小节内的顶层 bullet（`- ` 开头）连同其续行**，计数 **≥3**；
  2. **「带来源」= 该 bullet 块（bullet + 续行）内出现 `来源:`**（半/全角冒号都收）。
     **⚠️ 必须块级**：实测本仓 dogfood 的 `来源:` **全在续行**，「bullet 同行命中」= **0** ⇒ 任何**行级**口径都 0 命中。
  3. `## Open Questions` 里**每条**（按 `Q<n>` 编号）都要在 `## User Confirmation` 有对应 `Q<n>` 的确认记录；
  4. 占位确认不算真确认：**照搬 asterwynd 两张表** `UNCONFIRMED_EXACT` ∪ `UNCONFIRMED_STRONG`
     （`check_openspec_artifacts.py:143-151`）**连同**「短答复（≤20 字）才查强占位」的启发式。
- **⚠️ 移植陷阱（对抗验证已复现）**：asterwynd 的 `_extract_grill_decisions`（`:883`）只认 `- **决策**：` 前缀；
  本仓 dogfood 写的是 `- **决策（Dn）**：`（「决策」与 `**` 之间夹 `（Dn）`）⇒ **逐行跑该判定 = 命中 0 条**。
  **结论：按「顶层 bullet + 块级 `来源:`」判，绝不按 bullet 前缀字面。**
- 备选：写进 `contract.py`——否：`contract` 是门禁契约，evaluator 要被 host 侧 `guard` 复用，独立模块边界更干净。

### D2 「grill 报告」定位：**保留 stage 名**，且 stage 纳入必填

- 决策：(a) 默认保留 stage 名 `grill`，允许 policy 覆写（新增 `evidence.grill_stage`，缺省 `"grill"`）；
  (b) **把 `stage` 纳入 `REVIEW_MANIFEST_REQUIRED_FIELDS` 并做非空校验**（它今日「写而不校」）；
  (c) **缺 `stage=grill` 的 manifest = 红（fail-closed）**——报错文案要点名「现有 stage：…」，让拼错**可诊断**。
- **D2 措辞与 D9 对齐**：原稿「stage 拼错 ⇒ **静默失效**」的说法与 D9 冲突；**净行为定为 fail-closed 红**。
- **不收紧 `--stage` 值域**：`building`/`grill-adversarial` 等是自由 stage，硬枚举会与 `docs/gate.md:26`「阶段名任意」冲突
  ——**只收紧必填性，不枚举值**。

### D3 `guard` 怎么知道「当前 change」：分支名 + **必须命中现存目录**

- 决策：(a) **分支名** `<change-id>/<date>` 取**首段**（change id 是单段，`manifestcmd.py:54` 禁 `/`）；(b) env
  `WITNESSLOOP_CHANGE` 显式覆盖。
- **关键前置规则**（对抗验证补强）：**推得的 id 必须命中一个现存的 active change 目录**（且不落 `archive/**`），
  否则一律按「推不出」处理。**真问题不是「推不出」，是「推得出但推错」**——`fix/login-timeout`、`dependabot/…` 的
  首段会被当 change id → 目录不存在 → 误拦。
- **这不是新设计**：asterwynd `_current_change_id()`（`workflow_guard.py:332-361`，`:348` `if (CHANGES_DIR / head).is_dir(): return head`）
  就是这么做的 ⇒ **照搬已验证行为**。
- **推不出 / 推错时：fail-open（放行 + 显式提示）**——本地是「防遗忘」不是「防对抗」（见 D8），
  fail-closed 会把所有非 change 分支的开发堵死。

### D4 触发（写代码）vs 豁免（写文档）

- **触发 = 路径命中 `policy.require_change_for`**（与 `check._require_change`(`checkcmd.py:98`) **同源同字段**）；
  **其余全部豁免**（`docs/**`、`tests/**`、change 目录内文档 artifact）。
- **豁免文档是死锁防线**：写 `design.md`/`grill-review.md` 时证据尚不存在，不豁免就永远产不出证据。
  asterwynd 同款：`_is_change_doc_write`（`workflow_guard.py:517-531`）。

### D5 `guard` 动词的接口（host 中立）+ **退出码按动词分表**

- 形态：`witnessloop guard --root <r> [--path <p>]... [--change <id>]`（宿主适配器抽 path）。
- 退出码：**0 = 放行**；**2 = 拦**（理由到 stderr）；**3 = 未接入 → 放行 + 提示**（本地不该拦未接入的仓）。
- **⚠️ 退出码语义按动词相反**：`guard` 的 `2=拦` 而 `check` 的 `2=用法错误`（`constants.py:75`）；
  `guard` 的 `3=放行` 而 `check` 的 `3=不放行`（`checkcmd.py:42`）。`docs/gate.md §6` 的退出码表**须按动词分开写**。

### D6 CC hook 分发 / 安装

- **随 plugin 分发**：`plugin/hooks/hooks.json` + 极薄 shim，把 PreToolUse 的 `Write|Edit` 事件映射成
  `witnessloop guard --path …`。**install = 装 plugin**（不再是 asterwynd 的「手动 cp 进 gitignored `.claude/`」）。
- **⚠️ R8（须写进安装文档）**：plugin **只带 hooks + shim，不带二进制**；`witnessloop` 不在 PATH 时 hook 命令以
  **非 0（非 2）** 退出 → 按 CC 语义**不阻塞** → fail-open。⇒ 文档写明「装了 plugin **还要**装 CLI」。
- **⚠️ R7（机制未证实）**：`onFailure:"block"` 在本机 CC 官方 plugin 全树 **grep 0 命中**；「timed-out hook 不阻塞」
  **本地核不了** ⇒ 标**未证实**，实现期核实（若属实则 shim 需超时/`onFailure`）。

### D7 推翻 v1 决策（须显式记录 + 加守卫）

- v1（`docs/design.md:27` §2 点 6、`:145` §9 风险 4；`README.md:108`；`docs/reviews/grill-design.md:19`）：
  **强制落 CI，hooks 只 advisory**。
- 本 change：**hook 也强制**（本地层）。**不破坏架构**——hook 属**交互层**（本就 CC-first、host 特定），
  门禁层仍 host-agnostic（`guard` 动词 host 中立，任何宿主可调）。
- 动作：逐处改上述**四处** + **新建最小 ADR**（`docs/adr/0001-local-guard-hook.md`；`docs/adr/` 今日不存在）+
  **新增一条漂移守卫测试**钉新口径（`test_docs.py` 现无此措辞的守卫 ⇒ 漏改不会红）。

### D8 escape hatch 与**纠正**「绕过面」

- 保留逃生口：`WITNESSLOOP_SKIP_GUARD=1` 放行 + stderr 打一行「已跳过 guard」。**不写任何状态文件**（守「只读无状态」）。
- **⚠️ 纠正原稿的错误说法**：原写「agent 可以设 env 绕过」——**错**。CC 的 PreToolUse hook 是**外层进程**跑 `witnessloop guard`，
  agent 在会话内 `export …` 只改**自己那个 Bash 子进程**的环境，**改不了 hook 进程**。
- **真实绕过面**：(i) **改用 Bash 写文件**（`Write|Edit` matcher 不覆盖 Bash）；(ii) **不装/关插件**。
- 诚实边界：本地 `guard` 是「**防遗忘**」，**不是防对抗**；锚仍是远端 CI required check。

### D9 `check` 接入 evaluator + 回归红线 + **自伤面**

- `check` 对每个 change：要求**存在 `stage=grill` 的 manifest**，且**其报告正文合格**（D1 判据，块级）。
- **⚠️ 回归红线**：接上后本仓 `dogfood-bootstrap` **必须仍绿**（实测其 6 决策/6 OQ/6 确认合格）。
- **⚠️ 自伤面（2 条硬红，实现清单须含）**：`tests/test_cli.py:48-52`（`test_the_verb_surface_stays_small`，
  动词面恰为 4 个——加 `guard` 即红）、`tests/test_plugin.py:64-71`（`test_plugin_file_inventory_is_exactly_expected`，
  plugin 恰 4 文件——加 `hooks/hooks.json` + shim 即红）。`tests/test_docs.py:42-46` **不红**（只断言四动词**存在**），仅措辞同步。
- **对**接入方**是行为变更**：历史无 `stage=grill` manifest 的 change 会新增一条红 ⇒ README/gate.md 写明。
- **与 asterwynd 的**有意偏离**（Q7）**：asterwynd **事后** grill 门有**三重**豁免——(a) docs-only（`:379-383`）、
  (b) 无 `specs/*/spec.md`（`:385-389`）、(c) change type 不含 `DESIGN_TYPES`（`check_openspec_artifacts.py:742`，
  `DESIGN_TYPES={feature,refactor,process}`，`:32`）。witnessloop 的 change 契约**本就要求** `proposal/design/tasks/specs/reviews`
  齐备（`constants.py:39`），且 `check` **不解析 proposal 的 Change Type** ⇒「每 change 都要」是**自然结果**，**须明写**。

## 3. 接线点（实现清单）

- **⚠️ R1（先做）**：本 change 的 change 目录**当前缺 `tasks.md`、`specs/` 为空** ⇒ `check`/`manifest build` 当场红
  （`contract.py:97-100`、`manifestcmd.py:96-99`）。**先补** `tasks.md` + `specs/<cap>/spec.md`（空 `specs/` git 不跟踪）。
- `src/witnessloop/evidence.py`（新）：D1 的纯函数（复用 `contract.Finding`）。
- `src/witnessloop/guardcmd.py`（新）：D3/D4/D5 的路径分类与 change 解析。
- `src/witnessloop/cli.py`：加 `guard` 子命令。
- `src/witnessloop/checkcmd.py`：change 循环接入 evaluator（D9）。
- `src/witnessloop/constants.py`：`REVIEW_MANIFEST_REQUIRED_FIELDS` 加 `stage`（D2b）。
- `plugin/hooks/hooks.json` + shim（D6）。
- **⚠️ 改两处既有测试的期望集**：`tests/test_cli.py:48-52`、`tests/test_plugin.py:64-71`（D9 自伤面）。
- `docs/gate.md`（`guard` + `check` 正文校验 + **退出码分表**）、`README.md`（本地 guard 用法 + 装 plugin 还要装 CLI + 诚实边界）、
  `docs/design.md`（D7 四处）、**新 ADR**。

## 4. 风险

1. **R1（阻塞）**：本 change change 目录缺件（`tasks.md`/`specs`）⇒ 先补。
2. **R2（高，移植陷阱）**：照抄 asterwynd `- **决策**：` 前缀 ⇒ 本仓证据 0 命中 ⇒ 回归必红（D1）。
3. **R3（高，自伤）**：改 CLI 动词面 + plugin 文件清单 ⇒ **2 条测试硬红**（D9）；设计原稿漏了这两条。
4. **R4（中）**：D2/D9 措辞须对齐（净行为 fail-closed 红）。
5. **R5（中）**：`stage` 今日「写而不校」，D9 的定位键自身不在必填字段 ⇒ 纳入必填（D2b）。
6. **R6（中）**：D7 反转缺配套守卫 ⇒ 四处改 + 新建 ADR + 加守卫测试。
7. **R7（中，未证实）**：hook 超时是否 fail-open，本地核不了。
8. **R8（中）**：plugin 不带二进制 ⇒ 没装 CLI 即 fail-open；安装文档须写明。
9. **R9（低）**：设计引用的行号须精确（已按对抗验证校正）。
10. **R10（低）**：`guard` 与 `check` 退出码语义相反 ⇒ gate.md 按动词分表。
11. **R11（低）**：改 `plugin/**` 会触发 guard（`plugin/**` **在** `require_change_for`，`policy.json:11`）——
    正常流程证据先齐，**不自锁**；但「只在 `plugin/` 改一行又想绕过 grill」会被拦，属**有意**行为。
12. **R12（诚实边界）**：本地 guard 可被 Bash 写文件绕过、也可不装 plugin；锚是 CI。

## 5. 测试策略

- **单测（TDD）**：
  - `evidence.grill_evidence_findings`：合格样本 / `<3` 条 / **块级** `来源:`（含**续行**持有）/ 前缀变体
    `- **决策（Dn）**：` 与 `- **决策**：` 都要算 / `Open Questions` 未确认 / 占位（`待确认`）/ 缺节。
  - `guard`：命中 `require_change_for` 且缺证据 → 拦（exit 2）；证据齐 → 放；写文档 → 放；
    **推得 id 不命中现存 change 目录 → 放行 + 提示**；推不出 → 放行 + 提示；未接入 → 放行；`WITNESSLOOP_SKIP_GUARD=1` → 放行 + 留痕。
  - `manifest build` 的 `stage` 必填性（D2b）；`check` 对「stage 拼错」报可诊断的红。
- **端到端**：`check` 对「正文不合格」红；**回归**：本仓 `dogfood-bootstrap` 仍绿。
- **plugin**：`plugin/hooks/hooks.json` 存在且结构合 CC 格式（`matcher`/`command`）。

## 6. 文档影响

- `docs/design.md`：§2 点 6（`:27`）、§9 风险 4（`:145`）、§5.1/§5.2、§10（D7）。
- `docs/gate.md`：`guard` 动词 + `check` 正文校验 + **退出码按动词分表**。
- `README.md`：本地 guard 用法 + **装 plugin 还要装 CLI** + 诚实边界（D8）。
- `docs/reviews/grill-design.md:19`（D7 第三处）。
- **新 ADR**：`docs/adr/0001-local-guard-hook.md`。
- **新漂移守卫测试**：钉「hook 已从 advisory 改为强制」的口径（D7）。
- ⚠️ `tests/test_docs.py` 既有守卫（`VERB_SURFACE_DOCS` / `RUN_ID_DOCS` / `IDEMPOTENCY_DOCS` 含 `README.md`/`docs/design.md`/`cli.py`）。

## 7. Pre-Implementation Review

**已确认决策（grill 证伪后确认 · 来源 `grill-reviewer-grill-evidence-gate-2026-10-11`）**：
#2 属实（`check` 真不读正文）；`--stage` 写而不校；D4 死锁规避成立；**D6 的 CC hooks schema 可定案**（本机官方 plugin 实证）；
D9 回归红线可满足；D7 四处需改且无测试兜底。

**必须修改（已整合 · 来源 `grill-adversarial-reviewer-grill-evidence-gate-2026-10-11`，3 轮封顶 PASS）**：
- **移植陷阱**（R2，已复现：asterwynd 判定于 dogfood = 0 命中）⇒ D1 判据**块级**。
- **D2/D9 措辞对齐**（净行为 fail-closed 红）。
- **D3 补「推得 id 必须命中现存 change 目录」**（照搬 asterwynd `:348`）。
- **D8 纠正绕过面**（Bash 写文件 / 不装 plugin；env 那条错）。
- **自伤面红数**：2 条（`test_cli` / `test_plugin`），非 3 条。
- **`defer` 不存在**（正确集 `allow|deny|ask`）。
- 行号校正：`manifestcmd.py:137`、`workflow_guard.py:364/379-391/409-417/517-531`、
  `check_openspec_artifacts.py:143-151/739-796`、`policy.json:11`。
- R7 标**未证实**；R11 删「不在 `require_change_for`」。

**Code-Resolved 结论**：本 change change 目录当时不合契约（缺 `tasks.md`、`specs/` 空）⇒ 先补（R1）。

**用户确认**：Q1–Q7 **全按推荐**（2026-10-11）；逐条答复见 `reviews/grill-review.md` 的 `## User Confirmation`。

## 8. Open Questions（停轮待用户确认）

- **Q1** scope：本 change = `check` 正文校验（#2）+ `guard` + hook（B 轨）合一，还是拆两个？
- **Q2** `guard` 推不出 / 推错 change id 时：fail-open（放行 + 提示）还是 fail-closed（拦）？
- **Q3** 「grill 报告」定位：保留 stage 名 `grill`（+ 是否把 `stage` 纳入必填）？是否收紧 `--stage` 值域？
- **Q4** escape hatch（`WITNESSLOOP_SKIP_GUARD`）要不要？「跳过留痕」怎么做？
- **Q5** 是否**同时**提供 git-hook（pre-commit/pre-push）适配器，还是只做 CC hook（延后）？
- **Q6** evaluator 判据的精确口径（entry = 顶层 bullet+续行；「带来源」= 块内命中；占位字面集照搬 asterwynd）——是否照此定？
- **Q7** `check` 是否对**每个** change 都强制 grill 证据（含 docs-only / 非 feature 类）——作为与 asterwynd 的**有意更严**？

（每条的具体例子与推荐答案见 `reviews/grill-review.md` 的 `## Open Questions`。）
