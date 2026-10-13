# 设计阶段对抗验证（第 1 轮 R1）

> 零记忆独立审阅者，算法与格式依据 `templates/grill.md` **第 5 步**（对抗验证 loop）。
> **立场：默认上游结论有错，逐条证伪**；能实测的一律实测，平台语义查不到的**明写「未查证」**。
> 被审对象：`reviews/grill-review.md`（v2 决策记录）+ `design.md` v2.1 + `tasks.md` + `specs/adopter-test-job/spec.md`。
> 被审 revision：`bd53fdf30f79c77a15b2ca65ecd7196f688f95e8`（分支 `adopter-test-gate/2026-10-12`）。
> 被审 worktree **全程只读**；唯一仓内写入是本文件。

## Reviewer

- run id: `grill-adversarial-reviewer-adopter-test-gate-bd53fdf30f79`（未设 `WITNESSLOOP_RUN_ID` ⇒ 走模板第「怎么取 run id」的确定性兜底形态）
- 时间: 2026-10-13T00:57:17Z
- 方法（可复现）：
  - **副本** `/tmp/adv1/repo`：`cp -a` 后 `rm -f .git && git init -q && git add -A && git commit -qm base`，再 `rm -rf .venv && uv sync`（worktree 的 `.git` 是 `gitdir:` 指针文件）。另有 `/tmp/adv1/full`（`git clone` 的**带历史**副本，用于跑真 `manifest build` / `check`）。
  - **`init` 侧实验**（SIM）：`/tmp/adv1/sim/sim.py`（naive / out-of-ledger）、`sim2.py`（独立路径的两种落点）、`sim3.py`（策略字段后果）、`sim4.py`（把 D4 判据打进一份 **checkcmd 副本**后跑 PR 场景）。全部只在 `/tmp` 里对**运行时对象**打补丁，未改任何仓内文件；文中标注 SIM 的结论均为脚本实测输出。
  - **shell 语义**：真 `sh -c "$(cat f)"` 逐例测退出码。
  - **平台事实**：`gh api` 对真仓取证（branch protection / Actions 运行史）+ 官方文档 `WebFetch`。
  - 基线：副本里 `uv run pytest -q` → **431 passed in 25.97s**（与任务书给的基线一致）。

## Verdict

**CHANGES_REQUESTED**（2 条阻塞；**不推翻方案方向**——甲 / 先补文件后移 tag / 报告移出 `reviews/` / `!cancelled()` 四条我都独立复核**成立**，见下）。

**阻塞项**（都是「同一句话能被机械实现成两种相反结果」这一类，修法是各补 2–5 行规格，不动架构）：

- **X1｜`init --test-command` 在「命令文件已存在」时是静默 no-op，而默认路径恰好使文件存在**——
  `spec.md:9-10` 写的是**无条件** SHALL（「`init --test-command "<cmd>"` SHALL 把该命令写入命令文件」），
  而 `tasks.md:25`（B1）的机制是「**不存在才写**」。两者冲突，且冲突面是**最常见的那条序列**：
  plain `init`（默认就写哨兵，`spec.md:26-30`）⇒ 文件已存在 ⇒ 接入方再跑 `init --test-command "…"` 想接线
  ⇒ **exit 0 + 「init：已接入 witnessloop（幂等，无改动）。」+ 文件仍是哨兵**（SIM 实测，两种落点都一样，见 `## 新发现` N1）。
  这条不是「边界情况」：它让唯一一个**真能自动接线**的入口在默认序列里失效，而失败是**静默成功**。
- **X2｜「缺省 ⇒ 声明」只定了 `from_doc` 一侧，没定 `default_policy_doc()` 一侧；两种读法后果相反，其中一种让**已接入接入方**的 `init` 变 exit 1**——
  `tasks.md:13`（A2）说「字段缺省 ⇒ 声明（**用出厂默认路径**）」。若照既有惯例把该键**写进出厂 policy 文档**
  （`require_change_for` 就是「文档里显式写默认值」+ `from_doc` 兜底两处都在，`policy.py:30-49` 与 `:96-104`），
  则**任何用出厂 policy 接入过的仓**，之后跑 plain `init` 会命中 `initcmd.py:265-278` 的冲突分支 ⇒ **exit 1**
  （SIM 实测：`A) old-default adopter, plain init → exit = 1`，diff 就是新增的 `tests` 键）。
  ⇒ `init`（这个工具**唯一的升级入口**）对已接入仓**坏掉**——正是 D3 自己反对的那类死锁（`design.md:52-56`），
  而 `design.md:93-98`（D6）的后果清单只写了 check 侧「立刻红」，**没有一个字**提 init 侧。
  同时「显式空 ⇒ 不判」的**字面**没定：`""` / `[]` / `null` 三者里，`null` 在既有 `require_change_for` 范式下
  等于**缺省 ⇒ 判**（`policy.py:96-104` 用的是 `is None`），即「想 opt-out 反而被判」。
  （附带实测：`--no-tests` 之后跑 plain `init` 也是 exit 1，只有再带 `--no-tests` 才 exit 0——见 N2。）

**非阻塞，但建议同 PR 修（我逐条给了实测依据）**：X3 check 与门禁的哨兵/路径口径不一致；X4 `design.md:111` 与 R1 的「死窗口」理由为假；X5 三处「spec 写了但 tasks 没任务」；X6 tasks 的 `D0..D5` 与 design 的 `D1..D9` 标签撞名；X7 opt-out 只关 `check`、不关门禁那一步。详见 `## 新发现`。

## 逐条对抗

### A. Confirmed Decisions（`reviews/grill-review.md:40-111`，按出现顺序记作 CD-1..CD-8）

| # | 上游结论 | 我的复核 | 依据 |
|---|---|---|---|
| CD-1 | 没有任何外部接入方（穷举 owner 全部仓） | **成立（口径今天已过期）** | 我重跑 `gh repo list Xingkai98 --limit 300` ⇒ **82 个仓**（上游写 80）。差 2 个本身不影响结论，但「穷举」这句的**数字已经不准**，引用时要么重跑、要么写「以当时快照为准」 |
| CD-2 | `.github/**` 既不在受保护路径、也不在 `require_change_for`（本仓 + 出厂两份 policy） | **成立，逐字复核** | `.witnessloop/policy.json` `protected_paths=["openspec/specs/**",".witnessloop/**"]`、`require_change_for=["src/**","templates/**","plugin/**"]`；`policy.py:35-38` + `constants.py:27-36`；不变集 `policy.py:18-23` 四条都不含 `.github/**`。⇒ 种 `.github/witnessloop-tests.txt` 不需要解释事件 |
| CD-3 | 「新增 `init` 产物到不了已接入仓」+ 本仓 `init` 今天就坏 | **成立** | 副本真跑 `init --dry-run` ⇒ exit 1，成因确为定制 policy 撞出厂默认（`initcmd.py:265-278`），实证输出与 `design.md:18` 描述一致 |
| CD-4 | 「不进 hash 台账」是承重设计，最自然写法定会让接入方失去 `init` | **成立（两种形态都复现）** | SIM-naive：改命令后 plain `init` **exit 1** 且 `uninit` **也 exit 1**（整批拒删）；SIM-out-of-ledger：`init` 仍 exit 1、`uninit` exit 0 |
| CD-5 | `always()` 掩蔽说法为假；默认语义下前步失败 ⇒ 后步 skipped、job 仍 failure | **成立（我独立重取同一 run）** | `gh api …/actions/runs/38123102904/jobs`：`step4 uv run pytest=failure`、`step5 打包冒烟=skipped`、`job test=failure`。官方表达式页明文「A default status check of `success()` is applied unless you include one of these functions」 |
| CD-6 | required 粒度 = job，context 就是 `gate / check` | **成立（我独立重取）** | `gh api …/branches/main/protection` ⇒ `contexts=["gate / check"]`, `strict=true`, `enforce_admins=true`, `required_approving_review_count=0` |
| CD-7 | `wl-test` 连 branch protection 都开不了 | **成立（我独立重取）** | `gh api …/wl-test/branches/main/protection` ⇒ **403**「Upgrade to GitHub Pro or make this repository public…」 |
| CD-8 | v1 两份报告留在 `reviews/` 是机械问题；孤儿规则递归 + `matching[0]` 按字典序抢绑 | **结论成立，但机制有一处不准** | 孤儿规则递归**成立**（`contract.py:203` 用 `reviews.rglob("*.md")`），`history/v1/` 是**同级目录**、不在 `reviews/` 下 ⇒ **实测无孤儿**（见下）。但「**抢绑**」这条**走不通**：manifest 的落盘名由 **stage** 决定（`manifestcmd.py:149`：`reviews/{stage}.manifest.json`），两份 `stage=grill` 的 manifest **是同一个路径、后者覆盖前者**，造不出「字典序在前的那份赢」。真实失败形态是**孤儿红**（未绑定的那份报告），不是错绑 |

