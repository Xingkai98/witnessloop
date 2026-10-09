# M2「交互层」独立审阅（全新零记忆 reviewer）

Verdict: PASS

> 审阅者：**全新零记忆 reviewer**。不信任何自述——自己读源码、自己造临时 git 仓用**真实 CLI** 跑、
> 自己做**变异**并还原。只读源码/测试/配置；**唯一写入的文件就是本报告**。
> 基线：`git diff main...mvp-m2/2026-10-09`（4 个 M2 提交）、`docs/design.md` §5.2/§5.3/§10、
> `docs/tasks.md` E1–E5、`docs/gate.md` §3/§3.1。
> 复核命令：`export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q` → **234 passed in 12.87s**（与自述一致）。

**结论摘要**：M2 的 5 条任务（E1–E5）**逐条真的做到了**，且核心机制经独立实测站得住：
`manifest build` 与 `check` 确为**同一张 `HASHED_ARTIFACTS` 表 + 同一个 `sha256_tree`**——我改一处常量，
`check` 侧与 `build` 侧的测试**同时变红**（25 failed），证明不是「两份看着像的实现」；round-trip 我自造临时仓
从 `init` 到 `check` **独立跑绿**，故意破坏一处 `check` **如期变红**；E1 的「内联即判红」不是假保护——
把模板正文粘进适配器，共同段被测出 **153 字符 ≥ 60**、测试变红。**没有发现 MUST-FIX**：无崩溃、无门禁绕过、
无误拦合法 PR。发现的 3 个 SHOULD + 4 个 NIT 均为 M2 新增代码的**健壮性/一致性/文档漂移**问题，
不影响门禁正确性，详见 §4。

---

## 1. 实际运行结果

```
$ export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q
234 passed in 12.87s
```

无跳过、无 xfail。`uv run witnessloop --version` → `witnessloop 0.1.0`。工作树审阅前后均 `git status --porcelain` 干净
（所有变异都 `git checkout --` 还原）。

### 1.1 复现环境（规避「venv 拷贝坑」）

本仓 `.venv` 的 editable `.pth` 指向绝对路径 `/home/happy/witnessloop/src`——`cp -r` 仓库会「测原件、变异假活」。
我全程**在真实仓原地变异、跑完即 `git checkout --` 还原**（每步都核对 `git status`），或用
`uv run --project /home/happy/witnessloop` 驱动真实 CLI 作用于`/tmp` 下的临时仓。临时仓与驱动脚本都在仓外。

---

## 2. 逐任务验证表

| 任务 | 声称 | 独立核验 | 结论 |
|---|---|---|---|
| **E1** 模板与适配器**物理分离** | `templates/{grill,review-loop}.md` vs `plugin/commands/{grill,review-loop}.md` | 两目录物理分开（`find` 确认）；适配器只**引用**模板路径、正文不重复；「共同段 ≥60 字符即判内联」经变异为**真保护**（见 §3.5） | ✅ |
| **E2** `grill`（零记忆追问 → 结构化决策记录） | 适配器接线 + 模板承载算法 | `templates/grill.md`：参与者「必须另起一个 run、零记忆」；步骤列决策点/逐条追问/产出 `Confirmed Decisions`+`Open Questions`（每条配例子+推荐）/`停轮`/`User Confirmation`；硬约束「缺证据不得进入实现」。适配器 `plugin/commands/grill.md` 只做接线（读 policy 定位 change 目录、起审阅 run、调 `manifest build`） | ✅ |
| **E3** `review-loop`（独立审阅 → 修复 → 再审，有界轮数） | 同上 | `templates/review-loop.md`：审阅→给结论（`PASS`/`CHANGES_REQUESTED` 二选一）→修复（每修复补一条**能变红的回归测试**）→再审；**轮数封顶默认 3**；收尾写报告并调 `manifest build`。适配器接线一致 | ✅ |
| **E4** 只读、无状态 | 不得持有自己的状态文件 | `plugin/` 仅 4 个文件（`plugin.json` + 2 命令 + `README.md`），无 `.cache`/`state.json`；`test_plugin_file_inventory_is_exactly_expected` 钉住清单；适配器明文声明「只读」「无状态」「以 manifest 为准」 | ✅ |
| **E5** `manifest build` 产出 `check` 认的 manifest，与 `check` 共用表+函数 | 见 §3 | 共用**实测成立**（变异同时影响两侧）；round-trip 独立跑绿；负例拒写；幂等/不 auto-commit 成立 | ✅（附 §4-1/§4-2） |

