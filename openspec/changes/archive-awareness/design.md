# Design: archive-awareness

> 状态：**草稿**（grill → 设计对抗验证 **已回写** → **用户 2026-10-15 已停轮裁定**，见 §8；实现待任务单）。
> 依据 `proposal.md`；流程出处 `templates/grill.md`。
> 本文所有「实测」均为**本仓当前树**（基线 `ae99256`）上的复核：命令与输出见 §1，草稿期**未**改动任何 `src/`。

## 0. 一句话

给工具补上「**这个 change 被归档了**」这个表示：归档 move（`git mv changes/<id>/… → changes/archive/<name>/…`，R100）
把它带走的那个 change **放回本次 diff 的 change 集合**（id = 归档目录名，路径落在 `archive/<name>/` 下），
于是 ①`require_change_for` 不再误报、②`manifest build` 能解析归档目标、③`events` 扫得到归档目录——
**且不产生「归档一下就绕过三条证据门禁」的新口子**（§1.2 证明这是本 change 的主要风险）。

## 1. 现状（实测）

### 1.1 三条症状的根因（逐行核对，行号未漂）

| 位置 | 现状 | 后果 |
|---|---|---|
| `contract.py:58-86` `changed_change_ids` | 归档 move 的**新路径**（`archive/**`）与**旧路径**（`archived_sources`）都被 `continue` 掉 | 归档后集合恒为空 ⇒ 症状 ① |
| `contract.py:34-35` `change_dir` | 只解析 `changes_root/<id>` | 归档后 `manifest build` 判「change 目录不存在」⇒ 症状 ②（`manifestcmd.py:72-75` 复用同一判定） |
| `events.py:83` `load_all` | 一级 glob `f"{changes_root}/*/{events_file}"` | 归档 change 深一层 ⇒ 事件永不进池 ⇒ 症状 ③ |

**排除本身是对的**（`contract.py:59-63` 的注释就是理由）：不排除的话，
`archive` 会被当成一个 change id 去要 `proposal.md`，而**搬走的 active 源目录**会被报「目录不存在」
（`validate_change_dir:94`）。缺陷不是排除，而是**排除之后没有补上「归档发生了」这件事实**。

症状 ② 的报错文案里那句「diff 里出现了它的文件，但目录不在工作树中」是 `contract.py:94` 的**固定文案**，
**不是**对本次 diff 的观察——引用它时别当成证据。

### 1.2 ⚠️ 最要紧的实测：归档会让**三条证据门禁一起静默失效**

三个对照仓（同一份「零 manifest」的 change，只差它在不在 active），`check --base HEAD~1 --head HEAD`：

```console
# C1b-A：同 PR 新建 active change x（件齐、零 manifest，reviews/ 里**有实体文件**）+ 改 src/app.py
check：… 6 个变更文件，1 个 change 目录
  1. openspec/changes/x：缺少 review manifest（…）
  2. openspec/changes/x：无 stage=grill 的 manifest（现有 stage：（无））…
  3. openspec/changes/x：无 stage=grill-adversarial 的 manifest（现有 stage：（无））…
  4. openspec/changes/x：无 stage=building 的 manifest（现有 stage：（无））…
EXIT=1

# C1b-B：同上，但**没有** reviews/ 目录
check：… 5 个变更文件，1 个 change 目录
  1. openspec/changes/x：缺少必需件 reviews
  2. openspec/changes/x：缺少 review manifest（…）
  3. openspec/changes/x：无 stage=grill 的 manifest（…）
  4. openspec/changes/x：无 stage=grill-adversarial 的 manifest（…）
  5. openspec/changes/x：无 stage=building 的 manifest（…）
EXIT=1                      ← 两种造法都指向同一结论：三条 stage 门**都在跑**

# C3：同一个 change 在**同一个 PR 里被归档** + 改 src/app.py
check：… 6 个变更文件，0 个 change 目录
  1. src/app.py：src/app.py 属于必须挂 change 的路径（…），但本次 diff 里没有任何 change 目录（…）
EXIT=1                      ← 上面那 4 条**一条都没有**

# C2：纯归档（不改代码）、该 change 零 manifest
check：… 5 个变更文件，0 个 change 目录
check：通过 ✓
EXIT=0
```

机制在 `checkcmd.py:73-110`：`change_ids` 空 ⇒ `:79` 的 `for` 循环**空转** ⇒ 连 `:96` 的
`if code_hits:`（`building` / `grill-adversarial` 两条硬门）也**不执行**。

⚠️ **C1b 为什么列两个变体**：变更文件数取决于 `reviews/` 里**有没有实体文件**——git **不跟踪空目录**。
立项稿初版写的「5 个变更文件 + 4 项红」只在工作树里**恰好有一个未跟踪的空 `reviews/` 目录**时成立
（那正是我当时的临时仓），**从干净检出重跑不出来**（grill 实测）。⇒ 引用本表时请连**造法**一起引用。

⇒ **两条结论**（本 change 的全部形态都由它们决定）：

1. 今天 C3 那份 PR 是红的——但**红在错误的理由上**（误报 ①），而三条真门禁**根本没跑**；
2. 因此 ① 的修法**不能是「豁免」**：一旦只让 `_require_change` 闭嘴，C3 就从「1 项红」变成
   「**0 项红**」= 一个改了 `src/**` 却零 change 证据的 PR 直接放行 ⇒ **本 change 自己造出一个绕过通道**。
   修法只能是**「把归档 move 带走的那个 change 放回 change 集合」**（D2）。

### 1.3 三条症状是**同一个故事**（接入方的时序）

接入方的硬规则是「**实现 PR 同时归档**」，而归档之后还有收尾（`openspec/specs/**` 并入、
`docs/*-backlog.md` 清理）——这些写入**不是**证据文件 ⇒ 会让证据立刻 stale（`docs/gate.md §3.1`）。
于是顺序被逼成：**实现 → 归档 → 收尾 → 产出证据（reports + manifest + events）**。
最后一步要在**归档态**上做 ⇒ 撞 ②（build 拒绝）、③（事件写在归档目录里但扫不到）；
而 ① 让整条链在第一跳就红。⇒ 三处**必须一起修**，缺一条时序上就是死结。

### 1.4 参考实现研究（本仓的形态）

- **本仓的「参考实现」有两份**：①本仓自身的既有机制（`is_archive_move` / `archive_root` /
  `stale_exempt_paths` 里的 `archive/**`——归档豁免已经做了一半，本 change 是把它补完）；
  ②接入方 asterwynd 的实测记录（issue #21 引用其 PR #309 的 `stage-b-observations.md`）。
  **研究方法 = 在真 git 仓上复现**（§1.1/§1.2 的对照仓都可重跑），而不是读代码推断。
- ⚠️ **本仓没有 asterwynd 的 `Impact Analysis` / `RIR`（`research_tier`）/ benchmark gate**——
  那三条是**接入方的项目特有检查**，本仓在 change `building-review-gate` 里**明确列为非目标**
  （`openspec/changes/building-review-gate/proposal.md:52`、`tasks.md:54`）。本 change 的
  「影响面」因此落在**本仓自己的**载体上：§2.5（豁免面边界表）、§3（接线点）、§4（风险）、§5.2（回归面清单）。
- **asterwynd 侧数据只采用两条**：80 份归档事件文件零命中（症状 ③ 的规模）、归档态跳过 `tasks_hash`
  （本仓**不照抄**，理由见 D5）。**其余不复用**——它的 `ChangeType` / `_check_archived_completion_gate`
  与本仓形状不同（`docs/gate.md §10` 已记沿革）。

### 1.5 ⚠️ 归档的三条**连锁**（初版与 grill 稿都没写全 · **对抗轮实测逼出**）

1. **归档目录名 ≠ 源 id ⇒ 既有 manifest 全判「与目录不符」；而「重建」这条补救**跑不通**。**
   实测：`--change gwa` 在归档前 build ⇒ `change_id="gwa"`；搬进 `archive/2026-10-14-gwa/` 后，
   按 D2 的 label（`openspec/changes/archive/2026-10-14-gwa`）喂给**现有**校验器 ⇒ **每份 manifest 1 条**
   `manifest.change_id='gwa' 与目录不符`（`contract.py:250` 比的是 **label 末段**）。
   ⚠️ **初版给的补救（「用归档目录名重建」）在同一个 PR 里是死路**——见第 2 条。**定案：加别名（D8）**，
   **不重建**：归档态 target 的 `change_id` **同时接受**「归档目录名」与「源 id」（两者被本次 diff 的 move 机械地连起来）。
   实测：**只归档不重建** ⇒ 修后 **0 项红**（E1-①）；不加别名则是每份 1 条「与目录不符」。
   ⚠️ **本仓既有测试抓不到这条**：`tests/test_archive.py` 的归档是 `archive/add-retry`（**与源 id 同名**），
   末段比对恰好成立 ⇒ §5.1 必须补一条「**先用源 id build、再归档到 `<date>-<id>`**」的先红用例。
