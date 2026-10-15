# Grill-ADVERSARIAL R3: archive-arrival-recognition 对抗验证（独立零记忆审阅者）

> 任务：**证伪** R2 之后重写的现稿（D1 五条判据，重点**第 5 条（内容来源）**与**第 2 条（含全部必需件）**），
> 并独立复核作者在 `design.md §7.4` 列的「作者侧复算」。
> 硬约束：不向用户提问、只写本文件、不改 `src/` / `tests/` / 其它 change 文档。

## Reviewer

**独立零记忆**：本对话不携带该 change 的任何历史。设计稿里的「实测」「文件:行号」「今天成立」一律当**待验证断言**，
可复算的一律复算；R1 / R2 的结论只当**待复核的声明**。

**评审基线**：本报告的行号/引文对应**会话开始时读到的** `design.md`（575 行）与 `spec.md`（304 行）/ `tasks.md`（149 行），
即 commit `302dd31` 的文本。⚠️ 评审期间作者侧**并发改写**了 `design.md`（未提交，`+118/-30`，见文末「附」）——
本报告**不**对该新文本负责（也**没有**对抗验证过它）。

**读了**：本 change 的 `proposal.md` / `design.md`（575 行）/ `tasks.md` / `specs/archive-awareness/spec.md` /
`reviews/grill-design.md` / `reviews/grill-adversarial.md`（R1）/ `reviews/grill-adversarial-r2.md`（R2）；
源码 `src/witnessloop/{contract,checkcmd,gitutil,policy,paths,constants,manifestcmd,evidence,hashing}.py`；
测试 `tests/test_archive_awareness.py` / `tests/helpers.py` / `tests/conftest.py`。

**跑了**（逐条可复算；**全部 scratch 工件在 `/tmp`，未触碰仓内任何文件**，`git status` 收尾为空）：

1. `.venv/bin/pytest -q` → **601 passed**（全量基线绿）；`.venv/bin/pytest tests/test_archive_awareness.py -q` → **25 passed**。
2. **自写判据模拟器 `/tmp/r3sim.py`**：按 `design.md:69-104`（D1 五条）+ `design.md:247-254`（D7 的 `ls-tree` 命令表）+
   `spec.md:20-52`（Requirement 1 正文）**逐字重写**（**不**沿用 `/tmp/sim_d1r2.py` / `/tmp/sim_d1v3.py`——那两个是转写产物，
   不作为判据）。只读 git 树，同时算出**D4 收窄后的 active id 集合**。
   用法：`python3 /tmp/r3sim.py <repo> main HEAD [--verbose]`。
3. **对 R2 留下的 18 个构造仓全体复算**（`/tmp/cases/*`，基线 `main` / head `HEAD`）：**与 `design.md §7.4` 的表逐条一致**
   （见「C 节」表）——即我的独立转写与作者的模拟器在这些构造上不矛盾。
4. **新构造 14 个**（`/tmp/build_r3_cases.py` → `/tmp/r3cases/*`；`/tmp/build_r3_cases2.py` + 内联脚本 → `/tmp/r3cases2/*`），
   专打第 5 条的证据集定义、第 2 条与 D4 的措辞。
5. **真 CLI 端到端两条**（`/tmp/r3_e2e.py`，仓 `/tmp/e2e_r3_a1`、`/tmp/e2e_r3_a2`，用 `.venv/bin/python -m witnessloop`
   的 `init` / `manifest build` / `check`）：两条**都 `check：通过 ✓`（退出码 0）**，详见 A 节。
6. `git ls-tree` 三种写法的实测（一段名 / 多段名 / 目录 tree）、`git diff -M --name-status` 与 `-M -C` 的配对行为实测。
7. 直调 `contract.changed_change_ids` / `contract.archive_grant` 复算「今天」的行为，与新口径 A/B 对照。

---

## 对抗结论

### A. 找绕过（逐条成功 / 失败）

> 口径说明（沿用 R2 的诚实标注）：本 change **尚未实现**，所以任何「绕过」都由两半拼成——
> **到达判定那一半 = 我按现稿文本逐字转写的模拟器**（`/tmp/r3sim.py`），**证据门那一半 = 真 CLI 的 100% 真代码**。
> e2e 里我让真 CLI 认到达是用**一条 `git mv changes/stub archive/<name>` 的 R100 记录**走通**今天**的
> `archive_grant`（R2 的 F1/A1 用的是同一手法），**同时**用模拟器证明**现稿判据也给资格**。

#### ✅ A1（**证伪成功，高危**）：「报告挪出 `reviews/**`」⇒ 判据 5 对**最有价值的那份证据完全失明**

- **构造**（`/tmp/r3_e2e.py` 的 A1 段，仓 `/tmp/e2e_r3_a1`，**真 CLI**）：
  - base：`archive/2026-09-30-old/` 是一份流程齐全的归档 change（三份 manifest 由**真** `manifest build` 产出，
    grill 报告含 3 条 Confirmed Decisions）+ 一个只有 `notes.md` 的 active `stub`。
  - feature：① `git mv changes/stub archive/2026-10-15-stub`（R100，唯一 move，满足判据 4 的 `-stub` 后缀）；
    ② 把受害者的**三份报告逐字节**放到到达目录的**根**（`<A>/grill-review.md` 等，**不在 `reviews/**` 下**）；
    ③ `tasks.md` / `specs/cap/spec.md` 自己写（内容全新）；④ **手写**三份 manifest，`report_path` 指向根上的报告；
    ⑤ 改 `src/app.py`（本 PR 的唯一「创作」）。
- **实测**：
  ```
  [现稿判据模拟器] openspec/changes/archive/2026-10-15-stub: arrived=True c1=T c2=T c3=T c4=T c5=T
  [真 CLI] check 退出码 = 0
  check：基线 main...HEAD，12 个变更文件，1 个 change 目录
    change：2026-10-15-stub（归档）
  check：通过 ✓
  ```
  且三份报告的 blob 与受害者**逐字节相同**（`git hash-object` 对照）：
  ```
  grill-review.md      victim=f92865ac1df1320f75fa7a000eef0dc8f5b0fb27  arrival=f92865ac1df1320f75fa7a000eef0dc8f5b0fb27  相同
  grill-adversarial.md victim=6976a9739cf388c5fc514d4dab300188b9da7d62  arrival=6976a9739cf388c5fc514d4dab300188b9da7d62  相同
  building-review.md   victim=dee8d05057e65c4ef6d396dfaf2734e5c5602eae  arrival=dee8d05057e65c4ef6d396dfaf2734e5c5602eae  相同
  ```
  到达目录 `reviews/` 下只有三份手写 manifest（无 `.md`）⇒ 孤儿规则（`contract.py:333` 只扫 `reviews/**/*.md`）不报。
