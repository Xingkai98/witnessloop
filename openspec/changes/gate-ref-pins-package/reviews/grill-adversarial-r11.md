# 对抗验证 R11（独立零记忆）

## Reviewer

- 角色：本对话**不携带**该 change 的任何历史，所有文档里的「实测 / 已落库 / 已收敛」一律当**待验证断言**，可复算的一律复算。
- 工作目录：`/home/happy/wl-wt/archive-arrival-recognition`（witnessloop 仓的 git worktree，分支 `gate-ref-pins-package/2026-10-16`）。
- **被审 revision**：`git rev-parse HEAD` ⇒ `ba03ec82303541f27facf02a6ee169afef08d724`；`git status --porcelain` 在开工时为空（树干净、无未提交残渣）。
- 关键文件 blob（`git rev-parse HEAD:<path>`）：

  | 文件 | blob |
  |---|---|
  | `openspec/changes/gate-ref-pins-package/design.md` | `bd7d8b677f6299ecec93bf53c93804452fc4ba84` |
  | `openspec/changes/gate-ref-pins-package/proposal.md` | `903714c3fc903289fb93927e313cbe76d90cc71b` |
  | `openspec/changes/gate-ref-pins-package/tasks.md` | `73aca022d35341ca5d63b3751d976a2f67d3d9cc` |
  | `openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md` | `b5be2a29167236b07949e391270c811d1eb0cef4` |
  | `src/witnessloop/initcmd.py` | `b93b62bc427e3f982ecc23bdd3b685985f4da914` |
  | `src/witnessloop/checkcmd.py` | `e12db4d94a1d11daebc80eb1423298de57bf487a` |
  | `src/witnessloop/constants.py` | `0a64184d5435399646646356fac56dd68622ffb0` |
  | `.github/workflows/gate.yml` | `330104b810db66a7c382c89ec075a04cfb03798c` |
  | `docs/gate.md` | `d382528f79b6dd6fd245159ca70fb53889f311e0` |
  | `README.md` | `3bd4dc951af8c99ca5bc8899b1b370ce1edac339` |

- 快照与实验隔离：所有实验在 `/tmp/adv11/` 内。快照用 `git archive HEAD | tar -x -C /tmp/adv11`（**没用** `cp -a`，因为 worktree 的 `.git` 是指针文件）。真仓内**未做**任何 commit / checkout / reset / tag / push；本报告是唯一新增文件。
- 基线复算：`PYTHONPATH=src python3 -m pytest -q` ⇒ `689 passed in 36.11s`（与题面给的 689 一致）。
- 方法：①`git show --stat` 逐轮比对「处置里自称的落点文件」是否真在该提交里；②在 HEAD 上逐条核「那条断言/钉子/文档句**现在是否真的在**」；③对**行为面**的断言一律真跑（`uvx`/CI 面除外，见「未验证项」）。

## 对抗结论

### 1. 判据②：K1–K8 / L1–L6 / M1–M4 / N1–N3 / P1 / T1 / U1–U4 / V1–V4 / W1–W4 / X1 / O1 / O3 —— 逐条核，**未发现第二例 X1 式「自称已落库而实际没落」**

核法（两段）：**(a) 落点文件是否真在落地提交里**——`git show --stat` 逐个提交比对；**(b) 该落点内容在 HEAD 上是否真的存在**——grep 定位到行 +（行为类）真跑。

`git show --stat` 的逐轮结果（只列与「自称落点」相关的文件，均**命中**）：

