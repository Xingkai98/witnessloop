# 对抗轮 R10

> 独立零记忆对抗者。本报告里凡标「实测」的都有命令与原始输出；凡在本工作区不可复算的
> 一律进 `## 未验证项`，**不**计入必须修改项。文档里的「实测 / 已落库 / 已收敛」自述
> **不作为证据**，能重算的一律重算。

## Reviewer

- 身份：R10 独立零记忆对抗者（只读该 revision，不继承前九轮的结论）。
- 工作树：`/home/happy/wl-wt/archive-arrival-recognition`（分支 `gate-ref-pins-package/2026-10-16`）。
- **`git rev-parse HEAD` = `24582f1c994c90cc90708a1393c32eaa06aac205`**（题面给的冻结 revision，实测一致）。
- 本轮**未**在本仓做任何 commit / reset / tag / push；实验一律在 `/tmp/adv10/` 的快照副本
  （`git archive HEAD | tar -x`，`PYTHONPATH=/tmp/adv10/src/src`）里跑。
- 关键文件 blob（`git hash-object <file>`，本 revision 实测）：

  | 文件 | blob |
  |---|---|
  | `docs/gate.md` | `fde483098e6af873f01922f8cea4075ad024ebf7` |
  | `README.md` | `3bd4dc951af8c99ca5bc8899b1b370ce1edac339` |
  | `src/witnessloop/initcmd.py` | `411081cd7e752efe87bca382ce0b580a49745834` |
  | `src/witnessloop/checkcmd.py` | `e12db4d94a1d11daebc80eb1423298de57bf487a` |
  | `src/witnessloop/constants.py` | `0a64184d5435399646646356fac56dd68622ffb0` |
  | `.github/workflows/gate.yml` | `330104b810db66a7c382c89ec075a04cfb03798c` |
  | `openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md` | `f74c358a963fccaa747b9a25dd2bcfe838c8afdd` |
  | `openspec/changes/gate-ref-pins-package/design.md` | `41d4578ea97be4a069b3ace83c846eb40409bcde` |
  | `openspec/changes/gate-ref-pins-package/tasks.md` | `73aca022d35341ca5d63b3751d976a2f67d3d9cc` |
  | `openspec/changes/gate-ref-pins-package/proposal.md` | `903714c3fc903289fb93927e313cbe76d90cc71b` |

- 基线复算：`PYTHONPATH=src python3 -m pytest -q` ⇒ **`688 passed in 31.82s`**（exit 0），与题面一致。
- 判据口径：本轮只把**可证伪**项算数；措辞 / 计数 / 格式类不算证伪；先于本 change 存在的行为
  按题面纪律登记为低危观察。

## 对抗结论

### 1. 判据②（前九轮必须修改项是否全部落库）—— 逐条对正文与代码复核，**不采信 §7.9 自报表**

两条独立的方法：

1. 逐项到**该 revision 的正文 / 代码 / 钉子**里找那条东西本身（不是找 §7.9 表里那句「✅ 落地」）；
2. 把每轮 §7.9 表格的**「落点」列**与该轮落地提交的 `git show --stat` 比对，看落点里点名的文件
   是否真被那次提交改过（`git log --format='%h %s' | grep 落对抗轮` 取全部落地提交）。

**方法 2 的结果（机械比对，可复算）**：R1–R8 各轮落点里点名的文件都在对应提交的 `--stat` 里；
**只有 R9 的 W2 一行是例外**——落点写了 `docs/gate.md §1.2`，而 `24582f1` 根本没碰 `docs/gate.md`
（原始输出见 X1）。这条**不是**文档漂移，是「上一轮必须修改项没做完，却被写成了做完」。

**方法 1 的抽样锚点**（都能在该 revision 上直接读到；不逐条贴输出，只给落点）：

