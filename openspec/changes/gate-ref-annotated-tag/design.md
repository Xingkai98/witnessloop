# Design: gate-ref-annotated-tag（v1 · 待 grill）

> 依据 `proposal.md` 与 issue #42。流程出处 `templates/grill.md` / `templates/review-loop.md`。
> 决策编号 D1..D7；grill / 对抗验证结论在停轮后回写本文件末尾。

## 0. 一句话

**tag 形态取 `job.workflow_ref` 的 `refs/tags/<tag>`（可安装）；分支 / commit 形态保留
`job.workflow_sha`（它给的就是 commit，且是本次实际执行的精确 revision）。**
对 annotated tag，workflow_ref 给的是 tag 名（可安装），而不是 `job.workflow_sha` 的
**tag object sha**（uv **0.13.2 起**拒绝）。混合优先级同时避免分支 pin 的 TOCTOU。

## 1. 证据（本机实测 · 2026-10-20）

uv 0.13.3 装在 `/tmp/uv0133`（`curl -LsSf https://astral.sh/uv/0.13.3/install.sh | env UV_INSTALL_DIR=/tmp/uv0133 sh`），
每次用**独立** `UV_CACHE_DIR` 强制重新解析：

| 输入 ref | uv 0.13.3 | 解析/结果 |
|---|---|---|
| `00192abe45d2d72a4389eccb202faad48c34fa26`（v1.7.0 tag object） | **EXIT=1** | `Exact Git revision … does not match precise commit c9b2811…` |
| `refs/tags/v1.7.0` | EXIT=0 | `Building witnessloop @ …@c9b281167ad20b63e4832ad9ab8510964a2adc60` |
| `v1.7.0` | EXIT=0 | 同上 |
| `refs/heads/main` | EXIT=0 | `Building …@98b97b7046e98508470345ce081f7189c6c4269c` |
| `c9b281167ad20b63e4832ad9ab8510964a2adc60`（commit） | EXIT=0 | 同 commit |

对照（grill 独立复测，四个版本、各自全新 `UV_CACHE_DIR`）：uv **0.12.1 / 0.13.1** 对 tag object
sha EXIT=0；uv **0.13.2 / 0.13.3** EXIT=1（同一错误）。⇒ 版本分界是 **0.13.2**，不是 0.13.3。
GitHub 侧证据（**真 CI 日志**，run `38928669316`，job `gate / check`；grill 直接解压 run 日志复核）：

```
Uses: Xingkai98/witnessloop/.github/workflows/gate.yml@refs/tags/v1.7.0 (00192abe45d2d72a4389eccb202faad48c34fa26)
WL_WORKFLOW_REF: Xingkai98/witnessloop/.github/workflows/gate.yml@refs/tags/v1.7.0
WL_WORKFLOW_SHA: 00192abe45d2d72a4389eccb202faad48c34fa26
```

分支形态同样有真 CI 证据（跨仓探针 run `38853369550` 日志）：
`job.workflow_ref=…/probe-ref.yml@refs/heads/probe/workflow-ref`、`job.workflow_sha=6e2ec4d…`。

⇒ 对 callers 钉 annotated tag 的形态，`job.workflow_ref` 以 `@refs/tags/v1.7.0` 结尾；
`job.workflow_sha` 是 tag object。两者分开用即可：前者可安装、后者不可。
commit pin 的 workflow_ref 真实形状已由 asterwynd 真 CI 证实为 `@<40 位小写 hex>`
（run `39386712284`，gate 绿）。即使形状不符，也会落到 `job.workflow_sha`（同一 commit）
兜底，结果正确、只多一条 warning。

## 2. 决策

### D1 解析优先级：tag 用 workflow_ref，分支 / commit 用 workflow_sha（混合）

**顺序（分支顺序即语义）**：

1. 显式 `with.witnessloop-ref` 非空 ⇒ 用它（不变；显式意图优先）。
2. `job.workflow_repository != REPO_SLUG`（含空值：GHES / 非本仓 reusable）⇒ **直接 fail-closed**
   退 `WL_FALLBACK_REF` + `::warning::`，**不**再试 workflow_ref（不拿别人仓的 ref 去本仓装包）。
