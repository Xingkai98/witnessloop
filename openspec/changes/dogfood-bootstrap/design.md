# Design: dogfood-bootstrap（witnessloop 自举接入）

> 状态：**设计已收敛**（grill + 设计阶段对抗验证 2 轮 → PASS），待用户停轮确认。
> 依据 `proposal.md`。流程出处见 `templates/grill.md`。
> 审阅证据：`reviews/grill-review.md`（决策记录）、`reviews/grill-adversarial.md`（对抗验证，含 R2）。

## 0. 一句话

给 witnessloop **自己的仓**接上它自己的门禁：落 `.witnessloop/` + `openspec/changes/` 契约，
并补上接入所必需的 `init --policy` 通道——本 change 自己就是契约下的第一个 change。

## 1. 现状（实测，非推断）

| 事实 | 证据 |
|---|---|
| 无 `.witnessloop/` | 目录不存在 |
| CI 不跑门禁 | `ci.yml` 只有 pytest + 打包冒烟 |
| gate 不自触发 | `gate.yml` 仅 `on: workflow_call` |
| 零 PR | `gh pr list --state all` → `[]` |
| main 无保护 | `gh api .../branches/main/protection` → 404；rulesets `[]` |

（`gh` 两项属外部状态，实现期用 `gh` 实仓复核一次——审阅者 R7。）

## 2. 决策

### D1 采用 v1 硬编码的 change 契约（含 `specs/` 与 `tasks.md`）

本仓的 change 目录用默认形状：`openspec/changes/<id>/{proposal,design,tasks}.md` + `specs/` + `reviews/`。

- **为什么必须含 `specs/` 与 `tasks.md`**：`manifest build` 对 `constants.HASHED_ARTIFACTS`
  （含 `("tasks_hash","tasks.md")`、`("spec_hash","specs")`，`src/witnessloop/constants.py:55-58`）**逐项**
  `if not target.exists(): return _fail(...)`（`manifestcmd.py:96-100`）；`check` 的 `_check_hashes` **同样**硬要求
  `specs` 存在（`contract.py:379-383`）。这条路径**不读** `policy.required_artifacts`。
- **「改 policy 绕开」是双重的伪出路**：删 `required_artifacts` 里的 `specs` 只影响 `check` 的目录存在性判定
  （`contract.py:97-100`）与 build 先跑的契约判定（`manifestcmd.py:72-75`），**既救不了 build、也救不了 `check`**。
- **witnessloop 没有 spec 层，怎么凑？** 不凑——本 change 的 `specs/dogfood/spec.md` 写一条**真实能力要求**
  （「本仓自身仓库的改动受 change 契约与证据门禁约束」）。
- **⚠️ R1（阻塞）**：change 目录**必须全程完整**（含 `tasks.md` + 真实 `specs/<cap>/spec.md`）。
  空 `specs/` 目录 **git 不跟踪** ⇒ 本地可能因目录存在而**误绿**、CI 新检出时目录消失而红（「本地绿、CI 红」陷阱）。
  **两段提交约定必须在 change 目录补齐之后才开始**。
- **代价（诚实记）**：这暴露 v1 对「无 spec 层仓库」的接入摩擦（本仓自己就是第一个受害者）。修它属**另一个 change**。

### D2 `init` 增加 policy 定制通道（`--policy <file>`）

**缺口**：`init` 只写 `policy.default_policy_doc()`（`initcmd.py:44-48`，落点 `:46`），**无任何定制通道**
（`cli.py:39-47` 只挂 `--root`/`--dry-run`/`--gate-ref`）。默认 `require_change_for`（`constants.py:27-36`）
**不含 `templates/**`、`plugin/**`**——对 witnessloop 是**真空**：只改交互层（不碰 `src/`）的 PR 会绕过
「必须挂 change 目录」。手改 `.witnessloop/policy.json` 又会与 `init-manifest` 台账 hash 不符
⇒ `uninit` 整批拒删（`uninitcmd.py:58-61,71-87`）、重跑 `init` 报「被改动过」（`initcmd.py:153-168`）。

