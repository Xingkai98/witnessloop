# 对抗轮 R8（独立零记忆验证者）—— `archive-arrival-recognition`

> **结论摘要：已收敛，附带 8 条措辞项。**
> R7 报的两条必须项（M1 逃出 `A` 的拒绝面未登记 + Scenario 全称断言；M2 gitlink 枚举口径不自洽）**都已落库**，
> 且我**独立复算**确认新口径同时满足两侧：
> - **攻击仍红**：R5 的攻击构造（`symlink_ev` / `symlink_gate` / `symlink_gate2` / `symlink_archive_move`）、
>   偷字节（`inA_link_to_stolen`）、悬空（`dangling_inA` / `dangling_out`）、gitlink、以及我自建的
>   「链接指向 `changes_root` 内现成归档 change」（`p2`）全部不授予；
> - **合法仍绿**：R6 的两个钉绿构造 + `dir_link` + 我在本轮**新建**的正向半边构造
>   `p1`（链接指向 `<changes_root>` 之外**被跟踪**文件）与 `p4`（两跳后指向同一目标）**确实判绿**
>   ——R7 的 4 个「逃出 `A`」构造其实**全是悬空链接**（见 §R7 复核 ②），**正向半边在 R7 那一轮从未被真正测过**，
>   本轮补上了。
> - **gitlink / 悬空 / 未跟踪** 三类 fail-closed 在实现上可达成：`git ls-tree -r` 确实列 `160000 commit` 行（原始输出见下），
>   「未跟踪 / 悬空」在实现上收敛为「解析后的目标路径在 head 树里**没有 entry** ⇒ fail-closed」，可判、可测。
> **无新的必须修改项。**本轮报出的全部是措辞 / 登记 / 口径钉死类问题（**不影响任何用例的判红判绿**），
> 其中 3 条值得下一轮顺手改掉（`design.md:500` 的陈旧陈述、`(b)` 的判定对象、`spec.md:63` 与 `design.md:120` 的 gitlink 作用域）。

---

## Reviewer

**零记忆声明**：本对话不携带该 change 的任何历史。R1–R7（`reviews/grill-adversarial*.md` / `grill-design.md`）的结论
**只当待复核的声明**；三份文档里的「实测」「`文件:行号`」一律当**待验证断言**。
判据模拟器 `/tmp/r8sim.py` 由我**从零写成**（只按 `design.md §2 D1` + `spec.md` **当前正文**转写，只读 git 树，
**未**沿用 `/tmp/r3sim.py`…`/tmp/r7sim.py`，也没读它们的判据逻辑；唯一读过的是各 case 仓里的**数据**）。
本轮只写 `reviews/` 下这一个文件；未改 `src/` / `tests/` / 任何 change 文档；未 commit、未 push。

**HEAD**：`9db4c53b9a0f4023da841a98cc40d2ac01f31c7c`（`…按对抗轮 R7 回写…`）。工作树干净。

**读过的**：`design.md`（711 行）/ `specs/archive-awareness/spec.md`（366 行）/ `tasks.md`（212 行）/ `proposal.md`；
源码 `contract.py` / `checkcmd.py` / `gitutil.py` / `policy.py` / `constants.py` / `paths.py` / `hashing.py` / `manifestcmd.py`；
`tests/test_orphan_reports.py`；R7 报告全文；`git show 9db4c53`（R7 回写的**完整 diff**，用来核对「作者声明改了哪些地方」）。

**跑过的**：
- `/tmp/r8sim.py` 在**全部既有构造**上复算：`/tmp/cases/*`(18) + `/tmp/r3cases/*`(7) + `/tmp/r3cases2/*`(15)
  + `/tmp/r4cases/*`(10) + `/tmp/r5cases/*`(10) + `/tmp/r6cases/*`(7) + `/tmp/r7cases/*`(13) = **80 个**
  （引用按各仓实际分支：r7cases 多数用 `probe`，`t577` 用 `touching`，`pmd_invalid` / `symlink_gate` 用 `feature2`，`n12` 用 `n12`）；
- **自建 6 个新构造**（`/tmp/r8cases/*`，见 §R7 复核 ②）/ §独立证伪 A：`p1_link_out_tracked`、`p2_link_into_archived`、
  `p3_link_untracked`、`p4_link_chain_out`、`q1_link_launder`、`q2_specs_dir_link`；
- **今天的真 CLI**（`.venv/bin/python -m witnessloop check`，未改一行源码）在 7 个关键构造上取原始输出
  （用来验证「今天绿 → 本 change 红」这条登记的**事实前提**）；
- `pytest -q` 基线：**601 passed in 46.52s**（与 R7 报的基线一致）。

**方法学声明（沿用前几轮的口径，且必须写清楚）**：本 change **未实现**，所以「到达判定」那一半仍是
**按现稿文本逐字转写的模拟器**，只有「证据门」那一半是真 CLI。我的一切红/绿结论都只针对**到达判定**这一半。

