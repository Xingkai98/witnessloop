# Design: dogfood-bootstrap（witnessloop 自举接入）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 依据 `proposal.md`。流程出处见 `templates/grill.md`。

## 0. 一句话

给 witnessloop **自己的仓**接上它自己的门禁：落 `.witnessloop/` + `openspec/changes/` 契约，
并补上接入所必需的 `init --policy` 通道——本 change 自己就是契约下的第一个 change。

## 1. 现状（实测，非推断）

| 事实 | 证据 |
|---|---|
| 无 `.witnessloop/` | 目录不存在 |
| CI 不跑门禁 | `ci.yml` 只有 pytest + 打包冒烟 |
| gate 不自触发 | `gate.yml` 仅 `on: workflow_call` |
| 零 PR | `gh pr list --state all` → `[]` |
| main 无保护 | `gh api .../branches/main/protection` → 404；rulesets `[]` |

## 2. 决策

### D1 采用 v1 硬编码的 change 契约（含 `specs/`）

本仓的 change 目录用默认形状：`openspec/changes/<id>/{proposal,design,tasks}.md` + `specs/` + `reviews/`。

- **为什么必须含 `specs/`**：`manifest build` 硬要求 `specs/` 存在——`constants.HASHED_ARTIFACTS`
  含 `("spec_hash","specs")`，build 对缺失直接 `_fail`（`manifestcmd.py:98`）。且这是**常量**，
  policy 改不掉（`required_artifacts` 只影响 `check` 的目录存在性判定，救不了 build）。
- **witnessloop 没有 spec 层，怎么凑？** 不凑——本 change 的 `specs/dogfood/spec.md` 写
  一条**真实能力要求**：「witnessloop 自身仓库的改动受 change 契约与证据门禁约束」。git 不跟踪空目录，
  所以 `specs/` 下必须有一个真文件。
- **备选**：放宽 `required_artifacts` 去掉 `specs`——**否**：救不了 build（见上），且让本仓不走默认路径、
  dogfood 失真。
- **代价（诚实记）**：这暴露 v1 对「无 spec 层仓库」的接入摩擦（本仓自己就是第一个受害者）。
  修它是**另一个 change**（非目标），本 change 只如实记录。

### D2 `init` 增加 policy 定制通道（`--policy <file>`）

**缺口**：`init` 只写 `policy.default_policy_doc()`（`initcmd.py:94`），**无任何定制通道**。
而默认 `require_change_for`（`constants.py:27`）**不含 `templates/**`、`plugin/**`**——对 witnessloop
是**真空**：只改交互层（不改 `src/`）的 PR 会绕过「必须挂 change 目录」。手改 `.witnessloop/policy.json`
又会与 `init-manifest` 台账的 hash 不符，导致 `uninit` 拒删、重跑 `init` 报「被改动过」。

- **决策**：`init --policy <file>` ——用给定文件的内容作为 desired policy（替换默认），其余不变
  （仍幂等 / 只增不改 / 不 auto-commit / `--dry-run`）。
- **为什么不「先 init 再手改」**：那会产生对 `.witnessloop/policy.json`（不变集）的**修改**，
  按 `gate.md §5` 需写解释事件，且台账失真。`--policy` 让 policy **一次写成正确内容**（「新增」），
  天然免解释、台账自洽、`uninit` 可用。
- **备选**：
  - (β) init 采纳「已存在的 policy.json」为 desired——隐式、易与「只增不改」打架。否。
  - (γ) 接受默认 policy，把 `templates/**`/`plugin/**` 覆盖留作后续——留下**已知绕过洞**。否。
  - (δ) 手搓一致的 init-manifest——伪造台账。否。
- **边界**：`--policy` 文件必须是可解析的 JSON **对象**（轻校验；schema 深校验留给 `check` 时的
  `Policy.from_doc`）；文件缺失/非法 → 报错**不写任何文件**；与 `--dry-run` 组合照常。
- **已初始化后再给不同 policy** → 命中「只增不改」冲突路径，报 diff 拒绝（不静默改）。

### D3 A 自身的 diff 与门禁自洽

- **含 `src/**` 改动**（`init --policy` 的 CLI/实现）→ 触发 `require_change_for` → **必须挂 change 目录** ✓。
- **`.witnessloop/**` 是「新增」**（不变集「新增免解释」，`gate.md §5`）→ 不需解释事件 ✓。
- **`.github/workflows/witnessloop.yml`** 既不在 `protected_paths` 也不在不变集 → 普通文件 ✓。
- 因此 A 的 `check` 预期**绿**，无需任何解释事件。

