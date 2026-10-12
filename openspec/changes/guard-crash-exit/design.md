# Design: guard-crash-exit

> 状态：**设计已收敛**（grill + 对抗验证 R1/R2/R3 三轮 CHANGES_REQUESTED → 逐轮已整合；R3 收尾项已修）。停轮待用户确认。
> 依据 `proposal.md`。流程出处 `templates/grill.md`。
> 审阅证据：`reviews/grill-review.md`（决策记录）、`reviews/grill-adversarial.md`（对抗验证）。
> 关联 issue：witnessloop **#9**（低、非阻塞）。

## 0. 一句话

让 `guard` 的「**拦**」成为**只由「拦」自己产生**的退出码——**未预期异常绝不落进这个码**（fail-open），
并**在源头把已知的读失败归一成 verdict**（而不是崩溃），把该不变量钉成回归测试。

## 1. 现状（实测，带 `文件:行号`）

- **崩溃路径**：`cli.main`（`cli.py:136-173`）不 catch 任何异常；`__main__.py:6` 只做 `sys.exit(main())`。
  任何从 `guardcmd.run` 冒出的未捕获异常 ⇒ CPython 以 **status 1** 结束。
- **宿主映射**：`plugin/hooks/guard.sh:38-41` —— `if [ "$status" -eq 1 ]; then exit 2; fi; exit 0`。
  **1 → CC 的 2（block）** ⇒ **崩溃 = 误拦**。
- **读点清单（实测，`guard` 与 `check` 各走一条路，都漏 `UnicodeDecodeError`）**：
  | 读点 | 谁读到 | 文件 | 现有守卫 | 非法 UTF-8 时 |
  |---|---|---|---|---|
  | policy.json | `guard` / `check` | `policy.py:128` | `except (OSError, json.JSONDecodeError)` | 崩（`UnicodeDecodeError` 是 `ValueError` 子类、不被捕） |
  | review manifest | **`guard`** | `evidence.py:165`（`_read_json`） | 同上 | 崩 |
  | grill 报告正文 | `guard` / `check`（**共用**） | `evidence.py:216` | 无 | 崩 |
  | review manifest | **`check`**（先于 `evidence`！） | `contract.py:176`（`_bound_report`）、`contract.py:230`（`_validate_one`） | `except (OSError, json.JSONDecodeError)` | 崩 —— `checkcmd.py:75` 的 `validate_review_manifests` **先于** `:78` 的 `evidence`，故 `check` 的 manifest 读点走的是**这里**、不是 `evidence.py` |
  | 事件文件 | `check` | `events.py:51` | **无 try** | 崩（**本 change 非目标**——不同 artifact、且无 `guard` 路径，见 §非目标） |
  （另有潜在一处 `gitutil._run` 的 `FileNotFoundError`——`git` 不在 PATH 时；被通用兜底覆盖。）
- **「拦」= 1 的由来**：`guardcmd.py:129` `return C.EXIT_FAIL`（`constants.py:81`）——为避开 argparse 的 **2**
  （`cli.py:19-23`）。见 change `grill-evidence-gate` 的 D5 / 回归审阅 **Issue 3**。
- **`check` 侧同崩溃点**：`checkcmd` 也调同一函数 ⇒ 同样崩；但 `check` 崩溃退 1 = 「**未通过**」= **fail-closed，语义正确**。
- **退出码今日占用**：`0/1/2/3`（`constants.py:80-83`）；**4 空闲**（全树 grep 无 `EXIT_* = 4` / `exit(4)` / `return 4`）。
- **修完仍存的边界（对抗验证实测）**：`cli.py:14-15` 的**模块级** import（`from witnessloop import __version__`、
  `from witnessloop.constants import …`）发生在 `main()` **之前**、`__main__.py:3` 处 ⇒ 属 guard 分支 try **之外**。
  install 破损（如 `constants.py` 坏了）时 `witnessloop guard` **退 1 ⇒ 被 shim 当 block**（已复现）。见 D4/边界。

## 2. 决策

### D1 方向：选 **A（顶层兜底，`block` 保持 1）**，**否 B（专用 block 码）** —— 对抗验证已复核站得住

