# 设计阶段对抗验证: grill-adversarial-gate（第 1 轮 R1）

- run id: `adversarial-reviewer-grill-adversarial-gate-r1-2026-10-12T143037Z`
- 时间: 2026-10-12T14:30:37Z
- 立场: 默认上游结论有错，逐条证伪
- 方法: 在 `/tmp/gx/**` 的独立副本里做（每个副本先 `rm -rf .git && git init`，且各自 `uv sync` 重建 venv）；被审 worktree 全程只读，唯一的仓内写入是本文件。基线 `uv run pytest -q` = **420 passed**（独立复现）。四组 churn 对照全部实跑；机制探针用仓自己的 `conftest`/`helpers` 夹具在 `tmp_path` 真仓里跑。

## Verdict

**CHANGES_REQUESTED**

阻塞项 2 条（都在作者本次回写 `ef31a2a` 的**下游落地**，不在上游 grill 的结论本身）：

- **B-1**（`tasks.md:33-43`，仅 Q1 定案为**甲**时激活）B3 把「甲口径下要改的用例」写成「**再改 13 条**」，但**只枚举了 9 条**，且 B2 那 4 条在甲口径下**不是**甲乙共同的那 4 条（真正的交集是 `test_acceptance.py` 2 条 + `test_manifest_build.py` 1 条 + `test_orphan_reports` 的 4 个参数化项）。已实测出**完整且正确**的 13 条清单（下文「新发现 N-1」），照 B3 字面施工会漏改。
- **B-2**（`tasks.md:72-77`）E0b「重跑一次对抗轮」**没有规定第二份报告的落盘方式**，而两条路只有一条通：**必须覆盖同一路径**（实测：`reviews/grill-adversarial.md` 原地重写 + rebuild manifest ⇒ `check` 退 0；另起文件名 ⇒ 退 1 报**孤儿报告**）。这条不定死，实现期的 E0b 会直接撞上 D1 引以为据的那条孤儿规则。

其余全部为**非阻塞**（观察 / 文案 / 可诊断性），见「非阻塞观察」（共 9 条）。

---

## 逐条对抗（针对上游 Confirmed Decisions / 证伪清单 / 风险 / Open Questions）

### A. 上游 5 条 Confirmed Decisions

- **上游结论「D1 证据形态走 manifest，不复刻 asterwynd 裸文件——裸文件在本仓连绿都拿不到，`check` 退 1 并报孤儿」→ 我的复现：成立。** 实测（`grill`+`building` 证据齐备、另放一个没被绑定的 `reviews/grill-adversarial.md`）：`check` 退 **1**，且唯一的 finding 正是 `openspec/changes/add-x/reviews/grill-adversarial.md：孤儿报告：reviews/grill-adversarial.md 未被任何 manifest 绑定`。**机制事实无误**。（注意：若该 change 连一份 manifest 都没有，先报的是「缺少 review manifest」那条，孤儿规则排在后面——不影响结论。）

- **上游结论「D2 churn 表四次实测全部复现（基线 420；甲 30/390 → 17/403；乙 6/414 → 4/416）」→ 我的复现：四次数字逐字命中。** 独立建四份副本（`/tmp/gx/{jia,yi,jia-h,yi-h}`），补丁 = 在 `checkcmd` 的 change 循环里加一条与 building 同形、只换 `stage` 的判定；helpers 变体 = `commit_evidence` 默认 `stages` 加 `"grill-adversarial"`。输出：`30 failed / 390 passed`、`6 failed / 414 passed`、`17 failed / 403 passed`、`4 failed / 416 passed`；基线 `420 passed`。

- **上游结论「D6『revision 绑定那一半已经在』——三份证据齐备 `check` 退 0，此后只改 `design.md` 一行 ⇒ 退 1 并给 3 条『审阅的是旧 revision』」→ 成立，且我补出了它的**规律**。** 实测三组对照：**1 份** manifest 时 1 条、**2 份**时 2 条、**3 份**时 3 条 ⇒ **stale 条数 ≡ 该 change 目录里 manifest 的份数**（`contract.py:272-354` 的 `_check_git_span` 是逐 manifest 判的）。上游「恒为 3」只在「三份证据」这一前提下成立；`design.md:146`（D6）写「每一份 manifest 各报一条」是准确表述，`design.md:240`（§7）写「实测 3 条」也只在三份证据语境下成立——建议在 D6 那句后补一句「条数 = manifest 份数」，否则读者会把 3 当成常量。

- **上游结论「D4 接受『本地守卫不要求对抗轮证据』这个缺口」→ 成立，且我复现了它赖以成立的正向条件。** 实测 `guardcmd.py:118-127` 只调 `evidence_mod.grill_evidence_findings_in_change(... grill_stage=pol.grill_stage ...)`——**只查 grill 一条**。实测：一个只有 `stage=grill` manifest、**没有** `grill-adversarial` 的 change，`guard --change add-x --path src/app.py` ⇒ **退 0 放行**。⇒ 上游那句「补上这条不会消除缺口」以及 `design.md:130`（D4）「本 change 的 E0/E1 已按『先放行、定稿后重跑』处理，无须再加一层」**都不存在自锁**：放行只依赖 grill 证据。

- **上游结论「R1（0 条自伤）与 R6（无自锁）成立」→ 部分不成立（用词层面）。** 事实面成立：实测 5 个**有** `reviews/` 的 active change **5/5** 都有 `grill-adversarial.manifest.json`（`building-review-gate` / `dogfood-bootstrap` / `events-readpoint-fix` / `grill-evidence-gate` / `guard-crash-exit`），逐个读 JSON 确认 `stage=grill-adversarial` 且 `report_path` 可解析。**但**：本仓 active change 是 **6 个**，第 6 个是 `grill-adversarial-gate` **自己**（就是本 change）。上游写「5 个 active change」是把本 change 排除在计数之外——作为「0 条自伤」的证据这没问题（本 change 自己必然要产这份证据），但**作为本仓现状陈述不准确**；且 6 个里有 1 个（本 change）**今天没有** `grill-adversarial.manifest.json`，所以「本仓所有 active change 都有」这类措辞不能写进 README（`design.md:31-32` 已用「5 个 active change」，安全；`proposal.md:65` 同。无实际错误，仅提示别把 5 升级成「全部」）。

### B. 上游「原稿被证伪的事实」6 条

1. **「`test_orphan_reports.py` 实测 8 个测试项，原稿的 6 漏算 4 个参数化项」→ 成立。** 实测甲（helpers 补 stage 后）该文件的失败项正是 8：`test_build_then_check_agree_on_noncanonical_report_paths` 的 **4 个参数化项**（我在 `tests/test_orphan_reports.py:208-216` 读到参数表确为 `reviews/./…`、`reviews//…`、`reviews/../reviews/…`、`./reviews/…` 四条，参数值是 **`grill-review.md`**）+ `test_directory_named_like_a_report_is_not_an_orphan` + `test_extra_non_markdown_files_are_not_orphans` + `test_symlinked_report_is_not_an_orphan` + `test_two_manifests_binding_the_same_report_is_not_an_error`。**8 = 4 + 4，逐项对上。**

2. **「`tests/test_invariants.py` 不该出现在甲口径的清单里（补 helpers 后它不失败）」→ 成立。** 实测：`test_invariants.py::test_adding_new_evidence_needs_no_event` **出现在**不补 helpers 的 30 条里，**不在**补 helpers 后的 17 条里（`grep -c invariants` = 0）。作者已从 `tasks.md` B3 删除，正确。

3. **「漏了 `test_building_gate.py::test_not_required_when_only_the_change_dir_changed`，甲会让它变红、必须重写」→ 成立，但『必须重写』这个判断我要**削弱**。** 变红属实（实测它在甲的 17 条里、不在乙的 4 条里）。但**它机械上是可以改写成绿的**——只要给这个 fixture 补一份 `stage=grill-adversarial` 的证据（哪怕报告是空文件，见下）。⇒「甲在语义上不可接受」**不成立**；准确的说法是「甲让这条用例不再能表达『提案期不误伤对抗轮门禁』，因为甲的触发面**没有**『不触发』这个分支」。**这是我建议主 session 给用户的措辞**：选甲不是做不到，是这条门在提案期只能靠**空报告**满足——即「门在，但门后什么都没有」。

4. **「`design.md:84` 指向的『tasks B3 的实测记录』不存在」→ 成立且已修。** `design.md:86-87` 现在显式写明「已删——清单不在这两份文件里维护，权威出处是 `reviews/grill-review.md`」。实测 `tasks.md:87-89` 的「实测记录（实现期）」仍为「（待填）」，但那已不是悬空引用（正文不再指向它），仅是实现期待填的正常占位。

5. **「`design.md:131-132`（D6）『会让两份 manifest 一起 stale』不精确，实测是 3 条」→ 成立（3 条），但订正后的写法仍有残留歧义。** 见上文 A 节第 3 条：3 只对 3 份 manifest 成立。`design.md:146` 已改成「每一份 manifest 各报一条……（三份证据时实测 3 条）」，准确；但 `design.md:240`（§7）保留了「**3 条** stale」的裸数字，脱离上下文读会当成常量。非阻塞文案问题。

6. **「（量级订正）D3 的『三种记法并存』属实且更糟：5 份报告 16 轮」→ 我的独立计数：** 逐份数轮头（`^#{1,3}.*第 N 轮`）：`building-review-gate` 2、`dogfood-bootstrap` 1、`events-readpoint-fix` 2、`grill-evidence-gate` 3、`guard-crash-exit` 4 ⇒ **12**（其中 `guard-crash-exit` 正是上游点名的那份，R1–R4）。**补齐每份缺的第 1 轮轮头 = 5 ⇒ 16，逐份命中。** 载体分布也复现：`## Verdict` 小节 3 份 / `- 裁定:` bullet 2 份；5 份都含中间轮 `CHANGES_REQUESTED`。⇒「最终裁定 = PASS」需要先定义轮序再定义载体，两者都无统一形态——**属实**。

### C. 上游 Code-Resolved Questions（我逐条复核）

