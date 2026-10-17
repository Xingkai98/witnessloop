# grill-adversarial-b1

独立零记忆对抗确认（裁定 B 之后的第 1 轮）。本文把 change 内的「实测 / 已落库 / 已收敛」一律当待验证断言；凡可复算的均在本轮复算。

## Reviewer

**基准 revision / blob**

- 被审 HEAD：`43557e879bb9c5d3219aff4c470b557e571efd08`（`archive-arrival-d-side/2026-10-17`）。
- 对比基准（改动前）：`db247139d4588d80ca1a71ca668273830f3ce0f6`（`43557e8` 的 parent；`src/` 下只有 contract/checkcmd 两处差异，`git diff --stat db24713 HEAD -- src` 实测）。
- blobs：`src/witnessloop/contract.py` = `3e1f4fb9449a678b21fc46ef7495a86c1b9262fd`；`src/witnessloop/checkcmd.py` = `74690dc68c59e96db7b6684f0c32952591b90fa1`；`tests/test_archive_move_hint.py` = `c49dd4ab1f20fc0cdee7c6769c276a458188575b`；`specs/archive-awareness/spec.md` = `c013ddf85cf4e60038a8d29513e6bf8a6ed597ba`。
- 快照用 `git archive HEAD | tar -x -C /tmp/ab1/head` 与 `git archive db24713 | tar -x -C /tmp/ab1/old`；全部实验在 `/tmp/ab1/`，**未在真 worktree 做任何写操作**（除本报告）。

**跑过的东西**

1. 基线：`PYTHONPATH=src python3 -m pytest -q` ⇒ 原始输出 `716 passed in 80.76s (0:01:20)`。
2. 自建 `/tmp/ab1/harness.py`：7 种 diff 形态 × 6 个运行面（HEAD 原样 / `_move_half_hint` 返回空串 / `move_half_candidates` 返回 `{}` / 返回错路径 / hint 返回垃圾 / **改动前源码 db24713 子进程**），逐形态比较 `(退出码, findings 的 path 多重集)`。
3. `/tmp/ab1/harness.py boundary`：对 `move_half_candidates` 喂畸形输入（空 status、空 path、D=到达目录、D=change 目录、反斜杠、`./`、大小写、嵌套子路径、空 arrivals、空 changes_root 等）。
4. 示例可用性：7 组 `protected_write_event_types` policy，抽出消息里的 JSON 示例，喂 `events.load_events_file` + `events.covers`。
5. 补救位置：`/tmp/ab1/remedy.py`（写进「任一既有 change 目录」/ 写进归档后那份）与 `/tmp/ab1/size_sweep.py`（events 文件 1/2/5/20 行）；`/tmp/ab1/false_trigger.py`（无关删除 + 无关到达的误触发）。
6. 裁定落库：`evidence.grill_evidence_findings`、`grill_evidence_findings_in_change`；另跑 `contract.validate_review_manifests` 复核 manifest hash。
7. 归档实测：`git diff-tree -r -M --name-status 3d600aa | awk '{print $1}' | sort | uniq -c` ⇒ `58 R100`（另有 1 行 commit 自身），与文档「本仓第一次归档 58×R100」一致。

**没复算的**：真 CI / `gate.yml` / branch protection；接入方 asterwynd 的原始历史（本 worktree 无该仓）；`docs/gate.md §1.2` 的「新建只有事件文件的目录 ⇒ 7 条红」；不同 git 版本下的 rename 相似度阈值（本机 `git version 2.43.0`）。

## 对抗结论

### 1. 判定语义零改动（承重）——**实测成立**

`43557e8` 对 `src/` 只动两处（`git diff --numstat db24713 HEAD -- src` ⇒ `checkcmd.py +41/-1`、`contract.py +54/-0`）：`_move_half_hint` 只在 finding 消息里做字符串拼接（`checkcmd.py:407`），`move_half_candidates` 的结果不进入任何 `if`（`checkcmd.py:371` 之后）。下表每一格都是实跑（完整输出在 `/tmp/ab1/harness.py forms`；`paths` 为 finding path 多重集）：

