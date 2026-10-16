# 对抗审阅（A1 轮，独立零记忆）

## Reviewer

- **身份**：独立零记忆对抗者（A1 轮）。未参与本 change 的立项/grill/设计写作。
- **工作区**：`/home/happy/wl-wt/archive-arrival-recognition`（git worktree），
  `HEAD = f82595e5321de46a8051d6c75b5aa1acaa3406cd`（`f82595e Merge pull request #36 …`）。
- **被审对象**：`openspec/changes/archive-arrival-d-side/` 下的
  `proposal.md`、`design.md`、`tasks.md`、`specs/archive-awareness/spec.md`、`reviews/grill-design.md`，
  以及实现面 `src/witnessloop/{contract.py,checkcmd.py,gitutil.py,paths.py}`、`docs/gate.md`、
  既有测试 `tests/test_archive_arrival.py`、`tests/test_archive_awareness.py`。
- **读了什么**：上述文件（原仓**只读**：Read/grep/sed，未写、未 commit、未 reset）。
- **跑了什么**：全部实验在 `/tmp/a31/`，用 `git archive HEAD | tar -x -C …` 建代码根
  （本仓是 **git worktree**，`.git` 是指针文件，故**不能** `cp -a`）：
  - `/tmp/a31/base` = 未改代码（对照）
  - `/tmp/a31/p2` = 未改 + `d_move_halves`（design §2 D1 的三条判据，逐字转写）
  - `/tmp/a31/p4` = p2 + 原第 4 条「源目录在 head 树里不存在」
  - `/tmp/a31/p5` = p2 但第 3 条改成「到达的 `source_ids` 恰为 `{<id>}`」
  - `/tmp/a31/repo` = p2 + `changed_change_ids` 里的无条件 merge（tasks 3.3 的转写）
  - `/tmp/a31/mut` = base + 删掉 `contract.changed_change_ids:381-383`（变异实验）
  - 探针：`/tmp/a31/repo/tests/test_a1_e2e.py`（真 git 仓 + 把 CLI 当子进程跑、
    按 `PYTHONPATH` 切换代码根）、`test_a1_pure.py`（FakeTree 纯函数）、`test_a1_need.py`（逐条必要性）。
- **我**未**复算的**：issue #31 的原始测量（`design.md` 引的 `8e5fc83b` / `d94c08334`）、真 CI 的运行、
  接入方 asterwynd 的行为。这些**不计入**必须修改项（见「未验证项」）。
- **本仓写入**：仅本文件 `reviews/grill-adversarial-a1.md`（新建）。**未**修改任何**已跟踪**文件：
  `git status --porcelain` 输出为 `?? openspec/changes/archive-arrival-d-side/`（本条 change 的整个目录
  在 HEAD 里**未被跟踪**——`git ls-files` 对它**无**输出、`git ls-tree HEAD openspec/changes/` 里**没有**它），
  且**无** 任何 ` M`（已跟踪文件被改）条目 ⇒ 我确实只落了一个新文件。未 commit / 未 reset / 未 push。

---

## 对抗结论

### 0. 结论速览

| 面 | 结论 |
| --- | --- |
| 目标形态（issue #31 复现）修好了吗？ | **是**（S1：改前 `rc=1` 1 项 → 原型 `rc=0`） |
| 三条判据是**充分**的吗？ | **不是**——两条可复算的洗白构造（S2 蓄意钥匙、S8 **零钥匙**） |
| 三条判据**必要**吗？ | 逐条必要（c1/c2 对且不可去；c3 是 G1 的修法，去掉即复活） |
| 是「一份实现」吗？ | `d_move_halves` 是唯一判据实现 ✓，但 `changed_change_ids` 的 merge 是**第二处消费点**，且**有害** |
| `:381-383` 是死代码吗？ | **是**（变异存活，独立复现） |
| §6「无停轮问题」诚实吗？ | **不**——甲（=本次判据）的成本被低报，且存在**第四条路**（实测见 Open Questions） |
| G1–G6 按 artifact 落库了吗？ | **G1 部分 / G2 ✓ / G3 ✓ / G4 部分 ✗ / G5 ✗（spec 侧）/ G6 ✓** |
| **收敛** | **不收敛** |

