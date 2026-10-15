# 对抗轮 R6（独立零记忆验证者）—— `archive-arrival-recognition`

> **结论摘要：不收敛。** R5 的两处修复**都成立**（符号链接绕过确已关闭、D4 的行为变化确已登记且其
> fail-closed 对照成立），判据 1–5 在本轮全部既有构造上**没有新的可证伪项**。
> 但本轮独立复算发现 **1 条新的、可复算的、影响判红判绿的证伪项**：
> **Fix 1 的「Ev(A) 每一项须是普通文件」这条 fail-closed 规则本身引入一条未登记的行为变化**——
> **合法整目录归档 move（全 `R100`）只要证据里含一个符号链接，今天判绿、新稿判红**；
> 而「符号链接报告」正是**本仓自己有一条钉绿的既有测试支持的布局**（`tests/test_orphan_reports.py:273`）。
> 该后果未出现在 `spec.md` 的「有意的行为变化」清单、也未出现在 `design.md` 的「误伤面 / 已知边界」里，
> 且使 `spec.md:306-309` 那条无保留语 Scenario（同一内容两种位置结论一致）对该内容不再成立。
> 另有 **11 条措辞项**（含 R5 已提出但**未落库**的 6 条）。

---

## Reviewer

**零记忆声明**：本对话不携带该 change 的任何历史。前五轮（`grill-design.md` / `grill-adversarial.md`=R1 /
`-r2` / `-r3` / `-r4` / `-r5`）的结论**只当待复核的声明**；design / spec / tasks 里的「实测」「`文件:行号`」
一律当**待验证断言**。判据模拟器 `/tmp/r6sim.py` 由我**从零写成**（只读 `design.md §2 D1`/`§2 D4` 与
`spec.md` 当前正文 + `src/` 源码做事实核对；**未**沿用 `/tmp/r5sim.py` 或任何前轮脚本的判据逻辑，
也没读它们的实现）。本轮只写 `reviews/` 下这一个文件；未改 `src/` / `tests/` / 任何 change 文档；
未 commit、未 push。

**读过的**（当前 HEAD `64ecbd3`）：
`design.md`（696 行）/ `tasks.md`（192 行）/ `specs/archive-awareness/spec.md`（346 行）/ `proposal.md`；
源码 `contract.py` / `checkcmd.py` / `gitutil.py` / `policy.py` / `constants.py` / `paths.py` / `hashing.py` /
`manifestcmd.py` / `evidence.py`（部分）；`tests/test_archive_awareness.py`（通读 + 逐行号核对）、
`tests/test_orphan_reports.py`。

**跑过的**：
- `/tmp/r6sim.py` 在**全部既有构造**上复算：`/tmp/cases/*`(18) + `/tmp/r3cases/*`(8) + `/tmp/r3cases2/*`(18)
  + `/tmp/r4cases/*`(11) + `/tmp/r5cases/*`(10)（基线 `main` / head `feature`，`t577` 用 `touching`，
  `pmd_invalid` 用 `feature2`）；
- **自建 5 个新构造**（`/tmp/r6cases/*`）：`A_delall_unrelated`、`B_rename_unrecognized`、
  `C_pmd_rest_moved`、`D_delall_recognizing_born`、`symlink_move_legit`、`symlink_report_move`；
- **真 CLI**（今天的实现，`.venv/bin/python -m witnessloop check` / `manifest build`）跑在自建构造上，
  取「今天红 / 绿」的**原始输出**（见 M1 与「R5 修复复核」）；
- `pytest -q tests/test_orphan_reports.py::test_symlinked_report_is_not_an_orphan` ⇒ `1 passed`。

---

## R5 两处修复复核

### 修复 1（`Ev(A)` 每一项 SHALL 是普通文件；`120000`/`160000` ⇒ fail-closed）

**攻击面确已关闭（复核成立）**。用我的独立模拟器在 R5 的构造上复算：

```bash
$ python3 /tmp/r6sim.py /tmp/r5cases/symlink_ev main feature -v
  cand 2026-10-15-new   c1=True c2=True c3=True c4=True c5=False srcs=[] arrived=False
        ✗ …/2026-10-15-new/tasks.md          (mode=120000 非普通文件)
        ✗ …/2026-10-15-new/specs             (mode=120000 非普通文件)
        ✗ …/2026-10-15-new/reviews/link.md   (mode=120000 非普通文件)
  ARRIVED = []   ⇒ RED(没有任何 change 目录)
```

⇒ R5 的 A1（`ln -s` 借 `tasks.md`/`specs` 全过、`cp` 全拒）**不再成立**：本构造下符号链接版
与 `cp` 版现在同为红。且这条**在任何一种对 `Ev(A)` 的解释下都命中**（`tasks.md` 在 part 1、
`specs` 在 part 1、`reviews/link.md` 在 part 3 且也是某 manifest 的 `report_path` 目标）⇒ 对口径分歧免疫。

**覆盖率复核（我自造的相关变体）**：

