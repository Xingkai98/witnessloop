# Grill（对抗轮）：gate-ref-pins-package —— 独立零记忆证伪

## Reviewer

我是**独立零记忆**的对抗验证者：本对话不携带该 change 的任何历史；`design.md` / `proposal.md` / `reviews/grill-design.md` 里的
「实测」「文件:行号」「今天成立」一律当**待验证断言**，可复算的一律复算。**目标是证伪结论本身**，不是复述。

**测量基准（重要）**：本 worktree 的 HEAD 在本次会话进行中被移动过（`git reflog`：`da82eee` on `docs/archive-manifest-timing`
→ `0de517d` → `c7aa037` on `probe/workflow-ref`）。**下面所有行号与命令输出，除非另注，都以 `c7aa037`（当前 HEAD）为准**；
凡在 HEAD 移动前后有差异的，逐条标注。**仓内文件我一个都没改**（除本报告）；所有实验都在 `/tmp/adv/` 的模拟仓里做。

**实际读了**：本 change 的 `proposal.md` / `design.md` / `tasks.md` / `specs/gate-ref-pinning/spec.md` / `reviews/grill-design.md`；
源码 `src/witnessloop/{initcmd,uninitcmd,cli,constants,policy,paths,checkcmd,evidence}.py`；`.github/workflows/{gate,witnessloop,probe-ref}.yml`；
`.witnessloop/{init-manifest.json,policy.json}`；`tests/{test_init,test_init_policy,test_init_tests_command,test_gate_workflow}.py`；
`README.md` / `docs/gate.md` / `docs/design.md` / `templates/`；GitHub 官方 contexts 页与 reuse-workflows 页（本次抓取成功）。

**实际跑了（命令 + 真实输出要点，逐条可复算）**：

1. **三条机制断言**：`cat -n src/witnessloop/initcmd.py`（`caller_workflow` = `:30-47`，全文无 `with:`）；`cat -n .github/workflows/gate.yml`
   （`witnessloop-ref` 的 `default: "v1"` = `:19-23`；`uvx --from …@${{ inputs.witnessloop-ref }}` = `:57-59`）；
   `grep -rn "gate_ref\|gate-ref\|DEFAULT_GATE_REF" src/` ⇒ 消费点只有 `initcmd.py:192`（缺省解析）→ `:46`（`uses:`）→ `:250-251`（台账）
   → `uninitcmd.py:36-37`（渲染回滚 diff）。**三条全部成立**。
2. **v1 现场**：`git rev-parse v1` → `1d0032a…`（annotated tag 对象）；`git rev-parse v1^{}` → `ae992565ee2162e5b272af471e9adf895e7f83fb`；
   `git diff --stat v1..HEAD -- .github/workflows/gate.yml` ⇒ **空**（exit 0，无输出）；`git show v1:.github/workflows/gate.yml | grep default`
   ⇒ `:23 default: "v1"`；`git rev-list --count v1..HEAD` ⇒ **50**（不是文档写的 47，见 K5）。
3. **模拟仓复现（今日代码）**：`PYTHONPATH=src python3 -m witnessloop.cli init --root <scratch>` 接入干净仓 ⇒ plain `init` **EXIT=0「幂等」**。
4. **模拟 (A)**（源码拷到 `/tmp/adv/A/src`，只改 `caller_workflow` 加 `with:`；仓内源码未动）：对今日代码接入的仓跑新码 plain `init`
   ⇒ **EXIT=1 冲突**（diff 恰是 `+ with:` / `+ witnessloop-ref: "v1"`）；`init --gate-ref <与其台账逐字相同>` ⇒ **仍 EXIT=1**；`uninit` ⇒ **EXIT=0**。
5. **模拟 (B) 的「改一处」**（只把磁盘 caller 的 `@v1` 改成 `@v2`）：plain `init` ⇒ **EXIT=1**（走**漂移**分支「init 创建的文件被改动过」）；
   `uninit` ⇒ **EXIT=1「整批未删除」**；`init --gate-ref @v2` ⇒ **EXIT=1**。
6. **三条恢复路径**（本轮新增，全部实测）：① `git checkout -- .github/workflows/witnessloop.yml` ⇒ plain `init` **EXIT=0**、`uninit` **EXIT=0**；
   ② `rm .github/workflows/witnessloop.yml` ⇒ plain `init` **EXIT=1**（漂移「缺失」）但 `uninit` **EXIT=0**（干净重来）；
   ③ 台账里该条目 `sha256: null` + `gate_ref` 同步到新 ref ⇒ plain `init` **EXIT=0「幂等，无改动」**、`uninit` **EXIT=0**（见 A1）。
7. **Q2(a) 终态是稳定不动点**：手改 caller 为新形态 + 同步台账 `sha256`/`gate_ref` 后，用 (A) 补丁版跑 plain `init` ⇒ **EXIT=0 幂等**，
   `uninit` ⇒ **EXIT=0**（即 design 推荐的升级动作落在一个稳定态，不是又一个坑）。
