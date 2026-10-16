# Grill（对抗轮 R6）：gate-ref-pins-package —— 独立零记忆证伪

> 我是**独立零记忆**的对抗验证者：本对话不携带该 change 的任何历史。`proposal.md` / `design.md` /
> `tasks.md` / `spec.md` 与五份 review（R1 `grill-adversarial.md`、R2 `-r2`、R3 `-r3`、R4 `-r4`、R5 `-r5`）
> 里的「实测」「已落库」「已裁定」「已收敛」「零命中」一律当**待验证断言**，可复算的一律复算，
> **目标是证伪结论本身**。

## Reviewer

**读了什么**（全文实读，非 grep 采样）：`openspec/changes/gate-ref-pins-package/` 的 `proposal.md`、
`design.md`（含 §1 现状、§2 D1–D7、§3 接线点、§4 风险表、§5 测试策略、§7.9 全部对抗轮记录、§8 裁定）、
`tasks.md`、`specs/gate-ref-pinning/spec.md`；`reviews/` 的 R1–R5 五份报告（**含每份文末的「## 处置」**）；
实现面 `src/witnessloop/{initcmd,checkcmd,constants}.py`、`.github/workflows/gate.yml`、`docs/gate.md`、
`README.md`、`docs/design.md`；测试面 `tests/test_{init_gate_ref,check_package_ref,gate_workflow,docs}.py`
与 `tests/conftest.py`。

**基准 revision（本仓在本轮审阅期间被并发移动了**四次**，这一节必须读）**

| 时刻 | HEAD | 说明 |
|---|---|---|
| 我开始时 | `bd80b1d` | 我读文档/源码、做**前四批**变异实验的树；工作区**不干净**（见 §A） |
| 审阅中 | `b71f457` | 主 session 落库：我发现的**两处未提交测试**（+ 一条清单） |
| 审阅中 | `a66d51c` | `tasks.md` 勾选已完成项（纯勾选） |
| 审阅中 | `4538404` | 主 session 落库：**订正 `design §2 D1` 的判定顺序** + 新增判定顺序的钉子 |
| 审阅中 | `8297b82` | 主 session 落库：**为「两步 recipe 顺序不能反」补机械钉子**（`docs/gate.md` + `README`） |

**本报告的行号/blob 一律以 `8297b82` 为准**（= 我收尾时逐条复核的那棵树）。凡在 `bd80b1d` 或工作区上做的
变异，都单独标注树名。**关键事实：`src/` 在 `bd80b1d..8297b82` 之间一字未改**
（`git diff --stat bd80b1d..8297b82 -- src/` 为空）⇒ 我在 `bd80b1d` 的 `src/` 上测到的**实现行为**，
在 `8297b82` 上逐条成立（已在新树重跑关键项确认）。

| 文件 | blobs（`bd80b1d`） | blobs（`8297b82`） |
|---|---|---|
| `HEAD` | `bd80b1d288b14cd0ed5f5b9fdd3a3b24dec7bf02` | `8297b822a10a2eba4c7367694476dacf17bd26f0` |
| `src/witnessloop/initcmd.py` | `b33f40839215…` | `b33f40839215…`（**未变**） |
| `src/witnessloop/checkcmd.py` | `e12db4d94a1d…` | `e12db4d94a1d…`（**未变**） |
| `src/witnessloop/constants.py` | `0a64184d5435…` | `0a64184d5435…`（**未变**） |
| `.github/workflows/gate.yml` | `ddaabddf2442…` | `330104b810db…`（仅注释块） |
| `docs/gate.md` | `f79b48f8eaa2…` | `f79b48f8eaa2…`（**未变**） |
| `README.md` / `docs/design.md` | `700ade12d4ab…` / `dcbc79bd8fcd…` | 同 |
| `…/design.md` | `199d79c426c3…` | `cfcf10aad8db…`（§2 D1） |
| `…/tasks.md` | `ae81bcdef726…` | `7313e9f157b5…`（勾选） |
| `…/specs/…/spec.md` | `de8cc896c93e…` | `de8cc896c93e…`（**未变**） |
| `tests/test_init_gate_ref.py` | `ab18c335ae40…` | `e785c87a441e…` |
| `tests/test_check_package_ref.py` | `b9e2f2f6b03a…` | `dba4a2912bec…` |
| `tests/test_gate_workflow.py` | `6d68b0a700b0…` | `fb3972f4b030…` |
| `tests/test_docs.py` | `c3516c31b828…` | `ffc35fec04a3…` |

**快照方式（前几轮的事故教训已遵守）**：一律 `tar --exclude=./.git` 或 `git archive HEAD | tar -x -C …`
（**不用** `cp -a`——本目录是 linked worktree，`.git` 是指针文件，`cp -a` 会把指针带过去，
在副本里 commit 等于在真仓 commit）。所有实验在 `/tmp/adv6/`。**真仓我一个字节都没改**（除本报告）；
收尾时 `git status --porcelain` 只有本报告未跟踪、`HEAD = 8297b82`。

**实际跑了什么（命令 + 原始输出要点）**

1. **基线全量**：`bd80b1d` 导出树 ⇒ **676 passed**；工作区（含两处未提交测试）⇒ **678 passed**；
   `8297b82` ⇒ **680 passed**。三次都全绿。
2. **变异电池（本轮的主手段）**：每条 = 一份新副本 + **一次**精确替换（脚本断言命中恰好 1 次）+
   `PYTHONPATH=src python3 -m pytest -q -n 2` **全量**。共 **44 次**全量运行（同一变异在多个树上重跑的分别计入；另有一次因 OOM 被杀、已重跑），逐条结果见 §C 的表。
   （`-n 2`：本机 7.8 GB 内存，`-n 4` 跑到第 22 条时被 OOM 杀掉一次，已改小并重跑。）
3. **`sync_caller_gate_ref` 四个 `return None` 分支**：逐分支变异（§C 的 A 组）。
4. **`_already_initialized` 的 `ignore` / `handled`**：去掉过滤 / 传空 / 合成常量 / 传 `None`（B 组）。
5. **`vcs_info_from_direct_url` 的 `_text`**：三种改写（C 组）。
6. **`gate.yml` 解析优先级**：关掉 ②、去掉 `REPO_SLUG` 守卫、把「不匹配 ⇒ 落 workflow_ref」写回去（D 组）。
7. **`docs/gate.md §1.2` 两步 recipe**：删 ①、改编号、整行反序（E 组）。
8. **`gate.yml` 解析 step 交真 `sh` 跑**（env 照抄 step 的 `env:`）：`repository=someone/fork` +
   可用的 `workflow_ref=…@refs/heads/main`（无 sha）⇒ **`ref=v1`**（退兜底）；同形态但 repository 匹配
   ⇒ **`ref=main`**。原始输出见 §C2。
