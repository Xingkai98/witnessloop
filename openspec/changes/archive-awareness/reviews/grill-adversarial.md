# Grill 对抗验证: archive-awareness（第 1 轮 R1）

> 零记忆独立审阅者产出（算法与格式依据 `templates/grill.md` 第 5 步）。
> **READ-ONLY**：未改动 `src/`、未 commit、未建 manifest、未改被审 worktree 的 git 状态。
> 立场：**默认上游结论有错，逐条证伪**；能实测的一律实测，实测一律在 `/tmp` 的隔离副本里跑。
> 被审对象：整合稿四份（`proposal.md` / `design.md` / `tasks.md` / `specs/archive-awareness/spec.md`）
> + `reviews/grill-design.md`（grill 报告）。

## Reviewer

- run id: `grill-adversarial-reviewer-archive-awareness-4bd6ad0e2143`（未设 `WITNESSLOOP_RUN_ID` ⇒ 走
  `templates/grill.md`「怎么取 run id」的**确定性兜底**形态 `<stage>-<role>-<change>-<head 短摘要>`）
- 时间: 2026-10-14T15:33:09Z
- 被审 revision: `4bd6ad0e2143ee93ddb665a7d668ed9097ea1963`（分支 `archive-awareness/2026-10-14`，基线 `origin/main` = `ae99256`）
- 方法（可复现）：
  1. **隔离副本**：`git clone /home/happy/wl-wt/archive-awareness /tmp/wladv/repo`（带历史，供 `check --base` 用）；
     基线复核 `uv run pytest -q -p no:cacheprovider --basetemp=/var/tmp/wladvpytest` = **496 passed**（与被审稿一致）。
  2. **实验室脚手架** `/tmp/wladv/lab.py`：在每个用例里**新建真 git 仓**（`git init` + `init --test-command`），
     用被审 worktree 的**真 CLI**（`.venv/bin/python -m witnessloop`）驱动；`base` 用 `git branch -f base HEAD`
     在「base 状态已提交、PR 动作未做」的那一刻钉住，`check` 一律 `--base base`。
  3. **「修后」模拟** `/tmp/wladv/fixsim.py`：进程内把 `contract.changed_change_ids` 换成
     「active id ∪ D2 授予」、把 `events.load_all` 换成 D6 的两条显式 glob，从而对**完整 `check`**
     跑出修后行为，而**不动任何仓内文件**。id 记作 `archive/<name>`——这样既有
     `validate_change_dir` / `validate_review_manifests` / `evidence.*` **零改动**就解析到归档目录与归档 label
     （`f"{changes_root}/{change_id}"` 与 `rel_change.rsplit("/",1)[-1]` 恰好都正确）。
     ⚠️ 该模拟**不含** `manifestcmd` 侧（D4 未实现，见 §5），D4 相关结论另行标注。
  4. **纯函数直调**：`contract.is_archive_move` 7 组构造、`pathlib.glob` 三套模式逐例、
     `evidence.grill_evidence_findings` 直接喂 `grill-design.md`。
  5. 全称/计数一律 `grep -c` / `wc -l`；引用的既有 `文件:行号` **逐条 `sed -n` 复核**（见 §6）。
- 前置状态（实测，供下游读）：`reviews/grill-design.md` 过本仓 checker =
  **1 条**「缺少 `## User Confirmation` 小节」（`evidence.grill_evidence_findings`）；这与 `design.md §8`
  的自我声明一致（停轮时补 Q1 答复，`tasks.md` H2）。本文件按任务要求**不**建 manifest ⇒
  现在这份 change 仍是红的（孤儿规则/两处 stage 门），属**停轮之后的**步骤。

## Verdict

**CHANGES_REQUESTED**（2 条阻塞 + 1 条未决细节；**不推翻方案方向** ——
「三条症状 ⇒ 同一个根因」「§1.2 的 4 项红对照」「`_require_change` 不能改成豁免」
「第 6 面（部分 move）」四条我都**独立重跑为真**，见下）。

阻塞项都是同一类：**「这句话描述的流程/断言，机械实现出来是另一个结果」**——
不是架构问题，是 3 处规格补丁 + 1 处未定义的 tie-break。

- **M1（阻塞）｜「先归档 → 重建 → 每条一条事件」这条补救链在**同一个 PR** 里跑不通，
  而且会把 PR 判成两个 change 目录（其中一个不存在）。** 见 §2.1
  （实测 **6 → 11 条红**；按设计补 3 条事件后**仍 8 条红**，其中 5 条是补事件消不掉的幽灵 change 目录）。
- **M2（阻塞）｜`spec.md` Scenario 1 / `design.md §5.1` B3 / `tasks.md` B3 的验收断言
  「退出码为 0」按字面 fixture **为假**（实测 EXIT=1，6 条 finding）。** 见 §2.2。
- **M3（未决细节，建议须改）｜D7 的 `id → 目录` 映射**没有定义同名不同目录时的 tie-break，
  而该 diff **可构造**（实测）。见 §5.3。

## 逐条对抗结论

### 1. 绕过口：N1–N6 + 我自造的 6 种攻击（**逐条实测**）

全部在隔离副本里跑「今天」与「修后（D2+D6 模拟）」两遍。**结论：没有找到新的绕过面**；
设计新设的第 2 条判据（目标目录名须认得源 id）**确实**把第 6 面挡掉了，
A5/A5b 证明「名不认得源 id 的整目录 move」在修后依然 fail-closed。

| 用例（实测构造） | diff 关键状态 | 今天 | 修后（模拟） |
|---|---|---|---|
| **N1** 只改 `src/` | `A src/app.py` | EXIT=1，1 红 | EXIT=1，1 红 ✓ |
| **N2** **新建** `archive/2026-10-14-fake/**` | `A` ×4 + `A src/` | EXIT=1，1 红 | EXIT=1，1 红 ✓ |
| **N2b** 先建后 `git mv`、**同一 commit**（base 无源） | git 只报 `A` | EXIT=1，1 红 | EXIT=1，1 红 ✓ |
| **N3** `rmtree` 删 change 目录 | `D` ×10 + `A src/` | EXIT=1，8 红 | EXIT=1，8 红 ✓ |
| **N4** `M` 归档目录里已有文件 | `M archive/y/…` | EXIT=1，1 红 | EXIT=1，1 红 ✓ |
| **N6** `git mv changes/z/notes.md → archive/y/notes.md` | **`R100`**，`is_archive_move=True` | EXIT=1，1 红 | EXIT=1，1 红 ✓（D2 第 2 条**拒绝**：`y`≠`z` 且不以 `-z` 结尾） |
| **A4（我造）** `archive/2026-10-14-z` 已存在，把整目录 `changes/z2` 搬进去 | `R100`，授予候选 `2026-10-14-z` | EXIT=1，1 红 | EXIT=1，1 红 ✓（`-z2` 后缀不匹配） |
| **A5（我造）** 整目录 move、名**不认得**源 id（`2026-10-14-w ← z2`） | `R100` | EXIT=1，1 红 | EXIT=1，1 红 ✓（`授予=[]`） |
| **A5b（我造·最尖）** 同上，且**目标 change 证据齐备** | `R100` | —— | EXIT=1，**1 红** ✓（fail-closed，未被「证据齐备」洗白） |
| **A6（我造）** 源本来就在 archive（归档内改名） | `R100`（两端都在 `archive/`） | EXIT=1，1 红 | EXIT=1，1 红 ✓ |
| **A8（我造）** 整目录 move **带内容改动**（先改 `tasks.md` 再搬） | `R100` ×9 + **`A`+`D`** ×1（tasks.md 相似度低于阈值，git 不配对） | EXIT=1，5 红 | EXIT=1，14 红 ✓（`is_archive_move` 为假的那一半把 active id `m` 拉回集合 ⇒ 「change 目录不存在」） |