### B. 「原稿被证伪的事实」（`grill-review.md:331-357`，7 条）

1. **改命令 = 一次普通 commit「用户可见层面为假」** → **成立**（CD-4 实测复现，机制在 `initcmd.py:265-278`）。
2. **`always()` 掩蔽为假** → **成立**（CD-5）。
3. **「本仓自己与 `wl-test` 并列无所谓」半假** → **成立**；`wl-test` 的硬理由（无 protection）我已独立复取 403。
4. **`design.md:113`「默认 = 命令文件路径」不是可实现规格** → **成立，且作者只修了一半**：`design.md:97`（D6）现在写「字段缺省 ⇒ 声明」「显式空 ⇒ 不判」，但 see X2——**写进不写进出厂 policy 文档**这个读法仍未定。
5. **`spec.md:65`「命令出现在 `env:` 里」写不出来** → **成立，已修**：`spec.md:66-67`（主语改成**文件路径**）+ `spec.md:81-82`（结构断言断的是路径）+ `tasks.md:44-46`（C2 同口径）。✅ 三处一致。
6. **`tasks.md:20`（B1）「不参与 `uninit` 删除」是免费的** → **成立**：`uninitcmd.py:42`（`for entry in manifest.get("created_files", [])`）、`:91-95`（只 unlink 台账条目）。作者已改写成「**不需要改** `uninitcmd.py`」+ 反向风险提示（`tasks.md:28-29`）✅，并保留 `uninitcmd.py:37` 单参调用的警告。
7. **`wl-test` 严重度偏高** → **成立**（同 3）。

### C. Code-Resolved Questions（`grill-review.md:113-185`，CRQ-1..CRQ-11）

| # | 上游结论 | 复核 |
|---|---|---|
| CRQ-1 | 空文件 ⇒ `check` 绿 + 门禁 `sh -c ""` exit 0（双重绿） | **成立，复现**：`sh -c "$(cat 空文件)"` ⇒ exit 0；纯空白同。作者已加第三条判据（`spec.md:43-45`、`tasks.md:15-18`）✅ |
| CRQ-2 | 哨兵会被 `sh` 当命令执行（`sh: Syntax error`，exit 2） | **成立，复现**：`sh -c "<<REPLACE-ME>>"` ⇒ `sh: 1: Syntax error: end of file unexpected`、**exit 2**。作者已加「缺失**或含哨兵** ⇒ 跳过」✅ |
| CRQ-3 | 「改命令不撞台账」Scenario 字面真、用户可见假 | **成立**：`spec.md:36-39` 的 Then 仍只承诺「台账判定不受影响」——**但这一条现在是对的**了：因为 `design.md:52-56`（D3）已定「不进 `desired_files()`」，plain `init` 真能 exit 0（SIM 实测 case 4）。⇒ CRQ-3 的**病根已除**，只是 Then 的措辞仍窄（不覆盖「重跑 init 仍成功」这句更值钱的承诺，那句在 `spec.md:16` 里 ✅） |
| CRQ-4 | 本仓 `init` 今天就坏（exit 1） | **成立，副本实测复现**（与 CD-3 同一实验） |
| CRQ-5 | `policy.from_doc` 缺省语义两种读法、设计没定 | **成立，作者已定甲，但只定了 `from_doc` 一侧** ⇒ **残留 = X2** |
| CRQ-6 | 已接入仓 opt-out 只能改 policy（不变集、`M`）⇒ 每次一条事件 | **成立**（`policy.py:18-23`、`checkcmd.py:200`：`status[:1]=="A"` 只豁免新增）。但**低估**了摩擦：改完 policy 之后 bare `init` **永久 exit 1**（N2）。作者已把它写进 `spec.md:18-19`、`design.md:130-131`、`tasks.md:31-33` ✅ |
| CRQ-7 | 不需要改 `uninitcmd.py` | **成立**（见 B-6） |
| CRQ-8 | `spec.md:65` 主语写错 | **成立，已修**（见 B-5） |
| CRQ-9 | 本仓要不要动 policy，取决于 Q1 | **成立，已消解**：Q1 取甲 ⇒ `tasks.md:55-57`（D0）只补文件、不动 policy ✅ |
| CRQ-10 | 安全写法：路径经 `env:`、运行时 `cat` | **成立**，与 `design.md:72-82`（D5）、`spec.md:66-69`、`tasks.md:43-48`（C2）逐条一致 ✅ |
| CRQ-11 | `!cancelled()` 才是精确解 | **成立，我独立取到官方明文**：表达式参考页——`always()`「even when canceled」+「Avoid using `always` for any task that could suffer from a critical failure」+「use the recommended alternative: `if: ${{ !cancelled() }}`」。⇒ `check` 失败时会跑测试、run 被取消时不跑，✅ 与 `design.md:42-47`（D2）一致 |

### D. Open Questions（Q1..Q8）

- **Q1（缺省语义）**：推荐甲 ✅ 与我一致；**但见 X2**——甲只落了一半，`default_policy_doc()` 那一侧没定，而它才是决定「本仓/`wl-test`/任何出厂 policy 的仓 `init` 会不会 exit 1」的那一侧。
- **Q2（种子不进 `desired_files()`）**：推荐「不进」✅。**我独立复现了必要性**（CD-4 两形态）。另：`tasks.md:27`（B1）「代价：`--dry-run` 与产物清单要单独加一行」提了，但**没定那一行是无条件打还是「真会写才打」**——见 N3。
- **Q3（空/纯空白判红）**：推荐红 ✅。见 A-1（`## 新发现`）——这条只堵住了「意外空文件」，**没有**、也不该期望它堵住 `true` / `# TODO`；后两者属已声明边界（`spec.md:88-89`）。
- **Q4（先补文件再移 tag）**：推荐顺序 ✅ **保留**，但**理由句为假** ⇒ X4/N4。
- **Q5（v1 报告移出 `reviews/`）**：推荐移出 ✅，且**已执行**（`bd53fdf`：`history/v1/{README.md,v1-grill-review.md,v1-grill-adversarial.md}`）。机制订正见 CD-8。
- **Q6（仍移 `v1`，拆两步）**：推荐 ✅ 与我一致；`design.md:103-107` 的 ①–⑥ 清单我逐条核过，无遗漏（⑥ tag 注记我已核实现文是「滚动大版本，当前指向 v1.5.0」，移完必错）。
- **Q7（甲 + 写清能力天花板）**：推荐 ✅。`design.md:34-38` 已把天花板写成第四条边界，`spec.md:93-96` 同口径 ✅。
- **Q8（`!cancelled()`）**：推荐 ✅（见 CRQ-11）。

### E. 风险（R-v2-1..R-v2-8）

- **R-v2-1（自锁）**：**部分不成立** ⇒ X4。缓解动作（把补执行点写成前置任务）保留，但风险描述要改小。
- **R-v2-2（交互陷阱：必须改文件才能绿 + 改完 `init` 永久冲突）**：**已消解**（Q2 取「不进」）✅，实测 plain `init` 在改命令后 exit 0。
- **R-v2-3（承诺面 / 天花板）**：**已消解**（第四条边界已写）✅。
- **R-v2-4（证据链孤儿/错绑）**：孤儿部分**成立**，错绑部分**机制不准**（CD-8）。已通过搬迁消除 ✅。
- **R-v2-5（哨兵当命令跑 / 空文件全绿）**：**已消解** ✅（CRQ-1/2 的修法都进了 spec 与 tasks）。
- **R-v2-6（措辞能被机械实现成相反结果）**：**残留两条**——`design.md:97` 的「显式空」（X2）与 `design.md:80` 的哨兵子串口径（X3）。这条风险**没有被完全消解**，作者自己点出的病还在。
- **R-v2-7（`README.md:66` 在移 tag 后变成假）**：**成立且未处理** ⇒ X5（grill 提了，`tasks.md` / `design.md` 里**没有对应任务**）。
- **R-v2-8（job 结论未取到官方明文）**：**我也没取到**——`workflow-syntax-for-github-actions` 页仍在 `jobs.<job_id>.permissions` 处被截断（这次 WebFetch 的返回明确说 `jobs.<job_id>.steps` 一节不在可返回内容里）。⇒ **这条引用必须维持「实证（run 38123102904）+ 未取到官方明文」的标注**，别升级成「官方说」。

### F. design.md 的 D1..D9

