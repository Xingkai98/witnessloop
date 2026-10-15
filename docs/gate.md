# 门禁层数据契约（M1）

> 本文件是 `witnessloop` v1 门禁层的**实现级契约**：字段名、文件名、退出码。
> 依据 `docs/design.md` v0.2 §5.1 / §5.3。设计里没写到文件名一级的细节，
> 在这里落定——审阅时请重点看这些取舍。

## 1. 目标仓里长什么样

`witnessloop init` 写**三个台账产物**（幂等、只增不改、不 auto-commit）**外加一份命令文件**：

```
.witnessloop/policy.json          # 受保护路径 + 必需 artifact + 证据格式
.witnessloop/init-manifest.json   # 创建清单（含 sha256 台账）+ init 前 base ref
.github/workflows/witnessloop.yml # 极薄 caller：uses: <owner>/witnessloop/.../gate.yml@v1
.github/witnessloop-tests.txt     # 测试执行点：一行命令，门禁在与 check 同一个 job 里跑它
```

⚠️ **命令文件的双重身份**（change adopter-test-gate / design D3）：它是**产物**——
`--dry-run` 与产物清单都会列出它（且只列**真会写**的那些），但

- **不进 `init` 台账**（`.witnessloop/init-manifest.json` 的 `created_files` 恒为上面三条）；
- **不进 `desired_files()`**，因而不参与任何一条冲突判定（`initcmd.conflicting_files`）；
- 因此**不被 `uninit` 删除**（`uninitcmd` 只遍历台账条目 ⇒ 它天然看不见该文件）。

理由：`desired_files()` 同时喂**三个**消费者（写盘、台账、**两条冲突判定**），种子一旦进去，
接入方**改过命令之后** plain `init` 就会 exit 1——而「改命令」是**正常用法**（§11）。
代价（刻意接受）：`uninit` 往返**不再逐字节干净**，命令文件留在盘上；不要它就自己删。

写入语义：无 flag 时**只在文件不存在**时写**哨兵** `<<REPLACE-ME>>`（未接线 ⇒ `check` 判红）；
`init --test-command "<cmd>"` **总是覆盖**已有内容；`init --no-tests` 显式**不写**该文件
（并在 policy 里写 `tests.disabled: true`）。三态与判定见 §11。

一个 change 目录（OpenSpec 形状，硬编码，无 spec 适配器）：

```
openspec/changes/<change-id>/
  proposal.md
  design.md
  tasks.md
  specs/<capability>/spec.md      # 能力增量
  reviews/
    grill-review.md               # 报告（阶段名任意）
    grill.manifest.json           # 证据 manifest（必须与报告成对）
    building-review.md
    building.manifest.json
  workflow-events.jsonl           # 结构化解释事件（可选，受保护写入时需要）
```

### 1.1 `init --policy <file>`（自定义 policy）

默认 `init` 只写出厂 policy；目标仓常需定制（例如把交互层目录纳入 `require_change_for`）。
`init --policy <file>` 用**给定文件的内容**作为 policy，其余不变——`init` 仍幂等、只增不改、
不 auto-commit、支持 `--dry-run`。一次写成正确内容 ⇒ policy 是「**新增**」而非「修改」，
天然免解释事件、台账自洽、`uninit` 可回滚（反之，先 `init` 再手改会打破 init-manifest 台账，
`uninit` 因 hash 不符**整批拒删**）。

- **轻校验**：只要求「文件存在 + JSON 根是对象」；schema/字段的**语义**合法性由 `check` 的
  `Policy.from_doc` 兜底——两处各造一套判定会引入漂移面。`--policy` **允许指向仓外路径**
  （定制 seed 不入库，见 README「本仓自身接入」）。
- 已接入后再 `init --policy <与已落地不同>` → **报冲突**并以非零退出（**不**静默忽略）。

## 2. `policy.json`

```json
{
  "schema": "witnessloop/policy@v1",
  "changes_root": "openspec/changes",
  "protected_paths": ["openspec/specs/**", ".witnessloop/**"],
  "require_change_for": ["src/**", "lib/**", "app/**", "apps/**", "packages/**", "server/**", "cmd/**", "internal/**"],
  "required_artifacts": ["proposal.md", "design.md", "tasks.md", "specs", "reviews"],
  "evidence": {
    "review_manifest_glob": "reviews/*.manifest.json",
    "events_file": "workflow-events.jsonl",
    "protected_write_event_types": ["protected_path_write"]
  }
}
```

`protected_paths` / `require_change_for` 是**repo-agnostic 的参数化轴**——
目标仓换成自己的路径（如 `infra/**`）。其余字段缺省时回落到上面的默认值。

`require_change_for`：命中这些 glob 的改动**必须**挂一个 change 目录，否则 `check`
fail 并点名命中的文件。没有它时，`check` 只保证「**如果你**动了 change 目录/受保护
路径，它要齐备」——于是最省事的绕过方式是什么都不建（只改 `src/` 的 PR 直接放行）。
语义细节：

- **缺省**（字段不存在）→ 用出厂默认，老 policy 不会静默失去这条规则；
- 显式写 `[]` → **关掉**这条规则（逃生口）。⚠️ **注意它关掉的不止一条**：`require_change_for` 为空时，
  「改代码必须挂 change」（`_require_change`）、**§9 的 building 门禁**与 **§10 的 grill-adversarial 门禁**
  **三条**一并**静默失效**（实测：`check` 退 0）。
  反过来，若它**没覆盖该仓真实的代码路径**（例如真代码在 `services/**` 而这里只写了 `src/**`），效果相同——**静默通过**。
  这是**声明出来的逃生面**，不是遗漏；接入时请确认它覆盖了你真正的代码目录；
- 默认刻意**不含** `docs/**` / `tests/**`：纯文档、纯测试改动不该被拦。
- 判定看整个 diff（含删除与改名的旧路径），所以「删掉源码」同样算改了代码。

