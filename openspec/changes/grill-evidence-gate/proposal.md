# Proposal: grill-evidence-gate（grill 证据的机械判定 + 本地强制）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#7**（② 轨）、**#2**。

## 背景

issue #7 有两条轨。① **dogfood**（本仓接入自己的门禁）已随 change `dogfood-bootstrap` 落地。② **本地强制**仍未做：

- v1 只把强制放在 **CI（merge boundary）**，hooks 按既定决策只作 advisory；
- 于是「**写代码前缺 grill 证据就拦**」这一步**在本地没有任何执行体**——agent 会跳过它（实测：开发 #1/#3 时跳了）；
- 这正是 asterwynd **有**、witnessloop v1 **砍掉**的那层：asterwynd 用 PreToolUse guard 在写码前查 grill 证据（`scripts/workflow_guard.py` 的 `_grill_evidence_missing()`）。

同时本仓 **#2**：`check` **不解析报告正文**——一个空的、或 `## Open Questions` 没被用户确认过的
`grill-review.md`，只要 manifest 绑上就照样过门禁。

**两者是同一个知识**：「grill 证据算不算齐」。分两份实现必然漂移（正是本项目最忌的失败模式：
`check` 与 `manifest build` 已因「两边各写一套」踩过坑，故共用 `constants.HASHED_ARTIFACTS`）。

## 目标

1. **一个共享的「grill 证据完备性」判定**（host-agnostic、纯函数、可单测）。
2. **接进 `check`**（#2）：报告正文不合格 ⇒ 门禁红（**事后 / CI 层**）。
3. **新增 `guard` 动词 + CC hook**（#7 ②）：**写代码前**缺 grill 证据 ⇒ 拦（**事前 / 本地层**）。
4. hook **随 plugin 分发**（不是 asterwynd 那种「手动 cp 进 gitignored `.claude/`」——那条路 worktree 里根本不在场）。

## 非目标

- 不含 git-hook（pre-commit/pre-push）适配器——可选，见 design 的 defer 项。
- 不含签名 / 防伪造（沿用 v1 边界：**防漂移，不防伪造**）。
- 不新增其余动名词（`gate`/`event`/`status`/`policy upgrade`）。
- 不修 `--stage` 值域任意（是否连带收紧见 design 的 Open Question）。

## 验收

- **单测**：evaluator 每条判定；`guard` 三态（拦 / 放 / 豁免）。
- **端到端**：`check` 对「正文不合格的报告」红、对「合格」绿；`guard` 对「写码前无证据」拦、对「写文档」放。
- **回归**：接上 evaluator 后，本仓既有的 `dogfood-bootstrap` **仍绿**（不能把已合规的 change 判红）。
- 本 change 自己走完整流程（契约 + 证据 + `check` + PR；本仓已开 branch protection）。

## 测试策略

TDD。evaluator 用**报告文本**做输入 → 纯函数、用例密集；`guard` 复用同一 evaluator，
只多一层「路径分类 + change 解析」。详见 `design.md` §5。
