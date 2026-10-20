# Grill: gate-ref-annotated-tag 设计追问

## Reviewer

- run id: `grill-reviewer-gate-ref-annotated-tag-98b97b7046e9`
  （`WITNESSLOOP_RUN_ID` / `WITNESSLOOP_REVIEWER_RUN_ID` 均未设置；按 `templates/grill.md`「怎么取 run id」用确定性兜底：`<stage>-<role>-<change id>-<HEAD 前 12 位>`，HEAD = `98b97b7046e9`。）
- 时间: 2026-10-20T09:07:43Z
- verdict: **可进入对抗验证**（frontier 已空；有 6 条 medium 级需在实现前定案，见「风险」）。
- 审阅方式: 零记忆；只读仓内文本、代码、GitHub 真 CI 日志与本地一次性实验；未读作者会话。

## Confirmed Decisions

- **决策（需求对齐 · 根因与修复方向）**：issue #42 的根因判定成立，且「annotated tag 优先取 `job.workflow_ref` 的 `@` 后 namespaced ref」能消除 tag object sha 被交给 uv 的路径。
  理由：真 CI 日志（本仓 run `38928669316`，job `gate / check`）逐字给出 `Uses: …/gate.yml@refs/tags/v1.7.0 (00192abe…)`、`WL_WORKFLOW_REF: …/gate.yml@refs/tags/v1.7.0`、`WL_WORKFLOW_SHA: 00192abe…`；把**当前旧解析脚本**的 `run:` 原文交 `sh` 实跑，同一组输入输出 `ref=00192abe…`；uv 0.13.3 对 tag object sha `EXIT=1`、对 `refs/tags/v1.7.0` `EXIT=0`（解析到 commit `c9b2811…`）。
  来源: `grill-reviewer-gate-ref-annotated-tag-98b97b7046e9`
- **决策（实现细节 · workflow_ref 形态可解析）**：`job.workflow_ref` 对 annotated tag 与分支都给出 `…@{refs/tags|refs/heads}/<name>` 形态，按 `@` 后整段解析是可实现的。
  理由：tag 形态见上；分支形态由跨仓探针 run `38853369550` 日志直接给出 `PROBE job.workflow_ref=…/probe-ref.yml@refs/heads/probe/workflow-ref`、`job.workflow_sha=6e2ec4d…`。一次性 `sh` 探针验证了 `refs/tags/?*` / `refs/heads/?*` / 40 或 64 位小写 hex 的接受与拒绝边界。
  来源: `grill-reviewer-gate-ref-annotated-tag-98b97b7046e9`
- **决策（实现细节 · 守卫顺序）**：显式 `with.witnessloop-ref` → `job.workflow_repository` 守卫 → `job.workflow_ref` → `job.workflow_sha` 兜底 → fail-closed 的顺序正确，且把 workflow_ref 提前**不**破坏跨仓守卫。
  理由：`gate.yml:82-98` 现有的守卫在 sha/ref 之前；`tests/test_gate_workflow.py:508-524` 已用行为级测试钉住「repository 不匹配不落到 workflow_ref」。新设计 `design.md:42-53` 把 workflow_ref 提前但保留守卫在其之前，语义一致。
  来源: `grill-reviewer-gate-ref-annotated-tag-98b97b7046e9`
- **决策（测试策略 · 行为级回归能打红旧实现）**：新增 annotated-tag 用例在旧「sha 优先」实现下必红，且不是文本同义反复。
  理由：`tests/test_gate_workflow.py:294-321` 的 `_run_resolve` 把 step 的 `run:` 原文交真 `sh`；旧脚本实跑输出 `ref=00192abe…`（证据同上），与断言 `refs/tags/v1.7.0` 不同；安装步消费解析结果已有钉子 `tests/test_gate_workflow.py:532-549`。
  来源: `grill-reviewer-gate-ref-annotated-tag-98b97b7046e9`
