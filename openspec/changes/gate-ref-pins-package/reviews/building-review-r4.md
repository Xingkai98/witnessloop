# building-review-r4 — gate-ref-pins-package

## Reviewer

- **角色**：独立、零记忆的**实现后**审阅（building / **B4** 轮）。本对话**不携带**该 change 的
  任何实现历史；`design.md` / `tasks.md` / `specs/` / 提交说明里的「已落库」「实测」「已收敛」
  一律当**待验证断言**处理。我不是作者，**未改写任何实现**，只产出本报告。
- **审阅对象（revision 绑定）**：worktree `/home/happy/wl-wt/archive-arrival-recognition`，
  分支 `gate-ref-pins-package/2026-10-16`，
  HEAD = `58601b8420569a36efa195d412a9cdf1a738d0e6`（`git rev-parse HEAD` 原始输出）。
  上一轮（`reviews/building-review-r3.md`，**只读、未改**）针对 `125ea12`；本轮针对 `58601b8`。
- **验收标准**：`openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md`
  （5 条 Requirement）——规格是唯一判据，`design.md` / `tasks.md` 只作线索。
- **基线**：`PYTHONPATH=src python3 -m pytest -q` ⇒ **699 passed in 32.59s**（在 worktree 本体上复算，
  原始输出 `699 passed`）。所有变异版在 `/tmp/br4/{m1..m5}` 上各跑**全量** suite。
- **方法**：
  1. `git show --stat/--numstat 58601b8` 逐条核对上一轮「问题清单」**B3-1…B3-4** 的**落库实体**
     （不信处置表/提交说明，只信 diff + 代码行 + 测试行）；
  2. **动手变异** 5 组（M1/M2/M3 探三条新钉子真能红，M4/M5 复查上一轮登记的覆盖缺口是否被补）；
  3. **穷举矩阵**：`(文件在/不在) × (条目在/不在/被标 self) × (ref 同/不同) × (内容同/手改/不可解码)
     × (--dry-run 开/关)`，逐格记录退出码、台账条目数、caller 内容、`uninit` 结果；
  4. 文档对照：本 commit 是否改动用户文档（`--numstat` 决定）+ 文档里引用的文案是否还成立。
- **快照纪律**：全部实验在 `/tmp/br4/`（`git archive HEAD | tar -x` 解出的副本，**无 `.git`**；
  已确认 `/tmp/br4/base/.git` 不存在）；真仓内**未**做任何 commit / reset / tag / push。
- **证据约定**：每条结论带 `文件:行号` 或「命令 + 原始输出」。**没复算的一律标「未验证」**。

## 审阅结论

**上一轮唯一放行条件 B3-1 确实落了库，而且落的正是那条**（`--stat` + 代码行 + 变异三重核对）：
`:208` 的 `changing_ref` 现在在 `_set_ledger_gate_ref`（`:209`）**之前**求值，`:211` 的分叉改判
`changing_ref`；把这一处**变异回旧写法**（M1）⇒ 新钉子红，且**复现出的正是 r3 记的那句假话**
（`已补齐 …（ref 本来就是 <新 ref>，未改）`）。B3-2（读不出的 caller 不再静默覆盖）也落了库
（M2 红、探针实测文件字节未动）。B3-4（两处注释按事实改写）落了库。**B3-3 只落了一半**：
真重写文案 / dry-run 重写文案的新钉子都在（M1 / M3 各自打红），但「`已补齐` 那句真跑 print」
仍**零覆盖**（M5 全绿），`absent|absent|same` 这一格仍**无独立钉子**。

**本轮新发现一条低危行为不一致（B4-1，非本 commit 引入）**：当 caller 文件**不可解码**、
且 `--gate-ref` 给了**不同** ref 时，**真跑退 0**（照常重写）而 **`--dry-run` 退 1**
（`conflicting_files` 在 `ignore` 过滤**之前**抛 `ValueError`，`:596` vs `:600`）。
这与本 change 自己立的 R11-Y1 不变量（「dry-run 与真跑对同一状态同一结论」，`:562-566` 与
`tests/test_init_gate_ref.py:467` 钉着）在同族状态上仍然分叉；因为该格的前提是「不可解码的
caller」，属窄面且 fail-closed，故列为**非阻塞**。另有一条纯代码洁癖（B4-2，`changing_ref` 重复求值）。

