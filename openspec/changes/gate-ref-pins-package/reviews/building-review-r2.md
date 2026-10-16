# building-review-r2 — gate-ref-pins-package

## Reviewer

- **角色**：独立、零记忆的**实现后**审阅（building / **B2** 轮）。本对话**不携带**该 change 的
  任何实现历史；`design.md` / `tasks.md` / `specs/` / 提交说明里的「已落库」「实测」「已收敛」
  一律当**待验证断言**处理。我不是作者，**未改写任何实现**，只产出本报告。
- **审阅对象（revision 绑定）**：worktree `/home/happy/wl-wt/archive-arrival-recognition`，
  分支 `gate-ref-pins-package/2026-10-16`，
  HEAD = `c9568cc8c1a7d2eaadec372b77528d292a35987d`（`git rev-parse HEAD` 原始输出）。
  上一轮审阅（`reviews/building-review.md`，**只读、未改**）针对 `5bb7765`；本轮针对 `c9568cc`。
- **验收标准**：`openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md`
  （5 条 Requirement / 10 个 Scenario）——规格是唯一判据，`design.md` / `tasks.md` 只作线索。
- **基线**：`PYTHONPATH=src python3 -m pytest -q` ⇒ **694 passed**（在 `/tmp/br2/src` 副本上复算，
  副本由 `git archive HEAD | tar -x` 生成；六个被改动文件与 worktree 逐字节相同（`cmp -s` 全 same））。
- **方法**：
  1. `git show --stat c9568cc` / `--numstat c9568cc` 逐条核对上一轮「问题清单」B1-1…B1-10 的
     **落库实体**（不信处置表、只信 diff + 代码行）；
  2. **动手变异**：5 组实现侧变异，每组跑**全量** suite（M1/M2/M3 验上一轮的钉子真能红，
     M4/M5 探本轮新增分支的覆盖）；
  3. 边界态实跑：同 ref / 缺条目 / self 标记 / 手改 caller / `--dry-run` 的组合，**在
     `5bb7765` 与 `c9568cc` 两个 revision 上各跑一遍**做前后对照；
  4. 文档对照：`README.md` 新前提 vs `docs/gate.md §1.1/§1.2` vs `spec.md`。
- **快照纪律**：全部实验在 `/tmp/br2/`（`git archive` 解出的副本，**无 `.git`**）；
  真仓内**未**做任何 commit / reset / tag / push。
- **证据约定**：每条结论带 `文件:行号` 或「命令 + 原始输出」。**没复算的一律标「未验证」**。

## 审阅结论

**上一轮的三个放行条件都真的落了库**，且落的**就是**那条所指的东西（`--stat` + 代码/测试实体
逐条核过，B1-1/B1-2 的钉子经变异确认**真能红**，B1-3 的两处注释按事实改写且改写后的措辞
在 `caller_retarget_refusal` 内**成立**）。**但是**：B1-5 的修复（`sync_caller_gate_ref` 早退条件
放宽）在「**ref 相同 + caller 条目被标 `self: true`**」这一态上**新开了一条与它自己要修的
同族半回滚路径**——我实跑复现：`init` 退 **0** 并报「条目已补齐」，台账里**插出两条同路径条目**，
随后 `uninit` 二次 `unlink` 抛 `FileNotFoundError`、「已回滚」已打印、台账留在盘上。
这**恰好**是对抗轮 R11 的 Y2 / R9 的 W3 花了两轮去堵的那个态（`initcmd.py:232-243` 的注释与
`tests/test_init_gate_ref.py:482-509` 的用例都写着「否则会重复条目 ⇒ uninit 二次 unlink ⇒ 半回滚」），
只是那条守卫在**同 ref** 时被 `initcmd.py:222` 的早退绕过。⇒ 判据①（无未解决行为缺陷）**不满足**。

