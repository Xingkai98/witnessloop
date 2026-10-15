# Grill-ADVERSARIAL R4: archive-arrival-recognition 对抗验证（独立零记忆审阅者）

> 任务：**证伪** R3 之后重写的现稿（重点：`Ev(A)` 由数据推导、D4 的 `D` 侧排除键、判据 2 的「全部必需件」），
> 并复算 R3 附注点名的三处。
> 硬约束：不向用户提问、只写本文件、不改 `src/` / `tests/` / 其它 change 文档。

## Reviewer

**独立零记忆**：本对话不携带该 change 的任何历史。设计稿里的「实测」「文件:行号」「已订正」一律当**待验证断言**；
R1 / R2 / R3 的结论只当**待复核的声明**，不当事实。

**评审基线**：`git rev-parse HEAD` = **`0fa9a2a`**（`archive-arrival-recognition/2026-10-15`），
本报告所有 `文件:行号` 对应**会话开始时**读到的文本（`design.md` 669 行 / `spec.md` 330 行 / `tasks.md` 179 行 /
`proposal.md` 105 行）。评审期间**未改任何仓内文件**（`git status` 收尾：仅本报告一个新增文件）。

**读了**：本 change 的 `proposal.md` / `design.md` / `tasks.md` / `specs/archive-awareness/spec.md` /
`reviews/{grill-design,grill-adversarial,grill-adversarial-r2,grill-adversarial-r3}.md`；
源码 `src/witnessloop/{contract,checkcmd,gitutil,policy,paths,constants,manifestcmd,evidence,hashing,events}.py`；
测试 `tests/test_archive_awareness.py` / `helpers.py` / `conftest.py`。

**跑了**（全部可复算；scratch 只落在 `/tmp`）：

1. `.venv/bin/pytest -q` → **601 passed**；`tests/test_archive_awareness.py` → **25 passed**（与 R3 基线一致）。
2. **自写判据模拟器 `/tmp/r4sim.py`**——按 `design.md:69-104`（D1 五条）+ `design.md:283-288`（D7 命令表）+
   `design.md:238-245`（D4）+ `spec.md:20-57` **从零转写**（**未读** `/tmp/r3sim.py` / `/tmp/sim_d1v3.py` 的代码）。
   它同时算出「D4 收窄 + `D` 侧排除键」之后的 active id 集合。
   用法：`python3 /tmp/r4sim.py <repo> [base] [head] [--verbose]`（只读 git 树）。
3. 在 R2/R3 留下的 **41 个构造仓**（`/tmp/cases/*` 18 个、`/tmp/r3cases/*` 7 个、`/tmp/r3cases2/*` 14 个、`/tmp/e2e_*` 3 个）
   上独立复算 ⇒ 与 `design.md §7.4` 与 R3 的表**逐条一致**（见 C 节）。
   ⚠️ 这些仓是前几轮**造的数据**，我只当输入用；**不**采信它们的结论。
4. **自建 9 个新构造**（`/tmp/build_r4_cases.py` + 内联脚本 → `/tmp/r4cases/*`），专打 R3 附注三处 + 判据 2/5 的边界。
5. **真 CLI**（`.venv/bin/python -m witnessloop check`）在 `/tmp/e2e_r3_a1`、`/tmp/e2e_r3_a2`、`/tmp/e2e_partial`
   上复跑 ⇒ 三条**今天都 `check：通过 ✓`（退出码 0）**。用途只有一个：证明这三条的**证据门那一半是真的绿**，
   因此现稿若判「不授予」，起作用的只能是**判据 5**（而不是证据门）。
6. `git ls-tree` 的 pathspec 语义实测（含 `*` / `?` / `[` 的名字、`:(glob)` magic）；
   `git diff -M -C` 的 `C` 记录行为实测；`policy.Policy.from_doc` 的 `required_artifacts` / `changes_root` 覆写实测。

---

## 对抗结论

### A. 找绕过

#### A0. R3 附注点名的三处（本轮必答）

**①「手写 manifest 的 `report_path` 指向 change 目录内任意路径」还能不能出圈？ → 不能（已关掉）。**

- 构造 `/tmp/r4cases/i1a_deep_referenced`：受害者在 `archive/2026-09-30-old/`；`cp -r` 成 `archive/2026-10-15-new/`，
  把三份报告**逐字节**搬到 `<A>/deep/nested/`（`reviews/**` 之外），手写三份 manifest 把 `report_path` 指过去
  （manifest 本身仍落在 `reviews/`，被 glob 命中）。
  ```
  $ python3 /tmp/r4sim.py /tmp/r4cases/i1a_deep_referenced main HEAD
  2026-10-15-new: arrived=False c1=True c2=True c3=True c4=True c5=False srcs=[]
      第5条命中: .../2026-10-15-new/deep/nested/building-review.md
      第5条命中: .../2026-10-15-new/deep/nested/grill-adversarial.md
      第5条命中: .../2026-10-15-new/deep/nested/grill-review.md
      第5条命中: .../2026-10-15-new/specs/cap/spec.md
      第5条命中: .../2026-10-15-new/tasks.md
  ```
  ⇒ `Ev(A)` 的 part 2（`report_path` 解析出的那个文件）**真的**把「挪出 `reviews/` 的证词」抓回来了。
