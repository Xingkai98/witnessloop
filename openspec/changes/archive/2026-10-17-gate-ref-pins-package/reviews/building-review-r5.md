# building-review-r5 — gate-ref-pins-package

## Reviewer

- **角色**：独立、零记忆的**实现后**审阅（building / **B5** 轮）。本对话**不携带**该 change 的
  任何实现历史；`design.md` / `tasks.md` / `specs/` / 提交说明里的「已落库」「实测」「已收敛」
  一律当**待验证断言**处理。我不是作者，**未改写任何实现**，只产出本报告。
- **审阅对象（revision 绑定）**：worktree `/home/happy/wl-wt/archive-arrival-recognition`，
  分支 `gate-ref-pins-package/2026-10-16`，
  HEAD = `e168b521f634f56d3cf6ccd1326b74db4f33fcf8`（`git rev-parse HEAD` 原始输出）。
  上一轮（`reviews/building-review-r4.md`，**只读、未改**）针对 `58601b8`；本轮针对 `e168b52`
  （`e168b52` 的 parent 就是 `58601b8` ⇒ 相对上一轮**只多这一个提交**，已由 `git log --oneline -2` 核）。
- **验收标准**：`openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md`
  （5 条 Requirement）——规格是唯一判据，`design.md` / `tasks.md` 只作线索。
- **基线**：`PYTHONPATH=src python3 -m pytest -q` ⇒ **702 passed in 32.21s**（worktree 本体原始输出
  `702 passed in 32.21s`）。所有变异版在 `/tmp/br5/{m1..m5,n1..n4}` 上跑（m1–m5 跑**全量**，
  n1–n4 只跑对应测试文件）。
- **方法**：
  1. `git show --numstat e168b52` 逐条核对上一轮「问题清单」**B4-1…B4-3** 的**落库实体**
     （不信处置表/提交说明，只信 diff + 代码行 + 测试行）；
  2. **动手变异 5 组**（M1–M4 探 B4 三条钉子是否承重，M5 探新缺口）；另 **N1–N4** 四组
     定向变异，验证判据② 所依赖的 R1/R2/R3/R5 钉子**也真能红**；
  3. **穷举矩阵**：B4 的 36 格**重跑一遍**（同一 `matrix.py`），再跑一版**48 格**（多一类
     `content=bin` = caller 为不可解码字节），逐格记录退出码、条目数、`uninit` 结果与 stdout/stderr 签名；
  4. 另跑 11 格**补充面**（`--gate-ref` 之外：plain `init`、policy 漂移、条目缺失 × dry/real）；
  5. 文档对照：本 commit 是否改动用户文档（`--numstat` 决定）+ 文档里引用的文案是否还成立。
- **快照纪律**：全部实验在 `/tmp/br5/`（`git archive HEAD | tar -x` 解出的副本，**无 `.git`**；
  已确认 `/tmp/br5/base/.git` 不存在）。真仓内**未**做任何 commit / reset / tag / push。
- **证据约定**：每条结论带 `文件:行号` 或「命令 + 原始输出」。**没复算的一律标「未验证」**。

## 审阅结论

**上一轮唯一的放行条件 B4-1 确实落了库，落的正是那条，而且钉子真能红。** 另两条低危项
（B4-2、B4-3）也落了库，且各自有承重钉子（`--numstat` + 代码行 + 变异三重核对）。

三件事都有原始证据：

1. **B4-1**：`initcmd.py:598-600` 现在把收窄后的字典**交给** `conflicting_files`，`ignore` 过滤
   **不再**排在抛点之后（旧写法 `conflicts = [item for item in conflicts if item[0] not in ignore]`
   已删除，`--numstat` 记为 `10/7` 与之一致）。把它**变异回旧写法**（M1）⇒
   `test_an_undecodable_caller_does_not_fork_dry_run_from_the_real_run` 红，
   失败现场正是 `assert 1 == 0`（`tests/test_init_gate_ref.py:680`）即 dry-run 退 1 / 真跑退 0。
   **48 格矩阵**（含新增的 `bin` 面）`dry/real exit mismatch keys: []`——上一轮那条分叉**已消除**。
