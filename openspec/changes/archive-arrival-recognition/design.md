# Design: archive-arrival-recognition

## 0. 一句话

把「本次 diff 里到达了一个归档 change」的判定，从**逐文件改名分（`R100`）**换成
**目录级事实（`archive/<name>/` 在 base 里不存在、在 head 里存在）**；
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
  ⚠️ 三点这件事是 **D1 的基准修订必须对齐**的理由（见 D1 第 3 条）。

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
因此成熟做法**不把相似度当作授权依据**，而是：① 用**显式的身份事实**（路径前缀 / 目录存在性 / 内容哈希）
判定归属；② 把「内容是否变了」交给**独立的完整性校验**（哈希绑定）去抓。
本 change 沿用这条：归属看**目录存在性**，内容看**既有的 manifest 哈希绑定**。

### 1.5 ⚠️ 上一版哪一条真的承重（初稿读错，此处订正）

初稿把 `archive-awareness` 的两条否定面读成「承重的安全守卫」。复核后**只成立一条**：

- **不承重**：「放宽 N2（出生即归档）会新开一块审阅后可改的暗房」。**假**——
  `policy.stale_exempt_paths`（`src/witnessloop/policy.py:77`）把 `archive/**` **整块**列为允许出现，
  暗房**今天就已经存在**（任何已归档 change 的 `proposal/design/tasks` 审阅后被改都不判 stale）。
- **承重**：「不得给 `base` 里**已存在**的归档目录凭空授予资格」。否则
  `git mv changes/z/notes.md → changes/archive/y/notes.md` 会把资格给 `y`，
  而源 change `z` 因 `archived_sources` 被排除、**静默逃检**。

⇒ 本 change **反转前一条、完整保留后一条**（且用**更强的**手段保留：见 D3）。

## 2. 决策

### D1 「到达」的判据 = 目录级事实，不看改名分

`archive/<name>/` 是**本次到达的 change**，当且仅当**四条同时成立**：

1. **基准树里不存在**：在 **`M = git merge-base(base, head)`** 的树里，`<changes_root>/archive/<name>/` 前缀下**没有任何 tree entry**；
2. **head 树里存在**：该前缀下至少有一条 tree entry；
3. **不是从另一个归档目录改名而来**：到达组里**没有**任何记录的 `old_path` 落在
   `<changes_root>/archive/**` 下（否则就是「把旧归档目录改个名 ⇒ 白捡一份现成证据」，见 §5.3 N8）；
4. **有源时须名识别**：若到达组里存在 `old_path` 落在 `<changes_root>/<src>/` 下（即**有源** `src`），
   则要求 `name == src` 或 `name.endswith("-" + src)`。

⇒ 与 `change.status` 是 `A` 还是 `R<分数>` **完全无关**。两只症状（出生即归档 / move 带内容改动）同一刀切掉。
⇒ **「出生即归档」没有源**（条件 4 无从施加）——这正是本 change 要接受的**反转**；
而「内容整体搬进一个新建目录、源 change 仍在 active」**有源** ⇒ 条件 4 生效（`archive/misc/` 不认得 `z` ⇒ 不授予）。

**⚠️ 基准 revision 必须与 `changed_files` 同源（本项由 grill 逼出，初稿只写「base」）**：
`gitutil.changed_files`（`:105`）用的是 **`base...head`**，即 diff 成员是按 **merge-base** 算的。
基树查询若改用 `base` ref 的**原树**，则当 base 分支在分叉点之后又前进时，
「到达判定」与「diff 成员」会**对不上**（同一目录可能被 diff 认为新增、却被基树认为已存在，或反之）。
⇒ 本 change 把基准钉死为 **`merge-base(base, head)`**，并加一条用例（§5.1 第 7 条）。

**为什么不用 diff 推断「是否新增」**：diff 里「`A`」只说明这条路径是新增的，
说明不了**那个目录**是不是新的——「预存归档目录被塞进一个新文件」也是 `A`，
而那种情形正是必须继续拒绝的（D3）。⇒ **只有查基树**才能把两者分开。

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
> 属 §8 Q3 的暗房议题，**本 change 不宣称**在该维度上对称。

**为什么这条足以防绕过**：一份「伪造的归档目录」要绿，仍必须凑齐与 active change 等价的全部证据
（提案/设计/任务/specs/reviews、三份 stage manifest、`reviewer ≠ author`、grill ≥3 条决策、
building review …）。**到达方式不降低任何一条门槛**——这也是它与「凭空多出一个免检区」的本质区别。

### D3 保留真正承重的那条守卫，且**升级**为基树判定

