# Grill-ADVERSARIAL R2: archive-arrival-recognition 对抗验证（独立零记忆审阅者）

> 任务：**证伪** R1 之后重写的 `design.md`（D1 五条判据，重点第 5 条「内容来源/指纹」）与 `spec.md` / `tasks.md`。
> 硬约束：不向用户提问、只写本文件、不改 `src/` / `tests/` / 其它 change 文档。

## Reviewer

**独立零记忆**：本对话不携带该 change 的任何历史。设计稿里的「实测」「文件:行号」「今天成立」一律当**待验证断言**，可复算的一律复算。R1 的结论只当**待复核的声明**，不当事实。

**读了**：本 change 的 `proposal.md` / `design.md` / `tasks.md` / `specs/archive-awareness/spec.md` / `reviews/grill-design.md` / `reviews/grill-adversarial.md`（R1）；前身 `openspec/changes/archive-awareness/`（proposal / design / spec delta）；源码 `src/witnessloop/{contract,checkcmd,gitutil,policy,paths,constants,manifestcmd,evidence,hashing}.py`；测试 `tests/test_archive_awareness.py` / `tests/helpers.py` / `tests/conftest.py`。

**跑了**（逐条可复算；全部 scratch 工件在 `/tmp`，**未触碰**仓内任何文件）：

1. `.venv/bin/pytest tests/test_archive_awareness.py -q` → **25 passed**（与 R1 声明的基线一致）。
2. `git diff -M --name-status` 探针（`/tmp/gprobe`）：`cp -r` 现成归档目录 ⇒ 全 `A`；源目录**完全不在 diff 里** ⇒ 复现 R1 的 F1 前提。
3. **D1 五条件模拟器** `/tmp/sim_d1r2.py`（import 真 `witnessloop.gitutil/paths/policy`，用真 git 树；条件 1–5 逐字转写自 `design.md:69-122` 与 `spec.md:16-44`），对 18 个构造算 `arrived` + 逐条 c1..c5（构造脚本 `/tmp/build_cases.py` 建在 `/tmp/cases/*`）。
4. **真 CLI 端到端 ×4**（`witnessloop init` / `manifest build` / `check`）：`/tmp/e2e_archive.py`（补一个文件移动 + 整份搬证据 + 报告改后缀）、`/tmp/e2e_byte.py`（同构造，报告加**一个字节**）、`/tmp/e2e_delspec.py`（同构造，**删** `specs/` 内一个文件）、`/tmp/e2e_partial_move.py`（**一个文件 move + 其余整份 copy**）。
5. `git ls-tree` 两种写法的实测（`/tmp/cases/r11_base_blob`）：不带尾斜杠 → `100644 blob …`；带尾斜杠 `-r` → `''`。
6. `gitutil.diff_names` 的改名折叠实测（`/tmp/cases/r6_legit_move`）。
7. `git diff -M -l1`（renameLimit=1）下字节相同的改名**仍**配成 `R100`。
8. 浅克隆探针（`git clone --depth 1 --no-single-branch`）、merge-commit 探针。
9. `grep` 复核 design / spec / tasks / proposal 三份文档的口径（结果见 D/E 节）。

---

## 对抗结论

### A. 找绕过

> 复算入口：`python3 /tmp/sim_d1r2.py /tmp/cases/<name> main HEAD`（谓词）；`python3 /tmp/e2e_*.py`（真 CLI）。
> ⚠️ **模拟器是「spec 逐字转写」，不是实现**——五条判据的措辞我按 `design.md:69-122` + `spec.md:16-44` 抄写，真实现若在 D 的枚举范围、指纹匹配语义上不同，结论可能变。凡属「模拟器 + 真 CLI 组合」的结论我都标了**哪一半是实测**。

#### ✅ A1（**证伪成功，高危**）：豁免 ① 是**逐记录**的 ⇒「搬一个文件 + 其余整份 copy」把第 5 条整体洗白

- **构造**（`/tmp/e2e_partial_move.py`，真仓 + 真 CLI）：
  - base：active change `z`（件齐、三份 manifest 用**真** `manifest build` 产出、报告齐全）+ `app.py`。
  - feature：① 只改 `app.py`（本 PR 的**全部**创作）；② `git mv changes/z/notes.md archive/2026-10-15-z/notes.md`（**唯一**的 move），再把 `changes/z` 的其余文件**逐字节** `cp` 进 `archive/2026-10-15-z/`；用真 CLI 重绑三份 manifest（报告字节**一个都没改**）。
- **实测**（`check --base main --head HEAD`）：

  ```
  === diff -M --name-status main HEAD
  M       app.py
  R100    openspec/changes/z/notes.md       openspec/changes/archive/2026-10-15-z/notes.md
  A       openspec/changes/archive/2026-10-15-z/{proposal.md,design.md,tasks.md,specs/cap/spec.md}
  A       openspec/changes/archive/2026-10-15-z/reviews/{grill-review.md,grill-adversarial.md,building-review.md,*.manifest.json}
  === check 退出码 = 0
  check：基线 main...HEAD，12 个变更文件，1 个 change 目录
    change：2026-10-15-z（归档）
  check：通过 ✓
  ```
