# Grill 对抗验证: events-readpoint-fix

> **结论一句话**：**支点站得住**——我独立复核了 grill 的中心结论（今天 `check` **不吐 traceback**，
> 是 `entry.py` 兜住的一行 `witnessloop：内部错误（…）`、退 1），**grill 没翻错，design 不用再翻第三次**。
> 但 grill **自己**留下两处错，且其中一处是它**声称「实测」而实际为假**的观测；
> 另有 3 处「实现细节未定 / 测试配方会让实现卡住」的洞。故 **CHANGES_REQUESTED**（改动很小、都是外科手术）。

## Reviewer

- run id: `grill-adversarial-reviewer-events-readpoint-fix-2026-10-12`
  （`WITNESSLOOP_RUN_ID` 在本环境**未设**，故按 `templates/grill.md`「怎么取 run id」第 2 条走**确定性兜底**
  形态 `<stage>-<role>-<anchor>`；与 `grill-reviewer-events-readpoint-fix-2026-10-12` **结构上必然不同**。）
- 时间: **2026-10-12T08:47:12Z**
- 零记忆审阅者：不读作者/grill 的会话历史，只读 change 目录文本 + 只读仓库内容。
- 基线实测：`uv run pytest -q` ⇒ **413 passed**（与本 worktree 声明一致）。
- **所有实测在 `/tmp` 下的真 git 仓上跑**；本 worktree 只在「验证补丁是否真能转绿」时**临时打过补丁**，
  跑完已 `git checkout --` **全量还原**、`git status --porcelain` **为空**、**未 commit**（见末节第 12 条）。
- 一律用 `uv run witnessloop …`（PATH 上的裸 `witnessloop` 是另一份 uv-tool 安装）。

## Verdict

**CHANGES_REQUESTED**

**不阻塞的部分先说清楚**（免得读成「design 要重做」）：

- **中心前提（支点）成立**：grill 的翻转是对的，**design 不需要再翻第三次**。
- **D1 / D2 / D3 / D4 逐条复核后全部站得住**，且 D2「出路已现成」有更强证据（我用**未打补丁**的代码跑出了目标形态）。
- **新 spec 断言真的可判定**：未修 = 红、修后 = 绿，我两端都实测了。
- **读点族的边界（§2.5）实质完整**——但**分类**有两处错（见下）。

**阻塞的只有「会让实现卡住 / 让用户拿到假证据」的那几条**：`grill-review.md` 的 Q1 里有一条**自称实测、
实为假**的观测（会被直接端给用户拍板）；`proposal.md` 的读点表把两个**已经捕 `OSError`** 的点写成「漏 `OSError`」；
`tasks.md` 的 B3 若照本 change 自己推荐的「目录冒充」配方写用例**在声明的范围内永远红**。

## 逐条对抗结论

### 1. 支点：「今天 `check` 是 traceback 还是一行『内部错误』？」→ **grill 对，站得住（我独立复核）**

真 git 仓（`init` 接入 + `openspec/changes/demo/` + 含 `0xff` 的 `workflow-events.jsonl`）：

```
$ uv run witnessloop check --root /tmp/adv/repo --base base
（stdout 为空）
stderr: witnessloop：内部错误（UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 170: invalid start byte）
EXIT=1        grep -c Traceback ⇒ 0
```

⇒ **没有 Traceback**。design §1.1 的改写（`entry.py:35-41` 兜底 ⇒ 一行、退 1、不点名文件）**属实**。
两条附带结论也复核通过：

- **① 空 diff 同样走这条路**：`--base base --head base`（0 变更文件）⇒ **同样的那一行、EXIT=1**，
  且 stderr 里**连 `check：基线 …` 都没有** ⇒ `_report`（`checkcmd.py:102`）**一次都没跑到**。design §1.2 属实。
- **② `archive/` 下的坏文件不参与**：把坏 events 文件只放在 `openspec/changes/archive/old/` ⇒ `check` **通过（EXIT=0）**，
  实测 `root.glob("openspec/changes/*/workflow-events.jsonl")` **hits = []**。design §1.3 / R5 属实。
- **③ 「没有任何产品路径会吐 traceback」——我没能证伪，但有一条边界**：
  坏 events / 坏 policy / 坏 manifest / 坏报告 / 目录冒充 / mode-000 / `init` / `uninit` / 各 verb 组合，
  我一律只拿到**一行**「内部错误」或**一行**干净诊断，**没有一次 traceback**。
  连「stderr/stdout 编码不是 UTF-8」这条也没吐 traceback（`PYTHONIOENCODING=ascii` 与 `PYTHONUTF8=0 LC_ALL=C` 下
  仍是**一行** `witnessloop：内部错误（UnicodeEncodeError: …）`、退 1）。
  **唯一例外**：`cli_main` 里冒出的 **`KeyboardInterrupt`**（Ctrl-C）会**穿过** `entry.main`
  （它只捕 `Exception`）⇒ 真 traceback、退 130。见「新发现的风险」第 2 条——**这不推翻支点**（支点讲的是
  「坏文件 ⇒ 崩溃形态」，而 Ctrl-C 不是坏文件），但「没有任何产品路径」这句话作为**绝对句**是过宽的。

### 2. 「真正的缺陷 = 报成工具故障 + 解码分支不点名文件」→ **站得住**

实测对照（同一份坏 events 文件、只换成因）：

| 触发方式 | 今天 stderr 里有没有路径 |
|---|---|
| 非法 UTF-8（`0xff`） | **没有**（`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff …`） |
| `chmod 000`（uid 10001） | **有**（`PermissionError: [Errno 13] Permission denied: '<abs>'`） |
| 目录冒充 | **有**（`IsADirectoryError: [Errno 21] Is a directory: '<abs>'`） |

⇒ 「解码分支不点名文件」这条**实测成立**（不是修辞）。「把仓的问题报成工具故障」也成立
（`check` 退 1 = 未通过 ⇒ **fail-closed 方向本就正确**，确实只是可用性/可诊断性缺陷）。design §1.1 的两条**都对**。

### 3. D2「`check` 侧不改」→ **站得住，且比我预期的更强**

**未打补丁**、只用**合法 UTF-8 + 坏 JSON** 的 events 文件：

```
7. .：事件文件无法解析：/tmp/adv/rjson/openspec/changes/demo/workflow-events.jsonl:2 不是合法 JSON：Expecting value: line 1 column 1 (char 0)
```

⇒ 目标形态**今天就已经现成**，`checkcmd.py:167` 一行都不用动。design §1.4 属实。

### 4. D1／D3／D4 → **站得住**（D3 的两条措辞要收一收，见「必须修改」）

- **D1**：`EventError` 全树**只有 3 个生产位置**（`events.py:24` 定义、`:58`/`:60` 抛、`checkcmd.py:167` 捕），
  `load_events_file` 唯一调用点是 `events.py:76`，`guardcmd.py` **确实**不 import `events` ⇒ 「单点修好即全覆盖」属实。
  「静默跳过 ⇒ 假红」这条我**用机制验了**：把解释事件整个拿掉（等价于 `known` 变小），
  `check` 报 `openspec/specs/foo/spec.md：受保护路径被写入，但没有结构化解释事件`（退 1）
  ⇒ 确实是**假红**（fail-closed 的错原因），不是放行。D1 的改写方向对。
- **D4**：`evidence.py:225-228` 的两分支先例属实，措辞对是 `无法解码` / `无法读取`。
  形态可区分也成立：既有条是**行级**（`events.py:58/60` 的 `f"{path}:{lineno} …"`），新增条是**文件级**。
- **D3**：`read_text` 全树**实测 13 处**（与我 grep 完全一致）。
  ⚠️ 但「本仓**已有成文 idiom** `except (OSError, ValueError)`」这句**把仓库说齐整了**——实际是**三种并存**：
  `(OSError, ValueError)` **4 处**（`policy.py:134`、`contract.py:177/232`、`evidence.py:166`，**另有 `paths.py:69` 是同一 idiom 的换序写法** `(ValueError, OSError)`）、
  `(OSError, json.JSONDecodeError)` **2 处**（`initcmd.py:64/132`）、`(OSError, UnicodeDecodeError)` **1 处**（`evidence.py:225`）。
  **推荐本身仍然对**（`policy.py:135-136` 确实注释了「`ValueError` 涵盖 `JSONDecodeError` **与** `UnicodeDecodeError`」，
  选它是选**多数派 + 有注释的那个**），只是理由要说成「选多数派」而不是「选唯一既有写法」。