- **机理**：判据 5 的证据集是**三个路径前缀**（`tasks.md` / `specs/**` / `reviews/**`），而
  **`check` 只要求报告「解析后仍在 change 目录内」**（`contract.py:282-300`），**不要求它在 `reviews/` 下**——
  强制 `reviews/` 的只有 `manifest build`（`manifestcmd.py:136-142`）。⇒ 搬运者把**证词**换个路径就出了扫描面，
  而证词正是「白捡现成证据」里唯一值钱的东西。
- **这与现稿的明文宣称冲突**：
  - `design.md:95-100`：「它们就是「被 manifest 绑定 / 被引用为报告」的内容 …… 一次**搬运**必然连它们一起搬
    （否则证据门立刻红），**所以判据不漏**」——**实测证伪**：搬运者把报告挪到 change 目录根，证据门**没有**红（真 CLI 绿）。
    该段把「报告在 `reviews/` 下」当成了**事实**，而它只是**约定**（只有 `manifest build` 强制）。
  - `design.md:130` 表格行（现稿列）：「改某个证据文件的**路径**（改名 / 改后缀 / `specs` 换成同名文件）⇒ 拒 ✓
    （blob 比对**与路径无关**）」——**只对「改动后仍在三段前缀之内」成立**。
  - `design.md:142-143`：「「改路径」「删一个文件」「混源」「搬一个无关文件进来洗白」这几类零/极低成本的手法
    全都落在判据外」——**实测证伪**（改路径到前缀之外是零成本，且判据 5 看不到）。
- **与 R2 的关系**：R2 的 §E.3 把「报告可放在 `reviews/` 之外」当作**旧指纹判据**下的一条低危观察；
  作者把它降级成 `design.md:161-162` 的「**已知边界（低危，明写）**」。但现稿**把判据 5 升格为主守卫**之后，
  这条宽松面**变成承重的**——它不再是无害的边角，而是主守卫的**唯一漏点**。⇒ 严重度评估被低估，且与同稿的
  「判据不漏」自相矛盾。

#### ✅ A2（**证伪成功，高危**）：「给**每一个**证据文件追加一个字节」（一个 for 循环）⇒ 判据 5 失效

- **构造**（`/tmp/r3_e2e.py` 的 A2 段，仓 `/tmp/e2e_r3_a2`，**真 CLI**）：`cp -r` 受害者的整份证据到新归档目录，
  对**证据集内的每个文件**（`tasks.md` + `specs/**` + `reviews/**`）执行 `p.write_bytes(p.read_bytes() + b"\n")`，
  然后用**真 CLI** 重建三份 manifest，改 `src/app.py`。
- **实测**：
  ```
  [现稿判据模拟器] openspec/changes/archive/2026-10-15-stub: arrived=True c1=T c2=T c3=T c4=T c5=T
  [真 CLI] check 退出码 = 0 ；check：通过 ✓（12 个变更文件，1 个 change 目录）
  ```
  即：**三份真审阅报告的正文字节除末尾一个换行外原封不动**，`PASS`/决策记录/审阅者署名全部复用，判据 5 **零命中**。
- **机理**：判据 5 的 (a) 是「**blob 不出现**」= **逐字节**判据。改一个字节就换一个 blob。R2 已实测「改**一个**文件的一个字节」
  ⇒ 红（因为**其余**证据仍是旧 blob，N11 的形态）；本轮的构造是它的**自然补全**：把同样的改动施加到**每一个**证据文件，
  判据整体失效。这不是「成本升高」——是**同一成本**（`for p in ...: echo >> $p`，或 `git checkout` 后统一跑一次工具）。
- **与现稿明文冲突**：`design.md:145-148` 的自我豁免写的是「把 A 的**每一个**文件都改掉字节、再用 `manifest build`
  重算哈希，就绕过了第 5 条——但那**等价于「自己写一份完整证据」**（每个文件都得动）」。
  **这条等价是假的**：借用内容的**语义**（谁审的、审出了什么决策、对抗轮结论）**一个字节都没变**，
  变的只是每个文件末尾的一个换行；而「自己写一份完整证据」需要真的写报告。
  判据 5 自己声明的目标是「拦**机械搬运**，不是防伪造」（`design.md:147-148`）——本构造**正是机械搬运**。
  ⇒ 「每个文件都得动」既不是「等价于自己写」，也不构成任何**实质**成本。
- **同类文本**：`proposal.md:66` 把「复制后**改一两个字节**」列为不授予的形态；`design.md:313-315`（R7）说
  「必须**每一份**被复制的证据文件都**重写**」——「重写」在现稿里实际只是「改一个字节」。

#### ✅ A3（**证伪成功，中危**）：判据 5 的证据集**按路径形态**判，`specs` / `tasks.md` 的**另一种形态**整体出圈

- **构造与结果**（模拟器，`/tmp/r3cases2/a3b_specs_file_pristine`、`/tmp/r3cases2/a5_tasks_as_dir`）：

  | 构造 | 借用内容的位置 | 模拟器 |
  |---|---|---|
  | a3b | 受害者的一份 spec 文件**逐字节**放在 `<A>/specs`（**普通文件**，非目录）+ 三份报告逐字节放在 `<A>/*.md` | `arrived=True`，判据 5 **零命中** |
  | a5 | `<A>/tasks.md` 做成**目录**，里面放一份**逐字节**搬来的受害者 spec；三份报告挪到根 | `arrived=True`，判据 5 **零命中** |

  两条命令：`python3 /tmp/r3sim.py /tmp/r3cases2/a3b_specs_file_pristine main HEAD`（`c1..c5 全 T`）。
- **机理**：spec 的证据集写法是「`tasks.md`、`specs/**`、`reviews/**` 下的**全部文件**」（`spec.md:40-41`）——
  它按**路径前缀**取文件，而**必需件只判「路径存在」**（`contract.py:211-213`，`hashing.sha256_tree` 对文件/目录都工作，
  R2 已实测 `specs` 是普通文件时哈希绑定照样成立）。⇒ 同一个路径名，**是文件还是目录**改变了它是否在证据集里。
- **与现稿明文冲突**：`design.md:130` / `design.md:394`（**N10**）都**逐字**写「`specs` 换成同名普通文件 ⇒ 拒 ✓」。
  a3b 是这个形态的**内容版**（不是写新内容，而是把受害者的 spec **原样**放成同名文件）⇒ **不拒**。
  a5 更进一步（`tasks.md` 是目录，借用内容挂在它下面），现稿文本对此**没有任何条款**。
- **注**：a3b 的成立依赖「把 `specs` 本体算不算证据文件」这一**读法**（现稿文本「`specs/**` 下的全部文件」按字面
  不含 `specs` 自身）；**a5 不依赖任何读法**（`tasks.md/borrowed.md` 既不是 `tasks.md`、也不在另两段前缀下）。

#### ❌ 证伪失败（有价值的负面证据）

