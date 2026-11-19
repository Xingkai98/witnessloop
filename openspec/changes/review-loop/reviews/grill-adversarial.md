# Grill-Adversarial: review-loop 设计对抗验证

> 独立零记忆审阅者，默认 design 里的关键结论有错，逐条证伪。以下所有结论均以
> **当前工作树**代码与文档为准；能实测/复现的均已实测，无法验证的显式标注「未能验证」。

## 结论摘要

- **是否存在 medium+：否（0 个 medium+，无 blocker/high）。**
- 开批时的两个 medium（M1 `.reviewloop/` 复跑残留、M2 无 `where` finding 被丢弃）已由
  作者修复并经我逐条复核为**已修复**（见文末「五、修复复核（2026-11-19）」）。
- 剩余未修项均为 **low/nit**（L4 D2 措辞、L5 verdict 字段被忽略、L6 spec 配置段措辞、
  N1 未知模型无 warning），不构成 medium+，登记不修须写理由。
- 审查期间作者累计修复的项目（auth 单点化 / parse→BLOCKED / report.md 归属 / mock 冒充 /
  degraded_note / 预算前移 / M1 / M2 / 输入校验退出码 / report.py 加固）均已逐条复核，
  未发现新的 medium+。

---

## 一、已复核的修复项（作者在审阅期间提交，逐条验证）

| # | 作者声明 | 我的复核 | 结论 |
|---|---|---|---|
| 1 | `adapters.resolve_auth_token` 单点化，预检/回落判定/`build_adapter` 共用一条链 | `adapters.py:resolve_auth_token` 与 `build_adapter` 同源；`orchestrator._resolve_auth_token` 委托 `A.resolve_auth_token` | ✅ 一致 |
| 2 | 输出解析失败标记 `error_kind="parse"`，回落仍失败 ⇒ 整轮 `BLOCKED`，空 findings 不再判 PASS | `adapters.py` Claude/Codex 两处 `error_kind="parse" if err else None`；`orchestrator.py:374-383` 收集 `reviewer_errors` 并 `verdict="BLOCKED"` | ✅ 一致，且有测试 |
| 3 | `report.md` 由 `review report --out` 生成，`review run` 只写 `summary.json` | `design.md D1` / `spec.md` 已澄清；`REVIEW_REPORT_FILENAME` 未在 run 路径使用 | ✅ 一致 |
| 4 | 隐式回落 key 缺失 ⇒ `error_kind=auth` + `_NO_FALLBACK_ERROR`，round 级 `BLOCKED`，不跑 mock | `orchestrator.py:202-216`（`_NO_FALLBACK_ERROR`）、`:244-251`（early）、`:260-266`（runtime） | ✅ 一致；实测无 key 复现 `verdict=BLOCKED`，exit 1 |
| 5 | `degraded_note` 渲染进 markdown；mock 降级措辞不再误称「同源双审」 | `report.py:156-157` 渲染；`orchestrator.py:590-596` 区分「mock 降级 / 同源双审」 | ✅ 一致，有测试 |
| 6 | 预算检查前移到 judge/fixer 之前 | `orchestrator.py:393-401` 顺序为 reviewer_errors → PASS → budget → stalled → fixer | ✅ 一致（stall 不再越过预算） |

另：`design.md D9#6` 已如实标注「两路同一 actor」负样本是**产物级篡改检查**、非真实独立
run 的证明（`run_id` 带角色前缀，两路结构性不同）。该标注属实，不列为问题。

---

## 二、逐项证伪结论（D1–D10 与 Requirements）

### D1 子命令与产物边界 —— ✅ 成立
`review run` / `review report` 产物根 `.reviewloop/`、`config.resolved.json` /
`rounds/round-<n>.json` / `summary.json` 与实现一致；`report.md` 归属已澄清（见修复项 3）。
`.gitignore:8` 确含 `.reviewloop/`。
**唯一下游问题**：`.reviewloop/` 生命周期无隔离（见 M1）。

