# archive-awareness — 归档 change 的到达判定改为「目录级」

> 本 change 修改 `archive-awareness` 的两条 Requirement：
> 把「本次 diff 里到达了一个归档 change」的判据，从**逐文件 `R100` 改名**换成
> **`archive/<name>/` 在 base 里不存在、在 head 里存在**。
> 到达方式（`git mv` 过来 / 直接新建在 `archive/` 下）**不设限**；
> 到达的 target 走与 active change **完全同一套**契约与证据校验（**到达方式不改变证据门槛**）。
> ⚠️ 已知**会被反转**的旧条款：`archive-awareness` 的否定面 N2（「新建 `archive/<name>/**`（`A`、无 active 源）⇒ 不授予」）
> 与 N7（「同一 diff 里既归档又改写被 move 的文件 ⇒ 不授予」）。反转理由见
> `design.md §1.5`：这两条**不承重**（`archive/**` 的 stale 暗房今天就已存在）；
> 真正承重的「不得给 `base` 里已存在的归档目录授予资格」被 D3 **升级**保留。

## Requirement: 归档 change 的「到达」判定 SHALL 基于目录是否新增，SHALL NOT 基于逐文件改名分

`check` SHALL 把 `archive/<name>/` 认作「本次 diff 里到达的 change」，当且仅当**同时**满足：

1. 该目录在 **base** revision 的树里**不存在**（`<changes_root>/archive/<name>/` 前缀下没有任何 tree entry）；
2. 该目录在 **head** revision 的树里**存在**。

`check` SHALL NOT 依据 `git diff --find-renames` 给出的**逐文件状态**（`A` / `R<分数>`）或**相似度分数**
来判定到达资格。特别是：SHALL NOT 要求 `status == "R100"`，SHALL NOT 因为「某个被移动文件在同一 diff range 内
另有内容改动」而收回资格。

该 change 的 **id SHALL 是归档目录名**（不解析日期前缀）；其契约与证据校验 SHALL 与 active change 同一套
（必需件、review manifest 的 hash/revision 绑定、grill 报告正文、`code_hits` 触发的
`building` / `grill-adversarial` 两条硬门）。

### Scenario: 出生即归档（base 里无此 change，head 里全新增）
- **Given** diff 的 base 里**没有** `openspec/changes/<id>/`
- **And** head 里有 `openspec/changes/archive/2026-10-15-<id>/`（该目录下所有文件状态为 `A`）
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

### Scenario: 名识别守卫对**有源**的到达继续生效
- **Given** 一个**新建**的归档目录 `archive/misc/`，内容整体来自 active change `z`
- **When** 运行 `check`
- **Then** `misc` **不**被授予资格、不进 change 集合 ⇒ `_require_change` 照样命中
- ⚠️ 出生即归档这一路**没有源**可核对，该守卫在它上面无从生效（本 change 已接受的反转）

### Scenario: 基树不可读 ⇒ fail-closed
- **Given** 无法解析 base revision 的树（例如浅克隆）
- **When** 运行 `check`
- **Then** 退出码非 0，且报出**点名 base revision** 的 finding
- **And** **不授予**任何归档到达资格（不得静默按「已到达」或「未到达」之一放行）

## Requirement: 只有「base 里不存在」的归档目录才授予资格（**保留承重守卫**）

「该 change 出现在本次 diff 里」这一资格的取得，SHALL 满足上一条的两条判据；
且 `check` SHALL NOT 因下列动作而认为任何 change 出现在本次 diff：

- **修改 / 删除** `<changes_root>/archive/<name>/**` 里**已存在**的文件（目录在 base 里存在 ⇒ 判据 1 不成立）；
- 往一个**已存在**的归档目录里**新增**文件（同上）；
- 把 active change 的**单个文件**移入一个**已存在**的归档目录
  （如 `git mv changes/z/notes.md → changes/archive/y/notes.md`）——目标目录在 base 里存在 ⇒ 不授予，
  源 change `z` 不得因此**静默逃检**；
- **删除** change 目录（非 rename）；
- 把非 change 目录（如受保护 spec）搬进 `archive/`。

### Scenario: 触碰已存在的归档目录不授予资格（`M` / `A` 两种造法）
- **Given** base 里已存在 `archive/2026-09-30-old/`
- **When** 本 PR **修改**该目录里一个文件（`M`）、或往它里面**新增**一个文件（`A`），并改动 `src/**`
- **Then** 该目录**不**进 change 集合 ⇒ 退出码非 0，`_require_change` 命中

### Scenario: 单文件移入既有归档目录 ⇒ 源 change 不得静默逃检
- **Given** base 里已存在归档目录 `archive/y/` 与 active change `z`
- **And** 本 PR 执行 `git mv openspec/changes/z/notes.md openspec/changes/archive/y/notes.md`，并改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0（`y` 不被授予；`z` 也不得因此绕过）

## Requirement: 到达集合的用途 —— 归属、幽灵 id 与保护写豁免 SHALL 共用同一份判定

`check` SHALL 用**同一份**到达集合驱动三件事，SHALL NOT 各自实现一套：

1. **归属**：到达的归档目录进 change 集合（按归档路径校验）；
2. **幽灵 id 的排除**：属于到达组的记录，其 `old_path` SHALL 从「active change id」的取值里排除
   ——判据是**目录级**的，SHALL NOT 退回逐文件 `R100`；
3. **保护写豁免**：「该记录属于某个到达组」⇒ 对受保护文件（`policy.protected_paths` 命中或不变集）
   的写入 SHALL 免于「没有结构化解释事件」；SHALL NOT 要求记录状态为 `R100`。

`check` SHALL **不**因上述豁免而放松下列既有要求（回归护栏）：

- 对 **base 里已存在**的归档目录里文件的修改 / 删除 SHALL 仍要解释事件；
- 覆盖（重建）已存在的 `reviews/*.manifest.json` SHALL 仍要解释事件（`M` 一格）；
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

## Requirement: 到达方式 SHALL NOT 改变证据门槛（对称性不变量）

同一个 change 的同一份内容，`check` SHALL 给出**相同**的判绿判红结论——不论它放在
`<changes_root>/<id>/` 下还是放在 `<changes_root>/archive/<name>/` 下。

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
- `manifest build --change <name>` 对归档目录的支持与 `check` SHALL 共用同一实现；
- `check` 的退出码语义 SHALL 不变（非 0 = 未通过）。

### Scenario: 只改代码、什么都不建 —— 仍然红
- **Given** 一个 PR 只改动 `src/**`，没有新建任何 change 目录、也没有归档到达
- **When** 运行 `check`
- **Then** 退出码非 0，且点名该路径与 `require_change_for`

### Scenario: 删掉 change 目录 ≠ 归档 —— 仍然红
- **Given** base 上有 change `<id>`，本 PR 把 `openspec/changes/<id>/` 整个**删除**（`D`，不是 rename）
- **When** 运行 `check`
- **Then** 报「change 目录不存在」