- **A**：`guard` 加兜底——未预期异常 → 一行诊断 → 退**非 1**（fail-open）。
- **否 B 的理由 = 版本偏斜（实测证据）**：plugin 经 git / `--plugin-dir` 分发（`plugin/README.md:22-32`），
  CLI 经 `uv tool install …@v1` **独立**安装（`README.md:20`）；`constants.py:11` 的 `DEFAULT_GATE_REF` 只钉
  gate reusable workflow、**不钉本地 CLI**，`plugin/**` 里没有任何「要求 CLI 版本 ≥ X」声明（grep 0 命中）。
  ⇒ 二者**确可偏斜**，且 B 在偏斜下**二选一皆坏**：旧 shim(1→2)+新 CLI(block=4) ⇒ 4 无人命中 ⇒
  **静默永不拦**（比误拦更糟，因为无声）；新 shim 兼映射 {1,4} ⇒ 新 CLI 崩溃(退 1)又落进 block ⇒ **原 bug 复活**。
- **A 对偏斜免疫、且 shim 零改动**：`block` 仍是 1 ⇒ 旧/新 shim 都正确。

### D2 崩溃的退出码：新增 `EXIT_INTERNAL = 4`（fail-open，**绝不等于 1**）

- 语义：`4 = guard 内部错误（fail-open，不拦）`。仅 `guard` 用；`check` 不返回 4（其崩溃仍退 1 = 未通过）。
- 不用 0（与「正常放行」同码 ⇒ 丢失诊断性）；不用 3（`EXIT_NOT_ONBOARDED` 已占，`guardcmd.py:95`）。
- shim **无需认识它**（只认 1）⇒ 无新增耦合。

### D3 兜底落点：`cli.main` 的 **`guard` 分支**（`try/except Exception` 包住 **lazy import + run**）

- **覆盖**：`from witnessloop import guardcmd` 及其**传递依赖**（`contract`/`gitutil`/`evidence`/`paths`/`policy`）
  的 `ImportError` + `guardcmd.run` 的运行期异常。
- **不覆盖（边界，须写明）**：`cli.py:14-15` 的**模块级** import 失败（`witnessloop.cli` 自身起不来）。
  那属于「**安装破损**」——所有动词一起坏，不是 guard 专属；见 D9 与 Open Question **Q2**。
- **不 catch `BaseException`**：`argparse` 的 `--help`/用法错误是 `SystemExit`（且在 `parse_args`、dispatch 之前），
  实测不受影响；`KeyboardInterrupt` 实测以**信号**结束（shell 见 130 ≠ 1）⇒ shim 放行，非误拦。
- ⚠️ **实现细节（对抗验证实测的坑）**：`cli.py:15` 当前只 import `DEFAULT_GATE_REF, EXIT_USAGE`——
  必须**同时 import `EXIT_INTERNAL`**，否则照抄本示例会 `NameError` ⇒ **在 except 处理器里退出 1 ⇒ 原 bug 复活**。

### D4 证据「读不出」的语义：**甲案（统一视为不完备 ⇒ 拦 / 红）** —— 待用户裁定（Q1）

- **问题**：`guard` 撞上「证据文件存在、但**解码失败**」时该**拦**还是**放**？（grill 与对抗验证推荐不同。）
- **读点归宿（分解后）**：
  1. `policy.py:128`（**policy 读不出**）→ 归一为 `PolicyError` ⇒ `guardcmd.py:86-88` **放行**。
     **与既有「policy 非法 ⇒ 不拦」完全一致，无争议，直接采纳。**
  2. **manifest = 证据容器**：`evidence.py:165`（`guard` 侧）+ **`contract.py:176` / `contract.py:230`（`check` 侧）**
     → 捕 `UnicodeDecodeError`，**与既有「manifest 缺失 / JSON 语法坏」同归** ⇒ **拦 / 红**。
     ⚠️ **R3 M1 修正（原稿文案自相矛盾）**：原稿要 `guard` 侧的 finding 文案是「清单无法解码：<file>」**又要**「与 JSON 坏同归」——
     二者不可兼得（`_read_json` 捕到即返回 `None` ⇒ 走的是既有的「**无 stage=grill 的 manifest（现有 stage：…）**」文案，
     JSON 坏与字节坏**逐字相同**）。**定案**：`guard` 侧**不新增文案、不点名文件**（= 与 JSON 坏/缺失**逐字同归**，
     这是硬要求）；**「点名该文件」只落在 `check` 侧**（`contract.py:230` 的既有 `manifest 无法解析：<file>`）。
     代价：`guard` 侧对「坏 manifest」与「无 manifest」文案相同（轻微不可诊断）——记入 §4 R8，可另立 issue 改进。
     ——**这修掉 R1 实测出的裂缝**：今日「字节坏 manifest ⇒ 放（崩溃退 4）」与「JSON 坏 manifest ⇒ 拦」自相矛盾。
     ⚠️ **R2 修正：`check` 的 manifest 读点不在 `evidence.py`**——`checkcmd.py:75` 的 `validate_review_manifests`（→ `contract.py:230`）
     **先于** `:78` 的 `evidence` 调用。**只改 `evidence.py` 不够**：R2 实测「字节坏 manifest ⇒ `check` 仍 traceback（`contract.py:230`）」，
     与「JSON 坏 ⇒ 干净退 1」**不同归**。⇒ 归一必须**同时**覆盖 `contract.py:176,230`。
  3. `evidence.py:216`（**报告 = 证据内容**）→ 见下**甲/乙**。
