# Grill（对抗轮 R4）：gate-ref-pins-package —— 独立零记忆证伪

## Reviewer

我是**独立零记忆**的对抗验证者（本对话不携带该 change 的任何历史）：`proposal.md` / `design.md` /
`tasks.md` / `specs/gate-ref-pinning/spec.md` 与三份 review 里的「实测」「文件:行号」「已落库」
「已裁定」「已收敛」一律当**待验证断言**，可复算的一律复算，**目标是证伪结论本身**。

**基准 revision（本仓在本轮审阅期间被并发移动了四次，这一节必须读）**

| 时刻 | HEAD | 说明 |
|---|---|---|
| 我开始时 | `315574c` | 我读 `tasks.md` / `spec.md` / `docs/gate.md` 的版本 |
| 审阅中 | `af57236` | 主 session 落库「兜底 ref 措辞清理 + §3 revision 绑定订正」 |
| 我的一次**事故** | `da3db40` | **我的**误提交（见下「事故与还原」），已 `git reset --mixed` 撤销 |
| 收尾时 | `1b59eb6` | 主 session 落库「台账缺 caller 条目的钉子 + init 收尾话 + K8 行」 |

**本报告的行号与 blob 一律以 `af57236` 为准**（= 我实际逐条复核的那棵树）：

| 文件 | blob（`git rev-parse af57236:<路径>`） |
|---|---|
| `HEAD` | `af5723669091ed6b2bb9df2d7644d48bb9674a42` |
| `openspec/changes/gate-ref-pins-package/tasks.md` | `551a8bc3c5ca…` |
| `…/design.md` | `9f57e08058c4…` |
| `…/specs/gate-ref-pinning/spec.md` | `de8cc896c93e…` |
| `…/proposal.md` | `903714c3fc90…` |
| `src/witnessloop/constants.py` | `0a64184d5435…` |
| `src/witnessloop/initcmd.py` | `d706fbe5f838…` |
| `src/witnessloop/checkcmd.py` | `90be88ec3544…` |
| `src/witnessloop/contract.py` | `b9e1033dbef0…` |
| `.github/workflows/gate.yml` | `a9b86014d067…` |
| `docs/gate.md` | `62924fe2dd25…` |
| `README.md` / `docs/design.md` | `700ade12d4ab…` / `dcbc79bd8fcd…` |
| `tests/test_docs.py` | `c3516c31b828…` |
| `tests/test_gate_workflow.py` | `3d5970381412…` |
| `tests/test_init_gate_ref.py` | `88f6c38994a9…` |

凡是我在 `1b59eb6` 上复跑过的结论，都单独标注了「（`1b59eb6` 上复跑）」。

**事故与还原（如实披露）**

我在 `/tmp/adv4/repoX` 做 manifest 实验时用了 `cp -a <本 worktree> repoX`——而本仓是 **linked
worktree**，`cp -a` 把 `.git`（一个 `gitdir:` **指针文件**，指向
`/home/happy/witnessloop/.git/worktrees/archive-arrival-recognition`）一起复制了 ⇒ 我在
`repoX` 里跑的 `git add -A && git commit` **打进了真仓**，产生 `da3db40`「证据：四份 manifest
（额外 stage 名）」（`reviewer_run_id=rv-grill` 这类**我编的假值**，已核）。
**已还原**：`git reset --mixed af57236`，HEAD 回到 `af57236`，四份 manifest 不在盘上、不在索引里，
`git status --porcelain` 当时只剩主 session **自己**的未提交改动（`design.md` / `initcmd.py` /
`test_init_gate_ref.py`）。该提交**从未 push**。除本报告外，我对本仓的净改动为零。下方所有实验
此后一律改在 `git archive` 导出的**无 `.git`** 目录里做。

**实际跑了（命令 + 原始输出要点）**

1. **基线**：`git archive af57236 | tar -x` ⇒ `PYTHONPATH=src python3 -m pytest -q` ⇒ **673 passed**。
2. **M1 逐字模拟**（在 `af57236` 导出树上）：按 `tasks.md:86-98` 改
   ① `constants.py:21` → `@v1.7.0`、② `gate.yml:61` `WL_FALLBACK_REF` → `"v1.7.0"`、
   ③ `tests/test_gate_workflow.py:59` → `@v1.7.0` ⇒ `pytest -q` ⇒ **673 passed**（全绿）。