3. 解析 `job.workflow_ref` 的 `REF_PART`：**用已知前缀精确剥离**
   `<REPO_SLUG>/.github/workflows/gate.yml@`（这是本文件自己的路径）——
   ref 名或 workflow 路径里含 `@` / `@refs/heads/` / `@refs/tags/` 都不会截错；
   路径对不上（文件被改名等）⇒ `REF_PART=""`（响亮兜底，不静默猜）。
   剥离后只接受：`refs/tags/<非空>` / `refs/heads/<非空>` / 40|64 位小写 hex / 空。
   若 `REF_PART` 以 `refs/tags/` 开头 ⇒ `REF=REF_PART`（完整 namespaced tag ref）——
   **这是修 #42 的唯一分支**。
4. 否则若 `job.workflow_sha` 非空 ⇒ `REF=job.workflow_sha`：
   - `REF_PART` 是 `refs/heads/<非空>` 或 40/64 位小写 hex ⇒ **正常路径**（分支 / commit pin
     的精确 commit），不打 warning；
   - 其他 / 缺失 ⇒ **兜底路径** + `::warning::`（附原始 workflow_ref；这个 sha 对 annotated
     tag 可能是 tag object，uv 会响亮失败，不静默）。
5. 否则（sha 为空）若 `REF_PART` 是 `refs/heads/<非空>` 或 40/64 位小写 hex ⇒
   `REF=REF_PART`（降级路径，来源文案注明 sha 缺失）。
6. 全不行 ⇒ fail-closed 退 `WL_FALLBACK_REF` + `::warning::`（不静默装默认分支）。
7. 最终 `REF` 为空（含空白）⇒ `::error::` + **非零退出**，不写出 `ref=`。

**为什么是混合优先级（grill Q1）**：

- annotated tag 的 `job.workflow_sha` 是 **tag object**（本地无法从 40 位 sha 判断类型，
  见非目标）⇒ 只有 tag 形态必须走 workflow_ref 的 tag 名；uv 0.13.3 实测 tag ref 可安装。
- 分支 / commit pin 的 `job.workflow_sha` 就是 **commit**，且是本次实际执行的精确 revision。
  若改用会移动的 `refs/heads/<branch>`，uv 在安装时重新解析 ⇒ 可能装到比 workflow 文件**晚
  一个/多个 commit** 的包（TOCTOU），削弱「一个 ref 同时决定 workflow 文件与包」的契约。
- 因此：**tag 用 tag ref，其余保留 sha**；两者都优先「可安装且语义精确」的那个。

**为什么 tag 输出完整 namespaced ref（`refs/tags/x`）而不是剥掉前缀**：
- 避免「同名分支 / tag」的歧义；与 GitHub 给的值逐字一致，日志可对照；
- uv 0.13.3 实测可安装（§1）。分支在降级路径里同样保留完整 `refs/heads/x`。

**边界**：只接受**小写** hex 作为 commit sha。大写 40 位（罕见）会走 sha 兜底、结果仍是
同一个 commit，只多一条 warning。commit pin 的真实 workflow_ref 形状已由 asterwynd 的
真 CI 证实为 `@<40 位小写 hex>`（run `39386712284`），D5 用该形态做用例。

### D2 兜底与失败语义：保持「响亮」

- tag 正常路径：`REF=refs/tags/<tag>`，无 warning。
- workflow_ref 形态不可识别但 workflow_sha 可用 ⇒ **兜底 + `::warning::`**（warning 附上
  `WL_WORKFLOW_REF` 原值，便于诊断）。这是异常形态（GitHub 托管 runner 上 workflow_ref
  总是存在且形如 `owner/repo/path@ref`）；兜底值仍可能是 tag object，uv 会响亮失败，
  不会静默跑错版本。
- 两者都不可用 ⇒ 退**兜底 ref**（`WL_FALLBACK_REF`，与 `constants.DEFAULT_GATE_REF` 的
  ref 部分同源；本 change 移到 `v1.7.1`）并打 `::warning::`。**保持既有 fail-closed 语义**。
- **空 ref 守卫（grill Code-Resolved #11 的实测漏洞）**：若最终 `REF` 为空**或纯空白**
  （例如 `WL_FALLBACK_REF` 被误配成空串、或显式输入了一个空格），脚本 SHALL `::error::`
  并**非零退出**——否则会写出 `ref=` / `ref= `，安装步退化成 `git+…@`（静默装默认分支）。
  既有脚本在空串形态下 `EXIT=0`，本 change 顺手补上行为测试。
- `$GITHUB_OUTPUT` 仍**不兜底**：未定义 ⇒ 脚本退非零（响亮），不退化成 `git+…@`（默认分支）。
- `set -eu` 下，**可能缺失**的 job/input 变量一律 `${VAR:-}` 读；两个常量
  （`WL_REPO_SLUG` / `WL_FALLBACK_REF`）由 workflow 的 `env:` 恒定提供，按普通变量读。
  未定义的 job/input env 不导致 `unbound variable`（已有行为测试）。

