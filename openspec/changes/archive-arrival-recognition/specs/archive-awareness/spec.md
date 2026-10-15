# archive-awareness — 归档 change 的到达判定改为「目录级」

> 本 change 对 `archive-awareness` 的下列 Requirement 做**修改 / 新增**（不写计数——见下每条）：
> 把「本次 diff 里到达了一个归档 change」的判据，从**逐文件 `R100` 改名**换成**目录级事实**——
> `archive/<name>/` 在基准树里**没有 entry**、在 head 树里是一个**含全部必需件的 change 目录**、
> 且其内容**不是现成证据的机械搬运**。
> 到达方式（`git mv` 过来 / 直接新建在 `archive/` 下）**不设限**；
> 到达的 target 走与 active change **完全同一套**契约与证据校验（**到达方式不改变证据门槛**）。
> ⚠️ 已知**会被反转**的旧条款：
> - 否定面 **N7**（「同一 diff 里既归档又改写被 move 的文件 ⇒ 不授予」）——**反转**（`design.md §1.5`：它**不承重**，
>   且它正是接入方的真实形态 ii）；
> - 否定面 **N2**（「新建 `archive/<name>/**`（`A`、无 active 源）⇒ 不授予」）——**部分反转**：
>   **件齐**的新建归档目录**会**被授予（然后由证据门把关）；但**缺任一必需件**的伪造目录**仍不授予**
>   （判据 2 不成立 ⇒ 它根本不是到达）。⚠️ R1 曾把这条写成「全部反转」，第 2 条收紧后必须按本段读。
> 真正承重的「不得**白捡**一份现成证据」被**升级**保留：判据 3（记录层：来自 `archive/**` 的改名）
> + 判据 5（**内容层**：内容必须是新写的或本次搬来的）。

## Requirement: 归档 change 的「到达」判定 SHALL 基于目录级事实，SHALL NOT 基于逐文件改名分

`check` SHALL 把 `archive/<name>/` 认作「本次 diff 里到达的 change」，当且仅当**同时**满足：

1. **基准树里该路径完全没有 entry**：在 `M = git merge-base(base, head)` 的树里，
   `<changes_root>/archive/<name>` **既不是 tree 也不是 blob**（该路径下也没有任何 entry）。
   基准树 SHALL 是 **`git merge-base(base, head)` 的树**——与 `gitutil.changed_files`
   （`src/witnessloop/gitutil.py:105`）判定 diff 成员所用的 `base...head` **同源**；
   SHALL NOT 用 `base` ref 自身的树。
   ⚠️ 判据 SHALL **不**表述成「该前缀下没有任何 tree entry」：实测
   `git ls-tree -r <M> -- <path>/`（带尾斜杠）在「base 同路径是一个 blob」时返回 **0 行**，
   会把「base 里已有实体」误判成「不存在」。判定 SHALL 用**不带尾斜杠**的
   `git ls-tree <M> -- <path>`（base 是 blob ⇒ 非空 ⇒ **不授予**；不存在 ⇒ 空 ⇒ 进入下一条）；
2. **head 树里该路径是 tree，且含全部 `policy.required_artifacts`**
   （判定语义 SHALL 与契约门**完全一致**：`<dir>/<artifact>` **路径存在**——即「`specs` 是同名普通文件」
   这类形态与 `contract.validate_change_dir` 同结论）。
   ⇒ 组织型 / 工具型子目录（`archive/2026/`、`archive/notes/`、`archive/templates/`）SHALL NOT 被当作到达的 change；
3. **不是从另一个归档目录改名而来**：到达组里**没有**任何记录的 `old_path` 落在
   `<changes_root>/archive/**` 下；
4. **有源时须名识别**：若到达组里存在 `old_path` 落在 `<changes_root>/<src>/` 下（即**有源** `src`），
   则对**每一个**这样的源 SHALL 要求 `name == src` 或 `name.endswith("-" + src)`；
   **无源**（出生即归档）时本条无从施加；
