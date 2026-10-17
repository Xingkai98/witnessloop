# Grill（独立零记忆）：archive-arrival-d-side

> 对象：`openspec/changes/archive-arrival-d-side/{proposal,design,tasks}.md` + `specs/archive-awareness/spec.md`。
> 本文件由**零记忆 grill** 写：设计稿里的「实测」「文件:行号」「必然是」一律当待验证断言。
> 工作副本：`git rev-parse HEAD` = `f82595e5321de46a8051d6c75b5aa1acaa3406cd`（分支 `gate-ref-pins-package/tasks-bookkeeping`）。
> 实验**全部**在 `/tmp/g31*` 的副本里做（`git archive HEAD | tar -x -C …`）；仓内只写了本文件。

## Reviewer

**读了什么**：`proposal.md` / `design.md` / `tasks.md` / `specs/archive-awareness/spec.md` 全文；
issue #31 正文（`gh api repos/Xingkai98/witnessloop/issues/31 --jq .body`）；
`src/witnessloop/{contract.py,checkcmd.py,gitutil.py,paths.py,policy.py}` 的相关段；
`tests/test_archive_awareness.py`（F1–F18 = 18 条、N1–N6 = 6 条）、`tests/test_archive.py`、
`tests/test_archive_arrival.py`、`tests/{conftest.py,helpers.py}`。

**跑了什么**（命令 + 原始输出要点）：

| # | 命令 | 结果 |
|---|---|---|
| 1 | `cd /tmp/g31base && PYTHONPATH=src python3 -m pytest -q` | `702 passed in 143.81s`（= 基线，与 design 声称一致） |
| 2 | 原型：在 `/tmp/g31` 按 **§2 D1 逐字**实现 `d_move_halves` + 接线两处消费，`python3 -m pytest -q` | `702 passed in 62.60s` ⇒ D1 对既有 702 条**零回归**（也说明既有测试**一条都钉不到**新否定面） |
| 3 | 探针 C（删**整个** active change `b` + 另一次出生即归档的到达）：`/tmp/g31base`（未改） vs `/tmp/g31base`（带原型） | 未改 **✗ 9 项**（含 `b：change 目录不存在` + 3 条 `受保护路径被写入`）→ 带原型 **✗ 3 项**，那 6 条**全部消失** |
| 4 | 探针 E（`b` **仍在 head** 时删它的 `reviews/grill.manifest.json` + 别处同子路径 `A`）：cond4 在 vs 不在 | cond4 在 ⇒ `✗ 3 项`（含该条的「受保护路径被写入」）；**cond4 删掉 ⇒ `EXIT=0`（全绿）** |
| 5 | 纯函数探针（复用 `tests/test_archive_arrival.py` 的 `FakeTree`）直调 `d_move_halves` / `changed_change_ids` | 纯 `D`+`A` 下 `source_ids=[]`、`accepted_change_ids={'2026-10-15-z'}`；混合形态 `source_ids=['z']`；`b` 消失时 `d_move_halves` 返回 b 的**全部** D、`changed_change_ids==[]` |
| 6 | 变异测试：删掉 `contract.changed_change_ids` 里 `if not change.old_path: candidates.append(change.path)` 两行，跑 3 个归档测试文件 | `65 passed` ⇒ **那两行是死代码** |
| 7 | 探针 G/H（整目录搬移、**全部** D+A）：manifest 保留原 id vs 重绑成归档目录名 | 保留原 id ⇒ 3 条 `manifest.change_id='add-retry' 与目录不符`；重绑 ⇒ 该条消失 |
| 8 | `git diff -M --name-status` + `gitutil.changed_files`（各探针里 dump） | 复刻出 issue #31 同形 diff（`D …/workflow-events.jsonl` + `A …/archive/<name>/workflow-events.jsonl`），并确认**删整个目录**时 git 逐文件报 `D`、**不会**报「目录本身」的 D |

**没能复算的**：