8. **真 `uvx` 装包（本轮的关键实证）**：`uv` 不在环境里 ⇒ `python3 -m pip install --target /tmp/adv/uvpkg uv` 装上 **uv 0.13.1**；
   `uvx --from "git+https://github.com/Xingkai98/witnessloop@v1" witnessloop --version` ⇒ `witnessloop 0.1.0`；
   同一条命令换成 `python -c` 读元数据 ⇒
   `direct_url.json = {"url":"https://github.com/Xingkai98/witnessloop","vcs_info":{"vcs":"git","commit_id":"ae992565ee2162e5b272af471e9adf895e7f83fb","requested_revision":"v1"}}`；
   空缓存重跑（`UV_CACHE_DIR=/tmp/adv/uvcache`）时 uvx 自己打印
   `Building witnessloop @ git+https://github.com/Xingkai98/witnessloop@ae992565ee2162e5b272af471e9adf895e7f83fb`。
9. **本仓门禁**：`python3 -m witnessloop.cli check --root . --base origin/main --head HEAD` ⇒ **未通过 ✗（2 项）**，两条都是
   「新 change 目录缺 review manifest / 缺 stage=grill 的 manifest」；**与 caller / policy / 台账无关**。
   （同一命令用**陈旧的本地 `main`**（= `ae99256`，落后 47）当基线 ⇒ ✗ 13 项，会误导出「本 change 自撞」的结论——见 D6。）
   `python3 -m pytest -q`（`PYTHONPATH=src`）⇒ **635 passed**。
10. **路径保护面的实测**：用工具自己的 `paths.matches_any` 跑本仓 policy ⇒
    `.github/workflows/witnessloop.yml`：`protected=False invariant=False require_change=False`（见 B3）。
11. **GitHub 文档**：抓 `docs.github.com/.../contexts`（HTTP 200）逐字核对 `github.workflow_ref` / `github.workflow_sha` /
    `job.workflow_ref` / `job.workflow_sha` / `on.workflow_call.inputs.<inputs_id>.default` 的上下文可用性行（见 C/D）；reuse-workflows 页另抓成功，
    实测**没有**「github 上下文永远关联 caller」这类句子（与 grill 的观察一致）。

---

## 对抗结论

### A 找绕过 / 死锁

| # | 目标 | 结果 | 证据 |
|---|---|---|---|
| A1 | **找到第四条升级路径**（工具外、可用、且 `init`/`uninit` 全绿） | ✅ **成功** | 手改 caller 到新 ref 后，把台账里**该条目**的 `sha256` 置 `null` 并同步 `gate_ref` ⇒ plain `init` **EXIT=0「幂等，无改动」**、`uninit` **EXIT=0**（命令见 Reviewer 6-③） |
| A2 | 找到**非手工**的第四路径（只用工具命令） | ❌ 失败 | 试过并全部失败：`--dry-run` 后再手改（dry-run 不落盘，无状态可用）；`init --policy <与磁盘逐字相同>` 单独用（caller 轴照旧冲突）；`--gate-ref` 与实际 ref 不一致的组合（`@v2` + 台账 `@v1` ⇒ 期望值≠磁盘 ⇒ 冲突）；删台账（⇒ 退化成「未接入」分支，caller 已存在且不同 ⇒ 冲突退 1）；删 caller（⇒ 漂移「缺失」退 1）。**没有任何工具命令能改 ref 而保持幂等** |
| A3 | 证伪「e1/e2 的三条死锁」 | ❌ 失败（**grill 的三条实测我全部复现**） | Reviewer 4（(A) 下 plain `init` / 同 ref `--gate-ref` 均 EXIT=1）、Reviewer 5（(B) 下一步升级：plain `init` EXIT=1 走漂移、`uninit` EXIT=1、`--gate-ref @v2` EXIT=1） |
| A4 | 证伪「死锁是**永久**的」 | ✅ **成功** | 三条恢复路径全部实测可用（Reviewer 6）。且 `grep -rn "INIT_MANIFEST" src/witnessloop/*.py` 证明 **`check` 根本不读台账** ⇒ 死锁期间门禁本身照常工作，坏的只是 `init`/`uninit` 两个动词。⇒「永久」「再也卸载不掉」（CD4 / R3）**在用词上被证伪**：它是一个**响亮、可单条 `git` 或一次 JSON 编辑就恢复**的分叉态 |
| A5 | 证伪「(B) 的『存量仓零动作即生效』」 | ❌ 失败（**这条 grill 订正成立**） | `git diff --stat v1..HEAD -- gate.yml` 空 + `git show v1:…` 的默认值就是 `"v1"` ⇒ 存量仓跑的是改动前那份 gate.yml |
| A6 | 证伪「本仓台账足以判断自撞」 | ❌ 失败 | 台账 sha 与磁盘**逐字节相符**（`sha256sum` 输出 `0d1a84f0…` / `4861a80c…`，与 `.witnessloop/init-manifest.json:11,15` 同值）；generation 一变 ⇒ 冲突（A4 实测）、手改文件 ⇒ 漂移（Reviewer 5 实测） |
| A7 | 找**新的**死锁（工具会用但仓卡死） | ❌ 未找到新的 | 唯一「卡死」是 A4 那条已知分叉态；`sha256:null` 那条反而是**出口**（A1） |