9. **P1 的端到端复现**（`/tmp/adv6/e2e` 一次性 git 仓，真跑 CLI）：台账 `created_files` 改成 dict ⇒
   `init --gate-ref …@v9.9.9` ⇒ `init：…结构非法（created_files 不是数组）：无法核对台账漂移。`、
   **EXIT=1**、caller 与台账**一字未动**；plain `init` 同一条诊断、EXIT=1（§C4）。
10. **`installed_vcs_ref` 的宽 `except`**：monkeypatch `importlib.metadata.distribution` 抛
    `KeyboardInterrupt` / `SystemExit` ⇒ 实测两者**都照常传播**（`OK 传播: KeyboardInterrupt` /
    `OK 传播: SystemExit`）——独立复算 R5 的题面项结论，**成立**。
11. **本仓自举**：`git rev-list --count v1..origin/main` = **47**（复算 K5）；
    `git ls-remote --tags origin` 最大 = **`v1.6.0`**（`v1.6.0^{}` = `ae99256…`）⇒ 无 `v1.7.0`；
    `git ls-remote --heads origin | grep -i probe` ⇒ **exit 1（远端无 probe 分支）**；
    `git branch` 本地**仍留** `probe/workflow-ref`（K8 措辞与事实一致）。
12. **`check --root . 2>/dev/null | head -1`**（`docs/gate.md §1.2` 的 ①′ recipe）在**未接入**目录里实测：
    第一行确为 `check：本包来源（自报，尽力而为）：requested_revision=<未知>，commit_id=<未知>`、
    `rc=3` ⇒ M4 的「旧包没有这一行」那半条机制**可复算**。

**没能复算的**：见「未验证项」。

---

## 对抗结论

### A 交给本轮的 revision **工作区不干净** —— 两条「本轮点名面」在被审 revision 上没有钉子

**事实（收尾时已消失，但它是本轮输入的一部分，必须记）**：我开始时 `git status --porcelain` 是

```
 M tests/test_check_package_ref.py
 M tests/test_init_gate_ref.py
```

两份改动**未提交**，且正是本轮题面点名的两个变异面的钉子
（`test_an_unparseable_ledger_is_loud_and_untouched` 的 docstring 自述「对抗轮 R6 的变异面之一」；
`test_empty_string_fields_are_treated_as_absent` 钉 `_text` 的空串判定）。
后果是**可复算**的：在**已提交**的 `bd80b1d` 上（`git archive HEAD` 导出）跑同样的变异 ⇒

```
=== A1h_badjson_repair [bd80b1d] rc=0 :: 676 passed      ← 台账坏 JSON 分支改成「照写」：无红
=== C1h_empty_ok_head   [bd80b1d] rc=0 :: 676 passed      ← _text 收下空串：无红
```

⇒ **按「被审 revision = 提交物」读，这两个分支当时没有机械钉子**；按「工作区」读则有。
`b71f457` 已把它们落库，我在 `8297b82` 重跑同一变异 ⇒ 各 **1 failed**（§C N1/N2）。

**这条不是措辞、不是计数**：它决定「把被审 revision 定为哪个」会改变判据①的结论。
⇒ 记入 §D1，并在「收敛结论」里作为判①的输入。

### B 判据②：前五轮「必须修改项」逐条落库复核（去正文/代码里核，**不核 §7.9 自述表**）

**R1 的 K1–K8 —— 全部落进正文/实现 ✅**

| # | 要求 | 我在正文/代码里核到的落点（`8297b82`） |
|---|---|---|
| K1 | 删/改「包无法自报 ref」 | `design.md:136-154`（§2 D3 明写「**R1 K1 订正（原稿此处为假）**」）+ `spec.md:60-82` 的「`check` SHALL 自报…（尽力而为）」Requirement + `checkcmd.py:55-76,79-91` 的实现与 `tests/test_check_package_ref.py` 的钉子 |
| K2 | 改「没有任何提示」 | `proposal.md:19-29` 整节标题即「⚠️「没有任何提示」是**假**的（对抗轮 R1 的 K2 实测证伪，此处已改写）」 |
| K3 | 「永久死锁」降级 | `design.md:124-129`「**响亮、可恢复的分叉态**」+ 三条恢复路径（`git checkout --` / `rm` / `sha256: null`）+「`check` 不读台账 ⇒ 分叉期间门禁照常」（我复核 `checkcmd` 全文无 `INIT_MANIFEST`） |
| K4 | 自证行在 (A) 下矛盾 | `design.md:156-171`（§2 D4：本 PR **不做**本仓迁移，两条理由） |
| K5 | 「47 个提交」计数 | `design.md` 正文已去计数；我**独立复算** `git rev-list --count v1..origin/main` = **47** ⇒ K5 行「取决于测量哪个 ref」成立（仅 §7.9 的历史表里保留该数字） |
| K6 | 补 `docs/design.md:56,73` | `:56` 是**历史引文** + 指向 `docs/gate.md §1.2`；`:73` 已改 `uses: …@<ref>` 并写明「这一个 ref **同时**决定 workflow 文件与 witnessloop 包版本」（两处实读） |
| K7 | 登记 `sha256: null` 出口 | `design.md:130-134`（§2 D2 末条）+ `D6`（`:177-179`，明确**不**收紧） |
| K8 | 探针落点/清理 | `design.md:67-97`（原始输出即落点 + 「**远端已清理**、**本地仍留** `probe/workflow-ref`」+ 证据等级标注）+ `tasks.md:41-46`（3.0）；我复核远端**无** `probe/*`、本地**仍在** ⇒ 措辞与事实一致 |

**R2 的 L1–L6 —— 全部落库 ✅**（L3 我**实踩**验证有效性）