- 更强的一条：R3 的真 CLI 绿构造 `/tmp/e2e_r3_a1`（同形，报告放 change 目录**根**）在现稿文本下
  ```
  $ python3 /tmp/r4sim.py /tmp/e2e_r3_a1 main HEAD
  2026-10-15-stub: arrived=False c1=True c2=True c3=True c4=True c5=False srcs=['stub']
      第5条命中: .../2026-10-15-stub/building-review.md
      第5条命中: .../2026-10-15-stub/grill-adversarial.md
      第5条命中: .../2026-10-15-stub/grill-review.md
  ```
  而同一仓的真 CLI **今天仍绿**（12 个变更文件 / 1 个 change 目录 / `check：通过 ✓`）⇒ 二者之差只可能来自判据 5。
  ⇒ **R3 的 A1 确已关闭。**

**②「多份 manifest / 未知 stage 的 manifest」都被枚举进 `Ev(A)` 吗？ → 是。**

- 构造 `/tmp/r4cases/i1c_unknown_stage`：三份正式 manifest 自写、报告也自写；再放一份
  `reviews/bogus.manifest.json`（`stage: "bogus"`）把 `report_path` 指向 `<A>/borrowed2.md`（受害者的报告，逐字节）。
  ```
  $ python3 /tmp/r4sim.py /tmp/r4cases/i1c_unknown_stage main HEAD
  2026-10-15-new: arrived=False c1=True c2=True c3=True c4=True c5=False srcs=[]
      第5条命中: .../2026-10-15-new/borrowed2.md
      第5条命中: .../2026-10-15-new/specs/cap/spec.md
      第5条命中: .../2026-10-15-new/tasks.md
  ```
  ⇒ `policy.review_manifest_glob` 命中的**每一份**（含未知 stage）都进了 `Ev(A)`，其 `report_path` 目标也进了。
  （机制上与证据门一致：`contract.validate_review_manifests` 也遍历**全部** glob 命中项，与 stage 无关。）

**③「报告正文与 `report_path` 目标分离」（绑定一份、把借来的正文放另一处）→ 能构造出 `arrived=True`，但不是出圈。**

- 构造 `/tmp/r4cases/i1b2_separation_clean`：`<A>/borrowed.md` 是受害者报告的**逐字节副本**，
  **不被任何 manifest 绑定**、不在 `reviews/**`、不是 artifact；其余要件与三份报告/ manifest 全部自写（字节全新）。
  ```
  $ python3 /tmp/r4sim.py /tmp/r4cases/i1b2_separation_clean main HEAD --verbose
  2026-10-15-new: arrived=True c1=True c2=True c3=True c4=True c5=True srcs=[]
      Ev(A)=[.../reviews/building-review.md, .../reviews/building.manifest.json,
             .../reviews/grill-adversarial.manifest.json, .../reviews/grill-adversarial.md,
             .../reviews/grill-review.md, .../reviews/grill.manifest.json,
             .../specs/cap/spec.md, .../tasks.md]
  ```
  ⇒ `<A>/borrowed.md` **不在** `Ev(A)` 里（`arrived=True`）。
- **但它不是绕过**：证据门读取的报告是「`report_path` 解析出的文件」（`contract.py:502-514`）、
  manifest（`contract.py:252`）、artifact（`contract.py:522-534`）、`reviews/**/*.md`（孤儿规则 `contract.py:333`）——
  **一个没被绑定的文件不被任何一条读**。攻击者仍必须**自己写**一份合格的 grill 正文（我这构造里就写了），
  所以借来的那份**零收益**。
  ⇒ 精确结论：**`Ev(A)` 恰好是「门禁读取面」的上界**（唯一例外是 `workflow-events.jsonl`，见 E4，而它本就无需借用即可伪造）。

**④「A2 档不要求红」这条文档化天花板与 §8 Q4 的取舍是否一致？ → design.md 一致；`spec.md:66` 残留伪等价论证（矛盾）。**

- 一致的部分：`design.md:142`（表行「逃逸 ✗ —— 能力天花板」）、`design.md:180`（已知边界）、
  `§5.1 第 9 条 ⑩`（「**不拒**（= 能力天花板）…**不**要求它红」）、`§5.3 N21`（「⚠️ **不红 —— 能力天花板**」）、
  `spec.md:70-74`（「**绕过**本判据…**不挡**「跑一个脚本给每份证据各加一个字节」这一档」）——**口径一致**，
  且**没有**任何一处宣称拦住了这一档。R3 的 A2 构造在本轮复算下也是 `arrived=True`（见 C 节）。
