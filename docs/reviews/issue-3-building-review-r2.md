# 独立审阅 R2：issue #3（run id 确定性）实现

Verdict: **PASS**

被测对象：分支 `fix/run-id-determinism/2026-10-10`（head `2f217b2`），对比 `main`。
基线：`uv run pytest -q` → **342 passed**（与声明一致）。
本审阅为**全新零记忆**：独立读码全文、独立跑真 CLI、独立做**变异**（原地改坏 → 跑指定测试 → `git checkout -- <file>` 还原，全程 `git status` 干净），未采信任何自述。

**结论一句话**：R1 的两条**都真的修好了**——Q3 口径在**全部用户可见处**已统一、无自相矛盾；CD8 文档守卫现在**真能抓住**「给了才幂等」这类假说法（变异实测变红）。新发现**一处中低的守卫覆盖缺口**（幂等限定守卫对 3/8 个列名文件是**空转**，含 CD9 点名的 `cli.py`）与两处**字面量判据偏窄**，均**非阻塞**（无任何用户可见文档为假、无行为回归），故判 **PASS** 并附建议修法。

---

## 1. R1 两条项的独立复现

### 1.1 Q3 口径统一 —— ✅ 真修好（全部用户可见处）

逐个通读了所有会写 run-id / 身份口径的**用户可见文件**：`templates/review-loop.md`、`templates/grill.md`、
`plugin/README.md`、`plugin/commands/{grill,review-loop}.md`、`docs/design.md`、`docs/gate.md`、
`src/witnessloop/{cli,agentenv,contract,manifestcmd}.py`。结论：

- R1 Issue 1（`templates/review-loop.md:17`）**已改**：现为「强制 `reviewer_run_id != author_run_id`——但注意
  **兜底路径下两者结构性不同**，所以这道校验只挡『**显式**把同一个值喂给两个角色』，**不证独立 run**」
  （`templates/review-loop.md:16-18`），与同文件 `:127-135`、`:145-147` 口径一致，**不再自相矛盾**。
- R1 Issue 2（`manifestcmd.py:125` 用户可见报错）**已改**：实测输出为
  「…审阅者必须独立于作者（**兜底路径下两角色结构性不同，这道校验只挡「显式把同一个值喂给两个角色」**）。
  没有写出任何文件。」（§3 实测 (b)）。旧措辞「挡「忘了另开 run」」已消失。
- R1 Issue 3（`contract.py:253` 陈旧注释）**已改**（`contract.py:253-255`）。
- R1 Issue 5（`design.md:79` §5.1 无条件「幂等」）**已改**：现为「**固定 base 与 revision 时**幂等
  （幂等键 = `(change, stage, role, revision, base ref 的解析目标)`）」（`design.md:79-80`）。

**无一处仍写旧口径、无自相矛盾**（独立核对）：
- 全文搜索「挡「忘了另开 run」」，命中处**全部**是**否定/引述**形态
  （`design.md:101`、`gate.md:109`、`templates/{grill,review-loop}.md`、`agentenv.py:21`、以及 `tests/test_docs.py` 的判据注释本身），
  **没有**任何一处作**肯定**宣称「该校验证明独立」。
- 全文搜索「证独立 / 保证独立」只命中否定式「**不**证独立」（`plugin/README.md:56`、`templates/review-loop.md:18`、
  `design.md:143`、`contract.py:255`）。
- 「审阅者必须另起 run」这类**流程要求**保留得**正确**（它本就独立于机械校验）——`templates/review-loop.md:16`、
  `templates/grill.md:204-206` 明确写「兜底 id 的结构性差异**不代你保证**这一点」。

### 1.2 CD8 文档守卫 —— ✅ 真能抓「给了才幂等」这类

`tests/test_docs.py` 现新增三组守卫（`:49-126`）：`RUN_ID_DOCS`（含 `src/witnessloop/cli.py`）、
`STALE_FALLBACK_CLAIMS`（**新增 `"才幂等"`**）、`Q3_DOCS`、`IDEMPOTENCY_DOCS`。

