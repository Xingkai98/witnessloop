# Building review: convergence-based-stop

## Reviewer

- run id: `building-reviewer-convergence-2026-10-17`
- 时间: 2026-10-17（UTC）
- 被检 revision: `18424c1`；基线 `origin/main` `46e45b4`
- 零记忆声明: 未参与作者会话，没有作者侧记忆；只读仓库文本、git 历史与实际命令输出。
  未改实现、模板、适配器、测试或其它 change 文档；本报告是本次唯一写入的文件。未 commit。
- 审阅方式: `git diff origin/main...HEAD` 全量阅读；逐项核对 `tasks.md` 的 `[x]`；
  实读 `templates/review-loop.md`、`templates/grill.md`、`plugin/commands/*.md`、
  `plugin/README.md`、`README.md`、`docs/design.md`、`docs/gate.md`、`tests/test_convergence_stop.py`、
  `tests/test_templates.py`、`tests/test_plugin.py`；实读
  `src/witnessloop/{evidence,checkcmd,contract}.py`；跑全量测试、目标测试与 `/tmp` 变异；
  核对 `reviews/` 下报告与 manifest 绑定关系。
- 基线事实: `git diff --name-only origin/main...HEAD -- src/` 为 **0 个文件**；本次只改模板 / 适配器 /
  自述 / 测试与 change 制品，与 proposal 的非目标一致。
- 验证轮被检 revision: `6c914ff`（第 1 轮修复提交）；第二次验证与第 3 次开批的 revision:
  `1dffc29`；基线均为 `origin/main` `46e45b4`。
- **验证轮重排说明（building R1-3 schema）**: 本报告的 low/nit id 从 `L1–L7` 重排为
  `R1-5–R1-11`；验证期新增 deferred `R1-12`（medium）与 low/nit `R1-13–R1-15`。
  顶层 `## Verdict` 改为 `## 本轮判定（verdict）`，并追加 `## 闭环出口`；第 1 轮开批时的
  原子节内容保留，验证结果写在第 1 轮验证节。

## 本轮判定（verdict）

**PASS**（第 3 次开批为空；第 1 轮 R1-1–R1-4 与第 2 轮 R1-12 全部已修好）

- 第 1 轮：R1-1–R1-4 已修好。R1-2 在 `6c914ff` 首次验证时未修好（守卫无效），
  `1dffc29` 第二次验证已修好。
- 第 2 轮：deferred `R1-12` 以原 id 进入批次；`1dffc29` 已补
  `tasks.md` 的 `## F. 审阅修复（building R1）` 节，已验证。
- 第 3 轮：完整审阅当前实现，开批为空（0 条 medium+）⇒ **`PASS`**。
- 全量测试：`753 passed`（HEAD `1dffc29`）。
- deferred：0 条（R1-12 已进入第 2 轮并修好）。
- low/nit：10 条（`R1-5`–`R1-11`、`R1-13`–`R1-15`）；其中 R1-6 / R1-10 / R1-13 / R1-15
  已修，R1-5 / R1-14 部分已修，其余登记不修。

## 第 1 轮 · 批次（medium+）

| id | severity | 锚点 | 问题 |
|---|---|---|---|
| R1-1 | medium | `plugin/commands/review-loop.md:22`；`templates/review-loop.md:48-121`；`tests/test_convergence_stop.py:128-131`；`design.md:303-307` | 适配器要求按模板「步骤 1–8」执行，但模板只有 7 个执行步骤；测试还把「1–8」钉成硬断言，等于把错误编号固化 |
| R1-2 | medium | `specs/review-termination/spec.md:76-78`；`templates/review-loop.md:105-106`；`design.md:87-88` | 验证期安全例外的模态不一致：spec 说命中条件时 **SHALL** `BLOCKED`，模板与 design 说「**可** `BLOCKED`」 |
| R1-3 | medium | `reviews/grill-adversarial.md:87,102,173,179,183,198,212-214`；`specs/review-termination/spec.md:209-230`；`templates/review-loop.md:140-152,161-162` | 本 change 的首份 dogfood 报告不遵守新报告 schema：同轮复验被标成「第 2 轮 · 验证」，空批收口确认被标成「第 2 轮 · 批次 / 下一批」，同轮有两张验证表，id 使用 `I*` / `L*` / `N*` 而非规范要求的 `R<轮次>-<序号>` |
| R1-4 | medium | `design.md:355-359`；`tasks.md:64`；`tests/test_convergence_stop.py:72-149`；`plugin/commands/grill.md:23-27`；`docs/gate.md:716-718` | design §4.4 的「七要素 → 文件映射」只部分落地：5 个 allowlist 文件没有正断言；`plugin/commands/grill.md` 没有映射要求的 `deferred` / `下一批`，`docs/gate.md` 没有映射要求的「批次」措辞 |

### R1-1 适配器步骤号与模板实际步骤数不一致

- **问题**: `plugin/commands/review-loop.md:22` 写「按 `templates/review-loop.md` 的**步骤 1–8**执行」；
  实际模板只有 7 个 `### <n>.` 执行步骤：`templates/review-loop.md:48`（定位 change）、`:53`（钉基线）、
  `:66`（开批）、`:79`（全修）、`:89`（只做修复验证）、`:112`（收口与下一轮）、`:121`（出口与收尾）。
  没有第 8 步。`tests/test_convergence_stop.py:128-131` 仍断言适配器必须出现「1–8」，
  这会让测试在错误事实上保持绿色。
- **为什么是问题**: design §4.1 的落点计划把流程写成 8 步（`design.md:303-307`，第 7 步「20 上限与三出口」、
  第 8 步「收尾落 manifest」），proposal 与 tasks 也按 8 步写；实现时把「出口」和「收尾」合并成了模板
  第 7 步，却没有同步适配器、design、proposal、tasks 与测试。用户实际调用的命令入口因此引用了一个
  不存在的步骤号，审阅者按编号执行时会找不到第 8 步。
