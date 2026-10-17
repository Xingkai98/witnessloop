# Grill: convergence-based-stop 设计追问

## Reviewer

- run id: `grill-reviewer-convergence-2026-10-17`
- 时间: 2026-10-17（UTC）
- 被审 revision: `20f1089`（工作树；基线 `origin/main` `46e45b4`）
- 审阅方式: **只读**。逐条 `sed -n` 核对落点行号；全仓 `grep -n` 扫旧口径；读
  `src/witnessloop/{evidence,contract,checkcmd}.py` 核实 `check` 的实际判据；读
  `gh issue view 24` 仅作背景。未改 change 文档（本文除外）、模板、适配器、测试或生产代码；未 commit。
- 零记忆声明: 不引用作者会话；以下结论全部可由仓库文本与命令输出复核。本文替换
  2026-10-15 的旧 `reviews/grill-design.md`（旧模型产物，见文末「旧记录作废」）。

## Confirmed Decisions

- **决策：轮 = 非空 medium+ 批次的完整闭环；空批 = `PASS` 且不占轮；同批验证不通过继续修、不另计轮。**
  理由：`design.md:55,66,70-75` 与 `spec.md:19-32,34-38` 把「开批 → 全修 → 逐条验证 → 收口」写死，
  且明确「验证未通过仍是第 n 轮」。这与用户 2026-10-17 拍板的「一轮 = 一个有界闭环」一致。
  来源: grill-reviewer-convergence-2026-10-17
- **决策：轮数只数「已结束的非空 medium+ 批次」；第 20 轮收口后做一次收口确认，空批 ⇒ `PASS`，非空 ⇒ 超上限 `BLOCKED`；不产生第 21 轮修复。**
  理由：`design.md:82-89` 与 `spec.md:98-108,110-124` 逐条写明；`spec.md:106` 明确
  「收口确认 SHALL NOT 产生第 21 轮修复」。它把用户拍板的「20 上限」实现为安全上限，而不是
  固定轮数到点收工。
  来源: grill-reviewer-convergence-2026-10-17
- **决策：验证期禁提新问题；验证期发现的 medium+ 只进 deferred，low/nit 只进登记表；当前批次冻结。**
  理由：`design.md:70-78,165-169` 与 `spec.md:50-64,66-75` 把「唯一允许变化」限定为
  「`B_n` 验证状态、deferred 清单、low/nit 登记表」，并规定新 medium+ 不得扩大 `B_n`。
  这与用户拍板的「验证期间新发现只记入下一批」一致。
  来源: grill-reviewer-convergence-2026-10-17
- **决策：medium+ 必须全修并验证通过；low/nit 可登记不修但必须逐条写理由；severity 由审阅者定，开发者不得自行降级。**
  理由：`design.md:91-102,180-183` 与 `spec.md:77-96` 写死「medium+ 不得以登记不修放行」；
  `spec.md:85-86` 把「缺理由」定义为报告不完备（流程缺陷，非机械门禁）。与用户拍板一致。
  来源: grill-reviewer-convergence-2026-10-17
- **决策：出口只有 `PASS` / `BLOCKED` + 成因 / 超上限 `BLOCKED` + 建议推倒重开；`CHANGES_REQUESTED` 不是出口。**
  理由：`design.md:104-116` 与 `spec.md:126-143` 给出三种终结态，并明确 `CHANGES_REQUESTED`
  只是轮内状态（`spec.md:136-143`）。超上限出口必须写「建议推倒重开（revise the design）」
  （`spec.md:104-108`），不是「到轮数就停」。
  来源: grill-reviewer-convergence-2026-10-17
- **决策：设计对抗环与实现审阅环共用同一套批次模型；grill 的 frontier 追问轮显式豁免，不占 20。**
  理由：`design.md:185-191` 与 `spec.md:170-186` 写明两个环共用「批次 / 验证 / deferred / 20 / 三出口」，
  且 frontier 内部轮产出的是决策记录 `grill-design.md`，不是 verdict 报告。
  来源: grill-reviewer-convergence-2026-10-17
