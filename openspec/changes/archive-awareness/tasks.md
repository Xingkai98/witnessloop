# Tasks: archive-awareness

> 依据 `design.md`（草稿——grill 已回写；**对抗验证收敛 + 停轮项 Q1 确认前不得写实现代码**）。
> 原则：**测试先行（TDD）**；判定面小（两个纯函数 + 三处接线），用例密集在**对称性**与**否定用例**上。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/archive-awareness/spec.md`）。
> ⚠️ **两条连锁先读一遍再动手**（`design.md §1.5`）：①归档目录名 ≠ 源 id 时既有 manifest 判「与目录不符」；
> ②重建 = `M` 不变集路径 ⇒ 每条要一条解释事件。**补救顺序是「先归档 → 再用归档目录名重建」。**

## A. 契约层：change 集合的归档维（D1/D2/D7）

- [ ] A1 单测（先红）：`contract.change_targets(root, pol, changes)` 对「归档 move + 代码改动」的 diff
      返回**非空**集合；归档项 `id` = **归档目录名**（`archive/<name>/` 的 `<name>`，**不解析日期前缀**）、
      `label` = 仓根相对真实路径（`openspec/changes/archive/<name>`）
- [ ] A2 单测（先红）：`archive` **本身**永不作为 id；搬走的 active 源**不再**按 active 校验
      （即 `changes/<id>` 不出现在集合里——否则报「change 目录不存在」）
- [ ] A3 实现：`changed_change_ids` 增归档维（或并列的 `archived_change_ids`）+ `archived_change_dir`
      + `change_targets`。⚠️ `is_archive_move`（`contract.py:38-55`）**一行都不改**——R100 + 源必须在 active 是防伪造的锚
- [ ] A4 单测（回归）：`is_archive_move` 的 6 条既有语义不变（R100 / 带走改动不算 / 源不能本来就在 archive）
- [ ] A5 实现 + 单测（**先红·D2 第 2 条**）：授予资格还要**目标目录名认得源 id**
      （`<name> == <源id>` 或 `<name>.endswith("-" + <源id>)`，源 id 取旧路径 `changes_root/` 之后的首段）。
      用例：`archive/add-retry`（等值）与 `archive/2026-10-14-add-retry`（后缀）**授予**；
      `git mv changes/z/notes.md → changes/archive/y/notes.md`（`y` 既不等于也不以 `-z` 结尾）**拒绝**
      （本仓实测：该 diff 是 `R100`、`is_archive_move=True`、今天 `changed_change_ids=[]`）
- [ ] A6 单测：拒绝的形态要**回落到今天的行为**（不授予 ⇒ 集合为空 ⇒ `_require_change` 照样命中），不是静默放行

## B. `check` 侧：按归档路径跑同一套校验（D2/D3/D7）

- [ ] B1 实现：`checkcmd.run`（`:73-110`）的循环换成 `change_targets` 的三元组；
      三处 `contract.change_dir(...)`（`:86`/`:98`/`:105`）改用**解析后的目录**；
      `validate_change_dir` / `validate_review_manifests` 收 `directory` + `label`
      （⚠️ `contract.py:250` 的交叉校验取 **label 末段** ⇒ 归档态取的正是归档目录名；
      **但这只在 manifest 也按归档目录名重建过时自洽**——见 C7 与 `design.md §1.5`）
- [ ] B2 实现：`_require_change`（`:188-208`）**不加**「有归档 move 就放行」的分支（D3）——它由 B1 自动修好；
      仅改文案（提一句「本次 diff 里也没有归档 move」）
- [ ] B3 单测（**先红**·症状 ①）：归档 + 改 `src/`、归档 change **证据齐备** ⇒ `EXIT_PASS`（今天 1 项红）
- [ ] B4 单测（**先红**·防绕过钉子 R1）：归档 + 改 `src/`、归档 change **零 manifest** ⇒ 红，
      且 stderr **同时**含「缺少 review manifest」「无 stage=grill」「无 stage=grill-adversarial」「无 stage=building」
      （今天只有 `_require_change` 那 1 项——这条用例就是 `design.md §1.2` 的 C1b/C3 对照的机械化）
- [ ] B5 实现（依 R6）：`_report` 打印归档 change（标注 active / 归档）。
      ⚠️ `tests/test_check_contract.py::test_change_outside_changes_root_is_ignored` 断言 `"0 个 change 目录" in out`
      ⇒ 要么保留该子串，要么**同步**改那条测试（不许悄悄改）

## C. `manifest build`：归档目标与重建顺序（D4/D5/§1.5）

- [ ] C1 单测（**先红**·症状 ②）：`--change <归档目录名> --stage building --report reviews/building-review.md`
      ⇒ `EXIT=0`，manifest 落在 `openspec/changes/archive/<name>/reviews/building.manifest.json`
- [ ] C2 单测（先红·往返）：C1 产出的 manifest ⇒ 随后 `check` 认它（**hash 绑定在归档目录上成立**）
- [ ] C3 实现：`--change X` 解析 = active `<changes_root>/X` → 否则 `archive/X` → 否则报错；
      `manifest_rel` 由**解析后的目录**推（`manifestcmd.py:149` 是硬编码点）；
      `--report` 相对**解析后的目录**解析（`resolve_report_path` 本来就吃目录）
- [ ] C4 实现：`archive/` 下存在 `*-X` 时，报错文案**提示**候选、**不自动认**（否则就是猜——§2.6 的 CQ1）；
      另兜一句 `--change archive`（`archive` 本身是目录 ⇒ 会走 active 分支报「缺少必需件 proposal.md」）的困惑
- [ ] C5 单测（回归）：`--change <unknown>` 仍报错且点名该 id（`test_unknown_change_is_rejected`）；
      含 `/` / 绝对路径 / `..` 三种写法仍被拒（单段 + containment 两道守卫各管一类，别合并成一道）
- [ ] C6 决策落地：`tasks_hash` **照算不跳过**（D5）——⚠️ 若实现时发现归档态算不出（如 `tasks.md` 被归档器删了），
      **不要**加特例：那是「非 R100 归档 ⇒ 归档感知不适用」的自洽结果，在 design 里回写一笔即可
- [ ] C7 单测（**先红·R9 的钉子，本仓实测**）：证据齐备的 change，**归档前** `--change <源id>` build 出 manifest
      ⇒ 提交 ⇒ `git mv` 成 `archive/<date>-<id>/` ⇒ `check` **红**且点名
      「`manifest.change_id='<源id>' 与目录不符`」；改成「**先归档 → 用归档目录名重建**」⇒ 绿。
      ⚠️ 本仓既有测试用的归档名**与源 id 同名**，**抓不到**这条——所以它必须显式存在
- [ ] C8 单测（**先红·§1.5 第 2 条，本仓实测**）：在 base 已有证据的仓上，本 PR 先落一个**新 revision** 的提交、
      再重建三份 manifest ⇒ `check` **恰好 3 条**「受保护路径被写入，但没有结构化解释事件」；
      补三条 `protected_path_write` 事件 ⇒ 绿。⚠️ 必须**换 revision**：同一 revision 上重复 build 是逐字节幂等的，造不出 `M`

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

## F. 回归面（逐条点名，`design.md §5.2`）

- [ ] F1 `tests/test_archive.py` 6 条全绿（尤其 `test_archiving_a_change_passes_without_events`、
      `test_archived_change_is_no_longer_validated_as_active`）
- [ ] F2 `tests/test_require_change.py` 8 条全绿；`tests/test_check_protected.py` 全绿
- [ ] F3 `tests/test_manifest_build.py` 全绿（尤其 `test_rebuild_without_explicit_ids_is_byte_identical`——
      D1 换了 `change_id` 的来源，**幂等**必须仍然逐字节）
- [ ] F4 全量 `uv run pytest -q` 全绿（本 change 前实测基线 = **496 passed**）

## G. 文档

- [ ] G1 `docs/gate.md §5.1`：改写「归档 move 的两端都不计入 active change id」段（现在有**归档维**）；
      边界表照 `design.md §2.5`；**把 D2 第 2 条的命名约定写进文档**（目标目录名须 `<源id>` 或 `-<源id>` 结尾），
      并各记一句两条残留边界
- [ ] G2 `docs/gate.md §4`：⚠️ **必须改写** `:245-246`「archive/** 下的 events 文件既不会被读、也不提供豁免」
      （本 change 之后**为假**）；补「事件池 = active 一层 + archive 一层、不 dedup」，
      **并照 D6 写准两条既有口径**：`archive/` **直接下**的同名文件今天就会被读；`archive/<任意名>/` 会被当成归档 change 目录
      ——**别写成「只扫真 change 目录」**
- [ ] G3 `docs/gate.md §3.2`：`manifest build` 的归档解析 + **归档后的重建顺序（含重建要写解释事件）**
      + 「不合格就不写出」清单补两条 + `--change archive` 的兜底提示
- [ ] G4 `docs/gate.md §6`：`check` 退出码 `1` 的列举里补「归档 change 证据缺件」
- [ ] G5 `docs/gate.md §10`：给「本仓**无 archive 门禁**」加限定（指完成度门禁，不是归档感知）
- [ ] G6 `README.md`：归档段 + 「行为变更」段补对**接入方**的变更（归档 PR 现在要求该 change 证据齐备；
      归档后 `manifest build` 的用法与**重建顺序**）
- [ ] G7 ⚠️ **改写文档前先读 `tests/test_docs.py`**：`docs/gate.md` / `README.md` 都被它钉着——
      `IDEMPOTENCY_DOCS`（gate.md 里**每个**「幂等」要么讲 `init`、要么 ±2 行内带「固定 base 与 revision」；
      **G3 改的正是 §3.2 那个「幂等」密集处**）、`Q3_DOCS`（禁「挡「忘了另开 run」」）、
      `RUN_ID_DOCS`（「确定性」必须在场）、四条诚实边界关键词与举例。改完跑 `uv run pytest -q tests/test_docs.py`

## H. 证据链与收尾

- [ ] H1 实现期**实测**接入方的归档命令在真仓上的 `git diff --name-status` 输出是 **R100**
      （R3 的前提；若不是 R100，停下来回报，别硬上）
- [ ] H2 停轮拿到 **Q1** 答复 → 把用户答复逐条写进 `reviews/grill-design.md` 的 `## User Confirmation`
      （⚠️ **格式口径按本仓 checker**：`- **Q1**: 用户答复：…`，占位文本不算；本仓解析的是**报告**不是 `design.md`）
      → `manifest build --stage grill` 放行 `src/**` → 内容提交后**必须重跑**（否则 stale）
