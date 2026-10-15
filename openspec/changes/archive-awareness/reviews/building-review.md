# building-review（实现阶段独立审阅 · 第 1 轮）

> 算法与产物格式出处：`templates/review-loop.md`。**零记忆独立 run**：不继承作者的开发上下文。
> 被审 change：`archive-awareness`（issue **#21**）。被审 revision：**`4ad38f0`**（`4ad38f0a1804a9e1fb6407a7dbb1af6d125213a9`）。
> base：`origin/main` = `ae99256`（`ae992565ee2162e5b272af471e9adf895e7f83fb`）。
> 被审 worktree **只读**；唯一仓内写入 = 本文件（`reviews/building-review.md`）。
> ⚠️ 本仓 CI 只有 **pytest + dogfood `witnessloop check`**（`.github/workflows/ci.yml` / `gate.yml`）——
> 本 change **不适用** openspec validate / RIR / Impact Analysis，**未按那些评判**。

## Reviewer

- run id: `building-reviewer-archive-awareness-4ad38f0a1804`（未设 `WITNESSLOOP_RUN_ID` ⇒ 走模板「怎么取 run id」的确定性兜底形态）
- 时间: 2026-10-15（本地）
- 方法（可复现）：
  - **HEAD 全量**：`uv run pytest -q --basetemp=/home/happy/wl-basetemp-rev` ⇒ **516 passed**。
  - **基线副本** `/tmp/aa/base`（`git archive ae99256 | tar -x` + `uv sync`）：全量 **496 passed**；
    再把 HEAD 的 `tests/test_archive_awareness.py` 拷进去跑 ⇒ **10 failed, 10 passed**。
  - **变异副本** `/tmp/aa/mut`（`git archive HEAD | tar -x` + `uv sync`）：未变异态 **516 passed**；逐条变异见下。
  - **攻击台** `/tmp/aa/*.py`：在 `/tmp/aa/repos/**` 造**真 git 仓**（`git init` + 真 `git mv`），用
    `uv run --project /home/happy/wl-wt/archive-awareness witnessloop <verb> --root <副本>` 跑**被审 worktree 的代码**；
    对照侧用 `--project /tmp/aa/base` 跑**改前代码**。所有 `git mv` 由真 git 产出（rename 检测是真的）。
  - 计数一律 `grep -c` / `awk`，全称一律逐行读源码，不靠搜索截断下结论。

## Verdict

**PASS**

`tasks.md` 的 A–G 节全部 `[x]` 都有读得到、跑得着的真实实现（逐条见下，**1 条与文档不符**见 I1）；
H 节未勾选的 5 条**确实未到期**（收尾/证据由主 session 统筹，见 T-H）。
`spec.md` 的 **7 条 Requirement / 21 条 Scenario** 全部有对应实现；**19 条**有测试或我实测复核，
**2 条**（天字第一号的 uniform Scenario、别名「不是放开」）我**自己实测确认**行为正确但**仓内无测试钉住**（I2/I3）。
本 change 的核心风险面——「归档是否开出新的绕过通道」——**逐条实测为 fail-closed**（见 `## 绕过攻击实测`）：
只改 `src/`、伪造归档、部分 move（第 6 面）、只改归档内文件、删 change 目录 **改前改后全红**；
我另造的 9 类攻击（含 fnmatch 后缀碰撞、嵌套 move、符号链接逃逸、alias 放开、id 撞车、
`--change` 双向解析、`archive/` 一级事件文件、两份源撞一个归档目录）**全部 fail-closed 或与既有边界等价**。

**阻塞项：无。** 发现 **1 条 [x] 与代码不符**（I1·B2 文案）、**2 条 spec Scenario 无测试**（I2/I3）、
**2 处测试网眼**（I4/I5）、**3 条非阻塞观察**（I6/I7/I8）。按 verdict 判定规则
（只有「会让实现出错或与 spec 不一致」才阻塞），无一条达到 `CHANGES_REQUESTED`。

## Task Verification（逐项）

> 记法：**声称** → 证据（`文件:行号`，指 `4ad38f0` 的树）→ 结论。

### A. 契约层（D1/D2/D7/D8）

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| A1 | `change_targets` 对「归档 move + 代码改动」返回非空；归档项 id = 归档目录名、label = 仓根相对真路径 | `contract.py:150-184`；测试 `test_archive_awareness.py:77-89`（断言 `change_id == "2026-10-14-add-retry"`、`label == "openspec/changes/archive/2026-10-14-add-retry"`）。**实测先红**：改前 10 failed 含此条 | **成立** |
| A2 | `archive` 永不作为 id；搬走的 active 源不再按 active 校验 | `changed_change_ids`（`contract.py:85-116`）**逐字节未改**（我 `awk` 抽出两 revision 的函数体 `diff` = 相同，只有 docstring 追加）；`contract.py:110-111` 的 `archive/**` 排除仍在。测试 `:91-96`。误改它 ⇒ **13 failed**（变异 M7） | **成立** |
| A3 | `changed_change_ids` 增归档维 + `archived_change_dir` + `change_targets`；`is_archive_move` **一行都不改** | `contract.py:38-40`（`archived_change_dir`）、`:119-147`（`archive_grant`）、`:150-184`（`change_targets`）。`is_archive_move`（`:65-82`）两 revision **逐字节相同**（`diff` 空） | **成立** |
| A4 | 回归：`is_archive_move` 既有语义不变 | 函数体逐字节相同（上条）⇒ 语义结构性不变。⚠️ **仓内无任何测试直接调用 `is_archive_move`**（`grep -rn is_archive_move tests/` = **空**）；覆盖走 `archive_grant` 的委托（`test_grant_requires_...`：R085 / `A` / archive→archive / 源在 archive 四态）与端到端。可接受，见 I5 | **成立**（覆盖方式与 tasks 措辞不同） |
| A5 | D2 第 2 条：`<name> == <源id>` 或 `<name>.endswith("-" + <源id>)` 才授予 | `contract.py:141-147`。测试 `:99-121` 覆盖等值/后缀/不认得/R<100/`A`/源在 archive 六态。**实测先红**（含在改前 10 failed）。去掉这道闸 ⇒ **2 failed**（含 E6 端到端，变异 M1） | **成立** |
| A6 | 拒绝的形态回落到今天的行为（fail-closed，不是静默放行） | 我端到端实测 N6 ⇒ `EXIT=1`（`没有任何 change 目录`）；对齐掉落路径：`archive_grant` 返回 None ⇒ 无归档 target，`changes/z` 仍因 `archived_sources` 排除 ⇒ `change_ids` 空 ⇒ `_require_change` 命中 | **成立** |
| A7 | D8 别名：归档 target 的 `change_id` 接受 `{目录名, 源 id}`；**只改一处、只加一个参数** | `contract.py:180`（`accepted_change_ids=frozenset({name, source})`）、`:381-389`（`accepted = accepted_change_ids if ... else frozenset({rel_change.rsplit("/",1)[-1]})` + `if doc.get("change_id") and doc["change_id"] not in accepted`）。全库 `grep` 该比对**只有这一处**。去掉别名 ⇒ **4 failed**（变异 M5）；改成 `None`（放开）⇒ **4 failed**（变异 M11） | **成立** |
| A8 | D7 tie-break：列表、以目录为键、同 id 两份都校验、不许 `dict[id]=dir` | `contract.py:150-184` 返回 `list[ChangeTarget]`；`grants` 是 `dict[name] -> source`（**名字 → 源**，不是 id → 目录，不丢 target）。测试 `:124-136`。**我端到端复核**：构造「同名 move + 新增 active 子文件 + 改代码」⇒ `EXIT=1`、**13 项**，`openspec/changes/x` 与 `openspec/changes/archive/x` **两侧各出 finding**（无静默丢一份）。按 id 去重 ⇒ **1 failed**（变异 M2） | **成立** |

