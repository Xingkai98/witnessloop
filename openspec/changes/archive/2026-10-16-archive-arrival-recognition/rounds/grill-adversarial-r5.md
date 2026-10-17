# 对抗轮 R5（独立零记忆验证者）—— `archive-arrival-recognition`

> 结论摘要：**不收敛**。R4 的 4 条「文档级必须修改项」**已全部落库**（M5/M6 两条低危项部分落），
> 但本轮独立复算发现 **2 条新的、可复算的、影响判红判绿的证伪项**：
> **①判据 5 的 (a) 对符号链接（mode `120000`）失明**、**②D4 的排除条件把「搬一个文件 + 删除其余」当成「整体搬走」**。
> 两条都**不是**「比已接受的逐字节天花板（§8 Q4(c)）更便宜」的安全级绕过（这一点是负面证据），
> 但都落在设计**自己声称要挡**的类里，且各有零成本的最小复现。

---

## Reviewer

**零记忆声明**：本对话不携带该 change 的任何历史。前四轮（`grill-design.md` / `grill-adversarial.md` /
`-r2.md` / `-r3.md` / `-r4.md`）的结论**只当待复核的声明**；设计稿里的「实测」「`文件:行号`」一律当**待验证断言**。
判据模拟器 `/tmp/r5sim.py` 由我从零写成（**未**沿用 `/tmp/r3sim.py` / `/tmp/r4sim.py` 的判据逻辑，
只读了 `design.md` / `spec.md` 正文与 `src/` 源码做事实核对）。只写 `reviews/` 下这一个文件，未改任何 `src/` / `tests/` / 文档。

**读过的**（当前 HEAD `5e6fbf0`）：
`proposal.md` / `design.md`（680 行）/ `tasks.md` / `specs/archive-awareness/spec.md`（335 行）；
源码 `contract.py` / `checkcmd.py` / `gitutil.py` / `policy.py` / `paths.py` / `constants.py` / `evidence.py` /
`hashing.py` / `manifestcmd.py`；`tests/test_archive_awareness.py`（抽查 8 处行号）。

**跑过的**：
- `/tmp/r5sim.py`（我的独立模拟器，只读 git 树）在 `/tmp/cases/*`（18）+ `/tmp/r3cases/*`（8）+ `/tmp/r3cases2/*`（18）+
  `/tmp/r4cases/*`（11）**全部 55 个既有构造**上复算（基线 `main` / head `feature`，`t577` 用 `touching`）；
- 自建 10 个新构造（`/tmp/r5cases/*`）：`pmd_valid`（D4 缺陷，完整版）、`partial_move_delete`、`pmd_invalid`、
  `symlink_ev`、`symlink_gate`、`symlink_gate2`、`e11_proper`、`e12_copy`、`n12_del_one`
  （`e11_stub_ok` / `symlink_gate` 为中间产物）；
- **真 CLI**（今天的实现，`.venv/bin/python -m witnessloop check` / `manifest build`）跑在自建构造上，
  取「今天红 / 绿」的原始输出（见 A1 / A4）。

---

## R4 四条落库复核

> R4 的编号是 `M1`–`M6`；任务书说的「4 条文档级必须修改项」= `M1`（spec 伪等价）/`M2`（计数）/
> `M3`（完全旁路机理写窄）/`M4`（到达组定义），`M5`（措辞指针）/`M6`（建议）为低危附项。逐条核如下。

