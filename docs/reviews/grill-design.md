# grill 报告：witnessloop 设计追问

> 独立零记忆审阅者产出（2026-10-09）。READ-ONLY：未修改 witnessloop 任何文件、未动 git。
> 依据：`docs/design.md` v0.1、`README.md`、asterwynd 最新 master 参考树 `.paseo/worktrees/0frj3kg8/dev-workflow-toolkit` 实读（`scripts/workflow_guard.py`、`check_openspec_artifacts.py`、`platform_gate.py`、`agent/workflow/{event_log,models,state_machine,review_manifest}.py`、`.github/workflows/ci.yml`、`flow-policy.json`、`platform-gate.json`、一个归档 change 的产物）。

## 0. 关键事实订正（影响 Q1/Q5/Q11 的立论）

1. **`awaiting` 没有退役**。退役的是四阶段状态机的**投影产物入库**（`.gitignore`：`openspec/changes/*/handoff.json`、`workflow-state.json` 不再提交）。`awaiting` 本身活着：建模为 `blocked.awaiting_*`（`event_log.py:51-54`：`awaiting_proposal_confirmation` / `awaiting_human_review` / `awaiting_user_confirmation`），由 `workflow-events.jsonl` replay 判定（`is_awaiting_state`），guard 据此**拦截写代码**（`workflow_guard.py:_awaiting_block_reason`）。design §8-Q1 的前提（"状态机已退役，需重新论证"）把两件事混为一谈。真问题不是"要不要 awaiting"，而是"要不要给每个 change 保留一份**事件溯源、可 replay 的状态日志**"。
2. **所有门禁输入都是本地文本文件，且当前全部可自证**：
   - 受保护路径放行 = `workflow-events.jsonl` 里存在一行 `event_type`/`change_id`/`artifact_path` 对得上、且 `reason`/`approved_by` 非空的事件（`_validate_protected_artifact_event`）。`approved_by` 是自由文本，**无签名、无外部锚**。agent 手写一行提交即可过 CI。
   - review manifest 的 `reviewer_run_id` 是**自由字符串**，全仓无任何地方校验它对应一个真实、独立的 run。
   - `diff_hash` 明确是**参考性**的：`_verify_git_span` 在 shallow clone / rebase 后 base/head sha 不存在时**静默跳过**（`review_manifest.py:231-232`）。真正"权威"的是 tasks/spec/report 的**内容 hash**——但它只证明"这几个文件互相没漂移"，不证明"审阅真的发生过"。
3. 结论：现状的"机械门禁"是**防漂移（tamper-evidence）**，不是**防伪造（authenticity）**。design 的核心卖点"把可信变成机械可验证"目前被夸大——这是最大的"做虚"风险。

## 1. Confirmed Decisions

1. **两层架构**（门禁层 host-agnostic CLI + 交互层 host 中立模板）——强制必须落在 agent 之外。
2. **Python + uv、独立新仓、零 asterwynd import**——第二仓 acid test 是"可复用"的唯一证明。
3. **强制落 CI required check，hooks 只作提醒**——hook 可关、本地、可绕；required check 是唯一绕不过的点。
4. **数据契约以 change 目录为核心，证据 = 报告 + manifest 成对**——`report_hash` 钉死结论文件。
5. **manifest 必填字段集**（`reviewer_run_id` / `base_sha` / `head_sha` / `tasks_hash` / `spec_hash` / `diff_hash` / `report_hash`）——缺 `author_run_id`（见 §4）。
6. **受保护路径用声明式策略 + 多档 governance 表达**——分档是对抽象。

## 2. Open Questions（每条含 witnessloop 真实场景 + 推荐）

### Q1 — 是否保留 `awaiting` / 事件溯源状态日志？
**场景** change `add-retry-policy`：agent 写完 `design.md`，`reviews/grill-design.md` 里 Q1–Q3 标"待确认"。
- **不做 awaiting**：agent 自己把 `## User Confirmation` 段填成"Q1=是 Q2=是 Q3=是"（本就是它写的文本），guard 只看"Open Questions 是否都在该段出现"→ **放行写代码，用户从未拍板，门禁绿**。
- **做 awaiting**：进入 `blocked.awaiting_user_confirmation`，guard replay 判定后拒绝一切写代码；只有 `blocked_resolved` 解封。
- **但**解封事件同样是一行 JSONL——**谁能写、CI 怎么验"是人写的"**，现状无答案。awaiting 只是把自证从 prose 挪进 JSONL，**未增加信任**。

