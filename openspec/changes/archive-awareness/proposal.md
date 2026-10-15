# Proposal: archive-awareness（归档感知：归档 move 应被认作「该 change 存在」）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#21**。
> 实测来源：接入方 asterwynd（PR #309）的 `openspec/changes/archive/2026-10-14-guard-write-allowlist/stage-b-observations.md`；
> 本仓当前树上的**逐条复核**见 `design.md §1`（含命令与输出）。

## 背景

接入方在自己的规矩下**归档 change** 之后，本工具必红、且证据无法重建。三条症状同一个根因：

**`contract.changed_change_ids`（`src/witnessloop/contract.py:58-86`）有意把归档 move 的两端排除掉，
但排除之后没有任何东西补上「这里发生了一次归档」这个事实。**

排除本身是对的（`design.md §1.1` 逐条核过）：若不排除，`archive` 会被当成一个 change id 去要 `proposal.md`，
而搬走的那个 active 源目录会被报「目录不存在」。问题在于**排除是单向的**——工具于是失去了
「这个 change 被归档了」这个表示，而归档恰恰是接入方流程里**实现 PR 的收尾动作**。

## 三条症状（issue #21）

1. **`require_change_for` 误报**：归档后 `changed_change_ids` 恒为空 ⇒ `_require_change`
   （`src/witnessloop/checkcmd.py:188`）对「改了 `src/**` 这类路径」的 diff 误报
   「本次 diff 里没有任何 change 目录」。而「实现 PR 同时归档」是接入方的**硬规则**。
2. **`manifest build` 归档后拒绝执行**：`contract.change_dir()`（`:34-35`）只解析
   `changes_root/<id>` ⇒ 归档后报「change 目录不存在」，接入方**无法在归档之后重建证据**。
3. **归档事件扫不到**：`events.py:83` 用一级 glob `{changes_root}/*/{events_file}`
   ⇒ 归档 change 在 `archive/<name>/` 下**深一层、永不匹配**。合法受保护写入被报成「没有解释事件」。

## 实测（本仓当前树复核 · 与 issue 的出入逐条写明）

| # | 复核动作 | 结果 | 与 issue 的出入 |
|---|---|---|---|
| ① | 真仓里 `git mv openspec/changes/<id> → openspec/changes/archive/2026-10-14-<id>` + 同 PR 改 `src/app.py`，跑 `check` | `check：基线 …，8 个变更文件，**0 个 change 目录**` ⇒ finding「src/app.py … 但本次 diff 里没有任何 change 目录」、`EXIT=1` | 一致（行号也未漂：`checkcmd.py:188` 正是 `_require_change`） |
| ② | 同一个仓跑 `manifest build --change guard-write-allowlist --report reviews/building-review.md` | 「change 目录不合契约（与 check 同一套判定）：openspec/changes/guard-write-allowlist：change 目录不存在…」、`EXIT=1`。**对照**：把归档目录 `git mv` 回 active、同参数 ⇒ `EXIT=0` 并写出 manifest | 一致。⚠️ 报错里的「diff 里出现了它的文件」是**固定文案**（`contract.py:94`），不是对本次 diff 的观察——别把它当证据读 |
| ③ | 归档 change 里放一份 `workflow-events.jsonl`（点名 `openspec/specs/guard.md`），同 PR 写 `openspec/specs/guard.md` | 该写入被报「受保护路径被写入，但没有结构化解释事件」、`EXIT=1`；`Path.glob("openspec/changes/*/workflow-events.jsonl")` 实测 **hits=[]**，而 `…/*/*/…` 命中 `openspec/changes/archive/2026-10-14-guard-write-allowlist/workflow-events.jsonl` | 机制一致。⚠️ issue 的「全仓 80 份零命中」是**接入方全仓**的计数，本仓无从复核；本仓只复核了**机制**（单层 glob 对两层路径零命中） |

### 新发现（issue 未写，但决定本 change 的形态）：归档让**三条证据门禁一起静默失效**

同一个「零 manifest、零证据」的 change，只差**它在不在 active**：

