# 对抗轮 R9（独立零记忆验证者）

## Reviewer

- **冻结版本**：`git rev-parse HEAD` ⇒ `38650077b844ce0f9f1019160c34b65727f53fda`
  （worktree `/home/happy/wl-wt/archive-arrival-recognition`，分支 `gate-ref-pins-package/2026-10-16`）。
- **关键文件 blob（`git hash-object`）**：

  | 文件 | blob |
  |---|---|
  | `openspec/changes/gate-ref-pins-package/design.md` | `3f6b719964b4e6808dd03fc8cd214010896bba86` |
  | `…/tasks.md` | `19effc8913a94e74096067c7081b15e201208f61` |
  | `…/specs/gate-ref-pinning/spec.md` | `80333905be57566742bdfe3bd990f600986fbf29` |
  | `src/witnessloop/initcmd.py` | `3c8f2b37fb024e884127a8378b04b2785c6317fb` |
  | `src/witnessloop/checkcmd.py` | `e12db4d94a1d11daebc80eb1423298de57bf487a` |
  | `src/witnessloop/constants.py` | `0a64184d5435399646646356fac56dd68622ffb0` |
  | `.github/workflows/gate.yml` | `330104b810db66a7c382c89ec075a04cfb03798c` |
  | `docs/gate.md` | `fde483098e6af873f01922f8cea4075ad024ebf7` |
  | `README.md` | `3bd4dc951af8c99ca5bc8899b1b370ce1edac339` |

- **手法**：`git archive HEAD | tar -x -C /tmp/adv9/r9` 快照到仓外，一切实验只在 `/tmp/adv9/r9/` 里跑；
  真仓内**未** commit / reset / tag / push，除本文件外**未**写任何文件。
- **基线（本轮重跑）**：`PYTHONPATH=src python3 -m pytest -q` ⇒ **687 passed in 34.00s**。
- **不重跑**：R1–R8 已做过的 45+ 条「变异 → 全量套件」实验；不碰任务书列为「已定稿/刻意不修」的旧项
  （recipe 两步顺序、`design §2 D1` 排序、install 步吃不吃的正面项、三条台账分支、四段 notice 来源文案、
  兜底 ref 真读 env、自报两值绑定、自报是 `check` 第一行、V1 响亮拒绝、V2 的文档面文案）。
- **判据② 的核对方式**：逐条读 `spec.md`/`tasks.md`/`design.md` **正文**与 `src/`、`.github/`、`tests/` 的
  **代码**；**不采信** `design.md §7.9` 的自报表。

## 对抗结论

**总判：本轮**未**在 `src/` 与 `.github/workflows/gate.yml` 的行为层找到新缺陷；新证伪集中在
「规格/文档面」与「一条判据不一致（钉子级）」。因此按判据①的口径，本轮**仍不收敛**（见末节）。**

### 1. 判据②（历轮必须修改项是否真落地）——**逐条核过，全部落地**

按 `design.md §7.9` 的条目名为索引，逐条在**正文与代码**里找落点（不读自报表）：

