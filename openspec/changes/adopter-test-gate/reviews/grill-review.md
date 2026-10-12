# Grill: adopter-test-gate 设计追问

> 零记忆独立审阅者产出。算法与格式依据 `templates/grill.md`（7 维追问 + 设计树求完备 + 第 4 步决策记录）。
> 立场：**挑战而非确认**——不是复述 design，是逐条去打它。
> 原稿的三条「立项前实测约束」+ 全部平台断言 + D1–D8 都在 `/tmp` 独立副本里复现；被审 worktree **全程只读**，
> 唯一仓内写入是本文件（`git status` 见文末「仓内写入」）。
>
> **一句话结论**：**问题是真的、值得做**（issue #4 的核心实证我独立复核成立，见 CD-1）；
> 但原稿的**方案轴选错了地方**——现在这套设计把「接入方的测试」塞进 witnessloop 自己的
> reusable workflow 接口里，于是被迫连出一个**它其实不需要的** ref/发布决策（D5），
> 并且在**三条它没走到的设计树节点**上留下硬伤：
> ① **新能力到不了存量接入方**（实测：`init` 报「幂等，无改动」，新文件根本不落盘）；
> ② **D3 的「改这一行是给你的」是一条死锁**（实测：`init` 与 `uninit` **同时** exit 1，无出口）；
> ③ **D5 乙 的代价被严重低估**——`gate.yml@v1` 同时钉着**被 uvx 安装的 witnessloop CLI 版本**
> （`gate.yml:19-23`），移动 `v1` 会把积压 6 个提交里的**多条「对**接入方**是行为变更」**
> （`README.md:105-113` 自述，含「历史 change 会**新增一条红**」）**一次性**推给所有存量接入方。
> ⇒ **D5 的推荐是甲（新 tag），不是乙**；D1 的推荐见 Q1（丁/戊 优先，甲 次之，**己** 最省且是唯一本周就能帮到存量接入方的路）。

## Reviewer

- run id: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`
- 时间: 2026-10-12T15:43:59Z
- 被审 revision: `7099deb41238`（分支 `adopter-test-gate/2026-10-12`）
- 方法（可复现）：
  - 副本 `/tmp/grill-atg`：`cp -a` 后 `rm -f .git && git init -q && git add -A && git commit -qm base`
    （被审 worktree 的 `.git` 是 `gitdir:` 指针文件，不隔离会写回原仓），再 `rm -rf .venv && uv sync`。
  - 基线独立复现：`uv run pytest -q` = **431 passed**（与任务书一致）。**全程未改任何测试文件**，
    所以下面的「实测」都是**未改动工具**在真仓里的行为，不是模拟补丁的输出（唯二例外是 SIM 1/SIM 2 与
    Scenario A/B，那几条**明确标注**是在副本里给 `caller_workflow()` 打了补丁来模拟「本 change 之后」的工具）。
  - 平台事实用 `gh` CLI 对**真实仓**取证（`Xingkai98/witnessloop` / `Xingkai98/wl-test`），
    比读文档强：branch protection、check run 名、job 列表、acid test 仓的工作流清单。
  - 网络只用于查证「未声明 input」的平台行为（两处第三方真实 issue），结果**明确标注置信度**。

## Confirmed Decisions

- **决策**：**issue #4 的问题成立，且比原稿写得更硬**——「接入方的测试没有任何自动执行点」在真实仓里
  可机械复核：`Xingkai98/wl-test` 只有 `.github/workflows/witnessloop.yml` 一个工作流，而 acid test 的 PR 运行
  `38040394810` 的 job 列表**只有 `gate / check` 一项（9 秒，success）**，没有任何测试 job
  ⇒ `tests/test_greeting.py` 的 13 个用例**一次都没跑**（口径与 `docs/reviews/m3-acid-test.md:98` 的「13 tests」一致）。
  理由：这是本 change 唯一的立项依据，必须独立复核而不是引用作者自述。来源: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`
- **决策**：**D2 的平台前提成立，且这是本设计里唯一真正约束方案形状的事实**——
  `gh api repos/Xingkai98/witnessloop/branches/main/protection` 返回
  `required_status_checks.contexts = ["gate / check"]`（`strict: true`、`enforce_admins: true`），
  即 required 的粒度是**一个 job 级 context 字符串**，不是 step、不是 workflow 整体。
  理由：这决定了「并入既有 `check` job（乙）」是**唯一零新增平台操作**的形态；选独立 job（甲/丁）
  必然多出一个 context 要人工勾——而**没勾就是「测试跑了但不拦」**，正是 issue #4 的形态换个位置。
  来源: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`
- **决策**：**D5 的硬前置成立，且严重度被原稿低估**：caller 传**未声明**的 input ⇒
  run 变成 **`startup_failure`（零 job、不点名是哪个 input）** ⇒ `gate / check` 这个 check run
  **根本不会产生** ⇒ 若它已是 required，PR 停在「Expected — waiting for status to be reported」上，
  **既拦人也无日志可查**（比「红」更难诊断）。本仓已有同形态先例：`docs/design.md:55` 记录过一次
  「caller run **0 个 job**、报 workflow file issue」。
  理由：D5 不是「要不要现在就决定」，而是「决定错会让新接入方**首个 PR 就卡死且无从诊断**」。
  来源: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`（置信度见 CRQ-5）