## 逐维度结论

### 维度一：上一轮放行条件与低危项逐条落库核对（`--stat` + 实体）

`git show --numstat 58601b8` 原始输出：

```
345	0	openspec/changes/gate-ref-pins-package/reviews/building-review-r3.md
20	13	src/witnessloop/initcmd.py
36	0	tests/test_init_gate_ref.py
```

（`tests/` 的改动**全是纯新增**；代码改动面只有 `initcmd.py` 一个文件；`building-review-r3.md`
是上一轮报告的**归档新增**。**本 commit 未触碰** `README.md` / `docs/gate.md` / `gate.yml` /
`checkcmd.py` / `uninitcmd.py`。）

| 上轮项 | 自述 | 实体核对（`--stat` + 代码/测试行） | 判定 |
|---|---|---|---|
| **B3-1**（放行条件，真跑报反） | 已落 | `initcmd.py:205-208` 新注释 + `:208` 在 `:209` 的 `_set_ledger_gate_ref` **之前**重算 `changing_ref`；`:211` 改判 `if changing_ref:`（旧写法 `if manifest.get("gate_ref") != gate_ref:` 已删除，`--numstat` 记为 -13/+20 一致）。钉子：`tests/test_init_gate_ref.py:75-76`（`assert "已重写" in out and "改成" in out` 且 `"补齐"/"ref 未变" not in out`）。变异 **M1**（改回旧顺序）⇒ `1 failed, 698 passed`，且失败现场**逐字复现** r3 引的那句假话 | **落库，且是那条** ✓（钉子能红） |
| **B3-2**（不可解码的 caller 静默覆盖） | 已落 | `initcmd.py:266-272`：`except (OSError, UnicodeDecodeError) as exc:` ⇒ `return` 一句响亮拒绝（按 `isinstance(exc, UnicodeDecodeError)` 选「无法解码 / 无法读取」）。钉子：`tests/test_init_gate_ref.py:647-665`（断言退 1 + `"无法解码" in err` + 字节原样）。变异 **M2**（改回 `return None`）⇒ `1 failed, 698 passed` | **落库，且是那条** ✓（钉子能红） |
| **B3-3**（4 处覆盖缺口） | 未单独认领 | 补了 **2** 条新钉子（`:636` dry-run 将重写、`:647` 不可解码）+ 1 条断言（`:75`）。逐项复核见维度二/三：**第 1 条真重写文案**已钉（M1 红）；**第 2 条 `:215` 的 `已补齐` print** 仍**零覆盖**（M5 全绿）；**第 3 条 `handled` 冲突文案**——我实测**已有覆盖**（M4 红 2 条，与 r3 的 M4 结论相反，见维度二）；**第 4 条 `absent|absent|same`** 仍**无独立钉子**（现有 `:383` 用例走 `NEW_REF`） | **半落**（残留 ⇒ B4-3） |
| **B3-4**（两处注释按事实改写） | 已落 | `initcmd.py:314-317`：改成「在当前控制流下**恒真** … ⇒ **本身不可达**；留着是因为「被绕过后插重复条目」正是 B2-1 那次的回归形态」；`:290-292`：改成「在当前控制流下**不可达** … 保留它是**纵深防御**」。两处口径一致、与事实相符（self 那条在 `:246` 入口已无条件拒绝 ⇒ 两处的 `not entry.get("self")` 合取项在本函数内都取不到 False） | **落库，且是那条** ✓ |

### 维度二：变异验证（三条新钉子真能红 / 两条旧缺口是否补齐）

每组变异在 `/tmp/br4/{m1..m5}`（各由 `git archive HEAD` 解出、无 `.git`）上跑**全量** suite：