- **决策（发布/自举 · 临时钉 commit + 发版后回钉）**：先合入、在合并提交上打 annotated `v1.7.1`、再用回钉 PR 做真实 CI canary 的顺序可行；`98b97b7` 确为当前 `origin/main`。
  理由：`git ls-remote origin refs/heads/main` = `98b97b7046e98508470345ce081f7189c6c4269c`；caller 从 PR head 取（`.github/workflows/witnessloop.yml:14`），临时钉 commit 后旧 gate 的 `job.workflow_sha` 就是 commit（`gate.yml:84-86`），可安装；回钉 PR 的 caller 在 PR head 里钉 `@v1.7.1`，由 v1.7.1 的新 gate 判定。
  来源: `grill-reviewer-gate-ref-annotated-tag-98b97b7046e9`
- **决策（触发与门禁 · 本 change 可满足自己的门禁）**：本 change 会触发 `require_change_for`、三份 stage manifest 与受保护路径事件，但按 design/tasks 的安排可满足。
  理由：`src/witnessloop/constants.py` 命中 `src/**`（`.witnessloop/policy.json`）⇒ `code_hits` ⇒ `grill-adversarial` + `building` manifest（`src/witnessloop/checkcmd.py:167-207`）；`.witnessloop/init-manifest.json` 在不变集（`src/witnessloop/policy.py:18-23`）⇒ F1 需一条 `protected_path_write` 事件；新 change 目录的 `workflow-events.jsonl` 是新增（A），按 `src/witnessloop/checkcmd.py:393-394` 免事件。
  来源: `grill-reviewer-gate-ref-annotated-tag-98b97b7046e9`
- **决策（文档影响 · 旧结论落点已识别）**：D7 列出的同步面基本正确；`docs/gate.md` 的旧结论必须改写，不能用「tag object sha 可安装」的旧叙述继续发布。
  理由：`docs/gate.md:82-93` 明写「uv/git 能把 tag 对象 sha 解析成它指向的 commit」；`docs/gate.md:587-589`、`constants.py:14-26`、`README.md:190`、`gate.yml:40-45` 均仍是旧优先级叙述；`docs/design.md:57` 也被 `tasks.md:38` 点名。
  来源: `grill-reviewer-gate-ref-annotated-tag-98b97b7046e9`

## Code-Resolved Questions

- **uv 的版本分界到底在哪？** → **0.13.2 起拒绝，0.13.1 及更早接受**；`design.md` / `proposal.md` / `spec.md` 写的「uv ≥0.13.3 拒绝」不准确（会让读者以为 0.13.2 安全）。
  证据（本机四次独立安装 + 全新 `UV_CACHE_DIR`）：`/tmp/uv0121/uvx` 对 tag object sha `EXIT=0`；`/tmp/uv0131/uvx` `EXIT=0`；`/tmp/uv0132/uvx` `EXIT=1`（`Exact Git revision … does not match precise commit …`）；`/tmp/uv0133/uvx` `EXIT=1`。设计应把版本分界改成「0.13.2 起」，或写「实测 0.13.1 绿 / 0.13.2 红」。