- **决策：机械门禁口径不变——`check` 不解析报告正文；20 上限、批次冻结、deferred 是流程规定，不是机械判据。**
  理由：设计 D6（`design.md:193-200,254-261`）与 `spec.md:188-205` 明确这条诚实边界。
  代码侧可复核：`src/witnessloop/evidence.py:341-348` 的 `verify_body` 只对 `grill` 为真；
  `:373-380` 对 `building` / `grill-adversarial` 只判存在；`src/witnessloop/checkcmd.py:188-204`
  只要求 stage manifest 存在。⇒ 没有把「机械门禁会执行 20 上限」写成承诺。
  来源: grill-reviewer-convergence-2026-10-17

## Code-Resolved Questions

- **落点行号是否与当前工作树一致？** → 是，逐条命中。证据：`templates/review-loop.md:11,90,101,153`；
  `templates/grill.md:21,140,215`；`plugin/commands/review-loop.md:2,29`；`plugin/commands/grill.md:25`；
  `plugin/README.md:37`；`README.md:306`；`docs/design.md:25`；`docs/gate.md:716`；
  `tests/test_templates.py:257-258`；`tests/test_plugin.py:174-176`。`proposal.md:96` 写的
  `templates/grill.md:130-141` 是范围写法，实质旧句在 `:140`，范围覆盖到，不算漂移。
- **旧口径在规范面是否还有漏网？** → 在 proposal 自己界定的规范面（`templates/`、`plugin/`、
  `README.md`、`docs/design.md`、`docs/gate.md`）内，没有额外命中；上述 15 处就是全部。
  规范面之外仍有旧口径，但都属历史/夹具：`docs/tasks.md:43`、`docs/reviews/*`（多处）、
  `tests/test_grill_adversarial_gate.py:180`。**新测试的扫描面与排除名单没有写进 design/tasks**，
  见风险 R7。
- **`tests/test_templates.py:257-258` 与 `tests/test_plugin.py:174-176` 两条旧断言是否都列到了？**
  → 都列到了，且行号精确。证据：`tests/test_templates.py:257` 是注释「有界轮数封顶」、
  `:258` 是 `assert "轮" in text and "封顶" in text`；`tests/test_plugin.py:174` 是
  `def test_review_loop_adapter_states_the_bounded_rounds()`、`:176` 是
  `assert "轮" in text and ("封顶" in text or "上限" in text)`。
  ⚠️ 另有一处**不能当成断言改**的旧口径：`tests/test_grill_adversarial_gate.py:180` 的
  `report_body="…三轮封顶，交人判断。…"` 是「`check` 不解析 verdict 文本」的输入夹具
  （用例在 `:167-184`）。新的反子串测试若扫 `tests/` 全目录，会把它误判为旧口径。
- **`templates/review-loop.md:75-81` 的三态 verdict 表与 `plugin/commands/review-loop.md:63` 是否在落点表里？**
  → 不在。proposal 的落点表只列 `templates/review-loop.md:11,90-102,153` 与适配器 `:2,29`；
  但新模型把 `CHANGES_REQUESTED` 从「出口」降为「轮内状态」，三态表（`:75-81`）与适配器的
  「结论是三态」（`:63`）必须同步改写，否则读者仍会按旧语义把 `CHANGES_REQUESTED` 当停轮理由。
  design §4.1 的硬约束提到了这一点，但落点表不完整。
- **`check` 是否真的不解析 verdict / 批次 / severity / 轮数？** → 是。`grill` 的正文判据只在
  `src/witnessloop/evidence.py:259-330`，检查 `Confirmed Decisions` ≥3 且每条有 `来源:`、
  `Open Questions` 小节存在、每个 Qn 有 `User Confirmation`；**不读 verdict、批次、severity、轮数**。
  `stage_manifest_findings_in_change` 对 `building` / `grill-adversarial` 走 `verify_body=False`
  （`:341-348`），只解析 `report_path` 并确认文件存在（`:373-380`）。⇒ design D6 诚实。
