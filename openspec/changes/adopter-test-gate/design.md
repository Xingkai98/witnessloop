# Design: adopter-test-gate

> 状态：**草稿**（待设计 grill + 对抗验证收敛 → 停轮用户确认）。
> 依据 `proposal.md`（含三条立项前实测约束）。流程出处 `templates/grill.md`。

## 0. 一句话

让 `init` 接入的门禁**能跑接入方自己声明的测试命令**，并让它**真的能拦住合并**——
同时**必须**决定 `gate.yml` 的 ref / 发布策略（否则新接入方一 `init` 就坏，见 D5）。

## 1. 现状（实测，带 `文件:行号`）

| 事实 | 位置 | 说明 |
|---|---|---|
| caller 只跑 `check` | `initcmd.py:24-40`（`caller_workflow`） | 一个 `uses:` job，无 `with:`、无 steps |
| 门禁本体 | `.github/workflows/gate.yml` | `workflow_call`；已有 `base-ref` / `witnessloop-ref` 两个可选 input；作业 `check` |
| 本仓自己的测试 job | `.github/workflows/ci.yml` | `test` job 跑 `uv run pytest -q` + 打包冒烟——**是自测，不给接入方** |
| ref 钉在固定 tag | `constants.py:11` | `DEFAULT_GATE_REF = …gate.yml@v1`；`v1 == v1.5.0 == 843b691`，`origin/main == de51a01`（**领先 6 个提交**） |
| 运行时零依赖 | `pyproject.toml` | `dependencies = []`（pyyaml 只在 dev group，仅测试用） |
| caller 被台账管理 | `initcmd.desired_files` / `build_manifest` | caller 的 hash 进 `.witnessloop/init-manifest.json`，`uninit` 依它回滚；文件头写「请勿手改」 |

## 2. 决策（候选 · 待 grill 攻）

### D1 测试步骤住在 **reusable workflow**（`gate.yml`），由**可选 input** 驱动

- **否掉**「caller 里加第二个带 steps 的 job」：那是把 YAML 的维护责任推给接入方，
  且破坏 design §5.1 明写的「**极薄 caller**」契约（caller 只是 `uses:` 转发）。
- **否掉**「让 `check` 自己跑测试」：`check` 的性质是「判**流程证据**」，跑测试是另一件事；
  且 `check` 也在本地 / guard 路径上被调用，跑全量测试会污染它（慢、副作用、失败语义混淆）。
  这条写成 spec 的边界。
- 形态（丁）**`init` 另写一个独立的测试 workflow 文件**（如 `.github/workflows/tests.yml`，纯 steps、**不含
  `uses:`**）：完全不碰 `gate.yml` ⇒ **ref/版本问题自动消失**（D5 的硬约束不存在了），也不依赖 `workflow_call`
  的 input 声明语义。代价：接入方多一个文件要维护；`init` 要写一个带占位命令的模板；
  「极薄 caller」原则变成「两个各司其职的文件」（**未必是坏事**：测试本来就与 witnessloop 无关）。
  ⚠️ **这是 D1 的强竞争者**（它让 D5 整段作废）——grill 必须对它打分，不要只默认走 `gate.yml`。
- 形态（甲）：`gate.yml` 增 `workflow_call.inputs.test-command`（`required: false`，`default: ""`）。

### D2 **同一 job 还是独立 job** —— 关键取舍（Q1）

| | 甲：独立 `test` job | 乙：并入既有 `check` job 的后续步骤 |
|---|---|---|
| 接入方的平台操作 | **要再勾一次** required（第二个 job） | **零新增**（`gate / check` 已是 required） |
| 忘勾的后果 | 测试**跑了但不拦**——正是 issue #4 抱怨的形态换个位置 | 不存在这个静默面 |
| 职责/可诊断性 | job 名清晰、归因清晰 | job 名 `check` 不再只表示流程校验；失败**靠 step 名**区分 |
| 性能 | 与 check 并行 | 串行（check 很快，影响可忽略） |

- 平台事实：**required check 的粒度是 job，不是 step** ⇒ 乙 是唯一能「**零人肉步骤即拦住**」的设计。
- **倾向乙**（直击 issue 的「没人管」），但甲更干净——**交 grill 打分 + 停轮拍板**。

### D3 命令**从哪来**（单一事实源）—— Q2