- **「`grep -rn "grill-adversarial" src/` = 0 命中」→ 成立。**
- **「`§1.1` 表的行号全对」→ 成立，我逐条读源码核对**：`checkcmd.py:83-88`（grill 判定，`sed` 显示该调用正好落在这 6 行）、`checkcmd.py:91-98`（`if code_hits:` 块内的 building 判定）、`checkcmd.py:125-145`（`_require_change`）、`checkcmd.py:148-206`（`_protected_writes`）、`contract.py:185-219`（`_check_orphan_reports`，`def` 在 `:187`）、`evidence.py:172-235`（`stage_manifest_findings_in_change`，`def` 在 `:172`）、`evidence.py:238-257`（`grill_evidence_findings_in_change`，`def` 在 `:238`）。全对。
- **「asterwynd 的 `grill-adversarial` 唯一检查点在归档点」→ 成立。** 复核 `/home/happy/my-agent/scripts/check_openspec_artifacts.py`：`grill-adversarial` 的唯一逻辑出现是 `:1629-1639`，全落在 `_check_archived_completion_gate`（`def` 在 `:1565`）内；该函数唯一调用点 `:1685` 只对 `changes_root/"archive"/dir_name` 跑。`workflow_guard.py` 的 `grep -c adversarial` = **0**。触发条件四条（`primary != "docs"` ∧ `all_types & DESIGN_TYPES` ∧ `_changed_capabilities` ∧ `not exists`）与 `design.md:41-42` 的描述一致；`DESIGN_TYPES = {"feature","refactor","process"}` 确在 `:32`。**补一条上游没说的**：`grill-adversarial` 这个字符串在 my-agent 的**测试、AGENTS.md、docs、以及历史 change 目录**里还有多处出现（`grep -rln` 共 18 个文件），但**代码路径只有那一处**——上游「唯一检查点」的说法在「检查点」这个限定下成立，在「字符串出现次数」下不成立。措辞已足够精确。
- **「R4：`design.md` 的内容没有被任何 manifest 哈希绑定」→ 成立。** `constants.HASHED_ARTIFACTS` 实测只有 `("tasks_hash","tasks.md")` 与 `("spec_hash","specs")`（`constants.py:64-67`）。**在证据提交之前**把 `design.md` 整段替换（新提交）再落三份证据 ⇒ `check` **退 0**（实测）。
- **「改 `specs/` ⇒ 报 `spec_hash` 不匹配」→ 我这次没复现出不匹配。** 用同样手法（证据提交**之前**整段替换 `specs/x/spec.md` 并提交）⇒ `check` **退 0**，**没有** `spec_hash` 报错。原因不是上游错，是**手法时序**：`write_review` 是在写报告的那一刻对**当时**的 `specs` 取哈希，所以「先改 specs、后产证据」两侧天然一致。要复现 `spec_hash 不匹配`，必须「先产证据、后改 specs」。**这是对我自己探针的订正，上游那句结论（同一手法下 specs 会被哈希绑定而 design 不会）方向是对的**，但它举的手法严格说复现不出后半句——建议 `design.md:185-186` 与 `spec.md:117-119` 把这一句的分母写清（「**先产证据、后改** `specs/` ⇒ `spec_hash` 不匹配；同样时序改 `design.md` ⇒ 退 0」），否则照字面复现会得到反例。
- **「`design.md` 不在 `stale_exempt_paths`」→ 成立。** `policy.py:68-83` 的豁免只有 `.witnessloop/**`、`<changes_root>*/reviews/**`、事件文件、`archive/**`。
- **「§6 D1 前置：未被绑定的 `reviews/grill-adversarial.md` 会先被孤儿规则判红」→ 成立**（见 A 节 D1 条的实测输出）。
- **「`templates/grill.md:197-202` 的硬约束 #2 没有被本门禁强制」→ 成立。** 实读 `templates/grill.md:195-202`：硬约束 #2 = 「对抗验证已到 `PASS`（或轮数封顶并交人）」。`contract._check_git_span` 只判「manifest 的 `head_sha` 之后没有非证据改动」，不做两份 manifest 的先后比较。`design.md:189-191`（R4）已声明。

### D. 上游 Open Questions（Q1–Q5）

- **Q1「乙的绕过面不存在永逸绕过」→ 成立，且我能给出比上游更硬的机制理由。** 上游的论证是「后续那个改代码的 PR 自己的 diff 就触及 `require_change_for`」。我补一句：更强的是 **revision 绑定**——`_check_git_span` 要求证据的 `head_sha` 不早于最后一个非证据改动，所以「报告绑在旧 revision 而 spec 后来又改了」会直接判 stale。⇒ 「先提纯 change、后提改码」这条路，在**同一个 PR** 内被 `_check_git_span` 挡住，在**跨 PR** 场景下也只是把对抗轮推迟到前一个 PR 的合入点——但请注意：**跨 PR 拆分的真正后果**是「对抗轮针对的 design 可能已被前一个 PR 合入」，这正是 R4/边界声明 3 已声明的上限，**不是本 change 新增的洞**。结论：**乙的绕过面分析成立。**
- **Q2「回填 5 份历史报告的隐藏代价」→ 成立。** `report_hash` 是逐报告绑定的（`write_review` 用 `sha256_tree(report_file)`），改别的 change 的历史报告确实会让那份 manifest 不匹配。`grill-review.md:45` 与 `design.md:117-119` 的表述一致。
- **Q3「guard 只覆盖 `Write|Edit`、Bash 可绕过」→ 成立且我实测了 `guardcmd.py` 的只查 grill。** 见 A 节 D4 条。`design.md:128` 的「`echo > src/x.py` 或 `WITNESSLOOP_SKIP_GUARD=1`」两条逃生口在 `guardcmd.py:16-17,79-80` 有源码依据。
- **Q4「只写文档、不加过渡开关」→ 无实测可做（无新字段开关），但我验证了**出厂 policy 与老 policy 的回落**（见「新发现 N-4」）：加不加开关这件事本身不引入回落问题。**
- **Q5「在 E0 与 E1 之间显式加一步 E0b」→ 方案**方向正确**，机制上**走得通**，但**欠定**（阻塞项 B-2）。** 详见「新发现 N-2」的完整推演。

### E. 上游风险 R-new-1..6 / 作者新增 R7–R9

- **R-new-1（「存在」与「时序」会被混读）→ 成立。** 文案要求（`docs/gate.md §9` + README 并列写死两条边界）已落到 `design.md:189-191`、`tasks.md:65`（D3）、`spec.md:106-119`（边界声明 3）。**但 `tasks.md:65` 的 D3 只写了三条边界中的两条**（缺「设计内容未被哈希绑定」那条），而 `design.md:155` 要求 §9 写「触发面 + 判据 + **同两条边界**」——两处口径不一致（§9 两条 vs D3 三条）。非阻塞文案。
- **R-new-2（`design.md` 的改动有一段是无声的）→ 成立。** 实测确认：落在 `head_sha` 之前则完全无痕（`check` 退 0）。已写进 `design.md:147-148` 与 `spec.md:117-119`。
- **R-new-3（helpers 默认报告名与真实约定不同）→ 成立，且作者已把它落成任务。** `write_review` 实测默认 `report_rel = f"reviews/{stage}-review.md"`（`tests/helpers.py:132`）⇒ `grill-adversarial` 默认产 `reviews/grill-adversarial-review.md`，而仓里 5 份真实证据都在 `reviews/grill-adversarial.md`。已落 `tasks.md:31-32`（B1 顺手改）+ `tasks.md` D3/D4 的表述。**注意一个副作用**：一旦默认名改成 `reviews/grill-adversarial.md`，B1 的「多跑一次 build 即可」就要重新检查——`commit_evidence` 对 `("grill","grill-adversarial","building")` 三个 stage 各调一次 `write_review`，默认名互不相同（`grill-review.md` / `grill-adversarial.md` / `building-review.md`），**不冲突**；但 `grill-adversarial.md` 这个名字与 `templates/grill.md:187-190` 文档里的示例路径一致，是好事。
- **R-new-4 / R9（`require_change_for` 含 `templates/**` 与 `plugin/**`）→ 成立。** 实测 `.witnessloop/policy.json` 的 `require_change_for` = `["src/**","templates/**","plugin/**"]`（本仓），而 `tests/test_init_policy.py:22-31` 的 `CUSTOM_DOC` 注释也自述「与出厂默认的差异点：`require_change_for` 多出 `templates/**` 与 `plugin/**`（本仓自举所需）」。⇒ 乙口径下「只改模板」也要对抗轮证据，属实。已落 `design.md:207-209`（R9）+ `tasks.md:66`（D4）。
- **R-new-5（worktree 的 `.git` 是文件）→ 成立，本次我按它执行且未污染。** 我开工时 `cat .git` 确为 `gitdir: /home/happy/witnessloop/.git/worktrees/grill-adversarial-gate`；所有副本先 `rm -rf .git && git init -q` 再动。收工核对：`git status --short` 为空、HEAD 仍为 `ef31a2a`、`git worktree list` 只有本 worktree 与主仓。已落 `tasks.md:50-53`（B6）。
- **R-new-6（悬空引用）→ 已消解**（见 B 节第 4 条）。

🔴 **上游的一项**遗漏**（我补的）：新增 policy 轴 `evidence.grill_adversarial_stage` 的**连带改点**上游与作者都没写全。见「新发现 N-3」。

---

## 新发现（上游没有的）

### N-1（阻塞 B-1）甲口径下的**完整**既有用例改动清单 = 17 条，而 `tasks.md:33-43`（B3）只枚举了 **9** 条，漏掉 4 条

实测（helpers 补 `stage` 后、甲口径）17 条失败项的完整清单，按「`tasks.md` 有没有点名」切开：

**共同项 4 条（`甲 ∩ 乙`，实测交集精确等于 B2 那 4 条）——`tasks.md:33-35`（B2）已点名：**

| 用例 | `tasks.md` |
|---|---|
| `test_building_gate.py::test_green_when_building_evidence_present` | ✅ B2 |
| `test_building_gate.py::test_code_change_after_the_review_is_stale` | ✅ B2 |
| `test_building_gate.py::test_building_stage_is_configurable` | ✅ B2 |
| `test_check_protected.py::test_renaming_with_an_event_is_allowed` | ✅ B2 |

**甲独有 13 条（= B3 声称的「再改 13 条」）——B3 只枚举了其中 9 条：**

