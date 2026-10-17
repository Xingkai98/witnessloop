# Proposal: convergence-based-stop（审阅闭环的终止条件：有界批次 × 20 轮上限）

> **状态：按用户 2026-10-17 拍板的新模型重写。** 旧版（2026-10-15）的「消解式收敛判据 /
> 问题账本 / 无限轮」文档**全部作废**；其评审产物也不适用于新口径（见 `reviews/grill-design.md`
> 的「旧记录作废」一节）。关联 issue：witnessloop **#24**。
>
> **用户已拍板、本 change 不再重开的三个参数**：
> 1. 轮的定义 = **一个批次闭环**（不是「审阅者给一次 PASS」）；
> 2. 轮数上限 = **20**，超过 ⇒ `BLOCKED` + **建议推倒重开（revise the design）**；
> 3. 批次里 **medium 及以上必须全修**；**low / nit 可以「登记不修」但必须写理由**。

## 背景

`templates/grill.md`、`templates/review-loop.md`、`plugin/commands/*.md` 目前规定审阅闭环跑到
「**`PASS` 或轮数封顶（默认 3 轮）**」，到顶停下交人。

这个口径有两个问题（issue #24）：

- **「轮」没有定义**：一次审阅给一个 verdict 就算一轮，审阅者可以在修复过程中反复追加问题，
  轮次不可数、工作量无界；
- **固定 3 轮与「是否收敛」不等价**：本仓实测里既有第 3 轮才收敛的环，也有突破 3 轮仍在修
  的环（`events-readpoint-fix` 的 R3、`guard-crash-exit` 的 R5；行号见 design §1）。

用户 2026-10-17 裁定：**不再用「审阅 pass 次数」计轮**，改成下面这个**有界批次**模型。

## 新模型（用户裁定，逐条写死）

### 一轮 = 一个有界闭环

1. 审阅者提出**一批**问题（**只列 medium 及以上的阻塞项**）；
2. 开发者把这一批**全部修完**；
3. 审阅者**只做「修复验证」**：逐条确认这批问题是否已修好——
   **验证期间发现的新问题不许当场提**，只能记入「下一批」清单（deferred）；
4. 这一批**全部修好** ⇒ 本轮结束；**下一轮**才开始提新的一批。

⇒ **不许边改边提**。修复验证期间新发现的问题只能 deferred，不能扩当前批次。

### 轮数上限 = 20

- 超过 20 轮 ⇒ `BLOCKED`，报告 SHALL 明确写「**建议推倒重开（revise the design）**」；
- 这**不是**「到轮数就停」：第 20 轮结束后，若下一次开批仍发现 medium+，说明问题在**设计层面**
  没有被收口，重开设计比继续修更省；若下一次开批为空 ⇒ `PASS`。

### 批次里的 low / nit

- `low` / `nit` **可以登记不修**，但报告里**必须逐条写理由**；
- `medium` 及以上**必须全部修完并验证通过**，不得以「登记不修」放行。

### 三种出口（只有这三种）

| 出口 | 条件 | 报告必须写 |
|---|---|---|
| `PASS` | 一次开批**没有 medium+ 问题**（批次为空） | 收口确认 + low/nit 登记表 |
| `BLOCKED` + **成因** | 阻塞性缺陷（核心功能缺失 / 安全漏洞 / 测试大面积失败 / 同一批无法收口） | 成因 + 当前批次/验证状态 + 交人决策项 |
| 超上限 `BLOCKED` | 已跑满 20 轮，下一次开批仍有 medium+ | **建议推倒重开（revise the design）** + 第 20 轮账本 |

### 一个具体例子（写进 design，帮助理解）

- 第 1 轮：审阅者提 A/B/C（medium+）⇒ 开发者修完 A/B/C ⇒ 审阅者复验：A/B 已修好，C 没修好
  ⇒ **本轮不结束**，继续修 C（**这不算新一轮**）；修好后本轮结束。
- 第 2 轮：审阅者此时才提 D/E（以及第 1 轮 deferred 的问题）⇒ ……
- 直到某一轮**没有任何 medium+ 问题** ⇒ `PASS`。
- 若到第 20 轮仍有 medium+ 未收口 ⇒ `BLOCKED` +「建议重开设计」。

## 目标

1. 把「轮」定义为**非空 medium+ 批次的闭环**；验证不通过不另计轮，批次冻结、不得边改边提。
2. 把 20 写进模板/适配器/规格/文档，并写清「超过 = 建议重开设计」，不是「到点收工」。
3. 把 medium+ / low / nit 的处置口径写死：medium+ 全修；low/nit 登记不修须写理由。
4. 把三种出口写死：`PASS` / `BLOCKED` + 成因 / 超上限 `BLOCKED` + 建议重开。
5. 设计阶段对抗验证环与实现后审阅环**共用**同一套轮次模型；grill 的 frontier 追问轮
   **不**属于审阅轮，不受 20 上限约束（显式豁免）。
