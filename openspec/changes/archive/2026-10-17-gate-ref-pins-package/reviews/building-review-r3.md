# building-review-r3 — gate-ref-pins-package

## Reviewer

- **角色**：独立、零记忆的**实现后**审阅（building / **B3** 轮）。本对话**不携带**该 change 的
  任何实现历史；`design.md` / `tasks.md` / `specs/` / 提交说明里的「已落库」「实测」「已收敛」
  一律当**待验证断言**处理。我不是作者，**未改写任何实现**，只产出本报告。
- **审阅对象（revision 绑定）**：worktree `/home/happy/wl-wt/archive-arrival-recognition`，
  分支 `gate-ref-pins-package/2026-10-16`，
  HEAD = `125ea125d5fb3984918deb7b8437e0c8187d5f2b`（`git rev-parse HEAD` 原始输出）。
  上一轮（`reviews/building-review-r2.md`，**只读、未改**）针对 `c9568cc`；本轮针对 `125ea12`。
- **验收标准**：`openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md`
  （5 条 Requirement）——规格是唯一判据，`design.md` / `tasks.md` 只作线索。
- **基线**：`PYTHONPATH=src python3 -m pytest -q` ⇒ **697 passed in 31.59s**（在 worktree 本体上复算，
  原始输出 `697 passed`）。所有变异版在 `/tmp/br3/{m1..m6}` 上各跑**全量** suite。
- **方法**：
  1. `git show --stat/--numstat 125ea12` 逐条核对上一轮「问题清单」**B2-1…B2-7** 的**落库实体**
     （不信处置表/提交说明，只信 diff + 代码行 + 测试行）；
  2. **动手变异** 6 组（M1–M5 探「钉子真能红 / 真能漏」，M6 反向验证 B3-1 的修法）；
  3. **穷举矩阵**：`(文件在/不在) × (条目在/不在/被标 self) × (ref 同/不同) × (内容同/手改) ×
     (--dry-run 开/关)` = **34 格**，逐格记录退出码、台账条目数、caller 内容、`uninit` 结果；
  4. 文档对照：`README.md` 前提框 vs `docs/gate.md §1.2` vs `spec.md` vs **`v1` tag 的实测事实**
     （`git show v1:…`）。
- **快照纪律**：全部实验在 `/tmp/br3/`（`git archive HEAD | tar -x` 解出的副本，**无 `.git`**；
  已确认 `/tmp/br3/m1/.git` 不存在）；真仓内**未**做任何 commit / reset / tag / push。
- **证据约定**：每条结论带 `文件:行号` 或「命令 + 原始输出」。**没复算的一律标「未验证」**。

## 审阅结论

**上一轮的 7 条（B2-1…B2-7）确实都落了库**（`--stat` + 代码/测试实体逐条核过），
其中 **B2-1 / B2-4 / B2-5 的钉子经变异确认真能红**，B2-1 抓到的那个回归
（「同 ref + caller 那条被标 `self`」⇒ 插重复条目 ⇒ `uninit` 半回滚）在**穷举矩阵的 34 格里
一格都不再复现**（`dup>1` 的格子数 = **0**），且 dry-run 与真跑的退出码**逐格一致**。

**但是**：本轮在核对「真跑那条路到底会打印什么」时，抓到一条**上一轮 `c9568cc` 引入、
`r2` 漏掉的行为缺陷（B3-1）**：`src/witnessloop/initcmd.py:210` 的判据
`if manifest.get("gate_ref") != gate_ref:` 在 `:208` 的 `_set_ledger_gate_ref(...)` **已经把
`manifest["gate_ref"] = gate_ref`（`:320`）写进去之后**才求值 ⇒ **恒为 False**，
`:211-212` 的「已重写 …（→ <新 ref>）并同步台账」是**死代码**。后果是：**只要 ref 真的变了**，
用户看到的收尾文案是

```
init：已补齐台账里的 .github/workflows/witnessloop.yml 条目（ref 本来就是 <刚刚换成的那个新 ref>，未改）
init：已接入 witnessloop（台账里的 .github/workflows/witnessloop.yml 条目已补齐（ref 未变））。
```

——**两句都是假的**（台账 `gate_ref` 实测从 `@v1` 变成了 `@v9.9.9`、caller 文件也被重写）。
讽刺的是 `:213` 那句注释正写着「**别谎称改了 ref**」，而活着的那条分支恰是撒谎的那条。
⇒ 判据①（无未解决行为缺陷）**不满足**。

