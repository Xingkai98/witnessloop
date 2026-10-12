# adopter-test-job — 接入方的测试要有一个真的执行点

> 本 change 的能力增量：接入方能拿到**一个可用的测试执行点**（不再只有 `witnessloop check`），
> 且这个执行点**能被勾成 required 拦住合并**。交付形态**优先是「约定正确的 workflow 模板 + 复制配方」**，
> 而不是改动 witnessloop 的 `workflow_call` 接口。

## Requirement: 交付一个可用的测试执行点

本 change SHALL 交付一条**接入方可直接采用**的测试执行路径，使接入方自己的测试在 PR 上自动执行。

该路径 SHALL 对**已接入的仓**同样可达（存量接入方 SHALL NOT 需要改动 `init` 生成的任何文件——
实测那是死锁，见下面的 Requirement）。

> ⚠️ 具体形态（模板 + 文档 / `init` 种一份 + 模板 / `gate.yml` 加 input）由本 change 的 **Q1** 定案后
> 钉死在此；实现开始前 MUST 替换本括注。

### Scenario: 新接入方拿到执行点
- **Given** 一个刚 `witnessloop init` 的仓（Python、用 `pytest`）
- **When** 按 README 的配方采用测试工作流并把它勾成 required
- **Then** 该仓的 PR 会自动跑测试；测试失败 ⇒ 合并被拦

### Scenario: **存量**接入方拿到执行点（R11：原稿没覆盖的节点）
- **Given** 一个**已经接入**的仓（`init` 产物不许动）
- **When** 按 README 的配方采用测试工作流
- **Then** 它**无需**改动任何 `init` 生成的文件即可获得执行点

## Requirement: SHALL NOT 要求接入方手改 `init` 的产物

文档与 `init` 的输出 SHALL NOT 教接入方去修改 `init` 生成的文件来配置测试命令——
实测（本机复现）：改了之后 `init` **exit 1**、`uninit` **exit 1**、**删台账再 `init` 也 exit 1**
（「只增不改，拒绝覆盖已有文件」），且没有任何 flag 能表达「我确认」。

文档 SHALL 同时写明：**不要**用「先 `uninit` 再 `init`」做升级——`uninit` 会删掉台账里的**每一个**条目
（含 `.witnessloop/policy.json`），会**静默丢定制 policy**。

### Scenario: 文档不提供死锁路径
- **Given** README 的接入/升级配方
- **When** 逐条读它教接入方做的事
- **Then** **没有**任何一条是「手改 `init` 产物」或「先 `uninit` 再 `init`」

## Requirement: 空命令 ⇒ 跳过，但必须留下可见信号

测试命令未声明时，执行路径 SHALL **跳过**测试（不失败）——SHALL NOT 自行**探测**约定命令。
同时 SHALL 输出**运行时可观测的信号**（如日志里一行 `::notice::`「未声明测试命令」），
并在有命令时**回显实际执行的命令**。

理由：空=跳过 + required 绿 = 「**看起来在保护你**的绿勾」；`pytest --collect-only` 这类粘贴失误
（收集 N 个、跑 0 个、exit 0）会让门禁**永远绿**。

### Scenario: 空命令可见
- **Given** 采用测试工作流但未声明命令
- **When** PR 触发
- **Then** 该 job **成功**，且日志里有一行明说「未声明测试命令」（不是静默成功）

### Scenario: 不做探测
- **Given** 一个只用 `pytest` 的仓（没声明命令）
- **When** 触发
- **Then** SHALL NOT 自行推断并运行 `pytest`

## Requirement: 不得过度承诺（能力边界）

文档 SHALL 写明本能力**只在「本次 PR 未修改自己的 CI 配置」的前提下**成立——
`.github/workflows/**` 不在保护路径、branch protection 实测 `required_approving_review_count: 0`
⇒ 一个 PR 可以删掉自己的测试步骤（或写成 `|| true`）而 required check 依旧绿。
文档 SHALL NOT 承诺「测试失败一定拦住合并」这种无限定条件的说法。

### Scenario: 承诺带限定
- **Given** README / `docs/gate.md` 里关于本能力的表述
- **When** 逐句检查
- **Then** 每一处「拦住合并」都带「在你自己的 CI 配置未被本次 PR 修改的前提下」这一限定

## Requirement: `check` 不执行测试

`witnessloop check` SHALL NOT 执行接入方的测试命令——它只判**流程证据**；
跑测试是 CI 侧 job 的职责，本 change SHALL NOT 改变 `check` 的语义与耗时，SHALL NOT 让它依赖测试产物。

### Scenario: 本地 check 不跑测试
- **Given** 仓里已采用测试工作流
- **When** 本地运行 `witnessloop check`
- **Then** SHALL NOT 执行任何测试命令

## Requirement: 不新增运行时依赖

实现 SHALL NOT 给 `witnessloop` 增加运行时依赖（`pyproject.toml` 的 `dependencies` 保持 `[]`）。

### Scenario: 依赖不变
- **Given** 本 change 后的 wheel
- **When** 检查 METADATA
- **Then** SHALL NOT 出现新的 `Requires-Dist`