- **R1 的 F1 原版（纯 `cp -r` + 只手改 manifest 两个字段）** `/tmp/cases/r1_copy` ⇒ `arrived=False`，判据 5 命中 **8/8** 份证据文件。
- **R2 的 A2 与它的 4 个真 CLI e2e 仓**（`r2` 改 spec 路径 / `r3` 报告改后缀 / `r4` 改一个字节 / `r5` 混源 /
  `r19` `specs` 变文件；`/tmp/e2e_archive`（报告改后缀）/ `/tmp/e2e_byte`（+1 字节）/ `/tmp/e2e_delspec`（删一个 spec 文件）/
  `/tmp/e2e_partial`（一个文件 move + 其余 cp，命中 **5** 份））⇒ **全部 `arrived=False`**
  （`python3 /tmp/r3sim.py <repo> main HEAD`；我的独立转写与 `§7.4` 一致）。
  ⚠️ 但**同一种改法的「全文件版」（A2）逃逸** —— 即现稿只关掉了「只改一处」的那一档。
- **R2 的 A1（一个文件真 `git mv` + 其余整份 `cp`）**：`/tmp/e2e_partial` ⇒ `arrived=False`，判据 5 命中 5 份
  （`reviews/*.{md,manifest.json}` ×3 + `specs/cap/spec.md` + `tasks.md`），与 `§7.4` 的声明一致。
- **改名既有归档目录（N8）** `/tmp/cases/r8_rename_archived` ⇒ `c3=False`；**copy+删源** `/tmp/cases/r9_copy_then_delete`
  ⇒ `c3=False`（字节相同的删+增仍被 git 的 exact-rename 配对）。
- **预存归档目录加/改文件（N3/N2）** `r10`/`r11` ⇒ `c1=False`。
- **组织型子目录（F2/B1）** `r12`（只有 `10-15-foo`）与 `r15`（含 `reviews/` 子目录）⇒ **都 `c2=False`** ⇒ R2 的 B1 假红
  **确已修好**（`design.md:473` 的声明成立）。
- **必须绿的三条**：`r6`（纯 move）/ `r7`（move + 重建 manifest）/ `r13`（出生即归档）⇒ **全 `arrived=True`**
  （**核心目的达成**，R2 与作者侧的复算我复核成立）。
- **合法 move + 重度改写**（`/tmp/r3cases/m1`、`/tmp/r3cases2/m3`）：到达判定 `arrived=True`（c1..c5 全 T）。
  ⚠️ 但 **D4 的幽灵 id 没消**，见 A4。
- **误伤对照（E11）**：新 change 的 `design.md` 与 base 里某 change **逐字节相同** ⇒ `arrived=True`
  （`/tmp/r3cases2/e11b`）⇒ `design.md:139` 的声明成立。
- **判据 4 的「每一个源」**：`/tmp/r3cases2/t471d`（两个源都被 `2026-foo-z` 认得）⇒ `c4=T, arrived=True`；
  `/tmp/r3cases2/t471e`（第三源 `unrelated` 名不认得）⇒ **`c4=F` ⇒ 整个到达被拒** ⇒ `design.md:373` 对 `:471` 的声明成立。
- **同 diff 内「先复制进 A 再在 A 内改名」的洗白**（推演，**未实测**）：不可行——`changed_files` 是**树对树** diff
  （`gitutil.py:104-106`），A 内「创建又删除」的文件在 diff 里完全不出现，落地文件仍是 `A` 记录 ⇒ (a)(b) 双失。

#### ✅ A4（**证伪成功，中危**）：D4 的排除口径只认 `old_path` ⇒ **`D`+`A`（重写幅度大）仍留幽灵 active id**

- **构造**（`/tmp/r3cases2/m3_move_rewrite_tasks_only`）：base 有 active `z`（件齐）；feature `git mv changes/z archive/2026-10-15-z`
  并把 `tasks.md` **整体重写**（40 行新内容）、改 `src/**`。
- **实测**（`git diff -M --name-status` 实测该 `tasks.md` **没有**被配对成改名，而是 `D` + `A`）：
  ```
  [模拟器] openspec/changes/archive/2026-10-15-z: arrived=True c1=T c2=T c3=T c4=T c5=T
           D4 后的 active ids = ['z']
  ```
  ⇒ `z` 仍是 active target ⇒ `changes/z` 不存在 ⇒ 报「`openspec/changes/z`：change 目录不存在」⇒ **红**。
  今天的行为同样是红（实测 `contract.changed_change_ids(changes, "openspec/changes") == ['z']`）⇒ **不是回归**，
  但**也没被修好**——而 `design.md:102` 说「两只症状（出生即归档 / **move 带内容改动**）同一刀切掉」，
  `design.md:322`（§5.1 第 2 条）说这一类「退出码 0，且**无**幽灵 active id」。
- **机理**：D4 把排除键写成**「到达组的全部记录的 `old_path`」**（`design.md:202`、`spec.md:206-207`）。
  `D` 记录在 `gitutil._parse_name_status`（`gitutil.py:114-130`）里 **`old_path is None`**，它的**被删路径在 `path` 里**，
  于是 `changed_change_ids`（`contract.py:103-115`）照样从 `change.path` 取到首段 `z`。⇒ 只要有一个被搬走的文件
  重写到丢了改名配对，幽灵 id 就回来。**修法**（一行口径）：把 D4 的排除面写成「记录的 `old_path`，**以及** `D` 侧记录的
  `path`，若其所在源目录在 head 树里已不存在」。
- **现实性**：`proposal.md:22-23` 自己指出接入方「`tasks.md` 必须在实现 PR 内勾选完成——**勾选就是改动**」。
  勾选一两行 ⇒ `R<100` ⇒ 现稿修好；**整体重写** `tasks.md` / 整体重写 `specs/**`（spec delta 在实现期收缩很常见）
  ⇒ 掉出配对 ⇒ 幽灵 id 照旧。⇒ 本 change 的「症状 2」只被修好了一档。

### B. 找假阴性 / 误伤

#### ✅ B1（**证伪成功，中危**）：`design.md:363-366` / `tasks.md:57-60` 给的 **`:494` 改写配方产出的到达目录不是 target**

- **配方原文**：「feature 上把**整个** `changes/x` 纯 move 到 `archive/x`，**并**新建一个件齐的 `changes/x`」。
- **构造与实测**（`/tmp/r3cases2/t494b_regression_recipe`，`python3 /tmp/r3sim.py … main HEAD`）：
  ```
  openspec/changes/archive/x: arrived=False  c1=T c2=T c3=T c4=T c5=F  srcs=['x']
      第5条命中: .../archive/x/reviews/.gitkeep（既非新 blob 也非改名落点）
      第5条命中: .../archive/x/specs/cap/spec.md
      第5条命中: .../archive/x/tasks.md
  D4 后的 active ids = ['x']
  ```
  真实 diff（`git diff -M --name-status main HEAD`）：
  ```
  A   openspec/changes/archive/x/design.md
  R100 openspec/changes/x/notes.md → openspec/changes/archive/x/notes.md
  A   openspec/changes/archive/x/proposal.md
  A   openspec/changes/archive/x/specs/cap/spec.md
  A   openspec/changes/archive/x/tasks.md
  M   openspec/changes/x/specs/cap/spec.md      ← 源路径**仍在 head**（新 active change）
  ```