- **甲（推荐）**：报告读不出 ⇒ Finding「报告无法解码」⇒ **拦 / 红**。统一口径「**读不出 ⇒ 不可核验 ⇒ 不完备**」。
- **乙（R1/R2 原推荐：容器坏 ⇒ 拦、内容读不出 ⇒ 放）**：**是可实现的**——给共享函数加一个**带默认值**的调用者参数
  （或拆一个 `guard` 专用窄函数）即可。
  ⚠️ **R2 已证伪我原稿的两处理由，此处如实重写**：
  (a) 「乙在共享函数里无法干净实现」——**伪**（加默认参数即可）；
  (b) 「乙会让 `check` 变绿 ⇒ 失去 fail-closed」——**在真实场景下不成立**：报告通常是在 manifest **之后**被写坏的
  ⇒ `check` 由 `report_hash` **独立**判红（`contract._check_hashes`），**不会绿**。只有「作者把字节坏的报告
  **重新 `manifest build`** 进 manifest」这一角落才会绿（build 对字节算 hash），而那属**作者自欺**、
  落在「防漂移不防伪造」的既有边界内。
- **两案的真实差别**（不再用假前提，交用户裁定）：
  | | **甲（推荐）** | 乙 |
  |---|---|---|
  | 报告损坏时 `guard` | **拦**（快反馈：先修报告再写码） | **放**（交 CI 锚） |
  | 「重 build 坏报告」角落的 `check` | **红** | **绿**（靠作者自欺） |
  | 代码面 | **不新增参数** | 需调用者参数 / 窄函数 |
  | 与「manifest 缺失 ⇒ 拦」口径 | **一致** | 「容器 / 内容」两分（须在 spec 写明） |
- **共同点**：**崩溃都不再发生**（异常在源头归一成 verdict）。D3 的兜底从此只负责「**真正未预期**的异常」。
- **甲不自锁**（R2 实测）：写 `reviews/**` / `docs/**` 属文档豁免（不在 `require_change_for`）⇒ 报告坏了仍可先修报告。

### D5 policy 读失败的归一（无争议，直接采纳）

`policy.py:129` 的 `except (OSError, json.JSONDecodeError)` **补 `UnicodeDecodeError`** ⇒ 抛 `PolicyError`
⇒ guard 「policy 非法 ⇒ 不拦」（`guardcmd.py:86-88`）、`check` 走它既有的 `PolicyError` 分支（`checkcmd.py:33`）。
**理由**：读不出 policy = 连「什么算受管控」都不知道 ⇒ **不执行**（与既有语义同构），不是「拦」。

### D6 shim **零改动**（对抗验证已复核）

- `plugin/hooks/guard.sh:38-41` 的「只认 1、其余一律 0」对新增的 4 **天然正确**。
- 实测映射表：`1→2`、`4→0`、`0/2/3/127→0`。
- **不采用「marker + shim 判据」**：任何「让 shim 多判一个信号」的方案都引入 D1 否掉的偏斜风险。

### D7 文档：含一处**既有漂移**的订正

- `docs/gate.md §6`：`guard` 表加行 `4 | 内部错误（fail-open，**不拦**）`；注补「仅 `guard` 产出 4」；
  §8 补「崩溃/内部错误 ⇒ 放行」。
