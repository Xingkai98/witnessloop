# Grill: gate-event-guard 设计追问

## Reviewer

- run id: `grill-reviewer-gate-event-guard-2026-11-03`
- 时间: 2026-11-03
- verdict: **可进入对抗验证**（frontier 已空；无 Open Question 需用户拍板）。
- 审阅方式: 按 `templates/grill.md` 的 7 个维度逐项追问 `proposal.md` / `design.md`，
  只读仓内代码、文档与既有行为测试，不读作者会话历史。
- ⚠️ 流程偏差（如实记录）：报告文本产出在实现与测试跑绿之后；设计在写代码前定稿，
  未在报告产出前伪造任何 manifest / gate 结论。

## Confirmed Decisions

- **决策（需求对齐 · 守卫应在 gate 层）**：issue #48 是 workflow 调用契约问题，不是
  `check` 的区间判定问题；`check` 的 #45 语义（零变更 `EXIT_EMPTY=5`）不应为事件类型改变。
  理由：`checkcmd.run` 只接收 base/head，不知道 `GITHUB_EVENT_NAME`；把事件塞进 CLI
  会让本地动词依赖 CI 环境并把「零变更」与「事件不对」混成一个出口。
  来源: `grill-reviewer-gate-event-guard-2026-11-03`
- **决策（可测性 · 独立 shell 脚本）**：守卫逻辑必须在
  `scripts/gate-event-guard.sh` 里、只读 `GITHUB_EVENT_NAME`；YAML 只负责取得并执行。
  理由：单测可直接 `sh script` 逐字断言 stderr；YAML 内联 bash 不可单测，且与脚本
  双份实现必然漂移。`tests/test_gate_event_guard.py` 分脚本单测 / YAML 接线 / 行为级三层。
  来源: `grill-reviewer-gate-event-guard-2026-11-03`
- **决策（分发 · reusable workflow 看不到本仓 scripts/）**：reusable workflow 的工作区
  只有 **caller** 仓，第一次 checkout 前为空；因此「`sh scripts/gate-event-guard.sh`」
  在接入方仓会 127。选择：按 `steps.wl-ref.outputs.ref` 把本仓检出到 `.witnessloop-gate`
  （`fetch-depth: 1`、`persist-credentials: false`），执行后删除。
  理由：复用既有的「一个 ref 同时决定 workflow / 包」契约；`actions/checkout` 的
  ref-helper 明确处理 `refs/tags/*`；composite action 的 `uses:` 不能吃动态 ref、
  curl raw 会引入解析期网络依赖、`init` 写脚本会让老接入方缺件。
  来源: `grill-reviewer-gate-event-guard-2026-11-03`
- **决策（顺序 · 守卫尽早、check 不动）**：resolve → guard checkout → guard →
  caller checkout（`fetch-depth: 0`）→ setup-uv → check。resolve 仍是第一个 step
  （包来源先可见）；守卫在重 checkout 之前，非 PR 事件尽早失败。
  理由：既有 `test_resolve_step_is_the_first_step`；守卫不需要 caller 工作区；
  `check` 本体不改。
  来源: `grill-reviewer-gate-event-guard-2026-11-03`
- **决策（文案 · 三件事必须都在 stderr）**：PR 区间设计 / 零变更按 #45 不是通过 /
  需要放行必须显式 `--allow-empty` 且不要为了抹红默认加。
  理由：issue #48 原文；测试用稳定关键词（`pull_request`、`零变更`、`EXIT_EMPTY`、
  `--allow-empty`、`不要`）逐条断言，避免整句文案漂移导致无意义红。
  来源: `grill-reviewer-gate-event-guard-2026-11-03`
- **决策（adopter tests 的 `if`）**：用
  `${{ !cancelled() && steps.wl-event-guard.outcome != 'failure' }}`，而不是
  `== 'success'`。守卫失败 ⇒ 不跑测试；`check` 失败时守卫仍 success ⇒ 测试照常跑；
  更早步骤失败使守卫 skipped 时也维持旧行为。
  理由：`!= 'failure'` 同时满足「非 PR 不继续跑测试」与「PR 路径行为不变」。
  来源: `grill-reviewer-gate-event-guard-2026-11-03`

## Code-Resolved Questions

- **Q：守卫能不能直接读 `github.event_name` 的 `${{ }}` 内联进 run？**
  Resolved：不。经 `env:` 传入、脚本运行时读，与 adopter tests / resolve step 同口径，
  并让测试能在 `sh` 里注入事件名。
- **Q：`pull_request_target` 要不要放行？**
  Resolved：不放行。issue #48 原文是 `github.event_name != 'pull_request'`；
  `pull_request_target` 的安全语义不同，归入拒绝分支。
- **Q：脚本缺失时能不能静默跳过守卫？**
  Resolved：不能。显式 `witnessloop-ref` 若指到没有该脚本的旧 ref，守卫 step
  SHALL 点名 `WL_REF` 并 fail-closed；测试已覆盖。
- **Q：tag 形态的 checkout ref 是什么？**
  Resolved：resolve step 对 annotated tag 输出 `refs/tags/<tag>`；`actions/checkout`
  的 ref-helper 明确支持该前缀。不是把 tag object sha 交给 checkout（那与 #42 的
  uv 问题同源）。

## Open Questions

（无。可由代码 / 既有平台语义 / 测试定案；不需要用户额外拍板。）

## 风险

| 风险 | 等级 | 处置 |
|---|---|---|
| 每次 PR 多一次本仓 clone | medium | `fetch-depth: 1`、守卫后立即删除；未采用 sparse checkout 以免新增旋钮 |
| 跨仓 checkout 在 GHES / 私有 / 网络受限环境失败 | medium | 与既有「必须能访问 GitHub」能力边界同源；文档登记；失败是 fail-closed |
| `refs/tags/<tag>` 作为 checkout ref 未在真 CI 验证 | medium | 依赖 actions/checkout 的 ref-helper；PR 残余风险里如实登记 |
| 显式 `witnessloop-ref` 指到旧 ref，没有守卫脚本 | medium | 守卫 step 检查文件存在；缺失 ⇒ 点名 ref + fail-closed |
| 非 PR 事件下先做一次 clone 才拒绝 | low | 守卫在 caller 的重 checkout 之前；clone 是 `fetch-depth: 1` 的小仓 |
| 下游只认「base 解析失败」文案 | low | 新文案更明确；非 PR 仍是非 0，不改变「失败」语义 |

## User Confirmation

- **无 Open Question**。用户 2026-11-03 的任务书已给出：非 PR ⇒ `::error::` + 非 0；
  文案说清三件事；优先抽成可测脚本并由 gate.yml 调用；TDD、文档同步、check 绿、PR 不合并。
  本设计按该口径定案。
