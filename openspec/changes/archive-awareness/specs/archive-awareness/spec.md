# archive-awareness — 归档 move 使该 change 重新成为「本次 diff 的 change」

> 本 change 的能力增量：给工具补上「**这个 change 被归档了**」这个表示。
> 归档 move（`git mv <changes_root>/<id>/… → <changes_root>/archive/<name>/…`，`R100`，且 `<name>` 等于
> 或以 `-<id>` 结尾）把它带走的那个 change **放回本次 diff 的 change 集合**
> （id = 归档目录名，路径落在归档目录下），
> 于是 ①`require_change_for` 不再误报、②`manifest build` 能解析归档目标、③`events` 扫得到归档目录；
> **且不产生**「归档一下就绕过三条证据门禁」的新口子。
> ⚠️ 推荐时序（`design.md §1.6`，修后实测 `EXIT=0`）：
> **① 内容（实现 + 收尾）→ ② 在 active 态 build 证据（绑 ① 的 revision）→ ③ `git mv` 归档，放最后、纯改名**。

## Requirement: 归档 move 使该 change 进入本次 diff 的 change 集合

`check` SHALL 把一次**归档 move**（`contract.is_archive_move`，即 R100 纯改名、源在 active、
落点在 `<changes_root>/archive/**`）带走的那个 change 计入本次 diff 的 change 集合。
该 change 的 **id SHALL 是归档目录的名字**（`<changes_root>/archive/<name>/` 的 `<name>`——
**不解析日期前缀**、不回查旧路径作为身份），且 SHALL 按**归档路径**走与 active change **同一套**契约与证据校验
（change 目录必需件、review manifest 的 hash/revision 绑定、grill 报告正文、以及 `code_hits` 触发的
`building` / `grill-adversarial` 两条硬门）。

`check` SHALL **不**把 `archive` 本身当作 change id，SHALL **不**再按 active 目录校验那个已经搬走的源目录。

### Scenario: 归档 + 同 PR 改代码 ⇒ 不再误报「没有任何 change 目录」
- **Given** 一个 change `<id>` 在 base 上是**active**（提案态：件齐、尚无 manifest）
- **And** 本 PR 的提交序列是「① 改动 `src/**` → ② 在 **active 态**产出该 change 的 manifest（`head_sha` 绑 ① 的 revision）
  → ③ `git mv` 把它搬进 `<changes_root>/archive/2026-10-14-<id>/`（**纯改名，放最后**）」
- **When** 运行 `check`
- **Then** 不再出现「本次 diff 里没有任何 change 目录」那条 finding
- **And** 该 change 在**归档路径**上被校验（其 manifest 的 hash 与 revision 绑定必须成立）
- **And** 退出码为 0
- ⚠️ **这个 Given 必须写全**：若证据是**归档前**在旧 revision 上产出、而本 PR 又改了 `src/**`，则
  实测为 **3 条**「审阅的是旧 revision」（既有的「先内容、后证据」，`docs/gate.md §3.1`）——那是**既有**规则，
  与本 change 无关，**不得**当成「归档 ⇒ 自动绿」的验收断言

### Scenario: **纯归档 PR 也按同一套规则校验**（uniform —— 用户 2026-10-15 裁定的生效口径）
- **Given** 一个**历史 change** `legacy-x`（三份 manifest 是**归档前**用源 id 产的），
  其 `reviews/grill-review.md` 的 `## Confirmed Decisions` **只有 2 条**（不合规）
- **And** 本 PR **只做归档**：`git mv openspec/changes/legacy-x openspec/changes/archive/2026-10-15-legacy-x`，
  **一行代码都不改**（无 `code_hits`）
- **When** 运行 `check`
- **Then** 退出码非 0，且恰好 **1 项**：`openspec/changes/archive/2026-10-15-legacy-x/reviews/grill-review.md：
  `## Confirmed Decisions` 只有 2 条，少于硬门槛 3 条`（本仓实测；别名已吸收 `change_id` 那一类）
- **And** 修复路径是**两跳**：① 在**归档之前**的 diff 里补齐报告 + 重建那份 manifest（各写一条
  `protected_path_write` 事件）；② 归档 move 本身纯改名、放最后
- ⚠️ **不引入**「归档专用」的第二套判据、也**不**给纯归档 PR 开后门（`code-gated` / `contract-only` 已否决，见 `design.md §8`）

