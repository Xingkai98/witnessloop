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

## B. 测试（T-071 新增 44 条；2026-11-19 加固新增 79 条，合计 123 条）

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
- [x] B18 grill 第二轮发现：`allow_host_auth_fallback` 必须带进 resolved config；
      `FALLBACK_ROLE` 不再默认复用宿主 token；design/spec 同步 opt-in 前提。
- [x] B19 审阅上下文：变更文件清单 + diff 按代码/测试优先排序，上限 120000 字符；
      修掉 `diff[:20000]` 让 reviewer 看不到 `src/**` 的误报（实测 building review
      因此把「没看到代码」报成 blocker/high）。测试 `test_prioritize_diff_puts_code_before_docs`。
- [x] B20 digest 模式显式告知「无 diff、不要报代码不存在」并附工作树文件清单；
      design D9.8 登记限制。
- [x] B21 解析层结构校验：finding 必须是对象且 severity ∈
      blocker/high/medium/low/nit；字符串 finding / 缺 severity 判 parse 失败，
      不再静默丢成 PASS。测试 `test_parse_review_output_rejects_*`。
- [x] B22 judge 只复核 stalled 子集：其 PASS 不得覆盖同轮未送审的 medium+；
      有未复核项时最终判 BLOCKED。测试
      `test_judge_pass_does_not_cover_unstalled_findings`。
- [x] B23 预算检查前移到**每轮入口**：fixer 把累计成本推过预算后不再发起下一轮
      reviewer 调用。测试 `test_budget_stops_before_next_round_after_fixer`。
- [x] B24 `_render_markdown` 对非对象 config 受控渲染（不再 `.get` 崩溃）；
      非空数组负样本 `test_non_object_config_is_red`。
- [x] B25 内联 `auth_token` 只从写盘 config 脱敏；实际调用用内存运行时角色表
      `runtime_roles`，避免「resolved 说已解析、适配器拿空串」。测试
      `test_runtime_roles_keep_inline_token` / `test_resolve_config_redacts_inline_token`。
- [x] B26 fixer / judge 的失败写进 round manifest（`fixer.error` / `judge.error`）
      并进 Markdown 报告；不再静默吞掉。测试 `test_fixer_error_is_recorded` /
      `test_judge_error_is_recorded` / `test_report_renders_fixer_error`。
- [x] B27 severity 规范化贯穿解析/去重/收敛：`" HIGH "` 不得绕过阻塞判定。
- [x] B28 fixer/judge 不再被 reviewer 的 `findings` 解析器误伤；合法 `fixes` /
      `rulings` 不记为 parse 失败。测试 `test_fixer_valid_raw_is_not_marked_parse_error`。
- [x] B29 judge PASS 必须逐条覆盖 stalled 且全为 false-positive；否则 BLOCKED。
      测试 `test_judge_pass_requires_full_rulings` / `test_judge_pass_with_real_ruling_is_blocked`。
- [x] B30 `review report` 对 actors/findings/fixer/judge 的类型篡改受控判红，不崩溃；
      测试 `test_malformed_manifest_types_are_red`。
- [x] B31 `load_roles` 读文件 OSError 回落默认（语法坏才 ValueError）；
      `review run --base <ref>` 显式指定 diff base；回落只尝试一次。
- [x] B32 角色覆盖改为**字段级合并**；缺 `adapter` 抛 `ValueError`，不再隐式 mock。
      测试 `test_load_roles_merges_partial_overrides` /
      `test_resolved_role_requires_explicit_adapter`。
- [x] B33 `review report` 校验每轮至少两路 reviewer actors；fixer/judge 非对象类型
      判红。测试 `test_missing_reviewer_actors_is_red` /
      `test_malformed_manifest_types_are_red`。
- [x] B34 `review report --md` 真正可用（此前文档声称但 argparse 未注册）。
      测试 `test_report_accepts_md_flag`。
- [x] B35 适配器校验 HTTP 响应是 JSON 对象、Codex content 是字符串；
      `cost_usd` 对非 dict usage 返回 0。测试
      `test_claude_adapter_rejects_non_object_response` 等。
