# archive-awareness — 归档 move 使该 change 重新成为「本次 diff 的 change」

> 本 change 的能力增量：给工具补上「**这个 change 被归档了**」这个表示。
> 归档 move（`git mv <changes_root>/<id>/… → <changes_root>/archive/<name>/…`，R100，且 `<name>` 等于
> 或以 `-<id>` 结尾）把它带走的那个 change **放回本次 diff 的 change 集合**
> （id = 归档目录名，路径落在归档目录下），
> 于是 ①`require_change_for` 不再误报、②`manifest build` 能解析归档目标、③`events` 扫得到归档目录；
> **且不产生**「归档一下就绕过三条证据门禁」的新口子。
> ⚠️ 配套的**顺序约束**见「`manifest build` 支持归档目标」一节：归档后必须**用归档目录名重建** manifest，
> 且每条重建各要一条解释事件。

## Requirement: 归档 move 使该 change 进入本次 diff 的 change 集合

`check` SHALL 把一次**归档 move**（`contract.is_archive_move`，即 R100 纯改名、源在 active、
落点在 `<changes_root>/archive/**`）带走的那个 change 计入本次 diff 的 change 集合。
该 change 的 **id SHALL 是归档目录的名字**（`<changes_root>/archive/<name>/` 的 `<name>`——
**不解析日期前缀**、不回查旧路径），且 SHALL 按**归档路径**走与 active change **同一套**契约与证据校验
（change 目录必需件、review manifest 的 hash/revision 绑定、grill 报告正文、以及 `code_hits` 触发的
`building` / `grill-adversarial` 两条硬门）。

`check` SHALL **不**把 `archive` 本身当作 change id，SHALL **不**再按 active 目录校验那个已经搬走的源目录。

### Scenario: 归档 + 同 PR 改代码 ⇒ 不再误报「没有任何 change 目录」
- **Given** 一个 change `<id>` 在 base 上已是**证据齐备**的 active change
- **And** 本 PR 用一次 R100 `git mv` 把它搬进 `<changes_root>/archive/2026-10-14-<id>/`，并同时改动 `src/**`（命中 `policy.require_change_for`）
- **When** 运行 `check`
- **Then** 不再出现「本次 diff 里没有任何 change 目录」那条 finding
- **And** 该 change 在**归档路径**上被校验（其 manifest 的 hash 与 revision 绑定必须成立）
- **And** 退出码为 0

### Scenario: 归档 + 同 PR 改代码、但归档 change 零证据 ⇒ 四条缺件全点名（**防绕过**）
- **Given** 本 PR 把 change `<id>` 搬进 `archive/2026-10-14-<id>/`（目录里件齐、**零 manifest**），并同时改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0，且 stderr **同时**点名「缺少 review manifest」「无 `stage=grill` 的 manifest」
  「无 `stage=grill-adversarial` 的 manifest」「无 `stage=building` 的 manifest」
- **And** 其中描述这些证据的路径指向**归档目录**（`<changes_root>/archive/2026-10-14-<id>`）
- ⚠️ 这条是**防绕过**的钉子：只让 `_require_change` 闭嘴的实现会让本场景变绿（= 改了 `src/**` 却零 change 证据放行）

## Requirement: 只有真归档 move 才授予该资格（**四个否定面**）

「该 change 出现在本次 diff 里」这一资格的**唯一**取得方式是**归档 move**，且要**同时**满足两条：

1. `is_archive_move` 为真（R100 纯改名、源在 active、落点在 `<changes_root>/archive/**`）；
2. **目标目录名认得源 id**：`<name> == <源id>` 或 `<name>.endswith("-" + <源id>)`
   （`<源id>` = 旧路径里 `changes_root/` 之后的首段；**只做等值 / 后缀比对，不解析日期**）。
   不满足 ⇒ **不授予**（该 move 的两端仍按既有规则排除 ⇒ 集合为空 ⇒ 回落到今天的行为，fail-closed）。

`check` SHALL NOT 因下列动作而认为任何 change 出现在本次 diff：

- **新建** `<changes_root>/archive/<name>/**`（`A` 状态、无 active 源）——伪造的「看起来像归档」；
- **修改 / 删除** `<changes_root>/archive/<name>/**` 里**已存在**的文件；
- 把**受保护 spec** 之类的非 change 目录搬进 `archive/`；
- **把 active change 的单个文件改入一个已存在的归档目录**，而目标目录名**不认得**该源 id
  （如 `git mv changes/z/notes.md → changes/archive/y/notes.md`）——不授予，否则资格会被凭空给 `y`
  而源 change `z` **静默逃检**（本 change 之前的实测形态：该 diff 是 `R100`、`is_archive_move=True`、集合为空）。