| 决策 | 复核 |
|---|---|
| D1 甲 + 第四条边界 | **成立**（CD-2/CD-6 支撑；天花板已写进 spec） |
| D2 `!cancelled()` | **成立**（CRQ-11 官方明文）；`design.md:40-41` 已改成正确理由 ✅ |
| D3 种子不进 `desired_files()` | **成立且必要**（CD-4）——**但 `design.md:57` 那句「它是产物，但不由台账/冲突管辖」还没解决 X1 的写入语义** |
| D4 判据三条 | **成立**；第三条只堵意外空文件（A-1） |
| D5 `gate.yml` 那一步的形状 | **总体成立**；`design.md:80` 的 `*REPLACE-ME*` 与 A1 的哨兵串口径不一致 ⇒ X3 |
| D6 三态 | **成立但只落一半** ⇒ X2（阻塞） |
| D7 仍移 `v1`、拆两步 | **成立**；`design.md:111` 的理由句为假 ⇒ X4；`tasks.md` 的顺序与之**不一致**（`tasks.md:55`（D0）把补执行点排在发 tag **之前**，`design.md:108` 排在**之后**）——两种都安全，但两份 artifact 说法不同 |
| D8 v1 报告移出 | **成立**（已执行；机制订正见 CD-8） |
| D9 文档四条边界 + opt-out 摩擦 | **成立**；缺口 = `README.md:66`（X5）、opt-out 只关 check 不关门禁（X7）、`--test-command` 的静默 no-op（X1） |

## 新发现

### N1（阻塞 · X1）`init --test-command` 在文件已存在时静默 no-op —— SIM 实测

我把 design D3 的「独立路径（不存在才写）」按两种落点打进 `initcmd` 的副本，两种落点**都**得到：

```
1) fresh --dry-run:  + .witnessloop/policy.json / + caller / + init-manifest.json / + .github/witnessloop-tests.txt
2) fresh real init:  exit 0, 文件内容 '<<REPLACE-ME>>\n'
3) 已接入仓跑 `init --test-command "uv run pytest -q"`：
     init：已接入 witnessloop（幂等，无改动）。        ← exit 0
     文件内容仍是 '<<REPLACE-ME>>\n'                  ← flag 被静默吞掉
```

落点 A（种子只写在「未接入」分支内）：flag 连评估都没被评估。
落点 B（种子挪到 `_already_initialized` 早返回**之前**）：被评估了，但「不存在才写」仍然跳过。

⇒ 与 `spec.md:9-10` 的无条件 SHALL 冲突；`spec.md:36-39`（Scenario「改命令不撞台账」）只覆盖「**手改**文件后 `check` 仍判绿」，
而**「怎么把哨兵变成命令」这条路径在文档里只剩「手改文件」**（`tasks.md:55-57` 的 D0 对本仓正是这么做的）。
用户可见后果：接入方第一次 PR 红、「执行点未接线」，他照 `--test-command` 的语义再跑一次 `init`，
**得到一句成功**——然后 PR 还是红。修法二选一（需要作者定）：
(a) 文件已存在 **且** 显式传了 `--test-command` ⇒ **覆盖并 exit 0**（并把这条写进 spec 的 Scenario）；
(b) 显式传了 `--test-command` 而文件已存在且内容不同 ⇒ **报错 exit 1**（比 (a) 更符合「只增不改」的既有契约，但要多一条诊断文案）。

### N2（非阻塞，X2 的实测旁支）`--no-tests`（或手改 policy opt-out）之后，bare `init` 永久 exit 1

SIM 实测：

```
B) fresh `init --no-tests` -> exit = 0 | policy tests = {'execution_point': ''}
   then plain `init`       -> exit = 1   ← 冲突：磁盘 "" vs 期望 ".github/witnessloop-tests.txt"
   then `init --no-tests`  -> exit = 0
```

⇒ 文档建议的 opt-out 路径（「已接入仓改 `.witnessloop/policy.json`」）会让该仓进入「**bare `init` 不再可用**」的状态，
**只**比 CRQ-6 写的「每次 opt-out 要一条解释事件」严重。这条不是新机制（任何定制 policy 都这样，本仓就是活例），
但 D9 的 opt-out 段落应当**明说**它，否则文档是在推荐一条会咬人的路。

### N3（非阻塞）`--dry-run` / 产物清单那一行，「无条件打」还是「真会写才打」没定

`tasks.md:27` 只说要「单独加一行」。两种口径在**文件已存在**时分叉：

```
8) 未接入仓、但 .github/witnessloop-tests.txt 已存在（内容 'uv run pytest -q'）
   真跑 init  -> exit 0，文件内容**不变**（种子跳过）
   若产物清单无条件打印 "+ .github/witnessloop-tests.txt" ⇒ 它谎称自己创建了别人的文件
   若 --dry-run 无条件打印同理 ⇒ 说会写但实际不写
```

`initcmd.py:181-186`（dry-run 分支在写盘**之前**且提前 return）与 `:196-198`（产物清单）是两个不同位置，
实现者很容易只改一处。建议 spec 里把这一行钉成「**真会写才打**」。

### N4（阻塞级措辞 · X4）「先移 tag ⇒ 本仓合不了**任何** PR（含补执行点那条）」**为假**

推演 + 实测：`check` 判的是**被检 head 的检出树**（`checkcmd.py:27-55` 全程以 `root` 为基准；
`gate.yml:40-43` 显式 `ref: github.event.pull_request.head.sha`）。补执行点的那条 PR **自己就带着那个文件**
⇒ 新判据在它的 head 上**满足** ⇒ 绿。我在副本里把 D4 判据打进去实测过两端：

```
PR A（head 含 .github/witnessloop-tests.txt）→ check：通过 ✓ exit=0
PR B（head 不含该文件，例如一条改 README 的 PR）→ [SIM 新判据] 策略声明了执行点，但文件不存在 ⇒ exit=1
```

⇒ 真实的窗口是「**移 tag 之后、补文件落地之前，任何 head 里没有该文件的 PR 都红**」，
而那条补文件的 PR **恰恰不在其中**（它可以先合、合完窗口就关）。它**不是**「本仓合不了任何 PR」的死窗口。
`design.md:111`、`design.md:145`（R1）、`grill-review.md:310-311`（R-v2-1）三处都要改口径。
**D7 的执行顺序本身仍然保留**（先补文件更省事、且顺手把「文件在 main 上」这件事做实），只是理由要换：
不是「否则死锁」，而是「否则在途 PR 全红、且本仓要在红的门禁下补文件」。

### N5（非阻塞 · X3）check 与门禁的哨兵判据、路径来源**没有共用同一个来源**

- `design.md:80` 的 `case "$CMD" in *REPLACE-ME*)` 用的是**子串**；`tasks.md:11`（A1）的哨兵串是 `<<REPLACE-ME>>`。
  两者不同严格度 ⇒ 实测：`CMD='uv run pytest -k REPLACE-ME -q'` 时 `case` **命中 ⇒ 跳过**，
  而 `check` 若按完整哨兵串判 ⇒ **绿**。结果：**check 绿 + 测试一次没跑**——正是本 change 要消灭的那张脸，
  只不过触发条件是「命令里恰好含 `REPLACE-ME`」（例如某个用例名）。反向也有一条：文件写成
  `uv run pytest -q` + 注释行 `# <<REPLACE-ME>> 保留说明` ⇒ check **红**而命令其实是真的。
  ⇒ 修法：**两侧都从 `constants.py` 的同一个常量取值**（A1 已经把它放进 constants，只要别在 workflow 里手抄字面量），
  并在 spec 里写清**子串 vs 全串**。
- `env: WL_TESTS_FILE: .github/witnessloop-tests.txt`（`design.md:76`）是**硬编码**，而
  `policy.tests.execution_point` 是**路径字段**（`design.md:97`、`tasks.md:13`）⇒ 若接入方把它设成别的路径，
  `check` 判 A 文件、门禁读 B 文件 ⇒ **check 绿而门禁跳过**。建议把该字段收窄成「空 / 默认两条路」（或让门禁也从 policy 读路径）。

另外一条同族的健壮性缺陷（低）：CRLF。`printf 'uv run pytest -q\r\n'` ⇒ `sh -c "uv run pytest -q\r"` ⇒
`pytest: error: unrecognized arguments` ⇒ **exit 4**，而 `check`（去空白 + 无哨兵）判**绿**。fail-closed，不会静默放行，
但 Windows 编辑器改过这个文件的接入方会看到一条与「接线」无关的红。建议 `check` 顺带把 `\r` 归到空白里。

### N6（非阻塞 · X5）三处「spec 写了、tasks 里没有任务」

1. **`README.md:66`**：`init --policy` 「尚未随 `@v1` 发布」在**移 tag 之后变成假**。grill 自己提了（R-v2-7），
   但 `tasks.md` 的 F 节（F1/F2/F3，`tasks.md:83-89`）与 `design.md:122-131`（D9）**都没有它**。
2. **`spec.md:103-111`**（Requirement「不引入运行时依赖」+ Scenario「依赖为空」）要求「SHALL 有一条测试钉住它」，
   而 `grep -rn dependencies tests/` ⇒ **零命中**（`tests/test_invariants.py` 只钉不变集，`tests/test_entry.py` 只读 `pyproject` 的两个字面量）
   ⇒ 这条测试**不存在**，`tasks.md` A/B/C/E/F/G 里**没有一条任务去加它**。
