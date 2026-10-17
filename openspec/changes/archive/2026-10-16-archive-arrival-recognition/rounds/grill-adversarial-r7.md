# 对抗轮 R7（独立零记忆验证者）—— `archive-arrival-recognition`

> **结论摘要：不收敛。** R6 的符号链接修复（**按解析后的内容参与 (a)/(b) 比对 + 只对「逃出 `A` / 悬空 /
> gitlink」fail-closed**）在**它声称要保住的 in-A 一侧确实成立**：R6 的两个合法构造今天真 CLI 仍绿、
> 新口径下仍 `arrived=True`；R5 的攻击构造与我自己新造的 6 类变体（指向 A 内非证据文件的偷字节、链接套链接、
> `..` 归一化、绝对路径、悬空、指向目录）全部按预期判红/判绿，**本轮未能绕过判据 5 的符号链接口径**。
> 但有 **2 条新的、可复算的、影响判红判绿的证伪项**，且其中一条是 **R6 已明写而作者未落库的必须项**：
> 1. **M1**：R6 要求「给 `spec.md` 的『同一内容两种位置结论一致』Scenario 补一行限定」，**未落**——
>    该 Scenario（`spec.md:313-316`）仍是**无保留的全称断言**，我用 `/tmp/r7cases/escape_doc` 实测证伪
>    （同一份合法内容：active 位置今天真 CLI 绿 / 归档位置新口径红）；且「逃出 `A` ⇒ 不授予」这条拒绝面
>    **没有被登记**（`spec.md` 误伤面 / 有意的行为变化、`design.md §D1 已知边界`、`§5.2` 回归面都没有它）。
> 2. **M2**：「gitlink ⇒ 红」（`tasks.md:120`、`§5.3 N22 ②`）与 `Ev(A)` 的枚举口径**不自洽**：
>    `spec.md:60` 写「`<A>/reviews/**` 下的全部**文件**」、`tasks.md:141` / `design.md:317` 把
>    `git ls-tree -r` 描述成「只列 blob 行」，而**实测它还列 `160000 commit` 行** ⇒ 按「文件/blob」枚举实现时
>    `reviews/` 下的 gitlink 永不进 `Ev(A)` ⇒ 那条必须红不成立（我的 `gitlink` 探针：blob 枚举 ⇒ `arrived=True`）。
> 另有 **7 条措辞项**（含 R6 措辞 4/10/11/12 未落）。

---

## Reviewer

**零记忆声明**：本对话不携带该 change 的任何历史。R1–R6（`grill-design.md` / `grill-adversarial*.md`）的结论
**只当待复核的声明**；design / spec / tasks 里的「实测」「`文件:行号`」一律当**待验证断言**。
判据模拟器 `/tmp/r7sim.py` 由我**从零写成**（只按 `design.md §2 D1` + `spec.md` 当前正文转写，只读 git 树，
**未**沿用 `/tmp/r3sim.py` / `/tmp/r4sim.py` / `/tmp/r5sim.py` / `/tmp/r6sim.py`，也没读它们的判据逻辑）。
本轮只写 `reviews/` 下这一个文件；未改 `src/` / `tests/` / 任何 change 文档；未 commit、未 push。

**HEAD**：`806794bb66fd1090df530e8866a69a1b72ce97e0`（`archive-arrival-recognition：R5 记录行与 R6 口径对齐、去掉 tasks 重复行`）。

**读过的**：`design.md`（706 行）/ `specs/archive-awareness/spec.md`（354 行）/ `tasks.md` / `proposal.md`；
源码 `contract.py` / `checkcmd.py` / `gitutil.py` / `policy.py` / `constants.py` / `paths.py` / `hashing.py` /
`manifestcmd.py`；`tests/test_archive_awareness.py`（行号逐条核对）、`tests/test_orphan_reports.py`；
R6 报告全文。

**跑过的**：
- `/tmp/r7sim.py` 在**全部既有构造**上复算：`/tmp/cases/*`(18) + `/tmp/r3cases/*`(8) + `/tmp/r3cases2/*`(18)
  + `/tmp/r4cases/*`(11，`t577` 用 `touching`) + `/tmp/r5cases/*`(10，`pmd_invalid`/`symlink_gate` 用 `feature2`)
  + `/tmp/r6cases/*`(7)；
- **自建 12 个新构造**（`/tmp/r7cases/*`，脚本 `/tmp/r7build.sh` / `r7build2.sh` / `r7build3.sh`）：
  `ctrl_regular`、`dangling_out`、`dangling_inA`、`chain_escape`、`dir_link`、`inA_link_to_stolen`、`gitlink`、
  `escape_doc`、`escape_doc_regular`、`abs_link`、`n1_src_only`、`n4_into_existing`、`n5_delete_change`；
