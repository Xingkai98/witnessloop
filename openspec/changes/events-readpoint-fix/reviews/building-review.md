# Building Review: events-readpoint-fix

## Reviewer

- run id: `building-reviewer-events-readpoint-fix-2026-10-12`
- 时间: **2026-10-12T11:06:33Z**
- 被检 revision: `96199bc7c0b644d733f94339eee73efe22725b48`（`--base origin/main`，merge-base = `9210d9c`）
- 方式: **独立零记忆**实现审阅者（不读作者会话，只读 change 目录文本 + 仓库内容 + 实测）。
  默认实现有错：每条 `文件:行号` 自验；**6 条新用例逐条做变异检查**（改坏实现看是否真红）；
  4 个「逃逸变异」逐一在 `/tmp` 真 git 仓上复现其可达路径。**未 commit**，
  全部实验改动已 `git checkout HEAD --` 还原，收尾 `git status --porcelain` = **0 行**（唯一新增即本报告）。
- 环境: uid 非 root ⇒ `chmod 000` 真生效（无 R6 的 root 假绿干扰）；CLI 一律
  `uv run --project /home/happy/wl-wt/events-readpoint-fix witnessloop …`（**不用** PATH 上的裸 `witnessloop`）。
- 基线: `uv run pytest -q` ⇒ **419 passed**（21.81s）；`uv build` + `uvx --from <wheel> witnessloop --version`
  ⇒ `witnessloop 0.1.0`。

## Verdict

**PASS**

- **A1–A5 / B1–B4 / C1–C2 / D1–D3 逐项开门核实，全部真做完，0 个 ❌**（E0–E3 见下「任务逐项验证」的说明）。
- **6 条新用例逐条变异检查：无一假测试**——每条都至少有一个让**它自己**变红的实现改动（表格见「变异检查」）。
  关键那条端到端用例在**未打补丁**时**确实红**：实测 `5 failed, 1 passed`，与 `tasks.md` 的实测记录**逐字相符**。
- **文档与实现逐字相符**（含 §8 那句被订正过的「`check` ⇒ traceback」——实测确为**一行**「内部错误」、
  **不是 traceback**；以及「坏 events ⇒ 受保护写入整块不再评估、仍然是**红**不是绿」——两条我都独立复现）。
- 无阻塞项。发现 **4 个逃逸变异**（= 4 处「实现正确但**无任何测试钉住**」的覆盖缺口，均在可达路径上，
  退化成「内部错误」而非绕过面）与 5 条非阻塞观察，全部见 Issues。

## 任务逐项验证

> 声明（勾）一律不信；下面每条的 ✅ 都是我自己读 `文件:行号` 或跑出来的。
> ⚠️ `design.md`/`tasks.md` 引用的行号是**打补丁前**的编号（如 `initcmd.py:118/216`、`:63/131/201`、
> `uninitcmd.py:30/77`）；本报告的编号一律是**当前 HEAD** 的。

### A. `events.py` 读点归一

- **A1** ✅ `tests/test_events_readpoint.py:37-44` 用例在场；实现在 `src/witnessloop/events.py:50-57`
  （`except (OSError, UnicodeDecodeError)` → `raise EventError`）。**未被钉成假测试**：回退整段 try
  ⇒ 该用例红；`why` 写死 ⇒ 红（见变异 M2/M3/M4）。
- **A2** ✅ `tests/test_events_readpoint.py:47-55`（`path.mkdir()` 造 `IsADirectoryError`，与 uid 无关）；
  文案「无法读取」与「无法解码」**可区分**（`events.py:56` 的 `isinstance` 分支）。变异 M2 ⇒ 红。
- **A3** ✅ `tests/test_events_readpoint.py:58-75`：合法文件正常解析 **且** 逐行 JSON 错误的**行级**文案
  「不是合法 JSON」不变（`events.py:66`）。变异 M5（改这几个字）⇒ 红。