### B. `check` 侧（D2/D3/D7/D8）

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| B1 | `run()` 循环换 `change_targets` 三元组；三处 `change_dir(...)` 改用解析后的目录 | `checkcmd.py:77`（`targets = contract.change_targets(...)`）、`:78`（`change_ids` 由 target 去重派生）、`:84-119`；`:85-87` / `:88-92` / `:94-99`（`grill_evidence_findings_in_change(target.directory, label=target.label)`）/ `:106-119`（两条 stage 门）——**三处 `change_dir(...)` 已全部消失**（`grep -c "contract.change_dir(" src/witnessloop/checkcmd.py` = **0**） | **成立** |
| B2 | `_require_change` **不加**「有归档 move 就放行」的分支（由 B1 自动修好）；**仅改文案**（提一句「本次 diff 里也没有归档 move」） | `checkcmd.py:197-222`：**没有**豁免分支 ✓（docstring `:203-206` 还写明了「加这个分支是错的」）。⚠️ **但「改文案」没做**：用户可见的 finding 文案与 base **逐字节相同**（我抽出两 revision 的 `_require_change` 尾部 `diff` = 空）。见 **I1** | **半成立** |
| B3 | 先红：能绿的形态 = base active 提案态 → ①改代码 → ②active 态产证据 → ③归档放最后 ⇒ `EXIT=0` | 测试 `:165-181`。**改前红**（含在 10 failed）。**我另造 fixture 独立复跑** ⇒ `EXIT=0 findings=0`。变异：把归档 target 的 directory 指回 active ⇒ 7 failed（M10）；`change_ids` 只取 active ⇒ 2 failed（M8） | **成立** |
| B4 | 先红·防绕过：归档 + 改 `src/` + 零 manifest ⇒ 4 条缺件**全点名**，路径指向归档目录 | 测试 `:141-162`（断言 4 个 needle + `f"{ARCHIVE_REL}/{name}" in err` + `"没有任何 change 目录" not in err`）。**实测先红**（改前红）。变异「归档 target 跳过证据门禁」⇒ **1 failed**（正是此条）；变异「按 id 去重」无关 | **成立** |
| B5 | `_report` 打印归档 change（标注 active / 归档）；保留 `0 个 change 目录` 子串 | `checkcmd.py:291`（计数按去重 id）、`:297-302`（`f"{target.change_id}（归档）" if target.archived else target.change_id`）、`:292-296`（`N 个 change 目录` 子串**保留**）。回归护栏测试 `:184-195`。实测输出含 `2026-10-14-add-retry（归档）`。⚠️ 同 id 撞车时「N 个 change 目录」按**去重 id** 算（2 个目录报 1），见 I8 | **成立** |

### C. `manifest build`（D1/D4/D5/D8）

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| C1 | 先红·症状②：`--change <归档目录名>` ⇒ `EXIT=0`，manifest 落在归档目录 | `manifestcmd.py:33-48`（`resolve_change_dir`）、`:108-113`、`:201`（`manifest_rel = f"{label}/reviews/..."`）。测试 `:200-224`（含 `'"change_id": "<name>"'` 断言）。**实测先红**（在 10 failed 内）。我独立复跑：归档态 build 写出 `change_id=2026-10-14-gwa`、`tasks_hash` = 归档目录 `tasks.md` 的真哈希 | **成立** |
| C2 | 先红·往返：C1 产物随后被 `check` 认（hash 绑定在归档目录上成立） | 测试 `:222-224`（`commit_all` 后 `check == EXIT_PASS`）。我独立复跑 `§1.6` 全链 ⇒ `EXIT=0` | **成立** |
| C3 | `--change X` 解析 active → archive → 报错；`manifest_rel` 由解析后目录推；`--report` 相对解析后目录解析 | `manifestcmd.py:44-48`（active 优先）、`:113`（`directory, label = resolved`）、`:117-123`（`is_within(directory, changes_root)` 守卫保留）、`:131-136`（`resolve_report_path(directory, args.report)`，吃目录）、`:201`。**我实测**：`--change dup` 在 active 与 archive **同时存在**时 ⇒ `EXIT=0` 且**写到 active**（与 D4 的解析顺序一致）。⚠️ 这条顺序**无测试钉住**（变异 M9 = archive 优先 ⇒ **516 passed 逃逸**），见 I4 | **成立** |
| C4 | `archive/` 下有 `*-X` 时**提示**候选、**不自动认**；另兜 `--change archive` | `manifestcmd.py:51-69`（`_missing_change_message`：`candidates` 只进 hint，**不**参与解析）、`:100-105`（`change_id == C.ARCHIVE_DIR_NAME` ⇒ 专门报错）。测试 `:239-258` 三态。**实测先红**（在 10 failed 内） | **成立** |
| C5 | `--change <unknown>` 仍报错点名；含 `/` / 绝对路径 / `..` 仍被拒 | `manifestcmd.py:86-95`（单段守卫，**在**解析**之前**）+ `:117-123`（containment 守卫）——两道各管一类，未合并。既有测试 `test_manifest_build.py` 四条全绿（516 内） | **成立** |
| C6 | D5：`tasks_hash` **照算不跳过**，**不加**归档特例 | `evidence.py` / `hashing.py` 里 `grep archive` = **0 命中**（无特例）；`manifestcmd.py:174-181` 用**解析后的** `directory` 算 `HASHED_ARTIFACTS`。**我独立实测**：归档态 build 的 `tasks_hash` 与归档目录 `tasks.md` 的 `sha256_tree` **相等**（非占位） | **成立** |
| C7 | 先红·别名钉子（R9）：`--change <源id>` 产的 manifest，纯 R100 归档到 `<date>-<id>` 后 `check` 绿 | 测试 `:227-236`。⚠️ **它不是「先红」**：改前也 **passed**（改前该 change 压根不进集合 ⇒ 空转绿）——tasks 的「先红」标注不准，但**它确实是别名钉子**：去掉 D8 ⇒ **4 failed**（含此条，变异 M5）。**我独立复跑**：同形态 `EXIT=0` | **成立**（标注不准） |
| C8 | 先红·R12 后果：同一 diff 内 move + 改写被 move 的 manifest ⇒ 红 + 幽灵 active id | 测试 `:261-273`（断言 `openspec/changes/add-retry：change 目录不存在`）。⚠️ 同样**不是「先红」**（改前也 passed：R<100 ⇒ 不授予 ⇒ 源以 active id 回集合 ⇒ 同样报幽灵）。去掉「必须 R100」⇒ 3 failed（含此条，变异 M6） | **成立**（标注不准） |
| C9 | 先红·§1.5 第 3 条：归档已在 base，新 revision 重建三份 manifest ⇒ **恰好 3 条**受保护写入；补三条事件 ⇒ 绿 | 测试 `:276-315`（**数数**断言 `len(missing) == 3`）。**实测先红**（在 10 failed 内）。我独立复跑同形态（对照实验）见 `## 绕过攻击实测` 第 3 行 | **成立** |

### D. `events`（D6）

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| D1 | 先红·症状③：归档 change 的合法事件重新生效 | 测试 `:345-353` + 对照 `:355-362`（证明不是空真）。**实测先红**（在 10 failed 内）。我独立复跑正例 ⇒ `EXIT=0` | **成立** |
| D2 | `load_all` 改**两条显式 glob**，**不用** `rglob`/`**` | `events.py:97-101`。变异成 `rglob` ⇒ **1 failed**（变异 M4，正是 N5 那条） | **成立** |
| D3 | 否定 N5·方向已订正：**再深一层**不被读 | 测试 `:365-385`。⚠️ 同样**不是「先红」**（改前也 passed）。⚠️ **独立订正**：该用例的 `Given` 写的是 `archive/notes/sub/`（**两层**）——按 tasks D3 的字面「`archive/<name>/<sub>/`」是**一层**，两者都成立（一层也该不被读）；用例取更严的写法，无碍 | **成立** |
| D4 | 回归：`test_events.py` 全绿 + 既有行为不变 | 全量 516 内（`tests/test_events.py` / `test_events_readpoint.py` 未改，`git diff --name-status ae99256..4ad38f0 -- tests/` = 只 `A tests/test_archive_awareness.py`） | **成立** |

### E. 否定用例（本 change 的主要风险面）

> **全部由我实测**（不是只读作者测试）：命令与原始输出见 `## 绕过攻击实测`。

| # | 声称 | 我的实测 | 结论 |
|---|---|---|---|
| E1 N1 | 只改 `src/`、不建任何 change 目录 ⇒ 红 | `EXIT=1`，1 项：`src/app.py` 点名 `require_change_for` | **成立** |
| E2 N2 | 伪造归档（**新建** `archive/<date>-fake/**`，无 active 源）+ 改 `src/` ⇒ 不生效 | `EXIT=1`，1 项「没有任何 change 目录」（`is_archive_move` 要求 `R100` + `old_path`，`A` 恒 False） | **成立** |
| E3 N3 | **删除** change 目录（非 rename）⇒ 仍报「change 目录不存在」 | `EXIT=1`，6 项，第 1 项即 `openspec/changes/add-retry：change 目录不存在` | **成立** |
| E4 N4 | 只改 `archive/<name>/` 里已存在文件（`M`）+ 改 `src/` ⇒ 该 change 不进集合 | `EXIT=1`，1 项「没有任何 change 目录」 | **成立** |
| E5 N5 | 再深一层不被读 | 同 D3 | **成立** |
| E6 N6 | 第 6 面：单文件 `R100` 改入**已存在**的归档目录 `y`（名不认得源 `z`）⇒ 不授予 | `EXIT=1`，1 项「没有任何 change 目录」（`y` 未被凭空授予、`z` 未静默逃检） | **成立** |
| E7 N7 | 同一 diff 内 move + 改写被 move 的文件 ⇒ 红 + 幽灵 active id | 同 C8 | **成立** |

