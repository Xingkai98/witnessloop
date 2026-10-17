# review-termination — 审阅闭环的终止条件：有界批次 × 20 轮上限

> 本 change 的能力增量：审阅闭环（实现后的 `review-loop` 与设计阶段的对抗验证环）的轮次口径
> SHALL 为「**一个非空 medium+ 批次的闭环算一轮**」。
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
- **收口确认（closing check）**：一轮结束后的下一次开批；批次为空 ⇒ `PASS`。初次开批
  （第 0 轮）为空也记作收口确认。
- **已收口的轮**：`B_n` 全部验证通过的轮；只有它计入 20。`BLOCKED` / 超上限 `BLOCKED`
  是终结态，不计为已收口轮。
- **轮内 verdict**：本轮报告里的 `PASS` / `CHANGES_REQUESTED` / `BLOCKED`；只有终结时才写
  「闭环出口」。

## Requirement: 一轮 SHALL 是一个非空 medium+ 批次的闭环

审阅闭环 SHALL 按下列顺序推进：

1. 审阅者开批，只列 severity 为 `medium` / `high` / `blocker` 的问题；
2. 批次 `B_n` 在开批后 SHALL **冻结**——本轮内 SHALL NOT 增加、删除或替换成员；
3. 开发者 SHALL 修完 `B_n` 的每一项；**实现环**每项 SHALL 附一条**能变红的回归测试**
   （先红后绿）——既有模板的这条要求 SHALL NOT 被静默弱化；**设计环**的对应物见
   Requirement 6（可复现反例 / 文档守卫 / 逐条决策记录）；
4. 审阅者 SHALL 逐条验证 `B_n` 的每一项是否修好；
5. `B_n` 全部验证通过 ⇒ 本轮结束；否则开发者继续修，**仍是同一轮**，SHALL NOT 另计一轮。
6. **验证重试的终止点**：同一项被再次（第二次及以后）判 `未修好`、且开发者拿不出
   **新的、可验证的修复方案**时，审阅者 SHALL 以 `BLOCKED` + 成因终结（记录验证次数、
   每次的修复提交与测试）；第一次判 `未修好` 时开发者就明确拿不出新方案，也立即触发。
   **「新的、可验证的修复方案」** = 实现环：新 commit + 一条修复前红、修复后绿的回归测试
   （或可复现失败的命令）；设计环：具体文本修改 + 可复现反例 / 文档守卫 / 逐条决策记录。
   不新增数字上限。**若上述终止点发生在第 20 轮，出口是超上限 `BLOCKED`，不是通用
   `BLOCKED`**（见 Requirement 4）。

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

⚠️ **例外不是「新问题」**：若审阅者判定整体不可继续，SHALL 以 `BLOCKED` + 成因终结；
这不是扩批，而是三种出口之一。**「整体不可继续」SHALL 限定为**：该新问题使当前轮的验证
失去意义，或继续实现/验证本身不安全。其余安全漏洞 SHALL 进 `deferred`。
**所有** deferred medium+ 的「延后理由」列 SHALL 写「为什么可以延后一轮」；安全项额外写
「为什么晚一轮仍安全」。

**deferred 传递的硬规则**：下一次开批 SHALL 先读上一轮的 `deferred` 与 low/nit 表；
每个 deferred medium+ SHALL 以**原 id** 出现在下一轮批次，或出现在本轮 `BLOCKED` 的成因里。

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
- **severity SHALL 随批次冻结**：验证期若审阅者认为定级错误，只能记录争议并二选一：
  （a）按原 severity 要求修完；或（b）`BLOCKED` 并把争议写进成因。
  SHALL NOT 静默把批次项移出批次或降为 low/nit。
- **累积登记**：最终 `PASS` 报告 SHALL 携带累积 low/nit 登记表，或逐项链接到首次登记的
  轮次小节——不得只留最后一轮。
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

### Scenario: 验证期想把 medium 降为 nit ⇒ 不得静默移出批次
- **Given** 批次里有一条 severity = medium 的项，验证时审阅者认为它其实是 nit
- **When** 审阅者处置
- **Then** 只能二选一：按原 severity 要求修完，或 `BLOCKED` 并把争议写进成因；
  SHALL NOT 把它从批次静默移出后收口

