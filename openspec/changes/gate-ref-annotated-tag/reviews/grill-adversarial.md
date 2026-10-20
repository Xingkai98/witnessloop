# Grill 对抗验证: gate-ref-annotated-tag（第 1 轮 · 设计环）

## Reviewer

- run id: `grill-adversarial-reviewer-gate-ref-annotated-tag-98b97b7046e9`
  （`WITNESSLOOP_RUN_ID` / `WITNESSLOOP_REVIEWER_RUN_ID` 均未设置；按
  `templates/grill.md`「怎么取 run id」的确定性兜底，形态
  `<stage>-<role>-<change id>-<HEAD 前 12 位>`，HEAD = `98b97b7046e9`。）
- 时间: 2026-10-20T09:34:30Z
- 被审 revision: `98b97b7046e98508470345ce081f7189c6c4269c`（`HEAD` = `origin/main`；
  被审 change 目录为工作树内的 untracked 文件，未提交）
- 方法: 零记忆、只读。只使用仓内文本/代码、GitHub 真 CI 日志（run `38928669316`、
  跨仓探针 run `38853369550`、对照仓 `Xingkai98/asterwynd` 的 commit-pin run
  `39386712284`）、issue #42、本机 uv 0.12.1/0.13.1/0.13.2/0.13.3 实跑、一次性 `sh`
  解析器复现、仓内 `evidence.py` 实跑与 `pytest`。未读取作者会话历史或上一轮审阅结论。
- 判定口径: 默认被审设计有错，逐条证伪；**设计环的修复证据**只接受可复现反例 /
  改前失败改后通过的文档守卫 / 逐条决策记录。

## 本轮判定（verdict）

**第 1 轮：PASS（R1-1 / R1-2 均 2/2 已修好）。**
**第 2 轮：PASS（R2-1 已知前缀精确剥离，三例均验证通过）。**
**第 3 轮：PASS（0 条 medium+）。** 最终出口 **PASS**。low/nit 残余见累积登记表，不阻塞。

### 第 1 轮 · 批次

| id | severity | 锚点（文件:行） | 问题 |
|---|---|---|---|
| R1-1 | **high** | `openspec/changes/gate-ref-annotated-tag/design.md:170-171`、`tasks.md:53-54`、`reviews/grill-design.md:57` | F1 的迁移命令写成 `--gate-ref ...gate.yml@98b97b7`（**短 sha**；G2 用 `@v1.7.1` tag 名，不受此条影响）。`init` 不校验、逐字写进 caller（我在临时仓实跑复现：生成的 `uses: ...gate.yml@98b97b7`）。GitHub Actions 自 2021-02-15 起在 `uses:` 中拒绝缩写提交 SHA（官方 changelog 点名 action 引用；可复用 workflow 的官方语法页只写“a SHA”，未给短 sha 正例）。本仓唯一**已被真 CI 证明可绿**的 commit-pin 形态是 40 位全 sha：asterwynd 热修 caller 为 `@c9b281167ad20b63e4832ad9ab8510964a2adc60`，run `39386712284` / job `118508174549` 的 `gate / check` 成功。短 sha 一旦被 resolver 拒绝，reusable workflow 无法解析（0 job / workflow file issue），修复 PR 的 required `gate / check` **永远不会绿**，F1 的“临时钉 commit 让修复 PR 可绿”目标直接失败。设计自己的 prose（`design.md:166`）写的是**全** sha，命令却退化成短 sha——两者必须统一为 `98b97b7046e98508470345ce081f7189c6c4269c`，并在 F1 验收里钉住 caller 的 `uses:` 是 40 位小写 hex。 |
| R1-2 | **medium** | `openspec/changes/gate-ref-annotated-tag/reviews/grill-design.md:72`、`design.md:251-252`、`tasks.md:22-23` | grill 报告的 `## Open Questions` 正文写着“（无。Q1 / Q2 已按任务授权由作者……）”。`evidence.py` 的机械判据按 `\bQ(\d+)\b` 扫描**候选 Open Questions 小节正文**，因此抽出 Q1/Q2；`## User Confirmation` 里没有 `- **Q1**` / `- **Q2**` 行。我实跑 `evidence.grill_evidence_findings(...)` 得到 2 条 finding：`Open Question Q1 未经用户确认`、`Q2 未经用户确认`。`check` 对每个 target 都会跑这条正文判据（`checkcmd.py:182-187`），F2 的 `grill` manifest 一绑定该报告，修复 PR 的 `check` 必红；G2 回钉 PR 也会红。设计却把停轮门写成“无用户待拍板项”。⇒ 必须把 `## Open Questions` 正文改成真正无 Qn 记号（例如就写“（无）”；Q1/Q2 的讨论保留在 `## Code-Resolved Questions`），或在 `## User Confirmation` 记录**真实的**用户答复（当前不存在，不能伪造）；并在 F2 之前完成、重建 `grill` manifest。 |

