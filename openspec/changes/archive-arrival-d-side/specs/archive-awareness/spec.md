# archive-awareness — 搬移形状的 `D` finding SHALL 可行动（issue #31）

> 本 change 对 `archive-awareness` 做**一条新增**：**不新增任何豁免面**、**不修改任何既有 Requirement**。
>
> ⚠️ **用户 2026-10-17 裁定 B**：那条掉队的 `D` 记录**照旧要求解释事件**（判定与改动前**逐字相同**）；
> 本 change 只让那条红**可行动**——说清「这可能是搬移的一半」、给出**一行事件**的补救与**可直接复制**的 JSON 示例。
> 成本是**一行事件、同一个 PR**（用户原话：「纯搬移不用写，只有归档时顺手改了被搬文件才需要；仍然一个 change 一个 PR」）。
>
> ⚠️ **留档（为什么不是「发豁免」）**：把那条 `D` 认成「搬移的另一半 ⇒ 免事件」的判据试了四版，
> **每一版都被独立对抗轮造出一条绕过**（G1 / S2 / S8 / P7 / PFIVE / **X1**）；最后一版「覆盖」也不是充分条件
> （把源的每个相对子路径用**全新内容**造齐 + 删源 ⇒ 仍然通过）。⇒ **A 不是没做好，是做不完**（`design.md §3`）。

## Requirement: 搬移形状的 `D` finding SHALL 可行动，且 SHALL NOT 改变判定语义

当一条**受保护路径**的 `D` 记录（`status[:1] == "D"`，被删路径在 `change.path`、`change.old_path` 为空——
见 `gitutil._parse_name_status`）**看起来是一次搬移的一半**时，`check` SHALL 在**该条 finding 的消息里**给出：

1. **判定依据**：同一次 diff 里那条 `A` 的**实际路径**，以及它所在的**到达目录** `A_dir`；
2. **补救**：在**同一个 PR** 内补**一条**解释事件即可（不新增目录、不新增 PR）；
3. **可直接复制的 JSON 示例**——其 `event_type` SHALL 取自**本仓 policy 的允许集**
   （`policy.protected_write_event_types`；**SHALL NOT** 硬编码某个接入方 policy 里的类型名），
   `artifact_path` SHALL 是那条 `D` 的**真实路径**（`events.covers` **不接受通配**）。

「看起来是一次搬移的一半」的判据（**诊断用，不参与判定**）：

- `normalize(change.path)` 形如 `<changes_root>/<id>/<sub>`，`<sub>` **非空**，且**不在** `<changes_root>/archive/**` 下；
- 同一次 diff 里存在一条 `A` 记录，其路径落在**某个到达目录 `A_dir`** 之下（`archive_arrivals` 的判据 1/2/3/5
  一条不放松），且**相对子路径逐字相同**（`normalize(A.path) == f"{A_dir}/{<sub>}"`）。

**判定面（承重）**：

- 该 finding **SHALL 仍然产生**（红照旧、退出码照旧、`path` 字段照旧）；
- 本能力 SHALL NOT 改变**任何**豁免语义：对**任何**输入，`check` 的**退出码**与 **findings 的 path 集合**
  SHALL 与改动前**逐字相同**；唯一允许的差异是**消息正文末尾多一段诊断与示例**；
- 免于解释事件的集合 SHALL 保持为：`R`/`C` 记录的**到达搬移**（`checkcmd._archive_move_exempt` 的既有两条件）。
  **`D` 记录 SHALL NOT 因本能力获得任何豁免**。

⚠️ **诊断是启发式**（如实登记）：一条 `D` 恰好与一条无关的 `A` 同相对子路径时，文案会写「**可能**是」——
它只多一句提示、不改判定；照它补事件补的也是**那个被删路径**的解释，语义上仍然成立。
⚠️ **`protected_write_event_types` 为空**（policy 显式关掉）时 SHALL **不给示例**（只给文字补救）——
避免印出一条 `event_type` 为空的废示例。

### Scenario: 搬移形状 ⇒ 红照旧，但文案给出可用的补救
- **Given** 一次 diff：`<changes_root>/<id>/workflow-events.jsonl` 是 `D`，同一次 diff 里
  `<changes_root>/archive/<name>/workflow-events.jsonl` 是 `A`，且 `archive/<name>/` **是到达目录**
- **When** 跑 `check`
- **Then** 该 finding **仍然存在**（EXIT≠0、`path` = 那条 `D` 的路径）；
  且它的消息里含 `archive/<name>/workflow-events.jsonl`、「同一个 PR」、「一条」以及一个 JSON 示例；
  **把该示例解析出来喂给 `events.covers` SHALL 为真**（示例是**能直接用**的）

### Scenario: 照文案补一行事件之后 ⇒ 绿（同一个 PR）
- **Given** 上一条的 diff，**并且在同一次 diff 里**、在归档后那份 `workflow-events.jsonl` 末尾追加了那条事件
- **When** 跑 `check`
- **Then** `check：通过 ✓`——**没有新增任何 change 目录、没有新增 PR**

### Scenario: 纯搬移不带诊断（也不需要事件）
- **Given** 一次**纯 move**（被搬文件一个字节不改 ⇒ 全部 `R100`；本仓第一次归档实测 58 条全 `R100`）
- **When** 跑 `check`
- **Then** `check：通过 ✓`、**0 条 finding**——纯搬移**不需要**任何事件，也**不**出现诊断

### Scenario: 单独删一个受保护文件 ⇒ 照旧红，且**不**触发诊断
- **Given** 一次 diff 只删 `<changes_root>/<id>/workflow-events.jsonl`（同一次 diff 里**没有**任何到达目录）
- **When** 跑 `check`
- **Then** 该 finding **仍然存在**（与改动前同结论），且消息里**没有**「搬移的一半」那段诊断

### Scenario: 往**已存在**的归档目录搬 ⇒ 照旧红，且**不**触发诊断
- **Given** `archive/<name>/` 在**基准树里已经存在**（不是到达），本次 diff 把某个 active 文件搬进去
- **When** 跑 `check`
- **Then** 照旧红（与改动前同结论）；诊断**不**触发（它不是「到达目录」）

### Scenario: 示例的事件类型跟随 policy
- **Given** 一个 policy 把 `protected_write_event_types` 设为 `["protected_artifact_explained"]`
- **When** 触发上一条诊断
- **Then** 示例里的 `event_type` SHALL 是 `protected_artifact_explained`（**不是**硬编码的某个值）；
  置空时 SHALL 不给示例
