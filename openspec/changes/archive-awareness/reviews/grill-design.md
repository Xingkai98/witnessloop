# Grill: archive-awareness 设计追问

> 独立零记忆审阅者产出（2026-10-14）。**READ-ONLY**：未改动 `src/`、未 commit、未改被审 worktree 的 git 状态。
> 全部实测在隔离副本（`git archive HEAD | tar -x` + `git init`）里跑，见 `## Reviewer` 的方法栏。
> 结论按「挑战而非确认」写：下面每条 Confirmed Decision 都是**我自己重跑出来的**，与被审文档的出入写在「订正」里。

## Reviewer

- run id: `grill-reviewer-archive-awareness-ae992565ee21`（确定性兜底锚 = change id + 被审 revision 短摘要；宿主 session `aaf99cf1-0bbc-4116-9098-ee3bf825c924`）
- 时间: 2026-10-14T15:13:48Z
- 被审 revision: `ae992565ee2162e5b272af471e9adf895e7f83fb`（基线 `origin/main`；change 目录**未提交**，四份文档 `sha256sum` 汇总 = `616611106a6486abb92195f56664c45e256efdb86da41aa05a14ff2608abb6e2`）
- 方法: ① 读 `gh issue view 21 --json`、`proposal/design/tasks/spec` 四份、`templates/grill.md`、`docs/gate.md`；② 在 `/tmp/wlgrill/**` 造 9 个对照仓（C1b / C1b 变体 / C2 / C3 / 症状② / 症状③ / N1·N2·N2b·N4 / 借壳 / 往返），全部用 `uv run witnessloop --root <副本>` 跑**本 worktree 的代码**；③ 对纯函数做直接调用（`is_archive_move` 10 组、两条 glob、把现有校验器直接喂 `change_id="archive/<name>"`）；④ 全称/计数一律 `grep -c` / `wc -l`。
- 基线复核: `uv run pytest -q` = **496 passed**（与立项稿一致）。

## Confirmed Decisions

- **决策：三条症状在本仓当前树全部复现，且立项稿点名的所有 `文件:行号` 未漂。**
  理由（我的实测，不是转述）: ① `check --base HEAD~1 --head HEAD` 在「R100 归档 + 改 `src/app.py`」的仓里给 `…6 个变更文件，0 个 change 目录` + 唯一那条 `_require_change` 文案、`EXIT=1`；② 同一个仓（已归档）`manifest build --change gwa` 与 `--change 2026-10-14-gwa` **都**报「change 目录不存在」`EXIT=1`，把归档目录 `git mv` 回 active 后同参数 `EXIT=0`；③ 归档 change 的事件点名 `openspec/specs/guard.md`、同 PR 写该文件 ⇒ 报「没有结构化解释事件」`EXIT=1`。
  行号逐条复核（`grep -n`）: `contract.py:34/38/58/89/94/121/250`、`checkcmd.py:73/79/86/96/98/105/188/194`、`events.py:83`、`manifestcmd.py:72/149`、`policy.py:73-74` —— **全部命中，无漂移**。
  `来源: grill-reviewer-archive-awareness-ae992565ee21`
- **决策：`changed_change_ids` 的归档排除本身是对的；缺陷是「排除之后没有补上归档事实」——立项稿的根因判断成立。**
  理由: 我直接调用真函数：对上面那份归档 diff，`contract.changed_change_ids(changes, "openspec/changes")` 返回 `[]`；`archive` 从未作为 id 出现（`contract.py:75` 的 `continue` 覆盖 `archive/**`）。排除若拿掉，`archive` 会作为首段进入 id 集合、被 `validate_change_dir` 要 `proposal.md`——与 `contract.py:59-63` 的注释一致。
  `来源: grill-reviewer-archive-awareness-ae992565ee21`
