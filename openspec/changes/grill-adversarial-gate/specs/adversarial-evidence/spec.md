# adversarial-evidence — 设计对抗轮成为硬门

> 本 change 的能力增量：把「设计阶段跑对抗验证轮」（`grill` 之后、停轮之前的证伪环节）
> 从**自觉**变成 `check` 的**机械门**——触发条件满足时，该 change 必须有 `stage=grill-adversarial`
> 的审阅证据（manifest + 被它绑定的报告）。

## Requirement: 触发条件满足时，change 必须有设计对抗轮证据

`witnessloop check` SHALL 在**触发条件**满足时，要求被本次 diff 触及的 change 存在一份
**`stage=<grill_adversarial_stage>`**（默认 `grill-adversarial`，`policy.evidence.grill_adversarial_stage` 可覆写）
的 review manifest；缺失时 SHALL 报错并非零退出，错误信息 SHALL 点名**现有** stage 值以便诊断。

该触发条件 SHALL 是**客观的 git 事实**；SHALL NOT 由「`tasks.md` 是否勾选」之类的**自声明**触发——
不勾选即可绕过。

> ⚠️ **触发面待 Q1 裁定后钉死**（甲=与 grill 条同形，每个被触及的 change 都要求；
> 乙=与 building 条同形，本次 diff 触及 `policy.require_change_for` 时要求）。
> 实现开始前 MUST 用定案替换本节括注——spec 是 manifest 哈希绑定的 artifact，实现后再改会让证据 stale。

### Scenario: 未跑设计对抗轮
- **Given** 触发条件满足，该 change 只有 `stage=grill` 与 `stage=building` 的证据
- **When** 运行 `check`
- **Then** 报错并非零退出，且点名缺 `stage=grill-adversarial` 的审阅证据

### Scenario: 有对抗轮证据则通过
- **Given** 同一条件，但该 change 另有一份 `stage=grill-adversarial` 的 manifest 绑定着对抗验证报告
- **When** 运行 `check`
- **Then** 该条判定通过

### Scenario: 未触发时不误伤
- **Given** 本次 diff **不满足**触发条件
- **When** 运行 `check`
- **Then** **不**要求对抗轮证据

### Scenario: stage 拼错可诊断
- **Given** 用 `--stage grill-adversariall` 产出的 manifest，仓里没有 `stage=grill-adversarial` 的 manifest
- **When** 运行 `check`
- **Then** 报错并指出「现有 stage：…」

### Scenario: 对抗轮之后再改设计 ⇒ stale
- **Given** `stage=grill-adversarial` 的 manifest 记录 `head_sha=H`，且 `H` 之后的提交里改了 `design.md`
- **When** 运行 `check`
- **Then** 报「审阅的是旧 revision」并非零退出（复用既有 revision 绑定，不新增判据）

## Requirement: 证据形态是 manifest（不是裸文件）

该证据 SHALL 以**被 manifest 绑定**的形态存在（`stage=grill-adversarial` 的 manifest + 其
`report_path` 指向存在的报告），SHALL NOT 以「`reviews/` 下的裸报告文件」作为满足条件。

理由（本仓既有机制）：未被任何 manifest 绑定的 `reviews/*.md` 是**孤儿报告**，`check` 会**判红** ⇒
裸文件形态在本仓**不可用**——这也是与 asterwynd（裸文件存在性即可）的**必要偏离**。

### Scenario: 只有裸报告文件
- **Given** change 目录里有 `reviews/grill-adversarial.md`，但没有任何绑定它的 manifest
- **When** 运行 `check`
- **Then** 判红（孤儿报告），且该 change 仍被视为**缺**对抗轮证据

## Requirement: 判定与 grill / building 两条共用同一实现

「要求存在某 stage 的 manifest」SHALL 由**一处**实现提供（`evidence.stage_manifest_findings_in_change`），
grill / building / grill-adversarial 三条判定 SHALL 共用它——分两份实现必然漂移
（本仓已因「两边各写一套」踩过坑）。

该共用 SHALL **不**把 grill 专有的**报告正文**校验泄漏给对抗轮判定
（对抗轮**只**要求证据存在；若 Q2 选乙，另加「最终裁定 = PASS」判据——那是**新增**判据，不是复用）。

### Scenario: 对抗轮不要求 grill 式正文
- **Given** 一份 `stage=grill-adversarial` 的 manifest 绑定着一份普通对抗报告（无 `## Confirmed Decisions` 小节）
- **When** 运行 `check`
- **Then** 该条**不得**因缺少 grill 式小节而报错

## Requirement: 不改变写代码前的本地守卫

本能力 SHALL **只**作用于 `check`（事后 / CI）。`guard`（写码前 / 本地）SHALL **不**新增任何对抗轮条件。

⚠️ **随之而来的缺口（刻意接受，须显式声明）**：`templates/grill.md` 的写码前硬条件 #2
（「对抗验证已到 PASS 或轮数封顶交人」）在**本地守卫侧仍无强制**——`guard` 只查 grill 决策记录。
理由是守卫可绕过（未装 plugin / 用 Bash 写文件）、真正的锚是 CI required check。
**这不是「守卫已覆盖」，而是已知缺口。**

### Scenario: guard 不要求对抗轮证据
- **Given** 一个 change 的 grill 证据完备、但没有 `stage=grill-adversarial` 的 manifest
- **When** `guard --path src/x.py`
- **Then** **放行**（守卫不新增本条条件）

## Requirement: verdict 文本不参与判定（选甲时）

`check` SHALL NOT 解析对抗验证报告里的 verdict 文本（`PASS` / `CHANGES_REQUESTED`）——
本门禁保证的是「**该 change 存在一份可绑定的对抗轮证据**」。

> 若 Q2 选乙，本 Requirement 换成「最终裁定必须为 `PASS`」并须同时规定多轮报告的可判定形态与
> 「轮数封顶交人」的出路；甲是本 change 的推荐口径。

### Scenario: 结论是 CHANGES_REQUESTED 也能通过
- **Given** 一份 `stage=grill-adversarial` 的 manifest 绑定着最终裁定为 `CHANGES_REQUESTED` 的报告
- **When** 运行 `check`
- **Then** 该条判定通过（本门禁不解析 verdict 文本）

## 边界声明（**非新增行为**，把既有逃生面与已知上限写清）

1. **`policy.require_change_for` 写成 `[]`**（或没覆盖目标仓**真实**代码路径）时，`check` 的**整条代码门禁**
   ——「改代码必须挂 change」（`_require_change`）、`building` 门禁、以及与 `building` 同触发面的本门禁——
   SHALL 一并**静默失效**（实测 `check` 退 0）。这是**既有**逃生面，本 change **不**改变它，仅在此声明。
2. **「有 manifest」≠「真跑了独立 run」**：`reviewer_run_id` / `author_run_id` 是自由文本
   （兜底路径下两角色 id **结构性不同**）⇒ 一个 agent 可自造 manifest 满足本门禁。
   本工具**防漂移、不防蓄意伪造**。
3. **无法机械证明「对抗轮发生在 grill 之后、且针对同一份 design」**：`design.md` 的**内容**未被任何
   manifest 哈希绑定（`constants.HASHED_ARTIFACTS` 只含 `tasks.md` / `specs`）。本门禁保证的是
   「存在一份可绑定的对抗轮证据」，**不是**「它证伪了这份 design」。本 change **不**为此新增 `design_hash`。
