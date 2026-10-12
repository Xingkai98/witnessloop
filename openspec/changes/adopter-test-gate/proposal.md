# Proposal: adopter-test-gate（接入方的测试要进 CI，且要能拦住合并）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#4**。

## 背景

`init` 写的 caller workflow **只跑 `witnessloop check`**（`initcmd.caller_workflow`，`initcmd.py:24-40`）——
接入方自己的测试**没有任何自动执行点**：

- 实证（issue #4 来源）：M3 acid test 的 `add-greeting` change 引入了 `tests/test_greeting.py`（13 个用例），
  而目标仓的 CI 只跑 `check`，**pytest 一次都没跑**。
- 与流程要求直接冲突：流程规定「实现阶段 TDD、审阅者核实测试通过」（出处 `templates/review-loop.md:33,69,77`）
  ——**审阅者只能靠人工记忆跑一次**，没有 CI 兜底；测试「写完就烂」不会被任何机制发现。
- 对照：asterwynd 自己的 `ci.yml` 跑全量 pytest；本仓自己也有一条 `ci.yml`（`test` job）——
  **但那是 witnessloop 的自测，不是给接入方的**。接入方拿到的是一个**只看流程证据、不看代码好坏**的门禁。
- ⇒ 这是本仓「信任」主线里最后一个大洞：**`check` 保证「流程跑过了」，不保证「代码是好的」**。

## 立项前的关键实测（改变方案的三条约束）

1. **caller 是「极薄」且被台账管理**：`initcmd.caller_workflow` 只写一个 `uses:` job，
   文件头明写「请勿手改」，并且它的 hash 记在 `.witnessloop/init-manifest.json` 里（`uninit` 依它回滚）。
   ⇒ **接入方特有的东西**（他们的测试命令）**不能只靠手改 caller**——要么走 policy（工具拥有、JSON、可 `init --policy`），
   要么 caller 里能带 `with:` 参数。
2. **`@v1` 到不了新 `gate.yml`，而且它同时钉着 CLI 版本**（**已按 grill 订正**）：
   `DEFAULT_GATE_REF = …gate.yml@v1`（`constants.py:11`）；`v1 == v1.5.0 == 843b691`，main 领先 **6** 个提交
   （`git rev-list --count v1..origin/main` 实测）。
   ⚠️ **订正**：`v1` 不是「固定 tag」——它自己的注记写着「**滚动大版本**（当前指向 v1.5.0）」
   （`git tag -n99 v1`），历史上随发布滚动，只是最近 6 个提交没滚。
   更关键的一层：`gate.yml:19-23` 的 `witnessloop-ref` **默认值就是 `v1`**、caller 从不覆盖
   ⇒ **移动 `v1` = 连被 uvx 装下来的 witnessloop CLI 一起换**（把 6 个提交里多条「对**接入方**是行为变更」
   一起静默送达）。⇒ 若走「改 `gate.yml`」那条路，ref/发布策略是**硬前置**；
   而**选「模板 + 文档」那条路则整段不需要**（见 design D1/D5）。
3. **工具运行时零依赖**（`pyproject.toml` 的 `dependencies = []`；pyyaml 只在 dev group，给测试用）。
   ⚠️ **订正**（grill 指出我把两件事绑死了）：零依赖**不**等于「只能退化成子串匹配」——
   还有第三条路：**让 workflow 在运行时读仓内文件**（runner 自带 `jq`/`python3`），`check` 完全不参与。
   零依赖约束本身成立，但它**不**排除「单一事实源」。

## 目标（**已按 grill + 对抗验证 R1 收窄**）

交付**一个接入方可用的测试执行点**——**真正要交付的产品是「一份约定正确的 YAML + 一个可复制的配方」**
（grill 的论证：required check 的勾选**在所有方案里都是人工的**——required 粒度是 job）
⇒ 优先走**零接口、零 ref 耦合、且对存量接入方也可达**的路（design D1 的「己」+ 增量 ①②③），
把「接入方的测试」塞进 witnessloop 自己的 `workflow_call` 接口（甲）降为备选。

⚠️ **诚实前提（对抗轮 B-1）**：**本 change 是「零机械强制」的**——不拷模板、不勾 required，什么都不会发生。
交付物**必须自己说出这一点**，不得以「机械门禁项目」之名把它说得像有强制力。

同时把约束的后果写清：required 是人工一步、本能力的**能力边界**（只在 PR 不改自己 CI 的前提下成立）、
以及**哪条规则在哪个 ref 上生效**（⚠️ 本仓 PR 的门禁跑的是 `@v1` 的 CLI，**不含** #13/#16 的新门禁——对抗轮 B1 实测）。

## 与 issue #4 的关系（**不得含糊**）

issue #4 原文给的两条建议（「`init` 的 caller 顺带跑测试」/「policy 加测试命令字段由 `check` 调用」）
**都是机械的**，而本 change **一条都不做** ⇒ **不得**用本 change 直接关掉 #4：
要么保持 #4 open、要么关闭时**另开一条「机械执行点」issue** 承接那两条建议（design §6 的 Q9）。

## 非目标（**已按 grill 扩写**）

- **不让 `check` 去跑测试**：保持 `check` 的性质（只判流程证据）。⚠️ 论据**不是**「`check` 也被 guard 调用」
  ——grill 证伪了这条（`guard` 不调用 `check`）；真实论据是「跑测试是 CI 侧 job 的职责，且 `check` 的语义/耗时不该被改变」。
- **不做测试命令「探测」**（猜 `pytest` / `npm test`）：显式声明优于魔法，探测错会静默跑错东西。
- **不改 `gate.yml` 与 `DEFAULT_GATE_REF`**（在推荐方案下 ⇒ 连带**不需要** ref/发布决策）。
- **不改 `caller_workflow()` 的字节**（否则本仓自己的 init 台账会与磁盘不一致 ⇒ 此后任何 `init` 撞死锁，见 R17）。
- **不把「手改 `init` 产物」写成正常用法**（实测是死锁；文档只能教**模板/自有文件**这条路）。
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
