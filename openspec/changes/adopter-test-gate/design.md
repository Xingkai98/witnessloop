# Design: adopter-test-gate

> 状态：**设计已收敛** —— grill（证伪原稿 5 处事实 + 走到 3 个原稿没到的设计树节点）→
> 对抗验证 **R1 `CHANGES_REQUESTED`（4 阻塞）→ R2 `CHANGES_REQUESTED`（5 条机械）→ R3 `PASS`**（3 轮封顶）。
> 待**停轮**（Q1..Q13）用户确认。订正记录见 §7 / §7bis。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。决策记录：`reviews/grill-review.md`。

## 0. 一句话

交付「**接入方能拿到一个可用的测试执行点**」这一件事——**优先用一份约定正确的模板 + 文档（零代码、零接口、
对存量接入方也可达）**，而不是把接入方的测试塞进 witnessloop 自己的 `workflow_call` 接口里
（后者会连出**它其实不需要的** ref/发布决策，并在三条设计树节点上留下硬伤）。

## 1. 现状（实测 · 已按 grill 复核订正）

| 事实 | 位置 / 证据 | 说明 |
|---|---|---|
| caller 极薄 + 被台账管理 | `initcmd.py:24-40`（`caller_workflow`）、`initcmd.py:79-96`（台账） | `int`/`uninit` 都比对台账 hash |
| **`gate.yml` 自 `v1` 起从未改过** | `git log --oneline v1..origin/main -- .github/workflows/gate.yml` = **空**（同范围 `initcmd.py`/`constants.py` 有 6 个提交） | 本 change 是**第一次**面对 gate.yml 的发布策略 |
| **`v1` 是「滚动大版本」**（不是固定 tag） | `git tag -n99 v1` → 「witnessloop v1（**滚动大版本**，当前指向 v1.5.0）」；`v1^{commit} == v1.5.0^{commit} == 843b691` | 历史上随发布滚动，只是**最近 6 个提交没滚** |
| **`@v1` 同时钉着 gate.yml 与 CLI 版本** | `gate.yml:19-23` 的 `witnessloop-ref` **默认 `"v1"`**，而 caller 从不覆盖它 | ⇒ 移动 `v1` = 连**被 uvx 装下来的 witnessloop CLI** 一起换 |
| 零运行时依赖 | `pyproject.toml` `dependencies = []`（wheel METADATA 无 `Requires-Dist`） | pyyaml 只在 dev group（测试用） |
| **「只写三个文件」是被钉住的契约** | `docs/gate.md:9`、`tests/test_init.py:18,72,103` | 任何「`init` 多写一个文件」的方案都要动它 |
| **存量仓上「多写一个文件」到不了** | `_already_initialized`（`initcmd.py:207-281`）在无 drift/conflict 时**直接返回** ⇒ 实测输出「幂等，无改动」、**新文件不落盘** | 所有「加 init 产物」方案的共同瓶颈 |
| **手改 init 产物 = 死锁** | 实测（本机复现，见 §7-③）：改 caller 后 `init` **1** / `uninit` **1** / 删台账再 `init` **1**（「只增不改，拒绝覆盖」） | 没有 flag 能表达「我确认」；`uninitcmd.py:85-88` 的「请人工确认后重试」**不可满足** |
| 保护面 | `.witnessloop/policy.json` 实测：`protected_paths = ['openspec/specs/**','.witnessloop/**']`；本仓 `require_change_for = ['src/**','templates/**','plugin/**']` | `.github/**` **两者都不在** ⇒ 命令住那儿不需要解释事件 |
| required 粒度 = **job** | `gh api …/branches/main/protection` ⇒ `contexts = ["gate / check"]`（`strict`/`enforce_admins` 均 true） | 独立 job ⇒ 必然多一个人工勾选 |
| **本 change 的 CI 门禁跑的是 `v1` CLI**（**对抗轮 B1 实测**） | `.github/workflows/witnessloop.yml:14` 引 `@v1` + `gate.yml:19-23` 的 `witnessloop-ref` 默认 `v1`；v1 **没有 `evidence.py`**、`REVIEW_MANIFEST_REQUIRED_FIELDS` **不含 `stage`** | 实测：同一个「落了实现」的 diff，**v1 报 1 条、main 报 4 条** ⇒ 本 change 的 PR **不**被 #13/#16 那些新门禁约束 |
| **本仓自己的 pytest 不是 required check**（N6） | `gh api …/required_status_checks` = `["gate / check"]`；`gh pr checks 17` 里三条 `test` 均非 required | ⇒ **本仓可以带着失败的测试合入**——issue #4 的形态在**本仓自己身上**也有 |

