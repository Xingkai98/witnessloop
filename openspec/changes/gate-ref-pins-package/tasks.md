# Tasks: gate-ref-pins-package

> **停轮门已解除**（用户 2026-10-16 裁定 Q1–Q5，见 `design.md §8` 与
> `reviews/grill-design.md` 的 `## User Confirmation`）。实现按本文件执行。
>
> 本 change 的风险不是「改不动」，而是**把 `init` 的既有契约（幂等 / 只增不改）撞坏**、
> 以及把一次**全局**行为变化（新 ref 发布那一刻）当成局部改动发布。

## 0. 设计追问与用户确认（前置门）

- [x] 0.1 独立零记忆 grill → `reviews/grill-design.md`（`## Confirmed Decisions` ≥3 条、每条带 `来源:`；
      `## Open Questions`；`## User Confirmation`）。
- [x] 0.2 把停轮问题逐条抛给用户（各附具体例子与推荐）。
- [x] 0.3 答复逐条记进 `reviews/grill-design.md` 的 `## User Confirmation`（Q1–Q5，无「按推荐」类占位）；
      `design.md §8` 同步为「裁定」，两份文件的 **Q 集合 = {Q1…Q5}** 逐条一致。
- [ ] 0.4 对抗轮（独立零记忆，**无轮数上限、收敛才停**）→ `reviews/grill-adversarial*.md`。

## 1. 规格

- [ ] 1.1 `specs/gate-ref-pinning/spec.md`：按 Q1 裁定 (B′) 定稿「单一入口」与「不静默」两条 Requirement
      （含 K1 订正：包**能**自报 ref）。
- [ ] 1.2 同步 `docs/gate.md` / `README.md` / `docs/design.md` 的接入指引（怎么钉版本 / 怎么升级）。

## 2. 测试（先行）

- [ ] 2.1 解析面：从 `gate.yml` 抽出解析 step、用 `bash` 真跑（`GITHUB_OUTPUT` 捕获结果），覆盖
      `job.workflow_sha` 主路径 / 显式 `with:` 覆盖 / repository 不匹配 / sha 缺失走 `job.workflow_ref`
      兜底（`refs/heads/*`、`refs/tags/*`）/ 两样都缺 / `refs/pull/N/merge` 畸形 ⇒ fail-closed 退 `v1` + warning。
- [ ] 2.2 生成面：`init --gate-ref <ref>` 生成的 caller 里 `uses:` 逐字等于该 ref（(B′) 下 `caller_workflow()` 字节不变）。
- [ ] 2.3 升级路径：显式 `--gate-ref` 的覆盖语义（重写 caller + 同步台账 `sha256`/`gate_ref`、EXIT=0、
      随后 plain `init` 幂等、`uninit` 仍可用）+ plain `init` 的幂等回归 + 新仓目标文件已存在仍冲突。
- [ ] 2.4 日志面：`gate.yml` 把 ref 打进 `::notice::` 的那一步（断言文件内容）。
- [ ] 2.5 自报面：`check` 读 `direct_url.json` 的最佳努力实现（有 `vcs_info` ⇒ 打出；没有 ⇒ `<未知>` 且不影响退出码）。
- [ ] 2.6 回归：`init` 幂等 / `uninit` 回滚 / 冲突判定 / tests 文件独立路径。

## 3. 实现

- [x] 3.0 **真 CI 探针（Q1 的输入）—— 已跑成并定案**：跨仓形态（副本仓 `Xingkai98/asterwynd-wl-switch`
      的 caller → `Xingkai98/witnessloop/.github/workflows/probe-ref.yml@probe/workflow-ref`，run `38853369550`）
      实测 `job.workflow_sha` = reusable 自己的 commit、`github.workflow_sha` = 接入方自己的 commit
      ⇒ 定案 (B′)。**落点**：原始输出写进 `design.md §2 D1`（K8 要求的「结果贴回哪里」）。
      探针用的分支与文件**已全部删除**（witnessloop 侧复查 404），不留残余。
- [ ] 3.1 `.github/workflows/gate.yml`：`inputs.witnessloop-ref.default` 改 `""`；新增**第一个 step**
      （`id: wl-ref`）按 (B′) 解析并打 `::notice::`/`::warning::`；`uvx` 改用 `steps.wl-ref.outputs.ref`。
      接受判据 = `job.workflow_repository == constants.REPO_SLUG`，否则 fail-closed 退 `v1` 并打日志（M7）。
- [ ] 3.2 `src/witnessloop/initcmd.py`：已接入分支里，显式 `--gate-ref` ⇒ 重写 caller + 同步台账（Q2 (a)）。
- [ ] 3.3 `src/witnessloop/checkcmd.py`：自报本包 VCS ref（Q4 (a)，尽力而为）。
- [ ] 3.4 文档：`docs/gate.md`（§1 caller 行 + **§7 能力边界**加 Q5 的登记）、`README.md:20,119-121,170-177`、
      `docs/design.md:56,73`（K6）。
- [ ] 3.5 **`(post-merge)` 本仓自身迁移**：**不在本 PR 内**（design §2 D4：目标 ref 只在合并后才存在）——
      更新 `.github/workflows/witnessloop.yml` + `.witnessloop/init-manifest.json`，并建
      `openspec/changes/gate-ref-pins-package/workflow-events.jsonl` 写一条 `protected_path_write`
      （`artifact_path` 指向 `.witnessloop/init-manifest.json`、`reason`/`approved_by` 非空），
      否则改台账这个 `M` 必红。

## 4. 验证

- [ ] 4.1 `uv run pytest -q` 全绿。
- [ ] 4.2 端到端复验：改 `uses:` 一处之后，CI 日志里的 `witnessloop@<ref>` 跟着变（由 3.0 的跨仓探针实证）。
- [ ] 4.3 本仓自举 `check` 判绿。

## 5. 收尾

- [ ] 5.1 实现后独立审阅闭环 → `reviews/building-review.md`。
- [ ] 5.2 归档 / 回链 issue #30。

## 6. `(post-merge)` 待办（Q3 裁定；**本 PR 内一律不做**）

- [ ] 6.1 建 tag **`v1.7.0`**（指向合并后的 `main` 上含本 change 的那个 commit）。
- [ ] 6.2 把 `src/witnessloop/constants.py` 的 `DEFAULT_GATE_REF` 从 `…gate.yml@v1` 改成 `…gate.yml@v1.7.0`，
      并同步 `tests/test_gate_workflow.py` 里那条 `== …@v1` 的断言。
- [ ] 6.3 完成 3.5 的本仓自身迁移（caller + 台账 + 解释事件）。
- [ ] 6.4 **发布说明**里写清这是一次**全局**行为变化（design §4 R2）：接入方把 `uses:` 指到含新 gate.yml 的 ref 时，
      所有这样的仓**同时**切换包来源解析；并给出回退路径（指回旧 ref，或显式 `with: witnessloop-ref:`）。
- [ ] 6.5 ⚠️ **不动 `v1` tag**（它是别人依赖的发布物）。