5. **内容来源（防「搬运现成证据」）**：到达目录 A 的**证据文件集 `Ev(A)`** 里**每一个文件**
   （按 head 树；**内容为空**者除外）SHALL 满足下列**之一**：
   - (a) 其 blob 在基准树的 `<changes_root>/**` 里**不出现**（= 本次新写的内容）；
   - (b) 它是**本次 diff 里某条改名记录的落点**（记录的 `new_path`，即本次搬过来的）。
   违反 ⇒ `A` SHALL NOT 被授予资格。

   ⚠️ **`Ev(A)` SHALL 由数据推导，SHALL NOT 按路径前缀硬编码**（实测：按「`tasks.md` / `specs/**` / `reviews/**`」
   三段前缀硬编码时，**把报告挪出 `reviews/`**、**把 `specs` 换成同名普通文件**这两条零成本改法都能让证词整体出圈，
   且真 CLI 判绿）。`Ev(A)` SHALL 由下列三部分构成：
   1. `constants.HASHED_ARTIFACTS` 覆盖的 artifact 路径**整体**（`tasks.md`；`specs`——
      **是目录 ⇒ 其下全部文件；是普通文件 ⇒ 它自己**）；
   2. `policy.review_manifest_glob` 命中的**每一份 manifest**，**以及每份 manifest 的 `report_path`
      解析出的那个文件**（SHALL 用与哈希校验同一解析器 `contract.resolve_report_path`）；
   3. `<A>/reviews/**` 下的全部文件。

   ⚠️ `proposal.md` / `design.md` SHALL NOT 被纳入 `Ev(A)`：它们**不被 manifest 哈希绑定**，
   且「共用 stub ⇒ 逐字节撞车」是现实误伤源；排除它们**不削弱**本判据——搬运者仍会被上面三类文件抓住。

`check` SHALL NOT 依据 `git diff --find-renames` 给出的**逐文件状态**（`A` / `R<分数>`）或**相似度分数**
来判定到达资格。特别是：SHALL NOT 要求 `status == "R100"`，SHALL NOT 因为「某个被移动文件在同一 diff range 内
另有内容改动」而收回资格，SHALL NOT 依赖 `-M` / `-C` 的**副本检测启发式**
（实测 `-M -C` 看不见「源目录原封不动」的整份复制）。

⚠️ **判据 5 的能力边界（SHALL 明写，不得被读成防伪造）**：
- 它拦的是**机械搬运**：整份复制、复制后改路径、复制后改 / 删一两个文件（即使随后用 `manifest build`
  **重算哈希**）、混多个源、搬一个无关文件进来洗白、源是嵌套归档目录——上述形态 SHALL 全部不授予；
- 把**每一个**文件都改掉字节再重算 manifest 哈希者**不在此判据射程内**——那等价于「自己写一份完整证据」，
  属本工具既有的能力边界（`src/witnessloop/contract.py:9`：hash 绑定证「证据之间没漂移」，**不防伪造**）；
- **扫描面**是 `<changes_root>/**`（不是「扁平 change 目录」，也不是全仓）：放在 `changes_root`
  之外的现成证据副本**不可见**；
- **能力天花板（SHALL 明写，不得被读成「拦住了全部复用」）**：本判据是**逐字节**判据。
  把 `Ev(A)` 里**每一个**文件都动一个字节（例如各追加一个换行）、再用 `manifest build` 重算哈希 ⇒ **绕过**本判据
  （真 CLI 实测判绿），而证据的**语义内容未变**。⇒ 本判据挡的是**零改动 / 只动一处**的机械搬运；
  **不挡**「跑一个脚本给每份证据各加一个字节」这一档。封堵那一档需要**真实性**（签名 / 可验证来源），
  属本 change 的**非目标**（既有边界：hash 绑定证「证据之间没漂移」，**不防伪造**）。
- **完全旁路**：本判据的效力**依赖「`<changes_root>/**` 是存放 change 证据的唯一地方」这一前提**。
  现成证据的字节若在基准树里**另有副本**（发布副本 `docs/shipped/**`、仓内镜像、`changes_root` 迁移遗留的旧路径），
  把该副本 **`git mv` 进来** ⇒ (a) 与 (b) **同时**豁免同一份内容 ⇒ 本判据零命中。SHALL 登记进 `docs/gate.md §6`。