- 甲：**policy 字段** `tests.command` + `init` 把它 materialize 进 caller 的 `with:`。
  ⚠️ 漂移：policy 事后改了，caller 不会跟着变（`init` 只增不改 + 台账 hash）⇒ 会出一个
  「policy 说跑 X、CI 实际跑 Y」的静默分歧（本仓最恨的那类）。**否**，除非同时提供 `check` 校验——
  而 `check` 零依赖、解析不了 YAML（约束 3）。
- 乙：**只住 caller**（`with: test-command: <cmd>`）。caller 本来就是 CI 的属性、接入方可读可改；
  代价：文件头「请勿手改」与台账 hash 会让「想改命令」的人撞上冲突（fail-closed，可按既有冲突流程处理）。
- 丙：`init --test-command "<cmd>"` 写入 caller（= 乙的便利入口），**不新增 policy 字段**。
- **倾向 乙/丙**（caller 是唯一事实源，避掉漂移面），并把 caller 头注释改成
  「这一行是**给你的**：填你的测试命令；改了之后 `init` 会报冲突（见 `docs/gate.md §1.1`）」。

### D4 默认行为：**空命令 = 跳过**（不是失败、更不是默认跑）

- 存量接入方与「不写测试的仓」行为**完全不变**（这是 D5 选「移动 tag」时唯一安全的形态）。
- 不做探测（猜 `pytest`/`npm test`）：显式声明优于魔法（写进 spec 的边界）。

### D5 ref / 发布策略 —— **本 change 必须一起决定**（Q3）

硬约束：`init` 若开始写 `with: test-command:`，而 caller 引用的 `@v1` 的 `gate.yml` **没有声明该 input**，
`workflow_call` 会直接报错（⚠️ 平台行为断言，**待 grill 查证**）⇒ **新接入方一 `init` 就坏**。

- 甲：**发新 tag**（如 `v1.6.0`）+ `DEFAULT_GATE_REF` 指向它 + README 安装/接入示例同步。
  语义最清晰、可回滚；存量接入方要**显式 bump**（改 caller 里那一行 `@v1`→`@v1.6.0`——那行在台账里，
  得走冲突流程或 `--force` 类操作，**要写清怎么改**）。
- 乙：把 **`v1` 改成移动 tag**（GitHub Actions 的 major-tag 惯例，多数 action 都这么做）。
  `init` 继续写 `@v1`（**不改常量**）；新接入方立刻拿到；存量接入方**下次 CI 就拿到**——
  ⚠️ 但他们拿到的行为必须**默认无变化**（D4 = 空则跳过 ✓），否则就是**静默行为变更**。
  代价：把「移动 major tag」变成发布纪律（要写进 README/发布说明，且**回滚只能是新 commit**）。
- 丙：本 change **只改 main 上的 gate.yml + init**，ref/发布策略**单独立 issue** 作为前置。
  ⚠️ 这条最省，但会让本 change 的价值**悬空**（存入量接入方拿不到），且新接入方仍会坏（除非同时把
  caller 里的 input 也拿掉）。**若选丙，必须连带选定「本 change 期间 init 暂时不写 input」**，否则不自洽。
- **倾向甲或乙**；具体哪条**交停轮拍板**（它影响所有接入方 + 触及发布习惯）。
  ⚠️ **若 D1 选丁（独立测试 workflow）⇒ 本节整段作废**（不碰 `gate.yml` ⇒ 无 ref 问题）。
  这是 D1 与 D5 的**耦合**：D1 的选择决定 D5 是否存在——两个决策**必须一起看**，别分开拍。
- 丁（D1 的另一条路）：**不动 ref**，因为根本不需要——这是选丁的**主要收益**。

### D6 本仓自己的自举**不受本 change 影响**（要写进文档，避免误读）

本仓的 caller（`.github/workflows/witnessloop.yml`）引用的是 **`@v1`** ⇒ 本 change 对 main 上 `gate.yml`
的改动**不会**改变本仓 PR 的检查行为（本仓另有 `ci.yml` 的 `test` job 跑测试）。选 D5 乙 之后**将来**才会到达。

### D7 安全写法：命令必须经 `env:` 传入，**不**直接内联进 `run:`

`run: ${{ inputs.test-command }}` 是**脚本注入**形态（GitHub 官方明确建议把 `${{ }}` 放 `env:`）。
本例的 input 来自接入方自己的 caller（相对可信），但**照最佳实践写**、并在文档里说明；
测试要用 pyyaml 断言「命令出现在 `env:` 里 / 不以裸 `${{ }}` 出现在 `run:` 里」。

