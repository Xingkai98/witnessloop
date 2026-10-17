# 对抗审阅（A3 轮，独立零记忆）

## Reviewer

- **身份**：独立零记忆对抗者（A3 轮）。未参与本 change 的立项 / grill / A1 / A2。本对话**不携带**任何历史：
  文档里的「实测」「已落库」「已收敛」一律当**待验证断言**，凡可复算的一律复算。
- **工作区**：`/home/happy/wl-wt/archive-arrival-recognition`（git worktree），
  分支 `archive-arrival-d-side/2026-10-17`。
  **`git rev-parse HEAD` = `5af3e6f2c74514941d4f214317ec8bfe82a0378c`**
  （`git show --stat` ⇒ 单 commit 落 A2：`design.md` / `proposal.md` / `spec.md` / `tasks.md` +
  新文件 `reviews/grill-adversarial-a2.md`，共 515 insertions / 36 deletions）。
- **读了什么**：`proposal.md` / `design.md` / `tasks.md` / `specs/archive-awareness/spec.md` /
  `reviews/{grill-design.md,grill-adversarial-a1.md,grill-adversarial-a2.md}` 全文；
  `src/witnessloop/{contract.py,checkcmd.py,gitutil.py,paths.py,policy.py,constants.py}` 的相关段。
- **跑了什么**（实验**全部**在 `/tmp/a31c/`；代码根用 `git archive HEAD | tar -x -C …` 建——
  本仓是 worktree、`.git` 是指针文件，**不**能 `cp -a`）：

  | # | 命令 / 构造 | 结果 |
  |---|---|---|
  | 1 | `/tmp/a31c`（= HEAD 原样）：`PYTHONPATH=src python3 -m pytest -q` | **`702 passed in 176.67s`**（与称述的基线一致） |
  | 2 | `/tmp/a31c/p_ding` = 按 `design.md §2 D1` **逐字**转写 `d_move_halves`（四条第 1/2/3/4 条；第 4 条用 `view.entry(head_rev, f"{root}/{id}") is None`）+ 接线 `checkcmd._protected_move_exempt` 的 D 侧 | 见 `## 对抗结论` |
  | 3 | 同一原型加 `A3_MODE` 开关：`ding` = 四条 / `bing` = 「丙」（无第 4 条）/ `only4` = 无第 3 条 | 用于第 3/4 条的**必要性**复算 |
  | 4 | 真 git 端到端探针 **P0/P1/P7/P8/P9/P11/PFIVE/H/I/J/K/L/S8**（`p_ding/tests/test_a3_probe.py`：真仓 + 把 CLI 当子进程跑、按 `PYTHONPATH` 切代码根） | 见下，逐条附**原始输出** |
  | 5 | 纯函数面探针 M/N（`<sub>` 为空 / 尾斜杠 / `..` / archive 前缀 / A 记录形态 / `view.entry` 对 blob 的返回） | 见 §4 |
  | 6 | `p_ding` 全量回归：`PYTHONPATH=src python3 -m pytest -q --ignore=tests/test_a3_probe.py` | **`702 passed in 173.13s`** ⇒ 原型对既有 702 条**零回归** |

- **我**未**复算的**：issue #31 的原始测量（`8e5fc83b` / `d94c08334`，属接入方 asterwynd 的仓）、真 CI / GitHub Actions、
  接入方 asterwynd 的行为、`docs/gate.md` 的文案、实现本身（`tasks.md` 3.1–3.4 **全未勾**，仓库里**没有**
  `d_move_halves`——见「未验证项」）。我的原型是**我自己**按 §2 D1 逐字转写的，不是实现者的代码。
- **本仓写入**：**仅本文件**（新建）。`git diff --stat HEAD` 空 ⇒ 未改任何已跟踪文件；未 commit / 未 reset / 未 push。

---

## 对抗结论

### 0. 结论速览

| 面 | 结论 |
| --- | --- |
| 目标形态（issue #31 复现）修好了吗？ | **是**（P0：base `rc=1` 1 项 → 丁 `rc=0 通过 ✓`） |
| 判据（丁）**充分**吗？ | **不充分** —— **第五条路 PFIVE**：自造到达目录 + 一把钥匙 + **把该 change 的其余部分全删** ⇒ `check` **`rc=0 全绿`**，而那个 change 是被**销毁**的，不是被归档的（§2） |
| 第 3 条**真的必要**吗？ | **是**（复算 A1 的 S8 字面构造：`R055` 跨配对实测复现；去掉第 3 条 ⇒ 目标 finding 被洗白） |
| 第 4 条**真的必要**吗？ | **只对 A2 那一个实例必要**：去掉它 P7 确实复漏（`rc=0`）；但 PFIVE 一步变体同时绕过丙与丁 ⇒ 第 4 条挡的是**实例**不是**机制**（与 A2 自己诊断的「丙 只挡 S2 的实例」同型） |
| 其余候选第五条路（目录→文件 / 符号链接 / 改名成别的 active id / `archive/**` / `archive/<id>` / `..` 穿越） | **全部 fail-closed**（逐条实测，§4） |
| 误伤（N-m 那类）在真实流程多常见？ | **今天不可能新增红**（单调性：丁 只把 `D` 记录的判定从 `False` 改成 `True` ⇒ findings 集合只减不增；跨 12 个探针 **ding ≤ base 一次不例外**）。N-m 的真实形态要求「部分搬移 + 源 change 仍在 head」，而 `#29` 次序的正当归档**一条 `D` 都没有**（P9 复算）⇒ 判据 3/4 压根不被求值 |
| A2-1 / A2-3…A2-6 按 artifact 落库了吗？ | A2-1 ✓（但**其结论已被本轮证伪**）／ A2-3 ✓ ／ A2-4 ✓ ／ A2-5 ✓ ／ A2-6 ✓（N-c/N-g Scenario 已补；尾斜杠在 spec 与 tasks 2.3 有，design 的算法段只以「`<sub>` 为空」表述） |
| **A2-2 的「不成立」裁定成立吗？** | **不成立** —— 处置引的 `grill-design.md:198` 是 **A1-1** 那句的更正，**不是** G4 那句；G4 那句（`:204-205`）**原样未改**，与 `tasks.md:39-44` / `design.md:157` 直接矛盾（§6） |
| §6「停轮问题（无）」诚实吗？ | **部分**：立场问题（防伪造 vs 防漂移）确实只有用户能拍 ⇒ 已写进 Open Questions；但「丁 挡住 P7」是**本 change 自己的承诺**，它的依据已被证伪，**不能**用「不防伪造」这条边界句抵掉（§8） |
| **收敛** | **不收敛**（两条判据**都**不满足） |

