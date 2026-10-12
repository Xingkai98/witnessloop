# adopter-test-job — 接入方的测试要有一个真的执行点

> 本 change 的能力增量：接入方能拿到**一个可用的测试执行点**（不再只有 `witnessloop check`）。
> 交付形态**优先是「约定正确的 workflow 模板 + 复制配方」**（零接口、零 ref 耦合、对存量接入方当天可达）。
>
> ⚠️ **诚实前提（对抗轮 B-1 要求写进交付物）**：**本 change 是「零机械强制」的**——
> 它交付文档 + 模板；接入方不拷、不勾，什么都不会发生。**不得**以「机械门禁项目」之名把它说得像有强制力。

## Requirement: 交付一个可用的测试执行点

本 change SHALL 交付一条**接入方可直接采用**的测试执行路径，使接入方自己的测试在 PR 上自动执行。

该路径 SHALL 对**已接入的仓**同样可达，且 SHALL NOT 要求接入方改动 `init` 生成的任何文件
（实测那是死锁：`init` 与 `uninit` 同时 exit 1，见下一条 Requirement）。

交付物 SHALL 自述「**本 change 零机械强制**」（不拷不勾则什么都不发生）。

> ⚠️ 具体形态（模板 + 文档 / 模板 + 增量①②③（推荐）／`gate.yml` 加 input）由 **Q1** 定案后钉死在此；
> 实现开始前 MUST 替换本括注，并**删掉未选分支**。

### Scenario: 采用模板后的**内容**断言（结构式，可机械验证）
- **Given** 交付的模板文件
- **When** 用 YAML 解析它（先例与理由见 `tests/test_gate_workflow.py:32-34`）
- **Then** 它含三态分支：占位符未替换 ⇒ `::error::` + 非零；显式空 ⇒ `::notice::`；非空 ⇒ 回显命令
  （⚠️ **不写**「PR 触发后日志里有一行」这种**行为式** Scenario——本仓没有任何测试能验证 GitHub 的日志，见 N5）

### Scenario: 存量接入方不改 `init` 产物即可拿到执行点
- **Given** 一个**已经接入**的仓
- **When** 按配方采用测试 workflow（配方 SHALL 给**可达 ref + 可直接执行的获取命令**）
- **Then** 它**无需**改动任何 `init` 生成的文件；且配方里的 ref 上**确实存在**该文件（不会 404）

## Requirement: 三态语义（未声明 / 占位符没填 / 已声明）

交付物 SHALL 区分三种状态：**占位符未替换 ⇒ 失败**（`::error::` + 非零）；**显式空 ⇒ 跳过**（不失败）
并留下 `::notice::`；**非空 ⇒ 执行并回显实际命令**。
SHALL NOT 自行**探测**约定命令（猜 `pytest` / `npm test`）。

理由：模板路线的最大失败模式是「**拷了但没填**」——若那是绿 job，就等于工具亲手种下
「**看起来在保护你**的绿勾」。这一条正是把该风险从「大概率」压到「必须显式确认」。

### Scenario: 三态在交付物里都可辨（**内容式**，可机械验证）
- **Given** 交付的模板文件
- **When** 用 YAML 解析它（不是 grep 子串）
- **Then** 三态各有分支且可区分：**占位符未替换 ⇒ `::error::` + 非零退出**；
  **显式空 ⇒ `::notice::` 且不失败**；**非空 ⇒ 回显实际命令**。
  （⚠️ **不写**「PR 触发后日志里有一行」「该 job 失败」这类**行为式** Scenario——本仓没有任何测试
  能验证 GitHub 的 run 日志或 job 结论，见 N5 与 `spec.md` 上面那条同样的告诫。）

## Requirement: SHALL NOT 要求接入方手改 `init` 的产物

