# Building Review: archive-arrival-d-side

独立零记忆的**实现后**审阅（reviewer ≠ author）。本报告只做验证与取证；**没有修改任何实现文件**（唯一写入就是本文件）。

## Reviewer

- **被审 HEAD**：`ed1e41d505dab2c7a8a7a485e0041afbc8ea44c8`（分支 `archive-arrival-d-side/2026-10-17`，worktree `/home/happy/wl-wt/archive-arrival-recognition`）。
- **对照基准（改动前）**：`db24713`（`43557e8` 的 parent；`git log --oneline -2` 实测 `ed1e41d` / `43557e8`）。
- **快照方式**：`git archive HEAD | tar -x -C /tmp/br31/head`、`git archive db24713 | tar -x -C /tmp/br31/old`；全部实验在 `/tmp/br31/`，**未在真 worktree 做任何写操作**（`git status --porcelain` 在本报告落盘前为空）。
- **基线**：`PYTHONPATH=src python3 -m pytest -q` ⇒ 原始输出 `719 passed in 48.64s`（与任务书一致）。
- **本机**：`git version 2.43.0`；`/tmp/br31/harness.py` 用真实 `git` 仓 + 进程入口 `witnessloop.entry.main` 跑 `check`。
- **未验证**：
  - 接入方 asterwynd 的原始历史（本 worktree 没有该仓）；issue #31 的 `8e5fc83b..d94c08334` 只用测试脚手架复刻了同一 `D`+`A` 形态。
  - 真 CI / `gate.yml` / branch protection。
  - 不同 git 版本下的 rename 相似度阈值（临界行为只在 git 2.43.0 上跑过）。
  - `docs/gate.md §1.2` 的「只有事件文件的新目录 ⇒ 红会变多」没有重跑。

## 审阅结论

**判定面零改动成立**：7 种 diff 形态 × {HEAD 原样、`_move_half_hint` 返回空串、`move_half_candidates` 返回 `{}`、返回错路径、`hint` 返回垃圾、改动前 `db24713` 源码} 的 `(退出码, findings 的 path 多重集)` **逐格完全相同**（见下表；原始输出 `/tmp/br31/out_head.txt`、`/tmp/br31/out_old.txt`）。

**B1-1、B1-2、B1-3 已落库且实测有效**（代码 + 测试 + 四份文档 + `docs/gate.md` 同改）。落库证据 `git show --stat --oneline ed1e41d | tail -12`（原始输出）：

```
docs/gate.md                                       |   7 +-
openspec/changes/archive-arrival-d-side/design.md  |  30 ++--
.../reviews/grill-adversarial-b1.md                | 155 +++++++++++++++++++++
.../specs/archive-awareness/spec.md                |  34 +++--
openspec/changes/archive-arrival-d-side/tasks.md   |   4 +-
src/witnessloop/checkcmd.py                        |  36 ++++-
tests/test_archive_move_hint.py                    |  42 ++++++
7 files changed, 275 insertions(+), 33 deletions(-)
```
示例在正常 / 接入方 / 多类型 policy 下都能过 `events.covers`；带首尾空白的 policy 下不印示例、改印「不可满足」诊断；空允许集只在纯函数层可达且有单元用例。

**B1-4 未闭合**：`reviews/` 下 manifest 仍是旧 hash，`grill-adversarial-b1.md` 与本次 `building-review.md` 是孤儿报告，且本 change **没有 `stage=grill-adversarial` / `stage=building` 的 manifest**；自举 `check` 仍红（49 项，其中本 change 占 22 项）。任务书已说明 manifest 在本次审阅之后重建，因此这不构成实现缺陷，但**是开 PR 前必须闭环的簿记项**。

文档一致性存在 3 处事实性偏差（见 BR-2/BR-3/BR-4），均无行为后果；另有 4 项零覆盖/措辞类问题。**Verdict：有条件通过**，条件 = 重打 manifest（含补两个必需 stage）+ 处置 3 处文档偏差。

## 逐维度结论

### 1. 判定语义零改动（承重）——**实测成立**

方法：`/tmp/br31/harness.py` 对每种形态建一个真实 git 仓，跑 `check --base main --head HEAD`，从 stderr 解析 finding 的 path 多重集；再在同一形态上分别注入四个变异：

