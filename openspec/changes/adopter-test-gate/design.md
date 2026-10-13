# Design: adopter-test-gate（v2 · 机械版）

> 状态：**草稿 v2**（方向反转，见 `proposal.md`「为什么反转」）。待 grill + 对抗验证收敛 → 停轮。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。
> 前两轮的决策记录（v1 的「模板路线」）保留在 `reviews/grill-review.md` / `reviews/grill-adversarial.md`
> ——**它们证伪的事实仍然有效**（尤其那批实测），被推翻的只是**方案选择**。

## 0. 一句话

**`init` 把测试执行点写进去，门禁跑它，`check` 机械地要求它存在且已接线**——
因为「没有存量接入方」这条约束不成立，v1 那个「只给文档、零强制」的收敛没有理由了。

## 1. 现状（实测 · 沿用 v1 稿的复核结论）

| 事实 | 证据 |
|---|---|
| caller 极薄且被台账管理 | `initcmd.py:24-40`、`initcmd.py:79-96`；`init`/`uninit` 都比对台账 |
| **没有任何外部接入方**（v2 的新前提，已核实） | `gh search code --owner Xingkai98 witnessloop` **空**；唯一的「已接入」是 `wl-test`（用户自己的 acid test 仓、私有、可删）+ 本仓自己（dogfood） |
| **本仓自己的门禁跑的是 6 个提交前的 CLI** | `.github/workflows/witnessloop.yml:14` 引 `@v1`；`gate.yml:19-23` 的 `witnessloop-ref` 默认 `v1`；实测同一 diff「v1 报 1 条 / main 报 4 条」 |
| `gate.yml` 自 `v1` 起**从未改过** | `git log --oneline v1..origin/main -- .github/workflows/gate.yml` = 空 |
| **`v1` 自称「滚动大版本」** | `git tag -n99 v1` →「witnessloop v1（滚动大版本，当前指向 v1.5.0）」 |
| 零运行时依赖 | `pyproject.toml` `dependencies = []`（wheel 无 `Requires-Dist`） |
| **「只写三个文件」是被钉住的契约** | `docs/gate.md:9`、`tests/test_init.py:18,72,103` |
| **手改 `init` 产物 = 死锁** | 实测：`init`/`uninit`/`--dry-run`/`--policy`/`--gate-ref` **全 exit 1**；文件级出口有三条（恢复字节 / 删掉该文件 / 改台账 sha 仅对 `uninit` 有效），「删台账」既不必要也不充分 |
| **`uninit → init` 会丢定制 policy** | `uninitcmd.py:91-95` 删台账里**每一个**条目（含 `policy.json`） |
| 保护面 | `.witnessloop/**` 与 `openspec/specs/**`（本仓 policy 实测）；`.github/**` **不在**两者 ⇒ 放命令文件不需解释事件 |
| required 粒度 = **job** | `gh api …/protection` ⇒ `contexts = ["gate / check"]` |
| 本仓 `test` job **不是** required | 同上 ⇒ 本仓**可带红测试合入** |

## 2. 决策

### D1 执行点**写在哪**（机械）—— **Q1**

| | 要动 `gate.yml` 吗 | 需要新增人工步骤吗 | 命令能自由改吗 | 契约成本 |
|---|---|---|---|---|
| **甲（推荐）**：`init` 写一个**命令文件**（`.github/witnessloop-tests.txt`，`init --test-command` 代填）+ **`gate.yml` 新增一步读它并执行** | 是（⇒ 必须发版，见 D5） | **否**（测试与 `check` **同 job** ⇒ 复用已 required 的 `gate / check`） | **能**（该文件**不进台账**，是接入方自己的） | 小（多一个产物 ⇒ 改「三文件」表述） |
| **乙**：`init` 另写一个**独立测试 workflow** | 否 | 是（新 job 要再勾一次 required） | 能 | 破「三文件」契约较深（`tests/test_init.py:18,72,103`） |
| **丙**：命令进 **caller 的 `with:`**（`gate.yml` 加 input） | 是 | 否 | **不能**：caller 在台账里 ⇒ 改命令撞死锁 | caller 契约变更 |

- **推荐甲**：同时拿到「零新增人工步骤」与「命令可自由改」，且**不引入 `workflow_call` 的 input 声明耦合**
  ——命令是**运行时从检出出来的仓里读**的（runner 自带 `bash`/`cat`），所以**没有「未声明 input ⇒ startup_failure」那类风险**。
- **否丙**：caller 是台账文件，「改命令」会撞上实测的死锁（`init`/`uninit` 双双 exit 1）。
- **甲 vs 乙 的真正差别**是「测试跑在谁的门禁里」：甲塞进**已 required** 的 `gate / check`（零人工步骤）；
  乙是接入方自己的 job（更干净、权限更大——reusable workflow 的权限不能超出 caller，
  见 v1 稿的 R14——但**要再勾一次 required，忘勾就退回「跑了但不拦」**）。

