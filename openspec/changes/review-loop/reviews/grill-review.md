# Grill: review-loop 设计追问

## Reviewer
- run id: `grill-reviewer-review-loop-2026-11-19-rerun`（零记忆审阅者；`WITNESSLOOP_RUN_ID` 未设，按确定性兜底形态自拟，不代表真实 run 身份）
- 时间: 2026-11-19 07:24 UTC
- 快照: 当前工作树（HEAD `f8528ea`，内容提交「review-loop change 文档 + sol/flash 配置 + review loop 加固」）。只读核验时的文件 sha256 前缀：`adapters.py 55ef2834…`、`orchestrator.py 39dcf6f2…`、`report.py 0e8f01d7…`、`revision.py 6388668f…`、`roles.py 22e4d204…`。审阅期间工作树被并行修改；本报告以 2026-11-19T07:24Z 的这批内容为准。
- 实测：`.venv/bin/python -m pytest -q` → **849 passed**；`tests/test_review_*.py` → **60 passed**（2026-11-19T07:22Z）。

## Confirmed Decisions
- **双路 reviewer 并发 + 只按 `where` 去重取高 severity + `medium_plus_zero` 收敛**：合并后 blocker/high/medium 为零判 `PASS`，否则 `CHANGES_REQUESTED`。来源: 工作树核验 `src/witnessloop/review/orchestrator.py:365-405`、`tests/test_review_orchestrator.py::test_run_converges_with_mock_scenario`；`design.md` D5（:87-104）、`spec.md:8-19`；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **解析失败不再假 PASS（已修复）**：无法解析的输出被标 `error_kind="parse"`；回落仍失败时整轮 `BLOCKED`，空 findings 不参与 `PASS`。来源: 工作树核验 `src/witnessloop/review/adapters.py:230-232,280`、`src/witnessloop/review/orchestrator.py:264,396-405,415-420`、`tests/test_review_adapters.py::test_parse_error_marks_adapter_result_as_parse_failure`、`tests/test_review_orchestrator.py::test_reviewer_failure_blocks_instead_of_passing`；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **隐式回落 key 全缺不再用 mock 冒充审阅（已修复）**：`_call_reviewer` 返回 `_NO_FALLBACK_ERROR` + `error_kind="auth"`，round 级 `reviewer_errors` 判 `BLOCKED`；显式 `--adapter mock` 的烟测路径不受影响。来源: 工作树核验 `src/witnessloop/review/orchestrator.py:206-223,241-258,264-278`、`tests/test_review_orchestrator.py::test_no_keys_blocks_instead_of_mock_pass`；`design.md` D6、`spec.md:87-105`；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **预算检查前移到 judge / fixer 之前（已修复，软止损口径明确）**：未收敛时先判累计成本，超预算即 `BLOCKED`，不再发起 judge/fixer；单次调用本身可越过上限已写进 design D8。来源: 工作树核验 `src/witnessloop/review/orchestrator.py:425-430`、`tests/test_review_orchestrator.py::test_budget_stops_before_judge`；`design.md` D8（:138-141）；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **`report.md` 归属已澄清（已修复文档口径）**：`review run` 只写 `summary.json`，`report.md` 由 `review report --out` 生成。来源: 工作树核验 `src/witnessloop/review/orchestrator.py:609-613`、`tests/test_review_report.py::test_report_reads_back_actors_and_config_hash`；`design.md` D1（:26-27）、`spec.md:18-19`；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **`degraded_note` 已渲染进 Markdown 报告（已修复）**：两路都回落时「本轮为同源双审」出现在 `review report` 输出；两路都降到 mock 时写「本轮存在 mock 降级（不代表真实双审）」。来源: 工作树核验 `src/witnessloop/review/report.py:128-130,174-175`、`src/witnessloop/review/orchestrator.py:624-634`、`tests/test_review_report.py::test_report_renders_degraded_note`、`tests/test_review_orchestrator.py::test_final_report_does_not_call_mock_degradation_same_source`；`design.md` D6（:120-122）；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **宿主 `ANTHROPIC_*` 凭据默认不跨端点复用（已修复，角色级 opt-in）**：`resolve_auth_token` 只在角色显式 `allow_host_auth_fallback: true` 时才回落 `ANTHROPIC_*`；`FALLBACK_ROLE` 显式打开，普通 reviewer 默认关闭。**注意**：该 opt-in 尚未传播进 `config.resolved.json`（见风险 H2）。来源: 工作树核验 `src/witnessloop/review/adapters.py:283-304`、`src/witnessloop/review/orchestrator.py:196-204`、`tests/test_review_adapters.py::test_build_adapter_does_not_reuse_host_token_by_default`；`tasks.md` B13；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **auth 解析单点化（已修复）**：`roles._auth_resolved` 现在委托 `adapters.resolve_auth_token`，预检 / 回落判定 / `build_adapter` 同一口径。来源: 工作树核验 `src/witnessloop/review/roles.py:95-101,117`、`tests/test_review_roles.py::test_auth_resolved_matches_adapter_resolution`；`design.md` D4、`spec.md:144-153`；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **没有 `where` 的 finding 不再静默丢成 PASS（已修复）**：用合成 `where`（`<missing-where>:batch…`）保留并参与收敛判定。来源: 工作树核验 `src/witnessloop/review/orchestrator.py:117-144`、`tests/test_review_orchestrator.py::test_missing_where_does_not_converge`；`design.md` D5（:94-99）、`spec.md:12-14,33-37`；run `grill-reviewer-review-loop-2026-11-19-rerun`。
- **`.reviewloop/` 与门禁证据分离，且 digest 排除自身产物；fixer 不自动改代码**：`check` 仍只认 `reviews/*.manifest.json`；digest 排除 `.git` 与 `.reviewloop/`；fixer 只记录 `fixes` JSON。来源: 工作树核验 `src/witnessloop/constants.py:132-135`、`src/witnessloop/review/revision.py:25,57-74`、`src/witnessloop/review/orchestrator.py:441-445,518-533`、`tests/test_review_revision.py::test_digest_ignores_output_dir`；`proposal.md`「非目标」、`design.md` D9.2-3；run `grill-reviewer-review-loop-2026-11-19-rerun`。