- **决策：立项稿「新发现」（归档让三条证据门禁一起静默失效）成立，且 D2 修法把它从「1 项红」变成「4 项红」而不是「0 项红」。**
  理由（对照仓，全部我自建自跑）: **C1b**（同一个 diff 里建齐件、零 manifest 的 active `x` + 改 `src/app.py`）= `EXIT=1，4 项`（缺 review manifest · 无 stage=grill · 无 stage=grill-adversarial · 无 stage=building）；**C3**（同 change 同 PR 归档 + 改 `src/app.py`）= `EXIT=1，1 项`（只剩 `_require_change`）；**C2**（纯归档、零 manifest）= `EXIT=0`。
  再进一步（**这一步立项稿没做**）: 我把 D2 派生出的 id 直接喂给现有校验器（`validate_change_dir(root, pol, "archive/2026-10-14-x")` + `validate_review_manifests` + 两条 stage 门，label 取 `openspec/changes/archive/2026-10-14-x`），对 C3 那个仓跑出 **恰好 4 条**，全部落在归档路径上 ⇒ 「只让 `_require_change` 闭嘴会开绕过口」这个立论**成立**，`_require_change` 不能改成豁免。
  `来源: grill-reviewer-archive-awareness-ae992565ee21`
- **决策：症状 ② 报错里「diff 里出现了它的文件，但目录不在工作树中」是固定文案，不是对本次 diff 的观察。**
  理由: `manifestcmd.run_build` 全程不调用 `gitutil.changed_files`（只调 `rev_parse` / `resolve_diff` 类），那句字面量在 `contract.py:94`；实测里我**根本没有 diff**（同一 commit 上直接 build），文案照旧出现。
  `来源: grill-reviewer-archive-awareness-ae992565ee21`
- **决策：`is_archive_move`（`contract.py:38-55`）是可用的**防伪锚**，D2「一行都不改」的判断正确。**
  理由: 直接调用 10 组构造的 `Change`：
  `R100` active→archive = **True**；`A archive/…`（N2 伪造）= False；「先建后 `git mv`、同一 commit」（N2b，实测 `git diff` 只报 `A`）= False；`M archive/…`（N4）= False；`R087`/`C100`/源本来就在 archive/把受保护 spec 挪进 archive/在 active 内建目录 全部 False；`archive → active`（搬回来）= False。
  ⇒ N2/N4 的「不生效」是**结构性**的，不依赖实现细节。
  `来源: grill-reviewer-archive-awareness-ae992565ee21`
- **决策：「把归档 change 放回集合、按归档路径走同一套校验」在现有代码结构下**真能落**，且往返闭合。**
  理由: 我造了一个证据齐备的 change `y`（真 `manifest build` 出三份 manifest），`git mv` 到 `openspec/changes/archive/y/` 之后，把 `change_id="archive/y"`、label `openspec/changes/archive/y` 喂给**现有**的 `validate_change_dir` / `validate_review_manifests` / `grill_evidence_findings_in_change` / `stage_manifest_findings_in_change` ⇒ **零 finding**（hash 绑定、孤儿绑定、`reviewer≠author`、git span 全程在归档目录上正常工作；`contract.py:250` 取 label 末段，与归档目录名自洽）。⇒ D7 的「只留一份实现」不是愿望而是低风险。
  `来源: grill-reviewer-archive-awareness-ae992565ee21`
- **决策：「拿别人的旧报告当自己的证据」**今天就已可行**，不是本 change 引入的新类。**
  理由: 我实测了一个**不用任何归档技巧**的攻击：碰一下**已存在的 active change `q`** 的无关文件（`M openspec/changes/q/notes.md`）+ 改 `src/app.py`，随后在攻击 HEAD 上重建 `q` 的三份 manifest（复用 `q` 的旧报告）并提交事件 ⇒ `check` **`EXIT=0`（绿）**。
  意义: 这校准了「归档感知会不会开新绕过面」的严重性——工具的既有边界本就是「保证本 PR 里存在一个**证据齐备的 change**，不保证证据是为这段代码写的」（`docs/gate.md §7`）。见 `## 风险` R1 的逐条攻击结果。
  `来源: grill-reviewer-archive-awareness-ae992565ee21`

### 订正（立项稿里被我的实测改掉的说法）

