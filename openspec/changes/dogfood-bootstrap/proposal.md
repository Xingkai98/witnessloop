# Proposal: dogfood-bootstrap（witnessloop 自举接入）

> 状态：草稿（待 grill + 用户确认）。
> 关联 issue：witnessloop #7。

## 背景

witnessloop 的核心主张是「机械强制、不靠自觉」。但开发**它自己**的过程中（M1→M3→#1→#3），
没有任何机制强制走它自己的流程（issue #7 实测）：

- 仓里没有 `.witnessloop/`——**没对自己 `init`**；
- `.github/workflows/ci.yml` 只跑 pytest + 打包冒烟，**不跑 `witnessloop check`**；
- `gate.yml` 是纯 `workflow_call`（给接入方用），**从不自触发**；
- `gh pr list --state all` 为**空**——全仓开发**零 PR、直接 push `main`**；
- `main` **无 branch protection**（`gh api .../protection` → 404，rulesets 为空）。

于是 merge boundary 的两个前提（**走 PR** + **check 设 required**）**一个都没成立**：
门禁连挂都没挂上。（更深的洞——「写代码前的设计 grill 本地无执行体」——属 #7 的 B 轨与本仓 #2，
**不在本 change 范围**。）

## 目标

**让 witnessloop 自己的开发走完整流程**：change 契约（proposal/design/tasks/specs/reviews）
+ 证据绑定（review manifest）+ `check` 可跑并可绿。**本 change 自己就是契约下的第一个 change。**

## 交付

1. `.witnessloop/policy.json`（**本仓定制**：`require_change_for` 补上 `templates/**`、`plugin/**`）
   + `.witnessloop/init-manifest.json` + `.github/workflows/witnessloop.yml`（caller）。
2. `openspec/changes/` 契约在本仓生效；README / 开发说明写清「本仓改动走 change 契约」。
3. **`init` 支持自定义 policy**（`--policy <file>`）：默认 policy 不含 `templates/**`/`plugin/**`，
   而 `init` 目前**无任何定制通道**（只写 `default_policy_doc()`）；手改会打破 `init-manifest`
   台账（`uninit` 因 hash 不符拒删）——接入方几乎都要自定义 policy，这是**真缺口**。
4. （需用户手工一次）`main` branch protection：required check = witnessloop gate。

## 非目标（明确不做）

- **本地 pre-write 守卫（hook）**——#7 的 B 轨，另立。
- **报告正文校验**（Confirmed Decisions ≥3 / `来源:` / 停用确认齐）——本仓 #2，另立。
- 私有仓接入（#6）、fork PR（#5）。
- 改 `check`/契约的形状（`specs/` 硬要求等 v1 决策不动）。

## 验收

- **本地**：`witnessloop check --base main --head HEAD` 在 A 自己的 PR 上**绿**（含两段提交约定）。
- **负例**：改 `.witnessloop/policy.json` 不写解释事件 → `check` **拦**。
- **A 之后**：下一个 change 走 PR，required check 自动跑。

## 测试策略

- `init --policy` 走 TDD：单测覆盖「指定 policy → 内容/台账一致 → `uninit` 能回滚」、
  「policy 非法/路径逃逸 → 拒」、幂等。
- 端到端：A 自己的 change 目录通过 `check`（本仓首个真实 dogfood 样本）。