| # | R4 要求 | 状态 | 证据 |
|---|---|---|---|
| **M1** | `spec.md` 删掉「等价于自己写一份完整证据」这条伪等价论证 | **已落** | `grep -n "等价于「自己写一份完整证据」" design.md specs/archive-awareness/spec.md` ⇒ 只剩 `spec.md:71`（**SHALL NOT 写成**…R3 已证伪，转指 `design.md §D1`）、`design.md:163`（「那是错的」订正句）、`design.md:562`（历史处置表）。**没有**残留的断言式用法；spec 内部不再自相矛盾（`:71` 与 `:70-78` 的能力天花板段一致）。 |
| **M2** | 「必须改写」的计数与实列对齐（两处：§5.2 标题 / §4 风险表） | **已落** | `design.md:409` 标题「（**5 条**；改前绿是**旧语义**下的绿）」；`design.md:356` R5 行「**必须改写**（**5 条**）与**不要误改**（**3 条**）」；实列恰 5 项（`design.md:410/414/421/428/432` → `:274`/`:494`/`:600`/`:109`/`:49`），逐条核对 `tests/test_archive_awareness.py` 行号**全部命中**（`274`,`494`,`600`,`109`,`49` 与我 `sed -n` 读出的一致）；「不要误改」恰 3 项（`:541`/`:577`/`:378`，行号亦命中）。`design.md:568` 的历史行也同步改成「标题写 5 条、清单恰列 5 项」。 |
| **M3** | 「完全旁路」写明「分句 (a) 单独即豁免、与 `git mv`/`cp` 无关」 | **已落** | `design.md:183-188`：「那些字节**落在 `<changes_root>` 之外 ⇒ 分句 (a) 单独即豁免**，**与是 `git mv` 还是普通 `cp` 无关、也不需要任何 rename 记录**（实测：`a4b` 的 10 份文件 blob **0/10** …；普通 `cp` 的 `i5` 构造同样 `arrived=True`）」；`spec.md:79-82` 同步。 |
| **M4** | 把「到达组」的定义写死（design / spec / tasks 三处） | **已落** | `design.md:73-74`（术语段）、`spec.md:22-23`（术语段，含 SHALL）、`tasks.md:130`（3.2 括注「**到达组** = `new_path` 落在该目录下的记录集合」）。三处口径一致。 |
| M5① | `design.md` R7 行的「重写」→「至少动一个字节」 | **未落** | `design.md:358-359` 仍是「必须**每一份**被复制的证据文件都**重写**（或改成 `git mv`）」，与 `§D1` 的天花板（每份 +1 字节即可绕）措辞冲突。⇒ 见「措辞项 1」。 |
| M5② | `design.md:556` 的「（§3 第 5 条）」补模板项 | **部分落** | `design.md:567`（B3 行）现指「`§D1 第 5 条「已知边界」` + `§3 第 5 条` + `tasks.md 6.1`」：`§D1` 侧**有**（`design.md:193-194` ✅）、`tasks.md:171` **有** ✅，但 **`§3` 第 5 条**（`design.md:335-338` 的 `docs/gate.md` 更新清单）仍**没有**「模板放 `changes_root` 之外」这一项 ⇒ 该指针仍半悬。⇒ 见「措辞项 2」。 |
| M5③ | `§5.3` 表按编号排序 | **已落** | `design.md:449-469` 现为 `N1`→`N21` 顺序（`N19`/`N20`/`N21` 不再插在 `N11` 与 `N12` 之间）。 |
| M6 | （建议）`Ev(A)` part 3 与 part 2 口径对齐 + 补「空 / `.` artifact 名不参与判据 2」 | **已落** | `design.md:107-109` 明写 part 3「**刻意与 `policy.review_manifest_glob` 无关**（固定的兜底面）…自定义 glob 本就不可用」（引 `manifestcmd.py:136-142,201`）；`design.md:87-88` 补了「实现 SHALL 忽略**空串 / `.`** 这类退化 artifact 名…R4 实测 `required_artifacts: [""]` 只**多报红**」。⚠️ 但 spec 一侧未同步 ⇒ 见「措辞项 3」。 |

**小结**：4 条必须修改项**全部落库**，且我逐条做了机械核对（不是读作者的自我声明）。
R4 的两条低危附项（`M5①` 措辞、`M5②` 指针）**未完全落**——两者都不影响判据语义。

---

## 独立证伪

### A. 找绕过

**A0（先给负面证据）**：本轮**没有**找到「比 `§8 Q4(c)` 已接受的逐字节天花板更便宜」的绕过。
我的模拟器复算了 R4 判定为绕过成功的两个构造，结论与 R4 一致（完全旁路成立），
其余 30 余个搬运/改名构造全部 `arrived=False`。下面 A1 / A4 是**新**发现，但两者都**弱于**已接受的天花板
（A1 只能借到 `tasks.md` / `specs`，报告借不到；A4 不产出新绕过、只让一个 active change 静默消失）。

---

#### A1【新，低危，可复算】判据 5 的 (a) 对**符号链接**（mode `120000`）失明 ⇒ 「零改动复用现成证据」不判红

**机理**：`design.md:94-98` / `spec.md:44-48` 把 (a) 定义成「其 **blob** 在基准树的 `<changes_root>/**` 里不出现
（= 本次新写的内容）」，`design.md:99-107` 又把 `Ev(A)` 钉成「**按 head 树**」取。而 git 把符号链接存成
**mode `120000` 的 blob，内容是链接文本**（实测：`git ls-tree -r feature -- <A>` 里 `tasks.md` 是
`120000 blob 00ba5c40…`，其字节是 `../2026-09-30-old/tasks.md` 这一串路径，而不是被链接文件的内容）。
⇒ 只要把 A 的证据文件做成指向**仓内任一现成证据**（含 `<changes_root>` **之内**）的符号链接，
(a) 就成立，而**一个字节都没有改动、也没有任何 `cp`**。

**最小复现**（构造 `/tmp/r5cases/symlink_ev`，脚本见文件头注释；三步）：

