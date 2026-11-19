# Proposal: review-loop（多模型复审闭环，T-071）

> 关联任务：T-071（实现） / T-075（真模型复跑与正控）。分支：`feat/review-loop`。
> 一句话：把「双路异构 reviewer 并发审 → 按 `where` 去重取高 severity → fixer 出方案
> → 收敛 / 停滞升级 / 成本止损」做成 `witnessloop review run`，并提供
> `witnessloop review report --md` 读回产物；**与既有门禁判定正交**。

## 背景

`check` / `manifest build` 已经能证明「某次审阅发生过且绑定到哪个 revision」，
但**不负责组织审阅本身**：谁审、用哪个模型、几轮收敛、两路结果怎么合并、
停滞了怎么办、成本怎么止损，都留给操作者。人工做这套流程会出现：

- 单模型自审 ⇒ 独立性不足；
- 两路 reviewer 结论不合并 ⇒ 重复项、severity 口径不一致；
- 无限轮修复 ⇒ 成本和时间不可控；
- 审阅产物散落 ⇒ 无法机械读回、无法做负样本验证。

## 目标

1. **`witnessloop review run`**：一个 change 上跑多轮复审闭环。
   - 两路 reviewer（`reviewerA` / `reviewerB`）并发；
   - 合并规则：只按 `where` 去重，保留 severity 更高的那条；
   - 收敛判据：`pass_rule=medium_plus_zero`（blocker/high/medium 为零）；
   - 停滞升级：同一 `where` 连续 `stall_rounds` 轮重报 ⇒ judge 单点复核；
   - 成本止损：累计近似成本超过 `budget.max_cost_usd` ⇒ 停止；
   - fixer 只产出**修复方案**，不把模型 patch 自动打到代码上。
2. **`witnessloop review report --md`**：读回 `config.resolved.json` + 每轮 manifest，
   生成 Markdown，并跑四条负样本验证（篡改 manifest / 证据缺件 / 两路同一 actor /
   正控漏报），任一命中退出码 1。
3. **roles@v1**：四个角色（`reviewerA` / `reviewerB` / `fixer` / `judge`）的
   adapter / model / base_url / auth 都是配置，不硬编码；key 只经环境变量注入，
   不落盘、不进产物。
4. **回落规则机械执行**：reviewer 通路返回 auth / balance / model_not_found，或
   auth 一开始未解析 ⇒ 当场回落 `deepseek-flash`，manifest 标注 `degraded_from`；
   两路都回落时在 final note 写「本轮为同源双审」。
5. **真实模型验证**：在 `/tmp` 隔离仓上真跑 `glm-5.3`（无降级）与篡改 manifest
   正控，两路 reviewer 都报出注入的缺陷（T-075）。

## 非目标（本 change 明确不做）

- **不改门禁判定**：`check` / `contract` / `evidence` / `checkcmd` 一行不动；
  review loop 是「产出证据」一侧的新动词，不是第二套门禁。
- **不自动改代码**：fixer 只给方案；把任意模型 patch 自动落到工作树是安全边界之外。
- **不把 `.reviewloop/` 直接当门禁证据**：`check` 认的是
  `openspec/changes/<id>/reviews/*.manifest.json`；闭环跑完仍需 `manifest build`。
- **不做 per-change / per-stage 的 roles 路由**：当前 roles 是仓根一份全局配置；
  grill / grill-adversarial 由 host plugin 执行，不走本 CLI 的 adapters。
- **不签名、不防伪造**：run id 与 manifest 字段是自由文本，机械门禁防漂移不防蓄意伪造。
- **不引入状态机 / 数据库**：产物就是 JSON + Markdown，`.reviewloop/` 可随时删除重跑。

## 行为变更 / 受影响调用方

- 新增子命令 `review run` / `review report`；既有动词面与退出码不变
  （`test_cli.py` 的动词面断言更新为含 `review`）。
- 新增可选文件 `reviewloop.roles.json`（仓根）；不存在时用出厂默认角色表。
- 新增本地产物目录 `.reviewloop/`（已加入 `.gitignore`）；它不在受保护路径内，
  写盘不触发 `protected_path_write` 事件。
- 新增近似价格表项 `gpt-6.1-sol`（in $5 / out $30 per 1M tokens，按同代 Sol 档
  保守估算；仅用于预算止损与报告，不是计费依据）。

## 验收

- `uv run pytest -q` 全绿（原 788 + 新增 44；本轮再加 `gpt-6.1-sol` 价格回归测试）。
- `review run` 在 mock 场景 2 轮收敛；在 `/tmp` 真跑 glm-5.3 无降级、正控被两路报出。
- `review report --md` 四条负样本全红、正常产物读回绿。
- 本 change 的三份 stage manifest（grill / grill-adversarial / building）绑定最终内容
  revision，`check --base origin/main --head HEAD` 绿。
- PR 正文记录实测口径；**不自行合并 main**。

## 流程说明（如实）

本功能的实现提交（`8cc7ddd` … `99f910a`）先于本 change 目录落地。本轮补齐的
proposal / design / tasks / spec 与 grill / grill-adversarial / building 证据是
**复盘式**产物：它们绑定当前 revision、如实描述已实现的行为，**不声称**这些审阅
发生在实现之前。此偏差记录在 `tasks.md` 的「流程偏差」节。
