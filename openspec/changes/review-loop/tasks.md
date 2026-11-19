# Tasks: review-loop（多模型复审闭环）

> 依据 `design.md`。实现原则：TDD；证据原则：**先内容、后证据**。
> 本文件属于内容，被每份 manifest 的 `tasks_hash` 绑定——证据提交后再勾选会判 stale，
> 因此交付类步骤（G2/G3/G5/G6）保持 `[ ]`，完成情况以 PR 正文与门禁输出为准。

## A. 立项与实现（T-071）

- [x] A1 `revision.py`：GitRevision / DigestRevision / `mode=auto`，digest 排除
      `.git` 与 `.reviewloop/`。
- [x] A2 `roles.py`：roles@v1 读入、角色级覆盖、`config.resolved.json` 展开、
      auth 只记录「已解析/未解析」、config hash。
- [x] A3 `adapters.py`：`claude` / `codex` / `mock` 三个适配器；错误归一为
      `AdapterError(kind)`；`cost_usd` 近似计价。
- [x] A4 `orchestrator.py`：双路并发审 → 按 `where` 去重取高 severity → fixer 方案 →
      收敛 / 停滞升级 judge / 成本止损；每轮落 manifest。
- [x] A5 `report.py`：`review report --md` 读回产物，跑四条负样本验证。
- [x] A6 `cli.py` 加 `review` 子命令组（`run` / `report`）；动词面测试更新。

## B. 测试（新增 44 条 + 本轮 1 条）

- [x] B1 `tests/test_review_revision.py`（10）：git/digest 锚、排除项、内容变则锚变。
- [x] B2 `tests/test_review_roles.py`（6）：默认表、部分覆盖、auth 解析、hash。
- [x] B3 `tests/test_review_adapters.py`（9）：解析、severity、mock、成本、错误分类。
- [x] B4 `tests/test_review_orchestrator.py`（8）：合并去重、收敛、停滞、预算、fallback。
- [x] B5 `tests/test_review_report.py`（6）：四条负样本 + 正常读回。
- [x] B6 `tests/test_cli.py`：动词面含 `review`。
- [x] B7 `tests/test_review_adapters.py`：`gpt-6.1-sol` 价格表项回归
      （未知模型成本恒 0 会让预算止损失效）。
- [x] B8 auth 解析单点化：`adapters.resolve_auth_token` 同时供预检、回落判定与
      `build_adapter` 使用；回归测试覆盖 `ANTHROPIC_AUTH_TOKEN` 兜底。
- [x] B9 解析失败不再假 PASS：适配器把畸形输出标为 `error_kind=parse`，回落仍失败
      时整轮 `BLOCKED`；回归测试覆盖 adapter 与 orchestrator 两层。
- [x] B10 预算检查前移：未收敛时先判预算，再决定是否调用 judge / fixer；软止损
      边界写进 design D8。
- [x] B11 回落 key 缺失不再假 PASS：隐式回落不再跑 mock；返回 reviewer 失败并
      整轮 `BLOCKED`。显式 `--adapter mock` 的烟测路径保留。
- [x] B12 `degraded_note` 进 Markdown 报告；mock 降级写成「存在 mock 降级」，
      不冒充「同源双审」。
- [x] B13 host `ANTHROPIC_*` 兜底改为**角色显式 opt-in**（`allow_host_auth_fallback`），
      防止 reviewer 把宿主 token 发往别的端点；`roles._auth_resolved` 委托同一实现。
- [x] B14 `review report`：config 是合法 JSON 但非对象 ⇒ 证据缺件；round 非整数 ⇒
      受控 finding，不抛 `ValueError`。
- [x] B15 `review run` 开始时清理上一次的 `rounds/round-*.json` 与 `summary.json`，
      防止两次 run 混读。
- [x] B16 无 `where` 的 finding 用合成 `where` 保留，不再静默丢成 PASS；
      `--positive-control` 的逐字匹配限制写进 design D9.7。
- [x] B17 收尾：坏 `--pass-rule` / `--mock-scenario` 走 `EXIT_USAGE`；清掉
      过期注释/死导入；双失败路径保留原始 `degraded_from`。

## C. 真实模型验证（T-071 / T-075）

- [x] C1 T-071：full（git）四码 3/1/0/5 实测；lite（digest）loop 收敛。
- [x] C2 T-075：找到真实 glm key；修复 reviewerB `base_url` 多 `/v1` 的 404；
      真跑 `glm-5.3` 无 `degraded_from`。
