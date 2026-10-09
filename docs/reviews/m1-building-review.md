# M1「门禁层」独立审阅（building-review）

Verdict: CHANGES_REQUESTED

> 审阅者：独立零记忆 reviewer（自己读码、自己跑测试、自己做变异验证）。
> 基线：`git diff main...mvp-m1/2026-10-09`、`docs/tasks.md` A1–D6、`docs/design.md` v0.2、`docs/gate.md`。
> 复核命令（真实输出，见 §1.0）：`export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q` → **80 passed**。
>
> **结论摘要**：骨架、分发、三动词路由、init/uninit/check 的**主线正确性**都成立，80 个测试全绿，
> 变异验证显示核心逻辑（fail-closed、hash 绑定、reviewer≠author、不变集豁免、`_is_within`、树哈希）都被测试钉住。
> 但存在 **2 个 MUST-FIX 的逻辑/安全洞**（受保护路径「改名外逃」绕过 D5；`uninit` 无路径约束可越界删文件），
> **1 个 SHOULD 的设计偏离**（D3 声明要绑定的 `base_sha`/`head_sha` 实际只做「非空」检查），
> 以及一处**测试盲区**（design §9 点名、`gate.md §2` 明写的 glob 语义没有任何测试钉住——两个针对性变异全部存活）。
> 因此一次修复轮之后可转 PASS。

---

## 1. 实际运行结果

### 1.0 必跑命令（真实输出）

```
$ export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q
........................................................................ [ 90%]
........                                                                 [100%]
（-q 双静默；去掉 addopts 后的摘要：）
collected 80 items … 80 passed in 3.87s
```

`uv run pytest -o addopts=""`（带摘要）同样 **80 passed**。无跳过、无 xfail、无 warning 汇总异常。

### 1.1 审阅方法学（重要，且本身是一处可维护性坑）

我在 `/tmp` 里 `cp -r` 仓库做变异。**起初所有变异都「存活」，是假象**：`cp -r` 把仓库的 `.venv/`
一起复制了，而该 `.venv` 里的 editable 安装 `_editable_impl_witnessloop.pth` 指向的是
**绝对路径 `/home/happy/witnessloop/src`**——于是 `/tmp` 副本里跑 `uv run pytest`
测试的是**原始源码**，不是副本。（`uv run python -c` 有时走副本、有时走原件，极具迷惑性；
我用 `pytest -p <plugin> -s` 打印 `contract.__file__` 才定位到它。）

修正办法：`PYTHONPATH=<副本>/src uv run pytest`（PYTHONPATH 先于 site-packages 的 `.pth`），
并先用一次「预期必红」的变异（`_is_within → True`）确认基准可信。**下文所有变异结果都跑了修正后的驱动。**

> **可维护性 NIT**：仓库自带 `.venv` 的 editable 路径是绝对的，且本仓 **没有任何 CI 跑自己的测试**
> （见 §6）。任何「复制仓库做实验/在别处跑测试」的人都会踩同一个坑。建议 `.venv` 不入库（已在 `.gitignore`）
> 且**任何环境都不应预置**；真正解法是加一条自测 CI（§6）。

---

## 2. 任务逐项验证表（A1–D6）

