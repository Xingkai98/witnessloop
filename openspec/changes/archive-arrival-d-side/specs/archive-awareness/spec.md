# archive-awareness — 配不上 rename 的旧路径也 SHALL 被认成搬移的一半（issue #31）

> 本 change 对 `archive-awareness` 做**一条新增**（不修改既有 Requirement、不放松任何到达判据）：
> 到达组按**新路径**收集 ⇒ `git` 配不上 rename 时那条 **`D`（旧 active 路径）** 掉队，
> 被误报「受保护路径被写入，但没有结构化解释事件」。
>
> ⚠️ **会反转的旧行为**：issue #31 的复现形态**改前红 1 项、改后 0 项**。
> ⚠️ **不会反转的**：**纯 `D`+`A` 搬移**（一个 `R` 都没有）**改前改后都要事件**（见下面最后一条 Scenario）——
> 本 change 只**减少**红、不新增，也**不**用「放宽判据」换绿。
>
> ⚠️ **承诺面（三轮对抗之后写死）**：本判据只承诺两条——① 放行 issue #31 的形态；
> ② **单调性**（任何输入下都不比改动前更宽 ⇒ 不新增红、不误伤）。**蓄意伪造 = 非目标**
> （本 capability 的既有边界：**防漂移、不防伪造**，真锚是远端 branch protection + required check）。
> 已实测出来的**蓄意**路径（自造到达目录当钥匙的 P7、再把源删干净的 PFIVE）**逐条登记**在
> `design.md §3` 的 N-l / N-n，**不假装挡住**。

## Requirement: `D` 记录 SHALL 能成为一次到达搬移的另一半

一条 `D` 记录（`status[:1] == "D"`，被删路径在 `change.path`、`change.old_path` 为空——
见 `gitutil._parse_name_status`）SHALL 被认成**某次到达搬移的另一半**，
当且仅当**存在一个到达目录 `A`**（`archive_arrivals(...)` 的结果，判据 1/2/3/5 一条不放松）同时满足：

1. `normalize(change.path)` 形如 `<changes_root>/<id>/<sub>`，**`<sub>` 非空**，
   且该路径**不在** `<changes_root>/archive/**` 下；
2. **覆盖**：`<id>` 在**基准树**（`M = git merge-base(base, head)`）里的**每一个**文件
   `<changes_root>/<id>/<sub'>`，都有一条**落在 `A` 之下、相对子路径逐字相同**
   （`f"{A.directory}/{<sub'>}"`）的记录——该记录可以是
   **一条 `R`/`C`**（`old_path` = 源路径），**或**一条 **`A`**（且该源路径在本次 diff 里有一条 `D`）。

满足时：

- 该 `D` 记录 SHALL 免于「受保护路径被写入，但没有结构化解释事件」（**两档**受保护路径都适用：
  `policy.protected_paths` 命中的，与不变集）；
- 它的源 id SHALL 与 rename 的旧侧一样，从「active change id」的取值里**排除**
  ⇒ SHALL NOT 产生幽灵 active id、SHALL NOT 让该 change 按 active 契约被重复校验。

⚠️ **为什么是「覆盖」而不是「给单条 `D` 找一条配得上的 `A`」**：后者（无论再加多少合取项）**四轮独立审阅各被造出一条绕过**：

- **G1**：任何 change 目录的骨架（`proposal.md`/`design.md`/`tasks.md`/`specs/…`/`reviews/…`）彼此重合 ⇒
  「删掉整个 active change `b`」+「同一次 diff 里另有一次正当搬移」就能凑齐（实测 `✗9 → ✗3`）；
- **S2**：在**仍活着**的 `b` 里 `git mv` 一个小文件进到达目录（污染身份锚）⇒ `check` **rc=0 全绿**；
- **S8**：**零蓄意**——删整个 change + 别处重建 manifest ⇒ git 自给的跨 change `R055` 配对；
- **P7 / PFIVE**：**自造**一个过判据的到达目录，把源的**一个**文件搬进去当「钥匙」（PFIVE 还把源的其余部分删干净）。

**覆盖把它们全部挡住**，因为它们的共同点都是「**只搬了一两个文件**」；而要伪造覆盖，
就必须把 `<id>` 的**每一份内容**都放进 `A` —— 那时 `A` **就是** `<id>` 的归档
（并且 `A` 会按归档 change 走**同一套**契约与证据门禁）⇒ **这不是启发式，是充分条件**。

⚠️ **代价（如实登记）**：**部分搬移**（源 change 仍在 head，只搬走一部分文件）⇒ 覆盖不成立 ⇒
那些 `D` 仍要事件（**与改动前同结论**，本 change 只**减少**红、不新增）。
⚠️ **单调性承诺**：对**任何**输入，本 change 判出的 findings SHALL ⊆ 改动前的 findings（不新增红、不误伤）。
⚠️ **边界**：本判据不宣称「任何伪造都挡得住」——那是本 capability 的既定边界
（`docs/gate.md §7`：**防漂移、不防伪造**，真锚是远端 branch protection + required check）；
但**已实测的四条绕过一条都不剩**。