- **`grill-design.md` 要过 `grill` 正文判据需要什么？** → `Confirmed Decisions` 至少 3 条顶层 bullet、
  每条含 `来源:`；`Open Questions` 标题存在；`User Confirmation` 小节存在；若 `Open Questions`
  有 `Qn`，每个都要在 `User Confirmation` 里有非占位确认。证据：`src/witnessloop/evidence.py:24-29,259-330`。
  本报告满足：7 条 Confirmed Decisions、Open Questions 为「（无）」、User Confirmation 有四个已拍板事项。
- **本 change 落实现后，哪些 stage 会被机械要求？** → `templates/**` 与 `plugin/**` 在
  `.witnessloop/policy.json` 的 `require_change_for` 里；C3–C10 改到它们后 `code_hits` 为真，
  `src/witnessloop/checkcmd.py:167-204` 会同时要求 `grill-adversarial` 与 `building` 两份 manifest。
  `grill` 那份由 `grill_evidence_findings_in_change` 另行要求。
- **孤儿报告的判据是什么？** → `reviews/**/*.md` 里的**每个**报告都必须被某份 manifest 的
  `report_path` 引用，否则 `check` 报「孤儿报告」。证据：`src/witnessloop/contract.py:636-666`；
  `docs/gate.md:259-261`。这条判据**只做文件名交叉引用，不解析正文**。
- **旧 review 与孤儿规则是否冲突？** → **冲突，且当前工作树即可复现。** 当前
  `reviews/` 下有两份旧模型报告（`grill-design.md` 138 行、`grill-adversarial.md` 939 行），
  没有任何 `*.manifest.json`。design D8（`design.md:207-211`）说旧记录「不绑定 manifest」，
  但孤儿规则要求 `reviews/` 下每个 `.md` 都被绑定；两者不能同时成立。若为了消孤儿而把旧
  `grill-adversarial.md` 绑到 `stage=grill-adversarial`，它又变成旧模型假证据。见风险 R4。
- **`tasks.md` 的 A5 是否真的完成了？** → **没有。** `tasks.md:19-20` 把 A5 标成 `[x]`
  「旧版 `reviews/grill-design.md` / `reviews/grill-adversarial.md` 标作废并**从工作树移除**」，
  但当前工作树里两份旧文件都还在（`wc -l` 分别为 138 / 939）。本报告替换了旧
  `grill-design.md`；旧 `grill-adversarial.md` 仍需 B2 用新模型报告替换或移出 `reviews/`。
- **第 20 轮自身无法收口时，是否落到「超上限 `BLOCKED` + 建议重开」？** → **没有写清。**
  design `:67,83-89` 与 spec `:100-108` 的超上限出口都以「第 20 轮**收口后**」为前提；
  若第 20 轮的批次在验证中始终有「未修好」，第 20 轮就没结束，收口确认不会发生。此时只能走
  通用 `BLOCKED`（`design.md:109,115`；`spec.md:62-64,126-134`），而通用 `BLOCKED` 的报告要求
  是「成因 + 当前批次/验证状态 + 交人决策项」，**不要求**「建议推倒重开」。这与用户原话
  「到第 20 轮仍有 medium+ 未收口 ⇒ `BLOCKED` + 建议重开」有语义缺口。见风险 R1。
- **「同一批反复无法收口」是强制出口还是可选出口？** → **design 与 spec 的模态不一致。**
  `design.md:115` 写「**可以**按 `BLOCKED` 结束并写成因」；`spec.md:62-64` 写「若审阅者判定
  整体不可继续（…同一批反复无法收口），**SHALL** 以 `BLOCKED` + 成因终结」。若按 design 的
  「可以」，审阅者可以一直继续修；若按 spec 的「SHALL」，触发条件又完全依赖审阅者对「反复」的
  主观判断。两者都没有给出可复核的触发点。见风险 R2。
- **验证期发现新安全漏洞，走 deferred 还是 `BLOCKED`？** → **二义。** 主规则（`spec.md:50-60`）
  说验证期发现的任何新 medium+ 只进 deferred；例外（`:62-64`）说「安全漏洞」若被判为
  「整体不可继续」则 `SHALL` 以 `BLOCKED` 终结。设计没有定义「整体不可继续」的边界，也没有说
  同一个安全漏洞为什么不只是 deferred。`BLOCKED` 又是终结态、不自行修复（`design.md:112`；
  `spec.md:133`）⇒ 两种处理的后果完全不同（继续本轮修 vs 停下交人）。见风险 R3。