- **决策**：**D3 的「命令只住 caller」方向对，但落地方案缺一块必须补的机制：`test_command` 要进台账。**
  实测：`init --test-command "pytest -q"` 在**已接入仓**上直接 **exit 1 冲突**（Scenario A，未打补丁的工具
  走的就是这条既有路径），而新接入仓用过 `--test-command` 之后，**任何一次不带该 flag 的 plain `init`
  也会 exit 1 冲突**（Scenario B 后半）。
  理由：`gate_ref` 早就踩过同一个坑并已用「台账 recall」修好（`initcmd.py:131-141` + `initcmd.py:163`）；
  命令必须照抄这条修法，否则 D3 的「便利入口」对**唯一需要它的那批人（存量仓）不可用**，
  且会给新仓留下一个**永久冲突**的 `init`。
  来源: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`
- **决策**：**A2 的结论成立但表述要改**：`v1^{commit} == v1.5.0^{commit} == 843b691`、
  `git rev-list --count v1..origin/main` = **6**、`v1` 是 **annotated** tag（对象 `19ac94c`）、且 `v1` 是 main 的祖先。
  但「`v1` 是**固定** tag」与 tag 自己的注记冲突：`git tag -n99 v1` → 「witnessloop v1（**滚动大版本**，当前指向 v1.5.0）」。
  理由：这直接改 D5 的**代价评估**——`v1` 的语义本是滚动（历史上与 `v1.5.0` 同 commit），是**最近 6 个提交没滚**；
  所以「乙 = 移动 tag」不是发明新纪律，而是**恢复 tag 自称的惯例**；反过来「甲 = 只在新 tag 上发」才是改惯例。
  来源: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`
- **决策**：**A3「运行时零依赖」是硬约束，但它的推论「所以 `check` 只能退化成子串匹配」不成立。**
  实测：`uv build` 出的 wheel 的 METADATA **没有任何 `Requires-Dist` 行**；`grep -rn yaml src/` 零命中。
  理由：存在**第三条路**——让 **workflow 在运行时读仓内文件**（runner 上有 `jq`/`python3`），
  `check` 完全不参与 ⇒ 零依赖约束不受影响，也不需要「解析 YAML」。作者把「必须由 `check` 校验」
  与「必须有单一事实源」绑死了，见 CRQ-8 / Q8。
  来源: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`
- **决策**：**「新增 init 产物」这件事对存量接入方是死的**——任何「让 `init` 多写一个文件」的方案（丁）
  都**到不了**已接入仓：实测在已接入仓上跑带新产物的 `init`，输出是
  **「init：已接入 witnessloop（幂等，无改动）。exit=0」，而新文件没有落盘**（`_already_initialized`
  在无 drift、无 conflict 时直接返回，`initcmd.py:280-281`）。
  理由：这是设计树上一个**所有候选方案都要过的节点**，原稿完全没走到——它决定了丁能不能算「省」。
  来源: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`
- **决策**：**本 change 命中自身门禁的正面要求**：它改 `src/**`（`require_change_for` 命中）⇒
  除 `stage=grill` 外还**必须**有 `stage=grill-adversarial` 的 manifest（`templates/grill.md:195-200`，issue #16）；
  而 `gate.yml`/`docs/**`/`README.md` **不在**本仓 `protected_paths`（`.witnessloop/policy.json`：
  `["openspec/specs/**", ".witnessloop/**"]`）⇒ 改它们**不需要** `protected_path_write` 事件。
  理由：dimension 7（门禁改自己会不会死锁/误伤）逐条核过：本次写操作**不**触发自己要新增的规则，但它触发了
  既有的 grill-adversarial 机械要求（`README.md:105-113` 那条「对**接入方**是行为变更」正是这条）。
  来源: `grill-reviewer-adopter-test-gate-2026-10-12T154359Z`

## Code-Resolved Questions

- **CRQ-1｜「改了 caller 会怎样」——`init` 与 `uninit` 同时 fail-closed，且没有出口**（这是任务书要求回答、
  作者未回答的问题）。实测（未打补丁的工具，真仓 `/tmp/exp1`）：给 caller 加两行
  （`    with:` / `      test-command: "pytest -q"`，即 design.md:59-60 鼓励的那种改动）之后：
  - `init` → `exit 1`，`init：已接入，但 init 创建的文件被改动过（拒绝覆盖）：` + diff（`initcmd.py:241-258`）；
  - `uninit` → `exit 1`，`uninit：以下文件被改动过，拒绝删除：` + 同一份 diff（`uninitcmd.py:71-89`）；
  - **只删台账也不行**：`rm .witnessloop/init-manifest.json` 后 `init` 落到另一条分支
    `init：检测到冲突（只增不改，拒绝覆盖已有文件）` + `exit 1`（`initcmd.py:169-179`）；
  - **唯一可行**的恢复：把 caller 恢复成**逐字节**等于生成物 + 删台账（实测通过）——而「逐字节」对存量
    接入方是**不可知**的（那是他们当初那个 CLI 版本的生成物；本 change 之后更不可知，见 CRQ-2）。
  证据：`initcmd.py:207-281`、`uninitcmd.py:20-98`；实测输出见本条。附带一处**文案缺陷**：
  `uninitcmd.py:85-88` 说「请人工确认这些改动后重试」，但**没有任何 flag/流程**能表达这次确认，
  「重试」的结果逐字相同 ⇒ 这句指令不可满足。