## 2. 决策

### D1 测试步骤**住哪** —— 己（**推荐**）／甲（备选）／丁（否）／戊（**已删**，见下表）—— **Q1**

| | 接口/ref 耦合 | 命令日常可改 | 到达**存量**接入方 | 新契约成本 |
|---|---|---|---|---|
| **己（推荐）**：只发 `templates/github/adopter-tests.yml` 可复制模板 + README 配方，`init` 输出里提一句 | **无** | **自由**（是接入方自己的文件） | **可达**（自己拷） | **零** |
| ~~**戊**~~ **（对抗轮 B2：已从推荐里删除）** 原设想：`init` **种一次**（不存在才写、不进台账） | 无 | 自由 | 仍不可达 | **与 `spec.md` 的「SHALL NOT 要求手改 `init` 产物」直接冲突**（种子就是 init 生成、又必须被改）；只省**一次 `cp`**；**且有负作用**：`.github/workflows/**` 会被 GitHub 直接执行 ⇒ 出厂种子 = 工具自己静默种下一个**永远绿的 no-op check**（正是 D4 最恨的形态）。**若日后仍要做**：`init --with-tests` **显式 opt-in**，且种子必须是「占位符未替换 ⇒ 红」版本 |
| **甲（备选）**：`gate.yml` 加 `workflow_call.inputs.test-command` + step | **有** ⇒ 必须同时决定 D5 | 撞台账死锁（R10） | 需先移动/换 ref | `with:` 进 caller |
| **丁（否）**：`init` 写一个**台账管理**的独立测试 workflow | 无 | 撞台账死锁 | **不可达**（CD-7） | 破三文件契约 + `uninit` 回滚面扩张 |

- **否甲为主**的理由：它把「接入方的测试」塞进 witnessloop 的 `workflow_call` 接口 ⇒ 强制 D5（ref/发布），
  且**未声明 input ⇒ `startup_failure`、零 job、不点名**（R8）⇒ 决定错的代价是「每个 PR 卡死且无从诊断」。
- **否丁**：破了三文件契约**且**对存量不可达**且**撞台账死锁——三条缺点同时命中。
- **推荐 己 + 下面三条增量（对抗轮 B-1 提出、作者采纳）**：本 change 真正要交付的产品是
  「**一份约定正确的 YAML + 一个可复制的配方**」——因为 required 的勾选在**所有**方案里都是人工的
  （required 粒度 = job，见 §1）。⚠️ **「戊」已删**（见上表与 B2 的理由）。
  - **① 模板必须区分「未声明」与「占位符没填」**：空 ⇒ 跳过 + `::notice::`（D4）；
    **模板原样的占位符未替换 ⇒ `::error::` + exit 1**。⇒ 这把 D4 自己点名的
    「**看起来在保护你**的绿勾」从「大概率发生」压到「必须显式确认才可能」，
    而它**完全住在接入方自己的文件里**（零接口、零 ref、零 CLI 改动）。**这是 D4 与 D1 之间原本没闭合的缺口**
    ——己 让「拷了不填」成为最可能的失败模式，而 D4 的缓解（notice）原本是为「存量空命令」设计的。
  - **② `check` 在「仓里除 caller 外没有任何 workflow」时打一行 `::notice::`**（**零依赖**：列
    `.github/workflows/*` 即可，**不解析 YAML**；**非 finding、不改退出码、不改 `check` 语义**）。
    它只提供**可见性**、不提供强制，且对 `@v1` 接入方不可达（同 B1）。
  - **③ 配方必须给「可达 ref + 一条可直接执行的获取命令」**（N1：本仓惯例是钉 ref，而 `@v1` **没有**这个新文件
    ⇒ 照直觉去 `@v1` 取模板会 **404**）。