### D4 change-id / 分支 / 提交约定

- change-id `dogfood-bootstrap`；分支 `dogfood-bootstrap/2026-10-11`。
- witnessloop **没有**「分支名推 change-id」的约定（那是 asterndwynd guard 的机制）；`check` 从 **diff**
  推 change id（`changed_change_ids` 取路径首段）。分支命名仍按纪律，但**非门禁依赖**。
- **两段提交**（`gate.md §3.1`）：①内容（change 目录 + init 产物 + `--policy` 代码）②证据
  （`reviews/` 报告 + manifest）。`head_sha` 指①，被检 head 指②。

### D5 PR + required check（merge boundary）

- A 之后，本仓开发**改走 PR**；`main` 开 branch protection：required check = witnessloop gate。
- **鸡生蛋**：A 的 caller workflow 随 A 才落 `main`，且 required check 未开 → **A 自己只能本地
  `check`，bootstrap 靠自觉一次**。A 之后才有机械强制。（这正是本 change 的诚实前提，也是 #7 的注脚。）
- 实现期待核实：同仓 PR 触发 `pull_request` 时，GitHub 取 **base 还是 head** 的 workflow 文件；
  影响「A 之后第一个 PR 能否立刻被门禁覆盖」。
- **需用户手工一次**：开 branch protection（人肉那一签，design §4 / §9 风险 3）。

## 3. 接线点（实现清单，供 tasks 展开）

- `src/witnessloop/cli.py`：`init` 子命令加 `--policy`。
- `src/witnessloop/initcmd.py`：`desired_files` 接受外部 policy 文本；`run` 读取校验 `--policy`。
- `.witnessloop/policy.json`（本仓）：默认 + `require_change_for` 补 `templates/**`、`plugin/**`。
- `.github/workflows/witnessloop.yml`：init 产出的 caller。
- `README.md` / `docs/gate.md` / `docs/tasks.md`：文档同步。

## 4. 风险

1. **bootstrap 靠自觉一次**：A 自己无机械强制（见 D5）。→ 如实写进文档；A 后即机械。
2. **`--policy` 与漂移检测交互**：已 init（默认）再 `init --policy` 必须报冲突，不能静默改。
3. **`specs/` 硬要求伤非 spec 仓**（本仓即受害者）→ 记为已知摩擦，另立 change，不在本 change 修。
4. **首次真跑 `check` 可能有意外**：本仓 diff 若含 rename/删除，`check` 行为需实测确认。
5. **required check 开了但没人走 PR**：仍需 D5 同时「禁止直接 push」（require PR），否则门禁等于没开。

## 5. 测试策略

- **单测（TDD）**：`init --policy` —— 指定内容落盘且与台账一致；幂等；`uninit` 往返；
  非法 JSON / 非对象 / 路径逃逸 → 拒且不写；与 `--dry-run` 组合；已初始化后给不同 policy → 冲突。
- **端到端（本仓）**：A 自己的 change 目录 + 两段提交 + `manifest build` × N + `check` 绿。
- **负例**：改 `.witnessloop/policy.json` 不写事件 → `check` 拦；删某份 manifest → `check` 拦（孤儿/缺失）。

## 6. 文档影响

- `README.md`：加「本仓自身接入（dogfood）」+ `init --policy` 用法。
- `docs/gate.md`：加 `init --policy` 一节。
- `docs/design.md`：状态/§10 更新；§9 风险 4「强制只在 CI」**不变**（B 轨才改）。
- `docs/tasks.md`：追加 G 段（本 change 任务）。

## 7. Pre-Implementation Review

（待 grill + 对抗验证收敛后填写：已确认决策 / 必须修改（已整合）/ Code-Resolved 结论。）

## 8. Open Questions（停轮候选，待 grill 收敛后再定稿）

- **Q1** `init --policy` 纳入本 change，还是拆成独立 change（A0）？
- **Q2** A 自己只能本地 check（bootstrap 靠自觉一次）——可接受？
- **Q3** `main` 是否**同时**开「禁止直接 push（require PR）」？还是先只加 required check？
- **Q4** witnessloop 的 `protected_paths` 要不要加 `templates/**`（视交互层为受保护 artifact）？