```bash
cd /tmp/r5cases/symlink_ev
# ① A 的四份证据是符号链接（120000），目标是基准树里现成的归档 change
git ls-tree -r feature -- openspec/changes/archive/2026-10-15-new
#   120000 blob 00ba5c40…  …/2026-10-15-new/tasks.md
#   120000 blob 7dcedfeb…  …/2026-10-15-new/specs
#   120000 blob a511b39a…  …/2026-10-15-new/proposal.md
#   120000 blob 6b264b87…  …/2026-10-15-new/design.md
# ② 链接目标的内容与老 change 的证据逐字节相同（用的是 sha256_tree 本体，跟随符号链接）
python3 - <<'PY'
import sys; sys.path.insert(0,'/home/happy/wl-wt/archive-arrival-recognition/src')
from witnessloop.hashing import sha256_tree
A='/tmp/r5cases/symlink_ev/openspec/changes/archive/2026-10-15-new'
O='/tmp/r5cases/symlink_ev/openspec/changes/archive/2026-09-30-old'
for f in ('tasks.md','specs'):
    print(f, sha256_tree(f'{A}/{f}')==sha256_tree(f'{O}/{f}'))
PY
#   ⇒ tasks.md True / specs True（06ebf537… / 01c09e65…）
# ③ 我按现稿文本转写的模拟器：判据 5 零命中，A **是**到达
python3 /tmp/r5sim.py . main feature -v
#   ⇒ 2026-10-15-new: c1=True c2=True c3=True c4=True srcs=[] c5=True arrived=True
```

**对照（同一份内容，换成 `cp` 就被拒）**：`/tmp/cases/r19_copy_specs_as_file`、`/tmp/r3cases2/a3b_specs_file_pristine`、
`/tmp/r3cases2/a5_tasks_as_dir` 在我的模拟器上全部 `arrived=False`（命中项就是那份被复制的 `specs`/`tasks.md`）。
⇒ **同一份「借来的证据」，`cp` 会被拒、`ln -s` 全过**。

**「证据门那一半」也是绿的**（这是关键补强）：符号链接结构能通过**完整**的证据门——
把同一结构做成 **active** change 后跑今天的真 CLI 是**全绿**的（`/tmp/r5cases/symlink_gate2`，其
`tasks.md` / `specs` 也是 `120000` 符号链接）：

```bash
cd /tmp/r5cases/symlink_gate2
/home/happy/wl-wt/archive-arrival-recognition/.venv/bin/python -m witnessloop check --root . --base main --head feature
#   check：基线 main...feature，4 个变更文件，1 个 change 目录
#     change：z
#   check：**通过 ✓**   （exit=0）
# 证据实体确认：
#   z/tasks.md 内容哈希 = 06ebf537…  ==  archive/2026-09-30-old/tasks.md 内容哈希
#   z 的 tasks.md / specs / proposal.md / design.md 在树里都是 120000
```

（D2 声明归档 target 与 active 走**同一套**证据门 ⇒ 上面这条对到达目录同样成立。）

**这条能走多远（诚实划界，别夸大）**：
- **借得到**：`tasks.md`、`specs/**`（`Ev(A)` part 1 的两条 artifact 路径），以及 `proposal.md`/`design.md`
  （它们本就不在 `Ev(A)` 里）。
- **借不到**：三份审阅报告。报告必须被某份 manifest 的 `report_path` 引用，而
  `contract.resolve_report_path`（`contract.py:282-300`）用 `Path.resolve()` 展开符号链接并要求落在 change 目录**内**
  ⇒ 指向外面的报告链接**实测返回 `None`**（`resolve_report_path(A,'reviews/link.md') ⇒ None`）；
  若改成「真文件原样复制」则 blob 与 base 相同 ⇒ 判据 5 part 3 命中（`e12_copy` 实测 `arrived=False`）。
  三份 manifest 也必须自写（借来的 manifest 里 `change_id` 不匹配、`report_path` 也解析不到）。
- **与已接受天花板的关系**：逐字节天花板（每份证据 +1 字节）能借到**全部**证据、代价同量级
  ⇒ A1 **严格弱于**已接受的那一档。所以它**不是**「更便宜的新绕过」；
  它的价值在于**它落在判据自己声称要挡的「零改动」那一格里**（`spec.md:67-69` / `design.md:167-169`
  「挡零改动 / 只动一处的机械搬运」），却被漏掉；而且**封堵成本极低**（见「必须修改项 1」）。
- **顺带证伪的一句**：`design.md:183` / `spec.md:79-80` 写的「判据 5 的效力**完全依赖**
  「`<changes_root>/**` 是存放 change 证据的唯一地方」这一前提」**不成立**——
  在「changes_root **就是**唯一存放地」的前提下（本构造正是如此），判据 5 照样被绕过。

**试过但没成功的相关变体**（写清失败点，免得后来者重复）：
① 用**符号链接借报告** ⇒ `resolve_report_path` 返回 `None` ⇒ 红（`contract.py:296-300` 的 `is_within` 拦下）；
② 用**硬链接**借任何文件 ⇒ git 里就是普通 blob（内容相同）⇒ 判据 5 (a) 命中 ⇒ 红；
③ 借**符号链接型 manifest** ⇒ `change_id` 不匹配 / `report_path` 解析不到 ⇒ 红；
④ 让 `A/specs` 成为目录、逐文件符号链接 ⇒ 与 ①(A/specs 整体链接) 同一结论（part 1 取「是目录 ⇒ 其下全部文件」，
每个文件仍是 `120000`）⇒ 同样过。

---

#### A4【新，中低危，可复算】D4 的排除条件与它自己声明的原则**不自洽**：active change 可被「搬一个文件 + 删除其余」静默抹掉

