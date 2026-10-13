# Design: adopter-test-gate（v2.1 · 机械版 · 已按 grill v2 回写）

> 状态：**草稿 v2.1**。待对抗验证收敛 → 停轮（Q1..Q8）。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。决策记录：`reviews/grill-review.md`（v2）、
> `history/v1/`（**v1 那轮的记录**——它证伪的实测事实仍有效，被推翻的只是方案选择）。

## 0. 一句话

**`init` 把测试执行点写进去，门禁跑它，`check` 机械地要求它「存在、非空、已接线」**——
「没有存量接入方」这条前提不成立（grill v2 用更硬的口径复核过），所以 v1 那个「只给文档、零强制」没有理由。

## 1. 现状（实测 · 含 grill v2 的新发现）

| 事实 | 证据 |
|---|---|
| **没有任何外部接入方**（v2 前提，已用更硬口径复核） | 穷举 owner 全部 **80 个仓**逐个 `contents` 探测 ⇒ 只命中 `witnessloop` 与 `wl-test`；全局 code search 无第三方引用 |
| `wl-test` 比「可删」还彻底 | `gh api …/wl-test/branches/main/protection` ⇒ **403**（连 branch protection 都没开） |
| **本仓自己的 `init` 今天就坏**（与本次改动无关） | 真仓未打补丁：`init --dry-run` ⇒ **exit 1**（定制 policy 与出厂默认不同，命中 `initcmd.py:265-278`）⇒ **本仓没有任何可用的 `init` 入口**，迁移只能靠手工提交 |
| **本仓自己的门禁跑的是 6 个提交前的 CLI** | `.github/workflows/witnessloop.yml:14` 引 `@v1`；`gate.yml:19-23` 的 `witnessloop-ref` 默认 `v1`；实测同一 diff「v1 报 1 条 / main 报 4 条」 |
| `gate.yml` 自 `v1` 起从未改过；`v1` 自称「滚动大版本」 | `git log --oneline v1..origin/main -- .github/workflows/gate.yml` = 空；`git tag -n99 v1` |
| 零运行时依赖 | `pyproject.toml` `dependencies = []`（wheel 无 `Requires-Dist`） |
| `.github/**` **两者都不在**（本仓 policy 与出厂默认） | `protected_paths = ['openspec/specs/**','.witnessloop/**']`；本仓 `require_change_for = ['src/**','templates/**','plugin/**']`、出厂默认是 src/lib/… 那一串 |
| **手改 `init` 产物 = 死锁**；`uninit → init` 会丢定制 policy | 实测：`init`/`uninit`/`--dry-run`/`--policy`/`--gate-ref` 全 exit 1；`uninitcmd.py:91-95` 删台账里每一条 |
| required 粒度 = **job**；本仓 `test` 非 required | `gh api …/protection` ⇒ `contexts = ["gate / check"]` |
| **孤儿规则是 `reviews/**/*.md`（递归）** | `contract.py:185-220`；`evidence.py:192,197,210` 的 `matching[0]` 按**路径字典序**取 ⇒ 同 stage 的多份报告会**错绑** |

## 2. 决策

### D1 执行点写在哪：**甲**（命令文件 + `gate.yml` 读它）—— **Q7**

- 形态：`init` 种一份**命令文件** `.github/witnessloop-tests.txt`；`gate.yml` 新增一步**读它并执行**；
  测试与 `check` **同一个 job** ⇒ 复用已 required 的 `gate / check` ⇒ **接入方零新增人工步骤**。
- **否丙**（命令进 caller 的 `with:`）：caller 在台账里 ⇒ 改命令撞死锁。
- ⚠️ **甲的最大代价必须写进文档（grill v2 的 Q7，第四条诚实边界）**：接入方的测试从此跑在**别人的 job**
  里——`gate.yml:25-26` 只声明 `contents: read`（reusable workflow 权限不能超出 caller），
  且**不能加 `services:`、不能加自己的 `uses:` 步骤、不能上 matrix/缓存**，命令只能是**一行 shell**。
  需要 Postgres、matrix、OIDC 等的仓**应当改用「乙」（自己的 workflow）**，代价是自己再勾一次 required。
  **把「同 job」卖成普遍更优就是过度承诺。**

