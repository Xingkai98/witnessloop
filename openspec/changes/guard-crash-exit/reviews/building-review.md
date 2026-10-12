# Building Review: guard-crash-exit

## Reviewer
- run id: building-reviewer-guard-crash-exit-2026-10-12
- 时间: 2026-10-12T00:57:24Z
- 方式: 零会话记忆、独立复核；每条 `文件:行号` 自验；关键性质做**变异检查**（改坏实现看测试是否真红，做完全部还原）
- 环境: `uv run pytest -q` → **402 passed**；`uv build` + `uvx --from wheel witnessloop --version` → `witnessloop 0.1.0`（CI 同款冒烟）

## Verdict
**PASS**

实现与 spec 对齐、测试基本为真（变异检查逐条见下），无阻塞性缺陷。两条**非阻塞**建议：
①生产接线（`pyproject` 的 console-script → `entry`）**没有任何测试钉住**——一行回退即静默失联而全绿；
②C6 的 `test_check_stays_fail_closed_on_an_undecodable_report` 是**弱测试**（改坏它声称覆盖的实现仍绿）。

## 任务逐项验证

- **A1**：✅ `tests/test_entry.py:25` `assert entry._EXIT_INTERNAL == C.EXIT_INTERNAL == LITERAL_INTERNAL` + `:26 != EXIT_FAIL`；变异 M1 红。
- **A2**：✅ `src/witnessloop/constants.py:88` `EXIT_INTERNAL = 4`（注释齐备）。
- **B1**：✅ `tests/test_guard.py:187`（monkeypatch `evidence.grill_evidence_findings_in_change` 抛 `RuntimeError` ⇒ 4）；变异 M1 红。
- **B2**：✅ `tests/test_guard.py:205`；**R3 M4 的 `delattr` 是承重的**——去掉它跑整份 `test_guard.py` ⇒ 该用例红（见「实测复现」）。
- **B3**：✅ `tests/test_entry.py:46`（`sys.modules["witnessloop.cli"]=None` + `delattr`）⇒ 4；变异 M1 红。
- **B4**：✅ `tests/test_entry.py:42`、`:72`（非 guard verb 崩溃 ⇒ 1）；变异 M9 红。
- **B5**：✅ `src/witnessloop/entry.py:27-41`——依赖自由（只 `import sys`）、`_EXIT_INTERNAL=4`、argv 判 verb。
- **B6**：✅ `pyproject.toml:12` `witnessloop = "witnessloop.entry:main"`；`src/witnessloop/__main__.py:3` `from witnessloop.entry import main`。
- **B7**：✅ `tests/conftest.py:15,52` fixture 走 `entry.main`；变异 M6（回退 `cli.main`）⇒ 崩溃用例红。
- **B8**：✅ `src/witnessloop/guardcmd.py:12-14` docstring 指「崩溃兜底在进程入口 `entry.py`」。
- **B9**：✅ `entry.py:12-13`、`guardcmd.py:12`、`constants.py:84-87` 均声明不变量。
- **B10**：✅ `tests/test_entry.py:25`（两处字面量同值守卫）；变异 M1 红。
- **B11**：✅ `tests/test_entry.py:54`（`--help`/`--version` ⇒ `SystemExit(0)`、`bogus` ⇒ `SystemExit(2)`）；变异 M8（改捕 `BaseException`）红。
- **C1**：✅ `src/witnessloop/policy.py:129` `except (OSError, ValueError) as exc: raise PolicyError(...)`（`UnicodeDecodeError ⊂ ValueError`）。
- **C2**：✅ `tests/test_guard.py:224`；变异 M4（回退 `json.JSONDecodeError`）红。
- **C3**：✅ `src/witnessloop/evidence.py:166` `except (OSError, ValueError)` ⇒ `return None`（与 JSON 坏/缺失**逐字同归**，未新造文案）；变异 M2 红。
- **C4**：✅ `tests/test_guard.py:235`（断言 byte 案输出 **==** json 案输出）；变异 M2 红（`4 != 1`）。
- **C5**：✅ `src/witnessloop/evidence.py:217-226` 甲案 finding「报告无法解码」；`tests/test_guard.py:255`；变异 M5 红。
- **C6**：⚠️ 用例存在（`tests/test_check_grill_evidence.py:74`）但**弱**——见 Issues #2，变异 M5/M5b 仍绿。
- **C7**：✅ `contract.py:177`（`_bound_report`）与 `:232`（`_validate_one`）均补 `ValueError`；变异 M3（`:232`）红、M7（`:177`）红——C8 同时钉住两处。
- **C8**：✅ `tests/test_check_grill_evidence.py:56`（退出码 + 点名 `grill.manifest.json` + **不含「内部错误」**）；变异 M3、M7 均红。
- **D1**：✅ `tests/test_guard.py:178`；变异（shim 兼映射 4）红。
- **D2**：✅ `tests/test_guard.py:157`（`EXIT_FAIL → 2` 回归）仍绿。
- **D3**：✅ `plugin/hooks/guard.sh` 与 `origin/main` **零 diff**（`git diff origin/main...HEAD -- plugin/` 为空）。
- **E1**：✅ `tests/test_guard.py:44,53,108,114`（拦=1 / 放=0 / 未接入=3 / skip）全绿。
- **E2**：✅ 直接调 `evidence.grill_evidence_findings_in_change`：`dogfood-bootstrap` / `grill-evidence-gate` **findings=0**（见「实测复现」）。
- **F1**：✅ `docs/gate.md:279` 加行 `| 4 | 内部错误…只有 guard 会用 4 |`。
- **F2**：✅ `docs/gate.md:337-343` 补「崩溃/内部错误 ⇒ 放行」+ 读点归一表。
- **F3**：✅ `README.md:35`、`docs/adr/0001-local-guard-hook.md:16` 漂移订正为「CLI 退 1（shim 映射成 CC 的 2）」。
- **F4**：✅ `docs/gate.md:345-348` 写明「对**接入方**是行为变更」（甲案）。
- **G0/G1/G2/G3**（本任务清单外，仅备注）：`tasks.md` 把 **G3（PR→合入→关 issue #9）标 `[x]`** 属**超前勾选**——当前仍在 feature 分支。G0 的产物（`grill*.manifest.json`）在场。

