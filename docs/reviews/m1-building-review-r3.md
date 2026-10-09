# M1「门禁层」独立审阅 R3（第 3 轮 / 最终轮）

Verdict: CHANGES_REQUESTED

> 审阅者：**R3，全新零记忆 reviewer**。只读源码 + 自造临时 git 仓用**真实 CLI** 复现 +
> `PYTHONPATH` 隔离的变异测试；未修改任何源码/测试/配置（唯一写入的文件就是本报告）。
> 基线：`git diff ecbebc0..mvp-m1/2026-10-09`（6 个修复提交）、`docs/tasks.md` D3、
> `docs/design.md` v0.2、`docs/gate.md`、R1/R2 报告。
> 复核命令：`export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q` → **167 passed in 7.03s**（与自述一致）。

**结论摘要**：**R2 唯一的 MUST-FIX（§3-1：merge commit 下 D3 误报，会拦下合法 PR）确实修好了**——
我用真实 CLI 造了一个「base 分支在开分支后前进、PR 里因此有 merge commit」的仓，**修复前 exit 1（点名 base 侧
`src/other.py`）、修复后 exit 0 通过**；且「merge 之后再改 PR 自己的源码」仍 **exit 1 且只点名
`src/app.py`**（真阳性没被一起修没）。两个更早的 MUST-FIX（改名外逃、uninit 路径逃逸）也仍然被钉住。
R1/R2 的停轮问题 Q1–Q5 全部落地。回归测试经**变异验证**（8 个改坏实现全部变红）确认是真保护。
**但两轮修复本身新引入了一处回归**：R2-4 加的 `*_sha` 形状校验（`contract.py:171` `_SHA_RE.match(value)`）
在 manifest 的 `base_sha`/`head_sha` 是**非字符串 JSON 值**（数字 / 布尔 / 列表）时会抛**未捕获 `TypeError`**，
`check` 以 Python 栈回溯崩溃（修复前同一输入是**干净报错**）。这是 fail-closed（非零退出，不放过任何 PR），
但属「修复回合自己引入的崩溃」、且与 R1 一贯的「不得未受控崩溃」标准冲突，是本轮唯一阻塞项——一行可修。

---

## 1. 实际运行结果

```
$ export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q
167 passed in 7.03s
```

无跳过、无 xfail。`uv run --with pyyaml` 解析 `gate.yml`/`ci.yml` 均通过（见 §2.3）。

### 1.1 复现环境（延续 R1 §1.1 / R2 §1.1 的「venv 拷贝坑」规避）

仓库 `.venv/.../site-packages/_editable_impl_witnessloop.pth` 内容为**绝对路径** `/home/happy/witnessloop/src`。
我全程用 `PYTHONPATH=<目标 src> /home/happy/witnessloop/.venv/bin/python -m witnessloop …` 驱动真实 CLI
（先验证过 `PYTHONPATH` 先于 `.pth` 生效：打印 `witnessloop.__file__` 命中的是 `PYTHONPATH` 指向的副本）。
驱动脚本在 `/tmp/wl_repro/`（仓外），`git mv` 不动仓内任何文件。

---

## 2. R2 MUST-FIX（§3-1 merge 误报）的独立复现结论

**做法**：不采信自述、不跑现成单测，自己用 `/tmp/wl_repro/repro.py` 造仓：
main 上 `init` → 建 feature → 内容提交 C → 证据提交 E（manifest 记 `head_sha=C`、`base_sha=merge-base`）
→ 回 main 推一个**只改 `src/other.py`** 的提交 → feature `git merge --no-ff main`（生成 merge commit M）
→ `check --base main --head HEAD`（HEAD = M，即 `pull_request` 下 `actions/checkout` 默认检出的 test-merge 形态）。
用 `git worktree` 把 `fd38a19`（R2 修复前的最后提交）检出为 `/tmp/wl-prefix`，同一份输入分别喂给两份源码。

### 2.1 场景 1：base 前进 + PR 有 merge commit（期望：通过）

| 代码版本 | 命令 | 退出码 | 输出要点 |
|---|---|---|---|
| **修复前** `fd38a19` | `check --base main --head HEAD` | **1** | `审阅的是旧 revision：head_sha=ec0d1d2… 之后又改动了非证据文件：src/other.py` |
| **修复后** `1103451` | 同上 | **0** | `check：通过 ✓` |

### 2.2 场景 2：merge 之后再改 PR 自己的源码（真阳性须仍在）

在场景 1 的 merge commit M 之上，再 `write src/app.py` → commit → 同一命令：

