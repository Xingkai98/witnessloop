# Tasks: archive-awareness

> 依据 `design.md`（grill + 对抗轮已回写；**用户 2026-10-15 已停轮裁定：Q1 = uniform、Q2 = 不收紧** ⇒ 可进入实现）。
> 原则：**测试先行（TDD）**；判定面小（两个纯函数 + 三处接线），用例密集在**对称性**与**否定用例**上。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/archive-awareness/spec.md`）。
> ⚠️ **动手前先读 `design.md §1.5 / §1.6 / D8**（三条连锁 + 正确顺序 + 别名）：
> 本 change 曾把顺序写反（「归档后重建」在同一 diff 里跑不通）——对抗轮实测证伪，别再照抄旧说法。

## A. 契约层：change 集合的归档维（D1/D2/D7/D8）

- [ ] A1 单测（先红）：`contract.change_targets(root, pol, changes)` 对「归档 move + 代码改动」的 diff
      返回**非空**集合；归档项 `id` = **归档目录名**（`archive/<name>/` 的 `<name>`，**不解析日期前缀**）、
      `label` = 仓根相对真实路径（`openspec/changes/archive/<name>`）
- [ ] A2 单测（先红）：`archive` **本身**永不作为 id；搬走的 active 源**不再**按 active 校验
      （即 `changes/<id>` 不出现在集合里——否则报「change 目录不存在」）
- [ ] A3 实现：`changed_change_ids` 增归档维（或并列的 `archived_change_ids`）+ `archived_change_dir`
      + `change_targets`。⚠️ `is_archive_move`（`contract.py:38-55`，`:45` 那条 `status != "R100"`）
      **一行都不改**——它是防伪造的锚
- [ ] A4 单测（回归）：`is_archive_move` 的既有语义不变（R100 / 带走改动不算 / 源不能本来就在 archive）
- [ ] A5 实现 + 单测（**先红·D2 第 2 条**）：授予资格还要**目标目录名认得源 id**
      （`<name> == <源id>` 或 `<name>.endswith("-" + <源id>)`，源 id 取旧路径 `changes_root/` 之后的首段）。
      用例：`archive/add-retry`（等值）与 `archive/2026-10-14-add-retry`（后缀）**授予**；
      `git mv changes/z/notes.md → changes/archive/y/notes.md`（`y` 既不等于也不以 `-z` 结尾）**拒绝**
      （本仓实测：该 diff 是 `R100`、`is_archive_move=True`、今天 `changed_change_ids=[]`）
- [ ] A6 单测：拒绝的形态要**回落到今天的行为**（不授予 ⇒ 集合为空 ⇒ `_require_change` 照样命中），不是静默放行
- [ ] A7 实现 + 单测（**先红·D8 别名**）：归档 target 的 `change_id` **接受两个名字** `{归档目录名, 源 id}`
      （`contract.py:250` 的比对改成「∈ 接受集合」——**只改这一处、只加这一个参数**）。
      用例：① 用源 id build 的 manifest（`change_id="gwa"`）在 `archive/2026-10-14-gwa/` 下 **通过**；
      ② 用归档目录名 build 的也通过；③ **别的** change id（如 `"other"`）仍被判「与目录不符」（别名不是放开）
- [ ] A8 单测（**先红·D7 tie-break**）：构造「同 PR 内同名 move + 新增 active 子文件」的 diff
      （实测 `changed_change_ids` 今天 = `['x']`、授予也指向 `x`）⇒ `change_targets` 返回**两条**（列表、以目录为键）、
      **两份都校验**；断言**不出现**「只校验一份 / 静默丢一份」（**不许** `dict[id]=dir`）

## B. `check` 侧：按归档路径跑同一套校验（D2/D3/D7/D8）

