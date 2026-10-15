# Tasks: archive-arrival-recognition

> **测试先行**：第 2 节（测试）先于第 3 节（实现），先写后实现。
> **本 change 的核心风险是「把豁免面开大」**（`archive-awareness` 的 C3 教训：只让 `_require_change` 闭嘴的实现
> 会让「改了 `src/**` 却零 change 证据」的 PR 变绿）⇒ 每条新授予都必须配一条**同等强度**的证据门用例。
> ⚠️ 本文件与 `design.md §2 / §5 / §7.3b`、`specs/archive-awareness/spec.md` 逐条对齐；
> 改动这三处时**必须一起改**（R1 的 M-DOC1/2/3、R2 的 M3、R3 的 M5 都是三处漂移）。

## 0. 设计追问与用户确认（前置门，不完成不开工）

- [ ] 0.1 用独立零记忆设计追问（`grilling` skill 或等价流程）对 `design.md` 做追问，产出结构化决策记录到 `reviews/grill-design.md`（`## Confirmed Decisions` ≥ 3 条）。✅ 已完成（M1–M7 已回写）。
- [ ] 0.2 把 `design.md` `## 停轮问题` 的 **Q1–Q4**（Q1 名识别守卫 / Q2 stale 暗房 / Q3 嵌套归档布局 /
  Q4 第 5 条的**强度与能力天花板**）逐条停轮抛给用户，每条附**本 change 真实场景的具体例子**
  （参数 / 输入输出 / 前后对比）与推荐值，等待明确答复。
- [ ] 0.3 把答复逐条记进 `reviews/grill-design.md` 的 `## User Confirmation`（格式 `- **Q<n>**: 用户答复：<实质内容>；确认时间: <date>`，不得写「按推荐」这类占位）。
- [ ] 0.4 跑设计阶段审阅闭环（独立零记忆审阅者 → 对抗分析 → verdict → 修 → 再审，**直到收敛**）：
  - `reviews/grill-adversarial.md`（R1）✅ 完成：证伪 3 条（F1 copy 绕过 / F2 组织型子目录 / F3 改 id）；
  - `reviews/grill-adversarial-r2.md`（R2）✅ 完成：证伪 3 条（A1 豁免洗白 / A2 指纹形态可零成本打断 / A3 扫描面盲区）+ B1/B2，判定**不收敛**；
  - `reviews/grill-adversarial-r3.md`（R3）✅ 完成：证伪 5 条（A1 报告挪出 `reviews/` / A2 每个证据文件各加一字节 /
    A3 路径形态 / A4 `D`+`A` 幽灵 id / B1 `:494` 配方 / B2 `test_N6` 误判 / B3 模板骨架），判定**不收敛** ⇒ 已回写；
  - `reviews/grill-adversarial-r4.md`（R4）✅ 完成：**安全级新绕过 0 条**（R3 附注三处逐条复算成立：新 `Ev(A)` 抓回了挪出
    `reviews/` 的证词 / 天花板与 Q4 口径一致 / D 侧排除键不误排除），但报出 4 条**文档级**可证伪项
    （spec 残留伪等价论证、计数与实列不符、完全旁路的机理写窄、指针失效）⇒ 已**逐条机械核对**落库；
    另附低危：`required_artifacts:[""]` 可中和判据 2（只多报红、非绕过）、「到达组」需定义、空 `reviews/` 的树/工作树口径。
  - `reviews/grill-adversarial-r5.md`（R5）✅ 完成：R4 的 4 条**已核实全部落库**（另有 2 条措辞项）；判**不收敛**，
    新报 2 条**影响判红判绿**的可复算项：① `Ev(A)` 对**符号链接**失明（`120000` 的 blob 是链接文本）⇒ 已加
    「证据项须是普通文件、`120000`/`160000` ⇒ fail-closed」（§5.3 **N22** / `tasks.md` 2.9 ⑬）；
    ② D4 的「源目录不存在 ⇒ 整体搬走了」这条**推论为假**（也可能是被**删除**）⇒ 已订正措辞并把由此产生的
    红→绿**登记为有意的行为变化** + fail-closed 对照用例（`tasks.md` 2.11b / §5.1 2c）。
  - **R6**：待跑（针对 R5 两处修复之后的文本）。**收敛判据 = 一轮下来没有新的可证伪项
    且所有「必须修改项」都已落库**；没有轮数上限。
  - **收敛判据 = 一轮下来没有新的可证伪项、且所有「必须修改项」都已落库**；没有轮数上限。
