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

---

# 第 3 轮（R3）

> 立场：同 R1/R2——**默认修订稿仍有错**，逐条证伪。先核验 R2 的 N1/N2 **是否真被整合**（读文件 + 实测，不信声明），
> 再对**修订后**设计找**新**洞、走新增攻击角度。隔离副本在 `/tmp/r3`（`/tmp/r3orig` = 未打补丁、`/tmp/r3ev` = 只打 `evidence.py`），
> **未在仓库留文件**；仅改本文件，未 commit。真 CLI 走 `python -m witnessloop`（`PYTHONPATH` 指副本 `src`），真 git 仓。

## Reviewer
- run id: grill-adversarial-reviewer-guard-crash-exit-2026-10-12-r3
- 时间: 2026-10-12T08:20:00Z

## Verdict

**CHANGES_REQUESTED**

R2 的两条（N1/N2）**整合到位**，且我按 R2 的修法**实测复现**了「字节坏 manifest 在 `check` 下与 JSON 坏**同归**」——
N1 的修法有效。R1 的 5 条**全部未回退**。**但**修订稿仍残留**一处同类 over-claim**（与 R2 N1 同构：**spec/tasks 承诺的 finding 形态，其接线做不到**）：

- **M1（阻塞）**：`spec.md:39-40` Req2 与 `spec.md:48-51` Scenario 要求 `review manifest` 解码失败时 `guard` 的 finding
  **「点名该文件」**，`tasks.md` C4 进一步钉死「文案点名**『清单无法解码』**」。但 C3 的修法（`evidence.py:165` `_read_json`
  **补 `UnicodeDecodeError`**）**实测产出的文案是「无 stage=grill 的 manifest（现有 stage：（无））」**——**不含文件名、不含「清单无法解码」**。
  ⇒ **C4 自相矛盾**：它同时要求「文案点名『清单无法解码』」**与**「（与 JSON 坏 / 缺失**一致**）」，而 JSON 坏 / 缺失的文案恰是
  「无 stage=grill 的 manifest」——byte-bad **不可能**既说「清单无法解码」又「与 JSON 坏一致」。**照 C3 落地 ⇒ C4 必红**。
- **M2/M3/M4（非阻塞，但须一并订正）**：`F0`↔`G0` 标签错位；`design.md:3`/`tasks.md:3` 状态行 stale；
  B2 的 `sys.modules[...]=None` 技法**依赖导入序**（实测在「`guardcmd` 已被导入」时**不触发** ImportError）。

## R2 的 N1/N2 整合核验（逐条 · 读文件 + 实测）

### N1 → 整合**到位**，且**修法实测成立**

- **落点齐全**：`design.md:19-25`（§1 读点表新增 row：`contract.py:176` `_bound_report` / `contract.py:230` `_validate_one`）、
  `design.md:75-77`（D4-2 ⚠️ R2）、`design.md:144-145`（§3 接线点：`contract.py:176,230` 补 `UnicodeDecodeError`）、
  `tasks.md:28-31`（**C7** 实现 + **C8** 单测）**都在**。`spec.md` 未写行号（spec 不该写行号），其 `check` 侧口径见 Req2 正文。
- **行号核对**：`contract.py:176` = `_bound_report` 的 `json.loads(manifest_path.read_text(...))`；`contract.py:230` = `_validate_one` 的同款读——
  **两处 `except (OSError, json.JSONDecodeError)` 均漏 `UnicodeDecodeError`**，与 N1 断言一致。
- **实测（本仓新副本）**：`check` 遇**字节坏** `reviews/grill.manifest.json`：
  - **未打补丁**（`/tmp/r3orig`）⇒ **traceback**，崩在 `contract.py:230`（`_validate_one`，经 `validate_review_manifests` → `checkcmd.py:75`）——**复现 N1**。
  - **只打 `evidence.py`**（`/tmp/r3ev`，≈ C3 原样）⇒ `check` **仍 traceback**（`contract.py:230`）；`guard` 已干净（拦）。
    ⇒ **「只改 `evidence.py` 不够」属实**（N1 的根因坐实）。
  - **按 R2 修法补 `contract.py:176,230`**（`/tmp/r3`）⇒ `check` **退 1 且无 traceback**，三条 finding 与 **JSON 坏逐条同归**：
    `① …/grill.manifest.json：manifest 无法解析：<错>`、`② …/grill-review.md：孤儿报告…`、`③ …：无 stage=grill 的 manifest`。
  ⇒ **N1 整合正确、修法有效**（`design.md:76-77` 的「不同归」判断与「归一须同时覆盖 `contract.py:176,230`」**属实**）。

### N2 → 整合**到位**（假前提已删、按事实重写）

- `design.md:79-88` D4 已把 (a)、(b) 两条假前提**标为「伪」并改写**（`design.md:83-87`），并给出**甲/乙真实差别表**（`design.md:89-94`）。
- `grill-review.md:59-69` Q1 理由**同步重写**（`~~…~~ → 伪`）。
- **grep 复核**（`无法干净实现` / `变绿`）：两词在 `design.md`/`grill-review.md` 中**仅以「被证伪」形态出现**（`——**伪**` / `~~…~~`），
  **无残留的假陈述**。⇒ N2 **达标**。

## R1 的 5 条 → **全部未回退**（逐条复核）

1. **D3 over-claim 收窄** → 在。`design.md:30-34`（§1「修完仍存的边界」）、`design.md:56-59`（D3「不覆盖 `cli.py:14-15` 模块级 import」）、
   `design.md:225-226`（Q2）、`spec.md:15-16`（Requ1「已知边界（不在本要求内）」）。
2. **读点归一（policy/manifest/报告）** → 在，且已扩到 `contract.py`。`design.md:66-102`（D4/D5）、`spec.md:38-41`（Req2）、`spec.md:55-56`。
   实测三读点行为与设计逐点一致（见下「实测」）。
