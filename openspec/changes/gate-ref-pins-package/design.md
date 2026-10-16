# Design: gate-ref-pins-package

> 状态：**停轮已解除**（用户 2026-10-16 裁定 Q1–Q5，见 §8 与 `reviews/grill-design.md` 的
> `## User Confirmation`）。实现按本文件执行。

## 0. 一句话

让「接入方钉住的 ref」成为**单一事实来源**，同时决定 reusable workflow 文件与 **witnessloop 包**的版本；
并让 CI 日志能看见本次实际用的 ref。

## 1. 现状（逐行实测）

- `initcmd.caller_workflow(gate_ref)`（`src/witnessloop/initcmd.py:30-47`）生成：
  ```
  jobs:
    gate:
      uses: Xingkai98/witnessloop/.github/workflows/gate.yml@v1
  ```
  —— **没有** `with:`。
- `gate.yml` 的输入默认：`witnessloop-ref: {default: "v1"}`（`.github/workflows/gate.yml:19-23`），
  随后 `uvx --from "git+https://github.com/Xingkai98/witnessloop@${{ inputs.witnessloop-ref }}"`（`:57-59`）。
  ⇒ 包版本**完全由调用方是否传 `with:` 决定**；不传就是 `v1`。
- `--gate-ref` 只写进 caller 的 `uses:` 行 + 台账（`init-manifest.json` 的 `gate_ref` 字段，实测本仓台账里是
  `…gate.yml@v1`）⇒ **与包版本没有任何联系**。消费点全集（grill 与 R1 各自独立 grep 复算）：
  `cli.py:43-48` → `initcmd.py:192`（缺省解析）→ `:193`（desired）→ `:46`（`uses:`）→ `:251`（台账）
  → `uninitcmd.py:36-37`（回滚 diff 的期望内容）。**没有第五处**。
- `init` 的契约是**幂等 · 只增不改**：已接入的仓若目标文件与期望内容不同 ⇒ 冲突 ⇒ 退 1
  （`src/witnessloop/initcmd.py:224-234` 与 `:338-351` 的 `conflicting_files`）。**这条决定了本 change 的升级路径必须显式**。
- 本仓**自己**的 caller 也是旧形态（`.github/workflows/witnessloop.yml` 只有 `uses: …@v1`），
  台账里记着它的 sha256（`4861a80c…`）⇒ 本 change 落地时会**自撞**这条冲突判定（dogfood 面，见 D4）。

## 2. 决策

### ✅ D1（**已由真 CI 实测定案，2026-10-16**）：取 **(B′)** —— 包版本取自 reusable workflow **自己的 sha**

**决策细则**：`gate.yml` 把 `inputs.witnessloop-ref` 的 `default` 由字面量 `"v1"` 改成**空串**
（= 「自动」，与「显式传值」可区分），并在**第一个 step** 里解析出**本次实际用的包 ref**：

1. `inputs.witnessloop-ref` **非空** ⇒ 用它（**显式覆盖**，既有 `with:` 调用方不受影响）；
2. 否则 `job.workflow_repository == constants.REPO_SLUG` **且** `job.workflow_sha` 非空
   ⇒ 用 **`job.workflow_sha`**（= 被复用的那个 workflow 文件自己的 commit）；
3. 否则（repository 不匹配 / sha 为空）⇒ 尝试 `job.workflow_ref` 的 `@` 之后那段，
   仅接受 `refs/heads/<分支名>` 与 `refs/tags/<tag名>` 两种形态，并**剥掉前缀**只留分支名/tag 名
   （R2 的 D2 要求写死这一点：实测 `uvx` 对 `@refs/heads/main` 与 `@main` **都能装**，
   所以这是**取舍**不是必须——剥掉后日志与人眼更直白，代价是丢掉「同名 branch 与 tag」的消歧
   （该场景**未实测**）；两种形态任选其一都行，此处选**剥**）；
4. 以上都拿不到 ⇒ **fail-closed 到 `v1`** 并打 `::warning::`（不静默）。

```yaml
inputs:
  witnessloop-ref:
    description: "witnessloop 自身的 ref（钉版本）。留空 = 自动取本 reusable workflow 自己的 commit"
    required: false
    type: string
    default: ""
```