补：`cli.py` 把 `manifest` 加入子命令并 `cli.py:116-125` 处理「需要子命令」；`test_cli.py` 相应把动词面钉成
`{init,uninit,check,manifest}`。`resolve_base` 从 `checkcmd._resolve_base` **原样搬到** `gitutil.resolve_base`
（函数体逐字一致），`checkcmd.run` 与 `manifestcmd.run_build` 同调它——base 解析单一来源成立。

---

## 3. `manifest build` 重点核验

### 3.1 「共用同一张表 + 同一个哈希函数」——**真的共用**（不是两份像的）

消费点只有两处，都读同一常量、同一函数：

- `src/witnessloop/constants.py:55-58`：`HASHED_ARTIFACTS = (("tasks_hash","tasks.md"),("spec_hash","specs"))`
- `check` 侧：`src/witnessloop/contract.py:298` `for field, artifact in C.HASHED_ARTIFACTS:` + `sha256_tree(target)`（`:303`）
- `build` 侧：`src/witnessloop/manifestcmd.py:76` `for field, artifact in C.HASHED_ARTIFACTS:` + `sha256_tree(target)`（`:80`）

**变异证据（改一处，两侧同时受影响）**：把常量改成 `("spec_hash","specsX")`（不存在的目录）后跑全量 pytest：

```
25 failed, 209 passed
FAILED tests/test_manifest_build.py::test_round_trip_build_then_check_is_green
FAILED tests/test_manifest_build.py::test_hashes_use_the_same_implementation_as_check
FAILED tests/test_check_protected.py::test_protected_write_with_valid_event_passes
FAILED tests/test_invariants.py::test_adding_new_evidence_needs_no_event
FAILED tests/test_require_change.py::test_source_change_with_change_dir_passes
...（`check` 侧与 `build` 侧各有一批）
```

单改这一个常量能**同时**打破 `build` 写出的 manifest 与 `check` 的校验——这正是「单一绑定表」的结构性含义。
唯一不在表里的是 `report_hash`（路径动态），两侧分别用 `sha256_tree(report_file)`（`manifestcmd.py:81`）与
`sha256_tree(report_path)`（`contract.py:290`），**仍是同一个 `hashing.sha256_tree`**，文档也如实说明它单独处理。**真实共用。**

### 3.2 `head_sha` / `base_sha` 取值语义

- `head_sha = gitutil.rev_parse(root, "HEAD")`（`manifestcmd.py:83`）= 跑 build 时的 HEAD 提交，与 gate.md §3.2「在内容提交之后、证据提交之前跑」一致。
- `base_sha = rev_parse(root, resolve_base(root, args.base))`（`manifestcmd.py:86-87`）——**与 `check` 用同一个 `gitutil.resolve_base`**，缺省链（`WITNESSLOOP_BASE_REF` → `GITHUB_BASE_REF`→`origin/<ref>` → `origin/main|main|origin/master|master` → `main`）两边一致。
- `diff_hash` 用两点 `base_sha..head_sha` 的文本 sha256（`gitutil.diff_text`），informational，`check` 不校验内容（`contract.py:312`）。与文档一致。
- 实测（round-trip）：`head_sha` = 内容提交、`base_sha` = `main` tip、`report_path="reviews/building-review.md"`，字段集**恰为** gate.md §3 所列 12 项。

### 3.3 负例（是否**报错且不写出文件**）

