# grill-adversarial R7（独立零记忆对抗验证轮）

## Reviewer

- 身份：**独立零记忆对抗验证者**（R7）。本对话**不携带** `gate-ref-pins-package` 的任何历史：
  文档里的「实测 / 已落库 / 已裁定 / 已收敛」在核到之前一律当作**待验证断言**。
- 被审 revision：`9bf5c8c54359ecd428f0ca9fe67445c873298134`（`git rev-parse HEAD`）。
- 关键文件 blob（`git hash-object`，全部与工作区一致、无未提交改动）：

  | 文件 | blob |
  |---|---|
  | `design.md` | `6346a2b1782265e23a1571468400bce4d1da381c` |
  | `proposal.md` | `903714c3fc903289fb93927e313cbe76d90cc71b` |
  | `tasks.md` | `7313e9f157b524b92a6750569a777be7c794b2dd` |
  | `specs/gate-ref-pinning/spec.md` | `de8cc896c93e7cce65d6b83802509b144e00567f` |
  | `src/witnessloop/initcmd.py` | `b33f408392154593890b8a8af9ddaa37d8e5e9cd` |
  | `src/witnessloop/checkcmd.py` | `e12db4d94a1d11daebc80eb1423298de57bf487a` |
  | `src/witnessloop/constants.py` | `0a64184d5435399646646356fac56dd68622ffb0` |
  | `.github/workflows/gate.yml` | `330104b810db66a7c382c89ec075a04cfb03798c` |
  | `docs/gate.md` | `f79b48f8eaa26d3744017bcaf281fb3fb02b31e5` |
  | `README.md` | `700ade12d4ab45cebd7d0a61210dd0b88b2aa31e` |

- 基线复算：快照（`git archive HEAD | tar -x -C /tmp/adv7`，**不是** `cp -a`）里
  `PYTHONPATH=src python3 -m pytest -q` ⇒ **`681 passed in 39.80s`**（与题面一致）。
- 方法：**先变异、再跑全量**。每个变异在 `/tmp/adv7/mut/<name>/` 的独立快照里做
  （`git archive` 导出 ⇒ 副本里没有 `.git`，不可能污染真仓），然后跑全量。
  本仓**一个字节都没改**（除本报告）。
- 我**没有**重跑 R1–R6 已跑过的变异面（harness 每轮 38s，30+ 条无谓重复不值当）；下面每一条都是新面。

## 对抗结论

**判据①：不满足** —— 本轮找到 **4 条新的可证伪项**（U1–U4），全部是「**变异后全量 681 全绿**」
的形态、且都在本 change 新增的代码面上。**判据②：满足** —— K1–K8 / L1–L6 / M1–M4 / N1–N3 /
P1 / T1 与 R6 的另两条，我逐条去**正文与代码**里核过（**不核 §7.9 的自述表**），全部已落库。
⇒ **不收敛**（详见「收敛结论」）。

### 判据② 逐条核实（落点均已去正文/代码复核，非读 §7.9 表）