| 轮 | 项 | 本 revision 上的锚点 |
|---|---|---|
| R1 | K1（「包无法自报 ref」是假的） | `spec.md:71-72`（原稿订正注） |
| R1 | K2 | `proposal.md:19-29`（「没有任何提示」是假的…已改写） |
| R1 | K6 | `docs/design.md:56` 与 `:73` 两处都带「由 `gate.yml` 从 `job.workflow_sha` 推导」 |
| R1 | K3/K4/K5/K7/K8 | 正文可见；K8 的**证据本体**属不可复算 ⇒ 未验证项 U-1 |
| R2 | L1/L2/L4/L6 | 落点文件都在 `6813c8e` 的 `--stat` 里；L2 的「两步 recipe + 旧 CLI 症状」在 `docs/gate.md §1.2`（102-110）与 `README.md:198-200` |
| R3 | M1–M4 | `315574c` 的 `--stat` 含 constants/gate.yml/docs/README/tasks/tests；本轮**独立 grep 复核** 6.1 的「字面量族」：活面 `@v1` 只有 `constants.py:22`、`gate.yml` 的 `WL_FALLBACK_REF`、`tests/test_gate_workflow.py:59`，另加「不改但要保住前提」的 `NEW_REF`（`tests/test_init_gate_ref.py:28-32` 与 `:46`） |
| R4 | N1–N3 | `1099284` 的 `--stat` 含 `docs/gate.md` |
| R5 | P1 | `b186cfa` 的 `--stat` 含 `initcmd.py` + 钉子 |
| R6 | T1 | 钉子 `tests/test_gate_workflow.py:532 test_the_install_step_consumes_the_resolved_ref`；recipe 顺序钉子 `tests/test_docs.py:286` |
| R7 | U1–U4 | 钉子 `tests/test_gate_workflow.py:552/576/589`、`tests/test_check_package_ref.py:154/170` |
| R8 | V1 | `caller_retarget_refusal`（`initcmd.py:193-230`）+ 钉子 `tests/test_init_gate_ref.py:379`（实测：见 §「低危观察 O1」） |
| R8 | V2 | 代价段落 `docs/gate.md §1.2`（118-131）+ `README.md:209-212` |
| R8 | V3/V4 | 四类来源断言在 `tests/test_gate_workflow.py:552`（U1 行）|
| R9 | W1 | `spec.md:128-130` + `initcmd` 注释措辞已是「由 `caller_retarget_refusal` 变响亮」 |
| R9 | W3 | 三处同口径的 `not entry.get("self")` + 钉子 `tests/test_init_gate_ref.py:408` |
| R9 | W4 | `tasks.md:128-133`「按语义找 + `grep -n "@v1" README.md docs/gate.md`」 |
| R9 | **W2** | ⚠️ **半落库**：规格半边已落（`spec.md:101` 的 Given 前提 + `:105-108` 的 ⚠️ 段，`git blame` 显示由 `24582f1` 写入）；**文档半边未落** ⇒ **X1** |

### 2. 判据② 的例外 = X1（详见「必须修改项」）

`docs/gate.md §1.2`（那正是 W2 落点点名的位置）在本 revision 上**仍然只写一种成因**，
并且仍然留着被 W2 实测证伪过的那句无条件承诺；`README.md` 的升级 recipe 同病。

### 3. 判据①（本轮有没有新的可证伪项）

