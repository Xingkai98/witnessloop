# gate-event-guard（增补）— reusable gate 只接受 pull_request

> 本 change 只改 `gate.yml` 的**事件守卫**与文档；`witnessloop check` 本体不变。
> 关联 issue：witnessloop **#48**。

## Requirement: 守卫 SHALL 在 check 之前拒绝非 pull_request 事件

`gate.yml` SHALL 在 `witnessloop check` 步骤**之前**执行事件守卫：

1. `github.event_name == 'pull_request'` ⇒ SHALL 放行（退出码 0），继续后续步骤。
2. 其它值（`push` / `schedule` / `pull_request_target` …）或空值 ⇒ SHALL 输出
   `::error::` 并以**非 0** 退出；`check` 步骤 SHALL NOT 继续。
3. 守卫失败时 adopter tests SHALL NOT 继续（其 `if` 条件 SHALL 引用守卫 outcome）。
4. 守卫逻辑 SHALL 住在一个可单测的脚本里（`scripts/gate-event-guard.sh`），
   读 `GITHUB_EVENT_NAME`；`gate.yml` SHALL NOT 内联一段无法单测的裸 bash 判断。

### Scenario: pull_request（正常路径）
- **Given** `GITHUB_EVENT_NAME=pull_request`
- **When** 运行守卫脚本 / gate 的守卫 step
- **Then** 退出码 SHALL 为 0；stderr SHALL NOT 含 `::error::`
- **And** gate 后续步骤（checkout / check / adopter tests）行为与改动前一致

### Scenario: push / schedule
- **Given** `GITHUB_EVENT_NAME=push` 或 `schedule`
- **When** 运行守卫
- **Then** 退出码 SHALL 非 0
- **And** stderr SHALL 含：
  - 本门禁只接受 `pull_request`（点名当前事件）；
  - 本门禁按 PR 区间设计（base 是目标分支、head 是 PR head，恒有变更）；
  - 零变更按 issue #45 是「非通过」（`EXIT_EMPTY=5`），不是门禁故障；
  - 确实需要放行时显式 `--allow-empty`，**不要**为了抹红默认加。

### Scenario: GITHUB_EVENT_NAME 缺失
- **Given** `GITHUB_EVENT_NAME` 未定义或为空
- **When** 运行守卫
- **Then** 退出码 SHALL 非 0
- **And** stderr SHALL 点名 `GITHUB_EVENT_NAME` 无法判断事件类型

### Scenario: 守卫取得脚本的方式
- **Given** re-usable workflow 的工作区里只有 caller 仓
- **When** gate 运行守卫
- **Then** gate SHALL 按 `steps.wl-ref.outputs.ref` 检出本仓到临时子目录并执行
  `scripts/gate-event-guard.sh`
- **And** SHALL 在守卫结束后删除该子目录
- **And** 该 checkout SHALL 使用 `fetch-depth: 1` 与 `persist-credentials: false`

## Requirement: 文档 SHALL 解释非 PR 触发为何红、怎么正确放行

`docs/gate.md` SHALL 说明：

1. re-usable gate 按 PR 区间设计；`push` / `schedule` 下 `github.base_ref` 为空，
   base 可能不可解析或与 head 相同；
2. 零变更按 #45 是 `EXIT_EMPTY(5)`（无操作、非通过），不是「校验通过」；
3. 正确做法是把门禁挂在 `pull_request` 上；确实需要零变更放行时才显式
   `--allow-empty`，不要默认加。

`README.md` 的 CI / caller 段落 SHALL 同步一句同口径说明。

### Scenario: 文档可机械校验
- **Given** `docs/gate.md` 与 `README.md`
- **When** 运行 `tests/test_gate_event_guard.py`
- **Then** 两份文档 SHALL 同时出现 `pull_request` 与 `--allow-empty` 的说明
  （防止只改一处）