---

## R7 修复复核

### 复核 ① 新口径是否让「R5/R7 的攻击构造仍红」「R6 的合法构造仍绿」

**成立。** 新口径（`design.md:112-120` / `spec.md:65-72`）= 链接**按解析后的内容**参与 (a)/(b)；
`A` 之内 ⇒ 目标并入 `Ev(A)`；`A` 之外且**被跟踪** ⇒ 按目标路径在 head 树里的 blob 比对；
**未跟踪 / 悬空 / gitlink ⇒ fail-closed**。

| 构造 | 我的复算（`/tmp/r8sim.py`） | 期望 | |
|---|---|---|---|
| `r5cases/symlink_ev`（链接指向 base 里现成 change） | `ARRIVED = []`；findings `(a)&(b) fail: …/reviews/link.txt -> …/archive/2026-09-30-old/reviews/grill-review.md blob=b251c876` | 红 | ✅ |
| `r5cases/symlink_gate` / `symlink_gate2` | `ARRIVED = []`（`(a)&(b) fail` 命中目标 blob `d3f2dd55`） | 红 | ✅ |
| `r6cases/symlink_archive_move` | `ARRIVED = []`（`symlink target untracked/dangling fail-closed`） | 红 | ✅ |
| `r7cases/inA_link_to_stolen`（`A/tasks.md → design.md` 之外还塞 `reviews/notes.bin` = base 里现成 `tasks.md` 的副本） | `ARRIVED = []`；`(a)&(b) fail: …/reviews/notes.bin blob=51a2efdb` | 红 | ✅（「目标并入 `Ev(A)`」这条递归仍承重） |
| **自建** `p2_link_into_archived`（`A/reviews/link.txt → ../2026-09-30-old/reviews/grill-review.md`，**被跟踪**的现成证据） | `ARRIVED = []`；`symlink (a)&(b) fail: … blob=b251c876` | 红 | ✅（**这是 R7 修复后新口径的正面攻击**：目标在 `changes_root` 之内且被跟踪 ⇒ 必须按 (a) 命中） |
| `r6cases/symlink_report_move` / `symlink_move_legit`（钉绿布局 `alias.md → grill-review.md`） | `ARRIVED = ['2026-10-15-z']` | 绿 | ✅ |
| `r7cases/dir_link`（`link.txt → ../specs`，指向 `A` 内目录） | `ARRIVED = ['2026-10-15-z']` | 绿 | ✅ |
| **自建** `p1_link_out_tracked`（`A/reviews/link.txt → …/docs/notes.md`，**仓根、被跟踪、在 `changes_root` 之外**） | `ARRIVED = ['2026-10-15-z']` | 绿 | ✅ |
| **自建** `p4_link_chain_out`（`link.txt → link2.txt → …/docs/notes.md`，两跳后仍是被跟踪的仓外文件） | `ARRIVED = ['2026-10-15-z']` | 绿 | ✅ |

### 复核 ② 一个必须说清楚的**方法学发现**：R7 那 4 个「逃出 `A`」构造**全是悬空链接**

R7 的 M1 用的是 `/tmp/r7cases/escape_doc`，声称「同一份合法内容，active 位置今天真 CLI 绿 / 归档位置新口径红」，
并声称反向对照是「`link.txt` 是普通文件」。**我把这 4 个构造的链接文本逐字读了出来**：

```bash
$ for c in escape_doc chain_escape abs_link dangling_inA dangling_out; do
>   for b in $(git -C /tmp/r7cases/$c ls-tree -r probe 2>/dev/null | awk '$1=="120000"{print $3}' | sort -u); do
>     printf '%-16s %s => ' $c ${b:0:8}; git -C /tmp/r7cases/$c cat-file -p $b; echo; done; done
escape_doc       a9d34b8b => notes.md                 # ← in-A 目标，未提交（悬空）
dangling_inA     a9d34b8b => notes.md
dangling_out     67dc2f10 => ../../../docs/notes.md
chain_escape     67dc2f10 => ../../../docs/notes.md
abs_link         503b84a2 => /tmp/r7cases/escape_doc/docs/notes.md
```

（`escape_doc` 的 `link.txt` 文本实为 `../../../../docs/notes.md`，链接位于 `A/reviews/` ⇒ 解析到
`openspec/docs/notes.md`，而仓里被跟踪的是**仓根** `docs/notes.md` ⇒ **目标不存在** ⇒ 悬空。）

⇒ **R7 的「逃出 `A` 但目标被跟踪」这一情形，四个构造一个都没覆盖**（全是悬空或仓外不存在路径）。
所以「新口径是否让『指向 `changes_root` 之外被跟踪文件的链接』仍绿」在 R7 那一轮**根本没有被证伪或证实**。
本轮我按 `spec.md:71` 的字面语义**新建**了 `p1` / `p4`（见上表），二者**判绿** ⇒ **R7 修复的正向半边成立**。
这一点要写进下一轮的上下文，避免把「R7 已验证」当成对正向半边的验证。

