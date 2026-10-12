# Building Review: building-review-gate

## Reviewer

- run id: `building-reviewer-building-review-gate-2026-10-12`
- 时间: 2026-10-12T07:43:11Z
- 被检 revision: `38c58b903e84333cf2f70293a450253df6398698`（`--base origin/main`）
- 方式: 独立零记忆实现审阅者（**无**作者会话记忆）。默认实现有错，逐条开门核 `文件:行号`；
  能实测的在 `/tmp` 探针与本 worktree 打补丁后跑（`uv run pytest -q`）。**未 commit**，
  实验改动全部还原（`git status --porcelain -uall` = 0 行）。

## Verdict

**PASS**

- 任务 A1–A2 / B1–B9 / C1–C3 / D1–D4b **逐项核过，全部真做完**（0 个 ❌；E0–E3 按设计仍在途，非本范围）。
- 8 条新增用例**逐条**做变异检查：**无假测试**（每条都至少有一个让它变红的实现改动）。
- `uv run pytest -q` = **412 passed**（基线 404 + 8 新增，既有用例 0 条改动/0 条变红）。
- 两条对外行为变更**独立复现**（`exit 0 → exit 1`），README / `docs/gate.md §9` 的表述与实现逐字相符。

无阻塞项。发现 1 个**逃逸变异**（文档承诺的 `building_stage` 覆写轴无测试钉住）与 3 条非阻塞观察，见 Issues。

## 任务逐项验证

### A. policy / 常量轴（D2）

- **A1** ✅ `constants.py:49` `DEFAULT_BUILDING_STAGE = "building"`；`policy.py:117-119`
  `building_stage=str(evidence.get("building_stage") or C.DEFAULT_BUILDING_STAGE)`（缺省回落），
  字段进了 `Policy` dataclass（`policy.py:60`）。实测：`uv run python` 直接读本仓 policy ⇒
  `pol.building_stage == "building"`（本仓 policy 的 `evidence` **未**写该字段 ⇒ 走的正是回落分支）。

### B. 判定（D1/D2）

- **B1** ✅ 助手存在且 `verify_body=False` 时不读正文：`evidence.py:172-235`；用例
  `test_building_gate.py:127-146`。**变异验证**见下（改默认值 ⇒ 红）。
- **B2** ✅ grill 判定行为不变：`evidence.py:238-257` 薄封装传 `verify_body=True`，
  `reason` 逐字保留原句「grill 决策记录必须有对应的审阅证据」（`evidence.py:255`）。
  回归面实测：`test_check_grill_evidence.py`（5 条）+ `test_guard.py`（13 条）全绿。
  ⚠️ 唯一非零差异见 Issues N-3（一条**文案**从「无法核验 grill 证据」变「无法核验该 stage 的证据」）。
- **B3** ✅ `evidence.py:172` 抽出参数化助手；`checkcmd.py:83` 与 `guardcmd.py:112` 两处调用点行为不变。
- **B4** ✅ `test_building_gate.py:31-40`：改了 `src/app.py` + 只有 grill ⇒ exit 1，stderr 含
  `stage=building` 与 `changes/add-x`。**实测**（`/tmp/brg/probe.py` P1）：也是 exit 1。
- **B5** ✅ `test_building_gate.py:52-58`：只动 change 目录 ⇒ 绿。
- **B6** ✅ `test_building_gate.py:61-70`：`--stage buildings` ⇒ exit 1 且点名现有 stage。
  实测文案：`无 stage=building 的 manifest（现有 stage：grill, buildings）——…`。
- **B7** ✅ `test_building_gate.py:98-115`：审阅后再改 `src/` ⇒ exit 1 且含「审阅的是旧 revision」。
- **B8** ✅ `checkcmd.py:75` 算 `code_hits`、`:91-98` 在 change 循环内接入；文案经 `reason=` 参数传入
  （**参数化，非第二份实现**）。
