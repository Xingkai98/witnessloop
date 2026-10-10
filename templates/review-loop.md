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

## 审阅维度

1. **任务逐项验证**：逐条对照 `tasks.md`，每个 `[x]` 都要**读代码**确认实现**真实存在**
   ——不是看文件名、不是看 import、不是信 `[x]` 本身。
2. **正确性**：逻辑对不对，边界条件处理了没有。
3. **Spec 对齐**：实现是否完全覆盖 spec / tasks 的要求。
4. **冗余度**：有没有引入与既有工具重复的代码。
5. **测试覆盖**：关键路径有没有测试，修复有没有配回归测试。
6. **安全性**：注入、越权、信息泄露。
7. **可维护性**：代码清晰、模块合理、命名一致。
8. **CI 完整性**：有没有偷偷弱化 CI 配置（删步骤、放宽断言、`continue-on-error`）。

## 执行步骤

### 1. 定位 change

确定 `change-id` 与 change 目录。参数缺省时从上下文或当前分支推断。
change 若已归档（`<changes_root>/archive/…`），仍可在其实现分支上审。

### 2. 确定审阅基线

在审阅前先把基线钉死：

```
git fetch origin <主干>            # 尽力而为
git log <主干>..HEAD --oneline     # 确认要审的提交范围
git merge-base HEAD <主干>         # base，manifest 用
```

若分支**落后主干**（diff 里出现「删除已合入代码」这类假象），先
`git rebase <主干>` 并解决冲突，**再审**——否则审的是个不存在的差异。

### 3. 起零记忆审阅者（第 N 轮）

**另起一个 run**，零记忆、不继承开发上下文。交给它：

- change 目录的绝对路径 + `change-id`；
- 审阅对象：`git diff <base>...HEAD` + change 文档；
- 上面 8 个**审阅维度**；
- **任务逐项验证**：对照 `tasks.md` 每个 `[x]` 读代码确认真实存在；
- **批次 aware**：`tasks.md` 里标了「后续批」的 `[ ]` **不算缺陷**，
  别据此打 CHANGES_REQUESTED（只验证本批的 `[x]`）；
- **verdict 判定规则**（见下）；
- 跑相关测试并把结果写进报告；
- 产出报告 `<change-dir>/reviews/<stage>-review.md`，含 Verdict / Tasks
  Verification / Issues / Test Results / 结论。

**verdict 三态**（不许模糊）：

| verdict | 含义 |
|---|---|
| `PASS` | 所有 `[x]` 有真实实现，无未解决的中等以上问题，测试通过 |
| `CHANGES_REQUESTED` | 有需修复的问题，但不阻塞整体 |
| `BLOCKED` | **阻塞性缺陷**：核心功能缺失 / 安全漏洞 / 测试大面积失败 |

### 4. 判定并闭环

- `PASS` → 跳到第 6 步。
- `CHANGES_REQUESTED` → 进第 5 步。
- `BLOCKED` → **停下，向用户报告阻塞项，等指示；不自行修复**。
  阻塞性缺陷不是「作者顺手补一下」的事——它是设计或范围出了问题。

### 5. 修复并再审（**轮数封顶**，默认 3 轮）

- 逐条修复审阅报告的问题，每条都给出**具体**处置：文件与行、为什么是问题、
  改成什么样。笼统的「已优化」不算处置。
- **每个修复都要补一条能变红的回归测试**：先让它红（证明它真的在测那个问题），
  再改实现让它绿。
- **同步更新 change 文档**：在 `tasks.md` 追加一节「审阅修复」，注明每条问题与
  对应修复（审阅报告引用的行号就是修复的目标）。
- 跑相关测试确认全绿，**提交修复**。
- 回到第 3 步再审（第 N+1 轮）。

**封顶**：到第 3 轮仍 `CHANGES_REQUESTED`，**停下**向用户报告剩余阻塞项，
升级到人判断——不得无限循环，也不得在第 N 轮悄悄放水。

### 6. 收尾

- 报告已在上一步写好：`<change-dir>/reviews/<stage>-review.md`
  （结论、轮次、每条问题的处置、未决项）。
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

## 怎么取 run id

`reviewer_run_id` 与 `author_run_id` 是身份字段（自由文本，**防漂移不防伪造**）。
各 host 的适配器按**同一套**规则取值，别各自发明：

1. **环境优先**：读 `WITNESSLOOP_RUN_ID`（当前 run 的 id）。审阅者与作者是**不同的
   run**，各自的环境里这个值本就应当不同。同一进程里要同时给两个角色时，用角色
   专用变量（优先级更高）：`WITNESSLOOP_REVIEWER_RUN_ID` / `WITNESSLOOP_AUTHOR_RUN_ID`。
2. **取不到就生成**一个唯一 id，形态 `<stage>-<role>-<UTC 时间戳>-<短随机>`。
   把 `role` 编进 id，是为了让生成路径下两个角色**必然不同**。
3. **两者必须不同**：`manifest build` 对相等直接拒——那正是「忘了另开 run」的症状。
   只设共享的 `WITNESSLOOP_RUN_ID` 会让两个角色拿到同一个值、被门禁拦下，这不是 bug。

## 产物

- `<change-dir>/reviews/<stage>-review.md`（报告）
- `<change-dir>/reviews/<stage>.manifest.json`（manifest，由 `manifest build` 产出）
- `tasks.md` 的「审阅修复」节（`CHANGES_REQUESTED` 时）

## 硬约束

- `reviewer_run_id != author_run_id`；审阅者必须独立于作者。
- **verdict 三态**：`BLOCKED` 时停下报告、**不自行修复**。
- **批次 aware**：`tasks.md` 标「后续批」的 `[ ]` 不是缺陷。
- **manifest 是权威证据**：审阅结论以它为准，报告与它成对。
- 审阅者对 change 状态**只读**，**不得持有自己的状态文件**。
- 本工具**防漂移、不防蓄意伪造**：`reviewer_run_id` 是自由文本，别当成签名。