另有 5 条低危项（1 条新注释撒谎、1 处文案指向不存在的「下句」、1 处静默覆盖、1 处 dry-run 文案不准、
本轮新增的 2 个用户可见输出零覆盖），以及 1 条 README 新前提未兑现 B1-6 原意。
上一轮的 B1-4 / B1-8 / B1-10 三条**未落库**——`c9568cc` 的 `--stat` 里没有任何一处触及它们所指的行，
这与上一轮「B1-4…B1-10 不阻塞」的放行口径一致，**不**计入缺陷，但**本文不替它们背书**。

## 逐维度结论

### 维度一：上一轮「问题清单」逐条落库核对（`--stat` + 实体）

`git show --numstat c9568cc` 原始输出：

```
3	0	README.md
306	0	openspec/changes/gate-ref-pins-package/reviews/building-review.md
38	9	src/witnessloop/initcmd.py
35	0	tests/test_check_package_ref.py
2	2	tests/test_gate_workflow.py
47	0	tests/test_init_gate_ref.py
```

| 上轮项 | 自述 | 实体核对（`--stat` + 代码/测试行） | 判定 |
|---|---|---|---|
| **B1-1**（放行条件） | 已落 | `tests/test_check_package_ref.py:182-214` 新增 `test_installed_vcs_ref_reads_a_real_dist_info`：造**真** dist-info 上 `sys.path`，断言 `checkcmd.installed_vcs_ref()` 读出 `("v1.7.0", "ae9925…")`。变异 M1（把 `checkcmd.py:76` 改成 `return None, None`）⇒ **1 failed / 693 passed**（红） | **落库，且是那条** ✓ |
| **B1-2**（放行条件） | 已落 | `tests/test_init_gate_ref.py:542-556` 新增 `test_the_drift_branch_also_says_the_caller_half_landed`：手改 **policy** 命中漂移分支，断言 `err` 含「被改动过」+「已落盘、不回滚」。变异 M2（删掉 `initcmd.py:533-536` 的 `if handled: print(...)`）⇒ **1 failed / 693 passed**（红） | **落库，且是那条** ✓ |
| **B1-3**（顺手订正） | 已落 | `initcmd.py:252-258`（`caller_retarget_refusal` 内）与 `initcmd.py:280-281`（`_set_ledger_gate_ref` 内）注释改写。**前半条订正属实**：在该函数内，「走到 `:246` 就说明没有任何 caller 条目带 `self`」（`:232` 已把带 `self` 的全部拦下）⇒「当前不可达」在该函数内**成立**。**后半条（`:280-281`）不成立** ⇒ 见 **B2-2** | 半落：措辞换对了，但新写的另一处注释撒谎 |
| B1-4 | 未提 | `initcmd.py:224-226` 的 `return None  # 结构非法，同上` **一字未动**（`--stat` 无对应新增行） | 未落库（不阻塞） |
| **B1-5** | 已落 | `initcmd.py:168-181` 早退条件改宽（ref 相同 **且** 有非 self 的 caller 条目才 no-op）；`:201-206` 真跑按 ref 是否真变分叉文案；`tests/test_init_gate_ref.py:512-539` 新增钉子（变异 M3 把早退改回旧形态 ⇒ **1 failed / 693 passed**，红）。**但这条修复自己带出新缺陷** ⇒ **B2-1** | 落库，**同时引入 B2-1** |
| B1-6 | 已落 | `README.md:183-185` 新增前提框。**内容与 B1-6 的原意不同**（B1-6 要的是「那份 `uses:` 指向的 ref 里已含本 change 的 gate.yml」这个限定语）⇒ **B2-7** | 表面落库，原意未兑现 |
| B1-7 | 已落 | `initcmd.py:571-584` 冲突文案按 `handled` 分叉。**分叉本身实现正确**（组合语义路径不再出现「要更换 policy 请先 `uninit`」），但新文案自带一处悬空指代 ⇒ **B2-3**；且该分支零覆盖 ⇒ **B2-6** | 落库（有残留文案问题） |
| B1-8 | 未提 | 「抽 helper 去重」未做（`initcmd.py:218-226` 与 `:164-181` 仍是两段重复前言） | 未落库（不阻塞） |
| **B1-9** | 已落 | `tests/test_gate_workflow.py:504` 改成 `assert f"ref={_fallback_ref()}" in …`；`_fallback_ref()`（`:277-283`）从 gate.yml 的 `env.WL_FALLBACK_REF` 读数（现值见 `.github/workflows/gate.yml:66` = `"v1"`）⇒ 断言与被测输出的**取值同源**，post-merge 挪默认值时不再靠子串侥幸 | **落库，且是那条** ✓ |
| B1-10 | 未提 | `tasks.md` / `design.md` **未被本 commit 触及**（`--stat` 里没有这两个文件） | 未落库（不阻塞） |

