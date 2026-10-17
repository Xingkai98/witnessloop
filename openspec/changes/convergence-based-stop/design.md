# Design: convergence-based-stop（有界批次 × 20 轮上限）

> **状态：按用户 2026-10-17 拍板的新模型重写；grill（`reviews/grill-design.md`）的 R1–R13
> 已逐条整合（见文末 `## Pre-Implementation Review`）。** 旧版设计（收敛判据 / 问题账本 /
> 无限轮）与其评审产物**全部作废**；旧文件保留在 git 历史（旧分支提交 `9acdf2b` 与重写提交
> `20f1089`），不参与本 change 的证据。
> 关联 issue：witnessloop **#24**；基线：`origin/main` `46e45b4`（2026-10-17 fetch）。
>
> **用户已经拍板、本设计不再重开的参数**：
> 1. 轮 = **一个批次闭环**（开批 → 全修 → 只验证 → 收口）；
> 2. 轮数上限 = **20**，超过 ⇒ `BLOCKED` + **建议推倒重开（revise the design）**；
> 3. **medium+ 必须全修**；**low/nit 可登记不修，但必须写理由**。
>
> 停轮门结论：**没有需要用户再拍板的问题**（§8 的 Open Questions 为「无」）。

## 1. 现状与证据

### 1.1 旧口径的落点（本仓，origin/main 实测）

| 文件:行 | 原文（摘） |
|---|---|
| `templates/grill.md:21` | 时序图「…直到 PASS 或封顶」 |
| `templates/grill.md:130-141` | 「`CHANGES_REQUESTED` 则修并再审，直到 `PASS` 或**轮数封顶**（默认 3 轮，到顶交人判断）」 |
| `templates/grill.md:215` | 写码硬条件 #2「对抗验证已到 `PASS`（或轮数封顶并交人）」 |
| `templates/review-loop.md:11` | 「**有界轮数封顶**，避免『永远在修』和『自评通过』」 |
| `templates/review-loop.md:90-102` | 「### 5. 修复并再审（**轮数封顶**，默认 3 轮）」+「到第 3 轮仍 `CHANGES_REQUESTED`，停下…」 |
| `templates/review-loop.md:153` | 硬约束「…三轮封顶时该停下交人判断还是要停」 |
| `plugin/commands/grill.md:25` | 「直到 `PASS` 或轮数封顶」 |
| `plugin/commands/review-loop.md:2` | front-matter「…有界轮数，收尾落 manifest」 |
| `plugin/commands/review-loop.md:29` | 「6. **有界轮数**（默认上限 3 轮）…」 |
| `plugin/README.md:37` | 「…**轮数封顶**，收尾写报告并跑 `manifest build`」 |
| `README.md:306` | 「**循环收敛**：…有界轮数封顶」 |
| `docs/design.md:25` | 「4. **独立审阅闭环**：…**PASS 或 N 轮封顶**」 |
| `docs/gate.md:716` | 「非 `PASS` 收尾本身是 `templates/grill.md` 的**规定行为**（轮数封顶 → 交人判断）…」 |
| `tests/test_templates.py:257-258` | `assert "轮" in text and "封顶" in text` |
| `tests/test_plugin.py:174-176` | `assert "轮" in text and ("封顶" in text or "上限" in text)` |

### 1.2 为什么旧口径要换

- **轮不可数**：旧口径下「审阅者给一次 verdict」算一轮，但审阅者可以在开发者修复期间继续追加
  新问题；`guard-crash-exit` 的设计对抗实测跑到 **R5**（`:593` 轮头）、`events-readpoint-fix`
  的 R3 标题直接写「轮数封顶 · 最后一轮」——固定 3 轮**既没刹住 R5，也没解释 R3 为什么该停**。
- **停轮理由与收敛无关**：到第 3 轮仍 `CHANGES_REQUESTED` 就交人，可能恰好停在还在净进展时；
  而「有没有收敛」在旧口径里根本不进入判定。
- **工作量无界**：不冻结批次时，每修完一条又可能出现新的一条，一轮的工作量没有上界。

⇒ 新模型的核心不是「把 3 改成 20」，而是**先让一轮有界**：批次冻结、验证轮禁提新问题、
新问题一律进下一批。20 只是有界模型上的安全上限。