- **判据层模拟**（同一仓，`/tmp/e2e_partial`）：

  ```
  openspec/changes/archive/2026-10-15-z: arrived=True  c1=True c2=True c3=True c4=True c5=True  src=['z']  c5命中D=[]  |E(A)|=5
  base change dirs = ['openspec/changes/z']
  ```
- **机理**：`design.md:119-120` 的豁免 ① 是**逐记录**的——「到达组里**有一条**记录的 `old_path` 落在 D 下、`new_path` 落在 A 下」就把 D 判成「本次已被搬走」。于是一条 `notes.md` 的 move 就把 `E(z) ⊆ E(A)`（**逐字节成立**）的 D 从第 5 条里豁免掉了。第 3 条只看 `archive/**` 的 `old_path`（源是 active ⇒ 失明），第 4 条被 `2026-10-15-z` 的 `-z` 后缀满足。
- **这恰好是 spec 第 5 条正文要挡的形态**：`spec.md:34` 写「内容不得整份取自 base 树里**仍然存在**的 change 目录」——`changes/z` **确实仍然存在**，但豁免 ① 让它算「已搬走」⇒ **正文与豁免自相矛盾**。
- **注**：这个形状**今天也是绿的**（当前 `archive_grant` 靠那条 R100 记录授予）。所以它不是本 change 引入的回归，而是本 change **声称堵住**（`design.md:84`「新增，堵 F1 的 copy 变体」）却没堵住的口子。

#### ✅ A2（**证伪成功，高危**）：`E(D) ⊆ E(A)` 只识别「逐字节 + 同路径」的整份复制——**打断 ⊆ 的成本是零**

第 5 条在「源仍在 head」时是唯一屏障（A1 之外，r1 实测它确实挡住了 R1 的原版纯 `cp`）。但它对以下五种改法**全部失明**（模拟器实测 `arrived=True`）：

| # | 构造（`/tmp/cases/*`，均为**源码侧零创作成本**） | 模拟器 `arrived` | 真 CLI |
|---|---|---|---|
| r2 | `cp -r` + 把 `specs/cap/spec.md` **改名**成 `spec2.md` | `True`（`\|E(A)\|=5`，⊄ 因路径不同） | — |
| r3 | `cp -r` + 把报告 `grill-review.md` **改后缀**成 `.txt`（**零字节改动**） | `True`（`\|E(A)\|=4`） | `check` **退出码 0**（`/tmp/e2e_archive.py`） |
| r4 | `cp -r` + 给一份报告**加一个字节** | `True`（`\|E(A)\|=5`） | `check` **退出码 0**（`/tmp/e2e_byte.py`） |
| r5 | 报告取自 base 的 change `a`、`tasks.md`+`specs` 取自 change `b`（**混合两个源**，报告逐字节复用） | `True`（`E(a)⊄E(A)` 且 `E(b)⊄E(A)`） | — |
| r19 | `cp -r` + 把 `specs` **目录换成同名普通文件**（`E(A)` 丢光 `specs/**`） | `True`（`\|E(A)\|=4`） | — |
| — | `cp -r` + **删掉** `specs/` 内一个文件（必需件只查 `specs` 目录本身，`spec_hash` 由 `manifest build` 重算） | — | `check` **退出码 0**（`/tmp/e2e_delspec.py`） |

- **真 CLI 那三条的关键**：`manifest build` 会从磁盘**重算** `tasks_hash`/`spec_hash`/`report_hash`（`src/witnessloop/manifestcmd.py:146-153`），`check` 拿重算后的值与重算后的字节比（`src/witnessloop/contract.py:498-534`）——**自洽恒成立**。所以 `design.md:131` 表格里那行「**改字节** ⇒ 哈希绑定立刻崩 ⇒ **红**」**实测为假**：哈希绑定只能抓「不在 A 上重算 manifest」的改动，而 manifest 是攻击者手上的、且有官方命令可重算（`design.md:136-138` 自己也承认「改字节 + 重算哈希能过」，**与同节表格自相矛盾**）。
- **同节的「穷举」因此不成立**：`design.md:124-133` 列了四类改动并声称「四个方向都关掉了」；实测**只有第 1 类（改 `reviews/*.manifest.json` 字段）与「往 A 里新增文件」两类被关掉**（r1 / r16 实测 `c5=False` ⇒ 不授予），第 3 类（删文件）、第 4 类（改字节）**不成立**，且还有第 5 类没被列进穷举——**改「哪份证据放在哪个路径」**（r2/r3/r19；r3 是**零字节**）。

#### ✅ A3（**证伪成功，中危**）：第 5 条的 D 扫描只有「change 目录 × 相对路径」两个盲区

