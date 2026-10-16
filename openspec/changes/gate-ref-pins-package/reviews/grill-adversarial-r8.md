# grill-adversarial R8（独立零记忆对抗验证轮）

## Reviewer

- 身份：**独立零记忆对抗验证者**（R8）。本对话**不携带** `gate-ref-pins-package` 的任何历史：
  文档里的「实测 / 已落库 / 已裁定 / 已收敛」在核到之前一律当作**待验证断言**。
  本轮目标是**证伪结论本身**，不是复述它。
- 被审 revision：`ab67ebde939d6e8eaed9a2b80a8a1b9912d78a62`（`git rev-parse HEAD`），
  分支 `gate-ref-pins-package/2026-10-16`，`git status --porcelain` 起始为**空**（树干净）。
- 关键文件 blob（`git hash-object`，全部等于 `git ls-tree HEAD` 的值 ⇒ 工作区与 HEAD 一致）：

  | 文件 | blob |
  |---|---|
  | `design.md` | `6f86cf99528a0e4b653ec03f768e4c89f81e47c2` |
  | `proposal.md` | `903714c3fc903289fb93927e313cbe76d90cc71b` |
  | `tasks.md` | `7313e9f157b524b92a6750569a777be7c794b2dd` |
  | `specs/gate-ref-pinning/spec.md` | `de8cc896c93e7cce65d6b83802509b144e00567f` |
  | `src/witnessloop/initcmd.py` | `b33f408392154593890b8a8af9ddaa37d8e5e9cd` |
  | `src/witnessloop/checkcmd.py` | `e12db4d94a1d11daebc80eb1423298de57bf487a` |
  | `src/witnessloop/constants.py` | `0a64184d5435399646646356fac56dd68622ffb0` |
  | `.github/workflows/gate.yml` | `330104b810db66a7c382c89ec075a04cfb03798c` |
  | `docs/gate.md` | `f79b48f8eaa26d3744017bcaf281fb3fb02b31e5` |
  | `README.md` | `700ade12d4ab45cebd7d0a61210dd0b88b2aa31e` |
  | `tests/test_gate_workflow.py` | `ff50aab8d4bc21d348d73ad548a6ed07afa0618e` |
  | `tests/test_init_gate_ref.py` | `e785c87a441e107ac29033820565d9936ca79dd0` |
  | `tests/test_check_package_ref.py` | `09f63404758c90305efbb690a53fba5002222908` |

- 基线复算（原始输出）：`PYTHONPATH=src python3 -m pytest -q` ⇒ **`686 passed in 31.85s`**
  （与题面一致）。
- 方法：
  - 快照一律 `git archive HEAD | tar -x -C /tmp/adv8/<name>`（**不是** `cp -a`：worktree 的 `.git`
    是指针文件，复制会把 `git commit` 打进真仓——R4 的事故）。
  - 「变异 ⇒ 跑全量」全部在 `/tmp/adv8/mut*/` 的**无 `.git` 副本**里做；
    行为类实验在 `/tmp/adv8/<A|E|F|G|A2>` 里用**快照里的 CLI**（`PYTHONPATH=/tmp/adv8/snap/src`）跑。
  - 真仓**一个字节都没改**（除本报告），末尾已复查（见「收敛结论」）。
  - 前几轮已跑的 40+ 条变异**没有重跑**（题面点名不必重跑的那 8 条也一律没重跑）；下面每一条都是新面。

## 对抗结论

**判据①：不满足** —— 本轮找到 **4 条新的可证伪项（V1–V4）**，其中：

- **行为缺陷 1 条**：**V1** —— `init --gate-ref <新>` 在「台账里没有 caller 条目 **且** 盘上没有
  caller 文件」这一态下**静默 no-op**，却打印「幂等，无改动」、`gate_ref` **不**同步（实测原始输出在 V1）。
  这条与 `spec.md:113-118` 的 Scenario Then **正面冲突**。
- **行为面/文档 1 条**：**V2** —— 本轮交付的**升级动作**（`docs/gate.md:82-88` / `README.md:192-195`
  / `spec.md:84-99`）按字面执行后，**接入方自己的 `check` 必红**（台账同步 = 不变集里的 `M`，
  要一条 `protected_path_write` 事件）。该事件要求**只**写在 change 自己的迁移步骤里
  （`design.md:179-183` / `tasks.md:55-59` / `:120-123`），**接入方可见的文档里一个字都没有**。
- **缺一条钉子 2 条**：**V3**（spec 点名的第 4 类来源「兜底」在 `::notice::` 里的文案零断言）、
  **V4**（`--dry-run --gate-ref` 那条 Scenario 的「SHALL 不 说「幂等，无改动」」零断言）。

