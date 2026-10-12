# Building review —— 独立实现审阅（change `grill-adversarial-gate` / issue #16）

- **被审 revision**：`573ddc3`（分支 `grill-adversarial-gate/2026-10-12`）
- **base**：`origin/main` = `f77edf0`（`git merge-base HEAD origin/main` 实测同值，分支未落后主干）
- **审阅者**：独立 run、零记忆（本 run 只读被审仓，唯一写入 = 本文件）
- **轮次**：第 1 轮
- **基线**：`uv run pytest -q` ⇒ **429 passed**（与 tasks.md「实测记录」逐条对上）

## Verdict

**PASS**

所有 `[x]` 除 D2 一处**措辞与 diff 不符**（非阻塞，见 N-1）外均有真实实现；核心判定路径经 8 组变异验证**无逃逸**；
`check` 的收尾可绿性、旧 policy 回落、`init` 幂等三条均**独立实测**通过；无阻塞项。
非阻塞共 **8 条**（N-1..N-8）。

---

## 任务逐项验证

### A. 判定本体

**A1 —— `constants.DEFAULT_GRILL_ADVERSARIAL_STAGE` 与既有两条并列、注释写明被 `check` 要求。→ 成立。**
`src/witnessloop/constants.py:60` 定义 `DEFAULT_GRILL_ADVERSARIAL_STAGE = "grill-adversarial"`，位于
`DEFAULT_BUILDING_STAGE`（`:49`）与 `DEFAULT_GRILL_STAGE`（`:53`）之后；注释 `:55-59` 写明触发面
（「与 building **共用同一条**（本次 diff 触及 require_change_for = 落了实现）」）与判据
（「只要求**证据存在**，不解析 verdict 文本、不校验报告正文（空文件亦合格）」）。注释与实现一致
（`checkcmd.py:95-101` 传 `verify_body` 缺省 = `False`，见 `evidence.py:179`）。

**A2 —— `Policy` 字段 + `from_doc()` 缺省回落 + `default_policy_doc()` 写入。→ 成立（后半无回归，见 N-3）。**
字段 `src/witnessloop/policy.py:62`；出厂 doc `:46`；回落 `:120-123`
（`evidence.get("grill_adversarial_stage") or C.DEFAULT_GRILL_ADVERSARIAL_STAGE`）。
**独立实测（旧 policy 缺该键）**：在 `/tmp/rv` 副本加探针用例，`init` 后从 `policy.json` 的
`evidence` 里 `pop("grill_adversarial_stage")`（仓里自己的 `.witnessloop/policy.json` 本就缺该键，
走的就是回落分支），造「`src/` 改动 + 只有 grill/building 证据」⇒
`assert code == EXIT_FAIL` ∧ `"stage=grill-adversarial" in err` ∧ `"现有 stage：" in err` ⇒ **1 passed**。
另实测 `init` 产物：`{'…', 'grill_stage': 'grill', 'grill_adversarial_stage': 'grill-adversarial', 'building_stage': 'building'}`。
`init` 幂等 / 冲突 / 往返用例（`tests/test_init.py::test_init_is_idempotent`、
`::test_init_add_only_conflict_reports_diff_and_refuses`、`tests/test_init_policy.py::test_init_policy_idempotent`
等）在 429 passed 里全绿——新键不改变 `init` 行为（seed 逐字落盘，`read_json(...) == CUSTOM_DOC` 仍成立）。

**A3 —— 只在既有 `if code_hits:` 块内加判定，无第二份实现。→ 成立。**
`src/witnessloop/checkcmd.py:94` 是既有的 `if code_hits:`；新判定在 `:95-101`，building 那条在 `:102-108`，
两条**同形**且都调 `evidence_mod.stage_manifest_findings_in_change`（`evidence.py:172`）。
`grep -rn "grill-adversarial" src/` ⇒ 仅 `constants.py:58,60` 与 `checkcmd.py:89`（注释），
**没有**第二处「什么算代码」或第二个判定实现；`_code_hits`（`checkcmd.py:116-132`）仍是唯一口径。