### D3 `job.workflow_repository` 守卫：语义与优先级不变

守卫仍在「显式输入之后、任何 workflow_ref/sha 之前」。跨仓 / fork / GHES / 空值 ⇒ 直接
fail-closed 到兜底 ref，**不得**拿 workflow_ref（那可能是别人仓的 ref）。既有测试
`test_resolve_fails_closed_on_a_foreign_repository` /
`test_repository_mismatch_does_not_fall_through_to_workflow_ref` 原样保留。

### D4 日志：来源必须可读、且与新优先级一致

`::notice::witnessloop 包 ref = <ref>（来源：<WHY>）` 的 `WHY` 取值：

| 分支 | WHY 必须含 |
|---|---|
| 显式输入 | `显式` |
| tag（workflow_ref） | `job.workflow_ref` 且 `tag` |
| 分支 pin（workflow_sha） | `job.workflow_sha` 且 `分支` |
| commit pin（workflow_sha） | `job.workflow_sha` 且 `commit` |
| workflow_ref 不可识别 ⇒ workflow_sha 兜底 | `job.workflow_sha` 且 `兜底`，warning 附 `WL_WORKFLOW_REF` 原值 |
| sha 缺失 ⇒ workflow_ref 降级 | `job.workflow_ref` 且 `降级` |
| fail-closed | `fail-closed` |

这样接入方在 CI 日志里能直接看出「这次为什么用了 tag 名而不是 sha」。

### D5 回归测试：行为级 + 变异证明

`tests/test_gate_workflow.py` 的 D 组已经是「把 `run:` 原文交真 `sh` 跑」的形态（复用
`_run_resolve`）。本 change 新增/改写：

1. **annotated tag 主用例**（核心回归）：
   ```
   WL_WORKFLOW_REPOSITORY=Xingkai98/witnessloop
   WL_WORKFLOW_SHA=00192abe45d2d72a4389eccb202faad48c34fa26       # tag object
   WL_WORKFLOW_REF=Xingkai98/witnessloop/.github/workflows/gate.yml@refs/tags/v1.7.0
   ```
   ⇒ 断言解析结果 **等于 `refs/tags/v1.7.0`**、**不是**那个 40 位 sha、无 warning。
   旧的「sha 优先」实现返回 tag object sha ⇒ 该断言**必红**（开发期用临时还原的旧脚本
   实跑并记录输出）。
2. **形状守卫**：所有「来自 tag ref」的结果都不得是裸 40/64 位十六进制——即使 workflow_sha
   看起来像 commit，也不会被误当成 tag 的包 ref。
3. 分支 / commit pin：`workflow_sha` 保留精确 commit（分支：sha 值；commit：sha 值），
   并断言**不是** `refs/heads/main`（反面钉子，锁住混合优先级）。
4. workflow_ref 不可识别 + sha 非空 ⇒ sha 兜底 + warning（warning 含原值）；
   sha 空 + workflow_ref 是分支 / commit ⇒ workflow_ref 降级；
   两者都不可用 ⇒ fail-closed 兜底 ref + warning。
5. **边界样本**：`refs/tags/` / `refs/heads/`（斜杠后为空）、分支名含 `@`
   （`refs/heads/feature/a@b`）、ref 名里含 `@refs/heads/` / `@refs/tags/`、tag 名含 `@`、
   64 位 hex、大写 hex（预期落到 sha 兜底 + warning）、**workflow 路径不匹配已知前缀**
   （改名等）⇒ sha 兜底 + warning、commit-pin 的真实形态 `@<40 位小写 hex>`。
6. **空 fallback / 空白输入守卫**：`WL_FALLBACK_REF=''` + 两者都不可用、或
   `WL_INPUT_REF=' '` ⇒ 脚本 SHALL 非零退出，不得写出 `ref=`（旧脚本实测 `EXIT=0` + `ref=`）。
7. 既有语义逐条保留：显式覆盖（含 GHES 下显式值仍生效）、repository 不匹配直接 fail-closed、
   畸形样本（缺 @ / @ 后为空 / `refs/pull/30/merge`）、未定义 env、输出非空、
   常量同源、step 是第一个、安装步吃输出、input 默认空串。