| 任务 | 结论 | 证据（文件:行号 + 测试） |
|---|---|---|
| A1 pyproject + 包结构 + 入口 | ✅ PASS（带 NIT） | `pyproject.toml:10-11`（`[project.scripts] witnessloop`）、`src/witnessloop/`、hatchling。测试 `test_cli.py:54` 用 `python -m witnessloop` 跑通——**但没断言 `witnessloop` 控制台脚本名本身**（入口映射未被直接验证，NIT） |
| A2 CLI 路由 + 未知子命令响亮报错 | ✅ PASS | `cli.py:33-67`、`cli.py:74-76`（无子命令→2）、`cli.py:92`；`test_cli.py:30-38`（`gate`→exit 2 + "invalid choice"）、`test_cli.py:48`（恰 3 动词） |
| B1 `policy.json`（protected/required/evidence） | ✅ PASS | `policy.py:30-45`；`test_init.py:27-38` |
| B2 `init-manifest.json`（创建台账 + init 前 base ref） | ✅ PASS | `initcmd.py:58-74`；`test_init.py:56-74`（`base_ref=="main"`、`base_sha==HEAD`、自引用条目） |
| B3 极薄 caller workflow | ✅ PASS | `initcmd.py:24-41`；`test_init.py:41-53`、`test_gate_workflow.py`（文件真实存在、`workflow_call`、含 `witnessloop check`） |
| B4 幂等 / 只增不改 / 不 auto-commit | ✅ PASS | `initcmd.py:97-118`（冲突报 diff 拒写）、`:134-171`（漂移即响）；`test_init.py:85-120,134-139` |
| B5 `--dry-run` | ✅ PASS | `initcmd.py:113-118`；`test_init.py:123-131`（工作树 `status` 为空） |
| C1 依台账精确删除 | ✅ PASS（带 MUST-FIX 约束缺失，见 I-2） | `uninitcmd.py:41-55,75-79`；`test_uninit.py:20-34` |
| C2 改动过则拒删并报 diff | ✅ PASS | `uninitcmd.py:51-73`；`test_uninit.py:62-84` |
| C3 幂等 | ✅ PASS | `uninitcmd.py:24-27`；`test_uninit.py:48-59` |
| D1 无 policy → 「未接入」非零 | ✅ PASS | `checkcmd.py:30-42`（返回 `EXIT_NOT_ONBOARDED=3`）；`test_check_onboarding.py:13-24`、`test_acceptance.py:81-85` |
| D2 change 目录契约 | ✅ PASS | `contract.py:48-59`；`test_check_contract.py`（8 例） |
| D3 manifest 存在 + hash 绑定 | ⚠️ PARTIAL | `contract.py:62-162`。报告/tasks/specs/report 的 hash **确实绑定字节**（`test_check_manifest.py` 全绿）；**但 `base_sha`/`head_sha` 只做「非空」检查、从不与真实 base/head 比对**（见 I-3） |
| D4 `reviewer_run_id != author_run_id` | ✅ PASS | `contract.py:110-117`；`test_check_manifest.py:43-54` |
| D5 受保护写入需解释事件 | ⚠️ PARTIAL | `checkcmd.py:83-124`。新增/修改/删除都覆盖，**但「改名外逃」不覆盖**（见 I-1） |
| D6 不变集恒受保护 | ✅ PASS | `policy.py:18-23`（4 条，`test_invariants.py:20-24` 验证封顶）、`checkcmd.py:95,108-109`；`test_invariants.py` 4 例 |

`uninit`（C 组）与 `check`（D 组）的哈希/事件/不变集**主线行为**都被测试真实钉住——见 §5.2 的变异结果。

---

## 3. Issues（证据 + 严重度 + 复现/变异方法）

### I-1（MUST-FIX）受保护路径「改名外逃」绕过 D5：`git mv` 把受保护文件移出保护区，门禁放行

**证据**：`checkcmd.py:102-104`
```python
for change in changes:
    path = pathutil.normalize(change.path)          # 只看新路径
    by_policy = pathutil.matches_any(path, pol.protected_paths)
    ...
```
`git diff --name-status`（`gitutil.py:63-79`）对改名给出 `R<score> old new`，`Change.path=新、old_path=旧`。
`_protected_writes` **只取 `change.path`（新路径）**。于是把受保护文件改名到保护区之外，新路径不受保护 → 无 finding → 放行。
**注意这不一致**：同一模块的 `contract.changed_change_ids`（`contract.py:39-45`）**同时看 `path` 和 `old_path`**——
只有 `_protected_writes` 漏了 `old_path`。`gate.md §5` 明写「删除 (D) 需解释事件」，而改名 = 对旧路径的删除。

**复现（真实跑通，exit 0）**：
```bash
# main 上有 openspec/specs/retry/spec.md，feature 分支：
git mv openspec/specs/retry/spec.md src/moved-spec.md && git commit -m move
witnessloop check --base main --head HEAD     # → exit 0（放行）
# check 看到的 diff： R100  openspec/specs/retry/spec.md  src/moved-spec.md
```
对比：直接 `rm` 同一文件会被拦（`test_check_protected.py:92-103` 已钉）。**改名是 `rm` 的等价物却绕过门禁。**