- ⚠️ **既有漂移（对抗验证发现，本 change 顺带订正）**：`README.md:35` 与
  `docs/adr/0001-local-guard-hook.md:16` **都写** guard「拦（exit **2**）」，而现行 CLI 是 `guardcmd.py:129`
  = `C.EXIT_FAIL` = **1**（2 只是 **shim 给 CC 的映射**）。这是 change `grill-evidence-gate` 改「拦 2→1」时
  漏改的两处。**不改就是新增一处「本 change 主题」的文档漂移** ⇒ 纳入本 change 一并订正为
  「CLI 退 1（shim 映射成 CC 的 2）」。
- `docs/design.md`：grep 确认**不含** guard 退出码叙述 ⇒ 无需改（对抗验证已复核）。

### D8 漂移守卫 + 功能断言

- **常量守卫**：断言 `C.EXIT_INTERNAL == 4` 且 `!= C.EXIT_FAIL`（今日全树无任何测试约束 4 的取值 ⇒ 漏改不红）。
- **功能断言**（补「常量守卫挡不住 `sys.exit(1)`」的缺口）：B1–B3 三条用例直接断言**行为**（崩溃 ⇒ 4，非 1）。
- 加注释声明不变量：「`cli.main` 的 guard 分支及之后，1 **只**由 `return C.EXIT_FAIL` 产生」。

### D9 自伤面与顺序约束

- **无既有测试变红**：不改 CLI 动词面（只加常量）⇒ `tests/test_cli.py:50-54` 不红；不改 plugin 文件清单 ⇒
  `tests/test_plugin.py` 不红；`guard` 既有三态用例语义未动 ⇒ 仍绿。对抗验证实测：打补丁副本 **388 passed**。
- ⚠️ **顺序约束（对抗验证在本仓**实测复现**）**：`guard` 放行条件是「**grill 证据完备**」，**不是「change 目录在场」**。
  故**写 `src/**` 前，盘上必须已有一个 passing 的 `stage=grill` manifest**（否则 `guard --path src/…` 退 1）。
  而 `src/witnessloop/{constants,cli,guardcmd}.py` **都在** `require_change_for` 内（`constants.py:27-36`）。
  ⇒ 实施顺序：**先停轮拿确认 → 写 `## User Confirmation` → `manifest build --stage grill` 放行 → 再写 `src/**`
  → 内容提交后重跑 build 覆盖成最终 manifest**。`tasks.md` 记此为 **G0**（该文件 G 段首步）。

## 3. 接线点（实现清单）

- `src/witnessloop/constants.py`：`EXIT_INTERNAL = 4` + 注释。
- `src/witnessloop/cli.py`：`import EXIT_INTERNAL`（D3 ⚠️）+ `guard` 分支 `try/except Exception`。
- `src/witnessloop/policy.py`：`policy.py:129` 补 `UnicodeDecodeError`（D5）。
- `src/witnessloop/evidence.py`：`_read_json` 补 `UnicodeDecodeError` + 可诊断 Finding（D4-2）；
  报告读点补捕（D4-3）。
- `src/witnessloop/contract.py`：**`contract.py:176`（`_bound_report`）与 `contract.py:230`（`_validate_one`）**
  补 `UnicodeDecodeError`（D4-2 ⚠️ R2：`check` 的 manifest 读点在这里，不在 `evidence.py`）。
- `src/witnessloop/guardcmd.py`：模块 docstring 记「兜底在 `cli.main` 的 guard 分支 + 边界」。
- `docs/gate.md` §6/§8、`README.md:35`、`docs/adr/0001-local-guard-hook.md:16`（D7）。
- 测试：`tests/test_guard.py`（崩溃 ×2 + shim 新码 + 常量守卫）、`tests/test_evidence.py`（读点归一）、
  `tests/test_check_manifest.py` / `test_check_grill_evidence.py`（**`check` 对无法解码 evidence 的干净红**）。

### 非目标（本 change）

- **`events.py:51`**（`workflow-events.jsonl` 读点，`load_events_file` **无 try**）：`check`-only、**不同 artifact**、
  **无 `guard` 路径**，其崩溃退 1 = fail-closed（仅报错难看）⇒ 属**既有**问题、与本 issue（`guard` 误拦）不同类，
  不在本 change；建议另立 issue。（同理 `uninitcmd`/`initcmd` 的多个读点不在 `guard`/`check` 路径内。）

