# 对抗轮 R12：独立零记忆复核（收敛判定轮）

## Reviewer

- **身份**：本 change `gate-ref-pins-package` 的**第 12 轮**独立零记忆对抗复核。
  「零记忆」= 不采信 change 文档里任何「实测 / 已落库 / 已裁定 / 已收敛 / 已重排」的叙述，
  凡可重算的一律重算；文档写「已实测」而我无法复算的，一律记入「未验证项」。
- **冻结点**：分支 `gate-ref-pins-package/2026-10-16`，
  `git rev-parse HEAD` = `f6e275741cebcb2c178a1211343c275ab0c19be5`
  （= 上一轮 R11 的落点提交）。
- **开工前真仓洁净度确认**（题面要求的「先确认、再写报告」）：
  - `git log --oneline -2` ⇒ `f6e2757`（R11）/ `ba03ec8`（R10）；
  - `git status --porcelain` ⇒ **空输出**（真仓干净，本报告是本次唯一新增物；
    写报告之前连未跟踪文件都没有）。
- **关键物证 blob**（`git hash-object` 实测，前 10 位）：
  `design.md 55ff52fbad` / `spec.md b5be2a2916` / `tasks.md 98cfcd9b8c` /
  `proposal.md 903714c3fc` / `initcmd.py e597a2326e` / `checkcmd.py e12db4d94a` /
  `constants.py 0a64184d54` / `gate.yml 330104b810` / `docs/gate.md d382528f79` /
  `README.md 3bd4dc951a`。
- **方法**：全部实验在 `/tmp/adv12/` 里做——真仓零写入、零提交、零 tag、零 push。
  快照用 `git archive HEAD | tar -x -C <dir>`（**不用 `cp -a`**：本 worktree 的 `.git`
  是指针文件，`cp -a` 会把指针带过去、在副本里的提交会落回真仓）。
- **基线重算**：`PYTHONPATH=src python3 -m pytest -q` ⇒ **691 passed**
  （与题面给的基线条数一致，无遗漏/无新增红）。

## 对抗结论

**总判：判据② 满足；判据① 未找到新的行为级可证伪项；必须修改项 无。**

- **判据②（前十一轮的必须修改项是否真落库）：满足。**
  逐轮对**落点提交**跑 `git show --stat`，再对声称的落点文件逐条 `grep` / `Read` 验**内容**
  ——不采信 `design.md §7.9` 的「处置」文字、也不采信 §7.9 的落点表
  （上一轮 X1 正是靠这一手抓出来的：R9 的 W2 只落了规格半边、`docs/gate.md§1.2` 没落，
  而文字自述是「已落」）。本轮复算 **22 个落点提交**，结果见下表。
- **判据①（本轮是否找到新的行为级可证伪项）：未找到。**
  12 个 Scenario 逐个有**行为级**钉子（见下），20 条钉子逐条 `grep` 命中树上各 1 处；
  本轮的组合穷举与变异复核没有产出任何 Z 项。
- **必须修改项：无（Z 列表为空）。**

### 判据② 逐轮复算

| 轮 | 落点提交（`git show --stat` 已核对） | 声称的必须修改项 | 复核 |
|---|---|---|---|
| R1 | `5c03e26` | 停轮裁定落库 Q1=(B′) 等 | 命中 |
| R2 | `6813c8e` | L1–L6 + 低危观察 | 命中 |
| R3 | `37ab466` + `315574c` | M1–M4 + E1/E3 | 命中 |
| R4 | `1b59eb6` + `1099284` + `f045524` + `5384c6e` | N1–N3（含自查面扩到全仓） | 命中 |
| R5 | `1a0f9a2` + `b186cfa` + `bd80b1d` + `b71f457` | P1（台账非数组 fail-closed）+ 补钉 | 命中 |
| R6 | `4538404` + `8297b82` + `1474bb2` + `9bf5c8c` | T1（安装步吃解析输出）+ D1 顺序订正 | 命中 |
| R7 | `ab67ebd` | U1–U4（notice 来源文案 / 兜底真读 env / 两值绑定 / 是首行） | 命中 |
| R8 | `3865007` | V1–V4（V1 无条目无文件静默 no-op ⇒ 响亮拒绝） | 命中 |
| R9 | `24582f1` | W1–W4（定制 policy 前提 + refusal self 守卫 + 6.3 改按语义找） | 命中，**但 W2 只落了规格半边**（`docs/gate.md` 未含）⇒ 由 R10 补 |
| R10 | `ba03ec8` | X1（真正补 `docs/gate.md §1.2`）+ O1 + O3 | 命中 |
| R11 | `f6e2757` | Y1/Y2（`ignore` 同时作用于漂移判定；self 条目纳入拒绝面） | 命中 |

