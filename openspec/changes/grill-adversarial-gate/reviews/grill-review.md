# Grill: grill-adversarial-gate 设计追问

> 零记忆独立审阅者产出。算法与格式依据 `templates/grill.md`（7 维追问 + 设计树求完备 + 第 4 步决策记录）。
> 立场：**挑战而非确认**。原稿的实测数字与事实断言逐条独立复现（在 `/tmp` 副本里，未在被审仓做实验）。
> 复现结果：**churn 表四次数字全部逐字命中**；**6 条事实断言被证伪或需订正**（见文末）。

## Reviewer
- run id: `grill-reviewer-grill-adversarial-gate-2026-10-12T141224Z`
- 时间: 2026-10-12T14:12:24Z
- 方法：全量 pytest 四组对照（基线 / 甲 / 乙 × helpers 改与不改）+ 机制探针 + 全链路自伤模拟；只读源码与 asterwynd 先例。

## Confirmed Decisions

- **决策**：D1 证据形态走 `stage=grill-adversarial` 的 manifest，**不**复刻 asterwynd 的裸文件形态；理由：实测——change 目录里只放 `reviews/grill-adversarial.md` 而不给 manifest，`check` 退 **1** 并报 `孤儿报告：reviews/grill-adversarial.md 未被任何 manifest 绑定`，即「裸文件在本仓连绿都拿不到」是**机制事实**而非推测；来源: `grill-reviewer-grill-adversarial-gate-2026-10-12T141224Z`
- **决策**：D2 的 churn 表**四次实测全部复现**（基线 **420 passed**；甲 30 failed/390 passed → 17/403；乙 6/414 → 4/416），补丁形态与 `design.md:75-76` 描述一致（change 循环里加一条只换 `stage` 的同形判定）；理由：`/tmp/gag-jia-a|b`、`/tmp/gag-yi-a|b` 四份副本各跑一次全量 `uv run pytest -q`；来源: `grill-reviewer-grill-adversarial-gate-2026-10-12T141224Z`
- **决策**：D6「revision 绑定那一半**已经在**」成立，本 change 只补「必须存在」；理由：实测——三份证据齐备时 `check` 退 0，此后只改 `design.md` 一行内容，`check` 退 **1** 并给出 3 条「审阅的是旧 revision」，即「对抗轮之后再改 design ⇒ 必须重跑」无需新写代码；来源: `grill-reviewer-grill-adversarial-gate-2026-10-12T141224Z`
- **决策**：D4 接受「本地守卫不要求对抗轮证据」这个缺口（只改 `check`）；理由：`guard` 的 matcher 只覆盖 `Write|Edit`，agent 用 Bash 写文件即可绕过（`src/witnessloop/guardcmd.py:16-17` 自述「**防遗忘**，不是防对抗」）⇒ 补上这条**不会消除缺口**，只会在写码前多加一条可绕过、且与「停轮确认 → 才写码」时序纠缠的硬条件；来源: `grill-reviewer-grill-adversarial-gate-2026-10-12T141224Z`
- **决策**：R1（0 条自伤）与 R6（无自锁）成立；理由：5 个 active change 的 `grill-adversarial.manifest.json` **5/5** 存在且 `stage` 字段与 `report_path` 均可解析（实测逐个读取）；且全链路模拟——在副本里打乙补丁（触及 `src/**`）+ 提交实现 + 三份报告与三份 manifest 单独作证据提交 + `check`，**退 0**；来源: `grill-reviewer-grill-adversarial-gate-2026-10-12T141224Z`

## Code-Resolved Questions

