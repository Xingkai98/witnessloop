# 设计阶段对抗验证（第 1 轮 R1）

> 零记忆独立审阅者产出。算法与格式依据 `templates/grill.md` §5（设计阶段对抗验证 loop）。
> **立场：默认上一轮（`reviews/grill-review.md`）的结论有错，逐条去证伪**；能实测的一律实测。
> 被审 revision `0316bc00ebcde569205d8ff25f88e7e47d961ad2`；被审 worktree **全程只读**，
> 唯一仓内写入是本文件（`git status --porcelain` 在本文件创建前为空）。
> 所有实验在 `/tmp/adv-atg`（被审 revision 的隔离副本）、`/tmp/v1cli`（`v1` tag 的克隆）、
> `/tmp/adv-hist`（带完整历史的克隆）、`/tmp/e1`–`/tmp/e4`（一次性 fixture 仓）中完成。

## Reviewer

- run id: `grill-adversarial-reviewer-adopter-test-gate-0316bc00ebcd`
  （环境未设 `WITNESSLOOP_RUN_ID` / `WITNESSLOOP_REVIEWER_RUN_ID`，按 `templates/grill.md`
  「怎么取 run id」第 2 条生成**确定性兜底 id**：`<stage>-<role>-<anchor>`，
  anchor = change id + 被审 revision 前 12 位。**这是审阅目标的指纹，不代表真实 run 身份。**）
- 时间: 2026-10-12T15:55:55Z
- 方法（可复现）：
  - 副本 `/tmp/adv-atg`：`cp -a` 后 `rm -f .git && git init -q && git add -A && git commit -qm base`
    （被审 worktree 的 `.git` 是 `gitdir:` 指针文件，不隔离会写回原仓），再 `rm -rf .venv && uv sync`。
  - 基线独立复现：`uv run pytest -q` = **431 passed**（与任务书一致）。**未改动任何测试文件**
    ⇒ 下面的实测都是**未打补丁的工具**的行为；唯一一次打补丁是 SIM-E3（把 `desired_files()`
    包一层加一个种子文件来模拟「戊」），该条**明确标注**在报告中。
  - `v1` 那一侧：`git clone` 出独立仓 → `git checkout v1` → `uv sync`，用**真的 v1 CLI** 跑
    `check`（不是在 main 上模拟），因为本 change 的 PR 实际由它把关（见 B1）。
  - 平台事实用 `gh` CLI 对**真实仓**重新取证（branch protection / PR checks），不引用上游结论。
  - **未做**端到端 GitHub Actions 实测（无法在本机跑 Actions）；凡涉及平台运行时行为的断言都标注置信度。

## Verdict

**CHANGES_REQUESTED**

四条阻塞项 —— 都会让实现照着错的结论走、或让交付物与 issue/spec 对不上：

| # | 阻塞项 | 落点 |
|---|---|---|
| **B1** | 本 change 的门禁由 **`v1` CLI** 执行，而 v1 **没有 `evidence` 模块** ⇒ 上游「必须有三份 manifest，否则红」是**假的**（实测：v1 报 1 条、main 报 4 条） | `grill-review.md:81-87`（CD-9）、`tasks.md:61-64`（F0/F1/F2）、`README.md:105-120`、`templates/grill.md:195-200` |
| **B2** | D1 推荐的「**戊**（辅）」：对存量仓不可达**且**与 `spec.md:11-12` 直接冲突（戊 的种子文件**就是** init 生成、又**必须**被接入方改） | `design.md:30-46`（D1）、`tasks.md:16`（A2）、`spec.md:11-12` |
| **B3** | `design.md:65-66` 的「恢复路径**只有**『恢复字节 + 删台账』」是**假的**：实测有**三条**出口，且「恢复字节」不必删台账 | `design.md:64-67`（D3-①）、`grill-review.md:98-99`（CRQ-1）、`tasks.md:28-31`（B2）、`grill-review.md:269-271`（R10） |
| **B4** | `tasks.md:65`（F3 **关 issue #4**）与 issue #4 原文不符 —— #4 给的两条建议**都是机械的**，己 一条都不做 | `tasks.md:65`、`design.md:9`、`design.md:159-171` |

非阻塞（观察 / 文案 / 补测）写在 `## 新发现` 的 N1–N6 与 `## Code-Resolved`，**不影响本 verdict**。

## 逐条对抗

### 对 `## Confirmed Decisions`（8 条，逐条）

**CD-1（issue #4 的问题成立）—— 维持。** 独立复核：`gh issue view 4` 原文与我读到的
`proposal.md:11-17` 口径一致；上游引的 `wl-test` 只有 `witnessloop.yml` 一个 workflow、
acid test PR 的 job 只有 `gate / check` 我没有逐条重跑（需要网外资源），但**本仓自己**
就是同一个形态（CRQ-N6：本仓 `test` job 非 required）——问题成立，且多一个证据点。