> 注：上一轮报告 `reviews/building-review.md` 本身是在 **c9568cc 里**新增的（`306 +`），
> 属正常归档，**不是**「上一轮报告被改写」——我复核了它是新增文件（`--numstat` 为纯新增）。

### 维度二：变异验证（钉子真的能红吗）

在 `/tmp/br2/{m1..m5}`（各自由 `git archive HEAD` 解出）上做 5 组实现侧变异，每组跑**全量** suite：

| 变异 | 改什么 | 结果 | 原始输出要点 |
|---|---|---|---|
| **M1** | `checkcmd.py:76` → `return None, None`（B1-1 那一环） | **1 failed / 693 passed** | `FAILED tests/test_check_package_ref.py::test_installed_vcs_ref_reads_a_real_dist_info` |
| **M2** | 删 `initcmd.py:533-536` 漂移分支的 `handled` 打印（B1-2 那一行） | **1 failed / 693 passed** | `FAILED tests/test_init_gate_ref.py::test_the_drift_branch_also_says_the_caller_half_landed` |
| **M3** | `initcmd.py:173-181` 早退条件改回 `if manifest.get("gate_ref") == gate_ref: return None`（B1-5 的旧语义） | **1 failed / 693 passed** | `FAILED tests/test_init_gate_ref.py::test_same_ref_but_a_missing_caller_entry_repairs_the_ledger`（`:532` 断言 `"幂等" not in out`） |
| **M4** | 删 `initcmd.py:205` 的「已补齐台账里的 … 条目」**print** | **694 passed（全绿）** | 无失败 ⇒ 这条新输出**零覆盖**（**B2-6**） |
| **M5** | `initcmd.py:579` 的 `if handled` → `if False`（新冲突文案永不出现） | **694 passed（全绿）** | 无失败 ⇒ B1-7 新增的那段文案**零覆盖**（**B2-6**） |

**判定**：上一轮的两条放行钉子（M1/M2）经变异确认**真能红**，且各自只打红自己那一条（无
误伤、无遮蔽）。B1-5 的钉子（M3）也真能红。**但**本轮新增的另外两处用户可见输出
**没有任何用例经过**——与上一轮判为放行条件的 B1-2 是**同一类**（「本轮新增的用户可见输出分支
零覆盖」），只是危害更低（一个是信息行、一个是提示语，都不改变退出码）。

### 维度三：B1-5 新语义的中间态（本轮的重点）

`sync_caller_gate_ref` 的新早退条件（`initcmd.py:170-181`）要求「ref 相同 **且** 台账里有
**一条非 `self` 的** caller 条目」才算无事可做。我按 `run()` 的接线顺序
（`:353-361` `caller_retarget_refusal` → `:383-387` `sync_caller_gate_ref`）逐态实跑：

**（a）同 ref + 条目被标 `self` + 文件在盘上 ⇒ 台账被插出重复条目，`uninit` 半回滚（B2-1）**

实跑（`/tmp/br2/src` 上的探针，原始输出）：