1. **`proposal.md:43-45` 的 C1b/C3 对照表数字不完整、C1b 那一行自相矛盾。** 表里 C1b 写「**5 个变更文件**、**4 项红**」——这两者不可能同时成立：我实测「change 目录里**有** `reviews/` 实体文件」= 6 个变更文件 / 4 项红；「**没有** `reviews/` 目录」= 5 个变更文件 / **5** 项红（多一条「缺少必需件 reviews」）。C2/C3 两行（5 文件 0 项 / 6 文件 1 项）与我的实测**逐字一致**。⇒ 结论不受影响，但 C1b 那行必须拆成两个可重跑的对照（`design.md:36` 的控制台块同源）。
2. **`design.md:332`「它是 §1.2 那个绕过口的**唯一**闭合方式」为假。** Q1 里的 `code-gated` 选项**同样**闭合 §1.2 的绕过口——C3 那份 PR 的 `code_hits` 非空（我刚实测过它 4 项红、其中三条 stage 门就是 `code_hits` 拉起来的），所以 code-gated 在 C3 上会全量校验。uniform 的真正优势是「没有第二套判据」而不是「唯一」。
3. **`design.md:150` + `design.md:293`（N5）+ `tasks.md:54`（D3）+ `spec.md:99-102` 的否定断言为假，而且方向反了。** 见 `## 必须修改项` M3。
4. **`design.md:237-238`（R2 的补救路径）方向是错的。** 见 M2。

## Code-Resolved Questions（**建议移出停轮队列**：能由代码/证据定案，带 `文件:行号`）

- **Q2〔归档态 change id 的口径〕→ 只能是**归档目录名**，不是「源 id」，不需要用户拍板。**
  证据: `manifest build` 侧**没有 PR diff 口径**——`manifestcmd.run_build`（`:49` 取 `args.change`，`:61` 拼 `<changes_root>/<id>`）从不调用 `gitutil.changed_files`；要 `--change <源 id>` 命中，只能在 `archive/` 下按 `*-<id>` 后缀猜，而 `design.md:96`/`:340` 自己已承认那会有「同一 id 归档两次」的歧义。再叠加 D7 的「id→目录只留一份实现」（`design.md:170-177`），两个选项里只有一个可落。
  残余代价（`design.md:245-246` 的 R4）是「`change_id` 字面变长 ⇒ 下游自建工具可能读不惯」，那是**文档项**不是决策项。
- **Q3〔触碰归档文件算不算「该 change 出现在本次 diff」〕→ **不算**。**
  证据: 「算」= 任何 `M/D archive/<name>/**` 都能把该 change 拉进集合 ⇒ 比「什么都不建」更省事，且可重复；它与本 change 自己写的 `spec.md:36-43`「唯一取得方式是归档 move（R100 + 源在 active）」**直接矛盾**，也与 N4 互斥。`is_archive_move` 对 `M`/`D` 恒 False（我已实测），机械上本来也不会「算」——所以这条不是取舍，是要不要写进否定面清单。
- **Q4〔归档事件的授权面要不要收窄〕→ 收窄在今天的代码里**不可实现**，不必拍板。**
  证据: `events.Event`（`events.py:28-46`）**根本没有 `change_id` 字段**，`load_events_file`（`:69-76`）只取 `event_type/artifact_path/reason/approved_by` 四个键，`covers`（`:88-103`）也只比 `artifact_path`。要「收窄」就得新增字段 + 新增「事件只能豁免自己 change 的路径」语义 = 新增一条 change↔路径 映射，而本 change 把它列为非目标（`design.md:70-71`）。⇒ 剩下的只是「文档要写明池子变大」（`design.md:354` 已写），属任务不属决策。

## Open Questions（**只有这一条必须用户拍板**）