**CD-2（required 粒度 = job）—— 独立复核属实，且这是本设计唯一真正的天花板。**
`gh api repos/Xingkai98/witnessloop/branches/main/protection` 我重跑：`contexts = ['gate / check']`、
`strict = true`、`enforce_admins = true`、`approving_count = 0`、`codeowners = False`。
⇒ 「required 必须人工勾一次」成立。**但它的推论被上游放大了一步**：它只推出「**必然有一步人工**」，
**不**推出「整条路径都该是人工的」（见「对推荐方案 B-1」）。这是本报告与上游最大的分歧点。

**CD-3（D5 硬前置：未声明 input ⇒ `startup_failure`）—— 方向维持，但严重度与落点要改。**
① 我**同样无法**端到端实测（无 Actions 环境），沿用上游「非官方明文、置信度中高」的标注，**不辩解**。
② 但这条在**本 change 的推荐方案下已被绕开**：己 的 caller 里根本没有 `with:`（实测生成物
`initcmd.py:24-41` 只有 `uses:`），R8 的触发面消失。③ 真正的问题是**上游把这条的严重度用在了错的
地方**：它把「必须决定 D5」当成硬前置，却漏掉了一个更硬的事实 —— **本 change 自己的 PR 由 v1 把关**
（B1），而 D5 的整个论证正是 R12「移动 `v1` = 换 CLI」。⇒ 见 B1。

**CD-4（`test_command` 要进台账）—— 只对「甲/乙」成立，对推荐方案无意义，且**不该**进 spec。**
实测：`init --test-command "pytest -q"` 这条路在推荐方案（己/戊）下**不存在**（命令住在接入方自己的
文件里，`design.md:57-58`）。上游把一条**只属于备选分支**的机制写进了 Confirmed Decisions，
而它下游的 Q2 推荐答案也是这条 —— 这与 D1「否甲为主」互相矛盾：**既然甲是备选，为什么它的补丁
排在推荐答案里？**（`grill-review.md:190-196`）。非阻塞（不改变交付物），但它让「必然要做的改动」
清单虚高一项，会误导排期。

**CD-5（`v1` 的语义订正）—— 独立复核属实。** `git tag -n99 v1` = 「滚动大版本，当前指向 v1.5.0」；
`v1^{commit} == v1.5.0^{commit} == 843b691de2f7…`；`git rev-list --count v1..origin/main` = **6**。
上游的表述订正（不是「固定 tag」）**成立**，我维持。

**CD-6（零依赖 ≠ 只能子串匹配；有「运行时读仓内文件」第三条路）—— 成立，但与本 change 无关。**
`pyproject.toml` `dependencies = []` 实测；`grep -rn yaml src/` 零命中。CRQ-8 那条第三路（甲′）
确实存在且自洽。**但它是「甲」的变体**（`design.md:59-62` 自己也这么归），在推荐方案下不该出现在
Q2 的推荐答案里（同 CD-4）。

**CD-7（「新增 init 产物」对存量仓是死的）—— 独立复核属实，这是本报告确认的最扎实一条。**
实测 E3：老仓（被**旧**工具 init 过）跑**带种子文件**的 `init` ⇒ 输出
`init：已接入 witnessloop（幂等，无改动）。`、**exit 0**、`seeds present? False`。
机制：`initcmd.py:166-167` → `_already_initialized`（`initcmd.py:207-281`）在无漂移无冲突时
`initcmd.py:280-281` 直接返回，**不进入任何写盘路径**（写盘只在 `initcmd.py:188-194`）。
⇒ 「戊/丁 到不了存量仓」成立。**但上游由此得出的结论用在戊身上是错的**（B2）。

**CD-8（本 change 命中自身门禁的正面要求）—— 证伪。这是本报告最重要的一条。**
上游说：本 change 改 `src/**` ⇒ 「除 `stage=grill` 外还**必须**有 `stage=grill-adversarial` 的
manifest（`templates/grill.md:195-200`，issue #16）」。**实测为假**：

- 本仓自己的 caller 是 `.github/workflows/witnessloop.yml:14` → `uses: …gate.yml@v1`；
- `gate.yml:19-23` 的 `witnessloop-ref` **默认 `"v1"`**、caller 从不覆盖 ⇒ `gate.yml:57-58` 的
  `uvx --from git+…@${{ inputs.witnessloop-ref }}` 装下来的是 **v1 的 CLI**；
- **v1 没有 `evidence.py`**（`git show v1:src/witnessloop/evidence.py` = `fatal: exists on disk,
  but not in 'v1^{commit}'`），v1 的 `checkcmd.py` 只 import `contract/gitutil/events/paths/policy`；
- v1 的 `REVIEW_MANIFEST_REQUIRED_FIELDS` **连 `stage` 都不在必填里**（main 才加，`constants.py:79-89`）。

实测（`/tmp/adv-hist`，造「实现已落地」的 diff：`templates/**` 命中 `require_change_for`）：