---

### 1. 目标形态成立（S1，真 git 端到端）

构造：`add-retry` 是 base 上完整、有证据的 active change；head 上 `git mv` 整目录进
`openspec/changes/archive/2026-10-14-add-retry/`，其中 `workflow-events.jsonl` **重写**成全新内容
（⇒ git 报 `D` + `A` 而非 `R`）。命令：

```
PYTHONPATH=<code-root>/src python -m witnessloop check --root <repo> --base main --head HEAD
```

原始输出（`/tmp/a31/repo/tests/test_a1_e2e.py::test_S1_issue31_form`）：

```
--- 未改代码 ---        rc=1
  check：基线 main...HEAD，12 个变更文件，1 个 change 目录
  1. openspec/changes/add-retry/workflow-events.jsonl：受保护路径被写入，但没有结构化解释事件（…）
--- 原型D1(cond3) ---    rc=0
--- 原型D1+cond4 ---     rc=0
--- 原型D1+源集合=={id} --- rc=0
--- 原型D1(带merge/3.3) --- rc=0
```

⇒ **issue #31 的形态被修好了**，且三种加严候选都**不**回退它（`rc=0` 全保持）。**未验证**：与 issue #31
原始测量（12 文件 / 1 项）逐字一致——本工作区取不到 issue 原文，见「未验证项」。

---

### 2. **A1-1（核心）：判据不充分——两条可复算的洗白构造**

#### 2.1 构造 S2（蓄意钥匙）：**真 git 端到端，`check` 返回 `rc=0` 全绿**

在 S1 之上加两步（`test_a1_e2e.py::test_S2_attack_delete_b_events`）：

```python
git mv openspec/changes/another-change/notes.md \
       openspec/changes/archive/2026-10-14-add-retry/notes.md   # 钥匙：让 b ∈ A.source_ids
git rm -q openspec/changes/another-change/workflow-events.jsonl # 目标：删 active change 的受保护文件
```

diff（原始输出节选）：

```
R100  openspec/changes/another-change/notes.md  openspec/changes/archive/2026-10-14-add-retry/notes.md
D     openspec/changes/another-change/workflow-events.jsonl
```

`check` 结果（原始输出）：

```
--- 未改代码 ---        rc=1
  check：基线 main...HEAD，14 个变更文件，2 个 change 目录
  1. openspec/changes/add-retry/workflow-events.jsonl：受保护路径被写入，但没有结构化解释事件（…）
  2. openspec/changes/another-change/workflow-events.jsonl：受保护路径被写入，但没有结构化解释事件（…）
--- 原型D1(cond3) ---    rc=0
  check：基线 main...HEAD，14 个变更文件，2 个 change 目录      ← 一条 finding 都没有
```

⇒ **`another-change` 仍然活在 head 里、它的事件文件被删，而新判据判它「已解释」⇒ 全绿通过。**
这正是 grill 处置里被明确断言**不成立**的那条：
`reviews/grill-design.md:196-198`「⚠️ 你说的『去掉第 4 条后「`b` 仍在 head 时删它的文件」直接 EXIT=0 全绿』
在**新的第 3 条**下**不成立**——那条攻击拿不到 `b ∈ A.source_ids`」。**实测：拿得到，且一行 `git mv` 就够。**

#### 2.2 构造 S8（**零钥匙**，git 自己的跨 change 相似度配对）：部分洗白

`test_a1_e2e.py::test_S8_same_but_no_key_move`：**不**搬任何 b 的文件，只
`shutil.rmtree(openspec/changes/another-change)` + 在到达目录里重建三份 manifest（A 记录）。
git **自己**给出：

```
D     openspec/changes/another-change/workflow-events.jsonl
R055  openspec/changes/another-change/reviews/grill.manifest.json \
      openspec/changes/archive/2026-10-14-add-retry/reviews/grill.manifest.json
```

