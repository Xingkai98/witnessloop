# Tasks: adopter-test-gate（v2 · 机械版）

> 依据 `design.md`（v2，方向反转：用户 2026-10-13 指出「没有存量接入方」这条前提不成立）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/adopter-test-job/spec.md`）。
> ⚠️ **Q1–Q8 未定案前，A/B/C/P 几节的形态不确定**——定案后**必须**先把 `spec.md` 的对应段落替换成定案，
> 并**删掉未选分支**。

## A. `check` 的机械判定（D4，核心增量）

- [x] A1 `constants.py`：命令文件路径（`.github/witnessloop-tests.txt`）+ **哨兵串**（如 `<<REPLACE-ME>>`）
- [x] A2 `policy.py`：`Policy.tests_disabled` —— **缺省 ⇒ 声明**、**`tests.disabled: true` ⇒ 不判**
      ⚠️ 实现期**订正字段名**（对抗轮 Z2）：本行原写 `tests.execution_point`（一个**路径值**旋钮），
      而路径是**常量**（A1）——若允许 policy 指定别的路径，`check` 判 A 文件、`gate.yml` 读 B 文件
      ⇒ 又回到「一边判绿、一边静默跳过」。⇒ `policy.tests.*` 只认 `disabled` 这一个键。
      ⚠️ **两条字面必须钉死**（对抗轮 X2）：① **`default_policy_doc()` 不物化 `tests` 键**
      （否则已接入仓 plain `init` 会 exit 1）；② opt-out 只能写**布尔** **`tests.disabled: true`**
      （`from_doc` 是 `or DEFAULT` ⇒ `""`/`null`/缺省**都会**被读成「声明」⇒ 实现用 `is True`）
      ⚠️ 缺省取「声明」意味着**已接入仓（含本仓自己、`wl-test`）会立刻被判**⇒ 见 P 节的迁移任务
- [x] A3 `checkcmd.py`：新判定——声明了执行点时：**文件不存在 ⇒ 红**、**去空白后为空 ⇒ 红**、
      **含哨兵 ⇒ 红**、否则绿（**零依赖**：文件存在 + 字符串检查，**不解析 YAML**、不执行命令）
      ⚠️ **「去空白后非空」这一条是 grill v2 实测补的**：只判「存在 + 无哨兵」时，**空文件**会让
      `check` 绿 **且** 门禁 `sh -c ""` exit 0 ⇒ 双重绿、零测试（issue #4 的形态 + 一枚绿勾）
- [x] A4 单测（先红）：**四态**（缺失 / **空或纯空白** / 含哨兵 / 已接线）+ 未声明 ⇒ 不判 +
      错误文案点名**路径与原因**
- [x] A5 单测：`check` **不执行**该文件里的命令（R3 边界；用「留下痕迹就会失败」的哨兵命令证明没跑）

## B. `init` 侧（D3/D6）

- [x] B1 `init` 种命令文件（**无 flag 时**）：**不存在才写**、**走独立路径**——⚠️ **不能进 `desired_files()`**
      （带 `--test-command` 时见 B2：**总是覆盖**）
      （否则接入方改过命令后 plain `init` 就 exit 1，实测 `initcmd.py:265-278`）；代价：`--dry-run`
      输出与产物清单要单独加一行（`initcmd.py:181-186`/`:196-198`）
      ⚠️ **不需要改 `uninitcmd.py`**：它只遍历台账条目（`uninitcmd.py:42-60`）⇒ 文件不在台账就天然不会被删
      （改了反而危险：`uninitcmd.py:37` 是 `desired_files(gate_ref)` 的**单参**调用）
- [x] B2 `init --test-command "<cmd>"` ⇒ **总是写入该命令（覆盖）**——⚠️ 对抗轮 X1：原稿与 B1 的
      「不存在才写」冲突，实测「文件已存在 + 给了 flag」会**静默 exit 0「幂等，无改动」**、命令不生效，
      而默认路径（plain `init` 先写哨兵）恰好让文件存在 ⇒ **最常见的接线序列里这个 flag 是坏的**。
      无 flag 时 ⇒ 只在**文件不存在**时写哨兵（未接线 ⇒ `check` 判红，D4）
- [x] B3 `init --no-tests` ⇒ 不写该文件 + 策略里写 **`tests.disabled: true`**（显式 opt-out）
      ⚠️ **不是「置空」**：`from_doc` 用 `or DEFAULT`（falsy 即回落）⇒ `""` / `null` / 缺省**都会**被读成「声明」
      （对抗轮 Y1：本行原写「置空」与 A2/spec 的唯一字面直接相反）
      ⚠️ **已接入仓的 opt-out 摩擦要写进文档**（grill v2 的 CRQ-6）：`--no-tests` 只在**新接入**时可用；
      已接入仓只能改 `.witnessloop/policy.json`，而它是**不变集**且状态是 `M` ⇒ **每次都要写一条解释事件**
- [x] B4 **契约变更进 spec + 改既有断言**：`docs/gate.md:9`「只写三个文件」、
      `tests/test_init.py:18,72,103`（三文件枚举）——新产物是第四个（D6/R7）
- [x] B4b **覆盖分支的对外表现要定死**（对抗轮 Z1）：`--test-command` 在**已接入**仓上覆盖命令文件时，
      `init` 的**输出**不得说「幂等，无改动」（那会与「命令已生效」矛盾）、退出码仍为 0；
      plain `init` 且文件已存在时才是「幂等，无改动」⇒ 两条分支各一条断言
- [x] B5 单测：三态 + **幂等** + **`uninit` 之后命令文件仍在** +
      ⚠️ **回归重点**（D3 的兑现）：**接入方改过命令文件之后，plain `init` 仍 exit 0**（这条不测，D3 就是空话）
- [x] B6 ⚠️ **不许改 `caller_workflow()` 的字节**（否则本仓 init 台账与磁盘不一致，R9）——golden literal 钉住

## C. `gate.yml` 新增测试步骤（D1 甲 / D2）

- [x] C1 新 step：**读命令文件**——⚠️ **文件缺失 _或_ 内容含哨兵 ⇒ 跳过**（原稿只写「缺失 ⇒ 跳过」；
      哨兵会被 `sh` 当命令执行，症状是 `sh: Syntax error` 而不是清晰文案，实测 exit 2）
- [x] C2 **路径**经 `env:` 传、命令**在 `run:` 里运行时读**（grill v2 的 CRQ-10：`${{ }}` 是**解析期**插值
      ⇒ 插值文件内容等于把接入方内容当 workflow 源码）。⚠️ 断言的主语是**文件路径**，不是命令文本
      （spec 原稿那条「命令出现在 `env:` 里」**写不出来**——命令根本不在 workflow 里）
- [x] C3 **失败交互已定案**：测试步骤 `if: ${{ !cancelled() }}`、`check` 步骤排在前。
      ⚠️ 原稿的「`always()` 会掩蔽 check 的失败」**已被实测证伪**（失败步骤 + 后续 `skipped` ⇒ job 结论仍
      `failure`；真掩蔽开关是 `continue-on-error`）⇒ 理由改写为「门禁红时最需要测试反馈」+「取消时不重跑」
- [x] C4 单测：pyyaml 结构化断言（step 存在、**路径**走 `env:`、无文件/哨兵时跳过）+「gate.yml 既有断言全绿」
      ⚠️ **再加一条一致性测试**（对抗轮 X3）：`gate.yml` 里的路径与哨兵字面量 == `constants.py` 的两个常量
      == `policy` 的默认路径（三处同源）；否则会出现「`check` 判红、门禁静默跳过」的口径分裂
- [x] C5 **`gate / check` 这个 job 名不变**（接入方已把它勾成 required ⇒ 改名 = 静默失效）

## P. 发版 / ref（design D7 · **Q6 定案后执行**）

> ⚠️ 本节 id 用 `P*`（publish）而非 `D*`：`design.md` 的决策编号是 `D1..D9`，两个 `D` 含义不同
> 会造成「D3 指哪一条」的歧义（对抗轮 X6）。

- [x] P0 **（第一步）给本仓补执行点**：手工提交 `.github/witnessloop-tests.txt`（内容 `uv run pytest -q`）。
      ⚠️ 本仓的 `init` **今天就坏**（定制 policy 撞出厂默认，实测 exit 1）⇒ 只能手工提交。
      ⚠️ 原稿写「先移 tag ⇒ 本仓合不了任何 PR」——**实测证伪**（这条 PR 自带文件 ⇒ 绿）；
      真实代价只是「**在途** PR 在补文件落地前会红」⇒ 先补是为了**缩小红的窗口**（对抗轮 X4）
- [ ] P1 发 tag `v1.6.0`（含这 6 个提交 + 本 change）
- [ ] P2 把 `v1` **移动**到 `v1.6.0`（⚠️ **改写已发布 ref 的对外动作，执行前需用户在场确认**）
      并**同时改 tag 的 annotated 注记**（现文「当前指向 v1.5.0」会变错）
- [ ] P3 移动后**复核本仓自举**：本仓 PR 的 `gate / check` 开始跑新 CLI（会执行 #13/#16 的新门禁）
      ⇒ 若历史 change 目录因此报红，那说明**门禁真的生效了**，**不要**为了绿而回退 tag
- [ ] P4 文档写明 `wl-test`（唯一存量、可删）的规避法：把它的 caller 钉回 `v1.5.0`
- [x] ~~P5 （Q4）把本仓 `ci.yml` 的 `test` 勾成 required~~ —— **已放弃**（grill v2 的 Q4）：
      执行点已经进了 `gate / check`（它才是 required）⇒ 再勾一次只会让**同一批 pytest 跑两遍**；
      且本仓 `test` 非 required 这件事**不属于本 change 的范围**（另记）

## N. spec 有、tasks 缺的三条（对抗轮 X5）

- [x] N1 **依赖为空**要有测试钉住（`pyproject.toml` 的 `dependencies == []`，或 wheel METADATA 无 `Requires-Dist`）
- [x] N2 **文档守卫**（照 `tests/test_docs.py` 现成范式）：每处「拦住合并/合不了」都带限定（±2 行窗口）；
      文档里不出现「手改 `init` 产物」「先 `uninit` 再 `init`」的教法；README 接入段出现「四条边界」的关键词
- [x] N3 **X7 的文档要求要有落点**：写清「`tests.disabled: true` 只关 `check`，门禁那一步照旧会跑
      （文件在就跑、不在就跳过）」⇒ 归入 F1 的四条边界之外的第五条说明
- [x] N4 **`README.md:66` 那句在移 tag 后会变成假**（grill v2 的 R-v2-7 / X5）：`init --policy` 现在标着
      “尚未随 @v1 发布”，而 P2 移 tag 后它**已发布** ⇒ 一并订正

## E. 回归

- [x] E1 全量 `uv run pytest -q` 绿（记录基线与新增数）
- [x] E2 `init`/`uninit` 既有幂等 / 冲突 / 回滚用例全绿；`docs/gate.md` 的「三文件」表述已改
- [x] E3 `check`/`guard` 的**既有判定**不回归（新判定只加「执行点」一条）

## H. 报告布局（D8 / Q5）

- [x] E2a 把 **v1 的两份报告移出 `reviews/`** → `openspec/changes/adopter-test-gate/history/v1/`
      （`git mv`）。⚠️ 孤儿规则是 `reviews/**/*.md`（**递归**）⇒ 放在 `reviews/` 的子目录里**不算数**；
      且 `evidence.py:192,197,210` 的 `matching[0]` 按**字典序**取 ⇒ 留着会让**被校验正文的是 v1 那份**
- [x] E2b 本轮的 grill 记录落到 `reviews/grill-review.md`（v2 决策记录），`stage=grill` 的 manifest 指向它

## F. 文档（D9）

- [x] F1 `README.md`：接入段（`init --test-command`、命令文件怎么改、**同 job ⇒ 不用新增勾选**）+
      **四条边界**：① 只保证「存在 + 非空 + 已接线」、**不保证真跑了**；② **PR 可以改自己的 CI**；
      ③ 测试命令是**任意代码**、fork PR 也会跑；④ **能力天花板**（`contents: read`、无 services/matrix/
      额外 action、命令只能一行 shell ⇒ 需要这些能力的仓应改用「自己的 workflow」）
- [x] F2 `docs/gate.md`：§1（产物清单）、新增一小节（执行点门禁的语义与边界）
- [x] F3 `templates/review-loop.md`：补一句「测试须由 CI 执行」
- [x] F4 ⚠️ **不改** `openspec/changes/` 下**其他** change 目录的非证据文件（会让其 manifest 判 stale）

## G. 证据链与收尾

- [ ] **G0** 停轮拿到 Q1..Q8 答复 → 定案替换进 `spec.md` → **删未选分支** → 写 `## User Confirmation` →
      `manifest build --stage grill` 放行 `src/**` →（**G0b**）**重跑一轮设计对抗**（定案后）