- issue #31 的**原始**实测：`git cat-file -e 8e5fc83b` / `d94c08334` 在本仓均 `fatal: Not a valid object name`
  （那是接入方 asterwynd 的仓）⇒ 「原红 1 项」「`git diff` 里只有一条 `D`」「34 个变更文件」**未验证**，
  只复刻了**形态**（探针 8）。
- 探针 3–7 用的是**我自己**按 D1 逐字转写的原型，不是实现者的代码；结论对「按 D1 实现」成立，
  对实现者的**具体**写法不自动成立（尤其 G1 的修法会改判据）。
- 真实现（`d_move_halves` 落盘 + `docs/gate.md §5.1/§7` 文案）尚未存在 ⇒ tasks 3.1–3.4、4.2、4.3 均**未验证**。

## Confirmed Decisions

- **决策（D1）：§2 D1 的四条条件**可以同时**被一次「删掉整个 active change 目录」满足 ⇒ 判据不充分。**
  构造：base 上 `add-retry` 与 `another-change` 两个 active change；feature 里 ① 正当归档 `add-retry`（`R100`），
  ② `git rm -r changes/another-change`。此时 `another-change/reviews/grill.manifest.json` 这条 `D`：
  ① 在 `openspec/changes/another-change/` 下、`<sub>` 非空 ✓；② 同 diff 里有 `A`
  `archive/<name>/reviews/grill.manifest.json`（子路径逐字相同）✓；③ `<name>` 是本次到达 ✓；
  ④ `openspec/changes/another-change` 在 head 树里没有 entry（**整目录被删**也算）✓。
  ⇒ 四条全满足，删除被洗成「搬家的旧侧」。
  **来源:** 探针 3（未改 `✗ 9 项` → 带原型 `✗ 3 项`，消失的正是 `another-change` 的 3 条
  「受保护路径被写入」与 3 条按 id 校验的 finding）；探针 5 纯函数侧 `d_move_halves` 返回
  `['openspec/changes/b/design.md', ... 全部 5 条]` 且 `changed_change_ids == []`；
  代码路径 `contract.py:378-392`（`moved_sources`）+ `:393-402`（按 id 全量排除）。
  **为什么它一定是洞**：`design.md §3` 的 **N-c 自己声明**「删掉整个 active change 目录」不得被豁免；
  §4 R3 的理由「只有当两个 active 目录都**整体搬走**时才可能」把「搬走」与「消失（删除）」混为一谈
  —— 第 4 条只问「head 里有没有 entry」，删除同样满足。
  ⚠️ 结构性放大：本仓**每个 change 目录布局相同**（`proposal/design/tasks/specs/reviews`），
  ⇒ `<sub>` 逐字相同这条「证据」几乎不携带信息 —— 任意一次到达都能给任意一个被删 change 提供配对。

- **决策（D2）：第 4 条是**必须**的（§6 第 1 行的论断成立）。**
  把 cond4 从原型里删掉后，构造「`b` **仍在 head** 时删它的 `reviews/grill.manifest.json`，
  别处有一次到达且同子路径有 `A`」⇒ `check` **`EXIT=0`（全绿）**，即「删一个仍在 active 的 change 的
  受保护文件」被完全洗白；加上 cond4 后同一 diff 报 `✗ 3 项`（含该条的「受保护路径被写入」）。
  ⇒ §2 D1 与 §6 第 1 行「不加第 4 条就会开一个绕过」**可复算为真**。
  **来源:** 探针 4（`/tmp/g31no4`：`EXIT=0`；`/tmp/g31`：`✗ 3 项`）；issue #31 正文亦点名
  「单独删一个 active change 的文件不得因此获得豁免」。