### 5. 读点清单：**族边界实质完整，但分类有两处错**（grill 只纠出 `:201`，**漏了 `:63`/`:131`**）

全树 grep（`read_text` 13 + `read_bytes` 4）逐点核完：

| 读点 | 归到哪 | 实测/读码结论 |
|---|---|---|
| `events.py:51` | 无 try | ✅ 分类对（本 issue 本体） |
| `initcmd.py:118` | 无 try | ✅ 分类对（**但配方不完整，见「必须修改」第 4 条**） |
| `initcmd.py:216` | 无 try | ✅ 分类对 |
| `uninitcmd.py:77` | 无 try | ✅ 分类对 |
| `initcmd.py:201` | 有 try、`except json.JSONDecodeError` | ✅ 分类对（grill 纠对了） |
| `uninitcmd.py:30` | 有 try、`except json.JSONDecodeError` | ✅ 分类对 |
| **`initcmd.py:63`** | 表里写「有 try，但 `except json.JSONDecodeError`，**同时漏 `OSError` 与 `UnicodeDecodeError`**」 | ❌ **错**：`:64` 是 `except (OSError, json.JSONDecodeError) as exc` ⇒ **`OSError` 已捕**，只漏 `UnicodeDecodeError` |
| **`initcmd.py:131`** | 同上（表里同一行组） | ❌ **错**：`:132` 是 `except (OSError, json.JSONDecodeError)` ⇒ **`OSError` 已捕**，只漏 `UnicodeDecodeError` |
| `policy.py:133` / `contract.py:176` / `contract.py:231` / `evidence.py:165` / `evidence.py:224` | 已覆盖 | ✅ 复核通过 |
| `read_bytes` ×4（`hashing.py:19/35`、`initcmd.py:215`、`uninitcmd.py:59`） | 族外 | ✅ 已登记；`contract.py:373/386` 的 `sha256_tree` 在 `check` 主路径上、**早于** `evidence.py:224` 属实（见下） |

两份**独立的实测**，证明「漏 `OSError`」这条是错的、且 `:63` 根本不是缺陷：

```
# initcmd.py:131（ledger_gate_ref）——真缺陷（漏 UnicodeDecodeError）
$ uv run witnessloop init --root <含 0xff 的 .witnessloop/init-manifest.json 的仓>
witnessloop：内部错误（UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte）   EXIT=1

# initcmd.py:63（load_policy_override）——【不是缺陷】
$ uv run witnessloop init --root <干净仓> --policy <含 0xff 的 seed>
init：'utf-8' codec can't decode byte 0xff in position 0: invalid start byte      EXIT=1   ← 不是「内部错误」
```

`initcmd.py:63` 之所以不崩：漏捕的 `UnicodeDecodeError` **是 `ValueError` 的子类**，被 `run()` 的
`initcmd.py:146-150`（`try: load_policy_override(...)` / `except ValueError as exc`）**接住了**，
出去的是 `init：{exc}`。⇒ **`grill-review.md` 的 Q1「具体场景」里那句
「`init --policy <含 0xff 的 seed>` ⇒ 同样是「内部错误」（…实测路径见 `:62-65`）」是假观测**
（它甚至标了「实测」）。这一条会被原样端给用户拍板，**必须回写**。

另两处**grill 也没说准**的细节：

- **`:201` 在解码路径上被 `:131` 遮蔽**：`ledger_gate_ref`（`initcmd.py:156`）**先于** `_already_initialized`（`:160`）
  读同一个台账 ⇒ 台账是非法 UTF-8 时**先炸在 `:131`**。所以「只补 `:201` 的元组」**修不好解码那条**
  ——Q1 把 `:131` 与 `:201` 都列了 ✅（这点是运气好，不是分析对）。
- **`uninitcmd.py:30` 的「漏 `OSError`」用「目录冒充」够不着**：`uninitcmd.py:24` 的 `is_file()` 挡在前面，
  目录台账 ⇒ `uninit：未接入（或已回滚），无改动。`、**EXIT=0**（实测）。要触发它的 `OSError` 分支得用 **mode-000 文件**。

### 6. 新 spec 断言：**真的可判定（今天红、修后绿）** —— 逐字实测

我写了一条**独立**用例（自带造仓、直调 `witnessloop.entry.main`，不依赖本仓 `tests/conftest.py`）：

- **未打补丁** ⇒ **2 failed / 1 passed**：`事件文件无法解析` **不在** stderr；stderr 就是那一行
  `witnessloop：内部错误（UnicodeDecodeError: …）`；回归那条（合法 events 行为不变）**pass**。
- **打补丁（只改 `events.py`，用 `except (OSError, ValueError)` + D4 的两分支措辞）** ⇒ **3 passed**：

```
7. .：事件文件无法解析：<abs>/openspec/changes/demo/workflow-events.jsonl 无法解码：'utf-8' codec can't decode byte 0xff …
7. .：事件文件无法解析：<abs>/openspec/changes/demo/workflow-events.jsonl 无法读取：[Errno 21] Is a directory: '<abs>/…'
```

⇒ **「目录冒充触发 `IsADirectoryError`」实测成立**（不是别的异常），且修后走 `无法读取` 分支、与 `无法解码` 可区分。
⇒ 打补丁后 `uv run pytest -q` **仍 413 passed**（回归无伤）。spec.md 的 Scenario 1/2/3 **都可判定**。

**`chmod 000` 在 root 下假绿 —— 实测成立**（我不是 root，用 `unshare -r --map-root-user` 拿到了带 DAC_OVERRIDE 的 uid 0）：
同一个 `chmod 000` 的 events 文件，在 ns 内被**正常读出**、`check` 一路走到别的 finding、**没有 `PermissionError`**
⇒ 那条用例在 root 下确实**假绿**。R6 属实，且 R6 推荐的替代配方（目录冒充）**已实测可行**。

**spec Scenario 4（与 diff 无关）也可判定**：坏 events 在 base 上、`--base base --head base` ⇒ 仍然报
`1. .：事件文件无法解析：…`、EXIT=1（**未打补丁**时用坏 JSON 版本验的，机制同源）。

### 7. Q1「一并修」的**动作**能落地 —— 但**两条理由错了**、**一处配方不完整**

我把 Q1 推荐的范围**真的实现了一遍**（`events.py` + `initcmd.py:63/118/131/201/216` + `uninitcmd.py:30/77`）：

- `init` + 非法 UTF-8 的 `.witnessloop/policy.json`（`:118`）⇒ **变干净**：`init：.witnessloop/policy.json 无法解码：…`
- `init`（已接入）+ 非法 UTF-8 的台账（`:131`+`:201`）⇒ **变干净**
- 全量 `uv run pytest -q` ⇒ **413 passed**

⇒ 范围的**动作清单可行**。但三条问题：

1. **理由错**（见第 5 条）：`:63`/`:131` **不是**「漏 `OSError`」。
2. **`:63` 根本不坏**：它今天已经给出 `init：<decode error>`，不是「内部错误」。把它列进「一并修」最多算
   **文案改善**（改成 `--policy 文件无法解析为 JSON：…`），**不能**用「否则报内部错误」当理由。
3. **`:118` 的「新包 try」不是可实现的配方**：`conflicting_files`（`initcmd.py:108-121`）的返回值是
   `(rel, current, want)`，调用方 `initcmd.py:166-167` 直接 `render_diff(rel, current, want)` ⇒ `current.splitlines()`。
   我**故意**按最字面的「包一层 try、读不出给 `None`」实现了一次，结果**造出一个新的「内部错误」**：

```
init：检测到冲突（只增不改，拒绝覆盖已有文件）：
witnessloop：内部错误（AttributeError: 'NoneType' object has no attribute 'splitlines'）
```