**A4 —— 6 类用例齐备。→ 成立（9 条，6 类 + 3 条加固）。**
| 类别 | 用例 | 行号 |
|---|---|---|
| 触发红 | `test_red_when_code_changed_without_adversarial_evidence` | `tests/test_grill_adversarial_gate.py:44` |
| 补齐绿 | `test_green_when_adversarial_evidence_present` | `:57` |
| 未触发不要求 | `test_not_required_when_only_the_change_dir_changed` | `:67` |
| 拼错点名 | `test_stage_typo_is_diagnosable` | `:79` |
| 多 change 同 PR（加固） | `test_every_change_in_a_code_pr_must_have_adversarial_evidence` | `:96` |
| stale | `test_changing_the_design_after_the_adversarial_round_is_stale` | `:121` |
| 空正文亦合格（加固） | `test_empty_report_body_is_accepted` | `:151` |
| 轴可覆写 | `test_adversarial_stage_is_configurable` | `:169` |
| 不泄漏 grill 正文判据（加固） | `test_plain_report_without_grill_sections_is_accepted` | `:203` |

### B. 既有用例与脚手架

**B1 —— `commit_evidence` 默认补 stage + 默认报告名对齐真实约定。→ 成立（报告名那半无回归，见 N-4）。**
`tests/helpers.py:222` `stages=("grill", "grill-adversarial", "building")`；`:133-138` 让
`stage="grill-adversarial"` 默认写 `reviews/grill-adversarial.md`。三个 stage 默认名互不相同
（`grill-review.md` / `grill-adversarial.md` / `building-review.md`）⇒ 无文件名冲突。
该默认改动是**载荷**：变异 M5（还原为 `("grill","building")`）⇒ 2 条既有用例变红（见「变异验证」）。

**B2 —— 4 条既有用例只补证据、未放松断言。→ 成立。**
`git diff -U12` 逐条核对：`tests/test_building_gate.py:51`（`test_green_when_building_evidence_present`）、
`:113`（`test_code_change_after_the_review_is_stale`）、`:184`（`test_building_stage_is_configurable`）、
`tests/test_check_protected.py:183`（`test_renaming_with_an_event_is_allowed`）。四处**新增行只有
`write_review(..., stage="grill-adversarial")`**；删除行只有两处 commit message 文案
（`test_building_gate.py` 的 `"内容 + 两份证据"` → `"内容 + 三份证据"`、`"内容 + grill + building 证据"` →
`"内容 + grill + adversarial + building 证据"`）。**没有**断言被删、被放宽或被跳过。

**B3 —— 不适用（Q1 定案「乙」）。→ 成立**（`tasks.md:36` 已划掉并注明）。

**B4 —— 非目标登记。→ 成立**：`design.md:186-190`（D8）列出 archive 门禁 / `ChangeType` / verdict / `guard` /
`require_change_for=[]` warning / 签名六项。

**B5 —— `spec.md` 已按定案替换。→ 成立**：`specs/adversarial-evidence/spec.md:16-21` 触发条件为「触及
`require_change_for` + 复用 `checkcmd._code_hits` 同一口径」；`:33-38` 的 Given 是具体条件（只改文档 / 只动
change 目录）；`:39-44` 多 change 为乙口径；`:98-110` verdict 那条已无「选甲时」限定。全文无待定标记。

**B6 —— 配方纪律。→ 成立（本轮遵守）**：副本先在 `/tmp/rv` 做
`rm -f .git && git init -q && git add -A && git commit -qm base && rm -rf .venv && uv sync`；
被审 worktree 结束时 `git status --porcelain` **空**（未污染、未被切分支）。

### C. 回归

**C1 —— 全量绿。→ 成立**：`uv run pytest -q` ⇒ **429 passed**（19s）。

**C2 —— 其他 active change 不因此变红。→ 成立**：实测 6 个 active change 目录
（`building-review-gate` / `dogfood-bootstrap` / `events-readpoint-fix` / `grill-adversarial-gate` /
`grill-evidence-gate` / `guard-crash-exit`）**每个都有 `reviews/grill-adversarial.manifest.json`**；
且本 PR 的 diff 只触及 `openspec/changes/grill-adversarial-gate/` 一个 change 目录，其余 5 个根本
不进入判定循环。（tasks 写「5 个」，指除本 change 外的 5 个，与实测一致。）