- **新的行为缺陷：0 条。** 我没有找到任何用户会真撞上的新行为缺陷（题面优先项）。
- **题面建议的四条攻击面，逐条实测结果**（都在 `/tmp/adv10` 快照副本上真跑）：

  1. **`caller_retarget_refusal` 与 `sync_caller_gate_ref` 的组合能否被绕过**（两次读台账之间状态变化？）
     —— 实测**不能**：在「台账里没有 caller 条目 **且** 盘上没有该文件」的态上，
     `--dry-run` 与真跑**都**退 1 并打出同一句拒绝文案，caller 没有被凭空建出来、台账没被写：
     ```
     $ python3 -m witnessloop init --root . --dry-run --gate-ref …@v9.9.9
     init：无法按 --gate-ref 改 caller：.github/workflows/witnessloop.yml 既不在盘上、…（拒绝文案）
     dry-run EXIT=1
     $ python3 -m witnessloop init --root . --gate-ref …@v9.9.9
     （同一句） 真跑 EXIT=1
     ```
     两处读都是同一次进程内的同步读，中间没有别的写者；`--dry-run` 走的是同一条拒绝分支（fail-closed，合理）。
     ⇒ **不出题面担心的那个洞**。
  2. **未接入仓 + `--gate-ref`**（`desired_files(新 ref)` 与一份已存在的外来 caller 冲突）
     —— 已有钉子：`tests/test_init_gate_ref.py:175 test_foreign_caller_in_a_new_repo_still_conflicts`
     （整体不落盘）与 `:193 test_uninitialized_repo_writes_the_requested_ref`（干净新仓写进所请求的 ref）。
     ⇒ **已被钉住**。
  3. **`docs/gate.md §1.2` 的 ①′ recipe（`2>/dev/null | head -1`，而 `check` 在该态退出码非 0）会不会误导**
     —— recipe 成立：`check` 的自报行是它打印的**第一行**且在**任何 git 操作之前**（钉子
     `tests/test_check_package_ref.py:170`、`:83`），管道只是取行、退出码被管道吞掉属刻意（它自称「自证」，
     不声称通过）；同段 118-131 另有「升级 PR 会被自己的门禁拦一次」的显式警告。⇒ **不误导**。
     （唯一可挑的是没提醒 `| head -1` 会掩盖 `check` 的非零退出码；属措辞级，不进必须修改项。）
  4. **本 change 的每个 `spec.md` Scenario 是否都有行为级钉子** —— 逐个点名（12 个 Scenario 全覆盖）：

     | Scenario | 钉子 |
     |---|---|
     | 改一处、两处跟着变 | `test_resolve_prefers_the_reusable_workflows_own_sha`（`test_gate_workflow.py:357`）+ `test_the_install_step_consumes_the_resolved_ref`（`:532`，端到端「安装步吃不吃解析结果」）|
     | 显式 `with:` 覆盖仍然有效 | `:372` + `:385`（后者：job 上下文不可用时显式意图仍优先）|
     | 畸形 / 不可接受的输入 | `:392` `:407` `:420` `:438` `:454` `:482` `:508`（七条，含 repository 不匹配**不**落到 `workflow_ref`）|
     | 日志里能直接读到 ref | `:552`（四类来源文案）+ `:324`（是第一个 step）|
     | 能取到元数据 | `test_check_package_ref.py:31` `:90` `:66` `:99` |
     | 取不到元数据 | `:38` `:141` `:116`（宽 `except` 不吞 `BaseException`）|
     | 干净不动点 | `test_init_gate_ref.py:58` `:100` `:111`（⚠️ 但这条的 W2 前提见 O2）|
     | 不给 flag 时不动 | `:142` `:151` `:100` |
     | `--dry-run` 只预览、不许谎报幂等 | `:205` `:222` `:266` |
     | 台账里没有 caller 条目 | `:299` `:379` `:408` `:162` |
     | 与冲突的 `--policy` 同时给出 | `:235`（+ 对偶的 `:266`）|
     | 边界可见（caller 不受保护）| `tests/test_docs.py:268`；升级路径文档侧 `:277`、recipe 顺序 `:286` |

     ⇒ **12 个 Scenario 都有行为级钉子**（判据①在这一维上没有缺口）。
  5. **三处文档是否说同一件事** —— **不一致**，就是 X1 本体：`spec.md:105-108` 说两种成因，
     `docs/gate.md §1.2` 与 `README.md:198-200` 只说「旧 CLI」一种；且两处用户文档都没有
     「`uninit` 会把 caller 与台账（实测还有 `policy.json`）一起删」的警告。
  6. **`tasks.md §6` 与 `design.md §2 D4` 在 W2 之后有没有新的不一致** —— 没有。D4 / 3.5 / 6.4
     三处都仍把「本仓自身迁移」标成 `(post-merge)`、不在本 PR 内；`tasks.md:55-59`（3.5）与
     `:135`（6.4）内容一致；6.1 的「先改常量再 tag」时序与 D4 无冲突。

- **措辞 / 观察类（按纪律不算证伪，见低危观察）**：3 条（O1–O3）。
- **先于本 change 存在的行为**：`created_files` 元素非对象仍崩、`--gate-ref ""` 等价于不给、
  `…@refs/heads/` 空后缀——R9 已登记不修，本轮未重跑、也未新增。
- **本轮没做的新变异**：除 O2 那一次（删 spec 的 W2 段，见下）外未新增变异；题面声明的
  50+ 条历史变异未重跑。

### 4. 低危观察（**不计入**必须修改项，各附理由）