- [x] B36 judge 同一 where 的重复裁决取「任一非 false-positive 即不放行」；
      测试 `test_judge_duplicate_ruling_cannot_mask_real`。
- [x] B37 网络超时（`TimeoutError`/`OSError`）归一成 `AdapterError("other")`，
      不再让 CLI 崩成「内部错误」。测试 `test_http_timeout_is_adapter_error`。
- [x] B38 diff 获取失败（含坏 `--base`）直接中止 run，不再带着「无法取 diff」
      继续并可能产出 PASS；测试 `test_invalid_base_fails_before_review`。
- [x] B39 适配器结构加固：content 必须数组、text 必须是字符串、usage 必须是对象、
      token 字段容错；测试 `test_claude_adapter_rejects_non_array_content` 等。
- [x] B40 `review report` 严格要求 reviewerA/reviewerB 各一个且 run_id 非空不同；
      测试 `test_wrong_reviewer_roles_is_red` / `test_missing_run_id_is_red`。
- [x] B41 5xx/超时（`other`）也回落一次；测试 `test_runtime_other_error_falls_back`。
- [x] B42 reviewer 角色必须**各恰好一个**（重复 role 不再被 dict 覆盖）；
      测试 `test_wrong_reviewer_roles_is_red`。
- [x] B43 mock scenario 校验每轮是 findings 数组、每项是对象且 severity 合法；
      测试 `test_bad_mock_scenario_content_is_usage_error`。
- [x] B44 config.roles 的每个角色必须是对象；渲染逐角色防御；
      测试 `test_config_roles_non_object_is_red`。
- [x] B45 回落前检查剩余预算；首次请求已超预算时不再发起 fallback 付费调用。
      测试 `test_no_fallback_when_budget_already_exceeded`。
- [x] B46 Claude 适配器对非对象 usage 置 None，避免成本静默为 0；
      测试 `test_claude_adapter_tolerates_non_object_usage`。
- [x] B47 git 模式的 change 文档从被审 revision 读取（`git show`），
      不混入未提交修改；测试 `test_context_reads_docs_from_revision_not_worktree`。
- [x] B48 roles 覆盖值非对象 ⇒ ValueError（不静默回落默认）；
      测试 `test_load_roles_rejects_non_object_role`。
- [x] B49 adapter 名不在 claude/codex/mock ⇒ 展开配置时 ValueError；
      测试 `test_resolved_role_rejects_unknown_adapter`。
- [x] B50 拒绝 HTTP 重定向（防止 Authorization/x-api-key 跨信任域转发）；
      测试 `test_redirect_is_refused`。
- [x] B51 模型输出必须**恰好一个**顶层 JSON 对象；多对象判 parse 失败；
      测试 `test_parse_review_output_rejects_multiple_json_objects`。
- [x] B52 worktree digest 用长度前缀编码，消除内容含 NUL 时的哈希碰撞；
      测试 `test_digest_disambiguates_nul_in_content`。
- [x] B53 并发 reviewer 的预算快照边界写进 design D8（两路各一次 fallback
      可能合计越过上限一个调用，软止损已知限制）。
- [x] B54 fixer/judge 也走「恰好一个顶层 JSON 对象」校验；多对象不再取第一个
      对象放行。测试 `test_fixer_rejects_multiple_json_objects` /
      `test_judge_rejects_multiple_json_objects`。
- [x] B55 report 用 summary.json 的轮次核对磁盘 round 文件；少一轮即判红。
      测试 `test_missing_round_file_is_red`。
- [x] B56 缺 key 的回落分支同样检查剩余预算；预算已尽不再发 fallback。
      测试 `test_auth_missing_does_not_fallback_without_budget`。
- [x] B57 reviewer 的 `verdict` 参与判定：BLOCKED ⇒ 整轮 BLOCKED；
      CHANGES_REQUESTED 但无 findings ⇒ 合成 medium，不静默 PASS。测试
      `test_reviewer_blocked_verdict_blocks` /
      `test_reviewer_changes_requested_without_findings_blocks_pass`。
