# Grill: archive-arrival-recognition 设计追问（独立零记忆审阅者）

## Reviewer

我是**独立零记忆**的设计审阅者：本对话不携带该 change 的任何历史上下文，设计稿里的「实测」「文件:行号」「今天就成立」一律视为**待验证断言**，可复算的一律复算。

实际读了：本 change 的 `proposal.md` / `design.md` / `tasks.md` / `specs/archive-awareness/spec.md`；前身 `openspec/changes/archive-awareness/`（proposal / design / spec delta，重点看它自认的「残留边界」与 N2/N7）；源码 `src/witnessloop/{contract,checkcmd,gitutil,policy,evidence,events,paths,constants,manifestcmd}.py`；测试 `tests/test_archive_awareness.py`（全 620+ 行）。

实际跑了：
- `grep -n "^def " src/witnessloop/gitutil.py` / `grep -rn "is_archive_move|archive_grant|change_targets|diff_name_status" src/ tests/`（核对符号与调用点）；
- `PYTHONPATH=src python -c` 直调 `policy.Policy.from_doc({}).stale_exempt_paths` + `paths.matches_any`（复算「暗房」与对称性）；
- 自建 `/tmp/wlcheck` 真 git 仓做 `git mv`+改写，复算 `git diff -M --name-status` 的 `base...head`（三点）vs `base head`（两点）；
- 在既有 helper 上**模拟 D1 语义**（`archive/<first-seg>` 在 base 不存在 + head 存在 ⇒ 到达），跑 S1/S2/S3a/S3b 四组绕过构造；
- `git log --all --diff-filter=A --name-only -- 'openspec/changes/archive/*'`（本仓是否归档过）。

**未能复算**（标注「未验证」，不采信）：`design.md §1` 里接入方 asterwynd 的**具体相似度分数** `R068/R069/R070/R090`、三份真实 diff 的逐项 findings 数、以及「接入方 120 个归档目录」——那些来自另一个仓库的提交，本工作区无法复现；本仓历史里**从未归档过任何 change**（下面有证据），所以只能用合成构造逼近方向性结论。

---

## Confirmed Decisions

- **D3「基树判定能真正关掉 `archive-awareness` 自认的残留边界」——成立。** 前身 spec 自认的残留边界是「目标目录名恰好认得源 id 的**部分 move**」，例如 `git mv changes/y/<单文件> → changes/archive/2026-10-14-foo-y/…`（`2026-10-14-foo-y` **已存在**）。在 D1 下，该目录在 base 里存在 ⇒ 判据 1 不成立 ⇒ 不授予；即便目录本不存在（本次才建），它件不齐会照样红。⇒ 该构造在 D1 下必红，说法站得住。
  来源: `openspec/changes/archive-awareness/specs/archive-awareness/spec.md`（「残留边界（写明，别假装不存在）」段）+ `src/witnessloop/contract.py:119-147`（现状 `archive_grant` 会授予）+ 我本地 D1 模拟 `base_exists(name)=True ⇒ arrived=[] → 不授予`。

- **承重守卫②「不得给 base 里已存在的归档目录授予资格」在 D1 下确实保留得住。** D1 的第 1 条判据（base 树里不存在）在目录级直接覆盖了 `M`/`A`/`D`/单文件移入既有目录四类构造：这些构造的目标目录都在 base 里存在 ⇒ 不授予 ⇒ `require_change_for` 照样命中。既有测试 `test_N4`（`tests/test_archive_awareness.py:577`）与 `test_N6`（`:600+`，断言 `"没有任何 change 目录" in err`）在 D1 下**仍然通过**。
  来源: `src/witnessloop/contract.py:65-82`（现状语义）+ 我本地 D1 模拟（base 存在 ⇒ 不到达）+ `tests/test_archive_awareness.py:577,621`（两条既有红钉子）。

