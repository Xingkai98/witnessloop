# Proposal: gate-event-guard（reusable gate 只接受 pull_request；非 PR 事件给出决定性提示）

> 关联 issue：witnessloop **#48**。
> 一句话：`gate.yml` 在跑 `check` 之前先做**事件类型**守卫——非 `pull_request` 直接
> `::error::` + 非 0 退出，并解释「为什么非 PR 会红 / 怎么正确放行」；守卫逻辑抽成
> `scripts/gate-event-guard.sh`，由单测与行为测试覆盖。

## 背景（issue #48）

#45 之后，`witnessloop check` 对零变更区间已 fail-closed（`EXIT_EMPTY=5`）。
但 re-usable workflow `.github/workflows/gate.yml` **不校验调用事件类型**：

- 接入方把门禁挂到 `push` / `schedule` 上时，`github.base_ref` 为空；
  `gate.yml` 会算出 `BASE="origin/"`（或 base 与 head 是同一个提交）。
- 前一种形态下 `check` 报「无法解析 base ref：origin/」；后一种形态下走 #45 的
  `EXIT_EMPTY=5`。两者都是**正确的 fail-closed**，但对使用者呈现为一条
  「莫名其妙的红」——没有一句话说明「这个门禁本来就不是给 push 设计的」。

## 目标

1. `gate.yml` 在 `check` 步骤**之前**加决定性判断：
   - `github.event_name != 'pull_request'`（含空值）⇒ `::error::` + 非 0 退出；
   - 文案 SHALL 说清三件事：
     1. 本门禁按 **PR 区间**设计（base 是目标分支、head 是 PR head，区间里恒有变更）；
     2. `push` / `schedule` 触发时 base 与 head 通常是同一个提交，
        零变更按 issue #45 **不是通过**（`EXIT_EMPTY=5`）；
     3. 确实需要零变更放行时必须**显式** `--allow-empty`，**不要**为了抹红默认加上。
2. **守卫抽成可测脚本**：`scripts/gate-event-guard.sh`，读 `GITHUB_EVENT_NAME`；
   `gate.yml` 调它。不允许在 YAML 里写一段无法单测的裸 bash。
3. 单测覆盖：`pull_request` ⇒ 0；`push` / `schedule` / 空值 / 未定义 ⇒ 非 0，
   且 stderr 含上述关键提示。
4. 文档：
   - `docs/gate.md` 把「push 触发别用」从建议改成**解释**（为什么非 PR 会红、
     怎么正确放行）；
   - `README.md` 的 CI 段落同步一句。
5. 回归：**`check` 本体逻辑不变**；现有 adopter tests 与 PR 路径行为不变。

## 非目标

- **不**修改 `check` 的判定或退出码（#45 的语义保持）。
- **不**支持 `push` / `schedule` / `pull_request_target`；也不把 `--allow-empty`
  默认塞进门禁（那会抹掉「区间内有变更」这个前提）。
- **不**改变 caller workflow 的生成格式（`init` 的 caller 仍只触发 `pull_request`）。
- **不**重写包 ref 解析；守卫的 checkout 复用 `steps.wl-ref.outputs.ref`。
- **不**碰接入方仓或 `/home/shared/code/infra-learn-board`。

## 行为变更 / 受影响调用方

- **PR 路径不变**：守卫对 `pull_request` 直接放行；后续 checkout / setup-uv / check /
  adopter tests 的顺序与语义不变。
- **非 PR 路径**：现在会在 `check` 之前得到一条明确的 `::error::` 并以非 0 结束；
  不再表现为「base 解析失败」或零变更码 5 的隐晦红。adopter tests 也不会在守卫**失败**后
  继续跑（`if` 条件改为 `guard outcome != 'failure'`）。
- **新增一次 checkout**：re-usable workflow 的工作区里只有 caller 仓，看不到本仓
  `scripts/`；因此守卫前会按 `steps.wl-ref.outputs.ref` 把 `Xingkai98/witnessloop`
  检出到 `.witnessloop-gate`（`fetch-depth: 1`，守卫后立即删除）。这会给每次 PR
  增加一次小仓 clone；公共仓 / 默认 token 下可用，GHES / 私有 / 网络受限环境
  与既有「必须能访问 GitHub」的能力边界相同（见 §7）。
- **adopter tests 的 `if`**：从 `${{ !cancelled() }}` 变为
  `${{ !cancelled() && steps.wl-event-guard.outcome != 'failure' }}`——PR 上行为不变
  （`check` 失败时守卫仍是 success，测试照常跑；更早步骤失败导致守卫 skipped 时也不改变
  旧行为），只有守卫**明确失败**的非 PR 事件不再继续跑测试。

## 验收

- `scripts/gate-event-guard.sh` 单测：`pull_request` → 0；`push` / `schedule` / 空 /
  未定义 → 非 0 且 stderr 含 PR 区间、零变更非通过、`--allow-empty` 三组提示。
- `gate.yml` 结构测试：守卫 checkout / 守卫 step 都在 `witnessloop check` 之前；
  守卫 step 的 env 绑定 `github.event_name`；adopter tests 的 `if` 引用守卫结果。
- 行为测试：把守卫 step 的 `run:` 原文交给真 `sh` 跑（伪造 `.witnessloop-gate`），
  断言 PR 放行、非 PR 拒绝、且临时目录被清理。
- `PYTHONPATH=src python3 -m pytest -q` 全绿。
- `witnessloop check --base origin/main --head HEAD` 在本 PR 上绿（证据：原始输出）。
- 三份 stage manifest（grill / grill-adversarial / building）绑定最终内容 revision。
- PR 正文写 `fixes #48`；**不自行合并 main**。
