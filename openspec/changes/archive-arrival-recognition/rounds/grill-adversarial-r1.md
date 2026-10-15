# Grill-ADVERSARIAL: archive-arrival-recognition 对抗验证（独立零记忆审阅者）

> 任务：**证伪** `design.md` 的 D1（四条到达判据）与 D2–D7。证伪成功写构造，证伪失败写「试过什么」。
> 硬约束：不向用户提问、只写本文件、不改 `src/`/`tests/`/其他文档。

## Reviewer

**独立零记忆**：本对话不携带该 change 任何历史；设计稿里的「实测」「文件:行号」「今天成立」一律当**待验证断言**，可复算的一律复算。

**读了**：本 change 的 `proposal.md` / `design.md` / `tasks.md` / `specs/archive-awareness/spec.md` / `reviews/grill-design.md`；前身 `openspec/changes/archive-awareness/`（proposal / design / spec delta）；源码 `src/witnessloop/{contract,checkcmd,gitutil,policy,paths,manifestcmd,constants}.py`；测试 `tests/test_archive_awareness.py` / `tests/helpers.py` / `tests/conftest.py`。

**跑了**（命令 + 结论，逐条可复算）：

1. `uv run pytest tests/test_archive_awareness.py -q` → **25 passed**（当前基线绿）。
2. 干净 scratch 仓（`/tmp/arr2..arr9`，全部 `git init` 过）复算 `git diff --name-status -M <base> <head>` 在五种构造下的记录状态：归档目录**纯改名**（全 `R100`，`old_path` 落在 `archive/**`）；**改名 + 重度改写一个非哈希文件**（该文件变 `D`+`A`，其余仍 `R100`，`old_path` 仍在 `archive/**`）；**改名 + 重度改写 `tasks.md`**（`tasks.md` 变 `D`+`A`，其余仍 `R100`）；**move 出 active + 重建 manifest**（`R<100`，`old_path` 落在 `changes/<id>/**`）；**把既有归档目录的整份内容 `cp` 到新名**（全 `A`，**没有任何 rename 记录**）。
3. 复算 `gitutil.changed_files` 的三点语义（直接读 `src/witnessloop/gitutil.py:104-106`）+ `checkcmd.py:47-70` 的 base 解析调用链。
4. 写了一个**一次性** D1 四条件模拟器（`/tmp/sim_d1.py`，只 import 现成的 `gitutil`/`paths`，**未碰 `src/`、未碰仓内任何文件**），对 8 个构造算 `arrived=`（含 `c1..c4` 逐条）。
5. 端到端 proxy：用真 CLI（`uv run python -m witnessloop init/manifest build/check`）在 `/tmp/e2e` 造「完整证据的 active change」，再 `cp -r` 到新名 + 只改 manifest 的 `change_id`/`head_sha`/`base_sha` 三个字段，跑 `check`。
6. 直调 `contract.is_archive_move` / `contract.changed_change_ids` 复算保护写豁免面与幽灵 id 面。
7. `grep` 核对 tasks / design / spec 三份文档间的口径。

---

## 对抗结论

### A. 证伪「找绕过」——**成功 1 条（F1），失败 4 条**

#### ✅ F1（**证伪成功，高危**）：**COPY 变体绕过 D1 条件 3** —— 该变红的 PR 变绿

- **构造**（`/tmp/arr7` 实测）：
  - base 树：`openspec/changes/archive/2026-09-30-old/{proposal,design,tasks}.md + specs/ + reviews/{grill-review.md, grill.manifest.json}`（一份**证据齐全**的旧归档 change）。
  - head 树：**`cp -r` 整份到 `archive/2026-10-15-new/`（旧的 `archive/2026-09-30-old/` 原封不动保留）**，只 `sed` 改 `grill.manifest.json` 里的 `change_id`，并改 `src/app.py`。