- **但残留一处矛盾**（见 D-n1 / M1）：`design.md:156-158` 明写

  > `> ⚠️ **订正**：本稿初版把这条写成「等价于自己写一份完整证据（每个文件都得动）」。**那是错的**——`

  而 `spec.md:66` 仍在：
  ```
  $ grep -n "等价于「自己写一份完整证据」" specs/archive-awareness/spec.md
  66:- 把**每一个**文件都改掉字节再重算 manifest 哈希者**不在此判据射程内**——那等价于「自己写一份完整证据」，
  ```
  ⇒ 同一个 `spec.md` 里 line 66（「等价于自己写一份完整证据」）与 line 70-74（「**绕过**本判据」）**互相矛盾**，
  且 line 66 正是 `design.md` 声明「为假、已删除」的那条论证。**R3 的 M2 只落了一半**（它点名要同步
  `specs/…/spec.md:54-58` 的措辞，`design.md:551` 的处置段也只记了 design 侧）。

**⑤ D 侧排除键在「`D` 记录的 `path` 落在**仍在 head** 的源目录下」时不得排除 → 成立（实测）。**

- 构造 `/tmp/r4cases/i3_dpath_alive_src`：base 有件齐的 active `z`（+`notes.md`+`extra.md`）；
  feature：`git mv changes/z/notes.md archive/2026-10-15-z/notes.md`（制造源）
  + `git rm changes/z/extra.md`（**D 记录，path 落在仍在 head 的 `changes/z/` 下**）
  + 给到达目录写全新要件 + 改 `app.py`。
  ```
  $ git -C /tmp/r4cases/i3_dpath_alive_src diff -M --name-status main HEAD
  M	app.py
  A	openspec/changes/archive/2026-10-15-z/design.md
  R100	openspec/changes/z/notes.md	openspec/changes/archive/2026-10-15-z/notes.md
  A	openspec/changes/archive/2026-10-15-z/proposal.md
  A	openspec/changes/archive/2026-10-15-z/specs/cap/spec.md
  A	openspec/changes/archive/2026-10-15-z/tasks.md
  D	openspec/changes/z/extra.md
  $ python3 /tmp/r4sim.py /tmp/r4cases/i3_dpath_alive_src main HEAD
  2026-10-15-z: arrived=True c1=True c2=True c3=True c4=True c5=True srcs=['z']
  arrived = ['2026-10-15-z']
  D4 后的 active ids = ['z']          ← D 记录**没有**被排除，z 仍是 active target（按现稿文本）
  ```
  ⇒ 现稿的「且该目录在 head 树里已不存在」这一限定**确实**挡住了「重开 `test_N6` 式静默逃检」。
  同 diff 的 `test_N6` 原形（`/tmp/r3cases2/n6_exact`）也复核为 `active ids = ['another-change']`（今天 = `[]`）⇒ B2 的结论成立。
- ⚠️ 一处**未定义**（不影响本条结论，但会漂）：现稿在 `design.md:84-88/238-245`、`spec.md:35-44`、`tasks.md:129-131`
  都用「**到达组**」，却**从未定义它的成员**。我按唯一自然读法实现（组 = `new_path` 落在 `<A>/` 下的记录集合）。
  两种可能的读法（「只看出边」「看进出两边」）在判据 3/4 上方向都是 fail-closed，但**实现必须写死**。见 M4。

#### A1. 判据 5 的**完全旁路**：现稿把机理写窄了——**不需要 `git mv`，分支 (a) 单独即豁免**

- 构造 `/tmp/r4cases/i5_cp_from_outside_root`：base 里现成证据**只在 `docs/shipped/2026-09-30-old/`**（`changes_root` 之外）；
  feature **普通 `cp -r`**（⇒ 全 `A`、**零 rename 记录**）+ 手改 manifest 的 `change_id` + 改 `app.py`。
  ```
  $ python3 /tmp/r4sim.py /tmp/r4cases/i5_cp_from_outside_root main HEAD
  2026-10-15-new: arrived=True c1=True c2=True c3=True c4=True c5=True srcs=[]
  $ git -C /tmp/r4cases/i5_cp_from_outside_root diff -M --name-status main HEAD | head -5
  M	app.py
  A	openspec/changes/archive/2026-10-15-new/design.md
  A	openspec/changes/archive/2026-10-15-new/proposal.md
  A	openspec/changes/archive/2026-10-15-new/reviews/building-review.md
  ...
  ```
  ⇒ 分支 (b)（改名落点）**完全没参与**，单靠 (a)（blob 不在基准树 `<changes_root>/**` 里）就全过了。
- 旁证（用 R3 的 `a4b` 仓量化）：它的 10 份文件 blob **0/10** 出现在 base 的 `changes_root/**` 里
  ```
  $ python3 - <<'PY'   # 见正文脚本；输出：
    到达目录文件数=10，其中 blob 出现在 base changes_root/** 的=0
  PY
  ```
  ⇒ `a4b` 的 `arrived=True` 同样由 (a) 单独解释。
- 现稿的写法（`design.md:176-179`）是「…把那份副本 **`git mv` 进来**（实测 `a4b`：10 条 `R100`）⇒ (a) 与 (b)
  **同时**豁免同一份内容」——把 (b) 写成了必要条件。**实质结论（是旁路）没错，机理写窄了**（`cp` 同样，且成本更低）。见 M3。

#### A2. 证伪失败（失败的尝试，负面证据同样有价值）