### D2 revision 锚点 —— ⚠️ 一处陈述不实（low L4）
`digest` 排除 `.git` 与 `.reviewloop/`、git 无提交退回 digest 均实测成立
（`revision.py:77-99`）。但「**校验该 sha 是本仓提交**」**未被实现**：`review run` 无任何
显式 sha 入参，唯一 git 值来自 `rev_parse(root, "HEAD")`（`revision.py:90`），而
`Revision.is_ancestor`（`revision.py:40`）**在 review 环里没有任何调用方**。结论：该「校验」
是空陈述，建议删去或补一条「digest/git 值只取自 HEAD，无需额外校验」的如实说明。

### D3 roles@v1 整块替换 —— ✅ 成立
`load_roles` 的 `merged["roles"].update(roles)`（`roles.py`）确实是**角色级整块替换**：
只写 `model` 会丢该角色默认 `adapter/base_url/auth_env`，与 D3 描述、spec「未写字段不从默认
逐字段补」一致；语法坏抛 `ValueError` 不静默；auth 只记 `auth_resolved`。全部有测试钉住。

### D4 adapters —— ✅ 成立
claude `/v1/messages` 拼接、codex `/chat/completions` 拼接、mock 确定性、错误归一、JSON
解析与 `parse` 失败标记均与代码一致。`base_url` 拼接对齐已有回归测试
（`test_default_base_urls_match_adapter_splicing`）。

### D5 编排器收敛/停滞/预算 —— ✅ 成立（一处 nit）
- 并发、只按 `where` 去重取高 severity、`medium_plus_zero` 判据、停滞升级、成本止损顺序
  均与代码一致；预算已前移到 judge/fixer 之前（修复项 6）。
- 停滞检测 `_stalled_findings`（`orchestrator.py`）对「连续 `stall_rounds` 轮」的语义正确
  （`reversed(history)` + `break`，非连续不算）。
- **nit**：预算是事后软止损（代码注释已自认），fixer/judge 成本在当轮不参与预算判定，
  只进 `cumulative_cost_usd` 由下一轮检查。可接受，不列为必须修复。

### D6 回落规则 —— ✅ 成立（已修复后）
见修复项 1/4。当前行为：auth 缺失/通路 auth·balance·model_not_found·parse ⇒ 回落
deepseek-flash；连 deepseek key 也没有 ⇒ **拒绝 mock、该 reviewer 记 `error_kind=auth`、
整轮 `BLOCKED`**；显式 `--adapter mock` 烟测路径不受影响。与 `design.md D6` / `spec.md`
「通路失败」Requirement 现已对齐。

### D7 报告四条负样本 —— ⚠️ 三条成立、第 4 条机制不可用（medium M2）
- 负样本 1/2/3（篡改 manifest / 证据缺件 / 两路同一 actor）机械正确、有测试。
- 负样本 4（正控漏报）**机制不可用**：`report.py:108` 用 `str(f.get("where")) == positive`
  **逐字相等**。真模型 `where` 措辞不定（T-075 §6 明言「模型措辞不定 ⇒ 易误报」，并
  **弃用** `--positive-control` 改人工核对）。design/spec 未把这条限制写进 D7/D9。

### D8 成本模型 —— ✅ 成立（一处 low）
公式、近似价、默认 $30、未知模型 `(0,0)` 均与代码一致；`gpt-6.1-sol` 已进表并有回归测试。
**low**：未知模型价 `(0,0)` 时**没有任何运行期 warning**，预算止损失效无诊断
（`roles.resolve_config` 的 warnings 只覆盖 auth）。design 已写「必须同步加表」，但无强制。

### D9 已知限制 —— ✅ 成立
judge 上下文不足 / fixer 不改码 / `.reviewloop/` 非门禁证据 / roles 仓根全局 / 成本非计费 /
不防伪造 —— 全部如实。judge 上下文不足的后果（两次 `uncertain ⇒ BLOCKED`）有 T-075 实测。

### D10 验收与证据 —— ⚠️ 数字口径漂移（low L3）
单测全绿属实（实测 `838 passed`），但 D10 写「共 44 条新增」、proposal 写「788+44+1」、
merge-report §6 写「832/834」——与当前 `838` 及各文件实际测试数均不一致
（revision 11 / roles 8 / adapters 14 / orchestrator 9 / report 6）。「全绿」成立，但精确数
需同步。