- **deferred 是否一定进入下一轮批次？** → **只有 Scenario，没有开批的硬规则。**
  `spec.md:43,70` 的 Scenario 说 deferred 项进入下一轮批次，`:155` 规定 id 沿用；但
  Requirement 正文没有写「下一次开批 SHALL 读取上一轮 deferred 表并把所有 medium+ 纳入」。
  且 `spec.md:165-168` 自己承认 deferred 丢掉「只靠人读」可发现，`check` 不设防。
  见风险 R9。
- **审阅者能否在验证期把批次项降级为 low/nit？** → **没有对称规则。** `spec.md:83-84` 只禁止
  **开发者**自行降级；`design.md:98-99` 说复核「不得为了放行而改级」，但这是意图，不是可复核判据。
  批次冻结（`spec.md:24`）写的是「不得增加、删除或替换成员」，没有明确写「severity 也冻结」。
  审阅者在验证期把一条 medium 改判为 nit，就能让本轮不带修复地收口——效果等同于用户禁止的
  「降级跳过修复」。见风险 R8。
- **spec 是否把「每条修复配回归测试」写成 SHALL？** → **没有。** `design.md:69` 写「每项给出
  具体处置 + 一条能变红的回归测试」；`spec.md:25` 只写「开发者 SHALL 修完 `B_n` 的每一项」，
  报告表（`:150`）有「回归测试」列但没有「必须有」的 SHALL。既有模板
  `templates/review-loop.md:94-95` 是明确要求的。新 spec 作为规范 delta 不应静默弱化这条。
- **grill 写码硬条件 #2 改成「`PASS`（或 `BLOCKED` + 成因）」是否安全？** → **不安全。**
  `proposal.md:97` 与 `design.md:229` 计划把 `templates/grill.md:215` 的
  「`PASS`（或轮数封顶并交人）」改成「`PASS`（或 `BLOCKED` + 成因，含超上限建议重开）」。
  但硬约束的标题是「缺证据不得进入实现」（`templates/grill.md:213-220`）；`BLOCKED` 不是
  验证通过，也不是用户放行。按新措辞，设计对抗环 `BLOCKED` 后作者就可以开始写码，绕过了
  「停轮交人」的原意。见风险 R5。
- **两个环真的同构吗？** → **声明同构，但 BLOCKED 成因与修复面没有映射。** `spec.md:170-173`
  说共用同一模型；但通用 `BLOCKED` 成因里的「测试大面积失败」只适用于实现环
  （`design.md:109`），设计对抗环的 `BLOCKED` 成因没有单独定义。design §4.2（`:226-230`）
  只说「时序图与第 5 步改成批次模型」与「明确 frontier 豁免」，没有写对抗环由谁修
  （作者改 `design.md` / `grill-design.md`）、哪些文件允许改、报告要不要同样带六节。
  见风险 R11。
- **frontier 豁免的边界是否可被利用？** → **边界未定义。** `design.md:189-191` 与
  `spec.md:174-176` 豁免「为求设计树完备而做的内部轮」，但没有说 frontier 轮从何时开始、
  何时结束，也没有说「对抗环某个批次项的设计修复工作」算不算 frontier。若算，作者可以把
  对抗环的修复工作量标成 frontier，绕过 20 上限。见风险 R6。
- **报告形态是否记录了「收口确认 / 空批」？** → **没有独立小节。** `design.md:126-149` 与
  `spec.md:145-153` 的模板只有「批次 / 验证 / deferred / low-nits / 出口」。`PASS` 来自一次
  空批（`design.md:108`；`spec.md:132`），但模板没有要求写「收口确认：本次开批 0 条 medium+」。
  空的批次表与「没做这次审阅」在文本上不可区分。见风险 R12。