- **B9** ✅ `test_building_gate.py:75-95`：本 PR 落代码 + 顺带纯文档 change ⇒ 该文档 change 也被点名，
  有实现的那个**不**被点名（用例显式断言 `changes/impl-a：无 stage=building` 不在 stderr 中）。
  **实测**（probe P3a）：exit 1，唯一 building finding = `changes/b-doc`。

### C. 自伤面

- **C1** ✅ 既有用例**无一条改动**：`git diff origin/main...HEAD -- tests/` 只新增
  `tests/test_building_gate.py`（`--stat`：仅该文件 `157 +++`），既有测试文件 0 行改动；
  总数 412 = 404 + 8。grill 的「0 条新增失败」结论成立。
- **C2** ✅ 对三个 active change 直接调判定函数（`uv run python`，逐条）：
  `dogfood-bootstrap` / `grill-evidence-gate` / `guard-crash-exit` 的
  `grill_findings=[] building_findings=[]` ⇒ 结论**不合格数为 0**。
  （`building-review-gate` 自身 `building_findings` 有 1 条——**预期**，本 change 还没有 building 证据。）
- **C3** ✅ `guard` **零改动**（`git diff origin/main...HEAD -- src/witnessloop/guardcmd.py` 为空）；
  `guardcmd.py:112` 仍只调 grill 那条。spec Scenario「guard 不要求 building 证据」由既有
  `test_guard.py:53 test_allows_a_code_write_when_grill_evidence_is_complete`（只写 grill 证据 ⇒ 放行）钉住。

### D. 文档

- **D1** ✅ `docs/gate.md:267`（§6 `check` 退出码表）新列为「缺 building 审阅证据」。
  位置正确：改的是 `check` 那张表（`guard` 表在 `:271` 起，未受影响）。
- **D2** ✅ 新增小节**落在 §9**（`docs/gate.md:347-372`），触发 + 判据 + 边界齐备。
  ⚠️ tasks/design 写的是「§8」，实现选了 §9（§8 已被 grill 正文校验占用）——这个选择本身正确，
  但 `checkcmd.py:90` 的注释仍写「见 docs/gate.md **§8**」⇒ 指向错节（见 Issues N-1）。
- **D3** ✅ `README.md:108-113` 写明**两条**行为变更（① 改码没跑 review-loop 绿变红；
  ② 多 change 同 PR 每个都要 building 证据）。**两条我都独立复现**（probe P1 / P3d，均 `exit 0 → exit 1`，
  详见「实测复现」）。不是只写一条。
- **D4b** ✅ `docs/gate.md:70-75`（§2）显式声明 `require_change_for=[]` 会连 building 门禁一起静默失效，
  并补了「没覆盖真实代码路径 ⇒ 同样静默通过」；`specs/building-evidence/spec.md:70-77`「边界声明」节同义。
  **实测**（probe P2）：`require_change_for: []` + 改 `src/` + 只有 grill ⇒ `exit=0` ⇒ 文档的「实测：`check` 退 0」属实。
- **D4** ✅ `templates/review-loop.md:149-152`「门禁口径（甲案）」一句，与 Q1 = 甲（`grill-review.md`
  `## User Confirmation` Q1「取**甲案**——不解析 verdict 文本」）一致，且指向的 `§9` **正确**。

### E. 在途（非本范围）

- **E0/E1/E2** `[ ]` 未勾 —— **正确且是刻意的**：实测 `uv run witnessloop check --root . --base origin/main`
  当前 exit 1，其中第 5 条正是本门禁的 dogfood 结论：
  `openspec/changes/building-review-gate：无 stage=building 的 manifest（现有 stage：grill, grill-adversarial）`。
  本报告 + 随后的 `manifest build --stage building` 就是转绿的那一步。**门禁对自己生效，未见自锁。**

## 变异检查（每条新测试是否真能红）

方法：`python3` 精确替换实现的一处（`str.replace(old, new, 1)`，替换前断言命中 1 次），
`uv run pytest -q --tb=no -rf`，跑完 `git checkout -- <file>` 还原。**全程用 `uv run`**（PATH 上的裸
`witnessloop` 是另一份 uv-tool 安装，未打补丁——未使用）。

