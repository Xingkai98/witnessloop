# Grill: dogfood-bootstrap 设计追问

> 独立零记忆审阅者产出。算法与产物格式依据 `templates/grill.md`（第 3–5 步）。
> 本文件**只做设计求完备**：把能由代码/规格判定的自行定案，把真正需要人取舍的留成 Open Questions。
> **不做**第 6 步（停轮）与第 7 步（整合 design）——那是作者主 session 的事。

## Reviewer

- run id: `grill-reviewer-dogfood-bootstrap-2026-10-11`
- 时间: 2026-10-11T06:33:46Z

## Confirmed Decisions

> 逐条**证伪后再确认**。每条给出「核到了什么」，不是复述设计。

- **决策（D1）**：`specs/` 是 `manifest build` 的**硬要求，policy 改不掉**——属实，且比设计说得更死。
  理由：`HASHED_ARTIFACTS` 是常量，含 `("spec_hash","specs")`、`("tasks_hash","tasks.md")`（`src/witnessloop/constants.py:55-58`）；
  `manifest build` 对该表**逐项** `if not target.exists(): return _fail(...)`（`src/witnessloop/manifestcmd.py:96-99`），
  这条路径**不读** `policy.required_artifacts`。删 `required_artifacts` 里的 `specs` 只影响 `check` 的目录存在性判定
  （`src/witnessloop/contract.py:97-100`）与 build 先跑的契约判定（`manifestcmd.py:72-75`），救不了上面那次 `_fail`；
  **也救不了 `check`**——`_check_hashes` 同样硬要求 `specs` 存在（`src/witnessloop/contract.py:379-383`：
  `target=directory/"specs"`，缺则 `findings.append("specs 不存在，无法校验 spec_hash")`）。
  ⇒ 本 change **必须**提供真实 `specs/` 文件，「改 policy 绕开」是**双重的**伪出路。来源: `grill-reviewer-dogfood-bootstrap-2026-10-11`
- **决策（D2）**：`init` **确无 policy 定制通道**——属实（行号需校正，见风险 R3）。
  理由：`desired_files(gate_ref)` 签名只吃 `gate_ref`，内部写死 `policy.default_policy_doc()`（`src/witnessloop/initcmd.py:44-48`，`default_policy_doc()` 落点 `:46`）；
  `cli.py` 的 `init` 子命令只挂 `--root` / `--dry-run` / `--gate-ref`，无 `--policy`（`src/witnessloop/cli.py:39-47`）。
  ⇒ 「补 `--policy`」是对真缺口的补，不是镀金。来源: `grill-reviewer-dogfood-bootstrap-2026-10-11`
- **决策（D3-a）**：A 新增的**那两份具名不变集文件**在「新增」时免解释——**不是**整个 `.witnessloop/**` 免解释
  （口径收正，见对抗验证第 3 条）。
  理由：免解释只在 `by_invariant and status[:1]=="A"` 时 `continue`（`src/witnessloop/checkcmd.py:154-158`），
  而 `by_invariant` 只匹配**不变集 4 条 patterns**（`src/witnessloop/policy.py:18-23`）——含 `.witnessloop/policy.json`、
  `.witnessloop/init-manifest.json`。默认 `protected_paths` 的 `.witnessloop/**`（`policy.py:35-37`）只让 `by_policy=True`，
  **不**触发免解释：新增一个 `.witnessloop/extra.json` 仍要解释事件（`:157`）。
  ⇒ A 之所以免事件，是因为它新增的**恰是那两个具名不变集文件**，不是因为「在 `.witnessloop/**` 下」。
  来源: `grill-reviewer-dogfood-bootstrap-2026-10-11`
- **决策（D3-b）**：A 自身的 diff **预期绿、无需任何解释事件**——逐类核过，成立（前提是 change 目录补齐，见 CRQ1）。
  理由：A 的变更分类 = `src/**`（M，命中 `require_change_for`，但 change 目录在 ⇒ 满足）、`.witnessloop/**`（A，不变集免解释）、
  `.github/workflows/witnessloop.yml`（既不在 `protected_paths` 也不在不变集 ⇒ 普通文件）、`openspec/changes/**`（普通；
  其内 `reviews/*.manifest.json` 属不变集且 A ⇒ 免）、`docs/**` 与 `tests/**`（**不在** `require_change_for`）。
  逐类比对 `checkcmd.py:84-112`（require_change）与 `:151-171`（protected writes）。来源: `grill-reviewer-dogfood-bootstrap-2026-10-11`
