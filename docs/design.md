# witnessloop 设计 v0.2

> 状态：**设计已定**（经 grill + 独立对抗验证 + 用户逐项确认）。
> **实现状态：MVP 完成**（M1+M2+M3，全流程在第二仓跑通，见 `docs/tasks.md` 与 `docs/reviews/m3-acid-test.md`）。
> v0.1：2026-10-09 起草；v0.2：2026-10-09 收敛；其后增补 §4.1（分发与可见性，acid test 实测）。
> 证据见 [`docs/reviews/grill-design.md`](reviews/grill-design.md)、[`docs/reviews/grill-adversarial.md`](reviews/grill-adversarial.md)、[`docs/reviews/m1-acid-test.md`](reviews/m1-acid-test.md)。

## 1. 问题

Agent 写代码的核心风险不是「不会写」，而是「**不可信**」：

- 跳过设计直接写代码；
- 自评通过，没有独立第三方；
- 审阅走过场，或审阅者与作者共享上下文、盲区一致；
- 证据只存在于对话 transcript 里——不可提交、不可审计、不可复现。

## 2. 目标

把一套已在真实仓库跑过 300+ change 的流程，抽成**独立、可复用于任意代码仓**的工具，让「证据」变成机械可检查的东西：

1. **设计先行**：非平凡改动先有 design 文档。
2. **设计对抗（grill）**：独立零记忆审阅者对 design 逐轮追问，产出可提交的决策记录。
3. **实现**：测试先行（TDD）。
4. **独立审阅闭环**：实现完成后由独立零记忆审阅者审，PASS 或 N 轮封顶。
5. **证据绑定**：审阅结论与 manifest（审阅者身份 + base/head sha + 各 artifact hash）成对提交。
6. **门禁落 CI**：受保护 artifact 的写入需结构化解释事件；**强制落在 merge boundary（CI required check）**，agent hooks 只作提醒。

> **能力边界的诚实表述**：witnessloop **默认只提供「防漂移」**（防止证据文件事后被悄悄改动、防止流程被遗忘），**不提供「防蓄意伪造」**。防伪造需要外部锚（见 §5.3）——v1 不做，文档明写。

## 3. 非目标

- **不重造 spec/需求层**（用上游 OpenSpec 的目录契约）。
- **不做 LLM，也不做 agent 运行时**：witnessloop 寄生在已有 coding agent 上。
- **不锁定单一 agent host**（v1 只交付 Claude Code 适配器，但模板与适配器物理分离）。
- **不追求零配置**：目标仓必须显式 `init` 接入。

## 4. 已定架构轴（2026-10-09 拍板）

| 轴 | 决策 |
|---|---|
| 范围 | 门禁层 + 交互层（都抽） |
| 语言/工具链 | Python + uv，单二进制 `witnessloop` |
| 仓库边界 | 独立新仓（witnessloop），零 asterwynd import |
| 交互层 host | CC-first；模板与适配器**物理分离**，v1 只交付 CC |
| 分发 | 门禁层=独立 CLI（跑 CI）；交互层=CC plugin。**git 公开分发起步，marketplace 不上路线图**（可见性约束见 §4.1） |
| spec 依赖 | **硬编码 OpenSpec 形状的 change 契约**；只参数化 repo-agnostic 的轴（路径/策略）。不造 spec 适配器 |
| 状态真相源 | **manifest = 每 change 每阶段的权威证据**；事件日志降为可选历史，不重建 projection/replay 状态机 |
| 信任锚 | 靠**远端 branch protection + required check**（人手动开一次）+ 诚实话术。**v1 不造签名** |

### 4.1 分发与可见性（2026-10-09 真实仓 acid test 实测）

**v1 假设 witnessloop 公开。** 在私有仓下会发生两处摩擦，已用一次性仓 `Xingkai98/wl-test` 实测：

1. **reusable workflow 访问级别**：私有仓的 reusable workflow 默认 `none`，且**最多只能开放到「同 owner」**——外部接入方根本调不到。表现为 caller run **0 个 job**、报「workflow file issue」。
2. **CI 安装私有包需要凭据**：reusable workflow 里 `uvx --from git+https://github.com/<owner>/witnessloop@v1` 在私有仓下报 `fatal: could not read Username for 'https://github.com': terminal prompts disabled`。