- **`design.md §1.1` 引用了两个**不存在**的符号名（其余行号基本对得上）。** `gitutil.diff_name_status` 在仓里**没有**这个函数（真正的函数是 `changed_files`，`src/witnessloop/gitutil.py:99`，其 `--find-renames` 调用在 `:105`）；`checkcmd._check_protected_writes` 也**没有**（真名是 `_protected_writes`，`src/witnessloop/checkcmd.py:228`，`is_archive_move` 分支在 `:255`）。§1 自称「逐行核对」，符号名错会误导实现者。
  来源: `grep -n "^def " src/witnessloop/gitutil.py` → 仅 `changed_files`(:99)，无 `diff_name_status`；`grep -rn "_check_protected_writes" src/` → 空。

- **「`archive/**` 暗房今天就存在」——成立。** `stale_exempt_paths` 末项是 `f"{self.archive_root}/**"`（= `openspec/changes/archive/**`），它把整个归档区列为「审阅 revision 之后允许出现」；实测已归档 change 的 `proposal/design/tasks` 改后不判 stale。
  来源: `src/witnessloop/policy.py:77-92`；我直调 `Policy.from_doc({}).stale_exempt_paths` → `('.witnessloop/**', 'openspec/changes/*/reviews/**', 'openspec/changes/*/workflow-events.jsonl', 'openspec/changes/archive/**')`；`matches_any('openspec/changes/archive/2026-10-15-foo/proposal.md', ...)` → `True`。

- **但由「暗房存在」直接推出「D2 对称性不变量成立」是错的——该不变量在 stale 维度上今天即为假。** 实测：**同一个** `proposal.md`，放 active 路径 `openspec/changes/foo/proposal.md` **不**在豁免集里（`matches_any → False`），放归档路径 `openspec/changes/archive/2026-10-15-foo/proposal.md` **在**豁免集里（`True`）。⇒「同一份内容放 active 与 archive 判绿判红结论相同」在「审阅后又改了 proposal.md」这一维度上**结论不同**（active：stale 红；archive：绿）。本 change 显式选择不动暗房（Q3），所以这条 Requirement **按字面不可满足**，必须限定范围。
  来源: 我直调 `paths.matches_any` 的六路径输出（上面的命令），exempt 对比 `False != True`。

- **D1 的基准是 `git diff base...head`（三点/merge-base），不是两点。** `changed_files` 用的是 `f"{base}...{head}"`；而 `design.md §1.3` 的复算命令写的是 `git diff -M --name-status <base> <head>`（两点）。两者在 base == merge-base 时同结果（我实测两者输出逐行相同），但 base 不等于 merge-base 时会分叉。⇒ 新判据「查基树」必须钉死查**哪一个** revision，否则与到达集合的 diff 基准不一致。
  来源: `src/witnessloop/gitutil.py:105`（`f"{base}...{head}"`）+ `/tmp/wlcheck` 实测（三点/两点输出一致）。

- **D7 / §3.4 / tasks 3.5 声称「`checkcmd` 与 `manifestcmd` 共用同一份 target 解析（避免第二套实现）」——事实错误。** `manifestcmd` **根本不调用** `change_targets`；它只用 `contract.validate_change_dir` 与 `contract.resolve_report_path`，change 目标是靠 `resolve_change_dir` 在**磁盘存在性**上解析的（`--change X`）。所以没有「第二套 target 解析」可去共用。
  来源: `grep -n "change_targets" src/witnessloop/manifestcmd.py` → 空；`manifestcmd.py:33-48`（`resolve_change_dir`）+ `:122-131`（只用 validate_change_dir / resolve_report_path）。

- **本仓历史里从未归档过任何 change（复现了 proposal 的「为什么没被自己踩到」）。** `openspec/changes/` 下 **10 个目录全 active、无 `archive/`**；`git log --all --diff-filter=A -- 'openspec/changes/archive/*'` 输出为空。
  来源: `ls openspec/changes/` + `git log --all --diff-filter=A --name-only -- 'openspec/changes/archive/*'` → 空。

