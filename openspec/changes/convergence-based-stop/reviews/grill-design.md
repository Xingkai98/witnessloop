# Grill: convergence-based-stop 设计追问

> 独立零记忆审阅者产出（2026-10-15）。**READ-ONLY**：未改动 `src/`、未 commit、未改被审 worktree 的 git 状态。
> 全部实验在 `/tmp` 下跑（`/tmp/term/*.py` 为本轮的判据模型）。
> 立场：**默认设计有问题，逐条证伪**；结论按「挑战而非确认」写，下面每条 Confirmed Decision 都是**我自己重跑出来的**，
> 与被审文档的出入写在「订正」与「必须修改项」里。

## Reviewer

- run id: `grill-reviewer-convergence-based-stop-ef8b3ab73d39`（未设 `WITNESSLOOP_RUN_ID` ⇒ 走 `templates/grill.md`「怎么取 run id」的确定性兜底形态 `<stage>-<role>-<anchor>`）
- 时间: 2026-10-15
- 被审 revision: `ef8b3ab`（`origin/main`；change 目录 `openspec/changes/convergence-based-stop/` **未提交**，工作区唯一变更）
- 方法（可复现）：
  1. **落点逐行核对**：`grep -n '封顶\|轮数\|有界轮' templates/*.md plugin/**/*.md plugin/README.md README.md docs/gate.md docs/design.md`（**计数取全量、不用 `head` 截断**）；再对 `docs/gate.md:432-461`（§9 全节）单独 `grep -n '轮'` 求证「§9 无轮数字样」。
  2. **判据建模与反例搜索**：`/tmp/term/ledger.py`（把 `design.md §1.3.2` 的五条形状规则、§1.3.3 的判据 A/B、§1.3.4 的 floor 逐条落成可执行模型）+ `/tmp/term/t2.py`（四类攻击用例）——**用真跑代替推理**。
  3. **旁证仓实测**：`/home/happy/wl-wt/confirm-gate-fail-closed`（**兄弟 worktree**，change 目录**未提交**）逐节读 `reviews/grill-adversarial.md`；`openspec/changes/*/reviews/grill-adversarial.md` 逐份抽轮次与 verdict。
  4. **接入方镜像复核**：`/home/happy/my-agent` 逐处 `sed -n '<n>p'` 读 9 个落点，并用 `find … | xargs grep -ln` 扫**全量文件**（⚠️ 我第一遍用 `grep -rn` 时它**跳过了 `.claude/`**，差点漏报，见 M7）。
  5. **回归基线**：`uv run pytest -q` = **521 passed**（44.93s，与被审稿一致）。
- 基线复核: `uv run pytest -q` = **521 passed**；本 change **零 `src/` 改动**的口径复核为真（`grep -rn '轮\|封顶' src/` 只命中 `policy.py` 的不变集常量上限）。

## Confirmed Decisions

- **决策：13 处落点逐条复核结果与立案稿**逐字一致**（11 处未漂 + 2 处漂移），「§9 全节无轮数字样」也成立。**
  理由（我的实测）: 全量 `grep -n` 命中 `templates/grill.md:21/131/206`、`templates/review-loop.md:11/90/101/153`、`plugin/commands/grill.md:25`、`plugin/commands/review-loop.md:2/29`、`plugin/README.md:37`、`README.md:236`、`docs/gate.md:478`、`docs/design.md:25`——**前 11 处行号逐条命中**；`README.md:213` 那段今天是 archive-awareness 的接入方行为变更（漂移为真）；`docs/gate.md:423` 是 §8 的「证据读不出」表，那句在 `:478`（**§10**）而不在 §9（漂移为真）。对 §9（`:432-461`）单独 `grep -n '轮'` ⇒ **唯一命中是 `:437` 的「两端证据」**（非「轮数」）⇒「§9 全节无『轮数』字样」为真。
  `来源: grill-reviewer-convergence-based-stop-ef8b3ab73d39`
- **决策：两条机械钉子逐字在场，且它们钉的正是要被删掉的说法；`tests/test_grill_adversarial_gate.py:180` 的 fixture 是**第三种**东西，必须排除而不能改。**
  理由: `tests/test_templates.py:257-258` = `# 有界轮数封顶` / `assert "轮" in text and "封顶" in text`；`tests/test_plugin.py:174-176` = `def test_review_loop_adapter_states_the_bounded_rounds(): … assert "轮" in text and ("封顶" in text or "上限" in text)`——**两条都逐字命中**，且都只做**正向子串**断言。`:180` 的 `report_body="# 对抗验证\n\n## Verdict\n**CHANGES_REQUESTED**\n\n三轮封顶，交人判断。\n"` 是 `test_report_whose_verdict_is_changes_requested_is_accepted`（`:167-184`）的输入，钉的是「**`check` 不解析 verdict 文本**」——我另核了实现：`evidence.stage_manifest_findings_in_change`（`src/witnessloop/evidence.py:172-199`）对 `grill-adversarial` 走 `verify_body=False`，而 `verify_body=True`（`grill`）那条也只查「3 条决策 + `来源:` + Q 确认」，**两处都没有任何 verdict 解析**。⇒ 排除它是**对的**。
  `来源: grill-reviewer-convergence-based-stop-ef8b3ab73d39`
