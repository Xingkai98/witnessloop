# Grill: gate-ref-pins-package 设计追问（独立零记忆审阅者）

## Reviewer

我是**独立零记忆**的设计审阅者：本对话不携带该 change 的任何历史，设计稿里的「实测」「文件:行号」「今天就成立」一律当**待验证断言**，可复算的一律复算。

实际读了：本 change 的 `proposal.md` / `design.md` / `tasks.md` / `specs/gate-ref-pinning/spec.md`；模板 change `openspec/changes/archive-arrival-recognition/reviews/grill-design.md`（格式与 §8 的组织方式）；源码 `src/witnessloop/{initcmd,uninitcmd,cli,constants,checkcmd,policy,evidence,entry}.py`；`.github/workflows/{gate,witnessloop,ci}.yml`；`.witnessloop/{init-manifest.json,policy.json}`；`pyproject.toml` / `uv.lock`；`tests/{test_init,test_init_policy,test_init_tests_command,test_gate_workflow,test_uninit,test_docs,test_templates}.py`；`docs/gate.md` / `README.md`；issue #30 与 #31 正文；`templates/grill.md`（报告形状契约）。
另抓取了 GitHub 官方文档的 contexts 页（下文引用）——**reusable workflow 那页本次抓取 404**，只抓到 reusing-workflows 页。

实际跑了（命令 + 真实输出要点）：

1. **本仓 plain `init`**：`PYTHONPATH=src python3 -m witnessloop.cli init --root . --dry-run` ⇒ `init：检测到冲突（已接入，但本次指定的内容与已落地不同…）`，**EXIT=1**，且 diff **只涉及 `.witnessloop/policy.json`**（`require_change_for` + 三个 stage 键），caller 一行都没进 diff。
2. **带 seed 的基线**：从 `tests/test_init_policy.py:19-30` 的 `CUSTOM_DOC` 复原 seed 到 `/tmp/wl-seed.json`，`init --root . --dry-run --policy /tmp/wl-seed.json` ⇒ `init：已接入 witnessloop（幂等，无改动）。` **EXIT=0**。
3. **台账 vs 磁盘 hash**：`.witnessloop/policy.json` 与 `.github/workflows/witnessloop.yml` 的 sha256 与台账**逐字节相符**（`0d1a84f0…` / `4861a80c…`，match=True）；`.witnessloop/init-manifest.json` 自引用条目 `sha256: null`（设计如此）。
4. **模拟 (A)**（把源码拷到 `/tmp/e1/src` 改 `caller_workflow` 加 `with:`，**仓内源码未动**）：对一个用**今日代码**接入的仓跑新码 plain `init` ⇒ 冲突 **EXIT=1**（diff 正是 `+ with: / + witnessloop-ref: "v1"`）；`init --gate-ref <与其台账相同的 ref>` ⇒ 仍 **EXIT=1**。
5. **模拟 (a) 的朴素实现**（手改 caller 成新形态、**不同步台账 hash**）：之后 plain `init` ⇒ `init：已接入，但 init 创建的文件被改动过（拒绝覆盖）` **EXIT=1**；`uninit` ⇒ `uninit：以下文件被改动过，拒绝删除` + `整批未删除` **EXIT=1**。
6. **模拟 (B) 的「改一处」升级**（`/tmp/e2`，只把 `uses:` 的 `@v1` 改成 `@v2`）：plain `init` **EXIT=1**（走的是**漂移**分支不是冲突分支）、`uninit` **EXIT=1**、`init --gate-ref @v2` **EXIT=1**。
7. **v1 tag 现场**：`git rev-parse v1^{}` = `ae992565ee2162e5b272af471e9adf895e7f83fb`（= `v1.6.0`，与 issue #30 一致；`v1` 是 annotated tag，`git rev-parse v1` 给的是 tag 对象 `1d0032a`）；`git rev-list --count v1..HEAD` = **47**；`git diff --stat v1..HEAD -- .github/workflows/gate.yml` **为空**（gate.yml 自 v1 起没动过）；`git show v1:.github/workflows/gate.yml` ⇒ `default: "v1"`；`git diff --stat v1..HEAD -- src/` ⇒ 6 files, +922/−96。
8. `grep -rn "witnessloop-ref\|with:" tests/` ⇒ **空**（没有测试钉「caller 不得有 `with:`」）；`grep -rn "gate.yml\|@v1\|DEFAULT_GATE_REF" templates/ plugin/` ⇒ **空**。
9. `ls openspec/changes/*/workflow-events.jsonl` ⇒ **空**（本仓 11 个 change 无一带过解释事件文件）。
10. `find ~/.cache/uv ~/.local/share/uv -name direct_url.json` ⇒ `.venv/…/witnessloop-0.1.0.dist-info/direct_url.json` = `{"url":"file://…","dir_info":{"editable":true}}`（uv 落 PEP 610 文件）；**未找到**任何 VCS 安装（`vcs_info`）的样本。