- ⚠️ **必须写进交付物的自述**（对抗轮 B-1 的实质）：**本 change 是「零机械强制」的**——
  它交付的是文档 + 模板；接入方不拷、不勾，什么都不会发生。**不得**以「机械门禁项目」的名义
  把这件事说得像有强制力（那正是本仓自己最反对的形态）。
- ⚠️ **落地位置（N2）**：`templates/` 的契约是「**host 中立**」（`tests/test_templates.py:1-5,24-31`）；
  一份**纯 GitHub Actions** 的 YAML 直接放进去与契约相抵，且 `tests/test_templates.py:39` 的 fixture
  只参数化两个 `.md` ⇒ 新文件会**自动豁免**三条检查。⇒ 放 `templates/github/` 之类的子目录**并**把它纳入该 fixture。
- ⚠️ **R14（选己 的实质优势，原稿没提）**：reusable workflow 的权限**不能超出 caller**，而 witnessloop
  的 `gate.yml:25-26` 只声明 `contents: read` ⇒ 接入方**无法**为自己的测试要 `id-token: write`(OIDC)、
  `packages: read`、`pull-requests: write`。走他们自己的 workflow ⇒ 权限不受限。

### D2 失败交互（**只有当测试步骤落在 witnessloop 的 job 里时才存在**）—— **R13**

若曾走甲 + 「并入既有 `check` job」：默认 step 语义下 **`check` 失败 ⇒ 测试步骤根本不执行**
（门禁红时恰好是最想要测试反馈的时候）；改用 `if: always()` 又会**掩蔽** `check` 的失败信息。
⇒ 这条**没有**「两全」写法，必须在 spec 里显式钉死选哪一个**以及为什么**。
**走己 时这条自动消失**（接入方自己的 job/workflow，互不影响）——这是推荐方案的附带好处。

### D3 命令**住哪** + 台账/死锁 —— **Q2**

- **推荐**：命令写在**接入方自己的** workflow 文件里（模板的 `run:` / `env:`）⇒ 既不进 witnessloop 台账
  （无死锁、无解释事件），也天然是「每次运行读 PR 检出出来的当前值」（无漂移面）。
- **若**仍要 witnessloop 侧知道命令（甲′ = `gate.yml` 运行时读仓内文件，见 CRQ-8）：**文件位置必须在
  `protected_paths` 与 `require_change_for` 之外**（如 `.github/wl-test-command.txt`）——
  **不要**放 `.witnessloop/**`（受保护 ⇒ 每次改命令都要写 `protected_path_write` 解释事件），
  **不要**塞 `policy.json`（它是不变集里的**不可移除**保护路径）。
- **必须写进文档的两条**（原稿把这条包装成了特性）：
  1. **手改 `init` 产物 = 死锁**（实测：`init`/`uninit` 同时 exit 1，`--dry-run`/`--policy`/`--gate-ref`
     都**不是**出口）。⚠️ **原稿写「恢复路径只有『恢复字节 + 删台账』」——对抗轮 B3 实测证伪**：
     有三条**文件级**出口（① 把被改文件恢复成生成物 ② 直接删掉被改文件 ③ 改台账里的 sha 只对 `uninit` 有效
     ⇒ `uninit → init` 走得通），而**「删台账」既不必要也不充分**（只恢复字节就够；删了台账但字节没恢复仍 exit 1）。
     即便如此，它对**存量接入方**仍近乎不可知（生成物是他们当初那个 CLI 版本的字节）。
  2. **不要**建议「先 `uninit` 再 `init`」：实测 `uninitcmd.py:91-95` 会删台账里的**每一个**条目，
     包括 `.witnessloop/policy.json` ⇒ 会**静默丢定制 policy**（本仓自己就是受害者：policy 来自仓外 seed，seed 不入库）。
     ⚠️ 这条对 **D5 甲（换 tag）** 同样致命：`init --gate-ref <新 tag>` 在已接入仓上是 exit 1
     （走 `conflicting_files`），手改 ref 又落回死锁 ⇒ **存量接入方「换 tag」的代价是丢定制 policy**（N7）。

