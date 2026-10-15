# Design: archive-arrival-recognition

## 0. 一句话

把「本次 diff 里到达了一个归档 change」的判定，从**逐文件改名分（`R100`）**换成
**目录级事实（`archive/<name>/` 在 base 里不存在、在 head 里存在且是 change 目录）**；
到达方式（`git mv` 过来 / 直接新建在 `archive/` 下）不设限，而**到达方式不改变证据门槛**。

## 1. 现状（实测）

### 1.1 代理指标错在哪（逐行核对）

- `contract.is_archive_move`（`src/witnessloop/contract.py:65`）：`if change.status != "R100" or not change.old_path: return False`。
  **逐文件**、且**要求恰好 100%**。
- `contract.changed_change_ids`（`:85`）用它算 `archived_sources`（`:97`）⇒ 只有 `R100` 记录的 `old_path` 才被排除。
- `contract.archive_grant`（`:119`）以它为前提 ⇒ 只有 `R100` 才授予 target。
- `checkcmd._protected_writes`（`src/witnessloop/checkcmd.py:228`，`is_archive_move` 分支在 `:255`）以它为准 ⇒ 只有 `R100` 才免解释事件。
- `gitutil.changed_files`（`src/witnessloop/gitutil.py:99`，`--find-renames` 在 `:105`）用的是 **`base...head`（三点 / merge-base）**，
  且是**两树**比较 ⇒ 「相似度」是**整个 diff range** 的产物，**无法**区分「move 那一刻顺带改了」与「更早的提交里改过」。
  ⚠️ 三点这件事是 **D1 的基准修订必须对齐**的理由（见 D1 第 1 条）。

### 1.2 复现命令（与 `gate.yml` 逐字一致）

```
uvx --from "git+https://github.com/Xingkai98/witnessloop@<ref>" \
    witnessloop check --root . --base <PR 的 base branch tip> --head <PR head>
```

`<ref>` = `v1`（对照）/ `5535d9e`（含 PR #22）。三份 diff 的实测结果见 `proposal.md` 的表。

### 1.3 三种真实形态的 diff 状态（可复算：`git diff -M --name-status <base> <head>`）

| 形态 | 记录状态构成 | 今天的结果 |
|---|---|---|
| 接入方**真实实现 PR**（33 文件） | **全 `A`**（base 里无此 change） | ✗ 1 项：`require_change_for` 报「没有任何 change 目录」 |
| **纯归档 move**（14 文件） | **全 `R100`** | ✓ 通过，`1 个 change 目录` |
| 接入方**收尾 4 连提交**（16 文件） | **4×`R<100`**（`R068/R069/R070/R090`）+ 11×`R100` | ✗ 11 项：幽灵 active id（3）+ 受保护写入（8） |

`R<100` 的那 4 个文件是 `reviews/{building,grill-adversarial,grill}.manifest.json` 与 `workflow-events.jsonl`——
**恰好是 adopter 收尾次序的必然产物**（先在最终内容 head 上重建 manifest、再做 move；`change_archived` 事件还要在 move 之后追加）。

### 1.4 参考实现研究（本仓的形态）

业界对「移动即改名」的处理（`git log --follow`、`git diff -M`、IDE 重构）都承认**相似度是启发式**，
因此成熟做法**不把相似度当作授权依据**，而是：① 用**显式的身份事实**（路径前缀 / 目录存在性 / 内容哈希）
判定归属；② 把「内容是否变了」交给**独立的完整性校验**（哈希绑定）去抓。
本 change 沿用这条：归属看**目录存在性**，内容看**既有的 manifest 哈希绑定**，
**外加**一条目录级的内容来源判据（D1 第 5 条，对抗轮 R1 的 F1 逼出来的）。

### 1.5 ⚠️ 上一版哪一条真的承重（初稿读错，此处订正）

初稿把 `archive-awareness` 的两条否定面读成「承重的安全守卫」。复核后**只成立一条**：

- **不承重**：「放宽 N2（出生即归档）会新开一块审阅后可改的暗房」。**假**——
  `policy.stale_exempt_paths`（`src/witnessloop/policy.py:77`）把 `archive/**` **整块**列为允许出现，
  暗房**今天就已经存在**（任何已归档 change 的 `proposal/design/tasks` 审阅后被改都不判 stale）。
- **承重**：「不得给 `base` 里**已存在**的归档目录凭空授予资格」，其**具体威胁**是
  **白捡一份现成证据**：`git mv changes/z/notes.md → changes/archive/y/notes.md` 会把资格给 `y`，
  而源 change `z` 因 `archived_sources` 被排除、**静默逃检**。

⇒ 本 change **反转前一条、完整保留后一条**，且把后一条**升级**成两条独立判据：
D3（目录在基准树里已存在 ⇒ 不授予）+ **D1 第 5 条**（内容整份来自仍在的既有 change 目录 ⇒ 不授予）。
第二条是 R1 对抗轮用**端到端实测**逼出来的：只关 rename、不关 copy，等于半套守卫（见 §7.2 F1）。

## 2. 决策

### D1 「到达」的判据 = 目录级事实，不看改名分

`archive/<name>/` 是**本次到达的 change**，当且仅当**五条同时成立**：

1. **基准树里该路径完全没有 entry**：在 **`M = git merge-base(base, head)`** 的树里，
   `<changes_root>/archive/<name>` **既不是 tree 也不是 blob**（该路径下也没有任何 entry）。
   ⚠️ **措辞订正（R1 实测）**：初稿写「该前缀下没有任何 tree entry」——**对「base 同路径是一个 blob」是盲的**：
   `git ls-tree -r <M> -- <path>/`（带尾斜杠）对同路径 blob 返回 **0 行** ⇒ 会误判「不存在」。
   本稿钉死为「**该路径在基准树里完全没有 entry**」，实现用**不带尾斜杠**的
   `git ls-tree <M> -- <path>`（实测：base 是 blob 时返回 1 行 `100644 blob …`，非空 ⇒ 判「存在」）；
2. **head 树里存在、且是一个 tree、且其直接子项里含 ≥1 个 `policy.required_artifacts`**：
   这是「**change 目录**」的目录级定义（组织型 / 工具型子目录不是 change 目录，见 §5.3 N10）；
   探测用**契约门同一张** `policy.required_artifacts` 表，不引入第二套口径；
3. **不是从另一个归档目录改名而来**：到达组里**没有**任何记录的 `old_path` 落在
   `<changes_root>/archive/**` 下（否则「把旧归档目录改个名」就能白捡一份现成证据，见 §5.3 N8）；