另有 4 条（1 条残留静默覆盖 + 注释自称「交给别处报」不成立、1 条注释把可达性说反、
1 组覆盖缺口、1 条既有观察），均**不阻塞**。上一轮的 B1-4 / B1-8 / B1-10 仍未落库
（与本轮无关，**本文不替它们背书**）。

## 逐维度结论

### 维度一：上一轮「问题清单」逐条落库核对（`--stat` + 实体）

`git show --numstat 125ea12` 原始输出：

```
5	2	README.md
4	1	docs/gate.md
302	0	openspec/changes/gate-ref-pins-package/reviews/building-review-r2.md
41	12	src/witnessloop/initcmd.py
73	0	tests/test_init_gate_ref.py
```

（`tests/` 的改动**全是纯新增**：`git show 125ea12 -- tests/ | grep -c '^-[^-]'` ⇒ **0**；
`building-review-r2.md` 是上一轮报告的**归档新增**，非改写。）

| 上轮项 | 自述 | 实体核对（`--stat` + 代码/测试行） | 判定 |
|---|---|---|---|
| **B2-1**（放行条件，回归） | 已落 | `initcmd.py:236-239` 把「台账结构判据」**前移**到 `:245` 的 self 守卫之前（旧的 `or manifest.get("gate_ref") == gate_ref: return None` 早退已从 `caller_retarget_refusal` 里**删除**）；`:245-256` 的 self 守卫因此**无条件**执行。钉子：`tests/test_init_gate_ref.py:559-586`（**同 ref** + 标 self ⇒ 退 1、台账字节不变、条目数 == 1）。变异 **M1**（把早退放回去）⇒ `2 failed, 695 passed` | **落库，且是那条** ✓（钉子能红） |
| **B2-2**（注释撒谎） | 未提 | `initcmd.py:308-309` **一字未动**（本 commit 的 diff 里没有这一行）。但该注释的断言「当前不可达（被标 self 的 caller 条目在入口就被拒绝了）」在**本 commit 的修法之后成立**：`_set_ledger_gate_ref` 的唯一调用者是 `sync_caller_gate_ref`（`:208`），后者唯一调用点是 `run():412`，而 `run():386` 在任何写入之前先跑 `caller_retarget_refusal`——它现在对任何「caller 条目被标 self」都退 1（`:245`），故 `_set_ledger_gate_ref` 不可能在该态下被调用 | **未改字，但所诉事实已被消解**（不阻塞） |
| **B2-3**（文案悬空指代） | 已落 | `initcmd.py:604-608`：`⚠️ 但**别照下句做**：…` 已换成自足表述「⚠️ 这一行冲突与你那条显式 `--gate-ref` 无关；**不要**为此去跑 `uninit`——…policy 那条轴请**单独**解决（同时再给一次 `--policy <你的 seed>` 即可）。」；`docs/gate.md:120-122` 补了两种命令形态的引文 | **落库，且是那条** ✓（该分支仍零覆盖 ⇒ B3-3） |
| **B2-4**（静默覆盖手改 caller） | 已落 | `initcmd.py:258-274`：文件在 ∧ `manifest.gate_ref == gate_ref` ∧ 盘上内容 ≠ `caller_workflow(gate_ref)` ⇒ **响亮拒绝**。钉子：`tests/test_init_gate_ref.py:588-606`（断言退 1 + 手改内容原样保留）。变异 **M2**（把该判据改 `if False:`）⇒ `1 failed, 696 passed` | **落库，且是那条** ✓（钉子能红；残留见 B3-2） |
| **B2-5**（dry-run 文案） | 已落 | `initcmd.py:193-204`：`changing_ref` 在 dry-run 之前算好，两条 dry-run 文案按它分叉。钉子：`tests/test_init_gate_ref.py:609-629`（断言 `"补齐" in out and "ref 未变" in out` 且 `"改成" not in out`）。变异 **M3**（把 `if changing_ref:` 改 `if True:`）⇒ `1 failed, 696 passed` | **落库，且是那条** ✓（钉子能红） |
| **B2-6**（两处输出零覆盖） | 部分 | 补了一条钉子（`:609` 同时覆盖 dry-run 与真跑的**返回串**），但两处**用户可见输出**仍零覆盖：变异 **M4**（`initcmd.py:608` 的 `if handled` → `if False`）⇒ **697 passed（全绿）**；变异 **M5**（删掉 `initcmd.py:214` 的 print）⇒ **697 passed（全绿）** | **半落**（⇒ B3-3） |
| **B2-7**（README 前提框） | 已落 | `README.md:183-187` 重写。**且按 `v1` 的事实逐条核过为真**（见维度五）：`git show v1:.github/workflows/gate.yml \| grep -n "workflow_sha\|wl-ref"` ⇒ **只有两行无关的 `::notice::`（测试执行点）**；`git show v1:src/witnessloop/initcmd.py \| grep -n "def sync_caller_gate_ref"` ⇒ **无输出**；`v1` 的 `cli.py:44` 有 `--gate-ref`，`v1` 的 `initcmd.py:345-346` 正是那句「要更换 policy 请先 `uninit`」的冲突文案 ⇒ README 的「旧 CLI 跑第 ② 步只会得到一句指向 policy 的冲突，见 §1.2」**属实** | **落库**（原意以事实口径兑现；措辞差见维度五） |

