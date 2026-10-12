# Grill 对抗验证: guard-crash-exit

> 立场：**默认前一轮（`reviews/grill-review.md`）的结论是错的**，逐条证伪。
> 每个 `文件:行号` 都亲自打开核对；能实测的都在 `/tmp` 造仓/打补丁副本实测。
> 只写本文件，未改动 `grill-review.md` / `design.md` / `src/**` / `tests/**` / 其它任何文件，未 commit。

## Reviewer
- run id: grill-adversarial-reviewer-guard-crash-exit-2026-10-12
- 时间: 2026-10-12T00:04:01Z

## Verdict

**CHANGES_REQUESTED**

前一轮的**大方向（选 A、`block` 保持 1、顶层兜底、shim 零改动、4 空闲、不改 check）经得起证伪**，
且我用隔离副本把 D3 的修复路径跑通（非法 UTF-8 报告 ⇒ 退 4 ⇒ shim 放行；拦仍 1 ⇒ shim 2）。
但有 **3 类阻塞性缺口**：D3/spec 的「覆盖 import 缺口」**over-claim**（cli 自身 import 失败仍退 1 ⇒ 误拦，已复现）；
证据文件「解码失败」的语义**未裁定**且修复后制造出一致性裂缝（同一类损坏 manifest，字节损坏放行、JSON 损坏拦截）；
doc-sync 清单**漏了 `docs/adr/0001`**，而前一轮「README 不含 guard 退出码叙述」的判断**被证伪**（`README.md:35`）。
另有 `tasks.md` 未覆盖「实现前须先有 passing grill manifest」的顺序约束（已复现自锁）。

## 逐条对抗结论

### `## Confirmed Decisions`

- **CD1（方向选 A、否 B，核心理由 = 版本偏斜）** → **站得住**。
  证据：plugin 经 `git / --plugin-dir` 分发（`plugin/README.md:22-32`、`README.md:47`），CLI 经
  `uv tool install …@v1` 独立安装（`README.md:20`）；`constants.py:11` 的 `DEFAULT_GATE_REF` 只钉
  gate reusable workflow 的 ref（`.github/workflows/witnessloop.yml:11` / `gate.yml` 的 `witnessloop-ref`），
  **不钉本地 CLI**；`plugin/**` 里没有任何「要求 CLI 版本 ≥ X」的声明（`grep` 无命中）。⇒ 本地 shim 与本地 CLI
  确可偏斜，B 的两种坏法（旧 shim+新 CLI=4 ⇒ 静默永不拦；新 shim 兼映射 ⇒ 崩溃复活）成立。我实测 shim 映射
  `{0→0,1→2,2→0,3→0,4→0,127→0}`，与 `guard.sh:38-41` 一致。A 不动 shim ⇒ 对偏斜免疫。**未被推翻。**

- **CD2（新增 `EXIT_INTERNAL = 4`、4 空闲）** → **站得住**。
  证据：`constants.py:80-83` 仅 0/1/2/3；全树 `grep -rn "exit(4)\|return 4\|EXIT_*=4"` **0 命中**；
  全树无任何 `code not in (0,1,2,3)` / `0/1/2/3` 式断言，也无测试钉「退出码只有 0/1/2/3」。
  CC hook 对非 0/2 退出码 = 非阻塞（`docs/gate.md:8,36` 与 CC 约定一致），且 shim 把 4 映成 0、根本不直传给 CC ⇒ 无宿主语义冲突。**未被推翻。**

- **CD3（兜底落点 = `cli.main` 的 guard 分支，覆盖 import + run）** → **部分被证伪（over-claim）**。
  - 覆盖到的：`from witnessloop import guardcmd` 及其传递依赖（`contract`/`gitutil`/`evidence`/`paths`/`policy`）
    的 ImportError，以及 `guardcmd.run` 的运行期异常。实测：`sys.modules["witnessloop.guardcmd"]=None` 与
    「非法 UTF-8 报告」都退 **4**。
  - **没覆盖到的**：`cli.py` **自身**的顶层 import（`cli.py:14` `from witnessloop import __version__`、
    `cli.py:15` `from witnessloop.constants import …`）。这些在 `main()` 之前、`__main__.py:3`
    `from witnessloop.cli import main` 处发生，**不在** guard 分支的 try 内。
  - **复现**（`/tmp/gce2`，坏 `constants.py`）：`PYTHONPATH=/tmp/gce2 python3 -m witnessloop guard …`
    ⇒ `RuntimeError` 冒泡 ⇒ **exit 1** ⇒ 经 shim（`1→2`）**被当 block**。**这正是本 change 要消灭的那类误拦。**
  - ⇒ `grill-review.md` CD3 与 `design.md:73-76` 的措辞「一并兜住 import 缺口（半装/坏装）」对 **cli 自身依赖**
    不成立；`spec.md:8-9` 的绝对句「内部错误 SHALL 以非 1 的退出码返回」同样 over-claim。