| 用例 | 条数 | `tasks.md` 点名 |
|---|---|---|
| `test_orphan_reports.py::test_build_then_check_agree_on_noncanonical_report_paths`（4 个参数化项） | 4 | ✅ B3 |
| `test_orphan_reports.py::test_directory_named_like_a_report_is_not_an_orphan` | 1 | ✅ B3（按文件） |
| `test_orphan_reports.py::test_extra_non_markdown_files_are_not_orphans` | 1 | ✅ B3（按文件） |
| `test_orphan_reports.py::test_symlinked_report_is_not_an_orphan` | 1 | ✅ B3（按文件） |
| `test_orphan_reports.py::test_two_manifests_binding_the_same_report_is_not_an_error` | 1 | ✅ B3（按文件） |
| `test_building_gate.py::test_not_required_when_only_the_change_dir_changed` | 1 | ✅ B3 |
| `test_acceptance.py::test_f1_end_to_end_green` | 1 | ❌ **没点名** |
| `test_acceptance.py::test_f2_handwritten_allow_event_is_not_blocked` | 1 | ❌ **没点名** |
| `test_check_manifest.py::test_report_inside_reviews_is_evidence` | 1 | ❌ **没点名** |
| `test_manifest_build.py::test_round_trip_build_then_check_is_green` | 1 | ❌ **没点名** |

小计 8 + 1 + 4 = **13**（B3 枚举 9，漏 4）。

**关键交叉验证（排除「那 4 条会被 helpers 顺手治好」这个可能）**：我另跑了「**不补 helpers** + 甲补丁」的 30 条对照，`comm -12` 出「补/不补 helpers 都失败」的集合，其中含这 4 条 ⇒ **helpers 的默认改动治不好它们**，必须逐条改。而被 helpers 治好的 13 条（`test_check_manifest` 6 条、`test_check_protected` 2 条、`test_check_contract`/`test_check_onboarding`/`test_invariants`/`test_require_change` 各 1 条、`test_manifest_build::test_round_trip_with_a_protected_spec_write`）**不在甲的清单里**——这正是上游「事实 2」（`test_invariants.py` 不该出现）的同一个机制，只是上游只发现了其中 1 条。

**两处错误**：

1. **算术与来源都对不上**：`tasks.md:36` 写「甲：**再改 13 条**（实测 17 − 4；权威清单 = `reviews/grill-review.md`『原稿被证伪的事实』1–3）」。**数字 13 是对的**（17 − 4 确实 = 13，我实测交集精确等于 B2 的 4 条），**但它下游只枚举了 9 条**。更要紧的是那句「权威清单 = `grill-review.md` 的事实 1–3」——**那三条只覆盖 orphan 的 8 个参数化/非参数化项与 `test_not_required_…`**，根本不含 `test_acceptance` / `test_check_manifest` / `test_manifest_build` 那 4 条。⇒ **这句「权威出处」是悬空的**：照它去查会得到一份只有 9 条的清单，而 `tasks.md` 自己也是 9 条。两个「权威」同错，实现者无从发现漏了 4 条。（这正是本仓「修正只落一份 artifact」的老毛病：算出了 13，却只把其中 9 条写下来。）

2. 漏掉的 4 条里有 3 条来自 `test_acceptance.py` / `test_manifest_build.py`——**端到端 / 往返**类用例，它们红的原因是「自造证据集里现在还需要一份 `grill-adversarial` manifest」，改法与前 9 条同构（补证据，不放松断言），所以**不影响「不得放松原本要钉的东西」这条原则**，只是清单不全。

**修法（最小）**：把 `tasks.md:36` 的括注改成
`（实测 17 = B2 的 4 条 ∩ + 本行下方 13 条；完整清单：orphan 8 + test_not_required_… 1 + test_acceptance::test_f1_end_to_end_green + ::test_f2_handwritten_allow_event_is_not_blocked + test_check_manifest::test_report_inside_reviews_is_evidence + test_manifest_build::test_round_trip_build_then_check_is_green）`，
并删掉「权威清单 = `reviews/grill-review.md`『原稿被证伪的事实』1–3」这句（或改成「权威清单 = 本 change 的 `reviews/grill-adversarial.md` N-1」）。

### N-2（阻塞 B-2）E0b 的完整推演：**走得通，但必须写死「第二份报告覆盖第一份」**

我把 E0b 的三个可能形态全跑了一遍（`乙` + helpers 补丁的副本里）：

| 第二份报告的落盘方式 | 实测 `check` | 说明 |
|---|---|---|
| **原地覆盖** `reviews/grill-adversarial.md` + 重跑 `manifest build --stage grill-adversarial` | **退 0 ✅** | 报告文件仍只有一份；manifest 重建后 `report_hash` 对上。 |
| 另起文件名（如 `grill-adversarial-r2.md`）并**把它**建成新 manifest | **退 1 ✗** | 报 `孤儿报告：reviews/grill-adversarial.md 未被任何 manifest 绑定`——**第一份报告变成孤儿**。 |
| 另起文件名但**保留旧 manifest** | 不可行 | `stage_manifest_findings_in_change` 取 `matching[0]`（按路径排序），会**认第一份**，第二份反成孤儿。 |

⇒ **结论**：E0b「重跑一次对抗轮」**不是**「产一份新报告」，而是「**重写同一份报告 + 重建它的 manifest**」。这必须写进 `tasks.md` E0b（现在 `tasks.md:75-77` 只说要重跑，没说落盘方式）。**这不是我加的约束，是 D1 自己引以为据的孤儿规则**——上游 D1 用「裸报告会被孤儿规则判红」论证形态选择，却没人把同一条规则推到 E0b 上。

**其余推演（都通）**：
- **与 `guard` 的关系无死锁**：`guard` 只查 `grill_stage`（实测放行只需 grill manifest），E0 的「先放行 `src/**`」不依赖 `grill-adversarial` ⇒ 不存在「要写码就得先有对抗证据、要对抗证据就得先写码」的环。
- **与 `manifest build` 的时序无死锁**：`manifest build` 不 commit、`check` 只看 `HEAD` 可达的历史，所以「build → commit → rebuild」这条链没有任何环节要求「manifest 先于它绑定的 revision 存在」。
- **E0b 是**循环**而不是**单步**（上游与作者都没说）：第二份报告只要给出 `CHANGES_REQUESTED` 并要求修 `spec.md`/`design.md`，修完的证据立刻 stale ⇒ 必须再跑。实测：三份证据齐备 ⇒ `check` 退 0；此后改 `specs/x/spec.md` ⇒ 退 1。**这条本身是**正确且期望**的行为（`templates/grill.md:131` 的「修 → 再审」），但 `tasks.md:75-77` 的「**重跑一次**」会让实现者以为一次就够。**建议改写为「**重跑到 PASS 或轮数封顶**（默认封顶 3 轮，见 `templates/grill.md:131`），每轮覆盖同一份报告」**，并显式声明「Q2 选甲时，重跑到 `CHANGES_REQUESTED` 收尾也算合格（`spec.md:101-104` 的 Scenario 已钉住）」——否则实现者会以为必须重跑到 PASS，与 Q2 甲矛盾。

### N-3 `default_policy_doc()` 加字段是安全的（我实测排除了一个我担心的连带）

我原本怀疑 A2（往 `default_policy_doc()` 加 `grill_adversarial_stage`）会打红 `tests/test_init_policy.py:130`（`assert json.loads(policy.json) == policy_mod.default_policy_doc()`）——因为该行的断言是**整份 doc 相等**，而 `CUSTOM_DOC`（`tests/test_init_policy.py:22-31`）的 `evidence` 里没有新轴。

**实测结论：不会。** 我把 A2 的完整改动（`constants.py` 加常量 + `policy.py` 加字段/回落/出厂 doc）单独打进一份干净副本，全量 `uv run pytest -q` ⇒ **420 passed**。原因：`:130` 比的是「磁盘上的出厂 policy」与「现算的出厂 doc」，两者**同时**带上新轴，仍然相等；`CUSTOM_DOC` 那侧只在「冲突/幂等」用例里出现，不参与这条 `==`。⇒ **A2 是甲乙中性的，无连带**。（我把这条写成「实测排除」而不是「风险」，因为它本来是最像地雷的地方。）

### N-4 新增 policy 轴的回落语义与既有两条轴**一致**（实测）

- 出厂 doc：`policy.default_policy_doc()` 的 `evidence` 实测 = `{review_manifest_glob, events_file, protected_write_event_types, grill_stage, building_stage}`（新轴加入后应为 6 项）。
- **老 policy（`evidence` 里没有 `grill_adversarial_stage`）**：实测把该键删掉后 `check` **退 0**（回落出厂默认 `"grill-adversarial"`，保护性默认生效）。既有两条轴用的是同一套 `evidence.get(k) or C.DEFAULT_*` 写法（`policy.py:115-121`），A2 只需照抄 ⇒ **回落语义一致，无新风险**。

### N-5 ⚠️ 空报告正文**完全合法**——这条必须进诚实边界，否则读者会以为门至少核了内容

实测（`乙` 补丁副本）：把 `reviews/grill-adversarial.md` 写成**零字节**，再 `manifest build --stage grill-adversarial` 绑定它 ⇒ **`check` 退 0**。只有空格的报告（`"   \n\n"`）同样退 0。

这是 `verify_body=False` 的**直接推论**，机制无误、与 D3 甲一致。**但现有三处诚实边界都没写这一句**：
- `design.md:122-124`（诚实边界）写的是「跑一轮、拿到 `CHANGES_REQUESTED`、什么都不修也能过」；
- `spec.md:106-119`（边界声明 1–3）写的是 require_change_for=[]、防伪造、design 未绑定；
- `design.md:154` 要求 README/§9 并列写死**两条**边界（① verdict 不参与；② 只保证存在+绑 revision）。

**缺的是第三条**：「**报告正文不校验——空文件也算合格证据**」。不写这句，README 的「证据存在即满足」会被读成「至少有一份报告」。**建议**：`spec.md` 边界声明加第 4 条 + `design.md:154` 的两条边界扩成三条 + `tasks.md` D3/D4 同步。**非阻塞**（不影响实现正确性），但对**接入方的预期管理**是关键的一句。

### N-6 `spec.md` 的「多 change 同 PR」Scenario 与 D5 逐字对得上，**但它在乙口径下是**不成立的

- **对得上**：`spec.md:36-40` 的四要素（触发面内 / 另一个 change / 每个都被要求 / 不提供 `adversarial_exempt_changes`）与 `design.md:135-138`（D5）逐条对应，措辞一致。✅
- **对不上的是 Scenario 自己的 `Given`**：`spec.md:37` 写「本次 diff 触及触发面，且同时触及**另一个** change 目录（**该 change 自身无实现**）」。触发面 = `code_hits`（乙）时，一个「无实现」的 change 目录**不可能**自己满足触发面——所以这条 Scenario 只有在 **甲** 口径下才自洽。**甲/乙都没定案，这条 Scenario 现在编码的是甲的语义。** 这与 `spec.md:30-33` 那条「`Given` 待 Q1 定案替换」（已在 B5 登记）是**同一类问题**，但**没有被登记**——`tasks.md:47-49`（B5）只列了两处缺口，这两处第三条不在其中。