**判据②：满足** —— K1–K8 / L1–L6 / M1–M4 / N1–N3 / P1 / T1 / U1–U4 与 R6 的两条，我**逐条去
正文与代码里核**（**不核 §7.9 的自述表**，落点见下表），全部落在正文/实现/钉子处。
唯一一处**部分落库**：R7 的 U2 除了两条钉子外还要求改文档指向（`design.md:415-417` /
`tasks.md:92-93` 仍写「由 `test_resolve_constants_match_the_single_source` 钉住」，而该测试只比
env 字面量——**这正是 R7 点名的缺口本体**）；两条新钉子**已存在**，指向文本**未更新**。
我判它**不**单独构成「必须修改项」（那句话本身仍为真、只是不完整），但如实登记在此。

⇒ **不收敛**（判据①不满足；判据②满足）。判据①②的核实过程与结论见末节「收敛结论」。

### 判据② 逐条核实（落点均已去正文/代码复核，非读 §7.9 表）

| # | 我核到的落点（证据） | 结论 |
|---|---|---|
| K1 | `design.md:146-164`（「R1 K1 订正（原稿此处为假）」+ 证据等级）；`spec.md:60-72`（Requirement + 订正脚注）；`checkcmd.py:30-91` 真有 PEP 610 读取面 | 已落库 |
| K2 | `proposal.md:19-29` 整段改写（`⚠️「没有任何提示」是**假**的`，贴了 `uvx` 的 `Building witnessloop @ git+…`） | 已落库 |
| K3 | `design.md:134-144`（降级为「响亮、可恢复的分叉态」+ 三条恢复路径）；钉子 `tests/test_init_gate_ref.py:123-137` | 已落库 |
| K4 | `design.md:166-183`（本 PR 不做本仓迁移 + 自证命令今天本来就红 + post-merge 三件事） | 已落库 |
| K5 | `design.md:265` 的复算订正。**我独立复算**：`git rev-list --count v1..origin/main` = **`47`** ✓；`git rev-parse v1^{commit}` = `ae992565ee2162e5b272af471e9adf895e7f83fb` ✓（= `v1` tag 指的那个 commit） | 已落库（数字对） |
| K6 | `docs/design.md:56` 与 `:73` 两处都点名该 change 并指向 `docs/gate.md §1.2` | 已落库 |
| K7 | `design.md:140-144`（`entry.get("sha256") and …` 的已知出口）+ `:187-189`（D6 不收紧） | 已落库 |
| K8 | `design.md:77-104`（探针原始输出 + 证据等级）+ `tasks.md:41-46`（3.0） | 已落库 |
| L1 | `tasks.md:81-88`（「时序是承重的，别调换」→ 先改默认值）→ `:124`（再建 tag）→ `:125-126`（6.3 必须同一提交） | 已落库 |
| L2 | `docs/gate.md:100-110`（两步 + 旧 CLI 的冲突原文 + 「别去删 policy」）、`README.md:197-201` | 已落库 |
| L3 | `tests/test_gate_workflow.py:466-479`（`default == ""` 断言） | 已落库 |
| L4 | `spec.md:120-126`（Scenario）+ `initcmd.py:307-319` / `:466-479`（`handled` 文案）+ `tests/test_init_gate_ref.py:233-261` | 已落库 |
| L5 | `spec.md:106-111`（`--dry-run`）、`:113-118`（台账无 caller 条目）两条 Scenario 都在 | 已落库（但两条的钉子各有缺口，见 V1 / V4） |
| L6 | `design.md:226`（两类仓）、`docs/gate.md:119-124`、`tasks.md:128-132` | 已落库 |
| M1 | `tests/test_init_gate_ref.py:28`（`NEW_REF = …@v9.9.9`）+ `:46-48`（`test_new_ref_does_not_collide_with_the_factory_default`）+ `tasks.md:95-98` | 已落库 |
| M2 | `docs/gate.md:222-231`（落盘名 / 覆盖陷阱 / 两条落法）、`tasks.md:71-77`、`:16-19` | 已落库 |
| M3 | `tasks.md:114-119`（`head_sha` 之后只允许证据文件 + 正确顺序） | 已落库 |
| M4 | `docs/gate.md:90-100`（①′ 命令）与 `README.md:194`；钉子 `tests/test_docs.py:286-297`。**另我独立复算**：`git show v1:src/witnessloop/checkcmd.py \| grep -c 本包来源` ⇒ **`0`** ⇒ 文档那句「旧的 `@v1` 包**没有**这一行」**成立** | 已落库 |
| N1 | `tests/test_init_gate_ref.py:297-328`（补条目 + 插在 `self` 之前 + 随后幂等 + `uninit` 真能回滚） | 已落库 |
| N2 | `initcmd.py:276-279`、`:290-291`（不再自称「其余文件无改动」）+ 钉子 `tests/test_init_gate_ref.py:75-88` | 已落库 |
| N3 | 三处：`docs/gate.md:502-520`（§7.1 用「兜底 ref」表述）、`design.md:230`（§4 R6 表）、`tests/test_gate_workflow.py:277-283`（不在测试里硬编 `"v1"`）。**我另做全仓活面复查**（`grep -rn "v1" src/ .github/ tests/`）：剩下的命中全是 schema 标签（`witnessloop/policy@v1` 等）、历史引文、`DEFAULT_GATE_REF` 字面量自身、以及「v1 硬编码 OpenSpec 形状」这类**版本标签**用语 | 已落库 |
| P1 | `initcmd.py:168-174`（先判数组）+ `:191-213`（不再兜）+ `:400-411`（受控诊断退 1）+ 钉子 `tests/test_init_gate_ref.py:331-357` | 已落库 |
| T1 | `tests/test_gate_workflow.py:532-549`（钉来源 + run 里不得再出现该输入 + uvx 用的就是该变量） | 已落库 |
| U1 | `tests/test_gate_workflow.py:552-565`（三条分支的来源文案，见 V3 的**残留**） | 已落库（不完整，见 V3） |
| U2 | `tests/test_gate_workflow.py:568-578`（哨兵 `v9.9.9` 行为钉）+ `:581-586`（文本钉读点） | 钉子已落库；**文档指向半句未改**（见上） |
| U3 | `tests/test_check_package_ref.py:154-167`（注入二元组，两值各自绑定） | 已落库 |
| U4 | `tests/test_check_package_ref.py:170-179`（自报行是 stdout 第一行） | 已落库 |
| R6-D1 序 | `gate.yml:34-45`（①–⑤ 判定顺序逐条）+ `tests/test_gate_workflow.py:508-523` | 已落库 |
| R6-recipe 序 | `tests/test_docs.py:286-297`（`docs/gate.md` 与 `README.md` 两处都钉） | 已落库 |