- **猜想：`git ls-tree -- <path>` 的 pathspec 会 glob，从而让判据 1 把「基准树里存在 `archive/foo[1]`」误判成「0 行 ⇒ 无 entry ⇒ 放行」。**
  **被证伪**：
  ```
  $ cd /tmp/ltprobe2 && git ls-tree -r main -- '*.md'            # 仓里有 2 个 *.md
  (0 行)
  $ git ls-files '*.md'                                          # 对照：有 glob
  openspec/changes/archive/barXYZ/tasks.md
  openspec/changes/archive/foo1/tasks.md
  $ git ls-tree -r main -- ':(glob)*.md'
  fatal: :(glob)*.md: pathspec magic not supported by this command: 'glob'
  ```
  ⇒ `git ls-tree`（git 2.43.0）**不做 pathspec glob**，含 `*` / `?` / `[` 的目录名也按字面匹配。
  `design.md:285-287`（D7 表）的「存在 ⇒ 1 行 / 不存在 ⇒ 0 行」**成立**。⇒ 该绕过**不成立**。
- **猜想：把 `policy.required_artifacts` 覆写成 `[]` 关掉判据 2。** **被证伪**：
  `policy.py:115-117` 是 `tuple(doc.get("required_artifacts") or C.DEFAULT_REQUIRED_ARTIFACTS)` ⇒ `[]` 回落默认。
  ```
  required_artifacts=            [] -> ('proposal.md', 'design.md', 'tasks.md', 'specs', 'reviews')
  required_artifacts=          [''] -> ('',)
  required_artifacts=         ['.'] -> ('.',)
  required_artifacts=['specs/cap/spec.md'] -> ('specs/cap/spec.md',)
  (dir / '').exists() = True      (dir / '.').exists() = True
  ```
  ⇒ `[]` 关不掉；`[""]` / `["."]` **能**把判据 2 中和成「任何目录」（见 E2，方向 fail-closed，不构成绕过）。
- **判据 1 / 3 / 4 未能绕过**：预存目录加文件（`r10`）、base 同路径是 blob（`r11`）⇒ `c1=False`；
  改名既有归档目录（`r8`）、copy+删源（`r9`）⇒ `c3=False`；名不认得的第三源（`t471e`）⇒ `c4=False`（整个到达被拒）；
  顺带改 change id（`f3_change_id`）⇒ `c4=False`。
- **未能在新 `Ev(A)` 下找到新的出圈构造**：见 A0③ 的分析——`Ev(A)` 覆盖了门禁读取面的全部内容型文件。

### B. 找假阴性 / 误伤

- **必须绿的四条**（复算）：`r6` 纯 move / `r7` move+重建 manifest / `m1`+`m3` move+重度改写 / `r13` 出生即归档
  ⇒ 全 `arrived=True` 且 `active ids` 无幽灵 id。⇒ `design.md:143-145`、`proposal.md` 验收段的三条真实形态**成立**。
- **误伤对照（必须绿）**：`/tmp/r3cases2/e11b`（新 change 的 `design.md` 与 base 里某 change 逐字节相同）⇒ `arrived=True`
  ⇒ `design.md:146` 的声明成立。
- **空文件豁免（必须绿）**：自建 `/tmp/r4cases/empty13_gitkeep`（到达目录里放 0 字节 `.gitkeep`，base 里也有空文件）
  ⇒ `arrived=True` ⇒ `spec.md:82` / `§5.1 第 13 条` 成立。
- **明写的误伤面（预期红）**：自建 `/tmp/r4cases/e12_sibling_spec_copy`（原样复制兄弟 change 的 `specs/limits.md`）
  ⇒ `arrived=False`，**命中项只有该文件**
  ```
  第5条命中: openspec/changes/archive/2026-10-15-born/specs/limits.md
  ```
  ⇒ `design.md:170-173` 的「只点名该文件」成立（⚠️ 该构造里 `c2` 也是 False——因为 `reviews/` 是**空目录**，见 B-新）。
- **`test_N2`（`:541`）「不要误改」成立**：自建 `/tmp/r4cases/t541_forged_missing_reviews`（假归档缺 `reviews/`）
  ⇒ `c2=False` ⇒ 不是 target ⇒ `"没有任何 change 目录"` 仍成立。
- **`test_N4`（`:577`）「不要误改」成立**：自建 `/tmp/r4cases/t577_touch_existing_archive`（`M` 已归档文件 + 改代码）
  ⇒ `c1=False` ⇒ 不是 target ⇒ 断言仍成立。`test_deeper_events_file_is_not_read`（`:378`）同理（`r15` ⇒ `c2=False`）。
- **【新，低】空目录的树/工作树口径**：`reviews/` 若**空**，head **树**里没有它 ⇒ 判据 2 判「缺 `reviews`」（我在
  `e12` 构造里实测 `c2=False`），而 `contract.validate_change_dir`（`contract.py:211-213`，`(directory/artifact).exists()`，
  跑在**工作树**）会判「在」。真实 CI（checkout head，git 不记录空目录）下两者同结论，故**不是现实误伤**；
  但实现必须按**树**语义，建议在 `tasks.md 3.1/3.2` 写死「候选与判据 2 一律按 head 树；空目录不算存在」。

