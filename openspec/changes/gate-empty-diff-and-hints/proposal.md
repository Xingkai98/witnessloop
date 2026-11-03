# Proposal: gate-empty-diff-and-hints（零变更不再假绿；revision 不匹配给出可操作提示）

> 关联 issue：witnessloop **#45**、**#46**。
> 一句话：`check` 在**零变更区间**上 SHALL NOT 再打印「通过」——默认按「无操作（非通过）」
> 非零退出，只有显式 `--allow-empty` 才放行；证据 revision 与被检 revision 不可比时，
> SHALL 区分「证据是后代」与「旁支 / 不可达」两种情形，并给出可直接执行的补救命令。

## 背景（实测）

### #45：零变更 = 静默假绿

在本仓 `main` 上执行：

```
$ witnessloop check --base HEAD --head HEAD
check：本包来源（自报，尽力而为）：requested_revision=<未知>，commit_id=<未知>
check：基线 HEAD...HEAD，0 个变更文件，0 个 change 目录
check：通过 ✓
$ echo $?
0
```

`changed_files(base, head)` 为空时，现有实现照常走完校验：没有 target、没有 finding，
于是 `_report` 打印「通过 ✓」并退 0。**「没有任何东西被校验」被当成了「校验通过」**——
CI 里把 `check` 配成 required 时，一个误配的 base/head（或 checkout 到了错误 revision）
会得到一个绿勾，而不是一条响亮的失败。

### #46：revision 不匹配只报「祖先」，不告诉人怎么办

manifest 的 `head_sha` 不是本次被检 head 的祖先时，当前只报：

```
head_sha=… 不是本次被检 revision … 的祖先——审阅的是别的 revision
```

两种**成因完全不同**的情形共用这一句话：

1. **证据 revision 是被检 revision 的后代**——证据产生在更晚的 revision 上，
   当前区间看不到它。多半是 `--head` 指了一个较旧的 revision；改用包含它的区间即可。
2. **旁支 / 不可达**——证据产自另一条历史（例如在错误的分支上 build、rebase 后旧提交
   已不在交付链上）。唯一正确的补救是**在交付 revision 上重跑**该阶段审阅并重建 manifest。

现状要求使用者自己从 sha 推 git 拓扑，再自己拼 `manifest build` 命令；错误信息没有
可操作性。

## 目标

1. **零变更默认非零退出**：`check` 的 diff 为空时 SHALL 打印明确的**无操作**语义
   （如「无变更，跳过（非通过）」），SHALL NOT 打印「check：通过 ✓」。
   默认退出码 SHALL 非 0；使用**可区分的** `EXIT_EMPTY = 5`，避免与「真校验失败」的 1 混淆。
2. **显式放行**：新增 `--allow-empty`。只有带该 flag 时零变更才退 0，且输出 SHALL 写明
   「已按 `--allow-empty` 显式放行」，并说明本次没有校验任何内容。
3. **两种 revision 不匹配分支**：
   - (a) 证据 revision 是被检 revision 的**后代** ⇒ 提示改用包含它的区间
     （`witnessloop check --base <seed> --head HEAD`；若 HEAD 仍早于证据，则
     `--head <证据 sha>`）。
   - (b) **旁支 / 不可达** ⇒ 提示在交付 revision 上重跑 `manifest build`。
   - 两种情形都 SHALL 附一条**可用的检查命令模板**（带本次实际的 base ref）。
4. **回归测试**：先写会红的测试，锁住零变更的退出码 / 输出语义、`--allow-empty` 的放行文案、
   以及两种 revision 不匹配分支的提示内容。
5. **文档同步**：`docs/gate.md` §3 / §6、`README.md` 的 `check` 说明与退出码表。

## 非目标

- **不**改变「有变更时」的任何校验语义与退出码（0 通过 / 1 未通过 / 3 未接入）。
- **不**试图判断证据 revision 与交付 revision 的**内容**是否等价（例如 cherry-pick 后的
  等价补丁）——仍按 git 拓扑判定，与既有规则一致。
- **不**自动重跑 manifest build、不自动改写证据。
- **不**把 `--allow-empty` 扩散到 `guard` / `manifest` 等其它动词。
- **不**碰 `/home/shared/code/infra-learn-board` 或任何接入方仓。

## 行为变更 / 受影响调用方（向后兼容性）

**默认零变更即红是刻意的行为变更**：`check` 从「空 diff 退 0」变为「空 diff 退 5」。

- `.github/workflows/gate.yml`：只在 PR 上跑，base...head 非空时行为不变；**空 diff 的 PR
  现在会被拦**（符合意图）。该 workflow 不检查具体退出码，任何非 0 都失败。
- 本地 / 脚本里的 `witnessloop check`：若依赖「空 diff 退 0」做幂等判断，需显式加
  `--allow-empty`。
- `guard` / `manifest` 不受影响。
- 退出码 5 是**新增**的：只判断 `!= 0` 的调用方不受影响；硬编码 `== 1` 判失败的调用方
  需要把 5 也当作失败（或改用 `!= 0`）。

## 验收

- `tests/test_check_empty_diff.py`：零变更默认退 `EXIT_EMPTY`、无「check：通过 ✓」；
  `--allow-empty` 退 0 且输出含显式放行文案。
- `tests/test_revision_mismatch_hints.py`：构造「证据是后代」与「旁支」两个真实 git 场景，
  断言两种提示分别出现，且都含可执行的命令模板。
- `uv run pytest -q`（或 `.venv/bin/python -m pytest -q`）全绿。
- `witnessloop check --base origin/main --head HEAD` 在本 PR 上绿（证据：原始输出）。
- 三份 stage manifest（grill / grill-adversarial / building）绑定最终 revision。
- PR 正文写 `fixes #45, fixes #46`；**不自行合并 main**。
