# Grill v2: adopter-test-gate 设计追问（v2 · 机械版）

> 零记忆独立审阅者产出。算法与格式依据 `templates/grill.md`（7 维追问 + 设计树求完备 + 第 4 步决策记录）。
> 立场：**挑战而非确认**。前一轮（v1 稿）的 `reviews/grill-review.md` / `reviews/grill-adversarial.md`
> 我没读「结论」，只把它们的**实测事实**当输入复核了一遍；v2 反转后的**方案选择**全部重新打。
> 被审 worktree **全程只读**，唯一仓内写入是本文件（见文末「仓内写入」）。
>
> **一句话结论**：**反转本身是对的**——「没有存量接入方」这条前提我**独立复核成立**（A 节），
> 所以「只能给文档」那个收敛确实没有了理由；但反转后的**三条新机制里有两条第 3 个设计树节点没走**，
> 而它们恰好都落在**本仓自己身上**：
> ① **缺省语义没定**（`design.md:113` 的「默认 = 命令文件路径」两种读法后果相反：一种让**本仓自己**
>    在移动 `v1` 之后**立刻红**，另一种不判)——这是 A 节要补的节点；
> ② **种子文件进不进 `desired_files()` 没定** ⇒ 若进，接入方**改一次命令**就再也跑不了 `init`
>    （`init` exit 1，实测 E7b），D3 的「改命令 = 一次普通 commit」在用户可见层面不成立；
> ③ **「文件存在」被当成「已接线」** ⇒ **空文件**这一态作者没写，而它既让 `check` 判**绿**、
>    又让门禁 `sh -c ""` 返回 **exit 0** ⇒ 正是 issue #4 的形态**带上一枚绿勾**。
> 另外两条**操作性**发现：**本仓自己**今天跑 plain `init` 就已经 exit 1（pre-existing，实测 E7a）；
> 而 v1 的**两份报告留在 `reviews/` 里**会撞**孤儿规则**，且 `stage=grill` 的正文校验会因
> **manifest 路径字典序**选中 v1 那份而不是本文件（`evidence.py:197,210` 实测读码）。
>
> **D1 我的推荐与作者相同（甲），但理由要换**、且有天花板必须写进 spec（见 Q7）。
> **D5 我的推荐也与作者相同（移动 `v1`），但顺序要改**：**先给本仓补上执行点、再移 tag**（Q4）。

## Reviewer

- run id: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`
- 时间: 2026-10-13T00:45:59Z
- 被审 revision: `c802152693df29b4a0a886356bf05f4f58b26e7a`（分支 `adopter-test-gate/2026-10-12`）
- 方法（可复现）：
  - 副本 `/tmp/grill2/repo`：`cp -a` 后 `rm -f .git && git init -q && git add -A && git commit -qm base`，
    再 `rm -rf .venv && uv sync`（worktree 的 `.git` 是 `gitdir:` 指针文件，不隔离会写回原仓）。
  - `init` 侧实验（E2–E7b、`/tmp/sim/sim.py`、`/tmp/sim/sim2.py`）**不改仓内任何文件**：只在
    `/tmp` 脚本里给 `initcmd.desired_files` / `initcmd.build_manifest` 打运行时补丁来模拟「本 change 之后」
    的工具，**明确标注**为 SIM；未打补丁的真仓行为另行标注为「真仓」。
  - 平台事实用 `gh` CLI 对**真仓**取证：80 个 owner 仓逐个 `contents` API 探测、全局 `code search`、
    branch protection 重取、以及**本仓自己的 Actions 运行历史**（run `38123102904`）。
  - 文档查证：GitHub 官方 `evaluate-expressions-in-workflows-and-actions`（step 默认语义）与
    `about-status-checks`（skipped job 报 Success）。**取不到明文的**逐条标「未查证」。

## Confirmed Decisions

- **决策**：**「没有任何外部接入方」这条前提成立，且我用的口径比原稿更硬。**
  原稿的证据是 `gh search code --owner Xingkai98 witnessloop` 为空——这条口径**弱**（`--owner` 只覆盖
  自己、且 code search 对本人的私有仓索引不保证覆盖）。我换成**穷举式存在性探测**：`gh repo list Xingkai98`
  取回 **80 个仓**，逐个 `gh api repos/Xingkai98/<r>/contents/{.witnessloop/policy.json,.github/workflows/witnessloop.yml}`
  按**退出码**判命中（404 = 没有）。命中**只有两个**：`witnessloop`（本仓自举）与 `wl-test`。
  再加一次**全局** `gh search code witnessloop`：25 条命中**全部**是别的项目里同名的 `witnessLoop` 标识符
  （RSA witness loop / jcstress `WitnessLoop` 之类），**没有**任何仓引用本仓的 action 或 CLI。
  理由：这是整个反转的地基，必须能被别人一条命令重跑，而不是引用作者自述。来源: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`
