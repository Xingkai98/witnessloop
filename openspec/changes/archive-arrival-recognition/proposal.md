# Proposal: archive-arrival-recognition（归档到达方式：按**目录是否新增**判，不按**逐文件改名分**）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#26**。
> 实测来源：接入方 asterwynd 的**真实提交**（PR #309，issue #305 的阶段 C 前置验证 C1）；
> 本 change 的所有实测数字都可用 `design.md §1` 的命令复算，**不是**估计值。

## 背景

`archive-awareness`（PR #22）给工具补上了「这个 change 被归档了」的表示，修好了三条症状里的两条半。
但它在实现时用了一个**代理指标**：`contract.is_archive_move`（`src/witnessloop/contract.py:65`）要求
**逐文件** `status == "R100"`（100% 纯改名）。真实接入方的流程**必然**打不中这个指标，两类形态各自撞墙：

1. **出生即归档**：diff 的 base 里根本没有这个 change（change 与实现同一 PR 内产生），
   归档目录下的文件在 `git diff --find-renames` 里**全是 `A`、一个 rename 都没有** ⇒ 授予资格不触发
   ⇒ `0 个 change 目录` ⇒ `require_change_for` 报「属于必须挂 change 的路径，但本次 diff 里没有任何 change 目录」。
2. **同一次 move 里带了内容改动**：只要 change 自己的任一文件在**本 diff range 内**改过内容（哪怕改的是别的位置），
   git 就不再报 `R100`（实测该接入方为 `R068/R069/R070/R090`）⇒ 该 move 不授予 ⇒ 连带两个后果：
   被搬走的 active 目录**以幽灵 id 回到 change 集合**（报「change 目录不存在」+ 缺件），
   且每个这样的文件各报**两条**「受保护路径被写入，但没有结构化解释事件」。

而接入方**没有任何提交顺序能同时满足两边**：`archive-awareness` 认可的时序（`design.md §1.6`）
隐含「本 PR 内不得改动这个 change 自己的已存在文件」，而接入方的 `tasks.md` 必须在实现 PR 内勾选完成——
**勾选就是改动**。

### 实测（同一份 diff，只换包版本；命令与 `gate.yml` 逐字一致）

| 被检 diff | git 改名分 | `@v1`（`ae99256`） | `@main`（`5535d9e`，含 PR #22） |
|---|---|---|---|
| 接入方**真实实现 PR**（33 文件，base 里无此 change） | 全 `A` | ✗ **5 项** | ✗ **1 项** |
| **纯归档 move**（14 文件） | 全 `R100` | ✓（`0 个 change 目录`） | ✓（**`1 个 change 目录`**，认出归档） |
| 接入方**收尾 4 连提交**（16 文件） | 4×`R<100` + 11×`R100` | ✗ 12 项 | ✗ 11 项 |

⇒ PR #22 修好了它针对的两条（`@v1` 那一列 5 项与阶段 B 观测逐条相同，说明复现保真），
但**真实接入路径仍然红**：第一行 `@main` 剩的那 1 项正是 `require_change_for` 误报。

### 为什么设计时没暴露

**witnessloop 自己从未归档过任何 change**——`origin/main` 的 `openspec/changes/` 下 **9 个 change 全在 active**、
**没有 `archive/` 目录**。归档路径只被合成测试跑过，从未 dogfood ⇒ 这个代理指标的代价没被自己踩到。

### ⚠️ 上一版判据里，真正承重的是哪一条（初稿曾搞错，此处写明）

规格里两条否定面曾被读成「承重的安全守卫」，**复核后不成立**：

- `policy.stale_exempt_paths`（`src/witnessloop/policy.py:77`）把 **`archive/**` 整块**列为
  「审阅 revision 之后允许出现」⇒ 一块「审阅后还能改」的暗房**今天就已经存在**
  （任何**已归档** change 的 `proposal/design/tasks` 被改都不判 stale；接入方现有 120 个归档目录全部如此）。
  ⇒ 「放宽 N2 会新开暗房」是**假**的推论——它本来就在。