- **机理**：改名配对需要一条**删除**。配方里「新 active change」占着**同样的路径** ⇒ git 报 `M`（不是 `D`）⇒
  `archive/x/*` 变成 `A`，其 blob 又都在 base 的 `<changes_root>/**` 里 ⇒ (a)(b) 双失 ⇒ 第 5 条命中。
  （`git diff -M -C` 会报 `C100`，但 `gitutil.changed_files` 只用 `--find-renames`，**不产生 `C` 记录**。）
- **后果**：摘要仍是「1 个 change 目录」⇒ 配方**没有**保住它声称的意图（「同一 id 撞两个目录、两份都校验」）。
  可行的替代配方：`archive/x` 走**出生即归档**（要件与证据**全新**），**同时**在 base 已有、head 仍存在的
  `changes/x` 上改一个文件（`M`）⇒ 两个 target 都在。**建议**把配方改成这一条并补一条用例。

#### ✅ B2（**证伪成功，中危**）：`design.md:377` / `tasks.md:72` 把 `test_N6`（`:600`）列入「**不要误改**」是错的

- **声明**：`test_N6`（`:600`）断言的 `"没有任何 change 目录"` 在 D1 下**仍成立**。
- **复算**（`/tmp/r3cases2/n6_exact`，按测试源码逐字复刻的 diff 形态：base 上 archive 目标**已存在**、另一 active change
  在 base 上、feature 只搬它一个文件 + 改 `src/**`）：
  ```
  今天 changed_change_ids = []                       ← 现状（is_archive_move 把 old_path 排除掉）
  今天 archive_grant 命中 = []
  新口径 changed_change_ids（模拟器 D4）= ['another-change']
  ```
- **后果**：新口径下 `changes/another-change` 是 **active target** ⇒ `validate_change_dir` 通过（目录件齐）、
  但 `validate_review_manifests` 报「缺少 review manifest」⇒ stderr **不含**「没有任何 change 目录」⇒
  `tests/test_archive_awareness.py:621` 的断言 `"没有任何 change 目录" in err` **失守**。
- **这不是实现 bug，而是 spec 的**明确要求**：`spec.md:131-133`（与 `design.md:208-211`）写「把 active change 的**单个文件**
  移入一个**已存在**的归档目录……源 change `z` **不得因此静默逃检**」。⇒ **行为变化是对的，测试清单是错的**：
  `test_N6` 必须移进「必须改写」清单（断言改成「`another-change` 仍被按 active 契约校验」这一类）。
- **对照**：同段的 `test_N4`（`:577`）声明**成立**（该 diff 里没有任何记录带 `old_path` ⇒ target 集合为空 ⇒
  文案不变；今天的 25 条用例里它也确实绿）。

#### ✅ B3（**证伪成功，低-中**）：`m2` 仓内**模板骨架**被拒（已登记的误伤面，但被低估；且与排除 `proposal/design` 的理由自相矛盾）

- **构造**（`/tmp/r3cases/m2_template_stub`）：base 有 `changes/_template/{proposal,design,tasks}.md + specs/README.md + reviews/`；
  feature「出生即归档」一个 change，骨架由 `cp -r _template` 得来（`proposal.md`/`design.md` 改写，`tasks.md`/`specs/README.md`
  保持模板原样）。
- **实测**：`arrived=False`，判据 5 命中 **`tasks.md` 与 `specs/README.md`** ⇒ 一个**完全合法**的「照仓内模板建 change」
  流程被判红。
- **评价**：`design.md:150-156` 已把「被原样复制的 `tasks.md` 样板」登记为明写的误伤面 ⇒ 属**已知代价**，我**不**把它算作
  隐瞒。但两点值得写进文档：① 排除 `proposal.md`/`design.md` 的理由原文是「「stub 逐字节撞车」是**现实**误伤源」
  （`design.md:98-99`）——**这个理由对 `tasks.md` 一字不差地成立**（模板 skeleton 就是 tasks.md 撞车的最常见来源），
  排除集的选择与自己的理由是**不自洽**的；② 模板目录若在 `<changes_root>` **之内**（本构造）才撞车，放在仓内其它地方
  （如 `templates/`）不撞车 —— 建议在 `docs/gate.md §6` 明写「模板请放在 `changes_root` 之外」。

#### ❌ 证伪失败的「必须绿」形态（实测符合设计预期）

- 纯 move / move + 重建 manifest / 出生即归档（`r6`/`r7`/`r13`）⇒ 绿。
- move + **重度改写**：到达判定本身绿（只有 D4 的幽灵 id 那一层仍红，见 A4）。
- `design.md:139` 的 stub 误伤对照（`e11b`）⇒ 绿。
- `test_N2`（`:541`）的声明**成立**：假目录缺 `reviews/` ⇒ 第 2 条不成立 ⇒ 不是 target ⇒ `"没有任何 change 目录"` 仍在
  （今天的测试套件里它绿，且新口径下路径不变）。
- `test_deeper_events_file_is_not_read`（`:378`）仍绿：`archive/notes/` 只含 `sub/` ⇒ `c2=False` ⇒ 不是 target
  （`/tmp/cases/r12` 与 `r15` 的 `c2=False` 支持这一条）。

### C. 判据 1–5 的必要性与充分性（逐条，基于我自己的转写）

| # | 去掉它会怎样 | 它能不能被绕过 | 复算 |
|---|---|---|---|
| **1**（基准树无 entry） | 预存归档目录会被授予 ⇒ N2/N3/N4/N8 与 F1 的 copy 变体全回来 | **不能**（不带尾斜杠 `ls-tree` 对同路径 blob 返回 1 行 ⇒ 不授予） | `r10`/`r11`/`n6_exact` ⇒ `c1=F`；本次未找到反例 |
| **2**（head 是 tree + 含**全部**必需件） | F2/B1 的组织型目录假红回来（R2 的 B1 实测） | 作为**入口条件**不承重安全；**代价**是近失（near-miss）文案变差（见 E-2） | `r12`/`r15` ⇒ `c2=F`；多段名可判（下探针） |
| **3**（无来自 `archive/**` 的源） | 改名/copy+删源 白捡证据 | **挡得住** rename 与 copy+删源；对 copy（源不动）结构性失明（那是第 5 条的活） | `r8`/`r9` ⇒ `c3=F` |
| **4**（有源须名识别，**每一个**） | F3 的拒绝面消失；「名不认得的源混进到达组」不再被挡 | 不承重安全（它原本挡的 N6 已被判据 1 独立关掉）；**不误伤**常规 `<date>-<id>` 流 | `t471d` ⇒ `c4=T`；`t471e` ⇒ `c4=F`；`r6`/`r13` ⇒ `c4=T` |
| **5**（内容来源） | R1 的 F1 原版立刻复活（`r1` 唯一屏障就是它） | **能**，且成本极低：**A1**（报告挪出 `reviews/**`，证词逐字节复用）、**A2**（每个证据文件 +1 字节）、**A3**（`specs`/`tasks.md` 换形态）、**a4b**（源在 `changes_root` 之外时用 `git mv` 搬入，(a)(b) 双豁免） | 见 A 节 |