- **建议修复**: 二选一，但必须同步所有落点：
  1. 把模板第 7 步拆成「7. 出口判定」和「8. 收尾落 manifest」，与 design/proposal/tasks/适配器的 1–8 对齐；
  2. 或把适配器、design §4.1、proposal 落点表与 `tests/test_convergence_stop.py:128-131` 统一改成
     「步骤 1–7」或「按模板全文」。
  当前测试只断言「1–8」，应同时断言模板确有 8 个步骤（或改为不依赖数字的「按模板全文」守卫）。
- **复验（`6c914ff`）**: **已修好**。模板现在确有 8 个 `### <n>.` 步骤；适配器仍写「步骤 1–8」；
  测试新增 `test_review_loop_template_has_eight_execution_steps`。详见验证节与 Test Results。

### R1-2 安全例外的 SHALL / MAY 模态冲突

- **问题**: spec 的验证期例外写的是强制的：
  `specs/review-termination/spec.md:76-78`「若审阅者判定整体不可继续，**SHALL** 以 `BLOCKED` + 成因终结；
  ……『整体不可继续』**SHALL 限定为**：该新问题使当前轮的验证失去意义，或继续实现/验证本身不安全。
  其余安全漏洞 **SHALL** 进 `deferred`。」
  但模板写成可选的：`templates/review-loop.md:105-106`「该新问题使当前轮验证失去意义，或继续实现/
  验证本身不安全 ⇒ **可** `BLOCKED`」；design `design.md:87-88` 同样写「才**可** `BLOCKED`」。
- **为什么是问题**: 这是安全漏洞的例外路径。按模板/dsign，审阅者即使判定「继续验证不安全」也**可以**
  不 `BLOCKED`；按 spec，这种判定一旦成立就**必须** `BLOCKED`。执行者无法确定哪份文本优先。
  之前对抗轮已经把 R2 的「可以 vs SHALL」统一过一次，这里在新增的安全例外上又出现了同类问题。
- **建议修复**: 统一为 spec 的 `SHALL`（推荐，因为这是收紧后的安全例外）：
  `templates/review-loop.md:105-106` 与 `design.md:87-88` 改成「⇒ **SHALL** `BLOCKED`」。
  若确实想保留「可」，必须改 spec 并说明为什么不强制；这会改变安全例外的语义，不能静默做。
- **复验（`6c914ff`）**: **未修好**。`templates/review-loop.md:105-106`、`design.md:87-88,223-224`
  与 spec `:76-78` 的文本都已统一为 `SHALL`，但新增的守卫
  `tests/test_convergence_stop.py:154-159` 抓不住回归：把该例外精确改回「⇒ 可 `BLOCKED`」后，
  测试仍 `1 passed`。原因是它只断言全文出现 `SHALL 以`（模板 `:96` 的验证重试终止点也满足）
  且只禁止同一行的 ``可 `BLOCKED` ``（换行后匹配不到）。详见验证节与 Test Results。

### R1-3 首份 dogfood 报告不遵守新报告 schema

- **问题**: `reviews/grill-adversarial.md` 是本 change 按新模型产出的第一份对抗报告，但它的轮次标题
  与 id 不符合新模型：
  - `:87` 把第 1 轮批次的**同轮复验**写成「## 第 2 轮 · 验证」，虽然同一行括号里写「按新模型仍是
    第 1 轮，不是新开批」；
  - `:173`、`:179`、`:183`、`:198` 把空批的收口确认写成「第 2 轮 · 批次」「第 2 轮 · 下一批」
    「第 2 轮 · 新增 low / nit 登记」等；正文 `:176-177` 自己承认「下一次开批为空 ⇒ PASS，不消耗轮数；
    这是第 1 轮后的收口确认」；
  - `:35-53` 的第 1 轮验证表全部是「待验证 / 待定」，真正的验证结果在 `:102-123` 的另一张表里，
    同一轮出现两张验证表；
  - 批次 id 用 `I1`–`I12`（`:18-33`），low/nit 用 `L1`–`L7`（`:59-69`）与 `N1`–`N10`（`:183-196`），
    而 `specs/review-termination/spec.md:227-228` 与 `templates/review-loop.md:161-162` 规定
    `R<首次出现轮次>-<序号>`、初次 low/nit 用 `R0-<序号>`。
- **为什么是问题**: 这是本 change 的目标模型第一次 dogfood。读者按小节标题计数会得到「2 轮」，
  而模型只允许 1 个已收口轮；spec Requirement 5 要求「多轮同文件时，每轮小节标题 SHALL 带轮次，
  以便第三方只读相邻轮次即可复核」（`spec.md:229-230`）。报告还将被 D3 的
  `stage=grill-adversarial` manifest 绑定，若 schema 不规范，后续审阅者会直接继承错误的轮次账本。
- **建议修复**: 在绑定 manifest 前原地修正报告：
  - `:87` 改为「## 第 1 轮 · 验证」；
  - `:173` 改为「## 第 1 轮后 · 收口确认（空批）」；`:179` 改为「### 第 1 轮 · 下一批（deferred）」，
    `:183` 改为「### 第 1 轮 · low / nit 登记」；`#### 尝试证伪但未成立的方向` 不再带「第 2 轮」；
  - 合并两张验证表，或在 `:35-53` 明确标注「开批时快照，最终结果见同轮验证表」，并保留最终结果；
  - id 按 `R1-*`（批次）/ `R0-*`（初次 low/nit）/ 后续轮次编号重写，或在报告里显式记录
    「本报告为设计环首轮，id 采用 `I*` 是设计环的约定」——但后者与 spec 的 `SHALL` 冲突，
    需要先改 spec 才能采用。
