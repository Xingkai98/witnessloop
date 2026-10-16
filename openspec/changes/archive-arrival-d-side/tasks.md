# Tasks: archive-arrival-d-side

> 关联 issue：**#31**。本 change 的形态：**小、但判据要按承重写**——多一条或少一条都会
> 在「防绕过」与「防误伤」之间倒向一边（`design.md §2 D1` 的第 4 条就是那个支点）。

## 0. 前置门

- [x] 0.1 独立零记忆 grill → `reviews/grill-design.md`（`## Confirmed Decisions` ≥3 条、每条带 `来源:`；
      `## Open Questions`；`## User Confirmation`）。**判定：6 条必须修改项 G1–G6**
      （G1 = 判据可被「删掉整个 active change 目录 + 别处一次正当搬移」同时满足 ⇒ 那条绕过是真的）。
      ⇒ 判据已按 G1 **重写**：身份锚改成 `<id> ∈ A.source_ids`（git 自己配上的那个），
      并**去掉**了「源目录必须在 head 消失」那条（它会让 `D` 侧比 `R`/`C` 侧更严）。
- [x] 0.2 **停轮门**：`design.md §6` 论证「无需要用户拍板的问题」。grill 提出了 **Q1**（配对要不要加身份锚，
      三选一）——已由**本次改判据**自行裁定为**甲**（加锚），**另一条路的代价也写进了 §6 左列供用户复核**。
      除 Q1 外无其它停轮项。
- [ ] 0.3 对抗轮（独立零记忆，**无轮数上限、收敛才停**）→ `reviews/grill-adversarial*.md`
      （多轮用**不同 stage 名**，见 `docs/gate.md §3` 的约定）。

## 1. 规格

- [ ] 1.1 `specs/archive-awareness/spec.md`：把 D1 的判据写成 Requirement + Scenario（含 N-a…N-h 的否定面）。

## 2. 测试（先行）

- [ ] 2.1 端到端复刻 issue #31：active change 在 base、head 里整体进 archive，其中**一个受保护文件走 `D`+`A`**
      ⇒ 改前红 1 项；改后 `check` 通过 ✓。
- [ ] 2.2 **纯 `D`+`A` 形态（零 rename）**：`A.source_ids` 为空 ⇒ **源侧受保护文件照旧要事件**
      （N-i 的钉子；**与改动前同结论**，不是新红）。
- [ ] 2.3 否定面逐条：往**已存在**的归档目录搬 / **单独**删 active change 的文件 / 删整个 active change 目录 /
      **删掉整个 `b` 而别处有一次正当搬移的到达目录**（**G1 的杀手用例：改前会漏**）/
      **在仍活着的 `b` 里 `git mv` 一个小文件污染 `source_ids` 后再删它的受保护文件**（**A1 的 S2：改前会漏**）/
      **零蓄意跨配对**（A1 的 S8）/ 源在 active change 外 / `<sub>` 为空 / `archive/<name>` 不是到达。
- [ ] 2.4 纯函数面：`d_move_halves` 的配对算法（相对子路径逐字相等、前缀边界、大小写与 `./` 归一化）。

## 3. 实现

- [ ] 3.1 `src/witnessloop/contract.py`：新增 `d_move_halves(...)`（D1 判据的**唯一**实现）。
- [ ] 3.2 `src/witnessloop/checkcmd.py`：`_archive_move_exempt` 认 `D` 侧（查集合）。
- [ ] 3.3 **`changed_change_ids` 不动**（A1-2 订正）：早先那半已删除——在「恰为一个源」的锚下它恒为空 no-op，
      而在最坏情况下它是**第二个洞**（把还活着的 change 从 active id 里排除 ⇒ 逃掉契约校验，A1 的 S2 实测）。
      `:381-383` 的死分支也**不**顺手动（超出本 issue 的面）⇒ 登记为 §4 R5。
- [ ] 3.4 文档：`docs/gate.md §5.1`（归档豁免那节）与 `§7 能力边界`（登记「`D` 侧配对是推断的」这条边界）。

## 4. 验证

- [ ] 4.1 `uv run pytest -q` 全绿（含既有 18 条 F 组 / 6 条 N 组回归）。
- [ ] 4.2 复刻 issue #31 的命令 ⇒ `check：通过 ✓`。
- [ ] 4.3 本仓自举 `check` 判绿。

## 5. 收尾

- [ ] 5.1 实现后独立审阅闭环（reviewer ≠ author，收敛才停）→ `reviews/building-review.md`。
- [ ] 5.2 三份（+多轮）stage manifest；回链 issue #31。
- [ ] 5.3 **（本 change 之后）**用本修复做 witnessloop **第一次真实归档**（把已完结的 change 搬进 `archive/`）
      —— 那是本修复的**真实验证**，但属**另一个 PR**（归档是纯 rename 的簿记动作）。
