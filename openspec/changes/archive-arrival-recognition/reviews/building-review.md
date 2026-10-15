# Building Review: archive-arrival-recognition（issue #26）

## Reviewer

**独立零记忆**：本对话不携带该 change 的任何历史。设计稿里的「实测 / 已复算 / 今天成立」一律当**待验证断言**，
凡能复算的都自己复算过。我是**审阅者**，与作者无关。

**读了**：`proposal.md` / `design.md`（§0–§8 全文）/ `specs/archive-awareness/spec.md` / `tasks.md` /
`reviews/{grill-design,grill-adversarial}.md` / `rounds/grill-adversarial-r1…r7.md`；
实现 `src/witnessloop/{gitutil,contract,checkcmd,policy,paths,constants,manifestcmd,evidence,hashing}.py`；
测试 `tests/{test_archive_arrival,test_archive_awareness,test_archive}.py` + `tests/{helpers,conftest}.py`；
`docs/gate.md` / `README.md` 的归档段。

**跑了**（命令与要点，全部可复算）：

1. `.venv/bin/python -m pytest -q` → **623 passed**（41.7s）。基线绿。
2. 自造 **20 个 scratch 仓**（`/tmp/arr26/battery/*`，每例一个干净仓，全部走**真 CLI**
   `.venv/bin/python -m witnessloop init/manifest build/check`）复跑 R1–R8 的构造 + 新攻击，
   驱动器 `/tmp/rev26/battery.py`；另有 `/tmp/rev26/attack_symdir.sh` 专测本次的头号发现。
3. 120 个已归档 change 的大仓下测 `check`：**退出码 0，耗时 0.94s**（`/tmp/arr26/battery/perf120c`）——
   `tasks.md` 4.6 / design §3 第 1 条的调用成本担忧**证伪失败**（不构成问题）。
4. 本仓自举：`.venv/bin/python -m witnessloop check --root . --base main --head HEAD` → 退出码 1，见 §5。
5. 直调 `contract.archive_arrivals` / `changed_change_ids` 于真 git 仓上做函数级探针（下面 §5 的第二形态）。

---

## Verdict

**CHANGES_REQUESTED（Round 5 复验后仍为此；只剩 1 条，且**不是**安全绕过）**

- **Round 1–4 的五条（H1 / H2 / H3+H4 / H5 / H6）全部确已修复** ✓：
  battery **`与设计预期不符：0/20`**；Round 2 的 V1–V5、Round 3 的 V6–V8 **全部判红**；
  Round 4 的 `h5_launder.py` 从 `EXIT=0` 变成 **`EXIT=1`**；`pytest` **633 passed**。
- **仅剩 1 条必须修改项（中危，非安全绕过）**：H6 的修复用了「队列项总数 ≤ `budget = 1024`」这一**数量**上界，
  它把**病态环路**与**合法的大到达目录**一起封顶 ⇒ **证据树 ≳1010 个文件的合法到达会被判成「不是到达」**，
  报「没有任何 change 目录」，**并且把本 change 要消灭的幽灵 active id 症状原样带回来**
  （实测 1015 文件的**纯归档 move** ⇒ `openspec/changes/big：change 目录不存在` ×9 项）。
  详见 R5-③ 与「Round 5：必须修改项」。

---

## 核对结果

### ① 设计 ↔ 实现逐条

| 设计条文 | 实现 | 结论 |
|---|---|---|
| **判据 1**：`merge-base(base,head)` 的树里该路径**完全没有 entry**（blob 也算有） | `checkcmd.py:77-88` 先算 `gitutil.merge_base` 并把 **`merge_base`** 传下去（不是 `base` ref）；`contract.py:248` 用 `view.entry(base_rev, directory) is not None` 拒绝（`gitutil.py:155-162` 用**不带尾斜杠**的 `ls-tree`，blob 也返回 1 行） | ✅ 与 `design.md:77-83`、`spec.md:28-36` 一致 |
| **判据 2**：head 里是 tree 且含**全部** `required_artifacts`；忽略 `""`/`"."` 退化名 | `contract.py:233`（过滤空/`.`）+ `:241-255`（`child.type != "tree"` 先排除 + `walk(head,dir)` 判 `<dir>/<a>` 路径存在）；`near_miss_archives`（`:284-309`）同名处理 | ✅ 一致（一处口径差见 ④⑶） |
| **判据 3**：到达组里没有记录的 `old_path` 落在 `<changes_root>/archive/**` | `contract.py:260-265`（`under_path(old, archive_root)`，覆盖任意深度） | ✅ 一致 |
| **判据 5（a)(b)**：`Ev(A)` 每项是**新 blob** 或**本次改名落点** | `_content_provenance_ok`（`contract.py:166-207`）+ `_is_reused`（`:210-216`）：`sha in base_blobs and path not in rename_dests` ⇒ 拒 | ⚠️ **基本形态一致，符号链接的目录目标处不一致**（见 ⑤ 与「必须修改项 1」） |
| **`Ev(A)` 三部分**：`HASHED_ARTIFACTS` 路径整体 + 每份 manifest 的 `report_path` 目标 + `<A>/reviews/**` | `_evidence_paths`（`contract.py:124-163`）：`:137-145` artifact 整体（tree ⇒ `walk` 其下全部；否则只加自身）、`:146-149` manifest glob、`:150-151` `reviews/**`、`:152-162` `report_path` 目标 | ✅ 三部分齐；`proposal.md`/`design.md` **不在**集内（`constants.py:87-90` 只有 `tasks.md`/`specs`）✅ |
| **空文件豁免** | `EMPTY_BLOB_SHA`（`contract.py:66`）+ `_is_reused` 首条（`:212`） | ✅（实测绿，见 ②） |
| **D4**：排除键含 `R`/`C` 的 `old_path` **与** `D` 侧的 `path`，且源目录须在 head 里已不存在 | `changed_change_ids`（`contract.py:312-374`）：`:335-349` 由**到达组**推 `moved_sources`（要求 `view.entry(head_rev, <changes_root>/<src>) is None`），`:350-359` 对**全部**记录的 `(old_path, path)` 求交后排除 | ✅ 一致（边界见 ⑤ 的第 6 条） |
| **D5**：豁免 = 记录属于某到达组 **且** `old_path` 落在 `<changes_root>/<active-id>/` 下 | `_archive_move_exempt`（`checkcmd.py:255-274`）：旧侧要求 `old.startswith(root+"/")` 且**不在** `archive/**` 下；新侧要求 `new` 落在某个到达目录下 | ✅ 一致（「把受保护文件搬进到达目录仍要事件」由 `test_F5` + 我的复跑印证） |
| **D2 对称性**：归档 target 走同一套证据门 | `checkcmd.py:101-138` 对每个 target 走同一组判定，无特判；target 只换 `directory`/`label`/`accepted_change_ids`（`contract.py:377-412`） | ✅ |
| **D7 注入式树读取器 + fail-closed** | `TreeView`（`contract.py:69-85`）/ `GitTree`（`gitutil.py:191-207`）；`checkcmd.py:86-96` 捕获 `GitError` ⇒ 报 finding + 非零退出 | ✅（但无用例钉住，见「必须修改项 3」） |

### ② 真实现复跑 R1–R8 的构造（构造 → 期望 → 实测）

驱动器 `/tmp/rev26/battery.py`（每例干净仓、真 CLI），末次整跑 `与设计预期不符：3/20`：
**17 条与设计预期一致（含天花板），3 条不符——全是新攻击。**

**必须绿（6/6 实测绿）**

| 构造 | 期望 | 实测 |
|---|---|---|
| 出生即归档（件齐、内容全新 + 改 `src/**`） | 绿 | `PASS(0)` ✓ |
| 纯 move（`R100`，内容与证据都在 base） | 绿 | `PASS(0)` ✓ |
| move + 同 diff 内**重建被 move 的 manifest**（`R<100`） | 绿、无幽灵 id | `PASS(0)` ✓ |
| `reviews/alias.md → reviews/grill-review.md`（A **之内**的符号链接，本仓钉绿布局） | 绿 | `PASS(0)` ✓ |
| 符号链接指向 `<changes_root>` **之外**的**被跟踪**文件 | 绿 | `PASS(0)` ✓ |
| 空文件（0 字节）在到达目录里 | 绿 | `PASS(0)` ✓ |

**必须红（10/10 实测红）**

| 构造 | 期望 | 实测 |
|---|---|---|
| R1 的 **F1**：整份 `cp -r` 现成归档 change + 只改 manifest 的 `change_id` | 红 | `FAIL(1)`，报「没有任何 change 目录」✓ |
| **对照**：只把报告/`specs` **逐字节复制**进新目录（不加符号链接） | 红 | `FAIL(1)` ✓（⇒ 下面 ⑤ 的攻击正是靠符号链接把这一条洗白的） |
| R2 的 **A2**：复制 + 给**一个**证据文件加一个字节 + 重跑 `manifest build` | 红 | `FAIL(1)` ✓ |
| R2 的 **A3**：源是**嵌套**归档目录 `archive/2026/10-15-old/`，整份 `cp` 成扁平新名 | 红 | `FAIL(1)` ✓ |
| R3 的 **A1**：把报告**挪出 `reviews/`**（放 change 目录根）+ 手写 manifest 指过去 | 红 | `FAIL(1)` ✓ |
| R3 的 **A3**：`specs` 换成**同名普通文件**、借用内容塞进去 | 红 | `FAIL(1)` ✓ |
| **N8**：把基准树里**已存在**的归档目录改名 + 改代码 | 红 | `FAIL(1)` ✓ |
| **N3**：往已存在的归档目录**新增**一个文件 + 改代码 | 红 | `FAIL(1)` ✓ |
| R5 的 **symlink_ev**：`tasks.md`/`specs`/报告 = 指向现成 change 里**文件**的符号链接 | 红 | `FAIL(1)` ✓ |
| R7 的 **gitlink**：到达目录 `reviews/` 下出现 `160000` | 红 | `FAIL(1)` ✓ |

**补充复跑（我自己加的）**

| 构造 | 期望 | 实测 |
|---|---|---|
| **D4 形态 ii 的 R3-A4 版**：`git mv changes/z archive/2026-10-15-z` + 把 `tasks.md` 整体重写 | 绿、**无**幽灵 active id | `FAIL(1)`，但**无**「change 目录不存在」——到达被认出（`1 个 change 目录`），红的是我没重建 manifest 的 `tasks_hash`/stale。⇒ **D4 的 `D` 侧键成立** ✓ |
| **D4 极端版**：把被搬的**每一个**文件都整体重写（git 全报 `D`+`A`，无一条改名配对） | 设计未明写 | `FAIL(1)`：到达被认出（`2 个 change 目录`）但**幽灵 id `z` 回来**（`openspec/changes/z：change 目录不存在`）⇒ 见「建议 4」（非回归，今天也红；与 `design.md:283-285` 自认的「只被修好了一档」一致） |
| **完全旁路**（已登记边界）：把现成证据的**副本放在 `<changes_root>` 之外**（`docs/shipped/A/**`）再整份 `cp` 进来 | 绿（能力边界，非本 change 射程） | `PASS(0)` ✓（实测确认边界**如实**） |
| 到达目录里一个**悬空**符号链接（`spec.md:75` 的 fail-closed 面） | 红 | `FAIL(1)` ✓（行为对，但**无用例**，见「必须修改项 3」） |
| 120 个已归档 change 的大仓下 `check` | 无性能问题 | `PASS(0)`，**0.94s** ✓ |

### ③ 天花板与两条已知边界（实测确认）

- **逐字节天花板（§8 Q4 / `design.md:177-190`）**：整份复制后再给 `Ev(A)` 里**每一个**文件各追加一个换行
  + 官方 `manifest build` 重算哈希 ⇒ **实测 `PASS(0)`**。✅ **与文档一致**（本档是「不要求红」，
  实测确认它确实是绿的）。⚠️ **但它不是本 change 的天花板**：见 ⑤ 的第 1 条——存在一条
  **一个字节都不用改**的更进一步绕过。