### 复核 ③ gitlink / 悬空 / 未跟踪 三类 fail-closed 的**可实现性**

**可达成，但文本对实现者的约束有三处没钉死（见 §措辞项 1/2/3）。**

（1）`git ls-tree -r` **确实**列 gitlink 行——我自己复跑了一遍（这是 R7 的 M2 事实，本轮独立确认）：

```bash
$ cd /tmp/r7cases/gitlink && git ls-tree -r HEAD -- openspec/changes/archive/2026-10-15-z/reviews/
100644 blob 61780798228d…  …/reviews/b.md
100644 blob 5fa534db247a…  …/reviews/building.manifest.json
100644 blob 31334094c7d1…  …/reviews/ga.md
100644 blob 107804909820…  …/reviews/grill-adversarial.manifest.json
100644 blob e86af71c35b1…  …/reviews/grill-review.md
100644 blob e5bd4d30abae…  …/reviews/grill.manifest.json
160000 commit 2f781bdcc1bf972c9994c2ddb72dd0cbb625e382  …/reviews/sub      # ← gitlink 行在
```
⇒ `spec.md:62-63` 的「枚举 SHALL 覆盖全部非 tree 行」是可实现的；`design.md:322` 的订正（「不含 tree 行，
但**含** `160000 commit` 行」）与我实测一致。

（2）**三类 fail-closed 在实现上收敛为同一句判据**：把链接文本按
`resolve_report_path` 同款解析（`Path.resolve()` + `pathutil.is_within`，`spec.md:69` / `design.md:116`），
得到目标路径 `T`；再查 **head 树**里 `T` 有没有 entry：
- **悬空**（`T` 在树里没有 entry）⇒ fail-closed；
- **未跟踪**（`T` 只存在于工作树）⇒ 树里同样没有 entry ⇒ fail-closed（这正是 R7 §E-1 要求的方向）；
- **gitlink**（条目 mode `160000`）⇒ fail-closed。

⇒ 三类的**判定动作是可写的、可单测的**（注入式假树即可覆盖），且都落在我复算的 `ARRIVED=[]` 一侧：
`r7cases/gitlink [probe] → []`（`gitlink fail-closed: …/reviews/sub`）、
`r7cases/dangling_inA [probe] → []`（`in-A symlink target untracked/dangling fail-closed: …/reviews/notes.md`）、
**自建** `p3_link_untracked`（`A/reviews/link.txt → secret.md`，`secret.md` 提交后从工作树塞入、未提交）`→ []`。
⚠️ 但**实现者要同时用「工作树解析」拿路径、用「head 树」取字节**——两套世界的交接点在文本里只写了半句
（`Path.resolve()` 是文件系统操作，而 `取…在 head 树里的 blob` 是树操作），见 §措辞项 2。

（3）**「今天绿」的事实前提成立**（这是登记准确性的关键，我用真 CLI 逐条验了）：

```bash
$ cd /tmp/r7cases/escape_doc && … check --root . --base main --head feature   # check：通过 ✓
$ cd /tmp/r7cases/dangling_inA && … check --root . --base main --head probe   # check：通过 ✓
$ cd /tmp/r7cases/gitlink     && … check --root . --base main --head probe   # check：通过 ✓
```
⇒ `spec.md:105-106` / `spec.md:354-356` 写的「改动前判绿、本 change 判红」**事实成立**。

### 复核 ④ 登记与限定是否**完整且互不矛盾**

**四处登记位里三处已落、一处（`§5.2`）没落**，另有一处**陈旧陈述**（`design.md:500`）与一处**口径差**（gitlink 作用域）。

| 登记位（R7 的 M1 要求 / 作者声明） | 现状 | |
|---|---|---|
| `spec.md` 误伤面 | ✅ `spec.md:105-106` | |
| `spec.md` 有意的行为变化 3 | ✅ `spec.md:354-356`（并给了「反向仍须绿」） | |
| `design.md §D1 已知边界` | ✅ `design.md:206-207` | |
| **`design.md §5.2`（回归面）** | ❌ **没有**——`sed -n '432,474p' design.md \| grep -n '链接\|符号\|gitlink'` **零命中**。作者的 commit message 与 `tasks.md:39` 都声称登记进了「`design.md` 的『已知边界』**与 §5.2**」，**§5.2 那一半没做** | 措辞项 6 |
| Scenario 限定 | ✅ `spec.md:320-326`（补了 `② 本 change 明写的内容来源边界`） | |
| R7 的「7 条措辞项已落库」（`tasks.md:40`） | ⚠️ **不准**：R7 措辞 1（`design.md:384` 的「每一份…都**重写**」）与措辞 6 的 tasks 半边（`tasks.md:155` 仍写「`-r` = 其下**全部 blob**」）**没落** | 措辞项 4 / 5 |