3. **反向对照**：再把 `tests/test_init_gate_ref.py` 的 `NEW_REF` **还原成撞值**的 `@v1.7.0`
   ⇒ **6 failed, 667 passed**（5 条是 6.1 撞塌的原用例 + 1 条新前提钉子
   `test_new_ref_does_not_collide_with_the_factory_default`）⇒ `tasks.md:88-89` 的「5 failed」是**加钉子前**
   的口径（`R3` 手记里那个数），加钉子后同一塌陷会红 6 条——两个数**互不矛盾**，且证明前提钉子**有效**。
4. **M2 落地复算**（模拟仓，与本 change 同构）：对 4 份报告分别以
   `--stage grill` / `grill-adversarial` / `grill-adversarial-r2` / `grill-adversarial-r3` 各产一份
   manifest 并提交 ⇒ `check` **0 条孤儿**，只剩一条 `无 stage=building 的 manifest（现有 stage：
   grill, grill-adversarial, grill-adversarial-r2, grill-adversarial-r3）` ⇒ Q2 裁定 (a) **可行**。
5. **`tests/test_docs.py` 的两条新钉子逐个踩**（各删一个字面量后单跑对应测试）：
   `刻意不修` / `protected=False` / `invariant=False` / `先把 CLI 升上去` / `job.workflow_sha` /
   `init --gate-ref` ⇒ **6/6 全部 `1 failed`** ⇒ 钉子**真会红**，不是摆设。
6. **`init --gate-ref` × flag 组合矩阵**（12 组，已接入仓）：见 §D2；其中
   `--gate-ref + --test-command` 的收尾话**自相矛盾**（`af57236`），`1b59eb6` 已修。
7. **spec Scenario 覆盖插桩**：把 `initcmd._set_ledger_gate_ref` 的「补条目」分支改成写
   `/tmp/adv4/HIT_...`，跑**全量 673 条** ⇒ **探测文件从未出现**（`NOT HIT`）⇒ 该分支**零覆盖**；
   行为本身我用等价实验手工复算过（条目插在 `self` 之前、`gate_ref` 同步、随后 plain `init` 幂等）。
8. **`1b59eb6` 上复跑**：新钉子 `test_ledger_without_a_caller_entry_is_repaired` 通过；把它依赖的
   `entries.insert(at, …)` 变异成 `entries.append(…)` ⇒ **该条红、其余 15 条绿** ⇒ 新钉子有效。
   收尾话复跑：`init：已接入 witnessloop（已写入测试执行点，未 commit；…caller 与台账已改成 …）`。
9. **`check` 自报行会不会被当 finding**：findings 走 **stderr** 且带 `  N. <path>：<msg>`
   编号（`checkcmd.py:425-427`）；自报行走 **stdout** 且以 `check：本包来源（自报，尽力而为）：` 开头
   （`checkcmd.py:84-88`，`flush=True`，是 `run()` 的第一句 `:96`）⇒ **形态上不可混淆**。
10. **自报行只有 `check` 打**：`grep -rn "_report_package_source\|installed_vcs_ref" src/`
    ⇒ 定义 `checkcmd.py:76`、唯一调用 `checkcmd.py:96`；实跑 `guard`（stdout 空）⇒ `docs/gate.md §8`
    那句「只有 `check` 打」**属实**。
11. **本仓自证**：`PYTHONPATH=src python3 -m witnessloop check --root . --base origin/main --head HEAD`
    ⇒ **✗（4 项）**，全部是「缺 manifest / 缺 stage」类，与 caller / policy / 台账无关。
12. **远端 tag 清单**（只读 `git ls-remote --tags origin`）：最大 = **`v1.6.0`**，
    `v1^{}` = `v1.6.0^{}` = `ae99256…` ⇒ `README.md:125` 的「`@v1` 现在停在 `v1.6.0`（`ae99256`）」
    逐字属实；**不存在 `v1.7.0`**。
13. **计数复算**：`git rev-list --count v1..origin/main` = **47**（与 `design.md:253` 的 K5 行一致）；
    `git branch -a` 仍见 **`probe/workflow-ref`** ⇒ `design.md §2 D1` 的「本地仍留」属实。

**没能复算的**：见「未验证项」（真 CI 的 `job.*` 取值与 Q1 探针原始输出、GHES/fork/自建 runner、
真 `uvx …@v1.7.0`、issue #30 的两组 CI 数字）。

---

## 对抗结论

### A 基准纪律：三代「必须修改项」的落库复核

> 判据：去**正文 / 实现**里核，不核 `design.md §7.9` 的自述表。

**A1 M1（字面量族）——落库且有效 ✅**