1. `checkcmd._move_half_hint` 恒返回 `""`（等价于删掉 hint 的文本贡献）；
2. `contract.move_half_candidates` 恒返回 `{}`（等价于删掉调用）；
3. `move_half_candidates` 返回**错路径**（`BOGUS/PATH`）；
4. `_move_half_hint` 返回垃圾串（`GARBAGE {not json}`）。

| 形态 | HEAD 原样 `(exit, n, findings path 集合)` | 改动前 `db24713` | 四个变异面 |
|---|---|---|---|
| 纯 `R100` 搬移 | `(0, 0, ∅)` | 同 | 全部同 |
| issue #31 的 `D`+`A` | `(1, 1, {openspec/changes/add-retry/workflow-events.jsonl})` | 同 | 全部同 |
| 纯 `D`+`A`（零 `R`，整份重写进 archive） | `(1, 13, {openspec/changes/add-retry ×3, openspec/changes/add-retry/reviews/{building,grill-adversarial,grill}.manifest.json, openspec/changes/archive/2026-10-14-add-retry, openspec/changes/archive/2026-10-14-add-retry/reviews/{building-review.md,building.manifest.json,grill-adversarial.manifest.json,grill-adversarial.md,grill-review.md,grill.manifest.json}})` | 同（逐 path 相同） | 全部同 |
| 单独删一个受保护文件 | `(1, 1, {openspec/changes/add-retry/workflow-events.jsonl})` | 同 | 全部同 |
| 删掉整个 change 目录 | `(1, 6, {openspec/changes/add-retry ×3, openspec/changes/add-retry/reviews/{building,grill-adversarial,grill}.manifest.json})` | 同 | 全部同 |
| 往**已存在**的归档目录搬 | `(1, 1, {openspec/changes/add-retry/workflow-events.jsonl})` | 同 | 全部同 |
| 部分搬移（新归档目录缺件） | `(1, 7, {openspec/changes/add-retry ×3, .../reviews/{building,grill-adversarial,grill}.manifest.json, openspec/changes/archive/2026-10-14-add-retry/workflow-events.jsonl})` | 同 | 全部同 |

原始断言行（`/tmp/br31/out_head.txt` 与 `/tmp/br31/out_old.txt` 解析）：

```
pure_r100 SAME 0 0
issue31_d_a SAME 1 1
zero_r SAME 1 13
delete_one SAME 1 1
delete_change SAME 1 6
existing_archive SAME 1 1
partial SAME 1 7
（28 个变异格全部 same_as_base=True）
```

- hint 只在应当出现的形态出现（stderr 里 `搬移的一半` 的条数）：`pure_r100 0`、`delete_one 0`、`delete_change 0`、`existing_archive 0`、`partial 0`、`issue31_d_a 1`、`zero_r 3`（3 条 `D`+`A` 的 manifest）。**没有任何形态因 hint 新增/丢失 finding。**
- 代码结构上也支持这一点：`checkcmd.py:371` 的 `move_half` 只被 `checkcmd.py:407` 的字符串拼接使用，**不进入任何 `if`**；`contract.py:327-378` 是纯函数（不读盘、不读树）。

### 2. B1-1 / B1-2 / B1-3 是否真落库且有效——**B1-1…B1-3 有效；B1-4 未闭合**

**B1-1（示例印前用 `covers` 真验）——已落库、有效。**

- 代码：`checkcmd.py:454-465` 先构造 `events_mod.Event`，再调 `events_mod.covers(probe, path, pol.protected_write_event_types)`；只有为真才拼「可直接复制的示例」，否则拼「写法不可满足」。
- 实测（`/tmp/br31/out_examples.txt`）：
  - `["  protected_path_write  "]` ⇒ 无示例，`unsat_msg=True`；
  - `["   "]` ⇒ 无示例，`unsat_msg=True`；
  - 默认 / `["protected_artifact_explained"]` / `["alpha_type","beta_type"]` / `["", "protected_path_write"]` ⇒ 示例均 `covers=true`。
- 测试：`tests/test_archive_move_hint.py:283-297`（空白 policy）。

**B1-2（补救位置只写归档后那份 + 「通常一条、必要时两条」）——已落库、有效。**