glob 语义：`*` / `?` 不跨 `/`，`**` 跨（含零层，`**/x` 也匹配 `x`）。
不用 `fnmatch`——它的 `*` 跨 `/`，会让「前缀约束」失效。
逐条语义由 `tests/test_paths.py` 钉死（每条都可变异验证）。

归一化边界（design §9 风险 7）：`normalize` 只做 `\` → `/` 与前导 `./` 剥离。
**不做大小写折叠、不展开 `~`**——因为 M1 的输入恒为 git 输出的 posix 相对路径
（大小写敏感、无 `~`）。这条是**声明出来的边界**，不是遗漏。

## 3. `review manifest`（审阅证据的权威件）

```json
{
  "schema": "witnessloop/review-manifest@v1",
  "change_id": "add-retry-policy",
  "stage": "building",
  "reviewer_run_id": "run-…",
  "author_run_id": "run-…",
  "base_sha": "…",
  "head_sha": "…",
  "tasks_hash": "sha256(change/tasks.md)",
  "spec_hash": "sha256(change/specs/ 整棵树)",
  "diff_hash": "informational，不校验内容",
  "report_hash": "sha256(change/<report_path>)",
  "report_path": "reviews/building-review.md"
}
```

- **必需字段**：除 `diff_hash` 外全部（`diff_hash` 是 informational，见 design §5.3）。
- **内容 hash 绑定**：`tasks_hash` / `spec_hash` / `report_hash` 必须等于当前 artifact
  字节的 sha256——这是「证据之间没漂移」的机械证明。
- **目录哈希**：`spec_hash` 覆盖 `specs/` 整棵树，算法 = 对按 posix 相对路径排序的
  `(路径, 内容)` 对做 sha256（跨平台可复现，见 `hashing.sha256_tree`）。
- **revision 绑定**（`base_sha` / `head_sha`，tasks.md D3）：
  1. `base_sha` 与 `head_sha` 的形状必须是 **40 位小写十六进制**（`main` / `HEAD~3`
     这类符号 ref 会被拒——字段名叫 `*_sha` 就该是 sha），且**能解析成本仓的一个提交**
     （乱填 `"0"*40` 同样被拒）；
  2. `head_sha` 必须是本次被检 head 的**祖先**（含相等）；
  3. 从 `head_sha` 到本次被检 head 之间，只允许出现**证据文件**与**本 PR 自己的
     变更**，出现别的即判「**审阅的是旧 revision**」。两个过滤条件缺一不可：
     - **只算本 PR 改过的文件**（`base...head` 的变更集）。被检 head 可能是
       merge commit（`pull_request` 事件下 `actions/checkout` 默认检出 test-merge），
       base 侧顺带进来的改动不算本 PR 漂移。
     - **证据路径 = `.witnessloop/**`、`<changes_root>/*/reviews/**`、
       `<changes_root>/*/workflow-events.jsonl`**（收窄到 change 目录内——
       任意深度的 `reviews/` 目录都算证据会让 `src/reviews/x.py` 变成规避面）。
- **强制 `reviewer_run_id != author_run_id`**：兜底路径下两角色 id **结构性不同**，所以它只挡
  「**显式**把同一个值喂给两个角色」（如只设共享 `WITNESSLOOP_RUN_ID`）——**不**等于「挡忘了另开
  run」；也**不挡蓄意伪造**。兜底 id 是**「审阅目标的指纹」**、非真实 run 身份（见 design §5.2）。
- **每个审阅报告各配一份 manifest（无孤儿报告）**：`reviews/**/*.md` 里**每个**报告
  文件都必须被**某份** manifest 的 `report_path` 引用；否则 `check` 报
  「孤儿报告：`<path>` 未被任何 manifest 绑定」。`manifest build` 因此要**对每个报告
  各跑一次**：

  ```bash
  witnessloop manifest build --change <id> --stage grill \
    --report reviews/grill-review.md …          # → reviews/grill.manifest.json
  witnessloop manifest build --change <id> --stage grill-adversarial \
    --report reviews/grill-adversarial.md …     # → reviews/grill-adversarial.manifest.json
  ```

  判定**只做文件名交叉引用**，**不解析报告正文**。两侧都按**解析后**的路径比对
  （`resolve()` 之后再比），所以 `./`、`//`、`..`、反斜杠字面名、符号链接都不会
  造成误判；`report_path` 的解析/规范化只有**一处实现**
  （`contract.resolve_report_path`，`check` 的 hash 校验、孤儿绑定、`manifest build`
  三处共用）——口径分歧会同时造成漏报与假阳性。多份 manifest 指向同一个报告不额外
  报错（保持简单）；`reviews/` 下没有 `.md` 报告时不报孤儿（那种情况由「报告不存在」
  管）；目录名恰好以 `.md` 结尾**不算报告**。

  **某份 manifest 贡献不了绑定（解析不出 `report_path` / 逃逸），只是它自己少一条**
  ——孤儿判定**照常对其余报告执行**，绝不整体跳过。整体跳过等于给出一份特制 manifest
  就能关掉整条规则的开关（回归审阅 §3.2/§4）。原则：**宁多报，不漏报**。
- `report_path` 解析后必须落在 change 目录内（禁 `../` 逃逸）。
- ⚠️ **报告必须放在 `reviews/` 下**（`gate.md §1` 的布局约定）。放在 change 目录
  根（如 `report_path: "my-report.md"`）虽然能通过 hash 校验，但**不匹配证据
  glob**，于是在 `head_sha..被检 head` 的 delta 里被判 stray，会**额外**报一条
  「审阅的是旧 revision」——诊断上像误报，实际是违反布局约定。
  `tests/test_check_manifest.py::test_report_outside_reviews_is_not_evidence`
  把这条边界钉住了；若日后把 `report_path` 纳入证据判定，该测试会变红，
  届时须同步改本节并评估是否放宽了规避面。

### 3.1 由此推出的提交约定：**先内容，后证据**

一条 manifest 不可能写下**自己所在提交**的 sha（自指），所以「`head_sha` 等于本次被检
revision」在字面上不可满足。上面第 3 条是等价且可满足的写法：**`head_sha` 是最后一个
非证据 revision**。实务上就是：