改为**公开**后两处摩擦全消、零配置。**私有接入需要额外配置 token，不在 v1 范围。**（这也把最初「私有起步」的判断修正为「公开起步」。）

## 5. 架构

### 5.1 门禁层（enforcement，host-agnostic）

单二进制 `witnessloop`（Python + uv 分发），跑在**终端 / CI required check**。

**v1 交付 3 个门禁动词 + 1 个证据产出动词**：

- `init`：把 witnessloop 接入目标仓。**幂等、只增不改、不 auto-commit、支持 `--dry-run`**。写入：
  - `.witnessloop/policy.json`（受保护路径 + 必需 artifact + 证据格式 + `require_change_for`）
  - `.witnessloop/init-manifest.json`（创建清单 + init 前 base ref）
  - 一个极薄 GitHub caller workflow（`uses: <owner>/witnessloop/.github/workflows/gate.yml@v1`）
- `check`：CI 入口，**fail-closed**。校验 change 目录契约、review manifest 存在且 hash 绑定、`reviewer ≠ author`、受保护路径写入有结构化解释事件、**命中 `require_change_for` 的改动必须挂 change 目录**。无 policy 时报「未接入」并以非零退出。
- `uninit`：依 `init-manifest.json` 精确回滚（被改过的文件拒绝删并报 diff）。

外加一个**支撑动词**（M2 交付，交互层收尾要用）：

- `manifest build`：产出 `check` 认的 review manifest。**与 `check` 共用同一张
  字段↔artifact 绑定表和同一个哈希函数**（`constants.HASHED_ARTIFACTS` +
  `hashing.sha256_tree`），杜绝「产出的 manifest」与「校验的期望」两边漂移。
  幂等、不 auto-commit；不合格直接报错不写文件。

**不变集**：witnessloop 自身的输入（policy 文件、manifest）**恒受保护、不可由 repo policy 移除**，封顶 ~5 条常量。

**明确不做**（延后）：`gate`/`event`/`status`/`policy upgrade` 等其余动词、policy schema 冻结、platform-gate 自动注册。

### 5.2 交互层（interaction，CC-first）

- **host 中立模板 + 每 host 一个薄适配器**，物理分离；v1 只交付 CC 适配器。
- CC 适配器 = plugin（slash command + subagent + skill）：`grill`、`review-loop`。
- **重写，不回收**：asterwynd 的 `/grill`、`/review-loop`、`grilling` 不在版本控制、含私有约定，与「证据可信」自相矛盾。做法 = **重打包**：算法与 prompt 文本照收，去掉私有路径/issue 号，抽象成 host 中立模板。
- **硬约束**：交互层对 change 状态**只读**，**不得持有自己的状态文件**；一切以 `manifest` 为准。
- **两个取值覆盖点**（host 没有稳定的 run id 注入点，插件也没有固定安装位置，
  所以适配器与工具必须按同一套规则取值；可执行实现见 `src/witnessloop/agentenv.py`）：
  - `WITNESSLOOP_RUN_ID`：当前 run 的 id。**环境优先、生成兜底**——取不到就生成
    `<stage>-<role>-<UTC 时间戳>-<短随机>`，`role` 编进 id 所以两个角色必然不同
    （`reviewer_run_id != author_run_id` 是门禁的硬校验）。角色专用变量
    `WITNESSLOOP_REVIEWER_RUN_ID` / `WITNESSLOOP_AUTHOR_RUN_ID` 优先级更高。
  - `WITNESSLOOP_TEMPLATES_DIR`：覆盖模板目录；未设时适配器回落
    `${CLAUDE_PLUGIN_ROOT}/../templates`（`plugin/` 被单独拷走时靠它指回模板）。

### 5.3 数据契约

- change 目录契约：OpenSpec 形状（`proposal / design / tasks / specs delta`）+ `reviews/` + `workflow-events.jsonl`。
- 审阅证据 = **报告 + manifest 成对**。manifest 的 `head_sha` = **最后一个非证据 revision**，其到被检 head 之间只允许证据文件改动（由此推出**提交约定：先内容、后证据**；单提交 PR 不被支持）。
- manifest 字段：`reviewer_run_id` / `author_run_id`（**强制 `reviewer ≠ author`**）/ `base_sha` / `head_sha` / `tasks_hash` / `spec_hash` / `diff_hash`（informational）/ `report_hash`。
- **能力边界**：hash 绑定真实 artifact 字节，证明「证据之间没漂移」；`reviewer_run_id` 等身份字段是自由文本，v1 不做语义绑定。