- **CD4（shim 零改动）** → **站得住**。实测映射表见 CD1；`guard.sh` 只认 1，4 天然落 `exit 0`。

- **CD5（不改 `check`）** → **站得住**。`checkcmd.run` 只 catch `PolicyError`/`GitError`/`EventError`
  （`checkcmd.py:33,53,142`），报告解码失败会冒泡；我实测 `main(["check",…])` 在非法 UTF-8 报告上
  **抛 `UnicodeDecodeError`** ⇒ 真实 CLI 退 1 = 「未通过」= fail-closed，方向正确。

- **CD6（必须新增漂移守卫）** → **站得住**。全树 `grep` 无 `EXIT_INTERNAL`、无对 4 的断言 ⇒ 今日 4 的取值无人约束。

### `## Code-Resolved Questions`

- **「4 真的空闲吗？」→ 是** → **站得住**（见 CD2 证据）。
- **「`guard` 会先因 `report_hash` 不匹配而拦吗？→ 否」** → **站得住**。`guardcmd.py:108` 只调
  `grill_evidence_findings_in_change`，该函数（`evidence.py:170-217`）只读 manifest 的 `stage`/`report_path`
  再读报告正文，**全程不校验任何 hash**。
- **「`sys.modules[...]=None` ⇒ ImportError」** → **合理，未另测**（`ModuleNotFoundError ⊂ ImportError ⊂ Exception` 成立）。
- **「崩溃点只有 `evidence.py:216` 一处吗？→ 否，至少第二处（`evidence.py:165`）」** → **结论对，但枚举不完备（被证伪为「至少第二处」的完整性）**。
  实测存在**第三处**：`policy.py:128` `path.read_text(encoding="utf-8")`，其 `except (OSError, json.JSONDecodeError)`
  （`policy.py:129`）同样漏 `UnicodeDecodeError` ⇒ 非法 UTF-8 的 `.witnessloop/policy.json` ⇒ 崩 ⇒ 退 1 ⇒ 误拦
  （我实测：`policy invalid utf-8 → RAISED UnicodeDecodeError`）。另有潜在第四处：`gitutil._run`（`gitutil.py:29-34`）
  `subprocess.run(["git",…])` 在 `git` 不在 PATH 时抛 `FileNotFoundError`（`current_branch` 经 `guardcmd.py:52` 可达）。
  ⇒ 三/四处读点同病。**但**：这些点都被「顶层兜底」通用覆盖 ⇒ 前一轮用它论证「选通用兜底而非逐点 try」的**结论被加强**，只是它的枚举不完整。
- **「design D7『本 change 目录在场 ⇒ 不自锁』不成立（理由错、结论对）」** → **站得住**。
  `tests/test_guard.py:42-48` 正是「目录在、无 grill 清单 ⇒ BLOCKED」；我**在本仓实跑**：
  `uv run witnessloop guard --root . --path src/witnessloop/cli.py` ⇒ 退 **1**，文案「无 stage=grill 的 manifest（现有 stage：（无））」。
- **「加 `EXIT_INTERNAL` 会让既有测试变红吗？→ 否（388 passed）」** → **站得住**。我复跑基线 `uv run pytest -q` ⇒ **388 passed in 19.31s**。
- **「design D3 的示例代码不能直接落地（`EXIT_INTERNAL` 未 import ⇒ NameError）」** → **站得住**。我把 `cli.py` 按 `design.md:63-72` **逐字**打补丁（不加 import），在非法 UTF-8 报告上
  实跑 ⇒ `NameError: name 'EXIT_INTERNAL' is not defined` ⇒ **exit 1（误拦）**；补上常数+import 后 ⇒ `UnicodeDecodeError` 被兜住 ⇒ **exit 4**。
  （⇒ 实现时若照抄示例，本 bug **原样复活**，且发生在 except 处理器里。）
- **「文档影响面：`docs/design.md` 与 `README.md` 不含 guard 退出码叙述（无需改）」** → **被证伪**。
  `README.md:35` 明确写 `# 本地守卫：… → 拦（exit 2）`，挂在 `witnessloop guard --path src/x.py`（直调 CLI）下——
  **这就是一条 guard 退出码叙述**，且 CLI 实际是 1。前一轮只点了 `docs/adr/0001-local-guard-hook.md:16`，
  **漏了 README**。⇒「方法（grep guard 退出码叙述）+ 该改清单」不完整。
- **「`check` 与 `guard` 共用同一判定函数」** → **站得住**。`evidence.py:170` 被 `guardcmd.py:108` 与 `checkcmd.py:79` 共用。