- **决策**：**D3 的「命令文件既不在受保护路径、也不在 `require_change_for`」在本仓 policy 与出厂默认 policy
  上都成立——这条是设计里做得最干净的一处。** 逐字核过两份 policy：本仓 `.witnessloop/policy.json` 的
  `protected_paths = ["openspec/specs/**", ".witnessloop/**"]`、`require_change_for = ["src/**","templates/**","plugin/**"]`；
  出厂默认是 `policy.py:30-49` 的 `["openspec/specs/**",".witnessloop/**"]` + `constants.py:27-36` 的 8 条目录。
  `.github/**` **两边都不在**，也不在不变集（`policy.py:18-23`）里 ⇒ 种一个 `.github/witnessloop-tests.txt`
  不需要解释事件、不触发 `require_change_for`。
  理由：D3 的前提若错，整个「命令能自由改」的论证就塌；我按「本仓 + 出厂」双份核了两遍。来源: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`
- **决策**：**「新增 `init` 产物到不了已接入仓」在 v2 里仍然成立，但它现在是一条「**我自己**受影响」的路径，
  不是「无所谓」的路径。** 两条独立实测：① SIM（给 `desired_files` 加第四个文件）在一个**由旧工具接入**
  （台账里只有三件套）的仓上跑 `init` → 输出 `init：已接入 witnessloop（幂等，无改动）。`、**exit 0**、
  命令文件**没落盘**；机制是 `initcmd.py:166-167` 进 `_already_initialized`，无漂移无冲突时在
  `initcmd.py:280-281` 直接返回，**唯一写盘路径 `initcmd.py:188-194` 根本走不到**。
  ② **本仓自己**（真仓 policy、台账里三件套）：**不打任何补丁**跑 `init --dry-run` 就是 **exit 1**
  （定制 policy 与出厂默认不同 ⇒ `initcmd.py:265-278` 的「已接入 + 本次期望」冲突分支）。
  ⇒ 结论：**本仓自己既拿不到种子文件、`init` 也早就是坏的一条路**——反转后必须有人**手工**给它补一份
  命令文件（或显式 opt-out），这件事 `tasks.md` 里**没有任务**。
  理由：这正是「反转的地基」与「反转后的第一条落地」之间的缝。来源: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`
- **决策**：**「不进 hash 台账」是承重设计，且它不是自然实现——最自然的写法会让接入方改一次命令就失去 `init`。**
  实测两种形态：**SIM-naive**（把命令文件直接加进 `desired_files()`）⇒ 文件顺带进 `created_files` 台账 ⇒
  接入方把命令改成 `uv run pytest -x -q` 后：`init` 报「已接入，但 init 创建的文件被改动过（拒绝覆盖）」**exit 1**
  （`initcmd.py:220-239` 漂移分支）、`uninit` **也** exit 1（`uninitcmd.py:66-89`）。
  **SIM-out-of-ledger**（`build_manifest` 里剔除它）：漂移没了，但 **`init` 仍 exit 1**——因为
  `initcmd.py:265-278` 的 `conflicting_files(root, desired)` 用的还是**同一个 `desired`**，接入方改过的内容
  与「本次期望」（不给 `--test-command` 时 = 哨兵）不同 ⇒ 冲突。
  ⇒ 要让 D3 说的「改命令 = 一次普通 commit」**在重跑 `init` 时也成立**，种子必须**完全不进 `desired_files()`**
  （单独代码路径 + 单独 dry-run/输出），而设计从头到尾**没写这一条选哪边**。
  理由：D3 的「不进台账」只挡住了漂移分支，挡不住冲突分支——两者是**正交**的两条判定（v1 稿已实测过一次同形坑）。来源: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`
- **决策**：**D2 的平台语义我用本仓自己的 CI 历史钉死了：默认语义下前一步失败 ⇒ 后续步骤 `skipped`，
  而 job 的最终结论仍是 `failure`。** `gh api …/actions/runs/38123102904/jobs`（本仓 `dogfood-bootstrap`
  分支上一次真失败）逐步骤结论：
  `Set up job=success, Run actions/checkout@v4=success, Run astral-sh/setup-uv@v5=success, uv run pytest=failure,
  打包冒烟=skipped, Post Run setup-uv=skipped, Post Run checkout=success, Complete job=success`，
  **job conclusion = `failure`**。官方 `evaluate-expressions-in-workflows-and-actions` 亦明文：
  「A default status check of `success()` is applied unless you include one of these functions」。
  ⇒ 推论两条：(a) `design.md:50-51` 的「默认 step 语义下 `check` 失败 ⇒ 测试步骤不执行」**对**；
  (b) 同处的「`if: always()` 又会让测试的失败**掩蔽** `check` 的失败」**不对**——两个 step 的结论各自上报，
  job 结论两者皆红，**没有掩蔽**；真正的掩蔽开关是 `continue-on-error: true`（本 change 不涉及，但别写错理由）。
  另外 `about-status-checks` 明文：**被跳过的 job 会报 Success**。来源: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`
- **决策**：**required 的粒度确实是 job，且 context 字符串就是 `gate / check`——复核属实，这是本设计唯一真正的天花板。**
  `gh api repos/Xingkai98/witnessloop/branches/main/protection` 重取：
  `required_status_checks.contexts = ["gate / check"]`、`strict=true`、`enforce_admins=true`、
  `required_approving_review_count=0`、`require_code_owner_reviews=false`。
  并且真仓 run `38269060952` 的 job 列表就写着 `gate / check`。
  理由：它决定了「测试与 `check` 同 job ⇒ 零**新增**人工步骤」，也决定了任何独立 job 方案都要再勾一次。来源: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`
- **决策**：**「唯一存量 `wl-test` 无所谓」这句要补一个更硬的理由：它连 branch protection 都开不了。**
  `gh api repos/Xingkai98/wl-test/branches/main/protection` → **HTTP 403**「Upgrade to GitHub Pro or make
  this repository public to enable this feature」（`private: true`，非 Pro）。
  ⇒ 「测试失败 = 合不了」这条承诺在 `wl-test` 上**从来就不可能成立**（没有 required check 可言），
  所以「移动 `v1` 会波及它」的实际影响只剩「它下次 CI 跑新 CLI」，`design.md:86-87` / R8 的严重度评估是**偏高**的。
  理由：结论（可删、可接受）不变，但理由句要换——`design.md:87` 写的「把它的 caller 钉回 `v1.5.0`」这条规避法
  在它身上只影响 CLI 版本，不影响门禁强度。来源: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`