---

### 1. 目标形态复算成立（P0），原型与 A2 的数字逐条吻合

**P0**（issue #31 形态）：main 上 `add-retry` 是完整、有证据的 active change；feature 上 `git mv` 整目录进
`openspec/changes/archive/2026-10-14-add-retry/`，并把它的 `workflow-events.jsonl` 重写成新内容（⇒ 1 条 `D` + 10 条 `R100`）。原始输出：

```
--- base ---   rc=1   12 个变更文件，1 个 change 目录   1 项
  1. openspec/changes/add-retry/workflow-events.jsonl：受保护路径被写入，但没有结构化解释事件
--- 丁 ---     rc=0   check：通过 ✓
D_RECORDS ['openspec/changes/add-retry/workflow-events.jsonl']      ← 唯一一条 D
```

**P7 复算（A2-1 的字面构造）**：`--- base rc=1（1 项）--- 丙 rc=0 通过 ✓ --- 丁 rc=1（1 项）`。
⇒ 我的 `bing`（丙）与 A2 报告的数字**逐条吻合** ⇒ 我的原型是 `D1` 的忠实转写，可以拿它攻判据本身。

---

### 2. **A3-1（核心 · 新证伪）**：第五条路 —— 自造到达目录 + 钥匙 + **把源 change 的其余部分全删**

#### 2.1 构造（PFIVE，真 git 端到端，`rc=0 全绿`）

`p_ding/tests/test_a3_probe.py::test_G_PFIVE_fake_arrival_key_whole_b_gone`。main 上两个完整、有证据的
active change：`add-retry`(a)、`another-change`(b)。feature 上：

```
① 造一个**全新的**到达目录 A := openspec/changes/archive/2026-10-15-fake/
   · proposal/design/tasks.md + specs/a3u/spec.md + reviews/*.md + workflow-events.jsonl
     **全是新增文件**（内容唯一，避开到达判据 5 的「白捡」判定）⇒ 过判据 1/2/3/5
   · git mv changes/another-change/notes.md A/notes.md        # **钥匙**：唯一一条把 b 带进 source_ids 的记录
   提交（这些成为 diff 里的 A 记录）
② manifest build 给 A 造三份 stage manifest，**提交进树**
   （⇒ A/reviews/*.manifest.json 也成为 diff 里的 A 记录；这一步 A2 的 P13 已经做过，成本 0）
③ rm -rf openspec/changes/another-change/     # **把 b 的其余部分全删**，含它的 4 个受保护文件
   提交
④ manifest build 重绑 A 的 head_sha（不提交）
```

diff（原始输出，节选）：

```
D	openspec/changes/another-change/reviews/building.manifest.json
D	openspec/changes/another-change/reviews/grill-adversarial.manifest.json
D	openspec/changes/another-change/reviews/grill.manifest.json
D	openspec/changes/another-change/workflow-events.jsonl
A	openspec/changes/archive/2026-10-15-fake/reviews/building.manifest.json
A	openspec/changes/archive/2026-10-15-fake/reviews/grill-adversarial.manifest.json
A	openspec/changes/archive/2026-10-15-fake/reviews/grill.manifest.json
A	openspec/changes/archive/2026-10-15-fake/workflow-events.jsonl
R100	openspec/changes/another-change/notes.md	openspec/changes/archive/2026-10-15-fake/notes.md
```

纯函数侧（用**未改**的 base 代码根跑 `contract.archive_arrivals`）：

```
ARRIVAL 2026-10-15-fake | source_ids = ['another-change']
D_HALVES [ ... b 的 design.md / proposal.md / reviews/building-review.md / reviews/building.manifest.json /
             reviews/grill-adversarial.{md,manifest.json} / reviews/grill.manifest.json / tasks.md /
             workflow-events.jsonl ]          ← 四条判据**全部**满足
HEAD_IDS []                                    ← 没有幽灵 id，check 一声不吭
```

`check` 原始输出：

