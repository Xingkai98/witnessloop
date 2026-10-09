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
- 显式写 `[]` → **关掉**这条规则（逃生口）；
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
- **强制 `reviewer_run_id != author_run_id`**：挡「忘了另开 run」，**不挡蓄意**。
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

## 6. `check` 的退出码

| 码 | 含义 |
|---|---|
| 0 | 通过 |
| 1 | 未通过（契约缺件 / 证据漂移 / 受保护写入无解释 / base 解析失败） |
| 2 | 用法错误（argparse） |
| 3 | **未接入**——没有 `.witnessloop/policy.json`。fail-closed，绝不静默通过 |

`base` 解析顺序：`--base` → `WITNESSLOOP_BASE_REF` → `GITHUB_BASE_REF`（→ `origin/<ref>`）
→ `origin/main` \| `main` \| `origin/master` \| `master`。
`head` 解析顺序：`--head` → `WITNESSLOOP_HEAD_REF` → `HEAD`。

## 7. 能力边界（必须诚实转述）

hash 绑定证明**证据之间没漂移**；`reviewer_run_id` / `approved_by` 是自由文本，
v1 不做语义绑定、**不造签名**。因此：**默认只防漂移，不防蓄意伪造**——
agent 手写一行放行事件提交，门禁会绿（这是 design §2 明写的边界，
`tests/test_acceptance.py::test_f2_handwritten_allow_event_is_not_blocked`
把它钉成了契约）。真正的锚是远端 branch protection + required check。
