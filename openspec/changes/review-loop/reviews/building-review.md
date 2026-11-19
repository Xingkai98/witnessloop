# review loop 报告

## 配置
- **reviewerA**：adapter=codex model=gpt-6.1-sol base_url=https://heyroute.ai/v1
- **reviewerB**：adapter=claude model=glm-5.3 base_url=https://heyroute.ai
- **fixer**：adapter=claude model=deepseek-flash base_url=https://api.deepseek.com/anthropic
- **judge**：adapter=claude model=deepseek-flash base_url=https://api.deepseek.com/anthropic
- pass_rule=medium_plus_zero
- stall_rounds=2
- budget={'max_cost_usd': 2.0}
- config_hash=1e3371d8cfd73f473208bbd593072e4710a96fa753690282a79af19621a0ff42

## 各轮
### round 1 — verdict=BLOCKED
- actors：reviewerA/codex/gpt-6.1-sol, reviewerB/claude/glm-5.3
- cost_usd=0.2848
- note：达到最大轮数 1 仍未收敛
- [medium] src/witnessloop/review/adapters.py:cost_usd / roles.py:_resolved_role — 角色允许配置任意 model，但价格表之外的模型一律按零成本计算。使用未列入表中的真实付费模型时，所有请求的累计成本都保持为零，--budget 因而完全失去止损作用。这与 B7 所指出的风险相同，目前只是为一个模型补表，并未消除可配置模型路径上的问题。
- [medium] src/witnessloop/review/orchestrator.py:_run_fixer — fixer 只要返回非空且条目合法的 fixes，就会忽略适配器的所有解析错误。例如返回 {"verdict":"FAIL","findings":[],"fixes":[{"where":"x","action":"a"}]} 时，适配器按 B62/D4 正确标记 verdict 非法，但 _run_fixer 会将该错误清除并继续下一轮。这使文档要求的“显式非法 verdict 判 parse 失败”在 fixer 路径上不成立。
- [medium] src/witnessloop/review/orchestrator.py:_call_reviewer（运行期回落分支的预算条件） — 回落前预算检查的口径不一致：初始 auth 缺失分支用 `budget_left <= 0` 拦截（budget 耗尽时不再发付费回落），但运行期失败回落分支用的是 `(budget_left is None or cost <= budget_left)`。失败的首发调用通常成本为 0（auth/连接错误无 usage），当轮入口 `cumulative_cost == budget`（入口检查是严格 `>`）时 budget_left 恰为 0，`0 <= 0` 成立，仍会发起一次付费的 deepseek 回落调用——与 tasks B45/B56「首次请求已超预算时不再发 fallback 请求」的声称矛盾（且与同函数初始分支的行为不一致）。

## 最终判定：BLOCKED
- cumulative_cost_usd=0.285494