### D2 失败交互：`if: ${{ !cancelled() }}`（grill v2 的 Q8；原稿的 `always()` 论证已被证伪）

- **原稿说「`always()` 会掩蔽 `check` 的失败」——实测为假**：失败步骤 + 后续 `skipped` 步骤 ⇒ job 结论仍是
  `failure`（真掩蔽开关是 `continue-on-error`）。
- **定案**：用官方推荐写法 `if: ${{ !cancelled() }}`，理由改为**两条**：
  ① 门禁红的时候**最需要测试反馈**（一次 CI 里同时看到「缺 specs」与「pytest 失败明细」）；
  ② run 被取消时不必再跑一遍测试（`always()` 会）。
- 需求不是「无条件跑」，而是「**`check` 失败时也要跑**」⇒ `!cancelled()` 才是精确解。

### D3 命令文件的**双重身份**：是产物，但**不进台账、不参与冲突判定** —— **Q2**

- `desired_files()`（`initcmd.py:44-49`）同时喂**三个**消费者：写盘、台账、**两条冲突判定**（`:169-179`、`:265-278`）。
  ⇒ **种子不能进 `desired_files()`**：走一条**独立**路径（「不存在才写」）。
- **实测依据**：哪怕把文件从台账里剔掉，**只要它还在 `desired` 里**，接入方改过命令之后 plain `init` 就 **exit 1**
  （`initcmd.py:265-278`）——而 `uninit → init` 会**连 policy 一起删**。
  ⇒ 原稿那句「改命令 = 一次普通 commit」在这个意义上**是假的**，必须靠「不进 desired」来兑现。
- 代价：`--dry-run` 输出与「产物清单」打印要单独加一行（`initcmd.py:181-186`、`:196-198`），
  并在 spec 里把「**它是产物，但不由台账/冲突管辖**」这个双重身份写清楚。
- ⚠️ **「不参与 `uninit` 删除」是免费的**：`uninitcmd.py:42-60` 只遍历 `manifest["created_files"]`
  ⇒ 文件不在台账里就永远不会被它看到，**不需要改 `uninitcmd.py`**（改了反而危险：`uninitcmd.py:37` 是
  `initcmd.desired_files(gate_ref)` 的**单参调用**）。

### D4 `check` 的机械判据：**存在 + 非空（去空白）+ 不含哨兵** —— **Q3**

- 原稿只写了两条 ⇒ **实测漏洞**：**空文件**两条都满足 ⇒ `check` 绿 **且** 门禁 `sh -c ""` **exit 0**
  ⇒ 「有执行点、门禁跑了、required 绿、测试一个没跑」——**正是 issue #4 的形态，外加一枚绿勾**。
- **定案**：加第三条判据 **「去空白后非空」**，否则红、文案点名「执行点为空（未接线）」。
  理由：诚实边界说的是「证不了它**真跑了**」，而**空文件连「有命令」都不成立**——那是实现漏洞，不是能力天花板。
- 判定仍**零依赖**（文件存在 + 字符串包含），**不解析 YAML、不执行命令**。

### D5 `gate.yml` 那一步的形状（grill v2 的 CRQ-10）

```yaml
- name: adopter tests
  if: ${{ !cancelled() }}
  env:
    WL_TESTS_FILE: .github/witnessloop-tests.txt      # ⚠️ 必须等于 constants 里的默认路径
    WL_TESTS_SENTINEL: "<<REPLACE-ME>>"               # ⚠️ 必须等于 constants 里的哨兵串
  run: |
    [ -f "$WL_TESTS_FILE" ] || { echo "::notice::无测试执行点"; exit 0; }
    CMD=$(cat "$WL_TESTS_FILE")
    case "$CMD" in *"$WL_TESTS_SENTINEL"*) echo "::notice::执行点未接线"; exit 0;; esac
    sh -c "$CMD"
```

