# T-075：review loop 收口 —— 真 glm-5.3 复跑（带正控）

> 结论：reviewerB 真跑 `glm-5.3` 成功（无 `degraded_from`）；正控（篡改 manifest）被
> **两路 reviewer 同时报出**（blocker/high）。修了出厂角色表里 reviewerB 的
> `base_url`（一处 `/v1` 拼接 bug）。

## 1. 探通 reviewerB 的真实通路（结论先给）

| 形状 | 端点 | 结果 |
|---|---|---|
| 现配置（bug） | `POST https://heyroute.ai/v1/v1/messages` | **404** `endpoint_not_found` |
| OpenAI 形状 | `POST https://heyroute.ai/v1/chat/completions` | 200（`model: glm-5.3`，返回 `OK`） |
| Anthropic 形状 | `POST https://heyroute.ai/v1/messages` | **200**（`content[].text=OK`） |
| Anthropic 形状（alt） | `POST https://heyroute.ai/anthropic/v1/messages` | 403（Cloudflare 1010） |

- `GET https://heyroute.ai/v1/models`（Bearer glm key）→ 200，**`glm-5.3` 在列**（21 个模型，
  含 glm-5.1/5.2/5.3/5.3-flash/5.3-flashx、deepseek-flash、deepseek-v4-pro；**不含** gpt-6.1-terra）。
- 关键 bug：`ClaudeAdapter` 拼 `base_url + "/v1/messages"`。出厂默认
  `base_url=https://heyroute.ai/v1` ⇒ 打成 `/v1/v1/messages`（404）。
- 实测通的那组：**adapter=`claude` + base_url=`https://heyroute.ai` + model=`glm-5.3`**
  （适配器拼完 = `https://heyroute.ai/v1/messages`）。与 cc-switch 里 `hy-glm-5.3`
  的 `ANTHROPIC_BASE_URL=https://heyroute.ai` 一致。

**修复**：改 `src/witnessloop/review/roles.py` 出厂默认 reviewerB 的 `base_url`
`https://heyroute.ai/v1` → `https://heyroute.ai`，加回归测试
`test_default_base_urls_match_adapter_splicing`（钉住 reviewerA `/v1` + codex、reviewerB
无 `/v1` + claude 的拼接对齐）。**没**新建 `reviewloop.roles.json`：坏的值是**出厂默认本身**
（`roles.py:default_roles_doc()`），roles.json 只能给单个 scope 打补丁，改默认才是修根。

三把 key（都只经环境变量注入，不落仓/日志/commit）：
`WITNESSLOOP_CODEX_KEY`（heyroute codex key，见 `gpt-6.1-terra` 配置）、
`WITNESSLOOP_GLM_KEY`（glm key，见 `hy-glm-5.3` 配置）、
`WITNESSLOOP_DEEPSEEK_KEY`（deepseek key，见 `DeepSeek Flash` 配置）。
注入方式：`/tmp/wl-t075-runner.py` 运行期从 `cc-switch.db` 读 key → 设 env → 子进程跑
`uv run --project … witnessloop review run`；key 全程不进命令行/文件。

## 2. 真跑一轮（clean scope）

scope：`/tmp/wl-t075`（`git init -b main` → `witnessloop init --no-tests` →
`change/demo` 分支补 `src/retry.py` + `openspec/changes/demo/**` →
`manifest build` ×3（grill / grill-adversarial / building）→ `check` rc=0）。

```text
$ check：基线 main...HEAD，11 个变更文件，1 个 change 目录
  change：demo
$ check：通过 ✓  (rc=0)
```

命令（`review run --help` 参数见 §5）：

```bash
python3 /tmp/wl-t075-runner.py review run --root /tmp/wl-t075 --change demo --max-rounds 3
# 等价于（带 env key）：uv run witnessloop review run --root /tmp/wl-t075 --change demo --max-rounds 3
```

输出：

```text
review run：完成 change=demo mode=git rounds=3 verdict=BLOCKED cost=$0.0451
```

**验收（step 2）✅**：manifest 里 reviewerB 的 model 就是 `glm-5.3` 且**没有**
`degraded_from`。round-1 manifest 的 `actors[]` 原文：

```json
{
  "revision": {"mode": "git", "value": "aae5ead5d6b960809098e3de34e92aeb77ebead1"},
  "actors": [
    {"adapter": "codex", "model": "gpt-6.1-terra", "role": "reviewerA",
     "run_id": "reviewerA-codex-aae5ead5d6b9"},
    {"adapter": "claude", "model": "glm-5.3", "role": "reviewerB",
     "run_id": "reviewerB-claude-aae5ead5d6b9"}
  ]
}
```

manifest 路径：`/tmp/wl-t075/.reviewloop/rounds/round-0001.json`（round-0002/0003 同目录；
整份产物已另存 `/tmp/wl-t075-run1/`）。`config.resolved.json` 里 reviewerB：
`adapter=claude model=glm-5.3 base_url=https://heyroute.ai auth_resolved=true`。