（`R055` = 55% 相似度配对，是 **git 的**输出，不是攻击者选的路径。）⇒ `A.source_ids ∋ another-change`。
`check`（原始输出）：

```
--- 未改代码 ---        rc=1  5 项
  1. …/add-retry/reviews/grill.manifest.json
  2. …/add-retry/workflow-events.jsonl
  3. …/another-change/reviews/building.manifest.json
  4. …/another-change/reviews/grill-adversarial.manifest.json
  5. …/another-change/workflow-events.jsonl        ← 洗白目标
--- 原型D1(cond3) ---    rc=1  3 项
  1. …/add-retry/reviews/grill.manifest.json
  2. …/another-change/reviews/building.manifest.json
  3. …/another-change/reviews/grill-adversarial.manifest.json
```

⇒ **第 5 项（删掉整个 active change 的证据文件）被洗白**，而**没有任何蓄意动作**——
删除一个 change 目录 + 重建 manifest 是**正常簿记**，却因 git 的跨 change 相似度配对而拿到身份锚。
（第 2 项被去掉是**预期的**修复。）

#### 2.3 被证伪的文档断言（逐条，带 `文件:行号`）

| 断言 | 位置 | 实测 |
| --- | --- | --- |
| 「删掉整个 `b` 的攻击拿不到 `b ∈ A.source_ids`（`A` 的源是别人）⇒ **堵死**」 | `design.md:64` | **假**（S2、S8） |
| N-d 行「**第 3 条**不满足：`b ∉ A.source_ids`」 | `design.md:115` | **假**（S2：`b ∈ A.source_ids`） |
| `spec.md:52`「（**第 3 条**不满足：`b ∉ A.source_ids`）」 | `specs/archive-awareness/spec.md:52` | **假**（同上） |
| §4 R3 把残留框成「防漂移、**不**防蓄意伪造」 | `design.md:127` 附近、`spec.md:37` | **不够**：S8 **不是**伪造，是意外（零蓄意）⇒ 该免责条款盖不住 |
| 处置「那条攻击拿不到 `b ∈ A.source_ids`」 | `reviews/grill-design.md:196-198` | **假**（同上） |

并且它**违反 issue #31 自身的诉求**：`tasks.md:29-31`（2.3 否定面）明写要「**单独**删 active change
的文件」仍红 —— S2/S8 里 `another-change` 就是活着的 active change，判据却放它过关。
`design.md:114` 的 N-c 行（「删掉整个 active change 目录」）同理被 S8 部分证伪。

---

### 3. 三条判据的**必要性**（逐条实测，`test_a1_need.py`）

| 去掉哪条 | 后果 | 原始结论 |
| --- | --- | --- |
| c3（`<id> ∈ A.source_ids`） | 整目录删 `b`（b 不在 head）**也被豁免** ⇒ G1 复活 | `assert _det_variant(..., c3=False) == {…/b/reviews/grill.manifest.json}` **通过** |
| c2（存在逐字同子路径的 `A` 记录） | 只要 `id ∈ source_ids`，**任意子路径**的 `D` 都免（不需要配得上的 `A`） | `f"{CHANGES}/b/design.md" in got` **通过** |
| c1（前缀 `〈changes_root〉/<id>/<sub>`、非 `archive/**`） | `openspec/specs/x.md` 这类**仓库级**路径也能配 | c1 关 ⇒ `openspec/changes/a/openspec/specs/x.md` 入列 |

⇒ **三条各自承重**（c1 的「非 `archive/**`」半条对 c3 冗余，前半条必要——去掉后仓库根路径被豁免；
这是**低危观察**，不是必须修改项）。

---

### 4. 误伤面（false-negative）实测