⇒ **N1–N6 六条今天全红、修后全红**（`design.md §5.3` 的断言成立）；
`N2/N2b/N6/A4/A6` 的「不生效」是**结构性**的（`A`/`M`/`C` 状态下 `is_archive_move` 恒 False——我直接调用
7 组构造确认：`R100`+old 在 active ⇒ True；`M`/`D`/`R087`/`C100`/`A`/old 在 archive ⇒ 全 False）。

**「有没有别的授予/豁免路径被漏掉」——用计数口径穷举过：没有。**
`grep -rn 'archive|ARCHIVE_DIR_NAME|is_archive_move|archive_root' src/witnessloop/*.py`（去注释）只有 6 处落点：
`constants.py:37-38`（常量）、`policy.py:73-74` + `:91`（`archive_root` / `stale_exempt_paths` 的 `archive/**`）、
`contract.py:38-55`（`is_archive_move`）+`58-86`（`changed_change_ids`）、`checkcmd.py:235-239`（豁免解释事件）、
`guardcmd.py:64`（跳过字面量 `archive`）。⇒ 「change 存在于本次 diff」的**取得路径**只有两条：
active 路径首段（既有的）、D2 归档授予（新增的）；**事件、manifest、policy 都不授予 change 资格**。
`guardcmd.resolve_change_id`（`:56-66`）要求 id 命中**现存 active 目录** ⇒ 归档后推不出 ⇒ 放行，
与 `design.md §3.5` 登记的「已知缺口」一致（**fail-open，但那是本地守卫层，且设计显式声明不补**）。
另外我确认：**grant 失败的归档 move 仍照旧免解释事件**（`_protected_writes` 只看 `is_archive_move`，不看授予）
——这是今天的行为，不是新口子（纯改名是簿记动作）。

`design.md §1.2` 的对照表**逐格复现**（我自己的仓、自己的命令）：
C1b-A = 6 文件 / **4 项红**；C1b-B（无 `reviews/` 目录）= 5 文件 / **5 项红**；C3 = 6 文件 / **1 项红**；
C2 = 5 文件 / **EXIT=0**。⇒ grill 的 M5 订正**成立且可重跑**。
`is_archive_move` 的 10 组语义也**无漂移**（`contract.py:45` 仍是 `status != "R100" or not old_path` ⇒ False）。

### 2. M2 的连锁与顺序 —— ⚠️ **这里出问题**（两条阻塞）

#### 2.1 阻塞 M1：「先归档 → 用归档目录名重建 → 每条一条事件」在**同一个 PR** 里跑不通

`design.md §1.5` 第 2 条 / `tasks.md C8` / `spec.md` 的「归档后重建（覆盖）已存在的 manifest 仍要解释事件」
scenario 测的是**「归档已在 base、本 PR 只重建（`M` ×3）」**——那个设定我**复现为真**：

- 归档已在 base，本 PR 在新 revision 上重建 3 份 manifest（不写事件）⇒ `check` **恰好 3 条**
  「受保护路径被写入，但没有结构化解释事件」（`file:line` 级别逐份对应）；
- 补 3 条 `protected_path_write` 事件（`artifact_path` 指向那三份 manifest）⇒ **EXIT=0，绿** ✓。

**但 `design.md D4` 的代码块把 ①②③ 摆成**同一个 PR** 的三行（`spec.md:109-116` 同）——
那样跑出来是**另一个结果**。实测（同一 PR：① 归档 + 改码 → ② 用归档目录名重建 → ③ 各写一条事件）：

```console
# ① 归档 + 改 src/app.py 之后（只归档、还没重建）
修后 EXIT=1 findings=6
  archive/2026-10-14-gwa/reviews/building.manifest.json：manifest.change_id='gwa' 与目录不符
  archive/2026-10-14-gwa/reviews/building.manifest.json：审阅的是旧 revision：… 之后又改动了非证据文件：src/app.py
  （grill-adversarial / grill 同款各 2 条）

# ② 再在**同一 PR** 里重建三份 manifest ⇒ git 的改名配对变成 R085（改名**带**内容改动）
statuses: R085 changes/gwa/reviews/building.manifest.json → archive/2026-10-14-gwa/reviews/building.manifest.json
          R085 changes/gwa/reviews/grill-adversarial.manifest.json → …
          R085 changes/gwa/reviews/grill.manifest.json → …
修后 EXIT=1 findings=11    stdout: … 11 个变更文件，2 个 change 目录 / change：archive/2026-10-14-gwa, gwa
  1-5. openspec/changes/gwa：change 目录不存在 / 缺少 review manifest / 无 stage=grill / 无 stage=grill-adversarial / 无 stage=building
  6-11. 受保护路径被写入但没有解释事件 ×6（归档侧 3 条 + **旧路径侧 3 条**）

# ③ 按 design 说的「每条重建各配一条解释事件」（3 条，artifact_path 指向归档侧 manifest）
修后 EXIT=1 findings=8    ← 只清掉了**归档侧**那 3 条；**旧路径侧的 3 条 + 幽灵 active 目录那 5 条照旧**
  1-5. openspec/changes/gwa：change 目录不存在 / 缺少 review manifest / 无 stage=grill / 无 stage=grill-adversarial / 无 stage=building
  6-8. openspec/changes/gwa/reviews/{building,grill-adversarial,grill}.manifest.json：受保护路径被写入但没有解释事件
```

两个机制，都不是实现细节而是**规格后果**：

1. **重建把 `is_archive_move` 的「纯改名」前提毁掉了。** 重建 = 改内容 ⇒ git 把那次 move 报成 `R085` 而不是
   `R100` ⇒ `is_archive_move=False` ⇒ **旧路径不再进 `archived_sources`**（`contract.py:67-71`），
   于是被搬走的 `gwa` **以 active id 的身份回到集合**：`check` 报出 2 个 change 目录，其中一个
   （`openspec/changes/gwa`）**已不存在** ⇒ `validate_change_dir` 的「change 目录不存在」+ 缺件 4 条 = **5 条红**。
2. **`_protected_writes` 对 rename 记「两半」**（`checkcmd.py:243-245`：`old_path` 按 `D` 再记一次）⇒
   重建一份 manifest 要 **2 条**事件（新路径 + 旧路径），3 份 = **6 条**，不是 3 条。

⇒ `design.md D4` 的「每条重建各配一条解释事件」在**同一 PR** 下**少了一半**（3 条 vs 实际 6 条），
而真正咬住的是**幽灵 active 目录**那 5 条——**补再多事件也消不掉**（它来自 `changed_change_ids`，不是来自事件池）。
`spec.md:115` 的「同样的 `check` 通过」在**同一 PR** 下**为假**。
**这条不是边角**：`design.md §1.3` 说接入方的硬规则是「实现 PR 同时归档」，而 R2 的补救
正是冲着「已有证据的历史 change 要重建」去的——**恰好命中这个形态**。

**可落的两条出路（择一并写进 spec，我核过都可行）**：
(a) **把「归档 move」与「manifest 重建」拆到两个 check 区间**（归档落 base 之后再重建）——
与 §2.1 开头那段实测一致，3 条事件就够，且**不需要动 `is_archive_move`**；
(b) 若坚持同一 PR：必须**同时**写明「要吃 **6** 条解释事件」**且**解决幽灵 active id——
而后者要改 `changed_change_ids` 对「落点在 `archive/**` 但 `R<100`」的排除，
这**与 `design.md D2` 第 1 条「`is_archive_move` 一行都不改」和 `tasks.md A4` 直接冲突**，
且会**削弱**对 A8（边搬边改）的检出（实测 A8 今天/修后正是靠那条 `A`+`D` 才红的）。
⇒ **推荐 (a)**，并把 (b) 的代价写成「明确不做 + 为什么」。

#### 2.2 阻塞 M2：`§5.1 B3` / `spec.md` Scenario 1 的字面 fixture 达不到「退出码 0」

