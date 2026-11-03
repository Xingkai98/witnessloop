# Grill-Adversarial: gate-event-guard

## Reviewer

- run id: `grill-adversarial-gate-event-guard-2026-11-03`
- 对象: `design.md` D1..D8、`proposal.md` 验收 / 非目标、`specs/gate-event-guard/spec.md`
- 方法: 逐条**证伪**；每条给出可复现的输入 / 现有代码位置 / 期望行为。
- 最终 verdict: **PASS**（第 2 轮空批；无残留 medium+）。
- 诚实边界：同一工作流内的自审文本，**不是**独立模型 run；机械门禁只保证证据存在 +
  绑定 revision，不证明审阅者身份（同 `docs/gate.md §3`）。

## 第 1 轮（开批）

### R1-1（high，已修）reusable workflow 看不到本仓 `scripts/`

- **证伪尝试**：按直觉在 gate.yml 里写 `run: sh scripts/gate-event-guard.sh`。
- **反例**：reusable workflow 的工作区在 checkout 前为空、checkout 后是 **caller** 仓；
  witnessloop 的 `scripts/` 根本不在 ⇒ 接入方每条 PR 都会 127。这个方案会让门禁全红。
- **裁定**：守卫前按 `steps.wl-ref.outputs.ref` 检出本仓到 `.witnessloop-gate`，
  执行脚本后立即 `rm -rf`。行为测试在临时目录伪造该路径，证明 YAML 接线可跑。
- **落点**：`gate.yml` 的 `checkout gate event guard script` / `gate event guard`；
  `tests/test_gate_event_guard.py::test_guard_checkout_and_step_run_before_the_caller_checkout_and_check`。

### R1-2（medium，已修）脚本缺失不能静默跳过

- **证伪尝试**：显式 `with.witnessloop-ref` 指到 `v1.7.1`（尚无该脚本的旧 ref），
  而 caller 用的是新版 workflow。
- **反例**：若守卫 step 只执行 `sh .witnessloop-gate/scripts/...`，会得到
  `No such file` 的裸错；更糟的是若有人写成「文件不在就 exit 0」，守卫就被静默绕过。
- **裁定**：step 先 `[ -f ... ]`；缺失 ⇒ 点名 `WL_REF` + `::error::` + 非 0（fail-closed）。
  新增行为测试。
- **落点**：`gate.yml` 守卫 step；`test_yaml_guard_step_fails_closed_when_the_script_is_missing`。

### R1-3（medium，已修）新增 `actions/checkout` 会让既有测试选错 step

- **证伪尝试**：`test_gate_pins_the_pr_head_for_checkout` 取「第一个 actions/checkout」。
  新增守卫 checkout 后它会选中守卫那次，断言 caller 的 `ref`/`fetch-depth` 失败。
- **裁定**：测试改为按 **无 `path`** 选 caller checkout；并新增测试钉住守卫 checkout 的
  `repository` / `ref` / `path` / `fetch-depth` / `persist-credentials`。
- **落点**：`tests/test_gate_workflow.py`、`tests/test_gate_event_guard.py`。

### R1-4（medium，已修）adopter tests 的 `if` 若改成 `== 'success'` 会改变 PR 行为

- **证伪尝试**：把 `if` 收窄为「守卫 success 才跑」。
- **反例**：`check` 失败时守卫仍是 success，测试照常跑（OK）；但**更早的步骤失败**
  （如 setup-uv）会让守卫 skipped，旧行为下 adopter tests 仍会跑，新条件会跳过——
  这是一条与被测问题无关的行为变更。
- **裁定**：改用 `steps.wl-event-guard.outcome != 'failure'`。只有守卫**明确失败**
  （非 PR）才跳过测试；其它情形维持旧行为。
- **落点**：`gate.yml` adopter tests `if`；两处测试断言。

### R1-5（medium，登记）跨仓 checkout 的可用性边界

- **证伪尝试**：GHES / 私有 witnessloop / 网络受限环境。
- **风险**：守卫 checkout 会失败，job 在守卫文案之前就红；这与「本仓必须公开」
  的既有能力边界一致（`uvx --from git+https://github.com/...` 同样依赖公网）。
- **裁定**：不修。文档 §6.1 与 PR 残余风险里写明；失败是 fail-closed，不会静默放行。

### R1-6（medium，登记）`refs/tags/<tag>` 作为 checkout ref 未在本环境真 CI 验证

- **证伪尝试**：annotated tag 的 resolve 输出是 `refs/tags/vX.Y.Z`；checkout 需要它。
- **依据**：`actions/checkout` 的 ref-helper 明确处理 `refs/tags/*`；不是把 tag object
  sha 交给 checkout（#42 的 uv 问题不适用）。
- **裁定**：保持实现；列为 PR 残余风险，等真实 CI 用 tag 形态验证。

### R1-7（low，已修）空事件文案缺少 `pull_request` 关键词

- **证伪尝试**：`GITHUB_EVENT_NAME=""` 时只报「无法判断事件类型」，测试要求三组提示
  都在 stderr。
- **裁定**：空事件文案补「本门禁只接受 pull_request」；仍是 fail-closed。
- **落点**：`scripts/gate-event-guard.sh`。

### R1-8（low，登记）非 PR 事件仍会先做一次 `fetch-depth: 1` clone

- **裁定**：守卫必须取得脚本，必须 clone；用最小 fetch depth，并放在 caller 的
  `fetch-depth: 0` checkout 之前。成本可接受，登记不修。

## 第 2 轮（验证修复，只做确认）

- R1-1：YAML 有守卫 checkout + 守卫 step；行为测试在临时目录伪造路径并通过。
- R1-2：缺失脚本分支有测试，断言「无法取得守卫脚本」+ 非 0 + 清理。
- R1-3：两个 checkout 测试都按 `path` 精确选择；全量绿。
- R1-4：`if` 为 `!= 'failure'`；PR 路径（check 失败）仍跑测试。
- R1-5/R1-6：已登记；文档与 PR 残余风险覆盖。
- R1-7：空事件 stderr 含 `pull_request`。
- R1-8：已登记。
- **新问题**：无 medium+。

## 结论

**PASS**。无残留 medium+；D1..D8 的实现与测试可相互印证。实现后仍需 building 审阅
（独立于本报告）确认 `tasks.md` 的每一 `[x]` 都真实落地。
