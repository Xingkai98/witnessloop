# 对抗审阅（A2 轮，独立零记忆）

## Reviewer

- **身份**：独立零记忆对抗者（A2 轮）。未参与本 change 的立项 / grill / A1。本对话不携带任何历史：
  文档里的「实测」「已落库」「已收敛」一律当**待验证断言**，可复算的一律复算。
- **工作区**：`/home/happy/wl-wt/archive-arrival-recognition`（git worktree），
  分支 `archive-arrival-d-side/2026-10-17`。
  **`git rev-parse HEAD` = `ab060424c49aeb6cb976dcabc2f77031fb146ba5`**
  （`git show --stat` ⇒ 单个 commit 落了本 change 的 6 个文件 / 992 insertions）。
  ⚠️ 与 A1 报告里「整个 change 目录**未被跟踪**」的写法**不同**：现在它**已被跟踪**
  （`git ls-files openspec/changes/archive-arrival-d-side/` 有 6 条输出）⇒ 本轮清洁度**不能**用
  `git status` 判，我用 `git diff --stat HEAD`（**空**）+ `git status --porcelain`（只有本新文件）核。
- **读了什么**：`proposal.md` / `design.md` / `tasks.md` / `specs/archive-awareness/spec.md` /
  `reviews/grill-design.md` / `reviews/grill-adversarial-a1.md` 全文；
  `src/witnessloop/{contract.py,checkcmd.py,gitutil.py,paths.py,policy.py,constants.py}` 的相关段；
  `tests/{helpers.py,conftest.py,test_archive_awareness.py,test_archive_arrival.py}`。
- **跑了什么**（实验**全部**在 `/tmp/a31b/`，用 `git archive HEAD | tar -x -C …` 建代码根——
  本仓是 worktree、`.git` 是指针文件，**不**能 `cp -a` 整目录）：

  | # | 命令 / 构造 | 结果 |
  |---|---|---|
  | 1 | `/tmp/a31b/base` 未改代码：`PYTHONPATH=src python3 -m pytest -q` | `702 passed in 222.37s`（与称述的基线一致） |
  | 2 | `/tmp/a31b/p_proto` = 按 `design.md §2 D1` **逐字**实现 `d_move_halves` + 接线 `_archive_move_exempt`（③ = `source_ids == {<id>}`，即「丙」） | 见下 |
  | 3 | `/tmp/a31b/p_ji` = 同上但 ③ 改成 `<id> ∈ source_ids`（「甲」，A1 的旧判据） | 用于三路对照的交叉校验 |
  | 4 | 真 git 端到端探针 P0–P13（`p_proto/tests/test_a2_probe.py`：真仓 + 把 CLI 当子进程跑、按 `PYTHONPATH` 切代码根） | 见 `## 对抗结论` |
  | 5 | 回归：`p_proto` 下 `tests/{test_archive_awareness,test_archive,test_archive_arrival}.py` | `65 passed in 83.02s`（⇒ 原型对既有归档测试零回归） |

- **我**未**复算的**：issue #31 的原始测量（`8e5fc83b` / `d94c08334`）、真 CI、接入方 asterwynd 的行为
  ——它们**不计入**必须修改项（见「未验证项」）。
- **本仓写入**：仅本文件（新建）。`git diff --stat HEAD` 空 ⇒ 未改任何已跟踪文件；未 commit / 未 reset / 未 push。

---

## 对抗结论

### 0. 结论速览

| 面 | 结论 |
| --- | --- |
| 目标形态（issue #31 复现）修好了吗？ | **是**（P0：base rc=1 1 项 → 丙 rc=0） |
| 新判据（丙）**充分**吗？ | **不充分**——**第四条路**：自造一个到达目录即可（P7，`rc=0 全绿`） |
| 丙 挡住 A1 的 S2 了吗？ | 挡住了 A1 的**那一个构造**（P1 复算 rc=1）；**没挡住它的机制**（P7） |
| 丙 的误伤代价在真实流程下多常见？ | **≈ 0**（P9：`#29` 次序的正当归档 diff 里**一条 `D` 都没有**；P10：同 PR 归档两个 change 也不触发） |
| 「一份实现」？ | 与设计一致（`changed` 不动）——但实现的**判据仍可被绕过**（A2-1） |
| `<sub>` 边界 | 前导 `./` / 大小写 / 含 `/` / `<id>`≠`<name>` 均如设计；**尾斜杠**（`<id>/`）文档未钉（A2-6） |
| A1-1…A1-6 按 artifact 落库了吗？ | A1-1 ✓ / A1-2 ✓ / **A1-3 ✗** / A1-4 ✓ / A1-5 ✓ / **A1-6 ✗** |
| §6「停轮问题（无）」诚实吗？ | **部分**——Q1′ 的定案**依据**已被证伪；且存在一条真只有用户能拍的问题（QQ-A2-1） |
| **收敛** | **不收敛** |