➡️ **推荐：保留，但重构为"事件日志 + 不可自签的解封"**（人类终端密钥签名，CI 验签）。

### Q2 — OpenSpec 依赖强度：强依赖 vs spec-agnostic？
**场景** 目标仓是 Go 服务仓（无 `openspec/`、无 node），跑 `init`。
➡️ **推荐：spec-agnostic 内核 + OpenSpec 可选适配器**（检测到 `openspec/` 才委派）。

### Q3 — 受保护路径 / 文档布局怎么通用化？
**场景** 目标仓没有 `docs/known-debt.md`、没有 `openspec/specs/`。
➡️ **推荐：守卫自身的输入设为不可移除的"不变集"**（policy、event log、manifest、change artifacts 目录），其余走 repo-local policy 数据。

### Q4 — 命令/skill 回收 vs 重写？
**场景** `grilling` 在 `~/.agents/skills/grilling`；`/grill`、`/review-loop` 在 gitignored `.claude/`。
➡️ **推荐：重写**。回收物不在版本控制、无 provenance、含私有约定；交互层要 host 中立。做法 = 抽 `grilling` 的**算法**成 host 中立模板，适配器只绑入口/参数。

### Q5 — 证据强度：manifest hash 默认还是可选？
**场景** 审阅 agent 写 `building-review.md`（PASS），`manifest build` 生成 manifest——**全部可由作者自己生成**。
➡️ **推荐：hash 默认开（防漂移），话术降级为"防漂移不防伪造"；信任锚在外部可取证事实**（独立复核 reviewer run、CI run id）。

### Q6 — CC plugin：marketplace vs 私有/git 分发？
➡️ **推荐：私有/git 分发先行，marketplace 延后**（早期命令面会变；自动更新=远端代码在你 agent 里执行）。

### Q7 — 门禁 CLI 命令面与配置 schema？
➡️ **推荐：收成一个 `witnessloop` 二进制 + 子命令** `init/check/gate/manifest/event/status/policy`；policy schema v1 四段：`protected_paths[]` / `required_artifacts[]` / `evidence{strength,anchor}` / `gates[]`。

### Q8（补充）— 怎么"真正落 CI required check"而不依赖目标仓 CI 配置？
**场景** fork 的人不跑 init，CI 无 witnessloop 步骤 → 门禁**静默为零**。
➡️ **推荐三层**：init 写极薄 caller workflow（reusable workflow，tag 钉版本）；可选 `platform-gate` 注册 required check；**诚实文档化** witnessloop 无法凭空产生 required check。

### Q9（补充）— 多仓复用时策略如何注入/升级？
➡️ **推荐：策略住目标仓**（可评审、受保护），engine 由 reusable workflow tag 钉；`policy upgrade --check` 打印差异与迁移建议。

### Q10（补充）— `init` 改了目标仓怎么回滚？
➡️ **推荐**：init **只增不改、幂等、不自动 commit**；写 `witnessloop-init.json`；`uninit` 精确删除并校验 hash 未变；`--dry-run`。

### Q11（补充）— 证据锚在什么上？可伪造吗？
**场景** agent 直改受保护 spec，手写一行 `{"event_type":"current_spec_synced",...,"approved_by":"user"}` 提交 → **门禁绿**。
➡️ **推荐：分档并诚实标注**：默认档=防误改（不防蓄意伪造）；推荐档=签名锚或外部事实锚。

### Q12（补充）— 交互层与门禁层如何共享 change 状态、不产生两套真相源？
➡️ **推荐：事件日志是唯一真相，投影只是缓存**；CLI 独占 `event append`/replay；plugin **只读**、**严禁**持有自己的状态文件。

## 3. Risks / 失败模式

