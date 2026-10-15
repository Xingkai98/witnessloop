# open-questions-gate — `## Open Questions` 逐条确认判据 fail-closed

> 本 change 的能力增量：① 把 `check` / `guard` 对 grill 决策记录的第三条正文判据
> （「每个 Open Question 都必须有用户确认」）从 **fail-open**（取不到小节就静默跳过）
> 改成 **fail-closed**（小节缺失即红），并把「**像 Open Questions 的小节**」一并纳入候选；
> ② 让这条正文判据**对每一份** `stage=grill` 的 manifest 各跑一次
> （今天只校验排序第一份 ⇒ 一份诱饵 manifest 就能让正文判据整段失效）。
> ⇒ 「改一下标题」与「**同一个 stage 放多份、诱饵排序在前**」这两条路径被堵住。
> ⚠️ **不包括**「真决策记录绑到别的 stage」（`stage=grill` 只有一份合格 stub）——
> 那条不在机械面内，见边界声明 11 与停轮项 Q4 的例子 2。

## Requirement: `## Open Questions` 小节必须存在（与 `## User Confirmation` 对称）

`witnessloop check` 与 `witnessloop guard` SHALL 在 grill 决策记录的正文里要求存在
**候选 Open Questions 小节**（定义见下一条 Requirement）；一个都不存在时 SHALL 报错并非零退出，
措辞 SHALL 与「缺 `## User Confirmation`」那条**同形**（`缺少 \`## <标题>\` 小节`）。

该判据 SHALL 由 `evidence.grill_evidence_findings`（**唯一一处**实现的纯函数）承担，
`check` 与 `guard` SHALL 共用它——SHALL NOT 新增第二处实现或第二套「什么算 Open Questions 小节」的定义。

### Scenario: 整份报告没有 Open Questions 类标题
- **Given** 一份 `stage=grill` 的 manifest 绑定着的报告，正文里有 `## Confirmed Decisions`（3 条带 `来源:`）
  与 `## User Confirmation`，但**没有任何**含 `Open Question` 字样的二级标题
- **When** 运行 `check`（或 `guard` 拦住该 change 的代码路径）
- **Then** 报错并非零退出，message 含 `缺少 \`## Open Questions\` 小节`

### Scenario: 与 `## User Confirmation` 的缺件同形
- **Given** 一份报告同时缺 `## User Confirmation` 与任何 Open Questions 类标题
- **When** 运行 `check`
- **Then** **两条** finding 都在，且两条 message 的形状**相同**（都点名各自的小节标题）
  ⇒ 判据面此后对称，不存在「一条 fail-closed、一条 fail-open」

## Requirement: 候选小节的判定（逐字 ∪ 紧规则近义）

「候选 Open Questions 小节」SHALL 以二级标题（`## <标题>`）判定，满足**任一**即为候选：

1. 标题**逐字**等于 `Open Questions`；**或**
2. **反复**剥掉标题**尾部的括号限定语**后，余下部分匹配 `^(?:\S+[- ])*Open Questions$`
   ——即 `Open Questions` 是**结尾的短语**，其前只允许空格 / 连字符分隔的词。
   - **「尾部的括号限定语」的定义**：一对**配对**的括号（全角或半角）**紧贴标题末尾**，
     且其**内容不含任何括号**（即**不接受嵌套**）；**空括号 `（）` / `()` 同样算**
     并 SHALL 被剥掉。

⇒ 该定义 SHALL **排除**「`Open Questions` 出现在括号中间」的标题
（如 `逐条对抗（针对上游 … / 风险 / Open Questions）`），也 SHALL 排除
`Question`（单数）形态（如 `Code-Resolved Questions`）——后者是本仓 6 份真实报告里
**满是 Q 编号**的小节，误判它会一次性产生大片假红。

**四条口径 SHALL 定死**（否则实现者各写各的）：

1. **括号全角 `（）` 与半角 `()` 都 SHALL 被剥**；
2. **匹配 SHALL 大小写敏感**（`Open questions` / `open questions` **不是**候选）；
3. **连续多个尾括号 SHALL 全部剥掉**（不是只剥一层）；
4. **括号自身的匹配**：括号内容**不得含嵌套括号**；**空括号同样剥**。
   （实测分歧点：`## Open Questions（）` ⇒ **候选**；`## Open Questions（a（b）c）` ⇒ **非候选**。
   换一个实现（如贪婪 `.*`）两行结果会**反过来**——所以必须写死。）

⇒ 由此**已知**的两条副作用（**有意接受**，写进**边界声明 6**）：标题含**双空格**
（`Open  Questions`）或**尾部全角冒号**（`Open Questions：`）时**不是**候选 ⇒ **红**；
前者连 D4 的附加提示也不出现（提示用的子串大小写敏感且要求连续）。方向仍是 fail-closed
（作者写了个检查器认不出的标题 ⇒ 红，而不是放行）。