4. **有源时须名识别**：若到达组里存在 `old_path` 落在 `<changes_root>/<src>/` 下（即**有源** `src`），
   则要求 `name == src` 或 `name.endswith("-" + src)`；
5. **内容不得整份取自 base 树里仍然存在的 change 目录**（**新增，堵 F1 的 copy 变体**，定义见下）。

⇒ 与 `change.status` 是 `A` 还是 `R<分数>` **完全无关**。两只症状（出生即归档 / move 带内容改动）同一刀切掉。
⇒ **「出生即归档」没有源**（条件 4 无从施加）——这正是本 change 要接受的**反转**；
而「内容整体搬进一个新建目录、源 change 仍在 active」**有源** ⇒ 条件 4 生效（`archive/misc/` 不认得 `z` ⇒ 不授予）。

**⚠️ 基准 revision 必须与 `changed_files` 同源（本项由 grill 逼出，初稿只写「base」）**：
`gitutil.changed_files`（`:105`）用的是 **`base...head`**，即 diff 成员是按 **merge-base** 算的。
基树查询若改用 `base` ref 的**原树**，则当 base 分支在分叉点之后又前进时，
「到达判定」与「diff 成员」会**对不上**（同一目录可能被 diff 认为新增、却被基树认为已存在，或反之）。
⇒ 本 change 把基准钉死为 **`merge-base(base, head)`**，并加一条用例（§5.1 第 7 条）。

**为什么不用 diff 推断「是否新增」**：diff 里「`A`」只说明这条路径是新增的，
说明不了**那个目录**是不是新的——「预存归档目录被塞进一个新文件」也是 `A`，
而那种情形正是必须继续拒绝的（D3）。⇒ **只有查基树**才能把两者分开。

#### D1 第 5 条：内容来源判据（R1 的 F1 逼出来的）

**威胁（实测复现）**：把 base 里一份**证据齐全**的归档目录 `cp -r` 到新名（源目录**原封不动**），
只改 `reviews/*.manifest.json` 里的 `change_id` / `head_sha`，再改 `src/**`：
新目录在 diff 里**全是 `A`**、源目录**完全不在 diff 里** ⇒ 条件 3 看不见（组内没有 `old_path`）、
条件 4 无源可核 ⇒ 拿到资格 ⇒ 逐字节未变的证据让**全部哈希绑定、`reviewer ≠ author`、
grill 正文判据、三条 stage 门**通过 ⇒ **一个只改了 `src/**`、零新证据的 PR 变绿**。
本工作区实测（`/tmp/d8`）：`git diff -M --name-status` 全 `A`；新目录在基准树里 0 entry。

**判据（目录级内容事实，**不依赖 diff 记录**）**：

- 记 **`E(X)` = 目录 X 的「证据指纹」**：`(相对路径, blob sha)` 集合，取
  `<X>/tasks.md` + `<X>/specs/**` + `<X>/reviews/**/*.md`——
  即**被 manifest 哈希绑定的 artifact**（`constants.HASHED_ARTIFACTS` = `tasks.md` / `specs`）与
  **被绑定为报告的报告正文**（`reviews/**/*.md`）；**排除** `reviews/*.manifest.json` 本身
  （它是**自指**的元数据：改它不影响任何被绑字节）。
- 若 base 树里存在一个 change 目录 **D**（active 的 `<changes_root>/<id>/` 或归档的
  `<changes_root>/archive/<name>/`）满足 **`E(D) ≠ ∅`**、**`E(D) ⊆ E(A)`**，且
  **D 不是「本次已被搬走的目录」**，则**不授予** A。
- 「**本次已被搬走**」= 二者之一：① D 的路径是到达组某条记录的**源目录**（`old_path` 落在 D 下、
  `new_path` 落在 A 下）；② D 的路径在 **head 树**里已不存在。
  （两条都取「或」，是为了不误伤 `diff.renameLimit` 未配对、源目录被重建等边角；
  ① 挡的是「本次真的从它搬过来」，② 挡的是「它已经不在了 ⇒ 内容只能是从它搬走的」。）

**为什么这样够用（穷举机械复制者能做的四类改动）**：

| 攻击者的动作 | 结果 |
|---|---|
| 只改 `reviews/*.manifest.json`（`change_id` / `head_sha` / `base_sha`…） | 指纹**不含** manifest ⇒ `E(D) ⊆ E(A)` 仍成立 ⇒ **拒** ✓（`/tmp/d8` 实测两侧指纹逐行相同） |
| 往 A 里**新增**文件（哪怕新内容） | `⊆` 的语义是「D 的每个证据文件在 A 里**逐路径逐字节**都在」⇒ 新增不破坏 ⇒ **拒** ✓ |
| **删掉** A 里的某个证据文件 | `tasks.md`/`specs` 被哈希绑定、报告被 `report_path` 引用、`proposal/design/specs/reviews` 是必需件 ⇒ 缺件 / 哈希不匹配 ⇒ **红** ✓ |
| **改字节** | 同上：哈希绑定立刻崩 ⇒ **红** ✓ |

⇒ 四个方向都关掉了，且**不引入新的启发式**（全部是树对象事实）。

**它不改变工具既有的能力边界**（`contract.py:9`：hash 绑定证「证据之间没漂移」，**不防伪造**）：
一个愿意改字节**并重算 manifest 哈希**的构造仍能过——但那与「从零手写一份完整证据」**等价**，
是**本工具从来就不设防**的那一类（今天的 active change 路径同样拦不住）。
⇒ 第 5 条的目标是**机械复制**（`cp -r` + 改两个字段，零创作成本），不是防伪造。

**误伤面（明写）**：只有当某个 base change 目录的**全部**证据文件在 A 里逐字节重现、
且那个目录**在 head 里仍然存在**时才会拒绝。真实的新归档 change 不会命中；
**唯一**命中形态是「拿仓库里某个现成 change 当模板**整份逐字节**复制」——那正是本条要拒的形态。
已知边界（低危，fail-closed）：一次**合法 move** 若因 `diff.renameLimit` 未被 git 配对成 rename、
且源目录又被**重建**，会命中第 5 条（今天该形态因无 `R100` 本来也红 ⇒ 无回归）。

> **为什么不直接用 diff 的改名/复制检测**：R1 实测 `-M` 看不见 copy；**连 `-M -C` 也看不见**
> （`-C` 默认只从「被改 / 被删」的文件找副本，而复制攻击的源目录**原封不动**）；
> 要 `--find-copies-harder` 才可能看见——那仍是启发式，且会显著放大 diff 成本。
> ⇒ 用**树对象事实**（blob sha）而不是启发式，与本 change 的整体纪律一致。