| 形态 | HEAD 原样 `(exit, n, paths)` | OLD `db24713` | hint 返回空串 | candidates 返回 `{}` | candidates 返回错路径 | hint 返回垃圾 |
|---|---|---|---|---|---|---|
| 纯 `R100` 搬移 | `(0, 0, ())` | 同 | 同 | 同 | 同 | 同 |
| issue #31 `D`+`A` | `(1, 1, ('openspec/changes/add-retry/workflow-events.jsonl',))` | 同 | 同 | 同 | 同 | 同 |
| 零 `R` 整份重写进 archive | `(1, 21, (...21 条...))` | 同（逐 path 相同） | 同 | 同 | 同 | 同 |
| 单独删受保护文件 | `(1, 1, ('openspec/changes/add-retry/workflow-events.jsonl',))` | 同 | 同 | 同 | 同 | 同 |
| 删整个 change | `(1, 6, (...6 条...))` | 同 | 同 | 同 | 同 | 同 |
| 往**已存在** archive 搬 | `(1, 1, ('openspec/changes/add-retry/workflow-events.jsonl',))` | 同 | 同 | 同 | 同 | 同 |
| 部分搬移（新目录缺件） | `(1, 1, ('openspec/changes/archive/2026-10-14-add-retry/workflow-events.jsonl',))` | 同 | 同 | 同 | 同 | 同 |

原始断言行（7 形态全部）：`semantic_equal_to_OLD=True`、四个变异面的 `same_semantics=True`。零 `R` 形态的 21 条由 3×`openspec/changes/add-retry`、3 条 active manifest、15 条 archive manifest 组成；HEAD 与 OLD 的 path 多重集完全相等。**结论：findings 的有无 / path / 条数与退出码不变；唯一变化是消息后缀**（hint 数：issue31 原样 1、零 `R` 原样 3；关掉 hint 后 0）。

畸形输入（`harness.py boundary` 原始输出摘要）：`empty_status {}`、`empty_path_D {}`、`empty_path_A {}`、`D_equals_arrival_dir {}`、`D_equals_active_dir {}`、`trailing_slash_D {}`、`R_with_old {}`、`D_with_old {}`、`empty_arrivals {}`、`changes_root_empty {}`；`backslash`、`dot_prefix`、`nested_sub`、`unicode` 正确配对；**无异常**。反斜杠/`./` 被 `pathutil.normalize` 归一后按预期命中，大小写不同则按「逐字相同」不命中。

误触发验证（`false_trigger.py`）：构造「删除 victim 的 events 文件 + 一个无关 change 被归档且 events 被重写」⇒ `exit 1`、findings 为 `['openspec/changes/other/workflow-events.jsonl', 'openspec/changes/victim/workflow-events.jsonl']`、`hint triggered on unrelated deletion: True`。**误触发确实存在，但判定集合未变**；文案写的是「可能」，与 design/spec 的如实登记一致，按本轮判据不算缺陷。

### 2. 示例在「带空白的 policy」下**不能**通过 `covers`（B1-1）

`_move_half_hint` 直接取 policy 里的原字符串（`checkcmd.py:433-437`），只过滤空串、**不 strip**；而 `Event.__post_init__` 会 strip `event_type`，`events.covers` 又用 strip 后的值精确匹配 policy 原元组（`events.py:113`）。实测（`/tmp/ab1/harness.py examples` 原始输出）：

| policy `protected_write_event_types` | 示例里的 `event_type` | `covers` |
|---|---|---|
| `["protected_path_write"]`（默认） | `protected_path_write` | **True** |
| `["protected_artifact_explained"]` | `protected_artifact_explained` | **True** |
| `["alpha_type","beta_type"]` | `alpha_type` | **True** |
| `[]` | `protected_path_write`（loader 回落默认） | **True**（但见 B1-3） |
| `["  protected_path_write  "]` | `'  protected_path_write  '` | **False** |
| `["   "]`（全空白） | `'   '` | **False** |
| `["", "protected_path_write"]` | `protected_path_write`（取首个非空） | True |

复现命令与输出（聚焦）：

```
printed event_type repr = '  protected_path_write  '
policy allowed tuple    = ('  protected_path_write  ',)
covers                  = False
```

