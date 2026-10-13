# building-review（实现阶段独立审阅 · 第 1 轮）

> 算法与产物格式出处：`templates/review-loop.md`。**零记忆独立 run**：不继承作者的开发上下文。
> 被审 change：`adopter-test-gate`（issue #4）。被审 revision：**`79c8d5f`**（`79c8d5f51d82ecf64b5f9c0768bf6065ba4d947b`）。
> base：`origin/main` = `de51a01adcfadc409af0a4c3b7545f38ef9f2aee`（`git merge-base HEAD origin/main` 同值）。
> 被审 worktree **只读**；唯一仓内写入 = 本文件（`reviews/building-review.md`）。

## Reviewer

- run id: `building-reviewer-adopter-test-gate-79c8d5f51d82`（未设 `WITNESSLOOP_RUN_ID` ⇒ 走模板「怎么取 run id」的确定性兜底形态）
- 时间: 2026-10-13（本地）
- 方法（可复现）：
  - 副本 `/tmp/wlrev/repo`：`cp -a` 后 `rm -f .git && git init -q -b main && git add -A && git commit`，再 `rm -rf .venv && uv sync`。基线 **477 passed in 24.95s**。
  - 变异副本 `/tmp/wlrev/mut`（同法重建 venv）。⚠️ **踩到并记录一个陷阱**：只 `cp -a` 而不 `rm -rf .venv` 时，复制过来的 `.venv/bin/pytest` 的 shebang 仍指向**源副本**的 python ⇒ 变异**静默不生效**（第一轮 13 passed 是假象）。`rm -rf .venv && uv sync` 后复查 shebang = 本副本，变异才真正落地。**本报告的所有变异结论都取自重建 venv 之后**。
  - 门禁那一步：从 `gate.yml` **解析出 `run:` 原文**后交真 `sh -c`（脚本 `/tmp/wlrev/run.sh`，env 两变量照抄 `env:`），逐态跑退出码。
  - 真 CLI 端到端：`/tmp/wlrev/e2e`（真 git 仓，非测试进程内），CLI 用 `uv run --project <未变异的副本> witnessloop`。
  - 真 `check`：`git clone` 带历史副本 `/tmp/wlrev/full`，检 `origin/main...79c8d5f`。

## Verdict

**PASS**

所有 `[x]` 都有读得到、跑得着的真实实现（逐条见下）；spec 六条 Requirement 与四条诚实边界都落到了实现、测试与文档；全量 **477 passed**（基线一致），无既有限定被放宽（逐条看 diff：`tests/` 侧**被删掉的断言只有 5 行**，其中 3 行是 spec 强制要求的契约变更，2 行是接线）；`.github/workflows/gate.yml` 的改动**零删除**、无 `continue-on-error`、无 `xfail/skip`。

**阻塞项：无。** 发现 3 处「变异存活」的**测试强度缺口**（实现本身正确）+ 4 条非阻塞观察，逐条见 `## Issues`。按 verdict 判定规则（只有「会让实现出错或与 spec 不一致」才算阻塞），这些都不构成 `CHANGES_REQUESTED`。

## Task Verification（逐项）

> 记法：**声称** → 证据（`文件:行号`）→ 结论。行号一律指 `79c8d5f` 的树。