`design.md §5.1` 第 1 条 / `tasks.md B3` / `spec.md:23-29` 写的都是同一个先红用例：
「change 在 base 上**证据齐备** → 本 PR 归档 + 改 `src/**` ⇒ 修后 **EXIT_PASS**」。
实测（修后模拟，同一 fixture）：

```console
修后 EXIT=1 findings=6
  archive/2026-10-14-gwa/reviews/{building,grill-adversarial,grill}.manifest.json：manifest.change_id='gwa' 与目录不符
  archive/2026-10-14-gwa/reviews/{building,grill-adversarial,grill}.manifest.json：审阅的是旧 revision：… 之后又改动了非证据文件：src/app.py
```

两条都不是实现的锅，是 fixture 描述不完整：
① `change_id` 仍是**源 id**（`§1.5` 第 1 条，设计自己写明了）；
② 「本 PR 改了 `src/**`」意味着**证据之后又落了非证据改动** ⇒ `_check_git_span` 的 stale 判定命中
（这是本仓**既有的**「先内容、后证据」口径，`docs/gate.md §3.1`）。
⇒ 「证据齐备」在**归档路径 + 最终 revision** 上才成立。`design.md §4 R2` 其实已经写了补救顺序，
但 §5.1/§spec 的那条验收**没有**带上这个前提，读起来像是「归档 + 改码 ⇒ 自动绿」。
**修法**：把 Given 写全（「其 manifest 已在**归档路径**上、且 `head_sha` 绑定**本 PR 的最终内容 revision**」），
或把该条改成「先红 = 6 条」，把「绿」留给 `spec.md` 已有的那个「重建后往返」scenario。

#### 2.3 §2 的核心质疑：**`change_id` 该用源 id 还是归档目录名？——归档目录名，结论成立；但理由要改**

我逐条实测，结论是**设计选对了，且这不是「更别扭的口径」，而是被既有实现逼出来的唯一自洽解**：

- **绑定它的不是「build 侧没有 diff」那句话，而是 `contract.py:250`**：
  `doc["change_id"] != rel_change.rsplit("/", 1)[-1]` —— 交叉校验比的是 **label 的末段 = change 目录的名字**。
  归档态目录名是 `2026-10-14-gwa` ⇒ 想让它过，`change_id` **只能**是目录名，
  否则就得**给归档态单开一套校验器**——那正是本仓反复禁止的「两边各写一套口径」
  （`design.md D7`、`resolve_report_path` 的注释、`HASHED_ARTIFACTS`）。
- **「与 change 的身份是源 id 自相矛盾」这个疑虑不成立**：本工具里 change 的身份**从来就是目录名**
  （`change_dir(root, pol, id) = changes_root/<id>`，`contract.py:34-35`），源 id 只是**源 active 目录名**。
  归档改名后，它作为「active change」的那个身份结束了；D2 用 `old_path` 取源 id **只是授予判据**，
  不是身份，设计里没有第二处把它当身份用。⇒ 不矛盾。
- **「老的、未重建的归档 manifest 会永远判不符」——不会**，我实测过：
  归档态**只在「本 diff 里含搬进它的 move」时才被校验**（授予是按 diff 派生的）。
  后续一个不碰它的 PR（我造了「无关 PR」）⇒ 该归档 change **完全不进集合，0 条 finding**。
  ⇒ 不是「永远」，是「**归档那一个 PR** 吃一次」——也就是 R2 说的那条新红类。
- **但设计把选项表写窄了**：`design.md D1` 的表只列了「归档目录名 / 源 id / 日期前缀解析」，
  结论「两个候选里只有一个可落、无取舍」**偏强**。理由①「源 id 口径在 build 侧要按 `*-<id>` 后缀猜」——
  加一条**歧义即报错**的守卫，那条路是可实现的（不是不可落）；
  ②真正的硬约束是上面那条「共用校验器 + 末段比对」。
  ⇒ **结论保留，把理由改成 ②**；`design.md §2.6 CQ1` 同。
- **另有第三条路设计没算账（新发现，非阻塞）**：`D2` 第 2 条**已经**引入了一条命名约定
  （目标目录名须等值或以 `-<源id>` 结尾）。既然已经在约定命名，把它**收紧到「必须等于源 id」**
  （`archive/<id>`，正是 `tests/test_archive.py:35` 既有写法）就会**整条消掉 `§1.5` 第 1 条**：
  归档前后 `change_id` 不变 ⇒ **不需要重建**、不会判「与目录不符」、R9 的第一条用例不存在。
  实测对照：同一个 fixture 下，`archive/2026-10-14-gwa` ⇒ 6 条红（含 3 条 change_id 不符）；
  `archive/gwa` ⇒ **3 条红**（只剩 stale），`change_id` 那条类**整体消失**。
  代价是给接入方加一条改名要求（他们说日后再谈）；收益是 M2 的连锁只剩「stale」一半。
  ⇒ **不必推翻 D1**，但 `D1`/`§4 R4`/`§8 Q1` 应该把这条**摆出来并写明为什么不选**（我实测它能省掉一整类红）。

> 结论：**`change_id` = 归档目录名，正确、自洽、且被 `contract.py:250` 逼定**；
> 但它带来的是**真实成本**（重建 + 3~6 条事件），不是「作者的口径洁癖」——
> 成本该在 `D1`/`Q1` 里**明码标价**，并给出「收紧归档命名」这条更便宜的备选。

### 3. 三处事实订正 —— **三条都真修好了（逐条实测）**

1. **C1b 拆成两个可重跑变体** ✓：`proposal.md:43-44` 与 `design.md:36-51` 已拆成 C1b-A（6 文件 / 4 项）
   与 C1b-B（5 文件 / 5 项），我**从干净检出各跑一遍，数字逐字相同**；`design.md:67-69` 还写明了
   「只在工作树里恰好有未跟踪空 `reviews/` 目录时成立」这个成因。⇒ 订正到位，且**可重跑**。
2. **删掉「唯一闭合方式」** ✓：全库 `grep '唯一闭合'` 只剩三处**否定式**表述
   （`design.md:506` 的「理由**不是**…」、`design.md:472`、`reviews/grill-design.md:47/68,104`），
   `design.md:332` 那句已不存在；`§8 Q1` 的推荐理由改成了「没有第二套判据」✓。
3. **N5 改为「再深一层」+ `archive/` 一级会被读的口径** ✓：`design.md §5.3 N5`、`D6`、`R11`、
   `tasks.md D3/E5`、`spec.md:141-148` 全部改到位。我用真 `pathlib.glob` 逐例实测：
   - `changes/*/workflow-events.jsonl` **命中** `changes/archive/workflow-events.jsonl`（`*` 匹配 `archive`）——2 命中；
   - 新增 `changes/archive/*/workflow-events.jsonl` **命中** `changes/archive/notes/workflow-events.jsonl`——1 命中；
   - `changes/**/…`（`rglob` 形态）命中 **5** 处，**多出** `archive/y/sub/…` 与 `archive/y/notes/…`。
   ⇒ 「真否定面是再深一层」「前两者**会**被读」「**不能用 rglob**」三句**全部为真**。

### 4. Q2/Q3/Q4 → CQ1/CQ2/CQ3：**该留停轮还是可由代码定？——三条都可由代码定，但两条的理由句要改**

| 项 | 事实是否成立（我的实测/计数） | 该不该停轮 |
|---|---|---|
| **CQ2**（触碰归档文件不算「出现在本次 diff」） | **成立**：`contract.py:45` 要求 `status == "R100" and old_path`；直调 7 组：`M`/`D`/`R087`/`C100`/`A`/old-in-archive ⇒ **全 False**。机械上本来也不会「算」 | **不必停轮** ✓ |
| **CQ3**（归档事件授权面今天收窄不了） | **事实成立**：`events.Event` 只有 4 个字段（`events.py:37-41`）、`load_events_file` 只取那 4 个键（`:69-76`）、`covers` 只比 `artifact_path`（`:103`）、`events.py` 全文 `change_id` 出现 **0** 次。**但「今天收窄不了」偏强**：把「事件只在**本次 diff 的 change 集合**内的 change 目录里才提供豁免」是**不需要新字段**的（`load_all` 的读点与该集合求交即可）——那是**语义变更**（会推翻 `docs/gate.md §7` 的既有边界），不是**不可实现** | **不必停轮** ✓（理由句改「不改语义」） |
| **CQ1**（id 只能是归档目录名） | **结论成立**，但证据链该换成 `contract.py:250` 的**末段比对**（见 §2.3）；原证据句「build 侧无 diff ⇒ 只能猜」不构成「不可落」 | **不必停轮** ✓（理由句改） |

