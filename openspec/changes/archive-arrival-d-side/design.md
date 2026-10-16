# Design: archive-arrival-d-side

> 状态：草稿（grill 已完成 → 见 `reviews/grill-design.md`；对抗轮进行中）。
> **停轮门**：本文件 §6 逐条列出「为什么没有需要用户拍板的问题」，**其中 Q1 是 grill 提出、由本次改判据
> 自行裁定的**（另一条路也如实写下，供用户复核）。

## 0. 一句话

`git` 配不上 rename 时会留下**一条 `D`（旧 active 路径）+ 一条 `A`（archive 路径）**；
把那条**配得上对**的 `D` 认成「那次搬移的另一半」，使它**免解释事件**、并把它的源 id 从 active id 里排除。

## 1. 现状（逐行实测）

- **`D` 记录的字段落位**：`gitutil._parse_name_status`（`src/witnessloop/gitutil.py:210-225`）对非 `R`/`C` 记录
  走 `Change(raw, fields[i + 1])`（`:224`）——即被删路径进 **`path`**、**`old_path` 留 `None`**（`gitutil.py:16-22` 的 `Change`）。
- **受保护写入的豁免**：`checkcmd._protected_writes`（`src/witnessloop/checkcmd.py:346`）逐条记录判
  `_archive_move_exempt(change, pol, arrivals)`（`:373`）；而后者（`:324-343`）**第一句**就是
  `if not change.old_path: return False`（`:335`）
  ⇒ **`D` 记录永远拿不到豁免**——这正是 issue #31 那条红的来源。
  （`:339` 再要求 `old_path` 落在 `<changes_root>/<active-id>/` 下、`:342-343` 要求 `new_path` 落在某个到达目录下。）
- **到达组带 source_ids**：`contract.archive_arrivals`（`contract.py:253-324`）里 `group` 是
  `under_path(change.path, directory)` 的记录集合（`:300-302`），`sources`（`:314-320`）从 `group` 里
  **`old_path` 落在 `<changes_root>/<active-id>/` 下**的记录取——即 **git 自己配对出来的**那些源 id。
  那些 `old_path` 就是「这条到达目录是从哪个 change 搬来的」的**机器证据**。
- **幽灵 id 的既有处理**：`contract.changed_change_ids`（`contract.py:355-417`）用 `moved_sources`（`:378-392`）
  把源 id 从 active id 里排除。它只扫 `arrival.records`（= 新路径落在到达目录下的记录）⇒
  **纯 `D`+`A` 形态下 `moved_sources` 是空的**（没有 `R` 把源 id 带进来）。
  ⚠️ 混合形态（同一次 move 里既有配上的 `R`、也有配不上的 `D`）**今天已经没有幽灵 id**：
  配上的那些 `R` 已经把源 id 放进 `moved_sources`，而 `excluded`（`:393-402`）按 **id** 排除、同时看
  `(old_path, path)` 两侧 ⇒ 那条 `D` 的 `path` 顺带被排除。**所以 issue #31 的实测里只有「受保护写入」那一条红。**
- **复现（issue #31 原文）**：base `8e5fc83b`、head `d94c08334` + 归档目录名重绑 manifest ⇒
  `git diff -M --name-status` 里**只有一条 `D`**（`…/guard-write-allowlist/workflow-events.jsonl`），
  `check` 报 **1 项**「受保护路径被写入，但没有结构化解释事件」。本 change 在自己的测试里复刻了这个形态。

## 2. 决策

### D1 判据：把「配得上对的那条 `D`」认成搬移的一半

一条 `D` 记录（`status[:1] == "D"`）SHALL 被认成**某次到达搬移的另一半**，当且仅当**存在一个到达目录 `A`** 同时满足：

1. **源侧是 active**：`normalize(change.path)` 形如 `<changes_root>/<id>/<sub>`，`<sub>` **非空**
   （记录不能正好是目录本身），且该路径**不在** `<changes_root>/archive/**` 下；
2. **同一次 diff 里有一条配得上的 `A` 记录**：存在 `r` 使 `r.status[:1] == "A"` 且
   `normalize(r.path) == f"{A.directory}/{<sub>}"`（**相对子路径逐字相同**）；
3. **那个到达目录的源**恰是**这一个** change**：`A.source_ids == {<id>}`**
   —— 即 git 的相似度配对认为「`A` 是从 `<id>` 搬来的」，且**没有第二个** change 被配进来
   （`A.source_ids` 由 `contract.py:314-320` 收集：`group` 里 `old_path` 落在 `<changes_root>/<active-id>/` 下的那些记录）。

