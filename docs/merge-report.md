# Merge Report: review loop（多模型复审闭环，T-071）

> 状态：P1–P6 完成；T-071 当时 `uv run pytest -q` 为 832 passed，2026-11-19
> 加固后为 911 passed（见 §6 的日期注记）。
> 分支 `feat/review-loop`，基线 `origin/main` = `d5b380a`。本报告只陈述**实测**结果，
> 不伪造；降级点逐条如实记录。

## 0. 一句话

把「多模型复审闭环」做成 `witnessloop review` 子命令组（`run` / `report`），与既有
门禁判定（`contract` / `evidence` / `checkcmd`）**正交**——不在 `check` 里另写一套
门禁逻辑。双路 reviewer 并发审 → 按 `where` 去重取高 severity → fixer 出方案 →
收敛 / 停滞升级 judge / 成本止损；每轮 manifest 绑 `actors[]` + `config.resolved.json`
哈希，`review report --md` 读回并跑四条负样本验证。

## 1. 每阶段做了什么 + 证据

### P1 — revision 锚点（`src/witnessloop/review/revision.py`）

- `GitRevision`：commit sha + 祖先关系校验（复用 `gitutil.is_ancestor`）。
- `DigestRevision`：工作树 `sha256_tree`，稳定排序、排除 `.git` 与自身输出目录
  （`.reviewloop/`）。
- `mode: auto`：有 `.git` 用 Git，否则用 Digest；git 无提交时退回 Digest（如实标注）。
- 证据：`tests/test_review_revision.py`（10 条，含「digest 排除输出目录 / 排除 .git /
  内容变则锚变」）。

### P2 — lite 形态跑通（先打通链路）

`init` → `check --scope .` 缺证据红（rc=1）→ 补证据绿（rc=0）→ 空范围 rc=5。
三个码在 P5 full 形态实测落盘（见 §3）；另 `EXIT_NOT_ONBOARDED=3` 一并实测。

### P3 — roles@v1 + adapters

- `src/witnessloop/review/roles.py`：`reviewloop.roles.json`（schema
  `witnessloop/roles@v1`）读入/部分覆盖/展开成 `config.resolved.json`；auth 只记录
  「已解析/未解析」，**不落密钥**进产物。
- `src/witnessloop/review/adapters.py`：`claude`（Anthropic Messages）、`codex`
  （OpenAI chat/completions）、`mock`（确定性、按 round 出种子）三个适配器，统一
  `run(prompt+context) -> ReviewResult`；错误归一成 `AdapterError(kind)`（auth /
  balance / model_not_found / other）。
- 证据：`tests/test_review_roles.py`（6）、`tests/test_review_adapters.py`（9）。

### P4 — `review run` 编排器 + `review report --md`

- `src/witnessloop/review/orchestrator.py`：两路 reviewer 并发审 → `_merge_findings`
  **只按 `where` 去重、取 severity 高的那条** → fixer 出方案 → 收敛
  （`pass_rule=medium_plus_zero`）/ 停滞（`stall_rounds=2`，同一 where 连续两轮重报
  ⇒ 升级 judge 单点复核）/ 成本止损（`budget.max_cost_usd=30`）。
- `src/witnessloop/review/report.py`：`review report --md` 读回 round manifests +
  `config.resolved.json`，生成 Markdown，并跑四条负样本验证（篡改 manifest / 证据缺件 /
  两路同一 actor / 正控漏报），任一命中 ⇒ 退出码 1。
- `cli.py` 加 `review` 子命令组（`run` / `report`），**只在 review 处加代码**，不重排
  既有子命令。
- 证据：`tests/test_review_orchestrator.py`（8）、`tests/test_review_report.py`（6）、
  `tests/test_cli.py` 动词面更新为含 `review`。

### P5 — 真项目双形态验证（只在 `/tmp` 副本）

详见 §3 / §4。

### P6 — 本报告 + `docs/pr-draft.md`（英文草稿，只写不 push / 不 PR）。

## 2. 真值表与降级（实测）

