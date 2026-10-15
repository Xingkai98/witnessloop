# Tasks: archive-arrival-recognition

> **测试先行**：第 2 节（测试）先于第 3 节（实现），先写后实现。
> **本 change 的核心风险是「把豁免面开大」**（`archive-awareness` 的 C3 教训：只让 `_require_change` 闭嘴的实现
> 会让「改了 `src/**` 却零 change 证据」的 PR 变绿）⇒ 每条新授予都必须配一条**同等强度**的证据门用例。
> ⚠️ 本文件与 `design.md §2 / §5 / §7.2`、`specs/archive-awareness/spec.md` 逐条对齐；
> 改动这三处时**必须一起改**（R1 的 M-DOC1/M-DOC2/M-DOC3 就是三处漂移）。

## 0. 设计追问与用户确认（前置门，不完成不开工）

- [ ] 0.1 用独立零记忆设计追问（`grilling` skill 或等价流程）对 `design.md` 做追问，产出结构化决策记录到 `reviews/grill-design.md`（`## Confirmed Decisions` ≥ 3 条）。✅ 已完成（M1–M7 已回写）。
- [ ] 0.2 把 `design.md` `## 停轮问题` 的 **Q1–Q3**（R1 之后重排：名识别守卫 / stale 暗房 / 嵌套归档布局）
  逐条停轮抛给用户，每条附**本 change 真实场景的具体例子**（参数 / 输入输出 / 前后对比）与推荐值，等待明确答复。
- [ ] 0.3 把答复逐条记进 `reviews/grill-design.md` 的 `## User Confirmation`（格式 `- **Q<n>**: 用户答复：<实质内容>；确认时间: <date>`，不得写「按推荐」这类占位）。
- [ ] 0.4 跑设计阶段审阅闭环（独立零记忆审阅者 → 对抗分析 → verdict → 修 → 再审，**直到收敛**）：
  产出 `reviews/grill-adversarial.md`（R1，✅ 已完成）与 `reviews/grill-adversarial-r2.md`（R2，跑完 R1 的必须修改项之后）。
  **收敛判据 = 一轮下来没有新的可证伪项、且所有「必须修改项」都已落库**；没有轮数上限。
  能由代码判定的问题用**带 `文件:行号` 证据**的答案移出停轮队列。

## 1. 规格

- [ ] 1.1 修改 `archive-awareness` 规格：把「归档 move 使该 change 进入集合」改为
  「**归档目录的到达**使该 change 进入集合」，判据写成**五条**（见 `design.md §2 D1`），
  并写死 `SHALL NOT` 依据逐文件改名分 / `R100` / `-M -C` 的副本检测启发式。
- [ ] 1.2 重写否定面 Requirement：保留并**升级**「不得给 base 里已存在的归档目录授予资格」；
  **注明**旧否定面 N2 / N7 被本 change 反转及其理由；把「整份复制仍在的 change 目录」列进不授予面。
- [ ] 1.3 新增「到达集合的用途共用同一份判定」（归属 / 幽灵 id 排除 / 保护写豁免），
  并把 D4 的**收窄**（源目录仍在 head 里 ⇒ 不排除）与 D5 的**旧侧条件**（`old_path` 须落在 active change 目录下）写进正文。
- [ ] 1.4 新增「到达方式不改变证据门槛」的对称性不变量，并给「零证据归档 change 照样逐条点名」的防绕过用例。
- [ ] 1.5 新增「内容来源」判据的正文与 Scenario（`cp -r` 整份复制 / 归档目录改名 / 组织型子目录 / base 同路径是 blob）。
- [ ] 1.6 同步 current spec 到 `openspec/specs/archive-awareness/spec.md`，并按本仓政策追加解释事件（受保护路径）。

## 2. 测试（先行，先写后实现）

- [ ] 2.1 **到达判定的纯函数用例**（注入式**树读取器**，不碰真 git）：目录新增 ⇒ 到达；
  基准树里已有 entry（tree **或 blob**）⇒ 不到达；head 里不是 tree / 不含必需件 ⇒ 不到达；
  树读不出来 ⇒ fail-closed。
