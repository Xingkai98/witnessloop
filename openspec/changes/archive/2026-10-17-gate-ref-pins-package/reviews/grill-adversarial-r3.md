# Grill（对抗轮 R3）：gate-ref-pins-package —— 独立零记忆证伪

## Reviewer

我是**独立零记忆**的对抗验证者（本对话不携带该 change 的任何历史）：`proposal.md` / `design.md` / `tasks.md` /
`specs/gate-ref-pinning/spec.md` 与三份 review 里的「实测」「文件:行号」「已落库」「已收敛」一律当**待验证断言**，
可复算的一律复算，**目标是证伪结论本身**。

**基准 revision（重要——本轮 HEAD 被并发移动过三次）**

- 会话开始：`6813c8e`；审阅进行中先后变成 **`9fcb970`**、**`37ab466`**（主 session 在我审阅期间并发落库，
  第三次的 commit message 直接点名「对抗轮 R3 已暴露的三条 M1/M2/M4」——说明我此前的中间结论已被消费）。
- **本报告的行号与 blob 一律以 `37ab466` 为准**：

  | 文件 | blob |
  |---|---|
  | `HEAD` | `37ab466c8e27416b776798e582f4901c9b42642d` |
  | `openspec/changes/gate-ref-pins-package/tasks.md` | `27c805c9…` |
  | `…/design.md` | `4b4d21e9…` |
  | `…/specs/gate-ref-pinning/spec.md` | `2d98ab66…` |
  | `…/proposal.md` | `903714c3…` |
  | `src/witnessloop/constants.py` | `b4f71ea6…` |
  | `src/witnessloop/initcmd.py` | `d706fbe5…` |
  | `src/witnessloop/checkcmd.py` | `90be88ec…` |
  | `src/witnessloop/policy.py` | `2db8c312…` |
  | `.github/workflows/gate.yml` | `f2ff6bf5…` |
  | `tests/test_gate_workflow.py` | `db88375d…` |
  | `tests/test_init_gate_ref.py` | `0f1618a2…` |
  | `docs/gate.md` / `README.md` | `154e1622…` / `b6e574c2…` |

- **仓内除本报告外零改动**；全部实验在 `/tmp/adv3/`（`pristine`/`cur` = 工作树快照，`repoA`/`repoC` = 变异副本，
  `e5`~`e13` = 模拟仓与产物，`v1tree` = `git archive v1` 解出的旧包）。

**实际跑了（命令 + 原始输出要点）**

1. **基线**：`PYTHONPATH=src python3 -m pytest -q`（在 `37ab466` 的工作树快照上）⇒ **672 passed**。
2. **L3 的钉子真去踩**：把 `.github/workflows/gate.yml` 的 `witnessloop-ref.default` 改回 `"v1"` ⇒
   `pytest tests/test_gate_workflow.py -q` ⇒ **1 failed, 28 passed**，红的正是
   `test_witnessloop_ref_input_default_is_empty`（`AssertionError: assert 'v1' == ''`）。⇒ **L3 落实且有效**。
3. **tasks §6.1 按字面执行**（`constants.py:21` → `@v1.7.0`、`gate.yml:60` `WL_FALLBACK_REF` → `"v1.7.0"`、
   `tests/test_gate_workflow.py:59` → `@v1.7.0`；第 4 条已解耦）⇒ `pytest -q` ⇒ **5 failed, 667 passed**，
   全在 `tests/test_init_gate_ref.py`（详见 A1）。对照：同一实验在 `9fcb970`（未含这次修复）上是 **6 failed**。
4. **tasks §6.7 的验收命令**：`init --root <scratch> --dry-run` ⇒ 输出**只有文件清单**（
   `[dry-run] init 将创建…` + 四行 `+ …`），`… --dry-run | grep -c "uses:"` ⇒ **0**。
5. **组合语义（L4）**：`init --gate-ref <新> --policy <冲突>` ⇒ `EXIT=1`，stderr 首行
   `init：注意——.github/workflows/witnessloop.yml 已按显式 --gate-ref 处理（**已落盘、不回滚**）；下面报的是别的文件：`，
   caller 与台账**确已改写**（`gate_ref=…@v9.9.9`）。
6. **组合语义 × dry-run**：同一条命令加 `--dry-run` ⇒ stdout 说「`[dry-run] 将重写…`」，stderr 却仍说「**已落盘、不回滚**」——
   而磁盘与台账**一个字节都没动**（实测复核）。
7. **旧 CLI（真 v1 树，`git archive v1`）**：`init --gate-ref …@v1.7.0` ⇒ **EXIT=1** +
   `init：检测到冲突（…要更换 policy 请先 uninit）`，且 `grep -c sync_caller_gate_ref` = **0** ⇒ L2 的前提成立。
8. **`--version` 能不能区分新旧 CLI**：当前树与 v1 树都打 `witnessloop 0.1.0`（同值）；
   `init … | grep -ci "ref|commit_id|来源"` ⇒ **0**（详见 A2）。