**小结**：第 1/3/4 条的必要性我复核成立且未能绕过；第 2 条达到了它宣称的目的（关掉 B1 假红）；
**第 5 条「必要但不充分」**——它是 F1 原版唯一的屏障（必要），但它**按路径前缀定义证据集**、**按逐字节定义「新内容」**，
于是「换个路径放证词」「每个文件动一个字节」「换个路径形态」三条**零/近零成本**的路都不在它的射程内。
R2 说它「只覆盖一个点」；现稿把它扩成了一**条线**（三段前缀 × 逐字节），但**没有扩到面**。

**旁证（作者侧复算的独立复核）**：`design.md §7.4` 的 18 个构造我**逐条复算，结论全部一致**
（`r1/r2/r3/r4/r5/r16/r19` ⇒ `arrived=False`；`r6/r7/r13` ⇒ `True`；`r8/r9` ⇒ `c3=False`；
`r10/r11` ⇒ `c1=False`；`r12/r15` ⇒ `c2=False`；`r21` ⇒ `False` 且 `archive/2026` `c2=False`；
`/tmp/e2e_partial` ⇒ `arrived=False` 且命中 **5** 份证据；E11 ⇒ `True`）。
⇒ 作者的复算在其**转写口径内**是自洽的；本轮的证伪项全部落在**转写口径之外**（证据集边界 / 逐字节语义 / D4 措辞）。

### D. 与源码事实核对（`文件:行号`）

**成立（逐条复核过的）**

- `contract.py:65` `is_archive_move`（`status != "R100"` 早退）/ `:85-116` `changed_change_ids` / `:97-101` `archived_sources`
  / `:119-147` `archive_grant` / `:145` 名识别 / `:150-189` `change_targets`（以**目录**为键、别名取并集）
  / `:211-213` 必需件「路径存在」判定 / `:252` manifest glob / `:282-300` `resolve_report_path`（**只要求目录内**）
  / `:333` 孤儿扫描 `reviews.rglob("*.md")` / `:391-394` `change_id ∈ accepted` / `:498-534` 哈希绑定 —— 行号无漂移。
- `checkcmd.py:105-119` 两条 stage 硬门 / `:121` `_require_change` / `:178-194` `_code_hits` / `:228-286` `_protected_writes`
  （`:255` `is_archive_move` 早退、`:266-275` 保护面判定）—— 行号无漂移。
- `gitutil.py:99-111` `changed_files` 用 `base...head` **三点** + `--find-renames`（**仅** `-M`，无 `-C`）
  / `:114-130` `_parse_name_status`：**`R`/`C` 记录带 `old_path`，其余记录 `old_path=None`** —— 这是 A4 的根因。
- `policy.py:76-92` `stale_exempt_paths` 末项 `archive/**`（暗房存在）/ `:110-117` `require_change_for` 与
  `required_artifacts` 都用 `or DEFAULT`（**`[]` 关不掉**）/ `:18-23` 不变集。
- `constants.py:87-90` `HASHED_ARTIFACTS` = `tasks.md` + `specs`；`:95-105` manifest 必填字段。
- `manifestcmd.py:33-48` `resolve_change_dir`（active 优先、否则 `archive/<name>`、按**磁盘**存在性）
  / `:136-142` **报告必须落在 `reviews/`**（**只有它强制**）
  / `:146-153` 每次 build 从磁盘**重算**全部哈希 / `:201-204` manifest 也硬编码写到 `<label>/reviews/`。
- `hashing.py:22-37` `sha256_tree`：文件 ⇒ 其字节哈希；目录 ⇒ 排序后逐文件 —— 「`specs` 是普通文件」因此能过哈希关。
- `manifest build` **不调用** `change_targets`（全文 grep 为空）⇒ `design.md:260-262` 的订正成立。

**不成立 / 需订正（新）**

1. **`design.md:95-100`（「一次搬运必然连它们一起搬……所以判据不漏」）与实测相反**（A1：真 CLI 绿）。
   同样的错误前提还出现在 `design.md:96-97`（「报告在 `reviews/` 下」）与 `design.md:161-162`（把它降级为低危边界）。
2. **`design.md:145-148` 的等价性论证不成立**（A2：不是「等价于自己写一份完整证据」）。
3. **`design.md:102` / `design.md:322`（§5.1 第 2 条）对「move 带内容改动」的覆盖过宽**（A4：`D`+`A` 档仍红）。
4. **`design.md:202`（D4 的排除键）与 `spec.md:206-207` 漏了 `D` 侧记录的 `path`**（A4）。
5. **`design.md:377` / `tasks.md:72` 对 `test_N6` 的「不要误改」判定为假**（B2）。
6. **`design.md:363-366` / `tasks.md:57-60` 的 `:494` 改写配方不成立**（B1）。
7. **`design.md:358` 写「必须改写的既有测试（**3 条**）」，紧接着列了 **4** 项**（`:274`/`:494`/`:109`/`:49`+A 节）；
   `tasks.md:53-67` 列同样的 4 项且未给数字** ⇒ 计数与列表不一致（低危，文档）。
8. **`design.md:130` / `:394` 的「`specs` 换成同名普通文件 ⇒ 拒 ✓」对**内容版**为假**（A3-a3b），
   且现稿对「`tasks.md` 是目录」这一形态**没有条款**（A3-a5）。

### E. 低危观察（不阻塞）

1. **证据集把 `reviews/**` 写死，而 manifest 的查找走 `policy.review_manifest_glob`**：两者在自定义 glob 下分叉
   （`check` 用 `pol.review_manifest_glob` 找 manifest，`contract.validate_review_manifests:252`）。
   实测探针（`/tmp/e2e_r3_customglob` 的构造脚本）：把 glob 改成 `ev/*.manifest.json` 后，
   **`manifest build` 直接拒绝**——`manifest build：report_path='ev/grill-review.md' 必须落在 reviews/ 下`
   （`manifestcmd.py:136-142`），且它自己写 manifest 也硬编码 `reviews/`（`:201`）。
   ⇒ 该配置本就不可用（**这是既有不一致，非本 change 引入**）；但判据 5 的证据集若从
   `HASHED_ARTIFACTS` + `review_manifest_glob` **推导**而不是硬编码三段路径，会更稳。**（自定义 glob 下的端到端未实测）**