- **决策：判据 A 与 floor 的交互**实测为真**——「第一次再审零位移」确实被挡住，A 最早在第 3 轮触发。**
  理由: 用 `/tmp/term` 的模型跑「R1 报 2 条 → 之后每轮 `新增=∅ ∧ 已关闭=∅`」：直接按 `design.md §1.3.3` 不设 floor 判，**R2 就触发 A**；按 §1.3.4 的 floor（`n ≥ 3`）判，**R2 不触发、R3 触发 A**。⇒ 作者「floor 挡『第一次再审零位移就停』」的说法成立，`spec.md:102-105` 的 Scenario 与实现一致。
  `来源: grill-reviewer-convergence-based-stop-ef8b3ab73d39`
- **决策：`HANDOFF` 的三段式自我区分（verdict 与「终止原因」两个字段）在既有三态表下**落得下去**，不需要动 verdict 三态。**
  理由: `templates/review-loop.md:75-81` 的三态表只管「审阅者对代码的判断」，`plugin/commands/review-loop.md:63` 与 `docs/gate.md §9` 引用它的口径也都是这个；`HANDOFF` 写进**另一个字段**（`- 终止原因:`）既不动三态表，也不与 `BLOCKED`（「设计或范围出了问题 ⇒ 停下、不自行修复」，`templates/review-loop.md:87-88`）的语义撞车。`design.md CQ2` 的定案我复核为**正确**。
  `来源: grill-reviewer-convergence-based-stop-ef8b3ab73d39`
- **决策：接入方 asterwynd 的 9 处引用**行号全部未漂**——但清单**不完整**（见 M7）。**
  理由: 逐处 `sed -n '<n>p'` 读 `/home/happy/my-agent`：`AGENTS.md:18`、`AGENTS.md:104`、`README.md:148`、`docs/requirements-process.md:45`、`docs/requirements-process.md:189`、`docs/interview-script/questions/Q14-dev-process.md:13`、同文件 `:56`、`scripts/check_openspec_artifacts.py:1139`、`:1623` ⇒ **9/9 逐字命中**（`:56` 就是那句「**3 轮封顶**：审阅不会无限循环…」，`:1623` 与 `:1139` 是同一句报错文案的两处）。但改用 `find … | xargs grep -ln` 的**全量**扫描后另见 `.claude/commands/review-loop.md:78/87/153`（3 处，见 M7）。
  `来源: grill-reviewer-convergence-based-stop-ef8b3ab73d39`
- **决策：新规则**不会**比旧规则更早停——floor 把 A/B 的最早触发点都钉在第 3 轮，与旧 cap 同点。**
  理由: 判据 A 要求 `n ≥ 3`；判据 B 的停滞计数从第 2 轮起（`design.md §1.3.4`、`spec.md:91-97`）⇒ 最早也要 R2 与 R3 连续 ≤ 0，即**第 3 轮**。用 `/tmp/term` 遍历：**不存在任何账本形状能让新规则在 R2 停**。⇒ 新规则的净效果是**只放宽、不收紧**（对「还在挖新问题」的环），这一条作者没写下来，但它是这套判据的可取之处，建议写进 `design.md §1.3.4` 作为对照。
  `来源: grill-reviewer-convergence-based-stop-ef8b3ab73d39`

### 订正（立项稿里被我的实测改掉的说法）

1. **`design.md §1.4`（`:169-185`）的终止性论证**不成立**，`2·|O_1| + 2` 这个上界**是假的**。** 见 M1——这是本 change 唯一的**阻塞性**发现。
2. **`design.md §1.2 ①`（`:31-52`）与 `spec.md:28-36` 把样本 ① 称为「**实测/实录**」，但该文件**不在被审 revision 里**，而且它**已经有 R4**。** 见 M2。
3. **`design.md D2` 的理由 #2（`:239-240`）是无条件表述，与 §1.4 的诚实边界自相矛盾。** 见 M3。
4. **issue 举的样本 `archive-awareness` 确实对不上仓内记录（立案稿的方向对），但作者换的 `dogfood-bootstrap` 不是最贴近的那个。** 见 M8。
5. **`design.md §5.1 T2`（`:452-459`）的反断言写成「子串黑名单 + 7 个硬编码文件」，强度不够。** 见 M4。
6. **`tasks.md G1-G5`（`:96-103`）不是可执行的测试**——本 change 零 `src/` 改动，而判据只活在 prose 里，这五条没有任何东西可以跑。见 M5。