- **CRQ-2｜本 change 计划里的「头注释调整」= 对所有存量接入方的一次 `init` 故障**。`design.md:59-60`、
  `tasks.md:24`（B1）都写「把 caller 头注释改成『这一行是给你的』」。实测（SIM 2，副本里给
  `caller_workflow()` 只加一行头注释）：已接入仓（**文件未手改过**）跑 plain `init` →
  `init：检测到冲突（已接入，但本次指定的内容与已落地不同…要更换 policy 请先 uninit）`、**exit 1**。
  证据：`initcmd.py:260-278` 的 R2 冲突分支（磁盘 vs 本次期望）+ 实测输出。
  ⇒ 「头注释调整」不是零成本细节，它等价于「每个存量接入方的 `init` 立刻坏掉」，且恢复路径见 CRQ-1。
- **CRQ-3｜`test-command` 这个名字在 GitHub 表达式里合法（不必写 `inputs['test-command']`）**。
  用本仓自己的 CI 反证：`v1` 的 `gate.yml:49` 就有 `${{ inputs.base-ref }}`（点号解引用带连字符的 input 名），
  而 PR #17 的 `gh pr checks` 显示 `gate / check  pass  10s` —— 真跑过且成功。
  证据：`gh api`/`git show v1^{commit}:.github/workflows/gate.yml`（第 14、19、49、58 行）+ `gh pr checks 17`。
- **CRQ-4｜`with:` 是 caller 向 reusable workflow 传参的唯一正确键**（`uses:` job 允许的键只有
  `name/uses/with/secrets/needs/if/permissions`），所以 D1 甲 / D3 乙 的形态在语法上都对。
  证据：平台语法规则（与 CRQ-5 同源检索结果一致）；本仓 `gate.yml:11-23` 的 input 声明形状。
- **CRQ-5｜未声明 input 的行为：`startup_failure`、零 job、不点名（置信度：中高，非官方明文）**。
  两处**独立的第三方真实 issue** 复述了同一形态：编辑器 linter 报
  `Invalid input, <name> is not defined in the referenced workflow`，运行时是
  「`startup_failure`、零 job、不说哪个 input 错了」，并把「callee 必须在 caller 之前落地声明」列为**顺序规则**；
  一处还明确对比「composite action 只 warn，reusable workflow 是 strict」。
  **诚实边界**：我**没有**在 GitHub 官方文档里找到这句行为的明文（`docs.github.com` 的
  reusing-workflows 页面对「未声明 input」只字未提，只讲了类型必须匹配），也**无法在本机跑 Actions 做端到端实测**；
  判断依据是上述第三方复述 + 「编译期校验」的机制描述 + 本仓 `docs/design.md:55` 已记录过的同形态（0 job、报 workflow file issue）。
  ⇒ **结论仍按「会导致 run 无法启动」设计（fail-closed 方向），但把「官方明文」这个说法从文档里去掉**。
  证据：见文末「Sources」；`docs/design.md:55`。
- **CRQ-6｜`guard` 不调用 `check` ⇒ `design.md:29` 的理由句是错的（结论可留）**。
  `guardcmd.py` 只 import `constants/contract/evidence/paths/policy/gitutil`（`guardcmd.py:29-33`），
  `cli.py:153-160` 把 `guard` 与 `check` **分别**分派。所以「`check` 也在本地 / guard 路径上被调用」
  不成立——共享的是**判定库**，不是 `check` 这个动词。
  证据：`src/witnessloop/guardcmd.py:22-33`、`src/witnessloop/cli.py:153-160`。
- **CRQ-7｜A5.4 那条断言若按字面实现，会在**现有** `gate.yml` 上直接红**。
  实测（pyyaml 遍历 `jobs.*.steps[*].run`）：`gate.yml:57-58` 的 `run:` 里就有**裸** `${{ inputs.witnessloop-ref }}`
  （同一 step 的 `inputs.base-ref` 却规规矩矩走了 `env:`，`gate.yml:48-50`）。
  ⇒ `tasks.md:19`（A5.4）必须**限定到新增的测试步骤**，或**顺手把 `gate.yml:58` 也改成 env**（后者才是自洽的）。
  证据：实测脚本输出（`job=check step=2 name='witnessloop check' run 里出现裸 ${{ }}`）。