**未能复算**（一律标「未验证」，不采信）：`github.workflow_ref` 在 **called workflow** 里的取值语义；`uvx` 从 git URL 装包时是否在 wheel 里写 `direct_url.json` 的 `vcs_info`；接入方 asterwynd 的 CI 日志细节（issue #30 原文，另一个仓）。本工作区**没有可跑的 GitHub Actions**，这三条只能靠真 CI 探针。

---

## Confirmed Decisions

- **proposal/design 的三条机制断言逐条成立（复算通过）。** ① `caller_workflow()` 全文只有 `name/on/permissions/jobs.gate.uses`，**没有** `with:`（`src/witnessloop/initcmd.py:30-47`），而 `desired_files()` 只产出 policy 与 caller 两个文件（`:50-55`）；② `gate.yml` 的 `witnessloop-ref` 默认值确是字面量 `"v1"`（`.github/workflows/gate.yml:19-23`），消费点在 `:57-59` 的 `uvx --from "git+…@${{ inputs.witnessloop-ref }}"`；③ `--gate-ref` 只流进 caller 的 `uses:` 行与台账：`initcmd.py:192`（缺省解析：flag → 台账 → `DEFAULT_GATE_REF`）→ `:46`（写进 `uses:`）→ `:251`（写进台账 `gate_ref`），另外只在 `uninitcmd.py:36-37` 被读一次**用于渲染回滚 diff**。与包版本**没有任何联系**。
  来源: `src/witnessloop/initcmd.py:30-47,50-55,192-193,251`；`.github/workflows/gate.yml:19-23,57-59`；`src/witnessloop/cli.py:43-48`；`src/witnessloop/uninitcmd.py:35-37`；（对照 issue #30 的机制段逐条一致）。

- **既有接入方实际执行的是 `v1` 那份 gate.yml —— 所以 (B) 的「既有接入方零动作即生效」不成立。** `git diff --stat v1..HEAD -- .github/workflows/gate.yml` **为空**（该文件自 v1 起一字未改），而 `git show v1:.github/workflows/gate.yml` 的 `witnessloop-ref` 默认值就是 `"v1"`；v1 = `ae99256`（= v1.6.0），落后 HEAD **47 个提交**、`src/` 差 6 文件 +922/−96 行。⇒ 任何写进 `gate.yml` 的新默认值/新解析逻辑，**只有 caller 的 `uses:` 指到含该改动的新 ref 之后才会被执行**；「改 gate.yml 默认值 ⇒ 存量仓追溯生效」在机制上不成立。
  来源: 命令输出 `git diff --stat v1..HEAD -- .github/workflows/gate.yml`（空）+ `git show v1:.github/workflows/gate.yml` → `default: "v1"` + `git rev-list --count v1..HEAD` → 47；`src/witnessloop/constants.py:11`（默认 ref 钉 `@v1`）。

- **(A) 下既有接入方的 plain `init` 必退 1（实测），且 `--gate-ref` 现在救不了。** 对用今日代码接入的仓，用「caller 双写 `with:`」的代码跑 plain `init` ⇒ `init：检测到冲突（已接入，但本次指定的内容与已落地不同；只增不改，拒绝覆盖…）` **EXIT=1**；显式传**与其台账相同**的 `--gate-ref` 也 **EXIT=1**（冲突判定比的是「本次期望 vs 磁盘」，与 flag 是否显式无关）。
  来源: `/tmp/e1` 实测（源码拷到 `/tmp/e1/src` 后仅改 `caller_workflow`；仓内源码未动）+ `src/witnessloop/initcmd.py:338-351`（冲突分支）。

- **把升级动作写成「只重写 caller、其余文件照旧」会造成永久死锁（实测）。** caller 被重写而**台账里的 sha256 没跟着改**时：① 之后任何 plain `init` 报 `init 创建的文件被改动过（拒绝覆盖）` 并退 1；② `uninit` 报 `以下文件被改动过，拒绝删除` + `整批未删除` 退 1 —— 接入方**再也卸载不掉**（这正是 change `adopter-test-gate` 记录过的「手改 `init` 产物 = 死锁」）。⇒ 升级动作必须**原子地**重写 caller **与**台账里该条目的 `sha256`（及 `gate_ref`），design §8 那句「其余文件照旧只增不改」是被证伪的那一版。
  来源: `/tmp/e1` 实测输出 + `src/witnessloop/initcmd.py:293-331`（漂移分支：磁盘 vs 台账）+ `src/witnessloop/uninitcmd.py:58-62,71-89`；台账里确实记着 caller 的 sha（`.witnessloop/init-manifest.json:13-16`）。

- **(B) 宣称的「改一处即可升级」在今天的代码下同样死锁（实测）。** 只把 caller 的 `uses:` 从 `@v1` 改成 `@v2`（不加 `with:`）：plain `init` **EXIT=1**（命中的是**漂移**分支，文案是「init 创建的文件被改动过」——**不是** design 说的「冲突」）、`uninit` **EXIT=1**、`init --gate-ref @v2` 也 **EXIT=1**。⇒ (B) 的两条升级路径（手改／显式 flag）**今天都不通**，而 design 只把这条残留挂在 (A) 名下（§8 第二问的 ⚠️）。
  来源: `/tmp/e2` 实测输出；分支归属见 `src/witnessloop/initcmd.py:301`（先查「磁盘 vs 台账」）vs `:339`（后查「本次期望 vs 磁盘」）。