- [ ] G1（在 build 证据**之后**执行）两段提交 + `manifest build`（grill / grill-adversarial / building）+
      **本地** `check` 绿
- [ ] G2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] G3 PR → 合入（**优先 `--merge`**，见 issue #18）
- [ ] G4 关 issue **#4**（本 change 现在是**机械**的 ⇒ 名正言顺）

## 定案（用户 2026-10-13）

- **Q6 = 做发版**：发 `v1.6.0` + **移动 `v1`**（P1/P2；分步执行；移 tag 是改已发布 ref 的对外动作，
  **执行需用户在场**）。
- **Q1–Q5、Q7、Q8 = 全按推荐**（逐条答复见 `reviews/grill-review.md` 的 `## User Confirmation`）。
- ⇒ 未选分支（乙：独立测试 workflow／丙：命令进 caller 的 `with:`）**不再保留**。

## 明确不做（本 change）

`check` 执行测试 · 命令探测 · 手改 `init` 产物当通道 · 「uninit→init」式升级 · 引入运行时依赖 ·
改本仓 `ci.yml` 的**内容** · 替接入方勾 required（同 job 时不需要） · 给 `gate.yml` 存「逐字节不变」快照断言。

## 实测记录（实现期）

> 实现者填写（2026-10-13）。命令一律 `export PATH=/home/happy/.local/bin:$PATH` + `uv run pytest -q`
> （**不加** `--extra dev`）；**动手前的基线 = 431 passed**（实跑，与任务书一致）。

