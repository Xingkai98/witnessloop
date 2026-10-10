# Grill：issue #3 设计追问（`WITNESSLOOP_RUN_ID` 无自动注入点，影响证据幂等）

> 设计对象 = GitHub issue #3 的 comment「设计（待 grill + 用户确认后才能落实现）」，原文另存
> `/tmp/wl-grill/DESIGN.md`。**审的是设计，不是工作树里的未提交草稿**——草稿只是「该设计
> 会怎么落」的参考，不替它背书。
> READ-ONLY：**本审阅阶段**未产生任何新改动、未动 git（工作树里那 11 个改动文件是先前草稿，见上）。
> 时序按 `templates/grill.md`：grilling pass（审阅者独立求完备）→ 设计阶段对抗验证 loop
> （另起审阅者证伪 → 修 → 再审）→ **收敛后才停轮**。

## Reviewer
- run id（grilling pass）: `66a54c06-de97-4d6f-9cef-79c1b905a1b7`
- run id（对抗验证）: `51044ff3-7dcb-48c5-baac-1b043dd89733`
- 时间: 2026-10-10T11:07Z（grilling pass）/ 2026-10-10T11:09Z（对抗验证）

## Confirmed Decisions

- **CD1**：**兜底改确定性**——`<stage>-<role>-<anchor>`（本 change 唯一的行为改动）；
  取值链的关键性质（`role` 编进 id）与形态不变。理由：非确定性兜底
  `<stage>-<role>-<UTC 时间戳>-<短随机>` 使同一逻辑 run 重复 `manifest build` 产出不同
  manifest（这正是 issue #3 的现象）。来源: `66a54c06-de97-4d6f-9cef-79c1b905a1b7`
- **CD2**：**保留两级环境覆盖，优先级 `角色专用 > WITNESSLOOP_RUN_ID > 确定性兜底` 不变**；
  本 change 只改「兜底」一段。理由：与既有取值策略逐字一致，把「真实 run 身份」的入口留给
  host 注入——host（CC）无稳定注入点是整套设计的既定前提。来源: `66a54c06-de97-4d6f-9cef-79c1b905a1b7`
- **CD3**：**anchor = `change_id` + `head` 短摘要，不含 `base_sha`**。理由：base ref 会随上游
  合并漂移；把 base 编进锚会让 id **无谓抖动**（同一逻辑 run 重建得到不同 id）。head 才是
  「审的是哪个 revision」的判据。
  **修正（对抗验证）**：排除 base 只保住了「**id 稳定**」，**没有**保住「**manifest 字节可复现**」
  ——base 漂移仍改 `base_sha`/`diff_hash`（见 Q2）。原文「直接破坏幂等主张」只对 id 成立。
  来源: `66a54c06-de97-4d6f-9cef-79c1b905a1b7`（对照 `51044ff3-7dcb-48c5-baac-1b043dd89733`）
- **CD4**：**不删除 run id，本 change 也不改为绑定真实 run**。理由：删除会一并丢掉
  `reviewer ≠ author` 这条既有的反「审阅剧场化」控制；绑真实 run 受制于 host 无稳定注入点，
  属另一个 change。来源: `66a54c06-de97-4d6f-9cef-79c1b905a1b7`
- **CD5**：**旧的非确定性 manifest 保持兼容**，本 change 不新增任何 run-id 形态校验。理由：
  `check` 对 run id 只做「非空」与「不相等」两项判定，无格式/前缀校验 → 旧时间戳 id 照过。
  来源: `66a54c06-de97-4d6f-9cef-79c1b905a1b7`
- **CD6**：**兜底路径下 `reviewer ≠ author` 是「结构性恒真」，它不再等于「挡忘了另开 run」**。
  理由：`role` 编进 id 后，兜底路径下两个 id 天然不同、**门禁 D4 永不触发**；D4 只挡「显式把
  同一个值喂给两个角色」。必须把这条口径与 R4、`docs/design.md:107-108`、`docs/gate.md:108`
  统一，别一处说「挡忘开 run」、一处承认它不证独立性。来源: `51044ff3-7dcb-48c5-baac-1b043dd89733`（对抗校正）
