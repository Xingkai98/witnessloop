# Grill-Adversarial: dogfood-bootstrap 设计阶段对抗验证

> 独立零记忆审阅者产出。算法与 verdict 语义依据 `templates/grill.md` **第 5 步**
> （「设计阶段对抗验证 loop」）：**默认上面的结论有错**，逐条去**证伪** Confirmed
> Decisions 与 Open Questions，能实测/复现的就去实测。
> 本文件只做**对抗验证**——不改设计、不停轮、不整合 `design.md`。

## Reviewer

- run id: `grill-adversarial-reviewer-dogfood-bootstrap-2026-10-11`
- 时间: 2026-10-11T06:37:07Z
- 被审材料: `reviews/grill-review.md`（run `grill-reviewer-dogfood-bootstrap-2026-10-11`）
- 只读核验方式: Read 源码 + `git`/`find`/`grep` 实测（未改任何仓内文件，未用它途写入）

## Verdict

**CHANGES_REQUESTED**

六条 Confirmed Decisions 与六条 Code-Resolved Questions 的**核心结论我只证伪出「非核心」层**：
`specs/` 硬要求（D1）、`init` 无定制通道（D2）、不变集新增免解释（D3-a）、A 自身 diff 预期绿
（D3-b）、`pull_request` 取 head 侧（D5）、手改 policy 打破台账（D2 台账）、以及最关键的
**「已初始化后再 `init --policy` 是静默 no-op」**（CRQ-B）与 **「不会自锁」**（CRQ-E）
——这些**实质结论我逐条实测，全部成立，未被推翻**。

但**必须补**的项有四条（前三条是「结论对但引用/口径不准或夸大」，第四条是真实遗漏的守卫）：

1. **R3 的「行号校正」本身引错了行号**：`default_policy_doc()` 在 `initcmd.py:46`，
   不是 `:47`。R3 的任务就是校正行号，却引入了一个新的错行号（D2 亦同）。
2. **CRQ-C / R5 的 sha 引用不准**：`v1` 是**带注释 tag**，`git rev-parse v1` = `19ac94c`
   （tag 对象），其指向的 commit 才是 `843b691`（=`main`）。文中把「`git rev-parse main v1`
   = `843b691`」当成命令输出写出，与实际输出不符（该命令对 v1 打印的是 tag 对象）。
3. **D3-a 标题口径夸大**：「`.witnessloop/**` 的新增免解释」**不成立**——免解释只对
   **不变集那 4 条 patterns** 生效，不是整个 `.witnessloop/**`。A 恰好只新增其中两个文件
   才没事；换一个 `.witnessloop/extra.json` 就要事件。结论对 A 成立，但**口径错了**。
4. **R6 漏了 A 会直接踩到的守卫**：R6 只点名 `README.md`/`docs/gate.md`，但设计 §6 里
   A 还要改 `src/witnessloop/cli.py` 与 `docs/design.md`——**这两者都在漂移守卫名单里**
   （`RUN_ID_DOCS` 含 `cli.py`；`VERB_SURFACE_DOCS`/`RUN_ID_DOCS`/`IDEMPOTENCY_DOCS` 含
   `docs/design.md`）。A 改 `cli.py`（加 `--policy` help）时就可能踩红 CI。

核心结论不被推翻，故不是「必须推翻」；但上述四条是**必须补/必须改**的，故 **CHANGES_REQUESTED**。

## 逐条对抗

> 裁定档：**证伪**（实质结论错）/ **部分成立**（结论对，引用或口径不准/夸大）/
> **成立**（实测复核通过，未发现可推翻点）。

### Confirmed Decisions

#### D1 —— `specs/` 是 `manifest build` 硬要求，policy 改不掉
- **被证伪断言**：「`HASHED_ARTIFACTS` 常量含 `("spec_hash","specs")`/`("tasks_hash","tasks.md")`；
  build 对该表逐项 `_fail`；删 `required_artifacts` 里的 `specs` 只影响 `check` 目录存在性与
  build 先跑的契约判定」。