### 数字

- 全量：**477 passed**（基线 431 ⇒ **新增 46 条**）：新文件 `tests/test_adopter_tests.py` **13**、
  `tests/test_init_tests_command.py` **19**、`tests/test_gate_workflow.py` **+6**、
  `tests/test_docs.py` **+7**、`tests/test_invariants.py` **+1**（13+19+6+7+1 = 46）。
- **既有用例变红 22 条**，全部处置（见下「踩到的坑」#2/#3）——没有一条是「改断言让它绿」。

### 踩到的坑

1. **`--no-tests` 误打「policy 来自 --policy」**（手工 e2e 抓到，单测**没覆盖到**）：那条诊断的判据
   原本是 `policy_doc is not None`，而 `--no-tests` 也会改 policy doc ⇒ 用户没给过 `--policy`
   却被告知 policy 来自文件。改成 `policy_override`（= 真给过 flag），并补一条**先红后绿**的回归
   （`test_no_tests_does_not_claim_the_policy_came_from_a_file`）。
   同族的第二处：`--dry-run --test-command` 在**已接入**仓上收尾会说「其余文件无改动，**未 commit**」
   ——什么都没写、哪来的 commit。改成按「已写 / dry-run 将写 / 没动」三态给收尾语
   （`test_dry_run_on_an_onboarded_repo_writes_nothing_and_says_so`）。两处都是**同一类**缺陷：
   「写给用户的那句话」与「实际发生了什么」不一致，而 B4b 的全部要求就是这条。