## Code-Resolved Questions（**建议移出停轮队列**：能由证据/数学定案）

- **作者 Q1〔判据 B 的窗口宽度〕→ 不是「窗口多宽」的取舍，而是「现在的 B 根本给不出终止保证」——已由反例定案。**
  证据: 我按 `design.md §1.3.2/§1.3.3` 落成模型 `/tmp/term/ledger.py` 后构造了一条**完全合规**的账本（五条形状规则**零违规**）：
  `R1` 报 `{R1-1}`；此后**偶数轮**不修任何一条、新报 1 条（`净额 = −1`），**奇数轮**修掉上一条、不新报（`净额 = +1`）。
  实测结果（`/tmp/term/t2.py`）：`|O_n|` 在 `1,2,1,2,…` 之间摆动、净额序列 `[-1,+1,-1,+1,…]`、**跑 10000 轮判据 A 与 B 都不触发**（`停轮 = None / never`），而设计声称的上界是 `2·1+2 = 4`。
  ⇒ `design.md §1.4` 第 1 步「『净额 > 0』的轮次总数 ≤ `|O_1|`」是**非继**（non sequitur）：`|O|` 只有正净额轮才下降是对的，但**负净额轮会把它抬回去**，「再降就穿到负数」预设了没有负净额轮，是循环论证。§7 自曝 1 请对抗轮验证的就是这一点——**答案是否**。
  ⇒ 因此「窗口多宽」不是取舍；**「要不要真的给保证」才是**（进 `## Open Questions` Q1）。若选「给」，最小改动是把 B 从「连续两轮**每轮** ≤ 0」改成「最近两轮**累计** ≤ 0」（B′）；我实测同一攻击序列在 B′ 下于**第 3 轮**停轮，上界为 `W·(|O_1|+1) + 1`。
- **作者 Q2 〔「同一批问题」的粒度由谁定〕→ 由账本规则**结构性**定死，且作者担心的两个方向**都是反的**。**
  证据: 粒度选择只表现为「沿用旧 id」或「铸新 id」两种，二者都**合规**（规则 1/3）。但它们对判据的效果是可算的：**铸新 id ⇒ `新增 ↑` ⇒ `净额 = |已关闭| − |新增| ↓` ⇒ B 更容易触发**。所以「判成新问题可以无限续命」在**单步**上为假（它让停来得更快）；真正能续命的是**交替**（就是上面 Q1 的反例），而那与「粒度怎么判」无关。⇒ `design.md §8 Q2` 的推荐答案 ③（**显式声明沿用 + 给理由**）是**唯一可实现的答案**（`check` 不解析正文，D5；机械按锚点归并会把「同批」判宽，方向偏向提前停），**不必用户拍板**。
- **作者 Q2 的另一半〔issue 的两个样本要不要换名〕→ 要换，且**换成哪个**也能由仓内记录定案。**
  证据: ① `archive-awareness/reviews/building-review.md:24-26` 的 **R1 就是 `**PASS**`**，`reviews/grill-adversarial.md:1` 的标题是「（**第 1 轮 R1**）」且全文只此一轮 ⇒ issue 的样本名确实对不上。② 仓内真正「跑到第 3 轮」的环有 **4 个**（`adopter-test-gate` R3@`:432` `PASS`、`building-review-gate` R3@`:252` `PASS`、`grill-adversarial-gate` R3@`:425` `PASS`、`events-readpoint-fix` R3@`:489` `PASS`），其中 **`events-readpoint-fix` 的 R3 标题逐字写着「第 3 轮（R3 · **轮数封顶** · 最后一轮）」**——它才是 issue 原话「跑到第 3 轮才收敛」的**字面对应物**。见 M8。
- **作者 Q3 的**例子**（自指）复核为真，但它**不**说明规则形同虚设。**
  证据: 机制上，一份顶层 `## Verdict` 写 `CHANGES_REQUESTED`、另加 `- 终止原因: 未收敛（判据 B）` 的报告，走 `grill-adversarial` 门禁时 `verify_body=False`（`src/witnessloop/evidence.py:172-199`）⇒ **照样算证据齐备**。`docs/gate.md:476-478` 边界 ① 在**旧规则下就已经是这句**（「机械判据区分不了『封顶后交人』与『跑一轮就收工』」），所以本 change **既没让它变好也没让它变差**。⇒ 「规则形同虚设」这个说法对**门禁**太重、对**「可机械执行」这个宣称**却正好——而 `D5`/`§2.5` 已经照实写了这一点。**Q3 本身仍是用户取舍**（要不要为「人照合」新增一类证据与一类红）。