- **design 提的 Q1「显式查基树 vs 只用 diff 推断」其实可由代码定案，不该占用停轮时间。** 「只用 diff」的 (b) 方案有**具体绕过**：往一个**已存在**的归档目录新增一个文件，diff 里就是 `A`（`design.md §5.3` 的 N3 构造）⇒ (b) 按「有 A 记录」会授予 `archive/<old>` ⇒ N3 变绿。既然 (b) 可被证伪，(a) 是唯一正确选择，属「能由代码判定」。
  来源: `design.md §5.3` N3 + 我本地 D1/N3 推演（diff-only 会把 `A archive/<old>/new.md` 当到达 ⇒ 授予已存在目录）。

---

## Open Questions

> 本节与 `design.md §8` 的停轮问题**同集合、同编号**（R1 时的那四个问题已按文末「早期问题的去处」重排 / 移出）。
> 以下每条都**不能**由代码单独定案（涉及安全面取舍或范围取舍），需要用户拍板。
> **用户 2026-10-15 已逐条裁定**，答复见本文件 `## User Confirmation`。

### Q1 归档目录名「必须认得源 id」这条守卫（D1 第 4 条），对**有源**的到达是否保留？

- (a) 保留：`name == src` 或 `name.endswith("-" + src)` 才授予（**每一个**源都要满足）；
- (b) 删掉：到达方式不设限，名字不必再核。
- **具体例子**：`git mv openspec/changes/foo-x openspec/changes/archive/misc` + 改 `agent/x.py`（该 change 件齐、三份 manifest 齐）：
  - (a)：`misc` 不认得 `foo-x` ⇒ 不授予 ⇒ **红**；
  - (b)：该目录在基准树里没有 entry、内容是本次搬来的 ⇒ 到达 ⇒ 走**同一套**证据门 ⇒ **绿**。
  - **对照**：把同样内容 **`cp -r`** 到新建的 `archive/misc/`（源**不动**）⇒ 两种选法**都红**（第 5 条命中）。
- **补充事实（供决策）**：守卫**原始**要挡的形态（单文件 move 进**已存在**的归档目录）已被判据 1 独立关掉；
  「白捡证据」已由判据 3 / 判据 5 在记录层与内容层关掉 ⇒ 它只剩**命名约定**作用。
- **用户裁定**：见 `## User Confirmation` 的 Q1。

### Q2 `archive/**` 的 stale 豁免（「暗房」）本次一并收窄，还是另立？

- (a) 另立 issue，本次不动；(b) 本次一并收窄（范围膨胀到「归档后哪些改动该被允许」）。
- **具体例子**：已归档 change 的 `proposal.md` 在它那份 manifest 记的 `head_sha` **之后**被改一个字：
  今天 / (a) 不判 stale（`policy.stale_exempt_paths` 末项 `openspec/changes/archive/**`）；(b) 应当判 stale。
- ⚠️ 它与本 change 的「对称性不变量」耦合：只要暗房在，该不变量在 **stale 维度**就不成立 ⇒ 已限定到「证据门槛」维度。
- **用户裁定**：见 `## User Confirmation` 的 Q2。

### Q3 **嵌套归档布局**（`archive/2026/<name>/`）本次要不要支持？

- (a) 不支持（维持今天行为）；(b) 支持（候选定义改成 `archive/**` 下任意深度、件齐、整体新增的目录）。
- **具体例子**：某接入方按年份组织，落 `archive/2026/10-15-foo/{proposal.md, design.md, tasks.md, specs/, reviews/}`（件齐）+ 改 `src/app.py`：
  - (a)：**红** ——「`src/app.py` 属于必须挂 change 的路径……但本次 diff 里没有任何 change 目录」（与今天逐字相同）；
  - (b)：**绿** —— `2026/10-15-foo` 被认作到达。
- **用户裁定**：见 `## User Confirmation` 的 Q3。

### Q4 第 5 条（内容来源）的**强度**：接受「逐字节天花板」，还是再加一档？