```
$ (v1)   witnessloop check --root /tmp/adv-hist --base de51a01 --head HEAD
check：未通过 ✗（1 项）
  1. …：缺少 review manifest（审阅证据必须「报告 + manifest」成对，glob=reviews/*.manifest.json）
$ (main) witnessloop check --root /tmp/adv-hist --base de51a01 --head HEAD
check：未通过 ✗（4 项）
  1. 缺少 review manifest   2. 无 stage=grill 的 manifest
  3. 无 stage=grill-adversarial 的 manifest   4. 无 stage=building 的 manifest
```

⇒ `stage=grill` 正文校验、`grill-adversarial` 硬门、`building` 硬门**在本仓的 PR 上全部未生效**。
连带后果，三条都要改：
① `grill-review.md:81-87` 的 CD-8 应按第 6 处事实订正写进 `design.md §7`；
② `tasks.md:61-64`（F0/F1/F2）把三份 manifest 写成「必须」，实际是**自愿的超额交付**——
写「必须」会让实现者以为有机械兜底（正是本仓最恨的「看起来在保护你」）；
③ `README.md:105-120` 与本 change 要追加的 `templates/grill.md:195-200`，对**任何 `@v1` 接入方**
都是**空承诺** —— 而 R12（移动 `v1` 才送达）在同一份报告里被当作选己的核心理由。
**这是本 change 立论自身的活体反例**：它一边论证「6 个提交的行为变更到不了接入方」，
一边假定「这 6 个提交的行为变更在自己仓里已生效」。修法见 B1。

### 对「原稿被证伪的事实」5 条

1. `design.md:29`「`check` 也在 guard 路径上被调用」= **假** —— **维持上游**。
   `src/witnessloop/guardcmd.py:29-33` 只 import `constants/contract/evidence/paths/policy/gitutil`；
   `cli.py:153-160` 把 `guard`/`check` 分别分派。结论（不让 `check` 跑测试）保留、论据已换 ✓。
2. 「`v1` 不是固定 tag」= **维持**（`git tag -n99 v1` 原文见我上面的 CD-5）。
3. `tasks.md` 原 B5「改 `caller_workflow()` 字节 ⇒ 存量仓 init 报冲突」= 半假、两分支相反 —— **维持上游**。
   机制我也读了：台账漂移查的是「**磁盘 vs 台账 sha**」（`initcmd.py:228`），本次期望查的是
   「**磁盘 vs 生成的 desired**」（`initcmd.py:265-278`），两者正交 ⇒ 结论成立。
4. 「D4=空则跳过是移动 tag 唯一安全形态」不完整（漏 `witnessloop-ref` 默认 `v1`）—— **维持**，
   并且我加了更硬的一层证据：**本仓今天已经处在这个「没滚」的状态里**（B1/CRQ-C）。
5. `design.md:98-104`（D8 文档影响清单）有漏项 —— **维持**，但**上游自己又漏了两条**：
   ① `templates/**` 是 `require_change_for` 命中面，而这份清单没把「模板住哪」当成契约问题（见 N2）；
   ② 漏了「本 change 要动的 `templates/adopter-tests.yml` **如何到达接入方**（哪个 ref）」——
      而这个漏洞与 D5 否乙的理由**同源**（见 N1）。

### 对 风险 R8–R18

- **R8（未声明 input ⇒ startup_failure）** —— 方向维持、置信度标注维持（我无法实测）。**但对本 change
  已不适用**：己 的 caller 无 `with:`。⇒ 建议把 R8 从「本 change 的风险」重分类为「**甲分支**的风险」，
  否则它在 §4 里占着一个「高」，读者会以为推荐方案背着它。
- **R9（PR 可改自己的 CI）** —— **维持，且必须进 spec**（`spec.md:60-70` 已写）✓。补一条上游没说的：
  这条边界在本 change 的推荐方案下**更宽**，因为测试命令住在接入方自己的 workflow 里 —— 一个 PR
  不但能删掉它，还能把 `run:` 改成 `true`，而 required check 依旧绿。文档必须按「**你自己**的 CI 配置
  未被本次 PR 修改」措辞（`spec.md:62-65` 已经是这个口径 ✓）。
- **R10（台账死锁，高）** —— **结论的「无 flag 出口」属实，但「无出口」是错的**（B3）。
  另外**严重度分级错了**：R10 只有在 Q1=甲/丁 时才是「高」（那时文档真的教人手改 init 产物）；
  Q1=己 时它退化为**文档约束**（`spec.md:27-39` 那条 Requirement）。建议改成条件式严重度。
- **R11（多写一个文件到不了存量仓）** —— 维持，实测已复核（CD-7/E3）。
- **R12（`@v1` 同时钉 gate.yml 与 CLI）** —— **维持并加强**：我不但复核了 `gate.yml:19-23` 与
  `constants.py:11`，还实测了它今天的**后果**（B1）。这条是上游写得最好的一条。