- **CRQ-8｜「单一事实源 + 零漂移」有一条不用改 `check`、也不用改接口的第三条路**：
  把命令放进仓内一个文件，由 **workflow 在运行时读**（`gate.yml` 的 step 里 `cat`/`jq`，
  runner 自带 `jq`/`python3`）。这样 (a) `check` 完全不参与 ⇒ 零依赖约束不动；
  (b) 不存在「policy 改了 caller 不变」的漂移面（每次运行读的是 PR 检出出来的当前值）；
  (c) `workflow_call` 的 **input 接口不必变** ⇒ CRQ-5 那类 startup_failure 与 D5 的**接口部分**一起消失。
  代价与残留：**step 本身仍在 `gate.yml` 里** ⇒ 「存量接入方怎么拿到这个 step」这个 ref 问题**还在**（见 Q3）。
  证据：`gate.yml:25-26`（permissions）、`policy.py:30-41`（默认 `protected_paths` 含 `.witnessloop/**`）、
  `policy.py:88-110`（`from_doc` 用 `.get()` 读已知键，**未知字段被忽略**——所以往 policy 里加字段不会让旧 `check` 报错）。
- **CRQ-9｜D3 的「命令住哪」有一个隐藏地板：本仓/默认 policy 里 `.witnessloop/**` 是受保护路径**。
  ⇒ 命令若住 `.witnessloop/test-command`（或 `policy.json`），**每次改命令都要写一条 `protected_path_write` 解释事件**
  （`policy.py:18-23` 的不变集还额外把 `policy.json` 钉成**不可移除**的保护路径）。
  住 caller 的 `with:` 则**不触发**任何事件（`.github/**` 不在默认 `protected_paths`，也不在 `require_change_for`）。
  证据：`.witnessloop/policy.json`、`src/witnessloop/policy.py:18-23,30-41`、`src/witnessloop/constants.py:27-36`。
- **CRQ-10｜「三文件」是被钉住的契约，选丁就会破它（而且有个更省的位置）**。
  `docs/gate.md:9`「`witnessloop init` 只写三个文件」、`tests/test_init.py:18`（`test_init_creates_three_files`）、
  `tests/test_init.py:72`（`set(by_path) == {POLICY_PATH, GATE_WORKFLOW_PATH, INIT_MANIFEST_PATH}`）都按 3 个文件写死。
  ⇒ 若选丁，**spec delta 必须显式记这条契约变更**（当前 `spec.md` 里一个字都没有），且 `uninit` 的回滚面要跟着扩。
  证据：`docs/gate.md:9`、`tests/test_init.py:18,72`、`openspec/changes/adopter-test-gate/specs/adopter-test-job/spec.md`（无对应 Requirement）。
- **CRQ-11｜`gate.yml` 自 `v1` 起**从未改过**，`initcmd.py`/`constants.py` 却改了 6 次**。
  `git log --oneline v1..origin/main -- .github/workflows/gate.yml` **空**；
  同范围 `-- src/witnessloop/initcmd.py src/witnessloop/constants.py` 列出 6 个提交（含 `46`… 即 `442a2f7 dogfood-bootstrap（+ init --policy）`）。
  证据：上述两条 git 命令。⇒ 本 change 是**第一次**面对 gate.yml 的发布策略；而 `README.md:66` 已经诚实记过
  同一件事的另一面：「`init --policy` 是接入期新增的动词选项，**尚未随 `@v1` 发布**」。
- **CRQ-12｜原稿的「本仓自举不受影响」（D6）在**今天**成立、在**选乙之后立刻变假**，而 C2 想钉的是后者**。
  实测：`.github/workflows/witnessloop.yml:14` 确实 `uses: …gate.yml@v1`（与 `caller_workflow()` 产出逐字一致）；
  本仓 main 的保护规则里 required context 就是 `gate / check`。一旦 `v1` 移动，本仓自己的 caller 会**立即**执行
  新 `gate.yml`（CLI 版本也一起，因 `gate.yml:19-23` 的 `witnessloop-ref` 默认 `v1`）。
  证据：`gh api repos/Xingkai98/witnessloop/branches/main/protection`、`.github/workflows/witnessloop.yml:14`、
  `git show v1^{commit}:.github/workflows/gate.yml | sed -n '19,23p'`。

## Open Questions

> 原稿的 Q1–Q5 我逐条接手重写（保留其编号），**Q6–Q8 是原稿没问到、但设计树上有下游依赖的**。
> 全部只给推荐，不替用户拍板。