**变异/验证方法（证明测试没覆盖）**：目前任何测试都没有构造 rename；把 `_protected_writes` 的循环补上
`old_path`（正确修法）后跑全量，**没有任何测试变红**——即该分支零覆盖。

---

### I-2（MUST-FIX）`uninit` 无路径约束：可越界删除仓根之外的文件；绝对路径还会崩溃

**证据**：`uninitcmd.py:41-55` 遍历台账条目时 `path = root / rel`（`rel` 直接来自 manifest 的 `path`），
**没有任何 containment 检查**；随后 `uninitcmd.py:75-79` 直接 `path.unlink()`。
`_prune_empty_dirs`（`:85-91`）同样对越界目录一路上溯 `rmdir`，只以 `!= root` 为界。
对比：同一份代码对 `report_path` **是**有约束的（`contract._is_within`，`contract.py:165-170`）——`uninit` 漏了同款检查，属明显的自相矛盾。

**复现 A（越界删除，exit 0）**：伪造 `.witnessloop/init-manifest.json`：
```json
{"schema":"witnessloop/init-manifest@v1","created_files":[{"path":"../secret.txt","sha256":"<该文件真实hash>"}]}
```
`witnessloop uninit` → **删除仓根同级的 `../secret.txt`，exit 0**。（`path=root/"../secret.txt"`，
`Path.relative_to(root)` 对字面串成功 → `unlink()` 命中。）

**复现 B（崩溃）**：把 `path` 写成绝对路径 `/tmp/x/secret.txt` → `uninitcmd.py:77`
`path.relative_to(root)` 抛 **未捕获 `ValueError`**，栈回溯退出（非受控失败）。

**威胁模型**：manifest 是**提交进仓**的，agent/PR 可写。维护者一旦 `uninit`，即触发越界删除。
严重度按「任意文件删除 + 未受控崩溃」计 MUST-FIX（即便前置条件是「运行 uninit」，也不该无约束删除）。

**变异/验证方法**：把 `uninit` 加一条 `_is_within(path, root)` 守卫后跑全量——**没有测试变红**，说明该缺陷零覆盖。

---

### I-3（SHOULD）D3 要求绑定 `base_sha`/`head_sha`，实现只做「非空」检查（设计偏离）

**证据**：`constants.py:36-45` 把 `base_sha`/`head_sha` 放进 `REVIEW_MANIFEST_REQUIRED_FIELDS`，
`contract.py:95-99` 只检查「字段非空」；`_check_hashes`（`contract.py:124-162`）**只比对
`report_hash`/`tasks_hash`/`spec_hash`**，从不用 git 去核对 base/head。
任务 D3 原文：「hash 绑定（base/head sha + tasks/spec/report hash）」——**base/head 被点名要绑**。
而 `gate.md §3` 却把绑定范围收窄为「tasks/spec/report」——**两份基线自相矛盾**（见 §7 停轮问题）。

**复现（真实跑通，exit 0）**：
1. change 写齐证据并 commit（manifest 记下当时的 head_sha）→ 之后**再审**再推一个只改 `src/` 的 commit；
2. `check --base main --head HEAD` → **exit 0**：审阅的 head ≠ 当前 head，却视为通过（stale review 未检出）。
3. 更直白：测试脚手架 `helpers.py:76-77` 写死 `base_sha="0"*40 / head_sha="1"*40`，
   `test_check_manifest.py:97-109` 仍 **PASS**——即「乱填 base/head 也绿」已被现有测试坐实。

**影响**：削弱「防漂移」——审阅后追加的提交（哪怕动了被审代码）不会被发现，除非它恰好改了 tasks/spec/report 字节。
**修法二选一**（需人拍板，见 §7）：(a) 让 check 用 `git rev-parse` 比对 manifest 的 base/head 与本次 diff 的 base/head；
(b) 明确把 base/head 降级为 informational，并**同步改 design §5.3/D3 与 gate.md**，别让两份文档打架。

---

### I-4（SHOULD）glob 语义（design §9 点名、gate.md 明写）**零测试覆盖**，两个针对性变异全部存活

**证据**：全仓**没有 `test_paths.py`**。唯一触达 glob 的 `test_invariants.py:111-127`（`test_matching_semantics`）
只用 6 条路径 + 不变集 pattern，而这些路径在「正确实现」和「坏实现」下**结果相同**，无法证伪。