### 判据① 新证伪项（4 条）

---

**V1（行为缺陷）**：`init --gate-ref <新>` 在「台账无 caller 条目 **且** 盘上无 caller 文件」时
**静默 no-op**——`gate_ref` 不同步、条目不补、还打印「幂等，无改动」。

- 规格要求（`spec.md:113-118`，Scenario「台账里没有 caller 条目」）：
  > **Then** SHALL 同步 `gate_ref` 并**补上**该条目（`sha256` = 新内容），条目位置 SHALL 在台账自己的
  > `self` 条目**之前**；盘上**没有** caller 文件时 SHALL NOT 凭空新建它（**交给漂移判定响亮地报**）

- 实现（`initcmd.py:175-177`）：
  ```python
  path = root / C.GATE_WORKFLOW_PATH
  if not path.is_file():
      return None      # ← 直接放弃，连 gate_ref 都不同步
  ```
  而 `return None` 的后果是 `initcmd.py:300-301` 走 `_already_initialized(..., note=note)`——
  **不带 `ignore`/`handled`**；台账里既然**没有** caller 条目，漂移判定（`initcmd.py:416-424` 只遍历
  `created_files` 里列出的路径）**根本不会看 caller**，`conflicting_files()` 对**不存在**的文件也不报冲突
  （`initcmd.py:134-136` 的 `if path.exists()`）⇒ 三个分支全不命中 ⇒ 落到 `initcmd.py:483-485` 的
  「幂等，无改动」。

- 原始输出（命令：在 `/tmp/adv8/G`，快照 CLI；先 `init`，再把台账里 caller 条目删掉、把
  `.github/workflows/witnessloop.yml` 删掉，然后跑第 3 行那条命令）：
  ```
  ledger: caller entry removed -> ['.witnessloop/policy.json', '.witnessloop/init-manifest.json']
  caller file deleted
  === init --gate-ref NEW (entry absent AND file absent) ===
  init：已接入 witnessloop（幂等，无改动）。
  EXIT=0
  --- ledger gate_ref ---
  Xingkai98/witnessloop/.github/workflows/gate.yml@v1
  ```
  ⇒ 用户**显式**要求换成 `…@v1.7.0`，工具回「幂等，无改动」并把台账留在 `@v1`。
  这同时踩了本 change 的题眼（**不静默**）与本仓自己写下的「工具不撒谎」契约
  （`initcmd.py:382-384` 的 `note` 注释、`tests/test_init_tests_command.py:70-81` 的 B4b）。