**非阻塞但要合并处置**：B5 应扩成三处（补「多 change 同 PR」Scenario 时**顺带**把它的 `Given` 也按 Q1 定案写准）。若只按 B5 现有字面施工，Q1 选乙后 `spec.md:36-40` 会留下一条**在乙口径下永远无法构造**的 Scenario——`check` 不会因此报错（Scenario 是文档），但 spec 与实现会第一次出现真正的语义分歧。

### N-7 `design.md` §5「配套的 spec 修订」只列 2 处，`spec.md` 里实际有 **3 处**挂着「待 Q1/Q2 定案」

`design.md:224-228` 与 `tasks.md:47-49` 都写「两处缺口」。实读 `spec.md`，挂待定标记的数量更多：

1. `spec.md:16-18`「⚠️ 触发面待 Q1 裁定后钉死」；
2. `spec.md:30-33`「⚠️ `Given` 待 Q1 定案替换」；
3. `spec.md:36-40` 多 change Scenario 的 `Given`（**无标记**，但实际依赖 Q1，见 N-6）；
4. `spec.md:98-99`「> 若 Q2 选乙，本 Requirement 换成……」；
5. `spec.md:93` 的小节标题「Requirement: verdict 文本不参与判定（**选甲时**）」。

⇒ 「两处」是**下限不是全集**。**非阻塞**（实现者 grep 「待 Q1」/「若 Q2」能找齐），但把「两处」写成定数会让 E0「把定案替换进 `spec.md`」这一步的完成判据模糊。建议把 B5/§5 的措辞从「两处缺口」改成「**所有挂 Q1/Q2 待定标记的段落**，至少含下列 2 处」。

### N-8 R7/R8/R9 与任务的对应关系（逐条核）

| 风险 | 对应任务 | 结论 |
|---|---|---|
| R7（worktree `.git` 是文件） | `tasks.md:50-53`（B6） | ✅ 有 |
| R8（helpers 默认报告名） | `tasks.md:31-32`（B1 顺手改） | ✅ 有 |
| R9（`templates/**`/`plugin/**` 也算落实现） | `tasks.md:66`（D4 = README 写触发条件） | ⚠️ **勉强**：R9 要求「README 的触发条件里应写明含模板/插件目录」，D4 只说「写具体触发条件」，**没点明这句**。建议 D4 补「（本仓含 `templates/**` / `plugin/**`）」。 |

⇒ 「写了风险但没人做」的严格版本**不存在**，但 R9 的任务映射薄。**非阻塞**。

### N-9 `spec.md` 用的轴名与 `design.md` 的常量名对得上，但 spec 从未点明**默认值**在哪个阶段生效

`spec.md:9-11` 写「`stage=<grill_adversarial_stage>`（默认 `grill-adversarial`，`policy.evidence.grill_adversarial_stage` 可覆写）」，与 `design.md:64-65`（D1）一致。✅ 无问题，仅记录已核。

---

## Code-Resolved（我自己定案的，不进给用户的清单）

- **「甲在语义上不可接受」不成立**（上游 Q1 的措辞需要削弱）：`test_not_required_when_only_the_change_dir_changed` 在甲口径下**可以**改写成绿（补一份空正文的 `grill-adversarial` 证据即可，实测空文件合法）。准确的说法是「甲的触发面**没有『不触发』分支**，所以这条门在提案期只能靠空报告满足」。⇒ 这是给用户拍板甲的**关键事实**，措辞必须准。
- **`spec_hash 不匹配` 的复现手法要写清分母**：上游给的手法（证据提交**之前**整段替换 `specs/`）实测**退 0**；要看到不匹配必须「先产证据、后改 `specs/`」。结论方向不变，但照字面复现会得反例。
- **stale 条数 = manifest 份数**（1/2/3 三组对照实测），不是常量 3。
- **E0b 的第二份报告必须覆盖第一份**（三种落盘方式实测，只有覆盖退 0）。
- **`guard` 只需要 grill manifest** ⇒ E0 的「先放行 `src/**`」与 E0b 无环（实测 `guard --change add-x --path src/app.py` 在只有 grill 时退 0）。
- **A2（新增 policy 轴）是甲乙中性的、无连带**（实测全量 420 passed）。
- **老 policy 缺新轴 ⇒ 回落出厂默认，`check` 退 0**（实测）。
- **空/空白正文的对抗报告 ⇒ `check` 退 0**（实测）。
- **本仓 active change 是 6 个**（不是 5）：`building-review-gate` / `dogfood-bootstrap` / `events-readpoint-fix` / `grill-adversarial-gate` / `grill-evidence-gate` / `guard-crash-exit`；前 5 个有 `grill-adversarial.manifest.json`，第 6 个（本 change）没有——这是预期的。

---

## 非阻塞观察（共 9 条，均不影响判定正确性）

1. `design.md:240`（§7）的裸数字「**3 条** stale」脱离上下文会被当常量（见 A 节 D6 条）。
2. `tasks.md:36` 的「再改 13 条」与它自己的枚举（9 条）不符——**已列为阻塞 B-1**，此处不重复计数。
3. `tasks.md:65`（D3）写「**诚实边界**（verdict 不参与 / 设计内容未被哈希绑定 / 防漂移不防伪造）」= 三条，而 `design.md:154` 要求 §9 写「**同两条边界**」= 两条 ⇒ 口径不一致（建议 §9 写三条）。
4. `spec.md` 缺第 4 条边界：「报告正文不校验，空文件亦合格」（见 N-5）。
5. `tasks.md:47-49`（B5）与 `design.md:224-228`（§5）都写「**两处**缺口」，实际至少 3 处（见 N-6/N-7）。
6. `tasks.md:66`（D4）没点明 R9 要求的「本仓含 `templates/**` / `plugin/**`」那句（见 N-8）。
7. `design.md:185-186` / `spec.md:117-119` 的 `specs` 哈希复现手法需补时序（见 Code-Resolved）。
8. `tasks.md:36` 引的「权威清单 = `reviews/grill-review.md`『原稿被证伪的事实 1–3』」覆盖不到 `test_acceptance` / `test_manifest_build` 那 3 条（见 N-1 第 1 点）——修 B-1 时一并删掉这句。
9. `design.md:31-32` / `proposal.md:65` 的「5 个 active change」在本 change 合入后就不再是全集（会变 6 个）——是**当时的**实测陈述，措辞已安全（未写成「全部」），仅提示别升级措辞。

---

## 需要用户裁定（不阻塞我这一轮 verdict，随停轮的 Q1–Q5 一并给）

- **给 Q1 的一条新事实（措辞用）**：甲方**不是**「技术上做不到」——`test_not_required_when_only_the_change_dir_changed` 可以改写为绿（补空正文证据）。选择甲的真实代价是「**这条门在『只动 change 目录』的场景下只能被空气满足**」，即门形同虚设；而乙保留了「提案期不受这道门约束」这一可表达的语义。请主 session 用这个措辞，不要用上游「甲必须重写这条语义钉子 ⇒ 不可接受」的说法。
- **给 Q2 的一条新事实（措辞用）**：若选乙（要求最终裁定 = PASS），E0b 的重跑必须**重跑到 PASS**，而对抗轮的默认产出是 `CHANGES_REQUESTED`（5 份历史报告**每份**都含中间轮 CR，见 A 节 D3 条）⇒ 乙口径下**必须**同时给出 `reviews/<stage>-override.md` 之类的人工覆盖形态，否则 `templates/grill.md:131` 的「到顶交人」被无声取消。这条上游已提（`grill-review.md:47`），我实测确认其现实性。

---

## 复核边界（我这轮怎么做的）

- 全部实测在 `/tmp/gx/**`：`repo`（基线 + 机制探针）、`jia` / `yi`（甲乙补丁，helpers 不改）、`jia-h` / `yi-h`（甲乙补丁 + helpers 改）、`axis`（A2 单独验证）。**被审 worktree 未做任何实验**；本文件是唯一的仓内写入（新建）。
- ⚠️ **一个我踩到并修好的坑，值得记入实现期配方**：`cp -a` 出的副本会连 `.venv` 一起复制，而 `.venv/lib/.../_editable_impl_witnessloop.pth` 里写的是**源副本的绝对路径** ⇒ 在副本里跑 `uv run pytest` 会**测到源副本的代码**（我的第一轮四组对照因此全得 `2 failed / 418 passed`，与 churn 表完全不符）。**修法：副本里 `rm -rf .venv && uv sync` 重建**。`design.md:202`（R7）/`tasks.md:50-53`（B6）的配方只写了 `rm -f .git && git init`，**不够**——建议 B6 补一句「并 `rm -rf .venv && uv sync`，否则测的是别的副本」。（pytest 本身在 `tmp_path` 建独立仓，不受此影响；受影响的是**副本自己**的源码。）
- 环境：`export PATH=/home/happy/.local/bin:$PATH`；`uv run pytest -q`（未加 `--extra dev`）。基线 **420 passed** 独立复现两次。
- 收工核对：`git status --short` 为空、`git log -1` = `ef31a2a`、`git worktree list` 无新增 worktree、主仓与各副本的 `.git` 互不相干。

---

# 第 2 轮（R2）

- run id: `adversarial-reviewer-grill-adversarial-gate-r2-2026-10-12T143626Z`
- 时间: 2026-10-12T14:36:26Z
- 立场: 默认作者「已修完」的自述有错，逐条实测复核（不抽样、不看自述）
- 复核对象: 提交 `d6d74fa`（`git diff ef31a2a d6d74fa` 触及 `design.md` / `tasks.md` / `spec.md` + 新增本报告文件）
- 方法: `/tmp/g2/repo` 独立副本（`rm -rf .git .venv` → `git init` → `uv sync` 重建）；被审 worktree 只读，唯一写入是本次追加。

## Verdict

**PASS**

R1 的 2 条阻塞项（B-1、B-2）**都已真正关掉**，且是用**实测清单/实测机制**关的，不是措辞敷衍：B3 现在逐条点名全部 13 条（含 R1 新发现的 4 条），E0b 写死了落盘路径并改成循环。M-1..M-8 八项也已闭环。

**唯一遗留 = 3 条非阻塞的「摘要行未随正文一起改」（N-A/B/C）**，都是 `design.md` 的**引用/摘要**没跟上它自己的新正文：