2. **`gated` fixture 必须接线**：它原先跑 plain `init`（⇒ 哨兵文件 + 提交），在新判定下 `check`
   全红 ⇒ **12 个文件里 22 条既有用例一起变红**。处置：`conftest.gated` 改走 `--test-command`
   （`WIRED_TEST_COMMAND`），并给「期望 check 绿」的既有用例加 `helpers.init_wired()`。
   **这不是放宽断言**：那些用例考的是别的东西（受保护写入 / 孤儿报告 / stage 覆写 / 往返…），
   哨兵文件是**新契约下的未接线态**，混进去只会掩盖真因。**负例**用例（期望红的）保持 plain `init` 不动。
3. **两条 `uninit` 往返用例按新契约改了断言语义**（**契约变更**，不是放宽）：
   `test_uninit_removes_exactly_what_init_created` 原先断言 `.github/` **整个**消失、
   `test_uninit_round_trip_leaves_repo_clean`（与 `test_acceptance.test_f5`）原先断言工作树回到 init 前。
   命令文件**不进台账** ⇒ `uninit` 不删它 ⇒ 往返**不再逐字节干净**（spec 明写「SHALL 不参与
   `uninit` 的删除」）。改法是把它**钉得更死**：断言「只剩那一个文件」——用
   `git status --porcelain -uall`，否则 git 会把未跟踪目录折叠成 `.github/`（这里踩过一次）；
   另在 `tests/test_init_tests_command.py` 加 `test_tests_file_survives_uninit`。
   ⚠️ **若审阅认为这两处不该改语义，请直接指出**（这是本实现里唯一「改了既有断言含义」的地方）。