- **完全旁路（`<changes_root>` 之外另有副本）**：实测 `PASS(0)` ✅ 与 `spec.md:100-103` / `gate.md §7` 一致。
- **误伤面**：实测确认两条明写的误伤——（i）原样复制兄弟 change 的 `specs/**`（`spec.md:104-108`）；
  （ii）报告正文用同一份常量样板（我第一版性能构造里三个 change 共用同一份 `grill-review.md` 就触发了
  「没有任何 change 目录」）。**误伤方向是 fail-closed（拒绝），与文档一致**。

### ④ 测试质量

**真的在验行为的部分（认可）**：

1. `tests/test_archive_arrival.py` 的 19 条是**纯函数 + 假树**，直接打 `archive_arrivals` /
   `change_targets` / `changed_change_ids` 的判红判绿，不依赖文案；`FakeTree`（`:31-79`）能造出真 git
   里难造的形状（base 同路径 blob、gitlink、符号链接）。**判据 1/2/3/5 的主干都有正反用例**。
2. e2e（`test_archive_awareness.py` F 节）大量用**退出码**断言，配「同类构造必须绿」的对照
   （`test_F4` 红 vs `test_F2/F3/F1` 绿）⇒ 不是「写了断言但实现可绕过」。
3. 计数类断言（`:498` 报 2、`:386` 恰 1 项）配了反例钉子（`test_report_still_says_zero_change_dirs_for_a_docs_only_diff`），
   不是空真。
4. 既有测试的改写与 `design.md §5.2` 的清单**逐条对得上**：`:274→test_rebuilding_a_moved_manifest_in_the_same_diff_is_accepted`
   （语义反转 ✓）、`:494→test_the_summary_counts_directories_not_deduped_ids_on_a_tie`（改用 R3 给的替代配方 ✓）、
   `:600→test_N6_partial_move_into_an_existing_archive_dir_keeps_the_source_validated`（语义反转 ✓）、
   `:109` 删除 ✓、A 节迁移到新文件 ✓；「不要误改」的三条（`:541` / `:577` / `:378`）确实保持原样 ✓。

**问题（都在「必须修改项 3」里）**：

1. **`tests/test_archive_awareness.py:49-51` 的 `_targets()` 仍是旧签名**
   （`contract.change_targets(root, policy, changes)`，3 个参数；现行是 6 个）。它只被
   `:440 _disabled_alias_order_case()` 调用，而后者名字不以 `test_` 开头 ⇒ **pytest 不收集**。
   ⇒ 这是**一坨指向已删接口的死代码**：一旦有人把它改名成 `test_…`，立刻 `TypeError`。
   `design.md:463-465` 把「助手改为注入假树，按新接口改写」列进**必须改写**清单，**这一条没落**。
   同文件 `:432 _removed_alias_order_case()` 也是死占位。
2. **`tasks.md` 里承诺的用例有 4 处没有落地**（逐条核对）：
   - `tasks.md` **2.6c**（基准 revision 与 `changed_files` 同源的反例构造）—— 全仓 `grep merge_base tests/` 无命中，
     e2e 里**没有**任何用例能杀死「把 `merge_base` 换回 `base`」这个变异（`checkcmd.py:77-88` 的行为因此**无钉**）；
   - `tasks.md` **2.8**（树读不出来 ⇒ fail-closed）—— 无用例（实现见 `checkcmd.py:86-96`）；
   - `tasks.md` **2.9⑬②**（链接悬空 / 目标未被跟踪 ⇒ 红）—— 无用例（实现见 `contract.py:195-197`；我用 scratch 仓实测确实红）；
   - `tasks.md` **2.9⑬** 的正向半边（指向 `<changes_root>` **之外被跟踪**文件 ⇒ 绿，`spec.md:358-359` 明写）——
     无用例（我实测绿）。
3. 一处**口径不准**（设计文本 vs 实现，可产生误导性红）：`spec.md:37-39` 说判据 2「判定语义 SHALL 与契约门**完全一致**」，
   但契约门用**工作树** `.exists()`（`contract.py:430-436`），判据 2 用 **head 树**。
   差别只在「必需件是**空目录**」时：`reviews/` / `specs/` 若为空目录，契约门判**存在**、判据 2 判**不存在**
   ⇒ 出生即归档的作者会看到「没有任何 change 目录 + `archive/<name>` 缺 `reviews`」，而不是「空目录」。
   仓库自己知道这件事（`tests/test_archive_awareness.py:81-89` 的 `_tracked_review_placeholder` 就是绕它），
   但**没写进 spec 的「一处明写的偏离」**（该处只写了 `""` / `"."`）。

### ⑤ 我新造的绕过尝试（成功/失败都写）

**1. ✅ 成功（高危，头号发现）：符号链接的**目录**目标不被展开 ⇒ 判据 5 整体失明**

- **构造**（`/tmp/rev26/attack_symdir.sh`，仓在 `/tmp/arr26/battery/case_symlink_to_inner_dir`）：
  1. base 上放一份**证据齐全**的归档 change `archive/2026-09-30-old/`（三份真审阅报告 + 三份 manifest + `specs/`）；
  2. feature 上新建 `archive/2026-10-15-new/`，把上面那份的 `reviews/*.md`、`specs/retry/spec.md`
     **逐字节 `cp`** 进来，`proposal.md`/`design.md`/`tasks.md` 自己写（`tasks.md` 是**唯一**的新证据字节）；
  3. 用**官方** `manifest build` 产证据（`change_id` 已是新目录名，hash 绑的就是**借来的字节**）；
  4. 把 `reviews/` 与 `specs/` 的**内容**挪进 `A/_r`、`A/_s`，再
     `ln -s _r reviews`、`ln -s _s specs`（**链接文本是目录名**，目标是 `A` **之内**的目录）；
  5. 改 `src/app.py`。
- **实测**：

```
$ cmp <victim>/reviews/grill-review.md <A>/_r/grill-review.md   # 三份报告 + specs 全部
  reviews/grill-review.md: 与既有归档 change 逐字节相同
  reviews/grill-adversarial.md: 与既有归档 change 逐字节相同
  reviews/building-review.md: 与既有归档 change 逐字节相同
  specs/retry/spec.md: 逐字节相同
$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，13 个变更文件，1 个 change 目录
  change：2026-10-15-new（归档）
check：通过 ✓
EXIT=0
```

- **对照**（同一构造、只是**不**加符号链接）：`check：未通过 ✗ —— src/app.py … 本次 diff 里没有任何 change 目录`（红）。
  ⇒ 判据 5 的效力**完全**依赖「证据文件的路径就是它自己」这一隐含假设，符号链接的**目录**目标把它整个打穿。
- **根因（两处，同一成因）**：
  - `contract.py:191-204`：符号链接分支里，目标**落在 `A` 之内**时只做 `todo.append(target)`（`:203`），
    而下一轮对**目录条目**走 `:205 _is_reused(entry.sha, …)`——`entry` 是 tree，`entry.sha` 是**tree sha**，
    而 `base_blobs` 来自 `view.walk`（`:234`，`ls-tree -r`，**不含 tree 行**）⇒ **恒不命中** ⇒ 目录内容**从未被逐个比对**。
  - `contract.py:198-202`：目标**落在 `A` 之外**时同样只比 `target_entry.sha`——目标若是**目录**，
    比的就是那个 tree sha（同一条恒不命中）。
  - 实现**没有**做 `spec.md:72` 明文要求的「**目标是目录 ⇒ 其下全部文件逐个比对**」。
- **第二形态（函数级，同一根因）**：`A/reviews → ../2026-09-30-old/reviews`（**A 之外**的目录，指向现成 change 自己的证据目录）：

```
$ python -c "… contract.archive_arrivals(changes, pol, view, merge_base, 'HEAD') …"
archive_arrivals ⇒ [('2026-10-15-new', [])]      # 该目录里每一份文件都与基准树 changes_root 里的现成证据逐字节相同
```

  （这一形态我没做成完整 e2e `check`——它要求把 manifest 的 `change_id` 写进受害目录，会牵出覆盖/事件那一摊；
  故按**函数级**记，端到端留作未验证项。

**2. ✅ 成功（低危）：`spec.md:64` 的「`<A>` 下**任何位置**出现 gitlink ⇒ fail-closed」未落实**

- 构造：到达目录里放一个**非证据路径**的 gitlink（`git update-index --add --cacheinfo 160000,<sha>,A/vendor/sub`），其余全新。
- 实测：`check：通过 ✓`（`PASS(0)`）；而同一构造放在 `A/reviews/mod`（`Ev(A)` 内）⇒ 红 ✓。
- 根因：`contract.py:189-190` 的 `if entry.is_gitlink: return False` **只对 `todo` 里的条目**（= `Ev(A)` 及其解析目标）生效，
  没有「`<A>` 下任何位置」的扫描。⇒ **规范比实现宽**（`spec.md:64` 用了 `SHALL`）。

**3. ❌ 失败（照设计拒绝）**：`proposal.md`/`design.md` 逐字节复制（不在 `Ev(A)`）⇒ 绿（设计如此）；
   报告挪出 `reviews/`、`specs` 换形态、嵌套源、混源、只动一处、改名既有归档目录、往既有归档目录加文件、
   指向现成 change **文件**的符号链接、悬空链接、gitlink（在 `Ev(A)` 内）⇒ **全部红**，与设计逐条一致。

**4. ❌ 失败（性能担忧证伪）**：120 个已归档目录 + 1 个新到达 ⇒ `check` 0.94s、退出码 0。
   `archive_arrivals` 对已存在的目录每个只要 1 次 `ls-tree`（判据 1 先短路），新增候选才走贵的那条路。

---

## 必须修改项

**1）（高危）符号链接的「目录目标」必须按其下全部文件展开比对 —— 现在它整份复制都能过**

- 位置：`src/witnessloop/contract.py:191-204`（`_content_provenance_ok` 的符号链接分支）、
  `:234`（`base_blobs` 只含非 tree 行的前提）、`src/witnessloop/contract.py:137-145`（`_evidence_paths` 对
  `specs` 是符号链接时只收链接自身）。
- 违反对应：`spec.md:72-74`（「目标是目录 ⇒ 其下全部文件逐个比对」「与 `cp` 进来同结论」）、
  `design.md:121-124`、`docs/gate.md:331-332`（「以及**符号链接**指向基准树里现成 change —— **一律不授予**」）、
  `README.md:150-151`。
- 复现（真 CLI，一步步可重放）：`bash /tmp/rev26/attack_symdir.sh`；成品仓
  `/tmp/arr26/battery/case_symlink_to_inner_dir`：

```
$ cd /tmp/arr26/battery/case_symlink_to_inner_dir
$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，13 个变更文件，1 个 change 目录
  change：2026-10-15-new（归档）
check：通过 ✓      # 三份真报告 + specs 一个字都没改
```

- 期望修法（与 `spec.md:72-74` 一致）：解析目标时按 `head` 树判定目标的类型——**是 tree ⇒ 把其下全部文件
  逐个并入 `todo`**（递归到不动点、`seen` 防环；落在 `A` 之内与之外都要做），是 blob 才走现有的
  `_is_reused`。⚠️ 修完请把 `N22` 的构造扩成「目标是**目录**」的两个变体（`A` 之内 / `A` 之外），
  并给「合法 `reviews → 子目录`」补一条**必须绿**的对照（`spec.md:77` 已要求不得一刀切禁符号链接）。

**2）（低，但是明文 `SHALL`）`<A>` 下**任何位置**的 gitlink 未 fail-closed**

- 位置：`src/witnessloop/contract.py:189-190`（只查 `Ev(A)` 成员）。
- 违反对应：`spec.md:63-64`「**`<A>` 下任何位置出现 gitlink ⇒ fail-closed**（取宽的一侧）」。
- 复现：