- **Q1（原 Q1 重写）测试的**步骤**住哪**：甲「`gate.yml` 加 input + 步骤」／丁「`init` 另写独立测试
  workflow 文件」／**戊（新增，丁的变体）**：文件由 `init` **种一次**（不存在才写、**不进 hash 台账**、不参与冲突与
  `uninit` 删除）／**己（新增，零代码）**：只发 `templates/adopter-tests.yml` 可复制模板 + README 配方，`init` 输出里提一句。
  | | 接口/ref 耦合 | 命令可日常改 | 到达**存量**接入方 | 新契约成本 |
  |---|---|---|---|---|
  | 甲 | 有（必须同时决定 D5） | 撞台账死锁（CRQ-1） | 需 tag 移动或手改 ref | `with:` 进 caller |
  | 丁 | **无** | 撞台账死锁（同乙） | **不可达**（CRQ-7/CD-7） | 破「三文件」契约（CRQ-10） |
  | 戊 | **无** | **自由**（不台账） | 仍不可达（同丁） | 新增「种子文件」语义 |
  | 己 | **无** | **自由**（是接入方自己的文件） | **可达**（自己拷） | 零 |
  - ➡️ **推荐答案：己 为主、戊 为辅（新仓自动种一份、存量靠文档），甲 只在「必须住 gate.yml」时才考虑；
    D5 因此可以不进入本 change。** 理由：required check 的勾选在**所有**方案里都是人工的（CD-2），
    所以本 change 真正要交付的产品是「一份**约定正确**的 YAML + 文档」，不是 `workflow_call` 的接口；
    丙（policy 字段 + `check` 校验）被 A3 正确否掉，但 CRQ-8 说明「零依赖」并不排斥「workflow 运行时读文件」。
  - **具体例子**：新接入方 `acme/web`（Python，`pytest`）——己：`cp templates/adopter-tests.yml .github/workflows/tests.yml`，
    改一行 `run: pytest -q`，在 branch protection 里勾 `test`；**同一天**已接入的 `Xingkai98/wl-test`
    也照抄同一份模板即可拿到执行点（它今天只有 `witnessloop.yml` 一个 workflow，实测）。
    甲：`wl-test` 要拿到新步骤必须**先**有人移动 `v1`（D5），否则它的 `@v1` 永远只有 `check`。
- **Q2（原 Q2 重写）命令**声明在哪**：乙/丙「只住 caller（`with: test-command`）」／甲「policy 字段」／
  **甲′（新增）**：不新增 input，`gate.yml` 在运行时读仓内文件。
  - ➡️ **推荐答案：乙/丙 方向 + 一条硬补丁**——`test_command` 必须在 `init` 台账里留一份
    （照 `gate_ref` 的 recall 做法，`initcmd.py:131-141`/`:163`），否则**存量仓用不了这个入口、
    新仓的 plain `init` 永久冲突**（CD-4 实测）。若愿意多花一点，甲′ 更好：把命令放
    **既不在 `protected_paths`、也不在 `require_change_for`** 的位置（如 `.github/wl-test-command.txt`，
    CRQ-9），可以同时消掉「改命令撞台账」与「改命令要写解释事件」两种摩擦。
  - **具体例子**：接入方把 `pytest -q` 改成 `uv run pytest -q`（加了 uv 的习惯）——乙：手改 caller
    ⇒ `init`/`uninit` 双双 exit 1（CRQ-1），他们只能靠「记得别再跑 init」；甲′：改那个小文本文件，
    `init`/`uninit` 都不受影响，CI 下一次 PR 即生效。
- **Q3（原 Q3 重写）ref / 发布策略**：甲 发新 tag（`DEFAULT_GATE_REF` 指过去）／乙 把 `v1` 变成移动 tag／丙 单独立 issue 作前置。
  - ➡️ **推荐答案：甲。乙 的最大代价原稿没写**：`gate.yml:19-23` 的 `witnessloop-ref` **默认值是 `v1`**，
    而 caller 从不传它 ⇒ `@v1` 这个 tag **同时决定 gate.yml 的内容**和**被 `uvx` 装下来的 witnessloop CLI 版本**。
    移动 `v1` ⇒ 积压的 6 个提交里那些**「对**接入方**是行为变更」**（`README.md:105-113`，含
    「历史 change 若缺 `stage=grill` manifest 会**新增一条红**」）**一次性静默到达所有存量接入方**。
    「D4=空则跳过」只覆盖**新增的测试步骤**，完全不覆盖这一层 ⇒ 原稿「只要 D4 空则跳过就安全」这个论证**不成立**。
    乙 要安全，前提是**先把这 6 个提交的行为变更作为一次发布**跟用户逐个确认——那是另一个 change 的事。
    若最终选甲：**必须在同一 change 内**把「存量接入方怎么升」写清（改 ref 会撞台账：CRQ-1）。
  - **具体例子**：`acme/web` 已接入、`@v1`。今天它的 PR 是绿的；若把 `v1` 移到一个「要求每个 change 都有
    `stage=grill` manifest」的主线 commit，**它那个只改了 `README.md` 就没建 change 目录的历史分支**下次
    PR 立刻红（红线来自 `check` 的新校验，与测试命令毫无关系）——接入方完全无从归因。
- **Q4（原 Q4）空命令默认**：空 = 跳过（推荐）vs 默认跑约定命令（需探测，非目标已否）。
  - ➡️ **推荐答案：保留「空 = 跳过」，但**必须**加一条**可见性要求**，并且它该进 spec 而不是只进 README。
    （见 Q7；理由：空=跳过 + required 绿 = issue #4 的形态**带上一层「已勾 required」的安全感**。）
  - **具体例子**：接入方照文档勾了 required、以为安全，但命令一栏因为复制粘贴时丢了引号变成了空串
    ⇒ 每个 PR 都是绿的，测试一个都没跑——**与今日唯一的差别是多了一个「看起来在保护你」的绿勾**。
