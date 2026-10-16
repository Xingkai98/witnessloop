# witnessloop

把「agent 驱动的软件开发流程」做成**独立于任何代码仓、可复用于任意仓库**的工具。

流程：**设计先行 → 设计对抗式追问（grill）→ 实现 → 独立审阅闭环**，全程由**机械门禁 + 证据绑定**强制——而不是靠模型自觉。

> **状态：MVP 完成**（M1 门禁层 + M2 交互层 + M3 第二仓 acid test 全绿）。
> 动词面 = 3 个门禁动词（`init` / `uninit` / `check`，fail-closed）
> + 1 个证据产出动词（`manifest build`）；
> 交互层是 Claude Code plugin（`grill` / `review-loop`，只接线、只读、无状态）。
> 全流程已在**第二个真实仓**端到端跑通（`init → change → grill`（设计阶段对抗验证收敛）
> `→ 用户确认 → TDD → review-loop → check 绿`），见
> [docs/reviews/m3-acid-test.md](docs/reviews/m3-acid-test.md)。
> 设计见 [docs/design.md](docs/design.md)，任务见 [docs/tasks.md](docs/tasks.md)，
> 门禁层数据契约见 [docs/gate.md](docs/gate.md)；已知待办见仓库 Issues。

## 用法

```bash
uv tool install git+https://github.com/Xingkai98/witnessloop@v1
# ⚠️ 这个 ref 与 CI 里装包用的 ref **是同一件事**（issue #30 / change gate-ref-pins-package）：
#    钉旧了，本地 CLI 与 CI 里的门禁都跑旧行为。升级就把 ref 指到新 tag（见「怎么钉版本」）。

# 接入目标仓：幂等、只增不改、不 auto-commit。先看要写什么（不落盘）
cd your-repo && witnessloop init --dry-run
```

落盘时**三选一**（下面三条是**互斥的替代**，**不是顺序执行**；`--policy` 可与任一条组合）：

```bash
witnessloop init --test-command "uv run pytest -q"   # ① 推荐：接入 + 写**测试执行点**（见「接入方的测试进 CI」）
witnessloop init                                     # ② 不带 flag ⇒ 执行点是哨兵占位（`check` 会判红）
witnessloop init --no-tests                          # ③ 显式不要测试执行点（见那条的「opt-out 的语义」）
witnessloop init --policy /path/to/policy.json        # + 需要非默认 policy（见下「本仓自身接入」）

# 审阅跑完，落证据（复用 check 同一套哈希；幂等、不 auto-commit）
witnessloop manifest build --change add-retry --stage building \
  --report reviews/building-review.md \
  --reviewer-run-id run-A --author-run-id run-B

# CI 入口（fail-closed）
witnessloop check --base origin/main --head HEAD

# 本地守卫：写目标命中 require_change_for 且缺 grill 证据 → 拦（CLI 退 1；host shim 再映射成 CC 的 2）
# 通常由 host 的 PreToolUse hook 自动调（见下），也可手动/脚本调
witnessloop guard --path src/x.py

# 精确回滚（文件被改过就拒绝删除并报 diff）
witnessloop uninit
```

交互层（`grill` / `review-loop`）是一个 Claude Code plugin，**只做接线**——
算法在 host 中立的 `templates/` 下，适配器在 `plugin/` 下，两者物理分离：

```bash
claude --plugin-dir /path/to/witnessloop/plugin
```

分发按设计走 **git / 本地目录，不上 marketplace**（design §4）。

### 接入方的测试进 CI（测试执行点）

`init` 会把**测试执行点**写进目标仓：一份**命令文件** `.github/witnessloop-tests.txt`，
内容就是**一行 shell 命令**。

```bash
witnessloop init --test-command "uv run pytest -q"   # 接入时就把命令写进去（推荐）
witnessloop init                                      # 不带 flag ⇒ 文件里是哨兵 <<REPLACE-ME>>（check 判红）
witnessloop init --no-tests                           # 显式不要执行点（见下面的边界与 opt-out 说明）
```

- **门禁会跑它**：`.github/workflows/gate.yml` 新增一步，在本 job 内 `sh -c "$(cat 该文件)"`。
  它和 `check` 是**同一个 job** ⇒ **复用你已勾成 required 的 `gate / check`**：测试失败 = 合不了
  （⚠️ **不保证**它真跑过，见下面的边界 ①），**不需要任何新增的平台操作**。