- **O1（措辞类 / 有措辞先例）**：`design.md:373`（R8 的 V1 行；R9 小节从 `:350` 起）
  把 V1 的落地写成「做不成**响亮拒绝**（退 1、**不写任何东西**）」。实测在同时给 `--test-command` 时
  **会写**测试执行点再退 1：
  ```
  $ python3 -m witnessloop init --root . --gate-ref …@v9.9.9 --test-command "echo NEW"
  init：无法按 --gate-ref 改 caller：…（拒绝文案）
  init：已写入测试执行点 .github/witnessloop-tests.txt（--test-command 覆盖已有内容）
  EXIT=1
  ```
  台账未被写（`gate_ref` 仍是 `@v1`、条目未补）、caller 未复活 ⇒ **spec 的该 Scenario 要求
  （「SHALL 响亮失败（EXIT≠0 + 一句说明）」、「SHALL NOT 凭空新建 caller」「SHALL NOT 报幂等」）
  全部满足**；写测试文件是既有 `--test-command` 先例（Z1/O2：显式意图写在前）。⇒ 只是
  `design.md` 那句括注过强，建议收窄为「不写 caller 与台账」，**不改代码**。
- **O2（缺一条钉子，但被钉的行为先于本 change 存在）**：W2 描述的那条终态
  （定制 policy 的仓在 `init --gate-ref X` 之后，随后 plain `init` 仍退 1、不是不动点）
  在本 change 的测试里**没有钉子**——把 `spec.md:105-108` 那段 ⚠️ 整段删掉，
  全量照样全绿：
  ```
  变异：删掉 spec.md 的 W2 ⚠️ 段（105-108 行） ⇒ 688 passed in 40.56s
  ```
  但「custom policy 冲突 ⇒ `init` 退 1」这条行为**先于本 change 存在**（`origin/main` 上就有），
  按题面纪律登记为观察，不升为必须修改项。
- **O3（口径完整度）**：`spec.md:105-108` 写「`uninit` 会把 caller 与台账一起删掉」——实测**枚举不全**，
  它还会删 `.witnessloop/policy.json`：
  ```
  $ python3 -m witnessloop uninit --root .   # 定制 policy 的已接入仓
  uninit：已回滚 witnessloop 接入：
    - .witnessloop/policy.json
    - .github/workflows/witnessloop.yml
    - .witnessloop/init-manifest.json
  EXIT=0
  ```
  而定制 seed 按 `docs/gate.md:51`（「定制 seed 不入库」）与 `README.md:113` 惯例**不在 git 里**
  ⇒ 那句「不可照做」的劝告是对的，但读者会以为只需重跑 `init` 就能复原，实际可能丢掉
  只存在于盘上的 policy。建议 X1 修的时候顺手把枚举写全。

## 未验证项

以下在本工作区**不可复算**（无 GH 凭据 / 无网 / 目标物尚不存在），按题面纪律登记为未验证，
**不**计入必须修改项；它们也**没有**被本轮当成已证实的依据使用：

- **U-1（Q1 的输入，二手且不可复算）**：真 CI 里 `job.workflow_sha` = reusable 文件自己的 commit、
  `job.workflow_repository` / `job.workflow_ref` 的取值语义，以及 `design.md §2 D1` 转述的跨仓探针
  原始输出（副本仓 `Xingkai98/asterwynd-wl-switch` → `…/probe-ref.yml@probe/workflow-ref`，
  run `38853369550`）。本机无凭据、探针分支远端已删（文档自述 404）⇒ **只读到转述**。
  ⇒「(B′) 在真 CI 上成立吗」这一条本轮**未验证**。
- **U-2**：GHES 上 `job.*` 不可用、同 owner 的 fork 会误匹配 `REPO_SLUG`（`spec.md:21-24`、
  `docs/gate.md:538-539`）——同上不可复算。
- **U-3**：`uvx --from "git+https://…@<ref>"` / `pip install git+…` 的真实安装行为，
  以及 `…@refs/pull/N/merge` 能不能被 uv 装上（`spec.md:41-43` 已**只**做定性、未声称必然失败）
  ——本机无网/无凭据，未实测。