⇒ design 必须**指定读失败时调用方怎么办**（报一条干净的红 / 退回「`! {rel} 内容读不出」），否则实现者会
**照字面实现出一个新的 `内部错误`**——正好是本 change 要消灭的形态。

### 8. Q2「接受短路」→ **站得住**（实测两面）

- **短路属实且后果如述**：打补丁后，坏 events 文件 + 一个**缺解释事件的受保护写入**同仓 ⇒
  `check：未通过 ✗（1 项）`，**只有** `1. .：事件文件无法解析：…`，那条「受保护路径被写入，但没有结构化解释事件」
  **被整块吞掉**（`checkcmd.py:167-168` 直接 `return`，`for change in changes`（`:171-205`）不执行）。
- **无绕过**：那条 finding 自己就让 `check` 退 1 ⇒ **坏 events 文件不可能让 check 变绿**。
- **现状更差**：未打补丁时 stdout **空空如也**（`_report` 在 `:102`，短路点在 `:100`）⇒ 其它 finding **一条都不打印**。
- **否掉「逐文件隔离」的正确理由确实是「与 D2 冲突」**：逐文件隔离要么改 `load_all` 的返回契约
  （如 `(events, errors)`），要么让 `checkcmd` 自己逐文件 catch ⇒ 两条都要动 `checkcmd`/契约，与 D2 直接冲突。
  （design Q2 原稿说的「会把『事件坏了』混进『没有解释事件』」确实是错的——逐文件隔离**同时报两件事**、
  信息更多。grill 的纠正是对的 ✅）
- ⇒ 推荐「接受 + 写明**仍然红、不是绿**、且**与 diff 无关**」**站得住**。

### 9. Q3「验收断言改写」→ **站得住**

原稿那三条（`不抛异常` / `非 0` / `不含 Traceback`）**今天就已经全绿**——我实测确认：
未修代码上 `grep -c Traceback` = **0**、`EXIT=1` ⇒ 它们**钉不住任何东西**（是假红先）。
换成「stderr **不含** `witnessloop：内部错误`」则**今天红（含）、修后绿（不含）**，我两端都跑到了
⇒ Q3 的改写方向与「措辞从『是』收成『含』」都对（实测 stderr 里还有 `check：未通过 ✗（N 项）` 表头与其它 finding）。

### 10. Q4「本 change 不改诊断面形态」→ **站得住，且不会留下模糊 spec**

- 现象属实：events 那条 finding 是 `path="."` + message 里**绝对路径**（实测 `7. .：事件文件无法解析：/tmp/…`），
  与 `check` 其余 finding 的**仓根相对**口径不一致（`contract.py` 的 `Finding` docstring 明说相对）。
- **spec 不因此变模糊**：`spec.md:11` 已经把要求钉在**错误信息**上（文件级、不带 `:lineno`、`无法解码`/`无法读取`），
  修后产出的正是 `<abs path> 无法解码：…` ⇒ **可判定**。`path="."` 从来不在 spec 的射程里，
  「本 change 不改它」= **不在 spec 里许下任何关于它的承诺**，不构成模糊要求。
- 唯一要留意的是 `spec.md:12` 用「**与 `evidence.py` 相同的措辞**」做了**跨模块引用**——若哪天
  `evidence.py:225-228` 改了词，spec 这句会 stale。因为同一句里**也写了字面词**（`无法解码`/`无法读取`），
  判定不受影响，属可接受。

### 11. R2（自伤）→ **结论站得住，但 design 说的机制不准**

- **机制（building 门禁）属实**：stub 仓里「编辑另一个 change 目录 + 本次 diff 落 `src/**`」⇒
  `7. openspec/changes/old-change：无 stage=building 的 manifest（…）` ⇒ **红**（`checkcmd.py:91-98`）。
- **但在真仓里，红是另一条规则给的**：我在**真仓的 clone** 上复现了 R2 想防的动作
  （改 `openspec/changes/guard-crash-exit/design.md` + 落 `src/**`）⇒ 红，但 3 条全是
  `…/building.manifest.json：head_sha=… 不是本次被检 revision … 的祖先——审阅的是别的 revision`
  ⇒ 是**stale / revision 绑定**那条（`guard-crash-exit` **已经有** building manifest，所以 building 门禁不响）。
- 补充：**不落 `src/**` 也照样红**（只改另一个 change 目录 ⇒ 它进 `changed_change_ids` 就会被全套校）。
- ⇒ **行动指引「只改 `docs/gate.md`、绝不编辑别的 change 目录」是对的**（`guard-crash-exit/design.md:27`
  确实住着「本 change 非目标」那句，我核过），只是**别把机制只写成 building 门禁**。

### 12. R6 / §1.5 / R-G5 / tasks D1 的复核 → **全部属实**

- **R6**：见第 6 条（root 假绿 + 目录冒充可用）⇒ 属实。
- **§1.5**：`EventError` 生产位置 = 3 ✅（同第 4 条）；`guardcmd.py` 不 import `events` ✅。
- **R-G5**：端到端复现了——把一个**已 commit** 的报告 `chmod 000` 后跑 `check`：
  `witnessloop：内部错误（PermissionError: [Errno 13] Permission denied: '<abs>/…/grill-review.md'）`
  ⇒ `contract.py:373` 的 `sha256_tree`（`read_bytes`）**确实在** `evidence.py:224` 的正文守卫**之前**、且**未捕**。
  （`manifestcmd.py:100/101` 共用同一个 `sha256_tree`，同族。）⇒ 写进「非目标」是对的。
- **tasks D1**：`docs/gate.md §8` 的读点表**确实只有 3 行**（`:338-340` 的 policy.json / review manifest / grill 报告正文），
  **没有 events 行** ⇒ 正确动作是**新增一行**；`docs/gate.md:342` 确实留着那句**错的**
  「损坏的证据文件此前会**崩溃**（…；`check` ⇒ **traceback**）」⇒ R1/D1b 要订正的对象**确实存在**。

## 必须修改

1. **【阻塞·假证据】** `reviews/grill-review.md` 的 **Q1「具体场景」**里删掉/改写
   「`init --policy <含 0xff 的 seed>` ⇒ 同样是「内部错误」（…实测路径见 `:62-65`）」。
   实测输出是 `init：'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`（退 1），
   **不是**「内部错误」——漏捕的 `UnicodeDecodeError` 被 `initcmd.py:148` 的 `except ValueError` 接住了。
   `templates/grill.md` 第 5 步要求**停轮之前**把被证伪的结论回写。
2. **【阻塞·分类错】** 把 `proposal.md:45`（表里 `initcmd.py:63`、`:131` 那格）与
   `design.md:111` / `tasks.md:20-22`（B1）里的「**同时漏 `OSError` 与 `UnicodeDecodeError`**」
   改成「**只漏 `UnicodeDecodeError`**（`initcmd.py:64`/`:132` 已是 `except (OSError, json.JSONDecodeError)`）」，
   并把 `initcmd.py:63` 的动作从「补元组（否则报内部错误）」降级为「**文案改善（可选）**」——
   它今天已经是 `init：<decode error>`、退 1，**不是**本 issue 的缺陷形态。
3. **【阻塞·会让实现卡住】** 钉住 `tasks.md` **B3** 的用例配方：`init`/`uninit` 的「读不出」**必须用「非法 UTF-8」造，
   ⚠️ 不能用 R6 推荐的「目录冒充」**。原因（实测）：在这两条路径上，「目录」触发的**第一个**失败点是
   **族外**的 `initcmd.py:215` / `uninitcmd.py:59`（`read_bytes`）⇒
   - `init`（已接入）+ `policy.json` 是目录 ⇒ 仍是 `witnessloop：内部错误（IsADirectoryError: …）`；
   - `uninit` + 台账里某个文件是目录 ⇒ 仍是 `witnessloop：内部错误（IsADirectoryError: …）`；
   而换成非法 UTF-8 后两条都**变干净**。照「目录」写 ⇒ 用例在**声明的范围内永远红**，实现者会以为补丁错了。
   （顺带：`uninit` + 台账**自身**是目录根本到不了 `:30`——`uninitcmd.py:24` 的 `is_file()` 直接给
   `uninit：未接入（或已回滚），无改动。`、EXIT=0。）
4. **【阻塞·细节未定】** `design.md` §3 对 `initcmd.py:118` 只写了「**新包 try**」——这**不可实现**：
   `conflicting_files` 的返回值喂给 `render_diff`（内部 `current.splitlines()`）。必须写明读失败时调用方怎么报
   （例如「读不出 ⇒ 走 `无法解码`/`无法读取` 那对词、报一条红并退 1，**不进 diff**」）。
   我按最字面的「读不出给 `None`」试了一次，产出的正是 **`witnessloop：内部错误（AttributeError: 'NoneType' object has no attribute 'splitlines'）`**
   ——**本 change 要消灭的形态**。或者干脆把 `:118` 也移进非目标并说明理由。
5. **【非阻塞但请一并】** `tasks.md` B4 要求把 `read_bytes` 两处与 `sha256_tree` 写进
   `design.md` 的**「非目标」**——但 `design.md` **没有 `## 非目标` 段**（提案有、design 没有），
   这些内容目前只散在 §2.5「族外」与 §4 R7。要么补一个 `## 非目标` 段，要么把 B4 的指向改成 §2.5/R7。
6. **【非阻塞但请一并】** 收一收 D3 的措辞：「本仓**已有成文 idiom**」→ 改成
   「本仓**三种 `except` 并存**，选**多数派且带注释**的那个 `(OSError, ValueError)`」。顺带把
   `paths.py:69`（同 idiom 换序）与 `evidence.py:225` 计入分母。**推荐不变**。

## 新发现的风险

1. **（中·新的「半成品 init」）** `.witnessloop/init-manifest.json` 是**目录**时，`init` 会**先写完**
   `.witnessloop/policy.json` 与 `.github/workflows/witnessloop.yml`，**再**在
   `initcmd.py:181` 的 `manifest_path.write_text(...)` 上炸 `IsADirectoryError` ⇒ 一行「内部错误」、退 1，
   **仓里留下半套接入物（无台账）**。实测：`policy.json exists: YES` / `workflow YES`，`EXIT=1`。
   这是**写点**（不是 `read_text`）⇒ 落在 §2.5 族边界**之外**、也没进非目标登记。它比「诊断面难看」严重
   （**状态被改了一半**，而且没有台账可回滚）。**建议**：至少写进非目标/风险，别让下一个 issue 又从零发现它。
2. **（低·绝对句过宽）** 「**没有任何产品路径会吐 traceback**」对**非交互**调用成立（我穷举了坏文件的各种成因与 verb 组合），
   但对 **`KeyboardInterrupt`** 不成立：`entry.py:35` 只捕 `Exception`，`cli_main` 里的 Ctrl-C 会穿出去
   ⇒ **真 traceback、退 130**（实测，栈里看得见 `entry.py:34` → `cli.py:158`）。
   同理 `entry.py:16` 的注释「`KeyboardInterrupt` 以信号结束（shell 见 130 ≠ 1）」——退出码那句对，
   但**没提 traceback**。这不影响本 change（支点讲的是坏文件），**建议 design 把绝对句收成
   「任何**非交互**调用路径」**，免得日后被这句话反噬。
3. **（低·跨模块耦合）** `spec.md:12` 把措辞绑到 `evidence.py`（「与 `evidence.py` 相同的措辞」）。
   `evidence.py:225-228` 一改词，这句就 stale（判定不受影响，因为同句也给了字面词）。
   若想彻底解耦，就**只留字面词**。
4. **（低·清单完整性）** 「已覆盖（无需动）」清单漏了 `paths.py:69`；`read_bytes` 的「两处」与
   `hashing.py:19/35` 是分开写的（合计 4 处），读者容易少算。措辞收一下即可。
5. **（流程·非缺陷）** 本报告落盘后，`reviews/` 里 `grill-adversarial.md` **尚无对应 manifest**
   ⇒ 按 `docs/gate.md §3` 是**孤儿报告**，`reviews/` 是 `required_artifacts` 之一，此刻跑 `check` 会红。
   这是流程中间态（下一步 `manifest build --stage grill-adversarial` 才绑），**不是** change 的缺陷。
   另：实测 `grill-review.md` 的正文判定目前**只差 Q1–Q4 的 `## User Confirmation`**（其余全过）
   ⇒ E0 停轮拿到答复后即可放行，路径是通的。

## 我实测复现的

> 全部在 `/tmp/adv/**` 的真 git 仓上跑；一律 `uv run witnessloop …`（从本 worktree）。
> 验证补丁时临时改过 `src/witnessloop/{events,initcmd,uninitcmd}.py`，跑完**已全量还原**：
> `git status --porcelain` 输出为空，`diff` 三个文件与原始**逐字节一致**，**未 commit**。

1. **【支点·必答】真仓 + 含 `0xff` 的 `workflow-events.jsonl`**
   `uv run witnessloop check --root /tmp/adv/repo --base base`
   ⇒ stdout 空；stderr = `witnessloop：内部错误（UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 170: invalid start byte）`；
   **`EXIT=1`；`grep -c Traceback` = 0** ⇒ **不是 traceback**（grill 的翻转成立）。
2. **① 空 diff 走同一条路**：`check --root /tmp/adv/repo --base base --head base`
   ⇒ **同一行**、`EXIT=1`，且 stdout **连 `check：基线 …` 都没有**（`_report` 没跑）。
3. **② `archive/` 坏文件不参与**：坏文件只在 `openspec/changes/archive/old/` ⇒ `check：通过 ✓`、**`EXIT=0`**；
   `glob("openspec/changes/*/workflow-events.jsonl")` ⇒ **`[]`**。