- **CD7**：**「照着 export / 照着填」是误导文案，必须改正**——把打印的 id 抄进**共享**变量
  `WITNESSLOOP_RUN_ID` 会让两角色 id 合并、被 `build` **直接拒写**。真正含该文案的两处是
  **`plugin/README.md:54-55`** 与 **`plugin/commands/grill.md:56`**（`plugin/commands/review-loop.md`
  的对应段**没有**这句话，不应被点名）。改成：「要 pin 真身份用**角色专用**变量
  `WITNESSLOOP_REVIEWER_RUN_ID` / `WITNESSLOOP_AUTHOR_RUN_ID` 分别设；只设共享变量会被拒；
  兜底路径下**无需任何 export**」。来源: `51044ff3-7dcb-48c5-baac-1b043dd89733`
- **CD8**：**`cli.py:87` 的 `--reviewer-run-id` help「…→ 生成）。给了才幂等」现已为假**，
  须改为「缺省走确定性兜底，同样幂等」；并把 `src/witnessloop/cli.py` 纳入
  `tests/test_docs.py` 的漂移守卫（当前 `RUN_ID_DOCS` 只覆盖 6 个 md，抓不到这处）。
  来源: `51044ff3-7dcb-48c5-baac-1b043dd89733`
- **CD9**：**幂等主张须限定范围**——写成「**固定 base 与 revision 时** manifest 逐字节可复现」，
  幂等键含 base ref 的解析目标；同步 `cli.py:73` 那句无条件「幂等」。理由见 Q2 实测。
  来源: `51044ff3-7dcb-48c5-baac-1b043dd89733`

## Code-Resolved Questions

- **`check` 会不会因新的确定性 id 判错？** → 不会。只校验 (a) 字段非空（`contract.py:238-244`，
  取自 `constants.py:61-70`）；(b) `reviewer_run_id != author_run_id`（`contract.py:254`）。
  **无**任何正则/前缀/长度校验。`contract.py:248` 那条校验的是 `change_id`（与目录比），不是
  run id。（证据：`src/witnessloop/contract.py:238-260`）
- **旧的非确定性 manifest 兼容吗？** → 兼容。旧时间戳 id 非空、两角色不同 → 两项判定全过。
  （证据：同上一行）
- **兜底 id 是 manifest 里唯一的非确定源吗？** → **输入固定时是**。其余字段来自 git
  （`base_sha`/`head_sha`/`diff_hash`）或 artifact 字节（三个 hash），序列化 `sort_keys=False`、
  字面量顺序固定。**例外**：`base_sha`/`diff_hash` 依赖会漂移的 base ref（见 Q2）。
  （证据：`src/witnessloop/manifestcmd.py:84-139`；`src/witnessloop/policy.py:129-130`）
- **`build` 的输出走哪个流？会污染 CI 吗？** → 成功走 **stdout**（`manifestcmd.py:141-144`），
  失败走 **stderr**（`manifestcmd.py:29`）。CI 只跑 `check`、**不跑** `build`（`gate.yml` 是
  `workflow_call`、只 `witnessloop check`；本仓 `ci.yml` 只 pytest + `uv build`）。故 stdout
  **不进**任何门禁解析链路。（证据：`src/witnessloop/manifestcmd.py:29,141-144`；`.github/workflows/`）
- **`build` 取哪次提交作 head？** → 无 `--head` 参数；`head_sha = rev_parse(root, "HEAD")`
  （空仓提前 `_fail`）。按「先内容、后证据」，build 在证据提交**之前**跑，head = **内容提交**。
  （证据：`src/witnessloop/cli.py:72-99`；`src/witnessloop/manifestcmd.py:93-95`）
- **锚取 head 还是 base？** → 取 **head**：`default_run_anchor(change_id, head_sha)`；`base_sha`
  算而不入锚。（证据：`src/witnessloop/agentenv.py:41-47`；`src/witnessloop/manifestcmd.py:96-103`）