## 2. 新模型（规范定义）

### 2.1 名词

| 名词 | 定义 |
|---|---|
| **批次（batch）** | 某一轮开始时审阅者开出的 **medium+** 问题列表；**轮内冻结**。 |
| **轮（round）** | 一个**非空**批次的完整闭环：开批 → 开发者全修 → 审阅者逐条验证 → 全部通过 ⇒ 本轮结束。 |
| **验证（verification）** | 只核对当前批次每一项「是否已修好」；**不是**新一轮审阅，**不扫描/不追加**新的阻塞项。 |
| **deferred（下一批）** | 验证期间发现的新问题（以及重分类为 medium+ 的项）。只登记，**不扩当前批次**，进下一轮批次。 |
| **登记项（low / nit）** | 不进入阻塞批次的低严重度问题；可修可登记不修，登记不修必须写理由。 |
| **收口确认（closing check）** | 一轮结束后的下一次开批：若批次为空 ⇒ `PASS`；非空则成为下一轮。 |

### 2.2 一轮的精确流程

设第 `n` 轮（`n` 从 1 开始）：

1. **开批**：审阅者做一次完整审阅，产出本轮 **medium+ 批次** `B_n`。
   - `B_n = ∅` ⇒ **`PASS`**（不进入修复，不消耗轮数）。
   - `B_n ≠ ∅` 且已存在 20 个已结束的轮 ⇒ **超上限 `BLOCKED`**（§2.5）。
   - 否则本轮编号为 `n`，`B_n` **冻结**。
2. **全修**：开发者把 `B_n` 的每一项修完；每项给出具体处置 + 一条能变红的回归测试。
3. **验证**：审阅者只逐条确认 `B_n` 的每一项：
   - 已修好 ⇒ 记录 `已修好`（修复提交 + 回归测试）；
   - 没修好 ⇒ 记录 `未修好`，开发者继续修；**仍是第 `n` 轮**，不另计轮；
   - **验证重试的终止点（R2）**：同一项在本轮内被再次判 `未修好`，且开发者拿不出
     **新的、可验证的修复方案**时，审阅者 SHALL 以 `BLOCKED` + 成因终结（记录验证次数与
     未通过项）；不新增数字上限，但「同一批反复无法收口」是 **SHALL**，不是可选。
   - 验证期间发现的新问题 ⇒ 只写入 `deferred`（medium+）或 low/nit 登记表；
     **不得**当场作为本轮阻塞项提出，**不得**扩大 `B_n`。
     **安全漏洞的例外（R3）**：只有「该新问题使当前轮的验证失去意义，或继续实现/验证本身
     不安全」才可 `BLOCKED`；否则仍进 `deferred`，并在 deferred 行写明「为什么可以延后一轮」。
4. **收口**：`B_n` 全部为 `已修好` ⇒ 本轮结束，回到第 1 步做下一次开批（含 deferred）。
   **下一次开批 SHALL 先读上一轮的 deferred 与 low/nit 表**：每个 deferred medium+ SHALL
   以原 id 出现在下一轮批次，或出现在本轮 `BLOCKED` 的成因里（R9）。

> **「不许边改边提」是硬约束**：`B_n` 在开批时冻结。验证轮里唯一允许改变的是
> 「`B_n` 各项的验证状态」和「deferred / low/nit 登记表」；批次成员本身不变。

### 2.3 轮数上限 = 20

- 最多存在 **20 个已结束的轮**（`n = 1..20`）。
- **第 20 轮自身无法收口（R1）**：若 `B_20` 仍有任何一项为 `未修好`，本轮不会结束，
  收口确认不会发生——此时出口 SHALL 是**超上限 `BLOCKED`**（不是通用 `BLOCKED`）：
  报告 SHALL 写「**建议推倒重开（revise the design）**」+ 第 20 轮批次/验证账本 +
  未收口 medium+ 列表；SHALL NOT 开启第 21 轮。
- 第 20 轮收口后，审阅者仍要做一次**收口确认**（下一次开批）：
  - 批次为空 ⇒ `PASS`；
  - 批次非空 ⇒ **超上限 `BLOCKED`**：报告 SHALL 写「**建议推倒重开（revise the design）**」，
    并附第 20 轮账本与仍未收口的 medium+ 列表。