### C. 判据 1–5 的必要性与充分性

| # | 去掉它会怎样 | 能不能被绕过 | 本轮复算 |
|---|---|---|---|
| **1**（基准树无 entry） | 预存归档目录立刻被授予 ⇒ `N2`/`N3`/`N4`/R1-F1 的 copy 变体全回来 | **不能**（A2 的 pathspec 猜想被实测证伪） | `r10`/`r11`/`t577`/`t541` 边界构造 ⇒ `c1=False` |
| **2**（head 是 tree 且含**全部**必需件） | F2/B1 的组织型子目录假红回来 | 作为**入口条件**不承重安全；`[""]` 可中和（E2，方向 fail-closed） | `r12`/`r15` ⇒ `c2=False`；多段名可判（`required_artifacts=['specs/cap/spec.md']` 可解析） |
| **3**（组里无来自 `archive/**` 的源） | 改名既有归档目录 / copy+删源 ⇒ 白捡证据 | **挡得住**（对「copy 源不动」结构性失明，那是第 5 条的活） | `r8`/`r9` ⇒ `c3=False` |
| **4**（有源须名识别，**每一个**） | 「名不认得的源混进到达组」不再被挡；**「归档时顺带改 change id」这条唯一的守卫消失** | 不承重安全（它原本挡的 `N6` 已被判据 1 独立关掉），但不误伤常规 `<date>-<id>` | `t471d`/`r6`/`r13`/`i3` ⇒ `c4=True`；`t471e`/`f3_change_id` ⇒ `c4=False` |
| **5**（内容来源） | R1 的 F1 原版立刻复活（`r1` 唯一屏障就是它） | **必要但不充分**（R3 的判定我复核成立）：A1 类**已关**；剩余射程外 = A2 档（`a2_all_one_byte` ⇒ `arrived=True`，已文档化）+ `changes_root` 之外的副本（`i5` ⇒ `arrived=True`） | `r1` 命中 8/8；`i1a`/`i1c`/`a3b`/`a5`/`e12` 全 `arrived=False` |

**小结**：第 1/3/4 条的必要性复核成立、未被绕过；第 2 条达到它宣称的目的（关掉 B1 假红），但不承重安全；
**第 5 条「必要但不充分」，且其能力边界现稿**已**诚实写明**（唯一自相矛盾处是 `spec.md:66`）。

**独立复算与 `design.md §7.4` 的一致性**（我用自己的转写复跑 R2 的 18 个构造）：
`r1/r2/r3/r4/r5/r16/r19` ⇒ `arrived=False`；`r6/r7/r13` ⇒ `True`；`r8/r9` ⇒ `c3=False`；`r10/r11` ⇒ `c1=False`；
`r12/r15` ⇒ `c2=False`；`r21` ⇒ `False` 且 `archive/2026` `c2=False`；`/tmp/e2e_partial` ⇒ `arrived=False` 且命中 **5** 份
（`reviews/*.md` ×3 + `specs/cap/spec.md` + `tasks.md`）；`m3` ⇒ `arrived=True` 且 `active ids=[]`（A4 的修法**确实**生效）；
`a2_all_one_byte` ⇒ `True`（天花板）；`t494b_regression_recipe` ⇒ `False`（B1 成立）；`t471e` ⇒ `c4=False`。**逐条一致。**

### D. 与源码事实核对（`文件:行号`）

**成立（逐条复核过）**

- `contract.py:65` `is_archive_move`（`:72` `status != "R100"` 早退）/ `:85-116` `changed_change_ids`（`:97-101`
  `archived_sources`、`:110-111` `archive/**` 排除分支）/ `:119-147` `archive_grant`（`:145` 名识别）/
  `:150-189` `change_targets`（**列表**、以目录为键、别名取并集）——行号无漂移。
- `contract.py:211-213` 必需件「路径存在」判定 / `:252` `directory.glob(policy.review_manifest_glob)` /
  `:282-300` `resolve_report_path`（**只要求目录内**，不要求 `reviews/`）/ `:333` 孤儿扫描 `reviews.rglob("*.md")` /
  `:502-534` 哈希绑定（`report_hash` + `HASHED_ARTIFACTS` 两项）——行号无漂移。
- `checkcmd.py:105-119` 两条 stage 硬门 / `:121` `_require_change` / `:178-194` `_code_hits` / `:228-286` `_protected_writes`
  （`:255` `is_archive_move` 早退、`:260-275` 保护面判定、`:270` `by_invariant and status[:1]=="A"` 免事件）——无漂移。
- `gitutil.py:99-111` `changed_files` = `base...head` **三点** + `--find-renames`（**只有** `-M`，无 `-C`）⇒ **不产生 `C` 记录**；
  `:114-130` `_parse_name_status`：`R`/`C` 带 `old_path`，**其余记录 `old_path=None`**（`D` 的路径在 `path` 里）——A4 的根因，无漂移。