- **构造**（`/tmp/cases/r21_nested_source`）：base 里有嵌套归档 `openspec/changes/archive/2026/10-15-old/`（件齐、报告齐）。feature：把它**整份 `cp`** 成扁平新目录 `archive/2026-10-15-new/` + 改 `app.py`。
- **实测**：`git diff -M --name-status` 全 `A` ⇒ 第 3 条失明；模拟器 `archive/2026-10-15-new: arrived=True（c5=True）`，而 base 的 D 扫描只看到一个键 `openspec/changes/archive/2026`，其 `E=∅`（**相对路径**是 `10-15-old/tasks.md` 之类，既不是 `tasks.md`、也不匹配 `specs/**`）。
- **两条盲区的通用形式**：(i) D 必须是 `<changes_root>/<id>/` 或 `<changes_root>/archive/<name>/` 这一层；(ii) `E(X)` 的相对路径匹配在**更深一层**就落空。⇒ **任何不在「扁平 change 目录」位置的现成证据，第 5 条都看不见**（包括 `docs/shipped/**` 这类仓库里的历史副本——同机理，未另跑）。
- 这条**不能**靠「今天也不支持嵌套」挡回去：第 5 条是**本 change 的主守卫**，它的视野边界必须写清（见「必须修改项 M4」）。

#### ❌ 证伪失败（这些是有价值的负面证据）

- **R1 的 F1 原版（纯 `cp -r` + 改 manifest 两个字段、源目录原封不动）**：`/tmp/cases/r1_copy` ⇒ `arrived=False`，`c5=False`，`c5命中D=['openspec/changes/archive/2026-09-30-old']`。**第 5 条确实关掉了它**（与 `design.md:107-133` 的宣称一致）。
- **「copy + 删源」洗白（想靠豁免 ② 而不是 ① 过关）**：`/tmp/cases/r9_copy_then_delete` ⇒ `arrived=False`，**`c3=False`**。机理实测：字节相同的删+增**仍被 git 的 exact-rename 检测配对**（`git diff -M --name-status` 输出 10 条 `R100`，`old_path` 落在 `archive/**`）⇒ 第 3 条命中。**并且 `-l1`（renameLimit=1）下配对照旧**（`git diff -M -l1 --name-status` 同为 `R100`）⇒ 这条路不靠 renameLimit 侥幸。
- **改名既有归档目录（N8）**：`/tmp/cases/r8_rename_archived` ⇒ `arrived=False（c3=False）`。两条判据都命中，与 `design.md:364` 一致。
- **用豁免 ① 去豁免一个「归档」D**：任何满足 ① 的记录其 `old_path` 必落 `archive/**` ⇒ 第 3 条同时命中（**第 3 条与豁免 ① 在归档源上是耦合的**，我试了「把 D 的一个文件搬进 A」「搬进另一个新归档目录 A2」两种写法，前者被第 3 条挡、后者 ① 不成立 ⇒ 都不授予）。**但这条耦合在 active 源上不存在 —— 那就是 A1。**
- **预存归档目录 + 新增文件（N3）**：`/tmp/cases/r10_preexisting_plus_file` ⇒ `c1=False`。
- **从仍在 active 的源整份 `cp`（名不认得）**：`/tmp/cases/r14_copy_from_active` ⇒ `arrived=False`（`c5` 命中 `openspec/changes/z`）——这是**设计意图**（`design.md:88`），但 `design.md:460` 的「对照」行说这种「源目录不动」的 `cp` **两种选法都绿**，**与实测相反**（见 D 节）。
- **`archive/2026/` 组织型子目录（F2）**：`/tmp/cases/r12_org_dir` ⇒ `archive/2026: c2=False` ⇒ 不是 target，F2 修好（对**这一**形态）。

### B. 找假阴性 / 误伤

#### ✅ B1（**证伪成功，中低危**）：第 2 条把「F2 假阴性」只修了一半——只要组织型目录里有一个**与必需件同名**的直接子项，它又变成 target

- **构造**（`/tmp/cases/r15_org_dir_with_reviews`）：head 新建 `openspec/changes/archive/notes/reviews/x.md`（外加 `archive/notes/sub/workflow-events.jsonl`）+ 一份受保护写入 + 改 `app.py`。
- **实测**：模拟器 `openspec/changes/archive/notes: arrived=True（c2=True）`——因为 `notes` 的直接子项里有 `reviews`（`policy.required_artifacts` 的一项）⇒ 它被当成「到达的 change `notes`」⇒ `validate_change_dir('notes')` 会报「缺少必需件 proposal.md / design.md / tasks.md / specs」⇒ **今天不红、修后红**（今天 `changed_change_ids` 对 `archive/**` 一律排除、`archive_grant` 要求 `R100` + 源在 active ⇒ 无 target）。
- 与本仓既有测试的关系：`tests/test_archive_awareness.py:378` 用的是 `archive/notes/sub/workflow-events.jsonl`（`notes` 的直接子项只有 `sub`）⇒ 该用例**仍绿**、`design.md:350` 的说明成立；但**同款目录只要多一个 `reviews/` 子目录**就翻红。判据的判据是「≥1 个必需件」，比「是 change 目录」低得多。
- 严重度：需要「组织型目录 + 与必需件同名的子项」这一巧合，故不高；但它说明 **F2 只是被缩小、没有被关掉**，而 `spec.md:91-97` 的 Scenario 把结论写成了「组织型 / 工具型子目录 SHALL NOT 被当作到达的 change」——**这句话在 r15 形态下为假**。