- **决策**：**v1 的两份报告留在 `reviews/` 里是一个机械问题，不是措辞问题。**
  读码实测：`contract.py:185-220`（`_check_orphan_reports`）对 `reviews/` 下**每个 `*.md`（递归）**
  要求被某份 manifest 的 `report_path` 绑定，否则报「孤儿报告」；而 `validate_review_manifests`
  （`contract.py:126-151`）在**没有任何 manifest** 时**提前返回**、根本不查孤儿。
  **关键**：v1 的 CLI（`git show v1:src/witnessloop/contract.py` 第 146/148/184/214 行）**已有这条规则**
  （v1.4.0 的 #1）⇒ 本 change 的 PR 由 v1 把关（前轮 B1），**孤儿规则现在就生效**。
  另：`evidence.py:192` 用 `sorted(change_dir.glob(manifest_glob))`、`evidence.py:197,210` 取 `matching[0]`
  ⇒ 若为两份 grill 报告各建一份 `stage=grill` manifest，字典序在前的 `grill-review.manifest.json`（v1）
  **会赢**（`grill-review… < grill-v2-review…`），于是**被校验正文的是 v1 那份报告**，而它没有用户确认段
  ⇒ 报一串「Open Question Qn 未经用户确认」。文件名 `grill-v2-review.md` 反而让 v2 的报告**免检**。
  理由：这是本文件本身带来的副作用，作者排期时必须处理（见 Q5）。来源: `grill-reviewer-adopter-test-gate-v2-2026-10-13T004559Z`

## Code-Resolved Questions

- **CRQ-1｜「空文件」这一态：`check` 判**绿**，门禁跑 `sh -c ""` 也 exit 0 ⇒ 双重绿。**
  按 `design.md:69` 的判据（① 文件存在 ② 不含哨兵），空文件两条都满足 ⇒ 绿。我再用真 shell 验了门禁那一步：
  `printf '' > /tmp/e.txt; sh -c "$(cat /tmp/e.txt)"; echo $?` → **exit 0**（空白文件同）。
  ⇒ 结果是「有执行点、门禁跑了、required 绿、测试一个没跑」——**正是 issue #4 的形态，外加一枚绿勾**。
  证据：`design.md:69`、`spec.md:38-41`、实测输出。「写过但没写内容」这一态在 `design.md` / `spec.md` /
  `tasks.md` 里**一个字都没有**（`grep -rn "execution_point\|REPLACE-ME\|witnessloop-tests" src/ tests/ docs/ README.md templates/`
  零命中 ⇒ 是全新面）。**建议**：判定加第三条「**去空白后非空**」，并给它一条 Scenario。
- **CRQ-2｜哨兵文件会被门禁**当命令执行**，症状是 bash 语法错而不是清晰文案。**
  实测：`printf '<<REPLACE-ME>>\n' | … sh -c "$(cat …)"` → `sh: 1: Syntax error: end of file unexpected`、**exit 2**。
  `spec.md:56` 只写了「文件不存在时 SHALL 跳过」，`tasks.md:31`（C1）也只写「存在 ⇒ 读出内容；不存在 ⇒ 跳过」
  ——**「存在但是哨兵」没人管**。⇒ 新接入方跑完不带 `--test-command` 的 `init` 后，第一个 PR 的门禁
  会红在一个**语法错误**上（`check` 的红是清楚的，门禁这条不是）。**建议**：C1 明确「文件缺失**或内容为哨兵** ⇒ 跳过」。
- **CRQ-3｜「改命令不撞台账」的 Scenario 字面为真、用户可见为假。**
  `spec.md:31-34` 的 Then 只承诺「`init` / `uninit` 的**台账判定**不受影响」——这句**确实**为真
  （文件不在 `created_files` 里，`uninitcmd.py:42-60` 只遍历台账条目，`uninit` 甚至**不用改代码**就不会删它，
  见 `uninitcmd.py:20-27,42-60`）。但接入方实际会做的是「改完命令，下次接入别的 change 时再跑一次 `init`」
  ⇒ **exit 1**（实测 E7b，机制 `initcmd.py:265-278`）。⇒ 这条 Scenario 是本 change 里
  **最像「诱导错误泛化」的一处**：它用一个精确措辞把一条会咬人的行为写成了安全。
- **CRQ-4｜本仓自己的 `init` 今天就坏，与本次改动无关。**
  真仓、**未打补丁**：`init --dry-run` → `exit 1`。成因是定制 policy（`require_change_for` 三条、
  缺 `evidence.grill_stage` 等）与出厂默认不同，命中 `initcmd.py:265-278`。⇒ 「本仓自己是接入方」
  不能当作「顺带就行」——**它没有一个可用的 `init` 入口**，所有迁移动作都得靠手工提交。
- **CRQ-5｜`policy.from_doc` 的缺省语义有**两种读法**，后果相反，设计没定。**
  `design.md:113` 写「`tests.execution_point`（默认 = 命令文件路径；显式空/`--no-tests` ⇒ 不判）」。
  读法甲「**字段缺省 ⇒ 用出厂默认**」（= 本仓既有惯例，`policy.py:94-95` 的注释明写「保护性默认，
  别让老 policy 静默失去这条规则」；`require_change_for` 就是三态：缺省→默认、显式 `[]`→关，`policy.py:96-104`）；
  读法乙「**缺省 ⇒ 不判**」。
  两者对本仓自己与 `wl-test` 的后果：两份 policy 都**没有** `tests` 键（我逐字读过 `.witnessloop/policy.json`
  与 `wl-test` 的 policy.json）⇒ 甲 = 移动 `v1` 后**两边立刻红**（文件不存在）；乙 = 都不判、零迁移。
  ➡️ 见 Q1（我推荐甲，但要配套一条迁移任务）。
- **CRQ-6｜opt-out 对**已接入**仓不顺：`--no-tests` 只能在新接入时给。**
  `init` 的 flag 只在未接入分支有意义（`initcmd.py:166-167` 之后就是幂等/冲突分支，`tasks.md:22`（B3）
  也只写 `init --no-tests`）。已接入仓要 opt-out 只能改 `.witnessloop/policy.json`，而它是**不变集**
  （`policy.py:18-23`）且状态是 `M` ⇒ 命中 `checkcmd.py:194-215`（`status[:1] == "A"` 的豁免**只**给新增）
  ⇒ **每次 opt-out 都要写一条 `protected_write_event`**。这条摩擦 `design.md:73` 没写。