| 变体 | 结果 |
|---|---|
| `specs` 本身做成符号链接（**指向目录**，`120000` blob） | 命中（`ls-tree -r <A>/specs` 返回该 blob，实测）✅ |
| `reviews/link.md` 符号链接（part 3） | 命中 ✅ |
| 非空普通文件 / `reviews/.gitkeep`（0 字节） | **不**命中（空内容豁免 + mode 100644）✅（`r4cases/empty13_gitkeep` ⇒ `arrived=True`） |
| `tasks.md` 做成**目录**（借用内容塞进去） | 命中（part 1 取「是目录 ⇒ 其下全部文件」）✅（`r3cases2/a5_tasks_as_dir` ⇒ `c5=False`） |
| **硬链接**借内容 | 无法构造成绕过（git 里就是普通 blob、内容相同 ⇒ (a) 命中）——与 R5 同结论 |
| gitlink（`160000`） | 规则文本覆盖；**未构造真实用例**（见「未验证项 3」） |

**但这条修复引入了一条新的误伤 / 未登记的行为变化** ⇒ 见「必须修改项 M1」（本轮的阻塞项）。

### 修复 2（D4 措辞订正 + 行为变化登记 + 2c 用例）

**（a）订正确实落了库**：`design.md:249-251` 现在写「初稿把这条读成『该目录不存在 ⇒ 那个 change **整体**搬走了』
——**该推论为假**（源目录不存在也可能因为它的文件被**删除**）」，R5 指出的假等价句已删；
`design.md:252-256` 给出 R5 的构造、结论（「现稿在这种构造下**不再把 `x` 当 active**」）、
「**这是有意的行为变化，已登记**」与 fail-closed 对照；`spec.md:331-336` 登记了这一条并把
「被删文件里受保护的那几类（manifests / events）仍要解释事件」显式写出；`§5.1 2c`（`design.md:381-384`）
与 `tasks.md` 2.11b（`:120-122`）两条用例（①变绿 / ②仍红）都在。

**（b）行为变化登记**准确**：我按现稿文本复算，两条用例都成立**：

```bash
$ python3 /tmp/r6sim.py /tmp/r5cases/pmd_valid main feature
  cand 2026-10-15-x   c1=True c2=True c3=True c4=True c5=True srcs=['x'] arrived=True
  ARRIVED = ['2026-10-15-x']   ACTIVE = []            ⇒ 绿（今天：真 CLI 红 5 项，R5 已实测）
$ python3 /tmp/r6sim.py /tmp/r5cases/pmd_invalid main feature2
  cand 2026-10-15-x2  c1=True c2=False … arrived=False
  ARRIVED = []   ACTIVE = ['x']                       ⇒ 红（fail-closed 对照成立）
```

**（c）登记是否**完整**？——我自造了任务书点名的两个构造 + 两个附加构造，结论：**这两条形态都不翻转**，
登记没有漏掉它们**：

| 构造（`/tmp/r6cases/…`） | diff 要点 | 今天 | 现稿 | 翻转？ |
|---|---|---|---|---|
| `A_delall_unrelated` | **删除 `changes/x/**` 全部**（纯 `D`）+ 新建**与 x 无关**的件齐到达目录 `archive/2026-10-15-y/`（全新内容）+ 改 `src/app.py` | 红（`x` 幽灵 id） | `ACTIVE=['x']` ⇒ **红** | **否** ✅ |
| `B_rename_unrecognized` | 删除 `x` 其余文件 + 只把 `notes.md` 搬进**件齐但名字不认得 x** 的 `archive/2026-10-15-misc/` | 红 | `c4=False` ⇒ 该目录**不是到达** ⇒ `x` 仍被问话 ⇒ **红** | **否** ✅ |
| `D_delall_recognizing_born` | 删除 `x` 全部 + 新建**名字认得 x** 的件齐到达目录（**出生即归档**、无 rename） | 红 | `srcs=[]` ⇒ 无到达组 ⇒ `ACTIVE=['x']` ⇒ **红** | **否** ✅ |
| `C_pmd_rest_moved` | 删除 `x` 的 `design/proposal/reviews` + **把其余两份搬到 `src/`**（不是删除）+ 一个文件搬进名字认得 x 的到达目录 | 红（`x` 幽灵 id） | `ACTIVE=[]` ⇒ **绿** | **是**（同族） |

⇒ **翻转的**充要前提**是「有一条 rename 记录把 `changes/x/…` 的文件落进那个到达目录」**（这同时让 `x`
成为判据 4 的「源」）。上述 A/B/D 三条都没有这条 rename ⇒ `x` 逐条仍被问话 ⇒ 红，**登记没漏**。
`C` 与已登记项**同一机制、同一结论**，只是登记文案写的是「删除…其余文件」而 `C` 是「其余文件被搬到别处」
⇒ 归入「措辞项 11」（不影响任何用例判红判绿）。

**（d）登记理由的一句自洽性核对**：`spec.md:334-335` 声称「被删文件里受保护的那几类
（`reviews/*.manifest.json` / `workflow-events.jsonl`）仍要解释事件」——**源码核对成立**：
`D` 记录在 `gitutil._parse_name_status` 里 `old_path` 为空（`gitutil.py:127-128` 走 else 分支），
而 D5 的豁免要求 `old_path` 落在 `<changes_root>/<active-id>/` 下（`spec.md:246-248`）⇒ 该记录拿不到豁免；
`checkcmd._protected_writes`（`checkcmd.py:260-285`）对 `D` 用 `(change.path, "D")` 作待解释路径，
命中不变集 `**/reviews/*.manifest.json` 且 `status[:1] != "A"` ⇒ 仍报 finding ⇒ 红。
（**未跑真实现**——实现尚不存在；这是按源码的推演，标为「源码核对」，不是实测。）

