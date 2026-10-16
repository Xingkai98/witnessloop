# Design: gate-ref-pins-package

## 0. 一句话

让「接入方钉住的 ref」成为**单一事实来源**，同时决定 reusable workflow 文件与 **witnessloop 包**的版本；
并让 CI 日志能看见本次实际用的 ref。

## 1. 现状（逐行实测）

- `initcmd.caller_workflow(gate_ref)`（`src/witnessloop/initcmd.py:32-46`）生成：
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
  `…gate.yml@v1`）⇒ **与包版本没有任何联系**。
- `init` 的契约是**幂等 · 只增不改**：已接入的仓若目标文件与期望内容不同 ⇒ 冲突 ⇒ 退 1
  （`src/witnessloop/initcmd.py:224-234` 的 `conflicting_files`）。**这条决定了本 change 的升级路径必须显式**。
- 本仓**自己**的 caller 也是旧形态（`.github/workflows/witnessloop.yml` 只有 `uses: …@v1`），
  台账里记着它的 sha256（`4861a80c…`）⇒ 本 change 落地时会**自撞**这条冲突判定（dogfood 面，见 D4）。

## 2. 决策

### D1 单一事实来源：包版本 SHALL 取自「workflow 自己的 ref」

**选项**（本 change 的真实取舍，见 §8 Q1）：

- **(A) caller 显式双写**：`init` 生成的 caller 同时写
  `uses: …gate.yml@<ref>` 与 `with: { witnessloop-ref: "<同一个 ref>" }`。
  优点：直白、可本地复算（看生成文件就知道两处一致）；缺点：**既有接入方不受益**（他们的 caller 没 `with:`），
  且要改 `init` 的生成契约 ⇒ 撞「只增不改」的冲突判定（D2）。
- **(B) 让默认值等于「workflow 自己的 ref」**：`gate.yml` 里把 `witnessloop-ref` 的默认值改成
  **从解析出的 ref**（形如 `owner/repo/.github/workflows/gate.yml@<ref>`）。
  ⚠️ **grill 实测订正（M1）**：**「存量仓零动作即生效」不成立**——
  `git diff --stat v1..HEAD -- .github/workflows/gate.yml` **为空**、`git show v1:.github/workflows/gate.yml`
  的默认值就是 `"v1"`、且 `v1` 落后 47 个提交 ⇒ **存量仓跑的是 `v1` 那份 gate.yml，新默认逻辑根本不会执行**。
  ⇒ (B) 的真实收益只有一条：**改完 `uses:` 那一处之后，包版本自动跟着一致**（不必再管第二个输入）；
  存量仓仍必须先改 `uses:`（或过一次工具）。
  缺点：依赖 `github.workflow_ref` 在 **called workflow** 里指向**被调用的那个 workflow 及其 ref**
  —— 这条**本工作区无法验证**（要真 CI），见 §4 R1 与 §8 Q1。
- **(C) 版本台账**（`init` 写一份版本文件、`check` 读它）：引入第二个事实来源，与「一次入口」相抵 ⇒ **不取**。

### ✅ 已由**真 CI 实测定案（2026-10-16）**：取 **(B′)**

