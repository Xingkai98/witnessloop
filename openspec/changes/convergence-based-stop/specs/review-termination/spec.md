# review-termination — 审阅闭环的终止条件：有界批次 × 20 轮上限

> 本 change 的能力增量：把审阅闭环（实现后的 `review-loop` 与设计阶段的对抗验证环）的轮次口径
> 从「一次审阅 verdict 算一轮、3 轮封顶」改成「**一个非空 medium+ 批次的闭环算一轮**」。
> 轮内冻结批次、验证只做修复确认、新问题进下一批；最多 20 轮，超限 ⇒
> `BLOCKED` +「建议推倒重开（revise the design）」。
>
> 三种出口：`PASS` / `BLOCKED` + 成因 / 超上限 `BLOCKED` + 建议重开设计。

## 术语（规范定义）

- **批次（batch）**：一轮开始时审阅者开出的 **medium+** 问题列表；轮内冻结。
- **轮（round）**：一个**非空**批次的完整闭环（开批 → 全修 → 逐条验证 → 全部通过）。
- **验证（verification）**：只核对当前批次每一项是否修好；不是新一轮审阅。
- **deferred**：验证期间发现的 medium+ 新问题，登记给下一批，不扩当前批次。
- **low / nit**：不进入阻塞批次的低严重度问题；可修，也可登记不修（须写理由）。
- **收口确认（closing check）**：一轮结束后的下一次开批；批次为空 ⇒ `PASS`。

## Requirement: 一轮 SHALL 是一个非空 medium+ 批次的闭环

审阅闭环 SHALL 按下列顺序推进：

1. 审阅者开批，只列 severity 为 `medium` / `high` / `blocker` 的问题；
2. 批次 `B_n` 在开批后 SHALL **冻结**——本轮内 SHALL NOT 增加、删除或替换成员；
3. 开发者 SHALL 修完 `B_n` 的每一项；
4. 审阅者 SHALL 逐条验证 `B_n` 的每一项是否修好；
5. `B_n` 全部验证通过 ⇒ 本轮结束；否则开发者继续修，**仍是同一轮**，SHALL NOT 另计一轮。

`B_n = ∅`（开批时没有任何 medium+）⇒ 审阅闭环 SHALL 以 `PASS` 结束，不进入修复，也不消耗轮数。

⚠️ 轮数 SHALL 只按「非空 medium+ 批次」计数；单次审阅意见、单次修复提交、单次验证
SHALL NOT 各自计为一轮。

### Scenario: 第 1 轮验证不通过 ⇒ 继续修，不另计轮
- **Given** 第 1 轮批次为 A/B/C（均为 medium+）
- **When** 开发者修完 A/B/C，审阅者复验发现 A/B 已修好、C 未修好
- **Then** 本轮不结束；开发者继续修 C；C 修好并复验通过后，本轮结束
- **And** 轮数仍为 1；第 2 轮仅在开新批次时开始

### Scenario: 第 2 轮才提上一轮验证期间的新问题
- **Given** 第 1 轮验证期间审阅者发现新问题 D
- **When** 第 1 轮批次全部验证通过、本轮结束
- **Then** D 进入第 2 轮批次（作为 deferred 项），**不得**在第 1 轮验证期间作为阻塞项提出

### Scenario: 开批为空 ⇒ PASS
- **Given** 审阅者做下一次开批，未发现任何 medium+ 问题
- **When** 判定出口
- **Then** 以 `PASS` 结束；low/nit 若有，只进登记表

## Requirement: 验证期间 SHALL NOT 提新问题；新问题 SHALL 进入下一批

验证阶段（Requirement 1 第 4 步）SHALL 只做「当前批次逐项是否修好」的确认。审阅者在验证期间
发现的任何**新**问题 SHALL：

- severity 为 medium+ ⇒ 写入本轮报告的 `deferred`（下一批）清单，**不得**当场要求修复，
  **不得**扩大 `B_n`；
- severity 为 low / nit ⇒ 写入本轮报告的 low/nit 登记表。

验证阶段的唯一允许变化是：`B_n` 各项的验证状态、`deferred` 清单、low/nit 登记表。
批次成员 SHALL 保持不变。

⚠️ **例外不是「新问题」**：若审阅者判定整体不可继续（核心功能缺失 / 安全漏洞 /
测试大面积失败 / 同一批反复无法收口），SHALL 以 `BLOCKED` + 成因终结；这不是扩批，
而是三种出口之一。