---

## 独立证伪

### A. 找绕过

**A0（先给负面证据）**：本轮**没有**找到「比 `§8 Q4(c)` 已接受的逐字节天花板更便宜」的新绕过，
也**没有**找到能绕过判据 1 / 2 / 3 / 4 的新构造。Fix 1 关掉的正是 R5 的 A1；Fix 2 不改安全面（只改排除键的
条件与登记）。我的模拟器在 **55 个既有构造**上的结论与 `design.md §7.4` / R5 的 C 表**逐条一致**
（例外只有 `pmd_*` 两条：`pmd_valid` 现稿 `arrived=True`、`pmd_invalid(feature2)` `ACTIVE=['x']`——
这正是 R5 的 M2 修好后的预期）。

**A1（试过但**失败**的绕过，逐条写清失败点，免得后来者重复）**：

| 尝试 | 结果 |
|---|---|
| 用符号链接借**报告** | 命中（part 3 的 `120000` 规则）；且 `resolve_report_path` 本就拦指向 A 外的链接（`contract.py:296-300`） |
| 把**目录** `specs` / `reviews` 本身做成符号链接 | 命中（`ls-tree -r <A>/specs` 返回链接 blob 自身，已实测）；即便 Ev(A) 侧漏，证据门也会因 `report_path` 逃逸判红 |
| 符号链接指向 **A 内**的兄弟文件（合法样态） | **也命中** ⇒ 这正是 M1（误伤面），不是绕过 |
| 借 `proposal.md` / `design.md`（不在 `Ev(A)`） | 无收益：二者不被 manifest 绑定、证据门不读其内容（`design.md:64-65`） |
| **`.gitattributes` 的 `text`/`eol` 归一**让 blob ≠ worktree 字节 | 构不成绕过：`text` 属性在 `git add` 时把内容归一到 LF，blob 反而**等于**基准树里的 blob ⇒ (a) 命中（更红） |
| 用 `filter.*.clean` 让 blob 与 worktree 分叉（判据 5 读树、证据门读盘） | **理论面，未构造**（需要 `.git/config` 里的 filter 配置，CI 上不存在 ⇒ 检出的 worktree 与 blob 一致 ⇒ 证据门按 blob 内容算哈希 ⇒ 与本地 `manifest build` 记的哈希不符 ⇒ 红）。见「未验证项 4」 |
| `ident` 属性（`$Id$` 展开） | 同上：blob 侧被归一 ⇒ 不可能既「blob 新」又「worktree 逐字节等于受害者」 |

**A2（`D` 侧排除键的边界）**：我构造了 `D_delall_recognizing_born`（删全部 + 出生即归档的认得名目录）
与 `A_delall_unrelated`（删全部 + 无关到达目录），两者 `x` 都**没有**被静默排除 ⇒ 排除键没有过宽。
`r4cases/i3_dpath_alive_src`（源目录仍在 head）⇒ `ARRIVED=['2026-10-15-z']` 且 `ACTIVE=['z']` ⇒ 收窄生效 ✅。
`r3cases2/t471d_two_sources`（两个源都在 head）⇒ 两个源都仍是 active target（`ACTIVE=['foo-z','z']`）✅。

### B. 找假阴性 / 误伤

- **B1 新误伤（**本轮的核心发现**）**：Fix 1 的 fail-closed 规则命中**合法**样态 ⇒ 见「必须修改项 M1」。
  最小复现两份：`/tmp/r6cases/symlink_report_move`（符号链接**报告**——本仓有测试钉绿的布局）
  与 `/tmp/r6cases/symlink_move_legit`（符号链接 `tasks.md`）。今天真 CLI **两次都判绿**（见 M1 原始输出）。
- **B2 既有测试面复核**：通读 `tests/test_archive_awareness.py`，逐条判断新判据下的结果——
  `:151`（纯 move + 改码 ⇒ 归档路径上报四条缺件）⇒ 到达 ✅ 结论不变；
  `:175`（内容→证据→纯 `R100` 归档）⇒ 到达 ✅ 仍绿；
  `:240`（归档前 manifest 归档后仍绿）⇒ 到达 + 别名 ✅；
  `:403`（纯归档 PR 恰好 1 条 finding）⇒ 到达 ✅ 计数不变；
  `:430`（别名不放松 change_id）⇒ 到达 ✅；
  `:494` / `:600` / `:109` / `:49` / `:274` ⇒ 已在「必须改写（5 条）」里 ✅；
  `:541` / `:577` / `:378` ⇒ 确实**不需要**改写（`:541` 缺 `reviews/` ⇒ `c2=False`；`:577` 无 rename 记录
  ⇒ 无到达组 ⇒ `targets=[]`；`:378` 同）✅。**未发现**清单外的既有测试会翻红。
- **B3 E11/E12 复核**：`/tmp/r5cases/e11_proper` ⇒ `arrived=True`（共用 `proposal/design` stub 不误伤）✅；
  `/tmp/r5cases/e12_copy` ⇒ `arrived=False`，命中项含 `specs/cap/spec.md` ✅。