| 形态 | 实测 |
| --- | --- |
| 大小写不同（`Foo.md` vs `foo.md`） | **不配对**（`paths.normalize` 不做大小写折叠，`paths.py:13-24`）⇒ 该免却被拒 |
| 前导 `./` | **被吸收**（`normalize` 去前导 `./`）⇒ 不影响；**内部** `/./` 不是 git 的输出形态（我原先的构造无效，已改口径） |
| `<sub>` 为空 | 端到端**不可构造**（git 不为目录报 `D`）⇒ 只能纯函数测 |
| 纯 `D`+`A`（零 `R`，N-i） | **照旧红**（`source_ids` 空 ⇒ c3 不成立）——**与改动前同结论**，是如实登记的限制，不是新红 |
| **重写 + 有 R 兄弟**（`add-retry/reviews/grill.manifest.json` 被重写） | S1/S8 中该文件**仍红**（`A` 记录无 `A.source_ids` 锚，`R055` 只给 sibling 锚）⇒ **git 一旦不给该文件配对，判据依然拒绝**，这是**正确**的保守 |
| `<sub>` 含 `/`（深层子路径） | 逐字前缀比较，`sub` 保留 `/`，无边界问题（`test_a1_pure.py` 用 `reviews/grill.manifest.json` 覆盖） |

---

### 5. 「一份实现」与死分支

- **单实现 ✓（部分）**：判定逻辑只在 `contract.d_move_halves`（`design.md:82` 的签名）。S1/S2/S8
  的绿/红与纯函数探针 `d_move_halves` 的输出**一一对应**（`test_a1_pure.py::test_p1` 断言
  `f"{CHANGES}/b/reviews/grill.manifest.json" in det` **通过**）。
- **A1-2 的第二处消费点有害**：`contract.changed_change_ids` 里 tasks 3.3 的 merge
  （`design.md:87-88`、`tasks.md:38`）在 S2 下把 `b` 从 change 列表里**抹掉**：

  ```
  --- 原型D1(cond3) ---        check：…，14 个变更文件，2 个 change 目录
  --- 原型D1(带merge/3.3) ---   check：…，14 个变更文件，1 个 change 目录      ← b 消失
  ```
  ⇒ 仍然**活着**的 active change `b` **逃掉契约校验**（`accepted_change_ids` 不再含它）。
  该 merge 与 `changed_change_ids` 自己的 docstring 不变量（「源目录仍在 head 里 ⇒ 不排除」）冲突。
  纯函数佐证：`test_p2_ids_both_variants`（不 merge）`ids` 含 `b` ✓；`test_p4`（源目录已消失的正当部分搬移）
  ⇒ `d_move_halves == ` 空 且 `ids` 已由既有 `R` 兄弟排除 ⇒ **merge 在安全时是 no-op**。
- **`:381-383` 死代码 ✓（独立复现）**：变异（删掉该分支）后 `pytest -q` ⇒ **65 passed**，无测试失败。

---

### 6. G1–G6 落库审计（按 artifact，不按自述）

处置在 `reviews/grill-design.md:188-207`，声称「**G1–G6 全部已落库**」（`:190`）。逐条核对：

| 项 | 处置声称 | artifact 实测 | 判定 |
| --- | --- | --- | --- |
| **G1** | 判据已重写为身份锚；「那条攻击拿不到 `b ∈ A.source_ids`」 | 判据**确实**重写（`design.md:45`、`spec.md:21`）；但新判据**自己**引入新洞（§2），且 `design.md:64`/`:115`/`spec.md:52` 的旧理由**未随重写更新** | **部分落库 + 新增证伪** |
| **G2** | N-c 理由已改、补 N-d、补 spec Scenario | `design.md:114`（N-c 理由已改成「没有到达目录时」）、`:115`（N-d 行在）、`spec.md:48-57`（杀手 Scenario 在） | **✓ 落库**（但 N-d 行的理由见 A1-1） |
| **G3** | R1 指向 spec 里真实存在的 Scenario | `design.md:126`、`spec.md:74-78`（最后一条 Scenario） | **✓ 落库** |
| **G4** | 「本 change 会收掉它并**把那条空钉子测试一并订正**（tasks 3.3 已写明）」 | `tasks.md:38-39` 只写「把 `:381-383` 那个不可达的 `D` 分支收掉」，**没有**一个字要求订正测试；`tests/test_archive_arrival.py:300` 名字/注释**未改** | **✗ 未落库**（见 A1-3） |
| **G5** | 「已写进 **spec 的最后一条 Scenario** 与 §3 N-i」 | spec 最后一条 Scenario（`spec.md:74-78`）只讲 N-i 不被豁免；`grep -c "manifest\|别名\|与目录不符" specs/archive-awareness/spec.md` ⇒ **1**（即 `spec.md:60` 的路径名，**无**别名/绑定边界文字） | **✗ spec 侧未落库**（见 A1-4） |
| **G6** | spec 的加粗嵌套已修 | `spec.md:20` 现为 `**`f"{A.directory}/<sub>"`**（**相对子路径逐字相同**）`；坏嵌套模式 `grep '\*\*[^*]*\*\*[^*]*\*\*'` 无命中 | **✓ 落库** |