**变异结果（修正方法学后，`PYTHONPATH` 强制副本源码）**：
| 变异 | 改法 | 结果 |
|---|---|---|
| **M10** `*` 跨 `/`（正是 design 警告的 `fnmatch` 坑） | `paths.py:40` `"[^/]*"` → `".*"` | **80 passed（存活）** |
| **M11** `**/` 不再匹配零层目录 | `paths.py:34` `"(?:.*/)?"` → `"(?:.*/)"` | **80 passed（存活）** |

已验证这两个变异**确实改变了行为**（M10 下 `reviews/sub/x.manifest.json` 会错误命中 `**/reviews/*.manifest.json`；
M11 下顶层 `reviews/x.manifest.json` 会错误失配），却**没有任何测试变红**。

**影响**：`gate.md §2` 白纸黑字承诺的 `*`/`?` 不跨 `/`、`**` 跨（含零层）语义**没有任何回归防线**。
当前实现是**对的**（我用 16 条手工断言核对过，全部符合设计），但任何人日后「顺手换回 fnmatch 或简化正则」
都不会被拦。**建议新增 `test_paths.py`**，至少覆盖：`*` 不跨 `/`、`?` 不跨 `/`、`**` 零层、`**` 中间层、
反斜杠归一、前导 `./`、大小写（见 I-5）。

---

### I-5（SHOULD/NIT）design §9 风险 7 的「大小写 / `~`」未处理也未声明

**证据**：`paths.py:12-21` 只做 `\→/` 与前导 `./` 剥离。实测：
`matches("OpenSpec/Specs/X.md", "openspec/specs/**") == False`（不分大小写）；
`~` 不展开。
**判断**：M1 的输入恒为 **git 输出的 posix 相对路径**（大小写敏感、无 `~`），因此当前不处理**不构成 bug**；
但 design §9 把它列为已知坑、`gate.md` 只字未提「不处理」。**建议在 gate.md 明写边界**
（或补一条 NIT 级的规范化）。这一条不建议现在改行为，只建议补文档。

---

### I-6（NIT）单条事件用 `artifact_path:"**"` 即可豁免**全部**受保护路径（含不变集）

**证据**：`events.py:65-75` 把事件的 `artifact_path` 当 glob 匹配。实测
`covers(event(artifact_path="**"), "openspec/specs/…" | ".witnessloop/policy.json") == True`。
**判断**：事件本身就是自证的（design §2「防漂移不防伪造」），所以这不是新增攻击面；
但它把「结构化解释」塌缩成「一行 `**` 放行一切」，连不变集 `policy.json` 的**修改**都能被一条事件豁免。
**建议**：`gate.md` 注明该行为，或让不变集只接受精确/受限 pattern。

---

### I-7（NIT）冗余 / 死代码

- `policy.py:81-87` `effective_protected_paths` **定义后从未被引用**（`checkcmd.py:104-105` 手工做并集）。死代码。
- `events.py:73-75` `covers` 的第二个分支 `event.artifact_path == pathutil.normalize(artifact_path)`
  **恒冗余**：`matches` 对无通配的 pattern 已是精确匹配（`glob_to_regex` 会 `re.escape` 每个字符并锚 `\Z`）。
- `events.py:30` `Event.change_id` 在 check 逻辑里**从未被消费**（只有 manifest 的 `change_id` 被用）。
- `paths.matches`（`:51-52`）对已归一化的入参**再归一化一次**（`checkcmd.py:103` 已归一），幂等但重复。

---

## 4. 设计对齐（是否偷偷偏离 design v0.2）

**总体：对齐良好，无范围蔓延。**
- **动词数**：仅 `init`/`uninit`/`check`，`test_cli.py:48` 断言 `choices=={init,uninit,check}`——没有 `gate`/`event`/`status`/`policy`。
- **无签名/密钥**、**无状态机/projection/replay**、**无 spec 适配器抽象**（`constants.py` 只有 OpenSpec 形状常量）、**无 marketplace**：`src/` 下不存在对应模块，符合 design §4/§10「不做」。
- **不变集封顶**：4 条 ≤ 5（`policy.py:18-23`，`test_invariants.py:20-24`）。
- **能力边界诚实**：`gate.md §7` 与 `test_acceptance.py:45-63`（F2）把「手写放行事件不拦」钉成契约，与 design §2 一致。
- **唯一实质偏离是 I-3**（D3 的 base/head 绑定被弱化），且方向是「少做了声明要做的」，不是「多做了不该做的」。