### `## Open Questions`

- **Q1 推荐「保持 D4（放行）、不在共享函数里硬化」** → **方向站得住，但推荐所依据的框架有漏**。
  (a) 推荐对「**报告**读点（`evidence.py:216`）」成立：在共享函数硬化会把 guard 翻转成拦，正是本 change 要消的镜像；
  且 fail-closed 的锚 `check` 已覆盖。
  (b) **但**「报告读点」与「**清单**读点（`evidence.py:165`）」是**两个不同归宿**的读点，Q1 把二者混为一谈：
  `_read_json` 对**同级**失败模式（manifest **不存在** / **JSON 语法坏**）的既有契约是「当作没有 manifest ⇒ **拦**」
  （`evidence.py:184-203` 产 Finding）。我实测：**JSON 坏**的 manifest ⇒ guard 退 **1（拦）**；
  而**字节坏**的 manifest ⇒ 修复后经顶层兜底退 **4（放）**。⇒ **同一类「manifest 坏了」，字节坏放行、JSON 坏拦截**——
  这个裂缝是「顶层兜底」**隐式**替 `evidence.py:165` 拍的板，**design 从未裁过**。Q1 的推荐文本没覆盖这个点。
  （另注：该处失败对 `check` 同样致命——`check` 读同一 manifest 也会崩，退 1，方向仍对。）
- **Q2 推荐「check 崩溃输出不进本 change」** → **站得住**。`proposal.md:28-29` 明列 `check` 为非目标，「报错难看属可读性」；
  本 change 只动 `cli` 的 guard 分支 + 一个常量，不改 `check` 任何路径 ⇒ **未引入 check 回归**。
  **但**：spec 新增的 Requirement「崩溃兜底不改变 check 的语义」其 Scenario（`spec.md:59-62`）**无任何测试钉住**
  （`grep -rn "UnicodeDecode\|无法解码\|decode" tests/` **0 命中**）⇒ 该 Scenario 属「写了但不可机械验证」。

### `## 风险`（对前一轮风险段的证伪/补充）

- 前一轮「不变量未机械钉死」成立，但**低估了当前触发面**：`design.md:50` 声称「兜底后『1』只由 `return C.EXIT_FAIL` 产生」。
  我实测证明**当前就有一个非 block 的 exit 1 源**（cli 自身 import 失败，见 CD3），不止「日后有人写 `sys.exit(1)`」这种假设。
- 前一轮对 `BaseException`（`KeyboardInterrupt`）的担忧可**部分消除**：我实测 `raise KeyboardInterrupt` 在 CPython 下
  以**信号**结束（`returncode == -2`，shell 见 130），经 shim `status=130 ≠ 1` ⇒ **放行**，不会造成误拦。
  （`SystemExit(1)` 才是真 1——但全树 `grep` 无硬编码 `sys.exit(1)`，仅 `cli.py:177`/`__main__.py:6` 的 `sys.exit(main())`。）
- 前一轮「顺序约束」成立且**已在本仓复现**（见下「必须修改」第 4 条），但 `tasks.md` 至今未覆盖。

## 必须修改

1. **收窄 / 修正 D3 与 spec 的「import 缺口」over-claim，或把安全网前移到入口。**
   证据：`cli.py:14-15` 的顶层 import 在 guard 分支 try **之外**；实测坏 `constants.py` ⇒ `witnessloop guard` **exit 1** ⇒ shim 拦。
   建议修法（二选一，择一并同步 `design.md:60-79`、`spec.md:8-9,26-29`）：
   (a) **收窄措辞**：把「覆盖 import 缺口」改为「覆盖 `guardcmd` 及其传递依赖的 import 缺口」，并在 spec 把
   「内部错误 SHALL 非 1」限定为「`cli.main` guard 分支内」；或
   (b) **前移兜底**：在 `__main__.py` / console-script 入口（`pyproject.toml:15`）也包一层 fail-open，
   使「cli 自身 import 失败」也不再退 1。若不做 (b)，**必须**在 design 的「非目标/边界」里显式写明此洞。
2. **裁定并写清「证据文件解码失败」的语义（manifest vs report 两个读点）。**
   证据：`evidence.py:165-167`（`_read_json`，漏 `UnicodeDecodeError`）与 `evidence.py:216`（报告读）归宿不同，
   实测字节坏 manifest ⇒ 修复后放行、JSON 坏 manifest ⇒ 拦截、manifest 缺失 ⇒ 拦截。
   建议修法：在 `design.md`（D4/新增决策）明确一条统一规则并落到 `spec.md`。推荐：**让 `_read_json` 一并捕获
   `UnicodeDecodeError`**（⇒ 坏 manifest 一律当「无 manifest ⇒ 拦」，与 `evidence.py:194-203` 既有契约一致），
   而**仅报告读点**保留 fail-open——即「**证据容器坏 = 不完备 = 拦；证据内容读不出 = 不可判定 = 放**」。若坚持
   manifest 字节坏也放行，则须在 design/spec **显式写明**这处不对称及其理由。