```bash
git commit -m "内容：change 目录 + 实现代码 + spec 写入"   # ← head_sha 指这里
witnessloop …            # 跑 grill / review-loop，产出报告 + manifest + 事件
git commit -m "证据：reviews/ + workflow-events.jsonl"    # ← check 的被检 head
```

审阅之后**再落任何非证据文件**（哪怕只改 `src/`），下一次 `check` 会报
「审阅的是旧 revision：head_sha=… 之后又改动了非证据文件：…」。
补新的解释事件、补报告则不算——它们本身就是证据。

> **推论：内容与证据必须分属两个提交；单提交 PR 不被支持。**
> 若把内容和证据放进同一个 commit，写 manifest 时 HEAD 还停在改动前的提交上，
> `head_sha` 必然等于那个更早的 revision，于是 `head_sha..被检 head` 之间全是
> 内容文件 → 恒判 stale。这是自指带来的**固有约束**，不是缺陷；本仓用
> `tests/test_check_manifest.py::test_single_commit_pr_is_rejected` 把它钉成契约。
> 若要把单提交变成可行，需要引入 `base_sha`/`head_sha` 之外的第三锚（成本较高）。

### 3.2 怎么产出 manifest：`witnessloop manifest build`

审阅跑完，用这个动词把报告落成 manifest——**它复用 `check` 同一张绑定表
（`constants.HASHED_ARTIFACTS`）与同一个 `hashing.sha256_tree`**，两边不会漂移。

```bash
witnessloop manifest build \
  --root . --change <change-id> --stage <stage> \
  --report reviews/<stage>-review.md \
  --reviewer-run-id <审阅者 run> --author-run-id <作者 run> [--base <ref>]
```

- `head_sha` = 跑 build 时的 HEAD。所以要在**内容提交之后、证据提交之前**跑
  （§3.1）；随后把报告 + manifest 单独提交。
- `base_sha` = 给定 `--base`（缺省与 `check` 用同一套解析）的 sha。
- `tasks_hash` / `spec_hash` / `report_hash` 由 build 算出；`diff_hash` 是
  informational（如实算 `base..head` 的 diff 文本 sha256，`check` 不校验）。
- 写 `reviews/<stage>.manifest.json`。**固定 base 与 revision 时**逐字节可复现
  （同输入覆盖同一文件）、**不 auto-commit**。
- 不合格就**不写出文件**、直接报错：`reviewer_run_id == author_run_id`、
  `report_path` 逃逸出 change 目录、报告不在 `reviews/` 下（把这个坑从
  「CI 里像误报的 stale」变成清楚的即时错误）、缺 `tasks.md`、change 目录不存在、
  仓里没有提交、未接入（exit 3）。
- **归档目标也支持**（change `archive-awareness` / issue #21）：`--change <名字>` 先看
  `<changes_root>/<名字>`，不存在再看 `<changes_root>/archive/<名字>`（**精确**命中，
  **不**按 `*-<id>` 后缀猜）；解析到哪边，`--report` 就相对哪边解析、manifest 就写在哪边
  （`change_id` = **归档目录名**）。两条额外的即时错误：
  - **两处都找不到** ⇒ 报错点名该名字、**不写文件**；若 `archive/` 下有 `*-<名字>` 的候选，
    只**提示**（「归档态要用**目录名**作为 change id」），**不自动认**；
  - `--change archive` ⇒ 明确报「`archive` 是**归档根目录**、不是 change id」（不拦的话它会走
    active 分支、报「缺少必需件 proposal.md」，文案与病因毫无相似之处）。
- ⚠️ **归档后要改写证据** ⇒ 那是**不含该归档 move 的后继 diff**（覆盖 = `M` 不变集路径 ⇒ **每条一条**
  解释事件，见 §5）；**不许**与那个 move 放进同一个 diff（见 §5.1.1 第二条边界）。

## 4. 结构化解释事件（`workflow-events.jsonl`）

一行一个 JSON 对象：

```json
{"schema":"witnessloop/event@v1","event_type":"protected_path_write",
 "change_id":"add-retry-policy","artifact_path":"openspec/specs/retry/spec.md",
 "reason":"…","approved_by":"user:kai"}
```

`artifact_path` 必须是**具体路径**，不接受通配（`*` / `?`）——一条事件只豁免它
点名的那个文件。否则 `artifact_path:"**"` 会成为「一行放行一切」的后门，
连不变集都能被绕开。`reason` / `approved_by` 去空白后必须非空。
事件里的 `change_id` 是 informational，check 不消费它。

**读不出来怎么办**（change `events-readpoint-fix` / issue #12）：文件**解码失败或读不到**时，
`check` 给**一行点名文件**的 finding（`事件文件无法解析：<path> 无法解码|无法读取：…`）——
**不再**表现为工具故障（`witnessloop：内部错误（…）`）。退出码语义不变（仍非 0）。
⚠️ **代价（刻意接受）**：一个坏 events 文件会让**受保护写入那一整块**不再被评估
（`load_all` 是那块的第一句）⇒ 你会**少看到那一块**的 finding（**其它块照常打印**：change 契约、
manifest、grill 正文…都照旧）。**它仍然是红，不是绿**，所以没有绕过面——只是**归因不完整**：
先修 events 再重跑，才知道那块里还剩几条。
**覆盖范围 = active 一层 + 归档一层**（change `archive-awareness` / issue #21）：
`<changes_root>/*/workflow-events.jsonl` 与 `<changes_root>/archive/*/workflow-events.jsonl`。
同一 change 在两处各有一份时**两份都读**、任一条命中即豁免（`covers` 是**存在性**判定，不做去重）。
⚠️ 两条**既有**口径，别读成「只扫真 change 目录」：

- `changes/*/` 的 `*` **也匹配 `archive`** ⇒ `<changes_root>/archive/workflow-events.jsonl`
  （`archive/` **直接下**、不属于任何 change 目录）**会被读**；