- **误伤面**：A 里某个**非空证据文件**与 base 的 `<changes_root>/**` 下某文件**逐字节相同**、且它不是本次搬来的
  ⇒ **fail-closed 拒绝**（finding SHALL **同时点名两侧路径**）。现实来源：从兄弟 change 原样复制来的
  `specs/**` 文件、内容就是 `PASS\n` 这类**极短样板**的报告、被原样复制的 `tasks.md` 样板、
  仓内**模板骨架**（`changes/_template/**`——模板 SHALL 放在 `changes_root` 之外）。
  **空文件**（0 字节，如 `reviews/.gitkeep`）SHALL 被豁免；`proposal.md` / `design.md` 的逐字节撞车 SHALL NOT 触发。

该 change 的 **id SHALL 是归档目录名**（不解析日期前缀）；其契约与证据校验 SHALL 与 active change 同一套
（必需件、review manifest 的 hash/revision 绑定、grill 报告正文、`code_hits` 触发的
`building` / `grill-adversarial` 两条硬门）。

### Scenario: 出生即归档（base 里无此 change，head 里全新增）
- **Given** diff 的基准树里**没有** `openspec/changes/<id>/`
- **And** head 里有 `openspec/changes/archive/2026-10-15-<id>/`（**件齐**：`proposal.md` / `design.md` / `tasks.md` / `specs/` / `reviews/`，且这些内容都是本次新写的）
- **And** 本次 diff 同时改动命中 `policy.require_change_for` 的路径
- **When** 运行 `check`
- **Then** 退出码为 0，且不再出现「本次 diff 里没有任何 change 目录」
- **And** 该 change 在**归档路径**上被校验

### Scenario: 同一 move 内带内容改动（`R<100`）
- **Given** base 里有 active 的 `openspec/changes/<id>/`，其 `reviews/building.manifest.json` 与
  `workflow-events.jsonl` 在本 diff range 内被重建 / 追加过（实测为 `R069` / `R090`）
- **And** head 里该 change 位于 `openspec/changes/archive/2026-10-15-<id>/`
- **When** 运行 `check`
- **Then** 退出码为 0
- **And** stderr **不含**「`openspec/changes/<id>：change 目录不存在`」（**无幽灵 active id**）
- **And** stderr **不含**「受保护路径被写入，但没有结构化解释事件」中指向那几份 manifest / 事件文件的条目

### Scenario: 纯 move 的行为**逐条不变**（回归）
- **Given** 一次全 `R100` 的整目录 `git mv`，把已审的 change 从 active 搬进 `archive/`
- **When** 运行 `check`
- **Then** 退出码为 0（与改动前一致）
- **And** 该归档 change 仍被认作本次 diff 的 change（`1 个 change 目录`）
- **And** 判据 5 SHALL **不**误伤它：被搬走的文件都是本次 diff 里改名记录的落点（(b) 成立）

### Scenario: 组织型子目录 SHALL NOT 被当成到达的 change
- **Given** 基准树里没有 `openspec/changes/archive/2026/`
- **And** head 里有 `openspec/changes/archive/2026/10-15-foo/{proposal.md, design.md, tasks.md, specs/, reviews/}`
- **When** 运行 `check`
- **Then** `archive/2026/` **不**被认作到达的 change（它不含 `proposal.md` 等必需件，其直接子项是一个目录）
- **And** **不**出现「`archive/2026/` 缺少必需件 `proposal.md`」这类 finding
- **And** 行为与改动前一致：若非嵌套布局的 `archive/<name>/` 不存在，则「没有任何 change 目录」照旧命中

### Scenario: 只含部分必需件的子目录 SHALL NOT 被当成到达的 change
- **Given** head 里新建 `openspec/changes/archive/notes/`，其下只有 `sub/workflow-events.jsonl`
  与一个 `reviews/` 子目录（**没有** `proposal.md` / `design.md` / `tasks.md` / `specs/`）