- **B4 组织型子目录**：`cases/r12_org_dir`（`archive/2026/`）⇒ `c2=False`；`cases/r15_org_dir_with_reviews`
  ⇒ `c2=False` ⇒ 都不是 target、都报「没有任何 change 目录」✅。
- **B5 空文件豁免**：`r4cases/empty13_gitkeep` ⇒ `arrived=True` ✅。

### C. 判据逐条（`design.md §5.3` 的 N1–N22 + `§5.1` 第 1–14 条 + 2b/2c，我的独立复算）

| 用例 | 期望（现稿） | 我的复算（构造） | 一致？ |
|---|---|---|---|
| N1 只改 `src/**` | 红 | 无 target | ✅ |
| N2 改已存在归档目录（`M`） | 红 | `r4cases/t577_touch_existing_archive`（head=`touching`）⇒ 无到达 | ✅ |
| N3 往已存在归档目录新增（`A`） | 红 | `cases/r10_preexisting_plus_file` ⇒ `c1=False` | ✅ |
| N4 单文件移入**既有**归档目录 | 红 | `r3cases/n6_partial_into_existing` / `r3cases2/n6_exact` ⇒ `c4=False` 且无到达 | ✅ |
| N5 删除 change 目录 | 红 | `cases/r13`… 反例见 `r3cases2/t494_tie` ⇒ `ACTIVE=['x']` | ✅ |
| N6 到达但零 manifest | 红（逐条点名三 stage） | 到达成立；证据门部分同上（`symlink_gate2` 早期版本真 CLI 实测 3 条 stage finding） | ✅ |
| N7 到达目录缺必需件 | 红，报「没有任何 change 目录」 | `r4cases/t541_forged_missing_reviews` ⇒ `c2=False` | ✅ |
| N8 已存在归档目录改名 | 红（判据 3，且判据 5） | `cases/r8_rename_archived` ⇒ `c3=False` | ✅ |
| N9 纯 `cp -r` | 红（判据 5） | `cases/r1_copy` | ✅ |
| N10 复制 + 改路径 | 红 | `cases/r2_copy_specrename` / `r3_copy_reportext` | ✅ |
| N11 复制 + 只改一处 | 红 | `cases/r4_copy_onebyte` | ✅ |
| N12 复制 + 删一个证据文件 | 红 | `r5cases/n12_del_one`；另有 `cases/r9_copy_then_delete` | ✅ |
| N13 `git mv` 无关文件洗白（A1） | 红 | `cases/r16_copy_plus_add` | ✅ |
| N14 源是嵌套归档目录（A3） | 红 | `cases/r21_nested_source` | ✅ |
| N15 混源 | 红 | `cases/r5_mixed_sources` | ✅ |
| N16 / N17 组织型子目录 | 非 target | `r12` / `r15` | ✅ |
| N18 base 同路径是 blob | 红（判据 1 有 entry） | `cases/r11_base_blob` ⇒ `c1=False` | ✅ |
| N19 报告挪出 `reviews/`（R3-A1） | 红 | `r3cases/a1_report_repath` / `r4cases/i1a_deep_referenced` | ✅ |
| N20 换路径形态（`specs` 同名文件 / `tasks.md` 目…） | 红 | `r3cases/a3_repath_plus_specs_file` / `r3cases2/a3b_specs_file_pristine` / `a5_tasks_as_dir` | ✅ |
| **N22 符号链接搬运（R5 的 M1）** | 红（第 5 条 + 普通文件要求） | `/tmp/r5cases/symlink_ev` ⇒ `c5=False`（三条 `mode=120000`）⇒ `arrived=False` | ✅ **（本轮修复，复核成立）** |
| N21 每个证据文件各加一字节 | **不红（已知天花板）** | `r3cases/a2_all_one_byte` ⇒ `arrived=True` | ✅（与设计一致） |
| 受保护文件搬进到达目录 | 仍要解释事件 | 判据层不覆盖；**源码核对**：D5 豁免要求 `old_path` 落 `<cr>/<active-id>/`，`openspec/specs/x.md` 不满足 ⇒ 仍要事件（`spec.md:246-250`、`checkcmd.py:260-285`） | ✅（实现期义务） |
| 归档时顺带改 change id | 红（判据 4） | `r3cases2/f3_change_id` ⇒ `c4=False`、`ACTIVE=['old-id']` ⇒ 红 | ✅（**今天亦红**，见措辞项 7） |
| `§5.1` 1/2/2b/2c/4/5/10/12/13 条 | 见正文 | `r13`/`r7`/`m1`/`m3`/`pmd_valid`+`pmd_invalid`/`r15`/`i3_dpath_alive_src`/`n6_*`/`empty13_gitkeep` | ✅ |
| **`§5.1` 第 1/5/10/13 之外的「合法 move 含符号链接」** | **现稿未写**（无对应用例） | `symlink_move_legit` / `symlink_report_move` ⇒ **今天绿、现稿红** | ❌ **见 M1** |

**C 的唯一例外**：合法整目录 move 含符号链接（现稿用例表未覆盖）——即 M1。