**2026-10-16 真 CI 探针（同仓 reusable，push 触发）原始输出**（副本仓 `Xingkai98/asterwynd-wl-switch`，run 38852445945）：
```
PROBE JOB_WORKFLOW_REF        = Xingkai98/asterwynd-wl-switch/.github/workflows/probe-reusable.yml@refs/heads/master
PROBE JOB_WORKFLOW_SHA        = 8c218a1e9a2b9d27c3a686755b2987bac6fbe186
PROBE JOB_WORKFLOW_REPOSITORY = Xingkai98/asterwynd-wl-switch
PROBE JOB_WORKFLOW_FILE_PATH  = .github/workflows/probe-reusable.yml
PROBE GH_WORKFLOW_REF         = Xingkai98/asterwynd-wl-switch/.github/workflows/probe-caller.yml@refs/heads/master   ← caller 自己
PROBE GH_WORKFLOW_SHA         = 8c218a1e9a2b9d27c3a686755b2987bac6fbe186
PROBE GH_JOB_WORKFLOW_SHA     = <未定义或空>
PROBE GH_REF                  = refs/heads/master
```
⇒ **`job.workflow_ref` / `job.workflow_sha` 指向「被复用的那个 workflow 文件」及其 ref/sha**（文档口径证真 ✓）；
`github.workflow_ref` 指 **caller** ✓。⚠️ 本探针是**同仓**形态（caller 与 callee 同仓、ref 是分支）；
**跨仓**（接入方调 witnessloop 的 `gate.yml@v1`）**未实测**，但字段语义按文档一致 ⇒ 用法同。

**决策**：`gate.yml` 把 `witnessloop-ref` 的**默认值**改为由 **`job.workflow_sha`**（兜底 `job.workflow_ref` 的 ref 部分）推导，
并把「`job.workflow_repository == constants.REPO_SLUG`」作为**接受判据**（不满足 ⇒ 退 `v1` 并打日志，M7）。
**不再**推荐 (B)（`github.workflow_ref` = caller，用它会把 caller 的 ref 当包 ref ⇒ 全量硬红）；
(A)（caller 双写 `with:`）降级为**显式覆盖**手段（D2 的升级动作仍走它）。

### D2 既有接入方的升级路径 SHALL 是单一、显式、可复算的动作

`init` 的「只增不改」不许被本 change 打破（它是**唯一**的升级入口，`initcmd.py:9-13` 的教训：
tests 文件就是为绕开这条冲突判定才走了独立路径）。因此：

- **在 (B) 下**：既有接入方**无需改任何文件**（他们的 `uses:` ref 即包版本）；要**升级**时改
  `uses:` 的 ref（一处），或跑 `init --gate-ref <新 ref>`（显式 flag ⇒ 与 `--test-command` 同款「显式意图优先」）。
  ⚠️ 但 `init --gate-ref <新>` 现在会**撞冲突**（caller 内容不同）⇒ 见 Q2。
- **在 (A) 下**：必须有显式覆盖动作（推荐 `init --gate-ref <ref>` 改为「显式给定时**总是重写 caller**」，
  与 `--test-command` 的既有先例一致：`constants.py:24-27`「显式意图优先，不得静默 no-op」）。

### D3 「静默」SHALL 被消掉——但要如实说明边界

- `gate.yml` SHALL 在跑 `check` **之前**把本次的 ref **打进日志**（`echo`，含 `::notice::`），
  使 CI 日志直接可读；**对所有形态的 ref 都成立**（tag / 分支 / **sha**）。
- ⚠️ **做不到的部分要明说**：`check` **无法**打印「自己在用哪个 git ref」——
  包是 `uvx` 现场构建的 wheel，`src/witnessloop/__init__.py:22` 的 `__version__` 目前恒为 `"0.1.0"`
  （**与 tag 无关**），构建产物里没有 ref 信息 ⇒ 只能靠 D3 第一段的**日志侧**可见性。
  （把 `__version__` 与 tag 绑起来属**发布纪律**，与本 change 正交 ⇒ §3.5 非目标。）

### D4 本仓自己 SHALL 一起迁移（dogfood）

本仓的 caller 与台账（`.github/workflows/witnessloop.yml`、`.witnessloop/init-manifest.json`）在实现时
SHALL 一起更新到新形态。**grill 订正（M4）**，三件事必须写全：

1. **自证命令**：`init --dry-run --policy <seed>`（plain `init` **今天本来就退 1**，与 caller 无关 ⇒ 不能拿它当自证）。
2. **解释事件**：建 `openspec/changes/gate-ref-pins-package/workflow-events.jsonl` 并写一条 `protected_path_write`
   （`artifact_path` 指向 `.witnessloop/init-manifest.json`、`reason` / `approved_by` 非空），
   否则改台账这个 **`M`** 必红（`policy.py:18-23` 的不变集 + `checkcmd.py` 的保护写判定）。
