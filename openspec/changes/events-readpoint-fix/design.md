# Design: events-readpoint-fix

> 状态：**草稿**（grill 已回写 §0/§1/§2/§4/§5/§6 —— 它**证伪了原稿的中心前提**；待对抗验证 → 停轮）。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。
> 审阅证据：`reviews/grill-review.md`（决策记录）。

## 0. 一句话

`events.py` 的读点补上它本该有的那层 try（**沿用本仓既有 idiom `except (OSError, ValueError)`**）：
**读不出来 ⇒ 抛 `EventError`** ⇒ `check` 从「**把仓的问题报成工具故障**」变成**一行点名文件的干净 finding**。

## 1. 现状（实测）

### 1.1 ⚠️ **grill 证伪了原稿的中心前提**：「`check` 崩溃成 traceback」**不成立**

原来我写的是「`check` ⇒ 一大段 traceback」。**grill 在真 git 仓上实测**，今天真实的形态是：

```console
$ witnessloop check --root <含 0xff 的 workflow-events.jsonl 的仓> --base <base>
witnessloop：内部错误（UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 107: …）
EXIT=1                      ← **没有 Traceback**
```

原因：change `guard-crash-exit` 加的**进程入口兜底**（`entry.py:35-41`）把它接住了 ⇒ 一行诊断、退 1
（`pyproject.toml:12` / `__main__.py` / 连 `tests/conftest.py` 的 `cli` fixture 都走 `entry.main`）
⇒ **没有任何产品路径会吐 traceback**。

⇒ **真正的缺陷不是「有 traceback」**，而是这两条：

1. **把仓的问题报成工具故障**——`内部错误` 会让读者以为 **witnessloop 坏了**，而不是「**你的 events 文件坏了**」；
2. **解码分支不点名文件**（`OSError` 分支的 message 自带路径，解码分支不带）。

**⚠️ 本 change 的文档一律不得写「此前会崩溃 / traceback」**（那会变成长期留痕的**假历史**，见 R1/R-G1）。

### 1.2 这个读点是**全局的、与 diff 无关的**（比原稿说的更严重）

`checkcmd.py:100` **无条件**调 `_protected_writes`；`load_all`（`:166`）是它的**第一句**，在 `for change in changes`（`:171`）**之前**。
**实测**：连**空 diff**（`--base feature --head feature`，0 个变更文件）**照样**走这条路
⇒ 只要仓里**任一 active change 目录**有坏 events 文件，该仓的**每一次** `check` 都到不了 `_report`（`:102`）
——**连其它 finding 一条都不打印**。这是**现状**，比原稿 R4 说的更差。

### 1.3 覆盖范围 = **active** change 目录（不是「所有 events 文件」）

`events.py:75` 的 glob 是**单层** `f"{changes_root}/*/{events_file}"` ⇒ `archive/<id>/workflow-events.jsonl`（**两层**）
**既不会被读**（所以坏文件**不崩**，实测 `glob hits: []`）**也不会进入 `known`**
（已归档 change 的事件**不再提供豁免**）。这是**既有**行为，本 change 不改变它——但**文档必须写准范围**（R-G3）。

### 1.4 出路**已现成**（实测）

用**合法 UTF-8 + 坏 JSON** 的 events 文件（**未打任何补丁**）跑 `check`，今天就已经是目标形态：

```
6. .：事件文件无法解析：<abs>/openspec/changes/demo/workflow-events.jsonl:2 不是合法 JSON：…
```

⇒ 修完只是让**解码失败走同一条现成的路**。`checkcmd.py:167` 的 `except events_mod.EventError` 一行都不用动。

### 1.5 改动面很小（实测）

全树 `EventError` 只有 **3 个生产位置**：`events.py:24`（定义）、`:58`/`:60`（抛）、`checkcmd.py:167`（捕）；
`guardcmd.py` **完全不 import** `events` ⇒ 「events 是 `check`-only、无 `guard` 路径」这一 scoping 属实。

## 2. 决策

### D1 归一到 `EventError`（与「不是合法 JSON」同类型 → 同出路）