## Code-Resolved Questions
- 每轮 manifest 字段是否满足 spec？→ 是：`revision` / `config_hash` / `actors[]` / `findings` / `verdict` / `cost_usd` / `fixer` / `judge` / `note` 齐全。证据：`src/witnessloop/review/orchestrator.py:569-581`；`spec.md:45-53`。
- `review run` 是否会自动写 `report.md`？→ 不会；只写 `summary.json`。证据：`src/witnessloop/review/orchestrator.py:609-613`；`design.md` D1（:26-27）、`spec.md:18-19`。
- digest 锚是否会被自己的产物改掉？→ 不会；排除 `.git` 与 `.reviewloop/`。证据：`src/witnessloop/review/revision.py:25,59-76`；`tests/test_review_revision.py::test_digest_ignores_output_dir`。
- 解析失败会回落 / BLOCKED 吗？→ 会；`parse` 已进入回落集合，回落仍失败则 round 级 `reviewer_errors` 判 `BLOCKED`，且不继续调用 fixer/judge。证据：`src/witnessloop/review/orchestrator.py:264,396-405,415-420`。
- 已超预算时还会先调 judge / fixer 吗？→ 不会。证据：`src/witnessloop/review/orchestrator.py:425-430`；`tests/test_review_orchestrator.py::test_budget_stops_before_judge`。
- 连 deepseek key 都没有时会走 mock 假 PASS 吗？→ 不会（显式 `--adapter mock` 除外）。证据：`src/witnessloop/review/orchestrator.py:206-223,241-258`；`tests/test_review_orchestrator.py::test_no_keys_blocks_instead_of_mock_pass`。
- 宿主 token 默认会被发往任意端点吗？→ 默认不会；仅当角色带 `allow_host_auth_fallback: true` 才回落 `ANTHROPIC_*`。证据：`src/witnessloop/review/adapters.py:283-304`；`tests/test_review_adapters.py::test_build_adapter_does_not_reuse_host_token_by_default`。**但角色级 opt-in 经过 `resolve_config` 后会丢失，见风险 H2。**
- `roles._auth_resolved` 与适配器是否同口径？→ 是（已委托同一函数）。证据：`src/witnessloop/review/roles.py:95-101`；`tests/test_review_roles.py::test_auth_resolved_matches_adapter_resolution`。
- `review report` 对坏 config / 坏 round 字段是否 fail-closed？→ 是：非对象 config 判「证据缺件」；非整数 `round` 记 finding，不再抛 `ValueError`。证据：`src/witnessloop/review/report.py:34-48,63-71`；`tests/test_review_report.py::test_non_object_config_is_red`、`::test_non_integer_round_is_red`。
- 两次 run 的 round 会混读吗？→ 不会；`review run` 开始时清理 `rounds/round-*.json` 与 `summary.json`。证据：`src/witnessloop/review/orchestrator.py:330-331,586-598`；`tests/test_review_orchestrator.py::test_rerun_clears_stale_rounds`。
- 缺少 `where` 的 finding 会怎样？→ 用合成 `where` 保留并参与收敛判定，不会因合并为空判 `PASS`。证据：`src/witnessloop/review/orchestrator.py:117-144`；`tests/test_review_orchestrator.py::test_missing_where_does_not_converge`。
- judge 的上下文足够独立核验吗？→ 不足：只把 `where` 字符串交给 judge；属 `design.md` D9.1 已登记限制。证据：`src/witnessloop/review/orchestrator.py:538-544`；`docs/reviews/t075-glm-rerun.md` §2、§6。
- 「两路同一 actor」能证明真实独立审阅吗？→ 不能：`run_id` 带角色前缀；该负样本是产物级篡改检查，不是独立性证明。证据：`src/witnessloop/review/orchestrator.py:178-181`；`src/witnessloop/review/report.py:88-96`；`design.md` D9.6。
- `--positive-control` 的适用边界？→ 只做 `where` 逐字相等匹配，真模型措辞不定易误报；保留给 mock/确定性场景。证据：`design.md` D9.7（:166-168）。
- 成本是计费依据吗？→ 不是；近似价只用于止损与展示；`gpt-6.1-sol` 已进价格表。证据：`src/witnessloop/review/adapters.py:28-36`；`tests/test_review_adapters.py::test_cost_usd_knows_gpt_6_1_sol`。
- 当前测试真实数量？→ 全量 **849 passed**；`docs/merge-report.md` 的 832 / 841 是过期数字（见 L6）。
- 坏 `--pass-rule` / `--mock-scenario` 会怎样？→ `EXIT_USAGE` + 明确错误，不再 traceback。证据：`src/witnessloop/review/orchestrator.py:316-328`；`tests/test_review_orchestrator.py::test_bad_pass_rule_is_usage_error`、`::test_bad_mock_scenario_is_usage_error`。