| 负例 | 触发点 | 我实测 | 写出文件？ |
|---|---|---|---|
| `reviewer == author` | `manifestcmd.py:68-72` | exit 1，stderr 含「reviewer…author」 | **否** ✅ |
| `report_path` 逃逸 change 目录 | `:56-57`（`is_within`） | exit 1，含「逃逸」 | 否 ✅ |
| 报告不在 `reviews/` 下 | `:58-64`（`matches reviews/**`） | exit 1，含「reviews/」 | 否 ✅ |
| 报告文件不存在 | `:65-66` | exit 1，含「报告」 | 否 ✅ |
| 缺 `tasks.md` | `:78-79` | exit 1，含「tasks.md」 | 否 ✅ |
| change 目录不存在 | `:49-52` | exit 1，含 change id | 否 ✅ |
| 未接入（无 policy） | `:40-45` | **exit 3**，含「未接入」 | 否 ✅ |
| 仓里没有提交 | `:84-85` | exit 1，含「仓里还没有提交」。**我实测**（无提交仓 + init + 造 change 目录）成立 | **否** ✅ |

### 3.4 round-trip（自造临时仓，独立于仓库自带测试）

```
init → 内容提交 → manifest build → 证据提交 → check   ⇒ exit 0「check：通过 ✓」
```

随后故意破坏：build 之后改 `tasks.md` 再提交 → `check` **exit 1**，点名 `tasks_hash 不匹配` **且**「审阅的是旧 revision」。
真阳性在，不是空转。

### 3.5 E1「内联即判红」——**不是假保护**

`tests/test_plugin.py` 的 `MIN_INLINED_RUN=60` + `_longest_shared_run`（去围栏代码、归一空白后求最长共同段）。
我把 `templates/grill.md` 的「步骤」段（≈200 字符）逐字粘进 `plugin/commands/grill.md`：

```
E  assert 153 < 60
FAILED tests/test_plugin.py::test_adapter_does_not_inline_the_template[grill]
```

测出共同段 **153 字符**并变红——**真保护**。模板侧 `FORBIDDEN_TOKENS` + slash 正则也非空转（见 §4-3 的边界说明）。

---

## 4. Issues

无 MUST-FIX。以下按严重度排列。

### 4-1（SHOULD）`manifest build --change` 未做逃逸校验，可把 manifest **写到仓外**

`manifestcmd.py:47-48` 直接把 `args.change` 拼进路径：`directory = root / pol.changes_root / change_id`，
`:111-114` 又用同一个未校验的 `change_id` 拼出 `manifest_rel` 再 `mkdir`+`write_text`。而 `--report` 侧
（`:54-57`）有 `pathutil.is_within` 守卫——**两个来自同一 agent 的输入，一个守、一个不守**，属不一致。

**独立复现（真实 CLI，`/tmp` 下的临时仓）**：`--change "../../../../evilwl_$$"`，先造好目标目录：

```
$ witnessloop manifest build --root "$R" --change "../../../../evilwl_2914665" --stage building \
    --report reviews/building-review.md --reviewer-run-id a --author-run-id b
manifest build：已写入 openspec/changes/../../../../evilwl_2914665/reviews/building.manifest.json（未 commit）
exit=0
$ ls /tmp/evilwl_2914665/reviews/         # ← 仓外，落盘成功
building-review.md   building.manifest.json
$ git -C "$R" status --porcelain          # ← 仓内什么都没写
（空）
```

绝对路径 `--change /abs/dir` 只是把绝对段嵌进相对 `manifest_rel`、落进仓内的伪 change 目录（不逃逸），
但 `../` 形态**会逃逸到仓根之外**。**定级说明**：`build` 是作者本地跑的**生产者**，不构成门禁绕过，
也不是远程利用面；危害限于「在目标仓之外写文件 / 覆盖同名 `reviews/<stage>.manifest.json`」+
「与 `--report` 的加固哲学不一致」。**修法（便宜）**：对 `change_id` 也过一道 `is_within(directory, root/pol.changes_root)`
（或拒 `..`/绝对路径），与 `--report` 对齐；补一条负例测试。

### 4-2（SHOULD）`build` 绿灯但 `check` 红灯：`manifest build` 不校验 `required_artifacts`

`manifest build` 只校验 `tasks.md` 与 `specs`（即 `HASHED_ARTIFACTS` 两件，`manifestcmd.py:75-80`），
**不校验 `proposal.md` / `design.md` 等 `required_artifacts`**。于是可产出「build 报成功、check 立刻拒」的
不一致状态，削弱「证据回路闭合」的说法。

**独立复现**：change 目录只放 `tasks.md` + `specs/`（故意缺 `proposal.md`/`design.md`）：

