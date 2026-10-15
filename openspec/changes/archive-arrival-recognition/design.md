# Design: archive-arrival-recognition

## 0. 一句话

把「本次 diff 里到达了一个归档 change」的判定，从**逐文件改名分（`R100`）**换成
**目录级事实（`archive/<name>/` 在基准树里没有 entry、在 head 树里是一个完整的 change 目录、且内容不是现成证据的搬运）**；
到达方式（`git mv` 过来 / 直接新建在 `archive/` 下）不设限，而**到达方式不改变证据门槛**。

## 1. 现状（实测）

### 1.1 代理指标错在哪（逐行核对）

- `contract.is_archive_move`（`src/witnessloop/contract.py:65`）：`if change.status != "R100" or not change.old_path: return False`。
  **逐文件**、且**要求恰好 100%**。
- `contract.changed_change_ids`（`:85`）用它算 `archived_sources`（`:97`）⇒ 只有 `R100` 记录的 `old_path` 才被排除。
- `contract.archive_grant`（`:119`）以它为前提 ⇒ 只有 `R100` 才授予 target。
- `checkcmd._protected_writes`（`src/witnessloop/checkcmd.py:228`，`is_archive_move` 分支在 `:255`）以它为准 ⇒ 只有 `R100` 才免解释事件。
- `gitutil.changed_files`（`src/witnessloop/gitutil.py:99`，`--find-renames` 在 `:105`）用的是 **`base...head`（三点 / merge-base）**，
  且是**两树**比较 ⇒ 「相似度」是**整个 diff range** 的产物，**无法**区分「move 那一刻顺带改了」与「更早的提交里改过」。
  ⚠️ 三点这件事是 **D1 的基准修订必须对齐**的理由（见 D1 第 1 条）。

### 1.2 复现命令（与 `gate.yml` 逐字一致）

```
uvx --from "git+https://github.com/Xingkai98/witnessloop@<ref>" \
    witnessloop check --root . --base <PR 的 base branch tip> --head <PR head>
```

`<ref>` = `v1`（对照）/ `5535d9e`（含 PR #22）。三份 diff 的实测结果见 `proposal.md` 的表。

### 1.3 三种真实形态的 diff 状态（可复算：`git diff -M --name-status <base> <head>`）

| 形态 | 记录状态构成 | 今天的结果 |
|---|---|---|
| 接入方**真实实现 PR**（33 文件） | **全 `A`**（base 里无此 change） | ✗ 1 项：`require_change_for` 报「没有任何 change 目录」 |
| **纯归档 move**（14 文件） | **全 `R100`** | ✓ 通过，`1 个 change 目录` |
| 接入方**收尾 4 连提交**（16 文件） | **4×`R<100`**（`R068/R069/R070/R090`）+ 11×`R100` | ✗ 11 项：幽灵 active id（3）+ 受保护写入（8） |

`R<100` 的那 4 个文件是 `reviews/{building,grill-adversarial,grill}.manifest.json` 与 `workflow-events.jsonl`——
**恰好是 adopter 收尾次序的必然产物**（先在最终内容 head 上重建 manifest、再做 move；`change_archived` 事件还要在 move 之后追加）。

### 1.4 参考实现研究（本仓的形态）

业界对「移动即改名」的处理（`git log --follow`、`git diff -M`、IDE 重构）都承认**相似度是启发式**，
因此成熟做法**不把相似度当作授权依据**，而是：① 用**显式的身份事实**（路径前缀 / 目录存在性 / **树对象身份**）
判定归属；② 把「内容是否变了」交给**独立的完整性校验**（哈希绑定）去抓。
本 change 沿用这条：归属看**目录存在性**，内容看**既有的 manifest 哈希绑定**，
**外加**一条目录级的**内容来源判据**（D1 第 5 条，由对抗轮 R1 的 F1 逼出、由 R2 重做）。

### 1.5 ⚠️ 上一版哪一条真的承重（初稿读错，此处订正）

初稿把 `archive-awareness` 的两条否定面读成「承重的安全守卫」。复核后**只成立一条**：

- **不承重**：「放宽 N2（出生即归档）会新开一块审阅后可改的暗房」。**假**——
  `policy.stale_exempt_paths`（`src/witnessloop/policy.py:77`）把 `archive/**` **整块**列为允许出现，
  暗房**今天就已经存在**（任何已归档 change 的 `proposal/design/tasks` 审阅后被改都不判 stale）。
- **承重**：「不得给 `base` 里**已存在**的归档目录凭空授予资格」，其**具体威胁**是
  **白捡一份现成证据**。⚠️ **本轮的订正（R2 实测）**：这条威胁**不止一个机制**——
  ① 把已存在的归档目录**改名**（`git mv`）；② 把它**整份复制**到新名（源不动）；
  ③ 复制之后再**改路径 / 改一两个字节**并用 `manifest build` 重算哈希。
  今天挡它的是 `archive_grant` 的 `R100` + 名识别（**顺带**挡住了后两种），
  本 change 必须用**独立、显式**的判据挡住它们（见 D1 第 3 条与第 5 条）。

⇒ 本 change **反转前一条、完整保留后一条**，且把后一条升级成**两条**判据
（第 3 条 = 记录层：来自 `archive/**` 的改名；第 5 条 = **内容层**：内容不得是现成证据的搬运）。

## 2. 决策

### D1 「到达」的判据 = 目录级事实，不看改名分

`archive/<name>/` 是**本次到达的 change**，当且仅当**五条同时成立**。

> **术语**：**到达组**（arrival group）= 本次 diff 里 **`new_path` 落在某个到达目录 `A` 之下**的记录集合
> （判据 3 / 判据 4 / D4 / D5 里的「到达组」都指它）。`A` 本身由判据 1–2 与判据 5 选出。

1. **基准树里该路径完全没有 entry**：在 **`M = git merge-base(base, head)`** 的树里，
   `<changes_root>/archive/<name>` **既不是 tree 也不是 blob**（该路径下也没有任何 entry）。
   ⚠️ **措辞订正（R1 实测 / R2 复算）**：初稿写「该前缀下没有任何 tree entry」——**对「base 同路径是一个 blob」是盲的**：
   `git ls-tree -r <M> -- <path>/`（带尾斜杠）对同路径 blob 返回 **0 行**。本稿钉死为「**该路径完全没有 entry**」，
   实现用**不带尾斜杠**的 `git ls-tree <M> -- <path>`（实测：base 是 blob ⇒ 1 行 `100644 blob …`；不存在 ⇒ 0 行）。
   ⚠️ 这条**不是**「放行」而是**拒绝**：base 里同路径是 blob ⇒ **有** entry ⇒ **不授予**（R2 用模拟器复算 `c1=False`）。
   **基准 SHALL 是 `merge-base(base, head)` 的树**（与 `changed_files` 的 `base...head` 同源，见 §5.1 第 7 条）。
2. **head 树里该路径是 tree，且含全部 `policy.required_artifacts`**
   （判定语义与契约门**完全一致**：`<dir>/<artifact>` **路径存在**——
   实测 `git ls-tree -r <head> -- <dir>/` 一条命令即可判定，且对「`specs` 是同名普通文件」这类形态也与 `validate_change_dir` 同结论）。
   ⇒ 组织型 / 工具型子目录（`archive/2026/`、`archive/notes/`、`archive/templates/`）**不是** change 目录。
   ⚠️ 实现 SHALL 忽略**空串 / `.`** 这类退化 artifact 名（`(dir/"").exists()` 恒真 ⇒ 判据 2 会退化成「任何目录」；
   R4 实测 `required_artifacts: [""]` 只**多报红**、不构成绕过——判据 2 本就不承重安全，但文案会变差）。
3. **不是从另一个归档目录改名而来**：到达组里**没有**任何记录的 `old_path` 落在 `<changes_root>/archive/**` 下。
4. **有源时须名识别**：若到达组里存在 `old_path` 落在 `<changes_root>/<src>/` 下（即**有源** `src`），
   则对**每一个**这样的源 SHALL 要求 `name == src` 或 `name.endswith("-" + src)`；**无源**（出生即归档）时本条无从施加。
   ⚠️ **本轮钉死「每一个」**：初稿写「有源 `src`」未说明多源怎么办；取「每一个」是 fail-closed 的一侧，
   且它顺带关掉「把**别的** active change 的内容倒进我的到达目录、让它从集合里静默消失」这条路（见 D4）。
5. **内容来源判据**（**R1 的 F1 逼出 → R2 重做 → R3 收紧证据集**）：
   到达目录 A 的**证据文件集** `Ev(A)` 里**每一个文件**（按 head 树；**内容为空**者除外）SHALL 满足下列之一：
   - (a) 其 **blob 在基准树的 `<changes_root>/**` 里不出现**（= 本次新写的内容）；
   - (b) 它是**本次 diff 里某条改名记录的落点**（记录的 `new_path`，即本次搬过来的）。
   违反 ⇒ **不授予**。
   ⚠️ **`Ev(A)` SHALL 由数据推导，SHALL NOT 按路径前缀硬编码**——R3 用真 CLI 实测：
   按「`tasks.md` / `specs/**` / `reviews/**`」三段前缀硬编码时，**把报告挪出 `reviews/`**（放到 change 目录根）
   与**把 `specs` 换成同名普通文件**这两条**零成本**改法都能让证词整体出圈（`check：通过 ✓`）。
   `Ev(A)` 的定义：
   1. `C.HASHED_ARTIFACTS` 覆盖的 artifact 路径**整体**——`tasks.md`；`specs`（**是目录 ⇒ 其下全部文件；
      是普通文件 ⇒ 它自己**）⇒ 关掉「换路径形态」那一档；
   2. `policy.review_manifest_glob` 命中的**每份 manifest**，**以及每份 manifest 的 `report_path` 解析出的那个文件**
      （用既有的 `contract.resolve_report_path`，与哈希校验同一口径）⇒ 关掉「报告挪出 `reviews/`」那一档；
   3. `<A>/reviews/**` 下的全部文件（回归面：即使某份报告没被写进 `report_path` 也照样进集）。
      ⚠️ 这一项**刻意与 `policy.review_manifest_glob` 无关**（它是固定的兜底面）——两者在自定义 glob 下会分叉，
      但自定义 glob 本就不可用：`manifest build` 硬编码把报告与 manifest 写在 `<label>/reviews/` 下（`manifestcmd.py:136-142,201`）。
   `proposal.md` / `design.md` **不在**集内：它们不被哈希绑定，且「共用 stub ⇒ 逐字节撞车」是现实误伤源
   （实测 E11：两个 change 共用同一份 design stub ⇒ 不触发）。
   ⚠️ **符号链接 SHALL 按「解析后的内容」参与 (a)/(b) 比对**（**只作用于 `Ev(A)` 的条目**；`A` 下的非证据文件不参与判定）。
   依据（R5 的 M1 实测）：git 把符号链接存成「链接文本」的 blob——只看链接自身时，把 `tasks.md` / `specs` 做成
   **指向基准树里现成 change 的符号链接**，链接 blob 是**新**的（(a) 成立），而证据门读的是**解析后的内容**
   （逐字节等于受害者的）⇒ 不处理符号链接，判据 5 **整体失明**。
   解析口径 SHALL 与 `contract.resolve_report_path` 同款（`Path.resolve()` + `pathutil.is_within`，展开 `..` 与符号链接）：
   - 目标**落在 `A` 之内** ⇒ 取**目标文件**的 blob 参与比对，并把目标路径**并入 `Ev(A)`**（递归到不动点，配 visited 集防环）；
   - 目标**落在 `A` 之外** ⇒ 取**该目标路径在 head 树里的 blob** 参与比对（**与 `cp` 进来同结论**：
     字节落在 `<changes_root>/**` 就命中 (a)、否则放行——这正是本判据的模型，**不额外制造误伤**，见 R7 的 M1）；
   - 目标**未被 git 跟踪 / 悬空**，或该条目是 **gitlink（`160000`）** ⇒ **fail-closed 不授予**（其内容不在本仓树里，无法核验）。
   ⚠️ **SHALL NOT 一刀切「不许符号链接」**（R6 的 M1 实测：那是**合法绿色样态**被误伤）：
   `reviews/alias.md → reviews/grill-review.md`（指向 `A` **之内**）是本仓既有钉绿布局
   （`tests/test_orphan_reports.py:273` `test_symlinked_report_is_not_an_orphan`），真 CLI 今天判绿。

