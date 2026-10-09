Verdict: CHANGES_REQUESTED

> 审阅者：**R2，全新零记忆 reviewer**。只读源码 + 自造临时 git 仓复现 + `PYTHONPATH` 隔离的变异测试；
> 未修改任何源码/测试/配置（唯一写入的文件就是本报告）。
> 基线：`git diff ecbebc0..mvp-m1/2026-10-09`（6 个修复提交）、`docs/tasks.md` D3、`docs/design.md` v0.2、`docs/gate.md`。
> 复核命令：`export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q` → **146 passed in 5.68s**（与自述一致）。

**结论摘要**：R1 的两个 MUST-FIX（改名外逃、`uninit` 路径逃逸）**确实被堵住**——我分别用「修复前代码 vs 修复后代码」
在同一份伪造输入上实测，退出码从 `0 → 1` / `异常删除+崩溃 → 安全拒绝`，且两个 MUST-FIX 的新增回归测试在变异下**确实变红**。
`test_paths.py` 也真实钉住了 glob 语义（M10/M11 变异均红）。R1 §7 的 Q1–Q5 全部落地。
**但 D3 真绑定（Q1 的修法）引入了一个会在真实 CI 里误报的回归**：当被检 head 是 **merge commit**——
而这正是 `pull_request` 事件下 `actions/checkout` 的默认检出对象、也是 `gate.yml` 传给 `--head` 的东西——
只要 base 分支在开分支后前进过，门禁就会把一个**与本次 PR 无关的 base 侧文件**误判成
「审阅的是旧 revision：…之后又改动了非证据文件」，从而**拦下合法 PR**。这条我实测复现（见 §3-1），
是本次唯一阻塞项。其余为低severity 观察。

---

## 1. 实际运行结果

```
$ export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q
146 passed in 5.68s
```

无跳过、无 xfail。计数与提交自述一致，但下面的结论**全部**用我自己的临时仓与变异重跑过，未采信任何自述。

### 1.1 复现环境与「venv 拷贝坑」的规避

R1 §1.1 记录的坑真实存在：仓库 `.venv/.../site-packages/_editable_impl_witnessloop.pth` 的内容是
**绝对路径** `/home/happy/witnessloop/src`——`cp -r` 仓库后副本里测的是原件。我全程用
`uv run --project /home/happy/witnessloop … python -m witnessloop`（venv editable → 本仓 `src`）跑真实 CLI，
用 `PYTHONPATH=<副本>/src` 强制副本源码跑变异，并用一次**预期必红**的变异（`is_within → 恒 True`）先自检基准可信。

另注：`/home/happy/.local/bin/witnessloop` 是 `uv tool` 装的一份**拷贝**（非 editable）。
我 `diff -r` 过它的 `.py` 与仓库 `src` **逐字节相同**（只有 `.pyc` 缓存不同），所以 CLI 行为与本仓源码一致；
但提醒后续审阅者：**跑 `witnessloop` 前先确认这份拷贝没落后于源码**。

---

## 2. R1 两个 MUST-FIX 的独立复现结论

### I-1 改名外逃（`git mv` 受保护文件出保护区）

临时仓：main 上放 `openspec/specs/retry/spec.md` → `init` → 建 feature → `git mv` 到 `src/moved-spec.md` → commit。
`git diff --name-status --find-renames main...HEAD` 给出 `R100  openspec/specs/retry/spec.md  src/moved-spec.md`。

| 代码版本 | 命令 | 退出码 | 输出要点 |
|---|---|---|---|
| 修复前（`git archive ecbebc0` 重建） | `check --base main --head HEAD` | **0** | `check：通过 ✓`（放行） |
| 修复后（HEAD） | 同上 | **1** | `1. openspec/specs/retry/spec.md：受保护路径被写入，但没有结构化解释事件…` |

**结论：真堵住了**，且**点名的是旧路径**（`openspec/specs/retry/spec.md`），不是新路径。修复逻辑
（`checkcmd.py:113-118` 把 `old_path` 也当作一条 `status="D"` 的待解释目标）与「改名 = 对旧路径的删除」一致。

### I-2 `uninit` 路径逃逸

临时仓：伪造 `.witnessloop/init-manifest.json`，含两条越界条目——`path:"../secret.txt"`（相对逃逸）
与 `path:"/tmp/.../abs-secret.txt"`（绝对路径）。

