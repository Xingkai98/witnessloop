# Grill（对抗轮 R5）：gate-ref-pins-package —— 独立零记忆证伪

## Reviewer

我是**独立零记忆**的对抗验证者（本对话不携带该 change 的任何历史）：`proposal.md` / `design.md` /
`tasks.md` / `specs/gate-ref-pinning/spec.md` 与四份 review（R1 `grill-adversarial.md`、R2 `-r2`、
R3 `-r3`、R4 `-r4`）里的「实测」「文件:行号」「已落库」「已收敛」「零命中」一律当**待验证断言**，
可复算的一律复算，**目标是证伪结论本身**。

**基准 revision（本仓在本轮审阅期间被并发移动了两次，这一节必须读）**

| 时刻 | HEAD | 说明 |
|---|---|---|
| 我开始时 | `f045524` | 我读 `design.md` / `tasks.md` / `spec.md` / 源码、并做**全部**变异实验的树 |
| 审阅中 | `5384c6e` | 主 session 落库：`docs/gate.md §7.1` 补两条边界（**修好 §1.2 → §7.1 的悬空引用**）+ `checkcmd` 注释 |
| 审阅中 | `1a0f9a2` | 主 session 落库：把 `handled` 那句的**两面**都钉住 + N2 的修复补钉子（commit message 自述「对抗轮 R5 实测」） |

**本报告的行号与 blob 一律以 `1a0f9a2` 为准**（= 我收尾时逐条复核的那棵树）。凡在 `f045524` 上做的实验
（变异、边界矩阵、grep），都单独标注；两条并发提交**只改文档措辞与测试**（`5384c6e`：`docs/gate.md` +8 行、
`checkcmd.py` +3 行注释；`1a0f9a2`：`tests/test_init_gate_ref.py` +21/−2），**`src/` 的实现逻辑一行未动**
（`initcmd.py` blob 两棵树上都是 `607910f0…`）⇒ 我在 `f045524` 上测到的**实现行为**在 `1a0f9a2` 上逐条成立，
我已在当前树重跑关键实验确认。

| 文件 | blob（`1a0f9a2`） |
|---|---|
| `HEAD` | `1a0f9a2dfa2a4666094dc5e879f7caa6c4195fed` |
| `openspec/changes/gate-ref-pins-package/design.md` | `ee755aa3ef11…` |
| `…/tasks.md` | `98eea0040a4d…` |
| `…/specs/gate-ref-pinning/spec.md` | `de8cc896c93e…` |
| `…/proposal.md` | `903714c3fc90…` |
| `src/witnessloop/initcmd.py` | `607910f0d6ad…` |
| `src/witnessloop/checkcmd.py` | `e12db4d94a1d…` |
| `src/witnessloop/constants.py` | `0a64184d5435…` |
| `.github/workflows/gate.yml` | `a9b86014d067…` |
| `docs/gate.md` | `f79b48f8eaa2…` |
| `README.md` / `docs/design.md` | `700ade12d4ab…` / `dcbc79bd8fcd…` |
| `tests/test_init_gate_ref.py` | `3f267587f58d…` |
| `tests/test_gate_workflow.py` | `6d68b0a700b0…` |
| `tests/test_docs.py` | `c3516c31b828…` |
| `tests/test_check_package_ref.py` | `b9e2f2f6b03a…` |

**快照方式（上一轮的事故教训已遵守）**：一律 `git archive HEAD | tar -x -C /tmp/adv5/base2`
（**不用** `cp -a`——本目录是 linked worktree，`.git` 是指针文件，`cp -a` 会把指针带过去，
在副本里 commit 等于在真仓 commit）。所有实验在 `/tmp/adv5/`。**真仓我一个字节都没改**
（除本报告）；收尾时 `git status --porcelain` 为空、`HEAD = 1a0f9a2`。

**实际跑了（命令 + 原始输出要点）**

1. **基线**：`1a0f9a2` 导出树 ⇒ `PYTHONPATH=src python3 -m pytest -q` ⇒ **675 passed**
   （`f045524` 上是 674；`1a0f9a2` 新增 `test_rewrite_and_a_tests_write_do_not_contradict_each_other`）。
2. **N1 的钉子真会红吗**（改 `_set_ledger_gate_ref` 的补条目分支）：
   变异 A `entries.insert(at, …)` → `entries.append(…)` ⇒ **1 failed, 673 passed**，
   红的正是 `test_ledger_without_a_caller_entry_is_repaired`；
   变异 B 把整条补条目分支改成 `pass` ⇒ 同一条红。**两次都只有这一条红** ⇒ 该分支**仅**由这条钉子覆盖。→ **有效**。
3. **N2 的修复**：`init --root <已接入仓> --gate-ref …@v9.9.9 --test-command "uv run pytest -q"` ⇒ 收尾话
   `init：已接入 witnessloop（已写入测试执行点，未 commit；.github/workflows/witnessloop.yml 与台账已改成 …@v9.9.9）。`
   ——**不再自称「其余文件无改动」**（`f045524` 上的自否已消）。→ **有效**。
4. **N3 的全仓活面**：`grep -rn "退 \`v1\`\|退回 \`v1\`\|退 v1\|吃 \`v1\`" src/ tests/ docs/ README.md .github/`
   ⇒ **exit 1（零命中）**；再放宽到 `吃 v1|退 v1|退到 v1|退回 v1|一直吃|永远是 v1|恒为 v1` 并加扫 `openspec/`
   ⇒ 只命中 **历史引文/审阅报告自身**（`reviews/grill-design.md:159`、`reviews/grill-adversarial*.md`、
   `reviews/grill-adversarial-r4.md` 与 `tasks.md:104` 的 grep 命令原文）。`docs/gate.md §7.1:519`、
   `design.md §4 R6:218`、`tests/test_gate_workflow.py:410` 三处**已改成「兜底 ref（= `DEFAULT_GATE_REF` 的 ref 部分；今天 = `v1`）」**。→ **零命中属实**。