**新绕过 A1 的意义（不只是好奇）**：它证明升级路径**存在且无需改工具**——`init-manifest.json` 是提交进仓、接入方自己拥有的文件，
而 `initcmd.py:301` / `uninitcmd.py:59` 用的是 `entry.get("sha256") and …`：**任何 `sha256` 为 `null`/缺失的台账条目，两条判定都直接跳过**。
这把 design 的核心权衡前提（「不修 Q2 就只能手改两处、而手改会死锁」）改成了「不修 Q2 也能靠一次台账编辑走通」：
**Q2 的取舍从「有出口 vs 没出口」变成了「出口好用 vs 出口难用」**，这会影响 (a) 的必要性论证。

### B 找假阴性 / 误伤

- **B1（假阴性 · 强）proposal 的「没有任何提示」不成立。** `proposal.md:17` 写「接入方**不移动 `v1` tag 就永远吃到旧包**，
  且**没有任何提示**」。实测：**今天的 CI 日志里就有解析后的 commit sha**——空缓存下的 `uvx` 自己打印
  `Building witnessloop @ git+…@ae992565ee2162e5b272af471e9adf895e7f83fb`（Reviewer 8），正是 issue #30 引用的那串。
  ⇒ 真实缺口是「**已可见但未标注** + 两半不同步」，不是「不可见」。`design.md:65`（「不需要 grep uvx 的构建输出」）是准确版本，
  `proposal.md:17` 是过强版本。**后果**：会让人低估「先 grep 一下就定位」这个现成手段，也会高估 D3 的增量价值。
- **B2（假阴性 · 强）D3 的「能力边界」是假的，实测可证伪。** `design.md:66-68` 与 `design.md:128`（「已由代码定案」表）
  与 `spec.md:38-39`（写成一条 **SHALL 明写** 的能力边界）都断言「witnessloop **包自身**无法报告我是从哪个 git ref 构建的 / 构建产物里没有 ref 信息」。
  实测（uv 0.13.1，与 `gate.yml:57-58` **同一条** uvx 调用）：装下来的 dist-info 带 PEP 610 的
  `vcs_info.requested_revision = "v1"`、`commit_id = "ae9925…"`。⇒ `check` **可以**自报 ref（连 resolved commit 一起）。
  **具体后果两条**：① spec 会把一条**假约束**写死，实现者据此不会去做本来能做到的事；
  ② 即便只做 D3 的 echo，**echo 只能打出「请求的 ref」**（`v1`）而打不出 resolved commit——而 issue #30 的验收证据恰恰是 resolved sha；
  `check` 自报是**严格更强**的形态。**注意**：`__version__` 恒 `0.1.0`、与 tag 无关这条**成立**（`src/witnessloop/__init__.py:22`、
  `pyproject.toml:3`、`uv.lock` 同值；`checkcmd.py` 全文无版本输出）——被证伪的只是「构建产物里没有 ref 信息」这半句。
- **B3（漏 · 强）「钉住的 ref」本身不受保护**：用工具自己的匹配器实测，`.github/workflows/witnessloop.yml` 在
  `protected_paths` / `require_change_for` / `INVARIANT_PROTECTED_PATHS` 三处**全不命中**（Reviewer 10）。
  ⇒ 一个 PR 可以把 caller 的 `uses:` 改成**自己 fork 的 gate.yml**，`check` 不会报一条 finding；而 required check 的名字
  `gate / check` 前半来自 caller 的 job 名（`initcmd.py:44-46` 的 `gate:`，`tests/test_gate_workflow.py:232` 把它当契约钉着），
  只要 fork 那份 gate.yml 定义一个叫 `check` 的空 job，就仍能满足 required check。
  **这是本 change 的题眼（「钉住的 ref 决定包」）在机制上的反例**，而 design/spec 把它整段留在未表态面（**GitHub 端行为为推演，见「未验证项」**）。
- **B4（漏 · 中）(B) 下「单一事实来源」是默认值，不是不变式。** `design.md:35` 把「人只改 `with:` 而不改 `uses:` ⇒ 两处不一致」
  记为 **(A) 独有的代价**；但 `with:` 在 (B) 下**同样可写**（`gate.yml:19-23` 的 `required: false`，传了就覆盖默认值）⇒
  两种形态都留着第二个可写点，而**任何形态都不检测两处不一致**。D3 的 echo 若只打最后生效的那个 ref，这个不一致就仍然无声。
- **B5（误伤 · 中）`tests/test_init_tests_command.py:269-291` 不只是一条断言，它的**立论**在 (A) 下自相矛盾**：该用例名
  `test_caller_workflow_bytes_are_frozen`、docstring 写「**本 change 不许改 `caller_workflow()` 的字节**（本仓台账记着 caller 的 sha256）」
  ——即「(A) 必须改 `caller_workflow`」与「该测试禁止改」正面冲突，且它给出的理由正是**本 change 要拆开处理的台账**。
  grill 判「必改」是对的，但那是**语义层要重写**（不只是更新 golden），应作为 (A) 的显式代价登记。