4. **③ traceback 穷举**：坏 events（UTF-8 坏/目录/mode-000）、坏 policy、坏台账、坏报告、`init`/`uninit`/`check`/`manifest build`/`guard`
   与 `--policy`/`--base`/`--head` 组合 ⇒ **一次 traceback 都没有**；
   `PYTHONIOENCODING=ascii uv run witnessloop check …` 与 `PYTHONUTF8=0 LC_ALL=C …` ⇒ 仍是**一行**内部错误、`EXIT=1`。
   **唯一反例**：在 `cli_main` 内抛 `KeyboardInterrupt` ⇒ 真 traceback、`EXIT=130`（`entry.py:34` → `cli.py:158`）。
5. **D2「出路已现成」**：未打补丁 + 合法 UTF-8/坏 JSON ⇒
   `7. .：事件文件无法解析：<abs>/…/workflow-events.jsonl:2 不是合法 JSON：Expecting value: line 1 column 1 (char 0)`。
6. **断言可判定性（两态）**：自写独立用例（造仓 + 直调 `entry.main`）
   - 未打补丁 ⇒ **2 failed / 1 passed**（`事件文件无法解析` 不在 stderr；stderr 就是那一行内部错误；回归那条 pass）
   - 打补丁（`events.py` 用 `except (OSError, ValueError)` + `无法解码`/`无法读取`）⇒ **3 passed**，且
     `uv run pytest -q` ⇒ **413 passed**。
   实测修后两条形态：`…workflow-events.jsonl 无法解码：'utf-8' codec …` / `…workflow-events.jsonl 无法读取：[Errno 21] Is a directory: '…'`。
7. **目录冒充确实触发 `IsADirectoryError`**：`check` 对 `mkdir` 出来的 `workflow-events.jsonl`
   ⇒ 未修：`witnessloop：内部错误（IsADirectoryError: [Errno 21] Is a directory: '<abs>'）`；修后：`无法读取` 分支。
8. **`chmod 000` 在 root 下假绿**：`unshare -r --map-root-user`（ns 内 `uid=0`，带 DAC_OVERRIDE）
   ⇒ 同一个 mode-000 events 文件被**正常读出**、`check` 走到别处、**无 `PermissionError`** ⇒ 假绿成立。
   （非 root，uid 10001 时同文件确实报 `PermissionError: [Errno 13] …`。）
9. **R6 变量之外：`uninit` + 台账自身是目录** ⇒ `uninit：未接入（或已回滚），无改动。`、**`EXIT=0`**（`is_file()` 挡住）。
10. **Q1 范围真的实现了一遍**（`events.py` + `initcmd.py:63/118/131/201/216` + `uninitcmd.py:30/77`）：
    `init` + 非法 UTF-8 的 `policy.json`（`:118`）⇒ `init：.witnessloop/policy.json 无法解码：…`；
    已接入 + 非法 UTF-8 台账（`:131`+`:201`）⇒ `init：.witnessloop/init-manifest.json 无法解析：…`；
    全量 `pytest -q` ⇒ **413 passed**。
    同补丁下 **族外**两点**照旧崩**：`init` + `policy.json` 是目录（`:215`）⇒ 内部错误；
    `uninit` + 台账里文件是目录（`:59`）⇒ 内部错误。
11. **「读不出给 `None`」的后果**（证明 `:118` 配方不完整）：
    `init：检测到冲突（只增不改，拒绝覆盖已有文件）：` 后跟
    `witnessloop：内部错误（AttributeError: 'NoneType' object has no attribute 'splitlines'）`。
12. **Q2 短路**：打补丁 + 坏 events 与「缺解释事件的受保护写入」同仓 ⇒
    `check：未通过 ✗（1 项）`、**只有** `1. .：事件文件无法解析：…`（那条受保护写入 finding **被吞**）、`EXIT=1`。
    对照：把解释事件整个拿掉（合法 events）⇒ `7. openspec/specs/foo/spec.md：受保护路径被写入，但没有结构化解释事件` ⇒ **假红**机制成立。
13. **R2**：stub 仓「改别的 change 目录 + 落 `src/**`」⇒ `7. …：无 stage=building 的 manifest（…）` 红；
    **真仓 clone** 上做同一动作（改 `guard-crash-exit/design.md` + 落 `src/**`）⇒ 红的 3 条全是
    `head_sha=… 不是本次被检 revision … 的祖先——审阅的是别的 revision`（**stale 那条**，不是 building 门禁）。