| 轮 | 落地提交 | `--stat` 覆盖了自称的全部落点 |
|---|---|---|
| R1 K1–K8 | `5c03e26` + `545456c` + `5cc56b4` | design.md / proposal.md / spec.md / tasks.md / docs/design.md ✓ |
| R2 L1–L6 + D1/D2/D3/D4/D6 | `6813c8e` | README.md / docs/gate.md / design.md / spec.md / tasks.md / checkcmd.py / initcmd.py / tests×4 ✓ |
| R3 M1–M4 + E1/E3 | `37ab466` + `315574c` | tasks.md / initcmd.py / gate.yml / README.md / docs/gate.md / spec.md / tests×2 ✓ |
| R4 N1–N3 | `1b59eb6` + `1099284` | initcmd.py / tests/test_init_gate_ref.py / docs/gate.md / design.md / tasks.md / tests/test_gate_workflow.py ✓ |
| R5 P1（+1、2） | `b186cfa` + `1a0f9a2` | initcmd.py / gate.yml / tests/test_init_gate_ref.py ✓ |
| R6 T1 / 顺序 / D1 判定顺序 / recipe 顺序 | `1474bb2` / `4538404` / `8297b82` | tests/test_gate_workflow.py / gate.yml / design.md / tests/test_docs.py ✓ |
| R7 U1–U4 | `ab67ebd` | design.md / tests/test_check_package_ref.py / tests/test_gate_workflow.py ✓ |
| R8 V1–V4 | `3865007` | README.md / docs/gate.md / design.md / spec.md / initcmd.py / tests×2 ✓ |
| R9 W1–W4 | `24582f1` | design.md / spec.md / tasks.md / initcmd.py / tests/test_init_gate_ref.py ✓ |
| R10 X1 / O1 / O3 | `ba03ec8` | docs/gate.md / design.md / spec.md / initcmd.py / tests/test_init_gate_ref.py ✓ |

逐条**内容级**核实（在 HEAD 上的实际位置）：

