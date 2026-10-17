# Design: archive-arrival-d-side

> 状态：**停轮已解除**（用户 2026-10-17 裁定 **B**：不发豁免、只让 finding 可行动；见 §6 与
> `reviews/grill-design.md` 的 `## User Confirmation`）。

## 0. 一句话

`git` 配不上 rename 时留下的那条 `D`（旧 active 路径）**照旧红**（**本 change 不加任何豁免**）；
本 change 只让那条红**可行动**：说清「这可能是搬移的一半」、给出**一行事件**的补救与一个**可直接复制的 JSON 示例**。

## 1. 现状（逐行实测）

- **`D` 记录的字段落位**：`gitutil._parse_name_status`（`src/witnessloop/gitutil.py:210-225`）对非 `R`/`C` 记录
  走 `Change(raw, fields[i + 1])`（`:224`）——即被删路径进 **`path`**、**`old_path` 留 `None`**
  （`gitutil.py:16-22` 的 `Change`）。
- **受保护写入的判定**：`checkcmd._protected_writes`（`src/witnessloop/checkcmd.py:346`）逐条记录判
  `_archive_move_exempt(change, pol, arrivals)`（`:373`）；后者（`:324-343`）**第一句**就是
  `if not change.old_path: return False`（`:335`）⇒ **`D` 记录永远拿不到豁免**——这正是 issue #31 那条红的来源。
- **到达组带 source_ids**：`contract.archive_arrivals`（`contract.py:253-324`）的 `group` 是
  `under_path(change.path, directory)` 的记录集合（`:300-302`）。**它只看新侧** ⇒ `D` 侧天然进不来。
- **复现（issue #31 原文）**：base `8e5fc83b`、head `d94c08334` + 归档目录名重绑 manifest ⇒
  `git diff -M --name-status` 里**只有一条 `D`**（`…/guard-write-allowlist/workflow-events.jsonl`），
  `check` 报 **1 项**「受保护路径被写入，但没有结构化解释事件」。
- **本仓自己的第一次归档是纯 move**：58 条记录**全是 `R100`**（0 `A`/`D`/`M`）⇒ `check：通过 ✓`、
  **0 条 finding**（PR #38 / merge `e88c5b2`）。⇒ **纯搬移根本不需要任何事件**（用户裁定的原文也是这句）。

## 2. 决策（B）

### D1 判定语义：**零改动**

本 change **不新增任何豁免面**，也**不移动**任何判定：

- `_archive_move_exempt`（`checkcmd.py:324-343`）**不动**；
- `_protected_writes`（`:346-`）对 `policy.protected_paths` 与不变集的两档规则**不动**；
- `archive_arrivals` 的判据 1/2/3/5（`contract.py:290-313`）**不动**；
- `changed_change_ids`（`contract.py:355-417`）**不动**。

⇒ 对**任何**输入，`check` 的**退出码**与 **findings 集合（path + 消息正文的判定部分）**与改动前相同。
唯一允许变化的是：**某些 finding 的消息末尾多一段诊断 + 补救示例**（D2/D3）。

⚠️ **这一条是承重的**（用户裁定的原话：「本能力不改变任何豁免语义」）。它由 §7 的「判定不变」表钉住。

### D2 诊断面：一个纯函数，**只喂文案**

新增 `contract.move_half_candidates(changes, policy: Policy, arrivals) -> dict[str, str]`：

```python
"""诊断用（**不参与任何判定**）：`D` 记录 ↔ 同一次 diff 里「同相对子路径」的 `A` 落点。

返回 {normalize(D.path): normalize(A.path)}；同一个 D 有多条候选时取**字典序最小**的一条（确定性）。
"""
```

只收满足**全部**下列条件的记录对：

1. `change.status[:1] == "D"` 且 `change.old_path` 为空（`D` 侧的唯一形态，`gitutil.py:16-22`）；
2. `normalize(change.path)` 形如 `<changes_root>/<id>/<sub>`，`<sub>` **非空**，且**不在** `<changes_root>/archive/**` 下；
3. 同一次 diff 里存在一条 `A` 记录（`status[:1] == "A"`），其 `path` 落在**某个到达目录 `A_dir`** 之下
   （`arrivals` 的结果——判据 1/2/3/5 一条不放松），且**相对子路径逐字相同**：
   `normalize(A.path) == f"{A_dir}/{<sub>}"`。