⇒ 与 `change.status` 是 `A` 还是 `R<分数>` **完全无关**。两只症状（出生即归档 / move 带内容改动）同一刀切掉。

**为什么「到达方式不设限」不因此被限制**：合法 move 的文件全是改名记录的落点（(b) 成立）；
「出生即归档」与一切**真写着**的归档目录，其文件都是新 blob（(a) 成立）。两条路都在判据内。

#### D1 第 5 条：为什么是「内容来源」而不是「内容相似」

**威胁**（R1 的 F1 端到端实测 + R2 复算）：把一份**证据齐全**的现成 change 目录搬成新名，
再改 `src/**` ⇒ 一个**零新证据**的纯代码 PR 拿到资格。三个机制：

| 机制 | 今天 | 只有第 3 条时 | 本稿（第 5 条） |
|---|---|---|---|
| ① `git mv` 既有归档目录改名 | 不授予（名不认得 / 源在 archive） | **不授予 ✓**（第 3 条） | 不授予 ✓（第 3 条） |
| ② `cp -r` 整份复制（源不动） | **不授予**（全 `A` ⇒ 无 `R100`） | **授予 ✗**（R1 的 F1） | **不授予 ✓**（第 5 条） |
| ③ 复制 + 改路径 / 改一两个字节 + `manifest build` 重算哈希 | 不授予（同上） | **授予 ✗**（R2 的 A2） | **不授予 ✓**（第 5 条） |

**为什么不用「指纹集合包含」（初稿的形态，R2 已证伪）**：初稿把 A 的证据文件
（`tasks.md` + `specs/**` + `reviews/**/*.md`）的 `(路径, blob sha)` 集合 `E(A)` 与 base 里每个
change 目录的 `E(D)` 做 `⊆` 比对。R2 实测：**打断 `⊆` 的成本是零**——把某个证据文件**改个路径**
（改名 / 改后缀 / 把 `specs` 换成同名普通文件）就够，因为 `⊆` 逐路径比；再配一次
`manifest build` 重算哈希（`manifestcmd.py:146-153` 每次都从磁盘重算）就全过。
⇒ 那条判据只覆盖「逐字节 + 同路径」这一个点，而它**声称**堵住的是「白捡证据」这一类。**半套守卫没有意义**（R1 的原话）。

**现稿判据的覆盖（R2 的构造逐条复算）**：

| R2 构造 | 初稿指纹 ⊆ | 现稿 |
|---|---|---|
| 纯 `cp -r`（源不动） | 拒 ✓ | 拒 ✓ |
| 改某个证据文件的**路径**（改名 / 改后缀） | **逃逸 ✗**（真 CLI 绿） | 拒 ✓（blob 比对**与路径无关**） |
| 给某个证据文件**加一个字节** + 重跑 `manifest build` | **逃逸 ✗**（真 CLI 绿） | 拒 ✓（**其余**证据文件既不新、也不是本次搬来的） |
| **删**掉某个证据文件 + 重跑 `manifest build` | **逃逸 ✗**（真 CLI 绿） | 拒 ✓（同上） |
| 报告取自 change `a`、`tasks/specs` 取自 change `b`（**混源**） | **逃逸 ✗** | 拒 ✓（全部 blob 都在 base 的 `changes_root/**` 里） |
| **A1**：`git mv` 一个 `notes.md` 进 A + 其余**整份 `cp`** | **逃逸 ✗**（真 CLI 绿；初稿的豁免 ① 被一条无关 move 洗白） | 拒 ✓（`notes.md` 不在证据集里也无所谓——**其余每份证据**都不满足 (a)/(b)） |
| **A3**：源是**嵌套**归档目录（`archive/2026/10-15-old/`） | **逃逸 ✗**（D 扫描只认扁平 change 目录） | 拒 ✓（扫描面是 **`<changes_root>/**` 全量**，不是「change 目录」） |
| **R3-A1**（真 CLI 绿）：把三份报告**挪出 `reviews/`**（放 change 目录根）+ **手写** manifest 指过去 | 逃逸 ✗ | 拒 ✓（`Ev(A)` 含**每份 manifest 的 `report_path` 目标**） |
| **R3-A3**（模拟器）：`specs` 换成**同名普通文件**、或 `tasks.md` 做成**目录**，把借用内容塞进去 | 逃逸 ✗ | 拒 ✓（`Ev(A)` 取 artifact 路径**整体**：是文件就它自身、是目录就其下全部文件） |
| **R3-A2**（真 CLI 绿）：给 `Ev(A)` 里**每一个**文件各**追加一个字节** + 官方 `manifest build` 重算哈希 | 逃逸 ✗ | **逃逸 ✗ —— 能力天花板**（见下段；本档属「真实性 / 防伪造」，本 change 非目标，取舍见 §8 Q4） |
| 合法纯 move（`R100`） | 绿 ✓ | 绿 ✓（(b) 成立） |
| move + 重建 manifest（形态 ii） | 绿 ✓ | 绿 ✓（同上） |
| 出生即归档（全 `A`） | 绿 ✓ | 绿 ✓（(a) 成立） |
| **误伤对照**：新 change 的 `design.md` 与 base 里某 change 的 `design.md` 逐字节相同（stub） | ✗（误伤） | **绿 ✓**（`proposal`/`design` 不在证据集，实测 E11） |
| **误伤面**：新 change 原样复制了兄弟 change 的 `specs/limits.md` | 拒 | **拒**（实测 E12，只点名该文件 —— 这是**明写的代价**，见 §8 Q4） |

**为什么这条比指纹形态更强**：它**不把「路径」当身份**，而是要求「A 的每份**证据**要么是新的、要么是**本次**搬来的」。
「改路径」「删一个文件」「混源」「搬一个无关文件进来洗白」这几类零成本的「只动一处」手法全都落在判据外。

**⚠️ 能力天花板（诚实写明，不夸大；本条由 R3 用真 CLI 实测逼出）**：
判据 5 是**逐字节**判据。把 `Ev(A)` 里**每一个**文件都动一个字节（例如各追加一个换行）、
再用官方 `manifest build` 重算哈希，就**绕过**它——R3 实测 `check：通过 ✓`，而三份真审阅报告的
**语义内容一个字节没变**。
> ⚠️ **订正**：本稿初版把这条写成「等价于自己写一份完整证据（每个文件都得动）」。**那是错的**——
> 「每个文件各加一个换行」是**一个 `for` 循环**，与「真的写三份审阅报告」代价天差地别，
> 而且借用内容的语义（谁审的、审出什么决策、对抗轮结论）完全保留。R3 判定该等价论证为假，本稿据此删除。

⇒ 判据 5 的真实射程（**SHALL 按这个口径读**）：挡**零改动 / 只动一处**的机械搬运
（整份复制、复制后改路径、改一个字节、删一个文件、混源、搬无关文件洗白、源在嵌套目录）——
**不挡**「跑一个脚本给每份证据各加一个字节再重算 manifest」这一档。
**真正封堵那一档需要真实性**（签名 / 可验证来源 / 可追溯的作者身份），
而那是本 change 的**非目标**（既有边界：`contract.py:9`「hash 绑定证证据之间没漂移，**不防伪造**」）。
⇒ 这一档的取舍（接受并写明，还是再加一档强度）属 §8 **Q4**。

**误伤面（明写；本工作区实测 E11/E12，属 §8 Q4）**：只有当 A 的某个**非空证据文件**与 base 的
`<changes_root>/**` 下某个文件**逐字节相同**、且它不是本次搬来的，才会拒绝。三个现实来源：
① 从兄弟 change **原样复制**来的 `specs/**` 文件（实测 E12：只点名 `specs/limits.md`）；
② 内容就是 `PASS\n` 这类**极短样板**的报告；③ 被原样复制的 `tasks.md` 样板。
**已排除的误伤**（实测 E11）：`proposal.md` / `design.md` 逐字节撞车**不**触发；
**空文件**（0 字节，如 `reviews/.gitkeep`）**已豁免**。
失败是 **fail-closed**，finding **同时点名两侧路径**，修法是「写自己的内容」或「把那处复制改成 `git mv`」。

**已知边界（明写，逐条登记进 `docs/gate.md §6`）**：
- **完全旁路（R3 的 M6）**：判据 5 的效力**依赖**「`<changes_root>/**` 是存放 change 证据的唯一地方」这一前提
  （另有**逐字节天花板**这一条独立绕过，见下一条）。
  现成证据的字节若在基准树里**另有副本**（`docs/shipped/**` 这类发布副本、仓内镜像、`changes_root` 迁移遗留的旧路径），
  把那份副本搬进来就**逐字节复用**了整份证词：那些字节**落在 `<changes_root>` 之外 ⇒ 分句 (a) 单独即豁免**，
  **与是 `git mv` 还是普通 `cp` 无关、也不需要任何 rename 记录**（实测：`a4b` 的 10 份文件 blob **0/10** 落在 base 的 `changes_root/**` 里；
  普通 `cp` 的 `i5` 构造同样 `arrived=True`）⇒ 判据 5 零命中。
  （扫描面刻意只取 `changes_root/**`：取全树会把「任何一处逐字节撞车」都变成误伤。）
- **逐字节天花板**：`Ev(A)` 里每个文件各加一个字节 + 重算 manifest ⇒ 绕过（见上段）。
- **报告位置**：`check` 只要求报告「解析后仍在 change 目录内」，强制 `reviews/` 的只有 `manifest build`
  （`manifestcmd.py:136-142`）——**这条既有宽松面本 change 不改变**；但第 5 条现在**按 `report_path` 取证据**
  ⇒ 它**不再是**判据 5 的旁路（R3 的 A1 已关掉）。仍登记进 `docs/gate.md §6`。