6. 机械门禁口径**不变**：`check` 仍只判「证据存在 + 绑在最终 revision」，
   **不解析**批次、severity、轮次或出现次数——新模型靠**模板 + 独立审阅者**执行。

## 非目标

- **不在 `check` 里解析报告正文**（不解析 verdict / 批次 / severity / 轮数）。这是本仓
  `building` / `grill-adversarial` 两条门禁的既有口径，本 change 不改变。
- **不给「超过 20 轮」加机械判据**：它只在诚实的审阅者/开发者写出的报告上生效；
  与既有「证据存在」门禁一样，属于**防漂移、不防蓄意伪造**。
- **不回填历史记录**：`docs/reviews/*`、已归档 change 的报告、`docs/tasks.md` 是当时的记录，
  不按新口径改写。
- **不碰 asterwynd 侧**：其 12 处旧口径由另一个 change 承载，口径以本 change 的 spec 为准。
- **不改 `BLOCKED` 的既有语义**（阻塞性缺陷停下、报告、不自行修复），只补「超上限」这一成因。
- 不引入新参数（如每轮验证次数上限、severity 折算规则）；用户已拍板的三个参数之外不再加旋钮。

## 落点（origin/main `46e45b4` 实测行号）

| 文件:行 | 现状 | 改成 |
|---|---|---|
| `templates/review-loop.md:11` | 「有界轮数封顶」 | 批次闭环 + 20 轮上限 + 三种出口 |
| `templates/review-loop.md:90-102` | 「修复并再审（轮数封顶，默认 3 轮）」 | 「修复并验证（同轮不另计）」+ deferred + 20 上限 |
| `templates/review-loop.md:153` | 「三轮封顶时该停下交人」 | 超上限 ⇒ BLOCKED + 建议重开设计 |
| `templates/grill.md:21` | 「直到 PASS 或封顶」 | 「直到 PASS / BLOCKED；对抗环按批次模型」 |
| `templates/grill.md:130-141` | 对抗环「PASS 或轮数封顶（默认 3 轮，到顶交人）」 | 对抗环与 review-loop 同构：批次 / 验证 / deferred / 20 |
| `templates/grill.md:215` | 写码硬条件「PASS（或轮数封顶并交人）」 | 「PASS（或 BLOCKED + 成因，含超上限建议重开）」 |
| `plugin/commands/grill.md:25` | 「直到 PASS 或轮数封顶」 | 同上 |
| `plugin/commands/review-loop.md:2` | front-matter「有界轮数」 | 「批次闭环，20 轮上限，三出口」 |
| `plugin/commands/review-loop.md:29` | 「有界轮数（默认上限 3 轮）」 | 「batch / deferred / 20 / 三出口」接线 |
| `plugin/README.md:37` | 「轮数封顶」 | 同上 |
| `README.md:306` | 「有界轮数封顶」 | 批次模型 + 20 + 重开建议 |
| `docs/design.md:25` | 「PASS 或 N 轮封顶」 | 「批次闭环；20 轮上限；超限 BLOCKED + 重开」 |
| `docs/gate.md:716` | 「轮数封顶 → 交人判断」 | 「BLOCKED（含超上限建议重开）是规定出口」 |
| `tests/test_templates.py:257-258` | 断言「轮 + 封顶」 | 断言批次 / 20 / medium+ / deferred / 三出口 |
| `tests/test_plugin.py:174-176` | 断言「轮 + 封顶/上限」 | 同上（适配器接线层） |

## 验收

- **新口径在场**：`templates/review-loop.md` 能逐条查到
  ① 轮 = 非空 medium+ 批次闭环；② 验证期间新问题只进 deferred；③ 20 轮上限；
  ④ 超上限 `BLOCKED` +「建议推倒重开（revise the design）」；⑤ medium+ 全修；
  ⑥ low/nit 登记不修须写理由；⑦ 三种出口。
- **旧口径不再出现在规范面**：`templates/`、`plugin/`、`README.md`、`docs/design.md`、
  `docs/gate.md` 中不再有「3 轮封顶」「有界轮数」「轮数封顶」这类旧表述
  （`docs/gate.md:407/554` 的「常量封顶 / 路径深度封顶」与本规则无关，不动）。
- **两个环都覆盖**：`templates/grill.md` 的设计对抗环明确「与 review-loop 同构」，
  `templates/review-loop.md` 的实现环写明同一模型；grill frontier 追问轮显式豁免。
- **测试**：新增/改写的文档守卫变红 → 改文档 → 变绿；`uv run pytest -q` 全绿。
- **机械边界**：`witnessloop check` 判据零变化（不解析正文）；新增的只是文本与文档守卫。

## 测试策略

TDD。先写文档守卫（substring / 反 substring）让它们红，再改模板与文档让它们绿。
新增 `tests/test_convergence_stop.py` 钉住新模型的七个要素；改写 `tests/test_templates.py` 与
`tests/test_plugin.py` 里两条旧的「封顶」断言。不写「用自然语言判断语义」的测试——
文档守卫只能钉**措辞在场**，真正执行靠独立审阅者；这条诚实边界写进 design §6。