### Scenario: 归档 + 同 PR 改代码、但归档 change 零证据 ⇒ 四条缺件全点名（**防绕过**）
- **Given** 本 PR 把 change `<id>` 搬进 `archive/2026-10-14-<id>/`（目录里件齐、**零 manifest**），并同时改动 `src/**`
- **When** 运行 `check`
- **Then** 退出码非 0，且 stderr **同时**点名「缺少 review manifest」「无 `stage=grill` 的 manifest」
  「无 `stage=grill-adversarial` 的 manifest」「无 `stage=building` 的 manifest」
- **And** 其中描述这些证据的路径指向**归档目录**（`<changes_root>/archive/2026-10-14-<id>`）
- ⚠️ 这条是**防绕过**的钉子：只让 `_require_change` 闭嘴的实现会让本场景变绿（= 改了 `src/**` 却零 change 证据放行）

## Requirement: 只有真归档 move 才授予该资格（**五个否定面**）

「该 change 出现在本次 diff 里」这一资格的**唯一**取得方式是**归档 move**，且要**同时**满足两条：

1. `is_archive_move` 为真（R100 纯改名、源在 active、落点在 `<changes_root>/archive/**`）；
2. **目标目录名认得源 id**：`<name> == <源id>` 或 `<name>.endswith("-" + <源id>)`
   （`<源id>` = 旧路径里 `changes_root/` 之后的首段；**只做等值 / 后缀比对，不解析日期**）。
   不满足 ⇒ **不授予**（该 move 的两端仍按既有规则排除 ⇒ 集合为空 ⇒ 回落到今天的行为，fail-closed）。

⚠️ **两种命名都授予**（用户 2026-10-15 裁定 **不收紧**，`design.md §8` Q2）：`archive/<id>` **与**
`archive/<date>-<id>` 都算；本 change **SHALL NOT** 要求归档目录必须命名为 `archive/<id>`
（那会让接入方现有 `<date>-<id>` 目录与 OpenSpec `openspec archive` 自身的约定拿不到授予）。
⇒ 规格里**没有**「必须 `archive/<id>`」这类硬要求；「归档命名要不要统一」是**另立 change/issue** 的事。

`check` SHALL NOT 因下列动作而认为任何 change 出现在本次 diff：

- **新建** `<changes_root>/archive/<name>/**`（`A` 状态、无 active 源）——伪造的「看起来像归档」；
- **修改 / 删除** `<changes_root>/archive/<name>/**` 里**已存在**的文件；
- 把**受保护 spec** 之类的非 change 目录搬进 `archive/`；
- **把 active change 的单个文件改入一个已存在的归档目录**，而目标目录名**不认得**该源 id
  （如 `git mv changes/z/notes.md → changes/archive/y/notes.md`）——否则资格会被凭空给 `y`
  而源 change `z` **静默逃检**；
- **在同一个 diff 里既完成归档 move、又改写被 move 的文件**（含「归档之后、在归档态重建 manifest」）：
  内容一变 git 就不再报 `R100` ⇒ 该 move **不授予**任何资格，**且**被搬走的 active 目录会**以幽灵 id
  回到 change 集合**（`<changes_root>/<源id>：change 目录不存在` + 缺件），解释事件需求也**翻倍**
  （rename 的两半各记一次）。⚠️ **这个形态今天就已经红**（既有行为）⇒ 本 change 不制造它，
  但也**不得**把它写成推荐流程。

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

### Scenario: 同一 diff 里既归档又改写被 move 的文件 ⇒ 红，且报出幽灵 change 目录
- **Given** 一个证据齐备的 active change `<id>`（三份 manifest 在 base 里）
- **And** 本 PR「① `git mv` 归档 → ② 在归档态**重建**三份 manifest（内容变了）」
- **When** 运行 `check`
- **Then** 退出码非 0，且 stderr 含「`<changes_root>/<id>：change 目录不存在`」（幽灵 active id）
- **And** 该 move 不再被当作归档（git 报 `R<100`），**且**每份被改写的 manifest 各产生**两条**
  「受保护路径被写入，但没有结构化解释事件」（新路径 + 旧路径）
- **And** 补写解释事件**消不掉**幽灵 change 目录那几条

## Requirement: 归档态 change 的 `change_id` 接受两个名字（**别名**）

对一个由归档 move 授予的 target（源 id = `S`、归档目录名 = `N`），review manifest 的 `change_id` 字段
SHALL 被接受，当且仅当它等于 `N` **或** `S`。

`manifest build --change X` 产出的**新** manifest SHALL 写 `change_id = <解析出的目录名>`（归档态 = `N`）；
`S` 是**别名**，只为让**归档前**产出的 manifest 在归档之后继续有效——
`check` 与 `manifest build` SHALL 共用**同一个**校验器，别名是它的一个**参数**，**不是**第二套实现。

