# guard-exit-codes — 本地守卫的退出码不得把「崩溃」误判成「拦住」

> 本 change 的能力增量：让 `guard` 的「拦」退出码**只由「拦」自己产生**，
> 未预期异常一律走 **fail-open**（非 1），并使宿主 shim 的映射对版本偏斜免疫。

## Requirement: 守卫的内部错误不得被当成拦截

`witnessloop guard` SHALL 在其执行过程中出现**未预期异常**时**不**以「拦」的退出码结束——
即内部错误 SHALL 以**非 1**的退出码返回（fail-open 放行），并在标准错误输出一行诊断。

「拦」的退出码 SHALL 保持为 **1**，且 SHALL **只**由「命中 `require_change_for` 且当前 change
的 grill 证据不完备」这一显式判定产生。

内部错误的退出码 SHALL 由一个与「拦」（1）**不同**的常量定义（实现取 **4**）。

### Scenario: 报告无法解码不得拦下写入
- **Given** 当前 change 的 `stage=grill` manifest 绑定了一份**非法 UTF-8** 的报告
- **When** 运行 `guard --path src/x.py`（命中 `require_change_for`）
- **Then** 退出码**不是 1**（实现为 4），并打印一行诊断——宿主据此**放行**（fail-open）

### Scenario: 任意内部异常都不拦
- **Given** 判定过程中抛出任意未预期异常（如 `RuntimeError`）
- **When** 运行 `guard`
- **Then** 退出码**不是 1**，且打印诊断

### Scenario: 崩溃兜底覆盖 import 缺口
- **Given** `witnessloop guardcmd` 模块**导入失败**（`ImportError`）
- **When** 运行 `witnessloop guard`
- **Then** 退出码**不是 1**（走同一个兜底），而不是让 CPython 以 1 退出被宿主当成「拦」

### Scenario: 「拦」仍是 1（回归）
- **Given** 写目标命中 `require_change_for` 且当前 change 的 grill 证据不完备
- **When** 运行 `guard`
- **Then** 退出码仍为 **1**（既有契约不变）

## Requirement: 宿主 shim 只把「拦」映射成 block

随 plugin 分发的 `guard.sh` SHALL 仅把 `guard` 的 **1** 映射成宿主的 block 约定（CC 的 2），
其余一切退出码（含内部错误码 4、用法错误 2、未接入 3、二进制缺失 127）SHALL 一律放行。

该映射 SHALL 对 **shim 与 CLI 版本偏斜**保持安全：旧 shim（只认 1）配新 CLI 时，
「拦」仍映射正确、内部错误仍放行。

### Scenario: 内部错误码被放行
- **Given** `witnessloop guard` 以内部错误码（4）退出
- **When** 宿主 shim 处理该事件
- **Then** shim 以 0 退出（**不** block）

### Scenario: 「拦」仍映射为 block（回归）
- **Given** `witnessloop guard` 以 1 退出
- **When** 宿主 shim 处理该事件
- **Then** shim 退出 2（宿主的 block）

## Requirement: 崩溃兜底不改变 `check` 的语义

本能力 SHALL **只**作用于 `guard`；`check` 出现未预期异常时的退出码语义 SHALL 保持不变
（其崩溃仍以「未通过」的退出码结束——CI 锚保持 fail-closed）。

### Scenario: check 仍 fail-closed
- **Given** `check` 在执行中遇到一份无法解码的报告
- **When** 运行 `check`
- **Then** 它仍以非零（「未通过」）结束——本 change 不把它改成放行