**一处新引入的自相矛盾（重要）**：`design.md:500`（§5.3 N22 行）**仍写着 R6 时代的旧口径**
「**逃出 `A` 的链接直接 fail-closed**」。这与 `design.md:118-119` 和 `spec.md:71`（`A` 之外且被跟踪 ⇒ 按 blob 比对 ⇒ 可绿）
**直接冲突**，而且**可被我的 `p1` 构造成品证伪**（`p1` 的链接逃出 `A`、目标被跟踪 ⇒ `ARRIVED=['2026-10-15-z']`）。
它**不影响 N22① 的判红**（那里目标在 `changes_root` 内，两种读法都红），但它是「作者改了口径却漏改 §5.3 表」的**新残留**。

**一处口径差**：`spec.md:63` 与 `tasks.md:127` 把 gitlink 的 fail-closed 写成「**`<A>` 下**（或 `Ev(A)` 里）出现 gitlink」，
而 `design.md:120` / `design.md:206` 只写 **`Ev(A)` 里**。二者对「A 根下、非证据位置（如 `A/notes`）的 gitlink」给出**不同结论**
（spec/tasks ⇒ 红，design ⇒ 绿）。§5.3/§2.9 明列的 gitlink 位置（`reviews/` 下、artifact 目录之下）都落在 `Ev(A)` 内，
**没有必须用例翻转** ⇒ 记为措辞项 3。

---

## 独立证伪

### A 绕过（尝试过、**未成功**的）

| # | 构造（我自建） | 结果 |
|---|---|---|
| A1 | `p2_link_into_archived`：链接指向 `changes_root` **之内**的现成归档 change（被跟踪） | **拒** ✅（(a) 命中目标 blob） |
| A2 | `q1_link_launder`：先把受害者的报告在**它自己的归档目录里改名**（使该路径成为本次 diff 的**改名落点**），再让 `A/tasks.md` 链接过去 | **拒** ✅（(a) 命中；`q1` 见 §措辞项 1 的读法分歧） |
| A3 | `q2_specs_dir_link`：`A/specs` 做成指向**现成归档 change 的 `specs` 目录**的链接（**目录值**目标，正对 N22① 的 `specs` 字样） | **拒** ✅（`ARRIVED=[]`，命中 `…/2026-09-30-old/specs/cap/spec.md`） |
| A4 | `p4_link_chain_out`：两跳链接（`link.txt → link2.txt → 仓外被跟踪文件`） | 绿 —— **这是修复的目标行为**（与 `cp` 同结论） |
| A5 | `p3_link_untracked`：链接指向**只存在于工作树、未提交**的文件 | **拒** ✅（fail-closed） |
| A6 | 目录值目标（`q2`）在「取 blob」的字面读法下**可能被跳过** ⇒ 可能翻绿 | 未能在**设计文本**上复现（文本经「与 `cp` 同结论」可定案为红）——记 §措辞项 3 |
| A7 | 硬链接借内容 | **未构造**（git 里就是普通 blob ⇒ 与 R5 同结论）——沿用前轮「未验证」 |

**结论：新口径**没有**被绕过。**R5 的攻击形状在「文件值目标」与「目录值目标」两种形态下都被关掉；
R7 造成的误伤也修掉了（`escape_doc_regular` / `ctrl_regular` 仍绿、`p1` / `p4` 如期绿）。

### B 假阴性 / 误伤（**新证伪：0 条**）

- **必须绿的全部仍绿**（我的复算）：`r6cases/symlink_report_move`、`symlink_move_legit`、`r7cases/dir_link`、
  `r7cases/escape_doc_regular`、`ctrl_regular`、`cases/r6_legit_move`、`r7_move_rebuild`、`r13_born_archived`、
  `r4cases/empty13_gitkeep`、`r5cases/e11_proper`、`r4cases/i1b2_separation_clean`、`i3_dpath_alive_src`、
  `i5_cp_from_outside_root`、`r3cases2/a4b_outside_root`、`r3cases/m1_move_heavy_rewrite`、
  `r3cases2/m3_move_rewrite_tasks_only`、`r6cases/A_delall_unrelated` / `C_pmd_rest_moved` / `D_delall_recognizing_born`、
  `r5cases/pmd_valid` / `partial_move_delete`、`r3cases2/t471c` / `t471d` —— **全绿**。
- **明写误伤面仍红**（与文档一致）：`r4cases/e12_sibling_spec_copy`（只点名 `specs/limits.md`）、
  `r3cases/m2_template_stub`、`r5cases/e12_copy`。
- **新口径带来的误伤已登记且事实成立**（真 CLI 今天绿，见复核 ③(3)）⇒ 不构成新的**未登记**行为变化。

