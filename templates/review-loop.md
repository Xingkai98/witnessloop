# 模板：review-loop（独立审阅闭环）

> **host 中立模板。** 这里只有算法与 prompt 文本，不含任何 host 专有语法。
> 各 host 的适配器负责把它接到自己的命令入口（去哪找适配器由该 host 的发行方式决定，
> 本文件不指向任何具体目录）。
> **适配器不得复制本正文**——只引用本文件路径，物理分离是为了日后能换 host。

## 目的

实现完成后，由**独立零记忆**的审阅者审一遍；不通过就修，修完再审——
**有界轮数封顶**，避免「永远在修」和「自评通过」。

## 参与者

- **作者 run**：写实现、写 change 的那个 run。
- **审阅者 run**：**必须另起**。强制 `reviewer_run_id != author_run_id`
  （挡「忘了另开 run」，不挡蓄意伪造）。

## 输入

- `<change-dir>/tasks.md` 与 `design.md`（声称要做什么、怎么做）
- 实际的代码改动（本次 PR 的 diff）
- `<change-dir>/reviews/` 下已有的证据

## 步骤

1. **审阅**：审阅者零记忆地读 `tasks.md` / `design.md` 与 diff，判断：
   声称做的事是否真的做了、有没有做多余的事、tests 是否真的覆盖了改动、
   有没有偷偷放宽口径（例如把断言改弱以让测试变绿）。
2. **给结论**（二选一，不许模糊）：
   - `PASS`：证据齐、实现与 tasks/design 一致、没有未解释的偏离。
   - `CHANGES_REQUESTED`：逐条列出**具体**问题——文件与行、为什么是问题、
     期望变成什么样。笼统的「建议优化」不算 CHANGES_REQUESTED。
3. **修复**：作者按条目修，并且**每个修复都要补一条能变红的回归测试**：
   先让它红（证明它真的在测那个问题），再改实现让它绿。
   改不动、或认为审阅意见不对——说出来并给出理由，别默默忽略。
4. **再审**：回到第 1 步。轮数**封顶**（默认 3 轮）：到顶仍不通过就**停下来交人判断**，
   不得无限循环，也不得在第 N 轮悄悄放水。
5. **收尾**：
   - 写报告 `<change-dir>/reviews/<stage>-review.md`：结论（PASS /
     CHANGES_REQUESTED）、轮次、每条问题的处置、未决项。
   - 跑 `witnessloop manifest build` 产出 manifest：
     ```
     witnessloop manifest build \
       --root . --change <change-id> --stage <stage> \
       --report reviews/<stage>-review.md \
       --reviewer-run-id <审阅者 run> --author-run-id <作者 run> [--base <ref>]
     ```
   - **先内容提交、后证据提交**（`docs/gate.md §3.1`）：内容一个提交，
     报告 + manifest + 解释事件单独一个提交。审阅之后再落任何非证据文件，
     `check` 会判「审阅的是旧 revision」。

## 产物

- `<change-dir>/reviews/<stage>-review.md`（报告）
- `<change-dir>/reviews/<stage>.manifest.json`（manifest，由 `manifest build` 产出）

## 硬约束

- `reviewer_run_id != author_run_id`；审阅者必须独立于作者。
- **manifest 是权威证据**：审阅结论以它为准，报告与它成对。
- 审阅者对 change 状态**只读**，**不得持有自己的状态文件**。
- 本工具**防漂移、不防蓄意伪造**：`reviewer_run_id` 是自由文本，别当成签名。
