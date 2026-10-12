# Grill: guard-crash-exit 设计追问

> 本轮只做 grill（设计追问），**不含**对抗验证（另起 run）。
> 立场：**挑战而非确认**——design 里每个 `文件:行号` 我都亲自打开核对，能实测的都实测了。
> 未改动任何 `src/**` / `tests/**` / `plugin/**` / change 文本；临时验证脚本全在 `/tmp`。
>
> ⚠️ **对抗验证 R1 回写（`reviews/grill-adversarial.md`，verdict CHANGES_REQUESTED）**：本文件已被作者按对抗
> 结论**回写**——标 `【R1 回写】` 的段落是修正后的口径（CD3 / 两处 Code-Resolved / Open Questions）。
> 被证伪的是**枚举与声明范围**，**大方向未被推翻**（选 A、`block` 保持 1、4 空闲、shim 零改动、不改 `check`）。

## Reviewer
- run id: grill-reviewer-guard-crash-exit-2026-10-12
- 时间: 2026-10-11T23:57:12Z

## Confirmed Decisions

- **决策（方向 · 对 design D1 / design §8 第一条的定案）**：选 **A**——`cli.main` 顶层兜底、`guard` 的「拦」**保持** `EXIT_FAIL`(1)；**否定** B（专用 block 码）。理由：版本偏斜**真实存在**且可证——plugin 经 git / `--plugin-dir` 分发、CLI 经 `uv tool install` **独立**安装，二者**无版本互钉**（`plugin/README.md:82`「装了 plugin 必须还要装 CLI」；`constants.py:11` 的 `DEFAULT_GATE_REF` 只钉 gate workflow、不钉 CLI）；B 在偏斜下**二选一皆坏**：旧 shim(1→2)+新 CLI(block=4) ⇒ 4 无人命中 ⇒ **静默永不拦**（比崩溃误拦更糟，因为无声）；新 shim 兼映射 {1,4} ⇒ 新 CLI 崩溃(退 1)又落进 block ⇒ **原 bug 复活**。A 不动 block 码 ⇒ 对偏斜免疫（我按 旧/新 shim × 旧/新 CLI 矩阵逐格复核，A 四格全对，见 `design.md:44-48` 与实测）。来源: grill-reviewer-guard-crash-exit-2026-10-12

- **决策（崩溃码取值 · 对 design §8 第三条的定案）**：新增 `EXIT_INTERNAL = 4`。理由：0 与「正常放行」同码 ⇒ 日志里区分不出「发生过崩溃」（诊断性丢失）；3 已被 `EXIT_NOT_ONBOARDED` 占（`guardcmd.py:95`）；我全树 grep 确认 **4 完全空闲**——`constants.py:80-83` 只有 0/1/2/3，全树无 `EXIT_* = 4`、无 `exit(4)`、无 `return 4`。来源: grill-reviewer-guard-crash-exit-2026-10-12

- **决策（兜底落点 · D3）**：在 `cli.main` 的 `guard` 分支用 `try/except Exception` 兜住 **`from witnessloop import guardcmd` 及其传递依赖**（`contract`/`gitutil`/`evidence`/`paths`/`policy`）的 `ImportError`，以及 `guardcmd.run(args)` 的运行期异常。理由：我在 `/tmp` 的**隔离补丁副本**上实测（复制 `src/witnessloop`、按 D3 打补丁、`PYTHONPATH` 指过去）——(a) 非法 UTF-8 报告 ⇒ `UnicodeDecodeError`（`evidence.py:216`）⇒ 兜底 ⇒ 退 **4**（非 1）+ 一行诊断；(b) `sys.modules["witnessloop.guardcmd"]=None` ⇒ `guardcmd.run` 抛 `ImportError` ⇒ 同分支退回 **4**；(c) `--help`/用法错误在 `parse_args`（`cli.py:138`，dispatch **之前**）发生且以 `SystemExit` 退出（`BaseException` 子类，不被 `except Exception` 捕获）⇒ 行为不变。来源: grill-reviewer-guard-crash-exit-2026-10-12
  - **【R1 回写】收窄 over-claim**：原稿写「一并兜住 **import 缺口（半装/坏装）**」——**不成立**。`cli.py:14-15` 的**模块级** import 发生在 `main()` **之前**、`__main__.py:3` 处，**不在** guard 分支 try 内；对抗验证实测「坏 `constants.py` ⇒ `witnessloop guard` **退 1** ⇒ shim 当 block」。⇒ 兜底覆盖的是 **`cli.main` 入口**及其后的 lazy import；`witnessloop.cli` **自身** import 失败（安装破损）**不被覆盖**。已记入 design D3 边界 + Open Question **Q2**。来源: grill-adversarial-reviewer-guard-crash-exit-2026-10-12