2. **⚠️ 在同一个 diff 里「move + 改写被 move 的文件」= `R<100`，会同时炸三处**（本仓实测，四个数）：
   同 PR 内 ① 归档 + ② 用归档目录名重建三份 manifest + ③ 各写一条解释事件：

   ```console
   ① 只归档（R100，未重建）                修后 EXIT=0  0 项      ← 别名让既有 manifest 直接过
   ② 再重建 manifest                       修后 EXIT=1  9 项      ← git 把三份 manifest 报成 R075/R077
      1-3. openspec/changes/gwa：change 目录不存在 / 缺少 review manifest / 无 stage=grill   ← **幽灵 active id**
      4-9. 受保护路径被写入…×6（归档侧 3 条 + **旧路径侧 3 条**——rename 的两半各记一次）
   ③ 补 3 条事件（归档侧）                  修后 EXIT=1  6 项
   ③b 再补 3 条（旧路径侧）                 修后 EXIT=1  3 项      ← **那 3 条幽灵 id 补事件消不掉**
   ```

   机制：`is_archive_move` 要求 `R100`（`contract.py:45`）⇒ 内容一变就不是归档 move ⇒
   ①**不授予**任何归档 id，②旧路径不再进 `archived_sources`（`contract.py:67-71`）⇒ 被搬走的 `gwa`
   **以 active id 的身份回到 change 集合**（`validate_change_dir` 报「目录不存在」+ 缺件 4 条 = 5 条），
   ③`_protected_writes` 对 rename 记**两半**（`checkcmd.py:243-245`）⇒ 一次重建要 **2** 条事件（不是 1 条）。
   ⇒ **禁止这个形态**：`docs/gate.md` 要写明「**归档 move 必须是纯改名**：同一个 diff 里不得同时改写被移动的文件」，
   并给出上面的后果清单（否则接入方撞上后只会看到一堆看不懂的红）。
3. **重建（覆盖）已存在的 manifest = `M` 一个不变集路径（`policy.py:22`）⇒ 每条各要一条解释事件。**
   实测（**归档已在 base、本 diff 不含该 move**）：重建三份 manifest 而不写事件 ⇒ `check` **恰好 3 项**
   「受保护路径被写入，但没有结构化解释事件」；补 3 条 `protected_path_write`（`artifact_path` 指向那三份）
   ⇒ **`EXIT=0`，绿**（E2-C' ④⑤）。
   ⚠️ **边界**：同一 revision 上重复 build 是**逐字节幂等**的（本仓已文档化的性质）⇒ 不产生 `M`、不吃事件。
   ⚠️ 这条**只在「该 diff 不含那个 move」时有意义**（否则先撞第 2 条）。

### 1.6 ✅ 由此定下的**正确顺序**（修后实测 `EXIT=0`，0 项红）

```console
① 内容：实现 + 收尾（openspec/specs/**、backlog 清理…）——**所有非证据改动都在这**
② 证据：在 **active 态** build（`--change <id>`，绑 ① 的 revision）——`change_id` 就是**源 id**
③ 归档：`git mv changes/<id> → changes/archive/<date>-<id>`，**纯改名、放最后**
```

实测（E2-B'，`check --base <base>`）：变更文件 11 个（其中 3 份 manifest 是 **`A`**、其余是 `R100`）、
`1 个 change 目录`、**`EXIT=0`，0 项红** ⇒ 接入方的「实现 PR 同时归档」这条路**是通的**，
前提是**归档 move 是这一串提交里的最后一个**、且**不动被 move 的文件**。
⚠️ 若确实要在归档**之后**改写证据（例如换 revision 重绑），那是**不含 move 的后继 diff**（第 3 条：3 条事件）。

## 2. 决策

### D1 归档态 change id 的口径 = **归档目录名**（`archive/<name>/` 的 `<name>`）

三个候选：

| 候选 | `check` 侧 | `manifest build` 侧 | 结论 |
|---|---|---|---|
| **归档目录名**（选它） | 从 move 的**新路径**取 `archive/` 后一段，现成 | `archive/<name>` **精确命中**，零猜测 | ✅ 与 active 同构（id = 目录名） |
| 源 id（move 旧路径首段） | 也能取到 | ⚠️ 没有 diff 可看 ⇒ 只能在 `archive/` 下按 `*-<id>` 后缀猜（**加一条「歧义即报错」的守卫是可实现的**） | ❌ 但见下：真正的硬约束不是「不可落」 |
| 目录名前缀日期解析 | 需要约定 `<date>-`（本仓既有测试用 `archive/<id>`，**没有**日期前缀） | 同左 | ❌ 引入本仓没有的约定 |

⇒ **id 就是 change 目录的名字**，active 与 archive 一致；**不解析日期前缀、不回查旧路径**
（旧路径只用来判「这是不是一次真的归档 move」，见 D2）。

⚠️ **真正的约束在哪（对抗轮纠正了初版的理由句）**：不是「源 id 口径不可落」，而是
**`contract.py:250` 的交叉校验比的是 label 末段**（= change 目录的名字），且 `check` 与 `manifest build`
**必须共用同一个校验器**（本仓反复禁止「两边各写一套」）。想走「身份 = 源 id」就得给归档态单开一套校验器
或把 id 与 label 拆成两个参数——前者正是本仓要避免的漂移面，后者让「身份 = 目录名」这条一贯口径出现例外。
⇒ 结论保留（**身份 = 归档目录名**），但**代价要明码标价**（见 §1.5）：
归档改写了名字 ⇒ 归档**前**产出的 manifest 名字对不上 ⇒ 本 change 因此加了一条**别名** D8
（而不是让接入方去重建——重建在同一个 PR 里跑不通，见 §1.5 第 2 条）。

**被评估并否掉的一条备选：把归档命名收紧成 `archive/<id>`**（去掉 `<date>-` 前缀 ⇒ 名字不变 ⇒ 别名与
§1.5 第 1 条整类消失；对抗轮实测：同一 fixture 下红数 6 → 3）。**本 change 不选它**，理由两条：
① 它**修不了接入方的问题**——接入方现有 **80 份**归档目录就是 `<date>-<id>` 形态，且这是 **OpenSpec
`openspec archive` 自己的约定**；把授予判据收紧成「必须等值」会让他们的归档 move 一概**不授予** ⇒ 症状 ① 原样回来；
② 别名（D8）已经让两种命名**都能用**，再要求改名只增加迁移成本（80 个目录改名 = 每个目录里的 manifest
都会被判「旧路径删除」⇒ 约 **240 条**解释事件），收益是「少一个别名分支」。
⇒ 它作为**政策题**留给用户：见 §8 的 **Q2**（不改本 change 的实现——D8 在两种命名下都成立）。

### D2 归档 move ⇒ 该 change 进入本次 diff 的 change 集合，**按归档路径走同一套校验**

`changed_change_ids` 增加**归档维**。一次 move **授予资格**要同时满足**两条**：

1. `is_archive_move` 为真（R100 + 源在 active）——`is_archive_move` **一行都不改**
   （它是防伪造的锚：新建 `archive/<name>/…` 是 `A` 状态、无 `old_path` ⇒ 永远不算归档）；
2. **目标目录名认得源 id**：`<name> == <源id>` 或 `<name>.endswith("-" + <源id>)`
   （`<源id>` = 旧路径里 `changes_root/` 之后的首段；`<name>` = 新路径里 `archive/` 之后的首段）。
   **只做等值 / 后缀比对，不解析日期**。

授予后，id = `<name>`（D1）。**为什么需要第 2 条**（grill 挖出的第 6 面，本仓实测）：
`git mv openspec/changes/z/notes.md openspec/changes/archive/y/notes.md`（把 active change `z` 的**单个文件**
搬进一个**已存在**的归档目录 `y`）⇒ `git diff` 报 **R100**、`is_archive_move` = **True**
⇒ 不加第 2 条的话，资格会被**凭空授予 `y`**，而源 change `z` 因 `archived_sources`
（`contract.py:70`）被排除、**静默逃检**。加了第 2 条：`y` ≠ `z` 且不以 `-z` 结尾 ⇒ **拒绝**
⇒ 回落到今天的行为（`_require_change` 照样命中、照样红）。见 §2.5 的残留边界。