- **B6（误伤 · 低）GHES 面**：文档明确 `job.workflow_ref` / `job.workflow_sha` / `job.workflow_repository`
  「**not available on GitHub Enterprise Server**」。若 M7 的「接受判据」用 `job.*`，GHES 上必然落到 fail-closed ⇒ 落到 `v1`
  ⇒ GHES 接入方**永远**吃旧包（虽有日志，仍是本 change 要消灭的那类静默）。design/spec 未提这个平台面。

### C 逐条判 grill 的 CD1–CD11 与 M1–M7

> 判据：**成立** = 我独立复算通过；**部分** = 主结论对、细节/用词被我证伪；**不成立** = 核心断言与实测冲突。

| 条目 | 判定 | 我的复算与订正 |
|---|---|---|
| **CD1** 三条机制断言成立 | **成立** | `caller_workflow` = `initcmd.py:30-47` 确无 `with:`；`gate.yml:19-23` 默认 `"v1"`、`:57-59` uvx；`--gate-ref` 的消费点全集我已独立 grep 复核（`initcmd.py:192,46,250-251`；`uninitcmd.py:36-37`），确与包版本无关 |
| **CD2** 存量仓跑的是 v1 那份 gate.yml | **成立，但计数陈旧** | `git diff --stat v1..HEAD -- gate.yml` 空 ✅、`git show v1:…` 默认 `"v1"` ✅；**「47 个提交」实测为 50**（`git rev-list --count v1..HEAD`，见 K5） |
| **CD3** (A) 下 plain `init`/同 ref `--gate-ref` 均退 1 | **成立** | Reviewer 4 逐字复现（含 diff 形状） |
| **CD4** 只重写 caller、不同步台账 ⇒ 死锁 | **部分** | 行为**成立**（Reviewer 5 两条命令的 EXIT=1 与文案逐字一致）；**「永久」「再也卸载不掉」不成立**——三条恢复路径实测可用（A4/K3），且 `check` 不读台账 |
| **CD5** (B) 的「改一处」升级今天也死锁 | **成立** | Reviewer 5：plain `init` EXIT=1（**漂移**分支，文案「被改动过」——不是 design 说的「冲突」）、`uninit` EXIT=1、`--gate-ref @v2` EXIT=1 |
| **CD6** `--test-command` 先例不能外推 | **成立** | `constants.py:19-27`、`initcmd.py:195-203`、`docs/gate.md:18-27`、`tests/test_init.py:80-83`（「命令文件不进台账」）全部复核；正确先例 `--policy` 的冲突文案在 `initcmd.py:344-347` |
| **CD7** 「同一 diff 跑一次 init 自证」不可复现 | **部分** | 「plain `init` 今天退 1、且 diff 只关 policy」**成立**（我实跑：`--- a/.witnessloop/policy.json`，`require_change_for` 键差，EXIT=1）；`--dry-run --policy <seed>` ⇒ EXIT=0「幂等」**成立**。**但**新增的 `design.md:131` 把这条当成「本 change 内」的自证 ⇒ 在 **(A) 下它必红**（实测，见 K4） |
| **CD8** D4 迁移会新增「解释事件缺失」硬红 | **成立** | `.witnessloop/init-manifest.json` 确认命中不变集（`policy.py:20`，我跑匹配器复核）；`checkcmd.py:319-320` 的「不变集 + `A` ⇒ 免事件」逻辑成立；`ls openspec/changes/*/workflow-events.jsonl` **空**（实测）；`events.load_all`（`events.py:98-99`）确实读 `changes/*/workflow-events.jsonl` ⇒ M4 给的文件路径正确 |
| **CD9** D3 前半成立、后半过强 | **部分 → 现已可判** | 前半（`__version__` 与 tag 无关、`checkcmd` 无版本输出）**成立**；后半 grill 标「未验证且有反例机制」——**本轮实测反例成立**：`vcs_info` 真的写（B2/K1） |
| **CD10** 与 #31 文件级正交 | **未能独立复算** | `gh issue view 30/31` 在本机报 GraphQL `Projects (classic)` 错误、未取到正文 ⇒ **我不采信也不反驳**（见「未验证项」） |
| **CD11** 本仓台账足以判断自撞 | **成立** | sha 与磁盘逐字节相符（实测）；三条自撞路径（生成逻辑变 / 手改 / 台账 `M`）我分别复算 |
| **M1** 收益段与 R2 按实测改写 | **已落库、成立** | `design.md:39-43`（M1 订正）、`design.md:103`（R2 改成「新 ref 发布的那一刻」） |
| **M2** Q2(a) 补台账同步 + 作用域 + 换先例 | **已落库** | `design.md:151-155` 三条都在；作用域「已接入分支」对应 `initcmd.py:205` 之后，与 `tests/test_init.py:128-141` 不冲突——我的 (A) 终态实测（Reviewer 7）证明同步台账后确实稳定 |
| **M3** spec 正文推迟定稿 | **已落库** | `spec.md:13-18` 的两条删除线 + 「推迟到 Q1 裁定之后」 |
| **M4** D4 三件事写全 | **已落库，但 ① 有缺陷** | `design.md:76-81` 三件事在；②③ 复核成立；**①「自证命令写 `--dry-run --policy <seed>`」在 (A) 下不成立**（K4） |
| **M5** 探针时序提到实现前 | **已落库，但已过时** | `tasks.md:30-35`（3.0）与 `:46`（4.2）在；**但探针文件 `.github/workflows/probe-ref.yml` 已经存在**（`c7aa037`，另一分支 `probe/workflow-ref`），而 `tasks.md` / `design.md` **一个字都没提它**、也没登记「谁跑、结果记哪儿、用完即删」（K8） |
| **M6** 同源文档清单补 README 两处 | **已落库，清单仍不全** | `design.md:94-96` 在；**漏 `docs/design.md:56` 与 `docs/design.md:73`**（两处 `@v1`，grep 实测，K6） |
| **M7** 解析落点 + fail-closed 判据写死 | **成立，但有遗漏面** | 文档核对：`on.workflow_call.inputs.<inputs_id>.default` 的可用上下文实测为 `github, inputs, vars` ⇒ **`job.*` 不能用在那里**、只能进 step（M7① 成立）；但 M7 未覆盖 **B4**（显式 `with:` 覆盖）与 **B6**（GHES）|

