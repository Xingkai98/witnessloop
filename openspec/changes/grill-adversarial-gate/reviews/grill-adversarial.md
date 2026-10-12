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