- **U-4**：`v1.7.0` 尚不存在 ⇒ `tasks.md §6.1`「改完四处 `pytest` 全绿」、`§6.7` 的验收命令
  在本 revision 上**尚未执行**（题面已声明是 post-merge，登记不罚）。
- **U-5**：issue #30 正文里的数字与验收证据不在本仓，未核。
- **U-6**：本仓自举 `check` 判绿（`tasks.md 4.3`）与归档 / 回链（`5.2`）**未执行** ⇒ 未验证。
- **U-7（我自己的覆盖面缺口）**：本轮的 `init`/`uninit`/`check` 行为实测都在 `/tmp/adv10` 的
  **本地 git 仓**上做（无 remote、无 GitHub Actions）⇒ 与 CI 相关的行为差异面（`GITHUB_OUTPUT`
  的真实写法、`uvx` 缓存态、`job.*`）一律未验证；`gate.yml` 的解析 step 我只通过
  `bash` 真跑 + 仓内钉子复核（`tests/test_gate_workflow.py` 的 `_resolve*` 家族），
  **没有**在真 runner 上跑过。

## 必须修改项

**X1（唯一一条）· 类别：文档缺口 —— 前轮必须修改项未落库，且被写成了已落库。**

- **事实**：R9 的 W2（`design.md:357`）证伪的是「『干净不动点』那条 Then 对**定制 policy 的已接入仓**
  不成立」，它给的修法有**两个落点**：① Scenario 补前提；② `docs/gate.md §1.2` **两种成因都写**。
  ① 落了（`spec.md:101`、`:105-108`，`git blame` → `24582f1`）；**② 没落**。
- **证据 1（提交级，可复算）**：
  ```
  $ git show --stat 24582f1
   openspec/changes/gate-ref-pins-package/design.md   |  16 ++
   .../reviews/grill-adversarial-r9.md                | 300 +++++++++++
   .../specs/gate-ref-pinning/spec.md                 |  13 +-
   openspec/changes/gate-ref-pins-package/tasks.md    |  11 +-
   src/witnessloop/initcmd.py                         |  15 +-
   tests/test_init_gate_ref.py                        |  25 ++
  $ git show 24582f1 -- docs/gate.md        # ← 空输出（该提交没碰它）
  $ git log --oneline -1 -- docs/gate.md    # → 3865007（R8），R9 之后未再改
  ```
- **证据 2（正文级）**：`docs/gate.md §1.2` = 62-142 行，本 revision 上**只在 102-110 行把那个
  冲突症状归因于「旧 CLI」**（「**误导**：要换的不是 policy，是这个 CLI 太旧…**别去删 policy**，
  先确认 CLI 版本」），且 86-88 行仍留着**无条件**承诺：
  ```
  $ sed -n '86,88p' docs/gate.md
    2. 再 `witnessloop init --gate-ref <同一个新 ref>` ⇒ **重写 caller + 同步台账**
       （`init-manifest.json` 里该条目的 `sha256` 与 `gate_ref`），其余文件照旧只增不改；
       之后 plain `init` 回到幂等、`uninit` 仍可用。
  ```
  `grep -n "定制\|出厂" docs/gate.md` ⇒ 51, 59, 169, 538, 539, 738, 743, 747——**§1.2（62-142）区间内零命中**，
  即「定制 policy」这一成因在 §1.2 里根本没出现。`README.md:198-200` 同病
  （「用旧 CLI 跑第 ② 步会得到…**误导**（要换的不是 policy，是 CLI 太旧）」）；
  `README.md` 里 `grep -n uninit` ⇒ 8, 49, 115, 133, 199, 214，**无一处**警告它会连 caller + 台账一起删。
- **证据 3（行为级，实跑复现；正是 W2 描述的那类仓）**：
  ```
  # ① 用 --policy 接入（定制 policy 的仓）
  $ python3 -m witnessloop init --root . --policy /tmp/adv10/seed.json     → EXIT=0
  # ② 按 §1.2 走升级动作（**新版** CLI）
  $ python3 -m witnessloop init --root . --gate-ref …gate.yml@v9.9.9      → EXIT=1
    init：检测到冲突（…只增不改，拒绝覆盖。要更换 policy 请先 `uninit`）：   ← §1.2 说这条只可能是「旧 CLI」
    init：已重写 .github/workflows/witnessloop.yml（→ …@v9.9.9）并同步台账
  # ③ 随后 plain init（§1.2 承诺「回到幂等」）
  $ python3 -m witnessloop init --root .                                    → EXIT=1（同一句冲突文案）
  # ④ 若照文案与「先确认/按提示」的路子去 uninit
  $ python3 -m witnessloop uninit --root .                                  → EXIT=0，删掉 policy.json + caller + 台账
  ```