`checkcmd.run` 的循环从「id 列表」改成「`(id, directory, label)` 三元组」：
active ⇒ `changes/<id>`，归档 ⇒ `changes/archive/<name>`，`label` 用**仓根相对的真实路径**。
`contract.py:250` 的 `manifest.change_id` 交叉校验取 `label` 末段 ⇒ 与 D1 的 id 自洽
⚠️ **但只对「归档后产出」的 manifest 逐字成立**：归档**之前**用 `--change <源id>` build 的 manifest
（`change_id="<源id>"`）名字对不上 ⇒ 靠 **D8 的别名**吸收（**不是**靠重建——重建在同一个 diff 里跑不通，
§1.5 第 2 条）。**这条必须写进文档与测试**，否则接入方会在归档那一刻撞上一串新红。

### D3 `_require_change` 由 D2 自动修好（**不是**给它加豁免）

`change_ids` 非空 ⇒ `checkcmd.py:194` 直接返回 `[]`。⚠️ **不要**给 `_require_change` 加
「有归档 move 就放行」的分支——那正是 D2 要避免的绕过面。顺带改文案（提一句「本次 diff 里也没有归档 move」）。

### D4 `manifest build` 支持归档目标

解析顺序（`--change X`，`X` 仍是**单段**，`/` 照旧一律拒——归档目录名是单段，规则不变）：

1. `<changes_root>/X` 是目录 ⇒ active（今天的行为）；
2. 否则 `<changes_root>/archive/X` 是目录 ⇒ **归档**；
3. 否则 ⇒ 报错、**不写任何文件**。⚠️ 若 `archive/` 下存在名字以 `-X` 结尾的目录，
   报错文案**提示**它（「归档态请用**目录名**作为 change id，例如 `--change 2026-10-14-X`」），
   **但不自动认**——自动认就要猜（§2.6）。

其余全部复用既有实现：`validate_change_dir` 在**解析后的目录**上跑；
`--report` 相对**解析后的目录**解析（`contract.resolve_report_path(directory=…)` 本来就吃目录）；
`manifest_rel` 必须由**解析后的目录**推（`manifestcmd.py:149` 现在写死 `changes_root/<id>`，要改）；
`reviews/` 前缀守卫、逃逸守卫、`reviewer≠author` 守卫一律不变。

⚠️ **配套顺序：见 §1.6**（修后实测 `EXIT=0` 的那条）。
**初版写的「归档后重建 manifest」是错的**——它在同一个 PR 里跑不通（§1.5 第 2 条：`R<100` ⇒
不授予 + 幽灵 active id + 事件翻倍）。**本 change 的答案是别名 D8**：
归档态 target 的 `change_id` 同时接受「归档目录名」与「源 id」⇒ **归档前产出的 manifest 不需要重建**，
`manifest build --change <归档目录名>`（新产出的证据）与 `--change <源 id>`（归档前的证据）**都能过**。
⚠️ 真要改写**已存在**的归档 manifest ⇒ 那是 `M` ⇒ 每条一条解释事件（§1.5 第 3 条），
且该 diff **不得同时包含那个 move**。
⚠️ 边界（grill R5）：`<changes_root>/archive` 本身是目录 ⇒ `--change archive` 会走「active」分支并报
「缺少必需件 proposal.md」；`docs/gate.md §3.2` 要写一句，提示语也要兜。

### D5 已归档 change 的 `tasks_hash`：**照算，不跳过**

1. `tasks_hash` 是 manifest 的**必填字段**（`constants.REVIEW_MANIFEST_REQUIRED_FIELDS`），
   `check` 的 `_check_hashes` 拿它与 change 目录里的 `tasks.md` 对齐——跳过就要么多出**第二种 manifest 形状**、
   要么给 `_check_hashes` 开特例，两者都是本仓刻意避免的**漂移面**（同一个教训：`HASHED_ARTIFACTS`、`resolve_report_path` 各只留一份实现）。
2. **归档不改字节**：R100 ⇒ 归档后的 `tasks.md` 与归档前**逐字节相同** ⇒ 同一个 hash 在归档前后**都成立**，
   口径**没有任何变化**（不是「为归档引入新口径」，是「同一份文件换个位置」）。
3. asterwynd「归档态跳过 `tasks_hash`」是**它的**形态：本仓不复核其成因，也不照抄。
   若某个接入方的归档器会**改写 / 删除** `tasks.md`，那它**本来就不是** R100 归档
   ⇒ `is_archive_move` 不认它 ⇒ 整套归档感知对它**不适用**（届时 `check` 报的是「缺少必需件 tasks.md」这类
   既有 finding）。这是**自洽**的，不需要特例。

### D6 `events` 扫描覆盖归档目录：**两条显式 glob**，不 dedup

```python
for pattern in (f"{changes_root}/*/{events_file}", f"{policy.archive_root}/*/{events_file}"):
    for path in sorted(root.glob(pattern)): …
```

- **不用 `rglob` / `**`**：那会吃到 `archive/<name>/notes/workflow-events.jsonl` 这种**再深一层**的同名文件
  ⇒ 多出「谁都能放一份授权文件」的面。两条 glob 各自只覆盖**一个**目录层级（实测：
  `archive/y/sub/workflow-events.jsonl` **不**被任何一条命中）。
- ⚠️ **两条必须写准的既有口径**（立项稿初版在这里写错过，grill 实测纠正）：
  - `<changes_root>/*/<events_file>` 的 `*` **也匹配 `archive`** ⇒ `openspec/changes/archive/workflow-events.jsonl`
    （`archive/` **直接下**、不属于任何 change 目录）**今天就会被读**；
  - 新增那条 `archive/*/<events_file>` 的 `*` 匹配**任何**目录名 ⇒ `openspec/changes/archive/notes/workflow-events.jsonl`
    **会被读**（`notes` 被当成一个「归档 change 目录」——与本仓让 `is_archive_move` 接受任意 `archive/<name>/` 同款）。
  ⇒ 真正的否定面是「**再深一层**」，不是「`archive/` 一级下的非 change 目录」。`docs/gate.md §4` 要照这句写（§6）。
- **不 dedup**：`covers`（`events.py:88-103`）是**存在性**判定，不是计数——同一 change 在 active 与
  archive 各有一份时两份都读、**任一条命中即豁免**；两份内容不同则**并集**生效。
  这与今天「多个 change 目录的事件合并成一个池」是同款语义（`load_all` 本来就是并集），
  所以「同一 change 的事件只算一份」不需要新规则。
- ⚠️ **诚实边界（授权面变宽）**：事件池从「active 一层」扩到「active + archive 一层」。
  归档 change 的事件与其他事件**同等权威**——`event.change_id` 是 informational、`check` **不消费**它
  （`docs/gate.md §4`）。这不是新边界（今天任意 change 目录里的事件都能豁免任意路径，`docs/gate.md §7`
  的「防漂移不防伪造」），但**池子变大了**（接入方 80+ 份）⇒ 文档必须写准（§6）。见 §2.6（已定案）。
- ⚠️ **已知别扭（既有，非本 change 引入）**：归档目录里的 `workflow-events.jsonl` 在**不变集**里
  （`policy.INVARIANT_PROTECTED_PATHS` 的 `**/workflow-events.jsonl`）⇒ **A 免解释、M/D 要解释**。
  于是「往已存在的归档 events 文件里 append 一条事件」= `M` = 要一条解释事件，
  而那条事件**自己**就写在同一个文件里（`covers` 允许：`artifact_path` 指向该文件本身即可）。
  active change 今天就是这个形态，**本 change 不改**，但写进文档（否则会被当成新 bug 报）。

### D7 「id → 目录」的映射只留**一份实现**，且**以目录为键**（tie-break 定死）

新增 `contract.change_targets(root, pol, changes)` → **列表** `[(change_id, directory, label)]`
（active + 归档**并集**，`label` = 仓根相对的真实路径）。⚠️ **必须是列表、以目录为键**：
单段 id 会撞车——**实测可构造**（E3''）：base 里同时有 `changes/x`（新）与 `changes/archive/x`（旧），
本 PR 做 `git mv changes/x/notes.md → changes/archive/x/notes.md`（`R100`、`name == 源 id` ⇒ **授予 `x`**）
**且**同 PR 新增 `changes/x/extra.md`（⇒ active id 也是 `x`）⇒ **同一个 id `x` 来自两个不同目录**。
⇒ **定死**：映射**以目录为键**、**两份都校验**（不合并、不覆盖、不静默丢一份）。
撞车天然 fail-closed：那一对里通常至少有一份不合契约（实测：8 项红，两侧各自「缺少 review manifest + 三条 stage 门」）。
⚠️ **不得**实现成 `dict[change_id] = directory`——那会**静默丢掉一份**（丢掉哪份取决于实现），
而这条 diff 是攻击者可以构造的。

