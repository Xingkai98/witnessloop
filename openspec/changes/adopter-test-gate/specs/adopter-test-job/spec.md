# adopter-test-job — 接入方的测试进 CI，且**有机械保障**

> 本 change 的能力增量（v2 · 机械版）：`init` 把**测试执行点**写进去，`gate.yml` 跑它，
> `check` **机械地要求**它存在且已接线 ⇒ **没有测试执行点的仓会被拦住**，测试失败的 PR 合不了。

## Requirement: `init` 写入测试执行点

`init` SHALL 让新接入的仓**开箱即有一个测试执行点**：
`init --test-command "<cmd>"` SHALL 把该命令写入**命令文件**（默认 `.github/witnessloop-tests.txt`）；
**该 flag SHALL 覆盖已有内容**（显式意图优先——不得因为文件已存在而静默 no-op）。
未给该 flag 时 SHALL 只在**文件不存在**时写入**哨兵占位**（未接线 ⇒ 由下一条 Requirement 判红）。
`init --no-tests` SHALL 显式**不写**该文件，并在策略里写 **`tests.disabled: true`**（**这是唯一的 opt-out
字面**：`from_doc` 用 `or DEFAULT` 取默认值 ⇒ `""` / `null` / 缺省**都会**被读成「声明」）。

策略字段的**缺省语义**：**字段缺省 ⇒ 声明**（用默认路径）。⚠️ **出厂 policy 文档 SHALL NOT 物化
`tests` 键**——否则已接入的仓跑 plain `init` 会因「本次期望 ≠ 磁盘」而 exit 1（实测）。
（⇒ 已接入的仓会被立刻判；SHALL 在文档里给出补文件的迁移步骤。）opt-out 只在**新接入**时可用；
已接入的仓改 `policy.json`（不变集、状态 `M`）SHALL 需要一条 `protected_path_write` 解释事件。

该命令文件 SHALL **不进 `init` 台账**、SHALL **不进 `desired_files()`（即不参与冲突判定）**、
SHALL **不参与 `uninit` 的删除**。⇒ 接入方改命令之后，**再跑 plain `init` 仍 SHALL 成功**（不得 exit 1）；
改命令本身 SHALL 是一次普通 commit（不需要解释事件）。
⚠️ **已接入仓的 opt-out 摩擦**：`--no-tests` 只在**新接入**时可用；已接入仓改 `policy.json`
（不变集、状态 `M`）SHALL 需要一条 `protected_path_write` 解释事件——文档 SHALL 写明。

### Scenario: 给了命令就接线
- **Given** 一个新接入的仓，`init --test-command "uv run pytest -q"`
- **When** 检查命令文件与策略
- **Then** 命令文件存在且内容为该命令；策略声明了执行点；`check` 对该项判**绿**

### Scenario: 没给命令 ⇒ 哨兵
- **Given** 只跑了 `init`（没给 `--test-command`）
- **When** 运行 `check`
- **Then** **红**，且文案点名「执行点未接线（仍是哨兵）」

### Scenario: opt-out 不误伤
- **Given** `init --no-tests`（策略里为 `tests.disabled: true`）
- **When** 运行 `check`
- **Then** **不**因缺少执行点而红
- ⚠️ **边界**：`disabled` 只关 `check` **不关**门禁那一步——命令文件不在 ⇒ 门禁步骤跳过；
  若接入方想「连跑都别跑」，删掉命令文件即可。文档 SHALL 写明（否则会困惑「opt-out 了却还在跑」）。

### Scenario: 改命令不撞台账（可机械验证）
- **Given** 一个已接入的仓
- **When** 接入方直接改写命令文件的内容并提交
- **Then** `init` / `uninit` 的台账判定**不受影响**（该文件不在台账里）；`check` 仍判绿；
  并且**改完命令后再跑 plain `init` 仍 SHALL 成功**（不得 exit 1）

## Requirement: `check` 机械要求「执行点存在且已接线」

在策略**声明了执行点**的前提下，`check` SHALL 要求：① 该路径的**文件存在**；
② 它**去空白后非空**；③ 它**不含未替换的哨兵**。任一不满足 ⇒ SHALL 报错并**非零退出**。
（② 是必需的：只判 ①③ 时**空文件**会同时骗过 `check`（绿）与门禁（`sh -c ""` exit 0）⇒ 双重绿、零测试。）

该判定 SHALL **零依赖**（只做文件存在与字符串包含检查，SHALL NOT 解析 YAML、SHALL NOT 执行该命令）。

### Scenario: 执行点缺失 ⇒ 红
- **Given** 策略声明了执行点，但文件被删掉
- **When** 运行 `check`
- **Then** 非零退出，文案点名**路径**与「缺失」

### Scenario: 执行点为空 ⇒ 红
- **Given** 命令文件存在但是**空文件**（或全是空白）
- **When** 运行 `check`
- **Then** 非零退出，文案点名「执行点为空（未接线）」