| # | 我核到的落点（证据） | 结论 |
|---|---|---|
| K1 | `design.md:146-164`（`R1 K1 订正（原稿此处为假）`）、`spec.md:60-72`（Requirement + 订正脚注）、`design.md:436`（Q4 裁定）；`src/witnessloop/checkcmd.py:30-91` 真有 `vcs_info` 读取面 | 已落库 |
| K2 | `proposal.md:19-29` 整段改写（`⚠️「没有任何提示」是**假**的`，贴了 `uvx` 的 `Building witnessloop @ git+…`） | 已落库 |
| K3 | `design.md:134-139`（降级为「响亮、可恢复的分叉态」+ 三条恢复路径）；对应钉子 `tests/test_init_gate_ref.py:123-137`（`test_rewrite_rescues_a_hand_edited_caller`） | 已落库 |
| K4 | `design.md:166-181`（本 PR 不做本仓迁移 + 自证命令今天本来就红 + post-merge 三件事） | 已落库 |
| K5 | `design.md:263`（复算订正）；**我独立复算**：`git rev-list --count v1..origin/main` = **47** ✓；`git rev-parse v1^{commit}` = `ae99256…` = `v1.6.0` ✓ | 已落库（数字对） |
| K6 | `docs/design.md:56` 与 `:73` 两处都点名 change 并指向 `docs/gate.md §1.2` | 已落库 |
| K7 | `design.md:140-144`（`entry.get("sha256") and …` 的已知出口）+ `:187-189`（D6 不收紧） | 已落库 |
| K8 | `design.md:77-104`（探针原始输出 + 证据等级）+ `tasks.md:41-46`（3.0） | 已落库 |
| L1 | `tasks.md:79-84`（`⚠️ 时序是承重的，别调换`）+ `:86`（先改默认值）→ `:124`（再建 tag）+ `:125-126`（6.3 必须同一提交） | 已落库 |
| L2 | `docs/gate.md:100-110`（两步 + 旧 CLI 的冲突原文 + 「别去删 policy」）、`README.md:191-201` | 已落库 |
| L3 | `tests/test_gate_workflow.py:466-480`（`test_witnessloop_ref_input_default_is_empty`，断言 `default == ""`） | 已落库 |
| L4 | `spec.md:120-126`（Scenario）+ `initcmd.py:468-477`（`handled` 文案）+ `tests/test_init_gate_ref.py:233-261` | 已落库 |
| L5 | `spec.md:106-111`（`--dry-run`）、`:113-118`（台账无 caller 条目）两条 Scenario 都在 | 已落库 |
| L6 | `design.md:224`（R2 表两类仓）、`docs/gate.md:119-124`、`tasks.md:128-132` | 已落库 |
| M1 | `tests/test_init_gate_ref.py:28`（`NEW_REF = …@v9.9.9`）+ `:46-48`（`test_new_ref_does_not_collide_with_the_factory_default`）+ `tasks.md:95-98` | 已落库 |
| M2 | `docs/gate.md:222-227`（落盘名 / 覆盖陷阱 / 两条落法）、`:43-45`、`tasks.md:71-77`、`:16-19` | 已落库 |
| M3 | `tasks.md:114-119`（`head_sha 之后只允许证据文件` + 正确顺序） | 已落库 |
| M4 | `docs/gate.md:91-99`（①′ 命令）与 `README.md:194`；钉子 `tests/test_docs.py:286-300` | 已落库 |
| N1 | `tests/test_init_gate_ref.py:297-328`（补条目 + 插在 `self` 之前 + 随后幂等 + `uninit` 真能回滚） | 已落库 |
| N2 | `initcmd.py:277-279`、`:290-291`（不再自称「其余文件无改动」）+ 钉子 `test_rewrite_and_a_tests_write_do_not_contradict_each_other`（`test_init_gate_ref.py:75-88`） | 已落库 |
| N3 | 三处：`docs/gate.md:517-520`、`design.md:228`、`tests/test_gate_workflow.py:278-286`（`不在测试里硬编 "v1"`） | 已落库 |
| P1 | `initcmd.py:173-174`（先判数组）+ `:191-213`（不再兜）+ `:400-411`（受控诊断退 1）+ 钉子 `test_a_malformed_ledger_is_loud_and_never_rebuilt` | 已落库 |
| T1 | `tests/test_gate_workflow.py:532-549`（钉来源 + run 里不得再出现该输入 + uvx 用的就是该变量） | 已落库 |
| R6-D1 序 | `gate.yml:34-45`（①–⑤ 逐条）+ `tests/test_gate_workflow.py:508-521` | 已落库 |
| R6-recipe 序 | `tests/test_docs.py:286-300`（`docs/gate.md` 与 `README.md` 两处都钉） | 已落库 |

**额外复算（可复算的一律复算）**：