- 文案：`checkcmd.py:436-443` 明写「写进**该 change 归档后的** `workflow-events.jsonl`」「**不要**写进别的既有 change 目录」「通常**一条**就够；若追加本身让那个 events 文件的旧路径也掉成 `D`……再补一条（仍在同一个文件、同一个 PR）」。
- 文档：`design.md:99-102`、`specs/archive-awareness/spec.md:19-22`、`docs/gate.md:443-447` 同口径。
- 测试：`tests/test_archive_move_hint.py:300-308`（只指定归档后那份 + 「反复跑到」「再补一条」）。
- 实测二次补救（`/tmp/br31` 的 `mode_remedy3`）：人为让 events 文件从 `R100` 因追加变成 `D`+`A` 后，旧 events 路径重新变红；再往归档后 events 追加一条 `artifact_path` 指向旧 events 路径的事件 ⇒ 该 path 消失（`old-events-red: True → False`）。剩余的红是该场景下先于本 change 的「审阅的是旧 revision」证据漂移，与本 hint 无关。

**B1-3（空允许集只在纯函数层可达）——已落库、有效。**

- `policy.py:123-126` 对 `evidence.protected_write_event_types` 用 `or C.DEFAULT_PROTECTED_EVENT_TYPES`，显式 `[]` 回落默认（实测 `empty_list` 仍印默认类型的可用示例）。
- 文档已改成「只能由代码构造出的 `Policy` 触发」（`design.md:89-91`、`spec.md:44-46`、`tasks.md:31-33`）。
- 单元用例：`tests/test_archive_move_hint.py:311-322`（`dataclasses.replace(..., protected_write_event_types=())` ⇒ 无 `"event_type"`）。

**B1-4——未落库（见「6. 簿记」）。**

### 3. 示例的可用性——**正常/多类型可用；空白策略正确地不给示例；混合列表有一个诊断误报**

逐组 policy 实跑（`/tmp/br31/out_examples.txt`，每个 policy 一个真实仓，抽出消息里的 JSON 再喂 `events.load_events_file` + `events.covers`）：

| `protected_write_event_types` | 印出的 `event_type` | `covers` | 备注 |
|---|---|---|---|
| 默认 `["protected_path_write"]` | `protected_path_write` | **true** | `artifact_path` = 那条 `D` 的真实路径 |
| `["protected_artifact_explained"]` | `protected_artifact_explained` | **true** | 跟随 policy |
| `["alpha_type","beta_type"]` | `alpha_type` | **true** | 取首个非空 |
| `["", "protected_path_write"]` | `protected_path_write` | **true** | 跳过空串 |
| `[]`（经 `from_doc`） | `protected_path_write` | **true** | 回落默认，符合 B1-3 的订正 |
| `["  protected_path_write  "]` | 无示例 | — | 印「不可满足」 |
| `["   "]` | 无示例 | — | 印「不可满足」 |
| `["  bad  ", "good"]` | 无示例 | — | **误报**：`good` 其实可满足，消息却说「任何事件都过不了」（BR-5） |

`artifact_path` 是真实路径：`tests/test_archive_move_hint.py:147` 断言 `doc["artifact_path"] == old`；本次实测它与 finding 的 `path` 逐字相同，且 `covers` 为真。

### 4. 实现质量——**不崩、确定；发现两个边角**

`/tmp/br31/boundary.py` 对 `move_half_candidates` 直接喂畸形输入（原始输出）：

```
empty_status_D: {}
empty_path_D: {}
empty_path_A: {}
D_equals_arrival_dir: {}
D_equals_active_dir: {}
D_at_changes_root: {}
D_trailing_slash: {}
A_equals_arrival_dir: {}
A_missing: {}
R_with_old: {}
D_with_old: {}
backslash: {'openspec/changes/b/e': 'openspec/changes/archive/x/e'}
dot_prefix: {'openspec/changes/b/e': 'openspec/changes/archive/x/e'}
nested_sub: {'openspec/changes/b/reviews/m.manifest.json': 'openspec/changes/archive/x/reviews/m.manifest.json'}
multiple_A_same_sub: {'openspec/changes/b/e': 'openspec/changes/archive/a/e'}
case_sensitive: {}
empty_arrivals: {}
empty_changes_root: {}
slash_changes_root: {}
dot_changes_root: {}
archive_like_source_under_archive: {}
dup_D_same_path: {'openspec/changes/b/e': 'openspec/changes/archive/x/e'}
```