3. **doc-sync 两处** → 在。`design.md:110-119`（D7）、`tasks.md:48`（F3）**都**含 `README.md:35` **与** `docs/adr/0001-local-guard-hook.md:16`。
   **实测两处当前文本**确写「拦（exit 2）」（`README.md:35`、ADR:16），而代码 `guardcmd.py:129` = `C.EXIT_FAIL` = **1**（`constants.py:81`）⇒ 确为漂移。
4. **F0 顺序约束** → 在（**label 见 M2**）。`tasks.md:53-54`（G0）。
5. **spec 的 `check` Scenario 补用例** → 在。`tasks.md:27`（C6）、`spec.md:81-85`（Req4 Scenario）。⇒ 原「写了但不可验证」已消。

## R3 新证伪

### M1（阻塞）`guard` 侧 manifest 解码 finding 的**文案 over-claim**——C4 与 C3 互斥

- **声明**：`spec.md:39-40` Req2「`review manifest` 解码失败 ⇒ SHALL 产出一条**可诊断**的 finding（**点名该文件**）⇒ `guard` 拦」；
  `spec.md:48-51` Scenario「结论与 JSON 坏**一致**（拦 + **点名该文件**）」；`tasks.md:25` C4「字节坏 manifest ⇒ `guard` 退 1 且**文案点名『清单无法解码』**（与 JSON 坏 / 缺失一致）」；
  `tasks.md:24` C3「`_read_json` **补捕** ⇒ 产出 Finding「清单无法解码：`<file>`」」；`design.md:73` D4-2 同款文案；`design.md:142` §3「`_read_json` 补 `UnicodeDecodeError` + 可诊断 Finding」。
- **实测（`/tmp/r3`，按 C3 = 仅给 `_read_json` 的 `except` 加 `UnicodeDecodeError`）**：字节坏 manifest ⇒ `guard` **退 1**，stderr 文案
  = **「无 stage=grill 的 manifest（现有 stage：（无））——grill 决策记录必须有对应的审阅证据」**。**无文件名、无「清单无法解码」**。
  **与 JSON 坏 / manifest 缺失的文案逐字相同**。
- **根因**：`_read_json`（`evidence.py:163-167`）对**任何** JSON 解码失败（JSON 语法坏**或**字节坏）**都返回 `None`**⇒ 该 manifest 被静默跳过
  ⇒ `grill_evidence_findings_in_change`（`evidence.py:194-203`）走**通用**「无 stage=grill 的 manifest」分支，`Finding` 的 `path` 是 **change id 而非文件名**。
  **「补捕」只改变「崩 / 不崩」，不改变 finding 文案**。
- **矛盾点**：C4 同时要求「文案点名『清单无法解码』」**与**「（与 JSON 坏 / 缺失一致）」——而 JSON 坏 / 缺失文案是「无 stage=grill 的 manifest」。
  ⇒ 二者**不可兼得**：byte-bad 若真产出「清单无法解码」，就**与 JSON 坏不再一致**（除非 JSON 坏侧也改文案）。
  ⇒ **照 C3 落地，C4 必红**；照 C4 落地，得改的**不止** C3（要动共享函数 `grill_evidence_findings_in_change` 的文案逻辑，且会牵动 `check` 侧）。
- **修法（二选一，须同步 4 处）**：
  - **(a) 收窄文案（推荐，改动最小、与 R1 提案一致）**：把 `spec.md:39-40` 的「（点名该文件）」与 `spec.md:48-51` 的「点名该文件」
    限定到 **`check` 侧**（`contract._validate_one` 的 finding **确实**点名 manifest 文件——实测 finding `path` = `…/reviews/grill.manifest.json`），
    `guard` 侧改为「与 JSON 坏 / 缺失同归：**无 stage=grill 的 manifest**」；C4 断言改为 `guard 退 1 且文案含「无 stage=grill 的 manifest」`；
    `design.md:73,142` 的「清单无法解码：`<file>`」同步改为「`guard`：无 stage=grill 的 manifest；`check`：manifest 无法解析：`<file>`」。
  - **(b) 扩 C3（改动大）**：让 `grill_evidence_findings_in_change` 对**无法解析**的 manifest **按文件名**产 finding，且 **byte-bad 与 JSON-bad 都如此**
    （才保「同归」），并**防 `check` 侧** `contract`（`_validate_one`）与 `evidence`（共享函数）**对同一文件重复报**。此路须在 design/tasks 写明，非「补捕」二字可覆盖。

### M2（非阻塞）`F0` ↔ `G0` 标签错位

- `design.md:135`「`tasks.md` 记此为 **F0**」、`design.md:199`「**`tasks.md` 补 F0**」、`design.md:212`「F0 与两段提交不互斥」——但 `tasks.md:53` 的该步**标为** **G0**（§F 是「文档」，F1–F4，**无 F0**）。
  ⇒ design 两处交叉引用**指错标签**。修法：`design.md:135,199,212` 的 `F0` 统一改成 `G0`（或把 `tasks.md` 的 `G0` 改名 `F0`）。

### M3（非阻塞）状态行 stale

- `design.md:3`「…R1 CHANGES_REQUESTED → 已整合 → **待 R2**」——R2 已整合（commit `025e682`），应改「R2 已整合 → **待 R3/用户确认**」；
  `tasks.md:3`「**R1** 已整合」同滞后，应含 R2。**理由错（声明与实况不符）**是本仓红线，宜顺手订正。

### M4（非阻塞）B2 的 `sys.modules[...]=None` **依赖导入序**

- `design.md:173`/`tasks.md:15`/`spec.md:23-26` 用 `sys.modules["witnessloop.guardcmd"] = None` 造 `ImportError`。**实测**：
  - **新进程**（`guardcmd` 从未导入）⇒ `from witnessloop import guardcmd` **抛 `ModuleNotFoundError`** ⇒ 底 ⇒ 退 **4** ✅。
  - **`guardcmd` 已被导入过一次**（`witnessloop.guardcmd` 已成了 `witnessloop` 包的**属性**）⇒ `from witnessloop import guardcmd` **直接取属性、不再查 `sys.modules`**
    ⇒ **不抛** ⇒ `guard` 正常跑 ⇒ 退 **0**（实测；非 4）。⇒ **B2 若照抄，在完整 suite 里（任一 `guard` 调用先跑过即会污染）会红/不稳**。