### D2 到达方式不设限，且不改变证据门槛

到达的归档 target 走与 active change **完全同一套**：`validate_change_dir`（必需件）、
manifest 的 hash / revision 绑定、grill 报告正文判据、`code_hits` 触发的 `building` / `grill-adversarial` 硬门。
**SHALL NOT** 为归档 target 引入任何第二套判据或豁免。

> **对称性不变量**（本 change 的核心，**限定到「证据门槛」维度**）：
> 同一个 change 的同一份内容，放在 `changes/<id>/` 下与放在 `changes/archive/<name>/` 下，
> 在**证据门槛**上 SHALL 给出相同结论——必需件、manifest 的 hash / revision 绑定、
> `reviewer ≠ author`、grill 报告正文判据、以及 `code_hits` 触发的 stage 集合。
> ⚠️ **显式排除 `stale` 维度**（grill 实测纠正）：`policy.stale_exempt_paths` 对 `archive/**` **整块**豁免，
> 对 active 的 `proposal/design/tasks` **不**豁免（同一份 `proposal.md`：active ⇒ 不豁免、archive ⇒ 豁免，实测 `False vs True`）。
> ⇒ 「同一内容两种位置结论完全相同」按字面**不可满足**；这个非对称是**既有口径**，与本 change 正交，
> 属 §8 Q2 的暗房议题，**本 change 不宣称**在该维度上对称。

**为什么这条足以防绕过**：一份「伪造的归档目录」要绿，仍必须凑齐与 active change 等价的全部证据
（提案/设计/任务/specs/reviews、三份 stage manifest、`reviewer ≠ author`、grill ≥3 条决策、
building review …）。**到达方式不降低任何一条门槛**——这也是它与「凭空多出一个免检区」的本质区别。

### D3 保留真正承重的那条守卫，且**升级**为基树判定

**SHALL NOT** 给一个 `base` 里**已存在**的归档目录授予资格。
`archive-awareness` 用「目标目录名必须认得源 id」来挡，但它自己承认有**残留边界**：
目标名恰好认得源 id 的**部分 move** 仍会授予。

本 change 用 **D1 的第 1 条（基准树里没有 entry）**把它**真正关掉**：

| 构造 | `archive-awareness` | 本 change |
|---|---|---|
| `git mv changes/z/notes.md → changes/archive/y/notes.md`（`y` 已存在、名不认得 `z`） | 不授予 ✓ | 不授予 ✓（基准树里 `y` 存在） |
| `git mv changes/z/notes.md → changes/archive/2026-x-z/notes.md`（该归档目录**已存在**） | **授予**（残留边界） | **不授予 ✓** |
| 往**已存在**的归档目录新增 / 修改 / 删除文件 | 不授予 ✓ | 不授予 ✓（同上） |

**名识别守卫（D1 第 4 条）是否保留**见 §8 **Q1**（本稿当前取「保留」，**但推荐改成删除**，理由见该条）。

### D4 幽灵 active id：按**到达集合**排除旧路径，而不是按 `R100`

`changed_change_ids` 的 `archived_sources` 改为「**到达组的全部记录的 `old_path`**」。
到达组是**目录级**的（D1）⇒ `R<100` 的记录也在组内 ⇒ 幽灵 active id 消失。

⚠️ **收窄（grill R-B + R1 §E）**：不能无条件排除「到达组里所有 `old_path`」。
反例：一次到达 `archive/2026-10-15-other/`，同 diff 里还有人把 `changes/other/notes.md`
搬进这个新目录 —— 若照搬，`other` 会**静默消失**（它的目录还在 head 里、其它文件一个没动）。
⇒ 排除条件加一条**目录级事实**：**该记录的源 change 目录在 head 树里已不存在**
（= 那个 change **整体**搬走了；它才是那个被归档的 change）。
源目录仍在 head 里 ⇒ **不排除** ⇒ 它照旧按 active 契约校验（部分搬走的目录**必须**被问话）。

### D5 受保护写入的豁免：同一份到达集合，`R<100` 一并免，但**旧侧条件不许丢**

`_check_protected_writes` 里「归档 move 免解释事件」的判据，从**逐文件 `is_archive_move`**
换成「**该记录属于某个到达组，且其 `old_path` 落在 `<changes_root>/<active-id>/` 下**」。

**为什么必须带旧侧条件（R1 的 M-D5）**：初稿措辞是「该记录**属于某个到达组**」，未定义「属于」。
其自然实现（只看 `new_path` 落在到达目录下）会**放开**一条今天要事件的形态：
把 `openspec/specs/secret.md` **移入**一个到达的归档目录——今天该记录**要**事件，
宽口径下会被豁免 ⇒ 受保护物被搬出保护区却无需解释。⇒ 保留 `is_archive_move` 的**旧侧条件**
（源在 **active change 目录**下），只把「`R100`」放宽成「到达组」。

**放宽了什么**：`R<100` 的记录（如重建过的 manifest、被追加过的事件文件）不再各报两条
「受保护路径被写入，但没有结构化解释事件」；它们今天不豁免只是因为它俩**顺带改了内容**。
**为什么可接受**：那 8 条本来就是**收尾次序的必然产物**，不是「偷偷改动」；
而 manifest 的**内容真伪**由它自己的哈希绑定与 stale 判据把关，
**不靠**「要不要写一条解释事件」把关（active change 新增 manifest 本来就免事件，门槛一致）。

**没有放宽什么**：
- 对 `base` 里**已存在**的归档目录的修改 / 删除（`M` / `D`）——目录不在到达集合里 ⇒ **仍逐条要解释事件**（回归钉）；
- 「把受保护文件搬进到达目录」⇒ 旧侧不落在 active change 目录下 ⇒ **仍要事件**（M-D5 钉住）；
- 出生即归档（全 `A`）本来就不需要这条豁免：它的文件是**新增**，`**/reviews/*.manifest.json`
  与 `**/workflow-events.jsonl` 走既有的「不变集 + `A` ⇒ 免事件」分支，其余路径命中不了任何保护面。

### D6 归属与别名的口径不变

归档 target 的 `change_id` 仍是**归档目录名**；`accepted_change_ids` 仍是
`{归档目录名} ∪ {能从 move 记录里解析出的源 id}`。
出生即归档（无源）⇒ 集合只有目录名——与今天「用 `manifest build --change <目录名>`」的口径一致，
**不新增**别名种类。