- (c) **接受天花板 + 明写能力边界**：判据 5 挡**零改动 / 只动一处**的机械搬运
  （整份复制、改路径、改一个字节、删一个文件、混源、搬无关文件洗白、报告挪出 `reviews/`、换路径形态、源在嵌套目录），
  **不挡**「跑个脚本给每份证据各加一个字节 + 重算 manifest」；
- (a)+(b) 再加一档强度（把 `Ev(A)` 扩成「change 目录下全部非空文件」）——**实测只解决一半**（关不掉「每个文件各加一字节」），
  且误伤面变大（模板 / 样板文件都进集）。
- **具体例子**：一份 3 个月前的归档 change（三份真审阅报告齐）。`cp -r` 到新名后，对每份证据文件跑一次
  `printf '\n' >> "$f"`，再跑 3 次官方 `manifest build`，最后改 `src/app.py`：
  - (c)：**绿**（真 CLI 实测 `check：通过 ✓`）——本稿把它**明写**为已知边界；
  - 封堵它需要**真实性**（签名 / 可验证来源），属本 change 的**非目标**。
- **用户裁定**：见 `## User Confirmation` 的 Q4。

## 风险

- **R-A（中）：D1 把「到达」放宽到与 diff 状态完全解耦，等于把「一个新归档目录」与「一次真归档」画等号。** 除 Q1 的「复用别人证据」外，还包含「直接新建整份证据」这一路（design 已接受）。两者叠加后，`require_change_for` 的**语义从「你得为这次代码改动挂一个 change」退化为「工作树里得存在某个证据完整的 change 目录」**。design 用「本工具没有 change↔路径映射」解释，但 `_require_change` 的**文案**（`checkcmd.py:216-224`）仍在暗示「为这次改动挂 change」——口径与实现已有张力。
- **R-B（中）：D4「`archived_sources` = 到达组全部记录的 `old_path`」会把**别的** active change 的旧路径也一并排除。** 例：一次**到达**的归档 `2026-x-a`（新目录）+ 顺手 `git mv changes/other/notes.md → changes/archive/2026-x-a/notes.md`；该记录的 `old_path = changes/other/notes.md` 落进「到达组」⇒ `other` 从 active 集合里静默消失（若 `other` 其它文件没进 diff）。本次因 `2026-x-a` 件不齐仍红，不构成「变绿」绕过，但这是前身 spec 明令防的「静默逃检」同类面（只是从 `R100` 扩到了 `R<100`）。建议把 `archived_sources` 收窄到「`old_path` 落在该到达目录对应的源 change 内」，别用「到达组全部记录」。
- **R-C（低）：`archive/` 下第一段可能是**文件**而非目录。** 若新基树查询不校验「是 tree」，`archive/notes.md`（一个文件）会被当成到达的「目录」`notes.md` ⇒ 报「change 目录不存在」。实现必须要求 `tree`/目录存在，而非任意 entry 存在。
- **R-D（低）：浅克隆 `git ls-tree <rev>` 失败时的 fail-closed 会制造「环境型红」。** design 已列（R2）并给了用例，方向正确；需在实现时确认 base 的 tree 对象确实可达（本地工作树默认可达；只 `--depth 1` 且 base 不在浅边界内时有风险）。
- **R-E（低·未验证面）：design §1 的接入方实测数字（33 文件全 `A`、`R068/R069/R070/R090`、16 文件 11 项、「120 个归档目录」）本工作区**无法复算**。** 我用合成仓验证了**方向**（`git mv` + 改写被搬文件会产出 `R<100>` 或 `A`+`D`，取决于相似度），但没有复现其**具体分数与计数**。验收（`tasks 4.2`）必须在接入方仓里真跑，别拿本仓合成数字顶替。

---

## 必须修改项