- **决策（shim 零改动 · D5）**：`plugin/hooks/guard.sh` 保持「只认 1、其余放行」，新增 4 **无需改 shim**。理由：我直跑真实 shim（把固定退出码的假 `witnessloop` 放 PATH 首位）实测映射表：**1→2、4→0、0→0、2→0、3→0、127→0**，与 `guard.sh:38-41`「`if [ "$status" -eq 1 ]; then exit 2; fi; exit 0`」一致。来源: grill-reviewer-guard-crash-exit-2026-10-12

- **决策（不改 `check`）**：本 change **不动** `check` 的退出码语义。理由：我在带 `add-x` 分支的仓上实测——`check` 在同一非法 UTF-8 报告上**同点崩溃**（`evidence.py:216`）并退 **1**，而 `EXIT_FAIL`(1) 恰是 `check` 的「未通过」（`constants.py:81`）⇒ 崩溃与「未通过」同码、方向 fail-closed，CI 锚语义正确，不改。来源: grill-reviewer-guard-crash-exit-2026-10-12

- **决策（漂移守卫必要 · D6）**：必须新增一条钉「`guard` 内部错误码 ≠ `EXIT_FAIL`」的测试。理由：当前**无任何测试**约束 4 的取值（全树 grep 无 `EXIT_INTERNAL`、无对 4 的断言）⇒ 若日后有人把 4 改回 1，会**静默复活本 bug** 而不变红（同 `grill-evidence-gate` D7 的教训）。来源: grill-reviewer-guard-crash-exit-2026-10-12

## Code-Resolved Questions

- **`4` 真的空闲吗？** → 是。`constants.py:80-83` 定义 `EXIT_PASS=0 / EXIT_FAIL=1 / EXIT_USAGE=2 / EXIT_NOT_ONBOARDED=3`；全树 grep 无 `EXIT_*=4`、无 `exit(4)`、无 `return 4`。（证据：`src/witnessloop/constants.py:80-83` + 全树 grep）
- **`guard` 会先因 `report_hash` 不匹配而拦吗？**（决定测试 B1「覆写成非法字节」是否可行）→ **否**。`guardcmd.run` 只调 `grill_evidence_findings_in_change`（`guardcmd.py:108`），该函数读清单时**不校验任何 hash**、只读报告正文（`evidence.py:177-217`）⇒ 覆写报告不会先被 hash 拦下，能直达崩溃点。测试 B1 可行。（证据：`guardcmd.py:108`、`evidence.py:177-217`）
- **`sys.modules["witnessloop.guardcmd"]=None` 能让 `from witnessloop import guardcmd` 抛 `ImportError` 吗？** → **能**。实测抛 `ImportError: import of witnessloop.guardcmd halted; None in sys.modules`（`from ... import` 与裸 `import` 均然），且 `ModuleNotFoundError ⊂ ImportError ⊂ Exception` ⇒ 被 D3 兜底捕获，退回 4。测试 B3 可行。（证据：/tmp 实测）
- **崩溃点只有 `evidence.py:216` 一处吗？** → **否，实测 ≥3 处**【R1 回写】。`evidence.py:165`（`_read_json`）与 **`policy.py:128`**（`load_policy`）同病：两处的 `except (OSError, json.JSONDecodeError)` 都**漏** `UnicodeDecodeError`（它是 `ValueError` 子类，实测 MRO 为 `UnicodeDecodeError→UnicodeError→ValueError`）。另有潜在第 4 处 `gitutil._run`（`git` 不在 PATH ⇒ `FileNotFoundError`）。实测：**清单**非法 UTF-8 ⇒ guard 崩退 1；**policy** 非法 UTF-8 ⇒ `load_policy` 抛 `UnicodeDecodeError`。（证据：`evidence.py:163-167`、`policy.py:128-129`、`gitutil.py:29-34`、`guardcmd.py:52,108` + 实测）
  - **【R1 回写】原稿写「至少第二处」= 枚举不完备**（被对抗验证证伪「只有第二处」的完整性）。⇒ design §1 已列 ≥3 读点表，并**在源头按读点归一**（design D4/D5）——通用兜底仍覆盖未枚举者。
