# Design: review-loop（多模型复审闭环）

> 本文描述 `witnessloop review run` / `review report` 的实现级设计。所有行为均以
> 当前分支代码与 T-071 / T-075 实测为准；未实现的项写进 §9「已知限制」。
> **定位**：review loop 与 `check` 正交——它不改变任何门禁判定，只负责把「审阅过程」
> 组织起来并留下可读回的产物。

## D1 子命令与产物边界

新增 `witnessloop review` 子命令组：

```text
witnessloop review run --change <id> [--mode auto|git|digest]
                       [--base <ref>] [--pass-rule …] [--stall-rounds N]
                       [--budget USD] [--adapter claude|codex|mock]
                       [--max-rounds N] [--positive-control WHERE]
                       [--mock-scenario JSON]

witnessloop review report [--md] [--out FILE]
```

- 产物根：`.reviewloop/`（`constants.REVIEW_OUTPUT_DIR`）。每次 `review run`
  开始时会清掉上一次的 `rounds/round-*.json` 与 `summary.json`——report 读的是
  整个 `rounds/` 目录，旧轮残留会让两次 run 混读（甚至误报「篡改 manifest」）。
  - `config.resolved.json`：展开后的四个角色 + 运行参数；
  - `rounds/round-<n>.json`：每轮 manifest（schema `witnessloop/review-round@v1`）；
  - `summary.json`：最终 verdict、轮数、累计成本（`review run` 收尾写）；
  - `report.md`：人可读报告——由 `review report --out` 生成，**不是** `review run`
    自动写（`REVIEW_REPORT_FILENAME` 只是报告命令的默认文件名常量）。
- **不放 `.witnessloop/`**：那是受保护路径，每写一份 round manifest 都要解释事件；
  `.reviewloop/` 是本地审计产物，与 `.pytest_cache` 同类。
- `DigestRevision` 计算工作树哈希时排除 `.git` 与 `.reviewloop/`，避免「跑审阅
  改变自己的锚」。

## D2 revision 锚点（`review/revision.py`）

两种形态，`--mode auto` 时自动探测：

1. **GitRevision**：`mode=git`，锚 = commit sha；校验该 sha 是本仓提交。
2. **DigestRevision**：`mode=digest`，锚 = 工作树 `sha256_tree`；稳定排序、
   排除 `.git` 与 `.reviewloop/`。
3. 有 `.git` 但没有任何提交 ⇒ 退回 digest，并在产物里如实标注。

锚写入每轮 manifest 的 `revision.{mode,value}`，并参与 run id 的确定性生成。

## D3 roles@v1（`review/roles.py`）

仓根可选文件 `reviewloop.roles.json`：

```json
{
  "schema": "witnessloop/roles@v1",
  "roles": {
    "reviewerA": {"adapter": "codex",  "model": "gpt-6.1-sol", "base_url": "https://heyroute.ai/v1", "auth_env": "WITNESSLOOP_CODEX_KEY"},
    "reviewerB": {"adapter": "claude", "model": "glm-5.3",     "base_url": "https://heyroute.ai",    "auth_env": "WITNESSLOOP_GLM_KEY"},
    "fixer":     {"adapter": "claude", "model": "deepseek-flash", "base_url": "https://api.deepseek.com/anthropic", "auth_env": "WITNESSLOOP_DEEPSEEK_KEY"},
    "judge":     {"adapter": "claude", "model": "deepseek-flash", "base_url": "https://api.deepseek.com/anthropic", "auth_env": "WITNESSLOOP_DEEPSEEK_KEY"}
  }
}
```

- 文件不存在 / 读不出 ⇒ 出厂默认；**语法坏** ⇒ `ValueError`（显式错误，不静默）。
- 已知角色做**字段级合并**：只写 `model` 会保留默认 `adapter` / `base_url` /
  `auth_env`。缺 `adapter` **不得**静默落到 `mock`（`ValueError`）；`adapter` 不在
  `claude`/`codex`/`mock` 内同样在展开时 `ValueError`，不把拼写错误带进工作线程。