### D7 纯函数边界与接线

到达判定需要**树事实**（基树 + head 树），因此：

- 新增 `gitutil` 帮助函数（语义 **fail-closed**：读不出来 ⇒ 报 finding、**不授予**）：
  - `tree_entry(root, rev, path) -> (type, sha) | None`——**不带尾斜杠**查一个路径自身的 entry
    （blob 也算「存在」，见 D1 第 1 条；也用于「源目录在 head 里还在不在」）；
  - `tree_entries(root, rev, path) -> list[(type, sha, path)]`——列某个前缀下的全部 entry
    （`--` 直查路径本身而非 `path/`，避免 D1 第 1 条那个盲区）；指纹与必需件探测都用它。
- 到达判定只留**一份**实现，且**纯函数化**：把树读取作为**注入的谓词**（而不是在判定里调 git）——
  判定本体保持可单测（不需要真 git 仓）。
  ⚠️ **接口订正**：初稿只注入 `base_exists: (path) -> bool`，**不够**——D1 第 5 条要 **blob sha**、
  D4 要 **head 树**。⇒ 注入面写成一对读取器（如 `TreeReader` 协议：`entry(rev, path)` / `entries(rev, path)`，
  或 `base: Reader` + `head: Reader` 两个入参），由 `checkcmd` 传入真 git 实现、由单测传入**假树**。
- `contract.change_targets(...)` 增加树读取入参；`changed_change_ids` 同理（D4）。
- 保护写检查（`checkcmd._protected_writes`）接收同一份到达集合（含每个名字的到达组）。
- **`manifestcmd` 本 change 不改**：它**不调用** `change_targets`（`grep -n change_targets
  src/witnessloop/manifestcmd.py` 为空），自己按**磁盘存在性**解析 active 优先 / 否则 `archive/<name>`
  （`manifestcmd.py:33-48`）。两者真正共用的是 `validate_change_dir` 与 `resolve_report_path`。
  ⇒ 本 change **不**声称在 `change_targets` 上共用；若实现时发现 `manifest build` 也需要感知「到达」，
  须**另写清要共享什么**，不得含糊带过。

## 2.5 Code-Resolved Questions（不进停轮队列）

| # | 问题 | 结论 | 依据 |
|---|---|---|---|
| C1 | 「出生即归档」的归档目录名不认得任何源 id，名守卫会不会因此失效？ | 无源即无守卫可施；该路径的证据门槛与 active 完全一致（D2） | 本 change 的设计；用例见 §5.1 |
| C2 | 到达判据会不会把「预存归档目录 + 新增文件」误判为到达？ | 不会：基准树里该路径有 entry ⇒ D1 第 1 条不成立 | §5.3 的用例 N3 钉住 |
| C3 | 纯归档 move（全 `R100`）会不会因为换判据而**失效**？ | 不会：基准树里不存在 ⇒ 到达；今天认得，修后仍认得 | `proposal.md` 表第 2 行（修前修后都通过） |
| C4 | 会不会把 `archive` 当成一个 change id？ | 不会：`archive_root` 自身不是 target（既有行为，回归钉） | `changed_change_ids` 既有的 `archive/**` 排除分支 |
| C5 | 组织型 / 工具型子目录（`archive/2026/`、`archive/notes/`）会不会被当成到达的 change？ | **不会**：D1 第 2 条要求该目录的直接子项里含 ≥1 个 `policy.required_artifacts` | R1 的 F2；本工作区实测 `archive/2026/` 的直接子项是 `10-15-foo`（tree）、`archive/notes/` 下必需件数 = 0（`/tmp/d8d`） |
| C6 | `base` 里同路径是个**文件**、head 里变成目录，会不会被误判成「到达」？ | **会到达、且这是对的**（该路径在基准树里确实是新出现的目录），但**措辞不能写成「前缀下没有 tree entry」**（那样连「base 已是目录」也会漏） | R1 §E；本工作区实测带尾斜杠的 `ls-tree -r` 对同路径 blob 返回 0 行（`/tmp/d8c`）⇒ D1 第 1 条钉死为「没有任何 entry」 |
| C7 | 指纹比对会不会因为 manifest 里写死了 `head_sha` 而被旧内容「锁死」？ | 不会：指纹只取**被绑字节**（`tasks.md` / `specs/**` / `reviews/**/*.md`），manifest 自身不入指纹 | D1 第 5 条的定义；`/tmp/d8` 实测两侧指纹逐行相同（改过 manifest 仍命中） |

## 3. 接线点（实现清单）

1. `src/witnessloop/gitutil.py`：新增树查询帮助函数（`tree_entry` / `tree_entries`，fail-closed）。
   调用成本：**1 次** `ls-tree -r <merge-base> -- <changes_root>`（一次列全，供 D1 第 5 条的 D 扫描 +
   必备件基线）+ **每个到达候选 1 次** `ls-tree <head> -- <archive>/<name>`（第 1/2 条与指纹共用）
   + **每个源 id 1 次** `tree_entry(<head>, <changes_root>/<src>)`（D4 收窄）。
2. `src/witnessloop/contract.py`：新增到达判定（注入式树读取器）；改 `changed_change_ids`（D4）、
   新增内容来源判据（D1 第 5 条）、改 `change_targets`（用到达集合产出归档 target）。
3. `src/witnessloop/checkcmd.py`：把到达集合传给受保护写入检查（D5）；替换 `is_archive_move` 的用法；
   构造并传入真 git 版的树读取器。
4. `src/witnessloop/manifestcmd.py`：**本 change 不改它**（见 D7 的订正）。实现时若确认 `manifest build`
   无需感知「到达」，此处留空并写明理由；若需要，则单独列出要共享的函数。
5. `docs/gate.md`：§5.1.1（归档语义）/ §4 / §3.2 的措辞与判据同步；§6 的已知边界更新
   （删「R100 要求」，补「基树不可读 ⇒ fail-closed」与「整份复制既有 change 目录 ⇒ 不授予」）。
6. `README.md`：接入指引里「归档时序」一段按新判据改写。

## 3.5 非目标

- **不收窄 `archive/**` 的 stale 豁免**（暗房）——既有口径、与本 change 正交，**另立 issue**（§8 Q2）。
- **不支持嵌套归档布局**（`archive/2026/<name>/`，见 §8 Q3）——本次维持今天的行为。
- 不改归档命名约定；不引入签名 / 防伪造；不改退出码语义；不建立「change ↔ 代码路径」映射。
- 不把「出生即归档」写成**推荐**流程（它只是必须被正确识别的形态）。

