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
  "required_artifacts": ["proposal.md", "design.md", "tasks.md", "specs", "reviews"],
  "evidence": {
    "review_manifest_glob": "reviews/*.manifest.json",
    "events_file": "workflow-events.jsonl",
    "protected_write_event_types": ["protected_path_write"]
  }
}
```

`protected_paths` 是**repo-agnostic 的参数化轴**——目标仓加自己的路径（如 `infra/**`）。
所有字段缺省时回落到上面的默认值。

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
  1. `base_sha` 与 `head_sha` 都必须**能解析成本仓的一个提交**（乱填 `"0"*40` 会被拒）；
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