14. **R-G5 端到端**：已 commit 的报告 `chmod 000` ⇒
    `witnessloop：内部错误（PermissionError: [Errno 13] Permission denied: '<abs>/…/reviews/grill-review.md'）`
    ⇒ `contract.py:373` 的 `sha256_tree` 早于正文守卫且未捕。
15. **文档对象核对**：`docs/gate.md:338-340` 读点表**只有 3 行、无 events 行**；
    `docs/gate.md:342` 确有那句错的「`check` ⇒ traceback」；
    `openspec/changes/guard-crash-exit/design.md:27` 确有「本 change 非目标」字样（⇒ R2 的自伤面真实存在）。
16. **证据链就绪度**：`evidence.grill_evidence_findings(grill-review.md 正文)` ⇒ 只剩
    `Q1/Q2/Q3/Q4 未经用户确认` 4 条 ⇒ 其余（`Confirmed Decisions` ≥3、每条带 `来源:`）**已过**。
17. **基线**：`uv run pytest -q` ⇒ **413 passed**（打补丁后同）。

---

# 第 2 轮（R2）

> **结论一句话**：**6 项整合我逐条核完——5 项到位、1 项「做过头」**：`proposal.md:48` 与 `tasks.md:21-22`
> 把 R1 要求的那句「只漏 `UnicodeDecodeError`」**套到了 `initcmd.py:201` / `uninitcmd.py:30` 头上**——
> 而这两处的 `except` **只有 `json.JSONDecodeError`**（`initcmd.py:202` / `uninitcmd.py:31`），`OSError` **照样漏**
> （我实测到 `witnessloop：内部错误（PermissionError: …）`，栈分别钉在 `:201` / `:30`），
> 且与 **`design.md:122-124` 自己写的「`:201` 同时漏 `OSError` 与 `UnicodeDecodeError`」正面打架**。
> 故 **CHANGES_REQUESTED**——**唯一阻塞项就是这一处 3 行订正**（动作 `except (OSError, ValueError)` 本身不用改、范围不用重裁）；
> 其余（支点、§3.5、B3 配方、`:118` 定案、绝对句收窄、R2 机制）**全部 PASS**，且 `grill-review.md` 的假观测确已回写。

## Reviewer

- run id: `grill-adversarial-reviewer-events-readpoint-fix-2026-10-12-r2`
  （`WITNESSLOOP_RUN_ID` 本环境仍未设 ⇒ 同 R1 按 `templates/grill.md` 走确定性兜底形态 `<stage>-<role>-<anchor>`。）
- 时间: **2026-10-12T08:56:18Z**
- **零记忆（第 2 轮）**：不读作者 / grill / R1 的会话历史；R1 报告只作为**被核对象**读，不作为我的记忆。
- 基线实测：`uv run pytest -q` ⇒ **413 passed**（与 worktree 声明一致）。
- 本轮**未修改本 worktree 任何文件**（不跑补丁，只读 + 在 `/tmp/r2`–`/tmp/r5` 建仓跑 CLI）⇒ `git status --porcelain` 为空、**未 commit**。
- CLI 一律 `uv run witnessloop …`（PATH 上的裸 `witnessloop` 是另一份 uv-tool 安装）。

## Verdict

**CHANGES_REQUESTED**（1 条阻塞）

先说不阻塞的部分，免得读成「整合要重做」：**整合没有触碰任何 `src/**` / `tests/**`**
（`git show e324e5e --stat` 只含 `design.md`/`proposal.md`/`tasks.md`/`spec.md`/`reviews/*`）⇒ 「整合引入代码回归」这条路径不存在，
413 passed 与基线同源。支点、D1–D4、§3.5、B3 配方、`:118` 定案、绝对句、R2 机制**我逐条复核为真**（含末节 10 条独立实测）。

## 逐条核验（R1 的 6 项）

### 1.【假证据】`grill-review.md` Q1 的假观测 → ✅ **到位**（我独立复现了真观测）

`:77` 已用删除线划掉「`init --policy <含 0xff 的 seed>` ⇒ 同样是「内部错误」」，改写成「实测输出是 `init：'utf-8' codec can't decode byte 0xff …`（退 1）」，并带 `来源:`。
**我独立实测**（`/tmp/r2`，`--policy` 指向含 `0xff` 的 seed）：`init：'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`、`EXIT=1`
⇒ **不是**「内部错误」，与新回写的字面**逐字一致**；机制（漏捕的 `UnicodeDecodeError` 是 `ValueError` 子类，被 `initcmd.py:148` 的 `except ValueError` 接住）亦读码核实。**R1 阻塞①闭环。**

### 2.【分类错】`:63`/`:131` 的定性 → ⚠️ **半到位**（`:63` 对、`:131` 对，**但把 `:201`/`:30` 一起写坏了**）

- `proposal.md:49` 的 `:63` 格 ✅：`:64` 是 `except (OSError, json.JSONDecodeError)`、下游 `:148` 接住 ⇒ 「**不是**本 issue 的缺陷形态 ⇒ 降级为文案改善（可选）」——定性、理由、降级**三项都对**（读码 + 实测双复核）。
- `:131` 的「只漏 `UnicodeDecodeError`」✅（`:132` 确为 `except (OSError, json.JSONDecodeError)`）。
- ❌ 但新合并出来的那一行把 `:201` / `uninitcmd.py:30` **也算进了「只漏 `UnicodeDecodeError`」**——见阻塞项 **B1**。

### 3.【会让实现卡住】B3 / spec 的测试配方 → ✅ **到位，且它的理由我独立复核为真**

`tasks.md:28-31` 与 `spec.md` 新增的 ⚠️ 段都钉住：`init`/`uninit` 的「读不出」**必须用非法 UTF-8 造**，只有 `events` 那条用「目录冒充」。
**理由实测成立**（这正是 R1 阻塞③的关键）：
`init`（已接入）+ `.witnessloop/policy.json` 是**目录** ⇒ `witnessloop：内部错误（IsADirectoryError: …）`、退 1 ⇒ 先炸在**族外** `initcmd.py:215`（`read_bytes`）；
`uninit` + 台账里某文件是**目录** ⇒ 同形态 ⇒ 族外 `uninitcmd.py:59`。
反过来也核了 `events` 侧：目录冒充确实炸在**族内**那一点（`events.py:51`、`IsADirectoryError`，且单层 glob 真会把目录收进来）⇒ spec Scenario 2 的配方对。**R1 阻塞③闭环。**

### 4.【细节未定】`design.md` §3 的 `:118` 定案 → ✅ **到位且可落地**

`design.md:117-121`：读失败 ⇒ **报一行点名文件的诊断（`无法解码`/`无法读取`）+ 退 1，不进 diff**，**不得**让 `None`/异常流进 `render_diff`；
并给了显式二选一出口（移进非目标 + 写明理由）。`_already_initialized:224-229` 的 `! {rel} 缺失（台账记录它应存在）` 就是「不 render_diff、直接打印一行」的**现成先例**
⇒ 配方可实现，不会重蹈 `AttributeError: … splitlines`。**R1 阻塞④闭环。**

### 5.【非阻塞 5 条】→ ✅ **到位 4 条 + 2 处小瑕**

- **新 §3.5 非目标** ✅（`design.md:128-138`）：`read_bytes`（含「合计 4 处」的显式计数）、`sha256_tree`、**「半成品 `init`」写点**三条都在。
- **R9** ✅ 在（`:160`）。小瑕：编号排在 R7 之后、R8 之前（7 → 9 → 8），纯排版。
- **D3 措辞收紧** ✅：`:84-90` 已写成「**三种 `except` 并存**（**不是**『已有唯一 idiom』）」。**计数我逐条 grep 复核，全部为真**：
  `(OSError, ValueError)` **5 处**（`policy.py:134`、`contract.py:177/232`、`evidence.py:166`、`paths.py:69`〔换序〕）；
  `(OSError, json.JSONDecodeError)` **2 处**（`initcmd.py:64/132`）；`(OSError, UnicodeDecodeError)` **1 处**（`evidence.py:225`）。
- **§1.1 绝对句收窄** ✅：`design.md:26` 与 `proposal.md:37-38` 都收成「**非交互**调用路径」+ `KeyboardInterrupt` 例外。
- **R2 机制改 stale 判定** ✅：`design.md:145-149` 写的是 `_check_git_span` 的 stale 判定——我在代码里核到 `contract.py:272`（定义）与
  `:325`（`head_sha=… 不是本次被检 revision … 的祖先`）⇒ 机制名与 finding 文案都属实，「两种都会红」的注解也留着。