**C 的小结**：11 条 Confirmed Decisions 里，**没有一条核心行为断言被推翻**（CD1/2/3/5/6/8/11 全部复现成立）；被证伪的是三处**判断过度**：
CD4 的「永久」、CD9 的「未验证」（现在有实证了，反例成立）、CD7 的适用范围。7 条 M 全部已落库，其中 M4①/M6/M5 各带一处新缺陷。

### D 与源码/文档事实核对

| 断言 | 实测 |
|---|---|
| `caller_workflow()` 从不写 `with:` | ✅ `src/witnessloop/initcmd.py:30-47`（全文只有 `name/on/permissions/jobs.gate.uses`） |
| `gate.yml` 的 `witnessloop-ref` 默认 `"v1"` | ✅ `.github/workflows/gate.yml:19-23` |
| `--gate-ref` 只影响 `uses:` | ✅ 消费点全集 = `initcmd.py:192` → `:46` → `:250-251` → `uninitcmd.py:36-37`（`grep` 复核无第五处） |
| `__version__` 恒 `0.1.0` 与 tag 无关 | ✅ `src/witnessloop/__init__.py:22`；tag `v1.6.0` = `ae99256`；`cli.py:31-33` 打 `witnessloop 0.1.0` |
| init 冲突判定 / 漂移判定 / uninit 拒删 | ✅ 冲突 `initcmd.py:224-234` + `:338-351`；漂移 `:290-331`；拒删 `uninitcmd.py:58-61,71-89`（全部实跑触发过） |
| **「构建产物里没有 ref 信息」** | ❌ **假**（`vcs_info` 实测存在，B2/K1） |
| **「没有任何提示」** | ❌ **假**（uvx 打印 resolved sha，B1/K2） |
| 「v1 落后 47 个提交」 | ⚠️ **陈旧**：`git rev-list --count v1..HEAD` = **50**（`design.md:41` 与 `grill-design.md:18,32` 都写 47） |
| 台账 sha 与磁盘一致 | ✅ `0d1a84f0…` / `4861a80c…` 与 `.witnessloop/init-manifest.json:11,15` 逐字节相符；自引用条目 `sha256: null` |
| 「本 change 会自撞本仓门禁」 | ⚠️ **取决于基线选谁**：`check --base origin/main` ⇒ ✗ **2 项**（都只是「新 change 目录缺 manifest」，与 caller/台账无关）；用**陈旧的本地 `main`**（`ae99256`）当基线 ⇒ ✗ **13 项**，那 11 条额外红是**已在 main 的历史 change** 的 manifest 过期，不是本 change 造成的。**别用本地 `main` 当 PR 基线**（两分支都落后 `origin/main`） |
| 本仓测试面 | ✅ `PYTHONPATH=src python3 -m pytest -q` ⇒ **635 passed**（探针文件不影响任何用例） |

### E 低危观察

