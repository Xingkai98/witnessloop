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

**CHANGES_REQUESTED** —— 判据 5 存在一条**端到端可复现的绕过**：把到达目录的 `reviews/` / `specs/`
换成**指向「目录」的符号链接**（链接文本是目录名），实现只把该条目本身当 blob、**不展开目录内容**
（`spec.md:72` 明文要求「目标是目录 ⇒ 其下全部文件逐个比对」）⇒ 一份**逐字节未改**的现成审阅报告
+ `specs` 被整份复用，`check：通过 ✓`。另有 1 条 `spec` 明文 `SHALL` 未落实（gitlink）、
3 条测试/文档义务未落。

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