2. **B4-2**：`changing_ref` 现在全函数**只求值一次**（`grep -n changing_ref` 只有 `:197` 一处定义 +
   `:200`/`:210` 两处读）。M2（把求值挪到 `_set_ledger_gate_ref` 之后）⇒ 只打红
   `test_explicit_different_ref_rewrites_caller_and_syncs_the_ledger`，且失败现场**逐字复现**那句假话
   （`已补齐台账里的 … 条目（ref 本来就是 …@v9.9.9，未改）`）⇒ 求值**时机**被钉死、**唯一性**是真事实。
3. **B4-3**：两条新钉子都在且承重——M3（删 `:214` 真跑 print）⇒ `test_the_backfill_branch_prints_its_own_line`
   红；M4（让 `caller_retarget_refusal` 对同 ref 短路）⇒ `test_the_v1_refusal_also_fires_for_a_same_ref_request` 红。

**本轮未发现新的行为缺陷。** 重点复核的两条都过关：(a) `ignore` 提前生效**没有**造成「本该报的冲突被漏掉」
——`ignore` 全局只有 `initcmd.py:439` 一个调用点，且该调用点只在 `sync_caller_gate_ref` 返回非 `None`
（= 确实会/将重写 caller）时才到达，47 格矩阵与 11 格补充面的退出码/台账/内容逐格自洽（见维度四）；
(b) dry-run 与真跑在**含新增拒绝面**的 48 格上**逐格同退出码**。另发现两条**无行为后果**的
覆盖/边界项（B5-1 不可达的空后缀、B5-2 一条 print 零覆盖）——**它们不构成放行条件**，理由见 Verdict。

## 逐维度结论

### 维度一：上一轮放行条件与低危项逐条落库核对（`--stat` + 实体）

`git show --numstat e168b52` 原始输出：

```
274	0	openspec/changes/gate-ref-pins-package/reviews/building-review-r4.md
10	7	src/witnessloop/initcmd.py
59	0	tests/test_init_gate_ref.py
```

（`tests/` 的改动**全是纯新增**（59 行 0 删）；代码改动面只有 `initcmd.py` 一个文件、共 17 行；
`building-review-r4.md` 是上一轮报告的**归档新增**。**本 commit 未触碰** `README.md` / `docs/gate.md` /
`gate.yml` / `checkcmd.py` / `uninitcmd.py`。）

| 上轮项 | 自述 | 实体核对（`--stat` + 代码/测试行） | 判定 |
|---|---|---|---|
| **B4-1**（放行条件：`ignore` 在 `conflicting_files` **之后**才生效） | 已落 | `initcmd.py:594-603`：`conflicting_files(root, {rel: want for rel, want in desired.items() if rel not in ignore})`——收窄后的字典**进**函数；旧的「先全量再滤」那行**已删除**（`--numstat` `-7` 与删掉注释块 + 那两行一致）。钉子：`tests/test_init_gate_ref.py:668-681`（断言 `dry == real == C.EXIT_PASS` 且 caller 真被换成 `NEW_REF`）。变异 **M1** ⇒ `1 failed, 701 passed`，失败现场 `assert 1 == 0`（dry-run 退 1） | **落库，且是那条** ✓（钉子能红） |
| **B4-2**（`changing_ref` 重复求值，洁癖） | 已落（commit msg：只算一次） | `initcmd.py:193-197`：求值**收敛到 `:197` 一处**，`:205-215` 的旧第二处**已删除**；`grep -n changing_ref src/witnessloop/initcmd.py` 只回 `197`（定义）/`200`/`210`（读）。新注释 `:193-196` 把「为什么必须在 `_set_ledger_gate_ref` 之前」与「dry-run 与真跑共用同一个值」两点都写明 | **落库，且是那条** ✓ |
| **B4-3**（两处覆盖缺口） | 已落（commit msg：补两条钉子） | 缺口①：`:214` 真跑 print ⇒ 新钉子 `tests/test_init_gate_ref.py:684-700`（断言 stdout 含 `已补齐台账里的 <path> 条目`，与 note 行 `台账里的 <path> 条目已补齐` **语序不同**，所以只钉 print）。缺口②：`absent\|absent\|same` ⇒ 新钉子 `:703-724`（走 `OLD_REF` 而非 `NEW_REF`）。变异 **M3/M4** 各自打红对应那条 | **落库，且是那条** ✓（两条钉子都能红） |

