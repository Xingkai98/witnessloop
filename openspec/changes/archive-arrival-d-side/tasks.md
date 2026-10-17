# Tasks: archive-arrival-d-side

> 关联 issue：**#31**。用户 2026-10-17 裁定 **B**：**不发豁免**，把成本压到「**一行事件、同一个 PR**」，
> 交付物是**让那条 finding 可行动**（`design.md §2`）。
> ⚠️ 承重约束：**本能力不改变任何豁免语义**（`design.md §2 D1` / §4 / §7-1）。

## 0. 前置门

- [x] 0.1 独立零记忆 grill → `reviews/grill-design.md`（`## Confirmed Decisions` ≥3 条、每条带 `来源:`；
      `## Open Questions`；`## User Confirmation`）。G1–G6 已逐条落库（见该报告文末「## 处置」）。
- [x] 0.2 **停轮门**：`design.md §6` 的 **Q1**（新增豁免面可被伪造绕过 ⇒ A/B/C）**已由用户于 2026-10-17 裁定为 B**，
      原话要点与成本语义写进 `design.md §6` 与 `reviews/grill-design.md` 的 `## User Confirmation`。
- [x] 0.3 对抗轮 A1–A5（独立零记忆）→ `reviews/grill-adversarial-a1.md` … `a5.md`（各造出一条绕过；A5 的 X1 证明
      「覆盖」也不是充分条件）。**这五轮的产出是本 change 选 B 的直接依据**（`design.md §3` 留档）。
      ⚠️ **B 之后不再需要满轮重跑**，另跑 1 轮确认「B 形态下无未解决的可证伪项」（见 0.4）。
- [ ] 0.4 **B 形态的对抗确认（1 轮，独立零记忆）** → `reviews/building-review-b1.md` 或
      `reviews/grill-adversarial-b1.md`：重点确认「只改文案/文档」**没有**意外改变判定语义。

## 1. 规格

- [x] 1.1 `specs/archive-awareness/spec.md`：新 Requirement「搬移形状的 `D` finding SHALL 可行动」+ Scenario
      （含：**判定不变**、示例**能被 `covers` 认**、示例的类型**取自 policy**、诊断**不触发**的几种形态）。

## 2. 测试（先行）

- [x] 2.1 **判定不变表**（承重）：纯 `R100` 搬移 / issue #31 的 `D`+`A` / 纯 `D`+`A`（零 `R`）/ 单独删受保护文件 /
      删整个 change / 往已存在 archive 搬 / 部分搬移 ⇒ **退出码与 findings 的 path 集合与改动前逐字相同**。
- [x] 2.2 **诊断触发**（issue #31 的形态）：消息里含 `A` 的实际路径、「同一个 PR」「一条」、以及一个 JSON 示例；
      把示例解析出来喂 `events.covers` ⇒ **真**。
- [x] 2.3 **诊断不触发**：单独删 / 往已存在 archive 搬 / 源在 `<changes_root>/<id>/` 之外 / `<sub>` 为空。
- [x] 2.4 **示例的事件类型取自 policy**：换 policy 的允许集 ⇒ 示例跟着变；允许集带首尾空白 ⇒
      **不印**示例、改印「不可满足」诊断（B1-1）；允许集为空（**只能由代码构造的 Policy** 触发——
      `from_doc` 对 `[]` 回落默认）⇒ 不给示例（B1-3，纯函数级用例）。
- [x] 2.5 纯函数面：`move_half_candidates` 的相对子路径逐字相等 / 前缀边界 / `./` 归一化 / 多候选取字典序最小。

## 3. 实现

- [x] 3.1 `src/witnessloop/contract.py`：新增 `move_half_candidates(changes, policy, arrivals) -> dict[str, str]`
      （**纯函数、只喂文案**；签名与 `design.md §2 D2` 逐字一致）。
- [x] 3.2 `src/witnessloop/checkcmd.py`：`_protected_writes` 里**只拼文案**（在 `finding` 生成处追加诊断块）；
      **不改** `_archive_move_exempt`、**不改**两档判定。
- [x] 3.3 `docs/gate.md`：`§5.1`（归档豁免）补「配不上 rename 的旧侧怎么办」；`§7`（能力边界）补
      「诊断是启发式、不改变判定」。
- [x] 3.4 **不碰** `changed_change_ids`（`contract.py:355-417`）、不碰到达判据 1/2/3/5。

## 4. 验证

- [x] 4.1 `uv run pytest -q` 全绿（含既有 18 条 F + 6 条 N + `test_archive.py`）。
- [x] 4.2 **issue #31 的形态**：仍然 `✗ 1 项`（判定不变），且文案含诊断 + 可用的示例；
      **照文案补一行事件**之后 ⇒ `check：通过 ✓`（同一个 PR，零新增目录）。
- [ ] 4.3 本仓自举 `check` 判绿。
- [x] 4.4 **纯搬移回归**：本仓第一次归档的形态（58×`R100`）⇒ 仍然 0 findings、不需要任何事件
      （可用 `git log` 的 `3d600aa` 复算，或既有 `test_archive.py` 的归档用例）。

## 5. 收尾

- [ ] 5.1 实现后独立审阅闭环（reviewer ≠ author，收敛才停）→ `reviews/building-review.md`。
- [ ] 5.2 三份（+多轮）stage manifest；回链并**关闭** issue #31（comment 里引用裁定 B、成本、以及
      「纯 move 58×`R100` 全绿」的证据）。
- [x] 5.3 ~~（本 change 之后）用本修复做 witnessloop 第一次真实归档~~ —— **已提前完成且不依赖本 change**：
      纯 move 归档（PR #38 / merge `e88c5b2`）在**改动前**的判定下就全绿；它同时**证明了 B 的成本上限**。