- `events.py` 里「这片内容不能当 events 用」**已经**用 `EventError` 表达（`:57-60`）。读不出是**同一类**。
- **两条路都红，但报的原因不同**（grill 修正了原稿的理由）：
  - 现方案（`EventError`）：报**真原因**（文件读不出来）；
  - 备选「静默跳过坏文件」：`known` 变小 ⇒ 依赖该文件的受保护写入被报成「**没有**解释事件」⇒ **假红**，
    报的是**错原因**。
  ⇒ 原稿写的「结论仍然错，只是错得更隐蔽」**方向对、程度说反了**：它不是**更松**（不是放行），而是**更乱的假红**。已改。

### D2 `check` 侧**不改**（出路已现成，D1 之后自动生效）

见 §1.4 的实测。**少改一处就少一处漂移面**——这是本 change 明确的价值取向。

### D3 **不做抽象层**；且要**沿用本仓既有的 idiom**

- 全树 `read_text` 实测 **13 处**、出路**实测 6 种**（`EventError` / `ValueError` / `PolicyError` / 静默 `None` /
  `Finding` / `print+EXIT_FAIL`）⇒ 一个「统一 helper」要么带错误类型参数（省不了什么），要么把语义拍平。
- ⚠️ **grill 补了更省的切法**：本仓**已有成文 idiom** —— `except (OSError, ValueError)`
  （`policy.py:134`、`contract.py:177/232`、`evidence.py:166`；`policy.py:134-136` 还注释了
  「`ValueError` 涵盖 `JSONDecodeError` **与** `UnicodeDecodeError`」）。
  ⇒ 若 Q1 一并修，**沿用这个 idiom**（一处补一个词），**不要**写成 `except (OSError, UnicodeDecodeError, json.JSONDecodeError)`
  ——那与既有 4 处**分叉**，正是 D3 想避免的漂移面。

### D4 文案：**同一对词** + **文件级形态**

- 抄 `evidence.py:225-228` 的既有两分支：`why = "无法解码" if isinstance(exc, UnicodeDecodeError) else "无法读取"`
  ——**同一对词**（`无法解码` / `无法读取`），否则两处各写各的。
- **形态**：既有那条是**行级**（`f"{path}:{lineno} 不是合法 JSON：…"`，`events.py:58/60`）；
  新增应为**文件级、无 `:lineno`**（`f"{path} 无法解码：{exc}"` / `f"{path} 无法读取：{exc}"`）。
  两者形态本身就不同 ⇒ 混淆风险**低**（grill 实测复核）。

## 2.5 族边界（**本 change 的 scoping 定义** —— 原稿缺，grill 要求补）

- **族内（本 change 收口）**：**`read_text` 文本读点，落在 `check`/`init`/`uninit` 主路径** —— 精确清单依 **Q1** 裁定。
- **族外（写进「非目标」+ 理由，免得下次再问「为什么这里崩那里不崩」）**：
  - `read_bytes` 两处：`initcmd.py:215`、`uninitcmd.py:59`（`sha256_bytes(path.read_bytes())`）——
    **不同族**：无解码语义；且 `OSError` 的 message **自带文件名** ⇒ 今天的「内部错误」**已可定位**。
  - 间接：`hashing.py:19/31/35`（`sha256_file`/`sha256_tree`）。
    ⚠️ 但要知道 **`contract.py:373/386`**（`sha256_tree`）在 **`check` 主路径**上、且**早于**
    `evidence.py:224` 的正文守卫 ⇒ **「报告文件存在但不可读」仍会退成一行「内部错误」**——
    **已知未覆盖**（R-G5），写进非目标。

## 3. 接线点（实现清单）

- `src/witnessloop/events.py`：`load_events_file` 的读点包 try ⇒ 抛 `EventError`（D1/D4）。
- **（依 Q1）** `initcmd.py:118/216`、`uninitcmd.py:77`：**新包 try**；
  `initcmd.py:63/131/201`、`uninitcmd.py:30`：**补 except 元组**（用 D3 的 idiom）。
  ⚠️ **`initcmd.py:201` 是「补元组」不是「无 try」**——原稿与 tasks B1 分类错（它 `:200-204` 有 try，只是
  `except json.JSONDecodeError`，**同时**漏 `OSError` 与 `UnicodeDecodeError`）。grill 实测纠正。