### 维度二：变异验证（承重性，逐条都跑全量或定向）

| 变异 | 改什么 | 结果（原始输出） | 说明 |
|---|---|---|---|
| **M1** | 把 `:598-600` 改回旧写法（先 `conflicting_files(root, desired)`，再事后 `[... for item in conflicts if item[0] not in ignore]`） | **1 failed, 701 passed** —— `test_an_undecodable_caller_does_not_fork_dry_run_from_the_real_run`；`assert 1 == 0`（`test_init_gate_ref.py:680`） | 上一轮分叉**复现**⇒ B4-1 的钉子**真能红且只打红自己** |
| **M2** | 在 `_set_ledger_gate_ref` 之后重算 `changing_ref`（= B3-1 之前的旧顺序） | **1 failed, 701 passed** —— `test_explicit_different_ref_rewrites_caller_and_syncs_the_ledger`；失败现场 stdout 逐字为 `init：已补齐台账里的 … 条目（ref 本来就是 …@v9.9.9，未改）` | 求值**时机**这条不变量被钉住；同时证明 B4-2 的「只算一次」没有削弱它 |
| **M3** | 删掉 `:214` 的真跑 `已补齐…` print | **1 failed, 701 passed** —— `test_the_backfill_branch_prints_its_own_line`（stdout 只剩 note 行） | B4-3 缺口① **已闭环** |
| **M4** | 在 `caller_retarget_refusal` 里对「台账 `gate_ref` == 本次 ref」加一条早退 `return None` | **4 failed, 698 passed** —— 含 `test_the_v1_refusal_also_fires_for_a_same_ref_request`；而走 `NEW_REF` 的老用例 `test_no_caller_entry_and_no_file_refuses_loudly` **仍绿** | B4-3 缺口② **已闭环**（同 ref 是一根**独立**的轴） |
| **M5** | 删掉 `:203` 的 **dry-run** `将补齐…` print | **702 passed（全绿）** | **新缺口 B5-2**：与 B4-3 刚修掉的那条（`:214`）是**对称的一对**，B4-3 只修了真跑那半 |
| **N1** | 在 `gate.yml` 的 resolve step **之前**插一个 dummy step | **1 failed, 33 passed** —— `test_resolve_step_is_the_first_step` | 判据② 用：R2「必是第一个 step」的钉子承重 |
| **N2** | 把 `docs/gate.md` 的 `本 change **刻意不修**它` 改成 `不修它` | **1 failed, 49 passed** —— `test_gate_documents_the_unprotected_caller_boundary` | 判据② 用：R5 的文档钉子承重 |
| **N3** | 把 `gate.yml` 的 `elif [ -n "${WL_WORKFLOW_SHA:-}" ]` 改成 `elif false`（不再以 sha 为缺省） | **1 failed, 33 passed** —— `test_resolve_prefers_the_reusable_workflows_own_sha` | 判据② 用：R1 的缺省来源钉子承重 |
| **N4** | 把 `checkcmd.py` 的 `return _text("requested_revision"), _text("commit_id")` 两个字段**对调** | **4 failed, 8 passed** —— `test_parses_the_real_payload` 等 4 条 | 判据② 用：R3 的自报字段钉子承重 |

### 维度三：穷举矩阵（36 格重跑 + 48 格含新增拒绝面）与 11 格补充面

**(a) B4 的 36 格原样重跑**（`/tmp/br5/matrix.py`，在 `<HEAD>` 原样副本上）：

```
TOTAL ROWS: 36
dup>1 count: 0
dry/real exit mismatch keys: []
```

与 r4 同结论 ⇒ 本 commit **未回退**任何既有格，`dup>1`（B2-1 的重复条目回归）仍**不可达**。

**(b) 48 格（多一类 `content=bin` = caller 字节 `b"\xff\xfe not utf-8 \xff"`）**，`/tmp/br5/matrix2.out`：

```
TOTAL ROWS: 48
dup>1 count: 0
dry/real exit mismatch keys: []
```

新增的 12 格（`bin`）逐格如下（原始行）：