3. **`spec.md:98-101`**（Scenario「文档不含无限定承诺（机械可验证）」，按 `tests/test_docs.py` 的 ±2 行范式扫
   「拦住合并 / 合不了」）——`grep -rn "拦住合并\|合不了" tests/` ⇒ **零命中**，范式本身倒是真实存在
   （`tests/test_docs.py:117-140` 的 `test_every_idempotency_claim_is_scoped_or_qualified`），但**没有任务**去写这道新守卫。
   ⇒ 这三条不补，spec 的 Scenario 会在实现后**无法机械验证**（而本 change 的立论正是「机械」）。

### N7（非阻塞 · X6）`tasks.md` 的 `D0..D5` 与 `design.md` 的 `D1..D9` **标签撞名而含义不同**

`tasks.md:53` 的 D 节（发版）用 `D0/D1/D2/D3/D4/D5`，其中 `tasks.md:58` 的 **D1 = 发 tag**、`tasks.md:59` 的 **D2 = 移 v1**，
而 `design.md:29` 的 **D1 = 执行点写在哪**、`design.md:40` 的 **D2 = 失败交互**——同一份 change 里同一个编号指两件事。
更绕的是 `tasks.md:40` 的 C 节标题又写「（D1 甲 / D2）」指的是 **design 的** D1/D2。本仓门禁的判据是 `文件:行号`，
这种撞名会直接把「D2 已定案」读成两件事。建议 tasks 侧改成 `R0..R5`（release）或 `F0..`。

### N8（非阻塞 · X7）opt-out 只关 `check` 的判据，**不关**门禁那一步

`design.md:77-81`（D5）的门禁步是「**文件存在就执行**（缺失或含哨兵才跳过）」。
⇒ 一个**先接线、后想 opt-out** 的接入方（改 policy 为显式空）会发现：`check` 不再判他了，
但**他的测试仍然在每个 PR 里跑**（文件还在），失败照样红。真正的 opt-out = 改 policy **+ 删/清空该文件**。
`spec.md:31-34` 的 Scenario「opt-out 不误伤」只覆盖了 `check` 侧，`design.md:130-131` 的 opt-out 段落也只说「改 policy」。
（对**全新**接入方不是问题：`--no-tests` 根本不写文件。）

### N9（非阻塞）上游的 `gate.yml` 行号有一处已失效

`grill-review.md:285`（Q7）引「`gate.yml:58-59` 的 `permissions: contents: read`」；当前 revision 里
`permissions:` 在 **`gate.yml:25-26`**（`:58-59` 是 `uses:`/`with:` 那块）。`design.md:35` 用的 25-26 是**对的**。
⇒ 引用上游那一段时要拿 design 的行号，别抄 grill 的。

### 我**独立复核为真**的四条（防止下游把这些当成「没验」）

1. **空文件双重绿**（CRQ-1）——`sh -c ""` exit 0，复现。
2. **哨兵当命令跑**（CRQ-2）——`sh -c "<<REPLACE-ME>>"` exit 2 + `Syntax error`，复现。
3. **`history/v1/` 的搬迁安全**（B-6 的问点）——在 `/tmp/adv1/full` 里**真**跑
   `manifest build --stage grill` + `check`：报 **8 项**全是 `Open Question Q1..Q8 未经用户确认`（因为我没填 User Confirmation），
   **一条孤儿都没有**，`history/v1/*.md` 完全不入局。⇒ 递归孤儿规则只吃 `reviews/` 下，搬迁是对的。
4. **本 change 的 PR 由 `@v1` = v1.5.0 的 CLI 把关**（B-6 的问点）——`constants.py:11` 写 `@v1`、
   `.github/workflows/witnessloop.yml:14` 钉 `@v1`、`git rev-list -n1 v1` = `843b691`（v1.5.0）。
   我把 v1 的源码取出来核过：**有**孤儿规则（`git show v1:src/witnessloop/contract.py` 第 146/148/184/214 行），
   **没有**执行点判据（`grep -ni "tests\|execution_point\|REPLACE" v1:…/checkcmd.py` 零命中），
   **没有** grill 正文校验、**没有** `grill-adversarial` stage（`v1:constants.py` 无该常量）、`v1:evidence.py` 无「未经用户确认」。
   ⇒ 本 change 的 PR 不会因为「Q1..Q8 未确认」或「缺 grill-adversarial/building manifest」而红；
   那三条是**跑新 CLI 的本地 `check`**（`tasks.md:95` G1）才会要的，作者按 G0/G1 做就是对的。

## Code-Resolved

| 问题 | 结论 | 证据 |
|---|---|---|
| `reviews/` 的孤儿规则是否递归？`history/v1/` 是否豁免？ | **递归**（`rglob`），`history/` 不在 `reviews/` 下 ⇒ 豁免。实测：建 grill manifest 后 check 只报 Q1..Q8，无孤儿 | `contract.py:203`；`/tmp/adv1/full` 实跑 |
| 两份 `stage=grill` 的 manifest 能否并存（「抢绑」是否可发生）？ | **不能**：落盘名由 stage 决定 ⇒ 后者**覆盖**前者。真实失败形态是**孤儿红**，不是错绑。上游 CD-8/Q5 的机制句要订正（动作已做对，结论不变） | `manifestcmd.py:149`；`evidence.py:197-210` |
| `!cancelled()` 到底跑不跑？ | **`check` 失败时跑**（含状态函数即不施加默认 `success()`），**run 被取消时不跑** | 官方表达式页（我独立取到明文） |
| job 的最终结论 = 任一 step 失败即 failure？ | **实证成立，官方明文未取到**：`gh api …/runs/38123102904/jobs` ⇒ step4 failure + step5 skipped ⇒ `job test=failure`。`workflow-syntax` 页在 `jobs.<job_id>.permissions` 处被截断（本次 WebFetch 明确回报 `jobs.<job_id>.steps` 不在可返回内容里）⇒ **沿用「实证 + 未查证」标注** | 同左 |
| `uninit` 需要改吗？ | **不需要**：`uninitcmd.py:42` 只遍历 `created_files`；`uninitcmd.py:91-95` 只 unlink 台账条目。改动反而会撞 `uninitcmd.py:37` 的**单参** `desired_files(gate_ref)` | 读码 + SIM（out-of-ledger 形态下 `uninit` exit 0） |
| 本 change 自己要不要三份证据？ | **要，但由跑新 CLI 的本地 `check` 要求**（`code_hits` 非空 ⇒ `grill-adversarial` + `building`；`grill` 还要正文完备）。而**PR 上的 required check 跑的是 v1.5.0**，不要求这三条 | `checkcmd.py:75-108`；`v1:checkcmd.py`（无此逻辑） |
| 新增第 4 个产物会破哪些断言？ | `tests/test_init.py:72`（`set(by_path) == {...}`）、`:18`（用例名 `test_init_creates_three_files`）、`:103`（快照三元组）、`docs/gate.md:9`。⇒ 与 `tasks.md:34-35`（B4）列的**完全一致** ✅ | 读码 |
| 加 `--test-command` / `--no-tests` 会撞 flag 面守卫吗？ | **不会**：`tests/` 里没有 init 的 flag 枚举/`--help` 快照断言（只有逐条调用的功能用例） | `grep -rn "add_argument" tests/` 零命中 |
| `tests/test_docs.py` 有 spec 引用的那个 ±2 行范式吗？ | **有** | `tests/test_docs.py:117-140` |

## 需要用户裁定

上游 Q1..Q8 我逐条复核**同意其推荐**（含 Q1 甲、Q4 顺序、Q5 移出、Q6 移 tag、Q7 甲+天花板、Q8 `!cancelled()`），
**除 X2 之外没有新的用户级取舍**。X2 与 X1 是作者层能拍板的机械规格（我给了二选一），**不必占用用户的停轮预算**。
若作者希望把 X1 的选择抛给用户，问题应当是这样一句话：

> **接入方跑了不带 `--test-command` 的 `init`（拿到哨兵文件）之后，他再跑 `init --test-command "<cmd>"`，你要什么行为？**
> (a) 直接覆盖命令文件（`--test-command` 显式优先，符合直觉，但 `init` 的「只增不改」契约多一个例外）；
> (b) 报错 exit 1 并让他手改（守住「只增不改」，但要多一条诊断、且与「无需手改生成物」的目标（`proposal.md:38`）相抵）。

---

**本文件的机械副作用（请作者处理）**：这是 `reviews/` 下**第二份** `*.md`。
`reviews/` 目前**没有任何 `*.manifest.json`** ⇒ 当前 `check` 走「缺少 review manifest」的提前返回、**不查孤儿**（`contract.py:127-135`，实测）。
一旦开始 `manifest build`：`grill-review.md` 与本文件**各需一份 manifest**（否则报孤儿），
本文件的 manifest 用 `--stage grill-adversarial` ⇒ 落在 `reviews/grill-adversarial.manifest.json`，**不与 `grill.manifest.json` 撞名**。
另：本次未跑 `manifest build`（对抗轮不得自证），落盘由作者在 `tasks.md:94`（G0）之后统一做。