### F. 回归面

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| F1 | `tests/test_archive.py` 6 条全绿 | 全量 516 内；`tests/test_archive.py` **未被改动**。其中 `test_archiving_a_change_passes_without_events`（等值命名 `archive/add-retry`）在本 change 下**仍绿**——它现在**真的**走归档 target 校验（别名 `{add-retry}` 吸收 `change_id`） | **成立** |
| F2 | `test_require_change.py` 8 条 + `test_check_protected.py` 全绿 | 全量 516 内，两文件均未被改 | **成立** |
| F3 | `test_manifest_build.py` 全绿（尤其逐字节幂等） | 全量 516 内；我另证 D8 没动幂等键（`:194-198` 的 anchor 仍取 `change_id + head_sha`，`change_id` 仍 = 目录名） | **成立** |
| F4 | 全量 = 516 passed（基线 496 + 新增 20） | **独立复跑：HEAD `516 passed in 23.86s`；base `496 passed in 27.47s`；差 = 20 = `grep -c '^def test_' tests/test_archive_awareness.py`** | **成立** |

### G. 文档

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| G1 | `gate.md §5.1`：改写归档维 + 边界表 + 命名约定 + 别名口径 + 两条残留边界 | `docs/gate.md:305-338`（§5.1 改写 + **新增 §5.1.1**）：边界表 5 行、三条边界（命名须认得源 id / 纯改名 / 别名不必重建）。**残留边界如实写着**（§5.1.1 第一条边界即「名不认得 ⇒ 不授予」，第二、三条给了代价） | **成立** |
| G2 | `gate.md §4`：改写「archive/** 既不会被读」（**为假**）；补池子口径 + 两条既有口径 + 授权面变大 | `docs/gate.md:255-269`：`-` 行删掉旧假句、`+` 行写「active 一层 + 归档一层」「两份都读、不去重」+ **两条既有口径**（`archive/` 直接下会被读；`archive/<任意名>/` 当成归档 change 目录）+「授权面变大」。**我实测复核**：`changes/archive/workflow-events.jsonl` 与 `changes/archive/zzz/...` **都被读**，`archive/notes/sub/` **不被读** ⇒ 文档逐字与实测一致 | **成立** |
| G3 | `gate.md §3.2`：归档解析 + §1.6 顺序 + D8 别名 + 不写出清单补两条 + `--change archive` 兜底 | `docs/gate.md:222-232`：归档解析、两条新即时错误、`--change archive` 兜底、「归档后要改写证据 ⇒ 其后继 diff」。⚠️ **§1.6 的三步顺序只写在 §5.1.1 的第三条边界里**（`:325-327`「内容 → 在 active 态产证据 → 归档放最后」），§3.2 里**没有**——与 tasks G3 的字面（「§3.2 补 §1.6 的正确顺序」）有出入，但**文档整体有**，读者找得到 | **成立**（位置与 tasks 字面不同） |
| G4 | `gate.md §6`：退出码 1 的列举补「归档 change 证据缺件」 | `docs/gate.md:346`（§6 表内 `**归档 change 证据缺件**（§5.1.1——归档态与 active **同一套**判定）`） | **成立** |
| G5 | `gate.md §10`：给「本仓无 archive 门禁」加限定 | `docs/gate.md:491-493`：限定为「**不在归档点**跑完成度门禁」，并明说与 §5.1.1 的归档感知不是一回事 | **成立** |
| G6 | `README.md`：归档段 + 行为变更段补对**接入方**的变更（三步顺序 / build 用法） | `README.md:139-153`（归档感知段：三条操作边界含**三步顺序**）、`:210-217`（对**接入方**的行为变更：①修复②纯归档 PR 也会红 + 两样新能力） | **成立** |
| G7 | 改文档前读 `tests/test_docs.py`；改完跑它 | `uv run pytest -q tests/test_docs.py` ⇒ **47 passed in 0.12s**（与 tasks 的 47 一致）。全量 516 亦未破守卫 | **成立** |

### H. 证据链与收尾

| # | 状态 | 我的核 | 结论 |
|---|---|---|---|
| H1 | `[ ]` 接入方归档命令 `--name-status` 实测 | 未做（`tasks.md:218` 如实登记「本 worktree 跑不到 asterwynd 的仓」）。**等价覆盖存在**：本 change 的测试与我的攻击台的归档 move 全部由真 `git mv` 产生、真 git 报 **R100**（我 `git diff --name-status -M` 逐例核对过） | **未做，已如实登记** |
| H2 | `[x]` 停轮裁定落进 `grill-design.md`（**追加**，正文一字未改） | `git diff --numstat ae99256..4ad38f0 -- .../reviews/grill-design.md` = **131 insertions / 0 deletions** ⇒ **只增不删** ✓。`## Open Questions`（`grill-design.md:110`）与 `## User Confirmation`（`:125`）标题**逐字** ✓。我另直调 `evidence.grill_evidence_findings_in_change`：本 change 的归档态/active 态**均 0 条**（规则在跑，非空真） | **成立** |
| H3–H6 | `[ ]` 两段提交 + 三份 manifest + `check` 绿 / review-loop / PR+合入+关 #21 | 未勾选。我跑真 dogfood `witnessloop check --root . --base origin/main --head HEAD` ⇒ `13 个变更文件，1 个 change 目录` + **`check：未通过 ✗（4 项）`**（缺 review manifest + 三条 stage 门）、`EXIT=1` ⇒ 与 `tasks.md:220-221` 的记载**逐字一致**（`reviews/*.manifest.json` 确实未建） | **未到期** |
| H7 | `[ ]` 后续另立 change/issue | 未勾选；`docs/gate.md §5.1.1` 已写明「授予判据接受 `-<源id>` 后缀」（task 要求的落点已兑现） | **未到期** |

### 关于 `spec.md` 的 7 条 Requirement（对齐面）

| Requirement（`spec.md`） | 实现 | 测试 / 我的实测 |
|---|---|---|
| §12 归档 move 使该 change 进集合（3 Scenario） | `contract.py:119-184` + `checkcmd.py:77-119` | Sc.1（`:23`）`test_implement_then_archive_in_one_pr_passes` + **我实测 `EXIT=0`**；Sc.3（`:47`）`test_archived_change_is_validated_at_the_archived_path`；**Sc.2（`:35`·uniform 招牌场景）无测试——我实测行为正确**（见 **I2**） |
| §55 只有真归档才授予（5 否定面 / 4 Scenario） | `contract.py:133-147`（两道闸）+ `:141`（命名判据） | Sc.伪造（`:90`）N2 / Sc.触碰（`:95`）N4 / Sc.名不认得（`:101`）N6 / Sc.同一 diff 改写（`:107`）C8；「把受保护 spec 挪进 archive」由既有 `test_archive.py:104` 钉住。**我逐条实测全红** |
| §116 别名（3 Scenario） | `contract.py:180` + `:381-389` | Sc.1（`:125`）`test_pre_archive_manifest_still_passes_after_archiving`；Sc.2（`:132`）`test_manifest_build_into_the_archive_and_back`；**Sc.3（`:137`「不是放开」）无测试——我实测 `change_id='other'` ⇒ `EXIT=1`（3 项「与目录不符」）、`'gwa'` ⇒ `EXIT=0`**（见 **I3**） |
| §142 映射以目录为键（1 Scenario） | `contract.py:150-184`（list + `grants` 按名不按 id） | `test_tie_break_keeps_both_directories_for_the_same_id` + **我端到端复核（13 项，两侧各出）** |
| §155 `manifest build` 支持归档（3 Scenario） | `manifestcmd.py:33-48` / `:100-113` / `:201` | C1/C2/C5/C9 四条测试 + **我实测往返、解析顺序、`archive` 兜底** |
| §190 `events` 覆盖归档（2 Scenario） | `events.py:97-101` | `test_events_in_the_archive_cover_protected_writes` + `test_the_same_diff_without_the_archived_event_is_red` + `test_deeper_events_file_is_not_read` + **我实测三层口径** |
| §215 既有行为不变（3 Scenario） | `is_archive_move` 逐字节未改；`_protected_writes`（`checkcmd.py:225-283`）未改 | `test_archive.py` 6 条 + `test_require_change.py` + N1/N3 + **我实测 N1/N2/N3/N4/N6** |

**未发现「只有 spec 没有实现」或反之。**

## 绕过攻击实测（**本 change 的核心风险面**）

> 全部在 `/tmp/aa/repos/**` 的真 git 仓上跑**被审 worktree 的代码**（对照用 `/tmp/aa/base` 的改前代码）。
> 原始行由脚本打印，此处逐字抄录。

**① 否定面（必须红）——改后全红，且改前也全红（claim ① 复核见下）**

| 攻击 | 改后（`4ad38f0`） |
|---|---|
| N1 只改 `src/`、不建任何 change 目录 | `EXIT=1` · `1. src/app.py：…属于必须挂 change 的路径（policy.require_change_for），但本次 diff 里没有任何 change 目录` |
| N2 伪造归档（新建 `archive/2026-10-14-fake/**`）+ 改 `src/` | `EXIT=1` · 同上 1 项 |
| N3 删除 change 目录（`D`） | `EXIT=1` · `1. openspec/changes/add-retry：change 目录不存在（diff 里出现了它的文件，但目录不在工作树中）`（共 6 项） |
| N4 只改 `archive/<name>/` 内已存在文件（`M`）+ 改 `src/` | `EXIT=1` · 1 项「没有任何 change 目录」 |
| N6 第 6 面：`git mv changes/z/notes.md → archive/y/notes.md`（名不认得）+ 改 `src/` | `EXIT=1` · 1 项「没有任何 change 目录」 |

**② 我自己另造的攻击（不在作者的用例清单里）**

| # | 攻击 | 结果 | 判读 |
|---|---|---|---|
| **A1** | **残留边界②**：`git mv changes/y/notes.md → archive/2026-10-14-foo-y/notes.md`（目标**已存在**、名**恰好**认得源 id）+ 改 `src/`，**不重建** | `EXIT=1` · 6 项（3×`manifest.change_id='foo-y' 与目录不符` + 3×`审阅的是旧 revision…src/app.py`） | fail-closed |
| **A1'** | A1 **+ 在攻击 HEAD 重建目标的三份 manifest + 补三条事件** | **`EXIT=0` · 0 项** | ⚠️ **确实能绿**——但见下「校准」 |
| **A2** | **对照·既有边界**（`design.md §2.5` 残留 1 的等价物）：碰一个已存在的 **active** change `q` 的无关文件 + 改 `src/` + 在攻击 HEAD 重建 `q` 的三份 manifest | `EXIT=1` · 3 项「受保护路径被写入，但没有结构化解释事件」（补三条事件即绿） | **与 A1' 同类等价**：两者都要 3×`M` manifest + 3 条事件；A1' **还要**多一个已存在的归档目录 ⇒ 成本**不低于**既有边界 |
| **A3** | **后缀碰撞**：`archive/2026-foo-z/` + 同 diff 内 `changes/z/…` 与 `changes/foo-z/…` 两条 move 都指向它（两个源各满足 `-<源id>` 后缀） | `archive_grant` 各条 = `[('z','2026-foo-z'), ('foo-z','2026-foo-z')]`；`targets` 的 `accepted_change_ids` = `['2026-foo-z','z']` ⇒ **`foo-z` 不被接受** | fail-closed（**更严**），但与 D7「不许静默丢一份」的精神有出入 ⇒ **I6** |
| **A4** | **嵌套**：`git mv changes/A → changes/archive/A/A`（`name == source`，靠 `archive/A/keep.md` 让父目录存在） | `EXIT=1` · 9 项（全部落在 `openspec/changes/archive/A`，缺件 + 缺 manifest + 两条 stage 门） | fail-closed |
| **A5** | **id 撞车端到端**：同名 move + 新增 active 子文件 + 改代码 | `EXIT=1` · **13 项**，`openspec/changes/x`（4）与 `openspec/changes/archive/x`（9）**两侧各出** | ✅ D7 tie-break 成立，无静默丢一份 |
| **A6** | **`--change` 双向解析**：`dup` 在 active 与 archive **同时存在** | `EXIT=0` → **写到 active**（`openspec/changes/dup/reviews/building.manifest.json`） | ✅ 与 D4 顺序一致（但无测试，见 I4） |
| **A7** | **别名放开**：归档目录里的 manifest 写 `change_id='other'` | `EXIT=1` · 3 项 `manifest.change_id='other' 与目录不符`；同仓改成 `'gwa'`（源 id）⇒ `EXIT=0`；改成 `'2026-10-14-gwa'`（目录名）⇒ `EXIT=0` | ✅ spec `:137` 的 Scenario 成立（**但无测试**，见 I3） |
| **A8** | **符号链接逃逸**：`archive/evil → ../../../`（仓根）后 `manifest build --change evil` | `EXIT=1` · `change='evil' 逃逸出 openspec/changes/——change id 必须落在 changes root 之内`；仓外无残留 | ✅ containment 守卫（`manifestcmd.py:117-123`）有效 |
| **A9** | **事件池投毒**：新增 `openspec/changes/archive/zzz/workflow-events.jsonl`（**全新目录、永不被校验**）授权 `openspec/specs/x.md` 的写入 | 改后 `EXIT=0`（0 项）——**但改前（`ae99256`）同款也 `EXIT=0`**：新增 `openspec/changes/archive/workflow-events.jsonl`（`archive/` **直接下**）今天就会被 `changes/*/` 那条 glob 读到 | ⚠️ **既有口径的放大，不是新类**：改动前「往不受校验的位置丢事件文件」已有 **1 个**落点（`archive/` 根），改动后增到 **一族**（`archive/<任意名>/`）。同款手法在 active 层今天也成立（任意**已存在**的 change 目录）。`spec.md §190` 与 `gate.md §4` **已如实写明**「授权面变大」⇒ **I7**（非阻塞） |
| **A10** | **顺序**：`§1.6`（内容 → active 态产证据 → 归档放最后）**我自己造 fixture** 复跑 | `EXIT=0` · 0 项 | ✅ |
| **A11** | 归档态 build 的 `tasks_hash` 是否为真哈希（D5 不服软） | `change_id = 2026-10-14-gwa`；`tasks_hash 是真哈希 = True` | ✅ |

### 作者报告两处说法的独立复核

**① 「E 节否定面改前改后全红」——成立。**
判据不是作者的措辞，而是**我的两侧实测**：把 `tests/test_archive_awareness.py` 拷进 **base（`ae99256`）副本**跑 ⇒
`10 failed, 10 passed`；**E 节的 5 条（N1/N2/N3/N4/N6）全部落在 passed**（= 那 5 个攻击 diff 的 `check` 在**改前就是红的**），
D 节的 N5、C 节的 N7 同样 passed。改后这 7 条仍 passed，且我用**自造仓**逐条复跑了 N1/N2/N3/N4/N6 的原始输出（上表 ①）。
⇒ 「改前改后**都红**」在**否定面**这个口径上**逐条成立**。
⚠️ **但 tasks.md 里若干「**先红**」标注不实**（见 I5）：C7、C8、D3 三条**改前就是绿的**。

**② 「既有用例 0 条变红、全量 516 passed」——成立。**
证据（独立复跑，非引用）：
- 被审 worktree：`516 passed in 23.86s`（`--basetemp=/home/happy/wl-basetemp-rev`）。
- base 副本（`git archive ae99256` + 全新 venv）：`496 passed in 27.47s`。差 = **20** = `grep -c '^def test_' tests/test_archive_awareness.py`。
- **「既有用例 0 条变红」有结构性保证**：`git diff --name-status ae99256..4ad38f0 -- tests/` = **`A tests/test_archive_awareness.py`**（**只有新增，无任何既有测试被修改或删除**）⇒ 496 条全部原样，516 − 20 = 496 逐条一致。
- 另：`uv run pytest -q tests/test_docs.py` = `47 passed in 0.12s`（与 tasks 一致）。

## Issues

> 均为**非阻塞**（实现正确、与 spec 一致）。按「是否会让实现出错或与 spec 不一致」判，无一条达到 `CHANGES_REQUESTED` 门槛。

**I1（任务不实 · 中）｜`tasks.md` B2 的 `[x]` 有一半没兑现——用户可见的 `_require_change` 文案与改前逐字节相同。**
`tasks.md:39` 写「**仅改文案**（提一句「本次 diff 里也没有归档 move」）」，`design.md §3`（D3）也写「顺带改文案（提一句…）」。
**实测**：我把两 revision 的 `_require_change` 尾部抽出 `diff` ⇒ **空**；`checkcmd.py:215-221` 的 finding 文案与 `ae99256` **完全一致**
（「…但本次 diff 里没有任何 change 目录（…）。补一个 change 目录，或把该路径从 policy.require_change_for 里移除。」），**没有**「归档 move」字样。
新增的只有 docstring（`checkcmd.py:203-206`，解释「为什么不能加豁免分支」）。
⇒ 「**不加豁免分支**」这半条**严格成立**（我变异 M3 证实那个分支本就是**不可达**的：有授予 ⇒ `change_ids` 必然非空 ⇒ `if change_ids: return []` 已经返回），
但「改文案」这半条**没做**。⚠️ 这是 **`[x]` 与代码不符**，不是安全缺陷。最小修法：文案补一句「（本次 diff 里也没有归档 move 把它带回来）」，
或把 B2 拆成「实现（不加豁免）/ 文案」两项并如实勾选。

**I2（测试网眼 · 中）｜`spec.md:35-45` 的 **uniform 招牌 Scenario**（用户 2026-10-15 亲自裁定的那条）**仓内零测试**。**
该 Scenario 是 Q1 的直接产物（「纯归档 PR 也会红、恰好 1 项」），也是本 change 最容易被后人「顺手改回去」的一条语义。
**我独立实测**（自造仓：`legacy-x` 三份 manifest 是归档前用**源 id** 产的、`grill-review.md` 的 `## Confirmed Decisions` 只有 2 条，
PR 只做 `git mv`、一行代码不改）：
```
check：未通过 ✗（1 项）
  1. openspec/changes/archive/2026-10-15-legacy-x/reviews/grill-review.md：`## Confirmed Decisions` 只有 2 条，少于硬门槛 3 条