- **决策（D3）：§1「现状（逐行实测）」的代码事实**逐条**成立**（行号逐条抽查命中）。**
  `gitutil._parse_name_status`（`gitutil.py:210`）对非 `R`/`C` 走 `Change(raw, fields[i + 1])`（`:224`）
  ⇒ 被删路径进 `path`、`old_path=None`（`Change` 在 `:16`、`old_path` 在 `:26`）；
  `checkcmd._archive_move_exempt`（`:324`）第一句 `if not change.old_path: return False`（`:335`）
  ⇒ `D` 记录**永远**拿不到豁免；到达组按新路径收集（`contract.py:300-302`）⇒ `D` 进不了组。
  另：`R`/`C` 侧 `moved_content`（`contract.py:274-280`）确实**只**吃 `old_path`
  ⇒ 纯 `D`+`A` 形态下它是空的。
  **来源:** `grep -n` 逐条比对（`210/224/16/26`；`324/335`；`253/300-302/355/378-392/391/393-402`）；
  探针 5 实测纯 `D`+`A` 的 `source_ids == []`。

- **决策（D4）：`changed_change_ids` 里那段「`D` 侧」分支是**死代码**，且既有测试钉不到它。**
  `arrival.records` 只含 `path` 落在到达目录下的记录；`D` 记录的 `path` 是**旧 active 路径**，
  即使落在 `archive/` 里也会被 `:388` 的 `under_path(normalized, archive_root)` 提前 `continue`
  ⇒ `if not change.old_path: candidates.append(change.path)`（`contract.py:381-383`）永不生效。
  **来源:** 探针 6（删掉该分支后 `tests/test_archive_arrival.py` + `test_archive_awareness.py` +
  `test_archive.py` 仍 `65 passed`）；`tests/test_archive_arrival.py:300`
  `test_changed_change_ids_covers_d_side_paths_when_the_file_was_rewritten` 之所以绿，
  是 4 条 `R100` 兄弟记录把源 id 放进了 `moved_sources`（与 `design.md §1` 的说法一致），
  **不是**那条 `D` 记录起的作用 ⇒ 该测试名/注释**过度声称**。
  ⇒ 对 §2 D2 的「落点只有一处实现」：今天是**零处**（D 侧无处），明天若只**新增** `d_move_halves`
  而不删这段死码，就会**两套 D 谓词并存**（潜在第二份判据）。

- **决策（D5）：本 change 自己承诺的「纯 `D`+`A`」形态，会在**别名面**上比 `R` 形态**多一条红**。**
  到达 target 的 `accepted_change_ids = {归档目录名} ∪ arrival.source_ids`（`contract.py:448`），
  而 `source_ids` 只由 `R`/`C` 的 `old_path` 产生（`:314-320`）⇒ 纯 `D`+`A` 形态
  `source_ids == frozenset()` ⇒ 别名集合里**没有源 id**。于是接入方若照 `R` 形态的既有惯例
  （`tests/test_archive_awareness.py:685` `test_F3_…` 明示：归档时可改 id、manifest 保留原 id 也接受）
  **不重绑** manifest，就会吃到 `manifest.change_id='add-retry' 与目录不符`（`contract.py:657-660`）。
  **来源:** 探针 7（原地保留原 id ⇒ 3 条「与目录不符」；重绑成 `2026-10-14-add-retry` ⇒ 该条消失）；
  探针 5（纯 `D`+`A` `accepted_change_ids={'2026-10-15-z'}` vs 混合形态 `{'2026-10-15-z','z'}`）。
  ⇒ `design.md §6` 第 4 行的依据（「issue #31 的实测里那种形态没有『与目录不符』的红」）
  只覆盖**实测的混合形态**，对本 change 新引入的纯 `D`+`A` 形态**不成立**。