- **复验（`6c914ff`）**: **已修好**。报告现在有 `## Reviewer`（含 run id 与重排说明）、
  `## 本轮判定（verdict）`、`## 闭环出口`；同轮复验标题为
  `## 第 1 轮 · 验证（R1-1–R1-12 的修复复验；同轮，不是新开批）`；空批收口为
  `## 第 1 轮后 · 收口确认（空批）`；表格行无旧 `I*` / `L*` / `N*` id（旧 id 只出现在
  `:9` 的重排说明里）。详见验证节。

### R1-4 design §4.4 的七要素 → 文件映射未完整落地

- **问题**: design §4.4 明确要求：
  - 「批次 / 20 / 建议重开」必须出现在 `templates/grill.md`、`plugin/README.md`、`README.md`、
    `docs/design.md`、`docs/gate.md`（`design.md:357-358`）；
  - 「批次 / deferred / 20 / 三出口」必须出现在两个 `plugin/commands/*.md`（`design.md:359`）。
  `tasks.md:64` 把「另加七要素 → 文件映射」列为 C1 的 `[x]`。实际
  `tests/test_convergence_stop.py:72-149` 只对 `templates/review-loop.md`、`templates/grill.md`、
    `plugin/commands/review-loop.md` 与 spec 做了正断言；对 `plugin/commands/grill.md`、
    `plugin/README.md`、`README.md`、`docs/design.md`、`docs/gate.md` 只有反断言（`NORMATIVE` 扫描），
    没有任何正断言。内容侧也有缺口：`plugin/commands/grill.md:23-27` 只写「开批 / 全修 / 只验证 /
    收口；20 上限；三出口；frontier 豁免」，没有 `deferred` / `下一批`；`docs/gate.md:716-718`
    只写「20 轮超限 / 建议推倒重开 / 三出口」，没有「批次」。
- **为什么是问题**: 本 change 的核心交付物就是「模板 + 文档守卫」；design 把映射写成测试策略的一部分，
  是为了防止只在一行摘要里堆关键词、而其它规范文件悄悄漂移。当前 5 个文件没有正断言，后续改坏
  `README.md` / `docs/design.md` / `docs/gate.md` / 两个适配器的批次措辞时，测试仍会全绿。
  这属于「测试断言太弱」而不是「文档内容当前错误」——内容大部分已经在，但守卫没有覆盖设计承诺的范围。
- **建议修复**: 在 `tests/test_convergence_stop.py` 增加一条参数化映射测试，按 `design.md:355-359`
  的三组文件与元素逐一断言；并把 `plugin/commands/grill.md` 的 `deferred` / `下一批`、`docs/gate.md`
  的「批次」补进对应文本（或如果认为映射写错了，先改 design/tasks，再改测试）。
  该测试应在 `/tmp` 变异下能变红（例如删掉 `README.md` 的「20 轮」）。
- **复验（`6c914ff`）**: **已修好**。`FILE_MAPPING` + 参数化测试覆盖 8 个文件；
  `plugin/commands/grill.md:25` 已含 `deferred`（下一批），`docs/gate.md:718` 已含「批次」；
  删掉 `README.md` 的「20」或删掉 grill 适配器的 `deferred` 都会让映射测试变红。详见验证节。

## 第 1 轮 · 验证（R1-1–R1-4 的修复复验）

作者修复提交：`6c914ff`。只逐条复验下列 4 项，不扩批。

| id | 结果 | 修复提交 | 回归测试 / 设计环对应物 |
|---|---|---|---|
| R1-1 | **已修好** | `6c914ff` | `test_review_loop_template_has_eight_execution_steps`（模板 1–8 步）；变异删掉数字第 8 步 ⇒ `1 failed` |
| R1-2 | **已修好（第 2 次验证）** | `1dffc29` | 守卫已绑到例外段（模板 + design）；模板/design 变异均 `1 failed`；模板/design/spec 三处均为 `SHALL` |
| R1-3 | **已修好** | `6c914ff` | 报告 schema 重排（Reviewer / 本轮判定 / 同轮验证 / 空批收口 / 闭环出口）；表格行无旧 id |
| R1-4 | **已修好** | `6c914ff` | `test_normative_files_carry_their_required_terms`（8 文件映射）；删 README「20」或 grill 适配器 `deferred` ⇒ `1 failed` |

**验证纪律**: 验证期发现的新 medium+ 只写入下一节 `deferred`，不扩 `B_1`；low/nit 只进登记表。
R1-2 首次验证（`6c914ff`）判「未修好」；第 2 次验证（`1dffc29`）已修好，因此第 1 轮在本轮
收口；下一次开批把 deferred `R1-12` 纳入第 2 轮（见下）。

### R1-1（已修好）

- 模板当前有 8 个执行步骤：`templates/review-loop.md:48`（定位 change）、`:53`（钉基线）、
  `:66`（开批）、`:79`（全修）、`:89`（只做修复验证）、`:112`（收口与下一轮）、
  `:121`（出口）、`:164`（收尾）。
- 适配器仍要求「步骤 1–8」：`plugin/commands/review-loop.md:22`。
- 守卫：`tests/test_convergence_stop.py:147-151` 同时钉住 `### 1.`–`### 8.`；
  `/tmp` 变异把数字第 8 步改掉 ⇒ `1 failed in 0.58s`。

### R1-2（首次验证未修好；第 2 次验证已修好）

- 文本已修好：`templates/review-loop.md:105-106`、`design.md:87-88,223-224`、spec
  `:76-78` 都是 `SHALL 以 BLOCKED + 成因终结`。