9. **`uv tool install` 语义（拿真 uv 0.13.1，源码用本地 git 仓替代 GitHub，避免外发）**：
   ① 装 `@v1` ⇒ 命令打 `MARK-A`；② **不带** `--force` 装 `@v2` ⇒ uv 自己先 `-` 后 `+` **替换成功**；
   ③ `--force` 装 `@v2` ⇒ `MARK-B`。⇒ `--force` **不是**必要条件，但确实会替换（L2 的前置条件成立）。
   另：`uv tool install` 装出来的包**也**带 PEP 610 —— `direct_url.json` =
   `{"url":"file:///…","vcs_info":{"vcs":"git","commit_id":"facca298…","requested_revision":"v2"}}`。
10. **孤儿报告链**（模拟仓 `/tmp/adv3/e7`，与本 change 同构）：`reviews/` 放 5 份 `.md`、只建三份 stage manifest ⇒
    `check` 报 2 条 `孤儿报告`；再补一份 **同 stage** 的 manifest ⇒ 它**覆盖**了同名文件，孤儿变成**另一组**（见 A3）。
    每份报告各配一份、**多出的轮次用不同 stage 名**（`grill-adversarial-r2`/`-r3`）⇒ **0 条孤儿**。
11. **不变集 × `M`**：在 base 已含 manifest 的分支上改一份 `**/reviews/*.manifest.json` ⇒
    `check` 报 `…受保护路径被写入，但没有结构化解释事件（需 workflow-events.jsonl …）`。
    源码依据：`policy.py:19-23` 的不变集合该 glob，`checkcmd.py:385` 的「不变集 + `A` ⇒ 免事件」只对**新增**成立。
12. **revision 绑定**：在 base 已含 manifest 的分支上改一个**非证据**文件 ⇒ 三份 manifest 各报
    `审阅的是旧 revision：head_sha=… 之后又改动了非证据文件：…`（依据 `contract.py:683-688` / `:758`）。
13. **本仓自证**：`check --root . --base origin/main --head HEAD` ⇒ **未通过 ✗（4 项）**，全部是「缺 manifest」类
    （缺 manifest / 缺 grill / 缺 grill-adversarial / 缺 building），与 caller / policy / 台账无关。
14. **远端 tag 清单（只读 `git ls-remote --tags origin`）**：最大 = **`v1.6.0`**，`v1.6.0^{}` = `ae99256…`
    ⇒ **不存在 `v1.7.0`**（6.7 与 README 的「还不存在的 ref」窗口成立）。
15. **`guard` / `manifest build` 不自报包 ref**：`grep -rn "_report_package_source|installed_vcs_ref" src/` ⇒
    唯一定义在 `checkcmd.py:55/76`、唯一调用在 `checkcmd.py:96`（`run()` 第一件事）。

**没能复算的**：见「未验证项」——真 CI 的 `job.*` 运行期取值与 Q1 探针原始输出、GHES/fork/自建 runner、
真 `git+https://github.com/…@v1.7.0` 那条命令（tag 尚不存在）、issue #30 的两组 CI 数字。

---

## 对抗结论

### A 本轮新证伪 / 新缺口（非措辞）

**A1（新证伪 · 高）`tasks.md §6.1` 的「字面量族」仍缺第 5 处 ⇒ 逐字执行它** 仍留 5 条红，而红的原因与被测行为无关。**

- 证据：按 `tasks.md:74-88` 的四条逐字执行（① `constants.py:21`、② `gate.yml:60` `WL_FALLBACK_REF`、
  ③ `tests/test_gate_workflow.py:59`；④ 已由 `_fallback_ref()`（`tests/test_gate_workflow.py:277-283`）解耦，
  它自己也这么写了）⇒ `PYTHONPATH=src python3 -m pytest -q` ⇒ **5 failed, 667 passed**，
  全部落在 `tests/test_init_gate_ref.py`：
  `test_explicit_different_ref_rewrites_caller_and_syncs_the_ledger` /
  `test_rewrite_rescues_a_hand_edited_caller` / `test_dry_run_previews_without_writing` /
  `test_explicit_gate_ref_plus_conflicting_policy_writes_then_reports` /
  `test_dry_run_must_not_claim_it_wrote_anything`。
- 根因（一行）：`tests/test_init_gate_ref.py:24-25` 的 `NEW_REF = "…gate.yml@v1.7.0"` 与 6.1 之后的新
  `OLD_REF = C.DEFAULT_GATE_REF` **同值** ⇒ `sync_caller_gate_ref`（`initcmd.py:166`）判「台账里记的就是这个 ref」
  直接 `return None` ⇒ 这五条用例的前置（「换成一个不同的 ref」）整条塌掉。
  `test_dry_run_must_not_claim_it_wrote_anything` 那次尤其误导：它断言的是 M4 的语义（「不许说已落盘」），
  红的原因却是 ref 相同 ⇒ 输出里既没有「未落盘」也没有「已落盘」。
- 改法：`NEW_REF` 换成**不等于当前默认值**的 ref（如 `…@v1.8.0`），或把 `tests/test_init_gate_ref.py:24`
  补进 6.1 的清单（它是第 5 处，不是第 3/4 处的重复——第 4 处只覆盖 `test_gate_workflow.py` 内部）。