- **决策**：`init --policy <file>` ——用给定文件的内容作为 desired policy（替换默认），其余不变
  （仍幂等 / 只增不改 / 不 auto-commit / `--dry-run`）。
- **为什么不「先 init 再手改」**：那会对 `.witnessloop/policy.json`（不变集）产生**修改**，按 `gate.md §5`
  需写解释事件，且台账失真。`--policy` 让 policy **一次写成正确内容**（「新增」）⇒ 天然免解释、台账自洽、`uninit` 可用。
- **⚠️ R2（高，设计原稿在此处说错，已修正）**：**现状**下「已初始化后再 `init --policy <不同>`」**不是**报冲突，
  而是**静默 no-op（exit 0「幂等」）**——`run` 一见 `init-manifest.json` 存在即早返 `_already_initialized`
  （`initcmd.py:97-98`），后者只比**磁盘 vs 台账 hash**（`:144-154`）、**从不比磁盘 vs `desired`**，
  用户的 policy 被**悄悄忽略**。⇒ 实现**必须新增**比较分支（desired-vs-台账 或 desired-vs-磁盘）才兑现「冲突」承诺。
- **备选**：(β) init 采纳「已存在的 policy.json」为 desired（隐式、与「只增不改」打架）；(γ) 接受默认 policy
  留已知绕过洞；(δ) 手搓一致的 init-manifest（伪造台账）。**均否。**
- **边界**：`--policy` 文件须可解析为 JSON **对象**（**轻校验**；深 schema 留给 `check` 的 `Policy.from_doc`，
  见 Q6）；文件缺失/非法 → 报错**不写任何文件**；与 `--dry-run` 组合照常。

### D3 A 自身的 diff 与门禁自洽

- **含 `src/**` 改动**（`init --policy` 的 CLI/实现）→ 触发 `require_change_for` → **必须挂 change 目录** ✓。
- **`.witnessloop/**` 免解释的只是那两份具名不变集文件**（口径已收正，对抗验证第 3 条）：
  免解释 gate 是 `by_invariant and status[:1]=="A"`（`checkcmd.py:154-158`），而 `by_invariant` 只匹配
  **不变集 4 条 patterns**（`policy.py:18-23`）——含 `.witnessloop/policy.json`、`.witnessloop/init-manifest.json`。
  默认 `protected_paths` 的 `.witnessloop/**`（`policy.py:35-37`）**不**给免解释：新增 `.witnessloop/extra.json`
  仍要事件。A 之所以免，是因为它新增的**恰是那两个具名文件**。
- **`.github/workflows/witnessloop.yml`** 既不在 `protected_paths` 也不在不变集 → 普通文件 ✓。
- `openspec/changes/**/specs/**` **不**被默认 `openspec/specs/**` 误命中（前缀锚定，`paths.py:49,53`）⇒ 非受保护 ✓。
- ⇒ A 的 `check` 预期**绿**，无需任何解释事件（前提：change 目录补齐，见 D1/R1）。

### D4 change-id / 分支 / 提交约定 / manifest 身份

- change-id `dogfood-bootstrap`；分支 `dogfood-bootstrap/2026-10-11`。
- witnessloop **没有**「分支名推 change-id」的约定；`check` 从 **diff** 推 change id（`changed_change_ids` 取路径首段，
  `contract.py:82-86`）。分支命名仍按纪律，但**非门禁依赖**。
- **两段提交**（`gate.md §3.1`）：①内容（change 目录 + init 产物 + `--policy` 代码）②证据（`reviews/` 报告 + manifest）。
  `head_sha` 指①，被检 head 指②。