**设计原文**：
- `design.md:244-245`：「排除条件加一条**目录级事实**：**该记录的源 change 目录在 head 树里已不存在**
  （**= 那个 change 整体搬走了**；它才是那个被归档的 change）。源目录仍在 head 里 ⇒ **不排除** …
  （**部分搬走的目录必须被问话**）。」
- `spec.md:238-240` 同口径；`spec.md:311`（回归护栏）「**删除** change 目录（非 rename）SHALL 仍报「change 目录不存在」」。

**我的构造（`/tmp/r5cases/pmd_valid`，17 个变更文件）**：
base 里有一个 active change `x`（`proposal/design/tasks/specs/reviews` 齐 + `notes.md`）；
head 里 ① 新建**件齐**的 `openspec/changes/archive/2026-10-15-x/`（内容全新，走出生即归档）、
② 把 `changes/x/notes.md` **`git mv`** 进新目录（纯改名 ⇒ 到达组因此把 `x` 认成「源」、判据 4 也被 `-x` 后缀满足）、
③ 把 `changes/x/` 的**其余四份文件全部删除**、④ 改 `src/app.py`。

```bash
cd /tmp/r5cases/pmd_valid
git diff --name-status -M main...feature
#   A  …/archive/2026-10-15-x/{proposal.md,design.md,tasks.md,specs/cap/spec.md,reviews/*}
#   R100 changes/x/notes.md → archive/2026-10-15-x/notes.md
#   D  changes/x/{proposal.md,design.md,tasks.md,specs/cap/spec.md,reviews/grill-review.md}
#   M  src/app.py

# 今天（真 CLI，HEAD=5e6fbf0 的实现，未改一行源码）：
/home/happy/wl-wt/archive-arrival-recognition/.venv/bin/python -m witnessloop check --root . --base main --head feature
#   check：基线 main...feature，17 个变更文件，2 个 change 目录
#     change：x, 2026-10-15-x（归档）
#   check：未通过 ✗（5 项）   exit=1
#     1. openspec/changes/x：change 目录不存在（diff 里出现了它的文件，但目录不在工作树中）
#     2. openspec/changes/x：缺少 review manifest…
#     3-5. openspec/changes/x：无 stage={grill,grill-adversarial,building} 的 manifest…
#   ⚠️ 对 `2026-10-15-x` 本身**零 finding** ⇒ 那个到达目录已经满足**完整**证据门。

# 新设计（我按现稿文本转写的模拟器）：
python3 /tmp/r5sim.py . main feature -v
#   ⇒ 2026-10-15-x: c1=True c2=True c3=True c4=True srcs=['x'] c5=True arrived=True
#   ⇒ active_ids=[]        ← `x` 从 active 集合里**静默消失**，那 5 条 finding 一条都不会再出现
```

**为什么这是可证伪项**：`design.md:244-245` 把「源目录在 head 里已不存在」**等价**成「那个 change **整体**搬走了」。
本构造里源目录确实不存在，但它**没有**整体搬走——只搬走了 1 份 `notes.md`，另外 4 份证据是**被删除**的
（A 里那 4 份是另写的内容）。⇒ 那句等价为**假**；`design.md:245` 自己写的原则「部分搬走的目录**必须**被问话」
在这个构造上被违反（它恰恰是「部分搬走」，却被排除掉、不再被问话）。

**为什么值得改（而不是纯措辞）**：这是一条**今天红 → 改动后绿**的行为差异，且**没有任何用例/边界条目覆盖它**：
`spec.md` 的「有意的行为变化」清单（`spec.md:322-325`）只登记了「复制式归档」一条；
`§5.3` 的 N1–N21 里没有这一形态；`spec.md:332-336` 的 Scenario（删掉 change 目录 ⇒ 仍红）的 **Given**
写的是「整个删除（`D`，不是 rename）」⇒ 本构造恰好绕开了那条 Given。

**能走多远 / 走不到哪**（诚实划界）：
- 攻击者**必须**仍然交付一个**完整有效**的到达 change（判据 1–5 + 全套证据门），否则到达不成立、
  `x` 不会被排除（**fail-closed，实测**：`/tmp/r5cases/pmd_invalid`（到达目录件不齐）⇒ `arrived=[]`、`active_ids=['x']`）
  ⇒ 所以它**不能**用来「零证据落代码」，只能用来「让另一个 active change 的证据**被删除**而不被问话」。
- **没有干净的收窄办法**（这点很重要，别让作者白花时间）：我试过三种收窄，全部会误伤 `§5.1 2b` 想绿的形态
  （`git mv` + 把 `tasks.md`/`specs` **整体重写** ⇒ git 报 `D`+`A`）：
  ① 「`D` 侧路径只有在 `<A>/<相对路径>` 也在 head 里才排除」——本构造里 A 是**件齐**的 change，
     `proposal.md`/`design.md`/`tasks.md`/`specs` 的相对路径**本来就都在** ⇒ 照样漏；
  ② 「源 change 的每一份证据文件都要有落点」——同理（件齐的 A 天然覆盖全部相对路径）；
  ③ 「要求被搬文件逐字节相同」——会把 `§5.1 2b`（重写）判红，与设计**明写想支持**的形态冲突。
  ⇒ **只能靠内容判据**（而内容判据正是 `§8 Q4` 已裁定不做的那条路）。