| 组 | 落点（正文/代码/测试） | 结论 |
|---|---|---|
| K1（包**能**自报 ref） | `spec.md:60-72`（Requirement + 两个 Scenario）；`checkcmd.py` 的 `vcs_info_from_direct_url` / `installed_vcs_ref` / `_report_package_source` | ✅ 落地 |
| K2（「没有任何提示」是假的） | `proposal.md` 机制段 | ✅ 落地 |
| K3（「永久死锁」过强） | `design §2 D2` 三条恢复路径 + 措辞已降级 | ✅ 落地 |
| K4（自证条件） | `design §2 D4`：本 PR 不做本仓迁移（与 `tasks.md:55-59` 的 3.5 `(post-merge)` 一致） | ✅ 落地 |
| K5（47 这个计数口径） | `design.md:265` 复算订正 + 本轮复算：`git rev-list --count v1..origin/main` = 47、`v1..main` = 0（在本仓上重跑一致） | ✅ 落地 |
| K6（同源文档清单漏 `docs/design.md`） | `design §3` 接线点 5 | ✅ 落地 |
| K7（第四条升级路径登记） | `design §2 D2` 末条 + `§D6`（明确不收紧） | ✅ 落地 |
| K8（探针结果落点） | `design §2 D1` 写明落点；`tasks.md:41-46` 3.0；本轮复核本地分支 `probe/workflow-ref` = `c7aa0378b9c602f98e967ddcd14d437e256adcd2`（与 `tasks.md:46` 记的 `c7aa037` 一致） | ✅ 落地 |
| L1（post-merge 时序） | `tasks.md:79-84` 的承重告示 + 6.1（先改常量）→ 6.2（再 tag）+ 6.7 的 `git show v1.7.0:…constants.py` 自查 | ✅ 落地 |
| L2（旧 CLI 上 `--gate-ref` 不存在 ⇒ 两步） | `docs/gate.md §1.2`（两步 + 旧 CLI 症状）+ `README.md:188-218` | ✅ 落地 |
| L3（`inputs.witnessloop-ref.default == ""` 缺钉） | `tests/test_gate_workflow.py::test_witnessloop_ref_input_default_is_empty` | ✅ 落地 |
| L4（`--gate-ref` + 冲突 `--policy` 的组合语义） | `spec.md:125-131` 的 Scenario + `initcmd.py:516-521` 的 `handled` 先声明 | ✅ 落地 |
| L5（spec 缺两条 Scenario） | `spec.md:111-116`（dry-run）、`spec.md:118-123`（台账缺条目） | ✅ 落地 |
| L6（全局面说小了一类） | `design §4 R2`、`docs/gate.md:139-143`、`tasks.md:131-135` 三处点名两类仓 | ✅ 落地 |
| M1（字面量族 + `NEW_REF` 撞值） | `tasks.md:86-101` 四处清单；本轮照 6.1 的三处改动模拟 ⇒ **全绿**（注意其「⇒ `673 passed`」已陈旧，见 O3） | ✅ 落地 |
| M2（孤儿报告 / 同 stage 静默覆盖） | `docs/gate.md §3` + `tasks.md:70-77`（5.2）、`tasks.md:16-19`（0.4） | ✅ 落地 |
| M3（revision 绑定的正确顺序） | `tasks.md:117-122` | ✅ 落地 |
| M4（「先升 CLI」无法自证 ⇒ ①′） | `docs/gate.md §1.2` 与 `README.md:204-207` 的 ①′（本轮复核：①′ 打印的正是 `check` 的**第一行**、`flush=True`，且 `check` 在该态退出码非 0，`2>/dev/null \| head -1` 拿得到） | ✅ 落地 |
| N1（补条目分支零覆盖） | `tests/test_init_gate_ref.py::test_ledger_without_a_caller_entry_is_repaired`（补条目 + `sha256` + 插在 `self` 之前 + 随后幂等 + `uninit` 可回滚） | ✅ 落地 |
| N2（收尾话自相矛盾） | `initcmd.py` 的 `note` 不再自称「其余文件无改动」 | ✅ 落地 |
| N3（自查面 + 用「已知会漏的形态」验 grep） | 三处已改；`tasks.md:102-113` 把自查面扩到 `src/`+`tests/`(含 docstring)+`docs/`+`README.md`+`.github/` 并**补上 `openspec/`**（`tasks.md:107-109`） | ✅ 落地 |
| V1（静默 no-op） | `initcmd.caller_retarget_refusal`（`initcmd.py:191-221`）+ `tests/test_init_gate_ref.py:379-405`；本轮实跑对照：**有条目 + 文件缺失** ⇒ 漂移分支响亮报（`initcmd.py:489`）退 1、台账不动 | ✅ 落地（但其「唯一一种」提法被证伪，见 **W3**） |
| V2（升级即红 / 1 红 → 7 红） | `docs/gate.md:117-131`；本轮复核「红从 1 条变 7 条」的机制（新建「只有事件文件」的 change 目录 ⇒ 触发 change 目录契约） | ✅ 落地 |
| V3（notice 四类来源） | `tests/test_gate_workflow.py::test_resolve_notice_names_the_source_of_the_ref`；本轮实跑解析矩阵：四类来源文案**各自**出现（`job.workflow_sha` / `job.workflow_ref 的分支名` / `job.workflow_ref 的 tag 名` / `fail-closed`） | ✅ 落地 |
| V4（dry-run 轴上「不许谎报幂等」缺钉） | `tests/test_init_gate_ref.py::test_dry_run_previews_without_writing` 的 `assert "幂等" not in out` | ✅ 落地 |
| U1–U4（notice 来源文案 / 硬编兜底 / 自报两值对调 / 自报行插行） | `tests/test_gate_workflow.py` 的 `_fallback_ref()` 从 YAML 读 + 三条钉（比字面量、比行为、比脚本有没有读）；`tests/test_check_self_report.py` 的 U3/U4 两条 | ✅ 落地 |
| T1（install 步吃不吃解析输出） | `tests/test_gate_workflow.py::test_the_install_step_consumes_the_resolved_ref`；本轮复核 `gate.yml` 的 install 步确实用 `${{ steps.wl-ref.outputs.ref }}` | ✅ 落地 |
| P1（`created_files` 非数组的静默破坏分支） | `initcmd.py:440-450`（`_already_initialized` 的守卫）+ `initcmd.py:178-183`（`sync_caller_gate_ref` 一律拒绝重写）；本轮实跑「非数组」与「键缺失」两态 ⇒ 均受控退 1、台账**未**被重建 | ✅ 落地 |