EXIT=1
```
⇒ **行为正确、且与 spec 逐字一致**（顺带证明 D8 别名把 `change_id` 那一类 3 项**吞掉了**——这正是对抗轮对 Q1 例子「4 项 → 1 项」的校准）。
但 `grep -n "Confirmed Decisions" tests/test_archive_awareness.py` = **无命中** ⇒ 今天若有人把归档 target 从门禁里摘掉（变异 M3' 已证 **只被 1 条测试抓住**），
这条招牌语义没有独立的回归钉子。**最小修法**：把上面这个仓固化成一个用例（约 30 行，`write_evidence` 加一个 `grill_body` 形参即可）。

**I3（测试覆盖 · 中低）｜`spec.md:137-140` 的 Scenario「别名不是「放开」」没有独立用例。**
该 Scenario 要求「归档目录里 `change_id="other"` ⇒ 仍报与目录不符」。仓内的钉法是 `test_change_targets_...` 对 `accepted_change_ids` 做**集合相等**断言（机械钉得住，变异 M11 红）。
**我端到端实测**：`other` ⇒ `EXIT=1`（3 项）/ `gwa` ⇒ `EXIT=0` / `2026-10-14-gwa` ⇒ `EXIT=0` ⇒ 行为正确。
缺口只在「端到端那一跳没人守」。最小修法：把 `other` 那一态做成一条 `check` 级用例（`write_review(..., doc_overrides={"change_id":"other"})`，10 行）。

**I4（测试网眼 · 低）｜`manifest build` 的 active→archive 解析**顺序**无测试钉住（变异存活）。**
`manifestcmd.py:44-48` 的顺序是 D4 的明文（active 优先），`design.md` R5 也点名了「同名 active + archive 并存」这一态。
**复现（变异 M9）**：把两分支对调（archive 优先）⇒ **`516 passed`，零变红**。当前实现**是对的**（我实测 `--change dup` ⇒ 写到 active），缺口在「没人守着它不被改回去」。
最小修法：在 `test_manifest_build.py` 补一条「同名 active + archive 并存 ⇒ 写 active」。

**I5（文档不实 · 低）｜`tasks.md` 的三处「**先红**」标注经不起复核；另有一处用例数分节错误。**
- `tasks.md:68`（C7）「单测（**先红**·别名钉子 D8 / R9）」：该测试在 **base 副本上 passed**（改前归档 change 不进集合 ⇒ 空转绿）。
- `tasks.md:71`（C8）「单测（**先红**·R12 的后果）」：同样在 base 上 passed（`R<100` ⇒ 不授予 ⇒ 源以 active id 回集合 ⇒ 同样报幽灵）。
- `tasks.md:85`（D3）「单测（否定 N5）」标了「先红」句式：同样 base 上 passed。
  ⇒ 三条的**断言本身都成立、都有价值**（变异 M5/M6/M4 分别由它们抓住），问题只在「先红」这个**特征描述**不实——它们实际是**回归护栏**（改前改后都绿）。
  建议照实改成「回归护栏」或补上真正能区分的断言。
- `tasks.md:208` 的分节计数「A 4 / B 3 / **C 6** / D 3 / **E 4**」与实测不符：**A 4 / B 3 / C 5 / D 3 / E 5**（总数 20 ✓）。
  影响：`tasks.md:210` 那句「红的那 10 条 = 契约层 4 条 + 「归档 + 改码」的 4 条 + 归档态 build 2 条」也与实测的
  「契约 4 / check 2 / build 3 / events 1」对不上。

**I6（实现一致性 · 低）｜`grants` 那个 dict 会把**同名的第二个源**静默丢掉——与 D7 自己立的原则有出入（但 fail-closed）。**
`contract.py:167-171`：`grants: dict[str, str]`，`grants.setdefault(grant[1], grant[0])`。
**实测（A3）**：`archive/2026-foo-z/` 同时被 `changes/z/…` 与 `changes/foo-z/…` 两条 R100 指向 ⇒
`archive_grant` 两条都返回非 None，但 `accepted_change_ids` 只有 `{2026-foo-z, z}`，**`foo-z` 不被接受**。
⇒ 若该归档目录里既有 manifest 写的是 `foo-z`，会被判「与目录不符」⇒ **fail-closed（更严）**，不是绕过口。
但 D7 立的原则是「**不许** `dict[id]=dir`、不许静默丢一份」，这里在**别名**这一轴用的是 dict——两处口径不一致。
**判为非阻塞**：丢弃只让校验**更严**，且要构造两个源的名字互为后缀（`z` 与 `foo-z`），实践里极罕见。
若愿意对齐：`accepted_change_ids` 改成「所有满足 `name == s or name.endswith("-"+s)` 的源」的并集即可（纯并集，不引入新判据）。

**I7（授权面 · 低·已文档化）｜事件池的落点从「`archive/` 根一个路径」扩成「`archive/<任意名>/` 一族」。**
**实测（A9）**：改后，新增 `openspec/changes/archive/zzz/workflow-events.jsonl`（全新目录，**永不被任何 change 校验**）即可授权
`openspec/specs/x.md` 的任意写入 ⇒ `EXIT=0`。**改前同款也成立**：`openspec/changes/archive/workflow-events.jsonl`（`archive/` 直接下）今天就会被 `changes/*/` 那条 glob 读到；
更一般地，往任意**已存在**的 active change 目录丢一份新 events 文件今天也管用（`**/workflow-events.jsonl` 的新增（`A`）不需要解释事件，`checkcmd.py:267-268`）。
⇒ **不是本 change 引入的新类**，是既有口径的**放大**（1 个落点 → 一族）。`spec.md:190-197` 与 `docs/gate.md:255-269` **已如实写明**「授权面变大」，
`design.md` 的 CQ3 也明确「不改语义」是定案（用户未反对）。**判为可接受、非阻塞**；如日后想收紧，
最小改动是「事件只在本次 diff 的 change 集合内的 change 目录里提供豁免」（design CQ3 已指出这是**不需要新字段**就能做的），但那是语义变更、不在本 change 范围。

**I8（诊断面 nit · 低）｜同 id 撞车时 `check` 的摘要行会把两个目录说成一个。**
`checkcmd.py:291-296`：`change_ids` 按**去重后的 id** 算 ⇒ 撞车场景我实测输出 `2 个 change 目录` 会是 `1`（`targets` 有两条）。
`design.md` R6 说过「计数含义变了」，但只覆盖了「归档也算进去」，没覆盖「同 id 去重」。
影响纯诊断（findings 一条不少）。若要更准：改成 `len(targets)` 并另附 id 列表，或把「N 个 change 目录」改成「N 个 change（M 个目录）」。

## Test Results

> 全部为**我独立复跑**的原始行（非引用作者记录）。

- 被审 worktree 全量：`516 passed in 23.86s`（`uv run pytest -q --basetemp=/home/happy/wl-basetemp-rev`）。
- 基线副本 `/tmp/aa/base`（`git archive ae99256 | tar -x` + `rm -rf .venv; uv sync`）全量：`496 passed in 27.47s`。
- 基线副本 + HEAD 的 `tests/test_archive_awareness.py`：**`10 failed, 10 passed in 1.70s`**。
  - 红（= 本 change 的**新行为**）：契约层 4（`test_change_targets_...` / `test_archive_is_never_a_change_id_...` / `test_grant_requires_...` / `test_tie_break_...`）、
    check 2（`test_archived_change_is_validated_at_the_archived_path` / `test_implement_then_archive_in_one_pr_passes`）、
    build 3（`..._into_the_archive_and_back` / `..._unknown_and_archive_root_and_candidate_hint` / `..._already_archived_manifest_needs_one_event_each`）、
    events 1（`test_events_in_the_archive_cover_protected_writes`）。
  - 绿（= 否定面与回归护栏，**改前改后都绿**）：`test_N1` / `test_N2` / `test_N3` / `test_N4` / `test_N6` /
    `test_deeper_events_file_is_not_read` / `test_rebuilding_a_moved_manifest_in_the_same_diff_is_rejected` /
    `test_pre_archive_manifest_still_passes_after_archiving` / `test_the_same_diff_without_the_archived_event_is_red` /
    `test_report_still_says_zero_change_dirs_for_a_docs_only_diff`。
- 变异副本 `/tmp/aa/mut`（`git archive HEAD | tar -x` + `uv sync`）未变异态：`516 passed in 23.77s`。
- `uv run pytest -q tests/test_docs.py`：**`47 passed in 0.12s`**。
- 真 dogfood：`uv run witnessloop check --root . --base origin/main --head HEAD` ⇒
  `check：基线 origin/main...HEAD，13 个变更文件，1 个 change 目录` / `  change：archive-awareness` /
  `check：未通过 ✗（4 项）`（缺 review manifest + 三条 stage 门）/ `EXIT=1`（与 `tasks.md:220-221` 逐字一致）。

### 变异验证（12 个变异体，10 个被抓住、2 个逃逸）

在 `/tmp/aa/mut` 上逐条应用（`sed` 级补丁）→ 跑该新测试文件 → 还原。

| # | 变异 | 期望 | 实测 |
|---|---|---|---|
| **M1** | 去掉 D2 第 2 条（名不认得也授予） | 红 | ✅ **2 failed**（`test_grant_requires_the_target_name_to_recognize_the_source_id`、`test_N6_partial_move_into_an_existing_archive_dir_grants_nothing`） |
| **M2** | `change_targets` 按 id 去重（丢同 id 的第二份） | 红 | ✅ **1 failed**（`test_tie_break_keeps_both_directories_for_the_same_id`） |
| **M3** | `_require_change` 加「有归档授予就返回 `[]`」 | 红 | ⚠️ **0 failed**——但该分支**不可达**（有授予 ⇒ `change_ids` 非空 ⇒ 上面那句已返回），**语义等价**，不算逃逸 |
| **M3'** | 归档 target **跳过全部证据门禁**（只进集合） | 红 | ✅ **1 failed**（`test_archived_change_is_validated_at_the_archived_path`）——R1 那条禁令**有**钉子（只 1 条，见 I2） |
| **M4** | `events.load_all` 改用 `rglob` | 红 | ✅ **1 failed**（`test_deeper_events_file_is_not_read`） |
| **M5** | 去掉 D8 别名（`accepted = {name}`） | 红 | ✅ **4 failed** |
| **M6** | `is_archive_move` 接受 `R<100` | 红 | ✅ **3 failed**（含 `test_archive.py::test_modifying_a_file_inside_archive_still_needs_an_event`） |
| **M7** | `changed_change_ids` 不再排除 `archive/**` | 红 | ✅ **13 failed** |
| **M8** | `change_ids` 只取 active（归档不进 `_require_change`） | 红 | ✅ **2 failed** |
| **M9** | `resolve_change_dir`：archive 优先于 active | 红 | ❌ **`516 passed`（逃逸 → I4）** |
| **M10** | 归档 target 的 `directory` 指向 active | 红 | ✅ **7 failed** |
| **M11** | `accepted_change_ids` 放开为 `None` | 红 | ✅ **4 failed** |

## 结论

`PASS`。A–G 节的 `[x]` 逐条有真实实现：`is_archive_move` **逐字节未改**（我 `awk` 抽函数体 `diff` 验证），
`changed_change_ids` 只增 docstring，`archive_grant` 的两道闸与 `change_targets` 的「列表 + 以目录为键」都在，
`checkcmd` 三处 `change_dir(...)` 已全部换成解析后的目录，`manifestcmd` 的解析顺序/落盘/hash 口径与 `check` 共用同一实现，
`events` 是两条显式 glob（非 `rglob`），`policy.py` / `guardcmd.py` / `evidence.py` / `hashing.py` **一行未动**，
`.github/` / `templates/` / `plugin/` **零改动**（CI 未被弱化），`tests/` **只有新增、无任何既有断言被改**。

安全面：**本 change 没有开出新的绕过通道**。否定面 N1–N6 **改前改后全红**（两侧实测）；
我另造的 11 类攻击（残留边界、后缀碰撞、嵌套 move、id 撞车、`--change` 双向解析、别名放开、符号链接逃逸、
事件池投毒、`archive/` 一级）**全部 fail-closed 或与既有边界同类等价**——其中「部分 move 进已存在归档目录」那条
（`design.md` §2.5 残留 2）我**实测确认能绿**，但代价（3×`M` manifest + 3 条解释事件）**不低于**既有边界
（碰 active change + 重建 manifest），校准**成立**。唯一被放大的是**事件池落点数**（1 → 一族），
`spec.md` 与 `docs/gate.md §4` 已**如实写明**，且同款手法改前就能用 ⇒ 非阻塞。

作者的两处说法**都成立**：「E 节否定面改前改后全红」（我在 base 副本上复跑，5 条 E 用例全绿 = 攻击全红）、
「既有用例 0 条变红、516 passed」（`516` vs base `496`，差 20 = 新增数，且 `tests/` 侧只有 `A` 一条新文件）。

8 条非阻塞项里，**I1（B2 的 `[x]` 与实际不符）与 I2（uniform 招牌 Scenario 无测试）**最值得在收尾前顺手补上——
前者是 `[x]` 的准确性问题，后者是**用户亲自裁定**的那条语义唯一的钉子。

---

## 简报（≤300 字）

**Verdict：PASS**（无阻塞）。A–G 逐条读码 + 真 git 仓攻击台复核全部成立；`is_archive_move` 逐字节未改、
`tests/` **只新增无修改**、`.github/` 零改动；全量 **516 passed**（base **496**，差 = 新增 20 条）。
**否定面 N1–N6 改前改后全红**（我在 base 副本上跑，5 条 E 用例全绿 = 攻击红）；**另造 11 类攻击全 fail-closed**——
含「部分 move 进已存在归档目录」（能绿，但成本 ≥ 既有边界：3×`M` manifest + 3 条事件）、符号链接逃逸（守卫拦住）、
alias 放开（`other` 被拒）、id 撞车（两侧各出 13 项）。唯一放大：事件池落点 1 → 一族（`archive/` 根那个落点改前就有，已文档化）。
两处说法**都站得住**。非阻塞 8 条：**I1** B2 的 `[x]` 一半没做（`_require_change` 文案与改前逐字节相同）；
**I2** uniform 招牌 Scenario（纯归档 PR ⇒ 恰好 1 项）**仓内零测试**（我实测行为正确）；
**I4** `--change` active 优先无测试（变异逃逸）；**I5** tasks 三处「先红」标注不实 + 分节计数错。

---

## R2 复审（revision 64f3104）

> **追加节**——R1 正文（上方）**一字未改**。被审 revision = **`64f3104`**（在 `4ad38f0` 之上修 R1 的 8 条，
> 见 `git show e28e567`（代码/测试）+ `git show 64f3104`（文档/收入 R1 报告））；base 仍 `ae99256`。
> 本轮**重点**：两条**改了行为**的项（**I6** 别名取并集 / **I8** 计数按目录数）逐条实测；
> I1–I7 逐条复核；「13 failed / 10 passed」独立复跑；安全面**另造**攻击。

### Reviewer（R2）

- run id: `building-reviewer-archive-awareness-64f3104-r2`（未设 `WITNESSLOOP_RUN_ID` ⇒ 同 R1 的确定性兜底形态）
- 时间: 2026-10-15（本地）
- 方法（可复现）：
  - 三份**隔离副本**（各 `uv sync` 独立 venv）：`/tmp/aa2/base` = `ae99256`、`/tmp/aa2/prev` = `4ad38f0`（R1 被审那版）、
    `/tmp/aa2/mut` = `64f3104`（变异用）。**不在被审 worktree 上跑任何实验**（唯一写入 = 本节）。
  - 攻击台 `/tmp/aa2/attacks.py`（12 个配方）+ `e2e_i6.py` + `e2e_i8.py` + `recipe_m_i2.py` + `recipe_events.py`：
    全部在 `/tmp/aa2/repos/**` 造**真 git 仓**（`git init` + 真 `git mv`，`git diff` 报 **R100**），
    用 `uv run --project <副本> witnessloop <verb> --root <仓>` 跑**指定 revision 的代码**。
  - 全量/回归一律 `uv run pytest -q --basetemp=/home/happy/wl-basetemp-rev2`（不用 `/tmp`）；计数一律 `grep -c` / `awk`。

### Verdict

**PASS**（无阻塞）。

R1 的 8 条**全部有兑现**：I1/I2/I3/I4 有可复跑的测试钉子，I5/I7 的文档订正与实测逐字一致，
**I6/I8 两条行为变更经独立实测判定收敛**（I6：顺序漂移**真的修好了**，且**没有开出新的绕过通道**；
I8：确认**纯诊断**，判定面一条没动）。作者的两处关键说法——「13 failed / 10 passed」与「`519 passed`」——**逐字复现**。
新增 **4 条非阻塞**观察（R2-1…R2-4），无一条达到 `CHANGES_REQUESTED` 门槛。

### I6（**改了行为**）｜顺序漂移：**真修好了**；是否开出口子：**没有**

**① 单元探针**（同一份合成 diff、只换记录顺序；`change_targets` 直调，两 revision 同一脚本）：

```
prev 4ad38f0   A(z 先)  accepted=['2026-foo-z', 'z']        source='z'
               B(foo-z 先) accepted=['2026-foo-z', 'foo-z'] source='foo-z'   ← 漂移
head 64f3104   A(z 先)  accepted=['2026-foo-z','foo-z','z'] source='z'
               B(foo-z 先) accepted=['2026-foo-z','foo-z','z'] source='z'    ← 不漂移
单源退化情形两版一致；第三条「名字不认得」的源两版都不进集合。
```

**② 端到端**（真仓：`archive/2026-foo-z/` 里放好三份 manifest，`change_id` = 指定值；feature 上**两条** R100
分别把 `changes/z/…` 与 `changes/foo-z/…` 的文件搬进该目录；只改目标文件名 ⇒ 只改 git 输出顺序）：

| manifest 的 `change_id` | 顺序 | prev `4ad38f0` | head `64f3104` |
|---|---|---|---|
| `z` | z 先 | `EXIT=0` 0 项 | `EXIT=0` 0 项 |
| `z` | foo-z 先 | **`EXIT=1` 3 项**「manifest.change_id='z' 与目录不符」 | `EXIT=0` 0 项 |
| `foo-z` | z 先 | **`EXIT=1` 3 项**「…='foo-z' 与目录不符」 | `EXIT=0` 0 项 |
| `foo-z` | foo-z 先 | `EXIT=0` 0 项 | `EXIT=0` 0 项 |

⇒ **同一个逻辑 diff 在改前会在 0 项 / 3 项之间按顺序翻转**（我实测到两个方向），改后**四种组合全绿**。
作者的「取 diff 里先出现的源 ⇒ 随顺序漂移」**成立**，「只放宽别名集合」也**严格成立**：

- 新 `accepted` **⊇** 任一顺序下的旧 `accepted`（是**放宽**，不是收紧）；
- 且**恰好等于**两种顺序的**并**：`{D, z, foo-z} = {D,z} ∪ {D,foo-z}`。

**③ 有没有因此「本该红」的形态变绿？——有**red→green 的形态，但**不是新类、不是绕过口**。理由三条，均可复核：

1. **新增接受的名字只能是「本次 diff 里真有一条 R100 把它搬进该目录」的源。**
   我另造两个探针（与作者的用例清单无关）：
   - 配方 **K**：`D=archive/2026-foo-z`、真 move 的是 `foo-z`（授予），manifest 写**无关的** `other`
     ⇒ `EXIT=1`，3 项 `manifest.change_id='other' 与目录不符`（**别名不吸收无关 id**，`spec.md:137` 的 Scenario 成立）；
   - 配方 **I**：manifest 写**真搬进去了的** `foo-z` ⇒ `change_id` 那类 finding **消失**（只剩我 fixture 自带的
     stale-revision 3 项）——即被接受的名字**都能对上一条真 move**。
2. **`change_id` 是 manifest 里攻击者自己写的字段。** 谁能写 manifest，谁就能把值写成目录名——这道校验是
   **防漂移/防复制错位**，不是授权闸（`contract.py:8-9` 与 `design.md §5.3` 的原文口径）。
   放宽它**不可能**新增一项「攻击者本来做不到」的能力。
3. **全库没有任何下游消费 manifest 的 `change_id`**：`grep -c change_id src/witnessloop/*.py` ⇒
   `events.py` **0**、`evidence.py` **0**、`hashing.py` **0**；比对只发生在 `contract._validate_one`（一处）。
   （另：`events.Event` 的字段只有 `event_type/artifact_path/reason/approved_by`——事件的 `change_id` **解析即丢**，
   `docs/gate.md §4` 的「change_id 不被消费」**是真的**。）

⇒ **诚实标注**：确实存在「改前红、改后绿」的一类形态——就是漂移里**输**的那半边。但它**等于旧代码在另一种顺序下
已经会绿**的那一态（② 的表格里两行绿、两行红正好对调），所以是**把不可复现的口径改成确定性并集**，
而不是新开口子。**判为收敛**（`design.md` D8 的订正段、`tasks.md` 回写期记录与我的实测一致）。

### I8（**改了行为**）｜确认**纯诊断口径**，判定面一条没动

**端到端**（真仓：base 上 active `x` 有全套证据，feature 上「新增 `changes/x/extra.md` + `git mv changes/x/notes.md
changes/archive/x/notes.md`」⇒ 同名单段 id 同时来自 active 与归档）：

```
prev 4ad38f0   check：基线 main...HEAD，2 个变更文件，1 个 change 目录     ← 两个目录说成一个
                 change：x, x（归档）
               check：未通过 ✗（10 项）   [1..10 逐条]
head 64f3104   check：基线 main...HEAD，2 个变更文件，2 个 change 目录     ← 按目录数
                 change：x, x（归档）
               check：未通过 ✗（10 项）   [与 prev 逐条同文，只有 sha 不同]
```

- **findings 逐条一致**（10 = 10，内容逐字相同，仅 manifest 里绑的 sha 因提交 hash 不同而不同）⇒ **判定未变**。
- **判定面未动**（读码）：`checkcmd.py:78` 仍由 `targets` **按去重 id** 派生 `change_ids`、仍只喂 `_require_change`；
  `_report` 里只有那一行 `len(targets)` 变了（`:289-306`），`if targets:` 分支与 `（归档）` 标注未动。
- **`0 个 change 目录` 子串保留**：配方 B / D / E / J 的原始输出里都逐字出现（见下），
  `tests/test_check_contract.py:88` 与 `test_report_still_says_zero_change_dirs_for_a_docs_only_diff` **仍绿**。

### I1–I7 逐条（R2 复核）

| # | R1 的判定 | R2 复核（实测/读码，指 `64f3104` 的树） | 结论 |
|---|---|---|---|
| **I1** | `[x]` 一半没做：`_require_change` 文案与 base 逐字节相同 | **真改了**：`checkcmd.py:216-225` 的 finding 现在是「…但本次 diff 里没有任何 change 目录（…），**也没有一次把它归档进来的 `git mv …/…`**（**归档 move 也算「挂了 change」**——那个 change 会按归档路径走同一套证据门禁）。补一个 change 目录（或补上那条归档 move）…」。钉子 = `test_N1` 的 `assert "归档 move" in err and "git mv" in err`，**该断言在实现前红**（我复跑：base 上 `test_N1` 正因这一条落到 FAILED，见下 13 条） | **修好** |
| **I2** | uniform 招牌 Scenario 仓内零测试 | 新增 `test_uniform_validates_a_pure_archive_pr_like_active`（fixture = 新增的 `SHORT_GRILL`：2 条决策 + 归档前用**源 id** 产的证据 + 纯 `git mv`）。**我另造同形态仓复跑原始输出**：base `EXIT=0 / 0 项「通过 ✓」`（空转绿）；HEAD `EXIT=1`、**恰好 1 项**、逐字点名 `…/archive/2026-10-15-add-retry/reviews/grill-review.md：\`## Confirmed Decisions\` 只有 2 条，少于硬门槛 3 条`。变异**三条**都被它抓住：M3'（归档 target 跳过全部门禁）3 failed、M-U1（跳过 grill 正文判定）2 failed、M-U2（gate 指向 active 目录）5 failed | **修好**（钉子真实） |
| **I3** | 别名「不是放开」无独立用例 | 新增 `test_alias_does_not_loosen_the_change_id_check`（先红，在 13 条内）。双向我都端到端复核过：写 `other` ⇒ `EXIT=1`「与目录不符」（配方 K）；写合法源 id ⇒ 全链 `EXIT=0`（配方 L） | **修好** |
| **I4** | `--change` active 优先无测试（变异 M9 逃逸） | 新增 `test_manifest_build_prefers_the_active_directory_when_both_exist`。它**不是先红**（我复跑：base 上 **passed**，在 10 passed 内）——与作者自述一致。**变异 M9（archive 优先）⇒ 1 failed，正是它** ⇒ 钉子成立、逃逸口已封 | **修好** |
| **I5** | tasks 三处「先红」标注不实 + 分节计数错 | 三处已按实测改成**回归护栏**并附变异证据；我复跑 base：`C7` / `C8` / `N5` 三条**都在 10 passed 内**（= 改前也绿），标注订正**对**。分节计数 `grep` 复算 = **A 4 / B 3 / C 5 / D 3 / E 5 + I 3 = 23**，与 tasks 一致；A7 拆成「②③ 先红、① 回归护栏」也与实测一致 | **修好** |
| **I6** | `grants` 会静默丢掉同名的第二个源（与 D7 原则不一致） | 见上「I6」整节：**漂移真修好、未开出口子** | **修好** |
| **I7** | 事件池落点 1 → 一族（已文档化） | `docs/gate.md §4` 的订正**逐字与实测一致**。我三个落点各跑两版：`archive/workflow-events.jsonl`（`archive/` 直接下）⇒ **base 与 HEAD 都 `EXIT=0`**（既有口径，作者说「改前就能用」**成立**）；`archive/zzz/workflow-events.jsonl` ⇒ base `EXIT=1` / HEAD `EXIT=0`（本 change 新覆盖的一族）；`archive/zzz/sub/…` ⇒ **两边都 `EXIT=1`**（再深一层不读） | **修好**（文档与实测一致） |

### 「13 failed / 10 passed」独立复跑 —— **逐字复现**

`cp tests/test_archive_awareness.py → /tmp/aa2/base`（`ae99256`）+ `uv run pytest -q tests/test_archive_awareness.py`
⇒ **`13 failed, 10 passed in 2.09s`**（23 条）。逐条身份（`-v` 取的原文）：

- **红 13** = R1 那 10 条 + **3 条新增**：`test_uniform_validates_a_pure_archive_pr_like_active`、
  `test_alias_does_not_loosen_the_change_id_check`、`test_N1_...`（**因 I1 的新断言**红——其余断言在 base 上照样通过）。
- **绿 10** = R1 的 9 条（否定面 N2/N3/N4/N6 + N5 + N7 + 两条回归护栏 + `0 个 change 目录`）
  + **新增的 `test_manifest_build_prefers_the_active_directory_when_both_exist`**（I4 的**回归护栏**，改前也绿）。
- ⇒ 作者在 `tasks.md` 回写期写的「新增的 3 条里有 2 条先红 + N1 的文案断言」**逐字准确**。

其余复跑：被审 worktree 全量 **`519 passed in 25.00s`**（= R1 的 516 + 新增 3）；
F 节回归面 7 个文件 **`85 passed`**；`tests/test_docs.py` **`47 passed`**；
真 dogfood `witnessloop check --root . --base origin/main --head HEAD` ⇒ `14 个变更文件，1 个 change 目录` /
`未通过 ✗（4 项）`（缺 review manifest + 三条 stage 门）/ `EXIT=1`——**未建 `reviews/*.manifest.json`**（合规，本 change 禁止我建）。

### 安全面复跑（我自己另造，**不是**跑作者的用例）

| 配方 | 攻击 | HEAD 实测 | 判读 |
|---|---|---|---|
| **A** | 只改 `src/`、无 change 目录 | `EXIT=1` · 1 项（新文案） | fail-closed（与 base 同） |
| **B** | 伪造归档（新建 `archive/2026-10-15-fake/**`）+ 改 `src/` | `EXIT=1` · **0 个 change 目录** · 1 项 | fail-closed |
| **C** | 删 change 目录（`D`） | `EXIT=1` · 6 项，含「change 目录不存在」 | fail-closed |
| **D** | 只改**已在 base** 的归档目录里的文件（`M`）+ 改 `src/` | `EXIT=1` · **0 个 change 目录** · 1 项 | fail-closed |
| **E** | N6：单文件搬进已存在归档目录（名**不认得**源）+ 改 `src/` | `EXIT=1` · **0 个 change 目录** | fail-closed |
| **F** | 残留边界②：单文件搬进已存在目录、名**认得**源、**不重建**证据 + 改 `src/` | `EXIT=1` · 4 项（缺 manifest + 三条 stage 门，**全部落在归档路径**） | fail-closed |
| **G** | 两个源都搬进同一目录 + 改 `src/`（我的 fixture 让 `src/` 落在证据之后） | `EXIT=1` · 3 项「审阅的是旧 revision」 | 既有规则（非归档语义） |
| **I** | 同 G，且 manifest 写**真搬进去的**另一个源 id | `EXIT=1` · 3 项（**无** `change_id` 那类） | 别名按设计吸收 |
| **J** | D=`archive/2026-other`，move 的名字**认不得**源 + 改 `src/` | `EXIT=1` · **0 个 change 目录** | fail-closed（未凭空授予） |
| **K** | D 被真 move 授予，但 manifest 写**无关的** `other` | `EXIT=1` · 3 项「与目录不符」 | **别名不是放开** |
| **L** | 合法全链（`§1.6` 顺序 + 两条 move 进同一目录 + 改 `src/`） | **`EXIT=0` / 0 项**（prev 也 `EXIT=0`） | 未过度收紧 |

⇒ **本 change 仍未开出新的绕过通道**：N1–N6 改前改后全红；两条与「同目录多源」有关的新形态（F 红、G/I 只按既有
stale 规则红、J 未授予、K 拒无关 id）全部 fail-closed 或与既有边界等价。

### 新发现（R2，**均非阻塞**）

**R2-1（测试网眼 · 低）｜I6 的「并集」本身**没有测试钉住**（变异逃逸）。**
把 `change_targets` 的 `grants` 回退成「只留先出现的源」（等价于 `4ad38f0` 的语义）⇒ **`23 passed`，零变红**。
R1 的 I6 只要求「要么对齐、要么写明」，作者选了**改行为**——那就该有钉子。最小修法：在
`test_change_targets_...` 旁加一条 5 行的单元用例，断言「两条 move 指向同一目录 ⇒
`accepted_change_ids == frozenset({name, s1, s2})`」。

**R2-2（测试网眼 · 低）｜I8 的「按目录数」也没有测试钉住。** 把 `len(targets)` 换回 `len({t.change_id for t in targets})`
⇒ **`519 passed`**。同 id 撞车那个形态（我的 `e2e_i8` 仓）没进仓。最小修法：把撞车仓固化成一条
`check` 级用例（断言摘要行含 `2 个 change 目录`）。⚠️ 我**第一次**把变异误写成 `len(change_ids)`（`_report` 作用域里没这个名字）
⇒ 直接 `NameError`、17 failed——那是我的失误，已重做为正确变异，结论以上面为准。

**R2-3（nit）｜新文案是全库唯一在 finding 里用 Markdown 粗体 `**…**` 的。**
`checkcmd.py:221` 的 `**归档 move 也算「挂了 change」**` 在终端 / CI 日志里是**字面星号**；
其余 finding（含同文件的其它几条）都写纯文本。非缺陷，只是风格不齐。

**R2-4（nit）｜`source_change_id` 的「取值」无人消费。** `contract.py:186` 的 `min(sorted(sources), key=len)`
（注释：「取最短的源 = 该归档目录本来是哪个 change」）——但全库只用 `is not None`（`archived` property，
`contract.py:60-62`）与 `_report` 的 `（归档）` 标注，**值本身读不到**。所以那句注释描述的取舍**不可观测**。

> ⚠️ 顺带一条**校准**（供下游别误读）：`docs/reviews/m1-acid-test.md:14` 与 `reviews/building-review.md`（R1 正文）
> 里引用的旧 `_require_change` 文案**已与今天的实现不同**——两处都是**带日期的历史记录**（后者是 R1 自身的原始输出），
> 按「不改历史」的原则**保持原样**是对的，不必同步。

### 结论（R2）

**PASS**。8 条全部收敛：I1/I2/I3/I4 有**可复跑的钉子**（我逐条变异确认抓住），I5/I7 的文档订正与实测**逐字一致**，
**I6 的顺序漂移真的是 bug、真的修好了**（改前 0 项/3 项随顺序翻转，改后四种组合全绿），
且**没有开出绕过口**（新接受的名字只能是真被搬进该目录的源；`change_id` 是攻击者自写字段、非授权闸、
全库无下游消费）；**I8 确认纯诊断**（findings 逐条不变、`0 个 change 目录` 子串保留、判定面一条未动）。
作者的两处关键说法（`13 failed / 10 passed`、`519 passed`）**逐字复现**。
新增 4 条非阻塞（R2-1/R2-2 是**两条行为变更没有测试钉子**，最值得在收尾前补上；R2-3/R2-4 是 nit）。

### 简报（R2，≤300 字）

**Verdict：PASS**（无阻塞，8 条全收敛）。**I6 实测**：改前同一逻辑 diff 会按顺序在 0 项/3 项间**翻转**
（我端到端跑到两个方向：`change_id='z'`+z 先 ⇒ 绿、改成 foo-z 先 ⇒ 红 3 项），改后**四种组合全绿**、
`accepted = 两种顺序的并`——**漂移真修好**；**未开绕过口**（配方 K：写无关的 `other` 仍红 3 项；配方 J 未授予；
且 `change_id` 是攻击者自写字段、全库无消费 ⇒ 非授权闸）。**I8 纯诊断**：findings 逐条不变（10=10），
`0 个 change 目录` 子串保留，判定面未动。I1 文案真改了、I2 招牌场景我复跑（base `EXIT=0` 空转绿 / HEAD
**恰好 1 项**点名硬门槛，三种变异都抓住）、I3/I4 钉子真实（M9 ⇒ 只它一条红）、I5/I7 与实测一致。
**`13 failed / 10 passed` 逐字复现**；全量 **519 passed**；回归面 85 passed；安全面 A–L 全 fail-closed。
**新阻塞项：无**；新非阻塞 4 条（R2-1/R2-2：I6 并集与 I8 计数**两条行为变更无测试钉子**；R2-3/R2-4 nit）。