- **期望**：应红（这是「白捡现成证据」，与 D1 第 3 条要挡的 N8 同一威胁）。
- **实测**：
  - `git diff --name-status -M <base> HEAD`：`archive/2026-10-15-new/**` **全是 `A`**，`archive/2026-09-30-old/**` **完全不在 diff 里**（`-M` 只配对「删+增」，源文件还在 ⇒ 不配对成 rename）。
  - D1 模拟器：`archive/2026-10-15-new/  arrived=True (c1=True c2=True c3=True c4=True)` ⇒ 条件 3 **看不见**（组内没有任何 `old_path` 落在 `archive/**`，因为记录全是 `A`、无 `old_path`）；条件 4 也不触发（无 `changes/<src>/` 源）。
  - 端到端 proxy（`/tmp/e2e`，真 CLI）：把一份**逐字节相同**的任务/spec/报告复制到新名、**只改三个 JSON 字段**（`change_id`、`head_sha`、`base_sha`）后，`check` **通过 ✓**——`hash` 绑定（`tasks_hash`/`spec_hash`/`report_hash` 因字节未变而全部成立）、`reviewer≠author`、grill 正文判据、三条 stage 门**全部满足**。
- **结论**：D1 第 3 条**只关了 rename，没关 copy**。而设计给第 3 条写的理由（`design.md:234-235` N8：「把旧归档目录改名 ⇒ 白捡一份现成证据」）**在 copy 变体下仍然成立**：一个只改 `src/**`、复用别人现成证据、仅手改两个 manifest 字段的 PR **变绿**。这是本设计「到达方式不设限」所依赖的那条安全守卫（「不得白捡既有证据」）的**真实缺口**。
  - 附注：`-M`（现用）看不到；我实测连 `-M -C` 也没看出来（因为 `-C` 默认只从「被改/被删」的文件找副本，旧目录未被改），要 `--find-copies-harder` 才可能看到——所以**不建议**靠「加 `-C`」补，建议改成**语义判据**（见「必须修改项」）。

#### ❌ 证伪失败 A2：**把既有归档目录 `git mv` 改名**（N8 原版）
- 构造（`/tmp/arr2`、`/tmp/arr3` S1）：base 有 `archive/2026-09-30-old/`（证据齐），head 只做 `git mv archive/2026-09-30-old archive/2026-10-15-new` + 改 `src/**`。
- 期望：不授予（红）。实测：`git diff -M` 全 `R100`、`old_path` 落在 `archive/**`；模拟器 `arrived=False (c3=False)`。**条件 3 生效。**
- 加固测试：即使**重度改写其中一个非哈希文件**（`proposal.md`）把该文件变成 `D`+`A`，**其余 `R100` 文件仍带 `archive/**` 的 `old_path`** ⇒ 条件 3 仍命中（`/tmp/arr-exp` E2）。要把**全部**文件都变成非 rename，就必须改写 `tasks.md`/`specs/`（**它们被 manifest 哈希绑定**）⇒ 哈希崩 ⇒ 红。**⇒ 该路证伪失败。**

#### ❌ 证伪失败 A3：**先「洗」到 active 再交（content laundering）**（推演，未实测）
- 推演：若 base 里**同时**把这份证据放在一个**非 `archive/` 非 `changes/<id>/` 的路径**（如 `vendor/x/**`，与 `archive/old/**` 字节相同），`git` 的 rename 配对可能挑 `vendor/x` 作源 ⇒ `old_path` 不落 `archive/**`、条件 3/4 都不触发。
- 但：这要求**攻击者能改 base 树**（把证据预先复制到 `vendor/`），远超「误用」的威胁模型，且删 `archive/old/**` 的 manifest 记录仍落在不变集保护面（需要事件）。**不构成现实绕过**，列此仅为穷尽。

#### ❌ 证伪失败 A4：**预存归档目录 + 新增文件（N3）**
- 构造：base 有 `archive/2026-09-30-old/`，head 往其中**新增**一个文件 + 改 `src/**` ⇒ 模拟器 `c1=False ⇒ arrived=False`。**条件 1 生效。**