---

## 5. 测试覆盖与「假保护」审查

### 5.1 覆盖缺口

1. **glob 语义零覆盖**（I-4）——最严重。无 `test_paths.py`。
2. **rename（改名外逃）零覆盖**（I-1）。
3. **`uninit` 路径约束零覆盖**（I-2）。
4. **`base_sha`/`head_sha` 绑定零覆盖**（I-3）——现有测试反而坐实了「乱填也绿」。
5. **控制台入口名 `witnessloop` 未被直接验证**（`test_cli.py:54` 走的是 `python -m`）。
6. `gitutil._parse_name_status` 的 `C`（copy）分支、`current_branch` 的 detached HEAD 分支无直接测试（NIT）。

### 5.2 变异验证：哪些**被**钉住（反证「不是假保护」）

用「改坏实现 → 期望某测试变红」的方法，以下变异**全部如期变红**，说明核心逻辑有真实保护：

| 变异 | 期望 | 实际 |
|---|---|---|
| `_is_within → True`（去掉逃逸检查） | 逃逸测试红 | **1 failed** ✅ |
| 去掉 `reviewer != author`（D4） | 自审测试红 | **1 failed** ✅ |
| 去掉不变集「新增免解释」豁免（D6） | bootstrap 类测试红 | **10 failed** ✅ |
| 去掉 `reason`/`approved_by` 非空检查（D5） | 空字段测试红 | **2 failed** ✅ |
| 树哈希忽略文件内容 | spec/tasks 漂移测试红 | **1 failed** ✅ |
| `EXIT_NOT_ONBOARDED → 0`（静默通过） | D1 测试红 | **1 failed** ✅ |
| `normalize` 改用 `str.lstrip("./")` | 归一化测试红 | **2 failed** ✅ |
| `changed_change_ids` 置空 | 大面积红 | **17 failed** ✅ |

**结论**：D1/D4/D5/D6 与 hash 绑定的**主路径**测试是**真保护**（非剧场）。
缺口集中在 **I-1/I-2/I-3/I-4** 四条具体分支上。

### 5.3 TDD 真实性

提交历史（`94fff6e A` / `3c4203d B` / `b29cb28 C` / `dbddb13 D`）显示每个动词的**代码与测试同提交落地**，
无法从历史证明「先红后绿」的顺序；但测试是**行为级**（真实 git 仓 + 进程内 CLI），且变异验证（§5.2）
证明其非空转。**TDD 真实性：无法证伪，倾向于成立**；建议后续在 commit message 里保留 red→green 痕迹。

---

## 6. CI 完整性审查

**`gate.yml`（reusable，`workflow_call`）本身正确**：
- `fetch-depth: 0`（`gate.yml:34-36`）——浅克隆会让 merge-base 求不出，与 check 的 fail-closed 一致；
- `uvx --from git+…@<ref> witnessloop check --base "$BASE" --head HEAD`（`:50-52`），
  `${{ }}` 注入点放在 `env:`（安全写法，非直接进 `run:`）；
- base 解析在 workflow 里显式 `origin/<base_ref>`（`:44-49`）。

**结论性判断（含 design §9 风险 3「静默为零」）**：
- **鸡生蛋已被正确规避**：`check` 对「新增」证据/门禁配置免解释（`checkcmd.py:108-109`，`test_check_onboarding.py:46-53`），
  接入 PR 不会被自己拦；且经查证，`pull_request` 事件**从 PR 分支加载 workflow**，
  所以**新加的 caller 在本 PR 内就会跑**——bootstrap 路径成立（`test_bootstrap_pr_adding_init_files_passes` 是本地等价验证，非 GitHub 端验证）。
- **但「不跑 init 就静默为零」只被「话术 + exit 3」缓解，未被 CI 消除**：若目标仓从不加 caller，
  check 根本不会运行（`exit 3` 也无从触发）。这正是 design §9 风险 3 自认的边界。
- **本仓自身没有 CI 跑测试**：`.github/workflows/` 下只有 `gate.yml`，而它是纯 `workflow_call`
  （不会在 push/PR 自触发）。**这 80 个测试在任何地方都不会被自动执行**——SHOULD 补一条自测 CI。