**它不改变任何判定**：`checkcmd` 只把它返回的映射拿去**拼消息**，不参与 `if`、不影响 findings 的有无。
⇒ 这是本 change 唯一的「新增计算」，且它是**纯函数**（不读盘、不读树）。

⚠️ **诊断是启发式**（如实登记）：一条 `D` 恰好与一条无关的 `A` 同相对子路径时，文案会说「**可能**是」——
它不改判定、只多一句提示；真有人照它补事件，补的也是**那个被删路径**的解释，语义上仍然成立（那确实是一次删除，
除非它真是搬移的一半）。

### D3 文案与示例：事件类型**取自本仓 policy**，不硬编码

`_protected_writes` 生成 finding 时，若该记录在 `move_half_candidates` 里，则在**原有消息正文之后**追加：

```
（⚠️ 这可能是**一次搬移的一半**：`<D.path>` 被删，而同一次 diff 里 `<A.path>` 是它在到达目录
`<A_dir>` 下的同相对子路径新增。若确属搬移，请在**同一个 PR** 内补解释事件——写进**该 change 归档后的**
`workflow-events.jsonl`（**不要**写进别的既有 change 目录），通常**一条**；若追加让它的旧路径也掉成 `D`
再补一条（同一文件、同一 PR）：
{"schema":"witnessloop/event@v1","event_type":"<policy 的第一个允许类型>","change_id":"<归档目录名>",
 "artifact_path":"<D.path>","reason":"归档时与 change 一起搬进 archive/（git 未配成 rename）",
 "approved_by":"<你的名字或 run id>"}）
```

- **`event_type` 取自 `policy.protected_write_event_types` 的**首个非空项**，**不**硬编码 `protected_artifact_explained`。
  理由（**实确认**）：用户裁定的原话里那个类型是**接入方 asterwynd 的 policy** 里的名字
  （它的 `protected_write_event_types` 才含 `protected_artifact_explained`）；**witnessloop 自己的 policy
  只有 `["protected_path_write"]`**（`.witnessloop/policy.json` 实测），全仓 `grep protected_artifact_explained`
  **零命中**。若把接入方的类型名硬编码进示例，本仓接入方照抄会得到一条**不被 `covers` 认**的事件 ⇒
  红消不掉 ⇒ 示例就不是「可直接复制」的了。
  ⚠️ 若 `protected_write_event_types` **为空** ⇒ **不给示例**（只给文字补救）。⚠️ 这一态只能由**代码**
  构造出的 `Policy` 触发：`policy.Policy.from_doc` 对显式 `[]` 走 `or DEFAULT` **回落出厂默认**
  （B1-3 订正；不要在文档里写成「policy 写 `[]` 就不给示例」）。
  ⚠️ **示例印之前会用 `events.covers` 真验一遍**（B1-1）：policy 的允许集若本身**不可满足**
  （例如带首尾空白——`Event` 会把事件类型去空白，而 `covers` 比的是**未去空白**的允许集），
  就**不印示例**、改印一句「先修 policy」的诊断。**那是先于本 change 的 policy 写法问题**，
  本 change 不修它（修它会改变豁免语义）。
- **`artifact_path` 用真实路径**（那条 `D` 的路径）；`change_id` / `approved_by` 留 `<…>` 占位（不影响 `covers`：
  它只校验 `event_type` / `artifact_path` / `reason` / `approved_by` 非空、且 `artifact_path` **不接受通配**——见
  `events.covers` 的实现）。
- **事件写哪里（B1-2 实测订正）**：`events.load_all` 扫 `changes/*/workflow-events.jsonl` +
  `archive/*/workflow-events.jsonl`。SHALL 写进**该 change 归档后的**那份；
  **SHALL NOT** 写进**别的既有** change 目录——那是对不变集里一个 `M`，红会**转移**到那个文件（实测仍红）。
  **不要**为它新建一个「只有事件文件」的 change 目录（那会触发 change 目录契约，1 条红会变 7 条红，见 `§1.2`）。

### D4 成本语义（用户裁定的原文口径）

