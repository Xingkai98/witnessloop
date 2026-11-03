# Grill-Adversarial: gate-empty-diff-and-hints

## Reviewer

- run id: `grill-adversarial-gate-empty-diff-and-hints-2026-11-03`
- 对象: `design.md` D1..D8、`proposal.md` 的验收 / 非目标、`specs/check-noop-and-revision-hints/spec.md`
- 方法: 逐条**证伪**（不是复述）；每条问题给出可复现的输入 / 现有代码位置 / 期望行为。
- 最终 verdict: **PASS**（第 2 轮空批；无残留 medium+）。
- 诚实边界：本报告是同一工作流内的自审文本，**不是**独立模型 run；机械门禁只保证
  「证据存在 + 绑定 revision」，不证明审阅者身份（同 `docs/gate.md §3` 的既有口径）。

## 第 1 轮（开批）

### R1-1（medium，已修）零变更分流的位置会绕过既有 fail-closed 语义

- **证伪尝试**：把分流放到 `run()` 开头（`changed_files` 之前）最省事。
- **反例**：未接入的仓 `check --base HEAD --head HEAD` 会从 `EXIT_NOT_ONBOARDED(3)` 变成
  `EXIT_EMPTY(5)`；base 不可解析也会从 1 变成 5。这会让「未接入」不再响亮。
- **裁定**：分流必须在 `policy` 加载、base 解析、`changed_files` 成功**之后**。
- **落点**：`checkcmd.run` 的空列表分支；`tests/test_check_onboarding.py` 仍绿。

### R1-2（medium，已修）「不打印通过」不能只查 `"通过"` 子串

- **证伪尝试**：新测试若写 `assert "通过" not in out`，而默认文案是「非通过」，
  测试会因**正确的实现**变红（或迫使实现回避准确措辞）。
- **裁定**：测试钉**精确成功行** `check：通过 ✓` 缺席；允许「非通过」出现在无操作文案里。
- **落点**：`tests/test_check_empty_diff.py`。

### R1-3（medium，已修）既有 4 条测试依赖「零变更退 0」

- **证伪尝试**：只改实现、不跑全量测试。全量结果显示
  `test_wired_execution_point_passes`、`test_truthy_but_non_boolean_disabled_still_gets_judged`、
  `test_opt_out_policy_is_not_judged`、`test_check_prints_the_line_even_from_source` 变红，
  因为它们在空 diff 上调用 `check`。
- **裁定**：
  - 前三条是「执行点判定」的测试，必须给**真实非空 diff**，否则新语义下它们根本走不到
    被测分支（用 `--allow-empty` 混过去会让测试变成空真）。
  - 第四条只关心包来源自报行，给一个已提交的纯文档 diff 即可。
- **落点**：`tests/test_adopter_tests.py`、`tests/test_check_package_ref.py`；
  修复后全量 `773 passed`。

### R1-4（medium，已修）后代提示的 `--head HEAD` 可能仍是零变更

- **证伪尝试**：用户用 `--base <某个较旧提交> --head C1` 触发后代分支时，
  `--base <那个较旧提交> --head HEAD` 是正常的；但若 base 恰好也是 HEAD（`--base HEAD --head C1`），
  提示会退化成 `--base HEAD --head HEAD`（新的零变更码 5）。
- **裁定**：后代分支同时给出**第二条**精确命令 `--head <证据 sha>`；即使第一条不适用，
  使用者也有能包含证据 revision 的区间。不在提示里猜测分支名。
- **落点**：`contract._revision_mismatch_hint`；`tests/test_revision_mismatch_hints.py`
  同时断言两条命令。

### R1-5（low，已修）可写 manifest 的字段进入可复制命令

- **证伪尝试**：`stage` / `report_path` 是 agent 可写的 JSON；含引号、分号、换行时，
  直接拼进提示会诱导复制执行一条被篡改的命令。
- **裁定**：进入命令模板的值用 `shlex.quote`；简单值保持原样（模板仍可读）。
  该提示只显示、不执行；`check` 仍只读。
- **落点**：`contract._revision_mismatch_hint`。

### R1-6（low，登记不修）退出码 5 与脚本硬编码 `== 1`

- **证伪尝试**：某脚本把「失败」定义为 `rc == 1`；零变更现在退 5，会被当成成功。
- **裁定**：这是新增可区分码的已知代价。文档与 README 明确「`!= 0` 才是失败」；
  proposal 的「受影响调用方」一节列出。为保持 #45 要求的可区分性，不把 5 改成 1。

### R1-7（low，登记不修）`--allow-empty` 在非空 diff 上被忽略

- **证伪尝试**：用户可能以为该 flag 会放宽某些校验。
- **裁定**：help 与 README 写明它只影响**零变更**；回归测试钉住非空失败不受影响。
  报错反而会增加不必要的用法分支。

## 第 2 轮（验证修复，只做确认）

- R1-1：分流位置在 `checkcmd.run` 的 `changed_files` 之后；onboarding / base 失败测试仍绿。
- R1-2：新测试断言 `check：通过 ✓` 缺席，未使用 `"通过" not in text`。
- R1-3：4 条既有测试改为带真实 diff；全量 773 passed。
- R1-4：后代提示同时含 `--head HEAD` 与 `--head <证据 sha>` 两条命令。
- R1-5：`shlex.quote` 已加；简单值输出未变（测试仍断言 `--change add-x` 等）。
- **新问题**：无 medium+；R1-6 / R1-7 为已登记的 low，不阻塞。

## 结论

**PASS**。无残留 medium+；D1..D8 的实现与测试可相互印证。实现后仍需 building 审阅
（独立于本报告）确认 `tasks.md` 的每一 `[x]` 都真实落地。