- **Q5（原 Q5）文档告警**：是否把「测试命令 = 任意代码、fork PR 也会跑」写成显式告警（推荐写）。
  - ➡️ **推荐答案：写，并且**再补一条同族且更贴近本设计的告警**：**PR 可以改自己的 caller**。
    `.github/workflows/**` **不在**本仓 `protected_paths`、branch protection 实测
    `required_approving_review_count: 0` / `require_code_owner_reviews: false` ⇒ 一个 PR 可以把
    `with: test-command:` 那两行删掉（或改成 `pytest -q || true`），而 required check 依旧绿。
    这是**既有**边界（不是本 change 引入），但本 change 的 spec 写了「测试失败 SHALL 拦住合并」，
    不写清这条就会**过度承诺**。建议同时给「把 `.github/workflows/**` 交给 CODEOWNERS」这条可选加固。
  - **具体例子**：PR 作者（正是门禁要防的那个 agent）在自己的分支里删掉 caller 的 `with:` 两行，
    推上去，`gate / check` 绿，合并——测试从未运行，且**没有任何机制看得出来**。
- **Q6（新增）存量接入方**怎么升级**（本 change 缺这条，且它是所有方案的共同瓶颈）。
  - ➡️ **推荐答案：把「怎么到达存量仓」写成一条显式交付物**，三选一：
    ① 选己/戊（无需工具改动，文档即交付）；② 台账记 `version` 与 `test_command`，`init` 对缺失的
    **非台账产物**补种（改 `_already_initialized`，让它写「目标存在但缺失且不由 hash 约束」的文件）；
    ③ 提供 `init --upgrade`（改台账语义，最重）。**不要**依赖「先 `uninit` 再 `init`」——实测
    `uninit` 会删掉 `.witnessloop/policy.json`（`uninitcmd.py:91-95` 会删台账里的**每一个**条目），
    而本仓自己的 policy 是 `init --policy <仓外 seed>` 写的、seed **不入库**（`README.md:58`、
    `docs/gate.md:43`）⇒ 那条路会**静默丢掉定制 policy**（本仓自己就是受害者）。
  - **具体例子**：接入方想加测试命令，文档让他「先 uninit 再 init」——他照做，`uninit` 输出三行删除、
    一切正常，`init` 之后 policy 变回出厂默认（`require_change_for` 从 `["src/**","templates/**","plugin/**"]`
    退回 8 条默认、他定制的 `protected_paths` 没了），**没有任何提示说配置被重置了**。
- **Q7（新增）「空 = 跳过」要不要在 job 里留**运行时可观测信号**？
  - ➡️ **推荐答案：要，而且成本几乎为零**：空命令时打印一行 `::notice::`（或写 step summary）
    「未声明测试命令，本 job 只跑了流程校验」，非空时把**实际执行的命令**回显进日志/summary。
    这不改变任何退出码语义（仍绿），只是把「静默」变成「可看见的静默」。
  - **具体例子**：`test-command: "pytest --collect-only"`（一个很常见的粘贴失误——收集 13 个用例、跑 0 个、
    exit 0）⇒ 门禁**永远绿**。本仓最恨这类「永远绿的断言」（`events-readpoint-fix` 那轮 grill 的原话）。
    有了回显，至少日志里躺着一行 `ran: pytest --collect-only`。
- **Q8（新增）甲′ 的命令文件该放哪**（若采纳 CRQ-8 的「运行时读文件」）。
  - ➡️ **推荐答案：放既不在 `protected_paths` 也不在 `require_change_for` 的路径**（如 `.github/wl-test-command.txt`），
    **不要**放 `.witnessloop/**`（默认受保护 ⇒ 每次改命令都要写 `protected_path_write` 事件，CRQ-9）
    也**不要**塞进 `policy.json`（它是不变集里的不可移除保护路径）。若坚持住 policy，就得接受
    「改测试命令 = 一次受保护写入 + 解释事件」这个仪式，并写进文档。
  - **具体例子**：接入方一周里调了三次测试命令（加 `-x`、改到 `uv run pytest`、加 `-k smoke`）——
    住 `.witnessloop/` 的方案要写三条解释事件并解释为什么改命令算「受保护写入」；
    住 `.github/` 的方案是三次普通 commit。

## User Confirmation

> **本小节刻意留空**：按 `templates/grill.md` 的时序，停轮（第 6 步）发生在**设计对抗验证收敛之后**；
> 截至本文件产出（2026-10-12T15:43:59Z）**尚未停轮**，因此**没有任何用户答复**可记。
> 审阅者**不得**替用户拍板，也不得把自己的推荐答案当成用户的确认
> ——Q1–Q8 由作者在停轮后逐条回填（格式：`- **Qn**: 用户答复：…；确认时间: …`）。
> 机械提示：`check` 的正文校验在此阶段会对 Q1–Q8 各报一条「未经用户确认」，这是**预期状态**，不是本文件的缺陷。

## 风险

