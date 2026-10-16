# Grill（对抗轮 R2）：gate-ref-pins-package —— 独立零记忆证伪

## Reviewer

我是**独立零记忆**的对抗验证者（本对话不携带该 change 的任何历史）：`design.md` / `proposal.md` / `tasks.md` / `spec.md` 与两份
review 里的「实测」「文件:行号」「已定案」一律当**待验证断言**，可复算的一律复算，**目标是证伪结论本身**。

**本轮对象有两层，先说清基准（重要）**：

1. **change 四份文档**在本轮**一字未改**（blob：`design.md c2e2b1f2…`、`tasks.md 303200b9…`、`specs/gate-ref-pinning/spec.md 09d350a7…`、
   `proposal.md 903714c3…`）⇒ 行号引用稳定。
2. **实现是在我这次会话进行中并发落地的**：我快照了当时的未提交树到 `/tmp/adv2/snap`（`initcmd.py 90392fb6…` / `checkcmd.py 499034b4…` /
   `gate.yml 2167edb1…`），随后它在 16:03 被提交为 **`5cc56b4`**（含 `README.md` / `docs/gate.md` / `docs/design.md` / `src` / `tests`，`git status` 现为 clean）。
   ⇒ 本轮不止核对文档，**还能真跑实现**。凡引用实现处都以 `5cc56b4` 为准。

**实际读了**：change 的 `proposal.md` / `design.md` / `tasks.md` / `specs/gate-ref-pinning/spec.md` / `reviews/grill-design.md` /
`reviews/grill-adversarial.md`（R1）；源码 `src/witnessloop/{initcmd,checkcmd,uninitcmd,cli,constants,evidence,entry,policy,paths,hashing}.py`（含 5cc56b4 的改动）；
`.github/workflows/{gate,witnessloop,ci}.yml`；`.witnessloop/init-manifest.json`；`README.md` / `docs/gate.md` / `docs/design.md`；
`tests/{test_init,test_init_policy,test_init_gate_ref,test_check_package_ref,test_gate_workflow,test_uninit,test_init_tests_command}.py`。
另**成功抓到** GitHub 官方 contexts 文档与 **issue #30 正文**（本轮的新证据源，R1 当时两项都没取到）。

**实际跑了（命令 + 原始输出要点，逐条可复算）**：

1. **真 `uvx` 装包（uv 0.13.1；`pip install --target /tmp/adv2/uvpkg uv`）——ref 形态全覆盖**：
   | `--from git+https://github.com/Xingkai98/witnessloop@…` | 结果 |
   |---|---|
   | `v1`（tag） | ✅ 装成；`direct_url.json` = `{"vcs_info":{"vcs":"git","commit_id":"ae992565ee2162e5b272af471e9adf895e7f83fb","requested_revision":"v1"}}`；uvx 自己打印 `Building witnessloop @ …@ae992565…` |
   | `ae992565ee2162e5b272af471e9adf895e7f83fb`（40 位 sha） | ✅ `requested_revision` = 该 sha |
   | `refs/heads/main` | ✅ 解析成 `eaca5689…` |
   | `refs/tags/v1` | ✅ 解析成 `ae992565…` |
   | `archive-arrival-recognition/2026-10-15`（**带斜杠的分支名**） | ✅ |
   | `ef8b3ab7…`（`origin/main~3`：**非 tip、非 tag** 的 commit） | ✅ 装成 |
   | `refs/pull/1/merge` | ❌ `fatal: couldn't find remote ref refs/pull/1/merge`（该 PR ref 在本仓不存在；**e3 的定性因此仍只能停在「未实测」**） |
   | `2778bc24e13c8fdd18e18765c81eb0ff731e6568`（探针说这是**接入方**的 commit，不在本仓） | ❌ `fatal: remote error: upload-pack: not our ref …` ⇒ **硬红** |
2. **把 `gate.yml` 的解析 step 原文抽出、交真 `bash` 跑**（`GITHUB_OUTPUT` 捕获），8 个 case 全部符合 spec 的 Scenario：
   `job.workflow_sha` 主路径 ⇒ `ref=6e2ec4dc…` + `::notice::…（来源：job.workflow_sha…）`；显式 `with:` ⇒ `ref=v9.9.9（来源：调用方显式传入…）`；
   repository 不匹配 ⇒ `::warning::` + `ref=v1`；repository 空（GHES）⇒ 同上；sha 空 ⇒ 分支兜底 `ref=main`；sha 空 ⇒ tag 兜底 `ref=v1`；
   `refs/pull/30/merge` ⇒ warning + `ref=v1`；无 `@` ⇒ warning + `ref=v1`。
3. **测试面**：`PYTHONPATH=src python3 -m pytest -q`（在快照上）⇒ **665 passed**（R1 当时 635；新增 `test_init_gate_ref.py`、`test_check_package_ref.py`）。
   `tests/test_init_tests_command.py::test_caller_workflow_bytes_are_frozen` **仍在**且通过 ⇒ (B′) 下 `caller_workflow()` 字节不变的断言成立。