- ⇒ 因此我的建议是：**把它明写成一条「有意的行为变化 / 已知边界」并配一条用例钉住**（见「必须修改项 2」），
  同时把 `design.md:244-245` 的等价句改成准确的条件句。

---

### B. 找假阴性 / 误伤

- **B1 复核 `E11`（「必须绿」：新 change 的 `proposal.md`/`design.md` 与 base 某 change 逐字节相同 ⇒ 绿）**：
  R4 时代留下的 `/tmp/r3cases2/e11_stub` **构造无效**（该目录**缺 `reviews/`** ⇒ `c2=False`，根本没走到判据 5）。
  我另建 `/tmp/r5cases/e11_proper`（只共用 `proposal.md`/`design.md`，`tasks.md`/`specs`/报告全新）⇒
  `arrived=True` ✅ **design 的断言成立**。
  ⚠️ 附带确认：若**连 `tasks.md` 也**逐字节共用，则 `arrived=False`（我的 `e11_stub_ok` 命中 `tasks.md` 一份）
  ——这正是 `design.md:177` 已登记的误伤面③（「被原样复制的 `tasks.md` 样板」），**不是**新问题。
- **B2 复核 `E12`（明写的误伤面：原样复制兄弟 change 的 `specs/**` ⇒ 红，且**只点名该文件**）**：
  `/tmp/r4cases/e12_sibling_spec_copy` ⇒ `arrived=False`，命中项**只有** `specs/limits.md` ✅；
  我自建 `/tmp/r5cases/e12_copy`（`cp` 兄弟的 `specs/cap/spec.md`）⇒ 命中项含 `specs/cap/spec.md` ✅。
- **B3 组织型子目录两形态**（`§5.3` N16/N17）⇒ 都不是 target、都报「没有任何 change 目录」✅
  （`r12_org_dir` / `r15_org_dir_with_reviews` 与我的 `pmd_*` 同结论）。
- **B4 空文件豁免**（`§5.1` 第 13 条）⇒ `/tmp/r4cases/empty13_gitkeep` `arrived=True` ✅。
- **B5**：我**未能**构造出新的假红。逐条检查了「`renameLimit` 截断」（纯 move 都是 **exact rename**，
  不受 `-l` 限制 ⇒ `design.md:321` 的 C7 成立）、「move 内带内容改动」（`r7`/`m1`/`m3` 全绿）、
  「base ref 前进过」（基准取 `merge-base`，与 `changed_files` 同源 ✅）。

---

### C. 判据逐条（`§5.3` N1–N21 + `§5.1` 第 1–14 条，我的独立复算）

| 构造 | 期望（现稿） | 我的复算 | 一致？ |
|---|---|---|---|
| N1 只改 `src/**` | 红 | 无 target（`active=[]`、无到达） | ✅ |
| N2 改已存在归档目录（`M`） | 红 | `/tmp/r4cases/t577_touch_existing_archive`（head=`touching`）⇒ 无到达 | ✅ |
| N3 往已存在归档目录新增（`A`） | 红 | `r10_preexisting_plus_file` ⇒ `c1=False` | ✅ |
| N4 单文件移入**既有**归档目录 | 红 | `n6_exact`/`n6_partial_into_existing` ⇒ 无到达 | ✅ |
| N5 删除 change 目录 | 红 | `t494_tie` ⇒ `active=['x']`（报「change 目录不存在」） | ✅ |
| N6 到达但零 manifest | 红（逐条点名三 stage） | 到达成立、证据门逐条命中（真 CLI 在 `symlink_ev` 早期版本上实测 3 条 stage finding） | ✅ |
| N7 到达目录缺必需件 | 红，报「没有任何 change 目录」 | `t541_forged_missing_reviews` ⇒ `c2=False` | ✅ |
| N8 已存在归档目录改名 | 红（判据 3 且判据 5） | `r8_rename_archived` ⇒ `c3=False` | ✅ |
| N9 纯 `cp -r` | 红（判据 5） | `r1_copy` ⇒ 判据 5 全中 | ✅ |
| N10 复制 + 改路径 | 红 | `r2_copy_specrename` / `r3_copy_reportext` | ✅ |
| N11 复制 + 只改一处 | 红 | `r4_copy_onebyte` | ✅ |
| N12 复制 + 删一个证据文件 | 红 | 我自建 `/tmp/r5cases/n12_del_one`（`r4_copy_onebyte` 删掉 `specs/cap/spec.md`）⇒ `arrived=False`；另有 `r9_copy_then_delete` | ✅ |
| N13 `git mv` 无关文件洗白（A1） | 红 | `r16_copy_plus_add` | ✅ |
| N14 源是嵌套归档目录（A3） | 红 | `r21_nested_source` | ✅ |
| N15 混源 | 红 | `r5_mixed_sources` | ✅ |
| N16/N17 组织型子目录 | 非 target | `r12` / `r15` | ✅ |
| N18 base 同路径是 blob | 红（判据 1 有 entry） | `r11_base_blob` ⇒ `c1=False` | ✅ |
| N19 报告挪出 `reviews/`（R3-A1） | 红 | `a1_report_repath` / `i1a_deep_referenced` ⇒ 判据 5 命中被挪走的证词 | ✅ |
| N20 换路径形态（`specs` 同名文件 / `tasks.md` 目…） | 红 | `a3_repath_plus_specs_file` / `a3b_specs_file_pristine` / `a5_tasks_as_dir` | ✅ |
| N21 每个证据文件各加一字节 | **不红（已知天花板）** | `a2_all_one_byte` ⇒ `arrived=True` | ✅（与设计一致） |
| 受保护文件搬进到达目录 | 仍要解释事件 | 判据层未覆盖（`_protected_writes`）；**代码核对**：D5 豁免要求 `old_path` 落在 `<cr>/<active-id>/` 下，`openspec/specs/x.md` 不满足 ⇒ 仍要事件 | ✅（实现期义务） |
| 归档时顺带改 change id | 红（判据 4） | `f3_change_id` ⇒ `arrived=[]`、`active=['old-id']` | ✅ |
| `§5.1` 第 1、2、2b、4、5、10、12、13 条 | 见正文 | 逐条与上表同源（`r13`/`r7`/`m1`/`m3`/`i3_dpath_alive_src`/`r15`/`n6_*`/`empty13_gitkeep`） | ✅ |