- [ ] 0.5 把第 5 条与第 2 条的**能力边界**（`Ev(A)` 的定义 / 逐字节天花板 / `changes_root` 之外的完全旁路 / 误伤面 /
  模板要放在 `changes_root` 之外）写进 `docs/gate.md §6`，并把「复制式归档 ⇒ 不授予」这条**有意的行为变化**一并登记。

## 1. 规格

- [ ] 1.1 修改 `archive-awareness` 规格：把「归档 move 使该 change 进入集合」改为
  「**归档目录的到达**使该 change 进入集合」，判据写成**五条**（见 `design.md §2 D1`），
  并写死 `SHALL NOT` 依据逐文件改名分 / `R100` / `-M -C` 的副本检测启发式。
- [ ] 1.2 重写否定面 Requirement：保留并**升级**「不得给基准树里已有 entry 的归档目录授予资格」；
  **注明**旧否定面 N2 / N7 被反转的**准确范围**（N7 全反转；N2 只反转「件齐」那一半——
  缺任一必需件的伪造目录仍不授予，因为判据 2 不成立）。
- [ ] 1.3 新增「到达集合的用途共用同一份判定」（归属 / 幽灵 id 排除 / 保护写豁免），
  D4 的排除键 SHALL 同时覆盖 **`R`/`C` 记录的 `old_path`** 与 **`D` 侧记录的 `path`**（R3 的 M4），
  且 D5 的豁免须带**旧侧条件**（`old_path` 落在 active change 目录下）。
- [ ] 1.4 新增「到达方式不改变证据门槛」的对称性不变量，并给「零证据归档 change 照样逐条点名」的防绕过用例。
- [ ] 1.5 新增「内容来源」判据（第 5 条）的正文、**`Ev(A)` 的数据推导定义**、**能力天花板**与 Scenario：
  整份复制 / 复制后改路径 / 加一个字节 / 删一个文件 / 混源 / 搬无关文件洗白 / 嵌套源 /
  **报告挪出 `reviews/`**（R3-A1）/ **`specs` 或 `tasks.md` 换形态**（R3-A3）/ **每个文件各加一字节**（R3-A2，已知天花板）。
- [ ] 1.6 新增「组织型子目录不是到达的 change」的两个 Scenario（`archive/2026/…` 与「只含 `reviews/` 子目录」）。
- [ ] 1.7 归档时按 OpenSpec 流程把本 delta 并入 `openspec/specs/archive-awareness/spec.md`
  （⚠️ 本仓**从未归档过任何 change**，该目录尚不存在 ⇒ 由 archive 步骤创建），并按本仓政策追加解释事件（受保护路径）。

## 2. 测试（先行，先写后实现）

- [ ] 2.1 **到达判定的纯函数用例**（注入式**树读取器**，不碰真 git）：
  路径在基准树里没有 entry ⇒ 候选；有 entry（tree **或 blob**）⇒ 不到达；
  head 里不是 tree / **缺任一必需件** ⇒ 不到达；树读不出来 ⇒ fail-closed。
- [ ] 2.2 **出生即归档**：base 无此 change、head 有 `archive/<name>/`（全 `A`、件齐）+ 改 `require_change_for` 路径 ⇒ 退出码 0。
- [ ] 2.3 **move 内带内容改动**：全 `R<100`（含重建过的 manifest）⇒ 退出码 0，且**无**幽灵 active id。
- [ ] 2.3b **move + 被搬文件被整体重写**（R3 的 A4）：`git mv changes/z archive/2026-10-15-z` 并把 `tasks.md` 整体重写
  （git 报 `D`+`A`、不配对）⇒ 退出码 0，且**无**幽灵 active id（依赖 D4 的 `D` 侧排除键）。