**⚠️ 落点必须是 step，不能是 input 的 `default`**（M7①）：`on.workflow_call.inputs.<id>.default`
的可用上下文是 `github, inputs, vars` 三个（`job` **不在其中**）⇒ `job.*` 只能写在 step 里。

**接受判据是 `job.workflow_repository == REPO_SLUG`**（M7②）：`job.*` 在 called workflow 里指向
**被复用的文件**，但同 owner 的 fork 会把 `REPO_SLUG` 匹配上——所以这条判据是**必要不充分**；
不充分的那一半如实登记在 §4 R6（GHES / fork 面），本 change 不宣称覆盖。

**真 CI 探针原始输出（**跨仓**形态，副本仓 `Xingkai98/asterwynd-wl-switch`，run `38853369550`）**：

```
job.workflow_ref          = Xingkai98/witnessloop/.github/workflows/probe-ref.yml@refs/heads/probe/workflow-ref
job.workflow_sha          = 6e2ec4dc7955d6d155987a667040b126acab983b   ← reusable 自己的 commit
job.workflow_repository   = Xingkai98/witnessloop
job.workflow_file_path    = .github/workflows/probe-ref.yml
github.workflow_ref       = Xingkai98/asterwynd-wl-switch/.github/workflows/probe-caller-xrepo.yml@refs/heads/probe/xrepo   ← caller
github.workflow_sha       = 2778bc24e13c8fdd18e18765c81eb0ff731e6568   ← 接入方自己的 commit（不是 reusable 的）
github.job_workflow_sha   = （空）
```

- caller（副本仓）那一侧：`on: push`、分支 `probe/xrepo`、
  `uses: Xingkai98/witnessloop/.github/workflows/probe-ref.yml@probe/workflow-ref`（**跨仓**）。
- ⇒ **`job.workflow_sha` 唯一确定 reusable 自己的 commit**（`github.workflow_sha` 是接入方自己的，
  用它会在 witnessloop 仓取一个不存在的 commit ⇒ 全量硬红）。**故 (B′) 可行** ✓。
- 对照的**早一轮**同仓探针（run `38852445945`）给出同向结论；该轮是**同仓**形态（caller 与 callee 同仓）。
- **探针的清理**（R2 的 D4 订正措辞）：**远端已清理**——witnessloop 上的临时分支与文件已删
  （复查 404）；**本地仍留** `probe/workflow-ref` 分支（`c7aa037`），那是 Q1 唯一可追溯的**本地物证**，
  刻意不删。本文档保存原始输出即其落点（K8）。
  ⚠️ **证据等级如实标注**（R2 的未验证项 1）：这段探针输出是**单一来源、不可复现**的二手文本
  （当时的分支已删、两个 sha 取不到、issue #30 正文里**没有**这段 context dump）。
  ⇒ 依赖它的叙述（「`github.workflow_sha` 是接入方自己的 commit ⇒ 用它会硬红」那条）**另有一份独立依据**：
  GitHub 官方 contexts 文档明写 `job.workflow_ref` 在 job **直接定义在 workflow 文件里**时**等同**
  `github.workflow_ref` ⇒ 反推：job 定义在 **reusable** 里时两者**不同**，`job.workflow_sha` 绑的是
  「the workflow file that defines the current job」。**Q1 的结论不依赖那份探针**；
  被削弱的只是「(B) 已被证伪」这一句的**实测**强度（它还有文档依据 + R2 复现的
  「拿一个不在本仓的 sha 给 `uvx` ⇒ `upload-pack: not our ref` 硬红」这条机制旁证）。

前两轮「未跑成」的留档（探针分支 `probe/workflow-ref` / `c7aa037` 因副本仓 caller PR #5 的 base 冲突
DIRTY ⇒ 无 merge commit ⇒ 任何 workflow 都不跑）**已被上面这轮真跑成的跨仓探针取代**，不再开问题。

### D1 的选项对照（留档，供后来者理解为什么不是 (A)/(B)）