### 2. 判据①（本轮新证伪）

**行为层（`src/`、`gate.yml`）：0 条。** 我把任务书点的几个新面都过了一遍，结论如下：

- `caller_retarget_refusal()` ⇄ `sync_caller_gate_ref()` 的缝（两次读台账、`--dry-run`）：**有缝**，但缝在
  「`self` 标记」这个第三处判据上 ⇒ **W3**（行为可达性低）。
- 未接入仓里 `init --gate-ref` 撞上「新仓已有别人的 caller」：仍是**整体不落盘 + 判冲突**（`spec.md:90-91`
  保留的旧语义），本轮按代码与既有用例核对，**未见**新缝。
- `check` 自报 vs `guard` / `manifest build`：只有 `check` 打自报行（`checkcmd.run` 第一句），
  `guard` / `manifest build` 都不打 —— 与 `docs/gate.md §8` 的措辞一致，**无问题**。
- `docs/gate.md §1.2` 的 ①′ recipe（`2>/dev/null | head -1` + 非零退出码）：**成立**（见 M4 行）。
- `spec.md` 每个 Scenario 的行为级钉子：**逐个点过**。「台账里没有 caller 条目」有钉子，但其 **Then 的
  括号句机制归属写错** ⇒ **W1**；「显式换 ref 之后仍是干净的不动点」有钉子（出厂 policy 形态），
  但对**定制 policy 的仓**被实跑证伪 ⇒ **W2**（本轮最强的一条）。
- `tasks.md §6` vs `design.md §2 D4`（本仓自身迁移）：两处一致（都是 post-merge、手工改 caller+台账+事件），
  **未见**新缝；`tasks.md §5.2` 的「归档前先补 manifest」与本 change「先不归档」的措辞也自洽。

**新证伪（4 条，全部列为必须修改项）**：

| 编号 | 面 | 性质 |
|---|---|---|
| **W1** | `spec.md:118-123` 的 Then 括号句「交给漂移判定响亮地报」 | 规格面**机制归属错**（那一态漂移判定看不见）+ 同款错在 `initcmd.py:161-163` 的 docstring |
| **W2** | `spec.md:100-104` 的 Then（EXIT=0 / 随后幂等）在**定制 policy 的已接入仓**上被实跑证伪 | 规格+文档面（**有具体失败场景**：本仓自己就是这一类） |
| **W3** | `caller_retarget_refusal` 的判据缺 `not entry.get("self")` ⇒ V1 的静默 no-op 原样复现 | 行为面（可达性低：需手改台账）——属**钉子级** |
| **W4** | `tasks.md:128-129`（6.3）只点名 `README.md:20`，而 `README.md:189`、`README.md:206` 的 `@v1` 句子在 6.2 之后变成**错建议** | 文档面钉子级（与它自己 N3 的教训冲突） |

**低危观察 4 条（O1–O4，**不**列为必须修改项，供裁决）**：见「Open Questions」第 3–6 条
（元素非对象的台账崩、`refs/heads/` 空后缀、`--gate-ref ""`、`673 passed` 陈旧计数）。

**少数派意见**：W1 与 W4 单独看都够不上「行为缺陷」；把它们列进必须修改项是因为它们写的是**会被下一个人
当成事实照做**的句子（一个是「谁负责报」、一个是「发布后该钉哪个 ref」），而不是因为措辞不好看。

## 未验证项

（一律只作登记；**本报告未把其中任何一条写成已核实**。）