- **今天的真 CLI**（`.venv/bin/python -m witnessloop check`，未改一行源码）在全部新构造上取原始输出；
- `pytest -q` 基线：**601 passed in 46.63s**（exit 0）。

---

## R6 修复复核

### 修复 ①（符号链接口径：按解析后内容比对；只对逃出 `A` / 悬空 / gitlink fail-closed）

**成立（在它声称的射程内）**。三条硬证据：

（1）**R6 的两个合法构造今天真 CLI 判绿，新口径下仍授予**：

```bash
$ cd /tmp/r6cases/symlink_report_move && python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，11 个变更文件，1 个 change 目录
  change：2026-10-15-z（归档）
check：通过 ✓                      # exit 0
$ cd /tmp/r6cases/symlink_move_legit && ...   # 同样 check：通过 ✓
$ python3 /tmp/r7sim.py /tmp/r6cases/symlink_report_move main feature -v
  cand 2026-10-15-z   c1=True c2=True c3=True c4=True c5=True srcs=['z'] arrived=True
$ python3 /tmp/r7sim.py /tmp/r6cases/symlink_move_legit main feature --evrows=all
  ARRIVED = ['2026-10-15-z']
```

（2）**R5 的攻击构造被关掉**：

```bash
$ python3 /tmp/r7sim.py /tmp/r5cases/symlink_ev main feature -v
  cand 2026-10-15-new  c1=True c2=True c3=True c4=True c5=False srcs=[] arrived=False
        ✗ …/2026-10-15-new/specs（符号链接 解析到 …/archive/2026-09-30-old/specs（逃出 A） ⇒ fail-closed）
        ✗ …/2026-10-15-new/tasks.md（符号链接 解析到 …/archive/2026-09-30-old/tasks.md（逃出 A） ⇒ fail-closed）
        ✗ …/2026-10-15-new/reviews/link.md（符号链接 解析到 …/archive/2026-09-30-old/reviews/grill-review.md（逃出 A） ⇒ fail-closed）
$ python3 /tmp/r7sim.py /tmp/r6cases/symlink_archive_move main feature -v   # 悬空 + 逃出 ⇒ 同样红
```

（3）**我自己新造的 6 类变体**（全部「今天真 CLI 绿」，见下节 §C 的 `today_rc=0`）：

| 变体（构造） | 新口径 | 是否符合设计意图 |
|---|---|---|
| `inA_link_to_stolen`：链接指向 A 内**非证据**文件 `reviews/notes.bin`，而它是 base 里现成 `tasks.md` 的逐字节复制 | **红**（目标并入 `Ev(A)` ⇒ blob 在基准树 `changes_root/**`） | ✅ 「把目标路径并入 `Ev(A)`」这条递归确实承重 |
| `chain_escape`：`link.txt → link2.txt → ../../../docs/notes.md`（两级链逃出） | **红**（两跳都点名） | ✅ 「递归到不动点」 |
| `dir_link`：`link.txt → ../specs`（指向 A 内目录） | **绿** | ✅ 不误伤 |
| `dangling_inA` / `dangling_out`：悬空链接（A 内 / A 外） | **红** | ✅ 与 `spec.md:65` 一致 |
| `abs_link`：`link.txt → /tmp/…/docs/notes.md`（绝对路径） | **红** | ✅ |

⇒ **本轮未能绕过判据 5 的符号链接口径**（新绕过 0 条）。我对 `--follow=onehop`（只跳一跳）、
`--bmode=blob`（(b) 按 blob 而非路径）、`--link-also`（链接自身也须满足 (a)/(b)）三种写法分歧各跑了一遍，
**对上述全部构造结论相同**（唯一分歧见 §E-1「未跟踪目标」）。

### 修复 ②（D4 措辞订正 + 行为变化登记 + 2c 用例）

**文本层面已落库**：`design.md:249-264`（「该推论为假」+ R5 构造 + 「有意的行为变化，已登记」+ fail-closed 对照）、
`design.md:381-393`（2b/2c）、`spec.md:334-343`（行为变化 2 + 「对照仍须红」）逐条对上。
⚠️ **但 D4/D5 是未实现的部分**，今天的真 CLI 仍跑旧实现 ⇒ 我**无法**用真 CLI 验证 2c 的红/绿两侧
（记入「未验证项 2」）。

### 修复 ③（R6 要求里**未落**的一条）

R6 的「要求（二选一，或并取）」段末尾明写：