- **(A) caller 显式双写**：`init` 生成的 caller 同时写 `uses: …@<ref>` 与 `with: {witnessloop-ref: "<同一个 ref>"}`。
  优点：直白、可本地复算；缺点：**存量接入方仍要过一次工具**，且留下**第二个可写点**
  （人能只改 `with:` 不改 `uses:` ⇒ 又回到两处不一致）。⇒ 降级为**显式覆盖**手段，不再是主机制。
- **(B) 从 `github.workflow_ref` 解析**：**已证伪**——探针实测 `github.workflow_ref` 指 **caller**，
  用它会把**接入方自己的 ref**当成包 ref（`uvx` 去 witnessloop 仓取一个不存在的 ref ⇒ 全量硬红）。
  这里如实记录：**这一条是本 change 最重要的实测订正**。
- **(C) 版本台账**（`init` 写一份版本文件、`check` 读它）：引入第二个事实来源，与「一次入口」相抵 ⇒ **不取**。

### D2 既有接入方的升级路径 SHALL 是单一、显式、可复算的动作 —— **裁定 (a)**

`init` 的「只增不改」不许被本 change 打破（它是**唯一**的升级入口，`initcmd.py:9-13` 的教训：
tests 文件就是为绕开这条冲突判定才走了独立路径）。故：

- **升级动作（裁定 (a)）**：对**已接入**的仓，显式给 `--gate-ref` 时 ⇒ **重写 caller + 同步台账**
  （`init-manifest.json` 里该条目的 `sha256` **与** `gate_ref`），其余文件照旧只增不改。
  两条硬约束（grill M2，均已实测）：
  1. **必须同步台账**：只重写 caller 会让「磁盘 ≠ 台账」——plain `init` 走**漂移**分支退 1、
     `uninit` **拒删**退 1。
  2. **作用域限定「已接入分支」**（`initcmd.py:205` 之后）：否则会**静默覆盖**新仓里外来的 caller，
     推翻 `tests/test_init.py:128-141` 的保证。
- **先例纠正（grill CD6）**：`--test-command`（`constants.py:19-27`）**不进台账**，口径与 caller **相反**，
  **不能**援引；正确先例是 **`--policy`**（`initcmd.py:344-351` 的「显式给定时按新内容落地」一侧）——
  两者都是「**工具自己生成的产物**」，台账可由工具一致地维护。
- **死锁措辞降级（R1 K3）**：只重写 caller 的后果**不是**「永久死锁 / 再也卸载不掉」，
  而是一个**响亮、可恢复的分叉态**——三条恢复路径均已实测：① `git checkout -- <caller>` ⇒
  plain `init` EXIT=0；② `rm <caller>` ⇒ `uninit` EXIT=0（`uninitcmd.py:56-57` 对缺失文件 `continue`）；
  ③ 台账该条目 `sha256: null` + 同步 `gate_ref` ⇒ `init`/`uninit` 均 EXIT=0。且
  `grep -rn "INIT_MANIFEST" src/witnessloop/*.py` 证明 **`check` 不读台账** ⇒ 分叉期间门禁照常工作，
  坏的只是 `init`/`uninit` 两个动词。
- **已知工具外出口（R1 K7，登记 + 明确非目标）**：`initcmd.py:301` / `uninitcmd.py:59` 用的是
  `entry.get("sha256") and …` ⇒ **任何 `sha256` 为 `null`/缺失的台账条目，两条判定都直接跳过**；
  而 `build_manifest` 只对 `self` 条目写 `null`（`initcmd.py:104`）——即「`null` 的语义」是**约定**、
  不是**强制**。本 change **不收紧**它（收紧会动 `uninit` 的既有判定语义，属另一个面），
  但登记在此：它是升级路径的**第二条出口**，裁定 (a) 的理由是「出口**好用** vs **难用**」，不是「有没有出口」。

### D3 「静默」SHALL 被消掉——并且**包能自报 ref**（R1 K1 订正）

- `gate.yml` SHALL 在跑 `check` **之前**把本次的 ref **打进日志**（`::notice::`，见 D1 的 step），
  使 CI 日志直接可读；**对所有形态的 ref 都成立**（tag / 分支 / **sha**）。