**C 的唯一两处例外**：A1（符号链接）与 A4（D4 排除条件）——现稿的用例表**没有**覆盖这两种构造。

---

### D. 与源码事实核对（`文件:行号`）

| 断言 | 出处 | 核对 |
|---|---|---|
| `is_archive_move` 要 `R100` + `old_path` | `design.md:13` | ✅ `contract.py:65,72` |
| `changed_change_ids` / `archived_sources` | `design.md:15` | ✅ `contract.py:85,97-101` |
| `archive_grant` | `design.md:16` | ✅ `contract.py:119` |
| `_protected_writes` / `is_archive_move` 分支 | `design.md:17` | ✅ `checkcmd.py:228,255` |
| `changed_files` 用三点 + `--find-renames` | `design.md:18-19` | ✅ `gitutil.py:99,105` |
| `_parse_name_status` 对 `D` 把路径放 `path`、`old_path` 留空 | `design.md:249-251` | ✅ `gitutil.py:124-129`（`D` 走 else 分支，`Change(raw, fields[i+1])`） |
| `stale_exempt_paths` 整块豁免 `archive/**` | `design.md:55-57,210-211` | ✅ `policy.py:77,86-92` |
| `HASHED_ARTIFACTS` = `tasks.md` + `specs` | `tasks.md:130` | ✅ `constants.py:87-90` |
| `manifest build` 硬编码 `<label>/reviews/` | `design.md:109,190-191` | ✅ `manifestcmd.py:136-142` 与 `:201` |
| `manifest build` 每次从磁盘重算哈希 | `design.md:132-133` | ✅ `manifestcmd.py:146-153`（`sha256_tree(target)`） |
| `manifestcmd` 不调 `change_targets`、按磁盘存在性解析 | `design.md:305-309`、`spec.md:315-319` | ✅ `manifestcmd.py:33-48`；`grep -n change_targets src/witnessloop/manifestcmd.py` 为空 |
| `contract.py:9`「hash 绑定…不防伪造」 | `design.md:171` | ✅ `contract.py:8-9` |
| `resolve_report_path` 与哈希校验同一口径 | `design.md:106` | ✅ `contract.py:282-300`（`Path.resolve()` + `is_within`） |
| `§5.2` 逐条点名的既有测试行号 | `design.md:410-442` | ✅ 8 处行号（`:49/:109/:274/:378/:494/:541/:577/:600`）全部命中实际测试名 |

**D 的结论**：设计稿里的源码级事实断言**本轮未发现新的错误**（R1–R4 已把符号名类错误清干净了）。

---

### E. 低危观察（不阻塞）

1. **`archive/` 直接子项是 blob** 的形态（R4 的 E6）：现稿仍无条款。我的模拟器只把 head 里是 **tree** 的
   直接子项当候选 ⇒ 与现稿一致、不构成绕过。建议实现期在 `tasks.md 3.2` 明写（仍未落）。
2. **`workflow-events.jsonl` 不在 `Ev(A)`**（R4 的 E4）：门禁读它（`events.py`），但事件是**自由文本**、
   作者自写即可（`events.py:5-8` 明写「防漂移不防伪造」）⇒ 不是新面。建议在 `§D1 已知边界` 登记一行（仍未落）。
3. **`§5.3` 末行（归档时顺带改 change id）**：仍写「**当前设计下红**」，未补「今天亦红」
   （`f3_change_id` 实测 `arrived=[]`、`archive_grant` 零命中 ⇒ **今天也红**，R4 的 E5 未落）。