- **`refs/tags/v1.7.0` 在 uv 0.13.3 下真的可安装吗？** → **是**。证据：`UV_CACHE_DIR=/tmp/uv-cache-42-c /tmp/uv0133/uvx --from "git+https://github.com/Xingkai98/witnessloop@refs/tags/v1.7.0" witnessloop --version` ⇒ `Building witnessloop @ …@c9b281167ad20b63e4832ad9ab8510964a2adc60`、`witnessloop 0.1.0`、`EXIT=0`。短 tag 名 `v1.7.0` 同样 `EXIT=0`；`refs/heads/main` `EXIT=0`（解析到 `98b97b7…`）；commit sha `EXIT=0`；tag object sha `EXIT=1`。
- **`job.workflow_ref` 对 annotated tag 的实际形状？** → `Xingkai98/witnessloop/.github/workflows/gate.yml@refs/tags/v1.7.0`，同时 `job.workflow_sha=00192abe…`（tag object）。证据：真 CI run `38928669316` 的 job 日志（`WL_WORKFLOW_REF` / `WL_WORKFLOW_SHA` 两行 + `Uses:` 行）；`docs/gate.md:85` 记录了同一行。
- **`job.workflow_ref` 对分支的实际形状？** → `…@refs/heads/<branch>`。证据：跨仓探针 run `38853369550` 日志中的 `PROBE job.workflow_ref=Xingkai98/witnessloop/.github/workflows/probe-ref.yml@refs/heads/probe/workflow-ref` 与 `PROBE job.workflow_sha=6e2ec4dc…`。
- **commit pin 的 `job.workflow_ref` 形状？** → **已验证**为 `@<40 位小写 hex>`。证据：asterwynd 的 commit-pin 热修 caller（run `39386712284` / job `118508174549`，gate 绿）日志：`WL_WORKFLOW_REF: …/gate.yml@c9b281167ad20b63e4832ad9ab8510964a2adc60`、`WL_WORKFLOW_SHA: c9b2811…`。（对抗轮 R1-L1 复核。）
- **`refs/tags/`（斜杠后为空）会被误匹配吗？** → 若实现写成 `*@refs/tags/*`，**会**（glob 的 `*` 可匹配空）；必须用 `refs/tags/?*` / `refs/heads/?*` 强制非空。证据：一次性 `sh` 探针中 `refs/tags/`、`refs/heads/` 均落入「不可解析」分支。
- **分支名 / tag 名 / workflow 路径里含 `@` 会怎样？** → 采用**稳健定位**：优先锚定
  `@refs/tags/` / `@refs/heads/`，否则取最后一个 `@` 之后的 40/64 位小写 hex。这样
  `refs/heads/feature/a@b`、`gate@prod.yml@refs/tags/v1.7.0`、`refs/tags/v1@rc1` 都能正确解析
  （对抗轮 R1-L3 的修正）。