```
--- base ---  rc=1   22 个变更文件，1 个 change 目录
  1. openspec/changes/another-change/reviews/building.manifest.json：受保护路径被写入…
  2. openspec/changes/another-change/reviews/grill-adversarial.manifest.json：…
  3. openspec/changes/another-change/reviews/grill.manifest.json：…
  4. openspec/changes/another-change/workflow-events.jsonl：…
--- 丙 ---    rc=0   check：通过 ✓        ← 丙 也漏（第 4 条在这条路上不起作用）
--- 丁 ---    rc=0   check：通过 ✓        ← 本 change 的判据全绿
  [reviews/grill.manifest.json]             base=True  丙=False  丁=False
  [reviews/grill-adversarial.manifest.json] base=True  丙=False  丁=False
  [reviews/building.manifest.json]          base=True  丙=False  丁=False
  [workflow-events.jsonl]                   base=True  丙=False  丁=False
```

#### 2.2 为什么这是**新的**证伪，不是 N-l 的重复

N-l / design.md:65/72 / spec.md:106-112 的论证是**逐字**依赖第 4 条的：

> 「**第 4 条**不满足（`<id>` 仍在 head 里）」（`design.md:141`）

PFIVE 把「仍在 head 里」这半句**去掉**——攻击者本来就要把 `<id>` 的受保护文件**删掉**，
只要顺手把该 change 目录其余部分也删掉，第 4 条就**从阻塞条件变成自动满足的条件**：

| 判据 | P7（A2 的实例） | PFIVE（一步变体） |
|---|---|---|
| ① `D` 形如 `<root>/<id>/<sub>`、不在 `archive/**` | ✓ | ✓ |
| ② 同 diff 有一条路径逐字等于 `f"{A.directory}/{<sub>}"` 的 `A` 记录 | ✓（攻击者造的 `notes.md`） | ✓（同上；受保护文件的同子路径 A 记录由「到达目录本来就必须有必需件 + manifest」**免费**给出） |
| ③ `A.source_ids == {<id>}` | ✓ | ✓（同一把钥匙） |
| ④ `<root>/<id>` 在 head 里没有 entry | **✗**（b 还活着） | **✓**（b 被整个删掉） |

⇒ **第 4 条挡住的是「攻击者偷懒」这一个实例，不是「自造到达目录当钥匙」这个机制。**
这与 A2 对自己的诊断（「丙 只挡住 S2 的**一个实例**，机制未挡住」，`grill-adversarial-a2.md:127-132`）
是**同一个错误换了一层**：每一轮都在把上一轮的**实例**钉成否定面，而机制原封不动。

#### 2.3 「不防伪造」这条边界句能不能抵掉它？**不能**

两条理由，都可复算：

1. **本 change 自己承诺了这条**。`design.md:65`「**丁（取）**：第 3 条 ∧ 第 4 条 ⇒ S2 ✓ / S8 ✓ / **P7 ✓** 全部挡住」、
   `:72` 对照表的 **丁/P7 列 = ✓**、`spec.md:43`「**只有**第 3 条 ∧ 第 4 条一起挡住 ②③④」——
   这三句在 PFIVE 下为**假**（与 A2 证伪「丙/S2 = ✓」时是同一类断言）。
2. **文档里没有这条路**。`design.md §2 D1` 的「两条已知残留」只列 纯 `D`+`A` 与 跨配对；`§3` 的
   13 张否定面（N-a…N-m）里没有「源 change 被整个删掉 + 自造到达目录」；`§4 R1–R6` 也没有。
   → 「如实登记」这一半**也**没做。

#### 2.4 对照（证明这不是「任何构造都判绿」）

| 探针 | 构造 | base | 丁 |
|---|---|---|---|
| **P8** | 同 PFIVE 但**不搬**钥匙（`source_ids` 空） | rc=1，b 的 finding 在 | **rc=1，b 的 finding 在** ✓ |
| **P11** | 删掉**整个** b + 别处一次**正当**归档（A1 的 S8 / grill 的 G1 原文） | rc=1（8 项） | **rc=1（7 项，全在）** ✓ |
| **P1** | A1 的 S2：把仍活着的 b 的一个文件搬进**真**到达目录，再删 b 的受保护文件 | rc=1（2 项） | **rc=1（2 项）** ✓ |
| **L** | 「到达目录名恰好等于 `<id>`」（`archive/another-change`）的 PFIVE | rc=1（4 项） | **rc=1（3 项）** ← 同一个洞的弱形态（-1） |

---

### 3. 第 3 条 / 第 4 条的**必要性**（逐条复算，不是引用）

**第 4 条**：去掉它（`A3_MODE=bing` = 「丙」）⇒ P7 **`rc=0 通过 ✓`**（§1）。
⇒ 对 A2 实测出的那个**实例**，第 4 条**是必要的**。但 §2 的 PFIVE 表明：**同一机制**换一步就同时绕过丙与丁
⇒ 第 4 条是**充分性不足**的补丁，不是「机制级」修复。

**第 3 条**：去掉它（`A3_MODE=only4`，只留 1/2/4）⇒ 复算 A1 的 S8 **字面构造**
（删整个 `another-change` + 在到达目录里**重建三份 manifest 并提交**）。原始输出（节选）：

```
D	D	openspec/changes/another-change/reviews/building.manifest.json
R055	openspec/changes/another-change/reviews/grill.manifest.json
     →	openspec/changes/archive/2026-10-14-add-retry/reviews/grill.manifest.json
ARRIVAL 2026-10-14-add-retry | source_ids = ['add-retry', 'another-change']
  >>> base:  rc=1 5 项 | b 的事件文件红=True
  >>> only4: rc=1 3 项 | b 的事件文件红=False   ← 第 3 条一去，目标 finding 立刻被洗白
  >>> 丁:    rc=1 5 项 | b 的事件文件红=True    ← 第 3 条把它挡住
```