这直接违反 `specs/archive-awareness/spec.md:20-22`（示例 SHALL 取自 policy 允许集）与 `:49`（示例喂给 `events.covers` **SHALL 为真**），也违反 `design.md:88-89` 的「可直接复制」。根因（空白 policy 下任何事件都过不了 `covers`）先于本 change 存在——`Event` strip、policy 不 strip——但**本轮新增的「印一个可复制示例」的承诺**在这个 policy 类上是假的，且现有 14 条测试只覆盖了默认/接入方两种干净 policy。**这是本 change 的新可证伪项。**

### 3. 「补一条事件」的两个位置承诺会**继续红**（B1-2）

hint 文案（`checkcmd.py:427-431`）、`design.md:93-96`、`docs/gate.md:441-442` 都写了「写进归档后那份，**或任一既有 change 目录**的该文件；补**一条**即可」。实测两种反例：

**(a) 写进「任一既有 change 目录」⇒ 红转移到该 events 文件**

```
before: 1 ['openspec/changes/add-retry/workflow-events.jsonl']
after appending to existing change's events file: 1 ['openspec/changes/other-change/workflow-events.jsonl']
  1. openspec/changes/other-change/workflow-events.jsonl：受保护路径被写入，但没有结构化解释事件（...）
```

原因：既有 `workflow-events.jsonl` 是**不变集**受保护路径，本次是 `M`（不是 `A`），改它本身就需要解释事件；一条 `artifact_path` 指向原 `D` 的事件盖不住它。原文承诺的「一条」「不新增目录」在这个位置不成立。

**(b) 写进归档后那份，但那份是 `R100` 搬过来的 ⇒ 可能变成 `D`+`A`**

构造：change 的 events 文件原样 `git mv`（`R100`），只重写一个 `reviews/*.manifest.json`（`D`+`A`，触发 hint）；然后照文案往归档后 events 追加示例（`/tmp/ab1/size_sweep.py`）：

| events 文件行数 | 追加后 git 记录 | 追加后 findings |
|---|---|---|
| 1 | `D openspec/changes/add-retry/workflow-events.jsonl` + `A .../archive/.../workflow-events.jsonl` | **仍有 1 条**（path = `openspec/changes/add-retry/workflow-events.jsonl`） |
| 2 | `R050 ...` | `[]`（绿） |
| 5 | `R071 ...` | `[]`（绿） |
| 20 | `R091 ...` | `[]`（绿） |

即：只有追加后仍能配成 `R<100`（或目标文件本来就是 `A`）时，「一条」才成立。单行 events 文件（很常见：一个 change 只写一条事件）会被 git 拆成 `D`+`A`，红色只是换了 path。`design.md:94-96` 写的「它随 `R100` 被搬、或 `<100` 仍走搬移豁免」没有覆盖「追加动作本身把 `R100` 推成 `D`+`A`」这一分支。issue #31 的测试形态（归档后 events 是 `A`）恰好落在安全侧，所以 14 条测试没抓到。**这是本 change 的新可证伪项。**

### 4. 「policy 置空 ⇒ 不给示例」在真实 policy 上不可达（B1-3，文档/测试）

`Policy.from_doc` 对 `protected_write_event_types` 用 `or C.DEFAULT_PROTECTED_EVENT_TYPES`（`policy.py:123-126`）：显式 `[]` 会**回落默认**，不是「关掉」。实测：

```
policy types after []   = ('protected_path_write',)
example present         = True
```

⇒ `spec.md:75` 的「置空时 SHALL 不给示例」与 `design.md:88-89/185` 的「policy 显式关掉」在这个 worktree 的真实加载路径上不可触发；只有手工构造 `Policy` 或 `[""]` 才能走到 `checkcmd.py:433` 的 `if types` 分支。另：`design.md:82/155` 说取 `[0]`，实现取的是**首个非空**（`checkcmd.py:433-437`）；`["", "good"]` 时实现给 `good`（更合理），但与文档字面不一致。`tasks.md:31` 把「置空 ⇒ 不给示例」勾成 `[x]`，`tests/test_archive_move_hint.py` 里没有这条测试（全文件只测了换成接入方类型）。

### 5. 测试/取证与文档的其它偏差（低危，均不影响判定）