> 「并给 `spec.md:306-309` 的 Scenario 补上与 `D2` 同等的一行限定（**该 Scenario 现为无保留的全称断言**）。」

现文 `spec.md:313-316`：

```
### Scenario: 同一内容两种位置结论一致
- **Given** 同一份 change 内容（件齐 + 三份 manifest + 报告），一份在 `changes/<id>/`、一份在 `archive/<name>/`
- **When** 分别运行 `check`
- **Then** 两者的判绿判红结论相同
```

**一行限定也没有加**（对比：`spec.md:297-301` 的对称性不变量正文、`design.md:222-225` 的 D2 正文都在 R2
加过同类限定）。而这条 Scenario **今天仍可被证伪** ⇒ 见下面的 M1（本轮的第一条必须修改项）。

---

## 独立证伪

### A 绕过（尝试过、**未成功**的）

| # | 构造 | 结果 |
|---|---|---|
| A1 | 链接指向 A 内**非证据**文件（偷来的字节） | **拒** ✅（`inA_link_to_stolen`：`c5=False`，点名 `reviews/notes.bin`） |
| A2 | **链接套链接**（2 跳）逃出 A | **拒** ✅（`chain_escape`） |
| A3 | `..` 归一化逃出（`../../../docs/notes.md`） | **拒** ✅（`escape_doc`） |
| A4 | **绝对路径**链接 | **拒** ✅（`abs_link`） |
| A5 | 让 (b) 由「链接自身是改名落点」成立（R6 的对照构造） | 绿 —— **这是设计意图**（`symlink_report_move`） |
| A6 | 让 (b) 按 blob 而非路径匹配（`--bmode=blob`） | 结论不变（构造上无差异） |
| A7 | 硬链接借内容 | 未构造（git 里就是普通 blob ⇒ (a) 命中；与 R5 同结论）——记「未验证项 4」 |

**结论：判据 5 的符号链接口径本轮**没有**被绕过。若能绕过，最可能的形状是「让被偷内容的 blob 同时是
本次改名落点」，那需要一条**从非 archive 源搬进 A** 的改名记录 ⇒ 由判据 3（源在 `archive/**`）或
判据 4（名字须认得每一个源）拦下：我用 `/tmp/r6cases/B_rename_unrecognized`（`R100 x/notes.md → …-misc/notes.md`，
`c4=False`）与 `/tmp/r7cases/n4_into_existing`（`c1=False`）复算，两条都拒。

### B 假阴性 / 未登记的行为变化（**新证伪**）

#### B1（→ 必须修改项 **M1**）「逃出 `A` 的链接 ⇒ fail-closed」把**合法构造**由绿判红，且未登记

**最小复现**（我从零构造，base/head 都真 CLI 跑过）：

```bash
$ bash /tmp/r7build2.sh        # 造 /tmp/r7cases/escape_doc
$ cd /tmp/r7cases/escape_doc
$ python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，11 个变更文件，1 个 change 目录
  change：2026-10-15-z（归档）
check：通过 ✓                  # ← 今天 exit 0（绿）
$ python3 /tmp/r7sim.py /tmp/r7cases/escape_doc main feature --evrows=all
  cand 2026-10-15-z  c1=True c2=True c3=True c4=True c5=False srcs=['z'] arrived=False
        ✗ …/2026-10-15-z/reviews/link.txt（符号链接 解析到 openspec/docs/notes.md（逃出 A） ⇒ fail-closed）
  ARRIVED = []                 # ← 新口径红
```

**隔离变量**：同一脚本造的 `escape_doc_regular`（**唯一差别**：`link.txt` 是普通文件而不是符号链接）：
今天真 CLI `check：通过 ✓`，新口径 `ARRIVED = ['2026-10-15-z']`（**绿**）。另有 `ctrl_regular`
（在 move 提交里新加一个普通文件）同样「今天绿 / 新绿」。⇒ 红**只**由「它是符号链接」这一件事引起。

**为什么这条比「意图内的拒绝面」更值得登记**：
1. **未登记**：`spec.md:95-99`（误伤面）、`spec.md:334-343`（有意的行为变化）、`design.md:186-210`
   （`§D1 已知边界`）、`§5.2`（回归面）**四处都没有**「逃出 `A` 的链接」。接入方读任何一节都推不出。
2. **使一条无保留全称断言失守**（这正是 R6 要求补限定而**未落**的那一条）：`spec.md:313-316`
   「同一内容两种位置结论一致」——同一份内容放在 `changes/<id>/`（active ⇒ 判据 5 不适用 ⇒ 绿）
   与 `archive/<name>/`（新口径 ⇒ 红），结论**不同**。