落点内容抽验（全部**命中树上**，非仅凭文字自述）：

- **K6** `docs/design.md:56`、`:73` 均已写「这个 ref **同时**决定 workflow 文件与 witnessloop 包版本
  ——change `gate-ref-pins-package`，见 `docs/gate.md §1.2`」。
- **L3** `tests/test_gate_workflow.py:466 test_witnessloop_ref_input_default_is_empty`
  断言 `inputs.witnessloop-ref.default == ""`；`.github/workflows/gate.yml` 实测默认值为 `""`。
- **M2** `docs/gate.md:243/245/256/261/274` 有「每个审阅报告各配一份 manifest（无孤儿报告）」
  与「同 stage 静默覆盖」的陷阱段落；**M3** `docs/gate.md:231` 有「本 PR 自己的变更并不豁免」
  的 revision 绑定订正。
- **O1** `src/witnessloop/initcmd.py:338` 的 `refusal = caller_retarget_refusal(...)` 确实位于
  所有写入点之前（下一个写入判定 `if tests_write is not None:` 在 `:342`）。
- **O3** `spec.md:105-109` 的 `uninit` 危害枚举里已含 `policy.json`。
- **T1** `tests/test_gate_workflow.py:532 test_the_install_step_consumes_the_resolved_ref` 存在。
- **U1–U4** `test_resolve_notice_names_the_source_of_the_ref`(:552)、
  `test_resolve_reads_the_fallback_ref_from_its_env`(:576)、
  `test_the_report_line_binds_each_value_to_the_right_label`(:154)、
  `test_the_report_line_is_the_first_thing_check_prints`(:170) 均在。
- **X1** `docs/gate.md §1.2` 的定制 policy 段（R9 只落规格半边、R10 补上）已在树上。
- **Y1/Y2** `test_dry_run_and_the_real_run_agree_on_a_hand_edited_caller`(:463)、
  `test_a_self_flagged_caller_entry_with_the_file_present_is_refused`(:482) 均在；
  `initcmd.py` 里 `ignore=(C.GATE_WORKFLOW_PATH,)` 同时喂给漂移过滤与冲突面（Y1），
  `caller_retarget_refusal` 有 `not entry.get("self")` 守卫（W3/Y2）。

**独立发现的「声称落库但文件缺席」第二例：无。** 全仓 `grep -rn "def <pin>" tests/` 逐条返回 1，
即 20 条钉子各自唯一存在、无重名、无同名占位。

### 判据① 行为级复核（12 个 Scenario 的钉子）

| Scenario | 行为级钉子 | 本轮复核 |
|---|---|---|
| ① 改一处两处变 | `test_resolve_prefers_the_reusable_workflows_own_sha` / `test_caller_ref_matches_this_repo` | 在树上 |
| ② 显式 `with:` 覆盖 | `test_resolve_lets_an_explicit_with_override_win`(:372) + `…_even_on_an_unusable_job_context`(:385) | 在树上 |
| ③ 畸形输入 | `test_resolve_fails_closed_on_malformed_workflow_refs`(:438) + `…_never_leaves_the_ref_empty`(:454) | 在树上 |
| ④ 日志可读 | `test_resolve_notice_names_the_source_of_the_ref`(:552) | 在树上 |
| ⑤ 能取到元数据 | `test_parses_the_real_payload`(:31) | 在树上 |
| ⑥ 取不到元数据 | `test_absent_or_unusable_metadata_is_not_an_error`(:38) + `…_empty_string_fields_are_treated_as_absent`(:141) | 在树上 |
| ⑦ 干净不动点 | `test_plain_init_is_idempotent_after_the_rewrite`(:100) + `test_same_ref_is_a_noop`(:142) | 在树上 |
| ⑧ 不给 flag 不动 | `test_plain_init_still_refuses_a_hand_edited_caller`(:151) | 在树上 |
| ⑨ `--dry-run` 只预览 | `test_dry_run_previews_without_writing`(:205) + `test_dry_run_must_not_claim_it_wrote_anything`(:266) | 在树上 |
| ⑩ 台账无 caller 条目 | `test_ledger_without_a_caller_entry_is_repaired`(:299) + `test_no_caller_entry_and_no_file_refuses_loudly`(:379) | 在树上 |
| ⑪ 与冲突 `--policy` 组合 | `test_explicit_gate_ref_plus_conflicting_policy_writes_then_reports`(:235) | 在树上 |
| ⑫ 边界可见 | `test_gate_documents_the_unprotected_caller_boundary`(test_docs.py:268) | 在树上 |

本轮另跑的**行为实验**（均在 `/tmp/adv12/` 快照）：