- **K1**（包能自报 ref）→ `spec.md:60-72`、`design.md:146-164`（D3）、`checkcmd.py:79-92`。✓
- **K2**（「没有任何提示」是假的）→ `proposal.md:19-21` 有「⚠️「没有任何提示」是**假**的（对抗轮 R1 的 K2 实测证伪，此处已改写）」。✓
- **K3**（死锁措辞降级）→ `design.md:134-139`「响亮、可恢复的分叉态」+ 三条恢复路径。✓
- **K4** → `design.md:166-183`（D4 三条）。✓
- **K5** → `design.md:265-267`（计数口径 + 去掉具体数字）。✓
- **K6** → `design.md:218` 列出 `docs/design.md:56,73`；实查 `docs/design.md:56` 与 `:73` 都已写入 cross-ref（`@v1 那段的 ref 就是包版本——change gate-ref-pins-package 起…`）。✓
- **K7** → `design.md:140-144` + `D6`（`design.md:189-191`）。✓
- **K8** → `design.md:94-96` + `tasks.md:41-46`。✓
- **L1** → `tasks.md:79-84`（先改常量 → 再 tag）。✓
- **L2** → `docs/gate.md:82-110`（两步 + 旧 CLI 症状）、`README.md:188-200`（`:192` 的「升级**两步，顺序不能反**」+ `:198-200` 的误导文案警告）。✓
- **L3** → `tests/test_gate_workflow.py:466`（`test_witnessloop_ref_input_default_is_empty`）。✓
- **L4** → `spec.md:132-138`（组合语义 Scenario）+ `initcmd.py:358-362`（`handled` 两面）+ `tests/test_init_gate_ref.py:235`。✓
- **L5** → `spec.md:115-130`（dry-run / 台账缺条目两条 Scenario）。✓
- **L6** → `design.md:226`（§4 R2 两类仓）、`docs/gate.md:152-155`、`tasks.md:136-140`。实查 docs/gate.md 明写 ①/② 两类。✓
- **M1** → `tests/test_init_gate_ref.py:28`（`NEW_REF=…@v9.9.9`）+ `:46`（撞值前提的钉子）+ `tasks.md:98-101`。✓
- **M2** → `docs/gate.md §3` + `tasks.md:71-77`。✓
- **M3** → `tasks.md:117-122`（只许证据文件落在 `head_sha` 之后）+ `docs/gate.md:223-232`（§3 的 revision 绑定，「本 PR 自己的变更**并不豁免**」）。✓
- **M4** → `docs/gate.md:90-100`（①′ 自证命令 + 「有没有这一行」的判据）、`README.md:202-204`。✓
- **N1** → `tests/test_init_gate_ref.py:299`（`test_ledger_without_a_caller_entry_is_repaired`）。✓
- **N2** → `initcmd.py:341-342` 不再自称「其余文件无改动」+ `tests/test_init_gate_ref.py:75`。✓
- **N3** → `tests/test_gate_workflow.py:349` 一族用 `_fallback_ref()` 而非字面量；`design.md:230`、`docs/gate.md §7.1`、`tasks.md:102-109`。**实跑复核**：`grep -rn '"v1"\|@v1\b' src/ tests/ .github/` 的活面命中都带「今天 = v1 / 兜底 ref」语境，无「固定落点」写法。✓
- **P1** → `initcmd.py:170-176`（先判、不是数组就**不写**）+ `:238`（不再兜）+ `:451-462`（受控诊断退 1）+ `tests/test_init_gate_ref.py:333`。**实跑复核**：把台账 `created_files` 改成 dict ⇒ `init --gate-ref` **EXIT=1**、caller 与台账**逐字节未动**。✓
- **T1** → `tests/test_gate_workflow.py:532`（`test_the_install_step_consumes_the_resolved_ref`，钉 `steps.wl-ref.outputs.ref` + run 里不得再出现 `inputs.witnessloop-ref`）。✓
- **U1–U4** → `tests/test_gate_workflow.py:552`（来源四类文案）、`:576`（兜底真读 env，哨兵值）、`tests/test_check_package_ref.py:154`（两值绑定）、`:170`（自报行是 `check` 第一行）。✓
- **V1** → `initcmd.py:193-230`（`caller_retarget_refusal`）+ `tests/test_init_gate_ref.py:379`。**实跑复核**：`--gate-ref X` 在该态 ⇒ EXIT=1 + 「无法按 --gate-ref 改 caller：…既不在盘上、…也没有它的条目」、台账逐字节未动、文件未复活。✓
- **V2** → `docs/gate.md:132-146`、`README.md:209-211`、`spec.md:94-98` 三处都有「不变集 ⇒ `M` 需 `protected_path_write`」+「别新建只有事件文件的 change 目录（1 条红变 7 条红）」。✓
- **V3/V4** → `tests/test_gate_workflow.py:552` 的 `fallback` 分支断言 + `tests/test_init_gate_ref.py:216`（`assert "幂等" not in out`）。✓
- **W1** → `spec.md:128-130` + `initcmd.py:161-162`（措辞都改成「真正把它变响亮的是 `caller_retarget_refusal`」）。✓
- **W2** → `spec.md:100-108`（前提 + 定制 policy 的仓不满足 Then）+ `docs/gate.md:112-123`。**实跑复核**（见下 §3(d)）。✓
- **W3** → `initcmd.py:213-218`（`not entry.get("self")`）+ `tests/test_init_gate_ref.py:408`。✓
- **W4** → `tasks.md:128-134`（按语义找 + `grep -n "@v1" README.md docs/gate.md`）。✓
- **X1** → `docs/gate.md:112-123`（定制 policy 的仓也撞同一条冲突、`uninit` 不可照做、正确做法是同时带 `--policy`、限定作用范围）。**实跑复核**（见下 §3(d)）。✓
- **O1** → `initcmd.py:316-324`（refusal 在 `manifest_path.is_file()` 块的**最前面**）+ `tests/test_init_gate_ref.py:433`。**实跑复核**：`--gate-ref X --test-command "pytest -q"` 在拒绝态下 EXIT=1，`.github/` 下**没有**新测试文件、台账里 `tests` 零命中。✓
- **O3** → `spec.md:108`（`uninit` 危害枚举含 `policy.json`）；`docs/gate.md:117-119` 同。✓

⇒ **判据②满足**：前十轮（含 R10）的全部必须修改项都已落库，没有找到 X1 那样的「处置自称已落库、落地提交却不含该文件」。

（**我核的边界，如实说明**：我核的是「落点文件在该提交的 `--stat` 里」+「该文本/钉子在本轮 HEAD 上存在」+「行为类断言我**真跑**过」，**不是**把前十轮的每个变异都重跑一遍。所以「已落库」是**强证据**，不等于我复核了每一条变异当初是否真的变红。）

### 2. 判据①：题面点名的四条攻击面 —— 三条实测不通，一条**不通但在旁边挖出 Y1**