| # | 要求 | 落点 |
|---|---|---|
| L1 | post-merge 时序 | `tasks.md:86`（6.1 **先**改默认值）在 `:124`（6.2 **再** tag「含 6.1 改动」的 main）**之前**；`:125-126`（6.3）把 `README.md:20` 的新值与 tag 放同一提交。**顺序对** |
| L2 | recipe 补「先升 CLI」 | `docs/gate.md:82-110`（两步 + 旧 CLI 的 EXIT=1 与误导文案 + 「别去删 policy」）+ `README.md:188-196` |
| L3 | `inputs.witnessloop-ref.default == ""` 的钉子 | `tests/test_gate_workflow.py:466-479`；**我实踩：改回 `"v1"` ⇒ 该条红**（§C L3h） |
| L4 | 写死 `--gate-ref` × 冲突 `--policy` | `spec.md:120-126` 的 Scenario + `initcmd.py:307-311`（`handled`）+ `tests/test_init_gate_ref.py:233-261`（两面都钉） |
| L5 | spec 补两条 Scenario | `spec.md:106-111`（`--dry-run`）、`:113-118`（台账缺 caller 条目） |
| L6 | 点名**两类**仓 | `design.md:214`（§4 R2）+ `docs/gate.md` 的「发布面」段（两类仓 + 回退路径）+ `tasks.md:128-132`（6.5）——三处都在 |

**R3 的 M1–M4 —— 全部落库且有效 ✅**

- **M1**：`tests/test_init_gate_ref.py:28` `NEW_REF = …@v9.9.9` + `:46-48`
  `test_new_ref_does_not_collide_with_the_factory_default`；`tasks.md:95-98` 写明「没有第 4 处要改，
  但有一条前提要保住」。**我按字面模拟 6.1 的三处字面量改动**（`constants.DEFAULT_GATE_REF` →
  `@v1.7.0`、`gate.yml` 的 `WL_FALLBACK_REF` → `"v1.7.0"`、`test_gate_workflow.py:59` 的断言 → `@v1.7.0`）
  ⇒ **680 passed**（§C H61h）⇒「一处改不动」的病已治好。我另核：全仓 `gate.yml@v1` 字面量**只剩**
  `constants.py:22` 与 `test_gate_workflow.py:59` 两处（+ `gate.yml` 的 `"v1"`）⇒ 清单**完整**。
- **M2**：`docs/gate.md:210-232`（§3）写明「**每一份报告各配一份 manifest**」+ 同名覆盖陷阱 +
  两条可选落法；`tasks.md:71-77`（5.2）与 `:16-19`（0.4）各补一步。我复核
  `openspec/changes/archive-arrival-recognition/rounds/` **确实存在**（先例属实），
  本 change 的 `reviews/` 下 **0 份** `.manifest.json` ⇒「未混用」成立。
- **M3**：`tasks.md:114-118` 改成「`head_sha` 之后**只允许证据文件**」+ 正确顺序（先落代码 →
  提交 → 再重建 manifest）+ `:120-123` 指出重建 manifest 属**修改**不变集、要一条解释事件。
- **M4**：`docs/gate.md:90-100` 与 `README.md:202-204` 都补了 ①′ 与「旧的 `@v1` 包**没有**这一行」；
  我**实跑** `check --root . 2>/dev/null | head -1`（未接入目录）⇒ 第一行确是那一行、`rc=3`（§Reviewer 12）。

**R4 的 N1–N3 —— 全部落库且有效 ✅**

- **N1**：`tests/test_init_gate_ref.py:297-328` `test_ledger_without_a_caller_entry_is_repaired`；
  **我变异验证**：把补条目分支改成 `entries.append(…)` ⇒ 该条红、**其余 677 条绿**（§C F2）
  ⇒ 钉子**有效**且该分支**仅**它覆盖。
- **N2**：`initcmd.py:291` 的 `note` 不再自称「其余文件无改动」；钉子
  `test_rewrite_and_a_tests_write_do_not_contradict_each_other`（`tests/test_init_gate_ref.py:75-88`）。
- **N3**：三处漏网已改（`docs/gate.md:518-520`、`design.md:218`、`tests/test_gate_workflow.py` 四条
  docstring）；**我跑 R5 原有的那条命令**（`src/ tests/ docs/ README.md .github/`，不含 `openspec/`）
  ⇒ **exit 1（零命中）**，属实。再加扫 `openspec/changes/gate-ref-pins-package/` 后命中的全是
  **历史引文 / 审阅报告自身 / 机制描述的正确写法**（「兜底 ref（= `DEFAULT_GATE_REF` 的 ref 部分；
  今天 = `v1`）」）⇒ 无残留的**现行**错误断言。

**R5 的 P1 —— 已落库、我独立变异确认它真会红 ✅**

- 落点三层齐备：① `initcmd.py:173-174`（`created_files` 不是数组 ⇒ `return None`，**不写**）；
  ② `initcmd.py:191-213` 的 `_set_ledger_gate_ref` 不再兜（注释写明「调用方已保证是数组」）；
  ③ `initcmd.py:400-411` 的 `_already_initialized` 补**受控**诊断「结构非法（created_files 不是数组）」
  + 退 1（顺带堵上 dict 迭代出字符串键的既有崩溃面）。
- **我自己的变异**（§C A3/A3c）：在**已提交的** `bd80b1d` 上把两层**一起**退回旧行为
  （去掉 `sync_caller_gate_ref` 的守卫 **且** 恢复 `_set_ledger_gate_ref` 的 `entries = []` 重建）
  ⇒ **1 failed**，红的正是 `test_a_malformed_ledger_is_loud_and_never_rebuilt` ⇒ **钉子真会红**。
- **端到端复算**（§Reviewer 9）：修后行为是「受控失败 + 一个字节不动」，与旧行为（静默重建、
  EXIT=0、随后 `uninit` 报「已回滚」而 `policy.json` 留在盘上）相反 ⇒ **P1 确实堵住了**。

**⇒ 判据② 成立。**

### C 判据①：本轮的变异审计（题面点名的五个面 + 我另加的）

> 逐条格式：**变异 → 结果 → 该面是否被钉住**。树名见括号；`wt` = `bd80b1d` + 当时工作区的两处未提交测试。

**C1 题面点名的面**