### Scenario: 最终 PASS 报告保留前序 low/nit 登记
- **Given** 第 2 轮登记一条 low「登记不修 + 理由」，第 4 轮收口确认空批 ⇒ `PASS`
- **When** 第三方读最终报告
- **Then** 第 2 轮那条 low 仍可查（累积登记表或链接到第 2 轮小节）

## Requirement: 轮数上限 SHALL 为 20；超限 SHALL 以 BLOCKED + 建议重开设计结束

- 审阅闭环 SHALL 最多存在 **20 个已收口的轮**（非空 medium+ 批次；「已收口」= `B_n` 全部
  验证通过；`BLOCKED` / 超上限 `BLOCKED` 的终结态不计入）。
- **轮数 SHALL 按 change（且按环）累计**：后续报告 SHALL 保留前序轮次，或引用同一份叠写
  报告；换审阅者 run / 另写一份从第 1 轮开始的新报告 SHALL NOT 重置计数。重置只能来自
  用户的明确裁决，并记为 `BLOCKED` / 建议重开设计。
- **第 20 轮自身无法收口**：若第 20 轮达到 Requirement 1 第 6 条的验证重试终止点，
  出口 SHALL 是**超上限 `BLOCKED`**（不是通用 `BLOCKED`）：报告含「建议推倒重开
  （revise the design）」、第 20 轮批次/验证账本与未收口 medium+ 列表；
  SHALL NOT 开启第 21 轮。**第 20 轮收口后、收口确认前**：等待收口确认，不开启第 21 轮，
  不做修复。
- **零轮 PASS 与收口确认 id**：初次开批（第 0 轮）为空 ⇒ `PASS`；报告写
  `### 初次开批 · 收口确认`，low/nit 用 `R0-<序号>`。第 20 轮收口后的收口确认若发现
  medium+ ⇒ 超上限 `BLOCKED`，标识用 `C-<序号>`（或 `R20-C<序号>`）；发现 low/nit ⇒
  仍可 `PASS`，同样用 `C-<序号>`。
- 第 20 轮收口后，审阅者 SHALL 做一次**收口确认**（下一次开批）：
  - 批次为空 ⇒ `PASS`；
  - 批次非空 ⇒ **超上限 `BLOCKED`**。
- 超上限报告 SHALL 明确写「**建议推倒重开（revise the design）**」，并附第 20 轮账本与
  仍未收口的 medium+ 列表。
- 收口确认 SHALL NOT 产生第 21 轮修复；它只允许 `PASS` 或超上限 `BLOCKED`。
- 超上限的停轮原因 SHALL 被表述为「20 轮有界修复仍未收口，说明问题在设计层」，
  SHALL NOT 被表述为「到轮数就停」或「照合交人」。

### Scenario: 第 20 轮达到验证重试终止点 ⇒ 超上限 BLOCKED
- **Given** `B_20` 有 1 项，第二次验证仍为 `未修好`，开发者拿不出新的可验证修复方案
- **When** 判定出口
- **Then** **超上限 `BLOCKED`**；报告含「建议推倒重开（revise the design）」+ 第 20 轮账本
- **And** 不会开启第 21 轮，也不会退化成不带「建议重开」的通用 `BLOCKED`

### Scenario: 第 20 轮第一次未修好但开发者有新的可验证方案 ⇒ 同轮继续
- **Given** `B_20` 有 1 项，第一次验证判 `未修好`，开发者提交了新 commit + 先红后绿的回归测试
- **When** 判定出口
- **Then** **不是**超上限 `BLOCKED`；继续第 20 轮修复/验证（同轮，不另计轮）

### Scenario: 第 20 轮收口后仍有 medium+ ⇒ 超上限 BLOCKED
- **Given** 第 1–20 轮均已收口；收口确认发现 2 条 medium+（id 用 `C-1` / `C-2`）
- **When** 判定出口
- **Then** `BLOCKED`；报告含「建议推倒重开（revise the design）」与那 2 条问题
- **And** 不会开始第 21 轮修复