| 代码版本 | 退出码 | 点名的文件 |
|---|---|---|
| 修复前 | 1 | `src/app.py, src/other.py`（含误报的 base 侧文件） |
| **修复后** | **1** | **仅 `src/app.py`**（`src/other.py` 不再出现） |

**结论：§3-1 真修好了，且没有把真阳性一起修没。** 修复逻辑（`checkcmd.py:59-68` 把「本次 PR 变更集
`pr_paths`」传入 `SpanScope`，`contract.py:217-222` 令 `stray` 与 `pr_paths` 求交）独立核验正确：
`pr_paths = base...head` 的变更集，merge 场景下 base 侧独有文件不在其中，自动被排除；本 PR 自己审后改的文件在
`pr_paths` 里，仍被抓。

### 2.3 `gate.yml` 新增 `ref:` 表达式（本地跑不了 Actions，静态核对）

`.github/workflows/gate.yml:42`：`ref: ${{ github.event.pull_request.head.sha || github.sha }}`，`fetch-depth: 0` 保留。

- **语法合法**：`||` 是 GitHub 表达式支持的短路运算符；`github.event.pull_request.head.sha` 是 `pull_request`
  载荷的 PR 分支 head；`pyyaml` 解析该文件通过（`on:` 被 YAML 1.1 解析为布尔 `True`，是解析器惯例，
  GitHub 侧无碍）。
- **语义对**：`pull_request` 事件下把被检 head 钉在 PR 自己的 head（而非 test-merge），与 `check` 侧
  「stray 与 PR 变更集求交」形成**双层**：workflow 层让 `checked_head` 就不是 merge commit，`check` 层即使
  拿到 merge commit 也不误报。两层我都静态/实测对齐。非 PR 事件回落到 `github.sha`，语义合理。
- **残余风险**（本地无法验证，见 §5）：`github.event.pull_request` 在非 PR 事件下的空值解引用是否在各
  事件类型都安全（这是社区通行写法，但无法在本机跑 Actions 证实）；以及 `test_gate_workflow.py` 只断言
  字符串存在，**对新增的 `ref:` 行零覆盖**。

---

## 3. 逐条核验表 + 变异证据

### 3.1 变异方法学

`cp -r src tests pyproject.toml .github /tmp/wl-mut/base`（**不带 `.venv`**）；每次从 base 复制→改坏→
`cd <dir> && PYTHONPATH=<dir>/src … pytest -q`。**基准 167 passed**；**自检变异** `paths.is_within → 恒 True`
→ **7 failed**（基准可信）。8 个针对性变异**全部如期变红**：

| 变异 | 改坏的实现 | 结果 | 变红的测试 |
|---|---|---|---|
| **M1** merge 修复 | `contract.py` 去掉 `… in scope.pr_paths and` | **1 failed** | `test_base_advanced_then_merged_does_not_false_positive` |
| **M2** pr_paths 置空 | `checkcmd.py` `pr_paths=frozenset()` | **5 failed** | `test_code_committed_after_review_is_stale`、`test_real_stale_change_survives_the_merge_commit_fix`、`test_single_commit_pr_is_rejected`、`test_reviews_dir_outside_the_change_is_not_evidence`、`test_events_file_outside_the_change_is_not_evidence` |
| **M3** 证据 glob 收窄 | `policy.py` `*/reviews/**` 改回 `**/reviews/**` | **1 failed** | `test_reviews_dir_outside_the_change_is_not_evidence` |
| **M4** covers 拒通配 | `events.py` 删掉 `if any(ch in … GLOB_METACHARACTERS)` | **1 failed** | `test_events.py::test_literal_wildcard_in_a_filename_still_needs_a_concrete_name` |
| **M5** Event 不变式 | `events.py` 停用 `__post_init__` 的归一/去空白 | **4 failed** | `test_event_with_blank_reason_does_not_count`、`test_path_is_normalized_before_comparison`、`test_blank_explanation_fields_never_cover[reason-   ]`、`[…approved_by-  ]` |
| **M6** sha 形状校验 | `contract.py` 删掉 `_SHA_RE` 形状循环 | **2 failed** | `test_sha_fields_must_look_like_shas`、`test_head_sha_symbolic_ref_is_rejected` |
| **M7** 改名外逃（R1） | `checkcmd.py` 去掉 `old_path`→`D` 分支 | **1 failed** | `test_renaming_a_protected_file_out_of_the_area_is_rejected` |
| **M8** uninit 逃逸（R1） | `uninitcmd.py` 去掉 `is_within` 守卫 | **3 failed** | uninit 越界/绝对路径/无 sha 三条 |