- **R13（失败交互）** —— 维持「走甲才存在」；推荐方案下自动消失 ✓。
- **R14（reusable workflow 权限不能超出 caller）** —— 维持。补一条：`gate.yml:25-26` 的
  `contents: read` 是**这个论据的实测落点** ✓（我读了同一行）。
- **R15（破三文件契约）** —— 维持，但**上游自己踩了它**：推荐了戊（D1）却没把
  `spec.md` 的对应 Requirement 写出来（`spec.md` 通篇没有一个字提三文件 / 种子文件），
  只在 R15 里挂了个「必须进 spec delta」的欠条。⇒ 这是 B2 的一半。
- **R16（`run:` 里裸 `${{ }}` 断言会直接红）** —— **维持，独立复核属实**：
  `gate.yml:57-58` 的 `run:` 里确有裸 `${{ inputs.witnessloop-ref }}`，同 step 的
  `inputs.base-ref` 走了 `env:`（`gate.yml:48-50`）。✓
- **R17（改 `caller_workflow()` ⇒ 本仓 init 台账与磁盘不一致）** —— **维持，前提实测成立**：
  本仓 `.witnessloop/init-manifest.json` 里两项 sha 与磁盘**逐字节一致**
  （`policy.json 0d1a84f019a9`、`witnessloop.yml 4861a80caf3e`，均 match=True）。
  ⇒ 本 change 一旦动生成物，本仓此后任何 `init` 都会撞 B3 的多条分支。✓ 风险真实。
- **R18（理由句精度）** —— 维持（同证伪清单第 1 条）。

### 对推荐方案（B-1 … B-4，本节是最重要的）

#### B-1 己 还算不算「机械强制」？—— **不算，而且它没把这件事说出来**

事实面：己 = 一份可复制的 YAML + 文档 ⇒ **零强制**。接入方不拷、不勾，什么都不会发生；
拷了不填命令，得到的是**绿 job + 一行 notice**（D4）。这与 issue #4 原文给的两条建议
（`gh issue view 4`：「要么 `init` 生成的 caller workflow 顺带跑目标仓的测试…，要么在 policy 里加
「测试命令」字段由 `check` 调用」）**一条都不对应**。

**我的判断：这是「诚实的最小交付」，但诚实只到一半。**
- 站得住的部分：「required 的勾选在所有方案里都是人工的」（CD-2，我复核属实）⇒ 交付物里
  **必然**含人工步骤；在「不移动 `v1`、不碰 `gate.yml`」这两条本 change 自设的约束下，
  **任何 CLI 侧机制对存量接入方都不可达**（`@v1` 冻结 ⇒ CRQ-C）——所以「先发模板 + 文档」
  这个**排序**是对的，我不反对。
- 站不住的部分（这才是 B4 的实质）：**交付物没有一句说「本 change 零机械强制」**。
  `design.md:9` 仍在说「交付『接入方能拿到一个可用的测试执行点』这一件事」，`tasks.md:65` 还要
  **关 issue #4**。⇒ 后果是：一份**零强制**的东西，以一个**机械门禁**项目的名义，关掉了一个
  **明确要机械机制**的 issue。这正是本仓自己最反对的形态（「永远绿的断言」/「看起来在保护你」）。
- **该保留哪一部分机械性**（具体、且不违反本 change 的约束）：
  1. **模板区分「未声明」与「占位符没填」**：空 ⇒ 跳过 + `::notice::`（符合 `spec.md:41-58`）；
     **模板原样的占位符未替换 ⇒ `::error::` + exit 1**。这完全住在接入方自己的文件里，零接口、
     零 ref、零 CLI 改动，却把 D4 自己点名的「**看起来在保护你**的绿勾」（`design.md:71-74`）
     从「大概率发生」压到「必须显式确认才可能」。**这是我认为最该加的一条**，而它恰恰是
     D4 的论证与 D1 的推荐之间**没有闭合**的缺口：己 让「拷了不填」成为最可能的失败模式，
     D4 的缓解（notice）却是为「存量空命令」设计的。
  2. `check` 在「仓里除 caller 外没有任何 workflow」时打一行 `::notice::`（零依赖：列
     `.github/workflows/*` 即可，**不解析 YAML**、非 finding、不改退出码、不改 `check` 语义）——
     这是 B-4 那条「第四条路」。它只提供**可见性**，不提供强制，且同样受 ref 冻结约束。
  3. 配方给一条**可直接执行**的获取命令 + 一个钉住的 ref（见 N1）——把「人工步骤」从
     3 步（找文件 / 拷 / 改）压到 2 步，且不会踩 404。
