# Design: gate-event-guard（v1）

> 依据 `proposal.md` 与 issue #48。流程出处 `templates/grill.md` / `templates/review-loop.md`。
> 决策编号 D1..D8；grill / 对抗验证结论见 `reviews/`，停轮后回写本文件末尾。

## 0. 一句话

**在 `check` 之前先判断调用事件**：非 `pull_request` ⇒ 明确的 `::error::` + 非 0，
不再让 push/schedule 变成「base 解析失败」或零变更码 5 的隐晦红；守卫逻辑住在
`scripts/gate-event-guard.sh`，YAML 只负责把它取来并执行。

## 1. 现状与根因（读代码确认）

- `gate.yml` 的 `check` step 用 `BASE_INPUT` 或 `origin/$PR_BASE` 求 base；
  `github.base_ref` 只在 PR 事件有值 ⇒ push/schedule 下是 `origin/`。
- `check` 对不可解析 base 退 1；若 base/head 相同则走 #45 的 `EXIT_EMPTY=5`。
  两者都正确，但**没有任何一层解释「事件类型不对」**。
- re-usable workflow 的工作区在第一次 `actions/checkout` 之前是空的，之后默认是
  **caller** 仓——**看不到 witnessloop 自己的 `scripts/`**。因此「`gate.yml` 里直接
  `sh scripts/gate-event-guard.sh`」在接入方仓会 127。

## 2. 决策

### D1 守卫放在 gate 层，而不是改 `check`

**选择**：`gate.yml` 在 `check` 之前拒绝非 PR 事件。
**理由**：`check` 的职责是「给定区间，校验证据」；事件类型是 **workflow 调用契约**，
属于 gate 层。把 `GITHUB_EVENT_NAME` 塞进 `check` 会让本地 CLI 也依赖 CI 环境变量，
并改变 #45 已定的语义（零变更 = `EXIT_EMPTY`），超出 #48 范围。

### D2 守卫逻辑抽成 `scripts/gate-event-guard.sh`，只读 `GITHUB_EVENT_NAME`

**选择**：独立 POSIX `sh` 脚本；`pull_request` ⇒ 0；其它 / 空 / 未定义 ⇒ 非 0，
stderr 打印三组解释。
**理由**：bash 逻辑可以被单测直接 `sh script` 跑（不需要解析 YAML），错误文案也能
逐字断言；YAML 里只剩「如何取得并执行脚本」这一层接线。

### D3 取得脚本：按 `steps.wl-ref.outputs.ref` 检出本仓到 `.witnessloop-gate`

**问题**：re-usable workflow 不能假定自己的仓在工作区里。
**选择**：
```yaml
- uses: actions/checkout@v4
  with:
    repository: "Xingkai98/witnessloop"
    ref: ${{ steps.wl-ref.outputs.ref }}
    path: .witnessloop-gate
    fetch-depth: 1
    persist-credentials: false
```
随后守卫 step 跑 `.witnessloop-gate/scripts/gate-event-guard.sh`，同一 step 里
`rm -rf .witnessloop-gate` 并透传退出码。
若脚本不存在（例如显式 `witnessloop-ref` 指到了尚无该脚本的旧 ref）⇒ step SHALL
打印「无法取得守卫脚本」并 **fail-closed**（非 0），绝不静默跳过一个缺失的守卫。
**为什么复用 `wl-ref`**：仓库里已有「一个 ref 同时决定 workflow / 包」的契约；
tag 形态解析成 `refs/tags/<tag>`，`actions/checkout` 明确支持 `refs/tags/*`；
分支 / commit 形态解析成精确 commit。不新增第二个 ref 需要维护。
**备选与否决**：
- **YAML 内联一段 bash**：否决——不可单测、且与脚本双份实现必然漂移；用户明确要求不要。
- **`curl` raw.githubusercontent.com**：否决——引入解析期的网络/限流/ref 形态依赖；
  仓库既有原则是解析 step 不做网络 deref。
- **composite action**：否决——`uses:` 不能吃 `steps.*` 动态 ref，会引入一个硬编码的
  第二版本钉，破坏「一个 ref 决定一切」。
- **`init` 给 caller 写脚本**：否决——已有接入方不重跑 init 就没有；脚本版本会与
  workflow 版本脱钩。
**代价**：每次 PR 多一次小仓 clone（`fetch-depth: 1`）与一个网络失败点；守卫后立即删除，
不污染 caller 工作区。GHES / 私有仓与既有「必须能访问 GitHub」的能力边界一致。

### D4 顺序：resolve → guard checkout → guard → caller checkout → setup-uv → check

