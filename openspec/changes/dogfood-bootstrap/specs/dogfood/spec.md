# dogfood — witnessloop 自身接入

> 本 change 的能力增量：witnessloop **自己的仓库**接入它自己的 change 契约与证据门禁。
> （witnessloop v1 硬编码 OpenSpec 形状的 change 契约；本文件即该形状下的能力规格。）

## Requirement: 自身仓库的改动受 change 契约与证据门禁约束

witnessloop 仓库自身的非平凡改动 SHALL 落在 `openspec/changes/<id>/` 契约目录下，
并在合并前通过 `witnessloop check`；`require_change_for` SHALL 覆盖本仓的产品目录
（`src/**`、`templates/**`、`plugin/**`）。

### Scenario: 改动产品目录必须挂 change 目录
- **Given** 本仓 `main` 已接入（有 `.witnessloop/policy.json`）
- **When** 一个 PR 改动了 `src/` 或 `templates/` 或 `plugin/` 下任一文件
- **Then** `witnessloop check` 要求该 PR 携带**完整**的 change 目录（proposal/design/tasks/specs/reviews），
  否则报错并非零退出

### Scenario: 内容与证据分离提交
- **Given** 一个 change 已实现完成
- **When** 提交审阅报告与 manifest
- **Then** 内容与证据分属两个提交，`head_sha` 指最后一个非证据 revision

## Requirement: 自定义 policy 通过 `init --policy` 一次写成

首次接入需要非默认 policy 时，`witnessloop init --policy <file>` SHALL 以给定文件内容作为 policy 写入，
并保持**幂等、只增不改、不 auto-commit**、`uninit` 可精确回滚。

### Scenario: 已接入后给不同 policy
- **Given** 仓已接入（存在 `.witnessloop/init-manifest.json`）
- **When** 再次运行 `init --policy <与已落地内容不同的文件>`
- **Then** 报冲突并非零退出，**不得**静默忽略

### Scenario: 非法 policy 输入
- **Given** `--policy` 指向缺失 / 非法 JSON / 非对象 / 逃逸路径的文件
- **When** 运行 `init --policy`
- **Then** 报错并非零退出，**不写出任何文件**