`validate_change_dir` / `validate_review_manifests` 改为接受**解析后的目录 + label**（`evidence.py`
早就是「吃目录」的形状，只需传归档目录）。`change_dir` 保留（`guard` 与 active 路径仍用它）。
理由：本仓已经因为「两边各写一套路径口径」踩过坑（`resolve_report_path` 的注释、`HASHED_ARTIFACTS`）——
归档解析如果 `check` 与 `manifest build` 各写一套，症状 ② 会以另一种面貌回来。

### D8 归档态 target 的 `change_id` **同时接受两个名字**（源 id 与归档目录名）

**规则**：对一个由 D2 授予的归档 target（源 id = `S`、归档目录名 = `N`），manifest 的 `change_id` 字段
SHALL 被接受，当且仅当它等于 `N` **或** `S`。`manifest build --change X` 写下的**新** manifest 仍是 `N`
（= 归档目录名，D1 的身份）；`S` 是**别名**，只为让**归档前产出**的 manifest 继续有效。
这是**同一个校验器的一个参数**（接受的名字集合），**不是**第二套校验器、也不是第二份实现。

**为什么必须有它（而不是「重建」）**：没有别名，归档那一刻既有 manifest 全部判「与目录不符」（每份 1 条），
而唯一的补救「用归档目录名重建」在**同一个 diff** 里会毁掉 `R100` ⇒ 不授予 + 幽灵 active id + 事件翻倍
（§1.5 第 2 条，实测 9 → 6 → 3 项，最后 3 项**补事件消不掉**）。⇒ 加别名后：**只归档不重建 ⇒ 修后 0 项红**（E1-①）。
⚠️ **同一归档目录被多条 move 指向时，别名取并集**（实现期由 building-review 的 I6 逼出）：
`<name> == <源id>` 或 `-<源id>` 后缀可能对**多个**源同时成立（如 `z` 与 `foo-z` 都指向 `archive/2026-foo-z`）。
实现 SHALL 收集**所有**满足的源——取「diff 里先出现的那一个」会让别名随 **diff 顺序**漂移（不可复现），
正是 D7 立下「不许静默丢一份」要防的那类口径。

**代价（写明）**：归档态 manifest 的 `change_id` 因此可能出现两种字面（`gwa` 与 `2026-10-14-gwa`），
下游自建工具读它时要按「两者皆可」理解（R4）。**没有收紧命名的替代收益**见 D1 的备选段与 §8 Q2。
⚠️ 别名**只在授予发生时**（即该 diff 里含搬进该目录的 move）有意义——归档态 change 在别的 diff 里
根本不被校验（授予是按 diff 派生的，实测：不含该 move 的 PR ⇒ 0 项红、该 change 不进集合）。

## 2.5 豁免面：**归档 move 不豁免任何东西，它只是「归属」**（issue #21 的核心问题）

issue 问的是「① 只豁免它自己这一次 diff；② 还是同时豁免同 PR 内对该 change 覆盖路径的代码改动」。
本 change 的答案是**③ 两者都不是**：归档 move 使该 change **重新成为本次 diff 的 change**，
于是同 PR 的代码改动由**这个 change 自己的证据**回答——与今天「active change + 同 PR 代码改动」
的关系**逐字同构**，没有新的豁免概念，也没有新的「覆盖路径」概念（本工具从来没有 change↔路径 映射）。

| 动作 | 该 change 进集合？ | 走证据门禁？ | 依据 / 钉住它的用例 |
|---|---|---|---|
| `git mv changes/<id>/… → changes/archive/<name>/…`（**R100**，源在 active） | ✅（id=`<name>`） | ✅ 同 active | 本 change 核心；`test_archive.py` 6 条 |
| 同 PR 内的**代码改动**（`src/**`…） | —— | **不被豁免**：`code_hits` 触发 `building` / `grill-adversarial`，且要有该 change 的 manifest | §1.2 的 C1b/C3 对照 |
| **新建** `archive/<name>/…`（`A`，无 active 源） | ❌ | —— | N2：`is_archive_move` 要求 R100 + 源在 active |
| 改 / 删 `archive/<name>/` 里**已存在**的文件 | ❌ | —— | N4：否则「碰一下归档目录」比「什么都不建」还便宜 |
| **删除** `changes/<id>/`（`D`，非 rename） | ✅（active id 仍在） | ✅ | N3：仍报「change 目录不存在」 |
| 归档 move **带走内容改动**（`R<100` / `D+A`） | ❌（不是归档） | —— | 既有 `is_archive_move` 语义不动 |
| ⚠️ **同一个 diff 里既 move 又改写被 move 的文件**（如「归档 + 在归档态重建 manifest」） | ❌（`R<100` ⇒ 不授予）**且源 change 以幽灵 id 回到集合** | —— | §1.5 第 2 条（实测 9→6→3 项，其中 3 项补事件也消不掉）⇒ **禁止这个形态**，N7 钉住 |
| 把**受保护 spec** 挪进 `archive/` | ❌ | —— | `test_archiving_a_protected_spec_still_needs_an_event` |
| **第 6 面**：`git mv changes/<z>/<单个文件> → archive/<y>/<…>`（`R100`，目标目录**已存在**、且名字**不认得** `<z>`） | ❌（D2 第 2 条拒绝） | —— | 本仓实测：`is_archive_move=True`、`changed_change_ids` 今天 = `[]`；不加 D2 第 2 条就会被**凭空授予 `y`** 且 `z` **静默逃检** ⇒ N6 钉住 |

**残留边界（诚实写明，两条）**：

1. 一个 PR 里「归档 X」与「改 `src/`」之间**没有机械归属**——工具只保证「这个 PR 里存在一个**证据齐备**的
   change」，不保证那份证据是为这段代码写的（与今天 active change 完全同款，`docs/gate.md §7`）。
   **这不是本 change 引入的**，但本 change 让「归档」成为一条新的取得该资格的路 ⇒ 必须写进文档与否定用例。
2. **D2 第 2 条之后仍有残留**：名字**恰好**认得源 id 的「部分 move」——
   例如 `git mv changes/y/<单个文件> → archive/2026-10-14-foo-y/<…>`
   （`<name>` 以 `-y` 结尾 ⇒ 第 2 条放行）。此时授予的是**已存在的** `2026-10-14-foo-y`、而源 `y` 仍被排除。
   实测与校准（grill R1）：**要真变绿还必须在攻击 HEAD 上重建目标 change 的 manifest**
   （否则 `_check_git_span` 的 stray 会因 `src/**` 非证据而判「审阅的是旧 revision」）；
   而「碰一下 active change + 重建它的 manifest ⇒ 绿」**今天就已经可行**（grill 实测的一个不用归档技巧的攻击）。
   ⇒ 与既有边界**同类等价**，**不阻塞**；登记在此 + 写进 `spec.md` 的 Requirement 说明，不假装它不存在。

## 2.6 Code-Resolved Questions（**不进停轮队列** · 由代码与实测定案）

> grill 判定这三条**能由代码/证据定案**（`templates/grill.md` §3：能由代码或规格直接判定的进
> `## Code-Resolved Questions`，**不停轮**）。下面是结论 + **本仓复核**的依据。
> ⇒ 本文档对它们的**编号引用一律改成 CQ1/CQ2/CQ3**（不再写 Q2/Q3/Q4），
> 免得与停轮项 Q1/Q2（**已裁定**，见 §8）混淆——那两条才是要用户拍板的，本节三条不是。

- **CQ1（原 Q2）归档态 change id 只能是「归档目录名」**（作为**身份**；归档前产出的 manifest 另走 D8 的别名）。
  依据：**`contract.py:250` 的交叉校验比的是 label 末段**（= change 目录的名字），而 `check` 与
  `manifest build` **必须共用同一个校验器**（本仓反复禁止「两边各写一套」）。
  ⚠️ **不是**「源 id 口径不可落」——那条路加一条「歧义即报错」的守卫是可实现的（对抗轮纠正了初版的理由句）；
  否掉它的真正理由是「会给归档态单开一套校验器 / 让 id 与 label 拆成两个参数」= 本仓要避免的漂移面与例外。
- **CQ2（原 Q3）触碰已归档的 change 文件（`M` / `D`）不算「该 change 出现在本次 diff」。**
  依据：`is_archive_move` 对 `M`/`D` **恒 False**（本仓实测：`M archive/<name>/**` ⇒ False，
  `D` ⇒ False）⇒ 机械上本来也不会「算」；若改成「算」，任何一次触碰都能把该 change 拉进集合
  （比「什么都不建」更省事，且可重复），并与本 change 自己写的「唯一取得方式是归档 move」直接矛盾。
  ⇒ **不是取舍**，是「要不要写进否定面清单」——已写（N4 / N6）。
