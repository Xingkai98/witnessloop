# Building Review: confirm-gate-fail-closed

> 审阅者：**独立零记忆实现审阅**（building，**第 2 轮**）。
> 只读：除本文件外**未改**被审 worktree 的任何文件、未 commit。
> 基线：`origin/main` = **`ef8b3ab`**；被审提交 `ef8b3ab..9eb6e72`（6 个 commit）。
> 会改状态的实验在**隔离副本**里跑：`/tmp/cgf-rev2`（`tar` 整棵工作树 + `rm -f .git && git init -q`）、
> `/tmp/cgf-mut`（变异）、`/tmp/cgf-n3`（O(n²) 单跑）、`/tmp/cgf-bt-*`（basetemp）。
> ⚠️ 本仓 CI 只有 **pytest + dogfood `witnessloop check`**；**没有** openspec validate / RIR / Impact Analysis。

## Verdict

**PASS —— 已收敛，可进证据与 PR。**

上一轮唯一的那条**阻塞**（`evidence.py:41` 候选判定正则的**指数回溯**）**真的修好了**：
作者把 `^(?:\S+[- ])*Open Questions$` 换成 `_strip_trailing_qualifiers`（反向一遍）+ `_is_tail_phrase`
（前向一遍），我**自己另写 oracle**（规范正则 + 旧括号循环，逐字照抄）做了 **≈ 43 万条**输入对照
⇒ **0 处分歧**（唯一分歧类是**尾随 `\n`**，我用 `splitlines()` + `.strip()` 证明它在真实路径上
**不可达**）；性能从 R1 实测的 **0.34 s / 5.6 s / 挂住** 掉到 **微秒级**，且**证明是线性**
（规模翻倍耗时比 1.97 / 1.98 / 2.03 / 1.96）。作者**自报的第二条路径**（剥尾括号 O(n²)，
`（a）` × 20 000 原 **19.3 s**）一并线性化 —— 我用**真 O(n²) 变异**打它，
**恰好只让那一条用例转红**。作者说「oracle 当场抓出它第一版推导的洞（单独的 `-`）」
**我用变异独立复现**（去掉「末位分隔符前必须有一个词」⇒ 2 条等价性用例转红）。

4 条非阻塞**逐条真修好**（§7.20 四个指纹**实测吻合**且标签不再自相矛盾；接入方 fixture
**逐字节冻结**进 `tests/fixtures/`，`sha256 7a520c3e…` 与原检出**完全一致**，全量 **0 skipped**；
提示文案改单数并有用例钉住；两条副作用的「有无提示」补了断言）。**回归面干净**：
我自造的 **14 条攻击 + X1–X16（共 53 条用例，含 2 万条模糊 + 病态输入）全部仍按设计闭合**，
**没有一条被修正则改歪**。**16 组变异抽验**每组只让对应用例转红、还原后 sha256 一致。

本轮**没有新的阻塞项**。遗留的 3 条**全是措辞/注解级**（见 §R2-6），**不影响任何判定**，
**不建议为它们再开一轮**。

## R2 复审

### R2-1（上一轮**阻塞**）正则重写：**真线性 + 真语义等价** ✅

**做法**：我不信作者的 oracle 规模，自己从零写了一份对照脚本（`/tmp/cgf_oracle*.py`），
oracle = **规范正则本身**（`spec.md:38-39` 的 `^(?:\S+[- ])*Open Questions$` + D2 的尾括号剥离循环，
逐字照抄），对照三组：

| 对照 | 输入规模 | 分歧 |
|---|---|---|
| `_strip_trailing_qualifiers` vs 旧括号循环 | 20 456 | 68（**全是尾随 `\n`**，见下） |
| `_is_tail_phrase` vs 规范尾短语正则 | 17 213 | 1（同上） |
| `_is_open_questions_title` vs 全 oracle | **429 702** | 0 |
| 旧实现 vs 新实现（端到端） | 45 122 | 1（同上） |

输入空间（**穷举为主、随机为辅**，不是抽样）：
前缀 over `{a,-,空格}` **长 ≤ 9 全穷举**（59 048）；前缀 over `{a,-}` **长 ≤ 14 全穷举**（65 534，
专打连字符密度）；括号/字母/空格 **长 ≤ 5 全穷举**（9 331）；Unicode 空白口径
（`\t \n \r \x0b \x0c \x1c \x1d \x1e \x85 \xa0 　       ` 各挡分隔符/词内/首位/次末位）；
尾括号形态大扫（全角/半角/空/嵌套/混合/带空格，× 各种前缀 × 1–5 层）；混合随机 40 000 + 巨扫 220 000。
含 `Open Questions` 但前后带奇怪字符、超长与全角混合、连续分隔符、前导/尾随分隔符**都在**。

**唯一的实质分歧类：尾随 `\n`。** 规范正则用 `$`，Python 的 `$` **在尾随 `\n` 前也匹配** ⇒
`"Open Questions\n"` oracle 判 **候选**、新实现判**非候选**（反之亦然，涉及 `_strip_trailing_qualifiers`
的 68 例）。方向是 **oracle=True / impl=False**（本会是危险方向）。
**但它不可达**：候选判定的输入只来自 `_sections()` 的 `_HEADING_RE.match(line).group(1).strip()`
（`evidence.py:104-107`），而 `line` 来自 `text.splitlines()` —— `\n` / `\r` / `\x0b` / `\x0c` /
`\x1c` / `\x85` / ` ` 等**全是切分点**，不可能留在行内；`.strip()` 再抹一遍首尾空白
⇒ **title 永远无首尾空白** ⇒ 这条分歧**在生产的任何路径上都撞不到**。
（⇒ 记入 §R2-6 的 Nit-1：docstring 写「**逐输入**等价」，严格说是「**除尾随 `\n` 外**
逐输入等价，而那一类不可达」——一字之差的诚实度问题，不是缺陷。）

**性能实测**（`/tmp/cgf-rev2`，真函数直调，取 3 次最小；核对作者给的三个数字量级）：

| 输入 | R1 实测（修前） | **本轮实测（修后）** |
|---|---|---|
| 45 字 / 22 连字符 | 0.3457 s | **0.0005 ms** |
| 53 字 / 26 连字符 | 5.6104 s | **0.0005 ms** |
| 203 字 / 101 连字符 | 分钟级 | **0.0005 ms** |
| 20 002 字 / 10 000 连字符 | 等于挂住 | **0.0006 ms** |
| `（a）` × 20 000（**第二条路径**） | 19.3 s | **9.604 ms** |
| `（a）` × 40 000（无 `Open Questions`） | —— | 19.3 ms |

作者自报「45 字 0.34 s → 0.0004 ms / 53 字 6.5 s → 0.0005 ms / 20 002 字 → 0.0043 ms /
`（a）`×20 000 19.3 s → 9.0 ms」——**量级全部吻合**（我的绝对值略有出入，属正常机器差；
`0.0043 ms` vs 我的 `0.0006 ms` 同属微秒以下）。

**第二条路径是否真线性 ⇒ 是**（这是我本轮新增的、作者没给的证据）。规模翻倍耗时比：

