---
description: 独立审阅闭环——零记忆审阅者审实现，不通过就修并补回归测试，有界轮数，收尾落 manifest
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
5. 按 `templates/review-loop.md` 的步骤 1–6 执行，产出
   `<change-dir>/reviews/<stage>-review.md`。verdict 是**三态**：
   - `PASS` → 走收尾；
   - `CHANGES_REQUESTED` → 逐条修、每条补回归测试、在 `tasks.md` 追加
     「审阅修复」节、**提交修复**，然后再审；
   - `BLOCKED` → **停下、向用户报告阻塞项、不自行修复**（阻塞性缺陷是设计或范围的
     问题，不是顺手补一下的事）。
6. **有界轮数**（默认上限 3 轮）：到顶仍不通过就停下来交人判断，
   不要无限循环、也不要悄悄放宽断言让自己过。
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
  唯一 id（`<stage>-<role>-<utc>-<随机>`），两个角色必然不同。
- `WITNESSLOOP_TEMPLATES_DIR`：覆盖模板目录。默认
  `${CLAUDE_PLUGIN_ROOT}/../templates`——把 `plugin/` 单独拷走、脱离本仓时，
  用它把模板位置指回去。

## 约束

- **只读**：审阅者不改实现；修复由作者 run 做。
- **无状态**：本命令不创建、不维护自己的状态文件；状态一律以
  `reviews/*.manifest.json` 为准。
- 结论是**三态**：`PASS` / `CHANGES_REQUESTED` / `BLOCKED`，不许模糊；
  `BLOCKED` 时本命令只负责停下来把阻塞项讲清楚，**不自行修复**。
- **批次 aware**：`tasks.md` 里标「后续批」的未勾项不是缺陷，别据此打回。
- `CHANGES_REQUESTED` 的修复要同步更新 change 文档（`tasks.md` 追加「审阅修复」节）并提交。
- 身份字段是自由文本——本工具**防漂移、不防蓄意伪造**，别当成签名。
