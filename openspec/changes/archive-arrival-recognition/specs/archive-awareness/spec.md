# archive-awareness — 归档 change 的到达判定改为「目录级」

> 本 change 修改 `archive-awareness` 的四条 Requirement：
> 把「本次 diff 里到达了一个归档 change」的判据，从**逐文件 `R100` 改名**换成
> **`archive/<name>/` 在基准树里不存在、在 head 树里存在且**是一个含必需件的 change 目录****。
> 到达方式（`git mv` 过来 / 直接新建在 `archive/` 下）**不设限**；
> 到达的 target 走与 active change **完全同一套**契约与证据校验（**到达方式不改变证据门槛**）。
> ⚠️ 已知**会被反转**的旧条款：`archive-awareness` 的否定面 N2（「新建 `archive/<name>/**`（`A`、无 active 源）⇒ 不授予」）
> 与 N7（「同一 diff 里既归档又改写被 move 的文件 ⇒ 不授予」）。反转理由见
> `design.md §1.5`：这两条**不承重**（`archive/**` 的 stale 暗房今天就已存在）；
> 真正承重的「不得**白捡**一份现成证据」被 D3（基准树里已存在 ⇒ 不授予）与
> **D1 第 5 条**（内容整份来自仍在的既有 change 目录 ⇒ 不授予）**升级**保留。

## Requirement: 归档 change 的「到达」判定 SHALL 基于目录级事实，SHALL NOT 基于逐文件改名分

`check` SHALL 把 `archive/<name>/` 认作「本次 diff 里到达的 change」，当且仅当**同时**满足：

1. **基准树里该路径完全没有 entry**：在 `M = git merge-base(base, head)` 的树里，
   `<changes_root>/archive/<name>` **既不是 tree 也不是 blob**（该路径下也没有任何 entry）。
   基准树 SHALL 是 **`git merge-base(base, head)` 的树**——与 `gitutil.changed_files`
   （`src/witnessloop/gitutil.py:105`）判定 diff 成员所用的 `base...head` **同源**；
   SHALL NOT 用 `base` ref 自身的树。
   ⚠️ 判据 SHALL **不**表述成「该前缀下没有任何 tree entry」：实测
   `git ls-tree -r <M> -- <path>/`（带尾斜杠）在「base 同路径是一个 blob」时返回 **0 行**，
   会把「base 里已有实体」误判成「不存在」；
2. **head 树里该路径存在、是 tree，且其直接子项里含 ≥1 个 `policy.required_artifacts`**
   （探测 SHALL 用契约门**同一张** `policy.required_artifacts` 表）。
   ⇒ 组织型 / 工具型子目录（`archive/2026/`、`archive/notes/`、`archive/templates/`）
   SHALL NOT 被当作「到达的 change」；
3. **不是从另一个归档目录改名而来**：到达组里**没有**任何记录的 `old_path` 落在
   `<changes_root>/archive/**` 下（否则「把旧归档目录改个名」就能白捡一份现成证据）；
4. **有源时须名识别**：若到达组里存在 `old_path` 落在 `<changes_root>/<src>/` 下（即**有源** `src`），
   则 SHALL 要求 `name == src` 或 `name.endswith("-" + src)`；**无源**（出生即归档）时本条无从施加；
5. **内容不得整份取自 base 树里仍然存在的 change 目录**（**防「整份复制现成证据」**）：
   记 `E(X)` = 目录 X 的「证据指纹」= `(相对路径, blob sha)` 集合，取
   `<X>/tasks.md` + `<X>/specs/**` + `<X>/reviews/**/*.md`
   （= 被 manifest 哈希绑定的 artifact 与被绑定为报告的报告正文；**排除** `reviews/*.manifest.json` 自身）。
   若 base 树里存在一个 change 目录 `D`（active 的 `<changes_root>/<id>/` 或归档的
   `<changes_root>/archive/<name>/`）满足 `E(D) ≠ ∅`、`E(D) ⊆ E(A)`，
   且 **`D` 不是「本次已被搬走的目录」**（D 的路径既不是到达组某条记录的源目录，也**不是**在 head 树里已不存在），
   则 `A` SHALL NOT 被授予资格。
   ⇒ 只改 `reviews/*.manifest.json`、往 A 里新增文件都 SHALL NOT 使判据失效；
   删掉 / 改字节由既有的必需件、哈希绑定与孤儿规则拦下（**判据不宣称防伪造**，
   与 `contract.py` 既有的「防漂移、不防伪造」能力边界一致）。