```
| present | present | same | bin | real | 1 | 1 | same | BIN | 1 | …policy.json | NODEC+REFUSE |
| present | present | same | bin | dry  | 1 | 1 | same | BIN | 1 | …policy.json | NODEC+REFUSE |
| present | present | diff | bin | real | 0 | 1 | new  | NEW | 0 |  | RWT |
| present | present | diff | bin | dry  | 0 | 1 | same | BIN | 1 | …policy.json | - |
| present | absent  | diff | bin | real | 0 | 1 | new  | NEW | 0 |  | RWT |
| present | absent  | diff | bin | dry  | 0 | 0 | same | BIN | 0 |  | - |
| present | self    | *    | bin | *    | 1 | 1 | same | BIN | 0 |  | REFUSE+SELF |
```

⇒ **上一轮 B4-1 的那两格（`present|…|diff|bin`）现在 real/dry 都是 0**，而**不是** 0/1。
矩阵脚本直接打印的 `dry/real exit mismatch keys: []` 是逐格比对的结论，不是抽样。

**(c) 11 格补充面**（`/tmp/br5/probe_extra_faces.py`，覆盖 48 格矩阵**够不到**的轴：
不带 `--gate-ref` 的 plain `init`、policy 漂移、条目缺失）：

```
=== caller bytes undecodable (bin) ===
  OK  plain init (no --gate-ref)                        real=1[NODECDRIFT] dry=1[NODECDRIFT]
  OK  plain init, entry=absent                          real=1[NODEC]       dry=1[NODEC]
  OK  plain init, entry=self                            real=1[NODEC]       dry=1[NODEC]
  OK  --gate-ref <same>                                 real=1[NODECREFUSE] dry=1[NODECREFUSE]
  OK  --gate-ref <diff>                                 real=0[]            dry=0[]
  OK  --gate-ref <diff> + policy drift                  real=1[DRIFT]       dry=1[DRIFT]
  OK  --gate-ref <same> + policy drift                  real=1[NODECREFUSE] dry=1[NODECREFUSE]
  OK  --gate-ref <diff>, entry=absent                   real=0[]            dry=0[]
  OK  --gate-ref <same>, entry=absent                   real=1[NODECREFUSE] dry=1[NODECREFUSE]
=== caller readable but hand-edited (hand) — control ===
  OK  plain init, content=hand                          real=1[DRIFT]       dry=1[DRIFT]
  OK  --gate-ref <diff>, content=hand                   real=0[]            dry=0[]
```

**结论**：在 36 + 12 + 11 = **59 格**上，`--dry-run` 与真跑**没有一格退出码分叉**。

### 维度四：`ignore` 提前生效是否会**漏报**本该报的冲突（本轮重点）

从代码上确认题设前提——「`ignore` 只有 caller 一条，且只在确实会重写 caller 的调用点传入」：

1. **全局唯一调用点**：`grep -n "ignore=" src/witnessloop/initcmd.py` 只回
   `439:            ignore=(C.GATE_WORKFLOW_PATH,)`——`_already_initialized` 的两个调用点里
   （`:423` 与 `:434`）只有 `:434` 传 `ignore`，传的**只有 caller 一条**。
2. **到达 `:434` 的条件**：`:417-421` 的 `rewritten = sync_caller_gate_ref(...) if args.gate_ref else None`，
   `:422` 的 `if rewritten is None:` **早退**到不传 `ignore` 的 `:423`。⇒ 传 `ignore` **当且仅当**
   `args.gate_ref` 为真 **且** `sync_caller_gate_ref` 返回了非 `None` 的说明串。
3. **返回非 `None` 意味着什么**：`sync_caller_gate_ref` 的五个 `return None`（`:167`/`:169`/`:181`/`:188`/`:191`）
   已把「台账坏 / 不是对象 / ref 相同且条目在 / `created_files` 非数组 / 盘上没有 caller 文件」
   全部排除；能走到 `:199` 之后，`changing_ref=True` 时**真跑一定重写**（`:207`），
   `changing_ref=False`（补齐态）时**盘上内容必已等于本次期望**——因为
   `:262-278` 的 `caller_retarget_refusal` 已经在所有写入之前读过盘：ref 相同 ∧ 文件在 ∧ 内容≠期望
   ⇒ 那里就 `return` 一句拒绝、`:393-395` 直接退 1，**根本到不了** `sync`。⇒ 补齐态被 `ignore`
   滤掉的那条轴**本来就不会产生 conflict**。