| 代码版本 | `secret.txt` | `abs-secret.txt` | 退出码 | 崩溃? |
|---|---|---|---|---|
| 修复前（`ecbebc0`） | **被删** | 保留 | 1 | **是**：`ValueError: '…/abs-secret.txt' is not in the subpath of '…/repo'`（未捕获栈回溯） |
| 修复后（HEAD） | 保留 | 保留 | **1** | 否 |

修复后 stderr：`uninit：台账里有越界路径（仓根之外），拒绝执行：` + 逐条 `! … 不在仓根 … 之内` + `整批未删除`。
**结论：真堵住了**——越界整批拒绝（非零退出）、仓外文件均在、不崩溃。`uninitcmd.py:50-52` 的 containment 守卫 +
`:64-69` 的整批拒绝路径都生效。

---

## 3. Issues

### 3-1（MUST-FIX，本轮的阻塞项）D3 真绑定在 **merge commit** 下误报，会拦下合法 PR

**根因链**：
- `checkcmd.py:57`：`checked_head = gitutil.rev_parse(root, head) or head`——把「被检 head」当成了本次审阅要追溯到的终点。
- `contract.py:177`：`delta = gitutil.diff_names(root, head_sha, checked_head)`——`gitutil.diff_names` 是 **两点** diff
  `head_sha..checked_head`（`gitutil.py:53-60`），**比较的是两棵树的快照差**。
- `.github/workflows/gate.yml:52`：`witnessloop check --root . --base "$BASE" --head HEAD`。
  在 `pull_request` 事件下，`actions/checkout@v4`（未指定 `ref`）**默认检出 PR 的 test-merge commit**
  （`refs/pull/N/merge` = base tip 与 PR head 的合并）。于是 `checked_head` 就是那个 merge commit。

当 base 分支在开分支后**前进过**（这是活跃仓的常态），merge commit 的树里**包含 base 侧的改动**，
而 `head_sha`（内容提交）的树里没有。两点 diff `head_sha..merge` 于是把 **base 侧独有的文件**也算进 `delta`，
`contract.py:182-186` 判定它「不是证据 → stray」→ 报 `审阅的是旧 revision`。

**复现（真实跑通，exit 1）**：main 上 `init`(=B0，`89272d2`) → feature：内容提交 C(`e36047d`) → 证据提交 E(`899c781`)；
回 main 推 B2(`16f7a9c`)（只改 `src/other.py`）→ feature 上 `git merge main`（生成 merge commit M=`9e7ca2d`）：

```
$ witnessloop check --root . --base main --head HEAD      # HEAD = M（= actions/checkout 检出的 merge commit）
check：未通过 ✗（1 项）
  1. openspec/changes/add-x/reviews/building.manifest.json：
     审阅的是旧 revision：head_sha=e36047d… 之后又改动了非证据文件：src/other.py
EXIT=1
```

`src/other.py` 是**只在 base 侧**改的、与本次 PR 无关的文件，却被判成「PR 审阅后又动了代码」。
**控制组**：main 不前进、直接在 E 上 `check` → `通过 ✓`（exit 0）。即误报的触发条件就是「被检 head 是 merge commit 且 base 前进过」。

**影响**：门禁在它最主要的部署形态（GitHub `pull_request`）下会**拒绝合法 PR**。团队遇到莫名红灯后
最可能的反应是关掉 required check——正好击穿本工具的存在意义。设计文档 `gate.md §3.1` 只写了「先内容后证据」的提交约定，
**没有声明**「被检 head 不能是 merge commit」这一前提，所以这是**未声明的**陷阱，而非已知取舍。

**修法建议（择一，均小改）**：
- (a) 在 `_check_git_span` 里把 `stray` 与**本次 PR 自身的变更集**求交——即只把「既在 `head_sha..checked_head`、
  又在 `base...checked_head` 里」的文件算 stale。base 侧独有文件不在 PR 变更集里，自动被排除。
  `checkcmd.run` 已经算好了 `changes`，把它（或其路径集）传进去即可。
- (b) 换用「只看属于 PR 的提交」：`git log --no-merges head_sha..checked_head`，或 `git rev-list head_sha..checked_head --not <base>`，
  取这些提交改动的文件。等价效果，但要额外传 base。
- (c) 至少：`gate.yml` 显式 `ref: ${{ github.event.pull_request.head.sha }}`（检出头而非 test-merge），
  **并在 `gate.md §3.1` 写明「被检 head 必须是 PR head、不能是 merge commit」**。这条只堵住 CI 默认路径，
  堵不住「PR 分支自己 merge 了 base」（同一 merge commit 形态），所以建议 (a)/(b) 为主、(c) 为辅。