- **R1 K1 订正（原稿此处为假）**：原稿写「包自身**无法**报告自己在用哪个 ref / 构建产物里没有 ref 信息」——
  **实测证伪**。`uvx --from "git+https://github.com/Xingkai98/witnessloop@v1"`（uv 0.13.1，
  与 `gate.yml` 同一条 uvx 调用）装出的 dist-info 带 PEP 610 的 `direct_url.json`：
  ```json
  {"url":"https://github.com/Xingkai98/witnessloop",
   "vcs_info":{"vcs":"git","commit_id":"ae992565ee2162e5b272af471e9adf895e7f83fb","requested_revision":"v1"}}
  ```
  ⇒ **`check` 可以自报 ref，且连 resolved commit 一起报**（比 `echo` 多一维：`echo` 只能打出**请求的 ref**，
  打不出解析后的 commit，而 issue #30 的验收证据恰恰是 resolved sha）。
- **裁定（Q4 = 作者推荐）**：**纳入**——`check` 打印自己实际跑的 ref，**尽力而为**：
  读 `direct_url.json` 的 `vcs_info.requested_revision` / `commit_id`，取不到就打 `<未知>`，
  **绝不因此失败**（本地 editable / 源码直跑没有它）。
- **仍然成立的那半句**（不要一并删掉）：`__version__` 恒 `"0.1.0"`、**与 tag 无关**
  （`src/witnessloop/__init__.py:22`、`pyproject.toml:3`、`uv.lock` 同值；`checkcmd.py` 全文无版本输出）
  ⇒ **版本号**不能用来判断跑的是哪版，所以本 change 走的是 **VCS 元数据**这条链，不是版本号。

### D4 本仓自己的迁移 SHALL 是**(post-merge) 后继动作**，不在本 PR 内

原稿（grill CD7 / M4）写过「同一个 diff 里跑一次 `init` 自证不冲突」，**该步骤在本 PR 内不可执行**：

1. **迁移的目标 ref 在本 PR 内不存在**：本仓 caller 的 `uses:` 要指向一个**含新 gate.yml 的 ref**，
   而这样的 ref 只有在本 change 合并之后才存在（出厂默认仍是 `@v1` = `ae99256`，
   `git show v1:.github/workflows/gate.yml` 是**改动前**的文件、`git diff --stat v1..HEAD -- .github/workflows/gate.yml` **为空**）。
2. **自证命令今天本来就红，且与 caller 无关**（grill CD7 实测）：本仓 plain `init --dry-run` **今天已退 1**，
   且 diff **只涉及 `.witnessloop/policy.json`**（`require_change_for` 与三个 stage 键）；
   只有 `init --dry-run --policy <seed>` 才是「幂等，无改动」EXIT=0 —— 而 seed 是**仓外的临时文件、刻意不入库**
   （`README.md:111-113`；`README.md:225` 明写本仓 `init` 早就跑不动）。
3. ⇒ 迁移动作**拆成 post-merge 的后继动作**，与 Q3 的发布动作同批（见 §6 待办）：
   更新本仓 caller + 台账，并在同一批里建 `openspec/changes/gate-ref-pins-package/workflow-events.jsonl`
   写一条 `protected_path_write`（`artifact_path` 指向 `.witnessloop/init-manifest.json`、`reason`/`approved_by` 非空），
   否则改台账这个 **`M`** 必红（`policy.py:18-23` 的不变集 + `checkcmd.py:312-335`）。
   **本 PR 不动** `.github/workflows/witnessloop.yml` 与 `.witnessloop/init-manifest.json`。

### D5 非目标：与 #31 正交

`D` 侧掉队（issue #31）不在此列；本 change 只动「跑哪个包」这条链。

### D6 非目标：不收紧 `sha256: null`（K7）

见 D2 末条。本 change 只在文档里登记这条既有语义，不改判定。

### D7 caller 文件不受任何保护 —— **裁定：只登记文档，不加机械门**

R1 B3 实测：用工具自己的 `paths.matches_any` 跑本仓 policy ⇒

```
.github/workflows/witnessloop.yml：protected=False invariant=False require_change=False
```

