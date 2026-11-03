# Design: gate-empty-diff-and-hints（v1）

> 依据 `proposal.md` 与 issue #45 / #46。流程出处 `templates/grill.md` / `templates/review-loop.md`。
> 决策编号 D1..D8；grill / 对抗验证结论见 `reviews/`，停轮后回写本文件末尾。

## 0. 一句话

**零变更 ≠ 通过**：`check` 在空 diff 上默认返回可区分的非零码 `EXIT_EMPTY=5`，
只有显式 `--allow-empty` 才退 0；**revision 不匹配**按 git 拓扑分成「证据是后代」与
「旁支 / 不可达」两支，各给一条可直接执行的补救命令。

## 1. 现状与根因（读代码确认）

- `checkcmd.run` 在 `gitutil.changed_files(base, head)` 返回空列表后**没有分支**：
  `targets = []`、`findings = []`，`_report` 走到 `if not findings: print("check：通过 ✓")`
  ⇒ 退 `EXIT_PASS`。**「无输入」与「输入合格」共用同一个出口。**
- `contract._check_git_span` 只在 `not gitutil.is_ancestor(head_sha, checked_head)` 时
  报一句固定的「不是祖先——审阅的是别的 revision」，**没有反向判定**，也没有从
  `doc`（`stage` / `report_path`）与 context（`base` / change 名）拼出下一条命令。
- `gitutil` 已有所需的全部只读原语：`is_ancestor`、`rev_parse`、`merge_base`。
  ⇒ 本 change **不新增 git 依赖**，只在既有原语上做分支。

## 2. 决策

### D1 零变更在 `changed_files` 之后立即分流，且先于全部契约校验

**判定点**：policy 已加载、base 可解析、`changed_files` 成功返回 `[]` 之后。

**顺序理由**：把分流放在 policy / base 解析之后，保留既有的 fail-closed 语义——
未接入仍是 `EXIT_NOT_ONBOARDED(3)`、base 不可解析仍是 `EXIT_FAIL(1)`；放在契约校验之前，
是因为空 diff 下没有 target、没有受保护写入、没有需要核对的证据，
再跑一遍只会制造「看起来校验过」的假象。

**选择**：`if not changes: return _report_empty(...)`。
**备选**：把它做成一条 `Finding` 走既有失败路径。否决：那会打印「未通过（1 项）」并让
`--allow-empty` 需要「删 finding」，语义拧巴；空 diff 不是「校验失败」，是「没有校验」。

### D2 新退出码 `EXIT_EMPTY = 5`，`--allow-empty` 才放行

- 默认：`EXIT_EMPTY = 5`。
- `--allow-empty`：`EXIT_PASS = 0`。
- 既有码不变：0 通过 / 1 校验失败 / 2 用法 / 3 未接入 / 4 仅 guard 内部错误。

**为什么不是复用 1**：issue #45 明确允许「可区分的退出码」。5 让本地与 CI 日志能区分
「真的校验失败」与「区间为空、什么都没校验」；同时任何 `!= 0` 的 CI 判定仍然失败。
**代价**：硬编码 `== 1` 判失败的脚本需要把 5 也算失败——写进 proposal 的受影响调用方一节。

**为什么 `--allow-empty` 不作用于非空 diff**：flag 的语义是「允许空区间通过」，
不是「放宽一切」。非空 diff 下它被忽略（不改变结果），保持最小惊讶。

### D3 输出语义：不打印「check：通过 ✓」

零变更默认（退 5）：

```
check：基线 <base>...<head>，0 个变更文件，0 个 change 目录
check：无变更，跳过（非通过）✗ —— base 与 head 之间没有任何差异，本次没有校验任何内容
  CI / 脚本若确实预期零变更，显式加 --allow-empty 放行。
```

`--allow-empty`（退 0）：

```
check：基线 <base>...<head>，0 个变更文件，0 个 change 目录
check：无变更；已按 --allow-empty 显式放行（退出码 0）——本次没有校验任何内容。
```

- 保留既有子串 `0 个变更文件` / `0 个 change 目录`（`tests/test_check_contract.py` 等
  既有断言依赖它们）。
- **不再出现**成功行 `check：通过 ✓`。注意「非通过」里含「通过」二字——既有测试若用
  `"通过" not in out` 会误伤；新测试一律钉**精确成功行** `check：通过 ✓` 的缺席。
- 默认失败信息走 **stderr**（与既有失败一致），基线行走 stdout；`--allow-empty` 的
  放行信息走 stdout（它是成功出口）。

### D4 revision 不匹配的分支判据：单向祖先判定

`_check_git_span` 已在 `head_sha` 不是 `checked_head` 的祖先时进入失败分支。再判一次：

```
evidence_is_descendant = gitutil.is_ancestor(root, scope.checked_head, head_sha)
```

- `True` ⇒ **(a) 证据是被检 revision 的后代**（被检 revision 在证据的历史里）。
- `False` ⇒ **(b) 旁支 / 不可达**（两向都不是祖先）。

**为什么不用 `merge_base`**：两向 `is_ancestor` 已足够区分且语义直白；`merge_base` 在
无关历史上返回 None，但「有 merge-base 却不是祖先」同样是旁支，没必要引入第三种状态。
**注意**：进入该分支时 `head_sha != checked_head`（相等会先被判为祖先），所以不存在
「相等」的第 0 种情况。

### D5 (a) 后代分支的提示：改用包含它的区间

```
… 不是本次被检 revision <checked> 的祖先——审阅的是别的 revision。
  ⚠️ 证据 revision 是被检 revision 的**后代**：它产生在更晚的历史上，当前区间不包含它。
  若本次应检查到交付 HEAD，改用包含它的区间重跑：
    witnessloop check --base <base_ref> --head HEAD
  若 HEAD 仍早于该证据，直接检查到证据 revision：
    witnessloop check --base <base_ref> --head <head_sha>
```