### D4 默认行为：**空 = 跳过** + **可见信号**（Q4/Q7）

- 空 = 跳过（不失败、不探测）；但**必须**给运行时可观测信号，且这条进 **spec**（不只进 README）：
  空 ⇒ 打印一行 `::notice::`（「未声明测试命令，只跑了流程校验」）；非空 ⇒ 回显**实际执行的命令**。
- 理由：空=跳过 + required 绿 = 「**看起来在保护你**的绿勾」。例：`pytest --collect-only` 这类粘贴失误
  （收集 13 个用例、跑 0 个、exit 0）会让门禁**永远绿**——本仓最恨「永远绿的断言」。

### D5 ref / 发布策略：**甲（发新 tag）**，**否乙（移动 v1）** —— **Q3**

- **乙 的代价必须写全**（原稿漏）：`gate.yml:19-23` 的 `witnessloop-ref` 默认 `v1`、caller 从不覆盖 ⇒
  移动 `v1` 会把积压 6 个提交里**多条「对**接入方**是行为变更」**（`README.md:105-113` 自述，含
  「历史 change 若缺 `stage=grill` manifest 会**新增一条红**」）**一次性静默送达所有存量接入方**。
  「D4=空则跳过」只覆盖**新增的测试步骤**，完全不覆盖这一层 ⇒ 原稿「只要空则跳过就安全」**不成立**。
- **若 D1 选己 ⇒ D5 不进入本 change**（不碰 `gate.yml`）；若最终仍选甲 ⇒ **必须**在同一 change 内
  把「存量接入方怎么升」（含 R10 死锁）写成显式交付物，并选 D5 甲。
- 附带事实：`v1` 的注记自称「滚动大版本」⇒ 「乙 = 恢复 tag 自称的惯例」；但**惯例对不对先放一边**，
  按上面的代价评估，本 change **不**该顺手把 6 个提交的行为变更加载上去。

### D6 本仓自举：**今天不受影响**；C2 要钉对东西（CRQ-12）

- 实测：`.github/workflows/witnessloop.yml:14` 引 `gate.yml@v1`，本仓 main 的 required context = `gate / check`。
- ⚠️ **选乙之后这条立刻变假**（本仓自己的 caller 会立即执行新 gate.yml + 新 CLI）⇒ 这条校验
  **必须**与 D5 的定案一致：按推荐（**己**，不动 `gate.yml`）⇒ 用**回归检查项**——
  「本 change 的 diff **不含** `.github/workflows/gate.yml`」+「本仓 caller 仍引 `@v1`」；
  ⚠️ **不要**给 `gate.yml` 存快照/「逐字节不变」断言（它是要演进的 workflow，钉死等于禁止未来合法修改，CRQ-J-2）；
  若选乙 ⇒ 钉的是新语义（且要写清本仓自己也会被这次行为变更波及）。

### D7 `env:` 传参（防脚本注入）**要限定作用域**（CRQ-7 / R16）

- 现有 `gate.yml:57-58` 的 `run:` 里**就有**裸 `${{ inputs.witnessloop-ref }}`（同 step 的 `base-ref` 却规规矩矩走 `env:`）。
  ⇒ 断言若写成「`run:` 里不出现裸 `${{ }}`」会在**现状**上直接红。