⇒ 一个 PR 可以把 caller 的 `uses:` 改成**自己 fork 的 gate.yml**，`check` 不会报一条 finding。
**裁定（Q5 = 作者推荐）**：本 change **不**新增保护面（把 caller 纳入不变集会影响所有既有接入方，
且 required check 的名字 `gate / check` 前半来自 caller 的 job 名——那是个**平台面**的取舍，
值得单独一个 change），只把这条边界**写进 `docs/gate.md §7` 能力边界**。

## 3. 接线点（实现清单）

1. `.github/workflows/gate.yml`：
   - `inputs.witnessloop-ref.default` 由 `"v1"` 改 `""`；
   - **新增第一个 step**（`id: wl-ref`）：按 D1 解析 + `::notice::` 打日志 + 写 `$GITHUB_OUTPUT`；
   - `uvx` 那一步改用 `${{ steps.wl-ref.outputs.ref }}`。
2. `src/witnessloop/initcmd.py`：新增「已接入分支」里的显式 `--gate-ref` 重写 + 台账同步（D2）。
3. `src/witnessloop/checkcmd.py`：`check` 自报本包 VCS ref（D3 / Q4）。
4. `src/witnessloop/constants.py`：`DEFAULT_GATE_REF` **保持 `@v1`**（Q3 把「改默认值」列为 post-merge 事项），
   但注释要写清「ref 同时决定包版本」与「显式 `--gate-ref` 会重写 caller + 台账」。
5. 文档：`docs/gate.md`（§1 的 caller 行、**§7 能力边界**加 D7）、`README.md:20`（`uv tool install …@v1` ——
   **CLI 的安装 ref 与包版本同源**）、`README.md:119-121`（「`@v1` 是滚动大版本」须与目标 3「不动 `v1` tag」表态）、
   `README.md:170-177`（前置条件段的 `@v1`）、`docs/design.md:56,73`（K6 补的两处）。
   `templates/` 与 `plugin/` **零命中**（grill #8 / R1 E7 各自 grep 复核）⇒ 不动。

## 4. 风险

| # | 风险 | 处置 |
|---|---|---|
| R1 | ~~`github.workflow_ref` 语义未验证~~ | **已消解**：跨仓真 CI 探针实测（§2 D1）⇒ 定案 (B′) |
| R2 | **全局面是「新 ref 发布的那一刻」**（M1 订正），且**受影响的仓有两类**（R2 的 L6 补第二类）：① 把 `uses:` 指到含新 gate.yml 的 ref 的仓——在**它们动手的那一刻**切换；② `uses:` 写成**分支形态**（如 `@main`）的仓——**在合并那一刻零动作**切换包来源 | 发布说明里写明「这是一次**全局**行为变化」并**点名两类仓**；给回退路径（把 `uses:` 指回旧 ref，或显式 `with: witnessloop-ref:`） |
| R3 | ~~升级路径把接入方卡死~~ | **已降级**：需一次显式动作，且三条恢复路径实测可用（D2/K3） |
| R4 | 把 `__version__`/tag 绑起来的需求被夹带进来 | §3 非目标；D3 明写本 change 走 VCS 元数据而不是版本号 |
| R5 | 本仓自撞（policy 轴本来就红 + 台账 `M` 的解释事件） | D4：迁移拆成 post-merge 动作并写全三件事 |
| R6 | **`job.*` 在 GHES 上不可用**（R1 B6：文档明写 `not available on GitHub Enterprise Server`）；同 owner 的 **fork** 也能匹配上 `REPO_SLUG` 判据 | 两条都**如实登记、不宣称覆盖**：GHES / fork 场景落到 fail-closed ⇒ 吃 `v1`，但**日志里有 `::warning::`**（不静默）；判定不充分的那一半留给后续 change |
| R7 | `uninit` 的 diff 质量下降 | 新生成器对旧形态 caller 会打出「看起来要变成新形态」的 diff；**判定仍只看台账 hash**，回滚正确性不受影响（R1 E5 复核成立） |
| R8 | `refs/pull/N/merge` 的定性措辞 | 只说「**不是稳定的可安装 ref**」；**不**声称它必然安装失败（R1 E3：该 ref 通常能被 git fetch 到，未实测 uv 行为） |

## 5. 测试策略（TDD）