8. **旧测试处置**：
   - `test_resolve_prefers_the_reusable_workflows_own_sha` 的输入是分支 + 非空 sha，
     混合优先级下**仍然返回 sha** ⇒ 保持有效，只更新注释/名字（不要无理由改写）；
   - `test_resolve_falls_back_to_the_ref_part_of_job_workflow_ref` 会红（旧输出剥了前缀）
     ⇒ 按新输出（完整 `refs/tags/x`；分支在 sha 缺失时才是 `refs/heads/x`）改写；
   - `test_caller_ref_matches_this_repo` 的 `v1.7.0` ⇒ `v1.7.1`。
9. **确认旧实现会红**：开发时把 gate.yml 解析脚本临时换回旧优先级，跑新增核心用例，
   记录失败输出到 `tasks.md`；恢复后全绿。这不是「只加注释断言」——断言的是脚本**行为**。

不联网跑 uv：uv 的行为已由 §1 的实测固定；pytest 只断言「解析出的 ref 形态」（tag ref vs
tag object sha），这正是 bug 的根因层。

### D6 本仓 caller 的临时处置与 `v1.7.1` 发版

本仓 caller `.github/workflows/witnessloop.yml` 也钉 `@v1.7.0`。修复 PR 的 `pull_request`
运行会从 PR head 取 **caller**，但 `uses:` 指向的 **reusable workflow 仍是 v1.7.0 的旧文件**
⇒ 会撞同一个 bug（uv 0.13.3 下必红）。处置（与 issue #42 里 asterwynd 的临时办法同类）：

1. 在本 PR 内把 caller 临时钉到 **commit `98b97b7046e98508470345ce081f7189c6c4269c`**
   （= `origin/main`，commit pin 下旧 `gate.yml` 的 `job.workflow_sha` 是 commit，可安装）。
   用工具自己的迁移动作（grill 实测：本仓定制 policy 下必须带 `--policy`，否则 exit 1）：
   ```
   witnessloop init --dry-run \
     --gate-ref Xingkai98/witnessloop/.github/workflows/gate.yml@98b97b7046e98508470345ce081f7189c6c4269c \
     --policy .witnessloop/policy.json
   witnessloop init \
     --gate-ref Xingkai98/witnessloop/.github/workflows/gate.yml@98b97b7046e98508470345ce081f7189c6c4269c \
     --policy .witnessloop/policy.json
   ```
   ⚠️ **必须用 40 位全 sha**：GitHub Actions 拒绝 `uses:` 里的短 sha（对抗轮 R1-1；
   `init` 会逐字写进 caller）。验收：`grep 'uses:' .github/workflows/witnessloop.yml`
   必须是 `@98b97b7046e98508470345ce081f7189c6c4269c`（40 位小写 hex）。
   ⇒ 同步 `.witnessloop/init-manifest.json` 的 `gate_ref` 与 caller 条目的 `sha256`，
   并按不变集规则补一条 `protected_path_write` 解释事件（events 文件本 PR 新建 = `A`，
   自身不需要事件）。
2. 合入 → 在合并提交上打 **annotated `v1.7.1`**（tag message 写明修复 issue #42）→
   **不动** `v1` / `v1.7.0`。
3. 另起一个 PR 把 caller 回钉 `@v1.7.1`（同样用 `init --gate-ref …@v1.7.1 --policy …`）。
   这个 PR 跑的是 **v1.7.1 的新 `gate.yml`**，`job.workflow_ref` 以
   `@refs/tags/v1.7.1` 结尾 ⇒ 它的 `gate / check` 绿就是「annotated tag 形态被真实 CI
   验证」的端到端证据。
   ⚠️ **G2 需要重建三份 manifest**：该 PR 改了 caller（非证据路径），而 active change
   因 events 文件被改而成为 target ⇒ 旧 manifest 的 `head_sha` 到新 head 之间出现
   非证据改动 = stale。顺序：内容提交（caller + 台账）→ 在当前 HEAD 重建三份 manifest
   → 证据提交（manifest + events）。G2 的 events 需要**五条**：`init-manifest.json`、
   三份 manifest、以及 events 文件自己（它们都在不变集里，`M` 需解释）。

顺序固定：**先改 `constants.DEFAULT_GATE_REF` / `WL_FALLBACK_REF` 到 v1.7.1，再打 tag**
（反过来 tag 里的常量仍是旧值，收益落空——change `gate-ref-pins-package` 的同款教训）。
合并与打 tag 之间有一个窗口：main 上的 `init` 会写出指向尚不存在 tag 的 caller；合入后
**立即**打 tag，并在发布说明里写明窗口。