```
== same-ref self-flag == 0 OUT: init：已补齐台账里的 .github/workflows/witnessloop.yml 条目（ref 本来就是 …@v1，未改）
init：已接入 witnessloop（台账里的 .github/workflows/witnessloop.yml 条目已补齐（ref 未变））。
paths: ['.witnessloop/policy.json', '.github/workflows/witnessloop.yml', '.github/workflows/witnessloop.yml', '.witnessloop/init-manifest.json']
== uninit == 1
uninit：已回滚 witnessloop 接入：
  - .witnessloop/policy.json
  - .github/workflows/witnessloop.yml
ERR: witnessloop：内部错误（FileNotFoundError: … '.github/workflows/witnessloop.yml'）
```

**同一探针在 `5bb7765`（上一轮 revision）上**：

```
== same-ref self-flag == 0 OUT: init：已接入 witnessloop（幂等，无改动）。
paths: ['.witnessloop/policy.json', '.github/workflows/witnessloop.yml', '.witnessloop/init-manifest.json']
== uninit == 0
```

⇒ **这是 `c9568cc` 引入的回归**。根因两跳：① `caller_retarget_refusal:222` 的
`or manifest.get("gate_ref") == gate_ref: return None` 让 Y2 的 self 守卫在**同 ref** 时整条被绕过；
② `sync_caller_gate_ref:173-180` 的早退把「带 `self` 的 caller 条目」判为「不满足有事可做」⇒ 落入写盘路径；
③ `_set_ledger_gate_ref:277-285` 的循环因 `not entry.get("self")` 不匹配，走 `else` **新插一条同路径条目**。
③ 正是 `initcmd.py:232-243` 的注释与 `tests/test_init_gate_ref.py:482-509` 明说要避免的下场。

**（b）同 ref + 条目在 + 文件不在** ⇒ 仍是静默 no-op（`EXIT 0`「幂等」）——与上一轮一致，
B1-5 未触及；该态下 `uninit` 无半回滚风险（无文件可删），可接受。

**（c）同 ref + 缺条目 + `--dry-run`** ⇒ 台账不变（`(repo/C.INIT_MANIFEST_PATH).read_bytes()` 比对 True），
退 0，与真跑同结论（Y1 语义未被破坏）✓。**但文案不准** ⇒ **B2-5**。

**（d）同 ref + 缺条目 + caller 被手改** ⇒ 真跑**静默覆盖**手改内容（`EXIT 0`），
而**不带 `--gate-ref`** 的 plain `init` 对**同一状态**是响亮的冲突 `EXIT 1`（`conflicting_files` 判
磁盘 ≠ 期望）。对照：`5bb7765` 在该态下 `caller now: name: hand-edited`（保留手改、退 1）⇒ **B2-4**。

### 维度四：文案分叉（B1-7）与文档

- **组合语义路径（有 `--gate-ref`）**：实跑输出

  ```
  init：注意——.github/workflows/witnessloop.yml 已按显式 `--gate-ref` 处理（**已落盘、不回滚**）；下面报的是**别的**文件：
  init：检测到冲突（已接入，但本次指定的内容与已落地不同；只增不改，拒绝覆盖。⚠️ 但**别照下句做**：本行的冲突与你那条显式 `--gate-ref` 无关，而 `uninit` 会把 caller 与台账一起删掉。policy 那条轴要单独解决。）：
  ```

  规格该 Scenario 的两条 Then（点明「caller 已落盘、不回滚」+ 不让用户以为要去删 policy）**都满足**；
  但「**别照下句做**」的**下句不存在**（该分支恰好把那句替换掉了，后面直接是 `）：` 与 diff）⇒ **B2-3**。
- **`else` 分支（无 `--gate-ref`）**：仍打「要更换 policy 请先 `uninit`」，与 `5bb7765` 一致 ✓。
  但注意：**定制 policy 的仓 + plain `init --policy <不同>`** 这一态仍会打到这句，而 `docs/gate.md
  §1.2:117` 明说它「不可照做」——B1-7 的修复只覆盖了带 `--gate-ref` 的路径（该路径**不在** spec
  任何 Scenario 的 Given 里，故**不算**规格违反，仅登记为观察）。
