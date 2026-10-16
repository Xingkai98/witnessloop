# gate-ref-pinning — 接入方钉住的 ref 必须同时决定「跑哪个包」

> 本 change 的 capability 增量：把「接入方钉的 ref」当成**单一事实来源**，同时决定
> reusable workflow 文件与 **witnessloop 包**的版本；并让 CI 日志看得见本次实际用的 ref。
> ⚠️ 具体措辞（尤其是「默认值从哪里来」）**待 `design.md §8 Q1` 裁定**；本文件按本稿推荐 (B) 起草。

## Requirement: 接入方钉住的 ref SHALL 同时决定 workflow 文件与包版本

`init` 写出的 caller 与 reusable workflow SHALL 保证：**同一个 ref** 既决定 `uses:` 指向的 workflow，
也决定 `uvx` 安装的 witnessloop 包版本。接入方 SHALL NOT 需要分别维护两个 ref。

- 新接入方：`init --gate-ref <ref>` 之后，两处一致（可复算：看生成文件 + 看 CI 日志里解析到的 `witnessloop@<ref>`）。
- ⚠️ **本句 SHALL 推迟到 `design.md §8 Q1` 裁定之后再定稿**（grill M3）：(B) 下包版本**仍然**由
  `inputs.witnessloop-ref` 的**默认值**决定（只是取值被推导出来），(A) 下由 `with:` 决定——
  下面两种写法**各自只对一种机制成立**，在 Q1 裁定前不得作为 Requirement：
  - ~~(B) 版本：既有接入方零改动即满足~~（grill 实测已证伪：存量仓跑的是旧 gate.yml）
  - ~~(A) 版本：包版本由 caller 里的 `with:` 决定~~
  ⇒ 定稿时按裁定的机制保留其中一条，并相应改写本段。

### Scenario: 改一处、两处跟着变
- **Given** 一个已接入的仓，caller 是 `uses: …/gate.yml@<旧 ref>`
- **When** 把该行改成 `@<新 ref>` 并推一次 PR
- **Then** CI 日志里解析到的 witnessloop 包 ref SHALL 也是 `<新 ref>`（`gate / check` 用的是新包）

### Scenario: 畸形 / 解析不出的 ref
- **Given** 无法从 workflow 自身解析出 ref（运行环境不提供该信息），或解析结果**不可接受**。具体畸形样本（grill M7）：
  `owner/repo/x.yml`（缺 `@`）、`owner/repo/x.yml@`（`@` 后为空）、
  `<别的 owner/repo>/x.yml@refs/heads/main`（`owner/repo` ≠ `constants.REPO_SLUG`）、
  `…@refs/pull/30/merge`（PR 合并 ref，不是可安装的稳定 ref）
- **When** 运行门禁
- **Then** SHALL **fail-closed 到既有默认**（`v1`）**并打日志说明**，SHALL NOT 静默改变行为

## Requirement: 实际使用的 ref SHALL 在 CI 日志里可见

门禁 SHALL 在运行 `check` 之前把本次实际使用的 witnessloop ref **打进日志**（对所有 ref 形态成立：tag / 分支 / sha），
使接入方不必靠猜。

⚠️ **能力边界（SHALL 明写）**：witnessloop **包自身**无法报告「我是从哪个 git ref 构建的」
（`uvx` 现场构建 wheel，`__version__` 与 tag 无关）⇒ 本要求只承诺**日志侧**可见性。

### Scenario: 日志里能直接读到 ref
- **Given** 一次 PR 触发的 `gate / check`
- **When** 看该 job 的日志
- **Then** SHALL 有一行明确写出本次使用的 witnessloop ref（不需要 grep `uvx` 的构建输出）