- [ ] B1 实现：`checkcmd.run`（`:73-110`）的循环换成 `change_targets` 的三元组；
      三处 `contract.change_dir(...)`（`:86`/`:98`/`:105`）改用**解析后的目录**；
      `validate_change_dir` / `validate_review_manifests` 收 `directory` + `label` + **`accepted_change_ids`**（D8）
- [ ] B2 实现：`_require_change`（`:188-208`）**不加**「有归档 move 就放行」的分支（D3）——它由 B1 自动修好；
      仅改文案（提一句「本次 diff 里也没有归档 move」）
- [ ] B3 单测（**先红·症状 ①，fixture 必须写全**）：**能绿的形态** = base 里 change 已是 active（提案态）、
      本 PR「① 改代码 → ② **在 active 态** build 证据（绑 ①）→ ③ 归档 move 放最后、纯 R100」
      ⇒ 修后 **`EXIT=0` / 0 项红**（本仓实测）。
      ⚠️ **不要**写成「base 证据齐备 + 本 PR 归档 + 改 `src/` ⇒ EXIT_PASS」——那个字面 fixture 实测 **3 项红**
      （既有的「审阅的是旧 revision」，`docs/gate.md §3.1`），**今天红、修后仍红**（对抗轮 M2）
- [ ] B4 单测（**先红**·防绕过钉子 R1）：归档 + 改 `src/`、归档 change **零 manifest** ⇒ 红，
      且 stderr **同时**含「缺少 review manifest」「无 stage=grill」「无 stage=grill-adversarial」「无 stage=building」
      （今天只有 `_require_change` 那 1 项——这条用例就是 `design.md §1.2` 的 C1b/C3 对照的机械化）
- [ ] B5 实现（依 R6）：`_report` 打印归档 change（标注 active / 归档）。
      ⚠️ `tests/test_check_contract.py::test_change_outside_changes_root_is_ignored` 断言 `"0 个 change 目录" in out`
      ⇒ **建议保留该子串**（成本最低）；要改文案就**同步**改那条测试（不许悄悄改）

## C. `manifest build`：归档目标（D1/D4/D5/D8）

- [ ] C1 单测（**先红**·症状 ②）：`--change <归档目录名> --stage building --report reviews/building-review.md`
      ⇒ `EXIT=0`，manifest 落在 `openspec/changes/archive/<name>/reviews/building.manifest.json`
- [ ] C2 单测（先红·往返）：C1 产出的 manifest ⇒ 随后 `check` 认它（**hash 绑定在归档目录上成立**）
- [ ] C3 实现：`--change X` 解析 = active `<changes_root>/X` → 否则 `archive/X` → 否则报错；
      `manifest_rel` 由**解析后的目录**推（`manifestcmd.py:149` 是硬编码点）；
      `--report` 相对**解析后的目录**解析（`resolve_report_path` 本来就吃目录）；
      `manifestcmd.py:64` 的 `is_within(directory, changes_root)` 对归档目标**天然成立**（对抗轮复核）
- [ ] C4 实现：`archive/` 下存在 `*-X` 时，报错文案**提示**候选、**不自动认**（否则就是猜——§2.6 的 CQ1）；
      另兜一句 `--change archive`（`archive` 本身是目录 ⇒ 会走 active 分支报「缺少必需件 proposal.md」）的困惑
- [ ] C5 单测（回归）：`--change <unknown>` 仍报错且点名该 id（`test_unknown_change_is_rejected`）；
      含 `/` / 绝对路径 / `..` 三种写法仍被拒（单段 + containment 两道守卫各管一类，别合并成一道）
- [ ] C6 决策落地：`tasks_hash` **照算不跳过**（D5）——⚠️ 若实现时发现归档态算不出（如 `tasks.md` 被归档器删了），
      **不要**加特例：那是「非 R100 归档 ⇒ 归档感知不适用」的自洽结果，在 design 里回写一笔即可