### A. `check` 的机械判定

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| A1 | `constants.py`：命令文件路径 + 哨兵串 | `src/witnessloop/constants.py:27`（`ADOPTER_TESTS_PATH = ".github/witnessloop-tests.txt"`）、`:32`（`ADOPTER_TESTS_SENTINEL = "<<REPLACE-ME>>"`） | **成立** |
| A2 | `policy.py`：缺省 ⇒ 声明；`tests.disabled: true` ⇒ 不判；**订正字段名**（无 `execution_point` 路径旋钮） | `src/witnessloop/policy.py:70`（字段）、`:101-103`（`tests` 必须为对象，否则 `PolicyError`）、`:144`（`tests_disabled=tests.get("disabled") is True`，刻意**不**用 truthiness）；`default_policy_doc()`（`:30-52`）**无 `tests` 键**。字段名一致性：全库 `grep -rn execution_point` 只剩 `tasks.md:13` 的**订正说明**与 `reviews/`（历史记录）、测试函数名 —— `spec.md` / `design.md` / `README.md` / `docs/gate.md` **零命中**，**没有留下不一致的措辞** | **成立** |
| A3 | `checkcmd.py` 三条判据、零依赖 | `src/witnessloop/checkcmd.py:119-166`：`:129-132` disabled ⇒ `[]`；`:136-143` 不存在 ⇒ 红（点名路径）；`:151-157` 去空白为空 ⇒ 红；`:158-165` 含哨兵 ⇒ 红。**不解析 YAML、不执行命令**（无 `subprocess`/`yaml` import） | **成立** |
| A4 | 单测四态 + 未声明 ⇒ 不判 + 文案点名路径与原因 | `tests/test_adopter_tests.py:38`（已接线绿，对照组）、`:46-53`（缺失：`TESTS in err` + `"不存在" in err`）、`:57-65`（空/纯空白 ×3：`"为空"`）、`:68-75`（哨兵）、`:78-89`（哨兵在行中间——子串口径）、`:120-131`（`--no-tests` ⇒ 不判） | **成立** |
| A5 | `check` **不执行**命令 | `tests/test_adopter_tests.py:153-164`：命令文件写 `touch <仓外 marker>`，`check` 后断言 `not marker.exists()`。真跑：marker 未生成 ⇒ **命令确实没跑** | **成立** |

### B. `init` 侧

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| B1 | 无 flag ⇒ **不存在才写**、走**独立路径**、**不进 `desired_files()`**；`--dry-run`/清单单独加一行且**只列真会写**的 | `src/witnessloop/initcmd.py:195-203`（`tests_write` 三态）、`:242-243`（dry-run 只列真会写）、`:257-259`（清单）；`desired_files()`（`:50-55`）**不含**该文件。测试：`tests/test_init_tests_command.py:184-186`、`:224-241`。真跑：未接入仓 `init --dry-run` 列出该文件；文件已在 ⇒ **不列**且 `git status` 干净 | **成立** |
| B2 | `--test-command` ⇒ **总是覆盖**（X1 的回归） | `initcmd.py:198-199`（`tests_command is not None` ⇒ 无条件写）；测试 `test_init_tests_command.py:49-57`（哨兵 ⇒ 覆盖）、`:60-67`（手改过 ⇒ 覆盖）。真跑：plain `init`（哨兵）后再 `--test-command` ⇒ 文件变成 `uv run pytest -q`，exit 0 | **成立** |
| B3 | `--no-tests` ⇒ 不写文件 + 策略写**布尔** `tests.disabled: true` | `initcmd.py:179-186`（写 `{"disabled": True}`）、`:196-197`（不写文件）；`cli.py:56-70`（两 flag **互斥**，argparse 退 2）。真跑：`--no-tests` ⇒ 无文件 + `policy['tests'] == {'disabled': True}` + `check` 通过 ✓ | **成立** |
| B4 | 契约变更进 spec + 改既有断言 | `docs/gate.md:9`（「写**三个台账产物**…**外加一份命令文件**」）；`tests/test_init.py:21`（原名 `test_init_creates_three_files` ⇒ `test_init_creates_the_expected_files`，并**新增**第四个文件的断言） | **成立** |
| B4b | 覆盖分支**不得**说「幂等，无改动」、退出码仍 0；plain 且已存在才是「幂等」 | `initcmd.py:206-221`（覆盖分支给 `note`）、`:353-356`（`note` 非空 ⇒ 不打印「幂等」）。两条断言：`test_init_tests_command.py:72-82`（覆盖：`"幂等" not in out`）、`:100-109`（对照分支：`"幂等" in out`）。真跑输出逐字核对：覆盖 ⇒「已写入测试执行点…（--test-command 覆盖已有内容）」+「其余文件无改动，未 commit」 | **成立** |
| B5 | 三态 + 幂等 + `uninit` 后文件仍在 + **改命令后 plain `init` 仍 exit 0** | `test_init_tests_command.py:36`（无 flag ⇒ 哨兵）、`:43`（有 flag）、`:135-140`（`--no-tests`）、`:189-192`（不在台账）、`:211-219`（`uninit` 后仍在）、**`:195-208`（改命令后 plain `init` exit 0 且不覆盖）**。真跑复现：手工改成 `uv run pytest -x` 后 plain `init` ⇒「幂等，无改动」exit 0，内容未被改回 | **成立** |
| B6 | 不许改 `caller_workflow()` 的字节 | `tests/test_init_tests_command.py:246-268`（golden literal 逐字节）；`git diff` 里 `initcmd.py:30-47` **不在改动面内** | **成立** |