### Scenario: 逐字标题是候选
- **Given** 报告里有 `## Open Questions`
- **Then** 它是候选（本仓 8 份 `stage=grill` 报告全部命中）

### Scenario: 尾部带限定语的近义标题是候选
- **Given** 报告里只有 `## Design-Level Open Questions（已并入 design 的 Q1–Q6）`
  （接入方 `archive/2026-09-30-workflow-dry-run/reviews/grill-design.md:46` 的真实标题）
- **Then** 它是候选 ⇒ 其正文里的 `Q<n>` **全部**进入逐条确认判据

### Scenario: 半角括号同样是限定语
- **Given** 报告里只有 `## Open Questions (remaining)`
- **Then** 它是候选（半角括号与全角同义）

### Scenario: 连续多个尾括号全部剥掉
- **Given** 报告里只有 `## Open Questions（A）（B）`
- **Then** 它是候选（剥多轮直到不再有尾括号）

### Scenario: 空括号同样剥
- **Given** 报告里只有 `## Open Questions（）`
- **Then** 它是候选

### Scenario: 嵌套括号不算限定语
- **Given** 报告里只有 `## Open Questions（a（b）c）`
- **Then** 它**不是**候选 ⇒ 报「缺少小节」并附加提示（方向 fail-closed：写了个认不出的标题 ⇒ 红）

### Scenario: 大小写不匹配则不是候选
- **Given** 报告里只有 `## Open questions`（或 `## open questions`），且 `## Confirmed Decisions` 与
  `## User Confirmation` 都合格
- **Then** 它**不是**候选 ⇒ 报「缺少 `## Open Questions` 小节」；⚠️ 附加提示**不出现**
  （提示用的子串 `Open Question` 同样大小写敏感）

### Scenario: 括号中间的短语不是候选
- **Given** 报告里有 `## 逐条对抗（针对上游 Confirmed Decisions / 证伪清单 / 风险 / Open Questions）`
- **Then** 它**不是**候选（本仓 `grill-adversarial-gate/reviews/grill-adversarial.md:21` 的真实形态）
  ⇒ 它的 Q 编号**不得**变成「必须被用户确认」的要求

### Scenario: `Code-Resolved Questions` 不是候选
- **Given** 报告里有 `## Code-Resolved Questions`，正文含 `Q1`–`Q4`
- **Then** 它**不是**候选 ⇒ 那些编号**不得**产生「未经用户确认」的 finding

## Requirement: 内容判据作用于**全部候选的并集**

每个候选小节的正文 SHALL **全部**进入逐条确认判据（`Q<n>` 取**并集**）：
`## User Confirmation` 里缺少任一编号的确认时 SHALL 报错。
SHALL NOT 只取「第一个」候选、SHALL NOT 只取逐字那一个候选、SHALL NOT 静默丢弃任一候选小节。

同名标题出现**两次**时 SHALL 沿用既有 `_sections()` 的合并语义（`setdefault` 使同名小节的正文首尾相接）
——即并集，SHALL NOT 改成覆盖式（那会让「要求变少」，方向错误）。

### Scenario: 空壳小节 + 近义小节装真问题（**本 change 的核心症状**）
- **Given** 报告里 `## Open Questions` 存在但**为空**（`（无）`），
  而 `## Design-Level Open Questions（…）` 里写着 `- **Q1** …`，且 `## User Confirmation` 为空
- **When** 运行 `check`
- **Then** 报错 `Open Question Q1 未经用户确认` 并非零退出
  （⚠️ 本 change **之前**这是**绿**的：空串 ⇒ 逐条确认循环零次迭代）

### Scenario: 两个都像的标题并存 ⇒ 并集、不误伤
- **Given** 报告里同时有 `## Open Questions（**只有这一条必须用户拍板**）`（非逐字）
  与 `## Open Questions`（逐字），且两者的全部 `Q<n>` 都在 `## User Confirmation` 里有实质确认
  （本仓 `archive-awareness/reviews/grill-design.md:61/:110` 的真实形态）
- **When** 运行 `check`
- **Then** 该条判据**通过**（两节都进候选、Q 取并集；不因「有两个相似标题」而红）

### Scenario: 近义小节里有独立编号 ⇒ 必须被确认
- **Given** 逐字小节里是 `Q1`、另一个候选小节里是 `Q5`，`## User Confirmation` 只确认了 `Q1`
- **When** 运行 `check`
- **Then** 报错 `Open Question Q5 未经用户确认`
  （钉住「并集」而不是「只取逐字那个」）

### Scenario: 同名小节出现两次
- **Given** 报告里有两个 `## Open Questions`，各自装着不同的 `Q<n>`，`## User Confirmation` 只覆盖其中一节
- **When** 运行 `check`
- **Then** 未被覆盖的那些编号逐个报「未经用户确认」
  （并集方向；既有 `setdefault` 合并语义 **不**改变）