## 4. 风险

1. **R1（中）**：`except Exception` 掩盖真 bug ⇒ 缓解：诊断行含异常类型 + message；只作用于 `guard`。
2. **R2（中，边界）**：`witnessloop.cli` 自身 import 失败仍退 1 ⇒ 误拦（**安装破损**场景，已复现）⇒ Q2 裁定。
3. **R3（低）**：D4 甲案把「报告读不出」从「放」改成「拦」⇒ 对**接入方**是**行为变更**（损坏证据从静默放行变为拦）。
   须在 README/gate.md 写明。
4. **R4（低）**：4 的宿主语义？——shim 只输出 0/2 给 CC；4 只在**直连 CLI**可见。CC 对非 0/2 = 非阻塞，与意图一致。
5. **R5（低）**：`check` 侧只改**读点归一**（崩溃→干净红），**不动其退出码语义**（仍 1 = 未通过）。
6. **R6（低）**：读点清单可能仍不完备 ⇒ 通用兜底覆盖未枚举者（这正是选「通用兜底」而非「逐点 try」的理由）。
7. **R7（低）**：改 `plugin/**` 会触发 guard（`plugin/**` 在 `require_change_for`）——正常流程证据先齐，不自锁。
8. **R8（低，可诊断性小缺口 · R3 记）**：`guard` 侧对「**坏 manifest**」与「**无 manifest**」文案相同
   （`_read_json` 捕到即 `None` ⇒ 走既有的「无 stage=grill 的 manifest（现有 stage：…）」）⇒ 用户看不出「是坏了还是没写」。
   这是 D4-2 的**有意代价**（换取「与 JSON 坏逐字同归」）。**本 change 不修**；如要改进（让坏 manifest 点名文件）
   须连带让 JSON 坏也点名、并防 `check` 侧重复报 —— 另立 issue。
   （注：`check` 侧**有**点名——`contract.py:230` 的既有 `manifest 无法解析：<file>`。）

## 5. 测试策略（TDD）

- **先红（崩溃兜底 D3 —— 用**真正未预期**的异常触发，不用可归一的解码失败）**：
  - `test_guard_survives_an_arbitrary_internal_error`：monkeypatch `evidence.grill_evidence_findings_in_change`
    抛 `RuntimeError` ⇒ 退 `EXIT_INTERNAL`（≠1）+ 一行诊断。
  - `test_guard_dispatch_survives_a_broken_import`：`sys.modules["witnessloop.guardcmd"] = None` ⇒ 退 `EXIT_INTERNAL`。
  - `test_shim_allows_the_internal_error_code`：`_run_shim(cli_exit=C.EXIT_INTERNAL) == 0`；`.== EXIT_FAIL → 2` 回归。
- **先红（读点归一 D4/D5 —— 断言是**确定性 verdict**、且**不出现 traceback**）**：
  - 报告字节坏 ⇒ `guard`：**甲**退 **1** 且 stderr 含「报告无法解码」；**乙**退 4。（按 Q1 结果二选一，另一案断言相反。）
  - manifest 字节坏 ⇒ `guard` 退 **1** 且文案点名「清单无法解码」；**与 JSON 坏 / 缺失同归**（同一断言形状）。
  - policy 字节坏 ⇒ `guard` 退 `EXIT_PASS`。
  - **`check` 侧（D4-2 ⚠️ R2）**：字节坏 manifest ⇒ `main(["check",…])` **不抛异常**且非 0（干净红，非 traceback）；
    字节坏报告同理。
- **回归（不变红）**：既有 `guard` 三态 / shim 1→2 / 全量 388；本仓 `dogfood-bootstrap`、`grill-evidence-gate` 的 `check` 仍绿。

## 6. 文档影响

- `docs/gate.md` §6 + §8；`README.md:35`；`docs/adr/0001-local-guard-hook.md:16`（D7，含**既有漂移**订正）。
- **对**接入方**的行为变更**：D4 甲案（损坏证据从放行变拦）须写明。

## 7. Pre-Implementation Review