```
$ witnessloop manifest build ...                      ⇒ exit 0（打印「已写入」，报成功）
$ witnessloop check --base main --head HEAD           ⇒ exit 1
  1. openspec/changes/add-retry：缺少必需件 proposal.md
  2. openspec/changes/add-retry：缺少必需件 design.md
```

**修法**：`build` 开头复用 `contract.validate_change_dir(root, pol, change_id)`，非空即 fail（不写文件）。

### 4-3（SHOULD）新动词 `manifest build` 引入后，设计/自述仍写「3 个动词」——文档漂移

M2 把动词面从 3 个扩到 4 个（+`manifest build`），但**权威设计**与几处自述没跟上，现在自相矛盾：

- `docs/design.md:64`「**v1 只交付 3 个动词**」；`docs/design.md:129`「单二进制 + 3 动词（`init`/`check`/`uninit`）」——
  design.md **全文不含** `manifest build` 这个词（grep 证实）。
- `src/witnessloop/__init__.py:3`「单二进制，只有 3 个动词（design §5.1）」。
- `README.md:7-8`「状态：M1 已实现（三动词）…交互层 CC plugin 是 M2，**尚未开始**」——**而同一文件**下方
  （M2 新增行）已在演示 `manifest build` 与 plugin 用法。同一 README 内前后矛盾。

`gate.md §3.2`、`tasks.md` E5、`cli.py` docstring 都更新了，漏的是 design.md 与这两处自述。
对一个「以不让文档漂移为核心卖点」的项目，这处漂移值得顺手收口：把 design §5.1/§10 与 `__init__`/README 的
「3 动词」更新为「3 门禁动词 + `manifest build`」，并在 design 里给这个动词一个出处。

### 4-4（NIT）`templates/*.md` 引用了 CC 适配器目录 `plugin/`

两份模板都在首段写「各 host 的适配器负责把它接到自己的命令入口（见 `plugin/`）」（`templates/grill.md:4`、
`templates/review-loop.md:4`）。模板自述「host 中立、不含任何 host 专有语法」，却点名了 CC 侧目录名 `plugin/`。
`FORBIDDEN_TOKENS` 不含 `plugin`，所以测试不拦。属跨引用而非算法正文，影响很小——建议改成中性措辞
（如「见各 host 的适配器目录」）或干脆不提。**（真 host 专有 token 我逐一 grep 过：`.claude`/slash/`Task`/
`subagent`/`frontmatter` 等在两份模板里**均无**，`test_templates.py` 的断言是可靠的。）**

### 4-5（NIT）内联保护测试只比「同名」模板，围栏代码被整体剔除