- **决策（D5）**：D5 里「实现期待核实」的 GitHub 问题**已定案：`pull_request` 事件取 PR head（merge ref）侧的 workflow 文件，非 base 侧**。
  理由：GitHub 官方文档——`pull_request` 触发的 workflow 定义取自 PR head/merge 提交，运行上下文是合成的 merge commit；
  `pull_request_target` 才锁 base（见文末来源）。⇒ A 合并进 `main` 后，任何以 `main` 为 base 的 PR（无论改什么）都会带上 `main` 的 caller
  而触发；A 自己若开 PR 也会触发 caller（但见风险 R5：required check 未勾选，不拦）。来源: `grill-reviewer-dogfood-bootstrap-2026-10-11`
- **决策（D2 台账）**：手改 `.witnessloop/policy.json` 会**打破台账**——属实。
  理由：`uninit` 逐文件核 `sha256_bytes(path.read_bytes()) != entry["sha256"]`，不等即进 `conflicts` 并**整批拒删**
  （`src/witnessloop/uninitcmd.py:59-61, 71-87`）；重跑 `init` 同理会报「被改动过」（`initcmd.py:153-168`）。
  ⇒ 「先 init 再手改」确有代价，`--policy` 一次写正确的动机成立。来源: `grill-reviewer-dogfood-bootstrap-2026-10-11`

## Code-Resolved Questions

- **A 的 change 目录现在合契约吗？** → **不合：缺 `tasks.md`，且 `specs/dogfood/` 是空目录（无 spec 文件）。**
  实测：`find openspec/changes/dogfood-bootstrap -type f` 只有 `proposal.md`、`design.md`。这会让证据链**当场失败**：
  `manifest build` 先跑 `contract.validate_change_dir`，`required_artifacts` 含 `tasks.md`、`specs`、`reviews`
  ⇒ 报「缺少必需件 tasks.md」并 `_fail`（`contract.py:97-100` 经 `manifestcmd.py:72-75`）；即便绕过，后面 `HASHED_ARTIFACTS` 循环也因
  `tasks.md` 缺失 `_fail`（`manifestcmd.py:96-99`）。⇒ 实现前**必须先补** `openspec/changes/dogfood-bootstrap/tasks.md`
  与 `specs/<cap>/spec.md`（证据：`contract.py:97-100`、`manifestcmd.py:72-75, 96-99`）。
- **已初始化后再 `init --policy <与默认不同>` 会怎样？** → **现状是「静默 no-op（exit 0『幂等』）」，不是设计 D2 所称的「报 diff 拒绝」。**
  证据：`run` 一见 `init-manifest.json` 存在就走 `_already_initialized`（`initcmd.py:97-98`）；该函数只比**磁盘文件 vs 台账 hash**
  （`initcmd.py:144-154`），**从不比磁盘 vs `desired`**——`desired` 仅在发现 drift 时用于**渲染** diff。故 policy 未被动过时，
  传一个不同的 `--policy` 也判「无 drift」→ 打印「幂等，无改动」并 exit 0，用户的 policy **被悄悄忽略**。
  ⇒ 要兑现 D2/§5 的「冲突」承诺，必须**新增**比较分支（desired-vs-台账，或 desired-vs-磁盘）。证据：`initcmd.py:97-98, 134-171, 144-154`。
- **本仓已发布的 `@v1` 里有 `--policy` 吗？** → **没有。** `v1` 是**带注释 tag**：`git rev-parse v1` = `19ac94c`（tag 对象），
  解开后 `git rev-parse v1^{}` = `843b691`（= `main`，早于 HEAD `6aa9821`）；
  `git show v1:src/witnessloop/cli.py` 中无 `policy` 选项，`v1:src/witnessloop/initcmd.py` 的 `desired_files` 同现状。
  ⇒ A 的 bootstrap `init --policy` **必须跑源码/本地构建**，不能跑 `uv tool install …@v1`（那一版没有这个选项）。
  证据：`src/witnessloop/cli.py:39-47`（本仓版本，A 将改）+ tag `v1`（tag 对象 `19ac94c` → commit `843b691`）。