- 与相邻两态的对照（**只有这一态是坏的**，说明它不是「刻意不修」而是漏了）：
  - 条目**在**、文件**不在** ⇒ `EXIT=1` + 「被改动过」诊断（钉子 `tests/test_init_gate_ref.py:162-172`）；
  - 条目**不在**、文件**在** ⇒ 真补条目 + 同步（钉子 `tests/test_init_gate_ref.py:297-328`）；
  - 条目**不在**、文件也**不在** ⇒ **本 V1：EXIT=0 + 静默**（**无任何测试覆盖**，我实测得到）。

---
  
**V2（行为面 / 文档）**：本轮交付的「单一、显式」升级动作，照字面执行后**接入方自己的 required check 必红**，
而该后果在接入方可见的文档里**没有任何一处**提到。

- 文档给出的动作（`docs/gate.md:82-88`，`README.md:192-195` 同款三步；`spec.md:84-99` 是它的
  Requirement 形态）：
  ```
  ② 再 `witnessloop init --gate-ref <同一个新 ref>` ⇒ **重写 caller + 同步台账**
     （`init-manifest.json` 里该条目的 `sha256` 与 `gate_ref`），其余文件照旧只增不改；
     之后 plain `init` 回到幂等、`uninit` 仍可用。
  ```
- 但 `.witnessloop/init-manifest.json` 是**不变集**成员（`policy.py:18-23`），且**默认 policy 的
  `protected_paths` 也含 `.witnessloop/**`**（`policy.py:35-38`）⇒ **修改**它（状态 `M`；`A` 才免事件，
  `checkcmd.py:388-389`）必须有一条 `protected_path_write` 解释事件。
  该要求在本 change 里**只**写在「本仓自身迁移」的三处：`design.md:179-183`、`tasks.md:55-59`、`:120-123`
  （原文「否则改台账这个 **`M`** 必红」）——`docs/gate.md §1.2` / `README.md` 的升级 recipe **零提及**。
  （对照：`README.md:103-105` 对**同一条规则**在 `.witnessloop/policy.json` 上写得明明白白 ⇒
  文档面上是**自相矛盾**的：同目录同类文件，一处要求事件、另一处不提。）

- 原始输出（命令：在 `/tmp/adv8/A` 的快照仓里，先 `init` → 提交 → 按文档第 ② 步跑
  `init --gate-ref …@v1.7.0` → 提交 → `check --base main --head HEAD`）：
  ```
  === changed files ===
  .github/workflows/witnessloop.yml
  .witnessloop/init-manifest.json
  === check ===
  check：未通过 ✗（1 项）
    1. .witnessloop/init-manifest.json：受保护路径被写入，但没有结构化解释事件（需 workflow-events.jsonl 里有 event_type=protected_path_write、artifact_path 指向该文件、reason/approved_by 非空的事件）
  EXIT=1
  ```
- **差分对照**（同一快照、同一命令，只把「升级 PR」换成「首次接入 PR」）：
  ```
  === check on the ONBOARDING pr (ledger status A) ===
  check：通过 ✓
  EXIT=0
  ```
  ⇒ 是**本 change 新引入的那个动作**（升级时改台账）触发的，`A` 态的接入 PR 不受影响。
- 属性说明（避免夸大）：接入方**不是**死锁——`docs/gate.md §4` 有事件格式，补一条即可。
  被证伪的是**「单一、显式」这句话本身**：实际是「两步 + 一条不被 §1.2 提及的簿记步骤」，
  而阅读 §1.2 的人会在自己的 required check 上撞一次红。

---

**V3（缺一条钉子）**：`spec.md:57-58` 把来源**列举成四类**，其中「兜底」（= `job.workflow_ref` 成功
解析那条路）在 `::notice::` 里的文案**零断言**；把它换成一个**误导性**的标签，全量 686 条**全绿**。

- 规格原文（`spec.md:57-58`）：
  > **Then** SHALL 有一行明确写出本次使用的 witnessloop ref **及其来源**
  > （显式传入 / `job.workflow_sha` / 兜底 / fail-closed）
- 现有钉子（`tests/test_gate_workflow.py:552-565`）只断言**三类**：`显式` / `job.workflow_sha` /
  `fail-closed`。第 4 类「兜底」没有断言。