---

## 未验证项

1. **issue #31 的原始测量**：`design.md` §1 引的 `8e5fc83b` / `d94c08334`、以及 grill 的 `✗9 → ✗3`，
   本工作区取不到 issue 原文 ⇒ **未验证**。我**自己**的复现是 S1（12 文件 1 项 → 0 项）与 S8（5 项 → 3 项）。
   （它们**不**计为必须修改项——文档没把 issue 原文当已验证事实引用，只当背景。）
2. **真 CI**：本工作区**未**跑 GitHub Actions。`design.md`/`tasks.md` 的 CI 相关承诺**未验证**。
3. **接入方 asterwynd** 的行为**未验证**。
4. **N-h（symlink）**：既有钉子 `tests/test_archive_awareness.py:823`（F9）、`:855`（F10 gitlink）存在，
   但我**未**在本轮重跑并断言它们在新判据下仍绿（只跑了全量 `pytest -q`）。
5. **「大幅重写 ⇒ 无 R 兄弟」的统计面**：代码注释只论证「可能发生」（`design.md:127` R2），
   没有真实数据支撑发生率——**未验证**（不是必须修改项，是既有边界）。
6. `d_move_halves(…, view=None, head_rev=None)`（`design.md:82`）两个参数在 cond3 判据下**读不到用处**
   （cond4 的遗留）；我**未**验证实现时是否会真的传它们 ⇒ 属**签名冗余**观察。
7. **本仓工作区清洁度**：**已**核对。本文件写入后 `git status --porcelain` ⇒ `?? openspec/changes/archive-arrival-d-side/`
   （该 change 目录整体未跟踪），无 ` M` 条目 ⇒ 未改任何已跟踪文件（详见 `## Reviewer` 末条）。
8. **p5 的「源集合恰为 `{<id>}`」** 只跑了 `pytest -q`（702 passed）+ S1/S2/S8 三例；
   未跑 `test_a1_pure.py`/`test_a1_need.py` 全量 ⇒ 其误伤面（见 Open Questions）**未穷尽验证**。

---

## 必须修改项

### A1-1（判据不充分；**新证伪**，可复算）

**事实**：design §2 D1 的三条判据**不足**以堵住 issue #31 的诉求。两条真 git 构造：

- **S2**（蓄意钥匙，一行 `git mv`）：`another-change` 仍在 head、其 `workflow-events.jsonl` 被删，
  `check` **rc=0 全绿**（原始输出见 §2.1）。
- **S8**（**零蓄意**，git 自发 `R055` 跨 change 配对）：目标 finding 被洗白（5 项 → 3 项），见 §2.2。

**必须**（二选一，由用户拍板取舍，见 Open Questions）：

- ①**加严判据**（候选 乙/丙 已实测，见 Open Questions）；**或**
- ②**如实登记 + 补测试**：把「删掉整个 active change 的受保护文件，可被 git 的跨 change 相似度配对洗白」
  写进 `design.md §3`（新增一行）/`§4 R` + `spec.md`（新 Scenario）+ `docs/gate.md §7 能力边界`，
  并删掉 `design.md:64`、`:115`、`spec.md:52`、`reviews/grill-design.md:196-198` 里被证伪的断言。