`check` SHALL NOT 依据 `git diff --find-renames` 给出的**逐文件状态**（`A` / `R<分数>`）或**相似度分数**
来判定到达资格。特别是：SHALL NOT 要求 `status == "R100"`，SHALL NOT 因为「某个被移动文件在同一 diff range 内
另有内容改动」而收回资格，SHALL NOT 依赖 `-M` / `-C` 的**副本检测启发式**（实测 `-M -C` 看不见
「源目录原封不动」的整份复制）。

该 change 的 **id SHALL 是归档目录名**（不解析日期前缀）；其契约与证据校验 SHALL 与 active change 同一套
（必需件、review manifest 的 hash/revision 绑定、grill 报告正文、`code_hits` 触发的
`building` / `grill-adversarial` 两条硬门）。

### Scenario: 出生即归档（base 里无此 change，head 里全新增）
- **Given** diff 的基准树里**没有** `openspec/changes/<id>/`
- **And** head 里有 `openspec/changes/archive/2026-10-15-<id>/`（件齐：`proposal.md` / `design.md` / `tasks.md` / `specs/` / `reviews/`）
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
- **And** 达成的第 5 条判据 SHALL **不**误伤它：base 里的 `openspec/changes/<id>/` 在 head 里已不存在
  （整体搬走）⇒ 它不是「仍然存在的 change 目录」

### Scenario: **整份复制现成证据不授予资格**（防「cp -r」绕过）
- **Given** 基准树里已存在归档目录 `openspec/changes/archive/2026-09-30-old/`（证据齐全，**本 PR 原封不动**）
- **And** 本 PR 把它的**整份内容 `cp`** 到 `openspec/changes/archive/2026-10-15-new/`，
  只改其中的 `reviews/*.manifest.json`（`change_id` / `head_sha`），并改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0（`2026-10-15-new` 虽「在基准树里不存在」、且到达组里没有任何 `old_path`，
  但 `E(2026-09-30-old) ≠ ∅`、`⊆ E(2026-10-15-new)`，且源目录**仍在 head 里** ⇒ 判据 5 不成立）
- **And** stderr 点名 `src/**` 与 `require_change_for`
- ⚠️ 没有判据 5 时，这份**逐字节未变的现成证据**（哈希绑定、`reviewer ≠ author`、grill 正文、三条 stage 门
  全部成立）会让一个**零新证据**的纯代码 PR 变绿

### Scenario: 组织型子目录 SHALL NOT 被当成到达的 change
- **Given** 基准树里没有 `openspec/changes/archive/2026/`
- **And** head 里有 `openspec/changes/archive/2026/10-15-foo/{proposal.md, design.md, tasks.md, specs/, reviews/}`
- **When** 运行 `check`
- **Then** `archive/2026/` **不**被认作到达的 change（其直接子项是 `10-15-foo`，不含任何必需件）
- **And** **不**出现「`archive/2026/` 缺少必需件 `proposal.md`」这类 finding
- **And** 行为与改动前一致：若非嵌套布局的 `archive/<name>/` 不存在，则「没有任何 change 目录」照旧命中

### Scenario: 基准树里同路径是**文件**时不得被误放行
- **Given** 基准树里 `openspec/changes/archive/foo` 是一个 **blob**（文件）
- **And** head 里 `openspec/changes/archive/foo/` 是一个**目录**（含必需件）
- **When** 运行 `check`
- **Then** 判据 1 SHALL 判「基准树里该路径**有** entry」⇒ 不授予（不得因「前缀下没有 tree entry」的措辞漏洞放行）