- **A4** ✅ `events.py:50-57` 就是「读点包 try ⇒ `EventError`」；`checkcmd.py` **一字未改**——
  `git diff origin/main...HEAD -- src/witnessloop/checkcmd.py` 为空，`checkcmd.py:167` 的
  `except events_mod.EventError` 是既有代码（与 D2 一致）。
- **A5** ✅ `tests/test_events_readpoint.py:78-93`：断言 `"事件文件无法解析" in err` **且**
  `INTERNAL_ERROR not in err`。**未打补丁时真红**（见「实测复现」第 1 条），且红的正是这条断言链。

### B. 同族剩余读点（Q1 一并修）

- **B1** ✅ 四处 `except` 元组都补成 `(OSError, ValueError)`（D3 的多数派 idiom）：
  `initcmd.py:64`（`--policy`）、`initcmd.py:139`（`ledger_gate_ref`）、`initcmd.py:213`（台账）、
  `uninitcmd.py:31`（台账）。`git diff` 逐处比对确认**不是**「无 try」（原稿结论对）。
- **B2** ✅ 三处新包 try 都在：`initcmd.py:119-125`（`conflicting_files`，按 design §3 的定案**抛 `ValueError`**
  ⇒ 调用方报一行诊断并退 1，**没有**让 `None` 流进 `render_diff`）、`initcmd.py:227-234`（drift）、
  `uninitcmd.py:75-82`（冲突 diff）。`conflicting_files` 的**两处调用点都接住**：
  `initcmd.py:170-174`（未接入路径）与 `initcmd.py:255-259`（已接入路径），且 `conflicting_files`
  全树只有这两个调用点（`grep -rn conflicting_files src/ tests/`）。
- **B3** ✅ `tests/test_events_readpoint.py:96-103`（`init`）与 `:106-113`（`uninit`），两条都**用非法 UTF-8**、
  都断言「非 0 + 点文件 + **不含内部错误**」。变异 M7/M9 分别打红对应那一条。
- **B4** ✅ 非目标登记在 `design.md:134-144`（`read_bytes` 两处、`sha256_tree`、「半成品 `init`」、`KeyboardInterrupt`）。
  「半成品 `init`」我复现过：未接入 + `.witnessloop/init-manifest.json` 是**目录** ⇒ 先落下
  `policy.json` + `.github/workflows/witnessloop.yml`、再在写台账处 `IsADirectoryError` ⇒ 一行「内部错误」退 1
  （**登记属实**，本 change 未碰写点）。

### C. 回归

- **C1** ✅ 全量 419 绿；`tests/test_check_protected.py` / `tests/test_invariants.py` / `tests/test_acceptance.py`
  等既有 events 语义用例**0 条改动、0 条变红**（`git diff --stat` 里 `tests/` 只有新增那一个文件）。
- **C2** ✅ `uv run pytest -q` ⇒ **419 passed**。基线 413 的算术自洽：419 − 6（新文件恰 6 条用例）= 413，
  与 `tasks.md` 的「419 = 基线 413 + 6」及前两轮审阅独立测得的 413 一致。

### D. 文档

- **D1** ✅ `docs/gate.md:350` 新增 events 行（该表此前**只有 3 行、无 events 行**，原稿说「改一行」确是错的）；
  覆盖范围写在 `docs/gate.md:227-228`「**active** change 目录；`archive/**` 既不会被读、也不提供豁免」——
  **我实测过**：把事件只放进 `archive/<id>/`（合法）⇒ **不给豁免**（受保护写入那条 finding 照出）；
  放成**坏文件** ⇒ check 不崩、无 events finding。且 `git diff --stat` 确认**只改了 `docs/gate.md`**，
  未编辑任何别的 `openspec/changes/<other>/**`（R2 自伤面为 0）。
- **D1b** ✅ `docs/gate.md:352-355` 的错话已订正为「一行 `witnessloop：内部错误（…）`——**不是 traceback**」，
  并写明成因（进程入口 `entry.py` 兜住）。**实测相符**（见「实测复现」第 2 条）。
