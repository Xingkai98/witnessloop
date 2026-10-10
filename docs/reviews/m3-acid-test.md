# M3 acid test 记录（第二仓 + 真实分发）

> 2026-10-09。测试仓：`Xingkai98/wl-test`（一次性）。工具：`uv tool install git+https://github.com/Xingkai98/witnessloop@v1` → 解析到 commit `d213694`（含 M1+M2）。
> 目的：在**第二个真实仓**上验证 M1 门禁层 + M2 交互层（本轮先做 F2–F5 机械项；F1 全流程交互式，另记）。

## 安装

```
$ uv tool install --force "git+https://github.com/Xingkai98/witnessloop@v1"
Installed 1 executable: witnessloop                       # EXIT=0
$ witnessloop --version
witnessloop 0.1.0
# provenance: requested_revision v1 → commit_id d213694
```
`--help` 列出 `init / uninit / check / manifest`（`manifest` 下只有 `build`）。

## F4 — 不跑 init → 未接入 ✓

全新临时仓，不跑 `init`：
```
$ witnessloop check --root /tmp/f4-repo
check：未接入 witnessloop ✗
  没有找到 .witnessloop/policy.json。门禁 fail-closed：未接入 = 不放行。
  请先在目标仓运行 `witnessloop init` 并提交其产物。
EXIT=3
```
**符合预期**：exit 3（不是 0、不是 1），fail-closed 分支正确。

## F5 — init → uninit 往返 ✓（语义已澄清）

```
$ witnessloop uninit
uninit：已回滚 witnessloop 接入：
  - .witnessloop/policy.json
  - .github/workflows/witnessloop.yml
  - .witnessloop/init-manifest.json
EXIT=0
$ ls .witnessloop/                      # → No such file or directory（空目录也清掉）
$ git status --porcelain
 D .github/workflows/witnessloop.yml
 D .witnessloop/init-manifest.json
 D .witnessloop/policy.json
$ witnessloop uninit                    # 幂等
uninit：未接入（或已回滚），无改动。      EXIT=0
$ witnessloop init                      # 恢复
init：已接入 witnessloop（文件未 commit，请人工审阅后提交）  EXIT=0
```
**符合预期，但「工作树干净」不是正确预期**：init 产物在 wl-test 里**已被提交**，而 uninit 遵契约「不 auto-commit」，删已跟踪文件必然在 `git status` 留 3 条 `D`。**正确预期 = 「文件被删、无残留半删状态」**（本次达成）。「干净树」只在 init 产物从未被提交时成立。

附带观察：re-init 非字节幂等——`init-manifest.json` 的 `created_at` / `base_ref` / `base_sha` 会随重跑时的分支与 HEAD 变化。三个都是 informational 字段（`check` 不读、`uninit` 只读 `created_files` 的 hash），无功能影响。

## F2 — 手写放行事件 → check 通过 ✓（默认不防伪造）

`acid/f2` 分支（base = `main`），按 `gate.md §3.1` 两段提交：
```
# change 目录 openspec/changes/test-f2/{proposal,design,tasks}.md + specs/ + reviews/
# 写受保护路径 openspec/specs/test/spec.md
# 手写一行事件 workflow-events.jsonl：
#   {"event_type":"protected_path_write","artifact_path":"openspec/specs/test/spec.md",
#    "reason":"…","approved_by":"手填审批人（acid test）"}
$ git commit …                                   # ①内容提交 → 1c0f80a
$ witnessloop manifest build --change test-f2 --stage building \
    --report reviews/building-review.md \
    --reviewer-run-id acid-f2-reviewer --author-run-id acid-f2-author --base main
manifest build：已写入 …/reviews/building.manifest.json（未 commit）
  head_sha=1c0f80a…  base_sha=6564d42…            EXIT=0
$ git commit …                                   # ②证据提交 → 8408cad
$ witnessloop check --base main --head HEAD
check：基线 main...HEAD，8 个变更文件，1 个 change 目录
  change：test-f2
check：通过 ✓                                     EXIT=0
```
**符合预期**，正是 design §2 承认的边界：`approved_by` 随手填、事件手写，门禁照样放行。

**负控（强化结论）**：把 `workflow-events.jsonl` 清空后重跑 → check 立刻报
`openspec/specs/test/spec.md：受保护路径被写入，但没有结构化解释事件` EXIT=1。
证明事件**是**放行的那根杠杆，F2 不是「check 根本没查受保护路径」。

## F3 — 证据漂移 → 报错而非双绿 ✓

在 F2 基础上，再改一个被 hash 绑定的 artifact（`tasks.md`）：
```
$ git commit … openspec/changes/test-f2/tasks.md   # → 0362859
$ witnessloop check --base main --head HEAD
check：未通过 ✗（2 项）
  1. …/reviews/building.manifest.json：tasks_hash 不匹配：tasks.md 的字节与 manifest 记录不符（evidence 与 artifact 已漂移）
  2. …/reviews/building.manifest.json：审阅的是旧 revision：head_sha=1c0f80a… 之后又改动了非证据文件：openspec/changes/test-f2/tasks.md
EXIT=1
```
**符合预期**：两条独立机制都命中（hash 绑定 + stale revision），确实是报错而非双绿。

## F1 — 全流程 ✓

在 `wl-test` 分支 `acid/f1` 上端到端跑通（发布 tag 装工具）：

```
init → change(add-greeting) → grill（grilling pass + 设计阶段对抗验证 3 轮收敛 PASS）
  → 用户逐条确认 Q1–Q7 → 整合 design → TDD 实现（13 tests）→ review-loop（1 轮 PASS）
  → 先内容后证据两段提交 → manifest build ×2 → check
$ witnessloop check --base main --head HEAD
check：基线 main...HEAD，14 个变更文件，1 个 change 目录
  change：add-greeting
check：通过 ✓                       EXIT=0
```

证据：`reviews/{grill-review.md, grill-adversarial.md, building-review.md, grill.manifest.json, building.manifest.json}`。

**过程要点**：
- grill 时序 = **先对抗收敛、后用户确认**（`v1.3.0`）。对抗验证跑了 **3 轮**（CHANGES_REQUESTED×2 → PASS），期间逮到一个**真事实错误**（`greet(b"Alice")` 其实不抛异常、会静默产脏值）与一处**与已提交 spec 的冲突**——**都在用户看到之前被拦下**。这就是「收敛后才停轮」的价值。
- review-loop **1 轮 PASS**（三态 verdict；审阅者逐条读代码核实 `tasks.md` 的 `[x]`）。