- **符号链接的 fail-closed 残余（R7 的 M1）**：`Ev(A)` 里链接的**目标未跟踪 / 悬空**、或条目是 **gitlink**
  ⇒ 不授予（**今天判绿**）——这是本 change **明写的行为变化**（登记在 `spec.md` 的「有意的行为变化」第 3 条）。
- **模板骨架**：仓内模板若放在 `<changes_root>` **之内**（如 `changes/_template/**`），其 `tasks.md` / `specs/**`
  与新建 change 逐字节相同时会触发误伤 ⇒ **模板 SHALL 放在 `<changes_root>` 之外**（登记进 `docs/gate.md §6`）。
- **`workflow-events.jsonl` 不在 `Ev(A)` 里**（它是自由文本、不是被绑定的证据本体）——**本 change 不改变**这条既有面。
- **候选只取 tree**：`archive/` 的直接子项若本身是 blob（如 `archive/notes.md`）⇒ 不是到达候选（不会授予、也不会报缺件）。
- **`changes_root` 被 policy 覆写**：到达判定与 diff 成员共用**同一份**（工作树 / head 侧）policy，与今天一致。
- **判据 2 的近失文案（R3 的 E-2）**：件不齐的到达目录**不是** target ⇒ 报的是「没有任何 change 目录」，
  而**不**点名缺的那一件（如「缺 `reviews`」）。实现时在 `_require_change` 的文案里补一句
  「`archive/` 下存在缺必需件的目录 ⇒ 列出它」以消歧（`tasks.md` 3.9）。

### D2 到达方式不设限，且不改变证据门槛

到达的归档 target 走与 active change **完全同一套**：`validate_change_dir`（必需件）、
manifest 的 hash / revision 绑定、grill 报告正文判据、`code_hits` 触发的 `building` / `grill-adversarial` 硬门。
**SHALL NOT** 为归档 target 引入任何第二套判据或豁免。

> **对称性不变量**（本 change 的核心，**限定到「证据门槛」维度**）：
> 同一个 change 的同一份内容，放在 `changes/<id>/` 下与放在 `changes/archive/<name>/` 下，
> 在**证据门槛**上 SHALL 给出相同结论——必需件、manifest 的 hash / revision 绑定、
> `reviewer ≠ author`、grill 报告正文判据、以及 `code_hits` 触发的 stage 集合。
> ⚠️ **显式排除 `stale` 维度**（grill 实测纠正）：`policy.stale_exempt_paths` 对 `archive/**` **整块**豁免，
> 对 active 的 `proposal/design/tasks` **不**豁免（同一份 `proposal.md`：active ⇒ 不豁免、archive ⇒ 豁免，实测 `False vs True`）。
> ⇒ 「同一内容两种位置结论完全相同」按字面**不可满足**；这个非对称是**既有口径**，与本 change 正交，
> 属 §8 Q2 的暗房议题，**本 change 不宣称**在该维度上对称。（`proposal.md` 的验收段本轮同步加了这条限定。）

**为什么这条足以防绕过**：一份「伪造的归档目录」要绿，仍必须凑齐与 active change 等价的全部证据
（提案/设计/任务/specs/reviews、三份 stage manifest、`reviewer ≠ author`、grill ≥3 条决策、
building review …）。**到达方式不降低任何一条门槛**——这也是它与「凭空多出一个免检区」的本质区别。

### D3 保留真正承重的那条守卫，且**升级**为基树判定

**SHALL NOT** 给一个基准树里**已存在**的归档目录授予资格（D1 第 1 条），
**也 SHALL NOT** 给一份**搬运来的现成证据**授予资格（D1 第 5 条）。

`archive-awareness` 用「目标目录名必须认得源 id」来挡，但它自己承认有**残留边界**：
目标名恰好认得源 id 的**部分 move** 仍会授予。本 change 用第 1 条把它**真正关掉**：

| 构造 | `archive-awareness` | 本 change |
|---|---|---|
| `git mv changes/z/notes.md → changes/archive/y/notes.md`（`y` 已存在、名不认得 `z`） | 不授予 ✓ | 不授予 ✓（基准树里 `y` 有 entry） |
| `git mv changes/z/notes.md → changes/archive/2026-x-z/notes.md`（该归档目录**已存在**） | **授予**（残留边界） | **不授予 ✓** |
| 往**已存在**的归档目录新增 / 修改 / 删除文件 | 不授予 ✓ | 不授予 ✓ |

**名识别守卫（D1 第 4 条）是否保留**见 §8 **Q1**（本稿当前取「保留」，**推荐改成删除**，理由见该条；
R2 补充：「先修第 5 条、再谈这条」——第 5 条修好之后，删守卫是纯粹的命名约定取舍，不再放大安全面）。

### D4 幽灵 active id：按**到达集合**排除旧路径，而不是按 `R100`

`changed_change_ids` 的 `archived_sources` 改为「**到达组的全部记录的 `old_path`**」。
到达组是**目录级**的（D1）⇒ `R<100` 的记录也在组内 ⇒ 幽灵 active id 消失。

⚠️ **收窄（grill R-B + R1 §E）**：不能无条件排除「到达组里所有 `old_path`」。
反例：一次到达 `archive/2026-10-15-other/`，同 diff 里还有人把 `changes/other/notes.md`
搬进这个新目录 —— 若照搬，`other` 会**静默消失**（它的目录还在 head 里）。
⇒ 排除条件加一条**目录级事实**：**该记录的源 change 目录在 head 树里已不存在**。
⚠️ **R5 的 M2 订正**：初稿把这条读成「该目录不存在 ⇒ 那个 change **整体**搬走了」——**该推论为假**
（源目录不存在也可能因为它的文件被**删除**，而不是被搬走）。R5 实测的构造：删除 `changes/x/` 的其余 4 份文件、
只把 `notes.md` 搬进一个**件齐的**新到达目录 `archive/2026-10-15-x/`（名字认得 `x`）+ 改 `src/**`。
⇒ 现稿在这种构造下**不再把 `x` 当 active**（**今天**会报 5 项「`openspec/changes/x`：change 目录不存在」）。
**这是有意的行为变化，已登记**（`spec.md` 回归护栏段）：它与本 change 修好的形态同族（在 A 里重建了那份 change，
A 会被**完整校验**；被删文件里受保护的那几类（manifests / events）仍要解释事件）。
**fail-closed 对照仍然成立**：若 A **件不齐**（不是到达）⇒ `x` 仍被问话 ⇒ 红（§5.1 第 2c 条钉住）。
（R5 试过三种「按路径收窄」的写法，**都会误伤 §5.1 2b** 那条「move + 被搬文件整体重写」⇒ 只能明写 + 钉用例。）
源目录仍在 head 里 ⇒ **不排除** ⇒ 它照旧按 active 契约校验（部分搬走的目录**必须**被问话）。
（D1 第 4 条的「每一个源都须被认得」是**另一层**同类保护：名不认得的源根本不许进到达组。）

⚠️ **排除键 SHALL 同时覆盖 `D` 侧记录（R3 的 M4，实测）**：`gitutil._parse_name_status`（`gitutil.py:114-130`）
对 `D` 记录把**被删路径放在 `path`、`old_path` 留空**。于是「整体重写被搬走的 `tasks.md` / `specs`」
（40 行新内容 ⇒ git 不配对成改名，报 `D`+`A`）会让幽灵 id 回来：实测 `git mv changes/z archive/2026-10-15-z`
+ 把 `tasks.md` 整体重写 ⇒ 到达判定 `arrived=True`，但 `changed_change_ids` 仍返回 `['z']` ⇒ 报
「`openspec/changes/z`：change 目录不存在」⇒ 红（**今天也红**，所以不是回归，但**本 change 声称修好的形态 ii
只被修好了一档**）。⇒ 排除条件写成：
**「记录的 `old_path`（`R`/`C` 记录），以及 `D` 侧记录的 `path`，只要它落在某个到达组的源 change 目录
`<changes_root>/<src>/` 下、且该目录在 head 树里已不存在 ⇒ SHALL 排除」**（§5.1 第 2b 条钉住）。

### D5 受保护写入的豁免：同一份到达集合，`R<100` 一并免，但**旧侧条件不许丢**

`_check_protected_writes` 里「归档 move 免解释事件」的判据，从**逐文件 `is_archive_move`**
换成「**该记录属于某个到达组，且其 `old_path` 落在 `<changes_root>/<active-id>/` 下**」。

**为什么必须带旧侧条件（R1 的 M-D5）**：初稿措辞是「该记录**属于某个到达组**」，未定义「属于」。
其自然实现（只看 `new_path` 落在到达目录下）会**放开**一条今天要事件的形态：
把 `openspec/specs/secret.md` **移入**一个到达的归档目录——今天该记录**要**事件，
宽口径下会被豁免 ⇒ 受保护物被搬出保护区却无需解释。⇒ 保留 `is_archive_move` 的**旧侧条件**
（源在 **active change 目录**下），只把「`R100`」放宽成「到达组」。

**放宽了什么**：`R<100` 的记录（如重建过的 manifest、被追加过的事件文件）不再各报两条
「受保护路径被写入，但没有结构化解释事件」；它们今天不豁免只是因为它俩**顺带改了内容**。
**为什么可接受**：那 8 条本来就是**收尾次序的必然产物**，不是「偷偷改动」；
而 manifest 的**内容真伪**由它自己的哈希绑定与 stale 判据把关，
**不靠**「要不要写一条解释事件」把关（active change 新增 manifest 本来就免事件，门槛一致）。

**没有放宽什么**：
- 对基准树里**已存在**的归档目录的修改 / 删除（`M` / `D`）——目录不在到达集合里 ⇒ **仍逐条要解释事件**（回归钉）；
- 「把受保护文件搬进到达目录」⇒ 旧侧不落在 active change 目录下 ⇒ **仍要事件**（M-D5 钉住）；
- 出生即归档（全 `A`）本来就不需要这条豁免：它的文件是**新增**，`**/reviews/*.manifest.json`
  与 `**/workflow-events.jsonl` 走既有的「不变集 + `A` ⇒ 免事件」分支，其余路径命中不了任何保护面。

### D6 归属与别名的口径不变

归档 target 的 `change_id` 仍是**归档目录名**；`accepted_change_ids` 仍是
`{归档目录名} ∪ {能从 move 记录里解析出的源 id}`。
出生即归档（无源）⇒ 集合只有目录名——与今天「用 `manifest build --change <目录名>`」的口径一致，
**不新增**别名种类。

### D7 纯函数边界与接线

到达判定需要**树事实**，因此：