- **裁定：成立（但枚举不全，见「遗漏」O1）**。
- **证据**（实测复核）：
  - `HASHED_ARTIFACTS`（`src/witnessloop/constants.py:55-58`）= `(("tasks_hash","tasks.md"),("spec_hash","specs"))` ✓；
    与断言行号一致，且 `manifestcmd.py:96-100` 对该表逐项 `if not target.exists(): return _fail(...)` ✓。
  - 该循环**不读** `policy.required_artifacts`（`manifestcmd.py:96-100` 只引用 `C.HASHED_ARTIFACTS`）✓。
  - `required_artifacts` 只喂 `contract.validate_change_dir`（`contract.py:97-99`）与 build 先跑的契约判定
    （`manifestcmd.py:72-75`）✓。
  - 「改 policy 绕开」确是伪出路 ✓。

#### D2 —— `init` 确无 policy 定制通道
- **被证伪断言**：「`desired_files(gate_ref)` 只吃 `gate_ref`，内部写死 `default_policy_doc()`
  （`initcmd.py:44-48`，**落点 `:47`**）；`cli.py` 的 `init` 只挂 `--root`/`--dry-run`/`--gate-ref`」。
- **裁定：部分成立**——**实质成立，落点行号错**。
- **证据**：
  - `def desired_files(gate_ref)` 在 `initcmd.py:44`，`return {` 在 `:45`，**`default_policy_doc()`
    在 `:46`**，`caller_workflow(gate_ref)` 在 `:47`（`src/witnessloop/initcmd.py:44-48`，实测
    `grep -n "default_policy_doc" src/witnessloop/initcmd.py` → `46:...default_policy_doc()...`）。
    文中（D2 与 R3）两处都写成 `:47`，**均错一行**。
  - `cli.py` init 子命令无 `--policy`：确证（`src/witnessloop/cli.py:39-47`）✓。
  - 「补 `--policy` 是对真缺口的补」✓。

#### D3-a —— `.witnessloop/**` 的「新增」免解释（即使也在 protected_paths）
- **被证伪断言**：「**`.witnessloop/**`** 的『新增』免解释属实」。
- **裁定：部分成立（标题夸大）**——对 A 的**具体两个文件**成立，作为**类**不成立。
- **证据**：
  - 免解释只在 `if by_invariant and status[:1]=="A": continue`（`src/witnessloop/checkcmd.py:157-158`）
    **且** `by_invariant = matches_any(path, INVARIANT_PROTECTED_PATHS)`（`:154`）。
  - 不变集只有 4 条：`.witnessloop/policy.json`、`.witnessloop/init-manifest.json`、
    `**/workflow-events.jsonl`、`**/reviews/*.manifest.json`（`src/witnessloop/policy.py:18-23`）。
    **不是 `.witnessloop/**`**。
  - 默认 `protected_paths` 里的 `.witnessloop/**`（`policy.py:35-37`）只让 `by_policy=True`；
    若新增的是 `.witnessloop/extra.json`（只命中 by_policy、不命中不变集），
    `:157` 的 continue **不触发** ⇒ 仍需解释事件。∴ 标题口径错，A 之所以没事是因为它新增的
    恰是那两个**具名不变集文件**。
  - 「不变集含那两份文件、且默认 protected_paths 也收 `.witnessloop/**`」本身 ✓
    （`policy.py:18-23`、`:35-37`）。

#### D3-b —— A 自身 diff 预期绿、无需任何解释事件
- **被证伪断言**：逐类分类 = `src/**`(M，命中 require_change_for 但 change 目录在)/`.witnessloop/**`(A 免)/
  `.github/workflows/witnessloop.yml`(普通)/`openspec/changes/**`(普通，其 manifest 属不变集且 A 免)/
  `docs/**` 与 `tests/**`(不在 require_change_for)。