## Requirement: 缺件诊断 SHALL 列出含该字样的标题

候选为空而报告中**存在**含 `Open Question` 字样的二级标题时，finding SHALL 在通用文案之外
**列出**这些标题（**全部、去重、排序**），使修法（改名）一步可达——
SHALL NOT 只给一句「缺少小节」让作者去猜；SHALL NOT 只列其中一个。

该提示 SHALL 只陈述**观察到的事实**（「报告里有这些含该字样的标题」），
SHALL NOT 断言其中某个「就是你的 Open Questions 小节」——含该字样的标题里既有真正的近义标题，
也有语义无关的（如 `## 逐条对抗（针对上游 … / Open Questions）`）。

### Scenario: 含字样但不合规则的标题被列出
- **Given** 报告里只有 `## Open Questions 汇总`
- **When** 运行 `check`
- **Then** message **同时**含 `缺少` 与 `Open Questions 汇总`

### Scenario: 多个含字样的标题都被列出（含语义无关的）
- **Given** 报告里既没有候选标题，又有一处 `## Open Questions 汇总` 与一处
  `## 逐条对抗（针对上游 … / Open Questions）`
- **When** 运行 `check`
- **Then** 两个标题**都**出现在提示里（不替作者挑「最像的那个」）

### Scenario: 压根没有含字样的标题时不给提示
- **Given** 报告的标题是 `## 悬而未决的疑问`（不含 `Open Question` 字样）
- **When** 运行 `check`
- **Then** 仍是通用文案 `缺少 \`## Open Questions\` 小节`，**不含**那句附加提示
  （避免把无关标题误导成「差一点就对」）

## Requirement: 正文判据 SHALL 作用于**每一份** `stage=<grill>` 的 manifest

正文判据（`verify_body=True`）SHALL 对 `stage` 匹配的**每一份** manifest 各跑一次
（各以其 `report_path` 解析出的报告为准），SHALL NOT 只校验其中一份（今天只取**排序第一份**——
`evidence.stage_manifest_findings_in_change` 的 `matching[0]`）。
每份的诊断 SHALL 带上**那份 manifest 绑定的相对报告路径**，以便定位是哪一份不合格。

`verify_body=False` 的调用方（`building` / `grill-adversarial`）SHALL **行为不变**
（它们只要求证据**存在**，逐份与取一份等价）。

理由：只校验一份时，放一份**排序在前**、绑着合规短报告的诱饵 manifest 即可让正文判据**整段失效**
（实测，**标题逐字的**不合格报告：诱饵不在 **4 条**、诱饵在场 **0 条**）。
本 Requirement 与 `contract.py` 既有的「**宁多报不漏报**」原则对齐。

⚠️ **本 Requirement 覆盖到哪、不覆盖到哪（claim 必须收窄）**：它关掉的是
「**同一个 stage 有多份 manifest、只有排序最前那份被校验**」这**一个变体**。
它**关不掉**「真决策记录绑到**别的 stage**（如 `building`）、`stage=grill` 绑一份合格 stub」
——那一造法下 `stage=grill` 只有 stub 一个 manifest ⇒ 逐份 = 只校验 stub ⇒ **通过**
（实测：本 change **之前**与 D8 **之后**都是 0 条 finding）。
⇒ 本门禁的**前提**是「`stage=grill` 那份 manifest 绑定的报告**就是**决策记录」——
这是前提，**不是**它证明的结论（见边界声明 10 与 11）。

### Scenario: 诱饵 manifest 不得让真报告的判据消失
- **Given** 一个 change 目录里有**两份** `stage=grill` 的 manifest：
  `reviews/aaa.manifest.json` → 一份三节逐字齐全的**合规诱饵**；
  `reviews/zzz.manifest.json` → 一份**标题逐字**（`## Open Questions`）但**不合格**的报告
  （`## Confirmed Decisions` 只 1 条 + 缺 `## User Confirmation` + 正文有 `Q1`/`Q2` 且未确认）
- **When** 运行 `check`
- **Then** 报出那 **4 条** finding（与「没有诱饵」时**逐条相同**）并非零退出
  （⚠️ 本 change **之前**：诱饵在场 **0 条**、不在场 **4 条**——只校验了排序第一的诱饵）
- ⚠️ **该 Scenario 的 fixture MUST 是「标题逐字」的那一份**：换成一个**标题非逐字**的
  不合格报告会让它在**今天的代码**下也少掉 Open Questions 那部分（fail-open）
  ⇒ 该 Scenario 会**因为错误的理由通过**，钉不住它自称要钉的东西。

### Scenario: 多份都合格则不额外报错
- **Given** 同一造法，但**两份**报告都合格
- **When** 运行 `check`
- **Then** 0 条 finding（「逐份校验」不等于「多份即红」）