⇒ 该 `D` SHALL 免于「受保护路径被写入，但没有结构化解释事件」（**两档**受保护路径都适用）；
其源 id SHALL 与 rename 的旧侧一样**从 active change id 里排除**。

**为什么第 3 条是「**恰为** `{<id>}`」而不是「`<id> ∈ sources`」**（对抗轮 A1 的两条实测）：

- **`<id> ∈ sources` 仍可被洗白**：A1 的 **S2** 构造——在一个仍然活着的 change `b` 里
  `git mv` 一个小文件进某个到达目录 `A`（于是 git 配对 ⇒ `b ∈ A.source_ids`），
  再删掉 `b` 的受保护文件（`D`+`A` 同子路径）⇒ `check` **rc=0 全绿**；`b` 还活着却逃掉契约校验。
- **最狠的是它还会「零蓄意」发生**：A1 的 **S8**——只删掉整个 change 目录 + 在别处重建 manifest，
  git 自己就会给出**跨 change 的 `R055` 配对**（`another-change/reviews/grill.manifest.json → archive/<name>/…`，
  两份 manifest 的骨架本来就 >50% 相似）⇒ `<id>` 被污染、目标 finding 被洗白（5 项 → 3 项）。
- **A1 实测的三条路**（同一组构造）：
  | 路 | 判据第 3 条 | S1（issue 复现） | S2（拖一个活 change 进来） | S8（零蓄意跨配对） |
  |---|---|---|---|---|
  | 甲 | `<id> ∈ sources` | ✓ | **✗ 洗白** | **✗ 洗白** |
  | 乙 | 甲 + 源目录不在 head | ✓ | ✓ | **✗ 洗白**（S8 里那个源目录本来就没了） |
  | **丙（取）** | **`sources == {<id>}`** | ✓ | ✓ | ✓ |
- **取丙**：它是唯一同时挡住 S2 与 S8 的；代价如实登记——**当 git 把第二个 change 的文件也配进同一个到达目录时，
  这条搬移里所有的 `D` 都会**失去**豁免（多要一条解释事件）**。按本仓口径这是**响亮的保守**（fail-closed），
  也正是用户给的红线「不要为了变绿而放宽判据」的方向。
- ⚠️ 早先写过的「源目录必须在 head 树里消失」这一条**已删除**：乙 挡不住 S8，而且它会让 `D` 侧
  **比 `R`/`C` 侧更严**（部分搬移时，git 配上的免事件、配不上的孪生记录却要事件——同一件物理事实两种结论）。

**相对子路径的算法**（唯一一处实现）：两条都取前缀之后那段、**逐字相等**才算配对：
```
D 侧： p := normalize(change.path)；前缀 = f"{root}/{id}/"
A 侧： q := normalize(r.path)；   前缀 = f"{A.directory}/"
```
`<sub>` 为空（记录正好是目录本身）⇒ 不配对（第 1 条）。

**两条已知残留（如实登记）**：

- **纯 `D`+`A` 搬移**（一个 `R` 都没有 ⇒ `source_ids` 为空 ⇒ 第 3 条不成立）**不被豁免**：
  源侧受保护文件照旧要解释事件（**与改动前同结论**，不新增红）；其 manifest 本来也**必须**用归档目录名
  （`contract.py:314-320` 不给别名，#29 的次序已经这么写）⇒ 见 §3 N-i 与 §4 R1。
- **跨配对（A1 的 S8）**：git 把第二个 change 的文件也配进同一个到达目录时，
  这条搬移的 `D` **全部失去豁免**（多要事件）⇒ 见 §3 N-j 与 §4 R2。**这是刻意选的保守方向**。

### D2 落点：一个纯函数、一处消费（判据只此一份）

新增 `contract.d_move_halves(changes, policy, arrivals) -> frozenset[str]`：
返回**属于搬移另一半的 `D` 记录的规范化路径**集合（D1 的判据全在这里，只此一处）。
`checkcmd._archive_move_exempt`（`:324-343`）改成：`change.old_path` 那条路照旧；
`D` 记录（`old_path` 为空）则查集合成员。

⚠️ **`changed_change_ids` 不动**（A1 的 A1-2 订正）：早先写过「把 `D` 侧的源 id 并进 `moved_sources`」——
**那半已删除**，两个理由：
① 在「恰为一个源」的锚下，**纯 `D`+`A` 形态恒不成立**（`source_ids` 为空 ⇒ `d_move_halves` 恒空）
   ⇒ 那半在最好的情况下是 no-op；
② 在最坏的情况下它是**第二个洞**：把源 id 无条件并进 `moved_sources` 会让一个**还活着**的 change
   从 active id 里消失、逃掉契约校验（A1 的 S2 实测：`2 个 change 目录 → 1 个`）。