### D. 与源码事实核对（`文件:行号`）

| 断言 | 出处 | 核对 |
|---|---|---|
| `is_archive_move` 要 `R100` + `old_path` | `design.md:13` | ✅ `contract.py:65,72` |
| `changed_change_ids` / `archived_sources` 用 `is_archive_move` | `design.md:15` | ✅ `contract.py:85,97-101` |
| `archive_grant` | `design.md:16` | ✅ `contract.py:119,133,145` |
| `_protected_writes` / `is_archive_move` 分支 | `design.md:17` | ✅ `checkcmd.py:228,255` |
| `changed_files` 三点 + `--find-renames` | `design.md:18-19` | ✅ `gitutil.py:99,105` |
| `_parse_name_status` 对 `D` 把路径放 `path`、`old_path` 留空 | `design.md:260-261` | ✅ `gitutil.py:124-129` |
| `stale_exempt_paths` 整块豁免 `archive/**` | `design.md:214-215` | ✅ `policy.py:77,86-92` |
| `HASHED_ARTIFACTS` = `tasks.md` + `specs` | `design.md:104` | ✅ `constants.py:87-90` |
| `manifest build` 硬编码 `<label>/reviews/` | `design.md:109,191` | ✅ `manifestcmd.py:136-142,201` |
| `manifest build` 每次从磁盘重算哈希 | `design.md:137` | ✅ `manifestcmd.py:146-153` |
| `manifestcmd` 不调 `change_targets`、按磁盘存在性解析 | `design.md:316-318` | ✅ `manifestcmd.py:33-48`；`grep -n change_targets src/witnessloop/manifestcmd.py` 为空 |
| `contract.py:9`「hash 绑定…不防伪造」 | `design.md:175` | ✅ `contract.py:8-9` |
| `resolve_report_path` 与哈希校验同一口径 | `design.md:106` | ✅ `contract.py:282-300` |
| `§5.2` 逐条点名的既有测试行号 | `design.md:410-445` | ✅ 逐一 `sed -n` 命中（`:49/:87/:101/:109/:134/:274/:378/:471/:494/:541/:577/:600/:621`） |
| `tests/test_orphan_reports.py:273` 断言符号链接报告**不是**孤儿（绿） | （本轮新增核对） | ✅ 实跑 `1 passed` |

**D 结论**：设计稿里的源码级事实断言本轮**未发现新的错误**。

### E. 低危观察（不阻塞）

1. **`Ev(A)` part 3 在 `reviews` 本身是符号链接时的枚举口径**：此时 part 2 的 glob 与 part 3 的「其下全部文件」
   在**树**里都取不到条目（`reviews` 是一个 blob）。现稿的 mode 规则**恰好**补上了这个洞（`ls-tree -r <A>/reviews`
   返回该 blob 自身 ⇒ 命中 `120000`），但这是**实现细节**层面的兜底——建议把「`<A>/reviews` 自身若是 blob（含
   `120000`）如何处理」写进 `tasks.md` 3.2 的接线点，避免两种实现的 `c5` 结论分叉。**不构成绕过**（证据门
   也会因 `report_path` 逃逸判红）。
2. **`workflow-events.jsonl` 仍不在 `Ev(A)`**：事件是自由文本、作者自写即可（`evidence.py` 明写「防漂移不防伪造」）
   ⇒ 不是新面（R5 的 E2 同）。建议在 `§D1 已知边界` 登记一行（**仍未落**）。
3. **`archive/` 直接子项是 blob 的形态**（R4 的 E6）：现稿仍无条款；建议在 `tasks.md 3.2` 写死「候选只取 head 里是
   **tree** 的直接子项」（**仍未落**）。
4. **`§5.3` 末行（归档时顺带改 change id）**仍写「**当前设计下红**」而与「今天亦红」的实测（`f3_change_id`）不并列
   ⇒ 见措辞项 7。

---

## 未验证项

1. **接入方的具体数字**（`proposal.md` 的 33 文件全 `A`、`R068/R069/R070/R090`、16 文件 11 项、120 个归档目录）
   ——另一个仓的提交，本工作区**无法复算**（R1–R5 同）。
2. **现稿的「实现」不存在**：A/B/C 里**到达判定那一半**全部来自我按文本逐字转写的 `/tmp/r6sim.py`；
   证据门那一半在 e2e 构造里是真 CLI。最敏感的四处：① `report_path` 的解析口径（我按 `..` 归一 + 必须在 A 内 +
   跟随树内符号链接至多 8 跳，未复刻 `Path.resolve()` 的全部细节）；② 空文件按 head **blob 字节数**判（`git cat-file -s`）；
   ③ `C` 记录**不算** (b) 的影响（`gitutil.py:105` 只传 `-M`，实测构造不出 `C`）；④ 候选枚举只取 **tree**。
3. **gitlink（`160000`）**：规则文本覆盖，但我**未构造**真实子模块用例（`archive/<name>/specs` 下挂子模块），
   因此「今天绿 → 新稿红」的**程度**未实测（机理与符号链接同源）。