⇒ **停轮队列只剩 Q1 是成立的**（这三条确实是「要不要写进否定面清单/要不要改语义」，不是用户取舍）——
前提是把上面两句**过强的理由**改准。**Q1 本身的分叉面我也复现了**：
「纯归档 PR + 历史 change 证据不齐」今天 **EXIT=0**，uniform 修后 **EXIT=1（4 条：3 条 change_id 与目录不符 +
1 条 grill 正文少于 3 条）**，code-gated 会绿。⇒ Q1 是真取舍，**该停轮**。
⚠️ 一处小订正：`design.md §8 Q1` 举 uniform 的红只点了 grill 正文那一条，实测 **change_id 不符那 3 条也在**——
例子该把 4 条都列上，否则用户以为「补一份报告就绿」（还得重建 3 份 manifest）。

### 5. 实现可行性 / 未决细节 / **必须保持绿的既有测试**

**能落。** 三处接线点在代码里都是现成的形状：
- `contract.resolve_report_path(directory, …)` / `hashing.sha256_tree` / `evidence.*` **本来就吃目录**
  （`evidence.py:172` 的入参就叫 `change_dir`）+ `manifestcmd.py:83` 的 `report_rel` 由目录推 ⇒ D7 的「只留一份实现」是**低风险**的 ✓；
- `manifestcmd.py:61`（`changes_root / change_id`）与 `:149`（`manifest_rel` 硬编码）确实是 `--change` 侧
  唯一两处要动的地方 ✓（我 `grep -c 'changed_files' manifestcmd.py` = **0**，`gitutil.` 只有 `rev_parse`×2 / `resolve_base` / `diff_text`，
  CQ1 的事实底子成立）；
- `manifestcmd.py:64` 的 `is_within(directory, changes_root)` 对 `changes_root/archive/<name>` **天然成立** ⇒ 归档目标不会撞逃逸守卫 ✓。
- `--change archive` 的困惑点实测复现：`EXIT=1`，文案是「`openspec/changes/archive`：缺少必需件 proposal.md」（`R5` 描述准确）✓。

**未决细节（设计含糊过去的）：**

1. **§5.3 D7 的 tie-break 未定义（建议须改）**：`D7` 说 `change_targets` 返回「active + 归档**并集**」，
   但 `D1` 的 id 是**单段目录名**。我**构造出**同一 diff 里两条来源给出**同一个 id** 的情形：
   base 同时有 active `changes/x`（新）与归档 `changes/archive/x`（旧），本 PR 做
   `git mv changes/x/notes.md changes/archive/x/notes.md`（`R100`，`name == 源id` ⇒ 授予 `x`）
   **且**同 PR 新增 `changes/x/extra.md`。实测：
   `今天 active ids = ['x']`、`D2 授予 = [('x','x')]` ⇒ **同一 id 指向两个目录**。
   若按最自然的落法写成 `dict[id] = dir`，**其中一份会被静默丢掉**（丢掉哪一份取决于实现）。
   ⇒ 必须写明：映射**以目录为键**（或 id 撞车时**两份都校验 / 直接判红**）。
   （我的模拟把 id 记作 `archive/<name>`，所以**恰好绕过**了这个坑——这正说明单段 id 是有代价的。）
2. **`_report` 的计数口径（R6，设计已登记）**：`checkcmd.py:274-276` 的「N 个 change 目录」在归档态语义变了；
   `tests/test_check_contract.py:88` 的 `assert "0 个 change 目录" in out` 我确认在**位**且**不受影响**
   （该用例没有归档 move ⇒ 仍是 0）✓。设计说要「要么保留子串要么同步改测试」——**建议保留子串**（成本最低）。
3. **D4 的 `--report` 相对谁解析**：设计说「相对**解析后的目录**」（`D4`），但没说**报错文案**里的
   相对示例（`design.md D4` 提示「例如 `--change 2026-10-14-X`」）今天**不可能**成功
   （D4 未实现）⇒ 该提示语只有在**同一个 PR 里**先实现了 D4 才有意义（否则接入方照着做还是红）。属文档时序问题。

**必须保持绿（我逐条 `grep` 确认全部存在，且 `tests/test_require_change.py` 恰好 8 条、`tests/test_archive.py` 恰好 6 条）：**

- `tests/test_archive.py`（6 条）：`test_archiving_a_change_passes_without_events`、
  `test_archived_change_is_no_longer_validated_as_active`、`test_deleting_an_evidence_file_still_needs_an_event`、
  `test_modifying_a_file_inside_archive_still_needs_an_event`、`test_renaming_within_the_active_change_still_needs_events`、
  `test_archiving_a_protected_spec_still_needs_an_event` —— **尤其前两条**：
  它们用的归档名是 `archive/add-retry`（`tests/test_archive.py:35`，**与源 id 同名**），
  末段比对恰好成立 ⇒ 修后**不重建也应绿**。⚠️ 这也是 **R9 的盲点**：这 6 条**永远抓不到** `§1.5` 第 1 条。
- `tests/test_require_change.py` 全 8 条（N1 那两条在内）；
- `tests/test_check_contract.py`：`test_touched_but_absent_change_dir_is_reported`（N3）、
  `test_complete_change_passes`、`test_change_outside_changes_root_is_ignored`（R6 的子串）；
- `tests/test_manifest_build.py`：`test_unknown_change_is_rejected`（归档 fallback 不得吞掉「找不到」）、
  `test_nested_change_id_is_rejected`、`test_dotdot_change_id_is_still_caught_by_the_containment_guard`、
  `test_absolute_change_id_is_rejected`、`test_report_path_escaping_the_change_dir_is_rejected`、
  `test_report_outside_reviews_is_rejected`、`test_rebuild_without_explicit_ids_is_byte_identical`；
- `tests/test_events.py` / `test_events_readpoint.py` / `test_check_protected.py`；
- **幂等**（我实测）：同一 revision 上重复 `manifest build` 产出**逐字节相同**的
  `building.manifest.json`（sha256 两次一致）⇒ `D1` 换了 `change_id` 来源后这条**必须仍然成立**
  （锚 = `(change, stage, role, revision, base)`，`manifestcmd.py:111-115`）；
- 全量 `uv run pytest -q` = **496 passed**（我在隔离副本里复跑，与基线一致）。

### 6. 新引入的矛盾 / 悬空引用（改动后全库一致性）

- **Q 编号一致性 ✓**：全库 `grep -o 'CQ[0-9]'` / `'\bQ[0-9]\b'` 逐处核过——除 `design.md:279,282,287,292`、
  `tasks.md:159` 的「**（原 Qn）**」标注外，**没有**裸 `Q2/Q3/Q4` 残留；`§8` 只留 Q1；
  `design.md:485-490` 的「本仓 checker 的实际口径」描述与我跑的 `evidence.grill_evidence_findings`
  **逐条对得上**（它解析报告而非 `design.md`、`Code-Resolved Questions` 是独立小节不进判据）✓。
- **§「唯一取得方式」与 N4/N6 互斥性 ✓**：`spec.md:41` 的「唯一取得方式 = 归档 move」与
  `spec.md:50-55` 的四条否定面、`E5/E6` 一致（我把 N4/N6 跑成红，与「不授予」自洽）。