| 对照 | diff | `check` 结果 |
|---|---|---|
| **C1b-A** | 新建 active change `x`（件齐、**零 manifest**、`reviews/` 里**有实体文件**）+ 改 `src/app.py` | 6 个变更文件，**4 项红**：缺 review manifest · 无 `stage=grill` · 无 `stage=grill-adversarial` · 无 `stage=building` |
| **C1b-B** | 同上，但**没有** `reviews/` 目录 | 5 个变更文件，**5 项红**（多一条「缺少必需件 reviews」）——两种造法结论相同 |
| **C3** | 同一个 change 在**同一个 PR 里被归档** + 改 `src/app.py` | 6 个变更文件，**1 项红**：**只剩** `_require_change` 那条（三份 manifest 一条都没被要） |
| **C2** | 纯归档（不改代码）、该 change 零 manifest | 5 个变更文件，**`EXIT=0`，绿** |

⚠️ **文件数必须连造法一起读**：git **不跟踪空目录**，`reviews/` 里有没有实体文件会改变变更文件数
（初稿曾把两种造法的数字混写成「5 文件 + 4 项」，只在工作树里恰好有个未跟踪的空 `reviews/` 目录时成立——
grill 实测纠正，见 `design.md §1.2`）。

⇒ 今天 `check` 的机制是：`checkcmd.py:79` 的 `for change_id in change_ids:` 循环**空转** ⇒
不止「契约/证据校验」不跑，连 `if code_hits:`（`:96`）包着的 **`building` 与 `grill-adversarial` 两条硬门**也不跑。

**这直接定死了修法的形状**：若只修 ①（让 `_require_change` 不再误报），C3 那份 PR 会从
「1 项红」变成「**0 项红**」——一个**改了 `src/**` 却零 change 证据**的 PR 直接放行，
比现状**更差**（现状至少红着）。所以 ① 的修法**不能是「豁免」**，只能是
**「把归档 move 带走的那个 change 放回本次 diff 的 change 集合」**（`design.md D2`）。

## 目标

1. **归档 move 使该 change 进入本次 diff 的 change 集合**（id = 归档目录名），
   与 active change **走同一套**契约/证据校验，只是路径落在 `archive/<name>/` 下 ⇒ 症状 ① 消失，
   且**不产生** C3 那种绕过面。
2. **`manifest build` 支持归档目标**（`--change <归档目录名>`），并让**归档前**产出的 manifest 继续有效
   （**别名 D8**：归档态 target 的 `change_id` 同时接受「归档目录名」与「源 id」）⇒ 接入方**不必**为归档去重建证据。
   ⚠️ 配套的**正确顺序**（`design.md §1.6`，本仓实测修后 `EXIT=0`）：
   `① 内容（实现 + 收尾）→ ② 在 active 态 build 证据（绑 ① 的 revision）→ ③ git mv 归档，放最后、纯改名`。
   ⚠️ **禁止**在**同一个 diff** 里既 move 又改写被 move 的文件（含「归档后在归档态重建 manifest」）：
   那会把 `R100` 降级成 `R<100` ⇒ ①不授予 ②被搬走的 active 目录**以幽灵 id 回到集合** ③事件需求翻倍
   （实测 9 → 6 → 3 项，最后 3 项**补事件消不掉**）。要在归档**之后**改写证据 ⇒ 落在**不含 move 的后继 diff**
   （`M` 不变集路径 ⇒ 每条一条解释事件，实测 3 条 ⇒ 绿）。
3. **`events` 扫描覆盖归档目录** ⇒ 归档 change 里的事件重新生效。
4. **归归档的既有行为一条不破**（`is_archive_move` 的纯度判据、`archive/**` 不进 active id、
   `archive/` 不是法外之地、归档 move 免解释事件）。

## 非目标

- **不引入 asterwynd 式的「归档点完成度门禁」**（`_check_archived_completion_gate`）——
  本仓**无 `ChangeType`、无 `primary` 分类、`specs/` 恒备**，照搬不了（`docs/gate.md §10` 已写明沿革）。