```
n=  5000  2.426 ms
n= 10000  4.785 ms  ratio=1.97
n= 20000  9.460 ms  ratio=1.98
n= 40000 19.189 ms  ratio=2.03
n= 80000 37.648 ms  ratio=1.96      ⇒ 真线性（O(n²) 会是 4×）
```

**作者「oracle 抓出第一版推导的洞」这句话 ⇒ 我用变异独立复现**：去掉「末位分隔符前必须有一个词」
（即允许前缀是单独一个 `-`）⇒ **恰好** 2 条等价性用例转红
（`test_candidate_judgement_matches_the_spec_regex[短前缀穷举]` / `[随机长输入]`）、其余全绿。
这句话**不是自夸，是真的**。

### R2-2 四条非阻塞：**逐条核过，都真修好** ✅

| # | 上轮要求 | 本轮核实（**读代码 + 实测**） |
|---|---|---|
| ② | `design.md §7.20` 指纹块四个值全过期 + 块标签与表行自相矛盾 | ✅ **四个值逐个 `sha256sum` 复核，与块里写的逐字符相同**：`proposal b9d5d497…` / `tasks 378fc7c7…` / `spec ba3782c1…` / `grill-design 85fb8e33…`。块标签已改成「**实现审阅的修订落地之后**」、表行改成「**实现期修订稿**（当前）」⇒ **自相矛盾消除**。守卫仍绿：`tests/test_confirm_gate_docs.py` **12 passed**（`--collect-only` 实测 12 条） |
| ③ | 接入方 fixture 用绝对路径 ⇒ CI 恒 skip | ✅ `tests/fixtures/adopter-grill-design-nonverbatim.md` 的 `sha256 = 7a520c3e6ff10a21…`，与本机接入方检出那份 **逐字节相同**（我两边都算了）。用例改成读 fixture ⇒ **全量 `0 skipped`**、`grep -rn "pytest.skip\|@pytest.mark.skip" tests/` **零命中**。该用例在全量里**真跑**（单跑 PASSED）。⚠️ 它仍是**真钉子**（变异 M1 下转红）⇒ CI 上从此有替代品 |
| ④ | 提示文案的子串与实际筛选口径错位 | ✅ `_OPEN_QUESTIONS_HINT`（`evidence.py:45-48`）已改**单数** `Open Question`，并补注释说明「与判据逐字一致」；`design.md §D4` 同步。新增用例 `test_the_hint_names_the_substring_that_is_actually_filtered_on` 同时断言**含单数**且**不含复数**；我的变异 **N7**（改回复数）**恰好只让这一条转红** |
| ⑤ | 两条副作用的「有无提示」没断言 | ✅ 新增 `test_the_two_known_title_side_effects_differ_in_whether_the_hint_appears`：`Open  Questions`（双空格）⇒ **恰好 1 条、等于通用文案**（无提示）；`Open Questions：`（全角冒号）⇒ **1 条且含「检测到含」与标题名**（有提示）。与 `design.md:256-257` / `spec.md:58-61` 一致 |

⚠️ **一处残留**（**非阻塞**，见 §R2-6 Nit-3）：`docs/gate.md:400` 仍写「诊断**列出**报告里含
**`Open Questions`** 字样的二级标题」——与 ④ 是**同一类**错位（筛选口径是单数）。
R1 已判它「泛指、不构成错」；我**同意不阻塞**（描述的是**被实际列出集合的子集**，没有陈述假命题），
但既然 ④ 已经在代码与 design 里改齐，这一处**一字之差**顺手改齐更一致。

### R2-3 回归：14 条攻击 + X1–X16 **仍全部按设计闭合**，**语义没被改歪** ✅

我在隔离副本里**另写**了一份 53 条用例的攻击台（`/tmp/cgf-rev2/tests/test_r2_attacks.py`，
**不复用仓内 helper**，从零拼报告）：R1 的 14 条攻击 + X1–X16 逐条 + 20 000 条随机模糊 + 病态输入
（空串 / 只有围栏 / `## ` 空标题 / `\x00` / `## Open Questions` 裸标题…）。

```
53 passed in 3.59s        # 含 ATT-A 自检（合格报告 ⇒ 绿）——排除「环境坏了所以全红」
```

