# Building Review: dogfood-bootstrap（实现阶段独立审阅）

> 独立零记忆审阅者产出。算法 / 三态 verdict / 审阅维度依据 `templates/review-loop.md`。
> 只读核验：`git diff` + Read 源码 + `uv run pytest` 实测（未改任何文件，唯一写入即本报告）。

## Reviewer

- run id: `building-reviewer-dogfood-bootstrap-2026-10-11`
- 时间: 2026-10-11（UTC）
- 被审对象: `git -C . diff main..HEAD`（`6aa9821` 立项文档 + `6cb56ce` 实现；base = `843b691`）
- 审阅材料: change 目录 `proposal.md` / `design.md` / `tasks.md` / `specs/dogfood/spec.md` + `reviews/grill-*.md`

## Verdict

**CHANGES_REQUESTED**

核心能力（`init --policy` + R2 冲突修复 + 本仓接入 + 文档）**真实存在、实测通过**，
354 项测试全绿。但 **spec 的一个 Scenario 与实现/其它文档自相矛盾**（见 I1，中等），
属「spec 不对齐」范畴，需先对齐 spec 文本再收尾。非阻塞性缺陷，故非 BLOCKED。

---

## Tasks Verification（逐条读代码核实；⚠️ 本 change 的 tasks.md **19 条全为 `[ ]`、0 条 `[x]`**）

| 任务 | 属实? | 证据（file:line） |
|---|---|---|
| A1 指定内容落盘 + 台账 hash 一致 | ✅ | `tests/test_init_policy.py:39,46`；`initcmd.py:44-49`、`initcmd.py:80-85` |
| A2 幂等（同 policy 重跑 exit 0） | ✅ | `tests/test_init_policy.py:54`；`initcmd.py:225-226` |
| A3 `uninit` 往返 | ✅ | `tests/test_init_policy.py:64` |
| A4 缺失/非法/非对象 → 拒且不写 | ✅ | `tests/test_init_policy.py:74,84,92`；`initcmd.py:52-68`、`:114-121` |
| A4′ **逃逸路径 → 拒** | ❌ **未实现** | 见 I1：`initcmd.py:57` 明确**允许**仓外路径 |
| A5 `--dry-run` 组合 | ✅ | `tests/test_init_policy.py:108`；`initcmd.py:142-147` |
| A6 已接入后给不同 policy → 冲突（R2） | ✅ | `tests/test_init_policy.py:119`；`initcmd.py:204-223` |
| A7 `cli.py` 加 `--policy`；`desired_files` 接外部文本；`run` 读+轻校验 | ✅ | `cli.py:48-54`；`initcmd.py:44`、`:114-121` |
| A8 `_already_initialized` 新增 desired-vs-磁盘 冲突分支 | ✅ | `initcmd.py:209-223` |
| B1 落地 `.witnessloop/` + caller workflow（补 templates/plugin） | ✅ | `.witnessloop/policy.json`、`.witnessloop/init-manifest.json`、`.github/workflows/witnessloop.yml`；`require_change_for=[src/**,templates/**,plugin/**]` |
| B2 seed 不入库 | ✅ | `git ls-files` 无 seed；README 述明 seed 在仓外 |
| C1 `docs/gate.md` §1.1 | ✅ | `docs/gate.md:33-44` |
| C2 `README` dogfood 段 + `--policy` 用法 | ✅ | `README.md:48-63` |
| C3 `docs/design.md` 状态/§10 更新（§9 风险4 不变） | ✅ | `docs/design.md:4`、`:67-71`、`:154` |
| C4 `docs/tasks.md` 追加 G 段 | ✅ | `docs/tasks.md:59-73` |
| C5 同步 `tests/test_docs.py` 守卫 | ✅ | `uv run pytest` 全绿（含 `test_docs.py`）；改动未碰被钉措辞 |
| D1 端到端：两段提交 + `manifest build`×3 + `check` 绿 | ⏳ **未完成（预期）** | 实跑 `check` → 仍红（缺 manifest）；证据产出属收尾步骤，**不算缺陷** |
| D2 负例：改 `.witnessloop/policy.json` 无事件 → `check` 拦 | ✅ | 既有 `tests/test_invariants.py:44-59`（不变集对「修改」要事件，`checkcmd.py:157` 仅对 `A` 免） |
| D3 独立 review-loop | ⏳ 进行中（本报告） | — |
| D4 branch protection（需用户） | ⏳ 未做（需用户） | — |

> `_require_change`（`src/**` 命中）由 `checkcmd.py:84-112` + `tests/test_require_change.py` 覆盖；
> 本 change 自身 diff 含 `src/witnessloop/{cli,initcmd}.py`，实跑 `check` 仅报「缺 manifest」——
> 旁证 design D3「A 自身 diff 无需解释事件」成立。

---

## Issues