- **D2** ✅ `docs/gate.md:221-228` 补了「读不出来怎么办」。三条断言逐条实测：一行点名文件的 finding ✅、
  不再「内部错误」✅、退出码不变 ✅。「受保护写入那一整块不再被评估 / 仍然是红不是绿 / 没有绕过面」✅
  （见「实测复现」第 3 条）。⚠️ 只有一句措辞过宽，见 Issues ②。
- **D3** ✅ `README.md:108-110`（「解码失败 / 读不到」此前都是工具故障、现在是一行点名文件的 finding、
  退出码不变）。「读不到」这一半我**单独实测**过：用**目录**冒充 events 文件、**未打补丁** ⇒
  `witnessloop：内部错误（IsADirectoryError…）`、EXIT=1（见「实测复现」第 2 条的姊妹探针）。
- **E0** ✅ 两份 manifest 在场且 `stage` 正确（`reviews/grill.manifest.json`、`reviews/grill-adversarial.manifest.json`）。
- **E2** ⚠️ 勾了 `[x]`，但 HEAD 上 change 目录里**没有** `reviews/building-review.md` / `building.manifest.json`
  ⇒ 该勾**超前**（本报告即该产物）。**非阻塞**，同类「超前勾选」在 `guard-crash-exit` 的 building review 里也被记为非阻塞。
- **E1/E3** 未勾 —— 与设计一致（收尾在 build 证据之后）；我复核 `check` 现状确实**红 5 条**
  （2 条 grill manifest 的 `tasks_hash` 漂移 + 2 条 stale + 1 条缺 building manifest），正是 E1 要做的。

## 变异检查（每条新用例是否真能红）

全部变异用**精确串替换**改源码（`/tmp/mutate.py`），跑完立刻还原（收尾 `git status` 干净）。
`M6/M6b/M8/M10` 是**我另加的**「实现点是否有测试钉住」探测，不属于「新用例是否真能红」那一类，单独列在 Issues ①。

| 新用例 | 改坏哪一处 | 结果 |
|---|---|---|
| `test_illegal_utf8_becomes_an_event_error` | 回退 `events.py:50-57`（未打补丁） | **红** ✅ |
| 同上 | `events.py:56` `why` 写死「无法读取」（M3） | **红** ✅（只有这条红） |
| 同上 | `events.py:57` 去掉路径（M4） | **红** ✅（只有这条红） |
| `test_unreadable_file_becomes_an_event_error` | 回退 `events.py:50-57` | **红** ✅ |
| 同上 | `events.py:56` `why` 写死「无法解码」（M2） | **红** ✅（只有这条红） |
| `test_valid_events_still_parse` | `events.py:66` 行级文案改字（M5） | **红** ✅ |
| `test_check_reports_a_clean_finding_for_an_undecodable_events_file` | 回退 `events.py:50-57` | **红** ✅（先红在「含事件文件无法解析」那条断言上） |
| `test_init_reports_a_clean_error_for_an_undecodable_landed_file` | 回退 `initcmd.py:227-234`（drift 读点无 try，M7） | **红** ✅（只有这条红） |
| `test_uninit_reports_a_clean_error_for_an_undecodable_ledger` | `uninitcmd.py:31` `except` 回退成 `json.JSONDecodeError`（M9） | **红** ✅（只有这条红） |

**「端到端那条」专门核过两件事**（题面点名）：
1. 它**未打补丁时红**——不是「今天本来就绿」的假红先；
2. 它断言的两条**分别**可判定：`"事件文件无法解析" in err` 与 `INTERNAL_ERROR not in err`。
   未打补丁时 stderr **就是**那一行内部错误全文，故 `not in` 那条**今天为假**（`tasks.md` 的说法属实）。

**结论：6/6 新用例都是真测试，0 个假测试。**

## Issues