---

### 1. 目标形态复算成立（P0），且我的原型与 A1 数字逐条吻合

**P0**（issue #31 形态）：main 上 `add-retry` 是完整、有证据的 active change；feature 上 `git mv` 整目录进
`openspec/changes/archive/2026-10-14-add-retry/`，并把它的 `workflow-events.jsonl` 重写成新内容
（⇒ git 报 `D` + `A`，其余 10 条 `R100`）。原始输出：

```
--- base ---    rc=1   12 个变更文件，1 个 change 目录
  1. openspec/changes/add-retry/workflow-events.jsonl：受保护路径被写入，但没有结构化解释事件
--- 丙 ---      rc=0   check：通过 ✓
--- 甲 ---      rc=0
```

**P1**（A1 的 S2 原构造：把 `another-change/notes.md` 搬进**真**到达目录，再删 `another-change/workflow-events.jsonl`）：

```
--- base ---  rc=1（2 项：add-retry 的事件文件 + another-change 的事件文件）
--- 甲 ---    rc=0   ← 洗白（复算 A1 的结论）
--- 丙 ---    rc=1（2 项） ← 挡住；但同时把 add-retry 自己那条也一并打红 = design §2 D1 登记过的代价
```

⇒ 目标形态成立，且**我的原型是 `D1(丙)` 的忠实转写**（与 A1 的甲/丙结论逐条吻合）⇒ 可以拿它攻判据本身。

---

### 2. **A2-1（核心 · 新证伪）**：第四条路 —— 判据③ `A.source_ids == {<id>}` **仍可被满足，而 `A` 并不是 `<id>` 的归档**

#### 2.1 构造（P7，真 git 端到端，`rc=0 全绿`）

`p_proto/tests/test_a2_probe.py::test_P7_attack_with_key`。main 上两个完整、有证据的 active change：
`add-retry`(a)、`another-change`(b)。feature 上：

```
A2 := openspec/changes/archive/2026-10-15-fake/     # 一个**全新的**到达目录
      · proposal.md / design.md / tasks.md / specs/a2u/spec.md / reviews/*.md
        全是**新增**文件（内容唯一，避开到达判据 5 的「白捡内容」判定）
      · workflow-events.jsonl  也是新增文件（= 给 D 侧配对用的 A 记录）
git mv changes/another-change/notes.md  A2/notes.md        # **钥匙**：唯一一条把 b 带进 source_ids 的记录
git rm changes/another-change/workflow-events.jsonl        # 攻击目标：删「仍活着的」change 的不变集受保护文件
（再 manifest build 给 A2 造三份 stage manifest）
```

diff（原始输出）：

```
D	openspec/changes/another-change/workflow-events.jsonl
A	openspec/changes/archive/2026-10-15-fake/design.md
R100	openspec/changes/another-change/notes.md	openspec/changes/archive/2026-10-15-fake/notes.md
A	openspec/changes/archive/2026-10-15-fake/proposal.md
A	openspec/changes/archive/2026-10-15-fake/reviews/building-review.md
A	openspec/changes/archive/2026-10-15-fake/reviews/grill-adversarial.md
A	openspec/changes/archive/2026-10-15-fake/reviews/grill-review.md
A	openspec/changes/archive/2026-10-15-fake/specs/a2u/spec.md
A	openspec/changes/archive/2026-10-15-fake/tasks.md
A	openspec/changes/archive/2026-10-15-fake/workflow-events.jsonl
```

`check`（原始输出）：

```
--- base ---  rc=1   10 个变更文件，2 个 change 目录（another-change, 2026-10-15-fake（归档））
  1. openspec/changes/another-change/workflow-events.jsonl：受保护路径被写入，但没有结构化解释事件
--- 丙 ---    rc=0   check：通过 ✓          ← 一条 finding 都没有
--- 甲 ---    rc=0
```

纯函数侧（**未改**的 base 代码根跑 `contract.archive_arrivals`）：

```
ARRIVAL 2026-10-15-fake | source_ids = ['another-change']
```

⇒ `A.source_ids == {<id>}` **被逐字满足**，而 `A` 根本不是 `b` 的归档——它是攻击者**自己新建**的一个目录。

#### 2.2 为什么这是**新的**证伪，不是 S2 的重复