### 第 1 轮 · 验证

| id | 结果 | 修复证据（设计环） | 回归测试 / 文档守卫 |
|---|---|---|---|
| R1-1 | **已修好** | `design.md:179-184` 的两条命令与 `tasks.md:56-58` 均为 40 位全 sha `98b97b7046e98508470345ce081f7189c6c4269c`；`design.md:186-188` / `tasks.md:61` 加了 F1 验收（caller `uses:` 必须 40 位小写 hex）。我在临时仓实跑 `init --gate-ref <full sha> --policy .witnessloop/policy.json`：`EXIT=0`，caller 为 `uses: …gate.yml@98b97b7046e98508470345ce081f7189c6c4269c`，台账 `gate_ref` 同值、caller 条目 sha256 与磁盘可复算一致。`--gate-ref` 迁移命令的短 sha 扫描只剩 `design.md:273` 的 R1-1 **历史描述**（按约定豁免），无实际命令再用短 sha。 | F1 验收 + 修复 PR 真实 CI 的 `Uses: …@98b97b70…` 行（待 PR 产生）；本轮已用 init 实际输出验证。 |
| R1-2 | **已修好** | `reviews/grill-design.md:72` 的 `## Open Questions` 已逐字改为「（无）」；Q1/Q2 只保留在 `## Code-Resolved Questions`。重跑 `evidence.grill_evidence_findings(...)` ⇒ `[]`；`## User Confirmation` 小节仍在（无 Qn 需确认）。 | 文档守卫：改前 2 条 finding → 改后 `[]`（本轮实跑，见下）。 |

### 第 1 轮 · 下一批（deferred）

（空）——开批已列出本轮全部 medium+；验证期若发现新的 medium+，按 `templates/review-loop.md`
只登记到下一批，不扩大本轮。

### low / nit 登记（累积）