- `tasks.md §6.1` 现在把清单写成「1 `constants.py` / 2 `gate.yml` 的 `WL_FALLBACK_REF` /
  3 `tests/test_gate_workflow.py::test_caller_ref_matches_this_repo` 的断言 / 4 **没有第 4 处要改**，
  但 `tests/test_init_gate_ref.py` 的 `NEW_REF` 必须是**不可能等于出厂默认**的前提」，
  并声明「模拟执行下列改动 ⇒ `673 passed`；改之前是 `5 failed`」（`tasks.md:86-98`）。
- 我**按字面复算了整段**：见 Reviewer 第 2、3 条 ⇒ **673 passed** 与 **6 failed** 两个数都成立
  （6 = 5 + 新前提钉子，见上）。`NEW_REF = …@v9.9.9`（`tests/test_init_gate_ref.py:28`）与
  `test_new_ref_does_not_collide_with_the_factory_default`（`:46-48`）都在 ⇒ **前提本身被钉住**，
  这正是 R3 的 M1 要的那一半。

**A2 M2（多轮报告的 manifest）——落库 ✅**

- `docs/gate.md:218-226` 写明「落盘名是 `reviews/<stage>.manifest.json` ⇒ 同一个 stage 只能有一份
  manifest（后一次 `manifest build` 会**覆盖**前一份，而孤儿判定随之换成另一组）」+ 两条可选落法
  （额外 stage 名 / 放到 `reviews/` 之外，先例 `archive-arrival-recognition/rounds/`）+ 「同一次 change
  里别混」。
- `tasks.md:16-19`（0.4）与 `tasks.md:71-77`（5.2）各补了一步。本 change 自己只用**额外 stage 名**
  一条路（`reviews/` 下无 `rounds/`、无第二份同 stage manifest）⇒ **未混用**，且我实测 **0 条孤儿**。

**A3 M3（revision 绑定）——落库且与机制一致 ✅**

- `tasks.md:104-108` 现在写「`head_sha` 之后**只允许**出现证据文件（`reviews/*.md`、
  `reviews/*.manifest.json`）——「本 PR 自己的变更」（非证据）落在它之后**正是**判 stale 的那条规则
  所禁止的」。
- 源码核对：`contract.py:686-687`「head_sha 必须是本次被检 head 的**祖先**，且从 head_sha 到被检 head
  之间**只允许出现证据文件**。这等价于「head_sha 是最后一个非证据 revision」」；
  报错文案在 `contract.py:753-760`（`审阅的是旧 revision：head_sha=… 之后又改动了非证据文件：…`），
  过滤条件 `:747-752`（`scope.pr_paths` ∩ ¬`evidence_patterns`）⇒ **描述与实现一致**。
  `docs/gate.md:192-201` 同步写成同一口径（含「⚠️ **「本 PR 自己的变更」并不豁免**」）。

**A4 M4（升级自证）——落库 ✅**

- `docs/gate.md:90-100`（§1.2 的 ①′）+ `README.md:190-204`：两条 recipe 都在 ① 之后补
  `witnessloop check --root . 2>/dev/null | head -1` ⇒ `requested_revision=<你刚升的 ref>`，
  并写明旧包**没有**这一行。可复算面成立：自报行在 `run()` 第一句、先于任何 git 操作
  （`checkcmd.py:96`），且 `grep` 证明只有 `check` 打（Reviewer 10）。

**小结：判据②成立——K1–K8 / L1–L6 / M1–M4 我抽全核，全部落进正文或实现。**

### B R3 的 Q1 裁定（兜底 ref 与默认值**同源**）——**措辞未清干净（3 处漏网）**

裁定原文（`design.md:320-322`）自称：

> 「全局把「退 `v1`」的措辞改成「退**兜底 ref**（= `DEFAULT_GATE_REF` 的 ref 部分；今天 = `v1`）」——
> `spec.md`、`design.md`、`docs/gate.md §7.1`、`gate.yml` 注释、`tasks.md` **已逐处改完**。」

**这句断言是可证伪的，而且是假的**（`1b59eb6` 上复跑仍为假）：