- **CQ3（原 Q4）归档事件的授权面本 change **不收窄**——那是**改语义**，不是「做不到」。**
  依据：`events.Event`（`events.py:28-46`）只有 4 个字段，`load_events_file`（`:69-76`）只取那 4 个键，
  `covers`（`:88-103`）只比 `artifact_path`（`events.py` 全文 `change_id` 出现 **0** 次）。
  ⚠️ **「今天收窄不了」偏强**（对抗轮纠正）：把「事件只在**本次 diff 的 change 集合**内的 change 目录里才提供豁免」
  是**不需要新字段**的（`load_all` 的读点与该集合求交即可）——但那会**推翻 `docs/gate.md §7` 的既有边界**
  （事件是全局解释、`change_id` 是 informational），是**语义变更**，不是本 change 的目标。
  ⇒ 定案：**不改语义**，只把「池子变大」写进 `docs/gate.md §4`（§6 的 G2）。

## 3. 接线点（实现清单）

- `src/witnessloop/contract.py`
  - `changed_change_ids` 增加归档维（或新增 `archived_change_ids` 与它并列，由 `change_targets` 合并）。
    **保持**两条既有性质：`archive` 本身**永不**作为 id；搬迁走的 active 源**不再**按 active 校验。
  - **新增授予判据**（D2 第 2 条）：`<name> == <源id>` 或 `<name>.endswith("-" + <源id>)`；
    不满足 ⇒ **不授予**（该 move 的两个端点仍按既有规则排除 ⇒ 集合为空 ⇒ 回落到今天的行为，fail-closed）。
    这条**只影响「授予」**，不进 `is_archive_move`（后者的既有 6 条语义**一条都不能变**）。
  - 新增 `archived_change_dir(root, pol, name)`；新增 `change_targets(...)` → **列表**、
    **以目录为键**（D7 的 tie-break：同 id 两份都校验，**不许** `dict[id]=dir`）。
  - `validate_change_dir` / `validate_review_manifests` 收 `directory` + `label` +
    **`accepted_change_ids`**（D8：归档态 = `{归档目录名, 源 id}`；active = `{id}`）。
    ⚠️ `contract.py:250` 的比对改成「`doc["change_id"]` ∈ 接受集合」，**只有这一处、只有这一个参数**
    ——不是第二套校验器（D8）。
  - `is_archive_move` **不动**。
- `src/witnessloop/checkcmd.py`：`run()` 的循环换成 `change_targets`（三处 `change_dir(...)` 调用点：`:86`/`:98`/`:105`）；
  `_require_change` 文案（`:188-208`）；`_report` 打印归档 change（标注，见 R6）。
- `src/witnessloop/manifestcmd.py`：`--change` 解析（active → archive → 报错 + 提示）；
  `manifest_rel` 由**解析后的目录**推（`:149` 是硬编码点）；`validate_change_dir` 传解析后的目录。
- `src/witnessloop/events.py`：`load_all` 两条显式 glob（D6）。
- `src/witnessloop/policy.py`：**不改**（`archive_root` 已经在 `:73-74`）。
- `src/witnessloop/guardcmd.py`：**不改**（见 §3.5）。
- `tests/`：§5 的用例。
- 文档：§6。

## 3.5 非目标

- **asterwynd 式的归档点完成度门禁**（`_check_archived_completion_gate`）：本仓无 `ChangeType`/`primary`，照搬不了（§1.4）。
- **收紧归档命名为 `archive/<id>`**（对抗轮点名的第三路）：**本 change 不选**——理由与实测见 D1 的备选段；
  它作为政策题进 §8 的 **Q2**（**不影响本 change 的实现**：D8 让两种命名都能用）。
- **日期前缀解析**：`is_archive_move` 只认「落点在 `archive/**`」，本 change **不缩小也不扩大**它（D2 第 1 条）。
  ⚠️ 但**授予判据**（D2 第 2 条）确实引入一条**命名约定**：目标目录名必须等值或以 `-<源id>` 结尾。
  它**不解析日期**（`endswith` 而已），代价是「归档时改名成别的花样」的仓**拿不到**这个能力
  （回落到今天的行为，fail-closed；不是新退化）。这条约定**必须写进 `docs/gate.md`**，别只活在代码里。
- **change ↔ 代码路径的归属**：不引入（§2.5）。
- **`guard`（本地守卫）的归档支持**：`guardcmd.resolve_change_id` 要求 id 命中**现存 active 目录**；
  分支名是 `<id>/…` 而 change 已归档 ⇒ 今天就是「推不出 ⇒ 放行」（fail-open）。
  本 change **不**给它加归档分支：守卫是「防遗忘」层且用 Bash 写文件即可绕过（`README` 已写明），
  加一条只会多一个可绕过的面。**登记为已知缺口**。
- **events 去重 / 索引**：判定是存在性的，不需要；性能见 R8。
- 签名 / 防伪造；`check` 退出码语义。

## 4. 风险

1. **R1（高·防绕过）**：若实现成「归档 move 只让 `_require_change` 闭嘴」⇒ C3 那份 PR 从「1 项红」
   变「**0 项红**」（零 change 证据放行）。**缓解**：D2；机械钉子 = §5.3 的 N2/N4/N6 + 「归档 + 改码 + 零 manifest
   ⇒ 必须点出那 4 条缺件」的先红用例。
2. **R2（高·新增红类）**：归档 change 现在**真的**会被校验 ⇒ 历史 change（证据不齐、
   或在某些门禁引入**之前**造的）在**被归档的那一刻**可能新增红（**边界与停轮项**：见 §8 Q1）。
   ⚠️ **本 change 不做「重建」那条补救**（初版与 grill 稿都写错了顺序，对抗轮实测证伪）：
   正确做法是**别名 D8**（归档前的 manifest 不必重建）+ **§1.6 的顺序**（move 放最后、别动被 move 的文件）；
   要在归档**之后**改写证据 ⇒ 那是**不含 move 的后继 diff**（`M` ⇒ 每条一条事件，实测 3 条 ⇒ 绿）。
   不接受这条新红类的话：把纯归档 PR 与实现 PR **拆开**（注意：拆开后纯归档 PR 仍会吃 manifest 与 grill 正文那两条）。
3. **R3（中·前提）**：整套设计依赖 **R100 纯改名**。若接入方的归档器**边搬边改**（打勾 `tasks`、应用 spec delta）
   ⇒ `is_archive_move` 为假 ⇒ **回到今天的行为**（不是新退化，但归档感知对它不生效）。
   ⚠️ **反推证据**：接入方观测到的症状 ①（集合为空）**本身**证明它的归档是 R100——
   若归档是 `D+A`，`D` 侧路径会命中 active id、集合**非空**，报的会是「change 目录不存在」而非「没有任何 change 目录」。
   ⇒ 写进 `tasks`：实现期用真仓实测一次该接入方归档命令的 `--name-status` 输出（**R100** 才算通过）。
4. **R4（中·id 口径外溢）**：归档态 manifest 的 `change_id` 是**归档目录名**（`2026-10-14-x`）。
   若接入方另有工具按「源 id」读 manifest（例如自己去 grep `change_id`），会看到不一致。
   缓解：D4 的报错文案 + §6 文档 + §1.5 的连锁写明（**已定案 CQ1**，不交停轮）。
5. **R5（中·自伤）**：本 change 的实现 PR 若**顺带归档别的 change**，那个 change 会被按**今天的**规则校验 ⇒ 可能红（R2 的具体形态）。
   行动：实现 PR **不要顺带归档**；本仓 4 个已完成 change 的归档**另开 PR**。
6. **R6（低·诊断面）**：`_report` 的 `N 个 change 目录` 现在把归档的也算进去（数字含义变了）。
   **实现期定案**（building-review 的 I8）：计数按 **target（目录）数**算——同一个单段 id 撞两个目录时
   报 **2**（此前若按去重 id 会报 1，把两个目录说成一个）。⚠️ 子串 `0 个 change 目录` **原样保留**
   （`tests/test_check_contract.py` 依赖它 ⇒ **没动那条测试**）；`labels` 那一行仍逐条列出、可定位。
7. **R7（低·授权面）**：事件池变大（D6 / CQ3）。
8. **R8（低·性能）**：多一次目录 glob；接入方 `archive/` 下文件数大（80+ 份事件文件）。
   `load_all` 本来就全量读入内存 ⇒ 线性增长，可接受。**若将来成问题再谈索引**，本 change 不做。
