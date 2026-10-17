# Proposal: archive-arrival-d-side —— 让「掉队的 `D`」那条红**可行动**（issue #31）

> 状态：**停轮已解除**（用户 2026-10-17 裁定 **B**，见 `design.md §6` 与
> `reviews/grill-design.md` 的 `## User Confirmation`）。关联 issue：witnessloop **#31**。
> 实测来源：witnessloop `main`，用接入方 asterwynd 的真实历史复现（issue #31 正文有原始输出）。

## 背景

「归档到达」的判定是**目录级事实**（change `archive-awareness` / `archive-arrival-recognition`）：
`archive/<name>/` 在基准树里**没有 entry**、在 head 里是**含全部必需件**的 change 目录、
且内容**不是搬运现成证据**。到达组**按新路径**收集（`contract.archive_arrivals` 里 `under_path(change.path, directory)`）。

**缺口**：git 在**配不上 rename** 时会把同一个文件记成**两条独立记录**——一条 `D`（旧 active 路径）+ 一条 `A`（archive 路径）。
那条 `D` 的路径**不在** archive 目录下 ⇒ 进不了到达组 ⇒ 在 `check` 眼里它是「**删除一个受保护文件**」⇒ 要求解释事件。

### 实测（issue #31 原文，本机可复算）

```
git checkout -f d94c08334        # 接入方 asterwynd 的收尾链末端（change 此时已在 archive/）
# 用归档目录名重绑三份 manifest（#29 文档规定的次序）并提交
python3 -m witnessloop check --root . --base 8e5fc83b --head HEAD
```
`8e5fc83b` 是「change **在 base 里已是 active**」的形态（docs-first）。`git diff -M --name-status` 里**只有一条 `D`**：
`D  openspec/changes/guard-write-allowlist/workflow-events.jsonl`（该文件在 range 内被改写过，git 没配成 rename；其余文件配对正常）。

```
check：基线 8e5fc83b...HEAD，34 个变更文件，1 个 change 目录
  change：2026-10-14-guard-write-allowlist（归档）
check：未通过 ✗（1 项）
  1. openspec/changes/guard-write-allowlist/workflow-events.jsonl：受保护路径被写入，但没有结构化解释事件
```

⇒ **到达本身认出来了**（1 个 change 目录、标签是归档路径、无幽灵 active id），**这条红只来自那个掉队的 `D`**。

## 用户裁定：**B —— 不发豁免**（2026-10-17）

> 原话要点：**不发豁免**，由接入方在**同一个开发 PR 内**补**一行** `protected_artifact_explained` 事件；
> **不允许因此增加 PR 数量**。用户明确确认：「纯搬移不用写，只有归档时顺手改了被搬文件才需要；仍然一个 change 一个 PR。」

⇒ 本 change **不新增任何豁免面**：`D` 记录照旧要求解释事件（**判定结果与改动前逐字相同**）。
要交付的增量只有一个：**让那条 finding 变得可行动**。

## 目标

1. **诊断（不判定）**：当一条受保护路径的 `D` 记录**看起来是搬移的一半**时——
   同一次 diff 里存在一条 `A`，落在某个**到达**的归档目录 `A_dir` 下、且**相对子路径逐字相同**——
   那条 finding 的文案 SHALL 补上：
   - 说明「这可能是搬移的一半（旧路径被删、`<A_dir>/<sub>` 是新路径）」；
   - 给出**补救**：在**同一个 PR** 内补解释事件（**通常一条**；若追加本身让该 events 文件的旧路径也掉成 `D`，
     再补一条覆盖它——同一文件、同一 PR），`artifact_path` 指向该文件；
   - 给一个**可直接复制的 JSON 示例**（事件类型取自**本仓 policy 的允许集**——见 `design.md §2 D3`）。
2. **不改变任何判定语义**：豁免面、findings 的**数量与归属**、退出码，全部与改动前相同。
   本 change 之后，issue #31 的那条红**仍然红**——只是**照着文案补一行事件就能在同一个 PR 内消掉**。

## 非目标

- **不**给 `D` 记录加豁免（用户裁定 B；A 选项的完整实测史见 `design.md §3` 的「留档」）。
- **不**去恢复「配不上 rename 的文件」的配对信息、**不**比内容、**不**新造事件类型。
- **不**动到达判据 1/2/3/5，**不**动 `_archive_move_exempt` 的既有 `R`/`C` 路径。

## 验收

- **issue #31 的复现形态**：仍然 `✗ 1 项`（**判定不变**），但该 finding 的文案里含
  ①「搬移的一半」的判定依据（`<A_dir>` 与实际 `A` 路径）、② 一行事件的补救、③ 一个**能直接通过 `events.covers`** 的 JSON 示例。
- **照文案补一行事件之后**（同一个 PR 内）：`check：通过 ✓`——证明文案给的是**真能用的**补救。
- **纯搬移（58×`R100`，本仓第一次归档那次）**：仍然 `通过 ✓`、**不需要任何事件**（用户裁定原文：「纯搬移不用写」）。
- **判定不变**：既有 18 条 F 组 + 6 条 N 组 + `test_archive.py` 全绿；新增的「判定不变」用例逐条断言
  **退出码与 findings 集合**与改动前一致（只在文案上多了一段）。