4. **Q2(a) 升级路径实测 9 个场景**（脚本 `/tmp/adv2/q2probe.py`）：升级 EXIT=0 且台账 `sha256`+`gate_ref` 同步 ✅；随后 plain `init` 幂等 EXIT=0 ✅；
   `uninit` EXIT=0 ✅；`--dry-run --gate-ref` 不落盘且不谎报幂等 ✅；**新仓里有外来 caller ⇒ EXIT=1、整体不落盘、policy 未写** ✅（`tests/test_init.py:128-141` 的保证**没被打破**）；
   台账缺 caller 条目 ⇒ 补条目 EXIT=0 ✅；磁盘被手改 + 给新 ref ⇒ 修复 EXIT=0 ✅。
   ⚠️ **`--gate-ref <新> --policy <冲突>` ⇒ EXIT=1，但 caller 与台账已经改写**（部分落盘）。
5. **旧 CLI 跑「文档写的升级动作」**（README 让装的 `@v1` 包，真 uvx）：`witnessloop init --gate-ref …@v1.7.0` ⇒ **EXIT=1**，
   文案 `init：检测到冲突（已接入，但本次指定的内容与已落地不同；只增不改，拒绝覆盖。要更换 policy 请先 uninit）`。
6. **`check` 自报面**：源码直跑 ⇒ `check：本包来源（自报，尽力而为）：requested_revision=<未知>，commit_id=<未知>`，其后 `check：未通过 ✗（4 项）`（都只是缺 manifest）；
   **但 `uvx --from …@v1 witnessloop check` 的输出里根本没有这一行**（`@v1` = 改动前的包）。
   `vcs_info_from_direct_url` 对 11 种畸形输入（空/None/非 JSON/根是 list/无 vcs_info/字段为 int/字段为空串/坏字节/bytes）**全部返回 `(None, None)`，从不抛**。
7. **本仓自证命令复算**：plain `init --root . --dry-run` ⇒ **EXIT=1**，diff **只涉及 `.witnessloop/policy.json`**（`require_change_for` 与
   `grill_stage`/`grill_adversarial_stage`/`building_stage` 三个键）—— 与 `design.md:148-151` 的表述**逐条相符**；
   按 `tests/test_init_policy.py:19-30` 的 `CUSTOM_DOC` 复原 seed 后 `init --dry-run --policy <seed>` ⇒ **EXIT=0「幂等，无改动」** ✅。
8. **`grill_evidence_findings` 真跑**：`grill-design.md` ⇒ **0 findings**；`grill-adversarial.md` ⇒ 7 条（但 `constants.py:81-86` 与
   `evidence.py:346-347,373` 证明**只有 `grill` 段校验正文**，`grill-adversarial` 段 `verify_body=False` ⇒ R1 报告不阻塞 `check`，成立）。
   **游戏化实测**：把 `### Q4` 整段**移出**候选小节（挪到一个不相干的 `## 其它待议`）⇒ **仍然 0 findings**（Q4 从此不需要任何确认）；
   把标题改成 `## Open Questions 汇总` ⇒ 判「缺少 `## Open Questions` 小节」**fail-closed**（改名绕不过去）。
9. **git 事实**：`git rev-list --count v1..origin/main` = **47**；`v1..HEAD`(5c03e26) = **49**；`v1..main`(陈旧本地) = 0；
   `git diff --stat v1..HEAD -- .github/workflows/gate.yml` **空**；`git show v1:.github/workflows/gate.yml` 的默认值 = `"v1"`；
   远端 `refs/tags` 最大 = **v1.6.0**（**不存在 v1.7.0**）；`git ls-remote --heads` 里**没有** `probe/*`（远端确已清理），
   但本地仓**仍保留** `probe/workflow-ref` 分支与 `c7aa037`。
10. **官方 contexts 文档逐字**：`job.workflow_ref` = "The full ref of the workflow file that defines the current job."，并明写
    "**For jobs defined directly in a workflow file, this is the same as `github.workflow_ref`**"（⇒ 反推：job 定义在 **reusable** 里时两者**不同**）；
    `job.workflow_sha` = "**The commit SHA of the workflow file that defines the current job.**"；`job.workflow_repository` = "The `owner/repo` of the
    repository containing the workflow file that defines the current job."；三者都带 "(not available on GitHub Enterprise Server)"；
    `on.workflow_call.inputs.<inputs_id>.default` 的可用上下文 = "`github, inputs, vars`"（⇒ **M7① 与 design §4 R6 逐字成立**，`job.*` 只能进 step）。
11. **issue #30 正文（本轮抓到，R1 没抓到）**：正文的 CI 对照表 = 「`v1`（默认）⇒ **✗ 10 项**」/「`main` ⇒ **✗ 1 项**」⇒ 与 `proposal.md:33-34` **一致**；
    但正文里**没有** `job.workflow_sha` / `github.workflow_sha` 这类 context dump —— Q1 探针（run 38853369550）的原始输出**只存在于
    `design.md §2 D1` 那段粘贴里**（`proposal.md:4` 说「issue #30 正文有原始输出」，指的是 asterwynd 的 CI 对照，不是探针输出；措辞对得上，但容易被读成后者）。
    另：issue 正文自己写的是「落后 `main` **20+ 个提交**」。
12. **`git show 5cc56b4 -- src/witnessloop/constants.py | grep DEFAULT_GATE_REF`** ⇒ **无 `+/-` 命中** ⇒ 实现**没有**动 `DEFAULT_GATE_REF`（仍是 `@v1`），与 Q3 的 (post-merge) 一致。