| # | 改坏的实现 | 受影响用例 | 结果 |
|---|---|---|---|
| M1 | `checkcmd.py:91` `if code_hits:` → `if False:` | `test_red_when_code_changed_without_building_evidence`、`test_stage_typo_is_diagnosable`、`test_every_change_in_a_code_pr_must_have_building_evidence` | **3 红** ✅ |
| M2 | `checkcmd.py:94` `stage=pol.building_stage` → `stage=pol.grill_stage` | 同上 3 条 | **3 红** ✅ |
| M3 | `constants.py:49` `DEFAULT_BUILDING_STAGE = "building"` → `"grill"` | 同上 3 条 | **3 红** ✅ |
| M4 | `evidence.py:179` `verify_body: bool = False` → `True` | `test_green_when_building_evidence_present`、`test_code_change_after_the_review_is_stale`、`test_shared_helper_requires_only_existence_for_building` | **3 红** ✅ |
| M5 | `evidence.py:216` 去掉 `if not verify_body: return []`（恒验正文） | `test_check_red_when_the_grill_report_body_is_incomplete`、`test_check_stays_fail_closed_on_an_undecodable_report`、`guard` 的 `test_report_decode_failure_blocks_with_a_clear_message` | **3 红** ✅（grill 回归面真的钉住了） |
| M6 | `checkcmd.py:120` 去掉 `and pathutil.matches_any(...)`（恒命中） | `test_not_required_when_only_the_change_dir_changed` + `test_require_change.py` 3 条 | **4 红** ✅ |
| M7 | `checkcmd.py:113` `if not pol.require_change_for: return []` → 直接 `return []`（`_code_hits` 恒空） | building 3 条 + `test_require_change.py` 3 条 | **6 红** ✅（**证明 `_require_change` 真的共用 `_code_hits`**，不是两份口径） |
| M8 | `evidence.py:206` 把 `{reason}` 写死 → 固定文案 | `test_shared_helper_reports_missing_stage_with_the_given_reason` | **1 红** ✅ |
| M9 | `contract.py:343` `in scope.pr_paths` → `if False`（关掉 stale 判定） | `test_code_change_after_the_review_is_stale` | **1 红** ✅ |
| M10 | `evidence.py:198` `== stage` → 恒真（任意 stage 都算命中） | 6 条（含 `test_check_names_the_existing_stage_so_a_typo_is_diagnosable`） | **6 红** ✅ |
| **M11** | `policy.py:117-119` `building_stage` 忽略覆写 → `building_stage=C.DEFAULT_BUILDING_STAGE` | —— | **412 passed，全绿** ❌ **逃逸** |

**结论**：8 条新增用例**全部**至少被一个实现改动打红 ⇒ **无假测试**。
唯一逃逸的是 **M11**：文档（`docs/gate.md:349`、`spec.md:9`、`constants.py:46-48`）都写
「`policy.evidence.building_stage` 可覆写」，代码也**确实**实现了这条轴，但**没有任何测试**钉它 ⇒
把覆写整个删掉也全绿。这是**覆盖缺口**（不是假测试，因为没有任何用例声称在测它）——详见 Issues N-2。

## Issues

- **[非阻塞 N-1] 代码注释指向错节**：`src/witnessloop/checkcmd.py:90` 写
  「**不解析报告里的 verdict 文本**——见 `docs/gate.md §8`」，但 building 小节实际在 **§9**
  （`docs/gate.md:347`）；§8（`:305`）是「grill 证据的正文校验」。本仓卖点是「不让文档漂移」，
  这处指针恰恰会把读者引到另一条判据上。
  **建议修法**：`§8` → `§9`（一行）。`templates/review-loop.md:151` 与 `README.md` 引的 `§9` 是对的，
  只有这一处错。