1. **`probe-ref.yml` 已提交但无人认领**：`c7aa037`，内容只 echo 八个值。`tasks.md:30-35` 说探针要有「含探针 gate.yml 的 ref + 接入方副本仓」两个前提，**没写「探针文件在哪个分支、结果贴回哪里、谁删」**；而它已经躺在分支上了（K8）。
2. **探针里两个变量在官方 contexts 页零命中**：`github.job_workflow_sha` 与 `job.self_ref`（我对 contexts 页全文 grep，`job_workflow` 与 `self_ref` 各 **0 命中**）。要么探针会打出「<未定义或空>」白跑一格，要么得确认它们是不是别名（**运行期行为未验证**）。`github.workflow_ref` / `github.workflow_sha` / `job.workflow_ref` / `job.workflow_sha` / `job.workflow_repository` 都**在文档里**（`github.workflow_sha` 确实存在：'The commit SHA for the workflow file'）。
3. **`refs/pull/N/merge` 的定性措辞不准**：`spec.md:29` 说它是「不是可安装的稳定 ref」。稳定与否对；「不可安装」这一层我没验证（GitHub 的 git 服务通常能 fetch 该 ref）——别把它写成安装失败的理由。
4. **同一机制别人四天前就记过**：`openspec/changes/adopter-test-gate/design.md:20` 与 `.../reviews/grill-review.md:263,398` 已写「`gate.yml:19-23` 的 `witnessloop-ref` 默认 `v1`，caller 从不覆盖」。proposal 的「背景」把它叙述成新发现，读者会以为此前无人知晓。
5. **`uninit` 的 diff 会误导**（grill R7 已记，我复核成立）：`uninitcmd.py:37` 用**新**生成器渲染期望内容，对旧形态 caller 会打出「看起来要变成新形态」的 diff —— 判定仍只看台账 hash，回滚正确性不受影响。
6. **`docs/design.md:56,73`** 两处 `@v1`（安装指令与 caller 行）未进 M6 的同源清单。
7. `templates/` 与 `plugin/` 对 `gate.yml|@v1|DEFAULT_GATE_REF` **零命中**（我 grep 复核，与 grill #8 一致）。

---

## 未验证项

**明确不把推演写成实测：**

1. **`github.workflow_ref` / `job.workflow_ref` / `github.workflow_sha` 在 called workflow 里的运行期取值**——本工作区**没有可跑的 GitHub Actions**，仍**未验证**。
   - **文档侧我能确认的**：`job.workflow_ref` 的定义里明写「For jobs defined in a Reusable workflows, **this refers to the reusable workflow file**」，
     `job.workflow_sha` / `job.workflow_repository` 同族，且文档给的**示例**正是「reusable workflow 用 `job.workflow_sha` 检出它自己」；
     文档给的格式样例只出现 `@refs/heads/main` 形态。
   - **文档侧我不能确认的**：`github.workflow_ref` 在 called workflow 里指向 caller 还是 callee —— 我抓到的 contexts 页与 reuse-workflows 页**都没有表态**（grep「caller」「associated with」无相应句子）。
   - **若假设相反会怎样（具体后果）**：若 `github.workflow_ref` 实际指 **caller**，则 (B) 会拿**接入方自己**的 ref（`refs/heads/<branch>` 或 `refs/pull/N/merge`）去 `uvx` 装包
     ⇒ 装不到 ⇒ **全量硬红**，除非解析时校验 `owner/repo == constants.REPO_SLUG`（M7② 写了这条，但那是**另一个**判据、只在 `owner/repo` 不等时兜住；同 owner 的 fork 场景兜不住）；若它指 callee 但对**tag 形态**的 `uses:` 返回 `refs/tags/v1`，则 `uvx --from …@refs/tags/v1` 是否等价于 `@v1` **也未验证**（uv/git 解析 ref 的形态我这次没测）。
2. **fork 改向 required check 的 GitHub 端行为**（B3 的最后一跳）：我用工具自己的匹配器证明了 caller 文件**不受保护**（实测），
   但「fork 的无操作 gate.yml 能否满足名为 `gate / check` 的 required check」是**推演**，没跑 CI。
3. **issue #30 / #31 原文**：`gh issue view` 在本机报 GraphQL `Projects (classic)` 错误，正文没取到 ⇒ **CD10（与 #31 正交）我不采信也不反驳**；
   `proposal.md:19-22` 里「v1 ⇒ ✗10 项 / main ⇒ ✗1 项」的接入方实测我也**无法复算**（另一个仓 + 真 CI）。
4. **`uvx` 之外的 host**：我只验了 uv 0.13.1 的 VCS 安装；`pip install git+…` 是否同样落 `vcs_info`（PEP 610 要求，但实现各异）**未验证**；GHES/自建 runner 上的 uv 版本差异**未验证**。
5. **`github.job_workflow_sha` / `job.self_ref`（探针里的两个）的运行期行为**——文档零命中，既可能是空值也可能是别名，**未验证**（E2）。
6. **`refs/pull/N/merge` 是否可被 uv/git 安装**：未跑（E3）。
7. **模拟仓的结论到真仓的迁移**：A1（`sha256: null` 出口）与 A4（三条恢复路径）都在 `/tmp/adv/` 的模拟仓复现，**本仓未动、未验证在本仓上同样成立**（本仓的额外干扰是 policy 轴本来就红）。

---

## 必须修改项

> 每条带证据（`文件:行号` 或命令 + 真实输出）。**非纯措辞**的在前。

- **K1（假的能力边界，会写进 spec）**：删掉/改写 `design.md:66-68`、`design.md:128`（§8「已由代码定案」表的第一行）、
  `spec.md:38-39` 三处的「包自身无法报告 ref / 构建产物里没有 ref 信息」。
  **证据**：`uvx --from "git+https://github.com/Xingkai98/witnessloop@v1" python -c "import importlib.metadata as md;
  print(md.distribution('witnessloop').read_text('direct_url.json'))"` ⇒
  `{"url":"https://github.com/Xingkai98/witnessloop","vcs_info":{"vcs":"git","commit_id":"ae992565ee2162e5b272af471e9adf895e7f83fb","requested_revision":"v1"}}`。
  改法建议：把「做不到」改成「**做得到，但本 change 是否纳入待定**（Q4）」，并说明它比 echo 多出 **resolved commit** 这一维。
