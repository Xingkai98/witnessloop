# Tasks: gate-ref-pins-package

> **停轮门**：`design.md §8` 的 Q1–Q3 拿到用户答复前，**不写任何实现代码 / 测试代码**。
> 本 change 的风险不是「改不动」，而是**把 `init` 的既有契约（幂等 / 只增不改）撞坏**、
> 以及把一次**全局**行为变化（改 `gate.yml` 默认值）当成局部改动发布。

## 0. 设计追问与用户确认（前置门）

- [ ] 0.1 独立零记忆 grill → `reviews/grill-design.md`（`## Confirmed Decisions` ≥3 条、每条带 `来源:`；
      `## Open Questions`；`## User Confirmation` 留空待用户答复）。
- [ ] 0.2 把 `design.md §8` 的 **Q1–Q3** 逐条停轮抛给用户（各附具体例子与推荐）。
- [ ] 0.3 答复逐条记进 `reviews/grill-design.md` 的 `## User Confirmation`（不得写「按推荐」这类占位）。
- [ ] 0.4 对抗轮（独立零记忆，**无轮数上限、收敛才停**）→ `reviews/grill-adversarial*.md`。

## 1. 规格

- [ ] 1.1 `specs/gate-ref-pinning/spec.md`：写「单一入口」与「不静默」两条 Requirement（措辞随 Q1 定）。
- [ ] 1.2 同步 `docs/gate.md` / `README.md` 的接入指引（怎么钉版本 / 怎么升级）。

## 2. 测试（先行）

- [ ] 2.1 纯函数：`workflow_ref` → ref 的解析（tag / 分支 / sha / 畸形 fail-closed）。
- [ ] 2.2 生成面：`init --gate-ref <ref>` 生成的 caller（随 Q1 定断言）。
- [ ] 2.3 升级路径：显式 `--gate-ref` 的覆盖语义（随 Q2 定）+ plain `init` 的幂等回归。
- [ ] 2.4 日志面：`gate.yml` 打 ref 的步骤（断言文件内容）。
- [ ] 2.5 回归：`init` 幂等 / `uninit` 回滚 / 冲突判定 / tests 文件独立路径。

## 3. 实现

- [ ] 3.0 **（先于 3.1；它是 Q1 的输入，grill M5）真 CI 探针**：确认 `github.workflow_ref` /
      `job.workflow_ref`（及各自 `*_sha`）在 **called workflow** 里指向谁。
      两个前提要写清：① 需要一个**含探针 gate.yml 的 ref**（可推的分支 / fork，**不能**推 `v1`）；
      ② 需要一个**接入方副本仓**（如 C1-b 的 throwaway 仓）。
      探针至少 `echo` 四个值，并把 caller 的 `uses:` 换到另一个 ref、观察哪个值跟着变。
      结论证伪 (B) ⇒ 整体退 (A)（§8 Q1）。
- [ ] 3.1 `.github/workflows/gate.yml`（默认值 / 日志）：**若走 (B)**——解析落在 **step** 里
      （`on.workflow_call.inputs.*.default` 只允许 `github, inputs, vars` 三个上下文 ⇒ `job.*` 用不了），
      且**接受判据**是「解析出的 `owner/repo` == `constants.REPO_SLUG`」，否则退 `v1` 并打日志（grill M7）。
- [ ] 3.2 `src/witnessloop/initcmd.py`（caller 生成 / `--gate-ref` 覆盖语义；随 Q1/Q2 定）。
- [ ] 3.3 本仓自己的 caller + 台账（Q3 裁 (a) 时）。
- [ ] 3.4 文档。

## 4. 验证

- [ ] 4.1 `uv run pytest -q` 全绿。
- [ ] 4.2 （探针已提前到 3.0；此处只留**端到端复验**：改 `uses:` 一处后，CI 日志里的 `witnessloop@<ref>` 跟着变）。
- [ ] 4.3 本仓自举 `check` 判绿。

## 5. 收尾

- [ ] 5.1 实现后独立审阅闭环 → `reviews/building-review.md`。
- [ ] 5.2 归档 / 回链 issue #30。
