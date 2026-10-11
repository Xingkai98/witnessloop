# Design: grill-evidence-gate

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。

## 0. 一句话

把「grill 证据算不算齐」抽成**一个** host-agnostic 判定，接到**两处**：`check`（事后/CI）与
新的 `guard` 动词 + CC hook（事前/本地）。

## 1. 现状（实测）

- `check` 只校验**证据是否成对/绑定**，**不读报告正文**：`contract.validate_review_manifests`
  （`src/witnessloop/contract.py:121-149`）逐 manifest 校验 hash 绑定、`reviewer≠author`、孤儿绑定——
  一个空 `grill-review.md` 只要被 manifest 绑上就过。→ 这就是 **#2**。
- `manifest build` 把 `--stage` 原样写进 manifest（`manifestcmd.py:136`，字段 `stage`），值域**任意**。
- asterwynd 的对应物（可移植的是**谓词**，不是文件）：`scripts/workflow_guard.py:363` `_grill_evidence_missing()`
  （写码前判）+ `scripts/check_openspec_artifacts.py:716-752`（事后判：`## Confirmed Decisions` ≥3 且每条带 `来源:`，
  `## Open Questions` 未确认则不算完成）。
- 本仓已有：`.witnessloop/policy.json`（`require_change_for=[src/**,templates/**,plugin/**]`）、
  branch protection（require PR + required check `gate / check`）、`plugin/` 可分发。

## 2. 决策

### D1 共享 evaluator：新模块 `evidence.py`，**纯函数**

- 形态：`grill_evidence_findings(report_text: str) -> list[Finding]`（输入**文本**，不是路径）
  —— host-agnostic、无 IO、用例密集、`check` 与 `guard` 共用。
- 判定（移植 asterwynd，落到 witnessloop 的措辞）：
  1. 存在 `## Confirmed Decisions`，**≥3 条**，**每条带 `来源:`**；
  2. `## Open Questions` 里**每一条**都要在 `## User Confirmation` 有对应确认记录；占位文本
     （`待确认` / `待主 agent 提交` 等）**不算**确认；
  3. `## User Confirmation` 存在且非空。
- 备选：把判定写进 `contract.py`——否：`contract` 是**门禁契约**，而 evaluator 要被 host 侧的
  `guard` 复用，独立模块边界更干净。

### D2 「grill 报告」怎么定位？

- 候选：(a) 由 manifest 的 `stage`（**保留名** `grill`）定位；(b) 按文件名（`grill-review.md`/`grill-design.md`）；
  (c) policy 配 glob。
- **决策：(a) 为主** —— `stage` 是既有字段、grill 模板已用 `--stage grill`；把 `grill` 定为**保留 stage 名**
  （policy 可选覆写，默认 `grill`）。**不**用文件名（文件名是别的维度，且模板允许 `grill-design.md`/`grill-review.md` 两种叫法）。
- **⚠️ 已知脆弱点**：`--stage` 值域任意 ⇒ 若用户把 stage 拼错（`grills`），判定会**静默失效**（找不到 grill manifest）。
  → 见 D9 与 Open Question Q3。

### D3 `guard` 怎么知道「当前 change」？

- 候选：(a) **分支名** `<change-id>/<date>` 推（本仓分支纪律正是这个形状）；
  (b) env `WITNESSLOOP_CHANGE` 显式覆盖；(c) 取「有未提交改动的 change 目录」。
- **决策：(a) 为主 + (b) 兜底覆盖**。这不是门禁依赖（`guard` 是本地层），不违反「`check` 从 diff 推 change id」。
- **⚠️ 关键取舍（**Open Question Q2**）**：推不出 change id 时（分支不是 `<change-id>/<date>`，如 `hotfix-xxx`）——
  **fail-open（放行 + 提示）还是 fail-closed（拦）**？本地 guard fail-closed 会把所有非 change 分支的开发也堵死；
  fail-open 则「忘切分支」就能绕过。建议 **fail-open + 显式提示**（本地是「防遗忘」不是「防对抗」，见 D8）。