1. `tasks.md:86-98` 的 6.1 字面清单（items 1–3：`constants.DEFAULT_GATE_REF` → `@v1.7.0`、
   `gate.yml` 的 `WL_FALLBACK_REF` → `v1.7.0`、`test_caller_ref_matches_this_repo` 的 `== …@v1`）
   我在快照里照做 ⇒ **`681 passed`**（`tasks.md:88` 记的 `673 passed` 是当时的条数，
   属**计数**类差异，不计入必须修改项）。
   **反证**：同一张清单**只改 defaults 而不改 `WL_FALLBACK_REF`** 会红（`test_resolve_constants_match_the_single_source`），
   所以「这几处必须一起改」这条成立。
2. `git diff --stat v1..HEAD -- .github/workflows/gate.yml` 现在 **不为空**（85 insertions / 3 deletions）。
   `design.md:172` 的括号里写着它「**为空**」——那是实现落地**之前**测的，属**过时证据句**
   （结论「本 PR 不动 caller 的目标 ref 不存在」不受影响，见「未验证项」末条）。
3. `git show v1:.github/workflows/gate.yml` 里 `witnessloop-ref.default` 是 **`"v1"`**（第 23 行）
   ⇒ `design.md:172` 的「v1 那份是改动前的文件」成立。

### 判据① 新证伪项（4 条，全部「变异 ⇒ 681 全绿」）

| # | 变异（在快照里做） | 原始输出 | 为什么这是证伪而不是措辞 |
|---|---|---|---|
| **U1** | `gate.yml:109` 的 `echo "::notice::witnessloop 包 ref = $REF（来源：$WHY）"` 改成 `… = $REF"`（**删掉「来源」那一半**） | `681 passed in 38.55s` | `spec.md:56-58` 的 Scenario **Then 明写**「SHALL 有一行明确写出本次使用的 witnessloop ref **及其来源**（显式传入 / `job.workflow_sha` / 兜底 / fail-closed）」；`spec.md:35` 又写「日志 SHALL 说明 ref 来自「调用方显式传入」」。全仓**只有** `::notice::` 这个子串被人读（`tests/test_gate_workflow.py:367`、`:382`），`WHY` 的**任何取值**都没被断言过（`grep -rn "调用方显式传入\|来源：" tests/` 只命中一条**注释**，`:470`） |
| **U2** | `gate.yml:100` 的 `REF="$WL_FALLBACK_REF"` 改成 `REF="v1"`（**脚本不再读它自己声明的兜底常量**） | `681 passed in 37.78s` | Q1 裁定的原话是「`WL_FALLBACK_REF` 与 `DEFAULT_GATE_REF` 的 ref 部分**同源**（**由 `test_resolve_constants_match_the_single_source` 钉住**）」（`design.md:389-390`、`tasks.md:91-93`）。那条测试（`tests/test_gate_workflow.py:349-355`）**只比对 env 字面量**，没钉「脚本真的读它」——**文档把它写成了已验证**。加固：`!= "$WL_REPO_SLUG"` 换成 `!= "Xingkai98/witnessloop"` **且**把 warning 的成因文案整段换成 `"foreign"`，同样 681 全绿 |
| **U3** | `checkcmd.py:87-90` 的自报行把两值**对调**：`requested_revision={commit}`、`commit_id={revision}` | `681 passed in 37.79s` | 这是 Q4 唯一的用户可见产物，且**只有在真 `uvx` 装包时两值才非空**——而全部测试环境是**源码直跑**（两值恒 `<未知>`），所以两个**标签**被钉、两个**值**的绑定没被钉。后果：真 CI 里 `requested_revision` 会打出 resolved sha，而 `docs/gate.md:92-97` 的 ①′ recipe 明写 `requested_revision=<你刚升的 ref>`（`:96`）⇒ 用户会**误判「CLI 没升成」**；issue #30 的验收证据（resolved sha）也正好被搅乱 |
| **U4** | 在 `checkcmd.py:99` 的 `_report_package_source()` **之前**插一行 `print("check：启动（本行是新增的）")` | `681 passed in 35.57s` | `docs/gate.md:92-96` 与 `README.md:194` 的 ①′ 是 `witnessloop check --root . 2>/dev/null \| head -1`，**承重前提是「这一行是 stdout 第一行」**（我实跑确认今天成立：`check：本包来源（自报，尽力而为）：…` 就是第一行）。但没有任何钉子钉「它必须是第一行」——对比 `gate.yml` 的解析 step 有 `test_resolve_step_is_the_first_step`（`tests/test_gate_workflow.py:324-327`），`check` 侧缺同款 |

