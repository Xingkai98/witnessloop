# Proposal: gate-ref-pins-package（接入方钉住 witnessloop 的**包版本**）

> 状态：草稿（待 grill + 对抗 + 用户确认）。关联 issue：witnessloop **#30**（阶段 C 的硬前置）。
> 实测来源：副本仓 `Xingkai98/asterwynd-wl-switch`（C1-b 的真 CI 实验，issue #30 正文有原始输出）。

## 背景

接入方把 `gate / check` 勾成 required 之前，踩到一个**静默**的坑：**升级了 witnessloop，门禁仍用旧包判**。

### 机制（逐行）

- `init` 生成的 caller 只写一行 `uses: <gate_ref>`（`src/witnessloop/initcmd.py:32-46`），**从不**写 `with:`。
- **包版本**取 reusable workflow 的输入 `inputs.witnessloop-ref`（`.github/workflows/gate.yml:19-23`，`default: "v1"`）；
  调用方不传 ⇒ **恒为 `v1`**。
- `--gate-ref`（`src/witnessloop/cli.py:43-48`）只改 `uses:` 那一行，**不影响**包版本。

⇒ 接入方**不移动 `v1` tag 就永远吃到旧包**，且**没有任何提示**。

### 实测（副本仓真 CI，issue #30 原文）

同一构造、同一份 diff，只差包版本：`v1`（默认）⇒ `gate / check` **✗ 10 项**（含幽灵 active id、受保护写入误报——**都是已修好的旧行为**）；
`main` ⇒ **✗ 1 项**（只剩一条真实残余）。CI 日志里确实解析成 `witnessloop@ae992565ee2162e5b272af471e9adf895e7f83fb`（= `v1`）。

## 目标

1. **一次入口、两处一致**：接入方钉住的 ref，同时决定 **workflow 文件**与**包**；
   SHALL NOT 要求接入方分别管两个 ref。
2. **对既有接入方不静默**：升级动作/文档写清；且能看出「本次跑的是哪个 ref」。
3. **不动 `v1` tag**（那正是要避免的动作）。

## 非目标

- **不做** issue #31（`D` 侧掉队）相关任何事——正交。
- 不引入签名 / 不由本工具管理 tag / 不做自动升级。
- 不改 `gate.yml` 的 `check` 判定语义（本 change 只动「跑哪个包」这条链）。

## 验收

- 新接入方：`init --gate-ref <ref>` 生成的 caller 与包**同 ref**（可复算：看生成文件 + 看 CI 日志里解析到的 `witnessloop@<ref>`）。
- 既有接入方：有**单一、明确**的升级动作（且 `init` 仍保持「只增不改 / 幂等」的既有契约，不被本 change 打破）。
- 版本可见：CI 日志里能直接看到本次用的 ref（对 **sha** 形态的 ref 也成立）。