### Scenario: 验证期间发现新 medium+ ⇒ 只登记
- **Given** 第 3 轮批次 `B_3` 有 4 项，验证到第 2 项时发现一个 medium+ 新问题
- **When** 审阅者写本轮报告
- **Then** 该新问题只出现在 `### 第 3 轮 · 下一批（deferred）`；`B_3` 仍为 4 项
- **And** 第 3 轮批次全部验证通过后，本轮结束；该新问题进入第 4 轮批次

### Scenario: 验证期间把 low 重分类为 medium+ ⇒ 进 deferred
- **Given** low/nit 登记表里有一项，验证期间审阅者确认它实际是 medium+
- **When** 写本轮报告
- **Then** 它 SHALL 从 low/nit 表移到 `deferred`，**不得**当场加入当前批次

## Requirement: medium+ SHALL 全部修完；low/nit 可登记不修但 SHALL 写理由

- 批次内 severity ≥ `medium` 的每一项 SHALL 被修完并验证通过；SHALL NOT 以「登记不修」放行。
- severity 为 `low` / `nit` 的项 SHALL NOT 阻塞本轮收口或 `PASS`；开发者可以：
  - 修（报告写明修复提交与测试，若有）；或
  - **登记不修**，并在报告中逐条写明**理由**。
- severity SHALL 由审阅者定级；开发者 SHALL NOT 自行把 medium+ 降级以跳过修复。开发者若认为
  定级错误，SHALL 在报告中提出具体理由，由审阅者复核并给出结论。
- 「登记不修」缺理由 SHALL 视为报告不完备（流程缺陷）；本判据 SHALL NOT 被表述为由
  `check` 机械执行。

### Scenario: low/nit 登记不修 ⇒ 仍可 PASS
- **Given** 某轮开批没有 medium+，low/nit 登记表有 3 项，均写明「登记不修 + 理由」
- **When** 判定出口
- **Then** `PASS`——low/nit 不阻塞收口

### Scenario: 把 medium+ 写成「登记不修」⇒ 不合格
- **Given** 批次里有一条 severity = medium 的项，开发者标为「登记不修」
- **When** 审阅者验证
- **Then** 该项 SHALL 判为**未修好**；本轮不结束，直到它被修完并验证通过

## Requirement: 轮数上限 SHALL 为 20；超限 SHALL 以 BLOCKED + 建议重开设计结束

- 审阅闭环 SHALL 最多存在 **20 个已结束的轮**（非空 medium+ 批次）。
- 第 20 轮收口后，审阅者 SHALL 做一次**收口确认**（下一次开批）：
  - 批次为空 ⇒ `PASS`；
  - 批次非空 ⇒ **超上限 `BLOCKED`**。
- 超上限报告 SHALL 明确写「**建议推倒重开（revise the design）**」，并附第 20 轮账本与
  仍未收口的 medium+ 列表。
- 收口确认 SHALL NOT 产生第 21 轮修复；它只允许 `PASS` 或超上限 `BLOCKED`。
- 超上限的停轮原因 SHALL 被表述为「20 轮有界修复仍未收口，说明问题在设计层」，
  SHALL NOT 被表述为「到轮数就停」或「照合交人」。

### Scenario: 第 20 轮收口后仍有 medium+ ⇒ 超上限 BLOCKED
- **Given** 第 1–20 轮均已结束；收口确认发现 2 条 medium+
- **When** 判定出口
- **Then** `BLOCKED`；报告含「建议推倒重开（revise the design）」与那 2 条问题
- **And** 不会开始第 21 轮修复

### Scenario: 第 20 轮收口后批次为空 ⇒ PASS
- **Given** 第 1–20 轮均已结束；收口确认没有 medium+
- **When** 判定出口
- **Then** `PASS`——收口确认不占第 21 轮，也不把「第 20 轮」改写成停轮理由

### Scenario: 第 3 轮就到了空批 ⇒ PASS（远未到上限）
- **Given** 第 1、2 轮结束；第 3 轮收口确认没有 medium+
- **When** 判定出口
- **Then** `PASS`——上限 20 不参与「是否继续」的判定，只约束最坏情况

## Requirement: 出口 SHALL 只有三种

审阅闭环的终结态 SHALL 只有：

| 出口 | 条件 |
|---|---|
| `PASS` | 收口确认批次为空 |
| `BLOCKED` + 成因 | 阻塞性缺陷 / 同一批无法收口；停下报告、不自行修复 |
| 超上限 `BLOCKED` | 20 轮已结束且收口确认仍有 medium+；附「建议推倒重开（revise the design）」 |

`CHANGES_REQUESTED` SHALL NOT 被视为出口；它只表示「本批仍有未验证通过的项」，对应动作是
继续修 / 继续验证。