### D2 测试**跑在哪**：与 `check` **同一个 job**（推荐）

- 理由：required 的粒度是 **job**（实测）⇒ 同 job 才能「**零新增平台操作**就拦住」。
- ⚠️ **失败交互（必须钉死，v1 稿的 R13）**：默认 step 语义下 `check` 失败 ⇒ 测试步骤**不执行**
  （门禁红时恰是最想要测试反馈的时候）；`if: always()` 又会让测试的失败**掩蔽** `check` 的失败。
  ⇒ 二选一写进 spec，并给出理由。**推荐**：测试步骤 `if: always()`，且 `check` 步骤排在前、step 名区分。
- 备选：独立 job（失败归因清晰、可要 OIDC 等权限）——但**接入方必须再勾一次 required**。

### D3 命令的载体与「以后怎么改」—— **Q2**

- **推荐**：命令住 `.github/witnessloop-tests.txt`——**不在** `protected_paths`（`.github/**` 两者都不在）、
  **不进台账**（不是 `init` 生成物的 hash 对象；由 `init` **种一次**，之后归接入方）。
  ⇒ 改命令 = 一次普通 commit，**不撞死锁、不需要解释事件**。
- ⚠️ **`init` 种它的语义要写清**（这是 v1 稿里被对抗轮否掉的「戊」的正确形态）：
  文件**不存在才写**、**不进 hash 台账**、**不参与 `uninit` 删除**；内容 = 命令，或（未给命令时）**哨兵占位**。
- 命令**不进 policy**：`.witnessloop/**` 是受保护路径 ⇒ 每次改命令都要写 `protected_path_write` 解释事件。
- 命令**不进 caller**：见 D1 丙。

### D4 **`check` 机械要求「执行点存在且已接线」**（本 change 的核心增量）

`check` SHALL 在**策略声明了执行点**（`policy.tests.execution_point`，`init` 默认写上该路径）时，要求：

1. 该路径的**文件存在**；2. 它**不含未替换的哨兵**（「拷了但没填」⇒ **红**，不是绿）。

- **零依赖**：只做「文件在不在 + 字符串在不在」，**不解析 YAML**、不执行任何命令。
- **为什么不只是打一行 notice**：用户的诉求是「**没有 CI 测试 = 有问题**」⇒ 缺失必须**拦**，不是提醒。
- `init --no-tests`（或不声明执行点）⇒ 显式 opt-out、不判红（无测试仓不被误伤）。
- **诚实边界（必须写进 spec）**：`check` 只能证明「**有一个已接线的执行点**」，证不了「它真跑了」或
  「跑的是不是真测试」（`|| true` / `--collect-only` 都能骗过存在性判定）；「真跑了」由**平台侧 required check** 保证
  （与工具其余部分同一边界）。

### D5 **发版 / ref**（v2 必须一起做）—— **Q3**

- 事实：`init` 写 `@v1`，`gate.yml` 的 `witnessloop-ref` 默认也是 `v1`，而 `v1` 停在 6 个提交前
  ⇒ **本 change 改了 `gate.yml`（D1 甲）之后，接入方与本仓自举都拿不到**。
- **推荐**：**发 `v1.6.0`（含这 6 个提交 + 本 change）并把 `v1` 移到它**——
  `v1` 的注记本就自称「滚动大版本」，这是**恢复 tag 自称的惯例**，不是发明新纪律。
  - 顺带**修好本仓自举**：移动 `v1` 后，本仓 PR 的 `gate / check` 才真正执行 #13/#16 那些新门禁。
  - ⚠️ **风险**：移动 `v1` 会把 CLI 版本一起换（`witnessloop-ref` 默认值就是 `v1`）⇒
    **对 `wl-test`**（唯一存量）意味着它下次 CI 跑新 CLI——它是一次性 acid test 仓，可接受；
    若不想动它，把它的 caller 钉回 `v1.5.0` 即可。
- 备选：新开 tag（`init` 写它）且**不动** `v1`——那么本仓自举**仍然**跑旧 CLI（该洞不修）。

### D6 **`init` 的产物与幂等**（契约影响，必须进 spec）

- 新增产物：**命令文件**（D3）⇒ 必须显式改「只写三个文件」的契约（`docs/gate.md:9`、`tests/test_init.py:18,72,103`），
  并让 `uninit` **不**删它（它是接入方的）。
- 新增 `init --test-command "<cmd>"` 与 `init --no-tests` 两个 flag；**已有的幂等/冲突/回滚语义不许变**。
- ⚠️ **`caller_workflow()` 的字节若变化**（甲**不需要**改 caller ⇒ 最好别碰）：会让本仓自己的 init 台账
  与磁盘不一致（v1 稿的 R17）。

### D7 文档