### C 判据逐条（`§5.3` N1–N22 + `§5.1` 1–14 + 2b/2c）

「新口径」= `/tmp/r8sim.py`（`evrows=all`，即 `spec.md:62` 要求的全非 tree 行枚举）。「今天」= 未改源码的真 CLI。

| # | 构造（我的复算源） | 新口径 | 结论 |
|---|---|---|---|
| N1 | 只改 `src/**`（`r7cases/n1_src_only`） | 无候选 ⇒ 红 | ✅ |
| N2 | 改已存在归档目录里的文件（`r4cases/t577`，`touching`） | `c1=False` ⇒ 红 | ✅ |
| N3 | 往已存在归档目录新增文件（`cases/r10`） | `c1=False` ⇒ 红 | ✅ |
| N4 | 单文件 move 进已存在归档目录（`r7cases/n4_into_existing`） | 红 | ✅ |
| N5 | 删除 change 目录（`r7cases/n5_delete_change`） | 无候选 ⇒ 红 | ✅ |
| N6 | 到达件齐但零 manifest（`r3cases2/n6_exact`） | 到达 ⇒ 证据门点名 | ✅ |
| N7 | 新建 `archive/<name>/` 缺必需件（`r4cases/t541`） | `c2=False` ⇒ 不是到达 ⇒ 红 | ✅ |
| N8 | 改名已存在的归档目录（`cases/r8_rename_archived`） | `c3=False` ⇒ 红 | ✅ |
| N9 | 纯 `cp -r`（`cases/r1_copy`） | `c5=False` ⇒ 红 | ✅ |
| N10 | 复制 + 改路径（`cases/r2_copy_specrename`、`r3_copy_reportext`） | `c5=False` ⇒ 红 | ✅ |
| N11 | 复制 + 只改一处（`cases/r4_copy_onebyte`） | `c5=False` ⇒ 红 | ✅ |
| N12 | 复制 + 删一个证据文件（`r5cases/n12_del_one`） | `c5=False` ⇒ 红 | ✅ |
| N13 | `git mv` 无关文件 + 其余整份 `cp`（`cases/r16_copy_plus_add`） | `c5=False` ⇒ 红 | ✅ |
| N14 | 源是嵌套归档目录（`cases/r21_nested_source`） | 红 | ✅ |
| N15 | 混源（`cases/r5_mixed_sources`） | `c5=False` ⇒ 红 | ✅ |
| N16 | 组织型子目录（`cases/r12_org_dir`） | 非候选 ⇒ 红 | ✅ |
| N17 | `archive/notes/` 只含 `sub/`+`reviews/`（`cases/r15_org_dir_with_reviews`） | `c2=False` ⇒ 红 | ✅ |
| N18 | base 同路径是 blob（`cases/r11_base_blob`） | `c1=False` ⇒ 红 | ✅ |
| N19 | 报告挪出 `reviews/`（`r3cases/a1_report_repath`） | `c5=False` ⇒ 红 | ✅ |
| N20 | `specs` 换同名普通文件 / `tasks.md` 做成目录（`r3cases2/a3b_specs_file_pristine`、`a5_tasks_as_dir`） | `c5=False` ⇒ 红 | ✅ |
| N21 | **每份证据各加一个字节** + 重算 manifest（`r3cases/a2_all_one_byte`） | `ARRIVED=['2026-10-15-new']` ⇒ 绿 | ✅ **按设计不要求红**（明写天花板） |
| N22① | 链接指向基准树里现成 change（`r5cases/symlink_ev` / `symlink_gate` / `symlink_gate2`） | `c5=False` ⇒ 红 | ✅ |
| N22② | **悬空链接**（`r7cases/dangling_inA` / `dangling_out`） | `c5=False` ⇒ 红 | ✅ |
| N22② | **gitlink**（`r7cases/gitlink`，`probe`） | `ARRIVED=[]`（`gitlink fail-closed`）⇒ 红 | ✅（**M2 已闭合**） |
| N22② | **目标未跟踪**（自建 `p3_link_untracked`） | `ARRIVED=[]` ⇒ 红 | ✅ |
| 对照 | `alias.md → grill-review.md`（`r6cases/symlink_report_move` / `symlink_move_legit`） | `arrived=True` | ✅ **必须绿成立** |
| 对照 | 指向 `changes_root` **之外被跟踪**文件（自建 `p1` / `p4`） | `arrived=True` | ✅ **必须绿成立（本轮首次真正覆盖）** |
| 对照 | 纯 move / move+重建 manifest / 出生即归档（`cases/r6`、`r7`、`r13`） | `arrived=True` | ✅ |
| 对照 | 空文件豁免 / stub 误伤排除（`r4cases/empty13_gitkeep`、`r5cases/e11_proper`、`r3cases2/e11b`） | `arrived=True` | ✅ |
| §5.1 2b | move + 被搬文件整体重写（`r3cases/m1_move_heavy_rewrite`、`r3cases2/m3_move_rewrite_tasks_only`） | `arrived=True` | ✅ |
| §5.1 2c | 行为变化变绿侧（`r5cases/pmd_valid`、`r6cases/A_delall_unrelated` / `C_pmd_rest_moved` / `D_delall_recognizing_born`） | 绿 | ✅ |
| §5.1 2c | fail-closed 对照（`r5cases/pmd_invalid`） | `ARRIVED=[]` ⇒ 红 | ✅ |
| — | 受保护文件搬进到达目录 / 归档时改 change id（D5 / D4 侧） | — | **未实现 ⇒ 仅文本核对**（见「未验证项 2」） |

