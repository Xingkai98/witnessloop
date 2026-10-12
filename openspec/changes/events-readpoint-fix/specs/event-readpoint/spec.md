# event-readpoint — 事件文件读不出时给出**确定性结论**（而不是崩溃）

> 本 change 的能力增量：把 `workflow-events.jsonl` 的**读失败**（解码 / 权限）从**未捕获异常（崩溃）**
> 归一为**既有错误类型 + 既有出路**，使 `check` 报一行可诊断的 finding。

## Requirement: 事件文件读不出必须归一为 EventError

`workflow-events.jsonl` 的读取失败（**非法 UTF-8** 解码失败，或权限等 `OSError`）SHALL 被归一为
`witnessloop.events.EventError`（与既有的「不是合法 JSON」**同一错误类型**），
错误信息 SHALL **点名该文件**、并 SHALL 按**成因**区分（解码失败 ≠ 文件读不到）。

`check` SHALL 因此把它报成**一行可诊断的 finding**（`事件文件无法解析：…`）并以**未通过**的退出码结束——
SHALL **不**出现未捕获异常的栈回溯。

### Scenario: 非法 UTF-8 的 events 文件不崩
- **Given** 一个 change 目录里有 `workflow-events.jsonl`，且其内容是**非法 UTF-8**
- **When** 运行 `check`
- **Then** 非零退出，stderr 是「事件文件无法解析」那条 finding，且**不含** `Traceback`

### Scenario: 权限问题与解码失败可区分
- **Given** 事件文件**读不到**（如权限不足）
- **When** 运行 `check`
- **Then** 报错文案点名该文件、并指出是**读不到**（而不是误报成「解码失败」或「不是合法 JSON」）

### Scenario: 合法事件文件行为不变（回归）
- **Given** 一个合法的 `workflow-events.jsonl`
- **When** 运行 `check`
- **Then** 受保护写入的解释事件照常被认（既有行为不变）；逐行的 JSON 语法错误仍抛 `EventError`

## Requirement: 退出码语义不变

本 change SHALL **不**改变 `check` 的退出码语义：读失败前后**都**是「未通过」——
改变的只是**报错形态**（未捕获崩溃 → 干净的 finding）。

### Scenario: 读失败前后都是「未通过」
- **Given** 含非法 UTF-8 事件文件的仓
- **When** 运行 `check`
- **Then** 退出码**不是** 0（与修复前一致），只是不再有栈回溯