#### ✅ B2（**证伪成功，中低危**）：**复制式归档**（`cp` 而不 `git mv`）在名字认得源时会被第 5 条拒

- **推演 + 模拟器复算**：把「归档」实现成「拷一份到 `archive/<date>-<id>/`、active 目录留着」的仓（若接入方的归档器如此），其合法归档 PR 会命中 `E(旧目录) ⊆ E(新目录)` 且旧目录仍在 head ⇒ **`arrived=False` ⇒ 红**（r14 实测：`c5命中D=['openspec/changes/z']`）。
- 是否可接受取决于**有没有**这种流程：`design.md:140-142` 的「误伤面」只声明「唯一命中形态是拿现成 change 当模板**整份逐字节复制**」——复制式归档**正是**整份逐字节复制，所以设计口径上说得通；但 `design.md:460` 的「对照」行又明说这种 `cp` **是绿的**（自相矛盾，见 D 节）。本仓可复算的接入方证据（`proposal.md:18` 的 `R068/R069/R070/R090`）指向 `git mv` 式归档，故**对该接入方不构成误伤**。

#### ❌ 证伪失败的「必须绿」形态（实测符合设计预期）

- **出生即归档**（`/tmp/cases/r13_born_archived`）：`arrived=True`，c1..c5 全 True。
- **合法纯 move**（`r6`）：`arrived=True`，`src=['z']`。
- **move 内带内容改动 / 重建 manifest**（`r7`）：`arrived=True`（diff 里那一条实测是 `R099`，与 `design.md:37` 的「`R<100`」形状同类）。
- **N2 形态**（新建 `archive/<name>/…` 且证据是**自己写的**）：`arrived=True` ⇒ 由证据门拦（与 `tasks.md:51-53` 的语义反转一致）。

### C. 判据的必要性与充分性（第 1–5 条逐条）

| # | 去掉它会怎样 | 它能不能被绕过 | 复算 |
|---|---|---|---|
| **1**（基准树完全无 entry） | 预存归档目录会被授予 ⇒ N3/N4/N8 与 `archive-awareness` 自认的残留边界全部回来 | **不能**（对「base 同路径是 blob」已用不带尾斜杠的 `ls-tree` 钉死；两种写法我都实测：blob ⇒ `100644 blob …` / `''`，不存在 ⇒ `''`） | r10 `c1=False`；r11 `c1=False` |
| **2**（head 是 tree 且直接子项含 ≥1 必需件） | `archive/2026/` 这类组织型目录会被当成 change（R1 的 F2 回来） | 作为**入口**条件不构成绕过面（真把关的是证据门）；但**判据本身有两个瑕疵**：① 直接子项语义 ≠ 契约门的路径语义（若 policy 的 `required_artifacts` 写多段名，如 `reviews/grill-review.md`，探测**永不**匹配 ⇒ 到达判定整体失明、全部 fail-closed 红——模拟器实测 `c2=False`）；② 见 B1 | r12 `c2=False`；r15 `c2=True`（假红） |
| **3**（到达组无 `old_path` 落在 `archive/**`） | 改名既有归档目录 ⇒ 白捡证据（N8） | **实测挡得住** rename 与「copy+删源」两种洗白（r8/r9 `c3=False`；`-l1` 下 exact rename 仍配对）；对 copy（源不动 ⇒ 无 rename 记录）**结构性失明**——但那是第 5 条的活 | r8/r9 |
| **4**（有源时须名识别） | F3 的拒绝面消失（`archive/misc` 走完整证据门）。**不承重安全**（R1 的结论我复算成立：它原本要挡的 N6 已被第 1 条独立关掉） | 无（它只是收紧） | r6 `c4=True`；r14 有源但名认得 ⇒ 靠第 5 条才拦住 |
| **5**（内容不得整份取自仍在的 change 目录） | R1 的 F1 **原版**立即复活（r1 实测：唯一挡住它的就是 c5） | **能**，且成本极低：A1（豁免 ① 洗白）、A2（零/极低成本打断 ⊆ 的 5 种改法）、A3（D 扫描盲区） | 见 A 节 |

**小结（必要性与充分性）**：第 1、2、3、4 条都站得住（各自关掉了它该关的形态，且我未能绕过）；**第 5 条「必要但不充分」**——它是 F1 原版唯一的屏障（必要），但只覆盖「逐字节同路径整份复制」这一个点，五种同成本变体全部逃逸，且豁免 ① 让它在一个更现实的形态（A1）上**完全失效**。