- `grep -rn "grill-adversarial" src/` 是不是 0 命中？ → **是**（实测 exit=1、零输出）。证据：`src/**`
- `design.md §1.1` 那张表的行号对不对？ → **全对**：grill 判定 `src/witnessloop/checkcmd.py:83-88`、building 判定 `:91-98`、`_require_change` `:125-145`、`_protected_writes` `:148-206`、孤儿规则 `src/witnessloop/contract.py:185-219`、共用助手 `src/witnessloop/evidence.py:172-235`、grill 薄封装 `:238-257`
- asterwynd 的 `grill-adversarial` 有没有**第二个**检查点？ → **没有**。`scripts/` 下它只出现在 `check_openspec_artifacts.py:1629-1639`，全部落在 `_check_archived_completion_gate`（`def` 在 `:1565`），而该函数只在 `:1685` 对 `archive/<dir>` 被调用。证据：`/home/happy/my-agent/scripts/check_openspec_artifacts.py:1565,1629-1639,1685`
- asterwynd 的触发条件与豁免？ → `change_type.primary != "docs"` ∧ `(change_type.all_types & DESIGN_TYPES)` ∧ `_changed_capabilities(change_dir)` ∧ 文件不存在；`DESIGN_TYPES = {"feature","refactor","process"}`（`:32`）、`_changed_capabilities`（`:690-700`）、「存在性即可」注释（`:1630`）。与 `design.md:36-38` 一致。证据：同上
- asterwynd 守卫侧？ → `grep -c adversarial scripts/workflow_guard.py` = **0**（文件存在、零命中）。证据：`/home/happy/my-agent/scripts/workflow_guard.py`
- **R4**：`design.md` 的内容有没有被任何 manifest 哈希绑定？ → **没有**。`HASHED_ARTIFACTS` 只有 `("tasks_hash","tasks.md")` 与 `("spec_hash","specs")`（`src/witnessloop/constants.py:64-67`）。实测：在**证据提交之前**把 `design.md` 整段换掉再落证据 ⇒ `check` 退 **0**；同样的手法改 `specs/` ⇒ 报 `spec_hash 不匹配`。证据：`src/witnessloop/constants.py:64-67`、`src/witnessloop/contract.py:381-393`
- **D6**：`design.md` 在不在 `stale_exempt_paths`？ → **不在**（豁免只有 `.witnessloop/**`、`<changes_root>*/reviews/**`、事件文件、`archive/**`）。证据：`src/witnessloop/policy.py:68-83`
- **§6 D1**：未被 manifest 绑定的 `reviews/grill-adversarial.md` 会不会先被孤儿规则判红？ → **会**（实测退 1，文案点名 `grill-adversarial.md`）。证据：`src/witnessloop/contract.py:185-219`
- **Q2 的「多轮格式不一致」到底多大？** → 5 份 `grill-adversarial.md`、共 **16 轮**：轮头两种形态（`# 第 N 轮（RN）` 3 份 / `## 第 N 轮对抗验证` 2 份），且**第 1 轮 5 份都没有轮头**；裁定载体两种（`## Verdict` 小节 3 份 / `- 裁定:` bullet 2 份）；裁定文本三种写法（裸词、`**加粗**`、`**加粗** —— 长句`）。5 份的最终轮都是 `PASS`，但**每一份**都含中间轮 `CHANGES_REQUESTED`。⇒「最终裁定 = PASS」需要先定义**轮序**再定义**载体**，两者都没有统一形态。证据：`openspec/changes/*/reviews/grill-adversarial.md`
- **tasks.md B3 的清单与实测一致吗？** → **不一致**，三处（见「原稿被证伪的事实」1–3）。
- **spec.md 与 design 的 D1..D8 对得上吗？** → 大体对得上（D1↔§45-56、D2↔§7-18、D3↔§86-97、D4↔§72-84、D5 部分、D6↔§40-43、D8 部分）。**两处缺口**：① 缺「**多 change 同 PR**」Scenario——`design.md:122-125`（D5）把它列为**刻意的行为**，`changes/building-review-gate/specs/building-evidence/spec.md:29` 有对应的 Scenario，本 spec 没有；② `specs/adversarial-evidence/spec.md:30-33` 的「未触发时不误伤」Given 写成「本次 diff **不满足**触发条件」——在 Q1 定案前是**循环定义**，定案后应替换成具体条件（乙=只改文档 / 只动 change 目录）。
- **`templates/grill.md:197-202` 的硬约束 #2 被本门禁强制了吗？** → **没有**。`contract._check_git_span`（`src/witnessloop/contract.py:272-354`）只判「manifest 的 `head_sha` 之后没有非证据改动」，两份 manifest 的**相对先后**没有任何判据 ⇒ 门禁保证的是「存在一份绑定在最终 revision 的对抗证据」，不是「对抗轮发生在写码之前」。`design.md:165-169`（R4）已声明这一点，但文案层面容易被读成「写码前必须收敛」。