### Requirement 覆盖核对
- 「review run SHALL 组织双路闭环」「每轮 manifest SHALL 绑定角色与配置」「通路失败 SHALL
  机械回落」「report SHALL 跑四条负样本」「roles@v1 SHALL 四角色独立配置」「成本估算 SHALL
  对已知模型生效」「`.reviewloop/` SHALL NOT 当门禁证据」——除下述 M1/M2/L2 外均与实现一致。
- 「review report 配置段 SHALL 显示实际模型」（`spec.md:84`）**措辞与实现不符**：配置段
  渲染的是 `config.resolved.json` 的**配置意图**（`report.py:129-149`），实际模型（含
  `degraded_from`）只出现在「各轮」actors 段。应改措辞为「报告 SHALL 显示实际模型」。

---

## 三、详细 findings（按 severity 排序）

### M1（medium，✅ 已修复）`.reviewloop/` 无隔离/重置 —— 复跑残留旧 rounds，误报「篡改 manifest」

- **位置**：`src/witnessloop/review/orchestrator.py:329`（`roles_mod.write_config` 覆写）、
  `:439`（`_write_round_manifest` 覆写 round-<n>）；`src/witnessloop/review/roles.py:164`
  （`write_config` 只 `mkdir` 不清理）；`src/witnessloop/review/report.py:34-49`（glob 全部
  `round-*.json`）。
- **反例（已复现）**：同仓先跑 `review run --adapter mock --mock-scenario '{"1":[medium],"2":[]}'`
  （2 轮），再跑 `review run --adapter mock --mock-scenario '{"1":[]}' --positive-control src/x.py:999`
  （1 轮）。第二次 run **不清空** `.reviewloop/`，`round-0002.json` 残留；随后
  `review report` 输出：
  ```
  1. 篡改 manifest：round 2 的 config_hash 与 config.resolved.json 不符
  ```
  这不是篡改，是工具自身复跑造成的前后配置不一致。
- **后果**：证据目录可被污染；「篡改 manifest」这一 fail-closed 红被工具自己的生命周期
  触发，误导操作者去怀疑篡改。proposal 只说「可随时删除重跑」，但 CLI 不删除、不警告、
  不区分「旧 run 残留」与「被篡改」。
- **建议修法**（三选一）：
  1. `review run` 开始时清空 `.reviewloop/`（或对非空目录 `EXIT_USAGE` 要求先删）；
  2. 或在 `review report` 里把「config_hash 与当前 config 不符」细分为「残留旧 run」与
     「篡改」两类提示；
  3. 至少在任何一次覆盖写前打印 stderr 警告「`.reviewloop/` 非空，将覆盖」。

### M2（medium，✅ 已修复）正控漏报（负样本 #4）依赖 `where` 逐字相等，真模型下不可用；无 `where` finding 被静默丢弃

- **位置**：`src/witnessloop/review/report.py:95-113`（`str(f.get("where")) == positive` 精确匹配）；
  `src/witnessloop/review/orchestrator.py:117-138`（`_merge_findings` 对 `where` 为空的 finding
  `continue` 丢弃）；`orchestrator.py:327-328`（`--positive-control` 写死 `where` 串）。
- **反例**：T-075 §6 已实测并明言「`--positive-control` 要求 `where` 与 reviewer 输出**逐字
  相同**，模型措辞不定 ⇒ 易误报」，因此真模型正控**弃用该机制改人工核对 finding**。
  同一根因下：reviewer 若输出一条真实 blocker 但漏写/改写 `where`（模型常见），
  `_merge_findings` 会**静默丢弃**它，merged 为空 ⇒ `PASS` —— 真实问题被丢成假绿。
- **后果**：spec 声明的「review report SHALL 判正控漏报」机械上成立，但**真实运行下
  不可用**；且整个收敛/去重/停滞/正控信号全部押在「模型输出稳定且逐字一致的 `where`」上，
  这是单点脆弱。
