# building-review — gate-ref-pins-package

## Reviewer

- **角色**：独立、零记忆的**实现后**审阅（building / B1 轮）。本对话**不携带**该 change 的任何实现历史；
  `design.md` / `tasks.md` / `specs/` 里的「已落库」「实测」「已收敛」一律当**待验证断言**处理。
  我不是作者，**未改写任何实现**，只产出本报告。
- **审阅对象（revision 绑定）**：worktree `/home/happy/wl-wt/archive-arrival-recognition`，
  分支 `gate-ref-pins-package/2026-10-16`，HEAD = `5bb7765`
  （`git rev-parse --abbrev-ref HEAD` / `git log --oneline -1` 原始输出）。
  变更面按 `git diff eaca568..5bb7765` 界定（`eaca568` = 本分支并入的上一个 PR #29 的合并点；
  分支上还叠着 `main` 之外的若干已合并 PR，故**不**以 `main` 为基线）。
- **验收标准**：`openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md`
  （5 条 Requirement / 10 个 Scenario）。规格是唯一判据，`design.md` / `tasks.md` 只作线索。
- **基线**：`PYTHONPATH=src python3 -m pytest -q` ⇒ **691 passed**（在 HEAD `5bb7765` 上复算，
  与 tasks.md 4.1 的「全绿」一致）。
- **方法**：
  1. 只读审阅 + 与仓内既有实现/文档对照；
  2. **动手变异**：`git archive HEAD | tar -x -C /tmp/br1`（**不碰** worktree 的 `.git` 指针；
     真实仓内未做任何 commit / reset / tag / push），在副本上做 25 组实现侧变异，每组跑**全量** suite；
  3. 行覆盖：pip 被 PEP 668 拦住，改用 stdlib `python3 -m trace --count --missing`；
  4. 文档承诺实跑复现（§1.2 的两条主张、§8 的「只有 check 打」、README 的版本叙述）；
  5. 边界态探测（`--gate-ref` 等于台账现值时的缺条目 / 缺文件两态）。
- **证据约定**：每条结论带 `文件:行号` 或「命令 + 原始输出」。**没复算的一律标「未验证」**。

## 审阅结论

实现**确实交付了 spec 的 5 条 Requirement**，机制正确、与仓内风格一致，未发现会破坏
`init` 既有契约（幂等 / 只增不改）的行为缺陷：25 组变异里 21 组把 suite 打红（钉子密度高），
4 组为绿（对应下文 B1-1…B1-4 的覆盖缺口，其中 2 组已证明是**行为等价/被遮蔽**、不是漏判）。
文档承诺侧：§1.2 的两条主张、§8 的「只有 `check` 打」、README 的版本叙述**均实跑复现**，
未发现「文档承诺 ≥ 实现」的实质漂移，仅发现一处**未加限定的标题句**（B1-6）与一处
**自我加码但没钉子**的措辞（B1-7）。

问题集中在**覆盖缺口**（尤其 B1-1：本 change 新增的「`check` 自报包 ref」这条链的**最后一环**零覆盖，
即整条 Requirement 静默死掉时 691 条全绿）与**低危风格/文档项**。据此判 **有条件通过**：
条件是把 B1-1、B1-2 两条钉子补上（代价极低，各一条用例），并订正 B1-3 的注释措辞。
其余 7 条不阻塞。

## 逐维度结论

### 维度一：spec Requirement 逐条落地（验收标准）

