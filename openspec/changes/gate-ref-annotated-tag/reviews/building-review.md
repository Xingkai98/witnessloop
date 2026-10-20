# Building 实现后独立审阅: gate-ref-annotated-tag（第 1 轮）

## Reviewer

- run id: `building-reviewer-gate-ref-annotated-tag-98b97b7046e9`
  （`WITNESSLOOP_RUN_ID` / `WITNESSLOOP_REVIEWER_RUN_ID` 均未设置；按
  `templates/review-loop.md`「怎么取 run id」的确定性兜底
  `<stage>-<role>-<change id>-<HEAD 前 12 位>`，HEAD = `98b97b7046e9`。）
- 时间: 2026-10-20T10:07:48Z（审阅跨度约 09:36–10:08Z；含低 nit 复核）
- 被审 revision: `98b97b7046e98508470345ce081f7189c6c4269c`（`HEAD` = `origin/main`；
  被审内容为**工作树内未提交修改**——6 个 `M` 文件 + untracked change 目录）。
- 被审范围: `tasks.md` / `design.md` / `proposal.md` / `specs/gate-ref-pinning/spec.md`、
  `reviews/grill-design.md` / `reviews/grill-adversarial.md`、`.github/workflows/gate.yml`、
  `src/witnessloop/constants.py`、`tests/test_gate_workflow.py`、`README.md`、
  `docs/gate.md`、`docs/design.md`，以及自举计划（tasks F1/G2）。
- 方法: **零记忆、只读**。不读作者会话或前序结论；只以仓内文本、`git show origin/main:…`
  的旧实现、`/tmp` 副本实跑、本机 uv 0.12.1/0.13.1/0.13.2/0.13.3、`gh` 可见的真 CI run、
  `pytest`、`witnessloop check` 与实际 `sh` 执行解析 step 为准。默认立场：实现有错，逐条证伪。
- 材料变更提示: 审阅期间 `tasks.md` / `design.md`（`09:49:24Z`）、`gate.yml`
  （`09:57:19Z`，注释）、`docs/gate.md` / `tests/test_gate_workflow.py` / `tasks.md`
  （`10:05:53–55Z`，低 nit 修复）被**并发修改**。作者随后声明内容冻结（此后只有 F1 的
  caller/台账/事件簿记改动，不再动 tasks/design/spec/tests/docs）。本报告以**冻结后的最终
  内容**为准；实现逻辑未变（矩阵重跑逐行一致），6 项 low/nit 修复已逐条复核（见登记表）。
  建议 manifest 绑定前 content 保持冻结（见 R0-1）。

## 本轮判定（verdict）

**PASS（初次开批为空）。**

逐条复核 tasks A1–D5 真实存在；冻结后实跑 **768 passed**；issue #42 核心回归在旧实现上**必红**
（`ref=00192abe…`，即 tag object）；新实现在 annotated tag / 分支 / commit / 兜底 / 降级 /
fail-closed / 空 ref 各形态上与 spec 一致。**0 条 medium+**；登记 4 条 low + 3 条 nit
（其中 R0-2..R0-6 已在低 nit 复核前修复并逐项复核通过，均不阻塞）。

### 第 1 轮 · 批次

| id | severity | 锚点（文件:行） | 问题 |
|---|---|---|---|
| — | — | — | （空：0 条 medium+） |

### 第 1 轮 · 验证

（空批，无需修复验证。）本轮完整复核结论：

| 维度 | 结果 | 证据 |
|---|---|---|
| 任务逐项验证 | 通过 | A1–A4、B1–B4、C1–C4、D1–D5 的实现/文档真实存在（见下「任务逐项对账」）；E/F/G 未勾属「后续批」，不是缺陷 |
| 正确性 | 通过 | 旧/新解析器同一输入矩阵对比（见下）；tag/分支/commit/兜底/降级/空 ref 行为与 design D1/D2/D4 一致 |
| Spec 对齐 | 通过 | spec 的 6 步顺序、四类来源文案、空/纯空白守卫、repository 守卫优先级均逐条对上 |
| 冗余度 | 通过 | 解析逻辑单点实现；测试复用 `_run_resolve` 助手；常量与 gate.yml 由既有测试钉同源 |
| 测试覆盖 | 通过 | 核心回归在**旧实现上实测红**，且覆盖分支/commit/边界/空 ref；测试由 `.github/witnessloop-tests.txt`（`uv run pytest -q`）在门禁 job 执行 |
| 安全性 | 通过 | `run:` 无 `${{ }}` 插值；外部值只经 env 读、无 `eval`；repository 守卫先于 workflow_ref；空 ref 非零退出 |
| 可维护性 | 通过 | WHY 文案与 D4 表一致；前缀精确剥离有注释说明；常量「字面量族」关系写清 |
| CI 完整性 | 通过 | 未删/改任何既有 step，未引入 `continue-on-error`，adopter tests 接线未动；`.github/witnessloop-tests.txt` 仍为 `uv run pytest -q` |