### C. `gate.yml` 新增步骤

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| C1 | 文件缺失 **_或_** 含哨兵 ⇒ 跳过 | `.github/workflows/gate.yml:85-88`（缺失 ⇒ notice + exit 0）、`:90-95`（哨兵子串 ⇒ notice + exit 0）。**真 shell 实跑**（四态见 `## 变异验证` 的表）：缺失 ⇒ exit 0 + notice；哨兵 ⇒ exit 0 + notice；**空 ⇒ exit 0 且无 notice**（正如 spec 所说，这一态只能由 `check` 判） | **成立** |
| C2 | 路径经 `env:`、命令运行时读；断言主语是**路径** | `gate.yml:81-83`（`env:` 两变量）、`:89`（`CMD=$(cat "$WL_TESTS_FILE")`）、`:96`（`sh -c "$CMD"`）；`run:` 里**零 `${{ }}`**。测试 `tests/test_gate_workflow.py:89-101`（断言 `env["WL_TESTS_FILE"] == C.ADOPTER_TESTS_PATH`、`"${{" not in run`） | **成立** |
| C3 | `!cancelled()` + `check` 步骤在前 | `gate.yml:79-80`（`- name: adopter tests` / `if: ${{ !cancelled() }}`）；测试 `test_gate_workflow.py:117-130`（`check_index < tests_index` **且** `if` 逐字等于 `${{ !cancelled() }}`）。理由已按实测改写（`always()` 掩蔽为假）并写进 `gate.yml:65-73` 的注释 | **成立** |
| C4 | pyyaml 结构化断言 + 既有断言全绿 + **三处同源**的一致性测试 | `test_gate_workflow.py:81-87`（同 job）、`:89-101`（env/无插值）、`:104-114`（跳过分支）、`:117-130`（顺序 + `if`）、`:133-137`（job 名）、`:140-156`（同源）。同源是否真能「改一处就红」：**变异实测 M7/M8a/M8b 全红**（见下） | **成立** |
| C5 | `gate / check` 的 job 名不变 | `test_gate_workflow.py:133-137`（`list(jobs) == ["check"]` **且** caller 里 `\n  gate:\n` 仍在）；`gate.yml` 的 `jobs:` 块未被改 | **成立** |

### N / E / H / F / P