| # | Requirement | 实现落点 | 有无自动化钉子 | 结论 |
|---|---|---|---|---|
| R1 | 包版本缺省取自被复用 workflow 文件的 commit | `.github/workflows/gate.yml:58-109`（`id: wl-ref` 第一个 step）；`constants.py:12,22` 提供 `REPO_SLUG` / `DEFAULT_GATE_REF` | 有（`tests/test_gate_workflow.py:254-594`，D 组用真 `sh` 跑 `run:` + `GITHUB_OUTPUT` 捕获） | 机制落地 ✓；端到端 Then 只能靠真 CI（见「未验证」） |
| R2 | 实际使用的 ref 在 CI 日志可见、step 是第一个 | `gate.yml:108-109`（`::notice::`）、`gate.yml:58`（位置） | 有（`test_gate_workflow.py` 断言输出行 + first-step 位置 + `::warning::`） | ✓ |
| R3 | `check` 自报本包 ref（尽力而为，不改进出码） | `checkcmd.py:55-76`（`installed_vcs_ref`）、`79-91`（`_report_package_source`）、`run()` 首句调用 | **半边有**：「取不到」有钉子；「**取到**」这条主路径零覆盖 ⇒ **B1-1** | 实现 ✓ / 钉子不完整 |
| R4 | 既有接入方单一、显式升级动作 | `initcmd.py:193-247`（`caller_retarget_refusal`）、`250-272`（`_set_ledger_gate_ref`）、`149-190`（`sync_caller_gate_ref`）、`363-387`（`run()` 接线） | 有（`tests/test_init_gate_ref.py` 509 行：主路径/作用域/dry-run/缺条目修复/畸形台账/拒绝面/self 标记） | ✓ |
| R5 | caller 不受保护这条边界如实登记进 `docs/gate.md §7` | `docs/gate.md:535-567`（`§7.1`） | 有（`tests/test_docs.py:268`） | ✓ |

**逐 Scenario 的核对**（10 条）：

1. **R1-S1「改一处、两处跟着变」**：解析机制有钉子（`test_gate_workflow.py` 断言
   `job.workflow_sha` 主路径产出 `ref=<sha>`）。**但 Then 的「CI 日志里的 ref 就是新 ref 那份
   gate.yml 的 commit」在本工作区不可复算**（无 GitHub Actions）——tasks 3.0 记为跨仓探针实证，
   design §2 D1 自认是「单一来源、不可复现的二手文本」。→ **未验证**（见下）。
2. **R1-S2「显式 `with:` 覆盖仍有效」**：`gate.yml:78-80` 分支 1，钉子齐全 ✓。
3. **R1-S3「畸形/不可接受输入 ⇒ fail-closed + warning」**：`gate.yml:99-103`；四个畸形样本
   （缺 `@` / `@` 后空 / foreign repo / `refs/pull/30/merge`）都有用例 ✓。且 `test_gate_workflow.py`
   的 `_fallback_ref()` 从 gate.yml **读出**字面量而非硬编，兜底落点与 `DEFAULT_GATE_REF` 同源 ✓。
4. **R2-S1「日志里能直接读到 ref（含来源）」**：`::notice::` 输出 `ref=… （来源：…）`，钉子断言
   「调用方显式传入」等来源串 ✓。
5. **R3-S1「能取到元数据 ⇒ 有 requested_revision 与 commit_id」**：`vcs_info_from_direct_url`
   的纯函数用例覆盖了真实载荷（`tests/test_check_package_ref.py` 的 `REAL_DIRECT_URL`，
   `requested_revision "v1"` / `commit_id "ae9925…"`）——**但这是对纯函数喂**载荷**，
   不是对 `installed_vcs_ref()` 真去读 dist-info 的验证** ⇒ **B1-1**。
6. **R3-S2「取不到 ⇒ `<未知>` 且退出码不变」**：`test_wired_repo_check_line_survives_a_green_run`
   断言绿跑下仍打印该行且 `EXIT_PASS` ✓（另有 `except Exception` 的宽捕获，见维度二）。
7. **R4-S1「显式换 ref 后是干净不动点」**：主路径用例 ✓；`--gate-ref` 在**定制 policy 的仓**上撞
   另一条冲突轴这一**前提**也已在 `docs/gate.md §1.2:113` 与 spec 正文写明 ✓（我实跑复现，见维度四）。
8. **R4-S2「不给 flag 时不动」**：`test_init_gate_ref.py` 有 plain-init 幂等回归 ✓。
9. **R4-S3「`--dry-run` 只预览、不谎报幂等」**：dry-run 用例断言 `git status --porcelain` 不变 +
   输出不含「幂等，无改动」 ✓。
10. **R4-S4「台账没有 caller 条目」**：`_set_ledger_gate_ref` 在 `self` 条目**之前**插入 + 不凭空建文件 +
    响亮失败，`test_init_gate_ref.py:463-480` 两侧都钉 ✓。
11. **R4-S5「与冲突 `--policy` 同时给出（组合语义）」**：调用方与台账先落盘不回滚、输出点明，
    钉子在场（变异 M23 打红）✓。
12. **R5-S1「边界可见」**：`test_docs.py:268` ✓。