- 但守卫无效：`tests/test_convergence_stop.py:154-159` 只断言全文出现 `SHALL 以`（模板
  `:96` 的验证重试终止点也满足）且只禁止同一行的 ``可 `BLOCKED` ``；把例外精确改回
  `⇒ 可\n    `BLOCKED`` 后，`test_review_loop_template_security_exception_is_shall`
  仍 **`1 passed in 0.07s`**。
- **必须做**: 把守卫绑到例外句本身（例如取包含「验证失去意义」的句子/段落，断言其中含
  `SHALL` 且不含 `可`），并建议同时覆盖 `design.md`（至少模板 + design 两处）。
  这是该批次项第一次被判「未修好」；若下一次复验仍「未修好」且开发者拿不出新的可验证方案，
  才触发验证重试终止点。

#### 第 2 次验证：R1-2 已修好（`1dffc29`）

- 守卫已绑到例外段：`tests/test_convergence_stop.py:154-173` 的 `_exception_paragraph`
  取「验证失去意义」所在段落并归一空白；模板用 `**例外**`、design 用
  `**安全漏洞的例外` 起段，断言含 `SHALL 以 `BLOCKED`` 且不含 `可 `BLOCKED``。
- `/tmp` 变异：模板例外精确改回 `⇒ 可 `BLOCKED`` ⇒
  `test_security_exception_is_shall_in_template_and_design` **`1 failed in 0.05s`**；
  design 例外改回 `⇒ 可 `BLOCKED`` ⇒ 同一测试 **`1 failed in 0.20s`**。
- 三处文本均为 `SHALL 以 `BLOCKED` + 成因终结`：`templates/review-loop.md:105-106`、
  `design.md:87-88,223-224`、spec `:76-78`。
- **结果：已修好。** 第 1 轮 R1-1–R1-4 全部已修好 ⇒ 第 1 轮收口。

### R1-3（已修好）

- `reviews/grill-adversarial.md:3-9` 有 `## Reviewer`（run id + schema 重排说明）。
- `:11` 为 `## 本轮判定（verdict）`；`:93` 为
  `## 第 1 轮 · 验证（R1-1–R1-12 的修复复验；同轮，不是新开批）`；
  `:179` 为 `## 第 1 轮后 · 收口确认（空批）`；`:218` 为 `## 闭环出口`。
- 表格行无旧 `I*` / `L*` / `N*` id（`grep '^| *\(I[0-9]\|L[0-9]\|N[0-9]\)'` 无命中）；
  旧 id 只出现在 `:9` 的重排说明里。
- 同轮复验不再标「第 2 轮」；空批收口确认是 `第 1 轮后 · 收口确认（空批）`；id 为
  `R1-1–R1-12`、`R1-13–R1-19`、`C-1–C-10`，符合本轮要求。

### R1-4（已修好）

- `tests/test_convergence_stop.py:58-68` 的 `FILE_MAPPING` 覆盖 8 个文件；
  `:162-175` 是参数化正断言测试；spec 另有 `test_spec_requirements_cover_the_new_model`。
- `plugin/commands/grill.md:25` 已含 `deferred`（下一批）；`docs/gate.md:718` 已含「批次」。
- `/tmp` 变异：删 `README.md` 的「20」⇒
  `test_normative_files_carry_their_required_terms[README.md]` `1 failed, 7 passed`；
  删 grill 适配器的 `deferred` ⇒ 该文件的参数化项 `1 failed, 7 passed`。

## 第 1 轮 · 下一批（deferred）

| id | severity | 锚点 | 问题 | 来源 | 延后理由 |
|---|---|---|---|---|---|
| R1-12 | medium | `templates/review-loop.md:85-87,201`；`plugin/commands/review-loop.md:72`；`tasks.md` | 修复提交 `6c914ff` 没有按模板第 4 步在 `tasks.md` 追加「审阅修复」节；`git diff 18424c1..HEAD -- tasks.md` 为空，`grep -n '审阅修复' tasks.md` 无命中。修复内容只记在 `design.md` 的 Building R1 节（`:474-484`） | 验证期发现（R1 修复的流程合规） | 不影响 R1-2 的守卫修复；补一节不改变实现/测试，下一轮随批次修 |

## low / nit 登记

| id | severity | 锚点 | 处置 | 理由 |
|---|---|---|---|---|
| R1-5 | low | `templates/review-loop.md:157-158`；`design.md:193` | 部分已修 | 模板 `:158` 已改为覆盖「20 个轮已收口仍有 medium+，或第 20 轮自身未收口」；`design.md:193` 的报告 schema 仍写「BLOCKED（超过 20 轮，建议重开设计）」，属摘要残余 |
| R1-6 | low | `plugin/commands/grill.md:37-43` | 已修（`1dffc29`） | 适配器的 manifest 示例已改为 `--report reviews/grill-design.md`（`plugin/commands/grill.md:39`），与实际文件名一致 |
| R1-7 | low | `tests/test_convergence_stop.py:58-69` | 登记不修 | 裸「封顶」规则是行级允许词，理论上可在违规行同时写「常量」绕过；design §4.4 已明说这是行级规则而非语义解析，当前允许行均与本规则无关 |
| R1-8 | low | `tasks.md:65` | 登记不修 | C2 要求把红测原始输出写进 `reviews/building-review.md`，但该文件是 D1（本报告）的产物；作者把输出记在 `tasks.md:84-96`。属于任务编排顺序问题，不影响证据存在 |
| R1-9 | low | `templates/review-loop.md:112-119`；`specs/review-termination/spec.md:140-144` | 登记不修 | 模板没有重述「第 20 轮收口后、收口确认前：等待收口确认，不开启第 21 轮，不做修复」；step 3/6 的「下一次开批」逻辑已隐含，spec 有逐字规定 |
| R1-10 | low | `reviews/grill-adversarial.md:3-9`；`design.md:474-475` | 已修（R1-3） | 对抗报告已补 `## Reviewer` / run id 小节；design 的 Building R1 记录也写明了 run id。D3 的 manifest 仍会携带 `reviewer_run_id`，不影响证据 |
| R1-11 | low | `proposal.md:148` | 登记不修 | 「见验收的 11 个文件」是交叉引用，但 proposal 验收段没有枚举这 11 个；design §4.4 与 tasks C1 已枚举 |
| R1-13 | low | `tests/test_convergence_stop.py:58-68` | 已修（`1dffc29`） | `FILE_MAPPING` 已为两个适配器补上「出口只有三种」/「20」/「三出口」；design §4.4 同步写明「或等价『出口只有三种』」 |
| R1-14 | low | `templates/review-loop.md:72-76` | 部分已修 | 空批分支 `:74` 已改为「跳到第 7 步并继续第 8 步（收尾）」；20 轮超限分支 `:76` 仍只写「跳到第 7 步」，未点明第 8 步 |
| R1-15 | low | `design.md:431` | 已修（`1dffc29`） | R3 摘要已改为「⇒ `SHALL` `BLOCKED`」，与规范段 `:87-88,223-224` 和 spec `:76-78` 一致 |