## 4. 风险

| # | 风险 | 处置 |
|---|---|---|
| R1 | **豁免面被开大**（`archive-awareness` 的 C3 教训：只让 `_require_change` 闭嘴 ⇒ 零证据 PR 变绿） | §5.3 的每条否定面都配一条**同等强度**的证据门用例；D2 的对称性不变量写成断言 |
| R2 | 树查询在浅克隆下失败 | `gate.yml` 已 `fetch-depth: 0`；仍失败则 **fail-closed**（报 finding、不授予），并有用例钉住。⚠️ 触发面比初稿暗示的窄：`merge-base` 求不出时 `changed_files` **已经**抛错并 fail-closed（`gitutil.py:107`、`checkcmd.py:55`），新增的独立面只剩「`merge-base` 成功但对某个 tree/blob 的 `ls-tree` 失败」 |
| R3 | 到达判定依赖 git 新 API，行为漂移 | 判定做成**注入读取器**的纯函数，单测不碰真 git；接线处另有集成用例 |
| R4 | 与 `manifest build` 的归档解析出现**两套实现** | **已订正**：`manifestcmd` 不调 `change_targets`（M4 实测），本 change 不声称该处共用；真正共用的仍是 `validate_change_dir` / `resolve_report_path` |
| R5 | 旧行为被无意改动 | §5.2 回归面逐条点名；纯 move 与既有否定面各有用例；**§5.2 第 6 行点名 5 条必须改写的既有测试** |
| R6 | **D1 第 5 条误伤**「拿既有 change 当模板整份复制」之外的正常流程 | 误伤面已明写（§D1 第 5 条）：只有**全部**证据文件逐字节重现且源目录**仍在 head** 才拒绝；用例正面钉住「合法 move 不被误伤」 |
| R7 | 第 5 条让「拿旧 change 复制成新 change 再改内容」的接入方踩雷 | 复制后**改动任一被绑字节**（`tasks.md`/`specs`/报告）即不再命中；这本来就是正常用法（改内容 ⇒ 必须重跑证据、重建 manifest） |

## 5. 测试策略（TDD）

### 5.1 用例（实现前红、实现后绿）

1. **出生即归档**：base 无 `changes/<id>`、head 有 `archive/2026-x-<id>/`（全 `A`）+ 改 `src/**` ⇒ 退出码 0。
2. **move 内带内容改动**：全 `R<100`（含重建过的 manifest）⇒ 退出码 0，且**无**幽灵 active id。
3. **接入方真实形状**：§1.3 第 1 行与第 3 行的两份 diff 各一条集成用例（可从接入方提交复算）。
4. **对称性**：同一份 change 内容，`changes/<id>/` 与 `archive/<name>/` 两种位置判绿判红一致（D2 不变量）。
5. **别名**：单纯 move（不重建 manifest）后归档前产出的 manifest 仍通过（既有用例保持绿）。
6. **fail-closed**：树读不出来 ⇒ 报 finding、不授予。
7. **基准 revision 对齐**：`base` ref 在分叉点之后前进过（原树 ≠ merge-base 树）⇒
   到达判定与 `changed_files` 的成员口径一致；反例构造：一个目录在 `base` 原树里**存在**、
   但在 `merge-base` 树里**不存在**（分叉后才加），此时它**是**到达（与 diff 口径一致）。
8. **名识别对「有源」的到达生效**：`archive/misc/`（新建、内容整体来自 active `z`）⇒ 不授予。
   ⚠️ 若 §8 Q1 裁定改成 (b) 删守卫，本用例**语义反转**（改为「授予、走完整证据门」）。
9. **内容来源（D1 第 5 条，F1 的用例）**：把 base 里证据齐全的归档目录 `cp -r` 到新名、
   只改 manifest 的 `change_id`/`head_sha`、再改 `src/**` ⇒ **不授予** ⇒ `require_change_for` 命中 ⇒ 红。
   对照用例（防误伤）：同一构造下**真的 `git mv`**（源目录在 head 里消失）⇒ 绿。
10. **组织型子目录（F2 的用例）**：新建 `archive/2026/10-15-foo/{proposal.md,…}` + 改 `src/**` ⇒
    **不产生**「`archive/2026/` 缺少必需件」这类 finding（`archive/2026/` 不是 target）；
    同时钉住 `archive/notes/sub/workflow-events.jsonl` 那类构造的行为与今天一致。
11. **base 同路径是 blob**：base 有 blob `archive/foo`、head 是目录 `archive/foo/…` ⇒
    `tree_entry(<merge-base>, …)` 非空 ⇒ 第 1 条**不**成立（不因「前缀下没有 tree entry」的措辞漏洞放行），
    按到达处理并由证据门判定（C6）。
12. **D4 收窄**：到达目录 + 同 diff 里把**另一个仍在 head 的** active change 的文件搬进它 ⇒
    那个 change **仍按 active 校验**（不得静默消失）。

### 5.2 回归面（**必须保持绿**）