### Scenario: 一份读不出不影响其余份
- **Given** 两份 `stage=grill` manifest，其一的报告无法读取/解码
- **When** 运行 `check`
- **Then** 该份报「无法核验该 stage 的证据」，**另一份**仍按自己的正文照常判定

## Requirement: `_sections()` SHALL 跳过代码围栏

小节切分 SHALL **完全忽略 Markdown 代码围栏内部的行**：

1. 围栏里的一个 `## <标题>` 行 SHALL NOT 创建小节；**且**
2. 围栏里的**任何行**（含普通文本行）SHALL NOT 进入**任何**小节的正文——
   即使该围栏出现在某个已有小节的**内部**。

⚠️ **第 2 条是写死的唯一读法（R4 的消歧）**：spec 初版写「其正文 SHALL NOT 进入任何判据」，
**两读都读得通**——(i) 围栏行不进**任何**小节正文；(ii) 围栏行不建小节、但仍计入**当前**小节正文。
**取 (i)**，理由是**唯一能闭合 D9 那个假绿的读法**（本机实测，同一构造）：

| 构造：`## User Confirmation` **小节内部**放一个围栏，围栏里是 `- **Q1**: 用户答复：甲；确认时间: t` | 结果 |
|---|---|
| **今天**（不跳围栏） | **0 条（绿）**——围栏里的那行被当成**真确认** |
| **读法 (i)**（围栏行不进任何小节正文） | **1 条**：`Q1 未经用户确认` ✅ **闭合** |
| **读法 (ii)**（围栏行仍计入当前小节） | **0 条（绿）** ❌ **不闭合**（那行照样落进 UC 的正文） |

⇒ 读法 (ii) **修不掉**这个假绿（它正是 D9 要修的那一格）⇒ **只取 (i)**。

⚠️ **(i) 的代价（同为写死，见边界声明 14）**：围栏里的 `来源:` 或**整条决策 bullet**
也一并不可见 ⇒ `## Confirmed Decisions` 的两条子判据（「≥3 条」「每条块内含 `来源:`」）会
**多报**（本机实测：`来源:` 写进围栏 ⇒ 今天 **0** 条、**之后 1 条**「第 1 条缺 `来源:`」；
整条 bullet 写进围栏 ⇒ 今天 **0** 条、**之后 1 条**「只有 2 条，少于硬门槛 3 条」）。
方向是 fail-closed（多报不缺报），代价面实测 **0 / 211**（没有一份存量报告在 CD 里用围栏放这些）。

**围栏的判定 SHALL 可机械判定**（CommonMark 风格，写死以免各实现各写）：

- **开始**：一行（**去首尾空白后**）以 **≥3 个连续**的 `` ` `` 或 `~` 开头；余下内容（info string）不限；
- **结束**：一行（去首尾空白后）以**同一字符**、**不短于**开始标记的连续个数开头，且**其后只剩空白**；
- **未闭合**：从开始标记到文件末尾的所有行 SHALL 视为围栏内部。

⚠️ **本定义刻意**不采用** CommonMark 的「最多 3 空格缩进」上限**：本 spec 写的是
「去首尾空白后」，⇒ 一条 **4 空格缩进**的 ` ``` ` **同样开围栏**。这条是**写死的**，
实现者 SHALL NOT 按 CommonMark 顺手收窄（那样会与 spec 不符）。
方向是 fail-closed（多吞内容 ⇒ 更容易报「缺小节」）。

理由（与 M2/D8 同类，**已并进本 change**）：不跳围栏时，报告里**引用**一段
`## User Confirmation` 示例就会被当成**真确认** ⇒ 一份**真有未确认 `Q<n>`** 的报告**变绿**
（实测：修前 **0 条**、修后报「缺 `## User Confirmation`」+「`Q1` 未经用户确认」）。
这与 M4 声明的「围栏不跳」是**同一件事的两面**，而**确认侧的那一面是假绿**（不是误报）。
⇒ 本 change 把它**修掉**，而不是仅声明（见边界声明 7 改写）。

⚠️ **存量代价实测 = 0**：跳围栏后 finding 数**一变不变**的语料 ——
本仓 **`openspec/changes/**/reviews/*.md` 26 份**、接入方三份检出 **63 / 60 / 62 份**
（合计 **211 份**，0 份有差别）。
⚠️ **标签口径**（R4 的必改 3 + R6 的 N24）：上面那个 **211** 是**混合和**——
**本仓算全** `reviews/*.md`（**26** 份）而**接入方只算** `grill-design.md`（**63 / 60 / 62** 份）。
⇒ 统一口径下的数：**全 `reviews/*.md` = 525 份**、**只 `grill-design.md` = 187 份**、
**原混合 = 211 份**；**三套口径下都是 0 份有差别**（R6 逐份复算过 525 与 187）。
本仓那 26 份是 `openspec/changes/**/reviews/*.md` 口径；**repo-wide** 的 `*/reviews/*.md` 是 **41 份**
（多出的 15 份在 `docs/reviews/`）——两套下也都是 0。