- **N-A** `design.md:87` 仍写「权威出处是 `reviews/grill-review.md` 的『原稿被证伪的事实』」——**与 `tasks.md:37-38`、`tasks.md:48` 刚改成的「`reviews/grill-adversarial.md` 的 N-1」直接冲突**，且 R1 已实测那 4 条**不在** grill-review 里。
- **N-B** `design.md:291`（§7 Code-Resolved）仍写「只有上文 §5 列的**两处**缺口」——§5 自己已改成「所有挂 Q1/Q2 待定标记的段落（对抗轮 R1 指出『两处』是下限不是全集）」。
- **N-C** `design.md:289`（§7 Code-Resolved）仍写「改 `specs/` ⇒ `spec_hash` 不匹配」——R1 订正后 `design.md:196-198` 与 `spec.md:120` 都已写清「同一时序下改 `specs/` **也**退 0；要看到不匹配必须**先产证据、后改**」，**§7 这一行是唯一没跟上的**，照它复现会得反例（正是 R1 报的那个坑）。
- 附带（同一类）：`design.md:202`（R-new-1）仍要求 §9/README 写「**两条**边界」，而 `design.md:164-165`（D7）与 `tasks.md:79-82`（D3）已统一为**三条**。

⇒ 判定为事实缺陷、但不阻塞：`tasks.md B3:36-51`（实现者真正照着做的那份清单）**是完整正确的**，三条遗留都在 `design.md` 的摘要/引用层面，不会让实现走偏。建议按 N-A/B/C 顺手改掉——**这三处正是本仓 R1 报的「修正只落一份 artifact」，只是这次落在「摘要行」上。**

---

## 逐条核验（M-1 … M-8）

### M-1 `tasks.md` B3 的 13 条清单 + 「权威清单」悬空引用 → **已关掉**

**作者声称**：B3 给出完整清单、删掉悬空引用。
**实测**（`tasks.md:36-51` 逐行读）：

- ① `test_orphan_reports.py` **8 项**，且把 4 个参数化项与另外 4 条**逐个点名**（`:38-41`）✅
- ② `test_building_gate.py::test_not_required_when_only_the_change_dir_changed`（`:42`）✅
- ③ `test_acceptance.py::test_f1_end_to_end_green`（`:43`）✅
- ④ `test_acceptance.py::test_f2_handwritten_allow_event_is_not_blocked`（`:44`）✅
- ⑤ `test_check_manifest.py::test_report_inside_reviews_is_evidence`（`:45`）✅
- ⑥ `test_manifest_build.py::test_round_trip_build_then_check_is_green`（`:46`）✅
- 合计 8 + 1 + 4 = **13**，与 R1 实跑的 `jia-h` 17 条失败集**逐条一致**（我逐名字比对过，无遗漏、无多列）。
- 悬空引用：`tasks.md` 里「权威清单 = `grill-review.md`…1–3」**已删**；出处改指 `reviews/grill-adversarial.md` 的 N-1（`:37-38`、`:48`）——**该文件里 N-1 确实存在且就是这份清单**，指向有效 ✅
- 另：B3 还补了 R1 的交叉验证结论「漏的那 4 条**不会被 B1 的 helpers 默认改动治好**」（`:47`），并把我订正的措辞（②「只能靠空正文证据转绿」）写进 `:50-51` ✅

⇒ **关掉。** 但见 **N-A**：`design.md:87` 的同一句没改，两处出处现在互相矛盾。

### M-2 `tasks.md` E0b 的落盘方式 + 循环 + CHANGES_REQUESTED 合格 → **已关掉**

**作者声称**：写死「同一路径原地重写 + 重跑 manifest build」、改成循环、声明 Q2 甲下 CR 收尾也合格。
**实测**（`tasks.md:93-102`）：

- 「第二轮报告必须写在**同一路径** `reviews/grill-adversarial.md`……**不要**另起文件名——第一份会立刻变成**孤儿报告**、`check` 退 1，然后**重跑** `manifest build --stage grill-adversarial`」✅（`:96-99`）
- 「**它是循环不是单步**……**重跑到 PASS 或轮数封顶（默认 3 轮，`templates/grill.md:131`）**」✅（`:100-101`）
- 「**Q2 选甲时，以 `CHANGES_REQUESTED` 收尾也算合格**（`spec.md` 的 Scenario 已钉住）——别以为必须跑到 PASS」✅（`:102`；我核了 `spec.md:101-104` 确有那条 Scenario）

**我独立复核了这三点赖以成立的三条机制**（`/tmp/g2/repo` 新副本，走真实 `manifest build`、不靠 helpers 断言）：

| 做法 | 实测 |
|---|---|
| 报告文件名**与惯例无关**（绑 `reviews/adversarial-notes.md`）+ 第 2 轮**追加**进同一文件 + 重建 manifest | `check` **退 0** ✅ |
| 只追加、**不**重建 manifest | `check` **退 1**：`report_hash 不匹配：报告 reviews/grill-adversarial.md 的字节与 manifest 记录不符` ✅（⇒「必须重跑 build」是真的） |
| 第 2 轮写进**新文件名** | `check` **退 1**：`孤儿报告：reviews/grill-adversarial-r2.md 未被任何 manifest 绑定` ✅（⇒「不要另起文件名」是真的） |

另：R2 追加**只需重建 grill-adversarial 那一份** manifest，其余两份 manifest 不受影响（它们各自绑自己的报告，`report_hash` 互不相干）——我实测重建单份后 `check` 退 0。

⇒ **关掉。** 补充一句给实现者：`tasks.md:96` 说「关键是**路径不变**」是准确的——`check` 从不看文件名，只看该文件是否被某份 manifest 的 `report_path` 解析到。所以「原地重写」与「原地追加」等价，写哪一种都行（本仓惯例是追加，见 5 份历史报告）。

### M-3 第三条诚实边界（空文件亦合格）四处落地 → **已关掉**

| 应落之处 | 实测位置与措辞 |
|---|---|
| `spec.md` 边界声明 | `spec.md:124-127` 第 **4** 条「**报告正文不校验——空文件亦合格**」✅ 口径：判据止于 `verify_body=False`；零字节/空白 ⇒ 退 0 |
| `design.md` D3 | `design.md:129-131`「⚠️ **再加一条（对抗轮 R1 实测发现，原稿三条边界都没写）**」✅ |
| `design.md` D7 | `design.md:161-164` 三条并列，其中 ③「**报告正文不校验——空文件亦合格** —— 对抗轮 R1 的 N-5」✅ |
| `tasks.md` D3 | `tasks.md:79-82` 三条并列，③ 同款措辞 ✅ |
| `tasks.md` D4 | `tasks.md:83-85`「+ 同 D3 的三条边界」✅ |

⇒ **四处**都有，且「空文件亦合格」这个断言四处一致。**关掉。**
（一处可选打磨：`design.md:129-131` 把它称作「**再加一条**」，而 D7/tasks 称「三条边界」，读起来像 D3 有四条。实际 D3 现在列了 3 个独立事实（「跑一轮不修也能过」的已知上限、「空正文也合格」、以及原有的 D3 正文），而 D7/tasks 的三条是另一个分组（verdict 不参与 / 只保证存在+绑 revision / 空文件亦合格）——两组都是三条但**成分不同**，容易读混。非阻塞。）

### M-4 B5 从「两处」改成「所有挂 Q1/Q2 待定标记的段落」+ 多 change Scenario 的 Given → **已关掉**

- `tasks.md:55` 改成「把 `specs/adversarial-evidence/spec.md` 里**所有挂 Q1/Q2 待定标记的段落**按定案替换（「两处」是**下限不是全集**——对抗轮 R1 实测至少 5 处挂标记）」✅
- ③ 单列了多 change Scenario 的 `Given` 在乙口径下**永远构造不出来** ✅（`tasks.md:57-59`）
- `design.md §5:238-246` 同步改成同一口径并列 4 条 ✅
- **`spec.md:37-40` 本体的 Given 也已按 R1 标注**：「⚠️ 原稿写『该 change 自身无实现』——**那是甲的语义**……定案后 MUST 按 Q1 重写」✅

**我数了标记**：`spec.md` 里 `⚠️` 共 **5 处**（`:16` 触发面待 Q1、`:30` 未触发 Scenario 的 Given、`:37-39` 多 change Scenario、`:76` 若 Q2 选乙、`:96`+`:101` 「（选甲时）」小节 + 「若 Q2 选乙」），B5 声称的「至少 5 处」**属实**（B5 的编号①②③④ 覆盖了其中 3 处 + Q2 那处，多 change 那处单列）。

⇒ **关掉**（B5 的 ①② 有轻微交集：①「未触发时不误伤」的 Given 与 ②「触发条件本身（正文 + 各 Scenario 的 `Given`）」在「各 Scenario 的 Given」上重叠，读起来像两项其实覆盖三项。非阻塞。）

### M-5 `tasks.md` D4 点明 `templates/**` / `plugin/**` → **已关掉**

`tasks.md:83-84`：「写**具体触发条件**（⚠️ **必须点明**「落了实现 = 命中 `require_change_for`，**本仓含** `templates/**` / `plugin/**`」，R9）」✅ 与 `design.md:159-161`（D7）/ `design.md:223-225`（R9）口径一致。**关掉。**

### M-6 `spec_hash` 时序写清 → **design 正文关掉 / spec 关掉 / `design.md:289` 未关**

- `design.md:196-198`（R4）：「⚠️ **时序要写清**（对抗轮 R1 订正了 grill 原话）：同一时序下改 `specs/` **也退 0**——因为 `write_review` 是对**当时**的 `specs` 取哈希，两侧天然一致。要看到 `spec_hash 不匹配`，必须**先产证据、后改** `specs/`」✅
- `spec.md:118-120` 同款表述 ✅
- ❌ **`design.md:289`（§7 Code-Resolved）仍写**「R4 实测（整体替换 `design.md` 再落证据 ⇒ `check` 退 0；改 `specs/` ⇒ `spec_hash` 不匹配）✅」——**未改**。这一行是 R1 明确点名「照字面复现会得反例」的那句，现在成了 design.md 内部唯一与新正文矛盾的陈述。

⇒ **正文两处关掉，摘要一处未关**（见 **N-C**）。因 `tasks.md` 与 `spec.md` 都不依赖这句，非阻塞。

### M-7 stale 条数 ≡ manifest 份数 进 D6 与 spec Scenario + §7 裸数字加注 → **已关掉**