- **`--test-command` 的「显式意图优先」先例不能外推到 caller（口径反了）。** 该先例成立的前提是命令文件**刻意不进** `desired_files()`／台账／冲突判定（`constants.py:19-27`、`initcmd.py:195-203`、`docs/gate.md:18-27`、`tests/test_init.py:80-83` 断言它不在台账里）。caller 正相反：进 desired、进台账、参与**两条**冲突判定。更贴近的先例是 `--policy`：显式给**不同**内容 ⇒ **冲突退 1**，文案还写着「要更换 policy 请先 `uninit`」（`initcmd.py:344-347`），并由 `tests/test_init_policy.py:119-131` 钉死。⇒ design §8 第二问引 `constants.py:24-27` 支持推荐 (a) 是**援引错先例**。
  来源: 上述行号；对照 `src/witnessloop/constants.py:24-27` 与 `src/witnessloop/initcmd.py:338-351`。

- **「同一个 diff 里跑一次 `init` 自证不冲突」在本仓不可复现（实测）。** plain `init --dry-run` **今天就已经退 1**，而且那条红**只关于 policy**（`require_change_for` 与三个 stage 键），与 caller 无关；要用 `init --dry-run --policy <seed>` 才是「幂等，无改动」EXIT=0 —— 而 seed 是**仓外的临时文件、刻意不入库**（`README.md:111-113`；`README.md:225` 明写「本仓自己的 `init` 早就跑不动（定制 policy 撞出厂默认）」）。seed 内容可从 `tests/test_init_policy.py:19-30` 逐字复原（我照此复原后复算通过）。⇒ D4 的自证步骤必须写明这条命令，否则任何人按字面跑都会看到一条与 caller 无关的红、无法判断本 change 是否自撞。
  来源: 两条实测命令与输出；`README.md:111-113,225`；`tests/test_init_policy.py:19-30,33-36`。

- **D4 迁移本仓会在本仓门禁上新增一条硬红（解释事件缺失）。** `.witnessloop/init-manifest.json` 属**不变集**受保护路径（`policy.py:18-23`），而规则是「不变集：**新增**免事件、**修改/删除**要事件」（`checkcmd.py:316-321`，`if by_invariant and status[:1] == "A": continue`）。改台账 = `M` ⇒ 需要一条 `protected_path_write` 解释事件；而本 change 目录**没有** `workflow-events.jsonl`，本仓 11 个 change **无一**带过该文件（实测遍历），`tasks.md` 0–5 也**没有任何一项**要建它。⇒ 迁移动作按现稿执行会被自己的门禁判红。
  来源: `src/witnessloop/policy.py:18-23`、`src/witnessloop/checkcmd.py:312-335`；`ls openspec/changes/*/workflow-events.jsonl` → 空；`tasks.md:30-33`。

- **D3 的前半成立、后半（能力边界）过强。** 成立的一半：`checkcmd.py` 全文**没有**任何版本/ref 输出（`_report` 只打 `基线 base...head、N 个变更文件、N 个 change 目录` 与 findings），`--version` 走 `cli.py:31-33` 打印 `witnessloop 0.1.0`；`__version__` 恒 `"0.1.0"`（`src/witnessloop/__init__.py:22`）与 `pyproject.toml:3`、`uv.lock:227` 同值，而 tag 是 `v1.6.0` ⇒ **版本号与 tag 无对应关系**。过强的一半：「构建产物里没有 ref 信息」——uv 的安装会落 PEP 610 的 `direct_url.json`（本仓 `.venv/…/witnessloop-0.1.0.dist-info/direct_url.json` 实测存在，内容是 editable 的 `dir_info`），而 PEP 610 对 **VCS 安装**要求写 `vcs_info.requested_revision` / `commit_id`；本工作区无法跑 uvx 的 git 安装 ⇒ **uvx 是否照写未验证**。
  来源: `grep -n "version\|ref" src/witnessloop/checkcmd.py`（无版本相关命中）；`src/witnessloop/__init__.py:22`、`pyproject.toml:3`、`uv.lock:226-228`；`git rev-parse v1.6.0^{}` → `ae99256…`；`.venv/…/direct_url.json` 的 cat 输出（未验证项见「风险」）。

- **与 #31 在文件级面上正交（唯一交叠是文档）。** 本 change 的落点是 `.github/workflows/gate.yml` / `initcmd.py` / `constants.py` / 文档 / 本仓 caller+台账（`tasks.md:28-33`、`design.md:77-83`）；#31 的落点是 `D` 记录与到达组（issue #31 正文点名的 diff 解析与 `check` 判定）。二者**没有源码文件重叠**，唯一共享面是 `README.md` / `docs/gate.md` 的同文件编辑（合并冲突面，不是语义依赖）。
  来源: `tasks.md:28-33`；`gh issue view 31` 正文（复现命令与 finding 的判定链）。