## 第 1 轮后 · 收口确认

**第 1 轮收口。** 首次验证（`6c914ff`）时 R1-2 未修好；第 2 次验证（`1dffc29`）中
R1-2 已修好，R1-1–R1-4 全部通过。下一次开批把 deferred 的 medium `R1-12` 以原 id 纳入
第 2 轮批次（见下）；没有新增 medium+ 需要扩第 1 轮批次。

## 第 2 轮 · 批次（medium+）

| id | severity | 锚点 | 问题 |
|---|---|---|---|
| R1-12 | medium | `templates/review-loop.md:85-87,201`；`plugin/commands/review-loop.md:72`；`tasks.md:114-123` | R1 修复提交 `6c914ff` 没有按模板第 4 步在 `tasks.md` 追加「审阅修复」节；`1dffc29` 的 `## F. 审阅修复（building R1）` 是修复 |

## 第 2 轮 · 验证

| id | 结果 | 修复提交 | 回归测试 / 设计环对应物 |
|---|---|---|---|
| R1-12 | **已修好** | `1dffc29` | `tasks.md:114-123` 的 `## F. 审阅修复（building R1，2026-10-17）` 逐行列出 R1-1–R1-4、R1-12 与 low/nit 的处置 / 落点 / 提交；`grep -n '审阅修复' tasks.md` 命中 `:114` |

## 第 2 轮 · 下一批（deferred）

（无。R1-12 已修好；第 3 次开批为空。）

## 第 2 轮后 · 收口确认

**空批：0 条 medium+。** R1-12 已修好，第 2 轮收口。第 3 次开批（完整审阅当前实现）
未发现新的 medium+；只有 low/nit（见登记表）⇒ **`PASS`**。

### 尝试证伪但未成立的方向（3 个）

1. **R1-2 守卫仍只断言全文？** 未成立：守卫已绑到例外段（模板 + design）；模板/design
   两处变异均 `1 failed`。
2. **R1-12 只是名义上的 `tasks.md` 节？** 未成立：`tasks.md:114-123` 逐行列出了
   R1-1–R1-4、R1-12 与 low/nit 的处置 / 落点 / 提交，不是空壳。
3. **第 3 次开批仍有 medium+？** 未成立：完整复读当前规范面与测试，只有 R1-5 / R1-14
   的部分残余与 R1-7 / R1-8 / R1-9 / R1-11 的已知 low/nit，没有 medium+。

## 闭环出口

**`PASS`**。第 1 轮 R1-1–R1-4 全部已修好；第 2 轮 R1-12 已修好；第 3 次开批为空
（0 条 medium+），deferred 0 条。

## Tasks Verification

逐条对照 `tasks.md` 的 `[x]`；`[ ]` 的 D/E 是后续批，不报缺陷（D3/D4 未跑是 `check` 当前红的
原因，见 Test Results）。

### A. 文档重写

| 任务 | 状态 | 证据 |
|---|---|---|
| A1 | 真实存在 | `proposal.md:25-82`（新模型、20 上限、medium+/low、deferred、三出口）；`:98-120` 落点表 |
| A2 | 真实存在 | `design.md:51-296`（新模型定义、精确流程、轮数、出口、报告形态）；`:421-469` Pre-Implementation Review |
| A3 | 真实存在 | `tasks.md:9-132`（按批次组织，A–E 与验收清单） |
| A4 | 真实存在 | `specs/review-termination/spec.md:24-306`；`grep` 未发现「按审阅 pass 计轮」「无轮数上限」「轮数封顶」等旧口径 |
| A5a | 真实存在 | `reviews/grill-design.md:266-276`「旧记录作废」；当前文件 276 行，旧文件（`20f1089`）138 行；旧 grill-design 已被覆盖 |
| A5b | 真实存在 | `reviews/grill-adversarial.md:15-16,704-705` 覆盖旧报告；当前 `reviews/` 只有 2 份 `.md`，无任何 manifest，未给旧文件建 manifest |

### B. 设计阶段独立验证

