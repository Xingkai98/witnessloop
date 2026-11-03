# Grill: gate-empty-diff-and-hints 设计追问

## Reviewer

- run id: `grill-reviewer-gate-empty-diff-and-hints-2026-11-03`
- 时间: 2026-11-03
- verdict: **可进入对抗验证**（frontier 已空；无 Open Question 需要用户拍板）。
- 审阅方式: 按 `templates/grill.md` 的 7 个维度逐项追问 `proposal.md` / `design.md`；
  只读仓内代码、文档与真实 git 行为，不读作者会话历史。
- ⚠️ 流程偏差（如实记录）：本报告的**文本产出**发生在实现与测试跑绿之后（见
  `tasks.md`「流程偏差」），但设计（`design.md` D1..D8）在写代码前已定稿；
  未在报告产出前伪造任何 manifest 或绿色 gate 结论。

## Confirmed Decisions

- **决策（需求对齐 · #45 的根因）**：零变更区间的假绿来自 `checkcmd.run` 在
  `changed_files` 返回空列表后没有分支，`_report` 把空 `findings` 统一当作「通过」。
  修法应是在 `changed_files` 之后、契约校验之前分流，而不是把空 diff 做成一条 finding。
  理由：读 `src/witnessloop/checkcmd.py:116-213` 与 `:478-501` 可确认；
  `targets=[]` / `findings=[]` 时必然走到 `if not findings: print("check：通过 ✓")`。
  来源: `grill-reviewer-gate-empty-diff-and-hints-2026-11-03`
- **决策（退出码 · 可区分但不破坏 CI）**：默认用新增 `EXIT_EMPTY=5`，`--allow-empty` 退 0。
  任何 `!= 0` 的 CI 判定仍然失败；只挡「误配 base/head 拿绿勾」，不改变「有变更时」的
  0/1/3 语义。
  理由：issue #45 明确允许「非 0 或可区分的退出码」；`docs/gate.md §6` 的既有码位
  （0/1/2/3/4）里 4 已属 guard 内部错误，5 是下一个不冲突的值；
  `entry.py` 只兜未预期异常（check 仍退 1），不与此码冲突。
  来源: `grill-reviewer-gate-empty-diff-and-hints-2026-11-03`
- **决策（输出语义 · 不冒充成功）**：默认输出必须包含「无变更」与「非通过」，且不得出现
  精确成功行 `check：通过 ✓`；`--allow-empty` 的输出必须写明「已按 --allow-empty 显式放行」
  与「本次没有校验任何内容」。
  理由：`tests/test_check_empty_diff.py` 用精确成功行缺席来钉住它；不能只查 `"通过"` 子串——
  「非通过」本身包含这两个字，会误伤。既有摘要子串 `0 个变更文件` / `0 个 change 目录`
  被 `tests/test_check_contract.py`、`tests/test_archive_awareness.py` 依赖，必须保留。
  来源: `grill-reviewer-gate-empty-diff-and-hints-2026-11-03`
- **决策（#46 分支判据 · 两向祖先）**：在「不是祖先」分支里再判
  `is_ancestor(checked_head, head_sha)`：真 ⇒ 证据是后代；假 ⇒ 旁支 / 不可达。
  进入该分支时二者不可能相等（相等会被前一条判为祖先），因此不存在第 0 种情况。
  理由：`gitutil.is_ancestor` 已是既有原语；两向判定比 `merge_base` 少一个状态，
  且「有 merge-base 却互不为祖先」本来就是旁支。
  来源: `grill-reviewer-gate-empty-diff-and-hints-2026-11-03`
- **决策（#46 提示 · 可执行且只读）**：后代 ⇒ 给
  `witnessloop check --base <实际 base> --head HEAD` 与 `--head <证据 sha>`；
  旁支 ⇒ 给 `manifest build --change <目录名> --stage <stage> --report <report_path> --base <实际 base>`
  与复核命令。`check` 不自动重建、不改写 `head_sha`。
  理由：issue #46 的期望原文即这两种行动；`stage` / `report_path` 就在当前 manifest 的
  `doc` 里，change 名取**该 manifest 所在目录名**（归档态也能被 `manifest build --change`
  精确解析，见 `docs/gate.md §3.2`）。值经 `shlex.quote` 后再拼命令，避免可写 manifest
  把提示变成注入面。
  来源: `grill-reviewer-gate-empty-diff-and-hints-2026-11-03`
- **决策（测试策略 · 真实 git 场景）**：#45 用 `--base HEAD --head HEAD` 的真实零 diff；
  #46 用两个真实拓扑：C1 内容 → C2 更晚内容 → manifest 绑 C2 → `--head C1`（后代），
  以及 main 上无关提交作为 manifest `head_sha`（旁支）。不 mock git。
  理由：`tests/conftest.py` 的仓 fixture 与 `tests/helpers.py` 已提供真 git 脚手架；
  仓库既有约定是「正确性一半在 git 语义上，不 mock」。
  来源: `grill-reviewer-gate-empty-diff-and-hints-2026-11-03`

## Code-Resolved Questions

- **Q：零变更时还要不要校验 policy / base？**
  Resolved：要。分流放在 policy 加载与 base 解析之后、`changed_files` 成功之后，
  保留 `EXIT_NOT_ONBOARDED(3)` 与 base 解析失败 `EXIT_FAIL(1)` 的既有 fail-closed 语义。
  证据：`checkcmd.run` 的现有顺序（policy → base → changed_files）。
- **Q：`--allow-empty` 在非空 diff 上要不要报错？**
  Resolved：不要。语义是「允许空区间通过」；非空时忽略，保持最小惊讶。
  已有回归 `test_allow_empty_does_not_change_a_nonempty_failure`。
- **Q：后代提示里的 base 用哪个？**
  Resolved：用**本次实际使用的** `base`（显式 `--base` 或 `resolve_base` 的结果），
  不硬编码 `main`；后代分支额外提供 `--head <证据 sha>` 以覆盖「HEAD 仍早于证据」。
- **Q：多 change / 归档 change 时 `--change` 填什么？**
  Resolved：填该 manifest 所在目录名。active 是 `<id>`，归档是归档目录名；
  `manifest build` 对两者都有精确解析路径。

## Open Questions

（无。设计内可定案的问题均由代码 / 真实 git 行为定案；不需要用户额外拍板。）

## 风险

| 风险 | 等级 | 处置 |
|---|---|---|
| 某接入方在空 diff 上跑 check（push 事件 / 手动 workflow），升级后由绿转红 | medium | 刻意行为；proposal「受影响调用方」列明；需要时显式 `--allow-empty` |
| 下游脚本硬编码 `== 1` 判失败，新增 5 被漏判 | medium | 文档写清 `!= 0` 才是失败；PR 描述列出受影响调用方 |
| 「非通过」含「通过」子串，下游日志 grep 误判 | low | 新测试钉精确成功行 `check：通过 ✓` 缺席；文档示例用完整行 |
| 提示里的命令被复制到错误目录 / 错误分支 | low | 命令带 `--base <实际 base>`；旁支分支明确要求「在交付 revision 上」重跑 |
| 可写 manifest 的 `stage` / `report_path` 进入提示文本 | low | `shlex.quote` 后再拼；只显示、不执行 |

## User Confirmation

- **Q1/Q2/Q3**：无 Open Question。用户 2026-11-03 的任务书已给出：
  零变更默认非 0 / 可区分退出码、`--allow-empty` 显式放行、两类提示分支与检查命令模板；
  本设计按该口径定案。