- **裁定：成立（前提 change 目录补齐，见 CRQ-A/R1）**。
- **证据**：
  - protected 匹配是**前缀锚定**：`glob_to_regex` 以 `re.match(... + r"\Z")` 锚定（`src/witnessloop/paths.py:49,53`），
    故默认 `openspec/specs/**`（`policy.py:36`）**不**命中 A 的
    `openspec/changes/dogfood-bootstrap/specs/dogfood/spec.md` ⇒ 该 spec 非受保护 ✓（这是 A 能免事件的关键，实测复核）。
  - `.github/workflows/witnessloop.yml` 不命中 protected/不变集 ⇒ 普通 ✓；`docs/**`、`tests/**`
    不在 `DEFAULT_REQUIRE_CHANGE_FOR`（`constants.py:27-36`）✓。
  - `_require_change` 在 `change_ids` 非空时**提前返回**（`checkcmd.py:90`）⇒ `src/**` 的 M 不改写结论 ✓。
  - 事件文件缺失不报错：`events.load_all` 用 `root.glob(...)` 收集（`events.py:72-77`），无文件→空表 ✓。

#### D5 —— `pull_request` 取 PR head（merge ref）侧 workflow，`pull_request_target` 才锁 base
- **裁定：成立**。
- **证据**：GitHub 官方事件语义（`pull_request` 用 PR head/合成 merge commit 的 workflow 定义；
  `pull_request_target` 锁 base）。仓内旁证：本仓 `gate.yml` 自身注释也钉「`pull_request` 默认检出
  test-merge commit」（`.github/workflows/gate.yml:35-38`），与结论一致。

#### D2 台账 —— 手改 `.witnessloop/policy.json` 打破台账
- **裁定：成立**。
- **证据**：`uninit` 逐文件比 `sha256_bytes(path.read_bytes()) != entry["sha256"]`（`src/witnessloop/uninitcmd.py:58-61`），
  不等即进 `conflicts` 并整批拒删（`:71-87`）✓；重跑 `init` 比 disk-vs-台账 hash（`initcmd.py:153-168`）报「被改动过」✓。

### Code-Resolved Questions

#### CRQ-A —— A 的 change 目录现在合契约吗？
- **裁定：成立**。
- **证据（实测）**：`find openspec/changes/dogfood-bootstrap -type f` 现为
  `design.md`、`proposal.md`、`reviews/grill-review.md`；`specs/dogfood/` 为**空目录**
  （`find` 显示 `specs/dogfood` 存在但无文件）。`required_artifacts` 缺 `tasks.md`
  ⇒ `validate_change_dir`（`contract.py:97-99`）经 `manifestcmd.py:72-75` `_fail`；
  即使绕过，`HASHED_ARTIFACTS` 循环亦因 `tasks.md` 缺失 `_fail`（`manifestcmd.py:96-100`）。
  ⇒ 先补 `tasks.md` + `specs/<cap>/spec.md` ✓。
- **注**：文中「`find -type f` 只有 `proposal.md`、`design.md`」在**当时**为真（其自身报告尚未落盘）；
  现含 `reviews/grill-review.md`。属时点差异，不影响结论。

#### CRQ-B —— 已初始化后再 `init --policy <不同>` 的行为
- **被证伪断言**（针对设计 D2 的「报 diff 拒绝」）：现状其实是**静默 no-op（exit 0『幂等』）**。
- **裁定：成立，且是本审阅最有价值的一条**。
- **证据（逐行复现）**：
  - `run` 一见 `init-manifest.json` 存在即早返 `_already_initialized`（`src/witnessloop/initcmd.py:97-98`），
    **跳过** run 里那段 disk-vs-desired 的 `conflicts` 检查（`:100-111` 因此对已接入仓永不执行）。
  - `_already_initialized` 只比 **磁盘 vs 台账 hash**（`:144-154`），**从不比磁盘 vs `desired`**；
    `desired` 只在 drift 时用于**渲染** diff（`:154, :165`）。
  - ⇒ 传入不同的 `--policy`、而磁盘 policy 未被手改时，判「无 drift」→ 打印
    「init：已接入 witnessloop（幂等，无改动）。」并 `EXIT_PASS`（`:170-171`）——**用户 policy 被静默忽略**。
  - ⇒ 要兑现 D2/§5 的「冲突」承诺，**必须新增**比较分支（desired-vs-台账 或 desired-vs-磁盘）✓。

