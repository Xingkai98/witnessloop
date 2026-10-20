# Tasks: gate-ref-annotated-tag

> 依据 `design.md`。原则：**TDD**（先让回归在旧实现上红，再改解析器）。
> 流程：立项 → 独立零记忆 grill → 独立零记忆对抗验证（跑到收敛）→ 停轮门 → TDD →
> 独立审阅到收敛 → 三份 manifest → `gate / check` 绿 → PR `--merge` → v1.7.1 → 回钉验证 → 关 issue。

## A. 立项

- [x] A1 `proposal.md`：issue #42 的现象 / 根因 / uv 版本分界 / 目标 / 非目标 / 验收。
- [x] A2 `design.md`：D1 解析优先级、D2 fail-closed、D3 守卫、D4 日志、D5 回归测试、
      D6 自举与发版、D7 文档。
- [x] A3 `specs/gate-ref-pinning/spec.md`：能力增量（新优先级 + annotated tag 场景 + 回归测试要求）。
- [x] A4 uv 实测：tag object sha 在 **0.13.2 / 0.13.3** 失败、**0.12.1 / 0.13.1** 成功；
      `refs/tags/v1.7.0` / `v1.7.0` / `refs/heads/main` / commit 在 0.13.3 均成功。
      原始输出见 design §1。**版本分界 = 0.13.2**（不是 0.13.3）。

## B. 设计阶段（grill + 对抗验证）

- [x] B1 独立零记忆 grill：`reviews/grill-design.md`（模板结构：Confirmed Decisions ≥3 且带 `来源:`、
      Code-Resolved、Open Questions、风险、User Confirmation）。
- [x] B2 独立零记忆对抗验证：`reviews/grill-adversarial.md`，逐条证伪 D1..D7；跑到无 medium+ 收口。
      **结果：R1（R1-1/R1-2）→ R2（R2-1）→ 第 3 轮空批 ⇒ `PASS`。**
- [x] B3 停轮门：只把真正需要用户拍板的问题留下；能由代码 / 实测 / 既有语义定案的自己定案。
- [x] B4 回写 `design.md §4 Pre-Implementation Review`。

## C. TDD：回归测试先红

- [x] C1 新增核心行为用例：annotated tag（`WL_WORKFLOW_SHA`=tag object、`WL_WORKFLOW_REF=…@refs/tags/v1.7.0`）
      ⇒ 解析结果 = `refs/tags/v1.7.0`，不是 tag object sha。
- [x] C2 新增/改写：分支 pin（结果 = sha，**不是** `refs/heads/*`）、commit pin
      （真实形态 `@<40 位小写 hex>`）、workflow_sha 兜底（warning 含原值）、
      sha 空时的 workflow_ref 降级、双重不可用 fail-closed、**空兜底 ref / 纯空白输入非零退出**、
      `refs/tags/` / `refs/heads/` 空尾、分支名含 `@`、tag 名含 `@`、
      **ref 名里含 `@refs/heads/` / `@refs/tags/`**、**workflow 路径不匹配已知前缀**
      （改名）⇒ 响亮兜底、64 位 hex、大写 hex。
- [x] C3 **证明旧实现会红**：先写测试、在旧 `gate.yml` 上跑 ⇒ **13 条失败**（当时测试集；
      最终测试集下复跑为 **17 failed / 31 passed**，其中 2 条是兜底常量 `v1.7.0→v1.7.1` 的
      预期漂移）；核心用例输出 `ref=00192abe45d2d72a4389eccb202faad48c34fa26`（tag object）；再改实现。
- [x] C4 保留既有语义用例（显式覆盖 / 跨仓 / GHES / 畸形 / 未定义 env / 输出非空 / 常量同源 /
      step 顺序 / 安装步吃输出 / input 默认空串）全绿；`test_resolve_prefers_the_reusable_workflows_own_sha`
      在混合优先级下仍成立（保持）；`test_resolve_falls_back_to_the_ref_part_of_job_workflow_ref`
      改写为完整 namespaced ref；`:59` 的 `v1.7.0` → `v1.7.1`。

## D. 实现

- [x] D1 `gate.yml` 解析 step：按 design D1/D2 重写分支；`WHY` 文案按 D4；repository 守卫原样。
- [x] D2 `gate.yml` 头部注释与 input 描述更新（annotated tag 受支持）。
- [x] D3 `constants.DEFAULT_GATE_REF` → `v1.7.1`（`WL_FALLBACK_REF` 同步）；相关测试断言同步。
- [x] D4 `docs/gate.md §1.2 / §7.1`、`README.md`、`docs/design.md` 相关句子同步新语义。
- [x] D5 `uv run pytest -q` 全绿：**768 passed**（2026-10-20，含 GITHUB_OUTPUT 守卫回归后的最终计数）。

## E. 实现后独立审阅

