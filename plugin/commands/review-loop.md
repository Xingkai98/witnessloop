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
3. 起一个**另起的 run** 当审阅者，拿它的 id 作 `reviewer_run_id`；作者 run 的 id
   作 `author_run_id`。两者必须不同，否则 `manifest build` 会直接拒写。
4. 按 `templates/review-loop.md` 的步骤 1–5 执行，产出
   `<change-dir>/reviews/<stage>-review.md`。
5. **有界轮数**（默认上限 3 轮）：到顶仍不通过就停下来交人判断，
   不要无限循环、也不要悄悄放宽断言让自己过。
6. 收尾落证据（**内容提交之后、证据提交之前**）：

   ```
   witnessloop manifest build --root . --change <change-id> --stage <stage> \
     --report reviews/<stage>-review.md \
     --reviewer-run-id <审阅者 run> --author-run-id <作者 run> [--base <ref>]
   ```

   然后把报告 + manifest（以及需要的解释事件）**单独一个提交**（`docs/gate.md §3.1`）。
   审阅之后再落任何非证据文件，`witnessloop check` 会判「审阅的是旧 revision」。

## 环境（CC 侧怎么取 run id）

- `WITNESSLOOP_RUN_ID`：**当前 run** 的 id。审阅者与作者是**不同的 run**，各自环境里
  这个值本就应当不同。同一进程要同时给两个角色时，用
  `WITNESSLOOP_REVIEWER_RUN_ID` / `WITNESSLOOP_AUTHOR_RUN_ID`（优先级更高）。
- **不设也行**：`manifest build` 会按模板里那套规则生成一个唯一 id
  （`<stage>-<role>-<utc>-<随机>`），两个角色必然不同。设了才幂等。

## 约束

- **只读**：审阅者不改实现；修复由作者 run 做。
- **无状态**：本命令不创建、不维护自己的状态文件；状态一律以
  `reviews/*.manifest.json` 为准。
- 结论只有 `PASS` / `CHANGES_REQUESTED` 两种，不许模糊。
- 身份字段是自由文本——本工具**防漂移、不防蓄意伪造**，别当成签名。