- `design.md:154-155`（D6）：「⚠️ **条数 ≡ 该 change 目录里 manifest 的份数**（对抗轮 R1 做了 1/2/3 三组对照：1 份 ⇒ 1 条、2 份 ⇒ 2 条、3 份 ⇒ 3 条）——`_check_git_span` 是**逐 manifest** 判的，别把 3 当常量」✅
- `spec.md:53`：stale Scenario 的 `Then` 后补「（⚠️ 报错**条数 ≡ 该 change 目录里 manifest 的份数**——逐 manifest 判定，实测 1/2/3 份 ⇒ 1/2/3 条）」✅
- `design.md:257-258`（§7）：裸「**3 条**」后已加「——⚠️ **条数 ≡ manifest 份数**，见 D6，别当常量」✅

⇒ **三处全关掉。**

### M-8 `design.md` D3/D7 与 `tasks.md` D3/D4 都是三条 → **已关掉（口径已统一）**

- `design.md:164-165`（D7）：`§9 同族新增小节（触发面 + 判据 + **同三条边界**）` ✅
- `tasks.md:79-82`（D3）：`**三条诚实边界并列写死**（① verdict 不参与 … ② 只保证证据存在并绑在最终 revision … ③ 报告正文不校验——空文件亦合格）——与 README 的口径**逐条一致**（对抗轮 R1 指出原稿 design 要两条、tasks 要三条，口径不一致，已统一为**三条**）` ✅

⇒ **关掉。** ⚠️ 但**同一份 design.md 的 `:202`（R-new-1）仍写「必须并列写死两条边界」**——即 R1 报的「口径不一」在 D7 与 §4 R-new-1 之间**仍然存在**，只是方向反了（现在 D7 三条、R-new-1 两条）。见 **N-D**。

---

## R7 配方复核（第 9 项）

- `design.md:215-217`（R7）：「⚠️ **还要 `rm -rf .venv && uv sync`**（对抗轮 R1 踩到）：`cp -a` 会连 `.venv` 一起复制，而 editable 安装的 `.pth` 里写的是**源副本的绝对路径** ⇒ 在副本里 `uv run pytest` 会**测到源副本的代码**（它第一轮四组对照因此全得 `2 failed / 418 passed`）」✅ 成因与现象都写对。
- `tasks.md:64-66`（B6）：同款，且给了 `rm -rf .venv && uv sync` 的命令 ✅
- 我这次按它执行：副本 `rm -rf .git .venv` → `git init` → `uv sync` ⇒ `.pth` = `/tmp/g2/repo/src`、全量 `uv run pytest -q` = **420 passed**（与基线一致，证明测的是本副本而非别的副本）✅

⇒ **关掉。**

---

## 新发现（R2）

### N-A（非阻塞，但**是 R1 阻塞项的残留**）`design.md:87` 的「权威出处」未随 B3 一起改，两处现在互相矛盾

- `design.md:87`：「……已删——清单**不在这两份文件里维护**，权威出处是 `reviews/grill-review.md` 的「原稿被证伪的事实」。」
- `tasks.md:37-38` / `:48`：「……权威出处是 `reviews/grill-adversarial.md` 的 N-1。」
- **R1 已实测**：`grill-review.md` 的「原稿被证伪的事实 1–3」**覆盖不到**那 4 条（`test_acceptance` 2 + `test_check_manifest` 1 + `test_manifest_build` 1）——所以 `design.md:87` 现在指向一份**已知不完整**的清单，而 `tasks.md` 指向完整的那份。
- **修法**：把 `design.md:87` 的「权威出处是 `reviews/grill-review.md` 的『原稿被证伪的事实』」改成「权威出处是 `reviews/grill-adversarial.md` 的 **N-1**（`grill-review.md` 的事实 1–3 **覆盖不全**）」。
- 为什么值得改：`design.md` 是**下游实现者的第一读物**；照 `:87` 去查会得到 R1 之前那份只有 9 条的清单——**这正是 R1 那条阻塞项的成因，残留在摘要行里。**

### N-B（非阻塞）`design.md:291` 仍写「只有上文 §5 列的**两处**缺口」

§5 自己（`design.md:238-246`）已改成「**所有挂 Q1/Q2 待定标记的段落**……『两处』是**下限不是全集**（至少 5 处挂标记）」。`:291` 是同一份文档里对 §5 的**摘要**，未同步。**修法**：改成「§5 列出的**所有**挂 Q1/Q2 待定标记的段落」。

### N-C（非阻塞）`design.md:289`（§7 Code-Resolved）是 M-6 唯一未关的一处

见 M-6。**修法**：把「改 `specs/` ⇒ `spec_hash` 不匹配」改成「同一时序改 `specs/` **也退 0**（要看到 `spec_hash` 不匹配须**先产证据、后改** `specs/`）」——与 `design.md:196-198` / `spec.md:118-120` 对齐。

### N-D（非阻塞）`design.md:202`（R-new-1）与 `design.md:165`（D7）**边界条数仍然不一致**（方向与 R1 报的相反）

- `design.md:201-203`（§4 R-new-1）：「故 `docs/gate.md §9` 与 README **必须并列写死两条边界**：① verdict 不参与判定；② 本门禁只保证证据**存在**并绑在最终 revision，**不保证**对抗轮发生在写码之前。」
- `design.md:164-165`（D7）+ `tasks.md:79-82`（D3）：**三条**。

⇒ R1 的 M-8 只在 D7/tasks 侧统一了，§4 的 R-new-1 条文没跟上。**修法**：把 `:202` 改成「**三条边界**」并把 ③「报告正文不校验——空文件亦合格」补进那个列表。**非阻塞**（§9/README 的实际内容由 tasks D3「三条」驱动），但这是同一份 design.md 里第 4 处「摘要没跟上正文」。

### N-E（非阻塞 · 定性补充）三条遗留 N-A/B/C/D 的**共同成因**值得记一笔

四处全在 `design.md` 的**摘要/引用行**（`:87` §2 的出处声明、`:202` §4 的风险条文、`:289`/`:291` §7 的回顾），而它们各自对应的**正文**都改对了（`:36` §2 前文、`:164` D7、`:196` R4、`:238` §5）。⇒ 作者这轮的改法是「改正文 + 在 §7 追加一段回顾」，但**没回扫同文档内的旧摘要**。R1 报的是「修正只落一份 artifact」（design↔spec↔tasks 之间），这次是它的**文档内变体**（正文↔摘要）。**建议把这四行一并清掉，再进 E0**——因为它们全部是「实现者读 design 时会先撞到」的位置。

### N-F（已核，无问题）「多 change 同 PR」Scenario 的 Given 现在**仍带 `MUST 按 Q1 重写` 标记** ⇒ 与 `spec.md:16-18` 的「触发面待 Q1 裁定后钉死」是同一个待办，**不构成新的未登记缺口**

R1 的 N-6 担心它会「留下一条在乙口径下永远无法构造的 Scenario」而 B5 没登记。作者的处理是**在 Scenario 里就地标注**（`spec.md:37-39`）**并**把它列进 B5 ③（`tasks.md:57-59`）⇒ 已登记、且有就地标记兜底。**关掉**，无需再改。

### N-G（已核，无问题）`spec.md` 的 `⚠️` 计数与 B5 的「至少 5 处」吻合

`grep -c "⚠️"` = 5，与 B5 声称一致。**无问题。**

---

## Code-Resolved（R2）

- **报告文件名与判定无关**：实测绑 `reviews/adversarial-notes.md` ⇒ `check` 退 0。⇒ `tasks.md:96` 的「关键是**路径不变**」措辞准确（`check` 只看该文件是否被某 manifest 的 `report_path` 解析到）。
- **追加后**只重建 grill-adversarial 那一份** manifest 足够**（另两份的 `report_hash` 各绑自己的报告，不受影响）。
- **`reviews/grill-adversarial.md` 目前没有任何 manifest 绑定**（`openspec/changes/grill-adversarial-gate/reviews/` 只有 `grill-adversarial.md` 与 `grill-review.md`，无 manifest）⇒ **追加 R2 不会触发孤儿规则，也不会撞 `report_hash`**（当前 `check` 的两条 finding 是「缺 manifest / 无 stage=grill」）。这与 R1 的 B-2 是**同一个机制的乐观面**：E0b 之后才有绑定，届时才是「必须原地重写」。
- **基线复核**：`d6d74fa` 上全量 `uv run pytest -q` = **420 passed**（`/tmp/g2/repo`）。R2 只改了 `.md`，不触及 `src/` 与 `tests/`，无 churn。

## 复核边界（R2）

- 全部实测在 `/tmp/g2/repo`（`rm -rf .git .venv` → `git init -q` → `git add -A && git commit -qm base` → `uv sync`；`.pth` 实测 = `/tmp/g2/repo/src`）。
- ⚠️ **一次需记录的副作用**：我在**被审 worktree 内**跑了一次 `uv run witnessloop check --root .`（为读当前 `check` 状态），`uv` 因此在仓根建了 `.venv/`。该路径在 `.gitignore:1`（`.venv/`）内 ⇒ `git status --short` 仍为空、未产生任何可提交改动（收工核对：`git status --short` = 空）。此项**不构成对「仓库只读」的违反**（无 git 可见的写入），但按纪律记于此：**后续轮次若要读 `check` 状态，应在 `/tmp` 副本里跑**。
- 收工核对：`git status --short` 只有本报告文件的追加；HEAD 仍 `d6d74fa`；`git worktree list` 无新增 worktree。

---

# 第 3 轮（R3）

- run id: `adversarial-reviewer-grill-adversarial-gate-r3-2026-10-12T150130Z`
- 时间: 2026-10-12T15:01:30Z
- 立场: 默认「定案已完整落地」这个自述有错，逐份 artifact 对照实测
- 复核对象: 提交 `2cc56ce`（`git diff db4c29d 2cc56ce`：`spec.md` / `design.md` / `tasks.md` / `grill-review.md` 四处）
- 方法: `/tmp/g3/repo` 独立副本（`rm -rf .git .venv` → `git init` → `uv sync`；`.pth` 实测 = `/tmp/g3/repo/src`）。**未在被审 worktree 跑任何 `uv`**（R2 的遗留纪律已遵守）。

## Verdict

**PASS** —— 设计可冻结。

用户裁定（Q1 乙 / Q2 甲 / Q3 接受缺口 / Q4 只写文档 / Q5 采纳 E0b）**五条全部落到四处 artifact 且口径一致**；最关键的那条（`## User Confirmation` 能过 grill 证据判据）**实测通过**；定稿后的 5 条 Scenario 在乙口径下**全部可构造**；E0 → E0b → E1 链条**实测跑通到 `check` 退 0**。

遗留 **7 条非阻塞**（**没有一条**会改变实现行为或让门禁与 spec 不一致）：

