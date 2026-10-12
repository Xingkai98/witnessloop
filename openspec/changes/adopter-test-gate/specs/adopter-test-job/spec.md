# adopter-test-job — 接入方的测试进 CI 并拦住合并

> 本 change 的能力增量：`init` 接入的门禁**能跑接入方自己声明的测试命令**，且它**真的能拦住合并**
> （而不是「跑了但没人管」）。同时把「命令从哪来、空命令怎么办、required 怎么勾」写成对外契约。

## Requirement: 门禁可跑接入方声明的测试命令

`init` 生成的 caller workflow SHALL 能把接入方声明的**测试命令**传给 reusable workflow；
reusable workflow SHALL 在**非空**时执行它。

测试命令 SHALL **由接入方显式声明**（caller 的 `with:` 参数，`init --test-command` 是便利入口）；
SHALL NOT 由工具**探测**猜测（猜错会静默跑错东西）。

### Scenario: 给了命令就执行
- **Given** caller 里带 `with: test-command: <cmd>`
- **When** 该仓的 PR 触发门禁
- **Then** reusable workflow 执行 `<cmd>`；它失败 ⇒ 该 check **不通过**

### Scenario: 命令为空 ⇒ 跳过（不是失败）
- **Given** caller 没有给命令（存量接入方的 caller 就是这种形态）
- **When** 触发门禁
- **Then** **不执行**任何测试命令，且**不因此**失败——存量行为**逐字不变**

### Scenario: 不做探测
- **Given** 一个只写 `pytest` 的仓（没声明命令）
- **When** 触发门禁
- **Then** 工具 SHALL NOT 自行推断并运行 `pytest`（保持「空 = 跳过」）

## Requirement: 测试的通过与否 SHALL 能拦住合并

测试命令的失败 SHALL 反映在**可被 branch protection 设为 required 的 job** 上
（GitHub 的 required check 粒度是 **job**，不是 step）——SHALL NOT 出现「测试跑了、但没人能把它勾成必过」的形态。

> ⚠️ 具体形态（独立 `test` job / 并入既有 `check` job）由本 change 的 Q1 定案后钉死在此，
> 实现开始前 MUST 替换本括注。

### Scenario: 测试失败 ⇒ 合并被拦
- **Given** 接入方给了命令、且它会失败，并已按文档把对应 job 勾成 required
- **When** PR 触发门禁
- **Then** 该 required check 失败 ⇒ 合并被拦

## Requirement: 工具不替接入方执行测试（边界）

`witnessloop check` / `guard` SHALL NOT 执行接入方的测试命令——
它们只判**流程证据**；跑测试是 CI 侧 job 的职责。本地跑测试 SHALL 仍是接入方自己的事。

### Scenario: 本地 check 不跑测试
- **Given** policy 与 caller 里都声明了测试命令
- **When** 本地运行 `witnessloop check`
- **Then** SHALL NOT 执行任何测试命令（`check` 的语义与耗时不被改变）

## Requirement: 命令的传递方式 SHALL 避免脚本注入

reusable workflow SHALL 把命令经 **`env:`** 传给 step，SHALL NOT 将 caller 提供的值**裸内联**进
`run:` 脚本（GitHub 官方建议的写法）。

### Scenario: 结构断言
- **Given** `gate.yml` 的测试步骤
- **When** 用 YAML 解析断言（不是 grep 子串）
- **Then** 命令出现在 `env:` 里；`run:` 中不出现裸 `${{ inputs.test-command }}`

## Requirement: 对既有接入方**默认无行为变更**

触发面只在 caller **显式**给出命令时生效；未给命令的仓 SHALL 与改动前**逐字同行为**。
若本 change 同时改变了 reusable workflow 的 ref 策略，SHALL 保持「默认无变更」这一前提
（否则就是**静默行为变更**，必须在 README 显式声明）。

### Scenario: 存量接入方升级后行为不变
- **Given** 一个已接入的仓（caller 里没有命令）
- **When** 门禁跑在升级后的 reusable workflow 上
- **Then** 仍只跑 `check`；测试相关步骤被跳过

## 边界声明（必须写进文档）

1. **测试命令是任意代码**，会在**每个 PR**（含 **fork PR**）的 runner 上执行。这是「跑 CI」的常态，
   但接入方应知道；如需「fork PR 先批准」，那是**仓级设置**，本工具不替其决定。
2. **required 是人工勾一次的操作**：与 `check` 一样，工具无法验证平台侧配置；
   文档 SHALL 写明该步骤与「忘勾的后果」。
3. **命令的改动会影响台账**：caller 是 `init` 写并记账的文件，改它会让 `init` 报冲突（fail-closed）。