- 修法：B2 同时 **删除包属性**（`monkeypatch.delattr(sys.modules["witnessloop"], "guardcmd", raising=False)`）再置 `sys.modules[...]=None`，或**改用隔离子进程**。
  （**注**：这不是「B2 场景不成立」——它在隔离下成立；是**技法对导入序敏感**，须写死。）

### 走查过的角度：**无**新洞（特此记录，避免下一轮重复）

- **孤儿报告规则**（R3 点名角度）：字节坏 manifest 使 `contract._bound_report` 归一后返回 `None` ⇒ 其应对应的报告进不了 `bound` ⇒ `_check_orphan_reports`
  **确实额外报一条「孤儿报告」**。**但** JSON 坏 manifest **同样**触发该条（`_bound_report` 对 JSON 坏也返回 `None`）⇒ **两案仍逐条同归**，**非新不一致**（实测三条 finding 逐字相同）。
  语义上也非纯误导：「manifest 无法解析」+「报告无人绑定」是两条**互补**信息。⇒ **无需**顺带处理（若想更精准可另立 issue，**不阻塞**）。
- **`manifest build` 自己读 manifest 吗**（R3 点名角度）：**否**。`manifestcmd.run_build` 只读 policy / change 目录 / **report 字节**（`sha256_tree`）/ git；
  **不读任何 manifest**，且对同名 manifest **直接覆写**（`manifestcmd.py:152`）。**实测**：预置字节坏 manifest 后 `manifest build` **退 0**（覆写成功，无崩溃）。⇒ **无漏覆盖**。
- **D3 兜底与读点归一的交互**：归一后 `guard` **仍能**撞到 `EXIT_INTERNAL`，且**有真实（非 monkeypatch）触发源**——`git` 不在 `PATH` ⇒ `gitutil._run` 抛 `FileNotFoundError` ⇒ 底 ⇒ **退 4**（实测 `PATH=/nonexistent`）。
  B1（monkeypatch `RuntimeError`）是通用底**好代表**；B2 技法须修正（M4）。`design.md:27` 已括注 `gitutil._run` 这一潜在读点，**无遗漏**。
  grep 复核：全树**无**硬编码 `sys.exit(1)`/`raise SystemExit`/`return 1` ⇒「1 只由 `return C.EXIT_FAIL` 产生」在归一后**结构性成立**。
- **`design.md §5` 测试策略 vs C 段**：一致（报告字节坏「甲退 1 / 乙退 4」= C5；manifest 字节坏「退 1 与 JSON 坏/缺失同归」= C4；check 侧「干净红」= C8）。
  §5 的 TBD 措辞「（按 Q1 结果二选一）」**属预期**（Q1 是**未决**的 Open Question），非缺陷。
- **spec 逐条 ↔ tasks 用例**：9 个 Scenario **都有**对应用例（Req1×3↔B1/B2/E1、Req2×3↔C5/**C4**/C2、Req3×2↔D1/D2、Req4↔C6）。
  唯一「写了但形态对不上」的是 **M1**（Req2 正文/Scenario 的 `guard` 侧「点名该文件」）。
- **`contract.py` 单测归属**：`design.md:149` 已点名 `tests/test_check_manifest.py` / `test_check_grill_evidence.py`（`check` 对无法解码 evidence 的干净红 = C8 的落点）
  ⇒ **有**归属文件（`tasks.md` C7/C8 未重复点名，非缺陷）。
- **甲案角落（Q1）**：报告在 manifest **之后**损坏 ⇒ **甲** `check` 退 1（`report_hash 不匹配` + **「报告无法解码」**）；**「重建 manifest 于字节坏报告」后** ⇒ **甲仍退 1**（`报告无法解码`，实测）
  ——**甲确封住**该角落，`design.md:92` 的对比**属实**。

## 必须修改（R3）

1. **消灭 M1（唯一阻塞）**：二选一并**同步** `spec.md:39-40`、`spec.md:48-51`、`tasks.md:24-25`(C3/C4)、`design.md:73,142`——
   (a) **收窄文案**至实测形态（`guard`：无 stage=grill 的 manifest；`check`：manifest 无法解析：`<file>`），把「点名该文件」限定到 `check` 侧；或
   (b) **扩 C3** 为「按文件名产 finding（byte-bad 与 JSON-bad 一致）+ 防 `check` 侧重复报」。**不可**保留「补捕 ⇒ 点名该文件 / C4 文案『清单无法解码』」这套与实际接线互斥的措辞。
2. **订正 M2 标签**：`design.md:135,199,212` 的 `F0` → `G0`（或反向改名）。
3. **刷新 M3 状态行**：`design.md:3`、`tasks.md:3` 的 R1/R2 口径。
4. **加固 M4 技法**：B2 补 `delattr(sys.modules["witnessloop"], "guardcmd")` 或改隔离子进程。

## 我实测复现的（均在 `/tmp/r3*`，未在仓库留文件）

1. **基线**：本仓 `uv run pytest -q` ⇒ **388 passed in 19.23s**。
2. **甲副本全量**（按 design 落 `EXIT_INTERNAL=4` + `cli.py` guard 兜底 + `policy.py`/`evidence.py`/`contract.py:176,230` 补捕）⇒ **388 passed**（`/tmp` 模板路径假象用真 `templates/` + `.github/` 修正后消失，与代码无关）⇒ **无回归**。
3. **N1 复现与修复对照**（字节坏 `grill.manifest.json`）：
   - 未打补丁：`check` **traceback**（`contract.py:230`）；只改 `evidence.py`：`check` **仍 traceback**（`contract.py:230`）；补 `contract.py:176,230` 后：`check` **退 1 干净**。
   - 同修后 `check` 的三条 finding 与 **JSON 坏逐字相同**；`guard` 两案均退 1、文案「无 stage=grill 的 manifest」。