- **建议修法**：
  1. 正控匹配改为**归一化**（去空白、统一 `文件:行号` 形态、允许前缀/包含匹配），
     并在 design 记录该口径；
  2. 无 `where` 的 medium+ finding **不得静默丢弃**：要么记入 manifest 的 `raw`/`note`
     并让该轮 `CHANGES_REQUESTED`，要么至少打印 warning；
  3. 若保留现状，须在 design D7/D9 如实标注「正控漏报仅对 `where` 逐字一致成立，真模型
     建议人工核对」。

### L3（low）`--pass-rule` / `--mock-scenario` 非法输入 → 「内部错误（ValueError）」exit 1，非 EXIT_USAGE(2)

- **位置**：`src/witnessloop/review/orchestrator.py:144-147`（`_pass_rule_satisfied` 抛
  `ValueError`）、`:94-113`（`_parse_mock_scenario` 抛 `ValueError`）；两处调用均不在
  `try/except` 内（`:334`、`:380`）。
- **反例（已复现）**：
  ```
  $ witnessloop review run --change x --pass-rule bogus --adapter mock
  witnessloop：内部错误（ValueError: 未知 pass_rule：'bogus'）   # exit=1
  $ witnessloop review run --change x --adapter mock --mock-scenario 'notjson'
  witnessloop：内部错误（ValueError: --mock-scenario 不是合法 JSON：…）  # exit=1
  ```
- **后果**：用户输入错误被当作「内部错误」并以 exit 1（=失败）呈现，与 argparse 的用法错误
  语义（exit 2）不一致，误导排查方向。
- **建议修法**：`_pass_rule_satisfied` / `_parse_mock_scenario` 的 `ValueError` 在 `run()` 内
  捕获并返回 `C.EXIT_USAGE`（或给 `--pass-rule` 加 `choices` 限制）。

### L4（low）D2「校验该 sha 是本仓提交」未实现

- 见第二节 D2。建议删去该半句或在 `revision.py` 如实说明「git 锚只取 HEAD，无外部 sha 入参」。

### L5（low）reviewer 自报的 `verdict` 字段被忽略

- **位置**：`src/witnessloop/review/orchestrator.py:379-383`（verdict 只由
  `_pass_rule_satisfied(merged)` 计算，不读 `ReviewResult.verdict`）。
- **反例**：reviewer 输出 `{"verdict":"CHANGES_REQUESTED","findings":[]}`（或 findings 全部无
  `where`）⇒ merged 空 ⇒ `PASS`。模型自报「需改」被丢弃。
- **后果**：收敛判据只信结构化 findings，模型自己的裁决信号完全被忽略（设计 D5 确实如此
  定义，但后果未标注）。属低危，因正常契约下 verdict 与 findings 一致。
- **建议修法**：design 注明「verdict 字段仅作提示、不参与判定」；或对
  `verdict != PASS 且 findings 为空` 的轮记 warning。

### L6（low）spec「配置段 SHALL 显示实际模型」措辞与实现不符

- **位置**：`spec.md:84` vs `report.py:129-149`（配置段渲染 `config["roles"]` 的配置意图）。
- **建议修法**：spec 改为「报告 SHALL 显示实际模型（`各轮` actors 段含 `degraded_from`）」。

### N1（nit）未知模型价格 `(0,0)` 无运行期 warning

- **位置**：`adapters.py:cost_usd`（未知模型返回 0）；`roles.resolve_config` warnings 只覆盖 auth。
- **建议修法**：`resolve_config` 对 `model` 不在 `APPROX_PRICE_PER_MTOK` 的角色加一条
  warning「预算止损将失效」。

---

## 四、最终结论

- **medium+ 问题数：0（无 blocker / high / medium）。**
- 开批时的 M1、M2 已由作者修复，复核通过（见下节）；原 low 项 L3（非法输入退出码）也已在
  代码里修复（实测 `--pass-rule bogus` 与 `--mock-scenario 'notjson'` 均 exit 2）。