**SHALL NOT** 给一个 `base` 里**已存在**的归档目录授予资格。
`archive-awareness` 用「目标目录名必须认得源 id」（`name == src` 或 `name.endswith("-" + src)`）来挡，
但它自己承认有**残留边界**：目标名恰好认得源 id 的**部分 move** 仍会授予。

本 change 用 **D1 的第 1 条（基树不存在）**把它**真正关掉**：

| 构造 | `archive-awareness` | 本 change |
|---|---|---|
| `git mv changes/z/notes.md → changes/archive/y/notes.md`（`y` 已存在、名不认得 `z`） | 不授予 ✓ | 不授予 ✓（基树里 `y` 存在） |
| `git mv changes/z/notes.md → changes/archive/2026-x-z/notes.md`（该归档目录**已存在**） | **授予**（残留边界） | **不授予 ✓** |

**名识别守卫（`name` 认得 `src`）是否保留**见 §8 **Q2**（推荐：对「有源」的到达继续保留）。

### D4 幽灵 active id：按**到达集合**排除旧路径，而不是按 `R100`

`changed_change_ids` 的 `archived_sources` 改为「**到达组的全部记录的 `old_path`**」。
到达组是**目录级**的（D1）⇒ `R<100` 的记录也在组内 ⇒ 幽灵 active id 消失。

### D5 受保护写入的豁免：同一份到达集合，`R<100` 一并免

`_check_protected_writes` 里「归档 move 免解释事件」的判据，从**逐文件 `is_archive_move`**
换成「**该记录属于某个到达组**」。

**放宽了什么**：`R<100` 的记录（如重建过的 manifest）不再各报两条「受保护路径被写入，但没有结构化解释事件」。
**为什么可接受**：那 8 条本来就是**收尾次序的必然产物**，不是「偷偷改动」；
而 manifest 的**内容真伪**由它自己的哈希绑定与 stale 判据把关，
**不靠**「要不要写一条解释事件」把关（active change 新增 manifest 本来就免事件，门槛一致）。

**没有放宽什么**：对 `base` 里**已存在**的归档目录的修改 / 删除（`M` / `D`），
其目录不在到达集合里 ⇒ **仍逐条要解释事件**（回归钉）。

### D6 归属与别名的口径不变

归档 target 的 `change_id` 仍是**归档目录名**；`accepted_change_ids` 仍是
`{归档目录名} ∪ {能从 move 记录里解析出的源 id}`。
出生即归档（无源）⇒ 集合只有目录名——与今天「用 `manifest build --change <目录名>`」的口径一致，
**不新增**别名种类。

### D7 纯函数边界与接线

到达判定需要**基树**，因此：

- 新增 `gitutil` 帮助函数（如 `path_exists_at(root, rev, path)` / `tree_has_prefix(...)`），
  语义**fail-closed**：基树读不出来 ⇒ 报 finding、**不授予**（与 merge-base 求不出的既有处置同向）。
- `contract.change_targets(...)` 增加基准参数（**merge-base**，见 D1）；到达判定只留**一份**实现。
  ⚠️ **订正（grill 实测）**：初稿写「`checkcmd` 与 `manifestcmd` 共用 `change_targets`」是**错的**——
  `manifestcmd` **不调用** `change_targets`（`grep -n change_targets src/witnessloop/manifestcmd.py` 为空），
  它自己解析「active 优先、否则 `archive/<name>`」的目录（`manifestcmd.py:33-48`）。
  两者真正共用的是 `validate_change_dir` 与报告路径解析。⇒ 本 change **不**声称在 `change_targets` 上共用；
  若实现时发现 `manifest build` 也需要感知「到达」，须**另写清要共享什么**，不得含糊带过。
- 新增纯函数 `archive_arrivals(changes, changes_root, base_exists: Callable[[str], bool])`——
  把「基树查询」作为**注入的谓词**，判定本身保持可单测（不需要真 git 仓）。
- 保护写检查（`checkcmd`）接收同一份到达集合。

## 2.5 Code-Resolved Questions（不进停轮队列）

| # | 问题 | 结论 | 依据 |
|---|---|---|---|
| C1 | 「出生即归档」的归档目录名不认得任何源 id，名守卫会不会因此失效？ | 无源即无守卫可施；该路径的证据门槛与 active 完全一致（D2） | 本 change 的设计；用例见 §5.1 |
| C2 | 到达判据会不会把「预存归档目录 + 新增文件」误判为到达？ | 不会：基树里该目录存在 ⇒ D1 第 1 条不成立 | §5.3 的用例 N3 钉住 |
| C3 | 纯归档 move（全 `R100`）会不会因为换判据而**失效**？ | 不会：基树里不存在 ⇒ 到达；今天认得，修后仍认得 | `proposal.md` 表第 2 行（修前修后都通过） |
| C4 | 会不会把 `archive` 当成一个 change id？ | 不会：`archive_root` 自身不是 target（既有行为，回归钉） | `changed_change_ids` 既有的 `archive/**` 排除分支 |