4. **M1**：`guard` 遇字节坏 manifest ⇒ 文案 = 「无 stage=grill 的 manifest（现有 stage：（无））…」——**不含**文件与「清单无法解码」（对照 `spec.md:39-40`/`tasks.md:25`）。
5. **报告字节坏**（甲）：`guard` 退 1「报告无法解码：reviews/grill-review.md（UnicodeDecodeError）」；`check` 退 1（`report_hash 不匹配` + `报告无法解码`）——无 traceback。
6. **甲角落**：报告字节坏 **且重建 manifest** ⇒ `check` **退 1**（`报告无法解码`）——甲封住该角落。
7. **policy 字节坏**：`guard` 退 **0**（放行，`policy 非法…不拦`）；`check` 退 **1** 干净（`policy 非法`）。
8. **D3 兜底**：B1（monkeypatch `RuntimeError`）⇒ **退 4**；`sys.modules[...]=None`（**新进程**）⇒ 退 **4**，**（`guardcmd` 已导入）⇒ 退 0**（M4）；`git` 不在 `PATH` ⇒ 退 **4**（真实源）。
9. **shim 映射**（真 `guard.sh`）：`1→2`、`4→0`、`0/2/3/127→0`。
10. **`manifest build` 容忍预置字节坏 manifest**：退 **0**（覆写）。

---

# 第 4 轮（R4）

> 立场：R4 是 R3 明说的「作者刻意破例的最后一轮」——**只做确认，不重开** R1–R3 已闭的洞。
> 默认 R3 的「已整合」仍可能有漏，逐条**读文件 + 实测**核验 R3 的 M1–M4 **是否真被整合**（不信 commit message / 声明）。
> 隔离副本在 `/tmp/r4`（`/tmp/r4/repo` 真 git 仓 + `/tmp/r4/src` 按 C3/C7 打补丁副本），**未在仓库留文件**；仅改本文件，未 commit。

## Reviewer
- run id: grill-adversarial-reviewer-guard-crash-exit-2026-10-12-r4
- 时间: 2026-10-12T00:28:47Z

## Verdict

**CHANGES_REQUESTED**

R3 的 **M2/M3/M4 整合到位**（逐条核对；M4 的技法断言我独立实测坐实）。**但 M1 整合不完整**——
R3 点名的 over-claim 是「**同一处 × 两个 site**」：`spec.md:39-40` 正文 **+** `spec.md:48-51` Scenario，外加 `design.md:73,142`。
作者改了**正文**（`spec.md:39-40`）、`tasks.md` C3/C4、`design.md:73`，**但 `spec.md:48-51` Scenario 与 `design.md §5`（`:186`）两处原样留存**，
而这两处**恰仍写着 R3 M1 要消灭的「点名」+「同归」并存**：

- **N1（阻塞）** `spec.md:48-51`（Req2 的 Scenario「字节坏与 JSON 坏的同级失败同归」，`When` = **运行 `guard`**）仍写
  「结论与『manifest 是非法 JSON』**一致**（拦 + **点名该文件**）」。实测 `guard` 对**字节坏**与 **JSON 坏** manifest 的结论**逐字相同**、
  且**不含文件名**（「实测」2）⇒ 此 Scenario **既与同 Req 正文 `spec.md:40`「`guard` 侧……不额外点名文件」冲突**，
  也**与 `tasks.md` C4「断言两案输出**相等**」冲突**（C4 已不含「点名」）。按此 Scenario 写测试**必红**。
- **N2（阻塞）** `design.md:186`（§5 测试策略）仍写「manifest 字节坏 ⇒ `guard` 退 **1** 且**文案点名「清单无法解码」**；
  **与 JSON 坏 / 缺失同归**（同一断言形状）」——**与 `design.md:73-77`（D4-2）及 `tasks.md` C4 直接矛盾**：
  `guard` 不点名文件（实测），且「点名『清单无法解码』」与「与 JSON 坏同归」在本实现下**不可兼得**
  （`_read_json` 捕到即 `None` ⇒ 两案同一文案）。R3 在「走查过的角度」把 §5 判为「一致」时**漏读了该分句**
  （只转述「退 1 / 与 JSON 坏同归」而略去「点名『清单无法解码』」），故作者未动它。

这两处都属 R3 M1 的**同一 over-claim 未消**，是「会让测试失败 / spec over-claim」的硬问题 ⇒ 阻塞。

## R3 M1–M4 整合核验（逐条 · 读文件 + 实测）

### M1 → **未完全整合**（tasks / spec 正文 / D4-2 / R8 到位；**2 处残留**）

**已到位**（逐条核对，均自洽）：
- `tasks.md:26-27`（C3）：`_read_json` 补捕 `UnicodeDecodeError` ⇒「**与 JSON 坏/缺失同归**」，并显式警告「**不要**在这里新造『清单无法解码：`<file>`』文案」。✓
- `tasks.md:28-29`（C4）：「字节坏 manifest ⇒ `guard` 退 `1`，且其结论**与『JSON 坏 manifest』逐字相同**（断言**两案输出相等**，而非钉某个固定字符串）」。✓（正是 R3 要求的改法）
- `spec.md:39-40`（Req2 正文）：「……**同归**（`guard` **拦**、`check` **红**）；`check` 侧的 finding SHALL 点名该文件（`guard` 侧沿用既有文案、不额外点名文件）」。✓
- `design.md:73-77`（D4-2 ⚠️R3 M1）：明写「`guard` 侧**不新增文案、不点名文件**……**『点名该文件』只落在 `check` 侧**」。✓
- `design.md:171-175`（§4 R8）：记「`guard` 对『坏 manifest』『无 manifest』文案相同」为**有意代价**，并注「`check` 侧**有**点名」。✓

**残留（阻塞）**：`spec.md:48-51`（N1）与 `design.md:186`（N2）——见 Verdict。

### M2 → **整合到位**

- `grep -rn "F0"` 在 `design/tasks/spec/proposal` **0 命中**（仅 `reviews/grill-adversarial.md` 的 R1/R3 历史记录里，属预期）。
- `design.md:139`「`tasks.md` 记此为 **`G0`**（该文件 G 段首步）」、`design.md:208`「**`tasks.md` 补 `G0`**」、`design.md:221`「**`G0`** 与两段提交不互斥」——三处已统一为 **`G0`**，与 `tasks.md:57` 的 `G0` 一致。✓