- **优先级实现顺序？** → `for name in (role_env_name(role), RUN_ID_ENV)`，角色专用在前。
  （证据：`src/witnessloop/agentenv.py:36-38,66-70`）
- **`change_id` 含 `-` 会不会让锚歧义？** → **不会**。锚 = `change_id + "-" + head[:8]`，而
  `head[:8]` 恒为 8 字符（`rev_parse` 恒返回 40 位 sha），末 9 字符恒为 `-`+8 位，可无歧义回切。
  （**实测**：`default_run_anchor("foo-0123", "456789ab…")` = `foo-0123-456789ab`，
  而 change `foo` + head `01234567…` = `foo-01234567`，两者**不相等**；因前缀不定长但后缀恒 8 位，
  可无歧义回切。）
- **`change_id` 含 `/` 呢？** → `default_run_anchor` 直接 f-string **不归一化**，run id 里会出现
  `/`（**实测**：在临时仓建好嵌套目录 `openspec/changes/a/b/`（必需件齐备）后，
  `manifest build --change "a/b"` **`exit=0` 放行**，写出 `change_id='a/b'`、
  `reviewer_run_id='building-reviewer-a/b-<head8>'`）。即 `validate_change_dir`（`contract.py:89-100`）
  只在**目录不存在**时报「change 目录不存在」（`:93-94`）、在**目录存在但缺件**时报「缺少必需件」
  （`:97-99`）；**目录齐备即放行、不按段数拒绝**。真正拦得住的是
  **另一条路径**：`check` 侧 `contract.changed_change_ids` 对路径 `split("/")` **取首段**，会把
  `a/b` 看成 change `a`、在 `check` 阶段失配——**两条口径不一致**（既存问题，#3 把 change_id 写进
  身份串放大了它）。（证据：`src/witnessloop/manifestcmd.py:51-58`；`src/witnessloop/contract.py:58-86,89-100`）
- **`head_sha` 为 None 的路径？** → `default_run_anchor` 无守卫（`None[:8]` 会 `TypeError`），但
  当前由 `manifestcmd.py:94-95` 提前 `_fail` 挡住，**不可达**；把该函数导出为可复用 API 时应注明
  「调用方保证 head_sha 非 None」。（证据：`src/witnessloop/manifestcmd.py:93-95`）
- **空 env / 纯空白？** → `(env.get(name) or "").strip()` 后为空 → 走兜底；`"  x  "` → `"x"`。
  行为正确。（证据：`src/witnessloop/agentenv.py:65-70`）
- **导出的 `role` 取值固定吗？** → 调用点只用 `"reviewer"` / `"author"`，形态 `<stage>-<role>-<anchor>`
  因此可预测。（证据：`src/witnessloop/manifestcmd.py:104-109`）

## Open Questions

- **Q1 — anchor 的组成与短摘要长度？**
  场景：change `run-id-determinism`、stage `building`、内容提交 head `d70f2f99c077…`。
  - **A（仅 `change_id`）**：`building-reviewer-run-id-determinism` / `building-author-run-id-determinism`。
    缺点：**同一 change 的不同 revision 得到同一个 id**——审 rev1 与 rev2 的 reviewer id 完全相同，
    id 无法区分「审的是哪一版」。
  - **B（`change_id` + `head[:8]`，草稿选项）**：`building-reviewer-run-id-determinism-d70f2f99`。
    改一字节 → 新 head → 新 id；base 漂移**不影响** id。
  - **C（`change_id` + base + head）**：上游 `main` 前进（本 change 内容**分毫未动**）→ id 从
    `…-X-d70f2f99` 变成 `…-Y-d70f2f99`，同一逻辑 run 重建得到**不同** id → 幂等破裂。
  - ➡️ **推荐答案**：取 **B**，且把短摘要从 8 位提到 **≥12 位**（8 位仅 32 bit；碰撞概率虽低，
    但一旦撞上会让 id **丧失对 revision 的区分力**——权威区分仍在 40 位 `head_sha`，故不致命）。
