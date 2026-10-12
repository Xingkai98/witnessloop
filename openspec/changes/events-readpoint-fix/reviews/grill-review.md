# Grill: events-readpoint-fix 设计追问

> **结论**：D1/D2/D3/D4 四条决策**站得住**，修 `events.py:51` **值得做**；
> 但 **design 的中心前提（「`check` 崩成 traceback」）与实测不符**——今天**没有** traceback，
> 是 `entry.py` 兜住后的一行 `witnessloop：内部错误（UnicodeDecodeError: …）`（不点名文件、退 1）。
> 另有 **3 处读点分类错误**（`initcmd.py:201` 不是「无 try」；漏 `read_bytes` 两处；未定义族边界）。
> 实现前必须改写 `§0`/`§1`/`§4`/`§6` 的相应句子与 `spec.md` 的一条 Requirement
> ——否则会把**假的历史**写进 `README`/`docs/gate.md`，并留下一条**永远绿**的验收断言。

## Reviewer

- run id: grill-reviewer-events-readpoint-fix-2026-10-12
- 时间: 2026-10-12T08:37:07Z
- 零记忆审阅者（不读作者会话；只读 change 目录文本 + 只读仓库内容）
- 基线实测：`uv run pytest -q` ⇒ **413 passed**（与本 worktree 声明的基线一致）
- 所有实测在 `/tmp` 的**真 git 仓**上跑，本 worktree **未打补丁、`git status` 干净、未 commit**

## Confirmed Decisions

- **决策（D1）**：把读失败归一为 `EventError`（与「不是合法 JSON」同类型、同出路）；理由：**成立，且比 design 自己说的更强**——`load_events_file` 的**唯一**调用点是 `events.py:76`（`load_all`），`EventError` 的**唯一**消费者是 `checkcmd.py:167`，所以「单点修好即全覆盖」属实；并且**出路确实已现成**（见 D2 的实测）。**但 design 的论证前提必须改写**：`proposal.md:19,22`、`design.md:9,63-64`、`spec.md:12-13` 都说今天是「崩溃（traceback）」——实测**不是**（证据见 Code-Resolved 第 1 条）。真正的缺陷不是「有 traceback」，而是**把仓的问题报成工具故障**（`内部错误`）且**解码分支不点名文件**；这两条才是本 change 的价值，且都成立。来源: grill-reviewer-events-readpoint-fix-2026-10-12
- **决策（D2）**：`check` 侧不改（`checkcmd.py:167` 的既有 `except` 已够）；理由：**实测证实**。用合法 UTF-8 + 坏 JSON 的 events 文件（**未打任何补丁**）跑 `check`，今天就已经输出目标形态那条干净 finding：
  `6. .：事件文件无法解析：/tmp/e2e-jsonbad/openspec/changes/demo/workflow-events.jsonl:2 不是合法 JSON：Expecting value: line 1 column 1 (char 0)`
  ⇒ 修 `events.py` 后解码失败只是**走同一条现成的路**，`checkcmd` 一行都不用动。来源: grill-reviewer-events-readpoint-fix-2026-10-12