1. **真 CI 的 `job.*` 取值**：跨仓探针 run `38853369550` 的输出是**二手物证**——本地只能看到
   `design.md §2 D1` 的誊录与 `tasks.md:41-46` 的叙述；探针的分支/文件远端已 404，
   **本地分支 `probe/workflow-ref`（`c7aa0378…`）本轮只核了它存在，没重跑探针**。
   本 worktree 内**无法**再产生一次真 CI。
2. **GHES / 同 owner 的 fork**：`job.*` 不可用与「fork 也能匹配 `REPO_SLUG`」两条都是文档定性
   （`spec.md:21-24`），本环境无法构造。
3. **`refs/pull/N/merge` 在 uv 侧的行为**：`spec.md:42-43` 只做定性并**自称未实测**——与本轮实测一致
   （解析器把它 fail-closed 到 `v1` + warning，见实跑），**uv 会不会装得成仍未测**。
4. **`pip install git+…` / `uvx --from git+…@v1.7.0`**：该 tag **尚不存在** ⇒ `tasks.md:137-151`（6.6/6.7）
   的验收命令本轮跑不了。
5. **issue #30 里的数字**（如「680 条全绿」的口径）与 **`v1.7.0` 的发布日期**：仓外事实，未核。
6. **本仓自举 `check` 判绿**（`tasks.md:65` 的 4.3）与**归档/manifest 重建**（5.1/5.2）：未做
   ——本报告是未跟踪文件，且按 6.1 的顺序要求，重建 manifest 必须等四处改动落地并提交之后。
7. `tests/` 全量套件以外的面（`plugin/`、`templates/`）未在本轮目标内。

## 必须修改项

> 编号 W1、W2…；**非纯措辞**的排前面。基准 = **`3865007`**。

- **W2（非措辞 · 有具体失败场景）`spec.md` 的「不动点」Scenario 对**定制 policy 的已接入仓**不成立，
  而文档那条**唯一**的升级动作会给这类仓一句**照做就拆掉接入**的建议。**

  实跑（`/tmp/adv9/r9/p_cust`，出厂 policy 基础上加一个 `tests.command` 再接入，模拟任何 `--policy`/`--no-tests`
  接入过的仓）：

  ```
  ① init --root $A --policy seed.json            ⇒ RC=0（已接入，policy 落盘）
  ② init --root $A                               ⇒ RC=1  「检测到冲突…要更换 policy 请先 `uninit`」
  ③ init --root $A --gate-ref …@v9.9.9           ⇒ RC=1
       init：注意——.github/workflows/witnessloop.yml 已按显式 `--gate-ref` 处理（**已落盘、不回滚**）…
       init：检测到冲突（… 要更换 policy 请先 `uninit`）：  diff: policy.json   ← policy 轴
       init：已重写 .github/workflows/witnessloop.yml（→ …@v9.9.9）并同步台账
  ④ init --root $A（plain，回到幂等？）           ⇒ RC=1（**不**报「幂等，无改动」）
  ⑤ uninit --root $A                             ⇒ RC=0（这条仍成立）
  ```

  ⇒ 逐条对照 `spec.md:100-104` 的 Then：**「EXIT=0」❌**、**「随后 plain `init` SHALL 报『幂等，无改动』」❌**
  （「重写 caller + 同步台账」✅、「`uninit` 仍可用」✅）。且 `README.md:271` 明写
  「本仓自己的 `init` 早就跑不动（定制 policy 撞出厂默认）」，本轮实测本仓
  `.witnessloop/policy.json` **≠** `policy.default_policy_doc()`：

  ```
  landed == factory ? False
    evidence.building_stage: landed=None factory='building'
    require_change_for: landed=['src/**','templates/**','plugin/**']
                        factory=[…,'packages/**','server/**','cmd/**','internal/**']
  ```

  即 **本仓自己就是这一类**，任何按 `docs/gate.md §1.2` / `README.md:188-218` 走两步 recipe 的接入方
  （凡是用过 `--policy` / `--no-tests` 接入的）都会拿到 ⓐ 非零退出码、ⓑ 工具自己那句
  **「要更换 policy 请先 `uninit`」**——在这一态**照做会把 caller+台账整个删掉**（`uninit` 的实测输出：
  删 `.witnessloop/policy.json`、caller、台账），与用户想干的「换个 ref」正好相反。
  文档现在只把「打卡在 policy 上」这一个症状归因于**旧 CLI**（`docs/gate.md:105-108`：
  「要换的不是 policy，是这个 CLI 太旧……别去删 policy」），对这条**成因**给出的建议是错的。

  **修法（择一，都是一两行）**：① 给 `spec.md:101` 的 Given 加限定（如「policy 与出厂默认一致的已接入仓」），
  并在 `docs/gate.md §1.2` / `README.md` 的 ② 步补一句「若本仓 policy 是定制的，这一步会退 1：caller 与台账
  **已经改好了**，别照它的提示去 `uninit`（那会拆掉接入）」；或 ② 在 `initcmd` 的冲突文案里对该组合态
  改掉那句会误导的补救建议（`initcmd.py:513`）。