**判定**：R1/R2/R4/R5 的实现与钉子完整；**R3 只有后半（`<未知>`）有钉子，前半（真的取到元数据）
零覆盖** ⇒ 这是判据②的唯一实质缺口。

### 维度二：实现质量与仓内既有风格

- **职责划分清晰、与既有风格一致**。`checkcmd` 沿用本仓「纯函数 + IO 包装 + 打印」的三段式
  （`vcs_info_from_direct_url` 纯、`installed_vcs_ref` 只做 IO、`_report_package_source` 只做输出），
  与既有 `_tests_execution_point` 一路同形 ✓。`initcmd` 的新函数沿用本仓重 docstring + 轮次标注
  （R5/R8/R9/R11/R12）的习惯 ✓。
- **`gate.yml` 的解析 step**：注释块偏长但与文件既有的重注释风格一致；「常量必须与
  `constants.py` 同源」的提醒 + 3 条钉子与既有 `ADOPTER_TESTS_*` 的处理方式同构 ⇒ 不算过度设计 ✓。
  分支顺序（显式 `with:` → repository 判据 → sha → ref 兜底 → fail-closed）与 spec R1 的措辞**逐条对齐** ✓。
- **宽 `except`（`checkcmd.py:65-75`）**：`except Exception` 包住
  `distribution(...).read_text("direct_url.json")`，注释显式说明「按 spec（Q4）刻意宽、非 `BaseException`」。
  这是**合理的**：该行的语义是「尽力而为的信息行，绝不因此判红」，spec R3-S2 明确要求退出码不变；
  宽捕获正是达成「绝不判红」的手段。不构成缺陷 ✓。
- **重复实现（同族但更重的版本）**：`caller_retarget_refusal`（`initcmd.py:193-247`）与
  `sync_caller_gate_ref`（`initcmd.py:149-190`）各自重复了「读台账 → 比对 `gate_ref` →
  判 `created_files` 是数组」这段前言，
  同一次 `init --gate-ref` 调用里对同一个 manifest 文件最多读 4 次 ⇒ **B1-8**。
- **注释与实现不符 1 处**：`initcmd.py:230-241` 的最终拒绝里 `not entry.get("self")` 被上一分支
  遮蔽（`entry.get("self")` 为真时 `:216-227` 已提前 return），而注释写着它「不能省」 ⇒ **B1-3**。
- **分支无覆盖 2 处**：`initcmd.py:516`（漂移分支里的「已落盘、不回滚」打印）与
  `checkcmd.py:76`（`installed_vcs_ref` 的最后一环）⇒ **B1-2 / B1-1**。
- **可疑但无害 1 处**：`caller_retarget_refusal` 里「`created_files` 非数组 ⇒ `return None`」
  这一分支的行为与「落空」等价（后续 `sync_caller_gate_ref` 也会 `return None`）⇒ **B1-4**。

### 维度三：测试质量（动手变异）

在 `/tmp/br1` 副本上做 **25 组实现侧变异**，每组跑**全量** suite（基线 691 passed）：

- **21 组打红**（M1, M3, M5–M21, M23, M24）：包括 `caller_retarget_refusal` 的**每一条**
  `return <str>` / `return None` 分支、`_already_initialized` 的 `ignore` 参数、`check` 自报行、
  `gate.yml` 解析 step 的各个分支与顺序、`_set_ledger_gate_ref` 的插入位置。
- **4 组为绿**：
  - **M25 ← `checkcmd.py:76`**（`installed_vcs_ref` 的 `return vcs_info_from_direct_url(raw)`）⇒ **B1-1**；
  - **M22 ← `initcmd.py:516`**（漂移分支的 `handled` 打印）⇒ **B1-2**；
    （两者与 `trace --missing` 的未覆盖行**互相印证**：本 change 新增的未覆盖行恰好只有这两处。）
  - **M2**（去掉 `caller_retarget_refusal` 最终判定里的 `not entry.get("self")`）⇒ 绿，
    因为该守卫不可达（见 B1-3）；
  - **M4**（把「`created_files` 非数组」从 `return None` 改成落空路径）⇒ 绿，因为**两条路径的
    可观测行为相同**（我做了**返回到字节相同**的诊断串对比证明是行为等价，非漏判）⇒ B1-4。