文档与 `init` 的输出 SHALL NOT 教接入方修改 `init` 生成的文件来配置测试命令
（实测：改后 `init` 与 `uninit` **同时** exit 1，`--dry-run`/`--policy`/`--gate-ref` 都不是出口；
有效的出口是**文件级**的：恢复原字节 / 删掉该文件 / 改台账 sha 仅对 `uninit` 有效
——「删台账」**既不必要也不充分**）。

文档 SHALL 同时写明：**不要**用「先 `uninit` 再 `init`」做升级——它会删掉台账里的**每一个**条目
（含 `.witnessloop/policy.json`），**静默丢定制 policy**。

### Scenario: 文档不含两条死路（机械可验证）
- **Given** `README.md` / `docs/gate.md`
- **When** 用 `tests/test_docs.py` 的范式断言（禁语 + 必含限定）
- **Then** 文档里**不出现**「手改 `init` 产物」或「先 `uninit` 再 `init`」的教法

## Requirement: 不得过度承诺（能力边界）

文档 SHALL 在每一处「拦住合并」的表述上带限定：**在本次 PR 未修改自己 CI 配置的前提下**
（`.github/workflows/**` 不在保护路径、`required_approving_review_count: 0`
⇒ 一个 PR 可以删掉自己的测试步骤而 required check 依旧绿）。

### Scenario: 每处承诺都有作用域（机械可验证）
- **Given** README / `docs/gate.md`
- **When** 按 `tests/test_docs.py::test_every_idempotency_claim_is_scoped_or_qualified` 的范式（±2 行窗口）扫描
- **Then** 每一处「拦住合并」都带限定，没有无限定条件的裸承诺

## Requirement: `check` 的测试缺失播报是**非阻塞 notice**

（依 **Q13** 定案；未选则本节整节删除。）`witnessloop check` SHALL 在「仓里除 witnessloop 的 caller 外
没有任何 workflow」时输出一行**非阻塞**播报（`::notice::`）；该播报 SHALL **不**产生 finding、
SHALL **不**改变退出码、SHALL **不**显著改变耗时。

### Scenario: 播报不改判定（内容式）
- **Given** 一个除 caller 外无 workflow 的仓
- **When** 运行 `check`
- **Then** 输出里有一行 `::notice::`，且 **findings 与退出码与不播报时逐字相同**

## Requirement: `check` 不执行测试

`witnessloop check` SHALL NOT 执行接入方的测试命令——它只判**流程证据**；
本 change SHALL NOT 改变 `check` 的**判定语义**与耗时。（⚠️ 论据**不是**「`check` 也被 guard 调用」——那为假。
⚠️ 与上面那条「**非阻塞 notice**」Requirement 的关系：notice **只加一行播报**，不参与判定
⇒ 「不改变判定语义」与「加一行 notice」不矛盾；两条 Requirement 不是同一件事。）

### Scenario: 本地 check 不跑测试
- **Given** 仓里已采用测试 workflow
- **When** 本地运行 `witnessloop check`
- **Then** SHALL NOT 执行任何测试命令

## Requirement: 不新增运行时依赖

实现 SHALL NOT 给 `witnessloop` 增加运行时依赖（`pyproject.toml` 的 `dependencies` 保持 `[]`）；
该约束 SHALL 有一条测试钉住（现状：`tests/` 里零落点）。

### Scenario: 依赖为空
- **Given** 本 change 后的 `pyproject.toml`
- **When** 解析它
- **Then** `dependencies == []`

## 边界声明（必须写进文档）

1. 测试命令（若采用）是**任意代码**，会在每个 PR（含 **fork PR**）的 runner 上执行。
2. **本 change 零机械强制**：交付物是文档 + 模板，**不新增任何门禁**；且**本 change 自己的 PR**
   由 **`@v1` 的 CLI** 把关（v1 **不含** #13/#16 的新门禁）——文档 SHALL 写清**哪条规则在哪个 ref 上生效**。
3. 本仓自己的 `test` job 目前**不是** required（⇒ 本仓可带红测试合入）；本 change SHALL 把它写成一条**人工交付项**。