`§5.1` 第 3/7/8/9/10/11/12/13 条走的是上表同族构造；第 6/7 条（树读不出 / 基准 revision 对齐）**未复算**
（需要浅克隆与分叉后 base 前进的真仓，见「未验证项 3」）。

### D 源码核对（设计里的 `文件:行号` 断言）

**我核对到的逐条命中**（`sed -n` 打印比对）：

| 设计里的引用 | 实测 |
|---|---|
| `contract.is_archive_move` 只认 `R100` + 源在 active | ✅ `contract.py:72` `if change.status != "R100" or not change.old_path:` |
| `contract.changed_change_ids` / `archive_grant` / `change_targets` | ✅ `contract.py:85` / `:119` / `:150` |
| `contract.resolve_report_path`（`Path.resolve()` + `is_within`） | ✅ `contract.py:282`，内部 `:296-300` |
| `pathutil.is_within` | ✅ `paths.py:60`（`resolve().relative_to(...)`） |
| `hashing.sha256_tree` **跟随符号链接**（R5/R6 攻击前提） | ✅ `hashing.py:22-37`：`p.is_file()` + `entry.read_bytes()` ⇒ 链接文件按**目标字节**哈希 |
| `gitutil.changed_files` = `base...head`（三点）+ `--find-renames` | ✅ `gitutil.py:99-111` |
| `gitutil._parse_name_status` 对 `D` 把被删路径放 `path`、`old_path` 留空 | ✅ `gitutil.py:124-129` |
| `manifestcmd.resolve_change_dir` 按磁盘存在性、active 优先 | ✅ `manifestcmd.py:33-48`（`active.is_dir()` 优先，再 `pol.archive_root`） |
| `manifestcmd` **不调用** `change_targets`（design D7 / tasks 3.6 的关键事实） | ✅ `grep -n change_targets src/witnessloop/manifestcmd.py` **零命中** |
| `checkcmd._protected_writes` 用 `is_archive_move`（将被替换） | ✅ `checkcmd.py:228` / `:255` |
| `constants.HASHED_ARTIFACTS` = `tasks.md` + `specs`；`required_artifacts` 五项 | ✅ `constants.py:87-90` / `:55` |
| `tests/test_orphan_reports.py:273` 的钉绿布局 | ✅ `test_symlinked_report_is_not_an_orphan` 在 `:273`，`:283` 建 `alias.md → grill-review.md` |

**一处事实（本轮新确认，支撑 `design.md:322`）**：`git ls-tree -r` 的语义是「**不含 tree 行、含 `160000 commit` 行**」，
`design.md:322` 的订正准确（原始输出见 §复核 ③）。

### E 低危

1. **`Path.resolve()`（工作树）与 head 树混用**（R7 §E-1 的建议**未采纳**）：`spec.md:69` / `design.md:116` 明确把解析器钉成
   `Path.resolve()`（**文件系统**操作），而 (a)/(b) 的字节比对按 **head 树**。CI 里两者相等 ⇒ 无实害；
   但本地 `check` 在有未提交文件时会分叉：`p3` 这类「链接目标未提交」的构造，工作树解析**成功**、树查**失败** ⇒
   只有按树查才能得到 fail-closed。**建议 `spec.md` 钉死「内容与存在性一律按 **head 树**，`Path.resolve()` 只用于
   把链接文本规范化成仓根相对路径」**。（措辞项 2）
2. **目标解析到仓根之外**（如绝对路径 `/tmp/...`）：`spec.md:72` 的三类里没有这一类。
   实现若用 `Path(...).relative_to(root)` 会抛 `ValueError`（`check` 崩溃 ⇒ 退 1 ⇒ fail-closed，行为安全但非「受控 finding」）。
   建议补一句「目标落在仓根之外 ⇒ fail-closed」。（措辞项 3 的一部分）
3. **目录值目标**（`q2`）：`取目标文件的 blob` 对目录不适用。文本经「与 `cp` 进来同结论」可定案为**折叠子树**（= 红），
   但字面读法允许「无 blob ⇒ 跳过」（= 绿）。与 N22① 的 `specs` 字样直接相关 ⇒ 值得钉死。（措辞项 3）