5. **L3 的钉子踩**（把 `witnessloop-ref.default` 改回 `"v1"`）⇒ `test_witnessloop_ref_input_default_is_empty`
   **当场红**、其余 28 条绿。→ **有效**。
6. **`tasks.md §6.1` 的字面量族按字面模拟**（`constants.py` → `@v1.7.0`、`gate.yml:61` `WL_FALLBACK_REF` → `"v1.7.0"`、
   `tests/test_gate_workflow.py:59` 断言 → `@v1.7.0`）⇒ **674 passed**（`f045524` 上）。→ M1 的修法**闭环**。
7. **变异审计（本轮的主要手段）**，每条都在 `f045524` 导出树上跑全量或子集：
   | 变异 | 结果 | 该面是否被钉住 |
   |---|---|---|
   | 删掉 `check` 的 `_report_package_source()` 调用 | **3 failed** | ✅ |
   | 把「只在已接入分支」守卫（`if manifest_path.is_file()`）改成 `if True` | **175 failed** | ✅ |
   | `gate.yml` 的 `witnessloop-ref.default` → `"v1"` | **1 failed** | ✅ |
   | 删 4 个新文档字面量（`protected=False` / `刻意不修` / `先把 CLI 升上去` / `job.workflow_sha`） | 各 **1 failed** | ✅ |
   | **把 `handled` 的两条分支合成同一常量**（真跑也说「未落盘、不回滚」） | **674 passed** | ❌ **当时没钉住**（见 §C1） |
   | **把 N2 的 `note` 退回 `"其余文件无改动，未 commit"`** | **674 passed** | ❌ **当时没钉住**（见 §C2） |
8. **`sync_caller_gate_ref` 边界矩阵**（模拟仓，含台账损坏）：见 §D1 —— 其中一条**有实际后果**，见 §C3。
9. **`installed_vcs_ref` 的宽 `except`**：monkeypatch `importlib.metadata.distribution` 抛
   `KeyboardInterrupt` / `SystemExit` ⇒ **两者都照常传播**（`except Exception` 不兜 `BaseException`）。
10. **`gate.yml` 解析 step 交真 `sh` 跑**（env 照抄 step 的 `env:`）：GITHUB_OUTPUT 已设 ⇒ `EXIT=0` +
    `ref=abc123` + `::notice::`；**GITHUB_OUTPUT 未定义** ⇒ `EXIT=2`（`GITHUB_OUTPUT: parameter not set`）；
    指向不可写路径 ⇒ `EXIT=2`。见 §D3。
11. **本仓自证**：`check --root . --base origin/main --head HEAD` ⇒ **✗（4 项）**，全部「缺 manifest /
    缺 grill / 缺 grill-adversarial / 缺 building」类，与 caller / policy / 台账 / 解析面无关（5.1/5.2 尚未做）。
12. **测试独立性**：五个新/改的测试文件**逐个单跑**全绿；**文件级逆序**跑全量 ⇒ 674 passed；
    `grep` 确认没有测试写向真仓根（`REPO_ROOT` 只被 `read_text`）。→ 无互相依赖、无副作用。
13. **远端 tag / 分支**：`git ls-remote --tags origin` 最大 = **`v1.6.0`**（`v1.6.0^{}` = `ae99256…`）
    ⇒ 不存在 `v1.7.0`；远端**无** `probe/*`，本地**仍留** `probe/workflow-ref` ⇒ `design.md §2 D1` 措辞属实。

**没能复算的**：见「未验证项」（真 CI 的 `job.*` 运行期取值与 Q1 探针原始输出、GHES/fork/自建 runner、
真 `uvx …@v1.7.0`、issue #30 的两组数字、`refs/pull/N/merge` 的可安装性）。

---

## 对抗结论

### A 判据②：前四轮「必须修改项」逐条落库复核（去正文/代码里核，**不核** §7.9 的自述表）

**R1 的 K1–K8 —— 全部落进正文/实现 ✅**

| # | 要求 | 我在正文/代码里核到的落点（`1a0f9a2`） |
|---|---|---|
| K1 | 删/改「包无法自报 ref」 | `design.md §2 D3`（`:140-154`，明写「R1 K1 订正（原稿此处为假）」）+ `spec.md` 的「`check` SHALL 自报」Requirement（`:60-82`）。全仓 grep `无法报告\|没有 ref 信息\|无法自报` ⇒ 只剩**标注为被证伪的引文**（`design.md:140,249`、`spec.md:71`、`tests/test_check_package_ref.py:3`）⇒ 无残留的**现行**断言 |
| K2 | 改「没有任何提示」 | `proposal.md:19-29` 整段改写（标题即「…是**假**的」）；唯一的「没有任何提示」字样在标题里、且是否定式（grep 复核） |
| K3 | 「永久死锁」降级 | `design.md §2 D2`（`:124-129`「**响亮、可恢复的分叉态**」+ 三条恢复路径 + `check` 不读台账）——在**正文**，不在表里 |
| K4 | 自证行在 (A) 下矛盾 | `design.md §2 D4`（`:156-171`，本 PR **不做**本仓迁移） |
| K5 | 「47 个提交」计数 | `design.md` 正文已去计数；我独立复算 `git rev-list --count v1..origin/main` = **47**（`v1..HEAD` = 59）⇒ K5 行「取决于测量哪个 ref」成立 |
| K6 | 补 `docs/design.md:56,73` | `:56` 保留**历史引文** + 指向 `docs/gate.md §1.2`；`:73` 已改 `@<ref>`（两处实读） |
| K7 | 登记 `sha256: null` 出口 | `design.md §2 D2` 末条（`:130-134`）+ `D6`（`:177-179`，明确**不**收紧） |
| K8 | 探针落点/清理 | `design.md §2 D1`（`:84-97`：原始输出即落点、**远端已清理、本地仍留**）+ `tasks.md 3.0`（`:41-46`）；我复核远端无 `probe/*`、本地仍在 ⇒ 措辞与事实一致 |