- **分数**（可达性 / 强制力 / 实现成本 / 对 issue #4 的覆盖，各 0–5）：

  | 方案 | 可达存量 | 强制力 | 成本 | 覆盖 #4 |
  |---|---|---|---|---|
  | 己（现状推荐） | 5 | 0 | 1 | 0 |
  | **己 + 上面 ①②③** | 5 | 1（可见性，非拦） | 2 | 1 |
  | 甲 | 2（需换 ref） | 3 | 4 | 3 |
  | 戊（现状）/ 丁 | 2 | 3 | 5 | 3 |

  ⇒ **不足以推翻己，但足以要求把己写成「己 + ①②③」并把「零机械强制」写进交付物。**

#### B-2 己 与 戊 的组合自洽吗？—— **不自洽，戊 应删**

- 戊 对**存量**仓不可达（CD-7/E3 实测），而己 对**新**仓也可达 ⇒ 戊 给新仓省的**只有一次 `cp`**。
- 代价（都不是零）：破 `docs/gate.md:9`「只写三个文件」+ `tests/test_init.py:18,72,103` 三处钉死
  （CD-10/CRQ-10 属实）；新增「种子文件」语义（不存在才写、不进台账、不参与 `uninit`）；
  新增 spec Requirement（现在一个字都没有，R15 只是一张欠条）。
- **一处负作用（上游完全没提）**：`.github/workflows/**` 下的文件 GitHub **会直接执行**。戊 的种子
  模板若按 D4 的语义（空 ⇒ 跳过）出厂，新接入方**开箱即得一个永远绿的 no-op check**
  —— 这正是 `design.md:71-74`（D4）、`spec.md:46-48` 点名最恨的形态，而它由**工具自己**
  静默种下。戊 越「无感」，越像 D4 警告的那个「看起来在保护你的绿勾」。
- **若日后仍要做戊，形态建议**：`init --with-tests` **显式 opt-in**（默认路径仍「只写三个文件」
  ⇒ `tests/test_init.py` 的既有断言不必改，`docs/gate.md:9` 的默认契约不必破），
  且种子内容必须是 **①②③ 的「占位符未替换 ⇒ 红」版本**，不能是空 ⇒ 绿。

#### B-3 `spec.md` 的 Requirement 在己 下是否自洽？

- **「空命令 ⇒ 跳过 + 可见信号」（`spec.md:41-58`）：在己 下仍有「空」这个状态，可测，但测的是别的东西。**
  己 里命令住在接入方自己的文件 ⇒ 「空」= 模板的 `TEST_COMMAND` 为空/未填。可测性：
  **结构式可行**（pyyaml 解析模板断言「空分支打印 `::notice::`、非空分支回显命令」，
  与 `tests/test_gate_workflow.py:32-34` 的先例同款）；**行为式不可行**（`spec.md:50-53` 的
  Scenario 写的是「**When** PR 触发 … 日志里有一行」，本仓没有任何测试能验证 GitHub 的日志）。
  ⇒ 非阻塞，但 spec 是契约：应把 Scenario 改写成对**交付物内容**的断言
  （N5），否则这条 Requirement 在本仓**不可证伪**。
- **关于文档的 Requirement 是不是注水？—— 不是，本仓有现成范式，但 tasks 没给它安排任务。**
  `tests/test_docs.py` 里的 `test_every_idempotency_claim_is_scoped_or_qualified` 就是
  「同一文件里**每一处** X 都必须带限定词（±2 行窗口）」的机械实现；`test_docs_no_longer_call_hooks_advisory_only`
  是「禁语字面量 + 必含 token」的另一范式。⇒ 「不得过度承诺」（`spec.md:60-70`）完全可以照抄
  这个范式钉住（README / `docs/gate.md` 里每处「拦住合并」都要有「在…前提下」窗口）。
  「SHALL NOT 要求手改 `init` 产物」（`spec.md:27-39`）也一样可钉：除文档禁语外，还可以直接
  对 `init` 的 **stdout** 断言（本仓已有 `tests/test_init.py` 的子串断言先例）。
  ⇒ 结论：**这两条不是注水，是「钉得住但没人安排去钉」** —— 属于 tasks.md 的漏项（N4）。
- **`templates/**` 的检查面也漏了一条**：`tests/test_templates.py:39` 的 fixture **只**参数化
  `[grill.md, review-loop.md]` ⇒ 新增的 `templates/adopter-tests.yml` 会**自动豁免**
  「存在 / >500 字符 / host 中立」三条检查（N2）。tasks A4 只安排了「模板内容的 pyyaml 断言」，
  没有安排「把新文件纳入模板检查面」。

#### B-4 有没有第四条路被两轮都漏掉？

有，但**都不足以推翻己**，应作为己的增量（见 B-1 的 ①②③）：
- `init` 输出里给可直接执行的 `gh` 命令 / `gh workflow` 可安装的 starter：**部分被漏**。
  `design.md:123` 说「`initcmd` 只在 `init` 输出里加一行提示」——但 `tasks.md` **没有对应任务**（N3），
  且「一行提示」比「一条可执行命令」弱。可达性：只到达**新**接入方（存量仓跑 init 会报
  「幂等，无改动」，提示也只在写盘分支打印，见 `initcmd.py:196-204`）⇒ 中等价值。