- 新增 `gitutil` 帮助函数（语义 **fail-closed**：读不出来 ⇒ 报 finding、**不授予**）。
  ⚠️ **精确命令（本工作区实测，R2 独立复算）**——三种路径写法语义**不同**，别写错：
  | 用途 | 命令 | 实测语义 |
  |---|---|---|
  | 某路径**自身**是否存在（blob 或 tree） | `git ls-tree <rev> -- <path>`（**不带尾斜杠**） | 存在 ⇒ 1 行（`100644 blob …` 或 `040000 tree …`）；不存在 ⇒ 0 行。**D1 第 1 条用这个** |
  | 某目录的**直接子项** | `git ls-tree <rev> -- <dir>/`（**带尾斜杠**，不递归） | 列直接子项（blob + tree） |
  | 某目录**其下的条目** | `git ls-tree -r <rev> -- <dir>`（递归；带不带斜杠同结果） | 列 blob 行**与 `160000 commit`（gitlink）行**，**不含** tree 行（R7 实测：gitlink 行确实会出现）；因此「`specs` 是同名普通文件」看得见（与契约门 `.exists()` 同结论），**而 gitlink 条目也必须被显式处理**（见 §D1 第 5 条） |
  一次 `ls-tree -r <merge-base> -- <changes_root>` 就能同时拿到「基准树里全部 blob sha 集合」与「existing change 目录」。
- 到达判定只留**一份**实现，且**纯函数化**：把树读取作为**注入的谓词**（不在判定里调 git）——
  判定本体保持可单测（不需要真 git 仓）。注入面是**一对读取器**（`entry(rev, path)` / `entries(rev, path)`），
  由 `checkcmd` 传真 git 实现、由单测传**假树**。
- `contract.change_targets(...)` 增加树读取入参；`changed_change_ids` 同理（D4）。
- 保护写检查（`checkcmd._protected_writes`）接收同一份到达集合（含每个名字的到达组）。
- **`manifestcmd` 本 change 不改**：它**不调用** `change_targets`（`grep -n change_targets
  src/witnessloop/manifestcmd.py` 为空），自己按**磁盘存在性**解析 active 优先 / 否则 `archive/<name>`
  （`manifestcmd.py:33-48`）。两者真正共用的是 `validate_change_dir` 与 `resolve_report_path`。
  ⇒ 本 change **不**声称在 `change_targets` 上共用；若实现时发现 `manifest build` 也需要感知「到达」，
  须**另写清要共享什么**，不得含糊带过。

## 2.5 Code-Resolved Questions（不进停轮队列）

| # | 问题 | 结论 | 依据 |
|---|---|---|---|
| C1 | 「出生即归档」的归档目录名不认得任何源 id，名守卫会不会因此失效？ | 无源即无守卫可施；该路径的证据门槛与 active 完全一致（D2） | 本 change 的设计；用例见 §5.1 |
| C2 | 到达判据会不会把「预存归档目录 + 新增文件」误判为到达？ | 不会：基准树里该路径有 entry ⇒ 第 1 条不成立 | §5.3 的用例 N3 钉住 |
| C3 | 纯归档 move（全 `R100`）会不会因为换判据而**失效**？ | 不会：基准树里没有 entry、head 里是完整 change 目录、文件全是本次搬来的 ⇒ 到达；今天认得，修后仍认得 | §5.3 的用例 + 本工作区模拟器（E3） |
| C4 | 会不会把 `archive` 当成一个 change id？ | 不会：`archive_root` 自身不是 target（既有行为，回归钉） | `changed_change_ids` 既有的 `archive/**` 排除分支 |
| C5 | 组织型 / 工具型子目录（`archive/2026/`、`archive/notes/`）会不会被当成到达的 change？ | **不会**：第 2 条要求该目录含**全部**必需件——`archive/2026/` 的直接子项只有 `10-15-foo`；`archive/notes/`（含 `sub/`、甚至含一个 `reviews/` 子目录）都缺 `proposal.md` 等 ⇒ 不是 target（R2 的 B1 用「只要求 ≥1 个必需件」证伪成功，本条据此收紧） | R1 的 F2 + R2 的 B1；本工作区实测 `archive/2026/` 直接子项是 tree `10-15-foo`（`/tmp/d8d`） |
| C6 | `base` 里同路径是个**文件**、head 里变成目录，该不该授予？ | **不授予**（该路径在基准树里**有** entry ⇒ 第 1 条不成立）。⚠️ R1 曾把这条写成「是到达、且这是对的」，那是 R1 的 **M-C1 之前的残留**；R2 复算 `c1=False` 并把它列为自相矛盾项，本轮已全部回写（C6 / §5.1 第 11 条 / §5.3 N11 / spec 一并改） | 本工作区实测：带尾斜杠 `ls-tree -r` 对同路径 blob 返回 0 行、不带斜杠返回 1 行（`/tmp/d8c`） |
| C7 | 第 5 条的 blob 比对会不会把「合法 move 过来的文件」误判成「现成证据」？ | 不会：搬来的文件是本次 diff 的**改名记录落点** ⇒ (b) 成立。R2 实测 `-l1`（renameLimit=1）下**逐字节相同的改名仍被配对**（exact-rename 检测不受 `renameLimit` 影响，后者只约束 inexact 检测）⇒ (b) 在极限设置下也成立，且「复制+删源」那一路由第 3 条兜住 | R2 的 `r6`/`r7`/`r9` + 本工作区 E2/E3/E8 模拟器 |

## 3. 接线点（实现清单）

1. `src/witnessloop/gitutil.py`：新增树查询帮助函数（`tree_entry` / `tree_entries`，语义与 fail-closed 见 D7 的表）。
   调用成本：**1 次** `ls-tree -r <merge-base> -- <changes_root>`（一次列全，供第 5 条的 blob 集合）
   + **每个到达候选 1 次** `ls-tree -r <head> -- <archive>/<name>/`（第 2 条与第 5 条共用）
   + **每个到达候选 1 次** `ls-tree <merge-base> -- <archive>/<name>`（第 1 条）
   + **每个源 id 1 次** `tree_entry(<head>, <changes_root>/<src>)`（D4 收窄）。
2. `src/witnessloop/contract.py`：新增到达判定（注入式树读取器）；改 `changed_change_ids`（D4）、
   实现第 5 条内容来源判据、改 `change_targets`（用到达集合产出归档 target）。
3. `src/witnessloop/checkcmd.py`：把到达集合传给受保护写入检查（D5）；替换 `is_archive_move` 的用法；
   构造并传入真 git 版的树读取器。
4. `src/witnessloop/manifestcmd.py`：**本 change 不改它**（见 D7 的订正）。
5. `docs/gate.md`：§5.1.1（归档语义）/ §4 / §3.2 的措辞与判据同步；§6 的已知边界更新
   （删「R100 要求」，补：树不可读 ⇒ fail-closed；**整份 / 部分搬运现成证据 ⇒ 不授予**；
   **模板骨架 SHALL 放在 `<changes_root>` 之外**（放里面会被判据 5 误伤）；
   扫描面是 `<changes_root>/**`，放别处的历史副本不可见；报告可放在 `reviews/` 之外这条**既有**宽松面）。
6. `README.md`：接入指引里「归档时序」一段按新判据改写。

## 3.5 非目标

- **不收窄 `archive/**` 的 stale 豁免**（暗房）——既有口径、与本 change 正交，**另立 issue**（§8 Q2）。
- **不支持嵌套归档布局**（`archive/2026/<name>/`，见 §8 Q3）——本次维持今天的行为。
- **不引入签名 / 防伪造**（`contract.py:9` 的既有能力边界不变）——第 5 条只关**机械搬运**。
- 不改归档命名约定；不改退出码语义；不建立「change ↔ 代码路径」映射。
- 不把「出生即归档」写成**推荐**流程（它只是必须被正确识别的形态）。

## 4. 风险

| # | 风险 | 处置 |
|---|---|---|
| R1 | **豁免面被开大**（`archive-awareness` 的 C3 教训：只让 `_require_change` 闭嘴 ⇒ 零证据 PR 变绿） | §5.3 的每条否定面都配一条**同等强度**的证据门用例；D2 的对称性不变量写成断言；§5.3 新增 **N9–N13**（搬运类） |
| R2 | 树查询在浅克隆下失败 | `gate.yml` 已 `fetch-depth: 0`；仍失败则 **fail-closed**，并有用例钉住。⚠️ 触发面比初稿暗示的窄：`merge-base` 求不出时 `changed_files` **已经**抛错并 fail-closed（`gitutil.py:107`、`checkcmd.py:55`），新增的独立面只剩「`merge-base` 成功但对某个 tree/blob 的 `ls-tree` 失败」（R2 浅克隆探针支持：`--depth 1` 时 `merge-base` 无输出而 `ls-tree -r origin/main` 正常） |
| R3 | 到达判定依赖 git 新 API，行为漂移 | 判定做成**注入读取器**的纯函数，单测不碰真 git；接线处另有集成用例 |
| R4 | 与 `manifest build` 的归档解析出现**两套实现** | **已订正**：`manifestcmd` 不调 `change_targets`（grill M4 实测），本 change 不声称该处共用 |
| R5 | 旧行为被无意改动 | §5.2 回归面逐条点名；纯 move 与既有否定面各有用例；§5.2 第 6 行点名**必须改写**（5 条）与**不要误改**（3 条）的既有测试 |
| R6 | **第 5 条误伤**（逐字节撞车 ⇒ fail-closed 拒绝） | 误伤面已明写（§D1 第 5 条）：**空文件已豁免**；触发面是「极短样板文件 / 从兄弟 change 复制的 spec」；finding **同时点名两侧路径**；见 §8 Q4。用例正面钉住「合法 move / move+重建 manifest / 出生即归档不被误伤」（R2 已用模拟器 + 真 CLI 复核这三条） |
| R7 | 第 5 条让「拿旧 change 复制成新 change 再改内容」的接入方踩雷 | ⚠️ **订正（本轮实测）**：判据是**逐证据文件**的（`tasks.md` / `specs/**` / `reviews/**`），
所以「复制后只改一半」**仍会被拒**——必须**每一份**被复制的证据文件都重写（或改成 `git mv`）。
对「**复制式归档**」（`cp` 而不删源）是**有意的行为变化**（今天该形态也红：全 `A` ⇒ 无 `R100`），见 §8 Q4；
另外**符号链接的 fail-closed 残余**（目标未跟踪 / 悬空 / gitlink）是**今天绿 → 本 change 红**，已登记 |

## 5. 测试策略（TDD）

### 5.1 用例（实现前红、实现后绿）

1. **出生即归档**：base 无 `changes/<id>`、head 有 `archive/2026-x-<id>/`（全 `A`，件齐）+ 改 `src/**` ⇒ 退出码 0。
2. **move 内带内容改动**：全 `R<100`（含重建过的 manifest）⇒ 退出码 0，且**无**幽灵 active id。
2b. **move + 被搬文件被整体重写**（R3 的 A4：`git mv changes/z archive/2026-10-15-z` + 把 `tasks.md` 整体重写 ⇒
   git 报 `D`+`A`，**不**配对成改名）⇒ 退出码 0，且**无**幽灵 active id（依赖 D4 的 `D` 侧排除键，见 §2 D4）。