⇒ **第 3 条是必要的**（`R055` 这个跨 change 相似度配对是 **git 自己**给出的，不是攻击者选的路径，
与 A1 §2.2 的原文一致——我**逐字复现**了它）。同结论也在更简的构造上重复了一次
（P11：`only4` 下 b 的事件文件 `红=False`）。

⚠️ 顺带一条**先于本 change** 的观察（**不计入**本 change 的必须修改项）：那条 `R055`
让 b 的 `reviews/grill.manifest.json` 走**既有**的 `R`/`C` 豁免路径 ⇒ 在 **base** 就已 `红=False`
（`… 红=False` 那一栏 base 与 丁 相同）。这是 `R`/`C` 侧的既有边界，本 change 声明不动它（`design.md:177`）。

---

### 4. 其余候选第五条路：逐条实测（`test_H` … `test_N`）

| 候选 | 构造 | 结果（原始） | 判定 |
|---|---|---|---|
| **目录变文件** | `rm -rf changes/b` 后写一个**文件** `changes/b`（内容随意），再删受保护文件 | `D_HALVES []`；`base rc=1（9 项）` = `丁 rc=1（9 项）` | **fail-closed ✓**（`view.entry` 对 blob 返回 `('blob', …)` ⇒ 第 4 条判「还在」） |
| **符号链接** | `rm -rf changes/b` 后 `ln -s archive/<name> changes/b` | `D_HALVES []`；`base 9 项` = `丁 9 项` | **fail-closed ✓**（同上，symlink 也是 blob） |
| **改名成另一个 active id** | `git mv changes/b changes/another-change-v2` 后删 `-v2` 的受保护文件 | `base rc=1（13 项）` → `丁 rc=1（12 项）` | **fail-closed ✓**（D 的 `<id>` = `-v2`，仍在 head） |
| **`archive/**` 下（`<id>` == `archive`）** | 在 main 上先造 `archive/old/`，feature 里删它的 `workflow-events.jsonl` | `base 1 项` = `丁 1 项`（都不豁免） | **✓ 第 1 条挡住了** |
| **`archive/<name>` 与 `<id>` 同名** | 见 §2.4 的 **L** | `base 4 → 丁 3` | **同一个洞的弱形态**（不是「同名」带来的新问题） |
| **`<sub>` 穿越 `..`** | 纯函数：`changes/b/../c/x.jsonl` | `-> []` | **✓**（无逐字相同的 A 记录；git 也不产这种名字） |
| **`<sub>` 为空 / 尾斜杠** | 纯函数：`changes/b` 与 `changes/b/` | `-> []`（两者） | **✓**（`normalize` 不去尾斜杠 ⇒ 拆出空 `sub`） |
| **A 记录形态** | 纯函数：A 侧是 `R100` / `M` / 子路径不同 / 别的到达目录 | `-> []`（全部） | **✓**（只认 `status[:1]=="A"` 且逐字相同） |
| **第 3 条边界** | 纯函数：`source_ids` = `{b}` / `{b,c}` / `{c}` / 空 | `-> [D]` 只在前者 | **✓** |
| **第 4 条谓词** | 纯函数：`view.entry` 对 `tree` / `blob` / 不存在 | `('tree')` / `('blob')` / `None` | **✓**（只有 `None` 才算「离开」⇒ 方向安全） |

⇒ **我没有找到 PFIVE 之外的第二条新路**。上述 9 条里没有一条能拿到豁免。

---

### 5. 误伤面：`N-m` 在真实接入方流程里多常见？（可复算的判断，不穷尽）

**结论：本 change 在红/绿的**计数**上只减不增，因此不存在「新增红」意义上的误伤。**

1. **单调性（代码层论据 + 实测）**：`_archive_move_exempt` 只对 `D` 记录（`old_path` 为空）从 `False`
   变成 `∈ d_halves`；`R`/`C` 那条路、`changed_change_ids`、到达判据**一个字符没动**（`design.md D2/D4`）。
   ⇒ `check` 的 findings 集合是**子集**关系。跨 12 个探针实测（base→丁 的项数）：
   `1→0`（P0）、`8→7`（P11）、`2→2`（P1）、`1→1`（P7/P8）、`9→9`（H/J）、`13→12`（I）、`4→3`（L）、
   `5→5`（S8）、`4→0`（PFIVE）—— **没有一次 `丁 > base`**。
2. **N-m 的形态在正当流程里构造不出来（复算）**：`#29` 次序的**正当**归档 = 纯 `git mv` ⇒ 我的 P9 实测
   `D_RECORDS []`（与 A2 的 P9 一致）⇒ 判据 3/4 **压根不被求值**。
   而 `N-m` 要求「部分搬移 + 源 change **仍在 head**」：把一个 change 的**一部分**搬进一个**新的**到达目录，
   会让源 change 缺必需件（它自己的契约红就在那儿）——不是任何文档化流程产出的形态。
   ⇒ 我的判断：**发生率 ≈ 0**，且即使发生，代价也只是「维持改动前的红」，不是新红。
   （**未验证**：真实接入方的 diff 语料——见「未验证项」。）