4. 因此 `ignore` 唯一可能的「过抑制」是：**dry-run 下** caller 会被改而磁盘未改。这不是漏报而是
   **规格明写**的语义（`spec.md:119-120`：「SHALL 不报冲突（那条冲突正是这个动作要消掉的）」），
   且 `:429-433` 的 `handled` 文案会**按 dry-run 与否**分叉说明「未落盘 / 已落盘、不回滚」。
5. 矩阵佐证：59 格里**没有**「caller 轴被滤掉、而 real 分支其实不重写」的格
   （`sig` 列里凡 `diff` 格 real 侧恒为 `RWT`；`same` 格 real 侧恒为 `BACKFILL`/`REFUSE`，无静默）。

**结论**：提前生效**没有**引入新的漏报面；它只把「不可解码的 caller」从「先抛后滤」变成「先滤不读」，
这正是 B4-1 要的那一处改动。

### 维度五：前几轮登记「不修」项的现状复核（复算，非转抄）

| 登记项 | 本轮复算（命令 + 原始输出） | 结论 |
|---|---|---|
| `created_files` 元素**非对象**仍崩 | `/tmp/br5/probe_regressions.py`：分别把 `"not-an-object"` / `None` / `["nested"]` / `42` 追加进 `created_files` ⇒ 一律 `exit=1` + `witnessloop：内部错误（AttributeError: … object has no attribute 'get'）`（抛点 `initcmd.py:541` `rel = entry.get("path")`，本 commit 未触碰该循环） | **仍如登记所说**（既有；fail-closed；dry/real 同码） |
| 同上，**台账根不是对象**（新加的样本） | 把台账整体写成 `[1,2,3]` / `"str"` / `42` ⇒ real 与 dry **都** `exit=1` + 「内部错误（AttributeError）」 | **与登记同族**（`_already_initialized:524` 直接 `.get`；两条路径同码 ⇒ 不违反 Y1） |
| **caller 路径是个目录**（新加的样本） | 把 `.github/workflows/witnessloop.yml` 换成目录 ⇒ `exit=1` + 「内部错误（IsADirectoryError）」，real 与 dry **都** 1；plain `init`（不带 `--gate-ref`）**同样**崩 | **既有**（抛点在 merge-base 就已存在的 `sha256_bytes(path.read_bytes())`；本 change 未引入；fail-closed）⇒ 归入 B5-3 |
| `…@refs/heads/` 空后缀 | **本轮改为实跑**（直接抽取 `gate.yml` 的 resolve step 交给 `sh`）：`…@refs/heads/` 与 `…@refs/tags/` ⇒ `rc=0`、`ref=`（**空**）、**无 `::warning::`**；对照组 `…@refs/pull/30/merge` ⇒ `ref=v1` + 有 warning | **仍如登记所说**，且比 r4 的纯代码复核更硬（见 B5-1） |
| `--gate-ref ""` 等价于不给 | 探针：`init --gate-ref ""` ⇒ `exit=0` + `init：已接入 witnessloop（幂等，无改动）。`，caller 与台账**字节不变**（`:372` 的 `args.gate_ref or …` 与 `:387` 的 `if args.gate_ref:` 都把空串当假值） | **仍如登记所说** |
| `uninit` 对手改台账的**半回滚** | 矩阵 `absent\|self\|*` 四格 ⇒ `uninit` **exit=1**，`.witnessloop/` 剩 `init-manifest.json`（`matrix2.out` 的 `left` 列逐格打印）；本 commit `--numstat` **无** `uninitcmd.py` | **仍如登记所说**（既有、非本轮引入） |

### 维度六：文档/规格一致性（判据③）与 Requirement 追溯（判据②）

- **本 commit 未改动任何用户文档**（`--numstat` 只有 `initcmd.py` + `tests/` + 报告归档）⇒
  没有新增「文档承诺 ≥ 实现」的漂移面。