- **`check` 会机械地要求它「存在、非空、已接线」**：文件缺失 / 是空文件（或纯空白）/ 仍是哨兵
  `<<REPLACE-ME>>` ⇒ `check` 红并点名路径。它只看文件与字符串，**不执行**你的命令。
- **改命令是普通操作**：直接编辑 `.github/witnessloop-tests.txt` 并提交即可（`.github/**` 不在保护
  路径、不需要解释事件）。这个文件刻意**不进 init 台账**，所以**再跑 plain `init` 也不会**覆盖它或
  报冲突；想用 `init --test-command` 主动覆盖也行——**该 flag 总是覆盖**已有内容。

**四条诚实边界**（不写清就是过度承诺）：

1. `check` 只保证「**有一个已接线的执行点**」——**不保证**它真跑过，也**不保证**它跑的是真测试：
   `|| true`、`--collect-only`、一行 `# TODO` 注释、甚至 `true` / `:` 都能骗过存在性判定
   （第三条判据只堵**意外**写出来的空文件）。「真跑了」由**平台侧 required check** 保证。
2. **PR 可以改掉自己的命令文件 / CI 配置**（`.github/workflows/**` 不在保护路径、
   `required_approving_review_count: 0`）而 required check 依旧绿。
3. 测试命令是**任意代码**，会在**每个 PR（含 fork PR）**的 runner 上执行——别把密钥写进去
   （这个 job 只有 `contents: read`，也拿不到别的）。
4. **能力天花板**：走这个执行点意味着你的测试跑在**别人的 job** 里——只有 `contents: read` 权限
   （reusable workflow 的权限不能超出 caller），**没有 `services:`、不能加自己的 `uses:` 步骤、
   不能上 matrix/缓存**，命令只能是**一行 shell**。需要这些能力的仓应当改用**自己的 workflow**
   （代价：自己再勾一次 required）。**把「同 job」说成普遍更优就是过度承诺**——它是「零新增人工
   步骤」与「测试环境自主权」的交换。

**opt-out 的语义（第五条说明）**：`tests.disabled: true`（或新接入时的 `--no-tests`）**只关 `check`
那条判定，不关门禁那一步**——门禁只看「文件在不在 / 含不含哨兵」。想「连跑都别跑」就**删掉命令
文件**（那一步会跳过）。

⚠️ **已接入的仓怎么 opt-out**（这里容易说错）：`--no-tests` 是个**接入期**的 flag——已接入且
policy 还是出厂默认的仓给它会**报冲突退 1**（「本次期望 ≠ 磁盘」），只有 policy **已经是**
`tests.disabled: true` 时 `init --no-tests` 才幂等 exit 0。所以已接入的仓要 opt-out 就直接改
`.witnessloop/policy.json`：它是不变集、状态是 `M` ⇒ **每次都要一条 `protected_path_write` 解释
事件**；而且改完 policy 之后 plain `init` 会暂时 **exit 1**（任何定制 policy 都如此，不是该字段
独有——再带一次 `--no-tests` 即可）。

### 本仓自身接入（dogfood）

witnessloop **自己也走这套流程**：本仓有 `.witnessloop/policy.json`，非平凡改动落在
`openspec/changes/<id>/` 下、内容与证据分离提交，PR 由 required check 拦。本仓的
`require_change_for` 比出厂默认多收 `templates/**`、`plugin/**`（交互层也是产品面）。

本仓**需要定制 policy**，所以接入用 `init --policy <seed>` 一次写成（seed 是仓外的临时
文件、**不入库**；`.witnessloop/policy.json` 是唯一权威）——这样 policy 是「新增」而非
「修改」，免解释事件、台账自洽、`uninit` 可回滚。

> **诚实前提**：**接入本身**只能靠**本地** `witnessloop check` + 人工 review 兜一次——
> 因为它才引入 caller workflow、`main` 的 required check 那时尚未勾选；**接入之后**的 PR
> 才被机械拦。这是自举的固有鸡生蛋，不是遗漏。
>
> 另：`init --policy` 与 `--test-command` / `--no-tests` 是**接入期**的动词选项，自 **`v1.6.0`**
> 起随 `@v1` 发布。本地 CLI 还旧时，自己接入跑源码版（`uv run witnessloop …`）即可。
>
> ⚠️ **关于「`@v1` 是滚动大版本」这句旧说法**（change `gate-ref-pins-package` / issue #30 起**不再成立**）：
> `@v1` 现在**停在 `v1.6.0`**（`ae99256`），本 change 刻意**不动 `v1` tag**——它是别人依赖的
> 发布物，移动它会让所有钉 `@v1` 的仓在**没人做任何动作**的情况下换掉门禁本体与包。
> 新能力改由**新 tag**（`v1.7.0` 起）发布：升级 = 把 ref 指过去一处，包版本跟着走
> （见下「怎么钉版本 / 怎么升级」）。别再按「`@v1` 会跟着 `main` 滚」理解版本稳定性。