- **[非阻塞 N-2] 文档承诺的 `building_stage` 覆写轴零测试**：`spec.md:9` 与 `docs/gate.md:349` 都承诺
  「默认 `building`，`policy.evidence.building_stage` 可覆写」，实现也做了（`policy.py:117-119` ⇒
  `checkcmd.py:94`），但 **M11** 证明：把覆写整个忽略、恒用默认值，**412 条全绿**。
  类比既有的 `test_require_change_for_is_configurable`（`test_require_change.py:63`），
  本仓对「参数化轴」的惯例是**配一条可配置性用例**。
  **建议修法**：新增 `test_building_stage_is_configurable`——`init` 后把
  `evidence.building_stage` 改成 `"post-impl"`，造 `src/` 改动 + 只有 `stage=grill` ⇒ 期望 exit 1 且点名
  `stage=post-impl`；再补一份 `stage=post-impl` manifest ⇒ 期望绿。
  （说明：`grill_stage` 有**同款**既有缺口，本仓对它的处理是先例；故本条**不**判阻塞，
  但本 change 是**新加**这条轴，补上成本极低。）

- **[非阻塞 N-3] grill 那条的「行为不变」在**文案**上有一处收窄**：`evidence.py:232`
  原为 `f"报告{why}（{type(exc).__name__}）：无法核验 grill 证据"`，抽参后变成
  「无法核验**该 stage 的**证据」。判定行为（红/绿）确实不变，但 `guard` 与 `check` 的 grill 分支
  是**用户可见**文案，且没有任何用例断言这句（`test_guard.py:255` 只断言前缀「报告无法解码」）。
  **建议修法**：接受（共用助手的必然代价），或在 spec 的「行为不变」旁注明这处措辞变化。

- **[非阻塞 N-4] README 第②条少一个限定词**：`README.md:110`「且**一个 PR 同时触及多个 change** 时，
  **每个** change 都要 building 证据」——缺「且该 PR 触及代码」这个前提
  （`docs/gate.md:359-360` 写全了：「本 PR 触及代码 ⇒ 本 PR 触及的**每个** change 都要…」）。
  方向上属于**过度预警**（不会让接入方低估门禁），非阻塞。建议顺手补「（且该 PR 触及代码时）」。

- **[非阻塞 N-5] `init` 写出的 policy 少一个可发现入口**：`policy.py:45` 的 `default_policy_doc()`
  写了 `evidence.grill_stage`，但**不**写 `evidence.building_stage`。行为正确（缺省回落），
  但接入方打开 `.witnessloop/policy.json` 看不到这条轴，而 `docs/gate.md §2` 的 JSON 样例
  **两者都没列**（既有状态）⇒ 形成「文档有、样例没有、init 只写一半」的三方不一致。
  建议：与 `grill_stage` 对齐，`default_policy_doc()` 一并写 `building_stage`。

- **[非阻塞 N-6] `building_stage == grill_stage` 会让新门禁退化**（R1 的 R-new-9，未在文档中提醒）：
  若接入方把两者配成同值，building 那条退化为「复查 grill manifest」——无害但失去意义。
  §9 的覆写说明处可加一句「不要配成与 `grill_stage` 同值」。

## 实测复现

环境：`export PATH=/home/happy/.local/bin:$PATH`，cwd = `/home/happy/wl-wt/building-review-gate`。

1. **全量测试（基线核对）**
   `uv run pytest -q` → `412 passed in 19.89s`（执行前的基线声明 412 = 404 + 8 成立；
   `git diff origin/main...HEAD --stat -- tests/` 只有 `tests/test_building_gate.py | 157 +++`）。
2. **打包 / 安装烟测**
   `uv build` → `Successfully built dist/witnessloop-0.1.0.tar.gz` + `dist/witnessloop-0.1.0-py3-none-any.whl`；
   `uvx --from dist/*.whl witnessloop --version` → `witnessloop 0.1.0`，`exit=0`。（`dist/` 已删除。）
