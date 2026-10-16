# archive-awareness — 配不上 rename 的旧路径也 SHALL 被认成搬移的一半（issue #31）

> 本 change 对 `archive-awareness` 做**一条新增**（不修改既有 Requirement、不放松任何到达判据）：
> 到达组按**新路径**收集 ⇒ `git` 配不上 rename 时那条 **`D`（旧 active 路径）** 掉队，
> 被误报「受保护路径被写入，但没有结构化解释事件」。
>
> ⚠️ **会反转的旧行为**：issue #31 的复现形态**改前红 1 项、改后 0 项**。
> ⚠️ **不会反转的**：**纯 `D`+`A` 搬移**（一个 `R` 都没有）**改前改后都要事件**（见下面最后一条 Scenario）——
> 本 change 只**减少**红、不新增，也**不**用「放宽判据」换绿。

## Requirement: `D` 记录 SHALL 能成为一次到达搬移的另一半

一条 `D` 记录（`status[:1] == "D"`，被删路径在 `change.path`、`change.old_path` 为空——
见 `gitutil._parse_name_status`）SHALL 被认成**某次到达搬移的另一半**，
当且仅当**存在一个到达目录 `A`**（`archive_arrivals(...)` 的结果，判据 1/2/3/5 一条不放松）同时满足：

1. `normalize(change.path)` 形如 `<changes_root>/<id>/<sub>`，**`<sub>` 非空**，
   且该路径**不在** `<changes_root>/archive/**` 下；
2. **同一次 diff** 里存在一条 `status[:1] == "A"` 的记录 `r`，其 `normalize(r.path)` 逐字等于
   **`f"{A.directory}/<sub>"`**（**相对子路径逐字相同**）；
3. **`A.source_ids == {<id>}`** —— 即 git 的相似度配对认为「`A` 是从 `<id>` 搬来的」，
   且**没有第二个** change 被配进同一个到达目录
   （`contract.archive_arrivals` 收集的 `source_ids` 就是那些 `R`/`C` 记录的源）。

满足时：

- 该 `D` 记录 SHALL 免于「受保护路径被写入，但没有结构化解释事件」（**两档**受保护路径都适用：
  `policy.protected_paths` 命中的，与不变集）；
- 它的源 id SHALL 与 rename 的旧侧一样，从「active change id」的取值里**排除**
  ⇒ SHALL NOT 产生幽灵 active id、SHALL NOT 让该 change 按 active 契约被重复校验。

⚠️ **第 3 条是承重的、不是装饰**，而且它必须是「**恰为** `{<id>}`」（两轮独立审阅各实测出一条绕过）：
① **grill 的 G1**：任何 change 目录的骨架（`proposal.md`/`design.md`/`tasks.md`/`specs/…`/`reviews/…`）
彼此大量重合 ⇒ 「删掉**整个** active change `b`」+「同一次 diff 里另有一次正当搬移」就能凑齐前两条（实测 `✗9 → ✗3`）；
② **对抗轮的 S2**：在一个**仍活着**的 change `b` 里 `git mv` 一个小文件进到达目录（污染 `source_ids`）⇒
「`<id> ∈ sources`」那一版会被洗白（`check` **rc=0 全绿**）；
③ **对抗轮的 S8**：**零蓄意**——只删掉整个 change 目录 + 在别处重建 manifest，git 自己就会给出
**跨 change 的 `R055` 配对**（两份 manifest 的骨架天然 >50% 相似）⇒ 同样洗白。
⇒ 三条里只有「**恰为** `{<id>}`」同时挡住 ②③。
⚠️ **与 `R`/`C` 侧的差异（如实登记）**：`R`/`C` 是 git **逐文件**配对，`D`+`A` 只能**按相对子路径 + 源身份**推断
⇒ 证据来源同一个（都是 git 的配对），但推断面更窄。
**边界**：本判据**防漂移、不防蓄意伪造**（与本 capability 的既有边界同源：真锚是远端 branch protection + required check）。

⚠️ **代价（如实登记）**：当 git 把**第二个** change 的文件也配进同一个到达目录时，
这条搬移里所有的 `D` 都会**失去**豁免（多要一条解释事件）。那是**刻意的 fail-closed 方向**——
本判据的取向是「宁可多要一条解释，也不静默放过一次删除」。

### Scenario: issue #31 的复现形态改后判绿（**行为变化**）
- **Given** base 里该 change **已是 active**（docs-first 形态），head 里它整体在 `archive/<name>/` 下，
  其中一个受保护文件（如 `workflow-events.jsonl`）在 range 内被改写过 ⇒ git 报 **`D`（旧路径）+ `A`（archive 路径）**、不配对成 rename，
  而**其余文件配对正常且都属于同一个源**（⇒ `A.source_ids == {<id>}`）
