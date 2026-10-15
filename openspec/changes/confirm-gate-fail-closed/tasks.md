# Tasks: confirm-gate-fail-closed

> 依据 `design.md`（**grill 与设计对抗验证八轮都已跑并已回写**——R1 判 CHANGES_REQUESTED（5 条）、
> R2–R4（各 3 条）、R5（2 条）、R6–R7（各 3 条）、**R8（3 条一行改正）**，
> 见 `design.md §7.1/§7.5/§7.9/§7.11/§7.13/§7.15/§7.17/§7.19/§7.21`；
> **R8 判 CONVERGED（可停轮）**；**停轮项 Q4 已由用户 2026-10-15 裁定「接受」**
> （答复见 `reviews/grill-design.md` 的 `## User Confirmation`；生效口径 = `design.md §8`）
> ⇒ **前置门已过，可进入实现**）。
> ⚠️ **不再有「3 轮封顶」**（用户 2026-10-15 裁定）：**修到收敛为止** ⇒ 若再审又出必改项，
> 按同样流程继续整合，**不许**以「到顶了」为由收工。
> 原则：**测试先行（TDD）**；判定面是 `evidence.grill_evidence_findings` 的**一处分支**
> + `stage_manifest_findings_in_change` 的**一处取法**（逐份而非 `matching[0]`，D8）
> + `_sections()` 的**一处新语义**（**跳过代码围栏**，D9）；
> 用例密集在**七件容易漏的事**上（标题写花必须红 / 空壳 + 近义装真问题必须红 /
> 两处候选并存必须不误伤 / **诱饵 manifest 不得改变判定** / **围栏里的示例不得当真** /
> **围栏对 `## Confirmed Decisions` 的输入面也要钉** / **用例不得「因为错误的理由通过」**
> ——每个钉子都要先确认它**今天**的红/绿来自正确的原因）。
> ⚠️ **本文件的否定用例一律 `X1…X16`**（不是 `N…`）：`N1–N33` 是**七轮审阅者**的非阻塞项编号
> （R1 `N1–N8`、R2 `N9–N12`、R3/R4 `N13–N17`、R5 `N18–N22`、R6 `N23–N27`、R7 `N28–N33`；
> **R8 未新增非阻塞项**——它的 3 条都按「归档前一行改正」直接落掉了），
> 两套前缀不同以免钉错东西（R2 的 N11；N21 指出过一处 R2 期的记述里仍写 `X1–X13`）。
> ⚠️ **纪律（R3 要求，R4 证明它必须留着）**：再发现**任何**假绿/假红面，
> **先往 `design.md §8.1` 的面清单加一行**，再加进 Q4 与 spec 的边界声明
> ——**只改一处就是下一次复发**（该缺陷已被打回**六次**；R4 的 B7、R5 的 B8、R6 的 G8 都靠它）。
> ⚠️ **且已机械化**：计数类一致性由 `tests/test_confirm_gate_docs.py` 守卫（对不上就红）。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/open-questions-gate/spec.md`）。
> ⚠️ **动手前先读 `design.md §1.1.1 / §1.2 / §1.5 / §1.6 / D1 / D2 / D8**：
> 「只判存在」与「宽松匹配」两支都**被实测否掉**——别再照抄 issue 里那三个并列选项的**字面**。

## A. 候选集合（D2/D3/D6）——判据的地基

- [ ] A1 单测（**先红**）：候选判定函数对 `design.md §D2` 那张表的**每一行**给出期望结果
      （逐字 ✅ / `Open Questions（收敛后）` ✅ / `Open Questions（**只有这一条必须用户拍板**）` ✅ /
      `Design-Level Open Questions（已并入 design 的 Q1–Q6）` ✅ / `Remaining Open Questions` ✅ /
      `逐条对抗（针对上游 … / 风险 / Open Questions）` ❌ / `Open Questions 汇总` ❌）
      —— 外加 **M3 的四条细则各一行**：`Open Questions (remaining)`（半角）✅ /
      `Open Questions（A）（B）`（连续尾括号）✅ / `Open questions`（大小写）❌（**且无附加提示**）/
      **M-E 两条**：`Open Questions（）`（**空括号**）✅ / `Open Questions（a（b）c）`（**嵌套**）❌。
      另两条已知副作用各一行：`Open  Questions`（双空格）❌ 无提示 / `Open Questions：` ❌ **有**提示
- [ ] A2 实现：模块级正则 + 纯函数（如 `_open_question_sections(sections) -> list[str]`）；
      ⚠️ **排序后**返回（候选来自 `dict` 的 key ⇒ 不排序会依赖插入序，F7 钉住）
- [ ] A3 单测（**先红·R2 的钉子**）：`## Code-Resolved Questions` **不是**候选
      ——即使它的正文里满是 `Q1`–`Q4`（本仓 6 份真实报告就是这形态）
- [ ] A4 单测（**回归护栏**）：`_sections()` 的 `setdefault` 合并语义**未动**——
      两个 `## Open Questions` ⇒ 同一 key、正文首尾相接；两个 `## User Confirmation` ⇒ 同上
      （⚠️ 这两条**实现前也绿**：它们钉的是「别顺手改掉既有语义」，变异证据见 §5.4）
- [ ] A5 实现（**D8 · M2**）：`stage_manifest_findings_in_change` 的 `:210` 附近——
      `verify_body=True` 时对 `matching` 里**每一份** manifest 各跑一次正文判据
      （`label` = `f"{label}/{rel_report}"`；`verify_body=False` 分支**不动**；
      「报告读不出」那条早退**逐份**适用、互不影响）
- [ ] A6 实现（**D9 · R2 的 M-D 第 5 类**）：`_sections()`（`:52-64`）增加**围栏状态机**——
      围栏内的行**不参与**小节切分。口径**逐字**照 spec 的「`_sections()` SHALL 跳过代码围栏」：
      开始 = 去空白后以 **≥3 个**连续 `` ` `` 或 `~` 开头；结束 = **同字符**、**不短于**开始标记、
      **其后只剩空白**；**未闭合** ⇒ 到文件末尾全算围栏内。
      ⚠️ 这是本 change **唯一**动 `_sections()` 的地方（D6 的例外）；**签名与合并语义不变**

## B. `grill_evidence_findings` 的正文判据（D1/D4）

- [ ] B1 单测（**先红·F3**）：**完全没有** Open Questions 类标题的报告 ⇒ 1 条
      `缺少 \`## Open Questions\` 小节`（与「缺 `## User Confirmation`」**同形**），且**不含**近义提示
- [ ] B2 单测（**先红·F1/否定 X1**）：只有 `## 悬而未决的疑问`（不含 `Open Question` 字样）+ 无确认 ⇒ **红**
      （今天 **0 条**——这条就是 issue 的招牌攻击）
- [ ] B3 单测（**先红·F1 第二档**）：只有 `## Open Questions 汇总`（含短语、不合 D2）+ 无确认 ⇒ **红**，
      且 message **同时**含 `缺少` 与 `Open Questions 汇总`（钉住「响亮报错」而不是静默）。
      ⚠️ 文案断言**不得**写成「这就是你的小节」那类判断句——提示只陈述观察到的事实（`design.md §D4`）