**R2 的 L1–L6 —— 全部落库 ✅**

| # | 要求 | 落点 |
|---|---|---|
| L1 | post-merge 时序反过来 | `tasks.md:86`（6.1 **先**改默认值）在 `:117`（6.2 **再** tag「含 6.1 改动」的 main）**之前**；`:118-119`（6.3）把 `README.md:20` 的新值与 tag 放**同一个提交**；`:127-141`（6.7）给了可复算验收命令。**顺序对** |
| L2 | recipe 补「先升 CLI」 | `docs/gate.md:82-110`（两步 + 旧 CLI 的 EXIT=1 与误导文案 + 「别去删 policy」）+ `README.md:191-206` |
| L3 | `inputs.witnessloop-ref.default == ""` 的钉子 | `tests/test_gate_workflow.py:466-479`；**我实踩：改回 `"v1"` ⇒ 该条红**（Reviewer 5） |
| L4 | 写死 `--gate-ref` × 冲突 `--policy` | `spec.md:120-126` 的 Scenario + `initcmd.py:301-305`（`handled`）+ `tests/test_init_gate_ref.py:233-262`；实跑文案出现 |
| L5 | spec 补两条 Scenario | `spec.md:106-111`（`--dry-run`）、`:113-118`（台账缺 caller 条目） |
| L6 | 点名**两类**仓 | `design.md §4 R2`（`:214`）+ `docs/gate.md:119-122` + `tasks.md 6.5`（`:121-125`）——三处都在 |

**R3 的 M1–M4 —— 全部落库且有效 ✅**

- **M1**：`tests/test_init_gate_ref.py:28` `NEW_REF = …@v9.9.9` + `:46-48`
  `test_new_ref_does_not_collide_with_the_factory_default`（把**前提**钉住）；`tasks.md:95-98` 的 ④ 写清「没有第 4 处要改，
  但有一条前提要保住」。**我按字面模拟 6.1 的改动 ⇒ 674 passed**（Reviewer 6）⇒「一处改不动」的病已治好。
- **M2**：`docs/gate.md §3`（`:210-230`）写明「**每一份报告各配一份 manifest**」+ `reviews/<stage>.manifest.json`
  的**同名覆盖**陷阱 + 两条可选落法；`tasks.md 5.2`（`:71-77`）与 `0.4`（`:16-19`）各补一步。
  我复核 `openspec/changes/archive-arrival-recognition/rounds/` **确实存在**（先例属实），
  本 change 的 `reviews/` 下无 `rounds/`、无 manifest ⇒「未混用」成立。
- **M3**：`tasks.md:107-112` 改成「`head_sha` 之后**只允许证据文件**」+ 正确顺序（先落代码 → 提交 → 再重建 manifest），
  与 `contract.py` 的 revision 绑定口径一致。
- **M4**：`docs/gate.md §1.2`（`:90-100`）与 `README.md`（`:196-204`）都补了 ①′ 与「旧包**没有**这一行」；
  我复核自报行确在 `run()` 第一句（`checkcmd.py:99`）⇒ 在**未接入**目录里也打（`:109-115` 的 `EXIT_NOT_ONBOARDED` 分支之前）。

**R4 的 N1–N3 —— 全部落库且有效 ✅**

- **N1**：`tests/test_init_gate_ref.py:297-325` `test_ledger_without_a_caller_entry_is_repaired`；**我变异验证**：
  破坏补条目分支（`append` 或 `pass`）⇒ 该条红、**其余 673 条绿**（Reviewer 2）⇒ 钉子**有效**且该分支**仅**它覆盖。
- **N2**：`initcmd.py:271-285` 的 `note` 不再自称「其余文件无改动」；**实跑确认**输出自洽（Reviewer 3）。
- **N3**：三处漏网已改；全仓活面 grep **零命中**（Reviewer 4）。`tasks.md:99-104` 的自查面已从
  「`docs/` 与 `README.md`」扩到 `src/ tests/ docs/ README.md .github/`（但**其检出能力仍有两处缺口**，见 §E3）。

⇒ **判据②成立。**

### B R4「## 处置」以外的独立核查

R4 的报告末尾有主 session 追加的「处置」，我**不采信其自述**，逐条去树里核：N1/N2/N3 三条
与它写的一致（见 §A 末）；R4 关于自己误提交 `da3db40` 的还原声明——我复核 `git log --oneline`
里**无** `da3db40`、本 change 目录下 `find -name "*.manifest.json"` **零命中**、`git status` 干净
⇒ **净残留为零**属实。

### C 判据①：本轮新发现的可证伪项

**C1（非措辞 · 已被并发提交 `1a0f9a2` 落库）`handled` 那句的 dry-run 分叉**只被钉住了一半。**

- **实测（`f045524`）**：把 `initcmd.py:301-305` 的两条分支合成**同一个常量**
  （`… 已按显式 \`--gate-ref\` 处理（**未落盘、不回滚**）`）⇒ **全量 674 passed**；
  而**真跑**时这句话是**假的**——实跑输出：
  ```
  init：注意——.github/workflows/witnessloop.yml 已按显式 `--gate-ref` 处理（**未落盘、不回滚**）；下面报的是**别的**文件：
    盘上 caller 的 uses 行：    uses: Xingkai98/witnessloop/.github/workflows/gate.yml@v9.9.9
    台账 gate_ref：            Xingkai98/witnessloop/.github/workflows/gate.yml@v9.9.9
  ```
  ⇒ **一边改写 caller + 台账、一边说「未落盘」**，且**没有任何测试能发现**。
- **被证伪的断言有三处**：`spec.md:124`（Session「输出 SHALL **点明**「caller 已落盘、不回滚」」）、
  `initcmd.py:299-300`（「这句话**必须**随 dry-run 分叉」）、`tests/test_init_gate_ref.py` 的
  `test_dry_run_must_not_claim_it_wrote_anything` docstring（「**上一条**钉「真跑时要点明已落盘、不回滚」」）。
  根因是上一条用例当时只断言 `"不回滚" in err`——**「不回滚」在两种说法里都出现**，所以常量串两边都过。