3. **比判据自己的威胁模型更严**：`spec.md:91-94` 把「`changes_root` 之外的现成证据副本」明写为
   **已接受的完全旁路**（「分句 (a) 单独即豁免，**与是 `git mv` 还是普通 `cp` 进来无关**」）。
   于是在同一份**仓外字节**上：`cp` 进来 ⇒ 放行（登记为已知绕过），`ln -s` 进来 ⇒ 拒。
   即这条 fail-closed **没有增加任何安全性**（那些字节本来就被 (a) 豁免），却新增了一个拒绝面。
4. 这**不是**「规则没写」——规则写了（`design.md:120` / `spec.md:65`）；问题是 R6 要求的
   「残留后果登记 + Scenario 限定」这一半**没做**，而 R6 判定该类后果为**必须**（R6 报告 `:288-320`）。

**修法（二选一或并取，都能一轮收官）**：
- **(a) 收窄**：把 fail-closed 限定为「**解析后落在 `<changes_root>` 之内**、但逃出 `A`」（= R5/R6 攻击的形状：
  链接指向 `<changes_root>/archive/…` 里的现成证据）。R5 的两个攻击构造（`symlink_ev` / `symlink_archive_move`）
  的目标都落在 `changes_root` 之内 ⇒ **仍然全红**（我已复算）；而指向仓内无关文档 / 仓外的链接不再误伤。
- **(b) 登记**：在 `spec.md` 的「有意的行为变化」加一条（「证据里含**逃出 `A` 的链接 / 悬空链接 / gitlink**
  的到达目录不再被授予资格；**合法整目录 move 亦然（今天绿）**」）+ `spec.md:95-99` 误伤面补一行 +
  `design.md §D1 已知边界` 补一行 + `§5.2` 回归面注明 + **给 `spec.md:313-316` 的 Scenario 补一行限定**
  （与 D2 同款「本条不覆盖判据 5 明写的拒绝面」）+ 补一条钉住该行为的用例。

同类构造（都是「今天绿 / 新红」）：`dangling_out`（悬空且逃出）、`dangling_inA`（悬空但在 A 内）、
`abs_link`（绝对路径）。⚠️ 顺带一条**指错目标的链接**（写错文件名）会让整份合法证据 fail-closed ——
这与本项同族，连同上面的登记一起写。

#### B2（→ 必须修改项 **M2**）gitlink 规则与 `Ev(A)` 的枚举口径不自洽 ⇒ `N22 ②` 的必须红不成立

`tasks.md:120`（2.9 ⑬）与 `§5.3 N22 ②` 都要求「**悬空链接 / gitlink（`160000`）⇒ 红**」。
但 `Ev(A)` 的枚举口径写的是**文件**：`spec.md:60` 第 3 部分 = 「`<A>/reviews/**` 下的**全部文件**」，
第 1 部分 = 「是目录 ⇒ **其下全部文件**」；而 `design.md:317` 与 `tasks.md:141` 又把命令语义描述成
「`git ls-tree -r` = 只列 **blob** 行」。**实测该描述不准确**：

```bash
$ cd /tmp/r7cases/gitlink && git ls-tree -r HEAD -- openspec/changes/archive/2026-10-15-z/reviews/
100644 blob 61780798228d…	…/reviews/b.md
100644 blob 5fa534db247a…	…/reviews/building.manifest.json
100644 blob 31334094c7d1…	…/reviews/ga.md
100644 blob 107804909820…	…/reviews/grill-adversarial.manifest.json
100644 blob e86af71c35b1…	…/reviews/grill-review.md
100644 blob e5bd4d30abae…	…/reviews/grill.manifest.json
160000 commit 2f781bdcc1bf972c9994c2ddb72dd0cbb625e382	…/reviews/sub      # ← gitlink 行也在
```

⇒ 按「文件 / blob」枚举实现（这是对 `spec.md:60`「全部**文件**」+ `tasks.md:141`「只列 blob 行」的自然读法），
`reviews/` 下（以及 `specs/` 之下的）gitlink **永远不进 `Ev(A)`** ⇒ 永不评估 ⇒ **不红**：

```bash
$ cd /tmp/r7cases/gitlink && python -m witnessloop check --root . --base main --head HEAD   # 今天
check：通过 ✓                       # exit 0（今天没有任何东西读它）
$ python3 /tmp/r7sim.py /tmp/r7cases/gitlink main HEAD            # blob 枚举（我的默认读法）
  cand 2026-10-15-z   c1=True c2=True c3=True c4=True c5=True srcs=['z'] arrived=True
  ARRIVED = ['2026-10-15-z']        # ← 绿，与 tasks.md:120「gitlink ⇒ 红」矛盾
$ python3 /tmp/r7sim.py /tmp/r7cases/gitlink main HEAD --evrows=all   # 枚举全部 ls-tree -r 行
        ✗ …/2026-10-15-z/reviews/sub（gitlink 160000 ⇒ fail-closed）
  ARRIVED = []
```