## 3. 接线点（实现清单）

1. `src/witnessloop/gitutil.py`：新增基树查询帮助函数（fail-closed）。
2. `src/witnessloop/contract.py`：新增到达判定（注入式基树谓词）；改 `changed_change_ids` 与 `change_targets`。
3. `src/witnessloop/checkcmd.py`：把到达集合传给受保护写入检查；替换 `is_archive_move` 的用法。
4. `src/witnessloop/manifestcmd.py`：**订正后本 change 不改它**（它不调 `change_targets`，见 D7 的订正）。
   实现时若确认 `manifest build` 无需感知「到达」，此处留空并写明理由；若需要，则单独列出要共享的函数。
5. `docs/gate.md`：§5.1.1（归档语义）/ §4 / §3.2 的措辞与判据同步；§6 的已知边界更新。
6. `README.md`：接入指引里「归档时序」一段按新判据改写。

## 3.5 非目标

- **不收窄 `archive/**` 的 stale 豁免**（暗房）——既有口径、与本 change 正交，**另立 issue**（§8 Q3）。
- 不改归档命名约定；不引入签名 / 防伪造；不改退出码语义；不建立「change ↔ 代码路径」映射。
- 不把「出生即归档」写成**推荐**流程（它只是必须被正确识别的形态）。

## 4. 风险

| # | 风险 | 处置 |
|---|---|---|
| R1 | **豁免面被开大**（`archive-awareness` 的 C3 教训：只让 `_require_change` 闭嘴 ⇒ 零证据 PR 变绿） | §5.3 的每条否定面都配一条**同等强度**的证据门用例；D2 的对称性不变量写成断言 |
| R2 | 基树查询在浅克隆下失败 | `gate.yml` 已 `fetch-depth: 0`；仍失败则 **fail-closed**（报 finding、不授予），并有用例钉住 |
| R3 | 到达判定依赖 git 新 API，行为漂移 | 判定做成**注入谓词**的纯函数，单测不碰真 git；接线处另有集成用例 |
| R4 | 与 `manifest build` 的归档解析出现**两套实现** | D7：共用同一实现（`archive-awareness` 的 D7 同款纪律） |
| R5 | 旧行为被无意改动 | §5.2 回归面逐条点名；纯 move 与既有否定面各有用例 |

## 5. 测试策略（TDD）

### 5.1 用例（实现前红、实现后绿）

1. **出生即归档**：base 无 `changes/<id>`、head 有 `archive/2026-x-<id>/`（全 `A`）+ 改 `src/**` ⇒ 退出码 0。
2. **move 内带内容改动**：全 `R<100`（含重建过的 manifest）⇒ 退出码 0，且**无**幽灵 active id。
3. **接入方真实形状**：§1.3 第 1 行与第 3 行的两份 diff 各一条集成用例（可从接入方提交复算）。
4. **对称性**：同一份 change 内容，`changes/<id>/` 与 `archive/<name>/` 两种位置判绿判红一致（D2 不变量）。
5. **别名**：单纯 move（不重建 manifest）后归档前产出的 manifest 仍通过（既有用例保持绿）。
6. **fail-closed**：基树不可读 ⇒ 报 finding、不授予。
7. **基准 revision 对齐**：`base` ref 在分叉点之后前进过（原树 ≠ merge-base 树）⇒
   到达判定与 `changed_files` 的成员口径一致；反例构造：一个目录在 `base` 原树里**存在**、
   但在 `merge-base` 树里**不存在**（分叉后才加），此时它**是**到达（与 diff 口径一致）。
8. **名识别对「有源」的到达生效**：`archive/misc/`（新建、内容整体来自 active `z`）⇒ 不授予。

### 5.2 回归面（**必须保持绿**）

- 纯归档 move（全 `R100`）今天通过 ⇒ 修后仍通过。
- 只改 `src/**` 而**不建**任何 change 目录 ⇒ 仍红。
- **删除** change 目录（`D`，非 rename）⇒ 仍报「change 目录不存在」。
- 归档 target 的 `change_id` 别名行为不变。
- `archive/` 本身不是 change id。
- `uv run pytest -q` 全绿（基线数字在实现时实测填入，不写估计值）。

### 5.3 否定用例（**必须照样红 / 不授予**）