- **任务 §6.1 的「字面量族」断言独立复算**：把 4 处一起改成 `@v1.7.0` ⇒ **691 passed**（全绿）；
  只改 `constants.py` 一处 ⇒ **3 failed**（红）⇒ tasks 6.1「只改一处就会红」成立 ✓。

**判定**：钉子密度整体高，唯二实质缺口是 B1-1（中）与 B1-2（中）。

### 维度四：文档 vs 实现漂移（`docs/gate.md` / `README.md` / `docs/design.md`）

**§1.2 的两条主张我实跑验了，都成立**：

- **A「升级动作会被自己的门禁拦一次」**：在 scratch 接入仓上跑 `init --gate-ref <新 ref>` 后
  `check` 恰好报 **1 条** finding，落点是 `.witnessloop/init-manifest.json` ✓；
  变体（新建「只有事件文件的目录」）⇒ 从 1 条红变**恰好 7 条**红 ✓（与 `§1.2:143` 的「1 条红会变成 7 条红」一致）。
- **B「定制 policy 的仓不撞幂等」**：定制 policy 的仓上 `--gate-ref` 退 **EXIT 1**，
  其后 plain `init` **不**报「幂等，无改动」（撞的是出厂政策 ≠ 磁盘政策那条轴）✓
  ⇒ `§1.2:113` 的措辞成立。
- **C「`--gate-ref` 与冲突的 `--policy` 同时给出」**：退 **EXIT 0**、caller 与台账**已落盘不回滚** ✓。
- **§8 的「只有 `check` 打」**、**README 的「`@v1` 停在 v1.6.0 (ae99256)」**、
  **「旧的 `@v1` 包没有这一行」**：均实跑/查证复现 ✓；`v1` 那份 gate.yml 确实没有 `wl-ref` step ✓。
- **R5 的「实测」数字**：`.github/workflows/witnessloop.yml：protected=False invariant=False
  require_change=False` 复现 ✓；且一个把 caller 的 `uses:` 指向**别的仓**的 PR 跑 `check` **退 0（通过）** ✓
  ——即边界描述**属实、不夸大**。

**发现 2 处措辞层面的漂移/自我加码**：
- **B1-6**：`README.md:185` 的标题句「改一处、两处跟着走」**未加限定**，而在「`@v1` 这份旧
  gate.yml」窗口内不成立（旧 gate.yml 里没有本 change 的解析 step）。同节 20 行之后确实提了
  「含新 gate.yml 的 ref」，`README.md` 也明说「v1.7.0 发布之前请仍然钉 `@v1`」，
  故**不算实质超卖**，但标题句值得补一个限定语。
- **B1-7**：spec「组合语义」Scenario 要求「SHALL NOT 让用户以为要去删 policy」，**无钉子**；
  且该路径的输出仍带「要更换 policy 请先 `uninit`」，而本 change 的 `§1.2:113-118` 在
  定制 policy 的仓上把**同一句**判为「不可照做」（`uninit` 会把 `policy.json` + caller + 台账一起删）。
  不是规格违反（该 Scenario 的 Given 是「与已落地**不同**的 `--policy`」，即**本次已给 policy**），
  但属于**自我加码未兑现**。

### 维度五：收益是否被吹过头（GHES / fork / `v1.7.0` 未发布态）

- spec R1 的能力边界段（`:21-24`）**如实登记**了 `job.*` 在 **GHES 上不可用**、**同 owner 的 fork
  也能匹配**（判据必要不充分），并说明两者都 fail-closed 退当前默认 ref 且有 `::warning::` ✓。
- `DEFAULT_GATE_REF` 现仍为 `@v1`，`constants.py:22` 的注释与 tasks §6 都把它标为 `(post-merge)`
  （Q3 裁定：本 PR **不**做）✓ ——即本 PR **没有**声称 `@v1.7.0` 已经可用；
  README 的 recipe 明确写了「v1.7.0 发布之前，请仍然钉 `@v1`」✓。**未见过度宣称**。
- 唯一相关的可追溯性问题见 **B1-10**（tasks 3.0 说本地保留的 `probe/workflow-ref`/`c7aa037`
  是「Q1 唯一可追溯的本地物证」，但 design 里记的两个 sha 在本 worktree 对象库里都**不存在**）。

### 未验证（明确登记，不计入问题清单）