| # | 位置（`af57236`） | 原文 | 为什么是漏网 |
|---|---|---|---|
| 1 | `docs/gate.md:519` | 「⚠️ 诚实地说：**GHES 接入方会一直吃 `v1`**，区别只在日志里有一行 `::warning::`」 | 同一段**上一句**已改成「退回**兜底 ref**（= `DEFAULT_GATE_REF` 的 ref 部分，与出厂默认**同源**；今天 = `v1`）」——下一句立刻把同一个东西写成**永久 `v1`**，自相矛盾 |
| 2 | `design.md:218`（§4 R6 表） | 「GHES / fork 场景落到 fail-closed ⇒ **吃 `v1`**，但**日志里有 `::warning::`**」 | §4 R6 是**行为描述**（不是历史引文、不是错误信息复现），正是 `tasks.md:99-101` 要求改成「`DEFAULT_GATE_REF` 的 ref 部分」的那一类 |
| 3 | `tests/test_gate_workflow.py:410`（docstring） | 「design §4 R6 如实登记：GHES 接入方会一直吃 `v1`」 | 本仓自订的口径是「**测试里的口径也是口径，同样会漂**」（`tests/test_docs.py:95-96` 的 `Q3_DOCS` 把测试文件也纳入守卫）——它没被同一标准扫到 |

- 佐证「这是漏网而非有意保留」：同一批清理**改掉了**这三处**相邻**的兄弟句子——
  `tests/test_gate_workflow.py:347/405/434/481` 的四条 docstring 都从「退 `v1`」改成了「退**兜底 ref**」
  （`git show af57236 -- tests/test_gate_workflow.py`），唯独 `:410` 留在原地；
  `docs/gate.md:518` 改了、`:519` 没改；`design.md §7.9` 自己改了、`§4 R6` 没改。
- **警告**：`6.1` 之后 `WL_FALLBACK_REF` 会随 `DEFAULT_GATE_REF` 变成 `v1.7.0`，届时这三句**全是假陈述**
  （GHES 接入方不会「一直吃 v1」），而 `tasks.md:99-101` 的自查只点名了 `docs/` 与 `README.md`
  ——`design.md` 与 `tests/**` 不在它的字面射程里，所以照 6.1 执行**照不出来**。
- **不是漏网、别误判的两处**（我核过）：`design.md:316`「钉死 `v1` 会让 … 永远吃 `v1` 时代的包」是
  Q1 的**反事实论证**（在论证**不该**钉死 `v1`），必须原样保留；`gate.yml:4` 的
  `#   uses: …gate.yml@v1` 是**产物示例引文**，属 `tasks.md:100` 明写「保留」的一类（但 6.1 落地时
  它同样会变成旧值，建议顺手一起看）。

### C R3 的 Q2 裁定（报告留在 `reviews/` + 多轮用不同 stage 名）——**可用 ✅**

- `docs/gate.md §3`（`:206-226`）写清了「**每一份报告各配一份 manifest**（数量对齐，不是「每个 stage 一份」）」。
- 我用模拟仓**实复算**（Reviewer 4）：本 change 的 4 份报告 × 4 个不同 stage 名 ⇒ **0 条孤儿**，
  三个必备 stage 判定照旧满足（只剩 `building` 未产，那是 5.1 的活）。⇒ 裁定 (a) 的可行性**成立**。

### D 本轮新面核查

**D1 `tests/test_docs.py` 的两条新钉子——真会红 ✅**

`test_gate_documents_the_unprotected_caller_boundary`（`:268`）与
`test_gate_documents_the_ref_pinning_upgrade_path`（`:277`）共 6 个字面量，逐个删除后**各自 1 failed**
（Reviewer 5）⇒ 不是「写了但钉不住」。另：`test_every_idempotency_claim_is_scoped_or_qualified`
的 `IDEMPOTENCY_DOCS` **不含 README**，所以 `README.md:36` 那句「幂等、不 auto-commit」（窗口无
「固定 base 与 revision」）**不在**守卫射程里——这不是缺陷，是既有射程边界，记此以免误判为漏网。

**D2 `init --gate-ref` 的组合矩阵——一条自相矛盾的话（`af57236`）**

12 组组合（已接入仓）里，**唯一**文案有问题的这组：

```
$ init --root <repo> --gate-ref …@v9.9.9 --test-command "uv run pytest -q"
init：已写入测试执行点 .github/witnessloop-tests.txt（--test-command 覆盖已有内容）
init：已重写 .github/workflows/witnessloop.yml（→ …@v9.9.9）并同步台账
init：已接入 witnessloop（其余文件无改动，未 commit；.github/workflows/witnessloop.yml 与台账已改成 …@v9.9.9）。
```

最后一句**自己否自己**：前半说「其余文件无改动」，后半说 caller 与台账已改。
根因是 `initcmd.py:271` 的 `note` 是在**只考虑命令文件**的语境里造的常量串，
随后被 `:293` 与 caller 那半拼在一起。**spec 未覆盖这条轴**（「组合语义」Scenario 只写 `--policy`）。
⇒ `1b59eb6` 已改（`note = "[dry-run] 未落盘"` / `"已写入测试执行点，未 commit"`，我复跑确认）。
其余 11 组语义自洽（`--dry-run` 下 `changed=[]` 恒成立、`--no-tests` 的 EXIT=1 是 §11.2① 的既有摩擦、
「先写后判、不回滚」的文案与 `tests/test_init_gate_ref.py:217-243` 一致）。