- **W3（非措辞 · 钉子级）`caller_retarget_refusal` 与 `_set_ledger_gate_ref` / 漂移循环对「caller 条目」的
  判据不一致 ⇒ V1 的静默 no-op 在一个变体态上原样复现，而 V1 自称「唯一一种」。**

  判据对照：

  - `initcmd.py:214-217`（拒绝判据）：`any(isinstance(e, dict) and e.get("path") == GATE_WORKFLOW_PATH …)`
    —— **没有** `not e.get("self")`。
  - `initcmd.py:233-238`（`_set_ledger_gate_ref`）：`… and not entry.get("self")`。
  - `initcmd.py:458`（漂移循环）：`if not rel or entry.get("self") or …: continue`。

  实跑（`/tmp/adv9/r9/p_self2`：接入后把台账里 caller 那条标 `self: true`，再删掉盘上的 caller）：

  ```
  ON DISK: […, {"path": ".github/workflows/witnessloop.yml", "sha256": "4861a80c…", "self": true}, …]
  $ init --root $B --gate-ref …@v9.9.9
  init：已接入 witnessloop（幂等，无改动）。
  RC=0
  ledger gate_ref after run: Xingkai98/witnessloop/.github/workflows/gate.yml@v1   ← 没改
  ```

  ⇒ 用户要的换 ref 被**静默丢掉**，与 V1 修掉的那个症状逐字相同（打印「幂等，无改动」+ 台账留在 `@v1`），
  只是入口换成了 `self` 标记。**可达性**：需手改台账把 caller 那条标成 `self`（工具自身不会产生该形态）——
  与 R8 认定 V1 值得修时的可达性同一档（V1 也需要一个手工态）。
  **修法**：给 `initcmd.py:214-217` 的 `any(...)` 加同一个 `and not entry.get("self")`；
  并补一条钉子（`self` 标记 + 文件缺失 ⇒ 仍是响亮拒绝、而不是幂等）。

- **W1（规格面 · 机制归属错）`spec.md:122-123` 的「（交给漂移判定响亮地报）」写错了谁负责报。**

  `spec.md:118-123` 的 Given 是「台账里**没有** caller 那一条」；该态的括号句把响亮报告归给漂移判定。
  但**漂移判定只遍历台账条目**（`initcmd.py:456-462`），没有条目 ⇒ 它**看不见这个状态**——
  这句正是 V1 自己的注释写的（`initcmd.py:195-196`：「没有条目 ⇒ 漂移判定**看不见它**、不会报」）。
  真正响亮报的是**新增的** `caller_retarget_refusal`（无条目 + 无文件 ⇒ 退 1 + 打印原因，
  `tests/test_init_gate_ref.py::test_no_caller_entry_and_no_file_refuses_loudly`）。
  同款错在 `initcmd.py:161-163` 的 `sync_caller_gate_ref` docstring（「交给漂移分支响亮地报」）。
  注意：**用户可见结果是对的**（不凭空新建 + 响亮），错的只是「谁报」——所以这是**文字/归属级**，
  但它是 SHALL 的括号句，下一个照着 spec 重构的人可能据此删掉那条拒绝。
  **修法**：把两处改成「交给 `init` 自己响亮拒绝（`caller_retarget_refusal`）」；
  真正归漂移判定的是**另一个**态（有条目 + 文件缺失，本轮实跑确认由 `initcmd.py:489` 报）。