3. **把 `docs/adr/0001-local-guard-hook.md` 纳入 doc-sync 清单，并订正 `README.md:35`。**
   证据：`docs/adr/0001-local-guard-hook.md:16` 与 `README.md:35` **均**写 guard「拦（exit 2）」，而 CLI 实际
   `guardcmd.py:129` = `C.EXIT_FAIL` = **1**（2 只是 shim 给 CC 的映射）。`tasks.md` E3 只列
   「`README.md` / `docs/design.md`」，**未含 ADR**。建议：E3 增列该 ADR，并把两处的「exit 2」改为
   「CLI 退 1（shim 映射成 CC 的 2）」或等价准确表述。
4. **在 `tasks.md` 补「实现 `src/**` 之前必须先有一个 passing 的 `stage=grill` manifest」这一步。**
   证据（本仓实测）：`uv run witnessloop guard --root . --path src/witnessloop/cli.py` ⇒ exit 1
   「无 stage=grill 的 manifest」；且 `src/witnessloop/{constants,cli,guardcmd}.py` 均在 `require_change_for` 内
   （`constants.py:27-36`）。⇒ 实现者**先写 `src/**`** 会被自己的守卫拦。这不是死锁（本 change 会产出证据），
   但 `tasks.md` 现在没有任何一步覆盖它（前一轮只在 `## 风险` 里口头建议）。建议在 F 段前加：
   「**F0**：跑一次 `manifest build --stage grill`（先把 grill-review.md 的 Q1/Q2 写进 `## User Confirmation`，
   否则 guard 仍拦）→ 放行 `src/**` 写入；内容提交后**重跑覆盖**成最终 manifest。」
5. **给 spec 的 `check` Scenario 补测试，或删掉该不可验证的 Scenario。**
   证据：`spec.md:59-62` 声称「`check` 遇到无法解码的报告仍以非零结束」，但 `tests/` 无任何测试覆盖它
   （`grep` 0 命中），`design.md §5` 测试清单也没有 check 侧用例。建议：加一条
   `test_check_stays_fail_closed_on_an_undecodable_report`（断言 `main(["check",…])` 在非法 UTF-8 报告上不返回 0）。

## 新发现的风险

- **读点裂缝的连锁**：若日后有人**采纳 Q1 的替代方案**（在共享函数硬化 `evidence.py:216`），需同时处理
  **三个**读点（`evidence.py:216` / `evidence.py:165` / `policy.py:128`），否则只是把「洞」换个位置。
  这一条支持 Q1「不在共享函数硬化」的推荐，但也意味着 design 不能据此认为「读点只有一处」。
- **`check` 侧同病未纳入本 change 是对的，但 spec 把它写成了 Requirement** ⇒ 读者会以为它有测试背书（实际没有，见必须修改 5）。
- **`WITNESSLOOP_SKIP_GUARD=1` 与环境**：与本 change 无关，但注意 `spec.md` 未提逃生口对「内部错误放行」的语义关系（4 与 skip 都是放行，但语义不同）——非缺陷，提示文档若加「4」行宜一并说明。

## 我实测复现的

均在 `/tmp` 内造仓 / 打补丁副本，未在仓库留文件。

1. **基线**：`uv run pytest -q` ⇒ `388 passed in 19.31s`（与前一轮口径一致）。
2. **D3 修复路径跑通**（`/tmp/gce3root`，隔离副本，逐字按 `design.md:63-72` + 加 `EXIT_INTERNAL` 常量与 import）：
   - 非法 UTF-8 报告 ⇒ `guard` 退 **4** + 一行诊断；拦路径（manifset 在、报告不全）⇒ 退 **1**。
   - 真实 `guard.sh`：`cli_exit=1 → shim=2`、`cli_exit=4 → shim=0`（与 `{0→0,1→2,2→0,3→0,127→0}` 一起复现）。