4. **`tasks.md` 未覆盖 `spec.md` 的「既有行为不变（回归护栏）」那条 Requirement**（R4 的 E7 未落）。
5. **`required_artifacts: [""]` 的退化名**：`design.md:87-88` 已明写「实现 SHALL 忽略」，但 `spec.md:36-37`
   仍写「判定语义 SHALL 与契约门**完全一致**」⇒ 三处口径未对齐（见「措辞项 3」）。
6. **`i1b2_separation_clean` 这类构造**只验证到「报告与 `report_path` 目标分离」的一半；
   `tasks.md:118-120`（2.14）已把另一半列成实现期用例 ⇒ 不阻塞。

---

## 未验证项

1. **接入方的具体数字**（`proposal.md:30-32` 的 33 文件全 `A`、`R068/R069/R070/R090`、16 文件 11 项、「120 个归档目录」）
   ——另一个仓的提交，本工作区**无法复算**（R1–R4 同）。
2. **现稿的「实现」不存在**：A/B/C 里**到达判定那一半**全部来自我按文本逐字转写的 `/tmp/r5sim.py`。
   最敏感的四处：① `report_path` 的解析口径（我按 `..` 归一 + 「必须在 A 内」，未做符号链接展开的那一次
   ——真实现用 `Path.resolve()`，我在 A1 里**单独**验证过它会拦下指向 A 外的符号链接）；
   ② 空文件按 head **blob 字节数**判（我用 `git cat-file -s`）；③ `C` 记录**不**算 (b)（`gitutil.py:105` 只传 `-M`，
   实测构造不出 `C`）；④ 候选枚举只取 **tree**。**e2e 里证据门那一半是真 CLI，到达那一半不是。**
3. **浅克隆 / partial clone 下「`merge-base` 成功但 `ls-tree` 失败」这一独立面**：仍未复现（R1–R4 同）。
4. **merge commit 形态**：未取得可判定结论（R2–R4 遗留）。
5. **自定义 `review_manifest_glob` 端到端**：只到「`manifest build` 拒绝该布局」（`manifestcmd.py:136-142`）这一步。
6. **`policy.required_artifacts` 覆写成多段名 / 含 `""` 的端到端**：只做了取值与树可见性的核对。
7. **大仓（≥100 个归档目录）下逐字节撞车的概率**（`tasks.md:4.6`）：未测。
8. **`docs/gate.md` / `README.md`** 的对应改动属实现期义务，尚未落 ⇒ 未核。
9. **`§5.1` 第 6 条（树读不出来 ⇒ fail-closed）**：只做了设计文本核对，未构造「`merge-base` 成功但 `ls-tree` 失败」的真仓。

---

## 必须修改项

> 下面两条都是**设计文本 / 边界**层面的（不是实现 bug——实现还不存在）。
> **没有**「比 `§8 Q4(c)` 已接受的天花板更便宜」的安全级新绕过。

### M1（低危，判据 5 的射程）把「符号链接」补进 `Ev(A)` 的口径与已知边界

- **证据**：见 A1。最小复现：`/tmp/r5cases/symlink_ev`（模拟器 `c5=True arrived=True`，且
  `A/tasks.md` 与基准树里老 change 的 `tasks.md` **逐字节相同**）；`/tmp/r5cases/symlink_gate2`
  （同一结构走**完整**证据门 ⇒ 真 CLI `check：通过 ✓`）。
- **要求**：三选一（或并取）——
  ① `§2 D1` 第 5 条的 `Ev(A)` 口径补一句：**取条目时对 `mode 120000`（符号链接）SHALL fail-closed**
     （或按**解析后**的内容参与 (a)/(b) 比对）；实现落在 `tasks.md 3.2` 的接线点；
  ② `spec.md:44-48` 的判据 5 正文同步；
  ③ `§D1 已知边界` + `docs/gate.md §6` 各加一行；并补一条用例（`§5.3` 加 `N22`：把 `tasks.md` / `specs`
     做成指向基准树现成 change 的符号链接 ⇒ 不授予）。
- **为何是必须**：它落在判据**自己声称**要挡的「零改动机械搬运」格里（`spec.md:67-69`），
  且 `design.md:183` 的「完全依赖」句因此为假；封堵成本极低（一个 `mode` 判断），不引入误伤
  （正规 change 不会把证据做成符号链接；即便有，fail-closed 也是本 change 的既定方向）。

### M2（中低危，D4 的边界）把「源目录消失」的语义写准并登记这条有意的行为变化

- **证据**：见 A4。最小复现：`/tmp/r5cases/pmd_valid`（今天真 CLI ⇒ **红 5 项**，全部指向 `openspec/changes/x`；
  模拟器 ⇒ `active_ids=[]`，`x` **静默消失**）。对照：到达目录件不齐时 `x` **不**被排除
  （`/tmp/r5cases/pmd_invalid` ⇒ `active_ids=['x']`，fail-closed 成立）。