2c. **R5 的行为变化 + 它的 fail-closed 对照**：
   - （**变绿，须钉住**）删除 `changes/x/` 其余文件 + 只把 `notes.md` 搬进**件齐的**新到达目录 `archive/<date>-x/` + 改 `src/**`
     ⇒ 退出码 0（**今天**报「`openspec/changes/x`：change 目录不存在」×若干）——登记为**有意的行为变化**；
   - （**仍红，须钉住**）同上但到达目录**件不齐** ⇒ `x` 仍被问话 ⇒ 退出码非 0。
3. **接入方真实形状**：§1.3 第 1 行与第 3 行的两份 diff 各一条集成用例（可从接入方提交复算）。
4. **对称性**：同一份 change 内容，`changes/<id>/` 与 `archive/<name>/` 两种位置判绿判红一致（D2 不变量）。
5. **别名**：单纯 move（不重建 manifest）后归档前产出的 manifest 仍通过（既有用例保持绿）。
6. **fail-closed**：树读不出来 ⇒ 报 finding、不授予。
7. **基准 revision 对齐**：`base` ref 在分叉点之后前进过（原树 ≠ merge-base 树）⇒
   到达判定与 `changed_files` 的成员口径一致；反例构造：一个目录在 `base` 原树里**存在**、
   但在 `merge-base` 树里**不存在**（分叉后才加），此时它**是**到达（与 diff 口径一致）。
8. **名识别对「有源」的到达生效**：`archive/misc/`（新建、内容整体来自 active `z`）⇒ 不授予。
   ⚠️ 若 §8 Q1 裁定改成 (b) 删守卫，本用例**语义反转**（改为「授予、走完整证据门」）。
9. **内容来源（第 5 条）**：**逐个构造各一条**（R1 的 F1 + R2 的 A1/A2/A3 全部转成用例）：
   ① 纯 `cp -r`（源不动）；② 复制 + 改某个证据文件的**路径**；③ 复制 + 加**一个字节**并重跑 `manifest build`；
   ④ 复制 + **删**一个证据文件并重跑 `manifest build`；⑤ **混源**（报告取自 `a`、`tasks/specs` 取自 `b`）；
   ⑥ **A1**（`git mv` 一个非证据文件进 A + 其余整份 `cp`）；⑦ **A3**（源是嵌套归档 `archive/2026/10-15-old/`）
   —— 全部断言 **不授予** ⇒ `require_change_for` 命中 ⇒ 红。
   **防误伤对照（必须绿）**：同构造下**真的 `git mv`**（源目录在 head 里消失）⇒ 绿（实测 E3/E6/E7）。
   ⑧ **误伤对照（必须绿）**：新 change 的 `proposal.md` / `design.md` 与 base 里某 change 的**逐字节相同**（共用 stub）
   ⇒ 绿（本工作区实测 E11）；
   ⑨ **明写的误伤面（预期红，须在文档里登记）**：原样复制兄弟 change 的 `specs/**` 文件 ⇒ 红，且 finding **只点名该文件**
   （本工作区实测 E12）。
   ⑩ **R3 的三条（`Ev(A)` 的定义边界）**：**A1** 把三份报告**挪出 `reviews/`**（放 change 目录根）+ 手写 manifest 指过去
   ⇒ **拒**（`Ev(A)` 取 `report_path` 目标）；**A3** `specs` 换成同名普通文件 / `tasks.md` 做成目录、借用内容塞进去 ⇒ **拒**
   （`Ev(A)` 取 artifact 路径整体）；**A2** 给 `Ev(A)` 里**每一个**文件各加一个字节 + 官方 `manifest build` ⇒
   **不拒**（= **能力天花板**，§D1 第 5 条明写；用例按「文档化的已知行为」钉住，**不**要求它红）。
10. **组织型子目录**：新建 `archive/2026/10-15-foo/{…}` + 改 `src/**` ⇒ `archive/2026/` **不是** target
    （不产生「缺少必需件」）；**并且** R2 的 B1 反例：`archive/notes/` 里只有 `sub/` 与一个 `reviews/`
    子目录（缺 `proposal.md` 等）⇒ **也不是** target。两条都要钉。
11. **base 同路径是 blob**：base 有 blob `archive/foo`、head 是目录 `archive/foo/…` ⇒
    第 1 条判「有 entry」⇒ **不授予** ⇒ 红（且不得崩溃）。
12. **D4 收窄**：到达目录 + 同 diff 里把**另一个仍在 head 的** active change 的文件搬进它 ⇒
    那个 change **仍按 active 校验**（不得静默消失）。
13. **空文件豁免**：到达目录里放一个**空**文件（内容 0 字节，且 base 里也有空文件）⇒ **不**因此被拒。

### 5.2 回归面（**必须保持绿**）

- 纯归档 move（全 `R100`）今天通过 ⇒ 修后仍通过。
- 只改 `src/**` 而**不建**任何 change 目录 ⇒ 仍红。
- **删除** change 目录（`D`，非 rename）⇒ 仍报「change 目录不存在」。
- 归档 target 的 `change_id` 别名行为不变。
- `archive/` 本身不是 change id。
- **必须改写的既有测试**（5 条；改前绿是**旧语义**下的绿）：
  1. `tests/test_archive_awareness.py:274` `test_rebuilding_a_moved_manifest_in_the_same_diff_is_rejected`
     —— 断言「move + 重写被 move 的 manifest（`R<100`）⇒ 红 + 幽灵 id」，**这正是本 change 要修好的形态 ii**
     ⇒ 语义**反转**为「绿、无幽灵 id」，测试改名（如 `..._is_accepted`）。
     ⚠️ 它**不在** R1 的必须修改项里（grill M6 只点了 `:541`）——本稿补上，R2 复核同意。
  2. `:494` `test_the_summary_counts_directories_not_deduped_ids_on_a_tie` —— 其构造里 `archive/x/`
     **只有** `notes.md`（缺必需件）⇒ 第 2 条下它**不是** target ⇒ 报 1 而非 2。
     ⚠️ **改写配方订正（R3 的 B1，实测）**：初稿给的配方（「把整个 `changes/x` move 到 `archive/x`，
     **同时**新建一个件齐的 `changes/x`」）**不成立**——新 active change 占着**同一路径** ⇒ git 报 `M` 而非 `D`
     ⇒ 改名配不成 ⇒ `archive/x/**` 全是 `A` ⇒ 判据 5 命中 3 份（其 blob 都在 base 的 `changes_root/**` 里）。
     **改用**：`archive/x` 走**出生即归档**（要件与证据**全新**），**同时**在 base 已有、head 仍存在的
     `changes/x` 上改一个文件（`M`）⇒ 两个 target 都在（同 id 撞两目录的**意图**保住了）。
  3. `:109` `test_grant_requires_the_target_name_to_recognize_the_source_id` —— 直调
     `contract.archive_grant`；`archive_grant` 在本 change 里失去全部调用点（见 §3），
     ⇒ 随实现删除 / 改写为对新纯函数的用例（保留「`R<100` 也授予」这条断言——判据换了，语义不变）。
  4. `:49` 的 `_targets()` 助手与 A 节纯函数用例（`:87` / `:101` / `:134` / `:471`）——
     `change_targets` / `changed_change_ids` **签名变了**（要注入树读取器）⇒ 助手改为注入**假树**，按新接口改写（语义不变）。
     ⚠️ `:471` 的构造里有一个**名不认得的源** `unrelated`：D1 第 4 条取「每一个源都须被认得」⇒ 该到达**整体被拒**
     ⇒ 用例要改成「只留两个认得的源」（保住「别名取并集、与顺序无关」的原意），并**另加**一条「名不认得的源 ⇒ 整个到达不授予」。
  5. `:600` `test_N6_partial_move_into_an_existing_archive_dir_grants_nothing` ——
     ⚠️ **订正（R3 的 B2，实测）**：初稿把它列在「不要误改」里，**是错的**。该 diff 里有一条
     `git mv changes/another-change/notes.md → archive/<已存在的归档目录>/notes.md`，今天 `archived_sources`
     把它排除掉 ⇒ 集合为空 ⇒ 报「没有任何 change 目录」。**新口径**（D4 收窄后）**不再排除它**（`another-change`
     的目录**仍在 head 里**）⇒ 它会成为一个 active target ⇒ 改报「缺少 review manifest」⇒
     `:621` 的断言 `"没有任何 change 目录" in err` **失守**。
     ⇒ 移入「必须改写」：断言改成「`another-change` 仍被按 **active** 契约校验」（这正是 `spec.md` 回归护栏段
     明写的「源 change 不得静默逃检」）。
  ⚠️ **对照（不要误改）**：
  - `test_N2_a_forged_archive_grants_nothing`（`:541`）—— 它的假目录**缺 `reviews/`** ⇒ 按第 2 条（须含**全部**必需件）**不是** target
    ⇒ `"没有任何 change 目录" in err` **仍然成立** ⇒ **保持原样**（R1 的 M6 曾要求改写它；第 2 条收紧后不必要了；R3 复核成立）。
  - `test_N4`（`:577`）断言的 `"没有任何 change 目录"` 在 D1 下**仍成立**（该 diff 里没有任何带 `old_path` 的记录 ⇒
    target 集合为空；R3 复核成立）。
  - `test_deeper_events_file_is_not_read`（`:378`）仍绿（`archive/notes/` 缺必需件 ⇒ 不是 target）——注释应更新
    （R3 的 M7 提醒：这条**仍未**改，实现期别漏）。
- `uv run pytest -q` 全绿（基线数字在实现时实测填入，不写估计值）。

### 5.3 否定用例（**必须照样红 / 不授予**）

