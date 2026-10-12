# guard-exit-codes — 本地守卫的退出码不得把「崩溃」误判成「拦住」

> 本 change 的能力增量：让 `guard` 的「拦」退出码**只由「拦」自己产生**——已知的读失败在源头
> 归一成 verdict（不崩溃），真正未预期的异常走 fail-open（非 1）；宿主 shim 的映射对版本偏斜免疫。

## Requirement: 守卫的内部错误不得被当成拦截

`witnessloop guard` SHALL 在 **`cli.main` 的 `guard` 分派路径内**（含该分支的 lazy import 与 `guardcmd.run`
的执行过程）出现**未预期异常**时**不**以「拦」的退出码结束——即内部错误 SHALL 以**非 1**的退出码返回
（fail-open 放行），并在标准错误输出一行诊断。

「拦」的退出码 SHALL 保持为 **1**，且在该分派路径内 SHALL **只**由「命中 `require_change_for` 且当前
change 的 grill 证据不完备」这一显式判定产生。内部错误的退出码 SHALL 由一个与「拦」（1）**不同**的常量定义。

**已知边界（不在本要求内）**：`witnessloop.cli` **自身**的模块级 import 失败（安装破损）不被覆盖——
该情形下所有动词一起不可用，属声明边界，不是本守卫可兜的分派路径。

### Scenario: 任意内部异常都不拦
- **Given** `guardcmd.run` 在判定过程中抛出未预期异常（如 `RuntimeError`）
- **When** 运行 `guard`
- **Then** 退出码**不是 1**（实现为 `EXIT_INTERNAL`），且打印诊断

### Scenario: 崩溃兜底覆盖子模块 import 缺口
- **Given** `witnessloop.guardcmd` 模块**导入失败**（`ImportError`，如 `sys.modules[...]` 被置 None）
- **When** 运行 `witnessloop guard`
- **Then** 退出码**不是 1**（走同一个兜底），而不是让 CPython 以 1 退出被宿主当成「拦」

### Scenario: 「拦」仍是 1（回归）
- **Given** 写目标命中 `require_change_for` 且当前 change 的 grill 证据不完备
- **When** 运行 `guard`
- **Then** 退出码仍为 **1**

## Requirement: 证据文件解码失败必须归一为 verdict

`guard` 可达的**证据读点**在遇到无法按 UTF-8 解码的内容时 SHALL **不抛未捕获异常**，而 SHALL 归一为
一个确定性的结论：

- `.witnessloop/policy.json` 解码失败 ⇒ SHALL 归一为 `PolicyError` ⇒ `guard` **放行**（与「policy 非法」同归）；
- `review manifest` 解码失败 ⇒ SHALL 与「manifest 缺失 / JSON 语法坏」**同归**（`guard` **拦**、`check` **红**）；
  `check` 侧的 finding SHALL 点名该文件（`guard` 侧沿用既有文案、不额外点名文件）；
- grill 报告正文解码失败 ⇒ SHALL 产出一条可诊断的 finding ⇒ **拦**（采用「读不出 ⇒ 不可核验 ⇒ 不完备」的统一口径）。

### Scenario: 报告无法解码不得被当崩溃
- **Given** 当前 change 的 `stage=grill` manifest 绑定了一份**非法 UTF-8** 的报告
- **When** 运行 `guard --path src/x.py`（命中 `require_change_for`）
- **Then** 退出码与 stderr 是一条**确定性结论**（非崩溃、非 `EXIT_INTERNAL`），且不出现 traceback

### Scenario: 字节坏与 JSON 坏的同级失败同归
- **Given** 一个 `review manifest` 被写成非法字节（而非非法 JSON）
- **When** 运行 `guard`
- **Then** 结论与「manifest 是非法 JSON」**一致**（拦 + 点名该文件），不得一半拦一半放

### Scenario: policy 解码失败放行
- **Given** `.witnessloop/policy.json` 是非法 UTF-8
- **When** 运行 `guard`
- **Then** 放行（退出码 `EXIT_PASS`）

## Requirement: 宿主 shim 只把「拦」映射成 block

随 plugin 分发的 `guard.sh` SHALL 仅把 `guard` 的 **1** 映射成宿主的 block 约定（CC 的 2），
其余一切退出码（含内部错误码、用法错误 2、未接入 3、二进制缺失 127）SHALL 一律放行。

该映射 SHALL 对 **shim 与 CLI 版本偏斜**保持安全：旧 shim（只认 1）配新 CLI 时，「拦」仍映射正确、
内部错误仍放行。

### Scenario: 内部错误码被放行
- **Given** `witnessloop guard` 以内部错误码退出
- **When** 宿主 shim 处理该事件
- **Then** shim 以 0 退出（**不** block）

### Scenario: 「拦」仍映射为 block（回归）
- **Given** `witnessloop guard` 以 1 退出
- **When** 宿主 shim 处理该事件
- **Then** shim 退出 2（宿主的 block）

## Requirement: 崩溃兜底不改变 `check` 的退出码语义

本能力 SHALL **只**改 `check` 的**报错路径**（读点归一：崩溃 ⇒ 干净的 finding），SHALL **不**改变其
退出码语义——`check` 遭遇无法解码的证据时 SHALL 仍以「未通过」的退出码结束（CI 锚保持 fail-closed）。

### Scenario: check 在无法解码的报告上仍 fail-closed
- **Given** 一个 change 的 `stage=grill` manifest 绑定了一份非法 UTF-8 报告
- **When** 运行 `check`
- **Then** 它**不**以 0 结束（仍是「未通过」）