- **不把归档命名收紧成 `archive/<id>`**（对抗轮点名的第三路）：`is_archive_move` 只认「落点在 `archive/**`」，
  **不要求 `<date>-` 前缀**；授予判据可以是「等值 **或** `-<源id>` 后缀」。⇒ 本 change **不解析日期前缀**，
  也**不要求**接入方改掉他们现有 **80 份** `<date>-<id>` 目录（那会踩 OpenSpec 自己的归档约定）。
  ⚠️ 这条曾作为政策题进 `design.md §8` 的 **Q2**——**用户 2026-10-15 已裁定「不收紧」**：
  保持 `archive/<date>-<id>`，**D8 别名继续保留**（两种命名都能用），不要求接入方给 80 份既有目录改名；
  「归档命名要不要统一」**另立 change/issue**，不阻塞本 change。
- **不给「change ↔ 代码路径」建立归属关系**：本工具从来没有这套映射，本 change 也不引入
  （边界见 `design.md §2.5`）。
- 不引入签名 / 防伪造；不改 `check` 的退出码语义。

## 验收

- **症状级**（三条各自可判定，见 `design.md §5`）：
  - ① 归档 + 改代码的 PR ⇒ stderr **不含**「没有任何 change 目录」，且**含**归档 change 的 stage 证据要求（今天红、修后按证据齐备与否定）；
  - ② 归档后 `manifest build --change <归档目录名>` ⇒ `EXIT=0` 并在**归档目录内**写出 manifest；
  - ③ 归档 change 的合法事件 ⇒ 受保护写入**不再**被报「没有解释事件」。
- **否定用例（必须照样红，防绕过）**：
  - **N1** 只改 `src/`、**不建任何 change 目录** ⇒ 仍红（`tests/test_require_change.py::test_source_change_without_change_dir_is_rejected` 保持绿）；
  - **N2** 伪造成「看起来像归档」的 diff（**新建** `archive/<name>/…`、无对应 active 源）⇒ **不生效**；
  - **N3** **删除** change 目录（`shutil.rmtree`，非 rename）⇒ 仍报「change 目录不存在」；
  - **N4** 只改 `archive/<name>/` 下已存在文件（`M`）⇒ **不**使该 change 进入集合，`_require_change` 照样红。
  - **N6**（grill 挖出的第 6 面）把 active change `z` 的**单个文件** R100 改入**已存在**的归档目录 `y`
    （`y` 的名字不认得 `z`）⇒ **不授予任何资格**（否则资格会被凭空给 `y`，而 `z` 静默逃检）。
  - **N7**（对抗轮加的）**同一个 diff 里既 move 又改写被 move 的文件** ⇒ 红，且报出幽灵 active id
    （`openspec/changes/<源id>：change 目录不存在`）——**不许**因为「它看起来是一次归档」被放过。
- **uniform（Q1 裁定）**：**纯归档 PR 也会红**（与 active 同一套规则）——实测：把一份 grill 报告
  `## Confirmed Decisions` 只有 2 条的 change 纯归档（一行代码不改）⇒ 红 **1 项**（「少于硬门槛 3 条」）；
  历史 change 的补救**两跳**（先修证据 → 再归档）写进 `docs/gate.md` / `README` 的接入指引。
- **别名（D8）**：归档**前**用 `--change <源id>` 产的 manifest，在 `archive/<date>-<id>/` 下**仍通过校验**
  （实测「只归档、不重建」⇒ 修后 0 项红）；而 `--change <归档目录名>` 产的新 manifest 也通过。
- **顺序（§1.6）**：base 里已是 active 的 change，本 PR「改代码 → **在 active 态** build 证据 → 归档 move 放最后」
  ⇒ 修后 **`EXIT=0`，0 项红**（实测）。
- **回归**：`uv run pytest -q` **496 passed**（实测基线）保持全绿；清单见 `design.md §5.2`。

## 测试策略

TDD。判定面是两个纯函数（change 集合的划分、change 目录的解析）+ 三处接线，用例密集在
**「同一个动作在 active / archive 两种位置下的对称性」**与**四条否定用例**上——
本 change 的风险不是「改不动」，而是**把豁免面开大**（C3 已经证明这条路的代价）。