3. **时序**：迁移动作**拆成「合并 + 发布新 ref 之后」的后继动作**——同一个 diff 里**没有可指向的新 ref**
   （新 gate.yml 只在合并后才存在）⇒ 这一步**不能**和实现同一个 PR。

### D5 非目标：与 #31 正交

`D` 侧掉队（issue #31）不在此列；本 change 只动「跑哪个包」这条链。

## 3. 接线点（实现清单）

1. `.github/workflows/gate.yml`：默认值改 `github.workflow_ref` 解析（(B)）/ 或加 `echo` 日志（两种情况都要）。
2. `src/witnessloop/initcmd.py`：`caller_workflow()` 视 Q1 裁定改/不改；`--gate-ref` 的覆盖语义视 Q2 裁定。
3. `src/witnessloop/constants.py`：若改生成契约，`DEFAULT_GATE_REF` 的注释要写清「ref 同时决定包版本」。
4. 本仓自己的 caller + 台账（D4）。
5. `docs/gate.md` / `README.md`：接入指引里「怎么钉版本 / 怎么升级」一段。
   **grill M6 补两处必须一起改**：`README.md:20`（`uv tool install git+…@v1`——**CLI 的安装 ref 与包版本同源**，
   直接影响「新接入方会不会吃到旧包」）与 `README.md:119-121`（「`@v1` 是滚动大版本」——必须表态它与
   本 change 目标 3「不动 `v1` tag」的关系）。

## 4. 风险

| # | 风险 | 处置 |
|---|---|---|
| R1 | `github.workflow_ref` 在 called workflow 里的**取值语义**未经验证（(B) 的基石） | 实现期**先在副本仓实测**；证伪则退 (A)（§8 Q1） |
| R2 | **全局面不是「改默认值」这个动作，而是「新 ref 发布的那一刻」**（M1 订正）：接入方把 `uses:` 指到含新 gate.yml 的 ref 时，**所有**这样的仓同时切换包来源解析 | 发布说明里写明「这是一次**全局**行为变化」；并给回退路径（把 `uses:` 指回旧 ref） |
| R3 | `init` 的冲突判定被本 change 撞红（既有接入方跑 plain `init` 会退 1） | D2：显式动作 + D4 本仓先迁 |
| R4 | 把 `__version__`/tag 绑起来的需求被夹带进来 | §3.5 明写非目标 |

## 5. 测试策略（TDD）

⚠️ **停轮门**：拿到用户对 §8 的答复之前**不写任何实现/测试代码**。以下为实现期的用例清单：

1. **生成面**：`init --gate-ref <ref>` 生成的 caller 里，**ref 与包版本同源**（(A)：文件里两处逐字相等；
   (B)：文件里 `uses:@<ref>`，且 `gate.yml` 的默认解析给出同一 ref——以后者用**纯函数**解析 `workflow_ref` 字符串来测）。
2. **解析面（纯函数）**：给 `owner/repo/path@refs/tags/v1` / `@refs/heads/main` / `@<sha>` 三种形态，
   解析出的 ref 逐字正确；畸形输入 ⇒ **fail-closed**（退回 `v1` 并**打日志**，不静默）。
3. **不匹配可见性**：`gate.yml` 的日志步骤里出现本次 ref（断言文件内容，不跑 CI）。
4. **升级路径**：既有形态的 caller（无 `with:`）在 (B) 下**不需要改**（回归用例：plain `init` 在 (B) 下不产生冲突）；
   在 (A) 下断言「显式 `--gate-ref` 会重写 caller、plain `init` 仍只增不改」。
5. **回归**：`init` 的幂等 / `uninit` 回滚 / 冲突判定 / tests 文件独立路径**全部照旧**。

## 7.9 对抗轮（R1，报告见 `reviews/grill-adversarial.md`）