- **决策（D6）：§3 的 N-a…N-h 钉子审计（逐条找现有测试）。**
  有钉子：**N-b** = `tests/test_archive.py:60` `test_deleting_an_evidence_file_still_needs_an_event`（弱形态：diff 里没有任何到达）；
  **N-e** = `tests/test_archive_awareness.py:722` `test_F5_…`（`R100` 形态）；
  **N-g** = `tests/test_archive_awareness.py:249` `test_rebuilding_an_already_archived_manifest_needs_one_event_each`；
  **N-h** = `test_F8`（缺件）/`test_F4`（白捡内容）/`test_F9`（符号链接目录）/`test_F10`（gitlink）；
  **N-a** 只有 `test_N6`（`:585`）的 **R** 形态 + `test_N4`（`:562`）的 **M** 形态。
  **没有钉子**：**N-d**（`b` 仍在 head + 同子路径 A —— 我的探针 4 就是它）、
  **N-f**（`<sub>` 为空）、**N-a 的 `D`+`A` 形态**、**N-c 的「受保护写入」面与混合形态**（= G1）。
  **来源:** 逐条 `grep`/读用例（上列文件:行号）；探针 2 显示带原型的**全量 702 passed**
  ⇒ 新判据没被任何既有测试约束 ⇒ 缺口只在 tasks 2.3 的清单里，尚未落地。
  （`design.md §5.4` 的「既有 18 条 F 组 + 6 条 N 组」计数**正确**：`F1–F18`、`N1–N6`，N5 在 `:338`。）

## Open Questions

### Q1 修 #31 会新增一个**豁免面**，而它可被伪造绕过——接受吗？

- **事实（五轮对抗实测）**：任何**结构**判据都能被「控制整个 diff」的伪造者一起造出来。
  最后一版（**覆盖**：归档目录必须装下源 change 的**每一个相对子路径**）挡住了前四条绕过
  （G1/S2/S8/P7/PFIVE），但**挡不住第五条 X1**——把那些相对子路径用**全新内容**造齐 + 删源 ⇒ `check` **通过 ✓**。
- **具体例子（最小伪造 diff，可复算）**：base 里 change `b` 是 active（12 个文件）→ 新建
  `openspec/changes/archive/<name>/` 并造出**同样的 12 个相对子路径**（内容全新）→ 删掉整个 `b/` → 提交 ⇒
  改动前同一 diff 报 4 项（`b` 的受保护文件「没有结构化解释事件」），改后 **0 项**。
- **唯一有充分性的是「内容同一性」**（`A` 里必须是 `b` 的那些字节）——但它会把 **issue #31 自己的复现形态**判红
  （那条掉队的文件**本来就在 range 里被改写过**）⇒ **不能用**。
- **三条路**：**A**（推荐）按覆盖落地 + 如实写明可被伪造绕过（登记 X1，与既有边界「防漂移不防伪造」一致）；
  **B** 不发豁免、让接入方给那条文件写一行解释事件（**与 issue #31 正文的诉求相反**）；**C** 只豁免非受保护文件
  （**等价于不修**，issue 的那条恰好是受保护的事件文件）。
- **➡️ 推荐 A**，但这是**产品取舍**，不替用户拍板 ⇒ 本报告的 `## User Confirmation` **留空**，
  `tasks.md 3.9` 记为**停轮未解除**，PR 开成 **draft**。


## User Confirmation

> 停轮已于 **2026-10-17** 解除：用户对 `## Open Questions` 的 **Q1** 拍板如下（非「按推荐」类占位）。
> ⚠️ 本节落盘后本报告的 `report_hash` 已变化 ⇒ grill manifest 必须**重建**。

- **Q1**: 用户答复：**选 B —— 不发豁免**。那条掉队的 `D` 记录**照旧要求解释事件**（判定与改动前逐字相同）；由接入方在**同一个开发 PR 内**补**一行** `protected_artifact_explained` 事件（`artifact_path` 指向该文件），**不允许因此增加 PR 数量**。用户明确确认：「**纯搬移不用写，只有归档时顺手改了被搬文件才需要；仍然一个 change 一个 PR**」。⇒ 本 change 的交付改为「**让 finding 可行动**」（诊断依据 + 一行补救 + 可直接复制的 JSON 示例），**不新增任何豁免面**（`design.md §2`）。；确认时间: 2026-10-17

## 风险