丙 挡住的是 A1 的 **S2 那一个构造**（把 b 的文件塞进**真**到达目录 ⇒ `source_ids = {a, b} ≠ {b}`），
**不是 S2 的机制**。机制是「让某个到达目录的 source 集合**恰为** `{<id>}`」；而「哪个目录成为到达目录」
由**攻击者**决定（他可以在 `archive/` 下新建目录，判据 1/2/3/5 全部放行——P7 里 A2 被正常认成
「`2026-10-15-fake`（归档）」）。⇒ 只要**另起一个到达目录**，`==` 与 `∈` 就没有区别。

被本条证伪的实体（逐条 `文件:行号`）：

| 断言 | 位置 | 实测 |
| --- | --- | --- |
| 「**取丙**：它是唯一同时挡住 S2 与 S8 的」 | `design.md:66` | **假**：丙 只挡住 S2 的**一个实例**，机制未挡住（P7 `rc=0 全绿`） |
| 三路对照表里 丙 的 **S2 列 = ✓** | `design.md:65` | **假**（同上） |
| 「⇒ 三条里只有「**恰为** `{<id>}`」同时挡住 ②③」 | `specs/archive-awareness/spec.md:39` | **假**（同上） |
| 「⚠️ **「`<id> ∈ sources`」那一版会漏**（实测 rc=0 全绿）」——暗示 `==` 版不漏 | `spec.md:88` | **误导**：`==` 版**也**漏，只是换一条构造 |
| §2 D1「两条已知残留」只列了 纯 `D`+`A` 与 跨配对；§3 / §4 R 也无此形态 | `design.md:79-85`、`design.md:120-132`、`design.md:136-142` | **未登记**：第四条路在文档里**无处出现** |

#### 2.3 「那时 `b` 的其余受保护文件被豁免是否正确？」——**不正确**

`b` 在 head 里**仍然活着**：它的目录、五件必需件、三份 manifest 都在，`check` 也把它当 active change
正常校验（原始输出里 `change：another-change, 2026-10-15-fake（归档）`）。它的 `workflow-events.jsonl`
是**真删**；A2 里的同名文件是**另一个新增文件**——判据②只比**路径**，**不比内容**。
这正是 `tasks.md:29-31` 与 `spec.md:83-88` 声明要守住的那条：「**单独**删一个 active change 的受保护文件 ⇒ 仍要事件」。

**放大（P13）**：把 A2 的三份 manifest **提交进树**（使它们成为 diff 里的 `A` 记录——任何到达目录都必须有它们，
成本为 0），则 `b` 的 **3 份受保护 manifest 也一并被豁免**：

```
  [reviews/grill.manifest.json]              base=True  丙=False
  [reviews/grill-adversarial.manifest.json]  base=True  丙=False
  [reviews/building.manifest.json]           base=True  丙=False
  [workflow-events.jsonl]                    base=True  丙=False
```

⇒ 不变集的**全部 4 条**可同时洗白（且 `reviews/grill.manifest.json` 这类 `<sub>` 在本仓**每个 change
目录都一样** ⇒ 判据②的「逐字相同」几乎不携带信息，与 grill 的 R-b 同一观察）。

#### 2.4 对照组（证明这不是「任何构造都判绿」）

| 探针 | 构造 | base | 丙 |
| --- | --- | --- | --- |
| **P8** | 同 P7 但**不搬**钥匙 ⇒ `source_ids` 空 | rc=1，b 的 finding 在 | **rc=1，b 的 finding 在** ✓ |
| **P11** | 删掉**整个** `b` + 别处一次正当归档（N-d / G1 原文） | rc=1（7 项） | **rc=1（7 项全在）** ✓；`source_ids=['add-retry']` |
| **P10** | 同一 PR 归档**两个** change（且重写 c1 的事件文件） | — | `A1.source_ids=['add-retry']`、`A2.source_ids=['another-change']` ⇒ **git 未跨配对**（见 §3） |

---

### 3. 误伤面（保守代价）在真实接入方流程下的发生率 ≈ **0**（可复算）

- **P9（`#29` 次序的正当归档 = 纯 `git mv`）**：原始输出 `D_RECORDS []`
  ⇒ diff 里**一条 `D` 都没有** ⇒ 判据③**根本不会被求值** ⇒ 「跨配对 ⇒ 本搬移的 `D` 全部失去豁免」
  这条代价**不可能发生**。（11 条记录全是 `R100`。）
- **P10（同一 PR 归档两个 change，其中 c1 的事件文件被重写 ⇒ diff 里确有 `D`）**：
  两个到达目录各自 `source_ids` **单一且互不污染** ⇒ 也不触发代价。
