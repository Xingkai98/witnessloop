# Tasks: adopter-test-gate

> 依据 `design.md`（草稿——grill + 对抗验证收敛 + Q1..Q5 确认前不得写实现代码）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/adopter-test-job/spec.md`）。
> ⚠️ **Q1（步骤住哪）/ Q3（ref 策略）未定案前，A/B 两节的形态不确定**——定案后**必须**先把
> `spec.md` 的对应段落替换成定案（spec 是 manifest 哈希绑定的 artifact，事后改会让 `spec_hash` stale）。

## A. `gate.yml` 的测试步骤（D1 / D2 定案 / D7）

- [ ] A1 新增 `workflow_call.inputs.test-command`（`required: false`、`default: ""`）
- [ ] A2 按 **Q1 定案**放测试步骤：甲=新 `test` job；乙=并入既有 `check` job 的后续 step
- [ ] A3 命令**经 `env:` 传入**、**不**裸内联进 `run:`（D7；防脚本注入写法，依 GitHub 官方建议）
- [ ] A4 空命令 ⇒ **跳过**（不是失败）——既有接入方与无测试仓行为不变（D4）
- [ ] A5 单测（先红，`tests/test_gate_workflow.py` 同款 **pyyaml 结构化**断言，不 grep 子串）：
      1. input 已声明且 `default == ""`
      2. 有命令时会执行（断言 `env:` + `run:` 的具体形态与位置）
      3. 空命令时**不执行**（`if:` 条件，或 step 不存在——依定案钉死其中一种）
      4. 命令**不**以裸 `${{ }}` 出现在 `run:` 里（D7）

## B. `init` 侧接线（D3 定案 / D5 定案）

- [ ] B1 `initcmd.caller_workflow()`：按定案产出 `with:`（D3 乙/丙 = 命令住 caller）
- [ ] B2 `init --test-command "<cmd>"`（若 Q2 选丙）：缺省时不写该 input（或写显式空值，**二者择一钉死**）
- [ ] B3 若 Q3 选**甲**：`constants.DEFAULT_GATE_REF` 指向新 tag + `README.md` 安装/接入示例同步
      ⚠️ 必须在**同一** change 内完成，否则新接入方一 `init` 就坏（`workflow_call` 未声明 input 报错，R1）
- [ ] B4 若 Q3 选**乙**：`v1` 改移动 major tag 的**发布纪律**写进文档（`DEFAULT_GATE_REF` 不动）
- [ ] B5 单测：caller 含/不含 `with:` 的两种形态；既有幂等 / 冲突 / `uninit` 回滚用例全绿
      （⚠️ 改了 `caller_workflow()` 的字节 ⇒ 台账 hash 变 ⇒ **存量已接入仓跑 `init` 会报冲突**，
      这条**必须**写进文档并有用例钉住该行为是 fail-closed 的）

## C. 回归

- [ ] C1 全量 `uv run pytest -q` 绿（记录基线与新增数）
- [ ] C2 本仓自举**不受影响**（D6）：`.github/workflows/witnessloop.yml` 仍引 `@v1`；
      写一条注释或断言把「本 change 的 gate.yml 改动不影响本仓 PR 检查」钉住（避免误读）
- [ ] C3 `guard` / `check` 行为**零改动**（本 change 不碰 CLI 判定路径）

## D. 文档（D8）

- [ ] D1 `README.md`：接入段补「测试命令怎么给」「**空 = 跳过**」「required 是**人工勾一次**（job 粒度）」
- [ ] D2 `docs/gate.md`：§1（caller 多了 `with:`）+ 新增一小节（测试 job 的语义与边界）
- [ ] D3 `docs/design.md §5.1`：caller 契约由「极薄」扩成「**极薄 + 可选 `test-command`**」
- [ ] D4 `README.md`：**R4 告警**（Q5）——测试命令是**任意代码**，会在每个 PR（含 **fork PR**）执行
- [ ] D5 ⚠️ **不改** `openspec/changes/` 下**其他** change 目录的非证据文件（会让其 manifest 判 stale）

## E. 证据链与收尾

- [ ] **E0** 停轮拿到 Q1..Q5 答复 → 把定案替换进 `spec.md` + 写 `## User Confirmation` →
      `manifest build --stage grill` 放行 `src/**` →（**E0b**）**重跑一轮设计对抗**（Q5 的处置）
- [ ] E1（在 build 证据**之后**执行）两段提交 + `manifest build`（grill / grill-adversarial / building）+ `check` 绿
- [ ] E2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] E3（在 `check` 绿**之后**执行）PR（branch protection）→ 合入 → 关 issue **#4**
      ⚠️ **本框刻意留空**：PR/合入是证据提交之后的事，回填会让 `tasks_hash` stale。
      **合入方式**：见 issue #18（squash 会切断 manifest 的祖先链 ⇒ 优先 `--merge`）。

## 明确不做（本 change）

不让 `check` 跑测试（保持它「只判流程证据」）· 测试命令**探测** · 改本仓自己的 `ci.yml` ·
引入运行时依赖 · 替接入方决定 fork PR 策略（只写文档告警）。

## 实测记录（实现期）

（待填）