- 变异 A1（`gate.yml:90`，把**分支**兜底的来源文案改成**调用方显式传入**——不只是没来源，而是**指错**）：
  ```diff
  -                WHY="job.workflow_ref 的分支名（job.workflow_sha 缺失时的兜底）" ;;
  +                WHY="调用方显式传入的 with.witnessloop-ref" ;;
  ```
  原始输出：`686 passed in 38.23s`
  该变异下 CI 日志会打 `::notice::witnessloop 包 ref = feat/x（来源：调用方显式传入的 with.witnessloop-ref）`
  ——**与实际来源相反**，直接违背 `spec.md:57-58`。
- 变异 A2（`gate.yml:93`，tag 兜底的来源整段换成 `"???"`）：原始输出 `686 passed in 40.19s`。
- 顺带复算（能力内的探查，**未发现**可证伪项，如实记录）：我按 `gate.yml:87-96` 的 `case` 把解析 step
  抽出来真跑，`WL_WORKFLOW_REF` 取 `…@refs/heads/feat/x@y` ⇒ `ref=feat/x@y`（`##` 剥**最长**前缀，
  带 `@` 的分支名**正确保留**）；`…@refs/tags/v1.7.0` ⇒ `v1.7.0`；裸 `refs/heads/main`（无 `@`）
  ⇒ fail-closed 退兜底 ref + `::warning::`（与 `spec.md:40-42` 的「缺 `@`」样本一致）。
  **这一条（题面点名让我看的 `@` 分支名）没有找到缺陷。**

---

**V4（缺一条钉子）**：`spec.md:106-111` 的 `--dry-run` Scenario 明写「输出 SHALL **不**说「幂等，无改动」」，
但这条约束在 **`--gate-ref` 这条轴**上零断言。

- 规格原文（`spec.md:109-111`）：
  > **Then** caller 与台账 SHALL **都不落盘**（…），且输出 SHALL **不**说「幂等，无改动」（它确实会改），
  > SHALL **不**报冲突（那条冲突正是这个动作要消掉的）
- 全仓 `"幂等" not in` 的断言只有三处：`tests/test_init_gate_ref.py:71`（**非** dry-run 的重写路径）、
  `tests/test_init_tests_command.py:81`、`:95`（**tests 命令文件**那条轴，`--test-command --dry-run`）。
  **没有一个**落在 `--dry-run --gate-ref` 这条轴上——而 spec 那条 Scenario 的 When 正是
  `init --dry-run --gate-ref <新 ref>`。
- 变异（`initcmd.py:181`，把 dry-run 的 note 变成 falsy ⇒ `if note:` 落到「幂等」分支）：
  ```diff
  -        return f"[dry-run] 未落盘：{C.GATE_WORKFLOW_PATH} 与台账将一起改成 {gate_ref}"
  +        return ""
  ```
  原始输出：`686 passed in 38.18s`
  该变异下的**真实行为**（同一命令，变异前 / 变异后）：
  ```
  === baseline (unmutated) ===
  init：[dry-run] 将重写 .github/workflows/witnessloop.yml（→ …@v1.7.0）并同步台账
  init：已接入 witnessloop（[dry-run] 未落盘：.github/workflows/witnessloop.yml 与台账将一起改成 …@v1.7.0）。
  === mutated (note -> "") ===
  init：[dry-run] 将重写 .github/workflows/witnessloop.yml（→ …@v1.7.0）并同步台账
  init：已接入 witnessloop（幂等，无改动）。
  ```
  ⇒ 一个「同一次输出里前半句说将重写、后半句说幂等」的**自相矛盾**，规格明令禁止，**没有任何测试**会红。
- 属性说明：**今天的代码行为是对的**（我复跑未变异版确认）；这是「缺一条钉子」，不是行为缺陷。
  与 R5 修的那条（`已落盘` / `未落盘` 两面都要钉）属**同一个 spec 子句的另一个分支**
  ——R5 只覆盖了「报冲突时」的那半。

---

## 未验证项

以下**我做不到**，按题面规则**不计入必须修改项**（除非它们被文档写成了已验证——本轮**没有**
新增这一类；V2 是「文档漏写**新行为**的后果」，性质不同）：

1. **真 CI 的 `job.*` 取值**：`job.workflow_sha` / `workflow_repository` / `workflow_ref` 在真 GitHub 上
   的实际语义。本工作区跑不了跨仓真 CI。
2. **Q1 探针（run `38853369550`，`design.md:77-104`）的原始输出是二手、单一来源、不可复现**：
   它被**质疑**了（探针用的是 `probe-ref.yml` 而不是 `gate.yml`，且是**同 owner 跨仓**形态），
   但证伪它需要真 CI。**我确认文档已如实标注证据等级**（`design.md:97-104`），且结论另有官方
   contexts 文档依据 ⇒ 我**不**据此判 (B′) 错，但**我确实没有独立验证它**。