#### ❌ 证伪失败 A5：**只改 `src/**`、零 change 目录（N1）**
- 无任何 `archive/<name>/` 候选 ⇒ 模拟器返回「无候选」⇒ 不授予。**红。**

### B. 证伪「找假阴性」——**成功 2 条（F2 / F3）**，两条「必须绿」的形态**实测绿（证伪失败）**

#### ✅ B-good-1（**本 change 存在的理由之一，实测绿**）：**出生即归档（form i）**
- 构造（`/tmp/arr2` E4）：base 无任何 change；head 全 `A` 新建 `archive/2026-10-15-foo/**` + 改 `src/app.py`。
- 实测：`git diff` 全 `A`；模拟器 `archive/2026-10-15-foo/ arrived=True (c1..c4 全 True)`。**⇒ 这一路在 D1 下拿得到资格。**

#### ✅ B-good-2（**本 change 存在的理由之二，实测绿**）：**同一次 move 内带内容改动 / 重建 manifest（form ii）**
- 构造（`/tmp/arr2` E6、`/tmp/arr3` S3）：base 有 active `changes/z/`（含 manifest）；head `git mv changes/z archive/2026-10-15-z` **且**重建 `grill.manifest.json`（该文件变 `D`+`A`，其余 `R100`）+ 改 `src/**`。
- 实测：`old_path` 落在 `changes/z/**`（**不是** `archive/**`）⇒ 条件 3 不命中；条件 4：`src=z`，`2026-10-15-z` 满足 `endswith("-"+z)` ⇒ 命中。模拟器 `arrived=True`。**⇒ 这一路拿得到资格。**

#### ✅ F2（**证伪成功，中危——引入新的假阴性类**）：**`archive/` 下的「非 change 直接子目录」被判为到达**
- 构造（`/tmp/arr3` S4）：base 无 `archive/2026/`；head 新建 `openspec/changes/archive/2026/10-15-foo/{proposal.md,...}`（**按年份组织归档**）+ 只改文档。
- 期望：不该把 `2026` 当成一个 change（今天不会：`changed_change_ids` 对 `archive/**` 一律排除、`archive_grant` 也不授予 ⇒ 无 target）。
- 实测：模拟器 `archive/2026/  arrived=True (c1..c4 全 True)` ⇒ D1 会把 `2026` 认作「本次到达的 change」⇒ `validate_change_dir('2026')` 报「缺少必需件 proposal.md / design.md / tasks.md / specs / reviews」⇒ **红**。
- **该形态在本仓既有测试里已存在**：`tests/test_archive_awareness.py:378` `test_deeper_events_file_is_not_read` 就造了 `openspec/changes/archive/notes/sub/workflow-events.jsonl`（其注释明说「把 `notes` 当成一个『归档 change 目录』」）。今天它不产生 target；**D1 之后 `archive/notes/` 会成为一个到达 target 并被判缺件**。同款：`archive/templates/`、`archive/.gitkeep` 所在的目录、任何组织型子目录。
- **结论**：`grill-design.md` 的 **Q4** 正是这条，但**当前 design 既没回答、也没保留**（`design.md §8` 只剩 Q1–Q3，`§2.5` 也没有）。这是一条**被丢掉的真实假阴性**。

#### ✅ F3（**证伪成功，低-中危——未列明的拒绝面**）：**归档时顺带改 change id**
- 构造（`/tmp/arr6`）：base 有 active `changes/old-id/`（含 files）；head 做 `git mv changes/old-id archive/2026-10-15-new-id`（全 `R100`）+ 改 `src/**`。
- 实测：`git diff` 全 `R100`、`old_path` 落在 `changes/old-id/**`（不是 archive）⇒ 条件 3 不命中；条件 4：`src=old-id`，`2026-10-15-new-id` **既不等于 `old-id`、也不 `endswith("-old-id")`** ⇒ `c4=False` ⇒ `arrived=False` ⇒ **红**。
- **结论**：D1 会拒掉「归档改名 + change id 改名同时发生」。是否合法可争，但这是 **design §5.3 否定面表里没列、规范 Scenario 里也没写**的一类拒绝。至少要写明口径。

