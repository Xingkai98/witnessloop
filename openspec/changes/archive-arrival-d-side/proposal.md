# Proposal: archive-arrival-d-side —— 配不上 rename 的旧路径掉队（issue #31）

> 状态：草稿（待 grill + 对抗 + 停轮）。关联 issue：witnessloop **#31**。
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

## 为什么它是误报

那个文件**没有被删除**——它**跟着 change 一起搬进了 `archive/`**（同一次 diff 里有一条同相对子路径的 `A`）。
git 没配出 rename，于是它的旧路径被当成「删除受保护文件」。
⇒ 补解释事件**不是**正确解法（它不是删除，是搬家）；正确解法是**把它认成那次搬移的另一半**。

## 目标

一条 `D` 记录，当**同时**满足下列条件时，SHALL 被视为**那次搬移的一半**（与 rename 的旧侧同等对待）：

1. 它的路径在 `<changes_root>/<id>/…` 下（**active** 源侧，`<sub>` 非空、不在 `archive/**` 下）；
2. **覆盖**：源 change 在**基准树**里的**每一个**文件，都有一条落在**同一个到达目录** `A` 之下、
   相对子路径**逐字相同**的记录（`R`/`C` 的落点，或 `A` 记录 + 对应 `D`）。
## 非目标

- **不**放宽到达判据本身（判据 1/2/3/5 一条不动）。
- **不**去恢复「配不上 rename 的那些文件」的配对信息（那要自己算相似度，是另一个面）；
- **不**宣称「任何伪造都挡得住」（capability 的既定边界：防漂移、不防伪造；但已实测的绕过一条不剩）。
- **不**动 `R`/`C` 那条既有豁免路径（它由 git 自己配对，本来就准）。

## 验收

- issue #31 的复现命令 ⇒ `check：通过 ✓`（红从 1 项降到 0 项）。
- **否定面**逐条仍红（`design.md §3` 的 N-a…N-o）——含**四轮独立审阅**各实测出的绕过（G1 / S2 / S8 / P7 / PFIVE），
  **全部**由「覆盖不成立」挡住（它们共同点都是「只搬了一两个文件」）：
  grill 的 G1「删整个 change + 别处一次正当搬移」、A1 的 S2「拖一个仍活着的 change 进来」、
  A2 的 P7「自造到达目录当钥匙」）——逐条见 `specs/` 的 Scenario。