- **不是「到轮数就停」**：停下来的原因是「20 轮有界修复仍不能收口，说明问题在设计层」，
  不是「时间到了」。报告不得把超上限写成普通的交人/照合。
- **收口确认不算一轮**：它只允许两种结果——`PASS`，或超上限 `BLOCKED`；不会产生第 21 轮修复。
- **累计口径（R10）**：轮数是**按 change（且按环）累计**的。后续报告 SHALL 保留前序轮次，
  或引用同一份叠写报告；换审阅者 run / 另写一份从第 1 轮开始的新报告 SHALL NOT 重置计数。
  重置只能来自用户的明确裁决，并记为 `BLOCKED` / 建议重开设计。

### 2.4 严重度与处置

| 严重度 | 进入批次？ | 处置 |
|---|---|---|
| `blocker` / `high` / `medium`（合称 **medium+**） | 是 | **必须全部修完并验证通过** |
| `low` / `nit` | 否 | 可修；可**登记不修**，但报告必须逐条写**理由** |

- **定级由审阅者做**。开发者不得自行把 medium+ 降为 low 以跳过修复；若认为定级错误，
  SHALL 在报告中提出具体理由，由审阅者复核并给出结论。复核不得为了放行而改级。
- **severity 随批次冻结（R8）**：验证期若审阅者认为某条定级错误，只能记录争议并二选一：
  （a）按原 severity 要求修完；或（b）`BLOCKED` 并把争议写进成因。SHALL NOT 静默把
  批次项移出批次或降为 low/nit。
- 验证期间发现的新 `low/nit` 进登记表；新 `medium+` 进 deferred（下一批）。
- **low/nit 永不阻塞**：它们既不影响本轮收口，也不影响 `PASS`；但「登记不修」缺理由
  视为报告不完备（流程缺陷，不是机械门禁判据）。
- **累积登记（R13）**：最终 `PASS` 报告 SHALL 携带**累积** low/nit 登记表，或逐项链接到
  首次登记的轮次小节——不得只留最后一轮、让更早的登记从报告面消失。

### 2.5 三种出口（只有这三种）

| 出口 | 触发 | 报告必须包含 |
|---|---|---|
| **`PASS`** | 某次开批 `B = ∅` | 收口确认结论 + low/nit 登记表（若有） |
| **`BLOCKED` + 成因** | 阻塞性缺陷（核心功能缺失 / 安全漏洞 / 测试大面积失败 / 同一批反复无法收口） | 成因；当前批次与验证状态；交人决策项（照合 / 缩范围 / 放弃） |
| **超上限 `BLOCKED`** | 20 轮已结束，收口确认仍有 medium+ | 「**建议推倒重开（revise the design）**」；第 20 轮账本；未收口 medium+ 列表 |

- `BLOCKED` 不自行修复：它是**终结态**，把问题交回用户。
- `CHANGES_REQUESTED` **不是出口**：它只描述「本批仍有未验证通过的项」，是轮内状态；
  对应动作是继续修/继续验证，不是停下交人。
- 「同一批反复无法收口」**SHALL** 按 `BLOCKED` 结束并写成因（R2）：触发点是「同一项再次
  被判 `未修好`，且开发者拿不出新的、可验证的修复方案」，报告要如实记录验证次数与未通过项。
  本模型**不加**「每轮最多验证几次」的新参数（用户没有拍板这个旋钮）。

### 2.6 例子（逐字按用户口径）

- **第 1 轮**：审阅者提 A/B/C（medium+）⇒ 开发者修完 A/B/C ⇒ 审阅者复验：A/B 已修好，
  C 没修好 ⇒ **本轮不结束**，继续修 C（**这不算新一轮**）；C 修好后本轮结束。
- **第 2 轮**：审阅者此时才提 D/E（以及第 1 轮验证期间 deferred 的问题）⇒ ……
- 直到某一轮**没有任何 medium+ 问题** ⇒ `PASS`。
- 若到第 20 轮仍有 medium+ 未收口 ⇒ `BLOCKED` +「建议重开设计」。

### 2.7 报告形态（供第三方复核；`check` 不解析）

每轮报告 SHALL 至少有：