**U2 的诚实降级说明**（别把它说大）：我把 6.1 的改动 + `REF="v1"` 一起做，得到
`4 failed, 677 passed`（`test_resolve_fails_closed_on_a_malformed_workflow_refs` /
`test_repository_mismatch_does_not_fall_through_to_workflow_ref` 等）⇒ **U2 会在 post-merge 那一步被
现有的兄弟测试抓回来**，所以它不是永久黑洞；它今天全绿、且**文档把它写成「已由某测试钉住」**，
这两点才是必须修的实质。

## 未验证项

以下**我做不到**，按题面规则**不计入必须修改项**（除非它们被文档写成了已验证——U2 就属这一条，
已单列）：

1. **真 CI 的 `job.*` 取值**：`job.workflow_sha` / `workflow_repository` / `workflow_ref` 在真
   GitHub 上的实际语义。本工作区无法跑跨仓真 CI。
2. **Q1 探针（run `38853369550`，`design.md:77-104`）的原始输出是二手、单一来源、不可复现**
   ——文档自己已如实标注证据等级（`design.md:97-104`），我确认那段标注**确实写在正文里**，
   且结论另有官方 contexts 文档依据 + R2 的机制旁证。**我没有独立验证它**。
3. **GHES / 同 owner fork / 自建 runner** 面：`job.*` 不可用时的行为、uv 版本差异。
4. **`pip install git+…` 是否同样落 PEP 610 的 `vcs_info`**（只实测过 uv 0.13.1 的 `uvx`）。
5. **`v1.7.0` 尚不存在**：6.7 的验收命令、`README.md` 里指向 `@v1.7.0` 的 recipe，
   今天都指向一个不存在的 ref——文档已就地写明（`README.md:206-207`、`tasks.md:144`）。
6. **issue #30 的数字**（`v1` ⇒ ✗10 / `main` ⇒ ✗1）来自该 issue 正文，未复算。
7. **`refs/pull/N/merge` 的 uv 行为**：文档只说「不是稳定的可安装 ref」、不声称必然安装失败
   （`spec.md:42-43`）——这个谨慎措辞我认，但也**未实测**。
8. **过时证据句**（低危、非必须修改）：`design.md:172` 的
   `git diff --stat v1..HEAD -- .github/workflows/gate.yml` **为空**，以及 `design.md:263`
   的「`src/` 差 6 文件 +922/−96」——我复算现为 **非空**（85+/3−）与 **8 files +1135/−101**。
   两处都是「实现落地前测的」，结论（本 PR 不动 caller 的目标 ref）不受影响；
   属**时间点依赖的测量**，不是可复现的行为断言。建议把这两句改成不带数字的表述。

## 必须修改项

- **U1**（`gate.yml:109` / `spec.md:56-58`、`:35`）：`::notice::` 的「来源」是 spec 明写的 Then
  子句，却**零钉子**（删掉它 681 全绿）。加固：从 `gate.yml` 抽出解析 step 真跑（沿用
  `tests/test_gate_workflow.py` 的 `_run_resolve`），在**四条分支**上各断言 notice 里的来源字样
  （显式传入 / `job.workflow_sha` / 兜底 ref / fail-closed），并顺带钉 `::warning::` 里
  **成因文案非空**（我实测把它整段换成 `"foreign"` 也全绿）。