**(a) `caller_retarget_refusal` 与 `sync_caller_gate_ref` 两次读台账之间的一致性。**
两个函数各自 `json.loads` 台账一次；在 `initcmd.run` 里它们之间只夹着**测试文件写入**（`write_tests_file`，不碰台账）⇒ **单进程内两次读必同值**。我逐态推演并抽测了四个返回点，**互不矛盾**：①坏 JSON ⇒ 两者都 `None`，由 `_already_initialized` 报「无法解析」退 1（实测，`tests/test_init_gate_ref.py:362`）；②台账 `gate_ref` 已等于请求值 ⇒ 两者都 `None`，判「无事可做」；③`created_files` 非数组 ⇒ 两者都 `None`，由 `_already_initialized` 报「结构非法」退 1（实测）；④`path.is_file()` 为假 ⇒ refusal 只在「连条目都没有」时为真（真做不成）、有条目时为 `None` 而交给漂移分支响亮地报（实测 `tests/test_init_gate_ref.py:162` 的 EXIT=1 + 「缺失」）。**结论：无新缺陷**。

**(b) `--dry-run` 下的拒绝是否恰当 → 恰当。**
实跑：拒绝态 + `--dry-run --gate-ref X` ⇒ EXIT=1、同一句文案。这是**如实预告**（真跑也是 EXIT=1），不是谎报。**但同一片面上另有真问题 ⇒ Y1。**

**(c) `init --gate-ref` 在未接入仓上的路径 → 正确。**
实跑：新仓（无台账）+ `--gate-ref NEW` ⇒ caller 里 `uses: <NEW>`、台账 `gate_ref=NEW`、EXIT=0；新仓**已有**内容不同的 caller ⇒ EXIT=1、`冲突`、外来文件逐字保留、台账与 policy **都没被创建**（`tests/test_init_gate_ref.py:175`、`:193`）。作用域守卫没被推翻。

**(d) `docs/gate.md §1.2` 新增那段（含「同时给 `--policy` 两条轴就都不冲突」）→ 实跑**证真**。**
在 `/tmp/adv11/lab/cust`（用一份与出厂不同的 policy seed 接入）逐步实跑：

```
step1  init --policy seed                                  EXIT=0
step2  plain init                                          EXIT=1   ← 定制 policy 轴（既有行为）
step3  init --gate-ref <NEW>                               EXIT=1
       stderr：init：注意——.github/workflows/witnessloop.yml 已按显式 `--gate-ref` 处理（**已落盘、不回滚**）；下面报的是**别的**文件：
       stderr：init：检测到冲突（…要更换 policy 请先 `uninit`）…diff 只涉及 .witnessloop/policy.json
       stdout：init：已重写 …/witnessloop.yml（→ …@v9.9.9）并同步台账
       ⇒ 台账 gate_ref 与 caller 的 uses 行**都**已改成新 ref（先写、不回滚 ✓）
step4  plain init                                          EXIT=1   ← 随后**不**报幂等 ✓（§1.2 那句限定成立）
step5  init --gate-ref <NEW> --policy seed                  EXIT=0   输出「已接入 witnessloop（幂等，无改动）。」
```

⇒ `docs/gate.md:112-123` 的两条断言（「定制 policy 的仓也会退 1 且随后 plain init 不幂等」「同时带上 policy 两条轴就都不冲突」）**都成立**；`spec.md:100-108` 的前提与 `docs/gate.md:122` 的限定句与之**一致**。另外实跑确认 `uninit` 的后果描述也对（在本区另一仓上 `uninit` 把 `policy.json` + caller + 台账**一起**删掉）。

**(e) 三份文档对同一件事的说法是否仍一致 → 一致。**
V2 那件事（升级 PR 会被自己的门禁拦一次）在 `README.md:209-211` / `docs/gate.md:132-146` / `spec.md:94-98` 三处的实质（不变集 `M` ⇒ 要 `protected_path_write`、写进**既有** change 目录、新建只有事件文件的目录会 1 红变 7 红）**逐条对齐**；升级 recipe 的「两步、顺序不能反」在 `README.md:188-199` 与 `docs/gate.md:82-88` 一致，`spec.md` 只写工具那一半（不矛盾）。

