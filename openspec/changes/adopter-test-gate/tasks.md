# Tasks: adopter-test-gate（v2 · 机械版）

> 依据 `design.md`（v2，方向反转：用户 2026-10-13 指出「没有存量接入方」这条前提不成立）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/adopter-test-job/spec.md`）。
> ⚠️ **Q1–Q8 未定案前，A/B/C/D 四节的形态不确定**——定案后**必须**先把 `spec.md` 的对应段落替换成定案，
> 并**删掉未选分支**。

## A. `check` 的机械判定（D4，核心增量）

- [ ] A1 `constants.py`：命令文件路径（`.github/witnessloop-tests.txt`）+ **哨兵串**（如 `<<REPLACE-ME>>`）
- [ ] A2 `policy.py`：`tests.execution_point` —— **三态**（与 `require_change_for`/`policy.py:94-95` 同形）：
      **字段缺省 ⇒ 声明（用出厂默认路径）**、显式空 ⇒ 不判（供 `--no-tests`）。
      ⚠️ 缺省取「声明」意味着**已接入仓（含本仓自己、`wl-test`）会立刻被判**⇒ 见 D 节的迁移任务
- [ ] A3 `checkcmd.py`：新判定——声明了执行点时：**文件不存在 ⇒ 红**、**去空白后为空 ⇒ 红**、
      **含哨兵 ⇒ 红**、否则绿（**零依赖**：文件存在 + 字符串检查，**不解析 YAML**、不执行命令）
      ⚠️ **「去空白后非空」这一条是 grill v2 实测补的**：只判「存在 + 无哨兵」时，**空文件**会让
      `check` 绿 **且** 门禁 `sh -c ""` exit 0 ⇒ 双重绿、零测试（issue #4 的形态 + 一枚绿勾）
- [ ] A4 单测（先红）：**四态**（缺失 / **空或纯空白** / 含哨兵 / 已接线）+ 未声明 ⇒ 不判 +
      错误文案点名**路径与原因**
- [ ] A5 单测：`check` **不执行**该文件里的命令（R3 边界；用「留下痕迹就会失败」的哨兵命令证明没跑）

## B. `init` 侧（D3/D6）

- [ ] B1 `init` 种命令文件：**不存在才写**、**走独立路径**——⚠️ **不能进 `desired_files()`**
      （否则接入方改过命令后 plain `init` 就 exit 1，实测 `initcmd.py:265-278`）；代价：`--dry-run`
      输出与产物清单要单独加一行（`initcmd.py:181-186`/`:196-198`）
      ⚠️ **不需要改 `uninitcmd.py`**：它只遍历台账条目（`uninitcmd.py:42-60`）⇒ 文件不在台账就天然不会被删
      （改了反而危险：`uninitcmd.py:37` 是 `desired_files(gate_ref)` 的**单参**调用）
- [ ] B2 `init --test-command "<cmd>"` ⇒ 写入该命令；无参 ⇒ 写**哨兵**（未接线 ⇒ `check` 判红，D4）
- [ ] B3 `init --no-tests` ⇒ 不写该文件 + `tests.execution_point` 置空（显式 opt-out）
      ⚠️ **已接入仓的 opt-out 摩擦要写进文档**（grill v2 的 CRQ-6）：`--no-tests` 只在**新接入**时可用；
      已接入仓只能改 `.witnessloop/policy.json`，而它是**不变集**且状态是 `M` ⇒ **每次都要写一条解释事件**
- [ ] B4 **契约变更进 spec + 改既有断言**：`docs/gate.md:9`「只写三个文件」、
      `tests/test_init.py:18,72,103`（三文件枚举）——新产物是第四个（D6/R7）
- [ ] B5 单测：三态 + **幂等** + **`uninit` 之后命令文件仍在** +
      ⚠️ **回归重点**（D3 的兑现）：**接入方改过命令文件之后，plain `init` 仍 exit 0**（这条不测，D3 就是空话）
- [ ] B6 ⚠️ **不许改 `caller_workflow()` 的字节**（否则本仓 init 台账与磁盘不一致，R9）——golden literal 钉住

## C. `gate.yml` 新增测试步骤（D1 甲 / D2）

- [ ] C1 新 step：**读命令文件**——⚠️ **文件缺失 _或_ 内容含哨兵 ⇒ 跳过**（原稿只写「缺失 ⇒ 跳过」；
      哨兵会被 `sh` 当命令执行，症状是 `sh: Syntax error` 而不是清晰文案，实测 exit 2）
- [ ] C2 **路径**经 `env:` 传、命令**在 `run:` 里运行时读**（grill v2 的 CRQ-10：`${{ }}` 是**解析期**插值
      ⇒ 插值文件内容等于把接入方内容当 workflow 源码）。⚠️ 断言的主语是**文件路径**，不是命令文本
      （spec 原稿那条「命令出现在 `env:` 里」**写不出来**——命令根本不在 workflow 里）
- [ ] C3 **失败交互已定案**：测试步骤 `if: ${{ !cancelled() }}`、`check` 步骤排在前。
      ⚠️ 原稿的「`always()` 会掩蔽 check 的失败」**已被实测证伪**（失败步骤 + 后续 `skipped` ⇒ job 结论仍
      `failure`；真掩蔽开关是 `continue-on-error`）⇒ 理由改写为「门禁红时最需要测试反馈」+「取消时不重跑」
- [ ] C4 单测：pyyaml 结构化断言（step 存在、命令走 `env:`、无文件时跳过）+「gate.yml 既有断言全绿」
- [ ] C5 **`gate / check` 这个 job 名不变**（接入方已把它勾成 required ⇒ 改名 = 静默失效）

## D. 发版 / ref（D7 · **Q6 定案后执行**）

- [ ] D0 **（排在移 tag 之前，D6/Q4）给本仓补执行点**：手工提交 `.github/witnessloop-tests.txt`
      （内容 `uv run pytest -q`）。⚠️ 本仓的 `init` **今天就坏**（定制 policy 撞出厂默认，实测 exit 1）
      ⇒ 只能手工提交；而它本身也要过 required check ⇒ **先移 tag 会有一个「本仓合不了任何 PR」的窗口**
- [ ] D1 发 tag `v1.6.0`（含这 6 个提交 + 本 change）
- [ ] D2 把 `v1` **移动**到 `v1.6.0`（⚠️ **改写已发布 ref 的对外动作，执行前需用户在场确认**）
      并**同时改 tag 的 annotated 注记**（现文「当前指向 v1.5.0」会变错）
- [ ] D3 移动后**复核本仓自举**：本仓 PR 的 `gate / check` 开始跑新 CLI（会执行 #13/#16 的新门禁）
      ⇒ 若历史 change 目录因此报红，那说明**门禁真的生效了**，**不要**为了绿而回退 tag
- [ ] D4 文档写明 `wl-test`（唯一存量、可删）的规避法：把它的 caller 钉回 `v1.5.0`
- [x] ~~D5 （Q4）把本仓 `ci.yml` 的 `test` 勾成 required~~ —— **已放弃**（grill v2 的 Q4）：
      执行点已经进了 `gate / check`（它才是 required）⇒ 再勾一次只会让**同一批 pytest 跑两遍**；
      且本仓 `test` 非 required 这件事**不属于本 change 的范围**（另记）

## E. 回归

- [ ] E1 全量 `uv run pytest -q` 绿（记录基线与新增数）
- [ ] E2 `init`/`uninit` 既有幂等 / 冲突 / 回滚用例全绿；`docs/gate.md` 的「三文件」表述已改
- [ ] E3 `check`/`guard` 的**既有判定**不回归（新判定只加「执行点」一条）

## H. 报告布局（D8 / Q5）

- [ ] E2a 把 **v1 的两份报告移出 `reviews/`** → `openspec/changes/adopter-test-gate/history/v1/`
      （`git mv`）。⚠️ 孤儿规则是 `reviews/**/*.md`（**递归**）⇒ 放在 `reviews/` 的子目录里**不算数**；
      且 `evidence.py:192,197,210` 的 `matching[0]` 按**字典序**取 ⇒ 留着会让**被校验正文的是 v1 那份**
- [ ] E2b 本轮的 grill 记录落到 `reviews/grill-review.md`（v2 决策记录），`stage=grill` 的 manifest 指向它

## F. 文档（D9）

- [ ] F1 `README.md`：接入段（`init --test-command`、命令文件怎么改、**同 job ⇒ 不用新增勾选**）+
      **四条边界**：① 只保证「存在 + 非空 + 已接线」、**不保证真跑了**；② **PR 可以改自己的 CI**；
      ③ 测试命令是**任意代码**、fork PR 也会跑；④ **能力天花板**（`contents: read`、无 services/matrix/
      额外 action、命令只能一行 shell ⇒ 需要这些能力的仓应改用「自己的 workflow」）
- [ ] F2 `docs/gate.md`：§1（产物清单）、新增一小节（执行点门禁的语义与边界）
- [ ] F3 `templates/review-loop.md`：补一句「测试须由 CI 执行」
- [ ] F4 ⚠️ **不改** `openspec/changes/` 下**其他** change 目录的非证据文件（会让其 manifest 判 stale）

## G. 证据链与收尾

- [ ] **G0** 停轮拿到 Q1..Q8 答复 → 定案替换进 `spec.md` → **删未选分支** → 写 `## User Confirmation` →
      `manifest build --stage grill` 放行 `src/**` →（**G0b**）**重跑一轮设计对抗**（定案后）
- [ ] G1（在 build 证据**之后**执行）两段提交 + `manifest build`（grill / grill-adversarial / building）+
      **本地** `check` 绿
- [ ] G2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] G3 PR → 合入（**优先 `--merge`**，见 issue #18）
- [ ] G4 关 issue **#4**（本 change 现在是**机械**的 ⇒ 名正言顺）

## 明确不做（本 change）

`check` 执行测试 · 命令探测 · 手改 `init` 产物当通道 · 「uninit→init」式升级 · 引入运行时依赖 ·
改本仓 `ci.yml` 的**内容** · 替接入方勾 required（同 job 时不需要） · 给 `gate.yml` 存「逐字节不变」快照断言。

## 实测记录（实现期）

（待填）
