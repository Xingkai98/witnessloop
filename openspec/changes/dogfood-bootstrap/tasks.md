# Tasks: dogfood-bootstrap

> 依据 `design.md`（已收敛）。原则：**测试先行（TDD）**——每个能力先写失败测试再实现。
> ⚠️ R1：change 目录必须**全程完整**；两段提交（先内容、后证据）须在本文件与 `specs/` 补齐后才开始。

## A. `init --policy`（D2，含修正 R2）

- [ ] A1 单测（先红）：`init --policy <file>` 用给定内容落盘，且 `init-manifest` 台账 hash 与之一致
- [ ] A2 单测：幂等——同 policy 重跑 `init` 报「无改动」exit 0
- [ ] A3 单测：`init --policy` 后 `uninit` 能按台账精确回滚
- [ ] A4 单测：`--policy` 文件缺失 / JSON 非法 / 非对象 → **报错且不写任何文件**；
      `--policy` **允许指向仓外路径**（Q5：seed 不入库，故 seed 常在仓外）
- [ ] A5 单测：`init --policy` 与 `--dry-run` 组合（不落盘）
- [ ] A6 **单测（先红，R2 驱动）**：已接入后再 `init --policy <与已落地不同>` → **报冲突非零退出**（现状是静默 no-op）
- [ ] A7 实现：`cli.py` 的 `init` 加 `--policy`；`initcmd.desired_files` 接受外部 policy 文本；`run` 读取+轻校验
- [ ] A8 实现：`_already_initialized` 新增「desired 与已落地不同 ⇒ 冲突」分支（兑现 A6）

## B. 本仓接入（D1/D3/D5）

- [ ] B1 `witnessloop init --policy <seed>` 落地 `.witnessloop/policy.json` + `.witnessloop/init-manifest.json`
      + `.github/workflows/witnessloop.yml`（policy 的 `require_change_for` 补 `templates/**`、`plugin/**`）
- [ ] B2 seed 临时文件**不入库**（Q5）

## C. 文档同步（§6，含 R6 漂移守卫）

- [ ] C1 `docs/gate.md` 加 `init --policy` 一节
- [ ] C2 `README.md` 加「本仓自身接入（dogfood）」+ `init --policy` 用法
- [ ] C3 `docs/design.md` 状态/§10 更新（§9 风险 4 **不变**）
- [ ] C4 `docs/tasks.md` 追加 G 段
- [ ] C5 改上述文件（含 `cli.py`）后**同步 `tests/test_docs.py` 守卫**（碰掉被钉措辞则 CI 红）

## D. 证据链与收尾（§5）

- [ ] D1 端到端：本 change 两段提交 + `manifest build` × 3（grill / grill-adversarial / building）+ `check` 绿
- [ ] D2 负例：改 `.witnessloop/policy.json` 不写事件 → `check` 拦
- [ ] D3 独立 `review-loop`（实现完成后，PASS 或 3 轮封顶）
- [ ] D4（**需用户**）`main` 开 branch protection：**require PR** + required check = witnessloop gate（Q3）

## 明确不做（本 change）

本地 pre-write 守卫（#7 B 轨）· 报告正文校验（本仓 #2）· `policy upgrade` 动词（Q6a 立为后续）· 私有仓（#6）· fork PR（#5）。