- **悬空引用 ✗（1 处）**：`design.md:443` 写「（见 tasks 的 **G6**）」，但那条守卫在 `tasks.md` 的 **G7**
  （G6 是 README）。**改成 G7**。
- **事实句偏差 ✗（1 处，非阻塞）**：`design.md:442` / `tasks.md:111` 称「G3 要改的 `docs/gate.md §3.2`
  正是**「幂等」密集处**」——实测 `grep -n '幂等' docs/gate.md` 只有 **:9 / :52 / :497** 三处，
  **§3.2（:199-222）内 0 处**（那里只有限定词「固定 base 与 revision 时逐字节可复现」）。
  守卫（`tests/test_docs.py:117-135`）是**按文件整体扫**的 ⇒ **今天 §3.2 不撞它**；
  真正要小心的是「G3 若**新写**一个『幂等』就必须带限定词」。⇒ 句子改成这个意思即可。
- **`reviews/grill-design.md:84`** 引的 `tests/test_archive.py:26` **是错的**（:26 是 `init_wired(repo, cli)`，
  归档 move 在 `:35`）。该报告是绑定 `ae99256` 的历史产物，可以不改；但**下游别照抄这个行号**。
- `proposal.md` 的「非目标：不改 `archive/` 的命名约定」与 `D2` 第 2 条**新引入**命名约束之间的张力，
  `design.md §3.5` **自己写明**了 ✓（这条我认它是**诚实登记**，不是矛盾）。
- **行号复核结果（我逐条 `sed -n`）**：`contract.py:34/38/45/58/67-71/80/89/94/121/250`、
  `checkcmd.py:73/79/86/96/98/105/188/194`（`:86/:98/:105` 恰好 **3** 处 `contract.change_dir(`，与设计一致）、
  `events.py:83`、`manifestcmd.py:49/61/72/149`、`policy.py:22/73-74`、`docs/gate.md:245-246`、
  `README.md:135-137`、`templates/grill.md:91`、
  `openspec/changes/building-review-gate/{proposal.md:52,tasks.md:54}`、`tests/test_archive.py` 6 条、
  `tests/test_check_contract.py:88`、`tests/test_docs.py:117` —— **全部命中，只有上文两处例外**。

## 新发现

- **F1（阻塞，= M1）** 同一 PR 内「归档 + 重建 manifest」会把 `R100` 降级成 `R<100`，
  既让**被搬走的 active 目录以幽灵 id 回到集合**（5 条红），又让事件需求**翻倍到 6 条**；
  设计的补救顺序与 `spec.md:115` 的「同样的 check 通过」在该形态下**为假**。见 §2.1。
- **F2（阻塞，= M2）** `spec.md` Scenario 1 / `B3` 的验收断言按字面 fixture **不可达**（实测 6 条红）。见 §2.2。
- **F3（未决，= M3）** `D7` 的 `id → 目录` 未定义 tie-break，撞车形态**可构造**。见 §5.3-1。
- **F4（非阻塞·校准）** grill 的「碰一下 active change + 重建 manifest ⇒ 绿」是**真**的：我造了
  `M changes/q/notes.md` + `M src/app.py` + 在攻击 HEAD 重建 `q` 的三份 manifest + 3 条事件
  ⇒ `check` **EXIT=0（绿）**（今天与修后都一样）。⇒ R1/R10 的「同类等价、不阻塞」**校准准确**，
  我**不为它加码**；但这也说明「部分 move」的残留**不是**本 change 引入的新类 ✓（grill 的判断我复核为真）。
- **F5（非阻塞·反直觉的好消息）** 接入方**真实时序**（§1.3：change 在 base **零证据** ⇒ PR 归档 + 改码
  ⇒ **在归档路径上新产出**证据）在修后**能绿**：manifest 是 `A`（不是 `R<100>`）⇒ 没有幽灵 id、
  也没有「覆盖要事件」的问题。⇒ 本 change 的**主路径可用**；出问题的是「**已有证据**的历史 change」这条补救路径。
- **F6（非阻塞）** `archive/<id>`（同名归档，本仓既有写法）**不需要重建**也能过 `change_id` 那一关
  ⇒ 设计若愿意收紧命名，可省掉 §1.5 第 1 条一整类问题（见 §2.3 末）。
- **F7（非阻塞·文档面比设计写的更大）** `docs/gate.md §3.2` 的「幂等」说法与 `design.md:443` 的 G6/G7 引用
  都不准（§6）。另：**`README.md` / `docs/gate.md` 被 `tests/test_docs.py` 钉着**这件事，
  设计只对 **G3** 提了守卫——实测守卫是**文件整体**的（`RUN_ID_DOCS` 还含 `src/witnessloop/cli.py`、
  `templates/*`、`plugin/**`），**G1/G2/G4/G5 同样受约束**（例如 `确定性` 必须在场、
  不得出现 `挡「忘了另开 run」`）⇒ `tasks.md G7` 该说「**改任一节文档前先读 `tests/test_docs.py`**」，
  而不只是「改 §3.2 时」。

## 必须修改项

- **M1〔高·阻塞·`design.md §1.5-2` + `D4` 的代码块 + `§4 R2` + `tasks.md C7/C8` + `spec.md:109-123`〕**
  改正补救链的**适用范围**：`① 先归档 → ② 用归档目录名重建 → ③ 每条一条事件` 只在
  **归档 move 已经落进 base**（= 重建与 move **不在同一个 `base...head` 区间**）时成立。
  必须写清：同一 PR 内重建 ⇒ git 报 `R<100` ⇒
  (a) 被搬走的 active 目录**以幽灵 id 回到集合**（`openspec/changes/<源id>：change 目录不存在` 等 5 条）；
  (b) 事件需求是 **6 条**（新路径 + 旧路径各一条），不是 3 条。
  择一并落到 spec：**(a) 强制拆 PR**（推荐）／(b) 同一 PR 时写明 6 条事件 + 改 `changed_change_ids`
  对「落点在 `archive/**` 的 `R<100`」的排除（并**显式说明**这会**削弱**对「边搬边改」的检出，
  且与 `D2`「`is_archive_move` 一行都不改」的立场冲突）。**实测数字见 §2.1，可直接抄进文档。**
- **M2〔高·阻塞·`design.md §5.1` B3 + `tasks.md B3` + `spec.md:23-29`〕**
  把「归档 + 改 `src/`、证据齐备 ⇒ `EXIT_PASS`」的 fixture 写全：证据必须在**归档路径**上、
  且 `head_sha` 绑定**本 PR 的最终内容 revision**；否则该断言实测为 **EXIT=1 / 6 条红**
  （3 条 `change_id` 与目录不符 + 3 条 `审阅的是旧 revision`）。
  或把这条改成「先红 = 6 条」，把「绿」留给 `spec.md:98-103`（「归档后重建证据并往返」）那条 scenario。
- **M3〔中·`design.md §3 / D7` + `tasks.md A3`〕**
  写明 `change_targets` 在**同一 id 撞到两个目录**时的行为（实测可构造：`active x` ∪ `archive/x`），
  并规定**以目录为键 / 两份都校验 / 撞车判红**三者之一——**不要**用 `dict[id]=dir`（会静默丢一份红）。
- **M4〔低·`design.md §2.6 CQ1`、`§2.6 CQ3`〕** 两句**过强的理由**：
  CQ1 的「源 id 口径不可落」→ 改成「`contract.py:250` 的末段比对 + 共用校验器逼定」（见 §2.3）；
  CQ3 的「今天收窄不了」→ 改成「收窄=改语义（推翻 `docs/gate.md §7` 的既有边界），本 change 不做」。
- **M5〔低·`design.md:443`〕** 「（见 tasks 的 G6）」→ **G7**。
- **M6〔低·`design.md:442` + `tasks.md:111`〕** 删掉/改写「§3.2 是『幂等』密集处」——
  实测 `docs/gate.md` 的「幂等」在 `:9/:52/:497`，**§3.2 内 0 处**；守则是**文件整体**的，
  改成「**新写**『幂等』必须 ±2 行内带『固定 base 与 revision』或同句含 `init`」。