- `--adapter <name>` 覆盖**所有**角色的通路（`mock` 用于无网络打通链路）。
- auth 只记录「已解析 / 未解析」；key 从不写进 `config.resolved.json`。
  实际调用使用**内存里的运行时角色表**（`runtime_roles`，保留内联 `auth_token`），
  写盘/哈希用脱敏版本；两份表的 adapter/model/base_url/auth_resolved 一致。
- `allow_host_auth_fallback: true` 是可选的宿主兜底开关（`ANTHROPIC_*`）；默认关闭，
  避免把宿主 token 发往角色声明的其它端点。该开关必须原样进 resolved config。
- `config.resolved.json` 的 sha256 写入每轮 manifest 的 `config_hash`。

## D4 adapters（`review/adapters.py`）

统一接口 `run(prompt + context) -> ReviewResult`：

- `claude`：Anthropic Messages API，`POST {base_url}/v1/messages`。
  ⚠️ `base_url` 不能以 `/v1` 结尾（否则会打成 `/v1/v1/messages`，T-075 实测 404）。
- `codex`：OpenAI `chat/completions`，`POST {base_url}/chat/completions`。
- `mock`：确定性、无网络；按 `round` 返回 `scenario` 里的种子 findings。

错误归一成 `AdapterError(kind)`：`auth` / `balance` / `model_not_found` / `other`。
输出解析只接受一个 JSON 对象（允许 fenced），字段 `findings` / `verdict`；
解析不出 ⇒ `error_kind="parse"`，按通路失败处理（先回落；回落仍失败则本轮
`BLOCKED`）。**绝不把空 findings 当成 PASS**。finding 必须是对象且 `severity`
∈ blocker/high/medium/low/nit；解析层做 `strip().lower()` 规范化并**返回规范化值**，
避免 `" HIGH "` 绕过阻塞判定。fixer/judge 的合法输出分别是 `fixes` / `rulings`，
不能被 reviewer 的 `findings` 解析器误判为失败；三者都要求**恰好一个**顶层 JSON
对象（**顶层数组 `[{...}]` 不算**），多对象/数组包裹都是歧义输入，不得只取第一个。
显式给出的 `verdict` 不在三态内（如 `FAIL`）⇒ parse 失败，不静默改写为 `PASS`。

auth 解析只有**一处**：`resolve_auth_token(role)`（`auth_token` → `auth_env`；
只有角色显式 `allow_host_auth_fallback: true` 时才继续尝试 `ANTHROPIC_AUTH_TOKEN` →
`ANTHROPIC_API_KEY`），预检、回落判定与 `build_adapter` 共用它，且该开关会被复制进
`config.resolved.json`。否则会出现「预检说 key 在、适配器拿到空串」的静默失败，
或把宿主 token 发往别的端点。

## D5 编排器（`review/orchestrator.py`）

一轮：

1. 两路 reviewer **并发**（`ThreadPoolExecutor(max_workers=2)`），同一份
   `prompt + context`；context = tasks/design/proposal（各截 8000 字符）+
   变更文件清单 + diff（**代码/测试路径优先**，上限 120000 字符，超出显式标注），
   或 digest 模式的说明。git 模式下 change 文档用 `git show <revision>:<path>`
   读取——与 diff 同源，不混入工作树未提交修改。早先的 `diff[:20000]` 会被
   docs/change 文档吃满预算，reviewer 看不到 `src/**`，会把「没看到代码」误报成
   「代码不存在」。
2. 合并：`_merge_findings` **只按 `where` 去重**，保留 severity 更高的那条；
   没有 `where` 的 finding **不丢弃**——用合成 `where`（`<missing-where>:batch…`）
   保留，继续参与收敛判定并出现在报告里。否则模型漏写定位的真实 medium+ 会被
   静默丢成 PASS。