- **现状**：`1a0f9a2` 已补 `assert "已落盘" in err` / `assert "未落盘" not in err`
  （`tests/test_init_gate_ref.py:257-261`）。**我在当前树上重跑同一变异 ⇒ 1 failed** ⇒ 修法有效。

**C2（非措辞 · 已被并发提交 `1a0f9a2` 落库）R4 的 N2 修复当时**没有任何测试**。**

- **实测（`f045524`）**：把 `initcmd.py:285` 的 `note = "已写入测试执行点，未 commit"`
  退回 `"其余文件无改动，未 commit"`（= 恢复 N2 那条自相矛盾）⇒ **全量 674 passed**。
  ⇒ R4 判它「文案自相矛盾」的修复**只落在实现里、没有回归钉子**。
- **现状**：`1a0f9a2` 已加 `test_rewrite_and_a_tests_write_do_not_contradict_each_other`
  （`tests/test_init_gate_ref.py:75-89`，断言 `"其余文件无改动" not in out`）。**我在当前树上重跑同一变异 ⇒ 1 failed** ⇒ 修法有效。

> **C1/C2 的归属说明（如实披露，供下一轮复核）**：这两条是我在本会话里**独立**用变异审计发现的
> （`f045524` 树、全量 `674 passed`），但在**我写报告之前**，主 session 的 `1a0f9a2`
> 已把它们落库，且 commit message 自述「**对抗轮 R5 实测**」。我无法判定那是**本会话**的中间结论
> 被并发消费，还是**另一个同名 R5 实例**——与 R3 当年的情形同类。⇒ 我按「**本轮确实发现了新的可证伪项**」
> 记明（口径与 R3/R4 在同类并发情形下保持一致），但因它们**已在被审 revision 上修掉**，
> 它们**不构成本轮的必须修改项**。

**C3（非措辞 · 仍存在）`_set_ledger_gate_ref` 会**静默丢弃**台账里除 caller 之外的条目，并报成功。**

- **证据（`f045524` 与 `1a0f9a2` 上**同**结果；`initcmd.py` 两棵树上 blob 相同）**：
  `initcmd.py:189-192`：
  ```python
  entries = manifest.get("created_files")
  if not isinstance(entries, list):
      entries = []
      manifest["created_files"] = entries
  ```
  ⇒ `created_files` **可解析但不是 list**（键缺失 / 是 dict / 是字符串）时，**旧内容被整段丢掉**，
  再补一条 caller 条目 + 同步 `gate_ref`，然后 `:179` 把台账写回。实跑（键缺失与 dict 两种）：
  ```
  init：已接入 witnessloop（.github/workflows/witnessloop.yml 与台账已改成 …@v9.9.9）。   EXIT=0
  台账条目： ['.github/workflows/witnessloop.yml']          ← policy 与 self 两条**没了**
  uninit：已回滚 witnessloop 接入：  - .github/workflows/witnessloop.yml                  EXIT=0
  剩: init-manifest.json  剩: policy.json                  ← 一半没回滚，而它报了成功
  ```
- **为什么这是缺陷而不是「坏输入活该」**：同一个函数对**JSON 层**的损坏是 **fail-closed** 的
  （`initcmd.py:162-165`：解析失败 ⇒ `return None` ⇒ 交给 `_already_initialized` 报一手诊断）；
  对**形状层**的损坏却**静默重建**。同一份「坏台账」在两条相邻分支下得到相反的处置（诊断 vs 静默破坏），
  而破坏那一条**只报成功**。下游后果是 `uninitcmd.py:3-5` 自己写的契约（「任一文件被改过 → 整批拒绝删除
  并报 diff（**避免留下半删状态**）」）在这条路径上不成立：它 `EXIT=0` 报「已回滚」，而 `policy.json` /
  `init-manifest.json` 留在盘上（仓停在「半接入」态，`check` 仍把 policy 当作已接入）。
- **可达性如实说明**：触发前提是**仓外的台账损坏**（工具自己生成的台账恒为 list，
  `build_manifest` 见 `initcmd.py:97-113`）⇒ 严重度**低**；但它落在本 change **新引入**的代码里
  （`_set_ledger_gate_ref` 与 `sync_caller_gate_ref` 都由 `5cc56b4` 首次引入），
  且与 spec 的 Scenario（「台账里**没有 caller 那一条**」= list 存在、只缺一条）是**相邻但不同**的输入。
  ⇒ 记为 **P1**，见「必须修改项」。

### D 逐条报告题面点名的「主动找」的面

**D1 `sync_caller_gate_ref` 的边界矩阵（`f045524` 模拟仓实测）**

| 输入 | 结果 | 判定 |
|---|---|---|
| 台账 JSON 坏（不可解析） | `return None` ⇒ `_already_initialized` 报「无法解析」EXIT=1 | ✅ fail-closed |
| `created_files` **键缺失** | **静默重建**（丢掉 policy 条目）EXIT=0 | ❌ 见 **C3/P1** |
| `created_files` 是 **dict** | 同上（丢掉 dict 里的条目） | ❌ 同上 |
| caller 条目带 `self: true`（同路径） | for-else 不匹配 ⇒ **插出第二条同路径条目**（台账出现重复 path） | ⚠️ 低危（要求手工构造 `self:true` 的 caller 条目） |
| 台账里 caller 路径**大小写不同** | 同上 ⇒ **插出第二条同路径条目** | ⚠️ 低危（台账被手改） |
| caller 是**符号链接** | `path.is_file()` 跟随链接 ⇒ **写穿**到目标文件、链接保留；台账记新内容的 sha | ⚠️ 低危（`init` 从不建链接） |
| 盘上没有 caller | `return None` ⇒ 漂移分支响亮报「缺失」EXIT=1 | ✅（`test_missing_caller_is_not_resurrected`） |
| 台账 `gate_ref` 已等于目标 | `return None` ⇒ 幂等 EXIT=0 | ✅（`test_same_ref_is_a_noop`） |