### Scenario: 围栏里的 `## User Confirmation` 示例不算真确认
- **Given** 一份报告：`## Confirmed Decisions` 合格、`## Open Questions` 里有未确认的 `Q1`，
  报告中**唯一的** `## User Confirmation`（连同一行 `- **Q1**: 用户答复：…`）写在 ` ```markdown ` 围栏**里**
- **When** 运行 `check`
- **Then** 报「缺少 `## User Confirmation` 小节」与「Open Question Q1 未经用户确认」
  （⚠️ 本 change **之前**是 **0 条**——围栏里那段被当成真小节）

### Scenario: 围栏结构本身不被误判
- **Given** 围栏用 ` ```` `（4 个）开启、内部含一行 ` ``` `（3 个）作为内容
- **Then** 内部那行**不**结束围栏（结束标记须同字符且不短于开始标记）
- **Given** 一个**未闭合**的围栏
- **Then** 其后的全部内容都视为围栏内部（含其中的标题行）

## Requirement: 产出方 SHALL 产出逐字小节（含为空时）

`templates/grill.md`（grill 决策记录的**唯一**正文出处）SHALL 明写：
`## Open Questions` 的标题 SHALL **逐字**、且**即使为空也保留该小节**（写 `（无）`）。
host 适配器（如 `plugin/commands/grill.md`）SHALL 只做接线、**不复制**该正文口径
（既有约定：适配器引用模板路径，不重复其正文）。

理由：本条 Requirement 把「小节必须存在」变成**机械要求**；若产出方不保证产出它，
用新模板生成的报告会被新判据自造红——即门禁与模板互相打架。

### Scenario: 模板产出逐字小节
- **Given** 通读 `templates/grill.md` 的产物结构块
- **Then** 它含**逐字**的 `## Open Questions`，且明写「即使为空也保留小节 / 标题必须逐字」

## Requirement: 其余两条判据的**定义与实现**不变（但其**输入面**因 D9 而变）

本 change SHALL NOT 改变：`## Confirmed Decisions` 的「顶层 bullet ≥3 条且每条块内含 `来源:`」
**判据的定义与实现**、`## User Confirmation` 的**存在性判据**、
`_sections()` 按 `##` 切小节并以标题为键的**语义**、以及 `Q<n>` 的既有抽取口径
（`\bQ(\d+)\b`，含散文引用）。

⚠️ **收窄（R4 的必改 1）**：初版写的是「本 change SHALL NOT 改变 `## Confirmed Decisions` 的……判据」
——**在含围栏的输入上这句话为假**：D9 让围栏行**完全**不参与切分 ⇒ 写在围栏里的 `来源:` 或
整条决策 bullet **不再进入** `## Confirmed Decisions` 的正文 ⇒ 那条判据的**行为**在那些输入上确实变了
（实测：`来源:` 进围栏 ⇒ 今天 0 条 / 之后 1 条；整条 bullet 进围栏 ⇒ 今天 0 条 / 之后 1 条）。
⇒ 准确的表述是「**判据的定义与实现不变；它看到的正文变了**」——见边界声明 14。

### Scenario: `## User Confirmation` 缺失仍红
- **Given** 报告其余部分合格但缺 `## User Confirmation`
- **Then** 仍报 `缺少 \`## User Confirmation\` 小节`

### Scenario: `## Confirmed Decisions` 不足 3 条仍红
- **Given** 报告只有 2 条 `## Confirmed Decisions`，其余合格
- **Then** 仍报「少于硬门槛 3 条」，且**不**新增 Open Questions 相关的多余红

## 边界声明（**写清机械门保证什么、不保证什么**）

1. **空小节 = 空真通过**：逐字小节存在但无任何 `Q<n>`（空行或写 `（无）`）时，本判据**通过**。
   这与本 change **之前**的行为一致，且「必须显式写 `（无）`」这类判据**没有安全收益**
   （作者照样能写 `（无）`）。
   ⇒ 本门禁保证「**以 `Q<n>` 形式**声明过的 Open Question 都拿到确认」；
   **不**保证「报告里没有未声明的 Open Question」。