⚠️ **口径必须与 `check` 共用同一个来源**（对抗轮 X3）：路径与哨兵串都由 `constants.py` 定义，
workflow 里的字面量必须与之**逐字相同**——否则会出现「`check` 判红、门禁却静默跳过」（或反过来）。
⇒ 加一条**测试**钉住三处一致（`constants` / `gate.yml` / `policy` 默认值）。

- **路径经 `env:`、命令在运行时读**：`${{ }}` 插值发生在**解析期**，文件内容不受控 ⇒ 插值等于把接入方内容
  当 workflow 源码；`env:` + `cat` 让内容永远只是**数据**。
- **文件缺失 _或_ 内容为哨兵 ⇒ 跳过**（原稿只写了「缺失 ⇒ 跳过」——哨兵会被 `sh` 当命令执行，
  症状是 `sh: Syntax error` 而不是清晰文案）。
- ⚠️ **`spec.md` 里那句「命令出现在 `env:` 里」是写不出来的**（命令文本根本不在 workflow 里）⇒
  断言的主语必须改成**文件路径**。

### D6 策略字段的**缺省语义**：**取「字段缺省 ⇒ 声明」**（与既有惯例一致）—— **Q1**

- `policy.py:94-95` 的注释明写「保护性默认，别让老 policy 静默失去这条规则」；`require_change_for` 就是三态
  （缺省→默认、显式 `[]`→关）。本字段照抄这个三态。
- ⚠️ **但出厂 policy doc 里不物化 `tests` 键**（对抗轮 X2）：`init` 的 desired policy 一旦多一个键，
  **已接入仓**跑 plain `init` 就会因「本次期望 ≠ 磁盘」**exit 1**（实测，与本仓 `init --dry-run` 那条同机制）。
  ⇒ **语义默认只活在 `from_doc` 里**（缺省 ⇒ 用默认路径判），**不写进 `default_policy_doc()`**。
- ⚠️ **opt-out 的字面必须显式**（X2 后半）：`from_doc` 用的是 `evidence.get(k) or DEFAULT`（falsy 即回落）
  ⇒ `""` / `null` / 缺省**都会**被读成「声明」。⇒ 唯一的「不判」形态是显式布尔 **`tests.disabled: true`**
  （`init --no-tests` 写它）。这条是「一句话能被实现成两种结果」的典型，必须钉字面。
- 后果与配套：**本仓自己与 `wl-test` 的 policy 都没有 `tests` 键** ⇒ 移动 `v1` 后**立刻**跑上新 CLI、**立刻红**
  （文件不存在）⇒ **必须补一条迁移任务，且排在移 tag 之前**（D7）。
- 取「缺省 ⇒ 不判」的代价：本仓要 opt-in = 改受保护路径 = **一条解释事件**，一样要一次人工动作，
  却把默认从「拦」变成「不拦」——机械版立论就空了。

### D7 发版 / ref：**仍然移 `v1`，但拆成可回滚的两步** —— **Q6**

- 为什么必须移：`init` 写的是 `@v1`、`gate.yml` 的默认也是 `v1` ⇒ 「让新 `gate.yml` 到达 pin `@v1` 的仓」
  **只有**移动这一个办法（换 `DEFAULT_GROGATE_REF` 只影响将来新接入的仓，救不了本仓与 `wl-test`）。
- **全部后果列全**（原稿只写了①②）：① 本仓自举换新 `gate.yml`（意图内）；② 本仓自举的 **CLI 版本**一起换；
  ③ `wl-test` 同样换（无 branch protection，影响仅限此）；④ 将来按文档接入的仓拿到 v1.6.0 语义（意图内）；
  ⑤ 读者按 `README.md:20` 本地 `uv tool install …@v1` 的 CLI 也一起换；
  ⑥ **tag 的 annotated 注记会变错**（现文「当前指向 v1.5.0」）⇒ 一起改。