```
$ cd /tmp/arr26/battery/case_gitlink_outside_evidence
$ git ls-tree -r HEAD -- openspec/changes/archive/2026-10-15-g | grep commit
160000 commit 293b5a81c32228c6933ccbb66084c62ca9e80501  openspec/changes/archive/2026-10-15-g/vendor/sub
$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：通过 ✓      # 规范说这里应当 fail-closed
```

**3）（低）`tasks.md` 承诺的用例/任务未落 + 死代码**

- `tests/test_archive_awareness.py:49-51`：`_targets()` 仍是 3 参旧签名（现行 `contract.change_targets` 要 6 个），
  只被同样不收集的 `:440 _disabled_alias_order_case()` 调用；`:432 _removed_alias_order_case()` 同。
  ⇒ `design.md:463-465`（「必须改写」第 4 条）**未落**。`grep -rn "_targets(" tests/` 可见全部调用点。
- 缺 4 条用例（对应 `tasks.md` 2.6c / 2.8 / 2.9⑬② / 2.9⑬ 正向半边，见 ④⑵）：
  `grep -rn "merge_base\|树读不出来\|悬空" tests/test_archive_arrival.py tests/test_archive_awareness.py` → 0 命中。
  其中 **2.6c 最要紧**：`spec.md:238-242` 有专门 Scenario，而 e2e 里没有任何用例能杀死
  「把 `checkcmd.py:77` 的 `merge_base` 换回 `base`」这个变异。

**4）（低）`docs/gate.md` 缺一条 design 明列的登记**

- `design.md:365-368`（§3 第 5 条义务）要求 §6 的已知边界补「**树不可读 ⇒ fail-closed**」；
  `grep -n "树不可读\|ls-tree\|merge-base" docs/gate.md` → 0 命中（「模板放 `changes_root` 之外」与「扫描面」
  已在 §5.1.1/§7 落地，「报告可放 `reviews/` 之外」的既有宽松面仍只在 §3）。

---

## 未验证项

1. **浅克隆下「`merge-base` 求得出但 `ls-tree` 失败」这一独立面**（`design.md:384`、R2/R3 的未验证项 ③）——
   我没能构造出这个失败模式；`checkcmd.py:86-96` 的 `except GitError` 分支**未实测**触发过。
2. **merge commit 形态**（设计多处标注「未取得可判定结论」）——我有意没测（`scope.pr_paths` 那套是既有机制，
   与本 change 正交）。
3. **①-第二形态的完整 e2e**：`A/reviews → A 之外的目录` 我只做到函数级 `archive_arrivals ⇒ arrived=True`；
   完整 `check：通过` 需要把 manifest 的 `change_id` 写进受害目录（覆盖 + 解释事件），未构造。
   ⚠️ 但**同一根因**的第一形态已是完整 e2e 绿，修法也覆盖这一形态。
4. **`policy.review_manifest_glob` 覆写成自定义 glob** 的端到端（`design.md:111-112` 说自定义 glob 本就不可用）、
   **`required_artifacts` 覆写成多段名**的端到端（`design.md:86`、R3 的未验证项 ⑥）。
5. **接入方（asterwynd）的真实 diff 数字**（`R068/R069/R070/R090`、33/14/16 文件）——本工作区**不可复算**，
   与 `design.md:542-544` 的声明一致。
6. **本 change 自己的门禁**：`check --root . --base main --head HEAD` 现在**红**（退出码 1），
   其中 4 项是「`archive-arrival-recognition` 缺三份 manifest」——这是**流程状态**（本轮 building 证据正是产物），
   另 6 项是 `archive-awareness` / `confirm-gate-fail-closed` 的「审阅的是旧 revision」，由
   **本分支同时压着三个未发布 change** 且本 change 改动了 `README.md` / `docs/gate.md` 造成，
   与到达判定无关（`stale` 维度，`design.md:229-236` 已显式排除）。⇒ 我**没有**据此判红。

---

## 建议（不阻塞）

1. **`archive_arrivals` 在一次 `check` 里被算了两遍**：`checkcmd.py:87` 算一次、`:88` 的
   `change_targets`（`contract.py:387`）内部又算一次，`base_blobs` 也跟着重算一遍。120 目录下总耗时
   0.94s 所以**不构成问题**，但把 `arrivals` 作为参数传进 `change_targets` 可以省掉一整轮 `ls-tree`，
   也免掉「两份结果不同步」的长期风险。
2. **`_evidence_paths` 的 manifest 匹配用 `fnmatch`（`contract.py:148/153`），证据门用 `Path.glob`（`contract.py:475`）**：
   `fnmatch` 的 `*` **跨 `/`**，`Path.glob` 的不跨 ⇒ 自定义 glob 下两边会分叉。当前方向是
   `fnmatch` 更宽（更严），**不构成绕过**，但把两处统一到 `pathutil.matches` 可以消掉这个隐患。
3. **`_evidence_paths` 里「目标并入 `Ev(A)`」的过滤**（`contract.py:161`）要求
   `under_path(resolved, directory)`；`spec.md:73-74` 的措辞是「目标路径 SHALL 并入 `Ev(A)`」。
   现状与「A 之外的目标按 blob 比对」自洽，但建议在注释里点明「**A 之外的目录目标也要展开**」——
   这正是「必须修改项 1」漏掉的那半句。
4. **`design.md:399-401`（§5.1 第 2b 条）的措辞宜加限定**：实测「`git mv` + 把**每一个**被搬文件都整体重写」
   （git 全报 `D`+`A`、无一条改名配对）时，`changed_change_ids` 仍会返回源 id ⇒ 报「change 目录不存在」⇒ 红
   （`/tmp/arr26/battery/d4_all_rewritten`）。这与 `design.md:283-285` 自认的「只被修好了一档」一致、
   且**今天也红**（非回归），但 2b 现在读起来像是覆盖了「整体重写」这一整类。
   建议在 2b 后加一句「**前提：到达组里至少有一条改名记录可解析出源 id**」。
5. **`rounds/**` 不在 `stale_exempt_paths` 里**（`policy.py:86-92` 只豁免 `.witnessloop/**`、
   `<root>*/reviews/**`、`<root>*/workflow-events.jsonl`、`archive/**`）：把 R1–R7 从 `reviews/` 挪到 `rounds/`
   躲开了孤儿规则（`design.md:525` 的理由成立），代价是**这些逐轮报告从此落在 stale 判定面内**——
   事后补一轮 R8/R9 就会让本 change 的三份 manifest 一起判「审阅的是旧 revision」。
   建议把这条代价写进 `design.md §7` 的布局说明（并在收官时记得**最后**再重建 manifest）。
6. **判据 2 的「与契约门完全一致」宜改成「除空目录外一致」**（见 ④⑶）：`spec.md:37-39` 的措辞会让人以为
   两者逐字等价，而 `reviews/` / `specs/` 为空目录时结论相反，且**只会多报红**（不是安全面）。
   顺手可以在 `_require_change` 的近失文案（`checkcmd.py:234-240`）里把「空目录」也提一句。

---

# Round 2（复验）

**范围**：只复核作者声明的 4 项修复 + 找新缝。**零记忆**不适用（我持有 Round 1 的结论），
但**所有结论都重新实测**；作者声明一律当**待验证断言**。

**跑了**：

1. `.venv/bin/pytest -q` → **626 passed**（27.7s，Round 1 是 623 —— 多出的 3 条正是 `F9/F10/F11`）。
2. `bash /tmp/rev26/attack_symdir.sh`（Round 1 的头号构造，**未改动**）。
3. `/tmp/rev26/battery.py`（Round 1 的 20 个 case，**未改动**；含 3 条当时判绿的「新攻击」）。
4. **新造 5 条变体**（`/tmp/rev26/variants2.py`，全新仓）：符号链接链 / 目录链接混入新文件 /
   `reviews` 链到 `A` **之外**的目录 / gitlink 藏深层子目录 / manifest 走符号链接 + `report_path` 在 `reviews` 之外。
   ⚠️ 纪律：每个变体里**除故意借来的那部分**，其余文件一律带唯一标记 —— 否则红只是「常量样板报告撞车」
   这条既有误伤面，证明不了任何事（我第一版变体就踩了这个坑，已重做）。
5. 三条新测试的**读码 + 变异分析**（它们能不能杀死「把修复回退掉」的变异）。
6. `design.md §7.5` 的处置表逐条对照。

---

## R2-① 作者声明的 4 项修复：逐条复核

| # | 声明 | 复核方法 | 结论 |
|---|---|---|---|
| **H1** | `Ev(A)` 展开器重写为「目录与符号链接都展开到文件」 | 原构造 `attack_symdir.sh` 复跑；读 `contract.py:124-196` | ✅ **成立**：原构造现在 `0 个 change 目录` + 退出码 1（拒绝）；实现确实对 `entry.type == "tree"` 入队其下文件（`:177-178`）、对 `entry.is_symlink` 解析后入队（`:171-175`），只有**落到普通文件**的项才 `_is_reused`（`:180-183`） |
| **M2** | 比对前先扫 `<A>` 全域，任何 gitlink ⇒ 不授予 | `contract.py:148` + 我 Round 1 的构造复跑 | ✅ **成立**：`if any(row.is_gitlink for row in view.walk(rev, directory)): return False`；Round 1 判绿的「gitlink 在 `A/vendor/sub`」现在 `FAIL(1)` |
| **M3** | 新增 `F9/F10/F11`、删掉 `_targets()` 死代码 | 读 `tests/test_archive_awareness.py:820-905`、`grep _targets` | ⚠️ **部分成立**：三条用例确有且**真的在验行为**（见 R2-④）；`_targets()` 的**定义**已删，但它唯一的调用者 `_disabled_alias_order_case`（`:438`）**还在**，现在调用一个**已不存在的函数** ⇒ 死代码没清干净（见「必须修改项 2」） |
| **M4** | `docs/gate.md §5.1.1` 补「树不可读 ⇒ fail-closed」 | `grep -n "树读不出来" docs/gate.md` | ✅ **成立**：`docs/gate.md:343`「**树读不出来 ⇒ fail-closed**：到达判定要读 `merge-base(base, head)` 的树与 head 的树；…」 |

## R2-② 原构造复跑（原始输出要点）

**A. `bash /tmp/rev26/attack_symdir.sh`（Round 1 的 H1 构造，一字未改）**

```
=== CHECK（攻击后） ===
check：基线 main...HEAD，13 个变更文件，0 个 change 目录
check：未通过 ✗（1 项）
  1. src/app.py：src/app.py 属于必须挂 change 的路径……本次 diff 里没有任何 change 目录……
EXIT=1
```
（Round 1 此处是 `1 个 change 目录` + `check：通过 ✓`。）⇒ **H1 关闭**。

**B. `/tmp/rev26/battery.py`（20 个 case）**

```
OK green 出生即归档 / 纯 move / move+重建 manifest / A 内 alias.md / 指向 changes_root 外被跟踪文件 /
         空文件豁免                                                  （6/6 绿）
OK red   R1-F1 纯 cp / 对照(只复制字节) / R2-A2 / R2-A3 / R3-A1 / R3-A3 / N8 / N3 /
         R5 symlink_ev / R7 gitlink(reviews)                          （10/10 红）
OK 天花板 R3-A2（不要求红）                                          （实测绿，与文档一致）
OK 新攻击 gitlink 非证据位置 / 符号链接→A 内目录 ×2                    （3/3 红 —— Round 1 全绿）
与设计预期不符：0/20
```
⇒ 修复**没有**误伤那 6 条「必须绿」，也**没有**动天花板（仍绿，与 `spec.md:95-99` 一致）。

## R2-③ 新造的 5 条变体（`/tmp/rev26/variants2.py`，真 CLI，全部新仓）