### D7 文档与规格同步

- `gate.yml` 头部注释：规则顺序改为 ①显式 → ②repository 守卫 → ③tag 用 workflow_ref →
  ④分支/commit 用 workflow_sha → ⑤降级 / fail-closed；删掉「sha 优先」的旧叙述；
  写明 annotated tag 的 tag object 事实与空 ref 守卫。
- `docs/gate.md §1.2`：把「uv 能把 tag object sha 解析成 commit」的旧结论改成「**uv 0.13.2
  起**拒绝（0.13.1 及更早接受）」，写新解析规则、实测证据与「钉 annotated tag 是受支持形态」；
  说明 `check` 自报的 `requested_revision` 会显示 `refs/tags/v1.7.1`（预期形态）。
- `docs/gate.md §7.1`：兜底 ref 今天 = `v1.7.1`；GHES 边界不变。
- `docs/design.md:57`：包 ref 的推导句改为「tag 用 workflow_ref、其余用 workflow_sha 兜底」。
- `README.md`：安装/升级命令与「怎么钉版本」改为 v1.7.1；写明 annotated tag 受支持；
  旧 caller 的升级路径不变（`init --gate-ref …@v1.7.1`）；保留 `job.workflow_sha` 字样
  （`tests/test_docs.py` 钉住）。
- `constants.py` 的 `DEFAULT_GATE_REF` 与注释：v1.7.1；注释改为混合优先级 + issue #42。
- `tests/test_gate_workflow.py` 的 D 组注释（仍写着「sha 优先」）一并更新。
- spec delta：`specs/gate-ref-pinning/spec.md` 覆盖旧 Requirement 的冲突段落（本 change 的
  能力增量优先）。

## 3. 边界与风险

| 风险 | 处置 |
|---|---|
| 分支 pin 的 TOCTOU（包比 workflow 文件晚一个 commit） | **已消除**：分支 / commit 保留 `job.workflow_sha`（精确 commit），只有 tag 走 workflow_ref |
| tag 在「workflow 文件解析」与「uv clone」之间被移动 ⇒ 包与文件短暂不一致 | 接受：tag 本应不可变；比 tag object sha 不可安装要好。日志有 ref 可回溯 |
| caller 直接钉 **tag object sha**（而非 tag 名）⇒ workflow_ref 也可能是那个 sha，无网络无法分辨 | 不支持也不承诺（属畸形钉法）；兜底/安装会响亮失败，不会静默跑错版本 |
| workflow_ref 缺失或畸形（非 GitHub 托管 / 自建 runner 变体） | 退 workflow_sha 兜底 + warning（附原值）；再不行 fail-closed 兜底 ref + warning |
| 空 `WL_FALLBACK_REF` 导致 `ref=`（静默装默认分支） | 新增非空守卫：`::error::` + 非零退出，并补行为测试 |
| 兜底 ref `v1.7.1` 在 tag 发布前不可安装 | 顺序保证：先合入、立即打 tag；发布前没有 caller 会走新 gate.yml 的兜底路径（本仓 PR 临时钉 commit） |
| 老接入方（钉 `@v1.7.0`）不会自动吃到修复 | 架构决定：`uses:` 钉住的 reusable workflow 不会自己更新。issue #42 的接入方升级到 `@v1.7.1` 即可（文档写明）；本次不移动 `v1.7.0` |
| 自测门槛：修复 PR 的 `gate / check` 跑的是**旧** gate.yml | PR 内临时钉 commit 让它可绿；新 gate.yml 的真实 CI 验证放到回钉 `@v1.7.1` 的后续 PR（D6），并记录 `::notice::` 的 tag 来源行 |
| 浮动 `setup-uv` 是未声明的依赖（grill Q2） | 本 change 不 pin（见 proposal 非目标），登记为后续 change；回归测试只锁 ref 形态，不锁 uv 行为 |
| commit pin 的 workflow_ref 真实形状 | 已验证：asterwynd run `39386712284` 给出 `@<40 位小写 hex>`，gate 绿；D5 用该形态做用例 |
| G2 改了 caller（非证据）会让 active change 的旧 manifest 变 stale | G2 在最后一个内容 commit 上重建三份 manifest；events 五条（台账 + 3 manifest + events 自身） |

## 4. Pre-Implementation Review

### Grill（独立零记忆，2026-10-20）