3. **GHES / 同 owner fork / 自建 runner** 面：`job.*` 不可用时的行为、uv 版本差异。
4. **`pip install git+…` 是否同样落 PEP 610 的 `vcs_info`**（只实测过 uv 0.13.1 的 `uvx`）。
5. **`v1.7.0` 尚不存在**：`tasks.md:134-148` 的验收命令、`README.md` 里指向 `@v1.7.0` 的 recipe
   今天都指向一个**不存在的 ref**（文档已就地写明，见 `README.md:204-205` / `tasks.md:144`）。
6. **issue #30 的数字**（`v1` ⇒ ✗10 / `main` ⇒ ✗1）来自该 issue 正文，未复算。
7. **`refs/pull/N/merge` 的 uv 行为**：文档只说「不是稳定的可安装 ref」、**不**声称必然安装失败
   （`spec.md:42-43`）——这个谨慎措辞我认，但**未实测**。
8. **`installed_vcs_ref()` 命中同名无关 dist-info 时会静默报错值**（本轮新测出的**既有**属性，
   不是本 change 引入，登记为低危观察）：我在 `sys.path` 最前放一个伪造的
   `witnessloop-0.1.0.dist-info/direct_url.json`（指向 `https://github.com/EVIL/other`）⇒
   原始输出：
   ```
   installed_vcs_ref -> ('v9.9.9', 'deadbeef')
   check：本包来源（自报，尽力而为）：requested_revision=v9.9.9，commit_id=deadbeef
   ```
   ⇒ 自报行会**如实转述**它看到的那个 dist-info。真 CI 的 `uvx` 临时环境里只有一个 dist-info，
   所以**可达性未验证**；且 `importlib.metadata` 的解析顺序不是本 change 能控的。
9. **`with: witnessloop-ref: "   "`（纯空白）**：`gate.yml:78` 的 `[ -n "$WL_INPUT_REF" ]` 对空白为真 ⇒
   `ref=   `（空白 ref）⇒ `uvx …@   ` 会响亮失败（不是静默错版），但它**不是**「空串」。
   `tests/test_gate_workflow.py:454-463` 的 `test_resolve_never_leaves_the_ref_empty` 里那个
   `{"WL_INPUT_REF": " "}` 用例只靠 Python 的 `bool(" ") is True` 通过。
   我判**低危、非必须修改**（触发条件要求调用方显式写一个空格）。

## 必须修改项

- **V1**（`initcmd.py:175-177`；规格 `spec.md:113-118`）：让「台账无 caller 条目 **且** 盘上无 caller 文件」
  这一态**不静默**。两条路（择一，或都做）：
  ① 在该分支**不**提前 `return None`，而是照常同步 `manifest["gate_ref"]` 并补条目（**不**新建文件），
  即「条目/账本轴照做、文件轴不做」——这最贴合 `spec.md:113-118` 的字面（Then 两个分句可同时成立）；
  ② 或者保持不写，但把「响亮地报」**真做出来**（当前那条注释 `initcmd.py:158-160` 承诺的
  「交给漂移分支响亮地报」在这组合下**不可能**发生：漂移判定只遍历 `created_files` 里列出的路径）。
  无论走哪条，钉子都要有：在该组合下断言**输出里不得出现「幂等」**，且 `gate_ref` 终态符合所选语义。
  ⚠️ 改这条会碰到 `spec.md:113-118` 的措辞（那句「交给漂移判定响亮地报」按字面**无法实现**）——
  请把 Scenario 与实现一起改准，别只改一边。
- **V2**（`docs/gate.md:82-88` / `README.md:192-195` / `spec.md:84-99`）：把「升级动作 = 两步」订正为
  **三步**（或至少就地写明第三步），并**点名文件**：改 `.witnessloop/init-manifest.json` 是
  `M` ⇒ 升级 PR 需要一条 `protected_path_write` 解释事件（格式见 `docs/gate.md §4`），
  否则接入方自己的 `check` 必红。顺带把 `spec.md:84-99` 的 Requirement 加一条边界注
  （该动作改的是不变集成员）。**回退面很小**：三处文字 + 一条 Scenario 注。
- **V3**（`gate.yml:90` / `:93`；规格 `spec.md:57-58`）：把「兜底」那一类来源也钉住——在
  `tests/test_gate_workflow.py` 的 `_run_resolve` 上再加一条断言（例如
  `WL_WORKFLOW_REF=…@refs/heads/main` 且 sha 为空 ⇒ 来源文案里必须出现 `job.workflow_ref`
  或「兜底」）；`refs/tags/*` 那条同理。既然 spec 把来源**列举成四类**，四类都要有断言。