- **决策（D3）**：不做共用读文本 helper；理由：**成立**。全树 `read_text` 实测 **13 处**（`src/`：`events.py:51`、`policy.py:133`、`contract.py:176/231`、`evidence.py:165/224`、`initcmd.py:63/118/131/201/216`、`uninitcmd.py:30/77`），出路**实测 6 种**（`EventError` / `ValueError` / `PolicyError` / 静默 `None` / `Finding` / `print+EXIT_FAIL`），D3 说的「各不相同」属实。**但补一条更省的切法**：本仓**已有**一个成文 idiom —— `except (OSError, ValueError)`（`policy.py:134`、`contract.py:177/232`、`evidence.py:166`，`policy.py:134-136` 还专门注释了「`ValueError` 涵盖 `JSONDecodeError` **与** `UnicodeDecodeError`」）。若 Q1 一并修，应当**沿用这个 idiom**（一处补一个词），而不是逐点罗列异常名（`except (OSError, UnicodeDecodeError, json.JSONDecodeError)`）——后者与既有 4 处写法分叉，正是 D3 自己想避免的漂移面。来源: grill-reviewer-events-readpoint-fix-2026-10-12
- **决策（D4）**：文案点名文件 + 按成因分；理由：**成立，且有先例可抄**——`evidence.py:225-228` 已经写过完全相同的两分支（`except (OSError, UnicodeDecodeError)` + `why = "无法解码" if isinstance(exc, UnicodeDecodeError) else "无法读取"`），`docs/gate.md §8` 的表格也已经在用「解码失败 ≠ 文件读不到」这套措辞。**要求**：`events.py` 用**同一对词**（`无法解码` / `无法读取`），并把这套措辞钉进 `spec.md`（否则两处会各写各的）。混淆风险（design R3）实测**低**：既有条是**行级** `f"{path}:{lineno} …"`（`events.py:58/60`），新条是**文件级**（无 `:lineno`），形态本身就不同。来源: grill-reviewer-events-readpoint-fix-2026-10-12
- **决策（R4 + Q2 的结论方向）**：接受短路（不逐文件隔离）；理由：**方向对，但 design 给的理由是错的**（见 Open Questions Q2 与 Code-Resolved 第 8 条）。实测：`checkcmd.py:167-168` 直接 `return`，`for change in changes`（`:171-205`）整块**不再执行** ⇒ 所有受保护写入**都不再被评估**，design R4 的描述属实；但这**不是**新的坑——（a）现状**更差**：崩溃点在 `_protected_writes`（`checkcmd.py:100`）而 `_report` 在 `:102`，所以今天连其它 finding **一条都不打印**（实测：stderr 只有那一行「内部错误」）；修后至少给出全部 change 契约 finding + 这条；(b) **无绕过**：该 finding 自己就让 `check` 退 1，坏 events 文件**不可能**让 check 变绿。来源: grill-reviewer-events-readpoint-fix-2026-10-12
- **决策（`EventError` 的改动面）**：改 `events.py` 不会动到别处对这类型的假设；理由：全树 grep `EventError` 只有 3 个生产处——`events.py:24`（定义）、`:58`/`:60`（抛）、`checkcmd.py:167`（捕）；`guardcmd.py` **完全不 import** `events` ⇒ 「events 是 `check`-only、无 `guard` 路径」这一 scoping 属实（与 `guard-crash-exit` 的边界声明一致）。来源: grill-reviewer-events-readpoint-fix-2026-10-12

## Code-Resolved Questions

1. **「今天真的崩吗？是不是被谁兜住？」→ 不是 traceback，被 `entry.py` 兜住了。**
   证据：`src/witnessloop/entry.py:35-41`（`try: from witnessloop.cli import main … except Exception` ⇒ 打印 `witnessloop：内部错误（{type}: {exc}）`，`guard` 退 4、**其余动词退 1**）；`pyproject.toml:12` 与 `src/witnessloop/__main__.py` 都指向 `entry.main`，`tests/conftest.py:14,52` 的 `cli` fixture **也**走 `entry.main`。
   实测（真仓，onboard + 一个 change 目录 + 含 `0xff` 的 `workflow-events.jsonl`，`check --base <onboard>`）：
   ```
   $ uv run witnessloop check --root /tmp/e2e-events-repo --base <base>
   witnessloop：内部错误（UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 107: invalid start byte）
   EXIT=1
   ```
   进程内直调 `entry.main(["check", …])` 同样返回 `1`、stderr **无 `Traceback`**。
   ⇒ **spec.md 的验收句「SHALL 不出现未捕获异常的栈回溯」与 A5 的「不含 `Traceback`」今天就已经满足**，它们**钉不住**任何东西（详见 Q3）。