门禁结论（如实记录）：`uv run witnessloop check --base origin/main --head HEAD` 本地输出
`0 个变更文件，0 个 change 目录` → `通过`；这是因为改动**未提交**，diff 为空，判定是**空洞的**，
不作为本轮证据，也未据此报缺陷（按任务书要求）。

### 第 1 轮 · 下一批（deferred）

| id | severity | 锚点 | 问题 | 来源 | 延后理由 |
|---|---|---|---|---|---|
| — | — | — | （空） | — | — |

### low / nit 登记（累积）

| id | severity | 锚点 | 处置（登记不修） | 理由 / 证据 |
|---|---|---|---|---|
| R0-1 | low（流程） | `tasks.md` / `design.md` / `gate.yml` mtime | **登记（content 已冻结）** | 审阅期间材料被并发修改（09:49:24Z tasks/design、09:57:19Z gate.yml 注释、10:05:53–55Z low-nit 修复）。作者随后声明冻结；本报告按冻结后的最终内容复核，实现逻辑未变（矩阵重跑逐行一致），结论不变。manifest 的 `tasks_hash`/`spec_hash` 绑定前应保持冻结。 |
| R0-2 | low | `tasks.md:36-38`（C3） | **已修（复核通过）** | C3 现写「**13 条失败**（当时测试集；最终测试集下复跑为 **17 failed / 31 passed**，其中 2 条是兜底常量 `v1.7.0→v1.7.1` 的预期漂移）」。与我在 /tmp 副本的独立复跑逐字一致；核心用例红因（`ref=00192abe…`）未变。 |
| R0-3 | low | `docs/gate.md:62` | **已修（复核通过）** | 两行 `###` 已合并为单行 `### 1.2 钉住 ref：一个入口、两处一致（issue #30；annotated tag 修正：issue #42）`，括号平衡、标题完整。 |
| R0-4 | low | `tests/test_gate_workflow.py:707` | **已修（复核通过）** | 新增 `test_resolve_fails_loudly_when_github_output_is_undefined`：移除 `GITHUB_OUTPUT` 后 `rc != 0` 且 stderr 含 `GITHUB_OUTPUT`。全量测试 767 → **768 passed**（+1）。 |
| R0-5 | nit | `.github/workflows/gate.yml:80-85`；`design.md:102-104` | **已修（复核通过）** | 表述已限定为「**可能缺失**的 job/input 变量一律 `${VAR:-}` 读；两个常量 `WL_REPO_SLUG` / `WL_FALLBACK_REF` 由 workflow 的 `env:` 恒定提供」。与代码的两种读法一致，不再自相矛盾。 |
| R0-6 | nit | `.github/workflows/gate.yml:157` | **已修（复核通过）** | 文案改为「解析后为空或纯空白——拒绝写出空 ref（会装默认分支）」；行为不变（空/空白 ⇒ EXIT=1、不写 `ref=`）。 |
| R0-7 | nit | `README.md:20,205-207`；`docs/gate.md:100` | **按计划（复核通过）** | README 未改（diff 仍为 18+/8-）；发布窗口仍由 `design.md:208-209`（D6）、`tasks.md:73-74`（G1）与 Release 正文承担，属已声明时序。 |

**低 nit 复核（2026-10-20T10:07:48Z）**：R0-2..R0-6 五项已修并逐项复核通过，R0-7 按计划由
Release 正文承担；全量 `uv run pytest -q` → **768 passed in 40.77s**；解析 step 边界矩阵
重跑与首次逐行一致（annotated tag → `refs/tags/v1.7.0`；分支 / commit → commit sha；
空 fallback / 空白输入 → EXIT=1 且不写 `ref=`）。⇒ 这些低 nit 修复**不改变**本轮
0 条 medium+ 的结论，出口保持 **PASS**。

### 第 1 轮后 · 收口确认

- 审阅时间: 2026-10-20（09:36–10:08Z，含低 nit 复核）；范围：tasks/design/spec/reviews +
  全部实现面 + 自举计划。
