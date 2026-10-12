# event-readpoint — 事件文件读不出时给出**点名文件的结论**（而不是「内部错误」）

> 本 change 的能力增量：把 `workflow-events.jsonl` 的**读失败**（解码 / 权限）归一为**既有错误类型 + 既有出路**，
> 使 `check` 报**一行点名文件**的 finding——而**不是**把仓的问题报成工具故障（`witnessloop：内部错误`）。

## Requirement: 事件文件读不出必须归一为 EventError

`workflow-events.jsonl` 的读取失败（**非法 UTF-8** 解码失败，或权限等 `OSError`）SHALL 被归一为
`witnessloop.events.EventError`（与既有的「不是合法 JSON」**同一错误类型**、**同一出路**）。

错误信息 SHALL **点名该文件**（**文件级**形态，不带 `:lineno`——与既有的**行级**那条在形态上可区分），
并 SHALL 按**成因**区分：**解码失败** ⇒ `无法解码`；**文件读不到** ⇒ `无法读取`（**只钉这两个字面词**，不把措辞绑到别的模块的实现）。

`check` SHALL 因此把它报成 **`事件文件无法解析：…` 那条 finding**（一行、含文件路径），
且 SHALL **不**表现为 `witnessloop：内部错误（…）`。

### Scenario: 非法 UTF-8 的 events 文件 ⇒ 点名文件的结论
- **Given** 一个 **active** change 目录里有 `workflow-events.jsonl`，且其内容是**非法 UTF-8**
- **When** 运行 `check`
- **Then** stderr **含**「事件文件无法解析」**且不含** `witnessloop：内部错误`；退出码非 0
  （⚠️ 这是**可判定**的断言：修复前 `不含「内部错误」` **为假**）

### Scenario: 读不到与解码失败可区分（**events 路径用「目录冒充」造**）
- **Given** 一个**目录**冒充 `workflow-events.jsonl`（`IsADirectoryError`，与 uid 无关；`chmod 000` 在 root 下会假绿）
- **When** 运行 `check`
- **Then** 报错文案点名该文件、并指出是**读不到**（`无法读取`），**不是**误报成「无法解码」或「不是合法 JSON」

⚠️ **该配方只适用于 `events`**：`init`/`uninit` 路径上「目录」会先在**族外**的 `read_bytes` 处失败，
用例会**在声明范围内永远红** ⇒ 那两条路径的「读不出」**必须用非法 UTF-8 造**（见 design §5 / tasks B3）。

### Scenario: 合法事件文件行为不变（回归）
- **Given** 一个合法的 `workflow-events.jsonl`
- **When** 运行 `check`
- **Then** 受保护写入的解释事件照常被认；逐行的 JSON 语法错误仍抛 `EventError`（既有行级文案不变）

### Scenario: 事件读点是**与 diff 无关**的（回归护栏）
- **Given** 某个 active change 目录的 events 文件是坏的，而本次 diff **为空**
- **When** 运行 `check`
- **Then** 仍是上条那条 finding（该读点在 `_protected_writes` 的第一句，**先于**任何 per-change 判断）

## Requirement: 退出码语义不变（**回归护栏，非红先**）

本 change SHALL **不**改变 `check` 的退出码语义：读失败**前后都是「未通过」**——改变的只是**报错形态**
（`witnessloop：内部错误` → 一行点名文件的 finding）。⚠️ 因此本要求**不是先红测试**（退出码今天就已经非 0）。

### Scenario: 读失败前后都是「未通过」
- **Given** 含非法 UTF-8 事件文件的仓
- **When** 运行 `check`
- **Then** 退出码**不是** 0（与修复前一致），只是**不再**表现为 `内部错误`