- `policy.py:76-92` `stale_exempt_paths` 末项 `archive/**`（暗房存在）/ `:106-117` `require_change_for` 与
  `required_artifacts` 都用 `or DEFAULT`（**`[]` 关不掉**）/ `:18-23` 不变集；`constants.py:87-90` `HASHED_ARTIFACTS`；
  `manifestcmd.py:33-48` `resolve_change_dir`（按**磁盘**存在性）/ `:136-142` **报告必须落在 `reviews/`**（**只有它强制**）/
  `:146-153` 每次 build 从磁盘**重算**哈希；`hashing.py:22-37` `sha256_tree`（文件 ⇒ 其字节；目录 ⇒ 排序后逐文件）；
  `events.py:80-103` `load_all` 只读 `changes_root/*/` 与 `archive_root/*/` **一层**。
- `manifest build` **不调用** `change_targets`（`grep -n change_targets src/witnessloop/manifestcmd.py` 为空）
  ⇒ `design.md:294-298` / `tasks.md 3.6` 的订正成立。

**不成立 / 需订正（本轮新发现）**

1. **`spec.md:66` 与 `design.md:156-158` 直接矛盾**（design 判该等价论证为**假**并声明「本稿据此删除」；spec 仍在），
   且与**同一份** `spec.md:70-74` 自相矛盾。R3 的 M2 只落了 design 一侧。⇒ **M1**。
2. **「必须改写」的计数**：`design.md:398` 写「（**4** 条）」而紧接着实列 **5** 项（`:274`/`:494`/`:109`/`:49`/`:600`）；
   `design.md:345`（风险表 R5）仍写「必须改写（**3** 条）」；`design.md:557` 声称「计数与清单已对齐（§5.2）」——
   **该声称不成立**（R3 的 M5 只落了「3→4」，随后 B2 又加了第 5 项而未同步）。
   ```
   $ grep -n "（4 条；改前绿\|必须改写\*\*（3 条）\|计数与清单已对齐" design.md
   345:| R5 | ...（3 条）与**不要误改**（3 条）...
   398:- **必须改写的既有测试**（4 条；改前绿是**旧语义**下的绿）：
   557:| **M5**（中） | ... | 计数与清单已对齐（§5.2） |
   ```
   ⇒ **M2**。
3. **`design.md:556`（B3 处置）指向的「（§3 第 5 条）」里没有模板这一项**：`design.md:324-326` 的 `docs/gate.md`
   更新清单未含「模板放 `changes_root` 之外」（而 `tasks.md:25-26` 与 `tasks.md:167` 有）⇒ 指针失效。⇒ **M5**。
4. **`design.md:176-179`（完全旁路）把机理写成需要 `git mv`**（见 A1）⇒ **M3**。
5. **`design.md:347-348`（R7）写「必须**每一份**被复制的证据文件都**重写**」**——与天花板（每份文件 +1 字节即可）措辞不符
   （R3 的 E-4 未被 `§7.3b` 的处置表收录）。⇒ **M5**。
6. **`§5.3` 表行序跳号**：`N19`/`N20`/`N21` 插在 `N11` 与 `N12` 之间（`design.md:449-451`）⇒ 低危，建议按号排。
7. **「到达组」无定义**（`design.md:84-88/238-245`、`spec.md:35-44`）⇒ **M4**。

### E. 低危观察（不阻塞）

1. **「到达组」未定义**（M4）——实现期最可能漂的地方，与 R1/R2 栽过的坑同类。
2. **`required_artifacts: [""]` / `["."]` 会把判据 2 中和成「任何目录」**（实测 `(dir/"")` 与 `(dir/".")` 都是目录本身）。
   方向 fail-closed（只会把 `archive/2026/`、`archive/notes/` 重新变成 target、多报「缺少必需件」），**但**这会
   反过来推翻 R3 的 E-2 / `tasks.md 3.9` 想要的「近失文案」——`design.md:80-83` 建议补一句「空 / `.` 这类
   artifact 名不参与判据 2」。
3. **自定义 `policy.review_manifest_glob`**（R3 的 E-1）：实测 `manifest build` 直接拒
   （`manifestcmd.py:136-142`，报告必须在 `reviews/` 下）且它自己硬编码写 `reviews/`（`:201-204`）⇒ 该配置不可用。
   但判据 5 的 part 3 硬编码 `reviews/**`、part 2 用 glob ⇒ 两者在自定义 glob 下分叉（**本 change 不引入**，
   建议顺手把 part 3 也写成「glob 命中目录的 `**`」，或在 `docs/gate.md §6` 声明该配置不受支持）。
4. **`workflow-events.jsonl` 不在 `Ev(A)`**（也不在 1/2/3 任一部分），但门禁读它（`events.py`）。
   不过事件是自由文本、**无需借用即可由作者自写**（`events.py:5-8` 明写「防漂移不防伪造」）
   ⇒ **不是新面**，登记即可。
5. **`§5.3` 末行（归档时顺带改 change id）**措辞「**当前设计下红**」易被读成新引入的拒绝面；实测**今天也红**
   （`f3_change_id`：`changed_change_ids==[]`、`archive_grant` 零命中）⇒ 建议补「今天亦红」（R3 的 E-5 未处置）。