### C. 证伪「条件 3 / 条件 4 的必要性与充分性」

- **条件 3 必要性**：成立——去掉它，N8（rename 既有归档目录）确实变绿（`design.md:235` 的推理我复核成立，同一威胁在 F1 的 copy 变体下**已实际发生**）。
- **条件 3 充分性**：**不成立**——见 F1（copy 绕过）。这是本报告的最高优先级结论。
- **条件 4 误伤**：**会**——F3（归档时改 id）被误伤；另外 `endswith("-" + src)` 只在「归档目录名 = `<date>-<id>` 或 `<id>`」时成立，设计已声明「不改 `<date>-<id>` 约定」，所以**常规接入不受影响**（B-good-1/2 实测绿）；误伤面限于「id 本身在归档时被改」这类非典型流。
- **条件 4 不承重**：**完全正确**——条件 4 原本要挡的「单文件 move 进**已存在**归档目录」（N6）已被**条件 1** 独立关掉（我实测 `git mv changes/z/notes.md archive/y/notes.md` 时目标目录在 base 存在 ⇒ 条件 1 不成立）。所以条件 4 现在**只剩命名约定作用**，这与 `grill-design.md` 的 Q2 判断一致。

### D. M3 技术前提（**成立**）

- `gitutil.changed_files` **确为三点**：`src/witnessloop/gitutil.py:104-106` 传的是 `f"{base}...{head}"`（`--name-status -z --find-renames`）。**⇒ 设计 §1.1 的断言成立。**
- `check` 调用链上传入的 `base`：`checkcmd.py:47` `base = gitutil.resolve_base(root, args.base)` → `:54` `changed_files(root, base, head)`。`resolve_base`（`gitutil.py:54-71`）返回**显式参数 → `WITNESSLOOP_BASE_REF` → `origin/<GITHUB_BASE_REF>` → 主干**。所以「到达判定用 `merge-base(base, head)`」与 diff 成员**同源**，**结论在真实调用路径上成立**。
- **有没有更简单/更正确的做法**：**没有更好的**——三点 diff 只说哪些**路径**变了，说不出「某个**目录前缀**在 base 里有没有 entry」（N3：预存目录里加文件也是 `A`），所以必须显式查基树；而查基树必须先给一个 revision 名，`git merge-base` 是唯一自然来源。**⇒ 设计正确。**
- **一个边界**：`changed_files` 在 merge-base 求不出时（互不相关历史）**已经抛 `GitError`**（`gitutil.py:107-110`），`check` 在 `checkcmd.py:55-57` **已经 fail-closed 退出**。所以 D7 说的「基树读不出来 ⇒ 报 finding」的**独立**触发面很窄——只剩「merge-base 成功但对 base tree 对象 `ls-tree` 失败」（浅克隆 / partial clone / filtered）。**⇒ 设计的方向对，但覆盖面比它暗示的窄。**

### E. 低危观察（不阻塞）

- **`archive/<name>` 在 base 是「文件」而非目录时，条件 1 是盲的**（`/tmp/arr8` 实测）：base 有 blob `openspec/changes/archive/foo`，head 变成目录 `archive/foo/…`。
  - `git ls-tree -r <mb> -- openspec/changes/archive/foo/`（带尾斜杠）⇒ **空**（blob 在 `archive/foo`，不在 `archive/foo/` 下）⇒ 条件 1 判「不存在」⇒ `arrived=True`。
  - 不构成绕过（该目录仍要凑齐证据），但条件 1 的措辞应明确为「该路径在 base **完全没有 entry（blob 或 tree）**」，别写成「前缀下没有 tree entry」——后者对同路径 blob 放行，也正是 `grill-design.md` R-C 担心的「第一段可能是文件」。