3. **照抄 D3 示例（不加 import）⇒ 复活 bug**：非法 UTF-8 报告 ⇒ `NameError: EXIT_INTERNAL` ⇒ **exit 1**（误拦）。
4. **D3 边界洞**（`/tmp/gce2`，坏 `constants.py`）：`python -m witnessloop guard …` ⇒ `RuntimeError` ⇒ **exit 1**（shim 会当 block）。
5. **第三崩溃点**：非法 UTF-8 `.witnessloop/policy.json` ⇒ `policy_mod.load_policy` 抛 `UnicodeDecodeError`（`policy.py:128-129` 未捕获）⇒ guard 崩（修复前退 1）。
6. **读点裂缝**：`manifest 非法 JSON` ⇒ guard 退 **1（拦）**；`manifest 非法 UTF-8` ⇒ 崩（修复后放）；`manifest 缺失` ⇒ 拦。
7. **自锁复现**：本仓 `uv run witnessloop guard --root . --path src/witnessloop/cli.py` ⇒ **exit 1**「无 stage=grill 的 manifest」。
8. **check 侧**：`main(["check",…])` 在非法 UTF-8 报告上抛 `UnicodeDecodeError`（真实 CLI 退 1，fail-closed）。
9. **BaseException 归位**：`raise KeyboardInterrupt` ⇒ CPython **信号结束**（`returncode=-2`，shell 见 130）⇒ shim 放行，非误拦。

---

# 第 2 轮（R2）

> 立场：同 R1——**默认修订稿仍有错**，逐条证伪。先核验 R1 的 5 条必须修改**是否真被整合**（读文件、不信声明），
> 再对**修订后**设计找**新**洞。隔离副本在 `/tmp/r2`（未在仓库留文件）；仅改本文件，未 commit。

## Reviewer
- run id: grill-adversarial-reviewer-guard-crash-exit-2026-10-12-r2
- 时间: 2026-10-12T00:12:29Z

## Verdict

**CHANGES_REQUESTED**

R1 的 5 条**整合到位**（逐条见下，均有 `文件:行号` 核对）。但修订稿仍有一处**同类 over-claim 未消**，
且其根因正是 R1 自己**也没枚举全**的读点——只是换了模块：

- **N1（阻塞）**：`check` 遇**字节坏 manifest** 仍**崩**（traceback），而 **JSON 坏**给干净 finding——
  二者**不同归**。design D4-2 / spec Req2 声称的「manifest 解码失败 ⇒ `check` 红（**与 JSON 坏一致**）」
  **未被实现**，因为修复接线（`tasks.md` C3）只碰 `evidence.py`，而 `check` 在 `contract.py:_validate_one`
  **先崩**、**根本走不到** `evidence.py`。实测复现（甲副本）。
- **N2（阻塞·论证）**：甲案**否乙的理由**「乙会让 `check` 变绿 ⇒ 失去 fail-closed」**被证伪**（常见场景下
  `check` 仍红，靠 `report_hash` **独立**抓获）；且乙可**干净实现**（共享函数加一个带默认值的调用者参数）。
  甲案**可能**仍是对的选择，但**理由必须重写**——否则会误导用户对 Q1（**未决**）的裁定。

## R1 必须修改的整合核验（逐条）

1. **D3 over-claim 收窄** → **整合到位**。`design.md:30-32` 列为「修完仍存的边界」；`design.md:56-57`
   明写「**不覆盖**：`cli.py:14-15` 的**模块级** import 失败」；`spec.md:15-16` Requ1 加了「已知边界
   （不在本要求内）」；`design.md:136` R2 + `design.md:185-186` Q2。**实测边界仍在**：坏 `constants.py`
   ⇒ `guard` **退 1**（见「实测」6）。声明与实现一致，无 over-claim 残留。
2. **读点归一（policy/manifest/报告 三读点）** → **整合到位、但不完整**。`design.md:66-79` D4（policy⇒放、
   manifest⇒拦/红、报告⇒甲拦）与 `spec.md:38-41` Req2 **逐点一致**；`design.md:82-86` D5 与
   `spec.md:55-56` 的 policy 归一同口径。**无相互矛盾**。**但**三读点**只覆盖 `evidence.py`/`policy.py`**——
   `check` 侧另有 `contract.py:176,230` 两个 manifest 读点**未纳入**（N1）。
3. **文档漂移订正** → **整合到位**。`tasks.md:44`（F3）与 `design.md:98-102`（D7）**都**纳入
   `README.md:35` **与** `docs/adr/0001-local-guard-hook.md:16`。**实测两处当前文本**均写「拦（exit 2）」
   （`README.md:35` = 「…缺 grill 证据 → 拦（exit 2）」；ADR:16 =「…⇒ 拦（exit 2）」），而代码
   `guardcmd.py:129` = `C.EXIT_FAIL` = **1**（`constants.py:81`）⇒ **确为漂移**，订正方向正确。