| 变异 | 结果（全量） | 判定 |
|---|---|---|
| **① 台账坏 JSON**：`except …: return None` → `manifest = {"schema":…, "created_files": []}`（"帮它修好"） | `wt` **1 failed**；**`bd80b1d` 676 passed**；`8297b82` **1 failed** | `wt`/`8297b82` ✅；**被审 revision ❌**（§A） |
| **② ref 相同**：去掉 `manifest.get("gate_ref") == gate_ref` | `wt` **1 failed**（`test_same_ref_is_a_noop`） | ✅ |
| **③ `created_files` 非数组**：删掉 `initcmd.py:173-174` 的守卫 | `wt` **1 failed** | ✅ |
| **④ caller 文件不存在**：删掉 `initcmd.py:176-177` 的 `if not path.is_file()` | `wt` **1 failed**（`test_missing_caller_is_not_resurrected`） | ✅ |
| **`ignore`**：去掉 `initcmd.py:466` 的过滤 | `wt` **2 failed** | ✅ |
| **`ignore`**：调用点传 `ignore=()` | `wt` **2 failed** | ✅ |
| **`handled`**：两条分支合成同一常量（R5 的 C1 原案） | `wt` **1 failed**；`bd80b1d` **1 failed** | ✅（R5 的补钉**有效**） |
| **`handled`**：调用点传 `handled=None` | `wt` **2 failed**；`bd80b1d` **2 failed** | ✅ |
| **`_text` 空串**：`and value` 去掉（收下空串） | `wt` **1 failed**；**`bd80b1d` 676 passed**；`8297b82` **1 failed** | `wt`/`8297b82` ✅；**被审 revision ❌**（§A） |
| **`_text` 类型**：改成「非 None 即收」 | `bd80b1d` **1 failed** | ✅ |
| **`_text` 类型**：改成「truthy 即收」 | `wt` **1 failed** | ✅ |
| **gate.yml ②/③ 调换**：把 sha 分支短路掉（`&& false`） | `wt` **1 failed**（`test_resolve_prefers_the_reusable_workflows_own_sha`） | ✅ |
| **`REPO_SLUG` 判据挪到 sha 之后/去掉**：删掉该 `elif` | `wt` **1 failed** | ✅ |
| **`docs/gate.md §1.2` 删「① 先升 CLI」** | `wt` **1 failed**；`bd80b1d` **1 failed** | ✅ |
| **`docs/gate.md §1.2` 改编号（`1.`/`2.` 互换）** | `wt` 678 / `bd80b1d` 676 / `8297b82` **680 passed** | ⚠️ **不红**——但**渲染序未反转**（两条 bullet 的文字各自没动，「先/再」仍指同一件事）⇒ **不是语义反转**，见 §D3 |
| **`docs/gate.md §1.2` 整行反序**（把「再 `init`」那条搬到前面，真·渲染序反转） | `8297b82` **1 failed**（`test_gate_recipe_puts_the_cli_upgrade_before_the_ref_change`） | ✅（新钉子对**真反转**有效） |

**C2 我另加的一条：`design §2 D1` 第 3 条的触发条件与实现/spec 相矛盾（本轮已由 `4538404` 落库）**

`bd80b1d` 的 `design.md:42-43` 写：「3. 否则（**repository 不匹配** / sha 为空）⇒ 尝试
`job.workflow_ref` 的 `@` 之后那段…」，而 `gate.yml` 的实现里 **repository 不匹配时根本走不到那里**
（`gate.yml:81-82` 直接置 `FAILED` ⇒ 退兜底）。`spec.md:17-18` 与实现同向（「否则退回**兜底 ref**」）。
**可观测差别（我交真 `sh` 跑解析 step，原始输出）**：

```
A) repo=someone/fork + 可用的 workflow_ref（无 sha）
   (0, ['ref=v1'], '::warning::witnessloop 包 ref 解析失败，退到 v1 —— job.workflow_repository=「someone/fork」≠「Xingkai98/witnessloop」…')
B) repo 匹配 + 可用 workflow_ref（无 sha）—— 对照组
   (0, ['ref=main'], '::notice::witnessloop 包 ref = main（来源：job.workflow_ref 的分支名…）')
```

⇒ 旧文（若照它实现）预测 A 得 `ref=main`，实测是 `ref=v1`。**这是「change 自己新写的机制描述是假的」**，
不是措辞/计数。`4538404` 已把 `design.md:36-60` 按实现的分支顺序重写（①input ②repository ③sha
④workflow_ref ⑤兜底，且写明「**判定顺序即实现**」），并把 `gate.yml:34-45` 的注释改成同样五条；
新增钉子 `tests/test_gate_workflow.py:507-521`
`test_repository_mismatch_does_not_fall_through_to_workflow_ref`。**我在 `8297b82` 重跑同一变异
（让不匹配落到 workflow_ref）⇒ 1 failed**（§C N3）⇒ 修法有效。

**C3 其余变异（对照 / 覆盖度）**

| 变异 | 结果 | 判定 |
|---|---|---|
| 作用域守卫 `if manifest_path.is_file():` → `if True:` | `wt` **178 failed / 102 errors** | ✅（与 R5 的 175 failed 同向） |
| 删 `check` 的 `_report_package_source()` 调用 | `bd80b1d` **3 failed** | ✅ |
| 补条目 `entries.insert(at, …)` → `append(…)`（N1） | `wt` **1 failed** | ✅ |
| `_set_ledger_gate_ref` dry-run 下仍写盘（`if dry_run:` → `if False:`） | `wt` **2 failed** | ✅ |
| 只恢复 `_set_ledger_gate_ref` 的 `entries = []` 重建（**不**动守卫） | `wt` 678 / `8297b82` **680 passed** | ⚠️ 不红，但该分支**不可达**（唯一调用点是 `initcmd.py:185`，已被守卫拦住）⇒ 纯纵深防御，见 §D4 |
| 删 `initcmd.py:180` 的 dry-run `print(…)` | `wt` 678 / `8297b82` **680 passed** | ⚠️ 不红——纯屏幕文案（返回的 note 仍含「[dry-run] 未落盘」），见 §D5 |
| 去掉 `_set_ledger_gate_ref` 的 `and not entry.get("self")` | `bd80b1d` 676 / `8297b82` **680 passed** | ⚠️ 不红——只有**手造**一个 `self:true` 的 caller 条目才会分歧（R5 已登记为低危） |
| 删 `README.md` 的 `uv tool install … # ① 先升 CLI` 那一行 | `bd80b1d` 676 passed；`8297b82` **1 failed** | `8297b82` ✅（新钉子顺带覆盖） |
| 模拟 `tasks.md §6.1` 的三处字面量改动（M1） | `bd80b1d` **676 passed** | ✅ |

**C4 P1 的端到端原始输出**（`/tmp/adv6/e2e`，真 CLI）

```
init：.witnessloop/init-manifest.json 结构非法（created_files 不是数组）：无法核对台账漂移。
EXIT=1
caller 未动 ✓ ; 台账里 "not-a-list" 仍在（1 处）
plain init ⇒ 同一条诊断，EXIT=1
uninit    ⇒ witnessloop：内部错误（AttributeError: 'str' object has no attribute 'get'）  EXIT=1
```