- 唯一能触发代价的形态是 **S8 / N-k**（同一次 diff 里再删掉**整个**另一个 change 目录 ⇒ git 自发跨 change
  相似度配对）——那**不是**「`#29` 次序」，是异常簿记。

⇒ 结论：**丙 的误伤代价 ≈ 0**；它相对甲 的真实增量收益只在 **S8（零蓄意跨配对）那一格**。
这恰好抽掉了 `design.md:66` 选择 丙 时写下的依据（「同时挡住 S2 与 S8」）——**S2 那一格是假的**，
剩下的理由只有 S8 一格。这不等于该改（S8 那一格本身有价值），但**依据句必须改**。

---

### 4. `<sub>` 边界复核（逐条）

| 边界 | 实测 / 判断 |
| --- | --- |
| 前导 `./` | `paths.normalize` 去前导 `./`，D/A 两侧过**同一函数** ⇒ 无影响（git 也不产 `./` 形态）。**低危** |
| 大小写 | 逐字比较、**不**折叠大小写 ⇒ `Foo.md` 与 `foo.md` **不配对**（保守方向，正确；与 A1 同结论） |
| `<sub>` 含 `/` | 逐字前缀比较、`sub` 保留 `/`，无边界问题。实测深层子路径（`reviews/grill.manifest.json`、`specs/a2u/spec.md`）工作正常 |
| **路径正好是目录本身** | `<sub>` 为空 ⇒ 不配对。**两种写法都要挡**：`changes/<id>`（不含 `/`）与 `changes/<id>/`——`normalize` **不**去尾斜杠 ⇒ 会拆出 `sub == ""`。`design.md:72-77` 的算法段**只写了**前者（「`<sub>` 为空（记录正好是目录本身）」），**没写**尾斜杠那一支（见 A2-6） |
| 端到端可构造性 | git **不**为目录报 `D`（P0–P13 全量 `--name-status` 输出里从未出现）⇒ `<sub>` 为空**只能纯函数级测**（与 A1-6 同结论） |
| `archive/<date>-<id>` 命名、`<id>` ≠ `<name>` | **成立**：`<id>` 取自 D 的路径段，`<name>` 只用于定位 `A.directory`，两者不必相关（F2/F3 已钉） |
| `archive/**` 之外 | `contract.under_path` 按**路径分量**比 ⇒ `<changes_root>/archive-foo/…` **不会**被误判成 `archive/**` ✓ |

---

### 5. 规格可测性（`specs/archive-awareness/spec.md` 的 9 条 Scenario）

- **端到端可测**：8 条。我实测了其中 5 条：S1↔P0、N-d↔P11、N-j↔P1、N-i（A1 的 S3 形态）；
  N-a / N-b / N-e 有既有钉子（grill 的 D6 审计已列）。
- **只能纯函数级测**：**N-f（`<sub>` 为空）**——`spec.md:78-81` 的 `When` 仍写「运行 `check`」，
  **没有**任何「纯函数级」标注（`grep -c 纯函数 specs/.../spec.md` = **0**）⇒ 见 A2-3。
- **缺 Scenario**：spec 有 9 条，而 `design.md §3` 有 **11** 张否定面（`N-a…N-k`）。
  **N-c**（删掉整个 change、同 diff **无任何到达**）与 **N-g**（重建已存在的归档 manifest，`M`）
  **没有**对应 Scenario（两者有既有**代码**钉子：`tests/test_archive_awareness.py:249`；
  `tests/test_archive.py:60` 的弱形态）⇒ 见 A2-6（低危）。
- `tasks.md` 漏项 / 写不出来的项：`1.1` 的否定面计数过期（写 `N-a…N-h`，实为 `N-a…N-k`）⇒ 见 A2-5；
  `2.3` 里「`<sub>` 为空」未标「纯函数级」⇒ 见 A2-3。其余（2.1/2.2/2.4/3.x/4.x）**可写、能落地**。

---

### 6. §6「停轮问题（无）」的诚实性复核

- **Q1 / Q1′ 两行**：都如实写了替代路的代价（甲/乙/丙 的取舍与代价），**但 Q1′ 的定案依据**
  （`design.md:66`、`§6` 的 Q1′ 行「只有它同时挡住 S2 与 S8」）**已被 A2-1 证伪** ⇒ 依据句需改（A2-1）。
- **另外 4 行**（R/C 是否要求源目录消失、子路径要不要放宽到 basename、要不要把 `D`+`A` 喂给 `sources`、
  事件文件之外的受保护文件）**判断成立**，且都与代码实体一致（`contract.py:274-280` 的 `moved_content`、
  `contract.py:314-320` 的别名来源、`checkcmd.py:346-356` 的两档规则）。