---

# 第 2 轮（R2）

> 复审对象：`41e5df7`（R1 的 X1–X7 修复）。**只核机械项是否真关掉**，另附顺手发现。
> 方法：副本 `/tmp/adv2/repo`（`rm -f .git && git init -q && git add -A && git commit -qm base` + `rm -rf .venv && uv sync`），
> 基线 **431 passed in 29.82s**（与任务书一致；`41e5df7` 只改 `openspec/**` 四份文件，未动 `src/`）。
> 本轮**只读**：除本小节外未改任何文件。被审 revision 仍为分支头 `41e5df7`。

## Verdict

**CHANGES_REQUESTED**（3 处「改一行」；X1–X7 的**实质全部落地**，但 X2 与 X4 各有一处**旧字面残留**，
且残留的那两处正是**实现者会照做**的地方——照做出来的 `opt-out` 是坏的，照做出来的风险表仍挂着已证伪的理由句）。

- **Y1（X2 未关 · 阻塞）｜`tasks.md:36`（B3）**：「`init --no-tests` ⇒ 不写该文件 + **`tests.execution_point` 置空**（显式 opt-out）」
  —— 与同文件 `tasks.md:13-15`（A2，「opt-out 只能写 `tests.disabled: true`」）和 `spec.md:12-13` **直接相反**；
  按 B3 字面实现的后果正是 D6 新写的那句：`""` 是 falsy ⇒ `or DEFAULT` 回落 ⇒ 被读成「**声明**」⇒ `--no-tests` 之后**没有文件**却仍判 ⇒
  `spec.md:36-39` 的 Scenario「opt-out 不误伤」**不成立**。改法：`tests.disabled: true`。
- **Y2（X2 未关 · 阻塞）｜`design.md:152`**（接线点）：「`policy.py`：`tests.execution_point`（**三态**：缺省→默认、**显式空→不判**）」
  —— 与 `design.md:103-105`（D6 新写）**直接相反**，而 §3 接线点是实现者照着做的那一栏。改法：`tests.disabled` + 常量路径（见 Z2）。
- **Y3（X4 未关 · 阻塞级措辞）｜`design.md:161`（§4 风险 1/R1）**：仍原样写着
  「先移 tag 再补执行点 ⇒ **本仓合不了任何 PR**（含那个补执行点的 PR）⇒ D7 的粒度是硬要求」——
  D7（`design.md:119-124`）已把同一句标为**实测证伪**，风险表却没跟着改。风险表是审阅者最先读的地方，留着等于把已删的理由换个地方继续传。

其余 4 条（X1/X3/X5/X6/X7 各自的缺口）均为**非阻塞残留**，见下逐条。

## 逐条核验

### 1. X1（`--test-command` 静默 no-op）

- **`spec.md:9-11` ✅ 改齐**：`:9` SHALL 写入；`:10`「**该 flag SHALL 覆盖已有内容**（显式意图优先——不得因为文件已存在而静默 no-op）」；
  `:11`「**未给该 flag 时** SHALL 只在**文件不存在**时写入哨兵占位」。
- **`tasks.md:32-35`（B2）✅ 同口径**：「**总是写入该命令（覆盖）**…无 flag 时 ⇒ 只在**文件不存在**时写哨兵」。
- **`tasks.md:27`（B1）⚠️ 残留**：仍是无限定的「**不存在才写**」。与 B2 表面冲突——只看 B1 的实现者会把覆盖分支写没。
  改法：B1 加限定「（**无 flag 时**）不存在才写」。（非阻塞：B2 就在下面且写得很明确）
- **`spec.md:43-47`（Scenario）✅ 顺手补强**：Then 加了「并且**改完命令后再跑 plain `init` 仍 SHALL 成功**（不得 exit 1）」——
  这条正是 R1 说 CRQ-3「字面真、用户可见假」时缺的那半句，现在补上了 ✅。
- ⇒ **实质关掉**；B1 一处措辞残留。

### 2. X2（出厂 doc / opt-out 字面）

- **① 不物化 `tests` 键：`design.md:100-102` ✅ / `spec.md:15-16` ✅**，两处口径**一致**（都说了后果 = 已接入仓 plain `init` exit 1）。
- **② 唯一 opt-out 字面 = `tests.disabled: true`：`design.md:103-105` ✅ / `spec.md:12-13` ✅**，两处**一致**
  （都写了 `""` / `null` / 缺省 ⇒ 被读成「声明」，理由都是 `from_doc` 的 `or DEFAULT`）。
- **❌ `design.md:152`（Y2）、`tasks.md:36`（Y1）** 两处旧字面未清（见 Verdict）。
- **⚠️ `spec.md` 全文不出现 `tests.execution_point`**（`grep -n execution_point specs/adopter-test-job/spec.md` ⇒ 零命中）：
  规格面只钉了 `tests.disabled`，而「路径」这个字段**在 spec 里没有主语**。这同时让 R1-N5 的**后半仍开着**：
  只要 `execution_point` 还是「**路径值**」，接入方设成别的路径 ⇒ `check` 判 A 文件、`gate.yml`（`design.md:76` 硬编码）读 B 文件 ⇒ 又回到「一边绿一边跳过」。
  ⇒ 见 **Z2**。
- ⇒ **blocking 未关**（两处旧字面 + 一处缺主语）。

### 3. X3（口径同源）

| 要求 | 位置 | 结论 |
|---|---|---|
| D5 的 YAML 把**路径与哨兵**都放进 `env:` | `design.md:76-77`（`WL_TESTS_FILE` / `WL_TESTS_SENTINEL`，各带「必须等于 constants」注释） | ✅ |
| 注明必须与 `constants` 同源 + 加测试 | `design.md:85-87` | ✅ |
| tasks 有「三处逐字一致」的测试任务 | `tasks.md:55-57`（C4） | ✅ |
| spec Scenario 加同一条 **And** | `spec.md:91-92` | ✅ |

- **4/4 齐 ✅ 关掉**。附带：`design.md:81` 的 `case "$CMD" in *"$WL_TESTS_SENTINEL"*)` 已从手抄字面量改成**引用 `env` 变量**
  ⇒ R1-N5 的**前半**（子串口径分裂）可兑现为「同源」✅。
- 小 nit：`design.md:87` / `tasks.md:57` 写的断言目标是「`constants` / `gate.yml` / **`policy` 默认值**」——
  按 X2 的决定，`default_policy_doc()` **不含**该路径 ⇒ 实现者会去那里找一个**不存在**的字段、白写一条断言。
  措辞应改成「`policy.from_doc` 的默认值（同一个常量）」。

### 4. X4（被证伪的理由句）

- **`design.md:119-124` ✅**：「**给本仓补执行点（一个 PR）→ 发 `v1.6.0` → 移 `v1`**」+「原稿这里写过…**对抗轮实测证伪**…真实代价只是**在途** PR 会红 ⇒ 理由是**缩小红的窗口**」。
- **`tasks.md:65-71`（P0→P1→P2）✅ 同顺序**；`tasks.md:67-68` ✅ 同样改写。
- ⇒ **顺序在 design 与 tasks 之间一致 ✅**（先补执行点 → 发 tag → 移 tag）。
- **❌ `design.md:161` 残留**（Y3）。
- **❌ 另有一处「回写」义务未做**：`templates/grill.md:134` 要求「**被证伪的决策要回写 `grill-review.md`**——这一步必须在**停轮之前**做完」。
  `reviews/grill-review.md:243`（Q4 的具体例子）**逐字**还写着「⇒ **本仓合不了任何 PR，包括那份「补执行点」的 PR 本身**」，
  `:310-311`（R-v2-1）还写着「**修复它的 PR 本身也要过同一个 required**（Q4 的例子）」。
  本 commit `41e5df7` 未触及 `reviews/grill-review.md` ⇒ 证伪**只写进了 design**，没回写到决策记录。
  停轮时用户读的正是 grill-review，留着它就等于把这条已被推翻的推论再交一次给用户（**非阻塞，但模板明写是必需步骤**）。

### 5. X5（三条缺任务）

- `tasks.md:81`（**N1** 依赖为空测试）✅ / `tasks.md:82-83`（**N2** 文档守卫）✅ / `tasks.md:84-85`（**N3** `README.md:66` 订正）✅ ⇒ **3/3 关掉**。
- 小 nit（**Z4**）：N2 里多带了**两条 spec 里没有**的守卫（「文档里不出现『手改 `init` 产物』『先 `uninit` 再 `init`』的教法」、
  「README 接入段出现『四条边界』的关键词」）——是**加严**不是缺漏，但要么写进 `spec.md` 的诚实边界那节，要么标注为「超出 spec 的额外守卫」。