### D. 与源码事实核对（`文件:行号`）

**成立（我逐条复核）**

- `contract.py:65` `is_archive_move` / `:85` `changed_change_ids` / `:97` `archived_sources` / `:119` `archive_grant` / `:145` 名识别 / `:211-213` 必需件存在性判定 / `:252` manifest glob / `:333` 孤儿扫描 `reviews.rglob("*.md")` / `:391-394` `change_id ∈ accepted` / `:498-534` 哈希绑定 —— design `§1.1` 与 `§3` 的行号**无漂移**。
- `checkcmd.py:228` `_protected_writes`、`:255` `is_archive_move` 分支、`:270-271` 不变集 + `A` 免事件、`:82` `_code_hits`、`:105-119` 两条 stage 硬门、`:121` `_require_change` —— 全部对上。
- `gitutil.py:99` `changed_files`、`:105` `--name-only`… 更正：`:105` 是 `diff --name-status -z --find-renames f"{base}...{head}"`（**三点**）✓；`:54-71` `resolve_base` ✓；`:107-110` `GitError`（merge-base 求不出 ⇒ 既有 fail-closed）✓。
- `policy.py:76-92` `stale_exempt_paths`（末项 `archive/**` ⇒ **暗房存在**）✓；`:115-117` `required_artifacts` 的 `or DEFAULT` ⇒ **policy 写 `[]` 关不掉这条**（`design.md` 未展开、但结论正确）✓；`:18-23` 不变集 ✓。
- `constants.py:87-90` `HASHED_ARTIFACTS` = `tasks_hash→tasks.md`、`spec_hash→specs` ✓；`:95-105` manifest 必填字段 ✓。
- `manifestcmd.py:33-48` `resolve_change_dir`（active → archive → 报错）✓；`:101-105` `--change archive` 被拒 ✓；`:136-142` 报告必须在 `reviews/` 下 ✓；**`:146-153` 每次 build 都从磁盘重算全部哈希** ⇒ 攻击者可重算（这一条是 A2 的根因，`design.md:131` 的「哈希绑定立刻崩」不成立）。
- `hashing.py:22-37` `sha256_tree` 对**文件**也返回其字节哈希 ⇒ 「`specs` 是普通文件」能通过必需件与哈希两关（r19）。
- `design.md:74` 的实测断言「带尾斜杠的 `ls-tree -r` 对同路径 blob 返回 0 行」**复现成功**（`''` vs 不带尾斜杠的 `100644 blob …`）。
- `design.md:290`「`merge-base` 求不出时 `changed_files` 已经抛错并 fail-closed，新判据的独立触发面很窄」——浅克隆探针支持：`--depth 1` 克隆里 `git merge-base origin/main feature` **无输出**（无共同祖先），而 `ls-tree -r origin/main -- openspec/changes` **正常返回** ⇒ 独立面确实只剩「merge-base 成功但 ls-tree 失败」。
- R1 遗留项 ⑤「`manifest build` 不调 `change_targets`」——复核成立（`manifestcmd.py` 全文无 `change_targets`），且我用真 CLI 对**归档目录**跑通了 `manifest build --change 2026-10-15-stub`（4 次 e2e 里都成功）。

**不成立 / 自相矛盾（新）**

1. **`design.md:259`（C6）/`:318-320`（§5.1 第 11 条）/`:367`（N11）与 `design.md:73-76`（D1 第 1 条）+ `spec.md:99-103` 直接矛盾。**
   - C6 写「**会到达、且这是对的**」、N11 写「该目录**是**到达 ⇒ 红点由证据门给出」、§5.1 第 11 条写「第 1 条**不**成立…**按到达处理**」（同一句里自相矛盾）。
   - D1 第 1 条（钉死为「该路径完全没有 entry」）与 `spec.md:103`「判据 1 SHALL 判『基准树里该路径**有** entry』⇒ **不授予**」相反。
   - **模拟器实测（`/tmp/cases/r11_base_blob`，base 有 blob `archive/foo`、head 是含必需件的目录）**：`arrived=False（c1=False）` ⇒ **实现按 D1/spec 走就是「不授予」**，C6/N11/§5.1-11 三处是 M-C1 之前的残留（R1 的 M-C1 只改了 D1 第 1 条与 spec，没回写这三处）。