**D3 spec 的「台账里没有 caller 条目」Scenario——`af57236` 上零机械覆盖**

`spec.md:113-118` 是一条**有具体断言的** Scenario（同步 `gate_ref` + **补上**该条目 + 条目在 `self`
之前 + 盘上没 caller 时不得凭空新建）。插桩实测（Reviewer 7）：`_set_ledger_gate_ref` 的
`else:`（补条目）分支在**全量 673 条测试**下**一次都没进过** ⇒ 该分支是可执行但**无钉子**的。
行为本身我手工复算**正确**（条目插在 `self` 之前、`gate_ref` 同步、随后 plain `init` 幂等、
`uninit` 可用）⇒ 这是**覆盖缺口**，不是功能缺陷。⇒ `1b59eb6` 已补
`test_ledger_without_a_caller_entry_is_repaired`，且我变异验证它**真会红**（Reviewer 8）。

**D4 `check` 的自报行不会被误当成 finding ✅**

见 Reviewer 9：finding 走 stderr、`  N. <path>：<msg>`；自报行走 stdout、`check：…` 开头、且是
`run()` 的第一句。实跑本仓（Reviewer 11）两者同屏也不混淆。`--dry-run`/`--test-command`/`--no-tests`
的任何分支都吞不掉它（`:96` 在任何 `return` 之前）。

**D5 本仓自证 ✅**：`check --root . --base origin/main --head HEAD` = **✗4**，全部「缺 manifest」类
（缺 manifest / grill / grill-adversarial / building），与 caller / policy / 台账 / 解析面无关。

**D6 文档内部引用与编号 ✅**（`docs/gate.md` 本轮被改的 §1.2 / §3 / §7.1 / §8）

- 全文二级标题为 §1…§11 连续无缺号、无重号；指向本文的 §ref 无越界（不存在 `§12+`）。
- `§8:531`「§1.2 那条「本包来源（自报，尽力而为）」」⇒ 确实在 §1.2（`:77-80`）；
  `§1.2:74`「能力边界（GHES / fork 面）见 §7」⇒ §7 即「能力边界」；`:91`「见 §7.1」⇒ 存在。
- `§3` 与 `§3.1` / `§3.2` 的交叉引用自洽（`:288` / `:309` / `:558`）。

### E 低危观察（**不是**必须修改项）

1. **`init --gate-ref ""` 静默回落出厂默认**（**先于本 change 即存在**：`v1.6.0` 的
   `src/witnessloop/initcmd.py:192` 就是同一条 `args.gate_ref or ledger_gate_ref(...) or C.DEFAULT_GATE_REF`）。
   实测：新仓 `init --gate-ref ""` ⇒ **EXIT=0**，caller 写成 `uses: …gate.yml@v1`，**无任何提示**
   ——显式传的 flag 被静默丢掉（与本 change 引用为先例的「显式意图优先，不得静默 no-op」相反）。
   `--gate-ref " "` ⇒ 写出 `uses:  `（空 ref，EXIT=0）。**本 change 未引入、也未扩大它**
   （`sync_caller_gate_ref` 的入口同样是 `if args.gate_ref`），故不计入必须修改项。
2. **`check` 的退出码 3（未接入）也打自报行**——与 spec 的「任何分支都不该吞掉它」一致，不算缺口。
3. **`design.md:256`（K8 行）曾引用 §2 D1 里已不存在的措辞**（「探针文件已全部清理」），
   而 §2 D1 实际写的是「远端已清理、**本地仍留**」——引用与正文不符。`1b59eb6` 已对齐。
4. **远端 tag 面上的一个窗口**：`README.md:20` 的安装行仍是 `@v1`（6.3 的 post-merge 事项，
   与 Q3 一致，不算缺口）；`README.md:189` 的「新接入」示例却已经写 `@v1.7.0`，靠
   `:206` 的「v1.7.0 发布之前，请仍然钉 `@v1`」兜住——两处**时点不同、口径需要读者跨 17 行拼接**，
   属可读性面，不是错误。

---

## 未验证项

