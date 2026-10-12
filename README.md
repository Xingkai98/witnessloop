# witnessloop

把「agent 驱动的软件开发流程」做成**独立于任何代码仓、可复用于任意仓库**的工具。

流程：**设计先行 → 设计对抗式追问（grill）→ 实现 → 独立审阅闭环**，全程由**机械门禁 + 证据绑定**强制——而不是靠模型自觉。

> **状态：MVP 完成**（M1 门禁层 + M2 交互层 + M3 第二仓 acid test 全绿）。
> 动词面 = 3 个门禁动词（`init` / `uninit` / `check`，fail-closed）
> + 1 个证据产出动词（`manifest build`）；
> 交互层是 Claude Code plugin（`grill` / `review-loop`，只接线、只读、无状态）。
> 全流程已在**第二个真实仓**端到端跑通（`init → change → grill`（设计阶段对抗验证收敛）
> `→ 用户确认 → TDD → review-loop → check 绿`），见
> [docs/reviews/m3-acid-test.md](docs/reviews/m3-acid-test.md)。
> 设计见 [docs/design.md](docs/design.md)，任务见 [docs/tasks.md](docs/tasks.md)，
> 门禁层数据契约见 [docs/gate.md](docs/gate.md)；已知待办见仓库 Issues。

## 用法

```bash
uv tool install git+https://github.com/Xingkai98/witnessloop@v1

# 接入目标仓：幂等、只增不改、不 auto-commit
cd your-repo && witnessloop init --dry-run   # 先看要写什么
witnessloop init                             # 落盘，然后**人工审阅并提交**
witnessloop init --policy /path/to/policy.json   # 需要非默认 policy 时（见下「本仓自身接入」）

# 审阅跑完，落证据（复用 check 同一套哈希；幂等、不 auto-commit）
witnessloop manifest build --change add-retry --stage building \
  --report reviews/building-review.md \
  --reviewer-run-id run-A --author-run-id run-B

# CI 入口（fail-closed）
witnessloop check --base origin/main --head HEAD

# 本地守卫：写目标命中 require_change_for 且缺 grill 证据 → 拦（CLI 退 1；host shim 再映射成 CC 的 2）
# 通常由 host 的 PreToolUse hook 自动调（见下），也可手动/脚本调
witnessloop guard --path src/x.py

# 精确回滚（文件被改过就拒绝删除并报 diff）
witnessloop uninit
```

交互层（`grill` / `review-loop`）是一个 Claude Code plugin，**只做接线**——
算法在 host 中立的 `templates/` 下，适配器在 `plugin/` 下，两者物理分离：

```bash
claude --plugin-dir /path/to/witnessloop/plugin
```

分发按设计走 **git / 本地目录，不上 marketplace**（design §4）。

### 本仓自身接入（dogfood）

witnessloop **自己也走这套流程**：本仓有 `.witnessloop/policy.json`，非平凡改动落在
`openspec/changes/<id>/` 下、内容与证据分离提交，PR 由 required check 拦。本仓的
`require_change_for` 比出厂默认多收 `templates/**`、`plugin/**`（交互层也是产品面）。

本仓**需要定制 policy**，所以接入用 `init --policy <seed>` 一次写成（seed 是仓外的临时
文件、**不入库**；`.witnessloop/policy.json` 是唯一权威）——这样 policy 是「新增」而非
「修改」，免解释事件、台账自洽、`uninit` 可回滚。

> **诚实前提**：**接入本身**只能靠**本地** `witnessloop check` + 人工 review 兜一次——
> 因为它才引入 caller workflow、`main` 的 required check 那时尚未勾选；**接入之后**的 PR
> 才被机械拦。这是自举的固有鸡生蛋，不是遗漏。
>
> 另：`init --policy` 是接入期新增的动词选项，**尚未随 `@v1` 发布**——自己接入时跑源码版
> （`uv run witnessloop …`），公众要等**新 tag**。

### policy（`.witnessloop/policy.json`，住在目标仓、可评审）

`init` 写一份默认 policy。要定制就用 `init --policy <file>` **一次写成**（事后手改会打破
init-manifest 台账、`uninit` 拒删，见 [docs/gate.md §1.1](docs/gate.md)）：