- `archive/*/` 的 `*` 匹配**任何**目录名 ⇒ `<changes_root>/archive/notes/workflow-events.jsonl`
  会被当成一个「归档 change 目录」的事件文件。

真正**不被读**的是**再深一层**的（如 `<changes_root>/archive/<name>/sub/workflow-events.jsonl`）——
两条 glob 各自只覆盖一个层级，**不用** `rglob`/`**`（那会多出「谁都能放一份授权文件」的面）。
⚠️ 授权面因此**变大**：事件池的**落点**从「`archive/` 根**一个**路径」扩成「`archive/<任意名>/` **一族**」
（任意名都算，包括永远不会被任何 change 校验的目录）。它**不是新类**——同款手法改前就能用
（`openspec/changes/archive/workflow-events.jsonl` 今天就会被 `changes/*/` 那条 glob 读到；
更一般地，往任意**已存在**的 active change 目录丢一份新 events 文件今天也管用），
而事件本就是**全局解释**、`change_id` 不被消费（见 §7）⇒ 本 change 不改语义，只如实写明放大面。

## 5. 受保护写入的两档规则

| 路径来源 | 新增 (A) | 修改 (M) / 删除 (D) |
|---|---|---|
| `policy.protected_paths`（如 `openspec/specs/**`） | 需解释事件 | 需解释事件 |
| **不变集**（下述 4 条） | **免解释** | 需解释事件 |

不变集（`policy.INVARIANT_PROTECTED_PATHS`，4 条常量封顶，repo policy 移除不掉）：

```
.witnessloop/policy.json
.witnessloop/init-manifest.json
**/workflow-events.jsonl
**/reviews/*.manifest.json
```

**为什么新增免解释**：manifest / 事件文件 / 门禁自身配置的「新增」就是正常工作流。
若新增也要事件，每个正常 PR 都得为自己那份 manifest 写一条解释（自相矛盾），
接入 PR 更会被自己的门禁拦下（鸡生蛋）。**修改或删除**才是要解释的动作。

### 5.1 归档豁免：`<changes_root>/archive/**` 上的**纯改名**免解释

OpenSpec 的归档就是一次 `git mv`（active → `archive/`），而 manifest、事件文件都在
不变集里，改名会被判成「修改受保护路径」——于是每次归档都得手写一条解释事件。
归档是**簿记动作**，不该如此。豁免定义（`contract.is_archive_move`）刻意收窄：

| 动作 | 免解释？ |
|---|---|
| `git mv <changes_root>/<id>/… <changes_root>/archive/<id>/…`（**R100 纯改名**） | ✅ 免 |
| 带走内容改动的移动（R 分数 < 100 / D+A） | ❌ 仍要 |
| 删掉证据文件（如 manifest） | ❌ 仍要 |
| 改 `archive/` 里已有的文件 | ❌ 仍要 |
| active 目录内改名（含改名 manifest） | ❌ 仍要 |
| 把受保护 spec 挪进 `archive/` | ❌ 仍要 |

配套：归档 move 的两端都不计入 **active** change id（否则 `archive` 会被当成一个 change
id 去要 `proposal.md`，而搬走的那个 change 会被报「目录不存在」）；`archive/**` 同时
进 `stale_exempt_paths`（归档不改内容，不该触发「审阅的是旧 revision」）。

#### 5.1.1 归档感知：归档 move 把该 change「归属」回本次 diff（change `archive-awareness` / issue #21）

归档 move **不豁免任何东西**——它只让那个 change **重新成为本次 diff 的 change**，
于是 ①`require_change_for`（§2）不再对「实现 PR 同时归档」误报、
②`manifest build` 能解析归档目标（§3.2）、③`events` 扫得到归档目录（§4）。
判定与 active **同一套**（Q1 拍板 uniform：**接受「纯归档 PR 也会红」**）：

| 动作 | 该 change 进本次 diff？ | 走证据门禁？ |
|---|---|---|
| `git mv <changes_root>/<id>/… → <changes_root>/archive/<name>/…`（**R100**、源在 active、且 `<name>` == `<id>` 或以 `-<id>` 结尾） | ✅（id = **归档目录名**） | ✅ 与 active 同一套（契约 / manifest / grill 正文 / stage 门） |
| **新建** `archive/<name>/…`（无 active 源） | ❌ | —— |
| 改 / 删 `archive/<name>/` 里**已存在**的文件 | ❌ | —— |
| 把 active change 的**单个文件**改入**已存在的**归档目录、而目录名**不认得**源 id | ❌（不授予） | —— |
| 归档 move 的**两端** | —— | 不计入 **active** id |

⚠️ 三条必须知道的边界：

- **归档目录名要认得源 id**（等值、或 `-<id>` 后缀；**不解析日期前缀**）——`archive/<id>` 与
  `archive/<date>-<id>` 都算，**不要求**统一成哪一种。名不认得 ⇒ **不授予** ⇒ 回落到
  「什么都不建」的行为（照样红）。这条挡的是「把某个 active change 的单个文件搬进**别人的**
  归档目录」——那会让资格被凭空授予目标目录、而源 change **静默逃检**。
- **归档 move 必须是纯改名**：**同一个 diff 里不得同时改写被 move 的文件**（含「归档之后、在归档态
  重建 manifest」）——git 会报 `R<100`，于是 ①不授予 ②被搬走的 active 目录**以幽灵 id 回到集合**
  （报「change 目录不存在」）③一次改写要**两条**解释事件（rename 的新旧两半各记一次），
  且幽灵那几条**补事件也消不掉**。推荐顺序（`design.md §1.6`）：**内容 → 在 active 态产证据 → 归档放最后**。
- **归档前产出的 manifest 不必重建**：归档态 target 的 `change_id` **接受两个名字**——归档目录名
  （归档后产出的证据用）与**源 id**（归档**前**产出的证据用，一次改名把两者连起来）。
  少了这条别名，「实现 PR 同时归档」那张 PR 的既有证据会全部判「与目录不符」，
  而唯一的补救（重建）又撞上面那条 ⇒ 顺序上无解。