- **本仓台账足以对「会不会自撞」下判断（两条腿都实测过）。** 台账记着 caller 与 policy 的 sha256（`.witnessloop/init-manifest.json:8-22`，与磁盘 match=True）与 `gate_ref`（`:7`）⇒ ① **生成逻辑变了** ⇒ 走冲突分支退 1（`/tmp/e1` 实测）；② **手改了盘上文件** ⇒ 走漂移分支退 1（`/tmp/e2` 实测）；③ `gate_ref` 字段决定「不带 flag 时用哪个 ref」（`ledger_gate_ref`，`initcmd.py:149-159`），所以它必须与 caller 一起改，否则下一次 plain `init` 的期望值与磁盘立刻分叉。
  来源: 实测 3/4/5/6 + `src/witnessloop/initcmd.py:149-159,293-331`；`.witnessloop/init-manifest.json:7,13-16`。

---

## Code-Resolved Questions（已定案、移出停轮队列）

> 以下问题**能由代码/git/实测判定**，不该占用用户的停轮时间。design §8 的三问里，第三问（本仓自迁）整条落在这里。

1. **design §8 第三问（本仓要不要在同一个 change 里迁移）→ 定案：无法在同一个 diff 内完成，必须改写成「合并 + 发布新 ref 之后的后继动作」。**
   理由：新形态要生效，本仓 caller 的 `uses:` 必须指向一个**含新 gate.yml 的 ref**，而这样的 ref 在本次合并前**不存在**（出厂默认 = `@v1` = `ae99256`，`git show v1:.github/workflows/gate.yml` 是改动前的文件，`git diff --stat v1..HEAD -- gate.yml` 为空）。⇒ tasks 3.3 的「在同一个 diff 里跑一次 init 自证不冲突」没有可指向的对象。
   来源: `src/witnessloop/constants.py:11`；`git show v1:.github/workflows/gate.yml`；`git diff --stat v1..HEAD -- .github/workflows/gate.yml`（空）。**「选哪个 ref 兑现」不是代码问题**，见本报告 Q3。

2. **「本仓迁移的代价」已定案（两条路都实测）：** 选 (A) ⇒ 本仓 plain `init` 由「幂等」（今天带 seed 时 EXIT=0）变成「冲突退 1」；选 (B) ⇒ 生成逻辑不变、plain `init` 仍幂等，但**手改 `uses:` 的迁移动作**会命中漂移分支退 1 且 `uninit` 拒删。⇒ design 的风险表 R3 只在 (A) 下成立，D2 的「(B) 下既有接入方无需改任何文件」在「要升级」时自相矛盾（升级就得改那一行，改了就被判漂移）。
   来源: `/tmp/e1`、`/tmp/e2` 实测；`src/witnessloop/initcmd.py:301`、`src/witnessloop/uninitcmd.py:58-62`。

3. **「`check` 能不能自己报 ref」的定案要改口径**：前半（包内 `__version__` 不含 ref、与 tag 无关）**成立**；后半（「构建产物里没有 ref 信息」）**未验证且有反例机制**（PEP 610 的 `direct_url.json`）。⇒ 不能按 spec 现稿把它写成一条「能力边界 SHALL」——那可能是一条**假的能力边界**。
   来源: `src/witnessloop/__init__.py:22`、`pyproject.toml:3`；`.venv/…/direct_url.json` 实测；PEP 610 的 VCS 字段（未验证 uvx 行为）。

4. **哪些既有测试会被本 change 撞到（逐条点名）：**
   - `tests/test_init_policy.py:156-163`（显式给**不同** `--gate-ref` ⇒ 冲突退 1）在「显式总是重写 caller」下**语义反转**，必须改写（它正是把「拒绝」钉死的用例）。
   - `tests/test_init_tests_command.py:275-291` 是 `caller_workflow()` 的 **golden literal**（`assert … == expected`）⇒ 走 (A) 必改（本仓自举里的「A6 golden literal」同款）。
   - `tests/test_init.py:110-125`（幂等）与 `:128-141`（**新仓**目标文件已存在 ⇒ 冲突且整体不落盘）**不受影响**，但「显式总是重写」的作用域必须写死为**已接入分支**（`initcmd.py:205` 之后），否则会把新仓里外来的 `.github/workflows/witnessloop.yml` 静默覆盖，直接推翻 `:128-141` 的保证。
   - `tests/test_gate_workflow.py:232`（`"\n  gate:\n"` job 名契约）不受影响；`:59`（`C.DEFAULT_GATE_REF == …@v1`）在改 `DEFAULT_GATE_REF` 时必改。
   来源: 上述 `tests/…:行号` 逐条读过；`src/witnessloop/initcmd.py:205,224-234`。