- **大写十六进制 commit sha 会怎样？** → 按 spec 的「小写」规则会被判「解析不出」→ 走 `job.workflow_sha` 兜底 + warning（结果仍是同一个 commit，但 warning 误导）。证据：`sh` 探针对 `00192ABE…` 输出 `other:`。建议实现允许大小写（统一转小写）或至少把这一形态写进测试。
- **旧的 sha 优先实现会在新增核心用例上红吗？** → **会**。证据：用 `yaml.safe_load` 取出当前 `gate.yml` 的 `run:` 原文交 `sh`，输入 `WL_WORKFLOW_REPOSITORY=Xingkai98/witnessloop`、`WL_WORKFLOW_SHA=00192abe…`、`WL_WORKFLOW_REF=…@refs/tags/v1.7.0`，输出 `ref=00192abe45d2d72a4389eccb202faad48c34fa26`、`EXIT=0`；断言 `refs/tags/v1.7.0` 必红。
- **安装步真的消费解析结果吗？** → 是。`gate.yml:127-142` 用 `WL_REF: ${{ steps.wl-ref.outputs.ref }}`，run 里用 `"git+https://github.com/Xingkai98/witnessloop@$WL_REF"`；`tests/test_gate_workflow.py:532-549` 已把「不得再直接读 `inputs.witnessloop-ref`」钉住。
- **两者都不可用时会装默认分支吗？** → 在 `WL_FALLBACK_REF` **非空**时不会：输出 fallback ref + `::warning::`；`GITHUB_OUTPUT` 未定义时 `set -u` 让脚本退非零（响亮）。但 **`WL_FALLBACK_REF` 被定义为空**时会输出 `ref=` 且 `EXIT=0`，安装步会退化成 `git+…@`（装默认分支）。证据：实跑当前脚本、`WL_FALLBACK_REF=''` ⇒ `OUT='ref=\n'`、`EXIT=0`；`gate.yml:100-109`；现有 `tests/test_gate_workflow.py:454-463` **没有**覆盖空 fallback。
- **repository 守卫会拿别人仓的 ref 去装包吗？** → 不会；守卫在 workflow_ref 之前，且既有行为测试钉住。证据：`gate.yml:82-83`、`tests/test_gate_workflow.py:508-524`。
- **修复 PR 的 `gate / check` 跑的是旧 gate 吗？** → 是。临时钉 `98b97b7` 后，reusable workflow 仍是该 commit 的旧文件，旧 gate 用其 `job.workflow_sha`（= commit）装包；新 gate 的第一次真实运行发生在回钉 `@v1.7.1` 的 PR。证据：`.github/workflows/witnessloop.yml:14`、`gate.yml:84-86`；真 CI run `38928669316` 的 notice 行证明旧 gate 的「来源：job.workflow_sha」路径。
- **哪些既有测试会被新优先级打红？** → `tests/test_gate_workflow.py:357-369`（断言 sha 胜过 `refs/heads/main`）与 `:420-435`（断言剥前缀后的 `main` / `v1.7.0`）必须**改写或删除**；`:59` 硬编 `v1.7.0` 必须改成 `v1.7.1`。`tasks.md:30-31` 的保留清单**不**含这两条（所以不是矛盾），但 D5 也没点名它们要改写/删除——实现时会先看到两条预期外的红。
- **回钉 PR（G2）的受保护写入事件怎么放？** → 可追加到本 change（active 或 archived）的 `workflow-events.jsonl`；但该 events 文件本身在不变集里（`src/witnessloop/policy.py:21`），追加是一次 `M`，需要**另一条** `artifact_path` 指向该 events 文件的 `protected_path_write` 事件。归档路径不会被当成 active change target（`src/witnessloop/contract.py:410-470`），且 events 文件在 stale 豁免集（`src/witnessloop/policy.py:77-91`），因此不会连带触发 manifest 重建。⇒ G2 通常要写**两条**事件，不是一条。
- **本 change 会触发哪些自身门禁？** → `src/witnessloop/constants.py` 命中 `src/**` ⇒ `code_hits` ⇒ 必须有 `grill-adversarial` 与 `building` 两份 stage manifest（`src/witnessloop/checkcmd.py:167-207`）；`grill` 报告正文要满足 `Confirmed Decisions` ≥3 且每条带 `来源:`、`Open Questions` 逐字存在且每个 `Qn` 在 `User Confirmation` 有确认（`src/witnessloop/evidence.py:259-330`）。⇒ **本报告在停轮前会让 `check` 红在 Q1/Q2 未确认上，这是停轮门的预期行为**。
- **文档测试会挡住改写吗？** → `tests/test_docs.py:277-283` 要求 `docs/gate.md` 仍含字符串 `job.workflow_sha`。新文档只要保留「sha 兜底」叙述即可通过；整段删掉该词会红。`tests/test_docs.py:286-292` 仍要求「先升 CLI」在 `init --gate-ref` 之前，改写时不要打乱。
- **`setup-uv` 是否浮动了 uv 版本？** → 是。`gate.yml:125` 是 `astral-sh/setup-uv@v5`，未 pin uv version，默认装最新；本次事故正是浮动 uv（0.13.1→0.13.2/0.13.3）引入。证据：`gate.yml:125`；本机四版本实测。
- **先改 `DEFAULT_GATE_REF` 再打 tag 的顺序对吗？** → 对；但合并与打 tag 之间的窗口里，main 上的 `init` 会生成指向尚不存在 `v1.7.1` 的 caller（0 job「workflow file issue」）。证据：`constants.py:26`；归档 change 的 `tasks.md:171` 记录过同款教训。应尽快打 tag，或在发布说明里写明窗口。
- **F1/G2 的 caller 迁移命令能直接用 `init --gate-ref` 吗？** → **不能不带 `--policy`**。本仓 policy 是定制版（`require_change_for` 含 `templates/**` / `plugin/**` 等）；实测 `witnessloop init --root . --dry-run --gate-ref <ref>` **EXIT=1**，报 policy 冲突；加上 `--policy .witnessloop/policy.json` 后 **EXIT=0**，并正确打印「将重写 caller 并同步台账」。⇒ F1/G2 的命令应写成 `witnessloop init --gate-ref <ref> --policy .witnessloop/policy.json`（或等价的 seed 副本），否则自举步骤会先红在 policy 上。⚠️ `<ref>` 在 commit pin 时必须是 **40 位全 sha**（对抗轮 R1-1；短 sha 会被 GitHub `uses:` 拒绝）。证据：`.venv/bin/witnessloop init --help` 的 `--policy` 说明；上述两次 dry-run 输出。
- **旧结论还有哪些散落点？** → `docs/gate.md:92`（uv/git 能解析 tag object sha）、`docs/design.md:57`（包 ref 由 `job.workflow_sha` 推导）、`README.md:190`、`constants.py:14-26`、`gate.yml:34-45`、`tests/test_gate_workflow.py:254-265` 的 D 组注释。证据：全仓 `grep -rn workflow_sha docs README.md src .github tests`（排除 archive）。
- **Q1 分支 pin 的包 ref：统一 `workflow_ref` 优先，还是混合优先级？** → **作者定案：混合**。
  `refs/tags/<tag>` 用 workflow_ref（annotated tag 必需）；`refs/heads/*` 与裸 commit 保留
  `job.workflow_sha`（精确 commit），仅当 sha 缺失才退回 workflow_ref。理由：既修 #42，
  又保住「一个 ref 决定 workflow 文件与包」的精确性，消除包比 workflow 文件晚一个 commit 的
  TOCTOU。已整合进 `design.md` D1 / spec 的 Scenario 与 D5 测试清单。
  （依据：任务明确「能由代码/实测/既有语义定案的自己定案并给证据」，不向用户提问。）