- 说明：这一族**确实在收缩**（`9fcb970` 上同一实验 6 红 → `37ab466` 上 5 红），但**还没合上**；
  「6.1 只改一处会让 7 条测试红」这句在 `tasks.md:75-76` 里的自述也仍然偏小（按修复后的版本是 5）。

**A2（新证伪 · 中）「先升 CLI」这一步**无法自证**：现有 CLI 没有任何出口能告诉你它是从哪个 ref 装的，而文档让人「先确认 CLI 版本」。**

- 证据：`--version` 对**两个不同的包**给出同一个值——当前树 `PYTHONPATH=src python3 -m witnessloop.cli --version`
  ⇒ `witnessloop 0.1.0`；v1 旧树同命令 ⇒ `witnessloop 0.1.0`（这正是 `design.md §2 D3` 自己写的
  「`__version__` 恒 `0.1.0`、**与 tag 无关**」）。`init` 也**不自报**：`init --root … | grep -ci "ref|commit_id|来源"` ⇒ **0**。
- 而 `docs/gate.md §1.2`（`docs/gate.md:96-98` 一段）在旧 CLI 的 EXIT=1 之后写「看到这条又来路不明时，**别去删 policy**，
  **先确认 CLI 版本**」——**没有给确认手段**，且按现有出口**确认不了**。
- 唯一可行的确认口是 `check` 的第一行（`checkcmd.py:76-79`；实测在**未接入**的空目录也打：
  `check：本包来源（自报，尽力而为）：requested_revision=<未知>，commit_id=<未知>`），
  但 README 的两步 recipe（`README.md:189-196`）里没有这一步，也没说「跑 `check` 看那一行」。
- 正面补测（说明「能力有、缺的是文档那一步」）：`uv tool install` 装的包**也**带 PEP 610 `vcs_info`
  （见 Reviewer 第 9 条实跑）⇒ 装了新 CLI 之后 `check` 那一行会打出真值（`@v1.7.0` 时即
  `requested_revision=v1.7.0`）—— **只要有人告诉用户去看它**。
- 建议：在两步 recipe 的 ① 之后补一步可复算自查（`witnessloop check --root . | head -1`），
  或让 `init` 也打一行同款自报（但那是 `initcmd` 的新能力，属另一条取舍）。

**A3（新缺口 · 中）`reviews/` 每多一轮对抗报告就多一条孤儿报告，而 `manifest build` 的落盘名是 `<stage>.manifest.json` ⇒ 同 stage 会**静默覆盖**。**