- **Q1**: 归档 change 的校验深度——归档 change 进集合后校验到哪一层，即**接不接受「纯归档 PR 也会红」这条新红类**（`design.md:236-239` 的 R2）。
  **例子（分叉必须在纯归档 PR 上才看得出来，`design.md:326-329` 那个例子选错了场景）**：
  - 接入方 PR「实现 + 归档」：`git mv openspec/changes/guard-write-allowlist openspec/changes/archive/2026-10-14-guard-write-allowlist` **且**改 `src/agent/config.py`。该 PR `code_hits` 非空 ⇒ **uniform 与 code-gated 结果完全相同**（都跑三条 stage 门）⇒ 这个例子区分不出两个选项。
  - 真正分叉的例子：**纯归档 PR**，把 `legacy-x`（`reviews/grill-review.md` 的 `## Confirmed Decisions` 只有 2 条）搬进 `archive/2026-10-15-legacy-x`，**一行代码都不改**。uniform ⇒ **红**（`openspec/changes/archive/2026-10-15-legacy-x/reviews/grill-review.md：…少于硬门槛 3 条`），补救是在本 PR 内补齐这份报告随后**按归档目录名重建它的 manifest**（见 M2）；code-gated ⇒ **绿**（本 PR 无 `code_hits`）。
  - `contract-only` 已被机械排除（我实测 C3 的形态：归档 + 改代码但只查必需件 ⇒ 集合非空 ∧ 三条 stage 门不跑 ⇒ **0 项红 = 放行**），不是选项。
  ➡️ **推荐 uniform**（理由改成：避免第二套判据，而不是 `design.md:332` 那句「唯一闭合方式」）；真正的决策点是「愿不愿意让**纯归档 PR**也吃这条新红类」，以及不接受时改走「纯归档 PR 拆开」（注意：拆开后纯归档 PR 仍会吃 manifest / grill 正文那两条）。

## 风险

1. **R1（高·本 change 的绕过面）——「部分归档 move」能凭空授予一个已归档 change 的资格，且让**源 change 静默逃检**。** 逐条攻击结果（全部实测）：
   - **N1**（只改 `src/`、什么都不建）：**红** ✓（`EXIT=1`，点名 `src/app.py` + `require_change_for`）。
   - **N2**（**新建** `archive/2026-10-14-fake/**`、无 active 源 + 改 `src/`）：**红** ✓（`git diff` 是 `A`、无 `old_path` ⇒ `is_archive_move=False`，直接调用实测确认）。
   - **N2b**（**先建后 `git mv`**、同一 commit，看起来最像一次真归档）：`git diff --name-status --find-renames` 只给 `A`（git 在 base 里找不到源，不做改名配对）⇒ 仍 **红** ✓。
   - **N3**（`rmtree` 删 change 目录）：今天**红** ✓（`test_touched_but_absent_change_dir_is_reported` 钉住；D2 不碰这条路径）。
   - **N4**（`M` 归档目录里已有文件 + 改 `src/`）：**红** ✓（`M` ⇒ `is_archive_move=False`）。
   - **N5**：❌ **断言本身是假的**（见 M3）。
   - **⚠️ 未列出的第 6 种（`design.md:186-194` 的边界表、`spec.md:36-43` 的「三个否定面」都没收）**：把**任意 active change 的任意一个文件** R100 改名进**已存在**的归档 change 目录。
     实测: `git mv openspec/changes/z/notes.md openspec/changes/archive/y/notes.md` ⇒ `git diff` = `R100`；`contract.is_archive_move(...)` = **True**；按 `design.md:107-108` 的 D2 规则「取新路径里 `archive/` 之后的首段」派生的 id = **`y`**（≠ 源 change `z`，也≠被搬的东西）；`changed_change_ids` 今天 = `[]`。
     后果: `z`（源）因为 `archived_sources` 排除（`contract.py:70`）**不进集合**，`y` 进集合并通过（我另测：归档路径上证据齐备的 change 在校验器下零 finding）。
     严重性**校准**（重要，别过度报警）: 这**不是新类**——见 Confirmed Decision 6，今天「碰一下 active change + 重建它的 manifest」就能达到同样的绿，本工具从来只保证「存在一个证据齐备的 change」（`docs/gate.md §7`）。而且攻击要真变绿，还得在攻击 HEAD 上重建 `y` 的 manifest（否则 `_check_git_span` 的 `stray` 会因 `src/app.py` 非证据而报「审阅的是旧 revision」）。⇒ **不阻塞**，但 `spec.md:36`「唯一取得方式」那句 + 否定用例清单有**盲点**：一个把「部分 move 也算归档」实现出来的版本，会让 N1–N5 **全绿**。