| 任务 | 状态 | 证据 |
|---|---|---|
| B1 | 真实存在 | `reviews/grill-design.md:14-48`（7 条 Confirmed Decisions，每条有 `来源:`）；`:50-153` Code-Resolved；`:155-157` Open Questions「（无）」；`:251-264` User Confirmation 四个事项；实跑 `grill_evidence_findings` 返回 `[]` |
| B1b | 真实存在 | `design.md:421-441` 的 R1–R13 逐条整合；proposal/spec/tasks 同步（例如 `proposal.md:67-82`、`spec.md:133-156`） |
| B2 | 真实存在 | 报告内容存在：`reviews/grill-adversarial.md:26-41`（R1-1–R1-12 批次）、`:93-130`（同轮验证）、`:179-202`（空批收口）、`:218-220`（PASS）；R1-3 修复后 schema 重排完成，见验证节 |
| B3 | 真实存在 | `reviews/grill-design.md:251-264`（用户已拍板的四项）；Open Questions 为「（无）」 |
| B4 | 真实存在 | `design.md:444-466` 列出 I1–I12 的落点；`tasks.md:41-43` B4 写明整合面 |
| B5 | 真实存在 | `reviews/grill-adversarial.md:108-130` R1-1–R1-12 全部「已修好」；`:179-202` deferred 为 0；`:218-220` PASS |

### C. TDD 实现

| 任务 | 状态 | 证据 |
|---|---|---|
| C1 | 真实存在 | `tests/test_convergence_stop.py:24-37` 显式 allowlist；`:39-51` 词表；`:58-68` `FILE_MAPPING`；`:70-85` 裸「封顶」行级规则；`:89-160` 七要素与 R1-1/R1-2 守卫；`:162-175` 参数化文件映射。R1-1/R1-2/R1-4/R1-13 已补；R1-2 第二次验证已修好；R1-13 的适配器词条已在 `1dffc29` 补齐 |
| C2 | 真实存在（记录位置有偏差） | `tasks.md:84-96` 记录红测输出（`18 failed, 61 passed`）；字面要求的 `reviews/building-review.md` 当时尚不存在（由 D1 产出），见 R1-8。独立变异复现见 Test Results |
| C2b | 真实存在 | `tasks.md:89-92` 记录变异验证；本次在 `/tmp` 副本独立复现：旧措辞使 `test_normative_surfaces_drop_the_old_round_cap` **1 failed, 10 passed** |
| C3 | 真实存在 | `templates/review-loop.md:8-16`（目的）、`:46-177`（8 步流程）、`:203-224`（硬约束） |
| C4 | 真实存在 | `templates/grill.md:16-27`（时序）、`:132-159`（对抗环批次模型）、`:226-234`（写码硬条件 #2） |
| C5 | 真实存在 | `plugin/commands/review-loop.md:1-3`（front-matter）、`:22-33`（步骤 5/6）、`:62-71`（约束） |
| C6 | 真实存在 | `plugin/commands/grill.md:23-27`（步骤 5 的批次模型接线） |
| C7 | 真实存在 | `plugin/README.md:36-38`（命令说明中的批次模型 / 20 / 重开） |
| C8 | 真实存在 | `README.md:306-307`（核心卖点句） |
| C9 | 真实存在 | `docs/design.md:25-26`（目标第 4 条） |
| C10 | 真实存在 | `docs/gate.md:715-718`（`BLOCKED` 含超上限建议重开；机械接受 ≠ 终结出口；`CHANGES_REQUESTED` 是轮内状态） |
| C11 | 真实存在 | 第二次验证全量 `pytest -q` **753 passed**（HEAD `1dffc29`）；`templates/`、`plugin/`、`README.md`、`docs/design.md`、`docs/gate.md` 的旧口径 grep 无命中 |
| C12 | 真实存在 | `docs/gate.md:407`「常量封顶」、`:554`「路径深度封顶」、`docs/design.md:85`「封顶 ~5 条常量」均保留；`docs/reviews/**`、`docs/tasks.md`、归档 change 未回填 |

### D/E（未勾选，不报缺陷）

- D1 由本报告完成；D2–D4、E1–E4 均未执行。`witnessloop check` 当前报 4 条缺失 manifest，
  与 D3/D4 未执行一致，不是本批实现的缺陷。
- 提醒 D3：必须按实际文件名绑定 `reviews/grill-design.md`、`reviews/grill-adversarial.md`、
  `reviews/building-review.md` 三份报告；不要按旧示例去找
  `reviews/grill-review.md`（见 R1-6）。

## Test Results

### 第 1 轮开批时全量测试（仓内，HEAD `18424c1`）

```text
$ /home/happy/.local/bin/uv run pytest -q
........................................................................ [  9%]
........................................................................ [ 19%]
........................................................................ [ 29%]
........................................................................ [ 38%]
........................................................................ [ 48%]
........................................................................ [ 58%]
........................................................................ [ 67%]
........................................................................ [ 77%]
........................................................................ [ 87%]
........................................................................ [ 96%]
.......................                                                  [100%]
743 passed in 98.54s (0:01:38)
```

### 验证轮全量测试（仓内，HEAD `6c914ff`）

```text
$ /home/happy/.local/bin/uv run pytest -q
........................................................................ [  9%]
........................................................................ [ 19%]
........................................................................ [ 28%]
........................................................................ [ 38%]
........................................................................ [ 47%]
........................................................................ [ 57%]
........................................................................ [ 66%]
........................................................................ [ 76%]
........................................................................ [ 86%]
........................................................................ [ 95%]
.................................                                        [100%]
753 passed in 144.05s (0:02:24)
```

### 第二次验证全量测试（仓内，HEAD `1dffc29`）

```text
$ /home/happy/.local/bin/uv run pytest -q
........................................................................ [  9%]
........................................................................ [ 19%]
........................................................................ [ 28%]
........................................................................ [ 38%]
........................................................................ [ 47%]
........................................................................ [ 57%]
........................................................................ [ 66%]
........................................................................ [ 76%]
........................................................................ [ 86%]
........................................................................ [ 95%]
.................................                                        [100%]
753 passed in 71.69s (0:01:11)
```

### 第一次验证变异（HEAD `6c914ff`；保留以说明 R1-2 首次未修好的证据）

