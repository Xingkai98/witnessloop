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

**CHANGES_REQUESTED（Round 2 复验后仍为此）**

- **Round 1 的 H1 已修复**（原构造复跑：`0 个 change 目录`，拒绝）✓；**M2**（gitlink 全域 fail-closed）
  与 **M4**（gate.md 登记）已修 ✓；battery **`与设计预期不符：0/20`**。
- 但修复只覆盖了「从 `Ev(A)` 的**根**可达的目录」：`report_path` 目标仍只在
  **manifest 的树路径匹配 glob** 时才解析（`contract.py:184`）。于是同一类绕过换个形状仍然成立——
  **manifest 走符号链接（真身在别处）时，它的 `report_path` 指向 `reviews/` 之外** ⇒
  借来的三份审阅报告**逐字节未改**、`check：通过 ✓`（H2，见「Round 2」）。

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