**含义**：M1/M2 证明「求交修复」是承重结构（拿掉即误报回到/修复失效）；M3 证明证据收窄被钉住；
M4 证明 R2-4 声称「原先冗余无测试」的那行**现在真有定向测试钉住**；M5/M6 证明 Event 不变式与 sha 形状校验
被钉住；M7/M8 证明两轮修复没有把更早的 MUST-FIX 悄悄改回去。**回归测试不是空转。**

### 3.2 R1/R2 问题单项核验

| 项 | 落点 | 结论 |
|---|---|---|
| R2 §3-1 merge 误报（MUST-FIX） | `checkcmd.py:59-68`、`contract.py:217-222`、`gate.yml:42` | ✅ 真修好（§2 实测 + M1/M2） |
| R2 §3-2 单提交 PR 不支持 | `gate.md §3.1`、`test_single_commit_pr_is_rejected` | ✅ 已文档化并钉成契约 |
| R2 §3-3 证据路径过宽 | `policy.py:57-70` 收窄到 change 目录内 | ✅ 已收窄（M3） |
| R2 §3-4 covers 通配拒绝冗余 | `events.py:93-94` + `tests/test_events.py` | ✅ 已补定向测试（M4） |
| R2 §3-6 `*_sha` 收任意 ref | `contract.py:170-179` 形状校验 | ✅ 意图达成（M6）——**但见 §4-1 崩溃回归** |
| R1 I-1 改名外逃 | `checkcmd.py:126-128` | ✅ 仍钉住（M7） |
| R1 I-2 uninit 越界 | `uninitcmd.py:50-52,64-69` | ✅ 仍钉住（M8） |
| R1 I-3 base/head 真绑定 | `contract.py:152-231` | ✅ 与 `tasks.md D3`、`gate.md §3` 口径一致 |
| R1 I-4 glob 语义零覆盖 | `tests/test_paths.py`（180 行） | ✅ 已补，M3/M10/M11 类变异变红 |
| R1 I-7 死代码 | `policy.effective_protected_paths` 已删 | ✅ |
| R1 §6 缺自测 CI | `.github/workflows/ci.yml` | ✅ 已加（`uv run pytest -q` + wheel 冒烟） |
| R2 §3-5 is_within 跟随软链 | `paths.py:60-71` 未动 | ⚠️ NIT，保守但安全，留 M2（可接受） |

---

## 4. 新发现的问题

### 4-1（阻塞 / MUST-FIX，回归）`_SHA_RE.match(value)` 对**非字符串** manifest 字段抛未捕获 `TypeError`，`check` 栈回溯崩溃

**证据**：`src/witnessloop/contract.py:65`
```python
_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
```
`src/witnessloop/contract.py:165-179`（`_check_git_span`）
```python
base_sha = doc["base_sha"]      # ← 原样取自 JSON，未做类型收窄
head_sha = doc["head_sha"]
for field, value in (("base_sha", base_sha), ("head_sha", head_sha)):
    if not _SHA_RE.match(value):     # ← line 171：value 若是 int，TypeError
        ...
```
必需字段的「非空」预检用的是 `str(doc.get(field) or "").strip()`（`contract.py:124-126`），它只挡「空/假值」，
把**非空但非字符串**的值（如 `12345`、`true`、`["x"]`）原样放行到 `_check_git_span`。
`re.Pattern.match()` 只接受 `str`/`bytes`；`int`/`bool`/`list`/`dict` 一律抛
`TypeError: expected string or bytes-like object`。

**独立复现（真实 CLI，`check --base main --head HEAD`）**：造一份合法 change+证据，仅把 manifest 的
`base_sha` 写成 JSON 数字 `12345`（非 0，故不被「缺字段」预检拦下）：

```
$ PYTHONPATH=/home/happy/witnessloop/src … python -m witnessloop check --root . --base main --head HEAD
Traceback (most recent call last):
  …
  File "…/checkcmd.py", line 74, in run
    findings += contract.validate_review_manifests(…)
  File "…/contract.py", line 148, in _validate_one
    findings.extend(_check_git_span(root, manifest_rel, doc, scope))
  File "…/contract.py", line 171, in _check_git_span
    if not _SHA_RE.match(value):
TypeError: expected string or bytes-like object, got 'int'
EXIT=1   （未受控崩溃，非受控失败）
```
`head_sha` 同路径；`["x"]`（list）同样崩溃。