**性质**：这不是「实现 bug」，是**文本内部不一致**——同一份设计里，一处要求「gitlink ⇒ 红」，
另一处把 gitlink 排除在枚举之外。它决定一条**明写的必须红用例**能否成立 ⇒ 影响判红判绿（尽管
gitlink 的现实攻击面窄：本仓 `gate.yml:40` 只有 `actions/checkout@v4`、**没有** `submodules: true`，
子模块内容不会在 CI 里物化）。
**修法**：`spec.md` 明写「`Ev(A)` 的枚举 SHALL 含**非 blob 条目**（`160000`）」，或另立一条
「`<A>` 下任何 gitlink 条目 ⇒ 不授予（与是否落在 `Ev(A)` 无关）」；并订正 `design.md:317` /
`tasks.md:141` 的命令描述（「不含 **tree** 行」≠「只列 blob 行」）。

### C 判据逐条（`§5.3` N1–N22 + `§5.1` 1–14）

**新口径 = `/tmp/r7sim.py`（`evrows=all`，即最宽枚举；blob 枚举的分歧只影响 §C 的 N22②/gitlink 一行）；
「今天」= 未改源码的真 CLI。**

| # | 构造（我的复算源） | 今天 | 新口径 | 结论 |
|---|---|---|---|---|
| N1 | 只改 `src/**`（`/tmp/r7cases/n1_src_only`） | 红(1) | 无候选 ⇒ 红 | ✅ |
| N2 | 改已存在归档目录里的文件（`r4cases/t577`，`touching`） | 红 | `c1=False` ⇒ 红 | ✅ |
| N3 | 往已存在归档目录新增文件（`cases/r10`） | 红 | `c1=False` ⇒ 红 | ✅ |
| N4 | 单文件 move 进**已存在**的归档目录（`/tmp/r7cases/n4_into_existing`） | 红(1) | `c1=False` ⇒ 红 | ✅ |
| N5 | 删除 change 目录（`/tmp/r7cases/n5_delete_change`） | 红 | 无候选 ⇒ 红 | ✅ |
| N6 | 到达件齐但零 manifest（`r3cases2/n6_exact`、`r4cases/t541_*`） | 红 | 到达 ⇒ 由证据门点名 | ✅（到达判定非红因） |
| N7 | 新建 `archive/<name>/` 缺必需件（真 CLI 侧同 N6 反例） | 红 | `c2=False` ⇒ 红 | ✅ |
| N8 | 改名已存在的归档目录（`cases/r8_rename_archived`） | 红 | `c3=False`（+`c5`）⇒ 红 | ✅ |
| N9 | 纯 `cp -r`（`cases/r1_copy`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N10 | 复制 + 改路径（`cases/r2_copy_specrename`、`r3_copy_reportext`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N11 | 复制 + 只改一处（`cases/r4_copy_onebyte`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N12 | 复制 + 删一个证据文件（`r5cases/n12_del_one`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N13 | `git mv` 无关文件 + 其余整份 `cp`（`cases/r16_copy_plus_add`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N14 | 源是嵌套归档目录（`cases/r21_nested_source`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N15 | 混源（`cases/r5_mixed_sources`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N16 | 组织型子目录 `archive/2026/…`（`cases/r12_org_dir`） | 红 | 非候选 ⇒ 「没有任何 change 目录」 | ✅ |
| N17 | `archive/notes/` 只含 `sub/`+`reviews/`（`cases/r15_org_dir_with_reviews`） | 红 | `c2=False` ⇒ 非候选 | ✅ |
| N18 | base 同路径是 blob（`cases/r11_base_blob`） | 红 | `c1=False` ⇒ 红 | ✅ |
| N19 | 报告挪出 `reviews/`（`r3cases/a1_report_repath`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N20 | `specs` 换成同名普通文件 / `tasks.md` 做成目录（`r3cases2/a3b`、`a5_tasks_as_dir`） | 红 | `c5=False` ⇒ 红 | ✅ |
| N21 | **每份证据各加一个字节** + 重算 manifest（`r3cases/a2_all_one_byte`） | 绿 | `arrived=True` | ✅ **按设计不要求红**（明写天花板） |
| N22① | 链接指向基准树里现成 change（`r5cases/symlink_ev`） | 红(无 change 目录) | `c5=False` ⇒ 红 | ✅ |
| N22② | **悬空链接**（`/tmp/r7cases/dangling_inA`、`dangling_out`） | 绿 | `c5=False` ⇒ 红 | ✅ |
| N22② | **gitlink**（`/tmp/r7cases/gitlink`） | 绿 | **blob 枚举 ⇒ 绿（矛盾）** / 全行枚举 ⇒ 红 | ⚠️ **M2** |
| 对照 | `reviews/alias.md → reviews/grill-review.md`（`r6cases/symlink_report_move`、`symlink_move_legit`） | 绿 | `arrived=True` | ✅ **必须绿成立** |
| 对照 | 纯 move（`cases/r6_legit_move`）、move+重建 manifest（`r7_move_rebuild`）、出生即归档（`r13_born_archived`） | 绿 | `arrived=True` | ✅ |
| 对照 | 空文件豁免（`r4cases/empty13_gitkeep`）、`design`/`proposal` stub（`r5cases/e11_proper`） | 绿 | `arrived=True` | ✅ |
| 对照 | 明写误伤面：原样复制兄弟 change 的 `specs/**`（`r4cases/e12_sibling_spec_copy`） | 红 | `c5=False`，只点名该文件 | ✅（与文档一致） |
| — | 受保护文件搬进到达目录 / 归档时改 change id（D5/D4 侧） | — | **未实现 ⇒ 仅文本核对** | 见「未验证项 2」 |