## 6. 退出码（**按动词分表**——同一数字语义相反）

`check`：

| 码 | 含义 |
|---|---|
| 0 | 通过 |
| 1 | 未通过（契约缺件 / 证据漂移 / **孤儿报告** / **grill 报告正文不完备** / **缺设计对抗轮证据**（§10）/ **缺 building 审阅证据**（§9）/ 受保护写入无解释 / **归档 change 证据缺件**（§5.1.1——归档态与 active **同一套**判定）/ **测试执行点缺失、为空或未接线**（§11）/ base 解析失败） |
| 2 | 用法错误（argparse） |
| 3 | **未接入**——没有 `.witnessloop/policy.json`。fail-closed，绝不静默通过 |

`guard`（本地守卫，见 §8）——**与 `check` 同形状**：

| 码 | 含义 |
|---|---|
| 0 | **放行**（含：写文档豁免 / 推不出 change / 未给路径） |
| 1 | **拦住**——命中 `require_change_for` 且当前 change 的 grill 证据不完备 |
| 2 | 用法错误（argparse） |
| 3 | **未接入**——不拦（本地守卫对未接入的仓无意见） |
| 4 | **内部错误**（未预期异常，由**进程入口**兜底）——**fail-open，不拦**。**只有 `guard` 会用 4** |

⚠️ **`guard` 的「拦住」是 1，不是 2**：2 与「argparse 用法错误」同值 ⇒ **旧版 CLI 不认识
`guard` 子命令**时 argparse 退 2，会被宿主当成 block，把**每个 `Write|Edit` 都拦下**
（fail-open 反转成 fail-closed）。由 `plugin/hooks/guard.sh` 把 **1 → host 的 block（CC 的 2）**。
`3` 在两动词里仍相反：`check` 是「不放行」、`guard` 是「放行」。

⚠️ **`guard` 崩溃绝不等于「拦」**（issue #9）：退出码 **1** 同时是 CPython 未捕获异常的退出码，
若不兜底，`guard` 一崩就会被宿主当成 block ⇒ **误拦每个 `Write|Edit`**。故**进程入口**
（`src/witnessloop/entry.py`，console script 与 `python -m witnessloop` 都走它）捕获未预期异常：
verb 是 `guard` ⇒ **4**（fail-open）；其余 verb ⇒ **1**（`check` = 未通过 = fail-closed；`init`/`uninit`/
`manifest` = 失败）。**该保证只对两个声明入口成立**（console script 与 `python -m witnessloop`）——直接跑 `python -m witnessloop.cli` 绕开兜底，不属承诺入口。入口刻意**不 import `witnessloop` 任何模块**——这样连「`witnessloop.cli` 自身
导入失败」（安装破损）也兜得住。⇒ 「拦」(1) 成为**只由显式判定产生**的退出码。

`base` 解析顺序：`--base` → `WITNESSLOOP_BASE_REF` → `GITHUB_BASE_REF`（→ `origin/<ref>`）
→ `origin/main` \| `main` \| `origin/master` \| `master`。
`head` 解析顺序：`--head` → `WITNESSLOOP_HEAD_REF` → `HEAD`。

## 7. 能力边界（必须诚实转述）

hash 绑定证明**证据之间没漂移**；`reviewer_run_id` / `approved_by` 是自由文本，
v1 不做语义绑定、**不造签名**。因此：**默认只防漂移，不防蓄意伪造**——
agent 手写一行放行事件提交，门禁会绿（这是 design §2 明写的边界，
`tests/test_acceptance.py::test_f2_handwritten_allow_event_is_not_blocked`
把它钉成了契约）。真正的锚是远端 branch protection + required check。

## 8. grill 证据的正文校验（`check`）与本地守卫（`guard`）

**一侧判定、两处接线**——同一个纯函数 `evidence.py`，`check`（事后 / CI）与 `guard`（事前 / 本地）共用
（分两份实现必然漂移：本仓已因 `check` / `manifest build` 各写一套踩过坑，故共用 `constants.HASHED_ARTIFACTS`）。

**判据**（`src/witnessloop/evidence.py`）：`## Confirmed Decisions` **顶层 bullet（含其续行）≥ 3 条**、
**每条块内含 `来源:`**；`## Open Questions`（**逐字标题**）**必须存在**、其每条的 `Q<n>` 都要在
`## User Confirmation` 有对应确认；占位文本（`待确认` 等；**短答复才查强占位**）不算确认。
**块级**——`来源:` 允许只出现在续行（实测：本仓 dogfood 的 `来源:` **全在续行**，任何行级口径命中 0）。

**`## Open Questions` 的候选小节判定**（change `confirm-gate-fail-closed`）：**逐字** `Open Questions`，
或**以 `Open Questions` 结尾**的紧近义标题（反复剥掉尾部括号限定语后匹配——`## Open Questions（收敛后）`、
`## Remaining Open Questions` 算候选；`## Open Questions 汇总`、`## Open questions` **不算**）。
**一个候选都没有 ⇒ 红**，且诊断**列出**报告里含 `Open Questions` 字样的二级标题（全部、排序）——
让修法（改回逐字标题）一步可达，而不是静默跳过。内容判据作用于**全部候选小节的并集**
（同名标题沿用既有的 `setdefault` 合并语义）；**代码围栏内的行不参与小节切分**
（报告里**引用**一段 `## User Confirmation` 示例不再被当成真确认）。
**同一 stage 有多份 manifest 时逐份校验正文**（此前只校验排序第一份 ⇒ 一份合规的**诱饵**就能让
整段正文判据失效）。⚠️ 这道门的**前提**是「`stage=grill` 那份 manifest 绑定的报告**就是**决策记录」：
把真记录绑到别的 stage、给 `stage=grill` 一份合格 stub ⇒ 通过（不在机械面内）。

