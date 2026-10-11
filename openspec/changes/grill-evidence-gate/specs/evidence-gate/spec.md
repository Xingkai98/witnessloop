# evidence-gate — grill 证据的机械判定与本地强制

> 本 change 的能力增量：把「grill 证据算不算齐」抽成**一个**判定，接到 `check`（事后/CI）
> 与新的 `guard` 动词 + CC hook（事前/本地）。

## Requirement: 共享的 grill 证据完备性判定

系统 SHALL 提供一个 host-agnostic 的判定：给定一份 grill 决策记录的**文本**，判断它是否完备。
判据 SHALL 为：

1. `## Confirmed Decisions` 小节内**顶层 bullet（`- ` 开头，含其续行）≥ 3 条**；
2. **每条** bullet **块内**（bullet 行 + 其续行）出现 `来源:`（半/全角冒号均收）；
3. `## Open Questions` 里的**每个** `Q<n>` 在 `## User Confirmation` 有对应 `Q<n>` 的确认记录；
4. 占位文本（如 `待确认` / `待主 agent` 等；**短答复 ≤20 字才查强占位**）**不算**确认。

判定 SHALL 按**块级**而非行级——`来源:` 允许只出现在续行。

### Scenario: 合格的决策记录
- **Given** 一份报告有 3 条以上顶层 bullet、每条块内含 `来源:`，且每个 Open Question 都已在 User Confirmation 被确认
- **When** 运行判定
- **Then** 判为**完备**（无 findings）

### Scenario: 前缀变体都算数
- **Given** bullet 写作 `- **决策（D1）**：…`（「决策」与 `**` 间夹 `（D1）`）
- **When** 运行判定
- **Then** 该 bullet **算**一条（不得因前缀字面不匹配而漏计）

### Scenario: 来源只在续行
- **Given** bullet 首行不含 `来源:`、`来源:` 在其**续行**
- **When** 运行判定
- **Then** 该 bullet **算**带来源（行级口径会漏判）

## Requirement: `check` 校验报告正文

`witnessloop check` SHALL 对每个 change 校验其 **`stage=grill` 的 manifest 所绑定报告**的正文完备性
（用上一条的判据），不合格即 fail-closed 红。

`review manifest` 的 `stage` SHALL 为**必填字段**（非空）；缺 `stage=grill` 的 manifest SHALL 报错，
且错误信息 SHALL 点名**现有** stage 值以便诊断。

### Scenario: 空壳报告被拦
- **Given** 一个 change 的 `grill-review.md` 被 manifest 正确绑定，但正文为空或 `## Confirmed Decisions` 不足 3 条
- **When** 运行 `check`
- **Then** 报错并非零退出

### Scenario: stage 拼错可诊断
- **Given** 用 `--stage grills` 产出的 manifest，仓里没有 `stage=grill` 的 manifest
- **When** 运行 `check`
- **Then** 报错并指出「现有 stage：grills」

## Requirement: 写代码前缺 grill 证据即拦（本地 guard）

系统 SHALL 提供 `witnessloop guard` 动词：给定**写目标路径**，若该路径命中 `policy.require_change_for`
且**当前 change 的 grill 证据不完备**，则拦截（退出码 **1** + 理由），否则放行。
（宿主 hook 负责把 1 映射成该 host 的 block 约定——CC 的 2。**不用 2**：2 是 argparse 用法错误，
旧版 CLI 不认识 `guard` 时会退 2，直传会把每个 `Write|Edit` 都拦下。）

判定「当前 change」SHALL 以**分支名首段**为主、`WITNESSLOOP_CHANGE` 为覆盖；**推得的 id 必须命中一个现存
的 active change 目录**，否则视为「推不出」。

### Scenario: 缺证据写代码被拦
- **Given** 当前分支推得一个现存 change 目录，其 grill 证据不完备
- **When** `guard --path src/x.py`（命中 `require_change_for`）
- **Then** 拦截（exit 1）并给出理由

### Scenario: 写文档不拦（死锁防线）
- **Given** 同一 change 证据尚不完备
- **When** `guard --path openspec/changes/<id>/design.md`（不命中 `require_change_for`）
- **Then** 放行（否则永远产不出证据）

### Scenario: 推得 id 不命中现存目录（fail-open）
- **Given** 分支 `fix/login-timeout`（首段 `fix` 不是任何 active change 目录）
- **When** `guard --path src/auth.py`
- **Then** 放行并提示（**不**拦）