- **前身 grill 的 R-B（D4 的 `archived_sources` 过宽）当前 design 未处置**，但我实测其危害有限：`/tmp/arr9` 的构造里那条记录的 `old_path` 本就匹配 `is_archive_move`（今天就已经在 `archived_sources` 里），D4 真正新增的只有 **`R<100`** 记录那条窄缝。**非必须改，建议在实现时按 grill 的建议收窄到「源 change 自己的目录」。**

### F. spec delta ↔ design 一致性

- **四条条件措辞**：`design.md:68-73` 与 `spec.md:15-24` **逐条一致**（含「有源」「`name == src` 或 `name.endswith("-" + src)`」）。✅
- **对称性不变量的限定**：**两边都写了、且都显式排除 stale 维度**——`design.md:95-102`（D2）与 `spec.md:134-145`（Req4 + ⚠️ 段）。✅（grill 的 M2 已落。）
- **⚠️ 不一致（见下「必须修改项」）**：`spec.md:71` 写「SHALL 满足上一条的**两条**判据」，但上一条（`spec.md:13-24`）是**四条**条件。

---

## 未验证项

1. **接入方 asterwynd 的具体数字**（「33 文件全 `A`」「R068/R069/R070/R090」「收尾 16 文件 11 项」「120 个归档目录」）——另一个仓的提交，本工作区**无法复算**。我用合成仓验证了**方向**（`git mv` + 重建 manifest ⇒ `R<100`；copy ⇒ 全 `A`），但**没有**复现其分数与计数。`tasks 4.2` 必须在接入方仓里真跑。
2. **F1 的端到端是「proxy」**：我用**新建 active 目录**（`changes/newid`）跑通证据门禁，因为当前代码还没实现 D1、无法让 `check` 直接认一个「到达的归档目录」。D2 声称归档 target 与 active 走**同一套**门禁——我正在验证的正是这套门禁，所以 proxy 有效；但严格说「到达的**归档**目录」这一跳是**推演**，不是实测。
3. **浅克隆 / partial clone 下 `merge-base` 与 `ls-tree` 的确切失败模式**：我本地 `git clone --depth 1 file://...` 的实验没能干净复现（`origin/main` 未建立），**未取得可靠证据**。`gate.yml` 已 `fetch-depth: 0`，但 D7 的 fail-closed **具体断言**（哪句 finding 文案、退出码、`ls-tree` 失败 vs `merge-base` 失败如何区分）**未验证**。
4. **`git worktree` / merge commit 形态**：只做了逻辑推演（`checkcmd` 用 `rev_parse(head)` 且 `SpanScope` 已处理 merge commit），**未实测** merge commit 下 `merge-base(base, head)` 与原树分叉时的到达判定。
5. **`manifest build` 是否真的不需要感知「到达」**（D7 / `design.md:178` 的订正）：我只复核了「`manifestcmd` 不调用 `change_targets`」（`grep` 为空）这一**事实**，**没有**验证「本 change 之后 `manifest build` 仍无需感知到达」这一**结论**。

---

## 必须修改项

- **M-F1（高危，必须修）：D1 第 3 条不足以关掉它自己的威胁（copy 变体）。**
  - 现状：条件 3 只看「到达组里有没有记录的 `old_path` 落在 `archive/**`」⇒ 只关 rename。
  - 缺口：把既有归档目录的整份内容 **`cp` 到新名**（源不动）⇒ 全 `A`、无 `old_path` ⇒ 条件 3 失明；配合手改 manifest 的 `change_id`/`head_sha` 两个字段 ⇒ 证据门全过（`/tmp/e2e` 实测 `check：通过 ✓`）。
  - 建议（任选，需写进 design + spec + 用例）：① **把「到达」再加一条「到达目录的文件 blob 集合不得与 base 里任何现存归档目录的 blob 集合相同/为其子集」**（直接判「不是复制来的」）；② 或对到达目录做**内容指纹比对**（`sha256` 目录级）；③ 若坚持靠 diff，**必须**把 `changed_files` 的 `-M` 换成能看见副本的模式并**在规范里写死**（但 `-M -C` 我实测**看不见**，需 `--find-copies-harder`，且仍是启发式 ⇒ 不建议）。**同时把 N8 的 Scenario 扩成 rename + copy 两格。**