- **R8（高，平台耦合，原稿 R1 的加严重版）**：未声明 input ⇒ `startup_failure`（**零 job**）⇒
  required check **永不报告** ⇒ PR 停在「Expected — waiting for status to be reported」，
  **既拦人也无任何日志可看**。最危险的组合是**文档教人手改 caller 填命令**（`design.md:59-60`）
  + 存量接入方仍钉在**冻结的** `@v1`：照做的结果是**每个 PR 都卡死**，且症状与「测试命令写错了」毫无相似之处。
  缓解：选甲时把「先升 ref、再填命令」写成**有顺序的两步**，或干脆选丁/戊/己（不碰接口）。
- **R9（中高，安全边界，须写进 spec）**：PR 可修改自己的 caller/测试 workflow
  （`pull_request` 用的是 merge commit 的工作流文件；`.github/workflows/**` 不在保护路径；
  `required_approving_review_count: 0`）⇒ 「测试失败 SHALL 拦住合并」**只在 PR 不改自己 CI 的前提下成立**。
  （此条**未做端到端实测**：需要构造真 PR，超出只读约束；依据是平台语义 + 上述保护规则实测。）
- **R10（高，可用性）**：**台账死锁**：任何对 `init` 产物的一行手改，会让 `init` 与 `uninit` **同时** exit 1，
  且**没有**任何 flag 能表达「我确认这次改动」（CRQ-1）。本 change 的 D3 却把「手改这一行」当**正常用法**写进文档，
  等于把一个死锁包装成特性。缓解：命令不落台账（甲′/戊/己 中的任何一个）+ 文档补一条真正的恢复步骤。
- **R11（中）**：「新产物到不了存量仓」不是丁独有的问题，而是**任何**「`init` 多写一个东西」的方案的通病
  （实测 CD-7）。若本 change 的验收只在新仓上做，这个洞会**一路绿到用户手上**。
- **R12（中）**：D5 乙 会把 `witnessloop-ref` 默认值一起换掉（`gate.yml:19-23`）⇒ 存量接入方拿到的
  **不只是新步骤，还有一份新 CLI**。原稿的 R7 只算到「新 gate.yml 到得静默」，没算到这一层（见 Q3）。
- **R13（中，测试语义）**：**「空 = 跳过」与「测试步骤在 `check` 之后」会互相遮挡**：选 D2 乙（并入 `check` job）时，
  默认 step 语义下 **`check` 步骤失败 ⇒ 后续测试步骤根本不执行** ⇒ 门禁红的时候恰好是接入方最想要测试反馈的时候。
  反过来若用 `if: always()`，测试的失败又会掩盖 `check` 的失败信息。这条（失败交互与顺序）在 D2 与 A4 里都没定；
  建议在 A4 里把「失败交互」显式钉死（并写成 spec 的一条 Scenario）。
- **R14（中，能力天花板）**：reusable workflow 的权限**不能超出 caller**，而 witnessloop 自己的 `gate.yml:25-26`
  只声明 `contents: read` ⇒ 接入方**无法**为自己的测试要 `id-token: write`（OIDC）/`packages: read`/
  `pull-requests: write` 等（除非 witnessloop 替他们把这些权限写进自己的门禁文件——那是坏边界）。
  这是选丁/己（接入方自己的 workflow）的**技术优势**，原稿完全没提。
- **R15（低-中，契约）**：选丁会破「只写三个文件」的既有契约（`docs/gate.md:9`、`tests/test_init.py:18,72`），
  必须进 spec delta（CRQ-10）；否则又是一次「文档/测试各说各话」的漂移。
- **R16（低，测试写法）**：`tasks.md:19`（A5.4）若按字面写「`run:` 里不出现裸 `${{ }}`」会在**现有**
  `gate.yml:57-58` 上直接红（CRQ-7）；这条必须限定作用域，否则实现者会以为「断言写错了」而把它放宽成 grep。
- **R17（低，自举）**：本 change 改了 `caller_workflow()` 的字节之后，**本仓自己的 init 台账**
  （`.witnessloop/init-manifest.json` 里 `witnessloop.yml` 的 sha）与磁盘内容不再一致——
  `check` 不校验 init 台账所以不会红，但本仓此后**任何** `init` 都会撞 CRQ-1 的死锁，
  而恢复路线（`uninit`→`init`）会**丢掉定制 policy**（seed 不入库，`README.md:58`）。
  建议本 change 顺手把 seed 入库（或加一条 `init --force-caller`），否则下一轮改 caller 的人会踩同一个坑。
- **R18（低，理由句精度）**：`design.md:29`「`check` 也在本地 / `guard` 路径上被调用」为假（CRQ-6）。
  结论（不让 `check` 跑测试）仍成立，但别用这条当论据——审阅者一旦发现理由句是错的，会连带怀疑其余四条。

## 原稿被证伪的事实

1. **`design.md:29`**「`check` 也在本地 / `guard` 路径上被调用」——**假**。`guardcmd.py:22-33` 只 import
   `constants/contract/evidence/paths/policy/gitutil`，`cli.py:153-160` 把 `guard` 与 `check` 分别分派；
   `guard` **不调用** `check`。共享的是判定库（`evidence`/`policy`），不是动词。