| id | severity | 锚点 | 处置（第 2 轮复核） | 理由 / 证据 |
|---|---|---|---|---|
| R1-L1 | low | `design.md:41,240,265`；`reviews/grill-design.md:42` | **已修** | D1:85-86 与 §4 已把 commit-pin 形状写成“已由 asterwynd 真 CI 证实”；`grep 未验证` 在 design 中已无命中。证据：run `39386712284` 的 `WL_WORKFLOW_REF=…@c9b2811…`、`WL_WORKFLOW_SHA=c9b2811…`、gate 绿。 |
| R1-L2 | low | `proposal.md:42` | **已修** | proposal 已收窄为“所有**发布 tag**（`v1`、`v1.0.0…v1.7.0`）都是 annotated”，并注明 `wip-postmerge-*` 是轻量 tag。 |
| R1-L3 | low | `design.md:53-59`；`spec.md:12-17` | **已修** | 现已改为已知前缀精确剥离：普通 `@`、`@refs/heads/`、`@refs/tags/` 的 branch/tag 名均实测完整保留；路径不匹配（`gate@prod.yml`）⇒ sha 兜底 + warning。R2-1 已验证。 |
| R1-L4 | low | `spec.md:7`、`spec.md:12-26` | **已修** | 标题改为“按 ref 形态取可安装且精确的那个”；小写 hex、非空尾、纯空白守卫均对齐。 |
| R1-L5 | nit | `design.md:232`；`tasks.md:19` | **已修** | B1 已勾；`design.md` 的 Code-Resolved 计数已不再写 21（本轮 grep 未再命中）。 |
| R1-L6 | low | `tasks.md:64-65`；`reviews/grill-design.md:94-95` | **已修（引用）** | tasks F4 已写“授权来源：用户 2026-10-20 任务书「合入一律 `--merge`」”。零记忆审阅者只能核对这条在仓内引用，无法核对任务书原文；引用本身已满足 R1-L6 的“引用或改写”。 |
| R1-L7 | low | `design.md:97-100`；`.github/workflows/gate.yml:150-157` | **已修** | 实际 step 对 `WL_FALLBACK_REF=''` 与 `WL_INPUT_REF='   '` 均 `EXIT=1` + `::error::`，不写出 `ref=`；新增行为测试 `tests/test_gate_workflow.py:625-645`。 |
| R1-L8 | low | `design.md:157-159` | **已修（D5）**；§4 残句见 R3-L1 | D5 已明确 `test_resolve_prefers…` 在混合优先级下仍返回 sha、保持有效，只更新注释/名字；实际测试文件也未删除它。 |
| R1-L9 | low | `tasks.md:69-73`；`README.md` / `docs/gate.md` | **已按计划** | tasks G1 已写“合入后立即打 tag；窗口内不要接入/升级”，并明确“GitHub Release 正文 SHALL 写明这个窗口与钉 annotated tag 受支持”；用户可见发布说明由 Release 正文承担。 |
| R2-L1 | low | `design.md:122` | **已修** | D4 表已改成“`job.workflow_ref` 且 **降级**”；实际 step 的降级 WHY 与 `tests/test_gate_workflow.py:442-452` 的 `"降级"` 一致。 |
| R2-L2 | low | `design.md:41,240,265` | **已修** | design 中已无“未验证”；D1:85-86、§4:265 引用 asterwynd run `39386712284` 为已验证。 |
| R2-L3 | low | `design.md:259-260` | **未清 → R3-L1** | §4 “旧测试点名”仍要求 `test_resolve_prefers…` 与 `test_resolve_falls_back…` 都“必须改写/删除”；D5:157-159 已改为前者保持有效。 |
| R2-L4 | low | `design.md:150`；`tasks.md:33`；`tests/test_gate_workflow.py:541-552` | **已修** | `test_resolve_accepts_a_tag_name_with_a_plain_at_sign`（`refs/tags/v1@rc1`）与 R2-1 三例均已落。 |
| R2-L5 | low | `tasks.md:69-73`；`README.md` / `docs/gate.md` | **已按计划** | tasks G1 已明确 GitHub Release 正文承担窗口与“annotated tag 受支持”；用户可见说明在 Release，而非 README/docs。 |
| R2-L6 | low（流程） | `tasks.md:88-98`；`.github/workflows/gate.yml` 等修改态 | **已记录（不影响出口）** | tasks §流程偏差如实记录：实现于设计对抗第 2 轮验证期间开始，**未在 PASS 前产证据 manifest、未合入、未发版**，不伪造授权。`pytest -q` 现 **767 passed**。按 low 处置；不影响设计出口（该偏差已记录，F2/E1 仍按流程补证据）。 |
| R2-L7 | nit | `.github/workflows/gate.yml:183` | **已修** | 安装步注释已改为“tag 用 caller 钉的 tag ref；分支 / commit 用实际执行的 commit”。 |
| R2-L8 | nit | `tasks.md:21-22` | **待 PASS 后勾** | B2 仍 `[ ]` 且写“待验证”；本报告 PASS 后应改为 `[x]` 并引用本报告（不阻塞 PASS）。 |
| R2-L9 | nit | `design.md:272` | **已修** | §4 已写“第 1 轮批次（已验证通过）”。 |
| R3-L1 | low | `design.md:259-260` | 登记待作者订正 | §4 “旧测试点名”仍要求 `test_resolve_prefers…` 必须改写/删除；D5:157-159 已改为保持有效。删掉 §4 里对前者的要求即可。 |
| R3-L2 | low | `design.md:281` | 登记待作者订正 | §4 的 low/nit 摘要仍写“解析改为锚定 `@refs/tags\|heads/` + 最后一个 `@`”，与实际“已知前缀精确剥离”不一致；改成 prefix 方案。 |
| R3-L3 | low | `tasks.md:49` | 登记待作者订正 | D5 写“764 passed”，本轮实测 **767 passed**（新增三例 + 普通 `@` + 路径不匹配）；更新计数。 |
| R3-L4 | low | `tasks.md:21-22` | 登记待作者更新 | B2 仍 `[ ]`；“待验证”已过期。PASS 后勾上并引用本报告（与 R2-L8 同一项）。 |
| R3-L5 | low | `design.md:270-282` | 登记待作者补记 | §4 “设计阶段对抗验证”只有第 1 轮与 low/nit 摘要，**没有 R2-1（已知前缀剥离）这一条**；补一行“R2-1 已修并验证”。 |
| R3-L6 | nit | `design.md:102`；`.github/workflows/gate.yml:92-96` | 登记（措辞） | D2 写“一律 `${VAR:-}` 读”，但 `PREFIX="$WL_REPO_SLUG/..."` 与 `REF="$WL_FALLBACK_REF"` 是直接读；这两个是 step 内的**字面量 env**（始终存在，测试也从 YAML 注入），不构成实际失败。若要求逐字一致，改用 `${WL_REPO_SLUG:-}` / `${WL_FALLBACK_REF:-}`，或把 D2 的“一律”限定到外部 `job.*` / input。 |