## Open Questions

- **Q1 触发条件选甲还是乙？**
  - 甲的**真实**额外代价（原稿没写全）：它不只是多改 13 条用例——它会让 `tests/test_building_gate.py::test_not_required_when_only_the_change_dir_changed`（钉的正是「提案期 / 纯 change 目录改动**不误伤**」）变红，选甲必须**重写**这条语义钉子，而不是「只补证据」。
  - 乙的绕过面（实测结论）：**不存在**「先提纯 change 的 PR、后续再改代码」的永逸绕过——后续那个改代码的 PR 自己的 diff 就触及 `require_change_for`，届时仍要 `stage=grill-adversarial`。
  - 与 `templates/grill.md:197-202` 四项硬约束的对应：甲/乙**都只覆盖第 4 项**（`Confirmed Decisions` ≥3 带 `来源:`，且那是 grill 报告的判据）；第 1 项（frontier 空）无判据；第 2 项（对抗已 PASS）两条都不强制（见上一节）；第 3 项（Open Questions 已被用户确认）由 **grill** 那条的正文校验兜住（`evidence.grill_evidence_findings`）。⇒ 甲/乙的差别只在**触发面**，不在**时序强制**。
  - ➡️ **推荐答案**：**乙**（与 building 同一条 `code_hits` 判定）。这是本仓能表达的、最接近 asterwynd 三重豁免的客观判据；且把新概念的数量压到 1 个。
  - **具体例子**：同一个「只新增 `openspec/changes/foo/proposal.md`、一行 `src/` 都没动」的 PR——今天已经红（`validate_review_manifests` 要求 ≥1 份 manifest）；**选甲** ⇒ 此后它**还要**有 `stage=grill-adversarial` 才绿（设计还没写完就被要求跑对抗轮）；**选乙** ⇒ 它只要补齐 grill 证据即可。反过来，「改了 `src/witnessloop/checkcmd.py` + 顺带一个 change 目录」的 PR，甲与乙**都会**要 `stage=grill-adversarial`——差别只是 churn（实测 17 vs 4 条既有用例）。
- **Q2 verdict 文本是否机械判 `PASS`？**
  - 真实成本（实测，比原稿的估计更重）：5 份历史报告共 **16 轮**，轮头两种层级 + 第 1 轮全部无轮头 + 裁定载体两种 + 裁定文本三种；且每份都含中间轮 `CHANGES_REQUESTED`。
  - **回填的隐藏代价**（原稿没写）：改**别的** change 的历史报告会让那份 manifest 的 `report_hash` 不匹配。实测：改动 `old-change/reviews/grill-adversarial-review.md` 之后，任何**触及该 change 目录**的 PR 都会红 `report_hash 不匹配：报告 … 的字节与 manifest 记录不符`。⇒「回填 5 份」不是免费文案，而是给 5 个既有 change 各埋一颗地雷（在它们下次被触及前必须拆掉）。
  - ➡️ **推荐答案**：**甲（不解析 verdict）**。与 #13 已裁定的 building 口径一致；且回填代价高于原稿估计。
  - **具体例子**：`guard-crash-exit` 的对抗报告 R1–R4 全是 `CHANGES_REQUESTED`、R5 才是 `PASS`（`openspec/changes/guard-crash-exit/reviews/grill-adversarial.md:11,178,347,495,605`，`PASS` 在 `:607`）。选乙 ⇒ 该 change 在 R5 之前的任何 revision 上都红；而 `templates/grill.md:131` 的「到顶交人判断」若没有一条出路（如 `reviews/<stage>-override.md`），就等于被无声取消。