- `tasks.md:26-27` 声称新测试里有覆盖 7 形态的「判定不变表」；`tests/test_archive_move_hint.py:78-123` 实际只有 3 个判定断言（issue31 仍红、纯 rename 绿、单独删红），其余形态由**改动前就有**的 `test_archive_awareness.py` 的 N3/N6/F5/F6 覆盖——功能上没漏洞，但「新测试的表」这个说法不成立。
- `tasks.md:32` 声称纯函数测试覆盖「前缀边界 / `./` 归一化」；新测试文件里没有这两条（本轮 `boundary` 实测行为正确，但无测试钉住）。
- `design.md:85` 说「全仓 `grep protected_artifact_explained` 零命中」，本轮 `grep -rn` 在 43557e8 上实测 **11 处**命中（design 4 / proposal 1 / spec 2 / grill-design 1 / checkcmd 1 / 新测试 2；不计本 B1 报告），该断言写进文件的那一刻就不成立。
- `docs/gate.md:438` 指向 `openspec/changes/archive/archive-arrival-d-side/`；本分支（以及 main 的已归档集合）没有这个目录——该 change 仍是 active，正确路径是 `openspec/changes/archive-arrival-d-side/`。
- `design.md:74-79` 说文案会给出「它所在的到达目录 `A_dir`」；实际消息只给出 `A` 的完整路径（`checkcmd.py:426`），`A_dir` 只作为路径前缀隐含存在。按「措辞类不算证伪」登记，不展开。

### 6. 裁定落库与证据（按 prompt 第 5 点）

- `reviews/grill-design.md:129-134` 的 `## User Confirmation` 是**实质的 B**（不是占位）：`选 B —— 不发豁免`、`同一个开发 PR 内补一行`、`不允许因此增加 PR 数量`、`纯搬移不用写…仍然一个 change 一个 PR`，`确认时间: 2026-10-17`；与 `design.md:162-173`（§6）逐点一致。
- `evidence.grill_evidence_findings(text, report_path='reviews/grill-design.md')` ⇒ `[]`；`grill_evidence_findings_in_change(...)` ⇒ `[]`。**按 prompt 指定的函数，裁定落库为 0 findings。**
- 但是：`43557e8` 改了 `grill-design.md`（+5 行 User Confirmation）却**没有重建** `reviews/grill.manifest.json`（commit stat 不含该文件）。实测 `sha256_tree(report)` = `58be09ee...`，manifest 的 `report_hash` = `ad9499e8...`，**不匹配**；`contract.validate_review_manifests` 对该 change 报 14 条（A1–A5 的 `tasks_hash`/`spec_hash` 漂移、`grill.manifest.json` 的 report/tasks/spec 漂移、以及本轮 `grill-adversarial-b1.md` 尚未有 manifest 的孤儿报告）。`grill-design.md:132` 自己就写了「本节落盘后 report_hash 已变化 ⇒ grill manifest 必须重建」。这属于 `tasks.md 0.4/5.2` 明确登记的待办，但**当前 commit 的裁定落库在 hash 绑定层面尚未闭合**。

## 未验证项

- 真 CI / `gate.yml` / 远端 branch protection 的实际行为。
- issue #31 的原始 asterwynd 仓库与 `8e5fc83b..d94c08334` 原始历史（本 worktree 没有该仓；本轮用测试脚手架复刻了同一 `D`+`A` 形态）。
- `docs/gate.md §1.2` 的「新建只有事件文件的 change 目录 ⇒ 1 条红变 7 条红」未复算。
- 「本仓第一次归档 58×R100、0 findings」的 **check 输出**：本分支不包含 `openspec/changes/archive/`（main 的 `e88c5b2` 尚未合入本分支），只复算了 `git diff-tree` 的 58×R100；0 findings 由文档/既有测试转述，未在本 worktree 跑。
- 不同 git 版本（rename 相似度实现可能不同）下 1 行 events 文件的 `D`+`A` 临界行为；本机为 git 2.43.0。
- 全量自举 `check`（当前必然因上述 manifest 漂移 + 未完成的 B1 manifest 而红；本轮改为直接调用 `validate_review_manifests` 复核）。

## 必须修改项