3. **唯一真实的代价是「解不开」而不是「多报」**：`R2/R6` 登记的「跨配对 ⇒ 正当搬移的 `D` 失去豁免」
   在 P1 里实测到（`丁 2 项`，与 base 同），但**不new红**。

---

### 6. A2-1…A2-6 逐条按 **artifact** 核（`git show --stat 5af3e6f` + 文件实体）

| 项 | 处置称 | 实体核 | 判 |
|---|---|---|---|
| A2-1（第四条路 P7） | 接受，加第 4 条 | `design.md:39-50`（第 4 条）／`:55-65`（四路对照）／`:67-72`（表）／`§3 N-l`(`:141`)／`N-m`(`:142`)／`spec.md:106-112`（P7 Scenario）／`spec.md:114-118`（N-m Scenario）／`proposal.md:40-51`（四条） | **已落库 ✓**（但**结论**已被 §2 证伪） |
| A2-2（`grill-design.md:204-205` 假话） | **不成立**（更正已在 `:198`） | `grep -n`：`:198` 是 **G1** 那句（「我说的『新的第 3 条下不成立』**已作废**」）的更正；`:204-205` 的 **G4** 行**原样未改**：「本 change 会**收掉它**…（tasks 3.3 已写明）」 | **处置裁定不成立 ✗**（见下） |
| A2-3（A1-6 未落） | 已落 | `spec.md:92-94` 明写「**纯函数级**钉子」；`grep -c 纯函数` = **2**；`tasks.md:33` 有「`<sub>` 为空与尾斜杠（**纯函数级**）」 | **已落库 ✓** |
| A2-4（spec 的理由与 `==` 不符） | 已改 | `spec.md:65`：「（**第 3 条**不满足：`A.source_ids` 里是**另一个** change 的 id）」 | **已落库 ✓** |
| A2-5（tasks 1.1 计数过期） | 已改成 N-a…N-m | `tasks.md:21` = 「N-a…N-m」；`design.md` 的 `^| N-` = **13**；`proposal.md:61` = 「十三条」 | **已落库 ✓** |
| A2-6（缺 N-c/N-g Scenario + 尾斜杠） | 已补 + 并进纯函数级 Scenario | N-c = `spec.md:67-70` ✓；N-g = `spec.md:72-75` ✓；尾斜杠 = `spec.md:92-94` + `tasks.md:33` ✓（`design.md:88` 的算法段仍只以「**`<sub>` 为空**（记录正好是目录本身）」表述——语义覆盖了尾斜杠，但没点名该输入；**nit，不计必须项**） | **已落库 ✓** |

#### A2-2 的复核（我按要求专门复核了这个反驳）——**反驳不成立**

- 处置写的「更正已经在 `grill-design.md:198`」——`:198` 的原文是
  `⇒ ❌ **这句是错的，已作废**（对抗轮 A1 的 S2 实测…）`，紧跟在 `:196-197` 被划掉的
  「『新的第 3 条』下不成立」之后。那句属于 **A1-1**（它要求「删掉 `reviews/grill-design.md:196-198` 里被证伪的断言」），
  **不是** A2-2 说的 G4 行。
- A2-2 指的那一行**今天仍在**（`grill-design.md:204-205`）：
  「**G4**：接受——`changed_change_ids:381-383` 是死代码，本 change 会**收掉它**并把那条空钉子测试一并订正（tasks 3.3 已写明）。」
  而 `tasks.md:42-44` 写「**`changed_change_ids` 不动**…`:381-383` 的死分支也**不**顺手动…登记为 §4 R5」，
  `design.md:157`（§4 R5）写「**本 change 不动它**」。
  ⇒ **三处互相矛盾**，且那句「（tasks 3.3 已写明）」引的是一句**不存在于 tasks 3.3 的话**
  （A1-3 早已判定它不可实现：零 `R` ⇒ `d_move_halves` 必为空 ⇒ 那条「幽灵 id 已消除」的断言必假）。
- ⇒ **A2-2 成立**（= A1-3 的第二半未落库）。处置不是「看错了它是不是假话」，而是**引错了行**：
  `:198` 修的是另一句。

---

### 7. 规格可测性（`specs/archive-awareness/spec.md`，13 条 Scenario）

- **端到端可测（12 条）**：S1↔P0、N-d↔P11、N-c、N-g、N-a、N-b、N-e、S2↔P1、P7↔P7、N-m、S8↔S8、N-i。
  我实测了其中 **7** 条（P0/P11/N-c 形态/N-g 形态/N-a 形态/P1/P7/S8）。
- **只能纯函数级（1 条）**：`<sub>` 为空 / 尾斜杠（`spec.md:92-97`）。A2-3 的「加注」已落（`:93`），
  但该 Scenario 的 `When` **仍写**「运行 `check`」（`:96`）——按 A2-3 给的二选一它算过关，
  只是规格文字本身仍不可执行。**nit，不计必须项。**
- **缺 Scenario（1 条）**：`design.md §3` 的 **N-h**（归档目录缺必需件 / 内容来源存疑 / **是符号链接**）
  在 spec 里**没有**任何 Scenario（`grep 符号链接 specs/…/spec.md` ⇒ 0）。
  而 `proposal.md:63` 写「十三条否定面**逐条见 `specs/` 的 Scenario**」⇒ 该句对 N-h 为假。见 **A3-4**。