2. **「没有受保护写入的仓也会崩吗？`_protected_writes` 是否无条件调 `load_all`？」→ 会，而且比「没有受保护写入」更强。**
   证据：`checkcmd.py:100` 的 `findings += _protected_writes(root, pol, changes)` 在 `run()` 里**无条件**执行；`load_all` 是 `_protected_writes` 的**第一句**（`:166`），在 `for change in changes`（`:171`）**之前**。
   实测：(a) diff 只改一个**非受保护**文件（`src_notes.txt`）、坏 events 文件在 base 上 ⇒ **崩**（内部错误，退 1）；(b) **`--base feature --head feature`（空 diff、0 个变更文件）⇒ 照样崩**。
   ⇒ 这个读点是**全局的、与 diff 无关的**：只要仓里**任一 active change 目录**有坏 events 文件，该仓的**每一次** `check` 都走不到 `_report`。
3. **「`archive/` 下的坏 events 文件会崩吗？」→ 不会；`load_all` 的 glob 只有一层。**
   证据：`events.py:75` 是 `root.glob(f"{policy.changes_root}/*/{policy.events_file}")`——**单层 `*`**；归档布局是 `<changes_root>/archive/<id>/workflow-events.jsonl`（两层）。
   实测：把坏 events 文件放 `openspec/changes/archive/old-change/` ⇒ `check` **通过（EXIT=0）**，且实测 `glob hits: []`。
   ⇒ 两条后果：(a) 本 change 的覆盖面 = **active change 目录**，文档别写成「全部 events 文件」；(b) `known` 事件集**永远看不到已归档 change 的事件**（既有行为，本 change 不改变）。参见 R-G3。
4. **「Q1 列的读点全不全？」→ 方向对，但有 1 处分类错 + 1 处遗漏 + 已有 5 处需登记。**
   - **错**：`proposal.md:32` 与 `design.md:19` 把 `initcmd.py:201` 归入「**无 try**」。实际 `initcmd.py:200-204` **有** try，只是 `except json.JSONDecodeError`（`:202`）——它**同时**漏 `OSError` 与 `UnicodeDecodeError`，与 `:131`/`uninitcmd.py:30` 是**同一类**（补 except 元组，不是新包 try）。`tasks.md` 的 B1 沿用了这个错分类。
   - **漏**：`read_bytes` 读点 `initcmd.py:215`、`uninitcmd.py:59`（`sha256_bytes(path.read_bytes())`，**:215 无 try、:59 无 try**）——同一个「读不出 ⇒ 崩」族，只是没有解码那一半（mode-000 的 `.witnessloop/policy.json` 足以触发 `PermissionError`）。间接调用还有 `hashing.py:19/31/35`（`sha256_file`/`sha256_tree`），其中 `contract.py:373/386` 在 **`check` 主路径**上对报告/证据做 `sha256_tree` ⇒ 报告文件存在但不可读时，`check` 会在**证据正文那条守卫（`evidence.py:224`）之前**崩。
   - **已覆盖（核过，确认无需动）**：`policy.py:133-136`（`OSError, ValueError` → `PolicyError`）、`contract.py:176-177`（→ `None`）、`contract.py:231-232`（→ `Finding`）、`evidence.py:165-166`（→ `None`）、`evidence.py:224-228`（→ `Finding`，按成因分）。共 5 处。
   - **判据建议**：把族显式定义成「**`read_text` 文本读点**，落在 `check`/`init`/`uninit` 主路径上」，本 change 按 Q1 收口；`read_bytes`/`sha256_tree` 明写为**已知未覆盖**（见 Q1 推荐）。