⚠️ **残留边界（写明，别假装不存在）**：目标目录名**恰好认得**源 id 的「部分 move」
（如 `git mv changes/y/<单个文件> → changes/archive/2026-10-14-foo-y/<…>`）**仍会**授予资格。
校准：它要真变绿还必须在攻击 HEAD 上**重建**目标 change 的 manifest
（否则 `stray` 判定会因 `src/**` 非证据而报「审阅的是旧 revision」），
而「碰一下 active change + 重建它的 manifest ⇒ 绿」**今天就已经可行**（既有边界，见 `docs/gate.md §7`）
⇒ 与既有边界**同类等价**，本 change 不假装它被这次收紧消除了。

### Scenario: 伪造归档不生效
- **Given** 一个 PR **新建** `<changes_root>/archive/2026-10-14-fake/`（含 proposal/design/tasks/specs，无 active 源），并同时改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0，且报「必须挂 change 的路径…但本次 diff 里没有任何 change 目录」

### Scenario: 触碰已归档的 change 不授予资格
- **Given** 一个 PR 只**修改** `<changes_root>/archive/2026-10-14-<id>/reviews/building-review.md`（`M`）+ 改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0（该 change **不**进集合 ⇒ `_require_change` 命中）
- ⚠️ 否则「碰一下归档目录」会比「什么都不建」更省事，等于把最省事的绕过方式换了个门

### Scenario: 目标目录名不认得源 id 的移动不授予资格
- **Given** base 里已存在归档目录 `archive/y/`，且有一个 active change `z`（只动它的一个文件）
- **And** 本 PR 执行 `git mv openspec/changes/z/notes.md openspec/changes/archive/y/notes.md`，并改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0（`y` **不**被授予资格、也不进集合；`z` 同样不进 ⇒ `_require_change` 命中）
- **And** 不出现「`y` 的 evidence 齐备 ⇒ 放行」这类结果

## Requirement: `manifest build` 支持归档目标

`manifest build --change <name>` SHALL 在 `<changes_root>/<name>` 不存在而 `<changes_root>/archive/<name>` 存在时，
**在该归档目录内**完成与 active 同款的全过程：`--report` 相对**归档目录**解析、
`report_path` 必须落在 `reviews/` 下、`validate_change_dir` 在归档目录上跑、
manifest 写到 `<changes_root>/archive/<name>/reviews/<stage>.manifest.json`，
且其 `hash` 口径与 `check` **共用同一实现**。

`tasks_hash` SHALL 照常由归档目录里的 `tasks.md` 算出——**SHALL NOT 跳过**：
R100 保证归档前后字节相同 ⇒ 同一个值在归档前与归档后**都成立**（没有新口径）；
跳过会引入第二种 manifest 形状（或 `check` 侧的特例）= 漂移面。

`--change` SHALL 仍旧只接受**单段** id（`/`、绝对路径、`..` 一律拒），
SHALL 在两处都找不到时报错、**不写出任何文件**，且 SHALL **不**自动猜测「名字以 `-<id>` 结尾」的归档目录
（可以在报错文案里**提示**候选，但让人显式给出目录名）。

### Scenario: 归档后重建证据并往返
- **Given** change `<id>` 已被 `git mv` 进 `<changes_root>/archive/2026-10-14-<id>/`，且该目录里有 `reviews/building-review.md`
- **When** 运行 `manifest build --change 2026-10-14-<id> --stage building --report reviews/building-review.md`
- **Then** 退出码为 0，manifest 写在**归档目录内**、其 `change_id` 为 `2026-10-14-<id>`（归档目录名）
- **And** 随后运行 `check` 认这份 manifest（hash 绑定在归档目录上成立）

### Scenario: 找不到就不写（回归护栏）
- **Given** active 与 archive 下都没有 `<name>`
- **When** 运行 `manifest build --change <name> …`
- **Then** 退出码非 0、报错点名 `<name>`、**不**写出任何文件

### Scenario: 归档后必须**用归档目录名重建**（顺序不可颠倒）
- **Given** change `gwa` 在归档**前**用 `--change gwa` build 过 manifest（其 `change_id` 字段 = `gwa`）
- **And** 本 PR 把它 `git mv` 进 `<changes_root>/archive/2026-10-14-gwa/`
- **When** 运行 `check`
- **Then** 退出码非 0，且点名「`manifest.change_id='gwa' 与目录不符`」
  （`check` 拿 label 末段比对，归档态是**归档目录名**）