- **无异常**；空 status / 空 path / `D` 恰为到达目录或 active 目录 / 空 arrivals 都安全返回 `{}`。
- **确定性**：多候选按 `sorted()` 取字典序最小（`contract.py:375-377`；`tests/test_archive_move_hint.py:274-280`）。
- **反斜杠 / `./`**：`pathutil.normalize` 归一后正确配对（与 design 的「逐字相同」一致；大小写不同不配对）。
- 边角 1：`arrival.directory` 若带**尾斜杠**，`contract.py:350` 只 `normalize` 不去尾斜杠，随后 `path[len(directory)+1:]` 会错位一个字符 ⇒ 静默漏报（实测 `'openspec/changes/archive/x/'` 返回 `{}`）。生产路径的 `arrival.directory` 来自树遍历（无尾斜杠），**当前不可达**；属于纯函数鲁棒性缺口，无行为后果。
- 边角 2：`path` 本身含 `*`/`?` 时示例必然过不了 `covers`（`covers` 拒绝通配），消息却会说 policy 不可满足。极罕见，且是既有的「受保护路径不能含通配」边界，未计入放行条件。
- 可读性：hint 约 500+ 汉字、附一个 JSON 示例，长度偏大但信息完整（两侧路径、写作位置、换行兜底、示例）；作为 finding 消息可接受。

### 5. 文档一致性——**主干一致；3 处事实性偏差 + 2 处测试声明偏差**

逐条核对（四份 change 文档 + `docs/gate.md §5.1/§7`）：

**一致的部分**

- `docs/gate.md:435-448` 与代码一致：不发豁免、D 照旧红；诊断条件（同相对子路径的 `A` 落在本次到达目录）；补救只写归档后那份；通常一条、必要时两条；纯搬移零事件。
- `docs/gate.md:560-563`（§7）与代码一致：诊断是启发式、不改变任何判定。
- `spec.md:13-40` 的判定面、`spec.md:44-46` 的空允许集、`spec.md:48-60` 的 Scenario 与测试一一对应（见下）；`spec.md:62-88` 的「不触发 / 跟随 policy / 不可满足」四个 Scenario 也都有测试。
- `design.md:29-51`（D1 零改动）、`design.md:43-67`（D2 判据）、`design.md:69-102`（D3 示例与写入位置）、`design.md:104-112`（D4 成本）与实现/实测一致。
- `tasks.md:0.1-0.3`、1.1、2.1-2.4、3.1-3.4、4.1-4.2、4.4 的勾选有对应落地物；4.3（自举判绿）、5.1、5.2 未勾，符合当前状态。

**偏差（均无行为后果）**

- **BR-2**：`docs/gate.md:438` 写 `openspec/changes/archive/archive-arrival-d-side/`，该目录**不存在**（本 change 仍是 active，正确路径是 `openspec/changes/archive-arrival-d-side/`）。B1 报告已指出，未修。
- **BR-3**：`design.md:86-87` 仍写「全仓 `grep protected_artifact_explained` **零命中**」；实跑 `grep -rn` 当前有 11 处命中（design 4 / proposal 1 / spec 2 / grill-design 1 / checkcmd 1 / 测试 2，不计 B1 报告）。该断言落盘时即不成立。
- **BR-4**：`spec.md:18` 的 Requirement 1 要求消息给出「那条 `A` 的实际路径，**以及它所在的到达目录 `A_dir`**」；`design.md:74` 的模板也含 `<A_dir>`。实现（`checkcmd.py:436-437`）只给 `A` 的完整路径，**没有单独点名 `A_dir`**（可由路径前缀推出）。属措辞级未满足 SHALL。
- **BR-6**：`tasks.md:26-27` 说新测试含「7 形态判定不变表」——`tests/test_archive_move_hint.py:78-123` 实际只有 3 个判定断言（issue #31 红、纯 rename 绿、单独删红）；其余形态由既有 `test_archive_awareness.py` 的 N3/N6、F5/F6 等覆盖（功能无洞，但「新测试的表」不成立）。`tasks.md:34` 说纯函数测试覆盖「前缀边界 / `./` 归一化」——新测试文件里没有这两条用例（本次 `boundary.py` 实测行为正确）。
- **措辞级**：`proposal.md:49`、`proposal.md:64`、`tasks.md:3`、`tasks.md:50` 仍把成本写成无条件的「一条 / 一行」；对 issue #31 形态成立，但未反映 B1-2 的「必要时两条」。`spec.md:6-7` 同样。可与 BR-6 一并处理，无行为后果。