2. **`design.md:460`（§8 Q1 的「对照」行）与第 5 条矛盾**：「把同样的内容 `cp -r` 到新建的 `archive/misc/`（源目录**不动**）：两种选法**都绿**」——实测 `r14_copy_from_active` 是 `arrived=False（c5 命中）` ⇒ **不授予**（源在 active 且仍在 head）。该行是 R1 之前的文本。
3. **`design.md:131`（表格第 4 行「改字节 ⇒ 红」）与 `design.md:136-138`（正文「改字节 + 重算哈希能过」）矛盾**；实测站在正文一边（`/tmp/e2e_byte.py` → `check` 退出码 **0**）。
4. **`spec.md:43`（**规范性文本**）「删掉 / 改字节由既有的必需件、哈希绑定与孤儿规则拦下」**——实测不成立：删 `specs/` 内一个文件（必需件只查 `specs` 目录本身）与改一个字节，只要重算 manifest 就全过（`/tmp/e2e_delspec.py`、`/tmp/e2e_byte.py` 各退出码 0）。**规范文本写了一条实现给不出的保证**。
5. **`spec.md:39-41` 的豁免措辞比 `design.md:119-120` 更松**：spec 只写「D 的路径…是到达组某条记录的源目录」，**漏了 `new_path` 落在 A 下**这个限定。按 spec 逐字实现（任何到达组记录、哪怕 `new_path` 落在**别的**新归档目录）会比 design 多豁免一批 D ⇒ 洞更大（推演：D 的一个文件被搬进另一个新归档目录 ⇒ 按 spec 措辞 D 算「已搬走」⇒ 第 5 条失明；design 的措辞不成立）。**两处必须统一，并取 design 的窄口径**（其实按 M2 应把 ① 删掉）。
6. **`proposal.md:88-89`（验收里的「对称性」核心不变量）未跟上 `design.md:161-164` / `spec.md:214-218` 的限定**（proposal 仍是无条件表述，未排除 stale 维度）。同类文档漂移，R1 的 M-DOC 批次没覆盖 proposal。

### E. 低危观察（不阻塞）

1. **第 2 条与契约门的「同一张表」说法不准确**：契约门判的是 `<dir>/<artifact>` **路径存在**（`contract.py:211-213`），探测判的是「**直接子项名**」；policy 把 `required_artifacts` 写成多段名时两者分叉（模拟器实测：`required=('reviews/grill-review.md',)` ⇒ `c2=False` ⇒ 任何归档目录都不再是到达 ⇒ 全部 fail-closed 红）。`design.md:78-79`「探测用契约门同一张表，不引入第二套口径」在**语义**上站不住（同一张表、两种匹配语义）。
2. **`E(X)` 排除 `proposal.md`/`design.md` 使 ⊆ 更容易成立/被打断**：这两份是必需件、必须存在，但它们不参与指纹 ⇒ 攻击者可以用**自己写的** proposal/design 搭配**别人**的 tasks/specs/reports 通过全部判据（`⊆` 只看 D 的成员在不在 A 里）。属第 5 条设计取舍，但应在文档里写明「指纹只覆盖被绑字节」的后果。
3. **报告可以放在 `reviews/` 之外**：`check` 的 `resolve_report_path` 只要求「解析后仍在 change 目录内」（`contract.py:282-300`），只有 `manifest build` 才强制 `reviews/`（`manifestcmd.py:136-142`）⇒ 手写 manifest 把报告放在 change 根目录，就能同时避开指纹（`reviews/**/*.md`）与孤儿规则（`:333`）。这是 A2 的又一个变体，也是既有宽松面（本 change 未引入），建议在文档 §已知边界 里登记。
4. **审核我自己的三条 e2e 的「自证」局限**：三个真 CLI e2e 里，让当前代码认得归档目录的是 `archive_grant`（R100 + 名识别），而**新设计**会走第 1–5 条到达判定——第 5 条那一半是**模拟器**给的。也就是说「真 CLI 绿」证明的是**证据门那半**（那正是 `D2` 声称真正把关的东西），「到达判定那半」是 spec 转写。A1 的威力正来自：**即使**到达判定按 spec 给了资格，证据门也认不出复用。
5. **`design.md:143-144` 把 `diff.renameLimit` 只当「误伤（fail-closed）」面**：实测字节相同的改名在 `-l1` 下**仍配对** ⇒ 该边角只影响「被改写过的文件」；反方向（若哪天配对整体失效，豁免 ② 会让 N8 变绿）设计未讨论。低危（`diff.renameLimit`/`--no-renames` 非攻击者可控）。

---

## 未验证项

1. **接入方 asterwynd 的具体数字**（`proposal.md:30-32` 的 33 文件全 `A`、`R068/R069/R070/R090`、16 文件 11 项、「120 个归档目录」）——另一个仓的提交，本工作区**无法复算**（我只复现了**方向**：`git mv` + 改写被搬文件 = `R<100`（r7 实测 `R099`）、`cp` = 全 `A`）。`tasks 4.2` 必须在接入方仓里真跑。
2. **D1 第 5 条的「实现」**：本仓尚未实现本 change，我的结论来自**按 `design.md:69-122` + `spec.md:16-44` 逐字转写的模拟器**。若实现把 D 的枚举扩大/把指纹改成「内容 sha 多重集」等，A2/A3 的结论需要重新复算。
3. **浅克隆 / 部分克隆下 `ls-tree` 的确切失败模式**：我只测到「`--depth 1` 时 `merge-base` 无输出（既有 fail-closed 先命中）、同仓 `ls-tree -r origin/main` 正常」。**「merge-base 成功但 `ls-tree` 失败」这一独立面未复现**，D7 的 fail-closed 文案与退出码未验证。
4. **merge commit 形态**：我做了一次探针，但**构造失误**（把归档目录建在 base 上，`merge-base` 恰好 = base 自身），未取得该形态的可判定结论。基准与 `changed_files` 同源这一点只有**代码事实**支撑（`gitutil.py:105` 三点 + `checkcmd.py:47-54`），**未**跑成功的 merge 判定用例。
5. **`proposal.md` 表格里的 `@v1`/`@main` 两列对照**（修前 5 项 / 1 项 / 12 项 / 11 项）——需要那两个历史 ref 与接入方 diff，本工作区未复算。
6. **B2 的「接入方是否存在复制式归档流程」**：无法从本仓判定（我只能证明该形态会被第 5 条拒）。