- **Q2 — 「幂等」的契约怎么写才不含糊？**
  场景：内容不动，两次 build 之间 `origin/main`（缺省 base，`gitutil.resolve_base` 的回落目标）
  前进一次 ⇒ 第一次 `base_sha=X`/`diff_hash=H(X..head)`，第二次 `base_sha=Y`/`diff_hash=H(Y..head)`
  ⇒ 即便 `reviewer_run_id`/`author_run_id` **完全相同**，**manifest 字节不同**（对抗验证实测）。
  即当前定义「同 (change, stage, role, revision) 两次 build 字节一致」在 base 会动的环境里**为假**
  ——确定性 run id 是幂等的**必要不充分**条件。
  ➡️ **推荐答案**：把幂等键显式写成 **(change, stage, role, revision, base ref 的解析目标)**；文档
  与 `cli.py:73` 把「逐字节可复现」限定为「**固定 base 与 revision 时**」；测试要么用
  `--base <固定 sha>` 钉死 base，要么**补一条反向断言**（base 漂移**会**改变字节）——把边界钉住，
  别让假绿盖住它。
- **Q3 — 身份强度：接受「目标指纹」降级，还是投入真实 run 绑定？**
  场景：同一 stage、同一 revision 上**两个真正独立的真实审阅 run**，兜底路径下得到**一模一样**的
  id ⇒ 该字段**不承载独立性信息**；`reviewer ≠ author` 在兜底路径下**结构性恒真**、名存实亡。
  - 选项 1（接受，草稿）：保留 run id 作「审阅目标的指纹」，文档**说穿**它不证独立性；要真身份就设
    `WITNESSLOOP_RUN_ID`。
  - 选项 2（加强）：从 host 拿真实 run id / 绑 CI run——受制于 CC 无稳定注入点，属另一个 change。
  - 选项 3（fail-closed）：缺 env 时**报错**、逼用户 export——CC 无注入点，等于每次手工 export，高摩擦。
  - ➡️ **推荐答案**：**选项 1**（保留但说穿），并把 CD6 的口径统一到 `docs/design.md:107-108` /
    `docs/gate.md:108`。这也是「去掉 run id」的否证：去掉会一并丢这条（虽弱）的控制。
- **Q4 — 「打印实际 id」的形态与用法？**
  场景：用户看到 `reviewer_run_id=building-reviewer-X  author_run_id=building-author-X`，据
  `plugin/README.md:54-55`「照着填即可」把唯一的共享变量 `WITNESSLOOP_RUN_ID` 设成 reviewer 那个
  ⇒ 两角色**合并**、被 build **直接拒**（对抗验证实测 `exit=1`）。
  - 形态：现走 stdout（`manifestcmd.py:144`），`build` 不在 CI 链路，**无害**。
  - ➡️ **推荐答案**：(a) 保留 stdout，可选加 `--json`/单行稳定格式供脚本抓取；(b) 按 CD7 **改掉**
    `plugin/README.md:54-55`、`plugin/commands/grill.md:56` 的「照着 export/填」，改为「用角色专用
    变量分别设；只设共享变量会被拒；兜底路径下无需 export」。

## 风险

- **R1（修正后）**：`head[:8]` 仅 32 bit，碰撞后果是 **id 丧失对 revision 的区分力**（**不是**「两份
  manifest 并存共用同一 id」——同 `(change, stage)` 唯一路径 `reviews/<stage>.manifest.json`，
  跨 revision 只会**覆盖**）。权威区分在 40 位 `head_sha`，故不致命但违背「id 一眼看懂是哪一版」
  的初衷。→ 摘要 ≥12 位。
- **R2**：现有幂等测试钉在固定本地 `main`、且老用例显式传 `run-reviewer-1/run-author-1`，**改前就已
  幂等**——**盖不住** base 漂移边界，会让「幂等」看起来比实际更强。
- **R3**：user-facing「幂等」串（`cli.py:73`、`plugin/README.md:51`）在跨 base 场景下为假（Q2 已证）。
- **R4**：文档尚未同步「身份字段 = 目标指纹、不证独立性」这一层（`docs/design.md:107-108`、
  `docs/gate.md:108` 仍按「挡忘了另开 run」措辞）。