⚠️ 最后一行**不是**本 change 的新项：`uninitcmd.py:42` 的 `for entry in manifest.get("created_files", [])`
在 `v1` 树上**逐字相同**（`git show v1:src/witnessloop/uninitcmd.py` 同行同内容）
⇒ 按纪律**只登记**（§D6）。

### D 低危观察（**不是**必须修改项）

1. **被审 revision 的工作区不干净**（§A）：`bd80b1d` + 两处未提交测试。`b71f457` 已落库；
   **规范动作**是：一轮开始前明确声明「被审 revision」，并保证它干净——否则「提交物」与「工作区」
   两个读法会给出相反的判①结论。
2. **`design §2 D1` 第 3 条的触发条件写错**（§C2）：`4538404` 已改。属**本轮新证伪项**，
   已在被审 revision 之后落库。
3. **`docs/gate.md §1.2` 的 recipe 顺序钉子在「只改编号」形态下不红**：`8297b82` 的
   `tests/test_docs.py:285-299` 对 `docs/gate.md` 那半查的是**字面量先后**
   （`gate.index("先把 CLI 升上去") < gate.index("witnessloop init --gate-ref")`），
   把 `1.`/`2.` 互换 ⇒ 680 全绿。**但**：① 两条 bullet 的文字各自没动，「先/再」的语义仍正确；
   ② **真·渲染序反转**（整行搬位）**会红**（我实测，§C E 组最后一行）。⇒ 记**观察**，不判必须修改。
   README 那半用的是代码块内**行序**，对两种形态都红（我实测两种都红）。
4. **`_set_ledger_gate_ref` 的「不再兜 `created_files`」是纯纵深防御**：恢复旧重建逻辑**不红**
   （`8297b82` 680 passed），因为它的**唯一**调用点 `initcmd.py:185` 已被 `:173-174` 的守卫拦住。
   当前正确，但**它没有独立钉子**——若将来出现第二个调用点，这条保护会静默失效。
5. **`initcmd.py:180` 的 dry-run `print(…)` 无钉子**：删掉全量仍绿（`8297b82` 680 passed）。
   纯屏幕文案，用户可见的那句（返回的 note）仍由 `:181` 提供 ⇒ 无行为后果。
6. **`uninit` 对 `created_files` 非数组的台账仍是「内部错误」**（§C4）：
   `uninitcmd.py:42` 在 `v1` 树上同款 ⇒ **先于本 change 存在**，不计入本 change。
   ⚠️ 但 R5 的「处置」里那句「顺带堵上「dict 迭代出字符串键 ⇒ `AttributeError` 冒到入口」的**既有**崩溃面」
   若被读成**全仓**范围则不成立——被堵的只有 `initcmd._already_initialized` 那一处。
7. **`docs/gate.md §7.1` 的 GHES 承诺缺一个前提**：`:515-521` 写「两种情形都落到 fail-closed 退回兜底 ref…
   区别只在日志里有一行 `::warning::`（不静默）」，而 `gate.yml:108` 的 `>> "$GITHUB_OUTPUT"`
   **刻意不兜底**（未定义 ⇒ 脚本当场退 2）。若某 runner 不提供 `GITHUB_OUTPUT`，那台机器上是
   **第一个 step 就硬红**，warning/notice 都还没打 ⇒ 与 §7.1 的描述不一致。
   R5 已把「GHES/自建 runner 上 `GITHUB_OUTPUT` 会不会缺省」列为**本工作区不可验证**
   ⇒ 我按同一纪律**只登记**（若要把它当 GHES 的行为承诺，需加一句「前提：runner 提供 `GITHUB_OUTPUT`」）。
8. **`tests/test_gate_workflow.py:504` 的 `assert "ref=v1" in …` 是不带单源的弱字面量**：
   它从 step 的 `env` 里取 `WL_FALLBACK_REF` **不**参与，改成 `@v1.7.0` 后靠**子串**（`"ref=v1"` 是
   `"ref=v1.7.0"` 的前缀）继续通过——我按 6.1 模拟验证过（§C H61h 680 passed）。当前无害，
   但它是「将来把兜底改成不以 `v1` 开头就会静默失效」的那种断言。**先于本 change 存在**（`v1` 树同款）。
9. **`design.md §1`/§2 D2 的行号引用指向 `v1` 树**（如 `initcmd.py:192/193/251`、`:205/:301`）：
   在当前树上已漂（`:192` 现在是 `_set_ledger_gate_ref` 的 docstring）。但我逐条核过它们
   **在 `v1` 树上逐字命中**（`git show v1:src/witnessloop/initcmd.py | sed -n '192p'` 等），
   而该节标题就是「现状（逐行实测）」⇒ 它是**改动前**的快照，**不是**错误引用。只登记。

---

## 未验证项

> 每项写「若假设相反会怎样」。**都不是必须修改项**——我逐条查过：`design.md:87-94` 已给探针输出标
> 「单一来源、不可复现的二手文本」；`docs/gate.md:522-523` 已把自建 runner / `pip install git+…`
> 列为未验证面 ⇒ **没有被写成已验证**。

1. **`job.workflow_sha` / `job.workflow_repository` / `job.workflow_ref` 在 called workflow 里的运行期取值**，
   以及 Q1 探针（run `38853369550`）的原始输出：本工作区没有可跑的 GitHub Actions；分支/文件已删
   （我复核远端无 `probe/*`）；唯一载体是 `design.md:67-77` 的粘贴块。
   **若假设相反**（`job.workflow_sha` 实为 caller 的 commit）：每个接入方会**全量硬红**（不是静默吃旧包），
   且 `design.md §2 D1` / `gate.yml:47-52` / 三份 spec Scenario 与四条 `test_gate_workflow` 用例的**叙述**
   都要改（实现只用 `job.*`，行为本身不由这个假设决定，但**「用 `job.workflow_sha` 才对」这条判据**会塌）。
2. **真 `uvx --from git+https://github.com/Xingkai98/witnessloop@v1.7.0 …`**：`v1.7.0` **不存在**
   （`git ls-remote --tags origin` 最大 = `v1.6.0`）⇒ 我没跑过真命令；`tasks.md §6.7` 的验收命令仍是**前瞻性**的。
   **若假设相反**（tag 建错位置）：6.7 的三条自查里「`git show v1.7.0:… | grep DEFAULT_GATE_REF` 含 `@v1.7.0`」
   会红——那正是 L1 设计的护栏，所以它**有**兜底。