- 证据（模拟仓 `/tmp/adv3/e7`，与本 change 同构：`reviews/` 放 5 份 `.md`、建 `grill`/`grill-adversarial`/`building`
  三份 manifest、`check --base main --head HEAD`）：
  ```
  1. …/reviews/grill-adversarial-r2.md：孤儿报告：reviews/grill-adversarial-r2.md 未被任何 manifest 绑定
  2. …/reviews/grill-adversarial-r3.md：孤儿报告：reviews/grill-adversarial-r3.md 未被任何 manifest 绑定
  ```
  再补一次 `--stage grill-adversarial --report reviews/grill-adversarial-r2.md` ⇒ `ls` 显示
  `grill-adversarial.manifest.json` **只有一份**（把前一份覆盖了），孤儿随之变成 **r1 + r3`**。
- 可行的做法（我验过、**0 条孤儿**）：**每份报告各配一份 manifest，多出来的轮次用不同的 stage 名**
  （`grill-adversarial-r2`/`-r3`）。`check` 只要求三个必备 stage **各存在**，不排斥额外 stage。
- **本 change 自己就踩这条**：`reviews/` 现 3 份 `.md`（`grill-design` / `grill-adversarial` / `grill-adversarial-r2`），
  加上 `tasks.md:64`（5.1）的 `building-review.md` 与**本报告** ⇒ **共 5 份**，而
  `docs/gate.md:194-204` 的指引是「`manifest build` 因此要**对每个报告各跑一次**」、例子只给到两个 stage
  —— 按它照抄**会**得到孤儿；`tasks.md` / `design.md` 通篇没有这一步。
- 附带：`docs/gate.md:268` 只写「写 `reviews/<stage>.manifest.json`」，**没写**「同 stage 会覆盖」这条陷阱。

**A4（新证伪 · 中）`tasks.md:87-88` 那句「revision 绑定允许『本 PR 自己的变更 + 证据文件』落在 manifest 的 `head_sha` 之后」与机制**相反**。**

- 机制（`contract.py:683-688`）：「`head_sha` 必须是被检 head 的**祖先**，且从 `head_sha` 到被检 head 之间
  **只允许出现证据文件**」。实测复核：在 base 已含 manifest 的分支上改一个**非证据**文件
  （`openspec/changes/tc/design.md`）⇒ 三份 manifest 各报一条
  `审阅的是旧 revision：head_sha=025aeb13… 之后又改动了非证据文件：openspec/changes/tc/design.md`。
- ⇒ 成立的只有「**证据文件**落在 `head_sha` 之后」这半句；「本 PR 自己的变更」（非证据）落在之后**正是**这条规则禁止的。
  这句话落在 6.1（post-merge 重建 manifest 的操作说明）里，是执行者会照着做的地方，属**可执行的错误陈述**。

### B 逐条核 R1 的 K1–K8 是否真的落进正文 / 实现

> 判据：去正文与代码里核，不核 `design.md §7.9` 那张自述表。

| # | R1 要求 | 落点（`37ab466` 实核） | 判定 |
|---|---|---|---|
| K1 | 删/改「包无法自报 ref」 | `design.md §2 D3`（`design.md:134-152` 整段重写，含「R1 K1 订正（原稿此处为假）」）+ `spec.md:58-70` 的新 Requirement + `design.md:247` 表格行 | ✅ 落地 |
| K2 | 改「没有任何提示」 | `proposal.md:19-29` 整段改写（标题即「『没有任何提示』是**假**的（R1 K2 实测证伪）」） | ✅ 落地 |
| K3 | 「永久死锁」降级 | `design.md:107-127`（§2 D2：「响亮、可恢复的分叉态」+ 三条恢复路径 + `check` 不读台账） | ✅ 落地 |
| K4 | 自证行在 (A) 下自相矛盾 | `design.md:154-169`（§2 D4：本 PR 不做本仓迁移） | ✅ 落地 |
| K5 | 「47 个提交」计数 | `design.md:250-251` 的 K5 行给出「测量哪个 ref」的复算；正文已去计数 | ✅ 落地（R2 的判定我复核一致：`v1..origin/main` = 47，陈旧本地 `main` = 0，本仓两分支都落后 `origin/main`） |
| K6 | 补 `docs/design.md:56,73` | 两处均已改（`docs/design.md:56` 保留**历史引文**「`@v1`」、`:73` 改成 `@<ref>`），且 `tasks.md:49` 记了 | ✅ 落地 |
| K7 | 登记 `sha256: null` 出口 | `design.md:128-132`（§2 D2 末条）+ `design.md:175-177`（D6：明确不收紧） | ✅ 落地 |
| K8 | 探针落点 / 清理 | `design.md:62-95`（§2 D1 原始输出 + 措辞改成「**远端**已清理…**本地仍留** `probe/workflow-ref`」）+ 证据等级标注；实测 `git branch -a` 仍见 `probe/workflow-ref` ⇒ 措辞与事实一致 | ✅ 落地 |

**小结：K1–K8 全部落在正文/实现里**（不是只落在那张表里）⇒ 收敛判据②的 R1 那一半成立。

### C 逐条核 R2 的 L1–L6 是否真的落进正文 / 实现

| # | R2 要求 | 落点（`37ab466` 实核） | 判定 |
|---|---|---|---|
| L1 | post-merge 时序反过来 | `tasks.md:69-72` 的警示 + `:74`（先改常量）+ `:95`（再 tag「含 6.1 改动」的 main）+ `:97-98`（README:20 进清单）；✔️ 时序**自身**正确（tag 的那个提交已含常量） | ✅ 落地，但带两个新洞（**A1**、**A4**）与一条命令错误（原 6.7，已被 `37ab466` 改成 A5 里的新形态） |
| L2 | recipe 补「先升 CLI」 | `docs/gate.md §1.2`（`docs/gate.md:83-99`：两步 + 旧 CLI 的 EXIT=1 与误导文案 + 「别去删 policy」）+ `README.md:189-196` | ✅ 落地，但**前置条件不可自证**（**A2**） |
| L3 | 给 `inputs.witnessloop-ref.default == ""` 加钉子 | `tests/test_gate_workflow.py:464` `test_witnessloop_ref_input_default_is_empty`；**我实踩**：改回 `"v1"` ⇒ 该条红、其余 28 条绿 | ✅ 落地**且有效** |
| L4 | 写死「`--gate-ref` + 冲突 `--policy`」的组合语义 | `spec.md:118-124` 的新 Scenario + `initcmd.py:448-449`（`handled` 文案）+ `tests/test_init_gate_ref.py:208-233` | ✅ 落地（真跑时文案出现）；dry-run 分叉那句是 `37ab466` 新加的（见 D 表） |
| L5 | spec 补两条 Scenario | `spec.md:104-109`（`--dry-run` 只预览、不许谎报幂等）+ `spec.md:111-116`（台账缺 caller 条目） | ✅ 落地 |
| L6 | 全局面点名**两类**仓 | `design.md:212`（§4 R2）+ `docs/gate.md:107-110` + `tasks.md:100-103`（6.5） | ✅ 落地 |

**小结：L1–L6 全部落库**（判据②的另一半也成立）。**但（A1/A4）说明 L1 的修法自身还没闭环。**

### D 与源码 / 文档核对（含本轮并发落地的复核、本仓门禁自洽）

| 断言 | 我的实测 |
|---|---|
| `gate.yml` 解析 step 用 `job.*` 不用 `github.*` | ✅ `gate.yml:56-58` + `tests/test_gate_workflow.py:339-342` 钉住 |
| 解析 step 是 job 的第一个 step、且 `run:` 里无 `${{ }}` 插值 | ✅ `tests/test_gate_workflow.py:324-326`、`:344`；`${{` 只出现在 `env:` 值里 |
| input `default: ""`（中央机制） | ✅ `gate.yml:23`；L3 的钉子已实踩 |
| 解析 step 对**未定义** env 的健壮性 | ✅ 已落（`gate.yml:72-90` 一律 `${VAR:-}`；`tests/test_gate_workflow.py:480` 的钉子把四个键 `pop` 掉再交 `sh` 跑）。**对「真实 GitHub 会不会出现未定义」我的判断**：`env:` 的值即使取不到上下文也会渲染成**空串**（键仍在），所以 `set -u` 在真 CI 上不会因此开火——这是**纵深防御**而非修一个真 CI 见过的红（这一点 `gate.yml:69` 的注释里也是这么写的，措辞已如实）。 |
| `init --gate-ref` 重写 caller + 同步台账 | ✅ 实测 `EXIT=0`、caller 与 `gate_ref` 同步、随后 plain `init` 幂等（`tests/test_init_gate_ref.py` 全绿） |
| 作用域只在「已接入分支」 | ✅ `initcmd.py:286-298`；`test_foreign_caller_in_a_new_repo_still_conflicts` 绿 |
| 组合语义的「先写后判、不回滚」 | ✅ 实测（Reviewer 5） |
| **`--dry-run` 版本的那句话** | ✅ `37ab466` 已修：`initcmd.py:298-303` 按 `args.dry_run` 分叉成「**dry-run：未落盘**」/「**已落盘、不回滚**」；`tests/test_init_gate_ref.py:235-262` 钉住。我实跑复核：dry-run 下 stderr 不再出现「已落盘」 |
| `check` 自报 | ✅ `checkcmd.py:76-79` + `run()` 第一句（`:96`），任何分支都吞不掉；取不到打 `<未知>` 且不改退出码（宽 `except Exception`，`checkcmd.py:62-73`） |
| `guard` / `manifest build` **不**打自报行 | ✅ 实测（Reviewer 15）。**不算违规**——spec 只对 `check` 提 SHALL；但 `docs/gate.md §8` 说 guard「与 check 共用同一个判定」，读者可能以为自报也共用 ⇒ 低危措辞面，见 E3 |
| 「本 change 自撞本仓门禁」 | ✅ 不成立：`check --root . --base origin/main --head HEAD` ⇒ **✗4，全部是「缺 manifest」类**（含新出现的 grill-adversarial / building 两条），与 caller/policy/台账无关 |
| 同源文档清单（`@v1` 当当前值写的） | ✅ `grep -rn` 复核：`README.md:20`（6.3 已列入）、`docs/design.md:56`（历史引文，按新 6.1 的显式规则**保留**）、`docs/design.md:73` 已改 `@<ref>`；`templates/`、`plugin/` 仍零命中 |
| `README.md:20` 的字面量仍是 `@v1` | ✅ 仍是（6.3 是 post-merge 事项 ⇒ 与 Q3 一致，**不算**缺口；且 `README.md:201` 已写「v1.7.0 发布前请仍钉 @v1」） |
| 远端不存在 `v1.7.0` | ✅ `git ls-remote --tags origin` 最大 = `v1.6.0`（`v1.6.0^{}` = `ae99256`）⇒ 6.7 与 README 的窗口描述成立 |

### E 低危观察（**不是**必须修改项）

1. **6.7 的 `grep -n` 前缀**：`tasks.md:108` 用 `grep -n 'uses:'`，实际输出带行号前缀
   （我实跑：`14:    uses: Xingkai98/witnessloop/.github/workflows/gate.yml@v1`），
   而 `tasks.md:110-111` 说「那一行 SHALL **逐字**是 `    uses: …`」⇒ 逐字比对会差一个 `14:`。
   建议 `grep -h` 或 `sed -n '/uses:/p'`。（命令**结构**已可复算，所以只记低危。）
2. **6.7 的第二条自查依赖 `check` 能在非 git 目录里打出自报行**：`check --root /tmp/wl-v17 --base main --head HEAD` 里
   `/tmp/wl-v17` 不是 git 仓，但自报行在 `run()` 第一句、先于任何 git 操作 ⇒ 会打出来（我实测在空目录也打）。
   措辞「SHALL 有 `requested_revision=v1.7.0`」成立（PEP 610 的 `requested_revision` 就是被请求的 ref）。
3. **`docs/gate.md §8` 说 guard「与 `check` 共用同一个判定」，但包 ref 自报不共用**（guard/manifest build 都不打）。
   spec 没要求，属读者预期面。
4. **`uninit` 的 diff 文案**：`render_diff` 的 `tofile` 恒为「（witnessloop init 将写入）」，在 `uninit`（其实是**删除**）
   语境下会误导；实测手改 caller 后 `uninit` 打出 `- uses: …@v2` / `+ uses: …@v1`，看上去像「要改回 @v1」，
   而正确动作是 `init --gate-ref @v2` 同步台账（现在文档已引导）。R1 E5 / `design.md R7` 已记，**仍是现状**。
5. **`WL_FALLBACK_REF` 的语义会随 6.1 漂移**：`tests/test_gate_workflow.py:354` 把 fail-closed 落点与
   `DEFAULT_GATE_REF` 的 ref 部分**钉成同源** ⇒ 6.1 之后它会变成 `v1.7.0`，而
   `spec.md:17-18,44`、`design.md:47`、`docs/gate.md §7.1`、`gate.yml:39` 的注释都写「退 **v1**」。
   新 6.1 只列了「改 `gate.yml` 的字面量」，**没列**这些随之作废的措辞 ⇒ 见「Open Questions Q1」。
6. **`probe/workflow-ref` 本地分支仍在**（`git branch -a` 实测）——`design.md:82-83` 已如实写成「本地仍留」，
   属**已登记**，不是缺口。

---

## 未验证项

1. **`job.workflow_sha` / `job.workflow_repository` / `job.workflow_ref` 在 called workflow 里的运行期取值**，
   以及 **Q1 探针（run `38853369550`）的原始输出**：本工作区**没有可跑的 GitHub Actions**，那两次 run 的分支/文件已删，
   唯一载体是 `design.md:65-81` 的粘贴块 ⇒ 仍是**单一来源、不可复现**的二手文本。
   - **若假设相反会怎样**：若 `job.workflow_sha` 实为 caller 的 commit，则每个接入方的 gate 会**全量硬红**
     （不是静默吃旧包）；若 `job.workflow_ref` 兜底形态与 GitHub 实际返回的不符（例如返回裸 `v1`），
     兜底会落到 fail-closed 吃 `v1`（**响亮、有 warning**）。实现只用 `job.*`、不用 `github.*` ⇒ 行为不受影响，
     受影响的是 `gate.yml:41-43`、`design.md §2 D1`、`tests/test_gate_workflow.py:329-333` 等处的**叙述**。
2. **GHES / 同 owner fork / 自建 runner 的 uv 版本差异 / `pip install git+…`**：未验证。
   `docs/gate.md §7.1` **已如实登记**（含「GHES 接入方会一直吃 `v1`」）⇒ 这一条**不算缺口**。
3. **issue #30 里那两组 CI 数字（✗10 / ✗1）**：无法复算（另一个仓 + 真 CI）。我只核到「它与 `proposal.md:33-34` 的自述一致」。
4. **真 `uvx --from git+https://github.com/Xingkai98/witnessloop@v1.7.0 …`**：`v1.7.0` **还不存在**（Reviewer 14 已证），
   所以我**没有**跑过真命令。我用**本地 git 仓 + 真 uv 0.13.1**验证了它的机制面（`--force` 会替换、不带 `--force` 也会替换、
   `uv tool install` 同样落 PEP 610 `vcs_info`）——**这不能替代**「真 GitHub ref 上 `uvx` 能否装成」这一步。
5. **A2 的修法面**：我没有验证「`init` 打一行自报」在旧 CLI（`@v1`）上会不会因为 `direct_url.json` 缺失而
   需要额外分支——那是**新能力**的取舍，不在本 change 的现状里。

---

## 必须修改项

> 每条带证据（`文件:行号` 或命令 + 真实输出）。**非纯措辞**的在前。

- **M1（计划面 · 非措辞）`tasks.md §6.1` 的字面量族还缺第 5 处：`tests/test_init_gate_ref.py:24` 的 `NEW_REF`。**
  证据：按 `tasks.md:74-88` 的四条逐字执行 ⇒ `PYTHONPATH=src python3 -m pytest -q` = **5 failed, 667 passed**，
  全部在 `tests/test_init_gate_ref.py`（用例名见 A1）；根因是 `NEW_REF`（`…@v1.7.0`）与 6.1 之后的新
  `OLD_REF = C.DEFAULT_GATE_REF` 同值。
  改法：`NEW_REF` 换成不撞当前默认值的 ref（`…@v1.8.0`），或把它写成从 `C.DEFAULT_GATE_REF` **派生**的「另一个 ref」
  （例如把 ref 段换成 `v1.8.0`），并把这条补进 6.1 的清单；顺带把 `tasks.md:75-76` 的「7 条」订正为修后实测的条数。
- **M2（文档/机制面 · 非措辞）本 change 的 `reviews/` 会因「多轮对抗报告」产生孤儿报告，而按 `docs/gate.md §3` 抄会**静默覆盖**。**
  证据：模拟仓实测（`/tmp/adv3/e7`）——5 份报告 + 3 份 stage manifest ⇒ 2 条孤儿；补一份**同 stage** manifest ⇒
  覆盖同名文件、孤儿变成另一组。本 change 的 `reviews/` 将共有 **5 份 `.md`**（`grill-design` / `grill-adversarial` /
  `grill-adversarial-r2` / 本报告 / 5.1 的 `building-review.md`），而 `docs/gate.md:194-204` 的指引只覆盖「两个 stage」。
  改法：**每份报告各配一份 manifest**，多出的轮次用**不同 stage 名**（我实测 `grill-adversarial-r2` / `-r3` ⇒
  **0 条孤儿**、必备 stage 判定照旧满足）；把这条约定写进 `docs/gate.md §3`（并写明 `reviews/<stage>.manifest.json`
  的**同名覆盖**陷阱），`tasks.md` 补一步「每份报告各产一份 manifest」。
- **M3（可执行的错误陈述 · 非措辞）`tasks.md:87-88` 的 revision 绑定描述与机制相反。**
  证据：`contract.py:683-688` 的规则 + 实测（改一个**非证据**文件 ⇒ 三份 manifest 各报
  `审阅的是旧 revision：… 之后又改动了非证据文件：…`）。⇒「本 PR 自己的变更（非证据）落在 `head_sha` 之后」
  **恰是被禁止的**；成立的只有「**证据文件**落在 `head_sha` 之后」。
  改法：把该括号改成「**证据文件**（`reviews/*.md`、`reviews/*.manifest.json`）可以落在 `head_sha` 之后；
  非证据文件落之后即判 stale，所以重建 manifest 必须绑在**最后一条非证据提交**上」，并在 `tasks.md:89-91`
  之外补一句「重建 manifest 是 `M` 不变集 ⇒ 每份一条 `protected_path_write` 事件」（该条已在 `:89-91` 写了 ✅，
  只是与 `:87-88` 那句相邻、容易被读成同一件事）。
- **M4（入口面 · 非措辞）「先升 CLI」缺一条可复算的自证步骤：`--version` 对两个包同值、`init` 不自报。**
  证据：Reviewer 第 8 条（`witnessloop 0.1.0` ×2、`init` 输出里 0 处 ref）；`docs/gate.md:96-98` 让人
  「先确认 CLI 版本」却没说怎么确认；唯一可用的是 `check` 第一行（`checkcmd.py:76-79`，未接入目录也打）。
  改法：在 `docs/gate.md §1.2` 与 `README.md` 的两步 recipe 的 ① 之后补一步可复算自查，例如
  `witnessloop check --root . 2>&1 | head -1` 应打出 `本包来源（自报，尽力而为）：requested_revision=<你刚升的 ref>`。

---

## Open Questions

> 只放**真需要用户拍板**的。

**Q1（本轮新增）6.1 之后 fail-closed 的落点要不要跟着 `DEFAULT_GATE_REF` 漂移到 `v1.7.0`？**

- 事实：`tests/test_gate_workflow.py:354` 把 `WL_FALLBACK_REF` 与 `DEFAULT_GATE_REF` 的 ref 部分**钉成同源**
  ⇒ 6.1 若只改常量不改 `gate.yml:60`，这条测试红（我实测过）；改了之后，`spec.md:17-18,44`、
  `design.md:47`、`docs/gate.md §7.1`、`gate.yml:39` 注释里的「退 **v1**」全部作废（GHES/fork 接入方会改吃 `v1.7.0`）。
- 两条路：(a) **跟着漂移**（保持「fail-closed 退到本仓当前默认 ref」这条语义，改 spec/§7 的措辞）；
  (b) **钉死 `v1`**（把 `tests/test_gate_workflow.py:354` 从「同源」改成「固定 `v1`」，并说明为什么兜底不跟默认走）。
- 需用户拍板的原因：这改的是**契约面**——GHES / 同 owner fork 这些「拿不到 `job.*`」的接入方
  会落到哪个包，是面向接入方的行为承诺，不是实现细节。**我倾向 (a)**（「退到既有默认」比「退到一个越来越旧的 v1」更符合 `spec.md:44` 那句的原意）。

**Q2（本轮新增）多轮对抗报告怎么绑定：`grill-adversarial-r2` / `-r3` 这种**额外 stage 名**，还是把多出的轮次移出 `reviews/`？**

- 事实：孤儿规则扫 `reviews/**/*.md`（`contract.py:581-613`），而 manifest 落盘名是 `<stage>.manifest.json`
  ⇒ 同 stage 两份 manifest 会**互相覆盖**（实测）。三条路：(a) 额外 stage 名（我实测可用、0 孤儿）；
  (b) 把 r2/r3 搬到 `reviews/` 之外（本仓有先例：`openspec/changes/archive-arrival-recognition/rounds/`，
  移出去就不在孤儿的扫描面里）；(c) 不动工具、每轮用完即合并成一份报告。
- 需用户拍板的原因：这是**跨 change 的约定**（每个多轮对抗的 change 都会撞），且 `docs/gate.md §3` 的
  指引与 `manifest build` 的命名规则要一起改；本 change 自己马上就要用上（M2）。

---

## 收敛结论

**不收敛。**

判据：① 本轮**没有新的可证伪项**；② 前几轮的「必须修改项」**全部已落库**。**②满足、①不满足。**

1. **② 满足**：R1 的 **K1–K8 全部落进正文/实现**（见 B 表，逐条实核）；R2 的 **L1–L6 全部落库**（见 C 表）。
   其中 L3 我**真去踩了**：把 `gate.yml:23` 改回 `default: "v1"` ⇒ `test_witnessloop_ref_input_default_is_empty`
   当场红、其余 28 条绿 ⇒ 钉子**有效**（不是只写在文档里）。
2. **① 不满足：本轮有 4 条新的可证伪项，且全部实测复算**：
   - **A1/M1**：`tasks.md §6.1` 按字面执行仍留 **5 条红**（`NEW_REF` 与新的 `OLD_REF` 撞值），
     而 commit message 已自述「M1 已落」⇒ **修的还不完整**。
   - **A2/M4**：「先升 CLI」这一步**无法自证**（`--version` 两个包同值、`init` 不自报），
     而 `docs/gate.md §1.2` 让人「先确认 CLI 版本」。
   - **A3/M2**：本 change 的 `reviews/` 一旦补齐 manifest，就会因**多轮对抗报告**产生孤儿；
     `docs/gate.md §3` 的「对每个报告各跑一次」在同一 stage 上会**静默覆盖** manifest（本 change 自己有 3 轮）。
   - **A4/M3**：`tasks.md:87-88` 的 revision 绑定描述与 `contract.py:683-688` 相反（实测三条 stale 红）。
3. **本轮证伪失败（= 既有结论成立）的部分也一并记明**，避免读者以为全盘被推翻：
   `(B′)` 的上下文落点（`job.*` + step）与 `github.*` 不可用这条，源码/测试/官方上下文规则三方一致；
   解析 step 的 fail-closed 与兜底剥离**行为级**符合 spec（我复核了 `run:` 原文与 `tests/test_gate_workflow.py` 的 8 类用例）；
   `--gate-ref` 的重写-同步-幂等-可卸载终态是**不动点**；组合语义「先写后判、不回滚」实测自洽且**不产生分叉态**；
   `check` 自报**从不因取不到元数据而失败**（宽 `except` 是刻意且正确的）；作用域守卫**没有**打破
   「新仓已存在 caller ⇒ 冲突且整体不落盘」；远端 tag 清单实测最大 `v1.6.0`（无 `v1.7.0`）；
   `uv tool install`（含 `--force`）**确实会替换**已装 CLI（真 uv 0.13.1 实测）。
4. **下一轮该先做什么（按序）**：
   1. **M1**（一行改动 + 一句清单）：否则 post-merge 的 6.1 一落地就是红的。
   2. **M2**：本 change 自己的 `check` 会踩到（review 报告越多越明显），且 `docs/gate.md §3` 的指引是**错的**（会覆盖）。
   3. **M3**：一句**机制错误**，执行 6.1 的人会照着做。
   4. **M4**：一条入口步骤；补上之后 L2 的两步 recipe 才真正闭环。
   5. 剩下没落的只有 Q1/Q2 两个**契约/约定面**的取舍，需要用户拍板。

---

## 处置（主 session 在 R3 之后追加，非审阅者原文）

> 本报告判定**不收敛**（②满足、①不满足）。**M1–M4 与低危 E1/E3 已逐条落库**，
> 两条 Open Question 已由**作者裁定**（用户已明确「不要提问」），落点见 `design.md §7.9` 的「R3」小节。

- **M1**：`tests/test_init_gate_ref.py` 的 `NEW_REF` 改成 `…@v9.9.9`，并新增
  `test_new_ref_does_not_collide_with_the_factory_default` 把「前提」本身钉住；
  `tasks.md §6.1` 的清单补上这一条并订正条数。**你的实验已复现并验证修法有效**：
  按 6.1 的四处改动模拟执行 ⇒ `673 passed`（改前 `5 failed`）。
- **M2**：采你的方案 **(a) 额外 stage 名**（因为用户指定的产物路径就是 `reviews/grill-adversarial*.md`）；
  `docs/gate.md §3` 写明「每份报告各配一份 manifest」与 `reviews/<stage>.manifest.json` 的**同名覆盖**陷阱，
  并登记另一条路（`reviews/` 之外，先例 `archive-arrival-recognition/rounds/`）为**可选、不混用**。
- **M3**：`tasks.md §6.1` 那句已改成「`head_sha` 之后**只允许证据文件**」，并写清正确顺序
  （先落代码 → 提交 → 再重建 manifest）。你指出的是**可执行的错误陈述**，这条订正的价值最高。
- **M4**：`docs/gate.md §1.2` 与 `README.md` 的 recipe 都补了 ①′：
  `witnessloop check --root . 2>/dev/null | head -1` ⇒ `requested_revision=<刚升的 ref>`，
  并写明「旧包**没有**这一行 ⇒ 有没有这一行本身就是新旧判据」。
- **E1**：验收命令的 `grep -n` 改成 `grep -h`。**E3**：`docs/gate.md §8` 补「包 ref 自报**不共用**」。

### 两条 Open Question 的裁定（**作者裁定，非用户拍板**；可回退面已写明）

- **Q1 = 跟（同源）**：`WL_FALLBACK_REF` 与 `DEFAULT_GATE_REF` 的 ref 部分同源（你的倾向 (a)）。
  理由与代价写在 `design.md §7.9`；「退 `v1`」的措辞已在 `spec.md` / `design.md` / `docs/gate.md §7.1` /
  `gate.yml` 注释 / `tasks.md` 逐处改成「退**兜底 ref**（= `DEFAULT_GATE_REF` 的 ref 部分；今天 = `v1`）」。
- **Q2 = 报告留在 `reviews/`，多轮各用不同 stage 名**（你的方案 (a)）。理由：用户指定的产物路径如此；
  另一条路登记为可选。落点：`docs/gate.md §3` + `tasks.md` 5.2。