- **20 轮计数是否写明跨 run / 跨报告累计？** → **没有。** design `:82-89` 与 spec `:100-108`
  说「最多 20 个已结束的轮」，但没有说这个计数是**按 change 累计**、必须在后续报告中保留，
  也没有说换一个审阅者 run / 重写报告是否会重置。id 规则（`spec.md:155`）只保留首次出现轮次，
  不保留全量账本。`check` 不解析正文，所以重置在机械上不可见。见风险 R10。

## Open Questions

（无）

用户已于 2026-10-17 拍板模型、20 上限、medium+/low/nit 口径与三出口；本报告列出的
未决点都是**设计文本的精确化**（落点、模态、报告形态、孤儿规则冲突），可由审阅者/实现者
按用户已定参数自行定案，不需要用户再拍板。若实现或评审中要改变 20 这个数、severity 口径
或出口集合，按停轮门停下报告，不自行编答案。

## 风险

- **R1｜第 20 轮自身无法收口时，没有落到「超上限 `BLOCKED` + 建议重开」。**
  证据：`design.md:67,83-89,109,115`；`spec.md:100-108,62-64,126-134`。
  场景：第 20 轮的批次有一项，开发者修了多次仍「未修好」。本轮不结束，收口确认不发生；
  审阅者只能走通用 `BLOCKED`，报告写「交人决策项（照合 / 缩范围 / 放弃）」，而用户要的是
  「建议推倒重开（revise the design）」。**收法**：补一条——第 20 轮的批次只要仍有「未修好」，
  出口就是**超上限 `BLOCKED`**，报告必须带「建议推倒重开」与第 20 轮账本，不得开启第 21 轮。
- **R2｜验证重试无上限，20 轮的上界不是工作量的上界。**
  证据：`design.md:70-72,115-116,259-260`；`spec.md:50-59`。
  场景：第 1 轮只有一条 medium+；开发者每次提交的修复都被审阅者判「未修好」，重复 1000 次。
  这一轮永远不结束，也永远不产生第 2 轮 ⇒ 20 上限永远不触发。唯一的闸门是审阅者主观的
  「同一批反复无法收口」，而 design 说「可以」、spec 说「SHALL」，没有一致的可复核触发点。
  **收法**（不新增用户未拍板的数字参数）：把「同一批反复无法收口」定义为可复核的操作规则——
  同一项在同一轮内被验证为「未修好」且开发者无法给出新的、可验证的修复方案时，
  审阅者 SHALL 以 `BLOCKED` 终结，并在报告记录验证次数与未通过项；同时把 design 的「可以」
  与 spec 的「SHALL」统一。
- **R3｜验证期发现的安全漏洞，deferred 与 `BLOCKED` 的边界未定义。**
  证据：`spec.md:50-64`；`design.md:109,165-169`。
  场景：验证批次项 A 时发现一个 high 级注入漏洞。按主规则进 deferred，本轮继续验证 A；
  按例外可以是 `BLOCKED`，停下交人、不自行修复。两种都合规，但后果完全不同。
  **收法**：把例外收紧为「该新问题使当前轮的验证失去意义，或继续实现/验证本身不安全」；
  其余安全漏洞仍进 deferred，并在 deferred 行写明为什么可以延后一轮。报告必须写明选择理由。
- **R4｜旧 review 与孤儿规则冲突；A5 的 `[x]` 与工作树不符。**
  证据：`design.md:207-211,290-291`；`tasks.md:19-20`；`src/witnessloop/contract.py:636-666`；
  `docs/gate.md:259-261`。当前工作树：`reviews/grill-adversarial.md` 939 行（旧模型）、
  `reviews/grill-design.md` 138 行（旧模型，本文已替换）、0 份 manifest。A5 标 `[x]`，
  但旧对抗报告还在。C3–C10 落地后 `code_hits` 为真，`check` 会要求
  `stage=grill-adversarial` 的 manifest；不绑旧报告 ⇒ 孤儿；绑它 ⇒ 旧模型假证据。
  **收法**：B2 必须先用新模型报告覆盖 `reviews/grill-adversarial.md`，再对该新报告
  `manifest build`；若 B2 尚未完成，就把旧文件移出 `reviews/`（git 历史保留），且**不要**
  为它建 manifest。旧 `grill-design.md` 已由本文替换，同样只在 git 历史保留。