1. **R1-S1 的端到端 Then**：`job.workflow_sha == 被复用 workflow 文件的 commit` 是 GitHub Actions
   语义，本工作区**无 Actions**，无法复算；design §2 D1 自认探针输出为「单一来源、不可复现的二手文本」。
2. **`uvx` / `uv tool install` 在真 CI 上落 `direct_url.json` 的 `vcs_info`**：只验了测试里抄录的
   真实载荷（`REAL_DIRECT_URL`）与纯函数解析，未在真 uv 安装上端到端验证。
3. **README ①′ 的 self-proof recipe**（`check | head -1` 打出 `requested_revision=<新 ref>`）：
   需要真 uv 安装 + 已发布的 `v1.7.0`，本 PR 时序上不可能验证。
4. **GHES 上 `job.*` 不可用**：依据 GitHub 文档与 spec/design 的登记，未实测。

## 问题清单

> 排序：行为缺陷 / 覆盖缺口在前，文档漂移次之，风格殿后。每条带类别 + 严重度 + 证据。

### B1-1 · 覆盖缺口 · 中 —— `check` 自报包 ref 这条链的**最后一环**零覆盖

- **位置**：`src/witnessloop/checkcmd.py:76`（`return vcs_info_from_direct_url(raw)`，
  即 `installed_vcs_ref()` 里「真去读 dist-info」这一步）。
- **证据**：变异 M25（把该行改成直接 `return None, None`）跑**全量** suite ⇒ **691 passed，全绿**
  （`/tmp/br1/lab/M25/M25.txt`）。行覆盖 `python3 -m trace --count --missing` 同样标记该行为未执行。
- **为什么是问题**：spec R3 的**主干**就是「能取到元数据 ⇒ 打出 requested_revision 与 commit_id」，
  而现有两条 `check` 自报用例分别走的是「monkeypatch 注入」与「源码直跑 ⇒ `<未知>`」，
  `installed_vcs_ref()` **真读 dist-info** 的这条路（也正是 CI 里真实发生的那条）没有任何用例经过。
  ⇒ 该环静默坏掉时 691 条全绿，**整条 Requirement 无声死亡**。
  这与本 change 自己 R6/T1 立的标准（「最后一环必须有钉子」）不一致。
- **建议**：一条用例即可——注入一个假的 `importlib.metadata.distribution`（或 monkeypatch
  `installed_vcs_ref` 内部读取），返回真实载荷，断言 `installed_vcs_ref() == ("v1", "ae9925…")`。

### B1-2 · 覆盖缺口 · 中 —— `_already_initialized` 漂移分支的 `handled` 打印零覆盖

- **位置**：`src/witnessloop/initcmd.py:516`（漂移判定分支里打印「caller 已落盘、不回滚」那句）。
- **证据**：变异 M22（删掉该打印）⇒ **691 passed，全绿**；`trace --missing` 亦标为未执行。
  （本 change 在 `5bb7765` 的提交说明里明确写了这一句是 R12 的 P-2 订正项，属**有意的行为**。）
- **为什么是问题**：这是**新增**的一个用户可见输出分支，且承载 R12 P-2 的语义（漂移分支也须
  点明已落盘、不回滚），却没有任何用例走到 ⇒ 回归不会被发现。
- **建议**：复用现有 `_already_initialized` 的 handle-both-sides 用例形态，造出「台账在、盘上文件被
  手改（漂移）+ `--gate-ref`」这一态，断言输出含该句。

### B1-3 · 风格 / 注释与实现不符 · 低 —— 不可达守卫 + 过度声明其必要性

- **位置**：`src/witnessloop/initcmd.py:230-241`（最终 `any(... not entry.get("self"))` 里的
  `not entry.get("self")`）。
- **证据**：变异 M2（删除 `not entry.get("self")`）⇒ **全绿**。原因：`entry.get("self")` 为真时，
  上方 `:216-227` 已提前 return，该子条件**不可达**。我做了两条路径的**诊断串字节对比**，
  输出完全相同 ⇒ 属遮蔽/等价，**不是**漏判。
- **为什么是问题**：注释宣称该守卫「不能省」——与实现不符（可省）；未来若有人重排分支顺序，
  该守卫会**悄悄**变成承重件而无人知道。属注释撒谎类的低危项。