3. **GHES / 同 owner fork / 自建 runner 的 uv 版本差异 / `pip install git+…` 是否同样落 PEP 610 `vcs_info`**：
   未验证（`docs/gate.md:522-523` 已如实登记）。**若假设相反**（`pip install git+…` 不落 `vcs_info`）：
   `check` 的自报退化成 `<未知>`，但**不改退出码**（规格已定），只削弱 issue #30 的验收证据强度。
4. **issue #30 的两组 CI 数字（✗10 / ✗1）**：无法复算（另一个仓 + 真 CI）；我只核到它与 `proposal.md:33-34`
   的自述一致。**若假设相反**：`proposal.md` 的「实测」段的**说服力**变化，不影响任何机制结论。
5. **`refs/pull/N/merge` 能否被 uv/git 安装**：未实测（`spec.md:42-43` 已刻意只作定性、不声称必然失败）。
   **若假设相反**（它能装）：只是「畸形样本」的定性偏保守，fail-closed 行为不受影响（仍退兜底并告警）。
6. **`GITHUB_OUTPUT` 在 GHES / 老版自建 runner 上会不会缺省**：本工作区**不可验证**。
   **若假设「会缺省」成立**：那台机器上 gate 的**第一个 step 就红**（R5 实测未定义 ⇒ EXIT=2），
   而 `docs/gate.md §7.1:515-521` 把 GHES 描述成「fail-closed 退兜底 ref + 日志有 `::warning::`」
   ⇒ 两者**不一致**（是硬红，不是 warning）。这正是 §D7；我按判据纪律把它留在这里而不是必须修改项，
   因为「GHES 上会怎样」正是题面明写**不算必须修改项**的那个面。
7. **本轮四条并发落库（`b71f457` / `a66d51c` / `4538404` / `8297b82`）的归属**：commit message 自述
   「对抗轮 R6 实测」，其中包括**我独立推出**的两条（`design §2 D1` 判定顺序、recipe 顺序。
   我在写本报告前就已在 `/tmp/adv6` 里跑出对应的两张原始输出）。我**无法判定**主 session 是
   并发消费了本会话的中间结论，还是有**另一个同名 R6 实例**——与 R3/R5 当年的情形同类。
   ⇒ 我按「**本轮确实发现了新的可证伪项**」记（口径与前几轮一致），并在收敛结论里如实分开陈述。
8. **本报告的行号基准**：`8297b82`。若树在我写完后继续移动，请按上表 blob 重核行号
   （`src/` 三份文件在 `bd80b1d..8297b82` 之间**未变**，本报告引用的实现行号在 `8297b82` 上有效）。

---

## 必须修改项

> 基准 = **`8297b82`**（我收尾时逐条复核的那棵树）。**针对该 revision：本轮无必须修改项（0 条）。**

理由写在这里，免得读者以为漏了：本轮的四处新证伪项**全部已在被审 revision 之后落库**，
且我都**重跑同一变异确认它变红**：

| 本轮新证伪项 | 落库提交 | 我在 `8297b82` 的重跑结果 |
|---|---|---|
| 台账坏 JSON 分支在被审 revision 上无钉子（§A） | `b71f457` | `8297b82` **1 failed** ✅ |
| `_text` 空串判定在被审 revision 上无钉子（§A） | `b71f457` | `8297b82` **1 failed** ✅ |
| `design §2 D1` 第 3 条的触发条件与实现/spec 矛盾（§C2） | `4538404` | `8297b82` **1 failed** ✅ |
| `docs/gate.md §1.2` 的 recipe 顺序无机械钉子（§C1 E 组） | `8297b82` | `8297b82` **1 failed**（强形态）✅ |

**最接近「必须修改项」但我不判它的三条**（每条都写了理由，供下一轮复核）：

- 被审 revision **工作区不干净**（§D1）：它是**输入状态**问题、已由 `b71f457` 消除；
  按「必须修改项 = 针对被审 revision 的 `src/`+`docs/`+`tests/` 缺陷」这个口径它不成立。
- `docs/gate.md` 那半的 recipe 顺序钉子在**只改编号**时全绿（§D3）：真·渲染序反转**会红**，
  且两条 bullet 的文字语义未反转 ⇒ 不判。
- `_set_ledger_gate_ref` 的纵深防御无独立钉子（§D4）、dry-run `print` 无钉子（§D5）、
  `not entry.get("self")` 无钉子（§D4 表内）：三者都**无行为后果**或**不可达** ⇒ 不判。

---

## Open Questions

**（本轮无新增。** 用户已明确「不要向用户提问」（`design.md:359`）；本轮剩下的分歧面只有三条，
且都可以由「实现者按现有机制事实裁定」：

1. 「被审 revision」要不要在每轮开始时就由主 session**显式钉一个 commit 并保证工作区干净**？
   ——这是**流程**取舍，不是 change 的取舍（§D1）。我的倾向：要，否则判①会随读法翻转。
2. 只改编号那种「伪反转」要不要也钉住？我的倾向：不用（§D3 的三条理由）。
3. `uninit` 的同款崩溃面（§D6）要不要在本 change 顺手收掉？我的倾向：**不要**——它先于本 change 存在，
   且 `uninitcmd` 不在本 change 的受控面内（收它会扩大本 change 的 diff 面，与 D4/D5/D7 的取舍同向）。
   **）

---

## 收敛结论

**不收敛。**

**判据②（前五轮的必须修改项全部已落库）——满足 ✅**

- R1 的 **K1–K8**、R2 的 **L1–L6**、R3 的 **M1–M4**、R4 的 **N1–N3**、R5 的 **P1** 我**逐条去正文/代码里核**
  （**不核** §7.9 的自述表），落点见 §B。其中五条我**实踩/变异验证**过有效性：
  L3（改回 `"v1"` ⇒ 该条红）、M1（模拟 6.1 三处字面量 ⇒ `8297b82` 680 passed）、
  N1（补条目改 `append` ⇒ 仅该条红）、P1（两层一起退回旧行为 ⇒ 该条红，且端到端复现「受控失败」）、
  R5 的 handled 补钉（合成同一常量 ⇒ 红）。

**判据①（本轮没有新的可证伪项）——不满足 ❌**

- **本轮在被交给我的 revision（`bd80b1d` + 当时工作区）上确实产生了新的可证伪项，共 4 条**：
  ① 工作区两处**未提交**的测试正是题面点名面的钉子 ⇒ **按提交物读，`bd80b1d` 上这两条分支无钉子**
  （A1h / C1h：**676 passed**）；② `design §2 D1` 第 3 条的触发条件与实现/ spec 矛盾（实测 `ref=v1`
  vs 文档预测 `main`）；③ `docs/gate.md §1.2` 的「顺序不能反」当时无机械钉子（E1b：676 passed）。