独立零记忆对抗者判定**不收敛**：证伪 4 条（**全部针对本稿自己的断言**）+ 8 条必须修改项（K1–K8）。
其中**已在本节落库**的关键订正：

| # | R1 发现 | 处置 |
|---|---|---|
| 1 | 「包无法自报 ref」「没有任何提示」**是假的**（`uvx` 装出的 dist-info 带 `vcs_info.commit_id` / `requested_revision`；空缓存时 uv 自己会打印构建行） | D3 改写；**新增 §8 Q4** |
| 2 | 「升级路径**永久**死锁 / 再也卸载不掉」**过强**：三条恢复路径实测可用（`git checkout` 回退 / 删 caller 后 `uninit` EXIT=0 / 台账 `sha256: null`） | CD4/R3 措辞降级为「**需一次显式动作**」；Q2 从「有没有出口」变成「选哪条出口」 |
| 3 | 找到**第四条**升级路径：台账该条目 `sha256` 置 `null` + 同步 `gate_ref` ⇒ plain `init` EXIT=0、`uninit` EXIT=0 | §8 Q2 的选项里增列 |
| 4 | 「本 change 内只做 `init --dry-run --policy <seed>` 自证」在 (A) 下**会 EXIT=1**（caller 轴） | D4 的条件写清：自证**仅在 (B)/(B′) 且 caller 轴未变时**成立 |
| 5 | `v1` 落后 **50** 个提交（本稿写 47） | 数字订正 |
| 6 | M6 的同源文档清单漏 `docs/design.md:56,73` | 加进清单 |
| 7 | **Q1 的基石（`job.workflow_*` 语义）运行期未验证** | **已补测**：真 CI 探针（同仓 reusable）证真 ⇒ Q1 定案 **(B′)**（§2 D1） |

## 8. 停轮问题（Open Questions —— 逐条附真实场景的具体例子与推荐）

> ⚠️ 每条都给「参数 / 输入输出 / 前后对比」，便于快速判断。能由代码定案的不在此列。

### 已由代码定案、移出队列

| 问题 | 定案 | 依据 |
|---|---|---|
| `check` 能不能自己打印「我在用哪个 git ref」？ | **不能**（只能靠 CI 日志侧） | `uvx` 现场构建 wheel、`__init__.py:22` 的 `__version__` 恒为 `0.1.0`、与 tag 无关（实测本仓台账里 `witnessloop_version` 也是 `0.1.0`）⇒ D3 如实写明 |
| 要不要动 `v1` tag？ | **不动** | issue #30 的期望；tag 是别人依赖的发布物 |
| 要不要顺手修 #31？ | **不** | 正交（D5） |

### ~~Q1 修法形态~~ —— **已定案（见上表 + §2 D1 的探针原始输出）：取 (B′)**

（原留档说明：`github.workflow_ref` 指 caller、`job.workflow_sha` 才指被复用的 workflow 文件；
运行期已由真 CI 探针证真。）


- **(B)**（**本稿推荐**）：`gate.yml` 把 `witnessloop-ref` 的默认值改成从 `github.workflow_ref` 解析出的 ref。
  - **具体例子**：接入方 A 的 caller 是 `uses: …/gate.yml@v1`（今天就长这样，**没改任何东西**）：
    - 今天：包 = `v1`（= `ae99256`）⇒ 上游 #22/#25/#26/#28/#29 的修复**全部吃不到**；
    - (B) 之后：包 = 同一个 `@v1`（**仍旧**）——但一旦 A 把 caller 改成 `@v2`（**改一处**），包**立刻**跟着变成 `v2` ✓。
  - **具体例子 2（新接入方）**：`init --gate-ref Xingkai98/witnessloop/.github/workflows/gate.yml@v2`
    ⇒ (B) 下包也是 `v2`；(A) 下文件里会同时出现 `@v2` 与 `with: {witnessloop-ref: v2}`。