- [ ] 2.4 **纯 move 回归**：全 `R100` 的行为逐条与改动前一致（今天绿 ⇒ 修后绿）。
- [ ] 2.5 **对称性不变量**：同一份 change 内容，active 与 archive 两种位置判绿判红结论相同。
- [ ] 2.6 **否定面**（`design.md §5.3` N1–N21 逐条）：尤其
  N3（触碰**已有 entry** 的归档目录）、N4（单文件移入既有归档目录）、
  N6（到达但零证据 ⇒ 逐条点名三份 stage manifest）、N7（缺必需件 ⇒ **不是到达** ⇒ 报「没有任何 change 目录」）、
  N9–N15（第 5 条的七种搬运形态）、N16/N17（组织型子目录两种）、N18（base 同路径是 blob）、
  **N19（报告挪出 `reviews/`）/ N20（`specs`、`tasks.md` 换形态）**。
  ⚠️ **N21（每个证据文件各加一个字节）按「已知天花板」钉——不要求它红**（见 2.9 ⑩）。
- [ ] 2.6b **改写既有测试**（逐条点名；⚠️ 前两条是**语义反转**，不是「修一下断言」）：
  1. `tests/test_archive_awareness.py:274` `test_rebuilding_a_moved_manifest_in_the_same_diff_is_rejected`
     —— 断言「move + 重写被 move 的 manifest（`R<100`）⇒ 红 + 幽灵 active id」，**这正是本 change 要修好的形态 ii**
     ⇒ 反转为「退出码 0、无幽灵 id」，并改名（如 `..._is_accepted`）。
  2. `:494` `test_the_summary_counts_directories_not_deduped_ids_on_a_tie` —— 其构造里 `archive/x/`
     **只有** `notes.md`（缺必需件）⇒ 判据 2 下它不是 target ⇒ 报 1 而非 2。
     ⚠️ **配方订正（R3 的 B1）**：初稿配方（「整个 `changes/x` move 到 `archive/x` + 新建一个件齐的 `changes/x`」）
     **不成立**（新 active change 占同路径 ⇒ git 报 `M` ⇒ 配不成改名 ⇒ 判据 5 命中 3 份）。
     **改用**：`archive/x` 走**出生即归档**（要件与证据全新）+ 在 base 已有且 head 仍存在的 `changes/x` 上做一次 `M`。
  3. `:600` `test_N6_partial_move_into_an_existing_archive_dir_grants_nothing` ——
     ⚠️ **从「不要误改」移入本清单（R3 的 B2）**：新口径下 `another-change` 仍是 active target ⇒
     `:621` 的 `"没有任何 change 目录" in err` 失守 ⇒ 断言改成「`another-change` 仍被按 **active** 契约校验」
     （= `spec.md` 回归护栏段明写的「源 change 不得静默逃检」）。
  4. `:109` `test_grant_requires_the_target_name_to_recognize_the_source_id` —— 直调 `contract.archive_grant`，
     而 `archive_grant` 在本 change 里失去全部调用点（见 3.7）⇒ 随实现删除 / 改写为新纯函数的用例
     （保留「`R<100` 也授予」这条断言——判据换了，语义不变）。
  5. `:49` 的 `_targets()` 助手与 A 节纯函数用例（`:87` / `:101` / `:134` / `:471`）——
     `change_targets` / `changed_change_ids` **签名变了**（要注入树读取器）⇒ 助手改为注入**假树**，按新接口改写（语义不变）。
     ⚠️ `:471` 的构造里有一个**名不认得的源** `unrelated` ⇒ 判据 4（「每一个源都须被认得」）下该到达**整体被拒**
     ⇒ 改成「只留两个认得的源」（保住「别名取并集、与顺序无关」的原意），**另加**一条「名不认得的源 ⇒ 整个到达不授予」。
  ⚠️ **对照（不要误改）**：
  - `test_N2_a_forged_archive_grants_nothing`（`:541`）—— 假目录**缺 `reviews/`** ⇒ 判据 2（须含**全部**必需件）下**不是** target
    ⇒ `"没有任何 change 目录" in err` **仍成立** ⇒ **保持原样**（R1 的 M6 曾要求改写它；判据 2 收紧后不必要了；R3 复核成立）。
  - `test_N4`（`:577`）断言的 `"没有任何 change 目录"` 在 D1 下**仍成立**（R3 复核成立）。
  - `test_deeper_events_file_is_not_read`（`:378`）仍绿（`archive/notes/` 缺必需件 ⇒ 不是 target）——
    **注释要更新**（R3 的 M7：这条尚未改，实现期别漏）。