### 第 1 轮后 · 收口确认

- 复核时间: 2026-10-20（本轮）；范围: R1-1 / R1-2 及 low/nit 落点。
- **2/2 已修好，0 条 medium+ ⇒ 第 1 轮收口**。第 1 轮不再扩批；第 2 轮按新的完整审阅开批。

### 第 2 轮 · 批次

| id | severity | 锚点（文件:行） | 问题 |
|---|---|---|---|
| R2-1 | **medium** | `openspec/changes/gate-ref-annotated-tag/design.md:53-59`、`specs/gate-ref-pinning/spec.md:12-14`、`.github/workflows/gate.yml:95-101`、`tests/test_gate_workflow.py:471-491` | 新“稳健解析”仍会对**合法 ref 名里含另一命名空间**的形态**静默取错 ref**。实际 step 用 `*@refs/tags/?*` **先于** `*@refs/heads/?*`（tag 优先），并用 `${…##*@refs/…/}`（**最后**一次出现）截尾。我用**实际 gate.yml 的解析 step**（不是一次性脚本）复现：<br>① `WL_WORKFLOW_REF=…gate.yml@refs/heads/feature/a@refs/tags/b` + 非空 `WL_WORKFLOW_SHA=6e2ec4d…` ⇒ **`ref=refs/tags/b`**——branch pin 被当成 tag，**忽略**了精确 sha；若存在同名 tag `b` 会**静默装错版本**，否则才由 uv 响亮失败。<br>② `…@refs/tags/v1@refs/tags/rc`（sha 空）⇒ **`ref=refs/tags/rc`**（应为 `refs/tags/v1@refs/tags/rc`）。<br>③ `…@refs/heads/feature/a@refs/heads/b`（sha 空）⇒ **`ref=refs/heads/b`**（被截断）。<br>这些 ref 名在 Git 合法，且 design 明确宣称“分支/tag 名含 `@` 不截错”；但新增的 `test_resolve_parses_refs_with_at_signs_robustly` 只覆盖**普通 `@`**（`feature/a@b`、`gate@prod.yml`），没有覆盖名字里含 `@refs/heads/` / `@refs/tags/` 的形态；D5 点名的“tag 名含 `@`”用例也尚未落。⇒ 修法二选一：**(a)** 改成“**最先出现**的 `@refs/(heads\|tags)/` 才是真正的 ref 起点”，用**第一次**出现的尾段，并加上述三例；**(b)** 对这类歧义形态显式 fail-closed（不能**静默**把 branch 当 tag）。修复后必须补一组先红后绿的行为测试。 |

### 第 2 轮 · 验证