- [ ] B4 单测（**先红·F2/否定 X2·§1.5 的洞**）：逐字 `## Open Questions` **空着** +
      近义小节里放 `- **Q1** …` + `## User Confirmation` 空 ⇒ **红 1 条**
      （`Open Question Q1 未经用户确认`）——⚠️ 今天 **0 条**
- [ ] B5 实现：`:144-145` 两行改成「候选为空 ⇒ 红（两档文案）；否则 `body = "\n".join(候选正文)`」，
      逐 Q 循环**原封不动**
- [ ] B6 单测（**先红·否定 X7**）：同名 `## Open Questions` 两次、两次的 Q 不同 ⇒ **两个都要确认**；
      只确认一节 ⇒ **红**（钉住 D3 的**并集**方向）
- [ ] B7 单测（**先红·F9/X8 · D8 的钉子**）：一个 change 目录里放**两份** `stage=grill` manifest——
      `aaa.manifest.json` → 三节逐字齐全的合规**诱饵**、`zzz.manifest.json` → **不合格**的真报告
      ⇒ **逐条报出那 4 条**（与「没有诱饵」时**逐条相同**），且 label 指向那份的 `report_path`。
      ⚠️ 实现前：诱饵不在 **4 条**、诱饵在场 **0 条**（`design.md §1.1.1` 实测）。
      ⚠️ **fixture 的报告标题必须是逐字的 `## Open Questions`**（对抗轮 M-A）：拿「标题非逐字」的
      报告当 fixture，它在今天本来就少掉 Open Questions 那部分 ⇒ 用例会**因为错误的理由通过**
- [ ] B8 单测（**F10 · D8 的对照**）：同一造法但**两份都合格** ⇒ **0 条**（逐份 ≠ 「多份即红」）；
      另加：一份报告**读不出** ⇒ 该份报「无法核验」、**另一份**照常判定
- [ ] B9 单测（**X9 · M4 ②**）：候选小节**之外**的 `Q<n>` **不判**——在 `## Confirmed Decisions`
      的决策块里写「见 Q7 与 Q9」⇒ **0 条**
- [ ] B10 单测（**F11 · M-B 的边界钉子 · 护栏**）：真决策记录绑 `building`、`stage=grill` 绑合格 stub
      ⇒ **0 条**——**刻意接受**（今天与 D8 之后都一样）；这条用例守的是**边界声明 11**，
      免得将来有人把它当 bug「修」掉却不改声明
- [ ] B11 单测（**X10/F12 · M-D 的两条边界钉子**）：① 候选小节**内**、**不写成 `Q<n>`** 的问题
      （`- **问题**：…` / `待定：A 还是 B？`）⇒ **0 条**（钉住边界声明 1/3 的**收窄措辞**；
      ⚠️ 顺带钉一条反例：`- **Q１**`（全角数字）**会**被命中 ⇒ 1 条，**不是**漏判）；
      ② `### Open Questions`（H3）⇒ 候选为空 ⇒ **红**，且**断言附加提示不出现**（钉住已知盲区）
- [ ] B12 单测（**先红·F13/F14/X11 · D9 的钉子**）：① `## Open Questions` 有未确认 `Q1`、
      唯一的 `## User Confirmation`（含 `- **Q1**: …`）写在围栏里 ⇒ **实现前 0 条**、实现后 **2 条**；
      ② 围栏结构：` ```` `（4 个）开启 + 内部一行 ` ``` `（3 个）⇒ 那行**不**结束围栏；
      **未闭合**围栏 ⇒ 其后全部内容视为围栏内（其中的 `## Open Questions` 不成为候选）；`~~~` 同样生效；
      ③ **X11**：把围栏**拿掉**（写成普通小节）⇒ 变绿（钉住「围栏是唯一的差别」）
- [ ] B13 单测（**X12 · Q4 例子 5(b) 的边界钉子 · 护栏 · **两个输入都要**）**：
      ① `用户答复：待拍板；确认时间: t`（抽出正文 **3 字**，命中 `_UNCONFIRMED_STRONG`）⇒ **红 1 条**；
      ② `用户答复：待拍板，具体细节我会在下周的评审会议上确认；确认时间: t`（抽出正文 **21 字**）⇒ **0 条**。
      两句**只差长度** ⇒ **因正确的理由**钉住「长度阈值」；守的是 spec 边界声明 12。
      ⚠️ **不许**拿 `用户说待确认，稍后补上`（11 字）当第 ② 个输入（R3 的必改 1）：
      它绿是因为 `待确认` 只做**整串相等** ⇒ **把它原样截短照样绿** ⇒ 用例会**因错误的理由通过**。
      ⚠️ 实现时**先跑今天的行为**确认 ① 红、② 绿，再钉（该判据**今天就在**，不是本 change 新增）
- [ ] B14 单测（**X13 · D9 的对称代价钉子 · 护栏**）：`- **Q2**` 被围在**候选小节内的围栏**里 ⇒
      **实现前 1 条（红）**、实现后 **0 条（绿）**——**刻意接受**，守的是 spec 边界声明 13
- [ ] B15 单测（**X14 · Q4 第 7 类 / 声明 14 的钉子 · 护栏 · R4 主动构造**）：
      ① 某条决策的 `来源:` 写进围栏 ⇒ **实现前 0 条**、实现后 **1 条**「第 1 条 Confirmed Decision 缺 `来源:`」；
      ② **整条决策 bullet** 写进围栏 ⇒ **实现前 0 条**、实现后 **1 条**「只有 2 条，少于硬门槛 3 条」。
      ⇒ **刻意接受**（D9 读法 (i) 的另一侧代价）——用例守的是**声明 14**，
      免得将来有人把它当 bug「修」掉却不改声明
- [ ] B16 单测（**X15 · Q4 第 8 类 / 声明 6 的钉子 · 护栏 · R5 主动构造**）：一份报告有合格的
      `## Confirmed Decisions` + **逐字的** `## Open Questions`（正文 `（无）`）+ 一节
      `## Non-Open Questions`（正文 `- **Q9** …`）⇒ **实现前 0 条**、实现后 **1 条**
      （`Open Question Q9 未经用户确认`）。⚠️ 另跑 `## 未解决 Open Questions` 同款；
      **断言 `## Open Questions 汇总` / `## 悬而未决的疑问` 仍是 0 条**（钉住「多收」的边界，
      不是「凡像的都要确认」）。⇒ **刻意接受**，守的是**声明 6**
- [ ] B17 单测（**X16 · Q4 第 9 类 / 声明 15 的钉子 · 护栏 · R6 主动构造** · **两个方向都要**）：
      ① `## User Confirmation` 里同一个 `Q1` 写两行——占位在前、实质在后 ⇒ **0 条**；
      ② **对调**（实质在前、占位在后）⇒ **1 条**（`…的确认是占位文本`）；
      ③ 两条 `## User Confirmation` 小节各写一行 ⇒ 与 ①② **同款**（合并后仍按末行）。
      ⚠️ 该行为**今天就在**（`_confirmations` 是 `out[k]=v`）⇒ **先跑今天的行为再钉**，
      用例守的是**声明 15**（**刻意接受**的顺序相关性）