- **design D7「本 change 目录在场 ⇒ 不自锁」成立吗？** → **不成立（理由错，但结论对）**。guard 的放行条件是 **grill 证据完备**、不是「目录在场」：`run` 调 `grill_evidence_findings_in_change`，无 `stage=grill` 清单即产出一条 Finding ⇒ 拦（`guardcmd.py:108-129`、`evidence.py:189-203`）。既有测试 `test_blocks_a_code_write_without_grill_evidence`（`tests/test_guard.py:42-48`）正是「目录在、无 grill 清单 ⇒ BLOCKED」。⇒ 最终「不自锁」靠的是**本 change 的过程会产出 grill 证据**，不是「目录在场」；且因此存在一个顺序约束（见风险）。（证据：`tests/test_guard.py:42-48`）
- **加 `EXIT_INTERNAL` 会让既有测试变红吗？** → **否**。我把「`constants` 加 `EXIT_INTERNAL=4` + `cli` 按 D3 加兜底」打成一个**隔离副本**跑全量测试：**388 passed**（与基线口径一致）。首轮有 2 条 `test_agentenv` 失败，纯属副本落在 `/tmp` 导致模板路径解析成 `/tmp/templates` 的**路径假象**，加符号链接修正后即消失——与代码改动无关。（证据：/tmp/gce-fix 实测）
- **design D3 的示例代码能直接落地吗？** → **不能照抄**。`cli.py:15` 只 `from witnessloop.constants import DEFAULT_GATE_REF, EXIT_USAGE`，**没导入 `EXIT_INTERNAL`**；D3 示例（`design.md:71`）里裸写 `return EXIT_INTERNAL` 会 `NameError`。实现时须把 `EXIT_INTERNAL` 加进该 import（或写 `constants.EXIT_INTERNAL`）。design §3 的接线清单漏了这步。（证据：`src/witnessloop/cli.py:15`）
- **`--help` / 用法错误行为会变吗？** → **不会**。二者在 `parse_args`（`cli.py:138`，dispatch 之前）发生，且以 `SystemExit` 退出（`BaseException` 子类，`except Exception` 不捕获）。实测补丁副本：`["guard","--help"]`→`SystemExit(0)`、`["guard","--nope"]`→`SystemExit(2)`、`["bogus"]`→`SystemExit(2)`。（证据：`cli.py:18-23,138` + 实测）
- **文档影响面只有 design 说的那两处吗？** → **不，而且原稿判断被证伪**【R1 回写】。原稿写「`docs/design.md` 与 `README.md` **不含** guard 退出码叙述」——**错**：**`README.md:35`** 明写 `# 本地守卫：… → 拦（exit 2）`，挂在 `witnessloop guard --path src/x.py` 下，**这就是一条 guard 退出码叙述**、且 CLI 实际是 **1**。加上 **`docs/adr/0001-local-guard-hook.md:16`**（同样写 exit 2、同样与 `guardcmd.py:129` = `C.EXIT_FAIL` = 1 不符），**共两处既有漂移**（源自 change `grill-evidence-gate` 改「拦 2→1」时漏改）。（`docs/design.md` 确实只含概念性提及、无需改。）⇒ design D7 已把**两处**纳入订正清单。（证据：`README.md:35`、`docs/adr/0001-local-guard-hook.md:16`、`guardcmd.py:129`、`constants.py:81`）
- **`check` 与 `guard` 共用同一个判定函数吗？**（决定 Q1「硬化」的影响面）→ **是**。`grill_evidence_findings_in_change`（`evidence.py:170`）被 `guardcmd.run`（`guardcmd.py:108`）与 `check` 侧共用；在 `evidence.py:216` 处「硬化」会**同时**改变 `check` 与 `guard` 的行为，无法只作用于其一。（证据：`evidence.py:170`、`guardcmd.py:108`）