### policy（`.witnessloop/policy.json`，住在目标仓、可评审）

`init` 写一份默认 policy。要定制就用 `init --policy <file>` **一次写成**（事后手改会打破
init-manifest 台账、`uninit` 拒删，见 [docs/gate.md §1.1](docs/gate.md)）：

- `protected_paths`：写入需结构化解释事件（默认 `openspec/specs/**`、`.witnessloop/**`）。
- `require_change_for`：命中这些 glob 的改动**必须**挂一个 change 目录。默认覆盖常见
  源码目录（`src/**`、`lib/**`、`app/**`、`apps/**`、`packages/**`、`server/**`、
  `cmd/**`、`internal/**`），**不含** `docs/**`、`tests/**`。没有它，绕过门禁最省事的
  办法是什么都不建——只改 `src/` 的 PR 会直接放行。写 `[]` 可显式关掉。
- `required_artifacts` / `evidence`：change 目录必须齐备的件、证据文件名与事件格式。

归档（把 change 从 active `git mv` 进 `openspec/changes/archive/`）属簿记动作，
**不需要**手写解释事件；删改证据文件仍然要。边界见
[docs/gate.md §5.1](docs/gate.md)。

**归档感知**：把 change 搬进 `openspec/changes/archive/` 也**只会**做一件事——把那 change「归属」回本次 diff
（`require_change_for` 不再对它误报、`manifest build` 能解析归档目标、`events` 扫得到归档目录）。
它**不豁免任何东西**：归档态与 active 走**同一套**证据门禁，归档 PR **也会红**（uniform）。
（`archive-arrival-recognition` / issue #26 起，「到达」按**目录级事实**判：`git mv` 过来（**带内容改动也行**）
与**直接新建在 `archive/` 下**都认；但**搬运现成证据**（整份 `cp`、复制后改路径/改一处/混源、符号链接到既有 change）
**不授予**——它的两条已知边界见 `docs/gate.md §7`。）
三条要记住的操作边界：

- **归档时带内容改动也可以**（issue #26 放宽）：move 与「改写被 move 的文件」（含在归档态重建 manifest，
  git 报 `R<100`）同时在同一个 diff 里**照样算到达**，不再产生幽灵 id。
- **推荐时序按 change 的「来历」分两种**（issue #26 之后必须分开看）：
  - **change 在 base 里已经是 active**（例如先有一个文档 PR 把 change 落进主干，实现 PR 再来搬它）
    ⇒ **① 内容（实现 + 收尾）→ ② 在 active 态产证据 → ③ `git mv` 归档放最后**（省事，也省一次重建）。
  - **出生即归档**（change 与实现同一 PR 内产生，diff 里**一个 rename 都没有**）
    ⇒ 必须在**归档 move 之后**、用**归档目录名**产 manifest：
    `witnessloop manifest build --change <归档目录名> --stage <stage> --report reviews/<报告>.md`。
    原因见下一条。
- **不要「搬」现成证据**：把别的 change 的证据整份 `cp`/改名到新归档目录、或做成指向它的**符号链接**
  ⇒ 不授予（会报「没有任何 change 目录」）。
- **「源 id」别名**的前提是**有 rename**：归档态 manifest 的 `change_id` 接受「归档目录名」与**源 id**两个名字，
  而**源 id 只能从 rename 记录里解析**（`git mv <changes_root>/<id>/… → archive/<name>/…`；
  两种归档命名 `archive/<id>`、`archive/<date>-<id>` 都算）：
  - **有** rename（上面第一种来历）⇒ 归档**前**用源 id 产的 manifest **不必重建**；
  - **没有** rename（出生即归档）⇒ 只有**归档目录名**算数 ⇒ 归档前产的 manifest（`change_id=<源 id>`）
    会**报「与目录不符」**，必须**在归档后用归档目录名重建**（或在归档之后再产证据）。
  - 实测（接入方 asterwynd，issue #305 阶段 C）：出生即归档的实现 PR 精确报**三条**
    `manifest.change_id='<源 id>' 与目录不符`（三份 stage manifest 各一条）——重建后同一个 diff `check：通过 ✓`。
- **要改归档后的证据** ⇒ 放到**不含该归档 move** 的后继 diff 里（那会是覆盖 = 每条一条解释事件）。