#### CRQ-C —— 本仓已发布的 `@v1` 里有 `--policy` 吗？
- **被证伪断言**：「`git rev-parse main v1` = `843b691`（早于 HEAD `6aa9821`）」。
- **裁定：部分成立**——**实质成立，sha 引用不准**。
- **证据（实测）**：
  - `git rev-parse main v1 HEAD` → `main=843b691`、**`v1=19ac94c`（tag 对象）**、`HEAD=6aa9821`；
     `git rev-parse v1^{}` → `843b691`（带注释 tag 解开后的 commit，**恰等于 `main`**）。
    ∴ 把「`git rev-parse main v1` = `843b691`」当命令输出写出与实际不符（该命令对 v1 打印 `19ac94c`）——
    应为 `git rev-parse v1^{}`。
  - **实质**：`git show v1:src/witnessloop/cli.py` 无 `--policy`（只有 docstring 里的「policy upgrade」字样）；
    `v1:src/witnessloop/initcmd.py` 的 `desired_files` 同现状 ✓。⇒「`@v1` 无 `--policy`，bootstrap 必须
    跑源码/本地构建」成立 ✓。

#### CRQ-D —— `check` 怎样定位 change id、怎样判报告？
- **裁定：成立**。
- **证据**：change id 取 `changes_root/<首段>`（`contract.changed_change_ids`，`contract.py:82-86`）✓；
  report 必须落在 `reviews/` 下（build 守卫 `manifestcmd.py:84-90`）✓；孤儿规则 `contract.py:184-218` ✓；
  ⇒ A 产出 N 份报告就须 N 份 manifest ✓。

#### CRQ-E —— 本 change 会不会死锁 / 误伤自己？（**重点核对**）
- **被证伪断言**：「**不会自锁**」。
- **裁定：成立**——我按「上游流程变量 / 边界 / check 其他分支」逐面找自锁，**未找到**。
- **证据与反证尝试**：
  - A 新增 `templates/**`、`plugin/**` 到 `require_change_for`，而 A 自身 diff **不含**这两处
    （`git diff --name-status main..HEAD` 仅 `proposal.md`/`design.md`；设计 §3 接线点亦无 templates/plugin）
    ⇒ 不自我触发 ✓。
  - A 改 `src/**` 命中 require_change_for，但 A 的 change 目录在 ⇒ 满足（`checkcmd.py:90` 提前返回）✓。
  - A 新增 `.witnessloop/policy.json`/`init-manifest.json` 走不变集新增档 ⇒ 免解释（`checkcmd.py:154-158`）✓。
  - **我另试的自锁面（均不成立）**：
    (a) A 的 `openspec/changes/**/specs/**` 会不会被默认 `openspec/specs/**` 误命中？**否**——
        匹配前缀锚定（`paths.py:49,53`），实测不命中。
    (b) 两段提交（内容①/证据②，D4）会不会让 A 的 `head_sha` 判 stale？**否**——② 只增
        `openspec/changes/*/reviews/**`，落在 `stale_exempt_paths`（`policy.py:64-79`），delta 里无 stray。
    (c) 事件文件缺失会不会 `_fail`？**否**——`events.load_all` 空表（`events.py:72-77`）。
    (d) 归档/改名分支（`is_archive_move`、old_path）？A 无 rename ✓。
  - 「唯一鸡生蛋 = A 自己不被机械拦，D5 已诚实记」——**成立且必要**（见 R5）。故「不会自锁」站得住。