### M3 → **整合到位**

- `design.md:3`：「……R1/R2/R3 三轮 CHANGES_REQUESTED → 逐轮已整合；R3 收尾项已修。停轮待用户确认。」——**不再有「待 R2」**。✓
- `tasks.md:3`：「……R1/R2/R3 已逐轮整合、R3 收尾项已修……」——**不再是「R1 已整合」**。✓
- `grep "待 R2\|R1 已整合"` 在正文 **0 命中**（仅历史记录文件）。✓

### M4 → **整合到位，且技法断言经我独立实测坐实**

- `tasks.md:15-17`（B2）已写明：**只** `sys.modules[...]=None` **不够** ⇒ 必须**同时** `monkeypatch.delattr(witnessloop, "guardcmd", raising=False)`。✓
- **实测**（「实测」4）：**新进程**里 `sys.modules["witnessloop.guardcmd"]=None` ⇒ `from witnessloop import guardcmd` **抛 `ImportError`**；
  **先把 `guardcmd` 导入过**（它成了 `witnessloop` 包属性）后，同法**不抛**、`from … import` **直接取属性返回旧模块** ⇒ guard 正常跑（退 0、用例不稳）；
  补 `delattr(witnessloop, "guardcmd")` 后**恢复抛 `ImportError`**。⇒ **M4 的技术判断属实**，`tasks.md` 的修法**正确且必要**。

## 逐条对抗结论（对**修订后**稿的确认 / 新证伪）

- **spec.md Scenario ↔ tasks 用例一一对应** → **基本成立，1 处形态错位**：9 个 Scenario 均有用例
  （Req1×3↔B1/B2/E1、Req2×3↔C5/**C4**/C2、Req3×2↔D1/D2、Req4↔C6）。
  **唯一**错位的是 Req2 第二 Scenario（`spec.md:48-51`）——其 `Then` 仍含「点名该文件」，而对应用例 C4 已改为「两案输出相等」（= N1）。
- **`design.md §4 R8` 与 D4-2 一致** → **是**（R8 的「有意代价」与 D4-2 的「不点名文件」同口径）。
- **`design.md §5` 与 D4-2 一致** → **否，一处残留**（`:186` 的「点名『清单无法解码』」= N2）。另注 `:182` 仍只写
  `sys.modules["witnessloop.guardcmd"] = None`（**缺 M4 的 `delattr` 注解**）——但 `tasks.md` B2 已带注解，且 `:182` 只是「测试名 + 步骤」摘要、非唯一出处 ⇒ 记**非阻塞**。
- **`design.md` D4 甲/乙对比表（`:93-98`）无假陈述** → **是**（R2/R3 已重写；「甲封住『重 build 坏报告』角落的 `check`」经 R3 实测成立）。
- **spec 逐条真的可落地** → **基本成立**；唯一**不可照抄**的是 N1 那句。
- **`check` 侧「点名该文件」属实** → **是**（实测：`check` 对字节坏 / JSON 坏 manifest 均报
  `openspec/changes/add-x/reviews/grill.manifest.json：manifest 无法解析：<err>`，**含文件名**）⇒ `spec.md:40` 的 check 侧口径**正确**；错的只是把这一性质**搬到 guard** 的 N1/N2。
- **R3 的 M2/M3/M4 未回退** → **是**（本轮复核）。
- **无新洞**：本轮未发现 R1–R3 范围外的新问题；N1/N2 均为 R3 M1 的**未消残留**（R3 已点名 `spec.md:48-51`）。

## 阻塞项

1. **N1**：改 `spec.md:48-51`（Req2 Scenario）——把「（拦 + **点名该文件**）」改为**分侧**的准确表述，例如
   「结论与『manifest 是非法 JSON』**一致**（`guard` **拦**、文案同为『无 stage=grill 的 manifest』；`check` **红**、finding **点名该 manifest 文件**）」，
   删去 `guard` 侧的「点名该文件」，与 `spec.md:40` 正文、`tasks.md` C4 对齐。
2. **N2**：改 `design.md:186`（§5）——把「`guard`……文案点名『清单无法解码』；与 JSON 坏 / 缺失同归」改为
   「`guard` 退 `1`，文案 = **无 stage=grill 的 manifest**（**与 JSON 坏 / 缺失逐字相同**、**不点名文件**）」（可选：补一句「`check` 侧另有 `manifest 无法解析：<file>`」）。

## 非阻塞建议

- `design.md:182`（§5）的 `sys.modules["witnessloop.guardcmd"] = None` 摘要宜补「（**须同时 `delattr` 包属性**，见 `tasks.md` B2 / R3 M4）」，免得实现者单看 §5 照抄不稳定技法。
- `design.md:146`（§3 接线点）「`_read_json` 补 `UnicodeDecodeError` **+ 可诊断 Finding**」措辞偏松：`guard` 侧并**不新增**可诊断文案（与 D4-2 的定案相反）——宜改为「+ 与 JSON 坏/缺失**同归**（不新增文案）」，与 §5/§4 R8 同口径。
- `spec.md:40` 的「`check` 侧的 finding SHALL 点名该文件」目前**无独立 Scenario / 用例**（C7/C8 只钉「不抛异常 + 非 0」）——属既有行为（`contract.py:232`），可选补一条断言以钉死；**不阻塞**。

## 我实测复现的（均在 `/tmp/r4*`，未在仓库留文件）

1. **基线**：本仓 `uv run pytest -q` ⇒ **388 passed in 19.50s**。
2. **N1/N2 对照**（`/tmp/r4`：真 git 仓 + `PYTHONPATH=/tmp/r4/src`，`src` 按 C3（`evidence.py:166`）+ C7（`contract.py:177,231`）补 `UnicodeDecodeError`）：
   - `guard` 遇**字节坏** manifest ⇒ 退 **1**，stderr：`无 stage=grill 的 manifest（现有 stage：（无））——grill 决策记录必须有对应的审阅证据`（**无文件名**）。
   - `guard` 遇 **JSON 坏** manifest ⇒ **逐字相同**（同文案，退 1）。
   - ⇒ `spec.md:51` / `design.md:186` 的「`guard` 点名（该文件 / 『清单无法解码』）」**被证伪**。