2. **残留洞 A（写到了别的小节 · 停轮项 Q4 的例子 1）**：把真问题写进一个**不是候选**的标题
   ——**含 H3 形态**（`### Open Questions`）、也含「**含 `Open Question` 字样但不合候选规则**」的标题
   ——同时留一个**空的**（或非空的）逐字小节 ⇒ 本判据**通过**。
   ⚠️ **措辞口径（R8 订正）**：初版写「**不含** `Open Question` 字样的标题」，那**不是**这个洞的边界
   ——真正的边界是「**该标题不是候选**」。反例：`## Open Questions`（逐字、空）+ `### Open Questions`
   （装真问题）⇒ **0 条，且新语义下仍 0 条**（候选集合非空 ⇒ 缺件诊断 D4 也不触发）。
   ⚠️ **真正像真实误用的藏身处是模板**自带**的 `## Code-Resolved Questions`**
   （`templates/grill.md:104`）：把一条本该用户拍板的问题标成「能由代码定案」挪进去即可。
   例（接入方真实报告可复跑）：把 `:46` 那个带括号限定语的近义标题改成 `## Code-Resolved Questions`、
   另起一个正文写 `（无）` 的逐字 `## Open Questions` ⇒ **0 条（绿）**。
   机械门认不出它没见过的措辞。
   ⇒ **本门禁保证**：**声明在该小节里**的问题都拿到确认；
   **不保证**：**没有**被声明的问题——把问题写进**别的小节**
   （**包括 `## Code-Resolved Questions`**，模板自带、最像真实误用的那个藏身处）
   不在机械面的覆盖内。**防线是流程，不是文本匹配**：`templates/grill.md` 规定所有残留问题
   必须写进 `## Open Questions`；另有**流程强制**的三层兜底——对抗轮（零记忆、专事证伪）
   ＋ 独立审阅者 ＋ 人读最终报告。
   ⚠️ **用户 2026-10-15 已就此拍板：接受本条**（答复原文见
   `reviews/grill-design.md` 的 `## User Confirmation`）。**被否掉的更狠做法**：
   「报告里**任何位置**出现的 `Q<n>` 都必须被确认」——实测代价是**接入方新红 4 份、本仓新红 1 份**，
   红点全是**正文里的散文提及**（§8.1 的 R5 那一类放大到全篇），
   即**把准确率换成覆盖面**、并让人学会无视报警。
3. **残留洞 B（写对了小节、但没写成 `Q<n>` · 停轮项 Q4 的例子 3）**：
   **候选小节之内**，但**不写成 `Q<n>` 形式**的问题**完全不被判**。
   例：`## Open Questions` 正文写 `- **问题**：这个门禁要不要收紧？` 或 `待定：A 还是 B？`
   ⇒ **0 条 finding**（`\bQ(\d+)\b` 只认 `Q` + 数字）。
   ⇒ 这就是边界声明 1 措辞必须收窄成「**以 `Q<n>` 形式**声明过的」的原因。
   ⚠️ 反向的已知副作用：`- **Q１**`（**全角数字**）**会**被命中（`\d` 在 `str` 模式下匹配
   Unicode 数字）⇒ 报 1 条——**不是**漏判。
4. **残留洞 C（非 H2 的写法 · 停轮项 Q4 的例子 4）**：`### Open Questions`（H3）**不是**候选
   ——`_HEADING_RE` 只认 `## ` ⇒ 报「缺少小节」；且 **缺件诊断的附加提示不出现**
   （提示源是 `_sections()` 的 key，**只含 H2**）。此外 H3 那段正文会被并进**上一节**，
   ⇒ 还会附带一条**假红**（如「第 N 条 Confirmed Decision 缺 `来源:`」）。
   ⚠️ **方向断言要写准（R8 订正）**：**不是**「一律 fail-closed / 不会漏判」——
   H3 的正文**并进哪一节**决定结果：并进 `## Confirmed Decisions` ⇒ 多一条**假红**（fail-closed）；
   **并进 `## User Confirmation` 或自成首节** ⇒ 那一段**对判据不可见** ⇒ **静默绿**（**该形态下确实是漏判**）。
   ⇒ 本 change **只声明、不改判据面**（消掉假红要动 `_sections()`，属**明确的非目标**）；
   该漏判形态归入**残留洞 A**（声明 2 / Q4 第 1 类）的接受面。
5. **散文提及会变成要求（作用域 = **候选小节内部**）**：候选小节正文里被 `\bQ(\d+)\b` 命中的
   **任何**编号（包括「详见 Q3」这类引用）都会成为「必须被确认」的要求。
   这是既有抽取口径，本 change **不收紧**（收紧会漏判真正的 `Q<n>`）。
   ⚠️ **反过来也成立**：写在**候选小节之外**（`## Confirmed Decisions` / `## 风险` /
   `## Code-Resolved Questions` 等）的 `Q<n>` **不产生**任何要求（实测：决策块里写「见 Q7 与 Q9」⇒ 0 条）。
