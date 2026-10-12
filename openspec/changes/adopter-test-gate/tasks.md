# Tasks: adopter-test-gate

> 依据 `design.md`（**已按 grill + 对抗验证 R1 回写**：原稿 5 处事实被 grill 证伪、4 条阻塞被对抗轮证伪，
> 见 design §7 与 §7bis）。原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/adopter-test-job/spec.md`）。
> ⚠️ **Q1 定案前，A 节的形态不确定**（己=模板+文档／己+增量①②③（推荐）／甲=`gate.yml` 加 input）——
> 定案后**必须**先把 `spec.md` 的对应段落替换成定案（spec 是 manifest 哈希绑定的 artifact）。
> ⚠️ **定案后必须删掉未选分支**（否则「A 改 gate.yml」与「D2 gate.yml 不在 diff 里」会以两条互斥验收
> 同时留在同一份 tasks 里——对抗轮 CRQ-J 点名过这条）。

## A. 交付物本体（依 Q1 定案）

- [ ] A1 **己（推荐）**：新增测试 workflow 模板 `templates/github/adopter-tests.yml`（**位置依 Q11 定案**；
      ⚠️ **不要**直接放 `templates/` 根——那里契约定的是 **host 中立**，且 `tests/test_templates.py` 的
      fixture 只覆盖两个 `.md` ⇒ 新文件会自动豁免三条检查，**要把它纳入 fixture**）：
      - **① 模板必须区分「未声明」与「占位符没填」**：占位符**未替换 ⇒ `::error::` + exit 1**；
        显式空 ⇒ 跳过 + `::notice::`（这是 D1 与 D4 之间原本没闭合的缺口，R19）
      - 命令经 **`env:`** 传入（**不**裸内联进 `run:`）
      - 非空 ⇒ **回显实际执行的命令**（Q7）
      - 文件头注释：**这是你的文件，随便改**；**不要**去手改 `witnessloop init` 写的 caller（死锁）
- [ ] A2 **甲（备选）**：`gate.yml` 新增 `workflow_call.inputs.test-command`（`required: false`、`default: ""`）
      + 测试步骤；**必须同时**：① 台账记 `test_command`（照 `gate_ref` 的 recall 先例 `initcmd.py:131-141,:163`）
      ② 定 D5（**新 tag**，不是移动 `v1`）③ 按 D2 钉死**失败交互**（`check` 失败时测试跑不跑、是否 `if: always()`）
- [ ] A3 **②（依 Q13 定案）**：`check` 在「仓里除 caller 外没有任何 workflow」时打一行 `::notice::`
      ——**零依赖**（列 `.github/workflows/*` 即可，**不解析 YAML**）、**非 finding、不改退出码**。
      ⚠️ **必须配一条测试**（N8）：notice **只**在该条件成立时出现，且**退出码与 findings 都不变**
- [ ] A4 单测（先红）：模板用 **pyyaml 结构化断言**（先例与理由见 `tests/test_gate_workflow.py:32-34`）——
      三态各一条：**占位符未替换 ⇒ `::error::` + 非零**、显式空 ⇒ `::notice::`、非空 ⇒ 回显命令且走 `env:`
      （**断言限定到新增内容**，见 R16/CRQ-I：现有 `gate.yml:57-58` 就有裸 `${{ }}`）
- [ ] A5 `init` 输出补一行「测试执行点见 …」（N3①；⚠️ 只改 stdout、**不改任何生成物**——见 B3）
- [ ] A6 **`caller_workflow()` 逐字节稳定**：新增一条 **golden literal** 测试（CRQ-J-1）
      ——生成物是已接入仓的**实际契约**（台账 sha 绑着它），`tests/test_init.py:46-55` 现在只有子串断言，
      钉不住「加一行头注释」（而实测：加一行头注释会让存量仓 `init` 立刻坏）
- [ ] A7 **依赖不变**（N3②）：新增一条测试钉 `pyproject.toml` 的 `dependencies == []`
      （或断言 wheel 的 METADATA 无 `Requires-Dist`）——`spec.md` 有这条 Requirement 而 `tests/` 里**零落点**

## B. 存量接入方可达性（**R11：原稿没走到的节点**）

- [ ] B1 把「**存量接入方怎么拿到执行点**」写成**显式交付物**，且配方必须给
      **可达 ref + 一条可直接执行的获取命令**（N1）：⚠️ `@v1` 上**没有**这个新文件，照直觉去 `@v1` 取会 **404**
      （ref 策略依 Q12 定案）
- [ ] B2 文档**必须**写清「手改 `init` 产物 = 死锁」（三条**文件级**出口照 design D3-① 如实写：
      恢复字节 / 删掉该文件 / 改台账 sha 仅对 `uninit` 有效；**「删台账」既不必要也不充分**——
      对抗轮 B3 证伪了原稿的「唯一恢复路径」）
- [ ] B3 文档**必须**写清「**不要**用 `uninit → init` 升级」（会删掉台账里**每一个**条目含 `policy.json`
      ⇒ **静默丢定制 policy**，本仓自己就是受害者）
- [ ] B4 校验「本 change 不改 `caller_workflow()` 的字节」——**判据**（N9）：在 `DEFAULT_GATE_REF`
      **未变**的前提下，A6 的 golden literal 逐字节相等（即「不改生成物」这件事由 A6 的测试直接体现）
- [ ] B5 ~~戊（种子文件）~~ —— **对抗轮 B2 已从推荐删除**（与 spec 冲突 / 只省一次 `cp` / 会种下永远绿的
      no-op check）。**若用户仍要**：走 `init --with-tests` **显式 opt-in** + 种子必须是「占位符未替换 ⇒ 红」版本
      + 改三文件契约（`docs/gate.md:9`、`tests/test_init.py:18,72,103`）+ spec delta 显式记

## C. 边界与告警（D9 / Q5 / Q7 / B-1）

- [ ] C1 `README.md` 写**三条告警**：① 测试命令是**任意代码**，会在每个 PR（含 **fork PR**）执行；
      ② **PR 可以改自己的 CI**（`.github/workflows/**` 不在保护路径、`required_approving_review_count: 0`）
      ⇒ 承诺**限定为**「在本次 PR 未修改自己 CI 配置的前提下」；③ **本 change 是零机械强制**
      （不拷、不勾，什么都不会发生）——**不得**以机械门禁之名说得像有强制力
- [ ] C2 可选加固写进文档（不强制）：把 `.github/workflows/**` 纳入 `CODEOWNERS`
- [ ] C3 钉住两条**文档类 Requirement**（N4；范式见 `tests/test_docs.py:test_every_idempotency_claim_is_scoped_or_qualified`
      与 `test_docs_no_longer_call_hooks_advisory_only`）：
      ① 每处「拦住合并」都要带限定（±2 行窗口）；② 文档里**不出现**「手改 init 产物」/「先 uninit 再 init」的教法；
      ③ README 的接入段**必须出现**「零机械强制」字样（N10：`spec.md` 要求交付物自述这一点，
      否则会漂——与 N4 同族，但 N4 只覆盖了限定词与两条死路）
- [ ] C4 `check` / `guard` 的**判定逻辑**零改动：由既有 `tests/test_guard.py` 全绿 + 「本 change 的 diff
      **不含** `src/witnessloop/{guardcmd,contract,policy,evidence}.py` 的判定逻辑」保证
      （⚠️ **`checkcmd.py` 允许改动**——增量 ② 要在那里加一行非阻塞 notice；见 A3）。
      **不**用「`gate.yml` 逐字节不变」那种反模式断言（CRQ-J-2）

## D. 回归

- [ ] D1 全量 `uv run pytest -q` 绿（记录基线与新增数）
- [ ] D2 **回归检查项**：本 change 的 diff **不含** `.github/workflows/gate.yml` + 本仓 caller 仍引 `@v1`
      （⚠️ 写成检查项而非「快照断言」——`gate.yml` 是要演进的 workflow，钉死它等于禁止未来合法修改）
- [ ] D3 `templates/review-loop.md`：补一句「测试须由 CI 执行（见模板）」——⚠️ **只在本仓内为真**：
      对 `@v1` 接入方，这份模板改了也不会生效（N1）
- [ ] D4 **本仓自举（N6/R21，依 Q10 定案）**：把 `ci.yml` 的 `test` job 勾成 required（**人工一步**，
      写成本 change 的交付项）——否则本 change 自己的 PR 可以带着红测试合入

## E. 文档

- [ ] E1 `README.md`：接入段补「测试执行点怎么拿」「三态语义」「required 是**人工勾一次**（job 粒度）」
      + **写清哪条规则在哪个 ref 上生效**（B1：`@v1` 的 CLI 没有 #13/#16 的新门禁）
- [ ] E2 `docs/gate.md`：§7（能力边界补 D9）、新增一小节（本能力的语义与边界）
- [ ] E3 `docs/design.md`：§5.1 的 caller 契约（仅甲才需要改）
- [ ] E4 ⚠️ **不改** `openspec/changes/` 下**其他** change 目录的非证据文件（会让其 manifest 判 stale）

## F. 证据链与收尾

- [ ] **F0** 停轮拿到 Q1..Q13 答复 → 定案替换进 `spec.md` → **删掉未选分支**（A2）→ 写 `## User Confirmation` →
      `manifest build --stage grill` 放行 `src/**` →（**F0b**）**重跑一轮设计对抗**
- [ ] F1（在 build 证据**之后**执行）两段提交 + `manifest build`（grill / grill-adversarial / building）
      + **本地** `uv run witnessloop check` 绿
      ⚠️ **区分两件事**（B1）：**本地 check 跑的是 main 的代码**（会执行三份 manifest 的要求）；
      **CI 的 `gate / check` 跑的是 `@v1` 的 CLI**（**不**含这些新门禁）⇒ **不得**在 PR 正文或文档里
      写「本 PR 由三份 manifest 门禁拦住」
- [ ] F2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] F3（在 `check` 绿**之后**执行）PR → 合入（**优先 `--merge`**，见 issue #18）
- [ ] F4 **issue #4 的收口（依 Q9 定案）**：⚠️ **不得**用「零机械强制」的交付物直接关掉一个明确要**机械机制**的 issue
      ⇒ 推荐：**关 #4 时另开一条「机械执行点」issue**（承接 #4 原文的两条机械建议），
      或保持 #4 open 并只补完成说明（本 change 覆盖了哪一部分、哪一部分没有）

## 明确不做（本 change）

让 `check` 跑测试 · 测试命令**探测** · 手改 `init` 产物（死锁）· 「uninit→init」式升级（会丢 policy）·
**戊（种子文件，已按对抗轮 B2 删除）** · 改本仓 `ci.yml` 的**内容** · 引入运行时依赖 ·
替接入方勾 required · **顺手移动 `v1` tag**（R12）· 给 `gate.yml` 加「逐字节不变」的快照断言（CRQ-J-2）。

## 实测记录（实现期）

（待填）