9. **R9（中·测试盲点）**：本仓既有的归档测试用的目录名**与源 id 同名**（`archive/add-retry`）
   ⇒ `contract.py:250` 的末段比对恰好成立，**永远抓不到** §1.5 第 1 条（别名那一类）；
   而「先归档、再 build」的顺序也绕开它。
   **缓解（必须做）**：§5.1 补「**先用源 id build、再归档到 `<date>-<id>`**」（别名钉子）、
   「**同一 diff 里 move + 改写被 move 的文件**」的后果用例（R12）与「归档后在**后继 diff** 上重建 = 3 条事件」。
10. **R10（低·第 6 面残留）**：D2 第 2 条之后仍有「名字恰好认得源 id 的部分 move」可授予资格（§2.5 残留边界 2）。
    **校准**：与既有边界（碰 active change + 重建 manifest ⇒ 绿）同类等价，**不阻塞**；写进 spec 的 Requirement 说明与否定面清单。
11. **R11（低·`archive/` 不是真 change 目录也会被读）**：`events` 两条 glob 的 `*` 会匹配**任意**目录名
    （`archive/notes/…` 会被当成一个归档 change 目录的事件文件）。这是**既有口径**（active 一层同款），
    本 change 不收紧；但 `docs/gate.md §4` 必须写准（§6 的 G2），别写成「只扫真 change 目录」。
12. **R12（高·`R<100` 的同一 diff 改写）**：在**同一个 diff** 里既 move 又改写被 move 的文件（最典型的误用：
    「归档之后在归档态重建 manifest」）⇒ ① **不授予**（`is_archive_move` 要求 `R100`）② 被搬走的 active 目录
    **以幽灵 id 回到集合**（5 项红，**补事件也消不掉**）③ 事件需求**翻倍**（rename 两半各记一次：3 份 = 6 条）。
    实测 9 → 6 → 3 项（§1.5 第 2 条）。**缓解**：`docs/gate.md` 明确「归档 move 必须是纯改名」+ 把 §1.6 的顺序
    写成接入指引 + §5.1 的 R12 用例钉住后果。
13. **R13（中·id 撞车）**：单段 id 可同时来自 active 目录与归档授予（**实测可构造**，E3''）⇒ D7 定死
    「以目录为键的**列表**、两份都校验、不许 `dict[id]=dir`」。**缓解**：§5.1 的撞车用例。

## 5. 测试策略（TDD）

### 5.1 用例（**实现前红、实现后绿**的那些；每条可判定）

> ⚠️ **实现后订正**（building-review 的 I5）：本节的「别名钉子」与「`R<100` 的后果」两条，
> 实测**实现前就是绿的**（那时归档 change 压根不进集合 ⇒ 空转绿；后者靠既有路径也报同样的红）
> ⇒ 它们是**回归护栏**（价值在变异验证），不是「先红」。见 `tasks.md` 的同名订正与实测记录。

- **契约层**：归档 move + 代码改动的 diff ⇒ `change_targets` 非空，且归档项的 id = **归档目录名**、label = 归档相对路径。
- **`check` 症状 ①**：归档 + 改 `src/` ⇒ 不再报「没有任何 change 目录」（今天 1 项红），
  **且**归档 change 按归档路径被校验。⚠️ **要绿必须写全前置**（否则那条断言为假——实测）：
  证据必须①绑在**本 PR 的最终内容 revision**、②在**归档路径**上被解析到（= D8 别名或归档后产出）。
  - **能绿的形态（实测 `EXIT=0`，0 项红）**：base 里 change 已是 active（提案态）⇒ 本 PR
    「① 改代码 → ② **在 active 态** build 证据（绑 ①）→ ③ 归档 move 放最后（纯 R100）」。
  - **红的形态（实测 3 项）**：base 里已有证据且**本 PR 又改了 `src/`** ⇒ 3 条
    「审阅的是旧 revision：… 之后又改动了非证据文件：src/app.py」（既有的「先内容、后证据」，`docs/gate.md §3.1`）。
    这条**不是**归档带来的新红类，别把它当验收断言。
- **`check` 防绕过（R1 的钉子）**：归档 + 改 `src/`、且归档 change **零 manifest** ⇒ 红，且 stderr **同时点出**
  「缺少 review manifest」「无 `stage=grill`」「无 `stage=grill-adversarial`」「无 `stage=building`」
  （今天只有 `_require_change` 那 1 项）。
- **`check` 症状 ③**：归档 change 的 `workflow-events.jsonl` 点名一份受保护写入（同 PR 写 `openspec/specs/**`）⇒ 不再报「没有解释事件」（今天红）。
- **`manifest build` 症状 ②**：`--change <归档目录名> --report reviews/building-review.md` ⇒ `EXIT=0`，
  manifest 落在 `openspec/changes/archive/<name>/reviews/<stage>.manifest.json`；随后 `check` 认它（**往返**用例）。
- **⚠️ 别名钉子（D8，R9）**：证据齐备的 change `gwa`，用 `--change gwa` build（`change_id="gwa"`）⇒ 提交 ⇒
  `git mv` 到 `archive/2026-10-14-gwa/`（**纯 R100、不再重建**）⇒ `check` **绿**
  （实测 `EXIT=0`、0 项红）；⚠️ **不加 D8 别名**时同一 diff 每份 manifest 报 1 条「与目录不符」——
  这条用例就是那把钉子，且**本仓既有测试抓不到它**（它们的归档名与源 id 同名）。
- **⚠️ `R<100` 的后果（R12，今天红、修后**仍应红**）**：同一 diff 里 ① 归档 → ② 在归档态重建三份 manifest
  ⇒ 实测（修后模拟）`EXIT=1`：**9 项**（3 项幽灵 active id + 6 项受保护写入）；补 3 条事件 ⇒ 6 项；
  再补旧路径侧 3 条 ⇒ **仍有 3 项**（幽灵 id **补事件消不掉**）。⇒ 用例断言：
  「同一 diff 内 move + 改写被 move 的 manifest ⇒ 红，且 stderr 含『`openspec/changes/<源id>：change 目录不存在`』」。
- **⚠️ 归档**之后**改写证据 = 3 条事件（§1.5 第 3 条）**：归档已在 base（本 diff **不含**该 move），
  再重建三份 manifest ⇒ `check` **恰好 3 条**「受保护路径被写入，但没有结构化解释事件」；补三条
  `protected_path_write` 事件 ⇒ **绿**（实测 ④⑤）。⚠️ 必须**换 revision**：同一 revision 重复 build
  是逐字节幂等的，造不出 `M`。
- **⚠️ id 撞车（D7 的 tie-break）**：构造「同 PR 内同名 move + 新增 active 子文件」的 diff
  （实测 `changed_change_ids` 今天 = `['x']`、授予也指向 `x`）⇒ `change_targets` 返回**两条**、
  **两份都校验**（实测 8 项红：两侧各自「缺少 review manifest + 三条 stage 门」）；断言**不出现**
  「只校验其中一份」或「静默丢掉一份」。

### 5.2 回归面（**必须保持绿**，逐条点名）

- `tests/test_archive.py`：`test_archiving_a_change_passes_without_events`（纯归档 + 合规证据 ⇒ 仍绿）、
  `test_archived_change_is_no_longer_validated_as_active`（不为搬走的 active 源报「目录不存在 / 缺少必需件」）、
  `test_deleting_an_evidence_file_still_needs_an_event`、`test_modifying_a_file_inside_archive_still_needs_an_event`、
  `test_renaming_within_the_active_change_still_needs_events`、`test_archiving_a_protected_spec_still_needs_an_event`。
- `tests/test_require_change.py`：全部 8 条（尤其 N1 `test_source_change_without_change_dir_is_rejected`
  与 `test_deleting_source_without_change_dir_is_rejected`）。
- `tests/test_check_contract.py`：`test_touched_but_absent_change_dir_is_reported`（N3）、
  `test_complete_change_passes`、`test_change_outside_changes_root_is_ignored`（**注意 R6 的文案子串**）。
- `tests/test_manifest_build.py`：`test_unknown_change_is_rejected`（归档 fallback 不得吞掉「找不到」）、
  `test_nested_change_id_is_rejected`、`test_dotdot_change_id_is_still_caught_by_the_containment_guard`、
  `test_absolute_change_id_is_rejected`、`test_report_path_escaping_the_change_dir_is_rejected`、
  `test_report_outside_reviews_is_rejected`、`test_rebuild_without_explicit_ids_is_byte_identical`。
- `tests/test_events.py`（`covers` 全部语义）、`tests/test_events_readpoint.py`（读点归一）、
  `tests/test_check_protected.py`（受保护写入两档规则）。
- **全量**：`uv run pytest -q` —— 本 change 前的**实测基线 = 496 passed**。

### 5.3 否定用例（**必须照样红 / 不生效**）