| # | 声称 | 核到的证据 | 结论 |
|---|---|---|---|
| N1 | 依赖为空要有测试钉住 | `tests/test_invariants.py:140-151`（切出 `[project]` 表断言 `dependencies = []`） | **成立** |
| N2 | 文档守卫（±2 行范式 / 禁教法 / 四条边界关键词） | `tests/test_docs.py:164-217`：三条守卫（四关键词 `:170-186`、`MERGE_CLAIM_PHRASES` ±2 行 `:189-207`、禁「手改 `init` 产物」「先 `uninit` 再 `init`」`:209-217`）。实核：`不保证/可以改/fork/天花板` 在 `README.md` 与 `docs/gate.md` **各自都有** | **成立** |
| N3 | 写清「`tests.disabled: true` 只关 `check`，门禁照旧」 | `README.md:88-93`（「opt-out 的语义（第五条说明）」）、`docs/gate.md:493-495`（§11.2 末条） | **成立** |
| N4 | `README.md:66` 的「尚未随 `@v1` 发布」已订正 | `README.md:109-111`：改成「自 **`v1.6.0`** 起随 `@v1` 发布（`@v1` 是滚动大版本）」 | **成立** |
| E1 | 全量绿 + 基线/新增数 | 副本实跑 **477 passed in 24.95s**（任务书写基线 431 ⇒ 新增 46；与 `tasks.md:150-152` 的 13+19+6+7+1 分解一致：`test_adopter_tests.py` 13、`test_init_tests_command.py` 19、`test_gate_workflow.py` +6、`test_docs.py` +7、`test_invariants.py` +1） | **成立** |
| E2 | `init`/`uninit` 既有幂等/冲突/回滚全绿 + 「三文件」表述已改 | 477 passed 覆盖；`docs/gate.md:9` 已改（见 B4）。`uninitcmd.py` **未动**（`git diff --name-only` 零命中） | **成立** |
| E3 | `check`/`guard` 既有判定不回归 | 全量绿；`checkcmd.run` 只在 `:111` **追加**一行 findings，`_code_hits`/`_require_change`/`_protected_writes`/`contract.*` 未改 | **成立** |
| H(E2a) | v1 两份报告移到 `history/v1/`（`git mv`） | `git ls-tree -r 79c8d5f -- …/history` 有 3 份；`reviews/` 下只剩 v2 的 `grill-review.md` / `grill-adversarial.md`（+ 未跟踪的 manifest） | **成立** |
| H(E2b) | 本轮 grill 落 `reviews/grill-review.md`，`stage=grill` 的 manifest 指向它 | `reviews/grill.manifest.json` 的 `stage="grill"`、`report_path="reviews/grill-review.md"`。⚠️ 该文件**未跟踪且已 stale**（真 `check` 实测：`report_hash 不匹配` + `tasks_hash 不匹配` + `审阅的是旧 revision`）——**属预期的 G1 中间态**，不是缺陷 | **成立**（证据待 G1 重建） |
| F1 | README 接入段 + **四条边界** | `README.md:54-93`：接入段（`--test-command` / 怎么改命令 / 同 job ⇒ 不用新增勾选）**逐条**列出四条边界（`:76/:78/:80/:82`），且承诺句带限定（`:57-58`「测试失败 = 合不了（⚠️ **不保证**它真跑过…）」） | **成立** |
| F2 | `docs/gate.md` §1 产物清单 + 新增一小节 | `docs/gate.md:9-31`（§1 第四个产物 + 双重身份 + 写入语义 + 代价）、`:444-508`（§11，含 11.1 判据表 / 11.2 策略语义 / 11.3 四条边界）；退出码表 `:294` 已加「测试执行点缺失、为空或未接线（§11）」 | **成立** |
| F3 | `templates/review-loop.md` 补「测试须由 CI 执行」 | `templates/review-loop.md:33-35` | **成立** |
| F4 | 不动其它 change 目录的非证据文件 | `git diff --name-only origin/main...HEAD \| grep '^openspec/'` ⇒ 只有 `openspec/changes/adopter-test-gate/**` | **成立** |
| P0 | 本仓先补执行点（手工提交） | `.github/witnessloop-tests.txt` 内容 `uv run pytest -q`，**在 `79c8d5f` 里**（`git log -1 -- <file>` = `79c8d5f`）。design D7 的顺序要求（先补文件 → 再发/移 tag）满足 | **成立** |
| P1–P4 | 发 tag / 移 tag / 复核 / 文档 | 均未勾选 | **未到期**（需用户在场，符合 task 约束 7） |
| P5 | 放弃把 `ci.yml` 的 `test` 勾 required | `tasks.md:84-86` 已划掉并写明理由 | **成立** |
| G0–G4 | 证据链与收尾 | 未勾选 | **未到期**（G1 的 manifest 待建；本报告即 G2 的输入） |

### 关于 spec 的六条 Requirement（对齐面）