- 结论: **0 条 medium+ ⇒ PASS**。E2 无修复项；可勾 E1 并进入 F2（F1 的 caller/台账簿记已在
  冻结后落盘，不属于本轮 low/nit 复核面）。
- 低 nit 复核：R0-2..R0-6 已修并逐项复核通过，R0-7 按计划由 Release 正文承担；
  `pytest -q` → **768 passed**，结论不变。

## 独立实测证据（原始输出摘录）

### 1. 全量测试与门禁

```
$ /home/happy/.local/bin/uv run pytest -q      # 实现面（低 nit 修复前）
767 passed in 68.26s (0:01:08)

$ /home/happy/.local/bin/uv run pytest -q      # 冻结后（含 R0-4 新增用例）
768 passed in 40.77s

$ /home/happy/.local/bin/uv run witnessloop check --base origin/main --head HEAD
check：本包来源（自报，尽力而为）：requested_revision=<未知>，commit_id=<未知>
check：基线 origin/main...HEAD，0 个变更文件，0 个 change 目录
check：通过 ✓
EXIT=0        # 注意：改动未提交 ⇒ diff 为空，此「通过」是空洞的
```

### 2. 旧实现必红（把新测试文件放进 /tmp 副本，配 `origin/main` 的旧 gate.yml）

```
$ git show origin/main:.github/workflows/gate.yml > /tmp/review42/copy/.github/workflows/gate.yml
$ cp tests/test_gate_workflow.py /tmp/review42/copy/tests/
$ cd /tmp/review42/copy && .venv/bin/python -m pytest -q tests/test_gate_workflow.py
17 failed, 31 passed

$ pytest -q ...::test_resolve_annotated_tag_uses_the_tag_ref_not_the_tag_object_sha
E  AssertionError: assert '00192abe45d2...faad48c34fa26' == 'refs/tags/v1.7.0'
E    - refs/tags/v1.7.0
E    + 00192abe45d2d72a4389eccb202faad48c34fa26
1 failed
```

17 条中 2 条是旧 gate.yml 的兜底仍为 `v1.7.0`（常量迁移的预期漂移：
`test_resolve_constants_match_the_single_source` / `test_resolve_fails_closed_on_a_foreign_repository`），
其余 15 条是旧解析行为（含 issue #42 核心用例）。

### 3. 解析器边界矩阵（同一输入分别喂旧/新 `run:` 原文，`sh` 实跑）

```
case                     old                       new
annotated-tag            ref=00192abe…(tag object) ref=refs/tags/v1.7.0        （无 warning）
branch+sha               ref=6e2ec4d…              ref=6e2ec4d…                 （无 warning）
commit-pin               ref=6e2ec4d…              ref=6e2ec4d…                 （无 warning）
tag-name-@               ref=00192abe…             ref=refs/tags/v1@rc1
branch-@refs/tags+sha    ref=6e2ec4d…              ref=6e2ec4d…                 （未被误判为 tag）
tag-@refs/tags no sha    ref=rc                    ref=refs/tags/v1@refs/tags/rc
empty-tag-tail+sha       ref=6e2ec4d…(=旧)         ref=6e2ec4d… + warning
empty-head-tail+sha      ref=6e2ec4d…(=旧)         ref=6e2ec4d… + warning
refs/pull+sha            ref=00192abe…(=旧)        ref=00192abe… + warning（附原值）
path-mismatch+sha        ref=00192abe…(=旧)        ref=00192abe… + warning（附原值）
64-hex no sha            ref=v1.7.0(旧兜底)        ref=<64 hex>
uppercase-hex+sha        ref=6e2ec4d…(=旧)         ref=6e2ec4d… + warning
explicit                 ref=v2                    ref=v2（repository 不匹配也不影响显式值）
repo-mismatch+tagref     ref=v1.7.0                ref=v1.7.1 + warning（不落 workflow_ref）
undefined-env            ref=v1.7.0                ref=v1.7.1 + warning
whitespace-input         EXIT=0 ref=（空）          EXIT=1 + ::error::，不写 ref=
empty-fallback           EXIT=0 ref=（空）          EXIT=1 + ::error::，不写 ref=
whitespace-fallback      EXIT=0 ref=（空）          EXIT=1 + ::error::，不写 ref=
GITHUB_OUTPUT 未定义      EXIT=2                    EXIT=2（parameter not set，响亮）
```

### 4. uv 版本分界（独立安装、每次全新 `UV_CACHE_DIR`、真 GitHub 仓）