1. **解析面（gate.yml 的解析 step，从 YAML 抽出后真跑 bash）**：覆盖
   `job.workflow_sha` 主路径 / 显式 `with:` 覆盖 / repository 不匹配 / sha 缺失走 `workflow_ref` 兜底
   （`refs/heads/*` 与 `refs/tags/*`）/ 两样都缺 / `job.workflow_ref` 是 `refs/pull/N/merge` 畸形
   ⇒ 后者**fail-closed 退 `v1` 且打 warning**。用 `GITHUB_OUTPUT` 捕获解析结果。
2. **生成面**：`init --gate-ref <ref>` 生成的 caller 里 `uses:` 逐字等于该 ref（(B′) 下 `caller_workflow()`
   字节**不变**，故这条是回归性质的守卫）。
3. **升级路径**：既有形态的 caller（无 `with:`）+ 显式 `--gate-ref <新>` ⇒ **重写 caller + 同步台账
   （`sha256` 与 `gate_ref`）**、EXIT=0、随后 plain `init` 仍幂等、`uninit` 仍可用（终态是不动点）；
   plain `init` 与「不带 flag 的 `--policy` 语义」**照旧**。
4. **日志面**：`gate.yml` 里 ref 进 `::notice::` 的那一行（断言文件内容，不跑 CI）。
5. **自报面**：`checkcmd` 读 `direct_url.json` 的最佳努力实现——有 `vcs_info` 时打出
   `requested_revision`/`commit_id`，没有时打 `<未知>` 且**不影响退出码**。
6. **回归**：`init` 幂等 / `uninit` 回滚 / 冲突判定 / 新仓目标文件已存在仍冲突（`tests/test_init.py:128-141`）/
   tests 文件独立路径 —— 全部照旧。

## 7.9 对抗轮记录

### R1（报告见 `reviews/grill-adversarial.md`）

独立零记忆对抗者判定**不收敛**：证伪 4 条（**全部针对本稿自己的断言**）+ 8 条必须修改项（K1–K8）。
当时的处置方式是在本节记一张表（7dfe299），**但正文没有改**（K1 就因此漏在 `D3` 里到 545456c 都在）。
**本次（停轮解除后）已把 K1–K8 逐条落进正文**：

| # | R1 发现 | 落点 |
|---|---|---|
| K1 | 「包无法自报 ref」「构建产物里没有 ref 信息」**是假的**（PEP 610 `vcs_info` 实测存在） | §2 D3 改写 + §8 已定案表 + `spec.md` 的「能力边界」段重写；**Q4 裁 (a)：纳入自报** |
| K2 | 「没有任何提示」**是假的**（空缓存 `uvx` 自己打印 resolved sha） | `proposal.md` 机制段改写 |
| K3 | 「**永久**死锁 / 再也卸载不掉」**过强** | §2 D2 降级为「响亮、可恢复的分叉态」+ 三条恢复路径 |
| K4 | 「本 change 内只做 `init --dry-run --policy <seed>` 自证」在 (A) 下会 EXIT=1 | §2 D4 改写：本 PR **不做**本仓迁移，自证条件与 post-merge 动作一并写清 |
| K5 | 「`v1` 落后 47 个提交」**计数口径未标注**（R1 报 50） | **复算订正**：计数**取决于测量哪个 ref** —— `git rev-list --count v1..origin/main` = **47**，而在当时的 docs 分支上（多 3 个文档提交）测出来是 50。⇒ 改写成不依赖计数的表述（「落后数十个提交，`src/` 差 6 文件 +922/−96」），并在 `grill-design.md` 标注计数基准。**R1 的 K5 本身是测量口径造成的假差异。** |
| K6 | 同源文档清单漏 `docs/design.md:56,73` | §3 接线点 5 |
| K7 | 第四条升级路径（台账 `sha256: null`）未登记 | §2 D2 末条 + D6（登记为已知出口，**明确不收紧**） |
| K8 | 探针文件/结果无落点 | §2 D1 写明「原始输出保存在本文档即落点，探针文件已全部清理」；`tasks.md` 3.0 同步 |

### R2（报告见 `reviews/grill-adversarial-r2.md`）

独立零记忆对抗者判定**不收敛**：**R1 的 K1–K8 逐条核对「确实落进正文」**（判据②满足），
但**本轮新证伪 2 条**（判据①不满足）+ 4 条新缺口，编号 **L1–L6**。**已逐条落库**：