| # | 构造 | 期望 | 实测 |
|---|---|---|---|
| **V1** | `specs -> s1 -> s2`（链式符号链接，`s2` 真目录里是**借来的** specs） | 红 | **`FAIL(1)`**（`0 个 change 目录`）✓ 递归展开生效 |
| **V2** | `specs` 指向目录，目录里**混入一个自己写的新文件** + 借来的 spec | 红 | **`FAIL(1)`**（`0 个 change 目录`）✓ 新文件不构成豁免 |
| **V3** | `reviews` 指向 **`A` 之外**的目录（= 现成 change 自己的 `reviews/`，报告是 base 里的字节） | 红 | **`FAIL(1)`**（`0 个 change 目录`；另有 3 条「受保护路径被写入」，来自我改写受害 manifest 的 `change_id`）✓ 外侧半边也修好了 |
| **V4** | gitlink 藏在 `A/vendor/deep/nested/sub` | 红 | **`FAIL(1)`**（`0 个 change 目录`）✓ 全域扫描生效 |
| **V5** | `reviews/*.manifest.json` 是**符号链接**（真身 `_m/*.manifest.json`），其 `report_path` 指到 `reviews/` **之外**（`A/stolen/`，三份**逐字节借来**的报告） | 红 | **`PASS(0)` —— `check：通过 ✓`** ❌ **新缝（H2）** |

## R2-④ 三条新测试：真的在验行为吗？（含变异分析）

- **`test_F9_symlinked_directory_in_the_arrival_is_rejected`（`:820-849`）**：构造 `reviews -> _r`，
  `_r/grill-review.md` 是受害者报告的**逐字节**副本；断言 `EXIT_FAIL` + `"没有任何 change 目录" in err`。
  **变异分析**：把展开器回退成「只比 sha」⇒ `A/_r` 是 tree、tree sha 不在 `base_blobs` ⇒ 到达被授予 ⇒
  该构造**没有 manifest** ⇒ 报「缺少 review manifest」而**不是**「没有任何 change 目录」⇒ **断言失守**。
  ⇒ **能杀死回退变异，是在验行为**（不是验文案）。✅
- **`test_F10_gitlink_anywhere_under_the_arrival_is_rejected`（`:852-869`）**：gitlink 放在**非证据位置** `A/mod`；
  同一对断言。**变异分析**：删掉 `contract.py:148` 的全域扫描 ⇒ 到达被授予 ⇒ 报「缺少 review manifest」⇒ 断言失守。✅
  （小瑕疵：用的是 `'d'*40` 这种**不存在的 sha**，对 `ls-tree` 无影响，但不如真 sha 直观。）
- **`test_F11_arrival_judgment_uses_merge_base_not_the_base_ref`（`:872-905`）**：feature 上出生即归档，
  随后 **main 也前进**并加**同名**目录 ⇒ `base` 原树里有、`merge-base` 树里没有。
  **变异分析**：把 `checkcmd.py:77-88` 传的 `merge_base` 换回 `base` ⇒ 判据 1 不成立 ⇒ 到达不被认出 ⇒
  报「没有任何 change 目录」⇒ 断言失守。✅ 这是 Round 1 我点名的最要紧的那条缺口（`tasks.md` 2.6c）。
  ⚠️ **但它只断言「不出现那句话」，不断言退出码**——到达被认出但**因别的原因红**时它照样通过。
  钉住 merge-base 这一条够用，只是比其它「必须绿」用例弱一档（建议补 `assert code == C.EXIT_PASS`）。
- ❗ **三条新用例都不覆盖 H2 的形状**（manifest 走符号链接 + `report_path` 在 `reviews/` 之外）。

## R2-⑤ H2（新缝，高危）：`report_path` 只在 manifest 的**树路径**匹配 glob 时才被解析

**根因（一行）**：`src/witnessloop/contract.py:184`

```python
if under_path(path, directory) and fnmatch.fnmatch(path[len(directory) + 1:], manifest_glob):
    ... 解析 report_path、queue.append(resolved)
```

`path` 是**展开之后到达的那个文件的真实树路径**。manifest 若是**符号链接**（`reviews/x.manifest.json -> ../_m/x.manifest.json`），
队列里处理的是真身 `_m/x.manifest.json` ⇒ `fnmatch("_m/x.manifest.json", "reviews/*.manifest.json")` = **False**
⇒ 这段代码**跳过** ⇒ 该 manifest 的 `report_path` 目标**永远不进比对集**。
而证据门（`Path.glob`，跟随符号链接）照样能读到那份 manifest，并按 `report_path` 去读**借来的报告**。

**违反对应**：`spec.md:59-60`（`Ev(A)` 第二部分：「`policy.review_manifest_glob` 命中的**每一份 manifest**，
**以及每份 manifest 的 `report_path` 解析出的那个文件`」——这里那份 manifest **确实被 glob 命中**（路径就叫
`reviews/grill.manifest.json`），所以它的 `report_path` 目标 **SHALL** 进集）；
`design.md:108-109` 与 `design.md:211`（「第 5 条现在**按 `report_path` 取证据** ⇒ 它**不再是**判据 5 的旁路」）；
`docs/gate.md:329-330`。

**完整复现**（`/tmp/rev26/variants2.py` 的 `v5_manifest_symlink_report_outside_reviews`，成品仓在
`/tmp/arr26/battery/v5_manifest_symlink_report_outside_reviews`）：

```
$ cd /tmp/arr26/battery/v5_manifest_symlink_report_outside_reviews
$ for f in grill-review.md grill-adversarial.md building-review.md; do
    cmp openspec/changes/archive/2026-09-30-old/reviews/$f \
        openspec/changes/archive/2026-10-15-new/stolen/$f && echo "$f 逐字节相同"; done
grill-review.md 逐字节相同 / grill-adversarial.md 逐字节相同 / building-review.md 逐字节相同

$ ls -l openspec/changes/archive/2026-10-15-new/reviews/
building.manifest.json -> ../_m/building.manifest.json
grill-adversarial.manifest.json -> ../_m/grill-adversarial.manifest.json
grill.manifest.json -> ../_m/grill.manifest.json

$ python -c "import json;print(json.load(open('openspec/changes/archive/2026-10-15-new/_m/grill.manifest.json'))['report_path'])"
stolen/grill-review.md

$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，14 个变更文件，1 个 change 目录
  change：2026-10-15-new（归档）
check：通过 ✓
EXIT=0
```

**判据 5 实际比了哪些文件**（把 `contract._is_reused` 打桩后直调 `archive_arrivals`）：

```
   compared: tasks.md                                 reused=False
   compared: specs/retry/spec.md                      reused=False
   compared: _m/grill.manifest.json                   reused=False
   compared: _m/grill-adversarial.manifest.json       reused=False
   compared: _m/building.manifest.json                reused=False