6. **`archive/` 直接子项是 blob 的形态**（R3 的 E-6）：现稿无条款；我的实现与现稿一致（候选只取 tree），
   不构成绕过，建议实现期在 `tasks.md 3.2` 明写。
7. **`tasks.md` 没有覆盖 `spec.md` 的「既有行为不变（回归护栏）」那条 Requirement**（`tasks.md 1.1-1.7` 未列）
   ——低危的文档完整性缺口。

---

## 未验证项

1. **接入方的具体数字**（`proposal.md:30-32` 的 33 文件全 `A`、`R068/R069/R070/R090`、16 文件 11 项、「120 个归档目录」）
   ——另一个仓的提交，本工作区**无法复算**；我只复现了**方向**（`git mv` + 改被搬文件 ⇒ `R<100`；`cp` ⇒ 全 `A`）。
2. **现稿判据的「实现」不存在**：A/B/C 里的**到达判定那一半**全部来自我按文本逐字转写的 `/tmp/r4sim.py`。
   最敏感的四处（与 R3 相同）：①`report_path` 的**解析口径**（我按字符串归一 + `..`；真实现会用
   `contract.resolve_report_path` ⇒ `Path.resolve()`，含**符号链接**展开与**工作树**存在性）；②空文件按 head **blob 字节数**
   （我的读法）还是工作树；③是否把 `C` 记录算作 (b)（我按「只认 `R`」，与 `gitutil.py:105` 只传 `-M` 一致）；
   ④候选枚举只取 tree。**e2e 三条里证据门那一半是真 CLI，到达那一半不是。**
3. **浅克隆 / partial clone 下「`merge-base` 成功但 `ls-tree` 失败」这一独立面**：仍未复现（R1/R2/R3 同）。
4. **merge commit 形态**：未取得可判定结论（沿用 R2/R3 的遗留）。
5. **自定义 `review_manifest_glob` 端到端**：只到 E3 那一步（`manifest build` 拒绝该布局）。
6. **`policy.required_artifacts` 覆写成多段名的端到端**：只验证了 `Policy.from_doc` 的取值与「树里可见多段名」，
   未跑端到端。
7. **大仓（120 个归档目录）下逐字节撞车的概率**（`tasks.md 4.6`）：未测。
8. **`design.md §7.4` 的 E12 原始仓**（`只点名 specs/limits.md`）在 `/tmp` 里不存在 ⇒ 我**自建**等价构造
   （`/tmp/r4cases/e12_sibling_spec_copy`）复现了结论，但**不是**原作者那个仓。
9. `docs/gate.md` 的对应改动（`§3 第 5 条` / `tasks.md 6.1`）属实现期义务，尚未落 ⇒ 未核。

---

## 必须修改项

> 每条附最小复现与证据。**没有安全级的新绕过**；以下全部是**设计文本**层面的可证伪项。

- **M1（中）`spec.md:66` 必须与 `design.md §D1 第 5 条` 对齐——删掉「等价于「自己写一份完整证据」」这条伪等价论证。**
  - 证据：`design.md:156-158` 明写该论证「**那是错的**」且已删；`spec.md:66` 仍在，并与 `spec.md:70-74` 自相矛盾。
  - 最小复现：`grep -n "等价于「自己写一份完整证据」" specs/archive-awareness/spec.md design.md`
    ⇒ 命中 `spec.md:66`（design 侧只剩那条「订正」句）。
  - 这是 R3 的 M2 的**未落部分**；`design.md:551` 的处置段应补记 spec 一侧。
- **M2（中-低）订正「必须改写」的计数（或去掉数字）。**
  - 证据：`design.md:398`「（4 条）」vs 实列 **5** 项；`design.md:345` 仍「（3 条）」；`design.md:557` 的
    「计数与清单已对齐」为**假**。最小复现见 D-n2 的 `grep`。
- **M3（低）`design.md:176-179`（完全旁路）写明「分支 (a) 单独即豁免，与是否 `git mv` 无关」。**
  - 证据：`/tmp/r4cases/i5_cp_from_outside_root`（**普通 `cp`、零 rename**）⇒ `arrived=True`；
    `/tmp/r3cases2/a4b_outside_root` 的 10 份文件 blob **0/10** 在 base 的 `changes_root/**` 里。
- **M4（低）把「到达组」的定义写死**（`design.md §2 D1` / `spec.md Req1` / `tasks.md 3.2`）：
  「到达组 = 本次 diff 中 `new_path` 落在 `<A>/` 下的记录集合」。
- **M5（低）三处措辞/指针**：① `design.md:347-348`（R7）的「重写」→「至少动一个字节（见天花板）」；
  ② `design.md:556` 的「（§3 第 5 条）」补上模板项（或在 `design.md:324-326` 补「模板放 `changes_root` 之外」）；
  ③ `§5.3` 表按编号排序（`N19`–`N21` 现在插在 `N11` 与 `N12` 之间）。