- **三份报告 ⇒ 三份 manifest**（`grill-review.md`/`grill-adversarial.md`/`building-review.md` 各配一份；
  「跑一次绑一份、另一份晾着」会被判**孤儿**，`contract.py:184-218`）。每份 manifest 内
  `reviewer_run_id != author_run_id` 是**硬拒**（`manifestcmd.py:122-127`）；确定性兜底 id 含 `stage` ⇒ 三份天然互异。

### D5 PR + required check（merge boundary）

- A 之后，本仓开发**改走 PR**；`main` 开 branch protection：required check = witnessloop gate。
- **GitHub 侧已定案**（对抗验证）：`pull_request` 事件取 **PR head/merge ref** 侧的 workflow 文件（`pull_request_target`
  才锁 base）⇒ A 合并进 `main` 后，任何以 `main` 为 base 的 PR 都会带上 `main` 的 caller 而触发。
- **鸡生蛋**：A 的 caller workflow 随 A 才落 `main`，且 required check 未勾选 ⇒ **A 自己只能本地 `check`，
  bootstrap 靠自觉一次**。A 之后才有机械强制。（诚实前提，文档须写明。）
- **⚠️ `--policy` 未随 `@v1` 发布**（tag `v1` → commit `843b691` 无此选项）⇒ bootstrap 必须跑**源码版**
  `uv run witnessloop …`，不能 `uv tool install …@v1`。caller 仍钉 `gate.yml@v1`（`check` 读**数据** policy，不受影响）。
- **需用户手工一次**：开 branch protection（人肉那一签，design §4 / §9 风险 3）。

## 3. 接线点（实现清单）

- **新增 change 必需件（R1 阻塞项，先做）**：`openspec/changes/dogfood-bootstrap/tasks.md`
  + `openspec/changes/dogfood-bootstrap/specs/dogfood/spec.md`。
- `src/witnessloop/cli.py`：`init` 子命令加 `--policy`（**注意**：该文件在漂移守卫名单里，见 §6）。
- `src/witnessloop/initcmd.py`：`desired_files` 接受外部 policy 文本；`run` 读取校验 `--policy`；
  **新增**「已初始化后 desired 不同 ⇒ 冲突」分支（D2 R2）。
- `.witnessloop/policy.json`（本仓）：默认 + `require_change_for` 补 `templates/**`、`plugin/**`。
- `.github/workflows/witnessloop.yml`：init 产出的 caller。
- `README.md` / `docs/gate.md` / `docs/design.md` / `docs/tasks.md`：文档同步。

## 4. 风险

1. **R1（阻塞）**：change 目录缺 `tasks.md` / 空 `specs/` ⇒ build/check 当场拒；空目录 git 不跟踪 ⇒ 本地误绿、CI 红。
2. **R2（高）**：`init --policy` 在已接入仓现状是**静默 no-op**；实现必须显式加比较分支。
3. **R3**：设计原稿行号引用不精确，已按对抗验证校正（`:46`、`contract.py:379-383` 等）。
4. **R4**：bootstrap 必须用**源码版** witnessloop；`--policy` 要等**新 tag** 才对公众可用。
5. **R5**：A 自己不被机械拦（required check 未勾选）——诚实前提，文档写明。
6. **R6**：漂移守卫 `tests/test_docs.py` 罩住 `README.md`、`docs/gate.md`、**`src/witnessloop/cli.py`**、**`docs/design.md`**
   （`VERB_SURFACE_DOCS`/`RUN_ID_DOCS`/`Q3_DOCS`/`IDEMPOTENCY_DOCS`）。改这些文件若碰掉被钉的措辞（如「确定性」字样），
   CI 红（`tests/**` 属内容提交）。**设计 §6 原稿低估了爆点面。**
7. **R7**：`gh` 两项现状断言无法从仓内核实，实现期实仓复核。
8. **R8**：change 目录必须在**整条 PR 生命周期**里持续完整；两段提交须在补齐后才开始。
9. **R9（诚实边界）**：本 change **不修**「写代码前的设计 grill 本地无执行体」——那是 #7 的 B 轨；也不修「报告正文校验」——那是本仓 #2。