6. **近义判定是启发式**：候选定义只**收敛已知的真实写法**，不穷尽所有写法。
   两个方向都有已知形态（都是 fail-closed，**方向相反**）：
   - **落空**（该收没收 ⇒ **红**）：双空格 `Open  Questions`、尾部全角冒号 `Open Questions：`、
     大小写不符、**嵌套括号**、以及**标题行本身带反引号**——`` ## `Open Questions` `` ⇒ 逐字不等；
   - **多收**（不该收的收了 ⇒ **多要一条确认** · **停轮项 Q4 的第 8 类**）：
     **`## Non-Open Questions` / `## 未解决 Open Questions`** —— `^(?:\S+[- ])*Open Questions$`
     的「前缀词」比直觉宽 ⇒ 那个小节被当成**候选** ⇒ 它正文里的 `- **Q9** …` 会被**要求确认**
     （实测：今天 **0 条**、本 change 之后 **1 条**；见 `design.md §8.1` 的 **B8**）。
     ⇒ 本 spec **不**给 (b) 加「否定词黑名单」（`Non-` / `未` / `非`…）——那是**枚举否定词**，
     永远不完整，且会把规则从「一条正则」退化成「正则 + 词表」。
   它的价值是**可机械判定、可写进文档、可被测试钉住**——不是「完备」。
7. **代码围栏：本 change 已**修**（不再是一条「接受的洞」）**——`_sections()` 现在**跳过**围栏，
   所以「引用一段含 `## User Confirmation` 的示例即得真确认」这条**假绿已关闭**
   （见上一条 Requirement；存量代价实测 **211 份 0 影响**）。
   ⚠️ 与 M4 的关系：R1 曾把「围栏不跳」声明为**边界**（当时看到的是**误报**那一面：
   引用含 `## Open Questions` + 示例编号的片段会**增加**待确认项——方向 fail-closed、无害）；
   R2 指出**对称的那一面是假绿**（确认侧），⇒ 本 change **改判为缺陷并修掉**。
   ⚠️ 它确实是本 change 里**唯一**动 `_sections()` 的地方（D6 的例外，见 `design.md` D6/D9）：
   「按 `##` 切小节」仍只有一份实现，只是**多了一条「围栏内不算」的前置**。
   ⚠️ **围栏**外**的 `##` 行一律仍是小节**——包括**引用**一段模板示例的行。
   ⇒ 「在围栏外照抄一段 `## Open Questions` + `Q1` 的模板」会**真的**创建小节并**多要**一条确认。
   这是「按 `##` 切小节」的固有语义（方向 fail-closed：多报不缺报），**本 change 不收窄**；
   要引用就放进围栏。
8. **`guard` 侧随之变化**：同一纯函数被 `check` 与 `guard` 共用 ⇒ 本地守卫在「标题非逐字」
   时也会**拦**（本 change 之前放行）。这是**刻意**的：不给 `guard` 开豁免，
   否则等于承认「事前可以不带用户确认、事后必须带」。守卫可被绕过（不装 plugin / 用 Bash 写文件）
   是既有边界，与本条无关。
9. **不绑定 design 内容**：本判据只看 grill 决策记录的正文，
   **不**证明这些 Open Question 与 `design.md` 当前内容一致（本仓一贯不做 `design_hash`）。
10. **同 stage 多份 manifest 仍合法**：本 change 让它们**都被校验**，但**不**禁止重复
    （「要不要禁止同 stage 重复」不在本 spec 的能力面内）。
    ⚠️ 随之而来的噪声：两份 manifest 绑**同一份**报告 ⇒ 同一 finding 被报**两遍**
    （message 与 `label` 都逐字相同）⇒ 本 Requirement 里「`label` 能定位是哪一份」这条
    在这种情况下**失效**。**方向是多报不是漏报**，接受。
11. **`stage=grill` 那份 manifest 绑定的报告**就是**决策记录**（**本 spec 的前提**，
    不是它证明的结论 · 停轮项 Q4 的例子 2）：把真决策记录绑到**别的 stage**（如 `building`）、
    给 `stage=grill` 一份**合格 stub** ⇒ 本判据**通过**
    （实测：本 change 之前与本 change 的逐份校验之后**都是 0 条**）。
    ⇒ 本门禁**不**证明「作者心里的那份决策记录被校验过」；
    三类关掉它的办法（规范文件名 / 全篇扫 / 机械认定真记录）都被评估并否掉：
    第一类**无效**（把 stub 放在规范名上即可）；第二类**语义错且代价实测很大**——
    对 change 里**所有被绑定的报告**都跑正文判据，会让本仓 **24 份已绑报告里的 16 份**变红
    （`building` 8 + `grill-adversarial` 8，各自缺 `## Confirmed Decisions` / `## User Confirmation`），
    而它们**本来就不是决策记录**；第三类**不可判定**。⇒ 与「**防漂移、不防伪造**」的既有边界同类。