| 变异 | 改什么 | 结果（原始输出） | 说明 |
|---|---|---|---|
| **M1** | 把 `:208-211` 改回旧顺序（`_set_ledger_gate_ref` 之后再比 `manifest.get("gate_ref") != gate_ref`） | **1 failed, 698 passed** —— `test_explicit_different_ref_rewrites_caller_and_syncs_the_ledger`；失败现场 stdout 逐字为 `init：已补齐台账里的 … 条目（ref 本来就是 …@v9.9.9，未改）` | B3-1 的钉子**真能红**，且**只打红它自己**；同时证明旧 bug 的**症状**与 r3 复现的一致 |
| **M2** | `caller_retarget_refusal` 的 `except` 改回 `return None` | **1 failed, 698 passed** —— `test_an_unreadable_caller_is_not_silently_overwritten` | B3-2 钉子**真能红且只打红自己** |
| **M3** | `:197` 的 `if changing_ref:` 改 `if False:` | **1 failed, 698 passed** —— `test_a_dry_run_ref_change_says_it_will_rewrite_not_backfill` | dry-run 侧新钉子**真能红且只打红自己** |
| **M4** | `:602` 的 `if handled:`（**冲突分支**）改 `if False` | **2 failed, 697 passed** —— `test_explicit_gate_ref_plus_conflicting_policy_writes_then_reports`、`test_dry_run_must_not_claim_it_wrote_anything` | 该文案**已被覆盖**。**注意**：在 **parent `125ea12`** 上跑同一变异（`/tmp/br4/pm4`）⇒ 也 `2 failed, 695 passed` ⇒ 覆盖**不是本 commit 新增的**，r3 的 M4 记「全绿」**与本仓实测不符**（r3 称变异点在 `:608`；`125ea12` 的两个 `if handled` 在 `:561` / `:595`，`:608` 不是判据行） |
| **M5** | 删掉 `:215` 的 `print(f"init：已补齐台账里的 …")` | **699 passed（全绿）** | 该 print **仍零覆盖**：`:613` 的用例靠**返回串**里的「补齐 / ref 未变」通过 ⇒ B3-3 第 2 条**残留** |

### 维度三：判据组合穷举（36 格）与拒绝面复核

探针 `/tmp/br4/matrix.py` 在 `/tmp/br4/base`（= HEAD 原样副本）上跑。`file=present/absent`、
`entry=present/absent/self`、`ref=same`（= `C.DEFAULT_GATE_REF`）/`diff`（`…@v9.9.9`）、
`content=same/hand`（`hand` = caller 被手改成 `name: hand-edited`）、`dry=real/dry`。
**每格跑完 `init` 之后一律再跑一次 `uninit`**。原始输出（节选；完整 36 行见 `/tmp/br4/matrix.out`）：

```
| file | entry | ref | cont | dry | exit | dup | gref | caller | uninit |
|---|---|---|---|---|---|---|---|---|---|
| present | present | same | same | real | 0 | 1 | same | same | 0 |
| present | present | same | hand | real | 1 | 1 | same | hand | 1 |
| present | present | diff | same | real | 0 | 1 | new  | NEW  | 0 |
| present | present | diff | hand | real | 0 | 1 | new  | NEW  | 0 |
| present | absent  | same | same | real | 0 | 1 | same | same | 0 |
| present | absent  | same | hand | real | 1 | 0 | same | hand | 0 |
| present | absent  | diff | same | real | 0 | 1 | new  | NEW  | 0 |
| present | self    | same | same | real | 1 | 1 | same | same | 0 |
| present | self    | diff | hand | real | 1 | 1 | same | hand | 0 |
| absent  | present | same | same | real | 1 | 1 | same | gone | 0 |
| absent  | absent  | same | same | real | 1 | 0 | same | gone | 0 |
| absent  | absent  | diff | same | real | 1 | 0 | same | gone | 0 |
| absent  | self    | same | same | real | 1 | 1 | same | gone | 1 |  ← uninit 半回滚，剩 init-manifest.json
```

**统计（脚本直接打印的原始行）**：

```
TOTAL ROWS: 36
dup>1 count: 0
dry/real exit mismatch keys: []
```

**结论**：