- [ ] E1 独立零记忆 building 审阅：逐条验证 `[x]`、跑测试、读 diff；产出 `reviews/building-review.md`。
- [ ] E2 `CHANGES_REQUESTED` ⇒ 开批 → 全修（每条补回归）→ 只做修复验证 → 收口；直到 `PASS`。

## F. 证据 / 门禁 / 合入

- [ ] F1 本仓 caller 临时钉 commit `98b97b7046e98508470345ce081f7189c6c4269c`
      （**40 位全 sha**；短 sha 会被 GitHub `uses:` 拒绝——对抗轮 R1-1）：用
      `witnessloop init --gate-ref …@98b97b7046e98508470345ce081f7189c6c4269c --policy .witnessloop/policy.json`
      （不带 `--policy` 在定制 policy 仓会 exit 1——grill 实测）；同步台账 +
      **一条** `protected_path_write` 事件（本 PR 新建 events 文件 = `A`，自身免事件）。
      验收：caller 的 `uses:` 是 40 位小写 hex，且修复 PR 的 `gate / check` 真的由它触发。
- [ ] F2 三份 manifest：`grill` / `grill-adversarial` / `building`，绑定最终 revision。
- [ ] F3 `witnessloop check --base origin/main --head HEAD` 绿（记录原始输出）。
- [ ] F4 PR，正文引用 issue #42；**`--merge` 合入**。授权来源：用户 2026-10-20 任务书
      「合入一律 `--merge`」。

## G. 发版与自举验证

- [ ] G1 在合并提交上打 **annotated `v1.7.1`**（不动 `v1` / `v1.7.0`）。合入后**立即**打
      tag；窗口内不要接入 / 升级（`DEFAULT_GATE_REF` 已指向尚未存在的 tag）。
      GitHub Release 正文 SHALL 写明这个窗口与「钉 annotated tag 受支持」。
- [ ] G2 另起 PR：caller 回钉 `@v1.7.1`（同样 `init --gate-ref …@v1.7.1 --policy …`）；
      ⚠️ caller 是非证据路径 ⇒ 旧 manifest 会 stale：在内容提交后**重建三份 manifest**，
      并补 **5 条**事件（台账 + 3 份 manifest + events 文件自身）。该 PR 的 `gate / check`
      由 **v1.7.1 的新 `gate.yml`** 判定 ⇒ 真实 CI 验证 annotated tag 形态
      （记录 `::notice::` 里「来源：job.workflow_ref 的 tag ref」那一行）。
- [ ] G3 issue #42 写完成说明并关闭。

## 审阅修复

### 设计对抗（grill-adversarial）

| 问题 | 处置 | 落点 / 回归 |
|---|---|---|
| R1-1（high）迁移命令短 sha | 改成 40 位全 sha；F1 加 caller `uses:` 验收 | `design.md` D6 / `tasks.md` F1；对抗审阅者临时仓实跑复核 |
| R1-2（medium）grill 报告 `Q1/Q2` 机械红 | `## Open Questions` 逐字改为「（无）」；Q1/Q2 留在 Code-Resolved | `reviews/grill-design.md`；`evidence.grill_evidence_findings` → `[]` |
| R1-L1..L9 | commit-pin 改已验证、proposal 收窄、稳健解析、spec 措辞、D5 测试处置、F4 授权来源、窗口 | 见 design §4 / 上述各文件 |
| R2-1（medium）ref 名含另一命名空间被截错 | 改为**已知前缀精确剥离** `<REPO_SLUG>/.github/workflows/gate.yml@`；路径不匹配 ⇒ 响亮兜底 | `gate.yml` 解析 step；新增三例 + 普通 `@` + 路径不匹配测试 |
| R2-L1..L9 | D4「降级」、commit-pin 已验证、§4 旧测试措辞、tag 名 `@` 测试、Release 窗口、安装步注释、B2 状态 | 见 design §4 / `gate.yml` 注释 / `tests/test_gate_workflow.py` |

### 流程偏差（R2-L6，如实记录）

实现（`gate.yml` / `constants.py` / tests / docs）在设计对抗**第 2 轮验证期间**开始并跑绿，
未严格等到设计环 `PASS`。处置：**未在 PASS 前产出任何证据 manifest、未合入、未发版**；
R2-1 的设计缺陷正是由该轮对抗先发现并修复。此处如实登记为流程偏差，**不伪造用户授权**。

## 验收清单

- [ ] V1 annotated tag 形态：解析出 tag ref（不是 tag object sha）；旧实现在 C1 上红。
- [ ] V2 旧语义逐条保留（显式 / 守卫 / fail-closed / 日志来源 / 输出非空）。
- [ ] V3 uv 0.13.3 实测原始输出入报告（tag object 红、tag ref 绿）。
- [ ] V4 文档 / 规格 / 注释同步；不再出现「uv 能解析 tag object sha」的旧结论。
- [ ] V5 `uv run pytest -q` 全绿；三份 manifest；`check` 绿。
- [ ] V6 PR `--merge`；v1.7.1 已发（annotated）；本仓 caller 回钉后的 gate 绿；#42 已关。