- **建议**：二选一——删掉不可达子条件并改注释；或保留但在注释里写明它现在是**防御未来重排**的
  冗余（并加一条注释指向 `:216-227` 的提前 return）。

### B1-4 · 覆盖缺口 · 低 —— 「`created_files` 非数组 ⇒ `return None`」行为等价于落空

- **位置**：`src/witnessloop/initcmd.py:193-247`（`caller_retarget_refusal` 的该 `return None`）。
- **证据**：变异 M4（把该分支改为走落空路径）⇒ **全绿**；两条路径的**下游**可观测行为相同
  （后续 `sync_caller_gate_ref` 同样 `return None`）⇒ 行为等价，非漏判。
- **为什么是问题**：该分支是本 change 新增的显式返回，读代码的人会以为它区分了两种台账形态，
  实际不区分 ⇒ 语义含糊。低危。
- **建议**：要么删掉该分支交由下游统一处理，要么在注释里写明「与落空同义，仅为早退」。

### B1-5 · 边界行为 · 低 —— `--gate-ref` 等于台账现值且台账缺 caller 条目时静默 no-op

- **位置**：`src/witnessloop/initcmd.py` 的 `sync_caller_gate_ref`（`gate_ref` 已在台账 ⇒ `return None`）
  与 `caller_retarget_refusal` 的交互。
- **证据**：我做的边界态探测——已接入仓、台账**缺** caller 条目、`--gate-ref` 恰好等于台账里已记的
  ref ⇒ `init` 退 **EXIT 0** 且报「幂等，无改动」，条目**不补**；随后 `uninit` 退 0 但
  **caller 文件留在盘上**（policy/台账已删）⇒ 半回滚态。
- **为什么不算规格违反**：spec 该 Scenario 的 Given 是 `--gate-ref <**新** ref>`，此处输入的并非新 ref，
  **不在** Scenario 覆盖范围内。
- **建议**：不在本 PR 阻塞；可在 `docs/gate.md §1.2` 或函数 docstring 里点一句
  「同值调用不修复台账缺条目」，避免使用者把它当修复合令。

### B1-6 · 文档漂移 · 低 —— README 的标题句「改一处、两处跟着走」未加限定

- **位置**：`README.md:185`（「怎么钉版本 / 怎么升级」段的标题句）。
- **证据**：在 `@v1`（即当前出厂默认指向的那份**旧** gate.yml）窗口内，该句**不成立**——
  旧 gate.yml 没有本 change 的解析 step（我查过 `v1` 的 gate.yml，`wl-ref` step 不存在）。
- **为什么不算实质超卖**：同节 20 行后已提「含新 gate.yml 的 ref」，且 README 另处明写
  「`v1.7.0` 发布之前，请仍然钉 `@v1`」 ⇒ 信息齐全，只是标题句缺限定语。
- **建议**：标题句补「（前提：那份 `uses:` 指向的 ref 里已含本 change 的 gate.yml）」。

### B1-7 · 文档 / 规格口径 · 低 —— 组合语义的「别以为要去删 policy」无钉子，且该路径输出仍带「请先 uninit」

- **位置**：spec `:132-138` 的组合语义 Scenario（`SHALL NOT 让用户以为要去删 policy`）；
  实现输出见 `initcmd.py:553`（`只增不改，拒绝覆盖。要更换 policy 请先 uninit`）。
- **证据**：该路径的输出仍然带「要更换 policy 请先 `uninit`」；而本 change 自己在
  `docs/gate.md §1.2:113-118` 明确判定：在**定制 policy** 的仓上这句「**不可照做**」
  （`uninit` 会把 `policy.json`、caller 与台账**一起删掉**，而定制 seed 按惯例不入库）。
- **为什么不算规格违反**：该 Scenario 的 Given 是「同时给一份**与已落地不同**的 `--policy`」，
  即本次**已给** policy；此时那句提示并非唯一出路，语义上说得过去。
- **建议**：给「输出点明 caller 已落盘、不回滚」这个断言补一条钉子（现在只有 B1 轮的实跑 C 证明），
  并考虑在该路径的输出里补一句「本次已给 `--policy` ⇒ 无需 `uninit`」，把 §1.2 的自我加码兑现。

### B1-8 · 风格 · 低 —— `caller_retarget_refusal` 与 `sync_caller_gate_ref` 重复台账前言