- **M1（spec 自相矛盾，必须改）**：本 change 的 `specs/archive-awareness/spec.md` Requirement 1 说「**新建**的 `archive/<name>/` 即到达」，但**同一个 Requirement 下**的 Scenario「名识别守卫对有源的到达继续生效」说「**新建**的 `archive/misc/`（内容来自 active `z`）⇒ **不**授予」。两条对同一构造给出相反结论，而 Requirement 的**正文**里根本没有「名识别守卫」这一规则（只在 Scenario 里出现）。⇒ 要么把「有源则须名识别」写进 Requirement 正文并**定义「有源」**（从哪条记录、什么条件算『源』），要么删掉该 Scenario。
  来源: 本 change `specs/archive-awareness/spec.md` Requirement 1 正文 vs 其 Scenario；`design.md` Q2 与 §8。

- **M2（不变量过强，必须限定）**：Requirement「到达方式 SHALL NOT 改变证据门槛（对称性不变量）」按字面**不可满足**——`stale_exempt_paths` 对 `archive/**` 整块豁免、对 active 的 `proposal/design/tasks` 不豁免（实测 `False vs True`）。本 change 又显式不动暗房（Q3）。⇒ 必须把该不变量**限定到证据门槛维度**（必需件 / manifest hash+revision 绑定 / `reviewer≠author` / grill 正文 / stage 集合），并**显式排除 stale 维度**（或写明「stale 维度的非对称是既有口径、另立 issue」）。
  来源: 上面 Confirmed Decisions 的 `matches_any` 实测；`design.md §3.5` 非目标。

- **M3（基准未钉死，必须写死）**：新增的「查基树」必须查与到达集合**同一个** revision。`changed_files` 用的是 `base...head`（三点/merge-base，`src/witnessloop/gitutil.py:105`），所以基树查询应查 **`git merge-base(base, head)`** 的树，而不是 `base` ref 的原树——否则 base 分支在分叉点后又前进时，「到达判定」与「diff 成员」会对不上（同一目录可能被 diff 认为新增、却被基树认为已存在，或反之）。design §D7 只写「增加 `base` 参数」，没写是哪个 base。⇒ 在 design + spec 里钉死 revision，并加一条用例。
  来源: `src/witnessloop/gitutil.py:105`；design §1.3 复算命令（两点）与实现（三点）的口径差。

- **M4（事实错误，必须改）**：`design.md §3.4 / §3.5`、`tasks 3.5`、D7 声称「`manifestcmd` 与 `check` 共用同一份 target 解析（避免第二套实现）」——`manifestcmd` **不调用 `change_targets`**，没有可共用的第二套 target 解析。⇒ 删除或改写成**真实**可共用项（实际共用的是 `validate_change_dir` 与 `resolve_report_path`；若意图是让 `manifest build` 也感知「到达」，需另写清要共享什么）。
  来源: `grep -n "change_targets" src/witnessloop/manifestcmd.py` → 空；`manifestcmd.py:33-48,122-131`。

- **M5（引用错误，必须改）**：`design.md §1.1` 的两个符号名不存在：`gitutil.diff_name_status` → 实为 `changed_files`（`gitutil.py:99`，`--find-renames` 调用在 `:105`）；`checkcmd._check_protected_writes` → 实为 `_protected_writes`（`checkcmd.py:228`，`is_archive_move` 分支在 `:255`）。§1 以「逐行核对」为卖点，符号名错会直接把实现者带沟里。
  来源: `grep -n "^def " src/witnessloop/gitutil.py`；`grep -rn "_check_protected_writes" src/`。

- **M6（回归面必须点名，必须改 tasks）**：D1 会**改变既有测试的期望**：`tests/test_archive_awareness.py:541` `test_N2_a_forged_archive_grants_nothing`（新建 `archive/2026-10-14-fake/` + 改 `src/**`）今天断言 `"没有任何 change 目录" in err`；D1 之后该目录**是到达**，报的会是**缺件/缺 stage**（不再是「没有任何 change 目录」）⇒ 该断言必失败。`tasks 2.6` 只笼统写「N2/N3」，应**逐条点名**这个测试要改写（并说明「伪造归档从『不授予』变成『授予但证据门禁拦下』」这一语义反转）。对照：`test_N4`(:577)/`test_N6`(:600+) 断言的同字符串在 D1 下仍成立（目标目录在 base 存在），**不要**误改。
  来源: `tests/test_archive_awareness.py:541-557`（N2）、`:577`/`:621`（N4/N6）；D1 语义推演。