5. **「D1 否掉『静默跳过坏文件』的理由站不站得住？」→ 结论站得住，但要区分：它给出的是**假红**，不是假绿。**
   静默跳过 ⇒ `known` 变小 ⇒ 依赖坏文件里那条事件的受保护写入会被报成「受保护路径被写入，但没有结构化解释事件」（`checkcmd.py:197-205`）——**fail-closed 的假红**，不是放行。所以 D1 的结论（选 `EventError`）是对的，而且理由可以更强：两条路**都红**，但 `EventError` 报的是**真原因**，静默跳过报的是**错原因**。design D1 的措辞「结论仍然错，只是错得更隐蔽」**方向对、程度说反了**（不是「更松」而是「更乱的假红」）。**注意**：这条**不**能用来否掉「逐文件隔离」——见 Q2。
6. **「D4 会不会与既有那条混淆？该带什么？」→ 低风险；带**文件级**成因句，不学行级形态。**
   既有：`events.py:58` `f"{path}:{lineno} 不是合法 JSON：{exc}"`、`:60` `f"{path}:{lineno} 事件必须是 JSON 对象`（**行级**）。
   新增应为**文件级、无 `:lineno`**：`f"{path} 无法解码：{exc}"` / `f"{path} 无法读取：{exc}"`（`path` 变量在 `load_events_file` 内已可用）。实测 wrap 后的完整形态（以既有的 JSON 坏为例，见 D2）是 `事件文件无法解析：<path>…`，新增条会落在同一位置 ⇒ 只要内层句不同即可区分。
7. **「改动 `events.py` 会不会动到别处？」→ 不会（见 Confirmed Decisions 末条）**；`guard` 侧无路径（`guardcmd.py` 不 import `events`），`checkcmd.py:167` 是唯一消费者。全树 `EventError` 命中 3 个生产位置。
8. **「R4 是改善还是换了个坑？」→ 是改善，但在 R4 的**原因**之外还有一处 design 没写的相邻变化（都是变好）。**
   实测/读码：`checkcmd.py:165-168` 短路发生在 `_protected_writes` 的**开头**，`for change in changes`（`:171-205`）整块跳过 ⇒ 受保护写入**全部**不再被评估（design R4 属实）。与现状相比：(a) 现状连 `_report`（`:102`）都到不了，**其它 finding 一条都不打印**；修后能打印（实测修后形态：`check：未通过 ✗（6 项）` + 6 条，其中第 6 条是 events 那条）；(b) 无绕过（见 Confirmed Decisions 的 R4 条）。
9. **「spec 的『权限问题与解码失败可区分』能测吗？权限用例怎么造？」→ 能，且有两种造法，但**只有一种在 root 下也成立**。**
   实测（uid=10001）：`chmod 000 openspec/changes/demo/workflow-events.jsonl` ⇒ `PermissionError: [Errno 13] Permission denied: '<abs path>'`（**可达**）。
   实测：`mkdir openspec/changes/demo/workflow-events.jsonl`（**目录冒充 events 文件**）⇒ `IsADirectoryError: [Errno 21] Is a directory: '<abs path>'`（**同样可达**，且 glob（`events.py:75`）不筛类型，目录会被收进来）。
   ⇒ **推荐测试用后者**：与 uid 无关（测试若跑在 root，`chmod 000` 的 `open()` 会成功 ⇒ 那条用例假绿），无需清理文件权限，`OSError` 分支照走。前者可作为补充用例并注明 root 前提。
10. **「本 change 会不会自伤？」→ 有一个**实证**的坑：不要碰别的 change 目录。**
    实测：一个 PR 里同时 (i) 改了 `openspec/changes/old-change/proposal.md`，(ii) 落了实现（`src/**`）⇒ `old-change` 被算进 `changed_change_ids`，于是 `checkcmd.py:91-98` 对**每个** change id 都要 `stage=building` 的 manifest ⇒ `old-change：无 stage=building 的 manifest` **必然红**（且它拿不出来）。
    而 `design.md:20`/`tasks.md:30` 说的「读点表里 `events.py` 那行（被 `guard-crash-exit` 标为『非目标』）」——**那行不在 `docs/gate.md §8`**：`docs/gate.md §8` 的读点表**只有 3 行**（`.witnessloop/policy.json` / `review manifest` / `grill 报告正文`，见 `docs/gate.md:305` 起的表格），**没有 events 行**；「非目标」字样在 `openspec/changes/guard-crash-exit/design.md:27`（另一个 change 的文档）。
    ⇒ `tasks.md` D1 的正确动作是**新增一行**（不是「改一行」），且**只改 `docs/gate.md`**，**绝不**编辑 `openspec/changes/guard-crash-exit/**`。参见 R-G2。