- **[非阻塞] ① 4 个「逃逸变异」：改坏实现后**全量仍绿**（实现正确，但**无测试钉住**）。**
  逐个都在**可达路径**上复现过（改坏 ⇒ 用户拿回「内部错误」；补丁在位 ⇒ 干净诊断），
  即它们是**真实的覆盖缺口**、不是死代码：

  | 变异 | 位置 | 改坏后全量 | 可达路径复现（改坏 ⇒ 现象） |
  |---|---|---|---|
  | M6 | `initcmd.py:119-125`（`conflicting_files` 的读点，design §3 唯一定过案的地方） | **仍绿**（`tests/test_events_readpoint.py` 6 passed） | 未接入 + `.witnessloop/policy.json` 是**目录** ⇒ `witnessloop：内部错误（IsADirectoryError…）`；补丁在位 ⇒ `init：.witnessloop/policy.json 无法读取：…`、退 1 |
  | M6b | 同上但把 `None` 塞进 `render_diff`（design 明说**必须消灭**的形态） | **仍绿**（`test_events_readpoint.py` + `test_init.py` + `test_init_policy.py` 共 30 passed） | 同上场景 ⇒ 先打印「检测到冲突…」**再**`witnessloop：内部错误（AttributeError: 'NoneType' object has no attribute 'splitlines'）` —— design 的预言**逐字命中** |
  | M8 | `uninitcmd.py:75-82`（uninit 的冲突 diff 读点） | **仍绿**（`test_events_readpoint.py` + `test_init.py` + `test_uninit.py` 共 28 passed） | `init` 后把 `.witnessloop/policy.json` 写成非法 UTF-8 ⇒ 改坏：`witnessloop：内部错误（UnicodeDecodeError…）`；补丁在位：`  ! .witnessloop/policy.json 无法解码` |
  | M10 | `initcmd.py:213`（`init` 台账自身的读点） | **仍绿**（`test_events_readpoint.py` + `test_init.py` 共 17 passed） | 台账写成非法 UTF-8 ⇒ 改坏：`witnessloop：内部错误（UnicodeDecodeError…）`；补丁在位：`init：.witnessloop/init-manifest.json 无法解析：…` |

  ⚠️ 其中 **M10 与已测的 `uninitcmd.py:31` 是同一条修正的镜像**（台账非法 UTF-8），只有 `uninit` 那半有测试
  ——正是本仓自己反复强调要防的「修正只落一份」。**为什么不阻塞**：四处行为**都已正确**（我逐条实测），
  退化后果只是**诊断文案退回「内部错误」**，退出码仍是 1（仍红），**不产生绕过面**、不使任何 spec 要求落空
  （本 change 的 spec delta 只对 `workflow-events.jsonl` 提要求，且全部满足）。
  **建议修法（便宜）**：补 2~3 条即可盖住 4 处——(a) 给 `conflicting_files` 加一条单测（未接入 + 目录冒充
  `policy.json` ⇒ `ValueError` 且文案含 `无法读取`）——它同时把「不得把 `None` 塞进 `render_diff`」钉死；
  (b) 把 `uninit` 台账那条**镜像**成 `init` 台账版本（打 `initcmd.py:213`）；`uninitcmd.py:75-82` 用
  「已落地文件被改且非法 UTF-8」造（配方见 M8 那行的复现命令）。

- **[非阻塞] ② `docs/gate.md:224-226` 一句过宽：「你只会看到这一条 finding」。**
  实测（坏 events 复现）：`check` 仍然打印**其它块的** finding——我只多写了一个 change 目录 + 一个受保护 spec 写入，
  就打印了 **3 条**（2 条 change 契约 + 1 条 events）。被抑制的**只有 `_protected_writes` 那一块**的 finding。
  且紧跟的一句「**先修 events 再重跑，才知道还剩几条**」本身就预设了还有别的 finding ⇒ 两句自相矛盾。
  **建议修法**：把「⇒ 你只会看到这一条 finding」改成「⇒ **受保护写入**的 findings 会**全部**不再产出；
  其它块（change 契约 / manifest / building 门禁）的 finding 照常打印」。