### 3-2（SHOULD）「先内容、后证据」两提交约定本身，让**单提交 PR 永远无法通过**

`gate.md §3.1` 已诚实说明：manifest 不能写下自己所在提交的 sha（自指）。其可满足的等价写法是
「`head_sha` = 最后一个非证据 revision」。推论：若作者把**内容与证据放在同一个 commit**（对 agent 来说是很自然的
「一次写完、一次提交」），写 manifest 时 HEAD 还停在**改动前**的提交上，`head_sha` 必然等于那个更早的 revision，
于是 `delta(head_sha, checked_head)` 里全是内容文件 → 恒判 stale。换句话说，**本约定强制两次提交**，
单提交在字面上无法表达「我审的就是这个提交」。这是自指带来的固有约束、已文档化，属可接受取舍；
但它叠加 3-1 的 merge 误报后，会让「先内容后证据 + 让 PR 跟上主干」的正常流程双双踩雷。建议在 `gate.md §3.1`
补一句「内容与证据必须分属两个提交；单提交 PR 不被支持」，并优先修 3-1。

### 3-3（SHOULD/NIT）证据路径 `**/reviews/**` 过宽，可作 stale 规避面

`constants.py:38-42` 的 `EVIDENCE_PATH_PATTERNS` 里 `**/reviews/**` 匹配**任意深度**的 `reviews/` 目录。
用户可在审阅后把非证据内容塞进任意 `reviews/` 目录（如 `src/reviews/x.py`），`_check_git_span` 会当它是证据、不计入 stray。
`**/reviews/**`（而非仅 change 目录下的 reviews）是为了兼容报告位置，属宽放；但既然 D3 的目的是「防审阅后漂移」，
把范围收紧到「change 目录内 + 已知证据后缀」会更贴合意图。低危，可与 3-1 一并考虑。

### 3-4（NIT）`events.covers` 里的通配拒绝是「冗余且无测试钉住」的一行

`events.py:80-82`：
```python
if any(ch in event.artifact_path for ch in GLOB_METACHARACTERS):
    return False
return event.artifact_path == pathutil.normalize(artifact_path)
```
末行已是**相等**比较，`**` / `openspec/specs/**` 这类通配本就无法「等于」某个具体路径——安全属性由**相等**保证，
这一行只改变一种边缘行为：**文件名里字面含 `*`/`?`**（Linux 允许）时，一条点名该字面路径的合法事件会被拒。
变异验证：**删掉这一行 → 146 passed（存活）**，无测试会红。也就是说「一行 `**` 放行一切」这个洞**确实被相等比较堵死**
（我有更强变异佐证，见 §4 的 M-events-revert：退回旧 glob 实现 → 2 红），但这一行本身是**冗余的死防线**，
要么删除、要么补一条「字面含 `*` 的路径也应能点名」或「含通配的事件被拒」的定向测试。低危。

### 3-5（NIT）`paths.is_within` 用 `resolve()` 跟随符号链接——保守但正确，非 bug

`paths.py:60-71` 的 `is_within` 对双方都 `resolve()`（展开 `..` 与符号链接）。实测语义矩阵（真实文件系统 + 软链）：

| 场景 | 结果 | 期望 |
|---|---|---|
| 仓内普通文件 | 界内 | ✓ |
| 软链→**仓外** | 界**外**（拒绝） | ✓（正是要拦的逃逸） |
| 软链→仓内、但在 change 目录**之外**（作 report_path） | 界外（拒绝） | ✓（report 必须落在 change 目录内） |
| `../` 逃逸、绝对路径（仓外） | 界外（拒绝） | ✓ |
| `--root` 本身是软链 | 与直接跑结果一致（`checkcmd.run` 入口已 `resolve`） | ✓ |

结论：**只有指向仓外/越出 change 目录的软链会被拒**，而这恰是 fail-closed 想拒的。存在一处**语义不一致**：
`is_within` 跟随软链（判定目标是仓外），而 `uninitcmd.py:92` 的 `unlink` **只删链接本身、不删目标**——即守卫比实际操作更严，
会拒掉一个「删掉也无害的仓内链接」指向仓外的情形。属**过度保守但安全**，不建议现在改行为（改成 `lstat` 语义会削弱逃逸防护）。
记为 NIT，不阻塞。