> 现状**不可**接受：`docs/gate.md:430`「删掉证据文件（如 manifest）| ❌ 仍要」与
> `docs/gate.md:432`「active 目录内改名（含改名 manifest）| ❌ 仍要」在新判据下**变成假话**——
> tasks 3.4（文档）因此从「可选项」变成**必须项**。

### A1-2（tasks 3.3 的 merge 是「安全时 no-op、危险时第二个洞」）

**事实**：合并 `d_move_halves` 的源 id 进 `moved_sources`（`design.md:87-88`、`tasks.md:38`）在
S2 下让 `changed_change_ids` 丢掉 `b`（E2E：`2 个 change 目录` → `1 个`；纯函数 `test_p2`/`test_p4`），
**没有任何一格是它该做的**：D2 声称它覆盖「纯 `D`+`A` 幽灵 id 那一格」，
但纯 `D`+`A`（零 `R`）下 `d_move_halves` 恒为空 ⇒ 那格**不存在**（`design.md:88` 的措辞**假**）。

**必须**：删掉该 merge（或至少加「源 `<id>` 不在 head 树」守卫——但那使它纯属死代码）；
同时删掉 `design.md:88` 的理由句。

### A1-3（G4 的测试订正**不可实现**，且处置谎报）

**事实**：G4 要求「把 `tests/test_archive_arrival.py:300` 的空钉子测试改成**只有 `D` 记录（零 `R`）**的真用例」
（`reviews/grill-design.md:175-178`），处置称「tasks 3.3 已写明」（`:202-203`）。
实测：(a) `tasks.md:38-39` **没有**这句；(b) 在 cond3 判据下该订正**不可实现**——
零 `R` ⇒ 无锚 ⇒ `changed_change_ids` 必为 `['z']`、`d_move_halves` 必为空，
任何「幽灵 id 已消除」的断言**必然失败**（`test_a1_pure.py::test_p3`：`assert det == frozenset()` 通过，
`_attack(True)` 有 `R` 时 `test_p1` 才通过）。

**必须**：`tasks.md` 写明该测试**实际**怎么处理（我建议：改成断言「零 `R` ⇒ 源侧照旧要事件」的**正向**钉子，
与 N-i 同口径），并把处置对应行改成与 tasks 一致。

### A1-4（G5 的 **spec 侧** 未落库）

**事实**：处置称 G5「已写进 spec 的最后一条 Scenario 与 §3 N-i」（`reviews/grill-design.md:206`），
但 `grep -c "manifest\|别名\|与目录不符" specs/archive-awareness/spec.md` ⇒ **1**（仅 `spec.md:60` 的路径名）——
spec 里**没有**「manifest 必须用归档目录名 / 不得保留原 `<id>`（否则报『与目录不符』）」这条边界的任何文字。

**必须**：要么在 `spec.md` 补一段（推荐：并进最后一条 Scenario 的 Then），
要么把处置那行改成「只登记在 design §2 D1/§3 N-i，不写进 spec」。

### A1-5（`proposal.md` 与判据/规格不一致——proposal 是 change 的目标声明）

**事实**：`proposal.md:47` 仍列第 4 条「⚠️ 源 `<id>` 的目录在 **head 树里已不存在**」，而
`design.md §2 D1` 的修法（G1）恰恰是**去掉**它；`proposal.md:46` 的第 3 条是「满足现有的到达判据」
而非身份锚（全文**无** `source_ids`）；`proposal.md:60` 说「四条**否定面**」，而 `design.md §3` 现在是
**九条**（N-a…N-i，`design.md:112-120`）。

**必须**：`proposal.md` 的第 3/4 条与「四条否定面」按 design/spec 现状改写。

### A1-6（低危，可并入 A1-4 的同一处改动）：spec 的 N-f Scenario **不可端到端测**

`spec.md:69-72` 写成「**Given** 一条 `D` 记录的路径正好是 `<changes_root>/<id>`（目录本身）/
**When** 运行 `check`」——真 git **不会**为目录报 `D`（我构造不出该 `D` 记录），
故该 Scenario 只能落到纯函数面（`tasks.md:32` 的 2.4）。**必须**：把该 Scenario 的 When 改成
「构造该 `D` 记录（纯函数面）」或注明只由纯函数测试覆盖；否则它是**不可测的规格文字**。

