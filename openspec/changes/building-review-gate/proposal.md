# Proposal: building-review-gate（实现后独立审阅成为硬门）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#13**。

## 背景

witnessloop 的卖点是「**机械强制、不靠自觉**」（README / design §2）。但**它最核心的一步——「实现后跑独立审阅闭环」——目前完全靠自觉**：

- `check` 今天只要求「该 change 至少有一份 manifest」+「其中 `stage=grill` 的那份正文合格」
  （`checkcmd.py:71-86`；`evidence.grill_evidence_findings_in_change`）。
- **没有任何判定要求 `stage=building` 的 manifest** ⇒ **跳过 review-loop 的 PR 照样绿**。
- 实证：change `guard-crash-exit`（PR #11）的 review-loop R1 抓到「**一行回退 `pyproject` 就能静默拆掉 issue #9 的修复本体**」
  与一条**假测试**——抓得很准，**但如果我不跑它，门禁一样放行**。⇒ 与「不靠自觉」的自述**自相矛盾**。

**与 asterwynd 的差距（已读源码核对；**按函数名**引用 `_check_review_manifests`，不引行号——跨仓行号会漂）**：它要求——

```python
requires_building_review = (
    not archived and change_type.primary != "docs"
    and _changed_capabilities(change_dir) and _tasks_all_complete(change_dir)
)
if requires_building_review and not review_report.exists():
    return ["building-review.md missing — 独立 subagent 审阅未运行。"]
```

即「**报告 + manifest 必须存在**」。**注意：它不解析 verdict 文本**（全文件 grep 无 verdict/PASS 解析；
注释里的 “produced a PASS manifest” 指的是**那份被 manifest 绑定的证据**，不是文本判据）。⇒
asterwynd 的「PASS 硬门」= **「闭环必须跑过」**，不是「文本里必须有 PASS 字样」。

## 目标

把「实现后独立审阅」变成 `check` 的硬门：**本次 diff 落了实现（触及 `policy.require_change_for` 的路径）时，
该 change 必须有一份 `stage=building` 的审阅证据**（manifest + 其绑定的报告），否则 `check` 红。

复用**已有的** revision 绑定（`contract._check_git_span`）：任何非证据文件在 manifest 的 `head_sha` 之后被改
⇒ 判 stale ⇒ 红 ⇒ **审阅之后再改代码必须重跑审阅**——这一半已经实现，本 change 只是补上「必须存在」那一半。

## 边界声明（**重要 · 别让读者误读**）

本 change 让「**闭环必须跑过**」成为机械门（证据存在 + 审在最终 revision 上），
但**verdict 文本（`PASS` / `CHANGES_REQUESTED`）不参与任何判定** ⇒
**「PASS 不是硬门」这一点没有被本 change 改变**（选甲时；见 design D3/D3.1）。
issue 标题里的「PASS」指的是「**那份被 manifest 绑定的审阅证据**」，不是文本字样——
这也是 **asterwynd 先例的实际口径**（它同样不解析 verdict 文本）。

## 非目标

- **不加 grill-adversarial（设计对抗轮）的门禁**——同一机制、另一个 stage，留作后续 change。
- **不改 `guard`**：写码**前**不可能有「实现后」的审阅 ⇒ `guard` 仍只查 grill 证据。
- 不引入签名 / 防伪造（沿用「防漂移不防伪造」边界）。
- 不重做 asterwynd 的 `Impact Analysis` / RIR / benchmark gate 等**项目特有**检查。

## 验收

- **单测**：改了受管控代码但**缺** `stage=building` manifest ⇒ `check` 红且文案可诊断；
  有则绿；**只改文档 / 只动 change 目录（无实现）⇒ 不要求**（不得误伤提案期 change）。
- **回归红线**：本仓三个 active change（`dogfood-bootstrap` / `grill-evidence-gate` / `guard-crash-exit`）
  **都有** building manifest（实测：三份 `building.manifest.json` 均在）⇒ 接上后不得把它们判红。
- 本 change 自己走完整流程（契约 + 证据 + `check` + PR）。

## 测试策略

TDD。判定落在 `checkcmd` 的既有 change 循环里（与 grill 那条并列），复用 `evidence`/`contract` 的既有原语。
```