## Open Questions

> **三条**（Q1–Q3），逐条附具体例子。⚠️ 标题**逐字**不加后缀是**刻意的**——本仓 checker
> （`evidence.OPEN_QUESTIONS_TITLE = "Open Questions"`，`src/witnessloop/evidence.py:25`）按**逐字标题**
> 取小节，带括号的标题会命中不到 ⇒ 「每个 `Q<n>` 都要有用户确认」那条规则会变成**空真**
> （`archive-awareness` 的审阅者稿就踩过：它的 `## Open Questions（只有这一条必须用户拍板）` 被 checker 忽略，
> 主流程只好另加一个逐字小节，见 `openspec/changes/archive-awareness/reviews/grill-design.md:110-124`）。

- **Q1**: **终止保证的形态**——「无收敛才停」这句承诺，是要**真的**给出终止上界，还是接受「**条件保证**（账本如实且不交替）」并同步改弱卖点句？
  **例子（用本 change 自己的场景构造，已实测）**：`templates/review-loop.md` 改完后，某环的账本逐轮长这样——
  R1 报 `R1-1`（1 条）；R2 审阅者**又发现一条** `R2-1`、作者**一条没修**（`净额 = 0 − 1 = −1`）；R3 作者**修掉 `R2-1`**、审阅者**没发现新的**（`净额 = 1 − 0 = +1`）；R4 同 R2、R5 同 R3……
  五条形状规则**逐条满足**（`上一轮 ∪ 已关闭` 每轮都守恒），判据 A 永不成立（每轮 `新增` 或 `已关闭` 非空）、判据 B 永不成立（没有连续两轮 ≤ 0）。我实测这条序列跑 **10000 轮不停**。
  - **备选**：① **改判据 B 为「最近两轮累计净额 ≤ 0」**（我把同一序列喂进去 ⇒ **第 3 轮停**；上界 `W·(|O_1|+1)+1`，仍是导出量不是设定值）；② **保留现 B，把承诺降级**为「条件终止保证」并把 `design.md §6.1` 那句**卖点句**、`spec.md` 的「终止性由良基度量保证」Requirement 一起改弱；③ **补一个 backstop**（作者 D2 明确否决）。
  - ➡️ **推荐 ①**。理由：**它用一个词的改动换回真正的良基度量**（`Σ` 语义 vs 逐轮语义），不动「不看轮数」这个卖点、也不需要 backstop；②会让 §6.1 那句「轮数有上界（≤ 2 × 首轮问题数 + 2，是推导出来的，不是拍脑袋的数）」变成**已证伪的断言**，对**接入方**是一句假承诺。
- **Q2**: **判据 B 与 issue 原话的偏差要不要接受**——B 会在「**每一轮都真把上一轮修完了，只是越挖越深**」时停下交人，而 issue 给用户的定义是「**只剩同一批问题反复、没有新的实质发现** ⇒ 停下」。前者**有新发现**，按 issue 的原话**不该停**。
  **例子（`design.md §8 Q1` 的形态，我按现 B 复算）**：R1 报 5 条；R2 **修掉 5 条、又报 6 条**（`净额 = 5 − 6 = −1`）；R3 **修掉 6 条、又报 7 条**（`净额 = 6 − 7 = −1`）。⇒ 现 B 在 **R3** 停（连续两轮 ≤ 0）。但这两轮**一条都没欠**，且每轮都在挖更深的问题。对照：`confirm-gate-fail-closed` 的真实数字（R2 净额 `+2`、R3 有新增）⇒ 现 B **不会**在 R3 触发。
  - **备选**：① **接受**（B 只在「未关闭集合没有净缩小」时停，而「越挖越深」按本规格的定义**就不是收敛**；`HANDOFF` 不是收工，人看到「连续两轮净关闭 ≤ 0」这条机械事实后可以显式说「继续跑」）；② **加一条「新增单调不增」才算停滞**（⇒ **放弃终止保证**：可以构造每轮新增都比上轮多 1 的形态，永不满足）；③ **只用 A**（⇒ 完全放弃终止保证）。
  - ➡️ **推荐 ①**，但要求把话说全：`spec.md` 与 `templates/*.md` 必须写明「**B 比 issue 的原话更严**——它在『有新发现但净关闭 ≤ 0』时也会停」，否则接入方的访谈卖点句会把 B 讲成「没有新发现才停」，那是一句错话。
