# review-loop（增补）— 多模型复审闭环

> 本 change 只新增 `witnessloop review` 子命令组与相关产物；`check` / `contract` /
> `evidence` / `checkcmd` 的判定一行不改。所有要求都可由单测或产物读回机械验证。

## Requirement: `review run` SHALL 组织双路 reviewer 的多轮闭环

`witnessloop review run --change <id>` SHALL：

1. 解析 revision 锚点（git 或 digest），写入每轮 manifest 的 `revision`；
2. 并发调用 `reviewerA` 与 `reviewerB`，同一份 prompt + context；
3. 合并 findings 时**只按 `where` 去重**，保留 severity 更高的那条；没有 `where`
   的 finding SHALL NOT 被丢弃——SHALL 用合成 `where` 保留并参与收敛判定；
4. 在 `pass_rule=medium_plus_zero` 下，blocker/high/medium 为零 ⇒ `PASS`，
   否则 `CHANGES_REQUESTED`；
5. 同一 `where` 连续 `stall_rounds` 轮重报 ⇒ 升级 judge 单点复核；
6. 累计近似成本超过 `budget.max_cost_usd` ⇒ 停止并标 `BLOCKED`；
7. 每轮写一份 `rounds/round-<n>.json`，收尾写 `summary.json`；人可读的
   `report.md` 由 `review report --out` 生成（`review run` 不自动写）。

### Scenario: 两轮收敛
- **Given** mock 场景 round 1 返回 1 条 medium、round 2 返回空
- **When** `review run --max-rounds 3`
- **Then** `rounds=2`、`final_verdict=PASS`
- **And** round 2 的 `findings` 为空、`verdict=PASS`

### Scenario: 停滞升级
- **Given** 同一 `where` 在连续两轮都被两路 reviewer 报出
- **When** `stall_rounds=2`
- **Then** loop SHALL 在第 2 轮后停止，调用 judge 单点复核
- **And** final verdict 取 judge 的裁定（`PASS` / `CHANGES_REQUESTED` / `BLOCKED`）

### Scenario: finding 没有 where
- **Given** 某路 reviewer 报出一条 medium+ finding，但没有 `where` 字段
- **When** 合并 findings
- **Then** 该 finding SHALL 以合成 `where` 保留
- **And** 本轮 SHALL NOT 因 findings 合并后为空而判 `PASS`

### Scenario: 同仓复跑
- **Given** 上一次 `review run` 留下了 `rounds/round-0002.json`
- **When** 再次运行 `review run`（本次只产生 1 轮）
- **Then** 旧的 round 文件 SHALL 被清理
- **And** `review report` SHALL 只读到本次的轮次

### Scenario: 成本止损
- **Given** 累计成本已超过 `budget.max_cost_usd`
- **When** 本轮仍未收敛
- **Then** loop SHALL 停止，`final_verdict=BLOCKED`，note 写明成本止损

### Scenario: reviewer 输出无法解析
- **Given** 某路 reviewer 在回落之后仍返回无法解析的输出（`error_kind=parse`）
- **When** 本轮汇总
- **Then** 本轮 verdict SHALL 为 `BLOCKED`，SHALL NOT 因 findings 为空判 `PASS`
- **And** round manifest 的 note SHALL 点名失败的 role 与错误
- **And** SHALL NOT 继续调用 fixer / judge

## Requirement: 每轮 manifest SHALL 绑定角色与配置

每轮 manifest SHALL 含：

- `schema = witnessloop/review-round@v1`、`round`、`revision`；
- `config_hash`：`config.resolved.json` 的 sha256；
- `actors[]`：每个出场角色的 `{role, adapter, model, run_id}`，回落时额外
  `degraded_from`；
- `findings` / `verdict` / `cost_usd` / `fixer` / `judge` / `note`。

`config.resolved.json` SHALL NOT 含任何 API key；auth 只记录
`auth_resolved: true|false`。

### Scenario: 篡改检测
- **Given** 盘上 `config.resolved.json` 与某轮 manifest 的 `config_hash` 不符
- **When** `review report --md`
- **Then** 报告 SHALL 判「篡改 manifest」并以退出码 1 结束

### Scenario: 两路同一 actor
- **Given** 某轮 reviewerA 与 reviewerB 的 `run_id` 相同
- **When** `review report --md`
- **Then** 报告 SHALL 判「两路同一 actor」并以退出码 1 结束

## Requirement: 通路失败 SHALL 机械回落并留痕

reviewer 的 auth 一开始未解析，或通路返回 `auth` / `balance` /
`model_not_found` / `parse` 时，SHALL 当场回落 `deepseek-flash`：

1. `actors[].degraded_from` SHALL 记录原 model；
2. 回落成功时 SHALL NOT 中断本轮；
3. 两路都回落时，final note SHALL 写「本轮为同源双审」；
4. 连 deepseek key 也不可用时，SHALL 判该 reviewer 失败并使本轮 `BLOCKED`；
   SHALL NOT 用 mock 的零 findings 冒充 `PASS`。显式 `--adapter mock` 的烟测路径
   不受此限。

### Scenario: reviewerB 模型不可用
- **Given** reviewerB 通路返回 `model_not_found`
- **When** 跑一轮
- **Then** reviewerB 的 actor SHALL 是 `deepseek-flash`，且 `degraded_from`
  为原 model
- **And** `review report` 的配置段 SHALL 显示实际模型