- **M6（低，建议）判据 5 的 `Ev(A)` part 3 与 part 2 的目录口径对齐**（part 3 硬编码 `reviews/**`）：
  自定义 `review_manifest_glob` 下二者分叉（E3）；并在 `design.md:80-83` 补一句「空 / `.` 这类 artifact 名不参与判据 2」。

---

## Open Questions

> 只放**真需要用户拍板**的。能由代码 / 安全属性 / 本轮实测定案的都已移出（见「必须修改项」与 D 节）。

**OQ-1（= `design.md §8 Q4`，重问第三次）第 5 条的强度取哪一档？**
- 本轮的新证据只**加强**了现稿的推荐：新 `Ev(A)` 确实关掉了「报告挪出 `reviews/`」（`i1a` / `e2e_r3_a1`）
  与「换路径形态」（`a3b`/`a5`），而 A2 档在 (a)(b)(c) 三档里**都**逃逸（`a2_all_one_byte` ⇒ `arrived=True`）。
- **但请先修 M1**：用户读到的 `spec.md:66` 现在是「等价于自己写一份完整证据」——这条论证已被判为**假**，
  留着会让用户在错误的成本认知下拍板。

**OQ-2（= `§8 Q1`，未变）名识别守卫保留还是删除？** 本轮无新证据改变取舍；判据 4 我实测有效且不误伤常规流（`i3`/`r6`）。

**OQ-3（= `§8 Q2`）/ OQ-4（= `§8 Q3`）**：stale 暗房、嵌套归档布局——沿用 R3，本 change 正交、不阻塞。

---

## 收敛结论

**不收敛。**

**理由**：本轮**没有**找到新的安全级绕过（这一点是负面证据，见 A0/A2/C 节），但存在**新的、可复算的**设计文本证伪项，
且其中至少一条是**文档自相矛盾**（不是措辞偏好）——按本 change 自己的收敛判据（「没有新的可证伪项、且所有必须修改项都已落库」），
M1 / M2 未落库即不收敛。

**新的、可复算的证伪项（最小复现；全部在 `/tmp`，未改仓内任何文件）**

```bash
cd /home/happy/wl-wt/archive-arrival-recognition

# ① M1：design 说该论证为假并已删，spec 仍在（同一份 spec 内还自相矛盾）
grep -n "等价于「自己写一份完整证据」" \
     openspec/changes/archive-arrival-recognition/{design.md,specs/archive-awareness/spec.md}
#   → spec.md:66 命中；design.md 只剩 :156-158 的「那是错的」订正句
sed -n '66,67p;70,74p' openspec/changes/archive-arrival-recognition/specs/archive-awareness/spec.md
#   → line 66「…等价于「自己写一份完整证据」」 vs line 70-74「⇒ **绕过**本判据」

# ② M2：计数与实列不一致，且「已对齐」为假
grep -n "（4 条；改前绿\|必须改写\*\*（3 条）\|计数与清单已对齐" \
     openspec/changes/archive-arrival-recognition/design.md
#   → 345: (3 条) / 398: (4 条)  / 557: 「计数与清单已对齐（§5.2）」；而 :399-424 实列 5 项

# ③ M3：完全旁路**不需要 git mv**（分支 (a) 单独即豁免）
python3 /tmp/r4sim.py /tmp/r4cases/i5_cp_from_outside_root main HEAD
#   → 2026-10-15-new: arrived=True c1..c5 全 True（该 diff 全是 A，零 rename 记录）

# ④ 复算 R3 点名的三处（负面证据）
python3 /tmp/r4sim.py /tmp/r4cases/i1a_deep_referenced   main HEAD   # arrived=False（report_path 目标被抓回）
python3 /tmp/r4sim.py /tmp/r4cases/i1c_unknown_stage     main HEAD   # arrived=False（未知 stage manifest 也被枚举）
python3 /tmp/r4sim.py /tmp/r4cases/i1b2_separation_clean main HEAD   # arrived=True（未绑定的借用副本不进 Ev(A)，但门禁也不读它）
python3 /tmp/r4sim.py /tmp/r4cases/i3_dpath_alive_src    main HEAD   # arrived=True 且 active ids=['z']（D 侧排除键未误排除）
```

**负面证据（同样有价值）**：R2 的 18 个构造 + R3 的 21 个构造 + e2e 三条我**独立转写后逐条复算，与 `§7.4`/R3 的表一致**；
必须绿的四条全绿；判据 1/3/4 我未能绕过；`git ls-tree` 的 pathspec 猜想与 `required_artifacts: []` 猜想**均被实测证伪**；
R3 的 A1/A3/A4/B1/B2 处置**确已生效**（`i1a`/`a3b`/`a5`/`m3`/`t494b`/`n6_exact` 逐条复核成立）。

**给作者的收敛判据**：M1–M6 落库（M1 是**真改文本**、M2 是**改数字或删数字**，其余为措辞/指针）之后，再跑一轮 R5；
R5 若只剩措辞项即收敛。⚠️ 另请注意 `design.md:557` 之外的同类「处置声称」——本轮实测它**为假**，
说明处置表本身也需要跑一次「处置 vs 正文」的机械核对。