**没能复算的**：Q1 探针（run `38853369550`）的**原始输出**——那两次 run 的分支/文件已删、无法重跑，唯一载体是 `design.md §2 D1` 的文本块；
探针里两个 sha（`6e2ec4dc…` / `2778bc24…`）**取不到**；`job.*` 在真 CI 里的运行期取值；GHES / fork / 自建 runner / `pip install git+…` 的行为。见「未验证项」。

---

## 对抗结论

### A 本轮新证伪 / 新缺口（非措辞）

**A1（新证伪 · 高）post-merge 计划按其字面执行**无法兑现 Q3 的收益——打出的 `v1.7.0` 里 `DEFAULT_GATE_REF` 仍是 `@v1`。**

- 依据链：`tasks.md:69`（6.1）先「建 tag `v1.7.0`（**指向合并后的 `main` 上含本 change 的那个 commit**）」，
  `tasks.md:70`（6.2）**之后**才「把 `DEFAULT_GATE_REF` 从 `…@v1` 改成 `…@v1.7.0`」。
- 而 5cc56b4 的实现**没有**动这个常量（第 12 条证据），所以被 tag 的那个提交里 `constants.py:21` 就是 `@v1`。
- 后果（逐环，可复算）：接入方 `uv tool install …@v1.7.0` ⇒ 装到的是**M 那份代码** ⇒ `witnessloop init` 写出的 caller 是
  `uses: …gate.yml@v1`（**实测**：`@v1` 的 CLI 生成的 caller 逐字就是 `@v1`）⇒ 跑的是**改动前那份 gate.yml**（`git diff v1..HEAD -- gate.yml` 为空）
  ⇒ 包仍是 `ae99256`。**「新接入方默认吃到新包」（`design.md:269-271`、`grill-design.md` Q3 推荐）在 v1.7.0 上落空**，
  而且落空得比今天更隐蔽：接入方以为自己钉了 v1.7.0。
- 附带（同一条根因）：`README.md:181-192` 的新 recipe 直接写 `…@v1.7.0`，而 **v1.7.0 今天不存在**（第 9 条证据：远端 tag 最大 v1.6.0）
  ⇒ 这个 PR 合并后、6.1 执行前的窗口里，照 README 抄的人会把 caller 钉到一个**不存在的 ref**（`uvx`/workflow 加载都会失败）。
  文档没有任何一句提示「发布前请仍然钉 `@v1`」。
- 修法（择一，并写进 `tasks.md §6`）：**(i)** 把「改 `DEFAULT_GATE_REF` 的提交」作为**被 tag 的那个提交**——即 6.2 在 6.1 **之前**，
  6.1 改成「tag 到含 6.2 改动的最新 `main`」；或 **(ii)** 6.2 改成两步（先改常量到 `@v1.7.0`，再 tag 那个提交）。
  两条都要顺带把 **`README.md:20` 的安装 ref 新值**写进 §6 的动作清单（现在 §6 只字未提 README:20，`design.md:189-190` 只记了「同源」这一句提示，没写新值）。
- **可复算的验收命令**（建议直接进 `tasks.md §6`）：`uvx --from "git+https://github.com/Xingkai98/witnessloop@v1.7.0" witnessloop init --root <scratch> --dry-run <seed>`
  ⇒ 输出里的 caller 行 SHALL 逐字是 `uses: Xingkai98/witnessloop/.github/workflows/gate.yml@v1.7.0`。

**A2（新证伪 · 高）文档把 `init --gate-ref <新>` 写成「单一升级动作」，但 README 让接入方装的那个 CLI 上它不存在——实测 EXIT=1 且文案把人指向 policy。**

- 文档原文：`docs/gate.md:81-87`「**升级动作（单一、显式）**：对**已接入**的仓，显式给 `init --gate-ref <新 ref>` ⇒ 重写 caller + 同步台账」；
  `README.md:191-192` 的 recipe 也只有 `witnessloop init --gate-ref …`。两者都**没写前置条件**。
- 实测（第 5 条证据）：用 `README.md:20` 让装的 `@v1` 包跑这条命令 ⇒ **EXIT=1** +「检测到冲突…**要更换 policy 请先 `uninit`**」。
  ⇒ 每一个存量接入方**第一次**照文档升级都会撞一条**误导性**的红（他手里明明是 caller 的 ref 变了，文案却说 policy）。
- 根因：这个能力是**新版包**才有的（`initcmd.sync_caller_gate_ref`），而新版包所在的 ref **本 PR 内还不存在**（A1 的同一根因）。
- 修法：`docs/gate.md §1.2` 与 `README.md` 的 recipe **必须**先写「① 升级 CLI：`uv tool install git+…@<新 ref>`（否则下面这条命令会以「冲突」告终）」，
  再写 ② `init --gate-ref`；并把旧 CLI 的症状（EXIT=1 + `冲突` 文案）如实登记，否则接入方会去删 policy。
- 旁证（同一件事的正面）：`design.md:99-112` 与 `docs/gate.md:86-87` 说的「终态是干净不动点」我**复算成立**（第 4 条证据），
  所以缺的不是语义，是**前置条件与入口**。

**A3（新缺口 · 中）没有任何测试钉住 `on.workflow_call.inputs.witnessloop-ref.default == ""` ⇒ 中央机制可被静默改回原缺陷。**

