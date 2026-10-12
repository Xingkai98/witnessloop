# Proposal: grill-adversarial-gate（设计对抗轮成为硬门）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#16**。

## 背景

witnessloop 的门禁在设计阶段有一处不对称：**头尾硬、中间软**。

| 环节 | 现在的强制力 | 依据 |
|---|---|---|
| grill（设计追问决策记录） | ✅ 硬门 | `check` 要求 `stage=grill` manifest 且报告正文完备（`checkcmd.py:83-88` + `evidence.py:238-257`）；本地 `guard` 写码前就拦 |
| **grill-adversarial（设计对抗验证轮）** | ❌ **纯自觉** | `grep -rn "grill-adversarial" src/` = **0 命中**（实测） |
| building（实现后独立审阅） | ✅ 硬门 | #13 / PR #14（`checkcmd.py:91-98`） |

⇒ **跳过设计对抗轮的 PR 照样绿**：门禁既不知道有没有跑过，也不要求任何证据。

而这一环最贵。本仓最近 4 个 change（`guard-crash-exit` / `building-review-gate` /
`events-readpoint-fix` / `grill-evidence-gate`）里，**对抗轮抓到的全是「设计结论层面」的错**：

- 自相矛盾的决策（`guard-crash-exit`：要求同一诊断文案既「点名文件」又「与 JSON 坏完全同形」——不可能同时成立）；
- 被实测证伪的推断（`building-review-gate`：「接上后一批既有用例会变红」——实测 404 passed 不变）；
- 「修正只落一份 artifact」（`events-readpoint-fix`：只改 design 不改 spec/tasks）。

比实现后的审阅**更早发现、更便宜修**。

`templates/grill.md:195-202` 把「对抗验证已到 PASS（或轮数封顶交人）」列为**写码前的四项硬条件之一**，
但**没有任何机械检查**。

### 与 asterwynd 的差距（已读源码实测）

asterwynd **有**这道门，但位置、判据、证据形态三处都不同：

- **位置**：只在归档点——`_check_archived_completion_gate`（`scripts/check_openspec_artifacts.py:1565`；
  调用点 `:1685` 只对 `archive/<dir>` 跑）；
- **判据**（`:1632-1641`）：`primary != "docs" and (all_types & DESIGN_TYPES) and _changed_capabilities(...) and not exists(reviews/grill-adversarial.md)`
  （`DESIGN_TYPES = {"feature", "refactor", "process"}`，`:32`）；
- **形态**：**裸文件存在性**，注释明写「存在性即可」；
- **本地守卫不管**：`grep -c adversarial scripts/workflow_guard.py` = **0**。

witnessloop **无 archive 门禁、无 `ChangeType`、`specs/` 恒备** ⇒ 它的三重豁免
（docs / 无 spec delta / 非设计类）在本仓**没有对应物**，触发条件必须另定（见 design D2 / Q1）。

## 目标

设计对抗轮变成 `check` 的机械门：**触发条件满足时，该 change 必须有 `stage=grill-adversarial`
的审阅证据**（manifest + 被它绑定的报告），缺失则 `check` 红。

复用**已有的** revision 绑定（`contract._check_git_span`）：验收之后再改任何非证据文件 ⇒ 判 stale ⇒ 红
⇒ **对抗轮之后又改 design / code 必须重跑**。这一半已经实现，本 change 只补「**必须存在**」那一半。

## 非目标

- **不改 `guard`**（写码前的本地守卫）：asterwynd 先例在守卫侧也不要求它（实测 0 命中）；
  本仓 `guard` 的定位是「防遗忘」、可绕过，真正的锚是 CI required check。
- **不解析 verdict 文本**（Q2 定案：不解析）：见 design D3 的诚实边界。
- **不加 archive 门禁、不引入 `ChangeType`**。
- **不加豁免名单**（= 新的绕过面）。
- 签名 / 防伪造（沿用「防漂移不防伪造」边界）。

## 验收

- **单测**：触发条件满足但缺 `stage=grill-adversarial` manifest ⇒ `check` 红且文案**点名现有 stage**；
  补齐 ⇒ 绿；未触发（依 Q1 裁决）⇒ 不要求；对抗轮之后再改 design / code ⇒ **stale 红**（既有能力，加回归钉住）。
- **回归红线**：本仓 5 个 active change 目录**都有** `grill-adversarial.manifest.json`（实测）
  ⇒ 接上后 0 条自伤；既有用例的改动量**已实测**（甲 17 条 / 乙 4 条，见 design D2）。
- 本 change 自己走完整流程（契约 + 证据 + `check` + PR）。

## 测试策略

TDD。判定落在 `checkcmd` 既有 change 循环里（与 grill / building 那条并列），
复用 `evidence.stage_manifest_findings_in_change`（`evidence.py:172-235`）——**不写第二份实现**。