### D4 什么算「写代码」（触发）vs 豁免（写文档）？

- 判据：**触发 = 路径命中 `policy.require_change_for`**（与 `check` **同源同一个 policy 字段**，口径一致）；
  **其余全部豁免**（`docs/**`、`tests/**`、change 目录内的文档 artifact）。
- 为什么必须豁免文档：否则**死锁**——写 `design.md`/`grill-review.md` 时证据尚不存在，一写就被拦，
  永远产不出证据。asterwynd 正是这么做的（文档类写操作豁免，`workflow_guard.py:517-526`）。
- 备选：按「是否在 change 目录内」判豁免——不够：写 `src/` 之外的仓级配置（如 `.github/**`）时语义含糊。

### D5 `guard` 动词的接口（host 中立）

- 形态：`witnessloop guard --root <r> [--path <p>]... [--change <id>]`
  （host 适配器负责从工具事件里抽 path）；也可吃 stdin JSON（见 D6）。
- 退出码：**0 = 放行**；**2 = 拦**（理由到 stderr；2 是「用法」码，这里复用作「被守卫拦住」，
  与 CC hook 的 block 约定一致——见 D6）；**3 = 未接入**（本地不该拦，**放行** + 提示）。
- 备选：只吃 stdin JSON——否：args 形式更易单测、易脚本化、易被非 CC 的宿主调用；stdin 作为可选补充。

### D6 CC hook 怎么分发 / 安装？

- **随 plugin 分发**：`plugin/hooks/hooks.json`（CC plugin 的 hooks 目录）+ 极薄 shim，把 PreToolUse 的
  `Write|Edit`（必要时 `Bash`）事件映射成 `witnessloop guard --path …`。
- **install = 装 plugin**（不再是 asterwynd 的「手动 cp 进 gitignored `.claude/`」——那条路在 worktree 里根本不在场）。
- **⚠️ 待核实（实现期）**：CC plugin hooks 的**确切 schema**（`hooks/hooks.json` 的字段、PreToolUse 的
  matcher 与 stdin 载荷、block 语义是「exit 2」还是 JSON `decision`）。设计只定**方向**，schema 落实现时核实。

### D7 推翻 v1 决策（须显式记录）

- v1（`docs/design.md` §5.1 / §9 风险 4）：**强制落 CI，hooks 只 advisory**。
- 本 change：**hook 也强制**（本地层）。**不破坏**架构——hook 属**交互层**（本就 CC-first、host 特定），
  门禁层仍 host-agnostic（`guard` 动词本身 host 中立，任何宿主都能调）。
- 动作：更新 `docs/design.md` §5.1/§5.2/§9 风险 4 的表述；按仓库规则「偏离已定决策」**须记 ADR**
  （`docs/adr/`；witnessloop 目前无 ADR 目录，需新建一个最小 ADR）。

### D8 escape hatch 与诚实边界

- 需要逃生口：策略误判时不能把人堵死。**决策**：`WITNESSLOOP_SKIP_GUARD=1` 放行，但**打印一行**说明已跳过。
- **诚实边界（写进 README/docs）**：本地 `guard` 是「**防遗忘**」，**不是防对抗**——agent 可以设 env 绕过。
  真正的锚仍是远端 CI required check（`check` 侧的同判据不可绕过）。**不新增能力面，只降话术**。

### D9 `check` 接入 evaluator 的严格度 + 回归

- `check` 对每个 change：要求**存在 `stage=grill` 的 manifest**，且**其报告正文合格**（用 D1 判据）。
- **⚠️ 回归红线**：接上后，本仓既有的 `dogfood-bootstrap` **必须仍绿**。实测其 `grill-review.md` 有
  `## Confirmed Decisions`（6 条、带 `来源:`）与 `## Open Questions`（Q1–Q6）+ 6 条 `## User Confirmation`
  ⇒ 预期合格；若判红则是 evaluator 判据过严，**改判据**（而不是改那份已合入的证据）。