#### CRQ-F —— 现状表「零 PR / main 无保护」能在仓内核实吗？
- **裁定：成立**。
- **证据**：`ci.yml` 只 `pytest`+打包、on push/PR（`.github/workflows/ci.yml:10-33`）✓；
  `gate.yml` 仅 `on: workflow_call`（`.github/workflows/gate.yml:11-12`）✓；「零 PR/protection 404」
  确属外部状态，须 `gh` 实仓核 ✓。

## 遗漏的重要事实

- **O1（补强 D1）**：删 `required_artifacts` 里的 `specs` **并非只影响那两处**——`check` 的
  `_check_hashes` 也**硬性**要求 `specs` 存在（`contract.py:379-383`：`target=directory/"specs"`，
  `if not target.exists(): findings.append("specs 不存在，无法校验 spec_hash")`）。即：删 `required_artifacts`
  既救不了 build，也救不了 check。D1 的枚举把这条漏了（**方向上更强化 D1**，非推翻）。
- **O2（R6 的实质缺口，必须补）**：漂移守卫不只罩 `README.md`/`docs/gate.md`。A 设计 §6 还要改
  **`src/witnessloop/cli.py`**（加 `--policy`）与 **`docs/design.md`**——二者都在守卫名单里：
  `RUN_ID_DOCS` 含 `src/witnessloop/cli.py`（`tests/test_docs.py:51-61`）、`Q3_DOCS`/`IDEMPOTENCY_DOCS`
  亦含它（`:97-101,114`）；`VERB_SURFACE_DOCS`/`RUN_ID_DOCS`/`IDEMPOTENCY_DOCS` 含 `docs/design.md`
  （`:18,51,114`）。⇒ A 改 `cli.py` help 文案时若不保留「确定性」字样等，`test_docs.py` 会红（CI 属内容提交）。
  R6 只提 README/gate.md，**低估了爆点面**。
- **O3（上游流程变量）**：`manifest build` 的 run id 兜底走 `agentenv.resolve_run_id`，取
  `WITNESSLOOP_{REVIEWER,AUTHOR}_RUN_ID → WITNESSLOOP_RUN_ID → 确定性锚`（`cli.py:89-101,116-127`）。
  A 产出三份 manifest 时，`grill-adversarial` 那份的 `reviewer_run_id` **必须 ≠** `author_run_id`
  且不得等于 `grill` 那份的作者——否则 `manifest build` 直接拒（`manifestcmd.py:122-127`）。
  grill-review 的 CRQ-D 只讲了「N 报告 ⇒ N manifest」，**漏了「三份 manifest 之间的身份字段取值」**这条流程变量。
- **O4（Q5 的下游）**：CRQ-B 修好（desired-vs-台账 冲突）之后，**已接入仓没有任何**「换 policy」的
  正路——`uninit` 会连 caller/台账一起删、动词面又刻意不含 `policy upgrade`（`cli.py:3-7`）。
  这条既不进 grill-review 的 Q5、也不进设计 §8，是**被默默假设**的运维缺口（应升级为一个 Open Question）。

## 对抗结论

对 5 条 Open Questions 的**推荐答案方向**再判断（默认它们选错，逐条找反例）：

- **Q1（`--policy` 纳入 A 还是拆 A0）：方向对，但反方未充分展开。** 「拆 A0 会让 `templates/**`/`plugin/**`
  无覆盖、正是要堵的洞」——证据链成立（默认 `require_change_for` 确不含二者，`constants.py:27-36`）。
  可补的反方：A0 独立可**先把 `--policy` 的 tested 面单独钉死**，再看 A 一次集成；但净收益确不如合并。
  **裁定：采纳（非阻塞）。**
- **Q2（接受 bootstrap 靠自觉一次）：方向对。** 鸡生蛋在同 change 内不可消除（CRQ-E 复核确认自锁面不存在，
  只剩这一条），文档写明即可。**采纳。**