---

## Open Questions

### Q-A1-1（**只有用户能拍**）：锚不够，怎么补？

判据要「认 `D`+`A` 是一半」，就必须借 **git 自己的配对**当身份证明；而 git 的配对**是全局的**，
会把无关 change 的文件配进到达目录（S2/S8 都因此拿到锚）。三条加严路，我已**实测**其中前三条：

| 选项 | 判据 | S1（目标） | S2（蓄意钥匙） | S8（**零蓄意**） | `a` 侧误伤 | 全量回归 |
| --- | --- | --- | --- | --- | --- | --- |
| **甲** = 本次设计（cond3） | `<id> ∈ A.source_ids` | ✓ rc=0 | **✗ 放行（rc=0）** | **✗ 放行**（5→3 项） | 无 | 702 passed |
| **乙** = +cond4（源目录不在 head） | 甲 ∧ 源 `<id>` 不在 head 树 | ✓ rc=0 | **✓ 挡住（rc=1）** | ✗ **放行** | 无 | 702 passed |
| **丙** = +「源集合恰为 `{<id>}`」 | 甲 ∧ `A.source_ids == {<id>}` | ✓ rc=0 | **✓ 挡住（rc=1）** | **✓ 挡住（rc=1）** | **有**：S2/S8 里 `a` 自己也失去豁免（回到 5 项） | 702 passed |

- 乙 = design §2 D1 原本的第 4 条（被 G1 以「`D` 侧比 `R`/`C` 侧严 ⇒ 部分搬移不对称」为由**去掉**）。
  实测它**不**回退 S1、**不**破既有测试，**能**挡 S2，但**挡不住** S8（整目录删除时源目录本就不在 head）。
- 丙 最严（S2/S8 都挡），代价是「到达目录里混入**任何**第二个 change 的配对文件 ⇒ 该归档 change 的
  `D` 侧**整体**失去豁免」——即 S8 那种**意外**会让 `a` 的正当豁免**一起**变红。方向是保守的
  （宁可多红，不放行），但会把「git 的意外配对」变成**噪声红**。
- 还有一条我**未**实测的候选（**未验证**）：**内容同一性锚**——要求 `A` 侧 blob == `D` 侧的 base blob
  （或相似度阈值），可覆盖「零 `R` 的纯 `D`+`A`」（N-i）与「git 没配上但内容确实原样搬走」的情形，
  但同时会放行「copy+delete」（更像伪造面）⇒ 我不推荐它当**主**锚，可作为**附加**通道另行评估。

**我的推荐**：若要**保守**（优先「不放行删除」），取 **丙**，并接受「意外配对导致噪声红」的代价；
若要**贴 design 原意**（`D` 与 `R`/`C` 同结论、少误伤），取 **乙** 并在 `docs/gate.md §7` 如实登记
「S8 型（整目录删除 + git 意外配对）仍可被洗白」。**甲（现状）**只有在 ②「如实登记 + 补测试」被接受时才可保留。
—— 请用户在 **甲 / 乙 / 丙**（或「甲 + 登记」）之间拍一个。

### Q-A1-2：merge（tasks 3.3）去留？

它唯一的作用是把仍活着的 active change 从 `changed_change_ids` 里**抹掉**（A1-2 的洞），
而它声称覆盖的「幽灵 id」格在 cond3 下**不存在**。我建议**直接删掉**；
若用户认为「`D` 侧的源 id 必须与 `R` 侧同结论」是产品目标，那就得**同时**加「源目录不在 head」守卫
——但那样它退化成 cond4 的重复，且与 cond4 若不同时采纳会自相矛盾。**请一并拍**。

---

## 收敛结论

**不收敛**