**变异实测**（§3 全表）：往 `cli.py` 塞回 `# 给了才幂等` → **RED**（R1 时全绿）；塞进 `design.md` 同样 → **RED**。
基线时该守卫 `7 + 9 + 8 = 24` 个参数化用例全绿是**真的在检**（见 §2.3 的触发面分析，5 个文件真正触发）。

---

## 2. 新发现的问题

### Issue N1（中低，非阻塞）—— 幂等限定守卫对 3/8 个列名文件**空转**（含 CD9 点名的 `cli.py`）

`test_manifest_build_idempotency_claims_carry_the_qualifier`（`tests/test_docs.py:110-126`）的判据是**按行窗口**：
「某行含 `幂等` **且** 该行 ±3 行内出现字面量 `manifest build`」时才要求窗口内出现 `固定 base 与 revision`。
**哪一行都不满足**时，该参数化用例**恒绿**。逐文件实测触发面：

| 文件 | 触发用例数 | 判据是否真的在检 |
|---|---|---|
| `docs/design.md` | 1（L79） | ✅ 真检 |
| `templates/grill.md` | 1（L163） | ✅ |
| `templates/review-loop.md` | 1（L129） | ✅ |
| `plugin/commands/grill.md` | 1（L55） | ✅ |
| `plugin/commands/review-loop.md` | 1（L49） | ✅ |
| **`plugin/README.md`** | **0** | ⚠️ **空转** |
| **`src/witnessloop/cli.py`** | **0** | ⚠️ **空转** |
| **`docs/gate.md`** | **0** | ⚠️ **空转** |

原因：这三处「幂等」句与字面量 `manifest build` 相距**超过 ±3 行**（README 里 `manifest build` 出现在窗口**上一行**、
`cli.py` 只在模块 docstring 第 4 行出现 `manifest build`、`gate.md` 的幂等句压根不含 `manifest build`）。
**变异实测**（**不改变行数**、仅在同一行删掉限定词，确保不是靠错位触发的假阳性）：

| 变异 | 结果 |
|---|---|
| README 同行删「固定 base 与 revision 时」，改「重复 build 产出逐字节一致的 manifest（幂等）」 | **1 passed（未抓到 ❌）** |
| `cli.py` build help 同行删限定，改「（幂等；不 auto-commit）」 | **1 passed（未抓到 ❌）** |
| `gate.md` 同行删限定，改「**manifest build** … **幂等**」**但**把 `manifest build` 挪到别的行 | **1 passed（未抓到 ❌）** |

即：**从这三个文件里删掉 Q2/Q3 要求的限定词，CI 不会变红**——其中 `cli.py` 是 **CD9 点名**的「用户无条件「幂等」」落点，
它的限定词目前**实际不受守卫保护**。

> **与作者自陈的出入**：作者只自陈「`gate.md` 那条是空转」。**核对属实**，但**不止一条**——`cli.py`、`plugin/README.md`
> 同样空转。这一点重要：守卫把这 3 个文件**列进了 `IDEMPOTENCY_DOCS`**，于是测试报「8 passed」时给人一种
> 「8 个文件都验过」的**假保证**。对一个「以不让文档漂移为核心卖点」的项目，这是「守卫挂上了但没挂在目标上」的
> 同一类缺陷（R1 就是这么判 Issue 4 的），只是它**未被任何已确认决策强制**（CD9 只要求改文案、未要求加守卫），
> 且**没有任何当前文档因此为假**，故判**非阻塞**。

**建议修法**（任选其一，均为一处小改）：
- 把窗口按**语义块**而非固定 ±3 行划（例如「整段」或「到下一个空行」），或
- 判据改为**文件级正向约束**：文件里**出现 `幂等`** ⇒ 该文件**必须出现 `固定 base 与 revision`**（按文件而非按行窗口），
  对 `IDEMPOTENCY_DOCS` 全量成立；并**把 `cli.py` / `README` / `gate.md` 从空转变真检**后再宣称覆盖它们。

### Issue N2（低，非阻塞）—— CD8 守卫只抓 `"才幂等"` 子串，R1 点名的**同族**假说法仍漏