- **Q3（require PR + required check 同时开）：方向对且必要。** 只勾 required check 不禁直推，
  `git push origin main` 直接绕过（与设计 §4 风险 5 同款）——成立。**采纳。**
- **Q4（`templates/**` 是否进 protected_paths）：方向对（不进）。** 反方（与已受保护的
  `openspec/specs/**` 同性质）已诚实列出并交用户。**采纳，保留用户定夺。**
- **Q5（policy seed 是否入库）：方向对，但漏了 O4。** 「不单独入库、`.witnessloop/policy.json` 为唯一权威」
  成立；但**未回答**「日后如何合法改 policy」（O4）。**部分采纳**——须补一个 Open Question（见上）。
- **漏掉的 Open Question**：设计 D2 边界把 `--policy` 定为「**轻校验**（JSON 对象），深 schema 校验留给
  check 的 `Policy.from_doc`」。这是**用户可见的取舍**（交一个语义非法的 policy 会让 `init` 成功、`check` 才炸），
  却既不在 grill-review 的 5 条 Open Questions、也不在原设计 §8。**建议新增为 Open Question**。

**一句话**：核心结论（硬要求、静默 no-op、不会自锁）都经我实测复核、**未被推翻**；但 R3 的行号校正自摆乌龙
（`:47`→`:46`）、CRQ-C 的 v1 sha 引用不实（tag 对象 vs commit）、D3-a 口径夸大、R6 漏 `cli.py`/`docs/design.md`
两个必踩守卫——**故 CHANGES_REQUESTED（必须补，非推翻）**。

---

## 第 2 轮对抗验证

> 独立零记忆审阅者（再另起一个 run）产出。默认第 1 轮修订**有错**，逐条实测证伪。
> 算法与 verdict 语义依据 `templates/grill.md` 第 5 步。本文件只做对抗验证——不整合 `design.md`、不停轮。

- 时间: 2026-10-11T06:39:40Z
- 裁定: **PASS**
- 只读核验方式: Read 源码 + `grep`/`find`/`git rev-parse`/`git show` 实测；仓内源码自 `HEAD` **未再改动**
  （`git status --porcelain` 仅 `?? openspec/changes/dogfood-bootstrap/reviews/`），故第 1 轮已复核的行号继续有效。

### 逐条核验（4 条必改 + 4 条遗漏）

**必改 1 —— `default_policy_doc()` `:47`→`:46`（D2 与 R3 两处）：已落实。**
实测 `grep -n default_policy_doc src/witnessloop/initcmd.py` → `46:...policy.default_policy_doc()...`；
`sed -n '44,48p'` 确认 `def desired_files`=44、`return {`=45、policy 行=**46**、`caller_workflow`=47。
D2（`grill-review.md:25`）写「落点 `:46`」，R3（`:132`）写「实为 `:46`」，**两处均正确**。
全报告无残留指向 `default_policy_doc` 的 `:47`（`:134` 的 `:47` 是「原值已被校正」的元陈述，非事实引用）。

**必改 2 —— `v1` tag 的 sha 引用（CRQ-C 与 R5 两处）：已落实。**
实测 `git rev-parse v1` = `19ac94c2…` 且 `git cat-file -t v1` = `tag`（**带注释 tag 对象**）；
`git rev-parse v1^{}` = `843b691d…`（= `git rev-parse main`）；`HEAD` = `6aa98215…`。
CRQ-C（`:63-64`）与 R5（`:139`）均正确写成「tag 对象 `19ac94c` → commit `843b691`」，未再把 tag 对象当 commit。
旁证：`git for-each-ref refs/tags/v1` → `tag 19ac94c -> 843b691`。