## C. 不误伤（**回归护栏**——本 change 的主要风险是「收紧必伤存量」）

- [ ] C1 单测（**F4**）：把 `openspec/changes/archive-awareness/reviews/grill-design.md` 的
      **真实内容**作 fixture（`:61` 非逐字 + `:110` 逐字两处候选）⇒ **0 条**。
      ⚠️ 这条是**护栏**（实现前后都该绿）：它证明「取并集」不把本仓自己的历史报告判红；
      变异证据：把候选集合改成「只取逐字那个」⇒ 仍绿（`:61` 的 Q1 在 `:110` 里也有）
      ⇒ **必须同时补一条「`:61` 里有独立 Q」的构造**才有变异信号（见 C2）
- [ ] C2 单测（**先红·D3 的钉子**）：构造「逐字小节装 Q1、近义小节装 Q5」⇒ 只确认 Q1 ⇒
      **红**（`Q5 未经用户确认`）。⇒ 这条才是「并集 vs 只取一个」的**变异钉子**
- [ ] C3 单测（**F5**）：那 1 份接入方非逐字报告（`Design-Level Open Questions（…）`）的**真实内容**
      ⇒ **0 条**（它的 Q1/Q2/Q6 都有实质确认）
- [ ] C4 单测（**F7·确定性**）：同一段文本连续调用两次 ⇒ 候选集合与 finding 逐条相同（含顺序）

## D. 回归面（逐条点名，`design.md §5.2`）

- [ ] D1 `tests/test_evidence.py` **全部 9 条**保持绿
      （尤其 `test_missing_sections_are_flagged`——它只断言「有 finding」⇒ 多数一条也过；
      ⚠️ 实现时先确认它**没有**精确计数断言）
- [ ] D2 `tests/helpers.py::VALID_GRILL_REPORT` 仍合格（三节逐字齐全）
      ⇒ 依赖它的集成用例（`test_check_grill_evidence.py` / `test_guard.py` / `test_archive_awareness.py` …）全绿
- [ ] D3 `tests/test_archive_awareness.py::SHORT_GRILL` 仍**只**因「`## Confirmed Decisions` 只有 2 条」红 1 项
      （别多出 Open Questions 相关的红）
- [ ] D4 `tests/test_manifest_build.py` / `test_check_protected.py` / `test_events*.py` 全绿
- [ ] D5 全量 `uv run pytest -q` 全绿（本 change **前**实测基线 = **521 passed**；
      ⚠️ **加上本 change 新增的守卫 `tests/test_confirm_gate_docs.py`（12 条）后，全量 = 533**
      ——别拿 521 对账（R6 的 N26））

## E. 产出方：模板与命令（`proposal.md` 目标 5）

- [ ] E1 `templates/grill.md`：**加一句硬口径**（§4 的产物结构块后）——
      `## Open Questions` **必须逐字**、**即使为空也保留小节**（写 `（无）`）；
      标题加了限定词 ⇒ 检查器认不出 ⇒ **红**。⚠️ **不新增小节**（结构块 `:107` 已经在产出它）
- [ ] E2 `templates/grill.md`：§硬约束 ③ 补「小节必须**逐字**存在」
- [ ] E5（对抗轮 N5）`templates/grill.md`：结构块（`:93-114`）**补一行 `## User Confirmation`**
      （或明写「停轮后追加」）——现状是它只在第 6 步（`:143-144`）提，而新判据把「小节存在」
      变成硬要求 ⇒ 产出方义务应**自洽**。⚠️ 这是**既有**状态、不是本 change 的新红
- [ ] E3 **复核**（**不改**）`plugin/commands/grill.md`：它只接线、不复制正文（其 `:7-9`），
      且它在 `:27` / `:29` 提到的 `## Open Questions` / `## User Confirmation` 是**行内 code span、
      不在行首** ⇒ `_HEADING_RE`（`evidence.py:31`）根本不当它们是标题
      ⇒ 既不能自造红、也没有第二种措辞可订正。**结论写进实现回报**（别默默跳过）
- [ ] E4 ⚠️ 改 `templates/grill.md` 前后跑 `uv run pytest -q tests/test_docs.py` 与 `tests/test_templates.py`：
      `templates/grill.md` 在 `RUN_ID_DOCS` / `IDEMPOTENCY_DOCS` 名单里 ⇒
      新写的句子**不得**出现未限定的「幂等」、且文件里必须**仍有**「确定性」

## F. 文档

- [ ] F1 `docs/gate.md §8`：判据段（`:392-393`）补「`## Open Questions` 必须**逐字存在**」
      与候选集合口径（近义标题的边界照 `design.md §2.5`）
- [ ] F2 `docs/gate.md §8`：接入指引补 **CQ2 的补救姿势**——「标题非逐字 ⇒ **追加**一个逐字小节即可，
      **不改审阅者原文**」（照本仓 `archive-awareness` 的先例）
- [ ] F3 `README.md:172`：补「（小节必须**逐字**存在）」
- [ ] F4 ⚠️ 改 `docs/gate.md` / `README.md` 前先读 `tests/test_docs.py`（守卫按**文件整体**扫：
      `Q3_DOCS` 的旧口径、`STALE_CLAIMS` 的动词面、`IDEMPOTENCY_DOCS` 的「幂等」限定语）；
      改完跑 `uv run pytest -q tests/test_docs.py`

## G. 证据链与收尾

- [ ] G1 ⚠️ **R5（自伤面）**：本 change 的实现 PR 落 `src/**` ⇒ 它**自己**要有
      `stage=grill` / `stage=grill-adversarial` / `stage=building` 三份 manifest，
      且**它自己的 grill 报告必须过新判据**（含**逐字** `## Open Questions`）。
      ⚠️ **本 change 的实际产物名是 `reviews/grill-design.md`**（M1：**不是** `grill-review.md`）
      ⇒ `manifest build --stage grill --report reviews/grill-design.md`。
      用错文件名 ⇒ 多出一份**未绑定的孤儿报告**、`contract.py:315-345` 直接判红
      （本仓 8 个 change 里 7 个用 `grill-review.md`、`archive-awareness` 用 `grill-design.md`
      ——**按实际文件名写**，别按惯例猜）。
      ⇒ 本 change 是这条判据的**第一个用户**；收尾时按 `docs/gate.md §3.1` 的「先内容、后证据」顺序落库
      （核过：该报告标题已**逐字**，`grep -c '^## Open Questions$'` = **1**）
- [x] G2 **八轮都已跑并已回写**（`design.md §7.1…§7.21`）：grill（产物 `reviews/grill-design.md`）与
      设计对抗验证 **R1–R8 八轮**（产物 **`reviews/grill-adversarial.md`** 的八节；
      R1–R7 均判 `CHANGES_REQUESTED`、**R8 判 CONVERGED** ⇒ **22 条必改 + 3 条一行改正**已整合）。
      ⚠️ **两份报告各建一份 manifest**（对抗轮 N6/M1 同款）：
      `manifest build --stage grill --report reviews/grill-design.md` 与
      **`manifest build --stage grill-adversarial --report reviews/grill-adversarial.md`**。
      漏绑的那一份会成为**孤儿报告**、`contract.py:315-345` 判红