- `protected_paths`：写入需结构化解释事件（默认 `openspec/specs/**`、`.witnessloop/**`）。
- `require_change_for`：命中这些 glob 的改动**必须**挂一个 change 目录。默认覆盖常见
  源码目录（`src/**`、`lib/**`、`app/**`、`apps/**`、`packages/**`、`server/**`、
  `cmd/**`、`internal/**`），**不含** `docs/**`、`tests/**`。没有它，绕过门禁最省事的
  办法是什么都不建——只改 `src/` 的 PR 会直接放行。写 `[]` 可显式关掉。
- `required_artifacts` / `evidence`：change 目录必须齐备的件、证据文件名与事件格式。

归档（把 change 从 active `git mv` 进 `openspec/changes/archive/`）属簿记动作，
**不需要**手写解释事件；删改证据文件仍然要。边界见
[docs/gate.md §5.1](docs/gate.md)。

`init` 写的 caller workflow 引用本仓的 reusable workflow
`.github/workflows/gate.yml@v1`——记得在目标仓 branch protection 里把那个 job
勾成 required，否则门禁不会真的拦人（那一次人肉操作就是 v1 的「人类签名」）。

> **前置条件：本仓必须公开。** caller 引用的是本仓的 reusable workflow、CI 里用
> `uvx --from git+…@v1` 安装本包——两者在**私有**仓下都会失败（reusable workflow
> 访问级别默认 `none`；私有包安装报 `could not read Username`）。已实测，见
> [docs/design.md §4.1](docs/design.md)。私有接入需额外配 token，不在 v1 范围。

### 本地守卫与行为变更

交互层带一个 **PreToolUse 本地守卫**：`Write|Edit` 之前调 `witnessloop guard`——当前 change 的
grill 证据不完备就不许写代码路径（**写文档豁免**，否则永远产不出证据）。它与 `check` **共用同一个**
判定。装 plugin 时**同时要装 CLI**，否则命令找不到、守卫静默失效（fail-open）。

它是「**防遗忘**」不是防对抗：**用 Bash 写文件**（`matcher` 只覆盖 `Write|Edit`）**或不装 plugin
即绕过**。真正的锚仍是 CI required check。

⚠️ **对**接入方**是行为变更**：`check` 现在要求每个 change 有一个 **`stage=grill`** 的 manifest，
且该报告正文合格（`Confirmed Decisions` ≥3 且每条带 `来源:`、`Open Questions` 都经用户确认）——
**此前没有这道校验**；历史 change 若缺 `stage=grill` manifest 会**新增一条红**。详见
[docs/gate.md §8](docs/gate.md)。

⚠️ **对**接入方**还有两条行为变更**（`building` 门禁）：**改了代码**（触及 `policy.require_change_for`）的 PR
现在**必须**有一份 `stage=building` 的审阅证据（= 跑过 review-loop），**否则红**；
且**一个 PR 同时触及多个 change**（只要它触及了代码）时，**每个** change 都要 building 证据（要免除就把 change 拆到单独 PR）。
**注意**：这道门只保证「**闭环跑过 + 审在最终 revision 上**」——**报告里的 verdict 文本不参与判定**，
`PASS` / `CHANGES_REQUESTED` 都能过（§9 有完整口径）。

### 能力边界（别被「机械可验证」误导）

默认**只防漂移，不防蓄意伪造**：hash 绑定能证明证据之间没漂移，
但 `reviewer_run_id` / `approved_by` 是自由文本——agent 手写一行放行事件
就能过。这是设计就承认的边界，不是 bug。真正的锚是远端 branch protection
+ required check。详见 [docs/gate.md §7](docs/gate.md)。

## 为什么

Agent 写代码最大的风险不是「不会写」，而是「**不可信**」：跳过设计、自评通过、审阅走过场、证据只存在于对话里——不可提交、不可审计、不可复现。

witnessloop 要解决的是这个：把「可信」变成**机械可验证**的东西。

## 核心理念

- **独立见证**：每个审阅者都是零记忆的独立 agent，不审自己的活，不共享上下文。
- **证据绑定**：每次门禁通过都绑定可审计证据（审阅者 run id、base/head sha、artifact hash），而不是一句手写的 `PASS`。
- **循环收敛**：设计与实现各走一轮「审阅 → 修复 → 再审」，有界轮数封顶。
- **门禁落 merge boundary**：强制放在 CI required check。交互层另有一层**本地守卫**（写码前缺 grill 证据就拦），但它是「**防遗忘**」不是防对抗——用 Bash 写文件、或不装 plugin 就能绕过，**真正的锚仍是 CI**。

## 名字

`witness`（独立见证者）+ `loop`（审阅/追问的循环）。每一个审阅环都是一个零记忆的 witness。