5. **同源文档面（定案清单，供 tasks 1.2 补全）**：`docs/gate.md:14`（caller 行的 `@v1`）、`README.md:20`（`uv tool install git+…@v1`）、`README.md:119-121`（「自 v1.6.0 起随 `@v1` 发布（`@v1` 是滚动大版本）」）、`README.md:170-177`（前置条件段里的 `@v1`）、`.witnessloop/init-manifest.json:7`。`templates/` 与 `plugin/` **零命中**（`grep -rn "gate.yml\|@v1\|DEFAULT_GATE_REF" templates/ plugin/` 为空）⇒ 本 change 不必动这两个目录。
   来源: `grep -rn` 输出；`docs/gate.md:14`；`README.md:20,119-121,170-177`。

6. **机制落点（定案，供 Q1 用）**：GitHub contexts 页把 `github.workflow_ref` 描述为「The ref path to the workflow」+ 示例 `owner/repo/.github/workflows/x.yml@refs/heads/my_branch`；而同页 **`job.workflow_ref` 对 reusable workflow 里的 job 明确「refers to the reusable workflow file」**，`job.workflow_sha` / `job.workflow_repository` 同族（文档给的示例正是「reusable workflow 用 `job.workflow_sha` 检出自己」）。同页的上下文可用性表把 `on.workflow_call.inputs.<id>.default` 允许的上下文列为 `github, inputs, vars`——**`job` 不在其中** ⇒ 走 `job.*` 时**只能写在 step 里**，不能写在 input 的 `default:` 上。
   来源: 本次抓取 <https://docs.github.com/en/actions/reference/workflows-and-actions/contexts>（`github.workflow_ref` 行、`job.workflow_ref` 行、`on.workflow_call.inputs.<inputs_id>.default` 行）。⚠️ **运行时真实取值仍未验证**（见风险 R1）。

7. **`--gate-ref` 的全部消费点（定案，防「偷偷还有别处」）**：`cli.py:43-48`（flag 定义）→ `initcmd.py:192`（缺省解析）→ `:193`（desired）→ `:46`（`uses:`）→ `:251`（台账）→ `uninitcmd.py:36-37`（回滚 diff 的期望内容）。**没有任何一处**把它送到包版本链上。
   来源: `grep -rn "gate_ref\|gate-ref\|DEFAULT_GATE_REF" src/` 的完整命中集。

---

## Open Questions

> 三问都**不能**由代码单独定案（涉及要押注哪个 GitHub 机制、以及升级语义的产品取舍）。每条附本 change 真实场景的具体例子与推荐。
> 编号与 design §8 的对应关系：Q1 = design §8 的「修法形态」问；Q2 = design §8 的「升级动作」问；design §8 的「本仓自迁」问已按上节 Code-Resolved 移出；Q3 是本轮新发现（收益要在哪个 ref 上兑现）。

### ~~Q1 修法形态~~ —— **已由真 CI 实测定案（2026-10-16）：取 (B′＝`job.workflow_sha`)**

- 探针（副本仓 `Xingkai98/asterwynd-wl-switch`，run 38852445945，同仓 reusable workflow）实测：
  `PROBE JOB_WORKFLOW_SHA = 8c218a1e9a2b9d27c3a686755b2987bac6fbe186`、
  `PROBE JOB_WORKFLOW_REF = …/probe-reusable.yml@refs/heads/master`；
  而 `PROBE GH_WORKFLOW_REF = …/probe-caller.yml@refs/heads/master`（= **caller 自己**）、
  `PROBE GH_JOB_WORKFLOW_SHA = <未定义或空>`。
- ⇒ **`job.workflow_ref` / `job.workflow_sha` 唯一确定「被复用的那个 workflow 文件及其 sha」** ⇒ (B′) 可行 ✓。
- ⚠️ 同仓形态实测；**跨仓（接入方调 witnessloop）未实测**，字段语义按文档一致。
- 本问**不再占用用户时间**（详见 `design.md §2 D1` 与 §8 的已定案表）。

### Q2 升级动作：对**已接入**的仓，显式 `init --gate-ref <新 ref>` 应该「重写 caller（+台账）」还是「照旧拒绝、让人先 `uninit`」？

- 现状语义（代码逐行）：显式给**不同** `--gate-ref` ⇒ 与 `--policy` 同款 ⇒ **冲突退 1**，文案「要更换 policy 请先 `uninit`」（`initcmd.py:338-351`），并被 `tests/test_init_policy.py:156-163` 钉死。
- **具体例子（接入方 B，已接入、caller 里没有 `with:`）**：B 跑 `witnessloop init --gate-ref Xingkai98/witnessloop/.github/workflows/gate.yml@v2`
  - 今天 ⇒ **EXIT=1**（实测；若 B 之前已手改过 `uses:`，命中的是**漂移**分支，文案不同、退出码相同）；
  - 选「总是重写」⇒ 应改写 caller + **同步台账该条目的 `sha256` 与 `gate_ref`**，其余文件（policy）照旧只增不改 ⇒ EXIT=0，且之后 plain `init` 仍幂等、`uninit` 仍可用（否则就是上面 CD4 实测的永久死锁）；
  - 选「不给出口」⇒ B 只能 `uninit`（**会连 policy 一起删**）再 `init --policy`，或者手改两处（caller + 台账），而门禁工具本身不会替他做这件事。
