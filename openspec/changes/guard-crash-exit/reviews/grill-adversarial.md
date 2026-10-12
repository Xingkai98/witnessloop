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