- 纯归档 move（全 `R100`）今天通过 ⇒ 修后仍通过。
- 只改 `src/**` 而**不建**任何 change 目录 ⇒ 仍红。
- **删除** change 目录（`D`，非 rename）⇒ 仍报「change 目录不存在」。
- 归档 target 的 `change_id` 别名行为不变。
- `archive/` 本身不是 change id。
- **必须改写的既有测试**（改前绿是**旧语义**下的绿；本 change 反转其中两条的语义）：
  1. `tests/test_archive_awareness.py:274` `test_rebuilding_a_moved_manifest_in_the_same_diff_is_rejected`
     —— 它断言「move + 重写被 move 的 manifest（`R<100`）⇒ 红 + 幽灵 id」，**这正是本 change 要修好的形态 ii**
     ⇒ 语义**反转**为「绿、无幽灵 id」，测试应改名（如 `..._is_accepted`）。
     ⚠️ 它**不在** R1 的必须修改项里，是 grill M6 的同类但被漏掉的一条（本稿补上）。
  2. `:541` `test_N2_a_forged_archive_grants_nothing` —— 「伪造归档」从**不授予**变成**授予但由证据门禁拦下**；
     断言 `"没有任何 change 目录" in err` 必失败 ⇒ 改为断言缺件 / 缺 stage 那几条 finding。
  3. `:494` `test_the_summary_counts_directories_not_deduped_ids_on_a_tie` —— 它的构造里
     `archive/x/` **只有** `notes.md`（不含任何必需件）⇒ D1 第 2 条下它**不是** target ⇒ 报 1 而非 2。
     ⇒ 改写构造以保住「同一 id 撞两个目录、两份都校验」这个**意图**：base 上 active `x`（件齐）；
     feature 上把**整个** `changes/x` 纯 move 到 `archive/x`，**并**新建一个含必需件的 `changes/x`。
  4. `:109` `test_grant_requires_the_target_name_to_recognize_the_source_id` —— 直调
     `contract.archive_grant`；`archive_grant` 在本 change 里失去全部调用点（见 §3），
     ⇒ 随实现删除 / 改写为对新纯函数的用例（并保留「`R<100` 也授予」这条断言，因为判据换了）。
  5. `:49` 的 `_targets()` 助手与 A 节四条纯函数用例（`:87` / `:101` / `:134` / `:471`）——
     `change_targets` / `changed_change_ids` **签名变了**（要注入树读取器）⇒ 助手改为注入**假树**，
     四条用例按新接口改写（**语义不变**）。
  ⚠️ **对照（不要误改）**：`test_N4`（`:577`）/ `test_N6`（`:600`）断言的 `"没有任何 change 目录"` 在 D1 下**仍成立**
  （目标目录在基准树里存在）；`test_deeper_events_file_is_not_read`（`:378`）仍绿，但**理由变了**
  （从「`archive/**` 一律排除」变成「`archive/notes/` 不含必需件 ⇒ 不是 target」）——注释应更新。
- `uv run pytest -q` 全绿（基线数字在实现时实测填入，不写估计值）。

### 5.3 否定用例（**必须照样红 / 不授予**）

| # | 构造 | 期望 |
|---|---|---|
| N1 | 只改 `src/**`，不建 change | 红（`require_change_for`） |
| N2 | **修改**一个 `base` 里已存在的归档目录里的文件（`M`）+ 改 `src/**` | 红（不授予 ⇒ `require_change_for` 命中） |
| N3 | 往一个 `base` 里已存在的归档目录**新增**一个文件（`A`）+ 改 `src/**` | 红（基准树里该路径有 entry ⇒ 第 1 条不成立） |
| N4 | `git mv changes/z/notes.md → changes/archive/y/notes.md`（`y` 已存在、名不认得 `z`）+ 改 `src/**` | 红（D3） |
| N5 | 删掉 change 目录（非 rename） | 红（「change 目录不存在」） |
| N6 | 到达的归档 change **零证据**（件齐、零 manifest）+ 改 `src/**` | 红，且逐条点名三份 stage manifest（**防 R1**） |
| N7 | 伪造体：新建 `archive/<name>/` 但缺必需件（如无 `specs/`）+ 改 `src/**` | 红（契约门） |
| N8 | **把 `base` 里已存在的归档目录改名**（`archive/2026-09-30-foo/` → `archive/2026-10-15-foo/`，新名在基准树里不存在） | 红：D1 第 3 条（到达组里有 `old_path` 落在 `archive/**`）**且**第 5 条也命中（`E(旧目录) ⊆ E(新目录)` 且旧目录仍在 head）——两道都关 |
| N9 | **拷贝体（F1，新）**：`cp -r` 一份证据齐全的归档目录到新名（源**原封不动**）+ 只改 manifest 的 `change_id`/`head_sha` + 改 `src/**` | 红：D1 第 5 条（`E(D)` 非空且 `⊆ E(A)`，D 仍在 head） |
| N10 | **组织型子目录（F2，新）**：新建 `archive/2026/10-15-foo/{proposal.md,…}` + 改 `src/**` | 红，但**报的是**「没有任何 change 目录」（`archive/2026/` 不是 target），**不是**「`archive/2026/` 缺少必需件」这类假阴性 |
| N11 | **base 同路径是 blob（新）**：base 有 `archive/foo`（文件）、head 是 `archive/foo/{proposal.md,…}` + 改 `src/**` | 该目录**是**到达 ⇒ 红点由证据门给出（不得因「前缀下没有 tree entry」的措辞漏洞被放行、也不得报错崩溃） |
| — | **把受保护文件搬进到达目录**（`git mv openspec/specs/x.md → archive/<到达名>/x.md`） | 红（仍要解释事件，M-D5 钉住） |
| — | 归档时**顺带改 change id**（`git mv changes/old-id archive/2026-10-15-new-id`） | **当前设计下红**（第 4 条不满足）；这是**明写**的拒绝面，其取舍见 §8 Q1（选 (b) 则变绿） |

## 6. 文档影响

- `docs/gate.md`：§5.1.1 归档语义（判据从「R100」改成「目录新增 + 内容来源」）、§4（可达路径）、
  §3.2（时序建议）、§6（已知边界：删「R100 要求」，补「基树 / head 树不可读 ⇒ fail-closed」
  与「整份复制既有 change 目录 ⇒ 不授予」）。
- `README.md`：接入指引里归档时序一段；**不**把出生即归档写成推荐流程。
- 本仓 `openspec/specs/`：`archive-awareness` 能力的 delta 见 `specs/archive-awareness/spec.md`。
- **不改** `archive-awareness` 已归档 / 既有的其他 Requirement 文本（除本 change 明列的四条）。

## 7. Pre-Implementation Review

### 7.1 设计追问轮（独立零记忆审阅者，报告见 `reviews/grill-design.md`）

审阅者独立读了源码与 `archive-awareness` 的前身文档，复核了本稿的事实断言。**它确认了 3 条、推翻了 1 条设计缺陷、纠正了 4 处事实错误。** 本稿据此修订：