> 每一项都写「若假设相反会怎样」。**这些都不是必须修改项**——除非有文档把它们写成了已验证
> （我逐条查过，**没有**：`design.md:87-94` 已把探针输出标成「单一来源、不可复现的二手文本」，
> `docs/gate.md:515-516` 已把自建 runner / `pip install git+…` 列为未验证面）。

1. **`job.workflow_sha` / `job.workflow_repository` / `job.workflow_ref` 在 called workflow 里的运行期取值**，
   以及 **Q1 探针（run `38853369550`）的原始输出**：本工作区没有可跑的 GitHub Actions；那两次 run 的
   分支/文件已删；唯一载体是 `design.md:69-77` 的粘贴块。
   - **若假设相反**：若 `job.workflow_sha` 实为 caller 的 commit，则每个接入方会**全量硬红**
     （不是静默吃旧包）；若 `job.workflow_ref` 的实际形态与兜底解析不符（如返回裸 `v1`），
     兜底会 fail-closed 吃兜底 ref（**响亮、有 warning**）。实现只用 `job.*`、不用 `github.*`，
     行为不受影响，受影响的是 `design.md §2 D1` / `gate.yml:41-44` / `tests/test_gate_workflow.py:329-333`
     的**叙述**。文档已如实标等级 ⇒ **不算缺口**。
2. **GHES / 同 owner fork / 自建 runner 的 uv 版本差异 / `pip install git+…` 是否同样落 PEP 610
   `vcs_info`**：未验证。`docs/gate.md:515-516` 已如实登记（含「GHES 接入方会一直吃 <兜底 ref>」）。
3. **issue #30 的两组 CI 数字（✗10 / ✗1）**：无法复算（另一个仓 + 真 CI）。我只核到
   它与 `proposal.md:35-36` 的自述**一致**。
4. **真 `uvx --from git+https://github.com/Xingkai98/witnessloop@v1.7.0 …`**：`v1.7.0` **不存在**
   （Reviewer 12 已证），所以我没跑过真命令。我用本地 git 仓 + 真 uv 复算过机制面（R3 做过，
   本次未重做）。⇒ `tasks.md §6.7` 的验收命令仍是**前瞻性**的。
5. **`--gate-ref " "` 写出的 `uses:  ` 在真 CI 上会被 `uvx --from git+…@` 怎么处理**：未实测
   （只确认 `init` 侧 EXIT=0、落盘内容如此）。若假设「会硬红」成立，则它是一条**响亮**的失败
   （非静默），与 `E1` 的低危定性一致。

---

## 必须修改项

> 编号 **N1、N2…**；**非纯措辞的排前面**。每条带证据。**基准 = `af57236`**；
> 凡在 `1b59eb6` 已修的，标注「（`1b59eb6` 已修）」。

- **N1（覆盖缺口 · 非措辞）spec 的 Scenario「台账里没有 caller 条目」在 `af57236` 上**零机械覆盖**，
  而它承载的是一段**可执行但没钉子的新分支**。**
  证据：`spec.md:113-118` 给出四条具体断言；插桩 `initcmd._set_ledger_gate_ref` 的补条目分支后跑
  **全量 673 条** ⇒ 探测文件**从未生成**（原输出：`NOT HIT (分支零覆盖)`）。行为我手工复算**正确**，
  所以这是「缺钉子」而非「坏行为」——与本 change 自己援引的先例同类（R2 的 L3：
  「没有任何测试钉 `inputs.witnessloop-ref.default == ""` ⇒ 改回 `"v1"` 时机制静默退化且 665 条全绿」）。
  改法：补一条行为级用例（删掉台账里的 caller 条目 ⇒ 显式 `--gate-ref` ⇒ 条目被补、位置在 `self` 之前、
  随后 plain `init` 幂等、`uninit` 可用）。**（`1b59eb6` 已修：`test_ledger_without_a_caller_entry_is_repaired`；
  我把它依赖的 `insert` 变异成 `append` ⇒ 该条红、其余 15 绿 ⇒ 钉子有效。）**
- **N2（文案自相矛盾 · 非措辞）`init --gate-ref <新> --test-command <cmd>` 的收尾话自己否自己。**
  证据（`af57236` 实跑原文）：
  `init：已接入 witnessloop（其余文件无改动，未 commit；.github/workflows/witnessloop.yml 与台账已改成 …@v9.9.9）。`
  ——前半「其余文件无改动」与后半「caller 与台账已改」直接冲突；制造点在 `initcmd.py:271` 的常量串
  `note = "其余文件无改动，未 commit"` 被 `:293` 与 caller 那半拼接。**spec 未覆盖这条轴**
  （组合语义 Scenario 只写 `--policy`）⇒ 属未覆盖的坏组合态。**（`1b59eb6` 已修，我复跑确认输出不再自否。）**