- 按推荐（**己**）⇒ 本 change **不碰** `gate.yml`，这条退化为**模板的写法要求**（模板里命令经 `env:`）。
  若将来顺手改 `gate.yml:58`，那是一个**独立**的小清理，别混进本 change 的验收。

### D8 文档影响（**已按 grill 补漏**）

- `README.md`：接入段（测试执行点怎么拿、**三态语义**、required 是**人工勾一次**）+ **三条告警**（D9）。
- `docs/gate.md`：§7（能力边界补 D9）、新增一小节（本能力的语义与边界）。
- **`templates/github/adopter-tests.yml`**（**新文件**，己 的交付物；⚠️ 位置依 **Q11** 定案——
  `templates/` 根是 **host 中立**契约，纯 GitHub Actions 的 YAML 不该直接躺在那儿）+ `templates/review-loop.md`：
  ⚠️ **本 change 的立项理由之一就是「审阅者只能靠人工记忆跑一次测试」**，而
  `templates/review-loop.md:33,69,77` 那些「跑相关测试并写进报告」的条款**目前没有 CI 兜底** ⇒
  该模板要不要补一句「测试须由 CI 执行（见 `templates/github/adopter-tests.yml`）」是 D8 的一部分，
  **不改它这条冲突就还在**（grill 证伪第 5 条）。
- `proposal.md:13` 的「流程规定 TDD + 审阅者核实测试通过」补出处：`templates/review-loop.md:33,69,77`。

### D9 **能力边界（R9，必须进 spec，别过度承诺）**

本能力**只在「PR 不改自己的 CI」的前提下**成立：`.github/workflows/**` **不在**保护路径、
branch protection 实测 `required_approving_review_count: 0` / `require_code_owner_reviews: false`
⇒ 一个 PR 可以删掉自己的测试步骤（或写成 `|| true`）而 required check 依旧绿。
这与「门禁要防的那个 agent 恰好是 PR 作者」直接相关。文档**不得**承诺「测试失败一定拦住合并」，
而应写「**在你自己的 CI 配置未被本次 PR 修改的前提下**」。可选加固：把 `.github/workflows/**` 纳入
CODEOWNERS（写进文档，不强制）。

## 3. 接线点（依 Q1 定案）

- **选己（推荐）**：新增 `templates/github/adopter-tests.yml`（位置依 Q11）；`initcmd` 只在 `init`
  **输出**里加一行提示（**不改任何生成物**）；增量 ② 在 `checkcmd.py` 里加一行**非阻塞 notice**（依 Q13）；
  `README.md` / `docs/gate.md` / `templates/review-loop.md`。
  ⇒ **`gate.yml` 与 `constants.DEFAULT_GATE_REF` 都不动**。
- **选甲**：另需 `gate.yml` 新 input + step、`initcmd.caller_workflow()` 的 `with:`、台账记 `test_command`
  （否则存量仓用不了、新仓 plain `init` 永久冲突——`initcmd.py:131-141/:163` 已有 `gate_ref` 的 recall 先例）、
  以及 D5 甲（新 tag）。**明显更重**。

## 4. 风险（R1 起沿用 grill 编号）

1. **R8（高 · 平台耦合）**：未声明 input ⇒ `startup_failure`（**零 job**）⇒ required check **永不报告**
   ⇒ PR 停在「Expected — waiting for status to be reported」，**既拦人也无日志**。最危险组合是
   「文档教人手改 caller 填命令」+ 存量仓仍钉冻结的 `@v1`。⚠️ **置信度中高、非官方明文、无端到端实测**（CRQ-5）。