- **Q3**: **`HANDOFF` 之后人的「照合」要不要留结构化证据**（作者原文的 Q3，我复核后**维持**为需用户拍板）。
  **例子（本 change 自己的场景，机制已实测）**：本 change 的设计对抗环在 R3 触发 `HANDOFF`，报告顶层 `## Verdict` = `CHANGES_REQUESTED` + `- 终止原因: 未收敛（判据 B：…）`；用户看后回一句「**这条不是问题，照合**」。此时那份 `reviews/grill-adversarial.md` **照样算证据齐备**（`verify_body=False`，`src/witnessloop/evidence.py:181-186`），CI **绿**；人的裁定只活在 `tasks.md` / PR 描述的自由文本里，**没人读、也不可核**。
  - **备选**：① 沿用今天（零新红类，与 `docs/gate.md §10` 边界 ① 一致）；② `reviews/<stage>-override.md` + manifest（可审计，但新增硬门 + 对既有非 `PASS` 收尾是**新红类**）；③ 只在报告里加一张 `## 人裁定` 表（被 manifest 绑定、可复核，**不**进门禁判据）。
  - ➡️ **推荐 ①**（与本仓两次先例 `building-review-gate` 的 Q2 / `grill-adversarial-gate` 的 Q2 逐字同理由）；**若要 ③，必须同时说清它被谁读**——没人读的自由文本是摆设。

## 风险

1. **R1（**阻塞**·终止性论证为假）**：见 M1。这是本 change 的**目标 2**（「保留终止保证」）本身。逐条攻击结果（全部实测，`/tmp/term/t2.py`）：
   - **攻击 1「审阅者干脆不报新问题」（每轮 `新增=∅ ∧ 已关闭=∅`）**：**被挡住** ✓——R2 被 floor 拦下、**R3 触发判据 A ⇒ `HANDOFF`**。且 `HANDOFF` 不放行 ⇒ 这条攻击**拿不到 ship**。
   - **攻击 2「id 拆分续命」（`R1-3` → `R2-1` + `R2-2`，不记「已关闭」）**：**形状规则 5 能发现** ✓（我的模型给出 `R2: 集合守恒被破坏 ['R1-1','R1-2','R1-3'] != ['R1-1','R1-2']`），**但 `check` 不解析账本（D5）⇒ 无机械拦截**，只在「有第三方去读」时可见。
   - **攻击 3「关闭得名不副实」**：⚠️ **方向与作者设想相反**——虚报「已关闭」把 `净额` **推高** ⇒ 只会让 B **更晚**触发（是**续命**工具，不是提前收工工具）。⇒ 该攻击对「提前收工」无效，但它**与攻击 4 叠加**后正是 R1 的主形态。
   - **攻击 4「交替呼吸」（本文 Q1 的例子）**：**完全绕过** ✗——五条规则零违规、判据 A/B 都不触发、**10000 轮不停**。这是**唯一**能同时绕过 A 与 B 的形状，且**不需要任何伪造**（审阅者每两轮真发现一条新问题、作者每两轮真修掉一条即可）。
   - **攻击 5「首轮灌水」**：`|O_1| = 50` ⇒ 声称的上界 `102` 轮。⇒ 上界**由审阅者自己选择**，`§6.1` 的卖点句即便修好 B′ 也仍然是**弱**保证（`W·(|O_1|+1)+1`）；建议卖点句**同时**给出「**连续两轮无净进度就停**」这条**与规模无关**的实际刹停条件，别只卖那个上界。
   - **floor 之前那两轮能做什么**：R1 报问题（或 `PASS`）；R2 若零位移**只被推迟、不被接受**（实测：R2 不触发、R3 触发）⇒ **R2 不会被用来收工** ✓。代价是**恰好多跑一轮**（与旧 cap 同点，见 Confirmed Decision 6）。