### Scenario: `check` 不执行命令（边界）
- **Given** 命令文件内容是一条**必然留下痕迹/必然失败**的命令
- **When** 运行 `check`
- **Then** 该命令 SHALL NOT 被执行（无痕迹、无副作用），且判定只看文件与字符串

## Requirement: 门禁执行该命令，测试失败 ⇒ required check 失败

reusable workflow SHALL 读取命令文件并在**门禁的 job 内**执行该命令——**文件路径** SHALL 经 `env:` 传入、
命令 SHALL 在 `run:` 里**运行时读取**（SHALL NOT 把命令文本或文件内容做 `${{ }}` 插值：
插值发生在解析期 ⇒ 等于把接入方内容当 workflow 源码）。**文件缺失 _或_ 内容含哨兵时 SHALL 跳过执行**
（是否判红由上面的 `check` 决定）。

测试步骤 SHALL 与 `check` **处于同一个 job**（required 的粒度是 job ⇒ 接入方**无需新增任何平台操作**
即可让「测试失败 = 合不了」成立）；`check` 步骤 SHALL 排在测试步骤**之前**；测试步骤 SHALL 用
`if: ${{ !cancelled() }}`——理由是 ① 门禁红时**最需要测试反馈**（一次 CI 里看到两条问题）；
② run 被取消时不必再跑一遍测试。（`always()` 会连取消的 run 一起跑；默认语义则在 `check` 红时
完全不跑测试。⚠️ 曾有说法称 `always()` 会「掩蔽」`check` 的失败——**实测为假**：失败步骤 + 后续
`skipped` 步骤 ⇒ job 结论仍 `failure`。）

### Scenario: 结构断言（可机械验证）
- **Given** `gate.yml`
- **When** 用 YAML 解析它
- **Then** 存在读命令文件的 step；**文件路径**出现在 `env:` 里、`run:` 里不出现裸 `${{ }}`（尤其**不得**
  对文件内容/命令文本做 `${{ }}` 插值）；文件缺失**或内容含哨兵**时跳过；测试步骤用 `!cancelled()`
- **And** `gate.yml` 里的**路径**与**哨兵**字面量 SHALL 与 `constants.py` 的常量、`policy` 的默认路径
  **三处逐字一致**（否则 `check` 与门禁会出现「一边判红、一边静默跳过」的口径分裂）

## Requirement: 诚实边界（文档必须写清，否则算过度承诺）

文档 SHALL 写明：

1. `check` 只保证「**有一个已接线的执行点**」——**不保证**它真跑过，也**不保证**它跑的是真测试
   （`|| true`、`--collect-only` 都能骗过存在性判定）；「真跑了」由**平台侧 required check** 保证。
2. **PR 可以改掉自己的命令文件/CI 配置**（`.github/workflows/**` 不在保护路径、
   `required_approving_review_count: 0`）而 required check 依旧绿 ⇒ 承诺必须带这个限定。
3. 测试命令是**任意代码**，会在每个 PR（含 **fork PR**）的 runner 上执行。
4. **能力天花板**：走本 change 的执行点意味着测试跑在**别人的 job** 里——只有 `contents: read` 权限
   （reusable workflow 的权限不能超出 caller），**没有 `services:`、不能加自己的 `uses:` 步骤、
   不能上 matrix/缓存**，命令只能是**一行 shell**。需要这些能力的仓应当改用「自己的 workflow」
   （代价：自己再勾一次 required）。把「同 job」说成普遍更优即为**过度承诺**。

### Scenario: 文档不含无限定承诺（机械可验证）
- **Given** `README.md` / `docs/gate.md`
- **When** 按 `tests/test_docs.py` 的「同文件每处 X 都带限定（±2 行窗口）」范式扫描
- **Then** 每一处「拦住合并 / 合不了」都带上述限定之一

## Requirement: 不引入运行时依赖

实现 SHALL NOT 给 `witnessloop` 增加运行时依赖（`pyproject.toml` 的 `dependencies` 保持 `[]`），
SHALL 有一条测试钉住它。

### Scenario: 依赖为空
- **Given** 本 change 后的 `pyproject.toml`
- **When** 解析它
- **Then** `dependencies == []`

## Requirement: 产物契约变更（必须显式记录）

`init` 的产物由「**三个文件**」变为「三个 + **命令文件**」⇒ `docs/gate.md` 的表述与本仓
`tests/test_init.py` 的三文件断言 SHALL 一并更新；`uninit` SHALL **不删**命令文件。

### Scenario: 契约同步（可机械验证）
- **Given** `docs/gate.md` 与 `tests/test_init.py`
- **When** 检查产物清单
- **Then** 两者的表述与实现一致（命令文件在列、且被标注为「不参与 `uninit` 删除」）