### Scenario: 第 20 轮收口后批次为空 ⇒ PASS
- **Given** 第 1–20 轮均已收口；收口确认没有 medium+
- **When** 判定出口
- **Then** `PASS`——收口确认不占第 21 轮，也不把「第 20 轮」改写成停轮理由

### Scenario: 初次开批为空 ⇒ PASS（零轮）
- **Given** 第 1 次开批（第 0 轮）没有 medium+，但有 2 条 low/nit
- **When** 判定出口
- **Then** `PASS`；报告写 `### 初次开批 · 收口确认`，low/nit 用 `R0-1` / `R0-2`

### Scenario: 第 3 轮就到了空批 ⇒ PASS（远未到上限）
- **Given** 第 1、2 轮结束；第 3 轮收口确认没有 medium+
- **When** 判定出口
- **Then** `PASS`——上限 20 不参与「是否继续」的判定，只约束最坏情况

## Requirement: 出口 SHALL 只有三种

审阅闭环的终结态 SHALL 只有：

| 出口 | 条件 |
|---|---|
| `PASS` | 收口确认批次为空（含初次开批） |
| `BLOCKED` + 成因 | 阻塞性缺陷 / 同一批反复无法收口（触发点见 Requirement 1 第 6 条）；停下报告、不自行修复 |
| 超上限 `BLOCKED` | 20 个轮已收口且收口确认仍有 medium+，或第 20 轮自身达到验证重试终止点；附「建议推倒重开（revise the design）」 |

`CHANGES_REQUESTED` SHALL NOT 被视为出口；它只表示「本批仍有未验证通过的项」，对应动作是
继续修 / 继续验证。

### Scenario: 本批仍有未通过项 ⇒ 不是出口
- **Given** 第 5 轮批次尚有 1 项未修好
- **When** 写报告
- **Then** 报告可以写 `CHANGES_REQUESTED` 作为轮内状态，但 `## 闭环出口` 写「未定」；
  SHALL NOT 据此停下交人，除非命中 `BLOCKED` 的成因

## Requirement: 报告 SHALL 携带批次、验证、deferred 与 low/nit 登记

每一轮的审阅报告 SHALL 至少包含（**轮内 verdict 与闭环出口分开**）：

1. **本轮判定（verdict）**：`PASS` / `CHANGES_REQUESTED` / `BLOCKED`（轮内可见，不是终结出口）；
2. **批次表**：`id` / severity / 锚点（`文件:行`）/ 问题；
3. **验证表**：`id` / 结果（已修好 / 未修好）/ 修复提交 / **回归测试 / 设计环对应物**
   （设计环填可复现反例 / 改前失败改后通过的文档守卫 / 逐条决策记录，不得填 `N/A`）；
4. **deferred 表**：`id` / severity / 锚点 / 问题 / 来源 / **延后理由**；
5. **low/nit 登记表**：`id` / severity / 处置（已修 / 登记不修）/ 理由；
   最终 `PASS` 报告 SHALL 带**累积**登记表，或逐项链接到首次登记的轮次小节；
6. **收口确认**：`### 第 <n> 轮后 · 收口确认`（审阅时间 / 范围 / 0 条 medium+ 或 N 条）；
   `PASS` 出口 SHALL 引用这一节——空的批次表与「没做这次审阅」在文本上不可区分；
   **BLOCKED / 超上限 BLOCKED 报告 SHALL NOT 伪造收口确认**，改记「终止状态 / 验证账本 /
   未通过项」；
7. **闭环出口**：只在终结时填 `PASS` / `BLOCKED`（成因）/ 超上限 `BLOCKED`（建议重开设计）；
   轮内写「未定」。

`id` SHALL 形如 `R<首次出现轮次>-<序号>`；deferred 项进入下一轮批次时 SHALL 沿用原 id。
初次开批的 low/nit 用 `R0-<序号>`；第 20 轮收口后的收口确认用 `C-<序号>`（或 `R20-C<序号>`）。
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
- **设计环的 `BLOCKED` 成因映射**：核心需求缺失 / 设计自相矛盾 / 依赖不可满足 /
  同一批反复无法收口；作者负责改该 change 的**设计制品**：`design.md`、`proposal.md`、
  `specs/<capability>/spec.md`、`tasks.md`，以及决策记录 `grill-design.md`；报告同样带
  「批次 / 验证 / deferred / low-nit / 收口确认 / 出口」。