| # | 审阅者发现 | 本稿处置 |
|---|---|---|
| M1 | **规格自相矛盾**：Requirement 1 说「新建即到达」，同一 Requirement 的 Scenario 说「新建的 `archive/misc/` 不授予」，而正文**没有**名识别规则 | D1 补齐：把「有源时须名识别」写进正文并定义「有源」 |
| M2 | **对称性不变量按字面不可满足**：`stale_exempt_paths` 对 `archive/**` 整块豁免、对 active 的 `proposal/design/tasks` 不豁免 | D2 与 spec 都把不变量**限定到证据门槛维度**，并显式排除 stale 维度 |
| M3 | **基准未钉死**：`changed_files` 用 `base...head`（merge-base），基树查询若用 `base` 原树会与 diff 成员**对不上** | D1 第 1 条钉死为 **`merge-base(base, head)` 的树**，并加用例 |
| M4 | **事实错误**：`manifestcmd` **不调用** `change_targets`，本稿「共用同一实现」是假的 | D7 与 §3 第 4 条订正；不再声称该处共用 |
| M5 | **符号名错**：`gitutil.diff_name_status` / `checkcmd._check_protected_writes` 都不存在 | §1.1 改为 `changed_files`（`gitutil.py:99/105`）与 `_protected_writes`（`checkcmd.py:228/255`） |
| M6 | **既有测试必失败**：`tests/test_archive_awareness.py:541` 的断言在 D1 下不再成立 | §5.2 第 6 行逐条点名要改写的测试，并写明语义反转 |
| M7 | **停轮队列可瘦身**：初稿 Q1/Q4 能由代码定案 | §8 移出，附依据 |
| **新洞** | **改名一个已存在的归档目录 ⇒ 新名「在基准树里不存在」⇒ 白捡一份现成证据** | D1 第 3 条 + §5.3 N8 |

**未复核项（审阅者明确标注，R1 复核后仍成立）**：`proposal.md` 表里的具体相似度分数
（`R068/R069/R070/R090`）在本工作区**不可复算**——本仓从未归档过 change。
⇒ 实现期 4.2 必须用**接入方的真实提交**复算，不得直接引用本稿的数字。

### 7.2 对抗轮（R1，报告见 `reviews/grill-adversarial.md`）

独立零记忆对抗者，目标是**证伪** D1–D7。结论：**证伪成功 3 条**（F1 高危、F2 中危、F3 低-中危），
证伪失败 7 条（含「必须绿」的出生即归档与 move+重建 manifest 两条**实测绿**）。
本稿的处置：

| # | R1 发现 | 本稿处置 |
|---|---|---|
| **F1**（高危，端到端实测通过） | D1 第 3 条**只关 rename、没关 copy**：`cp -r` 现成归档目录 + 改两个 manifest 字段 ⇒ 零新证据的纯代码 PR **变绿** | **D1 新增第 5 条**（内容来源判据：`E(D)` 非空且 `⊆ E(A)`、且 D 未被搬走 ⇒ 不授予）；§5.3 新增 **N9**；本工作区复算见 §D1 第 5 条 |
| **F2**（中危，新增假阴性） | 组织型子目录 `archive/2026/` 被判成「到达的 change `2026`」⇒ 缺件假阴性；本仓既有测试 `tests/test_archive_awareness.py:378` 就含这种构造 | **D1 第 2 条**加「直接子项里含 ≥1 个 `policy.required_artifacts`」；§2.5 **C5**；§5.3 **N10**。嵌套归档是否支持 ⇒ §8 **Q3**（推荐本次不支持） |
| **F3**（低-中危，未列明的拒绝面） | 归档时顺带改 change id 被第 4 条拒绝，是否可接受未定 | 写进 §5.3 末两行（**明写的拒绝面**），并把取舍并入 §8 **Q1** |
| M-Q4 | 「`archive/` 非 change 子目录」假阴性被从停轮队列里丢掉 | 已作为 §8 **Q3** 回到队列（F2 的判据已把它从「误判」降级为「布局支持范围」） |
| M-D5（中危） | D5 的豁免措辞「属于某个到达组」过宽，会放开「把受保护文件搬进到达目录」 | **D5 收窄**：豁免还要求 `old_path` 落在 `<changes_root>/<active-id>/` 下；§5.3 加对照行 |
| M-DOC1 | `tasks.md` 3.5 与 `design.md` §3 第 4 条直接冲突 | 采纳 design 的订正（`manifestcmd` 不改），tasks 3.5 改写 |
| M-DOC2 | spec 写「上一条的**两条**判据」，而正文是四条（现为五条） | spec 改为「**五条**」，措辞与 design 逐条对齐 |
| M-DOC3 | `tasks.md` 0.2 写「Q1–Q4」，`design.md §8` 只有 Q1–Q3 | tasks 与 design 的编号对齐（§8 重排为 Q1–Q3） |
| M-DOC4 | spec 里「`manifest build --change <name>` … **共用同一实现**」重复了 M4 判为不实的主张 | 改成准确的共用项（`validate_change_dir` / `resolve_report_path`） |
| M-C1 | 条件 1 措辞「前缀下没有 tree entry」对「base 同路径是 blob」是盲的 | D1 第 1 条钉死为「该路径完全没有 entry」+ 实现用**不带尾斜杠**的 `ls-tree`；§2.5 **C6**；§5.3 **N11** |
| §E 低危（R-B） | D4 的 `archived_sources` 过宽，会把**别的仍在 head 的** active change 静默排除 | **D4 收窄**（源目录在 head 里已不存在才排除）；§5.1 第 12 条用例 |

**R1 的未验证项（本稿原样保留，实现期不得当已验证）**：
① 接入方 asterwynd 的具体数字（33 文件全 `A`、`R068…`、「120 个归档目录」）本工作区**无法复算**；
② R1 的 F1 端到端是**proxy**（用 active 目录跑通证据门禁——因为当时还没实现 D1），
「到达的**归档**目录」这一跳是推演 + 本工作区对 diff / 指纹的复算，**不是**实现后的实测；
③ 浅克隆下 `ls-tree` 的确切失败模式未取得可靠证据（D7 的 fail-closed 断言具体文案未定）；
④ merge commit 形态下 `merge-base` 与到达判定的交互未实测；
⑤ 「`manifest build` 是否真的不需要感知到达」只复核了「不调 `change_targets`」这一**事实**。

### 7.3 对抗轮（R2）

（待跑；产物进 `reviews/grill-adversarial-r2.md`。）

## 8. 停轮问题（Open Questions —— 逐条附本 change 真实场景的具体例子）

> 每条都给出**具体到参数 / 输入输出的前后对比**，便于快速判断。
> ⚠️ 编号在本轮**重排过**：初稿的 Q1/Q4 已由代码定案移出；R1 提议移出的「归档目录改名」见下方「已定案」表。
> **Q1 / Q3 是本轮（R1 之后）改过推荐的**，理由随条目给出。

### 已由代码 / 实测**定案**、移出停轮队列（不占用户时间）