## 6. 从 asterwynd 抽取的资产（探索 + 实测核对）

- **可抽内核 ≈ 5.3k LOC**：engine + `guard` + `checker` + `policy` + `platform_gate`；配套测试 ≈ 3.6k LOC。
- **主工作量 = 参数化，不是搬运**：`check_openspec_artifacts.py` 实测 **1802 行 / 72KB**，重度 asterwynd 专用（硬编码 change 类型枚举、`DESIGN_SECTIONS`、`BENCHMARK_SMOKE_CAPABILITIES`、backlog 路径）。把常量搬进 policy 才是主要成本。
- **两个缺口**：① 流程的「行为」不在版本控制 → 重写；② checker 惰性 `import agent.workflow.*`，绑死产品包 → 内联或抽接口。
- **状态机仪式残留 ≈ 1000 LOC**：v1 不搬。

## 7. 验收（acid test）

对**第二个、非 asterwynd 的仓库**端到端跑通：`init` → 写一个 change → grill → 实现 → review-loop 通过 → `check` 绿。

**必须含负例**：

- (a) 手写一行放行事件提交，`check` 的行为写清预期（默认：不拦，但文档注明不防伪造）；
- (b) 交互层状态与 manifest 故意漂移，系统应报错而非双绿；
- (c) 目标仓不跑 `init` 时，`check` 应报「未接入」而非静默通过；
- (d) `init` → `uninit` 回滚往返。

**已实测（M1 级，2026-10-09）**：在 `Xingkai98/wl-test` 上，一个「只改 `src/`、无 change 目录」的 PR 被**真 GitHub Actions 门禁拦下**，报错精确到 `policy.require_change_for` 与 `src/app.py`。**「有证据 → 通过」与完整流程待 M2**（CC plugin 产出证据）。详见 [`docs/reviews/m1-acid-test.md`](reviews/m1-acid-test.md)。

## 8. Open Questions（已收敛）

原 7 项 + 补充 5 项，全部经 grill + 对抗验证 + 用户确认。决策记录见 [`docs/reviews/grill-design.md`](reviews/grill-design.md) 的 `## User Confirmation`。

## 9. 风险

1. **证据可自证／可伪造（最高危）**：门禁输入都是 agent 可写的本地文本 → 默认只防漂移。→ 话术降级 + 文档写清；防伪造列为 v2 候选。
2. **越抽越耦合，且成本被低估**：`check_openspec_artifacts.py` 的常量参数化是主成本。
3. **required-check 鸡生蛋**：注册 required check 需 admin，fork/新仓不跑 init 就**静默为零**。→ `check` 无 policy 时报「未接入」。
4. **强制只在 CI 一层**：guard hook 是 PreToolUse、需手动装，CI 只跑 `check`。
5. **「独立审阅」剧场化**：`reviewer_run_id` 不校验 ⇒ 同一 run 既写又审也能过。→ 强制 `reviewer ≠ author`。
6. **可见性错配**：私有 witnessloop 会让接入方 CI 全面失败（见 §4.1）→ v1 明确要求公开。
7. **路径语义**：Windows 反斜杠/大小写/`~` 是已知坑，通用化须显式处理。

## 10. MVP 范围（一句话）

**在第二个真实仓库里，用机械门禁把「设计与实现的证据」绑进 CI required check。**

**做**：单二进制 + 3 个门禁动词（`init` / `check` / `uninit`）+ 支撑动词 `manifest build` · policy（受保护路径 + 必需 artifact + `require_change_for` + 证据格式）· manifest（含 `author_run_id`）· CC plugin 的 `grill` / `review-loop`（重写、只读、无状态）。

**不做**：签名/密钥 · marketplace · spec 适配器抽象 · 状态机/projection/replay · platform-gate 自动注册 · `policy upgrade` · 证据分档机制 · 多 host · 7 动词 · schema 冻结 · 私有仓接入。