- `grep -rn "witnessloop-ref" tests/` ⇒ 只有 `tests/test_gate_workflow.py:330`（钉 env 绑定）与注释；**没有**任何断言碰 `default`。
- 后果可复算：把 `.github/workflows/gate.yml:23` 改回 `default: "v1"` ⇒ **665 条测试仍全绿**，而第一个 step 的规则① 会对**每个**没传 `with:` 的接入方
  命中（`WL_INPUT_REF` 非空），日志还会说「来源：**调用方显式传入**的 with.witnessloop-ref」——我把 `WL_INPUT_REF=v1` 喂进真 step，输出正是
  `ref=v1` + 那句 notice（第 2 条证据的第二个 case）。**症状与今天的缺陷一模一样，且完全没有红灯。**
- 修法：加一条钉子（本仓对字面量的既有风格就是钉：见 `gate.yml:48-49` 的 `WL_REPO_SLUG`/`WL_FALLBACK_REF`、`tests/test_gate_workflow.py:322-336`），
  例如断言 `inputs["witnessloop-ref"]["default"] == ""` 且 `required is False`。

**A4（新缺口 · 中）`--gate-ref` 与冲突的 `--policy` 组合会「报失败但已落盘」。**

- 实测（第 4 条证据末）：`init --gate-ref <新> --policy <冲突>` ⇒ **EXIT=1**，但 `caller` 与台账**已经被改写**（`caller rewritten: True | ledger synced: True`）。
- 文档没定这个语义：`spec.md:82-102` 的升级 Requirement 只写「重写 caller + 同步台账，其余文件照旧只增不改」，
  `design.md:207-222`（§5 测试策略）也没有这条组合。既有先例是 `--test-command` 的「写在前、其余判定照旧参与退出码」（`initcmd.py` 的 Z1/O2 注释），
  但那条写的文件**不在台账里**，写坏也不产生分叉态；这条写的是**台账 + caller**。
- 现实现是自洽的（caller 与台账一起改，退 1 只剩 policy 一条轴），所以**不是**坏中间态；但「EXIT=1 却已落盘」必须被写死，
  否则下一个实现者会顺手改成「先判后写」，把 `--dry-run` 与「磁盘 ≠ 台账」的边界一起搅动。

### B 逐条核 R1 的 K1–K8 是否**落进正文**（不是核那张表）

| # | R1 要求 | 落库核对（正文，逐条） | 我的复算 |
|---|---|---|---|
| K1 | 删/改「包无法自报 ref」 | `design.md:121-139`（§2 D3 整段重写，「R1 K1 订正（原稿此处为假）」）+ `spec.md:58-70`（新 Requirement，含「R1 K1 的实测订正」）+ `design.md:234`（§7.9 表）| ✅ **实装且正确**；`uvx` 真装复现 `vcs_info`（第 1 条证据） |
| K2 | 改「没有任何提示」 | `proposal.md:19-29` 整段改写（现标题即「『没有任何提示』是**假**的（R1 K2 实测证伪）」）| ✅ 复现：空缓存 uvx 自打 resolved sha（第 1 条证据） |
| K3 | 「永久死锁」降级 | `design.md:109-114`（§2 D2 三条恢复路径 + `check` 不读台账）+ `grill-design.md:39-42`（追加订正）| ✅ 与 R1 一致；`grep -rn INIT_MANIFEST src/` 无 `checkcmd` 命中 |
| K4 | 自证行在 (A) 下自相矛盾 | `design.md:141-156`（§2 D4 整段重写：本 PR 不做本仓迁移、自证条件写明）| ✅ **且事实复核通过**：plain dry-run EXIT=1 且 diff 只关 policy；`--policy <seed>` EXIT=0（第 7 条证据） |
| K5 | 「47 个提交」计数 | `design.md:238`（K5 行）+ `grill-design.md:18,33`（标注基准）；正文已**去计数**（`grep -n "47\|落后" design.md` 只命中 K5 行本身）| ✅ **R1 的 K5 确系测量基准造成**：`v1..origin/main`=47、`v1..HEAD`=49、陈旧 `main`=0；issue #30 自己写「20+」⇒ 去计数是对的 |
| K6 | 补 `docs/design.md:56,73` | `design.md:191`（§3 接线点 5 列了两处）；且 5cc56b4 **真的改了这两行**（现为 `@<ref>` + 一句指向 §1.2 的提示）| ✅ 落地 |
| K7 | 登记 `sha256: null` 出口、裁定是否收紧 | `design.md:115-119`（§2 D2 末条）+ `design.md:162-164`（D6：明确**不**收紧）+ `design.md:240` | ✅ 落地；`initcmd.py` 的 `entry.get("sha256") and …` 我复核仍在 |
| K8 | 探针的落点/清理 | `design.md:62-82`（§2 D1 原始输出 + 「探针已全部清理（复查 404）」）+ `tasks.md:38-42`（3.0 含「落点」）| ⚠️ **落点成立**（远端 `probe/*` 确已删除，第 9 条证据），但「**已全部清理**」措辞超出了事实：本地仍留 `probe/workflow-ref` 分支与 `c7aa037`（低危观察 D4） |

**小结**：R1 的 8 条**全部已落进正文**（不是只落在那张表里）——这一条判据（收敛判据②）**满足**。
其中 K5 的「R1 自己错了」我独立复算**确认成立**（不是误订正）。

