# Building Review: gate-empty-diff-and-hints

## Reviewer

- run id: `building-reviewer-gate-empty-diff-and-hints-2026-11-03`
- 对象：`tasks.md` 的 A..E、实际代码 / 测试 / 文档 diff、`proposal.md` / `design.md` / spec
- 方法：逐条 `[x]` 读代码确认；跑 `.venv/bin/python -m pytest -q`；手工复现
  `check --base HEAD --head HEAD` 与 `--allow-empty`。
- verdict: **PASS**（无 medium+；4 条 low/nit 登记，不阻塞）。
- 诚实边界：同一工作流内的自审文本，不是独立模型 run；机械门禁只保证证据存在与
  revision 绑定（`docs/gate.md §3`）。

## 任务逐项验证

| 任务 | 结论 | 证据（读代码 / 实测） |
|---|---|---|
| A1 proposal 覆盖 #45/#46、非目标、受影响调用方 | ✅ | `proposal.md`「背景」「目标」「非目标」「行为变更 / 受影响调用方」 |
| A2 design D1..D8 具体、有备选/理由 | ✅ | `design.md` §2；每项含选择与代价 |
| A3 spec 能力增量与 Scenario | ✅ | `specs/check-noop-and-revision-hints/spec.md` 3 个 Requirement + 6 个 Scenario |
| B1/B2/B3 设计与对抗报告 | ✅ | `reviews/grill-design.md`（6 条 Confirmed、Open Questions=无）、`reviews/grill-adversarial.md`（R1 7 条 → R2 PASS）、`design.md §4` |
| C1 零变更测试先红 | ✅ | `tests/test_check_empty_diff.py:20,38,59`；红阶段 3 failed（旧实现） |
| C2 两种提示测试先红 | ✅ | `tests/test_revision_mismatch_hints.py:21,40`；红阶段 2 failed，旧文案只有「祖先」 |
| C3 既有「祖先」语义不回退 | ✅ | `tests/test_check_manifest.py::test_head_sha_must_be_an_ancestor_of_the_checked_head` 全绿 |
| D1 `EXIT_EMPTY=5` | ✅ | `src/witnessloop/constants.py:132`；新测试断言 `!= 0` 且 `!= EXIT_FAIL` |
| D2 `--allow-empty` | ✅ | `src/witnessloop/cli.py:109`；help 明说只影响零变更 |
| D3 空 diff 分流 + 输出 | ✅ | `src/witnessloop/checkcmd.py:131-136`、`_report_empty:489-520`；保留两个摘要子串 |
| D4 `SpanScope.base_ref` | ✅ | `contract.py:556`；`checkcmd.py` 传本次 `base` |
| D5 两向祖先 + 命令模板 | ✅ | `contract._revision_mismatch_hint:753-799`；`is_ancestor` 反向判定；`shlex.quote` |
| D6 文案语义 | ✅ | 默认无操作走 stderr；`--allow-empty` 走 stdout；无 `check：通过 ✓` |
| E1/E2/E3 文档 | ✅ | `docs/gate.md §3 / §6`、`README.md`「零变更不是通过」表 |
| F1/F2 本审阅 | ✅ | 本文件 |

## 实测

```
$ .venv/bin/python -m pytest -q
773 passed in 36.71s

$ .venv/bin/witnessloop check --base HEAD --head HEAD
check：基线 HEAD...HEAD，0 个变更文件，0 个 change 目录
check：无变更，跳过（非通过）✗ —— base 与 head 之间没有任何差异，本次没有校验任何内容
  这是无操作，不是通过。CI / 脚本若确实预期零变更，显式加 --allow-empty 放行。
rc=5

$ .venv/bin/witnessloop check --base HEAD --head HEAD --allow-empty
check：基线 HEAD...HEAD，0 个变更文件，0 个 change 目录
check：无变更；已按 --allow-empty 显式放行（退出码 0）——本次没有校验任何内容。
rc=0
```

## 修复批次

本审阅未发现 medium+，因此没有 `CHANGES_REQUESTED` 批次；以下低项登记。

## Low / Nit 登记

| 编号 | 级别 | 说明 | 处置 |
|---|---|---|---|
| L1 | low | 退出码 5 需要下游把「失败」写成 `!= 0`；硬编码 `== 1` 的脚本会漏判 | 文档 / README / proposal 已列受影响调用方；登记不修（保留 #45 要求的可区分性） |
| L2 | low | `--allow-empty` 在非空 diff 上被静默忽略 | help 与 README 写明「只影响零变更」；回归测试钉住非空失败不受影响 |
| L3 | low | 后代提示的 `--base <base_ref> --head HEAD` 在 `base_ref` 恰为 HEAD 时会退化为零变更 | 同时给 `--head <证据 sha>` 的第二条命令；不猜分支名 |
| L4 | nit | `_revision_mismatch_hint` 在每次失败时多跑一次 `merge-base --is-ancestor` | 可接受：只在失败诊断路径，调用次数等于不合格 manifest 数 |

## 结论

**PASS**。tasks A..E 的 `[x]` 均能在代码 / 测试 / 文档中找到对应实现；
全量 773 passed；零变更与 `--allow-empty` 的输出与退出码符合 issue #45；
两种 revision 不匹配提示符合 issue #46。可以进入证据提交与 PR。