1. **自证漏洞（最高危）**：门禁输入都是 agent 可写的本地文本。防漂移、不防伪造。
2. **抽取成本被系统性低估**：`check_openspec_artifacts.py` 单文件 **1802 行 / 72KB** 且重度专用；**通用化才是主工作量**。
3. **常量藏在 Python 而非 policy**：`BENCHMARK_SMOKE_CAPABILITIES` 等是代码里的 `set`。
4. **required-check 鸡生蛋**：不跑 init 就零强制且**无告警**。
5. **"独立审阅"剧场化**：`reviewer_run_id` 不校验 ⇒ 同一 run 既写又审也能过。
6. **双真相源漂移**。
7. **host 中立名义化**。
8. **供应链/自动更新**。
9. **路径语义**：Windows 反斜杠/大小写/`~` 是已知坑。

## 4. Suggested design revisions

- **§2 目标**：把"把可信变成机械可验证"改为**分档表述**。
- **§5.1 门禁层**：明确单一策略源位置、命令面收敛、`事件日志是唯一真相` 规则。
- **§5.2 交互层**：加硬约束——对 change 状态只读、不得持有自己的状态文件。
- **§5.3 数据契约**：manifest 补 `author_run_id`（强制 `reviewer≠author`）与可选 `anchor`；change 契约 spec-agnostic。
- **§6 抽取资产**：改写"5.3k LOC 可抽"，补"常量参数化是主工作量"。
- **§7 acid test**：补负例（手写放行事件 / 状态漂移 / 不跑 init / init→uninit）。
- **§8-Q1**：改为"是否保留事件溯源状态日志"。
- **§9 风险**：把"证据可自证/可伪造"提为第一条。

---

## User Confirmation

> 用户在对抗验证后逐项拍板（2026-10-09）。以下为最终决策，与 grill 原推荐有出入处已在括号内注明依据。

- **Q1（状态真相源）**：用户答复：**不保留事件日志 replay / 状态机**；改为 **manifest = 每 change 每阶段的权威证据**，事件日志降为可选历史（省 ~1000 LOC 残留）。依据：对抗验证 B 指出 asterwynd 本就有 manifest/events/state/handoff **四源并存**、事件日志从来不是唯一真相，且入口已删（近乎不可达）；少一个真相源少一类 bug。确认时间: 2026-10-09
- **Q2（spec 依赖）**：用户答复：**v1 硬编码 OpenSpec 形状的 change 契约**，只参数化 repo-agnostic 的轴（路径/策略）；**不造 spec 适配器**。依据：验收标准是"第二个**仓库**"而非"第二种 spec 系统"，为唯一实现造接口是过早抽象。确认时间: 2026-10-09
- **Q5 / Q11（信任锚 / 证据强度）**：用户答复：**v1 不造签名、不做分档机制**；靠**远端 branch protection + required check**（人手动开一次，该人肉操作即"人类签名"）+ 文档诚实写明"默认防漂移、不防伪造"。依据：单人开发下密钥与 agent 同机 = 零防御，且使用负担大。确认时间: 2026-10-09
- **Q7（命令面 / MVP 范围）**：用户答复：**MVP = 2 个动词**（`init` + `check`）+ `uninit` 回滚；**不做** gate/event/status/policy upgrade、不冻结 schema。依据：早期原型的死因是"永远做不完"，先证明"第二仓 PR 因缺证据被拦"成立。确认时间: 2026-10-09

**两道审阅一致、用户未反对的项**（照此定）：

- **Q4**：命令/skill **重写**（重打包 = prompt 文本照收，去私有路径/issue 号）。
- **Q6**：git/私有分发起步，**marketplace 从路线图删除**。
- **Q3**：不变集**封顶**（仅 policy/manifest 自保护，~5 条常量）。
- **Q9**：策略住目标仓；**砍掉 `policy upgrade`**（YAGNI）。
- **Q10**：init 幂等 / 只增不改 / `--dry-run` / 不 auto-commit / `uninit` 依 `init-manifest.json` 精确回滚。
- **Q8**：init 写极薄 caller workflow + 诚实文档；**砍掉 platform-gate 自动注册**（required check 由人手动开）。
- **Q12**：plugin 只读、无状态；manifest 为权威证据。
- 只做 CC，不做多 host（模板与适配器物理分离）。