**这是修复回合引入的回归**：修复前（`fd38a19`）同一输入走 `rev_parse`，f-string 把值 `str()` 化后交给 git，
返回 None → **干净报错** `base_sha=12345 不是本仓的提交（证据必须绑定真实 revision）`、exit 1、**无栈回溯**。
（我在 `/tmp/wl-prefix/src` 实测确认了这一点。）

**威胁模型 / 影响**：manifest 是**提交进仓、agent 可写**的（`gate.md §4`、`design §2`）。一个 agent/生成器
把 `base_sha`/`head_sha` 误写成数字/布尔/列表，就会让 `check` 以栈回溯崩溃。**关键定级说明**：崩溃使
`check` 非零退出，属 **fail-closed**——不放过任何 PR，因此**不是门禁绕过**；危害限于「诊断质量」与
「未受控崩溃」（而这恰是 R1 对 `uninit` 未捕获 `ValueError` 判定为 MUST-FIX 的同一类问题，且此处是**新引入**）。

**修法（一行，保留 R2-4 意图又不崩）**：匹配前做类型收窄，例如
```python
if not isinstance(value, str) or not _SHA_RE.match(value):
    findings.append(Finding(manifest_rel, f"{field}={value!r} 不是一个 git sha（40 位小写十六进制）"))
```
并补一条测试：manifest 的 `base_sha`/`head_sha` 为数字 → `check` 干净报错（exit 1，**不含** `Traceback`）。

### 4-2（NIT）`gate.yml` 新增的 `ref:` 行无任何测试覆盖

`test_gate_workflow.py:21-27` 只断言文件里含 `workflow_call` / `witnessloop check` / `fetch-depth: 0` 三个
**子串**——本轮新增的 `ref:` 表达式没有任何断言。属静态文件测试的常见边界；建议补一条断言
`"ref:" in text` 或断言该表达式文本存在，避免日后被误删。

### 4-3（NIT，非本轮引入）`report_path` 可落在 `reviews/` 之外 → 该报告不算「证据」→ 可能误报 stale

`gate.md §3` 把证据路径收窄为 `<changes_root>/*/reviews/**`、`<changes_root>/*/workflow-events.jsonl`、
`.witnessloop/**`；但 `contract._check_hashes`（`:237-245`）只要求 `report_path` 落在 **change 目录内**
（不要求 `reviews/` 下）。若某 change 把报告放在 change 目录根（如 `report_path="my-report.md"`），
该报告文件**不匹配**证据 glob，于是在 `head_sha..被检 head` 的 delta 中被判 stray → 误报「旧 revision」。
这是既有行为（R2 收窄前后都不把 `reviews/` 外的报告当证据），**非本轮引入**，且与 `gate.md §1` 约定
（报告在 `reviews/`）相悖，属低危边界；建议在 `gate.md §3` 注明「报告必须置于 `reviews/` 下」，或把
`report_path` 一并纳入证据判定的精确路径。

### 4-4（NIT）`Event` 归一化收口后，`covers` 与新 `test_events.py` 的重心完全落在相等比较上

`events.py:80-95` 的 `covers` 现在依赖 `Event.__post_init__`（`:42-46`）先归一 `artifact_path`。这个收口
是**正确的**（M5 证明被钉住），但把「不变式只在构造点守」变成新契约：任何绕过 `Event(...)` 直接操作字段的
写法都会失效。属正当重构，记录供后续维护者知晓。

---

## 5. 残余风险清单（含本地无法验证的部分）

1. **`gate.yml` 只能静态核对，跑不了 Actions**（本节最重要）：`ref: ${{ github.event.pull_request.head.sha || github.sha }}`
   的**语法与语义**我核对为正确，但以下**无法在本机证实**，留作残余风险：
   (a) 非 PR 事件下 `github.event.pull_request` 的空值解引用是否在所有事件类型都得到 `null` 而非报错
   （社区通行写法，但未经真实 runner 验证）；
   (b) 该 `ref:` 是否影响 required check 的登记/触发（应由 caller 侧 branch protection 决定，未变）；
   (c) fork PR 下 checkout 任意 sha 的行为（由 `actions/checkout@v4` 负责）。
2. **冲突解决型 merge**：若 PR `merge base` 时对**非证据文件**解冲突（冲突结果既非 base 版本也非 head_sha 版本），
   该文件会进 `pr_paths` 且在 delta 里 → 被 `check` 判 stale。CI 路径下 `ref:` 钉了 PR head（pre-merge）可规避；
   但「把已 merge 的分支 head 直接拿去 `check`」仍可能误报。低概率，未测。