1. **`dup > 1` 的格子数 = 0** ⇒ B2-1 那条「插重复条目 ⇒ `uninit` 二次 `unlink`」在**全部组合下不可达**
   （与 r3 同一结论，本 commit 未触动该面）。
2. **dry-run 与真跑逐格同退出码**（18 对全相符，`mismatch keys: []`）——**在「内容可解码」这一整个面上**，
   R11 的 Y1 语义未被本 commit 破坏。
3. **`absent|absent|same`（无条目 + 无文件 + ref 同）仍退 1**（结构判据先于 ref 判据，`:237-257`）——
   r3 顺带修好的那条**行为**没被回退；但**仍无独立钉子**（见维度二 M5 之外的 B4-3 第 4 条）。
4. **B3-2 的修复没有引入新的拒绝缝**：新增的那条拒绝只在「ref 同 ∧ 文件在 ∧ 读不出」时触发。
   逐格复核（探针第二段，caller 字节 = `b"\xff\xfe not utf-8 \xff"`）：

   ```
   present|same|real  exit=1 preserved=True   ERR=无法按 --gate-ref 补台账：… 无法解码
   present|same|dry   exit=1 preserved=True   ERR=（同上）
   present|diff|real  exit=0 preserved=False  （ref 变 ⇒ 照常重写，文案为「已重写」）
   present|diff|dry   exit=1 preserved=True   ERR=init：… 无法解码：'utf-8' codec can't decode  ← B4-1
   absent |same|real  exit=1 preserved=True   ERR=无法按 --gate-ref 补台账：… 无法解码
   absent |diff|real  exit=0 preserved=False
   absent |diff|dry   exit=1 preserved=True   ERR=（同上）                                 ← B4-1
   self   |*   |*     exit=1 preserved=True   ERR=… 里 caller 那条被标成了 `self: true`
   ```

   - 「ref 同」那两格：修前是**静默覆盖 / 走漂移报红**（parent `125ea12` 上 `absent|same|real` 实测
     退 **0** 且文件被抹掉），修后一律**响亮退 1 且文件字节未动** ⇒ 修复有效，且**没有**把任何
     原本正确的格变成误拒（`entry=present ∧ ref 同` 修前后**都**退 1，只是文案从「漂移」变成「无法解码」）。

### 维度四：`changing_ref` 的求值时机与两处文案的一致性

- **求值时机**：`:194`（dry-run 分支**之前**）与 `:208`（真写分支**之前**、`_set_ledger_gate_ref`
  `:209` **之前**）**两处都正确**。`:194` 供 `:197` 的 dry-run 分叉；`:208` 供 `:211` 的真跑分叉，
  且**早于** `:327` 那次就地改写（`manifest["gate_ref"] = gate_ref`），因此不再恒假。**已实测**：
  真跑换 ref 的 stdout 现在是
  ```
  init：已重写 .github/workflows/witnessloop.yml（→ …/gate.yml@v9.9.9）并同步台账
  init：已接入 witnessloop（.github/workflows/witnessloop.yml 与台账已改成 …@v9.9.9）。
  ```
  台账 `gate_ref` 实测 `@v1 → @v9.9.9` ⇒ **文案与实际动作一致**（B3-1 已闭环）。
- **`--dry-run` 与真跑文案各自与实际动作一致**：dry-run 只打 `[dry-run] 将重写 … / 将补齐 …` 且
  `git` 状态不变（`:196-201` 在 `write_text` 之前返回）；真跑打 `已重写 … / 已补齐 …`（`:211-216`）。
  两条 dry 文案的新钉子（`:636`）经 M3 证明承重。
- **B4-2（洁癖，非缺陷）**：`:194` 与 `:208` 是**两次内容完全相同**的求值——`:194` 与 `:208` 之间
  没有任何代码改动 `manifest`（只有 `:204` 的 `path.write_text`，改的是**磁盘上的 caller**，
  不是台账 dict）。`:208` 这次重算是**冗余**的；`:205-207` 的注释解释的是「顺序」，不是「为什么两处」。
  **不改变行为**（M1/M6 类变异都只在顺序上做文章），仅作可读性提示。

