# Tasks: events-readpoint-fix

> 依据 `design.md`（草稿——grill + 对抗验证收敛 + Q1/Q2 确认前不得写实现代码）。
> 原则：**测试先行（TDD）**。
> ⚠️ change 目录必须**全程完整**（本文件 + `specs/event-readpoint/spec.md`）。

## A. `events.py` 读点归一（D1/D2/D4）—— issue #12 本体

- [ ] A1 单测（先红）：`load_events_file` 遇**非法 UTF-8** ⇒ 抛 `EventError`（当前抛 `UnicodeDecodeError`）
- [ ] A2 单测（先红）：文案**按成因分**且**点名文件**（解码失败 ≠ 读不到）
- [ ] A3 单测（先红·回归）：**合法** events 的行为不变（正常解析 + 逐行 JSON 错误仍抛 `EventError`）
- [ ] A4 实现：`events.py` 的读点包 try ⇒ 抛 `EventError`（**不改 `checkcmd`**——出路已现成，D2）
- [ ] A5 端到端单测（先红）：含非法 UTF-8 events 的仓 ⇒ `check` **不抛异常**、**非 0**、
      stderr 含「事件文件无法解析」且**不含 `Traceback`**

## B. 同族剩余读点（**依 Q1 裁定**）

- [ ] B1 实现（若 Q1 一并修）：`initcmd.py:63/131` 的 except 元组补 `UnicodeDecodeError`；
      `:118/201/216` 的读点包 try
- [ ] B2 实现（若 Q1 一并修）：`uninitcmd.py:30` 的 except 补 `OSError`+`UnicodeDecodeError`；`:77` 的读点包 try
- [ ] B3 单测（若 B1/B2 做了）：`init` / `uninit` 各自「读不出 ⇒ 干净报错 + 非 0（无 traceback）」

## C. 回归

- [ ] C1 受保护写入豁免的既有用例全绿（合法 events 语义未变）
- [ ] C2 全量 `uv run pytest -q` 绿

## D. 文档

- [ ] D1 `docs/gate.md §8`：读点表里 `events.py` 那行（被 `guard-crash-exit` 标为「非目标」）改为**已覆盖**
- [ ] D2 `docs/gate.md §4`（结构化解释事件）：补「读不出 ⇒ 干净的 finding（不是崩溃）」
- [ ] D3 `README.md`：写明**对**接入方是**报错形态变更**（崩溃 traceback → 干净红；**不是新的红**）

## E. 证据链与收尾

- [ ] **E0** 停轮拿到 Q1/Q2 答复 → 写 `## User Confirmation` → `manifest build --stage grill` 放行 `src/**` →
      内容提交后**必须重跑**（否则 stale 红）
- [ ] E1 两段提交 + `manifest build`（grill / grill-adversarial / building）+ `check` 绿
- [ ] E2 独立 `review-loop`（PASS 或 3 轮封顶）
- [ ] E3 PR（branch protection）→ 合入 → 关 issue **#12**

## 明确不做（本 change）

共用读文本 helper / 全局重构（D3）· 改 `check` 退出码语义 · 改 `checkcmd`（D2）· 签名/防伪造。