- **U2**（`gate.yml:100` + `design.md:389-390` / `tasks.md:91-93`）：脚本**必须读**自己声明的兜底常量。
  加固：`_run_resolve` 里**传入一个与 `REPO_SLUG`/`v1` 都不同的 `WL_FALLBACK_REF`**（如 `"v0.0.1"`）
  并断言输出就是它——那样 `REF="v1"` 这种硬编码当场红；同时把文档里「由
  `test_resolve_constants_match_the_single_source` 钉住」这句话改成指向**读点**的钉子。
- **U3**（`checkcmd.py:87-91`）：自报行的**两个值**要与两个标签绑定。加固：把
  `_report_package_source()` 的输出格式抽成可测的纯函数（或在测试里 monkeypatch
  `installed_vcs_ref` 返回 `("v1", "ae9925…")`），断言整行**逐字**等于预期——只钉两个子串
  （`requested_revision=` / `commit_id=`）挡不住对调。
- **U4**（`checkcmd.py:99`）：①′ recipe 的承重前提「自报行是 stdout 第一行」应有钉子。
  加固：一条**行为级**断言（如 `cli("check", …)` 的 `out.splitlines()[0]` 就是自报行），
  或退一步——把 `docs/gate.md`/`README.md` 的 recipe 从 `head -1` 改成 `grep -m1 requested_revision`
  并对齐文档（那样 position 不再是承重前提）。

## Open Questions

1. **U3 的修法该走哪条**：抽纯函数（规格面更干净、但多一处间接）vs monkeypatch `installed_vcs_ref`
   （更贴近用户可见面、但测试要装 monkeypatch 钩子）？我倾向前者，理由与 P1 同：一个函数、一处判定。
2. **`::notice::` 的「来源」要不要算「措辞」**？我判**不算**：它不是同一句话的换词，而是一个
   **独立可观测**（哪条规则生效），且整个 change 的题眼就是「不静默」。若主 session 采纳相反读法，
   U1 应降为低危观察——**但那不改变本轮结论**（U3/U4 是纯行为面）。
3. **`_report_package_source()` 在 `argparse` 用法错误（EXIT_USAGE）时不会打**（`cli` 在 `run()`
   之前就退 2）。spec 的 Scenario 只覆盖「装好后正常运行」，所以我**不算它是缺口**；
   但若将来有人拿 ①′ 当「CLI 版本自检」，用法错误路径会静默不给信号。
4. **本仓 `reviews/` 已有 8 份报告**（含本轮）：`tasks.md:71-77` 的 stage 名清单现在需要
   `-r2…-r7`。处约定（`docs/gate.md:222-227`）没被违反，只是 5.2 的举例清单已过时——**措辞类**，不计入。

## 收敛结论

**不收敛。**

- **判据②（前六轮的「必须修改项」全部已落库）：满足。** K1–K8 / L1–L6 / M1–M4 / N1–N3 / P1 / T1
  与 R6 的另两条（D1 判定顺序、recipe 顺序）我**逐条去正文与代码里核过**（落点见上表，不读 §7.9
  自述表），全部落在正文/实现/钉子处；6.1 的字面清单我**实跑复算**为 `681 passed`。
- **判据①（本轮没有新的可证伪项）：不满足。** 4 条新证伪项（U1–U4），每条都是
  「在快照里变异 ⇒ 全量 681 全绿」的**原始输出**在案，且都在本 change 的分内面
  （U1/U2 在新增的解析 step，U3/U4 在新增的自报面）。
- 已知**刻意不修**的三条（`docs/gate.md` 只改编号时不再变红、`_set_ledger_gate_ref` 的纵深防御、
  dry-run 的 `print`）我**同意**它们是「无行为后果 / 不可达」——**不列**为必须修改项。
