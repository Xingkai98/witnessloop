# witnessloop 设计（草案 v0.1）

> 状态：**草案，待 grill + 对抗闭环**。
> 决策日期：2026-10-09。本文档由主 session 起草，尚未经独立审阅者逐项追问。

## 1. 问题

Agent 写代码的核心风险不是「不会写」，而是「**不可信**」：

- 跳过设计直接写代码；
- 自评通过（「我做的对啊」），没有独立第三方；
- 审阅走过场，或审阅者与作者共享上下文、盲区一致；
- 证据只存在于对话 transcript 里——不可提交、不可审计、不可复现。

代价是多轮返工、以及「看起来做完了其实没有」的假完成。

## 2. 目标

把一套已在真实仓库跑过 300+ change 的流程，抽成**独立、可复用于任意代码仓**的工具，把「可信」变成机械可验证的东西：

1. **设计先行**：非平凡改动先有 design 文档。
2. **设计对抗（grill）**：独立零记忆审阅者对 design 逐轮追问，产出结构化决策记录；**缺证据禁止写代码**（机械门禁）。
3. **实现**：测试先行（TDD）。
4. **独立审阅闭环**：实现完成后由独立零记忆审阅者审，PASS 或 N 轮封顶。
5. **证据绑定**：每次门禁通过绑定可审计证据（审阅者 run id、base/head sha、各 artifact hash）。
6. **机械门禁**：受保护 artifact 的写入需要结构化解释事件；CI required check 强制执行。

## 3. 非目标

- **不重造 spec/需求层**：复用上游 OpenSpec（成熟商品层），只在其上叠门禁。
- **不做 LLM 本身，也不做 agent 运行时**：witnessloop 是流程工具，寄生在已有 coding agent 上。
- **不锁定单一 agent host**：交互层 host 中立 + 适配器。
- **不追求零配置**：目标仓必须显式接入（`init` 会改目标仓）。

## 4. 已定架构轴（2026-10-09 拍板）

| 轴 | 决策 | 理由 |
|---|---|---|
| 抽取范围 | **门禁层 + 交互层** | 差异层全集；只抽机械门禁只给半套流程 |
| 语言/工具链 | **Python + uv** | 复用 asterwynd 现有 ~5.3k LOC 内核，改动最小；uv 分发成熟 |
| 仓库边界 | **独立新仓**（witnessloop） | 强制零 asterwynd 依赖；acid test 要跑第二仓 |
| 交互层 host | **CC-first，结构可扩展** | 先 CC 跑通，交互层按「host 中立模板 + 薄适配器」写，加 host 只加适配器 |
| 分发 | **门禁层独立 CLI + 交互层 CC plugin** | 强制落 CI（host-agnostic）；体验放在 host 内 |

## 5. 架构（两层）

### 5.1 门禁层（enforcement，host-agnostic）

一个独立 CLI（`witnessloop`，Python + uv 分发），跑在**终端 / CI required check**，与 agent 是谁无关。

- 命令面（草案）：`init` / `validate` / `gate` / `manifest`。
- **单一策略源**：一份声明式策略文件（受保护路径规则、必需 artifact、证据强度、gate 定义）。
- 职责：校验 artifact 齐备、校验证据存在且绑定正确、校验受保护路径的写入有结构化解释事件。

### 5.2 交互层（interaction，CC-first）

- **host 中立模板 + 每 host 一个薄适配器**；第一版只交付 Claude Code 适配器。
- CC 适配器 = plugin（slash command + subagent + skill）：`grill`、`review-loop`。
- 关键：交互层**只负责体验与驱动**，真正的强制在门禁层（CI），不靠 hooks。

### 5.3 数据契约

- change 目录约定（proposal / design / tasks / spec delta）。
- 证据文件命名与格式（grill 决策记录、审阅报告 + manifest）。
- manifest 字段：审阅者 run id、base/head sha、tasks/spec/diff/report 的 hash。

## 6. 从 asterwynd 抽取的资产（探索结论）

**机械内核可抽，约 5.3k LOC**：engine（`event_log` / `models` / `routing` / `review_manifest`）+ `guard` + `checker` + `policy` + `platform_gate`，配套测试约 3.6k LOC。

**两个缺口**：

1. **流程的「行为」不在版本控制里**——`/grill`、`/review-loop` 只在 gitignored 的 `.claude/`，`grilling` skill 只在 `~/.claude/`。抽取必须先决定回收还是重写。
2. **checker 非独立**——惰性 `import agent.workflow.*`，被绑死在 asterwynd 产品包上，需内联或抽接口。

**硬耦合待参数化**：repo 名、benchmark 领域常量、受保护路径表、platform-gate checks、CI 步骤。

## 7. 验收（acid test）

对**第二个、非 asterwynd 的仓库**端到端跑通：

`init` → 写一个 change → grill（含缺证据禁写验证）→ 实现 → review-loop 通过 → gate 绿。

这是「可复用于任意代码仓」唯一可信的证明。

## 8. Open Questions（待 grill 逐项确认）

- **Q1**：`awaiting` 停轮态是否保留？（asterwynd 的四阶段状态机已退役，此差异点需重新论证）
- **Q2**：OpenSpec 依赖强度——强依赖上游，还是 spec-agnostic（自定义目录）？
- **Q3**：受保护路径 / 文档布局如何通用化？
- **Q4**：命令/skill 从本机 `.claude/`、`~/.claude/` **回收**还是**重写**？
- **Q5**：证据强度——manifest hash 机制作为默认，还是可选增强？
- **Q6**：分发细节——CC plugin 是否上架 marketplace（供应链信任），还是私有 / git 分发？
- **Q7**：门禁 CLI 的命令面与配置 schema 具体形态。

## 9. 风险

- **越抽越耦合**：asterwynd 特有规则悄悄混进内核 → 用「第二仓 acid test」防。
- **强制不可靠**：靠 agent hooks 强制会漏 → 强制必须落 CI。
- **同质化**：变成「又一个 spec 工具」——探索发现已有十几个「agent 开发流程 + 门禁」的低星尝试。差异点必须钉死在**证据绑定 + 机械门禁**，不是概念新。