2. **第 2 条收紧的代价：近失（near-miss）文案变差**。「真的想归档但少写一件必需件」（例如报告放在 change 根而不是
   `reviews/`、或没有 `design.md`）在一版口径（≥1 件）下是 target ⇒ 报「**缺少必需件 `reviews`**」（可定位）；
   现口径下**不是** target ⇒ `_require_change` 命中，报的是「本次 diff 里**没有任何 change 目录**……补一个 change 目录
   （或补上那条归档 move）」——**对已经建了归档目录的接入方是误导性文案**。
   `design.md:391`（N7）与 `spec.md:106-108` 把这写成预期行为，但只论证了「组织型子目录」那一侧；
   近失那一侧没有任何 finding 会点名缺的那一件。建议：`_require_change` 的文案在「`archive/` 下存在缺件目录」时
   补一句提示（或把「最近缺件的归档目录」列出来）。
3. **空文件豁免的语义**：豁免按 **head 侧 blob 为 0 字节**判（`spec.md:64`）⇒ 把一份借来的文件**清空**同样逃逸判据 5；
   但清空后借用内容也没了，等价于自己写一个空文件 ⇒ **无实际收益**（推演，未实测；不建议花力气）。
4. **`design.md:314-315`（R7）的「必须每一份被复制的证据文件都**重写**」措辞**与判据实际强度不符（见 A2）。
5. **`—`（§5.3 末两行）「归档时顺带改 change id ⇒ 红」**：我复核成立（判据 4 名识别不满足），
   但注意**今天也红**（`archive_grant` 的名识别同样不满足）⇒ 它是「明写的拒绝面」，不是新引入的拒绝面，
   这一点 §5.3 的措辞（「**当前设计下红**」）容易读成新引入。建议补一句「今天亦红」。
   实测（`/tmp/r3cases2/f3_change_id`，`git mv changes/old-id archive/2026-10-15-new-id` + 改 `src/**`）：
   `contract.changed_change_ids(...) == []`、`archive_grant` 零命中 ⇒ 今天即报「没有任何 change 目录」。
6. **`archive/` 下直接子项是 blob 的形态**（`archive/foo` 是文件、head 里也是文件）：模拟器把它标成
   「n/a（不是候选）」，现稿没有条款；不构成绕过（不会授予），但值得在实现时明确「候选只取 tree」。

---

## 未验证项

1. **接入方的具体数字**（`proposal.md:30-32` 的 33 文件全 `A`、`R068/R069/R070/R090`、16 文件 11 项、「120 个归档目录」）
   —— 另一个仓的提交，本工作区**无法复算**；我只复现了**方向**（`git mv` + 改被搬文件 = `R<100`；`cp` = 全 `A`）。
2. **现稿判据的「实现」不存在**：A1–A4 的**到达判定那一半**来自我按文本逐字转写的 `/tmp/r3sim.py`。
   若真实现的转写口径不同，结论要重算——**最敏感的四处**：① 证据集是否含 `specs` 本体（A3-a3b）；
   ② 是否把 `C` 记录算作 (b)（现稿说「改名记录」+ `gitutil` 只用 `-M` ⇒ 不算）；
   ③ 「空文件」按 head blob 字节数还是按 worktree；
   ④ D4 是否把 `D` 侧 `path` 纳入排除（A4）。**e2e 里证据门那一半是真 CLI，到达那一半不是。**
3. **浅克隆 / partial clone 下「`merge-base` 成功但 `ls-tree` 失败」这一独立面**：仍未复现（R1/R2 同）。
4. **merge commit 形态**：未取得可判定结论（沿用 R2 的遗留）。
5. **自定义 `policy.review_manifest_glob` 下的端到端**：只做到「`manifest build` 拒绝该布局」这一步（E-1）。
6. **`policy.required_artifacts` 覆写成多段名**：我只验证了「多段名在 `ls-tree -r <head> -- <dir>/` 的输出里可见」
   （探针：`ls-tree HEAD -- <dir>/reviews/.gitkeep` ⇒ `100644 blob …`），**未**跑端到端；`design.md:81-82` 的说法方向正确。
7. **大仓（120 个归档目录）下「出生即归档」的逐字节撞车概率**（`tasks.md:127` 的 4.6）：未测。
8. **A2/A4 的现实频率**：接入方是否存在「整体重写 `tasks.md`/`specs`」与「报告放 `reviews/` 之外」的流程 —— 无法从本仓判定。

---

## 必须修改项

> 每条附最小复现与证据。**M1/M2/M3 同根（判据 5 的证据集与「新内容」定义），建议一起改。**

- **M1（高危）：判据 5 的证据集必须覆盖**报告**，或者必须把「报告落在 `reviews/` 下」变成 `check` 的硬约束。**
  - 证据：`python3 /tmp/r3_e2e.py`（A1 段）⇒ `check 退出码 = 0`、`check：通过 ✓`；三份报告与受害者
    `git hash-object` **逐字节相同**；`/tmp/r3sim.py` 判 `arrived=True`（c1..c5 全 T）。
  - 二选一（**推荐 (i)**）：
    (i) 证据集从「三段路径前缀」改成**由数据推导**：`HASHED_ARTIFACTS` 覆盖的 artifact + `policy.review_manifest_glob`
    命中的 manifest + **每份 manifest 的 `report_path` 解析出的那个文件**（`contract.resolve_report_path` 已有现成实现），
    再加上 `reviews/**`。这样「报告换路径」不再出圈，且不引入新的误伤面（报告本来就必须被 manifest 绑定）。
    (ii) 在 `check` 里补一条「报告 SHALL 落在 `<change>/reviews/` 下」（把 `manifestcmd.py:136-142` 的既有约束
    搬到 check）——但它会与「`check` 只要求目录内」的既有宽松面冲突，**且是既有行为变化**，需要单独登记。
  - 无论选哪个：`design.md:95-100`（「所以判据不漏」）与 `design.md:161-162`（低危边界）**必须重写为一致口径**。

- **M2（高危）：把「新内容」的口径与「机械搬运」的目标对齐，或**显式降级**目标并删掉伪等价论证。**
  - 证据：`python3 /tmp/r3_e2e.py`（A2 段）⇒ `check 退出码 = 0`（对**每一个**证据文件追加一个字节 +
    真 CLI 重建 manifest，报告正文其余字节完全复用）。
  - 最小要求（不改判据也要做）：**删掉 `design.md:146-148` 的「等价于自己写一份完整证据（每个文件都得动）」**，
    改成事实陈述：「判据 5 只挡**逐字节**复用；把每个证据文件动一个字节再重算 manifest 即绕过，
    成本是一个 `for` 循环」。并把 `proposal.md:66`、`design.md:313-315`、`specs/…/spec.md:54-58` 的措辞同步。
  - 若要把目标真正兑现（拦机械搬运），可行方向的**代价**必须实测：例如要求「A 的证据文件**不得与 base 里
    任何 change 目录下的同**相对路径**文件逐字节相同**（即 R2 的指纹形态，但**按相对路径**且**逐文件**）」——
    这会把「整份复制 + 原地不动」重新盖住，而对「把每个文件都改写」仍然失守（那才是真·自己写）；
    误伤面（stub、模板、`PASS\n`）需要 §8 Q4 的实测数据（`tasks.md:127`）才能定。**这属用户拍板（见 OQ-1）。**

