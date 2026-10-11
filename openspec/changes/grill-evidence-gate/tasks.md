# Tasks: grill-evidence-gate

> 依据 `design.md`（已收敛）。原则：**测试先行（TDD）**——每个能力先写失败测试再实现。
> ⚠️ R1：change 目录必须**全程完整**（本文件 + `specs/evidence-gate/spec.md`）；两段提交须在其齐备后才开始。

## A. 共享 evaluator（D1）

- [ ] A1 单测（先红）：`evidence.grill_evidence_findings(text)` 对**合格**样本 → 空 findings
- [ ] A2 单测：`## Confirmed Decisions` <3 条 → 红
- [ ] A3 单测：**块级 `来源:`**——bullet 同行不带、**续行**带 → **算合格**（本仓 dogfood 的真实形态）
- [ ] A4 单测：entry 前缀变体——`- **决策（Dn）**：` 与 `- **决策**：` **都要**算（**移植陷阱护栏**）
- [ ] A5 单测：`## Open Questions` 的 `Qn` 在 `## User Confirmation` 无对应 → 红
- [ ] A6 单测：占位确认（`待确认`/`待主 agent`…；**长答复豁免**的启发式）不算确认
- [ ] A7 单测：缺节（无 `## Confirmed Decisions` / 无 `## User Confirmation`）→ 红
- [ ] A8 实现：`src/witnessloop/evidence.py` 纯函数（复用 `contract.Finding`）

## B. `check` 接入（D9 / #2）

- [ ] B1 单测（先红）：`check` 对「正文不合格的报告」红、对合格绿
- [ ] B2 单测：manifest 缺 `stage` → 红（`constants.REVIEW_MANIFEST_REQUIRED_FIELDS` 纳入 `stage`）
- [ ] B3 单测：无 `stage=grill` 的 manifest → 红，文案点名「现有 stage：…」
- [ ] B4 **回归**：本仓 `dogfood-bootstrap` 仍绿
- [ ] B5 实现：`checkcmd` 接入 evaluator；`constants` 加 `stage`

## C. `guard` 动词（D3/D4/D5）

- [ ] C1 单测：命中 `require_change_for` 且缺证据 → exit **2**（拦）
- [ ] C2 单测：证据齐 → exit 0
- [ ] C3 单测：写文档（`reviews/**`/`openspec/changes/**`/`docs/**`）→ 放行（**死锁防线**）
- [ ] C4 单测：推得 id **不命中现存 active change 目录** → 放行 + 提示（Q2）
- [ ] C5 单测：推不出 / 未接入 → 放行 + 提示
- [ ] C6 单测：`WITNESSLOOP_SKIP_GUARD=1` → 放行 + stderr 留痕；`WITNESSLOOP_CHANGE` 覆盖分支名
- [ ] C7 实现：`src/witnessloop/guardcmd.py` + `cli.py` 加 `guard` 子命令

## D. CC hook 分发（D6）

- [ ] D1 实现：`plugin/hooks/hooks.json`（`matcher:"Write|Edit"` → shim）
- [ ] D2 实现：shim（从 stdin 取 `tool_input.file_path` → `witnessloop guard --path …`；exit 2 透传）
- [ ] D3 单测：`hooks.json` 结构合 CC 格式（`matcher`/`command`）
- [ ] D4 文档：README 写明「装了 plugin **还要**装 CLI」（否则非 2 退出 → 不阻塞 = fail-open，R8）

## E. 文档 + ADR（D7）

- [ ] E1 改**四处**「hooks 只 advisory」措辞：`docs/design.md:27`/`:145`、`README.md:108`、`docs/reviews/grill-design.md:19`
- [ ] E2 新增 ADR `docs/adr/0001-local-guard-hook.md`（`docs/adr/` 今日不存在，需新建）
- [ ] E3 新增**漂移守卫测试**钉「hook 已从 advisory 改为强制」（今日无此守卫 ⇒ 漏改不红）
- [ ] E4 `docs/gate.md`：`guard` 动词 + `check` 正文校验 + **退出码按动词分表**
- [ ] E5 `README.md`：本地 guard 用法 + 诚实边界（D8 的真实绕过面）

## F. 自伤修复（D9）

- [ ] F1 更新 `tests/test_cli.py:48-52` 期望动词集（+ `guard`）
- [ ] F2 更新 `tests/test_plugin.py:64-71` 期望文件清单（+ `hooks/hooks.json` + shim）

## G. 证据链与收尾

- [ ] G1 两段提交 + `manifest build` × 3 + `check` 绿
- [ ] G2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] G3 PR（本仓 branch protection 已开：require PR + required check `gate / check`）

## 明确不做（本 change）

git-hook 适配器（Q5 延后）· 签名 / 防伪造 · 其余动名词 · 收紧 `--stage` 值域 · 私有仓（#6）。