4. **`filter.*.clean` 让 blob 与 worktree 分叉**这一理论面：未构造（需要 `.git/config` 里的 filter，
   CI 上不存在 ⇒ 检出内容 = blob ⇒ 证据门按 blob 算哈希 ⇒ 与本地 manifest 记录的哈希不符 ⇒ 判红）。
   我判定它**不构成可用绕过**，但这是**推演**，非实测。
5. **浅克隆 / partial clone 下「`merge-base` 成功但 `ls-tree` 失败」这一独立面**：仍未复现（R1–R5 同）。
6. **merge commit 形态**：未取得可判定结论（R2–R5 遗留）。
7. **自定义 `review_manifest_glob` / `required_artifacts` 覆写成多段名的端到端**：只做了取值与树可见性的核对。
8. **大仓（≥100 个归档目录）下逐字节撞车的概率**（`tasks.md` 4.6）：未测。
9. **`docs/gate.md` / `README.md`** 的对应改动属实现期义务，尚未落 ⇒ 未核。
10. **§5.1 第 6 条（树读不出来 ⇒ fail-closed）**：只做了设计文本核对，未构造「`merge-base` 成功但 `ls-tree` 失败」的真仓。

---

## 必须修改项

### M1（低-中危，Fix 1 的射程）「`Ev(A)` 每一项须是普通文件」这条 fail-closed 规则**误伤合法样态**，且该行为变化**未登记**

**它是一条 green→red 的行为变化，今天真 CLI 实测绿、现稿判红，且没有任何文档条目覆盖。**

**最小复现 ①（符号链接**报告**——本仓自己有一条钉绿测试支持的布局）**：

```bash
$ cd /tmp/r6cases/symlink_report_move
$ git ls-tree -r HEAD -- openspec/changes/archive | grep alias
120000 blob 5f75b75d47c53bd327abb872a7c39a7a823bd941 openspec/changes/archive/2026-10-15-z/reviews/alias.md
#   alias.md -> grill-review.md（reviews/ 下的符号链接；正是 tests/test_orphan_reports.py:273 钉绿的布局）
$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD     # 今天真 CLI：整目录 git mv 归档
check：基线 main...HEAD，11 个变更文件，1 个 change 目录
  change：2026-10-15-z（归档）
check：通过 ✓
exit=0
$ python3 /tmp/r6sim.py . main feature -v                                   # 按现稿文本转写的判定
  cand 2026-10-15-z   c1=True c2=True c3=True c4=True c5=False srcs=['z'] arrived=False
        ✗ openspec/changes/archive/2026-10-15-z/reviews/alias.md  (mode=120000 非普通文件)
  ARRIVED = []   ACTIVE = ['z']   code_hits=0 targets=1 ⇒ RED(active 目录不存在: ['z'])
```

**最小复现 ②（符号链接 `tasks.md`）**：`/tmp/r6cases/symlink_move_legit`——同一 repo 结构，
`2026-10-15-z/tasks.md` 是 `120000`（指向同目录的 `design.md`，`git mv` 后仍有效）。
今天真 CLI：`check：通过 ✓`（`1 个 change 目录 / change：2026-10-15-z（归档）`，exit 0）；
现稿模拟器：`c5=False`（`…/tasks.md (mode=120000)`）⇒ `arrived=False` ⇒ `ACTIVE=['z']` ⇒ 红。

**为什么这是可证伪项（而不是「已接受的 fail-closed 方向」）**：

1. **今天判绿**（上面两次真 CLI 原始输出，exit 0）⇒ 这是**行为变化**，不是「本来也红」。
2. **它命中的是本仓明确支持的布局**：`tests/test_orphan_reports.py:273 test_symlinked_report_is_not_an_orphan`
   断言「只绑链接 ⇒ 不误报孤儿 ⇒ `check` 通过」（我实跑 `1 passed`）；`contract.py:323` 与 `docs/gate.md:157`
   也把符号链接列为**需正确解析**、而非需拒绝的对象。⇒ R5 的 M1 里那句「**不引入误伤**（正规 change 不会把证据
   做成符号链接）」的前提**为假**：本仓自己就把符号链接报告当作**正规**布局钉了绿。
3. **未登记**：`spec.md:327-336` 的「有意的行为变化」只有 2 条（复制式归档 / D4 的 pmd 族），
   `design.md:178-184` 的「误伤面」列了 3 类现实来源（兄弟 change 的 `specs/**`、`PASS\n` 样板、模板骨架）
   **不含符号链接**；`§D1 已知边界`（`design.md:186-202`）也不含。⇒ 接入方读任何一节都推不出这条。
4. **它使 spec 自己的 Scenario 失守**：`spec.md:306-309`「同一内容两种位置结论一致」的 Given 是
   「同一份 change 内容（件齐 + 三份 manifest + 报告），一份在 `changes/<id>/`、一份在 `archive/<name>/`」，
   Then 是「两者的判绿判红结论相同」——对本布局，**active 位置绿、archive 位置红**。