- 让 `check` 在「测试 workflow 不存在」时给**可见提示**（不拦、每次都提醒）：**被完全漏掉**，
  就是上面 ②。零依赖可实现（列目录，不解析 YAML），成本极低；但对 `@v1` 接入方不可达。
- 更值得做的其实是 **①（占位符未替换 ⇒ 红）**：它不新增任何 witnessloop 侧机制，
  却把己 的最大风险（拷了不填 = 绿）消掉 —— 而这一条在两轮里**都没有出现过**。

## 新发现

- **N1（中 · 分发面）｜己 的交付物没有「到达方式」**：`tasks.md:27`（B1）写「README 配方：
  拷模板 → 改一行 → 勾 required」，但**没说从哪拷**。而本仓的惯例是**钉 ref**
  （`constants.py:11` 的 `@v1`），`@v1` 上**不会有**这个新文件（v1 落后 6 个提交，含本 change），
  D5 又明确「不移动 `v1`」⇒ 抄 README 的接入方按直觉去 `@v1` 取模板会 **404**。
  ⇒ 配方必须给出**可达 ref + 一条可直接执行的获取命令**。同一问题也吞掉 tasks D3
  （`templates/review-loop.md` 补一句）：对 `@v1` 接入方，这份模板改了**也不会生效**，
  所以 `design.md:106-109`「不改它这条冲突就还在」**只在本仓内为真**。
- **N2（低-中 · 目录契约）｜`templates/adopter-tests.yml` 放错地方**：`templates/` 的契约是
  「**host 中立**模板（不含任何 host 专有语法）——否则『模板与适配器物理分离』就是名义上的」
  （`tests/test_templates.py:1-5,24-31`，亦见 `agentenv.py:23,37-38` 的
  `WITNESSLOOP_TEMPLATES_DIR` 语义）。放一份**纯 GitHub Actions** 的 YAML 进去，与这个契约相抵；
  且 `tests/test_templates.py:39` 的 fixture 只覆盖两个 `.md` ⇒ 新文件自动豁免三条检查。
  ⇒ 建议 `templates/github/` 之类子目录 + 纳入 fixture，或明确修订目录契约（本 change 没提这件事）。
- **N3（低 · tasks 漏项）｜两条已承诺的事没有任务，也没有测试**：
  ① `design.md:123`「`initcmd` 只在 `init` 输出里加一行提示」——`tasks.md` A/B/C/D/E/F **无此项**；
  ② `spec.md:82-89`「不新增运行时依赖」——`tasks.md` 无任务，`tests/` 里也**没有任何**测试
  钉 `dependencies == []` / wheel 的 `Requires-Dist`（我 grep 过 `Requires-Dist|dependencies` 在
  `tests/` 零命中；只有 `ci.yml:33-36` 的打包冒烟，它**不**断言依赖为空）。
  ⇒ spec 有 Requirement 而无任务，属「写在纸上没有落点」。
- **N4（低 · 漏测）｜文档类 Requirement 未被安排钉住**：见 B-3 第二条，范式在
  `tests/test_docs.py` 现成可用。
- **N5（低 · spec 可证伪性）｜`spec.md:50-53`、`:67-70` 的 Scenario 是行为式的**（「PR 触发 ⇒ 日志里
  有一行」/「逐句检查」），本仓无法机械验证；建议改写成对交付物内容的断言。
- **N6（中 · 自举）｜本仓自己的 pytest 不是 required check**：`gh api
  …/branches/main/protection/required_status_checks` = `{"contexts":["gate / check"]}`；
  `gh pr checks 17` 显示三条 `test`（`ci.yml`，push + pull_request 各跑一次）**均非 required**。
  ⇒ **本仓可以带着失败的测试合入** —— 这正是 issue #4 描述的形态出现在**本仓自己**身上，
  而 `design.md:1` 的整个立论是「本 change 是接入方的那个洞」。建议：在 `design.md §1` 现状表
  补这一行，并把「把 `test` 勾成 required」写成本 change 的一条人工交付项（勾选本身仍是人工，
  与 CD-2 一致）。
- **N7（低-中 · D5/Q3 的缺口）｜「甲（新 tag）」对存量接入方没有可行升级路径**：
  `init --gate-ref <新 tag>` 在已接入仓上会走 `conflicting_files`（`initcmd.py:265-278`）⇒ exit 1
  （机制同 E1 实测的 `init --policy`）；手改 ref 则落进 B3 的死锁。⇒ 上游 Q3 只写了「改 ref 会撞
  台账：CRQ-1」，没写它的**完整后果**：存量接入方升 tag 的代价是**丢定制 policy**。
  （对推荐方案无影响，但一旦将来选甲，这条必须先答。）

## Code-Resolved

