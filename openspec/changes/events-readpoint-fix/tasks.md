# Tasks: events-readpoint-fix

> 依据 `design.md`（草稿——grill + 对抗验证收敛 + Q1/Q2 确认前不得写实现代码）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/event-readpoint/spec.md`）。

## A. `events.py` 读点归一（D1/D2/D4）—— issue #12 本体

- [ ] A1 单测（先红）：`load_events_file` 遇**非法 UTF-8** ⇒ 抛 `EventError`（当前抛 `UnicodeDecodeError`）
- [ ] A2 单测（先红）：**目录冒充** events 文件（`IsADirectoryError`，与 uid 无关——`chmod 000` 在 root 下假绿，R6）
      ⇒ 抛 `EventError` 且文案是「**无法读取**」（与「无法解码」可区分，D4）
- [ ] A3 单测（先红·回归）：**合法** events 的行为不变（正常解析 + 逐行 JSON 错误仍抛 `EventError`）
- [ ] A4 实现：`events.py` 的读点包 try ⇒ 抛 `EventError`（**不改 `checkcmd`**——出路已现成，D2）
- [ ] A5 端到端单测（**先红**·可判定）：含非法 UTF-8 events 的仓 ⇒ stderr **含**「事件文件无法解析」
      **且不含 `witnessloop：内部错误`**（⚠️ **今天「不含内部错误」为假、修后为真**；**
      不要**写「不抛异常 / 非 0 / 不含 Traceback」——那三条**今天就已经全绿**，是假红先，Q3/R3）

## B. 同族剩余读点（**依 Q1 裁定**）

- [ ] B1 实现（若 Q1 一并修）：**补 except 元组**（用 D3 的既有 idiom `except (OSError, ValueError)`——
      **不要**逐点罗列异常名，那与既有 4 处分叉）到 `initcmd.py:63/131/201`、`uninitcmd.py:30`
      （⚠️ `:201` 是**补元组**不是「无 try」——grill 实测纠正原稿）
- [ ] B2 实现（若 Q1 一并修）：**新包 try** 在 `initcmd.py:118/216`、`uninitcmd.py:77`
- [ ] B3 单测（若 B1/B2 做了）：`init` / `uninit` 各自「读不出 ⇒ 干净报错（**不含 `witnessloop：内部错误`**）+ 非 0」
- [ ] B4 非目标登记（无论 Q1 怎么裁）：`read_bytes` 两处（`initcmd.py:215`/`uninitcmd.py:59`）与
      `sha256_tree`（`contract.py:373/386`）写进 design 的**非目标**并注明理由（**不同族**）

## C. 回归

- [ ] C1 受保护写入豁免的既有用例全绿（合法 events 语义未变）
- [ ] C2 全量 `uv run pytest -q` 绿

## D. 文档

- [ ] D1 `docs/gate.md §8`：**新增一行** events（该表**只有 3 行、无 events 行**——原稿说「改一行」是错的，grill 实测），
      写明覆盖范围 = **active change 目录**（`archive/**` 不参与，R5）；
      ⚠️ **只改 `docs/gate.md`**——**绝不**编辑 `openspec/changes/guard-crash-exit/**`（那会触发 R2 自伤：多 change 同 PR ⇒ 它也要 building 证据）
- [ ] D1b 订正 `docs/gate.md §8` 里**既有**那句错话（「`check` ⇒ traceback」——实测是**一行** `内部错误`，R1）
- [ ] D2 `docs/gate.md §4`（结构化解释事件）：补「读不出 ⇒ 干净的 finding（不是崩溃）」
- [ ] D3 `README.md`：写明**对**接入方是**报错形态变更**（`witnessloop：内部错误` → 一行点名文件的 finding；
      **退出码不变、不是新的红**）

## E. 证据链与收尾

- [ ] **E0** 停轮拿到 Q1/Q2 答复 → 写 `## User Confirmation` → `manifest build --stage grill` 放行 `src/**` →
      内容提交后**必须重跑**（否则 stale 红）
- [ ] E1 两段提交 + `manifest build`（grill / grill-adversarial / building）+ `check` 绿
- [ ] E2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] E3 PR（branch protection）→ 合入 → 关 issue **#12**

## 明确不做（本 change）

共用读文本 helper / 全局重构（D3）· 改 `check` 退出码语义 · 改 `checkcmd`（D2）· 签名/防伪造。