- **有没有真只有用户能拍的？有** ⇒ 见 `## Open Questions` 的 **QQ-A2-1**。它不是「甲/乙/丙 三选一」
  （那是代码可单方面改的），而是「**本门禁对蓄意伪造的立场**」：`spec.md:42` / `§4 R3` 声明
  「**防漂移、不防蓄意伪造**（真锚是远端 branch protection + required check）」，而 `§2 D1` 又**以
  「挡住蓄意的 S2」当选择理由**。两句只能留一句 —— 这是产品承诺，不是代码细节。

---

## 未验证项

1. **issue #31 的原始测量**：`design.md §1` 引的 `8e5fc83b` / `d94c08334`、「34 个变更文件」、
   「只有一条 `D`」——那两个 sha 属接入方 asterwynd 的仓，本工作区 `git cat-file -e` 取不到
   ⇒ **未验证**。我复算的是**形态**（P0：12 个变更文件 / 1 项红 → 0 项）。
   （**不**计为必须修改项——文档只把它当背景，未写成「已验证」。）
2. **真 CI / GitHub Actions**：**未验证**。
3. **接入方 asterwynd** 的行为：**未验证**。
4. **grill 的 `✗9 → ✗3`**：**未逐字重跑**。我复算的是同形态（P11：删整个 `b` + 正当归档；
   P2 的 S8 形态亦未重跑）。A1 的 S8（5 项 → 3 项）本轮**未**复算。
5. **我的原型不是实现者的代码**（实现尚不存在：`tasks.md` 3.1–3.4 全未勾）。结论对
   「按 `design.md §2 D1` 这么实现」成立；若实现者加了别的守卫，A2-1 需重跑。
6. **N-h（symlink / gitlink）、N-g 的既有钉子**：本轮只跑了全量（`p_proto` 下归档三文件 `65 passed`
   + `base` 全量 `702 passed`），未逐条断言。
7. **`d_move_halves` 的签名**（`design.md:89` 写 `(changes, policy, arrivals)`）在实现时是否需要
   `view` / `head_rev`：**未验证**（D1 的三条判据不读树，我的原型也没读；但若实现者要恢复
   「源目录不在 head」那条就会需要——而那条已被删除）。
8. **我的原型只接线了 `checkcmd` 一处**（与 D2「`changed_change_ids` 不动」一致）；
   `changed_change_ids` 侧**未**做任何改动 ⇒ 与设计面一致，无额外未验证面。

---

## 必须修改项

### A2-1（**核心 · 新证伪**：判据③仍可被绕过，第四条路未登记）

**事实**（真 git 端到端，附原始输出，见 §2）：`A.source_ids == {<id>}` **不足以**把 `A` 认定为 `<id>` 的归档。
攻击者只要**另建一个到达目录**（必需件全新、内容唯一 ⇒ 判据 1/2/3/5 全放行），把 `<id>` 的**一个**文件
`git mv` 进去当钥匙（⇒ `source_ids == {<id>}`），再删 `<id>` 的受保护文件（其 `<sub>` 在 `A` 里有配得上的
`A` 记录）⇒ `check` **`rc=0 全绿`**，而该 change **仍然活着**。放大版（P13）可一次洗掉**全部 4 条**
不变集受保护文件。

**必须**（二者其一 + 三处登记）：

- **① 加严判据**（候选方向，均**未**实测，只是方向）：
  - **(a) 要求 `<id>` 在 head 树里**与本次搬移一致**：即「`<id>` 的全部受保护文件都在这次搬移里」或
    「`<id>` 的目录不再在 head」——但后者 = 乙，A1 已实测挡不住 S8，且会让 `D` 侧比 `R`/`C` 侧更严（grill 已否）；
  - **(b) 要求到达目录 `A` 里**没有**「新增（`A` 记录）的必需件」**或**要求 `A` 至少有一条来自 `<id>` 的
    **必需件**级 `R`/`C` 记录（P7 的 A2 必需件全是新增 ⇒ 被拒；issue #31 形态里 `a` 的必需件全是 `R100` ⇒ 仍放行）——
    这条**看上去**能挡住 P7，但**我没有实测**，且它可能误伤 F1 的「出生即归档」形态边界，**必须**先跑；
  - **(c) 内容同一性锚**（grill 的 Q1 已否，理由是 issue #31 里那个文件**被改写过**）。
- **② 或如实登记 + 降级声明**：把「删掉一个**仍活着**的 change 的受保护文件，可被『自造到达目录 +
  一把钥匙』洗白」写进 `design.md §3`（新增一张否定面）/`§4 R`/`§2 D1 的残留清单` + `spec.md`（新 Scenario）
  + `docs/gate.md §7 能力边界`；并**删掉** `design.md:65-66` 的三路表 丙/S2 列与「唯一同时挡住」句、
  `spec.md:39`、`spec.md:88` 的「暗示 `==` 版不漏」措辞。