**`check` 侧**：每个 change 必须有一个 **`stage=<grill_stage>`**（默认 `grill`，`policy.evidence.grill_stage`
可覆写）的 manifest，且其报告正文合格；缺则**红**并点名**现有** stage（拼错可诊断）。
`stage` 因此纳入 manifest **必填字段**（此前「写而不校」）。
⚠️ **对**接入方**是行为变更**：历史无 grill manifest 的 change 会新增一条红；
标题**非逐字**的存量报告也会新增一条红（此前那条判据对它们**整段静默跳过**）。

- **标题非逐字时的补救姿势**：**追加**一个逐字的 `## Open Questions` 小节（把原小节里的
  `Q<n>` 抄进去，或写 `（无）`），**不改审阅者原文**——证据被 `report_hash` 绑着，改正文先撞
  hash 校验；**追加**属新增行，是既有先例。追加后按 §3.1 的顺序**重建那份 manifest**，
  报告与 manifest 一起作为**证据**提交。

**`guard` 侧**：`witnessloop guard --root R --path P [--path P2] [--change ID]`
——写目标命中 `policy.require_change_for` 且**当前 change 的 grill 证据不完备** ⇒ **1（拦）**。

- 当前 change：`--change` → `WITNESSLOOP_CHANGE` → **分支名首段**；**推得的 id 必须命中现存
  **active** change 目录**，否则按「推不出」处理（`fix/login-timeout` 这类分支的首段不是 change 目录）。
- **推不出 / 未给路径 / 写文档 / 未接入 ⇒ 放行**（fail-open）；写文档豁免是**死锁防线**（否则永远产不出证据）。
- **`--path` 传的是文件**（host hook 给的是 `file_path`）。传**目录**（如 `--path src`）不命中 `src/**`
  ⇒ 静默放行（声明的 fail-open 边界）；大小写**不折叠**同理（见 §2 的归一化边界）。
- 逃生口：`WITNESSLOOP_SKIP_GUARD=1`。
- CC hook 随 plugin 分发（`plugin/hooks/`）；**装了 plugin 还要装 CLI**，否则命令非 2 退出 = CC 视为不阻塞 = fail-open。
- **崩溃 / 内部错误 ⇒ 放行**（§6 的 4）：兜底在**进程入口**（`src/witnessloop/entry.py`，见 `docs/adr/0002`），
  当**任何**未预期异常冒到入口（含 `witnessloop.cli` 自身导入失败）⇒ `guard` 退 **4**、绝不退 1。
- **证据文件「读不出」⇒ 归一为 verdict（不再崩溃）**——口径见下。

**证据「读不出」（解码失败）的归宿**（change `guard-crash-exit`；读点归一）：

| 文件 | 归宿 | 为什么 |
|---|---|---|
| `.witnessloop/policy.json` | **放行** | 连受管控范围都读不出 ⇒ **不执行**（与既有「policy 非法 ⇒ 不拦」同归） |
| `review manifest` | **拦 / 红** | 与「manifest **缺失** / **JSON 语法坏**」**逐字同归**（字节坏不得一半拦一半放） |
| grill 报告正文 | **拦 / 红** | 统一口径「**读不出 ⇒ 不可核验 ⇒ 不完备**」 |
| `workflow-events.jsonl`（**active** change 目录） | **红（一行点名文件）** | 归一到 `EventError`（与「不是合法 JSON」同出路）；⚠️ 该读点**与 diff 无关**，坏文件会让**每次** `check` 的**受保护写入那一块**短路（见 §4） |

⚠️ **对**接入方**是行为变更**：损坏的证据文件此前会**崩**（`guard` ⇒ 退 1 被当 block **误拦**；
`check` ⇒ 一行 `witnessloop：内部错误（…）`——⚠️ **不是 traceback**：进程入口 `entry.py` 会兜住它，
这是本句此前的错误说法，已按实测订正）。现在两类都变成**确定性结论**（`guard` 拦 / `check` 干净的红）。
`check` **退出码语义不变**（仍非 0 = 未通过）。
⚠️ **可诊断性小缺口**：`guard` 侧对「**坏** manifest」与「**无** manifest」文案相同（都是「无 stage=grill 的
manifest（现有 stage：…）」）；`check` 侧会**点名**文件（`manifest 无法解析：<file>`）。

## 9. `building` 门禁：实现后独立审阅是硬门（change `building-review-gate`）

**触发**：本次 diff 触及 `policy.require_change_for` 下的路径（= **落了实现**）⇒ 被触及的 change
**必须**有一份 **`stage=<building_stage>`**（默认 `building`，`policy.evidence.building_stage` 可覆写）的
review manifest。缺失 ⇒ **红**并**点名现有 stage**。
（§10 的对抗轮门禁**共用同一条触发**——两者是同一个时点的**两端证据**。）

- **判据只有「证据存在」**（manifest + 其 `report_path` 解析得到的报告）。**不解析报告里的 verdict 文本**——
  `PASS` / `CHANGES_REQUESTED` **不参与任何判定**（与 asterwynd 先例同口径：它的「PASS 硬门」实质是
  「**闭环必须跑过**」）。⇒ 换句话说：**「PASS 不是硬门」这件事没有被本门禁改变**。
- **「审阅必须发生在最终实现之后」是既有能力**：§3 的 revision 绑定（`head_sha` 之后只许证据文件改动）
  已经保证「审完又改代码 ⇒ 判 stale ⇒ 红」。本门禁只补「**必须存在**」那一半。
- **触发用客观的 diff 事实**，**不**用「`tasks.md` 是否全部勾选」——勾选是自声明，**不勾就能绕过**。
- **多 change 同 PR**：本 PR 触及代码 ⇒ 本 PR 触及的**每个** change 都要 building 证据
  （前提是「**一个 PR 推进一个 change**」；要免除就把 change 拆到单独 PR）。**不提供**豁免名单——那就是绕过面。