- **`docs/gate.md §1.2:106` 的引文**（它引用的是**旧 CLI** 场景的输出）仍然成立 ✓；
  `:117` 那句（定制 policy 的仓会看到「要更换 policy 请先 `uninit`」）在带 `--gate-ref` 时
  **已不再逐字对应实现**（实现改说「别照下句做…」）——低危文档漂移，并入 **B2-3** 的备注。
- **`README.md:183-185` 新前提** vs `docs/gate.md §1.2` / `spec.md`：**不一致** ⇒ **B2-7**。
  `spec.md` 与 §1.2 都**没有**「先写 `@v1`、其余语义完全一样」这种说法；§1.2 的做法是给出
  ①② 两步与「定制 policy 的仓不满足该 Then」的前提。而 README 新前提给的限定语是
  「本仓已发布含本 change 的 ref（v1.7.0 起）」，**不是** B1-6 要的「那份 `uses:` 指向的 ref 里
  是否含本 change 的 gate.yml」；正文那句「**改一处、两处跟着走**」仍**无任何限定**地立着。

### 维度五：测试卫生

- `--numstat` 显示本轮测试改动**全是纯新增**（`35 +0` / `47 +0`），**没有**「从别的文件挪过来」
  的用例；`tests/` 全目录也没有新增重名用例
  （`grep -rhoP '^def (test_\w+)' | sort | uniq -d` 命中的 4 个重名**都不在本轮 diff 里**）。
- 三条新用例可**单独跑通**（`pytest <3 个 nodeid> -q` ⇒ `3 passed`），无顺序依赖。
- `test_installed_vcs_ref_reads_a_real_dist_info` 是**真**读 dist-info：宿主环境
  `python3 -c "importlib.metadata.distribution('witnessloop')"` ⇒ `PackageNotFoundError`，
  `src/` 下也没有 `.egg-info` / `.dist-info` ⇒ 用例只可能命中它自己造的 `tmp_path`；M1 证明它承重。
- 未见残留：`test_gate_workflow.py` 的两处改动是同文件内的字面量订正（`2 2`），无悬挂引用。

### 未验证（明确登记，不计入问题清单）

1. **R1-S1 的端到端 Then**（`job.workflow_sha` = 被复用文件自己的 commit）：GitHub Actions 语义，
   本工作区无 Actions，**未复算**（与上一轮同一登记）。
2. **真 `uvx` 安装落的 `direct_url.json`**：本轮的 B1-1 钉子用**手造** dist-info 覆盖了
   `installed_vcs_ref()` 的读取环，但**仍未**在真 uv 安装上端到端验证；`REAL_DIRECT_URL` 是抄录载荷。
3. **GHES 上 `job.*` 不可用**、**fork 判据必要不充分**：依据 spec/design 登记与 GitHub 文档，未实测。
4. **`docs/gate.md §1.2` 的 A/B/C 三条实跑主张**：本轮**未**重跑（上一轮复现过，本轮代码在
   这三条所指路径上无改动——B2-1/B2-4 是**新增**路径，不在这三条覆盖内）。
5. **`v1.7.0` 发布后的行为**（`DEFAULT_GATE_REF` 挪动、README ①′ recipe）：时序上不可验证。

## 问题清单

> 排序：行为缺陷在前，注释/文案/覆盖/文档殿后。每条带类别 + 严重度 + 证据。

### B2-1 · 行为缺陷（回归） · 中 —— 同 ref + caller 条目被标 `self` ⇒ 插重复条目，`uninit` 半回滚且 `init` 自称成功

- **位置**：`src/witnessloop/initcmd.py:173-181`（新早退条件）/ `:222`（`caller_retarget_refusal` 的同 ref 早退）
  / `:277-285`（`_set_ledger_gate_ref` 落到 `else` 新插条目）。