- 报告：`reviews/grill-design.md`（7 条 Confirmed Decisions、23 条 Code-Resolved）。
- **已整合的必须修改**：
  1. **版本分界**：uv **0.13.2** 起拒绝（0.13.1 及更早接受）——本文件 / proposal / spec /
     报告统一改写（原先写的 0.13.3 不准确）。
  2. **D1 改为混合优先级**（grill Q1）：tag 用 workflow_ref 的 tag ref；分支 / commit 保留
     workflow_sha 的精确 commit，避免分支 pin 的 TOCTOU。已补反面测试要求。
  3. **空 `WL_FALLBACK_REF` 守卫**：旧脚本实测 `ref=` + EXIT=0 ⇒ 新增 `::error::` + 非零退出
     与行为测试。
  4. **G2 事件计数**：追加 events 文件自身是 `M`，且 caller 变更会让旧 manifest stale ⇒
     G2 重建三份 manifest + 五条事件（已写入 D6 / tasks G2）。
  5. **迁移命令带 `--policy`**：本仓定制 policy 下 `init --gate-ref` 不带 `--policy` 会 exit 1
     （grill 实测）。
  6. **旧测试处置（终稿）**：`test_resolve_prefers_the_reusable_workflows_own_sha`
     （分支 + 非空 sha）在混合优先级下仍成立，**保持**；`test_resolve_falls_back_to_the_ref_part_of_job_workflow_ref`
     改写为完整 namespaced ref（实现里改名为 `..._to_the_full_ref_when_sha_is_missing`）；
     `test_caller_ref_matches_this_repo` 的 v1.7.0 → v1.7.1。
- **Code-Resolved 关键结论**：真 CI 日志直接证明 annotated tag 下
  `job.workflow_ref=…@refs/tags/v1.7.0`、`job.workflow_sha=<tag object>`；分支形态由跨仓
  探针日志证明为 `…@refs/heads/<branch>`；旧解析脚本在 annotated tag 输入下输出 tag object sha
  ⇒ 新增核心用例在旧实现上必红。commit pin 的 workflow_ref 形状已由 asterwynd 真 CI 证实
  （run `39386712284`）。
- **停轮门**：无用户待拍板项。Q1（混合优先级）/ Q2（是否 pin uv）已按任务授权由作者按既有
  语义定案；Q2 登记为后续 change（本 change 非目标）。

### 设计阶段对抗验证（独立零记忆，2026-10-20）

- 报告：`reviews/grill-adversarial.md`。
- **第 1 轮批次（已验证通过）**：
  - **R1-1（high）短 sha**：`init --gate-ref` 示例写成 `@98b97b7`，GitHub `uses:` 拒绝短 sha
    ⇒ F1 的 required check 永远不绿。已全部改成 40 位全 sha
    `98b97b7046e98508470345ce081f7189c6c4269c`，并加 F1 验收（caller 的 `uses:` 必须是 40 位 hex）。
  - **R1-2（medium）grill 报告机械红**：`## Open Questions` 正文里的 `Q1/Q2` 字样仍会被
    `evidence.py` 抽出，而 `## User Confirmation` 没有对应确认 ⇒ `check` 红。已把该小节改成
    逐字「（无）」；Q1/Q2 的定案保留在 Code-Resolved。
- **第 2 轮批次（已修，已验证）**：
  - **R2-1（medium）ref 名含另一命名空间被截错**：`@refs/tags|heads/` 锚定仍会被合法 ref 名
    （如 `refs/heads/feature/a@refs/tags/b`）骗过。最终修法：**用已知前缀**
    `<REPO_SLUG>/.github/workflows/gate.yml@` **精确剥离** `job.workflow_ref`，再做形态分类；
    路径不匹配（文件改名等）⇒ `REF_PART` 空（sha 兜底 + warning / fail-closed）。
    新增三例 + tag 名 `@` + 路径不匹配测试。
- **第 3 轮：0 条 medium+ ⇒ PASS**（`reviews/grill-adversarial.md` 的 `## 闭环出口`）。
- **low/nit 已处置**：commit-pin 形状改为「已验证」（asterwynd run `39386712284`）；proposal
  的「所有 tag」收窄为「所有发布 tag」；D4 的「降级」措辞；D5 不再要求改写仍然正确的
  `test_resolve_prefers_the_reusable_workflows_own_sha`；F4 写明 `--merge` 授权来源；
  Release 正文写明 v1.7.1 发布窗口；安装步注释同步。R2-L6（实现在设计 PASS 前已修改）
  在 `tasks.md §流程偏差` 如实登记，不伪造授权。