3. **`check` 侧点名属实**：`check` 遇**字节坏**或 **JSON 坏** manifest ⇒ 均报
   `openspec/changes/add-x/reviews/grill.manifest.json：manifest 无法解析：<err>`（**含文件名**），退 **1**（无 traceback）。
4. **M4 独立复现**（三态）：
   - 新进程 `sys.modules["witnessloop.guardcmd"]=None` ⇒ `from witnessloop import guardcmd` **抛** `ImportError: import of witnessloop.guardcmd halted; None in sys.modules`。
   - 先 `import witnessloop.guardcmd`（成包属性）后再置 `None` ⇒ **不抛**，`from witnessloop import guardcmd` **返回旧模块**（`hasattr` 为真）⇒ 对应 guard 退 0、用例不稳。
   - 追加 `delattr(witnessloop, "guardcmd")` 后 ⇒ **恢复抛** `ImportError`。⇒ `tasks.md` B2 的修法**正确且必要**。
5. **M2/M3 grep**：`F0` 在四个 change 文本 **0 命中**；`G0` 命中 `tasks.md:57` + `design.md:139,208,221`；`待 R2` / `R1 已整合` 在正文 **0 命中**（仅历史记录文件）。

---

# 第 5 轮（R5）

> 立场：**收窄轮**——只审 commit `a5c761d`（停轮确认 Q1=甲 / Q2=修掉 ⇒ **D3 重写为进程入口兜底** + ADR 0002）这一改动。
> 默认它有错，逐条证伪；能实测的都在 `/tmp` 造**打补丁副本**实测。**未在仓库留文件、未 commit**（`/tmp` 之外无产物）。
> **关键前提**：`a5c761d` **只改 docs**（`design.md`/`proposal.md`/`spec.md`/`tasks.md`/`grill-review.md` + 新增 ADR 0002），
> **未动 `src/**`、`pyproject.toml`、`src/witnessloop/__main__.py`、`tests/conftest.py`**（`git show --stat a5c761d` 核实）⇒
> 本轮是**设计期**审阅：D3 是**待实现的设计**（`tasks.md` B 段），我按它打补丁后**实测**其行为与覆盖。

## Reviewer
- run id: grill-adversarial-reviewer-guard-crash-exit-2026-10-12-r5
- 时间: 2026-10-12T09:05:00Z

## Verdict

**PASS**

D3 的**覆盖面经实测成立**（坏 `constants.py` / 坏 `cli.py` 经**真实入口**跑 `guard` ⇒ 退 **4**；`check`/`init`/`manifest` ⇒ **1**）；
入口改造**无回归**（`--help`/`--version`/用法错误仍以 `SystemExit(0/2)` 传播；补丁副本 **388 passed**；`uv build` + `uvx --from wheel --version` 通过）。
指派我证伪的**「argparse 前缀缩写 ⇒ 误拦复活」经实测为假前提**——argparse **不**对子命令做前缀缩写（`gu`/`bu` 均 → `invalid choice` 退 **2**；
`allow_abbrev` 只作用于长选项，`--vers` 可缩写退 0 对照）。
无阻塞项。3 处**文档残留 / 测试缺口**（均不阻塞，可后修）：`design.md:234` 仍把「兜底落 `cli.main` guard 分支」列为**已确认决策**（与 D3 矛盾）；
`design.md:155`（D8）仍写「`cli.main` 的 guard 分支及之后」（D3 已移除该分支）；「`SystemExit` 照常传播」这条**承重**性质**无任何测试钉住**。

## 逐条对抗结论

### 1. D3 的覆盖是否完整 → **是（实测成立）**

- **声明**（`design.md:57-89` D3；`spec.md:6-40` Req1 + 3 个 Scenario；`ADR 0002:19-30`）：入口 `try` **同时**包住
  (a) `from witnessloop.cli import main`（**含 `cli.py` 自身模块级 import 失败**）与 (b) `cli_main(argv)` 的运行期异常；
  verb=`guard` ⇒ **4**、其余 ⇒ **1**。
- **实测**（打补丁副本、**真实入口** `python -m witnessloop`，见「实测」2–3）：
  - 坏 `constants.py`（`cli.py:15` 模块级 import 炸）⇒ `guard` **退 4**、`check`/`init`/`manifest` **各退 1**；
  - 坏 `cli.py`（`__main__.py:3` 处 import 炸）⇒ `guard` **退 4**、`check` **退 1**；
  - 运行期 `RuntimeError`（monkeypatch `guardcmd.run`）⇒ `entry.main(["guard",…])` 返 **4**、`["check",…]` 返 **1**。
  ⇒ (a)/(b)/verb 分流三条断言**全部成立**；`cli.py:14-15` 的旧洞（R1–R4 反复复现的 `exit 1` 误拦）**已被入口兜底关闭**。
- **argv 判 verb 的漏洞面（指派假设）→ 证伪**：`design.md:78-80` 按 **argv 第一词**判 verb。指派攻击为
  「argparse 默认允许**子命令前缀缩写**，`witnessloop gu` 解析成 `guard`，但第一词是 `gu` ⇒ 判成非 guard ⇒ 退 1 ⇒ 误拦复活」。
  **实测（Python 3.12.13，本仓 `build_parser()`）**：`gu` / `guar` / `g` / `che` /（`manifest bu`）**全部** `invalid choice` ⇒ `SystemExit(2)`；
  经**真实入口**（`uvx` 装 wheel 后 `witnessloop gu`）**同退 2**。⇒ `allow_abbrev` **只作用于长选项**（`--vers` 可缩写、退 0），
  **不作用于子命令 choice** ⇒ 该「误拦复活」路径**不存在**。
  - **残留的（非本轮缺陷的）脆弱性**：verb 判据绑「argv 首词 = 规范动词」。今日顶层只有 `--version`/`-h`（都在 `parse_args` 里走 `SystemExit`、不落兜底），故成立；
    但若日后顶层新增**可置于子命令之前的全局选项**（如全局 `--root`），`witnessloop --root x guard` 首词就成了 `--root` ⇒ 崩溃时判成「非 guard」退 1 ⇒ 误拦复活。
    **当前不存在该选项**，故非缺陷（见非阻塞 6，建议留约束）。
