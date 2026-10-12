# Tasks: adopter-test-gate

> 依据 `design.md`（**已按 grill 回写**：原稿的 5 处事实被证伪、3 个设计树节点补齐，见 design §7）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/adopter-test-job/spec.md`）。
> ⚠️ **Q1 定案前，A/B 两节的形态不确定**（己=模板+文档／戊=模板+种子／甲=`gate.yml` 加 input）——
> 定案后**必须**先把 `spec.md` 的对应段落替换成定案（spec 是 manifest 哈希绑定的 artifact）。

## A. 交付物本体（依 Q1 定案）

- [ ] A1 **己（推荐·主）**：新增 `templates/adopter-tests.yml`——一份可直接复制的测试 workflow 模板：
      - 命令经 **`env:`** 传入（D7；**不**裸内联进 `run:`）
      - **空命令 ⇒ 打印 `::notice::`（「未声明测试命令，只跑了流程校验」）**；非空 ⇒ **回显实际执行的命令**
        （D4/Q7：把「静默」变成「看得见的静默」）
      - 文件头注释写明：**这是你的文件**，随便改；**不要**去手改 `witnessloop init` 写的 caller（那是死锁，见 B2）
- [ ] A2 **戊（推荐·辅，若用户选）**：`init` **种一次**该文件（不存在才写、**不进台账**、不参与冲突与 `uninit` 删除）
      ⇒ 需同时改「只写三个文件」契约（`docs/gate.md:9`、`tests/test_init.py:18,72,103`）+ spec delta 显式记这条（R15）
- [ ] A3 **甲（备选，若用户选）**：`gate.yml` 新增 `workflow_call.inputs.test-command`（`required: false`、`default: ""`）
      + 测试步骤；**必须同时**：① 台账记 `test_command`（照 `gate_ref` 的 recall 先例，`initcmd.py:131-141,:163`）
      ② 定 D5（**新 tag**，不是移动 `v1`）③ 按 D2 钉死**失败交互**（`check` 失败时测试跑不跑、要不要 `if: always()`）
- [ ] A4 单测（先红）：模板/workflow 用 **pyyaml 结构化断言**（先例与理由见 `tests/test_gate_workflow.py:32-34`）——
      空命令路径出现 `::notice::`、非空路径回显命令、命令在 `env:` 里（**断言限定到新增内容**，见 R16）
- [ ] A5 单测（仅甲）：`gate.yml` 的 input 声明 / 空则跳过 / 台账 `test_command` 的 recall 行为

## B. 存量接入方可达性（**R11：原稿完全没走到这个节点**）

- [ ] B1 把「**存量接入方怎么拿到执行点**」写成**显式交付物**（README 配方：拷模板 → 改一行 → 勾 required）
- [ ] B2 文档**必须**写清两条死锁事实（实测）：
      ① 手改 `init` 产物 ⇒ `init` 与 `uninit` **同时** exit 1，且**删台账也不管用**（「只增不改，拒绝覆盖」）；
      ② **不要**建议「先 `uninit` 再 `init`」——`uninit` 会删掉台账里的**每一个**条目（含 `policy.json`），
      会**静默丢定制 policy**（本仓自己就是受害者）
- [ ] B3 校验顺序：**本 change 不改 `caller_workflow()` 的字节**（否则本仓自己的 init 台账与磁盘不一致，R17）——
      用断言钉住（`DEFAULT_GATE_REF` 不变 + caller 生成物逐字节不变）
- [ ] B4 若 Q1 选**戊**：钉「种子只写一次、不进台账、不参与 `uninit`」（含「已存在则不覆盖」）

## C. 边界与告警（D9 / Q5 / Q7）

- [ ] C1 `README.md` 写**两条告警**：① 测试命令是**任意代码**，会在每个 PR（含 **fork PR**）执行；
      ② **PR 可以改自己的 CI**（`.github/workflows/**` 不在保护路径、`required_approving_review_count: 0`）
      ⇒ 本能力的承诺**限定为**「在本次 PR 未修改自己 CI 配置的前提下」（否则就是**过度承诺**）
- [ ] C2 可选加固写进文档（不强制）：把 `.github/workflows/**` 纳入 `CODEOWNERS`
- [ ] C3 `check` / `guard` **零改动**（本 change 不碰 CLI 判定路径；既有 `tests/test_guard.py` 全绿）

## D. 回归

- [ ] D1 全量 `uv run pytest -q` 绿（记录基线与新增数）
- [ ] D2 本仓自举：`gate.yml` **逐字节未变** + `.github/workflows/witnessloop.yml` 仍引 `@v1`
      （⚠️ 若最终选甲/乙，这条要按新语义改写——见 design D6/CRQ-12）
- [ ] D3 `templates/review-loop.md`：补一句「测试须由 CI 执行（见 `templates/adopter-tests.yml`）」
      ——**本 change 的立项理由之一**，不改它这条冲突就还在（design D8）

## E. 文档

- [ ] E1 `README.md`：接入段补「测试执行点怎么拿」「**空 = 跳过 + 可见信号**」「required 是**人工勾一次**（job 粒度）」
- [ ] E2 `docs/gate.md`：§1（若选戊 ⇒ 三文件契约变更）、§7（能力边界补 D9）、新增一小节（本能力的语义与边界）
- [ ] E3 `docs/design.md`：§5.1 的 caller 契约（若选甲才需要改；己/戊 不改契约）
- [ ] E4 ⚠️ **不改** `openspec/changes/` 下**其他** change 目录的非证据文件（会让其 manifest 判 stale）

## F. 证据链与收尾

- [ ] **F0** 停轮拿到 Q1..Q8 答复 → 把定案替换进 `spec.md` + 写 `## User Confirmation` →
      `manifest build --stage grill` 放行 `src/**` →（**F0b**）**重跑一轮设计对抗**（Q5 处置）
- [ ] F1（在 build 证据**之后**执行）两段提交 + `manifest build`（grill / grill-adversarial / building）+ `check` 绿
- [ ] F2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] F3（在 `check` 绿**之后**执行）PR → 合入 → 关 issue **#4**
      ⚠️ **本框刻意留空**（回填会让 `tasks_hash` stale）；**合入方式优先 `--merge`**（见 issue #18：squash 会切断 ancestor 链）

## 明确不做（本 change）

让 `check` 跑测试 · 测试命令**探测** · 手改 `init` 产物（死锁）· 「uninit→init」式升级（会丢 policy）·
改本仓 `ci.yml` · 引入运行时依赖 · 替接入方勾 required · **顺手移动 `v1` tag**（R12：会连带升级 CLI 并静默送达行为变更）。

## 实测记录（实现期）

（待填）