> 后三条都要求**仓外篡改**，我按纪律只登记为低危观察（不以它们判收敛）。
> 另记一条**先于本 change 存在**的相邻行为：`initcmd.py:397` / `uninitcmd.py:42` 的
> `for entry in manifest.get("created_files", [])` 遇到**非 dict 条目**（如 `["a.md"]`）会
> `AttributeError` ⇒ 入口兜底成「内部错误」退 1。`v1` 树上的同一行存在（`git show v1:src/witnessloop/initcmd.py`
> 第 293 行同款）⇒ **不是本 change 的新项**，登记备查。

**D2 `checkcmd.installed_vcs_ref` 的宽 `except` —— 按题面追问「有没有把该失败的也吞掉」**

- `checkcmd.py:55-76`（`except` 在 `:65`）兜的是 **`Exception`**。我用 monkeypatch 让 `importlib.metadata.distribution`
  抛 `KeyboardInterrupt` / `SystemExit` ⇒ **两者都照常传播**（实测输出 `OK: KeyboardInterrupt 照常传播` /
  `OK: SystemExit 照常传播`）⇒ **没有**吞掉这两个「该传播的」。
- 它**确实**会把「读元数据时的真 bug」（如 API 变更导致的 `AttributeError`）收敛成 `<未知>`——
  但这是 spec 明写的取舍（`spec.md:66-67`「SHALL NOT 因此改变退出码」），`docs/gate.md §7.1:531-534`
  也已如实登记「按规格兜而不是按成因枚举」。⇒ **不是缺口**。

**D3 `gate.yml` 解析 step 在日志里对**接入方**够不够用 —— 三处都实测了**

- `::notice::`（`gate.yml:101`）：形态正确（`echo "::notice::…"`），在日志与 annotation 里都可见；
  且我复核它**在写入 `$GITHUB_OUTPUT` 之后**（`:100` → `:101`）⇒ 只有在写 output 失败时才会连 notice 一起丢。
- `set -eu` 下的行为：四个来自 `${{ }}` 的键都用 `${VAR:-}` 读（`:73-91`），
  `WL_REPO_SLUG` / `WL_FALLBACK_REF` 是 step 自带字面量（`:60-61`，恒存在）⇒ 稳健性成立；
  我实跑「四个键全部 undefined」⇒ `EXIT=0` + warning（与 `test_resolve_survives_undefined_env_vars` 一致）。
- **`GITHUB_OUTPUT` 缺省**：`:100` 的 `>> "$GITHUB_OUTPUT"` **没有**用 `${VAR:-}` 兜，
  这是全脚本**唯一**一处未兜的变量读取，而 `:69-72` 的注释与 `tests/test_gate_workflow.py:483-487`
  的 docstring 都写着「**一律**用 `${VAR:-}` 读」。实测：`GITHUB_OUTPUT` **未定义** ⇒
  `step.sh: 38: GITHUB_OUTPUT: parameter not set`、**EXIT=2**（= 第一个 step 就红）；
  指向不可写路径 ⇒ 同样 EXIT=2。
  现有钉子 `test_resolve_survives_undefined_env_vars` **只 pop 那 4 个键、`GITHUB_OUTPUT` 始终设着**
  （`:496`）⇒ **测不到这一态**。
  ⚠️ **但我判定它不构成必须修改项**，理由是「修法比现状更坏」：若照字面把它也兜成 `${VAR:-/dev/null}`，
  则 `steps.wl-ref.outputs.ref` 会是**空**，`gate.yml:124,131-133` 的 `uvx --from git+…@$WL_REF`
  就变成「装**默认分支**」——**静默跑错版本**，正是本 change 要消灭的那一类；
  而现在的行为是**响亮**的（第一个 step 就红）。⇒ 现状是「违反自己措辞的 fail-closed」，
  记入「低危观察」与「未验证项」（真 CI 上 `GITHUB_OUTPUT` 会不会缺省，本工作区不可验证）。

**D4 `docs/gate.md` 的内部引用与编号自洽性**

- 二级标题 **§1…§11 连续、无缺号无重号**（实读）；§1.1/§1.2/§3.1/§3.2/§5.1/§5.1.1/§7.1/§11.1–§11.3 层级正常。
- **全文 `§x.y` 引用逐个解析**：`§1,§1.2,§2,§3,§3.1,§3.2,§4,§5,§5.1,§5.1.1,§6,§7,§7.1,§8,§9,§10,§11,§11.1,§11.3`
  **全部有对应标题**；仅 `§5.2` / `§5.3` 无对应标题，但它们的原文是 **`design §5.2` / `design §5.3`**
  （跨文件引用 `docs/design.md`）⇒ **不悬空**。
- **「见 §7.1」指向的地方真的讲了那件事吗** —— **这一条本轮抓到了真缺陷，且已被并发提交修掉**：
  `f045524` 的 `docs/gate.md:91` 写「`__version__` 恒为 `0.1.0`、与 tag 无关（**见 §7.1**）」，
  而 `f045524` 的 `§7.1` **整节没有 `__version__` 的内容**（`git show f045524:docs/gate.md | grep __version__`
  只命中 `:91` 自己）⇒ **悬空引用属实**。`5384c6e` 在 §7.1 补了那两条（现 `:527-534`）⇒ **现已自洽**。
- `§8:541-542`「§1.2 那条『本包来源』」⇒ 确在 §1.2（`:76-80`）✅；`§1.2:74`「见 §7」✅；
  `§1.2:117`「见 `specs/gate-ref-pinning/spec.md` 的对应 Scenario」是**裸能力路径**（不含 change 目录），
  但 `§7:481` 早已是同一写法（`specs/archive-awareness/spec.md`）⇒ 沿用既有惯例，**不是新缺陷**。