- **N3（措辞面，但会随 `6.1` 变成**假陈述**）「退 `v1`」的清理有 3 处漏网，而 `design.md` 自称「已逐处改完」。**
  证据：`design.md:320-322` 的「`spec.md`、`design.md`、`docs/gate.md §7.1`、`gate.yml` 注释、
  `tasks.md` **已逐处改完**」；反例（`1b59eb6` 上复跑仍存在）：
  `docs/gate.md:519`「GHES 接入方会一直吃 `v1`」、`design.md:218`「落到 fail-closed ⇒ 吃 `v1`」、
  `tests/test_gate_workflow.py:410`「GHES 接入方会一直吃 `v1`」。三者都是**机制描述**
  （不是历史引文、不是错误信息复现），正落在 `tasks.md:99-101` 要求改写成
  「`DEFAULT_GATE_REF` 的 ref 部分」的那一类；同批清理已把**相邻**的兄弟句改掉
  （`tests/test_gate_workflow.py:347/405/434/481`、`docs/gate.md:518`、`design.md §7.9`），
  只剩这三处 ⇒ **漏网**而非有意保留。后果：6.1 之后它们全变成假陈述，而 6.1 的自查只点名
  `docs/` 与 `README.md`，**照 6.1 执行查不出 `design.md` 与 `tests/**` 的这两处**。
  改法：统一改成「退**兜底 ref**（= `DEFAULT_GATE_REF` 的 ref 部分；今天 = `v1`）」，并把
  `tasks.md §6.1` 的自查面从「`docs/` 与 `README.md`」扩到「**全仓活文档 + 测试 docstring**」。

---

## Open Questions

**（本轮无新增。**R3 的两条已由作者裁定并落库（`design.md:309-328`）：Q1 = 同源（N3 是它**清理不彻底**
的执行残留，不是新取舍）、Q2 = 报告留 `reviews/` + 额外 stage 名（我实测可用）。
`E1`（`--gate-ref ""` 静默回落）我先于本 change 即存在、且本 change 未扩大它，属**另开一个 change**
的面，不值得在这里让用户拍板。**）**

---

## 收敛结论

**不收敛。**

**判据②（前三轮必须修改项全部已落库）——满足 ✅**

- R1 的 **K1–K8**：我核了 K1（`spec.md:60-72` + `design.md §2 D3`）、K2（`proposal.md:19-29`）、
  K3（`design.md:124-129` 的三条恢复路径）、K4（`design.md:156-171` §2 D4）、K5（计数复算 = **47**，
  `design.md:253` 口径成立）、K6（`docs/design.md:56` 保留历史引文 / `:73` 已改 `@<ref>`）、
  K7（`design.md:130-134`）、K8（`design.md:84-86`「远端已清理、本地仍留」；`git branch -a` 复算一致）
  ⇒ **全部在正文/实现里**。
- L1–L6：L1（`tasks.md:81-85` 时序 + `:114` 再 tag）、L2（`docs/gate.md:82-110` 两步 +
  旧 CLI 的 EXIT=1 与误导文案）、L3（`tests/test_gate_workflow.py:464` 钉子，R3 已实踩，我复核存在
  且语义正确）、L4（`spec.md:120-126` Scenario + `initcmd.py:298-302` 的分叉文案 +
  `tests/test_init_gate_ref.py:217-275`）、L5（`spec.md:106-118` 两条 Scenario）、L6
  （`design.md:212` + `docs/gate.md:119-122` + `tasks.md:118-122`）⇒ **全部落库**。
- M1–M4：见 §A1–§A4，**逐条复算**（M1 我按字面跑过，673 passed；M3 与 `contract.py:686-687` 逐字对齐）。

**判据①（本轮没有新的可证伪项）——不满足 ❌**

- **非措辞两条**：**N1**（spec 明写的 Scenario 所依赖的分支零覆盖，插桩可证）、
  **N2**（用户可见输出自相矛盾，`af57236` 实跑可证）。
- 措辞面一条：**N3**（`design.md` 自称「已逐处改完」，三处仍是固定 `v1` 的机制描述；
  按本轮纪律「措辞类不算证伪」，它**单独不足以**判 ① 不满足——但它**是**一条未落库的残留，
  且 6.1 一落地就变成假陈述）。