### Scenario: 归档前产出的 manifest 在归档后仍然有效
- **Given** active change `gwa` 的三份 manifest 由 `--change gwa` 产出（`change_id="gwa"`）并已提交
- **When** 本 PR **只**做 `git mv` 把它搬进 `<changes_root>/archive/2026-10-14-gwa/`（纯 `R100`、**不重建**）
- **Then** `check` 通过（退出码 0）——`gwa` 作为别名被接受
- ⚠️ 没有这条别名时，同一 diff 下**每份** manifest 各报一条「`manifest.change_id='gwa' 与目录不符`」；
  而「用归档目录名重建」这条补救在**同一个 diff** 里会触发上面那条「既归档又改写」的红 ⇒ 别名是必需的，不是洁癖

### Scenario: 归档后产出的 manifest 同样有效
- **Given** change 已被归档到 `<changes_root>/archive/2026-10-14-gwa/`
- **When** 运行 `manifest build --change 2026-10-14-gwa …`
- **Then** 写出的 manifest `change_id = "2026-10-14-gwa"`，`check` 也接受

### Scenario: 别名不是「放开」（回归护栏）
- **Given** 一个归档 target `archive/2026-10-14-gwa/`，其目录里某份 manifest 的 `change_id="other"`
- **When** 运行 `check`
- **Then** 仍报「`manifest.change_id='other' 与目录不符`」（只接受 `2026-10-14-gwa` 与 `gwa`）

## Requirement: 「id → 目录」的映射**以目录为键**（同 id 撞车时两份都校验）

`change_targets` 的结果 SHALL 是**列表**、**以目录为键**；当同一个单段 id 同时来自 active 目录与归档授予时，
`check` SHALL **两个目录都校验**——SHALL NOT 合并、SHALL NOT 覆盖、SHALL NOT 静默丢掉任一份。

### Scenario: 同 id 撞车（构造：同名 move + 新增 active 子文件）
- **Given** base 里同时有 `changes/x`（新）与 `changes/archive/x`（旧）
- **And** 本 PR 做 `git mv changes/x/notes.md → changes/archive/x/notes.md`（`R100`、`name == 源 id` ⇒ 授予 `x`）
  **且**新增 `changes/x/extra.md`（⇒ active id 也是 `x`）
- **When** 运行 `check`
- **Then** **两份目录都被校验**（`openspec/changes/archive/x` 与 `openspec/changes/x` 各自出 finding）
- **And** 不出现「只校验其中一份」的结果（撞车天然 fail-closed：通常至少一份不合契约）

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

### Scenario: 改写已存在的归档 manifest ⇒ 每条一条解释事件（**既有规则，回归护栏**）
- **Given** 归档已在 base（本 diff **不含**那个 move），本 PR 在**新的 revision** 上重建三份归档 manifest（= 覆盖，`M`）
- **When** 运行 `check`
- **Then** 恰好 3 条「受保护路径被写入，但没有结构化解释事件」（每份各一条）
- **And** 为每份补一条 `protected_path_write` 事件之后通过（退出码 0）
- ⚠️ 同一 revision 上重复 build 是**逐字节幂等**的 ⇒ 不产生 `M`（别把幂等读成「重建免事件」）；
  也**不可**把这个改写与那个 move 放进同一个 diff（见上一条 Requirement）

## Requirement: `events` 扫描覆盖归档目录

`events.load_all` SHALL 同时扫 `<changes_root>/*/<events_file>`（active 一层）与
`<changes_root>/archive/*/<events_file>`（归档一层）；SHALL NOT 递归到任意深度
（`rglob` / `**` 会让**再深一层**的同名文件也取得豁免权）。

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
  这是**既有口径**（active 一层同款），本 change 不收紧，但文档必须写准。

## Requirement: 既有行为不变（**回归护栏**）

本 change SHALL **不**改变下列既有行为：

- 只改 `src/**` 而**不建**任何 change 目录的 PR SHALL 照样红；
- **删除** change 目录（非 rename）SHALL 仍报「change 目录不存在」；
- `<changes_root>/archive/**` SHALL 仍然不是法外之地：修改 / 删除归档里的
  `reviews/*.manifest.json`、`workflow-events.jsonl` 等受保护文件 SHALL 仍要解释事件
  （`archive/` 上的**纯改名**才免解释）；
- **覆盖（= 重建）** 已存在的 `reviews/*.manifest.json` SHALL 仍要解释事件（`M` 一格）；
- 把受保护 spec 挪进 `archive/` SHALL 仍要解释事件；
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