`test_adapter_does_not_inline_the_template` 只拿 `grill` 适配器比 `grill` 模板（同名）。因此：
(a) 把 **review-loop** 模板正文粘进 **grill** 适配器不会被抓；
(b) `_prose` 先 `_FENCE.sub` 删除围栏块——适配器若把算法整段塞进 ``` 代码块就绕开了检测。
同名主路径已证为真保护（§3.5），以上是检测边界，供日后加固参考。

### 4-6（NIT）「仓里没有提交」负例无测试

`manifestcmd.py:84-85` 这个分支我在真实 CLI 上验证过（exit 1、不写文件，见 §3.3），但 `test_manifest_build.py`
**没有**对应用例，`gate.md §3.2` 却把它列进了负例清单。补一条即可闭合。

### 4-7（NIT）`plugin/README.md:44` 自述不精确

「`plugin/` 目录里除了 manifest 和两条命令没有别的文件」——但 `plugin/` 里还有 **`README.md` 自己**
（`test_plugin_file_inventory_is_exactly_expected` 的 `EXPECTED_FILES` 恰为 4 项）。句子漏了自身，无害但可修。

---

## 5. 覆盖缺口

1. `build` 与 `check` 的**同一性**只在测试里以「共同常量」被间接验证（`test_hashes_use_the_same_implementation_as_check`
   遍历 `C.HASHED_ARTIFACTS`，天然与实现同源）。**没有**一条测试会再独立硬编码「`spec_hash` 应覆盖 `specs/` 整棵树」
   的形状——若哪天有人把常量改错（如指向 `tasks.md`），`check` 与 `build` 会「一起错」，round-trip 仍绿。
   我这次的变异正是靠**其它**测试（如 `test_round_trip_with_a_protected_spec_write` 会因 `specsX` 缺件而红）才变红。
   建议补一条**独立锚定** artifact 形状的测试。
2. `manifest build` 的 `diff_hash` 无任何内容校验（设计如此），因此「某人把整个 manifest 的 diff_hash 换成常量」
   不会变红——属可接受的 informational 取舍，记录备查。
3. `--change`/`--stage` 的输入域未做形状约束（§4-1 是其中逃逸面）；`--stage` 值域任意（`a/b` 会嵌套到 manifest 文件名，
   但仍在 change 目录内，低危）。

---

## 6. 停轮问题（需人拍板）

**Q1（对应 §4-1 + §4-2）这两处「build 侧健壮性」要不要在 M2 收口，还是记入 M3？**
- 现状：都不影响门禁正确性（`check` 仍 fail-closed），但 (a) `--change` 可写到仓外、(b) `build` 绿灯/`check` 红灯。
- 选项：(a) **本轮顺手修**（两处都便宜：`change_id` 加 `is_within`、`build` 复用 `validate_change_dir`，各补一条负例）；
  (b) 记入 M3 任务清单，M2 维持现状。我的倾向：**至少把 §4-2 修掉**（一行复用现成校验，直接消除「build 说成功、check 说失败」的
  自相矛盾），§4-1 视成本一并做。

**Q2（对应 §4-3）design.md 是否补记 `manifest build` 这个动词？**
- 现状：design §5.1/§10 仍写「3 个动词」，与已交付的 CLI 矛盾；README 自身前后矛盾。
- 选项：(a) 本轮把 design §5.1/§10 + `__init__`/README 更新为「3 门禁动词 + 支撑动词 `manifest build`」（推荐，维护者信任的前提是设计即事实）；
  (b) 承认 design 冻结于 M1，M2 动词另立小文档。倾向 (a)。

**Q3（对应 §4-4）模板引用 `plugin/` 的中性化**：改措辞（零成本）还是接受为「可读性优于纯中性」？我倾向前者，但不阻塞。

---

## 7. 复现清单（可照跑）

```bash
export PATH=/home/happy/.local/bin:$PATH
cd /home/happy/witnessloop && uv run pytest -q                  # 234 passed

# §3.1 共用表：改 constants.py:55 的 "specs"→"specsX"，跑全量 → 25 failed；再 git checkout -- 还原
# §3.5 内联保护：把 templates/grill.md 的「## 步骤」段粘进 plugin/commands/grill.md
#        → test_adapter_does_not_inline_the_template[grill] 报 "assert 153 < 60"
# §3.4 round-trip：临时仓 init→内容提交→manifest build→证据提交→check(exit0)；
#        再改 tasks.md 提交 → check(exit1，tasks_hash 不匹配 + 旧 revision)
# §4-1 --change 逃逸：mkdir -p /tmp/evilwl/{specs/x,reviews} 并放齐 tasks.md/specs/报告，
#        witnessloop manifest build --change "../../../../evilwl" … → exit0，/tmp/evilwl/reviews/building.manifest.json 落盘
# §4-2 build 绿灯/check 红灯：change 目录只放 tasks.md+specs → build exit0；check exit1「缺少必需件 proposal.md/design.md」
```

**证据文件**：`src/witnessloop/{manifestcmd,constants,contract,gitutil,checkcmd,cli,__init__}.py`、
`plugin/{.claude-plugin/plugin.json,README.md,commands/{grill,review-loop}.md}`、
`templates/{grill,review-loop}.md`、`tests/{test_manifest_build,test_plugin,test_templates,test_cli}.py`、
`docs/{design,gate,tasks}.md`、`README.md`。

---

_审阅方法：只读源码 + 自造 `/tmp` 临时 git 仓用**真实 CLI** 端到端复现（含故意破坏）+ 原地变异后
`git checkout --` 还原（每步核对工作树干净）。未修改任何源码/测试/配置；唯一写入的文件为本报告。_