`base_ref` 取本次 `check` 实际使用的 base（`args.base` 解析后的值，缺省时是
`gitutil.resolve_base` 的结果）——**不猜主干名**。这满足 issue #46 的
「`--base <seed> --head HEAD`」示例，并额外给出「HEAD 仍早于证据」时的精确命令。

### D6 (b) 旁支分支的提示：在交付 revision 上重跑 manifest build

```
… 不是本次被检 revision <checked> 的祖先——审阅的是别的 revision。
  ⚠️ 它也不在被检 revision 的后代链上（旁支 / 不可达）：证据产自另一条历史，
     不能证明本次交付。
  处置：在交付 revision（<checked>）上重新跑该阶段审阅，并重建 manifest：
    witnessloop manifest build --change <change> --stage <stage> --report <report_path> --base <base_ref>
  然后用同一条区间复核：
    witnessloop check --base <base_ref> --head HEAD
```

`<change>` / `<stage>` / `<report_path>` 来自**当前这份 manifest 所在目录**：
`change` 用目录名（归档态也用归档目录名，`manifest build` 能精确解析），
`stage` / `report_path` 取 `doc` 的字段（缺字段/非字符串时退回 `<change>` / `<stage>` /
`<report_path>` 占位，仍保持模板形态）。**不从 `--report` 反推、不改写证据。**

### D7 不做的事（避免自伤 / 越权）

- **不**在失败分支里调用 `manifest build`：`check` 仍是只读动词。
- **不**自动改 `head_sha`：那正是「手改 manifest 骗过检查」。
- **不**把 descendant/side 分支做成新的 finding 条数：仍是一条 finding（既有测试与
  下游解析按「一条 manifest 一条」计数），只是**消息更可操作**。
- **不**影响「审阅的是旧 revision」（ancestor-but-stale）分支：那是第三种既有情形，
  与 issue #46 无关，文案保持不动。

### D8 测试与文档

- TDD：先落测试并跑红（`EXIT_EMPTY` 不存在 / 提示缺失），再实现。
- 单测覆盖：
  - 零变更默认：`code == EXIT_EMPTY`、`check：通过 ✓` 不在 stdout、无放行文案。
  - `--allow-empty`：`code == EXIT_PASS`、输出含 `--allow-empty` 与「显式放行」、
    **仍不**含 `check：通过 ✓`。
  - 非空 diff + `--allow-empty`：结果与不带 flag 相同（flag 只在空区间生效）。
  - descendant：真实 git 场景（内容提交 C1 → 更晚内容 C2 → 证据绑定 C2 → `--head C1`），
    断言「后代」+ 两条命令模板。
  - side：真实旁支场景（manifest `head_sha` 指向 main 上的无关提交），断言「旁支 / 不可达」
    + `manifest build --change … --stage … --report …` + `witnessloop check --base …`。
  - 既有 `test_head_sha_must_be_an_ancestor_of_the_checked_head` 仍绿（保留「祖先」子串）。
- 文档：`docs/gate.md` §3（revision 绑定失败提示）与 §6（退出码表加 5）；
  `README.md` 的 `check` 用法补 `--allow-empty` 一行与零变更语义。

## 3. 风险与缓解

| 风险 | 缓解 |
|---|---|
| **CI 误伤**：某接入方在空 diff 上跑 check（如 push 事件、手动 workflow）现在会红 | 刻意行为；proposal 列出受影响调用方；需要放行时显式 `--allow-empty` |
| **退出码 5 不被识别**：脚本硬编码 `== 1` 判失败 | 文档写清「`!= 0` 才是失败」；`EXIT_EMPTY` 与 `EXIT_FAIL` 不同值并有单测 |
| **提示里的 base_ref 不是用户想要的 seed** | 用**本次实际** base ref，不自作主张猜主干；后代分支额外给 `--head <证据 sha>` |
| **descendant 判定在浅克隆 / 无关历史下的行为** | 仍是既有 `is_ancestor` 语义：非祖先即进入错误分支，再按反向祖先分成两支；不新增网络/历史依赖 |
| **「非通过」含「通过」子串** | 新测试钉**精确成功行** `check：通过 ✓` 缺席；既有测试 `"通过" not in out` 只用于真失败场景（不会走到零变更分支） |
| **多 change 同 PR 时提示里的 change id** | 用**该 manifest 所在目录名**（`rel_change` 末段），不是共享 scope 的任意 id |

## 4. Pre-Implementation Review

- grill（`reviews/grill-design.md`）：frontier 已空，无 Open Question；确认 D1..D8 的
  代码位置与测试策略。
- 对抗验证（`reviews/grill-adversarial.md`）：R1 开批 7 条（3 medium 已修 / 1 medium
  已修 / 3 low，其中 2 条登记不修）→ R2 验证无 medium+ ⇒ **PASS**。
- 必须修改已回写：
  - 分流位置固定在 `changed_files` 之后（保留 3 / 1 的 fail-closed）；
  - 新测试钉精确成功行，不查 `"通过"` 子串；
  - 既有 4 条「零 diff 下断言通过」的测试改为带真实非空 diff；
  - 后代提示同时给 `--head HEAD` 与 `--head <证据 sha>`；
  - 提示中的可写字段经 `shlex.quote`。
- ⚠️ 流程偏差（如实记录）：`design.md` 在写代码前定稿，但 grill / 对抗验证报告文本产出在
  实现与测试跑绿之后；未在报告产出前伪造任何 manifest / gate 结论。人工把关由 Hermes
  事后复审。

## 5. 验收

见 `tasks.md` 与 `proposal.md`「验收」。