| id | 结果 | 修复证据（设计环） | 回归测试 |
|---|---|---|---|
| R2-1 | **已修好** | 解析改为**已知前缀精确剥离** `<REPO_SLUG>/.github/workflows/gate.yml@`；剥离后只接受 `refs/tags/<非空>` / `refs/heads/<非空>` / 40/64 位小写 hex；路径不匹配 ⇒ `REF_PART=""`（sha 兜底 + warning 或 fail-closed）。`design.md:53-59`、`spec.md:12-17` 已同步。 | 新增 `test_resolve_is_not_fooled_by_ref_names_containing_another_namespace`（三例）、`test_resolve_accepts_a_tag_name_with_a_plain_at_sign`、`test_resolve_falls_back_loudly_when_the_workflow_path_is_unexpected`；`pytest -q` → **767 passed**。 |

实际 `run:` 三例（本轮；完整矩阵见下）：

```
① branch @refs/tags/ + sha=6e2ec4d… → ref=6e2ec4dc7955d6d155987a667040b126acab983b（无 warning）
② tag @refs/tags/（sha 空）          → ref=refs/tags/v1@refs/tags/rc
③ branch @refs/heads/（sha 空）      → ref=refs/heads/feature/a@refs/heads/b
```

### 第 2 轮后 · 收口确认

- 2026-10-20（本轮复核）；范围 R2-1；**已修好，0 条 medium+ ⇒ 第 2 轮收口**。
- R2 low/nit 的处置见累积登记表；第 3 轮按新的完整审阅开批。

### 第 3 轮 · 批次

（空）——本轮完整审阅未发现新的 medium+；不重复 R1/R2 已修项。第 3 轮开批为空。

### 第 3 轮 · 验证

（空批，无需修复验证。）本轮复验了：前缀剥离在 dash 下的路径不匹配、ref 名含 `@` /
`@refs/...`、空尾、裸 hex、大写 hex、空与纯空白 ref；design/spec 的 SHALL 与实际 step
一致；`pytest -q` → **767 passed**。R2 low/nit 残余见累积登记表（均 low/nit）。

### 第 3 轮 · 下一批（deferred）

（空）——第 3 轮开批为空。

### 第 3 轮后 · 收口确认

- 2026-10-20（本轮）；范围：修订后的 D1/D2/D4/D5 + spec + 实际 `run:` + 767 passed。
- **0 条 medium+ ⇒ PASS**。R2-1 已修好；第 1/2/3 轮均收口。low/nit 残余见累积登记表，不阻塞。

## 独立实测证据（原始输出摘录）

### uv 版本与可安装性（每次独立 `UV_CACHE_DIR`）

```
uv0.12.1  tag-object 00192abe…  EXIT=0  → Building witnessloop @ c9b2811…
uv0.13.1  tag-object 00192abe…  EXIT=0  → Building witnessloop @ 00192abe…（仍安装成功）
uv0.13.2  tag-object 00192abe…  EXIT=1  → Exact Git revision … does not match precise commit c9b2811…
uv0.13.3  tag-object 00192abe…  EXIT=1  → 同上
uv0.13.3  refs/tags/v1.7.0      EXIT=0  → Building witnessloop @ c9b2811…
uv0.13.3  v1.7.0（短 tag）       EXIT=0  → Building witnessloop @ c9b2811…
uv0.13.3  refs/heads/main       EXIT=0  → Building witnessloop @ 98b97b7…
uv0.13.3  c9b2811…（commit）     EXIT=0
uv0.13.2  refs/tags/v1.7.0      EXIT=0  → Building witnessloop @ c9b2811…（本地 bare clone，排除网络）
```

PEP 610 证据（uv 0.13.3 装 `refs/tags/v1.7.0` 的构建环境 `direct_url.json`）：
`requested_revision=refs/tags/v1.7.0`、`commit_id=c9b281167ad20b63e4832ad9ab8510964a2adc60`。
⇒ design D7 说的“`check` 自报会显示 `refs/tags/v1.7.1`”成立。

### 真 CI 日志

annotated tag（run `38928669316`，job `117066704863`，日志经 API 解压）：