- **(A)**：`init` 生成的 caller 双写（见 D1）。
  - 代价：既有接入方**不受益**（要重跑 init 且要过一个显式动作）；且在「谁决定包版本」上留了**第二个可写点**
    （人可以只改 `with:` 而不改 `uses:` ⇒ 又回到两处不一致）。
- ⚠️ **运行期未验证（探针未跑成，如实记录）**：C1-a/R1 已从 GitHub `contexts` 文档取到**文档级证据**：
  **`job.workflow_ref` / `job.workflow_sha` / `job.workflow_repository` / `job.workflow_file_path` 才指向
  「被复用的那个 workflow 文件」**（文档原文：「for jobs in a reused workflow it refers to the reusable workflow file」，
  且文档的 reusable-workflow 示例就是用 `job.workflow_repository` + `job.workflow_sha` **检出它自己的源**）；
  `github.workflow_ref` 在该语境下**指 caller**。⇒ 形态上支持 **(B′)**。
  但**运行期未测到**：探针分支 `probe/workflow-ref`（`c7aa037`）曾推上去、副本仓的 caller PR #5 因
  **base 冲突（DIRTY ⇒ 无 merge commit ⇒ 任何 workflow 都不跑）** 而没跑出结果，**探针分支已按纪律删除**。
  ⇒ ⇒ **Q1 仍未定案**：定案需要一次**能跑起来的**真 CI 探针（PR 不 DIRTY + 能跨仓调 reusable workflow）。
- **推荐：(B) 为主 + (A) 兜底**（若实测证伪则整体退 (A)）。

### Q2 既有接入方的**升级动作**怎么写（(A) 下必需；(B) 下也有一个残留）？

- **(a) `init --gate-ref <ref>` 显式给定时「重写 caller **+ 同步台账该条目的 `sha256` 与 `gate_ref`**」**（**本稿推荐**）：
  - ⚠️ **必须同步台账（grill M2，已实测 `/tmp/e1`）**：只重写 caller 会**永久死锁**——
    plain `init` 走「台账漂移」退 1，**`uninit` 也拒删退 1**（接入方再也卸载不掉）。
  - ⚠️ **作用域限定「已接入分支」**（`initcmd.py:205` 之后）：否则会静默覆盖新仓里外来的 caller，
    并推翻 `tests/test_init.py:128-141`。
  - ⚠️ **先例换掉**：`--test-command`（`constants.py:19-27`）**不进台账**，口径与 caller **相反**；
    正确先例是 **`--policy`**（`initcmd.py:344-351`：显式给定时按新内容落地并同步台账）。
  - **具体例子**：接入方 B 今天跑 `witnessloop init --gate-ref …@v2`：今天 ⇒ **冲突退 1**（caller 内容与期望不同）；
    (a) ⇒ 重写 caller、其余文件照旧只增不改（`init --dry-run` 仍可预览）。
- **(b) 新增一个专门开关**（如 `init --upgrade-caller`）：语义更窄，但多一个概念、且与 `--gate-ref` 的意图重叠。
- **(c) 什么都不做**，只写文档让接入方手工改 caller：
  - **代价**：手改的文件下次 `init` 会被判「冲突」（因为台账里记的是旧 hash）⇒ 仍要一个动作。
- **推荐：(a)**。

### Q3 本仓自己的 caller/台账要不要在**同一个 change** 里迁移？

- **(a) 要**（**本稿推荐**）：本 change 落地时一并更新 `.github/workflows/witnessloop.yml` 与台账，
  并在 PR 里跑一次 `init` 自证不冲突 —— 这同时是**升级路径的活样板**。
- **(b) 不要**：本 change 只管工具，自己的仓下个 change 再迁。
  - **代价**：本 change 合并后本仓 plain `init` 会**冲突退 1**（因为生成逻辑变了、盘上文件没变）
    ⇒ 把问题推给下一个人，且与本 change 的 D4 自相矛盾。
- **推荐：(a)**。