### 3-6（NIT）`base_sha`/`head_sha` 只校验「可解析成本仓提交」，不校验 sha 形状

`contract._check_git_span`（`contract.py:149-164`）用 `rev_parse(ref^{commit})` 判「是不是本仓提交」。
`rev_parse` 接受**任意 ref 表达式**（`main`、`HEAD~3`、tag…）——字段名是 `*_sha` 却接受符号 ref。
危害极低（能解析就是对检得动的提交），但与字段语义/`gate.md §3`「sha」措辞略松。可选：加一条 `^[0-9a-f]{40}$` 形状检查。

---

## 4. 逐条修复核验表 + 变异证据

方法：`cp -r src tests pyproject.toml .github` 到 `/tmp/wl-mut/base`（**不带 `.venv`**），每次从 base 复制→改坏→
`PYTHONPATH=<run>/src uv run … pytest -q`。基准（未变异副本）**146 passed**；自检变异 `is_within→恒 True` **7 failed**（基准可信）。

| R1 项 | 修复落点 | 我做的变异（改坏对应实现） | 结果 | 判定 |
|---|---|---|---|---|
| I-1 改名外逃 | `checkcmd.py:113-118`（`old_path` 计为 `D`） | 去掉 `if change.old_path:` 分支 | **1 failed**（`test_renaming_a_protected_file_out_of_the_area_is_rejected`） | ✅ 真钉住 |
| I-2 uninit 逃逸 | `uninitcmd.py:50-52,64-69` | 去掉 `is_within` 守卫（`if False`） | **3 failed**（越界/绝对路径/无 sha 三条） | ✅ 真钉住 |
| I-3 D3 绑定 | `contract.py:133-195` | `_check_git_span` 整段禁用（`pass`） | **4 failed**（真实 revision ×2 + 祖先 + stale） | ✅ 真钉住（但见 3-1 误报） |
| I-4 glob 语义 | 新增 `tests/test_paths.py` | M10 `"[^/]*"→".*"`（`*` 跨 `/`） | **3 failed** | ✅ 真钉住 |
| I-4 | 同上 | M11 `"(?:.*/)?"→"(?:.*/)"`（`**/` 需斜杠） | **5 failed** | ✅ 真钉住 |
| I-6 事件通配后门 | `events.py:80-82` + 相等比较 | **M-events-revert**：退回旧 `matches() or ==` 实现 | **2 failed**（`test_catch_all_event…` / `test_glob_event…`） | ✅ 真钉住 |
| I-6（防线的防线） | `events.py:80` 单独那行 | 只删通配拒绝那一行 | **0 failed（存活）** | ⚠️ 冗余/无测试（NIT 3-4） |
| （纵深防御） | `uninitcmd.py:107` `_prune` 的 containment | 删掉该守卫 | **0 failed（存活）** | ⚠️ 无测试；但越界条目已在上游整批拒绝，属可接受的 defense-in-depth |

R1 §7 的停轮问题：**Q1** 选 (a) 修实现（`contract._check_git_span`）+ 同步 `gate.md §3`，与 `tasks.md D3` 口径一致；
**Q2** 改名按删除处理（已修）；**Q3** 加 containment（已修）；**Q4** 补 `test_paths.py`（已补，且真钉住）；
**Q5** 补 `ci.yml` 自测（已补：`uv run pytest -q` + wheel 冒烟）。**全部落地**。

---

## 5. 回归测试真实性

- `tests/test_paths.py`（新，180 行）：不是空转——M10/M11 两个针对性变异都如实变红，覆盖 `*`/`?` 不跨 `/`、
  `**` 零层/中间层、锚定、前缀约束、归一化边界（含 `lstrip("./")` 回归）、`is_within` 矩阵。**真保护**。
- 两个 MUST-FIX 的新增测试（`test_renaming_a_protected_file_out_of_the_area_is_rejected`、
  `test_uninit_refuses_paths_outside_the_repo` / `…absolute_paths_without_crashing` / `…escaping_entry_even_without_sha`）：
  对应实现被改坏后均变红，**真保护**。
- 测试脚手架改造（`helpers.py` 用真实 `base_sha`/`head_sha` + `commit_content`/`commit_evidence` 两提交）没有削弱旧断言：
  旧用例是**适配**新约定（把 `write_*+commit_all` 换成 `commit_content/commit_evidence`），断言文本基本原样保留。
  R1 §1.3 指出的「假 base/head（`0`×40 / `1`×40）也绿」已被 `helpers.py:101-102` 改成真实 sha 并加了两条负例测试钉死。
