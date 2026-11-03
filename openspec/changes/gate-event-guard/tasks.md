# Tasks: gate-event-guard

> 依据 `design.md`。原则：**TDD**（先写会红的守卫脚本 / YAML 接线测试，再实现）。
> 流程：立项 → grill → 设计对抗验证（跑到收敛，不停轮等用户）→ TDD → 独立 building 审阅 →
> 三份 manifest → `check` 绿 → PR（不自行合并 main）。

## A. 立项

- [x] A1 `proposal.md`：issue #48 的现象 / 根因 / 目标 / 非目标 / 行为变更 / 验收。
- [x] A2 `design.md`：D1 守卫层级、D2 独立脚本、D3 脚本取得方式、D4 顺序与 adopter tests
      `if`、D5 文案、D6 文档、D7 测试、D8 风险。
- [x] A3 `specs/gate-event-guard/spec.md`：事件判定 / 文案 / 文档的可验证要求。

## B. 设计阶段（grill + 对抗验证；不停轮等用户）

- [x] B1 grill：`reviews/grill-design.md`（Confirmed Decisions ≥3 带 `来源:`、
      Code-Resolved、Open Questions、风险、User Confirmation）。
- [x] B2 设计对抗验证：`reviews/grill-adversarial.md`，逐条证伪 D1..D8；无 medium+ 收口。
- [x] B3 把必须修改回写 `design.md §4`（不停轮等用户；人工把关由 Hermes 事后复审）。

## C. TDD：先红

- [x] C1 新增 `tests/test_gate_event_guard.py`：
      - `scripts/gate-event-guard.sh` 单测：`pull_request` → 0；`push` / `schedule` /
        `""` / 未定义 / `pull_request_target` → 非 0 + 三组提示；
      - YAML 接线：guard checkout + guard step 在 `witnessloop check` 之前；
        checkout 的 repository/ref/path/fetch-depth；guard env 与脚本路径；
        adopter tests 的 `if` 引用 guard outcome；
      - 行为：把 guard step 的 `run:` 交真 `sh`，断言放行 / 拒绝 / 清理。
      先跑：脚本不存在 / YAML 无守卫 ⇒ 红。
- [x] C2 更新既有 `tests/test_gate_workflow.py`：
      - `test_gate_pins_the_pr_head_for_checkout` 选 **caller** checkout（新增的 guard
        checkout 也是 `actions/checkout`）；
      - adopter tests 的 `if` 断言改为含 `steps.wl-event-guard.outcome != 'failure'`。
- [x] C3 既有 resolve / adopter tests / PR 路径用例保持绿。

## D. 实现

- [x] D1 新增 `scripts/gate-event-guard.sh`（POSIX sh，读 `GITHUB_EVENT_NAME`）。
- [x] D2 `gate.yml`：
      - resolve 之后加 guard 脚本 checkout（`repository` / `ref: steps.wl-ref.outputs.ref` /
        `path: .witnessloop-gate` / `fetch-depth: 1` / `persist-credentials: false`）；
      - 加 `gate event guard` step（`id: wl-event-guard`），执行脚本、删除临时目录、
        透传退出码；脚本缺失 ⇒ 点名 `WL_REF` 并 fail-closed；
      - adopter tests 的 `if` 收窄到 `guard outcome != 'failure'`。
- [x] D3 守卫 step 在 caller checkout / check 之前；resolve 仍是第一个 step。
- [x] D4 文案包含 PR 区间、零变更非通过、显式 `--allow-empty` 三件事。

## E. 文档

- [x] E1 `docs/gate.md`：`### 6.1 触发事件：本门禁只接受 pull_request`（解释原因与正确放行）。
- [x] E2 `README.md` CI / caller 段落同步一句。
- [x] E3 文档测试断言两份文档都提到 `pull_request` + `--allow-empty`。

## F. 实现后独立审阅

- [x] F1 building 审阅：逐条验证 `[x]`、跑测试、读 diff；产出 `reviews/building-review.md`。
- [x] F2 修复批次：无 medium+ ⇒ 无修复批次；low/nit 已登记。

## G. 证据 / 门禁 / PR

> G2/G3/G5/G6 是**内容提交之后**的交付步骤，故不在此文件里预先勾选——
> `tasks.md` 属于内容（被 manifest 的 `tasks_hash` 绑定），证据提交后再改会判 stale
> （`docs/gate.md §3.1`）。完成情况以 PR 正文与门禁输出为准。

- [x] G1 内容提交（脚本 + gate.yml + 测试 + 文档 + change 文档；**不含** `reviews/` 证据）。
- [ ] G2 三份 manifest：`grill` / `grill-adversarial` / `building`，绑定内容提交的 revision。
- [ ] G3 证据提交（`reviews/**`）。
- [x] G4 `PYTHONPATH=src python3 -m pytest -q` 全绿（788 passed）。
- [ ] G5 `witnessloop check --base origin/main --head HEAD` 绿（记录原始输出）。
- [ ] G6 分支 `fix/gate-event-guard` 推送 origin，`gh pr create` 正文写 `fixes #48`；
      **不自行合并 main**。

## 审阅修复

（grill / 对抗验证 / building 的修复项收敛后回写。）

## 流程偏差

（如有，如实记录。）