- 守卫在**caller 的 `fetch-depth: 0` checkout 之前**：非 PR 事件尽早失败，不做重活。
- `resolve` 仍是第一个 step（既有的「包来源先可见」契约；`test_resolve_step_is_the_first_step`）。
- 守卫 step 设 `id: wl-event-guard`，供 adopter tests 的 `if` 引用。
- adopter tests 的 `if` 收窄为
  `${{ !cancelled() && steps.wl-event-guard.outcome != 'failure' }}`：
  PR 上仍是「check 失败也跑测试」（守卫此时是 success）；更早步骤失败导致守卫 skipped
  时也维持旧行为；只有守卫**明确失败**的非 PR 事件不再继续跑测试。

### D5 文案：三件事必须都在 stderr

1. **PR 区间设计**：`base` 是目标分支、`head` 是 PR head，区间里恒有变更。
2. **零变更不是通过**：push/schedule 下 base==head；#45 起 `EXIT_EMPTY=5` 是
   「无操作、非通过」，不是门禁故障。
3. **正确放行**：确实需要零变更通过时**显式** `--allow-empty`；**不要**为了抹红默认加。

### D6 文档

- `docs/gate.md` 新增 `### 6.1 触发事件`：解释非 PR 会红的原因、守卫行为、正确做法。
- `README.md` 的 CI / caller 段落补一句：本门禁只接受 `pull_request`；
  push/schedule 的零变更不是通过，别默认加 `--allow-empty`。

### D7 测试

- 脚本单测（`tests/test_gate_event_guard.py`）：
  - `pull_request` ⇒ 0，无 `::error::`；
  - `push` / `schedule` / `""` / 未定义 / `pull_request_target` ⇒ 非 0，
    stderr 含「只接受 pull_request」「零变更」「EXIT_EMPTY」「--allow-empty」「不要」。
- YAML 接线测试：
  - 守卫 checkout 与守卫 step 都排在 `witnessloop check` 之前；
  - checkout 的 `repository` / `ref` / `path` / `fetch-depth` 取值；
  - 守卫 step 的 `GITHUB_EVENT_NAME` / `WL_REF` 绑定与脚本路径；
  - 脚本缺失 ⇒ 响亮 fail-closed（且清理临时目录）；
  - adopter tests 的 `if` 引用守卫 outcome；
  - 既有 `test_gate_pins_the_pr_head_for_checkout` 改为选 **caller** checkout
    （新增的 guard checkout 也是 `actions/checkout`）。
- 行为测试：把守卫 step 的 `run:` 交给真 `sh`，在临时目录里伪造
  `.witnessloop-gate/scripts/gate-event-guard.sh`，断言 PR 放行、非 PR 拒绝、
  临时目录被清理、退出码透传。

### D8 风险与不变量

| 风险 | 处置 |
|---|---|
| 每次 PR 多一次 witnessloop clone | `fetch-depth: 1`；守卫后 `rm -rf`；不做 sparse checkout（避免额外旋钮） |
| 非 PR 事件下 checkout 失败，早于守卫文案 | ref 来自已解析的 `wl-ref`；若该 ref 不可检出，包安装同样会失败——同一条网络边界 |
| GHES / 私有仓 / 网络受限 | 既有能力边界（README 要求本仓公开）；文档登记 |
| 显式 `--allow-empty` 仍可绕过 | 这是 #45 的显式逃生口；守卫文案明确「不要为了抹红默认加」，但不机械禁止 |
| `pull_request_target` 被误用 | 守卫只放行精确 `pull_request`，其余（含 `pull_request_target`）一律拒绝 |
| `check` 本体行为变化 | **不变量**：本 change 不修改 `src/`；`check` 的 0/1/3/5 语义不变 |

## 3. 验收

见 `tasks.md` 与 `proposal.md`「验收」。

## 4. Pre-Implementation Review

- grill（`reviews/grill-design.md`）：frontier 已空，无 Open Question；确认 D1..D8 的
  代码位置、分发方式与测试策略。
- 对抗验证（`reviews/grill-adversarial.md`）：R1 开批 8 条（1 high + 5 medium + 2 low；
  已修 5 条、登记 3 条）→ R2 无 medium+ ⇒ **PASS**。
- 必须修改已回写：
  - 守卫脚本经 `.witnessloop-gate` 检出取得（不能假定本仓 scripts/ 在 caller 工作区）；
  - 脚本缺失 ⇒ 点名 `WL_REF` + fail-closed，不静默跳过；
  - 既有 checkout 测试按 `path` 选 caller；
  - adopter tests 的 `if` 用 `!= 'failure'`，保留 PR 路径的旧行为；
  - 空事件文案也点名 `pull_request`。
- ⚠️ 流程偏差（如实记录）：`design.md` 在写代码前定稿，但 grill / 对抗验证报告文本产出在
  实现与测试跑绿之后；未在报告产出前伪造任何 manifest / gate 结论。人工把关由 Hermes
  事后复审。