4. `--evrows=blob`（只枚举 blob 行）在我全部构造上与 `evrows=all` **只差 gitlink 一行**：
   `r7cases/gitlink` 在 blob 枚举下 `arrived=True`（绿）——这**复现了 R7 的 M2 形状**，说明该订正确实承重。

---

## 未验证项

1. **到达判定那一半仍是「按文本逐字转写」的模拟器**（本 change 未实现）。最敏感的三处分歧已写进 §复核 ③/§E：
   ① 解析器用 `Path.resolve()` 还是纯词法 `normpath`；② 目录值目标怎么处理；③ `(b)` 的判定对象。
   除这三点外，各读法在我全部 86 个构造上同结论。
2. **D4 排除键 / D5 保护写豁免**：今天的 CLI 是旧实现（`archive_grant` + `is_archive_move`），
   **无法**用真 CLI 验证新口径 ⇒ 本轮对 `§5.1` 2b/2c、`§5.2` 的 5 条改写测试、`§5.3` 末两行只做**文本核对**。
3. 浅克隆失败面、merge commit 形态、自定义 `review_manifest_glob`、多段 `required_artifacts` 的端到端：无新证据（沿用前轮）。
4. **硬链接借内容**、gitlink 的**子模块内容**攻击：未构造（后者需 `gate.yml` 开 `submodules: true`；
   本仓 `gate.yml` 只有 `actions/checkout@v4`、无该键 ⇒ 子模块内容不会物化）。
5. 接入方真实提交（`R068/R069/R070/R090`）**不可复算**（本仓从未归档过 change）。
6. Windows 反斜杠 / `core.symlinks=false` 检出的链接：只走代码路径，**未单独构造**（与 R7 同）。

---

## 必须修改项

**无。**

R7 的两条必须项都已落库且经我独立复算成立：
- **M1**（逃出 `A` 的拒绝面未登记 + Scenario 全称断言）：登记进了 `spec.md:105-106`（误伤面）、
  `spec.md:354-356`（有意的行为变化 3）、`design.md:206-207`（已知边界）、`design.md:386`（R7 行），
  Scenario 限定补在 `spec.md:320-326`；且行为变化本身**事实成立**（真 CLI 今天绿，见 §复核 ③(3)）。
  ⚠️ 只有 `§5.2` 那一半没落（见 §措辞项 6）。
- **M2**（gitlink 与 `Ev(A)`「文件」枚举不自洽）：`spec.md:62-63` 明写「枚举 SHALL 覆盖全部非 tree 行」，
  `design.md:322` / `tasks.md:153` 订正了命令描述；我的 `r7cases/gitlink` 复算 `ARRIVED=[]`（红）⇒ 必须红**可满足**。

---

## 措辞项

（**均不影响任何用例的判红判绿**；1–3 建议下一轮顺手改掉。）

1. **`(b)` 的判定对象没钉死**（措辞项里最有实质的一条）：`spec.md:65` 说符号链接「参与 **(a)/(b) 比对**」，
   而 `spec.md:71` 只说「`A` 之外 ⇒ 按该目标路径在 head 树里的 blob 比对（与 `cp` 进来同结论）」——
   `(b)`（「是本次改名记录的落点」）到底看**链接自身的路径**还是**解析目标路径**，字面两可。
   我的自建 `q1_link_launder`（先把受害者的报告在它自己的归档目录内**原地改名**，再让 `A/tasks.md` 链接过去）
   在两种读法下**结论相反**：按「(b) 看链接自身路径」= 红；按「(b) 看目标路径」= 绿。
   `design.md:119` 的「字节落在 `<changes_root>/**` 就命中 (a)、**否则放行**」实际把 `A` 之外的情形定成了 **(a) 单独**（= 红），
   所以**设计意图是安全的**，但这句话与 `spec.md:65` 的「(a)/(b) 比对」并列时容易被实现者读成「(b) 也适用且以目标为对象」。
   **建议补一句**：「对 `A` 之外的链接，`(b)` 的判定对象是**链接自身所在路径**（等价于『把目标内容 `cp` 到该路径』）；
   目标路径本身是否为改名落点 SHALL NOT 参与判定。」
2. **`Path.resolve()` 与 head 树的口径**：`spec.md:69` / `design.md:116` 把解析器钉成 `Path.resolve()`（文件系统），
   而比对按 head 树（见 §E-1）。建议钉死「存在性与字节一律按 **head 树**；`Path.resolve()` 只用于路径规范化」，
   并补「目标解析到**仓根之外** ⇒ fail-closed」（现文三类 fail-closed 里没有这一类，见 §E-2）。