- [ ] 2.2 **出生即归档**：base 无此 change、head 有 `archive/<name>/`（全 `A`）+ 改 `require_change_for` 路径 ⇒ 退出码 0。
- [ ] 2.3 **move 内带内容改动**：全 `R<100`（含重建过的 manifest）⇒ 退出码 0，且**无**幽灵 active id。
- [ ] 2.4 **纯 move 回归**：全 `R100` 的行为逐条与改动前一致（今天绿 ⇒ 修后绿）。
- [ ] 2.5 **对称性不变量**：同一份 change 内容，active 与 archive 两种位置判绿判红结论相同。
- [ ] 2.6 **否定面**（`design.md §5.3` N1–N11 逐条）：尤其 N2/N3（触碰**已存在**归档目录）、
  N4（单文件移入既有归档目录）、N6（到达但零证据 ⇒ 逐条点名三份 stage manifest）、
  N8（把**已存在**的归档目录改名 ⇒ 不授予）、**N9（`cp -r` 整份复制 ⇒ 不授予）**、
  N10（组织型子目录 ⇒ 不是 target、不产生假阴性）、N11（base 同路径是 blob）。
- [ ] 2.6b **改写既有测试**（逐条点名；⚠️ 前两条是**语义反转**，不是「修一下断言」）：
  1. `tests/test_archive_awareness.py:274` `test_rebuilding_a_moved_manifest_in_the_same_diff_is_rejected`
     —— 断言「move + 重写被 move 的 manifest（`R<100`）⇒ 红 + 幽灵 active id」，**这正是本 change 要修好的形态 ii**
     ⇒ 反转为「退出码 0、无幽灵 id」，并改名（如 `..._is_accepted`）。
     ⚠️ 它**不在** R1 的必须修改项里（grill M6 只点了 `:541`）——本稿补上；
  2. `:541` `test_N2_a_forged_archive_grants_nothing` —— 「伪造归档（无源、件齐）」从**不授予**变成
     **授予但由证据门禁拦下**：断言 `"没有任何 change 目录" in err` 必失败 ⇒ 改为断言缺 manifest / 缺 stage 那几条 finding
     指向**归档路径**；
  3. `:494` `test_the_summary_counts_directories_not_deduped_ids_on_a_tie` —— 其构造里 `archive/x/` **只有** `notes.md`
     （不含必需件）⇒ D1 第 2 条下它不是 target ⇒ 报 1 而非 2。改写构造以保住「同一 id 撞两个目录、两份都校验」的**意图**：
     base 上 active `x`（件齐）；feature 上把**整个** `changes/x` 纯 move 到 `archive/x`，**并**新建一个含必需件的 `changes/x`；
  4. `:109` `test_grant_requires_the_target_name_to_recognize_the_source_id` —— 直调 `contract.archive_grant`，
     而 `archive_grant` 在本 change 里失去全部调用点（见 3.6）⇒ 随实现删除 / 改写为新纯函数的用例
     （保留「`R<100` 也授予」这条断言——判据换了，语义不变）；
  5. `:49` 的 `_targets()` 助手与 A 节四条纯函数用例（`:87` / `:101` / `:134` / `:471`）——
     `change_targets` / `changed_change_ids` **签名变了**（要注入树读取器）⇒ 助手改为注入**假树**，四条用例按新接口改写（语义不变）。
  ⚠️ **对照（不要误改）**：`test_N4`（`:577`）/ `test_N6`（`:600`）断言的 `"没有任何 change 目录"` 在 D1 下**仍成立**
  （目标目录在基准树里存在）；`test_deeper_events_file_is_not_read`（`:378`）仍绿，但**理由变了**
  （从「`archive/**` 一律排除」变成「`archive/notes/` 不含必需件 ⇒ 不是 target」）——注释应更新。
- [ ] 2.6c **基准 revision 用例**：base 分支在分叉点后前进过（`base` ref 树与 `merge-base` 树不同）⇒
  到达判定与 diff 成员口径一致（D1 第 1 条）。
- [ ] 2.7 **接入方真实形状的集成用例**：用接入方 PR 的那两份 diff（33 文件全 `A` / 16 文件含 `R<100>`）各一条，断言修前红、修后绿。
- [ ] 2.8 **fail-closed 用例**：树读不出来 ⇒ 报 finding、不授予、退出码非 0。
- [ ] 2.9 **内容来源用例（N9 + 防误伤对照）**：`cp -r` 整份复制 ⇒ 不授予；
  **同构造下真的 `git mv`**（源目录在 head 里消失）⇒ 绿。
- [ ] 2.10 **组织型子目录用例（N10）**：`archive/2026/10-15-foo/…` ⇒ `archive/2026/` 不是 target、
  不产生「缺少必需件」；并钉住 `archive/notes/sub/workflow-events.jsonl`（`:378`）的行为与今天一致。
- [ ] 2.11 **D4 收窄用例**：到达目录 + 同 diff 里把**另一个仍在 head 的** active change 的文件搬进它 ⇒
  那个 change 仍按 active 校验（不得静默消失）。