| # | R2 发现 | 落点 |
|---|---|---|
| L1 | **post-merge 时序反了** ⇒ 打出的 `v1.7.0` 里 `DEFAULT_GATE_REF` 仍是 `@v1`，「新接入方默认吃新包」在发布那一刻落空（且更隐蔽） | `tasks.md §6` 整段重写：**先改常量 → 再 tag 含该常量的提交**；补 `README.md:20` 的新值进动作清单与 6.7 的验收命令 |
| L2 | 文档把 `init --gate-ref` 写成「单一升级动作」，但**旧 CLI 上它不存在**（实测 EXIT=1 + 把人指向 policy 的误导文案） | `docs/gate.md §1.2` 与 `README.md` 的 recipe 都改成**两步**（① 先升 CLI ② 再换 ref）+ 如实登记旧 CLI 的症状 |
| L3 | **没有任何测试钉 `inputs.witnessloop-ref.default == ""`** ⇒ 改回 `"v1"` 时机制静默退化且 665 条全绿 | `tests/test_gate_workflow.py::test_witnessloop_ref_input_default_is_empty` |
| L4 | `--gate-ref` + 冲突 `--policy` 的**组合语义未写死**（实测 EXIT=1 但已落盘） | `spec.md` 新增该 Scenario（定为「先写后判、不回滚」）+ `initcmd` 在冲突文案前点明「已落盘、不回滚」+ `tests/test_init_gate_ref.py` 的钉子 |
| L5 | spec 缺两条场景（`--dry-run` / 台账缺 caller 条目） | `spec.md` 补两条 Scenario |
| L6 | 「全局行为变化」**说小了一类**：分支形态 caller（`@main`）**合并那一刻零动作**切换 | `design §4 R2`、`docs/gate.md §1.2`、`tasks.md 6.5` 三处点名两类仓 |

**R2 的低危观察也一并落库**（不是必须修改项，但便宜且正确）：

- D1：`docs/gate.md §1.2` 补「`check` 自报那行**由新版包起**才有」（旧包跑 `check` 看不到它）。
- D2：兜底**剥不剥** `refs/heads/` 前缀 → 见 §2 D1 第 3 条，已写死为**剥**。
- D3：`installed_vcs_ref` 改**宽 except**（成因枚举挡不住 `zipfile.BadZipFile` 这类意外，
  而规格是「SHALL NOT 因此改变退出码」）⇒ 按**规格**兜而非按成因枚举；测试钉住「抛什么都吞掉」。
- D4：探针清理措辞改成「**远端**已清理；本地分支刻意保留」，并给探针输出标**证据等级**（见 §2 D1）。
- D6：spec 第 5 条 Requirement（caller 不受保护要登记）补一条**机械钉子**
  （`tests/test_docs.py` 断言 `docs/gate.md` 里那段文本在）——它此前只靠人读。
- D5（**登记、本 change 不修**）：机械门判的是「**候选小节里**出现的每个 `Q<n>` 都有确认」——
  把某个 `### Q4` 整段**搬到另一个不相干的二级标题**下就能让它免于确认（R2 实测：仍然 0 findings）。
  ⇒ 本文件与 `grill-design.md` 里「两份文件的 Q 集合 = {Q1…Q5} 逐条一致」这句话**不是**机械判据，
  只由人复核。改标题绕不过去（fail-closed）。要机械封死属于 `evidence.py` 的机制面（须另开 change），
  本 change 明确**不动**——与 Q5 同一种取舍。

**R2 未能证伪的部分**（= 既有结论成立，一并记明，避免读者以为全盘被推翻）：(B′) 的上下文落点有
**官方文档逐字**支撑；`uvx` 对 40 位 sha / 分支 / tag / `refs/heads/*` / `refs/tags/*` / 带斜杠分支
**八种形态全部实跑可用**；解析 step 的 8 个 case 行为级符合 spec；升级终态是**不动点**；
作用域守卫**没有**打破「新仓已存在 caller ⇒ 冲突且整体不落盘」；`check` 自报从不因取不到元数据而失败；
D4 的两条实跑事实逐条成立。R2 还**独立复算确认了 K5 是 R1 自己错**。