- **B1-1（行为，中）**：`_move_half_hint` 在 policy 的 `protected_write_event_types` 带首尾空白（或全空白）时，会印出 `covers` 不认的「可直接复制的示例」，违反 spec `:49`。修法二选一：① 在 `Policy.from_doc` 里 strip（并保证 `covers` 用同一口径——这是先于本 change 的空白 policy 问题的正解）；② 至少在 `_move_half_hint` 里对候选示例做一次真实的 `events.covers` 校验，不通过就不印示例（但「一行事件即可」的文字在空白 policy 下仍不真，需一并如实说明）。
- **B1-2（行为/文档，中）**：删掉或改写「或任一既有 change 目录的该文件」这一补救位置（实测会把红转移到该 events 文件，`check` 仍红）；并修正「补一条即可」的无条件表述——当目标 `workflow-events.jsonl` 是本次 diff 里的 `R100` 搬移、且追加后配不成 `R<100`（实测 1 行 events 会变成 `D`+`A`）时，需要补**第二条**（覆盖该 events 文件自身）才能绿。`design.md:93-96`、`docs/gate.md:441-442`、finding 文案（`checkcmd.py:427-431`）三处同改。
- **B1-3（文档/测试，低）**：`spec.md:75`、`design.md:88-89/185`、`tasks.md:31` 的「置空 ⇒ 不给示例」与 `policy.py:123-126` 的 `or DEFAULT` 冲突；要么把 spec 改成「允许集缺省/为空 ⇒ loader 回落默认」，要么改为在 loader 层真正支持空集，并补一条对应测试。同时把 `design.md:82` 的 `[0]` 改成「首个非空」或改实现。
- **B1-4（证据/簿记，低，PR 前）**：重建 `reviews/grill.manifest.json`（report_hash 已是旧值）与 A1–A5 的 `tasks_hash`/`spec_hash`；本轮 `grill-adversarial-b1.md` 需要配 `grill-adversarial` stage manifest，否则自举 `check` 会报孤儿报告/hash 漂移。此项与 `tasks.md 0.4/5.2` 的未完成项重叠，但当前 commit 已经把 grill 报告改脏，不能留到忘记。

## Open Questions

- **Q-B1-a**：示例可用性应该由「policy 加载时 normalize」兜底，还是由「印示例前用 `covers` 自检」兜底？前者会改变既有空白 policy 的全局语义（先于本 change 的坑），后者只保证本 change 不再印废示例；选哪个需要 owner 拍板。
- **Q-B1-b**：在「目标 events 文件本身也是本次受保护写入」的形态下，用户裁定 B 的「一行事件」成本是否接受变成「两条」？若不接受，工具需要选一个本次为 `A` 的落点（或新建一个 events 文件）并在文案里说清，而不是无条件说「写进归档后那份」。
- **Q-B1-c**：是否补一条**变异型**回归测试（例如 monkeypatch `_move_half_hint` 返回空串/垃圾，断言 exit 与 finding path 集合不变），把「判定零改动」从「本轮人工验证」升级为机械钉子？本轮已人工验证成立，但现有测试没有这条。
- **Q-B1-d**：`design.md:85` 的「全仓 grep 零命中」与 `docs/gate.md:438` 的归档路径是笔误还是需要在归档后成立？按「措辞类不算证伪」本轮未计入必须修改项。

## 收敛结论

**不收敛。**

- **判据②（判定语义零改动）核实通过**：7 种形态 × {HEAD, hint 关闭, candidates 返回空/错路径, hint 返回垃圾, 改动前 db24713} 的 `(退出码, findings path 多重集)` 全部相同；畸形输入无崩溃；误触发只改文案、不改判定。
- **判据①（本轮没有新的可证伪项）未通过**：B1-1（带空白的 policy 下示例 `covers=False`，违反 spec 的 SHALL）与 B1-2（文档承诺的两个补救位置/「一条」在可复算形态下仍留红）都是本轮新造出的、可复现的行为性反例，不属于措辞/计数/格式类。
- B1-3/B1-4 是文档、测试声明与证据 hash 的问题，单独不构成判定面缺陷，但 B1-4 在开 PR 前必须闭环。

修掉 B1-1/B1-2（并处理 B1-3/B1-4）后，再跑一轮短确认即可收敛。