## Open Questions
（无）

## 风险
- **[medium] H2 `allow_host_auth_fallback` 未传播进 resolved config，预检与适配器再次分叉**：`roles._resolved_role` 构造的 `out` 只含 adapter/model/base_url/auth_env/auth_resolved，**不复制** `allow_host_auth_fallback`（`roles.py:104-118`）；而 `review run` 用的是 `role_cfgs = resolved["roles"]`（`orchestrator.py:357`），`adapters.resolve_auth_token` 读的正是这个被丢掉 flag 的 dict（`adapters.py:300`）。实测（设 `ANTHROPIC_AUTH_TOKEN`、不设 `WITNESSLOOP_DEEPSEEK_KEY`、角色带 `allow_host_auth_fallback: true`）：`config.resolved.json` 里 `auth_resolved=True`，但 `build_adapter` 拿到的 token 为空；同一原始 role 直接调用 `resolve_auth_token` 却非空。后果：用户显式打开的 opt-in 对 fixer/judge 变成空 key 请求（`_run_fixer`/`_run_judge` 没有 auth 预检，`orchestrator.py:518-554`），对 reviewer 则被忽略并回落——正是 spec 禁止的「预检说 key 在、适配器拿到空串」。修复：在 `_resolved_role` 中复制该字段（并让它进入 `config_hash`），补一条 `resolve_config → build_adapter` 的集成测试（现有 `test_auth_resolved_matches_adapter_resolution` 只测了直接调用 `_auth_resolved`，覆盖不到这条路径）。
- **[medium] M4 design / spec 仍写无条件的 `ANTHROPIC_*` 链，与已实现的行为不符**：`design.md:83-86` 与 `spec.md:144-153` 仍写 `auth_token → auth_env → ANTHROPIC_AUTH_TOKEN → ANTHROPIC_API_KEY` 无条件生效；代码现在要求角色显式 `allow_host_auth_fallback: true`（`adapters.py:286-303`）。spec 的 Scenario「key 只住在 ANTHROPIC_AUTH_TOKEN」也没有该前提，照 spec 实现会重新引入跨端点复用。修复：更新 D4 与 spec Requirement/Scenario，把 opt-in 前提写清；D3 的 roles 示例补上该字段（当前只有 `tasks.md` B13 记录了这次行为变更）。
- **[medium] M5 `FALLBACK_ROLE` 的宿主兜底是硬编码 opt-in，残余跨端点风险未消**：`FALLBACK_ROLE` 在代码里固定 `allow_host_auth_fallback: True`（`orchestrator.py:196-204`）。当宿主设了 `ANTHROPIC_*` 而没有 deepseek key 时（本机核验：`WITNESSLOOP_*` 均未设、`ANTHROPIC_*` 均 SET；未发请求），回落路径会把宿主 token 作为 `x-api-key` 发往 `api.deepseek.com`。代码无法判断该 token 是否真是 deepseek 凭据。建议：把 fallback 的宿主兜底也做成显式配置（env/`reviewloop.roles.json`），或至少在 design D6 写清「宿主 token 必须是对应端点可接受的凭据」这一前提；若确认接受该前提，可把本条降级为已接受风险（需在 design 落文）。
- **[low] L2 `degraded_note` 只覆盖「回落导致的同源」**：判定条件是「两路都有 `degraded_from`」（`orchestrator.py:624-634`）；两路本就配置成同一 model，或一路本就用 `deepseek-flash`、另一路回落到它时，不会提示。`design.md:156-160` 说「真实同源双审由 `degraded_note` / `degraded_from` 记录」应改为「只记录回落导致的同源」。（已按用户口径登记为已知限制。）
- **[low] L3 fixer / judge 失败没有单独 note**：`_run_fixer` 出错时得到 `fixes=[]` + `raw`（错误体）并继续；`_run_judge` 出错时退化为 `BLOCKED`，note 仍写「停滞升级」。H2 会让带 opt-in 的 fixer 走到这条静默路径。证据：`orchestrator.py:518-554`。（已按用户口径登记为已知限制。）
- **[low] L4 round manifest 无内容哈希，context 读工作树而 revision 锚 HEAD**：`_build_context` 的 tasks/design/proposal 从工作树读、diff 取 `base..HEAD`；脏工作树时 manifest 无法证明 reviewer 看到的 change 文档内容。证据：`orchestrator.py:156-175,569-581`。（已按用户口径登记为已知限制。）
- **[low] L5 对抗报告文件名仍未统一**：`tasks.md:75` 写 `reviews/grill-adversarial-review.md`，模板规定 `reviews/grill-adversarial.md`（`templates/grill.md:156,200`）。用户已说明将统一，当前工作树尚未改。
- **[low] L6 merge-report / design D10 测试计数过期**：`docs/merge-report.md:3,151` 仍写 832 passed，`:149` 写 849（与实测一致）；`design.md` D10 仍写「共 44 条新增」，而当前 `tests/test_review_*.py` 为 60 条。建议以实测 849 为准并删掉过期数字。
- **[nit] N1 `_reset_rounds` 在 `load_roles` 之前执行**：`review run` 先清空 `rounds/` + `summary.json`（`orchestrator.py:330-331`），再 `load_roles`（`:335-348`）；若 `reviewloop.roles.json` 语法坏，新 run 退出 1 但上一次的 round 已被删除。属本地可重跑目录，影响很小；可把 reset 放到配置校验之后。