- **要求**：① 把 `design.md:244-245` 的「（= 那个 change **整体**搬走了）」改成**准确的条件句**
  （条件就是「源目录在 head 树里已不存在」），并说明它**不**等价于「整体搬走」；
  ② 在 `spec.md:322-325` 的「有意的行为变化」里登记这一条（今天红 → 改动后绿：`x` 不再被问话）；
  ③ 在 `§5.2` / `§5.3` 各补一条用例钉住（含我给的 `pmd_valid` 形态与 `pmd_invalid` 的 fail-closed 对照）。
- **为何是必须（而非措辞）**：它是一条**未被任何用例覆盖的判红判绿差异**，且违反 `design.md:245` 自己写的
  原则「部分搬走的目录**必须**被问话」。**不要**试图用路径类规则收窄（我试过三种，全都会误伤 `§5.1 2b`
  想绿的「move + 整体重写」形态，见 A4 的分析）——**明写 + 用例**才是可落地的处置。

---

## 措辞项（不影响判据语义、不影响任何用例判红判绿；可当场落库）

1. **`design.md:358-359`（R4 的 `M5①`，未落）**：「必须**每一份**被复制的证据文件都**重写**（或改成 `git mv`）」
   → 与 `design.md:159-172` 的天花板自洽的写法是「**每份至少动一个字节**（见 §D1 的能力天花板）」。
2. **`design.md:567`（R4 的 `M5②`，部分落）**：B3 行的「`§3 第 5 条`」仍指向一个**不含模板项**的清单
   → 在 `design.md:335-338` 的 `docs/gate.md` 更新清单里补「模板 SHALL 放在 `changes_root` 之外」，
   或把该指针改成「`tasks.md 6.1`」。
3. **`spec.md:36-37`**：判据 2 写「判定语义 SHALL 与契约门**完全一致**」，而 `design.md:87-88` 要求实现
   **忽略**空串 / `.` 这类退化 artifact 名（契约门 `(dir/"").exists()` 恒真）⇒ 两处口径不同，
   建议 spec 补同一句偏离说明（三处漂移是本 change 自己点名的 must-fix 类）。
4. **`design.md:471`（R4 的 E5）**：「**当前设计下红**（第 4 条）」建议补「**今天亦红**」
   （实测 `f3_change_id`：`arrived=[]`、`archive_grant` 零命中）。
5. **`tasks.md`**：未列 `spec.md` 的「既有行为不变（回归护栏）」Requirement（R4 的 E7）。
6. **`design.md` 的 `§D1 已知边界`**：建议补第 4 条「`workflow-events.jsonl` 不在 `Ev(A)`（自由文本，非新面）」
   与第 5 条「`archive/` 直接子项是 blob 的形态：候选只取 tree」（R4 的 E4/E6）。
7. **`tasks.md 3.2`**：建议把「候选只取 head 里是 **tree** 的直接子项」写死（R4 的 E6）。

---

## 收敛结论

**不收敛。**

**判据（沿用本 change 自己写的）**：一轮下来**没有新的可证伪项**、**且所有「必须修改项」都已落库**。

- **「R4 的必须修改项已落库」这一半：成立。** `M1`/`M2`/`M3`/`M4` 四条**全部**落库（逐条机械核对，
  证据见上表；含 `§5.2` 两处计数与实列、`§5.3` 表序、三处「到达组」定义）。
  低危附项 `M5①`（措辞）与 `M5②`（指针）**未完全落**，但它们不影响判据语义 ⇒ 归「措辞项」。
- **「没有新的可证伪项」这一半：不成立。** 本轮独立复算给出 **2 条新的、可复算的**证伪项：
  **A1**（判据 5 的 (a) 对符号链接失明 ⇒ 逐字节相同的证据用 `ln -s` 全过、用 `cp` 全拒；
  连带证伪「判据 5 的效力完全依赖 `changes_root` 是唯一存放地」这句）与
  **A4**（D4 的排除条件把「搬一个文件 + 删除其余」当成「整体搬走」⇒ 一个 active change 静默消失，
  今天真 CLI 判红、改动后判绿）。两条都**不是**安全级新绕过（严格弱于已接受的逐字节天花板），
  但都**影响判红判绿、且现稿无用例覆盖**，不是「纯措辞 / 计数 / 指针」。
- ⇒ 按判据，**本轮判定不收敛**，阻塞项就是上面的 `M1` / `M2`。两条都能在一轮内收官：
  `M1` 是「补一句口径 + 一条用例」，`M2` 是「改一句等价句 + 登记一条行为变化 + 两条用例」。
  落库后本轮即可收敛（无安全级阻塞）。

---

### 附：本轮的复算资产（全部在 `/tmp`，未改仓内任何文件）

- 模拟器：`/tmp/r5sim.py`（`python3 /tmp/r5sim.py <repo> [base] [head] [-v]`）。
- 新构造：`/tmp/r5cases/pmd_valid`（A4 的完整版）、`partial_move_delete`、`pmd_invalid`（A4 的 fail-closed 对照）、
  `symlink_ev`（A1）、`symlink_gate2`（A1 的「证据门全绿」证据）、`e11_proper`、`e12_copy`、`n12_del_one`。
- 真 CLI 原始输出见 A1 / A4 的代码块（`check` 的 stdout/stderr 与 exit code）。
