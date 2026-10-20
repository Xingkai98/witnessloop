# gate-ref-pinning（增补）— 包 ref SHALL 按 ref 形态取「可安装且精确」的那个

> 本 change 修改既有能力 `gate-ref-pinning`（change `gate-ref-pins-package` 引入）。
> 冲突时**以本文件为准**：旧文里「包 ref 取 `job.workflow_sha` 优先」「uv 能解析 tag object sha」
> 的结论已被 issue #42 与实测推翻。

## Requirement: 缺省包 ref SHALL 按 ref 形态取「可安装且精确」的那个

调用方**未**显式传 `with: witnessloop-ref:` 且 `job.workflow_repository` 等于
`constants.REPO_SLUG` 时，`gate.yml` SHALL 按下列顺序确定 `uvx` 的包 ref：

1. 从 `job.workflow_ref` 解析 `REF_PART`：用已知前缀
   `<REPO_SLUG>/.github/workflows/gate.yml@` **精确剥离**（ref 名或 workflow 路径里含
   `@` / `@refs/...` 都不会截错）；剥离后只接受 `refs/tags/<非空>` /
   `refs/heads/<非空>` / 40 或 64 位小写 hex，其他形态视为空。
2. 若 `REF_PART` 为 `refs/tags/<非空>` ⇒ SHALL 使用**完整** `REF_PART`
   （如 `refs/tags/v1.7.0`）。**这是 tag 形态的唯一路径**——annotated tag 的
   `job.workflow_sha` 是 tag object，`uv >= 0.13.2` 拒绝。
3. 否则若 `job.workflow_sha` 非空 ⇒ SHALL 使用 `job.workflow_sha`：
   - `REF_PART` 为 `refs/heads/<非空>` 或裸**小写十六进制**（40 / 64 位）⇒ 正常路径
     （分支 / commit pin 的精确 commit），SHALL NOT 打 warning；
   - 其他形态（缺 `@`、`@` 后为空、`refs/pull/*`、大写 hex 等）⇒ 兜底路径，
     SHALL 打 `::warning::` 并附 `job.workflow_ref` 原值。
4. 否则（`job.workflow_sha` 为空）若 `REF_PART` 为 `refs/heads/<非空>` 或裸小写 hex ⇒
   降级使用 `REF_PART`，来源 SHALL 注明 sha 缺失。
5. 全不行 ⇒ SHALL fail-closed 到 `constants.DEFAULT_GATE_REF` 的 ref 部分并打
   `::warning::`；SHALL NOT 静默装默认分支。
6. 无论走哪条路径，最终 ref SHALL NOT 为空**或纯空白**；否则 ⇒ SHALL `::error::` 并
   **非零退出**（不得写出 `ref=`，否则安装步会装默认分支）。

显式 `with: witnessloop-ref:` 非空时 SHALL 仍然最优先；`job.workflow_repository` 不等于
`REPO_SLUG`（含空值）时 SHALL 直接 fail-closed，SHALL NOT 再尝试 `job.workflow_ref`。

### Scenario: annotated tag（issue #42 的根因形态）
- **Given** caller `uses: Xingkai98/witnessloop/.github/workflows/gate.yml@v1.7.0`，
  且 `v1.7.0` 是 annotated tag（tag object `00192abe…`，指向 commit `c9b2811…`）；
  即 `job.workflow_sha=00192abe…`、`job.workflow_ref=…/gate.yml@refs/tags/v1.7.0`
- **When** 门禁解析包 ref
- **Then** SHALL 得到 `refs/tags/v1.7.0`（或可安装的 tag 名），**SHALL NOT** 得到 `00192abe…`
  （tag object sha）；`uv >= 0.13.2` SHALL 能据此安装
  （实测：tag object sha 在 0.13.1 绿 / 0.13.2 与 0.13.3 红；tag ref 在 0.13.3 绿）
- **And** SHALL NOT 打 `::warning::`（这是正常路径）