11. **「findings 的路径形态：相对还是绝对？」→ 实测是**绝对路径**，且 `Finding` 的 `path` 字段是 `"."`；这是既有行为，本 change 继承。**
    证据：`checkcmd.py:168` `contract.Finding(".", f"事件文件无法解析：{exc}")`；`load_all` 传的是 `root.glob(...)` 的结果，而 `root` 已在 `checkcmd.py:28` `resolve()` ⇒ 绝对路径。实测输出前缀为 `.：事件文件无法解析：/tmp/e2e-jsonbad/openspec/changes/demo/…`。
    对比：`check` 里其它 finding 全是**仓根相对**（`contract.py:31-33` 的 `Finding` docstring 明说「`path` 是**仓根相对**路径，方便 CI 里点回去」；`_protected_writes` 用 `pathutil.normalize`）。⇒ events 这条是**异类**，但**不是本 change 引入的**（JSON 坏那条今天同样如此）。见 Q4。

## Open Questions

- **Q1〔范围〕**：只修 `events.py`，还是一并修同族读点？若一并修，修到哪为止？
  **具体场景**：`.witnessloop/policy.json` 被 `chmod 000` 后再跑 `witnessloop init` ⇒ 今天是一行 `witnessloop：内部错误（PermissionError: …）`（退 1，方向本就正确）；`init --policy <含 0xff 的 seed>` ⇒ 同样是「内部错误」（`initcmd.py:64` 的 `except` 漏 `UnicodeDecodeError`，实测路径见 `:62-65`）。
  **注意**：design Q1 的理由「它们的严重度**低一档**（崩 = 退 1 = 失败，方向本就正确）」**不成立**——events 那条**同样**是「退 1 = 失败、方向本就正确」（`proposal.md:22` 自己就这么写的）。四处的**实际**差别只有「谁在跟前」（`check` = CI 里给人看 vs `init`/`uninit` = 本地一次性命令），不是严重度档位。真正该用的判据是「**改动成本 vs 漂移面**」。
  - ➡️ **推荐答案**：**一并修**，范围钉成「`read_text` 文本读点、落在 `check`/`init`/`uninit` 主路径」：`events.py:51`（新 try）+ `initcmd.py:118/216`、`uninitcmd.py:77`（新 try）+ `initcmd.py:63/131/201`、`uninitcmd.py:30`（**补 except 元组，统一写成 `except (OSError, ValueError)`**，沿用 `policy.py:134` 的既有 idiom）——并把 `tasks.md` 的 B1 里 `:201` 从「无 try」改成「补元组」。`read_bytes` 两处（`initcmd.py:215`、`uninitcmd.py:59`）与 `sha256_tree`（`contract.py:373/386`）写进 `design.md` 的**非目标**并注明理由（不同族：无解码语义；且 `OSError` 的 message 自带文件名 ⇒ 今天的「内部错误」已可定位），免得下次再问「为什么这里崩那里不崩」。