- **R-a（我新发现，未在 §4 登记）**：`§3` 与 `spec` 的否定面清单**各自缺项**且措辞不同 ——
  `design.md §3` 有 N-c、spec **没有** N-c 的 Scenario；`design.md §4 R1` 明写「如实写进 spec 的
  Scenario」，而 spec 里**没有** R1（部分搬移 + 某个文件没被 git 配上）的 Scenario
  ⇒ 「规格可测」在这两格上不成立（`specs/archive-awareness/spec.md` 全文 5 个否定面 Scenario：
  N-a/N-b/N-d/N-e/N-f；无 N-c、无 R1）。
- **R-b**：`§4 R2`（配对靠推断、伪造空间比 `R`/`C` 大）**方向正确但偏乐观** —— 在本仓「所有 change
  目录同布局」的前提下，`<sub>` 相同不是弱证据而是**几乎无证据**，所以 §2 D1 的第 2 条
  实际不承担防御职责（真正承担的是第 4 条，而第 4 条在「删除」上失效）。
- **R-c（§4 R4 我复核为真）**：`head_rev` 树读不出来时 `checkcmd` 在到达判定前就
  `gitutil.GitError` ⇒ 报 finding 退 1（`checkcmd.py:159-168`）⇒ `d_move_halves` 只在树可读时被调到，fail-closed 成立。
- **R-d**：`d_move_halves` 会在 `checkcmd._protected_writes` 与 `contract.changed_change_ids`
  两处**各自**调用（后者又被 `change_targets` 调用）⇒ 纯函数、同参、结果一致（不会漂），
  但 `archive_arrivals` 每次 `check` 已被求 2 次、再加即为 3 次；实现时建议在 `checkcmd` 里算一次往下传。

## 必须修改项

- **G1（判据不充分，核心）**：`design.md §2 D1` 的四条条件**挡不住**「删掉整个 active change 目录」
  —— 它满足全部四条（Confirmed D1 的构造与实测：未改 `✗ 9 项` → 带原型 `✗ 3 项`），
  直接违反 `design.md §3` 自己声明的 **N-c**。修法见 **Open Questions Q1**（三选一，用户拍板）；
  无论选哪条，都必须在 §2/§3/§7 与 spec 里**如实登记**，并补上 N-c 混合形态的端到端测试。
- **G2（§3 N-c 的理由写错 + spec/tasks 缺这条）**：N-c 的理由「第 2 条不满足」只在
  「diff 里没有任何 `A`」时成立；一旦别处有一次到达且子路径相同（本仓必然相同，见 G1），
  第 2 条**满足**。⇒ 三处同改：`design.md §3` 的 N-c 行、`specs/archive-awareness/spec.md`（补 Scenario）、
  `tasks.md §2.3`（补测试项）。
- **G3（spec 缺 R1 的 Scenario）**：`design.md §4 R1` 写「如实写进 spec 的 Scenario」，
  但 `spec.md` 里没有「部分搬移 + 某个文件没被 git 配上 ⇒ 源目录仍在 head ⇒ 照旧红」这条。
  ⇒ 补 Scenario，或把 R1 的措辞改成「不写进 spec，只登记在 design」。
- **G4（第二份 D 谓词 + 空钉子）**：`contract.changed_change_ids:381-383` 的 `D` 侧分支是**死代码**
  （变异存活，Confirmed D4），而 `tests/test_archive_arrival.py:300` 的名字/注释把它说成有效
  ⇒ 实现 `§2 D2` 第 3 条时必须**删掉/替换**那段（否则「判据只在 `d_move_halves` 一处」在文字上不成立），
  并把该测试改成**只有 `D` 记录**（零 `R`）的真用例，否则它是空钉子（对应 `tasks.md §2.2`，但 2.2 只说了幽灵 id）。