2. **`proposal.md:25` / `design.md:18`**「`v1` 是**固定** tag」——**表述不准**。`v1` 是 annotated tag，
   注记原文是「witnessloop v1（**滚动大版本**，当前指向 v1.5.0）」（`git tag -n99 v1`），
   且 `v1^{commit} == v1.5.0^{commit} == 843b691` ⇒ 历史上是随发布滚动的，只是**最近 6 个提交没滚**。
   机械部分（6 个提交、`v1` 到不了新 gate.yml）**成立**。
3. **`tasks.md:29-30`（B5）**「改了 `caller_workflow()` 的字节 ⇒ 台账 hash 变 ⇒ 存量已接入仓跑 `init` 会报冲突」——
   **半假，且两个分支结论相反**。hash 台账比的是**台账 vs 磁盘**；改生成物影响的是**本次期望 vs 磁盘**（`initcmd.py:260-278`）。
   实测：选「缺省**不写** `with:`」时生成物**逐字节不变** ⇒ 存量仓 plain `init` 仍 `exit 0`「幂等，无改动」；
   真正会让存量仓立刻 `exit 1` 的是「写**显式空值**」**或**改头注释（SIM 2 实测）。
   ⇒ 这条告警不能当「两分支皆真」写进文档，必须与 `tasks.md:24`（B2）的「二者择一」绑在一起定。
4. **`design.md:64 / :77`**（D4/D5 乙）「`D4 = 空则跳过` 是选「移动 tag」时**唯一安全**的形态」——**不完整**。
   `gate.yml:19-23` 的 `witnessloop-ref` 默认值就是 `v1`，caller 从不覆盖 ⇒ 移动 `v1` **同时升级
   被 `uvx` 装下来的 witnessloop CLI**，把 6 个提交里多条「对**接入方**是行为变更」
   （`README.md:105-113`，含「历史 change 若缺 `stage=grill` manifest 会**新增一条红**」）一起静默送达。
   「空则跳过」只覆盖新增步骤，覆盖不了这一层。
5. **`design.md:98-104`（D8 文档影响清单）**——**有漏项**：`docs/gate.md:9`「只写三个文件」与
   `tests/test_init.py:18,72`（选丁即破，CRQ-10）；`templates/review-loop.md:69`「跑相关测试并把结果写进报告」
   （本 change 的立项理由就是「审阅者只能靠人工记忆跑一次」，流程模板不改，这条冲突就还在）；
   `docs/gate.md:§7`（能力边界，须补 R9 那条「PR 可改自己的 caller」）。
   另：`proposal.md:13` 的「流程规定 TDD + 审阅者核实测试通过」缺一个**文件:行号**出处——
   我只在 `templates/review-loop.md:33,69,77` 找到同义的表述，建议引用它。

## 仓内写入（含本文件对门禁的副作用，已实测）

- 唯一新增：`openspec/changes/adopter-test-gate/reviews/grill-review.md`（本文件）。
  被审 worktree 未做任何其他改动：`git status --porcelain` 只有 `?? openspec/changes/adopter-test-gate/reviews/`，
  `git diff` 为空。
- 所有实验在 `/tmp/grill-atg`、`/tmp/exp1`、`/tmp/expA`、`/tmp/expB`、`/tmp/expD`、`/tmp/verify` 中完成
  （副本一律先 `rm -f .git && git init -q`，避免 `gitdir:` 指针写回原仓）。
- **副作用（实测，作者请据此排期）**：`required_artifacts` 含 `reviews`，而立项草稿提交 `7099deb` **没有这个目录**
  ⇒ 那份草稿在 `check` 下是 **3 条** finding（含「缺少必需件 reviews」）。本文件把目录补上后降到 **2 条**：
  `缺少 review manifest` + `无 stage=grill 的 manifest`——**这两条要等作者在 E1 跑 `manifest build` 才会消**，
  本文件的存在**不能**代替 manifest（且 `reviews/` 下有报告但无 manifest 时，报的是「缺少 review manifest」，
  不是「孤儿报告」）。复现：
  `uv run witnessloop check --root <root> --base <base> --head HEAD`（只读，不写任何文件）。

## Sources

- 「未声明 input」的平台行为（**非官方明文**，两处第三方真实 issue + 一篇调试复盘）：
  - https://github.com/hyperi-io/hyperi-ci/issues/181
  - https://github.com/Extra-Chill/data-machine/issues/2918
  - https://learnedgeek.com/Blog/Post/debugging-startup-failure-reusable-workflows
- reusable workflow 的 check run 命名（`caller job / called job`）与 required 的 job 粒度：
  https://github.com/orgs/community/discussions/187865（以及 stackoverflow「整条 workflow 作为 required」问题）——
  但本报告的主证据是**本仓自己的 branch protection 实测**（`contexts = ["gate / check"]`），不依赖这两条。
- 官方文档中被**明确否决**的一条：`docs.github.com` 的 reusing-workflows 页面**没有**写「未声明 input 会怎样」
  （只写了类型必须匹配）⇒ 本报告把该断言标为「高置信、非官方明文、无端到端实测」。