**D5 `tests/` 的新钉子有没有互相矛盾 / 依赖别的测试的副作用**

- **无矛盾**：`test_init_policy.py` 里那条**语义反转**（`test_rerun_with_explicit_different_gate_ref_rewrites_the_caller`）
  与 `test_init_policy_after_initialized_with_different_policy_conflicts`（policy 仍判冲突）是**刻意成对**的，
  两者都绿；`tests/test_init_gate_ref.py` 的 16 条与 `tests/test_init.py` 的「新仓外来 caller ⇒ 冲突」也同向。
- **无副作用 / 无顺序依赖**：五个相关文件**逐个单跑**全绿；**文件级逆序**跑全量 ⇒ 674 passed；
  没有测试写向 `REPO_ROOT`（`conftest.py:109-112` 还做了宿主环境变量消毒）。
- **另一面（正向）**：本轮的变异审计说明多数新钉子**真的会红**（见 Reviewer 7 的表）；
  唯一的两个例外（C1/C2）已在 `1a0f9a2` 补上。

**D6 `tasks.md §6.1` 的自查命令**真的**能查出那类句子吗（拿一个已知会漏的形态试）**

- **能查出原案**：R4 报的三处（`docs/gate.md`「会一直吃 \`v1\`」、`design.md`「吃 \`v1\`」、
  `tests/` docstring）**都**含 `吃 \`v1\`` 或 `退 v1` ⇒ 当时若跑这条命令确实能命中。
- **但覆盖面比它自称的小**（实测，构造文件逐条试）：
  ```
  - GHES 接入方会一直吃 v1        ⇒ 无命中（少了反引号）
  - 落不到 job.workflow_sha 时就退到 v1   ⇒ 无命中（模式是「退 v1」，不是「退到 v1」）
  - 此时包仍然是 v1 / 兜底取 v1 tag       ⇒ 无命中
  - 退回 v1（无反引号）                   ⇒ 无命中
  ```
  四种形态**全部漏网**（`grep -rn "退 \`v1\`\|退回 \`v1\`\|退 v1\|吃 \`v1\`"` ⇒ `exit=1`）。
- **且路径面不含 `openspec/`**：命令的路径是 `src/ tests/ docs/ README.md .github/`，而
  `design.md §4 R6`（R4 N3 的漏网之一）住在 `openspec/changes/…/design.md` ——**正是**它自己那段括号里
  点名的漏网位置，却不在这条命令的射程内。⇒ 见「低危观察」E3。

### E 低危观察（**不是**必须修改项）

1. **`--dry-run --gate-ref X --test-command C` 的收尾话重复**：实跑输出
   `init：已接入 witnessloop（[dry-run] 未落盘；[dry-run] 未落盘：.github/workflows/witnessloop.yml 与台账将一起改成 …）。`
   ——两句都把「[dry-run] 未落盘」说了一遍（`initcmd.py:273` 与 `:174`）。语义正确、只是啰嗦。
2. **`GITHUB_OUTPUT` 未兜**（§D3）：实测未定义 ⇒ EXIT=2。**判定为可接受**——「修」它会换来
   `uvx …@` 装默认分支的**静默**错版，现状是响亮的 fail-closed。仅建议把 `:69` 那句「**一律**用 `${VAR:-}` 读」
   收窄成「四个 `${{ }}` 来源的键一律…」（诚实性），并**可选**地在 `:100` 前加一句显式检查 + 清楚的报错文案。
3. **`tasks.md §6.1` 的自查命令**：措辞说「**全仓活面**核一遍」，但列举的路径与命令都**不含 `openspec/`**
   （而它自己点名的 `design.md §4 R6` 就在那里），且漏 4 种无反引号/变体写法（§D6 实测）。
   实际漏网已修好，所以这只是**今后**的检出能力问题 ⇒ 登记，不判必须修改。
4. **`init --gate-ref ""` / `" "` 静默回落**：**先于本 change 存在**（`v1` 的 `initcmd` 同一条
   `args.gate_ref or ledger_gate_ref(...) or C.DEFAULT_GATE_REF`），本 change **未扩大**它
   ⇒ 按纪律**不计入**必须修改项（与 R4 的处置一致）。
5. **`uninit` 的 diff 文案**（`render_diff` 的 `tofile` 恒为「witnessloop init 将写入」）——R1 E5 / `design.md §4 R7`
   已记，**先于本 change 存在**，仍是现状。
6. **`design.md` 用 `§7.9` 作节号**（全篇没有 §6/§7/§7.1），多份文档与 review 都按这个号互引
   ⇒ 号虽怪但**内部一致**，且**先于本 change 的这几轮**已定型 ⇒ 只登记。
7. **`tasks.md:71-77`（5.2）的文件枚举只列到 `-r3`**（`grill-design` / `grill-adversarial` / `-r2` / `-r3` /
   `building-review`），而 `reviews/` 现在已有 `-r4` 与本报告（`-r5`）⇒ 枚举**每加一轮就旧一次**。
   但同段写的**规则**（「每份报告各配一份 manifest，多出来的轮次各用不同的 stage 名」）**自洽且覆盖它们**
   ⇒ 属**计数类**、按纪律**不算证伪**，登记在此以免被误判为漏落库。

---

## 未验证项

> 每一项都写「若假设相反会怎样」。**这些都不是必须修改项**——除非有文档把它们写成了已验证；
> 我逐条查过：`design.md:87-94` 已给探针输出标「单一来源、不可复现的二手文本」，
> `docs/gate.md:522-523` 已把自建 runner / `pip install git+…` 列为未验证面 ⇒ **没有被写成已验证**。