### 6. X6（标签撞名）

- **`tasks.md:60-63` ✅**：节名改成 `## P. 发版 / ref（design D7 …）`，条目 `P0..P5`，并写了说明
  「本节 id 用 `P*`（publish）而非 `D*`：`design.md` 的决策编号是 `D1..D9`，两个 `D` 含义不同会造成…歧义（对抗轮 X6）」✅。
- **`tasks.md:6` ⚠️ 残留**：仍写「…**A/B/C/D 四节**的形态不确定」——`D` 节已改名 `P`，且现在还多了 `N` 节。改法：`A/B/C/P`。
- 小 nit：`tasks.md:93` 的 `## H. 报告布局` 下条目仍叫 `E2a/E2b`（与 E 节的 `E2` 同前缀）——不重名，危害小，可与 `:6` 一起顺手归一。
- ⇒ **主体关掉**，一处旧编号残留。

### 7. X7（opt-out 只关 `check`）

- **`design.md:145-147` ✅** / **`spec.md:40-41` ✅**（Scenario「opt-out 不误伤」加了边界 And：「`disabled` 只关 `check` **不关**门禁那一步…
  若接入方想『连跑都别跑』，删掉命令文件即可。文档 SHALL 写明」）。
- **`tasks.md` ❌ 无承接**：F1（`tasks.md:102-105`）只列四条边界（①–④，不含这条）、F2（`:106`）只说 `docs/gate.md` §1 + 一小节、
  B3（`:36-38`）只说 opt-out 的**事件摩擦**。⇒ `spec.md:41` 那句「文档 SHALL 写明」**没有任务**（与 X5 同类，非阻塞）。

### 8. 有没有新引入的矛盾

- **① `--test-command` 覆盖 vs「改命令是接入方的自由」**：**不冲突** ✅ ——
  `spec.md:10` 的覆盖只发生在**显式给 flag** 时；`spec.md:20-22` 说的是**无 flag** 时的自由编辑 + plain `init` 不坏。
  但**新出现一处未定**（见 **Z1**）：覆盖落在**哪条分支**、与**退出码/文案**的关系没写，而 `initcmd.py:166-167`
  的 `_already_initialized` **早返回在任何种子逻辑之前** ⇒ 「总是覆盖」必须插到它之前（或写进它内部），两种落点用户可见结果不同。
- **② `tests.disabled` 与三条判据 / 门禁跳过条件**：**自洽** ✅ ——
  `spec.md:51` 的「在策略**声明了执行点**的前提下」把三判据限定在**未 disabled** 时；门禁的跳过条件是「缺失 or 含哨兵」
  （`spec.md:76-77`），与 `disabled` **正交**（disabled + 文件在 ⇒ 照跑，`spec.md:40-41` 已写明）。三条判据与 `disabled` 无交叠、无空洞。
- **③ 是否还有引用已被删掉的东西**：**有 3 处**（`design.md:152` / `tasks.md:36` / `design.md:161`，见 Y1–Y3）
  + **1 处跨件陈旧**：`proposal.md:58` 的**验收**仍写「`check` 在「执行点缺失 / 未替换哨兵 / 已接线」**三态**下的判定」——
  **漏了 D4 补的「空/纯空白」**（见 **Z3**）。

## 新发现（均为非阻塞）

- **Z1｜覆盖分支的落点、退出码与文案没定（X1 的尾巴）**。`initcmd.py:166-167` 的早返回在前，所以「总是覆盖」要么插在它**之前**、
  要么写进 `_already_initialized`。两种落点各有一个可见毛病：
  (a) 插在早返回之前、写完继续走 ⇒ 普通接入方看到的是 exit 0 + 「**init：已接入 witnessloop（幂等，无改动）。**」（`initcmd.py:280`），
  而这一跑**确实改了**命令文件 ⇒ **工具在撒谎**；
  (b) 同一落点碰上「policy 与出厂默认不同」的仓（本仓就是，`initcmd.py:265-278`）⇒ **exit 1，但文件已被覆盖** ⇒「失败的 init 带副作用」。
  ⇒ 建议 spec 补两句：**覆盖后 SHALL 打印点名该文件的一行（不得沿用「无改动」）**；**写入 SHALL NOT 因后续冲突判定回滚**，退出码沿用现有分支语义。
- **Z2｜`execution_point` 在 spec 里没有主语，且「路径可自定义」会让 check 与门禁分裂**（R1-N5 后半未关）。
  `spec.md` 只提 `tests.disabled`；`design.md:152`/`tasks.md:12` 仍把它叫 `tests.execution_point`（且 §3 那行还带旧的「显式空→不判」）。
  ⇒ 最小修法：**在 spec 里明写「命令文件路径是常量（`constants.py`），不是策略旋钮」**，`design.md:152` 改成只列 `tests.disabled` +
  常量路径；否则 `design.md:76` 的硬编码 `env` 与「三处同源」的断言都只是**默认值**层面的，用户设一个别的路径就破。
- **Z3｜`proposal.md:58` 的验收清单缺「空文件」一态**：仍写「三态」，未含 D4 的「空/纯空白 ⇒ 红」。
  验收面比 spec 少一条，收尾时容易漏测。（另：「三态」一词现在同时指策略字段与 check 判据，建议分开命名。）
- **Z4｜`tasks.md:82-83`（N2）的两条守卫超出 spec**（见 5 的小 nit）。
- **Z5｜轮次预算提示**：`templates/grill.md:130` 的默认封顶是 **3 轮**，而 `tasks.md:112-113`（G0/G0b）在**停轮与定案之后**还要
  「**重跑一轮设计对抗**」⇒ R1→R2→R3 正好把封顶用满。Y1–Y3 是**三行**的机械修改，**现在改掉**就不必占用 R3；
  否则 R3 若再 CHANGES_REQUESTED，按模板只能「到顶交人判断」——那会把一个措辞残留升级成人工裁决。
- **Z6（nit）**：`design.md:114` 的 `DEFAULT_GROGATE_REF` 拼写有误（应为 `DEFAULT_GATE_REF`；R1 时即在，本轮未动，顺手改）。

## 本轮 Code-Resolved

| 问题 | 结论 | 证据 |
|---|---|---|
| `41e5df7` 是否动过实现？ | **没有**：diff 只有 `design.md` / `tasks.md` / `spec.md` / `reviews/grill-adversarial.md` 四份 | `git show --stat 41e5df7` |
| 基线是否仍绿？ | **是**：**431 passed in 29.82s**（新副本 + `rm -rf .venv && uv sync`） | `/tmp/adv2/repo` |
| X3 的同源断言是否可兑现？ | **可以**：`design.md:81` 已改成 `case "$CMD" in *"$WL_TESTS_SENTINEL"*)`（引用变量而非手抄字面量） | `design.md:74-82` |
| `disabled` 会不会让门禁那一步也停？ | **不会**（正交）：门禁只看「文件在不在 / 含不含哨兵」 | `spec.md:76-77` vs `spec.md:40-41` |
| 证伪是否已回写决策记录（模板第 5 步硬要求）？ | **未回写**：`reviews/grill-review.md:243` 与 `:310-311` 仍是原句 | `templates/grill.md:134` |

---

# 第 3 轮（R3 · 终轮）

> 复审对象：`866046e`（R2 的 Y1–Y3 + 5 条非阻塞）+ `4468f5d`（proposal 验收）。**只核指定条目**。
> 副本 `/tmp/adv3/repo`（`rm -f .git && git init -q …` + `rm -rf .venv && uv sync`）⇒ 基线 **431 passed in 24.55s**（两个 commit 只动 `openspec/**`，未碰 `src/`）。
> 本轮只读；唯一写入是本小节。

## Verdict

**PASS**（R2 的 3 条阻塞 + 5 条非阻塞全部关掉；两条**非阻塞**观察见文末，可在实现期（G1）顺手处理，**不构成新一轮的理由**）。

## 逐条核验

### 1. Y1 —— `tasks.md` B3 的字面

- `tasks.md:37`（B3）✅：`init --no-tests` ⇒ 不写该文件 + 策略里写 **`tests.disabled: true`**；
  `:38-39` 还显式写了「⚠️ **不是「置空」**：`from_doc` 用 `or DEFAULT`…（对抗轮 Y1：本行原写「置空」与 A2/spec 的唯一字面直接相反）」。
- 与 `tasks.md:12-15`（A2）、`spec.md:12-13`（唯一 opt-out 字面）、`design.md:104` **四处同口径** ✅。
- 全库扫描：「置空」「显式空」**只剩否定句**（`tasks.md:38-39`、`design.md:153`），无一处仍把它当语义 ⇒ **关掉**。

### 2. Y2 —— `design.md` §3 接线点