- **R5｜grill 写码硬条件 #2 把 `BLOCKED` 写成可写码条件。**
  证据：`proposal.md:97`；`design.md:229`；`templates/grill.md:213-220`。
  场景：对抗环以 `BLOCKED` 结束（设计还有未解决的矛盾）；新措辞把它列为硬条件 #2 的满足项，
  作者据此开始写码。旧措辞「轮数封顶并交人」的语义是「已交给用户判断」，不是「自动放行」。
  **收法**：硬条件 #2 改成「`PASS`，或 `BLOCKED` + 成因 + **用户已明确裁决继续**」；
  `BLOCKED` 本身不能作为写码许可。
- **R6｜frontier 豁免可被用来吸收对抗环的修复工作量。**
  证据：`design.md:189-191`；`spec.md:174-186`。
  场景：对抗环批次项说「设计有一个未定义的依赖」；作者做了 10 轮设计树追问，并称之为
  frontier 轮，于是这 10 轮不占 20。**收法**：把豁免限定在**进入对抗环之前**的
  frontier 求完备阶段；由对抗环批次项驱动的设计探索属于该轮修复，不能改标为 frontier。
- **R7｜新的反子串文档守卫没有定义扫描面与排除名单。**
  证据：`tasks.md:34-39`；`design.md:239-245`。当前树上会撞反断言的旧口径在
  `tests/test_grill_adversarial_gate.py:180`（夹具「三轮封顶」）、`docs/tasks.md:43`
  （「有界轮数」）、`docs/reviews/*`（历史记录）。扫全仓 ⇒ 假红；只扫 7 个硬编码文件 ⇒
  新文件重新引入旧口径也不会被抓。**收法**：在 `tests/test_convergence_stop.py` 里显式列出
  规范面文件与历史/夹具排除名单（至少包含上述三处），并加一条变异验证：
  把 `templates/review-loop.md` 改回旧措辞必须 1 failed。
- **R8｜medium+ 在验证期被降级为 low/nit 没有对称规则。**
  证据：`design.md:98-99`；`spec.md:24,83-84`。
  场景：验证时审阅者认为批次里一条 medium 其实是 nit，把它从阻塞集移走；本轮就能在不修它
  的情况下收口。这与用户在参数 3 中禁止的「medium+ 靠降级跳过修复」效果相同。
  **收法**：batch 冻结时 severity 一并冻结；验证期若认为定级错误，只能记录争议并二选一：
  （a）按原 severity 要求修完；或（b）`BLOCKED` 并把争议写进成因。不得静默移出批次。
- **R9｜deferred 传递只有 Scenario，没有开批的硬规则。**
  证据：`spec.md:43,70,155,165-168`。
  场景：第 3 轮 deferred 了 `R3-2`；第 4 轮的开批审阅漏掉它；报告没有任何一行提到它；
  本轮全部验证通过后继续，最终 `PASS`。第三方只能靠人读发现账本不自洽。
  **收法**：在 Requirement 里写：第 n+1 轮开批 SHALL 先读第 n 轮的 deferred 与 low/nit 表；
  每个 deferred medium+ SHALL 以原 id 出现在下一轮批次，或出现在本轮 `BLOCKED` 的成因里。
- **R10｜20 轮计数没有写明按 change 跨 run/跨报告累计。**
  证据：`design.md:82-89`；`spec.md:100-108,155`。
  场景：跑完第 7 轮后换一个审阅者 run，写一份从第 1 轮开始的新报告，20 上限重新计数；
  `check` 不解析正文，机械上不可见。**收法**：写明账本是**按 change 累计**的，后续报告
  必须保留前序轮次（或引用同一份叠写报告）；重置计数只能来自用户的明确裁决，并记为
  `BLOCKED` / 建议重开设计。
