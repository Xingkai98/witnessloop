# Tasks: grill-evidence-gate

> 依据 `design.md`（已收敛）。原则：**测试先行（TDD）**——每个能力先写失败测试再实现。
> ⚠️ R1：change 目录必须**全程完整**（本文件 + `specs/evidence-gate/spec.md`）；两段提交须在其齐备后才开始。

## A. 共享 evaluator（D1）——**已完成**

- [x] A1 单测（先红）：`evidence.grill_evidence_findings(text)` 对**合格**样本 → 空 findings
- [x] A2 单测：`## Confirmed Decisions` <3 条 → 红
- [x] A3 单测：**块级 `来源:`**——bullet 同行不带、**续行**带 → **算合格**（本仓 dogfood 的真实形态）
- [x] A4 单测：entry 前缀变体——`- **决策（Dn）**：` 与 `- **决策**：` **都要**算（**移植陷阱护栏**）
- [x] A5 单测：`## Open Questions` 的 `Qn` 在 `## User Confirmation` 无对应 → 红
- [x] A6 单测：占位确认（`待确认`/`待主 agent`…；**长答复豁免**的启发式）不算确认
- [x] A7 单测：缺节（无 `## Confirmed Decisions` / 无 `## User Confirmation`）→ 红
- [x] A8 实现：`src/witnessloop/evidence.py` 纯函数（复用 `contract.Finding`）

## B. `check` 接入（D9 / #2）——**已完成**

- [x] B1 单测（先红）：`check` 对「正文不合格的报告」红、对合格绿
- [x] B2 单测：manifest 缺 `stage` → 红（`constants.REVIEW_MANIFEST_REQUIRED_FIELDS` 纳入 `stage`）
- [x] B3 单测：无 `stage=grill` 的 manifest → 红，文案点名「现有 stage：…」
- [x] B4 **回归**：本仓 `dogfood-bootstrap` 仍绿（实测 `findings = 0`）
- [x] B5 实现：`checkcmd` 接入 evaluator；`constants` 加 `stage`

## C. `guard` 动词（D3/D4/D5）——**已完成**

- [x] C1 单测：命中 `require_change_for` 且缺证据 → exit **2**（拦）
- [x] C2 单测：证据齐 → exit 0
- [x] C3 单测：写文档（`reviews/**`/`openspec/changes/**`/`docs/**`）→ 放行（**死锁防线**）
- [x] C4 单测：推得 id **不命中现存 active change 目录** → 放行 + 提示（Q2）
- [x] C5 单测：推不出 / 未接入 → 放行 + 提示
- [x] C6 单测：`WITNESSLOOP_SKIP_GUARD=1` → 放行 + stderr 留痕；`WITNESSLOOP_CHANGE` 覆盖分支名
- [x] C7 实现：`src/witnessloop/guardcmd.py` + `cli.py` 加 `guard` 子命令

## D. CC hook 分发（D6）——**已完成**

- [x] D1 实现：`plugin/hooks/hooks.json`（`matcher:"Write|Edit"` → shim）
- [x] D2 实现：`plugin/hooks/guard.sh`（从 stdin 取 `tool_input.file_path` → `witnessloop guard --path …`；退出码直传）
- [x] D3 单测：`hooks.json` 结构合 CC 格式（`matcher`/`command`）
- [x] D4 文档：README / `plugin/README.md` 写明「装了 plugin **还要**装 CLI」（否则非 2 退出 → 不阻塞 = fail-open，R8）

## E. 文档 + ADR（D7）——**已完成**

- [x] E1 改**四处**「hooks 只 advisory」措辞：`docs/design.md` §2 点 6 / §9 风险 4、`README.md` 核心理念、
      `docs/reviews/grill-design.md`（保留原文 + 加更新注）
- [x] E2 新增 ADR `docs/adr/0001-local-guard-hook.md`（`docs/adr/` 此前不存在，已新建）
- [x] E3 新增**漂移守卫测试**（`test_docs_no_longer_call_hooks_advisory_only`）钉新口径
- [x] E4 `docs/gate.md`：新增 §8（判定 + `guard` + **退出码按动词分表**）
- [x] E5 `README.md`：`guard` 用法 + 诚实边界（D8 的真实绕过面）

## F. 自伤修复（D9）——**已完成**

- [x] F1 更新 `tests/test_cli.py` 期望动词集（+ `guard`）
- [x] F2 更新 `tests/test_plugin.py` 期望文件清单（+ `hooks/hooks.json` + `hooks/guard.sh`）

## G. 证据链与收尾

- [ ] G1 两段提交 + `manifest build` × 3 + `check` 绿
- [ ] G2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] G3 PR（本仓 branch protection 已开：require PR + required check `gate / check`）

## 明确不做（本 change）

git-hook 适配器（Q5 延后）· 签名 / 防伪造 · 其余动名词 · 收紧 `--stage` 值域 · 私有仓（#6）。