**C3 —— `guard` 行为不变。→ 成立**：`grep -n "grill_adversarial\|grill-adversarial\|building_stage"
src/witnessloop/guardcmd.py` ⇒ **0 命中**；`tests/test_guard.py` 全绿。
spec「guard 不要求对抗轮证据」Scenario 由既有用例
`tests/test_guard.py::test_allows_a_code_write_when_grill_evidence_is_complete`（`:53`）钉住——
它只写 `stage="grill"` 证据、**没有**对抗轮 manifest，断言 `guard` 放行，与 Scenario 逐字对应。

### D. 文档

**D1 —— §6 红项清单加「缺设计对抗轮证据」。→ 成立**：`docs/gate.md:277`（退出码 1 那一行）。

**D2 —— §8 门禁/读点表加一行。→ 不成立**（见 N-1；`tasks.md:77`）。

**D3 —— §9 同族新增小节 + 三条诚实边界并列写死。→ 成立**：`docs/gate.md:390`（新 §10）给出触发面、
与 §9 共用判定（`:404` 判据 + 「**三条诚实边界**」抬头），以及三条边界（`:405-406` ①verdict 不参与判定、
`:407-408` ②只保证证据存在且绑在最终 revision、不保证写码之前、`:409` ③报告正文不校验——空文件亦合格），
末尾 `:423-424` 写明「**没有过渡开关**」。
`:365` 在 §9 补了指向 §10 的交叉引用。

**D4 —— README 对**接入方**的行为变更（具体触发条件 + 三条边界）。→ 成立**：`README.md:112-121`。
触发条件点明「= 本次 diff 命中 `policy.require_change_for`，本仓**含** `templates/**` / `plugin/**`」——
与 `.witnessloop/policy.json` 实测一致（`require_change_for = ["src/**","templates/**","plugin/**"]`）；
三条边界与 §10 **逐条同措辞**；「**不加**过渡开关」在 `:120`。

**D5 —— `templates/grill.md` 产物小节后补一句。→ 成立**：`templates/grill.md:195-200`，写明触发面与
building 相同、判据止于「证据存在」、三条边界、指向 `docs/gate.md §10`。

**D6 —— 不改其他 change 目录的非证据文件。→ 成立**：`git diff origin/main...HEAD --stat` 只列
本 change 目录 + `src/` + `tests/` + `docs/gate.md` + `README.md` + `templates/grill.md`。

### E. 证据链与收尾

**E0 / E0b（已发生的步骤）→ 成立**：`reviews/grill.manifest.json`（stage=`grill`，report_path=`reviews/grill-review.md`）
与 `reviews/grill-adversarial.manifest.json`（stage=`grill-adversarial`，report_path=`reviews/grill-adversarial.md`）
均存在，且两份报告文件都在（两两绑定，无孤儿）。
**E1（`[ ]`，后续批）→ 我实测「能让 check 变绿」**（见下「端到端复现」），manifest 的三份 stage 名 /
报告路径 / `report_path` 与 policy 的 stage 轴一致。
**E2（`[ ]`）** = 本轮即 E2。**E3（`[ ]`）** 超出本审范围。

---

## Issues

### 阻塞

**无。**

### 非阻塞

**N-1（任务验证）D2 标了 `[x]`，但 diff 里没有 §8 的任何改动。**
`tasks.md:77` 声称「§8：门禁/读点表加一行（`stage=grill-adversarial`）」。
实测：base 与 head 的 `docs/gate.md` 章节结构完全相同，**§8 是「grill 证据的正文校验（`check`）与本地
守卫（`guard`）」（`docs/gate.md:315`），里面没有「门禁/读点表」**；§8 唯一的表是「证据『读不出』（解码
失败）的归宿」（`:344-351`），四行分别是 policy / manifest / grill 报告正文 / events——而本门禁
`verify_body=False`（对抗报告**不是**读点）⇒ **该表本就不需要新增行**。
`git diff` 的三个 hunk 分别落在 §6 的退出码表（`:277`）、§9 的触发段（`:365`）、新 §10（`:390`）。
⇒ 实现**没有错**（无遗漏读点），错的是 D2 的措辞与 `[x]`。
**建议**：把 D2 订正为「§9 补一条指向 §10 的交叉引用（`:365`）」，或把交叉引用补在 §8 末尾；
不要为了对上一句任务描述去给 §8 的表硬塞一行（那会写进一个不存在的读点）。