- 另需一并裁定的作用域问题：这个「总是重写」**只能作用于已接入分支**（`initcmd.py:205` 之后）；否则「新仓里已存在一个外来的 `.github/workflows/witnessloop.yml`」会从「冲突拒绝」变成「静默覆盖」，推翻 `tests/test_init.py:128-141`。
- **➡️ 推荐答案**：**选「显式给定时重写 caller + 刷新台账」**（即 design 的 (a)，但必须补上「台账」这一步与作用域限制）。理由：① 它是唯一能让「钉一次、两处一致」在不手改台账的前提下成立的入口；② 拒绝语义（`--policy` 那款）在本 change 下会把每一个存量接入方都推向 `uninit`（连带删 policy），代价明显更大；③ design 援引的 `--test-command` 先例**不成立**（命令文件刻意不进台账），不要再拿它当理由；正确的理由与先例是 `--gate-ref` 是**工具自己生成的产物**的 ref、且台账可被工具一致地维护。

### Q4 `check` 要不要自己报告它跑的 ref？（对抗轮 R1 新增，见 `grill-adversarial.md`）

- R1 实测：`uvx` 装出的 dist-info 带 `vcs_info.commit_id` / `requested_revision` ⇒ 「包无法自报 ref」为假。
- **推荐**：纳入，做「尽力而为的打印」（取不到就打 `<未知>`、不失败）。

### Q5 caller 文件不受任何保护，要不要在本 change 里表态？（对抗轮 R1 新增）

- 事实：`.github/workflows/witnessloop.yml` 不在 `protected_paths` / 不变集里 ⇒ 改它不触发任何判定。
- **推荐**：本次只登记进文档（`docs/gate.md §7`），不新增保护面。

### Q3 本 change 的收益要在**哪个 ref** 上兑现（谁、什么时候发布它）？

- 事实：`DEFAULT_GATE_REF = …@v1`（`constants.py:11`）、CLI 安装指引也是 `uv tool install …@v1`（`README.md:20`）、README 又声明「`@v1` 是滚动大版本」（`README.md:119-121`）；而本 change 的目标 3 写着「**不动 `v1` tag`**」、非目标写「不做自动升级」。⇒ 新 gate.yml 只能活在一个**新 ref** 上，而那个 ref 一次都没被命名。
- **具体例子**：本 change 合并到 `main` 之后
  - 若**不**发新 ref：新接入方跑 `init`（出厂默认 `@v1`）⇒ caller 写 `uses: …@v1`，(A) 下再写 `with: witnessloop-ref: "v1"` ⇒ **包仍是旧包**，行为与今天**一模一样**（issue #30 的一号期望落空，只有「显式指到别的 ref 才生效」这一条能力被交付）；
  - 若发 `v1.7.0` 并**把 `DEFAULT_GATE_REF` 一起改到它**：新接入方默认就吃到新包；存量仓仍需自己把 `uses:` 指过去（配合 Q2 的动作）；
  - 若**按 README 的「滚动大版本」把 `v1` 移到新提交**：存量仓会**自动**吃到新包与新 workflow（因为两处都钉 v1）——但这与 design 目标 3「不动 `v1` tag」直接冲突，且会让「钉 v1」的人失去版本稳定性保证。
- **➡️ 推荐答案**：发新 tag（建议 `v1.7.0`）+ 把 `constants.DEFAULT_GATE_REF` 指过去，**并把 README:119-121 的「`@v1` 是滚动大版本」与目标 3 的关系写清**（要么明确「v1 不再移动，升级请改 ref」，要么明确「v1 随 v1.x 移动」——两者只能选一个）。**不要**在本 change 里移动 `v1`。同时把「探针门禁」写进 tasks：收益兑现前必须先有那个 ref，验收（issue #30 的验收 1）才跑得起来。

---

## 风险

- **R1（高 · 未验证）(B) 的基石**：`github.workflow_ref` 在 called workflow 里的取值语义本工作区无法验证（没有可跑的 Actions）。**两个方向都致命**：若它指 **called** 且含 ref ⇒ (B) 可行（但仍受 CD2 的「存量仓要改一处」限制）；若它指 **caller**（GitHub 社区长期的口径之一；本次抓取的两页文档**都没有**出现「github 上下文关联 caller」这句话，也没出现相反的），解析出的会是**接入方自己的 ref**（`refs/heads/<branch>` 或 `refs/pull/N/merge`）⇒ `uvx` 去 witnessloop 仓取一个不存在的 ref ⇒ **全量硬红**，而 spec 承诺的 fail-closed（退回 v1）**只有在解析时校验 `owner/repo == REPO_SLUG` 时才成立**——这条校验 spec/design 都没写。
- **R2（中）风险表 R2 的前提写反了**：`design.md:90` 说「改 `gate.yml` 默认值会**同时**影响所有接入方（含未升级者）」并称「这正是 (B) 的价值（追溯生效）」——按 CD2 实测，**未升级者跑的是旧 gate.yml，完全不受影响**；真正会同时变化的是「发布新 ref 之后所有指到它的 caller」。⇒ 风险表与 D1 的收益段要一起重写，否则会把「一次全局行为变化」的审批话术用在一个**不是全局**的改动上（反过来漏掉了真全局面：新 ref 发布那一刻，所有已升级的 caller 一起换包换 workflow）。
- **R3（高 · 已实测）升级路径的死锁面**：design 字面实现会让接入方失去 `uninit` 出口（`/tmp/e1`、`/tmp/e2` 两组实测）。这是本 change 里**唯一**能把「用户手上的仓卡死」的失效模式，必须先修 Q2 的动作再实现。
- **R4（中 · 未验证）D3 的能力边界可能是假的**：uv 落 PEP 610 的 `direct_url.json`（本仓 `.venv` 实测存在），PEP 610 对 VCS 安装要求写 `vcs_info.requested_revision`/`commit_id`。若 uvx 照写，则「包无法报告自己的 ref」不成立，spec 的「能力边界 SHALL 明写」会写成假话（**未验证**：本工作区跑不了 uvx 的 git 安装，也找不到现成的 `vcs_info` 样本）。
- **R5（中）本仓自撞的三处叠加**：plain `init` 今天已退 1（policy 轴，`README.md:225`）+ 生成逻辑一变再加一条 caller 轴（(A) 下）+ 台账 `M` 需要一条解释事件（`checkcmd.py:316-321`）。三处叠加后「跑一次 init 自证」既跑不动、又会新增一条红，见「必须修改项」M4。
- **R6（低 · 流程）本报告的 shape 与 manifest 重建**：`check` 的 grill 判决要求「`## Open Questions` 里每个 `Q<n>` 都在 `## User Confirmation` 有非占位确认」（`evidence.py:250-266`、`docs/gate.md:431-433`）。在用户答复落盘（tasks 0.3）之前，这份报告**过不了** `check`——属预期；但要注意**答复写进正文会改变 `report_hash`**，所以 grill manifest 必须在答复之后**重建**，否则 `check` 会报 hash 不符（`docs/gate.md:124-125`）。
- **R7（低）`uninit` 的 dip 质量下降**：(A) 之后 `uninit` 渲染的期望内容来自**新**生成器（`uninitcmd.py:36-37`），对旧形态的 caller 会打出一份「看起来要变成新形态」的 diff（删除判定仍只看台账 hash，实测不受影响）。文案会误导，但不影响回滚正确性。
- **R8（低）同源文档面漏项**：`README.md:20` 与 `README.md:119-121`（`@v1` 安装 + 「滚动大版本」声明）在本 change 的收益叙事里是**关键面**，tasks 1.2 只笼统写了「`docs/gate.md` / `README.md` 的接入指引」。