**「SHALL NOT 改变任何豁免语义」是否被测试真正钉住？——部分钉住，非完全。**

- 被钉住的方向：`tests/test_archive_move_hint.py:78-87` 断言 issue #31 形态仍 EXIT_FAIL 且只有 1 条、path 是那条 `D`；`:89-104` 断言纯 `R100` 仍 EXIT_PASS、0 finding；`:106-124` 断言单独删仍红。既有 F/N 组覆盖其余形态。若有人把 hint 用于 `if`（跳过 finding），这些测试会红。
- 未钉住的方向：没有**变异型**回归测试（例如 monkeypatch `_move_half_hint` / `move_half_candidates` 后断言 `(exit, path 集合)` 不变），所以「对**任何**输入逐字相同」目前只由本次人工 harness 验证，未升级为机械钉子（B1 的 Q-B1-c 仍开放）。本次实测已覆盖 7 形态 × 5 面，当前无缺陷；属零覆盖项。

**spec 每条 Requirement/Scenario 的钉子对照**

| Spec 条目 | 实现 | 钉子 |
|---|---|---|
| Req 1 判定依据（A 路径 + A_dir） | 部分（A 路径有，A_dir 未单独点名，BR-4） | `test_the_finding_names_the_counterpart_and_the_one_line_remedy` |
| Req 2 同一 PR、只写归档后、通常一条/必要时两条 | 有 | `test_the_remedy_names_only_the_archived_changes_events_file`、`test_appending_...` |
| Req 3 示例取自 policy、真实 artifact_path、印前 covers 真验 | 有 | `test_the_embedded_json_example_is_actually_usable`、`test_the_example_type_comes_from_the_policy`、`test_a_blank_laden_policy_...` |
| Req 判定面（仍红、path 不变、D 不获豁免） | 有 | `test_the_move_shaped_D_still_reddens_exactly_once` + 既有 F/N |
| Scenario 补事件后绿 | 有 | `test_appending_the_example_in_the_same_diff_turns_it_green` |
| Scenario 纯搬移无诊断、零事件 | 有 | `test_a_pure_rename_archive_is_still_green` |
| Scenario 单独删不触发 | 有 | `test_a_plain_deletion_is_still_red` |
| Scenario 往已存在 archive 搬不触发 | 有 | `test_a_move_into_an_existing_archive_dir_gets_no_move_hint` |
| Scenario 类型跟随 policy | 有 | `test_the_example_type_comes_from_the_policy` |
| Scenario 允许集不可满足 | 有 | `test_a_blank_laden_policy_prints_no_example_but_says_why` |
| 空允许集不印示例（正文说明） | 有 | `test_empty_types_print_no_example_at_the_unit_level` |

### 6. 簿记——**B1-4 未闭合；重建时需要处理的清单**

实测（`sha256_tree` 逐份复算 + 自举 `check --base main --head HEAD`）：

| 文件 | `report_hash` | `tasks_hash` | `spec_hash` |
|---|---|---|---|
| `reviews/grill.manifest.json` | **不符**（记录 `ad9499e8…`，实际 `58be09ee…`） | **不符** | **不符** |
| `reviews/grill-adversarial-a1…a5.manifest.json` | 符（5/5） | **不符**（记录 `efe0c193…`，实际 `deda1728…`） | **不符**（记录 `855a7365…`，实际 `6328212a…`） |