## 变异检查（每条新测试是否真能红）

| 测试 | 改坏处 | 结果 |
|---|---|---|
| `test_entry_internal_code_matches_the_documented_constant` | `entry._EXIT_INTERNAL = 4 → 1` | **红** ✅ |
| `test_guard_crash_through_the_entry_is_fail_open` | 同上 | **红** ✅ |
| `test_entry_closes_the_broken_cli_import_hole` | 同上 | **红** ✅ |
| `test_guard_survives_an_arbitrary_internal_error` | `_EXIT_INTERNAL=1` / fixture 回 `cli.main` | **红** ✅ |
| `test_guard_survives_a_broken_submodule_import` | `_EXIT_INTERNAL=1` | **红** ✅（`delattr` 去掉后整份文件跑亦红，证明 R3 M4 真） |
| `test_non_guard_crash_still_fails_closed` | `return _EXIT_INTERNAL`（泛化 4） | **红** ✅ |
| `test_broken_import_of_a_non_guard_verb_fails_closed` | 同上 | **红** ✅ |
| `test_entry_does_not_swallow_systemexit` | `except Exception → BaseException` | **红** ✅ |
| `test_policy_decode_failure_is_not_a_block` | `policy.py` 回 `json.JSONDecodeError` | **红** ✅（4 ≠ 0） |
| `test_byte_bad_manifest_matches_json_bad_manifest` | `evidence._read_json` 回 `json.JSONDecodeError` | **红** ✅（4 ≠ 1） |
| `test_report_decode_failure_blocks_with_a_clear_message` | 删 `evidence.py:217-226` 读点归一 | **红** ✅（4 ≠ 1） |
| `test_check_names_a_byte_bad_manifest_and_does_not_crash` | `contract.py:232` 回退 / `contract.py:177` 回退 | **红** ✅✅（两处都被钉） |
| `test_shim_allows_the_internal_error_code` | shim 兼映射 `4 → block` | **红** ✅ |
| `test_check_stays_fail_closed_on_an_undecodable_report` | 删 `evidence.py` 读点归一（M5/M5b） | **仍绿** ❌ **弱测试**（见 Issues #2） |