- **位置**：`src/witnessloop/initcmd.py:193-247` 与 `149-190`。
- **证据**：两函数各自实现「读台账 → 比对 `gate_ref` → 判 `created_files` 是数组」；同一次
  `init --gate-ref` 调用里对同一个 `init-manifest.json` 最多读 **4 次**（`run()` 接线 + 两个新函数）。
- **为什么是低危**：文件极小、无并发，重复不引入缺陷；但与仓内其它 helper（如 `_read_manifest`
  统一入口）的既有做法不一致，属可读性问题。
- **建议**：抽一个「读台账并返回 (entry, gate_ref)」的小 helper 给两处共用。

### B1-9 · 隐患 · 低 —— `tests/test_gate_workflow.py:504` 硬编 `assert "ref=v1" in …`

- **位置**：`tests/test_gate_workflow.py:504`。
- **证据**：同文件 `_fallback_ref()`（`:277-283`）刚刚为「不硬编 `v1`、从 gate.yml 读字面量」立了规矩，
  这一行却硬编 `"ref=v1"`。
- **为什么是问题**：post-merge 把兜底落点改到 `v1.7.0` 时，该断言靠**子串** `ref=v1` 侥幸仍绿
  （`ref=v1.7.0` 含 `ref=v1`）⇒ 断言语义被**静默弱化**，恰好是 tasks §6.1 想避免的那类陷阱。
- **建议**：改用 `assert f"ref={_fallback_ref()}" in …`。

### B1-10 · 证据可追溯性 · 低 —— 探针记录的两个 sha 在本 worktree 不存在

- **位置**：`tasks.md:41-46`（3.0）称本地保留的 `probe/workflow-ref`（`c7aa037`）是
  「Q1 唯一可追溯的本地物证」；`design.md §2 D1` 记录的原始输出里含 `6e2ec4d` / `2778bc2`。
- **证据**：`git cat-file -e 6e2ec4dc7955d6d155987a667040b126acab983b` 与
  `… 2778bc24e13c8fdd18e18765c81eb0ff731e6568` **均报 MISSING**；本地 `probe/workflow-ref`
  的 HEAD 是 `c7aa037`（含 `.github/workflows/probe-ref.yml`，34 行，内容形态与 design 记录的输出相符）。
  ⇒ 保留的那个分支**无法复算** design 里记的两个 sha。
- **为什么是低危**：design §2 D1 **已自行**把该证据登记为「单一来源、不可复现的二手文本」，
  并有独立（GitHub 文档）依据 —— 属**已披露**的证据等级问题，不是隐瞒。
- **建议**：把 tasks 3.0 的「唯一可追溯的本地物证」改为「唯一保留的探针**文件**（运行时的 revision
  已不可复算）」，口径与 design §2 D1 对齐。

## Verdict

**有条件通过。**

- 判据①（无未解决行为缺陷）：**满足**。未发现违反 spec 的行为缺陷；25 组变异中 4 组绿经查证为
  **已披露的覆盖缺口**（B1-1/B1-2）或**行为等价/遮蔽**（B1-3/B1-4），无漏判型缺陷。
- 判据②（每条 Requirement 有实现 + 钉子）：**R1/R2/R4/R5 满足**；**R3 未完全满足**——
  「能取到元数据」这条主干（`checkcmd.py:76`）零覆盖（B1-1），本 change 新增的另一个用户可见
  输出分支同样零覆盖（B1-2）。两条各补一条用例即可闭合。
- 判据③（无「文档承诺 ≥ 实现」漂移）：**满足**。§1.2 两条主张 + §8 + README 版本叙述均实跑复现，
  R1 的能力边界（GHES / fork）如实登记，未发现实质超卖；仅 B1-6 的标题句缺限定语、
  B1-7 属自我加码未兑现（低危，不阻塞）。

**放行条件（两条，代价极低）**：补 B1-1 与 B1-2 的用例；顺手订正 B1-3 的注释措辞。
B1-4…B1-10 不阻塞合并。

**未验证项**（不因此改变判定，但**不宣称**已验证）：R1-S1 的真 CI 端到端语义；
真 `uvx` 安装落的 `direct_url.json`；README ①′ 的 self-proof recipe；GHES 上 `job.*` 不可用。