- [ ] 2.12 **D5 旧侧条件用例**：把受保护文件（`git mv openspec/specs/x.md …`）搬进到达目录 ⇒ **仍要**解释事件。

## 3. 实现

- [ ] 3.1 `src/witnessloop/gitutil.py`：新增树查询帮助函数
  （`tree_entry` / `tree_entries`，**不带尾斜杠**查路径自身，`fail-closed`：读不出 ⇒ 抛错 / 返回失败，调用处报 finding）。
- [ ] 3.2 `src/witnessloop/contract.py`：新增到达判定（树读取作为**注入谓词**，判定本体为纯函数），
  实现 D1 的五条判据（含**内容来源**判据）。
- [ ] 3.3 `src/witnessloop/contract.py`：改 `changed_change_ids` 的 `archived_sources` 为**到达组 + 源目录已不在 head**口径（D4 收窄）。
- [ ] 3.4 `src/witnessloop/contract.py`：改 `change_targets` 用到达集合产出归档 target；保留名识别守卫（对**有源**的到达）。
- [ ] 3.5 `src/witnessloop/checkcmd.py`：`_check_protected_writes` 的保护写豁免改用**到达集合 + 旧侧条件**
  （`old_path` 须落在 active change 目录下）；保留「对已存在归档目录的修改 / 删除仍要事件」；
  构造并传入真 git 版的树读取器。
- [ ] 3.6 `src/witnessloop/manifestcmd.py`：**本 change 不改它**（grill M4 实测它**不调用** `change_targets`，
  按磁盘存在性解析 `resolve_change_dir`，`manifestcmd.py:33-48`）。
  实现时若确认 `manifest build` 无需感知「到达」，在此写明理由；若需要，**另列**要共享的函数，不得含糊带过。
  ⚠️ 初稿的「与 `check` 共用同一份 target 解析（单一实现）」是**事实错误**，已订正（R1 的 M-DOC1）。
- [ ] 3.7 核对：`is_archive_move` / `archive_grant` 若失去全部调用点则删除；若仍被别处使用则逐点确认语义未被削弱（不得留「看似归档」的半套判据）。

## 4. 验证

- [ ] 4.1 `uv run pytest -q`（新增用例 + 全量回归）。
- [ ] 4.2 用**接入方真实提交**复算 `proposal.md` 的表（三份 diff × 两个 ref），把原始输出要点记进 `reviews/` 或 PR 描述。
- [ ] 4.3 本仓 `witnessloop check` 对**本 change 自己**判绿（自举）。
- [ ] 4.4 逐条复算 `design.md §5.3` 的否定面（N1–N11），确认**照样红**。
- [ ] 4.5 **用真 CLI 复跑 R1 的 F1 端到端**：R1 只能拿 active 目录做 proxy（当时还没实现）；
  实现后必须用**到达的归档目录**重跑「`cp -r` 现成证据 + 改两个 manifest 字段 + 改 `src/**`」，确认 `check` 红。

## 5. 实现后独立审阅闭环

- [ ] 5.1 跑独立审阅闭环，产出 `reviews/building-review.md`（CHANGES_REQUESTED 则修复并加回归测试，再审，直到收敛）。
- [ ] 5.2 收敛后清理中间轮产物，或把最终版落到规范名（避免孤儿报告）。

## 6. 文档

- [ ] 6.1 `docs/gate.md`：§5.1.1 / §4 / §3.2 / §6 按新判据同步；删掉「R100 要求」的表述，
  补「树不可读 ⇒ fail-closed」与「整份复制既有 change 目录 ⇒ 不授予」。
- [ ] 6.2 `README.md`：接入指引的归档时序一段按新判据改写（**不**把出生即归档写成推荐流程）。
- [ ] 6.3 检查文档影响面：`docs/` 全量与本次判据相关的段落（关键词：`R100`、`归档 move`、`is_archive_move`、`archive_grant`）。

## 7. 收尾

- [ ] 7.1 确认三份 stage manifest 在**所有内容提交之后**重建，且 `reviews/` 处于「每份 `.md` 都被绑定」的一致状态。
- [ ] 7.2 归档 move **仍建议**放最后、独立提交（回归面用它钉「纯 move 逐条不变」）；
  但**不再强制**——形态 ii（move 内带内容改动）本次已是**被支持**的形态，若采用它，须同时验证 2.3 那条集成用例。
- [ ] 7.3 从 backlog / 相关跟踪处移除本 change 条目，并追加解释事件。
- [ ] 7.4 回链 issue #26：补完成说明 comment 并关闭。