- 这 4 条**全部在本轮进行中**由 `b71f457` / `4538404` / `8297b82` 落库，我在 `8297b82` 逐条重跑同一变异
  ⇒ **全部变红**。⇒ 它们是**本轮的证伪项**，但**不构成针对 `8297b82` 的必须修改项**。
- 我**不**把「已修复」当作「没发生过」的另一个理由：把新证伪项按「主 session 有没有看见」重新计零，
  会让判①退化成一条**对并发消费敏感的**判据——R5 已点过这个病（`grill-adversarial-r5.md` 的
  「C1/C2 的归属说明」）。故我按字面记：**本轮有新证伪项 ⇒ ① 不满足 ⇒ 不收敛。**

**本轮证伪失败（= 既有结论成立）的部分，一并记明，避免读者以为全盘被推翻**：
(B′) 的上下文落点（`job.*` + step，`gate.yml:58-113` 与行为级用例一致）；解析 step 是 job 的第一个
step 且 `run:` 内无 `${{ }}` 插值；①→⑤ 的分支顺序与 8 类行为级用例一一对应；
fail-closed 与兜底剥离**行为级**符合 spec（我交真 `sh` 复算三组输入）；
`--gate-ref` 的「重写-同步-幂等-可卸载」是**不动点**（含台账缺条目的补条目路径）；
作用域守卫**没有**被打破（删掉它 ⇒ 178 failed / 102 errors）；`check` 自报从不因取不到元数据而失败
（宽 `except` 是**刻意且正确**的，且**不吞** `BaseException`，我实测两者都照常传播）；
`--dry-run` 下「什么都不落盘、也不谎报」（组合矩阵实测）；`docs/gate.md` 的 § 编号与交叉引用**自洽**；
P1 的 fail-closed 修法**端到端**有效且**不产生半删态**；远端最大 tag = `v1.6.0`（`v1^{}` = `ae99256`，
逐字吻合 `README.md:125`）；远端**无** `probe/*`、本地**仍留** `probe/workflow-ref`（K8 措辞属实）。

**建议下一轮**：**若树在 `8297b82` 冻结**（或只在其上追加 `reviews/` 证据与 §7.9 的 R6 小节），
我这张表（§C 的 34 条变异 + §B 的逐条落点）**可以直接复算**，本轮剩余的**全部**是
「本工作区不可验证」的面（真 CI 的 `job.*`、GHES/自建 runner、`v1.7.0`、issue #30 的数字）
或已登记的低危观察（§D） ⇒ **下一轮应当收敛**。
若树**再次在轮内移动**，请先按上表 blob 说明「被审 revision」，否则判①会再次随读法翻转（§D1）。

---

## 追加：第二个独立 R6 实例的独立复核（**含一条 §C 未覆盖的新证伪项**）

> 本节由**另一个**独立零记忆 R6 实例（本会话）追加，**不改写上面任何内容**（上节可复算的部分我抽查一致）。
> 要记这一节的理由，正是上节「未验证项 7」那句自述——「我**无法判定**主 session 是并发消费了本会话的
> 中间结论，还是有**另一个同名 R6 实例**」：**答案是有**，本节即那个实例，且它**没有消费上节的任何结论**
> （两节的实验分别在 `/tmp/adv6b/`（本节）与 `/tmp/adv6/`（上节）各自独立跑成，本节在写之前只做了
> 「读上节正文 + 独立复算抽查」）。

**基准**：`git rev-parse HEAD` = `8297b822a10a2eba4c7367694476dacf17bd26f0`——我开始工作时树**已经**在这里，
**我没见过 `bd80b1d`**（上节 §A 的「工作区不干净」这一输入在我这一侧**不存在**：
我开始时 `git status --porcelain` 除本报告外为空）。快照用 `git archive HEAD | tar -x -C`（**无 `.git`**，
未用 `cp -a`）；基线 `PYTHONPATH=src python3 -m pytest -q` = **680 passed / 34.42s**。
关键 blob 与上节 §Reviewer 表**逐字一致**（`initcmd.py b33f4083…`、`checkcmd.py e12db4d9…`、
`constants.py 0a64184d…`、`gate.yml 330104b8…`、`docs/gate.md f79b48f8…`、
`tests/test_gate_workflow.py fb3972f4…`、`tests/test_init_gate_ref.py e785c87a…`）。

### 独立变异（每条 = 新副本 + 一次精确替换 + **全量** `pytest -q`）

| # | 变异（`8297b82`） | 结果 | 对上节的意义 |
|---|---|---|---|
| m1b | `docs/gate.md §1.2` + `README` 的 recipe **整行反序**（**保留**「先把 CLI 升上去」字样、只搬位） | **1 failed**（`test_docs.py::test_gate_recipe_puts_the_cli_upgrade_before_the_ref_change`） | 独立确认上节 §C1 末行 / §D3：新钉子对**真·渲染序反转**有效 |
| m2 | `gate.yml:81` 关掉 `repository != REPO_SLUG` 的 `elif`（= 让不匹配落到 `job.workflow_ref`） | **2 failed, 678 passed** | 独立确认上节 §C2 的 `4538404` 修法**有效** |
| m3 | 删 `initcmd.py:173-174` 的 `created_files` 非数组守卫（`sync_caller_gate_ref` 那层） | **1 failed**（`test_a_malformed_ledger_is_loud_and_never_rebuilt`） | 独立确认上节 §C1 第 ③ 行 |
| m4 | `initcmd.py:411` 的结构非法分支 `return C.EXIT_FAIL` → `C.EXIT_PASS` | **1 failed**（同一条） | 上节 §C 只测了「两层一起退回旧行为」；这里单测**退出码那一层**，也有钉子 |
| m5 | 删 `_set_ledger_gate_ref` 的 `and not entry.get("self")` | **680 passed（零红）** | 与上节 §C3 同行**逐字一致**（不可达 ⇒ 双方都不判） |
| m6 | `checkcmd.py:89` 把输出标签 `requested_revision=` 改词 | **3 failed**（`test_check_package_ref.py` 三条） | 「自报行」在**代码侧**有钉子（但**文档侧** `docs/gate.md:96` / `README.md:203` 的同一字面量无钉子——低危，同 §D 口径） |
| **m7** | **`gate.yml:132` 的 `WL_REF: ${{ steps.wl-ref.outputs.ref }}` 改回 `${{ inputs.witnessloop-ref }}`（= 逐字复现 issue #30 的原缺陷）** | **680 passed（零红）** ⚠️ | **上节 §C 未覆盖 / 未想到的面** |