既不必要又危险 ⇒ **不碰**。（`:381-383` 那个死分支也**不**顺手动：它是独立于本 change 的既有代码，
动它要改既有钉子测试，超出本 issue 的面——已登记在 §4 R5。）

### D3 只认 `A`，不认别的

配对的另一半 SHALL 是**一条 `A` 记录**（`status[:1] == "A"`）。
`R`/`C` 记录天然带 `old_path`，走既有那条路；`M`/`T` 更不认（它们不表示「搬进来」）。

### D4 不改到达判据

`archive_arrivals` 的判据 1/2/3/5（`contract.py:290-313`）**一条不动**。
本 change 只在「到达组**之后**的消费面」上加一条：`D` 记录的对侧。

### D5 事件类型与 id 语义照旧

豁免的语义是「这条记录**不是**删除、是搬家的旧侧」⇒ 它本来就不该要事件。
**不**新增事件类型、**不**改 `_protected_writes` 对 `policy.protected_paths` 与不变集的两档规则。

## 3. 否定面（SHALL NOT 被本 change 放开；逐条有测试）

| # | 形态 | 为什么不被豁免 |
|---|---|---|
| N-a | 往**已存在**的归档目录里搬东西（`archive/<name>/` 在基准树里有 entry） | 它不是**到达** ⇒ 不在 `arrivals` 里（第 3 条的前提就不成立） |
| N-b | **单独**删一个 active change 的文件（diff 里没有配得上的 `A`） | 第 2 条不满足 |
| N-c | 删掉**整个** active change 目录（同一次 diff 里**没有**任何到达目录） | 第 3 条不满足（没有 `A`，也没有 source_ids） |
| N-d | 删掉整个 active change `b` **且**别处恰有一次正当搬移的到达目录 `A`（子路径重合） | **第 3 条**不满足：`A.source_ids == {另一个 change}` ——**grill 的 G1，实测改前会漏** |
| N-j | 在**仍然活着**的 change `b` 里 `git mv` 一个小文件进到达目录 `A`（污染 `source_ids`），再删 `b` 的受保护文件 | **第 3 条**不满足：`A.source_ids` 至少是 `{真源, b}` ⇒ **不等于 `{b}`**——**对抗轮 A1 的 S2** |
| N-k | **零蓄意**：删掉整个 change 目录 + 在别处重建 manifest ⇒ git 自己给出**跨 change 的 `R055`** 配对 | **第 3 条**不满足（`source_ids` 被污染）⇒ 该搬移的 `D` 全部保持要事件（保守）——**A1 的 S8** |
| N-e | 把**受保护文件从 active change 外**搬进到达目录（如 `openspec/specs/x.md`） | 第 1 条不满足（源不在 `<changes_root>/<id>/` 下） |
| N-f | `D` 的路径正好是 `<changes_root>/<id>` 本身（`<sub>` 为空） | 第 1 条要求 `<sub>` 非空 |
| N-g | 重建已存在的 `reviews/*.manifest.json`（`M`） | 与 `D` 无关；既有 1 格红的回归照旧 |
| N-h | `archive/<name>/` 缺必需件 / 内容来源存疑 / 是符号链接 | 不在到达组里 ⇒ 第 3 条不成立 |
| N-i | **纯 `D`+`A` 搬移**（一个 `R` 都没有） | 第 3 条不成立（`source_ids` 为空）⇒ 源侧受保护文件**照旧**要事件（**与改动前同结论**，不是新红） |

## 4. 风险

| # | 风险 | 处置 |
|---|---|---|
| R1 | **纯 `D`+`A` 搬移不被豁免**（N-i）⇒ 那种形态下源侧受保护文件仍要事件 | 如实写进 `specs/` 的 Scenario（**与改动前同结论**：本 change 只**减少**红、不新增） |
| R2 | **跨配对会让正当搬移的 `D` 失去豁免**（N-j/N-k）：git 的相似度配对（两份 manifest 骨架天然 >50% 相似）可能把第二个 change 的文件也配进同一个到达目录 | **刻意的保守方向**（fail-closed）：结果是**多要一条解释事件**，不是静默放过；另一种写法（自己算相似度 / 内容同一性锚）是**另一个面**，非目标 |
| R3 | 伪造空间：`D` 侧配对比 `R`/`C` 侧弱（后者是 git **逐文件**配对；前者只能靠「同相对子路径 + 源身份」推断） | 两侧的证据来源**同一个**（都是 git 的配对）；本判据仍**防漂移、不防蓄意伪造**（与既有边界同源）。**推断面比 `R`/`C` 窄**这条已如实登记 |
| R4 | 到达判定用的树读不出来 | 既有路径已经 fail-closed（`checkcmd` 在到达判定前就 `GitError` ⇒ 报 finding 退 1）；本函数不需要额外读树 |
| R5 | `changed_change_ids:381-383` 是**死代码**、而既有钉子测试对它是**空的**（grill 的 G4 + A1 复核） | **本 change 不动它**（超出本 issue 的面，动它要改既有测试）；如实登记，留给专门的小清理 |