```markdown
### 第 <n> 轮 · 批次
| id | severity | 锚点（文件:行） | 问题 |
…

### 第 <n> 轮 · 验证
| id | 结果 | 修复提交 | 回归测试 |
…

### 第 <n> 轮 · 下一批（deferred）
| id | severity | 锚点 | 问题 | 来源 |
…

### low / nit 登记（累积：含前序轮次，或逐项链接）
| id | severity | 处置（已修 / 登记不修） | 理由 |
…

### 第 <n> 轮后 · 收口确认
- 审阅时间 / 审阅范围 / 结论：0 条 medium+ ⇒ PASS；或 N 条 medium+ ⇒ 下一轮 / 超上限 BLOCKED

## 出口
PASS | BLOCKED（成因：…） | BLOCKED（超过 20 轮，建议重开设计）
```

⚠️ **PASS 必须引用 `### 第 <n> 轮后 · 收口确认`**：空的批次表与「没做这次审阅」在文本上
不可区分（R12）。收口确认是 `PASS` 的证据位，不是可省略的装饰。

- `id` = `R<首次出现轮次>-<序号>`；deferred 项沿用首次出现的轮次编号，进入下一轮批次时
  不换 id（便于第三方追同一问题）。
- 同一份报告可以叠多轮（本仓惯例）；每轮小节标题带轮次，避免同名小节被合并。
- 这些是**流程约定**；`check` 只要求报告存在且被 manifest 绑定，**不解析**表格。

## 3. 决策记录

### D1：轮 = 非空 medium+ 批次的闭环（采纳用户裁定）

- **理由**：批次冻结后一轮的工作量有上界；验证不通过只是同轮重试，不产生「第 N 轮」的歧义。
- **备选**：按「审阅者给一次 verdict」计轮（旧口径）——`guard-crash-exit` 的 R5 证明它不可数；
  按「每次修复提交」计轮——会把同一批的多次修复算成多轮，偏离用户口径。
- **后果**：`PASS` 来自一次**空批**的开批，不是来自某轮验证结束。

### D2：验证轮禁提新问题，deferred 进下一批

- **理由**：这是「一轮有界」的关键；否则审阅者可以在验证时不断追加，轮次仍不可数。
- **边界**：验证只允许改「验证状态」和 deferred / low/nit 登记表；批次成员不变。
- **例外（R3）**：只有「该新问题使当前轮的验证失去意义，或继续实现/验证本身不安全」才可
  按 `BLOCKED` 终结；其余安全漏洞仍进 deferred，并在行内写明「为什么可以延后一轮」。
- **传递硬规则（R9）**：下一次开批 SHALL 先读上一轮的 deferred 与 low/nit 表；每个 deferred
  medium+ SHALL 以原 id 出现在下一轮批次，或出现在本轮 `BLOCKED` 的成因里。

### D3：20 轮上限 + 超限建议重开

- **理由**：用户拍板；有界模型下 20 轮足够大，再大说明该推倒重开。
- **计数**：只有非空 medium+ 批次算轮；收口确认（空批）不占轮；按 change（且按环）累计，
  后续报告保留前序轮次（R10）。
- **第 20 轮自身无法收口（R1）**：若 `B_20` 仍有 `未修好`，出口 SHALL 是**超上限 `BLOCKED`**
  +「建议推倒重开（revise the design）」+ 第 20 轮账本，不得开启第 21 轮。
- **超限处理**：第 20 轮收口后的收口确认若仍有 medium+ ⇒ `BLOCKED` +「建议推倒重开
  （revise the design）」。这不是「到轮数就停」——停的原因是 20 轮有界修复仍未收口。
- **备选**：无限轮（旧版设计）——用户已否决；把收口确认也计一轮——会让第 20 轮恰好收敛的
  change 无法 `PASS`，与「某一轮没有任何 medium+ ⇒ PASS」冲突。

### D4：medium+ 全修；low/nit 登记不修须写理由（采纳用户裁定）

- 严重度由审阅者定；开发者不得自行降级；**severity 随批次冻结（R8）**——验证期认为定级
  错误时，只能按原 severity 修完，或 `BLOCKED` 并记录争议，不得静默移出批次。
- low/nit 不阻塞收口与 `PASS`；「登记不修」缺理由 = 报告不完备；
  最终 `PASS` 报告要带**累积** low/nit 登记（R13）。