- **K2（假命题驱动收益叙事）**：`proposal.md:17` 的「且**没有任何提示**」必须改。
  **证据**：空缓存 `uvx`（`UV_CACHE_DIR=/tmp/adv/uvcache`）输出
  `Building witnessloop @ git+https://github.com/Xingkai98/witnessloop@ae992565ee2162e5b272af471e9adf895e7f83fb`。
  ⇒ 改成「日志里有 resolved sha，但**没有标注、也没有把 ref 与包对应起来**」；`design.md:64-65` 的措辞（「不需要 grep uvx 的构建输出」）可保留。
- **K3（风险等级被夸大，会驱动审批口径）**：CD4 / `design.md:104`（R3）/ `grill-design.md:37` 的「**永久**死锁 / 接入方**再也卸载不掉**」
  改为「**响亮但可恢复**的分叉态」，并登记三条恢复路径。
  **证据**：(i) `git checkout -- .github/workflows/witnessloop.yml` 后 plain `init` **EXIT=0**、`uninit` **EXIT=0**；
  (ii) `rm .github/workflows/witnessloop.yml` 后 `uninit` **EXIT=0**（`uninitcmd.py:56-57` 对缺失文件 `continue`）；
  (iii) 台账该条目 `sha256: null` + `gate_ref` 同步 ⇒ plain `init` **EXIT=0「幂等」**、`uninit` **EXIT=0**；
  (iv) `grep -rn "INIT_MANIFEST" src/witnessloop/*.py` ⇒ 除 `initcmd`/`uninitcmd` 外无消费者 ⇒ **`check` 不读台账，门禁不受影响**。
- **K4（新增设计行在 (A) 下自相矛盾）**：`design.md:131` 的「本 change 内只做 `init --dry-run --policy <seed>` 自证」必须加条件。
  **证据**：同一命令在本仓跑——今日代码 ⇒ `init：已接入 witnessloop（幂等，无改动）。` **EXIT=0**；
  (A) 补丁版 ⇒ `init：检测到冲突（…）` + `--- a/.github/workflows/witnessloop.yml` / `+ with:` / `+ witnessloop-ref: "v1"` **EXIT=1**。
  ⇒ 该命令**证明不了**「不冲突」，它只会把本 change 新引入的那条轴照出来；应在 (A) 分支下写明「实现 PR 里这条红是**预期**」，
  并把「自证」挪到迁移完成之后。
- **K5（计数陈旧）**：`design.md:41`、`grill-design.md:18,32` 的「47 个提交」→ 实测 **50**（`git rev-list --count v1..HEAD`，HEAD `c7aa037`）。
  建议改成不依赖计数的表述（「落后数十个提交，且 `src/` 差 6 文件 +922/−96」）。
- **K6（同源文档清单不全）**：`design.md:94-96`（M6）的清单补 `docs/design.md:56`（`uvx --from …@v1` 私有仓说明）与
  `docs/design.md:73`（caller 行 `uses: …gate.yml@v1`）。
  **证据**：`grep -rn "@v1\b" README.md docs/gate.md docs/design.md templates/` ⇒ 命中 `docs/design.md:56,73`。
- **K7（升级路径的存在性未被登记 ⇒ Q2 的取舍前提错了）**：把 A1 的「台账 `sha256: null` + 同步 `gate_ref`」作为**已知的工具外出口**写进 design，
  并裁定是否收紧：`initcmd.py:301` / `uninitcmd.py:59` 的 `entry.get("sha256") and …` 让**任何 null/缺失 sha 的条目跳过两条判定**，
  而 `build_manifest` 只对 `self` 条目写 `null`（`initcmd.py:104`）——即「null 的语义」是**约定**、不是**强制**。
  **证据**：实测（Reviewer 6-③）+ 上述两行源码。
- **K8（仓状态与 change 文档脱节）**：`.github/workflows/probe-ref.yml` 已随 `c7aa037` 提交（分支 `probe/workflow-ref`），
  但 `tasks.md` / `design.md` / `spec.md` 对它**零提及**，Q1 的输入（探针结果）也没有落点。
  **证据**：`git show --stat c7aa037` ⇒ `A .github/workflows/probe-ref.yml`；`grep -n "probe-ref" openspec/changes/gate-ref-pins-package/*.md` ⇒ **无命中**。
  ⇒ tasks 3.0 需补「探针文件在哪、结果贴回哪个文件、用完删不删、谁跑」。

---

## Open Questions

> 只放**真需要用户拍板**的。凡能由代码/规格定案的，我都在正文给依据并**移出**。

**已移出（本轮定案，不再是问题）**