- 文档里出现的 `无法解码`（`README.md:248`、`docs/gate.md:363`）都是 **`check` 的事件文件**那条
  finding 的引文；本 change 新增的是 **`init` 的 caller 无法解码**（`initcmd.py:267-271`），
  **两条不同的消息**，不存在引文失配。
- `docs/gate.md:62-155`（§1.2）逐条与实现对照：解析 step「在第一个 step」⇒ `gate.yml:58`（第一个 step，
  N1 已钉）；`init --gate-ref` 的两步顺序 ⇒ `test_gate_recipe_puts_the_cli_upgrade_before_the_ref_change`；
  冲突文案引文 ⇒ `initcmd.py:610-620` 逐字相符。
- `design.md:461` 的 Y1 行把 `ignore` 描述为「同时作用到**漂移循环**」。实现**还**把它作用到了
  `conflicting_files` 的**读点**（`:598-600`）。这不是「承诺 ≥ 实现」——那句话没被证伪
  （`ignore` 确实作用到漂移循环，`:565`），只是**没写全**；且 B4-1 修复后 Y1 的**不变量**在
  不可解码面上也成立了。
- **判据② 的追溯（5 条 Requirement 都有实现 + 钉子，且钉子承重）**：

| Requirement | 实现 | 钉子 | 承重性证据 |
|---|---|---|---|
| R1 包版本缺省取自 `job.workflow_sha` | `gate.yml:67-109`（`elif [ -n "${WL_WORKFLOW_SHA:-}" ]` @ `:84-86`） | `tests/test_gate_workflow.py:357` `test_resolve_prefers_the_reusable_workflows_own_sha` | **N3** ⇒ 红 |
| R2 实际 ref 在 CI 日志可见（且是**第一个 step**） | `gate.yml:58-109`（`::notice::` @ `:109`） | `tests/test_gate_workflow.py:324/552` | **N1** ⇒ `test_resolve_step_is_the_first_step` 红 |
| R3 `check` 自报包 ref（尽力而为） | `src/witnessloop/checkcmd.py:30-89` | `tests/test_check_package_ref.py`（12 条） | **N4** ⇒ 4 条红 |
| R4 单一显式升级动作（本 change 主体） | `initcmd.py:149-215` / `:218-298` / `:342-441` / `:494-632` | `tests/test_init_gate_ref.py`（34 条） | **M1–M4** ⇒ 各打红对应那条 |
| R5 caller 不受保护的边界如实登记 | `docs/gate.md:538-556`（§7.1） | `tests/test_docs.py:268` | **N2** ⇒ 红 |

### 未验证（明确登记，不计入问题清单）

1. **R1-S1 的端到端 Then**（`job.workflow_sha` = 被复用文件自己的 commit）：GitHub Actions 语义，
   本工作区无 Actions，**未复算**（与四轮同一登记）。
2. **真 `uvx` 安装落的 `direct_url.json`**：仍是抄录载荷 + 手造 dist-info 覆盖读取环，**未**端到端验证。
3. **GHES 上 `job.*` 不可用**、**fork 判据必要不充分**：依据 spec/design 登记与 GitHub 文档，未实测。
4. **`docs/gate.md §1.2` 的 A/B/C 三条实跑主张**：本轮未重跑（改动不在这三条所指路径上）。
5. **`v1.7.0` 发布后的行为**：时序上不可验证。
6. **R1/R2/R3/R5 的钉子只各做了一条定向变异**（N1–N4），未穷举其全部用例；R4 之外的
   Scenario 行为复核沿用前几轮结论。
7. **`…@refs/heads/` 空后缀的「上游可达性」**：本轮**实跑**确认了脚本行为（B5-1），
   但「真 CI 里 `job.workflow_ref` 是否可能给出这个形态」**未验证**——我按 git 语义判断为不可达。

## 问题清单

> 排序：行为/边界在前，覆盖/健壮性殿后。**B5-1…B5-3 三条均为非阻塞**，理由见 Verdict。
> 已闭环的 B4-1/B4-2/B4-3 只在下面第一段登记，不重复列条目。