- **N1** 只改 `src/`、不建任何 change 目录 ⇒ 红（今天红、修后必须还红）。
- **N2** 伪造归档：新建 `openspec/changes/archive/2026-10-14-fake/{proposal,design,tasks,specs}/…`（无 active 源）+ 改 `src/` ⇒ **不生效**（实测今天红：`_require_change` 命中；修后仍必须红）。
- **N3** 删除 change 目录（非 rename）⇒ 仍报「change 目录不存在」。
- **N4** 只改 `archive/<name>/` 里已存在的文件（`M`）+ 改 `src/` ⇒ 该 change **不进**集合 ⇒ 红（今天红、修后必须还红）。
- **N5（⚠️ 立项稿初版写反了，grill 实测纠正）**：真正**不被读**的是「**再深一层**」的
  `<changes_root>/archive/<name>/<sub>/workflow-events.jsonl`（两条 glob 各只覆盖一个层级）。
  **不**能拿 `changes/archive/workflow-events.jsonl`（`archive/` 直接下）或 `changes/archive/notes/workflow-events.jsonl`
  当否定面——**实测两者都会被读**（前者的 `*` 匹配 `archive`，后者把 `notes` 当成一个归档 change 目录），见 D6 与 R11。
- **N6（第 6 面，grill 挖出）**：把 active change `z` 的**单个文件** R100 改入**已存在**的归档目录 `y`
  （`git mv changes/z/notes.md → changes/archive/y/notes.md`）+ 改 `src/` ⇒ **不授予任何资格**、
  `_require_change` 照样红。⚠️ 实测：今天 `is_archive_move=True`、`changed_change_ids=[]`；
  **不加 D2 第 2 条**的话，这个 diff 会「凭空」让 `y` 进集合而 `z` 静默逃检 ⇒ 这条用例就是那条判据的钉子。
- **N7（R12）**：同一 diff 内「move + 改写被 move 的文件」⇒ 红（含幽灵 active id），**不许**因为
  「反正它是一次归档」而被放过。见 §5.1 的 R12 用例（同一条，两处都点名）。

## 6. 文档影响

- **`docs/gate.md §5.1`**：改写「配套：归档 move 的两端都不计入 active change id…」那段——现在有**归档维**；
  补「归档 change 按**归档路径**走同一套契约/证据门禁」；边界表照 §2.5 更新；
  **并把 D2 第 2 条的命名约定写进文档**（目标目录名必须 `<源id>` 或以 `-<源id>` 结尾；否则不授予资格）
  ——别让它只活在代码里；两条残留边界（§2.5）也各记一句。
- **`docs/gate.md §4`**：⚠️ **必须改写** `:245-246` 那句「覆盖范围是 active change 目录：`archive/**` 下的 events 文件**既不会被读、也不提供豁免**（既有行为）」——本 change 之后**为假**。
  补「事件池 = active 一层 + archive 一层；同一 change 两份都读、任一条命中即豁免」，
  **并照 D6 写准两条既有口径**（`archive/` 直接下的同名文件今天就会被读；`archive/<任意名>/` 会被当成归档 change 目录）
  ——**别写成「只扫真 change 目录」**（R11）。
- **`docs/gate.md §3.2`**：`manifest build` 的 change 解析（active → archive）、
  **§1.6 的顺序与 D8 的别名**（「归档前的 manifest 不必重建；要改写已归档的 manifest ⇒ 每条一条事件；
  同一 diff 里 move + 改写被 move 的文件 = 红」），以及「不合格就不写出」清单补两条
  （两处都找不到；归档目录名提示而不自动认）；另加一句：`archive` 本身是目录 ⇒ `--change archive` 走 active 分支
  并报「缺少必需件 proposal.md」（grill R5 的困惑点）。
  ⚠️ **`tests/test_docs.py` 的「幂等」守卫是**按文件整体**扫的**（`IDEMPOTENCY_DOCS`：`docs/gate.md` 里**每个**
  「幂等」要么同句含 `init`、要么 ±2 行内带「固定 base 与 revision」）。
  ⚠️ **对抗轮纠正了本稿初版的说法**：`docs/gate.md` 的「幂等」实测只在 `:9` / `:52` / `:497`，
  **§3.2（`:199-222`）内 0 处** ⇒ 今天改 §3.2 **不会**撞它；真正的风险是**新写**一个「幂等」时必须带限定词
  （见 tasks 的 G7——它已扩成「改**任一节**文档前先读 `tests/test_docs.py`」）。
- **`docs/gate.md §6`**：`check` 退出码 `1` 的括号清单里补「**归档 change 证据缺件**」（语义不变，只是列举）。
- **`docs/gate.md §10`**：那句「本仓**无 archive 门禁**」**加一句限定**——它指「不在归档点跑完成度门禁」，
  与「归档感知」不是一回事（否则读者会把本 change 读成自相矛盾）。
- **`README.md`**：归档段（`:135-137`）补「归档 change 仍按同一套证据门禁校验（在归档路径上）」；
  「行为变更」段补一条对**接入方**的变更（归档 PR 现在要求该 change 证据齐备；归档后 `manifest build` 的用法）。
- **本 change 自己的 spec delta**：`specs/archive-awareness/spec.md`。

## 7. Pre-Implementation Review

**grill 与对抗轮都已回写**（`reviews/grill-design.md` = run `grill-reviewer-archive-awareness-ae992565ee21`；
`reviews/grill-adversarial.md` = run `grill-adversarial-reviewer-archive-awareness-4bd6ad0e2143`，R1 判
**CHANGES_REQUESTED**、**不推翻方案方向**）。**用户已于 2026-10-15 停轮裁定**（§8：Q1 = uniform、Q2 = 不收紧）。

### 7.1 对抗轮（R1）确认的（它自己重跑过；本稿据此**不推翻**）

- 绕过口 **N1–N6 今天全红、按 D2+D6 模拟修后仍全红**；它另造 6 种攻击（A4/A5/A5b/A6/A8…）修后全部 fail-closed。
- 穷举 `src/witnessloop/` 的 6 处 archive 落点 ⇒ **无新的授予/豁免路径**（`constants.py:37-38`、`policy.py:73-74`/`:91`、
  `contract.py:38-55`/`:58-86`、`checkcmd.py:235-239`、`guardcmd.py:64`）。
- **`change_id` 用归档目录名是对的**（被 `contract.py:250` 的末段比对逼定；「身份 = 目录名」是本工具一贯口径；
  老归档只在含该 move 的那个 PR 里校验一次，实测：不含它的 PR ⇒ 该 change 不进集合、0 项红）。
- 三处事实订正**全部真修好**（C1b 两个变体可重跑、删掉「唯一闭合方式」、N5 改成「再深一层」）；
  `is_archive_move` 10 组语义无漂移；§1.2 的四项对照逐格复现。

### 7.2 对抗轮证伪并已整合（本稿的改动）

- **阻塞①（M1）——本稿的「补救链」在同一个 PR 里跑不通**：实测「归档 + 用归档目录名重建」会把
  `R100` 降级成 `R075/R077` ⇒ 不授予 + **幽灵 active id** + 事件翻倍（本仓复现 9 → 6 → 3 项，
  最后 3 项**补事件消不掉**）。**已改**：① 新增 **D8 别名**（归档前的 manifest 不必重建）——
  实测「只归档不重建」修后 **0 项红**；② 新增 **§1.6 的正确顺序**（move 放最后）——实测修后 **0 项红**；
  ③ 新增 **R12** 与用例：明确禁止「同一 diff 里 move + 改写被 move 的文件」，并写明它的三条后果。
  ⚠️ **与对抗报告的一处不同**：它推荐的 (a)「把归档 move 与重建拆到两个 check 区间」**本身不足以变绿**——
  归档那一个 PR 仍会因 `change_id` 不符而红（它 §2.2 的实测正是 6 项红里含 3 项 `change_id`）。
  真正让它可绿的是 **D8**（别名）。⇒ 本稿同时采纳 D8（使它 (a) 的拆分成为可选的**替代**而非必需）。
- **阻塞②（M2）——验收断言按字面 fixture 不可达**：实测「base 证据齐备 + 本 PR 归档 + 改 `src/`」
  = **3 项红**（全是既有的「审阅的是旧 revision」，与归档无关）。**已改**：§5.1/`tasks` B3/`spec` 的 Scenario
  改成「给出**能绿**的形态（§1.6）+ 明说红的形态与原因」，不再写「归档 + 改码 ⇒ 自动绿」。