2. **R2（高·必修）——归档目录名 ≠ 源 id 时，该 change 的**全部**既有 manifest 立刻被判「与目录不符」，且补救动作本身会撞受保护路径。** 见 M2。
3. **R3（中）——测试盲点让 R2 永远不被 TDD 抓到。** 本仓 `tests/test_archive.py:26` 的归档是 `archive/add-retry`（**与源 id 同名**），所以 `contract.py:250` 的末段比对恰好成立、永远不会暴露 R2；`design.md:263-267` / `tasks.md:36-38` 计划的往返用例也是「先归档、再 build」的顺序，同样绕过。必须在 §5.1 补一条「**先 build、再归档到 `<date>-<id>`**」的先红用例。
4. **R4（中）——症状 ③ 的文档面比 `design.md:299-300` 写的更大。** `docs/gate.md:245-246` 只是「不为真」的一句；但**没有任何测试钉住**「`archive/**` 的事件不被读」这条既有行为（我 `grep -rn archive tests/ | grep -v test_archive.py` = **0 命中**），所以 G2 是一次**没有守卫**的行为翻转——建议顺手补一条（真否定，见 M3）。
5. **R5（低）——D4 的解析顺序在「同名 active + archive 同时存在」时 active 优先**，而 `check` 侧派生的 id 是归档目录名 ⇒ 两侧可能指向不同目录。fail-closed（active 那份会被按契约校验），但值得在 `docs/gate.md §3.2` 写一句。另：`manifest build --change archive` 会因为 `<changes_root>/archive` 是目录而走「active」分支，报「缺少必需件 proposal.md」——文案会让人困惑，建议也在提示语里兜一句。
6. **R6（低）——性能与授权面**：`design.md` R7/R8 已写（事件池 +80 份、多一次 glob）。我复核了 `load_all` 本来就是全量读入内存（`events.py:80-85`），线性增长可接受。

## 必须修改项

- **M1〔高·`spec.md:36-43`、`design.md:186-194`、`tasks.md:57-63`〕**：@「只有真归档 move 才授予该资格」的否定面清单**不完备**——缺「**把 active change 的单个文件** R100 改名进一个**已存在的**归档目录」这一面（实测 `is_archive_move=True`、派生 id = 目标目录名 ≠ 源 id，源 change 还因此静默逃检）。
  两种收法，作者/用户择一并在 spec 里写明**为什么**：
  (a) **纯 diff 可判**：要求目标目录名与**源 id**一致（等于 `<源id>` 或以 `-<源id>` 结尾）——源 id 从 move 的 `old_path` 首段现成可取，只做后缀比对、**不解析日期**，对 `z → archive/2026-10-14-y` 直接拒绝；
  (b) **要求归档目标目录在 base 里不存在**（`archive/<name>/` 是本 diff 新建）——更严，但要查 base 树（`git ls-tree`），会打破 `tasks.md:9-11` A1 假定的「纯函数（只吃 diff）」性质。
  无论选哪个，都必须在 spec 的同一条 Requirement 里**显式写出这条否定用例**。