- **为什么这是必须修改项（而不是措辞）**：① 它是**上一轮登记过的必须修改项**、落点点名了该文件，
  却没落 —— 判据② 直接不满足；② 它是**用户真会撞到**的：按 §1.2 / README 的 recipe 走两步的
  接入方，只要 policy 是定制的（**本仓自己就是这一类**，`README:271` 已自认 `init` 跑不动），
  就会拿到那句「请先 `uninit`」，而照做会**连 caller + 台账 + policy 一起删**；定制的 policy 按
  `docs/gate.md:51`/`README:113` 的惯例**不入库**，删掉后可能根本恢复不了；
  ③ §1.2 那句「之后 plain `init` 回到幂等、`uninit` 仍可用」在本 revision 上**仍是假的**（步骤 ③ 实测 EXIT=1）。
- **证据 4（被写成已验证）**：`design.md:355` 写「…四条全在规格/文档/钉子层面，**已逐条落库**」，
  `reviews/grill-adversarial-r9.md:285` 更是直接断言「`docs/gate.md §1.2` 的那段**现在两种成因都写了**」。
  两句在本 revision 上都不成立。
- **最小修法（建议）**：`docs/gate.md §1.2` + `README.md` 升级 recipe 各补一句「若本仓 policy 是
  定制的（≠ 出厂默认），第 ② 步会退 1 并报 policy 冲突——**这不是 CLI 旧**，且**不要照那句
  『先 `uninit`』去做**：`uninit` 会连 caller / 台账 / `policy.json` 一起删；出路是
  `init --gate-ref <新> --policy <seed>` 或手工提交 caller + 台账」；并订正 `design.md:355` 的
  「已逐条落库」与 `r9:285` 那句话。注意：这两处文档改动**不会**碰现有钉子
  （`tests/test_docs.py:277` 只断言「先把 CLI 升上去 / `init --gate-ref` / `job.workflow_sha` 在文里」，
  `:286` 只断言顺序），所以夹具不用动。

**下一条 X 不存在。** 其余发现按纪律归入 `低危观察`（措辞 / 先于本 change 存在）或 `未验证项`
（本工作区不可复算），理由逐条已写明。

## Open Questions

- **Q6（给作者）**：X1 的修法形态要不要连「出路」一起写进 §1.2？我建议写，否则读者只被告知
  「别 uninit」，却不知道**该做什么**（本仓自己是走「手工提交 caller + 台账」，见 `README:267-271`
  与 `tasks.md 3.5`）。
- **Q7**：O2 要不要补钉子（把「定制 policy 的仓在 `--gate-ref` 之后 plain `init` 仍退 1」钉住）？
  若不钉，本仓既有态度是「边界要能被机械钉住」（`tests/test_docs.py:92-95` 的注释），
  那就该在 `spec.md:105-108` 明写「此前提**无机械钉子，仅文字**」。
- **Q8**：O1 的 `design.md` 括注「不写任何东西」是否收窄为「不写 caller 与台账」？（**不需要**改代码。）
- **Q9**：`docs/gate.md §1.2` 的 ①′ recipe 要不要补一句「`| head -1` 会掩盖 `check` 的非零退出码，
  这条只用于自证包来源，不代表 `check` 通过」？（措辞级。）
- **Q10（本轮我自己没做的）**：我没有在真 runner 上跑过 `gate.yml`（U-7），也没有复算 §2 D1 的探针
  （U-1）。若作者认为这两条必须有独立复核，需要给出可复算的路径（例如探针分支/文件重建并给 run id）。

## 收敛结论

**不收敛。**