**N-2（注释一致性）`checkcmd._code_hits` 的 docstring 仍只枚举两个消费者。**
`src/witnessloop/checkcmd.py:119-121` 写「`_require_change`（改代码必须挂 change）与本 change 新增的
`building` 门禁**共用它**」——现在有**三个**消费者（`_require_change`、building、grill-adversarial）。
新注释 `:89-93` 已把两者共用的关系写对，但底层 docstring 未同步，读者会以为只有两个。
**建议**：`:119-121` 改为「与 `building` / `grill-adversarial` 两条门禁共用」。

**N-3（测试覆盖）`default_policy_doc()` 写入新键**（A2 后半）无回归钉。
变异 M8：删掉 `policy.py:46` 那行后全量 **430 passed（不红）**。
行为本身正确（实测 `init` 产物含该键），但这意味着「出厂 policy 写出新轴」这条**只能靠读代码**保证。
与 #13 的 N-5 同类。**建议**：在 `tests/test_init.py::test_policy_schema_has_three_sections`（`:37-40`）
的 `set(policy["evidence"]) >= {...}` 里补 `"grill_adversarial_stage"`。

**N-4（测试覆盖）B1 后半（helpers 默认报告名）无回归钉。**
变异 M7：把 `write_review` 的默认名还原成 `reviews/{stage}-review.md` ⇒ 全量 **429 passed（不红）**。
不影响门禁正确性（判定只看 manifest + `report_path` 解析），属脚手架可读性；记录以备将来有人改动
helper 时没有护栏。

**N-5（Spec 对齐）两条 Scenario 只被「更强/间接」覆盖，没有字面用例。**
① `spec.md:107-110`「结论是 `CHANGES_REQUESTED` 也能通过」：测试里**没有**任何对抗报告的正文含
`CHANGES_REQUESTED`（`grep -rn CHANGES_REQUESTED tests/` 只命中 `test_templates.py` 的模板文案断言）。
逻辑上已被 `test_empty_report_body_is_accepted`（`:151`）**严格覆盖**（`verify_body=False` ⇒ 正文一个字节
都不读，`PASS` / `CHANGES_REQUESTED` / 空文件不可区分），故**不算假绿**；但若想让 Scenario 与用例一一对应，
补一条正文字面写 `CHANGES_REQUESTED` 的用例最省事。
② 「对抗轮不要求 grill 式正文」Scenario 的用例 `test_plain_report_without_grill_sections_is_accepted`
（`:203`）**直接调 `evidence.stage_manifest_findings_in_change`**、不走 CLI；变异 M3
（在 `checkcmd` 里把 `verify_body=True`）下**它不红**——真正拦住「正文判据泄漏」的是
`:151` 的空正文用例（M3 下红）。⇒ 该 Scenario 已被覆盖，但这条用例钉的是 helper 的默认值而非接线。
**建议**（可选）：让 `:203` 也走一遍 `check`。

**N-6（断言精度，可选）两处断言可被「别的东西」满足，实测未逃逸。**
① `tests/test_grill_adversarial_gate.py:96` 的
`assert f"changes/{OTHER}" in err and f"stage={STAGE}" in err` 是**两段独立子串**，理论上可被两个不同
finding 各自满足；更紧的写法是断言完整句 `f"changes/{OTHER}：无 stage={STAGE}"`。实测 M1 / M6 下它**确实
变红**，所以**不是**假绿，只是精度可提升。
② `:121` 的 `test_changing_the_design_after_the_adversarial_round_is_stale` 在改 `design.md` 后三份
manifest **同时** stale，断言「审阅的是旧 revision」由任一份满足 ⇒ 它钉的是**共用 span 机制**而不是
对抗那份 manifest。这与 A4 第 5 条的措辞（「复用既有 span 判定，加回归钉住」）**一致**，不算缺陷。
（我实测确证：M1 删掉新门禁后这条**仍绿**。）