- 孤儿报告：`reviews/grill-adversarial-b1.md`（无 manifest）；本报告 `reviews/building-review.md` 落盘后也将是孤儿，需在重建时各配一份。
- **缺 stage**：自举 `check` 报 `无 stage=grill-adversarial 的 manifest（现有 stage：grill, grill-adversarial-a1…a5）` 与 `无 stage=building 的 manifest`。重建时不能只重绑 hash，还必须让**恰好** `stage=grill-adversarial` 与 `stage=building` 各有一份 manifest（现有 a1…a5 的 suffix 命名不满足门禁的精确匹配，`evidence.py:361`）。
- 自举 `check` 原始输出共 **49 项**；其中 **1–22 项属于本 change**（a1–a5 的 tasks/spec/hash + 旧 revision 漂移、grill 的三项漂移、b1 孤儿、缺两个 stage）。另外 **23–49 项属于 4 个既有 change**（`archive-arrival-recognition` 3、`archive-awareness` 3、`confirm-gate-fail-closed` 3、`gate-ref-pins-package` 18），成因为本分支改了 `docs/gate.md` 等非证据文件、使它们的旧 manifest 出现「审阅的是旧 revision」——这是仓里既有的跨 change 簿记约定（对照 `5146fec` 的「重打 18 份 manifest」），重建时应一并处理。
- `tasks.md:51` 4.3「本仓自举 check 判绿」未勾，与上述一致；`tasks.md:57-59` 5.2 未勾。按任务书，manifest 由后续步骤重建，本报告不代建。

## 问题清单

| 编号 | 严重度 | 结论 | 证据 |
|---|---|---|---|
| **BR-1** | 阻断合并（簿记，非实现） | B1-4 未闭合：manifest hash 漂移、b1/本报告孤儿、缺 `stage=grill-adversarial` 与 `stage=building`；自举 check 红（本 change 22 项）。开 PR 前必须重打。 | 上文「6. 簿记」的 hash 表；`python3 -m witnessloop check --root . --base main --head HEAD` 的第 1–22 项 |
| **BR-2** | 低（文档） | `docs/gate.md:438` 指向不存在的 `openspec/changes/archive/archive-arrival-d-side/`。 | 该文件该行；`ls` 无此目录 |
| **BR-3** | 低（文档） | `design.md:86-87` 的「全仓 grep 零命中」不成立（实测 11 处）。 | `grep -rn protected_artifact_explained …` |
| **BR-4** | 低（spec 保真） | Requirement 1 要求消息给出 `A_dir`，实现只给 `A` 的完整路径；`design.md:74` 模板同带 `<A_dir>`。 | `spec.md:18`、`design.md:74`、`checkcmd.py:436-437` |
| **BR-5** | 低（诊断措辞，边缘） | 允许集为 `["  bad  ", "good"]` 时印「任何事件都过不了」，但 `good` 可满足；同时错过一个可用示例。 | `/tmp/br31/out_examples.txt` 的 `mixed_blank_first`；`checkcmd.py:444-465` |
| **BR-6** | 零覆盖/声明偏差 | `tasks.md:26-27/34` 对测试覆盖面的描述大于实际（7 形态表只在新文件里覆盖 3 个；前缀边界/`./` 无测试）；`proposal/tasks` 仍写无条件的「一条」。 | `tests/test_archive_move_hint.py:78-124`；本次 `boundary.py` 输出 |
| **BR-7** | 边缘（可行动性范围） | 对 **policy 声明保护**（非不变集）的 `D`+`A`，A 侧 finding 无 hint；照旧路径示例补一条后 A 侧仍红，「通常一条」在该类不成立。issue #31 的不变集形态不受影响，判定未变。 | `mode_remedy3` 的 STEP1/STEP2 输出；`checkcmd.py:393-394`（A 仅对 invariant 豁免） |
| **BR-8** | 零覆盖（无行为后果） | 「SHALL NOT 改变任何豁免语义」没有变异型回归测试钉「任何输入」；本次 7×5 harness 已人工验证成立。 | `tests/test_archive_move_hint.py` 只有 3 个判定断言；B1 的 Q-B1-c 仍开放 |

## Verdict

**有条件通过** —— 实现与判定面没有发现行为缺陷（7 形态 × 6 运行面逐格相同；B1-1…B1-3 已落库且有效）；放行条件 = **BR-1 的 manifest 重建必须在开 PR/合并前闭环**（重绑 grill 与 a1–a5、为 b1 与本报告补 manifest、补 `stage=grill-adversarial` 与 `stage=building`，并处理本分支给其他 4 个 change 带来的 27 项旧 revision 漂移），以及处置 **BR-2/BR-3/BR-4** 的文档/ spec 偏差（或由 owner 明确接受为措辞）。**BR-5、BR-6、BR-7、BR-8 不构成放行条件**：它们或只影响极端 policy / 自定义保护路径下的提示完整性，或只是测试声明与零覆盖，均不改变退出码、findings 的 path 集合或任何豁免语义。