**现状不可接受**：`design.md:66`、`spec.md:39` 与 `spec.md:88` 现在**是假话/误导话**，而这条路在
`design.md §2 D1 的两条已知残留`、`§3`、`§4 R1–R5` 里**一处都没有**。

### A2-2（A1-3 的**落库自述为假**——报告实体未改，且与 tasks/design 自相矛盾）

**事实**：`grill-adversarial-a1.md:377-378` 声称
「**处置里那句「tasks 3.3 已写明」是假的**，**已改**：G4 现在只登记为 §4 R5（**不动**那个死分支…）」。
但 `reviews/grill-design.md:204-205` **原文照旧**：

```
- **G4**：接受——`changed_change_ids:381-383` 是死代码，本 change 会**收掉它**并把那条空钉子测试一并订正
  （tasks 3.3 已写明）。
```

—— 与 `tasks.md:39-41`（「**`changed_change_ids` 不动**…`:381-383` 的死分支也**不**顺手动…登记为 §4 R5」）
和 `design.md:142`（§4 R5「**本 change 不动它**」）**直接矛盾**。句中的「（tasks 3.3 已写明）」也仍是那句被
判定为假的引用。

**必须**：把 `grill-design.md` 的 G4 行按 A1 的处置口径更正（加删除线 + 「❌ 已作废，见 A1 处置」，
与同文件 `:196-200` 对另一句的更正手法一致）。

### A2-3（A1-6 的**落库自述为假**——spec 与 tasks 里都没有「纯函数级」标注）

**事实**：`grill-adversarial-a1.md:383` 声称
「已在 `tasks.md 2.3` 与 spec 里写明它是**纯函数级**的钉子」。实体：

- `specs/archive-awareness/spec.md` 全文 `grep -c 纯函数` ⇒ **0**；`spec.md:78-81` 的 N-f Scenario 仍写
  「**When** 运行 `check`」（不可端到端构造 ⇒ 该 Scenario 目前是**不可测的规格文字**）。
- `tasks.md:32` 的 2.3 清单里只列了「`<sub>` 为空」，**无一字**说它只能纯函数级测；
  `tasks.md:33` 的 2.4 只覆盖「相对子路径逐字相等 / 前缀边界 / 大小写与 `./` 归一化」。

**必须**：把 `spec.md:78-81` 的 `When` 改成「构造该 `D` 记录（纯函数面）」或加注「只由纯函数测试覆盖」，
并在 `tasks.md 2.3`（或 2.4）写明它是纯函数级钉子。二者取一即可，但**必须**与 A1 的处置口径一致。

### A2-4（`spec.md:61` 的理由与判据不符；A1-1 的「删除被证伪断言」未执行）

**事实**：`spec.md:61`（N-d 那条杀手 Scenario 的 `Then` 理由）仍写
「（**第 3 条**不满足：`b ∉ A.source_ids`）」。当前判据是 **`A.source_ids == {b}`**：
`b ∉ A.source_ids` **既不充分也不必要**（`{b, c}` 也满足 `≠ {b}` 而 `b ∈ sources`）。
A1-1 的必须条款 ② 明列了「删掉 … `spec.md:52`（本条）… 里被证伪的断言」，**未执行**。
（说明：我在 P11 用该 Scenario 的**字面构造**实测 `source_ids=['add-retry']` ⇒ `b ∉ A.source_ids` 在该构造里
**碰巧为真**；但作为**理由**它把判据写回了「甲」，读到它的人会以为 ③ 是 `∈`。）
同条 Scenario 的 `Given` 也写 `A.source_ids = {<别的 id>}`，与 `Then` 的理由口径不一。

**必须**：把该处理由改成 `A.source_ids ≠ {b}`（与 `spec.md:88` 的 S2 Scenario 口径统一）。

### A2-5（`tasks.md 1.1` 的否定面计数过期）

**事实**：`tasks.md:21` 写「把 D1 的判据写成 Requirement + Scenario（含 **N-a…N-h** 的否定面）」，而
`design.md §3` 现有 **11** 张（`N-a…N-k`：`grep -c '^| N-'` = 11），`proposal.md:60` 也已改成「十一条」。
若实现者照 1.1 字面执行，规格增量会**漏掉 N-i / N-j / N-k**（正是本 change 最承重的三条）。

**必须**：把 1.1 的 `N-a…N-h` 改成 `N-a…N-k`（与 design §3 / proposal 对齐）。