### C 与源码 / 文档事实核对（含实现面）

| 断言 | 我的实测 |
|---|---|
| `caller_workflow()` 不写 `with:`（改动前形态） | ✅ `@v1` 包真跑生成的 caller 只有 `name/on/permissions/jobs.gate.uses`（第 5 条证据的产物） |
| 「`--gate-ref` 只影响 `uses:`」（改动前） | ✅ 与包版本无任何联系（R1 的消费点全集我未逐条重 grep，采信其与 `gate.yml:57-59` 的一致） |
| (B′) 的上下文落点 | ✅ **官方文档逐字佐证**：`job.workflow_ref` 明写「job 直接定义在 workflow 文件里时**等同** `github.workflow_ref`」⇒ reusable 场景下不同；`on.workflow_call.inputs.<id>.default` 只允许 `github, inputs, vars` ⇒ `job.*` 只能进 step（`gate.yml:52-63` 正是这么写的） |
| 「走 `github.*` 会全量硬红」 | ✅ **机制侧独立复现**：把一个**不在本仓**的 40 位 sha 交给 `uvx` ⇒ `fatal: remote error: upload-pack: not our ref`（第 1 条证据末行） |
| `__version__` 恒 `0.1.0`、与 tag 无关 | ✅ `src/witnessloop/__init__.py:22`；`uvx …@v1 --version` 打 `witnessloop 0.1.0` |
| `checkcmd` 自报 = 尽力而为 | ✅ 源码直跑打 `<未知>`、退出码不变；纯函数 11 种畸形输入全不抛（第 6 条证据） |
| spec 的「畸形样本」fail-closed | ✅ 8 个 case 真跑，`refs/pull/N/merge` / 无 `@` / repo 不匹配 / 空 repo 全部 `::warning::` + `ref=v1`（第 2 条证据） |
| 升级动作的作用域不破坏「新仓已存在 caller ⇒ 冲突」 | ✅ **实测**：新仓 + 外来 caller + `--gate-ref` ⇒ EXIT=1、文件未动、policy 未写（第 4 条证据 E） |
| `design.md:148-151`（plain dry-run 退 1、只关 policy；seed ⇒ 幂等） | ✅ **逐字复算成立**（第 7 条证据） |
| issue #30 的「v1 ⇒ ✗10 / main ⇒ ✗1」 | ✅ 与**抓到的正文**一致（第 11 条证据）；数字本身（真 CI）我无法复算 |
| 「本 change 会自撞本仓门禁」 | ✅ 不成立：`check --base origin/main` ⇒ ✗4 项，**全部是「缺 manifest」**（含新出现的 grill-adversarial / building 两条），与 caller / policy / 台账无关（第 6 条证据） |
| `README.md:20` 的安装 ref 与包同源 | ✅ 5cc56b4 加了提示（`README.md:21-22`），但**字面量仍是 `@v1`**（A1 的附带面） |

### D 低危观察（**不是**必须修改项）

1. **Q4 的自报在「包还是旧的」时不存在**：`uvx --from …@v1 witnessloop check` 的输出里**没有** `本包来源` 那行（第 6 条证据）。
   这是鸡生蛋的自然结果，但 `docs/gate.md:77-79` 把它写成了读者**现在**就能看到的承诺。建议加半句「该行由新版包起才有」。
2. **兜底把 `refs/heads/x` 剥成 `x`**（`gate.yml:78-84`）：实测**未剥**的 `@refs/heads/main` 与 `@refs/tags/v1` 都能装（第 1 条证据），
   剥掉反而丢了「同名 branch/tag」的消歧。两种都可用，但 design 的措辞（「只接受 `refs/heads/<分支名>` 与 `refs/tags/<tag名>` 两种形态」）**没把剥不剥写死**，
   实现替他选了「剥」。建议明确。
3. **`installed_vcs_ref` 的 except 元组**是 `(ImportError, PackageNotFoundError, OSError, ValueError, TypeError)`：
   `importlib.metadata.distribution()` 在 sys.path 上有**别的包的坏 dist-info**（zip 损坏）时会抛 `BadZipFile`（`Exception` 子类），不在其中
   ⇒ `check` 会崩，入口兜底退 1（`entry.py:41`）——与 spec 的「SHALL NOT 因此改变退出码」相抵。**未复现**（纯推演，见「未验证项」）。
4. **「探针已全部清理」措辞超出事实**：本地仓仍留 `probe/workflow-ref` 分支与 `c7aa037`（第 9 条证据）。远端确已清理。
   建议措辞改成「远端已清理」（保留本地反而是好事——那是 Q1 唯一可追溯的物证）。
5. **Q 集合的机械门只判「候选小节里的 Q 都有确认」**：把 `### Q4` 挪到不相干小节 ⇒ **0 findings**（第 8 条证据）。
   所以 `tasks.md:14-15` / `design.md:249` 的「两份文件的 Q 集合 = {Q1…Q5} 逐条一致」**不是**机械判据，只靠人复核。
   （改名绕不过去：`## Open Questions 汇总` 被判「缺少该小节」，fail-closed ✅。）
6. **`spec.md` 第 5 条 Requirement（caller 不受保护要登记）没有机械钉子**：`docs/gate.md:455-476` 确实写了（我读了），
   但没有任何测试钉住那段文本 ⇒ 它退化成「靠人读」。与本仓对文档的既有态度（`tests/test_confirm_gate_docs.py` 之类）相比偏松。低危。