- **N-1..N-4（同一类：条件句残留）**：定案已锁死乙/甲，但四处仍留着「**若 Q2 选乙**」「**Q2 选甲时**」这类**分支条件句**——`spec.md:76`（唯一在 spec 内的残留）、`tasks.md:101`、`tasks.md:108`、`proposal.md:56`。
- **N-5**：`tasks.md:89`（E0）把在 R2 已关闭的「B5 的两处」写回成待办（B5 本身在 `:56` 已标 `[x]` 已完成）。
- **N-6**：`design.md:119` 的「（Q2 定案 = 甲）」在「甲/乙」同时是 Q1 选项的语境里有歧义（会被读成「Q1 选甲」）。
- **N-7（新发现，实现期需注意）**：E0b 若给 `CHANGES_REQUESTED` 并要求改 `spec.md`/`design.md`，**grill 那条 manifest 也会同时变 stale**（实测：5 条 finding 里 2 条指向 `grill.manifest.json`）；`tasks.md:99-100` 只提「改完证据立刻 stale ⇒ 再跑」，**没说 grill 那份也要重建**（E1 会兜住，但那之前 `check` 会红）。

---

## 逐条核验

### M-1 定案是否完整落到四处、口径一致（含「有没有残留甲/待定」）→ **成立（遗留 7 条非阻塞，见下）**

**作者声称**：定案替换进 spec/design/tasks 三处 + `## User Confirmation`。

**实测**（逐份读，`git diff db4c29d 2cc56ce`）：

**`spec.md`**
- `:16-21` 触发条件正文 = **乙**：「触及 `policy.require_change_for` 下的路径（= 落了实现）……SHALL 复用 `checkcmd._code_hits` 的同一口径」✅——**行号我核过**：`src/witnessloop/checkcmd.py:106-122` 正是 `def _code_hits`（`def` 在 `:106`、`return sorted(...)` 收在 `:122`），**引用准确** ✅
- `:24` 未跑 Scenario 的 `Given` 改成「改了 `src/**`（命中 `require_change_for`）」✅
- `:34-35` 未触发 Scenario 的 `Given` 由**循环定义**改成具体条件「未触及 `require_change_for`（只改文档 / 只动 change 目录）」✅（R1 Code-Resolved 那条已关）
- `:40` 多 change Scenario 的 `Given` 改成乙口径「触及 `require_change_for` 且**同时**触及另一个 change 目录」，`:42` 的 `Then` 从「**每个**」改成「**两个**」✅
- `:96` Requirement 标题去掉「（选甲时）」；`:98-102` 正文改成无条件 + 补理由，删掉「若 Q2 选乙」分支 ✅
- `:90-91` 守卫缺口显式标注 Q3 已接受 ✅
- ❌ **`:76` 残留**：「（对抗轮**只**要求证据存在；**若 Q2 选乙**，另加「最终裁定 = PASS」判据——那是**新增**判据，不是复用）」

**`design.md`**
- `:3-6` 状态从「**草稿**」改成「**设计环已收敛**……决策已定稿」✅
- `:71-76`（D2）标「**乙**（Q1 停轮定案）」+ 说明甲被否的理由 ✅
- `:119-122`（D3）标「（Q2 定案 = 甲）」+ 说明乙被否 ✅（措辞见 N-6）
- `:145-147`（D4）标「Q3 定案：接受缺口」✅
- `:174-176`（D7）标「Q4 定案：只写文档、不加开关」✅
- `:320-331`（§8）标题改成「**停轮裁定**（Q1..Q5 —— 用户 2026-10-12 已逐条确认，**无待定项**）」+ 一张五行的裁定表 ✅
- `:332` 显式声明「下面保留五个问题的**完整分析**……是上述裁定的**证据**，**不是待定项**」✅ —— **这条很关键**：它让「§8 后面还大段写着『推荐乙』『（推荐）』」不再构成残留（作者已预先声明它们是证据而非待定项）。我认可这个处理。

**`tasks.md`**
- `:17`（A3）写死「**触发面 = Q1 定案「乙」** ⇒ 放进既有的 `if code_hits:` 块（与 building 那条并列）」✅
- `:36`（B3）标 `[x] ~~B3 若 Q1 选甲~~ —— **Q1 定案「乙」⇒ 本条不适用**（保留下方清单作为「甲为什么被否」的证据）」✅ —— **保留清单 + 标不适用**，比删掉更好（证据留档）
- `:56`（B5）标 `[x] **已做（2026-10-12，随停轮定案）**` 并列 ①②③④ ✅
- ❌ **`:101` 残留**：「⚠️ **Q2 选甲时**，以 `CHANGES_REQUESTED` 收尾也算合格」——Q2 已定案，条件句应去掉（改成「**定案是甲**（Q2）⇒ …」）
- ❌ **`:108` 残留**：「verdict 文本判据（**若 Q2 选甲**）」
- ❌ **`:89` 残留**：E0 里「把定案替换进 `spec.md` 的触发条件（**+ B5 的两处**）」——B5 已于 R2 扩成「所有挂 Q1/Q2 待定标记的段落」且本轮标 `[x]` 完成，这里把已关闭的旧说法写回成待办

**`proposal.md`**
- ❌ **`:56` 残留**：「**不解析 verdict 文本**（**选甲时**）：见 design D3 的诚实边界。」——（选甲时）是条件限定，现已无条件

⇒ **四处口径一致**（触发条件 = 乙、verdict = 不解析、guard 不动、只写文档），**没有一处编码了甲的口径**；残留的 4 处全是「已锁死的条件句没删」的**文案**问题。

### M-2 `## User Confirmation` 能否真过 grill 证据判据 → **关掉（实测，且带对照组）**

**作者声称**：`grill-review.md:82-89` 新增 `## User Confirmation`，逐条记 Q1..Q5 答复 + 确认时间。

**实测（端到端，非只跑解析器）**：在 `/tmp/g3/repo` 里把**本 change 真实的** `grill-review.md` 搬进测试仓，用**真实 CLI** `manifest build --stage grill` 绑上它，再跑 `check`：

```
[build grill] exit=0
check：通过 ✓        (exit=0)
```

**并直接读解析器内部**：

```
FINDINGS: 0
Open Questions 里的 Qn: [1, 2, 3, 4, 5]        ← 恰好 Q1..Q5，无多无少
User Confirmation 解析出: {1: '**乙**——触发面…', 2: '**甲**——**不解析** verdict 文本…',
                           3: '**接受缺口**——…', 4: '**只写文档**——…', 5: '**采纳 E0b**——…'}
```

⇒ **5 个 Qn 全部匹配、全部判为实质答复**（`_is_unconfirmed` 对 5 条都是 `False`），`grill_evidence_findings` 返回 **0 条**。**不再报**「Open Question Qn 未经用户确认」，也**不报**「是占位文本」。

**对照组（证明这道判据确实在判，不是空过）**：

| 篡改 | 实测 `check` |
|---|---|
| 删掉 `- **Q5**:` 整行 | **退 1**：`Open Question Q5 未经用户确认（## User Confirmation 里没有 Q5）` ✅ |
| 把 Q3 答复改成短占位「待确认」 | **退 1**：`Open Question Q3 的确认是占位文本` ✅ |
| 把 Q3 改成「**待确认**（稍后补齐）**——但其实后面写了一大堆实质内容说明理由**」 | 退 0（**通过**）——见「已知宽松面」 |

**⚠️ 已知宽松面（非本轮引入，且代码里已自述）**：`evidence._is_unconfirmed`（`src/witnessloop/evidence.py:100-108`）对**长答复**（> `_UNCONFIRMED_MAX_ANSWER_LEN` = 20 字）**不做**占位检查。⇒ 「以占位词开头 + 后面凑够 20 字」即可混过。该函数 docstring（`evidence.py:115-118`）**已明写**「占位启发式是短答复子串匹配……属『防漂移不防伪造』的既定边界，非缺陷」，且**与 grill 门禁既有行为完全一致**（本 change 未触碰）。**故不构成本 change 的缺陷**，我仅在确认它的边界时实测到并记录。

⇒ **这条最关键的要求：关掉。**

### M-3 定稿后的 Scenario 在乙口径下是否都可构造 → **关掉（逐条过）**

| Scenario | `Given` | 能否用真实 git 场景造出 |
|---|---|---|
| 未跑设计对抗轮（`:23-26`） | 改了 `src/**`，只有 grill+building 证据 | ✅ |
| 有对抗轮证据则通过（`:28-31`） | 同条件 + 一份 `grill-adversarial` manifest 绑着报告 | ✅ |
| 未触发时不误伤（`:33-37`） | 未触及 `require_change_for`（只改文档 / 只动 change 目录） | ✅ |
| **多 change 同 PR（`:39-43`）** | 触及 `require_change_for`（落实现）**且同时**触及另一个 change 目录 | ✅ **R1 的洞已补** |
| stage 拼错可诊断（`:45-48`） | 用 `grill-adversariall` 产的 manifest、仓里没有 `grill-adversarial` 的 | ✅ |
| 对抗轮之后再改设计 ⇒ stale（`:50-54`） | `head_sha=H` 之后改了 `design.md` | ✅ |

R1 唯一点名构造不出来的那条（多 change 同 PR：旧 `Given` 写「另一个 change 自身**无实现**」）**已改**：新 `Given` 把「落实现」放在**主** change 上、另一个 change 只要求「被触及」——这在乙口径下**可构造**（同一 PR 改 `src/` + 两个 change 目录）。我按此构造过（R2 的 `test_every_change_in_a_code_pr_must_have_building_evidence` 是同一形态的先例）。**逐条都可构造，无残留。**

### M-4 定案改动有没有引入新矛盾 → **未发现矛盾；发现 1 条实现期提醒（N-7）**

逐项对：