### A2-6（低危：spec 缺 N-c / N-g 的 Scenario；`<sub>` 尾斜杠未在文档钉住）

**事实**：
- spec 有 **9** 条 Scenario，`design.md §3` 有 **11** 张否定面；缺 **N-c**（删整个 change 且同 diff 无任何到达）
  与 **N-g**（重建已存在的归档 manifest）的 Scenario（两者只有**代码**钉子）。
- `design.md:72-77` 的算法段只写「`<sub>` 为空（记录正好是目录本身）」，未覆盖 `changes/<id>/`
  （`normalize` 不去尾斜杠）这一支；实现若只判「不含 `/`」会漏掉它（我的原型显式判了 `sub == ""`）。

**必须**：补 N-c/N-g 的 Scenario（或显式声明它们由既有代码钉子覆盖），并在 `design.md §2 D1` 的算法段与
`tasks.md 2.4` 里补一句「尾斜杠 ⇒ 拆出空 `sub` ⇒ 不配对」。

---

## Open Questions

### QQ-A2-1（**真只有用户能拍**）：本门禁对「蓄意伪造」的立场——留「防漂移」还是留「挡 S2」？

**事实（已复算）**：`spec.md:42` / `design.md §4 R3` 声明本 capability「**防漂移、不防蓄意伪造**
（真锚是远端 branch protection + required check）」；而 `design.md:66` / `spec.md:39` **以「挡住蓄意的 S2」
作为选 丙 的理由**。这两句不能同时成立：

- 若**留「防漂移」**（= 承认本判据挡不住蓄意者）⇒ **A2-1（P7）落在既有边界内**，正确处置是
  「登记 + 删掉 S2/S8 的挡截声明」（A2-1 的 ② 分支），并且**甲 也可以**（更简单、误伤更小）——
  那么 `design.md:65` 的三路表就要重写：三路的差异只剩 S8 一格。
- 若**留「挡 S2」**（= 本判据必须挡住蓄意构造）⇒ 必须换锚，且**三条已知候选都有登记过的代价**：
  (a)「源目录不在 head」(乙) 挡不住 S8 且让 `D` 侧严于 `R`/`C`；(b) 内容同一性锚会被 issue #31 的
  「被改写的文件」拒掉；我**新提**的候选是「要求到达目录 `A` 至少有一条来自 `<id>` 的**必需件**级
  `R`/`C` 记录」——它看上去能挡住 P7 / P13 而不挡 issue #31 形态，**但我没有实测**（见未验证项 5、
  A2-1 ①(b)），且可能误伤 F1 的出生即归档边界。

**为什么只有用户能拍**：这是**产品承诺**（门禁对谁负责、承诺到哪一档），不是代码细节；
而且它决定了本 change 的**验收口径**（`proposal.md` 的「十一条否定面」是否要多一条、S1 的正向承诺是否要收窄）。

**我的推荐（不替用户选）**：先跑一次我提的候选 (b) 的探针（成本 ≈ 1 个测试）；若它同时满足
「挡 P7/P13」+「放行 S1」+「不破 F1–F18」，取 (b)；否则走 A2-1 的 ② 分支（登记 + 删声明），
并把「不防蓄意伪造」从**角落的边界句**提升到 `§2 D1` 的**正文**。

---

## 收敛结论

**不收敛**（两条判据**都**不满足）。

- **判据 ①「本轮没有新的可证伪项」→ 不满足**。
  本轮新增**可复算**的证伪（真 git + 真 CLI，附原始输出，**不是**措辞/计数/格式）：
  **A2-1**——第四条路：自造一个到达目录即可满足判据③，`check` **`rc=0 全绿`**，而被删文件的 change
  **仍然活着**（P7）；放大版 P13 可一次洗掉全部 4 条不变集受保护文件。
  它同时证伪了 `design.md:65-66`、`spec.md:39`、`spec.md:88` 三处**关于「丙 挡住 S2」**的断言。