- **M-Q4（中危，必须补）：把被丢掉的「`archive/` 非 change 子目录」假阴性补回停轮队列或写成判据。**
  - `design.md §8` 只剩 Q1–Q3、`§2.5` 也没有；但 F2 实测「`archive/2026/10-15-foo` ⇒ `2026` 被判为到达 ⇒ 红」，且本仓既有测试 `tests/test_archive_awareness.py:378` 就含这种目录。至少要**明确选**：`archive/` 下第一段必须是 change 目录（硬约定），还是「只把含必需件之一的目录当 target」。
- **M-D5（中危，必须修）：D5 / 规范 Req3 的保护写豁免定义过宽。**
  - 现状措辞「该记录**属于某个到达组**」（`design.md:129-140`、`spec.md:107-121`）未定义「属于」；其自然实现（`new_path` 落在到达目录下）会把「把 `openspec/specs/x.md` 等受保护文件**移入**到达目录」的记录也豁免。
  - 实测：今天 `contract.is_archive_move(Change("R100","archive/2026-10-15-new/secret.md","openspec/specs/secret.md"))` ⇒ **`False`**（今天的豁免**要求 `old_path` 落在 active change 目录**）⇒ 该记录**今天要事件**。D5 的宽口径会**放开**它。
  - 建议：把豁免严格限定为「**`old_path` 落在某个 active change 目录** 且 `new_path` 落在到达目录」（即保留 `is_archive_move` 的**旧侧条件**，只把「R100」放宽成「到达组」）。这样既达成 D5 的目的（重建 manifest 的 `R<100` 记录免事件），又不放开「把保护物搬出保护区」。
- **M-DOC1（必须修）：`tasks.md:42`(3.5) 与 `design.md:178`(§3 第 4 条) 直接冲突。** tasks 写「`manifestcmd.py`：与 `check` 共用同一份 target 解析（单一实现）」，design 写「订正后本 change **不改它**」。二者只能留一个——grill M4 已实测 `manifestcmd` 不调用 `change_targets`，**应采纳 design 的订正、改写 tasks 3.5**。
- **M-DOC2（必须修，spec 自矛盾）：`spec.md:71` 「SHALL 满足上一条的**两条**判据」应为「**四条**判据**（且四条的措辞与 `design.md:68-73` 对齐）**。**
- **M-DOC3（必须修）：`tasks.md:10` 写「停轮问题的 **Q1–Q4**」，但 `design.md §8` 现在是 **Q1–Q3**。** 命令文件与产物不一致，会误导执行者。
- **M-DOC4（建议修）：`spec.md:171` 「`manifest build --change <name>` 对归档目录的支持与 `check` SHALL **共用同一实现**」重复了 grill M4 判为**不实**的主张**（实际共用的是 `validate_change_dir` 与 `resolve_report_path`，不是「target 解析」）。要么删、要么改成准确的可共用项。
- **M-C1（建议修）：条件 1 措辞。** 「该前缀下没有任何 tree entry」对「base 同路径是 blob」是盲的（F2/低危 E 实测）。改成「该路径在 base revision 的树里**完全不存在**（blob 或 tree 皆算存在）」，并把「到达目录必须是 tree」写死（呼应 grill R-C）。

---

## Open Questions

> 只放**真正需要用户拍板**的。能由代码/安全属性定案的我已尽量移出（见下）。