arrivals: [('2026-10-15-new', [])]
```

⇒ `A/stolen/*.md`（三份**逐字节借来**的审阅报告）**一次都没进比对**。

**对照（证明那份借来的文件正是门禁真正消费的证词）**：把 `A/stolen/grill-review.md` 换成一份**不合规**的
短 grill 报告（2 条决策）并同步 `report_hash` ⇒

```
check：未通过 ✗（1 项）
  1. openspec/changes/archive/2026-10-15-new/stolen/grill-review.md：`## Confirmed Decisions` 只有 2 条，少于硬门槛 3 条
```

⇒ 通过/不通过**完全取决于 `A/stolen/` 里那份文件**，而它正是从既有归档 change 逐字节搬来的。

**与 H1 的关系**：同一类（`Ev(A)` 由**路径**推导，路径一旦被符号链接「挪位」就有条目出圈），
修 H1 时把「根可达的目录」展开到文件了，但**`report_path` 这条推导链仍以「manifest 的树路径匹配 glob」为前提**。
⇒ 建议的修法见「必须修改项 1」。

## R2-⑥ `design.md §7.5` 处置表与我的复验结论对照

| §7.5 的说法 | 我的复验 |
|---|---|
| 「Verdict = CHANGES_REQUESTED，1 条高危 + 3 条低危，均已修复」 | H1 ✅ 已修；M2 ✅、M4 ✅；M3 ⚠️ 只做了一半（见「必须修改项 2」）⇒ **不能写「均已修复」** |
| H1 处置：「重写 `Ev(A)` 展开器……新增 `test_F9`」 | ✅ 与实现/用例一致；但 **未覆盖** H2 的形状 |
| M3 处置：「新增 `test_F11` ……；删死代码」 | F9/F10/F11 ✅ 三条都在且真在验行为；**死代码未删净**（`_disabled_alias_order_case` 现在调用已删除的 `_targets`） |
| 引用的 battery 输出（`6 条全绿 / 12 条全红 / 天花板绿 / 0/20`） | ✅ 与我复跑的原样输出一致（我给的是同一批 case 的实测） |
| （未提及）`tasks.md` 2.8 树不可读、2.9⑬② 悬空链接、2.9⑬ 正向半边 三条用例 | ⚠️ **仍未落**（`grep -n "dangling\|树读不出来\|GitError" tests/test_archive_*.py` → 0 命中） |

## Round 2：必须修改项

**1）（高危，新）`report_path` 的解析不得以「manifest 的**树路径**匹配 glob」为前提**

- 位置：`src/witnessloop/contract.py:184`（`if under_path(path, directory) and fnmatch.fnmatch(path[len(directory) + 1:], manifest_glob):`）；
  配套 `:151-156`（`roots` 的 manifest 来源）。
- 违反对应：`spec.md:59-60`、`design.md:108-109` / `:211`、`docs/gate.md:329-330`。
- 复现：`/home/happy/wl-wt/archive-arrival-recognition/.venv/bin/python /tmp/rev26/variants2.py v5`；或直接
  `cd /tmp/arr26/battery/v5_manifest_symlink_report_outside_reviews && .venv/bin/python -m witnessloop check --root . --base main --head HEAD`（上面有完整输出）。
- 期望修法（建议）：**凡被访问到、且其内容被 json 解析为对象的 manifest（不论是以什么路径到达的），
  都要接着把 `report_path` 目标入队**——即把 `:184` 的判据从「路径匹配 glob」改成
  「这个文件**是一份 manifest**」。判定「是不是 manifest」可沿用**起点**信息：从 `roots` 里那批
  「按树路径匹配 glob 的 manifest 路径」出发，沿符号链接/目录展开时**记住来源**（或在出队时比较
  `entry.sha` 与已登记 manifest 的 sha）。
  ⚠️ 修完请补一条**必须红**用例：`reviews/*.manifest.json` 是符号链接 + `report_path` 指向 `reviews/` 之外
  （即 H2 的形状），并确认 `test_F9` 那种「`reviews` → 目录」的形状仍然红。

**2）（低）M3 只做了一半：死代码没删净 + 三条用例仍未落**

- `tests/test_archive_awareness.py:438` `_disabled_alias_order_case()` 现在调用
  **已被删除**的 `_targets`（`:453-454`）⇒ 一旦有人把它改名成 `test_…`（pytest 只收集 `test_` 前缀），
  立刻 `NameError`。同文件 `:430 _removed_alias_order_case()` 也是死占位。建议两段一并删掉，
  把「别名与顺序无关」搬到 `tests/test_archive_arrival.py`（那里已有等价覆盖）。
- 仍缺 3 条用例（`tasks.md` 2.8 / 2.9⑬② / 2.9⑬ 正向半边）：
  `grep -n "dangling\|悬空\|树读不出来\|GitError\|未被 git 跟踪" tests/test_archive_arrival.py tests/test_archive_awareness.py` → 0 命中。
  三条的行为我都实测过是对的（悬空链接 ⇒ 红；指向 `changes_root` 之外被跟踪文件 ⇒ 绿；树不可读 ⇒ `checkcmd.py:86-96` 报错退出），
  但**没有钉子**。

## Round 2：未验证项

1. H2 的**修法**我没给实现（只给方向）；修完需要重新复跑本节的 V1–V5 + `battery.py` 全量。
2. 我**没有**再找「`report_path` 之外的推导链」还有没有别的同类缝（例如 `<A>/reviews` 这个**根**本身能不能
   被别的形状绕过）——本轮只做了 V1–V5 五条。
3. Round 1 的未验证项 1/2/4/5（浅克隆独立失败面、merge commit 形态、自定义 glob 与多段 `required_artifacts`
   的端到端、接入方真实数字）**仍然未验证**（与 `design.md:620-625` 的清单一致）。
4. 本 change 自己的门禁仍红（缺三份 manifest + 相邻 change 的 stale）——流程状态，见 Round 1 §5，本轮未复测。

## Round 2：建议（不阻塞）

1. `test_F11` 建议补 `assert code == C.EXIT_PASS`（现在只钉「不出现那句话」）。
2. `test_F10` 建议用真实 sha 而不是 `'d'*40`（可读性）。
3. `design.md §7.5` 的「均已修复」宜改成逐条状态（H1 ✅ / M2 ✅ / M3 ⚠️ 部分 / M4 ✅），
   并补一句「本轮复验另发现 H2（见 `reviews/building-review.md` 的 Round 2）」。
4. `contract.py:184` 那行值得加注释说明「manifest 的**真身路径**可能不匹配 glob」——这正是 H2 的成因，
   留给下一个读代码的人。

---

# Round 3（复验）

**范围**：复核作者声明的 H2 修复 + 低危项，并对**新实现**再找缝。所有结论都重新实测；
作者声明一律当**待验证断言**。

**跑了**：

1. `.venv/bin/pytest -q` → **629 passed**（28.3s；Round 2 是 626，多出的 3 条正是 `F12/F13/F14`）。
2. `/tmp/rev26/battery.py`（Round 1 的 20 个 case，**一字未改**）→ 末行 `与设计预期不符：0/20`。
3. `/tmp/rev26/variants2.py`（Round 2 的 V1–V5，**一字未改**）→ **5/5 全红**（V5 = Round 2 的 H2 构造，
   现在 `FAIL(1)`）。
4. **新造 3 条变体**（`/tmp/rev26/variants3.py`，全新仓）：V6 manifest 两跳符号链接 / V7 `reviews` 目录链接 +
   manifest 在链接目标里 + `report_path` 在 `reviews` 之外 / V8 `specs` 指向 **A 之外**的目录。
5. 三条新用例（`F12/F13/F14`）的**读码 + 回退变异分析**；`F11` 的强化核对。
6. 对 Round 2 报告的一处**自我订正**（见 R3-⑤）。

---

## R3-① 作者声明的修复：逐条复核

| # | 声明 | 复核 | 结论 |
|---|---|---|---|
| **H2** | `_content_provenance_ok` 改成按「**看见的路径**」认 glob（`is_manifest(seen)`）、按**内容源**读 manifest 正文取 `report_path`；队列改 `(seen, content_src)` 二元组 | 读 `contract.py:158-176`（`is_manifest(seen)` + `queue_report(seen, content_src)` 用 `view.read(rev, content_src)`）+ Round 2 的 V5 构造复跑 | ✅ **成立**：V5 现在 `FAIL(1)`（`0 个 change 目录`）；新用例 `F12` 正是该形状 |
| **低危** | 删掉 `_disabled_alias_order_case`；新增 `F12/F13/F14`；`F11` 强化为 `assert code == C.EXIT_PASS` | `grep -n "_disabled_alias_order_case" tests/test_archive_awareness.py`；读三条新用例 | ⚠️ **部分成立**：三条新用例 ✅ 都在且真在验行为（见 R3-④）；`F11` 确已强化为 `assert code == C.EXIT_PASS` ✅；但 **`_disabled_alias_order_case` 仍在**（`tests/test_archive_awareness.py:464`），**并且仍然调用已不存在的 `_targets`**（`:475-476`）——与「删掉」的声明不符（它名字不以 `test_` 开头，pytest 不收集，所以**不影响任何测试结果**，但改名即成 `NameError`） |
| — | （未声明）`design.md` 是否同步 | `grep -n "H2\|Round 2" design.md` | ❌ §7.5 的表**未更新**（仍写 Round 1 的「均已修复」，没有 H2/H3 的痕迹）——Round 2 的建议 3 未落（不阻塞，但表里那句现在**不准确**） |

## R3-② 原构造复跑（原始输出要点）

**A. `/tmp/rev26/battery.py`（20 case，未改）**

```
OK green 出生即归档 / 纯 move / move+重建 manifest / A 内 alias.md / 指向 changes_root 外被跟踪文件 /
         空文件豁免                                                   （6/6 绿）
OK red   R1-F1 / 对照(只复制字节) / R2-A2 / R2-A3 / R3-A1 / R3-A3 / N8 / N3 /
         R5 symlink_ev / R7 gitlink(reviews)                          （10/10 红）
OK 天花板 R3-A2（不要求红）                                           （绿，与文档一致）
OK 新攻击 gitlink 非证据位置 / 符号链接→A 内目录 ×2                     （3/3 红）
与设计预期不符：0/20
```

**B. `/tmp/rev26/variants2.py`（Round 2 的 V1–V5，未改）**

```
OK V1 符号链接链 → 借来的目录（specs）        FAIL(1)
OK V2 specs 目录链接 + 混入新文件             FAIL(1)
OK V3 reviews 链接到 A 之外的目录             FAIL(1)   ← ⚠️ 红因见 R3-⑤（不是判据 5）
OK V4 gitlink 藏在深层子目录                  FAIL(1)
OK V5 manifest 符号链接 + report_path 在 reviews 之外  FAIL(1)   ← Round 2 的 H2，已关闭
```

**C. `pytest -q`** → `629 passed`。

## R3-③ 新造的 3 条变体（`/tmp/rev26/variants3.py`，真 CLI，全新仓）

| # | 构造 | 期望 | 实测 |
|---|---|---|---|
| **V6** | `reviews/x.manifest.json -> ../_l1/x.manifest.json -> ../_l2/x.manifest.json`（真身），真身里 `report_path: "stolen/…"`，三份报告放在 `A/stolen/`（**逐字节借来**） | 红 | **`PASS(0)`** ❌ |
| **V7** | `reviews -> _r`（**A 之内的目录**符号链接），三份 manifest 是 `_r/` 里的**普通文件**，`report_path: "stolen/grill-review.md"`，三份报告放在 `A/stolen/`（**逐字节借来**） | 红 | **`PASS(0)` —— `check：通过 ✓`** ❌ **H3（高危）** |
| **V8** | `A/specs -> ../2026-09-30-old/specs`（**A 之外**的目录，现成 change 自己的 specs），其余文件全部唯一 | 红 | **`PASS(0)` —— `check：通过 ✓`** ❌ **H4（中危）** |

**V7 详证**（成品仓 `/tmp/arr26/battery/v7_reviews_dir_link_manifest_report_outside`）

```
$ for f in grill-review.md grill-adversarial.md building-review.md; do
    cmp openspec/changes/archive/2026-09-30-old/reviews/$f \
        openspec/changes/archive/2026-10-15-new/stolen/$f && echo "$f 逐字节相同"; done
grill-review.md 逐字节相同 / grill-adversarial.md 逐字节相同 / building-review.md 逐字节相同

$ ls -l openspec/changes/archive/2026-10-15-new/        # reviews 是**目录**符号链接
lrwxrwxrwx  reviews -> _r
drwxr-xr-x  stolen/            specs/            _r/
$ ls openspec/changes/archive/2026-10-15-new/_r/        # manifest 是**普通文件**
building.manifest.json  grill-adversarial.manifest.json  grill.manifest.json
$ python -c "import json;print(json.load(open('…/_r/grill.manifest.json'))['report_path'])"
stolen/grill-review.md

$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，12 个变更文件，1 个 change 目录
  change：2026-10-15-new（归档）
check：通过 ✓
EXIT=0
```

**判据 5 实际比了哪些文件**（打桩 `contract._is_reused`）：

```
   compared: tasks.md                                      reused=False
   compared: specs/retry/spec.md                           reused=False
   compared: _r/grill.manifest.json                        reused=False
   compared: _r/grill-adversarial.manifest.json            reused=False
   compared: _r/building.manifest.json                     reused=False
arrivals: [('2026-10-15-new', [])]
```

⇒ `A/stolen/*.md`（三份**逐字节借来**的审阅报告）**一次都没进比对**。

**对照（证明门禁消费的正是那份借来的文件）**：把 `A/stolen/grill-review.md` 换成不合规的短 grill 报告
（2 条决策）并同步 `report_hash` ⇒ `check：未通过 ✗ … stolen/grill-review.md：## Confirmed Decisions 只有 2 条，少于硬门槛 3 条`。

**V8 详证**（成品仓 `/tmp/arr26/battery/v8_specs_link_to_dir_outside`）

```
$ ls -l openspec/changes/archive/2026-10-15-new/specs
lrwxrwxrwx  openspec/changes/archive/2026-10-15-new/specs -> ../2026-09-30-old/specs
$ cmp  .../2026-09-30-old/specs/retry/spec.md  .../2026-10-15-new/specs/retry/spec.md   # 经链接
  （逐字节相同）
$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，11 个变更文件，1 个 change 目录
  change：2026-10-15-new（归档）
check：通过 ✓
```

**根因（两条，同一族）**

- **H3**：`is_manifest(seen)`（`contract.py:158-166`）用的是**队列项里的 `seen`**，而目录展开时
  `queue.extend((row.path, row.path) …)`（`:204`）把 `seen` 换成了**链接解析之后的路径**
  （`A/reviews/x` ⇒ `A/_r/x`）⇒ 逻辑路径 `reviews/x.manifest.json` **丢了** ⇒ glob 不再命中
  ⇒ `queue_report`（`:210`）不触发 ⇒ `report_path` 目标不进集。V6 是同一处的另一个形状：
  `queue_report` 只读**一跳**（`view.read(rev, content_src)`，`:167-176`），指向符号链接时
  `git show` 返回的是**链接文本**（不是 JSON）⇒ `json.loads` 抛 `ValueError` ⇒ 静默 `return`。
- **H4**：`:199`（`elif _is_reused(view.entry(rev, target).sha, seen, …)`）对**目标在 `A` 之外**的符号链接
  只比**一条 entry 的 sha**。目标是**目录**时比的是 tree sha，而 `base_blobs` 来自
  `view.walk`（`ls-tree -r`，**不含 tree 行**）⇒ **恒不命中** ⇒ 目录内容从不展开；
  这与 `spec.md:74`「目标在 `A` 之外 ⇒ 按该目标路径在 head 树里的 blob 比对（**与 `cp` 进来同结论**）」
  直接冲突。

## R3-④ 三条新用例：真的在验行为吗？（回退变异分析）

- **`F12_symlinked_manifest_still_pulls_in_its_report`**：Round 2 的 V5 形状，断言 `EXIT_FAIL` + `"没有任何 change 目录"`。
  **变异**：把 `is_manifest` 换回「按真身路径匹配 glob」（即回退 H2 的修复）⇒ 报告不进集 ⇒ 到达被授予 ⇒
  该构造的 manifest 里 `base_sha="0"*40` 解析不到提交 ⇒ 红的是**别的** finding（「不是本仓的提交」），
  `"没有任何 change 目录"` **不出现** ⇒ 断言失守。✅ **能杀死回退变异**。
- **`F13_unreadable_tree_is_fail_closed`**：`monkeypatch` 让 `GitTree.walk` 抛 `GitError`，断言 `EXIT_FAIL` + `"fail-closed" in err`。
  **变异**：删掉 `checkcmd.py:86-96` 的 `except gitutil.GitError` ⇒ 异常冒到 `entry.py`，
  退 **1**（`check` 不是 `guard`）⇒ **退出码断言杀不死它**，但 `entry.py` 的兜底文案是
  `witnessloop：内部错误（…）`（**不含 `fail-closed`**）⇒ `"fail-closed" in err` **失守**。✅
  ⚠️ 它靠**文案**区分「受控 fail-closed」与「崩溃」——这里是合理的（两者退出码同为 1，
  不用文案就没有可观测量），但它是三条里最弱的一条，建议同时断言
  `"无法读取" in err` 或直接断言 finding 的 `path` 前缀。
- **`F14_dangling_symlink_is_fail_closed`**：`A/specs/dangling -> nowhere.md`，断言 `EXIT_FAIL` + `"没有任何 change 目录"`。
  **变异**：删掉 `contract.py:191-192` 的 `target is None or view.entry(rev, target) is None ⇒ return False` ⇒
  悬空链接静默通过（`entry is None ⇒ continue`）⇒ 到达被授予 ⇒ 该构造**没有 manifest** ⇒
  报「缺少 review manifest」而不是「没有任何 change 目录」⇒ 断言失守。✅
- **`F11` 强化核对** ✅：`assert code == C.EXIT_PASS, err` 已在（Round 2 的建议 1 已落）。
- ❗ 三条新用例都**不覆盖** H3（目录链接 + manifest 在链接目标 + `report_path` 在外）与 H4（A 之外目录目标）。

## R3-⑤ 对 Round 2 报告的一处**自我订正**

Round 2 我把变体 **V3**（`reviews` 指向 `A` 之外目录）记成「✅ 外侧半边也修好了」。
**那条结论不成立**：直调 `contract.archive_arrivals` 显示它**被授予**
（`arrivals: [('2026-10-15-new', [])]`，trace 里 `compared: reviews reused=False`——比的是被链接目录的 **tree sha**）。
V3 之所以仍然 `FAIL(1)`，红因是**证据门**：受害目录里那三份 manifest 的 `report_path` 是相对 **change 目录**
写的（`reviews/x.md`），解析到 `A` 下就**逃逸**了（`report_path='reviews/building-review.md' 逃逸出 change 目录`）
+ 哈希不符 + 孤儿报告（共 21 项，其中没有「没有任何 change 目录」）。
⇒ 我当时只看了退出码、没看红因，**把「恰好红」当成了「判据 5 修好了」**。
**V8 才是这条路的干净版本**（把 `specs` 而不是 `reviews` 指向 A 之外的目录，其余全部唯一）⇒ 判绿。

## Round 3：必须修改项

**1）（高危，新）H3：符号链接的**逻辑路径**必须在整条遍历里保留 —— 现在目录链接一展开就丢了**

- 位置：`src/witnessloop/contract.py:158-166`（`is_manifest(seen)` 用队列项的 `seen`）、
  `:204`（`queue.extend((row.path, row.path) …)` 把 `seen` 覆写成链接解析后的路径）、
  `:167-176`（`queue_report` 只读一跳，`git show` 遇到符号链接返回**链接文本**）。
- 违反对应：`spec.md:59-60`（manifest 命中 glob ⇒ 其 `report_path` 目标 SHALL 进集）、
  `spec.md:72-73`（「目标路径 SHALL 并入 `Ev(A)`，递归到不动点」）、`docs/gate.md:329-330`。
- 复现：

```
$ /home/happy/wl-wt/archive-arrival-recognition/.venv/bin/python /tmp/rev26/variants3.py V7
!! V7 reviews 目录链接 + manifest 在 _r + report_path 在 reviews 之外  期望=FAIL 实测=PASS(0)
$ cd /tmp/arr26/battery/v7_reviews_dir_link_manifest_report_outside
$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：通过 ✓        # A/stolen/ 里三份报告与 openspec/changes/archive/2026-09-30-old/reviews/ 逐字节相同
```

- 期望修法（建议）：把队列项从 `(seen, content_src)` 改成 **`(logical, content)`**，
  其中 `logical` 是「**按符号链接语义看见的**仓根相对路径」：
  - 目录展开：`queue.extend((f"{logical}/{name}", row.path) for row in view.walk(rev, content))`；
  - 符号链接：`logical` 保持不变、`content` = 解析后目标（这样 `is_manifest`/`_is_reused` 的 (b) 都用 `logical`）；
  - `queue_report` 沿链接**递归**解析（配 `visited` 防环），并在解析途中**任何一跳**是 manifest 时都读它。
  ⚠️ 修完请补用例：`reviews -> _r` + manifest 在 `_r/` + `report_path` 在 `reviews/` 之外（= V7），
  以及 manifest 两跳链接（= V6）。

**2）（中危，新）H4：符号链接目标在 `A` 之外且是**目录**时必须展开其下文件**

- 位置：`src/witnessloop/contract.py:199`（`elif _is_reused(view.entry(rev, target).sha, seen, …)`）。
- 违反对应：`spec.md:74`（「与 `cp` 进来同结论」）、`design.md:123-124`。
- 复现：

```
$ /home/happy/wl-wt/archive-arrival-recognition/.venv/bin/python /tmp/rev26/variants3.py V8
!! V8 specs 指向 A 之外的目录（借来的 specs 字节）                期望=FAIL 实测=PASS(0)
# A/specs -> ../2026-09-30-old/specs，specs/retry/spec.md 逐字节 = 现成 change 的；check：通过 ✓
```

- 期望修法：目标是 tree 时⇒ `queue` 其下每个文件（`(logical_child, child)`，`logical_child` 沿用**链接自身**
  的路径作 (b) 的判定对象，见 `spec.md:76`），不要再拿 tree sha 去比 `base_blobs`。

**3）（低）`_disabled_alias_order_case` 其实**没删**

- `tests/test_archive_awareness.py:464`（函数仍在）、`:475-476`（仍在调用**已不存在**的 `_targets`）。
  与作者「删掉…死用例」的声明不符；它现在还多了一层「调用不存在函数」的坏味道。
  ⇒ 删掉它（与同文件 `:456 _removed_alias_order_case` 一起），或把「别名与顺序无关」搬进
  `tests/test_archive_arrival.py`（那里已有等价覆盖）。

## Round 3：未验证项

1. H3/H4 的**修法**只给方向，未实现；修完需重跑 `battery.py` 全量 + `variants2.py` V1–V5 + `variants3.py` V6–V8。
2. 我**没有**穷尽这条「路径推导被符号链接改名」的家族——本轮只覆盖了目录链接（V7）、链接链（V6）、
   A 外目录目标（V8）三种；`report_path` 指向「指向 A 外目录的符号链接」等组合未逐一构造。
3. Round 1/2 的未验证项（浅克隆独立失败面、merge commit 形态、自定义 `review_manifest_glob` 与多段
   `required_artifacts` 的端到端、接入方真实数字）**仍未验证**（与 `design.md:620-625` 一致）。
4. 本 change 自己的门禁仍红（缺三份 manifest + 相邻 change 的 stale）——流程状态，本轮未复测。

## Round 3：建议（不阻塞）

1. `F13` 建议除了 `"fail-closed"` 再断言一条结构性内容（如 `"无法读取" in err`），减少对文案的依赖。
2. `design.md §7.5` 的表建议补 Round 2/3 的两行（H2 已修 / H3·H4 待修），别让「均已修复」留在库里。
3. 这已经是**第三次**在同一处（`Ev(A)` 的路径推导 + 符号链接）被证伪。建议**改结构**而不是继续打补丁：
   在遍历里**只**用「逻辑路径」做归属/glob/(b) 判定、用「内容路径」只做读取，两者**永不混用**；
   并补一条**属性式**回归（对同一份 `A`，任意地在 `A` 内插入 `ln -s` 不应改变判定结果）——
   否则下一轮还会在第四个形状上复现。

---

# Round 4（复验）

**范围**：复核作者声明的 H3/H4 + 低危修复，并对新实现（`seen` / `src` / `follow` 三个新概念）再找缝。
作者声明一律当**待验证断言**。

**跑了**：

1. `.venv/bin/pytest -q` → **631 passed**（29.4s；Round 3 是 629，多出的 2 条正是 `F15/F16`）。
2. `/tmp/rev26/battery.py` → 末行 **`与设计预期不符：0/20`**。
3. `/tmp/rev26/variants2.py`（Round 2 的 V1–V5）→ **5/5 全红**。
4. `/tmp/rev26/variants3.py`（Round 3 的 V6–V8）→ **3/3 全红**（V7/V8 的 `check` 输出已是「`0 个 change 目录`」，即到达被**判据 5** 拒，不再靠证据门兜底）。
5. **新造 5 条变体**（`/tmp/rev26/variants4.py`，全新仓）+ **1 条无符号链接的洗白**（`/tmp/rev26/h5_launder.py`）。
6. `F15/F16` 的读码 + 回退变异分析。

---

## R4-① 作者声明的修复：逐条复核

| # | 声明 | 复核 | 结论 |
|---|---|---|---|
| **H3+H4 同一根因** | 队列 `(seen, src)`；新增 `follow()` 跟链到不动点（悬空/gitlink/逃出仓根/过深 ⇒ fail-closed）；目录展开保留 `seen` 前缀；`judge_path` = 目标在 `A` 内 ⇒ 目标自身路径、逃出 ⇒ `seen`；manifest 正文按 `follow()` 后的内容源读 | 读 `contract.py:169-226`；V5/V7/V8 三个原构造复跑 | ✅ **成立**：V7（Round 3 的 H3）现在 `0 个 change 目录`；V8（H4）同样；`follow` 的 4 个 fail-closed 出口（`:176-185`）都在 |
| **低危** | 删掉 `_disabled_alias_order_case`；新增 `F15`（H3 回归）/`F16`（H4 回归） | `grep -n "_disabled_alias_order_case" tests/test_archive_awareness.py` → **0 命中**；读 `F15/F16` | ✅ **成立**：死用例已删（同文件 `:456 _removed_alias_order_case` 是纯 docstring 占位，无害，见「建议 3」）；两条回归用例都在且**真在验行为**（见 R4-④） |

## R4-② 复跑原始输出要点

```
$ .venv/bin/pytest -q                       →  631 passed in 29.38s
$ python /tmp/rev26/battery.py              →  与设计预期不符：0/20
$ python /tmp/rev26/variants2.py            →  V1..V5 全部 FAIL(1)（5/5）
$ python /tmp/rev26/variants3.py            →  V6/V7/V8 全部 FAIL(1)（3/3）
      V7: check：基线 main...HEAD，12 个变更文件，0 个 change 目录   ← Round 3 时是「1 个 change 目录 + 判据 5 放行」
      V8: check：基线 main...HEAD，11 个变更文件，0 个 change 目录   ← 同上
```

⇒ Round 3 的两条高危/中危**确已关闭**，且**没有**误伤 6 条「必须绿」与天花板（battery 仍 0/20）。

## R4-③ 新造的变体

| # | 构造 | 期望 | 实测 |
|---|---|---|---|
| **W1** | 链接链里混入**逃出仓根**的一跳（`A/specs -> ../../../../../../etc/passwd`），其余件齐、内容全新 | 红 | **`FAIL(1)`** ✓（`follow` 的 `_resolve_rel` 返回 None ⇒ fail-closed） |
| **W2** | **同一个最终文件**被两条不同 `seen` 路径指到（`A/reviews/alias1.md` 与 `A/specs/alias2.md` 都指向 `A/stolen-report.md`，内容是借来的） | 红 | **`FAIL(1)`** ✓（两条 seen 都判同一个 `final`，都命中） |
| **W3** | `report_path` 指到 **`A` 内的一个目录**（目录里是借来的报告） | 红 | **`FAIL(1)`** ✓（判据 5 拒；证据门另有「报告不存在」，但到达已先被拒） |
| **W4** | `report_path` 指向**另一份 manifest**（`A/reviews/alias.manifest.json -> grill.manifest.json`） | 观察 | **`PASS(0)`** —— 这**不是**绕过：该构造里所有证据字节都是本次新写的，多一份同 stage 的 manifest 被容忍属于既有口径 |
| **W5** | **自引用的目录符号链接**：`ln -s .. A/specs/l`（从 `A/specs` 出发 `..` = `A` 自己） | 红 | ❌ **`check` 30s / 60s 内都没有结束**（`timeout` 退 124）—— **H6** |
| **H5** | **不需要任何符号链接**：`git mv docs/templates/<f> A/reviews/<f>`（造出 R 记录）+ 覆盖成借来的字节 | 红 | ❌ **`PASS(0)`，`check：通过 ✓`**，三份报告与既有归档 change **逐字节相同** —— **H5** |

### H5 详证（`/tmp/rev26/h5_launder.py`，一条命令可复算）

```
$ .venv/bin/python /tmp/rev26/h5_launder.py
R057  docs/templates/grill-adversarial.md → openspec/changes/archive/2026-10-15-new/reviews/grill-adversarial.md
R063  docs/templates/grill-review.md      → openspec/changes/archive/2026-10-15-new/reviews/grill-review.md
  grill-review.md / grill-adversarial.md / building-review.md 与既有归档 change 的逐字节相同？ True / True / True
check：基线 main...HEAD，11 个变更文件，1 个 change 目录
  change：2026-10-15-new（归档）
check：通过 ✓
EXIT = 0
```

**机理**：`rename_dests`（`contract.py:236-238`）是**路径集合**；`_is_reused`（`:227-233`）的 (b) 只问
「`judge_path` 在不在这个集合里」，**从不看落点上的字节是不是搬来的那份**。
于是「先 `git mv` 一个相似文件占住证据路径（该路径从此永久进 `rename_dests`），再把内容覆盖成借来的字节」
就同时躲开 (a)（blob 在 `base_blobs` 里）与 (b)（路径是改名落点）。

**前提（必须写明，不夸大）**：要让 git 把这次搬运记成 `R` 记录，被搬的 base 文件与最终内容须 **≥50% 相似**
（git 默认阈值）。本构造用 `docs/templates/*.md`——**规格自己正是要求把模板放在 `changes_root` 之外**
（`spec.md:104-108` 的误伤面 + `docs/gate.md:338`），所以「仓里有与报告同源的模板/样板文件」是**本仓推荐的布局**，
不是奇技淫巧。样本量：我用 95% 相似（模板 = 报告改一个词 + 追加一行）；阈值本身取决于内容，未做扫参。

### H6 详证（`/tmp/arr26/battery/w5_self_referential_dir_symlink`）

```
$ ls -l openspec/changes/archive/2026-10-15-new/specs/
lrwxrwxrwx  l -> ..
$ timeout 60 .venv/bin/python -m witnessloop check --root . --base main --head HEAD
$ echo $?
124                       # 60s 内没有结束，被 timeout 杀掉

# 直接打 archive_arrivals，统计每 5 秒发的 git ls-tree 次数：
  t=   5s  ls-tree: entry=  2113  walk=   268  （archive_arrivals 仍未返回）
  t=  10s  ls-tree: entry=  4238  walk=   534
  t=  20s  ls-tree: entry=  8343  walk=  1047
  t=  35s  ls-tree: entry= 14675  walk=  1838
```

**机理**：目录展开时 `queue.append((f"{prefix}/{rel}", row.path))`（`contract.py:205-208`），
`prefix` = 上一层的 **`seen`**；而 `seen_paths`（`:187, 194-196`）**按 `seen` 去重**。
自引用链接让 `seen` 每轮都变（`A/specs/l` → `A/specs/l/specs/l` → …），
**永不重复** ⇒ visited 集形同虚设 ⇒ 队列无界增长、进程不终止。
`design.md:73` 与 `spec.md:73` 都写着「递归到不动点，配 **visited 防环**」——这条**未落实**。
影响：任何提交了这种链接的 PR 都会让 CI 的 `check` 挂到 job 超时（不是判绿，是**不判**）。

## R4-④ `F15`/`F16` 真的在验行为吗？（回退变异分析）

- **`F15_dir_link_keeps_the_logical_path_for_manifests`**（= Round 3 的 H3 形状）：`reviews -> _r`，
  manifest 在 `_r/` 里、`report_path` 指向 `stolen/grill-review.md`（借来的）；断言 `EXIT_FAIL` + `"没有任何 change 目录"`。
  **变异**：把目录展开的 `seen` 前缀换回「真身路径」（即回退 H3 的修复）⇒ manifest 不被认成 manifest ⇒
  `report_path` 不进集 ⇒ 到达被授予 ⇒ 该构造的 manifest `base_sha="0"*40` 解析不到提交、且缺另两个 stage，
  **报的是别的 finding**，`"没有任何 change 目录"` 不出现 ⇒ 断言失守。✅ **能杀死回退变异**。
- **`F16_dir_link_target_outside_a_cannot_borrow_a_whole_tree`**（= Round 3 的 H4 形状）：`specs` 指向 A 之外的目录；
  同款断言。**变异**：把「A 外目录逐文件比对」退回「只比目标 tree sha」⇒ `_is_reused(tree_sha)` 恒 False ⇒
  到达被授予 ⇒ 该构造**没有 manifest** ⇒ 报「缺少 review manifest」⇒ `"没有任何 change 目录"` 不出现 ⇒ 失守。✅
- ⚠️ 两条都**不覆盖** H5（无符号链接）与 H6（不终止）——它们打的是判断逻辑与终止性，不是符号链接形状。

## R4-⑤ 试过但**没有**构成绕过的方向（如实记录）

- `report_path` 指向**另一份 manifest**（W4）：判绿，但那次构造里所有证据字节都是新的，不构成复用。
- **两条 `seen` 路径指向同一份借来的最终文件**（W2）：被判据 5 抓住（两条 seen 各自都比到了那个 `final`）。
- **链中混入逃出仓根的一跳**（W1）：`follow` 的 `_resolve_rel` 直接返回 None ⇒ fail-closed ✓。
- **`report_path` 指向 `A` 内的目录**（W3）：拒 ✓。
- 另核对：`follow()` 的 32 跳上限对**环形文件链接**（`a -> b`、`b -> a`）有效（超限 ⇒ None ⇒ fail-closed）——
  只有**目录**自引用（H6）绕过了它，因为那种环路不在 `follow` 里、而在**展开队列**里。

## Round 4：必须修改项

**1）（高危，新）H5：判据 5 的 (b) 必须同时看「落点的内容」，不能只看「落点的路径」**

- 位置：`src/witnessloop/contract.py:227-233`（`_is_reused`）与 `:236-238`（`rename_dests` 的构造）。
- 违反对应：`spec.md:51`（(b) = 「它是本次 diff 里某条改名记录的落点（记录的 `new_path`，**即本次搬过来的**）」——
  「即本次搬过来的」这个**内容**含义没被判、只判了路径）；
  `design.md:133-134`（「合法 move 的文件**全是**改名记录的落点」——这句话的前提是落点内容 = 搬来的内容）。
- 复现：`.venv/bin/python /tmp/rev26/h5_launder.py`（输出见 R4-③；`check：通过 ✓`，三份报告逐字节 = 既有归档 change 的）。
- 期望修法（建议）：把 `rename_dests` 从「路径集合」升级成 **「(落点路径, 该记录源路径在 base 里的 blob sha)」集合**，
  `_is_reused` 命中 (b) 的条件收紧成「路径匹配 **且** `entry.sha` == 那条记录的源 blob」。
  ⚠️ 核对不误伤：形态 ii（move + 重建 manifest）里**未改动**的被搬文件，其 head blob 恰好等于
  base 里 `changes/<id>/<file>` 的 blob ⇒ (b) 仍成立；**被改写**的那些文件内容是新写的 ⇒ 走 (a)。
  请一并补一条**必须红**用例（= H5 形状：`git mv <相似文件> <证据路径>` + 覆盖成借来的字节）。

**2）（中危，新）H6：自引用的目录符号链接会让 `check` 不终止 —— visited 集必须按「内容身份」而不是「逻辑路径」**

- 位置：`src/witnessloop/contract.py:187`（`seen_paths`）、`:194-196`（按 `seen` 去重）、`:205-208`（用 `seen` 拼前缀）。
- 违反对应：`design.md:73` / `spec.md:73`（「递归到不动点，**配 visited 集防环**」）。
- 复现：`cd /tmp/arr26/battery/w5_self_referential_dir_symlink && timeout 60 .venv/bin/python -m witnessloop check --root . --base main --head HEAD; echo $?` → **124**（60s 未终止）。
- 期望修法（建议）：① 记账去重改用 `(seen, final)` 或直接按 `final`（内容身份）——同一份内容重复比对没有意义；
  ② 对**逻辑路径深度**（或队列项总数 / 轮数）设硬上限，超出 ⇒ **fail-closed**（报 finding、非零退出），
  保证任何输入下 `check` 都终止。两条建议都做，别只做一条。

## Round 4：未验证项

1. H5 修复后需重跑 `battery.py` + `variants2/3/4.py` + `h5_launder.py` 全量。
2. H5 的**相似度阈值**未扫参：我只构造了 95% 相似的模板；「多相似才够」取决于 git 的 `-M` 启发式，未测。
   同样未测：如果仓库里**没有**任何与借来内容 ≥50% 相似的 base 文件，H5 是否还成立（我判断不成立）。
3. H6 的**触发面**只测了「`specs` 下的自引用链接」一种；`reviews` 下的、以及「A→B→A 双向目录链接」未逐一构造
   （机制上同族）。
4. Round 1/2/3 的未验证项（浅克隆独立失败面、merge commit 形态、自定义 `review_manifest_glob` 与多段
   `required_artifacts` 的端到端、接入方真实数字）**仍未验证**。
5. 本 change 自己的门禁仍红（缺三份 manifest + 相邻 change 的 stale）——流程状态，本轮未复测。

## Round 4：建议（不阻塞）

1. `contract.py:205` 的 `prefix = seen if seen == src else seen` 是**恒等于 `seen`** 的三元式（两个分支一样），
   读起来像是漏了点什么，建议直接写 `prefix = seen` 或删掉这个临时变量。
2. 这一处（`Ev(A)` 的推导）四轮里被连打四次（H1/H2/H3+H4、现在的 H5/H6），**打法在变**：
   前三轮是**符号链接形状**，这一轮是**改名记录**与**终止性**。建议在收官前做一次**结构性**收口：
   把「归属」统一表达成对**内容身份（blob sha + 来源记录）**的判定，而不是对路径字符串的判定；
   并补一条**属性式**回归——「只往 `A` 里加符号链接 / 只改 A 内文件的名字，不得翻转判定」。
3. `tests/test_archive_awareness.py:456 _removed_alias_order_case` 现在只剩 docstring（无害），
   建议顺手删掉，别留一个叫 `_removed_..._case` 的空函数。
4. `design.md §7.5` 仍停在 Round 1 的四行（「均已修复」）。建议每轮复验后同步该表（至少补一行
   「Round 2/3 的 H2/H3/H4 已修；Round 4 的 H5/H6 待修」），否则库里的结论会与实际状态脱节。

---

# Round 5（复验）

**范围**：复核作者声明的 H5/H6 修复 + 收敛判定。作者声明一律当**待验证断言**。

**跑了**：

1. `.venv/bin/pytest -q` → **633 passed**（45.3s；Round 4 是 631，多出的 2 条正是 `F17/F18`）。
2. `/tmp/rev26/battery.py` → **`与设计预期不符：0/20`**。
3. `/tmp/rev26/variants2.py`（V1–V5）→ **5/5 全红**；`/tmp/rev26/variants3.py`（V6–V8）→ **3/3 全红**。
4. `/tmp/rev26/h5_launder.py` → **`EXIT = 1`**（Round 4 时是 `EXIT = 0`），报「没有任何 change 目录」。
5. **新造变体**（`/tmp/rev26/variants5.py`）：W6 **预算边界扫描**（合法到达 + `specs/` 下 50/200/500/900/1000/1100 个新文件）、
   W7 同 diff 内「先建后移」、W8 `moved_content` 语义核对；另加一条**大仓纯归档 move**（1015 文件）。
6. `F17/F18` 的读码 + 回退变异分析。

---

## R5-① 作者声明的修复：逐条复核

| # | 声明 | 复核 | 结论 |
|---|---|---|---|
| **H5** | (b) 收紧为「**内容未变的搬移**」：`moved_content` = `(new_path, 源侧 blob)` 二元组，源侧取 `merge-base` 树里 `old_path` 的 sha；落点 blob 必须**等于**源侧 blob | 读 `contract.py`（`moved_content` 的构造 + `_is_reused`）；`h5_launder.py` 复跑 | ✅ **成立**：`h5_launder.py` 现在 `EXIT=1`（Round 4 是 `EXIT=0`）；`_is_reused` 的 (b) 条件已是 `(normalize(path), sha) not in moved_content` —— 看的是**内容**，不再只看路径 |
| **H6** | 展开循环加显式预算（`budget = 1024`，超限 ⇒ `return False` fail-closed） | 读 `contract.py` 的 `budget`；Round 4 的自引用构造复跑 | ⚠️ **「不终止」确已修好**（下面就是它的**边界**问题）：`specs/l -> ..` 现在**能返回**、且该到达被拒 ✓ |
| **新增用例** | `F17`（洗白改名）/`F18`（自引用目录链接） | 读 `tests/test_archive_awareness.py` | ✅ 两条都在，且**真在验行为**（见 R5-④） |
| **规范性正文** | `spec.md` 的 (b) 与「展开 SHALL 有硬上限」写进正文 | `grep -n "内容未变\\|硬上限" spec.md` → `:51-58` | ✅ 已进正文（(b) 的收紧与硬上限都有 `SHALL`） |

## R5-② 复跑原始输出要点

```
$ .venv/bin/pytest -q                        →  633 passed in 45.25s
$ python /tmp/rev26/battery.py               →  与设计预期不符：0/20
$ python /tmp/rev26/variants2.py             →  V1..V5 全部 FAIL(1)
$ python /tmp/rev26/variants3.py             →  V6/V7/V8 全部 FAIL(1)
$ python /tmp/rev26/h5_launder.py            →  check：未通过 ✗（1 项）… 没有任何 change 目录   EXIT = 1
```

⇒ Round 1–4 的五条**全部关闭**，且**没有**误伤 6 条「必须绿」与天花板（battery 仍 0/20）。

## R5-③ 新造的变体

| # | 构造 | 期望 | 实测 |
|---|---|---|---|
| **W6** | 合法「出生即归档」+ `specs/` 下 50 / 200 / 500 / 900 / **1000** 个**新写**文件 | 绿 | **全部 `PASS(0)`** ✓（1000 个文件都没事） |
| **W6′** | 同上，但 `specs/` 下 **1100** 个新文件 | 绿 | ❌ **`FAIL(1)`**：`0 个 change 目录`（到达**没被认出**） |
| **W6″** | 合法**纯归档 move**（全 `R100`）一个含 **1015** 个文件、证据齐全的 active change | 绿、无幽灵 id | ❌ **`FAIL(1)`，9 项**，第 1 项就是 **`openspec/changes/big：change 目录不存在`**（幽灵 active id 回来了） |
| **W7** | 同 diff 内「先建 `A/tmp/x.md` 再 `git mv` 到 `A/reviews/extra.md`」 | 到达被认出（源不在 base ⇒ 不该误判） | **到达被认出** ✓（`1 个 change 目录`；该构造另因我自己没给它配 manifest 而报了孤儿报告，与判据 5 无关） |
| **W8** | 直调纯函数核对 `moved_content` 的语义 | — | 见下 |

**预算边界扫描（实测）**

```
specs 文件数= 1005 ⇒ 退出码=0（到达被认出）
specs 文件数= 1015 ⇒ 退出码=1
specs 文件数= 1021/1022/1023/1024/1030 ⇒ 退出码=1
```

阈值落在 **1005–1015** 之间，与 `budget = 1024` 每次出队扣 1 相符
（出队项 = 3 个 artifact 根 + glob 命中的 manifest + `specs` 展开的每个文件 + `reviews` 展开的每个文件）。

**大仓纯归档 move 的完整症状（`/tmp/arr26/battery/bigmove`）**

```
$ .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，1025 个变更文件，1 个 change 目录
  change：big                                   ← 只认出**源 id**，归档目录没被认出
check：未通过 ✗（9 项）
  1. openspec/changes/big：change 目录不存在（diff 里出现了它的文件，但目录不在工作树中）
  2. openspec/changes/big：缺少 review manifest …
  3. openspec/changes/big：无 stage=grill 的 manifest …
  4-9. …/reviews/*.manifest.json：受保护路径被写入，但没有结构化解释事件（×6）
```

这 9 项正是 `design.md §1.3` 表格里**改动前**的形态 ii 症状（幽灵 id + 受保护写入），
即：**大到达目录会让本 change 的核心修复整体失效**，而且文案指向完全错误的方向
（作者会以为「忘了建 change 目录」）。

## R5-④ `F17`/`F18` 真的在验行为吗？（回退变异分析）

- **`F17_laundering_via_a_similar_file_rename_is_rejected`**（= Round 4 的 H5 形状）：`git mv templates/report.md
  <到达>/reviews/grill-review.md` + 覆盖成借来的字节；断言 `EXIT_FAIL` + `"没有任何 change 目录"`。
  **变异**：把 `moved_content` 退回「只存落点路径」（即回退 H5）⇒ 该路径是改名落点 ⇒ 判据 5 放行 ⇒
  到达被授予 ⇒ 该构造**没有 manifest** ⇒ 报「缺少 review manifest」而**不是**「没有任何 change 目录」⇒ 断言失守。✅
  （它的注释还把「必须相似但**不**逐字节相同」这条前提写清楚了 —— 逐字节相同会变 `R100`，那本来就属「内容原样搬过来」。
  这条注释与我的实测一致。）
- **`F18_self_referential_directory_link_terminates`**（= Round 4 的 H6 形状）：`specs/l -> ..`；
  断言 `EXIT_FAIL` + `"没有任何 change 目录"`，并显式钉「**check 能返回**」。
  **变异**：删掉 `budget` ⇒ 该用例**不是断言失守，而是整个用例（乃至整个 pytest 进程）挂死**
  ⇒ 仍然会被发现，但**发现方式是挂起**而不是一条失败 —— 建议配 `pytest-timeout`（见「建议 2」）。
  现状：能返回且判红 ✓。

## R5-⑤ 试过但**没有**构成绕过的方向（如实记录）

- **H5 的"残余"**：(b) 现在要求「落点 blob == 源侧 blob」，所以只有当 **base 里另有一份逐字节相同的副本、
  且它不在 `archive/**` 下**（否则判据 3 直接拒）时，才能把那份副本 `git mv` 进来当豁免。
  我把「源在 `A` 之内（同 diff 先建后移）」（W7）与「源在 `A` 之外」两条都试了：
  前者源不在 `merge-base` 树里 ⇒ `moved_content` 根本不会为它记条目 ⇒ 内容只能靠 (a) 过关（实测到达被认出 ✓）；
  后者若源在 `archive/**` 下则由判据 3 拦。**没找到可在一次 PR 内实现的绕过**（构造「base 里恰好有非归档副本」
  需要 base 本身满足条件，属既有的「完全旁路」家族）。
- **`moved_content` 的源侧取 `merge-base` 树 vs head 树**：实现用 `view.entry(base_rev, old_path)`
  （`base_rev` = `merge_cmd` 算出的 merge-base，与 `base_blobs` 同源）⇒ 两边口径一致 ✓；我未构造出
  「同一 old_path 在 merge-base 与 head 里内容不同、导致豁免判定翻转」的构造（试了「同 diff 内先改后移」，落到 (a)）。
- **`R100` 的源在 `A` 之内**（同 diff 先建后移）：见 W7 —— 到达被正确认出，未构成绕过 ✓。
- **`F17` 的前提（相似度）**：git 默认 `-M` 阈值 50%；我 Round 4 的构造用 95% 相似。
  更低相似度下是否仍能被配对**未做扫参**（不影响「修好/没修好」的结论，但阈值本身未标定）。

## Round 5：必须修改项

**1）（中危，非安全绕过）展开预算按「队列项数量」封顶 ⇒ **证据树 ≳1010 个文件的合法到达被判成「不是到达」**，
且症状是本 change 要消灭的幽灵 id**

- 位置：`src/witnessloop/contract.py` 的 `budget = 1024` 与 `while queue: budget -= 1; if budget < 0: return False`
  （Round 4 我引的是 `:187-208` 一带，本轮该行随修复下移，以 `budget` 字样定位）。
- 违反对应：本 change 自己的**核心目标**（`design.md §1.3` / `spec.md:116-122` 的「出生即归档」Scenario、
  `spec.md:124-131` 的「同一 move 内带内容改动」Scenario：退出码 0、**无**幽灵 active id）；
  以及 `spec.md:57-58` 新写的硬上限条款——它要求「封顶」，但**没有**要求「把合法的**广度**也一起封顶」，
  更没要求「超限时静默降级成『没有任何 change 目录』」。
- 复现（两条，都可复算）：

```
# ① 合法出生即归档 + specs 下 1015 个新文件（全绿内容）
$ python /tmp/rev26/variants5.py W6      # 见 R5-③；1005 个文件 PASS(0)，1015 个文件 FAIL(1)

# ② 合法纯归档 move（全 R100）+ 1015 个文件
$ cd /tmp/arr26/battery/bigmove && .venv/bin/python -m witnessloop check --root . --base main --head HEAD
check：基线 main...HEAD，1025 个变更文件，1 个 change 目录
  change：big
check：未通过 ✗（9 项）
  1. openspec/changes/big：change 目录不存在          ← 幽灵 active id（本 change 就是要消灭它）
```

- 期望修法（三选一，我倾向前两条一起做）：
  1. **把封顶对象从「广度」换成「病态深度」**：统计**逻辑路径深度**（或同一 `src` 被重复进入的次数）
     并设限 —— 自引用链接的特征是 `seen` 不断变长/同一 `src` 被反复进入，而合法的大目录只是「宽」。
  2. **超限时给一条点名 finding**（如「到达判定的展开超出上限 N ⇒ fail-closed」），**不要**静默降级成
     「没有任何 change 目录」——后者会把作者引向完全错误的方向。
  3. 若判定「>1000 文件的到达不在支持范围」，就把这条**明写进 `docs/gate.md §7`（能力边界）与 `spec.md`**，
     并仍然做第 2 条（点名文案）。
- ⚠️ 修完请补两条用例：① `specs/` 下 ~1500 个文件的**合法到达** ⇒ **绿**；② 自引用链接 ⇒ **红且能返回**（`F18` 已有）。

## Round 5：未验证项

1. 修复后需重跑 `battery.py` + `variants2/3/5.py` + `h5_launder.py` 全量。
2. `budget` 的**确切**阈值我只扫到「1005 绿 / 1015 红」这一档（未逐点二分）；扣减口径（每次出队扣 1，
   含被 `seen` 去重掉的重复项）是我**读码**得出的，未单独构造验证。
3. `F17` 前提里的「相似度下限」未扫参（见 R5-⑤）。
4. Round 1–4 的未验证项（浅克隆独立失败面、merge commit 形态、自定义 `review_manifest_glob` 与多段
   `required_artifacts` 的端到端、接入方真实数字）**仍未验证**。
5. 本 change 自己的门禁仍红（缺三份 manifest + 相邻 change 的 stale）——流程状态，本轮未复测。

## Round 5：建议（不阻塞）

1. `contract.py` 里 `prefix = seen if seen == src else seen`（Round 4 已提）**仍在**，两个分支同值 ⇒ 直接写 `seen`。
2. `F18` 这类「靠不终止来暴露」的用例，建议给测试套件配 `pytest-timeout`（或在该用例内用线程/子进程加超时），
   否则回退变异的表现是**挂起**而不是失败，在 CI 上就是一次超时排障。
3. `design.md §7.5` 从 Round 1 起就没再更新（现在停在「H1–M4 均已修复」）。四轮复验的结论都只在
   `reviews/building-review.md` 里；建议在收官时把这五轮的 H1–H6 与各自用例号补进 §7.5，
   否则 change 的设计档与实际修复史对不上。