- **[非阻塞] ③ `init` 的 drift 路径把**占位字符串**喂进了 `render_diff`**（`initcmd.py:232`，
  与它自己的注释「**不硬编 diff**」不符）。实测输出：

  ```
  init：已接入，但 init 创建的文件被改动过（拒绝覆盖）：
  --- a/.witnessloop/policy.json（当前）
  +++ b/.witnessloop/policy.json（witnessloop init 将写入）
  @@ -1 +1,34 @@
  -（无法解码）+{
  ```
  即「当前内容」被渲染成一行 `（无法解码）`，且因无换行与 `+{` 挤在一起 ⇒ 看着像真 diff。
  它**不崩、点名了文件（diff 头）、退 1、确定性**，故不阻塞；但**兄弟路径**（`uninitcmd.py:80`）用的是
  既有的 `  ! <rel> 无法解码` 形状，两处**不一致**。
  **建议修法**：drift 那条照抄 uninit：`print(f"  ! {rel} {why}", file=sys.stderr)`（或至少不把占位文本当内容）。

- **[非阻塞] ④ `docs/gate.md:350` 「坏文件会让**每次** `check` 都短路」**：短路的**主体**是
  `_protected_writes` 那一块，不是整个 `check`（§4 的表述是准的：它写了「受保护写入那一整块」）。
  建议加两字：「会让每次 `check` 的**那一块**短路」。

- **[非阻塞] ⑤ `docs/gate.md:352-353` 这句被订正的话跨了两个世代**：前半句「损坏的证据文件此前会**崩**
  （`guard` ⇒ 退 1 被当 block **误拦**…）」说的是 `guard-crash-exit` **之前**；后半句（本 change 订正的部分）
  说的是 `guard-crash-exit` **之后**（一行「内部错误」）。且对**本 change 新增的 events 行**而言，
  `guard` 半边根本不适用（events 是 `check`-only，`guardcmd.py` 完全不 import `events`——我复核过）。
  **建议**：把 `guard` 半边标注世代，或拆成两句。（订正本身**没错**，我实测过。）

> **另核过的、结论为「无问题」的点**（题面点名或本仓易踩）：
> `conflicting_files` 只被那两处调用且都接住；`EventError` 全树仍只有
> `events.py:24`（定义）/`:57`（抛）/`checkcmd.py:167`（捕）三个生产位置，无第三个消费者会把它变成「内部错误」；
> `guardcmd.py` 与 `events` 零耦合；退出码常量未动（`check` 一律 1，`EXIT_FAIL`）；
> 文档里**没有**「没有任何产品路径会吐 traceback」这类绝对句——`design.md:26-28` 与 `proposal.md` 都收成了
> 「**非交互**」并点明 `KeyboardInterrupt` 例外。

## 实测复现