- **判据 ①（本轮无新的可证伪项）→ 不满足**。本轮新增**可复算**的证伪：A1-1（S2 `rc=0` 全绿 +
  S8 零蓄意洗白）、A1-2（`b` 逃掉契约校验，`2 个 change 目录` → `1 个`）、A1-3（G4 的订正不可实现）、
  A1-6（N-f 不可端到端测）。这些**不是**措辞/计数/格式问题，是**行为**差异（真 git + 真 CLI，附原始输出）。
- **判据 ②（已知必须修改项已按 artifact 落库）→ 不满足**。G5 的 **spec 侧**未落库（A1-4，处置谎报）；
  G4 的**测试订正**未落库且在新判据下不可实现（A1-3）；G1 的落库**不完整**——新判据自己引入新洞，
  且四处旧理由（`design.md:64/115`、`spec.md:52`、`grill-design.md:196-198`）**未随重写更新**（A1-1）。
  G2/G3/G6 已按 artifact 确认落库。

> 收敛的两个条件**都**要求「必须修改项 A1-1…A1-6 全部落库 → 复跑对抗轮，
> 且该轮**不再**产生新的可证伪项」。当前停在 **G1**（判据不足，且是**新增**的不足），
> 与 grill 轮停在同一个骨头上——**判据借 git 的配对当身份证明，而 git 的配对是全局的**。

---

## 处置（主 session 在 A1 之后追加，非审阅者原文）

> **A1-1…A1-6 全部已落库**。这一轮最有价值的是 **A1-1**：它证明我上一轮按 grill 的 G1 写的锚
> （`<id> ∈ A.source_ids`）**仍然可被洗白**，而且 **S8 是零蓄意的**。判据已按你实测的三条路改成 **(丙-A)**。

- **A1-1（判据不充分）**：接受。**判据第 3 条改成 `A.source_ids == {<id>}`**（你实测的丙-A）。
  依据写进 `design.md §2 D1` 的**三路对照表**（甲/乙/丙 × S1/S2/S8），
  代价（跨配对时该搬移的 `D` 全部失去豁免）如实登记在 §3 N-j/N-k 与 §4 R2。
  ⚠️ 我上一轮在 `grill-design.md` 的「处置」里写过「那条攻击拿不到 `b ∈ A.source_ids`」——
  **那句是错的**（S2 正是拿到它的方式）；该报告文末已按事实更正。
- **A1-2（merge 是洞 / 恒空）**：接受，**D2 的那半已整段删除**：`changed_change_ids` 不动
  （在「恰为一个源」的锚下 `d_move_halves` 对纯 `D`+`A` 恒为空 ⇒ 那半是 no-op；
  而无条件并进 `moved_sources` 会让**活着的** change 逃掉契约校验——你的 S2 实测 `2 个 change 目录 → 1 个`）。
- **A1-3（G4 的订正不可实现 + 处置谎报）**：接受。**处置里那句「tasks 3.3 已写明」是假的**，
  已改：G4 现在只登记为 §4 R5（**不动**那个死分支，超出本 issue 的面），tasks 3.3 明确写「不碰」。
- **A1-4（G5 的 spec 侧）**：已补——spec 最后一条 Scenario 现在写明「同一形态下到达目录没有 source id 别名
  ⇒ manifest 必须用归档目录名，否则报『与目录不符』」。
- **A1-5（proposal 过期）**：已改——目标里的四条改成三条（去掉「源目录必须在 head 消失」那条），
  验收里的「四条否定面」改成「十一条（N-a…N-k）」。
- **A1-6（N-f 不可端到端测）**：已在 `tasks.md 2.3` 与 spec 里写明它是**纯函数级**的钉子
  （`<sub>` 为空的记录在端到端里构造不出来）。

### 你的两条 Open Question

- **Q-A1-1（锚不足怎么补）**：**取丙**（`sources == {<id>}`），理由与代价见上。
  你说「甲仅在『如实登记 + 补测试』被接受时保留」——**不保留甲**：S2 的 `rc=0 全绿` 是不可接受的。
- **Q-A1-2（merge 去留）**：**删**（见 A1-2）。

**下一轮（A2）**：树已冻结在本改动后的 revision。请优先攻**新判据**（丙）的绕过与误伤面，
以及「还有没有第四条路」。