（全部变异已 `git checkout` 还原；收尾 `git status --porcelain` 干净。）

## Issues

- **[非阻塞] ① 生产接线未被任何测试钉住（最重要的一条）**。
  证据：把 `pyproject.toml:12` 回退成 `witnessloop = "witnessloop.cli:main"` ⇒ `uv run pytest -q` **仍 402 passed**。
  原因：`tests/conftest.py:15` 的 fixture 与 `tests/test_entry.py` 都**直接** `from witnessloop.entry import main`，
  绕过了 packaging；CI 冒烟（`ci.yml` 的 `uvx --from wheel witnessloop --version`）只验 `--version`，不碰兜底。
  ⇒ 任何一次把 `[project.scripts]` 改回 `cli.main` 的重构都会**静默拆掉 issue #9 的修复本体**，而全绿。
  建议修法：加一条断言 wiring 的用例（读 `pyproject.toml` 的 `[project.scripts].witnessloop == "witnessloop.entry:main"`，
  或对**装好的** console script 跑一次「坏 `constants.py` ⇒ guard 退 4」的端到端冒烟）。
- **[非阻塞] ② C6 用例是弱/不可证伪的**（`tests/test_check_grill_evidence.py:74`）。
  证据：删掉 `evidence.py:217-226`（它声称要覆盖的读点归一）后该用例**仍绿**——断言只有 `code != EXIT_PASS`，
  而该非 0 由 `contract._check_hashes` 的 **hash 不匹配**（测试里报告被改写、manifest 未重建）**或**入口兜底把崩溃
  转成 1 来保证，根本走不到 evidence 读点。它无法区分「干净的红」与「崩到入口兜底的 1」（C8 用 `"内部错误" not in err` 做到了，C6 没做）。
  ⇒ `check` 侧的「报告无法解码 ⇒ 干净红」**没有强测试钉住**（`guard` 侧有 `test_report_decode_failure_blocks_with_a_clear_message`）。
  影响有限（spec 对该 Scenario 只要求「非 0」，且该性质确实成立），故非阻塞。
  建议修法：像 C8 那样加断言——先写坏报告**再 `manifest build`**（让 `report_hash` 匹配），断言 stderr 含「报告无法解码」且不含「内部错误」。
- **[非阻塞] ③ `constants.py:87` 错别字**：`⇒ 那里用车字面量，` —— 多了个「车」（应为「用字面量」）。
- **[非阻塞] ④ 诚实边界的小残留**（`docs/gate.md:337-343`、`docs/adr/0002` 的「**绝不**退 1」「任何崩溃」）：
  在**已声明的**两个入口（console script / `python -m witnessloop`）下字面为真（已实测）。但存在字面反例：
  `python -m witnessloop.cli`（`src/witnessloop/cli.py:177` 的 `sys.exit(main())`）**绕过 entry**——若 `cli.main` 崩溃即退 1。
  该调用无任何调用方（shim 走 console script、`-m` 走 `__main__`），故不实用；亦非文档承诺的入口。另：`except Exception`
  不覆盖 `SystemExit(1)` / `BaseExceptionGroup`（今日代码路径**无** `sys.exit(1)`，grep 已确认）——均为**潜在**、非现行。
  建议：文档「任何崩溃」可加一句限定「经上述入口」。
- **[非阻塞] ⑤ 措辞**：`evidence.py:224` 的 finding 对 `OSError`（如权限）也写「报告无法解码（PermissionError）」，
  非解码错误时文案略偏。极小，可留。