### D5：设计对抗环与实现审阅环共用同一模型

- `templates/grill.md` 的对抗验证环与 `templates/review-loop.md` 的 building 环同构：
  另起独立零记忆审阅者、开批、验证、deferred、20 上限、三出口。
- **设计环的 `BLOCKED` 成因映射（R11）**：核心需求缺失 / 设计自相矛盾 / 依赖不可满足 /
  同一批反复无法收口；作者负责改 `design.md` / `grill-design.md`；报告同样带
  「批次 / 验证 / deferred / low/nit / 收口确认 / 出口」。
- **显式豁免（R6）**：grill 的 frontier 追问轮**仅指进入对抗环之前**、为求设计树完备而做的
  内部轮；它不是审阅轮，不受 20 上限与「验证禁提新问题」约束。**由对抗环批次项驱动的设计
  探索属于该轮修复**，SHALL NOT 改标为 frontier。

### D6：机械门禁零变化

- `check` 仍只判「manifest + 报告存在、绑在最终 revision、reviewer ≠ author」；
  **不解析** verdict / 批次 / severity / 轮数 / deferred。
- 理由：与本仓 §9 building、§10 grill-adversarial 的既有口径一致；机械解析正文会引入
  「格式规范 + 历史回填 + 覆盖机制」的成本，且无法防伪造。
- **诚实边界**：20 上限、批次冻结、deferred 都靠**模板 + 独立审阅者**执行；
  `check` 绿只证明「有绑在最终 revision 的报告」，不证明报告里真的按新模型跑了。

### D7：不做本 change 之外的回填

- `docs/reviews/*`、已归档 change 的历史报告、`docs/tasks.md` 是当时的记录，不改写。
- asterwynd 的 12 处旧口径由镜像 change 承载；本 change 只在 proposal 里点名，不碰对方仓库。

### D8：本 change 自身的旧评审记录作废（R4）

- 2026-10-15 的 `reviews/grill-design.md`、`reviews/grill-adversarial.md` 是**旧模型**产物，
  不适用于新口径，不作为本 change 的证据。
- **孤儿规则冲突的处置**：`check` 要求 `reviews/**/*.md` 的每个报告都被 manifest 绑定
  （`src/witnessloop/contract.py:636-666`）——「留着旧文件但不绑 manifest」会变成孤儿报告，
  「绑旧文件」会变成旧模型假证据。⇒ 旧 `grill-design.md` 已被 2026-10-17 的新报告**覆盖**；
  旧 `grill-adversarial.md` 必须由 B2 用新模型报告**覆盖**后再建 manifest，或从 `reviews/`
  **移出**（git 历史保留），且**不得**为旧文件建 `stage=grill-adversarial` manifest。
- 旧内容可从 git 历史 `9acdf2b`（首次落盘）与 `20f1089`（重写时再次落盘）查。
- 本 change 的新证据从 2026-10-17 的新 grill 报告开始。

## 4. 落点与改法

### 4.1 `templates/review-loop.md`（核心）

- 目的：把「有界轮数封顶」改成「**批次闭环 + 20 轮上限**」。
- 执行步骤改为：
  1. 定位 change；2. 钉基线；3. **开批**（只列 medium+；空批 ⇒ PASS）；
  4. **全修**；5. **只做修复验证**（未通过 ⇒ 继续修，同轮；新问题 ⇒ deferred，不得当场提）；
  6. **收口**（全通过 ⇒ 本轮结束；下一次开批）；7. 20 上限与三出口；
  8. 收尾落 manifest。
- **三态 verdict 表（`templates/review-loop.md:75-81`）也要改**：`CHANGES_REQUESTED` 从
  「出口」降为「轮内状态」；`BLOCKED` 仍是出口；`PASS` 来自收口确认。
- 报告形态加 `### 第 <n> 轮后 · 收口确认`，`PASS` 必须引用它（R12）。
- 硬约束：批次冻结核 severity（R8）/ 验证禁提新问题 / medium+ 全修 / low/nit 登记须理由 /
  20 上限（含第 20 轮自身未收口，R1）/ deferred 传递（R9）/ 总账累计（R10）/
  `CHANGES_REQUESTED` 不是出口 / `check` 不解析正文。

