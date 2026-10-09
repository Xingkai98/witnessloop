# 对抗验证报告：grill 结论复核

> 两个独立零记忆审阅者对 grill 报告做对抗验证（2026-10-09）。READ-ONLY。
> A = 事实核查（试图证伪 grill 的事实断言）；B = 建议批判（试图证伪 grill 的建议）。
> 结论：grill 的**核心命题成立**（现状是防漂移、不防伪造），但有**两处夸大**被纠正；建议部分被**大幅砍范围**。

---

## A. 事实核查

**总评**：断言 1/2/4 成立；3 部分成立（presence 有、语义绑定无）；5 成立（行数微偏）。grill 有两处框架性夸大。

| # | grill 断言 | 裁定 | 硬证据 |
|---|---|---|---|
| 1 | `awaiting` 没退役 | **成立（有重要保留）** | `event_log.py:51-54` 三态；`:365-367` `is_awaiting_state`；`workflow_guard.py:540-561` `_awaiting_block_reason` 命中则 exit 2。**保留见下「遗漏」第 1 条——入口已删。** |
| 2 | 受保护路径放行可自证 | **成立** | `check_openspec_artifacts.py:1246-1263`：`required_fields=("reason","approved_by")`，仅校验非空字符串；`approved_by` 无签名，CLI `workflow_state.py:696` 自由文本直写。 |
| 3 | `reviewer_run_id` 全仓无校验 | **部分成立** | grep 只在写/读/常量/测试。**但** `review_manifest.py:188-190` 有**非空 presence 校验**；缺的是与真实审阅 run 的**语义绑定**，不是「无任何校验」。 |
| 4 | `_verify_git_span` base/head 不存在时静默跳过 | **成立** | `review_manifest.py:215` 函数体，跳过点在 `:231-232`；返回空 errors，无告警。 |
| 5 | checker ~1780 行 + 硬编码枚举 | **成立（行数略偏）** | 实测 **1802 行 / 72486 B**；`ALLOWED_TYPES(:31)`、`DESIGN_TYPES(:32)`、`BENCHMARK_SMOKE_CAPABILITIES(:35)`、`DESIGN_SECTIONS(:51)`、backlog 路径 `(:1694)`。 |

**grill 的事实错误 / 夸大**：

- 行号偏差：`event_log.py` 实为 51-54；`_verify_git_span` 跳过点在 231-232。
- 「只校验字段非空」欠准：还校验 `schema`、`event_type ∈ allowed`、`change_id` 匹配与路径覆盖。
- 「`reviewer_run_id` 无任何校验」**夸大**：存在非空 presence 门。
- 「退役的只是 handoff/workflow-state 不再入库」不准确：AGENTS.md 明列 `flow approve/advance/block/confirm` 与 legacy 子命令**已删除**；`.gitignore` 只忽略 **active** 路径，`git ls-files` 显示 11 份归档 `workflow-state.json` + 多份归档 `handoff.json` **仍被跟踪**。

**grill 遗漏的重要事实**：

1. **awaiting 无入口**：`append_blocked_event`（`event_log.py:98`）**无任何生产调用方**（仅 tests）；CLI 入口（`flow block/confirm`）已删。guard 执法保留但**近乎不可达**——说成「活的 gate」有误导。
2. **hook 层在 CI 不存在**：guard 是 PreToolUse hook，靠手动 cp `workflow_hook.example.json`；本 worktree 无 `.claude/`。**CI 只跑 checker 一层**——「双层兜底」只在交互式会话成立。
3. **manifest 非纯自由文本**：`report_hash`/`spec_hash`/`tasks_hash` **绑定真实 artifact 字节**；仅身份字段（`reviewer_run_id`/`approved_by`）是自由文本。
4. **CI 已知并规避第 4 条**：`ci.yml` 用 `fetch-depth: 0` + `--require-base` 对冲静默跳过。
5. 存在 kill switch：`workflow_methods.json` 的 enable 开关。

---

## B. 建议批判

**立场**：默认怀疑。判据：每项是「让**首个真实仓库**跑通门禁」的必要件，还是「为通用/安全先造机制」的延后件。

**报告的系统性缺陷**：12 项里 **0 项主张删减**，全是新增机制。早期原型的真实死因是「**永远做不完**」，不是缺功能。

**先纠正一个隐含前提**：真实强制是 **PreToolUse hook + CI required check**，**不是签名**；证据核心是 **review manifest**（仅 264 LOC）；asterwynd **全库无任何签名**（`grep hmac|ed25519|nacl` 全空）。