**(f) 12 个 Scenario 是否逐个有行为级钉子 → 是（我逐个点了对应测试名）。**
:26↔`test_resolve_prefers_the_reusable_workflows_own_sha`/`test_the_install_step_consumes_the_resolved_ref`；:32↔`test_resolve_lets_an_explicit_with_override_win`；:37↔`test_resolve_fails_closed_on_malformed_workflow_refs` + `…_on_a_foreign_repository`；:54↔`test_resolve_notice_names_the_source_of_the_ref`；:74↔`test_parses_the_real_payload`；:79↔`test_absent_or_unusable_metadata_is_not_an_error`；:100↔`test_explicit_different_ref_rewrites_caller_and_syncs_the_ledger` + `test_plain_init_is_idempotent_after_the_rewrite` + `test_uninit_still_works_after_the_rewrite`；:110↔`test_same_ref_is_a_noop`；:115↔`test_dry_run_previews_without_writing`；:122↔`test_ledger_without_a_caller_entry_is_repaired` + `test_no_caller_entry_and_no_file_refuses_loudly`；:132↔`test_explicit_gate_ref_plus_conflicting_policy_writes_then_reports`；:147↔`test_gate_documents_the_unprotected_caller_boundary`。**⇒ 没有「缺一条钉子」类的新项。**

### 3. 本轮**新证伪** 2 条（都是**行为缺陷**，不属措辞/计数/格式）

见「必须修改项」的 Y1、Y2。两条都有可复算反例。

### 4. 低危观察（**登记、不列为必须修改项**）

- **O-a（先于本 change）**：台账「无 caller 条目 **且** 盘上无文件 **且** 台账 `gate_ref` **已等于**请求值」时，`init --gate-ref <同一个值>` 仍打「幂等，无改动」EXIT=0（V1 的 refusal 只在「要改成**别的**值」时为真）。实跑复现。判为先于本 change：同一状态下 plain `init`（不给 flag）行为相同，而「caller 缺失对 `init` 不可见」是既有判定面，不是本 change 引入的。
- **O-b（计数/清单类，不算证伪）**：`tasks.md:72` 的报告清单只举到 `-r3`（现已有 r2–r10 与本份）；`tasks.md:88-89` 的「改之前是 `5 failed`」在当前树上实测是 **`1 failed`**（我模拟 6.1 的改动实测，见下）。两处都是**测量时点**的数，不是行为问题。
  - **6.1 的实质断言我复算了**：只改 ①`constants.DEFAULT_GATE_REF` + ②`gate.yml` 的 `WL_FALLBACK_REF` ⇒ `1 failed, 688 passed`（失败项正是 `test_caller_ref_matches_this_repo`）；补上 ③该断言 ⇒ **`689 passed`**。⇒ 「字面量族 = 这三处 + 一条 `NEW_REF` 前提」这一族**是完整的**。
- **O-c（排版）**：`design.md §7.9` 的小节顺序是 R1→R2→R3→R4→R5→**R10**→R9→R8→R7→R6（R10 插在 R5 之后、其余降序）。
- **O-d（已登记不修，复核登记**准确**）**：`…@refs/heads/` 空后缀仍会产出空 ref（脚本的 `case` 在 `gate.yml:87-96`，`*@refs/heads/*` 分支在 `:88-89`，`REF="${WL_WORKFLOW_REF##*@refs/heads/}"` 在空后缀下得到空串且**不**置 `FAILED` ⇒ 会打出 `ref=` + notice）——上游不可能给出这个形态，不可达，登记无误。
- **O-e（已登记不修，复核「先于本 change」**成立**）**：`created_files` 的元素**非对象**仍会崩——`initcmd.py:467` 的 `entry.get("path")` 与 `:475` 的 `path.read_bytes()` 在旧版（`git show 32c819a:src/witnessloop/initcmd.py` 的同一循环）**逐字相同** ⇒ 确系既有面。

## 未验证项

以下面**本工作区不可验证**，一律不作必须修改项（也未发现被文档写成「已验证」的）：