- **证据**（`5bb7765` vs `c9568cc` 同探针对照，原始输出见维度三(a)）：
  `c9568cc` 下 `init --gate-ref <与台账相同的 ref>` 退 **0**，台账 `created_files` 变成
  `[…, '.github/workflows/witnessloop.yml', '.github/workflows/witnessloop.yml', …]`（同路径两条），
  随后 `uninit` 退 **1** 并打 `witnessloop：内部错误（FileNotFoundError: …）`，此前已打印「已回滚」、
  且**把 policy 删了**（半回滚）；`5bb7765` 下同一探针退 0「幂等，无改动」、台账无重复、`uninit` 退 0。
- **为什么是问题**：这正是 **R11 的 Y2 / R9 的 W3** 花两轮堵掉的态——`initcmd.py:232-243` 的注释与
  `tests/test_init_gate_ref.py:482-509` 的 docstring 逐字写着「否则 … 同路径出现两次 ⇒ 随后 `uninit`
  二次 `unlink` 抛 `FileNotFoundError`（「内部错误」+ 已打印「已回滚」+ 台账留在盘上）」。
  B1-5 的修复目标是「不再半回滚」，**结果在同 ref 这一支上新开了一条同族半回滚**，且**现有用例看不见**
  （`:500-509` 那条用的是 `NEW_REF`，走的是「ref 不同 ⇒ 早退不触发 ⇒ 守卫生效」那一支）。
- **建议**（任选其一，均为一处改动）：把 `:222` 的同 ref 早退**移到** self 守卫之后（让「条目被标
  `self`」无论 ref 是否相同都响亮拒绝）；或在 `sync_caller_gate_ref` 的新早退里把「存在带 `self` 的
  caller 条目」也判为**不能**走补齐路径（返回 `None` 交给上游拒绝）。并补一条**同 ref** 的用例。

### B2-2 · 注释撒谎 · 低 —— 新写的注释断言「不可达 / 在入口就被拒绝」，与 B2-1 直接矛盾

- **位置**：`src/witnessloop/initcmd.py:280-281`（`_set_ledger_gate_ref` 里本轮**新加**的注释）。
- **证据**：注释写「`not entry.get("self")`：…**当前不可达**（被标 self 的 caller 条目**在入口就被拒绝了**，
  见那里）」。但 `caller_retarget_refusal:222` 在 `manifest.get("gate_ref") == gate_ref` 时**先 return None**，
  self 守卫（`:232-243`）**根本不会执行**；B2-1 的实跑就是这个反例（该守卫**被走到**并把
  `_set_ledger_gate_ref` 推进了重复插入的 `else` 支）。⇒ 与 B1-3 要修的是**同一类**缺陷
  （注释宣称的必要性/可达性与事实不符），只是换了一处、且这次还反过来。
- **为什么是问题**：读代码的人会以为「self 守卫在 `_set_ledger_gate_ref` 里纯属冗余」，从而
  在排查 B2-1 类问题时**跳过**它；而它恰恰是承重的（删掉它反而会走「匹配那条 self 条目并改 sha」的
  正常支——**恰好**消除重复插入——所以这段注释的因果也说反了）。
- **建议**：随 B2-1 的修复一并按事实改写。

### B2-3 · 文案 · 低 —— 冲突文案的 handled 分支指向一个不存在的「下句」

- **位置**：`src/witnessloop/initcmd.py:577`（`"⚠️ 但**别照下句做**：…"`）。
- **证据**：实跑输出（维度四）中，该分支把原本的「**要更换 policy 请先 `uninit`**」替换掉了，
  于是这句后面直接跟 `）：` 与 diff ——**没有任何「下句」**。对照 `else` 分支（`:580`）
  才是那句被指的文本。无任何用例断言这段文案（变异 M5 ⇒ 694 全绿）。