- **非 guard verb 的 fail-closed**：`check` 崩溃 ⇒ **1**（= 未通过）、`init`/`manifest` ⇒ **1**（= 失败）—— 实测成立，与 `spec.md:19-20,37-40` 一致。

### 2. 入口改造有无回归 → **无（实测）**

- **`SystemExit` 传播**：经真实入口 `--version` ⇒ **0**、`--help` ⇒ **0**、未知子命令 ⇒ **2** —— 不被 `except Exception` 吃掉（`SystemExit` ⊂ `BaseException`）。与 `design.md:81-82` / `ADR 0002:26` 一致。
- **388 全绿**：`tests/conftest.py` 的 `cli` fixture 改调 `entry.main`（其余按 D3/D4/D5 落补丁）⇒ `uv run pytest -q` ⇒ **388 passed**（「实测」1）。
- **`test_cli.py` 直接调 `cli.main` 的路由用例**（`:19,25,32,45,58,64`，`from witnessloop.cli import … main`）**不受 fixture 影响**（fixture 只被别的文件用）⇒ 仍直测进程内 API，符合 `design.md:174`「`cli.main` 仍是进程内 API」。
- **打包 / CI**：`pyproject.toml:11` 改 `witnessloop.entry:main` 后，`uv build` 成功、`uvx --from dist/*.whl witnessloop --version` ⇒ **退 0 且打印 `witnessloop 0.1.0`**（与 `ci.yml:29-33` 的打包冒烟同款命令）；`python -m witnessloop --version` 同（`test_cli.py:69` 的 `test_console_script_is_installed` 也在 388 里绿）⇒ CI 不受影响。
- **ⓘ 一处测量假象（非缺陷，记录以免误导下一轮）**：我首轮用 `uvx --from <本地 wheel>` 连跑时 `init`/`guard` 曾返回 1——**根因是 uvx 按 `name==version`（同为 `0.1.0`）缓存了旧环境**（原 wheel 与补丁 wheel 版本号相同）；清缓存重测即得预期值：未接入仓 `guard` ⇒ **3**（原/补丁 wheel 同值）、`init` ⇒ **0**、`bogus` ⇒ **2**。⇒ 与本次改动无关。

### 3. 两处 `4` 的等值守卫 → **在位**

- `spec.md:14`：「该常量 SHALL 在入口与 `constants` 两处**同值**（由测试钉住）」；`design.md:88-89`（D8）；`tasks.md:29`（**B10**：`entry._EXIT_INTERNAL == C.EXIT_INTERNAL == 4`）；`tasks.md:9`（A1：`C.EXIT_INTERNAL == 4 != EXIT_FAIL`）。三处齐备、口径一致。✅
- `4` 今日仍空闲（`constants.py:80-83` 只有 0/1/2/3）；`grep -rn "sys.exit(1)\|SystemExit(1)\|return 1" src/witnessloop/` **0 命中**（D8 的「1 只由 `return C.EXIT_FAIL` 产生」结构性成立）。

### 4. spec/tasks/design 与改动是否一致？→ **基本一致；2 处残留（非阻塞）**

- **Req1 措辞 + Scenario**（`spec.md:6-45`）与 D3/ADR 同口径：进程入口、含 `cli` 自身 import 失败、非 guard ⇒ 1。✅
- **B 段**（`tasks.md:12-29`）：B1/B2（guardcmd ImportError + `delattr` 注解，**R4 M4 在**）/B3（cli import）/B4（非 guard⇒1）/B5/B6/B7/B8/B10 —— 齐备且与 D3 一致。✅
- **ADR 0002 事实**：`entry.py` 不 import witnessloop、argv 首词分流、只捕 `Exception`、单一兜底、两处 `4` 同值 —— 与 D3 逐条对得上。✅
- **残留 ①（非阻塞）**：`design.md:234`（§7「已确认决策」）仍写「兜底落 **`cli.main` guard 分支**」——与 D3（入口）**直接矛盾**；紧邻的 `design.md:238` 又写「CD3 … **R5 起升级为『彻底关闭』**：兜底前移到进程入口」⇒ **§7 内部自相矛盾**。属「声明与实况不符」，但**不导致实现/测试失败、非 spec over-claim** ⇒ **不阻塞**。
- **残留 ②（非阻塞）**：`design.md:155`（D8）「加注释声明不变量：『**`cli.main` 的 guard 分支及之后**，1 只由 `return C.EXIT_FAIL` 产生』」——D3 已**移除** `cli.main` 里的 guard 兜底分支，此措辞**所指的「分支」已不存在**（易被读成「去 `cli.main` 加分支」）。
- **对照**：R3/R4 点名的两处 over-claim（`spec.md` 旧 Scenario「guard 点名该文件」、`design.md` 旧 §5「清单无法解码」）**已消**——`grep` 在 `spec.md`/`tasks.md` 无「guard 点名该文件」「清单无法解码」残留。✅

### 5. 甲案（Q1）是否一致落地 → **是（实测）**