2. **R2（高·证据不可复现）**：见 M2——本 change 的**头号实证**（样本 ①）落在**被审 revision 之外**的**未提交**目录里，且它的关键推论与被引文件**自身的 R4** 相反。对一份卖点就是「证据可复核」的 change，这是自伤。
3. **R3（中·守卫可被改宽）**：见 M4。反断言是可改写的**子串黑名单**，且扫描面是**硬编码的 7 个文件**——新加一份复述旧口径的文档不会被抓。
4. **R4（中·判据只活在 prose 里）**：见 M5。本 change **零 `src/` 改动**、`check` 不解析账本（D5 有意为之），而 G1–G5「用例」没有任何东西可跑 ⇒ **A/B、floor、五条规则的全部语义没有任何机械钉子**。这既是「语义随时可被后人改掉」的风险，也是**本次 R1 之所以能溜到设计评审才暴露**的原因。
5. **R5（中·多轮同文件时账本无锚点）**：见 M6。本仓既有报告**一律把多轮写进同一份文件**（`dogfood-bootstrap/reviews/building-review.md` 的 `## 第 2 轮审阅`/`## 第 3 轮审阅`；`confirm-gate-fail-closed/reviews/grill-adversarial.md` 的 `## R2 复审`/`## R3 复审（封顶）`/`## R4 复审`；`building-review-gate/design.md:53-62` 已把「轮次记法不统一」写成实测结论）⇒ 一份报告里会出现**多个逐字相同的 `## 问题账本`**，而 `evidence._sections`（`src/witnessloop/evidence.py:52-64`）对同名标题是 `setdefault` + 追加 ⇒ **会把它们合并成一个小节**。「第三方只读相邻两轮报告」在**同文件多轮**时**没有可指的锚点**。
6. **R6（中·账本诱使少报）**：作者已自认（`design.md R4`）——我复核为真且**方向确认**：账本不惩罚多报（只把 `|O_1|` 与上界推大），但**惩罚「漏报后再补」**（补进来算 `新增`，让 B 更易触发）⇒ 净激励朝向「一次报全」。但**它不能防「一开始就少报」**，而首轮少报会**同时**把上界压小、把 B 推后。
7. **R7（低·镜像清单不全且有一处改不到）**：见 M7。
8. **R8（低·自打脸）**：本 change 合入后自己的三份报告要按**新规则**产出（`tasks.md H1/H2/H4`）。我逐条核过：**机械上过得去**（`grill` 那条查的是 3 条决策 + `来源:` + Q 确认，与账本无关；`grill-adversarial`/`building` 只查存在），但**格式上现在产不出来**——见 M6。另：`tasks.md H2` 说「若触发 `HANDOFF` ⇒ 按 §3.5 报三节，**别**在 R3 硬停」，这句话在**现 B 下写不出来**（B 恰恰会在「有新增且连续两轮净额 ≤ 0」的 R3 停），改完 M1 才自洽。

## 必须修改项

- **M1〔**阻塞**·`design.md §1.4:169-185`、`spec.md:135-154`（终止性 Requirement）、`spec.md:150-154`（「上界是导出量」Scenario）、`design.md §6.1:515-519`（Q14 卖点句）、`proposal.md:106-107`（目标 2）〕**：**终止性论证不成立，`2·|O_1| + 2` 是假上界。**
  实测反例（`/tmp/term/ledger.py` + `/tmp/term/t2.py`，五条形状规则**零违规**）：`R1` 报 `{R1-1}`；偶数轮「不修 + 新报 1 条」（`净额 = −1`）、奇数轮「修掉上一条 + 不新报」（`净额 = +1`）⇒ `|O|` 在 `1,2,1,2,…` 摆动、净额 `[-1,+1,…]`、**10000 轮内 A/B 均不触发**（声称上界 = 4）。
  根因：`§1.4` 第 1 步把「只有正净额轮让 `|O|` 下降」误推成「正净额轮总数 ≤ `|O_1|`」——**负净额轮会把 `|O|` 抬回去**，所以计数无界。§7 的自曝 1 问的正是这一点，答案是**否**。
  收法（作者/用户择一并在 spec 写清为什么）：
  (a) **把判据 B 改成「最近两轮（或 W 轮）**累计**净额 ≤ 0」**——同一反例序列在 B′ 下**第 3 轮停**，上界 `W·(|O_1|+1)+1`（我实测）；这是**唯一**既保住「不看轮数」又恢复良基度量的收法；
  (b) 保留现 B，把目标 2 降级为「**条件**终止保证（账本如实且不交替）」，并**同步**改弱 `§6.1` 的卖点句与 `spec.md` 的上界条款（**不许**把 `2·|O_1|+2` 留给接入方）。
  **无论选哪个**，`proposal.md` 的「验收」里那条「有净进度即继续」必须补上**反向**用例：**「交替呼吸」序列不得被判为收敛，也不得无限跑**。
- **M2〔高·`design.md §1.2 ①:31-52`、`design.md:41-49`（重算块）、`spec.md:28-36`（Scenario「同构形态 ⇒ 不停」）、`proposal.md:60-73`（实测 ①）〕**：**样本 ① 的证据面与推论都要订正。**
  实测：① 该文件**不在被审 revision 里**——它属于**兄弟 worktree** `/home/happy/wl-wt/confirm-gate-fail-closed`，且 `git status --porcelain` 显示 `openspec/changes/confirm-gate-fail-closed/` 是 **`??`（未提交）** ⇒ 任何在 `ef8b3ab` 上审计的第三方**读不到**它，而它**随时可变**。② 四个行号引用（`:52`/`:370`/`:578`/`:782`）**逐字为真** ✓，**但该文件有 `## R4 复审`（`:841`）**，其开头写「（**第 4 轮**；本仓**已废除「3 轮封顶」**⇒ 修到收敛为止）」。
  ⇒ 所以「**旧规则在 R3 强制停下交人**」是**反事实**，不是 `§1.2` 标题所称的「**实录**」（实录恰恰是：R3 标了「封顶」之后**照旧跑了 R4**）。收法：把该结论改写成它真正支持的命题——「**旧 cap 在实践中没有刹住这一环（R3 → R4）**，所以 cap 不是「收敛」的同义词」，并**把在审用文献指为「兄弟 worktree + 未提交」并附 `sha256sum`**（该文件自己已在用指纹纪律，`design.md` 却漏了）。