- [x] G3 **停轮**：把 `design.md §8` 的 **Q4**（唯一一条，**各类残留全列**——⚠️ **不写死类数**：
      R4-② 与 R6-② 都是「这一处写死的类数过期」⇒ 以 `design.md §8` 的 Q4 正文为准，
      `tests/test_confirm_gate_docs.py` 会替你核）一次性交用户确认——**用户 2026-10-15 已裁定「接受」**，
      答复已逐条写进 **`reviews/grill-design.md`** 的 `## User Confirmation`（⚠️ 该小节标题**逐字**，
      且**追加**在审阅者原文之后，**不改其正文**——`design.md §2.6` CQ2；
      ⚠️ 该文件是审阅者维护的，**只读**，本 change 只**追加**）。
      ⚠️ 答复必须写成 `- **Q4**: 用户答复：…；确认时间: <date>` 形态（`_CONF_LINE_RE`），否则仍会红
      ⚠️ `## Open Questions` 那一节正文里**不得**出现 `Q` 加数字的字面
      （候选小节内的任何编号都会被要求确认——§4 R4；用「上文 CQ4/CQ5/CQ6」指代）
- [ ] G4 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] G5 PR（branch protection）→ 合入 → 关 issue **#23**
- [ ] G6 ⚠️ 本 change 的实现 PR **不要顺带归档别的 change**（那会让被归档的 change 按本 change 的
      新规则重判一次；见本仓 `archive-awareness` 的 H6 同款教训）
- [ ] G7（R1 的 N4 / R2 的 N9 / R4 的 N17 / R5 的 N22）**每轮整合后记一次在审稿指纹**：
      ⚠️ **同时复核计数类陈述**（面数 / 声明数 / Q4 类数 / 用例前缀上限）——
      本 change 已把这件事故化：**跑 `tests/test_confirm_gate_docs.py`**（机械守卫，
      文档里的数与实际结构不一致就红），别靠人数。在 `design.md §7.20` 的表里
      **追加一行**（口径：`sha256sum <按字典序的 5 条路径> | sha256sum`）。
      ⚠️ 触发点 = **任何一次**改动本 change 四份文档之后（否则「哪一稿被审过」在链上不可追）；
      ⚠️ `reviews/` 下两份报告**不进**该合值（它们是只读证据，改了就是另一回事）

## 明确不做（本 change）

`## Confirmed Decisions` / `## User Confirmation` 的口径（D7）· `_sections()` 的**合并语义与签名**
（D6；⚠️ **「跳过代码围栏」不在此列——那是 D9，本 change 要做**）·
「Open Questions 必须非空 / 必须写推荐答案 / 必须配例子」这类**内容质量**判据 ·
`design_hash` / 报告 ↔ design 内容绑定 ·
**跨仓**改接入方那份存量报告（`design.md §2.6` CQ6）· **禁止同 stage 重复 manifest**（D8 只让它们
**都被校验**，不禁止）· **`### `（H3）标题的识别**与**确认答复的真伪判定**（Q4 第 4 / 5(b) 类）·
退出码语义 · 签名 / 防伪造 ·
宽匹配（凡含 `Open Question` 字样都算候选——真理由是**边界不可解释**，见 `design.md §1.6` 的 ② 行订正）。

## 实测记录（立项期，基线 `ef8b3ab`）

> 命令与输出见 `design.md §1`；下游可直接重跑。**立项期未改动任何 `src/`**（本文件的 `[ ]` 全为空是刻意的）。

- **fail-open 对照（§1.2，招牌实验）**：取接入方真实报告
  `2026-09-30-workflow-dry-run/reviews/grill-design.md`，直调 `grill_evidence_findings`：
  原样 **0 条**；**只把标题改成逐字** ⇒ 仍 0 条（Q1/Q2/Q6 本有确认）；逐字 + 清空 `## User Confirmation`
  ⇒ **红 3 项**（Q1/Q2/Q6）；**非逐字** + 清空确认 ⇒ **0 条**。
  ⇒ **同一份正文、只换标题**，判据从「红 3 项」变「绿」（issue 的机制描述逐字成立）。
- **§1.5 的空壳绕过（今天绿）**：逐字 `## Open Questions` 留空（`（无）`）+ 真问题写进
  `## Design-Level Open Questions（…）` + `## User Confirmation` 空 ⇒ **0 条**。
  ⇒ 「只判存在」单独不闭合（这是本 change 选 ③ 的直接原因）。
- **`setdefault` 合并（§1.4）**：两个 `## Open Questions` ⇒ 同一个 key、正文
  `'- **Q1** 甲？\n\n- **Q2** 乙？\n'` ⇒ **并集**。两份真实报告（`adopter-test-gate:373/:410`、
  `events-readpoint-fix:102/:107`）各有**两个** `## User Confirmation` 且今天**绿** ⇒ 合并语义**已在被依赖**。
- **存量语料（§1.3/§1.6）——三份检出，计数一律 `find | wc -l` / `grep -l | wc -l` 复算**：
  - **`/home/happy/my-agent`**（HEAD `3c7196b`，branch `master`，**口径：限 `openspec/changes/`**）：
    `grill-design.md` **60 份**（**全在 `archive/` 内**）、逐字 `## Open Questions` **59**、
    非逐字 **1**、逐字 `## Confirmed Decisions` **60/60**、`*.manifest.json` **0**。
    ⇒ **issue 的 60 / 59 / 1 就是这一份检出**（三个数逐一命中）。
    ⚠️ **必须限定目录**（对抗轮 N8）：整棵 checkout 是 **148 份**——多出的 **88 份**在
    `.claude/worktrees/` 的**嵌套 worktree** 里。只写「60 份」会让人复现不出来。
  - `/home/happy/wl-review-a`（HEAD `6f75370`）：63 份（archive 内 62）、逐字 62、非逐字 1。
  - `/home/happy/wl-dryrun`：62 份、逐字 61、非逐字 1。
  - **三份检出里非逐字的那一份是同一个文件、同一个标题**
    （`archive/2026-09-30-workflow-dry-run/reviews/grill-design.md:46`）。
  - 本仓：`stage=grill` 报告 **8 份**，全部有候选标题；`archive-awareness/reviews/grill-design.md`
    **同一份里两处**（`:61` 非逐字 + `:110` 逐字）。
  - **③ 语义下的模拟：两份语料「新红 0」**（原型实现见 `design.md §D2` 的规则；实现期用真实现复算一遍）。
    ⚠️ **前提**：接入方检出里 `*.manifest.json` = **0 份** ⇒ 那些报告**今天不被门禁评估**；
    「新红 0」是「**假如都被绑定**」的模拟，**不是**今天跑 `check` 的观测。