`§5.1` 第 3/7/8/9/10/11/12/13 条走的是上面同族构造（组织型子目录 / base blob / 内容来源 / 空文件）；
第 7 条（基准 revision 与 diff 成员同源）与第 6 条（树读不出来 ⇒ fail-closed）**未复算**
（需要分叉后 base 前进 / 浅克隆，记「未验证项 3」）。

### D 源码核对（设计里的 `文件:行号` 断言）

**逐条命中**（我 `sed -n` 打出来比对）：

| 设计里的引用 | 实测 |
|---|---|
| `contract.is_archive_move`（`:65`）⇒ `if change.status != "R100" or not change.old_path` | ✅ `contract.py:65` 起，`:72` 为 R100 判断 |
| `contract.changed_change_ids`（`:85`）/ `archived_sources`（`:97`） | ✅ |
| `contract.archive_grant`（`:119`） | ✅ |
| `checkcmd._protected_writes`（`:228`）/ `is_archive_move` 分支（`:255`） | ✅ |
| `checkcmd.py:105-119` 的 stage 硬门由 `code_hits` 触发 | ✅ `:105` = `if code_hits:` |
| `gitutil.changed_files`（`:99`）/ `--find-renames`（`:105`）/ `base...head`（三点） | ✅ |
| `gitutil._parse_name_status`（`:114-130`）对 `D` 把被删路径放 `path` | ✅ |
| `policy.stale_exempt_paths`（`:77`）、末项 `archive/**` | ✅ |
| `manifestcmd.resolve_change_dir`（`:33-48`）按磁盘存在性、active 优先 | ✅ `:33` 起 |
| `manifestcmd.py:136-142` 报告须落 `reviews/` | ✅ `:136` 起 |
| `manifestcmd.py:146-153` 每次从磁盘重算哈希 | ✅ `:146` 起 |
| `manifestcmd.py:201` 写 `<label>/reviews/<stage>.manifest.json` | ✅ |
| `contract.py:9`「hash 绑定…**不防伪造**」 | ✅ 模块 docstring |
| `tests/test_orphan_reports.py:273` `test_symlinked_report_is_not_an_orphan` | ✅ 函数就在 `:273` |
| `tests/test_archive_awareness.py` 的 `:49/:87/:101/:109/:134/:274/:378/:471/:494/:541/:577/:600/:621` | ✅ **13 处全部命中**（函数名与设计描述一致） |

**一处事实不准**（→ 并入 M2）：`design.md:317` / `tasks.md:141` 把 `git ls-tree -r` 写成「只列 **blob** 行」。
实测它还列 `160000 commit`（gitlink）行（原始输出见 §B2）。**准确的措辞是「不含 tree 行」**。

**一条源码级确认**（支撑 R5/R6 的整个方向）：`hashing.py:23-24` 的 `sha256_tree` 用 `p.is_file()` /
`p.rglob(...)`——**跟随符号链接** ⇒ 证据门读的确实是「解析后的内容」⇒ R5 的攻击前提成立、
R6 选「按解析后内容比对」是正确方向。

### E 低危