- [ ] 2.6c **基准 revision 用例**：base 分支在分叉点后前进过（`base` ref 树与 `merge-base` 树不同）⇒
  到达判定与 diff 成员口径一致（判据 1）。
- [ ] 2.7 **接入方真实形状的集成用例**：用接入方 PR 的那两份 diff（33 文件全 `A` / 16 文件含 `R<100>`）各一条，断言修前红、修后绿。
- [ ] 2.8 **fail-closed 用例**：树读不出来 ⇒ 报 finding、不授予、退出码非 0。
- [ ] 2.9 **内容来源用例（第 5 条）——把 R1 的 F1、R2 的 A1/A2/A3、R3 的 A1/A2/A3 全部转成用例**：
  ① 纯 `cp -r`（源原封不动）；② 复制 + 改某证据文件的**路径**（改后缀 / 改名）；
  ③ 复制 + 只改**一处**（给某一个证据文件加一个字节 / 删一个文件）并重跑 `manifest build`；
  ④ **混源**（报告取自 `a`、`tasks/specs` 取自 `b`）；⑤ **R2-A1**（`git mv` 一个非证据文件进 A + 其余整份 `cp`）；
  ⑥ **R2-A3**（源是嵌套归档 `archive/2026/10-15-old/`）；⑦ **R3-A1**（三份报告**挪出 `reviews/`** 放 change 目录根 +
  手写 manifest 用 `report_path` 指过去）；⑧ **R3-A3**（`specs` 换成同名普通文件 / `tasks.md` 做成目录，借用内容塞进去）
  —— 全部断言**不授予** ⇒ `require_change_for` 命中 ⇒ 红。
  ⑨ **防误伤对照（必须绿）**：同构造下**真的 `git mv`**（源目录在 head 里消失）⇒ 绿。
  ⑩ **能力天花板（R3-A2）**：给 `Ev(A)` 里**每一个**文件各加一个字节 + 官方 `manifest build` ⇒
  **按现稿不红** ⇒ 用例**钉住这一已知行为**（并在测试里写明「这是 §8 Q4 的文档化天花板；
  若用户裁『不接受』，本用例改判红」）。**不要**把这条写成「必须红」。
  ⑪ **误伤对照（必须绿）**：新 change 的 `proposal.md` / `design.md` 与 base 里某 change **逐字节相同**（共用 stub）⇒ 绿。
  ⑫ **明写的误伤面（预期红，文档里已登记）**：原样复制兄弟 change 的 `specs/**` 文件 ⇒ 红，finding **只点名该文件**。
  ⑬ **符号链接搬运（R5 的 M1）**：把 `tasks.md` / `specs` / 报告做成**指向基准树里现成 change 的符号链接** ⇒ 红
  （`Ev(A)` 要求普通文件；mode `120000` / `160000` ⇒ fail-closed）。
- [ ] 2.10 **组织型子目录用例（两种）**：`archive/2026/10-15-foo/…` ⇒ `archive/2026/` 不是 target；
  **B1 变体**：`archive/notes/` 只含 `sub/` 与一个 `reviews/` 子目录 ⇒ 也不是 target、不产生「缺少必需件」假阴性。
  并钉住 `archive/notes/sub/workflow-events.jsonl`（`:378`）的行为与今天一致。