### 4.2 `templates/grill.md`（对抗环）

- 时序图与第 5 步改成「批次模型，与 review-loop 同构」。
- 写码硬条件 #2 改成「对抗验证已 `PASS`，或 `BLOCKED` + 成因 + **用户已明确裁决继续**」；
  `BLOCKED` 本身 SHALL NOT 作为写码许可（R5）。
- 明确 frontier 追问轮豁免的起止：仅限进入对抗环之前的求完备阶段；对抗环批次项驱动的
  设计探索属于该轮修复（R6）。
- 设计环的 `BLOCKED` 成因映射与修复面见 D5（R11）。

### 4.3 适配器与自述

- `plugin/commands/review-loop.md`：front-matter、步骤 5/6、约束同步；
  **`:63` 的「结论是三态」也要改**，否则 `CHANGES_REQUESTED` 仍被当出口。
- `plugin/commands/grill.md`：步骤 5 同步。
- `plugin/README.md`：命令说明同步。
- `README.md:306`、`docs/design.md:25`、`docs/gate.md:716`：自述同步。

### 4.4 测试（R7 的扫描面）

- 改 `tests/test_templates.py:257-258` 与 `tests/test_plugin.py:174-176` 的旧断言。
- 新增 `tests/test_convergence_stop.py`：
  - **规范面清单**（显式列出）：`templates/review-loop.md`、`templates/grill.md`、
    `plugin/commands/review-loop.md`、`plugin/commands/grill.md`、`plugin/README.md`、
    `README.md`、`docs/design.md`、`docs/gate.md`、`tests/test_templates.py`、
    `tests/test_plugin.py`、`specs/review-termination/spec.md`。
  - **排除名单**（历史/夹具，不得被反断言误伤）：`docs/tasks.md`、`docs/reviews/**`、
    `openspec/changes/archive/**`、`openspec/changes/<其它 change>/**`、
    `tests/test_grill_adversarial_gate.py:180`（夹具里的旧措辞是「check 不解析正文」的输入）。
  - 模板/适配器/自述含新模型七要素；规范面不再出现旧口径（`3 轮封顶`、`三轮封顶`、
    `有界轮数`、`轮数封顶`）。
  - **变异验证**：把 `templates/review-loop.md` 的一处新措辞改回旧口径，测试必须 1 failed
    （可在本地手动验证并记入 building 报告；不把变异提交进仓）。

## 5. 测试策略（TDD）

1. 先写 `tests/test_convergence_stop.py` 与两条旧断言的改写版，跑 `uv run pytest -q` 确认**红**；
2. 再改模板/适配器/文档；
3. 目标：全量 `uv run pytest -q` 全绿（基线 `723 passed`，2026-10-17 实测）。
4. **变异验证**（R7）：临时把 `templates/review-loop.md` 的一处新措辞改回旧口径，
   确认新测试**变红**；改回后复绿。变异不提交。
5. 文档守卫只钉**措辞在场**，不证明语义执行；语义由独立零记忆审阅者按 tasks 逐项核对。

## 6. 诚实边界

- `check` **不解析**报告正文（D6）：新模型的 20 上限、批次冻结、deferred、severity
  都是**流程规定**，不是机械门禁判据。
- 本 change 的「20」是**安全上限**，不是收敛判据；真正的收敛判据是「收口确认时批次为空」。
- 「同一批反复无法收口」按 `BLOCKED` 处理，报告要如实记录验证次数；本 change 不新增
  「每轮验证次数上限」参数（用户未拍板）。
- 不承诺「20 轮内一定收敛」；只承诺「超过 20 轮时给出可行动的结论：重开设计」。

## 7. 验收

- 规范面（`templates/`、`plugin/`、`README.md`、`docs/design.md`、`docs/gate.md`）
  能逐条查到新模型七要素；不再有旧口径（`3 轮封顶`、`有界轮数`、`轮数封顶`）。
- `specs/review-termination/spec.md` 的 Requirement 覆盖：
  轮定义、批次冻结、验证禁提新问题、deferred、medium+ 全修、low/nit 登记须理由、
  20 上限与超限建议重开、三出口、两个环适用 + frontier 豁免、机械门禁零变化。