### 维度五：前几轮登记「不修」项的现状复核

| 登记项 | 本轮复算（命令 + 原始输出） | 结论 |
|---|---|---|
| `created_files` 元素**非对象**仍崩 | 探针：把 `"not-an-object"` 追加进 `created_files` ⇒ `initcmd.py:542` `rel = entry.get("path")` 抛 `AttributeError: 'str' object has no attribute 'get'`，被 `entry.main` 兜住 ⇒ **exit 1 + `witnessloop：内部错误（AttributeError: …）`**（`None` / `[...]` 元素同型） | **仍如登记所说**（`:542` 无 `isinstance(entry, dict)` 守卫；本 commit 未触碰该循环） |
| `…@refs/heads/` 空后缀 | **按代码复核（未实跑 shell）**：`.github/workflows/gate.yml:88-89` 的 `*@refs/heads/*` 分支 ⇒ `REF="${WL_WORKFLOW_REF##*@refs/heads/}"` 在空后缀下得空串且**不**置 `FAILED` | **仍如登记所说**（登记为「上游不可能给出这个形态 ⇒ 不可达」） |
| `--gate-ref ""` 等价于不给 | 探针：`init --gate-ref ""` ⇒ **exit 0 + `init：已接入 witnessloop（幂等，无改动）。`**，台账与 caller **字节不变**（`run():374` 的 `args.gate_ref or …` 与 `:389` 的 `if args.gate_ref:` 都把空串当假值） | **仍如登记所说** |
| `uninit` 对手改台账的**半回滚** | 矩阵 `absent\|self\|*` 四格 ⇒ `uninit` **exit 1**，`.witnessloop/` 剩 `init-manifest.json`（`uninitcmd.py:53` 把 `self` 条目当「台账自己那条」放进 `doomed`，`:94` 的 `unlink()` 未防「不存在」）；本 commit `--numstat` **无** `uninitcmd.py` | **仍如登记所说**（既有、非本轮引入） |

### 维度六：文档一致性（判据③）

- 本 commit **未改动任何用户文档**（`--numstat` 只有 `initcmd.py` + `tests/` + 报告归档）⇒
  没有新增「文档承诺 ≥ 实现」的漂移面。上一轮 r3 已逐条核过 README 前提框与 `docs/gate.md §1.2`，
  本轮**未重跑**（改动不在这两条路径上）。
- 文档里出现的 `无法解码`（`README.md:248`、`docs/gate.md:363`）都是 **`check` 的事件文件**
  那条 finding 的引文，与本 commit 新增的 **`init` caller 无法解码** 是**两条不同的消息**，
  不存在引文失配。
- `spec.md:115-120`（`--dry-run` Scenario）与实现一致（dry-run 不落盘、不说「幂等」）；
  但它在「不可解码的 caller」这一**未列举前提**下会被 B4-1 分叉打到（见问题清单）。

### 未验证（明确登记，不计入问题清单）

1. **R1-S1 的端到端 Then**（`job.workflow_sha` = 被复用文件自己的 commit）：GitHub Actions 语义，
   本工作区无 Actions，**未复算**（与前三轮同一登记）。
2. **真 `uvx` 安装落的 `direct_url.json`**：仍是抄录载荷 + 手造 dist-info 覆盖读取环，**未**端到端验证。
3. **GHES 上 `job.*` 不可用**、**fork 判据必要不充分**：依据 spec/design 登记与 GitHub 文档，未实测。
4. **`docs/gate.md §1.2` 的 A/B/C 三条实跑主张**：本轮未重跑（改动不在这三条所指路径上）。
5. **`v1.7.0` 发布后的行为**：时序上不可验证。
6. **R1 / R2 / R3 / R5 的实现与钉子**：本轮只复算了 R4（`init --gate-ref`）相关；本 commit 未触及
   `gate.yml` / `checkcmd.py` / `uninitcmd.py` / `docs/`，其余四条**沿用前几轮结论，未逐条重新复算**。
7. **`…@refs/heads/` 空后缀**：只按 `gate.yml:88-89` 的代码形状复核，**未**实跑那段 shell。