5. **有严格更好的写法，且 R5 自己给过**：R5 的 M1 要求里选项 ① 的原话是「…SHALL fail-closed（**或按解析后的
   内容参与 (a)/(b) 比对**）」。按**解析后的内容**比对时：本布局的 `alias.md` 解析到 A 内的 `grill-review.md`，
   该 blob 是本次改名落点 ⇒ (b) 成立 ⇒ **绿**（与今天一致）；而 R5 的 `symlink_ev`（`tasks.md -> ../2026-09-30-old/tasks.md`）
   解析后的 blob 落在基准树 `changes_root/**` 且不是本次改名落点 ⇒ (a)(b) 皆不成立 ⇒ **红**（攻击仍被关掉）。
   ⇒ 现稿选的那一档（无差别 fail-closed）**不是**封堵该绕过所必需的：`cp` 那一档本来就红，
   符号链接这一档用「解析后比对」或「仅对**逃出 A** 的链接 fail-closed」即可。

**要求（二选一，或并取；都能在一轮内收官）**：
- **① 收窄规则**（推荐）：把现稿的「`Ev(A)` 每一项 SHALL 是普通文件」改成
  **「SHALL 按**解析后**的内容参与 (a)/(b) 比对；符号链接／gitlink **解析出 `A` 之外**（或无法解析）者 ⇒ fail-closed」**
  （等价写法：解析后的目标仍在 `A` 内 ⇒ 正常比对；逃出 `A` ⇒ 不授予）。同步 `spec.md:59-62`、
  `design.md:112-115`、`tasks.md 2.9⑬`、`§5.3 N22`，并把 `N22` 的期望值写清（链接**指向 `changes_root` 里
  现成 change** ⇒ 红；链接**指向 `A` 内** ⇒ 按 (a)/(b) 判）。
- **② 保留现稿的无差别 fail-closed**：则**必须登记**——在 `spec.md:327-336` 的「有意的行为变化」加一条
  （「证据里含符号链接／gitlink 的到达目录不再被授予资格；**合法整目录 move 亦然**（今天绿）」），
  并在 `design.md:178-184` 的「误伤面」与 `§D1 已知边界` 各补一行、`§5.2` 的回归面注明
  「`test_symlinked_report_is_not_an_orphan` 的布局在**归档侧**不再成立」、补一条钉住该行为的用例。
- 并给 `spec.md:306-309` 的 Scenario 补上与 `D2` 同等的一行限定（该 Scenario 现为无保留的全称断言）。

**为何是必须（而非措辞）**：它是一条**今天绿 → 改动后红**的判红判绿差异，未被任何用例 / 边界条目覆盖，
且与本仓既有钉绿测试的布局直接冲突。

---

## 措辞项（不影响判据语义、不影响任何用例判红判绿；可当场落库）

1. **`design.md:483-485`（`§5.3` 表序）**：N22 被插在 **N20 与 N21 之间**（`N20` → `N22` → `N21`），
   编号序又被打破——R5 的措辞项 3 刚把这张表排成 `N1`→`N21`（R5 报告 `:47` 记为「已落」），本轮插入 N22 时回退。
   改法：把 `N22` 移到 `N21` 之后（末行「—」之前）。
2. **`tasks.md:66` 与 `tasks.md:165`**：两处写「**N1–N21 逐条**」/「逐条复算 … **（N1–N21）**」，
   未含本轮新增的 **N22**（4.4 的复算范围会漏掉它）。改成 `N1–N22`（并把 N21 的豁免说明保留）。
3. **`tasks.md:32`**：与 `:30-31` **重复**了一行「**收敛判据 = 一轮下来没有新的可证伪项、且所有「必须修改项」都已落库**；没有轮数上限。」
   （`:30-31` 已写同一句）⇒ 删去重复的那一行。
4. **`design.md:370`（R7 行，R5 措辞项 1 **未落**）**：「必须**每一份**被复制的证据文件都**重写**（或改成 `git mv`）」
   与 `design.md:163-176` 的能力天花板口径打架（天花板是「每份 +1 字节」）⇒ 改为「每份至少动一个字节（见 §D1 的能力天花板）」。
5. **`design.md:346-348`（`§3` 第 5 条的 `docs/gate.md` 清单，R5 措辞项 2 **未落**）**：清单里仍**没有**
   「模板 SHALL 放在 `changes_root` 之外」，而 `design.md:567` 的 B3 行把这个指针指到了「`§3` 第 5 条」⇒ 指针半悬。
   补上该项，或把该指针改成「`tasks.md 6.1`」。
6. **`spec.md:36-37`（R5 措辞项 3 **未落**）**：判据 2 写「判定语义 SHALL 与契约门**完全一致**」，
   而 `design.md:87-88` 要求实现**忽略**空串 / `.` 这类退化 artifact 名（契约门 `(dir/"").exists()` 恒真）
   ⇒ 两处口径不同；建议 spec 补同一句偏离说明。
7. **`design.md:487`（R5 措辞项 4 **未落**）**：「归档时顺带改 change id」行仍只写「**当前设计下红**（第 4 条）」，
   建议补「**今天亦红**」（我的 `r3cases2/f3_change_id` 复算：`arrived=[]`、`ACTIVE=['old-id']` ⇒ 今天也红）。
8. **`design.md:190`**：「判据 5 的效力**完全依赖**『`<changes_root>/**` 是存放 change 证据的唯一地方』这一前提」
   ——该「完全依赖」是 R5 的 A1 顺带证伪过的措辞（现稿 `spec.md:84` 已软化成「依赖」，design 未同步）。
   建议补半句：「**另有逐字节天花板**这一独立绕过（见下一条）」。