## 5. 测试策略（TDD，先红后绿）

1. **正向**：复刻 issue #31 的形态（active change 在 base、head 里整体进 archive，其中一个受保护文件是 `D`+`A` 而非 rename，
   **其余文件有配上的 `R`**）⇒ `check` **通过 ✓**（改前红 1 项）。
2. **否定面**：§3 的 N-a…N-k 逐条一条测试（能端到端就端到端，细粒度直接测纯函数）。
   **两个杀手用例**：**N-d**（grill 的 G1：删整个 change + 别处一次正当搬移 ⇒ 改前会漏）与
   **N-j**（A1 的 S2：`git mv` 一个小文件污染 `source_ids` ⇒ 「`<id> ∈ sources`」那版会漏）。
3. **纯函数面**：`d_move_halves` 的配对算法（相对子路径逐字相等、前缀边界、`./` 归一化、`<sub>` 为空）。
4. **回归**：`tests/test_archive_awareness.py`（18 条 F 组 + 6 条 N 组）与 `tests/test_archive.py` 全绿。

## 6. 停轮问题（**无**；含 grill 提出的 Q1 的自行裁定）

| 候选问题 | 定案 | 依据 |
|---|---|---|
| **Q1（grill 提出）**：「`D`+`A` 配对要不要引入**身份锚**？」grill 给了三选一：**(甲-G)** 加锚 ／ **(乙-G)** 只靠子路径 + 放宽 manifest 别名集合 ／ **(丙-G)** 把「删整个 change 目录」从否定面划掉 | **取 (甲-G) 加锚**（锚 = 到达目录的源身份）。**(乙-G) 被否**：它要放宽接入方可见的 manifest `change_id` 别名集合——违反「不为变绿放宽判据」；**(丙-G) 被否**：它把「删掉一个 change 目录」变成合法洗白路径（grill 实测 `✗9 → ✗3`） | grill 报告文末的「处置」；`contract.py:314-320`（别名来源）；§3 N-d |
| **Q1′（对抗轮 A1 提出）**：grill 的锚**还不够**（S2 拖活 change 进来、S8 零蓄意跨配对都能洗白）。A1 实测三条路：**(甲-A)** `<id> ∈ sources` ／ **(乙-A)** 甲 + 「源目录不在 head」 ／ **(丙-A)** `sources == {<id>}` | **取 (丙-A)**（最保守）。依据：只有它同时挡住 S2 与 S8；**(乙-A)** 挡不住 S8（S8 里那个源目录本来就没了）且会让 `D` 侧比 `R`/`C` 侧更严。**代价**：跨配对时这条搬移的 `D` 全部失去豁免（多要事件）——**刻意的 fail-closed 方向**，见 §3 N-j/N-k 与 §4 R2 | A1 报告 `grill-adversarial-a1.md`；§2 D1 的三路对照表 |

| 「要不要让 `R`/`C` 也要求源目录消失？」 | **不要**：`R`/`C` 的配对是 git 算的（有证据），今天的行为被 F 组 18 条钉住；改它超出本 issue | `contract.py:274-280`（`moved_content` 用 git 的配对）；`tests/test_archive_awareness.py` 的 F 组 |
| 「相对子路径要不要允许「同 basename 即可」？」 | **不要**：那会把「删 `b/tasks.md`」配上「`A` 的 `archive/<name>/x/tasks.md`」等错配；逐字相等是唯一可复算的口径 | §2 D1 的算法 |
| 「要不要把 `D`+`A` 也喂给到达组的 `sources`（源 id 别名）？」 | **不改**：那是放宽 manifest 的 `change_id` 校验面（接入方可见契约）；issue #31 的实测里那种形态**没有**「与目录不符」的红（归档目录名本来就在别名集合里） | issue #31 原文的实测输出；`contract.change_targets` 的 `accepted_change_ids` |
| 「事件文件之外的受保护文件（如 manifest）也会掉队吗？」 | **是**，同一条规则覆盖：`_protected_writes` 对**两类**受保护路径共用 `_archive_move_exempt` | `checkcmd.py:346-356` 的两档规则 |