①执行点写入 → B1/B2/B3/B4/B4b ✅；②`check` 三判据 → A1–A5 ✅；③门禁执行 + 同 job + `env:`/运行时读 + 跳过条件 → C1–C5 ✅；④诚实边界（四条 + 文档守卫 Scenario）→ F1/F2/N2，且 `README.md:76-85` 与 `docs/gate.md:501-508` 逐条同口径 ✅；⑤零依赖 → `policy.py`/`checkcmd.py` 无新 import + N1 ✅；⑥产物契约 → B4/E2 + `docs/gate.md` 命令文件标注「不参与 `uninit` 删除」✅。**未发现「只有 spec 没有实现」或反之。**

## 第 2 条的独立判断：`uninit` 三处断言改语义，是契约必然还是「为了让测试变绿」

**结论：是 spec 的必然结果，不是放宽；而且是「改得更死」而不是「改松」。**

- 依据（spec 侧）：`specs/adopter-test-job/spec.md:21-22` 逐字写「该命令文件 … SHALL **不参与 `uninit` 的删除**」；`:125-126`（Requirement「产物契约变更」）再写一次「`uninit` SHALL **不删**命令文件」。⇒ 文件由 `init` 创建、而 `uninit` **被要求不删它** ⇒ 「往返后工作树逐字节回到 init 前」这条旧断言**与 spec 直接矛盾**，**必须**改。这不是作者的便利选择。
- 依据（机制侧）：`uninitcmd.py:42` 只遍历 `init-manifest.json` 的 `created_files`，而该文件**不进台账**（`tests/test_init_tests_command.py:189-192` 实断）⇒ 不看代码也能推出「删不掉」。作者**没有**为了让测试绿去改 `uninitcmd.py`（`git diff --name-only` 零命中）——这是关键：如果动机是「变绿」，最省事的路正是去 `uninitcmd` 里加一句 `unlink`。
- 依据（强度侧）：三处断言**都从「相等」改成「精确等于一个已知残留」**：`tests/test_uninit.py:58` 与 `tests/test_acceptance.py:107` 一律用 `git status --porcelain -uall` 断言**恰好等于** `?? .github/witnessloop-tests.txt\n`（`-uall` 是作者踩过「git 把未跟踪目录折叠成 `.github/`」之后加的），并**另加**更强的一条：`tests/test_uninit.py:42-44` 断言该文件内容仍是哨兵、`tests/test_init_tests_command.py:211-219` 断言 `uninit` 后文件与台账状态。旧的 `== before`（before 恒为空串）**更弱**——它对「`.github/` 之外的任何新残留」都无感。
- 唯一「变窄」的地方（如实记录）：`test_uninit_removes_exactly_what_init_created` 原先断言 `.github/` **整个**消失，现在改断 `.github/workflows` 消失、`.github/` 仍在（因为命令文件在里面）。这正是同一契约变更的另一面，`tests/test_uninit.py:38` 的注释写明了。
- 我的判断：**成立**。残留本身是**被声明出的代价**（`docs/gate.md:26` 明写「代价（刻意接受）：`uninit` 往返不再逐字节干净…不要它就自己删」），不是被掩盖的缺陷。

## Issues

> 均为**非阻塞**（实现正确、与 spec 一致）。按「是否会让实现出错」判，无一条达到 `CHANGES_REQUESTED` 的门槛。

**I1（测试强度 · 中）｜`gate.yml` 那一步的用例是**文本**断言，语义回归会逃逸。**
`tests/test_gate_workflow.py:104-114` 用 `assert '-f "$WL_TESTS_FILE"' in run` / `assert '"$WL_TESTS_SENTINEL"' in run` / `assert "exit 0" in run` 钉行为。**复现（变异 M2b/M2c，均在 `/tmp/wlrev/mut`）**：① 保留 `case` 分支、只删掉它内部的 `exit 0`（哨兵会**落到** `sh -c "$CMD"` ⇒ 门禁跑哨兵、`sh: Syntax error`、exit 2）⇒ **477 passed，零变红**；② 把 `sh -c "$CMD"` 挪到 `case` **之前**（未接线仓的门禁步骤也去执行哨兵）⇒ **477 passed，零变红**。当前实现**是对的**（真 shell 实跑四态见下表），缺口在「没人守着它不被改回去」。最小修法：在用例里把 `run:` 交 `subprocess.run(["sh","-c",run], env=…)` 跑一遍，断言「哨兵态 exit 0 且 stdout 含 `::notice::`」「已接线态 exit 7 ⇒ returncode 7」。**这同时是本仓执行点要走的那段 shell**，值得一条真执行的用例。