- **Q2〔短路 / R4〕**：坏 events 文件让受保护写入**整块**不再被评估——接受 + 写明，还是逐文件隔离？
  **具体场景**：PR 改了 `openspec/specs/foo/spec.md`（缺解释事件，本该报）**并且**另一个 change 的 `workflow-events.jsonl` 是坏的 ⇒ 修后只报「事件文件无法解析」一条，那条「缺解释事件」**不报**。两者都退 1，所以没有绕过；代价是**归因不完整**（人得先修 events 再重跑才知道还剩几条）。
  **design 原始理由的问题**：Q2 写「逐文件隔离会把『事件坏了』混进『没有解释事件』，反而更隐蔽」——这**把「逐文件隔离」与 D1 否掉的「静默跳过」混为一谈**。正确的逐文件隔离是**同时**报「这个 events 文件坏了」**并且**继续用其余文件评估 ⇒ 信息**更多**不更少，不存在「混进」。真正否掉它的理由应是：要改 `load_all` 的返回契约（如 `(events, errors)`）或让 `checkcmd` 逐文件 catch ⇒ **与 D2「不动 checkcmd」直接冲突**。
  - ➡️ **推荐答案**：**接受短路**（不逐文件隔离），但**把 Q2 的理由改写成上面那条**（D2 冲突 + 两条路都红 + 现状更差），并在 `docs/gate.md §4` 写明「一个坏 events 文件 ⇒ 受保护写入**整块**不再评估（仍然**红**，不是绿）」。**另注**：design R4 低估了影响面——短路与 diff **无关**（Code-Resolved 第 2 条：空 diff 也走这条路），受影响的是该仓**每一次** `check`。
- **Q3〔验收断言可判定性〕**：`spec.md` 里有两处**今天就已经绿**的断言，`tasks.md` A5 也把它们当「先红」：
  **具体场景**：`spec.md:12-13` 的「SHALL **不**出现未捕获异常的栈回溯」、`spec.md:35-38` 的「Scenario: 读失败前后都是『未通过』」，以及 `tasks.md:13-14` A5 的「`check` **不抛异常**、**非 0**、…**不含 `Traceback`**」。
  **实测**：把 A5 的这几条断言写成用例、**在未修的代码上**跑 ⇒ `不抛异常`/`非 0`/`不含 Traceback` **全部通过**（只有「stderr 含『事件文件无法解析』」是红的）。⇒ A5 不是（也不该宣称是）红先测试；「不含 Traceback」这条**永远绿**，钉不住任何东西。
  - ➡️ **推荐答案**：改写为**可判定**且**今天红、修后绿**的形态，例如把「不含 `Traceback`」换成「stderr **不含** `witnessloop：内部错误`」（实测：今天有、修后无）；`spec.md:12-13` 的绝对句改成「读失败 SHALL 得**一行点名文件的 finding**，SHALL **不**表现为 `witnessloop：内部错误`」；`spec.md:35-38` 那条 Scenario 明确标注为**回归护栏（不是红先）**，或直接删掉（它只重复了 Requirement 的语义）。同时 `spec.md:18` 的「stderr **是**…那条 finding」措辞应收成「stderr **含**…」（实测 stderr 还有 `check：未通过 ✗（N 项）` 表头和它前后的其它 finding）。
- **Q4〔诊断面形态〕**：events 那条 finding 的 `path` 是 `"."`、message 里是**绝对路径**，与 `check` 其余 finding 的仓根相对口径不一致（Code-Resolved 第 11 条；既有行为，非本 change 引入）。
  **具体场景**：CI 日志里出现 `6. .：事件文件无法解析：/home/runner/work/<repo>/<repo>/openspec/changes/x/workflow-events.jsonl 无法解码：…`——`/home/runner/work/…` 是 runner 的临时目录，而同一份输出里其它 finding 都是 `openspec/changes/x：缺少必需件 design.md` 这种可点回仓的形态。
  - ➡️ **推荐答案**：**本 change 不改**（保持与既有 JSON 坏那条逐字一致 ⇒ 不动 `checkcmd`，符合 D2），但**在 `design.md §4 风险` 里记一笔**接受。若用户想顺手一致化：让 `EventError` 携带**仓根相对**路径（或携带 `Path` 由 `checkcmd.py:168` 转相对），`checkcmd` 约 3 行改动 ⇒ 那是**显式的 D2 例外**，须写明。**不要**在 spec 里只写「点名文件」而不定形态——今天正是这个模糊导致 `.` + 绝对路径并存。

