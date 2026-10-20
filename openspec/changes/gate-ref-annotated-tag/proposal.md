# Proposal: gate-ref-annotated-tag（annotated tag 不再把 tag object sha 当包 ref）

> 关联 issue：witnessloop **#42**。
> 一句话：**tag 形态**从 `job.workflow_ref` 取调用方实际钉的 `refs/tags/<tag>`（可安装）；
> **分支 / commit 形态**保留 `job.workflow_sha`（它给的就是 commit，且是本次实际执行的精确
> revision）。annotated tag 下不再把 **tag object sha** 交给 `uvx`，同时不引入分支 pin 的
> TOCTOU（包比 workflow 文件晚一个 commit）。

## 背景（实测）

接入方把 caller 钉在 **annotated tag** 上（`uses: …/gate.yml@v1.7.0`）时，`job.workflow_sha`
给的是 **tag object** 的 sha（本仓 `v1.7.0`：tag object `00192abe…` → commit `c9b2811…`），
不是 commit。当前解析优先级（change `gate-ref-pins-package` 的 (B′)）是
**`job.workflow_sha` 优先、`job.workflow_ref` 兜底** ⇒ 这个 tag object sha 被直接交给
`uvx --from git+…@<sha>`。

**uv 0.13.2 起拒绝「精确 revision ≠ commit」**（本机实测：0.12.1 / 0.13.1 仍接受，
0.13.2 / 0.13.3 拒绝；issue 里观察到的是 0.13.3）。本机实测（同一台机器、同一公开仓）：

```
# uv 0.13.3，tag object sha（= 当前 job.workflow_sha 的值）
$ uvx --from "git+https://github.com/Xingkai98/witnessloop@00192abe45d2d72a4389eccb202faad48c34fa26" witnessloop --version
error: Failed to resolve `--with` requirement
  cause: Git operation failed
  cause: Exact Git revision `00192abe45d2d72a4389eccb202faad48c34fa26` does not match precise commit `c9b281167ad20b63e4832ad9ab8510964a2adc60` for `https://github.com/Xingkai98/witnessloop`
EXIT=1

# uv 0.12.1，同一个 tag object sha（修复前的「10-19 绿」）
$ uvx --from "git+…@00192abe45d2d72a4389eccb202faad48c34fa26" witnessloop --version
   Updated https://github.com/Xingkai98/witnessloop (c9b281167ad20b63e4832ad9ab8510964a2adc60)
witnessloop 0.1.0
EXIT=0

# uv 0.13.3，tag ref / tag 名 / 分支 ref / commit 都成功（解析到的都是 commit c9b2811… / 98b97b7…）
$ uvx --from "git+…@refs/tags/v1.7.0" witnessloop --version   # EXIT=0，Building …@c9b2811…
$ uvx --from "git+…@v1.7.0"        witnessloop --version   # EXIT=0，Building …@c9b2811…
$ uvx --from "git+…@refs/heads/main" witnessloop --version # EXIT=0，Building …@98b97b7…
$ uvx --from "git+…@c9b2811…"      witnessloop --version   # EXIT=0
```

⇒ 对 annotated tag，**同一个 ref 的「tag 名」是可安装的，「tag object sha」不可安装**。
本仓所有**发布 tag**（`v1`、`v1.0.0`…`v1.7.0`）都是 annotated ⇒ 这是常态，不是边角
（另有 `wip-postmerge-*` 轻量 tag，不属发布物）。

## 目标

1. **解析优先级（混合）**：显式 `with.witnessloop-ref` → `job.workflow_repository` 守卫 →
   `job.workflow_ref` 是 `refs/tags/<tag>` ⇒ 用完整 tag ref → 否则 `job.workflow_sha` 非空
   ⇒ 用 sha（分支 / commit pin 的精确 revision）→ 否则用 workflow_ref 的分支 / commit →
   fail-closed。annotated tag 因此解析成 `refs/tags/v1.7.0`，不再是 tag object sha；
   分支 pin 仍钉在本次执行的精确 commit（不引入 TOCTOU）。
2. **保持既有守卫**：`job.workflow_repository` 不等于 `REPO_SLUG`（含 GHES / 别人仓 / 空值）
   ⇒ 直接 fail-closed，**不**去试 workflow_ref；显式输入仍然最优先。
3. **行为级回归测试**：把解析 step 的 `run:` 原文交给真 `sh` 跑，注入
   `WL_INPUT_REF` / `WL_WORKFLOW_SHA` / `WL_WORKFLOW_REF` / `WL_WORKFLOW_REPOSITORY`；
   断言 annotated tag 形态解析出 **tag ref**（且不是 40 位 sha），并证明**旧的 sha 优先实现**
   在该测试下必红。
4. **发 `v1.7.1`**（annotated，指向含修复的提交），文档写明「钉 annotated tag 是受支持形态」；
   **不动** `v1` / `v1.7.0`。
5. 本仓 caller 的临时处置：它自己也钉 `@v1.7.0` ⇒ 修复 PR 的门禁会撞同一个 bug。
   先按 issue #42 的同类办法把 caller **临时钉到 commit**（同步 init 台账 + 解释事件），
   `v1.7.1` 发布后回钉 `@v1.7.1`，用真实 CI 验证新 `gate.yml`。

## 非目标

- **不**在解析器里做网络 deref（GitHub API / `git ls-remote` / `git fetch`）把 tag object peel 成 commit：
  门禁的第一个 step 不该引入新的网络/凭据/限流依赖。
- **不**改 CLI（`check` / `init` / `manifest`）的语义；本 change 只改 reusable workflow 的 ref 解析。
- **不**给 GHES 补 `job.*`（GHES 上仍按既有语义 fail-closed 到兜底 ref）——能力边界不变。
- **不**修「caller 文件不受保护」那条既有边界。
- **不 pin `setup-uv` 的 uv 版本**（grill Q2）：本次事故确实由浮动的 uv 引入，但「是否把 uv
  钉死」是依赖治理取舍（会延迟安全/修复更新），本 change 只登记为**后续 change**，不扩大范围。
  代价：未来 uv 再改变 git ref 解析仍可能影响接入方；本 change 的回归测试锁住 ref 形态，但不锁 uv 行为。

## 验收

- `tests/test_gate_workflow.py` 的 D 组：annotated tag 行为级用例在**旧实现上红、新实现上绿**；
  分支 / commit / 显式覆盖 / 跨仓 / GHES / 畸形输入 / 未定义 env / 输出非空等既有语义全部保留。
- `uv run pytest -q` 全绿。
- `witnessloop check --base origin/main --head HEAD` 在本 PR 上绿（证据：原始输出）。
- 三份 stage manifest（grill / grill-adversarial / building）绑定最终 revision。
- PR `--merge` 合入；在合并提交上打 annotated `v1.7.1`；本仓 caller 回钉 `@v1.7.1` 的 PR
  由**新的** `gate.yml` 判绿（真实 CI 证据）。
- issue #42 收到完成说明并关闭。