- [ ] C7 单测（**先红·别名钉子 D8 / R9**）：证据齐备的 change、用 `--change <源id>` build（`change_id="<源id>"`）
      ⇒ 提交 ⇒ `git mv` 成 `archive/<date>-<id>/`（**纯 R100、不重建**）⇒ `check` **绿**。
      ⚠️ 本仓既有测试用的归档名**与源 id 同名**（`test_archive.py`），**抓不到**这条 ⇒ 它必须显式存在
- [ ] C8 单测（**先红·R12 的后果**）：同一 diff 里 ① 归档 → ② 在归档态重建三份 manifest ⇒ 红，
      且 stderr 含「`openspec/changes/<源id>：change 目录不存在`」（幽灵 active id）。
      实测（修后模拟）：**9 项**（3 幽灵 + 6 受保护写入）；补 3 条事件 ⇒ 6 项；再补旧路径侧 3 条 ⇒ **仍 3 项**
      （幽灵 id **补事件消不掉**）⇒ 这条用例钉的是「别把这个形态当推荐流程」
- [ ] C9 单测（**先红·§1.5 第 3 条**）：归档已在 base（本 diff **不含**该 move），在**新 revision** 上重建三份 manifest
      ⇒ `check` **恰好 3 条**「受保护路径被写入，但没有结构化解释事件」；补三条 `protected_path_write` ⇒ 绿。
      ⚠️ 必须**换 revision**：同一 revision 重复 build 是逐字节幂等的，造不出 `M`

## D. `events`：扫描覆盖归档（D6）

- [ ] D1 单测（**先红**·症状 ③）：归档 change 的 `workflow-events.jsonl` 点名一份受保护写入
      （同 PR 写 `openspec/specs/**`）⇒ `check` **不再**报「受保护路径被写入，但没有结构化解释事件」（今天红）
- [ ] D2 实现：`events.load_all`（`:80-85`）改**两条显式 glob**（active 一层 + `policy.archive_root` 一层）。
      ⚠️ **不要**用 `rglob` / `**`（会吃**再深一层**的同名文件 ⇒ 多出授权面）
- [ ] D3 单测（否定 N5·**方向已订正**）：`<changes_root>/archive/<name>/<sub>/workflow-events.jsonl`
      （**再深一层**）**不**被读。⚠️ **不要**拿 `changes/archive/workflow-events.jsonl` 或
      `changes/archive/notes/workflow-events.jsonl` 当否定面——本仓实测**两者都会被读**（`design.md` D6/R11）
- [ ] D4 单测（回归）：`test_events.py` 全绿（`covers` 语义未动）+ 合法 events 既有行为不变

## E. 否定用例（**必须照样红 / 不生效**——本 change 的主要风险面）

- [ ] E1 **N1**：只改 `src/`、不建任何 change 目录 ⇒ 红（`test_source_change_without_change_dir_is_rejected` 保持绿）
- [ ] E2 **N2**：伪造归档（**新建** `archive/2026-10-14-fake/{proposal,design,tasks,specs}/…`，无 active 源）+ 改 `src/` ⇒ **不生效**、仍红
- [ ] E3 **N3**：**删除** change 目录（非 rename）⇒ 仍报「change 目录不存在」（`test_touched_but_absent_change_dir_is_reported` 保持绿）
- [ ] E4 **N4**：只改 `archive/<name>/` 里**已存在**的文件（`M`）+ 改 `src/` ⇒ 该 change 不进集合、`_require_change` 红
- [ ] E5 **N5**：同 D3（**再深一层**才是真否定面）
- [ ] E6 **N6（第 6 面）**：`git mv changes/<z>/<单个文件> → changes/archive/<y>/<…>`（目标目录**已存在**、名字**不认得** `<z>`）+ 改 `src/` ⇒ **不授予任何资格**、照样红（A5 的钉子）
- [ ] E7 **N7（R12）**：同一 diff 内「move + 改写被 move 的文件」⇒ 红 + 幽灵 active id（同 C8）