- `tests/`：`events.py` 单测 + `check` 端到端（**可判定形态见 §5**）。
- 文档：**只改 `docs/gate.md`**（§4 + §8）——见 R-G2。

## 4. 风险

1. **R1（高·文档失真 · R-G1）**：若照原稿措辞把「此前**崩溃**（`check` ⇒ **traceback**）」写进 `README`/`docs/gate.md`，
   就是把**假历史**写进接入方文档。⚠️ **`docs/gate.md §8` 里已经有一句同样错的**（「`check` ⇒ traceback」，
   来自 change `guard-crash-exit`）——本 change **一并订正**为实测形态（一行「内部错误」、退 1、不点名文件）。
2. **R2（高·自伤 · R-G2）**：PR 里出现**任何**别的 `openspec/changes/<other>/**` 编辑 ⇒ 那个 change 被算进
   `changed_change_ids`，而本次 diff 落了 `src/**` ⇒ 它也被要求 `stage=building` manifest ⇒ **必红**（grill 实测）。
   ⚠️ 原稿/tasks 指向的「非目标那一行」恰住在 `openspec/changes/guard-crash-exit/design.md:27`（**另一个 change 的文档**）
   ⇒ **收口时只改 `docs/gate.md`**，绝不编辑别的 change 目录。
3. **R3（中·验收断言不可判定 · Q3）**：原稿的`「不抛异常 / 非 0 / 不含 Traceback」**今天就已经全绿**（grill 实测）
   ⇒ 钉不住任何东西。**已按 Q3 改写 §5**。
4. **R4（中·短路 · Q2）**：一个坏 events 文件 ⇒ `_protected_writes` **整块 return** ⇒ **所有**受保护写入不再被评估。
   **接受**（理由见 §8 Q2：逐文件隔离与 D2 冲突），但**写明**：仍然**红**（不是绿），且**与 diff 无关**（§1.2）。
5. **R5（中·覆盖范围 · R-G3）**：`archive/**` 的 events 文件不参与（§1.3）⇒ 文档别写成「所有 events 文件」。
6. **R6（中·假绿测试 · R-G4）**：用 `chmod 000` 造「读不到」，在 **root** 下 `open()` 会**成功** ⇒ 用例**假绿**。
   ⇒ 主用例改用**目录冒充 events 文件**（实测同样触发 `IsADirectoryError`，与 uid 无关）。
7. **R7（低·族边界漂移 · R-G5）**：`sha256_tree` 那条（§2.5）——已写进非目标。
8. **R8（低·诊断面形态 · Q4）**：events 那条 finding 的 `path` 是 `"."`、message 里是**绝对路径**，
   与 `check` 其余 finding 的**仓根相对**口径不一致（既有行为，非本 change 引入）。
   **本 change 不改**（保持与既有 JSON 坏那条逐字一致 ⇒ 不动 `checkcmd`，符合 D2），在此**记一笔接受**。

## 5. 测试策略（TDD）

- **先红（真能红）**：
  - `load_events_file`（非法 UTF-8）⇒ 抛 `EventError`（当前抛 `UnicodeDecodeError`）；
  - `load_events_file`（**目录冒充**文件）⇒ 抛 `EventError` 且文案是「**无法读取**」（R6）；
  - `check` 端到端：stderr **含**「事件文件无法解析」**且不含 `witnessloop：内部错误`**（今天**红**、修后**绿** —— Q3）；
  - 合法 events 的既有行为不变（回归）。
- ⚠️ **不写「不含 Traceback / 不抛异常 / 非 0」当红先断言**——它们**今天就已经成立**（Q3/R3）。
  退出码不变这条**保留为回归护栏**（在 spec 里明标，不宣称是红先）。

## 6. 文档影响

- `docs/gate.md §4`（结构化解释事件）：补「读不出 ⇒ 一行点名文件的 finding（**不是** `内部错误`）」+
  「坏 events ⇒ 受保护写入**整块**不再评估（仍然**红**；且与 diff 无关）」。
- `docs/gate.md §8`：**新增一行** events ✅（该表**只有 3 行**，**没有** events 行——原稿/tasks 说「改一行」是错的），
  写明覆盖范围 = **active change 目录**（R5）。
- ⚠️ **同一节里那句既有错话**（「`check` ⇒ traceback」）**一并订正**（R1）。
- `README.md`：写明**对**接入方是**报错形态变更**（「内部错误」→ 一行点名文件的 finding；**退出码不变、不是新的红**）。

## 7. Pre-Implementation Review

**已确认决策（grill 逐条实测 · 来源 `grill-reviewer-events-readpoint-fix-2026-10-12`）**：
D1 归一为 `EventError` 成立（**且比原稿论证更强**：唯一调用点 `events.py:76`、唯一消费者 `checkcmd.py:167`）；
D2 出路已现成（用**未打补丁**的代码实测出目标形态）；D3 不做抽象层成立（13 处读点 / 6 种出路），
**并补了「沿用既有 idiom `except (OSError, ValueError)`」**；D4 有先例可抄（`evidence.py:225-228`），混淆风险低（实测）。

**被 grill 证伪并已改写**：
- **中心前提**：今天**没有** traceback（是 `entry.py` 兜住的一行「内部错误」）⇒ §0/§1.1 重写；
  真缺陷 = **把仓的问题报成工具故障** + **解码分支不点名文件**。
- **读点分类**：`initcmd.py:201` **有** try（是「补元组」不是「无 try」）；**漏** `read_bytes` 两处
  （`initcmd.py:215`/`uninitcmd.py:59`）与 `sha256_tree`（`contract.py:373/386`）⇒ 已定义**族边界**（§2.5）。
- **`tasks.md` D1 动作错**：`docs/gate.md §8` 的表**只有 3 行、无 events 行** ⇒ 应是**新增一行**，且**只改 `docs/gate.md`**
  （原稿指向的「非目标」字样住在**另一个 change 的文档**里，碰它会触发 R-G2 自伤）。
- **Q2 的理由错**：逐文件隔离**不是**「混进」（它会**同时**报两件事，信息更多）；正确否掉它的理由是**与 D2 冲突**。
- **R4 低估影响面**：短路**与 diff 无关**（空 diff 也走这条路）。
- **验收断言不可判定**（Q3）⇒ §5 已改成**今天红、修后绿**的形态。

## 8. Open Questions（停轮待用户确认）

- **Q1〔范围〕**：只修 `events.py`，还是一并修同族读点（修到哪为止）？
  ⚠️ 原稿的理由「它们的严重度**低一档**」**不成立**——events 那条**同样**是「退 1 = 方向本就正确」；
  四处的实际差别只是「谁在跟前」（`check` = CI 里给人看 vs `init`/`uninit` = 本地一次性命令）。
  **推荐：一并修**，范围钉成「`read_text` 文本读点、落在 check/init/uninit 主路径」：
  `events.py:51`（新 try）+ `initcmd.py:118/216`、`uninitcmd.py:77`（新 try）+
  `initcmd.py:63/131/201`、`uninitcmd.py:30`（**补 `except (OSError, ValueError)`**）；
  `read_bytes` 两处与 `sha256_tree` 写进**非目标**并注明理由。
- **Q2〔短路 / R4〕**：坏 events 让受保护写入**整块**不再被评估——接受 + 写明，还是逐文件隔离？
  **推荐：接受**（不逐文件隔离），理由换成「**逐文件隔离与 D2 冲突**（要改 `load_all` 契约或让 `checkcmd` 逐文件 catch）
  + 两条路都红 + 现状更差」，并在 `docs/gate.md §4` 写明「仍然**红**，不是绿」。
- **Q3〔验收断言〕**：原稿的两处断言今天已绿 ⇒ **推荐**把「不含 `Traceback`」换成
  「**不含 `witnessloop：内部错误`**」（今天红、修后绿）；`spec` 的绝对句改成
  「SHALL 得一行点名文件的 finding，SHALL **不**表现为 `witnessloop：内部错误`」；
  退出码那条**明标为回归护栏**（或删）。`spec` 的「stderr **是**」收成「**含**」。
- **Q4〔诊断面形态〕**：events 那条 finding 是 `path="."` + 消息里**绝对路径**，与其余 finding 的仓根相对口径不一致
  （既有行为）。**推荐：本 change 不改**（保持与 JSON 坏那条一致 ⇒ 不动 `checkcmd`），仅在 §4 R8 记一笔。