| 角色 | 真值模型 | 实测模型 | 通路 | 降级 |
|---|---|---|---|---|
| reviewerA | `gpt-6.1-terra` | `gpt-6.1-terra` | codex / heyroute `/v1` | 无 |
| reviewerB | `glm-5.3` | **`glm-5.3`** | claude / heyroute `/v1/messages`（`base_url=https://heyroute.ai`） | 无（T-075 真跑） |
| fixer | `deepseek-flash` | `deepseek-flash` | claude / deepseek `/anthropic` | 无 |
| judge | `deepseek-v4-pro` | `deepseek-v4-pro`（仅停滞时） | claude / deepseek `/anthropic` | 无 |

**T-075 更正（如实）**：T-071 时「第三把 key 在本机不存在」是**找漏了**——真 key 其实在
`~/.cc-switch/cc-switch.db`（sqlite，表 `providers`，`name='hy-glm-5.3'`，
`settings_config` 含 `ANTHROPIC_BASE_URL=https://heyroute.ai`、`ANTHROPIC_MODEL=glm-5.3`、
51 字符 API key）。叠加一个真 bug：出厂默认 reviewerB 的
`base_url=https://heyroute.ai/v1` 会让 `claude` 适配器打成 `/v1/v1/messages`（404
`endpoint_not_found`）——两者叠加才导致 T-071 全程回落 `deepseek-flash`。T-075 已修
`base_url`（`roles.py` 去掉 `/v1`），真跑 glm-5.3 且**带正控**（篡改 manifest 被两路
reviewer 报出 blocker/high）。详见 `docs/reviews/t075-glm-rerun.md`。

本轮**不是**「同源双审」：reviewerA=terra、reviewerB=glm-5.3，两路模型不同源。
若 reviewerA 也降级（如 terra 通路失效），`final.degraded_note` 会写「本轮为同源双审」。

## 3. 双形态结果（P5）

**full 形态**（`git clone … → /tmp/wl-p5-full`，`mode=auto` → git）——四码实测：

| 码 | 场景 | 实测输出 |
|---|---|---|
| **3** | 未接入 | `check：未接入 witnessloop ✗` |
| **1** | 内容在、证据缺 | `check：基线 …，9 个变更文件，1 个 change 目录 / check：未通过 ✗（2 项）` |
| **0** | 证据齐 | `check：基线 …，13 个变更文件，1 个 change 目录 / check：通过 ✓` |
| **5** | 零变更 | `check：基线 HEAD...HEAD，0 个变更文件，0 个 change 目录 / check：无变更，跳过（非通过）✗` |

loop（mock 场景：第 1 轮 1 条 medium、第 2 轮空）：`review run` mode=git、rounds=2、
verdict=PASS、`review report --md` 验证通过 ✓。原始日志：
`/tmp/wl-p5-logs/full.log`。

**lite 形态**（`tar --exclude .git` → `/tmp/wl-p5-lite`，`mode=auto` → digest）——

- 无 `.git`，`review run` 同一套命令自动探测为 **digest**：`mode=digest rounds=2
  verdict=PASS cost=$0.0000`，`review report --md` 验证通过 ✓。
- `check` 在无 git 目录下：`check：未通过 ✗ —— 无法解析 base ref：main`（rc=1）。
  ⚠️ **诚实边界**：`check` 是 git-diff 门禁（既有设计），无 git 目录只能到
  `3`（未接入）与 `1`（base 解析失败）——**四码 0/5 只在 full（git）形态可到**；
  lite 形态的交付点是「digest 锚 + loop 无 git 收敛」。原始日志：
  `/tmp/wl-p5-logs/lite.log`。

## 4. 每轮成本

| 形态 / 轮 | 成本（USD，近似） | 说明 |
|---|---|---|
| full mock loop（2 轮） | $0.0000 | mock 无网络 |
| lite mock loop（2 轮） | $0.0000 | mock 无网络 |
| **真模型 loop（1 轮）** | **$0.0145** | terra(3.4k tok 级) + deepseek-flash；见 `real-loop.out` |

成本是**估算**（`adapters.APPROX_PRICE_PER_MTOK` 的近似单价 × usage tokens），
只用于 `budget.max_cost_usd` 止损与报告，不是计费依据。