- **And** 改用「先归档 → `manifest build --change 2026-10-14-gwa`」重建之后，同样的 `check` 通过

### Scenario: 重建（覆盖）已存在的 manifest 仍要解释事件（**既有行为，回归护栏**）
- **Given** base 上已有 change 的证据（`reviews/*.manifest.json` 在不变集里）
- **And** 本 PR 在**新的 revision** 上重建那三份 manifest（= 覆盖，working tree 状态 `M`）而未写事件
- **When** 运行 `check`
- **Then** 恰好 3 条「受保护路径被写入，但没有结构化解释事件」（每份各一条）
- **And** 为每份补一条 `protected_path_write` 事件之后通过
- ⚠️ 在**同一个 revision** 上重复 build 是**逐字节幂等**的 ⇒ 不产生 `M`、不吃这条规则（别把幂等读成「重建免事件」）

## Requirement: `events` 扫描覆盖归档目录

`events.load_all` SHALL 同时扫 `<changes_root>/*/<events_file>`（active 一层）与
`<changes_root>/archive/*/<events_file>`（归档一层）；SHALL NOT 递归到任意深度
（`rglob` / `**` 会让任意深度的同名文件也取得豁免权）。

同一 change 的事件在 active 与 archive 各有一份时 SHALL **两份都读、任一条命中即豁免**
（判定是**存在性**的，不做去重）；两份内容不同时并集生效。

### Scenario: 归档 change 的解释事件重新生效
- **Given** 已归档的 change 在 `<changes_root>/archive/2026-10-14-<id>/workflow-events.jsonl` 里有一条
  `event_type=protected_path_write`、`artifact_path` 点名 `openspec/specs/x.md`、`reason`/`approved_by` 非空的事件
- **And** 本 PR 写入 `openspec/specs/x.md`（`policy.protected_paths` 命中）
- **When** 运行 `check`
- **Then** 不再报「受保护路径被写入，但没有结构化解释事件」（修复前**红**）

### Scenario: **再深一层**的同名文件不被读（⚠️ 否定面已订正）
- **Given** 存在 `<changes_root>/archive/<name>/<sub>/workflow-events.jsonl`（比归档 change 目录**深一层**）
- **When** 运行 `check`
- **Then** 它不被当作任何 change 的事件（不提供豁免）
- ⚠️ **不能**拿 `<changes_root>/archive/workflow-events.jsonl`（`archive/` **直接下**）或
  `<changes_root>/archive/notes/workflow-events.jsonl` 当否定面——本仓实测**两者都会被读**：
  前者的 `*` 匹配 `archive`，后者把 `notes` 当成一个「归档 change 目录」。
  这是**既有口径**（active 一层同款，`*` 匹配任何目录名），本 change 不收紧，但文档必须写准。

## Requirement: 既有行为不变（**回归护栏**）

本 change SHALL **不**改变下列既有行为：

- 只改 `src/**` 而**不建**任何 change 目录的 PR SHALL 照样红；
- **删除** change 目录（非 rename）SHALL 仍报「change 目录不存在」；
- `<changes_root>/archive/**` SHALL 仍然不是法外之地：修改 / 删除归档里的
  `reviews/*.manifest.json`、`workflow-events.jsonl` 等受保护文件 SHALL 仍要解释事件
  （`archive/` 上的**纯改名**才免解释）；
- 把受保护 spec 挪进 `archive/` SHALL 仍要解释事件；
- **覆盖（= 重建）** 已存在的 `reviews/*.manifest.json` SHALL 仍要解释事件（`M` 一格，与今天同款）；
- `check` 的退出码语义 SHALL 不变（非 0 = 未通过）。

### Scenario: 只改代码、什么都不建 —— 仍然红
- **Given** 一个 PR 只改动 `src/app.py`（命中 `policy.require_change_for`），没有新建任何 change 目录、也没有归档 move
- **When** 运行 `check`
- **Then** 退出码非 0，且点名 `src/app.py` 与 `require_change_for`

### Scenario: 删掉 change 目录 ≠ 归档 —— 仍然红
- **Given** base 上有 change `<id>`，本 PR 把 `openspec/changes/<id>/` 整个**删除**（`D`，不是 rename）
- **When** 运行 `check`
- **Then** 报「change 目录不存在」

### Scenario: 归档 move 仍免解释事件
- **Given** 一次 R100 `git mv` 把已审的 change 从 active 搬进 `archive/`（其中的 `reviews/*.manifest.json` 在不变集里）
- **When** 运行 `check`
- **Then** 不报「受保护路径被写入」（今天的行为，本 change 保持不变）