- **Q2 是否在 `gate.yml` 里 pin uv 版本？** → **作者定案：本 change 不 pin**，在
  `proposal.md` 非目标与 `design.md` 风险表显式登记为后续 change。理由：pin uv 是依赖治理
  取舍（会延迟安全/修复更新），且 `setup-uv` 目前只钉 action 大版本；本 change 的回归测试锁
  的是 ref 形态，不锁 uv 行为。代价与窗口已写入文档。

## Open Questions

（无）

## 风险

- **[medium] 分支 pin 的 TOCTOU 与契约弱化**（`design.md:55-59`、`design.md:162`）：统一 workflow_ref 优先让包可以比 workflow 文件晚一个/多个 commit；风险表的「接受」没有测试或日志钉子。→ 见 Q1；建议混合优先级。
- **[medium] 版本分界写错**（`design.md:14-26`、`proposal.md:16`、`spec.md:31`）：实测是 **0.13.2 起**拒绝（0.13.1 仍绿），不是 0.13.3 起；三处文档与验收 V4 都要改，否则发布物会带着错误结论。
- **[medium] G2 的受保护路径事件少算一条**（`design.md:134`、`tasks.md:56-57`）：追加到既有 `workflow-events.jsonl` 本身是 `M`（`src/witnessloop/policy.py:21`），需要自覆盖事件；G2 写「（同步台账 + 事件）」单数，按字面执行会红。→ 明确两条事件 + 指定 active/archived 落点。
- **[medium] F1/G2 的迁移命令漏了 `--policy`**（`design.md:131-134`、`tasks.md:48`、`tasks.md:56`）：本仓 policy 是定制版，`init --gate-ref` 不带 `--policy` 实测 dry-run `EXIT=1`（policy 冲突）；tasks 只写「同步台账」，按字面执行会先红。→ 明确写成 `witnessloop init --gate-ref <ref> --policy .witnessloop/policy.json`（G2 同理），或明确手工改 caller + 重算台账 sha256 的替代路径。
- **[medium] 空 `WL_FALLBACK_REF` 仍会静默装默认分支**（`design.md:65-73`、`spec.md:50`、`gate.yml:100-109`）：实跑 `WL_FALLBACK_REF=''` 得到 `ref=` 且 `EXIT=0`，与「SHALL NOT 输出空 ref」直接冲突。→ 在写 `ref=` 前加非空守卫（空则 exit 非零），并补一条行为测试；现有 `tests/test_gate_workflow.py:454-463` 未覆盖。
- **[low] 旧优先级测试未在 D5 里点名**（`design.md:97-123`、`tests/test_gate_workflow.py:357-369,420-435`）：`test_resolve_prefers_the_reusable_workflows_own_sha` 与 `test_resolve_falls_back_to_the_ref_part_of_job_workflow_ref` 编码的是旧优先级，必须改写/删除；tasks C4 的保留清单**不**含这两条，所以不是矛盾，但 D5 也没点名，实现时会先看到两条预期外的红。→ 在 D5 的「改写」清单里点名；`tests/test_gate_workflow.py:59` 的 `v1.7.0` 已由 tasks D3「相关测试断言同步」覆盖。
- **[low] `docs/design.md:57` 的旧结论未进 D7**（`design.md:144-156`、`tasks.md:38`）：tasks D4 说同步 `docs/design.md`，design D7 没列；验收 V4 的「不再出现旧结论」应把这条也算进去。→ 把 `docs/design.md:57`、`README.md:190`、`tests/test_gate_workflow.py:254-265` 的注释一并列入 D7（tasks D4 已覆盖前者，补齐即可）。
- **[medium] setup-uv 浮动版本是未声明的依赖**（`gate.yml:125`）：本次故障的成因就是浮动 uv；修复只覆盖当前 uv 行为，未降低「上游再变一次」的概率。→ 见 Q2。
- **[low] 解析边界测试缺口**（`design.md:97-123`、`spec.md:12-16`）：`refs/tags/` 空值、大写 hex、分支名含 `@`、64 位 hex、commit-pin 的真实 workflow_ref 形状均无用例；实现上必须用 `refs/tags/?*` 而不是 `refs/tags/*`。→ 加入 D 组，成本很低。
- **[low] workflow_ref 不可用 + sha 可用时，兜底 warning 信息不足**（`design.md:50-52`）：warning 不打印原始 `WL_WORKFLOW_REF`，一旦 GitHub 形态变化，接入方只能看到「用了 sha」而看不到实际形态。→ warning 里附上原值。
- **[low] `v1.7.1` 打 tag 前的窗口**（`constants.py:26`、归档 change 的 `tasks.md:171`）：合并后、打 tag 前，main 上的 `init` 会写出指向不存在 tag 的 caller（0 job）。→ 合并后立即打 tag；发布说明写明窗口。
- **[low] 新 gate 在发布前没有真实 tag 形态运行**（`design.md:127-142`）：修复 PR 的 required check 必然跑旧 gate；回钉 PR 是第一个 canary。设计已正确承认并安排后续验证；若要进一步降风险，可在修复 PR 里加一个**非 required** 的临时 caller（钉 PR 分支）跑一次新 parser，或至少在回钉 PR 的验收里记录 `::notice::` 的「来源：job.workflow_ref 的 tag」那一行。
- **[low] `check` 自报行在 CI 里会变成 namespaced ref**（`docs/gate.md:74-80`）：新 gate 传 `refs/tags/v1.7.1`，PEP 610 的 `requested_revision` 预计会显示 `refs/tags/v1.7.1`；文档里的示例仍写短 tag 名，需说明这是预期形态（本地 `uv tool install @v1.7.1` 仍显示短名）。
- **[low] 本 change 没有归档步骤/时序**（`tasks.md:53-58`）：G2 的事件落点取决于本 change 在回钉 PR 时是 active 还是 archived；两者都可行，但 tasks 应显式选一个，避免执行时临时判断。
- **[low] `gate.yml` 本身不在 `require_change_for`**（`.witnessloop/policy.json`）：本次自举靠 `src/witnessloop/constants.py` 触发 change 契约；这是既有边界，不是本 change 的缺陷，但「只改 gate.yml 的 PR 不需要 change」仍然成立，登记为宜。

## User Confirmation

- （无待确认项。任务明确「能由代码 / 实测 / 既有语义定案的自己定案并给证据；不要向用户提问」；
  Q1 / Q2 的定案理由与证据见 `## Code-Resolved Questions`。本条不是用户答复，只是停轮门的记录。）