- **诱饵 manifest（§1.1.1 · M2 · 新发现）**：两份 `stage=grill` manifest——
  `aaa.manifest.json` → 合规诱饵、`zzz.manifest.json` → **标题逐字**但不合格的真报告
  ⇒ 诱饵不在 **4 条**、诱饵在场 **0 条**。成因 = `evidence.py:210` 的 `matching[0]`。
  **已并进本 change（D8）**。
  ⚠️ **fixture 必须逐字**（对抗轮 M-A 纠正）：本记录初版用的是**标题非逐字**的真实报告、
  且把「拿掉诱饵 ⇒ 1 条」当成今天的结果——**那个数只在 ③ 之下成立**；今天的代码下它
  **拿掉诱饵是 2 条、有诱饵是 0 条**（有诱饵时 `matching[0]` 选中诱饵 ⇒ 真报告压根没被校验；
  它少的正是 Open Questions 那段，因 fail-open 本就整段不判）⇒ 会把
  「诱饵生效」与「fail-open」两个成因混在一起。本机直调复核：
  `逐字 4→0`、`非逐字 2→0`（`/tmp/c4-adv/probe2.py`）。
- **D8 关不掉的变体（§D8 · M-B · 作者侧已复现）**：真决策记录绑 `building`、
  `stage=grill` 绑**合格 stub** ⇒ `grill_evidence_findings_in_change` = **`[]`**
  ——**今天与 D8 之后都一样**。⇒ D8 的 claim 已**收窄**：它关的是「同 stage 多份」这一个变体。
- **M-E 括号实测**：`Open Questions（）`（空括号）⇒ **候选**；
  `Open Questions（a（b）c）`（嵌套）⇒ **非候选**。⇒ 已写进 spec 的 (b) 定义与 D2 第 4 条细则。
- **M-D 两条新残留实测**：① 候选小节**内**、非 `Q<n>` 形式（`- **问题**：…` / `待定：…`）⇒ **0 条**；
  ⚠️ 但 `- **Q１**`（**全角数字**）**会**被 `\bQ(\d+)\b` 命中（`\d` 匹配 Unicode 数字）⇒ 1 条
  （对抗报告称它 0 条——**不成立**，见 `design.md §7.6`）；
  ② `### Open Questions`（H3）⇒ 今天报 `第 4 条 Confirmed Decision 缺 \`来源:\``（H3 正文被并进上一节）。
- **D8 的存量代价 = 0**：本仓 8 个已落证据的 change，每个**恰好 3 份** manifest
  （`grill` / `grill-adversarial` / `building` 各 1）⇒ **无同 stage 重复**；本 change 自己 **0 份**；
  三份接入方检出 **0 份**。
- **② 行的订正（§1.6）**：本仓 `grill-adversarial-gate/reviews/grill-adversarial.md:21` 的标题
  `## 逐条对抗（针对上游 Confirmed Decisions / 证伪清单 / 风险 / Open Questions）` **含**
  `Open Questions` 字样——但它**只出现在 `stage=grill-adversarial` 的报告里**，
  而正文判据只作用于 `stage=grill`（`evidence.py:216-217` 的 `verify_body`）
  ⇒ 拿它当「宽匹配会假红」的**实测证据**是**错的**（立项稿初版这么写过，**已订正**）。
  排除宽匹配的真理由是**边界不可解释**。
- **`## Code-Resolved Questions` 的假红面（§4 R2）**：本仓 6 份报告的该小节正文里满是 Q 编号
  （`adopter-test-gate` `[1]`、`archive-awareness` `[2,3,4]`、`events-readpoint-fix` `[1,2,3,4]`、
  `grill-adversarial-gate` `[1,2]`、`grill-evidence-gate` `[1,3]`、`guard-crash-exit` `[1]`）
  ⇒ D2 必须把 `Question`（单数）排除在外，**A3/X6 是这条的钉子**。
- **M3 边界实测**：`Open Questions (remaining)`（半角）✅；`Open Questions（A）（B）` ✅；
  `Open Questions 汇总` ❌（红 + 提示）；`Open questions` / `open questions` ❌（红、**无**提示）；
  `Open  Questions`（双空格）❌（红、无提示）；`Open Questions：` ❌（红、**有**提示）；
  `Non-Open Questions` ✅（多收一节，fail-closed 方向）。