- **M3〔中·`design.md D2:232-243`，尤其理由 #2 `:239-240`〕**：**「B 已经覆盖了『停不下来』的全部形态」是无条件表述，与 `§1.4` 的诚实边界（`:182-185`）自相矛盾。** 由 M1 的反例，B **不**覆盖「交替呼吸」。收法：给理由 #2 补上前提「**在账本如实、且不出现正负交替的前提下**」，或按 M1(a) 改 B。
- **M4〔中·`design.md §1.5:202-216`、`§5.1 T2:452-459`、`tasks.md E1:60-62`、`E3:65-72`〕**：**「必须加反断言」这条要求本身不够——反断言写成子串黑名单会被改写绕过，扫描面是 7 个硬编码文件会漏新落点。**
  实测：`"3 轮封顶" not in text` / `"轮数封顶" not in text` / `"有界轮数" not in text` 这一类，**同义改写即逃逸**（例：把 `templates/review-loop.md:101` 改成「本闭环不设**轮数**上的**封顶**」——两个词都在、连写串不在 ⇒ 反断言全绿）。更强的形态（我已核过不误伤）：
  (a) **逐行断言「同一行不同时含 `轮` 与 `封顶`」**——实测 `docs/design.md:85`（「封顶 ~5 条常量」）与 `docs/gate.md:280`（「4 条常量封顶」）**都不含 `轮`** ⇒ 这条断言**不会误伤**这两处正当用法，却把任何「轮数/封顶」的同义改写都判红；
  (b) **扫描面改成「全仓 `find` + 显式允许名单」而**不是**硬编码 7 个文件**——允许名单只放四处历史面（`docs/reviews/*`、`docs/tasks.md`、`openspec/changes/<其它 change>/**`、`tests/test_grill_adversarial_gate.py:180`），**新文件默认判红（fail-closed）**；否则「新增一份复述旧口径的文档」永远抓不到。
  (c) **保留 `E4` 的变异验证**（把 `templates/review-loop.md` 改回旧措辞 ⇒ 必须 1 failed）——这一步是**必须做的**，我认可作者把它写成硬要求；建议再加一条变异：**删掉 floor 那句** ⇒ 也必须 1 failed。
- **M5〔中·`tasks.md G1-G5:96-103`、`design.md §5.2:470-479`〕**：**N1–N4 目前不可执行，不是「先红用例」。** 本 change 零 `src/` 改动、`check` 不解析账本（D5），文档措辞之外**没有任何东西**能承载 A/B/floor/五条规则的语义 ⇒ 这五条要么**补一个 test-local 参考实现**（在 `tests/` 内实现「读两份账本 → 判 `should_stop`」并跑 N1–N4 + 我这条「交替呼吸」反例），要么**明确降级**为「prose 检查」并承认它们**钉不住任何东西**。⚠️ 这正好是 M1 溜到设计评审才暴露的原因：**没有模型就没有反例搜索**。
- **M6〔中·`spec.md:53-89`（「每轮审阅报告携带问题账本」Requirement）、`spec.md:115-120`（`HANDOFF` 三节）、`design.md §1.3.1:69-91`、`design.md §3.5:388-398`〕**：**「每轮审阅报告」的**边界**与**锚点**都没定义，本 change 合入后会立刻自造不合规。**
  ① **哪份报告算「每轮审阅报告」**——`grill-design.md`（决策记录，无「轮」的概念）算不算？按字面算，则它没有账本 ⇒ 不合规；不算，则规格必须写明。
  ② **多轮同文件时账本怎么分节**——本仓既有报告**一律多轮同文件**（`building-review-gate/design.md:53-62` 实测：`dogfood-bootstrap` 顶层 `## Verdict` 是**第 1 轮**的，后接 `## 第 2 轮审阅`/`## 第 3 轮审阅`；`confirm-gate-fail-closed` 是 `## R2 复审`/`## R3 复审（封顶）`/`## R4 复审`）。若每轮各写一个 `## 问题账本`，同一文件里就有多个逐字相同标题，而 `evidence._sections`（`src/witnessloop/evidence.py:52-64`）会**合并**同名小节 ⇒ 第三方**无法**「只读相邻两轮」。
  ⇒ 规格必须二选一并**逐字写死**：(a) 每轮**一个**账本小节，标题含轮次（如 `### 第 N 轮 · 问题账本`），**相邻两轮**的定义随之写死；或 (b) 每轮**一份**报告文件（`reviews/<stage>-review-rN.md`）——但这会撞 `.gitignore`/孤儿规则与既有多轮惯例，代价更大。**推荐 (a)**，并同步修订 `design.md §1.3.1` 里「逐字标题 `## 问题账本`」这句。