### Scenario: 基树不可读 ⇒ fail-closed
- **Given** 无法解析基准 revision 的树（例如浅克隆，且 `merge-base` 本身可解析）
- **When** 运行 `check`
- **Then** 退出码非 0，且报出**点名该 revision** 的 finding
- **And** **不授予**任何归档到达资格（不得静默按「已到达」或「未到达」之一放行）

## Requirement: 只有「base 里不存在**且内容不是白捡**」的归档目录才授予资格（**保留承重守卫**）

「该 change 出现在本次 diff 里」这一资格的取得，SHALL 满足上一条的**五条**判据
（其措辞与 `design.md §2 D1` 逐条对齐）；
且 `check` SHALL NOT 因下列动作而认为任何 change 出现在本次 diff：

- **修改 / 删除** `<changes_root>/archive/<name>/**` 里**已存在**的文件（基准树里该路径有 entry ⇒ 判据 1 不成立）；
- 往一个**已存在**的归档目录里**新增**文件（同上）；
- 把 active change 的**单个文件**移入一个**已存在**的归档目录
  （如 `git mv changes/z/notes.md → changes/archive/y/notes.md`）——目标目录在基准树里存在 ⇒ 不授予，
  源 change `z` 不得因此**静默逃检**；
- **删除** change 目录（非 rename）；
- 把非 change 目录（如受保护 spec）搬进 `archive/`；
- **整份复制**一个**仍然存在**的 change 目录（判据 5）；
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

### Scenario: 把已存在的归档目录**改名**不授予资格（防「白捡现成证据」）
- **Given** 基准树里已存在 `openspec/changes/archive/2026-09-30-foo/`（证据齐全）
- **And** 本 PR 只做 `git mv openspec/changes/archive/2026-09-30-foo openspec/changes/archive/2026-10-15-foo`，
  并改动 `src/**`，**没有**产出任何新证据
- **When** 运行 `check`
- **Then** 退出码非 0（判据 3 不成立——到达组里有 `old_path` 落在 `archive/**`）
- **And** 判据 5 通常也同时命中（旧目录的内容指纹 `⊆` 新目录，且旧目录仍按新名存在于 head）
- ⚠️ 没有这两条判据时，这份**三个月前的现成证据**会被复用 ⇒ 一个零新证据、只改了 `src/**` 的 PR 变绿

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
- ⚠️ 本条是**拒绝面本身**，其取舍（是否保留判据 4）见 `design.md §8 Q1`——裁定删守卫则本 Scenario 语义反转

## Requirement: 到达集合的用途 —— 归属、幽灵 id 与保护写豁免 SHALL 共用同一份判定

`check` SHALL 用**同一份**到达集合驱动三件事，SHALL NOT 各自实现一套：

1. **归属**：到达的归档目录进 change 集合（按归档路径校验）；
2. **幽灵 id 的排除**：属于到达组、**且其源 change 目录在 head 树里已不存在**的记录，
   其 `old_path` SHALL 从「active change id」的取值里排除——判据是**目录级**的，SHALL NOT 退回逐文件 `R100`。
   ⚠️ SHALL NOT 无条件排除到达组里所有 `old_path`：源目录**仍在 head 树里**（= 只搬走了部分文件）
   ⇒ 那个 change SHALL 照旧按 active 契约被校验（不得静默消失）；
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
- **Then** 仍报该记录的「受保护路径被写入，但没有结构化解释事件」
  （旧侧不在 active change 目录下 ⇒ 不满足豁免的旧侧条件）

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

### Scenario: 只改代码、什么都不建 —— 仍然红
- **Given** 一个 PR 只改动 `src/**`，没有新建任何 change 目录、也没有归档到达
- **When** 运行 `check`
- **Then** 退出码非 0，且点名该路径与 `require_change_for`

### Scenario: 删掉 change 目录 ≠ 归档 —— 仍然红
- **Given** base 上有 change `<id>`，本 PR 把 `openspec/changes/<id>/` 整个**删除**（`D`，不是 rename）
- **When** 运行 `check`
- **Then** 报「change 目录不存在」