- **V4**（`initcmd.py:181`+`:302`；规格 `spec.md:109-111`）：补一条**行为级**断言——
  `init --dry-run --gate-ref <新>` 的输出里 `"幂等" not in out`（并同时钉它**不**报冲突、
  且 `git status --porcelain` 不变）。这条与 R5 修的那条（`已落盘`/`未落盘` 两面）是同一条
  spec 子句的两个分支，别只留一个。

## Open Questions

1. **V1 该走哪条语义**（同步台账但不建文件 vs 什么都不做但响亮报错）？我倾向①（同步 + 补条目 +
   不建文件）：它与 `spec.md:113-118` 的 Then **逐字相容**，且「用户显式给了 ref ⇒ 台账必须跟着走」
   符合本 change 的「单一事实来源」。另一种做法要**改 spec**（那句「响亮地报」按字面不可实现）。
2. **V2 的修法面**：只加文档（三步）+ `spec.md` 一句边界注，还是干脆让 `init` 在同步台账时
   **自动**在 change 目录里写一条事件？后者会把「工具自己写解释事件」引入本 change 的作用域
   （`init` 目前完全不碰 `workflow-events.jsonl`）⇒ 我倾向**只改文档**，但这需要主 session 拍。
3. **`design.md §1` 的「消费点全集……没有第五处」现在是过时证据句**：本 change **自己**新增了
   一个消费点（`initcmd.sync_caller_gate_ref` 读 `manifest["gate_ref"]`），且那段里的行号
   （`initcmd.py:192/193/251`）已漂到 `:259/260/348`。它不是行为缺陷、属**测量时点**类
   （与 R7 登记的两条同性质），但既然 R7 那两条被要求「改成不带数字的表述」，这条是否也一并处理？
   我**没有**把它列为必须修改项（§1 明确自称是「**现状**逐行实测」，读作历史快照成立）。
4. **`tests/test_gate_workflow.py:504` 的 `assert "ref=v1" in out_path…` 是**子串**断言**：
   post-merge 把兜底改成 `v1.7.0` 后它仍会通过（`"ref=v1"` 是 `"ref=v1.7.0"` 的前缀）。
   即「它在这一步**不会**按设计意图变红」。`tests/test_gate_workflow.py:568-578` 的哨兵测试
   覆盖了同一件事，所以我不列为必须修改项，但它是颗**哑雷**（同族的还有
   `tests/test_gate_workflow.py:59`，那条**会**红，且已经在 `tasks.md:94` 的清单里）。

## 收敛结论

**不收敛。**

- **判据②（前七轮的「必须修改项」全部已落库）：满足。** K1–K8 / L1–L6 / M1–M4 / N1–N3 / P1 / T1 /
  U1–U4 与 R6 的两条（D1 判定顺序、recipe 顺序）我**逐条去正文与代码里核过**（落点见上表，
  不读 §7.9 自述表），全部落在正文/实现/钉子处。**唯一残留**：R7 的 U2 除了两条钉子，还要求把
  `design.md` / `tasks.md` 里「由 `test_resolve_constants_match_the_single_source` 钉住」这句
  改成指向**读点**的钉子（`design.md:415-417`、`tasks.md:92-93` 仍在指 env 字面量那条）——
  钉子本体已在，**指向文本未更新**。我判它**不足以**推翻判据②（那句话仍为真、只是不完整，
  且属**指向/措辞**类），但如实登记，供主 session 一句改掉。
- **判据①（本轮没有新的可证伪项）：不满足。** 4 条新证伪项，按类别分开陈述：
  - **行为缺陷（1 条）**：V1 —— `init --gate-ref` 在「台账无条目 + 盘上无文件」时静默 no-op
    并谎报「幂等」，与 `spec.md:113-118` 的 Then 正面冲突（**无任何测试覆盖**，我实测）。
  - **行为面 / 文档（1 条）**：V2 —— 本轮交付的升级动作按字面执行 ⇒ **接入方的 required check 必红**
    （台账 = 不变集 `M`，要解释事件），而这条后果只在 change **自己的**迁移步骤里写过。
    这不是「某个变异没被钉」，是**交付物照文档用不通**。
  - **缺一条钉子（2 条）**：V3（spec 列举的 4 类来源里「兜底」那类的 notice 文案零断言，
    变异后打出一条**指错来源**的日志仍全绿）、V4（`--dry-run --gate-ref` 那条 Scenario 的
    「不许谎报幂等」零断言，变异后输出自相矛盾仍全绿）。两条的**当前代码行为都是对的**。