2. **R9（中高 · 安全边界）**：见 D9。**必须进 spec**，否则**过度承诺**。
3. **R10（条件式严重度 · 对抗轮 CRQ-A 订正）**：**条件 = 该仓是否已手改过 `init` 产物**——对**照文档做**的接入方**不成立**（文档不教这条路，本 change 新增的交付物也不要求手改）；对**已经手改过**的仓成立（近乎不可知）。实测：`init`/`uninit`/`--dry-run`/`--policy`/
   `--gate-ref` 全 exit 1，**没有 flag 能表达确认**；但**并非无出口**（B3 的三条文件级出口）。
   原稿把它写成「唯一出口是恢复字节+删台账」**过头了**。仍然成立的部分：本 change **不得**把
   「手改 init 产物」当正常用法（对存量接入方近乎不可知）。
4. **R11（中）**：任何「`init` 多写一个东西」的方案都对**存量仓不可达**（CD-7）⇒ 验收**不能只在新仓上做**。
5. **R12（中）**：`@v1` 同时钉 gate.yml **与** CLI 版本 ⇒ 移动它 = 一份新 CLI 静默到达（D5 否乙的核心理由）。
6. **R13（中）**：失败交互（D2）——走甲时才存在，且没有两全写法。
7. **R14（中 · 能力天花板 → 选己 的论据）**：reusable workflow 权限不能超出 caller
   ⇒ witnessloop 的 `contents: read` 会把接入方的测试锁死在这个权限里。
8. **R15（低-中 · 契约）**：选**丁**（或日后若做**戊**）破「只写三个文件」契约（`docs/gate.md:9`、`tests/test_init.py:18,72`）⇒ 必须进 spec delta。
9. **R16（低 · 测试写法）**：D7 的断言必须限定作用域，否则在现状上直接红。
10. **R17（低 · 自举）**：本 change 若改 `caller_workflow()` 的字节 ⇒ **本仓自己的** init 台账与磁盘不一致
    ⇒ 此后任何 `init` 撞死锁，而恢复路线会丢定制 policy（本仓 policy 来自仓外 seed、不入库）。
    ⇒ 建议：本 change **不改** `caller_workflow()`（选己 天然满足）；若必须改，顺手把 seed 入库或加恢复通道。
11. **R18（低 · 理由句精度）**：原稿用「`check` 也在本地/guard 路径上被调用」当论据——**假**（`guard` 不调用 `check`，
    见 §7-①）。结论（不让 `check` 跑测试）保留，但论据要换。
12. **R19（高 · 本 change 自己的最大风险，对抗轮 B-1）**：**己 让「拷了模板但没填命令」成为最可能的失败模式**
    ——那时的形态是**绿 job**，正是 D4 点名的「看起来在保护你」。⇒ 靠增量 **①（占位符未替换 ⇒ 红）**消掉；
    **没有 ① 就不该推荐己**（这条是 D1 与 D4 之间原本没闭合的缺口）。
13. **R20（中 · 自举，对抗轮 B1/CRQ-F）**：**本 change 的门禁由 `v1` CLI 执行**（v1 无 `evidence` 模块）
    ⇒ 本 change 的 PR **不**被 #13/#16 的新门禁约束，本仓最近 6 个 change 同理
    ⇒ **任何「本仓 PR 由新规则拦住」的表述都是假的**，文档必须写清「哪条规则在哪个 ref 上生效」。
14. **R21（中 · 自举，对抗轮 N6）**：**本仓自己的 `test` job 不是 required** ⇒ 本仓可以带着失败测试合入
    （issue #4 的形态在**本仓自己身上**也存在）⇒ 本 change 应把「把 `test` 勾成 required」写成一条**人工交付项**。

## 5. 测试策略（TDD）

- **模板/工作流**：用 **pyyaml 结构化断言**（先例与理由见 `tests/test_gate_workflow.py:32-34`：只 grep 子串钉不住
  「位置 + 取值」都重要的行）——断言模板里：命令经 `env:`、空时有 `::notice::`、非空时回显实际命令。
- **若选己**：另需钉「`init` 输出里提到了测试执行点」；`caller_workflow()` 的**逐字节稳定**用 golden literal（CRQ-J-1）。
- **若选甲**：`gate.yml` 新 input 的声明 / 空则跳过 / 三文件契约变更 / 台账 `test_command` recall
  （照 `initcmd.py:131-141` 的 `gate_ref` 先例）。