1. **R1-1**：把模板数字第 8 步改掉（`### 8.` → `### 八.`）：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_review_loop_template_has_eight_execution_steps
E  AssertionError: assert '### 8.' in '...'
FAILED tests/test_convergence_stop.py::test_review_loop_template_has_eight_execution_steps
1 failed in 0.58s
```

2. **R1-2**：把安全例外从 `⇒ SHALL 以` 精确改回 `⇒ 可`：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_review_loop_template_security_exception_is_shall
.                                                                        [100%]
1 passed in 0.07s
```

⚠️ 这是 **R1-2 未修好**的直接证据：守卫在回归发生时仍为绿色。原因是 `assert "SHALL 以" in text`
被模板 `:96` 的验证重试终止点满足；`assert "可 `BLOCKED`" not in text` 又匹配不到换行后的
``⇒ 可\n    `BLOCKED` ``。

3. **R1-4**：删掉 `README.md` 的「20」：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_normative_files_carry_their_required_terms
E  AssertionError: README.md 缺映射要求的 '20'
FAILED tests/test_convergence_stop.py::test_normative_files_carry_their_required_terms[README.md]
1 failed, 7 passed in 0.16s
```

4. **R1-4**：删掉 `plugin/commands/grill.md` 的 `deferred`：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_normative_files_carry_their_required_terms
E  AssertionError: plugin/commands/grill.md 缺映射要求的 'deferred'
FAILED tests/test_convergence_stop.py::test_normative_files_carry_their_required_terms[plugin/commands/grill.md]
1 failed, 7 passed in 0.38s
```

### 第二次验证变异（HEAD `1dffc29`；在 `/tmp/cbs-r2` / `/tmp/cbs-r2b` 副本执行，未改仓内文件）

1. **R1-2 模板**：把例外从 `⇒ SHALL 以\n    `BLOCKED`` 精确改回 `⇒ 可 `BLOCKED``：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_security_exception_is_shall_in_template_and_design
E  AssertionError: assert 'SHALL 以 `BLOCKED`' in '**例外**：该新问题使当前轮验证失去意义，或继续实现/验证本身不安全 ⇒ 可 `BLOCKED` + 成因终结，并在成因里写明为什么不能 deferred；'
FAILED tests/test_convergence_stop.py::test_security_exception_is_shall_in_template_and_design
1 failed in 0.05s
```

2. **R1-2 design**：把 design 例外改回 `⇒ 可 `BLOCKED``：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_security_exception_is_shall_in_template_and_design
E  AssertionError: ...
FAILED tests/test_convergence_stop.py::test_security_exception_is_shall_in_template_and_design
1 failed in 0.20s
```

3. **R1-12**：无自动化变异；直接核对 `tasks.md:114-123` 的
`## F. 审阅修复（building R1，2026-10-17）` 表，逐行包含 R1-1–R1-4、R1-12 与 low/nit 的
处置 / 落点 / 提交。

### 第 1 轮开批时目标测试子集（仓内，HEAD `18424c1`）

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py tests/test_templates.py tests/test_plugin.py
........................................................................ [ 91%]
.......                                                                  [100%]
79 passed in 0.84s
```

### 变异验证（在 `/tmp/cbs-mut` 副本执行，未改仓内文件）

1. 把 `templates/grill.md` 的新措辞改回「直到 PASS 或轮数封顶」：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_normative_surfaces_drop_the_old_round_cap
FAILED tests/test_convergence_stop.py::test_normative_surfaces_drop_the_old_round_cap[templates/grill.md]
1 failed, 10 passed in 0.11s
```

2. 在 `templates/review-loop.md` 追加一行裸「封顶」：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_normative_surfaces_drop_the_old_round_cap
E  AssertionError: templates/review-loop.md:224 含裸「封顶」：'封顶'；与本规则无关的行必须同行含「常量」或「路径深度」
FAILED tests/test_convergence_stop.py::test_normative_surfaces_drop_the_old_round_cap[templates/review-loop.md]
1 failed, 10 passed in 0.07s
```

3. 把适配器「步骤 1–8」改成「步骤 1–6」：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_convergence_stop.py::test_plugin_review_loop_adapter_runs_all_template_steps
FAILED tests/test_convergence_stop.py::test_plugin_review_loop_adapter_runs_all_template_steps
1 failed in 0.05s
```

4. 把模板正文的 100 字符段落逐字复制进适配器：

```text
$ /home/happy/.local/bin/uv run pytest -q tests/test_plugin.py::test_adapter_does_not_inline_the_template
E  AssertionError: review-loop 适配器内联了模板正文（共同段 99 字符 ≥ 60）
FAILED tests/test_plugin.py::test_adapter_does_not_inline_the_template[review-loop]
1 failed, 1 passed in 0.06s
```

以上变异均已恢复 `/tmp` 副本；仓内 `git status --short` 保持干净（本报告除外）。

### 机械门禁与既有判据

`git diff --name-only origin/main...HEAD -- src/` 输出为空（0 个文件），本 change 没有改
`src/`。实读既有判据：`src/witnessloop/evidence.py:259-330` 是 `stage=grill` 的正文完备性
（`Confirmed Decisions` ≥3 条且每条有 `来源:`、`Open Questions`、`User Confirmation`）；
`:334-380` 的 `verify_body=False` 对 `building` / `grill-adversarial` 只要求报告存在；
`src/witnessloop/contract.py:636-666` 是孤儿报告判据。与本 change「不新增正文解析」的声明一致。
本 change 的 spec `:274-306` 也如实写了这一点。

`grill-design.md` 正文自检：

```text
$ PYTHONPATH=src .venv/bin/python -c "from pathlib import Path; from witnessloop.evidence import grill_evidence_findings; p=Path('openspec/changes/convergence-based-stop/reviews/grill-design.md'); print(grill_evidence_findings(p.read_text(encoding='utf-8'), report_path=str(p)))"
[]
```