- **操作前置未自动化**：caller 引用 `gate.yml@v1`，需 `v1` tag 真实存在；required check 需人工在
  branch protection 勾选（design §4 认此为「人类签名」）。属已知取舍，但建议 README/`gate.md` 用清单固化。

---

## 7. 停轮问题（需人拍板）

**Q1（I-3 根因）`base_sha`/`head_sha` 到底绑不绑？两份基线自相矛盾。**
- 例：`docs/tasks.md` D3 写「hash 绑定（**base/head sha** + tasks/spec/report hash）」，
  而 `docs/gate.md §3` 只写「tasks/spec/report」；实现跟了 gate.md。
- 现状后果：审阅后追加一个只改 `src/` 的提交，`check` 仍绿（stale review 漏检）。
- 请拍板：(a) 修实现，让 check 比对 manifest.base/head 与真实 base/head；或 (b) 认 gate.md，
  **同步修订 design §5.3 与 D3** 删掉 base/head 的「绑定」措辞。**二者必须择一，别让文档继续打架。**

**Q2（I-1）「改名」是否**本应**算受保护写入？**
- 例：`git mv openspec/specs/retry/spec.md src/x.md` 目前放行。若认为「移走受保护 artifact = 删除、须解释」，
  则按 MUST-FIX 修 `_protected_writes` 纳入 `old_path`；若刻意允许，请在 `gate.md §5` 明写「改名免解释」。
- 我的建议：**按删除处理**（与现有「rm 需解释」一致），修 `_protected_writes`。

**Q3（I-2）`uninit` 的越界删除按什么威胁模型定级？**
- 例：伪造 `init-manifest.json` 里 `path:"../secret.txt"` → `uninit` 真删了仓外文件（我实测 exit 0）。
- 若认为「manifest 可被 agent 提交」在威胁模型内 → MUST-FIX（加 containment）；若认为 uninit 仅本地可信操作 →
  至少也应修**绝对路径崩溃**（`uninitcmd.py:77` 未捕获 `ValueError`）。**倾向：加 containment（低成本、消除矛盾）。**

**Q4（范围）`test_paths.py` 的缺失要不要在 M1 补，还是留到 M2？**
- 例：M10/M11 两个变异（`*` 跨 `/`、`**/` 需斜杠）**全部存活**；`gate.md §2` 却已把它写进契约。
- 我的建议：**M1 就补**——契约已发布，且这是 design §9 点名的头号风险，回归成本极低。

**Q5（CI）是否给 witnessloop 本仓加一条自测 CI（`uv run pytest`）？**
- 例：当前 80 个测试**无任何自动执行点**；`.venv` 复制坑（§1.1）也因缺 CI 而无人发现。
- 建议：M1 即加（哪怕只是 `pull_request` 上跑 `uv run pytest`）。

---

## 8. 复现清单（可照跑）

```bash
export PATH=/home/happy/.local/bin:$PATH
cd /home/happy/witnessloop && uv run pytest -q                 # 80 passed

# I-1 改名外逃（expect: 现在的实现 exit 0）
#   main 有 openspec/specs/retry/spec.md；feature：git mv … src/x.md；check --base main --head HEAD
# I-3 stale review（expect: exit 0，乱填 base/head 也绿）
#   init→change+evidence→commit→再推 src-only commit→check
# I-4 glob 语义变异（expect: 80 passed 即「未被钉住」）
cp -r . /tmp/wl2 && PYTHONPATH=/tmp/wl2/src uv run pytest -q   # 注意先用必红变异自检基准
#   M10: paths.py ":40 [^/]* -> .*"   M11: ":34 (?:.*/)? -> (?:.*/)"
```

**证据文件**：`docs/gate.md`（glob 契约 §2、受保护两档 §5、退出码 §6）、`docs/design.md`（§5.3、§9 风险 3/7）、
`docs/tasks.md`（D3）、`src/witnessloop/{paths,checkcmd,contract,uninitcmd,policy,events}.py`。

---

_审阅方法：只读源码 + 真实 tmp git 仓复现 + `PYTHONPATH` 隔离的变异测试；未修改任何源码/测试/配置。_
