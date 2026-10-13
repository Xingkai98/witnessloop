# Tasks: adopter-test-gate（v2 · 机械版）

> 依据 `design.md`（v2，方向反转：用户 2026-10-13 指出「没有存量接入方」这条前提不成立）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/adopter-test-job/spec.md`）。
> ⚠️ **Q1–Q4 未定案前，B/C/D 三节的形态不确定**——定案后**必须**先把 `spec.md` 的对应段落替换成定案，
> 并**删掉未选分支**。

## A. `check` 的机械判定（D4，核心增量）

- [ ] A1 `constants.py`：命令文件路径（`.github/witnessloop-tests.txt`）+ **哨兵串**（如 `<<REPLACE-ME>>`）
- [ ] A2 `policy.py`：`tests.execution_point`（默认 = 命令文件路径；**显式空 ⇒ 不判**，供 `--no-tests`）
- [ ] A3 `checkcmd.py`：新判定——声明了执行点时：**文件不存在 ⇒ 红**、**含哨兵 ⇒ 红**、否则绿
      （**零依赖**：只做文件存在 + 字符串包含检查，**不解析 YAML**、不执行命令）
- [ ] A4 单测（先红）：三态（缺失 / 含哨兵 / 已接线）+ 未声明 ⇒ 不判 + 错误文案点名**路径与原因**
- [ ] A5 单测：`check` **不执行**该文件里的命令（R3 边界；用「留下痕迹就会失败」的哨兵命令证明没跑）

## B. `init` 侧（D3/D6）

- [ ] B1 `init` 种命令文件：**不存在才写**、**不进 hash 台账**、**不参与 `uninit` 删除**（D3 的语义）
- [ ] B2 `init --test-command "<cmd>"` ⇒ 写入该命令；无参 ⇒ 写**哨兵**（未接线 ⇒ `check` 判红，D4）
- [ ] B3 `init --no-tests` ⇒ 不写该文件 + `tests.execution_point` 置空（显式 opt-out）
- [ ] B4 **契约变更进 spec + 改既有断言**：`docs/gate.md:9`「只写三个文件」、
      `tests/test_init.py:18,72,103`（三文件枚举）——新产物是第四个（D6/R7）
- [ ] B5 单测：三态 + **幂等**（重复 `init` 不覆盖接入方改过的命令文件）+ 冲突语义不变 +
      `uninit` 之后命令文件**仍在**（它是接入方的）
- [ ] B6 ⚠️ **不许改 `caller_workflow()` 的字节**（否则本仓 init 台账与磁盘不一致，R9）——golden literal 钉住

## C. `gate.yml` 新增测试步骤（D1 甲 / D2）

- [ ] C1 新 step：**读命令文件**（存在 ⇒ 读出内容；不存在 ⇒ 跳过）
- [ ] C2 命令**经 `env:`** 传给 `run:`（**不**裸内联 `${{ }}`；断言**限定到本 step**——
      现有 `gate.yml:57-58` 本身就有裸 `${{ }}`）
- [ ] C3 **失败交互钉死**（R2）：`check` 排在前 + 测试步骤 `if: always()`（或反之）——**二选一写进 spec 并给理由**
- [ ] C4 单测：pyyaml 结构化断言（step 存在、命令走 `env:`、无文件时跳过）+「gate.yml 既有断言全绿」
- [ ] C5 **`gate / check` 这个 job 名不变**（接入方已把它勾成 required ⇒ 改名 = 静默失效）

## D. 发版 / ref（D5 · **Q3 定案后执行**）

- [ ] D1 发 tag `v1.6.0`（含这 6 个提交 + 本 change）
- [ ] D2 把 `v1` **移动**到 `v1.6.0`（⚠️ **改写已发布 ref 的对外动作，执行前需用户在场确认**）
- [ ] D3 移动后**复核本仓自举**：本仓 PR 的 `gate / check` 开始跑新 CLI（会执行 #13/#16 的新门禁）
      ⇒ 若历史 change 目录因此报红，那说明**门禁真的生效了**，**不要**为了绿而回退 tag
- [ ] D4 文档写明 `wl-test`（唯一存量、可删）的规避法：把它的 caller 钉回 `v1.5.0`
- [ ] D5 （Q4 定案）把**本仓自己的** `ci.yml` `test` job 勾成 required（**人工一步**）

## E. 回归

- [ ] E1 全量 `uv run pytest -q` 绿（记录基线与新增数）
- [ ] E2 `init`/`uninit` 既有幂等 / 冲突 / 回滚用例全绿；`docs/gate.md` 的「三文件」表述已改
- [ ] E3 `check`/`guard` 的**既有判定**不回归（新判定只加「执行点」一条）

## F. 文档（D7）

- [ ] F1 `README.md`：接入段（`init --test-command`、命令文件怎么改、**同 job ⇒ 不用新增勾选**）+
      **三条告警**（fork PR 会跑你的命令 / **PR 可以改自己的 CI** / **`check` 只保证「存在且已接线」**）
- [ ] F2 `docs/gate.md`：§1（产物清单）、新增一小节（执行点门禁的语义与边界）
- [ ] F3 `templates/review-loop.md`：补一句「测试须由 CI 执行」
- [ ] F4 ⚠️ **不改** `openspec/changes/` 下**其他** change 目录的非证据文件（会让其 manifest 判 stale）

## G. 证据链与收尾

- [ ] **G0** 停轮拿到 Q1..Q4 答复 → 定案替换进 `spec.md` → **删未选分支** → 写 `## User Confirmation` →
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