### I1（MUST · 中等）spec 的 Scenario 要求「逃逸路径 → 拒」，实现却**明确允许仓外路径**，且 change 内部文档互相矛盾

`specs/dogfood/spec.md` 的「非法 policy 输入」Scenario 把「逃逸路径」列为必须报错、不写文件的
非法输入：

- `specs/dogfood/spec.md:34`：`**Given** `--policy` 指向缺失 / 非法 JSON / 非对象 / **逃逸路径**的文件`
- `specs/dogfood/spec.md:36`：`**Then** 报错并非零退出，**不写出任何文件**`

但实现**没有任何**「逃逸路径」判定，且**刻意允许**仓外路径：

- `src/witnessloop/initcmd.py:52-68` `load_policy_override` 只查「文件存在 + JSON 根是对象」；
- `src/witnessloop/initcmd.py:57`：注释明写「**允许指向仓外路径**（seed 不入库，常在仓外，见 Q5）」；
- `tests/test_init_policy.py:100` `test_init_policy_outside_repo_is_allowed` **断言仓外路径应当成功**。

更甚：change 内部对「路径逃逸」的口径**自相矛盾**——
`proposal.md:52`（「policy 非法/**路径逃逸** → 拒」）与 `design.md:126`（§5 测试策略：
「非法 JSON / 非对象 / **路径逃逸** → 拒且不写」）说「拒」；而 `design.md` D2 边界
（`:62`，只列「缺失/非法」）、`tasks.md:12`（A4：**允许指向仓外路径**）、`README.md:54`、
`docs/gate.md:42` 说「允许」。**同一 change 内 A 处说拒、¬A 处说允许。**

- **判定**：spec 是**规范性**产物；其 Scenario 列举的四类输入里，「逃逸路径」一类
  既无实现、也无测试，且与 Q5/A4 的刻意决策相反。属 spec 未对齐。
- **建议处置**（推荐改 spec，与 Q5 一致）：删除 `spec.md:34` 的「逃逸路径」四字，
  并同步 `proposal.md:52` / `design.md:126` 的「路径逃逸」表述；若确要保留该语义，
  则须给出**可判定**的定义（仓外是允许的，故须另立判据）并补实现 + 负例测试。
  二者取其一，**不得**维持现状。

### I2（LOW · 文档/流程）`tasks.md` 19 条全 `[ ]`、0 条 `[x]`，低估已完成进度

`openspec/changes/dogfood-bootstrap/tasks.md`（与 `docs/tasks.md:59-73` 的 G 段）把所有
已实现并测过的条目（A1–A8、B1–B2、C1–C5）都留在未勾选状态。review-loop 要求收尾时
`[x]` 反映真实完成项；当前读者无法从勾选判断进度。
**建议**：把 A/B/C 各条改为 `[x]`，D1/D2 完成后勾选，D3 完成后勾选，D4 留 `[ ]`（需用户）。

### I3（LOW · 可维护性，信息性）两处冲突判定逻辑近乎重复 + 重跑 `init` 的 `--gate-ref` 语义

- `initcmd.py:130-140`（首次 init 的冲突块）与 `initcmd.py:209-223`（已接入后的冲突块）
  是近乎逐字重复的列表推导，只差报错文案。可抽一个 `_conflicts(root, desired)` 助手，
  以免两处将来漂移。
- `_already_initialized` 重建 `desired` 用的是**本次调用**的 `args.gate_ref`（`cli.py:44`，
  默认 `@v1`），**不读**台账里记录的 `gate_ref`。故若某仓曾以非默认 `--gate-ref` 接入，
  之后跑不带该 flag 的 `init` 会因 caller workflow 内容不同而报「冲突」——行为是
  fail-closed（安全），但对「幂等」的朴素期待是个意外。可接受，建议注释点明。
  （本次 dogfood 用默认 `@v1`，不触发。）

---

## Test Results

- `uv run pytest -q` → **354 passed in 15.15s**（含 `test_docs.py` 漂移守卫全绿）。
- `uv run witnessloop check --base main --head HEAD` → **exit 1**，唯一 finding：
  `openspec/changes/dogfood-bootstrap：缺少 review manifest`。
  = **预期**：审阅证据（manifest）尚未产出（属 review-loop §6 收尾）；除证据外 A 自身 diff 无告警，
  旁证 design D3 与 `require_change_for` 生效。

---

## 结论

- 实现（`init --policy`、R2 冲突修复、本仓接入、文档同步、漂移守卫）**核心属实、测试通过**；
  唯一阻塞收尾的是 **I1**（spec Scenario 与实现/文档口径矛盾），必须先对齐 spec 文本。
- **verdict = CHANGES_REQUESTED**：修掉 I1（推荐改 spec + 同步 proposal/design 措辞）、
  顺手处理 I2/I3，再进 §6 收尾（`manifest build`×3 → `check` 绿）。
- 未发现安全漏洞、未发现 CI 弱化（`.github/workflows/ci.yml`、`gate.yml` **未改动**，
  diff 仅**新增** `witnessloop.yml` caller），未发现核心功能缺失 ⇒ 非 BLOCKED。

---

## 第 2 轮审阅

- 时间: 2026-10-11 07:55 UTC
- 裁定: **PASS**
- 被审对象: 修复提交 `d3226a2`（R1 I1–I3），实测 + 读码 + `uv run pytest -q`。

### 逐条核验

**I1（spec 口径矛盾）— 已落实。**
- `specs/dogfood/spec.md:34` 的「非法 policy 输入」Scenario 已删「逃逸路径」，只余「缺失 / 非法 JSON / 非对象」；
  并**新增**正向 Scenario「seed 在仓外（允许）」（`:38-41`），由 `tests/test_init_policy.py:100`
  `test_init_policy_outside_repo_is_allowed` 背书（已读，断言仓外 seed → 成功）。
- `proposal.md:52`、`design.md:126` 措辞同步为「非法 JSON / 非对象 → 拒；**仓外路径允许**」；
  `design.md` D2 边界（`:64-65`）仍为「缺失/非法 → 报错不写」——与「仓外允许」不冲突（仓外不是非法）。
- **实测**：`grep -rn '逃逸' openspec/changes/dogfood-bootstrap/` 命中**仅**本报告（R1 正文）与
  `spec.md:41`（正向句「**不**因『逃逸』报错」）。change 内**再无**「路径逃逸 → 拒」矛盾表述。

**I2（tasks 勾选如实）— 已落实。**
- `tasks.md`：A1–A8、B1–B2、C1–C5、**D2 均 `[x]`**；D1/D3/D4 仍 `[ ]`（收尾项，D3 即本审阅）。
- `docs/tasks.md` G 段：G1/G2/G3 `[x]`，G4/G5 `[ ]`——与 A/B/C 完成、D1/D4 未完成一致。
- **核实被勾项真的完成**：`git ls-files` 确认 `.witnessloop/{policy.json,init-manifest.json}` +
  `.github/workflows/witnessloop.yml` 已入库（B1/B2）；A/C 由 `tests/test_init_policy.py`、`test_docs.py`
  全绿覆盖；D2 由 `tests/test_invariants.py:44` `test_policy_file_stays_protected_even_if_repo_policy_forgets`
  覆盖（改 `.witnessloop/policy.json` 不写事件 → `check` 断言 `EXIT_FAIL` + 「受保护路径被写入」）。

**I3（去重 + gate_ref 语义）— 已落实。**
- (a) **已抽** `initcmd.conflicting_files`（`initcmd.py:108-121`），两处冲突判定（首次 `:163`、
  已接入 `:237`）**都用它**；`grep` 确认无残留的重复内联推导（仅存的 `for rel, ... in desired.items()`
  在 `build_manifest:82` 与写入循环 `:177`，非冲突逻辑）。
- (b) **已改**：`cli.py:45` `--gate-ref` 默认 `None`；`initcmd.py:156`
  `gate_ref = args.gate_ref or ledger_gate_ref(manifest_path) or C.DEFAULT_GATE_REF`，
  新增 `ledger_gate_ref`（`:124-134`，坏台账/缺键 → None）。
  **实测**（`/tmp` 临时仓，真跑 CLI）：① `init --gate-ref acme/...@v9` → 台账与 caller 均为 `@v9`；
  ② 不带 flag 重跑 → 「幂等」exit 0，台账仍 `@v9`；③ 显式不同 `--gate-ref` → 「冲突」exit 1 且打 diff。
- (c) **两条回归测试真覆盖**：`test_rerun_without_gate_ref_after_custom_is_idempotent`（不带 flag 幂等、
  台账沿用 custom——修复前默认 `@v1` 会误判冲突，**修复前必红**）、
  `test_rerun_with_explicit_different_gate_ref_conflicts`（显式不同 → 冲突）；二者均过。

### 新问题

- 无**须修**问题。一处**观察性 nit**（不影响裁定）：`test_rerun_with_explicit_different_gate_ref_conflicts`
  所测的「显式不同 gate-ref → 冲突」在**修复前即已成立**，故它是**回归守卫**而非「修复前必红」的新回归测试；
  I3(b) 的真正红-先行测试是前一条。可选加注释点明，非缺陷。

### 测试结果

- `export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q` → **356 passed**（较 R1 的 354 增 2，即新增回归测试）。
- `tests/test_init_policy.py` 单独 13 passed；两条新增测试单独 2 passed。

### 结论

- I1 已消矛盾（spec + proposal + design 三处对齐、且补正向 Scenario 有测试背书）、I2 勾选如实、I3 去重与
  gate_ref 沿用台账**均落实且实测通过**，无引入新问题 ⇒ **verdict = PASS**，可进 §6 收尾
  （`manifest build` × 3 → `check` 绿）。