### Scenario: 分支 pin / commit pin（保留精确 commit）
- **Given** `job.workflow_ref=…@refs/heads/main` 或 `…@<40 位 commit sha>`，
  且 `job.workflow_sha` 非空
- **When** 门禁解析包 ref
- **Then** SHALL 使用 `job.workflow_sha`（分支 / commit pin 的精确 commit），
  SHALL NOT 使用会移动的 `refs/heads/main`（避免包比 workflow 文件晚一个 commit 的 TOCTOU）
- **And** `job.workflow_sha` 为空时，才 SHALL 降级使用 `REF_PART`（`refs/heads/main` / commit）

### Scenario: workflow_ref 不可用 ⇒ sha 兜底
- **Given** `job.workflow_ref` 缺失或畸形，且 `job.workflow_sha` 非空
- **When** 门禁解析包 ref
- **Then** SHALL 使用 `job.workflow_sha`，并 SHALL 打 `::warning::`（附原值）说明这是兜底
  （若该值是 tag object，`uv >= 0.13.2` 会响亮失败——SHALL NOT 静默跑错版本）

### Scenario: 两者都不可用 ⇒ fail-closed
- **Given** `job.workflow_ref` 解析不出、`job.workflow_sha` 为空（或 `job.*` 整体不可用）
- **When** 门禁解析包 ref
- **Then** SHALL 退兜底 ref（与 `constants.DEFAULT_GATE_REF` 的 ref 部分同源；本 change 起
  = `v1.7.1`）并打 `::warning::`；SHALL NOT 输出空 ref（空 ref 会装默认分支）
- **And** 若兜底 ref 本身也配成空串 ⇒ SHALL `::error::` 并非零退出

## Requirement: 解析行为 SHALL 有行为级回归测试

`tests/test_gate_workflow.py` SHALL 把解析 step 的 `run:` 原文交给真 `sh` 执行（不是文本断言），
注入 `WL_INPUT_REF` / `WL_WORKFLOW_SHA` / `WL_WORKFLOW_REF` / `WL_WORKFLOW_REPOSITORY`，
至少覆盖：annotated tag 形态、分支 pin（结果是 sha，不是 `refs/heads/*`）、commit pin
（真实形态 `@<40 位小写 hex>`）、sha 兜底（warning 含原值）、双重不可用 fail-closed、
空兜底 ref / 纯空白输入非零退出、`refs/tags/` / `refs/heads/` 空尾、分支名含 `@`、
tag 名含 `@`、**ref 名里含 `@refs/heads/` / `@refs/tags/`**、**workflow 路径不匹配
已知前缀**（改名）⇒ 响亮兜底、64 位 hex、大写 hex、显式覆盖、跨仓守卫、未定义 env。

### Scenario: 旧实现（sha 优先）会红
- **Given** 同一组 annotated tag 输入
- **When** 用旧的「`job.workflow_sha` 优先」解析脚本执行
- **Then** 测试 SHALL 失败（解析出 tag object sha ≠ `refs/tags/v1.7.0`）；
  开发记录 SHALL 保存该失败输出，证明测试不是同义反复

## Requirement: 实际使用的 ref 与来源 SHALL 在日志里可见

解析 step SHALL 打出 `::notice::`，包含最终 ref 与来源；来源文案 SHALL 区分：
显式传入 / `job.workflow_ref` 的 tag / `job.workflow_sha` 的精确 commit（分支 / commit pin）/
`job.workflow_sha` 兜底 / workflow_ref 降级 / fail-closed。
「job.workflow_sha 兜底」的 `::warning::` SHALL 附上 `job.workflow_ref` 原值。
该 step SHALL 仍是 job 的第一个 step。

## Requirement: 版本与发布

本 change 合入后 SHALL 发布 **annotated `v1.7.1`**（指向含修复的提交），
`constants.DEFAULT_GATE_REF` 与 `gate.yml` 的 `WL_FALLBACK_REF` SHALL 在打 tag 前指向它；
SHALL NOT 移动 `v1` / `v1.7.0`。文档 SHALL 写明「把 caller 钉在 annotated tag 上是受支持形态」。