### Scenario: issue #31 的复现形态改后判绿（**行为变化**）
- **Given** base 里该 change **已是 active**（docs-first 形态），head 里它整体在 `archive/<name>/` 下，
  其中一个受保护文件（如 `workflow-events.jsonl`）在 range 内被改写过 ⇒ git 报 **`D`（旧路径）+ `A`（archive 路径）**、不配对成 rename，
  而**其余文件配对正常**（⇒ 覆盖成立：源的每个文件都有落点）
- **When** 运行 `check`
- **Then** SHALL **不**报该 `D` 记录的「受保护路径被写入，但没有结构化解释事件」（**改动前红 1 项**）
- **And** 该 change 的源 id SHALL NOT 出现在 active change id 里

### Scenario: **纯 `D`+`A` 搬移**（一个 `R` 都没有）⇒ **豁免**（覆盖成立）
- **Given** 一次整目录搬移里**所有**文件都是 `D`+`A`（没有任何 `R`/`C`），**源的每个文件都有对应的 `A`**
- **When** 运行 `check`
- **Then** SHALL 免解释事件（封面上覆盖成立）
- ⚠️ **这一条是相对早先版本的修正**：甲/乙/丙 那几版要求「身份锚」（`source_ids` 非空）⇒ 反而把这一形态判成要事件；
  **覆盖把它改对了**

### Scenario: 只搬了**一两个**文件 ⇒ 不豁免（**四轮绕过统一被挡**）
- **Given** 任一条：(a) 删掉整个 active change `b` 而另有一次正当搬移（**G1**）；
  (b) 在仍活着的 `b` 里 `git mv` 一个文件进到达目录再删它的受保护文件（**S2**）；
  (c) 删整个 change + 别处重建 manifest 让 git 给出跨 change 的 `R055`（**S8**）；
  (d) 自造一个到达目录、只搬源的一个文件当钥匙（**P7**），再把源的其余部分删干净（**PFIVE**）
- **When** 运行 `check`
- **Then** 这些 `D` 记录 SHALL **仍然**要解释事件（**覆盖不成立**：源里有文件在 `A` 下没有落点）
  ⇒ ⚠️ **逐条都是「改造之前会漏」的形态**（G1 实测 `✗9 → ✗3`、S2 实测 `rc=0 全绿`、PFIVE 实测 `rc=0 全绿`）

### Scenario: **部分搬移** ⇒ 不豁免（**与改动前同结论**）
- **Given** 源 change **仍在 head**（只搬走了它的一部分文件）
- **When** 运行 `check`
- **Then** 那些 `D` 记录**照旧**要解释事件（覆盖不成立）——本 change **只减少红、不新增**

### Scenario: 往**已存在**的归档目录搬 ⇒ 不豁免（否定面，回归）
- **Given** `archive/<name>/` 在**基准树里已有 entry**（不是本次到达），本 PR 把某个 active change 的文件搬进去
- **When** 运行 `check`
- **Then** 仍报「受保护路径被写入，但没有结构化解释事件」（它不在到达组里）

### Scenario: **单独**删一个 active change 的文件 ⇒ 不豁免（否定面，回归）
- **Given** 本 diff 删掉 `<changes_root>/<id>/reviews/grill.manifest.json`，且**没有任何**配得上的 `A`
- **When** 运行 `check`
- **Then** 仍报该记录的「受保护路径被写入，但没有结构化解释事件」（覆盖不成立）

### Scenario: 受保护文件从 active change **外**搬进到达目录 ⇒ 不豁免（回归）
- **Given** 本 PR 删掉 `openspec/specs/x.md` 并在到达目录里新增 `archive/<name>/x.md`
- **When** 运行 `check`
- **Then** 仍报该 `D` 记录的「受保护路径被写入，但没有结构化解释事件」（第 1 条不满足）

### Scenario: 到达目录**不是真到达**（缺必需件 / 符号链接 / 内容来源存疑）⇒ 不豁免（回归）
- **Given** `archive/<name>/` 缺必需件、或是符号链接、或其内容来源不过判据 5
- **When** 运行 `check`
- **Then** 它**不在**到达组里 ⇒ 覆盖那条判据无对象 ⇒ 仍要事件（到达判据本 change **一条不放松**）

### Scenario: `<sub>` 为空 / 尾斜杠 ⇒ 不配对（回归；**纯函数级**钉子）
- ⚠️ 端到端构造不出来（`git` 不会把「目录本身」报成 `D`）⇒ SHALL 由**纯函数级**用例钉住
  （`d_move_halves` 对 `<sub>` 为空 / 以 `/` 结尾的输入返回空集）。

### Scenario: 重建**已存在**的 `reviews/*.manifest.json`（`M`）⇒ 仍要事件（回归，与本 change 无关）
- **Given** 本 diff 不含任何归档到达，只有一个既有 manifest 被重建（`M`）
- **When** 运行 `check`
- **Then** 恰好 **1 条**「受保护路径被写入，但没有结构化解释事件」（`D` 侧判据对 `M` 一概不适用）