| 曾经的提问 | 定案 | 依据 |
|---|---|---|
| 到达判定用「显式查基树」还是「只用 diff 推断」？ | **显式查基树**（无选择余地） | 只用 diff 会被 §5.3 **N3** 直接证伪：往**已存在**的归档目录加文件状态也是 `A`，diff-only 会授予 |
| 归档 target 的 stage 集合是否与 active 完全一致？ | **完全一致、零特判** | `checkcmd.py:105-119` 的 stage 硬门由 `code_hits` 触发；选「更松」即违反 D2，属自相矛盾 |
| 把**已存在**的归档目录**改名**（`archive/2026-09-30-foo/` → `archive/2026-10-15-foo/`），该不该授予资格？ | **不授予**（= D1 第 3 条 + 第 5 条） | 允许它等于**接受一个已知绕过**（零新证据的纯代码 PR 变绿）——这是本工具的核心安全属性，不是口味问题。R1 的 F1 进一步证明「白捡证据」在 copy 变体下**已经可达** ⇒ 没有「另一个可接受的策略」可选。若将来要加**友好文案**（在拒绝时点名「检测到归档目录改名」），属实现细节，不占停轮 |

### Q1 归档目录名「必须认得源 id」这条守卫（D1 第 4 条），对**有源**的到达是否保留？

- (a) **保留**（**当前稿的文本**）：`name == src` 或 `name.endswith("-" + src)` 才授予。
- (b) **删掉**（**本稿的推荐**；grill 与 R1 都建议 (b)）：到达方式不设限，名字不必再核。
- **本稿改推荐为 (b) 的三条理由**：
  1. 它原本要挡的形态（**单文件** move 进**已存在**的归档目录）已被 **D1 第 1 条**独立关掉（R1 实测）；
  2. 「白捡现成证据」已由 **D1 第 3 / 第 5 条**在**记录**与**内容**两个层面关掉；
  3. 留下的唯一后果是**命名约定**，而它与本 change 的「到达方式不设限」相抵：
     同一份内容、同一个最终路径 `archive/misc/`，判绿判红**取决于 base 里源目录在不在**。
- **具体例子**：
  - `git mv openspec/changes/foo-x openspec/changes/archive/misc` + 改 `agent/x.py`（该 change 件齐、三份 manifest 齐）：
    - (a)：`misc` 不认得 `foo-x` ⇒ 不授予 ⇒ **红**，报「`agent/x.py` 属于必须挂 change 的路径……但本次 diff 里没有任何 change 目录」；
    - (b)：该目录在基准树里不存在 ⇒ 到达 ⇒ 走**同一套**证据门 ⇒ **绿**（要红也只能因为证据不全）。
  - **对照**：把同样的内容 `cp -r` 到新建的 `archive/misc/`（源目录**不动**）：两种选法**都绿**（无源可核 ⇒ 第 4 条无从施加）。
  - **再对照（R1 的 F3）**：`git mv openspec/changes/old-id openspec/changes/archive/2026-10-15-new-id`（**归档顺带改 change id**，证据齐）：
    - (a)：`2026-10-15-new-id` **既不等于** `old-id`、**也不以** `-old-id` 结尾 ⇒ **红**（明写的拒绝面）；
    - (b)：**绿**（别名集合 = {新目录名} ∪ {从 move 记录解析出的源 id} 已覆盖两侧，manifest 用哪个 id 都认）。
- **推荐：(b)**（fail-closed 方向相反的一刀：删守卫是**放宽**，所以即使裁 (a) 也不阻塞实现——
  但裁 (a) 会让「归档时改 id」这类非典型流程必须拆成两步）。

### Q2 `archive/**` 的 stale 豁免（「暗房」）本次一并收窄，还是另立？

- (a) **另立 issue，本次不动**（**本稿推荐**）：与本 change 正交；且它**今天就已存在**，不是本 change 造成的。
- (b) 本次一并收窄：范围膨胀到「审阅后允许出现哪些归档路径」，需要独立的证据推导。
- **具体例子**：已归档 change 的 `proposal.md`，在它那份 manifest 记的 `head_sha` **之后**被改一个字。
  - 今天 / (a)：**不判 stale**（路径命中 `policy.stale_exempt_paths` 末项 `openspec/changes/archive/**`）。
  - (b)：应当判 stale。但这与「到达识别」是两件事——修 (b) 得先回答「归档后哪些改动该被允许」。
- ⚠️ 这条**不阻塞**本 change：对称性不变量（D2）已限定到「证据门槛」维度、并显式排除 stale 维度。

### Q3 **嵌套归档布局**（`archive/2026/<name>/`）本次要不要支持？

- **背景（本轮已修的假阴性）**：R1 的 F2 指出「`archive/` 下的非 change 直接子目录会被判成到达的 change」。
  本稿已用 **D1 第 2 条**（直接子项须含 ≥1 个 `policy.required_artifacts`）修掉：
  `archive/2026/`、`archive/notes/`、`archive/templates/` 这类组织型 / 工具型子目录**不再被误判**
  （本工作区实测 `archive/2026/` 的直接子项只有 `10-15-foo`（tree）、`archive/notes/` 下必需件数 = 0）。
- **剩下的是另一个问题**：**嵌套归档**本身要不要**支持**。
- (a) **本次不支持**（**本稿推荐**）：今天也不支持——`archive_grant` 取 `archive/` 后**第一段**做目录名
  （`2026`），名字认不得源 id ⇒ 不授予 ⇒ 只改 `src/**` 的 PR 报「没有任何 change 目录」⇒ **红**。
  本稿的探测把它排除后，**行为与今天逐字相同（仍红）**，但报的是**准确的那句话**。
- (b) 本次支持：把候选定义改成「`archive/**` 下**任意深度**、含必需件、且相对基准树整体新增的目录」，
  change id 取该目录名（`10-15-foo`）——牵动 `change_id` 口径、中间层校验、别名集合与 `manifest build` 的
  目录解析，范围不小。
- **具体例子**：某接入方想按年份组织归档，落 `openspec/changes/archive/2026/10-15-foo/{proposal.md, design.md, tasks.md, specs/, reviews/}`
  （件齐、三份 manifest 齐），本 PR 同时改 `src/app.py`：
  - 今天 / (a)：**红**——报「`src/app.py` 属于必须挂 change 的路径……但本次 diff 里没有任何 change 目录」
    （与今天的逐字输出一致，不会再多报一条莫名其妙的「`archive/2026/` 缺少必需件」）。
  - (b)：**绿**——`2026/10-15-foo` 被认作到达，按其证据校验。
- **推荐：(a)**。理由：本 change 的非目标已写「不改归档命名约定」；支持嵌套布局需要独立的
  「归档目录布局」议题（含 `manifest build --change` 的解析口径），与「到达识别」正交。