### 维度二：变异验证

每组变异在 `/tmp/br3/{m1..m6}`（各由 `git archive HEAD` 解出、无 `.git`）上跑**全量** suite：

| 变异 | 改什么 | 结果（原始输出） | 说明 |
|---|---|---|---|
| **M1** | `caller_retarget_refusal` 头部恢复 `if not isinstance(manifest, dict) or manifest.get("gate_ref") == gate_ref: return None`（= 把 B2-1 的回归放回去） | **2 failed, 695 passed** —— `test_same_ref_with_a_self_flagged_entry_is_refused_not_duplicated`、`test_a_hand_edited_caller_with_no_ledger_entry_is_not_silently_clobbered` | B2-1 的钉子**真能红**（但它同时打红 B2-4 的钉子：该早退会一并绕过 `:262` 的内容判据，两条钉子共用同一个前缀） |
| **M2** | `initcmd.py:262` 的判据改 `if False:`（= 去掉 B2-4 的拒绝） | **1 failed, 696 passed** —— 只有 `test_a_hand_edited_caller_with_no_ledger_entry_is_not_silently_clobbered` | B2-4 钉子**真能红且只打红自己** |
| **M3** | `initcmd.py:200` 的 `if changing_ref:` 改 `if True:`（= 去掉 B2-5 的 dry-run 分叉） | **1 failed, 696 passed** —— 只有 `test_the_repair_branch_says_it_only_filled_the_ledger` | B2-5 钉子**真能红且只打红自己** |
| **M4** | `initcmd.py:608` 的 `if handled` 改 `if False`（handled 冲突文案永不出现） | **697 passed（全绿）** | 该段文案**零覆盖** |
| **M5** | 删掉 `initcmd.py:214` 的 `print(f"init：已补齐台账里的 …")` | **697 passed（全绿）** | 该 print **零覆盖**（`:609` 的用例靠**返回串**里的「补齐 / ref 未变」通过） |
| **M6** | 把 `initcmd.py:210` 的 `if manifest.get("gate_ref") != gate_ref:` 改成 `if changing_ref:`（= **修 B3-1**） | **697 passed（全绿）**；且探针实跑输出变成正确的 `init：已重写 .github/workflows/witnessloop.yml（→ …@v9.9.9）并同步台账` / `… 与台账已改成 …@v9.9.9` | 修法**安全且有效**，反过来说明**当前那句假话没有任何钉子**（⇒ B3-3） |

### 维度三：判据组合穷举（34 格）与「拒绝面 / 早退面」的互补性

探针在 `/tmp/br3/base`（= HEAD 原样副本）上跑。`file=present/absent`、`entry=present/absent/self`、
`ref=same/diff`（`same` = `C.DEFAULT_GATE_REF`，`diff` = `…@v9.9.9`）、`content=same/hand`
（`hand` = caller 被手改成 `name: hand-edited`）、`dry=real/dry`。**每个格子跑完 `init` 之后
一律再跑一次 `uninit`**，看它是否半回滚。原始输出（节选，完整 34 行）：