**N-7（文档细节）两处枚举/交叉引用滞后。**
① `src/witnessloop/checkcmd.py:93` 的「（见 docs/gate.md §9）」——新门禁的正文在 **§10**（§9 是 building）。
② `docs/gate.md:72-74` 的逃生面说明仍写「`require_change_for` 为空时『改代码必须挂 change』与**本节的
building 门禁**一并静默失效」——现在是**三条**规则（spec `spec.md:114` 的边界声明 1 已写全三条）。
不影响行为，属文案同步。

**N-8（引用漂移）`spec.md:19` 的 `checkcmd.py:106-122` 在实现后已不成立——它现在指向**新门禁块**。**
实测（`git show origin/main:src/witnessloop/checkcmd.py` vs 工作区）：base 里 `_code_hits` 的 `def` 在
`checkcmd.py:106`、`_require_change` 在 `:125` ⇒ 设计冻结时该引用**是准的**；本 change 自己的 diff 让
`_code_hits` 位移到 `:116-132`（新 `def` 在 116），于是 `:106-122` 现在落在「新注释 + `if code_hits:` +
grill-adversarial 判定块 + `_code_hits` 前半」上——读者按引用跳过去会看到**另一段代码**。
同类漂移：`design.md:23-26` 与 `:282` 的 §1.1 行号（`83-88/91-98/125-145/148-206` ⇒ 现为
`83-88/102-108/135-145/158-216`）。
**性质**：`spec.md` 是被 manifest 哈希绑定的 artifact，而**行号引用天然随代码漂移**——这不是实现缺陷。
**建议**：**不要**为一行引用去churn 设计环（会让 E0b 的对抗轮前提作废）。要么在 E1 重建三份 manifest 时
顺带把 `spec.md:19` 的引用**去掉行号**（只留 `checkcmd._code_hits` 这个符号名 ⇒ 永久免疫漂移），
要么至少在 `tasks.md` 的「审阅修复」节登记为已知偏差。

---

## 变异验证

全部在 `/tmp/rv` 副本上做（`cp -a` 后 `rm -f .git && git init && uv sync`，**未动被审 worktree**），
每组变异后还原原文件并复跑确认回到 429 passed。

| # | 变异（改回旧行为 / 制造缺陷） | 结果 | 判定 |
|---|---|---|---|
| M1 | 删掉 `checkcmd.py:95-101` 整块（= 本 change 之前的行为） | **4 红**：`test_red_when_code_changed_without_adversarial_evidence`、`test_stage_typo_is_diagnosable`、`test_every_change_in_a_code_pr_must_have_adversarial_evidence`、`test_adversarial_stage_is_configurable` | ✅ 核心用例钉住实现 |
| M2 | `policy.py` 的 `grill_adversarial_stage` 忽略覆写、恒用出厂默认 | **1 红**：`test_adversarial_stage_is_configurable` | ✅ #13 的 M11（覆写轴被判逃逸）**不再复现** |
| M3 | 新判定传 `verify_body=True`（把 grill 专有正文判据泄漏过来） | **4 红**，含 `test_empty_report_body_is_accepted` | ✅ 诚实边界 ③ 被钉住 |
| M4 | 去掉 `if code_hits:`（触发面变无条件 = 甲案） | **2 红**：本 change 的与 building 的 `test_not_required_when_only_the_change_dir_changed` | ✅ 「未触发不误伤」被钉住 |
| M5 | `helpers.commit_evidence` 默认 stages 还原为 `("grill","building")` | **2 红**：`test_check_protected.py::test_writes_outside_protected_paths_need_no_event`、`test_require_change.py::test_source_change_with_change_dir_passes` | ✅ B1 的默认改动是载荷（且 2 + B2 的 4 = design 实测的「不改 helpers ⇒ 6 red」，数字自洽） |
| M6 | 新判定的 stage 轴接错成 `pol.building_stage` | **4 红**（同 M1 那 4 条） | ✅ 轴接线被钉住 |
| M7 | `helpers.write_review` 默认报告名还原为 `reviews/{stage}-review.md` | **429 passed（不红）** | ⚠️ 无回归 ⇒ N-4 |
| M8 | `default_policy_doc()` 删掉 `grill_adversarial_stage` | **430 passed（不红）** | ⚠️ 无回归 ⇒ N-3 |

