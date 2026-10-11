# ADR 0001：本地守卫（写码前缺 grill 证据就拦）

- 状态：已采纳
- 日期：2026-10-11
- 关联：change `grill-evidence-gate`、issue #7（② 轨）

## 背景

v1 的既定决策是「**强制落 CI（merge boundary），agent hooks 只作提醒**」（`docs/design.md` §2 点 6 / §9 风险 4）。
实测后果（issue #7）：开发 witnessloop **自己**时，**设计阶段的 grill 被跳过且没人拦**——因为
「写码前缺 grill 证据就拦」这一步在**本地没有任何执行体**。核心主张（机械强制、不靠自觉）在自己仓里不成立。

## 决策

**新增本地守卫**：`witnessloop guard` 动词（host 中立）+ 随 plugin 分发的 CC PreToolUse hook。
写目标命中 `policy.require_change_for` 且**当前 change 的 grill 证据不完备** ⇒ 拦（exit 2）。

## 备选

1. **不做本地层**（维持 v1）——否：流程仍可被跳过。
2. **只做 git-hook（pre-commit/pre-push）**——host 无关、人也能用，但边界在 **commit**、且要维护第二套安装
   路径；CI required check 已兜底，边际收益低。**延后**（design Q5）。
3. **把判定塞进门禁层**——否：门禁层 host-agnostic 是既定轴；本地守卫依赖 host 的**工具事件** ⇒ 归**交互层**。

## 影响

- `guard` 属**交互层**（host 特定接线），但**动词本身 host 中立**——门禁层仍 host-agnostic。
- **不移动 v1 的锚**：本地层可绕（Bash 写文件 / 不装 plugin），**真正的锚仍是 CI required check**。
- 与 `check` **共用同一个** `evidence.grill_evidence_findings` 判定——杜绝「两边各写一套」的漂移
  （本仓已因 `check` / `manifest build` 各写一套踩过坑，故共用 `constants.HASHED_ARTIFACTS`）。

## 代价 / 风险

- 本地层会给人「已强制」的错觉 ⇒ §9 风险 4 与 README 明写「防遗忘 ≠ 防对抗」。
- hook 的失败模式多为 **fail-open**（二进制不在 PATH、超时）⇒ 写进安装文档（README / `plugin/README.md`）。

## 参考

- `templates/grill.md`（grill 的产出形态与硬门槛）
- asterwynd `scripts/workflow_guard.py` 的 `_grill_evidence_missing()`（本地判的谓词原型；**只移植谓词**，
  其 `- **决策**：` 前缀匹配不能照抄——会把 `- **决策（D1）**：` 判成 0 条）