## 问题清单

> 排序：行为不一致在前，覆盖/洁癖殿后。已闭环的 B3-1/B3-2/B3-4 只在下面第一段登记，不重复列条目。

**已闭环（本轮复核确认）**：**B3-1** 真跑报反（`:208` 求值时机 + `:75-76` 钉子，M1 红）；
**B3-2** 不可解码的 caller 静默覆盖（`:266-272` 拒绝 + `:647-665` 钉子，M2 红）；
**B3-4** 两处注释按事实改写（`:290-292` / `:314-317`）。

### B4-1 · 行为不一致（**非本 commit 引入**） · 低 —— caller 不可解码 ∧ `--gate-ref <不同 ref>` 时，`--dry-run` 退 1 而真跑退 0

- **位置**：`src/witnessloop/initcmd.py:596`（`conflicts = conflicting_files(root, desired)`，会在
  `read_text` 解码失败时抛 `ValueError`）与 `:600`（`conflicts = [item for item in conflicts if item[0] not in ignore]`
  ——`ignore` 过滤**排在抛点之后**）。
- **证据**：探针两格（caller 字节 `b"\xff\xfe not utf-8 \xff"`）：
  ```
  present|diff|real  exit=0 preserved=False
  present|diff|dry   exit=1 preserved=True  ERR=init：… 无法解码：'utf-8' codec can't decode
  absent |diff|real  exit=0 preserved=False
  absent |diff|dry   exit=1 preserved=True  ERR=（同上）
  ```
  同一状态、两条路径给出**相反退出码**；且 `--dry-run` 会先印 `init：[dry-run] 将重写 …（→ …@v9.9.9）并同步台账`，
  再在 stderr 报一句无法解码 ⇒ 自相矛盾。
- **归因**：**不是**本 commit 引入——在 parent `125ea12`（`/tmp/br4/parent`）上同一探针给出**相同**结果
  （`diff|real=0` / `diff|dry=1`）。但它是**本 change 新功能**（`init --gate-ref` 的已接入分支）内部的洞：
  `ignore` 这条轴的语义（`:509-513`「从两条判定里都排除掉」）没有覆盖到 `conflicting_files` 的**抛点**。
- **为什么是问题**：与 `initcmd.py:562-566` 自己立的 Y1 不变量和 `tests/test_init_gate_ref.py:467`
  （`test_dry_run_and_the_real_run_agree_on_a_hand_edited_caller`，用的是**可解码**的手改内容）矛盾——
  现有钉子只钉了「可解码」的同一个族，**漏了「不可解码」这一子集**。窄面 + fail-closed（真跑也会成功，
  只是 dry-run 先报红）⇒ **不阻塞**。
- **建议**（一处改动）：把 `:596` 的期望集先按 `ignore` 收窄，再交给 `conflicting_files`，例如
  `conflicting_files(root, {k: v for k, v in desired.items() if k not in ignore})`；
  或让 `conflicting_files` 对 `ignore` 里的路径不抛。并给 `:467` 的用例加一条**不可解码**变体。

### B4-2 · 代码洁癖 · 低 —— `changing_ref` 在同一函数里被求值两次（`:194` 与 `:208`，值恒等）

- **位置**：`src/witnessloop/initcmd.py:194` 与 `:208`。
- **证据**：两行文本逐字相同（`changing_ref = manifest.get("gate_ref") != gate_ref`）；两行之间只有
  `:204` 的 `path.write_text`（改磁盘上的 caller），**没有任何**代码改动 `manifest` 这个 dict
  ⇒ `:208` 的重算恒为冗余。`:205-207` 的注释解释的是「必须在改台账之前」，不是「为何两处都算」。
- **为什么是问题**：不改变任何行为（M1/M6 类变异都只在**顺序**上做文章），只是让「哪一处才是承重的」
  变模糊——将来若有人只删 `:208` 而不删 `:194`，真跑分支仍正确；只删 `:194` 则 dry-run 分支要么
  `NameError` 要么退回旧写法。**不阻塞**。