| # | 构造 | 期望 |
|---|---|---|
| N1 | 只改 `src/**`，不建 change | 红（`require_change_for`） |
| N2 | **修改**一个 `base` 里已存在的归档目录里的文件（`M`）+ 改 `src/**` | 红（不授予 ⇒ `require_change_for` 命中） |
| N3 | 往一个 `base` 里已存在的归档目录**新增**一个文件（`A`）+ 改 `src/**` | 红（基树里该目录存在 ⇒ 不授予） |
| N4 | `git mv changes/z/notes.md → changes/archive/y/notes.md`（`y` 已存在、名不认得 `z`）+ 改 `src/**` | 红（D3） |
| N5 | 删掉 change 目录（非 rename） | 红（「change 目录不存在」） |
| N6 | 到达的归档 change **零证据**（件齐、零 manifest）+ 改 `src/**` | 红，且逐条点名三份 stage manifest（**防 R1**） |
| N7 | 伪造体：新建 `archive/<name>/` 但缺必需件（如无 `specs/`）+ 改 `src/**` | 红（契约门） |
| N8 | **把 `base` 里已存在的归档目录 `archive/2026-09-30-foo/` 改名成 `archive/2026-10-15-foo/`**（新名在基准树里不存在 ⇒ 单看 D1 的 1/2 条会判「到达」），且其内容携带**完整现成证据** + 本 PR 只改 `src/**` | 红：D1 第 3 条（到达组里有 `old_path` 落在 `archive/**`）⇒ 不授予 |
| — | **同上但少了第 3 条**（= 初稿的判据）：新名是「到达」⇒ 那份现成证据被复用 ⇒ **一个只改了 `src/**`、零新证据的 PR 变绿** | ⚠️ 这是 grill 挖出的洞，D1 第 3 条正是为它而加 |

## 6. 文档影响

- `docs/gate.md`：§5.1.1 归档语义（判据从「R100」改成「目录新增」）、§4（可达路径）、§3.2（时序建议）、§6（已知边界删掉「R100 要求」那条、补「基树不可读 ⇒ fail-closed」）。
- `README.md`：接入指引里归档时序一段；**不**把出生即归档写成推荐流程。
- 本仓 `openspec/specs/`：`archive-awareness` 能力的 delta 见 `specs/archive-awareness/spec.md`。
- **不改** `archive-awareness` 已归档/既有的其他 Requirement 文本（除本 change 明列的三条）。

## 7. Pre-Implementation Review

### 7.1 设计追问轮（独立零记忆审阅者，报告见 `reviews/grill-design.md`）

审阅者独立读了源码与 `archive-awareness` 的前身文档，复核了本稿的事实断言。**它确认了 3 条、推翻了 1 条设计缺陷、纠正了 4 处事实错误。** 本稿据此修订：

| # | 审阅者发现 | 本稿处置 |
|---|---|---|
| M1 | **规格自相矛盾**：Requirement 1 说「新建即到达」，同一 Requirement 的 Scenario 说「新建的 `archive/misc/` 不授予」，而正文**没有**名识别规则 | D1 补齐为**四条**条件：把「有源时须名识别」写进正文并定义「有源」 |
| M2 | **对称性不变量按字面不可满足**：`stale_exempt_paths` 对 `archive/**` 整块豁免、对 active 的 `proposal/design/tasks` 不豁免 | D2 与 spec 都把不变量**限定到证据门槛维度**，并显式排除 stale 维度 |
| M3 | **基准未钉死**：`changed_files` 用 `base...head`（merge-base），基树查询若用 `base` 原树会与 diff 成员**对不上** | D1 第 1 条钉死为 **`merge-base(base, head)` 的树**，并加用例 |
| M4 | **事实错误**：`manifestcmd` **不调用** `change_targets`，本稿「共用同一实现」是假的 | D7 与 §3.4 订正；不再声称该处共用 |
| M5 | **符号名错**：`gitutil.diff_name_status` / `checkcmd._check_protected_writes` 都不存在 | §1.1 改为 `changed_files`（`gitutil.py:99/105`）与 `_protected_writes`（`checkcmd.py:228/255`） |
| M6 | **既有测试必失败**：`tests/test_archive_awareness.py:541` 的 `test_N2_a_forged_archive_grants_nothing` 断言的字符串在 D1 下不再成立 | `tasks.md` 2.6b 逐条点名要改写它，并写明语义反转 |
| M7 | **停轮队列可瘦身**：初稿 Q1/Q4 能由代码定案 | §8 移出，附依据；停轮从 4 条降到 3 条 |
| **新洞** | **改名一个已存在的归档目录 ⇒ 新名「在基准树里不存在」⇒ 白捡一份现成证据 ⇒ 零新证据的纯代码 PR 变绿** | D1 新增**第 3 条**（到达组里若有 `old_path` 落在 `archive/**` ⇒ 不授予）；§5.3 新增 **N8** 钉住 |