- [x] B58 summary.json 缺失/不可解析/rounds 非数组 ⇒ 证据缺件；
      测试 `test_missing_or_malformed_summary_is_red`。
- [x] B59 fixer 缺 `fixes` / judge verdict 非法或缺 `rulings` ⇒ 记录失败并 BLOCKED；
      测试 `test_fixer_missing_fixes_is_recorded` / `test_judge_invalid_verdict_is_blocked`。
- [x] B60 顶层数组（`[{...}]`）不算「一个 JSON 对象」；测试
      `test_parse_review_output_rejects_top_level_array`。
- [x] B61 fixer 失败即停止并 `BLOCKED`，不进入下一轮让空 findings 收口；
      测试 `test_fixer_failure_blocks_run`。
- [x] B62 显式非法 verdict（如 `FAIL`）判 parse 失败，不静默改写为 PASS；
      测试 `test_parse_review_output_rejects_illegal_explicit_verdict`。
- [x] B63 `--budget` 必须是有限非负数；nan/inf/负数走 `EXIT_USAGE`。
      测试 `test_non_finite_budget_is_usage_error`。
- [x] B64 停止分支同步 round manifest 的 `verdict`（预算/fixer/judge），
      summary 与 round 不再各说各话。
- [x] B65 fixer 的 `fixes` 逐条校验（对象 + where + action）；空/非法条目算失败。
      测试 `test_fixer_invalid_fix_items_are_recorded`。
- [x] B66 reviewer 返回 CHANGES_REQUESTED 但无 findings 时，即使另一路有 findings
      也保留合成 medium，不让其他 finding 掩盖。
- [x] B67 合成 medium 只补给**自己没给 medium+** 的 reviewer；正常报出缺陷的
      reviewer 不再被扣假问题。
- [x] B68 judge 上下文包含 stalled finding 的 what/suggestion/severity 与
      截断的 review context（diff/设计），不再只给 where 串；测试
      `test_judge_context_includes_findings_and_diff`。
- [x] B69 fixer 混合有效/非法条目也判失败（不静默过滤坏条目）；
      测试 `test_fixer_mixed_valid_and_invalid_items_is_error`。
- [x] B70 达到 max_rounds / 下一轮入口预算止损时，最后一轮 manifest 的 verdict
      同步为最终 verdict；测试 `test_max_rounds_syncs_last_manifest_verdict`。
- [x] B71 `--budget` 必须是有限**正数**（0 也不再允许，避免一次调用都不发）。
- [x] B72 数组包裹检测只拒绝 `[{...}]`，不误伤散文里的 `[P1]`；
      测试 `test_parse_review_output_allows_prose_brackets`。
- [x] B73 summary.json 的 rounds 条目必须都是含整数 round 的对象；
      测试 `test_summary_rounds_malformed_entries_are_red`。
- [x] B74 degraded_note 扫描所有轮次（不只看最后一轮）；Markdown 报告显示
      cumulative_cost_usd。

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
- **grill 第二轮 H2/M5**：`allow_host_auth_fallback` 带进 resolved config；
  回落通路不再默认复用宿主 `ANTHROPIC_*` token（缺 `WITNESSLOOP_DEEPSEEK_KEY`
  时判 BLOCKED）。测试 `test_resolved_role_keeps_host_fallback_flag`。

## 流程偏差

- **实现先于 change 目录**：功能代码在 `8cc7ddd` … `99f910a` 已提交；本 change 的
  proposal / design / tasks / spec 与三份 stage 证据是**复盘式补齐**，绑定当前
  revision，不声称审阅发生在实现之前。
- **judge 模型调整**：T-071/T-075 时 judge 出厂默认是 `deepseek-v4-pro`；本轮按
  用户决定改为 `deepseek-flash`。这是 `reviewloop.roles.json` 的配置选择，不改代码默认。
- **成本口径**：`gpt-6.1-sol` 不在本机 `model_pricing` 表；价格按同代 Sol 档估算，
  报告里的 USD 只用于止损，不是账单。