**I2（测试强度 · 中低）｜「唯一的 opt-out 字面是布尔真」没有钉满。**
`src/witnessloop/policy.py:144` 刻意用 `is True`；`tests/test_adopter_tests.py:103-113` 列了 `""`/`None`/`False`/缺省 四类 falsy。**复现（变异 M4）**：把 `is True` 改成 `bool(tests.get("disabled"))` ⇒ **477 passed，零变红**——因为被覆盖的值全是 falsy，两种写法同结果。差异出现在**真值但非布尔**的输入：`{"tests":{"disabled":1}}` 或 `"disabled":"true"` 下，`is True` ⇒ 「声明、要继续判」（= spec 要的），`bool()` ⇒ 「opt-out」（= 违约）。最小修法：`test_adopter_tests.py:103` 那条用例补 `assert Policy.from_doc({"tests": {"disabled": 1}}).tests_disabled is False` 与 `"true"` 一条。

**I3（健壮性 · 低）｜CRLF：`check` 绿而门禁红（fail-closed，但症状与「接线」无关）。**
**复现**（`/tmp/wlrev/crlf`，真 CLI + 真 `sh`）：文件写 `uv run pytest -q\r\n` ⇒ `check` **通过 ✓（exit 0）**；门禁那一步 `CMD=$(cat …)` 得到 `…-q\r` ⇒ `sh -c` 交给 pytest ⇒ `pytest: error: unrecognized arguments:` ⇒ **exit 4**。实测：`$(cat)` 只吃行尾 `\n`，**`\r` 留在命令尾**。⇒ Windows 编辑器改过该文件的接入方会看到一条与「接线」无关的红。⚠️ **独立订正上游**：对抗轮 N5 建议「`check` 顺带把 `\r` 归到空白里」**修不了这一条**——`checkcmd.py:151` 的 `content.strip()` **本来就吃 `\r`**（Python 的 `str.strip()` 含 `\r`），问题在**门禁侧**把 `\r` 交给了 `sh`。可行修法：门禁改 `CMD=$(tr -d '\r' < "$WL_TESTS_FILE")`（或 `init` 侧写盘归一 + 文档提示）。**不阻塞**：它从不静默放行，且 spec 未涉及行尾。

**I4（观察 · 低）｜第三条判据只堵「意外空文件」，堵不住「只有注释 / `true` / `:`」。**
**复现**（真 CLI + 真 `sh`）：文件内容 `# TODO: 接线\n` ⇒ `check` **通过 ✓**，门禁 `sh -c "# TODO: 接线"` ⇒ **exit 0**。⇒「有执行点、门禁跑了、required 绿、零测试」，与空文件是同一张脸，只是触发条件是「有人写了个占位注释」。**判为可接受**：spec 只定义三条判据且明令**零依赖**（不解析、不执行），这属 `spec.md:98-99` 的诚实边界 ①（`|| true`/`--collect-only`）同一类。建议（非必须）：把 `#` 开头与 `true` 也写进边界 ① 的举例（`README.md:76-77` / `docs/gate.md:501-503` 现在只举了 `|| true` 与 `--collect-only`）。

**I5（观察 · 低）｜失败的 `init` 会留下写入副作用（已在 tasks 里认下，但无断言钉住）。**
`src/witnessloop/initcmd.py:207-222`：已接入仓上「`--test-command` 覆盖」写在 `_already_initialized` 的冲突判定**之前**且**不回滚** ⇒ `init --test-command X --policy <不同>` 会**先覆盖命令文件、再 exit 1**。`tests/test_init_tests_command.py:112-130` 只断 `exit == EXIT_FAIL` 与 `"冲突" in err`，**没断文件已被覆盖**。作者已在 `tasks.md:180-182`（踩到的坑 #5）与 Z1/O2 里认下「写在前、不因后续冲突回滚、当场打印点名那一行」。⇒ 行为已文档化，非缺陷；建议顺手补一条断言把它钉成契约（否则将来谁把写入挪到判定之后，没人会发现行为变了）。