4. **顺序约束 F0** → **整合到位、且正确**。`tasks.md:49-50`（G0）补了「先 `manifest build --stage grill`
   放行 `src/**` 写入 → 内容提交后**重跑覆盖**」。**约束本身对**：`guard` 放行条件是「grill 证据完备」
   （`guardcmd.py:108-114`）、非「目录在场」；`src/**` 在本仓 policy 的 `require_change_for` 内
   （`.witnessloop/policy.json`：`src/**`/`templates/**`/`plugin/**`）。**实测**：本仓
   `guard --path src/witnessloop/cli.py` ⇒ **退 1**「无 stage=grill 的 manifest」（「实测」5）；
   **且 F0 流程端到端可跑通**（「实测」7）。
5. **spec 的 `check` Scenario 补用例** → **整合到位**。`tasks.md:27`（C6）补
   `test_check_stays_fail_closed_on_an_undecodable_report`，对应 `spec.md:81-85` Req4 Scenario。
   ⇒ 原「写了但不可验证」**已消**。

## 逐条对抗结论（对**修订后**设计的新证伪）

### N1（阻塞）`check` + 字节坏 manifest 仍崩——「与 JSON 坏同归」不成立

- **design/spec 的声明**：`design.md:69-71` D4-2「manifest 解码失败 ⇒ 可诊断 Finding ⇒ **拦 / 红**……
  **这修掉对抗验证实测出的裂缝**（字节坏 manifest 放 vs JSON 坏拦）」；`spec.md:39-40` Req2「`check`
  **红**（与 **manifest 缺失 / JSON 语法坏一致**）」；`spec.md:48-51` Scenario「字节坏与 JSON 坏的同级
  失败同归」。
- **实测（甲副本，「实测」3）**：把 `reviews/grill.manifest.json` 覆写为非法 UTF-8（字节坏）⇒ `check`
  **退 1 且带 traceback**（崩在 `contract.py:230`）；把同一文件覆写为**非法 JSON** ⇒ `check` **退 1 且
  干净**（`manifest 无法解析：…` + 孤儿 + 无 stage）。⇒ **同级失败在 `check` 侧仍不同归**——正是 design
  声称「已修掉」的那条裂缝**在 `check` 侧原样存在**。
- **根因**：`checkcmd.run` 的调用顺序是 `validate_review_manifests`（`checkcmd.py:75`）**先于**
  `grill_evidence_findings_in_change`（`checkcmd.py:79`）。前者在 `contract._validate_one`
  （`contract.py:230`）对 manifest 做 `json.loads(read_text)`，`except (OSError, json.JSONDecodeError)`
  **漏 `UnicodeDecodeError`** ⇒ **在到达 `evidence.py` 前就崩**。⇒ `tasks.md` C3（只改 `evidence.py:165`）
  **对 `check` 无效**——那条只在 **`guard`** 生效（甲副本：`guard` 遇字节坏 manifest ⇒ **干净退 1（拦）**，
  「实测」3）。
- **第二处**：`contract.py:176`（`_bound_report`）**同病**，同样 `check` 可达、同样漏捕——只是 `:230` 先崩
  轮不到它。⇒ **R1 枚举了 ≥3 处崩溃点（`evidence`×2 + `policy`），但 `contract.py` 这两处 R1 也没列**；
  design 沿用 R1 的枚举，故**同样漏**。「读点枚举不完备」这坑**两轮都没抓全**（换了模块）。
- **与既有边界的关系**：`proposal.md:28-29` 把「`check` 报错难看」列为**非目标**，但 `design.md:140`
  R5 与 `spec.md:78-79` Req4 又**明确要**「只改 `check` 的报错路径（崩溃 ⇒ 干净的 finding）」——**设计自己
  承诺了 `check` 侧归一**，执行清单却只覆盖**报告**读点。⇒ 承诺与接线**不一致**。

### N2（阻塞·论证）甲案否乙的理由被证伪；乙可干净实现

- **design 的声明**（`design.md:74-78` D4-2 / `grill-review.md:59-61` Q1 理由(1)）：乙案「在共享函数里
  **无法干净实现**」——「让它对报告读失败**返回空 findings**（= 放行）会**同时让 `check` 变绿**
  ⇒ CI 锚失去 fail-closed」；「要两者分支就得给共享函数加『调用者』参数（**把职责渗入门禁层**）」。
- **实测（乙副本，「实测」4）**：
  - **报告在 manifest 之后被损坏**（**常见场景**：附写一个 `0xff`）⇒ 乙案下 `check` **仍退 1**
    （`report_hash 不匹配` 由 `contract._check_hashes`（`contract.py:371`）**独立**抓获）——**`check`
    没有变绿**。⇒ design 的「会同时让 `check` 变绿」**在这条常见路径上不成立**。
  - 仅当「报告损坏 **且** manifest 也在损坏字节上**重建**」（`manifest build` 读**字节**、不校报告正文，
    `manifestcmd.py:101` ⇒ 确实可行）时，乙才让 `check` **退 0（绿）**。