```
| file | entry | ref | cont | dry | exit | dup | idem | caller | uninit |
|---|---|---|---|---|---|---|---|---|---|
| present | present | same | same | real | 0 | 1 | 幂等 | same    | ok |
| present | present | same | hand | real | 1 | 1 |      | same    | uninit-refused: uninit：以下文件被改动过，拒绝删除： |
| present | present | diff | same | real | 0 | 1 |      | CHANGED | ok |
| present | present | diff | hand | real | 0 | 1 |      | CHANGED | ok |
| present | absent  | same | same | real | 0 | 1 |      | same    | ok |
| present | absent  | same | hand | real | 1 | 0 |      | same    | 退 0 但 caller 残留（见注） |
| present | absent  | diff | same | real | 0 | 1 |      | CHANGED | ok |
| present | absent  | diff | hand | real | 0 | 1 |      | CHANGED | ok |
| present | self    | same | same | real | 1 | 1 |      | same    | ok |
| present | self    | same | hand | real | 1 | 1 |      | same    | ok |
| present | self    | diff | same | real | 1 | 1 |      | same    | ok |
| present | self    | diff | hand | real | 1 | 1 |      | same    | ok |
| absent  | present | same | same | real | 1 | 1 |      | same    | ok |
| absent  | present | diff | same | real | 1 | 1 |      | same    | ok |
| absent  | absent  | same | same | real | 1 | 0 |      | same    | ok |
| absent  | absent  | diff | same | real | 1 | 0 |      | same    | ok |
| absent  | self    | same | same | real | 1 | 1 |      | same    | INTERNAL-ERROR（见 B3-5） |
```

（`dry` 那 17 行与 `real` 逐格一一对应，**退出码全部相同**，`dup` 恒为 0 或 1；为省版面不重复列出。
注：`present|absent|same|hand` 这一格是**探针人为造的坏台账**——台账里少了 caller 条目、
盘上的 caller 又是手改内容，所以 `init` 按 B2-4 拒绝（不修台账），随后 `uninit` 退 0、
删掉 policy 与台账、**把没有条目的 caller 留在盘上**。这既不是本轮引入的，也不是
`init --gate-ref` 的路径问题（是「台账缺条目 ⇒ `uninit` 不删 caller」这条既有语义，
正是 B1-5 让补齐路径存在的理由）；登记在此只为把矩阵读全。）

**结论**：

1. **`dup > 1` 的格子数 = 0**（脚本直接统计：`重复条目行数: 0`）⇒ B2-1 那条「插重复条目 ⇒
   `uninit` 二次 `unlink`」的路径在**全部组合下不可达**。
2. **dry-run 与真跑逐格同退出码**（17 对全相符）⇒ R11 的 Y1 语义未被本轮改动破坏。
3. **拒绝面（4 类拒绝 + 1 类放行）与 `sync_caller_gate_ref` 的早退条件**：
   - refusal **拒绝**（`initcmd.py:245` self 守卫 / `:267` 同 ref + 内容不符 / `:288` 无条目 + 无文件，
     加上「台账结构非法交给别处」）⇒ `run():386-388` 在**任何写入之前**退 1，`sync` **根本不被调用**
     ⇒ 不存在「拒绝面放过、而 `_set_ledger_gate_ref` 落进 `else` 插重复」的缝（矩阵里
     `present|self|*`、`present|absent|same|hand`、`absent|absent|*` 全部退 1、台账字节不变）。
   - refusal **放行 ∧ sync 走早退**（`initcmd.py:173-181`：ref 相同 ∧ `created_files` 是数组 ∧
     存在非 self 的 caller 条目）⇒ 真·无事可做；此态下若盘上内容与期望不同，漂移分支响亮退 1
     （格 `present|present|same|hand`）⇒ 没有静默放过。
   - refusal **放行 ∧ sync 不走早退** ⇒ 三条：① ref 相同但缺条目（补台账，格
     `present|absent|same|same`，退 0 且台账条目数回到 1）；② ref 不同（重写，格
     `present|*|diff|*`）；③ 文件不在（`sync:190` 早退 ⇒ 交给漂移分支响亮退 1，格 `absent|present|*`）。
   - **唯一的缝**是 `initcmd.py:265-266` 的 `except (OSError, UnicodeDecodeError): return None`
     ⇒ **B3-2**。
4. **顺带修好的另一条静默 no-op**：`absent|absent|same`（无条目 + 无文件 + **同 ref**）在
   `c9568cc` 里会被「ref 相同」的早退放行 ⇒ 落进 sync 后又因文件不在返回 `None` ⇒
   `_already_initialized` 既无漂移（无条目可遍历）也无冲突（文件不在）⇒ **退 0「幂等，无改动」**
   ——正是 V1 要堵的那条。结构判据前移把它一并堵上了（现退 1）。**但这一格没有独立钉子**：
   现有 V1 用例（`tests/test_init_gate_ref.py:379`）走的是 `NEW_REF`，M1 也只打红另外两条（⇒ B3-3）。