1. **「未被 git 跟踪的目标」在两种口径下分歧**（低危）：`dangling_inA` 里我把 `reviews/notes.md`
   写进工作树但**不提交**，链接就解析到了真实文件。树口径（`Ev(A)` 按 head 树）⇒ 仍算「悬空 ⇒ 红」；
   工作树口径（`Path.resolve`）⇒ 目标内容是新的 ⇒ (a) 成立 ⇒ 绿。CI 里 worktree == head ⇒ 无实害，
   但两套口径会在**本地 `check`** 上分叉。建议 `spec.md` 钉死「`Ev(A)` 与链接解析**都按 head 树**」。
2. **「悬空但在 A 内」也判红**（`dangling_inA`）：这是 `spec.md:65` 明写的，但它的现实形态是
   「链接写错了文件名 / 目标被删」⇒ 一整份合法证据 fail-closed 且 finding 只说「悬空」。
   与 B1 同族，登记时一并说明。
3. **`--bmode=blob`（(b) 按 blob 匹配）** 与 `--bmode=path` 在我全部构造上结论相同 ⇒ 该口径分歧
   目前**不可利用**（但仍建议 spec 把 (b) 钉成「记录的 `new_path`」这一路径口径，因为
   `spec.md:50` 已这么写，而 `design.md:97` 也是）。——两处文本一致，仅实现期别漂。
4. `--link-also`（链接自身也须满足 (a)/(b)）与默认读法结论相同：`symlink_report_move` 的 `alias.md`
   自身也是 `R100` 落点 ⇒ 两种读法都绿。⇒ 该分歧不可利用。

---

## 未验证项

1. **到达判定那一半仍是「按文本逐字转写」的模拟器**（本 change 未实现）。最敏感的两处分歧：
   ① `Ev(A)` 枚举是否含**非 blob 条目**（M2 就是它）；② 链接解析用 `Path.resolve`/`posixpath.normpath`
   还是字符串前缀检查（我用词法 `normpath` 后再比前缀；若实现是「先比前缀再归一化」，`A/sub/../../../…`
   会漏 —— 建议 spec 钉死解析器，见「措辞项 5」）。除「未跟踪目标」（§E-1）外，三种读法在我全部构造上同结论。
2. **D4 排除键 / D5 保护写豁免**：今天的 CLI 是旧实现（`archive_grant` + `is_archive_move`），
   **无法**用真 CLI 验证新口径 ⇒ 本轮对 §5.1 2b/2c、§5.2 的 5 条改写测试、`§5.3` 末两行只做**文本核对**。
3. 浅克隆失败面、merge commit 形态、自定义 `review_manifest_glob`、多段 `required_artifacts` 的端到端：
   无新证据（沿用前轮）。
4. 硬链接借内容、gitlink 的**子模块内容**攻击：未构造（后者需要 CI `submodules: true`，
   `gate.yml:40` 只有 `actions/checkout@v4`、无该键 ⇒ 内容不会物化）。
5. 接入方真实提交（`R068/R069/R070/R090`）**不可复算**（本仓从未归档过 change）。
6. Windows 反斜杠链接：只走代码路径（词法归一化后要么悬空要么逃出，两种读法都红），**未单独构造**。

---

## 必须修改项

**M1（新，影响判红判绿）：「逃出 `A` 的链接 ⇒ 不授予」这条拒绝面未登记，且 R6 要求补的 Scenario 限定未落库。**
- 证据：`/tmp/r7cases/escape_doc`（今天真 CLI `check：通过 ✓` exit 0；新口径 `ARRIVED = []`）；
  隔离变量对照 `/tmp/r7cases/escape_doc_regular`（同一构造、`link.txt` 换成普通文件 ⇒ 今天绿、新口径 `arrived=True`）；
  同类还有 `dangling_out`（悬空+逃出）、`dangling_inA`（悬空在 A 内）、`abs_link`（绝对路径），均「今天绿 / 新红」。
- 未落库的三处：`spec.md:95-99`（误伤面）、`spec.md:334-343`（有意的行为变化）、`design.md:186-210`
  （`§D1 已知边界`）+ `§5.2`（回归面）；以及 **R6 明写要求而现文 `spec.md:313-316` 仍是全称断言**。
- 修法：**(a)** 把 fail-closed 收窄为「解析后落在 `<changes_root>` **之内**但逃出 `A`」（R5 的两个攻击构造
  仍全红，我已复算），或 **(b)** 按上文 §B1 的四项登记 + 给该 Scenario 补一行限定 + 补钉用例。