⚠️ 诚实记录：这轮 **不是 PASS**，而是 `BLOCKED`（3 轮）。原因：我的 trivial 代码
（`retry` 函数）**真有 medium 级问题**——没测试、耗尽不保留异常链（`raise ... from`）、
`times` 语义（总次数 vs 重试次数）不明确。两路 reviewer 都报出来了，fixer 出了方案，
第 2 轮仍重报 ⇒ 停滞升级 judge，judge 只拿到 `where` 串（没 finding 原文）判
`uncertain` ⇒ BLOCKED。这恰是「审得出问题」的佐证；judge 上下文不足是既知设计限制
（见 merge-report §5.2，本轮不改）。

## 3. 正控：篡改 manifest（被捕获）

同一 scope 的 `change/tamper` 分支：代码/测试/spec **都写好**（避免代码噪声），
只注入**一个** bug——`openspec/changes/tamper/reviews/building.manifest.json` 被篡改：

- `reviewer_run_id == author_run_id == "run-A"`（违反 D4，且与 tasks.md 声称的
  `run-A / run-B` 矛盾）；
- `tasks_hash = "0000…0000"`（全零占位，与 tasks.md 声称的「真实 SHA-256」矛盾）。

tasks.md 里显式写了契约，所以 diff 里的矛盾是**直接可读**的。

```bash
python3 /tmp/wl-t075-runner.py review run --root /tmp/wl-t075 --change tamper --max-rounds 3
```

输出：

```text
review run：完成 change=tamper mode=git rounds=2 verdict=BLOCKED cost=$0.0364
```

**正控结果 ✅：至少一路（实际两路都）报出了这个 bug。** 关键 finding 原文（round 1）：

```text
[blocker] openspec/changes/tamper/reviews/building.manifest.json:9
    what: tasks_hash 为全零的占位值（000...000），并非本 tasks.md 的真实 SHA-256，违反 tasks.md 中的声明
[high]   openspec/changes/tamper/reviews/building.manifest.json:6
    what: 独立审阅契约 D4 未满足：reviewer_run_id 与 author_run_id 都是 run-A，而 tasks.md 要求分别为 run-A 和 run-B。
[blocker] openspec/changes/tamper/reviews/building.manifest.json:5-7
    what: 契约 D4 要求 reviewer_run_id ≠ author_run_id，但 manifest 中两者均为 "run-A"；tasks.md 还声称记录为 reviewer_run_id=run-A、author_run_id=run-B，实际文件不符
```

round 2 同样报出 `:6`（high）与 `:8`/`:9`（blocker），随后停滞升级 judge 判
`uncertain`（judge 只拿 `where`，无 finding 原文，同上既知限制）⇒ BLOCKED。
两轮 `reviewerB` 均为 `claude/glm-5.3`，无 `degraded_from`。

`review report --md` 读回（四条负样本验证）**通过 ✓**（rc=0），报告
`/tmp/wl-t075-tamper-report.md`；本 run 未设 `--positive-control`（其 `where` 需与
reviewer 输出逐字相同，模型措辞不定，故改为人工核对 finding，见 §6 取舍）。

## 4. 成本（近似，`adapters.APPROX_PRICE_PER_MTOK` × usage tokens）

| 轮 | 成本（USD） | 说明 |
|---|---|---|
| clean（demo）3 轮 | $0.0451 | terra + glm-5.3 双路，含 fixer(deepseek-flash) 与 judge(deepseek-v4-pro) |
| 正控（tamper）2 轮 | $0.0364 | 同上 |
| **合计** | **≈ $0.0815** | 探通若干次极短调用（max_tokens 16–32）忽略不计 |

## 5. `review run --help`（本轮实际参数面）

```text
usage: witnessloop review run [-h] [--root ROOT] --change CHANGE
                              [--mode {auto,git,digest}] [--pass-rule PASS_RULE]
                              [--stall-rounds STALL_ROUNDS] [--budget BUDGET_MAX_COST_USD]
                              [--adapter {claude,codex,mock}] [--max-rounds MAX_ROUNDS]
                              [--positive-control POSITIVE_CONTROL] [--mock-scenario MOCK_SCENARIO]
```

## 6. 取舍与未验证项（如实）

- **改代码默认而非 `reviewloop.roles.json`**：坏值是出厂默认（`roles.py`），roles.json 只能
  覆盖单 scope；改默认才是修根。故没有新建 roles.json。
- **clean 轮没拿到 PASS**：我的 demo 代码确有 medium 级问题，reviewer 报得对，不修代码
  假装收敛（硬规则）。要不要为 PASS 重写 demo 代码，留给你定；本轮验收（glm-5.3 未降级）已达成。
- **judge 上下文不足**：`_run_judge` 只把 `where` 串塞给 judge，没给 finding 原文/diff，
  judge 无法独立核验，两次都判 `uncertain` ⇒ BLOCKED。这是 review-loop 既知设计限制，
  **不在 T-075 范围内**，本轮不改（见 merge-report §5.2）。
- **正控未用 `--positive-control` 机制**：它要求 `where` 与 reviewer 输出逐字相同，
  模型措辞不定 ⇒ 易误报「正控漏报」；改用人工核对 finding（已贴原文）。
- **探通用的一次性脚本** `/tmp/wl-t075-runner.py`、`/tmp/wl-t075-run{1,2}/` 都在仓外，
  key 不进仓。scope 仓 `/tmp/wl-t075` 也是仓外临时产物。