1. **`ignore` 过抑制面**：通读 `initcmd.py`，`ignore=(C.GATE_WORKFLOW_PATH,)` 只在
   `rewritten is not None`（即 caller 确实被重写/预览）那条 `_already_initialized` 路径上传入，
   且只过滤 caller 那一条路径 ⇒ 不会掩盖**其它**文件的漂移。手改 caller + 真跑、
   手改 caller + `--dry-run` 两种情形下 `ignore` 的取值路径均已走到，无过抑制。
2. **`caller_retarget_refusal` 误报面**：正常台账（caller 条目非 self）+ 无手改的场景下不触发拒绝；
   self 条目场景（`test_a_self_flagged_caller_entry_does_not_hide_the_refusal`:408）触发拒绝且
   台账字节不变（`test_a_refused_retarget_writes_nothing_at_all`:433）。
3. **15 例组合穷举**（`--gate-ref` × `--dry-run` × `--policy` × 已接入/未接入 × caller 手改/完好）
   + 不动点不变式检查器：全部不变式成立；`--dry-run` 的输出里**不含**「幂等」字样
   （曾疑此处违约，重跑 `exp4.py` 逐字节核对后确认为我读错对齐，**非缺陷**）。

## 未验证项

以下面无法在本 workspace 复算，一律**不**计入必须修改项（题面明令）。
若某处文档把它们写成「已实测」，那才是必须修改项——**本轮未发现这种写法**：

- **真实 CI 的 `job.workflow_sha` / `job.workflow_repository` / `job.workflow_ref` 取值**：
  GH Actions 运行时上下文，本机无法复算；只验证了 `gate.yml` 解析 step 在这些变量被喂成
  指定值时的**脚本行为**（`tests/test_gate_workflow.py` 用真 `sh` 驱动）。
- **Q1 的跨仓探针输出**（run `38853369550`、副本仓 `Xingkai98/asterwynd-wl-switch`）：
  二手证据，本机无法复跑；只复核了「原始输出写进 `design.md §2 D1`」这一落点在树上。
- **探针分支远端已删（404）**、本地分支 `probe/workflow-ref`（`c7aa037`）仍在：未复核远端删除动作。
- **GHES / fork / self-hosted runner** 下的行为：无环境。
- **`uvx --from "git+https://github.com/…@v1.7.0"`** 与 **`pip install git+…`**：无网络/无该 ref。
- **`v1.7.0` 目前不存在**：无法验证打 tag 后的行为（tasks.md §6 全是 `(post-merge)`）。
- **issue #30 的编号与内容**：未访问 tracker。
- **`refs/pull/N/merge` 形态下 uv 的解析行为**：只验证了 `gate.yml` 对该形态**拒绝**（fail-closed
  退兜底 ref + warning），未验证 uv 侧。
- **本仓自举 `check` 判绿（tasks 4.3）、归档与清单补齐（5.x）、`(post-merge)` 6.x**：均**未做**，
  且题面/文档本身标注为未完成（`tasks.md` 里对应复选框为 `[ ]`）。
- **未重跑前十一轮的全部 55+ 条变异**：只对本轮新关注的组合面与关键钉子重跑；其余变异复核
  采信 R1–R11 报告 + 落点 `git show --stat` 复核（已做）。

## 必须修改项

**无。Z 列表为空。**

本轮没有产出任何 Z 项。理由：
- 判据② 全绿（22 个落点提交逐条内容核对命中，未发现第二处「声称落库但文件缺席」）；
- 判据① 未找到新的**行为级**可证伪项（12 个 Scenario 逐个有行为级钉子，20 条钉子全在树上，
  组合穷举与不变式检查全部通过）；
- 其余发现均为**措辞/自述类**或**既有行为**，按题面纪律不计为必须修改项
  （见下方「低危观察」，已登记、不阻塞收敛）。

### 低危观察（登记，不计为必须修改项）

- **P-1（自述类 / 格式）**：`design.md:453` 自称「本节的 R 小节顺序……**已按 R1→R10 重排**」，
  `reviews/grill-adversarial-r11.md:238` 自称「`design §7.9` 的小节顺序**已按 R1→R11 重排**」，
  但 `grep -n "^### R" design.md` 实测顺序为
  `R1(253) R2(272) R3(307) R4(323) R5(334) R6(350) R7(383) R8(405) R9(421)`、
  **`R11(437)`、`R10(455)`** —— R10/R11 **仍然是反的**，两处自述均**为假**。
  影响：仅阅读顺序，不影响任何判定面（§7.9 是叙事表，判据②不读它）。
  属「自述与事实不符」的格式类问题，非行为缺陷。