### Scenario: 本批仍有未通过项 ⇒ 不是出口
- **Given** 第 5 轮批次尚有 1 项未修好
- **When** 写报告
- **Then** 报告可以写 `CHANGES_REQUESTED` 作为轮内状态，但出口仍是「未结束」；
  SHALL NOT 据此停下交人，除非命中 `BLOCKED` 的成因

## Requirement: 报告 SHALL 携带批次、验证、deferred 与 low/nit 登记

每一轮的审阅报告 SHALL 至少包含：

1. **批次表**：`id` / severity / 锚点（`文件:行`）/ 问题；
2. **验证表**：`id` / 结果（已修好 / 未修好）/ 修复提交 / 回归测试；
3. **deferred 表**：`id` / severity / 锚点 / 问题 / 来源；
4. **low/nit 登记表**：`id` / severity / 处置（已修 / 登记不修）/ 理由；
5. **出口**：`PASS` 或 `BLOCKED`（成因）或超上限 `BLOCKED`（建议重开设计）。

`id` SHALL 形如 `R<首次出现轮次>-<序号>`；deferred 项进入下一轮批次时 SHALL 沿用原 id。
多轮同文件时，每轮小节标题 SHALL 带轮次（例：`### 第 3 轮 · 批次`），以便第三方只读相邻轮次
即可复核。

### Scenario: 第三方只读两轮即可复核
- **Given** 一份报告同文件含 `### 第 3 轮 · 批次` 与 `### 第 4 轮 · 批次`，第 3 轮的
  deferred 项 `R3-2` 出现在第 4 轮批次表
- **When** 第三方只读这两节
- **Then** 能判定 `R3-2` 是第 3 轮验证期间发现、第 4 轮才开修的问题，不需要读会话史

### Scenario: deferred 项丢掉 ⇒ 可被发现（但只靠人读）
- **Given** 第 3 轮 deferred 表含 `R3-2`，第 4 轮批次表没有它，也没有 `BLOCKED` 出口
- **When** 第三方复核
- **Then** 能判定账本不自洽；⚠️ `check` **不解析**该表，机械上不设防

## Requirement: 设计对抗环与实现审阅环 SHALL 共用同一模型；grill frontier 追问轮豁免

- `templates/review-loop.md` 的实现后审阅环与 `templates/grill.md` 的设计阶段对抗验证环
  SHALL 使用同一套轮次模型（批次 / 验证 / deferred / 20 / 三出口）。
- `grill` 的 **frontier 追问轮**（为求设计树完备而做的内部轮）SHALL NOT 算作审阅轮，
  SHALL NOT 受 20 上限或「验证禁提新问题」约束；它产出的是决策记录 `grill-design.md`，
  不是 verdict 报告。

### Scenario: 对抗环的验证期发现新问题
- **Given** 设计对抗环第 2 轮批次已全部修完，验证时又发现一条必须修改
- **When** 审阅者写报告
- **Then** 该条进 deferred，进入第 3 轮批次；不得当场扩第 2 轮批次

### Scenario: grill frontier 的内部轮不占 20
- **Given** grill 为求 frontier 为空内部走了 5 轮追问
- **When** 进入设计对抗环
- **Then** 对抗环仍从第 1 轮开始计数；frontier 的 5 轮不占 20 上限

## Requirement: 机械门禁口径 SHALL NOT 改变

`witnessloop check` SHALL 继续只判：

- change 契约件存在；
- review manifest + 报告存在、hash 绑定最终 revision、`reviewer_run_id != author_run_id`；
- `stage=grill` / `grill-adversarial` / `building` 的证据存在（按既有触发面）。

`check` SHALL NOT 解析报告里的 verdict、批次、severity、轮数、deferred 或 low/nit 理由。
⚠️ 诚实边界 SHALL 如实写明：`check` 绿只证明「有绑在最终 revision 的报告」，
**不证明**报告按新模型执行；20 上限、批次冻结、deferred 都是**流程规定**，
不是机械判据（与本仓 §9/§10 的既有口径一致）。

### Scenario: 报告写着旧口径也能过机械门禁
- **Given** 一份被 manifest 绑定的报告，正文仍写「3 轮封顶」
- **When** 跑 `check`
- **Then** 机械判据仍可能判绿——因此本 change 必须同时提供**文档守卫**与**独立审阅**，
  SHALL NOT 宣称 `check` 能识别旧口径

### Scenario: 新模型不新增任何 `check` finding
- **Given** 同一份 diff（只改模板/适配器/自述/测试，不碰 `src/`）
- **When** 在改动前后分别跑 `check`
- **Then** findings 的**类别与数量**不变（证据存在性口径未动）