| # | 问题 | 结论（证据） |
|---|---|---|
| CRQ-A | 手改 `init` 产物后，是否**所有**入口都 exit 1、且**无** flag 出口？ | **exit 1 属实、无 flag 出口属实**；但**并非无出口**（实测 E2a/E2b/E2c 三条文件级出口，见 B3）。`--dry-run`（`initcmd.py:181-186` 只在写盘分支生效）、`--policy`、`--gate-ref` 都不是出口：实测 E1 里 `init --dry-run` = **1**、`init --policy` = **1**。环境变量里没有能表达确认的项（`grep os.environ src/witnessloop/` 只命中 `WITNESSLOOP_BASE_REF`/`GITHUB_BASE_REF`/`WITNESSLOOP_HEAD_REF`/guard 的 change 变量/`SKIP_ENV`，均与 init 无关）。 |
| CRQ-B | 直接改台账 JSON 的 hash 字段算不算出口？ | **算一条，但只对 `uninit` 有效**：改 sha 后 `init` 仍 **1**（`initcmd.py:265-278` 比的是磁盘 vs **生成物**），`uninit` 变 **0**（`uninitcmd.py:58-61` 比的是磁盘 vs **台账**）⇒ `uninit → init` 走通（E2c 实测）。 |
| CRQ-C | 「另一个入口能落新文件」吗？ | **不能**（E3 实测）。所有写盘都在 `initcmd.py:188-194`，只被「未接入 + 无冲突 + 非 dry-run」触达；已接入一律先走 `_already_initialized`。 |
| CRQ-D | `@v1` 是否同时钉 gate.yml 与 CLI？若 caller 显式传 `witnessloop-ref` 呢？ | **成立**（`gate.yml:19-23` 默认 `"v1"` + `gate.yml:57-58` 的 uvx + `constants.py:11`）。**反例检验**：显式传 `with: witnessloop-ref:` **能**解耦，但生成的 caller **不传也不能传** —— `caller_workflow()`（`initcmd.py:24-41`）只产出 `uses:`；手加 `with:` 即落入 CRQ-A 的死锁 ⇒ 实际不可用，结论不受影响。 |
| CRQ-E | 三文件契约 / 保护路径 / required 粒度 | 逐条复核**属实**：`docs/gate.md:9`；`tests/test_init.py:18`（函数名）、`:72`（`set(by_path) == {…}`）、`:103`（幂等测试里的三文件枚举）；`.witnessloop/policy.json` 的 `protected_paths`/`require_change_for`（`src/**`,`templates/**`,`plugin/**`）；`gh api` 的 `contexts = ['gate / check']`。`tests/test_init.py:46-55` **只做子串断言** ⇒ tasks B3 的「逐字节」是**新增**测试。 |
| CRQ-F | 本 change 的实际门禁是哪个 CLI？ | **`v1`**（`.github/workflows/witnessloop.yml:14` + `gate.yml:19-23`）。v1 无 `evidence.py`、`REVIEW_MANIFEST_REQUIRED_FIELDS` 不含 `stage`（`constants.py:79-89` 是 main 才加的）⇒ 实测 v1 报 1 条 / main 报 4 条（B1）。 |
| CRQ-G | R17 的前提（本仓台账与磁盘一致）成立吗？ | **成立**：`.witnessloop/init-manifest.json` 两项 sha 与磁盘逐字节一致（`0d1a84f019a9` / `4861a80caf3e`，均 match），`gate_ref` = `…gate.yml@v1`。 |
| CRQ-H | 「uninit 会静默丢定制 policy」属实吗？ | **属实**：实测 E2d —— `init --policy <自定义>` 后 `uninit → init`，policy 里的自定义项计数从 2 变 **0**。机制：`uninitcmd.py:42-62` 把台账里**每一个**条目都列入 `doomed`（含 `policy.json`），`uninitcmd.py:91-95` 逐个删除。 |
| CRQ-I | R16 的断言方向 | **属实**：`gate.yml:57-58` 的 `run:` 里是裸 `${{ inputs.witnessloop-ref }}`，而 `gate.yml:48-50` 同 step 的 `base-ref` 走 `env:` ⇒ 任何「`run:` 里不得出现裸 `${{ }}`」的全量断言在**现状**上直接红。 |
| CRQ-J | tasks C3 / D2 的断言方向 | 见下条「对 C3/D2 的判断」。 |

**对 C3/D2 的判断（任务书点名）**：本 change 的推荐方案是「不碰 `gate.yml`、不改
`caller_workflow()` 的字节」，但**这三件事该用三种不同的东西钉**：
1. **`caller_workflow()` 的逐字节稳定** —— **值得**一条金句（golden literal）测试，理由是 R17：
   生成物是已接入仓的**实际契约**（台账 sha 绑着它），不是普通实现细节。现有
   `tests/test_init.py:46-55` 只有子串断言，钉不住「加了一行头注释」（而 CRQ-2 已经证明
   加一行头注释会让存量仓 `init` 立刻坏）⇒ tasks B3 的「逐字节」应显式写成**新增测试**。