- **tasks.md 漏项 / 写不出来的项**：`2.4` 的清单（「相对子路径逐字相等、前缀边界、大小写与 `./` 归一化」）
  **没写尾斜杠**（`2.3` 里写了）；其余（2.1/2.2/2.3/3.x/4.x）都可写、能落地。
  另：`3.1` 要求用 `view.entry(head_rev, …)`，而 `design.md:102` 的签名 `(changes, policy, arrivals)`
  **传不进** view/head_rev ⇒ 见 **A3-3**。

---

### 8. §6「停轮问题（无）」的诚实性

- **Q1 / Q1′ 两行**：把替代路的代价写在同一行，**形式上是诚实的**；但 **Q1′ 的定案依据**
  （`design.md:65`、`:72` 的「丁 是唯一同时挡住 S2/S8/P7 的」）**已被 §2 证伪** ⇒ 依据句要改。
- **`design.md §6`「要不要让 `R`/`C` 也要求源目录消失？」**：**成立**——`R`/`C` 是 git 逐文件配对，
  改它超出本 issue，且 P1/S8 实测到它的既有形态（b 的 manifest 在 base 就 `红=False`），与本 change 无关。
- **「相对子路径要不要允许同 basename」「要不要把 `D`+`A` 喂给 `sources`」「事件文件之外的受保护文件」**：
  三行均与代码实体一致（我读了 `contract.py:274-280` 的 `moved_content`、`:314-320` 的 `sources`、
  `checkcmd.py:346-356` 的两档规则）⇒ **成立**。
- **有没有真只有用户能拍的？有** ⇒ 见 `## Open Questions` 的 **OQ-A3-1**。
  ⚠️ 但**要说清**：`design.md:155` / `spec.md:46` 的「防漂移、不防伪造」是**能力边界**；
  而 §2 证伪的是**本 change 自己写下的**「丁 挡住 P7」这句**承诺**。**边界句不能用来抵掉自己对某条路的承诺**
  ——否则 §3 的 13 张否定面全部可以一句话作废（它们同样是「蓄意构造」）。这两件事必须分开处理。

---

## 未验证项

1. **issue #31 的原始测量**：`design.md §1` 引的 `8e5fc83b` / `d94c08334`、「34 个变更文件」、「只有一条 `D`」
   —— 那两个 sha 属接入方 asterwynd 的仓，本工作区取不到 ⇒ **未验证**。我复算的是**形态**
   （P0：12 个变更文件 / 1 项红 → 0 项）。
   （**不**计为必须修改项——文档只把它当背景，未写成「已验证」。）
2. **真 CI / GitHub Actions**、**接入方 asterwynd 的行为**：**未验证**。
3. **`grill` 的 `✗9 → ✗3`**：**未逐字重跑**（我不知道它那条 diff 的确切构造）。我复算的是同族的
   `P11`（删整个 `b` + 正当归档：base 8 项 → `only4` 6 项）与 `S8`（base 5 项 → `only4` 3 项）。
4. **实现尚不存在**：`tasks.md 3.1–3.4` 全未勾，`grep -rn d_move_halves src/` ⇒ **0 命中**
   ⇒ 本轮的结论对「按 `design.md §2 D1` 这么实现」成立。若实现者额外加守卫（或另换锚），**A3-1 必须重跑**。
5. **`d_move_halves` 的签名**：`design.md:102` 写 `(changes, policy, arrivals)`，第 4 条需要 view + head_rev
   ⇒ 我按**判据**（而不是按那行签名）实现：`d_move_halves(changes, policy, arrivals, view, head_rev)`。
   实现者会撞上同一处不一致（A3-3）。
6. **`N-h`（symlink / gitlink 的到达目录）**：我只跑了 H/J 两个「`<id>` 侧是 symlink/blob」的探针
   （都 fail-closed），**没有**构造「到达目录本身是 symlink / 缺必需件」的端到端探针；spec 里也**没有**它的 Scenario。
7. **真实接入方的 diff 语料**（§5 的「N-m 发生率 ≈ 0」）：**未验证**——我给的是
   「正当归档一条 `D` 都没有」（P9 复算）+ 形态分析，不是频率统计。
8. **我未跑** `docs/gate.md` 的文案核对（tasks 3.4 是未来项，尚未落）。

---

## 必须修改项

### A3-1（**核心 · 新证伪**：第五条路 PFIVE —— 「自造到达目录 + 钥匙 + 把源 change 整个删掉」）

**事实**（真 git 端到端，附原始输出，见 §2）：第 4 条的前提（`<id>` 离开 head）与攻击目标
（删掉 `<id>` 的受保护文件）**天然同向**——攻击者只要把 `<id>` 的**其余部分也删掉**，第 4 条就自动满足。
结果：`check` **`rc=0 全绿`**（base `rc=1` 4 项），被删的是该 change 的**全部 4 个不变集受保护文件**
（事件文件 + 3 份 manifest），而到达目录里**只有 1 个文件**真的来自那个 change（钥匙），其余全是伪造内容。
`HEAD_IDS []`（无幽灵 id、无其它红）。丙（无第 4 条）也漏 ⇒ 第 4 条在这条路上**零作用**。

被本条**证伪**的实体（逐条 `文件:行号`）：