- **CRQ-7｜`design.md:60-61` 说「不进台账、不参与 `uninit` 删除」——后半句是免费的。**
  `uninitcmd.py:42-60` 只遍历 `manifest["created_files"]`；文件不在台账里就永远不会被它看到
  ⇒ **不需要任何 `uninitcmd.py` 改动**。`tasks.md:20`（B1）把它写成一条要实现的语义，实现者可能白改一遍
  `uninitcmd.py`（改了反而有风险：`uninitcmd.py:37` 是 `initcmd.desired_files(gate_ref)` 的**单参调用**，
  加参数会撞这里）。
- **CRQ-8｜`spec.md:65` 的「命令出现在 `env:` 里」是一句**实现不了**的断言。**
  设计走的是「**运行时从检出出来的仓里读文件**」（`design.md:41`），所以命令文本**根本不出现在 workflow 里**
  ——能进 `env:` 的只有**文件路径**。`tasks.md:32-33`（C2）写的是「命令经 `env:` 传给 `run:`」，口径不同。
  ⇒ 机械断言按哪个字面写都能过或都不过，取决于实现者怎么理解；**必须在 spec 里把主语从「命令」改成「文件路径」**。
- **CRQ-9｜本 change 自己要不要动本仓 policy，取决于 Q1 的答案。**
  若 Q1 取甲（缺省⇒声明）⇒ **不用动 policy**，只要补一个 `.github/witnessloop-tests.txt` 文件
  （`.github/**` 不在保护面，无事件）。若取乙（缺省⇒不判）⇒ 要让本仓真的被判，就得显式往 policy 里加
  `tests.execution_point`，那**要一条解释事件**（CRQ-6 同理）。`tasks.md` 两种都没安排任务。
- **CRQ-10｜门禁那一步的安全写法（问题 B3 的「语法上怎么写才安全」）。**
  安全形态是：**路径经 `env:`、命令在 `run:` 里运行时读**，不做任何 `${{ }}` 插值：
  ```yaml
  - name: adopter tests
    if: ${{ !cancelled() }}          # 见 CRQ-11
    env:
      WL_TESTS_FILE: .github/witnessloop-tests.txt
    run: |
      if [ ! -f "$WL_TESTS_FILE" ]; then echo "::notice::no test execution point"; exit 0; fi
      CMD=$(cat "$WL_TESTS_FILE")
      case "$CMD" in *REPLACE-ME*) echo "::notice::execution point not wired"; exit 0;; esac
      sh -c "$CMD"
  ```
  理由：`${{ }}` 插值发生在**解析期**，文件内容不受控 ⇒ 插值等于把接入方内容当 workflow 源码；
  `env:` + `cat` 让内容永远只是**数据**。`if:` 里用 `hashFiles(...)` 也可（step 级 `if` 在 checkout 之后求值），
  但把「读文件」与「判存在」放同一处 shell 里，断言面更小、更好测。
- **CRQ-11｜`always()` 不是这里最精确的写法，官方推荐 `!cancelled()`。**
  官方该页原文把 `always()` 描述为「even if the workflow/run is canceled」并**警示**
  「against using it for anything prone to critical failure, such as fetching sources」，
  同时明说「the recommended alternative for running regardless of outcome is `if: ${{ !cancelled() }}`」。
  ⇒ 需求是「`check` 失败时也跑测试」，**不需要**「run 被取消时还跑测试」⇒ 用 `if: ${{ !cancelled() }}`。
  这同时让 `design.md:52` / `spec.md:59-60` 的「二选一」变成**三个选项**（默认 / `always()` / `!cancelled()`），
  我推荐第三个。

## Open Questions

> 下面 8 条是**设计树上的未决节点**，不是风格偏好。每条都落到本 change 的**真实场景**。
> **Q1 是 A 节要求补的那条**，Q2/Q3 是 B 节实测打出来的，Q4/Q5 是「本仓自己」这条路径上的两条。

- **Q1 执行点判定的**缺省语义**：策略里没有 `tests` 键时，`check` 判还是不判？**
  `design.md:113` 的「默认 = 命令文件路径」既可以读成「字段的默认值」也可以读成「`init` 写出的默认值」。
  这一条决定**本仓自己**与 `wl-test` 的下场：两份 policy 都**没有** `tests` 键，
  而移动 `v1`（D5）会让它们**立即**跑上新 CLI。
  - ➡️ **推荐答案：取「字段缺省 ⇒ 声明」（甲），与本仓既有惯例一致**（`policy.py:94-95`：缺省→出厂默认，
    显式 `[]`/空→关；`require_change_for` 就是这三态），**但必须把一条迁移任务补进 tasks**：
    在本 change 内**手工**给本仓补一份 `.github/witnessloop-tests.txt`（内容 `uv run pytest -q`），
    并**在移 tag 之前**落地。理由：机械版立论是「没有测试执行点 = 有问题 ⇒ 拦」，若对**唯一剩下的
    那条老 policy** 反而不判，那这条门禁在本仓自己身上就是空的；而取乙的代价是「本仓要 opt-in」
    = 改受保护路径 = 一条解释事件（CRQ-6），一样要一次人工动作，却把默认从「拦」改成「不拦」。
  - **具体例子**：本 change 合入后 `git push origin v1.6.0 && git push -f origin v1.6.0^{}:refs/tags/v1`
    ——下一分钟，本仓任何一个 PR（哪怕只改 `README.md`）的 `gate / check` 变成
    「未通过 ✗（1 项）1. .github/witnessloop-tests.txt：策略声明了执行点，但文件不存在」。
    取甲 + 补文件 = 这条红**从不出现**；取乙 = 它**永远不出现**，但本仓的测试也就**永远不会**被 `check` 过问。