细节与边界表见 [docs/gate.md §5.1.1](docs/gate.md) 与 §4。

`init` 写的 caller workflow 引用本仓的 reusable workflow
`.github/workflows/gate.yml@<ref>`——记得在目标仓 branch protection 里把那个 job
勾成 required，否则门禁不会真的拦人（那一次人肉操作就是 v1 的「人类签名」）。

### 怎么钉版本 / 怎么升级

caller 里的那**一个** ref 同时决定「跑哪份 workflow 文件」与「跑哪个 witnessloop 包」：
`gate.yml` 把包 ref 解析成 `job.workflow_sha`（= 被复用的那个 workflow 文件自己的 commit），
显式 `with: witnessloop-ref:` 仍可覆盖 ⇒ **改一处、两处跟着走**（细节见
[docs/gate.md §1.2](docs/gate.md)；GHES / fork 等能力边界见其 §7）。

```bash
# 新接入：直接钉你要的 ref（⚠️ v1.7.0 发布前请用 @v1，见下）
witnessloop init --gate-ref Xingkai98/witnessloop/.github/workflows/gate.yml@v1.7.0

# 已接入：升级**两步，顺序不能反**
uv tool install --force git+https://github.com/Xingkai98/witnessloop@v1.7.0   # ① 先升 CLI
witnessloop check --root . 2>/dev/null | head -1                              # ①′ 自证：看这一行
witnessloop init --gate-ref Xingkai98/witnessloop/.github/workflows/gate.yml@v1.7.0   # ② 再换 ref
```

⚠️ **第 ① 步不能省**：重写 caller 的语义是**新版包**才有的。用旧 CLI 跑第 ② 步会得到
EXIT=1 与一句把人指向 **policy** 的「检测到冲突…要更换 policy 请先 `uninit`」——
**误导**（要换的不是 policy，是 CLI 太旧）；看到它**别去删 policy**。

⚠️ **①′ 是唯一能确认 CLI 换没换成的办法**：`--version` 判不出来（版本号恒为 `0.1.0`、与 tag 无关），
`init` 也不自报。`check` 的第一行是唯一出口——它打 `requested_revision=<你刚升的 ref>`；
旧的 `@v1` 包**没有这一行**，所以「有没有这一行」本身就是新旧判据。

⚠️ **`v1.7.0` 发布之前，请仍然钉 `@v1`**：这个 tag 是随本 change 的 `(post-merge)` 步骤建的，
在它出现之前指过去会钉到一个**不存在的 ref**。

⚠️ **别手改 caller**：手改 ⇒「磁盘 ≠ 台账」⇒ plain `init` 报「被改动过」、`uninit` 拒删
（有出口，但要用上面那个动作）。要看**本次到底跑了哪个 ref**：`gate / check` 日志里那行
`::notice::witnessloop 包 ref = …（来源：…）`，以及 `check` 自己那行
`本包来源（自报，尽力而为）`（它还能给出解析后的 commit；⚠️ 该行**由新版包起**才有——
拿旧包跑 `check` 看不到它）。

> **前置条件：本仓必须公开。** caller 引用的是本仓的 reusable workflow、CI 里用
> `uvx --from git+…@<ref>` 安装本包——两者在**私有**仓下都会失败（reusable workflow
> 访问级别默认 `none`；私有包安装报 `could not read Username`）。已实测，见
> [docs/design.md §4.1](docs/design.md)。私有接入需额外配 token，不在 v1 范围。

### 本地守卫与行为变更

交互层带一个 **PreToolUse 本地守卫**：`Write|Edit` 之前调 `witnessloop guard`——当前 change 的
grill 证据不完备就不许写代码路径（**写文档豁免**，否则永远产不出证据）。它与 `check` **共用同一个**
判定。装 plugin 时**同时要装 CLI**，否则命令找不到、守卫静默失效（fail-open）。

它是「**防遗忘**」不是防对抗：**用 Bash 写文件**（`matcher` 只覆盖 `Write|Edit`）**或不装 plugin
即绕过**。真正的锚仍是 CI required check。

⚠️ **对**接入方**是行为变更**：`check` 现在要求每个 change 有一个 **`stage=grill`** 的 manifest，
且该报告正文合格（`Confirmed Decisions` ≥3 且每条带 `来源:`、`Open Questions` 都经用户确认——
⚠️ `## Open Questions` 小节必须**逐字**存在，标题改了、或压根没这个小节 ⇒ 红）——
**此前没有这道校验**（标题非逐字的报告此前会被**整段静默跳过**）；历史 change 若缺
`stage=grill` manifest 会**新增一条红**。详见 [docs/gate.md §8](docs/gate.md)。