## F. 回归面（逐条点名，`design.md §5.2`）

- [ ] F1 `tests/test_archive.py` 6 条全绿（尤其 `test_archiving_a_change_passes_without_events`、
      `test_archived_change_is_no_longer_validated_as_active`）
- [ ] F2 `tests/test_require_change.py` 8 条全绿；`tests/test_check_protected.py` 全绿
- [ ] F3 `tests/test_manifest_build.py` 全绿（尤其 `test_rebuild_without_explicit_ids_is_byte_identical`——
      D1/D8 动了 `change_id` 的来源，**幂等**必须仍然逐字节：对抗轮复核「同一 revision 两次 build 的 sha256 相同」）
- [ ] F4 全量 `uv run pytest -q` 全绿（本 change 前实测基线 = **496 passed**）

## G. 文档

- [ ] G1 `docs/gate.md §5.1`：改写「归档 move 的两端都不计入 active change id」段（现在有**归档维**）；
      边界表照 `design.md §2.5`；**把 D2 第 2 条的命名约定写进文档**（目标目录名须 `<源id>` 或 `-<源id>` 结尾）；
      补 D8 的**别名口径**（`change_id` 两种字面都合法）；两条残留边界各记一句
- [ ] G2 `docs/gate.md §4`：⚠️ **必须改写** `:245-246`「archive/** 下的 events 文件既不会被读、也不提供豁免」
      （本 change 之后**为假**）；补「事件池 = active 一层 + archive 一层、不 dedup」，
      **并照 D6 写准两条既有口径**：`archive/` **直接下**的同名文件今天就会被读；`archive/<任意名>/` 会被当成归档 change 目录
      ——**别写成「只扫真 change 目录」**
- [ ] G3 `docs/gate.md §3.2`：`manifest build` 的归档解析 + **§1.6 的正确顺序** + **D8 别名**
      （归档前的 manifest 不必重建；要改写已归档的 manifest ⇒ 每条一条事件；同一 diff 里 move + 改写 = 红）
      + 「不合格就不写出」清单补两条 + `--change archive` 的兜底提示
- [ ] G4 `docs/gate.md §6`：`check` 退出码 `1` 的列举里补「归档 change 证据缺件」
- [ ] G5 `docs/gate.md §10`：给「本仓**无 archive 门禁**」加限定（指完成度门禁，不是归档感知）
- [ ] G6 `README.md`：归档段 + 「行为变更」段补对**接入方**的变更（归档 PR 现在要求该 change 证据齐备；
      **§1.6 的三步顺序**；`manifest build --change <归档目录名>` 的用法）
- [ ] G7 ⚠️ **改**任一节**文档前先读 `tests/test_docs.py`**（守卫是**按文件整体**扫的，不只 §3.2）：
      它钉着 `docs/gate.md` / `README.md` / `templates/**` / `plugin/**` / `src/witnessloop/cli.py`——
      `IDEMPOTENCY_DOCS`（每个「幂等」要么同句含 `init`、要么 ±2 行内带「固定 base 与 revision」；
      实测 gate.md 的「幂等」在 `:9`/`:52`/`:497`，**§3.2 内 0 处** ⇒ 风险只在**新写**一个「幂等」）、
      `Q3_DOCS`（禁「挡「忘了另开 run」」）、`RUN_ID_DOCS`（「确定性」必须在场）、四条诚实边界关键词与举例。
      改完跑 `uv run pytest -q tests/test_docs.py`

## H. 证据链与收尾

- [ ] H1 实现期**实测**接入方的归档命令在真仓上的 `git diff --name-status` 输出是 **R100**
      （R3 的前提；若不是 R100，停下来回报，别硬上）
- [ ] H2 ✅ **已做（2026-10-15 用户停轮裁定）**：Q1 = **uniform**、Q2 = **不收紧**，逐条写进
      `reviews/grill-design.md`（**追加** `## Open Questions`（Q1+Q2）+ `## User Confirmation`；
      **审阅者原正文一字未改**，`git diff` 只有新增行）。
      ⚠️ **实现期踩坑记录（重要）**：本仓 checker 按**逐字标题**取小节
      （`evidence.OPEN_QUESTIONS_TITLE = "Open Questions"`）⇒ 审阅者原标题带括号时那条规则**空真**
      ⇒ 追加的小节标题必须逐字。直调结果 `grill_evidence_findings ⇒ 0 条`；反证（拿掉 Q2 的确认）
      ⇒ 报 `Open Question Q2 未经用户确认`（规则确实在跑）。
      实现期在内容提交后跑 `manifest build --stage grill` 放行 `src/**` → **必须重跑**（否则 stale）
- [ ] H3 （收尾，在 build 证据**之后**）两段提交 + `manifest build`（grill / grill-adversarial / building）+ `check` 绿
- [ ] H4 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] H5 （收尾）PR（branch protection）→ 合入 → 关 issue **#21**
- [ ] H6 ⚠️ 本 change 的实现 PR **不要顺带归档别的 change**（R5：那会让被归档的 change 按今天的规则被校验），
      也**不要在同一个 diff 里既归档又改写被归档 change 里的任何文件**（R12：幽灵 active id）
- [ ] H7 **后续（不阻塞本 change，也不由本 change 开 issue）**：「归档命名要不要统一成 `archive/<id>`」
      ——§8 的 Q2 已裁定**不收紧**；若日后要统一，**另立 change/issue**（迁移成本见 §8 Q2：80 个目录 ≈ 240 条事件）。
      本 change 只负责在 `docs/gate.md §5.1` 写明「授予判据接受 `-<源id>` 后缀」这条**现有约定**。

## 明确不做（本 change）

asterwynd 式归档完成度门禁 · 日期前缀解析 · **收紧归档命名为 `archive/<id>`**（§8 Q2 **已裁定不收紧**；「归档命名要不要统一」**另立 change/issue**，本 change 不开）·
change ↔ 代码路径归属 · `guard` 的归档支持（已知缺口）· events 去重/索引 · 签名/防伪造 · 改 `check` 退出码语义。

## 实测记录（立项期，基线 `ae99256`）

- 三条症状**全部在本仓当前树复现**（真 git 仓 + `uv run witnessloop`，命令与输出见 `design.md §1`）；
  行号**未漂**（`contract.py:34/58-86`、`checkcmd.py:188`、`events.py:83`）。
- 新增实测（issue 未写）：**归档使三条证据门禁静默失效**（C1b-A 6 文件/4 项红 vs C3 6 文件/1 项红；
  C1b-B 无 `reviews/` 目录 = 5 文件/5 项红）——两个变体都可从干净检出重跑。
- 反向对照：把归档目录搬回 active，`manifest build` 同参数 `EXIT=0` ⇒ 症状 ② 的成因确定是**路径解析**，不是别的。
- glob 实测：`openspec/changes/*/workflow-events.jsonl` 在本仓复现仓里 **hits=[]**；两层模式命中归档那份。
- 全量测试基线：**496 passed**（`uv run pytest -q`）。
- ⚠️ 立项期**未**改动任何 `src/`（本文的 `[ ]` 全为空是刻意的：实现留给实现环节）。

## 实测记录（grill 回写期，同一基线 `ae99256`）

grill（独立零记忆审阅者）在隔离副本里重跑了全部对照；**作者侧**逐条复核了它的「必须修改项」：

- **M5 复核**：C1b-A（`reviews/` 里有实体文件）= 6 文件 / **4** 项红；C1b-B（无 `reviews/` 目录）= 5 文件 / **5** 项红
  ⇒ 初稿那行「5 文件 + 4 项」**只在工作树里有未跟踪的空 `reviews/` 目录时成立**，已改成两个可重跑变体。
- **M2a 复核**：`--change gwa` 归档前 build ⇒ `change_id="gwa"`；`git mv` 成 `archive/2026-10-14-gwa/` 后
  按 D2 的 label 喂**现有**校验器 ⇒ **1 条**「`manifest.change_id='gwa' 与目录不符`」。
- **M1 复核（第 6 面）**：`git mv changes/z/notes.md → changes/archive/y/notes.md` ⇒ `git diff` = **R100**、
  `is_archive_move=True`、今天 `changed_change_ids=[]`、D2 派生的 id = `y`（源 = `z`）；
  D2 第 2 条（等值 / `-<源id>` 后缀）**拒绝**它 ⇒ 回落到今天的行为（A5/E6 钉住）。
- **M3 复核**：`changes/archive/workflow-events.jsonl` **会**被 active 那条 glob 读到（`*` 匹配 `archive`）；
  `changes/archive/notes/workflow-events.jsonl` **会**被新 glob 读到（`notes` 被当成归档 change 目录）；
  真正不被读的是 `archive/<name>/<sub>/workflow-events.jsonl`（再深一层）⇒ N5 已订正。
- **M4 复核**：`code-gated` **同样**闭合 §1.2 的绕过口（C3 的 `code_hits` 非空）⇒ §8 Q1 的推荐理由已改。

## 实测记录（对抗轮回写期，基线 `4bd6ad0`）

对抗轮（R1）判 **CHANGES_REQUESTED**（不推翻方案方向）；**作者侧**逐条复现了它的阻塞项（均在 `/tmp` 隔离仓）：

- **阻塞①（M1）复现**：同一 PR 内「归档 + 用归档目录名重建 manifest」⇒ git 把三份 manifest 报成
  **`R075/R077`**（不再是 R100）⇒ ①不授予 ②被搬走的 `gwa` **以幽灵 id 回到集合**（`2 个 change 目录`）
  ③事件需求翻倍。实测（含 D8 别名的修后模拟）：**① 只归档 = 0 项 → ② 重建后 9 项 → ③ 补 3 条事件 6 项 →
  ③b 再补旧路径侧 3 条 = 3 项（幽灵 id 补事件也消不掉）**。
  ⇒ 定案：**别名 D8**（不重建）+ **§1.6 的顺序**（move 放最后）+ **R12/N7**（禁止同一 diff 内改写被 move 的文件）。
- **阻塞②（M2）复现**：「base 证据齐备 + 本 PR 归档 + 改 `src/`」的字面 fixture ⇒ 修后 **3 项红**
  （全是既有的「审阅的是旧 revision」）⇒ B3/spec 的 Scenario 已按「能绿的形态」重写。
  另实测**能绿**的主路径（§1.6）：`EXIT=0`、0 项红，11 个变更文件（3 份 manifest 是 `A`、其余 `R100`）。
- **阻塞③（M3）复现**：构造出「同 PR 内同名 move + 新增 active 子文件」的 diff
  （今天 `changed_change_ids = ['x']`、授予也指向 `x`）⇒ D7 定死「列表、以目录为键、两份都校验」。
- **§1.5 第 3 条复核**：归档已在 base 时，在新 revision 上重建三份 manifest ⇒ **恰好 3 项**；补三条事件 ⇒ **绿**。
- **与对抗报告的两处不同**：① 它推荐的「拆两个 check 区间」**不足以变绿**（归档那个 PR 仍因 `change_id` 不符
  红——它自己 §2.2 的实测正是 6 项里含 3 项 `change_id`）⇒ 真正解决它的是**别名 D8**，本稿已采纳；
  ② 它算的 Q1 例子「uniform ⇒ 4 项红」在 **D8** 之下是 **1 项**（3 项 `change_id` 已被别名吸收）。
- 基线：`uv run pytest -q` = **496 passed**（与本 change 前一致）。