- **`check` 怎样定位 change id、怎样判报告？** → change id 取 `changes_root/<首段>`（`contract.changed_change_ids`，`contract.py:82-86`）；
  报告路径必须落在 `reviews/` 下（`manifestcmd.py:84-90`，「必须落在 `reviews/` 下」那条 `_fail`）；
  `reviews/**/*.md` 里**每个**报告都必须被某份 manifest 的 `report_path` 引用，否则报孤儿（`contract.py:184-218`）。
  ⇒ A 若产出 `grill-review.md` / `grill-adversarial.md` / `building-review.md` 三份报告，**必须**各有
  `grill.manifest.json` / `grill-adversarial.manifest.json` / `building.manifest.json` 三份 manifest——
  「跑一次绑一份、另一份晾着」会被门禁拦。另：每份 manifest 内 `reviewer_run_id != author_run_id` 是**硬拒**
  （`manifestcmd.py:122-127`）；确定性兜底 id 含 `stage` ⇒ 三份天然互异，无需额外手工区分。
  证据：`contract.py:82-86, 184-218`、`manifestcmd.py:84-90, 122-127`。
- **本 change 会不会死锁 / 误伤自己？** → **不会自锁**，只有一处已知「鸡生蛋」，设计已承认。
  证据链：A 新增 `templates/**`、`plugin/**` 到 `require_change_for`，但 A 自身**不触碰**这两处 ⇒ 不自我触发；
  A 改 `src/**` 命中 `require_change_for`，但 change 目录在 ⇒ 满足；A 新增 `.witnessloop/**` 走不变集新增档 ⇒ 免解释
  （`checkcmd.py:151-158`）；A 的 CI `check` 由 `@v1` 的二进制跑、只读**数据** policy ⇒ 不依赖本 change 的新码，无引导死锁。
  唯一「鸡生蛋」= A 自己不被机械拦（required check 未勾选），D5 已诚实记为 bootstrap 靠自觉一次。
  证据：`checkcmd.py:84-112, 151-171`、`contract.py:58-86`。
- **现状表里「零 PR / main 无保护」能在仓内核实吗？** → **不能，属外部状态。** 仓内可核实的是 CI 面：
  `ci.yml` 只跑 `pytest`+打包（`.github/workflows/ci.yml:19-34`）、`gate.yml` 仅 `on: workflow_call`（`.github/workflows/gate.yml:11-12`）；
  「`gh pr list` 为空」「protection 404」须 `gh` 实仓核（见风险 R7）。

## Open Questions

- **Q1** `init --policy` 纳入本 change，还是拆成独立 change（A0）？
  - ➡️ **推荐答案：纳入本 change（A）。** 若拆 A0，则 A 只能用**默认** policy——`templates/**`、`plugin/**` **不被覆盖**，
    交互层改动（只改 `templates/grill.md` 而不碰 `src/`）可**无 change 目录**放行，正是本 change 要堵的**已知绕过洞**；
    且 A0 自己也得走一遍完整 change 契约，净增一轮证据开销而无额外收益。例子：未来一个「微调 grill 算法」的 PR，
    不挂 change 目录即可通过 `check`——除非 `--policy` 与 A 同批落地。
- **Q2** A 自己只能本地 `check`（bootstrap 靠自觉一次）——可接受？
  - ➡️ **推荐答案：接受，这是鸡生蛋的固有代价，无法在同一 change 内消除。** 例子：A 的 PR 即便触发了 caller workflow，
    `main` 的 required check 尚未勾选 ⇒ 不拦人；本次靠**本地** `witnessloop check --base main --head HEAD` + 人工 review 兜一次，
    A 合并后**才**机械强制。文档须写明「A 之后才机械强制」，别让读者以为 A 自身被门禁验过。
- **Q3** `main` 是否**同时**开「禁止直接 push（require PR）」？还是先只加 required check？
  - ➡️ **推荐答案：同时开，且必须。** 只加 required check 而不禁直推，任何人 `git push origin main` 直接绕过 PR，
    required check **永不触发** ⇒ 门禁等于没开（与本设计 §4 风险 5 同款）。例子：开 require PR + required check 才是完整 merge boundary；
    反之，先只勾 required check 会给「已上机械门禁」的**假安全感**。
