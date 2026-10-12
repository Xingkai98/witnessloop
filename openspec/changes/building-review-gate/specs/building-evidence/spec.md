# building-evidence — 实现后独立审阅成为硬门

> 本 change 的能力增量：把「实现后跑独立审阅闭环」从**自觉**变成 `check` 的**机械门**——
> 本次 diff 落了实现 ⇒ 该 change **必须**有一份 `stage=building` 的审阅证据，且它**审在最终 revision 上**。

## Requirement: 落了实现就必须有实现后审阅证据

`witnessloop check` SHALL 在**本次 diff 触及 `policy.require_change_for` 下的路径**（即落了实现）时，
要求被触及的 change 存在一份 **`stage=<building_stage>`**（默认 `building`，`policy.evidence.building_stage`
可覆写）的 review manifest；缺失时 SHALL 报错并非零退出，错误信息 SHALL 点名**现有** stage 值以便诊断。

该要求 SHALL **不**由「tasks.md 是否勾选」触发——勾选是自声明，不勾即可绕过。

### Scenario: 改了代码但没跑 review-loop
- **Given** 本次 diff 改了 `src/**`（命中 `require_change_for`），该 change 只有 grill 证据
- **When** 运行 `check`
- **Then** 报错并非零退出，且点名缺 `stage=building` 的审阅证据

### Scenario: 有实现后审阅证据则通过
- **Given** 同一条件，但该 change 还有一份 `stage=building` 的 manifest 绑定着审阅报告
- **When** 运行 `check`
- **Then** 该条判定通过

### Scenario: 提案期 / 纯文档改动不误伤（单 change 情形）
- **Given** 本次 diff **未**触及 `require_change_for` 下的路径（只改文档或只动 change 目录）
- **When** 运行 `check`
- **Then** **不**要求 building 审阅证据（否则每个 in-flight change 都会被红）

### Scenario: 多 change 同 PR —— 全部 change 都被要求（**刻意的行为**）
- **Given** 本次 diff 既触及 `require_change_for` 下的路径，又触及**另一个** change 目录（该 change 自身无实现）
- **When** 运行 `check`
- **Then** **两个** change **都**被要求 building 审阅证据——本门禁采用「**一个 PR 推进一个 change**」前提：
  要免除就把 change 拆到单独 PR。**不提供** `building_exempt_changes` 之类的豁免名单（豁免名单 = 新的绕过面）。

### Scenario: stage 拼错可诊断
- **Given** 用 `--stage buildings` 产出的 manifest，仓里没有 `stage=building` 的 manifest
- **When** 运行 `check`
- **Then** 报错并指出「现有 stage：buildings」

## Requirement: 审阅必须发生在最终实现之后

上述判定 SHALL 复用既有的 revision 绑定：manifest 的 `head_sha` 与被检 head 之间**只允许**出现证据文件改动。
⇒ **审阅之后再改任何非证据文件**（哪怕只改一行 `src/`）SHALL 判为「审阅的是旧 revision」并非零退出。

### Scenario: 审阅后又改代码 ⇒ stale
- **Given** `stage=building` 的 manifest 记录 `head_sha=H`，且 `H` 之后的提交里改了 `src/`
- **When** 运行 `check`
- **Then** 报「审阅的是旧 revision：… 之后又改动了非证据文件」并非零退出

## Requirement: 不改变写代码前的本地守卫

本能力 SHALL **只**作用于 `check`（事后 / CI）。`guard`（写码前 / 本地）SHALL 仍只要求 grill 证据——
「实现后」的审阅在写码**之前**不可能存在，强加会自锁。

### Scenario: guard 不要求 building 证据
- **Given** 分支推得一个现存 change，其 grill 证据完备但没有任何 building 证据
- **When** `guard --path src/x.py`
- **Then** **放行**（不得要求尚未发生的实现后审阅）

## Requirement: 判定与 grill 那条共用同一实现

「要求存在某 stage 的 manifest」SHALL 由**一处**实现提供，`check` 的 grill 判定与 building 判定
SHALL 共用它——分两份实现必然漂移（本仓已因「两边各写一套」踩过坑）。

该共用 SHALL **不**把 grill 专有的**报告正文**校验泄漏给 building 判定（building **只**要求证据存在——除非 Q1 选乙，那时另加「最终裁定 = PASS」的判据）。

### Scenario: building 不要求 grill 式正文
- **Given** 一份 `stage=building` 的 manifest 绑定着一份普通审阅报告（无 `## Confirmed Decisions` 等小节）
- **When** 运行 `check`
- **Then** building 那条**不得**因缺少 grill 式小节而报错

## 边界声明（**非新增行为**，仅把既有逃生面的后果写清）

`policy.require_change_for` 显式写成 `[]`（或在目标仓里没覆盖其**真实**代码路径）时，
`check` 的**整条代码门禁**——「改代码必须挂 change」（`_require_change`）**与本 change 新增的 building 门禁**——
SHALL 一并**静默失效**（实测：`check` 退 0）。这是**既有**的逃生面，本 change **不**改变它，
但 SHALL 在 `docs/gate.md §2` 与本 spec 显式声明，避免读者以为「机械强制」在这条最省事的配置上仍然成立。