- **R11｜两个环的 `BLOCKED` 语义与修复面不完全同构。**
  证据：`spec.md:170-173,62-64`；`design.md:109,185-191,226-230`。
  场景：设计对抗环发现「设计对某个核心需求没有答案」——这是设计级阻塞，但通用 `BLOCKED`
  成因表里的「测试大面积失败」是实现环的；设计环的 `BLOCKED` 成因、修复责任人与允许修改的
  文件都没有写。**收法**：给设计对抗环一张 `BLOCKED` 成因映射（核心需求缺失 / 设计自相矛盾 /
  依赖不可满足 / 同一批反复无法收口），并写明作者负责改 `design.md` / `grill-design.md`，
  报告同样带批次 / 验证 / deferred / low-nits / 出口五节。
- **R12｜报告形态缺少「收口确认 / 空批」的记录位。**
  证据：`design.md:126-149`；`spec.md:145-153`。
  场景：第 3 轮批次收口后，下一次开批 0 条 medium+ ⇒ `PASS`；但报告只有空的批次表，
  读者无法区分「做了这次开批且为空」与「忘了做开批」。**收法**：在报告模板加
  `### 第 <n> 轮后 · 收口确认`（审阅时间 / 范围 / 0 条 medium+ 的结论），并规定 `PASS`
  必须引用这一节。
- **R13｜low/nit 登记是否累积未定义。**
  证据：`spec.md:145-153`；`design.md:108`。
  场景：第 2 轮登记一条 low「不修 + 理由」；最终 `PASS` 报告只带最后一轮的 low/nit 表，
  第 2 轮那条从报告面消失。**收法**：要求最终 `PASS` 报告携带**累积** low/nit 登记表，
  或逐项链接到首次登记的轮次小节。

## User Confirmation

- **1｜轮模型**：用户 2026-10-17 拍板（逐字要点）：「一轮 = 一个有界闭环：审阅者开一批
  medium 及以上的问题 → 开发者全部修完 → 审阅者只做修复验证（逐条确认；验证期间发现的新问题
  不许当场提，只能记入下一批 deferred）→ 这一批全部修好 ⇒ 本轮结束；下一轮才提新一批。
  不许边改边提。」确认时间: 2026-10-17
- **2｜20 上限**：用户 2026-10-17 拍板：「轮数上限 = 20；超过 ⇒ `BLOCKED`，并明确写
  「建议推倒重开（revise the design）」，不是「到轮数就停」。」确认时间: 2026-10-17
- **3｜medium+ / low / nit**：用户 2026-10-17 拍板：「批次里的 low / nit 可以登记不修，
  但必须在报告里写理由；medium 及以上必须全修。」确认时间: 2026-10-17
- **4｜三出口**：用户 2026-10-17 拍板：「出口只有三种：`PASS` / `BLOCKED` + 写明成因 /
  超上限 `BLOCKED` + 建议重开。」确认时间: 2026-10-17
- **本 change 无新增待拍板问题。** 本报告 `## Open Questions` 为「（无）」；上述 R1–R13 是
  设计文本的精确化与实现风险，不需要用户重新选择参数。确认时间: 2026-10-17

## 旧记录作废

- 2026-10-15 的旧 `reviews/grill-design.md`（138 行）与 `reviews/grill-adversarial.md`
  （939 行）是**旧模型**（收敛判据 / 问题账本 / 无限轮 / 3 轮封顶口径）的产物，
  **不适用于** 2026-10-17 新口径。它们**不是**本 change 的证据，**不绑定** manifest，
  也不得在后续报告中当作已确认结论引用。
- 旧内容可从 git 历史 `9acdf2b`（该文件首次落盘）与 `20f1089`（新模型重写时再次落盘）查。
- 本文（`grill-reviewer-convergence-2026-10-17`）已替换工作树里的旧 `grill-design.md`；
  旧 `grill-adversarial.md` 在本审阅开始时仍在工作树。按 A5 与新模型，B2 必须用新报告
  覆盖它，或把它移出 `reviews/`（git 历史保留）；**不得**直接为旧文件建
  `stage=grill-adversarial` manifest——那会同时制造孤儿规则冲突与旧模型假证据（见风险 R4）。