⚠️ **对**接入方**还有一条报错形态变更**（issue #12）：损坏的 `workflow-events.jsonl`
（解码失败 / 读不到）此前会表现为**工具故障**——`witnessloop：内部错误（UnicodeDecodeError…）`，
现在是一行**点名文件**的 finding（`事件文件无法解析：… 无法解码：…`）。**退出码不变**（仍非 0）。

⚠️ **对**接入方**还有一条行为变更**（`grill-adversarial` 门禁，issue #16）：**改了代码**
（= 本次 diff 命中 `policy.require_change_for`，本仓**含** `templates/**` / `plugin/**`）的 PR 现在**必须**
有一份 `stage=grill-adversarial` 的审阅证据（= 跑过**设计阶段的对抗验证轮**：grill 之后、停轮之前的
证伪环节），**否则红**。触发面与下面那条 `building` 门禁**完全相同**（同一个时点的两端证据）。
**三条诚实边界**（与 [docs/gate.md §10](docs/gate.md) 逐条一致）：
① 报告的 **verdict 文本不参与判定**（`PASS` / `CHANGES_REQUESTED` 都能过）；
② 只保证证据**存在**并绑在最终 revision，**不保证**对抗轮发生在**写码之前**；
③ **报告正文不校验——空文件亦合格**。
**不加**过渡开关（开关 = 静默绕过面）。

⚠️ **对**接入方**还有两条行为变更**（`building` 门禁）：**改了代码**（触及 `policy.require_change_for`）的 PR
现在**必须**有一份 `stage=building` 的审阅证据（= 跑过 review-loop），**否则红**；
且**一个 PR 同时触及多个 change**（只要它触及了代码）时，**每个** change 都要 building 证据（要免除就把 change 拆到单独 PR）。
**注意**：这道门只保证「**闭环跑过 + 审在最终 revision 上**」——**报告里的 verdict 文本不参与判定**，
`PASS` / `CHANGES_REQUESTED` 都能过（§9 有完整口径）。

⚠️ **对**接入方**还有一条行为变更**（**测试执行点**门禁，issue #4）：`check` 现在要求
`.github/witnessloop-tests.txt` **存在、去空白后非空、且不含哨兵** `<<REPLACE-ME>>`，否则**红**
（空文件会让 `check` 与门禁**同时**判绿而测试一个都不跑，所以它必须判）。策略字段的语义是
**缺省 ⇒ 声明** ⇒ **已接入的仓会被立刻判**。迁移三选一：

```bash
printf 'uv run pytest -q\n' > .github/witnessloop-tests.txt   # ① 手工补一份（最简单）
witnessloop init --test-command "uv run pytest -q"            # ② 让 init 写（policy 与出厂默认一致的仓才行）
# ③ 不要这个执行点：policy 里写 "tests": {"disabled": true}（改不变集，需一条解释事件）
```

⚠️ 本仓自己的 `init` 早就跑不动（定制 policy 撞出厂默认）⇒ 本仓那次是走 ① 手工提交的。
口径与四条边界见上节与 [docs/gate.md §11](docs/gate.md)。

⚠️ **对**接入方**还有一条行为变更**（**归档感知**，issue #21）：归档 move 现在会把那个 change
**归属回本次 diff** ⇒ 它照旧要走**同一套**证据门禁（契约 / manifest / grill 正文 / stage 门）。
**两条后果**：① 「实现 PR 同时归档」不再被误报「没有任何 change 目录」（这是修复）；
② **纯归档 PR 也会红**——若那份 change 的证据本来就不合规（历史 change），归档那一刻会被点出来
（Q1 拍板 uniform，接受这条新红类；补救 = 在**归档之前**的 diff 里补证据，见
[docs/gate.md §5.1.1](docs/gate.md)）。
**还给两样**：`manifest build --change <归档目录名>` 能在归档目录里产证据；`events` 扫得到
`archive/*/workflow-events.jsonl`（此前归档 change 的事件一律不生效）。

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
- **门禁落 merge boundary**：强制放在 CI required check。交互层另有一层**本地守卫**（写码前缺 grill 证据就拦），但它是「**防遗忘**」不是防对抗——用 Bash 写文件、或不装 plugin 就能绕过，**真正的锚仍是 CI**。

## 名字

`witness`（独立见证者）+ `loop`（审阅/追问的循环）。每一个审阅环都是一个零记忆的 witness。