- **乙可干净实现**：给共享函数加一个**带默认值**的调用者参数（如 `on_unreadable_report="block"`，
  `guard` 传 `"allow"`），或让函数返回「不可核验」标记由**调用者**决定取舍——两者都在 `evidence.py`
  **一处**完成，`check` 仍 fail-closed、`guard` 仍 fail-open。⇒ 「无法干净实现」**是断言，不是事实**。
- **评估（翻不翻转？）**：甲案**不必然翻转**——甲仍有**真实**优势：(1) 无需新参数（口径留在共享函数里、
  不向门禁层渗**调用者**语义）；(2) 收紧「重建 manifest 于损坏字节」这个**乙漏掉**的角落（上条第二条）。
  但 **design 用来否乙的『会让 check 变绿』是错的前提**，而 Q1 是**未决的用户裁定**——**用错前提引导裁定**
  正是本仓「不许假声明」的红线。⇒ **必须**把 D4/Q1 的理由改成**真**陈述（甲严格 fail-closed、且在重建
  角落更严；代价仅是无参数的简洁性），或据此**重新评估**推荐。

### 其余角度（多为**确认**，无新洞）

- **甲案不自锁** → **成立**。`require_change_for` 不含 `reviews/**`/`docs/**`；写报告/文档在 `_code_paths`
  （`guardcmd.py:67-75`）里**豁免放行**。⇒ 「报告损坏 ⇒ 甲拦」**不会**锁死修复路径。`design.md:80` 成立。
- **甲案新增的 fail-closed 与 `docs/gate.md §8` 冲突？** → **已被 design 预见**。`gate.md:314` 的 fail-open
  列表（推不出/未给路径/写文档/未接入）**不含**「证据损坏」；甲**新增**一类 fail-closed，但 `design.md:137`
  R3 + `tasks.md:45` F4 已标为「对**接入方**的行为变更，须写明」，`design.md:96-97` D7/F2 计划改 §6/§8。
  ⇒ 不是隐藏冲突，是**已登记的行为变更**。
- **`check` 侧对别的 change 回归？** → **无**。基线 `uv run pytest -q` ⇒ **388 passed**；甲副本（补
  `EXIT_INTERNAL` + `guard` 兜底 + policy/evidence 补捕）⇒ **388 passed**（「实测」2）。改动只**多捕**异常、
  不增删规则 ⇒ 既有 change 的 `check` 不受影响。`design.md:113-114` D9 成立。
- **`design.md §1` 读点表**（`design.md:19-25`）→ **对 guard 准确、完整**。沿 `guardcmd.run` 链核对：文件
  读取仅 `policy.py:128`、`evidence.py:165`、`evidence.py:216` 三处（+ 非文件读 `gitutil._run`，已括注）
  ⇒ **无第 5 个 guard 可达读点**。缺的两处（`contract.py:176,230`）是 **`check` 专属**，不在 guard 链上——
  故 §1 表**无错**，只是**整体清单**仍不完整（N1）。
- **F0/两段提交互斥？** → **不互斥，但「重跑」是承重的**。实测（「实测」7）：F0 build（pre-content）→ 写
  `src/**` 放行 → 内容提交 → **重跑 build** → 证据提交 ⇒ `check` **绿**；**不重跑** ⇒ `check` 判
  「审阅的是旧 revision」（head_sha 停在 pre-content，`src/**`+change 目录全成 stray）。
- **spec 的每条 Scenario 都有对应用例** → **是**（Req1×3↔B1/B2/E1；Req2×3↔C5/C4/C2；Req3×2↔D1/D2；
  Req4×1↔C6）。**唯一**「写了但无 Scenario/无用例」的残留是 **Req2 正文里的 `check` 侧 manifest 归一**
  （见 N1）——它是**正文**而非独立 Scenario，故 R1 的第 5 条（补 check Scenario）**没覆盖到它**。

## 必须修改（R2）

1. **消灭 `check` 侧 manifest 读点的崩溃（或收窄 spec/design 的 `check` 声明）。** 二选一：
   (a) 把 `contract.py:176` 与 `contract.py:230` 的 `except (OSError, json.JSONDecodeError)` **一并补
   `UnicodeDecodeError`**（⇒ 字节坏 manifest 也走「manifest 无法解析」那条**干净 finding**，与 JSON 坏同归），
   并把 `tasks.md` C3/C4 的接线**扩到 `contract.py`**、补一条对 `check` 的用例；
   (b) 若不动 `contract.py`：把 `spec.md:39-40` 的「`check` **红**（与 JSON 语法坏**一致**）」**收窄**为
   「`guard` 侧一致；`check` 侧仍为**受控非零**（traceback，fail-closed 方向正确但不可诊断）」，并同步
   `design.md:69-71` D4-2。**不可**留着「已修掉裂缝 / 与 JSON 坏一致」的 in-line 声明而实际 `check` 仍崩。