- **G5（§6 第 4 行的依据不成立 + Scenario 边界未写清）**：见 Confirmed D5 —— 纯 `D`+`A` 形态下
  `accepted_change_ids` 里没有源 id，manifest 不重绑就报「与目录不符」（探针 7：+3 条）。
  ⇒ 要么把 `§6` 第 4 行的**依据**改成「本 change 只承诺不产生幽灵 id，不承诺 manifest 保留原 id 也能过」，
  要么把它并进 G1/Q1 一起裁；`spec.md` 第 2 个 Scenario 的 Then 也要把这条边界写清。
- **G6（纯措辞）**：`specs/archive-awareness/spec.md:16` 的加粗嵌套坏掉了
  （`` **`<sub>` 与第 1 条**逐字相同**``）；不影响语义，顺手修。

---

## 处置（主 session 在 grill 之后追加，非审阅者原文）

> **G1–G6 全部已落库**（G6 是纯措辞、随本次一并修）。

- **G1（判据不充分，核心）**：接受——那条绕过是真的。**判据已重写**：
  去掉「源目录必须在 head 树里消失」，改成**身份锚** `<id> ∈ A.source_ids`
  （= git **自己**至少把 `<id>` 里的一个文件配对进了该到达目录）。
  理由与两条备选的代价写在 `design.md §2 D1` 与 §6（Q1 的三选一：取**甲**）。
  ⚠️ ~~你说的「去掉第 4 条后『`b` 仍在 head 时删它的文件』直接 EXIT=0 全绿」在**新的第 3 条**下不成立
  —— 那条攻击拿不到 `b ∈ A.source_ids`（`A` 的源是别人）。~~
  ⇒ ❌ **这句是错的，已作废**（对抗轮 A1 的 S2 实测：在仍活着的 `b` 里 `git mv` 一个小文件进到达目录
  **就能**拿到 `b ∈ A.source_ids`，`check` 会 rc=0 全绿）。第 3 条已改成 **`A.source_ids == {<id>}`**，
  见 `design.md §2 D1` 的三路对照表与 `grill-adversarial-a1.md` 的处置。
- **G2**：§3 的 N-c 理由已改（它只在**没有**到达目录时成立），并**补了 N-d 这条杀手用例**
  （连同 spec 的 Scenario「删掉整个 active change 且别处有一次正当搬移 ⇒ 仍要事件」）。
- **G3**：§4 R1 现在指向 spec 里真实存在的 Scenario（最后一条「纯 `D`+`A` 搬移不被豁免」）。
- **G4**：接受——`changed_change_ids:381-383` 是死代码。
  ⚠️ **本条已两次修订**：① 最初写「本 change 会收掉它并把空钉子测试订正」；
  ② A1 之后改成「不动它，只登记 §4 R5」（A1-2 证明去动它会开第二个洞）；
  ③ A3 指出**这句在 A1/A2 两轮都没真正改到**（A2 的处置里我把 A2-2 判成「看错了」，
  但 A2-2 指的是**这一处**、而它当时**确实原样未动**）⇒ **本次真的改了**：G4 = **不修**，
  落点是 `design.md §4 R5`（登记为超出本 issue 面的小清理）+ `tasks.md 3.3`（明写「不碰」）。
- **G5**：你指出的「纯 `D`+`A` 形态下 `source_ids` 为空 ⇒ manifest 不重绑会报『与目录不符』」
  在新判据下**不再是一个承诺**：那种形态**本来就不被豁免**，它的 manifest 也**必须**用归档目录名
  （`contract.py:314-320` 不给别名，#29 的次序已经这么写）⇒ 已写进 spec 的最后一条 Scenario 与 §3 N-i。
- **G6**：`spec.md` 的加粗嵌套已修（该段本轮重写过）。

### 关于你的 Q1（唯一一条 Open Question）

**没有停轮**，但**不等于**替你把它抹掉了：结论「取甲」写在 `design.md §6` 的 Q1 行，
**乙／丙 两条路的代价也在同一行里写清**，供用户复核（丙 会把「删掉一个 change 目录」变成合法洗白路径——
正是你 G1 实测的那个 `✗9 → ✗3`）。