| 原问题 | 定案 | 依据 |
|---|---|---|
| `check` 能不能自己打印「我在用哪个 git ref」？ | **能**（`__version__` 与 tag 无关是真的，但「构建产物无 ref」是假的） | 实测 `direct_url.json` 的 `vcs_info`（K1） |
| 「不修 Q2 就没出口、仓会被卡死」 | **有出口，且可恢复** | 三条恢复路径实测（K3/A1） |
| 用 `github.*` 还是 `job.*` 做解析上下文 | **优先 `job.*`**（文档明确「refers to the reusable workflow file」，且给了「用它检出自己」的官方示例）；`github.workflow_ref` 在 called 场景**文档无表态**，用它属押注 | 本次抓取的 contexts 页逐字 |
| (A)/(B) 落定后 `init`/`uninit` 会不会被新形态自己搞坏 | **不会**：新形态终态是稳定不动点 | Reviewer 7 实测（plain `init` EXIT=0、`uninit` EXIT=0） |

**留给用户**

- **Q1（收窄版）修法形态**：探针**仍必须先跑**——尤其要确认 tag 形态 `uses:` 下 `job.workflow_ref` 返回什么（`refs/tags/v1`？`v1`？），
  以及同 owner 的 **fork** 场景下 `owner/repo` 校验是否兜得住（M7② 只写了「不等于 `REPO_SLUG` 就退 v1」，同 owner 的 fork 不在保护面内）。
  探针之外的部分现在有文档依据（`job.*`）。
- **Q2（收窄版）升级动作**：从「有没有出口」变成「**出口用哪一条**」——
  (a) 工具改（design 推荐，终态已实测稳定）／(c) 只写文档、让接入方手改 caller **+ 台账**（现在证明可行，见 A1/K7）／
  拒绝语义照旧。**并请一并裁定 K7**（要不要把 `sha256: null` 收紧成只能用于 `self`）。
- **Q3（不变）在哪个 ref 兑现收益**：`v1.7.0` + 改 `DEFAULT_GATE_REF` / 动 `v1` tag / 不发新 ref。
  ⚠️ `README.md:119-120` 明写「`@v1` 是滚动大版本」，这与 `proposal.md:29` 目标 3「不动 `v1` tag」正面冲突——
  **「动 `v1`」其实是一条文档承诺过的、零接入方动作的路径**，请明确它为何被排除（本次实测：v1 那份 gate.yml 一字未改，
  动 v1 会让所有存量仓**同时**吃到新 workflow + 新包）。
- **Q4（本轮新增）**：既然包能自报 ref（K1），**要不要把「`check` 打印自己的 `requested_revision` + `commit_id`」纳入本 change**？
  它比 echo 强（resolved commit、且不依赖新 gate.yml 被跑到），但会动 `checkcmd.py`（扩大本 change 的受管控面）。
- **Q5（本轮新增）**：`.github/workflows/witnessloop.yml` **不受任何保护**（B3），要不要在本 change 表态（纳入受保护路径 / 显式写进非目标）？

---

## 收敛结论

**不收敛。**

判据（本轮没有新的可证伪项 **且** 所有「必须修改项」都已落库）**两条都不满足**：

1. **出现新的可证伪项，且已实证**（不是措辞/计数）：
   - **B2/K1**：`design.md:66-68,128` 与 `spec.md:38-39` 的「能力边界」被 `uvx` 真装实测**证伪**（`vcs_info.commit_id`/`requested_revision` 确实存在）。
   - **B1/K2**：`proposal.md:17` 的「没有任何提示」被实测**证伪**（fresh uvx 打印 resolved sha）。
   - **A4/K3**：CD4 / R3 的「**永久**死锁 / 再也卸载不掉」被三条恢复路径实测**证伪**（且 `check` 不读台账）。
   - **A1/K7**：第四条升级路径**存在**（台账 `sha256: null` + 同步 `gate_ref` ⇒ `init`/`uninit` 全绿），design 的取舍前提需重述。
   - **K4**：`design.md:131` 新增的「本 change 内只做 `init --dry-run --policy <seed>` 自证」在 (A) 下**实测自相矛盾**。
2. **「必须修改项」8 条全部未落库**（K1–K8 均指向 `design.md` / `proposal.md` / `spec.md` / `tasks.md`，本轮我只被允许写这一份报告）。

**本轮证伪失败（= grill 成立）的部分也一并记明，避免读者以为全盘被推翻**：三条机制断言（CD1）、存量仓跑 v1 那份 gate.yml（CD2）、
(A)/(B) 下两类升级动作今天都退 1 的行为（CD3/CD5，含漂移分支与冲突分支的**归属差异**）、`--test-command` 先例不成立（CD6）、
D4 的解释事件硬红（CD8）、台账足以判断自撞（CD11）——**我独立复算全部通过**。
11 条 CD 中没有一条的核心行为断言被推翻；被推翻的是三处**判断过度**与一处**未验证项的实测结论**。

**建议下一轮**：先把 K1–K5 回写（K1/K4 会改变 Q1 的选项集合与 spec 的定稿内容），补齐探针结果的落点（K8），再开第二轮对抗；
第二轮应能收敛到「已收敛，附带 n 条措辞项」（K5/K6 属措辞计数类）。