### D8 文档影响

- `README.md`：接入段补「测试命令怎么给 + **空 = 跳过** + required 是**人工勾一次**（job 粒度）」；
  若 D5 选乙，补一句发布纪律（`v1` 是移动 major tag）。
- `docs/gate.md`：§1（目标仓长什么样 → caller 多了 `with:`）、新增一小节（测试 job 的语义与边界）。
- `docs/design.md §5.1`：caller 契约由「极薄」扩成「极薄 + 可选 `test-command`」。

## 3. 接线点（实现清单，依 D1–D5 定案）

- `.github/workflows/gate.yml`：新 input + 步骤（位置依 Q1）。
- `src/witnessloop/initcmd.py`：`caller_workflow()` 加 `with:` 段（依 D3/D4）+ 头注释调整。
- `src/witnessloop/constants.py`：`DEFAULT_GATE_REF`（依 D5 甲；乙则不动）。
- `tests/`：`test_gate_workflow.py`（pyyaml 结构化断言）+ `test_init*.py`（幂等 / 冲突 / 回滚）。
- 文档（D8）。

## 4. 风险

1. **R1（高，平台耦合）**：未声明 input ⇒ `workflow_call` 报错。**待 grill 查证**（本机跑不了 Actions）。
   若成立 ⇒ D5 是**硬前置**，不能拖。
2. **R2（中）**：D2 选甲 ⇒ 默认出现「测试跑了但不拦」——把 issue 的问题换了个位置（且更难发现）。
3. **R3（中）**：D3 选甲 ⇒ policy↔caller 漂移面（且 `check` 零依赖、验不了）。
4. **R4（中，须写进文档）**：测试命令是**任意代码**，会在**每个 PR**（含 **fork PR**）的 runner 上执行。
   这对「正常 CI」是可接受常态，但会让「外部贡献者的代码自动跑」——接入方应知道（GitHub 亦有
   「fork PR 需批准」的仓级设置）。**本 change 不替接入方决定**，只写清。
5. **R5（低）**：D2 选乙 ⇒ 失败归因靠 step 名，`gate / check` 这个 job 名不再只表示流程校验。
6. **R6（低）**：本仓自举不受影响（D6），但**文档不写清就容易被误读**。
7. **R7（低）**：D5 选乙（移动 tag）⇒ 存量接入方**下次 CI 就拿到新 gate.yml**；只要 D4=空则跳过就安全，
   但这是一条**新的发布纪律**，回滚只能靠新 commit。

## 5. 测试策略（TDD）

- **gate.yml**：pyyaml 解析（理由见 `tests/test_gate_workflow.py:32-34`：只 grep 子串钉不住「位置 + 取值」都重要的行）——
  断言：input 已声明且默认空；空时不执行 / 给了就执行；命令经 `env:` 传（D7）。
- **init**：caller 含 `with:` 段与命令；空命令时 caller **不含**该段（或含显式空值——二者择一钉死）；
  既有幂等 / 冲突 / `uninit` 回滚用例全绿。
- **回归**：全量 pytest 绿；本仓 `.github/workflows/witnessloop.yml` 与 `gate.yml@v1` 的关系有断言或注释（D6）。

## 6. Open Questions（停轮待用户确认）

- **Q1 测试步骤住哪**：甲 独立 `test` job（职责清晰，但接入方**要再勾一次** required，忘勾=跑了不拦）；
  乙 **并入 `check` job**（零新增平台操作 ⇒ 真能拦；代价：job 名语义变宽、失败靠 step 名归因）。
  **倾向乙**。例子见 D2 表。
- **Q2 命令声明在哪**：甲 policy 字段（漂移面）；乙/丙 **只住 caller**（`init --test-command` 作便利入口）。
  **倾向乙/丙**。
- **Q3 ref / 发布策略**：甲 发新 tag（清晰、要 bump）；乙 **把 `v1` 变成移动 major tag**（新接入方立刻拿到、
  存量下次 CI 拿到，**要求 D4=空则跳过**才安全）；丙 本 change 不动 ref（**会让本 change 价值悬空**，须连带
  让 init 暂时不写 input）。
- **Q4 默认开还是关**：**空 = 跳过**（推荐，存量零影响）vs 默认跑某个约定命令（需探测，见非目标）。
- **Q5 是否把「测试命令 = 任意代码、fork PR 也会跑」写成 README 的显式告警**（R4）：**推荐写**。