- [ ] 2.11b **D4 的行为变化用例（R5 的 M2）**：① 「删除 `changes/x/` 其余文件 + 只把 `notes.md` 搬进**件齐的**
  新到达目录 `archive/<date>-x/`」⇒ 退出码 **0**（钉住这条**有意的行为变化**，并在测试里写明「改动前红」）；
  ② 同上但到达目录**件不齐** ⇒ 退出码**非 0**（fail-closed 对照）。
- [ ] 2.11 **D4 收窄用例**：到达目录 + 同 diff 里把**另一个仍在 head 的** active change 的文件搬进它 ⇒
  那个 change 仍按 active 校验（不得静默消失）；**并且**（R3 附注 ③）`D` 记录的 `path` 落在**仍在 head** 的源目录下时
  **不得**被排除。
- [ ] 2.12 **D5 旧侧条件用例**：把受保护文件（`git mv openspec/specs/x.md …`）搬进到达目录 ⇒ **仍要**解释事件。
- [ ] 2.13 **空文件豁免用例**：到达目录里放一个**空**文件（且 base 里也有空文件）⇒ **不**因此被拒。
- [ ] 2.14 **`Ev(A)` 定义用例（R3 附注 ①）**：手写一份 manifest 把 `report_path` 指向 change 目录内的**任意**路径
  （含 `reviews/` 之外、含指向另一份**没被绑定**的文件）⇒ 指向的那个文件 SHALL 进 `Ev(A)`；
  「报告正文与 `report_path` 目标分离」（绑定 A 却把借来的正文放 B）这条组合 SHALL 复算。

## 3. 实现

- [ ] 3.1 `src/witnessloop/gitutil.py`：新增树查询帮助函数（`tree_entry` / `tree_entries`），
  **精确命令语义见 `design.md §2 D7` 的表**（不带尾斜杠 = 路径自身；带尾斜杠 = 直接子项；`-r` = 其下全部 blob），
  `fail-closed`：读不出 ⇒ 抛错 / 返回失败，调用处报 finding。
- [ ] 3.2 `src/witnessloop/contract.py`：新增到达判定（树读取作为**注入谓词**，判定本体为纯函数），
  实现 D1 五条判据：判据 1（基准树无 entry）、判据 2（head 是 tree 且含**全部**必需件，语义与 `validate_change_dir` 一致）、
  判据 3（记录层）、判据 4（**每一个**源都须被名字认得）、
  判据 5（**到达组** = `new_path` 落在该目录下的记录集合；`Ev(A)` **按数据推导**：`HASHED_ARTIFACTS` 的 artifact 路径整体 + 每份 manifest 的
  `resolve_report_path(report_path)` 目标 + `reviews/**`；**逐文件**判「新 blob or 本次改名落点」；**空文件豁免**）。
- [ ] 3.3 `src/witnessloop/contract.py`：改 `changed_change_ids` 的 `archived_sources` 为
  「**`R`/`C` 记录的 `old_path` + `D` 侧记录的 `path`**，只要落在某个到达组的源 change 目录下、
  且该目录在 head 树里已不存在」（D4 收窄 + R3 的 M4）。
- [ ] 3.4 `src/witnessloop/contract.py`：改 `change_targets` 用到达集合产出归档 target。
- [ ] 3.5 `src/witnessloop/checkcmd.py`：`_check_protected_writes` 的保护写豁免改用**到达集合 + 旧侧条件**
  （`old_path` 须落在 active change 目录下）；保留「对已存在归档目录的修改 / 删除仍要事件」；
  构造并传入真 git 版的树读取器。
- [ ] 3.6 `src/witnessloop/manifestcmd.py`：**本 change 不改它**（grill M4 实测它**不调用** `change_targets`，
  按磁盘存在性解析 `resolve_change_dir`，`manifestcmd.py:33-48`）。
  实现时若确认 `manifest build` 无需感知「到达」，在此写明理由；若需要，**另列**要共享的函数。
  ⚠️ 初稿的「与 `check` 共用同一份 target 解析（单一实现）」是**事实错误**，已订正（R1 的 M-DOC1）。