## Open Questions

> 【R1 回写】原 Q1/Q2 经对抗验证后**重述**为下面两条（原 Q1 的「硬化 or 不硬化」被证伪为框架有漏——
> 它把「manifest 读点」与「报告读点」**混为一谈**，二者归宿不同；原 Q2 的「check 崩溃输出」已被
> 甲案顺带解决，不再单列）。

- **Q1** 证据文件**存在、但解码失败**（损坏）时，`guard` 该**拦**还是**放**？
  **具体场景 A（报告损坏）**：你把 `openspec/changes/<id>/reviews/grill-review.md` 存成了一个非法 UTF-8 文件
  （混进一个 `0xff` 字节）。此时 **甲案** ⇒ `guard --path src/x.py` 退 **1**（拦）+ 提示「报告无法解码」，
  你先去修报告再写代码（写文档仍豁免 ⇒ 不死锁）；**乙案** ⇒ `guard` 退 **0**（放，这是**被处理过的确定性结论**、不是崩溃），
  让你照写，等 CI 的 `check` 变红。
  **具体场景 B（manifest 损坏）**：`reviews/building.manifest.json` 被写成非法字节。**甲/乙两案都拦**——
  因为「manifest 缺失 / JSON 语法坏」本就拦（`evidence.py:184-203`），字节坏必须与之一致，否则自相矛盾。
  **具体场景 C（policy 损坏）**：`.witnessloop/policy.json` 损坏 ⇒ **两案都放行**（连受管控范围都读不出 ⇒ 不执行）——
  与既有 `PolicyError` 处理同归，**无争议**。
  - ➡️ **推荐答案：甲案（统一「读不出 ⇒ 不可核验 ⇒ 不完备」⇒ 拦 / `check` 红）**。
    **【R2 回写】原稿否乙的两条理由已被 R2 证伪，现按事实重述**：
    - ~~「乙无法干净实现」~~ → **伪**：给共享函数加一个**带默认值**的调用者参数（或拆一个 `guard` 专用窄函数）即可。
    - ~~「乙会让 `check` 变绿 ⇒ 失去 fail-closed」~~ → **真实场景下伪**：报告通常在 manifest **之后**被写坏
      ⇒ `check` 由 `report_hash` **独立**判红（`contract._check_hashes`），**不会绿**；只有「把字节坏报告
      **重新 `manifest build`** 进 manifest」这一角落才绿（属**作者自欺**，落在「防漂移不防伪造」边界内）。
    - **两案的真实差别**：甲=报告损坏时 `guard` **拦**（快反馈：先修报告）、封住上述角落（`check` 仍红）、**不新增参数**、
      与「manifest 缺失⇒拦」**同口径**；乙=报告损坏时 `guard` **放**（交 CI 锚）、**需新增调用者参数**、
      「容器/内容」两分须在 spec 写明、上述角落 `check` 会绿。
    - **为何仍推荐甲**：口径统一（少一类特例）、反馈更早、不留「重 build 坏报告」这个绿洞；代价仅是 `guard` 对
      **不可核验**的证据更严——而这与本门禁「证据不完备不许写码」的主张一致，且**不自锁**（写报告属文档豁免，R2 已实测）。
- **Q2**（边界/范围）`witnessloop.cli` **自身** import 失败（**安装破损**，如 `constants.py` 坏了）时
  `witnessloop guard` 仍退 **1** ⇒ 被 shim 当 block（对抗验证已复现）。
  **具体场景**：一次坏发布把 `constants.py` 打成语法错；装了 plugin 的仓里，**每个 `Write/Edit` 都被拦**，
  且 hook 进程读不到你 `export WITNESSLOOP_SKIP_GUARD=1`（那是外层进程）⇒ 只能拆 plugin/重装 CLI。
  - ➡️ **推荐答案：收窄声明 + 显式记录边界（不扩本 change 的范围）**。理由：该场景的前提是**安装破损**
    （此时 `check`/`init` 等**所有**动词一起坏，不是 guard 专属），而修法是**新增一个 entry 模块 + 改
    `pyproject.toml` 的 console-script 入口**（架构级、会动 packaging 契约）——超出「低优先 bugfix」的尺度。
    ⇒ 在 design 的**边界/非目标**里写明这个洞，spec 的绝对句收窄为「`cli.main` guard 分支内」。
    （若你要求**彻底关掉**这个洞，我改走「前移到入口」方案：新 entry 兜底 + argv 判 verb。请明示。）