- **Q3 是否接受「本地守卫不要求对抗轮证据」这个缺口？**（D4）
  - ➡️ **推荐答案**：**接受**（只改 `check`）。我补一条比 D4 更硬的理由：`guard` 只覆盖 `Write|Edit`，Bash 写文件即可绕过 ⇒ 补上这条**不会**消除缺口，只加一条可绕过却与「停轮确认 → 才写码」时序纠缠的硬条件；真正的锚是 CI required check。
  - **具体例子**：`grill-adversarial.manifest.json` 还没建时写 `src/x.py`——`guard --path src/x.py` 今天**放行**（`guardcmd.py:112-119` 只查 grill），加条件后仍可用 `WITNESSLOOP_SKIP_GUARD=1` 或一次 `echo > src/x.py` 放行；而 CI 的 `check` 两条路径都拦。
- **Q4 对既有接入方的行为变更怎么落？**（照 #13 Q3 口径）
  - ➡️ **推荐答案**：**只写文档**（README + `docs/gate.md`）+ 明确声明「对**接入方**是行为变更」，**不加过渡开关**（开关 = 静默绕过面，正是 D5 拒绝的那类东西）。
  - **具体例子**：已接入的仓升级后，一个「改了 `src/**` 但没有 `stage=grill-adversarial` manifest」的 in-flight PR 由绿变红；若加 `policy.evidence.require_grill_adversarial=false` 开关，该 PR 保持绿而门禁静默失效。
- **Q5（本审阅新增）R4 的空洞在**本 change 自己**身上必然发生——要不要在本 change 内处置？**
  - 事实：`templates/grill.md` 要求对抗轮在**停轮之前**跑完，而本 change 的 `spec.md`/`design.md` 要**停轮拿到 Q1..Q4 之后**才定稿（`tasks.md:57-59` 的 E0：把定案替换进 `spec.md`）。⇒ 本 change 的 `grill-adversarial.md` 必然是对**未定稿**设计的证伪，manifest 却在定稿后重跑 ⇒ 门禁「绿」，而报告针对的是一份被取代的稿子。这不是假设，是**必然**。
  - ➡️ **推荐答案**：**在 E0 与 E1 之间显式加一步**——「Q1..Q4 定案、`spec.md`/`design.md` 改完后，**重跑一次设计对抗轮**（可只针对被定案改动的部分），再落 `stage=grill-adversarial` 证据」；**不**在本 change 内新增 `design_hash`（那要改 manifest schema = 另一次 change，且 R4 已声明为已知上限）。
  - **具体例子**：若 Q1 定案为**甲** ⇒ `spec.md` 的触发条件从乙改写为「每个被触及的 change」、`checkcmd.py` 的判定从 `if code_hits:` 块挪到 grill 那条旁边、`tasks.md` B2 的 4 条变 17 条；而对抗轮原稿逐条对抗的正是「乙的四条理由」并实测验过乙的 churn ⇒ 该报告**整节作废**，但 manifest 照样绿。

## 风险