**必改 3 —— D3-a 口径收正（免解释只对不变集 4 条 patterns，非整个 `.witnessloop/**`）：已落实。**
实测 `INVARIANT_PROTECTED_PATHS` 恰 **4 条**（`policy.py:18-23`：`policy.json`／`init-manifest.json`／
`**/workflow-events.jsonl`／`**/reviews/*.manifest.json`）；免解释 gate = `if by_invariant and status[:1]=="A": continue`
（`checkcmd.py:154` 定义 `by_invariant`、`:157-158` continue）；默认 `protected_paths` 里的 `.witnessloop/**`
（`policy.py:35-37`）只令 `by_policy=True`。D3-a（`grill-review.md:28-35`）表述与源码一致，
并明确「新增一个 `.witnessloop/extra.json` 仍要解释事件」——标题不再夸大。

**必改 4 —— R6 爆点面补 `src/witnessloop/cli.py` 与 `docs/design.md`：已落实。**
实测 `tests/test_docs.py`：`VERB_SURFACE_DOCS`=18、`RUN_ID_DOCS`=51（含 `docs/design.md`=52、`src/witnessloop/cli.py`=60）、
`Q3_DOCS`=97、`IDEMPOTENCY_DOCS`=114；R6（`grill-review.md:140-144`）已点名二者并引 `:18,51,97,114`，对位准确。
另核 `design.md` §6：第 84 行确列 `src/witnessloop/cli.py`、第 109 行确列 `docs/design.md` ⇒ 「A 要改这两处」属实。

**遗漏 O1 —— `_check_hashes` 也硬要求 `specs`：已落实（并入 D1）。**
实测 `contract.py:379-383`：`for field, artifact in C.HASHED_ARTIFACTS:`（379）→ `target = directory / artifact`（380）→
`if not target.exists(): findings.append(Finding(manifest_rel, f"{artifact} 不存在，无法校验 {field}"))`（381-382）。
D1（`grill-review.md:21-22`）已写入此条（`src/witnessloop/contract.py:379-383`）。

**遗漏 O2 —— 即 R6：已落实**（同「必改 4」，R6 现覆盖 `cli.py`/`docs/design.md`）。

**遗漏 O3 —— 三份 manifest 的身份字段取值：已落实（并入 CRQ-D）。**
实测 `manifestcmd.py:122`：`if reviewer_run_id == author_run_id:` → `:123-127` `return _fail("…审阅者必须独立于作者…")`。
CRQ-D（`grill-review.md:73-74`）已写「每份 manifest 内 `reviewer_run_id != author_run_id` 是硬拒（`manifestcmd.py:122-127`）；
确定性兜底 id 含 `stage` ⇒ 三份天然互异」。

**遗漏 O4 —— 合法改 policy + `--policy` 轻/深校验取舍：已落实（立为 Q6）。**
Q6（`grill-review.md:112-121`）齐备两问：**(a)** 日后如何合法改 policy（推荐本 change 只埋锚点、`policy upgrade` 立为后续 change）；
**(b)** `--policy` 轻校验 vs 深校验（推荐轻校验 + init 输出警告）。与 O4 建议一致。

### 新问题
**未发现。** 额外证伪两处易错点，均成立：
- CRQ-C/R4 的实质「`@v1` 无 `--policy`」：`git show v1:src/witnessloop/cli.py` 中唯一 `policy` 字面量在 docstring
  （「其余动词…policy upgrade 刻意不存在」），`init` 子命令**无** `--policy`；`v1:src/witnessloop/initcmd.py` 的
  `desired_files(gate_ref)`（`:44`）与 `default_policy_doc()`（`:46`）同现状 ⇒ 「bootstrap 必须跑源码版」成立。
- D3-b 与收正后的 D3-a 不冲突：A 在 `.witnessloop/` 下**只**新增那两个具名不变集文件，故 D3-b 的
  「`.witnessloop/**`（A，不变集免解释）」对 A 成立。

### 结论
第 1 轮 4 条必改与 4 条遗漏**全部落实且经实测复现正确**，未引入新问题，核心结论（`specs/` 硬要求、
`init --policy` 静默 no-op、不会自锁）继续成立——**PASS**。