## 风险

> 【R1 回写】本节经对抗验证补充/修正；**新发现**项以对抗验证结论为准。

- **新发现（读点 ≥3，非「第二处」）**：`evidence.py:165`（manifest）与 **`policy.py:128`**（policy）同病——`except`
  子句都漏 `UnicodeDecodeError` ⇒ 崩 ⇒ 退 1 ⇒ 误拦。design 只点了一处 `evidence.py:216`。⇒ design D4/D5
  **在源头逐读点归一**（policy⇒放、manifest⇒拦、报告⇒按 Q1），通用兜底（D3）只接「真正未预期」的异常。
- **新发现（文档漂移 ×2，既有）**：`README.md:35` 与 `docs/adr/0001-local-guard-hook.md:16` **都写** guard「拦（exit 2）」，
  而代码是 **1**（源自 `grill-evidence-gate` 改「2→1」时漏改）⇒ design D7 一并订正。
- **新发现（不变量未机械钉死）**：D2/D3 声称「兜底后 1 **只**由 `return C.EXIT_FAIL` 产生」（`design.md:50`）。这只在「guard 链路里没有别的 `sys.exit(1)` / `raise SystemExit(1)`」时成立；漂移守卫只钉常量，挡不住日后有人在链路里写出 `sys.exit(1)`。建议在漂移守卫旁补一条**功能断言**（guard 分支兜底确实返回 `EXIT_INTERNAL`，B1–B3 已覆盖）或加注释声明该不变量。
- **新发现（文档漂移 · 自伤面）**：`docs/adr/0001-local-guard-hook.md:16` 已与代码不符（写 exit 2，实为 1）。本 change 的主题恰是 guard 退出码，若不订正，会**新增**一处文档漂移——而本仓卖点正是「文档不漂移」。建议把该 ADR 纳入 D6 的同步清单。
- **新发现（自伤面 · 顺序约束）**：由 Code-Resolved 的 D7 修正推出——`guard` 要求「`reviews/*.manifest.json` 里有 `stage=grill` 且报告合格」**在盘上**；而按 `docs/gate.md §3.1`「先内容后证据」，`manifest build` 本该在内容提交**之后**跑。于是实现时**先写 `src/**`**（`constants.py`/`cli.py`/`guardcmd.py` 均在 `require_change_for` 内）**之前**，必须先有一个（哪怕是临时的）grill manifest 在盘上，否则每次 `Write|Edit` 都被拦。可行解：实现前先跑一次 `manifest build`（`head_sha` 暂指当时 HEAD）放行，内容提交后**重跑覆盖**成最终 manifest。建议在 `tasks.md` 点明这一步，避免实现者误以为「目录在场即可写 src」。这**不是死锁**（本 change 的过程会产出证据），但 design D7 的现有措辞（「目录在场 ⇒ 不自锁」）会误导。
- **已承认（design R2）**：`except Exception` 可能掩盖真 bug——缓解（诊断行含异常类型 + message、且只作用于 `guard`）成立、可接受。
- **已核对（design R4）**：CC 对非 0/2 退出码视为**非阻塞**（放行）——与意图一致；且 shim 实际把 4 映射成 **0**、不直传，故这条只在「绕过 shim 直连 CLI」时才相关。
- **流程提示（非缺陷）**：本报告是 grill 产物，**尚无** `## User Confirmation` 段；因此 `check` 此刻会把上面的 Q1/Q2 判为「未经用户确认」= 红，**这是预期的**——停轮拿到用户答复后须把 Q1/Q2 逐条写进 `## User Confirmation`（`- **Q1**: 用户答复：…；确认时间: …`），本 change 才会转绿。