- **阻塞③（M3）——D7 的 tie-break 未定义**：本仓**构造出**同一 id 撞两个目录的 diff（E3''：`changed_change_ids`
  今天 = `['x']`、授予也指向 `x`）。**已改**：D7 定死「**列表、以目录为键、两份都校验**」，禁止 `dict[id]=dir`。
- **M4/M5/M6（理由句与引用）**：D1 / CQ1 / CQ3 的过强理由已按实测改写；
  `design.md` 里指向 tasks 的 **G6 → G7**；「§3.2 是幂等密集处」已订正（实测 §3.2 内 **0** 处「幂等」）。
- **M7（Q1 例子）**：见 §8——⚠️ 按 **D8** 重新算过：纯归档 PR 的新红类是 **1 项**（grill 正文），
  **不是**对抗报告测的 4 项（那 3 项 `change_id` 不符已由别名吸收）。

**grill 确认（它自己重跑过）**：

- 三条症状在本仓当前树**全部复现**，本文点名的 `文件:行号` **无漂移**；基线 `uv run pytest -q` = 496 passed。
- **核心立论成立**：把 D2 派生出的 id 直接喂给**现有**校验器，C3 那个仓得**恰好 4 条** finding（全在归档路径上）
  ⇒ 「只让 `_require_change` 闭嘴会开绕过口」成立，`_require_change` **不能**改成豁免。
- `is_archive_move` 是**可用**的防伪锚（10 组构造全部符合预期）；「放回集合 + 按归档路径校验」在现有代码结构下**真能落**（往返闭合）。
- N1/N2/N2b/N3/N4 五条否定用例**今天全部红** ✓。

**grill 证伪并已整合（本稿的改动）**：

- **M2（最高优先）**：归档目录名 ≠ 源 id 的连锁（`change_id` 立刻不符；重建 = `M` 不变集路径要事件）
  ⚠️ **grill 当时给的补救（「先归档 → 用归档目录名重建 → 每条一条事件」）已被对抗轮证伪并替换**
  ——同一 diff 里重建会毁掉 `R100`（§1.5 第 2 条）⇒ 现行答案是 **D8 别名 + §1.6 的顺序**（见 §7.2）。
- **M1（第 6 面）**：单个文件 R100 改入**已存在**的归档目录 ⇒ 凭空授予 + 源 change 静默逃检。
  已加 **D2 第 2 条**（目标目录名须认得源 id）挡掉它，并把残留写进 §2.5 残留边界 2（不假装它不存在）。
- **M5**：C1b 的「5 个变更文件 / 4 项红」只在「工作树里有个未跟踪的空 `reviews/` 目录」时成立 ⇒
  §1.2 改成两个**都可重跑**的变体（6/4 与 5/5）。
- **M4**：「uniform 是绕过口的**唯一**闭合方式」**为假**——`code-gated` 同样闭合（C3 的 `code_hits` 非空）⇒ 已改。
- **M3**：N5 与那条 spec Scenario 的否定断言**方向反了**（`archive/` 一级下的同名 events 文件**会被读**）⇒
  §5.3 N5 改成「再深一层」，D6 补两条既有口径，R11 登记。
- **R3（grill）**：既有测试的归档名**与源 id 同名** ⇒ 抓不到 M2 的连锁 ⇒ §5.1 补两条用例（R9）。

**Code-Resolved（grill 判定可由代码定案）**：原 Q2/Q3/Q4 ⇒ 见 §2.6，**不进停轮队列**。

**停轮**：**2026-10-15 用户已逐条裁定**（Q1 + Q2，§8）——**无待定项**。

## 8. 停轮裁定（Q1..Q2 —— 用户 **2026-10-15 已逐条确认**；答复原文见 `reviews/grill-design.md` 的 `## User Confirmation`）

> 名称与格式沿用本仓先例（`grill-adversarial-gate` / `adopter-test-gate` 的 `## 停轮裁定`）。
> 原 Q2/Q3/Q4（**编号**）已由 grill 判定为可由代码定案，移入 §2.6（CQ1/CQ2/CQ3），**不进停轮**——
> 注意本节的 **Q2 是另一条**（对抗轮之后新开的政策题，与 §2.6 的 CQ2 不是一回事）。
> ⚠️ **本仓 checker 的实际口径**（`evidence.grill_evidence_findings`，我逐行读过并直调验证）：
> 它解析的是 **grill 报告**（`reviews/grill-design.md`，由 `stage=grill` 的 manifest 以 `report_path` 绑定），
> **不是** `design.md`；且它按**逐字标题**取小节（`OPEN_QUESTIONS_TITLE = "Open Questions"`）。
> 要求：`## Confirmed Decisions` ≥3 条且每条带 `来源:`、`## User Confirmation` 小节存在、
> 且 `## Open Questions` 里的**每个 `Q<n>`** 都要在该小节里有 `- **Qn**: 用户答复：…；确认时间: <date>`。
> ⇒ 本期已在报告里**追加**了标题逐字的 `## Open Questions`（Q1+Q2）与 `## User Confirmation`（两条实质答复），
> **审阅者原正文一字未改**（`git diff` 只有新增行）。直调结果：`grill_evidence_findings ⇒ 0 条`；
> 反证（拿掉 Q2 的确认）⇒ 报 `Open Question Q2 未经用户确认` ⇒ **规则确实在跑，不是空真**。

- **Q1〔归档 change 的校验深度〕＝ 裁定 `uniform`（生效口径）**：归档 change 进集合后，
  走与 active **同一套**规则（不引入「归档专用」的第二套判据）；
  **接受**「纯归档 PR 也会红」这条新红类。
  **可判定的例子**（对抗轮选定的分叉场景，本仓实测）：PR **只做归档**——
  `git mv openspec/changes/legacy-x openspec/changes/archive/2026-10-15-legacy-x`，**一行代码都不改**，
  而 `legacy-x/reviews/grill-review.md` 是早期写的、`## Confirmed Decisions` 只有 2 条
  （它的三份 manifest 是归档前用源 id 产的）。
  - **今天**：`check` **绿**（集合为空，这份 change 压根不被校验）——同款实测见 §1.2 的 C2（`EXIT=0`）。
  - **本 change（uniform）**：**红 1 项**——`openspec/changes/archive/2026-10-15-legacy-x/reviews/grill-review.md：
    `## Confirmed Decisions` 只有 2 条，少于硬门槛 3 条`（本仓实测：`alias=True` ⇒ 1 项；`alias=False` ⇒ 4 项，
    多出的 3 项是 `change_id` 与目录不符——**已由 D8 别名吸收**）。
  - **补救两跳（写进 `docs/gate.md` / `README` 的接入指引）**：
    ① 证据不合规的**历史 change** 要在**归档之前的 diff** 里修（补齐报告 + 重建那份 manifest + 各写一条
    `protected_path_write` 事件）——同一 diff 里改被 move 的文件 ⇒ `R<100` ⇒ 幽灵 active id（§1.5 第 2 条，
    **这个限制今天就已存在**，对抗轮 A8 实测今天 5 项红）；
    ② 归档 move 本身必须**纯改名、放最后**（§1.6 的三步顺序）。
  - **否决的备选（各一句）**：`code-gated`（只在落了代码时全量校验）——也能闭合 §1.2 的绕过口，
    但会给同一件事留两种判据；`contract-only`（归档只查必需件）——**留绕过口**（归档 + 改代码 ⇒ 0 项红 = 放行）；
    「纯归档 PR 与实现 PR 拆开」——不是备选而是**用户可选的缓解**（拆开后纯归档 PR 仍吃 manifest 与 grill 正文两条）。
- **Q2〔归档目录命名要不要收紧成 `archive/<id>`〕＝ 裁定 `不收紧`（生效口径）**：
  保持 `archive/<date>-<id>`；**D8 的别名继续保留**（归档态 target 的 `change_id` 同时接受「归档目录名」与「源 id」，
  两种命名都能用）；**不要求**接入方给 80 份既有目录改名。
  - **否决 `archive/<id>` 的理由（实测）**：收紧授予判据（「必须等值」）会让接入方现有 **80 份**
    `<date>-<id>` 归档目录 + **OpenSpec `openspec archive` 自身**的日期约定**一概拿不到授予**
    ⇒ **症状 ① 原样回来**；而改名迁移本身约要 **240 条**解释事件（80 个目录 × 3 份 manifest 的「旧路径删除」）。
    它的收益（`change_id` 那一类红整类消失，对抗轮同一 fixture 6 → 3 项）**已被 D8 别名覆盖**。
  - **后续（不阻塞本 change）**：「归档命名要不要统一」**另立 change/issue**——本 change 不自己开 issue，
    只在 `tasks.md` 的「明确不做」里登记，并在 `docs/gate.md §5.1` 写明「授予判据接受 `-<源id>` 后缀」这条约定。