```
Uses: Xingkai98/witnessloop/.github/workflows/gate.yml@refs/tags/v1.7.0 (00192abe45d2d72a4389eccb202faad48c34fa26)
WL_WORKFLOW_SHA: 00192abe45d2d72a4389eccb202faad48c34fa26
WL_WORKFLOW_REF: Xingkai98/witnessloop/.github/workflows/gate.yml@refs/tags/v1.7.0
##[notice]witnessloop 包 ref = 00192abe…（来源：job.workflow_sha…）
check：本包来源（自报…）：requested_revision=00192abe…，commit_id=00192abe…
```

分支探针（跨仓 run `38853369550`，repo `Xingkai98/asterwynd-wl-switch`）：

```
job.workflow_ref = Xingkai98/witnessloop/.github/workflows/probe-ref.yml@refs/heads/probe/workflow-ref
job.workflow_sha = 6e2ec4dc7955d6d155987a667040b126acab983b
job.workflow_repository = Xingkai98/witnessloop
github.workflow_sha = 2778bc24…（caller 自己的，证伪点）
```

commit pin（**本轮新增**，asterwynd run `39386712284` / job `118508174549`，gate 绿）：

```
Uses: Xingkai98/witnessloop/.github/workflows/gate.yml@c9b281167ad20b63e4832ad9ab8510964a2adc60
WL_WORKFLOW_REF: Xingkai98/witnessloop/.github/workflows/gate.yml@c9b281167ad20b63e4832ad9ab8510964a2adc60
WL_WORKFLOW_SHA: c9b281167ad20b63e4832ad9ab8510964a2adc60
##[notice]witnessloop 包 ref = c9b2811…（来源：job.workflow_sha…）
```

### 解析器一次性复现（按 design D1 写成 `sh`，`dash` 下跑）

```
tag-annotated      ref=refs/tags/v1.7.0          （无 warning）
branch-with-sha    ref=6e2ec4d…                  （无 warning）
commitpin-hex      ref=6e2ec4d…                  （无 warning）
malformed+sha      ref=00192abe…                 warning（附原值）
sha-empty-branch   ref=refs/heads/main
sha-empty-tag      ref=refs/tags/v1.7.0
tag-empty-tail     ref=<sha> + warning
branch-empty-tail  ref=<sha> + warning
branch-with-@      ref=refs/heads/feature/a@b
hex64              ref=<64 hex>
uppercase-hex      ref=<sha> + warning
undefined-env      ref=<fallback> + warning
empty-fallback     EXIT=1 + ::error::（旧实现：EXIT=0 + ref=）
GITHUB_OUTPUT 缺失  EXIT=2
repo-mismatch      ref=<fallback> + warning（不落 workflow_ref）
at-in-path-tag     ref=<tag object sha> + warning（第 1 轮一次性脚本的边界；现实现见下）
```

### 实际 gate.yml 解析 step 边界矩阵（第 2 轮 · 修复前）

直接取 `.github/workflows/gate.yml` 的 `run:` 交 dash（不是一次性复刻）；除注明外
`WL_WORKFLOW_REPOSITORY=Xingkai98/witnessloop`。这一组是 **R2-1 修复前**的历史证据：

```
annotated tag                     ref=refs/tags/v1.7.0
branch+sha                        ref=6e2ec4dc7955d6d155987a667040b126acab983b
commit pin                        ref=6e2ec4dc7955d6d155987a667040b126acab983b
workflow path @ plain             ref=refs/tags/v1.7.0
branch name @ plain               ref=refs/heads/feature/a@b
tag name @ plain                  ref=refs/tags/v1@rc1
branch name @refs/heads/ (sha空)  ref=refs/heads/b                 ← R2-1 ③（应为完整 branch ref）
branch name @refs/tags/  (有 sha) ref=refs/tags/b                  ← R2-1 ①（branch 被当 tag、忽略 sha）
tag name @refs/heads/             ref=refs/tags/v1@refs/heads/rc
tag name @refs/tags/              ref=refs/tags/rc                 ← R2-1 ②（应完整 tag ref）
path @refs/tags/ + tag            ref=refs/tags/v1.7.0
no @ bare hex                     ref=<sha> + fallback warning
refs/tags/ / refs/heads/ 空尾      ref=<sha> + fallback warning
empty WL_FALLBACK_REF             EXIT=1（无 ref= 写出）
WL_INPUT_REF='   '                EXIT=1（无 ref= 写出）
undefined env                     ref=v1.7.1 + warning
```