| 断言 | 位置 | 实测 |
|---|---|---|
| 「**丁（取）**：第 3 条 ∧ 第 4 条 ⇒ S2 ✓ / S8 ✓ / **P7 ✓** 全部挡住」 | `design.md:65` | **假**（PFIVE `rc=0 全绿`） |
| 四路对照表 丁 行 / **P7 列 = ✓** | `design.md:72` | **假**（同上） |
| 「**只有**「第 3 条 ∧ 第 4 条」一起挡住 ②③④」 | `spec.md:43` | **假**（同上） |
| 「第 4 条…把「**仍然活着**的 change 被人删掉一个受保护文件」与「整仓归档」区分开」 | `design.md:48-50` | **误导**：它区分的是「活着的 change」；对「change 被销毁」与「整仓归档」**区分不开** |
| `N-l` 的「**第 4 条**不满足（`<id>` 仍在 head 里）」 | `design.md:141` / `spec.md:112` | 只对**实例**为真；同一机制的 PFIVE 未登记 |
| 「两条已知残留」+ `§3`（13 张）+ `§4 R1–R6` | `design.md:90-98` / `:131-147` / `:149-158` | **未登记**：PFIVE 在文档里**无处出现** |

**必须（二者其一 + 三处登记）**：

- **① 加严判据**（候选方向，均**未**实测，只是方向）：
  - **(a) 到达目录必须**真的是这次搬移的容器**：要求 `<id>` 的**必需件级**文件在本次搬移里**成对**
    出现（即 `<A>` 里有来自 `<id>` 的 `R`/`C` 记录，覆盖 `required_artifacts` 的**全部**项）。
    P7/PFIVE 里 A 的必需件全**新增** ⇒ 被拒；issue #31 形态里 a 的必需件全是 `R100` ⇒ 仍放行。
    ⚠️ 会误伤「出生即归档」（F1 族）与「必需件被重写」的形态，**必须先跑**。
  - **(b) 要求「本次搬移覆盖 `<id>` 的**全部** diff 记录」**（即 `<id>` 的每条 `D` 都要有配得上的
    `A` 或 `R`）——PFIVE 里 b 有 9 条 `D` 而 A 里只配得上 6 条同类 ⇒ 可拒；但会把
    「部分搬移」整体推回红（与 N-m 同向，可接受）。
  - 二者都要**先实测**误伤面（尤其 F 组 18 条 + N 组 6 条），再定。
- **② 或如实登记 + 降级声明**：把 PFIVE 写进 `design.md §3`（新增一张否定面）＋ `§4 R`＋
  `spec.md`（新 Scenario）＋ `docs/gate.md §7 能力边界`，并**删掉/改写**上表里被证伪的 4 处措辞
  （`design.md:48-50`、`:65`、`:72`、`spec.md:43`）。

**现状不可接受**：`design.md:65/:72`、`spec.md:43` 现在**是假话**，而这条路在文档里**一处都没有**
—— 与 A2 当时对 P7 的判词（「现状不可接受」）同型。

### A3-2（A2-2 的「不成立」裁定**是错的**——引错行；A1-3 的第二半仍未落库）

**事实**（见 §6）：处置称「更正已经在 `grill-design.md:198`」，但 `:198` 是 **G1** 那句剰除线的更正；
A2-2 指的 **G4** 行（`grill-design.md:204-205`）**原样未改**，且与 `tasks.md:42-44`、`design.md:157`（§4 R5）
**三处互相矛盾**。

**必须**：把 `grill-design.md:204-205` 的 G4 行按 `tasks.md 3.3` / `design.md §4 R5` 的口径更正
（加删除线 + 「❌ 已作废：本 change **不动**那个死分支，见 tasks 3.3 / §4 R5」），
与同文件 `:196-200` 对另一句的更正手法一致；并把「A2-2 不成立」这个裁定本身更正掉。

### A3-3（低危：`design.md:102` 的签名表达不了第 4 条）

**事实**：`design.md:102` 写 `contract.d_move_halves(changes, policy, arrivals) -> frozenset[str]`，
而第 4 条（`design.md:48-50`）要求读 **head 树**；`tasks.md:39-40`（3.1）也要求
「用与 `changed_change_ids:391` **同一个谓词**：`view.entry(head_rev, f"{root}/{id}") is None`」
⇒ 签名必须带 `view` + `head_rev`。A1（`:231`）与 A2（未验证项 7）都提过这个参数问题，
但**这一轮它从「读不到用处」变成了「必须能读到」**，而 design 仍未改。

**必须**：把 `design.md:102` 的签名改成 `d_move_halves(changes, policy, arrivals, view, head_rev)`
（或如同 `changed_change_ids` 那样把 `view`/`head_rev` 显式列为参数）。

### A3-4（低危：`proposal.md:63` 的「逐条见 `specs/` 的 Scenario」对 **N-h** 为假）

**事实**：`design.md §3` 有 13 张否定面（N-a…N-m），`spec.md` 有 13 条 Scenario，但**不是一一对应**：
**N-h**（归档目录缺必需件 / 内容来源存疑 / **是符号链接**）**没有任何 Scenario**（`grep 符号链接` ⇒ 0）。
⇒ `proposal.md:61-63`「**十三条否定面**逐条仍红…**逐条见 `specs/` 的 Scenario**」对 N-h 为假。
（与 A2-6 对 N-c/N-g 的判词同类；**覆盖类**，**不计入**判据① 的「新证伪」。）

**必须**：补一条 N-h 的 Scenario（或显式写「N-h 由既有代码钉子 + `archive_arrivals` 判据 2/5 覆盖，不单列」）。