- **设计环的「能变红的回归测试」对应物**：验证表的「回归测试 / 设计环对应物」列 SHALL 填
  可复现反例 / 一条改前失败、改后通过的文档守卫 / 逐条决策记录（三选一），SHALL NOT 填 `N/A`
  来静默弱化既有模板的「每个修复都要红绿」要求。
- `grill` 的 **frontier 追问轮** SHALL 仅指**进入对抗环之前**、为求设计树完备而做的内部轮；
  它 SHALL NOT 算作审阅轮，SHALL NOT 受 20 上限或「验证禁提新问题」约束。
  **由对抗环批次项驱动的设计探索属于该轮修复**，SHALL NOT 改标为 frontier。

### Scenario: 对抗环的验证期发现新问题
- **Given** 设计对抗环第 2 轮批次已全部修完，验证时又发现一条必须修改
- **When** 审阅者写报告
- **Then** 该条进 deferred，进入第 3 轮批次；不得当场扩第 2 轮批次

### Scenario: grill frontier 的内部轮不占 20
- **Given** grill 为求 frontier 为空内部走了 5 轮追问
- **When** 进入设计对抗环
- **Then** 对抗环仍从第 1 轮开始计数；frontier 的 5 轮不占 20 上限

### Scenario: 设计环的修复证据不是 `N/A`
- **Given** 设计对抗环第 2 轮批次有一条「设计对需求 X 没有答案」
- **When** 作者修复并在验证表填证据
- **Then** 填的是可复现反例、改前失败改后通过的文档守卫、或逐条决策记录之一；
  SHALL NOT 填 `N/A`

## Requirement: 机械门禁 SHALL NOT 新增正文解析（既有判据不变）

本 change SHALL NOT 新增任何 `check` 判据；既有判据保持：

- change 契约件存在；
- review manifest / 报告 / revision / hash / `reviewer_run_id != author_run_id`；
- 孤儿报告（`reviews/**/*.md` 必须被某份 manifest 绑定）；
- **`stage=grill` 的决策记录正文完备性**（既有判据：`Confirmed Decisions` ≥3 且每条有
  `来源:`、`Open Questions`、`User Confirmation`；`src/witnessloop/evidence.py:259-330`）；
- **`stage=grill-adversarial` / `building` 存在即可**（`verify_body=False`；
  `evidence.py:334-380`）。

`check` SHALL NOT 解析 verdict、批次、severity、轮数、deferred 或 low/nit 理由（新模型不进入
机械面）。⚠️ 诚实边界 SHALL 如实写明：`check` 绿只证明「既有证据判据通过」，
**不证明**报告按新模型执行；20 上限、批次冻结、deferred 都是**流程规定**，
不是机械判据（与本仓 §9/§10 的既有口径一致）。**但 `stage=grill` 的正文结构是会被解析的**
——这是既有事实，不是本 change 新增；不得写成「`check` 不解析报告正文」。

### Scenario: `building` / `grill-adversarial` 报告写着过时措辞也能过机械门禁
- **Given** 一份被 manifest 绑定的 `stage=building`（或 `grill-adversarial`）报告，
  正文仍写一句过时的轮次口径
- **When** 跑 `check`
- **Then** 机械判据仍可能判绿——因此本 change 必须同时提供**文档守卫**与**独立审阅**，
  SHALL NOT 宣称 `check` 能识别过时措辞
- **And** 如果是 `stage=grill` 的报告，既有的正文完备性判据仍会生效（不是只判存在）

### Scenario: 新模型不新增任何 `check` finding
- **Given** 同一份 diff（只改模板/适配器/自述/测试，不碰 `src/`）
- **When** 在改动前后分别跑 `check`
- **Then** findings 的**类别与数量**不变（证据存在性口径未动）
- ⚠️ `templates/**`、`plugin/**` 在 `require_change_for` 内（`.witnessloop/policy.json:8-12`）
  ⇒ 改动前后都会要求同一批 stage manifest；该 Scenario 说的是「不新增 finding 类别/数量」，
  **不是**「没有 code_hits / 没有 stage 要求」