- `README.md`：接入段（`init --test-command`、命令文件怎么改、**测试与 `check` 同 job ⇒ 不用新增勾选**、
  三条告警：fork PR 会跑你的命令 / **PR 可以改自己的 CI** / **`check` 只保证「执行点存在且已接线」**）。
- `docs/gate.md`：§1（`init` 产物多一个命令文件 ⇒ 改「三个文件」的表述）、新增一小节（执行点门禁的语义与边界）。
- `templates/review-loop.md`：补一句「测试须由 CI 执行」。

### D8 非目标（写进 spec）

不 `check` 跑测试 · 不探测命令 · 不用手改 `init` 产物当通道 · 不引入运行时依赖 · 不替接入方勾 required ·
不改本仓 `ci.yml` 的内容（只建议把它勾成 required，见 Q4）。

## 3. 接线点

- `src/witnessloop/constants.py`：命令文件路径 + 哨兵串常量。
- `src/witnessloop/policy.py`：`tests.execution_point`（默认 = 命令文件路径；显式空/`--no-tests` ⇒ 不判）。
- `src/witnessloop/checkcmd.py`：新判定（存在 + 非哨兵，否则红）。
- `src/witnessloop/initcmd.py`：新产物（种一次、不进台账）+ 两个 flag；`uninitcmd.py`：不删它。
- `.github/workflows/gate.yml`：新 step（读命令文件 ⇒ 经 `env:` 执行；文件不存在 ⇒ 跳过但由 `check` 判红）。
- `tests/`：pyyaml 结构化断言 + `init` 侧用例 + `check` 三态用例。
- 文档（D7）。

## 4. 风险

1. **R1（高 · 发布）**：不动 ref ⇒ 本 change 的功能**到不了接入方**，且本仓自举继续跑旧 CLI ⇒ D5 是硬前置。
2. **R2（中 · 失败交互）**：同 job 下 `check` 失败会**跳过**测试步骤（或 `if: always()` 掩蔽）⇒ 必须钉死一种。
3. **R3（中 · 能力边界）**：`check` 只保证「执行点存在且已接线」，**不保证真跑了**（D4 的诚实边界）。
4. **R4（中 · 台账）**：命令文件若哪天被纳入台账/受保护路径 ⇒ 退回「改命令要写解释事件」或死锁（D3 已规避）。
5. **R5（中 · 平台）**：`.github/workflows/**` 不在保护路径、`required_approving_review_count: 0`
   ⇒ **PR 可以改掉自己的执行点/命令文件**而 required check 依旧绿（既有边界，spec 必须写清，否则**过度承诺**）。
6. **R6（中 · fork PR）**：测试命令是**任意代码**，会在每个 PR（含 fork PR）的 runner 上执行。
7. **R7（低 · 契约）**：新增第四个产物 ⇒ 破「三文件」契约，必须进 spec + 改既有断言。
8. **R8（低 · 迁移）**：`wl-test`（唯一存量、可删）会被移动 `v1` 波及 ⇒ 文档给出「钉回 `v1.5.0`」的规避法。
9. **R9（低 · 自举）**：若本 change 改 `caller_workflow()` 的字节 ⇒ 本仓 init 台账与磁盘不一致（v1 稿的 R17）。

## 5. 测试策略（TDD）

- `init`：命令文件三态（`--test-command` / 无参 ⇒ 哨兵 / `--no-tests`）+ 幂等/冲突/`uninit`（**不删命令文件**）。
- `check`：执行点**缺失 ⇒ 红**、**含哨兵 ⇒ 红**、**已接线 ⇒ 绿**；未声明/`--no-tests` ⇒ 不判。
- `gate.yml`：pyyaml 结构化断言（新 step 存在、命令经 `env:`、文件不存在时跳过）。
- 端到端：真仓 `init --test-command "sh -c 'exit 1'"` ⇒ `check` 绿（执行点在）而**门禁**跑该命令会红。

## 6. 停轮（Q1..Q4 —— 待用户确认）

| # | 问题 | 推荐 |
|---|---|---|
| **Q1** | 执行点写在哪：**甲** 命令文件 + `gate.yml` 读它（同 job、零新增勾选）／乙 独立测试 workflow（要再勾 required）／丙 命令进 caller（撞台账死锁） | **甲** |
| **Q2** | 命令载体：**`.github/witnessloop-tests.txt`**（可自由改）／policy（受保护 ⇒ 每次改要写解释事件）／caller（死锁） | **命令文件** |
| **Q3** | 发版：**发 `v1.6.0` + 移动 `v1`**（顺带修好本仓自举）／新 tag 不动 `v1`（本仓自举仍是旧 CLI） | **发版 + 移动 `v1`** |
| **Q4** | 顺带把**本仓自己的** `ci.yml` `test` job 勾成 required？ | **是**（否则本仓可带红测试合入——#4 的形态在本仓自己身上） |