- **M7〔低·`design.md §8 Q1` 的例子〕** uniform 的红要写全 **4 条**（3 条 `change_id` 与目录不符 +
  1 条 grill 正文少于 3 条），否则用户会以为「补一份报告就绿」。
- **M8〔低·`tasks.md G7`〕** 「改 §3.2 前先读 `tests/test_docs.py`」→「**改任一节文档前**先读」
  （守卫覆盖 `docs/gate.md` / `README.md` / `templates/**` / `plugin/**` / `src/witnessloop/cli.py`）。

> **不需要改的（我独立复核为真，防止下游把它们当「没验」）**：三条症状与全部 `文件:行号`；
> `§1.2` 的 4 项红对照（含 M5 的两个变体）；`is_archive_move` 的 10 组语义；
> `_require_change` 不能改成豁免的立论（C3 那份 PR 修后确实会变 4 条真门禁红）；
> N1–N6 + A4/A5/A6/A8 今天全红；M2a（每份 manifest 各 1 条 `change_id` 不符）、
> M2b（新 revision 上重建 = **恰好 3 条** + 3 条事件 ⇒ 绿）；D6 让症状③ 的那条 finding 消失；
> 同 revision 重复 build 逐字节幂等；基线 496 passed。

---

# R2 复审（revision `ef53065`）

> 第二轮独立零记忆对抗者（**未读 R1 的会话历史**，只读 R1 的**产物** `grill-adversarial.md`）。
> **READ-ONLY**：未改 `src/`、未 commit、未建任何 `*.manifest.json`、未动被审 worktree 的 git 状态
> （复核后 `git status` 干净、HEAD 仍 `ef53065`）。全部实验在 `/tmp/r2lab/**` 的隔离副本里跑。

## Reviewer（R2）

- run id: `grill-adversarial-reviewer-archive-awareness-ef53065f62ae`（同 R1 的确定性兜底形态 `<stage>-<role>-<change>-<head 前 12 位>`）
- 时间: 2026-10-14T15:51:17Z
- 被审 revision: `ef53065f62aef729f7a224676f4504c5b01d924f`（分支 `archive-awareness/2026-10-14`，基线 `origin/main` = `ae99256`）
- 方法（可复现）：
  1. **隔离副本**：`git clone /home/happy/wl-wt/archive-awareness /tmp/r2lab/repo`（带历史，供 `check --base` 用）。
     基线复核 `uv run pytest -q -p no:cacheprovider --basetemp=/tmp/r2lab/pt` = **496 passed**（与被审稿一致）。
  2. **实验室** `/tmp/r2lab/lab.py`：每个用例新建真 git 仓（`git init` + `uv run witnessloop init --test-command`），
     用被审 worktree 的**真 CLI**（进程入口 `witnessloop.entry.main`）驱动，`check` 一律 `--base main`。
  3. **「修后」模拟 `fixed(alias=…)`**：进程内把 `contract.changed_change_ids` 换成「active id ∪ D2 授予」
     （id 记作 `archive/<name>`，这样既有校验器**零改动**就解析到归档目录与归档 label）、把
     `events.load_all` 换成 D6 的两条显式 glob、把 `contract._validate_one` 的 `change_id` 比对换成
     「`∈ {归档目录名, 源 id}`」（D8）。`alias=False` 只关掉 D8 这一层，用来隔离**别名单独的贡献**。
     ⚠️ 该模拟不含 `manifestcmd` 侧（D4），D4 相关只做纸面复核。
  4. 纯函数/路径直调（`pathlib.glob` 逐例）、全称/计数一律 `grep -c` / `wc -l`，引用的 `文件:行号` 逐条复核。

## Verdict（R2）

**PASS — 收敛成立，无新阻塞**（建议：2 条非阻塞的文档订正，见「新发现」）。

- **阻塞①（D4 补救链跑不通）→ 真修好**：换成 D8 别名 + §1.6 顺序 + R12/N7。三条独立实测全部复现（见 §2）。
- **阻塞②（fixture 字面不可达 EXIT=0）→ 真修好**：`spec.md` Scenario 1 / `tasks.md B3` 改成「能绿的形态」+
  明说红的形态；实测能绿形态 `EXIT=0`、字面形态 **3 项红**（恰好是被复审稿写的 3）。
- **阻塞③（D7 tie-break 未定义）→ 真修好**：D7 定死「列表、以目录为键、两份都校验」，spec 有独立 Scenario；
  撞车形态**可机械构造**（实测 8 项红，两个目录都被校验）。
- **它反驳 R1 的两处 → 两处都成立**（实测，见 §4）。
- **别名（D8）方案 → 没有开出新的授予/豁免路径**（N1–N7 + R1 六种攻击修后**全红**）；
  但「张冠李戴」**是真实发生的**——**仅在**已被 §2.5 残留边界 2 承认的「部分 move」形态下，
  且**不改变红绿结果**（同一个绿不用别名也拿得到）。⇒ **不阻塞**，但 D8/R4 该把这条边界写清（新发现 N-1）。

## 1. 别名方案（D8）——`change_id` 校验到底放宽了多少（**主打项，全实测**）

### 1.1 正/负控制

| 用例 | 造法 | today | fixed(alias) | fixed(无 alias) |
|---|---|---|---|---|
| **P1 只归档** | base：active `gwa` 证据齐备（`change_id="gwa"`）；PR：**只** `git mv` 到 `archive/2026-10-14-gwa` | 0 | **0** | **3**（每份 manifest 1 条 `change_id='gwa' 与目录不符`） |
| **P2 别名护栏** | 同上，但把归档态 `building.manifest.json` 的 `change_id` 改成 `"other"` | — | **红**（`change_id='other' 与目录不符`）| — |

⇒ **P1 坐实两点**：① 复审稿「只归档不重建 = 0 项红」**为真**；② 这个 0 **完全由别名购得**——关掉别名，
同一 fixture 立刻 3 项红。⇒ 别名是**必需**的（不是洁癖），且**归档前产出**的 manifest 二字面都过。
P2 坐实别名**不是「放开」**：第三个名字仍被判「与目录不符」（`spec.md` 的护栏 Scenario 成立）。

### 1.2 ⚠️ 攻击：它到底会不会「张冠李戴」

**结论：会——但只在已被承认的「部分 move」残留下，且不带来新的红→绿能力。**

| 用例 | 构造（都在隔离真仓） | today | alias=ON | alias=OFF |
|---|---|---|---|---|
| **E1（攻击）** | base：`archive/2026-10-14-foo-y/`（**他人的**归档目录，只有件）+ active `changes/y`；PR：改 `src/app.py` + `git mv changes/y/notes.md → archive/2026-10-14-foo-y/notes.md`（**R100 单文件**）+ 在该目录里写三份 `change_id="y"` 的 manifest | 1 红 | **`EXIT=0` 全绿** | **3 红**（`change_id='y' 与目录不符`×3） |
| **E2（对照）** | 同 E1，但 manifest 写**目录名** `change_id="2026-10-14-foo-y"` | 1 红 | **`EXIT=0`** | **`EXIT=0`** |
| **E3（攻击变体）** | base：active `gwa`；PR：改 src + **整目录**归档 `gwa → archive/2026-10-14-gwa`，但 manifest 写 `change_id="other-change"` | 1 红 | **3 红**（拒） | **3 红**（拒） |