## 实测复现

- 全量：`uv run pytest -q` ⇒ `402 passed`（基线 388 + 入口 6 + 读点/check 8，与 `tasks.md` 口径一致）。
- CI 冒烟：`uv build --out-dir /tmp/wl_dist` + `uvx --from /tmp/wl_dist/*.whl witnessloop --version` ⇒ `witnessloop 0.1.0`，exit 0。
- **头号修复端到端**（坏 `constants.py` 的安装破损，`/tmp/brokenpkg`）：
  - `PYTHONPATH=/tmp/brokenpkg python3 -m witnessloop guard --root /tmp --path src/x.py` ⇒ `内部错误（SyntaxError…）`，**exit 4**（fail-open）；
  - `… check --root /tmp --base main` ⇒ **exit 1**（fail-closed）；
  - 对照旧入口（`from witnessloop.cli import main`）会直接抛 ⇒ 退 1 ⇒ 被 shim 当 block（与 ADR 0002 一致）。
- **KeyboardInterrupt 走信号**（ADR 承重性质）：子进程 `raise KeyboardInterrupt` / SIGINT-self ⇒ `returncode=-2`（被信号杀，shell 见 130 ≠ 1）⇒ shim 放行。证实。
- **B2 的 `delattr` 承重性**：删 `delattr(witnessloop,"guardcmd")` 后跑**整份** `tests/test_guard.py` ⇒ 该用例**红**（`1 != 4`）；单独跑该用例则绿（`guardcmd` 尚未成为包属性）。与 R3 M4 描述一致。
- **wiring 缺口**：`pyproject.toml` 回退 `cli.main` ⇒ 全量 **402 passed**（弱覆盖，见 Issues #1）。
- **E2 回归**：`evidence.grill_evidence_findings_in_change` 对 `dogfood-bootstrap` / `grill-evidence-gate` ⇒ `findings=0`。
- 收尾：全部变异 `git checkout` 还原，`git status --porcelain` 干净（仅本报告为新增）。

---

# 第 2 轮（R2）

## Reviewer
- run id: building-reviewer-guard-crash-exit-2026-10-12-R2
- 时间: 2026-10-12（R2：收窄——仅复核修复 + 确认最终 revision）
- 方式: 零会话记忆、独立复核；**不信声明**，每条 `文件:行号` 自验；两条关键修复做**变异检查**（改坏实现看测试是否真红，做完全部还原）
- 环境: `uv run pytest -q` → **404 passed**；`uv build` + `uvx --from wheel witnessloop --version` → `witnessloop 0.1.0`（exit 0）

## Verdict
**PASS**（无阻塞项）

修复 **1–4 逐条到位**且经变异检查证真；**修复 5 实际未落地**（`evidence.py` 根本没被修复提交改动——见下），但其属 R1 已裁「极小、可留」的纯文案问题，不使任何测试失败、不造成 spec over-claim，故**不构成阻塞**。

## 逐条核验（R1 的 5 条非阻塞项）

