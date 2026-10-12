# Proposal: guard-crash-exit（guard 崩溃不得被当成 block）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#9**（低、非阻塞；change `grill-evidence-gate` 第 2 轮实现审阅的遗留）。

## 背景

`guard` 的「拦」当前定义为退出码 **1**（`constants.py:81` 的 `EXIT_FAIL`，为避开 argparse 的 **2**
而选 1，见 change `grill-evidence-gate` 的 D5 / 回归审阅 Issue 3）。代价是：

- **1 同时也是 Python 进程「未捕获异常」的退出码**（`cli.main` 不 catch；`__main__.py` 只 `sys.exit(main())`）。
- 而 `plugin/hooks/guard.sh:38-41` 把 **1 → CC 的 2（block）**。

⇒ `guard` **自身崩溃**时，宿主把它读成「**拦住**」——**误拦每个 `Write|Edit`**。
实测触发例：`evidence.py:216` 用 `report.read_text(encoding="utf-8")` 读一份**非法 UTF-8** 的报告
⇒ `UnicodeDecodeError` ⇒ 崩溃退 1 ⇒ 被当 block。

这与 Issue 3 **同类**（「非 block 语义的退出码被当成 block」），只是触发源从「旧版 CLI 的 argparse
**用法错误**（退 2）」换成「`guard` **崩溃**（退 1）」。Issue 3 已修；这条未修。

## 目标

1. 让 `guard` 的**「拦」与非「拦」退出码互斥**：**未预期异常绝不被宿主当成 block**（fail-open），
   并把该不变量**钉成回归测试**（防日后回退）。
2. **在源头把已知的读失败归一成 verdict**：`guard`/`check` 可达的证据读点（policy / review manifest / 报告）
   遇**解码失败**时**不崩溃**，而是产出一条确定性结论（manifest 坏 ⇒ 拦/红；policy 坏 ⇒ 放；报告坏 ⇒ 见 Q1）。

## 非目标

- **不改 `check` 的退出码语义**：`check` 遇同类问题的退出码仍是「未通过」= fail-closed；本 change 只把它的
  **报错路径**从 traceback 改成干净的 finding（读点归一），**不改**它「通过 / 不通过」的判据。
- **`events.py:51`（`workflow-events.jsonl` 读点）**：`check`-only、不同 artifact、无 `guard` 路径，
  其崩溃退 1 = fail-closed（仅报错难看）⇒ 属**既有**问题、另立 issue（design §3 非目标）。
- **不引入签名 / 防伪造**（沿用 v1 边界：防漂移，不防伪造）。
- **不动 hook 的安装/分发方式**（沿用 `grill-evidence-gate` 的 D6）。
- **兜 `witnessloop.cli` 自身模块级 import 失败**（安装破损）——用户 Q2 裁定「修掉」⇒ 兜底前移到进程入口 `entry.py`（**因此不列为非目标**）。
- 不新增动词、不改 plugin 文件清单。

## 验收

- **单测**：`guard` 遭遇未预期异常 ⇒ 退 **非 1**（fail-open）+ 一行诊断；且**「拦」仍是 1**（不回归）。
- **shim 单测**：CLI 以此新码退出 ⇒ shim 放行（exit 0）；「拦」（1）仍映射到 CC 的 2。
- **端到端**：真实触发例（非法 UTF-8 报告）⇒ `guard` 不再被当 block。
- 本 change 自己走完整流程（契约 + 证据 + `check` + PR；本仓已开 branch protection）。

## 测试策略

TDD。崩溃用**两条路径**造：(a) 真实触发例——把 `stage=grill` 的合格报告覆写成非法字节；
(b) 通用——monkeypatch `evidence.grill_evidence_findings_in_change` 抛异常。shim 侧沿用既有
`_run_shim` 假 CLI 手法，补「新码 → 放行」用例。详见 `design.md` §5。