- **Q2 种子文件进不进 `desired_files()`（决定接入方改命令之后 `init` 还能不能用）？**
  `initcmd.py:44-49` 的 `desired_files()` 同时喂**三个**消费者：写盘（`:188-194`）、台账（`:79-95`）、
  以及**两条冲突判定**（`:169-179` 与 `:265-278`）。实测 E7b：哪怕把文件从台账里剔掉，
  **只要它还在 `desired` 里，接入方改过命令后 plain `init` 就 exit 1**。
  - ➡️ **推荐答案：不进。** 种子走一条**独立**代码路径（「不存在才写」，且**不参与** `conflicting_files`），
    代价是 `--dry-run` 输出与「产物清单」打印要单独加一行（`initcmd.py:181-186`、`:196-198`），
    并且要在 spec 里把「它是产物，但不由台账/冲突管辖」这个**双重身份**写清楚。
    理由：D3 把「改命令」定义成**正常用法**，那它就不能让 `init` 变坏；否则又回到前一轮 R10 那种
    「把死锁包装成特性」。反过来若取「进 `desired`」，就必须在文档里写「改命令之后**不要**再跑 `init`」，
    而这句在一个「`init` 是唯一升级入口」的工具里是不可执行的建议。
  - **具体例子**：接入方周一 `init --test-command "uv run pytest -q"`，周三把命令改成
    `uv run pytest -x -q --cov`（很常见的迭代）。取「不进」：`init` 照常 exit 0「幂等，无改动」，CI 用新命令。
    取「进」：他下次为了**别的**原因跑 `init`（比如本 change 之后的升级）时得到
    `init：检测到冲突（已接入，但本次指定的内容与已落地不同…请先 uninit）` exit 1，
    而 `uninit → init` 会**连 policy 一起删**（`uninitcmd.py:91-95` 删台账里每一个条目）。

- **Q3 「文件存在但内容为空/纯空白」判什么？（`design.md:69` 只写了两条判据）**
  实测 CRQ-1：空文件 ⇒ `check` 绿（不含哨兵）**且**门禁 `sh -c ""` exit 0 ⇒ 全绿、零测试。
  - ➡️ **推荐答案：加第三条判据「去空白后非空」，判红，文案点名「执行点为空（未接线）」；
  并给一条 Scenario（`Given` 空的命令文件 `When` check `Then` 红）。**
    理由：`design.md:74-76` 自己写的诚实边界是「证不了它真跑了」，但**空文件连『有一个命令』都不成立**
    ——它是「文件在不在」这一层的漏洞，不是能力天花板，没有理由放过。
  - **具体例子**：接入方在 GitHub 网页上点「Add file → Create new file」写好路径，编辑器里一犹豫先提交了空文件；
    下个 PR 里 `gate / check` 绿、日志里一行 `::notice::`（若按 CRQ-10 写了）也没有——
    `tests/` 一个用例没跑，而分支保护上挂着一个漂亮的绿勾。这正是 issue #4 要消掉的形态。

- **Q4 本仓自己怎么拿到执行点，以及**移 tag 与补文件的先后**？**
  `tasks.md` 里没有任何一条任务提到「本仓自己」，而 D5（`tasks.md:40-44`，D1/D2）是把 `v1` 移走。
  两者顺序颠倒的后果很具体（Q1 的例子）。另外本仓自己 `ci.yml` 的 `test` job 与新增的执行点会**跑两遍同样的 pytest**，
  而 `design.md:108` / Q4 又提议把 `ci.yml` 的 `test` 勾成 required ⇒ 变成**两处 required、两次全量测试**。
  - ➡️ **推荐答案：把「本仓补一份 `.github/witnessloop-tests.txt`（内容 `uv run pytest -q`）」写成 D 节的一条
    显式任务，并规定**必须先合入这条、再移 `v1`**；同时**放弃 Q4 的「把 `ci.yml` 的 `test` 勾成 required」**
    ——执行点已经进了 `gate / check`（它才是 required），再勾一次只是让同一批测试跑两遍。
    理由：本仓的 `init` 已经坏了（CRQ-4），所以这条只能靠手工提交，必须有任务、否则一定漏。
  - **具体例子**：合入本 change → 移 `v1` → 本仓下一个 PR（例如给 `README.md` 改一个错字）：
    `gate / check` 里 `check` 步骤红（执行点缺失）、测试步骤 `skipped`（`design.md:50` 说对了）
    ⇒ **本仓合不了任何 PR，包括那份「补执行点」的 PR 本身**（它也要过 required）。补成一条任务就没有这个窗口。

- **Q5 v1 的两份报告（`grill-review.md` / `grill-adversarial.md`）怎么办？**
  `design.md:5-6` 明确说保留它们。但 `contract.py:185-220` 的孤儿规则要求 `reviews/` 下**每个 `*.md`**
  都被某份 manifest 绑定，且 v1 的 CLI **已带这条规则**（`git show v1:src/witnessloop/contract.py:146,148,184,214`）；
  而 `evidence.py:192,197,210` 的 `matching[0]` 按 manifest 路径字典序取第一份
  ⇒ 再建一份 `stage=grill` 的 manifest 也**抢不过** `grill-review.manifest.json`，被校验正文的会是 v1 那份。
  - ➡️ **推荐答案：把 v1 的两份报告**移出 `reviews/`**（例如 `openspec/changes/adopter-test-gate/history/v1/`），
    只留一份 `stage=grill` 的 manifest 指向本文件（或作者指定的 v2 决策记录）。
    理由：v1 报告的 manifest 绑的是**旧 revision 的 tasks/spec hash**，v2 改写了这两份 artifact 之后
    必然判 drift；留着它们既救不回 v1 的设计，又制造孤儿/错绑两条红。若坚持留在 `reviews/` 下，
    至少要让**两份 grill 报告各有一份 manifest**，并且要在文档里承认「被机械校验正文的是字典序更靠前的那份」。
  - **具体例子**：作者按模板给 `grill-v2-review.md` 建 `stage=grill` manifest、又给 `grill-adversarial.md`
    建对抗 manifest，**忘了 v1 的两份报告** ⇒ 本 change 的 PR（由 v1 CLI 把关）直接报
    `孤儿报告：reviews/grill-review.md 未被任何 manifest 绑定`。
    这是**机械的**、与设计内容无关的失败——而它恰好会出现在「本 change 已经做完」的那一刻。