| 面 | 结果 |
|---|---|
| ATT-A 自检（合格 ⇒ 绿） | ✅ |
| ATT-B 花哨标题 `## 悬而未决的疑问` + 未确认（**走真 CLI**） | ✅ `EXIT_FAIL` + `缺少 \`## Open Questions\` 小节` |
| ATT-C 空壳 + 真问题进近义小节（**走真 CLI**） | ✅ `EXIT_FAIL` + `Q1 未经用户确认` |
| ATT-D 诱饵 manifest（`aaa.` 合规在前 / `zzz.` 坏在后） | ✅ `EXIT_FAIL` + **Q1/Q2 逐条报出** |
| ATT-D2 **加诱饵前后 finding 逐条相同** | ✅（X8 的「两种造法全等」这半边） |
| ATT-E 唯一 `## User Confirmation`（含真答复）写进围栏 | ✅ 红（缺 UC + Q1 未确认） |
| ATT-F 零宽空格 / 全角 `Ｏ` / 尾部 `．`/`、`/`：`/`\t` / 双空格 / 全小写（8 变体） | ✅ **全部红**，无静默跳过 |
| ATT-G 逐字标题缩进两格 | ✅ 红（fail-closed） |
| ATT-H `- **Ｑ1**`（全角 Q） | ⚪ 绿 —— 与声明 3 / X10 反例一致，**已知残留** |
| ATT-I `## Open Questions` 整个藏进围栏 | ✅ 红（候选为空） |
| ATT-J 结束标记 ` ``` extra ` | ✅ **不**算结束 |
| ATT-K `~~~` 开、`` ``` `` 关 / ```` ```` ```` 开、` ``` ` 关 | ✅ **两种都不算结束** |
| ATT-L 未确认 `Q2` 围进**候选小节内**的围栏 | ⚪ 绿 —— 声明 13 / X13，**用户已裁定接受** |
| ATT-M >20 字答复带 `待拍板` | ⚪ 绿；**边界精确在 20/21 字**（我用 20 字 vs 21 字亲手验） |
| ATT-N 连字符密集长标题（22 / 26 / 101 / 10 000） | ✅ **不再挂住**（上一轮的 ❌ 已消除） |
| X1–X16 逐条 | ✅ **16/16 与设计一致**（含 X6 Code-Resolved 不候选、X9 小节外不判、X10 全角数字**会**命中、X12 20/21 边界、X13/X14 围栏两侧代价、X15 多收边界、X16 末行胜**两方向**） |
| 20 000 组随机模糊 | ✅ 0 异常 |

**结论：修正则没有把语义改歪。** 值得单说的两条：`ATT-D2` 证明 D8 的「逐份校验」仍成立
（诱饵在场只多出**它自己**一条 finding，真报告的 Q1/Q2 一条不少）；`ATT-L` / `ATT-H` / `ATT-M`
三个「已知残留」**方向与文档逐字一致**，没有因为线性化而扩大或收窄。

### R2-4 变异验证：**抽验 16 组**（含 6 组我另造的）✅

每组：改一行实现 ⇒ 跑 `tests/test_evidence.py` + `tests/test_check_grill_evidence.py` + 我的攻击台
⇒ 只列**新增转红**的用例 ⇒ 还原后复算 sha256。**全部 16 组的还原 sha256 与基线一致**。

| 变异 | 实测 |
|---|---|
| M1 候选退回「只认逐字」 | ✅ 转红，含 `test_the_adopters_non_verbatim_report_passes`（**CI 上从此有替代品的那个钉子**） |
| M4 关掉围栏状态机 | ✅ **15** 条转红（含我攻击台的 ATT-E/J/L + X13/X14） |
| M5 D8 退回 `matching[0]` | ✅ **4** 条转红（含 ATT-D / ATT-D2） |
| M8 存在性改回 fail-open | ✅ **17** 条转红（含 ATT-B + ATT-F **8 个变体全部**） |
| M6 候选不排序 | ✅ **2** 条转红 |
| **N1 恢复原始正则**（把上一轮的缺陷放回去） | ✅ **仓自己的性能钉子抓住**：`26 连字符 ⇒ 8.35 s` 断言失败（`1 failed, 72 passed in 8.52s`）——**是干净红，不是挂住** |
| **N2 去掉「末位分隔符前必须有一个词」**（作者自报的洞） | ✅ **2** 条等价性用例转红 |
| **N3 剥尾括号退回真 O(n²)** | ✅ **恰好 1 条**转红：`test_a_long_run_of_trailing_qualifiers_is_stripped_in_linear_time`（5.07 s）。其余 81 条全绿 ⇒ 同时证明**该重写语义等价** |
| N4 不检查「前缀里的空白只能是空格」 | ✅ 3 条等价性用例转红 |
| N5 不检查「没有两个相邻空白」 | ✅ 1 条转红（`[空白口径]`） |
| N6 剥尾括号不 strip 中间空白 | ✅ 4 条转红 |
| N7 提示文案改回复数（非阻塞 ④ 的回归） | ✅ **恰好 1 条**转红（钉 ④ 的那条） |
| N8 围栏「开始」放宽成 ≥1 | ✅ 1 条转红（误伤本仓真实报告） |
| N9 结束标记不要求「其后只剩空白」 | ✅ 1 条转红 |
| **N10 结束标记不要求同字符** | ⚪ **0 条转红** —— **这不是用例失效**：我**穷举 54 610 组 `(line, 开字符, 长度)`** 证明 `marker[0] == char` 被同一行里的 `not stripped.strip(char)` **逻辑蕴含**（`stripped.strip(char)` 为空 ⇒ `stripped` 全由 `char` 组成 ⇒ `_fence_run` 必返回 `char`）⇒ 这是**语义等价变异**，与 R1 的 M7 同类，**不算缺陷** |
| N11 结束标记不要求「不短于」 | ✅ 1 条转红 |

**⚠️ 抽验中发现的唯一新事实**（**非阻塞**，Nit-2）：`_is_tail_phrase` docstring（`evidence.py:151-152`）写
「`str.isspace()` 与 `\s` **并不完全一致**（如 `\x1c`），而这个判定的规范是正则」——
我**全码点扫描 `0..0x10FFFF`**：`re.match(r"\s", chr(c))` 与 `chr(c).isspace()` **0 处不一致**。
CPython 里 `\s`（str 模式）就是 `Py_UNICODE_ISSPACE`，与 `str.isspace()` **同一个谓词**。
⇒ 这句注解**不成立**。**实现两种写法都对**（用 `_WHITESPACE_RE` 甚至更贴「跟引擎走」的意图），
只是理由写错了——**不影响任何判定**，顺手改掉即可。

### R2-5 两处说法独立复跑 ✅

```
$ export PATH=/home/happy/.local/bin:$PATH
$ uv run pytest -q --basetemp=/home/happy/wl-basetemp-rev2
601 passed in 30.55s
```
⇒ **成立**：`601 passed`（= R1 的 592 + 本轮 9 条），**`-rs` 下 0 skipped**。
（本轮 9 条 = 2 性能 + 1 输入集规模 + 4 等价性 + 2 提示，与 `tasks.md` 的记账一致。）

```
$ uv run witnessloop check --root . --base origin/main --head HEAD
check：基线 origin/main...HEAD，14 个变更文件，1 个 change 目录
  change：confirm-gate-fail-closed