### 实际 gate.yml 解析 step 边界矩阵（第 3 轮 · 修复后）

同一实际 `run:`（已知前缀精确剥离），R2-1 三例与边界复跑：

```
R2-1 ① branch @refs/tags + sha    ref=6e2ec4dc7955d6d155987a667040b126acab983b（无 warning）
R2-1 ② tag @refs/tags (sha空)     ref=refs/tags/v1@refs/tags/rc
R2-1 ③ branch @refs/heads (sha空) ref=refs/heads/feature/a@refs/heads/b
annotated tag                     ref=refs/tags/v1.7.0
branch+sha                        ref=6e2ec4dc7955d6d155987a667040b126acab983b
commit pin                        ref=6e2ec4dc7955d6d155987a667040b126acab983b
tag plain @                       ref=refs/tags/v1@rc1
path mismatch + sha               ref=<sha>（+ warning；test 断言原值）
path mismatch no sha              ref=v1.7.1（+ warning）
no prefix tag-like                ref=<sha>（+ fallback warning）
prefix + extra @ tail             ref=<sha>（+ fallback warning）
refs/tags/ / refs/heads/ 空尾      ref=<sha>（+ warning）
64 hex                            ref=<64 hex>
uppercase hex                     ref=<sha>（+ warning）
empty WL_FALLBACK_REF             EXIT=1（无 ref= 写出）
WL_INPUT_REF='   '                EXIT=1（无 ref= 写出）
undefined env                     ref=v1.7.1 + warning
```

### 自身门禁 / R1 验证 / 基线（本轮）

```
# R1-2：改前 2 条 finding（第 1 轮已记录）→ 改后 0 条
evidence.grill_evidence_findings(reviews/grill-design.md) -> []

# R1-1：临时仓实际 init（全 sha）
witnessloop init --gate-ref ...gate.yml@98b97b7046e98508470345ce081f7189c6c4269c --policy .witnessloop/policy.json
  EXIT=0; caller uses: ...@98b97b7046e98508470345ce081f7189c6c4269c
  台账 gate_ref 同值; caller 条目 sha256 == 磁盘 sha256

# R2-1 新测试已落并通过：
test_resolve_is_not_fooled_by_ref_names_containing_another_namespace
test_resolve_accepts_a_tag_name_with_a_plain_at_sign
test_resolve_falls_back_loudly_when_the_workflow_path_is_unexpected

# 当前工作树（实现先行已在 tasks §流程偏差记录；R2-L6）
.venv/bin/python -m pytest -q -> 767 passed
```

### 外部依据

- GitHub Changelog, “GitHub Actions: Short SHA deprecation”:
  <https://github.blog/changelog/2021-01-21-github-Actions-short-sha-deprecation/>
- GitHub Docs, “Reusing workflows”:
  <https://docs.github.com/en/actions/sharing-automations/reusing-workflows>
- GitHub Docs, “Security hardening for GitHub Actions”（“Pin actions to a full-length
  commit SHA”；并写明同一原则适用于 reusable workflows）:
  <https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions>
- 可复用 workflow 调用语法 reusable:
  <https://raw.githubusercontent.com/anthonysidesapps/docs/1ff44fe6f706f60c94903c2235b11f6d196ca212/data/reusables/actions/reusable-workflow-calling-syntax.md>

## 闭环出口

**PASS**（第 1 轮 R1-1/R1-2、第 2 轮 R2-1 均验证通过；第 3 轮完整审阅 0 条 medium+）。
low/nit 残余见累积登记表，均不阻塞。R2-L6 的流程偏差由作者在 `tasks.md §流程偏差` 如实记录
（**未在 PASS 前产证据 manifest、未合入、未发版，不伪造授权**），按 low 处置，不影响设计出口；
F2/E1 后续仍按流程补证据。