- **M3（中危）：判据 5 的证据集必须对「同一路径的另一种形态」有说法（`specs` 是文件 / `tasks.md` 是目录）。**
  - 证据：`python3 /tmp/r3sim.py /tmp/r3cases2/a3b_specs_file_pristine main HEAD` ⇒ `arrived=True`（借用 spec 逐字节保留）；
    同命令对 `/tmp/r3cases2/a5_tasks_as_dir` ⇒ `arrived=True`（`tasks.md` 目录里塞逐字节搬来的 spec）。
  - 修法：证据集按**规范化后的目录前缀**取（`<A>/specs` 本体与 `<A>/tasks.md` 本体也算证据文件），
    并在 `spec.md:40-41` 补一句「`specs` / `tasks.md` 为普通文件时，该文件自身即证据文件」。
    同时把 `design.md:130`/`:394`（N10）的「`specs` 换成同名普通文件 ⇒ 拒 ✓」改成它**实际**成立的条件。

- **M4（中危）：D4 的排除口径补上 `D` 侧记录的 `path`。**
  - 证据：`python3 /tmp/r3sim.py /tmp/r3cases2/m3_move_rewrite_tasks_only main HEAD` ⇒ `arrived=True` 但
    `active ids = ['z']` ⇒ 报「`openspec/changes/z`：change 目录不存在」；根因见 `gitutil.py:114-130`
    （`D` 记录无 `old_path`）。
  - 修法：`design.md:202-211` 与 `spec.md:206-209` 的措辞改成「该记录的 `old_path`（改名），以及 `D` 侧记录的 `path`，
    若其所在源目录在 head 树里已不存在」。并在 §5.1 第 2 条补一条**重度改写**用例（`tasks.md` / `specs` 整体重写）。

- **M5（中危）：修 §5.2 / `tasks.md 2.6b` 的测试清单（两处判定为假 + 一处计数）。**
  - 证据：`/tmp/r3cases2/n6_exact`（今天 `changed_change_ids=[]` vs 新口径 `['another-change']`）⇒ `test_N6`（`:600`）
    **必须改写**（且理由正是 `spec.md:131-133` 要求的「不得静默逃检」）——从「不要误改」移入「必须改写」。
  - 证据：`/tmp/r3cases2/t494b_regression_recipe` ⇒ 配方产出的 `archive/x` **不是** target（判据 5 命中 3 份）
    ⇒ `:494` 的改写配方要换成 B1 给的替代配方。
  - `design.md:358` 的「3 条」应为「4 条（含 `:49` 的助手改写）」。

- **M6（低-中）：把「`changes_root` 之外的现成证据」这条边界的**后果**写清，并承认 (b) 是自证豁免。**
  - 证据：`python3 /tmp/r3sim.py /tmp/r3cases2/a4b_outside_root main HEAD` ⇒ `arrived=True`（10 条 `R100`，
    `docs/shipped/2026-09-30-old/**` → `archive/2026-10-15-new/**`，**逐字节**）。即：源在 `<changes_root>` 之外时，
    (a) 与 (b) **同时**豁免同一份内容 —— 这不是「低危边角」，而是判据 5 的**完全旁路**。
  - 建议措辞：「判据 5 的效力**完全依赖** `<changes_root>/**` 是「唯一存放 change 证据的地方」这一前提；
    一旦证据的字节在 base 里另有副本（`changes_root` 迁移、仓内镜像、`docs/shipped` 发布副本），
    把副本 `git mv` 进来即逐字节复用 ⇒ **不授予**这条目标在这些形态下失效」（并在 `docs/gate.md §6` 登记）。

- **M7（低）：`test_deeper_events_file_is_not_read`（`:378`）的注释**（`design.md:378` 与 `tasks.md:72` 说「注释应更新」）
  在现稿里**仍未更新**（测试文件里没有对应改动，且本 change 不改 `tests/`）—— 记在这里以免实现期漏掉。

---

## Open Questions

> 只放**真需要用户拍板**的。能由代码 / 安全属性定案的都已移出（见「必须修改项」与 D 节）。

**OQ-1（= `design.md §8 Q4` 的**重问**，因为现稿的两条「成本」论证都已被证伪）第 5 条的强度取哪一档？**
- 具体例子（同一份**真审阅报告**，三种处置；成本都是分钟级脚本）：
  - **(a) 现稿**：只挡「逐字节 + 固定路径形态」的复用 ⇒ A1/A2/A3 三条都绿（真 CLI 已实测两条）。
  - **(b) 证据集 = change 目录下**全部**非空文件（除 `proposal.md`/`design.md`）**：A1/A3 被关掉（报告换路径也进集），
    A2（每个文件动一个字节）**仍绿**；代价：误伤面比现稿大（`reviews/*.manifest.json` 与任何模板/样板文件都进集）。
  - **(c) 承认它是「只挡整份逐字节复制」**（= 删掉 A2/A3 那一半宣称，把能力边界写成一句话，并把
    `design.md:102` 的「两只症状同一刀切掉」收敛为「出生即归档 + R<100 的 move」）。
- **我的判断**：(a) 与 (c) 自洽，(b) 是中间档但**只解决一半**（A2 那种「每个文件动一个字节」是**根本性**的：
  只要判据是逐字节的，「全部改一遍」就永远逃逸——而那不是伪造，因为**内容没变**）。
  ⇒ 真正要拍板的是：**「把借用来的证据每个文件改一个字节」算不算违规**。若算，(a)(b) 都不够；
  若不算，就该按 (c) 把宣称收敛到能力（并把「防伪造」的边界明写在 `docs/gate.md §6`）。
  **我倾向 (c)+M1/M3**（先把「报告换路径」这类**真的零成本**路径关掉，再明确承认逐字节判据的天花板），
  但这一条**取决于用户对「白捡证据」的威胁模型**（是防「顺手 copy」还是防「有意的低成本洗白」）。

**OQ-2（= `design.md §8 Q1`，保留、未变）：归档目录名「必须认得源 id」这条守卫是否保留？**
- 本轮的新证据：判据 4 的「每一个源」口径我实测**是有效的**（`t471e` ⇒ 整个到达被拒），且它对**常规** `<date>-<id>`
  流程不误伤（`t471d`/`r6`/`r13` 全绿）⇒ 无论裁 (a) 保留还是 (b) 删除，**都不影响本轮的证伪项**，可直接随用户裁。