**已确认决策（grill 证伪后确认 · 来源 `grill-reviewer-guard-crash-exit-2026-10-12`）**：
方向 A / `block` 保持 1；`EXIT_INTERNAL=4` 且 4 空闲；兜底落 `cli.main` guard 分支；shim 零改动；
不改 `check` 退出码语义；必须新增漂移守卫。

**必须修改（已整合 · 来源 `grill-adversarial-reviewer-guard-crash-exit-2026-10-12`，R1 CHANGES_REQUESTED）**：
- **CD3 over-claim 收窄**：兜底覆盖 `guardcmd` 及其传递依赖的 import 缺口，**不**覆盖 `cli.py` 自身模块级 import（D3 + 边界 + Q2）。
- **读点枚举修正**：≥3 处（`evidence.py:216` / `evidence.py:165` / `policy.py:128`），非「一处」（§1 + D4/D5）。
- **`README.md:35` 也在写 `exit 2`**（grill 漏、对抗验证证伪其「README 不含退出码叙述」）⇒ D7 纳入订正。
- **裁定「解码失败」语义**（D4 甲案）并落 spec。
- **`tasks.md` 补 G0**（实现前须先有 passing grill manifest；自锁已实测复现）。
- **spec 的 check Scenario 补测试**（原为「写了但不可验证」）。

**必须修改（已整合 · 来源 `grill-adversarial-reviewer-guard-crash-exit-2026-10-12` R2，CHANGES_REQUESTED）**：
R2 确认 R1 的 5 条**全部到位**，但**新证伪两条**（均已整合）：
- **N1 `check` 的 manifest 读点在 `contract.py`，不在 `evidence.py`**：`checkcmd.py:75` 的
  `validate_review_manifests`（→ `contract.py:230`）**先于** `:78` 的 `evidence`。只改 `evidence.py`
  时「字节坏 manifest ⇒ `check` 仍 traceback」，与「JSON 坏 ⇒ 干净退 1」不同归 ⇒ **本 change 原 spec 的
  「与 JSON 坏同归」是 over-claim**。⇒ D4-2 的归一**扩到 `contract.py:176,230`**（§1 表 + §3 接线点 + §5 用例）。
- **N2 甲案否乙的两条理由被证伪**：①「乙无法干净实现」伪（加带默认值的调用者参数即可）；
  ②「乙 ⇒ `check` 变绿」在真实场景下伪（报告在 manifest **之后**损坏 ⇒ `report_hash` **独立**判红，
  只有「把坏报告重 build 进 manifest」这一角落才绿）⇒ **D4 的对比表重写**（不再用假前提引导 Q1）。
- **未发现新洞**：甲不自锁、无 check 回归（甲/乙副本均 388 passed）、`design.md §1` 的 `guard` 读点表完整
  （无第 5 读点）、G0 与两段提交不互斥（但**重跑 build 是承重的**：不重跑 ⇒ stale 红）。

**Code-Resolved 结论**：
`guard` 不校验 hash（`guardcmd.py:108` ⇒ `evidence.py:170-217`）⇒ 覆写报告能直达崩溃点；
`sys.modules[...]=None` ⇒ `ImportError` 可造；照抄 D3 示例不加 import ⇒ `NameError` ⇒ bug 复活（实测）；
`KeyboardInterrupt` 走信号 ⇒ 非误拦；4 空闲且无测试/文档钉「退出码只有 0–3」。

## 8. Open Questions（停轮待用户确认）

- **Q1** **报告**内容「读不出（解码失败）」时 `guard` 该**拦**还是**放**？
  **甲（推荐）**= 统一「读不出 ⇒ 不可核验 ⇒ 不完备」⇒ **拦**（快反馈，且与「manifest 缺失 ⇒ 拦」同口径）；
  **乙** = 内容读不出 ⇒ **放**（容器/内容两分，交 CI 锚）。**两案的真实差别见 D4 的表**（R2 已证伪我原稿的两条否乙理由，
  现按事实重述：乙**可实现**、且**不会**让真实场景的 `check` 变绿）。
- **Q2** `witnessloop.cli` 自身 import 失败（**安装破损**）导致的 exit 1 ⇒ 误拦：**收窄声明 + 记录边界**（推荐）还是
  **前移到入口**（新增 entry 模块 + 改 packaging）？

（每条的具体例子与推荐答案见 `reviews/grill-review.md` 的 `## Open Questions`。）