- **报告读点 ⇒ 拦**：`spec.md:55` + `design.md:108-109`（D4-3）+ `tasks.md:39`（C5）一致；实测字节坏报告 ⇒ `guard` 退 **1** + 「报告无法解码：…」、无 traceback。
- **manifest 读点 ⇒ 与 JSON 坏/缺失同归（拦 / 红）**：`spec.md:53-54` + `design.md:97-107`（D4-2）+ `tasks.md:35-38`（C3/C4）一致；实测 **字节坏** 与 **JSON 坏** manifest 的 `guard` 结论**逐字相同**（皆退 1、文案「无 stage=grill 的 manifest（现有 stage：（无））」）；`check` 侧字节坏 manifest ⇒ **干净红（退 1）且 finding 点名该文件**（`…/grill.manifest.json：manifest 无法解析：…`）、无 traceback。
- **policy ⇒ 放**：`spec.md:52` + `design.md:130-132`（D5）+ `tasks.md:33-34`（C1/C2）一致；实测字节坏 policy ⇒ `guard` 退 **0**（放行，文案「policy 非法（.witnessloop/policy.json 无法解析：…）——不拦」）。
- `grill-review.md:96-102` 的 `## User Confirmation` 已就位：**Q1=甲、Q2=修掉** —— 与 D3/D4 的定案一致。✅

## 阻塞项

**无。** 本轮未发现会让实现 / 测试失败、或使 spec over-claim 的硬问题。指派证伪的「argparse 前缀缩写 ⇒ 误拦」**经实测为假前提**。

## 非阻塞建议

1. **`design.md:234`**：把「兜底落 `cli.main` guard 分支」改为「兜底落**进程入口** `entry.py`」（消 §7 内部矛盾）。
2. **`design.md:155`**：D8 不变量措辞里「`cli.main` 的 guard 分支及之后」已随 D3 失效 ⇒ 改为「`entry.py` 的 guard 兜底之后」。
3. **补一条「`SystemExit` 不被吞」的测试**（当前 B 段 / `design.md §5` / `spec.md` 均**无**）：如 `entry.main(["--help"])` ⇒ `pytest.raises(SystemExit)` code 0、`entry.main(["bogus"])` ⇒ code 2。这是「`--help`/用法错误照常传播」这条**承重**性质（`design.md:81-82`、`ADR 0002:26`）**唯一**的机械保证；缺它则日后若有人把 `except Exception` 误改成 `except BaseException`，`--help` 会被吞成 1/4 而**无测试报警**。（性质与 R1 第 5 条同源：**写了但不可验证**。）
4. **`design.md:61-71` 的 D3 代码片段缺 `import sys`**（却用 `sys.stderr` / `sys.argv`）：与 R1 抓过的「示例不能直接落地」同类——若实现者**逐字照抄**且 except 分支触发，会 `NameError: sys` ⇒ 冒泡 ⇒ **exit 1 ⇒ 误拦复活**。建议片段补 `import sys` 或标注「省略 stdlib import」。（**设计正文本身正确**；仅示例片段不完整，故不阻塞。）
5. **`tests/conftest.py` 的 `cli` fixture 改走 `entry.main` 后**：`check`/`init`/`manifest` 用例里的**真崩溃**会被入口吞成**退出码 1** 而非 traceback ⇒ 测试失败时可诊断性下降（看到 exit 1 而非异常栈）。若接受该代价（换来 B 组走真实入口）则保留；否则可另留一个**直调 `cli.main`** 的 fixture 给非 guard 用例。
6. **可选**：在 D3 留一句「verb 判据**假设子命令是 argv 首词**」的约束（防日后顶层加全局选项使首词错位 ⇒ 误拦，见「逐条 1」末）。

## 我实测复现的

均在 `/tmp` 内（`/tmp/r5` = 按 D3/D4/D5 落补丁的**完整副本**；`/tmp/r5badc`、`/tmp/r5badcli` = 坏 `constants.py` / 坏 `cli.py`；`/tmp/orig` = 未打补丁副本对照），**未在仓库留文件、未 commit**；真 CLI 走 `python -m witnessloop`（`PYTHONPATH` 指副本 `src`，已验证**优先于** editable 安装）。

1. **基线 & 补丁全量**：本仓 `uv run pytest -q` ⇒ **388 passed**；补丁副本（`entry.py` + `constants.EXIT_INTERNAL` + `policy/evidence/contract` 补捕 + conftest 改 entry）⇒ **388 passed**。
2. **D3 覆盖 · 坏 `constants.py`**（`cli.py:15` 模块级 import 炸）：`python -m witnessloop <verb>` ⇒ `guard` **退 4**、`check`/`init`/`manifest` **各退 1**，stderr 一行「witnessloop：内部错误（RuntimeError: broken install）」。
3. **D3 覆盖 · 坏 `cli.py`**：`guard` **退 4**、`check` **退 1**。运行期异常（monkeypatch）⇒ `entry.main(["guard",…])`=**4**、`["check",…]`=**1**。
4. **`SystemExit` 传播**：真实入口 `--version`=**0**、`--help`=**0**、`bogus`=**2**。
5. **argparse 前缀缩写（证伪指派假设）**：`gu`/`guar`/`g`/`che`/`manifest bu` 全 → `invalid choice` ⇒ `SystemExit 2`；`--vers` → `SystemExit 0`（选项可缩写、子命令**不**可）；真实 wheel 上 `witnessloop gu` 同 ⇒ **2**。
6. **甲案三读点**：字节坏报告 ⇒ `guard` **1**「报告无法解码」、`check` **非 0**（含 `report_hash 不匹配` + 报告无法解码）、均无 traceback；字节坏 manifest ⇒ `guard` **1**，与 **JSON 坏** manifest 输出**逐字相同**；`check` 侧字节坏 manifest ⇒ **干净红 + 点名文件**（`…/grill.manifest.json：manifest 无法解析：…`）；字节坏 policy ⇒ `guard` **0**（放行）。
7. **打包 / CI**：`uv build` 成功；`uvx --from dist/*.whl witnessloop --version` ⇒ **0** / `witnessloop 0.1.0`；未接入仓 `guard` ⇒ **3**（原 / 补丁 wheel 同值）。
8. **常量守卫就绪**：`entry._EXIT_INTERNAL == C.EXIT_INTERNAL == 4`（补丁副本断言通过）。
9. **残留 grep**：`design.md:234`「兜底落 `cli.main` guard 分支」、`design.md:155`「`cli.main` 的 guard 分支及之后」命中（见非阻塞 1/2）；`spec.md`/`tasks.md` 无「guard 点名该文件」「清单无法解码」残留。