**I6（措辞 nit）｜三处措辞比实现强。**
① `specs/adopter-test-job/spec.md:9`「（默认 `.github/witnessloop-tests.txt`）」——实现里这个路径**没有第二个取值**（是 `constants.py:27` 的常量，policy 无路径旋钮），「默认」二字是旧 `execution_point` 旋钮的残留；② `tests/test_init_tests_command.py:143-147` 的 docstring 与 `README.md:89-90`「`--no-tests` 只在**新接入**时可用」——实测：**已**在 `tests.disabled: true` 状态下的仓再跑 `--no-tests` 是**幂等 exit 0**（`/tmp/wlrev/e2e2` 实跑），只有「从默认 policy 的已接入仓切到 opt-out」才会冲突；③ `README.md:23-26` 把三条 `init`（`--dry-run` / `--test-command` / plain / `--no-tests`）并排放在**同一个代码块**里，读起来像要顺序执行（它们是**互斥的替代**）。

**I7（环境差异 · 无需动作）｜`tasks.md:208-210` 的「现在跑是 3 项红」是**作者本机脏工作区**的数。**
我在**干净克隆**（`/tmp/wlrev/full`，检 `79c8d5f`）实跑真 `check`：无 manifest ⇒ **4 项红**（缺 manifest / 缺 grill / 缺 grill-adversarial / 缺 building）；把那份未跟踪的 `grill.manifest.json` 放进树后再跑 ⇒ **6 项红**（+`report_hash 不匹配` / +`tasks_hash 不匹配` / +`审阅的是旧 revision` / +孤儿）。**两种都印证同一结论**：**没有一条是执行点判定**（本仓 `.github/witnessloop-tests.txt` 已接线，该判据绿）⇒ task 约束 7 成立，属预期中间态。

## 变异验证

在 `/tmp/wlrev/mut`（`cp -a` + `rm -f .git && git init` + **`rm -rf .venv && uv sync`**）逐条应用、跑全量、`git checkout -- .` 还原。**11 个变异体，8 个被抓住、3 个逃逸**。

| # | 变异 | 期望 | 实测 |
|---|---|---|---|
| **M1** | `checkcmd.py` 删掉「去空白非空」判据 | 红 | ✅ **3 failed**（`test_empty_execution_point_is_rejected[ ]` ×3） |
| **M2** | `gate.yml` 整段删掉哨兵 `case` 分支 | 红 | ✅ **1 failed**（`test_adopter_tests_step_skips_when_missing_or_unwired`） |
| **M2b** | 保留 `case`、只删其内部 `exit 0` | 红 | ❌ **477 passed（逃逸 → I1）** |
| **M2c** | 把 `sh -c "$CMD"` 挪到哨兵 `case` **之前** | 红 | ❌ **477 passed（逃逸 → I1）** |
| **M3** | `--test-command` 改回「不存在才写」（X1 那个 bug） | 红 | ✅ **4 failed**（含 `..._overwrites_an_existing_sentinel`、`..._overwrites_a_hand_edited_command`） |
| **M4** | `policy.py`：`is True` ⇒ `bool(...)` | 红 | ❌ **477 passed（逃逸 → I2）** |
| **M5** | `default_policy_doc()` 物化 `tests` 键 | 红 | ✅ **2 failed** |
| **M6** | 把命令文件塞进 `desired_files()` | 红 | ✅ **11 failed**（含 `test_tests_file_is_not_in_desired_files` / `..._not_in_the_ledger` / X1 的三条） |
| **M7** | `gate.yml` 路径字面量改成 `.github/wl-tests.txt` | 红 | ✅ **5 failed**（三处同源真的钉住了） |
| **M8a** | `constants.ADOPTER_TESTS_PATH` 改值 | 红 | ✅ **2 failed** |
| **M8b** | `constants.ADOPTER_TESTS_SENTINEL` 改值 | 红 | ✅ **1 failed** |
| **M9** | `checkcmd.py` 删掉「文件缺失」判据 | 红 | ✅ **1 failed** |