- 真正承重的是**另一条**：**不得给一个 `base` 里已存在的归档目录凭空授予资格**。
  否则「把 active change 的**单个文件** `git mv` 进别人家归档目录」就能把资格给到目标目录，
  而源 change 因 `archived_sources` 被排除、**静默逃检**（规格的 N6 正是防这个）。

⇒ 本 change **只反转**前一条，**完整保留**后一条。

## 目标

1. **「本次到达的归档 change」改为目录级判定**：
   `archive/<name>/` 在 `base` 里**不存在**、在 `head` 里存在 ⇒ 它就是本次到达的 change
   （两个目标）。
2. **到达方式不设限**：整目录 `git mv` 过来（含本 diff range 内有内容改动）与**直接新建在 `archive/` 下**
   一律认。⇒ 症状 1、2 同时消失。
3. **保留既有的、真正承重的收窄面**（`design.md §2.4`）：`base` 里**已存在**的归档目录
   SHALL NOT 被授予资格；对它的修改 / 删除 SHALL 仍要解释事件；单文件移入既有归档目录 SHALL NOT 授予。
4. **不产生新的绕过面**：归档 target 走与 active change **完全同一套**契约与证据校验
   （必需件、manifest 的 hash/revision 绑定、grill 正文、以及 `code_hits` 触发的
   `building` / `grill-adversarial` 两条硬门）——**到达方式不改变证据门槛**。

## 非目标

- **不收窄 `archive/**` 的 stale 豁免（暗房）**。它是既有口径、与本 change 正交，
  且**放宽 N2 不会使它变差**（它今天就对所有已归档 change 成立）。⇒ 另立 issue 跟踪。
- **不引入签名 / 防伪造**；不改 `check` 的退出码语义。
- **不改 `archive/<date>-<id>` 命名约定**（`archive-awareness` 已由用户裁定「不收紧」）。
- **不给「change ↔ 代码路径」建立归属关系**（本工具从来没有这套映射）。
- **不把「出生即归档」写成推荐流程**：它只是**必须被正确识别**的形态之一。

## 验收

- **症状级**（三条各自可判定，命令见 `design.md §5`）：
  - ① 接入方**真实实现 PR 的 diff**（33 文件、全 `A`、`agent/**` 命中 `require_change_for`）⇒
    不再出现「没有任何 change 目录」，且该 change 按**归档路径**被校验；
  - ② 接入方**收尾 4 连提交**那一份 diff（含 `R068/R069/R070/R090`）⇒ 不再报幽灵 active id、
    不再报那 8 条「受保护写入没有解释事件」；
  - ③ **纯归档 move**（全 `R100`）的行为**逐条不变**（今天绿，修后仍绿；今天认得，修后仍认得）。
- **否定用例（必须照样红 / 不授予）**：`design.md §5.3` 逐条列出，其中**必须保持**的是
  「`base` 里已存在的归档目录被**修改**」（`M`）与「单文件 `git mv` 进**既有**归档目录且目标名不认得源 id」。
- **对称性**：同一个 change 的同一份内容，**放在 active 与放在 `archive/` 下判绿**——
  这对本 change 是核心不变量（到达方式不该影响证据门槛）。
- **回归**：`uv run pytest -q` 全绿（基线见 `design.md §5.2` 的实测数字）。

## 测试策略

TDD。判定面是**两个纯函数**（到达判定、change 集合划分）加三处接线；用例密集在
**「同一动作在 `A` / `R100` / `R<100` / `M` 四种 diff 状态下的对称与不对称」**上——
本 change 的风险不是「改不动」，而是**把豁免面开大**（`archive-awareness` 的 C3 教训：
只让 `_require_change` 闭嘴的实现会让「改了 `src/**` 却零 change 证据」的 PR 变绿）。
⇒ 每条新授予都必须配一条**同等强度的证据门**用例。