2. **重写否乙的理由（`design.md:74-78` D4-2 / `grill-review.md` Q1 理由(1)）。** 把被实测证伪的前提
   「乙会让 `check` 变绿 ⇒ 失去 fail-closed」换成**真**陈述：乙**只在**「重建 manifest 于损坏字节」这一角落
   漏 fail-closed；甲**无新参数、口径不向门禁层渗调用者语义**，且在**该角落**更严。给出**可干净实现的乙案**
   （调用者参数 / 不可核验标记）并说明**为何仍（或不）推荐甲**。Q1 既为未决裁定，理由必须经得起证伪。

## 新发现的风险

- **「崩溃归一」在 `check` 侧是**分模块**的**：`evidence.py` 修好 ≠ `check` 不崩——`contract.py` 是 `check`
  的**第一道** manifest 读点（`checkcmd.py:75` 先于 :79）。⇒ 任何「归一共享函数读点」的方案，若只盯
  `evidence.py`，都**够不到** `check` 的 manifest 路径。这与 R1「读点枚举不完备」**同源、但换了模块**，
  两轮都没抓到 ⇒ 建议改用「**谁先在 `check` 路径读 manifest**」而非「谁在共享函数里」来列清单。
- **`manifest build` 读报告用**字节**（`manifestcmd.py:101` `sha256_tree`）⇒ 能在**字节坏报告**上**成功**
  产出 manifest**。这使「重建 manifest 掩盖报告损坏」成为**可达**回避面——正是甲相对乙的价值所在；建议在
  D4/Q1 **点明**这条（比现写的「会让 check 变绿」**准确**）。
- **F0 的重跑是承重的**：忘了重跑 ⇒ `check` stale。`tasks.md:49-50` 已写「重跑覆盖」，属实且必需；建议在
  F0 句末**显式**加「（**必须**重跑；否则 stale——且重跑前先 freeze `tasks.md`/`specs`，否则 hash 漂移）」。

## 我实测复现的

均在 `/tmp/r2` 内造仓 / 打补丁副本，**未在仓库留文件**；真 CLI 走 `python -m witnessloop`（`PYTHONPATH`
指副本 `src`），真 git 仓。

1. **基线**：`uv run pytest -q` ⇒ **388 passed in 18.09s**。
2. **甲副本全量**：按 design 落 `EXIT_INTERNAL=4` + `cli.py` guard 分支 `try/except` + `policy.py`/`evidence.py`
   补捕 ⇒ `PYTHONPATH=副本/src pytest -q` ⇒ **388 passed**（首跑 2 条 `test_agentenv` 红为 `/tmp` 模板
   路径假象，符号链接修正后消失——与代码无关；与 `grill-review.md:38` 口径一致）。
3. **`check` + 字节坏 manifest 仍崩**（甲副本）：
   - 字节坏 `grill.manifest.json` ⇒ `check` 退 **1 带 traceback**（`contract.py:230`）；`guard` 遇同一文件
     ⇒ **干净退 1（拦）**。
   - JSON 坏同一文件 ⇒ `check` 退 1 **干净**（`manifest 无法解析` + 孤儿 + 无 stage）⇒ **不同归**。
4. **乙副本（报告读失败 ⇒ 返回空 findings）**：
   - 报告在 manifest 之后损坏 ⇒ `check` **退 1**（`report_hash 不匹配`）——**没变绿**；`guard` 退 **0**。
   - 报告损坏 **且** manifest 重建于损坏字节 ⇒ `check` **退 0（绿）**——乙**唯一**漏 fail-closed 的角落。
5. **自锁复现**：本仓 `guard --root . --path src/witnessloop/cli.py` ⇒ **退 1**「无 stage=grill 的 manifest
   （现有 stage：（无））」。
6. **`cli.py` 自身 import 边界仍在**（甲副本，坏 `constants.py`）：`guard` ⇒ **退 1** `RuntimeError: broken
   install`（shim 会当 block）——与 `design.md:56-57` 声明的边界一致。
7. **F0 流程端到端**（甲副本）：F0 build（pre-content）⇒ 写 `src/**` 放行（退 0）⇒ 内容提交 ⇒ **重跑**
   build ⇒ 证据提交 ⇒ `check` **通过 ✓**；**不重跑** ⇒ `check` 退 1「审阅的是旧 revision」。
8. **字节坏 policy**（甲副本）：`guard` 退 **0**（放行，`policy 非法…不拦`）；`check` 退 **1** 干净
   （`policy 非法`）——与 `design.md:82-86` D5 一致。