---

## 必须修改项

- **M1（D1 的收益段与 R2 的全局性陈述按实测改写）**：删掉「既有接入方零动作即生效」与「追溯生效」（证据：`git diff --stat v1..HEAD -- .github/workflows/gate.yml` 为空 + `git show v1:…` 默认 `"v1"` + v1 落后 47 提交），改成「存量仓仍要改 `uses:` 一处（或过一次工具），(B) 只是让**改完之后**两处自动一致」；风险表 R2 按 R2 条目重写（真正的全局面 = 新 ref 发布时刻）。
  来源: `.github/workflows/gate.yml:19-23`；`src/witnessloop/constants.py:11`；上述 git 命令输出。

- **M2（Q2 的选项 (a) 必须补两件事，并撤掉错误援引）**：① 动作 = 重写 caller **+ 同步台账该条目的 `sha256` 与 `gate_ref`**（否则永久死锁：plain `init` 走漂移退 1、`uninit` 拒删退 1 —— 已实测）；② 作用域限定「已接入分支」（`initcmd.py:205` 之后），否则会静默覆盖新仓里外来的 caller 并推翻 `tests/test_init.py:128-141`；③ 删掉对 `constants.py:24-27`（`--test-command`「显式意图优先」）的援引——那是**不进台账**的文件，口径与 caller 相反，正确先例是 `--policy`（`initcmd.py:344-347`）。
  来源: `/tmp/e1` 实测；`src/witnessloop/initcmd.py:205,293-331,338-351`；`src/witnessloop/uninitcmd.py:58-62,71-89`；`src/witnessloop/constants.py:19-27`。

- **M3（spec 正文与 Q1 未决状态冲突，必须推迟定稿）**：`spec.md:13-15` 写「既有接入方 SHALL **无需改动**即满足本要求（即包版本 SHALL 由 `uses:` 那一行的 ref 决定，**而不是由一个独立输入的默认值决定**）」——(B) 下包版本**仍然**由 `inputs.witnessloop-ref` 的默认值决定（只是取值被推导出来），(A) 下由 `with:` 决定 ⇒ 这两句正文**各自只对一种机制成立**，在 Q1 裁定前不能作为 Requirement 定稿（`spec.md:5` 已自认"按本稿推荐 (B) 起草"，但 `tasks.md:17` 把它列成一条待办事项，容易让人以为可以照着写）。
  来源: `openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md:5,13-15`；`.github/workflows/gate.yml:19-23,57-59`。