- **判据②：不满足。** R9 的 W2 只落了规格半边；文档半边（`docs/gate.md §1.2`，W2 落点里明确点名的
  那一个文件）没落，而 §7.9 与 R9 报告的处置文本把它写成了「已逐条落库 / 现在两种成因都写了」
  ⇒ 这是「**前轮必须修改项未落库**」+「**未做的被写成做了**」两条同时成立。
  其余各轮（R1–R8、R9 的 W1/W3/W4）本轮逐条对正文 / 代码 / 钉子复核，**均已落库**；
  逐轮把 §7.9 的「落点」列与该提交的 `--stat` 机械比对，也**只有 W2 这一处**对不上。
- **判据①：本轮的结论是「无新的可证伪项」。** 新行为缺陷 **0 条**；题面建议的四条攻击面
  逐条实测：**都不能被绕过**、**都已有钉子**、**不误导**（见「对抗结论 §3」逐条与 12 个
  Scenario 的钉子点名表）。剩下的 3 条是**措辞 / 观察类**（O1–O3），按题面纪律不算证伪。
- **类别陈述（题面要求分开）**：
  - **行为缺陷**：本轮 **0 条**（这是本轮的主要正面结论：`src/` 与 `gate.yml` 的行为层在
    该 revision 上没有被本轮证伪）。
  - **缺一条钉子**：**1 条候选**，即 O2（W2 那条终态无钉子；变异「删掉 `spec.md:105-108` 那段」
    仍 688 全绿）。但它描述的行为**先于本 change 存在**，按纪律**降级为低危观察**，
    **不是**本轮必须修改项。
  - **必须修改**：**1 条**，X1，类别是**文档缺口 / 前轮落点未执行**（不是行为缺陷，也不是缺钉子）。
- **下一轮的最小闭环**：做完 X1 的两处文档补写 + 订正 `design.md:355` / `r9:285` 那两句之后，
  判据② 即可回绿；若同时采纳 Q7，O2 也随之消掉。**在那之前，本 change 不具备收敛条件。**

---

## 处置（主 session 在 R10 之后追加，非审阅者原文）

> 本报告判定**不收敛**（判据②不满足、判据①满足——你明确写了「新行为缺陷 **0** 条」）。
> **X1 已落库**，两条低危观察也一并处理。**X1 抓得对，而且抓到的是我的自述与事实不符**：

- **X1（前轮必须修改项未真正落库）**：R9 的 W2 我在 `grill-adversarial-r9.md` 的「处置」里写
  「`docs/gate.md §1.2` 的那段现在两种成因都写了」——**那是假的**：`git show --stat 24582f1`
  里根本没有 `docs/gate.md`。**本次真正落库**：`docs/gate.md §1.2` 现在有一段专门的
  「**同一条冲突还有一个『不是旧 CLI』的成因**」——定制 policy 的仓跑升级动作也会退 1、
  随后 plain `init` 不报幂等；**并写明那句「要更换 policy 请先 `uninit`」不可照做**
  （`uninit` 会把 `policy.json`、caller、台账一起删，而定制 seed 按惯例不入库 ⇒ 恢复不回来），
  给出正确做法（`init --gate-ref <新> --policy <你的 seed>`），并限定「干净不动点」那句承诺的适用范围。
  ⚠️ 教训记在这里：**「处置」里写「已落库」必须以落地提交的 `--stat` 为准**，不能凭记忆——
  你这轮用 `git show --stat` 逐轮比对正是抓住它的方法。
- **O1（拒绝前已经有写入）**：接受。把 `caller_retarget_refusal` 的调用**提到 `if manifest_path.is_file():`
  块的最前面**（在 `--test-command` 那条轴之前）⇒ 做不成时**一个字节都不写**；
  钉子 `test_a_refused_retarget_writes_nothing_at_all`（断言测试执行点也没被写）。
- **O3（`uninit` 的危害枚举漏 `policy.json`）**：已补进 `spec.md` 的对应 Scenario。
- **O2（W2 的终态无独立钉子）**：接受你的判断——那条终态（定制 policy 的仓 plain `init` 照旧退 1）
  **先于本 change 存在**，属既有行为面 ⇒ **登记不修**。

**R11**：树在该 revision 上冻结。你已判「新行为缺陷 0 条、12 个 Scenario 逐个点名全有行为级钉子」——
若下一轮确认 X1 落库且无新项，**请如实判「已收敛」**；若仍有新项，照旧标明类别。