- **盲区**：merge-commit 形态**无任何测试覆盖**（`check` 的测法恒为 feature 上的两点/三点、head 从不是 merge commit），
  这正是 3-1 误报能溜过 146 个测试的原因。修 3-1 时应补一条「base 前进 + merge commit 作 head → 应**通过**」的回归测试。

---

## 6. 停轮问题（需人拍板）

**Q1（阻塞，对应 3-1）D3 真绑定在 merge-commit 下误报，怎么修？**
现状：`pull_request` + base 前进 = 门禁拦合法 PR（我实测 exit 1，点的是 base 侧文件）。
请拍板 (a) 让 `stray` 与 PR 自身变更集求交（推荐，改动最小、语义最贴「本 PR 是否 stale」）、
(b) 改用 `git rev-list … --not base` 只取 PR 提交、或 (c) 仅改 `gate.yml` 检出头 + 文档声明。
我倾向 **(a) 为主、(c) 为安全垫**：单靠 (c) 堵不住「PR 分支自己 merge base」。

**Q2（对应 3-2）是否接受「单提交 PR 不支持」？**
若接受，请在 `gate.md §3.1` 显式写明；若不接受，需要另想一条不依赖自指的绑定方式（如引入 `base_sha`+`head_sha`
之外的第三锚），成本较高，建议 M1 先文档化。

**Q3（对应 3-3/3-4/3-5/3-6）这些低危项是否本轮处理？**
我的建议：3-4（删冗余行或补定向测试）、3-6（sha 形状校验）**顺手做**；3-3、3-5 留 M2 并在 `gate.md` 标注边界即可。

---

## 7. 复现清单（可照跑）

```bash
export PATH=/home/happy/.local/bin:$PATH
cd /home/happy/witnessloop && uv run pytest -q                       # 146 passed

# 跑真实 CLI（venv editable 指向本仓 src）：
WV() { uv run --project /home/happy/witnessloop --quiet python -m witnessloop "$@"; }

# I-1 改名外逃：main 建 openspec/specs/retry/spec.md → init → feature → git mv 到 src/x.md → commit
#   WV init --root .; git add -A; git commit; git checkout -b feature; mkdir src; git mv <spec> src/x.md;
#   git add -A; git commit; WV check --root . --base main --head HEAD   # 修复后 exit 1，点名旧路径
#   （对修复前代码：git archive ecbebc0 src | tar -x -C /tmp/wl-old; PYTHONPATH=/tmp/wl-old/src … → exit 0）

# I-2 uninit 逃逸：伪造 .witnessloop/init-manifest.json 含 "../secret.txt" 与绝对路径
#   WV uninit --root .        # 修复后 exit 1、仓外文件在、无 Traceback
#   （修复前：真删 ../secret.txt 且绝对路径抛未捕获 ValueError）

# 3-1 merge-commit 误报：
#   内容提交 C → 证据提交 E（manifest.head_sha=C） → 回 main 推 B2（只改 src/other.py）
#   → feature: git merge main（得 merge commit M） → WV check --root . --base main --head HEAD
#   → 误报 "审阅的是旧 revision … src/other.py"，exit 1

# 变异（PYTHONPATH 强制副本源码，先跑 is_within→True 自检必红）：
#   cp -r src tests pyproject.toml .github /tmp/wl-mut/base   # 不带 .venv
#   M10 paths.py:41 "[^/]*"→".*" ; M11 paths.py:35 "(?:.*/)?"→"(?:.*/)" ;
#   M-rename checkcmd.py:115 去 old_path ; M-uninit uninitcmd.py:50 去守卫 ;
#   M-D3 contract.py:129 禁用 _check_git_span ; M-events-revert events.py:82 退回 glob
```

**证据文件**：`src/witnessloop/{paths,checkcmd,contract,uninitcmd,events,gitutil}.py`、
`tests/{test_paths,test_check_protected,test_check_manifest,test_uninit}.py`、`docs/gate.md §3/§3.1/§4`、
`.github/workflows/gate.yml:52`。

---

_审阅方法：只读源码 + 真实 tmp git 仓复现（含重建修复前代码对比）+ `PYTHONPATH` 隔离的变异测试；未修改任何源码/测试/配置；唯一写入文件为本报告。_