R1 原文：守卫「抓不到 CD8 真正要防的那一类假说法——**任何**「X 才幂等」「**重复 build 会得到不同 id**」式的新假话
都能静默留存」。本轮把 `"才幂等"` 加进了判据，故「给了才幂等」这一支**已抓**（§1.2）；
但**同族的另一支**「重复 build 会得到不同 id」**不含量子串 `才幂等`**，仍漏网：

| 变异 | 结果 |
|---|---|
| `cli.py` 追加 `# 重复 build 会得到不同 id` | **1 passed（未抓到 ❌）** |

**副带风险（误伤面）**：`"才幂等"` 是裸子串判据——一句**正确**的说法如「只有在固定 base 与 revision **时才幂等**」
也会被它判红（当前无此写法，属潜在误伤）。建议把该支换成**正向约束**（出现 `幂等` ⇒ 必须出现 `固定 base 与 revision`，
即 N1 的改法），既覆盖全族、又不会误伤「…才幂等」的正确句。

### Issue N3（低，非阻塞）—— Q3 守卫是**精确字面量**，换一种旧口径写法即漏

`STALE_Q3_CLAIM = "挡「忘了另开 run」"`（`tests/test_docs.py:88`）用**精确字面量**。**精确回滚**能抓
（M3：`cli.py` 塞回 `（挡「忘了另开 run」）` → RED；M9：`manifestcmd.py` 报错回滚到旧句 → RED），
但**去掉引号/换措辞的旧口径**漏网：

| 变异 | 结果 |
|---|---|
| `manifestcmd.py` 改成旧口径但**不写引号**：「这道校验只挡**忘了另开 run**，即…」 | **1 passed（未抓到 ❌）** |

属可接受的漂移守卫粒度（最可能发生的回归是**逐字回滚**，已能抓），**低**。

### Issue N4（nit）—— 遗留旧口径：`tests/test_check_manifest.py:55` 的 docstring

```
"""D4：同一个 run 既写又审 → 必须拦下（挡「忘了另开 run」）。"""
```

与 R1 Issue 3（`contract.py:253`）**同一类**「非用户可见的 Q3 漂移面」——`contract.py:253` 本轮已清，
**这一处漏了**。该文件**不在** `Q3_DOCS`（守卫清单只含 6 个 md + `cli.py` + `manifestcmd.py` + `contract.py`，
**不含测试文件**），故守卫也不覆盖它。而且这句本身**half-true**：用例是**显式**把 `"same-run"` 喂给两角色才被拦，
并非「同一个 run 既写又审」在兜底路径下会被拦（兜底路径根本不会命中 D4）。非用户可见，nit，建议顺手同步措辞。

---

## 3. 变异证据（关键实现 / 守卫「改坏 → 变红」，原地变异后还原）

隔离方式：**原地变异 → 跑指定测试 → `git checkout -- <file>`（或 cp 备份）还原**；每轮结束 `git status` 干净。
未用 `uv run --project <副本>`（那会回落原仓代码、测不到变异）。