- `design.md:152-154` ✅：「`policy.py`：语义 = **缺省 ⇒ 声明**（用默认路径）、**`tests.disabled: true` ⇒ 不判**；
  ⚠️ **`default_policy_doc()` 不物化 `tests` 键**（见 D6/X2）——「显式空 ⇒ 不判」这个字面**不成立**」。
- 与 `design.md:100-105`（D6）逐句一致，旧「三态：缺省→默认、显式空→不判」已消失 ⇒ **关掉**。

### 3. Y3 —— 风险表 + 证伪回写

- `design.md:161-164`（R1）✅：已改为「先移 tag ⇒ **在途** PR 会红（而**补执行点那条 PR 自己带着文件、是绿的**——对抗轮 X4 实测证伪了原稿「本仓合不了任何 PR」的说法）⇒ D7 的顺序仍保留，理由是**缩小红的窗口**，不是避免自锁」，且严重度由「高」降为「中」，与 `design.md:119-124`（D7）一致 ⇒ **关掉**。
- `reviews/grill-review.md:395-410` ✅ 新增「## 对抗轮回写（证伪记录 · 依 `templates/grill.md:134` 的硬要求）」，
  含四条：**CD-8**（本 change 命中自身门禁 —— 只有 `v1` CLI 把关，实测同一 diff「v1 报 1 条 / main 报 4 条」）、
  **CRQ-1**（死锁的恢复路径）、**CRQ-7 / `always()` 掩蔽说法**、**方案整体（v1 的模板+文档路线被推翻）**——
  与 R2 要求的四项**逐项对上** ⇒ **关掉**。

### 4. 非阻塞四项 + Z1

| 项 | 位置 | 结论 |
|---|---|---|
| tasks 头注编号 | `tasks.md:6`：**A/B/C/P 几节** | ✅ 关掉（`D` 已消失） |
| B1 的「无 flag 时」限定 | `tasks.md:27`：「B1 `init` 种命令文件（**无 flag 时**）：不存在才写…（带 `--test-command` 时见 B2：**总是覆盖**）」 | ✅ 关掉，与 B2（`:32-35`）无冲突 |
| X7 的文档要求有任务承接 | `tasks.md:90-91`：**N3**「写清『`tests.disabled: true` 只关 `check`，门禁那一步照旧会跑』」 | ✅ 关掉（X7 的 `spec.md:41` 现在有落点） |
| `proposal.md` 验收补空文件态 | `proposal.md:58-59`：**四态**（缺失 / **空或纯空白** / 未替换哨兵 / 已接线） | ✅ 关掉 |
| **Z1**（覆盖分支不得说「幂等，无改动」） | `tasks.md:44-46`：**B4b**「输出不得说『幂等，无改动』、**退出码仍为 0**；plain `init` 且文件已存在时才是『幂等，无改动』⇒ 两条分支各一条断言」 | ✅ 关掉 |

## 新增观察（两条，**非阻塞**，不影响 PASS）

- **O1（标签编号跨件歧义）**：`reviews/grill-review.md:395` 起的回写小节用的是 **v1 记录**的编号
  （那里的 `CRQ-1` = 「改了 caller 会怎样」、`CRQ-7` = 「A5.4 断言在现有 `gate.yml` 上直接红」、
  `CD-8` ≈ 三份 manifest），而**同一份文件**自己的 `CRQ-1` = 「空文件双重绿」（`:115`）、`CRQ-7` = 「不参与 `uninit` 删除」是免费的（`:150`）。
  ⇒ 读者在本文件内按编号回查会查到**另一个话题**。建议在小节首行加一句「以下编号引自 `history/v1/v1-grill-review.md`」，或给标签加 `v1-` 前缀。
  （另：该节复述的「穷举 owner 全部 **80** 个仓」按 R1 的复核今天是 **82**——引用时以快照为准。）
- **O2（B4b 的「退出码仍为 0」与既有冲突判定）**：`initcmd.py:265-278` 的「已接入 + 本次期望 ≠ 磁盘 ⇒ exit 1」
  是 `dogfood-bootstrap` 修过的硬判定（防「`--policy` 被静默忽略」）。B4b 若按字面实现成「给了 `--test-command` 就 exit 0」，
  会让 `init --test-command X --policy <不同>` 这种调用**静默吞掉 policy 冲突**。
  ⇒ 建议实现时把「退出码仍为 0」限定为「**无其它冲突时**」，即：覆盖写在早返回**之前**、其余判定照旧参与退出码。
  这条与 Z1 的落点（`initcmd.py:166-167` 早返回之前）是同一处，实现时一并定即可。

## 本轮 Code-Resolved

| 问题 | 结论 | 证据 |
|---|---|---|
| 两个 commit 是否动过实现？ | **没有**：只有 `design.md` / `tasks.md` / `proposal.md` / `reviews/*.md` | `git show --stat 866046e` / `4468f5d` |
| 基线是否仍绿？ | **是**：**431 passed in 24.55s**（新副本 + 全新 venv） | `/tmp/adv3/repo` |
| 唯一 opt-out 字面是否四处同口径？ | **是**：`spec.md:12` / `design.md:104,152` / `tasks.md:12,14,37` | `grep -rn "tests.disabled"` |

---

# 定案后重跑（R4）

> 依 `templates/grill.md` 的时序：停轮尘埃落定后、**写码之前**，对抗轮针对**定稿**再跑一次。
> 被审 revision：`4df66e9`（分支 `adopter-test-gate/2026-10-12`）——⚠️ **工作区不是干净的**：
> `design.md` / `tasks.md` 有**未提交**改动，另有**未跟踪**的 `reviews/grill.manifest.json`（本节把它们一并核了）。
> 方法：`/tmp/adv4/repo`（`cp -a` 后 `rm -f .git && git init -q …` + `rm -rf .venv && uv sync` ⇒ 基线 **431 passed**）+
> `/tmp/adv4/full`（`git clone` 的**带历史**副本，用于跑**真** `check` / `guard` / `sha256_tree`）。
> 本轮只读；唯一写入是本小节。

## Verdict

**CHANGES_REQUESTED**（3 条，全是**文件卫生 + 证据自洽**，各 ≤5 行；**设计内容本身已定案且可执行**，
`guard` 已放行 `src/**`——见第 4 条。修完这三条即可开始实现，不必再走一轮对抗）。

- **W1｜`reviews/grill-review.md` 有**两份**同名 `## User Confirmation`**：`:373` 是**旧空占位**
  （「本小节刻意留空…**没有任何用户答复可记**」+「`check` 会报 Q1–Q8 未经用户确认，这是**预期状态**」），
  `:412-425` 才是真正的 Q1–Q8 答复。⇒ 决策记录**自己打自己**（答复上方写着「没有答复」），
  且占位里那句机械提示在定案后**已经是假的**。修法：删掉 `:373-379` 那段占位（或改成一行「见文末」指针）。
  （**机械上仍能过**——见第 3 条——所以是人读面的缺陷，不是门禁缺陷。）
- **W2｜`reviews/grill.manifest.json` 与它自己的 `head_sha` 不自洽**：`tasks_hash=bba69b16…` 是
  **工作区那份未提交的 `tasks.md`** 的哈希，而 `tasks.md@4df66e9 = 691d085b…`（同一 `sha256_tree`，实测）
  ⇒ 这份 manifest 断言的内容**不在它声明的 revision 里**。实测后果（`/tmp/adv4/full`，真 `check`）：
  - 检 **`4df66e9`（= CI 会检出的样子）** ⇒ 2 项红：`tasks_hash 不匹配` + 孤儿（见 W3）；
  - 检 **作者本机脏工作区** ⇒ 只剩孤儿 1 项红（哈希对上了）。
  ⇒ 它**只能在脏工作区里自洽**；`design.md` / `tasks.md` 一提交，`head_sha` 之后就有非证据文件变更
  ⇒ `contract.py:340-353` 的 stale 判据照红。修法：**提交定案内容之后再 `manifest build` 一次**（G1 本来就列了这件事，
  但那份未跟踪的 manifest 别按现状提交/沿用）。
- **W3｜`design.md:184` 与状态行互相矛盾**：`:3` 已写「状态：**已定案**」，而 `## 6. 停轮（Q1..Q8 —— **待用户确认**）`
  的表头一字未改，表里（`:186-196`）仍以「推荐」口吻并列 **甲／乙／丙** 等未选分支，
  与 `tasks.md:128-134`（定案节：「未选分支**不再保留**」）冲突。修法：`:184` 改「## 6. 停轮（Q1..Q8 —— **已由用户确认，见 `reviews/grill-review.md` 的 User Confirmation**）」，
  并把表头「推荐」列改成「用户裁定」。

（**W3 只是文件卫生**；若作者判定 §6 作为「当时的提问记录」保留原样更有价值，可只改标题、不删表——我不坚持删表。）

## 逐条核验

### 1. 定案是否完整且一致地落进**四处**（逐份点名）