对照组：每次变异前/后均在副本上跑基线确认 429（M8 时 430，因副本里多了我的探针用例，探针随后删除）。

---

## 测试与端到端复现

1. **全量**：`uv run pytest -q` ⇒ `429 passed in 19.13s`。
2. **`check` 在当前 revision 上的红是预期的**（未收尾）：`witnessloop check --root . --base origin/main --head HEAD`
   ⇒ 退 1，**恰好 5 条**：`grill-adversarial.manifest.json` 的 `tasks_hash 不匹配` + `审阅的是旧 revision`、
   `grill.manifest.json` 的同两条、`无 stage=building 的 manifest（现有 stage：grill, grill-adversarial）`。
   形状与 tasks.md「实测记录」的「属预期」描述一致（**不列为 issue**）。
3. **收尾可绿性（E1 可行性）独立实测**：在 `/tmp/e1`（`git clone` 出来、`origin/main` 指向 `f77edf0` 的副本）按
   `templates/review-loop.md §6` 的顺序做——写 `reviews/building-review.md` ⇒ 对
   `grill` / `grill-adversarial` / `building` 三个 stage 各跑一次 `manifest build --base origin/main`
   ⇒ `git commit` 证据提交 ⇒ `check --base origin/main --head HEAD` ⇒ **`check：通过 ✓`，exit 0**。
   ⇒ 三份 stage 名、报告路径、`report_path` 与 policy 的 stage 轴**一致**，收尾步骤**能**让 `check` 变绿
   （另实测：证据提交落 `reviews/**` 属 `stale_exempt_paths`，不会把刚建的 manifest 判 stale）。
4. **旧 policy 回落**：见 A2 探针，**1 passed**。
5. **`init` 产物**：含 `grill_adversarial_stage: "grill-adversarial"`，且 `init` 幂等/冲突/往返用例全绿。
6. **`guard` 不受影响**：`guardcmd.py` 0 命中，`tests/test_guard.py` 全绿。

---

## 结论

核心判定路径（`if code_hits:` 内复用 `stage_manifest_findings_in_change`）**正确、无重复实现、无新增绕过面**：
触发面与 building 严格同一（M4 证明「不触发」分支真实存在），stage 轴可覆写且有测试（M2 证明 #13 的覆写
逃逸不再复现），判据止于 `verify_body=False`（M3 证明「空文件亦合格」被钉住），`guard` 零改动，
文档三处（`docs/gate.md §10` / `README.md` / `templates/grill.md`）与实现的触发面、判据、三条诚实边界
**逐条一致**，且**没有**「文档承诺但代码没做」的条目。

D2 的 `[x]` 与 diff 不符是**任务描述**的问题而非实现问题（§8 本就无读点要加）；连同 7 条非阻塞观察
（注释枚举滞后 / 两条轴与出厂 doc 无回归 / 两条 Scenario 只被更强用例覆盖 / 两处断言精度 / 两处文案同步 /
spec 行号引用漂移），建议在收尾时按 `templates/review-loop.md §5` 记入 `tasks.md` 的「审阅修复」节——
但**它们都不阻塞合入**。

## 中文简报

**Verdict：PASS**（第 1 轮，无阻塞，非阻塞 8 条）。

判定正确、无第二份实现（`checkcmd.py:94-101` 在既有 `if code_hits:` 内复用共享助手）。独立复现：全量 **429 passed**；当前 `check` 恰 5 条红（属预期）；**收尾可绿**——`/tmp/e1` 克隆副本按 review-loop §6 建 building 报告＋三份 manifest ⇒ `check` **exit 0**；旧 policy 缺新键**回落出厂默认**。

变异 **8 组无逃逸**：删实现 4 红、覆写失效 1 红（#13 的覆写逃逸不再复现）、`verify_body=True` 4 红、触发面改无条件 2 红。两处无回归：出厂 doc 新键、helpers 默认报告名。

唯一不成立：**D2**「§8 表加一行」在 diff 里不存在（§8 无读点表）⇒ 任务措辞不准（N-1）。余 5 条非阻塞：注释枚举滞后、`spec.md:19` 行号漂移、两 Scenario 仅间接覆盖、断言精度、文案同步。