- **执行粒度**：**给本仓补执行点（一个 PR）→ 发 `v1.6.0` → 移 `v1`（单独一次操作）→
  在移完后的第一个 PR 上人工确认 `gate / check` 的结论符合预期**。
  ⚠️ **原稿这里写过「先移 tag ⇒ 本仓合不了任何 PR（含补执行点那条）」——对抗轮实测证伪**：
  `check` 判的是**被检 head 的树**，而补执行点那条 PR **自己就带着那个文件** ⇒ 它是绿的。
  真实代价只是「**在途** PR 在补文件落地前会红」⇒ 顺序仍按上面的写法（先补、再移），
  但理由是「**缩小红的窗口**」，不是「避免自锁」。

### D8 v1 的两份报告**移出 `reviews/`** —— **Q5**

- 孤儿规则是 **`reviews/**/*.md`（递归）**，且 `matching[0]` 按**路径字典序**取 ⇒ v1 的
  `grill-review.md` / `grill-adversarial.md` 若留在 `reviews/` 下：既会**变成孤儿**（没 manifest），
  又会**抢绑**（字典序在 v2 报告之前 ⇒ 被校验正文的是 v1 那份，而它绑的是旧 revision 的 hash ⇒ 必判 drift）。
- **定案**：移到 `openspec/changes/adopter-test-gate/history/v1/`（不属 `reviews/` ⇒ 两条红都不发生），
  只留一份 `stage=grill` 的 manifest 指向 v2 的决策记录。
- 保留它们的理由：那批**被证伪的实测事实**（死锁/不可达/`always()`/三文件契约…）仍然是本 change 的证据链的一部分。

### D9 文档（含**四条**诚实边界）

- `README.md`：接入段（`init --test-command`、命令文件怎么改、**同 job ⇒ 不用新增勾选**）+
  **四条边界**：① `check` 只保证「**存在、非空、已接线**」，不保证**真跑了**；② **PR 可以改自己的 CI**；
  ③ 测试命令是**任意代码**、会在每个 PR（含 fork PR）跑；④ **能力天花板**（只有 `contents: read`、
  没有 services/matrix/额外 action、命令只能一行 shell；需要这些 ⇒ 改用乙）。
- `docs/gate.md`：§1（产物清单多一个命令文件 + 它的双重身份）、新增一小节（执行点门禁的语义与边界）。
- `templates/review-loop.md`：补一句「测试须由 CI 执行」。
- ⚠️ **已接入仓 opt-out 的摩擦要写明**：`--no-tests` 只在**新接入**时可用；已接入仓只能改
  `.witnessloop/policy.json`，而它是**不变集**且状态是 `M` ⇒ **每次都要写一条 `protected_path_write` 事件**。
- ⚠️ **opt-out 只关 `check`，不关「门禁那一步」**（对抗轮 X7）：`tests.disabled: true` 时 `check` 不判，
  而 `gate.yml` 的测试步骤**照旧会跑**（文件在就跑、不在就跳过）⇒ 若接入方想「连跑都别跑」，
  那要删掉命令文件（步骤会跳过）。这条 SHALL 写进文档，避免「opt-out 了却还在跑测试」的困惑。

## 3. 接线点

- `constants.py`：命令文件路径 + 哨兵串。
- `policy.py`：语义 = **缺省 ⇒ 声明**（用默认路径）、**`tests.disabled: true` ⇒ 不判**；
  ⚠️ **`default_policy_doc()` 不物化 `tests` 键**（见 D6/X2）——「显式空 ⇒ 不判」这个字面**不成立**
  （`or DEFAULT` 会把 `""`/`null` 都读成声明）
- `checkcmd.py`：新判定（存在 + 去空白非空 + 无哨兵）。
- `initcmd.py`：种子走**独立路径**（不进 `desired_files()`、不进台账、不参与冲突）+ `--test-command` / `--no-tests`。
- `.github/workflows/gate.yml`：D5 的 step（**`gate / check` 这个 job 名不变**）。
- `tests/`：三态 + 空文件 + 哨兵 + `init` 侧（含「改命令后 plain `init` 仍 exit 0」这条回归）。
- 文档（D9）。

## 4. 风险

