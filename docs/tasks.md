# witnessloop MVP 任务清单

> 依据 `docs/design.md` v0.2 §10。范围锁定：**2 动词 + `uninit`**。明确不做项见 design §10。
> 原则：测试先行（TDD）。每个能力先写失败测试再实现。

## A. 骨架与分发

- [x] A1 `pyproject.toml`（uv 可 `uv tool install`）+ 包结构 + 控制台入口 `witnessloop`
- [x] A2 CLI 框架（子命令路由；未实现子命令给出明确报错，不静默）

## B. `init`（接入目标仓）

- [x] B1 生成 `.witnessloop/policy.json`（schema：`protected_paths[]` + `required_artifacts[]` + `evidence`）
- [x] B2 生成 `.witnessloop/init-manifest.json`（创建清单 + init 前 base ref）
- [x] B3 生成极薄 GitHub caller workflow（`uses: <owner>/witnessloop/.github/workflows/gate.yml@v1`）
- [x] B4 **幂等 + 只增不改 + 不 auto-commit**（已有文件不覆盖；冲突时报 diff）
- [x] B5 `--dry-run` 打印将做的改动，不落盘

## C. `uninit`（精确回滚）

- [x] C1 依 `init-manifest.json` 删除本工具创建的文件
- [x] C2 文件 hash 被改过则**拒绝删除**并报 diff
- [x] C3 幂等（重复 uninit 安全）

## D. `check`（CI 入口，fail-closed）

- [x] D1 无 policy 时输出「**未接入**」并以非零退出（**不得静默通过**）
- [x] D2 校验 change 目录契约（proposal/design/tasks/specs + reviews/）
- [x] D3 校验 review manifest 存在且 hash 绑定（base/head sha + tasks/spec/report hash）
- [x] D4 校验 `reviewer_run_id != author_run_id`
- [x] D5 校验受保护路径写入有结构化解释事件（`reason`/`approved_by` 非空）
- [x] D6 不变集：policy / manifest 恒受保护、不可由 repo policy 移除（~5 条常量封顶）

## E. 交互层（CC plugin）

- [ ] E1 host 中立模板（grill / review-loop 的算法与 prompt）与 CC 适配器**物理分离**
- [ ] E2 CC 适配器：`grill` 命令（零记忆追问 → 结构化决策记录）
- [ ] E3 CC 适配器：`review-loop` 命令（独立审阅 → 修复 → 再审，有界轮数）
- [ ] E4 **只读、无状态**（不得持有自己的状态文件；一切以 manifest 为准）

## F. 验收（acid test，见 design §7）

- [ ] F1 第二个**非 asterwynd** 仓库端到端跑通：`init` → change → grill → 实现 → review-loop → `check` 绿
- [ ] F2 负例 (a)：手写一行放行事件提交，`check` 行为符合预期（默认不拦 + 文档注明不防伪造）
- [ ] F3 负例 (b)：交互层状态与 manifest 故意漂移 → 报错而非双绿
- [ ] F4 负例 (c)：不跑 `init` → `check` 报「未接入」
- [ ] F5 负例 (d)：`init` → `uninit` 回滚往返

## 里程碑

- **M1**：A + B + C + D（门禁层可跑，`check` 能在第二仓拦下缺证据 PR）——**已完成**（分支 `mvp-m1/2026-10-09`）
- **M2**：E（交互层 CC plugin 可用）
- **M3**：F（第二仓 acid test 全绿，含负例）

## 明确不做（v1）

签名/密钥 · marketplace · spec 适配器抽象 · 状态机/projection/replay · platform-gate 自动注册 · `policy upgrade` · 证据分档机制 · 多 host · 7 动词 · schema 冻结。