- 向后兼容：历史 change 若没有 `stage=grill` manifest，会**新增一条红**。本仓当前只有 `dogfood-bootstrap`
  （有 grill manifest）⇒ 无影响；对**接入方**是**行为变更**，须在 README/gate.md 写明（属本 change 的验收面）。

## 3. 接线点（实现清单）

- `src/witnessloop/evidence.py`（新）：D1 的纯函数 + Finding 复用 `contract.Finding`。
- `src/witnessloop/guardcmd.py`（新）：D3/D4/D5 的路径分类与 change 解析。
- `src/witnessloop/cli.py`：加 `guard` 子命令；`check` 无需新参数。
- `src/witnessloop/checkcmd.py`：change 循环里接入 evaluator（D9）。
- `plugin/hooks/hooks.json` + shim（D6，schema 实现期核实）。
- `docs/gate.md` / `README.md` / `docs/design.md` + **新 ADR**（D7）。

## 4. 风险

1. **本地 guard 可被绕过**（env / 不装 plugin）→ 文档降话术（D8），锚仍是 CI。
2. **stage 拼错 ⇒ evaluator 静默失效**（D2 脆弱点）→ 见 Q3。
3. **CC plugin hooks schema 未经核实** → 实现期核实，否则 `plugin/hooks/` 画不出来。
4. **误拦开发**：触发面（`require_change_for`）过宽会把非 change 场景堵死 → D3 的 fail-open 取舍。
5. **回归**：evaluator 判据若过严会咬到本仓/接入方的已有 change → D9 红线。
6. **死锁**：D4 的文档豁免若漏了某类路径，会卡住证据产出本身（asterwynd 踩过：文档写操作必须豁免）。

## 5. 测试策略

- **单测（TDD）**：
  - `evidence.grill_evidence_findings`：合格样本 / `<3 条 Confirmed Decisions` / 缺 `来源:` /
    `Open Questions` 未确认 / 占位文本（`待确认`）/ 缺节。
  - `guard`：命中 `require_change_for` 且缺证据 → 拦（exit 2）；证据齐 → 放；写文档 → 放；
    推不出 change id → 按 Q2 的定论；未接入 → 放行 + 提示；`WITNESSLOOP_SKIP_GUARD=1` → 放行 + 留痕。
- **端到端**：`check` 对「正文不合格」红；**回归**：本仓 `dogfood-bootstrap` 仍绿。
- **plugin**：hook 配置存在且指向 `guard`（能在测试里校验 JSON schema，若能核实 CC 格式）。

## 6. 文档影响

- `docs/design.md`：§5.1/§5.2/§9 风险 4（D7）+ §10。
- `docs/gate.md`：`guard` 动词 + `check` 新增正文校验（**接入方行为变更**）。
- `README.md`：本地 guard 用法 + 「装 plugin 即装 hook」+ 诚实边界（D8）。
- **新 ADR**：`docs/adr/0001-local-guard-hook.md`（D7 的决策记录）。
- ⚠️ `tests/test_docs.py` 漂移守卫（`VERB_SURFACE_DOCS` / `RUN_ID_DOCS` / `IDEMPOTENCY_DOCS` 含
  `README.md` / `docs/design.md` / `cli.py`）——改文案须同步。

## 7. Pre-Implementation Review

（待 grill + 对抗验证收敛后填写。）

## 8. Open Questions（停轮候选，待 grill 收敛后定稿）

- **Q1** scope：本 change = `check` 正文校验（#2）+ `guard`+hook（B 轨），**还是拆成两个 change**？
- **Q2** `guard` 推不出 change id 时，**fail-open（放行 + 提示）还是 fail-closed（拦）**？
- **Q3** 「grill 报告」定位用**保留 stage 名** `grill`，还是 policy 可配？是否**同时收紧 `--stage` 值域**
  （否则拼错即静默失效）？
- **Q4** escape hatch（`WITNESSLOOP_SKIP_GUARD`）要不要？「跳过时留痕」怎么做（本地留痕有意义吗）？
- **Q5** 是否**同时**提供 git-hook（pre-commit/pre-push）适配器，还是只做 CC hook（延后）？