- **Q6 有没有比「移动 `v1`」更稳、又能达到同样目的的做法？**
  D5（`design.md:78-88`）与 `tasks.md:41-44` 选的是移动 `v1`。移动 `v1` 的**全部**后果我列一遍：
  ① 本仓自举的 `gate.yml` 换新（意图内）；② 本仓自举的 **CLI 版本**跟着换（`gate.yml:19-23` 的
  `witnessloop-ref` 默认 `v1`，caller 从不覆盖）；③ `wl-test` 同样换 CLI（无 branch protection，见 CD-7，影响仅限此）；
  ④ 将来**任何**按文档 `init`（`constants.py:11` 写 `@v1`）接入的仓，拿到的是「v1.6.0 语义」的 `gate.yml`
  和 CLI——这是**意图内**的；⑤ 本仓读者按 `README.md:20` 的 `uv tool install …@v1` 本地装的 CLI 也一起换；
  ⑥ tag 的 annotated 注记（现文「滚动大版本，当前指向 v1.5.0」）**会变成错的**，得一起改。
  - ➡️ **推荐答案：仍然移动 `v1`（没有更稳的等价做法），但要 (a) 补齐上面 ⑥ 的注记、
    (b) 按 Q4 把顺序改成「先给本仓补执行点、再移 tag」、(c) 在 `design.md §4` 里把 ①②③⑤⑥ 列全。**
    理由：`init` 写的是 `@v1`、`gate.yml` 的默认也是 `v1`，所以「让新 gate.yml 到达 pin `@v1` 的仓」
    **只有**移动这一个办法（换 `DEFAULT_GATE_REF` 只影响**将来**新接入的仓，救不了本仓自己与 `wl-test`）；
    而「不动 `v1`、只发 `v1.6.0`」的代价是本仓自举**永远**跑旧 CLI（`design.md:88` 已承认）——
    那等于把本 change 要修的洞（issue #4 同源的「门禁跑 6 个提交前的 CLI」）留一半。
    唯一**更稳**的变体是把「移 tag」拆成**独立的、可回滚的一步**（发 `v1.6.0` 一个 PR、移 `v1` 单独一次操作，
    并在移完后的第一个 PR 上人工确认 `gate / check` 的结论符合预期）——我推荐按这个粒度执行。
  - **具体例子**：移完 `v1` 之后第一次跑 CI，如果 `design.md §1` 那批「6 个提交里的行为变更」
    （`README.md:105-113` 自述：历史 change 缺 `stage=grill` manifest **新增一条红**）把某个**历史 change
    目录**顶红了，操作者需要能判断「这是门禁生效了，不是 tag 移错了」。没有上面 (b)(c) 的清单，
    这一步是纯凭记忆的。

- **Q7 D1 甲 / 乙 / 丙 的取舍：甲的「零新增人工步骤」论证有没有洞？**
  甲的论证（`design.md:34-45`）是「同 job ⇒ 复用已 required 的 `gate / check` ⇒ 零**新增**人工步骤」。
  复核：**论证本身站得住**（required 粒度 = job 已实测 CD-6；`.github/workflows/**` 不在保护面已实测 CD-2），
  但表格里「甲 vs 乙 的真正差别」一栏**漏了甲最大的代价**：接入方的测试从此跑在**别人的 job** 里，
  即 `gate.yml:58-59` 的 `permissions: contents: read`（reusable workflow 权限不能超出 caller），
  且**不能加 `services:`、不能加自己的 `uses:` 步骤、不能上 matrix/缓存**，命令只能是**一行 shell**。
  反过来乙（自己的 workflow）这些全都能做，代价只是**再勾一次 required**。
  - ➡️ **推荐答案：维持甲，但把「能力天花板」写进 `design.md` 的 D1 表格与 `spec.md` 的诚实边界**
    （与 D4 的三条边界并列成第四条）：**接入方的测试运行在一个只有 `contents: read`、
    没有 services/matrix/额外 action 的环境里；需要这些能力的仓应当改用乙（自带 job），
    代价是自己再勾一次 required。** 这一条不写，文档就是**过度承诺**——而本仓对「过度承诺」有明确的判据
    （`spec.md:67-80` 自己定义的那条 Requirement）。
  - **具体例子**：接入方 `acme/web` 的测试需要一个 Postgres。甲：他只能把
    `pg_ctl start` 塞进那一行命令里（没有 `services:` 可用），或者不用数据库跑测试；
    乙：他写 `services: postgres:16` 一步到位。甲不是**错**的，但把「同 job」卖成**普遍更优**是错的
    ——它是「零新增人工步骤」与「测试环境自主权」的交换。

- **Q8 门禁那一步的 `if:`：默认 / `always()` / `!cancelled()` 三选一？**
  `design.md:50-52` 与 `spec.md:58-60` 都只给了**两个**选项，并且给 `always()` 配了一个**不成立**的理由
  （见 CD-6 的 (b)）。官方文档明说「run regardless of outcome」的推荐写法是 `!cancelled()`。
  - ➡️ **推荐答案：`if: ${{ !cancelled() }}`，且把理由从「不掩蔽 check 的失败」改成
    「**门禁红的时候最需要测试反馈**」+「run 被取消时不必再跑一遍测试」；
    并在 spec 里把这句写成**结论 + 理由**，不要留「SHALL 在实现前显式钉死」这种占位（`spec.md:59-60`）。**
  - **具体例子**：PR 的 change 目录缺 `specs/` ⇒ `check` 步骤红；同一 PR 里 `src/` 有一处真 bug。
    `!cancelled()`：日志里同时看到「缺必需件 specs」与 `pytest` 的失败明细，一次解决两件事。
    默认语义：只有「缺 specs」，作者修完 specs 再推一次才发现测试也是红的（两轮 CI）。
    `always()`：同样能看到两条，但 run 被手动取消时还会再起一个跑测试的 step。