| # | 构造 | 期望 |
|---|---|---|
| N1 | 只改 `src/**`，不建 change | 红（`require_change_for`） |
| N2 | **修改**一个基准树里已存在的归档目录里的文件（`M`）+ 改 `src/**` | 红（不授予 ⇒ `require_change_for` 命中） |
| N3 | 往一个基准树里已存在的归档目录**新增**一个文件（`A`）+ 改 `src/**` | 红（基准树里该路径有 entry ⇒ 第 1 条不成立） |
| N4 | `git mv changes/z/notes.md → changes/archive/y/notes.md`（`y` 已存在、名不认得 `z`）+ 改 `src/**` | 红（第 1 条） |
| N5 | 删掉 change 目录（非 rename） | 红（「change 目录不存在」） |
| N6 | 到达的归档 change **件齐、零 manifest** + 改 `src/**` | 红，且逐条点名三份 stage manifest（**防 R1**） |
| N7 | 新建 `archive/<name>/` 但缺必需件（如无 `reviews/`）+ 改 `src/**` | 红 —— ⚠️ **理由订正**：不是「到达后由契约门报缺件」，而是**第 2 条不成立 ⇒ 它不是到达** ⇒ `_require_change` 命中（报「没有任何 change 目录」） |
| N8 | **把基准树里已存在的归档目录改名**（新名在基准树里没有 entry） | 红：第 3 条（到达组里有 `old_path` 落 `archive/**`）**且**第 5 条也命中（内容两边都不是） |
| N9 | **纯 `cp -r`**（R1 的 F1：源原封不动 + 只改 manifest 的 `change_id`/`head_sha`） | 红：第 5 条 |
| N10 | **复制 + 改路径**（改证据文件的后缀 / 改名 spec 文件） | 红：第 5 条（blob 比对与路径无关） |
| N11 | **复制 + 只改一处**（给**某一个**证据文件加一个字节 / 删掉一个，并重跑 `manifest build` 重算哈希） | 红：第 5 条（**其余**证据文件既不新、也不是本次搬来的） |
| N12 | **复制 + 删一个证据文件**（并重跑 `manifest build`） | 红：第 5 条（同上） |
| N13 | **A1**：`git mv` 一个非证据文件（如 `notes.md`）进 A + 其余整份 `cp` | 红：第 5 条（第 3 条失明：源是 active；第 4 条被 `-<src>` 后缀满足） |
| N14 | **A3**：源是**嵌套**归档目录 `archive/2026/10-15-old/`，整份 `cp` 成扁平新名 | 红：第 5 条（扫描面是 `<changes_root>/**` 全量） |
| N15 | **混源**：报告取自 base 的 change `a`、`tasks.md` + `specs` 取自 change `b` | 红：第 5 条 |
| N16 | **组织型子目录**：新建 `archive/2026/10-15-foo/{…}` + 改 `src/**` | 红，但报的是「没有任何 change 目录」（`archive/2026/` 不是 target），**不是**「`archive/2026/` 缺少必需件」 |
| N17 | **组织型子目录（B1 变体）**：`archive/notes/` 只含 `sub/` 与一个 `reviews/` 子目录 | 同上：不是 target |
| N18 | **base 同路径是 blob**：base 有 `archive/foo`（文件）、head 是 `archive/foo/{…}` + 改 `src/**` | 红（第 1 条判「有 entry」⇒ 不授予） |
| N19 | **复制 + 报告挪出 `reviews/`**（放 change 目录根）+ 手写 manifest 指过去（R3 的 A1，真 CLI 曾绿） | 红：第 5 条（`Ev(A)` 含**每份 manifest 的 `report_path` 目标**） |
| N20 | **复制 + `specs` 换成同名普通文件**、或 **`tasks.md` 做成目录**并把借用内容塞进去（R3 的 A3） | 红：第 5 条（`Ev(A)` 取 artifact 路径**整体**） |
| N21 | **复制 + 给 `Ev(A)` 里每一个文件各加一个字节** + 官方 `manifest build`（R3 的 A2，真 CLI 绿） | ⚠️ **不红 —— 能力天花板**（§D1 第 5 条明写；用例只钉「已知行为」，见 §8 Q4）。**若用户选「再加一档强度」，本行改判红** |
| N22 | **符号链接**（R5 的 M1 + R6 的 M1）：① 把 `tasks.md` / `specs` / 报告做成**指向基准树里现成 change 的符号链接**；② 同类的**悬空链接** / **gitlink**（`160000`） | ① 红（按解析后的内容比对 ⇒ 指向 `changes_root` 里现成 change ⇒ 既非新 blob、也非本次改名落点；**逃出 `A` 的链接直接 fail-closed**）；② 红（fail-closed）。**对照（必须绿）**：`reviews/alias.md → reviews/grill-review.md`（指向 `A` **之内**、且目标是本次改名落点）⇒ 第 5 条不命中（本仓既有钉绿布局 `tests/test_orphan_reports.py:273`） |
| — | **把受保护文件搬进到达目录**（`git mv openspec/specs/x.md → archive/<到达名>/x.md`） | 红（仍要解释事件，M-D5 钉住） |
| — | 归档时**顺带改 change id**（`git mv changes/old-id archive/2026-10-15-new-id`） | 红（第 4 条）——⚠️ **今天亦红**（`archive_grant` 的名识别同样不满足）⇒ 这是**明写的拒绝面**、**不是本 change 新引入的**；取舍见 §8 Q1（选 (b) 则变绿） |

## 6. 文档影响

- `docs/gate.md`：§5.1.1 归档语义（判据从「R100」改成「目录新增 + 内容来源」）、§4（可达路径）、
  §3.2（时序建议）、§6（已知边界：删「R100 要求」，补树不可读 / 搬运现成证据 / 扫描面 / 报告可放 `reviews/` 之外）。
- `README.md`：接入指引里归档时序一段；**不**把出生即归档写成推荐流程。
- 本仓 `openspec/specs/`：`archive-awareness` 能力的 delta 见 `specs/archive-awareness/spec.md`。
- `proposal.md`：验收段的「对称性」补上 stale 维度的排除（R2 的 D-6）。
- **不改** `archive-awareness` 已归档 / 既有的其他 Requirement 文本（除本 change 明列的四条）。

## 7. Pre-Implementation Review

### 7.1 设计追问轮（独立零记忆审阅者，报告见 `reviews/grill-design.md`）

审阅者独立读了源码与 `archive-awareness` 的前身文档，复核了本稿的事实断言。**它确认了 3 条、推翻了 1 条设计缺陷、纠正了 4 处事实错误。** 本稿据此修订：

| # | 审阅者发现 | 本稿处置 |
|---|---|---|
| M1 | **规格自相矛盾**：Requirement 1 说「新建即到达」，同一 Requirement 的 Scenario 说「新建的 `archive/misc/` 不授予」，而正文**没有**名识别规则 | D1 补齐：把「有源时须名识别」写进正文并定义「有源」 |
| M2 | **对称性不变量按字面不可满足**：`stale_exempt_paths` 对 `archive/**` 整块豁免、对 active 的 `proposal/design/tasks` 不豁免 | D2 与 spec 都把不变量**限定到证据门槛维度**，并显式排除 stale 维度（`proposal.md` 本轮也补） |
| M3 | **基准未钉死**：`changed_files` 用 `base...head`（merge-base），基树查询若用 `base` 原树会与 diff 成员**对不上** | D1 第 1 条钉死为 **`merge-base(base, head)` 的树**，并加用例 |
| M4 | **事实错误**：`manifestcmd` **不调用** `change_targets` | D7 与 §3 第 4 条订正；不再声称该处共用 |
| M5 | **符号名错**：`gitutil.diff_name_status` / `checkcmd._check_protected_writes` 都不存在 | §1.1 改为 `changed_files`（`gitutil.py:99/105`）与 `_protected_writes`（`checkcmd.py:228/255`） |
| M6 | **既有测试必失败**：`:541` 的断言在 D1 下不再成立 | §5.2 逐条点名要改写的测试。⚠️ **R2 之后订正**：第 2 条收紧为「须含**全部**必需件」⇒ `:541` 的假目录缺 `reviews/` ⇒ **不再需要改写**（改为「不要误改」清单） |
| M7 | **停轮队列可瘦身**：初稿 Q1/Q4 能由代码定案 | §8 移出，附依据 |
| **新洞** | **改名一个已存在的归档目录 ⇒ 白捡一份现成证据** | D1 第 3 条 + §5.3 N8 |

**未复核项（审阅者明确标注，R1/R2 复核后仍成立）**：`proposal.md` 表里的具体相似度分数
（`R068/R069/R070/R090`）在本工作区**不可复算**——本仓从未归档过 change。
⇒ 实现期 4.2 必须用**接入方的真实提交**复算，不得直接引用本稿的数字。

### 7.2 对抗轮（R1，报告见 `reviews/grill-adversarial.md`）

独立零记忆对抗者，目标是**证伪** D1–D7。结论：**证伪成功 3 条**（F1 高危、F2 中危、F3 低-中危），
证伪失败 7 条（含「必须绿」的出生即归档与 move+重建 manifest 两条**实测绿**）。
本稿的处置：

| # | R1 发现 | 本稿处置 |
|---|---|---|
| **F1**（高危，端到端实测通过） | D1 第 3 条**只关 rename、没关 copy**：`cp -r` 现成归档目录 + 改两个 manifest 字段 ⇒ 零新证据的纯代码 PR **变绿** | **D1 新增第 5 条**（内容来源判据）；§5.3 **N9**；R2 复核：第 5 条的**当前形态**确实关掉了纯 `cp`（`arrived=False`） |
| **F2**（中危，新增假阴性） | 组织型子目录 `archive/2026/` 被判成「到达的 change `2026`」⇒ 缺件假阴性 | **D1 第 2 条**；§2.5 **C5**；§5.3 **N16**。⚠️ **R2 复算**：初稿的「≥1 个必需件」只修了一半（含 `reviews/` 子目录的组织型目录仍是 target）⇒ 本轮收紧为「**全部**必需件」（N17 钉住） |
| **F3**（低-中危，未列明的拒绝面） | 归档时顺带改 change id 被第 4 条拒绝，是否可接受未定 | 写进 §5.3 末两行（**明写的拒绝面**），取舍并入 §8 **Q1** |
| M-Q4 | 「`archive/` 非 change 子目录」假阴性被从停轮队列里丢掉 | 已作为 §8 **Q3** 回到队列 |
| M-D5（中危） | D5 的豁免措辞「属于某个到达组」过宽，会放开「把受保护文件搬进到达目录」 | **D5 收窄**：豁免还要求 `old_path` 落在 `<changes_root>/<active-id>/` 下；§5.3 加对照行 |
| M-DOC1 | `tasks.md` 3.5 与 `design.md` §3 第 4 条直接冲突 | 采纳 design 的订正（`manifestcmd` 不改），tasks 3.5 改写 |
| M-DOC2 | spec 写「上一条的**两条**判据」，而正文是四条 | spec 改为与正文一致（现为五条） |
| M-DOC3 | `tasks.md` 0.2 写「Q1–Q4」，`design.md §8` 只有 Q1–Q3 | tasks 与 design 的编号对齐 |
| M-DOC4 | spec 里「`manifest build --change <name>` … **共用同一实现**」重复了 M4 判为不实的主张 | 改成准确的共用项（`validate_change_dir` / `resolve_report_path`） |
| M-C1 | 条件 1 措辞「前缀下没有 tree entry」对「base 同路径是 blob」是盲的 | D1 第 1 条钉死为「该路径完全没有 entry」+ 精确 `ls-tree` 用法（D7 表）；§5.3 **N18**。⚠️ **R2 复算**：初稿只改了 D1 与 spec，**C6 / §5.1-11 / N11 三处残留自相矛盾**（说「是到达」）⇒ 本轮全部回写为「不授予」 |
| §E 低危（R-B） | D4 的 `archived_sources` 过宽，会把**别的仍在 head 的** active change 静默排除 | **D4 收窄**（源目录在 head 里已不存在才排除）；§5.1 第 12 条用例 |

**R1 的未验证项（原样保留，实现期不得当已验证）**：
① 接入方 asterwynd 的具体数字本工作区**无法复算**；② R1 的 F1 端到端是 **proxy**（用 active 目录跑通证据门禁）；
③ 浅克隆下 `ls-tree` 的确切失败模式未取得可靠证据（R2 补了探针：`--depth 1` 时 `merge-base` 无输出而 `ls-tree -r origin/main` 正常）；
④ merge commit 形态未实测（R2 的构造失误，仍未取得可判定结论）；⑤ 「`manifest build` 是否真的不需要感知到达」只复核了「不调 `change_targets`」这一**事实**。