- **附**：`docs/gate.md:117` 仍以「那句『要更换 policy 请先 `uninit`』**不可照做**」的措辞描述
  定制 policy 的仓，而该路径（带 `--gate-ref`）实现已不再打那句 ⇒ 引用面轻微过时。
- **建议**：把「别照下句做」改成自足表述（如「⚠️ **不要**为这行冲突去 `uninit`：…」），
  并在 §1.2 的对应句里注明「该路径的文案已按 `handled` 分叉」。

### B2-4 · 行为 / 一致性 · 低 —— 补齐路径静默覆盖手改过的 caller（`EXIT 0`），与 plain `init` 的响亮冲突相反

- **位置**：`src/witnessloop/initcmd.py:197-206`（补齐路径无条件 `path.write_text(content)`）。
- **证据**：维度三(d)——同 ref + 缺条目 + caller 内容为 `name: hand-edited`：
  `c9568cc` 下退 **0**，caller 被改写回 `caller_workflow(gate_ref)`，输出只说「条目已补齐（ref 未变）」，
  **不提文件被重写**；`5bb7765` 下退 1、手改内容保留。同一状态下不带 `--gate-ref` 的 plain `init`
  是 `EXIT 1`「检测到冲突」。
- **为什么是问题**：`--gate-ref` 的「显式意图优先」在 **ref 未变**时并不成立（用户没要求换 ref），
  却拿它当覆盖凭据；且与 `init` 自己的「只增不改」判定对**同一状态**给出相反结论。
- **建议**：补齐时若盘上内容 ≠ `caller_workflow(gate_ref)`，改为**响亮拒绝**（或至少把
  「已重写 caller」写进输出）；不阻塞合并（需要「缺条目 + 手改 caller」两个手工态同时成立）。

### B2-5 · 文案 · 低 —— 补齐态下 `--dry-run` 说「将一起改成 <同一个 ref>」

- **位置**：`src/witnessloop/initcmd.py:193-195`（dry-run 早于「ref 是否真变」的分叉）。
- **证据**：实跑（维度三(c)）`--dry-run --gate-ref <同 ref>`、台账缺条目 ⇒
  `init：[dry-run] 将重写 …（→ …@v1）并同步台账` / `[dry-run] 未落盘：… 与台账将一起改成 …@v1`。
  而真跑路径已经为同一态准备了准确文案（`:205`「ref 本来就是 …，未改」）⇒ 两条路径对**同一状态**
  的**描述**不一致（退出码一致，不违反 Y1）。
- **建议**：把 dry-run 的返回句也按 `manifest.get("gate_ref") == gate_ref` 分叉。

### B2-6 · 覆盖缺口 · 低 —— 本轮新增的两处用户可见输出零覆盖

- **位置**：`src/witnessloop/initcmd.py:205`（「已补齐台账里的 … 条目」print）与 `:571-584`
  （`handled` 分支的新冲突文案）。
- **证据**：变异 **M4**（删 `:205` 的 print）⇒ **694 passed**；变异 **M5**（`:579` 的 `if handled`
  改 `if False`）⇒ **694 passed**。两者都**没有**任何用例变红。
- **为什么是问题**：与上一轮判为**放行条件**的 B1-2 同类（「本轮新增的用户可见输出分支零覆盖」）——
  同一轮里，作者为 B1-2 补了钉子，却在自己新增的另外两处输出上又留了同样的洞。
  危害更低（信息行 + 提示语，都不动退出码），故**不**列为放行条件。
- **建议**：各补一条断言（`"条目已补齐" in out` / `"别照下句做" not in err` 或正向断言新文案）。

### B2-7 · 文档 · 低 —— README 新前提未兑现 B1-6 的原意，且与本节 ① 的自述矛盾