## 风险

- **R-v2-1（高 · 自锁）**：本 change 的产物会让**本仓自己**在移 tag 之后立刻红（Q1 取甲 + `tasks.md` 无迁移任务），
  且**修复它的 PR 本身也要过同一个 required**（Q4 的例子）。缓解：把「补执行点」写成前置任务并按 Q4 排序。
- **R-v2-2（中高 · 交互陷阱）**：三条机制（D3「文件归接入方、随便改」+ D4「哨兵判红」+ `init` 的冲突分支）
  叠起来是：接入方**必须**改这个文件才能变绿，**改完** `init` 就永久冲突（Q2/CRQ-3）。
  单独看每条都对，合起来是一条没有出口的路。缓解：Q2 取「种子不进 `desired_files()`」。
- **R-v2-3（中 · 承诺面）**：甲的**能力天花板**（read-only 权限、无 services/matrix、单行命令）不写进文档，
  `spec.md:67-80` 自己定义的那条「过度承诺」判据在本 change 上就**不成立**了（Q7）。
- **R-v2-4（中 · 证据链）**：v1 的两份报告留在 `reviews/` 会触发**孤儿规则**；若用「再加一份同 stage 的 manifest」
  绕过，则被校验正文的是字典序更靠前的 v1 报告（`evidence.py:197,210`），v2 的报告反而**免检**（Q5）。
- **R-v2-5（中 · 门禁语义）**：哨兵文件被当命令执行 ⇒ 症状是 `sh: Syntax error`（实测 exit 2），
  与「执行点没接线」毫无相似之处（CRQ-2）；空文件则是**全绿**（CRQ-1）。两者都不在设计里。
- **R-v2-6（低-中 · 措辞）**：`spec.md:65`「命令出现在 `env:` 里」（CRQ-8）与 `design.md:113`「默认 = 命令文件路径」
  （CRQ-5）都是**能被机械实现成两种相反结果**的措辞。本仓的既有教训是「理由句错会连带其余被怀疑」（前一轮 R18），
  这两句就是同类。
- **R-v2-7（低 · 文档面）**：`docs/gate.md:9` 的「只写三个文件」与 `tests/test_init.py:18,72,103` 的三处断言
  已被 `tasks.md:23-24`（B4）覆盖 ✓；但 `README.md:66` 那句「`init --policy` 尚未随 `@v1` 发布」
  在本 change 移 tag 之后**变成假**，没人安排改它。
- **R-v2-8（低 · 未查证）**：**「job 的最终结论 = 任一 step 失败即 failure」我只有**本仓自己的一次运行史**
  （run `38123102904`）作实证，**没有**从官方文档取到明文（`workflow-syntax` 页在 `jobs.<job_id>.steps` 处被截断）。
  判定方向（fail-closed）不受影响，但若有人要引用这句话，请标「实证 + 未取到官方明文」。

## 原稿被证伪的事实

1. **`design.md:59`（D3）与 `spec.md:31-34`（Scenario「改命令不撞台账」）**——「改命令 = 一次普通 commit，
   不撞台账、不需要解释事件」**在用户可见层面不成立**。不是台账问题，是**冲突**问题：
   `conflicting_files(root, desired)`（`initcmd.py:265-278`，被 `:169-179` 复用）用的是**同一个 `desired`**，
   所以只要种子在 `desired_files()` 里，接入方改过内容之后 plain `init` 就 **exit 1**——**哪怕它不在台账里**
   （实测 E7b：SIM-out-of-ledger 形态，`build_manifest` 已剔除该文件，`init` 仍 exit 1）。
   这条是前一轮被点名过的同形坑（「台账判定 vs 本次期望判定正交」）在 v2 换了个位置重现。
2. **`design.md:50-52`（D2）**——「`if: always()` 又会让测试的失败**掩蔽** `check` 的失败」**不成立**。
   实证（run `38123102904`）：失败的 step 与后续 `skipped` 的 step 各自独立上报，**job 结论 = failure**；
   两个 step 同时失败时两条都看得见。真正的掩蔽开关是 `continue-on-error: true`（本 change 未涉及）。
   决策（`check` 在前 + 测试步骤带状态函数）可以留，**理由句必须换**（并顺带升级成 `!cancelled()`，CRQ-11）。
3. **`design.md:18`**——把「本仓自己（dogfood）」与 `wl-test` 并列为「两条无所谓的路径」**半假**。
   `wl-test` 确实无所谓（**它连 branch protection 都开不了**，`gh api …/protection` → 403，
   所以「测试失败 = 合不了」在它身上从来不成立——这比「一次性仓、可删」是更硬的理由）。
   但**本仓自己不是无所谓**：它**今天**跑 `init --dry-run` 就 exit 1（真仓实测 E7a，定制 policy 撞出厂默认），
   任何迁移都只能手工提交；而按 Q1 甲的语义它会**在移 tag 后被自己的新门禁拦下**。
4. **`design.md:113`**——「`tests.execution_point`（默认 = 命令文件路径…）」**不是一个可实现的规格**：
   它没区分「字段缺省时的判定」与「`init` 写出的默认值」，而这两种读法对本仓自己与 `wl-test` 是
   「立刻红」与「永远不判」的区别（CRQ-5、Q1）。