### 维度四：新发现（B3-1 / B3-2 的原始证据）

**B3-1：真跑「ref 真的变了」的收尾文案说反 + 死代码**

探针（`/tmp/br3/probe2.py`，跑在 HEAD 副本上）原始输出：

```
===== A 有条目 + ref 变（真跑） =====
exit=0 | ledger gate_ref: '…/gate.yml@v1' -> '…/gate.yml@v9.9.9' | caller_ref_in_file=NEW
STDOUT: init：已补齐台账里的 .github/workflows/witnessloop.yml 条目（ref 本来就是 …/gate.yml@v9.9.9，未改）
init：已接入 witnessloop（台账里的 .github/workflows/witnessloop.yml 条目已补齐（ref 未变））。
```

根因链（两跳）：

1. `initcmd.py:208` 调 `_set_ledger_gate_ref(manifest, gate_ref, …)`；
2. 该函数最后一行 `initcmd.py:320` 执行 `manifest["gate_ref"] = gate_ref` ——**就地**把 dict 改了；
3. `initcmd.py:210` 才求值 `if manifest.get("gate_ref") != gate_ref:` ⇒ **恒为 False**
   ⇒ `:211-212` 的「已重写」分支**永不执行**，`:214-215` 的「已补齐 / ref 未变」是**唯一出口**。

同一探针在 **M6（把 `:210` 换成 `if changing_ref:`）** 上：

```
STDOUT: init：已重写 .github/workflows/witnessloop.yml（→ …/gate.yml@v9.9.9）并同步台账
init：已接入 witnessloop（.github/workflows/witnessloop.yml 与台账已改成 …/gate.yml@v9.9.9）。
```

⇒ 修法（一处判据）已验证有效，且**不改变任何退出码 / 落盘内容**（`697 passed`）。

**B3-2：不可解码的 caller 会被静默覆盖，且注释自称「交给下面那两条判定去报」不成立**

探针原始输出（`无条目 + ref 同 + caller 写成非法 UTF-8`）：

```
exit=0 | ledger gate_ref: '…@v1' -> '…@v1' | caller_ref_in_file=OLD      # 文件已被改写回 caller_workflow(OLD_REF)
STDOUT: init：已补齐台账里的 .github/workflows/witnessloop.yml 条目（ref 本来就是 …@v1，未改）
```

`initcmd.py:265-266` 的 `except (OSError, UnicodeDecodeError): return None` 注释写「读不出：
交给下面那两条判定去报（别在这里猜）」，但**这条 `return None` 恰好跳过**了它下面那两条判定
（`:275` 的「有条目 + 文件缺失」与 `:288` 的「无条目 + 无文件」都要求**文件不在**），
`run()` 于是照常走到 `sync_caller_gate_ref` 的 `:206-208` **无条件 `write_text`** ⇒ 用户手写的内容被抹掉、EXIT 0、
输出不提这件事。（同款状态若内容**可解码**则被 `:267` 响亮拒绝 —— 该判据本身是对的。）

### 维度五：文档一致性（README 前提框 / `docs/gate.md §1.2` / `spec.md`）

- **README `:183-187` 新前提框的事实核对**（命令 + 原始输出见维度一 B2-7 行）：
  「`v1` 那份 `gate.yml` 里没有解析 step」「`@v1` 的旧 CLI 没有这条语义」「跑它只会得到一句
  指向 policy 的冲突」**三条全属实**。
- **与 `docs/gate.md §1.2` 一致**：§1.2 `:82-88` 的两步升级、`:102-111` 的「为什么 ① 不能省」
  （含 `:106` 那句旧 CLI 冲突文案）与 README 前提框**同口径**。
  §1.2 `:120-122` 新增的引文（「这一行冲突与你那条显式 `--gate-ref` 无关；**不要**为此去跑
  `uninit`……」）与实现 `initcmd.py:605-607` **逐字相符**（省略号处为省略的尾句）；
  §1.2 `:106` 引的那句（「…要更换 policy 请先 `uninit`」）经 `git show v1:src/witnessloop/initcmd.py
  | sed -n '345,346p'` 确认是 **v1 的原文**，且新加的说明（§1.2 `:122`）「上面引的那句是**不带**
  `--gate-ref` 时的形态」与实现（`initcmd.py:608` 的 `if handled` 只在带 flag 时走新文案）**相符**。
  （§1.2 `:112-126` 的「定制 policy 的仓」前提本轮未重跑，与「未验证 4」同一条。）