7. **`refs/pull/N/merge` 实测**：本仓该 ref 不存在（`refs/pull/1/merge` fetch 失败）。`spec.md:41` 的措辞已经**刻意只作定性**
   （「不是稳定的可安装 ref…不声称它必然安装失败」）⇒ 措辞是对的，我这次也没能把它测成「必然失败」。
8. **R2 的「全局行为变化」覆盖面被说小了一点**：`design.md:199`——「接入方把 `uses:` 指到含新 gate.yml 的 ref 时…所有这样的仓**同时**切换」。
   但**分支形态**（`uses: …@main`）的 caller 在**合并那一刻**就无声切换了包来源，接入方**零动作**。发布说明（`tasks.md:73-74`、`docs/gate.md:88-89`）
   应当点名这一类仓，否则「这是全局变化」这句话会被读成「只有动手的人受影响」。

---

## 未验证项

1. **`job.workflow_sha` / `job.workflow_repository` / `job.workflow_ref` 在 called workflow 里的运行期取值**——本工作区**没有可跑的 GitHub Actions**，
   仍**未验证**。**Q1 探针（run `38853369550`）无法复算**：那两次 run 的分支/文件已删，唯一载体是 `design.md §2 D1` 的粘贴块；
   我抓了 issue #30 正文，**里面没有那段 context dump** ⇒ 那是**单一来源、不可复现**的二手文本。
   - **我能给的旁证（正面）**：官方 contexts 文档对 `job.workflow_ref` 的表述（「job 直接定义在 workflow 文件里时等同 `github.workflow_ref`」）
     在 reusable 场景下**只能**解读成「指被复用的那个文件」；`job.workflow_sha` 的表述同样绑定「the workflow file that defines the current job」。
     ⇒ **Q1 的结论不依赖那份探针**：即便探针文本是伪造或误读，(B′) 仍有独立依据；被削弱的是「(B) 已被证伪」这半句。
   - **我能给的旁证（风险侧）**：`gate.yml` 的接受判据只看 `job.workflow_repository`，**不看 sha 属于哪个仓** ⇒ 它兜不住「`job.workflow_sha` 猜错了仓」这种错。
     但**失败模式是响亮的**：我把一个不在本仓的 sha 交给 `uvx` ⇒ `upload-pack: not our ref` 硬红（第 1 条证据）。
     **若假设相反会怎样**：若 `job.workflow_sha` 实为 caller 的 commit，则每个接入方的 gate 会**全量硬红**（不是静默吃旧包）；
     若 `job.workflow_ref` 的兜底形态与 GitHub 实际返回的形态不符（例如返回裸 `v1` 而非 `refs/tags/v1`），兜底会落到 fail-closed 吃 `v1`（响亮，有 warning）。
2. **探针里那两个 sha 的取值**（`6e2ec4dc…` = reusable 的 commit、`2778bc24…` = 接入方的 commit）：**取不到**（仓/分支已删）。
   **依赖它们的结论**逐条列出：① `design.md:62-79`、`design.md:261-263`、`spec.md:6-8`、`docs/gate.md:70-74`、`gate.yml:44-47` 的注释、
   `tests/test_gate_workflow.py:253-262` 的注释、`tasks.md:38-42` —— 这些**全部**在叙述「`github.workflow_sha` 是接入方自己的 commit ⇒ 用它会硬红」；
   ② 「(B) 已证伪」（`design.md:89-91`）整条。
   **若它们反了会怎样**：**行为不变**（实现只用 `job.*`、不用 `github.*`），但**文档会说反**——上述 7 处会变成假陈述（其中 3 处进了 repo 的正文/注释）。
   ⇒ 建议给这 7 处统一加一句「依据：不可复现的跨仓探针（见 §2 D1）+ 官方文档的 `job.workflow_ref` 定义」。
3. **GHES / 同 owner fork / 自建 runner 的 uv 版本差异 / `pip install git+…` 是否同样落 `vcs_info`**：全部**未验证**（只验了 uv 0.13.1 的 `uvx`）。
   `docs/gate.md:469-474` 已如实登记（含「GHES 接入方会一直吃 `v1`」）⇒ 这一条**不算缺口**。
4. **issue #30 里那两组 CI 数字（✗10 / ✗1）**：我只能核对「与抓到的正文一致」，**没法复算**（另一个仓 + 真 CI）。
5. **D3 的 BadZipFile 面**：**未复现**（推演）。若成立，`check` 会以退出码 1 结束（fail-closed，不是静默），但违反 spec 的「取不到不失败」。
6. **并发实现的时间差**：我快照的是未提交树，最终（`5cc56b4`）另有 `README.md` / `docs/*` 的改动；`src` / `gate.yml` / `tests` 我在快照与 HEAD 各核了一遍（内容一致）。
   若这个 worktree 在我写报告之后又被改动，本报告的行号需按 blob 哈希重核。

---

## 必须修改项

> 每条带证据（`文件:行号` 或命令 + 真实输出）。**非纯措辞**的在前。