**M2（新，决定 `N22 ②`/`tasks.md:120` 的必须红能否成立）：gitlink 规则与 `Ev(A)` 的「文件」枚举不自洽。**
- 证据：`git ls-tree -r` 原始输出含 `160000 commit` 行（§B2）；`/tmp/r7cases/gitlink` 在 blob 枚举下
  `arrived=True`（绿）而全行枚举下 `c5=False`（红），今天真 CLI 绿。
- 修法：`spec.md` 明写枚举含非 blob 条目（或另立「`<A>` 下任何 `160000` 条目 ⇒ 不授予」），
  并订正 `design.md:317` / `tasks.md:141` 的命令描述。

---

## 措辞项

1. **`design.md:378-380`**（R7 行）：仍写「必须**每一份**被复制的证据文件都**重写**（或改成 `git mv`）」，
   R6 措辞 4 要求的「每份**至少动一个字节**（见 §D1 的能力天花板）」未逐字落地 —— 与天花板口径（`design.md:169-171`
   「各追加一个换行」）仍有措辞差。
2. **`spec.md:338-343`**（有意的行为变化 2）：构造仍写「**删除** `changes/<id>/` 的其余文件」，
   R6 措辞 11 建议的机制口径「源目录在 head 里消失（其文件被**删除或被搬走**）」未落。
   复算：`/tmp/r6cases/C_pmd_rest_moved`（其余文件被搬到 `src/`）⇒ `ARRIVED=['2026-10-15-x']`（绿，同结论）
   ⇒ **措辞差，不影响判红判绿**。
3. **`tasks.md`**：仍未列 `spec.md`「既有行为不变（回归护栏）」Requirement 的落地任务（R6 措辞 12 未落）。
4. **`tasks.md` 3.1/3.2**：仍未写死「到达候选只取 head 树里是 **tree** 的直接子项」（R6 措辞 10 未落；
   `spec.md` 判据 2 侧有等价语义，tasks 侧没有；`design.md:206` 有「候选只取 tree」的边界行）。
5. **`design.md:112-120` / `spec.md:62-69`**：符号链接条款**未限定作用域**（「`Ev(A)` 的条目」还是
   「`A` 下**所有**条目」）。按后者读，`design.md -> ../../docs/x.md` 这类**非证据**文件链接也会 fail-closed
   （比现稿更严的误伤）。建议补「本条只作用于 `Ev(A)` 的条目」，并钉死解析器（`Path.resolve()` +
   `pathutil.is_within`，与 `resolve_report_path` 同口径）。
6. **`design.md:317` / `tasks.md:141`**：命令描述不准（「只列 blob 行」⇒ 应为「**不含 tree 行**，
   但**含** `160000` gitlink 行」）——与 M2 同一处。
7. **`tasks.md:119-120`**（2.9 ⑬）：未钉住链接 / gitlink 的**位置**（`reviews/` 下、artifact 目录**之下**）
   ⇒ 用例无法覆盖 M2 的形状。

---

## 收敛结论

**不收敛。**

判据 = 「本轮没有新的可证伪项 **且** 所有『必须修改项』都已落库」。两条都不满足：

- **有新的可证伪项**（且都**影响判红判绿**，不是措辞）：
  - M1：`spec.md:313-316` 的无保留 Scenario 仍可被证伪（`escape_doc`：今天真 CLI 绿 / 新口径红；
    对照 `escape_doc_regular` 隔离出「它是符号链接」这一唯一变量）；且「逃出 `A` ⇒ 不授予」的拒绝面
    四处登记位全空。
  - M2：`N22 ②` / `tasks.md:120` 的「gitlink ⇒ 红」在 `Ev(A)` 的「文件」枚举下**不可满足**
    （`gitlink` 探针：blob 枚举绿 / 全行枚举红），根因是 `design.md:317` / `tasks.md:141` 对
    `git ls-tree -r` 输出的描述与实测不符。
- **R6 的一条必须项未落库**：R6 报告 `:317` 明写「并给 `spec.md:306-309` 的 Scenario 补上与 `D2` 同等的
  一行限定（该 Scenario 现为无保留的全称断言）」——现文 `spec.md:313-316` 无任何限定（M1 第 2 条）。

**修复本身是成立的**（这一点要写清楚，避免下一轮误判）：R6 的符号链接口径在 **in-A 一侧**完全达到目的——
R6 的两个合法构造仍绿（真 CLI + 模拟器双证）、R5 的攻击构造仍红、我新造的 6 类变体（非证据文件偷字节 /
链接套链接 / `..` / 绝对路径 / 悬空 / 指向目录）全部落在预期一侧，**本轮没有找到绕过**。
本轮的两条必须项都出在**同一处修复的边界登记与枚举口径**上，属一轮内可收官的改动。