| 形态 | 成本 |
|---|---|
| **纯搬移**（全部 `R100`，被搬文件一个字节不改） | **零**——`check` 直接绿（本仓第一次归档实测：58×`R100`、0 findings） |
| **归档时顺手改了被搬文件**（那条记录配不上 rename ⇒ `D`+`A`） | **通常一条事件、同一个 PR**——照 finding 文案复制示例、填两处占位。⚠️ B1-2 实测：若追加本身让那个 events 文件的**旧路径**也配不上 rename（单行文件追加一行就可能），再补**一条**覆盖它——**仍在同一个文件、同一个 PR**，反复跑到绿为止 |
| 其它形态 | 与改动前**完全相同**（本 change 不碰判定） |

**SHALL NOT 因此增加 PR 数量**（用户原话）——事件放在**同一个开发 PR** 里。

### D5 落点

1. `src/witnessloop/contract.py`：`move_half_candidates(...)`（纯函数，§D2）；
2. `src/witnessloop/checkcmd.py`：`_protected_writes` 里**只拼文案**（finding 的 `path` 字段不变）；
3. `docs/gate.md §5.1`（归档豁免那节）：补一段「配不上 rename 的旧侧怎么办」；
4. `docs/gate.md §7`（能力边界）：登记「诊断是启发式、不改变判定」。

## 3. 留档：**为什么不是 A**（五轮对抗的实测史）

早先的设计是「把那条 `D` 认成搬移的另一半 ⇒ **免解释事件**」。判据演进四版，**每一版都被下一轮独立审阅造出一条绕过**：

| 版本 | 判据 | 被谁破 | 怎么破的 |
|---|---|---|---|
| 甲 | 同相对子路径的 `A` + 到达 | grill 的 **G1** | 删掉整个 active change `b`：骨架子路径与任何到达目录都重合 ⇒ 凑齐 |
| 乙 | 甲 + 「源目录已离开 head」 | A1 的 **S8** | **零蓄意**：删整个 change + 别处重建 manifest ⇒ git 自己给出跨 change 的 `R055` 配对 |
| 丙 | 甲 + 「`A.source_ids == {<id>}`」 | A2 的 **P7** / A3 的 **PFIVE** | 自造一个过判据的到达目录，把源的一个文件搬进去当**钥匙**；再把源删干净 |
| 丁 | **覆盖**（源在基准树里的每个文件都要在 `A` 下有同相对子路径落点） | A5 的 **X1** | 把源的每个相对子路径都用**全新内容**造齐 + 删源 ⇒ 覆盖成立 ⇒ `check` **通过 ✓**（**是伪造，不是搬移**） |

**A3 给出的根因**（A5 证明它对「覆盖」同样成立）：只要攻击者能控制整个 diff，任何**结构**证据都能被一起造出来。
⇒ **这条路打不完**；而唯一有充分性的「内容同一性」会把 issue #31 自己的复现形态判红（那个掉队的文件**本来就在
range 内被改写过**）⇒ 不能用。

⇒ 用户在 2026-10-17 选了 **B**：**不发豁免**，把成本压到「一行事件、同一个 PR」。
**这份留档是本 change 最有价值的资产之一**：它证明了「A 不是没做好，而是做不完」。
（五轮的原始报告：`reviews/grill-adversarial-a1.md` … `a5.md`。）

## 4. 否定面：**全部照旧**（本 change 不放开任何一条）

| # | 形态 | 改动后的结果 |
|---|---|---|
| N-a | 往**已存在**的归档目录里搬东西 | 照旧（不是到达；该红的红） |
| N-b | **单独**删一个 active change 的文件 | 照旧红 |
| N-c | 删掉**整个** active change 目录 | 照旧红（**本 change 不加豁免**⇒ 不会出现 A 选项下「删一个 change 不用解释」的伪造路径） |
| N-d / N-j / N-k / N-l / N-n | 四轮审阅造的五条**蓄意/零蓄意**绕过（G1 / S2 / S8 / P7 / PFIVE） | 照旧红——**它们本来就要事件，本 change 不给任何豁免** |
| N-o | **X1**（把源的全部相对子路径用全新内容造齐 + 删源） | 照旧红——**这正是 B 相对 A 的全部价值**：这条伪造路径**不存在** |
| N-e / N-f | 源不在 `<changes_root>/<id>/` 下 / `<sub>` 为空 | 仍是普通删除，照旧红；**诊断也不触发**（D2 收的条件） |
| N-g | 重建 `reviews/*.manifest.json`（`M`） | 与 `D` 无关；既有回归照旧 |
| N-h | `archive/<name>/` 缺必需件 / 内容来源存疑 / 符号链接 | 不是到达 ⇒ 诊断**不触发**（只提示「可能是搬移」，不会把它当搬移） |
| N-i | **纯 `D`+`A` 搬移**（零 `R`，但整份搬走了） | 照旧红（**与改动前同结论**）；**诊断会触发**并给出补救（这时补一行事件就是正确动作） |