3. **`report_path` 落在 `reviews/` 之外** → 误报 stale（§4-3），低危边界。
4. **证据 = `<change>/reviews/**` 下任意文件**：作者仍可把非证据内容塞进某 change 的 `reviews/` 子目录来
   躲开 stale 判定（已被收窄到 change 目录内，影响面有限）。
5. **`is_within` 跟随符号链接**（R2 §3-5，未改）：保守但正确；`uninitcmd` 的 `unlink` 只删链接本身，
   守卫比操作更严——不构成 bug。
6. **仓库自带 `.venv` 的 editable 路径是绝对路径**（R1 §1.1）：`cp -r` 仓库后再跑测试仍会踩「测的是原件」
   的坑（我全程用 `PYTHONPATH` 强制副本规避）。`ci.yml` 已把 CI 侧消掉，但**本地复制仓库的人**仍会踩。
7. **`test_gate_workflow.py` 对 `ref:` 行零覆盖**（§4-2）。

---

## 6. 停轮问题（需人拍板）

**Q1（对应 §4-1，唯一阻塞项）`base_sha`/`head_sha` 为非字符串 JSON 值时 `check` 崩溃，怎么处理？**
- 现状：`contract.py:171` `_SHA_RE.match(<非 str>)` → 未捕获 `TypeError` → 栈回溯；修复前同输入是干净报错。
- 选项：(a) **匹配前加 `isinstance(value, str)` 收窄**（推荐，一行，保留 R2-4 的「形状校验」意图）；
  (b) 在 `_validate_one` 里对这两个字段先做 `str()` 规范化再比对。二者等价，选 (a) 更直白，并补一条
  「非字符串 sha → 干净报错（无 Traceback）」的回归测试。
- 我的判定：**这是回归，应在本轮修掉再转 PASS**；危害面小（fail-closed），但「修复回合自己引入未受控崩溃」
  不该带进 M1。

**Q2（范围）§4-3（`report_path` 在 `reviews/` 外）与 §4-2（`ref:` 无测试）要不要本轮顺手做？**
- 建议：§4-2 顺手补一行断言（零成本）；§4-3 在 `gate.md §3` 加一句边界说明即可，行为留 M2。

---

## 7. 复现清单（可照跑）

```bash
export PATH=/home/happy/.local/bin:$PATH
cd /home/happy/witnessloop && uv run pytest -q                 # 167 passed

# §2 merge 误报独立复现（真实 CLI，PYTHONPATH 隔离）
PREFIX=$(git worktree add -q /tmp/wl-prefix fd38a19 && echo /tmp/wl-prefix)
/home/happy/witnessloop/.venv/bin/python /tmp/wl_repro/repro.py /tmp/wl-prefix/src   /tmp/wl_repro/work_prefix
/home/happy/witnessloop/.venv/bin/python /tmp/wl_repro/repro.py /home/happy/witnessloop/src /tmp/wl_repro/work_fixed
#   修复前：scenario1 exit 1（点名 src/other.py）；修复后：scenario1 exit 0、scenario2 exit 1（仅 src/app.py）

# §4-1 崩溃：把 change manifest 的 base_sha 写成 JSON 数字 12345，再 check → TypeError 栈回溯
#   （对照 fd38a19：干净报错 "base_sha=12345 不是本仓的提交"）

# 变异（PYTHONPATH 强制副本源码；先跑 is_within→True 自检必红 7 failed）
cp -r src tests pyproject.toml .github /tmp/wl-mut/base     # 不带 .venv
#   M1 contract.py 去 "in scope.pr_paths"            → 1 failed
#   M2 checkcmd.py  pr_paths=frozenset()             → 5 failed
#   M3 policy.py    */reviews/** → **/reviews/**     → 1 failed
#   M4 events.py    删 covers 拒通配行               → 1 failed
#   M5 events.py    停用 __post_init__               → 4 failed
#   M6 contract.py  删 _SHA_RE 形状循环              → 2 failed
#   M7 checkcmd.py  删 old_path 目标                 → 1 failed
#   M8 uninitcmd.py 删 is_within 守卫               → 3 failed
```

**证据文件**：`src/witnessloop/{contract,checkcmd,policy,events,gitutil,uninitcmd,paths}.py`、
`tests/{test_check_manifest,test_check_protected,test_events,test_paths,test_uninit}.py`、
`.github/workflows/{gate,ci}.yml`、`docs/gate.md §2/§3/§3.1`。

---

_审阅方法：只读源码 + 真实 tmp git 仓用真实 CLI 复现（含 `git worktree` 重建修复前代码对比）+
`PYTHONPATH` 隔离的 8 项变异测试；未修改任何源码/测试/配置；唯一写入文件为本报告。_
