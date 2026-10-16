# gate-ref-pinning — 接入方钉住的 ref 必须同时决定「跑哪个包」

> 本 change 的 capability 增量：把「接入方钉的 ref」当成**单一事实来源**，同时决定
> reusable workflow 文件与 **witnessloop 包**的版本；让「本次实际用的 ref」可见；并给出
> 既有接入方**单一、显式**的升级动作。
> **机制按用户 2026-10-16 的 Q1 裁定定为 (B′)**（`design.md §2 D1` 有跨仓真 CI 探针的原始输出）：
> 包版本的**缺省**取自 **`job.workflow_sha`**（= 被复用的那个 workflow 文件自己的 commit），
> 显式 `with: witnessloop-ref:` 仍可覆盖。

## Requirement: 包版本的缺省 SHALL 取自「被复用的那个 workflow 文件的 commit」

`gate.yml` SHALL 在调用方**未**显式传 `with: witnessloop-ref:` 时，用
**`job.workflow_sha`**（该 reusable workflow 文件自己的 commit）作为 `uvx` 安装的 witnessloop 包版本；
调用方因此 SHALL NOT 需要分别维护两个 ref —— 把 caller 的 `uses:` 指到某个 ref，
包版本就跟着落在**那个 ref 解析出的那份 gate.yml 的 commit** 上。

- 接受判据：解析所依赖的 `job.workflow_repository` SHALL 等于 `constants.REPO_SLUG`
  （`Xingkai98/witnessloop`）——否则退回**兜底 ref**（fail-closed；见下条 Scenario 的定性）。
- `job.workflow_ref` SHALL 只作**兜底**（`job.workflow_sha` 缺失时）：仅接受 `refs/heads/<分支名>`
  与 `refs/tags/<tag名>` 两种形态。
- ⚠️ **能力边界（如实登记、不宣称覆盖）**：`job.*` 在 **GitHub Enterprise Server 上不可用**；
  同 owner 的 **fork** 也能匹配上 `REPO_SLUG` 判据（判据**必要不充分**）。两种情形都落到
  fail-closed 退**本仓当前默认 ref**（`constants.DEFAULT_GATE_REF` 的 ref 部分；今天 = `v1`），
  区别是**日志里有 `::warning::`**（不静默）。见 `design.md §4 R6`。

### Scenario: 改一处、两处跟着变
- **Given** 一个已接入的仓，caller 是 `uses: …/gate.yml@<旧 ref>`
- **When** 把该行改成 `@<新 ref>` 并推一次 PR
- **Then** CI 日志里 SHALL 出现本次实际用的包 ref，且它就是**新 ref 那份 gate.yml 的 commit**
  （`gate / check` 用的是新包）

### Scenario: 显式 `with:` 覆盖仍然有效
- **Given** 一个 caller 写 `uses: …/gate.yml@<ref>` 且同时写 `with: witnessloop-ref: <另一个值>`
- **When** 运行门禁
- **Then** SHALL 用 `<另一个值>` 装包（显式意图优先），且日志 SHALL 说明 ref 来自「调用方显式传入」

### Scenario: 畸形 / 不可接受的输入
- **Given** 满足任一条：`job.workflow_repository` 不等于 `constants.REPO_SLUG`（含**空值**，
  如 GHES）、`job.workflow_sha` 为空且 `job.workflow_ref` 解析不出可安装的 ref。
  具体畸形样本：`owner/repo/x.yml`（缺 `@`）、`owner/repo/x.yml@`（`@` 后为空）、
  `<别的 owner/repo>/x.yml@refs/heads/main`（`owner/repo` ≠ `REPO_SLUG`）、
  `…@refs/pull/30/merge`（PR 合并 ref，**不是稳定的可安装 ref**——⚠️ 只此定性，
  **不**声称它必然安装失败：该 ref 通常能被 git fetch 到，uv 侧行为**未实测**）
- **When** 运行门禁
- **Then** SHALL **fail-closed 到既有默认**（= `constants.DEFAULT_GATE_REF` 的 **ref 部分**；
  今天 = `v1`，随出厂默认一起挪，**不写死某个 tag**）**并打 `::warning::` 说明**，SHALL NOT 静默改变行为