- **W4（文档面 · 钉子级）`tasks.md:128-129`（6.3）的同步面漏了 `README.md:189` 与 `README.md:206`。**

  6.3 只点名 `README.md:20`。但同一个 6.2 之后：

  ```
  README.md:189:# 新接入：直接钉你要的 ref（⚠️ v1.7.0 发布前请用 @v1，见下）
  README.md:206:⚠️ **`v1.7.0` 发布之前，请仍然钉 `@v1`**：…
  ```

  这两句是**发布前**的指引，`v1.7.0` 一建出来就变成**错建议**（与 6.2/6.3 的意图相反），
  属于「安装文档的字面量」这一条任务自己声明的范围。这与本 change 自己在 `tasks.md:102-109`（N3）
  立的口径冲突——「自查面不能只点名几处」。**修法**：6.3 的动作清单补 `README.md:189`、`README.md:206`
  （删掉/改写「发布前请仍然钉 `@v1`」），或明确写上「发布后这两句必须一起改」。

## Open Questions

1. **W2 的修法口径**（要人拍板）：把它当**规格限定**（Scenario 的 Given 加「policy 与出厂默认一致」）、
   还是把它当**行为目标**（定制 policy 的仓上 `init --gate-ref` 也应该 EXIT=0——即把 policy 轴
   像 caller 轴一样放进 `ignore`）？我倾向后者更贴合「单一、显式的升级动作」，但那会与本 change
   已定的组合语义（`spec.md:125-131`：policy 轴**照旧**参与退出码）产生张力，需要一起裁。
2. **W3 的处置**：加 `not entry.get("self")` 判据（一行），还是像其它「手工态」一样登记为刻意不修？
   （我倾向加：它直接与 V1 的「唯一一种」自称冲突。）
3. **O1（低危观察）**：`created_files` 的守卫只覆盖「不是数组」；**数组元素非对象**仍崩
   （实跑：`created_files = ["x", 1]` ⇒ `AttributeError: 'str' object has no attribute 'get'`，
   经 `entry.py` 兜成一句「内部错误」+ RC=1；`uninitcmd.py:43` 同款）。
   base（`ae99256`）同样崩 ⇒ 属**既有行为**，不列必须修改项；但 `initcmd.py:442-447` 的注释读起来像把
   这一族关掉了，一行 `isinstance(entry, dict)` 可以补齐。要补吗？
4. **O4（低危观察 · 钉子级）**：解析器对 `…@refs/heads/`、`…@refs/tags/`（前缀之后为空）会输出
   **空的 `ref=` 且不打 `::warning::`**（本轮实跑：`ref=''`、notice 打「ref = （来源：job.workflow_ref 的分支名）」、
   warning 无）⇒ 与 `spec.md:45-46` 的「fail-closed 到既有默认 + warning」不符，且
   `tests/test_gate_workflow.py:454` 的 `test_resolve_never_leaves_the_ref_empty` 自称「任何输入下都不得为空」
   而其枚举的 4 个输入里没有这种形态。**不可达**（GitHub 生成的 `job.workflow_ref` 的分支/tag 名非空），
   故只登记：要收紧就把 `case` 的 glob 写成 `*@refs/heads/?*`，或把该测试的措辞改成「已枚举的输入」。
5. **O2（低危观察）**：`--gate-ref ""` 是 falsy ⇒ 与「不给」等价（既有链，base 同；`initcmd.py:292`），
   无告警。刻意保持？
6. **O3（低危观察）**：`tasks.md:89` 的「⇒ `673 passed`」与今天基线 **687** 不一致（陈旧计数；
   6.1 执行时若照它对数会以为改动没生效）。要不要顺手改成「(post-merge 时以当时基线为准)」？

## 收敛结论

**不收敛。**

**判据①（本轮无新可证伪项）——不满足。**
本轮在 `src/` 与 `.github/workflows/gate.yml` 的**行为层找不到新缺陷**（任务书点名的五个新面里，
未接入分支、`check` 自报 vs `guard`/`manifest build`、①′ recipe、`tasks §6` vs `design §2 D4`
四项**未见**新缝），但新增了 **4 条可复现的证伪**，**全部属「规格/文档面」或「钉子级」**，没有一条是
「用户会碰到的 `src` 行为缺陷」：

- **W2**：规格 Then + 文档 recipe 在**一整类真实仓**（定制 policy 的已接入仓，**含本仓**）上不成立，
  且工具自己的建议（「请先 `uninit`」）照做会拆掉接入 —— 具体失败场景，不是措辞。