- [ ] 3.7 核对：`is_archive_move` / `archive_grant` 若失去全部调用点则删除；若仍被别处使用则逐点确认语义未被削弱。
- [ ] 3.8 **性能核对**：第 5 条只加 **1 次** `ls-tree -r <merge-base> -- <changes_root>`（全量一次）
  + 每个到达候选 2 次（`-r <head> -- <archive>/<name>/` 与 `ls-tree <merge-base> -- <archive>/<name>`）
  + 每个源 id 1 次；大仓（接入方 120 个归档目录）实测调用耗时，写进 PR 描述。
- [ ] 3.9 `src/witnessloop/checkcmd.py`：`_require_change` 的**近失文案**（R3 的 E-2）——当 `archive/` 下存在
  **缺必需件**的目录时，在报错里**列出它并点名缺的那一件**（否则「没有任何 change 目录」对已经建了归档目录的接入方是误导）。

## 4. 验证

- [ ] 4.1 `uv run pytest -q`（新增用例 + 全量回归）。
- [ ] 4.2 用**接入方真实提交**复算 `proposal.md` 的表（三份 diff × 两个 ref），把原始输出要点记进 `reviews/` 或 PR 描述。
- [ ] 4.3 本仓 `witnessloop check` 对**本 change 自己**判绿（自举）。
- [ ] 4.4 逐条复算 `design.md §5.3` 的否定面（N1–N21），确认**照样红**（N21 除外——按天花板钉「已知不红」）。
- [ ] 4.5 **用真 CLI 复跑 R1/R2/R3 的端到端构造**（三轮的 e2e 里「到达判定那一半」都是模拟器，只有证据门是真 CLI）：
  实现后必须用**到达的归档目录**重跑 R1-F1、R2-A1、R2-A2（改路径 / 改一处）、R2-A3、**R3-A1（报告挪出 `reviews/`）**、
  **R3-A3（换路径形态）**，确认 `check` **红**；并用**合法 move**复跑同构造确认**绿**。
- [ ] 4.6 **误伤面实测**：在一个含 ≥100 个归档目录的仓里跑一次真实的「出生即归档」，确认没有因逐字节撞车被拒；
  若有，记录是哪个文件撞了（这正是 §8 Q4 的证据）。同时复算 R3 的 `m2`（仓内模板骨架）形态。

## 5. 实现后独立审阅闭环

- [ ] 5.1 跑独立审阅闭环，产出 `reviews/building-review.md`（CHANGES_REQUESTED 则修复并加回归测试，再审，直到收敛）。
- [ ] 5.2 收敛后清理中间轮产物，或把最终版落到规范名（避免孤儿报告）。

## 6. 文档

- [ ] 6.1 `docs/gate.md`：§5.1.1 / §4 / §3.2 / §6 按新判据同步；删掉「R100 要求」的表述，补：
  树不可读 ⇒ fail-closed；**搬运现成证据 ⇒ 不授予**；`Ev(A)` 的定义；**逐字节能力天花板**；
  **`changes_root` 之外副本是完全旁路**；误伤面（含模板要放在 `changes_root` 之外）；
  「复制式归档 ⇒ 不授予」这条有意的行为变化；报告可放在 `reviews/` 之外这条**既有**宽松面。
- [ ] 6.2 `README.md`：接入指引的归档时序一段按新判据改写（**不**把出生即归档写成推荐流程）。
- [ ] 6.3 检查文档影响面：`docs/` 全量与本次判据相关的段落（关键词：`R100`、`归档 move`、`is_archive_move`、`archive_grant`）。

## 7. 收尾

- [ ] 7.1 确认三份 stage manifest 在**所有内容提交之后**重建，且 `reviews/` 处于「每份 `.md` 都被绑定」的一致状态。
- [ ] 7.2 归档 move **仍建议**放最后、独立提交（回归面用它钉「纯 move 逐条不变」）；
  但**不再强制**——形态 ii（move 内带内容改动）本次已是**被支持**的形态，若采用它，须同时验证 2.3 与 2.3b 两条用例。
- [ ] 7.3 从 backlog / 相关跟踪处移除本 change 条目，并追加解释事件。
- [ ] 7.4 回链 issue #26：补完成说明 comment 并关闭。
