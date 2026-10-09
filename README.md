# witnessloop

把「agent 驱动的软件开发流程」做成**独立于任何代码仓、可复用于任意仓库**的工具。

流程：**设计先行 → 设计对抗式追问（grill）→ 实现 → 独立审阅闭环**，全程由**机械门禁 + 证据绑定**强制——而不是靠模型自觉。

> **状态：M1「门禁层」已实现**（`init` / `uninit` / `check` 三动词，fail-closed）。
> 交互层 CC plugin（grill / review-loop）是 M2，尚未开始。
> 设计见 [docs/design.md](docs/design.md)，任务见 [docs/tasks.md](docs/tasks.md)，
> 门禁层数据契约见 [docs/gate.md](docs/gate.md)。

## 用法

```bash
uv tool install git+https://github.com/Xingkai98/witnessloop@v1

# 接入目标仓：幂等、只增不改、不 auto-commit
cd your-repo && witnessloop init --dry-run   # 先看要写什么
witnessloop init                             # 落盘，然后**人工审阅并提交**

# CI 入口（fail-closed）
witnessloop check --base origin/main --head HEAD

# 精确回滚（文件被改过就拒绝删除并报 diff）
witnessloop uninit
```

`init` 写的 caller workflow 引用本仓的 reusable workflow
`.github/workflows/gate.yml@v1`——记得在目标仓 branch protection 里把那个 job
勾成 required，否则门禁不会真的拦人（那一次人肉操作就是 v1 的「人类签名」）。

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
- **门禁落 merge boundary**：强制放在 CI required check，agent hooks 只作辅助提醒——不依赖模型自律。

## 名字

`witness`（独立见证者）+ `loop`（审阅/追问的循环）。每一个审阅环都是一个零记忆的 witness。