**已闭环（本轮复核确认）**：**B4-1** `ignore` 提前生效（`:598-600`，M1 复现旧分叉、48 格矩阵 `mismatch []`）；
**B4-2** `changing_ref` 单点求值（`:197`，`grep` 唯一，M2 打红且复现假话）；
**B4-3** 两条钉子（`:684` / `:703`，M3/M4 各自打红）。

### B5-1 · 边界（fail-open）· 低 —— `…@refs/heads/` / `…@refs/tags/` 空后缀 ⇒ `ref` 为空、**无 warning**、退出 0

- **位置**：`.github/workflows/gate.yml:88-89` 与 `:91-92`
  （`REF="${WL_WORKFLOW_REF##*@refs/heads/}"` 在空后缀下得**空串**，且**不**置 `FAILED`）。
- **证据（本轮实跑，非代码阅读）**：把 resolve step 的 `run` 原文交给 `sh` 跑，`WL_WORKFLOW_REPOSITORY=REPO_SLUG`：
  ```
  …@refs/heads/ (空分支名)   rc=0  ref=['ref=']        warning=False
  …@refs/tags/  (空 tag 名)  rc=0  ref=['ref=']        warning=False
  …@refs/pull/30/merge       rc=0  ref=['ref=v1']      warning=True
  ```
  后者是 spec 明列的畸形样本（处理正确）；前两者**静默**给出空 ref。
- **为什么是问题**：空 ref 会让 `uvx --from git+…@` 装**默认分支**——正是
  `tests/test_gate_workflow.py:454` 的 docstring 点名要防的那件事
  （「**任何输入下都不得为空**」），而该用例的样本清单（`:456-460`）**只有 4 条**，不含这两个形态；
  也偏离 spec 那句「仅接受 `refs/heads/<分支名>` 与 `refs/tags/<tag名>` 两种形态」
  （空分支名不是 `<分支名>`）。属本 change 新增面（main 的 `gate.yml` **没有**解析 step，
  `git show main:.github/workflows/gate.yml` 可核）。
- **为什么仍非阻塞**：**不可达**——`job.workflow_ref` 由真实 git ref 渲染，而 git 不允许
  名为 `refs/heads/`（空分支名）的 ref；规则①（显式 `with:`）先于本分支命中，接入方也构造不出来。
- **建议**（一处改动）：把 `*@refs/heads/*` 的匹配改成「`@` 之后必须还有非空内容」，
  或在该分支里补 `[ -n "$REF" ] || FAILED=…`。

### B5-2 · 覆盖缺口（print-only，**无行为后果**）· 低 —— dry-run `将补齐` 那条 print（`initcmd.py:203`）零覆盖

- **证据**：**M5**（删掉 `:203` 的 `print(f"init：[dry-run] 将补齐台账里的 … 条目（ref 未变）")`）
  ⇒ **`702 passed（全绿）`**。现有 `tests/test_init_gate_ref.py:613-633` 的 dry-run 断言
  （`"补齐" in out and "ref 未变" in out`）是靠 `:204` 的**返回串**（→ `:629` 由 note 打印）通过的，
  与 `:203` 那行是**两句不同的话**。
- **为什么是问题**：这与 B4-3 缺口①（真跑 `:214`）**完全对称**——B4-3 只修了真跑那半，
  dry-run 这半仍是空的。（**注**：`:201` 的 dry-run `将重写` print 已被
  `test_a_dry_run_ref_change_says_it_will_rewrite_not_backfill` 钉住，只有 `:203` 漏网。）
- **为什么无行为后果 / 非阻塞**：删掉它**不改任何退出码、不改任何落盘**；同一条信息仍由
  `:204` 的 note 经 `:629` 打给用户（矩阵里 `present|absent|same|same|dry` 实测 `exit=0` 且
  stderr/stdout 签名仍是 `BACKFILL`）。属纯文本覆盖缺口，与 B4-3 同族。
- **建议**：在 `test_the_repair_branch_says_it_only_filled_the_ledger` 里加一行
  `assert "init：[dry-run] 将补齐" in out`（或照 B4-3 的写法新增一条）。

### B5-3 · 既有健壮性 · 低（**与登记一致，非本轮引入**）—— 手改台账 / 手建目录 ⇒「内部错误」而非受控诊断