- **与 `spec.md` 一致**：spec 里**没有**「先写 `@v1`、其余语义完全一样」这种说法（上一轮 B2-7
  指出的那句已被删除）；「组合语义」Scenario 要求输出**点明**「caller 已落盘、不回滚」——
  该句由 `initcmd.py:423-427` 的 `handled` 固定串给出，**与本轮的文案改动无关，仍满足**。
- **残留（不阻塞）**：新前提框的限定语仍写作「本仓已发布含这个能力的 ref（`v1.7.0` 起）」，
  而未逐字用上一轮 B1-6 想要的那句「你 caller 的 `uses:` 指向的那份 ref 里含不含本 change 的
  `gate.yml`」。两者在**本仓**语境下等价（发布 tag 即 ref），差别只在「指向 `@main` 一类分支」
  的边角；`README:212-213` 的旧警告与它语义重复但不矛盾。
- **未发现**「文档承诺 ≥ 实现」的漂移（本轮改动面里没有：README/§1.2 描述的能力都能在
  `initcmd.py` 里找到实现）。

### 未验证（明确登记，不计入问题清单）

1. **R1-S1 的端到端 Then**（`job.workflow_sha` = 被复用文件自己的 commit）：GitHub Actions 语义，
   本工作区无 Actions，**未复算**（与上两轮同一登记）。
2. **真 `uvx` 安装落的 `direct_url.json`**：仍是抄录载荷 + 手造 dist-info 覆盖读取环，**未**端到端验证。
3. **GHES 上 `job.*` 不可用**、**fork 判据必要不充分**：依据 spec/design 登记与 GitHub 文档，未实测。
4. **`docs/gate.md §1.2` 的 A/B/C 三条实跑主张**：本轮未重跑（本轮改动不在这三条所指路径上）。
5. **`v1.7.0` 发布后的行为**：时序上不可验证。
6. **R1 / R2 / R3 / R5 的钉子**：本轮只复算了 R4（`init --gate-ref`）相关；
   其余四条要求的实现与钉子**沿用上一轮结论**（本 commit 未触及 `gate.yml` / `checkcmd.py` /
   `docs/gate.md §7`），**未逐条重新复算**——`grep -rln "workflow_sha" tests/` ⇒
   `tests/test_gate_workflow.py`、`tests/test_docs.py` 仍在，可作线索而非本轮结论。

## 问题清单

> 排序：行为缺陷在前，注释/覆盖/观察殿后。每条带类别 + 严重度 + 证据。

### B3-1 · 行为缺陷（用户可见输出撒谎 + 死代码） · 中 —— 真跑「ref 真的换了」时报「ref 本来就是 <新 ref>，未改」

- **位置**：`src/witnessloop/initcmd.py:210`（恒假判据）/ `:211-212`（死分支）/ `:214-215`（唯一出口）
  / `:320`（`manifest["gate_ref"] = gate_ref` 的就地改写）。
- **证据**：维度四的探针原始输出——台账 `gate_ref` 实测 `@v1 → @v9.9.9`、caller 文件被重写，
  而 stdout 是「已补齐 … 条目（ref 本来就是 …@v9.9.9，未改）」+「… 已补齐（ref 未变）」。
  该分支自 `c9568cc`（上一轮的 B1-5 修复）起就是死的（`git show 5bb7765:src/witnessloop/initcmd.py`
  里这一处是**无条件** `print("init：已重写 …")`，没有判据）。
- **为什么是问题**：① 用户拿不到任何「它确实动了 ref」的信号，误以为请求被丢掉；
  ② 它把**刚被写进去的新值**说成「本来就是」——这不是漏报而是**报反**；③ 注释 `:213`
  「别谎称改了 ref」与事实相反，会误导后来改这块代码的人；④ 修法一行、且 M6 证明
  `697 passed` 不变 ⇒ 纯收益。
- **建议**：把 `:210` 的判据改成已算好的 `changing_ref`（或把 `:193-197` 的 `changing_ref`
  连同「改写前是否不同」一起在 `_set_ledger_gate_ref` **之前**存下），并补一条用例：
  「`--gate-ref <不同 ref>` 真跑 ⇒ 输出含 `已重写` 且**不含** `ref 未变`」。