## Requirement: 实际使用的 ref SHALL 在 CI 日志里可见

门禁 SHALL 在运行 `check` **之前**把本次实际使用的 witnessloop ref **打进日志**（`::notice::`），
**对所有 ref 形态成立**（tag / 分支 / **sha**），使接入方不必去 grep `uvx` 的构建输出。
该 step SHALL 是 job 里的**第一个 step**——后续步骤失败时也要能看见它。

### Scenario: 日志里能直接读到 ref
- **Given** 一次 PR 触发的 `gate / check`
- **When** 看该 job 的日志
- **Then** SHALL 有一行明确写出本次使用的 witnessloop ref **及其来源**（显式传入 / `job.workflow_sha` /
  兜底 / fail-closed）

## Requirement: `check` SHALL 自报它实际跑的包 ref（尽力而为）

`check` SHALL 打印**本进程所装的 witnessloop 包**的 VCS 元数据
（PEP 610 `direct_url.json` 的 `vcs_info.requested_revision` 与 `commit_id`），
使「包版本」不止在 CI 日志侧可见，也不止能看见**请求的 ref**、还能看见**解析出的 commit**。

⚠️ **这是尽力而为**：元数据取不到（本地 editable 安装、源码直跑、非 VCS 安装）时
SHALL 打印 `<未知>`，且 SHALL NOT 因此改变退出码。
⚠️ **与 `__version__` 的分工**：`__version__` 恒为 `0.1.0`、**与 tag 无关**
（`src/witnessloop/__init__.py:22`），所以**版本号不能**用来判断跑的是哪版——
本要求走的是 **VCS 元数据**这条链。
（R1 K1 的实测订正：原稿写「包**无法**自报 ref / 构建产物里没有 ref 信息」是**假**的，
`uvx` 装出的 dist-info 确实带 `vcs_info`。）

### Scenario: 能取到元数据
- **Given** `check` 由 `gate.yml` 通过 `uvx --from "git+…"` 安装后运行
- **When** 看它的输出
- **Then** SHALL 有 `requested_revision` 与 `commit_id` 两值

### Scenario: 取不到元数据
- **Given** witnessloop 以 editable / 源码方式运行（没有 `direct_url.json` 的 `vcs_info`）
- **When** 看它的输出
- **Then** SHALL 打印 `<未知>`，且**退出码不变**（不因为报不出 ref 而判红）

## Requirement: 既有接入方 SHALL 有单一、显式的升级动作

对**已接入**的仓，显式给 `init --gate-ref <新 ref>` SHALL **重写 caller + 同步台账**
（`init-manifest.json` 里该条目的 `sha256` **与** `gate_ref`），其余文件照旧**只增不改**；
执行后 plain `init` SHALL 回到幂等、`uninit` SHALL 仍可用（终态是**不动点**）。

- **作用域**：该行为 SHALL 只作用于**已接入**分支（存在 `init-manifest.json` 时）——
  未接入的仓里若已存在内容不同的 caller，仍 SHALL 判冲突并整体不落盘。
- **诚实边界**：不修这条时，接入方并非「没有出口」（三条恢复路径实测可用，见 `design.md §2 D2`），
  而是出口**难用**——本要求交付的是**好用**的那条。
- **代价（SHALL 写进文档）**：本动作会改写 `.witnessloop/init-manifest.json`，而它在**不变集**里
  ⇒ 该 PR 会**多一条**「受保护路径被写入但没有解释事件」的红，接入方 SHALL 在该 PR 里补一条
  `protected_path_write` 事件（写在某个**既有** change 目录的 `workflow-events.jsonl`；
  新建「只有事件文件的目录」会让红从 1 条变 7 条——实跑复现，见 `docs/gate.md §1.2`）。
  文档 SHALL 把这条代价与补救写清，SHALL NOT 只写「重写 caller + 同步台账」就算完。