| # | R1 issue | 状态 | 自验证据 |
|---|---|---|---|
| 1 | 生产接线无测试钉住 | ✅ **到位** | `tests/test_entry.py:28` `test_production_wiring_points_at_the_entry_guard`（断言 `pyproject` 含 `witnessloop.entry:main`、不含 `cli:main`，且 `__main__.py` 走 entry）+ `tests/test_entry.py:41` `test_test_harness_goes_through_the_real_entry`（断言 `conftest.py` 走 entry）。两条**均非假测试**（变异 M1/M3 真红）。 |
| 2 | C6 弱测试 | ✅ **到位** | `tests/test_check_grill_evidence.py:74`：先写坏字节报告、再 `manifest build` 重建（让 `report_hash` 匹配、**越过** `contract._check_hashes`），才断言 `"报告无法解码" in err`（`:109`）且 `"内部错误" not in err`（`:110`）——真正打到 `evidence.py:217` 读点。变异 M2 证真。 |
| 3 | `constants.py` 错别字 | ✅ **到位** | `src/witnessloop/constants.py:86` 现为「…⇒ 那里**用字面量**，」（「车」已删；`grep 用车` 无命中）。 |
| 4 | `gate.md` 诚实边界 | ✅ **到位** | `docs/gate.md:287` 补「**该保证只对两个声明入口成立**（console script 与 `python -m witnessloop`）——直接跑 `python -m witnessloop.cli` 绕开兜底，不属承诺入口」。 |
| 5 | `evidence.py` 文案按成因分 | ❌ **未落地** | `src/witnessloop/evidence.py:224` 仍是 `f"报告无法解码（{type(exc).__name__}）：无法核验 grill 证据"`——`OSError`（如 `PermissionError`）与 `UnicodeDecodeError` **共用同一句**，未「按成因分『无法解码 / 无法读取』」。`git diff 25e90f3 3e92691 -- src/witnessloop/evidence.py` **为空**（该文件最后一次改动在 `25e90f3`，`3e92691` 未碰它）；`grep -rn "无法读取\|按成因" docs/ openspec/ src/` 全无命中。⚠️ 而 `3e92691` 的提交信息自称「文案按成因分（解码失败 vs 读不到）」——**该声明与实际不符**。 |

## 变异检查（重点：两条关键修复能否被变异打红）

| 变异 | 操作 | 针对用例 | 结果 |
|---|---|---|---|
| **M1** | `pyproject.toml:12` 回退 `witnessloop = "witnessloop.cli:main"` | `test_production_wiring_points_at_the_entry_guard` | **红** ✅（`assert 'witnessloop = "witnessloop.entry:main"' in pyproject` 失败）。已还原。 |
| **M2** | `evidence.py:219` `except (OSError, UnicodeDecodeError)` → `except OSError`（拿掉 `UnicodeDecodeError` 归一） | `test_check_stays_fail_closed_on_an_undecodable_report` | **红** ✅（异常冒到入口兜底，stderr 变 `内部错误（UnicodeDecodeError…）`，`:109` 的 `"报告无法解码" in err` 失败——正是 R1 指出的「弱测试两种非 0 均可满足」的分歧点）。已还原。 |
| M3（附加） | `tests/conftest.py:15` `from witnessloop.entry import main` → `witnessloop.cli` | `test_test_harness_goes_through_the_real_entry` | **红** ✅。已还原。 |

- 对照 R1：旧版 C6 只断言 `code != EXIT_PASS`，M2 下 `entry` 兜底把它变成 1 ⇒ **仍绿**；新版断言**文案**故 M2 必红——**C6 已从弱测试变强**，R1 issue #2 的真实性由此被反证。
- 全部变异已 `git checkout` 还原；收尾 `git status --short` 只剩作者的 2 份 manifest（`M`）+ 本报告（`??`），与开工快照一致。

## 阻塞项
**无。** 修复 5 未落地属纯文案、且 R1 已裁「极小、可留」，不使任何测试失败、不造成 spec over-claim ⇒ 不翻转 PASS。唯一值得主 session 知晓的是**声明与事实的偏差**：`3e92691` 提交信息声称修复了 5 条，实为 4 条。

## 实测
- 全量：`uv run pytest -q` ⇒ **404 passed**（R1 基线 402 + 新增接线 2 条 = 404，口径自洽）。
- CI 同款冒烟：`uv build --out-dir /tmp/wl_dist2` + `uvx --from /tmp/wl_dist2/*.whl witnessloop --version` ⇒ `witnessloop 0.1.0`，exit 0。
- 变异全部还原后复跑全量 ⇒ **404 passed**；`git status --short` 干净（仅 2 份 manifest + 本报告）。
- 无新增 over-claim / 与 spec 不一致 / 假测试：`docs/` 与 `openspec/` 中无「按成因 / 无法读取」字样（该声明仅存在于提交信息）；三条新/改测试在变异下均真红。