### B3-2 · 行为 / 一致性 · 低 —— 不可解码的 caller 被**静默覆盖**（EXIT 0），且注释宣称的兜底不存在

- **位置**：`src/witnessloop/initcmd.py:263-266`。
- **证据**：维度四的探针——`无条目 + ref 相同 + caller 非法 UTF-8` ⇒ 退 0，文件被改写回
  `caller_workflow(ref)`，输出只说「条目已补齐（ref 未变）」，**不提文件被重写**；
  同一判据在内容**可解码**时是响亮退 1（`:267-273`，M2 证明其钉子承重）。
- **为什么是问题**：这是 B2-4 修掉的那类「静默覆盖用户内容」的**残留子集**（上轮修法只是
  把「全部」缩到「不可解码的」），而 `:266` 的注释「交给下面那两条判定去报」**不成立**：
  那条 `return None` 跳过的正是它下面那两条（它们都要求**文件不在**）。
- **建议**：把 `:265-266` 改成与 `:267` 同款的响亮拒绝（读不出 ⇒ 猜不出以哪边为准，
  `<path> 无法解码：…请人工确认`），或至少在输出里写明「已重写」。不阻塞。

### B3-3 · 覆盖缺口 · 低 —— 4 处行为/输出无任何用例，其中一处正是 B3-1 逃过上一轮的原因

- **位置/证据**（全部为**全绿**变异）：
  1. `initcmd.py:210-212` 的真「已重写」文案：**M6**（修 B3-1）⇒ `697 passed`；
  2. `initcmd.py:214` 的 print：**M5**（删掉它）⇒ `697 passed`（`:609` 的用例靠返回串通过）；
  3. `initcmd.py:604-608` 的 `handled` 冲突文案：**M4**（`if False`）⇒ `697 passed`；
  4. `absent|absent|same`（无条目 + 无文件 + **同 ref**）的响亮拒绝：**M1** 只打红另外两条，
     现有 V1 用例（`tests/test_init_gate_ref.py:379`）走 `NEW_REF`。
- **为什么是问题**：第 1 条直接解释了 B3-1 为什么能在上一轮「三条放行条件都验过」的情况下溜过去——
  **恰好是那条路的输出没人断言**；第 3 条与上一轮判为**放行条件**的 B1-2 同类（本轮新增的
  用户可见输出零覆盖）。危害：都不改退出码，故**不**列为放行条件。
- **建议**：随 B3-1 一起补第 1 条钉子；第 2/3/4 条各补一行断言即可。

### B3-4 · 注释与事实不符 · 低 —— 新注释自称「**不是**「不可达」」，与它自己的前半句矛盾

- **位置**：`src/witnessloop/initcmd.py:283-286`（本 commit 改写的那段）。
- **证据**：注释写「本函数里那个 `not entry.get("self")` 是**纵深防御**（上面的「被标 self ⇒
  拒绝」分支已先拦下它们）——但**不是**「不可达」」。既然 `:245` 的守卫对**任何**带 `self` 的
  caller 条目都先退 1，`:275-280` 里那个 `and not entry.get("self")` 合取项在本函数内**恒真**
  （等价于只看 `path` 相符）⇒ 它就是**不可达/空转**的；注释给的理由（「B2-1 的回归正是
  『少了口径一致就会插重复条目』」）说的是**另一处**守卫（B2-1 的病灶在 `run()` 的接线顺序），
  不能支撑「不是不可达」。
  另：`:308-309` 把 `_set_ledger_gate_ref` 里的同款守卫叫「**纵深防御**」，但直接调用探针
  （`/tmp/br3/probe4.py`，绕过 `run()` 的拒绝面调 `sync_caller_gate_ref`）显示：被标 `self` 时
  正是这个守卫让循环走 `else`、**插出第 2 条同路径条目**（`caller 条目数: 2`），随后
  `uninit` 报 `witnessloop：内部错误（FileNotFoundError: …）`。也就是说它**不是**「少出 bug 」
  的防线，而是**该走 `break` 却插重复**的那一环（删掉它反而会命中 `self` 那条、只改 `sha`）。
- **为什么是问题**：与 B1-3 / B2-2 同一类（注释宣称的可达性/因果与事实不符），且**本轮新写**；
  运行时无影响（拒绝面已无条件先拦），故**不阻塞**。