3. **目录值目标 + gitlink 作用域**：① 「按目标**文件**的 blob 比对」对**目录**目标不适用
   （N22① 明写 `specs`，而 `specs` 是目录）——建议改成「目标是目录 ⇒ 其下全部文件逐个比对（等价于把该目录 `cp` 进来）」；
   ② gitlink 作用域在 `spec.md:63` / `tasks.md:127`（「**`<A>` 下**（或 `Ev(A)` 里）」）与 `design.md:120` / `:206`（只 `Ev(A)`）**不一致**，
   建议统一（取宽的一侧，即「`<A>` 下任何 `160000` 条目 ⇒ 不授予」）。
4. **`design.md:384`（R7 行）仍写「必须**每一份**被复制的证据文件都**重写**（或改成 `git mv`）」**——
   与 `§D1 第 5 条` 的**能力天花板**（`design.md:171-177`：各加**一个字节**即可绕过）措辞冲突，
   这正是 **R7 的措辞项 1**（要求改成「每份**至少动一个字节**」），本轮**未落库**。
5. **`tasks.md:155`** 仍写「`-r` = 其下**全部 blob**」——即 **R7 的措辞项 6 的 tasks 半边**（未落库）。
   同段的 `tasks.md:153` 已写对（「须同时覆盖 blob 行与 `160000 commit` 行」），但括注仍是旧描述。
6. **`design.md §5.2` 未加登记行**（作者的 commit message 与 `tasks.md:39` 都声称「登记进 …『已知边界』**与 §5.2**」，
   而 §5.2（`design.md:432-474`）**零命中** `链接/符号/gitlink`）。建议补一行：
   「含未跟踪 / 悬空链接 / gitlink 的到达目录在改动前判绿、本 change 判红」。
7. **`tasks.md:40` 的「7 条措辞项已落库」与 `tasks.md:39` 的「登记进…§5.2」两句计数/范围不准**：
   实际未落的是 R7 措辞 1（→ 本表 4）与措辞 6 的 tasks 半边（→ 本表 5），§5.2 未改（→ 6）。
8. **`design.md:500`（§5.3 N22 行）仍写「逃出 `A` 的链接直接 fail-closed」**——R6 旧口径的残留，
   与 `design.md:118-119` / `spec.md:71` 冲突（可被我的 `p1` 构造证伪：逃出 `A` 且目标被跟踪 ⇒ 绿）。
   建议改成「逃出 `A` 到**被跟踪**目标 ⇒ 按目标 blob 比对；仅在**未跟踪 / 悬空 / gitlink** 时 fail-closed」。
9. **`spec.md:320-326` 的 Scenario 限定 ②** 只举了两类内容来源边界（符号链接 / gitlink / 悬空；`changes_root` 外另有副本），
   而第 5 条**其它**命中（如原样复制兄弟 change 的 `specs/**`：active ⇒ 绿、archive ⇒ 红）同样造成位置差异。
   建议把 ② 的主语明确成「**第 5 条整体**（以下为举例）」以免被读成穷举。
10. **`spec.md:96-99` 的「完全旁路」段** 写「与是 `git mv` 还是普通 `cp` 进来**无关**」——
   在新的符号链接口径下还应算上 `ln -s`（链接到 `changes_root` 之外被跟踪文件 ⇒ (a) 同样豁免）。建议补半句。

---

## 收敛结论

**已收敛，附带 10 条措辞项（无必须修改项）。**

判据 = 「本轮没有新的可证伪项 **且** 所有『必须修改项』都已落库」。两条都满足：

- **R7 的两条必须项都已落库**，并经我独立复算成立（M1 的四处登记中三处已落 + 行为变化事实成立；
  M2 的枚举口径订正到位，`r7cases/gitlink` 复算为红）。
- **没有新的可证伪项**：我在 80 个既有构造 + 6 个自建构造（含**首次真正覆盖**的「逃出 `A` 但目标被跟踪」正向半边、
  目录值目标、未跟踪目标、改名落点洗白）上复算，**没有找到能翻绿的绕过**，也没有出现必须绿被误伤。
  本轮的全部发现都落在**措辞 / 登记 / 口径钉死**这一层：它们**不改变判据对任何用例的判红判绿**
  （最接近语义的是措辞项 1 的 `(b)` 判定对象，但 `design.md:119` 的「否则放行」已把 `A` 之外的情形定成 (a) 单独 ⇒ 设计意图为红）。
- **必须修复项：无**（措辞项 1/2/3 建议在实现前顺手改掉，因为它们决定实现者怎么写那一行判据；
  6/7 影响「已落库」这一claim的准确性）。

**这一轮值得记进下一轮上下文的结论**（避免误判）：
① **R7 的修复在两侧都成立**，包括 R7 从未真正测过的正向半边（`p1` / `p4`）；
② **R7 的 4 个「逃出 `A`」构造全是悬空链接**，R7 报告里「指向仓外被跟踪文件」的语义并未被那批构造覆盖；
③ `git ls-tree -r` 含 `160000 commit` 行已由我独立复现，M2 的订正承重且正确。