### R2 的一条 Open Question 与本 change 的处置

- R2 的 Q1（`--gate-ref` + 冲突 `--policy` 该「先写后判」还是「两轴一起不落盘」）：
  **采纳 R2 的推荐 = 保持现状（先写后判、不回滚）+ 把文案改准**。理由即其正文给的三条：
  ① 与 `--test-command` 的既有先例同口径；② 「两轴一起不落盘」会让本 change 的主入口
  被一个**正交**参数连坐；③ 现状不产生分叉态、恢复路径单一。
  ⚠️ 这是**作者按独立审阅的推荐落库**，不是用户拍板——已写进 `spec.md` 的 Scenario，
  若用户不同意，改的是那一条 Scenario + `initcmd` 的落盘顺序（面很小）。

## 8. 停轮问题（**Q1–Q5 已逐条裁定**，用户答复原文见 `reviews/grill-design.md` 的 `## User Confirmation`）

> 本节的编号与 `reviews/grill-design.md` 的 `## Open Questions` **逐条一致（Q1–Q5）**。

### 已由代码 / 实测 / 用户裁定、移出队列

| 问题 | 定案 | 依据 |
|---|---|---|
| Q1 修法形态 | **(B′)**：包 ref = `job.workflow_sha`（兜底 `job.workflow_ref`），`REPO_SLUG` 判据，fail-closed 退 `v1` | 跨仓真 CI 探针（§2 D1 原始输出） |
| `check` 能不能自己打印「我在用哪个 git ref」？ | **能**（读 PEP 610 `vcs_info`），**且裁定纳入**（尽力而为、取不到不失败） | `uvx` 真装实测（§2 D3）；Q4 裁定 |
| 要不要动 `v1` tag？ | **不动** | issue #30 的期望；tag 是别人依赖的发布物（Q3 裁定） |
| 要不要顺手修 #31？ | **不** | 正交（D5） |

### Q1 修法形态 → **裁定 (B′)**（详见 §2 D1；跨仓探针原始输出在上）

### Q2 升级动作 → **裁定 (a)**：显式 `--gate-ref` ⇒ 重写 caller **+ 同步台账**（详见 §2 D2）

### Q3 收益在哪个 ref 上兑现 → **裁定 (a)**：发新 tag `v1.7.0` 并把 `DEFAULT_GATE_REF` 指过去

- **⚠️ 打 tag 与改默认值都是 `(post-merge)` 事项**：本 change **不动 `v1` tag、也不创建 `v1.7.0`**，
  `constants.DEFAULT_GATE_REF` 在本 PR 内**保持 `@v1`**。
- 理由（grill Q3 的三条具体例子）：不发新 ref ⇒ 新接入方拿到的仍是旧包（一号期望落空）；
  **动 `v1` tag** ⇒ 存量仓会**同时**换 workflow + 换包（`README.md:119-121` 的「滚动大版本」承诺），
  与目标 3 正面冲突且让人失去版本稳定性保证；**发新 tag + 改默认值** ⇒ 新接入方默认吃到新包，
  存量仓仍自己把 `uses:` 指过去（配合 Q2 的动作）。
- **发布说明 SHALL 写清这是一次全局行为变化**（§4 R2），并给出回退路径。

### Q4 `check` 要不要自报它跑的 ref → **裁定 (a)**：纳入，尽力而为、取不到不失败

- 依据：R1 K1 的实测（`vcs_info.requested_revision` / `commit_id` 真实存在），它比 gate.yml 的 `echo`
  **严格更强**（多出 resolved commit 这一维）。
- 代价（如实登记）：动了 `checkcmd.py` ⇒ 扩大本 change 的受管控面；本 change 接受。

### Q5 caller 文件不受任何保护，要不要在本 change 表态 → **裁定**：只登记文档（`docs/gate.md §7`），不加机械门

- 依据：R1 B3 实测 `protected=False invariant=False require_change=False`；把 caller 纳入保护面
  会同时改变所有既有接入方的判定（且 `gate / check` 的 required 名字面是平台面取舍）⇒ 另开 change。