| # | 位置 | 结论 |
|---|---|---|
| 1 | **`design.md` 状态行** | ✅ **有**：`design.md:3-4`「状态：**已定案**（用户 2026-10-13 逐条确认 Q1..Q8：**Q6 批准发版**…其余七条按推荐）。下一步：G0 → G0b → 实现（TDD）」。⚠️ 与 `:184` 的「待用户确认」矛盾 ⇒ **W3**。⚠️ 且**未提交**（工作区改动） |
| 2 | **`tasks.md` 的「定案」节** | ✅ **有**：`tasks.md:128-134`「## 定案（用户 2026-10-13）」——Q6=做发版（P1/P2，分步，**移 tag 需用户在场**）；Q1–Q5、Q7、Q8=按推荐；「未选分支（乙／丙）**不再保留**」。⚠️ 未提交 |
| 3 | **`spec.md`** | ✅ **形态即甲**（`spec.md:71-72`「测试步骤 SHALL 与 `check` **处于同一个 job**」+ `:93-96` 第四条能力天花板）；**无** `甲/乙/丙`、**无** `待定案/二选一/任选/TBD/待补`（`grep` 零命中）✅ |
| 4 | **`reviews/grill-review.md` 的 `## User Confirmation`** | ✅ 有 Q1–Q8 逐条**非占位**答复（`:412-425`，八条都带「用户答复：…；确认时间: 2026-10-13」）——但**同名小节出现两次**（`:373` 空占位 + `:412` 真答复）⇒ **W1**。另：小节位置在 `## Sources` / `## 对抗轮回写` **之后**，与模板的段序不同（不影响解析） |

> 补充：`proposal.md` 未在四处之列，但 `:38`（目标 1「命令在接入时给」）与 `:53`（「同 job 时不需要新增勾选」）与定案**一致** ✅。

### 2. 有没有新引入的矛盾

- **Q6「做发版」与 P 节是否一致（含「移 tag 需用户在场」）**：✅ **一致**——
  `tasks.md:69-73`（P1 发 tag / P2 移 tag，P2 明写「⚠️ **改写已发布 ref 的对外动作，执行前需用户在场确认**」+ 同步改 tag 注记）
  与 `tasks.md:128-131`（定案节）同口径；`design.md:119-124`（D7）的「补执行点 → 发 `v1.6.0` → 移 `v1`」顺序一致 ✅。
- **Q4 放弃 `ci.yml` required 后的残留相反表述**：✅ **无**——`tasks.md:81-83`（P5 已划掉 + 「已放弃」理由）、
  `design.md:191`（Q4 行写「**放弃**把 `ci.yml` 的 `test` 勾 required」）、`tasks.md:138`（「明确不做」也写了「替接入方勾 required（同 job 时不需要）」）。
  唯一还提「勾 required」的地方是**甲方案之外**的 乙（`design.md:38`）与**平台既有事实**（`design.md:25`），不构成矛盾。
- **新矛盾**：**W2**（manifest 哈希 vs head_sha，机械可验）与 **W3**（design 内部 状态行 vs §6 表头）；**W1** 是记录文档自相矛盾。

### 3. `## User Confirmation` 是否真能过 grill 正文判据（机械验证）

**结论：能过** ✅ —— 在 `/tmp/adv4/full` 里跑**真** `check`（源码 CLI，`--base origin/main --head HEAD`），
**没有任何一条**「Open Question Qn 未经用户确认」。机制：`evidence.py:52-64` 的 `_sections()`
对**同名标题用 `setdefault` 累加**，两份 `## User Confirmation` 的正文被**合并**成一节，
所以 `:412` 起的 `- **Qn**: 用户答复：…` 仍被 `_confirmations()`（`:85-94`）抓到；占位那段的 `>` 引用行不匹配 `_CONF_LINE_RE`（`:35`）。

**但整个 `check` 是红的**（本节顺带核实，两种状态都跑了）：

```
TEST A（干净 4df66e9 = CI 视角）           ✗ 2 项
  1. reviews/grill.manifest.json：tasks_hash 不匹配（evidence 与 artifact 已漂移）
  2. reviews/grill-adversarial.md：孤儿报告：未被任何 manifest 绑定
TEST B（叠加作者的未提交改动 = 本机态）    ✗ 1 项
  1. reviews/grill-adversarial.md：孤儿报告：未被任何 manifest 绑定
```

⇒ 第 2 条**是预期中间态**（`tasks.md:122-124`（G1）会建 `stage=grill-adversarial` 的 manifest 来绑本文件）；
第 1 条就是 **W2**。两条都必须在合 PR 前清掉，且**现在这份 manifest 不能直接用**。

### 4. 本 change 现在可以开始实现了吗？

**可以** ✅（三条 W 都不阻塞写码，只阻塞「证据定稿」）——实测依据：

- **本地 `guard` 已放行**（脏工作区，真跑）：`guard --root . --path src/witnessloop/checkcmd.py --change adopter-test-gate` ⇒ **exit 0**；
  `.github/workflows/gate.yml` 亦 exit 0（`.github/**` 不命中 `require_change_for`）。
  ⇒ G0 的「建 grill manifest 放行 `src/**`」**已生效**。
- **A/B/B4b/C/N/E/F/G/P 逐条看过**，**无「靠猜才能做」**项：A1（常量两条）、A2（两条字面）、A3（四条判定）、A4/A5（先红单测 + 不执行命令）、
  B1/B2/B3（三分支：无 flag 不覆盖 / 有 flag 覆盖 / `--no-tests` 写 `disabled`）、B4（既有断言改点已点名到 `文件:行号`）、
  B4b（两条分支各一条断言：覆盖不说「幂等，无改动」≠ plain-init 才说）、B5/B6（回归 + golden literal）、
  C1–C5（step 形态 / `env:` 主语 / `!cancelled()` / 三处同源断言 / job 名不变）、N1–N3、E1–E3、F1–F4、G0–G4、P0–P5 全部**可执行**。
- **`spec.md` 的每条 Requirement 都有任务**：①执行点写入→B1/B2/B3/B4/B4b；②`check` 三判据→A1–A5；③门禁执行→C1–C5；
  ④诚实边界（四条 + 文档守卫 Scenario）→F1/F2/N2；⑤零依赖→N1；⑥产物契约→B4/E2 ✅。
- **⊘ 一处空转**：`tasks.md:103-104`（**E2a**「把 v1 的两份报告移出 `reviews/`」）**已经完成**
  （`bd53fdf` 就做了；`openspec/changes/adopter-test-gate/history/v1/` 下三份文件已在）⇒ 应直接标 `[x]` 或删除，
  否则实现者会去找一份早已搬走的文件。（E2b 与 G1 的 manifest 落盘有重叠，无害。）
- **两处「覆盖含糊」**（非阻塞，建议顺手在 F 节点名）：
  (a) `spec.md:17`「SHALL 在**文档里给出补文件的迁移步骤**」——F1（README 接入段）/F2（`docs/gate.md` 新小节）的措辞**没点名**这件事（P0 是本仓的动作、不是文档内容）；
  (b) R3 已提的 **O2**（B4b 的「退出码仍为 0」宜限定为「无其它冲突时」，否则 `init --test-command X --policy <不同>` 会吞掉 `initcmd.py:265-278` 的 policy 冲突）——实现时与 Z1 的落点一并定即可。

## 本轮 Code-Resolved

| 问题 | 结论 | 证据 |
|---|---|---|
| `## User Confirmation` 能过机械判据吗？ | **能**：真 `check` 下 0 条「未经用户确认」（同名标题被 `_sections` 合并） | `/tmp/adv4/full` 实跑；`evidence.py:52-64,85-94` |
| 现存 `grill.manifest.json` 自洽吗？ | **不自洽**：`tasks_hash` = 工作区版本（`bba69b16…`），`tasks.md@4df66e9` = `691d085b…`（同 `sha256_tree`）；`spec_hash`/`report_hash` 则**对得上** | 用 `witnessloop.hashing.sha256_tree` 在三处实算 |
| 它能在 CI 里过吗？ | **不能**：检 `4df66e9` ⇒ `tasks_hash 不匹配`（+孤儿） | TEST A 实跑 |
| 孤儿是缺陷还是中间态？ | **中间态**：G1（`tasks.md:122-124`）会建 `grill-adversarial` manifest 绑本文件 | TEST A/B 都只剩它 |
| 本 change 是否已放行写码？ | **是**：`guard --path src/witnessloop/checkcmd.py` ⇒ exit 0 | TEST B 实跑 |
| 两个新 commit 动过实现吗？ | **没有**：`4df66e9` 只改 `reviews/*.md`；`design.md`/`tasks.md` 的定案改动**还在工作区**（未提交） | `git show --stat 4df66e9` + `git status` |
| 基线？ | **431 passed**（`/tmp/adv4/repo`，全新 venv） | 见上 |