5. **`spec.md:65`**——「命令出现在 `env:` 里」按设计（运行时读仓内文件）**无法满足**：
   workflow 里只会出现**文件路径**，命令文本从不出现（CRQ-8）。`tasks.md:32-33` 的口径与之不同。
6. **`tasks.md:20`（B1）**——「不参与 `uninit` 删除」被写成一条待实现的语义，但它是**免费的**：
   `uninitcmd.py:42-60` 只遍历台账条目，不在台账里的文件它根本看不见（CRQ-7）。
   真正的风险在反方向：为了这条去改 `uninitcmd.py` 会撞上 `uninitcmd.py:37` 的**单参** `desired_files(gate_ref)` 调用。
7. **`design.md:86-87` / R8**——`wl-test` 的严重度**偏高**（同第 3 条：它没有 branch protection，
   「钉回 `v1.5.0`」这条规避法在它身上只影响 CLI 版本，不影响门禁强度）。

## 仓内写入（含本文件对门禁的副作用）

- 唯一新增：`openspec/changes/adopter-test-gate/reviews/grill-v2-review.md`（本文件）。
  被审 worktree 未做任何其他改动（`git status --porcelain` 在写入前为空；`git diff` 为空）。
- 所有实验在 `/tmp/grill2/repo`（副本）与 `/tmp/sim/` 下完成；副本先 `rm -f .git && git init -q`
  再 `uv sync`，避免 `gitdir:` 指针写回原仓。测试基线未重跑（本文件不改任何代码），
  前一轮的 431 passed 与本轮无关。
- **副作用（机械、请作者处理）**：本文件是 `reviews/` 下**第三个** `*.md`。当前该目录**没有任何
  `*.manifest.json`** ⇒ `check` 走的是「缺少 review manifest」的提前返回（`contract.py:126-140`），**不查孤儿**。
  一旦开始 `manifest build`，**三份报告都要各有一份 manifest**，否则报孤儿（`contract.py:185-220`）；
  并且两份 `stage=grill` 时被校验正文的是字典序更靠前的那份（`evidence.py:197,210`）。见 Q5。
- 本文件按模板留了空的 `## User Confirmation`（停轮之前不得替用户拍板）⇒ 在作者停轮并逐条回填之前，
  `check` 会对 `## Open Questions` 里的每条各报一条「未经用户确认」。**这是预期状态**，不是本文件的缺陷。

## User Confirmation

> **本小节刻意留空**：按 `templates/grill.md` 的时序，停轮（第 6 步）发生在**设计对抗验证收敛之后**；
> 截至本文件产出（2026-10-13T00:45:59Z）**尚未停轮**，因此**没有任何用户答复**可记。
> 审阅者**不得**替用户拍板，也不得把自己的推荐答案当成用户的确认——Q1–Q8 由作者在停轮后逐条回填
> （格式：`- **Qn**: 用户答复：…；确认时间: …`）。
> 机械提示：`check` 的正文校验在此阶段会对 Q1–Q8 各报一条「未经用户确认」，这是**预期状态**。

## Sources

- step 的默认状态检查与 `always()` / `!cancelled()` 的官方表述：
  `https://docs.github.com/en/actions/reference/evaluate-expressions-in-workflows-and-actions`
  （原文：「A default status check of `success()` is applied unless you include one of these functions」；
  `always()`「even if the workflow/run is canceled」+「the recommended alternative for running regardless
  of outcome is `if: ${{ !cancelled() }}`」）。
- 「被跳过的 job 会报 Success」：`https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks`。
- **未查证**：job 的最终结论在「某 step 失败」时的官方明文——`workflow-syntax` 参考页在
  `jobs.<job_id>.steps` 一节被截断，本会话取不到。我改用**本仓自己的运行史**做实证
  （`gh api repos/Xingkai98/witnessloop/actions/runs/38123102904/jobs`），见 CD-6 与 R-v2-8。
- 其余全部结论来自本机实测（`/tmp/grill2/repo`、`/tmp/sim/`）与真仓 `gh` 取证（80 仓存在性扫描、
  branch protection、Actions 历史），不依赖第三方复述。

## 对抗轮回写（证伪记录 · 依 `templates/grill.md:134` 的硬要求）

> 本节由作者在**停轮之前**回填：本文件里被后续审阅**证伪/订正**的结论在此登记，避免读者按已失效的说法施工。

- **CD-8（本 change 命中自身门禁的正面要求）** ⚠️ **被证伪**：本 change 的 PR 由 **`v1` CLI** 把关
  （`.github/workflows/witnessloop.yml:14` + `gate.yml:19-23` 的 `witnessloop-ref` 默认 `v1`），
  而 v1 **没有 `evidence` 模块**、`REVIEW_MANIFEST_REQUIRED_FIELDS` **不含 `stage`**
  ⇒ 实测同一 diff「v1 报 1 条 / main 报 4 条」。⇒ 「必须有三份 manifest 否则红」**只在 main 及其后的 ref 上成立**。
- **CRQ-1（死锁的恢复路径）** ⚠️ **订正**：「恢复路径只有『恢复字节 + 删台账』」**为假**——
  实测三条**文件级**出口（恢复字节 / 删掉该文件 / 改台账 sha 仅对 `uninit` 有效），
  「删台账」**既不必要也不充分**。
- **CRQ-7 / 多轮 `always()` 的掩蔽说法** ⚠️ **订正**：「`always()` 会掩蔽 `check` 的失败」**为假**
  （失败步骤 + 后续 `skipped` ⇒ job 结论仍 `failure`；真掩蔽开关是 `continue-on-error`）⇒ 定案改用 `!cancelled()`。
- **方案整体（v1 的「模板 + 文档」路线）** ⚠️ **被推翻**：其前提「有存量接入方」经用户指出、
  并以**更硬口径**复核（穷举 owner 全部 80 个仓）后**不成立** ⇒ v2 改为**机械版**。
  v1 的记录已移至 `history/v1/`。