## 风险

- **R-G1（高·文档失真）**：若照 `design.md:64`（R1）、`design.md:84`（§6 D3）的措辞写 `README`/`docs/gate.md`——「此前会**崩溃**（`check` ⇒ **traceback**）」——就会把**假历史**写进接入方文档（`docs/gate.md §8` 已经有同样一句错的：「`check` ⇒ traceback」，见 `docs/gate.md` §8 的 ⚠️ 段）。实测今天 `check` 的形态是**一行** `witnessloop：内部错误（UnicodeDecodeError: …）`、退 1、**不点名文件**。**必须**把这几处（含 §8 既有那句）一并改写成实测形态，否则下一个人会据此做出错误判断（例如以为「有 traceback ⇒ 退出码会变」）。这也是本 change 唯一会**长期留痕**的错误。
- **R-G2（高·自伤）**：PR 里出现**任何**别的 `openspec/changes/<other>/**` 编辑 ⇒ 那个 change 被算进 `changed_change_ids`，而本次 diff 落了 `src/**` ⇒ 它也被要求 `stage=building` 的 manifest ⇒ **必红**（实测，见 Code-Resolved 第 10 条）。而 `design.md:20`/`tasks.md:30` 指向的「非目标那一行」恰好住在 `openspec/changes/guard-crash-exit/design.md:27`。⇒ 收口时**只改 `docs/gate.md`**；若真要改那个 change 的文档，须先接受它也会被要求 building 证据（几乎必然不值得）。
- **R-G3（中·覆盖范围）**：`events.py:75` 的单层 glob ⇒ `archive/**` 的 events 文件**既不会被读**（坏文件不崩、也不报）**也不会进入 `known`**（已归档 change 的事件不再提供豁免）。本 change **不改变**这个行为，但 `docs/gate.md §8` 新增那行必须写准覆盖范围是 **active change 目录**，别写「所有 events 文件」——否则又是一条会误导的文档。
- **R-G4（中·假绿测试）**：用 `chmod 000` 造「读不到」用法例，在 **root** 下（部分 CI 容器 / 本地 docker）`open()` 会成功 ⇒ `OSError` 分支根本走不到，用例会**假绿**。⇒ 主用例用**目录冒充**（实测同样触发 `IsADirectoryError`，与 uid 无关）。
- **R-G5（中·族边界漂移）**：`contract.py:373/386` 在 `check` 主路径上用 `sha256_tree`（`read_bytes`）算报告/证据 hash，**在读正文那条守卫（`evidence.py:224`）之前**。所以「报告文件存在但不可读」⇒ `check` 仍会退成一行「内部错误」。本 change 若不把族边界写清楚（Q1 推荐），这条会成为下一个「同一族的剩余成员」issue。
- **R-G6（低·流程）**：本 review 落盘后，change 目录新增了 `reviews/`，但 `reviews/*.manifest.json` 尚未产出 ⇒ 按 `docs/gate.md §3` 这是**孤儿报告**，本仓 `check` 会红。这是流程中间态（下一步 `manifest build --stage grill` 才绑），**不是**缺陷；但**别**在绑定前跑 `check` 并据此判断本 change 的成色。另：`reviews/` 是 `required_artifacts` 之一，本文件落盘同时消掉了「缺少必需件 reviews」那条红。

## User Confirmation

> **待停轮填写**（`templates/grill.md` 第 6 步）：Q1–Q4 逐条交用户裁定后，把「确认了什么 + 依据 + 时间」写在此处。
> 本报告**不得**替用户拍板，也**不得**把自己写的推荐当成用户的确认——在那之前，本 change 的 grill 证据**不完备**（`evidence.grill_evidence_findings` 会据此报红，这是 fail-closed 的正确行为）。