- [ ] H3 （收尾，在 build 证据**之后**）两段提交 + `manifest build`（grill / grill-adversarial / building）+ `check` 绿
- [ ] H4 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] H5 （收尾）PR（branch protection）→ 合入 → 关 issue **#21**
- [ ] H6 ⚠️ 本 change 的实现 PR **不要顺带归档别的 change**（R5：那会让被归档的 change 按今天的规则被校验）

## 明确不做（本 change）

asterwynd 式归档完成度门禁 · 日期前缀解析（但 D2 第 2 条引入一条**命名约定**，已写进 G1）·
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
- **M2b 复核**：在**新 revision** 上重建三份 manifest（`M` ×3）而不写事件 ⇒ `check` **恰好 3 条**
  「受保护路径被写入」；base revision 上重复 build 是**逐字节幂等**的 ⇒ 不产生 `M`（边界已写入 §1.5）。
- **M1 复核（第 6 面）**：`git mv changes/z/notes.md → changes/archive/y/notes.md` ⇒ `git diff` = **R100**、
  `is_archive_move=True`、今天 `changed_change_ids=[]`、D2 派生的 id = `y`（源 = `z`）；
  D2 第 2 条（等值 / `-<源id>` 后缀）**拒绝**它 ⇒ 回落到今天的行为（A5/E6 钉住）。
- **M3 复核**：`changes/archive/workflow-events.jsonl` **会**被 active 那条 glob 读到（`*` 匹配 `archive`）；
  `changes/archive/notes/workflow-events.jsonl` **会**被新 glob 读到（`notes` 被当成归档 change 目录）；
  真正不被读的是 `archive/<name>/<sub>/workflow-events.jsonl`（再深一层）⇒ N5 已订正。
- **M4 复核**：`code-gated` **同样**闭合 §1.2 的绕过口（C3 的 `code_hits` 非空）⇒ §8 Q1 的推荐理由已改。
- 停轮队列：**只剩 Q1**（原 Q2/Q3/Q4 进 `design.md §2.6` 的 CQ1/CQ2/CQ3）。