- **L1（计划面 · 非措辞）post-merge 时序必须反过来，否则 `tasks.md §6` 执行完 Q3 的收益仍然落空。**
  证据：`tasks.md:69`（6.1 先建 tag，明确「指向…含本 change 的那个 commit」）→ `tasks.md:70`（6.2 后改 `DEFAULT_GATE_REF`）；
  `git show 5cc56b4 -- src/witnessloop/constants.py | grep DEFAULT_GATE_REF` ⇒ 无命中（常量仍是 `@v1`）；
  `README.md:20` 的安装字面量仍是 `@v1`；实测 `@v1` 的 CLI 生成 `uses: …@v1`。
  改法：让**被 tag 的那个提交**含有常量改动（6.2 → 6.1 或 6.1 改指向），并把 `README.md:20` 的**新值**写进 §6（现在 §6 完全没提它）；
  顺带在 `README.md:181-192` 加一句「`v1.7.0` 发布前请仍钉 `@v1`」（§6.5 不动 v1 与 6.1 之间必然存在这个窗口）。
  验收命令（可复算）：`uvx --from "git+…@v1.7.0" witnessloop init --root <scratch> --dry-run` 的 caller 行 SHALL 逐字为 `…@v1.7.0`。
- **L2（文档/入口 · 非措辞）升级 recipe 必须补「先升 CLI」这一步。**
  证据：`docs/gate.md:81-87`、`README.md:191-192` 把 `init --gate-ref <新>` 写成升级动作；
  实测（`README.md:20` 让装的 `@v1` 包）⇒ `EXIT=1`，`init：检测到冲突（…要更换 policy 请先 uninit）`。
  改法：`docs/gate.md §1.2` + `README.md` 的 recipe 第一步写 `uv tool install git+…@<新 ref>`，并如实登记旧 CLI 的症状（否则人跑去删 policy）。
- **L3（缺钉子 · 非措辞）给 `inputs.witnessloop-ref.default == ""` 加一条测试。**
  证据：`grep -rn "witnessloop-ref" tests/` ⇒ 只有 `tests/test_gate_workflow.py:330` 的 env 绑定，没有任何 `default` 断言；
  把 `.github/workflows/gate.yml:23` 改回 `default: "v1"` 时机制静默退化（我把 `WL_INPUT_REF=v1` 喂进真 step ⇒ `ref=v1` +
  `::notice::…（来源：调用方显式传入的 with.witnessloop-ref）`，即原缺陷 + 一条误导性日志），而 665 条测试全绿。
- **L4（语义待写死 · 非措辞）把「`--gate-ref` + 冲突 `--policy`」的退出码与落盘顺序写进 spec/§5.3。**
  证据：实测 `init --gate-ref <新> --policy <冲突>` ⇒ `EXIT=1` 且 `caller rewritten: True | ledger synced: True`；
  现状自洽（两条轴都改了、只剩 policy 一条红），但文档未定义；建议明确「先写 caller+台账、后判其余，失败**不回滚**」（与 `--test-command` 的 Z1/O2 先例同口径），
  并把「要换 policy 请先 `uninit`」的文案在这个组合下改成不误导的说法。
- **L5（spec 补 Scenario · 半措辞）升级 Requirement 补两条场景**：① `--dry-run --gate-ref <新>` ⇒ 不落盘、且**不得**说「幂等，无改动」；
  ② 台账 `created_files` 里**没有** caller 条目时 ⇒ 补条目并同步（实现两者都已按合理语义做：实测 dry-run 不落盘且 note 如实、
  缺条目 ⇒ EXIT=0 且插入到 `self` 之前）。要求既已定稿，就把这两条钉进 `specs/gate-ref-pinning/spec.md:82-102`。
- **L6（发布说明覆盖面 · 措辞）全局面的描述要覆盖「分支形态 caller」。**
  证据：`design.md:199`、`docs/gate.md:88-89`、`tasks.md:73-74` 都把全局面写成「接入方把 `uses:` 指过去的那一刻」；
  但 `uses: …@main` 这类 caller 在**合并那一刻**就零动作切换包来源。

---

## Open Questions

> 只放真需要用户拍板的。其余（含 L1 的时序、L2 的前置条件）我已在正文给依据并**移出**。

**Q1（本轮新增）`--gate-ref` 与冲突的 `--policy` 同时给出时，`init` 应该「先写后判、退 1 且不回滚」还是「两轴一起不落盘」？**

- 事实（实测）：现在落在**前一种**——`EXIT=1`，但 caller 与台账**已经改写**（L4 的证据）。现状态自洽（没有「磁盘 ≠ 台账」的分叉态），
  可复算恢复路径也简单：把 policy 那条轴单独解决（`uninit` 后重来）即可。
- 具体例子（接入方 B）：B 想「换 ref」**并且**「换一份定制 policy」。今天他会看到：两件事只做成了半件、退出码说失败。
  他不知道该重跑什么（重跑 `--gate-ref` 已无改动、`--policy` 仍冲突）。
- **推荐**：**保持现状（先写后判、不回滚）+ 把文案改准**。理由：① 与 `--test-command` 的既有先例同口径（`initcmd.py` 的 Z1/O2 注释明写「写在前、其余判定照旧参与退出码」）；
  ② 改成「两轴一起不落盘」会把 caller 轴也拖进 `--policy` 的判定，反而让「换 ref」这个本 change 的**主**入口被一个**正交**参数连坐；
  ③ 现状不产生分叉态，恢复路径单一。