1. 真 CI 的 `job.*` 上下文语义（`job.workflow_sha` / `workflow_repository` / `workflow_ref`）与 `>=` 行为 —— 无 GitHub CI 可跑。
2. `design.md §2 D1` 的跨仓探针原始输出（run `38853369550`）：**单一来源、不可复现**的二手文本（分支已删）。文档自己已在 `design.md:97-104` 标注了证据等级，`spec.md:6` 也指向它 —— 属**如实标注**，不算把它写成已验证。
3. GHES / 同 owner fork 面、「`pip install git+…` / `uvx --from` 在真 CI 可否安装」。
4. `v1.7.0` 尚不存在 ⇒ `tasks.md §6` 的 6.2–6.7 只能在发布后验（本轮只模拟了 6.1 的字面量族，见 O-b）。
5. issue #30 的数字（如「落后 47 / 50 个提交」）—— 未复算，且正文已改成不依赖计数。
6. `refs/pull/N/merge` 在 `uv` 侧的行为（`spec.md:42-43` 只做定性、明确说未实测 —— 与文档一致）。
7. 「旧包（`@v1` = v1.6.0）跑 `check` 没有自报行」这条 —— 本工作区里只有当前源码版（`<未知>`），拿不到旧包。
8. `tasks.md 4.3`（本仓自举 `check` 判绿）与归档面 —— 属 post-merge / 收尾，未跑。
9. 本轮**没有**重跑前十轮的每一个变异（只核落点与钉子是否存在 + 行为面真跑），见「判据②」节末的边界说明。

## 必须修改项

### Y1（**行为缺陷**，中低危）：`--dry-run --gate-ref` 与**真跑**对同一状态给出相反结论 —— dry-run 会为一个「它正要修掉」的漂移报红并退 1

- **状态**：已接入的仓 + caller 被手改过（磁盘 ≠ 台账）。**这一态是本 change 明确要接管的**（`tests/test_init_gate_ref.py:123` 的 `test_rewrite_rescues_a_hand_edited_caller` 就是「K3 的分叉态要能被这个动作救回来」）。
- **复算（`/tmp/adv11/lab/dr`，同一棵树、同一状态）**：

  ```
  # 真跑
  $ python3 -m witnessloop init --root . --gate-ref X@v9.9.9
  init：已重写 .github/workflows/witnessloop.yml（→ X@v9.9.9）并同步台账
  init：已接入 witnessloop（.github/workflows/witnessloop.yml 与台账已改成 X@v9.9.9）。
  EXIT=0

  # 同状态的 dry-run
  $ python3 -m witnessloop init --root . --dry-run --gate-ref X@v9.9.9
  EXIT=1
  stdout: init：[dry-run] 将重写 .github/workflows/witnessloop.yml（→ X@v9.9.9）并同步台账
  stderr: init：已接入，但 init 创建的文件被改动过（拒绝覆盖）：
          --- a/.github/workflows/witnessloop.yml（当前）
          +++ b/.github/workflows/witnessloop.yml（witnessloop init 将写入）
          @@ -1 +1,14 @@
          -name: tampered
  ```
- **新引入性（已对照改动前复核）**：在改动前的树上（`git archive 32c819a`）同一状态下 **dry-run 与真跑都退 1**（两边一致）；改动后真跑退 0、dry-run 仍退 1 ⇒ **分叉是本 change 引入的**。
- **机制**：`initcmd.py:517` 的 `ignore` **只**过滤「本次期望 vs 已落地」那条判定，**不**过滤 `initcmd.py:464-505` 的漂移循环；dry-run 下 `sync_caller_gate_ref` 不落盘 ⇒ 漂移仍在；真跑下它把 caller 与台账一起改掉 ⇒ 漂移消失。既有钉子只覆盖了 pristine 仓（`tests/test_init_gate_ref.py:222`）。
- **为什么不接受**：`spec.md:115-120` 的 dry-run Scenario 的**理由**（「那条冲突正是这个动作要消掉的」⇒ 不报它）对漂移**同样成立**（那是同一个动作要消掉的另一条红）；且 `--dry-run` 的既定含义是「只预览」，此处却给出与真跑相反的结论。
- **修法**（任选，都是小面）：①把 caller 那条轴在**已按显式意图处理**时对漂移判定也排除（与 `ignore` 同口径，但仍**不得**放过非 caller 的漂移）；或 ②保持退 1，但在文案里点明「该漂移正是本次 `--gate-ref` 会一并修掉的」。补一条钉子：在**手改 caller** 的状态下断言 dry-run 的退出码与真跑一致。