### Scenario: 连回落 key 也没有
- **Given** reviewer 的 auth 未解析，且 `WITNESSLOOP_DEEPSEEK_KEY` /
  `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` 都不可用
- **When** 跑一轮（未显式 `--adapter mock`）
- **Then** 本轮 verdict SHALL 为 `BLOCKED`
- **And** manifest note SHALL 说明「拒绝用 mock 冒充审阅」
- **And** SHALL NOT 以零 findings 判 `PASS`

## Requirement: `review report --md` SHALL 跑四条负样本验证

`review report` SHALL 在读回产物时验证：

1. 篡改 manifest（`config_hash` 不符）；
2. 证据缺件（config 缺失 / 无 round / round 读不出）；
3. 两路同一 actor（reviewerA 与 reviewerB 的 `run_id` 相同）；
4. 正控漏报（声明了 `positive_control.where`、`PASS` 收口但从未报出）。
   该匹配是 **`where` 逐字相等**；真模型措辞不定时不可靠，属于已知限制
   （design D9.7），不作为真实模型审阅的默认安全网。

任一命中 ⇒ 退出码 1；全部通过 ⇒ 0。

### Scenario: 正控漏报
- **Given** `config.resolved.json` 含 `positive_control.where=X`，loop 以 `PASS` 收口
- **When** 所有轮的 merged findings 都没有 `where=X`
- **Then** 报告 SHALL 判「正控漏报」并以退出码 1 结束

## Requirement: roles@v1 SHALL 让四个角色独立配置

仓根 `reviewloop.roles.json`（可选）SHALL 支持四个角色
`reviewerA` / `reviewerB` / `fixer` / `judge`，每个角色独立配置
`adapter` / `model` / `base_url` / `auth_env`（或内联 `auth_token`）。

1. 文件不存在 ⇒ SHALL 使用出厂默认角色表；
2. 文件语法坏 ⇒ SHALL 抛显式错误，不静默回落；
3. 角色级覆盖是**整块替换**：未写的字段不会从默认角色逐字段补；
4. `--adapter <name>` SHALL 覆盖所有角色的通路（`mock` 用于无网络链路）。

### Scenario: 用户指定 reviewerA / judge
- **Given** `reviewloop.roles.json` 把 reviewerA 配成 `gpt-6.1-sol`、
  judge 配成 `deepseek-flash`
- **When** `review run`
- **Then** `config.resolved.json` 的 reviewerA.model SHALL 为 `gpt-6.1-sol`，
  judge.model SHALL 为 `deepseek-flash`
- **And** manifest 的 `actors[]` SHALL 与实际调用一致

## Requirement: auth 解析 SHALL 只有一处实现

预检「auth 是否解析」、回落判定与 `build_adapter` 实际取 token SHALL 共用
`adapters.resolve_auth_token`，顺序为 `auth_token` → `auth_env`；只有角色显式
`allow_host_auth_fallback: true` 时才继续尝试 `ANTHROPIC_AUTH_TOKEN` →
`ANTHROPIC_API_KEY`。该开关 SHALL 原样进入 `config.resolved.json`。

### Scenario: key 只住在 ANTHROPIC_AUTH_TOKEN（显式 opt-in）
- **Given** 角色声明 `auth_env=WITNESSLOOP_MISSING_KEY`（未设置）且
  `allow_host_auth_fallback: true`
- **And** 宿主设置了 `ANTHROPIC_AUTH_TOKEN`
- **When** 构造适配器 / 预检 auth
- **Then** 两处 SHALL 都拿到同一个非空 token
- **And** SHALL NOT 出现「预检说有 key、适配器发空 key」的静默失败

### Scenario: 未 opt-in 时不复用宿主 token
- **Given** 角色未声明 `allow_host_auth_fallback`，其 `auth_env` 未设置
- **And** 宿主设置了 `ANTHROPIC_AUTH_TOKEN`
- **When** 构造适配器
- **Then** 适配器 SHALL NOT 使用宿主 token（空 token）

## Requirement: 成本估算 SHALL 对已知模型生效

`cost_usd(model, usage)` SHALL 按 `APPROX_PRICE_PER_MTOK` 计算：

- 已知模型（含 `gpt-6.1-sol`、`glm-5.3`、`deepseek-flash`）SHALL 得到非零成本；
- 未知模型 SHALL 得到 0（这是已知边界：预算止损失效，新增模型必须同步加表）；
- 成本只用于预算止损与报告，SHALL NOT 被描述为账单。

### Scenario: gpt-6.1-sol 计价
- **Given** usage = 1000 input / 500 output tokens
- **When** `cost_usd("gpt-6.1-sol", usage)`
- **Then** 结果 SHALL 等于 `1000/1e6*5.0 + 500/1e6*30.0`

## Requirement: `.reviewloop/` SHALL NOT 被当作门禁证据

review loop 产物 SHALL 落在 `.reviewloop/`，不得写入
`openspec/changes/<id>/reviews/*.manifest.json` 的命名空间；`check` 的证据仍由
`manifest build` 产出。`.reviewloop/` SHALL 被 `.gitignore` 忽略。

### Scenario: 闭环跑完但未 build
- **Given** `review run` 成功产出 `.reviewloop/rounds/*.json`
- **When** `check` 读取 change 目录
- **Then** 若 `reviews/*.manifest.json` 不存在，`check` SHALL 判红（与 review loop
  是否跑过无关）