1. **`job.workflow_sha` / `job.workflow_repository` / `job.workflow_ref` 在 called workflow 里的运行期取值**，
   以及 **Q1 探针（run `38853369550`）的原始输出**：本工作区没有可跑的 GitHub Actions；分支/文件已删；
   唯一载体是 `design.md:69-77` 的粘贴块。
   - **若假设相反**：若 `job.workflow_sha` 实为 caller 的 commit，则每个接入方会**全量硬红**（不是静默吃旧包）；
     若 `job.workflow_ref` 的实际形态与兜底解析不符（如返回裸 `v1`），兜底会 fail-closed 吃兜底 ref
     （**响亮、有 warning**）。实现只用 `job.*`、不用 `github.*` ⇒ 行为不受影响，受影响的是
     `design.md §2 D1` / `gate.yml:42-44` / `tests/test_gate_workflow.py:329-335` 的**叙述**。
2. **真 `uvx --from git+https://github.com/Xingkai98/witnessloop@v1.7.0 …`**：`v1.7.0` **不存在**
   （`git ls-remote --tags origin` 最大 = `v1.6.0`）⇒ 我没跑过真命令；`tasks.md §6.7` 的验收命令仍是**前瞻性**的。
3. **GHES / 同 owner fork / 自建 runner 的 uv 版本差异 / `pip install git+…` 是否同样落 PEP 610 `vcs_info`**：
   未验证（`docs/gate.md:522-523` 已如实登记）。
4. **issue #30 的两组 CI 数字（✗10 / ✗1）**：无法复算（另一个仓 + 真 CI）；我只核到它与
   `proposal.md:33-34` 的自述**一致**。
5. **`refs/pull/N/merge` 能否被 uv/git 安装**：未实测（`spec.md:42-43` 已刻意只作定性、不声称必然失败）。
6. **`GITHUB_OUTPUT` 在 GHES / 老版自建 runner 上会不会真的缺省**：本工作区**不可验证**。
   - **若假设「会缺省」成立**：那台机器上 gate 的**第一个 step 就红**（我实测：未定义 ⇒ EXIT=2），
     而 `docs/gate.md §7.1:515-521` 把 GHES 描述成「fail-closed 退回兜底 ref + 日志有 `::warning::`」
     ——两者**不一致**（不是 warning，是硬红，且 notice/warning 都还没打）。
     这不改变我「修法比现状更坏」的判断（见 §E2），但**若你要把 §7.1 那句当成 GHES 的行为承诺，
     它需要加一句「前提：runner 提供 `GITHUB_OUTPUT`」**。⇒ 我把它列在这里而不是必须修改项，
     因为「GHES 上会怎样」正是判据纪律明写**不算**的那个面。
7. **本报告的行号基准**：`1a0f9a2`。若树在我写完后继续移动，请按上表 blob 重核行号
   （`initcmd.py` / `gate.yml` / `constants.py` / 三份 change 文档在本轮**未变**）。

---

## 必须修改项

> 编号 **P1、P2…**；**非纯措辞**的排前面。基准 = **`1a0f9a2`**。

- **P1（非措辞 · 新代码的静默破坏分支）`_set_ledger_gate_ref` 对「`created_files` 不是 list」的处置
  与它对「JSON 不可解析」的处置相反：前者**静默重建**、后者 fail-closed。**
  - **证据**：`initcmd.py:189-192`（`if not isinstance(entries, list): entries = []`）+
    `:179`（写回台账）+ `:162-165`（JSON 坏 ⇒ `return None`，走诊断路径）。
    实跑（`f045524` 与 `1a0f9a2` 同结果）：台账删掉 `created_files` 键 ⇒
    `init --gate-ref …@v9.9.9` ⇒ **EXIT=0**、台账只剩 caller 一条（policy 条目**没了**）；
    随后 `uninit` ⇒ **EXIT=0「已回滚 witnessloop 接入」**，而 `policy.json` 与 `init-manifest.json`
    **都还在盘上** ⇒ `uninitcmd.py:3-5` 自述的「避免留下半删状态」不成立。
  - **可达性**：前提是**仓外**的台账损坏（工具自产的台账恒为 list）⇒ 严重度低；
    但它落在本 change **新引入**的代码里，且与 spec 的 Scenario（`:113-118`，list 在、只缺 caller 一条）
    是相邻的不同输入 ⇒ 值得按同一标准处置。
  - **改法（择一，都可复算）**：把「`created_files` 存在但不是 list」当作与「台账无法解析」**同一类**——
    在 `sync_caller_gate_ref` 里提前 `return None` 并让 `_already_initialized` 报一行点名文件+成因的诊断
    （注意：`initcmd.py:397` 对**非 dict 条目**的 `AttributeError` 是**先于本 change 存在**的相邻缺口，
    选这条改法时要一并把 `_already_initialized` 的遍历改成只报成因、不崩——后半可另记一条，
    但两处叠起来才会让「拒绝」真正可用）；或者补一条钉子把现状的语义**写死**
    （但这会把「静默丢条目」变成受测契约，我不推荐）。
  - ⚠️ 若你判定「仓外篡改的台账不属本工具的契约面」，那这条降级为 E 类观察——
    请**明写**这个取舍（现在的代码其实已经对 JSON 坏台账表了态，形状坏这一半缺一句表态）。

**（本轮无其他必须修改项。** C1/C2 两条我独立发现的证伪项**已在 `1a0f9a2` 落库**，
我在当前树上重跑变异确认修法有效 ⇒ 不计入本轮的必须修改项。**）**

---

## Open Questions

**（本轮无新增。** 用户已明确「不要向用户提问」（`design.md:329`），而本轮剩下的分歧面只有 P1 的
「拒绝 vs 修复」与它的契约归属——那是一条**实现者按现有机制事实即可裁定**的取舍（同一函数内两条相邻分支的
处置一致性），不需要用户拍板；我在 P1 里给了推荐并写明可回退面。**）**

---

## 收敛结论

**不收敛。**

**判据②（前四轮必须修改项全部已落库）——满足 ✅**