- **R5（前向）**：当前 `check` 不校验 run-id 形态，故旧 manifest 安全；**一旦日后**加形态校验，
  所有已落盘的旧时间戳 id 会**突然变红**——若加须配迁移/宽限。
- **R6**：草稿删除了 `test_generated_ids_are_unique_across_many_calls`（断言 200 次生成互不相同），
  替换为确定性断言——这是测试意图的**主动翻转**（从「唯一」到「可复现」），方向对，但应在 design
  里**显式记录**，免得后续审阅者当成回归。
- **R7**：`change_id` 含 `/` 的口径不一致——`manifest build` 侧**实测放行**（`exit=0`，run id 里出现
  `/`），而 `check` 侧 `changed_change_ids` 对路径 `split("/")` **取首段**、会把 `a/b` 看成 `a`。这是
  **既存**问题，#3 把 change_id 写进身份串**放大**了它；设计应决定锚里的 change_id 是否归一化成单段。
- **R8**：`manifest build` 的**幂等窗口 = 同一 HEAD + 同一 base 解析目标**；按「先内容、后证据」，
  证据提交后再跑 build 会把 `head_sha` 顶到证据提交、anchor 随之改变（= 换了 revision）。设计应
  显式写明「不要在证据提交后重跑 build」，而非默认它不会发生。

## User Confirmation

> 用户在**对抗验证收敛之后**被停轮一次、逐条拍板（2026-10-10）。以下为最终决策，均已整合进设计文档。

- **Q1（anchor 组成 / 摘要长度）**：用户答复：**选 B** —— `anchor = change_id + head_sha 短摘要`，
  且**短摘要取 ≥12 位**（**不用**草稿的 8 位）。依据：head 才是「审的是哪个 revision」的判据；
  base 易漂移、编进锚有害无益；加长摘要避免 id 丧失 revision 区分力。时间: 2026-10-10
- **Q2（幂等契约）**：用户答复：**幂等键显式写成 `(change, stage, role, revision, base ref 的解析目标)`**；
  文档与 `cli.py` 把「逐字节可复现」**限定为「固定 base 与 revision 时」**；测试要么用 `--base <固定 sha>`
  钉死，要么**补一条反向断言**（base 漂移**会**改变字节）。依据：只固定 run id 不足以保证字节一致
  （base 漂移仍改 `base_sha`/`diff_hash`）。时间: 2026-10-10
- **Q3（身份强度）**：用户答复：**接受「目标指纹」降级**——保留 run id 作「审阅目标的指纹」、文档**说穿**
  它不证独立性；要真身份就设 `WITNESSLOOP_RUN_ID`。并把 `docs/design.md`（run id 段）与 `docs/gate.md`
  里「挡忘了另开 run」的口径统一为「**结构性恒真、只挡显式把同一值喂给两角色**」。依据：绑真实 run
  受制于 host 无稳定注入点（属另一 change）；fail-closed 高摩擦。时间: 2026-10-10
- **Q4（打印形态 / 文案）**：用户答复：**保留 stdout 输出**（可选加 `--json`，`build` 不在 CI 链路）；
  **改掉** `plugin/README.md` 与 `plugin/commands/{grill,review-loop}.md` 里「照着 export/填」的文案
  ——写成「要 pin 真身份用**角色专用**变量 `WITNESSLOOP_REVIEWER_RUN_ID` / `WITNESSLOOP_AUTHOR_RUN_ID`
  分别设；只设共享变量会被拒；**兜底路径下无需 export**」。依据：把打印的 id 抄进共享变量会让两角色
  合并、被 `build` 拒写（实测）。时间: 2026-10-10

**整合落点**：Q1–Q4 + 对抗验证的必须修改已写进 `docs/design.md`（§5.2 / §5.3 / §9）、`docs/gate.md`、
`plugin/README.md`、`plugin/commands/grill.md`、`plugin/commands/review-loop.md`、
`templates/grill.md`、`templates/review-loop.md`。`src/` 实现待另开（草稿与定稿的差异见会话返回的 gap 报告）。