- **纯文档 / 纯 change 目录改动 ⇒ 不要求**（否则每个提案期的 in-flight change 都会被红）。
- **`guard` 不受影响**：写码**之前**不可能有「实现后」的审阅，强加会**自锁**。
- ⚠️ **别把 `building_stage` 配成与 `grill_stage` 相同**：两处会指向同一份 manifest ⇒ building 门禁**退化**
  （grill 的 manifest 同时充当实现后审阅），等于悄悄关掉本门禁。
- **与 grill 那条共用同一实现**（`evidence.stage_manifest_findings_in_change`，一处实现、两种深度：
  building 只到「存在」为止，grill 再校验报告正文）。

⚠️ **对**接入方**是两条行为变更**：
① 「改了代码但没跑 review-loop」的 PR 从**绿变红**；
② **多 change 同 PR** 时**每个** change 都要 building 证据（此前可以「一个 PR 捎带一个纯文档 change」）。

⚠️ **诚实边界**：本门禁只保证「**有一份可绑定的 manifest 存在**」，**不保证**真跑了一次独立 run——
兜底路径下 `reviewer_run_id ≠ author_run_id` **结构性恒真**（§3），一个 agent 即可自造 manifest 满足它。
即「**证据存在性**机械、**审阅真实性**不机械」。

## 10. `grill-adversarial` 门禁：设计对抗轮是硬门（change `grill-adversarial-gate`）

**触发**：与 §9 **共用同一条判定**——本次 diff 触及 `policy.require_change_for` 下的路径（= **落了实现**）
⇒ 被触及的 change **必须**有一份 **`stage=<grill_adversarial_stage>`**（默认 `grill-adversarial`，
`policy.evidence.grill_adversarial_stage` 可覆写）的 review manifest。缺失 ⇒ **红**并**点名现有 stage**。

它补的是设计环的**中间那一环**：grill 决策记录（§8）与实现后审阅（§9）此前都是硬门，而中间的
**对抗验证轮**（grill 之后、停轮之前）只有自觉——本 change 之前 `grep -rn "grill-adversarial" src/`
在 `src/` 里 **0 处功能性命中**。而这一环恰恰最贵：本仓最近 4 个 change 里，它抓到的**全是设计结论层面**的错
（自相矛盾的决策、被实测证伪的推断、「修正只落一份 artifact」）。

- **为什么触发面与 §9 相同**（而不是「每个 change 都要求」）：这样**一个触发概念**（`code_hits`）就够，
  「提案期 / 纯文档 change 不受这道门约束」这一**可表达**的语义得以保留；若改成无条件，
  那条语义就没了——「只动 change 目录」的场景**只能被空正文报告满足**（见下面 ①③）。
- **判据只有「证据存在」**（manifest + 其 `report_path` 解析得到的报告）。**三条诚实边界**：
  1. **verdict 不参与判定**：`PASS` / `CHANGES_REQUESTED` **都合格**。非 `PASS` 收尾本身是
     `templates/grill.md` 的**规定行为**（轮数封顶 → 交人判断），机械判据区分不了「封顶后交人」与「跑一轮就收工」。
  2. **只保证证据存在、且绑在最终 revision**——**不保证**对抗轮发生在**写码之前**
     （manifest 之间**不做先后比较**；`templates/grill.md` 的写码前硬条件 #2 仍**无机械判据**）。
  3. **报告正文不校验——空文件亦合格**（判据止于「文件存在」）。别把「证据存在即满足」读成「至少有一份**有内容**的报告」。
- **多 change 同 PR / 纯文档不误伤 / 与 grill 共用同一实现**：同 §9（共用 `evidence.stage_manifest_findings_in_change`，
  一处实现、两种深度——对抗轮只到「存在」为止）。
- **`guard`（本地守卫）不受影响，这是一个**已知缺口**：`guard` 仍只查 grill 证据（§8），
  写码前**不**要求对抗轮证据。理由是守卫只覆盖 `Write|Edit`、用 Bash 写文件即可绕过 ⇒ 补上也不消除缺口，
  只会多一条可绕过、且与「停轮确认 → 才写码」时序纠缠的条件。真锚仍是 CI required check。
- ⚠️ **别把 `grill_adversarial_stage` 配成与 `grill_stage`（或 `building_stage`）相同**：两处会指向同一份
  manifest ⇒ 其中一条门禁**退化**（等于悄悄关掉它）。
- ⚠️ **与 asterwynd 的差异（别照抄它的做法）**：asterwynd **有**这道门，但①挂在**归档点**
  （`_check_archived_completion_gate`，只对 `archive/<dir>` 跑）；②判据更窄（`primary != "docs"` ∧
  `DESIGN_TYPES` ∧ 有 spec delta）；③证据形态是**裸文件**（`reviews/grill-adversarial.md` 存在即可）。
  本仓**无 archive 门禁、无 `ChangeType`、`specs/` 恒备**，且**裸报告会被孤儿规则判红**（§3）⇒
  形态**必须**是 manifest；触发面也**必然**与它不同。
  ⚠️ 这里说的「**无 archive 门禁**」指「**不在归档点**跑一道完成度门禁」（asterwynd 的
  `_check_archived_completion_gate` 是那种）；它与 §5.1.1 的**归档感知**不是一回事——
  后者只是让归档 move 把 change 归属回本次 diff、并**照旧**跑本 change 已有的门禁。

⚠️ **对**接入方**是行为变更**：**改了代码**（触及 `require_change_for`）的 PR 现在**必须**有
`stage=grill-adversarial` 的审阅证据（= 跑过设计阶段对抗验证），**否则红**。**没有过渡开关**
（开关 = 静默绕过面）。

## 11. 测试执行点：接入方的测试进 CI（change adopter-test-gate / issue #4）

**背景**：`init` 写的 caller workflow 只跑 `witnessloop check` ⇒ **接入方自己的测试没有任何自动
执行点**（实测：M3 acid test 那条真实 PR 的 job 列表只有 `gate / check`，pytest 一次都没跑）。
本 change 交付**机械**版本：**没有测试执行点的仓会被拦住**，测试失败的 PR **合不了**
（⚠️ 这只保证「执行点存在且已接线」，**不保证**它跑的是真测试——四条诚实边界见 §11.3）。