```
git: v1.7.0 = tag object 00192abe45d2d72a4389eccb202faad48c34fa26
             → peeled commit c9b281167ad20b63e4832ad9ab8510964a2adc60
uv 0.12.1  tag-object 00192abe…  EXIT=0  Building …@c9b2811…（安装成功）
uv 0.13.1  tag-object 00192abe…  EXIT=0  Building …@00192abe…（仍安装成功）
uv 0.13.2  tag-object 00192abe…  EXIT=1  Exact Git revision … does not match precise commit c9b2811…
uv 0.13.3  tag-object 00192abe…  EXIT=1  同上
uv 0.13.3  refs/tags/v1.7.0      EXIT=0  Building …@c9b2811… / witnessloop 0.1.0
```

### 5. 真 CI（`gh` 可见的 run 与其 annotation）

```
run 38928669316（witnessloop，caller @v1.7.0 annotated tag，gate 绿）：
  witnessloop 包 ref = 00192abe45d2d72a4389eccb202faad48c34fa26（来源：job.workflow_sha…）
run 39386712284（asterwynd，commit pin，gate 绿）：
  witnessloop 包 ref = c9b281167ad20b63e4832ad9ab8510964a2adc60（来源：job.workflow_sha…）
```

⇒ 旧 gate 在 annotated tag 下确实把 tag object 交给 uv；commit pin 下 `job.workflow_sha` 是
commit。两 run 的 job 级完整日志在本环境取不到（`gh run view --log` 空输出），
`WL_WORKFLOW_REF` 行以 design 引用与上述 notice 为准；tag object → commit 的关系已本地 git 验证。

### 6. 自举计划 F1 实跑（/tmp 仓库副本，不动仓内文件）

```
$ witnessloop init --root . --dry-run --gate-ref …gate.yml@98b97b7046e98508470345ce081f7189c6c4269c \
    --policy .witnessloop/policy.json
init：[dry-run] 将重写 .github/workflows/witnessloop.yml（→ …@98b97b70…）并同步台账
EXIT=0

$ witnessloop init --root . --gate-ref …gate.yml@98b97b7046e98508470345ce081f7189c6c4269c \
    --policy .witnessloop/policy.json
EXIT=0
caller: uses: Xingkai98/witnessloop/.github/workflows/gate.yml@98b97b7046e98508470345ce081f7189c6c4269c
ledger: gate_ref 同值；caller 条目 sha256 == 磁盘 sha256
不带 --policy ⇒ EXIT=1（policy 冲突）
```

⇒ F1 的命令、40 位全 sha、台账同步均可行；「caller 是非证据路径、`init-manifest.json` 在
不变集 ⇒ 需一条 `protected_path_write`、events 文件为 `A` 免事件」与
`src/witnessloop/policy.py` / `checkcmd._protected_writes` 一致。

### 7. G2 事件计数（静态核对，未实测未来 PR）

`src/witnessloop/policy.py` 的 `INVARIANT_PROTECTED_PATHS` 含
`**/reviews/*.manifest.json` 与 `**/workflow-events.jsonl`；`_protected_writes` 对 `M` 要求
解释事件、对 `A` 豁免。G2 的 `M` = `init-manifest.json`（1）+ 三份 manifest（3）+
events 文件自身（1）= **5 条**，与 tasks G2 一致；caller 不在受保护/`require_change_for` 面，
无需事件。三份 manifest 重建后仍绑定报告，orphan 规则（`contract._check_orphan_reports`）
可满足。**未实测**完整 G2 diff（依赖未来 PR）。

### 8. 任务逐项对账（只列需说明项）

- A1–A4：proposal/design/spec 齐备；A4 的 uv 分界已由本轮 §4 独立复现。
- B1：`evidence.grill_evidence_findings(reviews/grill-design.md)` → `[]`（Confirmed Decisions 7 条、
  每条带 `来源:`；`## Open Questions` =「（无）」）。
- B2–B4：对抗报告三轮收敛至 PASS；design §4 已含停轮门与 R2-1 记录。
- C1–C4：用例均存在；C3 的「13 条」计数见 R0-2（核心红已复现）。
- D1–D5：D1/D2 解析 step 与注释、D3 常量 `v1.7.1`、D4 文档均已落；D5 实测 768 passed。
- E1/E2、F、G 未勾：按 review-loop「批次 aware」属后续批，不是缺陷。

## 闭环出口

**PASS**（初次开批 0 条 medium+；4 low + 3 nit 已登记，其中 R0-2..R0-6 已复核修复，
R0-7 按计划由 Release 正文承担，均不阻塞）。