- **Q4** witnessloop 的 `protected_paths` 要不要加 `templates/**`（视交互层为受保护 artifact）？
  - ➡️ **推荐答案：不加 `protected_paths`；`templates/**`、`plugin/**` 只进 `require_change_for`（D2 已含）。**
    理由：进 `protected_paths` ⇒ 每次改 `templates/grill.md` / `plugin/commands/*.md` 都要手写一条解释事件（`reason`/`approved_by`），
    属**纯噪音**；而 `require_change_for` 已强制「改它必须挂 change 目录 + 有 manifest 绑定的证据」，保护强度已足。
    例子：一次「收紧 grill 的对抗轮数」的 `templates/` 改动——用 change 目录里的 `design.md`/`spec.md` 承载理由，
    比一行自由文本事件的**信息量更大**、更可审计。反方意见：`templates/` 是「流程的规范定义」，与已被保护的 `openspec/specs/**` 同性质——
    若采纳此立场则加 （代价 = 每次改动多一条事件）。**此点请用户定夺。**
- **Q5** A 的定制 policy **源文件**是否入库、放哪？
  - ➡️ **推荐答案：不单独入库；让已提交的 `.witnessloop/policy.json` 作为唯一权威 policy，`--policy` 的输入一次性使用。**
    例子：把 desired policy 写成 `openspec/changes/dogfood-bootstrap/` 下的临时 seed 跑一次 `init --policy`，产物入库即可；
    若把 seed 也提交，就多了一份与 `.witnessloop/policy.json` 重复的真相源，日后**两处改一处忘**、易漂移（正是本项目最忌的失败模式）。
- **Q6**（对抗验证 O4 新增）两个下游取舍：**(a) 日后如何合法改 policy？** **(b) `--policy` 输入做轻校验还是深校验？**
  - ➡️ **推荐答案：(a) 本 change 只埋锚点、不造 `policy upgrade` 动词**（动词面刻意不含它，`cli.py:3-7`），
    把「已接入仓改 policy 的正路」立为**后续 change**，本 change 先**承认这个运维缺口**。理由：现在**没有任何正路**——
    `uninit` 会连 caller/台账一起删、动词面无 upgrade ⇒ 改 policy 是个**被默默假设**的死角。
    **(b) 推荐轻校验**（仅要求可解析为 JSON 对象；深 schema 交给 `check` 的 `Policy.from_doc`），
    但在 `init` 输出里**明确警告**「policy 语义合法性由 `check` 兜底，`init` 不保证」。
    例子：(a) 某天要把 `require_change_for` 加一条新 glob——当前只能 `uninit && init --policy`，
    会重建 caller 与台账、产生一次受保护写入，代价与语义都含糊。(b) 传一个
    `{"required_artifacts": "not-a-list"}` 的 policy——轻校验下 `init` 成功、直到 `check` 才炸；
    深校验下 `init` 当场拒。**此点请用户定夺。**

## 风险

- **R1（阻塞级）**：A 的 change 目录**当前缺 `tasks.md`，`specs/dogfood/` 为空**（CRQ1）。设计 D1 把 change 目录当成「默认形状已含 `tasks.md`」，
  但交付/接线点**从未列出创建 `tasks.md`**——这是被默默假设的必需件。且空 `specs/` 目录 git **不跟踪**：
  本地 `check` 可能因目录存在而**误绿**，CI 新检出时目录消失 ⇒ `specs` 缺失 `_fail`（「本地绿、CI 红」陷阱）。
  **先补 `tasks.md` + `specs/<cap>/spec.md` 再跑证据链。**
- **R2（高）**：`init --policy` 的「已初始化后给不同 policy」现码是**静默 no-op**（CRQ2）——比报错更坑：退出码 0、
  无任何输出暗示 policy 被忽略，用户会以为定制生效。实现必须显式加比较分支（否则 §5 测试「已初始化后给不同 policy → 冲突」必红）。
- **R3**：设计里的 `文件:行号` 引用**不精确**——D1 引 `manifestcmd.py:98`（`_fail` 更早 `:72-75` 就拒，
  `_check_hashes` 侧在 `contract.py:379-383`）；D2 引 `initcmd.py:94`（`default_policy_doc()` 实为 `:46`，
  无定制通道的证据在 `:44-48` 与 `cli.py:39-47`）。下游检查器若按行号解析会错位，建议校正。
  （**本报告自身**已按对抗验证第 1 条把 `:47` 校正为 `:46`。）