- **W3**：`caller` 条目判据三处不一致 ⇒ V1 的静默 no-op 在一个变体态复现，V1 的「唯一一种」被证伪
  —— 行为面，但可达性低（需手改台账），故定性为**钉子级**。
- **W1**：`spec.md` 的 Then 括号句把「谁响亮报」写错了（用户可见结果仍对）—— 规格面**机制归属**。
- **W4**：`tasks.md 6.3` 的同步面漏了 `README.md:189/206`（发布后变错建议）—— 文档面钉子级。

按判据①的口径，**W2 与 W3 是「可证伪」而非「措辞」**（各自附了实跑输出与具体失败场景），
因此本轮不能算收敛。分类上：**新证伪 = 0 条行为缺陷（`src`/`gate.yml`）＋ 2 条规格/文档面断言错
（W1、W2）＋ 2 条钉子级（W3、W4）；另有 4 条低危观察（O1–O4，含 1 条不可达输入）。**

**判据②（历轮必须修改项全部落地）——满足。**
K1–K8、L1–L6、M1–M4、N1–N3、P1、T1、U1–U4、V1–V4 **逐条在正文与代码里核过**（不采信 §7.9 自报表），
全部落地；本轮**复算/复跑**过的有：K5（47）、K8（本地探针分支 `c7aa0378…`）、M1（四处字面量族 ⇒ 全绿）、
P1（非数组/键缺失两态受控退 1，不重建）、V1（有条目 + 文件缺失 ⇒ 漂移分支响亮报）、V2（1 红 → 7 红）、
V3（四类来源文案实跑）、M4（①′ 成立）、T1（install 步吃 `steps.wl-ref.outputs.ref`）、全量套件（687 passed）。

**建议下一轮**：只需回 **W2**（一条口径裁定 + 一两行文档/规格改动）、**W3**（一行判据 + 一条钉子）、
**W1/W4**（各一句文案）与 O3/O4 的取舍。这四条都不动 `src/` 的机制，回完即可复判。

---

## 处置（主 session 在 R9 之后追加，非审阅者原文）

> 本报告判定**不收敛**（判据②满足、①不满足），基准 `3865007`。**W1–W4 全部已落库**；
> 你那条「`src/` 与 `gate.yml` **行为层零新缺陷**」的结论我按字面采信，本轮四条都在
> 规格/文档/钉子层面。

- **W2（规格/文档，有具体失败场景）**：`spec.md` 的「干净不动点」Scenario 补**前提**
  ——「policy 与出厂默认一致（或本次同时给 `--policy`）」，并写明**定制 policy 的仓不满足它**、
  且那句「要更换 policy 请先 `uninit`」**不可照做**（`uninit` 会把 caller + 台账一起删）。
  这正是本仓自己的形态（`README` 的「本仓自身接入」已自认 `init` 跑不动）。你还指出了
  文档把该症状**只**归因于「旧 CLI」——`docs/gate.md §1.2` 的那段现在两种成因都写了。
- **W3（钉子级行为）**：`caller_retarget_refusal` 的条目扫描补 `not entry.get("self")`，
  与 `_set_ledger_gate_ref` / 漂移循环**同口径**（三处不一致就是缺口本体）。
  钉子 `test_a_self_flagged_caller_entry_does_not_hide_the_refusal`；
  变异复核：在**未含该守卫**的树上它**红**、在有守卫的树上**绿**。
- **W1（机制归属错）**：`spec.md` 与 `initcmd` 注释里那句「交给漂移判定响亮地报」都改了
  ——漂移判定只遍历台账条目，那一态它**看不见**；把它变响亮的是 `caller_retarget_refusal`。
- **W4（文档面）**：`tasks.md 6.3` 从「点名 `README.md:20`」改成「**按语义找** README 里所有
  把 `@v1` 当当前值写的地方」并附 `grep -n "@v1" README.md docs/gate.md`，写明行号会漂、
  历史引文保留。

**你的低危观察**：`tasks.md` 里那个陈旧的「673 passed」已改成不依赖计数；
另外三条（`created_files` 元素非对象仍崩、`…@refs/heads/` 空后缀、`--gate-ref ""` 等价于不给）
**登记不修**——前两条属**先于本 change 存在**的行为，第三条是本仓既有的参数解析口径。

**R10**：树在该 revision 上冻结。请**优先找行为缺陷**；若只剩「再补一条钉子」，请标明类别。