1. **R-new-1（中）——「存在」与「时序」会被混读。** 实测：`_check_git_span`（`src/witnessloop/contract.py:272-354`）只判「manifest 的 `head_sha` 之后无非证据改动」，**两份 manifest 的先后不做比较**。⇒ 建议在 `docs/gate.md §9` 与 README 把两条边界并列写死：①「verdict 不参与判定」；②「本门禁保证证据**存在**并绑定在最终 revision，**不保证**对抗轮发生在写码之前」。
2. **R-new-2（中）——`design.md` 的改动有一段是无声的。** `design.md` 不被任何 hash 绑定，而 `spec.md`/`tasks.md` 被绑定。⇒「对抗轮之后改 design 要重跑」只在改动落在 manifest 的 `head_sha` **之后**才成立；落在**之前**（但对抗轮已跑过）则完全无痕。R4 说对了一半，这一半应当补上。
3. **R-new-3（低，可诊断性）——helpers 补 stage 后的报告文件名与仓库真实约定不同。** `write_review` 默认产 `reviews/grill-adversarial-review.md`，而本仓 5 份真实证据都在 `reviews/grill-adversarial.md`（实测逐个读取）。不影响判定，但会让「孤儿报告」用例更难读；建议 B1 顺手让默认 `report_rel` 对 `grill-adversarial` 用真实约定的名字。
4. **R-new-4（低）——触发面要写准。** 本仓 `.witnessloop/policy.json:8-12` 的 `require_change_for` 含 `templates/**` 与 `plugin/**` ⇒「只改模板」的 PR 也算「落了实现」，乙口径下同样要对抗轮证据。这对本仓是好事（模板就是流程本体），但 README 的触发条件里应写明「落了实现 = 命中 `require_change_for`，**含模板 / 插件目录**」。
5. **R-new-5（低，工程纪律，本次已踩到）——本仓 worktree 的 `.git` 是文件。** `gitdir: /home/happy/witnessloop/.git/worktrees/<id>`，所以 `cp -a` 出的副本会让 `git` 命令**作用回原 worktree**（共用 index/gitdir；`git checkout -b` 与 `git commit` 会改原仓的分支与 HEAD）。本次审阅因此误改了 worktree，已完整复原（见「复核边界」）。建议把这条写进 `design.md` 的实测配方：**在副本里做实验前先 `rm .git && git init`**，否则实测会污染被审仓。
6. **R-new-6（低）——悬空引用。** `design.md:84` 写「实测清单见 tasks B3 的实测记录」，而 `tasks.md:69-71` 的「实测记录（实现期）」是空的（正文「（待填）」）。

## 原稿被证伪的事实

1. **`design.md:83-84` 与 `tasks.md:34` 的「`test_orphan_reports.py` 6 条」不成立，实测 8 个测试项。** 甲口径（helpers 补 `stage` 后）该文件的失败项为：`test_build_then_check_agree_on_noncanonical_report_paths` 的 **4 个参数化项**（`./reviews/…`、`reviews//…`、`reviews/../reviews/…`、`reviews/./…`）+ `test_directory_named_like_a_report_is_not_an_orphan` + `test_extra_non_markdown_files_are_not_orphans` + `test_symlinked_report_is_not_an_orphan` + `test_two_manifests_binding_the_same_report_is_not_an_error` = **8**。原稿的「6」漏算了参数化的两个项。
2. **`tasks.md:35` 把 `tests/test_invariants.py` 列进「选甲要改」的清单不成立。** 在 B1（`commit_evidence` 默认 `stages` 补 `grill-adversarial`）**已做**的前提下，甲口径的 17 条失败里没有 `test_invariants.py`；它只出现在**不补 helpers** 的 30 条里（由 helpers 修复）。B3 是 B1 之后的步骤，故这条是错的。
3. **`tasks.md:34-35` 漏了 `tests/test_building_gate.py::test_not_required_when_only_the_change_dir_changed`。** 实测：甲（helpers 补 stage 后）会让这条变红，乙不会。这条钉的正是「提案期 / 纯 change 目录改动**不误伤**」——甲口径下必须**重写**它，而 `tasks.md:36` 的「不得放松它们原本要钉的东西」在这里直接撞车。
4. **`design.md:84` 指向的「tasks B3 的实测记录」不存在**（`tasks.md:69-71` 为空）。
5. **`design.md:131-132`（D6）「会让两份 manifest 一起 stale」不精确，实测是 3 条。** 当 change 同时有 `grill`/`grill-adversarial`/`building` 三份 manifest 时，改 `design.md` 后 `check` 退 1 并给出 **3 条**「审阅的是旧 revision」（每份 manifest 一条）。
6. **（量级订正，非推翻）`design.md:104-106`（D3）的「三种记法并存」属实且更糟**：实测 5 份报告 16 轮，轮头两种层级、第 1 轮 5 份全无轮头、裁定载体两种、裁定文本三种；5 份最终轮都是 `PASS`，但**每份**都含中间轮 `CHANGES_REQUESTED`。