### Scenario: 显式换 ref 之后仍是干净的不动点
- **Given** 一个已接入的仓（caller 无 `with:`），且它的 **policy 与出厂默认一致**（或本次同时给了 `--policy`）
- **When** 跑 `witnessloop init --gate-ref <新 ref>`
- **Then** SHALL 重写 caller、SHALL 同步台账的 `sha256` 与 `gate_ref`，EXIT=0；
  且随后 plain `init` SHALL 报「幂等，无改动」、`uninit` SHALL 能正常回滚
  ⚠️ **前提不能省（R9 的 W2，实跑证伪过）**：**定制过 policy 的仓不满足这个 Then**——
  `--gate-ref` 会退 1，且随后 plain `init` **不**报「幂等，无改动」（它撞的是**另一条轴**：
  出厂政策 ≠ 磁盘上的定制政策）。此时那句「要更换 policy 请先 `uninit`」**不可照做**——
  `uninit` 会把 `policy.json`、caller **与台账一起删掉**，而定制 seed 按惯例不入库。本仓自己就是这一类（`README` 的「本仓自身接入」）。

### Scenario: 不给 flag 时不动
- **Given** 同一个已接入的仓
- **When** 跑不带 `--gate-ref` 的 plain `init`
- **Then** SHALL 保持「幂等，无改动」（**不**顺手改 caller），与今天一致

### Scenario: `--dry-run` 只预览、且不许谎报幂等
- **Given** 一个已接入的仓 + 显式 `--gate-ref <新 ref>`
- **When** 跑 `init --dry-run --gate-ref <新 ref>`
- **Then** caller 与台账 SHALL **都不落盘**（`git status --porcelain` 逐字不变），
  且输出 SHALL **不**说「幂等，无改动」（它确实会改），SHALL **不**报冲突
  （那条冲突正是这个动作要消掉的）

### Scenario: 台账里没有 caller 条目
- **Given** 已接入的仓，但 `created_files` 里**没有** caller 那一条
- **When** 显式跑 `init --gate-ref <新 ref>`
- **Then** SHALL 同步 `gate_ref` 并**补上**该条目（`sha256` = 新内容），
  条目位置 SHALL 在台账自己的 `self` 条目**之前**；盘上**没有** caller 文件时 SHALL NOT 凭空新建它，
  并且该请求 SHALL **响亮失败**（EXIT≠0 + 一句说明），SHALL NOT 报「幂等，无改动」
  ⚠️ **措辞订正（R9 的 W1）**：此前这里写「交给漂移判定响亮地报」是**错的**——
  漂移判定只遍历台账条目，看不见「无条目 + 无文件」这一态；把它变响亮的是
  `initcmd.caller_retarget_refusal`（R8 的 V1 新增）

### Scenario: 与冲突的 `--policy` 同时给出（组合语义）
- **Given** 一个已接入的仓，同时给 `--gate-ref <新 ref>` 与一份**与已落地不同**的 `--policy`
- **When** 跑 `init`
- **Then** caller 与台账 SHALL **先按显式意图改写且不回滚**，`--policy` 那条轴照旧参与退出码
  （EXIT≠0）；输出 SHALL **点明**「caller 已落盘、不回滚」，SHALL NOT 让用户以为要去删 policy。
  ⚠️ 这是**刻意**与「未接入分支的整体不落盘」不同的一条语义，理由是同款先例
  `--test-command`（`initcmd` 的 Z1/O2 注释）：显式意图优先、写在前、其余判定照旧参与退出码。

## Requirement: caller 文件不受保护这条边界 SHALL 被如实登记

`.github/workflows/witnessloop.yml`（caller）**不在** `protected_paths` / 不变集 / `require_change_for` 里
（实测：`.github/workflows/witnessloop.yml：protected=False invariant=False require_change=False`）——
即一个 PR 可以把 caller 的 `uses:` 改成**别的仓**的 workflow 而 `check` 不报 finding。
本 change SHALL 把这条边界写进 `docs/gate.md §7 能力边界`，SHALL NOT 在本 change 内新增保护面。

### Scenario: 边界可见
- **Given** 读者查 `docs/gate.md` 的能力边界一节
- **When** 读「caller 不受保护」那一条
- **Then** SHALL 能读到：这条边界存在、后果是什么、以及本 change **刻意不修**它的理由