- **spec 说「复用 `_code_hits` 同一口径」而 design/tasks 提到别的判定？** → **没有矛盾**。`spec.md:19`（`_code_hits`）、`design.md:72`（「甲/乙……**`code_hits`**（本次 diff 触及 `policy.require_change_for`）时才要」）、`tasks.md:17`（「放进既有的 `if code_hits:` 块」）三处指**同一个**判据，且 `checkcmd.py:106-122` 就是它的唯一实现（`:109-111` 的 docstring 明写「**唯一**口径……分两份实现必然漂移」）✅
- **`_code_hits` 的行号引用对不对？** → **对**（`checkcmd.py:106-122`）✅——值得一提：这正是 R2 抓到的「引用行号没随正文改」那类问题，本轮**没有**重犯。
- **E0b 与 E0 的先后在新口径下是否成立？** → **成立**。`guard` 放行 `src/**` 只依赖 **grill** 证据（R1 实测：只有 grill manifest 时 `guard --change add-x --path src/app.py` 退 0），而 grill 证据在 E0 就产出 ⇒ 「先放行、定案后重跑对抗」不产生环。且乙口径下本 change 自己落了实现 ⇒ 它**必然**要 `stage=grill-adversarial`，与 E0b 的存在一致（不是多余步骤）✅
- **乙口径下 `guard` 与 `check` 的差集**：`guard` 不要求对抗轮（D4），`check` 要求 ⇒ 本地可先写码、CI 才拦——这与 Q3「接受缺口」一致，无矛盾 ✅
- ⚠️ **N-7（新发现）**：**E0b 的重跑会连带让 `grill` 那条 manifest 变 stale**。实测（`/tmp/g3/repo` 的 E0→E0b 链条）：E0b 第一轮之后若按第二轮发现改 `specs/`，`check` 出 **5 条** finding，其中 **2 条**指向 `grill.manifest.json`（`spec_hash 不匹配` + `审阅的是旧 revision`）；重建 `grill-adversarial` 之后那 2 条**仍在**。⇒ `tasks.md:99-100` 只说「改完证据立刻 stale ⇒ 再跑」，**没点明 grill 那份也要重建**。E1（`tasks.md:102`）会兜住（它明说要重建 grill/grill-adversarial/building 三份），但**在 E0b 与 E1 之间 `check` 会红**——实现者若在这个窗口跑 `check` 会看到「自己刚修完却更红」而困惑。**修法**：`tasks.md:99-100` 补一句「**改 `spec.md`/`design.md` 后，`grill` 那份 manifest 也会同步 stale ⇒ 一起重建**」。

### M-5 E0b 自身的产物约定与后续链条 → **关掉（实测链条跑通）**

**作者声称**：R3 结论追加到同一路径。

**实测**（`/tmp/g3/repo` 全链条，结果见下）：路径不变、追加式，`check` 走到 **exit=0**。

```
E0:                     exit=1（只缺 building——E1 才补；符合预期）
E0b-R1:                 exit=1（同上）
E0b-修spec后:            exit=1，5 条（2 条 grill + 2 条 grill-adversarial + 1 条 building）
E0b-R2(覆盖+重建):       exit=1，3 条（grill-adversarial 的 2 条 **全部消失**；剩的 3 条都不是它）
E0b-改design后:          exit=1，4 条（grill-adversarial 正确报「head_sha 之后改动了 design.md」）
E1（实现 + 三份全重建）:  exit=0  ✅
```

⇒ **无孤儿 / 无 `report_hash` 陷阱**：
- 第 2 轮**覆盖同一路径** ⇒ 报告文件仍**只有一份**、仍被**重建后的** manifest 绑定 ⇒ 孤儿规则不触发、`report_hash` 对得上 ✅
- 重建 `grill-adversarial` 之后它自己的 2 条 stale **立即消失**（说明重建是有效的、不是掩耳盗铃）✅
- 之后再改 `design.md` ⇒ 它**正确**变 stale ⇒ 机制在「追加式报告」下**依然有效**（没有因为追加而失效）✅
- E1 把三份全部重建 ⇒ **退 0**，链条收口 ✅

**另**：本轮的 R3 报告追加是**安全的**——`openspec/changes/grill-adversarial-gate/reviews/` 里**没有**任何 manifest（`grill-adversarial.md` / `grill-review.md` 都是**未绑定**的裸报告），孤儿规则要「有 manifest 且报告未被绑定」才触发（`contract.py:185-219`）；当前 `check` 的两条 finding 是「缺少 review manifest」「无 stage=grill 的 manifest」，与追加无关。⇒ **R3 追加后不会新增任何僵局**，E0b 届时才需要「原地覆盖 + 重建 manifest」。

### 顺带复核：R2 的 4 条非阻塞遗留是否已清 → **已全部清掉**

| R2 遗留 | 现状 |
|---|---|
| `design.md:87` 权威出处指错 | 现 `:95`「（`grill-review.md` 的「事实 1–3」只覆盖其中 9 条，**不足以**当权威出处——这正是对抗轮 R1 的阻塞项 B-1）」✅ |
| `design.md:202` 「两条边界」 | 全文件已无「两条边界/同两条」✅ |
| `design.md:291` 「两处缺口」 | 现 `:310-311`「缺口清单见 §5（**不是定数**……）」✅ |
| `design.md:289` `spec_hash` 时序 | 现 `:308`「**证据之前**整体替换 `design.md` ⇒ 退 0；要看到 `spec_hash 不匹配` 必须**先产证据、后改** `specs/`」✅ |

（`:304`/`:317` 仍出现「两处缺口」「两条边界」字样，但都是**回顾 R2 历史**的行文，不是残留断言。）

**回归**：`2cc56ce` 上全量 `uv run pytest -q` = **420 passed**（`/tmp/g3/repo`，与基线一致，无 churn）。

---

## 新发现（R3）

### N-1（非阻塞 · 文案）`spec.md:76` 是 **spec 内**唯一残留的分支条件句

`（对抗轮**只**要求证据存在；若 Q2 选乙，另加「最终裁定 = PASS」判据——那是**新增**判据，不是复用）。`
Q2 已定案为甲 ⇒「若 Q2 选乙」永远不会发生。**修法**：删掉分句，或改成「（Q2 定案为甲：对抗轮**只**要求证据存在，不解析 verdict——见下方 `Requirement: verdict 文本不参与判定`）」。
**为什么单独点出来**：其余残留都在 tasks/proposal（过程文档），**只有这一条在 spec 内**——而 spec 是 manifest 哈希绑定的 artifact，读者会把它当**已成文的需求**。

### N-2（非阻塞 · 文案）`tasks.md:101` 与 `tasks.md:108` 的「若 Q2 选甲」条件句

- `:101`：「⚠️ **Q2 选甲时**，以 `CHANGES_REQUESTED` 收尾也算合格」——Q2 已定案，应改成「定案是甲（Q2）⇒ 以 `CHANGES_REQUESTED` 收尾也算合格」。
- `:108`：「verdict 文本判据（**若 Q2 选甲**）」——应改成「verdict 文本判据（Q2 定案：不解析）」。
两处都不影响实现（A3/A4 已按乙/甲写死），但留着会让读者以为还有待定项。

### N-3（非阻塞 · 文案）`proposal.md:56` 的「（选甲时）」

`- **不解析 verdict 文本**（选甲时）：见 design D3 的诚实边界。` ⇒ 括号里的限定应去掉（Q2 已定案为甲，这就是无条件非目标）。

### N-4（非阻塞 · 文案）`tasks.md:89`（E0）把 R2 已关闭的「B5 的两处」写回成待办

`E0 停轮拿到 Q1..Q4 答复 → 把定案替换进 spec.md 的触发条件（**+ B5 的两处**）→ …`
B5 在 R2 已扩成「**所有挂 Q1/Q2 待定标记的段落**」、本轮 `:56` 已标 `[x]` 完成 ⇒ 这里应改成「（**+ B5 列的各项，已于本轮全部替换完毕**）」，否则读起来像 E0 还要再做一遍。

### N-5（非阻塞 · 可读性）`design.md:119` 的「（Q2 定案 = 甲）」

D3 的 `甲`/`乙` 是 **Q2 的**两个选项（甲 = 不解析 / 乙 = 判 PASS），而 Q1 的选项**也叫**甲/乙（甲 = 无条件 / 乙 = `code_hits`）。`:119` 的「Q2 定案 = 甲」在整份文档同时用这两套甲/乙的语境里，**会被读成「Q1 选了甲」**——与同页 `:71`「D2 触发条件 = **乙**（Q1 停轮定案…）」正好对撞。**修法**：改成「（Q2 定案：**不解析 verdict**）」——去掉「= 甲」，直接说内容。

### N-6（非阻塞 · 实现期提醒）E0b 的 stale 会**连带 grill 那份**，`tasks.md` 没提

见 M-4 的 N-7。**修法**：`tasks.md:99-100` 补「改 `spec.md`/`design.md` 后，**`grill` 那份 manifest 也会同步 stale ⇒ 一起重建**」。**为什么值得改**：E1 虽然兜住，但 E0b→E1 窗口里 `check` 会因为**两份**证据红，实现者刚修完反而看到更多红项，容易误判成「修坏了」。

### N-7（非阻塞 · 边界记录）`evidence._is_unconfirmed` 的长答复宽松面

见 M-2 的「已知宽松面」。**非本 change 引入**（`evidence.py:100-108` 是既有实现、docstring 已自述），**只是本轮实测确认了它的边界**：占位词 + ≥20 字即可通过。若日后要收紧，那是另一次 change（本 change 的 D8 非目标不含它）。

---

## Code-Resolved（R3）

- **`spec.md:19` 引的 `checkcmd.py:106-122` 准确**：`def _code_hits` 在 `:106`，`return sorted(...)` 收在 `:122`（逐行 `awk` 核过）。
- **R2 的 4 条非阻塞遗留已全部清掉**（`design.md:95` / `:310-311` / `:308`；全文件已无「两条边界」断言）。
- **`## User Confirmation` 的 5 个 Qn 与 `## Open Questions` 的 5 个 Qn 精确一一对应**（parser 内部实测：`[1,2,3,4,5]` ↔ 5 条解析成功的答复）。
- **E0→E0b→E1 全链条在乙口径下可跑到 `check` 退 0**（六步实测，见 M-5）。
- **追加式报告不破坏 revision 绑定**：重建 manifest 后 `grill-adversarial` 的 stale 消失；再改 `design.md` 它**仍会**正确变 stale。
- **R3 追加本身安全**：该 change 目录当前**没有任何 manifest** ⇒ 不触发孤儿规则、不撞 `report_hash`。
- **基线**：`2cc56ce` 上全量 `uv run pytest -q` = **420 passed**。

## 复核边界（R3）

- 全部实测在 `/tmp/g3/repo`（`rm -rf .git .venv` → `git init -q` → `git add -A && git commit -qm base` → `uv sync`；`.pth` 实测 `/tmp/g3/repo/src`）。
- **遵守了 R2 的纪律**：本轮**未在被审 worktree 里跑 `uv`**（所有 `check` / `manifest build` / `pytest` 都在 `/tmp/g3/repo`）。
- 收工核对：`git status --short` 只有本报告文件的追加；HEAD 仍 `2cc56ce`；`git worktree list` 无新增 worktree。