### 7.3 对抗轮（R2，报告见 `reviews/grill-adversarial-r2.md`）

独立零记忆对抗者，针对**重写后**的 D1（五条判据，重点第 5 条）与 spec/tasks。
结论：**证伪成功 3 条**（A1/A2 高危、A3 中危）+ 2 条假阴性/误伤（B1/B2），
并复核了 R1 的 7 条失败项（纯 `cp` 确实被挡住、`copy+删源` 由第 3 条兜住、N8/N3/N4 照旧）。
**它判定不收敛**，并给出 M1–M5。本稿处置：

| # | R2 发现 | 本稿处置 |
|---|---|---|
| **A1**（高危，真 CLI 实测绿） | 初稿第 5 条的豁免 ①（「D 是某条记录的源目录」）是**逐记录**的 ⇒ `git mv` 一个无关文件进 A 就把整条判据洗白 | **判据重做**：现稿不再有「D 枚举 + 豁免」这套结构，改为**逐文件**的「新内容 or 本次搬来的」⇒ A1 自然关闭。§5.3 **N13**；§5.1 第 9 条 ⑥ |
| **A2**（高危，真 CLI 实测绿） | `E(D) ⊆ E(A)` 只识别「逐字节 + 同路径」的复制；改路径 / 加一个字节 / 删一个文件 / 混源 全部逃逸；`manifest build` 会**重算哈希** ⇒ 初稿表格里「改字节 ⇒ 红」**为假** | **判据重做**为 blob 级、**与路径无关**、**逐文件**的判据 ⇒ 六种变体全部关闭；§5.3 **N10–N12 / N15**；§5.1 第 9 条。初稿那张「四类穷举」表**删除**，改为**明写能力边界**（每个文件都改字节 + 重算哈希 ⇒ 不命中，属不设防的伪造面） |
| **A3**（中危） | D 扫描只覆盖**扁平** change 目录、且按相对路径匹配 ⇒ 嵌套 / 历史副本不可见 | 现稿的扫描面是 **`<changes_root>/**` 全量 blob**（不枚举 change 目录、不比路径）⇒ 嵌套源关闭；§5.3 **N14**；`changes_root` 之外的副本作为**已知边界**明写 |
| **B1**（中低危） | 第 2 条「≥1 个必需件」只修了半个 F2：含 `reviews/` 子目录的组织型目录仍是 target ⇒ 新假红 | 第 2 条收紧为「含**全部**必需件」；§5.1 第 10 条 + §5.3 **N17** |
| **B2**（中低危） | 「复制式归档」（`cp` 而不 `git mv`、源目录留着）会被第 5 条拒 | **接受**（该形态今天也红：全 `A` ⇒ 无 `R100` ⇒ 不授予）；写进 §4 R7 与 §8 **Q4**；对已知接入方（`git mv` 式）不构成误伤 |
| M1 | 第 5 条只识别一个点却声称堵住一类 | 判据重做（见 A2）；穷举表删除、边界明写 |
| M2 | 豁免 ① 可被一条无关 move 洗白 | 判据重做后**该结构整体消失**（无 D 枚举、无豁免）；R2 建议的「只留 ②」不再需要 |
| M3 | 4 处文档自相矛盾（C6/§5.1-11/N11 vs D1-1；§8 Q1 的「都绿」；`:131` vs `:136`；spec 的假保证） | 全部回写：C6 改「不授予」、§5.1 第 11 条重写、§5.3 N18；§8 Q1 例子重写；穷举表删除；spec 删掉那条假保证并改为**明写边界** |
| M4 | 第 5 条的能力边界没写进 design/spec | §D1 第 5 条的「已知边界」段 + spec 正文 + `docs/gate.md §6` 义务（§3 第 5 条） |
| M5 | 第 2 条「同一张表」措辞不准（同一张表、两种匹配语义；多段 `required_artifacts` 会让探测失明） | 第 2 条改为「与契约门**同一判定语义**（`<dir>/<artifact>` 路径存在）」，并说明实现用一条 `ls-tree -r` 判定 |

**R2 的未验证项（原样保留）**：① 接入方数字仍不可复算；② R2 的判据层结论来自**按 spec 逐字转写的模拟器**，
真实现若在枚举 / 匹配语义上不同则需重算（⇐ 本 change 的 §2.5 表与 D7 已把语义钉到命令级，降低这个风险）；
③ 「`merge-base` 成功但 `ls-tree` 失败」这一独立面仍未复现；④ merge commit 形态未取得可判定结论；
⑤ `proposal.md` 表里的两列对照未复算；⑥ 「接入方是否存在复制式归档流程」无法从本仓判定。

### 7.3b 对抗轮（R3，报告见 `reviews/grill-adversarial-r3.md`）

独立零记忆对抗者，针对 **R2 之后重做**的判据 2 / 判据 5。结论：**证伪成功 5 条**
（A1/A2 高危、A3/A4 中危、B1/B2/B3 中低危）。它**按现稿文本独立重写了一份判据模拟器**，在 R2 的全部 18 个构造上
复算，结论与 §7.4 的表**逐条一致**。**它判定不收敛**，给出 M1–M7。本稿处置：

| # | R3 发现 | 本稿处置 |
|---|---|---|
| **A1**（高危，真 CLI 实测绿） | 把三份报告**挪出 `reviews/`**（放 change 目录根）+ 手写 manifest 指过去 ⇒ 判据 5 按**路径前缀**取证据 ⇒ 证词整体出圈 | **`Ev(A)` 改为由数据推导**：`HASHED_ARTIFACTS` 的 artifact 路径整体 + 每份 manifest 的 `report_path` 目标（`resolve_report_path`）+ `reviews/**`。§5.3 **N19** |
| **A2**（高危，真 CLI 实测绿） | 给 `Ev(A)` 里**每一个**文件各加一个字节 + 官方 `manifest build` 重算 ⇒ 判据 5 零命中，而**报告的语义内容一字未改** | **承认天花板**：删掉初稿「等价于自己写一份完整证据」的**伪等价论证**（R3 判定为假，本稿照改），明写真实射程与「封堵它需要真实性 / 签名，属非目标」（§D1 第 5 条）。§5.3 **N21**；取舍进 §8 **Q4** |
| **A3**（中危） | 证据集按**路径前缀**取 ⇒ `specs` 换成同名普通文件、或 `tasks.md` 做成目录时，借用内容整体出圈 | `Ev(A)` 取 **artifact 路径整体**（是目录 ⇒ 其下全部文件；是普通文件 ⇒ 它自己）。§5.3 **N20** |
| **A4**（中危） | `gitutil` 的 `D` 记录 `old_path` 为空、被删路径在 `path` 里 ⇒ 「move + 被搬文件整体重写」仍留幽灵 active id（**今天也红**，非回归，但本 change 声称修好的形态 ii 只修好一档） | **D4 排除键补 `D` 侧 `path`**（§2 D4 的订正段）；§5.1 **2b** |
| **B1**（中危） | §5.2 给 `:494` 的改写配方**产出的到达目录不是 target**（新 active change 占同路径 ⇒ git 报 `M` 而非 `D` ⇒ 配不成改名 ⇒ 判据 5 命中 3 份） | 换成 R3 给的替代配方（`archive/x` 走出生即归档 + 在 `changes/x` 上做一次 `M`）；§5.2 第 2 条 |
| **B2**（中危） | `test_N6`（`:600`）被列入「不要误改」是**错的**：D4 收窄后它成为 active target ⇒ `:621` 的断言失守 | 移入「必须改写」（第 5 条），断言改成「`another-change` 仍按 active 契约校验」；§5.2 |
| **B3**（低-中） | 仓内**模板骨架**（`changes/_template/**`）被原样复制 ⇒ 误伤（已登记，但理由与「排除 `proposal`/`design`」的依据不自洽） | 明写「模板请放在 `changes_root` 之外」（**§D1 第 5 条「已知边界」+ §3 第 5 条 + `tasks.md` 6.1**）；作为 §8 Q4 的误伤证据 |
| **M5**（中） | 「必须改写（3 条）」与实列不一致 | ⚠️ R3 只落了一半（R4 复核为假）；本轮**已机械核对**：标题写 **5 条**、清单恰列 5 项（`:274`/`:494`/`:600`/`:109`/`:49`），R5 表的那处计数同步改齐 |
| **M6**（低-中） | `changes_root` 之外的现成证据 `git mv` 进来 ⇒ (a)(b) **同时**豁免同一份内容 ⇒ **判据 5 的完全旁路** | 从「低危边角」升格为**明写的完全旁路**（§D1 第 5 条「已知边界」）；`docs/gate.md §6` 登记（**§D1 第 5 条「已知边界」+ §3 第 5 条**） |
| **M7**（低） | `:378` 的注释更新未落 | 记进 `tasks.md`（实现期做） |
| **E-2**（低） | 判据 2 收紧后**近失文案变差**（件不齐 ⇒ 「没有任何 change 目录」，不点名缺的那一件） | `_require_change` 文案补一句：列出「`archive/` 下缺必需件的目录」（`tasks.md` 3.9） |

**R3 复核「成立」的声明**（负面证据）：`:541` 在「不要误改」清单里**正确**；`:577` 正确；`:378` 仍绿；
`:471` 的「每一个源」口径正确；R2 的 18 个构造与 §7.4 **逐条一致**；
必须绿的三条（纯 move / move+重建 manifest / 出生即归档）**全绿**；R2 的 B1 假红**确已修好**；判据 1/3/4 它**未能绕过**。

**R3 的未验证项（原样保留）**：① 接入方数字仍不可复算；② **到达判定那一半仍来自「按文本逐字转写」的模拟器**
（证据门那一半是真 CLI）——最敏感的四处：`Ev(A)` 是否含 `specs` 本体 / 是否把 `C` 记录算作 (b) /
「空文件」按 head blob 还是 worktree / D4 是否纳入 `D` 侧 `path`（本稿已把后两条写死）；
③ 浅克隆的独立失败面；④ merge commit 形态；⑤ 自定义 `review_manifest_glob` 的端到端；
⑥ `required_artifacts` 覆写成多段名的端到端；⑦ 大仓下逐字节撞车的概率（`tasks.md` 4.6）；
⑧ A2/A4 在接入方的**现实频率**。

### 7.4 作者侧复算（本工作区，`/tmp` 一次性模拟器 + scratch 仓；**不是**审阅者结论）

本稿的两条新判据（第 2 条、第 5 条）在落稿后由**作者**用一次性模拟器 `/tmp/sim_d1v3.py`
（只读 git 树、不碰仓内文件）在 **R2 留下的全部 18 个构造仓**（`/tmp/cases/*`，**审阅者造**）+ 自造构造上复算：