## 5. 测试策略

- **单测（TDD）**：`init --policy` —— 指定内容落盘且与台账一致；幂等；`uninit` 往返；非法 JSON / 非对象 /
  路径逃逸 → 拒且不写；与 `--dry-run` 组合；**已初始化后给不同 policy → 冲突**（⚠️ 现状是 no-op，
  这条测试会先红，正是 R2 的驱动）。
- **端到端（本仓）**：A 自己的 change 目录 + 两段提交 + `manifest build` × 3 + `check` 绿。
- **负例**：改 `.witnessloop/policy.json` 不写事件 → `check` 拦；删某份 manifest → `check` 拦（孤儿/缺失）。

## 6. 文档影响

- `README.md`：加「本仓自身接入（dogfood）」+ `init --policy` 用法。
- `docs/gate.md`：加 `init --policy` 一节。
- `docs/design.md`：状态/§10 更新；§9 风险 4「强制只在 CI」**不变**（B 轨才改）。
- `docs/tasks.md`：追加 G 段（本 change 任务）。
- **⚠️ 上述文件（含 `cli.py`）在 `tests/test_docs.py` 漂移守卫名单里**（见 R6），改文案须同步测试。

## 7. Pre-Implementation Review

**已确认决策（grill 证伪后确认 · 来源 `grill-reviewer-dogfood-bootstrap-2026-10-11`）**：
D1（`specs`/`tasks.md` 是 build+check 硬要求、policy 救不了，且是**双重**伪出路）、D2（`init` 无定制通道、
手改破台账）、D3（A 自身预期绿、无需解释事件）、D5（`pull_request` 取 head 侧）、D2-台账。

**必须修改（已整合，来源对抗验证 `grill-adversarial-reviewer-dogfood-bootstrap-2026-10-11`）**：
- 行号校正（`default_policy_doc()` `:46`；`v1` = tag 对象 `19ac94c` → commit `843b691`）。
- D3-a 口径收正：免解释只对**不变集 4 条**，不是整个 `.witnessloop/**`。
- R6 爆点面补 `cli.py` + `docs/design.md`。
- D1 补 `_check_hashes`（`contract.py:379-383`）；D4 补三份 manifest 的身份字段约束。
- **新增 Q6**（policy 变更正路 + 轻/深校验取舍）——原设计与被 grill 版本都漏了。
- **修正 D2 的实体错误**：已接入后 `init --policy` 现状是**静默 no-op**，非「报冲突」。

**Code-Resolved 结论**：A 的 change 目录当时不合契约（缺 `tasks.md`、`specs/` 空）⇒ 先补（R1）；
`@v1` 无 `--policy` ⇒ 用源码版（R4）；本 change **不会自锁**（对抗验证另试 4 条自锁面均不成立）。

**用户确认**：Q1–Q6 **全按推荐**（2026-10-11）；逐条答复见 `reviews/grill-review.md` 的 `## User Confirmation`。

## 8. Open Questions（停轮待用户确认）

- **Q1** `init --policy` 纳入本 change，还是拆成独立 change（A0）？
- **Q2** A 自己只能本地 check（bootstrap 靠自觉一次）——可接受？
- **Q3** `main` 是否**同时**开「禁止直接 push（require PR）」，还是先只加 required check？
- **Q4** witnessloop 的 `protected_paths` 要不要加 `templates/**`（视交互层为受保护 artifact）？
- **Q5** A 的定制 policy **源文件**是否入库、放哪？
- **Q6** 两个下游取舍：**(a) 日后如何合法改 policy？** **(b) `--policy` 输入轻校验还是深校验？**

（每条的具体例子与推荐答案见 `reviews/grill-review.md` 的 `## Open Questions`。）