- **必须说明的时序**：N1 与 N2 在我收尾时**已被主 session 落库到 `1b59eb6`**
  （commit message 逐条点名；我在该树上复跑验证了钉子会红、文案不再自否）。
  ⇒ 若把 `1b59eb6` 视作「对 R4 的回应」，则本轮**剩余可执行项只有 N3**；N3 属措辞，
  下一条判据在措辞清干净后应当**收敛**。我仍按「本轮发现了新的可证伪项」判 **不收敛**，
  与 R3 在同类并发情形下的判定口径保持一致——**这一句请在下一轮复核。**

**本轮证伪失败（= 既有结论成立）的部分**，一并记明，避免读者以为全盘被推翻：
`(B′)` 的上下文落点（`job.*` + step，`gate.yml:53-101` 与 `tests/test_gate_workflow.py` 的 8 类行为级
用例一致）；解析 step 是 job 的第一个 step 且 `run:` 内无 `${{ }}` 插值；fail-closed 与兜底剥离
**行为级**符合 spec；`--gate-ref` 的「重写-同步-幂等-可卸载」是**不动点**（含台账缺条目的补条目路径，
我手工复算通过）；组合语义「先写后判、不回滚」及其文案；`--dry-run` 下「什么都不落盘、也不谎报」
（12 组组合里 `changed=[]` 恒成立）；`check` 自报从不因取不到元数据而失败（宽 `except` 是按规格兜）；
caller 不受保护这条边界已登记且刻意不修（`docs/gate.md §7.1`）；远端最大 tag = `v1.6.0`
（`v1^{}` = `ae99256`，逐字吻合 README）；`check --root . --base origin/main --head HEAD` 只剩
「缺 manifest」类 4 项。

---

## 处置（主 session 在 R4 之后追加，非审阅者原文）

> 本报告判定**不收敛**（②满足、①不满足），基准 `af57236`。**N1–N3 全部已落库**：
> N1/N2 在你审阅期间就已由 `1b59eb6` 修掉（你也复核了），**N3 由本次提交落库**。

- **N1**（`_set_ledger_gate_ref` 的补条目分支零覆盖）：已加
  `tests/test_init_gate_ref.py::test_ledger_without_a_caller_entry_is_repaired`
  —— 断言补出来的条目 `sha256` 正确、**排在 `self` 之前**、且随后 plain `init` 幂等、`uninit` 能真回滚它。
- **N2**（`--gate-ref` + `--test-command` 的收尾话自相矛盾）：`initcmd` 的收尾 note 不再自称
  「其余文件无改动」（两条轴都可能动过），改成只陈述自己那一件事。
- **N3**（R3-Q1 自称「措辞已逐处改完」是假的，仍漏 3 处）：`docs/gate.md §7.1`、`design.md §4 R6`、
  `tests/test_gate_workflow.py` 的 docstring 三处已改；并把 `tasks.md §6.1` 的自查面从
  「`docs/` 与 `README.md`」扩到 **`src/` + `tests/`（含 docstring）+ `docs/` + `README.md` + `.github/`**，
  附一条可直接跑的 `grep` 命令。全仓活面复查（同样的 grep）现在**零命中**。

### 关于你报告里那次事故（`da3db40`）——已核，无残留

你在 `/tmp/adv4/repoX` 的 `git commit` 打进了真仓（`da3db40`，四份 manifest、`reviewer_run_id` 是编造值），
随后 `git reset --mixed af57236` 还原。**我独立核过**：`git log` 上 `da3db40` 不可达、
`find . -name "*.manifest.json"` 在本 change 目录下**零命中**、`git status` 只有你这份报告未跟踪、
后续 `1b59eb6` 的 stat 只有三个文件（不含 manifest）。⇒ **净残留为零，且从未 push**。
唯一痕迹是本地 `git reflog` 里那条悬空记录（不进 PR、不影响任何判定）。
⚠️ 记在这里是提醒后来者：**worktree 的 `.git` 是指针文件，`cp -a` 会把它带过去**——
在副本里 commit 等于在真仓 commit。这条**不是**本 change 的缺陷，不产生必须修改项。

### 低危观察的处置

- `init --gate-ref ""` 静默回落出厂默认、`" "` 写出 `uses:  ` 两个——你已核**先于本 change 存在**
  （v1.6.0 同款），本 change 未扩大 ⇒ **登记不修**（属 `initcmd` 的参数解析面，另开 change）。
- 真 CI 的 `job.*` 取值、Q1 探针的二手输出、GHES/fork/自建 runner、真 `uvx …@v1.7.0`、
  issue #30 的两组数字：**均为「本工作区不可验证」**，文档已如实标注 ⇒ 按判据纪律**不计入必须修改项**。