### 6.【新增内容的小瑕】→ 非阻塞

`design.md:107`「『已覆盖（无需动）』清单……**（共 5 处）**」后面实际列了 **6** 个位置
（`policy.py:133`、`contract.py:176`、`contract.py:231`、`evidence.py:165`、`evidence.py:224`、`paths.py:69`）⇒ 应为「共 6 处」。
同段 `:85` 说 `(OSError, ValueError)` **5 处**、`:90` 又说「与既有 **4 处**分叉」——两种口径各自都讲得通（4 = 不换序的写法，5 = 含 `paths.py:69`），
但同一节并列两个数字容易误读，收一下更稳。

## 跨文档一致性扫描

| 事实 | 结论 |
|---|---|
| `:201` 的定性 | ❌ **`design.md:124`（同时漏两者）vs `proposal.md:48` / `tasks.md:22`（`OSError` 已捕）** ⇒ 阻塞 **B1** |
| `:63` 的定性 | ✅ 一致（`proposal.md:49` / `tasks.md:23` / `grill-review.md:77` 都写「不是缺陷形态 · 可选」）。⚠️ 小瑕：`design.md:122` 与 `:210`（§8 Q1）仍把 `:63` **无条件**列在「补元组」范围内 ⇒ 与「可选」的措辞不齐（动作无害，非阻塞） |
| `read_bytes` 处数 | ✅ 一致：`design.md:108`「合计 **4 处**」（直接 2 + 间接 2）、`tasks.md:32`「4 处」；`design.md:105/121/211` 的「两处」都指**直接**那两处，口径可辨 |
| `init`/`uninit` 测试配方 | ✅ 一致（`tasks.md:28-31` 与 `spec.md` ⚠️ 段同口径：必须非法 UTF-8）。⚠️ 小瑕：`spec.md` 的 ⚠️ 写「见 design §5 / tasks B3」，但 **design §5 里没有这条配方**（只在 §3.5 与 tasks B3）⇒ 指向应收成 `tasks.md B3` |
| 绝对句的收窄 | ✅ 一致（`design.md:26`、`proposal.md:37-38`）。change 目录里其余提到 traceback 的地方都是**被订正的对象**或**订正记录**，不是残留绝对句 |
| R2 的机制 | ⚠️ `design.md:145-149` 已改成 stale ✅，但 `tasks.md:44` 的括注仍是旧口径「多 change 同 PR ⇒ 它也要 building 证据」——design 已注明「两种都会红」且行动指引相同 ⇒ 非阻塞 |
| `grill-review.md:50` | ⚠️ 该行仍把 `:201` 与 `:131` 并成「**同一类**（同时漏 `OSError` 与 `UnicodeDecodeError`）」——对 `:201` 对、对 `:131` 错。R1 当时只点了 proposal/design/tasks 三处 ⇒ 属**遗留未清**（非阻塞，顺手可改） |
| `docs/gate.md:342` 的假话 | ✅ 仍是**待订正对象**（`tasks.md:45` 的 D1b 覆盖它）⇒ 不是残留，是排期中的任务 |

## 阻塞项

**B1（阻塞 · 分类错反着又犯了一遍）** — `proposal.md:48`、`tasks.md:21-22`

- **原文**：`proposal.md:48`「`initcmd.py:131`、**`:201`**、`uninitcmd.py:30` ｜ 有 try，但 `except json.JSONDecodeError` ⇒ **只漏 `UnicodeDecodeError`**」；
  `tasks.md:21-22`「**补 except 元组**……到 `initcmd.py:131/201`、`uninitcmd.py:30`（⚠️ **三处**都是补元组不是「无 try」，且**只漏 `UnicodeDecodeError`**——`OSError` **已捕**）」。
- **为什么错**：`initcmd.py:202` 与 `uninitcmd.py:31` 的 `except` **只有 `json.JSONDecodeError`**（不是元组）⇒ `OSError` **没被捕**。
  三处里**只有 `:131`** 是「`OSError` 已捕」。同一 change 的 `design.md:122-124` 明写 `:201`「**同时**漏 `OSError` 与 `UnicodeDecodeError`」
  ⇒ **两份文档对同一条事实各说各话**，而这正是本 change 立项时被纠过两次的那类错（R1 阻塞②）。
- **实测（`traceback` 直接钉行）**：台账 `chmod 000` 后——
  - `init` ⇒ `witnessloop：内部错误（PermissionError: [Errno 13] … init-manifest.json）`、退 1，栈钉在 **`initcmd.py:201`**；
  - `uninit` ⇒ 同形态，栈钉在 **`uninitcmd.py:30`**。

  （`ledger_gate_ref`（`:131`）先捕掉 `OSError` 返回 `None`，于是 `init` 一路走到 `:201` 才炸 ⇒ 「`:201` 漏 `OSError`」是**可观测**后果，不只是纸面分类。）
- **最小订正**（3 行，不动范围、不动动作）：把「只漏 `UnicodeDecodeError`（`OSError` 已捕）」**限定到 `initcmd.py:131`**；
  对 `initcmd.py:201`、`uninitcmd.py:30` 改回 `design.md:124` 的口径——「有 try，但 `except json.JSONDecodeError`（`:202`/`:31`）⇒ **同时漏 `OSError` 与 `UnicodeDecodeError`**」。
  B1 的**动作**（统一写成 `except (OSError, ValueError)`）**不必改**；B3 的配方（非法 UTF-8）**继续钉住**——它是「解码那一半」的红先，
  「`OSError` 那一半」在 `init`/`uninit` 上按 R1 的族外论证**不必**造用例。

## 我实测的

> 本轮**没有**给 worktree 打补丁（无需：被核对象是文档 + 已有的行为）；全部实测在 `/tmp/r2`–`/tmp/r5` 上跑，CLI 一律 `uv run witnessloop …`。

1. **基线**：`uv run pytest -q` ⇒ **413 passed**（72s，exit 0），与基线声明一致。
2. **整合未碰代码**：`git show e324e5e --stat` = `design.md` / `proposal.md` / `tasks.md` / `spec.md` / `reviews/*` 五份文档（+ 新增 R1 报告），**没有** `src/**`、`tests/**`。
3. **`init --policy <含 0xff 的 seed>`**（`/tmp/r2`）⇒ `init：'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`、`EXIT=1` ⇒ R1 的回写字面**逐字为真**（「内部错误」那条假观测可证伪）。
4. **`init` + 台账 `chmod 000`**（已接入）⇒ `witnessloop：内部错误（PermissionError: [Errno 13] Permission denied: '<abs>/init-manifest.json'）`、`EXIT=1`；直调 `initcmd.run`（绕开 `entry.main` 兜底）后栈钉在 **`initcmd.py:201`**。
5. **`uninit` + 台账 `chmod 000`** ⇒ 同形态；直调 `uninitcmd.run`，栈钉在 **`uninitcmd.py:30`** ⇒ `:30` 的 `except`（`:31`）漏 `OSError` 亦实证。
6. **`init`/`uninit` + 台账非法 UTF-8** ⇒ `witnessloop：内部错误（UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff …）`、`EXIT=1`（`init` 侧栈钉在 `:131` = 「`:131` 遮蔽 `:201`」那条；`uninit` 侧钉在 `:30`）⇒ 非法 UTF-8 确实是这两条路径的红先配方。
7. **族外性复核**（B3 理由）：`init` + `policy.json` 是目录 ⇒ `内部错误（IsADirectoryError …）`（族外 `:215`）；`uninit` + 台账里文件是目录 ⇒ 同（族外 `:59`）⇒ 用「目录冒充」写 B3 用例确实够不着族内读点。
8. **`events.py:51` 的目录冒充**（反向对照）：直调 `load_events_file`，栈钉在 **`events.py:51`**、`IsADirectoryError`；单层 glob 确实把这个目录收了进来 ⇒ spec Scenario 2 的配方成立。
9. **证据判定**：`evidence.grill_evidence_findings(grill-review.md)` ⇒ **只剩 Q1–Q4 未经用户确认 4 条**（其余全过）⇒ 与 R1 末节第 16 条一致。
   另：把**同一判定**套到 `grill-adversarial.md` 会得「缺 `## Confirmed Decisions` / 缺 `## User Confirmation`」2 条，但 `check` 只在 `pol.grill_stage`（默认 `grill`）上开 `verify_body`
   （`checkcmd.py:83` → `evidence.py:238`），`building` 那条只要求「存在」（`:92-98`）⇒ **这不是 gate 缺口**，也是本轮追加进本文件（而非新开文件）不引入新红的原因。