- **R4**：**bootstrap 必须用源码版 witnessloop。** `--policy` 未随 `@v1` 发布（CRQ3：v1=`843b691` 无此选项），
  `uv tool install …@v1` 跑 `init --policy` 会失败。release 侧：`--policy` 要等**新 tag** 才对公众可用；
  本仓 caller 仍钉 `gate.yml@v1`（check 读**数据** policy，不受影响，故本仓门禁不必升 tag）。
- **R5**：A **自己**的 PR 即便触发 caller，因 required check 未勾选而**不被拦**——诚实前提，须文档写明（与 Q2 呼应）。
  另一面：caller 解析 `gate.yml@v1` 需要该 tag 存在——**已验证 `v1` tag 存在**（带注释 tag 对象 `19ac94c` → commit `843b691`），故 A 合并后门禁可解析、不死链。
- **R6**：文档/代码改动可能触**漂移守卫**测试——`tests/test_docs.py` 把「动词面」表述与 run-id 措辞**钉成测试**
  （`VERB_SURFACE_DOCS`、`RUN_ID_DOCS`、`Q3_DOCS`、`IDEMPOTENCY_DOCS`）。爆点面**不止** `README.md`/`docs/gate.md`：
  A 设计 §6 还要改 **`src/witnessloop/cli.py`**（加 `--policy` help）与 **`docs/design.md`**——二者都在守卫名单里
  （`RUN_ID_DOCS` 含 `cli.py`；`VERB_SURFACE_DOCS`/`RUN_ID_DOCS`/`IDEMPOTENCY_DOCS` 含 `docs/design.md`，
  `tests/test_docs.py:18,51,97,114`）。任一改动若碰掉被钉的措辞（如「确定性」字样），CI 红（`tests/**` 属内容提交）。
  设计 §6「文档影响」未提示这一点。
- **R7**：现状表里 **GitHub 侧断言**（`gh pr list` 为空、`main` protection 404）无法从仓内核实，本审阅**只读仓**只能验证
  CI 面（`ci.yml`、`gate.yml`）。建议实现期用 `gh` 实仓复核一次；若与实际不符，D5 的前提要重述。
- **R8（静默假设）**：change 目录必须在**整条 PR 的生命周期**里持续存在且完整。`check` 从**每次 diff** 推 change id
  （`contract.py:58-86`）；任何中间态（如先提交 change 目录、后补 `tasks.md`）都会让该中间 revision 的 `check` 红。
  两段提交约定（先内容、后证据）必须**在 change 目录已完整**之后才开始。

---

来源（Q/D5 的 GitHub 事实）：GitHub Docs, *Events that trigger workflows → `pull_request`*（workflow 定义取自 PR head/merge ref，运行于合成 merge commit；`pull_request_target` 才锁 base）— <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>。

---

## User Confirmation

> 停轮结算：用户在对抗验证收敛（2 轮 PASS）后**一次性**确认，答复口径「**按推荐**」（2026-10-11）。

- **Q1**: 用户答复：纳入本 change（A）——`init --policy` 与契约采纳同批落地，不拆 A0；确认时间: 2026-10-11
- **Q2**: 用户答复：接受 A 自己只能本地 check（bootstrap 靠自觉一次），文档须写明「A 之后才机械强制」；确认时间: 2026-10-11
- **Q3**: 用户答复：同时开「禁止直接 push（require PR）」+ required check；确认时间: 2026-10-11
- **Q4**: 用户答复：**不加** `templates/**` 到 `protected_paths`，`templates/**`/`plugin/**` 只进 `require_change_for`；确认时间: 2026-10-11
- **Q5**: 用户答复：定制 policy 源文件**不入库**，`.witnessloop/policy.json` 为唯一权威 policy；确认时间: 2026-10-11
- **Q6**: 用户答复：(a) 本 change **只埋锚点、不造 `policy upgrade` 动词**，改 policy 的正路立为**后续 change**；(b) `--policy` **轻校验**（仅要求可解析为 JSON 对象），深 schema 交给 `check`；确认时间: 2026-10-11