- **M4（D4 / tasks 3.3 必须写全三件事）**：① 自证命令写成 `init --dry-run --policy <seed>`（plain `init` 今天**本来就退 1**，且那条红与 caller 无关）；② 建 `openspec/changes/gate-ref-pins-package/workflow-events.jsonl` 并写一条 `protected_path_write`（`artifact_path` 指向 `.witnessloop/init-manifest.json`、`reason`/`approved_by` 非空），否则改台账必红；③ 迁移动作拆成**合并 + 发布新 ref 之后**的后继动作（同一个 diff 内无可指向的 ref）。
  来源: `/tmp` 无（本仓实测两条命令）；`src/witnessloop/policy.py:18-23`；`src/witnessloop/checkcmd.py:312-335`；`ls openspec/changes/*/workflow-events.jsonl`（空）；`src/witnessloop/constants.py:11`。

- **M5（探针的时序与前提要写进 tasks）**：`design.md:89`（R1）说「实现期**先**在副本仓实测」，而 `tasks.md:38-39` 把它排在 §4 验证（在 §3 实现之后）⇒ 时序号错，应在 §3 之前，作为 Q1 的输入；且探针的**两个前提**没写：需要一个「含探针 gate.yml 的 ref」（可推的分支/fork）与一个接入方副本仓；探针至少要 `echo` 四个值（`github.workflow_ref` / `github.workflow_sha` / `job.workflow_ref` / `job.workflow_sha`），并把 caller 的 `uses:` 换一个 ref 观察哪个值跟着变。
  来源: `design.md:41-46,89`；`tasks.md:38-39`。

- **M6（同源文档清单补两处）**：`README.md:20`（`uv tool install git+…@v1` —— CLI 的安装 ref 与包版本同源）与 `README.md:119-121`（「`@v1` 是滚动大版本」——与目标 3「不动 `v1` tag」的关系必须表态）。这两处比 `docs/gate.md:14` 更需要改，因为它们直接影响「新接入方会不会吃到旧包」。
  来源: `README.md:20,119-121`；`docs/gate.md:14`。

- **M7（若走 (B)/(B′)，把解析落点与 fail-closed 判据写死）**：① 落点：`on.workflow_call.inputs.*.default` 只允许 `github, inputs, vars` 三个上下文 ⇒ `job.*` **只能**在 step 里算；② 接受判据：解析出的 `owner/repo` 必须等于 `constants.REPO_SLUG`（否则退 v1 并打日志）——不然在「`github.workflow_ref` 指 caller」的分支下会拿接入方自己的 ref 去装包；③ spec 的「畸形」用例（`spec.md:22-25`）要给出**具体**畸形样本（缺 `@`、`@` 后为空、`owner/repo` 不匹配、`refs/pull/N/merge`）。
  来源: 本次抓取的 GitHub contexts 页（`on.workflow_call.inputs.<inputs_id>.default` 的上下文可用性行 + `job.workflow_ref` 行）；`src/witnessloop/constants.py:8,11`；`openspec/changes/gate-ref-pins-package/specs/gate-ref-pinning/spec.md:22-25`。

---

## 逐维度速览（templates/grill.md 的七维度）

| 维度 | 结论 |
|---|---|
| 需求对齐 | 三条机制断言对得上（CD1）；但收益叙事与实测不符（CD2/R2）——「钉住的 ref 决定包」今天**已经**在 v1 上成立，缺口是「换 ref 时包不跟」+不可见+v1 落后 |
| 实现细节 | 机制落点未定死（M7）；(B) 的解析上下文选错风险（R1）；(a) 的台账同步缺失（M2） |
| 依赖 | 依赖一个**尚不存在**的「含新 gate.yml 的 ref」（Q3）；依赖未验证的 GitHub 上下文（R1）；不依赖 #31（CD10） |
| 风险 | R1–R8；最高危的是升级路径把 `init`/`uninit` 双入口卡死（R3，已实测） |
| 测试策略 | 两条既有测试会被撞（`test_init_policy.py:156-163`、`test_init_tests_command.py:275-291`）；缺「台账同步」与「uninit 仍可用」的回归用例（M2） |
| 文档影响 | 四处 `@v1` 表述（M6）+ 本仓台账/事件文件（M4） |
| 触发与门禁 | 本 change **自己会撞自己**：本仓 plain `init` 今天已退 1，加上 caller 轴与台账 `M` 的解释事件要求（CD7/CD8/M4） |

---

## User Confirmation

<!-- 停轮之后由主 session 追加：逐条覆盖上面 `## Open Questions` 的 Q1/Q2/Q3，
     形如 `- **Q1**: 用户答复：…；确认时间: YYYY-MM-DD`。
     ⚠️ 答复落盘后必须**重建** grill manifest（report_hash 变了）。 -->