⚠️ **唯一的行为面差异**是**文案**：某些红会多一段诊断 + 示例。**判定（红/绿、路径、条数）不变**。

## 5. 风险

| # | 风险 | 处置 |
|---|---|---|
| R1 | 文案被当成「工具认了这是搬移」 | 文案第一句就写「**可能**是」；并在 `docs/gate.md §7` 明写「诊断是启发式、**不改变判定**」 |
| R2 | 示例的事件类型与接入方 policy 不符 | 取自允许集的**首个非空项**（**不硬编码**）；印前用 `covers` 真验，验不过就不印并说清原因（D3） |
| R3 | 有人把事件写进「只有事件文件」的新目录 ⇒ 7 条红；或写进**别的既有** change 目录 ⇒ 红转移 | 文案**只**指定「该 change 归档后那份」，并引 `docs/gate.md §1.2` / `§5.1` 的实跑记录 |
| R4 | `move_half_candidates` 被误用在判定里 | 它是**纯函数**且**只**在 `_protected_writes` 的拼文案处被调用；§7 的「判定不变」表 + 变异测试钉住 |
| R5 | 诊断漏报（该提示的没提示） | 只影响可行动性、不影响判定；N-i 的正向用例钉住 issue #31 的形态**一定**触发 |

## 6. 停轮问题（**Q1 已由用户裁定 = B，无遗留**）

### Q1（**已裁定 2026-10-17：B**）修 #31 会新增一个豁免面，而它可被伪造绕过——接受吗？

- **三条路**：**A** 按「覆盖」落地 + 如实登记可被伪造绕过；**B** **不发豁免**，改成让接入方写**一行**解释事件；
  **C** 只豁免非受保护文件（**等价于不修**）。
- **用户裁定：B**。要点（原话）：**不发豁免**，由接入方在**同一个开发 PR 内**补**一行**
  `protected_artifact_explained` 事件；**不允许因此增加 PR 数量**；明确确认「**纯搬移不用写**，
  只有归档时顺手改了被搬文件才需要；**仍然一个 change 一个 PR**」。
- ⇒ 本 change 的交付：**判定零改动** + **可行动的 finding**（D2/D3/D4）。
- **成本被实测限定得很窄**：本仓第一次归档（纯 move，58×`R100`）**零 finding**；
  只有「归档时顺手改了被搬文件」那一种形态需要那一行事件。

**本 change 没有其它需要用户拍板的问题**（§7 的每条都由代码/实测/既有裁定定案）。

## 7. 测试策略（TDD）

1. **判定不变（承重）**：一张**形态 × 期望（退出码, findings 的 path 集合）**的表，覆盖：
   纯 `R100` 搬移 / issue #31 的 `D`+`A` 形态 / 纯 `D`+`A`（零 `R`）/ 单独删一个受保护文件 /
   删整个 change / 往已存在的 archive 搬 / 部分搬移 —— 断言**与改动前逐字相同**。
2. **诊断触发**：issue #31 的形态 ⇒ 消息里含
   ① `A` 的实际路径、②「同一个 PR」「一条」这些字、③ 一个 **`events.covers` 认的** JSON 示例
   （把示例解析出来、喂给 `covers`，断言为真——**示例必须是真能用的**）。
3. **诊断不触发**：单独删（没有同相对子路径的 `A`）/ 往**已存在** archive 搬（不是到达）/ 源在 change 外 / `<sub>` 为空。
4. **示例的类型取自 policy**：把 policy 的 `protected_write_event_types` 换成别的值 ⇒ 示例跟着变；
   置空 ⇒ 不给示例（只给文字补救）。
5. **纯函数面**：`move_half_candidates` 的相对子路径逐字相等、前缀边界、`./` 归一化、多候选取最小（确定性）。
6. **回归**：`tests/test_archive_awareness.py`（18 条 F + 6 条 N）+ `tests/test_archive.py` 全绿。