3. **本 change 的 dogfood 状态**
   `uv run witnessloop check --root . --base origin/main --head HEAD` → `exit=1`，5 项：
   4 项是两份 grill manifest 的 `tasks_hash` 漂移 + `审阅的是旧 revision`（**预期**，E1 重建后消失），
   第 5 项 = `openspec/changes/building-review-gate：无 stage=building 的 manifest（现有 stage：grill, grill-adversarial）`
   —— 正是本门禁的触发，**门禁确实挂上了判定路径**。
4. **独立端到端探针**（`/tmp/brg/probe.py`，复用本仓 `tests/helpers.py`/`conftest.py` 原语，产物全在 `/tmp`）

   | 探针 | 构造 | 期望 | 实际 |
   |---|---|---|---|
   | P1 | tasks.md **全部勾选** + 改 `src/app.py` + 只有 grill | 仍要求 building（**不由勾选触发**） | `exit=1` ✅ 点名 `stage=building` |
   | P2 | `require_change_for: []` + 改 `src/` + 只有 grill | 整条代码门禁静默失效 | `exit=0` ✅ 文档的「实测退 0」属实 |
   | P3a | 多 change：`impl-a`(有 building) + `b-doc`(无) | 只点 `b-doc` | `exit=1` ✅ 唯一 building finding = `changes/b-doc` |
   | P3c | 多 change **正确次序**（先全部内容、后全部证据），两个都补 building | 绿（门禁**可满足**，非死局） | `exit=0` ✅ |
   | P4 | building manifest 绑一份**非 grill 式**报告（`CHANGES_REQUESTED`、无 `## Confirmed Decisions`） | 绿（**不解析 verdict 文本**） | `exit=0` ✅ |
   | P5 | building manifest 绑一份**空**报告（hash 一致） | 绿（只要求**存在**） | `exit=0` ✅ |
5. **两条对外行为变更的独立复现**（探针 + `checkcmd.py:91` 临时改 `if False:` 模拟未打补丁的判定路径，
   跑完 `git checkout --` 还原）

   | 行为变更 | 未打补丁 | 当前实现 |
   |---|---|---|
   | ① 改了代码但没跑 review-loop（P1 场景） | `exit=0`（**绿**） | `exit=1`（红） |
   | ② 多 change 同 PR，纯文档 change 缺 building（P3d：正确次序，`b-doc` 只有 grill） | `exit=0`（**绿**） | `exit=1`（红，只点 `b-doc`） |

   ⇒ README / `docs/gate.md §9` 的「两条行为变更」**不是把现状写成规范**，是真实变更。
6. **C2 回归（三个 active change 直调判定）**
   `uv run python` → `dogfood-bootstrap / grill-evidence-gate / guard-crash-exit`：
   `grill=[] building=[]`（均合格）。
7. **spec 覆盖核对**：`specs/building-evidence/spec.md` 的 4 条 Requirement / 7 个 Scenario，
   逐条找到实现点与钉住它的用例：
   Req1-S1 → `test_building_gate.py:31`；S2 → `:42`；S3 → `:52`；S4 → `:75`；S5 → `:61`；
   Req2-S1 → `:98`（+ 实现 `contract._check_git_span`，既有）；Req3-S1 → `test_guard.py:53`（既有）；
   Req4-S1 → `:127`（单元层）+ `:42`（端到端层，building 报告是普通正文）。
   边界声明 → `test_require_change.py:87`。**无未被钉住的 Requirement/Scenario。**
8. **交叉仓声明抽查**（`docs/gate.md:353-355` 的 asterwynd 口径）：
   `/home/happy/my-agent/scripts/check_openspec_artifacts.py` 中 `PASS` 的 4 处命中全在注释/文案
   （`:1122`、`:1139`、`:1623`、`:1640`、`:1716`），**无** verdict 解析逻辑 ⇒ 「它的『PASS 硬门』实质是
   『闭环必须跑过』」属实。
9. **还原确认**：所有变异跑完即 `git checkout --`；`git status --porcelain -uall` = **0 行**；
   `grep -rn "if False:" src/witnessloop/checkcmd.py` 无残留；`dist/` 已 `rm -rf`；**未 commit**。
