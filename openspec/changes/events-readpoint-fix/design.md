# Design: events-readpoint-fix

> 状态：**草稿**（待设计 grill + 对抗验证收敛 → 停轮用户确认）。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。

## 0. 一句话

`events.py` 的读点**补上它本来该有的那层 try**：读不出 ⇒ 抛 `EventError`（与「不是合法 JSON」同出路）
⇒ `check` 由 **traceback 崩溃**变成**一行可诊断的干净红**。

## 1. 现状（实测）

- `events.py:49-57`：`load_events_file` —— 循环里**逐行** JSON 解析有 `except json.JSONDecodeError → EventError`（`:56-58`），
  但**整个文件的 `read_text`（`:51`）没有任何 try** ⇒ 读失败（解码 / 权限）直接冒泡。
- `checkcmd.py:166-168`：`_protected_writes` 只捕 `events_mod.EventError`，转成
  `Finding(".", f"事件文件无法解析：{exc}")` ⇒ **出路已经现成**，缺的只是让读失败也走这条。
- `events.load_all`（`:72-77`）遍历 `<changes_root>/*/<events_file>` 逐个调 `load_events_file` ⇒ 单点修好即全覆盖。
- **同族剩余成员**（立项时逐点核，见 proposal 的表）：`initcmd.py:63/131`、`uninitcmd.py:30` 的 `except` 元组漏
  `UnicodeDecodeError`（`uninitcmd` 连 `OSError` 都漏）；`initcmd.py:118/201/216`、`uninitcmd.py:77` **无 try**。
- **前一个 change 的边界声明**：`guard-crash-exit` 的 design §3「非目标」把 `events.py:51` 列为非目标并指向本 issue
  ⇒ 本 change **收口**时须同步更新那张读点表（§文档影响）。

## 2. 决策

### D1 归一到 `EventError`（**文件自己的错误契约**）

- `events.py` 里「这片内容不是合法的 events」**已经**用 `EventError` 表达（`:56-58`、`:60`）。读不出是**同一类**
  「这份文件不能当事件用」⇒ 复用同一类型。
- **收益**：`checkcmd` 的既有 catch 直接把 `guard`/`check` 语境下的它变成**一行 finding**（无需改 checkcmd），
  且**报错文案自动点名文件**（`EventError` 的文案里带 `path`）。
- 备选（否）：让读失败**静默跳过**该文件 ⇒ **不行**：那会把「事件文件坏了」变成「没有解释事件」，
  从而把「受保护写入有此事件」误判成「无解释」⇒ **结论仍然错**，只是错得更隐蔽。
- 备选（否）：抛 `OSError`/`UnicodeDecodeError` 原样上抛 ⇒ 现状。

### D2 `check` 侧**不改**（出路已现成）

`checkcmd._protected_writes` 已有 `except events_mod.EventError` ⇒ D1 之后自动变干净红。
**不为本 change 动 checkcmd**——少改一处就少一处漂移面。

### D3 **不做抽象层**（明确否掉「共用读文本 helper」）

- 全树 `read_text(encoding="utf-8")` 有 10+ 处，但**各自的错误类型与出路不同**
  （`EventError` / `ValueError` / `PolicyError` / 静默 `None`）⇒ 一个「统一 helper」要么带错误类型参数
  （= 抽象没省掉什么），要么把不同语义拍平（= 引入新的一致性面）。
- 本仓既有取向：「**三行相似代码好过一个过早的抽象**」。⇒ 本 change **只修实际有危害的读点**，
  不做全局重构。（若 Q1 决定一并修 `initcmd`/`uninitcmd`，也是**同一种本地修补**，不是抽象。）

### D4 文案：点名**文件**与**成因**

`EventError` 的文案 SHALL 含文件路径；成因按类型分（解码失败 vs 读不到），避免把权限问题报成「不是合法 JSON」。
（口径与 `guard-crash-exit` 的 D4 一致：**文案按成因分**。）

## 3. 接线点（实现清单）

- `src/witnessloop/events.py`：`load_events_file` 的读点包 try ⇒ 抛 `EventError`。
- **（若 Q1 选一并修）** `src/witnessloop/initcmd.py`（`:63`/`:131` 的 except 元组；`:118`/`:201`/`:216` 的读点）、
  `src/witnessloop/uninitcmd.py`（`:30` 的 except 元组补 `OSError`+`UnicodeDecodeError`；`:77` 的读点）。
- `tests/`：`events.py` 单测 + `check` 端到端（**不抛异常**、非 0、文案是那条 finding、无 traceback）。
- 文档：`docs/gate.md §8` 的读点表（把 `events.py` 从「非目标」改为已覆盖）+ `docs/gate.md §4`（结构化解释事件）补一句。

## 4. 风险

1. **R1（中）**：把「读不出」归一到 `EventError` ⇒ `check` 由**崩溃（退 1）**变成**干净红（退 1）**——
   **退出码不变**，但**行为变了**（不再 traceback）。对**接入方**是**报错形态变更**（不是新的红），须写明。
2. **R2（低）**：若 Q1 选一并修 `init`/`uninit` ⇒ 改动面扩大；那两处的「崩」退 1 = 失败（方向正确），
   修它是**可用性**改善，须各自有回归测试。
3. **R3（低）**：`EventError` 的文案若与既有那条（「不是合法 JSON」）混同，会误导 ⇒ D4 要求按成因分。
4. **R4（低）**：`load_all` 一旦抛 `EventError` ⇒ **整个 `check` 提前返回**那条 finding
   （`_protected_writes` 直接 return）⇒ 受保护写入那一整块**不再被评估**。这与**现状的崩溃**相比是改善
   （现状连 finding 都没有），但**须写明**：一个坏的 events 文件会让整个受保护写入检查短路。

## 5. 测试策略（TDD）

- **先红**：`load_events_file`（非法 UTF-8）⇒ 抛 `EventError`（当前抛 `UnicodeDecodeError`）。
- **先红**：`check` 端到端——含非法 UTF-8 events 文件的仓 ⇒ **不抛异常**、非 0、stderr 含「事件文件无法解析」、
  **不含 `Traceback`**。
- **回归**：合法 events 的既有用例（受保护写入豁免）全绿。
- **（若 Q1 选一并修）**：`init`/`uninit` 各自的「读不出 ⇒ 干净报错 + 非 0」用例。

## 6. 文档影响

- `docs/gate.md §8`：读点表里 `events.py` 那行（前一个 change 标为「非目标」）改为**已覆盖**。
- `docs/gate.md §4`（结构化解释事件）：补「事件文件读不出 ⇒ 干净的 finding（不是崩溃）」。
- `README.md`：**对**接入方**是报错形态变更**（不是新红）——按 R1 写明。

## 7. Pre-Implementation Review

> 待 grill + 对抗验证后填写。

## 8. Open Questions（停轮待用户确认）

- **Q1** **范围**：只修 `events.py`（`check` 主体，issue #12 的本体），还是**一并修** `initcmd`/`uninitcmd` 的
  同族读点（把这类彻底关掉）？**我倾向一并修**——都是**本地一行级**修补，且「读不出 ⇒ 崩」这条族一旦留着，
  下次还会有人问「为什么这里崩那里不崩」；但它们的严重度**低一档**（崩 = 退 1 = 失败，方向本就正确）。
- **Q2** 坏 events 文件会让 `_protected_writes` **整个短路**（R4）——可接受（现状更差），还是应当
  **逐文件**隔离（一个坏文件只让**它自己**那段失效）？**我倾向接受 + 写明**：逐文件隔离会把「事件坏了」
  混进「没有解释事件」，反而更隐蔽。