- **M7（停轮队列可瘦身，建议改）**：`design.md §8` 的 **Q1** 与 **Q4** 能由代码定案，应移出停轮队列（附证据），别占用户时间：
  - **Q1（显式查基树 vs 只用 diff 推断）**：diff-only 方案 (b) 被 §5.3 的 N3 构造**直接证伪**（往已存在归档目录加文件 = `A` ⇒ (b) 会授予）⇒ 只能选 (a)。见 Confirmed Decisions 末条。
  - **Q4（归档 target 的 stage 集合是否与 active 完全一致）**：这是既有 `code_hits` 触发的 `building`/`grill-adversarial` 两条硬门（`checkcmd.py:105-119`）的直接推论 + D2 对称性——选 (b) 即违反 D2，属自相矛盾 ⇒ 定案 (a)。
  来源: `checkcmd.py:105-119`（stage 硬门由 `code_hits` 触发）；`design.md §5.3` N3；D2 文本。

---

## User Confirmation

- **Q1**: 用户答复：删掉名识别守卫（选 (b)）——归档目录名不再要求认得源 id，有源与无源的到达一律只看「是否新到达 + 内容来源」；确认时间: 2026-10-15
- **Q2**: 用户答复：本次不收窄 `archive/**` 的 stale 豁免（暗房），另立 issue 跟踪（已开 Xingkai98/witnessloop#27）；确认时间: 2026-10-15
- **Q3**: 用户答复：不支持嵌套归档布局（`archive/2026/<name>/`），维持今天行为（该形态仍判红）；确认时间: 2026-10-15
- **Q4**: 用户答复：接受判据 5 的逐字节天花板，并把该能力边界明写进规格（不再加档）；确认时间: 2026-10-15

---

## 早期问题的去处（R1 时的四问；**未**占用用户时间）

> ⚠️ **如实说明**：下列四个问题**从未**停轮给用户——它们在 R1–R8 的对抗轮里**由代码 / 实测定案**后移出队列，
> 作者**不**把它们算作「用户确认过」。R1 版的 Q 编号与现稿的 Q1–Q4 **不是同一套**，这里按**内容对应关系**写明，
> 并沿用**不带 `Qn` 记号**的写法，避免与停轮队列的编号混淆。

1. **（R1 版问题一）把「已存在」的归档目录改名算不算到达？** → **由实测定案：不授予**
   （判据 3 记录层：到达组里没有 `old_path` 落在 `archive/**`；判据 5 内容层通常同时命中）。
   证据：R1 的 F1 与 R2 的 A2 构造（`cp -r` / 改名 + 只改 manifest 两个字段）实测。
2. **（R1 版问题二）新建归档目录被当成 target、组织型 / 工具型子目录被判红，这个代价是否接受？** →
   **由实测定案**：判据 2 收紧为「含**全部**必需件」，`archive/2026/`、`archive/notes/` 都**不是** target
   （R1 的 F2 / R2 的 B1 构造实测）。**范围性**的那一半（嵌套布局要不要支持）升格为现稿 **Q3**。
3. **（R1 版问题三）到达判定用「显式查基树」还是「只用 diff 推断」？** → **由代码定案：显式查基树**
   （diff-only 会被「往已存在的归档目录加文件也是 `A`」直接证伪）。
4. **（R1 版问题四）归档 target 的 stage 集合是否与 active 完全一致？** → **由代码定案：完全一致、零特判**
   （stage 硬门由 `code_hits` 触发；选「更松」即违反对称性不变量）。
5. **（R1 版问题二的后半）「归档目录名必须认得源 id」这条守卫是否保留？** → **用户裁定**：删（升格为现稿 **Q1**）。
6. **（R1 版问题三的另立选项）`archive/**` 的 stale 豁免** → **用户裁定**：本次不收窄、另立 issue #27（升格为现稿 **Q2**）。