- **M7〔低·`proposal.md:135-150`（镜像表）、`design.md §6.2:523-528`、`tasks.md H6:118-122`〕**：**接入方镜像清单**不全**，且其中一处**改不到**。**
  实测（`find` 全量扫描，**不用 `grep -r`**——它会跳过 `.claude/`，我第一遍就漏了）：现行面共 **12 处**，清单列了 9 处，漏 **`.claude/commands/review-loop.md:78`（`### 5. 修复并再审（≤3 轮封顶）`）、`:87`、`:153`**——这**正是** witnessloop 侧 `plugin/commands/review-loop.md` 的镜像物（本 change 已把它列为落点，见 `design.md:362`），漏掉它就是 `R5` 警告的「两边各编一套」。
  ⚠️ **两跳后果**：该文件被 asterwynd 的 `.gitignore:9`（`.claude/`）忽略 ⇒ **镜像 change 的 PR 改不到它**，必须走「本地/带外更新 + 在镜像 change 里写明」；否则改完 CI 绿、而 agent 实际读到的仍是旧规则。
  另：`docs/openspec-change-backlog.md:167`（「已合入归档 2026-09-15…building 审阅闭环 3 轮封顶内收敛」）是**历史记录**，应进**排除**清单（与 `docs/reviews/*` 同款），清单里要**点名**它，否则镜像那侧的「旧口径不再出现」扫描会要么误红、要么被写宽。
- **M8〔低·`design.md §1.2 ②:53-65`、`proposal.md:75-88`（实测 ②）、`design.md §8 Q2 第二半:584-588`〕**：**样本名要换，且换成 `events-readpoint-fix` 比 `dogfood-bootstrap` 更贴近 issue 的原话。**
  实测：issue 原话是「**跑到第 3 轮才收敛**」。① 作者换的 `dogfood-bootstrap`：`reviews/building-review.md` 顶层 `## Verdict` = `CHANGES_REQUESTED`（`:15`）→ `## 第 2 轮审阅`（`:124`）→ `## 第 3 轮审阅`（`:179`），据 `building-review-gate/design.md:57` 记 R2 裁定 `PASS` ⇒ **它在 R2 就收敛了**，作者自己也承认这条「是『新规则不更差』的护栏，不是新收益」⇒ 它**证不出** issue 的论点。② 真正贴近的是 **`events-readpoint-fix/reviews/grill-adversarial.md:489`**——标题**逐字**含「**第 3 轮（R3 · 轮数封顶 · 最后一轮）**」、R3 verdict = `PASS`（`:510`），且它与 issue 的样本 ① 同为**设计对抗环**（同一种产物）。
  ⇒ 建议：样本换成 `events-readpoint-fix`（并保留 `dogfood-bootstrap` 作「不更差」的第二旁证）；**同时如实标注**：仓内**没有**「R3 仍 `CHANGES_REQUESTED`、再跑一轮就收敛」的实录 ⇒「旧规则在未收敛时强制停」在仓内是**风险**（cap 与收敛不等价）而**非已观测缺陷**；而 `guard-crash-exit/reviews/grill-adversarial.md`（R1→**R5**，`:485`/`:593`）是「**旧 cap 在实践中已被突破**」的旁证——这条对「去掉固定轮数」是**强**支持，建议一并收进去。

> 说明：本文件按任务要求落在 `reviews/grill-design.md`。⚠️ 它与本仓其余 change 的 `reviews/grill-review.md` **是同一件产物**（`templates/grill.md:91` 明写「`reviews/grill-review.md`（即 `grill-design.md`）」）。无论用哪个名字，**必须由 `stage=grill` 的 manifest 以 `report_path` 绑定**，否则 `check` 的孤儿规则会在本 change 自己身上判红。
> ⚠️ **停轮前的预期状态**：本文件含逐字标题的 `## Open Questions`（Q1–Q3）而尚无 `## User Confirmation` ⇒ `evidence.grill_evidence_findings` 会报「缺少 `## User Confirmation` 小节」+ 3 条「未经用户确认」。这是**停轮前应有的**状态（与 `confirm-gate-fail-closed` 的 R4 §10 记的同款），停轮答复补齐后消失。**不要**为了让 checker 变绿而给本文件自造红/自造确认。