4. **`--dry-run` 那一行只列「真会写」的**（N3）：文件已存在时 plain `init` 不动它，所以不列——
   `test_dry_run_does_not_claim_a_file_it_would_not_write` 钉住。
5. **本仓 `init` 的哨兵会先落盘**（本机实测）：`init` 后 `_already_initialized` 才因**定制 policy**
   报冲突 exit 1，而命令文件此时**已写**。这是 Z1/O2 认下的行为（写在前、不因后续冲突回滚、
   当场打印点名那一行 ⇒ 绝不静默），但**本仓自己不会碰到**（P0 是手工提交）。

### 真跑过的（命令 + 结果）

- `uv run pytest -q` ⇒ **477 passed**（基线那次 **431 passed**）。
- **真 CLI 端到端**（`/tmp/e2e/r`，真 git 仓，不是测试进程内）：
  - plain `init` ⇒ 清单含 `+ .github/witnessloop-tests.txt`，内容 `<<REPLACE-ME>>`；
    `check` ⇒ **红**，点名路径 + 「未接线（仍是哨兵）」。
  - 已接入仓 `init --test-command "uv run pytest -q"` ⇒ 「已写入测试执行点…（--test-command 覆盖已有内容）」
    + 「已接入 witnessloop（其余文件无改动，未 commit）」、**不说「幂等」**、exit 0、内容确实被覆盖。
  - 再 plain `init` ⇒ 「幂等，无改动」exit 0；**手工改过命令之后** plain `init` 仍 **exit 0**
    且**不覆盖**（D3 兑现）；随后 `check` ⇒ **通过 ✓**。
  - `init --no-tests` ⇒ 无命令文件 + policy 里 `"tests": {"disabled": true}`；`check` ⇒ **通过 ✓**。
  - `uninit` ⇒ 三个台账产物删净，**命令文件仍在**。
- **门禁那一步的 shell 真跑**（从 `gate.yml` 解析出 `run:` 后交 `sh -c`，四态各一次）：
  缺失 ⇒ exit 0 + `::notice::`；哨兵 ⇒ exit 0 + notice；**空 ⇒ exit 0 且无 notice**
  （⇒ 「空」只能由 `check` 判——这条实测正好证明第三条判据不可省）；已接线 `exit 7` ⇒ **exit 7**
  （失败会顶到 job）；已接线真命令 ⇒ 命令**真的执行了**（空目录里跑 pytest 得 exit 5「no tests ran」）。

### 没验证的（别当成已验证）

- **平台侧**：`gate / check` 的 required 语义、以及「`check` 红 + 测试红」时 job 结论的实际表现——
  沿用 grill 的实测（run `38123102904`）与官方表达式页，**本轮没有再跑真 CI**（要真 PR 才看得到）。
- **本仓自己的新门禁**：P2 移 tag 之前，本仓的 `gate / check` 仍跑 v1.5.0 的旧 `gate.yml`
  ⇒ 新的 `adopter tests` 步骤**没有在本仓 CI 里跑过**（跑过的只是把 `run:` 抽出来在本机 `sh` 里执行）。
- **`wl-test` 的波及**（design R9）——不在本 PR 范围。
- **本地 `check` 全绿**：还差 G1 的 manifest（现有 `grill.manifest.json` 按 R4-W2 已 stale；
  `grill-adversarial` / `building` 两份未建）⇒ 现在跑是 **3 项红，都不是执行点判定**
  （`report_hash` 不匹配 / 审阅的是旧 revision / 孤儿报告）。