10. **干净性**：本轮**未改**本 worktree 任何文件（只读 + `/tmp` 建仓）；`git status --porcelain` 为空、**未 commit**。

---

# 第 3 轮（R3 · 轮数封顶 · 最后一轮）

> **结论一句话**：**R2 的唯一阻塞项已彻底闭环**——`initcmd.py:63/131` 与 `:201`/`uninitcmd.py:30` 的**两类分类**在
> `proposal.md` / `design.md` / `tasks.md` 三份文档里**逐字同口径**，且我**开门核码 + 实测钉行**双复核为真
> （`:64`/`:132` 是 `(OSError, json.JSONDecodeError)` ⇒ 只漏解码；`:202`/`uninitcmd.py:31` 只有 `json.JSONDecodeError` ⇒ 两个都漏）。
> **无新引入的不一致、无过度订正**（这次的订正是**往回收**，方向对）。**PASS。**
> 唯一须点名的是**一条非阻塞的「声称做了、其实没做」**：commit `43117c3` 的消息说回写了 `grill-review.md` 里
> 「与 `:131` 同一类」那句，但**该文件本次一个字节都没动**（git 证据见下）——见「非阻塞但请一并」。

## Reviewer

- run id: `grill-adversarial-reviewer-events-readpoint-fix-2026-10-12-r3`
  （`WITNESSLOOP_RUN_ID` 本环境仍未设 ⇒ 同 R1/R2 按 `templates/grill.md` 走确定性兜底形态 `<stage>-<role>-<anchor>`。）
- 时间: **2026-10-12T09:18:44Z**
- **零记忆（第 3 轮 · 轮数封顶）**：不读作者 / grill / R1 / R2 的会话历史；R1、R2 的报告只作为**被核对象**读，不作为我的记忆。
- 基线实测：`uv run pytest -q` ⇒ **413 passed**（32.58s，exit 0），与基线声明一致。
- 本轮**未修改本 worktree 任何文件**（只读 + 在 `/tmp/r3` 建仓跑 CLI）⇒ `git status --porcelain` 为空、**未 commit**。
- CLI 一律 `uv run --project <本 worktree> witnessloop …`（PATH 上的裸 `witnessloop` 是另一份 uv-tool 安装）。

## Verdict

**PASS**

- R2 的**唯一阻塞项**（两类分类）**已到位**，且这次是**反向订正**（把上一轮的「只漏」收回到只有 `:131` 适用）——方向对；
- 三份文档的读点分类**逐字一致**且**与代码一致**（第 1 节，含**两份独立实测**）；
- **未新引入**不一致、**未过度订正**；`docs/gate.md §8` 那句错话仍是**排期中的 D1b 对象**（不是残留）；
- 支点 / D1–D4 / §3.5 / B3 配方 / `:118` 定案 / 绝对句 / R2 机制 —— **R2 已复核，本轮抽查复现无翻覆**。

## 逐条核验（本轮收窄范围：这次整合 2 项 + 有无新问题）

### 1.【R2 阻塞项】两类分类 → ✅ **三份文档逐字一致，且与代码一致**（开门核码 + 实测钉行）

**代码事实**（`grep -n "" <file> | sed -n`，本 worktree 原样，未打补丁）：

| 读点 | `except` 子句（**实测原文**） | 漏什么 |
|---|---|---|
| `initcmd.py:63`（`--policy`） | `:64` = `except (OSError, json.JSONDecodeError) as exc:` | **只漏** `UnicodeDecodeError` |
| `initcmd.py:131`（`ledger_gate_ref`） | `:132` = `except (OSError, json.JSONDecodeError):` | **只漏** `UnicodeDecodeError` |
| `initcmd.py:201`（`_already_initialized`） | `:202` = `except json.JSONDecodeError as exc:` | **两个都漏** |
| `uninitcmd.py:30` | `:31` = `except json.JSONDecodeError as exc:` | **两个都漏** |

**三份文档的对应措辞**（逐字抄，`|` 分列以示同口径）：

- `proposal.md:48`：`initcmd.py:131` ｜「`:132` 是 `except (OSError, json.JSONDecodeError)` ⇒ **只漏 `UnicodeDecodeError`**」
- `proposal.md:49`：`initcmd.py:201`、`uninitcmd.py:30` ｜「有 try，但 `except` **只有 `json.JSONDecodeError`** ⇒ **`OSError` 与 `UnicodeDecodeError` 都漏**」
- `proposal.md:50`：`initcmd.py:63` ｜「`:64` 是 `except (OSError, json.JSONDecodeError)` ⇒ **只漏 `UnicodeDecodeError`**；而它又被下游 `:148` 的 `except ValueError` 接住」⇒ **降级为「文案改善（可选）」**
- `design.md:124`：`initcmd.py:131`（`:132`）、`initcmd.py:63`（`:64`）：`except (OSError, json.JSONDecodeError)` ⇒ **只漏 `UnicodeDecodeError`**
- `design.md:125`：`initcmd.py:201`（`:202`）、`uninitcmd.py:30`（`:31`）：`except` 只有 `json.JSONDecodeError` ⇒ **`OSError` 与 `UnicodeDecodeError` 都漏**
- `tasks.md:22-23`：`:131`/`:63` **只漏 `UnicodeDecodeError`**（`OSError` 已捕）；**`:201`/`uninitcmd.py:30` 两个都漏**——其 `except` 只有 `json.JSONDecodeError`

⇒ **`{63, 131}` / `{201, 30}` 的二分，三份文档与代码四方完全对齐**，且三份都附了同一套动作
（`design.md:127`、`tasks.md:20`：统一补成 `except (OSError, ValueError)`，**两类都适用**）。
**⚠️ 本轮「一处说 A、另一处说 B」我没有抓到**——这与前两轮各抓出一条不同，说明这次是真落齐了。

### 2.【顺手项】三小项 → ✅ 2 项到位、⚠️ 1 项「声称做了但没做」

- **`design.md:107` 计数 5 → 6** ✅：现为「`policy.py:133`、`contract.py:176/231`、`evidence.py:165/224`、**`paths.py:69`**（共 **6** 处）」——
  我逐个数：1 + 2 + 2 + 1 = **6** ✓，与 R2 的复核一致。
- **`tasks.md:45` 改成 stale 口径** ✅：现为「改别的 change 目录里的**非证据文件** ⇒ 它的 manifest 判 **stale**」，
  与 `design.md:151-155`（`_check_git_span` 的 stale 判定为主、building 门禁为辅）同口径；行动指引「只改 `docs/gate.md`」不变。
- **`grill-review.md` 那句回写** ❌ **未落盘** —— 这是本轮唯一须点名的项，见「非阻塞但请一并」第 1 条（**它不阻塞**，理由同节）。

### 3.【有无新问题】→ **无新不一致、无过度订正**

- **是不是「又做过头」？不是。** 这次的订正是**往回收**：把 R2 指出的「四个读点一律只漏解码」收回成
  「只有 `:63`/`:131` 如此，`:201`/`:30` 两个都漏」——**收的方向与代码事实一致**（第 1 节实测），
  且**没有**顺手把不该改的也改了（`design.md` 的「已覆盖」6 处、`read_bytes` 4 处、B3 配方、`:118` 定案**均未被动**）。
- **整合未触碰代码** ✅：`git show 43117c3 --stat` = `design.md` / `proposal.md` / `tasks.md` / `reviews/grill-adversarial.md`
  **四份 .md**，**没有** `src/**`、`tests/**` ⇒ 「整合引入代码回归」这条路不存在，413 passed 与基线同源。
- **残留的两处小瑕**（R2 已判**非阻塞**，本轮复核仍在，**未恶化**）：
  1. `design.md:122` 与 §8 Q1（`:216`）仍把 `:63` **无条件**列进「补 except 元组」的动作组，而同节 `:130` 又说 `:63` **降级为可选**
     ⇒ 措辞不齐。**动作无害**：`:63` 若真补 `ValueError`，只是把 `init：'utf-8' codec …` 变成
     `init：--policy 文件无法解析为 JSON：…`（**都是退 1、都不是「内部错误」**）⇒ 纯文案改善，不制造红。
  2. `tasks.md:21` 的动作清单列 3 个目标（`:131/201`、`uninitcmd.py:30`）而 `:22` 的括注说「**四处**」——第 4 处 `:63` 在同句里被标为可选
     ⇒ 内部可解释，非矛盾。