### 新证伪项 **T1**：`gate.yml` 的**安装步吃不吃解析 step 的输出**，全仓无钉子

- **事实**：`gate.yml:132`（`- name: witnessloop check` 的 `env.WL_REF`）是解析结果**唯一**的消费点——
  它被喂进 `run:` 里的 `uvx --from "git+https://github.com/Xingkai98/witnessloop@$WL_REF"`。
- **变异**：把这一行改回 v1 的形态。`git show v1:.github/workflows/gate.yml` 的安装行**正是**
  `"git+https://github.com/Xingkai98/witnessloop@${{ inputs.witnessloop-ref }}"` ⇒ 我的 m7 就是**把
  这个 change 的整个机制按 v1 原样退回去**，而 **680 条全绿**。
- **后果（可复算）**：`inputs.witnessloop-ref` 的默认值是 `""`（`gate.yml:23`，由
  `tests/test_gate_workflow.py:478` 钉住「非空 ⇒ (B′) 退化成原缺陷」），所以接入方**只要没写 `with:`**，
  `WL_REF` 就是**空串** ⇒ uvx 的 URL 退化成 `git+https://github.com/Xingkai98/witnessloop@` ⇒
  **装默认分支**（静默跑错版本）。这正是 `gate.yml:105-107` 自己写明要避免的「与『包版本钉没钉住』
  毫无相似之处的**静默错版**」——**而全量测试一条都不会红**。
- **覆盖缺口**：现有用例只测**解析 step 自己**的逻辑——`_run_resolve` 交真 `sh` 跑**它的** `run:`（好），
  但 `test_resolve_step_binds_the_right_contexts`（`tests/test_gate_workflow.py:329-347`）只断言**该 step**
  的 `env`，`test_resolve_step_is_the_first_step` 只断言它是 `steps[0]`；**没有一条**断言安装步的
  `env["WL_REF"]` 绑到 `steps.wl-ref.outputs.ref`。`grep -rn "outputs.ref\|WL_REF" tests/` ⇒ **零命中**
  （唯一出现处是 `gate.yml:132` 自己）。
- **定性**：这是**本 change 新写的机制**（v1 树上没有解析 step，也没有 `steps.wl-ref`），
  不是措辞/计数，也**不是**先于本 change 存在的行为（旧行为只是「没有解析 step」，而「要求安装步吃它的
  输出」是 spec 第 1 条 Requirement 的核心断言：`spec.md:12-15` 与 Scenario「改一处、两处跟着变」的
  Then「`gate / check` 用的是新包」，`spec.md:26-30`）⇒ **对 `8297b82` 是一条必须修改项**。

### 对上一节结论的修订（**只此一处**）

- 上节「必须修改项」写「针对该 revision：本轮无必须修改项（**0 条**）」⇒ 按上表 m7，应为 **1 条（T1）**。
- 上节「收敛结论」判**不收敛** ⇒ **结论不变**，且理由**多一条、与读法无关**：即便不采用上节 §A 的口径
  （把「轮内已修复的新证伪项」仍计入判①），`8297b82` 上仍**净剩**这一条**未落库**的新证伪项
  ⇒ 无论按「提交物」还是按「工作区」读，**判①都不满足**。
- **建议的落法**（一行钉子即可，`tests/test_gate_workflow.py`）：解析 YAML 后断言安装步的
  `env["WL_REF"] == "${{ steps.wl-ref.outputs.ref }}"`（等价写法：钉住它**不得**是
  `${{ inputs.witnessloop-ref }}`）。这与我 m7 变异的方向一一对应（m7 之后该条应红）。

**本节没能做的**：没有跑真 `uvx` / 真 Actions（同「未验证项」）；没有重跑上节 §C 的另外 27 条变异
（只抽查了 m2/m3/m5/m6 四条与 §C 一致）；没有核对 `design.md`/`tasks.md` 的**全部**行号引用
（只抽查了 §B 点名的十处，均命中）。

---

## 处置（主 session 在 R6 之后追加，非审阅者原文）

> ⚠️ **本报告由两个互不消费的 R6 实例写就**（上节 = 第一个实例，18:19 落盘；「## 追加」节 = 第二个实例）。
> 第一个实例的会话在写完之后崩掉、**没有发回完成通知**，我据此误判「本轮无产物」并重启了一个新实例——
> 两个实例各自独立跑了实验（`/tmp/adv6/` 与 `/tmp/adv6b/`），第二个**没有覆写**第一个的内容。
> 两个实例都判**不收敛**；第二个还补了第一条遗漏的证伪项（T1）。**净效果是好的**（多一轮独立复核），
> 但这份报告的形状不是设计出来的，如实记在这里。

**判据②：满足**（两个实例各自逐条核过 K/L/M/N/P，均落库）。

**T1（第二个实例的新证伪项）已落库**：`gate.yml` 的安装步「吃不吃解析 step 的输出」全仓无钉子——
把它改回 `${{ inputs.witnessloop-ref }}`（= 逐字复现 issue #30 的原缺陷）**680 条全绿**。
已加 `tests/test_gate_workflow.py::test_the_install_step_consumes_the_resolved_ref`（钉 `env.WL_REF`
的来源、run 里不得再出现那个输入、uvx 用的就是该变量）。变异复核：改回旧绑定 ⇒ **红**。

**第一个实例的四条证伪项**（工作区未提交 / D1 第 3 条触发条件 / recipe 顺序 / 两条分支无钉子）
全部已在被审 revision 之后落库，且两个实例都在新树上重跑同一变异确认变红。

**两个实例都没判为「必须修改项」的三条**（`docs/gate.md` 只改编号时的顺序绿、`_set_ledger_gate_ref`
的纵深防御无独立钉子、dry-run 的 `print` 无钉子）：**接受它们的判断**——都属「无行为后果 / 不可达」，
登记为已知低危面，不修（修 = 为零行为后果的代码加测试，只会增加维护面）。

**判① 的读法之争**（第一个实例在「未验证项」里点了名）：若把「在轮内被并发修掉的证伪项」重新计零，
判①会退化成**对并发消费敏感**的判据。**采纳它的口径**：按字面记——本轮**有新证伪项 ⇒ 不收敛**。
它也给了收敛的**前提条件**：树在被审 revision 上冻结（或只追加 `reviews/` 证据与 §7.9 小节），
下一轮才可复算这张表。⇒ 下一轮（R7）开始前我不再改动 `src/`、`gate.yml`、`docs/`。