**门禁那一步的真 shell 四态（+4 个边界态）** —— 从 `gate.yml:84-96` 取出 `run:` 原文交真 `sh`：

| 文件状态 | 实测 | 与 spec 一致？ |
|---|---|---|
| 缺失 | `::notice::没有测试执行点…` / **exit 0** | ✅ |
| `<<REPLACE-ME>>` | `::notice::测试执行点未接线（仍是哨兵），跳过。` / **exit 0** | ✅ |
| 空（0 字节） | 无任何输出 / **exit 0** | ✅（「空」只能由 `check` 判） |
| 纯空白 `   \n\n` | 无输出 / **exit 0** | ✅ |
| 已接线 `exit 7` | **exit 7**（会顶到 job） | ✅ |
| 已接线 `touch <marker>` | 命令**真的执行**（marker 生成） | ✅ |
| `<<REPLACE-ME>>\r\n` | 仍命中 ⇒ notice / exit 0（与 `check` 同口径） | ✅ |
| `echo REPLACE-ME-ok`（子串不含 `<<>>`） | 不跳过、**正常执行** | ✅（N5 前半的双侧分裂已消解：两侧都取 `constants` 的**同一个全串**） |

**真 CLI 端到端**（`/tmp/wlrev/e2e`·`/e2e2`，真仓）：plain `init` ⇒ 清单含 `+ .github/witnessloop-tests.txt`（内容 `<<REPLACE-ME>>`）、`check` 红并点名路径 + 「未接线（仍是哨兵）」；`--test-command` ⇒ 覆盖 + **不说「幂等」** + exit 0；再 plain `init` ⇒ 「幂等，无改动」exit 0；手改命令后 plain `init` ⇒ exit 0 且不覆盖（**D3 兑现**）；`--no-tests` ⇒ 无文件 + `tests={'disabled': True}` + `check` 通过 ✓；`uninit` ⇒ 三个台账产物删净、命令文件仍在；两 flag 互斥 ⇒ argparse **exit 2**。**全部与 spec 逐字一致。**

## Test Results

- 副本 `/tmp/wlrev/repo`（全新 venv）：**477 passed in 24.95s**（基线 431 ⇒ +46，与 `tasks.md:150-152` 一致）。
- 变异副本重建 venv 后同样 **477 passed**（未变异态）。
- 真 `check`：干净 `79c8d5f` ⇒ **4 项红（全是缺 manifest）**；叠上未跟踪 manifest ⇒ **6 项红**。**均不含执行点判定** ⇒ 属预期中间态。

## 结论

`PASS`。本批 A1–A5 / B1–B6+B4b / C1–C5 / N1–N4 / E1–E3 / H / F1–F4 / P0 全部有真实实现且可由测试/真 CLI/真 shell 复现；`.github/witnessloop-tests.txt`（P0）已在 `79c8d5f` 里；契约变更（第四个产物 + `uninit` 不删它）是 spec 明文要求，对应的三处断言语义变更**成立且更严**。P1–P4 / G0–G4 未到期。

---

## 简报（≤300 字）

**Verdict：PASS**（无阻塞项）。A–F/H/N/P 逐条读码 + 真 CLI + 真 shell 复核全部成立；477 passed 与基线一致；`gate.yml` 零删除、无 `continue-on-error`/`xfail`。**第 2 条独立判断：契约必然，不是改松**——`spec.md:21,126` 明文「`uninit` 不删命令文件」，`uninitcmd.py:42` 只遍历台账 ⇒ 旧断言「往返逐字节干净」与 spec 直接矛盾；作者没动 `uninitcmd.py`，三处改成 `-uall` 精确等于「只剩一个文件」，比原来更严。**11 个变异体：8 红 3 逃逸**（M2b/M2c 是 `gate.yml` 语义回归、M4 是「唯一 opt-out 字面」没钉满——实现正确，只是测试网眼）。非阻塞：CRLF 下 check 绿而门禁红（N5 修法方向错）、注释占位可绕过（属已声明边界 ①）。