**OQ-3（= `design.md §8 Q2`，保留、未变）：`archive/**` 的 stale 豁免（暗房）本次收窄还是另立？**
（与本 change 正交；现稿已把对称性不变量限定到「证据门槛」维度，故不阻塞。）

**OQ-4（= `design.md §8 Q3`，保留、未变）：嵌套归档布局 `archive/2026/<name>/` 本次是否支持？**
（现稿 (a) 不支持 + 现口径报「没有任何 change 目录」，我复核 `r12`/`r21` 与今天**逐字相同**。）

---

## 收敛结论

**不收敛。**

**新的、可复算的证伪项（最小复现；全部在 `/tmp`，未改仓内任何文件）**：

```bash
cd /home/happy/wl-wt/archive-arrival-recognition      # ⑤④ 里的 `src` 取相对路径

# ① A1（高危，真 CLI 绿）：报告挪出 reviews/** ⇒ 判据 5 失明，证词逐字节复用
python3 /tmp/r3_e2e.py            # 看 "A1 报告逐字节挪出 reviews/" 段 → "check 退出码 = 0 / check：通过 ✓"
git -C /tmp/e2e_r3_a1 diff -M --name-status main HEAD | grep -E 'grill-review|building-review'   # A（不是 R）
for f in grill-review.md grill-adversarial.md building-review.md; do
  git -C /tmp/e2e_r3_a1 hash-object openspec/changes/archive/2026-09-30-old/reviews/$f
  git -C /tmp/e2e_r3_a1 hash-object openspec/changes/archive/2026-10-15-stub/$f        # 两个 sha 相同
done

# ② A2（高危，真 CLI 绿）：每个证据文件 +1 字节 + manifest build 重算 ⇒ 判据 5 零命中
python3 /tmp/r3_e2e.py            # 看 "A2 每个证据文件 +1 字节" 段 → "check 退出码 = 0 / check：通过 ✓"

# ③ A3（中危，模拟器）：specs 换形态 / tasks.md 做成目录 ⇒ 借用内容逐字节保留仍 arrived=True
python3 /tmp/r3sim.py /tmp/r3cases2/a3b_specs_file_pristine main HEAD   # arrived=True c1..c5 全 T
python3 /tmp/r3sim.py /tmp/r3cases2/a5_tasks_as_dir        main HEAD   # arrived=True c1..c5 全 T

# ④ A4（中危，模拟器 + 今天行为对照）：D+A 的幽灵 active id 仍在
python3 /tmp/r3sim.py /tmp/r3cases2/m3_move_rewrite_tasks_only main HEAD   # arrived=True 但 active ids = ['z']
python3 -c "import sys;sys.path.insert(0,'src');from witnessloop import contract,gitutil;\
print(contract.changed_change_ids(gitutil.changed_files('/tmp/r3cases2/m3_move_rewrite_tasks_only','main','HEAD'),'openspec/changes'))"

# ⑤ B2（中危）：test_N6（:600）的「不要误改」判定为假
python3 /tmp/r3sim.py /tmp/r3cases2/n6_exact main HEAD   # 新口径 active ids = ['another-change']（今天 = []）

# ⑥ B1（中危）：§5.2 给 :494 的改写配方产出的到达目录不是 target
python3 /tmp/r3sim.py /tmp/r3cases2/t494b_regression_recipe main HEAD   # arrived=False（第 5 条命中 3 份）、1 个 target

# ⑦ M6（低-中）：changes_root 之外的现成证据 git mv 进来 ⇒ 逐字节复用且判据 5 零命中
python3 /tmp/r3sim.py /tmp/r3cases2/a4b_outside_root main HEAD   # arrived=True（10 条 R100）
```

**负面证据（同样有价值）**：R2 的 18 个构造我**独立转写后逐条复算，与 `design.md §7.4` 一致**；
纯 move / move+重建 manifest / 出生即归档三条「必须绿」**全部绿**；判据 1/3/4 我未能绕过；
R2 的 B1 假红**确已修好**；`:471` 的「每一个源」声明、`:541` 的「不要误改」声明、`:378` 的稳定性、
`design.md:139` 的 stub 误伤对照 —— 这几条我复核**成立**。

**给作者的收敛判据**：M1–M7 落库（M1/M2/M3 需要**真的改判据或改口径**，不是改措辞）之后，再跑一轮 R4；
R4 若只剩措辞项即收敛。

---

## 附：评审期间文本被并发改写（**非本审阅者所为**，仅供下一轮 R4 定位）

- **事实**（`git status` / `git diff --numstat`，本审阅者**未**编辑 `design.md`）：本报告落盘时
  `openspec/changes/archive-arrival-recognition/design.md` 处于**已修改未提交**状态
  （`118 insertions(+), 30 deletions(-)`，mtime `2026-10-15 18:06`，且评审期间**仍在增长**）；
  `git status` 里除本报告外**只有**它一个改动项（`src/` / `tests/` / 其它 change 文档均未动）。
- **后果**：**本报告的行号与引文对应的是会话开始时读到的文本**（`design.md` 575 行、commit `302dd31`）；
  新文本里 `§2 D1 第 5 条` / `§5.2` / `§5.3` 的段落已被重写，**行号会漂移**。
- **就我通读到的 diff 而言**，新文本似乎在**正面处置**本报告的 M1（`Ev(A)` 改为由 `HASHED_ARTIFACTS` +
  `review_manifest_glob` + `report_path` 推导）、M3（artifact 路径「整体」：是文件就它自身、是目录就其下全部文件）、
  M4（D4 增加 `D` 侧 `path` 排除键 + §5.1 第 2b 条用例）、M5（`:600` 移入「必须改写」、`:494` 换成本报告 B1 给的替代配方、
  「3 条」改「4 条」）、M6（`changes_root` 之外的副本升格为「完全旁路」并写明 (a)(b) 双豁免）、M2（把
  `design.md:146-148` 的伪等价论证**删除**，改写成「**能力天花板**」明写，A2 档**不要求红**）、以及 E-2（近失文案）。
- ⚠️ **但这些改动我**没有**对抗验证过**（本轮只审了旧文本）⇒ **R4 至少应复算这三处**：
  ① 新的 `Ev(A)` 定义下，**手写 manifest 的 `report_path` 指向 change 目录内的任意路径**是否还能构造出圈
  （特别是「报告正文与 `report_path` 目标分离」的组合）；
  ② 「A2 档不要求红」这条**文档化天花板**是否与 §8 Q4 的取舍一致（若用户裁「不接受」则全案要重做）；
  ③ 新的 D 侧排除键在「`D` 记录的 `path` 落在**仍在 head** 的源目录下」时**不得**排除（否则会重开 `test_N6` 那条静默逃检）。