- **回归**：全量 pytest 绿；**`gate.yml` 不进本 change 的 diff**（回归检查项，**不**做快照断言——CRQ-J-2）。

## 6. 停轮裁定（Q1..Q13 —— **待用户确认**）

| 问题 | 推荐 | 一句话理由 |
|---|---|---|
| **Q1 步骤/交付物形态** | **己 + 增量 ①②③**（甲备选；**戊已删**；丁否） | 交付物应是「约定正确的 YAML + 配方」；**没有 ① 就不该推荐己**（R19） |
| **Q2 命令住哪** | 接入方自己的文件（**不台账**）；若走甲′ 放 `.github/` 而非 `.witnessloop/` | 避开死锁（R10）与「改命令要写解释事件」（CRQ-9） |
| **Q3 ref 策略** | **甲（新 tag）**；**否乙** | 移动 `v1` 会连带升级 CLI（R12）；选己 ⇒ 本 change 不需要它 |
| **Q4 空默认** | 保留「空=跳过」 | 存量零影响；探测会静默跑错东西 |
| **Q5 告警** | 写（fork PR + **PR 可改自己的 CI** + **本 change 零机械强制**） | 后者是 B-1 的实质：不得以机械门禁之名说得像有强制力 |
| **Q6 存量升级** | 写成**显式交付物**；**勿**「uninit→init」 | 那条路会静默丢定制 policy（实测） |
| **Q7 可见信号** | 要（`::notice::` + 回显命令） | 把「静默」变成「看得见的静默」 |
| **Q8 命令文件位置** | 避开保护路径（`.github/…`） | 否则每次改命令都要写解释事件 |
| **Q9（对抗轮新增）issue #4 怎么收口** | **保持 open 或关 #4 并另开一条「机械执行点」issue**（推荐后者） | #4 原文给的两条建议**都是机械的**，本 change 一条都不做（B4）——不能用零强制的东西关掉一个要机械机制的 issue |
| **Q10（对抗轮新增）本仓自举** | **本 change 顺带把 `ci.yml` 的 `test` 勾成 required**（人工一步） | 否则本 change 自己的 PR 可以带着红测试合入（N6/R21） |
| **Q11（对抗轮新增）模板放哪** | `templates/github/`（+ 纳入 `tests/test_templates.py` 的 fixture） | `templates/` 的契约是 **host 中立**（N2） |
| **Q12（对抗轮新增）模板的分发 ref** | 配方点名 `main`（并写明未钉版本）**或**顺带发一个 tag | ⚠️ 选后者会把 D5 重新拉回本 change（N1） |
| **Q13（对抗轮新增）是否把 ② （`check` 的 `::notice::`）纳入** | 纳入（非阻塞、不改退出码） | 它给本 change 一点**可见性层面**的机械性，部分回应 #4 |

每条的具体例子、反驳与出处见 `reviews/grill-review.md` 与 `reviews/grill-adversarial.md` 的对应小节。

## 7bis. 对抗验证 R1/R2 的证伪与订正（已整合 · 来源 `grill-adversarial-reviewer-adopter-test-gate-0316bc00ebcd`）

- **B1**：本 change 的 CI 门禁跑 **`v1` CLI**（无 `evidence` 模块）⇒ 原稿/grill 关于「必须三份 manifest，
  否则红」的表述**对本 PR 为假**（实测 v1 报 1 条 / main 报 4 条）⇒ 已在 §1 加行、在 tasks F1/F2 区分
  「本地 `uv run`（main 代码）」与「CI（v1）」，并在 §7-6 记入。