- R1 的 **K1–K8**、R2 的 **L1–L6**、R3 的 **M1–M4**、R4 的 **N1–N3** 我**逐条去正文/代码里核**
  （不核 §7.9 的自述表），落点见 §A；其中三条我**实踩/变异验证**过有效性：
  L3（改回 `"v1"` ⇒ 该条红）、M1（模拟 6.1 四处改动 ⇒ 674 passed）、N1（破坏补条目分支 ⇒ 仅该条红）。

**判据①（本轮没有新的可证伪项）——不满足 ❌**

- **C3 / P1（仍在）**：新代码 `_set_ledger_gate_ref` 对形状损坏的台账**静默丢条目并报成功**，
  下游让 `uninit` 在 `EXIT=0` 的「已回滚」下留下 `policy.json` + `init-manifest.json`
  ——与 `uninitcmd` 自己写的契约相反，也与同一函数内 JSON 坏台账的 fail-closed 处置相反。
  这是**行为面**（不是措辞/计数/格式），实测可复算。
- **C1 / C2（已在被审 revision 上修掉，但属于本轮新发现的可证伪项）**：`handled` 那句的 dry-run 分叉
  当时只钉住一半（真跑说「未落盘」而实际改写了 caller + 台账 ⇒ **674 passed**）；
  R4 的 N2 修复当时**零钉子**（退回自否文案 ⇒ **674 passed**）。两条都已由 `1a0f9a2` 修好，
  我在当前树上重跑同一变异 ⇒ 各 **1 failed** ⇒ 修法有效。

**本轮证伪失败（= 既有结论成立）的部分，一并记明，避免读者以为全盘被推翻**：
(B′) 的上下文落点（`job.*` + step，`gate.yml:53-101` 与 8 类行为级用例一致）；解析 step 是 job 的第一个
step 且 `run:` 内无 `${{ }}` 插值；fail-closed 与兜底剥离**行为级**符合 spec；
`--gate-ref` 的「重写-同步-幂等-可卸载」是**不动点**（含台账缺条目的补条目路径）；
作用域守卫**没有**被打破（删掉它 ⇒ 175 条红）；`check` 自报从不因取不到元数据而失败
（宽 `except` 是**刻意且正确**的，且**不吞** `BaseException`，我实测两个都照常传播）；
`--dry-run` 下「什么都不落盘、也不谎报」（组合矩阵实测）；
`docs/gate.md` 的 § 编号与交叉引用**自洽**（唯一一处悬空引用已由 `5384c6e` 修好）；
测试之间**无矛盾、无顺序依赖、无副作用**（单跑 + 逆序全量均绿）；
远端最大 tag = `v1.6.0`（`v1^{}` = `ae99256`，逐字吻合 `README.md:125`）；
`check --root . --base origin/main --head HEAD` 只剩「缺 manifest」类 4 项。

**建议下一轮**：只需回 P1 一条（一个分支的处置 + 可选的一句 spec/注释表态）。回完之后，
本轮**剩余面全是「本工作区不可验证」的（真 CI 的 `job.*`、GHES/自建 runner、`v1.7.0`、issue #30 的两组数字）
或已登记的低危观察** ⇒ 下一轮应当**收敛**。

---

## 处置（主 session 在 R5 之后追加，非审阅者原文）

> 本报告判定**不收敛**（②满足、①不满足），基准 `f045524` → 收尾 `1a0f9a2`。三条新证伪里，
> 第 1、2 条**已在 `1a0f9a2` 由我落库**（你复核确认修法有效），**P1 由本次提交落库**。

- **P1（`_set_ledger_gate_ref` 对「`created_files` 不是数组」静默重建 ⇒ 丢条目 + `uninit` 半删）**：
  **修法照你的描述收紧到 fail-closed**：
  1. `sync_caller_gate_ref` 在写之前**先判** `created_files` 是不是数组，不是就**不写**（返回 `None`）；
  2. `_set_ledger_gate_ref` **不再**兜这个情形——调用方已保证是数组（注释写明为什么）；
  3. `_already_initialized` 补一条**受控**诊断（「`created_files` 不是数组：无法核对台账漂移」+ 退 1）
     ——顺带堵上你顺带暴露的那个**既有**崩溃面（dict 会迭代出字符串键 ⇒ `entry.get` 抛
     `AttributeError` 冒到进程入口，只留一句「内部错误」；字符串则逐字符迭代）。
  **钉子**：`tests/test_init_gate_ref.py::test_a_malformed_ledger_is_loud_and_never_rebuilt`
  ——断言退 1、诊断里有「结构非法」、caller 与台账**一个字节都没动**，且 plain `init` 走同一条受控路径。
- **第 1 条（`handled` 只钉了一半）**：已改成两面都钉——`assert "已落盘" in err` **且**
  `assert "未落盘" not in err`。变异复核：把两条分支合成同一常量 ⇒ 现在**红**
  （你跑的是「674 passed」，现在 `1 failed`）。
- **第 2 条（N2 的修复零钉子）**：新增 `test_rewrite_and_a_tests_write_do_not_contradict_each_other`
  ——两条轴同动时收尾话不得自称「其余文件无改动」。变异复核：把 note 退回旧文案 ⇒ 现在**红**。

### 你点名的两个「题面项」的处置

- `installed_vcs_ref` 的宽 `except` **不吞 `BaseException`**：你的实测与我的读码结论一致；
  已在 `checkcmd` 与 `docs/gate.md §7.1` 各写明一句（免得后来者以为它吞 Ctrl-C）。
- `>> "$GITHUB_OUTPUT"` 未兜底：**照你的判断，刻意不兜**——已在 `gate.yml` 就地写清理由
  （兜了会退化成 `uvx --from git+…@` 装默认分支的**静默错版**；现状是响亮的 fail-closed）。

### 低危观察的处置

- `tasks.md §6.1` 的自查 grep 抓不住变体、且面不含 `openspec/`：已改成**面含 `openspec/changes/gate-ref-pins-package/`**，
  并把单一字面 grep 降级为「起手式」，写明**必须用已知会漏的形态试过**、抓完**逐条人判**。