### Y2（**行为缺陷**，低危 —— 需手工改台账才能达到）：caller 条目被标 `self: true`（文件在盘上）时，`init --gate-ref` 写出**重复条目**，并让随后的 `uninit` 半回滚 + 报「内部错误」

- **复算（`/tmp/adv11/lab/selfdup2`）**：接入后把台账里 caller 那条改成 `"self": true`，然后

  ```
  $ python3 -m witnessloop init --root . --gate-ref X@v9.9.9      # EXIT=0
  台账 created_files：[('.witnessloop/policy.json', None),
                      ('.github/workflows/witnessloop.yml', None),   ← 新增的重复条目
                      ('.github/workflows/witnessloop.yml', True),   ← 手工标 self 的那条
                      ('.witnessloop/init-manifest.json', True)]

  $ python3 -m witnessloop uninit --root .
  witnessloop：内部错误（FileNotFoundError: [Errno 2] No such file or directory: '…/.github/workflows/witnessloop.yml')   ← stderr
  uninit：已回滚 witnessloop 接入：                                        ← stdout 同时说了成功
    - .witnessloop/policy.json
    - .github/workflows/witnessloop.yml
  EXIT=1
  ⇒ .witnessloop/init-manifest.json **留在盘上**（半回滚）
  ```
- **机制**：`_set_ledger_gate_ref`（`initcmd.py:241-254`）的匹配用 `not entry.get("self")`（与另两处同口径）⇒ 手工标 self 的那条**不**被认作 caller 条目，于是走 `else` 分支（`:249-254`）**再插一条**，台账里同一路径出现两次；`uninitcmd.py:53-55` 把 `self` 条目也 `doomed.append(path)`（**不去重**），`uninitcmd.py:91-95` 逐条 `unlink()` ⇒ 第二次 `unlink` 抛 `FileNotFoundError`，冒到进程入口成「内部错误」，而「已回滚」已提前打印（`:91`）⇒ 与 `uninitcmd` 自称的「避免留下半删状态」相反。
- **新引入性**：`_set_ledger_gate_ref` 是本 change 新增（`5cc56b4`），改动前的 `init` 从不改既有台账 ⇒ 「台账里出现重复条目」这一态**此前不可达**，`uninit` 那处不去重的缺陷因此才被激活。
- **为什么不接受**：R9 的 W3 已经把「手工把 caller 条目标成 `self: true`」**确立为本 change 要守的威胁模型**（并为此补了 `not entry.get("self")` 守卫 + 钉子 `tests/test_init_gate_ref.py:408`）——同一个状态在「文件不在」那一半守住了（响亮拒绝），在「文件在」这一半却**写坏台账 + 写死 `uninit`**。修法：让 `_set_ledger_gate_ref` 把 self 标记的 caller 条目**也**认作同一条（更新而非新插），或在该态 fail-closed 拒绝（与 V1 同向）。

## Open Questions

- **Q-A**：`--dry-run --gate-ref` 在**漂移态**下应当 (i) 与真跑一致退 0（把 caller 那条漂移也视作「本动作会消掉」），还是 (ii) 保持退 1 但文案改成「这条漂移将被本次动作一并修掉」？现状是第三种（退 1 且不说明会被修掉）。**倾向 (i)**，理由是 `spec.md:115-120` 对「冲突」给出的理由对「漂移」同构。（Y1）
- **Q-B**：`self: true` 标在 caller 条目上时，`_set_ledger_gate_ref` 应当 (i) 视为同一性匹配（就地更新）还是 (ii) 与 V1 一样响亮拒绝？**倾向 (ii)**（与 R9 W3 的口径一致：这一态是「台账被手工改坏了」，工具不该替用户猜）。（Y2）
- **Q-C**（登记，不阻塞）：`design.md §7.9` 的小节要不要按轮次升序排（现为 R1–R5、R10、R9、R8、R7、R6）？

