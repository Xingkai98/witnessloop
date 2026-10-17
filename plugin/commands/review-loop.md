---
description: 独立审阅闭环——零记忆审阅者按批次模型审实现，最多 20 轮，超限 BLOCKED + 建议重开设计，收尾落 manifest
---

# /review-loop <change-id> [stage]

**本适配器只做接线。** 算法与 prompt 文本在
`${CLAUDE_PLUGIN_ROOT}/../templates/review-loop.md`（仓库里即 `templates/review-loop.md`）。
**不要凭记忆复述那套流程**——先读它，再按它执行；本文件不重复它的正文。

## 接线步骤

1. 取 `change-id` 与 `stage`（默认 `building`）。
2. 定位 change 目录：`<changes_root>/<change-id>/`，`changes_root` 读
   `.witnessloop/policy.json`（缺省 `openspec/changes`）。
3. **先把审阅基线钉死**：确定主干 ref、`git merge-base` 得到的 base。
   分支若落后主干，先 rebase 再审——否则审的是一个不存在的差异。
4. 起一个**另起的 run** 当审阅者，拿它的 id 作 `reviewer_run_id`；作者 run 的 id
   作 `author_run_id`。两者必须不同，否则 `manifest build` 会直接拒写。
   审阅者零记忆，并要求它**逐项验证 `tasks.md` 的每个 `[x]`**（读代码确认真实存在），
   且**对「后续批」的 `[ ]` 不报缺陷**。
5. 按 `templates/review-loop.md` 的**步骤 1–8**执行，产出
   `<change-dir>/reviews/<stage>-review.md`。**轮 = 一个非空 medium+ 批次的闭环**：
   - **开批**：只列 medium+；空批 ⇒ `PASS`；批次冻结（含 severity）；
   - **全修**：逐条修 + 回归测试（先红后绿）；
   - **只做修复验证**：验证期新问题只进 `deferred`（下一批），不得当场提；
     未修好 ⇒ 同轮继续，不另计轮；
   - **收口**：全部验证通过 ⇒ 本轮结束；下一次开批再判断 `PASS` / 下一轮。
   verdict 三态值仍在，但**出口只有三种**：`PASS` / `BLOCKED` + 成因 /
   超上限 `BLOCKED` + 建议重开设计；`CHANGES_REQUESTED` 是轮内状态，不是出口。
6. **20 轮上限**：只有非空 medium+ 批次算轮（按 change/环累计）；第 20 轮自身达到验证重试
   终止点，或第 20 轮收口后的收口确认仍有 medium+ ⇒ **超上限 `BLOCKED` + 建议推倒重开
   （revise the design）**，不是「到轮数就停」。`BLOCKED` 时停下、向用户报告、不自行修复。
7. 收尾落证据（**内容提交之后、证据提交之前**）：

   ```
   witnessloop manifest build --root . --change <change-id> --stage <stage> \
     --report reviews/<stage>-review.md \
     --reviewer-run-id <审阅者 run> --author-run-id <作者 run> [--base <ref>]
   ```

   然后把报告 + manifest（以及需要的解释事件）**单独一个提交**（`docs/gate.md §3.1`）。
   审阅之后再落任何非证据文件，`witnessloop check` 会判「审阅的是旧 revision」。

## 环境（CC 侧怎么取 run id / 模板）

- `WITNESSLOOP_RUN_ID`：**当前 run** 的 id。审阅者与作者是**不同的 run**，各自环境里
  这个值本就应当不同。同一进程要同时给两个角色时，用
  `WITNESSLOOP_REVIEWER_RUN_ID` / `WITNESSLOOP_AUTHOR_RUN_ID`（优先级更高）。
- **不设也行**：`manifest build` 会按 `templates/review-loop.md` 里那套规则生成一个
  **确定性**兜底 id（`<stage>-<role>-<anchor>`，`anchor` = change id + `head` 短摘要 **≥12 位**），
  两个角色必然不同、同输入同 id（**固定 base 与 revision 时**重复 build 幂等）。
  它是**「审阅目标的指纹」、不代表真实 run 身份**；`manifest build` 会把实际采用的 id 打进输出。
  **要 pin 真身份**，用**角色专用**变量 `WITNESSLOOP_REVIEWER_RUN_ID` /
  `WITNESSLOOP_AUTHOR_RUN_ID` **分别设**；只设共享的 `WITNESSLOOP_RUN_ID` 会被 `build` 拒写；
  兜底路径下无需任何 export。
- `WITNESSLOOP_TEMPLATES_DIR`：覆盖模板目录。默认
  `${CLAUDE_PLUGIN_ROOT}/../templates`——把 `plugin/` 单独拷走、脱离本仓时，
  用它把模板位置指回去。

## 约束

- **只读**：审阅者不改实现；修复由作者 run 做。
- **无状态**：本命令不创建、不维护自己的状态文件；状态一律以
  `reviews/*.manifest.json` 为准。
- **出口只有三种**：`PASS` / `BLOCKED` + 成因 / 超上限 `BLOCKED` + 建议重开；
  三态值仍在，但 `CHANGES_REQUESTED` 只是轮内状态，不是出口；
  `BLOCKED` 时本命令只负责停下来把阻塞项讲清楚，**不自行修复**。
- **批次冻结（含 severity）**；验证期新问题只进 `deferred`；medium+ 全修；
  low/nit 登记不修须逐条写理由。
- **批次 aware**：`tasks.md` 里标「后续批」的未勾项不是缺陷，别据此打回。
- `CHANGES_REQUESTED` 的修复要同步更新 change 文档（`tasks.md` 追加「审阅修复」节）并提交。
- 身份字段是自由文本——本工具**防漂移、不防蓄意伪造**，别当成签名。