- **`docs/gate.md:342` 的错话** ✅ 仍是**待订正对象**（`tasks.md:46` 的 D1b 覆盖它：「实测是**一行** `内部错误`」），**不是残留**。
  `docs/gate.md:336-340` 的读点表**确实只有 3 行、无 events 行** ⇒ D1「**新增一行**」的对象仍对。

### 4.【收尾核对】pytest / 证据判定 / 干净性

- **`uv run pytest -q` ⇒ 413 passed**（32.58s）✅ —— 与基线声明一致。
- **`evidence.grill_evidence_findings(grill-review.md)` ⇒ 4 条**，**只有** Q1/Q2/Q3/Q4「未经用户确认」
  ⇒ **与 R1 末节第 16 条、R2 末节第 9 条一致**，其余（`## Confirmed Decisions` ≥3、每条带 `来源:`）**已过** ⇒
  E0 停轮拿到答复后即可放行，路径仍通。
- **干净性** ✅：`git status --porcelain` 为空、**未 commit**；本 worktree 的 `src/**` **一个字节未改**（补丁只跑在 `/tmp` 上，且我**根本没打补丁**——本轮被核对象是文档 + 既有行为）。

## 非阻塞但请一并（**不构成 CHANGES_REQUESTED**，但请别跳过）

**1. `grill-review.md:50` 的回写「声称做了、其实没做」——commit 消息与 tree 不符。**

- **声称**：`43117c3` 的提交消息第 3 条：「顺手：… 回写 `grill-review.md` 里「与 `:131` 同一类」那句（R2 指出的遗留）」。
- **事实**：`43117c3` 的 `--stat` **不含** `grill-review.md`；`git log -1 --format="%h %s" -- reviews/grill-review.md`
  ⇒ 最后改动是 **`e324e5e`**（R1 整合，**早于** R2）；`grep -n "同一类" reviews/grill-review.md` ⇒ 该句**仍原样在 `:50`**。
- **为什么不阻塞**（我按「会让实现失败 / spec 自相矛盾 / 结论站不住」三条逐一排除）：
  1. **不会让实现失败**：实现者读的是 `design.md §3` 与 `tasks.md B1`，两处**已正确**（第 1 节）；
  2. **不是 spec 自相矛盾**：`spec.md` **不含**任何读点分类；`proposal`/`design`/`tasks` 三份**已一致**；
     `:50` 只活在**决策记录**里，且它**自己的括注**把「同一类」定义为「补 except 元组，不是新包 try」——
     **按这个自述口径，四个读点确实同类**（都要补元组），所以该句至多**歧义**，不是可判定的假话（R2 读成「漏集合同类」，那是另一种读法）；
  3. **结论站不住？不**：`grill-review.md:50` 在 `## Code-Resolved Questions`（`:29-73`），**不在**停轮交给用户的
     `## Open Questions`（`:74-91`），Q1 的推荐答案（`:79`）只给**统一动作**、不含错误分类 ⇒ **用户拍板面干净**。
     （对照：R1 阻塞① 之所以阻塞，是因为那条假观测**就在 Q1 本体里**，`templates/grill.md` 明说「别把没经证伪的结论拿去让用户拍板」。）
- **但仍建议现在改**（**此刻是免费的**）：一行编辑，把「与 `:131`/`uninitcmd.py:30` 是**同一类**」收成
  「与 `:201`/`uninitcmd.py:30` **同属「补元组」那一类**（`:131` 只漏解码，见 `design.md:124`）」。
  **过时点**：一旦 `manifest build --stage grill` 绑了 `grill-review.md`，再改它就会把 manifest 判 **stale**、须重建
  ⇒ 趁 E0 之前改，代价为 0。
- **顺带（同一性质）**：`proposal.md:53` 说「**两轮审阅纠正了我三处分类错**」，紧接着却列了 **①②③④ 四项**
  （④ 是 `:63` 的**降级**，不是「分类错」）⇒ 数字与枚举对不齐。纯措辞，非阻塞。

## 我实测的

> 全部在 `/tmp/r3` 的**真 git 仓**上跑（`git init` + `witnessloop init` 接入 + `.witnessloop/init-manifest.json`）；
> 本 worktree **只读**、**未打补丁**、`git status --porcelain` 为空、**未 commit**。CLI 一律 `uv run --project <本 worktree> witnessloop …`。
> 运行身份 **uid=10001**（非 root ⇒ `chmod 000` 真实生效，无 R6 的 root 假绿干扰）。

1. **基线**：`uv run pytest -q` ⇒ **413 passed**（32.58s，exit 0）。
2. **整合未碰代码**：`git show 43117c3 --stat` = `design.md` / `proposal.md` / `tasks.md` / `reviews/grill-adversarial.md` **四份 .md**，
   `src/**`、`tests/**` **未动**。
3. **开门核码**（`except` 子句原文，四方对齐）：`initcmd.py:64` = `except (OSError, json.JSONDecodeError) as exc:`；
   `initcmd.py:132` = `except (OSError, json.JSONDecodeError):`；`initcmd.py:202` = `except json.JSONDecodeError as exc:`；
   `uninitcmd.py:31` = `except json.JSONDecodeError as exc:`。
4. **实测·台账 `chmod 000`**（直接调 `initcmd.run` / `uninitcmd.run`，绕开 `entry.main` 兜底，`traceback` 钉行）：
   - `init` ⇒ `PermissionError`，帧链 `initcmd.py:160` → **`initcmd.py:201`**
     （⇒ `:132` 的 `OSError` **确实捕了**、返回 `None`，一路走到 `:201` 才炸 ⇒ 「`:201` 漏 `OSError`」是**可观测**后果）；
   - `uninit` ⇒ `PermissionError` @ **`uninitcmd.py:30`**。
   ⇒ 文档「`:201`/`:30` **两个都漏**」**实测为真**。
5. **实测·台账非法 UTF-8**（同一仓，把台账写成 `\xff\xfe`）：
   - `init` ⇒ `UnicodeDecodeError`，帧链 `initcmd.py:156` → **`initcmd.py:131`**
     （⇒ `:132` **没有**捕 `UnicodeDecodeError`，且 `:131` **遮蔽**了 `:201`——与 R1 第 5 条的「遮蔽」论证一致）；
   - `uninit` ⇒ `UnicodeDecodeError` @ **`uninitcmd.py:30`**。
   ⇒ 文档「`:131` **只漏** `UnicodeDecodeError`」与「`:30` 两个都漏」**实测为真**（**两条路都**钉在声明的那一行）。
6. **CLI 端到端**（同上两因、走产品入口）：`chmod 000` 台账 ⇒ `init` 与 `uninit` 各得**一行**
   `witnessloop：内部错误（PermissionError: [Errno 13] Permission denied: '<abs>/init-manifest.json'）`、**`EXIT=1`**
   ⇒ 「内部错误」形态与文档描述**逐字一致**，且**不是** traceback。
7. **计数复核**：`grep -rn` 全树 ⇒ `(OSError, ValueError)` **5 处**（`policy.py:134`、`contract.py:177/232`、`evidence.py:166`、`paths.py:69`〔换序〕）、
   `(OSError, json.JSONDecodeError)` **2 处**（`initcmd.py:64/132`）、`(OSError, UnicodeDecodeError)` **1 处**（`evidence.py:225`）；
   `read_text` **13 处**、`read_bytes` **4 处**（`hashing.py:19/35`、`initcmd.py:215`、`uninitcmd.py:59`）
   ⇒ `design.md:107` 的「共 6 处」与 `§2.5/§3.5` 的「合计 4 处」**全部为真**。
8. **文献对象核对**：`docs/gate.md:336-340` 读点表**只有 3 行、无 events 行** ✅；`docs/gate.md:342` 确有那句错的
   「`check` ⇒ traceback」✅（⇒ D1「新增一行」、D1b「订正错话」的对象都真实存在）。
9. **回写落盘核对**：`git log -1 --format="%h %s" -- openspec/changes/events-readpoint-fix/reviews/grill-review.md`
   ⇒ **`e324e5e`**（非 `43117c3`）；`grep -n "同一类"` ⇒ `grill-review.md:50` **原样仍在** ⇒「已回写」**不成立**。
10. **证据判定**：`evidence.grill_evidence_findings(grill-review.md)` ⇒ **4 条**，全是 Q1–Q4「未经用户确认」⇒ 与 R1/R2 一致。
11. **干净性**：本 worktree `git status --porcelain` 为空、**未 commit**；本轮唯一改动是本文件（**仅追加** R3 段，R1/R2 逐字保留）。