- **When** 运行 `check`
- **Then** SHALL **不**报该 `D` 记录的「受保护路径被写入，但没有结构化解释事件」（**改动前红 1 项**）
- **And** 该 change 的源 id SHALL NOT 出现在 active change id 里

### Scenario: **删掉整个 active change** 且别处有一次正当搬移 ⇒ 仍要事件（**杀手用例**）
- **Given** 同一次 diff 里 (a) 一次**正当**搬移产生了到达目录 `A`（`A.source_ids = {<别的 id>}`），
  且 (b) **另一个** active change `b` 被**整体删除**（它的文件全是 `D`，子路径与 `A` 里的重合）
- **When** 运行 `check`
- **Then** 仍 SHALL 报 `b` 的每个受保护文件的「受保护路径被写入，但没有结构化解释事件」
  （**第 3 条**不满足：`b ∉ A.source_ids`）——⚠️ **改前会漏**（grill 实测 `✗9 项 → ✗3 项`）

### Scenario: 往**已存在**的归档目录搬 ⇒ 不豁免（否定面，回归）
- **Given** `archive/<name>/` 在**基准树里已有 entry**（不是本次到达），本 PR 把某个 active change 的文件搬进去
- **When** 运行 `check`
- **Then** 仍报「受保护路径被写入，但没有结构化解释事件」（不在到达组里 ⇒ 第 3 条不成立）

### Scenario: **单独**删一个 active change 的文件 ⇒ 不豁免（否定面，回归）
- **Given** 本 diff 删掉 `<changes_root>/<id>/reviews/grill.manifest.json`，且**没有任何**配得上的 `A`
- **When** 运行 `check`
- **Then** 仍报该记录的「受保护路径被写入，但没有结构化解释事件」（第 2 条不满足）

### Scenario: 受保护文件从 active change **外**搬进到达目录 ⇒ 不豁免（回归）
- **Given** 本 PR 删掉 `openspec/specs/x.md` 并在到达目录里新增 `archive/<name>/x.md`
- **When** 运行 `check`
- **Then** 仍报该 `D` 记录的「受保护路径被写入，但没有结构化解释事件」（第 1 条不满足）

### Scenario: `<sub>` 为空 ⇒ 不配对（回归）
- **Given** 一条 `D` 记录的路径正好是 `<changes_root>/<id>`（目录本身）
- **When** 运行 `check`
- **Then** 它 SHALL NOT 被认成搬移的一半（第 1 条要求 `<sub>` 非空）

### Scenario: 拖一个**仍活着**的 change 进来 ⇒ 不豁免（**对抗轮的 S2 杀手用例**）
- **Given** 在一个**仍然活着**的 change `b` 里 `git mv` 一个小文件进某到达目录 `A`
  （于是 git 配对 ⇒ `b` 被配进 `A.source_ids`），**再删**掉 `b` 的一个受保护文件（`D`+`A` 同相对子路径）
- **When** 运行 `check`
- **Then** 仍 SHALL 报 `b` 那条记录的「受保护路径被写入，但没有结构化解释事件」
  （**第 3 条**不满足：`A.source_ids ≠ {b}`）——⚠️ **「`<id> ∈ sources`」那一版会漏**（实测 rc=0 全绿）

### Scenario: **零蓄意跨配对** ⇒ 不豁免（**对抗轮的 S8**，保守方向）
- **Given** 只删掉整个 change 目录 + 在别处重建 manifest，git **自己**给出跨 change 的 `R055` 配对
  （`another-change/reviews/grill.manifest.json → archive/<name>/…`）
- **When** 运行 `check`
- **Then** 该搬移的 `D` SHALL **保持**要解释事件（`source_ids` 被污染 ⇒ 第 3 条不满足）
  —— 这是**刻意的保守**：宁可多要一条解释事件，也不把一次删除洗成搬家

### Scenario: **纯 `D`+`A` 搬移不被豁免**（**已登记的限制**，改动前后同结论）
- **Given** 一次整目录搬移里**所有**文件都是 `D`+`A`（没有任何 `R`/`C` ⇒ `A.source_ids` 为空）
- **When** 运行 `check`
- **Then** 源侧的受保护文件**照旧**要解释事件（**第 3 条不成立**）——⚠️ 这与**改动前**结论相同，
  **不是**本 change 引入的新红；原因与代价见 `design.md §2 D1` 与 §3 N-i。
  ⚠️ 同一形态下到达目录**没有** source id 别名（`contract.archive_arrivals` 只从 `old_path` 收集）
  ⇒ 它的 manifest **必须**用归档目录名（否则报「`manifest.change_id` 与目录不符」）——#29 文档规定的次序已经这么写
