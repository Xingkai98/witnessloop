# Tasks: gate-empty-diff-and-hints

> 依据 `design.md`。原则：**TDD**（先让零变更 / 两种提示的测试在旧实现上红，再改实现）。
> 流程：立项 → grill → 设计对抗验证（跑到收敛，不停轮等用户）→ TDD → 独立 building 审阅 →
> 三份 manifest → `check` 绿 → PR（不自行合并 main）。

## A. 立项

- [x] A1 `proposal.md`：issue #45 / #46 的现象、根因、目标、非目标、行为变更与受影响调用方、验收。
- [x] A2 `design.md`：D1 零变更分流、D2 `EXIT_EMPTY=5` + `--allow-empty`、D3 输出语义、
      D4 单向祖先判定、D5/D6 两种提示、D7 不做的事、D8 测试与文档。
- [x] A3 `specs/check-noop-and-revision-hints/spec.md`：能力增量（零变更语义 / 退出码 /
      `--allow-empty` / 两类 revision 不匹配提示）。

## B. 设计阶段（grill + 对抗验证；不停轮等用户）

- [x] B1 grill：`reviews/grill-design.md`（Confirmed Decisions 6 条且带 `来源:`、
      Code-Resolved、Open Questions = 无、风险、User Confirmation）。
- [x] B2 设计对抗验证：`reviews/grill-adversarial.md`，R1 开批 7 条 → 全修 / 登记 →
      R2 无 medium+ ⇒ **PASS**。
- [x] B3 把必须修改回写 `design.md §4`（不停下来等用户确认；人工把关由 Hermes 事后复审）。

## C. TDD：先红

- [x] C1 新增 `tests/test_check_empty_diff.py`：
      - 零变更默认 `EXIT_EMPTY`、**不**打印 `check：通过 ✓`；
      - `--allow-empty` 退 0、输出写明「显式放行」且仍不冒充校验通过；
      - 非空 diff 时 `--allow-empty` 不改变既有结果。
      **红证据**：旧实现下 `tests/test_check_empty_diff.py` 3 条全部失败
      （`EXIT_EMPTY` 不存在 / `--allow-empty` 被 argparse 拒 / 零变更仍退 0）。
- [x] C2 新增 `tests/test_revision_mismatch_hints.py`：
      - 证据 revision 是**后代** ⇒ 「后代」+ `witnessloop check --base main --head HEAD`
        + `--head <证据 sha>`；
      - **旁支 / 不可达** ⇒ `manifest build --change … --stage … --report …` + 复核命令。
      **红证据**：旧实现下 2 条失败，stderr 只有「祖先——审阅的是别的 revision」。
- [x] C3 既有 `test_head_sha_must_be_an_ancestor_of_the_checked_head` 等保持绿
      （「祖先」子串不回退；全量 773 passed）。

## D. 实现

- [x] D1 `constants.EXIT_EMPTY = 5`（注释说明只用于 `check` 的零变更）。
- [x] D2 `cli.py`：`check` 增加 `--allow-empty`（help 写明只影响零变更）。
- [x] D3 `checkcmd.run`：`changed_files` 为空 ⇒ `_report_empty`；默认退 `EXIT_EMPTY`，
      `--allow-empty` 时打印显式放行并退 0；保留 `0 个变更文件` / `0 个 change 目录` 子串。
- [x] D4 `contract.SpanScope` 增加 `base_ref`；`checkcmd` 传入本次实际 base。
- [x] D5 `_check_git_span`：反向 `is_ancestor` 分「后代」与「旁支 / 不可达」；
      消息带 `change` / `stage` / `report_path` / `base_ref` 拼出的可执行命令。
      `validate_review_manifests` → `_validate_one` 透传 change 目录名。
- [x] D6 文案不出现误导性成功；默认无操作走 stderr，`--allow-empty` 走 stdout。

## E. 文档

- [x] E1 `docs/gate.md` §3：revision 不匹配的两种提示；§6：`check` 退出码表加 5。
- [x] E2 `README.md`：`check` 用法补 `--allow-empty` 与零变更语义。
- [x] E3 既有 `check`「通过」描述与新语义不冲突（成功行只在有变更且无 finding 时出现）。

## F. 实现后独立审阅

- [x] F1 building 审阅：逐条验证 `[x]`、跑测试、读 diff；产出 `reviews/building-review.md`。
- [x] F2 修复批次：无 medium+ ⇒ 无修复批次；low/nit 已登记。

## G. 证据 / 门禁 / PR

> G2/G3/G5/G6 是**内容提交之后**的交付步骤，故不在此文件里预先勾选——
> `tasks.md` 属于内容（被 manifest 的 `tasks_hash` 绑定），证据提交后再改会判 stale
> （`docs/gate.md §3.1`）。完成情况以 PR 正文与门禁输出为准。

- [x] G1 内容提交（实现 + 测试 + 文档 + change 文档；**不含** `reviews/` 证据）。
- [ ] G2 三份 manifest：`grill` / `grill-adversarial` / `building`，绑定内容提交的 revision。
- [ ] G3 证据提交（`reviews/**` + `workflow-events.jsonl`，如需要）。
- [x] G4 `.venv/bin/python -m pytest -q` 全绿（本机无 `uv`，用 venv 入口）。
- [ ] G5 `witnessloop check --base origin/main --head HEAD` 绿（记录原始输出）。
- [ ] G6 分支 `fix/gate-empty-diff-and-hints` 推送 origin，`gh pr create`
      正文写 `fixes #45, fixes #46`；**不自行合并 main**。

## 审阅修复

（building 审阅的修复项收敛后回写。）

## 流程偏差（如实记录）

设计（`design.md`）在写代码前定稿；但 grill / 对抗验证的**报告文本**产出在实现与测试
跑绿之后。未在报告产出前伪造任何 manifest / gate 结论；三份 manifest 均在内容提交后、
证据提交前由 `manifest build` 按真实 HEAD 产出。人工把关由 Hermes 事后复审。