- **证据（探针原始输出）**：
  ```
  created_files 元素 = 'not-an-object' / None / ['nested'] / 42
      exit=1  err=witnessloop：内部错误（AttributeError: '<T>' object has no attribute 'get'）
  台账整体 = [1,2,3] / "str" / 42        exit=1（real 与 dry **都** 1）
  caller 路径是个目录（real / dry / plain init）   exit=1  内部错误（IsADirectoryError: …）
  ```
- **归因**：抛点分别是 `initcmd.py:541`（`entry.get`，无 `isinstance(entry, dict)` 守卫）、
  `:524`（台账根 `.get`）、`:548`（`sha256_bytes(path.read_bytes())`——该写法在 **merge-base
  `ae99256`** 就已存在 ⇒ 非本 change 引入）。
- **为什么非阻塞**：三条都是 fail-closed（退 1、不静默改变行为），**dry 与 real 同退出码**（不违反 Y1），
  且都需要手工破坏台账/目录（`created_files` 里塞字符串、把 caller 换成目录）才可达。
  与登记口径一致：**仍如登记所说**。

## Verdict

**通过。**

- **判据①（无未解决的行为缺陷）：满足。** 上一轮的放行条件 **B4-1 已闭环**——`:598-600` 让 `ignore`
  在进 `conflicting_files` 之前生效，M1 复现旧分叉、修后 **59 格（36+12+11）dry/real 逐格同退出码**；
  B4-2 的求值时机与唯一性经 M2 + `grep` 证明。本轮**未发现新的行为缺陷**；`ignore` 提前生效
  经调用点分析 + 矩阵证明**无过抑制**。
- **判据②（spec 每条 Requirement 有实现与钉子）：满足。** 5 条 Requirement 各有 `文件:行号` 的实现与
  钉住它的用例，且 **R1/R2/R3/R5 各用一条定向变异（N1–N4）验证钉子真能红**，R4 用 M1–M4 验证。
- **判据③（无「文档承诺 ≥ 实现」漂移）：满足。** 本 commit 未改用户文档；`README.md:248` /
  `docs/gate.md:363` 的「无法解码」是 `check` 事件文件那条，与 `init` caller 那条不冲突；
  `docs/gate.md §1.2` 逐条与实现相符。
- **判据④（上一轮放行条件确实已用 `--stat` 核过）：满足。** `git show --numstat e168b52` 逐条核过
  B4-1…B4-3 的落库实体（`initcmd.py 10/7`、`tests 59/0`），三处实体与自述一致，且 M1/M3/M4
  证明对应钉子真能红——**未出现第五次「自称已落库而实际没落」**。

**残留的三条问题（B5-1 / B5-2 / B5-3）都不构成放行条件**，逐条说明理由：

- **B5-1**（空后缀 ⇒ 空 ref）是**不可达**的（git 不能有名为 `refs/heads/` 的空分支名），
  且 fail-open 面只在「上游给出非法 ref 形态」时才会碰到；它值得修，但**不是**本 change 的
  行为回归，也不影响任何可达路径。
- **B5-2** 是一条 **print 的覆盖缺口**，删掉它**不改任何退出码、不改任何落盘**，
  同一信息仍由 note 行送达用户——纯文本钉子缺失。
- **B5-3** 是**既有**（merge-base 同形）+ fail-closed + 需手工破坏台账/目录才可达的健壮性项，
  dry 与 real 同退出码。

前几轮在「零覆盖 / 洁癖」类项上偏严（每轮因此都能再找出低危项）。本轮按判据①②③④ 如实判：
四条判据全满足，残留项**均无行为后果**（或被判定为不可达），故给 **通过**。

**未验证项**（不因此改变判定，但**不宣称**已验证）：R1-S1 的真 CI 端到端语义；真 `uvx` 安装落的
`direct_url.json`；GHES 上 `job.*` 不可用；`v1.7.0` 发布后的行为；`docs/gate.md §1.2` 的 A/B/C
三条实跑主张；R1/R2/R3/R5 的**全部**用例（各只做一条定向变异）；`…@refs/heads/` 空后缀的
**上游可达性**（脚本行为已实跑，CI 侧是否可能出现该形态未验证）。