12. **确认侧沿用既有的占位启发式（三层，口径以代码为准）**（**停轮项 Q4 的例子 5(b)**）：
    `## User Confirmation` 的答复正文由 `_ANSWER_RE`（`evidence.py:36`）抽出 ——
    取 `用户答复：` 与 `；确认时间` **之间**的那段。`_is_unconfirmed`（`evidence.py:97-106`）
    对**抽出的正文**判三件事，**命中任一即算占位**：
    **(i)** 去空白后为空；**(ii)** 与 `_UNCONFIRMED_EXACT`（`evidence.py:39-42`，13 个词：
    `todo` / `tbd` / `n/a` / `na` / `无` / `none` / `待确认` / `未确认` / `待定` / `pending` /
    `待补充` / `占位` / `未决`）**整串相等**；**(iii)** 正文**长度 ≤ 20**
    （`_UNCONFIRMED_MAX_ANSWER_LEN`，`evidence.py:48`）**且含**任一 `_UNCONFIRMED_STRONG` 词
    （`evidence.py:43-46`：`待主 agent` / `待主agent` / `待用户` / `placeholder` /
    `tobeconfirmed` / `待拍板` / `未拍板`）。
    ⇒ **长度阈值只对「强占位词」生效**；`_UNCONFIRMED_EXACT` 走的是**整串相等**，与长度**无关**。
    实测（本机直调，端到端）：`待拍板`（3 字）⇒ **红**；
    `待拍板，具体细节我会在下周的评审会议上确认`（**21 字**）⇒ **0 条（绿）**。
    ⇒ 本门禁**不**验证「这句答复真的是人说的 / 真的拍了板」；且**本 change 选择不把强占位词扫描
    放宽到任意长度**（那会闭合本条，代价是合法长答复里提到 `待拍板` 就假红）。
    这是**刻意的取舍 + 能力上限**（同「防漂移、不防伪造」一类），**不是**「补不上」。
13. **围栏内的 `Q<n>` 也不进判据**（**停轮项 Q4 的第 6 类** · **D9 的对称代价**）：
    `_sections()` 跳过围栏 ⇒ 把 `- **Q2** …` **围起来**的那一行**不进入** `## Open Questions` 的正文
    ⇒ 该编号**不被要求确认**。实测：同一份报告（`Q1` 已确认，`Q2` 写在 ` ```text ` 围栏里）
    ⇒ 本 change **之前 1 条（红）**、**之后 0 条（绿）**。
    ⇒ 本门禁**不保证**「**被围起来的**问题拿到确认」——这是 D9 关掉确认侧假绿所付的**对称代价**：
    机器分不出围栏里那行是「**引用**」还是「**声明**」（那是语义区别，不是机械区别）。
    代价面实测 **0 / 211 份**（含围栏的 35 份里，没有一份在候选小节内放 `Q<n>`）；
    方向是**作者自伤**（要真绿得自己把问题围起来），不是外部绕过。
14. **围栏内的行同样不计入 `## Confirmed Decisions`**（**停轮项 Q4 的第 7 类** ·
    **D9 读法 (i) 的另一侧代价 · R4 主动构造**）：`_sections()` 完全跳过围栏 ⇒ 写在围栏里的
    `来源:` 或**整条决策 bullet** **不再进入**该小节的正文 ⇒ 那两条子判据会**多报**。
    实测（同一份合格报告，只把一处内容挪进围栏）：`来源:` 进围栏 ⇒ 今天 **0 条**、
    之后 **1 条**「第 1 条 Confirmed Decision 缺 `来源:`」；整条 bullet 进围栏 ⇒ 今天 **0 条**、
    之后 **1 条**「只有 2 条，少于硬门槛 3 条」。
    ⇒ 这就是「本 change **不改变** `## Confirmed Decisions` 判据」这句**必须收窄**的原因：
    **判据的定义与实现不变；它看到的正文变了**（见「其余两条判据的定义与实现不变」那条 Requirement）。
    代价面实测 **0 / 211**（没有一份存量报告在 CD 里用围栏放这些）；
    方向是 fail-closed（多报不缺报），且只有作者自己把 `来源:` 围起来才会触发。
15. **同一个 `Q<n>` 被确认两次时，末行赢**（**停轮项 Q4 的第 9 类** · **R6 主动构造**）：
    `_confirmations`（`evidence.py:85-94`）用 `out[int(...)] = …`（**后写覆盖**，**不是** `setdefault`）
    ⇒ `## User Confirmation` 里同一个编号写**两遍**时，**只有最后一行算数**，
    结果与**行序**相关。实测：`- **Q1**: …待拍板…`（占位）在前、
    `- **Q1**: …甲…`（实质）在后 ⇒ **0 条（绿）**；**对调 ⇒ 1 条（红）**。
    ⚠️ **本节与「内容判据作用于全部候选的并集」那条 Requirement 不矛盾**：那条管的是
    `_sections()` 这一层的**小节合并**（并集）；**同一编号的多次确认**走的是
    `_confirmations` 的**末行**语义——**两层不同**，本条把下面那层写清。
    ⇒ 本门禁**不保证**「每次重复确认都被看见」，也**不**对同一编号做一致性检查；
    改法（任一行为实质即算 / 全部行都须实质）都会开新的口子或误伤修复动作 ⇒ **声明，不修**。
