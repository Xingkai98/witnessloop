# Tasks: archive-arrival-recognition

> **测试先行**：第 2 节（测试）先于第 3 节（实现），先写后实现。
> **本 change 的核心风险是「把豁免面开大」**（`archive-awareness` 的 C3 教训：只让 `_require_change` 闭嘴的实现
> 会让「改了 `src/**` 却零 change 证据」的 PR 变绿）⇒ 每条新授予都必须配一条**同等强度**的证据门用例。

## 0. 设计追问与用户确认（前置门，不完成不开工）

- [ ] 0.1 用独立零记忆设计追问（`grilling` skill 或等价流程）对 `design.md` 做追问，产出结构化决策记录到 `reviews/grill-design.md`（`## Confirmed Decisions` ≥ 3 条）。
- [ ] 0.2 把 `design.md` `## 停轮问题` 的 **Q1–Q4** 逐条停轮抛给用户，每条附**本 change 真实场景的具体例子**（参数 / 输入输出 / 前后对比）与推荐值，等待明确答复。
- [ ] 0.3 把答复逐条记进 `reviews/grill-design.md` 的 `## User Confirmation`（格式 `- **Q<n>**: 用户答复：<实质内容>；确认时间: <date>`，不得写「按推荐」这类占位）。
- [ ] 0.4 跑设计阶段审阅闭环（独立零记忆审阅者 → 对抗分析 → verdict → 修 → 再审，直到收敛），产出 `reviews/grill-adversarial.md`。能由代码判定的问题用**带 `文件:行号` 证据**的答案移出停轮队列。

## 1. 规格

- [ ] 1.1 修改 `archive-awareness` 规格：把「归档 move 使该 change 进入集合」改为「**归档目录的新增**使该 change 进入集合」，并写死 `SHALL NOT` 依据逐文件改名分 / `R100`。
- [ ] 1.2 重写否定面 Requirement：保留并**升级**「不得给 base 里已存在的归档目录授予资格」；**注明**旧否定面 N2 / N7 被本 change 反转及其理由。
- [ ] 1.3 新增「到达集合的用途共用同一份判定」（归属 / 幽灵 id 排除 / 保护写豁免）。
- [ ] 1.4 新增「到达方式不改变证据门槛」的对称性不变量，并给「零证据归档 change 照样逐条点名」的防绕过用例。
- [ ] 1.5 同步 current spec 到 `openspec/specs/archive-awareness/spec.md`，并按本仓政策追加解释事件（受保护路径）。

## 2. 测试（先行，先写后实现）

- [ ] 2.1 **到达判定的纯函数用例**（注入式基树谓词，不碰真 git）：目录新增 ⇒ 到达；目录已存在 ⇒ 不到达；基树不可读 ⇒ fail-closed。
- [ ] 2.2 **出生即归档**：base 无此 change、head 有 `archive/<name>/`（全 `A`）+ 改 `require_change_for` 路径 ⇒ 退出码 0。
- [ ] 2.3 **move 内带内容改动**：全 `R<100`（含重建过的 manifest）⇒ 退出码 0，且**无**幽灵 active id。
- [ ] 2.4 **纯 move 回归**：全 `R100` 的行为逐条与改动前一致（今天绿 ⇒ 修后绿）。
- [ ] 2.5 **对称性不变量**：同一份 change 内容，active 与 archive 两种位置判绿判红结论相同。
- [ ] 2.6 **否定面**（`design.md §5.3` N1–N7 逐条）：尤其 N2/N3（触碰**已存在**归档目录）、N4（单文件移入既有归档目录）、N6（到达但零证据 ⇒ 逐条点名三份 stage manifest）。
- [ ] 2.7 **接入方真实形状的集成用例**：用接入方 PR 的那两份 diff（33 文件全 `A` / 16 文件含 `R<100`）各一条，断言修前红、修后绿。
- [ ] 2.8 **fail-closed 用例**：基树不可读 ⇒ 报 finding、不授予、退出码非 0。

## 3. 实现

- [ ] 3.1 `src/witnessloop/gitutil.py`：新增基树查询帮助函数（`fail-closed`：读不出 ⇒ 抛错/返回失败，调用处报 finding）。
- [ ] 3.2 `src/witnessloop/contract.py`：新增到达判定（基树查询作为**注入谓词**，判定本体为纯函数）；改 `changed_change_ids` 的 `archived_sources` 为**到达组**口径。
- [ ] 3.3 `src/witnessloop/contract.py`：改 `change_targets` 用到达集合产出归档 target；保留名识别守卫（对**有源**的到达）。
- [ ] 3.4 `src/witnessloop/checkcmd.py`：`_check_protected_writes` 的保护写豁免改用**到达集合**；保留「对已存在归档目录的修改 / 删除仍要事件」。
- [ ] 3.5 `src/witnessloop/manifestcmd.py`：与 `check` 共用同一份 target 解析（**单一实现**，不留第二套）。
- [ ] 3.6 核对：`is_archive_move` / `archive_grant` 若失去全部调用点则删除；若仍被别处使用则逐点确认语义未被削弱（不得留「看似归档」的半套判据）。

## 4. 验证

- [ ] 4.1 `uv run pytest -q`（新增用例 + 全量回归）。
- [ ] 4.2 用**接入方真实提交**复算 `proposal.md` 的表（三份 diff × 两个 ref），把原始输出要点记进 `reviews/` 或 PR 描述。
- [ ] 4.3 本仓 `witnessloop check` 对**本 change 自己**判绿（自举）。
- [ ] 4.4 逐条复算 `design.md §5.3` 的否定面，确认**照样红**。

## 5. 实现后独立审阅闭环

- [ ] 5.1 跑独立审阅闭环，产出 `reviews/building-review.md`（CHANGES_REQUESTED 则修复并加回归测试，再审，直到收敛）。
- [ ] 5.2 收敛后清理中间轮产物，或把最终版落到规范名（避免孤儿报告）。

## 6. 文档

- [ ] 6.1 `docs/gate.md`：§5.1.1 / §4 / §3.2 / §6 按新判据同步；删掉「R100 要求」的表述，补「基树不可读 ⇒ fail-closed」。
- [ ] 6.2 `README.md`：接入指引的归档时序一段按新判据改写（**不**把出生即归档写成推荐流程）。
- [ ] 6.3 检查文档影响面：`docs/` 全量与本次判据相关的段落（关键词：`R100`、`归档 move`、`is_archive_move`、`archive_grant`）。

## 7. 收尾

- [ ] 7.1 确认三份 stage manifest 在**所有内容提交之后**重建，且 `reviews/` 处于「每份 `.md` 都被绑定」的一致状态。
- [ ] 7.2 归档 move 必须是**独立的纯 rename 提交**（不与内容改动并用）。
- [ ] 7.3 从 backlog / 相关跟踪处移除本 change 条目，并追加解释事件。
- [ ] 7.4 回链 issue #26：补完成说明 comment 并关闭。