**形态**（design D1 甲：命令文件 + `gate.yml` 读它）：

- `init` 写 `.github/witnessloop-tests.txt`（内容 = **一行 shell**）；`--test-command` **总是覆盖**。
- `gate.yml` 新增一步 `adopter tests`，与 `check` **同一个 job**（`if: ${{ !cancelled() }}`）：
  **文件缺失 _或_ 内容含哨兵 ⇒ 跳过**；否则 `sh -c "$(cat <文件>)"`。命令失败 ⇒ job 失败 ⇒
  **合不了**（required 粒度是 job ⇒ 接入方**不需要新增**任何平台操作）。
  ⚠️ 这只保证「命令被执行了」，**不保证**它是真测试（见下面的边界 ①）。
- 测试步骤排在 **`check` 之后**：门禁红的时候**最需要**测试反馈（一次 CI 里同时看到「缺必需件」
  与 pytest 失败明细）；用 `!cancelled()` 而不是 `always()` 是为了**run 被取消时不再跑一遍**
  （曾有说法称 `always()` 会「掩蔽」`check` 的失败——**实测为假**：失败步骤 + 后续 `skipped`
  步骤 ⇒ job 结论仍 `failure`；真正的掩蔽开关是 `continue-on-error`）。

### 11.1 `check` 侧的三条判据（**零依赖**）

在策略**声明了执行点**的前提下，`check` 要求「**① 文件存在 ② 去空白后非空 ③ 不含未替换哨兵**」。
判定只做**文件存在与字符串包含**检查：**不解析 YAML、不执行**该命令（执行是门禁那一步的职责）。

| 命令文件的状态 | `check` | 门禁那一步 |
|---|---|---|
| 不存在 | **红**（点名路径） | 跳过 |
| 空 / 纯空白 | **红**（`测试执行点为空（未接线）`） | `sh -c ""` ⇒ exit 0 |
| 含未替换哨兵 | **红** | 跳过 |
| 已接线 | 绿 | 执行命令 |

⚠️ **空文件那一态必须判**：只判「存在 + 无哨兵」时，空文件会让 `check` 判绿 **且** 门禁
`sh -c ""` 退 0 ⇒ 「有执行点、门禁跑了、required 绿、测试一个没跑」——正是 issue #4 的形态
外加一枚绿勾。**所以「空 ⇒ 红」只能由 `check` 给**，门禁那一步给不了。

哨兵与路径是**子串口径**：`check` 判「文件内容里含哨兵串」，门禁用同一个常量做 `case` 匹配——
两侧**必须同源**（`constants.ADOPTER_TESTS_PATH` / `ADOPTER_TESTS_SENTINEL`，
`tests/test_gate_workflow.py` 钉住三处逐字一致），否则会出现「`check` 判红、门禁却静默跳过」。

### 11.2 策略语义：**缺省 ⇒ 声明**，唯一的 opt-out 是 `tests.disabled: true`

- **字段缺省 ⇒ 声明**（用默认路径判）——与 `require_change_for` 同一条既有惯例
  （§2：保护性默认，别让老 policy 静默失去这条规则）。⇒ **已接入的仓会被立刻判**；
  补文件的迁移步骤见 README 的接入段。
- **唯一的 opt-out 字面是布尔 `tests.disabled: true`**（`init --no-tests` 写它）。
  `""` / `null` / `false` **都不是** opt-out：`Policy.from_doc` 沿既有惯例用 `or DEFAULT`
  （falsy 即回落），所以这两个字段只认布尔真。
- ⚠️ 出厂 policy doc **不物化** `tests` 键（`default_policy_doc()` 里没有它）——物化会让
  **已接入的仓**跑 plain `init` 时因「本次期望 ≠ 磁盘」命中冲突分支 **exit 1**。
- ⚠️ **`tests.disabled` 只关 §11.1 那条判定，不关门禁那一步**：门禁只看「文件在不在 /
  含不含哨兵」，与 policy **正交**。想「连跑都别跑」要**删掉命令文件**（那一步会跳过）。
- **已接入仓的 opt-out 摩擦（两条，都是实测）**：① `--no-tests` 是**接入期**的 flag——已接入且
  policy 还是出厂默认的仓给它会**报冲突退 1**（「本次期望 ≠ 磁盘」；只有 policy 已经是
  `tests.disabled: true` 时 `init --no-tests` 才幂等 exit 0）⇒ 已接入仓的 opt-out 走改
  `.witnessloop/policy.json`，而它是不变集且状态是 `M` ⇒ **每次都要写一条
  `protected_path_write` 解释事件**（§5）；② 改完 policy 之后 plain `init` 会因「本次期望 ≠
  磁盘」**exit 1**（直到你再带 `--no-tests`）——任何定制 policy 都如此，不是本字段独有。

### 11.3 诚实边界（README 有同口径的四条）

① `check` 只保证「**有一个已接线的执行点**」——**不保证**它真跑过，也**不保证**它跑的是真测试：
`|| true`、`--collect-only`、一行 `# TODO` 注释、甚至 `true` / `:` 都能骗过存在性判定
（§11.1 的第三条判据只堵**意外**写出来的空文件——「写了个占位注释」不在它的射程里）。
「真跑了」由**平台侧 required check** 保证。
② **PR 可以改掉自己的命令文件 / CI 配置**（`.github/workflows/**` 不在保护路径、
`required_approving_review_count: 0`）而 required check 依旧绿。
③ 测试命令是**任意代码**，会在每个 PR（含 **fork PR**）的 runner 上执行。
④ **能力天花板**：走本执行点意味着测试跑在**别人的 job** 里——只有 `contents: read` 权限
（reusable workflow 的权限不能超出 caller），**没有 `services:`、不能加自己的 `uses:` 步骤、
不能上 matrix/缓存**，命令只能是**一行 shell**。需要这些能力的仓应当改用**自己的 workflow**
（代价：自己再勾一次 required）。**把「同 job」说成普遍更优即为过度承诺。**