**读法（关键在 E1 vs E2）**：
- **E1 说明别名确实把一个「别的 change 的 id」接受进了这个目录**。授予该 target 的 move 源是 active `y`，
  故接受集合 = {`2026-10-14-foo-y`, **`y`**}`；`y` 是**另一个（仍是 active 的）change 的 id**，
  而该目录本属 change `foo-y`。⇒ 复审稿问的「一份 `change_id` 等于源 id 的 manifest，
  会不会被另一个归档 change（目录名碰巧以该源 id 结尾）接受」——**答案：会**（`2026-10-14-foo-y`
  以 `-y` 结尾，S=`y`，被接受）。**别名确实把 `change_id` 校验从 `{N}` 放宽到 `{N,S}`**，而 `S` 可以是**外来 change 的 id**。
- **但 E2 证明这不是新能力**：同一个绿，只要把 `change_id` 写成**目录名**（身份口径本来的合法字面），
  **关掉别名照样绿**。⇒ 别名只改了「你必须写哪个字面」，没有把任何**本该红**的形态变成绿。
  这与本工具自陈的边界（`contract.py` 头注「防漂移不防伪造」）一致：能写 manifest 的对手本来就能写任意 `change_id`。
- **E3 定边界**：**真归档**（move 源 = 目录所属的 change）时 `S` 就是该 change 自己的 id，接受集合
  `{N,S}` 里没有外来名字 ⇒ 第三个名字（`other-change`）**照样拒**。⇒ 别名**没有连带放开**。

### 1.3 与「身份 = 目录名」的自洽性

**自洽，但复审稿把「归谁」这一侧写得比实际窄**：D1「身份 = 归档目录名」说的是**校验落在哪个目录**，
别名只放宽**该目录内 manifest 声明的名字集合**（D8 明写「同一个校验器的一个参数」）——这一层口径**没被推翻**。
⚠️ 但在**部分 move**下，被放宽进来的 `S` 是**别的 change 的 id**，此时「该目录里的 manifest 声明自己属于谁」
与「该目录属于谁」**可以不一致**。复审稿的 §2.5 残留边界 2 / R10 只承认了「部分 move 会**授予**该 target」，
**没写**「别名还会让这个 target 接受**外来 id**」。⇒ 建议在 D8 / R4 / §2.5 残留边界 2 补一句
（**非阻塞**：不改变红绿、不越过 E2 的能力上界）。

### 1.4 会不会出现「同一份 manifest 同时满足两个 change」

**不会（文件级）。** 一份 manifest 物理上只在一个目录里，而每个 target 只校验**自己目录**里的 manifest
⇒ 不存在一份文件被两个 target 计为证据。唯一「同一字面满足两个 target」的情形是 **D7 撞车**
（active `changes/x` 与授予的 `archive/2026-10-14-x` 同时存在，接受集合都含 `x`）——**天然 fail-closed**（§3 实测 8 项红）。

## 2. 阻塞①②③ 逐条结论

### 阻塞①（M1）——**真修好**（三条实测）

| 项 | 复审稿的说法 | 我的实测（隔离真仓 + `fixed(alias=True)`） |
|---|---|---|
| §1.6 顺序能绿 | 内容 → **active 态**建证据 → move 放最后 ⇒ `EXIT=0`、11 个变更文件 | **复现**：`EXIT=0`、`11 个变更文件`、`1 个 change 目录`（`archive/2026-10-14-gwa`）；3 份 manifest 是 `A`、其余 `R100` |
| 「只归档」= 0 项 | 别名让归档前产出的 manifest 直接过 | **复现**（P1：`0`；无别名 `3`）|
| 9 → 6 → 3 的后果链 | 同一 diff 重建 ⇒ `R<100` ⇒ 不授予 + 幽灵 active id + 事件翻倍 | **逐格复现**：① 只归档 `0` → ② 再重建 **`9`**（3 幽灵 + 6 受保护写入）→ ③ 补归档侧 3 条 `6` → ③b 补旧路径侧 3 条 **`3`（那 3 条幽灵 active id 补事件消不掉）** |

⇒ **与复审稿/commit message 的「9 → 6 → 3」逐字吻合**，幽灵 id 不可消也复现。**这条阻塞真闭合了。**

### 阻塞②（M2）——**真修好**

- 「能绿的形态」（§1.6）**可达**：见上，`EXIT=0`。
- 「红的形态」**复现为 3 项**：base 证据齐备 + 本 PR 归档 + 改 `src/`（= R1 §2.2 的字面 fixture）
  ⇒ `fixed` **3 项**，全是既有的「审阅的是旧 revision…src/app.py」。**且这 3 项与归档无关**（R1 说对）。
- `spec.md` Scenario 1 的 `Given` **已写全**（active → 改 src → **active 态**建证据（绑 ① 的 revision）→ 纯 `R100` 归档放最后），
  `Then` 要求 `退出码为 0`，并附 ⚠️ 说明字面形态是 3 条**既有**规则的 stale、**不得**当验收断言。⇒ 断言**可达**，不再是空头支票。

### 阻塞③（M3）——**真修好**

- D7 定死「`change_targets` 返回**列表**、**以目录为键**、同 id 撞车**两份都校验**、**不许** `dict[id]=dir`」；
  `spec.md` 有独立 Requirement + Scenario「同 id 撞车」；`tasks.md A8` 有先红用例。
- **撞车可机械构造**（实测）：base 同时有 `changes/x` 与 `archive/2026-10-14-x`；PR
  `git mv changes/x/notes.md → archive/2026-10-14-x/notes.md`（`R100`，`name` 以 `-x` 结尾 ⇒ 授予）
  **且**新增 `changes/x/extra.md` ⇒ `check` 输出 `2 个 change 目录`（`archive/2026-10-14-x`, `x`），
  **两份各出 finding**（`8` 项 = 两侧各 4 条）。⇒ tie-break 有规则、有用例、fail-closed。

## 3. N1–N7 与 R1 的六种攻击 —— **复跑结果（今天 / 修后全红）**

| 用例 | diff 关键状态 | today | 修后（D2+D6+D8） |
|---|---|---|---|
| **N1** 只改 `src/` | `A src/app.py` | 1 红 | **1 红** ✓ |
| **N2** 新建 `archive/<name>/**`（无源） | `A`×4 + `A src/` | 1 红 | **1 红** ✓ |
| **N2b** 先建后搬、同一 commit | git 只报 `A` | 1 红 | **1 红** ✓ |
| **N3** 删除 change 目录（`D`） | `D`×4 + `A src/` | 5 红 | **5 红** ✓ |
| **N4** 改归档里已有文件（`M`） | `M` + `A src/` | 1 红 | **1 红** ✓ |
| **N5**（D6 否定面「再深一层」） | `pathlib.glob` 直调 | — | **成立**：两条 glob 并集**命中** `archive/workflow-events.jsonl` 与 `archive/notes/workflow-events.jsonl`，**不命中** `archive/<name>/<sub>/…`；`rglob` 会多命中那两条 ⇒「真否定面是再深一层」「不能用 rglob」**均为真** ✓ |
| **N6** 单文件 `R100` 改入不认得的目录 | `R100`，`is_archive_move=True` | 1 红 | **1 红** ✓（D2 第 2 条拒绝：`y`≠`z` 且不以 `-z` 结尾）|
| **N7** 同 diff「move + 改写被 move 的文件」 | `R074`/`A`+`D` | 9–15 红 | **红**（含幽灵 active id）✓ |
| **A4** 整目录搬进已存在的 `archive/2026-10-14-z` | `R100` | 1 红 | **1 红** ✓（`-z2` 后缀不匹配）|
| **A5** 整目录 move、名不认得源 id | `R100` | 1 红 | **1 红** ✓（授予 = `[]`）|
| **A5b（最尖）** 同 A5，且目标 change 证据齐备 | `R100` | 1 红 | **1 红** ✓（`fail-closed`，未被「证据齐备」洗白）|
| **A6** 源本来就在 archive（归档内改名） | `R100`（两端都在 `archive/`）| 1 红 | **1 红** ✓ |
| **A8** 整目录 move **带内容改动** | `R100`×4 + `A`+`D` | 5 红 | **9 红** ✓（不授予 + 幽灵 id `m`）|

> 另复现了 `design.md §1.2` 的四格对照（C1b-A = **6 文件 / 4 项**；C1b-B = **5 文件 / 5 项**；
> C3 = **6 文件 / 1 项**；C2 = `EXIT=0`）与 `spec.md` 的防绕过 Scenario（归档 + 改 src、**零 manifest** ⇒
> 修后**恰好 4 条**缺件，路径全指向**归档目录**）。⇒ **没有找到新的授予/豁免路径**；D2 第 2 条**确实**把第 6 面挡掉。

## 4. 它反驳 R1 的两处 —— **两处都成立（实测）**

1. **「R1 推荐的『拆两个 check 区间』本身不足以变绿」→ 成立。**
   无别名时，含该 move 的**归档 PR**（base 证据齐备 + 归档 + 改 `src/`）实测 **6 项红**
   （3 条 `change_id='gwa' 与目录不符` + 3 条 stale），加上别名才降到 3（只剩 stale）。
   R1 自己 §2.2 测的正是这 6 条。⇒ 拆区间**只修了重建那个 PR**，**修不了归档那个 PR**；
   真正让它可绿的是 **D8**。复审稿的订正**正确**。
2. **「Q1 例子在别名之下是 1 项红、不是 4 项」→ 成立。**
   纯归档 PR（`legacy-x` 的 grill 正文只有 2 条 Confirmed Decisions、manifest 用源 id 产出）实测：
   `alias=ON` → **1 项**（`grill-review.md：## Confirmed Decisions 只有 2 条，少于硬门槛 3 条`）；
   `alias=OFF` → **4 项**（3 条 `change_id` + 1 条 grill 正文）。⇒ R1 的 M7 订正（「要写 4 条」）在 D8 之下**过期**，
   复审稿改成 **1 项**是对的。**同一 fixture** 若把归档目录收紧成 `archive/legacy-x`（同名）⇒ **1 项**（无论别名开关）
   — 顺带印证了 D1 备选段「收紧命名能整类消掉 `change_id` 那条」的说法。

## 5. 停轮队列该几条

- **Q1〔归档 change 的校验深度〕——是必须停轮的用户决策。** 分叉只在**纯归档 PR** 上可见（实测 P1/§4-2：
  `uniform` ⇒ 红 1 项；`code-gated` ⇒ 绿），`contract-only` 已被机械排除（归档 + 改码 ⇒ **0 项红 = 放行**，C3 形态）。
  两条候选（uniform / code-gated）**都闭合** §1.2 的绕过口 ⇒ 不是「哪条唯一正确」，而是**愿不愿意让纯归档 PR 也吃新红类**——
  这是口味/政策，**推不出唯一答案**，该停轮。✓
- **Q2〔要不要把归档命名收紧成 `archive/<id>`〕——合法政策题，但**不必**卡本 change。**
  复审稿自己写明「**不影响本 change 的实现**」（D8 在两种命名下都成立）；
  且机械门只解析**报告**（`reviews/grill-design.md`）的 `## Open Questions`，那份报告里**只有 Q1**，
  故 **Q2 不进机械判据**。⇒ **停轮队列实际是 1 条（Q1）**；Q2 可作为「顺带问一句」的政策题，
  否则会拿一个不影响实现的远期问题卡住这一轮。⚠️ 注意：Q2 的成本数字有误（见新发现 N-2）。

## 6. 一致性 / `specs/**` / 既有测试

- **Q 编号一致性 ✓**：`design.md §2.6` 用 **CQ1/CQ2/CQ3**、`§8` 用 **Q1/Q2**，其余 `Q2/Q3/Q4`
  只出现在「（原 Qn）」历史标注里；`spec.md` / `tasks.md` **零** `Q<n>` 悬空引用（`grep` 核过）。
- **R1 的三处事实/引用订正 ✓**：`design.md` 指向 tasks 的悬空引用已改 **G6 → G7**；
  `docs/gate.md` 的「幂等」实测**只在 `:9`/`:52`/`:497`，§3.2（`:199-222`）内 0 处**（`grep -c` = 3）；
  全库 `唯一闭合` 只剩**否定式**表述。⇒ M4/M5/M6 到位。
- **`specs/**` ✓**：本 change 的 spec 有 **7 条 Requirement / 20 条 Scenario**；
  「五个否定面」逐条对得上（新建 / 改删 / 受保护 spec / 部分 move / 同 diff 改写）；
  每条 Requirement 都有对应先红用例或护栏 Scenario；`docs/gate.md:245-246` 那句「`archive/**` 下的 events 被读不到」
  仍在位（**本 change 之后为假**，G2 已列）。
- **必须保持绿的既有测试（逐条 `grep -c` 核过存在）**：
  - `tests/test_archive.py` **6 条**——尤其 `test_archiving_a_change_passes_without_events`（纯归档 + 合规证据 ⇒ 仍绿）
    与 `test_archived_change_is_no_longer_validated_as_active`（**不复报「change 目录不存在 / 缺少必需件」**）。
    ⚠️ 它们用的归档名 **`archive/add-retry`（与源 id 同名）** ⇒ 末段比对恰好成立。**实测**：
    同名归档在 `today` 与 `fixed` **都绿**、且 `change 目录不存在` 不出现（P6/§3）。
  - `tests/test_require_change.py` **8 条**（N1 的 `test_source_change_without_change_dir_is_rejected` 在内）；
  - `test_renaming_within_the_active_change_still_needs_events`（active 内纯改名仍要事件）**实测修后仍红** ✓；
  - `test_archiving_a_protected_spec_still_needs_an_event`（受保护 spec 挪进 `archive/` 仍要事件）**实测仍红** ✓；
  - `tests/test_manifest_build.py`（`test_unknown_change_is_rejected`：归档 fallback 不得吞掉「找不到」，
    `test_rebuild_without_explicit_ids_is_byte_identical`：D8 动了 `change_id` 来源 ⇒ **幂等**必须仍逐字节）、
    `tests/test_check_contract.py`（`:88` 的 `"0 个 change 目录" in out` 子串**在位** ⇒ R6 建议保留子串是对的）、
    `tests/test_events*.py`、`tests/test_check_protected.py`。
  - 全量基线 **496 passed**（我在隔离副本里复跑一致）。

## 新发现（均**非阻塞**）

- **N-1〔低·文档〕别名在「部分 move」残留下**接受外来 change 的 id，D8/R4/§2.5 没写这条。**
  见 §1.2/§1.3。**为何不阻塞**：它不越过 E2 的能力上界（不用别名也拿得到同一个绿），
  属既有边界（`防漂移不防伪造`）的**同类**；但「接受集合含外来 id」这一点该**明写**，
  免得日后有人以为「别名只在两种**自己的**名字间切换」。建议在 `D8` 末段与 `§2.5` 残留边界 2 各加一句。
- **N-2〔低·事实〕Q2 的迁移成本「≈240 条事件」应为 ≈480。**
  实测：把一个带 3 份 manifest 的归档目录**改名**（`archive/2026-10-14-gwa → archive/gwa`，纯 `R100`）
  ⇒ `check` **恰好 6 条**「受保护路径被写入」（**每份 manifest 记新路径 `R100` + 旧路径 `D` 两半**）；
  `240 = 3×80` 只算了**一半**，实际 **≈480（2 × 3 × 80）**。
  ⚠️ 这条还与复审稿**自己的** `§1.5` 第 2 条 / `R12` 冲突——那里明写「rename 两半各记一次：3 份 = **6** 条」。
  Q2 是政策题、不影响实现，故**不阻塞**；但数字要订正，否则用户据此拍板会低估一半。

> **R2 总结**：三条阻塞**均真修好**（可重跑）；别名方案**没有**开出新的授予/豁免路径
> （N1–N7 + R1 六种攻击修后全红），其「张冠李戴」只在**已承认的**部分 move 残留下出现、且**不改变红绿**；
> R1 两处反驳**都成立**；停轮队列**实际 1 条（Q1）**。建议只在**文档**上补 N-1 一句、订正 N-2 一个数——
> 二者都不构成再来一轮对抗的阻塞项。
