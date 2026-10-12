# Proposal: adopter-test-gate（接入方的测试要进 CI，且要能拦住合并）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#4**。

## 背景

`init` 写的 caller workflow **只跑 `witnessloop check`**（`initcmd.caller_workflow`，`initcmd.py:24-40`）——
接入方自己的测试**没有任何自动执行点**：

- 实证（issue #4 来源）：M3 acid test 的 `add-greeting` change 引入了 `tests/test_greeting.py`（13 个用例），
  而目标仓的 CI 只跑 `check`，**pytest 一次都没跑**。
- 与流程要求直接冲突：流程规定「实现阶段 TDD、审阅者核实测试通过」——**审阅者只能靠人工记忆跑一次**，
  没有 CI 兜底；测试「写完就烂」不会被任何机制发现。
- 对照：asterwynd 自己的 `ci.yml` 跑全量 pytest；本仓自己也有一条 `ci.yml`（`test` job）——
  **但那是 witnessloop 的自测，不是给接入方的**。接入方拿到的是一个**只看流程证据、不看代码好坏**的门禁。
- ⇒ 这是本仓「信任」主线里最后一个大洞：**`check` 保证「流程跑过了」，不保证「代码是好的」**。

## 立项前的关键实测（改变方案的三条约束）

1. **caller 是「极薄」且被台账管理**：`initcmd.caller_workflow` 只写一个 `uses:` job，
   文件头明写「请勿手改」，并且它的 hash 记在 `.witnessloop/init-manifest.json` 里（`uninit` 依它回滚）。
   ⇒ **接入方特有的东西**（他们的测试命令）**不能只靠手改 caller**——要么走 policy（工具拥有、JSON、可 `init --policy`），
   要么 caller 里能带 `with:` 参数。
2. **`v1` 是固定 tag，main 已领先 6 个提交**：`DEFAULT_GATE_REF = …gate.yml@v1`（`constants.py:11`），
   而 `v1 == v1.5.0 == 843b691`，`origin/main == de51a01`（实测 `git rev-list --count v1..origin/main` = **6**）。
   ⇒ **对 `gate.yml` 的任何改动都到不了已接入方**；更硬的是：若 `init` 开始往 caller 里写一个新的 `with:` 参数，
   而 `@v1` 的 `gate.yml` **没有声明**这个 input，GitHub 的 `workflow_call` 会**直接报错**
   （「未声明的 input」——⚠️ 属平台行为断言，**待 grill 查证/实测**：本机跑不了 Actions）
   ⇒ **本 change 必须同时决定 ref / 发布策略**，否则新接入方一 `init` 就坏。
3. **工具运行时零依赖**（`pyproject.toml` 的 `dependencies = []`；pyyaml 只在 dev group，给测试用）
   ⇒ 若想让 `check` 去校验 caller 里「测试命令有没有接上」，会**引入依赖或退化成脆弱的子串匹配**——
   这条是设计取舍的硬约束。

## 目标

让门禁能跑**接入方自己声明的**测试命令，并且**能作为 required check 拦住合并**（不只是「跑了」）。
同时把上面三条约束的后果在文档里写清（含「required 需要人工勾一次」这个已知的人肉步骤）。

## 非目标（候选，待 grill/停轮确认）

- **不让 `check` 去跑测试**：保持 `check` 的性质（只判流程证据），测试是**另一个 job / 另一段步骤**。
- **不做测试命令「探测」**（猜 `pytest` / `npm test`）：显式声明优于魔法，探测错会静默跑错东西。
- 不改本仓自己的 `ci.yml`（它是自测，跟接入方无关）。
- 不引入运行时依赖。

## 验收

- **测试**：`gate.yml` 的结构用**已有的** `tests/test_gate_workflow.py` 同款手法（pyyaml 解析 + 定位具体字段）钉住——
  而不是 grep 子串。
- **幂等/兼容**：`init` 的产物变化要过既有的幂等 / 冲突 / `uninit` 回滚用例；
  **空命令 = 跳过**（存量接入方与不做测试的仓行为不变）。
- **本仓自举不回归**：本仓自己的 caller（`.github/workflows/witnessloop.yml`）与本 change 的关系要说清
  （它引用的是 `@v1`，本 change 的 `gate.yml` 改动**不会**影响本仓自己的 PR 检查）。
- 本 change 自己走完整流程（契约 + 证据 + `check` + PR）。

## 测试策略

TDD。`gate.yml` 的断言走 **pyyaml 结构化解析**（`tests/test_gate_workflow.py` 已有先例与理由注释：
「只 grep 子串钉不住位置 + 取值都重要的行」）；`init` 侧断言走既有 `tests/test_init*.py` 的手法。