2. **`gate.yml` 不动** —— **不该**加「逐字节不变」的测试。它是会演进的 workflow，
   钉死它等于禁止未来的合法修改；且它与 `tasks.md:47`（D2）的措辞混在一起，容易被实现成
   「给 gate.yml 存一个金句 sha」这种反模式。**正确做法**：D2 改成**回归检查项**
   （「本 change 的 diff 不含 `.github/workflows/gate.yml`」+ 既有 `tests/test_gate_workflow.py` 全绿），
   而不是「断言」。
3. **`check`/`guard` 零改动（`tasks.md:42`）** —— 用既有 `tests/test_guard.py` 全绿 + diff 不含
   `src/witnessloop/{checkcmd,guardcmd,contract,policy}.py` 保证即可。
4. **与残留「甲」分支的关系**：A3/A5（`tasks.md:18-23`）是**条件**任务，与 C3/D2 不构成硬矛盾；
   但 Q1 定案后**必须删掉未选分支**，否则「A5 改 gate.yml」与「D2 gate.yml 逐字节未变」会以
   两条互斥的验收同时留在同一份 tasks 里 —— `tasks.md:6-7` 的头注已预警这一点，
   建议在 `tasks.md:61`（F0）明写「删未选分支」。

## 需要用户裁定

> 均**不阻塞**本轮 verdict（阻塞项是 B1–B4；上面四条即使全按我的建议改，也仍需用户拍板下面这些）。

1. **Q1 的形态（原 Q1）**：己 ／ **己 + B-1 的 ①②③**（我推荐后者）／ 戊-by-flag ／ 甲。
   我的推荐：**己 + ①②③，戊 从推荐里删掉**（理由见 B2；若保留必须是 opt-in flag + 「占位符未替换 ⇒ 红」）。
2. **issue #4 的收口方式（B4 的下游）**：把 #4 保持 open？还是关 #4 并另开一条「机械执行点」issue？
   我的推荐：**后者**（本 change 交付文档/模板，#4 的机械诉求另开一条，`tasks.md:65` 改写）。
3. **本仓自举（N6）**：本 change 是否顺带把 `ci.yml` 的 `test` job 勾成 required？
   我的推荐：**是**（人工一步，写进 tasks）——否则本 change 自己的 PR 可以带着红测试合入。
4. **模板的落地位置（N2）**：`templates/adopter-tests.yml` 直接放 `templates/`？
   还是新建 `templates/github/`（或别处）以免与「host 中立」契约相抵？
5. **模板的分发 ref（N1）**：配方点名 `main`？还是本 change 顺带发一个 tag（这会把 D5 从
   「不进入本 change」重新拉回来，需用户明确同意）？

## 复核记录（可复现）

- 基线：`/tmp/adv-atg` → `uv run pytest -q` = **431 passed**。
- 死锁与出口：`/tmp/e1`（`init`=0 → 手改 → `init`=1 / `uninit`=1 / `init --dry-run`=1 /
  `init --policy`=1 / 删台账后 `init`=1）；`/tmp/e2a`（只恢复字节 → `init`=0）；
  `/tmp/e2b`（删掉被改文件 → `uninit`=0 → `init`=0）；`/tmp/e2c`（改台账 sha → `uninit`=0 → `init`=0）；
  `/tmp/e2d`（`uninit→init` 后自定义 policy 计数 2 → 0）。
- 存量仓可达性：`/tmp/e3`（新仓，SIM 戊 打补丁 → 种子落盘 True）；
  `/tmp/e4`（旧工具 init 过的仓 + SIM 戊 → 「幂等，无改动」exit 0，种子**不**落盘）。
- 门禁差异：`/tmp/v1cli`（`v1` 的独立克隆）+ `/tmp/adv-hist`（带历史），
  在「实现已落地」的 diff 上 v1 = 1 条 / main = 4 条。
- 平台事实：`gh api repos/Xingkai98/witnessloop/branches/main/protection`（`contexts`/`strict`/
  `enforce_admins`/`approving_count`/`codeowners`）、`…/required_status_checks`、`gh pr checks 17`、
  `gh issue view 4`。
- 仓内写入：**仅本文件**。被审 worktree 在本文件创建前 `git status --porcelain` 为空。

## Sources

- `templates/grill.md` §5（本轮的算法与格式出处）、§「怎么取 run id」。
- 被审产物：`proposal.md` / `design.md` / `tasks.md` / `specs/adopter-test-job/spec.md` /
  `reviews/grill-review.md`。
- 平台行为（**未端到端实测**，沿用上游「非官方明文、置信度中高」的标注）：
  `startup_failure`（R8/CD-3）我**没有**独立复核，只标注其**已不适用于推荐方案**。
- branch protection / PR checks / issue #4：`gh` 对真实仓的即时取证（本次重跑）。