3. verdict：`medium_plus_zero` 判据下，blocker/high/medium 为零 ⇒ `PASS`，
   否则 `CHANGES_REQUESTED`。**任一 reviewer 在回落之后仍有 `error`**（含
   `parse`）⇒ `BLOCKED`，本轮立即停止；空 findings 不会被判成收敛。
   reviewer 自己的 `verdict` 也参与判定：`BLOCKED` ⇒ 整轮 `BLOCKED`；
   `CHANGES_REQUESTED` 但没给 medium+ findings ⇒ 合成 medium，不静默 `PASS`
   （即使另一路已有 findings 也保留这条异常意见）。
   停止分支（预算 / fixer 失败 / judge）必须同步 round manifest 的 `verdict`，
   不能 summary 说 `BLOCKED`、round 仍写 `CHANGES_REQUESTED`。
4. 分支：
   - `PASS` ⇒ 收口，`final_verdict=PASS`；
   - 停滞（同一 `where` 连续 `stall_rounds` 轮）⇒ 升级 judge，单点复核。
     judge 的 `PASS` 必须逐条覆盖送审的 stalled 项且每项为 `false-positive`；
     只拿到 `verdict` 字段不足以放行。同轮还有未送审的 medium+ 时，judge 的
     `PASS` 也不能覆盖它们（最终 `BLOCKED`）。
   - 累计成本 > budget ⇒ `BLOCKED`（成本止损）；
   - 否则跑 fixer，记录修复方案，进入下一轮；`fixes` 必须是对象数组且每条含
     `where`/`action`。**fixer 失败（缺数组/空/条目非法）⇒ 本轮直接 `BLOCKED`
     停止**，不进入下一轮让空 findings 收口。
5. 每轮落一份 manifest：`revision` / `config_hash` / `actors[]` /
   `findings` / `verdict` / `cost_usd` / `fixer` / `judge` / `note`。
6. `actors[]` 含 `{role, adapter, model, run_id, degraded_from?}`；run id 是
   `role-adapter-revision[:12]` 的确定性字符串（防漂移，不防伪造）。

## D6 回落规则（机械执行，不静默）

- reviewer 的 auth 一开始未解析 ⇒ 直接回落 `deepseek-flash`，不白打一次网络。
- 通路返回 `auth` / `balance` / `model_not_found` / `parse` / `other`（含 5xx /
  超时 / 响应结构非法）⇒ 当场回落 `deepseek-flash`。
- 回落成功：`actors[].degraded_from = 原 model`，manifest / report 可见。
- 回落 key 只认 `WITNESSLOOP_DEEPSEEK_KEY`；**不**默认复用宿主 `ANTHROPIC_*`
  token（避免把宿主凭据发往 `api.deepseek.com`）。
- 连 deepseek key 也没有 ⇒ **不再用 mock 冒充审阅**：该 reviewer 记
  `error_kind=auth`，整轮按 reviewer 失败 `BLOCKED`。显式 `--adapter mock` 的
  无网络烟测路径不受影响（那条路不会进入回落分支）。
- 两路都回落到 deepseek-flash ⇒ `final.degraded_note = 本轮为同源双审`；
  两路都降到 mock ⇒ 写「本轮存在 mock 降级（不代表真实双审）」。`summary.json`
  与 `review report` 的 Markdown 都显示它（不能只留在 JSON 里）。
- `--adapter mock` 时不回落（本来就是 mock）。

## D7 报告与负样本（`review/report.py`）

`review report --md` 读 `config.resolved.json` + `rounds/*.json` + 可选 `summary.json`，
生成 Markdown，并跑四条机械验证：

1. **篡改 manifest**：某轮 `config_hash` ≠ 盘上 config 的 sha256；
2. **证据缺件**：config 缺失 / 没有任何 round / 某轮读不出；
3. **两路同一 actor**：同一轮 reviewerA 与 reviewerB 的 `run_id` 相同；
4. **正控漏报**：config 声明 `positive_control.where`、loop 以 `PASS` 收口，
   但该 `where` 从未出现在任何一轮 merged findings 里。⚠️ 这是**逐字相等**匹配；
   真模型措辞不定，T-075 因此没有使用 `--positive-control`（见 D9.7）。

任一命中 ⇒ 退出码 1；全部通过 ⇒ 0。报告本身只渲染事实，不改判定。
额外的结构校验：每轮必须恰有 `reviewerA` / `reviewerB` 各一个且 `run_id` 非空不同；
`config.roles` 的每个值必须是 JSON 对象；`summary.json` **必须存在且可解析**，
其 `rounds` 必须是数组，且与磁盘 `rounds/` 文件集合一致（少一轮不能验证通过）。
损坏的产物要受控判红，不能让渲染崩溃。