---

## 必须修改项

> 每条附证据。**M1/M2 是同一根因的两半，建议一起改。**

- **M1（高危，必须修）：第 5 条目前只识别「逐字节 + 同路径」的整份复制，F1 的可达性没有实质降低。**
  - 证据：`python3 /tmp/sim_d1r2.py /tmp/cases/{r2,r3,r4,r5,r19} main HEAD` ⇒ 全部 `arrived=True`；`python3 /tmp/e2e_{archive,byte,delspec}.py` ⇒ `check` 退出码全 **0**（报告改后缀 / 加一个字节 / 删一个 spec 文件，各自都是「零或极小创作成本」）。
  - 要求：至少**改掉 `design.md:124-133` 的「四类穷举」表与 `design.md:136-138` 的等价性论证**（现状是表格与正文互相打脸，且「改字节 ⇒ 红」实测为假）；并**在 design / spec 里明写第 5 条的真实覆盖范围**（= 「源目录原封不动、A 与 D 的证据指纹逐路径逐字节相同」这一**唯一**形态）。
  - 可选加强（需权衡 `R7` 的误伤面，见 Open Questions）：把 `E(X)` 从 `(路径, blob sha)` 集合改成 **blob sha 的多重集**（去路径）⇒ 关掉 r2/r3/r19 这类「改路径」绕过；或对报告正文做**内容规范化指纹**（但 r4/r5 仍可绕过）。
- **M2（高危，必须修）：豁免 ① 是逐记录的，可被一条无关的 `git mv` 整体洗白（A1）。**
  - 证据：`/tmp/e2e_partial_move.py` ⇒ `check` 退出码 **0**（报告逐字节未改）；同仓模拟器 `arrived=True（c5=True）`；而 `spec.md:34` 的正文写「不得整份取自…**仍然存在**的 change 目录」——`changes/z` 仍然存在。
  - 建议：**删掉 ①，只留 ②**（「D 的路径在 head 树里已不存在」）。依据：合法 move 的源目录**整体**消失 ⇒ ② 独立成立——`r6`（纯 move）与 `r7`（move+重建 manifest）在**只有 ②** 时仍是 `arrived=True`（`c5` 不命中，因为 ② 豁免）；而 A1 的 `changes/z` 在 head 里仍在 ⇒ ② 不成立 ⇒ 第 5 条命中 ⇒ 关掉。若坚持保留 ①，必须把它收窄为「**D 的全部证据文件**都出现在 A 里」（而不是「有一条记录从 D 进了 A」）。
  - **我已实测这条修法**（把模拟器的 `moved` 改成「只有 ②」，其余不动）：`r6_legit_move → arrived=True`、`r7_move_rebuild → arrived=True`（两条「必须绿」不受伤）；`e2e_partial → arrived=False（c5 命中 changes/z）`（A1 被关掉）；`r1_copy / r9 / r14` 仍 `False`（无回归）。命令：`python3 /tmp/sim_d1_only2.py`（= `sim_d1r2.py` 且 `moved` 只取 ②）。
  - 同时：**`spec.md:39-41` 的措辞要么与 design 对齐（先删 ①），要么补上 `new_path` 落在 A 下**（现状 spec 比 design 更松，见 D-5）。
- **M3（中，必须修）：三处文档自相矛盾 + 一处规范性文本写了实现给不出的保证。**
  - `design.md:259`（C6）/`:318-320`（§5.1-11）/`:367`（N11）说「base 同路径是 blob ⇒ **是到达**」，与 `design.md:73-76` 和 `spec.md:99-103`（**不授予**）相反；模拟器实测 `c1=False`（= 实现按 D1/spec ⇒ 不授予）。三处必须回写。`§5.1 第 11 条`那句「第 1 条**不**成立…按到达处理」本身也不可执行，需重写。
  - `design.md:460`（「`cp -r` 到新建 `archive/misc/`… 两种选法**都绿**」）与第 5 条相反（`r14` 实测不授予）。
  - `design.md:131`（改字节 ⇒ 红）与 `:136-138` 相反（`/tmp/e2e_byte.py` 退出码 0）。
  - `spec.md:43`（「删掉 / 改字节由必需件、哈希绑定与孤儿规则拦下」）实测为假（`e2e_byte` / `e2e_delspec` 退出码 0）；`manifestcmd.py:146-153` 使得 manifest 可被攻击者重算。
