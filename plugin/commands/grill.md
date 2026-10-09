---
description: 设计对抗式追问——独立审阅者对 design 逐轮追问，产出决策记录，停轮等你确认
---

# /grill <change-id>

**本适配器只做接线。** 算法与 prompt 文本在
`${CLAUDE_PLUGIN_ROOT}/../templates/grill.md`（仓库里即 `templates/grill.md`）。
**不要凭记忆复述那套流程**——先读它，再按它执行；本文件不重复它的正文。

## 接线步骤

1. 取 `change-id`（参数缺省时问用户；不要猜）。
2. 定位 change 目录：`<changes_root>/<change-id>/`，`changes_root` 读
   `.witnessloop/policy.json`（缺省 `openspec/changes`）。
3. 起一个**另起的 run** 当审阅者（作者 run 与审阅者 run 必须不同）。审阅者零记忆：
   不读作者的会话历史、不共享上下文，只读 change 目录里的文本。
4. 按 `templates/grill.md` 的步骤 1–5 执行，产出
   `<change-dir>/reviews/grill-review.md`。
5. **停轮**：把 `## Open Questions` 逐条交给用户确认后再往下走。
   `## User Confirmation` 没写齐之前，**不要开始实现**。
6. 收尾落证据（内容提交之后、证据提交之前）：

   ```
   witnessloop manifest build --root . --change <change-id> --stage grill \
     --report reviews/grill-review.md \
     --reviewer-run-id <审阅者 run> --author-run-id <作者 run> [--base <ref>]
   ```

   然后把报告 + manifest **单独一个提交**（`docs/gate.md §3.1`）。

## 环境（CC 侧怎么取 run id / 模板）

- `WITNESSLOOP_RUN_ID`：**当前 run** 的 id。把它设成你这个会话的 id；审阅者是另起的
  run，它自己环境里该有**不同**的值。同一进程要同时给两个角色时，用
  `WITNESSLOOP_REVIEWER_RUN_ID` / `WITNESSLOOP_AUTHOR_RUN_ID`（优先级更高）。
- **不设也行**：`manifest build` 会按 `templates/grill.md` 里那套规则生成一个唯一
  id，两个角色必然不同。设了才幂等（同一个 id 重建出同一份 manifest）。
- `WITNESSLOOP_TEMPLATES_DIR`：覆盖模板目录。默认
  `${CLAUDE_PLUGIN_ROOT}/../templates`——把 `plugin/` 单独拷走、脱离本仓时，
  用它把模板位置指回去。

## 约束

- **只读**：不改 change 目录以外的任何东西。
- **无状态**：本命令不创建、不维护自己的状态文件；change 的状态一律以
  `reviews/*.manifest.json` 为准。别把结论只留在会话里。
- 审阅者 ≠ 作者；身份字段是自由文本——本工具**防漂移、不防蓄意伪造**。