- `uv run pytest -q` 全绿。
- 三份 stage manifest（grill / grill-adversarial / building）齐全且 `witnessloop check` 绿。

## 8. Open Questions

（无）

用户 2026-10-17 已把模型、20 上限、medium+/low 口径全部拍板；本设计没有需要用户再拍板的
开放问题。若实现或评审中出现只有用户能拍的（例如改变 20 这个数、改变 severity 口径），
按停轮门要求停下报告，不自行编答案。

## 9. 风险

- **DR1｜措辞扩散**：旧口径散落在 9 个文件 + 2 条测试；漏一处就会出现两套规则。
  → 用文档守卫 + 全仓 grep（tasks.md 的验收项）逐处核对。
- **DR2｜`CHANGES_REQUESTED` 语义漂移**：旧模板把它当出口；新模型必须写明它**不是出口**，
  否则读者仍会「三轮 CR 就停下」。→ 模板与适配器各写一条反断言，测试钉住。
- **DR3｜20 上限被误读成「到点收工」**：报告与模板必须写「超限 = 建议重开设计」，不是照合。
  → spec 的 Scenario 与模板逐字写。
- **DR4｜`check` 绿 ≠ 模型被执行**：D6 的诚实边界必须写进 spec 与 README，避免过度承诺。
- **DR5｜旧评审记录被误当证据**：本 change 的 `reviews/` 只保留新口径报告；旧文件从工作树移除
  （git 历史可查），并在新报告中写明作废。

## Pre-Implementation Review

**Grill（`reviews/grill-design.md`，run `grill-reviewer-convergence-2026-10-17`）**：

- 7 条 Confirmed Decisions，`Open Questions` 为「（无）」；本 change 无新增待拍板问题。
- **必须修改（已整合）**：
  - **R1** 第 20 轮自身无法收口 → 明写超上限 `BLOCKED` + 建议重开（§2.3、D3、spec Requirement 4）。
  - **R2** 验证重试无上限 → 统一为 `SHALL`：无新可验证修复方案 ⇒ `BLOCKED` + 记录验证次数（§2.2、§2.5）。
  - **R3** 验证期安全漏洞二义 → 收紧例外：只有「验证失去意义/继续不安全」才 `BLOCKED`，否则 deferred 并写延后理由（§2.2、D2）。
  - **R4** 旧 review 与孤儿规则冲突、A5 假 `[x]` → D8 写明「覆盖或移出，不得绑旧文件」；tasks A5 拆成 A5a/A5b（A5b 待 B2）。
  - **R5** grill 写码硬条件 #2 把 `BLOCKED` 当许可 → 改成「`PASS`，或 `BLOCKED` + 成因 + 用户明确裁决继续」（§4.2）。
  - **R6** frontier 豁免边界 → 仅限进入对抗环之前；批次项驱动的探索属于该轮修复（D5、§4.2）。
  - **R7** 反子串测试扫描面/排除名单 → 显式清单 + 变异验证（§4.4、§5）。
  - **R8** 验证期降级无对称规则 → severity 随批次冻结；只能按原级修或 `BLOCKED`（§2.4、D4）。
  - **R9** deferred 传递只有 Scenario → 写成开批硬规则（§2.2、D2、spec Requirement 2）。
  - **R10** 20 轮累计口径 → 按 change（且按环）累计，报告保留前序轮次（§2.3、D3）。
  - **R11** 两环 `BLOCKED` 语义不同构 → 设计环成因映射 + 修复面 + 报告节（D5、§4.2）。
  - **R12** 报告缺收口确认记录位 → 加 `### 第 <n> 轮后 · 收口确认`，`PASS` 必须引用（§2.7）。
  - **R13** low/nit 登记是否累积 → 最终 `PASS` 报告带累积登记或链接（§2.4、D4）。
- **Code-Resolved**：落点行号全部核对；旧口径在规范面内无漏网；`tests/test_grill_adversarial_gate.py:180`
  的旧措辞是夹具，不改成断言；`check` 的正文判据只在 `evidence.py:259-330`，`building`/`grill-adversarial`
  只判存在（`evidence.py:373-380`）。

**停轮门**：无新增待拍板问题。用户 2026-10-17 的四个事项已记入 `grill-design.md` 的
`## User Confirmation`。