| 构造 | 结果 |
|---|---|
| R2 的 r1/r2/r3/r4/r5/r16/r19（纯复制 / 改路径 / 改一个字节 / 删文件 / 混源 / 复制+新增 / `specs` 换成文件） | 全部 `arrived=False`（第 5 条命中），**含真 CLI 曾实测绿的那三条** |
| R2 的 A1 构造 `/tmp/e2e_partial`（曾真 CLI 绿） | `arrived=False`（第 5 条命中 5 份证据文件） |
| R2 的 A3 构造 r21（源是嵌套归档目录） | `arrived=False`；`archive/2026/` 本身 `c2=False`（不是 target） |
| R2 的 B1 构造 r15（`archive/notes/` 含 `reviews/` 子目录） | `c2=False` ⇒ **假红修好** |
| r6 纯 move / r7 move+重建 manifest / r13 出生即归档 | 全部 `arrived=True`（**必须绿的三条不受伤**） |
| r8 改名既有归档目录 / r9 复制+删源 / r10 预存目录加文件 / r11 base 同路径是 blob / r14 从 active 复制 | 全部 `arrived=False`（分别由第 3 / 3 / 1 / 1 / 5 条命中） |
| 自造 E11（新 change 的 design stub 与 base 里某 change 逐字节相同） | `arrived=True` ⇒ **误伤已排除** |
| 自造 E12（原样复制兄弟 change 的 `specs/limits.md`） | `arrived=False`，命中项**只有** `specs/limits.md` ⇒ 误伤面**精确可解释** |

⚠️ 该复算是**按本稿逐字转写的模拟器**，不是实现。**R3 已按现稿文本独立重写了一份模拟器并在同一批构造上复算，
结论与本表逐条一致**；实现期仍必须重算（`tasks.md` 4.5/4.6）。

## 8. 停轮问题（Open Questions —— 逐条附本 change 真实场景的具体例子）

> 每条都给出**具体到参数 / 输入输出的前后对比**，便于快速判断。
> ⚠️ 编号在 R1 后重排过一次、在 R2 后**新增 Q4**；被移出队列的条目附依据。

### 已由代码 / 实测**定案**、移出停轮队列（不占用户时间）

| 曾经的提问 | 定案 | 依据 |
|---|---|---|
| 到达判定用「显式查基树」还是「只用 diff 推断」？ | **显式查基树**（无选择余地） | 只用 diff 会被 §5.3 **N3** 直接证伪：往**已存在**的归档目录加文件状态也是 `A` |
| 归档 target 的 stage 集合是否与 active 完全一致？ | **完全一致、零特判** | `checkcmd.py:105-119` 的 stage 硬门由 `code_hits` 触发；选「更松」即违反 D2 |
| 把**已存在**的归档目录**改名**，该不该授予资格？ | **不授予**（第 3 条 + 第 5 条） | 允许它等于**接受一个已知绕过**（零新证据的纯代码 PR 变绿）。R1 的 F1 与 R2 的 A2 进一步证明「白捡证据」有多个机制 ⇒ 没有「另一个可接受的策略」可选 |
| 「复制式归档」被拒（R2 的 B2）该不该放行？ | **拒绝**（= 第 5 条的必然结论） | 该形态今天也红（全 `A` ⇒ 无 `R100` ⇒ 不授予）；放行它就要放弃第 5 条，回到 R1/R2 已证伪的状态。若将来要「友好文案」（拒绝时点名「检测到整份复制自 `X`」），属实现细节 |
| 第 5 条的**实现形态**（指纹集合 vs 逐文件）该选哪个？ | **逐文件「新内容 or 本次搬来的」** | R2 实测指纹形态的六种零成本逃逸（A2）⇒ 指纹形态**不充分**；逐文件形态把它们全关掉，且更简单。**代价**（误伤面）见 Q4 |

### Q1 归档目录名「必须认得源 id」这条守卫（D1 第 4 条），对**有源**的到达是否保留？

- (a) **保留**（**当前稿的文本**）：`name == src` 或 `name.endswith("-" + src)` 才授予（**每一个**源都要满足）。
- (b) **删掉**（**本稿推荐**；grill 与 R1 都建议 (b)）：到达方式不设限，名字不必再核。
- **理由**：① 它原本要挡的形态（**单文件** move 进**已存在**的归档目录）已被第 1 条独立关掉；
  ② 「白捡现成证据」已由第 3 条与第 5 条在**记录层**与**内容层**关掉（R2 复核 A1–A3 后第 5 条已收紧）；
  ③ 剩下的唯一后果是**命名约定**，而它与「到达方式不设限」相抵。
- **具体例子**：`git mv openspec/changes/foo-x openspec/changes/archive/misc` + 改 `agent/x.py`（该 change 件齐、三份 manifest 齐）：
  - (a)：`misc` 不认得 `foo-x` ⇒ 不授予 ⇒ **红**，报「`agent/x.py` 属于必须挂 change 的路径……但本次 diff 里没有任何 change 目录」；
  - (b)：该目录在基准树里没有 entry、内容是本次搬来的 ⇒ 到达 ⇒ 走**同一套**证据门 ⇒ **绿**（证据不全才会红）。
  - **对照（R2 订正过的版本）**：把同样的内容 **`cp -r`** 到新建的 `archive/misc/`（源目录**不动**）——
    **两种选法都红**（第 5 条命中：内容不是本次搬来的）。⚠️ 初稿写「两种选法都绿」，那是 R2 的 M3 点名的错误文本。
- **推荐：(b)**。删守卫是**放宽**，所以即便裁 (a) 也不阻塞实现；裁 (a) 会让「归档时顺手改 change id」必须拆两步。

### Q2 `archive/**` 的 stale 豁免（「暗房」）本次一并收窄，还是另立？

- (a) **另立 issue，本次不动**（**本稿推荐**）：与本 change 正交；且它**今天就已存在**，不是本 change 造成的。
- (b) 本次一并收窄：范围膨胀到「审阅后允许出现哪些归档路径」，需要独立的证据推导。
- **具体例子**：已归档 change 的 `proposal.md`，在它那份 manifest 记的 `head_sha` **之后**被改一个字。
  - 今天 / (a)：**不判 stale**（命中 `policy.stale_exempt_paths` 末项 `openspec/changes/archive/**`）。
  - (b)：应当判 stale。但这与「到达识别」是两件事——修 (b) 得先回答「归档后哪些改动该被允许」。
- ⚠️ 这条**不阻塞**本 change：对称性不变量（D2）已限定到「证据门槛」维度、并显式排除 stale 维度。

### Q3 **嵌套归档布局**（`archive/2026/<name>/`）本次要不要支持？

- **背景**：R1 的 F2（组织型子目录被当成到达的 change）已由第 2 条修掉：`archive/2026/`、`archive/notes/`
  都不是 target（要含**全部**必需件才算 change 目录）。
- (a) **本次不支持**（**本稿推荐**）：今天也不支持——`archive_grant` 取 `archive/` 后**第一段**做目录名（`2026`），
  名字认不得源 id ⇒ 不授予 ⇒ 只改 `src/**` 的 PR 报「没有任何 change 目录」⇒ **红**。
  本稿的探测把它排除后，**行为与今天逐字相同（仍红）**，但报的是**准确的那句话**。
- (b) 本次支持：候选定义改成「`archive/**` 下**任意深度**、件齐、且相对基准树整体新增的目录」，
  change id 取该目录名（`10-15-foo`）——牵动 `change_id` 口径、中间层校验、别名集合与 `manifest build` 的目录解析。
- **具体例子**：某接入方按年份组织归档，落 `archive/2026/10-15-foo/{proposal.md, design.md, tasks.md, specs/, reviews/}`（件齐、三份 manifest 齐）+ 改 `src/app.py`：
  - 今天 / (a)：**红**——「`src/app.py` 属于必须挂 change 的路径……但本次 diff 里没有任何 change 目录」（逐字与今天相同，不多报「`archive/2026/` 缺少必需件」）；
  - (b)：**绿**——`2026/10-15-foo` 被认作到达。
- **推荐：(a)**（非目标已写「不改归档命名约定」；支持嵌套需要独立的「归档目录布局」议题）。

### Q4 第 5 条（内容来源）的**强度**：接受「逐字节天花板」，还是再加一档？

> ⚠️ 本轮（R3 之后）**重问**：初稿那两条「成本论证」已被 R3 用真 CLI 证伪（见 §7.3b 的 A1/A2），所以问题变具体了。

**真实的选择是：把「借用来的证据每个文件改一个字节」算不算违规？**

- **(c) 接受天花板 + 明写能力边界（本稿推荐）**：判据 5 挡**零改动 / 只动一处**的机械搬运
  （整份复制、改路径、改一个字节、删一个文件、混源、搬无关文件洗白、报告挪出 `reviews/`、换个路径形态、源在嵌套目录），
  **不挡**「跑个脚本给每份证据各加一个字节 + 重算 manifest」。
  - **具体例子**：一份 3 个月前的归档 change（三份真审阅报告齐）。攻击者 `cp -r` 到新名，
    再对每份证据文件跑一次 `printf '\n' >> "$f"`，然后跑 3 次官方 `manifest build`，最后改 `src/app.py`。
    - (c)：**绿**（判据 5 不命中；R3 用真 CLI 实测过 `check：通过 ✓`）——本稿把它**明写**为已知边界。
    - 代价：这一档绕过**存在且被文档承认**；收益：不引入新的误伤面，不需要新概念（签名 / 来源认证）。
- **(a)+(b) 再加一档强度**：把 `Ev(A)` 扩成「change 目录下**全部非空文件**（除 `proposal.md`/`design.md`）」——
  实测能关掉「报告挪出 `reviews/`」与「换路径形态」，但**关不掉** A2（每个文件各加一个字节仍然全绿），
  代价是误伤面变大（`reviews/*.manifest.json`、任何模板 / 样板文件都进集，R3 的 `m2` / `B3` 就是模板骨架被拒）。
  - 换言之：**它只解决一半，而那一半已被现稿用更精确的方式解决**（`report_path` + artifact 路径整体）。
- **真诚性判据**：R3 的原话——「只要判据是逐字节的，『全部改一遍』就永远逃逸，而那不是伪造，因为**内容没变**」。
  要真正封堵它，需要的是**真实性**（签名 / 可验证来源 / `reviewer_run_id` 的密码学绑定），
  而那是本 change 的**非目标**，也是 `contract.py:9` 早已声明的能力边界。
- **推荐：(c)**。理由：① 更强的档位并不能达到用户真正想要的效果（挡不住 A2），却带来真实误伤；
  ② 本 change 的目标是修**假阴性**（接入方的真实形态），安全面只需**不退化**——
  而 (c) 相对「今天」是**净增强**（今天连纯 `cp -r` 都拦不住，因为它走的是 R100 名识别）；
  ③ 把边界写在规范与 `docs/gate.md §6` 里，比留一个「声称堵住、实际漏」的半套守卫更安全。
- ⚠️ **若用户要求「连 A2 也挡」**：那需要另立 change（证据真实性 / 签名），
  **不是**在本判据上再加一条启发式——加启发式只会把误伤面推大而仍然漏 A2。