- **M2〔高·必须·`design.md:236-239`（R2 补救路径）、`design.md:322-332`（Q1 例子）、`spec.md:72-76`、`tasks.md:36-38`〕**：写入两条**今天没写、但一定会撞上**的连锁，并把补救顺序改正：
  1. **`contract.py:250` 的交叉校验取的是 label 末段**（我直接调用实测）：归档态 label = `openspec/changes/archive/2026-10-14-x`，末段 = `2026-10-14-x`，而**归档之前**用 `--change x` build 的 manifest 里 `change_id="x"` ⇒ 一归档就报
     `manifest.change_id='x' 与目录不符`（实测输出）。⇒ 「本 PR 内**先修证据、再归档**」（`design.md:238`）对 manifest **方向相反**：正确顺序是**先归档、再用归档目录名 `manifest build` 重建全部 manifest**（改名不做内容改动 ⇒ `report_hash`/`tasks_hash`/`spec_hash` 全部照旧成立，只有 `change_id` 变了）。
  2. **重建 = 覆盖已存在的 `reviews/*.manifest.json` = `M` 一个不变集路径**（`policy.py:22`）⇒ 每条覆盖都要一条解释事件。我实测：重建一个 active change 的三份 manifest 而不写事件，`check` 立刻给 3 条「受保护路径被写入，但没有结构化解释事件」；补上三条事件后 `EXIT=0`。⇒ 接入方「实现 → 归档 → 重建三份 manifest」这条链会**额外**吃 3 条解释事件，`design.md`/`tasks.md` 必须写明（否则会被当成新 bug 报）。
- **M3〔中·必须·`design.md:150`、`design.md:293`（N5）、`tasks.md:54`、`tasks.md:63`、`spec.md:99-102`〕**：N5 与那条 spec Scenario 的 Then **与所选实现相反**，必须换成真否定。实测（`pathlib.glob`，本仓语义同）：
  - `openspec/changes/*/workflow-events.jsonl` **命中** `openspec/changes/archive/workflow-events.jsonl`（`*` 匹配 `archive`）——N5 说它「不被当成任何 change 的事件」，**今天就是假的**，改完还是假的；
  - 新增的 `openspec/changes/archive/*/workflow-events.jsonl` **命中** `openspec/changes/archive/notes/workflow-events.jsonl`（`*` 匹配 `notes`）——`spec.md:99-102` 的 Given 举的正是这个例子，Then 却写「不被读」。
  ⇒ 改成实现真能保证的否定：`<changes_root>/archive/<x>/<notes>/workflow-events.jsonl`（**再深一层**）不被读；并在 `docs/gate.md §4` 诚实写明「`archive/` 一级下的非 change 目录里的同名文件**会被读**——与 active 一层今天的行为同款」。
- **M4〔低·`design.md:332`〕**：删掉/改写「它是 §1.2 那个绕过口的**唯一**闭合方式」——`code-gated` 同样闭合它（实测 C3 的 `code_hits` 非空）。
- **M5〔低·`proposal.md:43` + `design.md:36`〕**：C1b 那行的「5 个变更文件」与「4 项红」互斥；按实测拆成「有 `reviews/` 实体文件 ⇒ 6 文件 / 4 项」与「无 `reviews/` 目录 ⇒ 5 文件 / 5 项」两条，或统一到其中一种造法上。
- **M6〔低·`tasks.md:76-81`（G1–G5）〕**：`docs/gate.md` 与 `README.md` 都被 `tests/test_docs.py` 钉着，G1–G5 改写时必须不破：`IDEMPOTENCY_DOCS`（`tests/test_docs.py:104-127`）要求 gate.md 里**每个**「幂等」（现于 `:9`、`:52`、`:497`）要么讲 `init`、要么 ±2 行内带「固定 base 与 revision」；`Q3_DOCS` 禁「挡「忘了另开 run」」；`RUN_ID_DOCS` 要求「确定性」在场。**G3 要改写 `manifest build` 那一节（`docs/gate.md §3.2`），正是「幂等」密集处**——建议在 tasks 里点名这条守卫。

> 说明：本文件按任务要求落在 `reviews/grill-design.md`。⚠️ 它与本仓其余 change 的 `reviews/grill-review.md` **是同一件产物**（`templates/grill.md:91` 明写「`reviews/grill-review.md`（即 `grill-design.md`）」）。无论用哪个名字，**必须由 `stage=grill` 的 manifest 以 `report_path` 绑定**，否则 `check` 的孤儿规则（`contract.py:203`，`reviews/**/*.md` 逐个必须被某份 manifest 引用）会在本 change 自己身上判红。