- **B2**：**戊 已从推荐删除**（与 spec 冲突 + 只省一次 `cp` + 会种下永远绿的 no-op check）。
- **B3**：「唯一恢复路径」**为假** ⇒ 已按三条文件级出口改写（§2 D3-①、R10）。
- **B4**：**不得**用零强制的交付物去关 #4 ⇒ 已改为 Q9，并补 ①②③ 三条增量。
- **N1–N7**：分发 ref / 模板位置 / 缺任务 / 漏测 / spec 可证伪性 / 本仓 test 非 required / 甲 的升级代价
  —— 逐条落进 §1、D1、D3、§4（R19–R21）、§6（Q9–Q13）与 tasks。
- **CRQ-J（怎么钉三件事）**：`caller_workflow()` 的**逐字节稳定**值得一条 golden literal 测试（生成物是
  已接入仓的实际契约，R17）；**`gate.yml` 不该钉「逐字节不变」**（它是要演进的 workflow，钉死会禁止未来合法修改）
  ⇒ 改成**回归检查项**（本 change 的 diff 不含它 + 既有 `tests/test_gate_workflow.py` 全绿）；
  `check`/`guard` 的**判定逻辑**零改动由既有用例 + diff 范围保证——⚠️ **判定路径**限定，`checkcmd.py` **允许**改动（增量 ② 要在那里加一行非阻塞 notice，见 tasks C4）。

## 7. 原稿被证伪的事实（grill 提出 · 作者独立复核属实）

1. **`design.md:29`**「`check` 也在本地 / guard 路径上被调用」——**假**。`guardcmd.py:22-33` 只 import
   `constants/contract/evidence/paths/policy/gitutil`；`cli.py:153-160` 把 `guard` 与 `check` **分别**分派。
   共享的是**判定库**，不是动词。⇒ 结论保留（不让 `check` 跑测试），**论据改写**（见 R18）。
2. **`proposal.md:25` / `design.md:18`**「`v1` 是**固定** tag」——**表述不准**：`git tag -n99 v1` 的注记原文是
   「滚动大版本，当前指向 v1.5.0」。机械部分（6 个提交、到不了新 gate.yml）成立。
3. **`tasks.md` 原 B5**「改 `caller_workflow()` 的字节 ⇒ 存量仓 `init` 报冲突」——**半假、两分支结论相反**：
   台账比的是「台账 vs 磁盘」，改**生成物**影响的是「本次期望 vs 磁盘」。实测：选「缺省**不写** `with:`」
   ⇒ 生成物逐字节不变 ⇒ 存量仓 plain `init` 仍 exit 0；真正会立刻打破的是「写**显式空值**」或**改头注释**。
   ⇒ 这条必须与 tasks B2 的「二者择一」绑在一起定。
   **另经作者独立复现**（`/tmp/atg-check`）：手改 caller 后 `init` **exit 1**、`uninit` **exit 1**、
   **删台账再 `init` 也 exit 1**（「只增不改，拒绝覆盖已有文件」）⇒ **死锁属实**。
4. **`design.md:64/77`**（D4/D5 乙）「空则跳过 ⇒ 移动 tag 唯一安全」——**不完整**：漏了 `witnessloop-ref`
   默认 `v1` 这一层（R12）。
5. **`design.md:98-104`**（D8 文档影响清单）**有漏项**：三文件契约（`docs/gate.md:9` + `tests/test_init.py:18,72`）、
   `templates/review-loop.md:33,69,77`、`docs/gate.md §7`（D9），以及 `proposal.md:13` 缺 `文件:行号` 出处。
6. **（对抗轮 R1 补）`grill-review.md` 的 CD-8 与 `README.md:105-120` 的隐含前提**：「本仓/接入方的 PR
   必须有三份 manifest，否则红」——**对本包的 PR 为假**：本仓 caller 引 `@v1`，而 v1 的 CLI **没有 `evidence` 模块**、
   `REVIEW_MANIFEST_REQUIRED_FIELDS` 也不含 `stage` ⇒ 实测同一 diff「v1 报 1 条 / main 报 4 条」。
   ⇒ 已在 `grill-review.md` 的 CD-8 处加订正指针；README 相关表述要写明**哪条规则在哪个 ref 上生效**。