- 另：题面点名让我看一眼的新面里，**`--gate-ref` + `--no-tests`**、**`--policy` + `--gate-ref`
  时 `desired_files()` 用哪份 doc**、**`check` 自报在重定向下丢不丢**、**`gate.yml` 的
  `permissions:` / `on:` / job 名**四条**我试过、都**没找到可证伪项**：
  - `--no-tests` 只改 `policy_doc`（`initcmd.py:250-253`）⇒ 两条轴各自参与退出码，与
    `spec.md:120-126` 的组合语义同口径；`--policy` 就是 `desired_files()` 用的那份 doc
    （`initcmd.py:260`），符合文档。
  - 重定向/管道：`flush=True`（`checkcmd.py:90`）+ 实跑 `… 2>/dev/null | head -1` ⇒ 那一行正常输出
    （`head -1` 之后的 `BrokenPipeError` 是**先于**本 change 的既有形态：任何第二个 stdout 行都会触发，
    且 recipe 已 `2>/dev/null` 且不看退出码）。
  - `permissions: contents: read` / `on: workflow_call`（两个输入）/ 唯一的 `check` job 都没被本
    change 碰到（`gate.yml:11-30`，另有 `tests/test_gate_workflow.py:228-232` 钉 job 名与 caller 的 `gate:`）。

---

## 处置（主 session 在 R7 之后追加，非审阅者原文）

> 本报告判定**不收敛**（判据②满足、①不满足），基准 `9bf5c8c`。**U1–U4 全部已落库**，
> 每条都用「改回旧行为 ⇒ 该变异现在变红」复核过：

- **U1（`（来源：$WHY）` 删掉全绿）**：新增 `test_resolve_notice_names_the_source_of_the_ref`
  —— 三条分支各自的**来源文案**都被断言（显式 / `job.workflow_sha` / fail-closed）。
- **U2（脚本把 `REF="$WL_FALLBACK_REF"` 硬编成 `"v1"` 全绿）**：两条钉子
  —— 行为侧 `test_resolve_reads_the_fallback_ref_from_its_env`（把兜底 ref 换成哨兵 `v9.9.9`，
  fail-closed 的输出必须跟着变）+ 文本侧 `test_resolve_script_reads_both_constants_from_the_environment`
  （`run` 里必须出现两个变量的**读**）。你那句「那条同源测试只比对 **env 字面量**」正是缺口本体。
- **U3（自报行两值对调全绿）**：新增 `test_the_report_line_binds_each_value_to_the_right_label`
  —— 注入 `("REF-X","COMMIT-Y")` 后断言 `requested_revision=REF-X` 与 `commit_id=COMMIT-Y` 各自绑对。
  你点出的**真 CI 后果**（两值都非空 ⇒ 用户照 ①′ 会误判「CLI 没升成」）是这条的价值所在。
- **U4（自报行前插一行 stdout 全绿）**：新增 `test_the_report_line_is_the_first_thing_check_prints`
  —— 钉住「①′ recipe 的承重前提：自报行是 `check` 的第一行」。

**你登记的两条过时证据句**（`design.md` 的「diff 为空」与「6 文件 +922/−96」）**已就地标注测量时点**：
它们是**本 change 之前**的数（本 change 自己改了 `gate.yml` / `src`），结论不受影响；
同时把正文里那个具体数字去掉了，只留「落后数十个提交」。

**你试过但没找到可证伪项的四条**（`--gate-ref`+`--no-tests`、`--policy`+`--gate-ref` 的 doc 选择、
重定向下自报丢不丢、`gate.yml` 的 `permissions`/`on`/job 名）：接受，不追。

**下一轮（R8）**：树在被审 revision 上**冻结**（本轮之后只追加 `reviews/` 证据与 §7.9 小节）。
若你在该冻结树上仍找到**行为缺陷**（不是「某个变异没被钉」），那必须落库；
若只剩「再补一条钉子」类的面，请在收敛结论里**如实说明它是哪一类**，不要与行为缺陷混计。