- [x] C3 T-075 正控：篡改 manifest 的 `reviewer_run_id == author_run_id` 与全零
      `tasks_hash` 被两路 reviewer 报出（blocker/high）。
- [x] C4 T-075 如实记录：clean demo 因代码确有 medium 问题判 `BLOCKED`；judge
      只拿 `where` 导致 `uncertain`，属既知限制。

## D. 本轮用户配置

- [x] D1 `reviewloop.roles.json`：reviewerA = `gpt-6.1-sol`（codex / heyroute）；
      reviewerB = `glm-5.3`（claude / heyroute）；fixer = `deepseek-flash`；
      judge = `deepseek-flash`（按用户 2026-11-19 决定）。
- [x] D2 `adapters.APPROX_PRICE_PER_MTOK` 增加 `gpt-6.1-sol: (5.0, 30.0)`，
      注释说明是按同代 Sol 档的保守估算。
- [x] D3 探通 `gpt-6.1-sol` 的 `chat/completions` 通路（200，model 回显正确）。

## E. 本 change 的文档与证据

- [x] E1 `proposal.md` / `design.md` / `tasks.md` / `specs/review-loop/spec.md`。
- [x] E2 grill 审阅：`reviews/grill-review.md`（Confirmed Decisions ≥3 带 `来源:`、
      Open Questions、User Confirmation）。
- [x] E3 设计对抗验证：`reviews/grill-adversarial.md`，逐条证伪关键决策。
- [ ] E4 building 审阅：`reviews/building-review.md`（`review run` 产物 + 人工核对；
      必须在内容提交之后跑，绑定该 revision）。
- [ ] E5 三份 stage manifest：`grill` / `grill-adversarial` / `building`，
      绑定内容提交 revision。

## F. 交付

- [x] F1 `uv run pytest -q` 全绿。
- [ ] F2 `check --base origin/main --head HEAD` 绿（记录原始输出）。
- [ ] F3 证据单独提交（`reviews/**` + manifest）。
- [ ] F4 push `feat/review-loop`，`gh pr create` 到 `main`；**不自行合并 main**。
- [ ] F5（需用户）`main` 开 branch protection：require PR + required check。

## 审阅修复

grill / 对抗验证在本内容提交前发现并已修复：

- **H1 宿主 token 跨端点复用**：`resolve_auth_token` 的 `ANTHROPIC_*` 兜底改为角色
  显式 `allow_host_auth_fallback`；普通 reviewer 默认 fail closed。测试
  `test_build_adapter_does_not_reuse_host_token_by_default`。
- **M1 `roles._auth_resolved` 第二套解析**：委托 `adapters.resolve_auth_token`；
  测试 `test_auth_resolved_matches_adapter_resolution`。
- **M2 config 非对象放行 / round 非整数崩溃**：`report.verify` 判「证据缺件」；
  `_read_rounds` 受控报错。测试 `test_non_object_config_is_red` /
  `test_non_integer_round_is_red`。
- **M3 旧 rounds 混读**：`review run` 开始时 `_reset_rounds`；测试
  `test_rerun_clears_stale_rounds`。
- **无 `where` finding 被静默丢弃**：改用合成 `where` 保留并阻塞收敛；测试
  `test_merge_findings_keeps_findings_without_where` /
  `test_missing_where_does_not_converge`。
- **parse 失败假 PASS / 回落 key 缺失假 PASS / 预算顺序 / auth 单点化 /
  `degraded_note`**：见 B8-B12。
- **逐字 `--positive-control`**：保留机制但登记为真实模型限制（design D9.7）。
- **L 系列**：坏用法走 `EXIT_USAGE`；过期注释/死导入清理；双失败路径保留原始
  `degraded_from`。

## 流程偏差

- **实现先于 change 目录**：功能代码在 `8cc7ddd` … `99f910a` 已提交；本 change 的
  proposal / design / tasks / spec 与三份 stage 证据是**复盘式补齐**，绑定当前
  revision，不声称审阅发生在实现之前。
- **judge 模型调整**：T-071/T-075 时 judge 出厂默认是 `deepseek-v4-pro`；本轮按
  用户决定改为 `deepseek-flash`。这是 `reviewloop.roles.json` 的配置选择，不改代码默认。
- **成本口径**：`gpt-6.1-sol` 不在本机 `model_pricing` 表；价格按同代 Sol 档估算，
  报告里的 USD 只用于止损，不是账单。