- **建议**：把 `:194` 那处改成注释指向 `:208`，或干脆两处合并成一处（`changing_ref` 在 dry-run
  `if` 之前算一次、真写分支复用同一变量）。

### B4-3 · 覆盖缺口（B3-3 的残留） · 低 —— 两处仍未钉住

- **证据**（全绿变异的原始输出）：
  1. `:215` 的真跑 `已补齐` **print**：**M5**（删掉该行）⇒ `699 passed（全绿）`——`:613` 的用例
     靠**返回串**里的「补齐 / ref 未变」通过（print 与 return 是两句不同的话）。
  2. `absent|absent|same`（无条目 + 无文件 + **同 ref**）的响亮拒绝：矩阵里该格实测退 1，但现有
     `tests/test_init_gate_ref.py:383` 的用例走的是 `NEW_REF` ⇒ **同 ref** 这一支无独立钉子。
  （**注**：r3 记的第 3 条「`handled` 冲突文案零覆盖」经本轮 **M4 实测为误记**——该文案**已有** 2 条
  用例覆盖，且在 parent 上同样覆盖，见维度二。）
- **为什么是问题**：两处都**不改退出码**（只是 print 文本 / 拒绝理由是否被钉），危害与前几轮同族；
  **不阻塞**。
- **建议**：各补一行断言（`assert "已补齐" in out` 用**真跑 stdout**；`absent|absent|same` 加一条
  走 `OLD_REF` 的用例）。

## Verdict

**有条件通过。**

- 判据①（无未解决行为缺陷）：**上一轮的放行条件已闭环**——B3-1 真跑报反已修（`:208` 时机 + `:75-76`
  钉子，M1 复现旧症状、修后实测文案与动作一致），B3-2 已修（M2 + 探针：文件字节未动）。
  **残留一条低危行为不一致 B4-1**（不可解码的 caller + 换 ref：dry 退 1 / 真跑退 0），
  系**既有**（parent 同现象）、窄面、fail-closed ⇒ 列为**非阻塞**，但**未消除**。
- 判据②（每条 Requirement 有实现 + 钉子）：**R4 满足**（`spec.md:100-138` 的 5 个 Scenario 各有实现与
  用例：`:104`/`:146`/`:209`+`:270`/`:303`+`:383`/`:239`，本轮复算相关那份）；**R1 / R2 / R3 / R5 未复算**
  （见「未验证」6，本 commit 未触及它们所指的文件）。
- 判据③（无「文档承诺 ≥ 实现」漂移）：**满足**。本 commit **未改**用户文档，无新增漂移面；
  现有引文（`README.md:248` / `docs/gate.md:363`）与本 change 的消息不冲突。
- 判据④（上一轮放行条件确实已用 `--stat` 核过）：**满足**。`git show --numstat 58601b8` 逐条核过
  B3-1…B3-4，实体与自述一致；B3-1 的钉子经 M1 **真能红**且只打红自己。

**放行条件（一条，一处改动 + 一条用例）**：修 **B4-1** —— 让 `_already_initialized` 在把 `desired`
交给 `conflicting_files` **之前**先按 `ignore` 收窄（`initcmd.py:596`），使「不可解码的 caller + 换 ref」
在 `--dry-run` 下与真跑**同退出码**，并给 `tests/test_init_gate_ref.py:467` 加一条不可解码变体。

**不阻塞**：B4-2（`changing_ref` 重复求值，洁癖）、B4-3（`:215` print 与 `absent|absent|same` 两处覆盖）、
以及维度五复核为「仍如登记所说」的四项历史登记（`created_files` 元素非对象 ⇒ `:542` `AttributeError`、
`…@refs/heads/` 空后缀、`--gate-ref ""` 等价于不给、`uninit` 对手改台账的半回滚）。

**未验证项**（不因此改变判定，但**不宣称**已验证）：R1-S1 的真 CI 端到端语义；真 `uvx` 安装落的
`direct_url.json`；GHES 上 `job.*` 不可用；`v1.7.0` 发布后的行为；R1/R2/R3/R5 的实施与钉子；
`…@refs/heads/` 空后缀的实跑（仅按代码复核）。