| # | 变异 | 文件 | 目标测试 | 结果 |
|---|---|---|---|---|
| M1 | 塞回 `# 给了才幂等` | `cli.py` | `test_docs_promise_a_deterministic_fallback[cli.py]` | **1 failed ✅**（R1 时全绿） |
| M10 | 塞回 `<!-- 给了才幂等 -->` | `docs/design.md` | 同上 `[design.md]` | **1 failed ✅** |
| M3 | 塞回旧口径 `（挡「忘了另开 run」）` | `cli.py` | `test_docs_use_the_settled_identity_wording[cli.py]` | **1 failed ✅** |
| M11 | 塞回旧口径 | `docs/design.md` | 同上 `[design.md]` | **1 failed ✅** |
| M9 | 报错**精确回滚**旧句 | `manifestcmd.py` | 同上 `[manifestcmd.py]` | **1 failed ✅** |
| M5 | 删掉 `固定 base 与 revision 时` 限定 | `docs/design.md` | `…idempotency…[design.md]` | **1 failed ✅** |
| M8 | 改成含 `manifest build` 的无条件「幂等」 | `docs/gate.md` | `…idempotency…[gate.md]` | **1 failed ✅** |
| I1 | `ANCHOR_DIGEST_LEN = 12 → 8` | `agentenv.py` | `tests/test_agentenv.py` | **2 failed ✅** |
| I2 | build 忽略 `--base`（base 不进键） | `manifestcmd.py` | `test_base_drift_does_change_the_bytes` | **1 failed ✅** |
| I3 | 关掉 ① 单段校验 | `manifestcmd.py` | `test_nested_change_id_is_rejected` | **1 failed ✅** |
| **M2** | 塞回**同族**假说法 `重复 build 会得到不同 id` | `cli.py` | `test_docs_promise_a_deterministic_fallback[cli.py]` | **1 passed ❌ ← N2** |
| **M4** | 旧口径**去引号**改述 | `manifestcmd.py` | `test_docs_use_the_settled_identity_wording` | **1 passed ❌ ← N3** |
| **M6b** | 同行删限定（README，不改行数） | `plugin/README.md` | `…idempotency…[README]` | **1 passed ❌ ← N1** |
| **M7b** | 同行删限定（`cli.py`，不改行数） | `src/witnessloop/cli.py` | `…idempotency…[cli.py]` | **1 passed ❌ ← N1** |
| **M8b** | 同行删限定（`gate.md`，不改行数） | `docs/gate.md` | `…idempotency…[gate.md]` | **1 passed ❌ ← N1** |

结论：**目标类（CD8「给了才幂等」、Q3 旧口径逐字回滚、CD9 限定词在 design.md/模板）都有能被变异变红的测试**；
缺口感只有 §2 的 N1/N2/N3（守卫**覆盖不足**，非目标不达标）。

**端到端真 CLI 抽检**（scratch 仓 `/tmp/wl-r2/scratch`，`uv run --project` 指回本仓）：

```
(a) 无 env       → reviewer_run_id=building-reviewer-add-retry-ca85fba2ac79
                   author_run_id  =building-author-add-retry-ca85fba2ac79      # 结构化不同、12 位摘要
(b) WITNESSLOOP_RUN_ID=shared → 报错：…「兜底路径下两角色结构性不同，这道校验只挡「显式把同一个值喂给两个角色」」…
(c) 固定 base 连跑两次 → manifest 字节 sha256 前 16 位 = 8303ad31d8096dc0 = 8303ad31d8096dc0（逐字节一致）
(d) --change foo/bar  → 报错：change='foo/bar' 不能含 `/`：change id 是 `openspec/changes/<id>/` 的**单段**目录名。
```

---

## 4. Q1 / Q2 / Q4 / ① 抽查（不回归）

R1 已逐条验过；本轮抽查关键性质仍**有变红测试保护**（§3 的 M5/M8/I1/I2/I3 即为其证据）：
Q1 摘要 ≥12 位（I1 红）、Q2 幂等键含 base（I2 红 + 端到端 (c)）、① 单段校验（I3 红 + 端到端 (d)）、
Q4 stdout 打印实际 id（端到端 (a)）。**无回归**。

---

## 5. 未覆盖 / 边界备注（非阻塞）

- N1 修复后，建议**同时**把 `cli.py`/`README`/`gate.md` 从「空转」变「真检」，否则「列名却空转」的假保证仍在。
- 判据「字面量 substring」这一族（N2/N3）本质上只能抓**逐字回滚**；真正稳健的写法是**正向约束**
  （出现 `幂等` ⇒ 必须出现限定；出现 run-id 兜底 ⇒ 必须含 `确定性`），本轮已是 substring 版，属**增量**改进。
- 本轮未触碰 `manage`/`check` 对 run-id 的形态校验（CD5 有意保留），符合定稿。

## 6. 停轮问题

无**需人拍板**的停轮问题。N1–N4 都非阻塞；N1 的修法是一处窗口/判据小改，N2/N3/N4 顺带即可。

## 7. Reviewer

- 分支: `fix/run-id-determinism/2026-10-10`（head `2f217b2`）
- 基线: `uv run pytest -q` → 342 passed（复现一致）
- 时间: 2026-10-10
- 方式: 全新零记忆；通读全部用户可见文件 + scratch 真仓跑 CLI + 15 组原地变异（全部还原、`git status` 干净）