- **位置**：`README.md:183-185`（本轮新增的前提框）；对照的事实：`.github/workflows/gate.yml`
  在 `v1` 里**没有** `wl-ref` 解析 step（`git show v1:.github/workflows/gate.yml | grep -n "wl-ref\|workflow_sha"`
  ⇒ **无输出**），`v1` 的 `init` **没有**重写语义（`git show v1:src/witnessloop/initcmd.py | grep -n
  "def sync_caller_gate_ref"` ⇒ **无输出**；`v1` 已有 `--gate-ref` 但只作用于新仓，见 `v1` 的 `run()`）。
- **证据/矛盾点**：
  1. B1-6 要的限定语是「**那份 `uses:` 指向的 ref 里已含本 change 的 gate.yml**」——新前提给的却是
     「本仓已发布含本 change 的 ref（v1.7.0 起）」，**两个条件并不等价**（指 `@main` 可满足前者不满足后者）；
     正文的「**改一处、两处跟着走**」（`README.md:187-190`）**仍无任何限定地立着**。
  2. 「其余步骤与语义完全一样」在 `@v1` 窗口**不成立**：该窗口下第 ② 步的「重写 caller + 同步台账」
     语义**不存在**——这正是**同节 15 行之后**的 `README.md:199-203`「⚠️ 第 ① 步不能省：重写 caller 的
     语义是**新版包**才有的」在说的话。
  3. 与 `README.md:210-212`（已有的「`v1.7.0` 发布之前，请仍然钉 `@v1`」）**重复**，且新的这句更弱化风险。
- **建议**：把前提框改成 B1-6 的原意（「前提：你 caller 的 `uses:` 指向的那份 ref 里**已含本 change
  的 gate.yml**；`v1`（现状）不含 ⇒ 该窗口内『改一处、两处跟着走』不成立，请按 §1.2 的
  能力边界理解」），删掉「其余步骤与语义完全一样」。

## Verdict

**有条件通过。**

- 判据①（无未解决行为缺陷）：**不满足**。B2-1 是 `c9568cc` **引入**的行为回归（`5bb7765` 无此问题），
  后果与上一轮/对抗轮反复堵的那个「半回滚 + 自称成功」同族，且现有用例看不见。
- 判据②（每条 Requirement 有实现 + 钉子）：**满足**。R1/R2/R4/R5 的钉子与上一轮一致；R3 的
  最后缺环（B1-1）已补且经变异确认真能红 ⇒ 5 条 Requirement 的主干都有实现 + 钉子。
  （B1-2/B1-5 的钉子同样经变异确认真能红。）
- 判据③（无「文档承诺 ≥ 实现」漂移）：**基本满足**。未发现规格级超卖；R1 的能力边界仍如实登记。
  低危项 B2-3/B2-7 属措辞与自述矛盾（B2-7 的「语义完全一样」在 `@v1` 窗口不成立），**不阻塞**。
- 判据④（上一轮放行条件确实已落库，用 `--stat` 核过）：**满足**。B1-1 / B1-2 / B1-3 三条都
  落了库、且落的**就是**那条所指的东西（B1-3 只在 `_set_ledger_gate_ref` 那半留有 B2-2）。

**放行条件（一条，一处改动 + 一条用例）**：修 B2-1 —— 让「caller 条目被标 `self: true`」在
**ref 相同**时也走**响亮拒绝**（或让 `sync_caller_gate_ref` 不在该态走补齐路径），
并补一条**同 ref** 的用例（钉住「台账不得出现同路径两条条目、`uninit` 不得半回滚」）。

**不阻塞**：B2-2（随 B2-1 一并改注释）、B2-3、B2-4、B2-5、B2-6、B2-7；
B1-4 / B1-8 / B1-10 仍未落库（与上一轮「不阻塞」的口径一致）。

**未验证项**（不因此改变判定，但**不宣称**已验证）：R1-S1 的真 CI 端到端语义；真 `uvx` 安装落的
`direct_url.json`（本轮只用手造 dist-info 覆盖了读取环）；GHES 上 `job.*` 不可用；`v1.7.0` 发布后的行为。