```console
# 0. 环境与基线
$ export PATH=/home/happy/.local/bin:$PATH
$ uv run pytest -q                      ⇒ 419 passed in 21.81s
$ uv build --out-dir /tmp/wlbuild && uvx --from /tmp/wlbuild/*.whl witnessloop --version
                                        ⇒ witnessloop 0.1.0

# 1. 未打补丁（git checkout origin/main -- src/witnessloop/{events,initcmd,uninitcmd}.py）
$ uv run pytest tests/test_events_readpoint.py -q
  ⇒ 5 failed, 1 passed        （绿的正是「合法 events 行为不变」那条回归——与 tasks.md 记录逐字相符）
  端到端那条先红在：  assert '事件文件无法解析' in "witnessloop：内部错误（UnicodeDecodeError: …）"
  ⇒ 该用例的「不含内部错误」断言今天**确为假**（stderr 就是那一行）

# 2. 文档 §8 那句「此前是一行内部错误、不是 traceback」+ README 的「读不到」
$ printf '{"event_type": "protected_path_write", "x": "\xff\xfe"}\n' > <repo>/openspec/changes/add-x/workflow-events.jsonl
$ uv run witnessloop check --root <repo> --base main --head HEAD     # 未打补丁
  witnessloop：内部错误（UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 45: …）
  EXIT=1                              ⇒ 一行、无 Traceback、且**其它 finding 一条都不打**（_report 根本没跑到）
$ mkdir <repo>/openspec/changes/add-x/workflow-events.jsonl          # 「读不到」：目录冒充，未打补丁
  witnessloop：内部错误（IsADirectoryError: [Errno 21] Is a directory: '…/workflow-events.jsonl'）
  EXIT=1                              ⇒ README「读不到此前也是工具故障」属实

# 3. 修后（还原补丁）+ 同场景：一行点名文件的 finding；受保护写入那块确实不再评估；仍然红
$ uv run witnessloop check --root <repo> --base main --head HEAD
  check：未通过 ✗（3 项）
    1. openspec/changes/add-x：缺少 review manifest（…）
    2. openspec/changes/add-x：无 stage=grill 的 manifest（…）
    3. .：事件文件无法解析：<abs>/openspec/changes/add-x/workflow-events.jsonl 无法解码：'utf-8' codec …
  EXIT=1
  ⚠️ 我故意在同一个 PR 里无解释地改了受保护文件 openspec/specs/foo/spec.md：
     「受保护路径被写入，但没有结构化解释事件」那条 finding **消失了**（对照：events 合法时它会打印）
     ⇒ §4 的「整块不再评估 / 仍然是红不是绿 / 没有绕过面」属实；但「你只会看到这一条 finding」不属实（见 Issue ②）

# 4. 与 diff 无关（spec 的「回归护栏」Scenario，无对应用例）
$ uv run witnessloop check --root <repo> --base HEAD --head HEAD     # 空 diff
  check：基线 HEAD...HEAD，0 个变更文件，0 个 change 目录
    1. .：事件文件无法解析：… 无法解码：…        EXIT=1     ⇒ 读点确实与 diff 无关

# 5. 配方纪律（题面第 3 条）——「事件族用目录、init/uninit 用非法 UTF-8」这个分工**有必要**
$ <已接入仓> rm .witnessloop/policy.json && mkdir .witnessloop/policy.json && uv run witnessloop init --root .
  witnessloop：内部错误（IsADirectoryError: … '/tmp/rec1/.witnessloop/policy.json'）     # 补丁在位也红
  ⇒ 「目录」触发的**第一个**失败点是族外的 read_bytes（initcmd.py:226）——用它写 init 用例**永远红**
$ <已接入仓> rm .witnessloop/init-manifest.json && mkdir .witnessloop/init-manifest.json && uv run witnessloop uninit --root .
  uninit：未接入（或已回滚），无改动。   EXIT=0       # :24 的 is_file() 直接放行，根本到不了读点
$ <已接入仓> rm .witnessloop/policy.json && mkdir .witnessloop/policy.json && uv run witnessloop uninit --root .
  witnessloop：内部错误（IsADirectoryError: … '/tmp/rec3/.witnessloop/policy.json'）   # 同族外 read_bytes（:59）
$ check + events 是**目录**：`  3. .：事件文件无法解析：… 无法读取：[Errno 21] Is a directory: …`   EXIT=1
  ⇒ events 族**两种配方都行**（load_events_file 没有 read_bytes）；init/uninit **只能用非法 UTF-8**。
     tasks.md B3 / design §5 / spec.md 的这条警告**逐字属实**（我在三条路径上分别复现）。

# 6. archive 覆盖范围（§4 新增声明的范围）
$ 事件只放 openspec/changes/archive/add-x/workflow-events.jsonl（合法）⇒ 受保护写入那条 finding **照出**（不给豁免）
$ 把它写成非法 UTF-8 ⇒ check 不崩、**无** events finding（glob 是单层，archive/** 不被读）
```

**收尾**：所有变异/探针改动已还原，`git status --porcelain` = **0 行**（唯一写入 = 本报告文件本身）。