## User Confirmation
- reviewerA=`gpt-6.1-sol`、judge=`deepseek-flash`：依据 `tasks.md` D1 记录的用户 2026-11-19 决定；确认时间：2026-11-19。
- 用户表示「开搞目标 push pr」：依据本次任务提供的用户确认记录；确认时间：2026-11-19。
- 说明：以上确认**不涵盖**本报告的风险项与设计取舍；`## Open Questions` 无未决项，故无逐条 `Qn` 确认。

## 结论
- **medium+ 不为零：3 条 medium（H2 / M4 / M5），无 high/blocker。**
- 必须修复项：
  1. **H2**：`_resolved_role` 复制 `allow_host_auth_fallback`（并纳入 config hash），补 `resolve_config → build_adapter` 集成测试，消除「config 说 auth_resolved、适配器拿到空串」的分叉。
  2. **M4**：把 opt-in 前提写进 `design.md` D4 与 `spec.md` 的 auth Requirement/Scenario，D3 示例补字段；否则 spec 仍在要求无条件使用宿主 token。
  3. **M5**：把 `FALLBACK_ROLE` 的宿主兜底改为显式可配置，或在 design D6 落文接受该前提（二选一；未落文前按 medium 计）。
- 已修复并复核（详见下节）：parse 失败不再假 PASS、回落 key 全缺不再 mock 假 PASS、预算前移、`report.md` 归属、`degraded_note` 渲染、宿主 token 默认拒绝、`_auth_resolved` 单点化、report 坏 config/坏 round fail-closed、旧 rounds 清理、坏 CLI 参数走 `EXIT_USAGE`、无 `where` finding 保留、过期注释/死导入清理、双失败路径保留原始 `degraded_from`。
- low/nit 不阻塞：L2/L3/L4 已按已知限制登记；L5 待统一文件名；L6 待重跑后统一计数；N1 为可重跑目录的轻微顺序问题。
- 未决 `Qn`：无。