## 复核边界（我这轮怎么做的）

- 全部实测都在 `/tmp` 副本里：`/tmp/gag-probe`（基线 420 passed）、`/tmp/gag-jia-a|b`、`/tmp/gag-yi-a|b`（四组 churn）、`/tmp/gag-d6`（机制探针：R4 / D6 / D1 / spec 哈希 / 孤儿）、`/tmp/gag-sim`（自伤全链路模拟）。**未在被审仓做任何实验**；本文件是唯一的仓库写入。
- ⚠️ **一次污染与完整复原（须记录）**：本仓 worktree 的 `.git` 是**文件**（`gitdir: /home/happy/witnessloop/.git/worktrees/grill-adversarial-gate`），`cp -a` 出的副本因此**共用原 worktree 的 gitdir 与 index** ⇒ `/tmp/gag-sim` 里的 `git checkout -b sim` 与两次 `git commit`（`1e4e4a8`、`8fb5c6d`）落到了**原 worktree**。已复原：`git checkout -f grill-adversarial-gate/2026-10-12` + `git branch -D sim`。复核结果：`git status --short` 为空、`git diff HEAD --stat` 为空、`design.md`/`proposal.md`/`tasks.md` 字节数 = **16915 / 4417 / 5253**（与开工快照逐字节一致）、`git worktree list` 各 worktree 分支不变、主 worktree `/home/happy/witnessloop` 仍为 clean `main`；两个游离提交已无任何分支引用。
- **实测数字不受污染影响**：pytest 一律在 `tmp_path` 里 `git init` 独立仓（不与本仓 gitdir 相干）；自伤模拟用的是 `git diff <base>..<head>`（与工作树无关），且证据提交内含乙补丁（`src/witnessloop/checkcmd.py` +7 行、含 `grill_adversarial_stage`），触发面成立。但方法论教训已记入 R-new-5。

## User Confirmation

> 停轮：收敛后的 Open Questions 一次性交用户裁定（用户在获得「每条附推荐答案 + 本 change 真实场景例子」后逐条选择）。
> 用户的答复是**唯一**的确认来源；本文件此前写的一切推荐答案都只是推荐。

- **Q1**: 用户答复：**乙**——触发面 =「本次 diff 命中 `policy.require_change_for`（= 落了实现）」时才要求对抗轮证据，与 building 门禁同一条判定；并**明确否掉甲**（甲=每个 change 都要）：拒绝理由与实测数据一并给出（甲 17 条既有用例、且「只动 change 目录」场景只能被空正文报告满足 ⇒ 门形同虚设）；确认时间: 2026-10-12
- **Q2**: 用户答复：**甲**——**不解析** verdict 文本（`PASS` / `CHANGES_REQUESTED` 都合格），与 #13 已裁定的 building 口径一致；接受随之而来的诚实边界（含「报告正文不校验、空文件亦合格」）；确认时间: 2026-10-12
- **Q3**: 用户答复：**接受缺口**——本 change **只改 `check`**，不给本地 `guard` 增加对抗轮条件（守卫可绕过、且与「停轮确认 → 才写码」时序纠缠）；该缺口在 spec 的边界声明里显式写出；确认时间: 2026-10-12
- **Q4**: 用户答复：**只写文档**——对既有接入方的行为变更靠 `README.md` + `docs/gate.md` 声明，**不加**过渡开关（开关=静默绕过面）；确认时间: 2026-10-12
- **Q5**: 用户答复：**采纳 E0b**——定案（Q1..Q5 落进 spec/design/tasks）之后**重跑一轮设计对抗**（同一路径覆盖 + 重建 manifest；若给 `CHANGES_REQUESTED` 则重跑到 PASS 或 3 轮封顶），使对抗证据针对**定稿后**的设计；确认时间: 2026-10-12