- **When** 运行 `check`
- **Then** `archive/notes/` **不**被认作到达的 change（判据 2 要求**全部**必需件）
- **And** stderr **不**出现「`archive/notes/：缺少必需件 proposal.md」这类假阴性
- ⚠️ 若判据 2 只要求「≥1 个必需件」，本形态会翻成假红（R2 的 B1）

### Scenario: 基准树里同路径是**文件** ⇒ 不授予
- **Given** 基准树里 `openspec/changes/archive/foo` 是一个 **blob**（文件）
- **And** head 里 `openspec/changes/archive/foo/` 是一个含必需件的**目录**
- **When** 运行 `check`
- **Then** 判据 1 SHALL 判「基准树里该路径**有** entry」⇒ **不授予**
  （不得因「前缀下没有 tree entry」的措辞漏洞放行，也不得崩溃）

### Scenario: 基树不可读 ⇒ fail-closed
- **Given** 无法解析基准 revision 的树（例如浅克隆，且 `merge-base` 本身可解析）
- **When** 运行 `check`
- **Then** 退出码非 0，且报出**点名该 revision** 的 finding
- **And** **不授予**任何归档到达资格（不得静默按「已到达」或「未到达」之一放行）

## Requirement: 只有「基准树里没有**且内容不是搬运来的**」的归档目录才授予资格（**保留承重守卫**）

「该 change 出现在本次 diff 里」这一资格的取得，SHALL 满足上一条的**五条**判据
（其措辞与 `design.md §2 D1` 逐条对齐）；
且 `check` SHALL NOT 因下列动作而认为任何 change 出现在本次 diff：

- **修改 / 删除** `<changes_root>/archive/<name>/**` 里**已存在**的文件（基准树里该路径有 entry ⇒ 判据 1 不成立）；
- 往一个**已存在**的归档目录里**新增**文件（同上）；
- 把 active change 的**单个文件**移入一个**已存在**的归档目录
  （如 `git mv changes/z/notes.md → changes/archive/y/notes.md`）——目标目录在基准树里有 entry ⇒ 不授予，
  源 change `z` 不得因此**静默逃检**；
- **删除** change 目录（非 rename）；
- 把非 change 目录（如受保护 spec）搬进 `archive/`；
- **整份复制**一个仍在的 change 目录，或复制后**改路径 / 只动一处（改一个字节 / 删一个文件）/ 混多个源**（判据 5）；
- 把复制的**报告挪出 `reviews/`**（放 change 目录根）再用 manifest 的 `report_path` 指过去（判据 5；
  `Ev(A)` 按 `report_path` 取证据），或把 `specs` / `tasks.md` **换成另一种路径形态**后把借用内容塞进去（判据 5）；
- 把**已存在**的归档目录**改名**（判据 3；判据 5 通常同时命中）。

### Scenario: 触碰已存在的归档目录不授予资格（`M` / `A` 两种造法）
- **Given** base 里已存在 `archive/2026-09-30-old/`
- **When** 本 PR **修改**该目录里一个文件（`M`）、或往它里面**新增**一个文件（`A`），并改动 `src/**`
- **Then** 该目录**不**进 change 集合 ⇒ 退出码非 0，`_require_change` 命中

### Scenario: 单文件移入既有归档目录 ⇒ 源 change 不得静默逃检
- **Given** base 里已存在归档目录 `archive/y/` 与 active change `z`
- **And** 本 PR 执行 `git mv openspec/changes/z/notes.md openspec/changes/archive/y/notes.md`，并改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0（`y` 不被授予；`z` 也不得因此绕过）

### Scenario: 把已存在的归档目录**改名**不授予资格
- **Given** 基准树里已存在 `openspec/changes/archive/2026-09-30-foo/`（证据齐全）
- **And** 本 PR 只做 `git mv openspec/changes/archive/2026-09-30-foo openspec/changes/archive/2026-10-15-foo`，
  并改动 `src/**`，**没有**产出任何新证据
- **When** 运行 `check`
- **Then** 退出码非 0（判据 3 不成立——到达组里有 `old_path` 落在 `archive/**`）
- **And** 判据 5 通常也同时命中

### Scenario: **整份复制现成证据不授予资格**（防 `cp -r` 绕过）
- **Given** 基准树里已存在归档目录 `openspec/changes/archive/2026-09-30-old/`（证据齐全，**本 PR 原封不动**）
- **And** 本 PR 把它的**整份内容 `cp`** 到 `openspec/changes/archive/2026-10-15-new/`，
  只改其中的 `reviews/*.manifest.json`（`change_id` / `head_sha`），并改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0（判据 5 不成立：A 里每一个文件既不是新 blob，也不是本次 diff 里改名记录的落点）
- **And** stderr 点名 `src/**` 与 `require_change_for`
- ⚠️ 没有判据 5 时，这份**逐字节未变的现成证据**（哈希绑定、`reviewer ≠ author`、grill 正文、三条 stage 门
  全部成立）会让一个**零新证据**的纯代码 PR 变绿

### Scenario: 复制后**改路径 / 改一个字节 / 删一个文件 / 混源**也 SHALL NOT 授予
- **Given** 同上的复制构造，但攻击者额外做下列**任一**改动：
  ① 把某个证据文件**改名或改后缀**（如 `reviews/grill-review.md` → `.txt`）；
  ② 把 `specs/` 目录换成同名普通文件；
  ③ 给某个证据文件**加一个字节**，随后用 `manifest build` **重算** manifest 哈希；
  ④ **删**掉 `specs/` 里的一个文件，随后重算哈希；
  ⑤ 报告取自 base 的 change `a`、`tasks.md` + `specs` 取自 change `b`；
  ⑥ 同时 `git mv` 一个**非证据文件**（如 `notes.md`）进新目录，其余整份 `cp`；
  ⑦ 把三份报告**挪出 `reviews/`**（放 change 目录根），再用 manifest 的 `report_path` 指过去；
  ⑧ 把 `specs` 换成**同名普通文件**、或把 `tasks.md` 做成**目录**，把借用内容塞进去
- **When** 运行 `check`
- **Then** 退出码非 0（判据 5 逐文件成立性都被破坏：总有一个文件既不新、也不是本次搬来的）
- ⚠️ 判据 5 SHALL NOT 依赖「路径」或「哈希是否被重算」——`manifest build` 会从磁盘重算哈希
  （`src/witnessloop/manifestcmd.py:146-153`），因此**哈希绑定本身不足以**拦住这些改动

### Scenario: 源是**嵌套**归档目录时同样不授予
- **Given** 基准树里有 `openspec/changes/archive/2026/10-15-old/`（件齐、报告齐）
- **And** 本 PR 把它**整份 `cp`** 成扁平的新目录 `openspec/changes/archive/2026-10-15-new/`，并改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0（判据 5 的扫描面是 `<changes_root>/**` **全量**，不是「扁平 change 目录」）
- ⚠️ 若把扫描面收窄成「扁平 change 目录 + 相对路径匹配」，本形态会漏（R2 的 A3）

### Scenario: 基准 revision 与 diff 成员同源
- **Given** PR 的 base 分支在**分叉点之后**又前进过（`base` ref 的树 ≠ `merge-base` 的树）
- **When** 运行 `check`
- **Then** 到达判定的基准 SHALL 是 `merge-base(base, head)` 的树，与 `changed_files`（`base...head`）**同源**
- **And** 一个「在 `merge-base` 树里不存在、在 `base` ref 树里存在」的归档目录，SHALL 被判为**到达**（与 diff 口径一致）

### Scenario: 归档时顺带**改 change id** ⇒ 当前设计下不授予（**明写的拒绝面**）
- **Given** base 里有 active `openspec/changes/old-id/`（证据齐全）
- **And** 本 PR 执行 `git mv openspec/changes/old-id openspec/changes/archive/2026-10-15-new-id`，并改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0（判据 4 不成立：`2026-10-15-new-id` 既不等于 `old-id`、也不以 `-old-id` 结尾）
- ⚠️ 本条是**拒绝面本身**，取舍见 `design.md §8 Q1`——裁定删守卫则本 Scenario 语义反转

## Requirement: 到达集合的用途 —— 归属、幽灵 id 与保护写豁免 SHALL 共用同一份判定

`check` SHALL 用**同一份**到达集合驱动三件事，SHALL NOT 各自实现一套：

1. **归属**：到达的归档目录进 change 集合（按归档路径校验）；
2. **幽灵 id 的排除**：属于到达组、**且其源 change 目录在 head 树里已不存在**的记录，
   其 **`R`/`C` 记录的 `old_path` 与 `D` 侧记录的 `path`** SHALL 从「active change id」的取值里排除
   ——判据是**目录级**的，SHALL NOT 退回逐文件 `R100`。
   ⚠️ **`D` 侧记录必须一并覆盖**：`gitutil._parse_name_status` 对 `D` 记录把被删路径放在 `path`、`old_path` 留空，
   于是「move 之后把被搬文件**整体重写**」（git 报 `D`+`A`、不配对成改名）会让幽灵 id 回来。
   ⚠️ SHALL NOT 无条件排除到达组里所有 `old_path`：源目录**仍在 head 树里**（= 只搬走了部分文件）
   ⇒ 那个 change SHALL 照旧按 active 契约被校验（不得静默消失）；
   同理，**`D` 记录的 `path` 落在仍在 head 的源目录下时 SHALL NOT 排除**；
3. **保护写豁免**：「该记录属于某个到达组，**且其 `old_path` 落在 `<changes_root>/<active-id>/` 下**（源在
   **active** change 目录里）」⇒ 对受保护文件（`policy.protected_paths` 命中或不变集）的写入
   SHALL 免于「没有结构化解释事件」；SHALL NOT 要求记录状态为 `R100`。
   ⚠️ 旧侧条件 SHALL NOT 丢：只看 `new_path` 落在到达目录下会把「把 `openspec/specs/x.md`
   等受保护文件**移入**到达目录」这条记录也豁免掉——今天它**要**解释事件。

`check` SHALL **不**因上述豁免而放松下列既有要求（回归护栏）：

- 对 **base 里已存在**的归档目录里文件的修改 / 删除 SHALL 仍要解释事件；
- 覆盖（重建）已存在的 `reviews/*.manifest.json` SHALL 仍要解释事件（`M` 一格）；
- 把受保护文件**移入**到达目录 SHALL 仍要解释事件；
- manifest 的 hash / revision 绑定、`reviewer ≠ author`、grill 正文判据 SHALL 逐条照旧。

### Scenario: 到达组内的 `R<100` 记录免解释事件
- **Given** 一次整目录 move，其中 `reviews/building.manifest.json` 在本 diff range 内被重建过（`R069`）
- **When** 运行 `check`
- **Then** 不报该 manifest 的「受保护路径被写入，但没有结构化解释事件」

### Scenario: 到达组外仍然逐条要事件（回归）
- **Given** 本 diff **不含**任何 move，只有一个已归档 change 的 `reviews/grill.manifest.json` 被重建（`M`）
- **When** 运行 `check`
- **Then** 恰好 **1 条**「受保护路径被写入，但没有结构化解释事件」
- **And** 补一条 `protected_path_write` 事件后通过

### Scenario: 把受保护文件搬进到达目录 ⇒ 仍要解释事件
- **Given** 一个到达的归档目录 `archive/<name>/`，本 PR 同时执行
  `git mv openspec/specs/x.md openspec/changes/archive/<name>/x.md`
- **When** 运行 `check`
- **Then** 仍报该记录的「受保护路径被写入，但没有结构化解释事件」（旧侧条件不满足）

### Scenario: 部分搬走的 active change 不得静默消失
- **Given** 一个到达的归档目录 `archive/<name>/`（本次新建、件齐），
  同 diff 里还把**另一个仍在 head 里**的 active change `other` 的某个文件搬进了它
- **When** 运行 `check`
- **Then** `other` SHALL 仍按 **active** 契约被校验（它的目录在 head 里还存在）
- **And** 它 SHALL NOT 因「属于到达组」而被从 change 集合里静默移除

## Requirement: 到达方式 SHALL NOT 改变证据门槛（对称性不变量）

同一个 change 的同一份内容，`check` SHALL 在**证据门槛**维度给出**相同**的判绿判红结论——
不论它放在 `<changes_root>/<id>/` 下还是放在 `<changes_root>/archive/<name>/` 下。
「证据门槛」SHALL 指：必需件、review manifest 的 hash / revision 绑定、`reviewer ≠ author`、
grill 报告正文判据、以及 `code_hits` 触发的 stage 集合。

⚠️ 本不变量 **SHALL NOT** 被读成「两种位置的结论在**任何**维度都相同」：
`policy.stale_exempt_paths` 对 `<changes_root>/archive/**` **整块**豁免，
而对 active change 的 `proposal.md` / `design.md` / `tasks.md` **不**豁免
（同一份 `proposal.md`：active ⇒ 不豁免、archive ⇒ 豁免）。该**非对称是既有口径**，
本 change **不改变**它、也**不宣称**在该维度上对称。

`check` SHALL NOT 为归档 target 引入任何第二套判据、豁免或更松的 stage 集合
（例如「归档态不要求 `grill-adversarial`」这类特判）。

### Scenario: 零证据的归档 change 照样逐条点名（防绕过）
- **Given** 一个**到达**的归档 change（件齐、**零 manifest**）且本次 diff 命中 `require_change_for`
- **When** 运行 `check`
- **Then** 退出码非 0，且 stderr **同时**点名「缺少 review manifest」「无 `stage=grill` 的 manifest」
  「无 `stage=grill-adversarial` 的 manifest」「无 `stage=building` 的 manifest」
- **And** 这些路径指向**归档目录**

### Scenario: 同一内容两种位置结论一致
- **Given** 同一份 change 内容（件齐 + 三份 manifest + 报告），一份在 `changes/<id>/`、一份在 `archive/<name>/`
- **When** 分别运行 `check`
- **Then** 两者的判绿判红结论相同

## Requirement: 既有行为不变（**回归护栏**）

本 change SHALL **不**改变下列既有行为：

- 只改 `require_change_for` 路径而**不建**任何 change 目录的 PR SHALL 照样红；
- **删除** change 目录（非 rename）SHALL 仍报「change 目录不存在」；
- `<changes_root>/archive/**` SHALL 仍然不是法外之地（对该区**已存在**文件的修改 / 删除仍要解释事件）；
- 归档 target 的 `change_id` **别名**（归档目录名 与 源 id）SHALL 照旧；
- `archive` 本身 SHALL **不**被当作 change id；
- `manifest build --change <name>` 对归档目录的支持与 `check` SHALL 继续共用**同一套**契约判定与报告路径解析
  （`contract.validate_change_dir` / `contract.resolve_report_path`）——
  ⚠️ 二者**不**共用「本次 diff 触及哪些 change」的判定：`manifest build` **不调用** `change_targets`，
  它按**磁盘存在性**解析 active 优先、否则 `archive/<name>`（`src/witnessloop/manifestcmd.py:33-48`）；
  本 change SHALL NOT 声称在该处共用，也 SHALL NOT 让 `manifest build` 引入第二套「到达」判据；
- `check` 的退出码语义 SHALL 不变（非 0 = 未通过）。

⚠️ **有意的行为变化（不是回归，须在 `docs/gate.md §6` 记录）**：
「**复制式归档**」（`cp` 一份到 `archive/<date>-<id>/` 而**不**删源目录）在本 change 下 SHALL NOT 被授予资格
（判据 5）。它在改动前**也**不授予（全 `A` ⇒ 无 `R100`），故非回归；
但对采用该流程的接入方是**可感知的**行为（报错文案从「没有任何 change 目录」变为判据 5 的 finding，且点名两侧路径）。

### Scenario: 只改代码、什么都不建 —— 仍然红
- **Given** 一个 PR 只改动 `src/**`，没有新建任何 change 目录、也没有归档到达
- **When** 运行 `check`
- **Then** 退出码非 0，且点名该路径与 `require_change_for`

### Scenario: 删掉 change 目录 ≠ 归档 —— 仍然红
- **Given** base 上有 change `<id>`，本 PR 把 `openspec/changes/<id>/` 整个**删除**（`D`，不是 rename）
- **When** 运行 `check`
- **Then** 报「change 目录不存在」