| 条 | 裁定 | 反建议 |
|---|---|---|
| Q1 事件日志+签名 | ❌ 过度设计 | **砍签名与密钥对**（单机私钥=零防御）。真正的锚是远端 branch protection + required check，**人手动开一次就是那个「人类签名」**。事件日志降为可选历史。 |
| Q2 spec-agnostic 适配器 | ⚠️ 方向对、轴错 | 验收要的是「第二个**仓库**」不是「第二个 spec 系统」。v1 把 OpenSpec 形状契约**硬编码**；要参数化的轴是 **repo-agnostic**（路径/策略）。 |
| Q3 不变集 | ✅ 对，但要封顶 | 不变集只留**自保护**规则，~5 条封顶，默认开（无 policy=allow）。 |
| Q4 重写命令/skill | ✅ 完全对 | rewrite = **重打包**，prompt 文本照收；别回收 `.claude`/`~/.claude` 里的路径与 issue 号。 |
| Q5 hash 默认开+降级话术 | ✅ 对且最重要 | 本地 advisory、CI 强制；无 CI 的仓留逃生口。 |
| Q6 私有/git 先行 | ✅ 对 | marketplace 从路线图**删除**，而非「延后」。 |
| Q7 7 动词 + schema 冻结 | ❌ 范围失控 | 7 动词是产品面不是 MVP。v1=**`init` + `check`**；schema 冻结推迟到第二仓之后。 |
| Q8 init + 可选注册 required check | ⚠️ 半对 | 保 caller workflow + 诚实文档；**砍自动注册**（拖入 471 LOC GitHub-API 专用、最不可移植的模块）。 |
| Q9 策略住仓 + upgrade | ✅ 前对后砍 | `upgrade --check` 是给「尚未发布的 schema」写迁移器，YAGNI，砍。 |
| Q10 init 幂等/只增/uninit | ✅ 最佳项 | 补：init 写 `.witnessloop/init-manifest.json` 自己的账本；必须 `--dry-run`。 |
| Q11 证据分档 | ❌ 只剩一档 | 实际只有「hash 绑定 manifest」一档；为唯一非空档造「分档机制」=给空档写代码。**单档 + 文档**即可。 |
| Q12 事件日志唯一真相 | ⚠️ 一半对 | plugin 无状态=对；但 asterwynd 本就**四源并存**。应定 **manifest = 每 change 每阶段权威证据**。 |

**必须（MVP 内）**：Q4 重写收文本 · Q5 hash 默认开+诚实锚 · Q10 init 幂等/只增/`init-manifest`/dry-run/uninit · Q3 不变集（仅自保护，封顶） · Q12 manifest 为权威、plugin 无状态 · Q2 的务实一半（repo-agnostic 参数化 + OpenSpec 契约硬编码） · Q6 git 分发。

**可以砍（延后/删除）**：Q1 签名与密钥对 · 事件日志 projection/replay/状态机（~1000 LOC） · Q2 的 spec 适配器接口 · Q7 的 5 个动词与 schema 冻结 · Q8 的自动注册/platform-gate · Q9 的 upgrade · Q11 的分档机制 · 多 host 适配器（只留 CC） · marketplace。

**MVP 最小可行范围**：**在第二个真实仓库里，用机械门禁把「设计与实现的证据」绑进 CI required check。**
交付单二进制（uv）+ 2 动词（`init` / `check`）；`init` 幂等/只增/`--dry-run`/不 auto-commit/写 `.witnessloop/`；`check` fail-closed；CC plugin 两条命令 `grill`/`review-loop`（重写、只读、无状态）。

**结论**：报告**方向**（证据绑定 + 机械门禁 + 锚在 CI）成立，Q4/Q5/Q10 对；但 **Q1/Q7/Q11 过度设计**，Q2/Q8/Q9/Q12 各有过半需砍。照报告全做会拖到「永远做不完」；砍到两条动词后，第一版两周内可在第二仓跑通 acid test。

---

## 采纳结论

对抗验证后，主 session 与用户据此**下调了 grill 的 Q1/Q5/Q7/Q11 方案**（见 [`grill-design.md`](grill-design.md) `## User Confirmation`）：不造签名、不造分档、不保事件日志 replay、MVP 砍到 2 动词。grill 的**核心命题**（防漂移 ≠ 防伪造）被完整采纳并写进 `docs/design.md` §2 / §5.3 / §9。