1. **R1（中 · 发布顺序）**：先移 tag 再补执行点 ⇒ **在途** PR 会红（而**补执行点那条 PR 自己带着文件、是绿的**
   ——对抗轮 X4 实测证伪了原稿「本仓合不了任何 PR」的说法）⇒ D7 的顺序（先补 → 发 tag → 移 tag）
   仍保留，理由是**缩小红的窗口**，不是避免自锁。
2. **R2（中 · 台账）**：种子若进了 `desired_files()` ⇒ 接入方改命令后 `init` 永久冲突 ⇒ D3 是硬要求。
3. **R3（中 · 能力边界）**：只保证「存在 + 非空 + 已接线」，**不保证真跑了**（D4/D9 的边界）。
4. **R4（中 · 平台）**：PR 可以改掉自己的命令文件/CI ⇒ required 依旧绿（既有边界，须写明）。
5. **R5（中 · fork PR）**：测试命令是任意代码，会在 fork PR 的 runner 上执行。
6. **R6（中 · 契约）**：新增第四个产物 ⇒ 破「三文件」契约（`docs/gate.md:9`、`tests/test_init.py:18,72,103`），必须进 spec。
7. **R7（中 · 报告布局）**：v1 两份报告留在 `reviews/` ⇒ 孤儿 + 错绑两条红（D8）。
8. **R8（低 · 自举）**：本 change 若改 `caller_workflow()` 的字节 ⇒ 本仓 init 台账与磁盘不一致（本来已坏，见 §1）。
9. **R9（低 · 迁移）**：`wl-test` 会被移 tag 波及（影响仅限该仓，且它连 protection 都没开）。

## 5. 测试策略（TDD）

- `check`：**缺失 / 空（含纯空白）/ 含哨兵 / 已接线** 四态 + 未声明 ⇒ 不判；并证明**不执行**命令。
- `init`：三态（`--test-command` / 无参⇒哨兵 / `--no-tests`）+ **改命令后 plain `init` 仍 exit 0**（D3 的回归）
  + 幂等 / 冲突 / `uninit`（命令文件**不在台账** ⇒ 无需改 `uninitcmd`）。
- `gate.yml`：pyyaml 结构化断言（step 存在、**路径**走 `env:`、`!cancelled()`、缺失/哨兵时跳过）+ `job` 名不变。
- 端到端：真仓 `init --test-command "sh -c 'exit 1'"` ⇒ `check` 绿（执行点在）而门禁跑该命令会红。

## 6. 停轮（Q1..Q8 —— 待用户确认）

| # | 问题 | 推荐 |
|---|---|---|
| **Q1** | 策略字段**缺省**语义：**甲** 缺省⇒声明（合既有惯例，需配套本仓迁移任务）／乙 缺省⇒不判（本仓要 opt-in = 一条解释事件） | **甲** |
| **Q2** | 种子**进不进 `desired_files()`**：**不进**（走独立路径）／进（⇒ 改命令后 `init` 永久冲突） | **不进** |
| **Q3** | 「文件存在但空/纯空白」判什么：**红**（加第三条判据）／绿 | **红** |
| **Q4** | 本仓自己怎么拿到执行点 + 移 tag 的先后：**先补文件（手工提交）→ 再移 tag**；**放弃**把 `ci.yml` 的 `test` 勾 required（会与执行点跑两遍同样的 pytest） | **按此** |
| **Q5** | v1 的两份报告：**移出 `reviews/`**（到 `history/v1/`）／留下（⇒ 孤儿 + 错绑） | **移出** |
| **Q6** | 发版：**仍移 `v1`**，但拆成「发 `v1.6.0` → 补执行点 → 移 `v1` → 人工确认首 PR」并**改 tag 注记**／只发新 tag 不动 `v1`（本仓自举永远跑旧 CLI） | **移 `v1`（分步）** |
| **Q7** | D1 形态：**甲**（+ 把**能力天花板**写成第四条边界）／乙（要再勾一次 required）／丙（撞台账死锁） | **甲 + 写清天花板** |
| **Q8** | 测试步骤的 `if:`：**`!cancelled()`** ／ `always()`（run 被取消时还会跑）／默认（`check` 红时不跑测试） | **`!cancelled()`** |