## D8 成本模型

- `cost_usd(model, usage)`：`input_tokens/1e6 * in_price + output_tokens/1e6 * out_price`。
- `APPROX_PRICE_PER_MTOK` 是**近似价**，只用于 `budget.max_cost_usd` 止损与报告。
- `--budget` 必须是**有限非负数**；nan/inf/负数会让比较恒假，直接 `EXIT_USAGE`。
- 默认预算 `$30`；未收敛时，在**发起 judge / fixer 之前**检查累计值，超出即停止；
  并在**每轮入口**再检查一次，fixer 推过预算后不再发起下一轮 reviewer 调用；
  reviewer 内部回落前也看剩余预算，首次请求已超预算时不再发 fallback 请求；
  「auth 一开始缺 key」的回落分支同样受这条预算检查约束。
  ⚠️ 两路 reviewer 并发，各自拿到轮次开始时的剩余预算快照；极端情况下两路各发起
  一次 fallback 仍可能合计越过上限一个调用。这是软止损的**已知并发边界**，不做
  共享额度预留。
  这是**软止损**：单次调用本身可能把累计值推过上限（不做事前额度预留），但不会
  在已超预算后继续发起额外调用。
- 每轮 manifest 的 `cost_usd` = **两路 reviewer** 成本；fixer / judge 成本计入
  `summary.cumulative_cost_usd`，不单独落盘。
- 未知模型名 ⇒ 价格 `(0, 0)` ⇒ 成本恒 0、预算止损失效。**新增模型必须同步加表**
  （本 change 为 `gpt-6.1-sol` 加了 $5/$30 的保守估算）。

## D9 已知限制（如实）

1. **judge 上下文不足**：`_run_judge` 只把 `where` 字符串交给 judge，不给 finding
   原文 / diff。T-075 实测两次都判 `uncertain` ⇒ `BLOCKED`。属既知设计限制。
2. **fixer 不自动改代码**：只产出 `fixes` JSON；安全边界。
3. **`.reviewloop/` 不是门禁证据**：`check` 只认 `reviews/*.manifest.json`；
   闭环跑完仍需 `manifest build`。
4. **roles 是仓根全局**：没有 per-change / per-stage 路由；grill / grill-adversarial
   由 host plugin 执行，不走本 CLI 的 adapters。
5. **成本不是计费依据**：价格表是硬编码近似；未知模型不追踪。
6. **不防伪造**：run id / manifest 字段是自由文本，机械门禁防漂移不防蓄意伪造。
   本 CLI 的 `_actor_run_id` 带角色前缀（`reviewerA-…` / `reviewerB-…`），所以两路
   run id **结构性不同**；`review report` 的「两路同一 actor」负样本是**产物级**
   篡改检查（手工把 manifest 两个 run id 改成相同才会触发），**不是**对真实独立
   run 的证明。真实同源双审由 `degraded_note` / `degraded_from` 记录。
7. **`--positive-control` 只做 `where` 逐字相等匹配**：真模型措辞不定，容易误报
   「正控漏报」；T-075 因此改用人工核对 finding 原文。该机制保留给 mock/确定性
   场景，不作为真实模型审阅的默认安全网。
8. **digest 模式看不到 diff**：无 `.git` 时 context 只有 change 文档 + 工作树文件
   清单，并在 prompt 里明确告知「不要因为看不到代码就报代码不存在」。要审实现必须
   用 git 模式；digest 模式只保证链路与文档审阅可跑。

## D10 验收与证据

- 单测：revision / roles / adapters / orchestrator / report / CLI 动词面，共 44 条新增。
- 真跑：T-075 clean（glm-5.3 无降级，3 轮 $0.0451）+ tamper 正控（两路报出，2 轮 $0.0364）。
- 本 change 三份 stage manifest 绑定最终内容 revision；`check` 绿。
- 每轮 manifest 与 `config.resolved.json` 的哈希绑定可被 `review report` 读回验证。