- **判据 ②「已知必须修改项全部已落库」→ 不满足**。
  逐条按 **artifact** 核（`git show --stat ab06042` + 文件实体）：
  **A1-1 ✓**（`design.md:45` / `spec.md:21` / `proposal.md:46` 都是 `== {<id>}`，三路表在；
  但 `spec.md:61` 的理由未随改 → A2-4）／**A1-2 ✓**（`design.md:94-101`、`tasks.md:39-41` 均已删那半，
  理由①「恒空 no-op」②「第二洞」成立）／**A1-3 ✗**（`grill-design.md:204-205` 的假话未更正，
  A1 自己的处置 `:377-378` 谎报「已改」→ A2-2）／**A1-4 ✓**（`spec.md:102-103` 有别名/「与目录不符」边界文字）／
  **A1-5 ✓**（`proposal.md:42-47` 三条、`:60` 十一条，与 `design.md §3` 的 11 张一致；
  但 `tasks.md:21` 仍是 `N-a…N-h` → A2-5）／**A1-6 ✗**（`spec.md:78-81` 仍写「运行 check」、
  `grep 纯函数` = 0、`tasks.md 2.3` 无一字，A1 的处置 `:383` 谎报「已写明」→ A2-3）。
  （G1–G6 侧：G1 部分——判据确已重写但**新判据自己又被绕过**；G2/G3/G5/G6 ✓ 按实体落库；
  G4 见 A2-2。）

> 收敛要两条**都**满足（本轮**没有新的可证伪项** ∧ 已知必须修改项**全部按 artifact 落库**）。
> 当前停在 **A2-1**：与 grill 的 G1、A1 的 A1-1 落在**同一根骨头**上——**判据把「git 自己的配对」当身份证明，
> 而 git 的配对是全局的、且到达目录可由被门禁的那一方自造**。丙 只是把「污染已有到达目录」换成了
> 「自造一个到达目录」，成本没有实质变化。
> 下一轮（A3）请优先攻 **A2-1 ①(b) 的候选锚**（「到达目录至少有一条来自 `<id>` 的必需件级 `R`/`C`」）
> 与 **F1 出生即归档边界** 是否被它误伤。

---

## 处置（主 session 在 A2 之后追加，非审阅者原文）

> **A2-1 已落库（判据再次收紧）**；A2-3/A2-4/A2-5/A2-6 已落库；**A2-2 不成立**（证据见下）。

- **A2-1（第四条路：自造到达目录当钥匙）**：**接受，这是本轮最有价值的一条**。
  判据改成 **第 3 条（`A.source_ids == {<id>}`）∧ 第 4 条（`<id>` 在 head 树里没有 entry）**（= 四条实测路里的**丁**）。
  依据与四路对照表写进 `design.md §2 D1`；代价（N-m：部分搬移 + 未配上的文件仍要事件）写进 §3 N-l/§4 R6。
  ⚠️ 你同时实测出**误伤面 ≈ 0**（P9/P10：按 #29 次序的正当归档里根本没有 `D`+`A` 对，判据③④压根不被求值）
  —— 这条我采纳并写进了 §2 D1：它让「第 4 条」成为一个**几乎零代价**的收紧。
- **A2-2（`grill-design.md:204-205` 假话未更正）**：**成立 —— 我上一轮的「不成立」裁定是错的**（A3 复核）。
  我引的 `:198` 是**另一处**更正（G1 那句）；你指的 `:204-205`（G4 那行）当时**确实原样未动**。
  **现已改**：G4 那行重写成「本条已两次修订；本次真的改了：G4 = 不修，落点是 §4 R5 + tasks 3.3」。
  ⇒ 这是本 change 里**第三次**「作者自述与事实不符」，而且**是我误判了审阅者**——记在这里。
- **A2-3（A1-6 未落）**：**成立**，已落 —— spec 的 `<sub>` 为空那条 Scenario 现在**明写**它只能由
  **纯函数级**用例钉住（端到端构造不出来）。
- **A2-4（spec 的理由与 `== {<id>}` 不符）**：已改（`A.source_ids` 里是**另一个** change 的 id）。
- **A2-5（tasks 1.1 计数过期）**：已改成 N-a…N-m（并补了「`<sub>` 为空只能纯函数级」的说明）。
- **A2-6（缺 N-c/N-g 的 Scenario）**：已补两条（删整个 change 目录且无到达、重建既有 manifest）。
  尾斜杠那条并进了「`<sub>` 为空 / 尾斜杠 ⇒ 不配对」的纯函数级 Scenario。

### 你的 Open Question（QQ-A2-1：门禁对「蓄意伪造」的立场）

**没有停轮**，但把它**明写成立场**而不是抹掉：`design.md §6` 现在写明——
本仓门禁的既定边界是「**防漂移，不防伪造**」（真锚是远端 branch protection + required check），
本 change **沿用它**：把三轮实测出的四条绕过逐条钉成否定面（N-d/N-j/N-k/N-l），
但**不**承诺「任何伪造都挡得住」。**要改成防伪造，动的是整个 capability 的边界（另一个 change）**，
不是本 change 的一行判据。这条留给你复核。

**下一轮（A3）**：树已冻结。请优先攻**(丁)** 的绕过与误伤，以及「第 4 条是否真的必要/是否还有第五条路」。