## 收敛结论

**不收敛。**

- **判据②（前十轮的「必须修改项」是否全部已落库）⇒ 满足。**
  我对 K1–K8 / L1–L6 / M1–M4 / N1–N3 / P1 / T1 / U1–U4 / V1–V4 / W1–W4 / X1 / O1 / O3 逐条核了两段：**落地提交的 `git show --stat` 是否含自称的落点文件** + **该文本/钉子在本轮 HEAD（`ba03ec8`）上是否真的存在**（行为类另**真跑**过：P1 / V1 / O1 / W2+X1 / dry-run 面 / §6.1 的字面量族）。**没有发现第二例 X1 式「处置自称已落库、落地提交却不含该文件」。**
- **判据①（本轮是否没有新的可证伪项）⇒ 不满足。**
  **新证伪 2 条，类别都是「行为缺陷」（非措辞 / 非计数 / 非格式）**：
  - **Y1**：`--dry-run --gate-ref` 在「caller 被手改」状态下退 1，而真跑退 0 —— 预览与真跑结论相反（改动前两者一致 ⇒ 本 change 引入）；机制在 `initcmd.py:517` 的 `ignore` 不覆盖 `:464-505` 的漂移循环。
  - **Y2**：caller 条目被标 `self: true`（文件在盘上）时，`init --gate-ref` 写出重复条目并让 `uninit` 半回滚 + 报「内部错误」（改动前该态不可达）；与 R9 W3 已确立的威胁模型同一状态、只有一半被守住。
  - **没有「缺一条钉子」类的新项**：12 个 Scenario 仍逐个有行为级钉子（我逐个点了测试名，见 §2(f)）。
  - **另**：未发现任何「本工作区不可验证的面」被文档写成了已验证（`design.md:97-104` 与 `spec.md:42-43` 反而**主动**标注了证据等级与未实测项）——故这些只进「未验证项」，不构成必须修改项。
- **⇒ 两条判据都要满足才收敛**，判据①不满足 ⇒ **不收敛**。Y1/Y2 修完（并各补一条钉子）后可再审。

---

## 处置（主 session 在 R11 之后追加，非审阅者原文）

> 本报告判定**不收敛**（判据②满足、①不满足），基准 `ba03ec8`。**Y1、Y2 已落库**，
> 两条都用「在**未含修复**的树上跑新钉子 ⇒ 红」复核过。你这两条是本 change 里
> **最后一批行为缺陷**，而且都能追到本 change 自己新写的代码上（Y1 是 `ignore` 的作用面漏了一条判定、
> Y2 是 `_set_ledger_gate_ref` 的匹配口径与拒绝面不齐），价值很高。

- **Y1**：`ignore` 现在**同时**作用于「本次期望 vs 已落地」与「磁盘 vs 台账」两条判定，
  且**只**由「确实会重写 caller」的调用点传入（文件缺失 / 台账坏 / 结构非法 / caller 那条被标 `self`
  都**不**传——那些要么响亮拒绝、要么交给漂移判定报）。`_already_initialized` 的 docstring 同步改写。
- **Y2**：`caller_retarget_refusal` 现在**先**查「caller 那条有没有被标 `self`」——
  有就拒绝（不论文件在不在），并说明为什么（`self` 是自指条目的专用标记、更新会插重复条目、
  删的时候会半回滚）。W3 的那条钉子按新文案改了断言（它原来断言的「条目」二字已不在文案里）。
- **低危项**：`tasks.md` 的报告清单/陈旧计数已改成「按语义数 / 按语义找」；
  `design §7.9` 的小节顺序已按 R1→R11 重排（你说得对，那是逐次插入造成的）。

**R12**：树在该 revision 上冻结。你已确认「无『缺一条钉子』类新项、12 个 Scenario 全有钉子」——
若下一轮确认 Y1/Y2 落库且无新项，**请如实判「已收敛」**。