check：未通过 ✗（4 项）
  1. …：缺少 review manifest（glob=reviews/*.manifest.json）
  2. …：无 stage=grill 的 manifest（现有 stage：（无））
  3. …：无 stage=grill-adversarial 的 manifest（现有 stage：（无））
  4. …：无 stage=building 的 manifest（现有 stage：（无））
RC=1
```
⇒ **成立**：4 项**全是「缺 manifest」**，**没有一条正文判据红**（G1 按设计由主流程在内容冻结点统一建）。

### R2-6 收敛判断 ⇒ **已收敛，可进证据与 PR** ✅

**判据**：本 change 的两条目标（① `## Open Questions` 判据 fail-open → fail-closed；
② 正文判据对**每一份** `stage=grill` manifest 逐份跑）**在代码、用例、变异、真 CLI 四个层面都成立**；
上一轮的阻塞项**已修且我独立证明修对了**；四条非阻塞**逐条真修好**；
回归面（14 攻击 + X1–X16 + 存量语料）**没有一条被改歪**；`601 passed` / `check` 4 项全对得上。
**剩下的只是措辞/注解级**（下面 3 条，**都不改变任何判定**、**都不必再开一轮**）：

| # | 遗留（**全非阻塞**） | 性质 | 建议 |
|---|---|---|---|
| **Nit-1** | 新实现在**尾随 `\n`** 的输入上与规范正则不一致（oracle=True / impl=False） | **不可达**（title 由 `splitlines()` + `.strip()` 保证无首尾空白），docstring 的「**逐输入**等价」严格说该收窄成「**除尾随 `\n` 外**」 | 改一句 docstring；或 `_is_tail_phrase` 开头加 `if remaining != remaining.rstrip(): return False` **无用**（反方向才对）——**推荐只改措辞**，别动代码 |
| **Nit-2** | `_is_tail_phrase` docstring 的「`str.isspace()` 与 `\s` 并不完全一致（如 `\x1c`）」**事实错误** | 全码点实测 **0 处不一致**；**实现两种写法都对** | 删掉/改写那半句 |
| **Nit-3** | `docs/gate.md:400` 仍写复数「含 `Open Questions` 字样」 | 与已修的非阻塞 ④ **同类**；R1 已判「泛指、不构成错」，**我同意不阻塞** | 一字改成单数，与代码/design 对齐 |
| **Nit-4**（信息） | 第二条线性用例（`（a）`×10 000）实测 **4.8 ms**、阈值 **50 ms** ⇒ 只有 ~10× 余量（慢 CI 上偏紧）。判据面仍极宽（线性 4.8 ms vs 二次退化 ~4.8 s，差 **1000×**） | 纯余量提示，**本轮未观察到抖动** | 可选：阈值抬到 0.5 s（判别力几乎不变） |

**其余口径**：
- **G7 仍是 `[ ]`** —— `§7.20` 的四个稳定锚**在任何一份被锚文档再被改动时都会重新失效**
  （我本轮核过它们**此刻是对的**）。这是设计里已写明的收尾动作，**不是我记的缺陷**。
- ⚠️ **本文件的这次重写不会让那四个锚失效**（`reviews/building-review.md` **不在**被锚的四份里）。
- `tasks.md` 的记账自洽（`592 → 601`、9 条新增与实测一致）；`grep -rn "pytest.skip" tests/` **零命中**。
- 我**没有**发现任何新的挂死 / 静默 / 假绿路径。上一轮那条「一份报告即可让 `check`（CI）与
  `guard`（本地写代码路径）**共用**的路径挂住」的**唯一入口已被堵死**：
  `src/` 里再无嵌套量词形态（`grep -rnE '\(\?:[^)]*[+*]\)[+*]'` 只命中 docstring 里的规范形态引用），
  且两条历史 O(n²)/O(2ⁿ) 路径都有**时间上界用例**钉住（变异 N1/N3 实测转红）。

---

# R1 复审（**已取代**）

> ⚠️ **本节是 R1 轮的原文，原样保留以备追溯。**
> 其 **Verdict = CHANGES_REQUESTED** 与 **Issue 1（阻塞：候选判定正则指数回溯）**
> **已被上方的 R2 结论取代** —— 阻塞项**已修并复核通过**，4 条非阻塞**已逐条落地**。
> 本节里的**行号 / 计数（`592 passed`）/ sha256 / 代码片段**均针对 **R1 时点的工作树
> （`ef8b3ab..4e5ac5c`）**，**不代表当前状态**；请以上方 `## Verdict` / `## R2 复审` 为准。

# Building Review: confirm-gate-fail-closed

> 审阅者：**独立零记忆实现审阅**（building）。判定依据 `docs/gate.md` 与 `specs/open-questions-gate/spec.md`。
> 只读：除本文件外**未改**被审 worktree 的任何文件、未 commit。所有会改状态的实验都在
> **隔离副本** `/tmp/cgf-rev`（`tar` 整棵工作树 + `rm -f .git && git init -q`）与 `/tmp/cgf-rev-old`（回退件）里跑。
> 基线：`origin/main` = **`ef8b3ab`**；被审提交 `ef8b3ab..4e5ac5c`（4 个 commit）。
> ⚠️ 本机 `main` 分支是 **`ae99256`**（落后 origin/main），故一切 diff / `check --base` 一律用 `origin/main`。

## Verdict

**CHANGES_REQUESTED**

**change 的目标全部真实达成**：`## Open Questions` 这条判据**确实**从 fail-open 变成 fail-closed，
D1–D9 **逐条**落到 `src/witnessloop/evidence.py`（唯一改动的生产文件），spec 的每条 Requirement /
Scenario 都有对应实现与用例，12 组变异我**抽验 14 组**（含我自己另造的 6 组）全部「只让对应用例转红、
还原后 sha256 一致」。作者的**两处说法**（`592 passed`、`check` 的 4 项全是缺 manifest）**独立复跑成立**；
**三处存疑**逐条核完，其中 ① 的「1 / 525」**精确复现**。

**但本 change 引入了一处新的、可达的健壮性缺陷**：新增的候选判定正则
`_OPEN_QUESTIONS_TAIL_RE`（`src/witnessloop/evidence.py:41`，用在 `:137`）是
**嵌套量词 + 可含分隔符的 `\S+`** ⇒ **指数级回溯**。触发它**不需要**标题与 Open Questions 有关
（候选判定对**每个** H2 标题都跑），**也不需要**恶意：一个连字符较多的长标题即可
（实测：45 字 / 22 连字符 ⇒ **0.36 s**；53 字 ⇒ **5.6 s**；按 2^(连字符数) 增长 ⇒ 约 70 字即分钟级）。
`check`（CI）与 `guard`（本地写代码路径的守卫）**共用**这条路径 ⇒ 一份报告即可让门禁**挂住不返回**，
而不是干净地红。这属本仓自己划定的「不许崩到入口兜底」同一类（`guard-crash-exit` 的先例），
且**是本次改动新开的面**（该正则在 `ef8b3ab` 不存在）。故不 PASS。

其余三条为**非阻塞**（文档可追性、CI 上一条守卫恒 skip、文案与判据的措辞错位），列在 Issues 里。

## Test Results

### 作者自报 ①：全量测试（独立复跑）

```
$ export PATH=/home/happy/.local/bin:$PATH
$ uv run pytest -q --basetemp=/home/happy/wl-basetemp-rev
........................................................................ [ 97%]
................                                                         [100%]
592 passed in 30.93s
```

### 作者自报 ②：`check` 的 4 项（独立复跑）

```
$ uv run witnessloop check --root . --base origin/main --head HEAD
check：基线 origin/main...HEAD，13 个变更文件，1 个 change 目录
  change：confirm-gate-fail-closed
check：未通过 ✗（4 项）
  1. openspec/changes/confirm-gate-fail-closed：缺少 review manifest（审阅证据必须「报告 + manifest」成对，glob=reviews/*.manifest.json）
  2. openspec/changes/confirm-gate-fail-closed：无 stage=grill 的 manifest（现有 stage：（无））——grill 决策记录必须有对应的审阅证据
  3. openspec/changes/confirm-gate-fail-closed：无 stage=grill-adversarial 的 manifest（现有 stage：（无））——设计阶段的对抗验证轮（grill 之后、停轮之前的证伪环节）必须有审阅证据
  4. openspec/changes/confirm-gate-fail-closed：无 stage=building 的 manifest（现有 stage：（无））——本 change 改了受管控代码，必须有实现后的独立审阅证据（review-loop）
RC=1
```

⇒ **成立**：4 项**全是「缺 manifest」**，**没有一条正文判据红**（G1 未勾、按设计由主流程在内容冻结点统一建）。

### 作者自报 ①：D9 的存量代价「1 / 525」（我**自己复算**）

```python
# 语料口径 = 四份检出的 openspec/changes/**/reviews/*.md
find /home/happy/my-agent/openspec/changes \
     /home/happy/wl-review-a/openspec/changes \
     /home/happy/wl-dryrun/openspec/changes \
     /home/happy/wl-wt/confirm-gate-fail-closed/openspec/changes \
     -path '*/reviews/*.md' -type f | wc -l
# 161 + 171 + 167 + 26 = 525   （逐份检出：161 / 171 / 167 / 26）
```

对照组**不是** `ef8b3ab`（那会把 D1/D2/D4 的效应混进来），而是**同一份新代码、只把围栏状态机短路**
（`marker = None`）的变体 ⇒ 差异**只**来自 D9：

```
D9-only effect: corpus 525 -> differing files: 1
   .../confirm-gate-fail-closed/openspec/changes/confirm-gate-fail-closed/reviews/grill-adversarial.md
     D9off(1): ['缺少 `## Confirmed Decisions` 小节']
     D9on (3): ['缺少 `## Confirmed Decisions` 小节', '缺少 `## User Confirmation` 小节', '缺少 `## Open Questions` 小节']
```

**精确命中作者的说法**：**恰好 1 / 525**，就是本 change 自己的 `reviews/grill-adversarial.md`，**1 → 3**，
**方向是多报**。子语料同样复算：

```
四份检出里全部 grill-design.md: 187 份, D9 下有差别 0          （60 / 63 / 62）
```

**是否可接受 ⇒ 可接受，不必改报告写法**：该份 manifest 的 stage 是 `grill-adversarial`，
`checkcmd.py:109-121` 调 `stage_manifest_findings_in_change` **不传** `verify_body` ⇒ `False`
⇒ 只要求「证据存在」⇒ **这 3 条根本不进 `check`**（与 `check` 的 4 项实测吻合）。
⚠️ 一处**措辞**：作者写「方向是多报」——更准确的是「**不进判据面**」（既不是多报也不是漏报）。
改动一份**只读对抗证据**去迁就一条**不作用于它**的判据，代价大于收益 ⇒ **不改**。

### 变异验证（我**抽验 14 组**；作者称 12 组）

每组：改一行实现 ⇒ 跑 `tests/test_evidence.py` + `tests/test_check_grill_evidence.py` ⇒ 只列**转红**的用例 ⇒ 还原后复算 sha256。

| 变异 | 期望的红 | 实测 | 还原 sha256 |
|---|---|---|---|
| M1 候选退回「只认逐字」 | F2/X2 + C2 红，**C1 仍绿** | ✅ 15 red：`test_an_empty_shell_plus_a_synonym_hiding_a_real_question`、`test_the_union_of_candidates_requires_the_synonym_sections_numbers`、候选判定表 5 行、`test_the_adopters_non_verbatim_report_passes`；**C1 `test_the_repos_own_two_candidate_titles_…` 确实不在红名单** | 一致 |
| M2 放松成「含 `Question`」 | A3/X6 + 判定表红 | ✅ 16 red（含 `test_code_resolved_questions_is_never_a_candidate`） | 一致 |
| M3 `setdefault` 改覆盖式 | A4 红 | ✅ 1 red：`test_sections_keeps_merging_same_titled_sections` | 一致 |
| M4 关掉围栏状态机 | D9 的 10 条全红 | ✅ 10 red | 一致 |
| M5 D8 退回 `matching[0]` | F9/X8 红、**F10 仍绿** | ✅ 2 red：`test_a_decoy_manifest_does_not_disable_the_body_judgement`、`test_an_unreadable_report_does_not_stop_the_others`；**F10 确实仍绿** | 一致 |
| M6 候选不排序 | C4 红 | ✅ 2 red（`test_candidate_set_and_findings_are_deterministic`） | 一致 |
| **M8（我另造）存在性改回 fail-open**（删 `else` 分支） | F1/F3/X1 红 | ✅ 5 red | 一致 |
| **M9（我另造）并集 → 只取逐字那个** | C2 红 | ✅ 3 red | 一致 |
| **M10（我另造）并集 → 只取排序第一** | C2 红 | ✅ 2 red | 一致 |
| **M11（我另造）缺件诊断不列标题** | X1 的第二档文案红 | ✅ 2 red | 一致 |
| **M12（我另造）结束标记不要求「其后只剩空白」** | F14 红 | ✅ 1 red | 一致 |
| **M13（我另造）结束标记不要求同字符/不短于** | F14 红 | ✅ 2 red | 一致 |
| **M14（我另造）围栏「开始」放宽成 ≥1** | 误伤本仓真实报告 | ✅ 1 red：`test_the_repos_own_two_candidate_titles_do_not_produce_findings` | 一致 |

（我另造的第 15 组 `M7` 事后判定**语义等价**、不是有效变异——它 rc=0 全绿，**不算**「用例失效」的证据，已剔除。）

### 我**自己另造的**攻击（14 条，非作者所写；全部在隔离副本里跑，`tests/test_zz_attacks.py`）

| # | 攻击 | 结果 |
|---|---|---|
| ATT-A | 攻击台自检：合格报告 ⇒ `check` PASS | ✅ PASS（排除「因为环境坏了所以全红」） |
| ATT-B | 标题 `## 悬而未决的疑问` + Q1 未确认（**走真 CLI**） | ✅ `EXIT_FAIL` + `缺少 \`## Open Questions\` 小节` |
| ATT-C | 逐字小节留空 + 真问题进 `## Design-Level Open Questions（…）` | ✅ `EXIT_FAIL` + `Q1 未经用户确认` |
| ATT-D | **诱饵 manifest**（`aaa.manifest.json` 绑合规报告，字典序在前）+ `zzz.manifest.json` 绑坏报告 | ✅ `EXIT_FAIL` + `Q1`/`Q2` 逐条报出 |
| ATT-E | 唯一的 `## User Confirmation`（含真答复）写进围栏 | ✅ `EXIT_FAIL` + 缺 UC + Q1 未确认 |
| ATT-F | 零宽空格 / 全角 `Ｏ` / 尾部 `．` / `、` 等**认不出的标题** | ✅ 全部红（无静默跳过） |
| ATT-G | 逐字标题**缩进两格** ⇒ 不是 H2 | ✅ 红（fail-closed） |
| ATT-H | `- **Ｑ1**`（全角 Q） | ⚪ 绿 —— 与**声明 3** 一致（不是写成 `Q<n>`），**已知残留**不是新洞 |
| ATT-I | 把 `## Open Questions` 整个藏进（并从）围栏 | ✅ 红（候选为空） |
| ATT-J | 结束标记写成 ` ``` extra ` | ✅ **不**算结束 ⇒ 继续吞到文件尾 |
| ATT-K | `~~~` 开、`` ``` `` 关（字符不同） | ✅ **不**算结束 |
| ATT-L | 把未确认的 `Q2` 围进**候选小节内**的围栏 | ⚪ **变绿** —— 声明 13 / Q4 第 6 类、**用户已裁定接受** |
| ATT-M | >20 字答复里带 `待拍板` | ⚪ 绿 —— 声明 12；⚠️ **边界精确在 20/21 字**（我第一版用 20 字仍红，改成 21 字才绿，与文档逐字一致） |
| ATT-N | 连字符多、无空格的长标题 | ❌ **指数回溯 ⇒ 见 Issue 1** |
| — | 20 000 组随机输入模糊测试 | ✅ 0 异常 |
| — | 空串 / 只有围栏 / `## ` 空标题 / `\x00` | ✅ 0 异常 |

**结论**：prompt 点名的六条攻击面里，**五条**（花哨标题、空小节、围栏藏示例、诱饵 manifest、
非候选小节的 `Q<n>`、同键后写覆盖）**全部按设计闭合或按声明接受**；
**唯一没闭合的是「围栏藏真问题」这一侧**——它是**声明 13 / Q4 第 6 类**明写的对称代价，
**用户 2026-10-15 已裁定接受**，且方向是**作者自伤**（要真绿得自己把问题围起来），
不是外部绕过 ⇒ 我**不**把它记为缺陷，但它确实是「藏真问题 ⇒ 变绿」这条路径的**真实存在**。

### 存量影响（用**真实现**对 `ef8b3ab` 直调全语料复算）

```
决策记录语料（四份检出里全部 grill-design.md / grill-review.md）: 194 份, 有差别 0
本仓 openspec/changes/**/reviews/*.md: 26 份, 有差别 17 份
  ⇒ 17 份**全部**是 building-review.md / grill-adversarial.md（verify_body=False，不进 check）
  ⇒ 本仓 8 份 grill-design.md **一份没变**
```

⇒ 作者「决策记录语料 194 份 ⇒ 0 份有差别」**成立**；「③ 新红 0」**成立**。

## Tasks Verification（逐条**读代码 + 实测**核实，不信勾选）

### A. 候选集合（D2/D3/D6）

| 条 | 结论 | 证据 |
|---|---|---|
| A1 判定表逐行 + M3/M-E 四条细则 + 两条副作用 | ✅ | `tests/test_evidence.py:155-184` 的 `CANDIDATE_TITLES` **22 行**逐行参数化；半角 / 连续尾括号 / 大小写 / 空括号 / 嵌套 / 双空格 / 尾冒号 / `Code-Resolved` / 带反引号**都在**。⚠️ 细项：`Open  Questions`（双空格）与 `Open Questions：` 的**「有/无附加提示」那一半没有断言**（见 Issue 4） |
| A2 正则 + 纯函数，**排序后**返回 | ✅ | `evidence.py:113-145`；A2 的排序断言 `tests/test_evidence.py:187-200`；变异 M6 转红 |
| A3 `## Code-Resolved Questions` 不是候选 | ✅ | `tests/test_evidence.py:221-230`；变异 M2 转红 |
| A4 `setdefault` 合并语义未动 | ✅ | `tests/test_evidence.py:203-218`；变异 M3 转红 |
| A5 D8：`verify_body=True` 对**每一份**跑 | ✅ | `evidence.py:336-362`；`tests/test_check_grill_evidence.py:160-235`；变异 M5 转红 |
| A6 D9：`_fence_run` + `_sections()` 围栏前置 | ✅ | `evidence.py:63-110`；10 条围栏用例；变异 M4 全红 |

### B. `grill_evidence_findings` 的正文判据（D1/D4）

| 条 | 结论 | 证据 |
|---|---|---|
| B1 完全没有该类标题 ⇒ 1 条同形 finding、无提示 | ✅ | `test_missing_open_questions_section_is_flagged_without_a_hint`（**断言 message 相等**，非「非空」）；代码 `evidence.py:269-270` |
| B2 X1：不含字样的花哨标题 ⇒ 红 | ✅ | 同上文件 `:241-247`；我的 ATT-B 走真 CLI 复现 |
| B3 含短语但不合 D2 ⇒ 红 + 列出它 | ✅ | `test_a_near_miss_title_is_flagged_and_listed`（`startswith` + 含标题串） |
| B4 X2：空壳 + 近义装真问题 ⇒ 红 | ✅ | `test_an_empty_shell_plus_a_synonym_hiding_a_real_question`；ATT-C 走真 CLI 复现 |
| B5 实现：候选为空 ⇒ 红；否则并集 | ✅ | `evidence.py:248-270` |
| B6 X7：同名两节 ⇒ 并集 | ✅ | `test_two_same_titled_sections_are_unioned` |
| B7 X8/F9：诱饵 manifest | ✅ | `test_a_decoy_manifest_does_not_disable_the_body_judgement`（**断言两条造法的 `[(path,message)]` 全等** + label 指向真报告） |
| B8 F10 两份都合格 ⇒ 0；一份读不出不影响其余 | ✅ | `test_multiple_compliant_manifests_are_not_an_error`、`test_an_unreadable_report_does_not_stop_the_others` |
| B9 X9：候选小节外 `Q<n>` 不判 | ✅ | `test_q_numbers_outside_the_candidate_sections_are_not_judged`（断言 `== []`） |
| B10 F11：真记录绑别的 stage ⇒ 0（边界钉子） | ✅ | `test_a_real_record_bound_to_another_stage_is_accepted` |
| B11 X10：非 `Q<n>` 不判 + 全角数字**会**命中 | ✅ | `test_questions_not_written_as_qn_are_not_judged` + `test_a_fullwidth_digit_is_still_matched` |
| B12 X11/F13/F14：围栏 | ✅ | `test_a_fenced_user_confirmation_is_not_a_real_confirmation`（**`len == 2`**）、`test_removing_the_fence_is_the_only_difference`、`test_a_longer_fence_…`、`test_an_unclosed_fence_…`、`test_a_closing_fence_must_have_nothing_but_whitespace_after_it`、`test_tilde_fences_…`、`test_an_indented_fence_still_opens` |
| B13 X12：20/21 字**只差长度** | ✅ | `test_the_placeholder_length_threshold_is_what_separates_these_two`；我用 20 字 vs 21 字**亲手验证边界就在 20**（与文档逐字一致） |
| B14 X13：围栏里的 `Q2` 不判（刻意接受） | ✅ | `test_a_question_inside_a_fence_is_not_judged`；我的 ATT-L 独立复现 |
| B15 X14：围栏里的 `来源:` / 整条 bullet ⇒ 多报 | ✅ | `test_a_fenced_source_line_is_not_counted`、`test_a_whole_fenced_decision_bullet_is_not_counted`，**都断言精确 message 列表** |
| B16 X15：`Non-Open Questions` 多收 + 边界反例 | ✅ | `test_a_prefix_widened_title_becomes_a_candidate`、`test_similar_but_non_candidate_titles_do_not_require_confirmation` |
| B17 X16：同键后写覆盖（**两方向**） | ✅ | `test_the_last_confirmation_line_for_a_number_wins`、`test_swapping_the_two_confirmation_lines_flips_the_verdict`、`test_two_confirmation_sections_merge_and_the_last_line_still_wins` |

### C. 不误伤（回归护栏）

| 条 | 结论 | 证据 |
|---|---|---|
| C1 本仓 `archive-awareness/reviews/grill-design.md` 真实内容 ⇒ 0 | ✅ | `test_the_repos_own_two_candidate_titles_do_not_produce_findings`；我直调复核：候选 = `['Open Questions', 'Open Questions（**只有这一条必须用户拍板**）']`，Q 并集 `{1,2}`、确认 `{1,2}` ⇒ 0 条。**且我验证了作者的注释是对的**（`:61` 的 Q1 在 `:110` 里也有 ⇒ 只认逐字时**仍绿**，故 C2 才是并集的变异钉子） |
| C2 「逐字装 Q1、近义装 Q5」只确认 Q1 ⇒ 红 | ✅ | `test_the_union_of_candidates_requires_the_synonym_sections_numbers`；变异 M9/M10 转红 |
| C3 接入方非逐字报告真实内容 ⇒ 0 | ✅（本机）| `test_the_adopters_non_verbatim_report_passes`——⚠️ **CI 恒 skip**，见 Issue 3 |
| C4 确定性（同输入两次、含反转插入序） | ✅ | `test_candidate_set_and_findings_are_deterministic`；变异 M6 转红 |

### D. 回归面

| 条 | 结论 | 证据 |
|---|---|---|
| D1 `tests/test_evidence.py` 原 9 条保持绿；`test_missing_sections_are_flagged` **无精确计数** | ✅ | 该用例 `assert findings` 一行（`tests/test_evidence.py:94-96`），无计数断言 |
| D2 `VALID_GRILL_REPORT` 仍合格 | ✅ | 全量 592 绿 + 所有依赖它的集成用例绿 |
| D3 `SHORT_GRILL` 仍**只**红 1 项 | ✅ | `tests/test_archive_awareness.py:425` `assert len(findings) == 1` 且断言 `少于硬门槛 3 条`——**精确计数**，通过 |
| D4 `test_manifest_build` / `test_check_protected` / `test_events*` 全绿 | ✅ | 全量 592 绿 |
| D5 全量 | ✅ | **592 passed**（见上） |

### E. 产出方

| 条 | 结论 | 证据 |
|---|---|---|
| E1 `templates/grill.md`：逐字 + 为空也保留 | ✅ | 模板 diff `templates/grill.md:118-122`（「标题必须逐字…即使没有待定问题也要保留该小节」），**未新增小节**（结构块 `:107` 已在产出它） |
| E2 硬约束 ③ 补「小节必须逐字存在」 | ✅ | `templates/grill.md:216` |
| E5 结构块补 `## User Confirmation` | ✅ | `templates/grill.md:114-116` |
| E3 **复核不改** `plugin/commands/grill.md` | ✅ **结论成立** | `git diff ef8b3ab..HEAD -- plugin/` **空**；`plugin/commands/grill.md:27` 的 `## Open Questions` 在**行内 code span、且行首是列表标记 `6.`**，`:29` 前有 **3 空格缩进** ⇒ `_HEADING_RE`（`^##\s+`）**两条都匹配不上** ⇒ 既不自造红、也无第二种措辞可订正 |
| E4 改模板前跑 `test_docs.py` / `test_templates.py` | ✅ | 全量 592 绿（两文件在名单内） |

### F. 文档

| 条 | 结论 | 证据 |
|---|---|---|
| F1 `docs/gate.md §8` 补存在性 + 候选口径 | ✅ | `docs/gate.md:393-402` |
| F2 补 CQ2 补救姿势（追加逐字小节、不动原文） | ✅ | `docs/gate.md:408-411` |
| F3 `README.md` 补「小节必须逐字存在」 | ✅ | `README.md:171-175` |
| F4 改文档前读 `test_docs.py` | ✅ | 全量绿 |

### G / 「明确不做」

- G1（三份 manifest）/ G4（review-loop）/ G5（PR）/ G6 / G7 在 `tasks.md` 里**仍是 `[ ]`**（`tasks.md:180-217`）
  ⇒ 我**不**把未勾项当缺陷；本题的产物就是 G4。
- 「明确不做」清单**逐条核对未被顺手做掉**：`## Confirmed Decisions` / `## User Confirmation` 口径未动
  （`evidence.py:225-246` 与 `ef8b3ab` 逐字相同）；`_sections()` 签名与合并语义未动（A4 钉住）；
  无 `design_hash`；未跨仓改接入方报告；未禁止同 stage 重复 manifest。
- `tests/test_confirm_gate_docs.py`（**12 条**，`--collect-only` 实测）**不是**被改出来的软守卫：
  `_change_dir()` **找不到就 fail 不 skip**（`:101-105`），失败信息**响亮**。

## Issues

### 1（**阻塞**）候选判定正则**指数回溯** ⇒ `check` / `guard` 可被一份报告挂住

`src/witnessloop/evidence.py:41`
```python
_OPEN_QUESTIONS_TAIL_RE = re.compile(r"^(?:\S+[- ])*Open Questions$")
```
用在 `src/witnessloop/evidence.py:137`（`_is_open_questions_title` 的返回）。`[- ]` 本身**也**是 `\S`
⇒ 每个连字符都是 `\S+` 的合法切点 ⇒ **2^(连字符数)** 条回溯路径。这是经典的 `(a+a)*` 形态。

实测（`/tmp/cgf-rev/.venv/bin/python`，直调真函数）：

```
连字符  8（标题 17 字）: 0.0000s
连字符 16（标题 33 字）: 0.0050s
连字符 20（标题 41 字）: 0.0810s
连字符 22（标题 45 字）: 0.3457s
连字符 26（标题 53 字）: 5.6104s      # 每 +1 连字符 ≈ ×2
```

**触发不需要与 Open Questions 有关**——`_open_question_sections`（`evidence.py:140-145`）对**每个**
H2 标题都调它：

```
与 Open Questions 无关的 H2 标题 x-x-…-x（45 字，22 连字符）
  grill_evidence_findings 耗时 0.361s
```

**影响面**：`checkcmd.py:94`（CI / 事后）与 `guardcmd.py:112`（本地 / 事前写代码路径）**共用**这条路径
⇒ 一份报告即可让 CI 的 `check` **不返回**（job 超时、合不了）、让本地 `guard` **把写操作挂住**。
方向**不是**放行（不是 fail-open），而是**拒绝服务 / 挂起**——但它与本仓已立的标准同类：
`guard-crash-exit` 那一次就是因为「崩溃出栈」被当成缺陷修的，而**挂起比崩溃更坏**
（崩溃有出口码，挂起没有）。

**为什么是本 change 的新面**：该正则在 `ef8b3ab` **不存在**（`_is_open_questions_title` 是本 change 新增）。
存量语料**不受影响**（我扫了全部 525 份的**每一个** H2 标题，最慢 0.0008s）。

**修法方向（一行，且更贴 spec 文字）**：spec 的原话是「`Open Questions` 是**结尾短语**，其前只允许
空格 / 连字符分隔的**词**」（`spec.md:38-39`）——「词」不应含连字符，故把词部收紧成
**不含分隔符**的字符类（等价形态：`[^\s-]+` 代替 `\S+`，或用原子组 / 占有量词）即可消除回溯，
且对判定表 22 行**逐行结果不变**（`Design-Level` 这类词由 `[^\s-]+` + `[- ]` 两段自然吃下）。
⚠️ 改完请**重跑判定表**（`tests/test_evidence.py:155-184`）与全量 592 条——本仓对「顺手放松/收紧」
的口径极敏感，这类改动必须有用例背书。

**建议加的钉子**：一条「长连字符标题必须在常数时间内判完」的用例（`time.perf_counter` 上界），
否则这条面下次仍会静默回来。

### 2（非阻塞 · 可追性）`design.md §7.20` 的「本轮稳定锚」已经**整块失效**，且它的标签自相矛盾

`openspec/changes/confirm-gate-fail-closed/design.md:1216`（表行）写
「**本轮（R8 整合稿）** … 见下面那份「本轮稳定锚」」，而 `:1221` 那份块标的是
「**本 R3 整合之后**实测」——**表行与块的标签互相打架**（R4–R8 都加了表行，没人刷新块）。

更要紧的是**四个值现在全对不上**（我逐个 `sha256sum` 复算）：

| 文件 | `§7.20` 块里写的 | 实测（`4e5ac5c` 工作树） |
|---|---|---|
| `proposal.md` | `f3bd55c0…` | `b9d5d497…` |
| `tasks.md` | `720711fe…` | `0129b1ea…` |
| `specs/open-questions-gate/spec.md` | `4dbcbcea…` | `ba3782c1…` |
| `reviews/grill-design.md` | `0b6fb06f…` | `85fb8e33…` |

⇒ 这**不是**作者自报的「只有 `tasks.md` 一处」：`grill-design.md` 变是因为 **G3 把用户裁定
追加进 `## User Confirmation`**（这一处**该**变，是设计的预期动作），`proposal` / `spec` 也变过。
**后果**：`§7.20` 现在**回答不了**它自称要回答的问题（「哪一稿被审过」）。
**是否让某条守卫失去意义 ⇒ 没有**：`tests/test_confirm_gate_docs.py` **不读**指纹值
（它自己写明「四个模式之外的任何计数：… §7.20 指纹表的行数 —— 结构变了它们不会自动报」，`:38`），
`test_loose_caliber_identity` 只按正则**数行**（`^\| R\d+ (?:对抗|复审) `），而
`grill-design.md` 的 sha256 也**没有**被任何测试钉住 ⇒ **没有守卫因此失效**，只是追不了链。
**落点**：`tasks.md:210-216` 的 **G7**（仍是 `[ ]`）就是为此写的 ⇒ 建议 G7 收尾时
**既补一行表行、也把那块刷新并改准标签**（或干脆把块改成「每次收尾重算」的公式化写法，
别再让标签与表行各说各话）。

### 3（非阻塞 · 与仓库自己的口径冲突）接入方 fixture 用绝对路径 ⇒ **CI 上恒 skip**

`tests/test_evidence.py:557-562`：
```python
path = Path("/home/happy/wl-review-a/openspec/changes/archive/2026-09-30-workflow-dry-run"
            "/reviews/grill-design.md")
if not path.is_file():
    pytest.skip(f"接入方检出不在本机：{path}（CI 无此 fixture）")
```
- **skip 本身不算「过宽」**：条件只有「这个绝对路径不在」一条，失败信息**点名路径**，不是静默吞。
- **但它在 CI 上恒 skip**，而本仓**自己的书面标准**明确否掉这种做法
  （`tests/test_confirm_gate_docs.py:90-93`：「`skip` 在 CI 上表现为 `N skipped` + `rc=0`
  （**静默绿**）——**一个能静默消失的守卫比没有守卫更坏**」）。
- **代价可量化**：我实测这条用例**不是花瓶**——变异 M1（候选退回「只认逐字」）下它**转红**
  （`test_the_adopters_non_verbatim_report_passes`），即它承担着一个**真实的变异钉子**；
  CI 上这条钉子**完全没有替代品**。
- **本仓自己的护栏仍被覆盖**（这是我判它非阻塞的理由）：C1（本仓真实报告）+ C2（构造的并集钉子）
  + 22 行判定表 + `test_similar_but_non_candidate_titles_do_not_require_confirmation` 都在 CI 上真跑。
- **建议**：把那份报告的**内容**冻成 `tests/fixtures/*.md`（⚠️ **别**放进本 change 的
  `openspec/changes/<id>/reviews/`——那会触发 `contract._check_orphan_reports` 的孤儿报告红），
  用例读 fixture ⇒ 该钉子在全平台生效。

### 4（非阻塞 · 措辞）提示文案的**子串**与**筛选口径**错位一处

`src/witnessloop/evidence.py:44-47` 的文案写「检测到含 `` `Open Questions` `` 字样的标题」，
而筛选条件是 `evidence.py:159` 的 `"Open Question" in title`（**单数、且大小写敏感**）。
⇒ 一个含 `Open Question` 但**不含** `Open Questions` 的标题（如 `## Open Question Archive`）会被列出，
但文案声称它含的是 `Open Questions`。`spec.md:140` 写的是**单数**（`Open Question` 字样）
⇒ **代码对、文案偏**。纯 UX，不影响任何判定；顺手把 `_OPEN_QUESTIONS_HINT` 的
「`Open Questions` 字样」改成「`Open Question` 字样」即可。
（`docs/gate.md:395-396` 与 `templates/grill.md:120-121` 有同源的「含 `Open Questions` 字样」表述，
但那两处的语境是给作者看的泛指，不构成错。）

### 5（非阻塞 · 可选）两条已知副作用的「提示有/无」没有用例钉

`tasks.md:39` 的 A1 末句要求 `Open  Questions`（双空格）与 `Open Questions：`（尾部全角冒号）
各有一行；`tests/test_evidence.py:173-174` 只钉了**「非候选」**这一半，
**「前者无提示 / 后者有提示」**这一半（`design.md:256-257`、`spec.md:58-61` 明确写了两者不同）
**没有断言**。我直调复核**行为与文档一致**，但这条面**没有钉子** ⇒ 将来有人改宽 `near` 的筛选
不会红。建议各补一行断言（与 B1/B3 同款）。

## 三处存疑的核查结论

| # | 作者自报 | 我的复核 |
|---|---|---|
| ① | D9 让 525 份里**恰好 1 份** finding 数变化（自己的 `grill-adversarial.md`，1→3，方向多报；`verify_body=False` ⇒ 不进 `check`） | ✅ **精确复现**（见上；对照组是「新代码但关掉围栏」的同源变体，隔离干净）。**可接受**（不进判据面；改一份只读对抗证据不值得）。⚠️ 措辞建议：「多报」→「**不进判据面**」 |
| ② | 接入方 fixture 用绝对路径 ⇒ CI 无检出、该条显式 skip | ✅ 条件**不宽**、信息**响亮**；⚠️ 但**在 CI 上恒 skip**，且本仓自己的书面标准否掉 skip ⇒ 见 **Issue 3**。本仓侧护栏（C1/C2/判定表）**仍被 CI 覆盖** ⇒ 非阻塞 |
| ③ | `tasks.md` 勾选改了四份文档之一，`design.md §7.20` 指纹未更新 ⇒ 是否让某条守卫失去意义 | ✅ **没有守卫失去意义**（守卫不读指纹值，docstring `:33-46` 自己写明；`grill-design.md` 的 sha256 也没被任何测试钉住）。⚠️ 但比自报的**更严重**：**四份里的四份**锚值全对不上、且块的标签（R3）与表行（R8 整合稿）**自相矛盾** ⇒ 见 **Issue 2**。落点是仍为 `[ ]` 的 **G7** |

## 结论

- **目标达成**：`## Open Questions` 判据的 fail-open **确实**被堵死（标题写花 ⇒ 红；空壳 + 近义装真问题 ⇒ 红；
  诱饵 manifest 不再能让正文判据整段失效；围栏里的示例不再充当真确认）。D1–D9 **逐条**有实现、有断言、
  有变异证据。**Spec 的每条 Requirement / Scenario 我逐条对到了实现与用例**（含 15 条边界声明：
  声明 1/2/3/4/5/6/7/11/12/13/14/15 我都独立构造了输入复现其方向，结论与文档一致）。
- **回归面干净**：`592 passed`；决策记录语料 194 份 **0 差异**；本仓 8 份 `stage=grill` 报告 **0 新红**；
  `check` 的 4 项**全是缺 manifest**。
- **阻断项只有一条**：**Issue 1**（新增正则的指数回溯 ⇒ 门禁可被挂住）。它**不影响**本 change 的语义正确性，
  但**必须修**——它是本 change 新开的面、修法一行、且属于本仓已立标准的同一类。修完（+ 一条时间上界的钉子）
  即可 PASS，其余 4 条按各自建议顺手处理即可，**不阻塞**。
