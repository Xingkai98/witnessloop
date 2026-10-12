# Tasks: grill-adversarial-gate

> 依据 `design.md`（**设计已冻结**：grill + 对抗 R1/R2/R3 → **PASS** + 停轮 Q1..Q5 已确认 2026-10-12）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/adversarial-evidence/spec.md`）。
> ✅ **Q1 已裁定 = 乙**（触发面 = 本次 diff 触及 `require_change_for`，与 `building` 共用 `code_hits`）；
> 定案已替换进 `spec.md`（B5）——spec 是 manifest 哈希绑定的 artifact，**实现后不得再改**。

## A. 判定本体（设计 D1 + Q1 定案）

- [x] A1 `constants.py`：`DEFAULT_GRILL_ADVERSARIAL_STAGE = "grill-adversarial"`（与 `DEFAULT_GRILL_STAGE` /
      `DEFAULT_BUILDING_STAGE` 并列，注释写明「被 `check` 要求存在」）
- [x] A2 `policy.py`：`Policy.grill_adversarial_stage` 字段 + `from_doc()` 缺省回落 + `default_policy_doc()`
      写入 `evidence.grill_adversarial_stage`（与既有两条 stage 轴**同形**）
- [x] A3 `checkcmd.py`：change 循环里加一条 `evidence_mod.stage_manifest_findings_in_change(...)`，
      `stage=pol.grill_adversarial_stage`、`verify_body=False`、`reason` 点明「设计阶段对抗验证轮」；
      **触发面 = Q1 定案「乙」** ⇒ 放进既有的 `if code_hits:` 块（与 building 那条并列）
      ——**不写第二份判定实现**
- [x] A4 单测（先红，`tests/test_grill_adversarial_gate.py`，与 `test_building_gate.py` 同构）：
      1. 触发 + 只有 grill/building 证据 ⇒ 红，文案点名 `stage=grill-adversarial`
      2. 补齐该 stage 的 manifest + 报告 ⇒ 绿
      3. `stage` 拼错 ⇒ 文案**点名现有 stage**
      4. 未触发的情形 ⇒ **不要求**（甲=不适用；乙=纯文档 / 只动 change 目录）
      5. 对抗轮之后再改 `design.md` ⇒ **stale 红**（复用既有 span 判定，加回归钉住）
      6. `evidence.grill_adversarial_stage` **可覆写**——⚠️ **必须有用例**（#13 的 M11：覆写轴无测试被变异检查逃逸）

## B. 既有用例与脚手架（⚠️ 数字是**实测**，见 design D2）

- [x] B1 `tests/helpers.py`：`commit_evidence` 默认 `stages` 补 `"grill-adversarial"`
      （与 `write_review` 的 `stage` 默认 `"building"` 不冲突——多跑一次 build 即可）；
      ⚠️ 顺手让 `grill-adversarial` 的默认报告名对齐真实约定 `reviews/grill-adversarial.md`
      （现在默认产 `reviews/grill-adversarial-review.md`，与仓里 5 份真实证据不一致——R8）
- [x] B2 改**自造证据集**的既有用例（甲乙共同的硬核）：`tests/test_building_gate.py::test_green_when_building_evidence_present`、
      `::test_code_change_after_the_review_is_stale`、`::test_building_stage_is_configurable`、
      `tests/test_check_protected.py::test_renaming_with_an_event_is_allowed`（共 4 条，乙口径实测）
- [x] ~~B3 若 Q1 选甲~~ —— **Q1 定案「乙」⇒ 本条不适用**（保留下方清单作为「甲为什么被否」的证据）。
      若日后真有仓选甲，完整清单（对抗轮 R1 实测，逐条点名的出处：
      `reviews/grill-adversarial.md` 的 N-1）：
      ① `tests/test_orphan_reports.py` **8 项** = `test_build_then_check_agree_on_noncanonical_report_paths`
      的 **4 个参数化项** + `test_directory_named_like_a_report_is_not_an_orphan` +
      `test_extra_non_markdown_files_are_not_orphans` + `test_symlinked_report_is_not_an_orphan` +
      `test_two_manifests_binding_the_same_report_is_not_an_error`；
      ② `tests/test_building_gate.py::test_not_required_when_only_the_change_dir_changed`（1 条）；
      ③ **`tests/test_acceptance.py::test_f1_end_to_end_green`**（**原稿漏**）；
      ④ **`tests/test_acceptance.py::test_f2_handwritten_allow_event_is_not_blocked`**（**原稿漏**）；
      ⑤ **`tests/test_check_manifest.py::test_report_inside_reviews_is_evidence`**（**原稿漏**）；
      ⑥ **`tests/test_manifest_build.py::test_round_trip_build_then_check_is_green`**（**原稿漏**）。
      ⚠️ 漏的那 4 条**不会被 B1 的 helpers 默认改动治好**（对抗轮实测：它们在「不补 helpers」的 30 条里也在）
      ⇒ 必须逐条改。⚠️ 原稿引的「权威清单 = `grill-review.md` 事实 1–3」**覆盖不到**这 4 条，已删——权威出处是
      `reviews/grill-adversarial.md` 的 N-1。
      ⚠️ ① 与 ② 的性质**不同**：① 只是补证据；② 钉的正是「提案期 / 纯 change 目录改动**不误伤**」——
      甲口径下它**只能靠空正文证据转绿**（空报告合法），即这条门在该场景下**形同虚设**（design D2/Q1 的措辞）。
      其余：改这些用例时**不得**放松它们原本要钉的东西（孤儿规则 / 往返 / 端到端），只补证据。
- [x] B4 ~~非目标登记~~（**已做**）：design D8 已列非目标（archive 门禁 / `ChangeType` / verdict / `guard` /
      `require_change_for=[]` warning / 签名）
- [x] B5 **已做（2026-10-12，随停轮定案）**：`spec.md` 里所有挂 Q1/Q2 待定标记的段落已按定案替换——
      ① 触发条件正文改为「触及 `require_change_for` + 复用 `checkcmd._code_hits` 同一口径」；
      ② 「未触发时不误伤」的 `Given` 由循环定义换成具体条件（只改文档 / 只动 change 目录）；
      ③ 「多 change 同 PR」的 `Given` 改为乙口径（落实现 + 同时触及另一个 change 目录）；
      ④ verdict 那条 Requirement 去掉「（选甲时）」限定并删掉「若 Q2 选乙」分支
- [x] B6（**已遵守**）⚠️ **实测配方纪律**（R7，本次 grill 已踩到；对抗轮 R1 又补了一条）：
      本仓 worktree 的 `.git` 是**文件**（`gitdir: <主仓>/.git/worktrees/<id>`）⇒ `cp -a` 出的副本
      **共用原 worktree 的 gitdir/index**，副本里的 `git checkout -b`/`git commit` 会**落到被审 worktree**。
      在副本里做 git 操作前先 `rm -f .git && git init -q && git add -A && git commit -qm base`；
      **且** `rm -rf .venv && uv sync`——`cp -a` 会连 `.venv` 一起复制，editable 安装的 `.pth` 写的是**源副本的
      绝对路径** ⇒ 不重建就**测到别的副本的代码**（对抗轮 R1 第一轮四组对照因此全得 `2 failed / 418 passed`）

## C. 回归

- [x] C1 全量 `uv run pytest -q` 绿（基线 **420 passed**）
- [x] C2 本仓 5 个 active change 目录**不因本 change 变红**（实测它们都有 `grill-adversarial.manifest.json`）
- [x] C3 `guard` 行为**不变**（既有 `tests/test_guard.py` 全绿，无新增守卫条件）

## D. 文档

- [x] D1 `docs/gate.md §6`：`check` 的红项清单加「缺设计对抗轮证据」
- [x] D2 `docs/gate.md §8`：门禁/读点表加一行（`stage=grill-adversarial`）
- [x] D3 `docs/gate.md §9` 同族新增小节：触发面（Q1 定案）+ 判据 + **三条诚实边界并列写死**
      （① verdict 不参与判定；② 只保证证据**存在**并绑在最终 revision，**不保证**对抗轮发生在写码之前；
      ③ **报告正文不校验——空文件亦合格**）——与 `README.md` 的口径**逐条一致**（对抗轮 R1 指出原稿
      design 要两条、tasks 要三条，口径不一致，已统一为**三条**）
- [x] D4 `README.md`：对**接入方**的行为变更——写**具体触发条件**（⚠️ **必须点明**「落了实现 = 命中
      `require_change_for`，**本仓含 `templates/**` / `plugin/**`**」，R9）+ 缺它的红 + 同 D3 的三条边界
- [x] D5 `templates/grill.md`：产物小节后补一句「这条现在被 `check` 机械要求（触发面与豁免）」
- [x] D6 ⚠️ **不改** `openspec/changes/` 下**其他** change 目录的非证据文件（会让其 manifest 判 stale —— #12 的教训）

## E. 证据链与收尾

- [x] **E0（已做 2026-10-12，`2cc56ce`）** 停轮拿到 Q1..Q5 答复 → 把定案替换进 `spec.md`（+ B5 已勾）→
      写 `## User Confirmation`（对抗轮 R3 已实测它能过 grill 判据）→ `manifest build --stage grill` 放行 `src/**`
- [x] **E0b（Q5 的处置 · 已做 2026-10-12，R3 `PASS`）**：定案后**重跑设计对抗轮**（对**定稿后**的设计）——
      因为定案会改 `spec.md`/`design.md`/`checkcmd.py` 的形态，而对抗轮原稿针对的是**定稿前**的稿子；
      不重跑 ⇒ 门禁绿、但证据针对的是一份被取代的设计（R4 的机制空洞在**本 change 身上必然发生**）。
      ⚠️ **落盘方式必须写死（对抗轮 R1 的阻塞项 B-2，三种方式实测只有一种通）**：第二轮报告必须写在
      **同一路径** `reviews/grill-adversarial.md`（本仓惯例是把第 2 轮**追加**进同一份文件，关键是**路径不变**；
      **不要**另起文件名——第一份会立刻变成**孤儿报告**、`check` 退 1），然后**重跑**
      `manifest build --stage grill-adversarial`。
      ⚠️ **它是循环不是单步**：若第二轮给 `CHANGES_REQUESTED` 并要求改 `spec.md`/`design.md`，改完证据立刻 stale
      ⇒ 再跑。**重跑到 PASS 或轮数封顶（默认 3 轮，`templates/grill.md:131`）**；
      ⚠️ **Q2 选甲时，以 `CHANGES_REQUESTED` 收尾也算合格**（`spec.md` 的 Scenario 已钉住）——别以为必须跑到 PASS。
      ⚠️ **对抗轮 R3 的 N-6（实测）**：E0b 的追加会让 **`grill` 那份 manifest 也变 stale**（实测 5 条 finding
      里 2 条指向它，因为 `report_hash` 绑的是报告字节）——**E1 会一并重建**，但那之前 `check` 是红的，
      **属预期**，别以为实现错了。
- [ ] E1（收尾步骤，在 build 证据**之后**执行）两段提交 + `manifest build`（grill / grill-adversarial / building）+ `check` 绿
- [ ] E2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] E3（收尾步骤，在 build 证据**之后**执行）PR（branch protection）→ 合入 → 关 issue **#16**

## 明确不做（本 change）

archive 门禁 · `ChangeType` · **verdict 文本判据（Q2 定案：不解析 ⇒ 不做）** · 改 `guard` · `require_change_for=[]` warning ·
签名/防伪造 · 新增 `design_hash`（R4 已声明为已知上限）。

## 实测记录（实现期）

- **429 passed**（基线 **420** + 新增 **9**）——既有用例**改 4 条**（实测预测值，实现后逐条对上）：
  `test_building_gate.py` 3 条 + `test_check_protected.py::test_renaming_with_an_event_is_allowed` 1 条；
  全部是**补一份 `stage=grill-adversarial` 证据**，**没有放松任何断言**。
- **D2 的 churn 数字在真实实现上复现**：先落补丁前的测试文件 ⇒ 新用例 **9 红**（其中 `STAGE` 常量缺失
  让文件整体 collection error）；实现 A1–A3 后 9 绿。
- **变异自检**（本仓有「覆写轴无测试被逃逸」前科）：把 `policy.from_doc` 的
  `grill_adversarial_stage` 覆写改成**恒用默认** ⇒ `test_adversarial_stage_is_configurable`
  **变红**（钉住了）；还原后全量回绿。
- **`guard` 零改动**：`uv run witnessloop guard --root . --path src/witnessloop/checkcmd.py` 在设计证据
  （`stage=grill` manifest）落地后**退 0 放行**——证实「先放行、后重跑 manifest」这条链**无自锁**
  （与 grill / 对抗轮的实测一致）。
- **`check` 在本 change 上的当前状态**：实现提交后 `check` 会红（E0 的三份 manifest 因内容改动判 stale，
  且缺 `stage=building`）——**属预期**，E1 两段提交 + 重建三份 manifest 后转绿。
