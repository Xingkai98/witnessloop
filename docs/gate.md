# 门禁层数据契约（M1）

> 本文件是 `witnessloop` v1 门禁层的**实现级契约**：字段名、文件名、退出码。
> 依据 `docs/design.md` v0.2 §5.1 / §5.3。设计里没写到文件名一级的细节，
> 在这里落定——审阅时请重点看这些取舍。

## 1. 目标仓里长什么样

`witnessloop init` 只写三个文件（幂等、只增不改、不 auto-commit）：

```
.witnessloop/policy.json          # 受保护路径 + 必需 artifact + 证据格式
.witnessloop/init-manifest.json   # 创建清单（含 sha256 台账）+ init 前 base ref
.github/workflows/witnessloop.yml # 极薄 caller：uses: <owner>/witnessloop/.../gate.yml@v1
```

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
  「改代码必须挂 change」（`_require_change`）**与本节的 building 门禁**一并**静默失效**（实测：`check` 退 0）。
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
⚠️ **覆盖范围是 active change 目录**：`archive/**` 下的 events 文件**既不会被读、也不提供豁免**
（既有行为）。

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

配套：归档 move 的两端都不计入 active change id（否则 `archive` 会被当成一个 change
id 去要 `proposal.md`，而搬走的那个 change 会被报「目录不存在」）；`archive/**` 同时
进 `stale_exempt_paths`（归档不改内容，不该触发「审阅的是旧 revision」）。

## 6. 退出码（**按动词分表**——同一数字语义相反）

`check`：

| 码 | 含义 |
|---|---|
| 0 | 通过 |
| 1 | 未通过（契约缺件 / 证据漂移 / **孤儿报告** / **grill 报告正文不完备** / **缺 building 审阅证据** / 受保护写入无解释 / base 解析失败） |
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
**每条块内含 `来源:`**；`## Open Questions` 每条的 `Q<n>` 都要在 `## User Confirmation` 有对应确认；
占位文本（`待确认` 等；**短答复才查强占位**）不算确认。
**块级**——`来源:` 允许只出现在续行（实测：本仓 dogfood 的 `来源:` **全在续行**，任何行级口径命中 0）。

**`check` 侧**：每个 change 必须有一个 **`stage=<grill_stage>`**（默认 `grill`，`policy.evidence.grill_stage`
可覆写）的 manifest，且其报告正文合格；缺则**红**并点名**现有** stage（拼错可诊断）。
`stage` 因此纳入 manifest **必填字段**（此前「写而不校」）。
⚠️ **对**接入方**是行为变更**：历史无 grill manifest 的 change 会新增一条红。

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