- 需用户拍板的原因：这改的是 `init` 的**契约面**（「只增不改」的边界），不是纯实现细节。

---

## 收敛结论

**不收敛。**

两条判据**①不满足、②满足**：

1. **① 不满足：本轮有新的可证伪项（不是措辞/计数/格式），且已实测**：
   - **L1/A1**：`tasks.md §6` 按字面执行 ⇒ 打出的 `v1.7.0` 里 `DEFAULT_GATE_REF` 仍是 `@v1` ⇒ 「新接入方默认吃到新包」落空（常量未改有 `git show` 证据；`@v1` CLI 生成 `@v1` 有实跑证据）。
   - **L2/A2**：文档写的「单一升级动作」在 README 让装的 CLI 上 **EXIT=1** 且文案误导（实跑，`@v1` 真包）。
   - （另有 3 条**新缺口**但严格说不是「证伪」：L3 缺 input default 的钉子、L4 组合语义未写死、L5 spec 缺两条场景。）
2. **② 满足：R1 的 K1–K8 全部已落进正文**（见「对抗结论 B」逐条表；其中 K5 我复算确认是 R1 自己错，订正成立）。

**本轮证伪失败（= 既有结论成立）的部分也一并记明**，避免读者以为全盘被推翻：
(B′) 的上下文落点（`job.*` + step）有**官方文档逐字**支撑；`uvx` 对 40 位 sha / 分支 / tag / `refs/heads/*` / `refs/tags/*` / 带斜杠分支**全部可用**（8 种形态实跑）；
解析 step 的 8 个 case **行为级**符合 spec 的 Scenario；升级路径的终态**是不动点**（plain `init` 幂等、`uninit` 可用）；
作用域守卫**没有**打破「新仓已存在 caller ⇒ 冲突且整体不落盘」；`check` 自报**从不因取不到元数据而失败**；`design.md` §2 D4 的两条实跑事实**逐条成立**；
`(B′)` 下 `caller_workflow()` 字节不变的冻结测试**仍在且通过**。

**下一轮该先做什么（按序）**：

1. **先改 L1/L2**（都在 `tasks.md §6` / `README.md` / `docs/gate.md §1.2`）：把「改 `DEFAULT_GATE_REF` 的提交」放到被 tag 的提交上、把 `README.md:20` 的新值写进 §6、
   给升级 recipe 补「先升 CLI」与「发布前仍钉 `@v1`」。**这三处不改，本 change 的核心收益在发布那一刻仍然交付不了。**
2. **再补 L3 的钉子测试**（一条断言，成本最低、防的是中央机制的静默回归）。
3. **然后 L4/L5 把语义写死**（改 `initcmd.py` 注释 + `spec.md` 两条 Scenario）；L6 一句话。
4. 最后重跑一轮对抗：**下一轮应能收敛**——剩下的面（GHES/fork/自建 runner、`refs/pull` 可安装性、`job.*` 运行期取值）都是**已如实登记且本工作区不可验证**的，不应再作为「必须修改项」出现。

---

## 处置（主 session 在 R2 之后追加，非审阅者原文）

> 本报告判定**不收敛**（①不满足、②满足）。L1–L6 与低危观察 D1/D2/D3/D4/D6 **已逐条落库**，
> 落点见 `design.md §7.9` 的「R2」表。**下一轮（R3）对象是回写之后的树。**

- **L1**：`tasks.md §6` 整段重写——**先改 `DEFAULT_GATE_REF` 再到含该改动的提交上打 tag**；
  补 `README.md:20` 的新值进动作清单；补 6.7 的可复算验收命令；补「`v1.7.0` 发布前仍钉 `@v1`」。
- **L2**：`docs/gate.md §1.2` 与 `README.md` 的 recipe 改成**两步**（① 先升 CLI ② 再换 ref），
  并如实登记旧 CLI 的 EXIT=1 与那条把人指向 policy 的误导文案。
- **L3**：`tests/test_gate_workflow.py::test_witnessloop_ref_input_default_is_empty`。
- **L4**：`spec.md` 新增组合语义 Scenario；`initcmd._already_initialized` 在冲突文案前点明
  「caller 已落盘、不回滚」；`tests/test_init_gate_ref.py` 的钉子。
- **L5**：`spec.md` 补「`--dry-run`」与「台账缺 caller 条目」两条 Scenario。
- **L6**：`design §4 R2`、`docs/gate.md §1.2`、`tasks.md 6.5` 三处点名**两类**受影响的仓。
- **D1/D2/D3/D4/D6**：见 `design.md §7.9` 的对应行。**D5**（Q 集合的机械门可被「搬小节」绕过）
  与本报告都**如实登记、本 change 不修**（属 `evidence.py` 的机制面）。

### 对 R2 的 Open Question Q1 的处置（**作者按你的推荐落库，非用户拍板**）

**采纳推荐 = 保持现状（先写后判、不回滚）+ 把文案改准**，理由即你正文给的三条
（与 `--test-command` 先例同口径；「两轴一起不落盘」会让主入口被正交参数连坐；现状不产生分叉态）。
⚠️ 这是**本 change 里唯一一条由独立审阅推荐、作者落库、而未经用户逐字拍板的契约面语义**——
已写进 `spec.md` 的 Scenario，可复核、可回退（面 = 一条 Scenario + `initcmd` 的落盘顺序）。