- 已知**刻意不修**的四条（`docs/gate.md` 只改编号时不再变红、`_set_ledger_gate_ref` 的纵深防御、
  dry-run 的 `print`、`_set_ledger_gate_ref` 的 `self` guard）我**同意**它们是「无行为后果 / 不可达」，
  **不列**为必须修改项。
- 题面点名让我挑的**新面**里，我试过、**未找到可证伪项**的四条，如实记录（避免读者以为全盘被推翻）：
  ① `gate.yml` 剥 `refs/heads/` 前缀在**带 `@` 的分支名**下正确（`feat/x@y` ⇒ `feat/x@y`）；
  ② 台账 caller 条目 `sha256: null`（K7 的出口）+ 新重写 ⇒ **修好了**，终态是不动点
  （`--gate-ref` 把 `sha256` 补实、随后 plain `init` 幂等、`uninit` EXIT=0，实测）；
  ③ `docs/gate.md §1.2` 的 ①′ `… 2>/dev/null \| head -1`：未接入目录里 **stdout 有那一行**
  （`check：本包来源…`），管道退 0、裸跑退 3（= `EXIT_NOT_ONBOARDED`），**没有** BrokenPipe 可见症状；
  该 recipe 不看退出码，故我判**低危观察**、非必须修改项；
  ④ `installed_vcs_ref()` 的同名 dist-info 遮蔽 ⇒ 见「未验证项 8」（可达性未验证，属既有属性）。
- **本报告未改动真仓任何被审文件**。收尾复查：
  `git log --oneline -2` ⇒ `ab67ebd …` / `7dfe299 …`；`git status --porcelain` ⇒ 只有本报告一份未跟踪文件。

---

## 处置（主 session 在 R8 之后追加，非审阅者原文）

> 本报告判定**不收敛**（判据②满足、①不满足），基准 `ab67ebd`。**V1–V4 全部已落库**，
> 每条都复核过。**V1 与 V2 是本 change 里最后两条**非「缺钉子」类的发现**，谢谢。

- **V1（行为缺陷）**：`init --gate-ref <新>` 在「台账无 caller 条目 **且** 盘上无文件」时**静默 no-op**。
  **修法**：新增 `initcmd.caller_retarget_refusal()`，在 `run()` 里**先判可否做成**，做不成就
  **响亮拒绝**（一句说明 + 退 1），不做任何写入。钉子
  `test_no_caller_entry_and_no_file_refuses_loudly`（断言退 1、不出现「幂等」、
  台账逐字节未动、也没复活 caller）。⚠️ 我第一版把判据写成「无条目就拒」，被
  `test_ledger_without_a_caller_entry_is_repaired` 当场抓住（文件在 ⇒ 补条目即可，能做成）——
  **加了一行 `is_file()` 守卫**才对。
- **V2（文档缺口）**：文档给的升级动作照字面做 ⇒ 接入方 `check` **必红**。**我独立复现了**：
  `check` 报 `.witnessloop/init-manifest.json：受保护路径被写入，但没有结构化解释事件`（EXIT=1）；
  补一条 `protected_path_write` 事件后该条消失；⚠️ 但我**也复现了你没提到的更坏一步**——
  把事件放进**新建的**「只有事件文件」的目录，会触发 change 目录契约、红从 **1 条变 7 条**
  （缺必需件 + 缺 manifest）。⇒ 文档写的是「写进**既有** change 目录」这条路，
  并把「新建只有事件的目录会更糟」一并写明。落点：`docs/gate.md §1.2`、`README.md`、
  `spec.md` 的升级 Requirement 的「代价（SHALL 写进文档）」。
- **V3（缺钉子）**：`test_resolve_notice_names_the_source_of_the_ref` 补第四类来源
  （`job.workflow_ref` 兜底）的断言——spec 列了**四类**，此前只钉三类。
- **V4（缺钉子）**：`--dry-run --gate-ref` 轴上补 `assert "幂等" not in out`。
- **你点名的措辞残留**（`design.md` / `tasks.md` 仍写「由 `test_resolve_constants_match_the_single_source` 钉住」
  兜底同源）：已改成**三条**并列，并写明 R7-U2 证明只靠第一条会被「把字面量硬编进脚本」蒙过去。

**R9**：树在该 revision 上冻结（本轮之后只追加 `reviews/` 证据与 §7.9 小节）。
请**优先找行为缺陷**（V1/V2 那类）；若只剩「再补一条钉子」，请标明类别。