---

## Open Questions

### OQ-A3-1（**真只有用户能拍**）：本门禁对「蓄意伪造」的立场 —— 留「防漂移」还是留「挡 S2/P7/PFIVE」？

**事实（已复算）**：`spec.md:46` / `design.md:155`（§4 R3）声明本 capability
「**防漂移、不防蓄意伪造**（真锚是远端 branch protection + required check）」；
而 `design.md:55-72` / `spec.md:33-43` **以「挡住蓄意的 S2 / P7 / S8」作为选判据的理由**，
并把四条绕过（N-d/N-j/N-k/N-l）**钉成否定面**。这两件事只能二选一：

- **若留「防漂移」**（= 承认本判据挡不住蓄意者）⇒ **P7、PFIVE、G1 全都落在既有边界内**，
  正确处置是「登记 + 删掉『丁 挡住 P7』的措辞」（A3-1 的 ② 分支）；
  **而且 `甲`（`<id> ∈ sources`，最简、误伤最小）反而更诚实** ⇒ `design.md:67-72` 的四路对照表要重写
  （四路的差异只剩 S8 一格）。`docs/gate.md §7` 也要把「不防伪造」从角落的边界句提到 §2 D1 的正文。
- **若留「挡蓄意」** ⇒ 必须换锚，且候选（**(a)** 到达目录须含源 change 的**必需件级成对** `R`/`C` 记录、
  **(b)** 本次搬移须覆盖 `<id>` 的**全部** diff 记录、**(c)** 内容同一性锚）**都有登记过的代价**
  （(c) 会被 issue #31 的「被改写的文件」拒掉）。**三条我都未实测**（见未验证项 4）。

**为什么只有用户能拍**：这是**产品承诺**（门禁对谁负责、承诺到哪一档），不是代码细节；
且它决定本 change 的**验收口径**（`proposal.md` 的「十三条否定面」是否要加第 14 条、
S1 的正向承诺是否要收窄、要不要为它换锚）。

**我的推荐（不替用户选）**：先跑一次候选 (a) 的探针（成本 ≈ 1 个测试 + 一遍 F/N 组回归）；
若它同时满足「挡 PFIVE/P7」「放行 S1」「不破既有 702 条」，取 (a)；
否则走 A3-1 的 ② 分支（**登记** + 删声明），并把「不防蓄意伪造」提升到 `§2 D1` 的正文。
**在此之前**，至少要把 PFIVE 登记进 `§3`/`§4`、并删掉 `design.md:65/:72` 与 `spec.md:43` 的假话——
这一步**不需要**用户拍板。

---

## 收敛结论

**不收敛**（两条判据**都**不满足）。

- **判据 ①「本轮没有新的可证伪项」→ 不满足**。
  本轮新增**可复算**的证伪（真 git + 真 CLI 子进程，附原始输出，**不是**措辞/计数/格式）：
  **A3-1**——第五条路 PFIVE：**自造到达目录 + 一把钥匙 + 把源 change 的其余部分全删**
  ⇒ 四条判据同时满足、`check` **`rc=0 全绿`**（base `rc=1` 4 项），一次洗白该 change 的
  **全部 4 个不变集受保护文件**。它同时证伪了 `design.md:48-50` / `:65` / `:72` / `spec.md:43`
  四处**关于「丁 挡住 P7」**的断言，并揭示了第 4 条的**结构性缺陷**：
  它的前提（源 change 离开 head）与攻击目标（删掉该 change 的受保护文件）**天然同向**，
  攻击者只要多删一步就把它从阻塞条件变成满足条件。
  另有 **A3-2**（处置对 A2-2 的「不成立」裁定引错行，是一个新的可证伪断言且为假）。
- **判据 ②「已知必须修改项全部已落库」→ 不满足**。
  逐条按 **artifact** 核（`git show --stat 5af3e6f` + 文件实体）：
  A2-1 ✓／A2-3 ✓／A2-4 ✓／A2-5 ✓／A2-6 ✓（A2-2 除外，见下）；
  **A2-2 ✗**（= A1-3 的第二半）：`grill-design.md:204-205` 的 G4 行仍是「本 change 会**收掉它**…
  （tasks 3.3 已写明）」，与 `tasks.md:42-44`、`design.md:157` 矛盾 ⇒ 未更正；
  而处置的「A2-2 不成立」引的是**另一句**的更正行（`:198`）。

> 收敛要两条**都**满足（本轮**没有新的可证伪项** ∧ 已知必须修改项**全部按 artifact 落库**）。
> 当前停在 **A3-1**：它与 grill 的 G1、A1 的 A1-1、A2 的 A2-1 落在**同一根骨头**上——
> **判据把「git 自己的配对」当身份证明，而 git 的配对是全局的、且到达目录与源 change 都由被门禁的那一方掌握**。
> 四轮下来，每一轮都堵住了上一轮**实测出的那个实例**（`∈`→`==`、`==`→`== ∧ 源已离开`），
> 而**机制**一次没有被堵住：`∈`→`==` 换的是攻击者造哪个目录；`==`→`== ∧ 源已离开` 换的是
> 「删一个文件」→「删整个 change」。⇒ 下一轮（A4）的**真问题**是 OQ-A3-1 那个立场，
> 或者在「挡蓄意」这一档上换一个**内容级/必需件级**的锚（A3-1 ①(a)/(b) 先实测误伤面）。
