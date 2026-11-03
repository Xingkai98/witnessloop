# Building Review: gate-event-guard

## Reviewer

- run id: `building-reviewer-gate-event-guard-2026-11-03`
- 对象：`tasks.md` 的 A..E、`scripts/gate-event-guard.sh`、`gate.yml`、测试与文档 diff
- 方法：逐条 `[x]` 读代码确认；跑 `PYTHONPATH=src python3 -m pytest -q`；
  把守卫 step 的 `run:` 交真 `sh` 跑（PR / push / 脚本缺失三种输入）；解析 YAML 看 step 顺序。
- verdict: **PASS**（无 medium+；4 条 low/nit 登记）。
- 诚实边界：同一工作流内的自审文本，不是独立模型 run；机械门禁只保证证据存在与
  revision 绑定（`docs/gate.md §3`）。

## 任务逐项验证

| 任务 | 结论 | 证据 |
|---|---|---|
| A1/A2/A3 立项文档与 spec | ✅ | `proposal.md` / `design.md` / `specs/gate-event-guard/spec.md` |
| B1/B2/B3 设计与对抗 | ✅ | `reviews/grill-design.md`（6 条 Confirmed、Open Questions=无）、`reviews/grill-adversarial.md`（R1 8 条 → R2 PASS）、`design.md §4` |
| C1 守卫测试 | ✅ | `tests/test_gate_event_guard.py:49,54,62,73,115,129,140,150,183,190,199,223`；红阶段 15 failed |
| C2 既有测试适配 | ✅ | `tests/test_gate_workflow.py` 按 `path` 选 caller checkout；adopter tests `if` 断言 `!= 'failure'` |
| C3 既有语义 | ✅ | 全量 `788 passed`；resolve / adopter / PR 路径用例未回退 |
| D1 独立脚本 | ✅ | `scripts/gate-event-guard.sh:1-36`（POSIX sh，读 `GITHUB_EVENT_NAME`） |
| D2 gate.yml 接线 | ✅ | `gate.yml:174-208`（guard checkout、guard step、缺失脚本 fail-closed） |
| D3 顺序 | ✅ | 解析 YAML：`wl-ref` → guard checkout → guard → caller checkout → setup-uv → check → adopter tests；`wl-ref` 仍是第一个 step |
| D4 三件事文案 | ✅ | `scripts/gate-event-guard.sh:19-34`：PR 区间 / 零变更 `EXIT_EMPTY=5` / 显式 `--allow-empty` 且「不要」默认加 |
| E1 docs/gate.md §6.1 | ✅ | `docs/gate.md:570` 起：原因、守卫行为、正确做法 |
| E2 README | ✅ | `README.md:199` 起：只接受 `pull_request`、零变更不是通过、别默认加 `--allow-empty` |
| E3 文档测试 | ✅ | `tests/test_gate_event_guard.py:223` |

## 实测

```
$ PYTHONPATH=src python3 -m pytest -q
788 passed in 35.62s
```

行为级（测试内）：
- `GITHUB_EVENT_NAME=pull_request` ⇒ guard step 退 0，`.witnessloop-gate` 被删除；
- `push` ⇒ 非 0，stderr 有 `::error::` 与「零变更」，临时目录被删除；
- 脚本缺失 ⇒ 非 0，stderr 点名「无法取得守卫脚本」，临时目录被删除。

## 修复批次

本审阅未发现 medium+，无 `CHANGES_REQUESTED` 批次；以下低项登记。

## Low / Nit 登记

| 编号 | 级别 | 说明 | 处置 |
|---|---|---|---|
| L1 | low | 每次 PR 多一次 `Xingkai98/witnessloop` 的 `fetch-depth: 1` clone | 守卫后在 step 内 `rm -rf`；不采用 sparse checkout（少一个旋钮）；登记 |
| L2 | low | `refs/tags/<tag>` 作为 `actions/checkout` 的 ref 未在本环境真 CI 验证 | 依赖 ref-helper 的 `refs/tags/*` 支持；PR 残余风险登记，发布后由真实 tag 触发验证 |
| L3 | low | `scripts/**` 不在 `policy.require_change_for`，未来改守卫脚本不会被机械要求挂 change | 本 PR 自带 change；登记为后续 policy 取舍，不在本 change 扩大范围 |
| L4 | nit | 文档测试用关键词（`pull_request` / `零变更` / `--allow-empty`）而非整句 | 刻意：文案可读性优先，避免一改措辞就红；行为断言在脚本测试里 |

## 结论

**PASS**。tasks A..E 的 `[x]` 均能在代码 / 测试 / 文档中找到对应实现；
全量 788 passed；`check` 本体未改动（`src/` 零 diff）；事件守卫、缺失脚本 fail-closed、
adopter tests 条件与文档均符合 issue #48。可以进入证据提交与 PR。