**OQ-1（必须补问；本报告新增）：`archive/` 下的「非 change 直接子目录」怎么处置？**
- 具体例子：某接入方想按年份归档，落 `openspec/changes/archive/2026/10-15-foo/{proposal.md,…}`。base 里没有 `archive/2026/`。
  - 今天：无 target，`2026/` 不被校验。
  - D1（现稿）：`archive/2026/` 是**新建**的 ⇒ 被当作「到达的 change `2026`」⇒ 报「缺少必需件 proposal.md/design.md/tasks.md/specs/reviews」⇒ **红**。同款：`archive/templates/`、`archive/README.md` 所在的 `archive/`（若 `archive/` 本身新建）等任何组织型/工具型子目录。
- 需拍板：(a) 接受「`archive/` 下第一段必须是 change 目录」成为**硬约定**（组织型目录一律不许）；(b) 只把「**含任一必需件**（如 `proposal.md`）的子目录」当 target（把裸组织型目录放行）；(c) 其它。
- （`grill-design.md` 的 Q4 就是这条，当前 design 丢了它；`tests/test_archive_awareness.py:378` 是本仓的真实样本。）

**OQ-2（= design Q1，保留）：归档目录名「必须认得源 id」这条守卫，对**有源**的到达是否保留？**
- 具体例子（沿用 grill 的、补全两侧）：同上内容，用 `git mv changes/foo-x archive/misc` 放进去 ⇒
  - (a) 保留守卫：`misc` 不认得 `foo-x` ⇒ 不授予 ⇒ 红（要求你按 `archive/<date>-foo-x` 命名）；
  - (b) 删守卫：授予 ⇒ 走完整证据门禁（件齐才绿）；
  - **对照**：把同一内容**直接新建**（不做 move）到 `archive/misc/`（无源）⇒ **两种选法都授予**。
- ⇒ 同一最终状态（内容都在 `archive/misc/`），判绿判红**取决于 base 里源目录在不在**——这与「到达方式不设限」相抵。**是真用户/口径决策**（是否强制命名约定），保留。
- 附：条件 4 已**不承重安全**（原要挡的 N6 已被条件 1 独立关掉，实测），所以这条纯粹是命名约定取舍。

**OQ-3（= design Q2，保留）：`archive/**` 的 stale 豁免（暗房）本次收窄，还是另立？**
- 具体例子：已归档 change 的 `proposal.md`，在其 manifest 记的 `head_sha` **之后**改一个字。
  - 今天 / (a) 另立：**不判 stale**（`policy.stale_exempt_paths` 末项 `openspec/changes/archive/**`，`policy.py:77-92`）。
  - (b) 本次收窄：应判 stale。但这需要先回答「归档后哪些改动该被允许」，与「到达识别」正交。
- ⇒ 范围决策，保留。（注意：它决定对称性不变量**能不能**写成无条件——现稿已限定到证据门槛维度，所以 (a) 不再阻塞本 change。）

**OQ-4（= design Q3，**建议移出停轮队列**——见下方理由）：把**已存在**的归档目录**改名**，该不该授予资格？**
- 具体例子：某仓 3 个月前归档了 `archive/2026-09-30-foo/`（证据齐全）。今天 `git mv archive/2026-09-30-foo archive/2026-10-15-foo` 并顺手改 `agent/x.py`，**零新证据**。
  - (a) 不授予（= D1 第 3 条）：红。
  - (b) 授予：那份 3 个月前的证据被复用 ⇒ 绿。
- **建议移出**：`design.md:234-235` **自己已经证明** (b) 会让「只改 `src/**`、零新证据的 PR 变绿」——这是本工具存在的**核心安全属性**，不是口味问题；而本报告的 **F1** 进一步证明「白捡证据」在 copy 变体下**已经可达**。(b) 因此不是「另一个可接受的策略」，而是「接受一个已知绕过」。若一定要让用户拍板，应把它**改写成**「归档目录改名**要不要被显式拒绝/要写解释事件**」（即在 (a) 之上是否再加一条更友好的报错文案），而不是「要不要授予」。⇒ 我判定它是**可由安全属性定案**的一条，建议从停轮队列移出（改由代码定案为 (a)），或至少重新表述。
