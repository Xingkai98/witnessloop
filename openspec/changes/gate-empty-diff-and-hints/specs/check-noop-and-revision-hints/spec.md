# check-noop-and-revision-hints（增补）— 零变更不假绿；revision 不匹配给可操作提示

> 本 change 修改既有 `check` 能力的两个边角，不改变「有变更时」的任何判定语义。
> 关联 issue：witnessloop **#45**、**#46**。

## Requirement: 零变更区间 SHALL NOT 被判为「通过」

`check` 的 `base...head` 变更集为空时，SHALL：

1. 打印明确的**无操作**语义（含「无变更」与「非通过」），SHALL NOT 打印成功行
   `check：通过 ✓`；
2. 默认返回**非 0** 退出码，且该码 SHALL 可与「真校验失败」的 `EXIT_FAIL(1)` 区分
   （本 change 定为 `EXIT_EMPTY(5)`）；
3. 保留既有摘要子串 `0 个变更文件` 与 `0 个 change 目录`；
4. 在 `--allow-empty` 显式给定时返回 `EXIT_PASS(0)`，且输出 SHALL 写明
   「已按 `--allow-empty` 显式放行」并说明**本次没有校验任何内容**；
5. SHALL NOT 让 `--allow-empty` 改变非空 diff 的任何判定。

未接入（无 policy）与 base 不可解析仍 SHALL 保持既有 fail-closed 行为
（`EXIT_NOT_ONBOARDED(3)` / `EXIT_FAIL(1)`），SHALL NOT 因零变更而放行。

### Scenario: `--base HEAD --head HEAD`（issue #45 的形态）
- **Given** 一个已接入的仓，base 与 head 解析到同一个提交
- **When** 运行 `witnessloop check --base HEAD --head HEAD`
- **Then** 退出码 SHALL 为 `EXIT_EMPTY(5)`（≠ 0）
- **And** stdout/stderr SHALL 含「无变更」与「非通过」
- **And** stdout SHALL NOT 含 `check：通过 ✓`

### Scenario: 显式 `--allow-empty`
- **Given** 同上，但带 `--allow-empty`
- **When** 运行 `check`
- **Then** 退出码 SHALL 为 0
- **And** 输出 SHALL 含 `--allow-empty` 与「显式放行」
- **And** 输出 SHALL NOT 声称本次校验通过（不出现 `check：通过 ✓`）

### Scenario: 非空 diff 不受 `--allow-empty` 影响
- **Given** 一个有变更、但证据不合格的 PR
- **When** 带 `--allow-empty` 运行 `check`
- **Then** 结果 SHALL 与不带该 flag 相同（仍 `EXIT_FAIL(1)`）

## Requirement: revision 不匹配 SHALL 区分「后代」与「旁支 / 不可达」并给命令

manifest 的 `head_sha` 不是本次被检 revision 的祖先时，`check` SHALL 再判一次反向祖先：

1. **证据 revision 是被检 revision 的后代**（`checked_head` 是 `head_sha` 的祖先）⇒
   消息 SHALL 说明「后代」，并 SHALL 给出**至少一条**可执行的检查命令模板：
   `witnessloop check --base <本次 base ref> --head HEAD`；
   若 HEAD 仍早于证据，SHALL 给出 `--head <证据 sha>` 的形式。
2. **旁支 / 不可达**（两向都不是祖先）⇒ 消息 SHALL 说明「旁支 / 不可达」，
   并 SHALL 给出在交付 revision 上重建该阶段证据的可执行模板：
   `witnessloop manifest build --change <change> --stage <stage> --report <report_path> --base <本次 base ref>`，
   以及一条 `witnessloop check` 复核模板。
3. 两种情形都 SHALL 保留既有诊断子串「祖先」，且 SHALL NOT 改变 finding 条数
   （每份不合格 manifest 仍各一条）。

`<change>` SHALL 取该 manifest 所在 change 目录名（active 用 `<id>`，归档用归档目录名）；
`<stage>` / `<report_path>` SHALL 取当前 manifest 的字段（取不到时退回占位符）。
`check` SHALL NOT 自动重建 manifest、SHALL NOT 改写 `head_sha`。

### Scenario: 证据产生在更晚的 revision 上
- **Given** 内容提交 C1，随后又在 C2 落了内容并使用 C2 作为 manifest 的 `head_sha`
- **When** 运行 `witnessloop check --base main --head C1`
- **Then** stderr SHALL 含「后代」与
  `witnessloop check --base main --head HEAD`
- **And** SHALL 含 `witnessloop check --base main --head <C2>`

### Scenario: 证据来自旁支（rebase / 错误分支）
- **Given** manifest 的 `head_sha` 指向一条与交付 HEAD 互不可达的历史
- **When** 运行 `check`
- **Then** stderr SHALL 含「旁支」或「不可达」
- **And** SHALL 含
  `witnessloop manifest build --change <id> --stage <stage> --report <report> --base main`
- **And** SHALL 含一条 `witnessloop check --base main --head HEAD` 复核模板

### Scenario: 既有「审阅的是旧 revision」不被改写
- **Given** `head_sha` 是被检 head 的祖先，但其后落了非证据文件
- **When** 运行 `check`
- **Then** 仍 SHALL 报既有的「审阅的是旧 revision」与文件列表（本 change 不改该分支）