9. **`design.md §D1 已知边界`（`:186-202`，R5 措辞项 6 **未落**）**：建议补两条——
   ①「`workflow-events.jsonl` 不在 `Ev(A)`」（自由文本，非新面）；②「`archive/` 的直接子项若本身是 blob ⇒ 不是候选（候选只取 tree）」。
10. **`tasks.md:137-141`（3.2，R5 措辞项 7 **未落**）**：建议把「候选只取 head 里是 **tree** 的直接子项」写死。
11. **`spec.md:331-336`（本轮新增观察）**：行为变化 2 的构造写的是「**删除** `changes/<id>/` 的其余文件」，
    而同一机制也覆盖「其余文件被**搬到别处**」（我的 `/tmp/r6cases/C_pmd_rest_moved`：把 `x` 的 `tasks.md`/`specs` 
    搬到 `src/`、其余删除、一个文件搬进名字认得 `x` 的到达目录 ⇒ 现稿 `ACTIVE=[]` ⇒ **绿**，与已登记项同结论）。
    建议把该条写成机制口径：「源 change 目录在 head 里消失（其文件被**删除或被搬走**）」（不影响任何用例判红判绿）。
12. **`tasks.md`（R5 措辞项 5 **未落**）**：仍未列 `spec.md` 的「既有行为不变（回归护栏）」Requirement 的落地任务
    （该 Requirement 是 R1 的 M6 之后新增的，`tasks.md` 1.x 里没有对应条目）。

---

## 收敛结论

**不收敛。**

**判据（沿用本 change 自己写的，`tasks.md:30-32`）**：一轮下来**没有新的可证伪项**、**且所有「必须修改项」都已落库**。

- **「R5 的两处修复已落库且成立」这一半：成立。**
  - **Fix 1**（符号链接 / gitlink fail-closed）：规则文本三处齐（`design.md:112-115` / `spec.md:59-62` /
    `tasks.md 2.9⑬`）、用例 `§5.3 N22` 在；我的独立模拟器在 `/tmp/r5cases/symlink_ev` 上复算
    `arrived=False`（三条 `mode=120000`）⇒ **R5 的 A1 确已关闭**，且该结论对 `Ev(A)` 的三种解释都成立。
  - **Fix 2**（D4 措辞 + 行为变化登记）：假等价句已删（`design.md:249-251`）、行为变化已登记
    （`spec.md:331-336`）、两条用例（`§5.1 2c` / `tasks.md 2.11b`）在；我用自造构造复算
    `pmd_valid`⇒绿、`pmd_invalid`⇒红（fail-closed 对照成立），并**用 4 个自造构造逐一验证了登记的完备性**
    ——任务书点名的两条（删全部+无关到达目录、删其余+名字不认得）与另一条（删全部+名字认得但无 rename）
    **都不翻转**，翻转的充要前提是「有一条 rename 记录把源目录的文件落进到达目录」，登记没有漏。
- **「没有新的可证伪项」这一半：不成立。** 本轮独立复算给出 **1 条新的、可复算的、影响判红判绿的**证伪项
  **M1**：Fix 1 的 fail-closed 规则本身误伤**合法整目录归档 move**（证据含符号链接），
  **今天真 CLI 两次判绿（exit 0，原始输出见 M1）、现稿判红**；命中的恰是本仓有钉绿测试支持的布局
  （`tests/test_orphan_reports.py:273`，实跑 `1 passed`），且未出现在 `spec.md` 的「有意的行为变化」、
  `design.md` 的「误伤面」与「已知边界」中，并使 `spec.md:306-309` 的无保留 Scenario 失守。
  它**不是**安全级新绕过（方向是 fail-closed），但**不是**「纯措辞 / 计数 / 指针」。
- ⇒ 按判据，**本轮判定不收敛**，阻塞项只有 **M1**，且它能在**一轮内**收官：**要么**把规则收窄成
  「按解析后的内容比对，只有解析出 `A` 之外的链接才 fail-closed」（R5 的 M1 选项 ① 已给出，且比现稿**更精确**：
  攻击仍红、合法样态仍绿），**要么**保留现稿口径但把这条行为变化**登记**进
  「有意的行为变化 + 误伤面 + 已知边界」并补一条用例 + 给 `:306-309` 的 Scenario 加限定。
  其余 12 条均为**措辞 / 计数 / 指针**类，不阻塞。

---

### 附：本轮的复算资产（全部在 `/tmp`，未改仓内任何文件）

- 模拟器：`/tmp/r6sim.py`（`python3 /tmp/r6sim.py <repo> [base] [head] [-v]`，只读 git 树）。
- 新构造（`/tmp/r6cases/`）：
  - `symlink_report_move`、`symlink_move_legit` —— **M1 的两份最小复现**（前者是本仓钉绿的符号链接报告布局）；
  - `A_delall_unrelated`、`B_rename_unrecognized`、`D_delall_recognizing_born` —— 行为变化登记**完备性**的否定对照（都不翻转）；
  - `C_pmd_rest_moved` —— 同族但登记文案未覆盖的写法（措辞项 11）。
- 真 CLI 原始输出见 M1 与「R5 两处修复复核」的代码块（`check` 的 stdout/stderr 与 exit code）。