- **建议**：把两处注释统一成一句实话：「该合取项在本函数内**恒真**（self 那条在 `:245` 已被拦），
  保留它是为了让**口径**在将来改动时不分叉；一旦有人把 `:245` 的守卫挪走，它就会从此处
  落进 `else` 插重复条目」。

### B3-5 · 观察（**既有、非本轮引入**） · 低 —— 手改台账（caller 那条标 `self` 且文件缺失）时 `uninit` 仍会半回滚

- **证据**：矩阵里 `absent|self|*` 四格 + 独立探针原始输出：

  ```
  uninit exit 1
  OUT: uninit：已回滚 witnessloop 接入：
    - .witnessloop/policy.json
  ERR: witnessloop：内部错误（FileNotFoundError: … '/…/.github/workflows/witnessloop.yml'）
  left: ['.witnessloop/init-manifest.json']
  ```

  根因在 `src/witnessloop/uninitcmd.py:53`（`entry.get("self")` ⇒ 当作「台账自己那条」放进
  `doomed` 末尾）与 `:94`（`path.unlink()` 未防「不存在」）。
- **为什么登记**：这正是 `initcmd.py:246-250` 那段注释引用的危害（「删的时候会半回滚」），
  而本轮的修法是**拒绝**（`init` 退 1、把人交回给用户）——用户手里最自然的下一步 `uninit`
  恰好会踩它。**本轮任何改动都没有触碰 `uninitcmd.py`**（`--numstat` 无该文件），
  且该态需要**两处**手工损坏（条目标 `self` **且** 文件被删）⇒ 不阻塞、不计入本轮缺陷。
- **建议**（可选，一行）：`uninitcmd.py:53` 只把 `rel == C.INIT_MANIFEST_PATH` 判为「台账自己那条」，
  `self` 标记不足以改变它的**删除次序**该不该跳过 `exists()` 检查；或在 `:94` 前加
  `if path.exists()`。

## Verdict

**有条件通过。**

- 判据①（无未解决行为缺陷）：**不满足**。B3-1 是 `c9568cc` 引入、`125ea12` 未修的行为缺陷
  （真跑换 ref 成功后**报反**：说自己没改、还把新 ref 说成「本来就是」），且**零覆盖**
  （M6 把它修好 ⇒ 仍然 `697 passed`）；B3-2 是同类的残留静默覆盖（窄，一行可修）。
- 判据②（每条 Requirement 有实现 + 钉子）：**满足**（与上一轮同一结论）。本轮改动只落在 R4
  所指的 `init --gate-ref` 一条轴上；R1/R2/R3/R5 的实现与钉子本轮**未复算**（见「未验证」6）。
- 判据③（无「文档承诺 ≥ 实现」漂移）：**满足**。README 新前提框的三条事实断言经 `git show v1:…`
  逐条核实为真，与 `docs/gate.md §1.2` / `spec.md` 同口径；仅残留一处措辞差（前提写成
  「已发布含该能力的 ref」而非逐字的那句），**不阻塞**。
- 判据④（上一轮放行条件确实已落库，用 `--stat` 核过）：**满足**。B2-1 落了库、落的就是那条
  （结构判据前移 + 同 ref 的钉子，M1 证明能红）；B2-4 / B2-5 的钉子经 M2 / M3 确认**只打红自己**。

**放行条件（一条，一处判据 + 一条用例）**：修 **B3-1** —— 让真跑那条路按「**改写前**的
`manifest["gate_ref"]` 是否不同于 `gate_ref`」分叉（用 `:193` 已算好的 `changing_ref` 即可），
并补一条断言「`--gate-ref <不同 ref>` 真跑 ⇒ 输出含 `已重写`、不含 `ref 未变`」的用例。

**不阻塞**：B3-2（建议同批修，一行）、B3-3 的 2/3/4 三条覆盖、B3-4（注释按事实改写）、
B3-5（既有，`uninitcmd.py`，本轮未触碰）；B1-4 / B1-8 / B1-10 仍未落库（与前两轮口径一致）。

**未验证项**（不因此改变判定，但**不宣称**已验证）：R1-S1 的真 CI 端到端语义；真 `uvx` 安装落的
`direct_url.json`；GHES 上 `job.*` 不可用；`v1.7.0` 发布后的行为；R1/R2/R3/R5 钉子的本轮复算。