**未复核项（审阅者明确标注）**：`proposal.md` 表里的具体相似度分数（`R068/R069/R070/R090`）在本工作区**不可复算**——
本仓从未归档过 change。⇒ 实现期 4.2 必须用**接入方的真实提交**复算，不得直接引用本稿的数字。

### 7.2 对抗轮（R1）

（待跑；产物进 `reviews/grill-adversarial.md`。）

## 8. 停轮问题（Open Questions —— 逐条附本 change 真实场景的具体例子）

> 每条都给出**具体到参数/输入输出的前后对比**，便于快速判断。
> ⚠️ **初稿有 4 条，grill 后只剩 3 条**——两条能由代码定案的已移出（见下方「已定案」）。

### 已由代码/实测**定案**、移出停轮队列（不占用户时间）

| 初稿问题 | 定案 | 依据 |
|---|---|---|
| 到达判定用「显式查基树」还是「只用 diff 推断」？ | **显式查基树**（无选择余地） | 只用 diff 会被 §5.3 **N3** 直接证伪：往**已存在**的归档目录加文件状态也是 `A`，diff-only 会授予 |
| 归档 target 的 stage 集合是否与 active 完全一致？ | **完全一致、零特判** | `checkcmd.py:105-119` 的 stage 硬门由 `code_hits` 触发；选「更松」即违反 D2，属自相矛盾 |

### Q1「归档目录名必须认得源 id」这条守卫，对**有源**的到达是否保留？

- (a) **保留**（本稿推荐）：`name == src` 或 `name.endswith("-" + src)` 才授予。
- (b) 删掉（**grill 建议**）：已经有了「基准树里不存在」这条更强的判据，名字不必再核。
- **具体例子**：把 active change `z` 的内容整体搬进一个**新建**的、名字叫 `archive/misc/` 的目录，并顺手改 `agent/x.py`。
  - (a)：`misc` 不认得 `z` ⇒ 不授予 ⇒ 该 PR **红**，要求你按约定命名归档目录（`archive/<id>` 或 `archive/<date>-<id>`）。
  - (b)：该目录在基准树里不存在 ⇒ 授予 `misc` ⇒ 该 PR **绿**。
- 说明：这条守卫**只对「有源」的到达**生效；「出生即归档」没有源可核对，两种选法在那里**一样**（都授予）。

### Q2 `archive/**` 的 stale 豁免（「暗房」）本次一并收窄，还是另立？

- (a) **另立 issue，本次不动**（本稿推荐）：与本 change 正交；且它**今天就已存在**，不是本 change 造成的。
- (b) 本次一并收窄：范围膨胀到「审阅后允许出现哪些归档路径」，需要独立的证据推导。
- **具体例子**：已归档 change 的 `proposal.md`，在它那份 manifest 记的 `head_sha` **之后**被改一个字。
  - 今天 / (a)：**不判 stale**（路径在 `archive/**` 里，整块豁免）。
  - (b)：应当判 stale。但这与「到达识别」是两件事——修 (b) 得先回答「归档后哪些改动该被允许」。

### Q3 把**已存在**的归档目录**改名**（`archive/2026-09-30-foo/` → `archive/2026-10-15-foo/`），该不该授予资格？

- (a) **不授予**（本稿推荐，= D1 第 3 条）：改名后的新名在基准树里不存在，若只看「是否新增」会判成到达，
  于是**一个只改了 `src/**`、零新证据的 PR 会因为白捡那份现成证据而变绿**。
- (b) 授予：允许 adopter 自由重命名归档目录（把归档改名当簿记动作）。
- **具体例子**：某仓 3 个月前归档了 `archive/2026-09-30-foo/`（证据齐全）。今天有人
  `git mv openspec/changes/archive/2026-09-30-foo openspec/changes/archive/2026-10-15-foo`，
  并顺手改了 `agent/x.py`，**没有**产出任何新证据。
  - (a)：不授予 ⇒ `agent/x.py` 报「属于必须挂 change 的路径…」⇒ **红**。
  - (b)：授予 `2026-10-15-foo` ⇒ 那份 3 个月前的证据被复用 ⇒ **绿**。
- ⚠️ (b) 的代价是本 change 的核心安全属性；但 (a) 会让「归档目录改名」变成一次必须解释的动作。