- **P-2（措辞类）**：`handled` 那句「已按显式 `--gate-ref` 处理（**已落盘、不回滚**）」只在
  **冲突**分支打印；**漂移**分支（caller 被手改、`--gate-ref` 把它救回来）仍会重写 caller
  并在 stdout 说「已重写 … 并同步台账」，但 stderr 失败信息里**没有**这句 note。
  两面语义一致（都真落盘了），只是 note 的覆盖面比字面窄。不影响退出码、不影响幂等。
- **P-3（既有行为，非本 change 引入）**：台账 `gate_ref` 已是请求值、但磁盘 caller 被手改时，
  `init --gate-ref <同一 ref>` 退 1 且不修复——与 plain `init` 行为相同，且改动前即如此
  （属 R11 已登记的 `O-a` 同一族）。**不计为本 change 的新项**。

## Open Questions

- **OQ-1（留给后续轮/作者）**：`design.md:453` 与 `reviews/grill-adversarial-r11.md:238` 的
  「已重排」自述为假（见 P-1）。是否要在合并前把小节顺序与自述对齐（或直接删掉这两句自述）？
  建议：**删自述**而非改顺序（§7.9 按轮次追加更自然，强行按号重排会反复产生同样的漂移）。
- **OQ-2**：`tasks.md:6.3` 的 `grep -n "@v1" README.md docs/gate.md` 逐条人判——
  实测 `docs/gate.md` 命中 5 处（`:99/:103` 为历史引文/错误信息复现，`:161/:203/:349` 是
  `policy@v1`/`manifest@v1`/`event@v1` 这类 **schema 标签**，与 gate ref 无关）。
  该指令虽已写明「逐条人判」，但 `@v1` 这个 grep 会稳定命中 4 处**无关**行，
  执行者若「一律替换」会改坏 schema 标签。建议在 6.3 里点名「schema 标签不在此列」。
- **OQ-3**：`Q1=(B′)` 的本地物证是本地分支 `probe/workflow-ref`（`c7aa037`），
  远端已删。若该分支被后续分支清理误删，Q1 将失去可追溯物证。是否要在 change 文档里
  登记「此分支不可删」的显式理由？（R2 的 D4 已订正措辞，此处仅确认仍成立。）

## 收敛结论

**已收敛。**

- **判据② 结果：满足。** 22 个落点提交逐条 `git show --stat` + 落点内容核对，
  前十一轮的必须修改项（K1–K8 / L1–L6 / M1–M4 / N1–N3 / P1 / T1 / U1–U4 /
  V1–V4 / W1–W4 / X1 / O1 / O3 / Y1–Y2）**全部真落库**；
  未发现第二处「声称落库但文件缺席」（唯一的 X1 已由 R10 的 `ba03ec8` 补上）。
- **判据① 结果：通过（未找到新的行为级可证伪项）。** 12 个 Scenario 逐个有行为级钉子，
  20 条钉子逐条命中树上；本轮新做的组合穷举（15 例）与不变式检查全部成立；
  `ignore` 无过抑制、`caller_retarget_refusal` 无误报。
- **新增证伪类别统计**：本轮**没有新增证伪项**。仅 3 条低危观察——
  P-1 属**自述/格式类**（§7.9 顺序自述为假），P-2 属**措辞覆盖类**（`handled` note 未覆盖漂移分支），
  P-3 属**既有行为类**（同 ref + 手改 caller 不修复，改动前即如此）。
  三者均**不构成行为缺陷**，按题面纪律不升为必须修改项，已登记并附建议（见 Open Questions）。
- **最终裁定：本 change 的对抗轮到此**已收敛**。** Z 列表为空；
  余下未验证项受环境所限、且**没有任何文档把它们写成已实测**，故不阻塞收敛。

---

## 处置（主 session 在 R12 之后追加，非审阅者原文）

**收敛已确认，对抗轮到此结束（R1–R12）。** 你的三条低危观察：

- **P-1**：你说得对，而且这是**第二例 X1 式「作者自述与事实不符」**——我上一轮把顺序写对了的**自述**
  是假的。**本次真的换了顺序**（现为 R1→R11 连续），并把那句自述改成可复核的写法。
  记在这里：**两次都是靠 `git show --stat` / 行号复核抓到的**，不是靠读处置。
- **P-2**：接受。漂移分支也印那句「已落盘、不回滚」了（两个分支同一句话）。
- **P-3**：接受你的归类——**登记不修**（本 change 之前即如此）。

**后续**：本 change 进入收尾——实现后独立审阅（`reviews/building-review.md`）、
三份 stage manifest、本仓自举 `check`、开 PR。**本轮之后不再改 `src/` / `gate.yml` / `docs/`**，
除非 building 审阅提出必须修改项（那会再触发一轮证据重建）。