- 剩余未修项为 **low/nit**：L4（D2「校验 sha 是本仓提交」空陈述，`design.md:39`）、
  L5（reviewer 自报 `verdict` 字段被忽略，`orchestrator.py:403-406`）、L6（spec「配置段
  显示实际模型」措辞，`spec.md:97`）、N1（未知模型价格 `(0,0)` 无 warning）。这些不构成
  medium+，不阻塞收口。
- 结论：**本 change 的设计结论经证伪后成立，medium+ 为零。**

---

## 五、修复复核（2026-11-19）

逐条复核作者声明的修复（均以当前工作树代码为准）：

| 原 finding | 修复内容 | 证据（文件:行号 / 测试名） | 复核结论 |
|---|---|---|---|
| **M1** | `review run` 开始时 `_reset_rounds(root)` 清掉上次 run 的 `rounds/round-*.json` 与 `summary.json` | `orchestrator.py:333`（调用）、`:586-604`（`_reset_rounds` 定义）；`tests/test_review_orchestrator.py::test_rerun_clears_stale_rounds` | ✅ 已修复 |
| **M2** | `_merge_findings` 对无 `where` 的 finding 用合成键 `<missing-where>:batch{i}:item{j}` 保留，参与收敛判定、出现在报告里 | `orchestrator.py:128-135`（合成 `where`）；`tests/test_review_adapters.py::test_merge_findings_keeps_findings_without_where`、`tests/test_review_orchestrator.py::test_missing_where_does_not_converge` | ✅ 已修复 |
| M2 的「`--positive-control` 逐字匹配」 | 未改模糊匹配，改为**如实登记限制**：`design.md D9.7`（`design.md:166-167`）与 `spec.md` 已写明「真模型措辞不定、T-075 因此弃用该机制」 | `design.md:133-135`、`:166-167` | ✅ 已登记（不算未修复项） |
| **H1**（ANTHROPIC_* 跨端点复用） | `resolve_auth_token` 默认**不**再尝试 `ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_API_KEY`，只有角色显式 `allow_host_auth_fallback: true` 才兜底；回落目标 `FALLBACK_ROLE` 打开该开关 | `adapters.py:283-304`（开关逻辑）、`orchestrator.py:195-205`（`FALLBACK_ROLE.allow_host_auth_fallback=True`） | ✅ 已修复 |
| roles `_auth_resolved` 第二套解析 | 委托 `adapters.resolve_auth_token`，与预检/构造适配器同口径 | `roles.py:95-101`；`tests/test_review_roles.py::test_auth_resolved_matches_adapter_resolution` | ✅ 已修复 |
| report.py 加固（config 非对象 / round 非整数） | `verify` 对 config「缺失/不可解析/非对象」统一判证据缺件；`_read_rounds` 拒绝 `round` 非整数 | `report.py:60-65`、`:44-48`；`tests/test_review_report.py::test_non_object_config_is_red` / `::test_non_integer_round_is_red` | ✅ 已修复 |
| （附）L3 非法输入退出码 | `--pass-rule` / `--mock-scenario` 非法输入 → 干净报错并 `EXIT_USAGE(2)`（实测 exit 2） | `orchestrator.py:150`、`:321`（pass-rule）、`:325-329`（mock-scenario try/except） | ✅ 已修复 |

**剩余风险（均为 low/nit，不阻塞）**：

- **L4**（low）：`design.md:39`「校验该 sha 是本仓提交」仍是空陈述——`review run` 无外部
  sha 入参，`Revision.is_ancestor` 无调用方。建议删去该半句。
- **L5**（low）：`orchestrator.py:403-406` verdict 只由 `_pass_rule_satisfied(merged)`
  计算，reviewer 自报的 `verdict` 字段被忽略（设计如此，后果未标注）。
- **L6**（low）：`spec.md:97`「配置段 SHALL 显示实际模型」与 `report.py` 实现不符——实际
  模型（含 `degraded_from`）在「各轮」actors 段，配置段显示的是配置意图。
- **N1**（nit）：未知模型价格 `(0,0)` 无运行期 warning，预算止损失效无诊断。

以上四项登记不修须写理由；均不构成 medium+，不影响「medium+ 为零」的结论。