- **M4 边界实测**：① `_sections()` **不跳代码围栏**——把 `## User Confirmation` +
  `- **Q1**: …` 写进 ` ```markdown ` 围栏（围栏外没有那一节）⇒ `_sections()` 的 keys 里**有**
  `User Confirmation`、确认**被取到**、判据 **0 条（绿）**；② 候选小节**之外**的 `Q<n>` **不判**
  （决策块里写「见 Q7 与 Q9」⇒ **0 条**）。
- **行号核对（§1.1）**：issue 引的 `evidence.py:24-26` / `:52-64` / `:140-142` / `:144` 在本树**逐字命中**；
  「少于 3 条」那段 issue 写 `:126-131`、本树是 **`:126-133`**（`Finding(...)` 的收尾行）。
  M2 点名的 `:197-210` 也**逐字命中**（`:197` `matching = [`、`:200` `if not matching:`、`:210` `_, doc = matching[0]`）。
- **全量测试基线**：`uv run pytest -q` = **521 passed**（`ef8b3ab`）。

## 实测记录（grill 回写期 · 审阅者 run `grill-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`）

独立零记忆审阅者在**隔离副本**里重跑了全部关键实测（原报告见 `reviews/grill-design.md`）；
**作者侧**逐条复核并整合（`design.md §7.2`）：

- **它复现的**：§1.2 的 E1–E4 四个数逐个一致；§1.5 的空壳洞今天 **0 条**、① 下**仍 0 条**（⇒ ① 不闭合）、
  ③ 下 **1 条**；「③ 新红 0」独立复算（接入方 0/0、本仓 0/0；① 为 1/0；strawman 4/1）；
  把本稿 spec 的语义**真做出来**（副本 `/tmp/probe-patched`）跑全量 ⇒ **521 passed**。
- **它挖出的 M2**（本稿初版没有）：`evidence.py:210` 只校验排序第一份 ⇒ 诱饵即可让三条正文判据一起失效。
  **作者侧已独立复现**（`/tmp/c4-probe/m2b.py`：③ 之下诱饵在场 **0 条**、拿掉诱饵 **1 条**）⇒ 已并进本 change（D8）。
- **它挖出的 M3/M4**：D2 的括号/大小写/连续尾括号未定死；边界声明缺「围栏不跳」与「候选小节外不判」。
  **作者侧已逐条实测复核**（见上两段）⇒ 已写进 D2 的三条细则与 spec 的边界声明。
- **它提的订正 1–4 已全部整合**：§1.6 ② 行的自相矛盾（真理由是边界不可解释，不是误伤）；
  §2.5 的残留洞换例子（`## Code-Resolved Questions`）；Q3 的风险订正（`report_hash` 先拦）；
  `proposal.md` 的「存量影响 0」补前提。
- **⚠️ 作者侧对它的**一处**订正**（`design.md §7.3`）：它称「issue 的 60/59/1 在任何检出里都复现不出来」
  ——**不成立**：它的扫描范围是 `/home/happy/wl-*/`，而 **`/home/happy/my-agent`**（60/59/1）
  不在该 glob 内。⇒ 以**三份检出对照表**为准（`design.md §1.3`）。
- **停轮队列**：它判定立项稿的 Q1–Q3 全部可由代码/实测定案 ⇒ 已移入 `design.md §2.6`（CQ4/CQ5/CQ6）；
  **唯一停轮项**是它新提的 **Q4**（残留洞的接受面，含 `## Code-Resolved Questions` 这个藏身处）。

## 实测记录（对抗轮回写期 · run `grill-adversarial-reviewer-confirm-gate-fail-closed-ef8b3ab73d39`）

独立零记忆审阅者判 **CHANGES_REQUESTED**（**不推翻方案方向**；5 条必改全在证据/措辞/边界层）。
**作者侧**逐条复核并整合（`design.md §7.5`）：

- **它独立复现为真**（不推翻）：E1–E4 四个数；① 不闭合 / ③ 闭合（空壳洞今天 0 条、① 下仍 0 条、
  ③ 下 1 条）；`setdefault` 合并；D2 判定表 **15 行逐行**一致；M4 两条边界；
  `③+D8` 原型 **521 passed**；D8 存量代价 0；「新红 0」（且更强：逐文件计数**全部不变**）；
  M1 已修、`plugin/commands/grill.md` 不改、本 change 自己报告标题逐字。
- **M-A（证据因果写错）已修**：诱饵 fixture 换成**标题逐字**的不合格报告（无诱饵 **4 条** → 有诱饵 **0 条**）。
  作者侧复核：**成立**。
- **M-B（claim 收窄）已修**：实测「真记录绑别的 stage + grill 绑合格 stub」⇒ 今天与 D8 之后都 **0 条**
  ⇒ 收窄为「D8 关的是**同 stage 多份**这一变体」+ spec 边界声明 11 + Q4 例子 2。
  三条替代路（规范文件名 / 全篇扫 / 机械认定）各自否掉的理由写进 `design.md` D8。
- **M-C（内部矛盾）已修**：统一为「**只有 ①** 被实测排除；② 同样闭合、存量同样 0，
  但**边界不可解释**（设计判据）；③ 是**同时满足闭合与可机械判定**的那条」。
- **M-D（边界越界 + 漏两条）已修**：边界声明 1 收窄为「**以 `Q<n>` 形式**声明过的」；
  补残留洞 B（候选小节内非 `Q<n>`）与 C（非 H2 的 `### Open Questions`）。
- **M-E（漏定死一条）已修**：补「括号内容不含嵌套、空括号同样剥」+ 2 判定行 + 2 用例 + 2 变异行。
- **非阻塞项已处理**：N1（§1.7 → §1.1.1，排在 §1.2 之前）、N5（模板结构块补 `## User Confirmation`
  ⇒ E5）、N6（G2 点名对抗轮产物 + `manifest build --stage grill-adversarial`）、
  N7（同报告重复报 ⇒ spec 边界声明 10）、N8（`my-agent` 计数补口径）。
- **⚠️ 作者侧对它的一处订正**（`design.md §7.6`）：它称 `- **Q１**`（全角数字）「同样 0 条」——
  **不成立**：`\bQ(\d+)\b` 的 `\d` 在 `str` 模式下匹配 Unicode 数字 ⇒ 实测命中、报 1 条。
  它关于「`问题` / `待定` 这类非 `Q<n>` 形式不判」的**主结论仍成立**。
- **前置状态（供下游读）**：本 change 自己的 `reviews/grill-design.md` 过 checker = **2 条**
  （缺 `## User Confirmation` + 其 `Q4` 未经确认）——**停轮前的预期状态**，G3 补齐后消失。

## 实测记录（对抗轮 **R2 复审**回写期 · run `grill-adversarial-reviewer-r2-confirm-gate-fail-closed-ef8b3ab73d39`）

R2 判 **M-A～M-E 五条真收敛、语义不推翻**，另判 **CHANGES_REQUESTED（3 条新必改）**。
**作者侧**逐条复核并整合（`design.md §7.9`）：

- **R2-①（状态陈述不实）已改**：本文件抬头的「设计对抗验证尚未跑」与 `design.md §7`、本文件 G2
  **矛盾** ⇒ 已改成「两轮都已跑并已回写」。
- **R2-②（Q4 接受面缺第 5 类）已改**：`design.md §8` 的 Q4 从 **4 类扩到 5 类**；其中
  **(a) 围栏里的 `## User Confirmation` 示例 ⇒ 未确认的 Q 变绿** ⇒ **并进本 change 修掉（D9）**；
  **(b) `> 20 字`占位答复当实质确认** ⇒ 进 Q4 + **spec 边界声明 12**。
  作者侧复核（本机直调）：**(a) 修前 0 条 / 修后 2 条**；
  **(b) 短答复（`待确认`）⇒ 1 条、> 20 字答复 ⇒ 0 条**（阈值 `_UNCONFIRMED_MAX_ANSWER_LEN = 20`，
  `evidence.py:48`）。
- **R2-③（D8 ② 的因果写错）已改**：**成立**——实测 `grill-adversarial-gate/reviews/grill-adversarial.md`
  在 ③ 下**候选集合 = `[]`** ⇒ 初版那句「会去要求确认它那一节的编号」**不成立**。
  换成实测代价：**24 份已绑报告里 16 份**（`building` 8 + `grill-adversarial` 8）会变红。
  **结论不变**（该路仍不可取）。
- **R2-④（悬空引语 + 自相矛盾句）已改**：删掉那句引用（`grep 机械上不成立` 现在只命中 R2-④ 的记述本身），
  直接写收窄后的 claim。
- **R2-⑤（记指纹）已改**：`design.md §7.20` 新增指纹表（R1–R4 四轮 + 本轮稳定锚），并把「每轮整合后补记一行」
  写进本文件的 **G7**。
- **D9 的存量代价实测 = 0**：跳围栏前后 finding 数**一变不变**的语料 =
  本仓 `openspec/changes/**/reviews/*.md` **26 份** + 三份接入方检出 **63 / 60 / 62 份**，
  **合计 211 份、0 份有差别**。（⚠️ 标签口径已按 R3 §8.4② 订正：repo-wide 的 `*/reviews/*.md` 是 41 份；
  两套口径下都是 0。）
- **R2 的非阻塞项**：N9（⇒ G7 + §7.20）、N10（= R2-④）、**N11**（否定用例前缀 `N` 与审阅者非阻塞项
  `N` **撞车** ⇒ 本文件与 `design.md` 的否定用例**全部改成 `X` 前缀**
  （R2 当时止于 `X12`；R3–R5 逐轮加至 **`X15`**——别把这里的 `X12` 当成当前上限））、
  N12（`SHORT_GRILL` 锚点实测 `tests/test_archive_awareness.py:33`，原稿写 `:32-39` ⇒ 已对齐）。

## 实测记录（对抗轮 **R3 复审**回写期 · run `grill-adversarial-reviewer-r3-confirm-gate-fail-closed-ef8b3ab73d39`）

R3 判 **R2 的 3 条真修好**（并独立复算其数字）、**M-A～M-E 仍收敛**、**语义不推翻**，
另判 **CHANGES_REQUESTED（3 条新必改）**。**作者侧**逐条复核并整合（`design.md §7.11`）：

- **R3-①（5(b) 的例子演示不了那条规则）已改**：**成立**。本机端到端直调复核：
  `待确认`（3 字）⇒ **红**；`用户说待确认，稍后补上`（**11 字**）⇒ **绿**（因**无强占位词命中**）；
  `待拍板`（3 字）⇒ **红**；`待拍板，具体细节我会在下周的评审会议上确认`（**21 字**）⇒ **绿**。
  ⇒ 旧例子差的是**内容**不是**长度** ⇒ 四处同源订正（§2.5 / Q4 5(b) / spec 声明 12 / **B13**），
  并把**真实判据**（三层）写清。
- **R3-②（D9 的对称代价）已改**：**成立**。本机直调：`- **Q2**` 围进候选小节内的围栏 ⇒
  **今天 1 条（红）**、**跳围栏后 0 条（绿）** ⇒ 进 **Q4 第 6 类** + **声明 13** + **X13 / B14**。
  **不改代码**（机械分不出「引用」与「声明」）。
- **R3-③（同类残留）已改齐**：`§5.4` 的 `N6`/`N7` → **`X6`/`X7`**、`§7.6` 的 `N10` → **`X10`**；
  「11 条边界声明」→ **13 条**；`spec.md` 的「边界声明 4」→ **声明 6**；删掉 `design.md` 的**孤立残句**。
- **R3 的形式化纪律**：新增 **`design.md §8.1` 面清单**（13 个面 ↔ 11 条声明的对照表 +
  「先加表、再加 Q4 与声明」的规矩），把「接受面写全」从**每次靠人记**变成**表驱动**。
- **不再有「3 轮封顶」**（用户 2026-10-15 裁定）：本文件抬头已写明「**修到收敛为止**」；
  R3 节标题里的「封顶」只是历史字样。

## 实测记录（对抗轮 **R4 复审**回写期 · run `grill-adversarial-reviewer-r4-confirm-gate-fail-closed-ef8b3ab73d39`）

R4 判 **R3 的 3 条真修好**、**M-A～M-E 仍收敛**、**D9 的边界不推翻**、**语义不推翻**，
另判 **CHANGES_REQUESTED（3 条新必改）**。**作者侧**逐条复核并整合（`design.md §7.13`）：

- **R4-①（第 7 类：D9 也改了 `## Confirmed Decisions` 的输入面）**：**成立**，且是 R4 **主动构造**
  出来的。本机直调复核：`来源:` 进围栏 ⇒ 今天 **0** / 之后 **1**；整条 bullet 进围栏 ⇒ 今天 **0** / 之后 **1**。
  **消歧**：spec 那句两读，本机实测**只有读法 (i) 闭合 D9 的假绿**
  （围栏放在 `## User Confirmation` **小节内部**时：(i) ⇒ 1 条、**(ii) ⇒ 仍 0 条**）⇒ 已写死 (i)。
  同步 **§8.1 加 B7**、**Q4 第 7 类**、**声明 14**、**X14 / B15**，并把**四处**「判据一条不动」
  的 claim 收窄为「**判据的定义与实现不变；它看到的正文变了**」。
- **R4-②（G3 写「五类」）**：Q4 早已是六类 ⇒ **已改「七类」**。
- **R4-③（「已改」不实）**：glob 标签**三处全部补改**（`tasks.md` / `spec.md` / `design.md §D9`），
  并把那句 claim 改成事实描述；同时写清 **26 = `openspec/changes/**/reviews/*.md`**、
  **repo-wide = 41**、两套口径下都是 0。
- **R4 的非阻塞项**：N13（两个过期指针 ⇒ Q4 第 4 类 / §2.5 第 9 个数据行）、
  N14（「无论有无诱饵」⇒ 改成「拿掉诱饵 2 / 有诱饵 0」，两处同源）、
  N15（自查枚举补 **R5** ⇒ 14 面逐条枚举；「一一对上」⇒「各自有对应声明」）、
  N16（B10/B9 按编号排序）、N17（「三轮」→「**四轮**」+ §7.20 补 R4 行）。

## 实测记录（对抗轮 **R5 复审**回写期 · run `grill-adversarial-reviewer-r5-confirm-gate-fail-closed-ef8b3ab73d39`）

R5 判 **R3 / R4 的必改逐条真修好**、**M-A～M-E 仍收敛**、**读法 (i) 不推翻**、**语义不推翻**，
另判 **CHANGES_REQUESTED（2 条新必改）**。**作者侧**逐条复核并整合（`design.md §7.15`）：

- **R5-①（第 15 面：候选规则多收一节）**：**成立**，R5 主动构造。本机直调复核：
  `## Non-Open Questions` / `## 未解决 Open Questions`（正文 `- **Q9** …`）
  ⇒ **今天 0 条**、**新语义 1 条**。⇒ 已落 **§8.1 的 B8** / **Q4 第 8 类** / **声明 6**
  / **X15 + B16** 钉子，并把 `§D2` 那条**悬空指针**「（§2.5）」接到真落点。
- **R5-②（三处当前时态的 `13` 已过期）**：**成立** ⇒ 三处同步（声明 **14** / 面 **15** /
  `X1–X15`）。⚠️ **并按要求加机械守卫**（不再靠人数）：
  **新增 `tests/test_confirm_gate_docs.py`（6 条）**，从 change 目录的文档里抽出
  面数 / 声明数 / Q4 类数 / 否定用例上限，与 `§8.1` 与 spec 的**实际结构**逐项对账，
  对不上就红；**只扫本 change 目录**（归档后自动落到 `archive/<date>-<id>/`，找不到就 **skip**），
  同一条断言行里带「当时 / 已改 / R<n> / 历史 / 原稿 / 初版」等豁免词的**不算** ⇒ 不误伤历史记述。
  已做**变异验证**：把 `spec 声明总数` 改成 13 ⇒ 守卫**红**；还原 ⇒ 绿。
- **R5 的非阻塞项**：N18（宽松口径实测 **17** 不是 18 ⇒ 已订正并写清推导）、N19（「两处」→「三处」）、
  N20（§3.5 补**内联收窄句**）、N21（漂移行号 ⇒ 改成不带行号的指代；R2 期记述标注为历史）、
  N22（「四轮」→「**五轮**」+ §7.20 补 R5 行）。

## 实测记录（对抗轮 **R6 复审**回写期 · run `grill-adversarial-reviewer-r6-confirm-gate-fail-closed-ef8b3ab73d39`）

R6 判 **R5 的必改逐条真修好**、**第 15 面四处落点齐全**、**M-A～M-E 仍收敛**、**语义不推翻**；
它用 **33 组变异**量了守卫、并**主动构造**出第 16 面。3 条新必改，**都已整合**（`design.md §7.17`）：

- **R6-①（第 16 面：`_confirmations` 同键后写覆盖）**：**成立**。本机直调复核：
  同一个 `Q1` 写两行，**占位在前 ⇒ 0 条**、**对调 ⇒ 1 条**；两节 UC 合并后同款。
  ⇒ **§8.1 加 G8** / **Q4 第 9 类** / **声明 15** / **X16 + B17**；
  并**订正 D3 与 `§1.4` 末尾**那两处「只声明了 `_sections()` 的并集」的说法——
  写明「**并集只管到 `_sections()` 这一层**，下一层是后者赢」。
- **R6-②（守卫四个可绕口 + `skip` 过宽）**：**成立** ⇒ 守卫 **6 → 10 条**，逐条堵：
  ① `Q4-N` 落点存在性；② 面行**跳号**检测；③ **近似格式报错**；④ 找不到 change 目录 ⇒ **fail 不 skip**；
  ⑤ `tasks.md` G3 **禁止硬编码类数**。
  **变异验证原始行**（改坏 ⇒ 红、还原 ⇒ 绿）：
  `Q4-8 → Q4-99` ⇒ `FAILED test_face_rows_point_at_existing_q4_classes`（1 failed, 9 passed）；
  删 B8 行 + 计数同步 ⇒ `FAILED test_face_count_matches_proposal_claim`（1 failed, 9 passed）；
  `|  **B8b**  |` ⇒ `FAILED test_no_approximate_face_or_case_markup`（3 failed, 7 passed）；
  `* **X16**` ⇒ `FAILED test_negative_case_prefix_is_contiguous_and_claimed`（2 failed, 8 passed）；
  G3 写「九类」⇒ `FAILED test_task_g3_does_not_hardcode_the_class_count`（1 failed, 9 passed）；
  删 change 目录 ⇒ **10 errors / pytest rc=1**（原先 `6 skipped` / rc=0）。还原后 **10 passed**。
- **R6-③（两处过期）**：**成立** ⇒ ① G3 去掉硬编码类数 + 守卫 ⑤（该位置已过期两次）；
  ② `§8.1` 旁注按实测改 **19 / 五行**，并写明它被订正两次的**失效史**（N18 与 N22 互相打架）。
- **R6 的非阻塞项**：N23（skip ⇒ fail）、N24（211/35 的混合口径 ⇒ 已在 spec 写明统一口径
  525 / 187 / 211 **三套下都是 0**）、N25（守卫三处 raw 扫描改走豁免）、
  N26（**521 是 change 前基线；加守卫后全量 = 533**，已写进 D5）、N27（= 守卫缺口 ①）。

## 实测记录（对抗轮 **R7 复审**回写期 · run `grill-adversarial-reviewer-r7-confirm-gate-fail-closed-ef8b3ab73d39`）

R7 判 **R6 的 3 条必改「2 条真修好、1 条没关上」**、**第 16 面落点齐全**、**M-A～M-E 仍收敛**、
**语义不推翻**；它用 **25 组变异**量守卫，并**主动构造 9 组**找第 17 面 —— **没撞出新面**。
3 条必改，**都已整合**（`design.md §7.19`）：

- **R7-①（守卫第②条没关上）**：**成立**——删 **B8**（末位）+ 计数同步 ⇒ `10 passed`。
  ⇒ 改成**结构性断言**：面行 id **集合 == §8.1 逐条枚举的 id 集合**（`test_face_rows_match_the_enumeration_line`）。
  **变异验证原始行**：删 B8（末位）⇒ `FAILED test_face_rows_match_the_enumeration_line`（1 failed, 9 passed）；
  删 B7 ⇒ **2 failed**（另含 `test_every_face_has_a_declaration…`）；删 R5（中间位）⇒ 1 failed；
  删 G8 ⇒ **2 failed**；还原 ⇒ **11 passed**。
- **R7-②（旁注「五行 / 19」）**：**成立**（实测 **20 / 六行**，同一位置第 3 次）。
  ⇒ **不再写死这两个数**，改成**公式** + 指向**新加的恒等式守卫** `test_loose_caliber_identity`
  （`宽松 = 严格 − B 行数 + 指纹表行数`）。
- **R7-③（「全量 = 527」）**：**成立**（R7 当时 531；**本轮加第 11 条守卫后 = 532**）⇒ 两处同步 **532**，
  并全库扫过同类「全量 / passed」数字（只剩 `521`（change 前基线）与 `532` 两种正确表述）。
- **R7 的非阻塞项**：N28（② 覆盖面写进 docstring）、N29（③ 扩到**全角竖线 / 列表 / 引用** +
  **Q4 缩进检测** —— 三种写法与 2 空格缩进**全部由绿转红**）、N30（⑤ **扫全部** G3 行 + 豁免 ——
  第二行硬编码**转红**）、N31（§8.1 的 R1 行补「首节变体 ⇒ 静默绿」）、
  N32（接入方 fixture 改**绝对路径**）、N33（第 16 面措辞改「取舍」，并补记第三条改法的代价）。
- **守卫的设计天花板**已写进 `tests/test_confirm_gate_docs.py` 的模块 docstring（R7 §1.6）：
  它保证**四份文档内九个写死模式**的一致性，**不保证「该在的东西还在」**。

## 实测记录（对抗轮 **R8 复审**回写期 · run `grill-adversarial-reviewer-r8-confirm-gate-fail-closed-ef8b3ab73d39`）

R8 判 **CONVERGED（设计已收敛，可进停轮）**，明确「**不建议再开第 9 轮**」；**第 18 面搜索没撞出新面**。
3 条「归档前一行改正」**已全部落掉**（纯文本，不动语义 / 不动实现清单 / 不动 spec 的 Requirement）：

- **R8-①（假保证）**：**空逐字 H2 + `### Open Questions` 装真问题** ⇒ **0 条、新语义下仍 0 条**
  （本机直调复现）⇒ 声明 2 / Q4 第 1 类的边界放宽成「**不是候选**的标题（**含 H3 形态**）」；
  §8.1 的 **R1** / Q4 **第 4 类** / **声明 4** 的方向句改准（并进 UC **或它是首节** ⇒ **静默绿**，
  归入第 1 类 / 声明 2）；R7 那句「以**存在前置小节**为前提」订正为「以『**上一节是 CD**』为前提」。
- **R8-②（交叉引用）**：守卫 docstring 的 **3 处 `§7.18`** → **`§7.20`**（同类 `§7.14` 也一并改齐）。
- **R8-③（未守卫的计数）**：已**接进守卫** —— 新增 `test_face_declarations_and_totals_are_consistent`。
  **变异验证**：「落在 13 条」→ 9 ⇒ `FAILED`（1 failed, 11 passed）；「≠」→「=」⇒ `FAILED`；还原 ⇒ `12 passed`。
- **R8-④（公式文本）**：取「**写进天花板**」——docstring 补「公式的**文本**不受守卫保护」+
  §8.1 的「机械钉住」改成「机械钉住**那条恒等式**」。**变异**：公式 `+`→`−` ⇒ **仍 12 passed**（已声明）。
- **R8-⑤**：N31 括注已按 R8-① 改准；docstring 另补「**自洽地加面**同样绿」（原只写了删侧）。
- **同步**：守卫 **12** 条、全量 **533**；轮次「七」→「**八**」；§7.20 指纹表加 R8 行。