## 修复复核（2026-11-19）
- **H1（跨端点复用宿主 token）→ 已修复**：`adapters.resolve_auth_token` 默认只认 `auth_token` / `auth_env`，仅 `allow_host_auth_fallback is True` 时才回落 `ANTHROPIC_*`（`adapters.py:283-304`）；`FALLBACK_ROLE` 显式打开（`orchestrator.py:196-204`）；回归测试 `test_build_adapter_does_not_reuse_host_token_by_default`、`test_build_adapter_uses_shared_auth_resolution`。**复核备注**：默认路径已安全；角色级 opt-in 的传播链有缺口，另见新发现 H2。
- **M1（`roles._auth_resolved` 第二套解析）→ 已修复**：`roles.py:95-101,117` 委托 `adapters.resolve_auth_token`；测试 `test_auth_resolved_matches_adapter_resolution`。
- **M2（config 非对象放行）→ 已修复**：`report.py:63-71` 对非 dict config 判「证据缺件」；测试 `test_non_object_config_is_red`。
- **M3（旧 rounds 混读）→ 已修复**：`orchestrator.py:330-331,586-598` 在 run 开始时清理 rounds/summary；测试 `test_rerun_clears_stale_rounds`。
- **L1（round 非整数崩溃）→ 已修复**：`report.py:34-48` 将非整数 `round` 记为 finding；测试 `test_non_integer_round_is_red`。
- **L2/L3/L4 → 已按已知限制登记**：L2 见 `design.md` D9.6 段（表述仍需按上文 L2 修正）；L3/L4 按用户口径登记，design D9 尚未逐条落文。
- **L5 → 待统一**：`tasks.md:75` 仍写 `grill-adversarial-review.md`；用户已说明将改为 `grill-adversarial.md`。
- **L6 → 待重跑后统一**：全量实测 **849 passed**；`docs/merge-report.md:3,151` 的 832 与 `design.md` D10 的「44 条新增」仍过期。
- **N1（过期注释）→ 已修复**：`orchestrator.py:7` 改为 `.reviewloop/rounds/`、`:472` 改为写 `summary.json`；`revision.py:59-61` 改为 `.reviewloop`。
- **N2（死导入）→ 已修复**：`orchestrator.py:24` 不再导入 `field`。
- **N3（坏 CLI 参数 traceback）→ 已修复**：`orchestrator.py:316-328` 走 `EXIT_USAGE`；测试 `test_bad_pass_rule_is_usage_error`、`test_bad_mock_scenario_is_usage_error`。
- **N4（双失败路径覆盖 `degraded_from`）→ 已修复**：`orchestrator.py:266-268` 用 `if degraded_from is None` 保留原始 model。
- **复核中新发现**：H2（opt-in 未传播，medium）、M4（design/spec 未写 opt-in，medium）、M5（FALLBACK_ROLE 硬编码宿主兜底，medium）。