`witnessloop check`（当前 HEAD；D3/D4 尚未执行）：

```text
$ /home/happy/.local/bin/uv run witnessloop check --base origin/main --head HEAD
check：本包来源（自报，尽力而为）：requested_revision=<未知>，commit_id=<未知>
check：基线 origin/main...HEAD，17 个变更文件，1 个 change 目录
  change：convergence-based-stop
check：未通过 ✗（4 项）
  1. openspec/changes/convergence-based-stop：缺少 review manifest（审阅证据必须「报告 + manifest」成对，glob=reviews/*.manifest.json）
  2. openspec/changes/convergence-based-stop：无 stage=grill 的 manifest（现有 stage：（无））——grill 决策记录必须有对应的审阅证据
  3. openspec/changes/convergence-based-stop：无 stage=grill-adversarial 的 manifest（现有 stage：（无））——设计阶段的对抗验证轮（grill 之后、停轮之前的证伪环节）必须有审阅证据
  4. openspec/changes/convergence-based-stop：无 stage=building 的 manifest（现有 stage：（无））——本 change 改了受管控代码，必须有实现后的独立审阅证据（review-loop）
exit=1
```

这 4 条全部是 D3/D4 未执行导致的预期失败，不是本批实现缺陷。D3 完成后应复跑并记录原始输出。

### 旧口径扫描

- `templates/`、`plugin/`、`README.md`、`docs/design.md`、`docs/gate.md`：
  `3 轮封顶` / `三轮封顶` / `有界轮数` / `轮数封顶` / `N 轮封顶` / `或封顶` / 裸「封顶」均无命中
  （裸「封顶」的三条允许行 `docs/gate.md:407/554`、`docs/design.md:85` 仍在）。
- 规范面之外的旧口径保留在 `docs/tasks.md:43`、`tests/test_grill_adversarial_gate.py:180`
  与历史 change / `docs/reviews/**`，均在 design §4.4 的显式排除面内。
- `templates/review-loop.md`、`templates/grill.md` 中无 host 专有语法（`grep` 未命中
  `CLAUDE_PLUGIN_ROOT` / `Claude` / `plugin/` / `.claude`）；适配器物理分离守卫已用变异验证变红。

## 结论

**最终 Verdict：PASS**

| 轮次 / id | 结果 | 关键证据 |
|---|---|---|
| 第 1 轮 R1-1 | 已修好 | 模板 8 步（`templates/review-loop.md:48,53,66,79,89,112,121,164`）；适配器 `:22`；删数字第 8 步 ⇒ `1 failed` |
| 第 1 轮 R1-2 | 已修好（第 2 次验证） | `tests/test_convergence_stop.py:154-173` 绑到例外段（模板 + design）；模板/design 变异均 `1 failed`；三处文本均 `SHALL` |
| 第 1 轮 R1-3 | 已修好 | `reviews/grill-adversarial.md:3-9,11,93,179,218`；表格行无旧 id |
| 第 1 轮 R1-4 | 已修好 | `tests/test_convergence_stop.py:58-68,162-175`；`plugin/commands/grill.md:25`；`docs/gate.md:718`；两处变异 `1 failed` |
| 第 2 轮 R1-12 | 已修好 | `tasks.md:114-123` 的 `## F. 审阅修复（building R1）` 逐行列出修复 |

- 第 1 轮与第 2 轮均已收口；第 3 次开批为空（0 条 medium+）⇒ **`PASS`**。
- deferred **0 条**（R1-12 已进入第 2 轮并修好）。
- **low/nit 共 10 条**：`R1-5`–`R1-11`（原 `L1`–`L7` 重排）与 `R1-13`–`R1-15`；
  其中 R1-6 / R1-10 / R1-13 / R1-15 已修，R1-5 / R1-14 部分已修，其余登记不修。
- 第二次验证全量测试 `753 passed`（HEAD `1dffc29`）。

**必须修改项**：无。

**已确认无问题项**

- 第 1 轮 R1-1–R1-4 与第 2 轮 R1-12 全部已修好；R1-1/R1-2/R1-4 的守卫均已在 `/tmp` 变异下变红。
- 新模型七要素仍真实落进 `templates/review-loop.md` 与 spec：批次冻结、验证期 deferred、
  20 上限、超上限 `BLOCKED` + 建议重开、medium+ 全修、low/nit 登记须理由、三出口
  （`templates/review-loop.md:8-16,66-177,203-224`；`spec.md:24-306`）。
- 两个环都覆盖：`templates/grill.md:132-159` 明确与 review-loop 同构；frontier 豁免边界写入
  `templates/grill.md:154-155` 与 `spec.md:254-256`。
- 旧口径已从规范面清除；`docs/gate.md:407/554`、`docs/design.md:85` 的无关「封顶」保留。
- `src/` 未改；`check` 的既有判据（含 `stage=grill` 正文完备性）与「不新增正文解析」声明一致。
- 适配器未复制模板正文（物理分离测试可变异变红）；`plugin/` 文件清单未变。
- 模板无 host 专有语法。
- `reviews/` 只有两份新模型报告；旧模型报告已被覆盖、没有为旧文件建 manifest。
- 旧短语、裸「封顶」、适配器 1–6、模板内联四类守卫仍可变红。

**后续批注意**

- D2 的审阅侧已随 PASS 完成；D3 必须绑定三份实际报告
  （`grill-design.md` / `grill-adversarial.md` / `building-review.md`）；D4 再跑 `check`。
- D/E 的 `[ ]` 不构成本批缺陷；本报告不据此打回。
- `witnessloop check` 当前仍报 4 条缺失 manifest，这是 D3/D4 未执行导致的预期失败，
  不是本报告的 PASS 之外的新 finding。
