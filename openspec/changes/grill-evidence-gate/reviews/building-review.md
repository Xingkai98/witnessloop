# Building Review: grill-evidence-gate

> 审阅者：**独立零记忆实现审阅**（building）。算法与三态 verdict 依据 `templates/review-loop.md`。
> 只读：除本文件外未改任何文件、未 commit。
> 基线：`git merge-base HEAD main` = `843b691`；被审提交 `442a2f7..e425f63`（change 本体为 `16815c5`/`1fa4219`/`e425f63`）。
> 说明：本仓 `main` **落后于** `dogfood-bootstrap`(#8)，故 `git diff main..HEAD` 会把 #8 的改动一并纳入（见 Issue 8）。

## Verdict

**CHANGES_REQUESTED**

核心能力（共享 evaluator、`check` 接入、`guard` 动词 + hook、文档/ADR/守卫）**都已真实落地且行为正确**——我逐条读代码并**实测**确认：380 条测试全绿；evaluator 对 `dogfood-bootstrap` 与 `grill-evidence-gate` 两份真实报告均判合格（回归红线保住）；`check` 对「无 `stage=grill` / 缺 `stage` / `stage=grills`」三种情形分别给出可诊断的红。

但**没有一条 `[x]` 该被无条件相信**：`tasks.md` 里 **B1/B2/B3/C6 声称的「单测」并未全部在场**（行为有、测试缺），且 `plugin/hooks/guard.sh` 的退出码直传在**旧版 CLI** 下会把「未拦」翻成「全拦」。这些是需要修复的问题，但**不阻塞整体**，故 `CHANGES_REQUESTED`。

## Test Results

```
$ export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q
380 passed in 51.59s
```

补充实测（非仓库测试，`uv run python` 内联）：

- `evidence.grill_evidence_findings(dogfood-bootstrap/reviews/grill-review.md)` → **空**（合格）✅ B4 回归红线成立。
- `evidence.grill_evidence_findings(grill-evidence-gate/reviews/grill-review.md)` → **空**（合格）✅
- `check --base main --head HEAD`（本仓）→ 2 个 change：`dogfood-bootstrap` 报 3 条（base 假象，见 Issue 8）、`grill-evidence-gate` 报 2 条（**G1 未做**：无 manifest；无 `stage=grill` manifest）——G 未勾，属预期。
- `check` 三态实测：只有 `building` manifest → 红「现有 stage：building」；删 `stage` 字段 → 红「manifest 缺字段：stage」；`stage=grills` → 红「现有 stage：grills」。✅ B1 负向 / B2 / B3 的**行为**正确。

## Tasks Verification（逐条读代码核实，不信勾选）

### A. 共享 evaluator（D1）

| 条 | 结论 | 证据 |
|---|---|---|
| A1 合格样本 → 空 findings | ✅ | `tests/test_evidence.py:33`；`evidence.py:109-155` |
| A2 `<3` 条 → 红 | ✅ | `tests/test_evidence.py:38`；`evidence.py:121-128` |
| A3 块级 `来源:`（续行持有）→ 合格 | ✅ | `tests/test_evidence.py:44`；`_blocks` 见 `evidence.py:67-78` |
| A4 前缀变体 `- **决策（Dn）**：`/`- **决策**：`都算 | ✅ | `tests/test_evidence.py:56`；判据按「顶层 bullet + 块级 `来源:`」，不认前缀字面 |
| A5 `Qn` 无对应确认 → 红 | ✅ | `tests/test_evidence.py:68`；`evidence.py:139-150` |
| A6 占位确认不算 + 长答复豁免 | ✅ | `tests/test_evidence.py:75,82`；`_is_unconfirmed` `evidence.py:97-106` |
| A7 缺节 → 红 | ✅ | `tests/test_evidence.py:90`；`evidence.py:117,136` |
| A8 纯函数实现 | ✅ | `src/witnessloop/evidence.py`（复用 `contract.Finding`） |

### B. `check` 接入（D9 / #2）

| 条 | 结论 | 证据 |
|---|---|---|
| B1 `check` 对不合格报告红、对合格绿 | ⚠️ **部分**：正向有测试（`tests/test_manifest_build.py:69`）；**负向（绑定一份不合格正文 → `check` 红）无测试**。行为我已实测正确。见 Issue 1 |
| B2 manifest 缺 `stage` → 红 | ⚠️ **部分**：`constants.py:67-77` 已纳 `stage`，通用缺字段分支在 `tests/test_check_manifest.py:40`（但删的是 `base_sha`，**没有一个测试删 `stage`**）。行为实测正确。见 Issue 1 |
| B3 无 `stage=grill` → 红 + 点名「现有 stage：…」 | ⚠️ **部分**：实现 `evidence.py:189-198`，行为实测正确；但「现有 stage」串在测试里 **0 命中**（同时是 spec Scenario「stage 拼错可诊断」缺测试）。见 Issue 1 |
| B4 dogfood-bootstrap 仍绿 | ✅ | evaluator 对其实测 findings=0 |
| B5 `checkcmd` 接入 + `constants` 加 `stage` | ✅ | `checkcmd.py:78-84`、`constants.py:67-77` |

### C. `guard` 动词（D3/D4/D5）

| 条 | 结论 | 证据 |
|---|---|---|
| C1 命中且缺证据 → exit 2 | ✅ | `tests/test_guard.py:33`；`guardcmd.py:112-124` |
| C2 证据齐 → exit 0 | ✅ | `tests/test_guard.py:42` |
| C3 写文档 → 放行 | ✅ | `tests/test_guard.py:51`；`guardcmd.py:96-97` |
| C4 推得 id 不命中现存目录 → 放行 + 提示 | ✅ | `tests/test_guard.py:61`；`guardcmd.py:37-59,100-101` |
| C5 推不出 / 未接入 → 放行 + 提示 | ✅ | `tests/test_guard.py:87`（未接入）、`:61`（推不出） |
| C6 `SKIP_GUARD` 放行 + 留痕；`WITNESSLOOP_CHANGE` 覆盖 | ⚠️ **部分**：`SKIP_GUARD` 有测（`tests/test_guard.py:93`）；**`WITNESSLOOP_CHANGE` env 覆盖分支名无测试**（`:71` 用的是 `--change`）。见 Issue 2 |
| C7 实现 + `cli` 子命令 | ✅ | `src/witnessloop/guardcmd.py`、`cli.py:61-76,153-156` |

### D. CC hook 分发（D6）

| 条 | 结论 | 证据 |
|---|---|---|
| D1 `hooks.json`（`Write\|Edit` → shim） | ✅ | `plugin/hooks/hooks.json`（`description` + `PreToolUse`→`matcher:"Write\|Edit"`） |
| D2 `guard.sh` 取 `file_path` → `guard --path`；退出码直传 | ✅（但见 Issue 3） | `plugin/hooks/guard.sh:14-32` |
| D3 `hooks.json` 结构合 CC 格式 | ✅ | `tests/test_plugin.py:217-226` |
| D4 README 写明「装 plugin 还要装 CLI」 | ✅（但缺**版本**要求，见 Issue 3） | `plugin/README.md:76-89`；`tests/test_plugin.py:236` |

### E. 文档 + ADR（D7）

| 条 | 结论 | 证据 |
|---|---|---|
| E1 四处「hooks 只 advisory」措辞 | ✅ | `docs/design.md` §2 点 6、§9 风险 4；`README.md`；`docs/reviews/grill-design.md`（保留原文 + 更新注） |
| E2 新 ADR | ✅ | `docs/adr/0001-local-guard-hook.md`（新建目录） |
| E3 漂移守卫测试 | ✅ | `tests/test_docs.py:141-162`（STALE_HOOK_CLAIMS 覆盖旧措辞，可变异验证） |
| E4 `gate.md` §8（判定 + `guard` + 退出码分表） | ✅ | `docs/gate.md:290-315`、退出码分表 §6 `:257-276` |
| E5 README `guard` 用法 + 诚实边界 | ✅ | `README.md:35-37,109` |

### F. 自伤修复（D9）

| 条 | 结论 | 证据 |
|---|---|---|
| F1 `test_cli.py` 期望动词集 +`guard` | ✅ | `tests/test_cli.py:40-54` |
| F2 `test_plugin.py` 期望文件清单 +hook 两件 | ✅ | `tests/test_plugin.py:20-27` |

### G. 证据链与收尾

- G1/G2/G3 **未勾**——按 `review-loop` 「批次 aware」：G 是**审阅之后**的批次（G2 即本审阅），其 `[ ]` **不算缺陷**。但注意：本 change **当前 `check` 红**（无 manifest），须 G1 补齐后自绿。

## Issues

### Issue 1（中）— B1/B2/B3 声称的「单测」不全在场

`tasks.md` 勾了 B1/B2/B3 的「单测」，但：

- **B1 负向无测试**：没有任何测试把一份**不合格正文**绑到 `stage=grill` manifest 后断言 `check` 红。`tests/test_evidence.py:1` 只在**纯函数**层覆盖「不合格 → findings」，没走 `check` 接线；`check` 侧只被正向覆盖（`tests/test_manifest_build.py:69`）。
- **B2 无测试删 `stage`**：`tests/test_check_manifest.py:40` 删的是 `base_sha`；`tests/test_manifest_build.py:135` 只**正向**断言产物含必填字段（**不**钉 `stage ∈ REVIEW_MANIFEST_REQUIRED_FIELDS`——把 `stage` 从常量删掉，该测试照样绿）。
- **B3 的文案无测试**：`现有 stage` 串只在 `src/witnessloop/evidence.py:194`，测试里 0 命中；这同时是 spec `specs/evidence-gate/spec.md:46-49` 的 Scenario「stage 拼错可诊断」**缺测试**。

行为我已实测三态全对（见上），故这是**测试覆盖 / `[x]` 准确性**问题，非逻辑缺陷。**处置**：补三条能变红的测试（`check` 绑定不合格 grill 正文 → 红；删 `stage` → 红；`stage=grills` → 红且 stderr 含「现有 stage：grills」）。

### Issue 2（中）— C6 的 `WITNESSLOOP_CHANGE`（env 覆盖分支名）未测

`src/witnessloop/guardcmd.py:29,48` 实现了 `WITNESSLOOP_CHANGE` 优先于分支名，但 `tests/test_guard.py:71`（`test_explicit_change_overrides_the_branch`）走的是 `--change`，不是该 env。`WITNESSLOOP_CHANGE` 在 `tests/` **0 命中**。**处置**：补一条 `monkeypatch.setenv("WITNESSLOOP_CHANGE", ...)`、分支推不出的用例，断言被拦。

### Issue 3（中）— 旧版 CLI 会把「未拦」翻成「全拦」（fail-open → fail-closed 反转）

`plugin/hooks/guard.sh:32` 把 `witnessloop guard` 的退出码**直传**。若 PATH 上的 `witnessloop` 是**旧版**（不含 `guard` 动词），argparse 报 `invalid choice: 'guard'` 并以 **2** 退出（`src/witnessloop/cli.py:21-23` 把一切 usage 错固定到 `EXIT_USAGE=2`），而 CC 视 **exit 2 = block** ⇒ **每个 `Write|Edit` 都被拦**。

- 实测：本机 `/home/happy/.local/bin/witnessloop`（旧版 0.1.0，无 `guard`）→ shim 以 **2** 退出：
  `witnessloop: error: argument <命令>: invalid choice: 'guard' (choose from init, uninit, check, manifest)`。
- `design.md` R8 只覆盖「二进制**不在** PATH → 127 → fail-open」，**漏了「在 PATH 但过期 → 2 → fail-closed」**。
- 同一根因的次生面：`guard` 是 `EXIT_BLOCKED=2`（`constants.py:88`）与 `EXIT_USAGE=2`（`:82`）**同值**——任何 guard 侧的 argparse 用法错误（如 `--path` 值以 `-` 开头）都会被 CC 当成「拦住」。

**处置**（择一，需设计定夺）：安装文档加 **最低 CLI 版本**要求（「该 CLI 必须含 `guard` 动词」）；或 shim 对 `guard` 的**用法错误**做区分。注意：不能简单把「2 + usage 文案」当放行——它与「2 = 拦」冲突，须在 design 里定案。

### Issue 4（低）— `guard --path` 传目录（无尾斜杠）静默放行

`paths.matches("plugin", "plugin/**") == False`（`src/witnessloop/paths.py:25-57`，`**/` 只匹配「零层目录」而**单段目录名**不匹配 `dir/**`）。故 `guard --path src` / `--path plugin`（目录）→ 不命中 `require_change_for` → **放行**。CC hook 传的是 `file_path`（文件），正常路径不受影响；但手动/脚本调 `guard --path <目录>` 会静默 fail-open。属声明的 fail-open 边界，建议文档点一句或对无扩展名的目录形态补一次匹配。

### Issue 5（低）— 大小写不折叠 ⇒ 大小写不敏感 FS 上的绕过面

`normalize` 只做 `\`→`/` 与前导 `./` 剥离，**不折叠大小写**（`src/witnessloop/paths.py:13-22`）。`SRC/x.py` 不命中 `src/**` → `guard` 放行。`docs/gate.md §2:80-82` 已把该边界**声明**出来，但与本地守卫组合会降低其在 macOS 等大小写不敏感 FS 上的有效性。记录为已知。

### Issue 6（低）— evaluator 的宽松面（均属「防漂移不防伪造」既定边界）

- **空 `## Open Questions` ⇒ 直接合格**（`src/witnessloop/evidence.py:139-140`，无 Qn 则无确认要求）。一份只含 3 条 trivial 决策 + 空 OQ 的报告可通过 `check`。这是 spec 判据 3 的空真结果，非缺陷；建议在 `gate.md §8` 或 `evidence.py` docstring 点明，免得被当成漏洞。
- **占位启发式的空隙**：`待确认（稍后）` 这类「短、非精确实例、非强占位」答复被当实质确认（`evidence.py:97-106`）；照搬 asterwynd 两张表的必然结果。
- **`## Open Questions` 内任意 `Q<n>` 文本**（推荐子条、正文交叉引用）都会被当成「须被确认的问题」（`evidence.py:81-82`）；引用一个**未列为问题**的 Q 号会产生假阳性（低概率）。实测 `Q10`/`Q1` 前缀**不**混淆（`\bQ(\d+)\b`，`Q10`→10）。
- 实测「一条 `来源:` 放行三条」**不成立**（`_blocks` 使每条 bullet 各自需命中 `来源:`，`evidence.py:67-78,129-133`）。

### Issue 7（低）— README 未提「对**接入方**是行为变更」

`design.md` D9 要求「README/gate.md 写明」，`docs/gate.md:302-303` 有「⚠️ 对**接入方**是行为变更」；但 `README.md` 只加了 `guard` 用法与诚实边界，**未**提「历史无 `stage=grill` manifest 的 change 会新增一条红」。建议 README 补一句。

### Issue 8（信息）— 基线假象：`main..HEAD` 含 4 个提交

任务称「3 个提交」，实测 `git log main..HEAD` 为 **4 个**（含 `442a2f7 dogfood-bootstrap (#8)`）。本仓 `main`（`843b691`）落后于 #8，故按 `--base main` 跑 `check` 会把 #8 的改动一并纳入，并对 `dogfood-bootstrap` 的 3 份 manifest 报「`head_sha=893597…` 不是被检 revision 的祖先——审阅的是别的 revision」（**base 假象**，非本 change 缺陷）。建议：审本 change 时把 base 钉在 `442a2f7`，或先把 #8 合入 `main`。

## 冗余度 / 可维护性 / 安全性 / CI 完整性

- **冗余度**：evaluator 单一实现、被 `check`（`checkcmd.py:78-84`）与 `guard`（`guardcmd.py:103-108`）共用（`evidence.grill_evidence_findings_in_change`），未发现与既有模块重复的判定。`_read_json`（`evidence.py:158-162`）为小工具，可接受。
- **可维护性**：模块边界清晰（`evidence` / `guardcmd` / `checkcmd`），命名与既有风格一致；`constants.EXIT_BLOCKED` 与 `EXIT_USAGE` 同值一事已在注释（`constants.py:85-88`）与 `gate.md §6` 显式记载。
- **安全性**：`guard` 无状态、不改任何文件；`WITNESSLOOP_SKIP_GUARD` 只影响 hook 那个**外层进程**——会话内 agent 的 `export` 改不了它（`guardcmd.py:76-77` 的注释与 design D8 一致）。真实绕过面（Bash 写文件 / 不装 plugin）已在 README/gate.md/ADR **诚实写明**。
- **CI 完整性**：`442a2f7..HEAD` **未触碰** `.github/workflows/**`，无删步骤、无放宽断言、无 `continue-on-error`。自伤面（`test_cli`/`test_plugin`）已同步（F1/F2）。

## 结论

实现质量高、核心行为实测正确、文档与守卫同步到位；**回归红线（dogfood-bootstrap 仍合格）成立**。需修的是**测试与承诺的对齐**（Issue 1/2）与**旧版 CLI 下的误拦反转**（Issue 3），以及若干文档/边界的小项。按 `review-loop` 第 5 步：逐条修复、每个修复补一条**能变红**的回归测试、在 `tasks.md` 追加「审阅修复」节，再进入第 2 轮审阅。

## 第 2 轮审阅

- 时间: 2026-10-11T13:18:54Z
- 裁定: **PASS**
- 基线/revision: `git merge-base HEAD main` = `843b691`；被审修复提交 `e425f63..0d41b73`（change 本体 `16815c5`/`1fa4219`/`e425f63`）。
- 实测命令: `export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q` → **388 passed in 67.15s**（第 1 轮 380 → +8，恰为新补测试：`test_check_grill_evidence.py` 3 条 + `test_guard.py` 1 条 env + 4 条 shim）。

### 逐条核验（Issue 1–8，全部**实测**：变异测试证其能变红）

- **Issue 1 — 已落实。** 新增 `tests/test_check_grill_evidence.py`，三条用例**逐条变异验证**：
  - 注释掉 `checkcmd.py:78-84` 的正文校验接线 → `test_check_red_when_the_grill_report_body_is_incomplete` **红**（`AssertionError` @ `:27`）。
  - 从 `REVIEW_MANIFEST_REQUIRED_FIELDS`（`constants.py:67`）删 `"stage"` → `test_check_red_when_the_stage_field_is_missing` **红**（`AssertionError` @ `:42`）。
  - 把 `evidence.py:199` 的文案「现有 stage：」改成别的 → `test_check_names_the_existing_stage_so_a_typo_is_diagnosable` **红**（`AssertionError` @ `:53`）。
  三条均断言真实行为，**非恒真**。
- **Issue 2 — 已落实。** `tests/test_guard.py:88` `test_change_env_overrides_the_branch`（`monkeypatch.setenv("WITNESSLOOP_CHANGE", "add-x")`、分支 `feature` 推不出）。实测：把 `CHANGE_ENV` 从 `guardcmd.py:53` 的 candidates 删掉 → 该用例 **红**（`assert 0 == 1`）。
- **Issue 3（本轮重点）— 已落实，且真堵住了误拦。**
  - `constants.py:88` 的 `EXIT_BLOCKED` **已撤**（全仓 `grep EXIT_BLOCKED` 仅命中本报告的历史记述，无源码/活文档引用）。
  - `guardcmd.py:129` 的「拦」改为 `C.EXIT_FAIL`(1)；`plugin/hooks/guard.sh:38-41` 把 **1 → CC 的 2**、**其余一律 exit 0**。
  - 补 4 条 shim 回归测试；**变异验证**：把 `guard.sh` 改回直传（`exit "$status"`）→ `test_shim_maps_guard_block_to_the_hosts_block_code`、`test_shim_does_not_treat_a_stale_cli_usage_error_as_block`、`test_shim_allows_when_the_cli_is_missing` **全红**（3 failed）。即「2 = 旧版 CLI 用法错误」**真被映射成放行**。
  - **真机端到端**：本机 `/home/happy/.local/bin/witnessloop` 是旧版 **0.1.0（无 `guard` 动词）**，`guard` 退 2；经 shim → **exit 0（放行）**，不再是「每个 Write/Edit 全被拦」。二进制缺失（PATH 无 witnessloop）→ shim **exit 0**。真拦场景（已接入仓 + change 目录在 + 无 grill 证据）→ `guard` 退 **1**（非 2），stderr 给出可诊断理由。
- **Issue 4 — 已落实（文档）。** `docs/gate.md:315-316` 点明「`--path` 传**文件**；传目录（如 `--path src`）不命中 `src/**` ⇒ 静默放行（声明的 fail-open 边界）」。`docs/gate.md:81-82` 既有归一化边界与 §8 交叉引用齐备。
- **Issue 5（并入 Issue 4/6 修复）— 已落实（文档）。** `docs/gate.md:316`「大小写**不折叠**同理」。
- **Issue 6 — 已落实（文档）。** `src/witnessloop/evidence.py:114-116` docstring 新增「**已知宽松面**」小节，点明空 `## Open Questions` **空真通过** + 占位启发式的短答复空隙（第 1 轮建议的「gate.md §8 或 docstring」二选一，取 docstring）。
- **Issue 7 — 已落实。** `README.md:93-104` 新增「### 本地守卫与行为变更」，含 `⚠️ **对**接入方**是行为变更**`（历史缺 `stage=grill` manifest 的 change 会**新增一条红**）。
- **Issue 8 — 已落实。** `tasks.md:72` H6 记下本地 `main` ref 落后于 #8 的基线假象，建议用 `--base origin/main`。实测 `git rev-parse origin/main` = `442a2f7`（**含 #8**）⇒ 该建议确实能避开假象。

### 一致性核验

- `design.md:81` D5、`specs/evidence-gate/spec.md:53-56`、`docs/gate.md:273/277`（§6 表 + §8）、`guardcmd.py:7` docstring **口径统一**：`guard` 拦 = **1**（0 放行 / 1 拦 / 2 用法 / 3 未接入）。
- 活文档**无残留「拦 = 2」**。仍出现的 `exit 2` 有三处，均**非缺陷**：(a) `design.md:30`、`spec.md` 旁注讲的是 **CC 宿主 hook 的 block 约定**（D6，仍成立）；(b) change 自己的 grill 记录（`reviews/grill-review.md:48`、`grill-adversarial.md:68`）是**历史证据、且被 grill manifest 的 `report_hash` 绑定**——改它会令本 change `check` 报 hash 不匹配，**不应改**；D5 的 2→1 变更已由 `design.md:82-85` 的「⚠️ R1 修复」注记显式记录。
- 无删/弱化测试：`git diff e425f63 0d41b73 -- tests/` 仅 **+122 行**（`EXIT_BLOCKED`→`BLOCKED=C.EXIT_FAIL` 属跟随实现的正确改名），无删用例、无放宽断言。
- **CI 完整性**：`e425f63..0d41b73` **未触碰** `.github/workflows/**`。

### 新问题（低，不阻塞）

- **[低] 崩溃 → fail-closed 的残余面。** `cli.main`（`cli.py:136`）无顶层异常兜底，`guardcmd.run` 抛未捕获异常时 Python 以 **1** 退出，而 shim 把 **1 当「拦住」** ⇒ 崩溃会被映射成 block（旧版直传时崩崩溃=1 在 CC 下**不拦**，故本次 2→1 把「崩溃」从 fail-open 翻成了 fail-closed，与 Issue 3 同**类别**，换了个触发源）。实测可达点：`evidence.py:216` 的 `report.read_text(encoding="utf-8")` **未包 try** —— grill 报告含非法 UTF-8 字节 → `UnicodeDecodeError` 回溯、退 1。**为何不阻塞**：该可达崩溃恰发生在「正在校验 grill 报告」的场景，**block 本就是正确结果**（判定与崩溃同向）；唯一能构造「正确=放行却崩溃=拦」的路径（如 `git` 不在 PATH，`gitutil._run` 的 `subprocess.run` 抛 `FileNotFoundError`）过于人为，且 guard 的**判定本身正确**。**建议（后续，非本 change）**：给 `guardcmd.run`（或 `cli.main`）加一层「未预期异常 ⇒ 返回非 1 的错误码」兜底，使 shim 侧 fail-open；并给 `evidence.py:216` 的读取加 `OSError/UnicodeDecodeError` 处理。

### 结论

第 1 轮 8 条 issue（含关键的 Issue 3 误拦反转）**逐条落实、且每条修复都由能变红的回归测试佐证**——变异测试 3+1+3 例全红、真机旧版 CLI 端到端放行；388 条测试全绿；活文档口径统一为「拦=1」。仅余一条**低severity 的理论残余面（崩溃→block）**，不构成中等以上问题，可在后续 change 处理。**裁定 `PASS`**。