- **M4（中，必须修）：把第 5 条的能力边界写进 design / spec（否则它会被读成比实际强的守卫）。**
  - D 扫描只覆盖「扁平 change 目录」（`/tmp/cases/r21_nested_source` ⇒ `arrived=True`）；`E(X)` 的相对路径匹配在更深一层落空；不在 change 目录里的历史副本（`docs/**` 等）完全不可见。至少要在 `docs/gate.md §6 已知边界`（`tasks.md:110-111` 已列该节的更新义务）与 spec 里写明「第 5 条只比对 base 树里**扁平 change 目录**的指纹」。
- **M5（低-中，建议修）：第 2 条的假阴性残留与措辞。**
  - 证据：`/tmp/cases/r15_org_dir_with_reviews` ⇒ `archive/notes` 因含 `reviews/` 子目录而 `arrived=True` ⇒ `validate_change_dir('notes')` 报缺件（新假红）；`design.md:78-79` 的「同一张表、不引入第二套口径」在实现语义上是「同一张表、**两种匹配语义**」（多段 `required_artifacts` ⇒ 探测永不匹配，模拟器实测 `c2=False`）。建议：spec 第 2 条补一句「必需件匹配为**直接子项名**；多段名不支持」，或让探测改用与契约门同款的路径存在性判定。

---

## Open Questions

> 只放**真需要用户拍板**的。能由安全属性定案的我都已移出（例如「要不要授予改名既有归档目录」= 不授予，R1 已定案，我复算 `r8` 支持）。

**OQ-1（第 5 条的强度：加强还是**显式降级**？）**
- 具体例子（同一份 reused 证据，两种处置）：
  - (a) **加强到能挡「零/极低成本改法」**：把指纹改成「blob sha 多重集 + 报告正文规范化」，并对「A 的证据在 base 里任何 change 目录内能找到对应物」直接拒。代价：`R7` 的误伤面扩大（「拿旧 change 当模板改用」会更难，任何**逐字节相同**的报告都会命中）。
  - (b) **承认它只是「挡最廉价的一键 `cp -r`」**：把 `design.md:124-133` 的穷举与 `:136-138` 的等价性论证删掉，改写成明确的**能力边界**（「只拦『源原封不动 + 指纹逐路径逐字节相同』」，其余归入既有的「防漂移不防伪造」），`spec.md:42-44` 同步。
- 我的判断：**(a) 与 (b) 都自洽，但现状（既声称「堵住 F1 的 copy 变体」、又只覆盖一个点）不自洽** ⇒ 必须二选一。若选 (b)，则 `design.md:56-63/§1.5` 那句「白捡证据已被升级保留」需要相应降调（否则规范与能力不符）。

**OQ-2（= design §8 Q1，保留，未变）**：归档目录名「必须认得源 id」这条守卫是否保留？
- 注意我这一轮的新证据：**删掉它（选 (b)）会让 A1 更严重**——A1 现在还需要一条名认得源的 move 记录来满足第 4 条；删掉第 4 条之后，「内容整份来自仍在 active 的 z、A 叫任意名」也会被授予（前提是第 5 条被 A2 类改法打断）。⇒ 若 M2 不修（豁免 ① 不收窄），Q1 选 (b) 是**净放宽**。建议：**先修 M1/M2，再谈 Q1**。

---

## 收敛结论

**不收敛。** 本轮有新的可证伪项，且其中两条（M1/M2）直接推翻设计对第 5 条的两个关键宣称（`design.md:84`「堵 F1 的 copy 变体」、`:133`「四个方向都关掉了」）。

**新的、可复算的证伪项（最小复现）**：

```bash
# ① A1：一个文件 move + 其余整份 copy（零字节改动）⇒ 真 CLI 绿
python3 /tmp/e2e_partial_move.py          # → "=== check 退出码 = 0 / check：通过 ✓"
python3 /tmp/sim_d1r2.py /tmp/e2e_partial main HEAD   # → arrived=True（c1..c5 全 True）

# ② A2：把 ⊆ 打断的三种零成本改法（模拟器 arrived=True）+ 两个真 CLI 绿
python3 /tmp/build_cases.py
python3 /tmp/sim_d1r2.py /tmp/cases/r3_copy_reportext main HEAD   # arrived=True |E(A)|=4
python3 /tmp/sim_d1r2.py /tmp/cases/r19_copy_specs_as_file main HEAD  # arrived=True
python3 /tmp/e2e_byte.py                  # 报告加一个字节 → check 退出码 0
python3 /tmp/e2e_delspec.py               # 删一个 spec 文件 → check 退出码 0
```

**给作者的收敛判据**：M1–M5 落库（其中 M1/M2 需要真的改判据或改口径，而不只是改措辞）之后，再跑一轮 R3；R3 若只剩措辞项即收敛。