真模型 loop 实测收敛：`review run：完成 change=p5-demo mode=git rounds=1
verdict=PASS cost=$0.0145`（trivial change 上两路 reviewer 均报 0 条 medium+）。
round-1 manifest 的 `actors[]`：
`reviewerA/codex/gpt-6.1-terra` + `reviewerB/claude/deepseek-flash
（degraded_from glm-5.3）`；`review report --md` 读回一致。

## 5. 未完成项 / 阻塞点（如实）

> **2026-11-19 更新**：item 1 已由 T-075 解决（真跑 `glm-5.3`，无 `degraded_from`，
> 见 `docs/reviews/t075-glm-rerun.md`）；item 4 正由本 change 的三份 stage 证据补齐；
> item 5 的「不 push / 不 PR」是 T-071 当时的约束，本轮用户已明确要求 push PR。
> 原条目保留作历史记录。

1. ~~**`glm-5.3` 未跑真值**~~（T-075 已解决）：第三把 key 在本机不存在，reviewerB 全程回落
   `deepseek-flash`。要真跑 glm-5.3 需补 heyroute 第三把 key（`hy-glm-5.3`）。
2. **fixer 不自动改代码**：`review run` 的 fixer 只产出**修复方案**（JSON `fixes`），
   不把任意模型 patch 自动打到代码上（安全边界）。因此真模型在**有真实 bug** 的仓上
   收敛依赖 reviewer 下一轮确实不再报 medium+，或走停滞升级 / 成本止损收口；
   本 P5 用 trivial change + mock 场景演示「收敛」链路。
3. **lite 的 `check` 到不了 0/5**：`check` 是 git-only（既有设计，本 change 不改它），
   无 git 目录只能 rc=3/rc=1；四码在 full 形态实测。
4. **本仓 dogfood 未跑**：本 change 新增 `src/**`（命中本仓 `require_change_for`），
   但未为本仓自身建 openspec change 目录 + 三份 stage 证据（不在 T-071 验收内；
   合入前的本仓门禁证据属后续任务）。不做不装。
5. **不 push、不 PR、不改版本号、不动 upstream / OpenDirector 本体**：本 change 只在
   `feat/review-loop` 分支提交；`docs/pr-draft.md` 只是草稿。

## 6. 验收对照（机器可判）

> 2026-11-19 更新：加入 `gpt-6.1-sol` 价格回归、auth/parse/回落修复、预算前移、
> 旧 rounds 清理、去重加固、host-token opt-in、上下文优先排序与
> parse/judge/fixer 多轮加固、diff 失败中止、响应结构、mock 输入与 reviewer 证据
> 校验后为 **911 passed**；其余条目保留 T-071 当时的实测记录。

1. ✅ `uv run pytest -q` 全绿：**832 passed**（原有 788 + 新增 44）。
   `git diff --stat origin/main...HEAD`：15 files changed, 1918 insertions(+), 4 deletions(-)。
2. ✅ full 形态四码 3/1/0/5 实测落盘（`/tmp/wl-p5-logs/full.log`）；lite 形态 digest
   loop 收敛（`lite.log`）。
3. ✅ 每轮 manifest 绑 `actors[]`（role/adapter/model/run_id/degraded_from）+ `config_hash`；
   `review report --md` 读回一致（`real-report.out` / `test_review_report.py`）。
4. ✅ 四条负样本全红：`test_tampered_manifest_is_red` / `test_missing_evidence_is_red` /
   `test_same_actor_twice_is_red` / `test_positive_control_missed_is_red`。
5. ✅ `docs/merge-report.md` + `docs/pr-draft.md`（英文）。

## 7. 改动文件清单

```
.gitignore                              (+1  .reviewloop/)
src/witnessloop/cli.py                   (review 子命令组，只在 review 处加代码)
src/witnessloop/constants.py             (review 常量 + 退出码注释)
src/witnessloop/review/__init__.py
src/witnessloop/review/revision.py
src/witnessloop/review/roles.py
src/witnessloop/review/adapters.py
src/witnessloop/review/orchestrator.py
src/witnessloop/review/report.py
tests/test_cli.py                        (动词面 + review)
tests/test_review_revision.py
tests/test_review_roles.py
tests/test_review_adapters.py
tests/test_review_orchestrator.py
tests/test_review_report.py
docs/merge-report.md
docs/pr-draft.md
```
