# Tasks: gate-ref-pins-package

> **停轮门已解除**（用户 2026-10-16 裁定 Q1–Q5，见 `design.md §8` 与
> `reviews/grill-design.md` 的 `## User Confirmation`）。实现按本文件执行。
>
> 本 change 的风险不是「改不动」，而是**把 `init` 的既有契约（幂等 / 只增不改）撞坏**、
> 以及把一次**全局**行为变化（新 ref 发布那一刻）当成局部改动发布。

## 0. 设计追问与用户确认（前置门）

- [x] 0.1 独立零记忆 grill → `reviews/grill-design.md`（`## Confirmed Decisions` ≥3 条、每条带 `来源:`；
      `## Open Questions`；`## User Confirmation`）。
- [x] 0.2 把停轮问题逐条抛给用户（各附具体例子与推荐）。
- [x] 0.3 答复逐条记进 `reviews/grill-design.md` 的 `## User Confirmation`（Q1–Q5，无「按推荐」类占位）；
      `design.md §8` 同步为「裁定」，两份文件的 **Q 集合 = {Q1…Q5}** 逐条一致。
- [x] 0.4 对抗轮（独立零记忆，**无轮数上限、收敛才停**）→ `reviews/grill-adversarial*.md`
      （**裁定 Q2（多轮报告的落点）**：报告留在 `reviews/`，多出来的轮次**各用一个不同的 stage 名**
      ——`grill-adversarial-r2` / `-r3`…… 见 `design.md §7.9` 的 Q2 与 `docs/gate.md §3`。
      另一条路是放到 `reviews/` 之外（先例 `archive-arrival-recognition/rounds/`），**本 change 不混用**）。

## 1. 规格

- [x] 1.1 `specs/gate-ref-pinning/spec.md`：按 Q1 裁定 (B′) 定稿「单一入口」与「不静默」两条 Requirement
      （含 K1 订正：包**能**自报 ref）。
- [x] 1.2 同步 `docs/gate.md` / `README.md` / `docs/design.md` 的接入指引（怎么钉版本 / 怎么升级）。

## 2. 测试（先行）

- [x] 2.1 解析面：从 `gate.yml` 抽出解析 step、用 `bash` 真跑（`GITHUB_OUTPUT` 捕获结果），覆盖
      `job.workflow_sha` 主路径 / 显式 `with:` 覆盖 / repository 不匹配 / sha 缺失走 `job.workflow_ref`
      兜底（`refs/heads/*`、`refs/tags/*`）/ 两样都缺 / `refs/pull/N/merge` 畸形 ⇒ fail-closed 退兜底 ref + warning。
- [x] 2.2 生成面：`init --gate-ref <ref>` 生成的 caller 里 `uses:` 逐字等于该 ref（(B′) 下 `caller_workflow()` 字节不变）。
- [x] 2.3 升级路径：显式 `--gate-ref` 的覆盖语义（重写 caller + 同步台账 `sha256`/`gate_ref`、EXIT=0、
      随后 plain `init` 幂等、`uninit` 仍可用）+ plain `init` 的幂等回归 + 新仓目标文件已存在仍冲突。
- [x] 2.4 日志面：`gate.yml` 把 ref 打进 `::notice::` 的那一步（断言文件内容）。
- [x] 2.5 自报面：`check` 读 `direct_url.json` 的最佳努力实现（有 `vcs_info` ⇒ 打出；没有 ⇒ `<未知>` 且不影响退出码）。
- [x] 2.6 回归：`init` 幂等 / `uninit` 回滚 / 冲突判定 / tests 文件独立路径。

## 3. 实现

- [x] 3.0 **真 CI 探针（Q1 的输入）—— 已跑成并定案**：跨仓形态（副本仓 `Xingkai98/asterwynd-wl-switch`
      的 caller → `Xingkai98/witnessloop/.github/workflows/probe-ref.yml@probe/workflow-ref`，run `38853369550`）
      实测 `job.workflow_sha` = reusable 自己的 commit、`github.workflow_sha` = 接入方自己的 commit
      ⇒ 定案 (B′)。**落点**：原始输出写进 `design.md §2 D1`（K8 要求的「结果贴回哪里」）。
      探针用的分支与文件**远端已全部删除**（复查 404）；**本地仍留** `probe/workflow-ref`
      分支（`c7aa037`）——它是 Q1 唯一可追溯的本地物证，刻意不删（R2 的 D4 订正措辞）。
- [x] 3.1 `.github/workflows/gate.yml`：`inputs.witnessloop-ref.default` 改 `""`；新增**第一个 step**
      （`id: wl-ref`）按 (B′) 解析并打 `::notice::`/`::warning::`；`uvx` 改用 `steps.wl-ref.outputs.ref`。
      接受判据 = `job.workflow_repository == constants.REPO_SLUG`，否则 fail-closed 退**兜底 ref**
      （= `DEFAULT_GATE_REF` 的 ref 部分，与它同源）并打日志（M7）。
- [x] 3.2 `src/witnessloop/initcmd.py`：已接入分支里，显式 `--gate-ref` ⇒ 重写 caller + 同步台账（Q2 (a)）。
- [x] 3.3 `src/witnessloop/checkcmd.py`：自报本包 VCS ref（Q4 (a)，尽力而为）。
- [x] 3.4 文档：`docs/gate.md`（§1 caller 行 + **§7 能力边界**加 Q5 的登记）、`README.md:20,119-121,170-177`、
      `docs/design.md:56,73`（K6）。
- [ ] 3.5 **`(post-merge)` 本仓自身迁移**：**不在本 PR 内**（design §2 D4：目标 ref 只在合并后才存在）——
      更新 `.github/workflows/witnessloop.yml` + `.witnessloop/init-manifest.json`，并建
      `openspec/changes/gate-ref-pins-package/workflow-events.jsonl` 写一条 `protected_path_write`
      （`artifact_path` 指向 `.witnessloop/init-manifest.json`、`reason`/`approved_by` 非空），
      否则改台账这个 `M` 必红。

## 4. 验证

- [x] 4.1 `uv run pytest -q` 全绿。
- [x] 4.2 端到端复验：改 `uses:` 一处之后，CI 日志里的 `witnessloop@<ref>` 跟着变（由 3.0 的跨仓探针实证）。
- [x] 4.3 本仓自举 `check` 判绿（`check --base origin/main --head HEAD` ⇒ 通过 ✓）。

## 5. 收尾

- [x] 5.1 实现后独立审阅闭环 → `reviews/building-review.md`（**B1–B5 五轮**；
      B5 判**通过**）。后续轮次的报告按 M2 的约定各用不同 stage 名。
- [ ] 5.2 归档 / 回链 issue #30。
      ⚠️ **归档之前**先把 manifest 补齐（对抗轮 R3 的 M2）：本 change 的 `reviews/` 会有
      **多份** `.md`（`grill-design` / `grill-adversarial`（R1）/ `-r2`…`-r11` / `building-review` —— 
      **按语义数，别按这里的清单数**：对抗轮跑到收敛为止，清单会继续长），
      而 `manifest build` 的落盘名是 `reviews/<stage>.manifest.json` ⇒ **同 stage 会静默覆盖**。
      ⇒ **每份报告各配一份 manifest**，多出来的对抗轮用**不同的 stage 名**
      （`--stage grill-adversarial-r2` / `-r3`；实测 0 条孤儿，必备 stage 判定照旧满足）。
      约定与陷阱已写进 `docs/gate.md §3`；⚠️ 文档面上 `stage` 名同时决定 `workflow-events`
      的解读惯例，别只改一半。

## 6. `(post-merge)` 待办（Q3 裁定；**本 PR 内一律不做**）

> ⚠️ **时序是承重的，别调换**（对抗轮 R2 的 L1 实测指出：原稿「先 tag 后改默认值」会让打出的
> `v1.7.0` 里常量仍是 `@v1` ⇒ 用 `@v1.7.0` 装的 CLI 生成的 caller 还是 `uses:@v1` ⇒
> **Q3 的收益在发布那一刻就落空**，而且落空得更隐蔽：接入方以为自己钉了 v1.7.0）。
> ⇒ **被 tag 的那个提交，必须已经含常量改动。**

- [ ] 6.1 **先**改默认值：`DEFAULT_GATE_REF` 从 `…gate.yml@v1` 改成 `…gate.yml@v1.7.0`。
      它不是一处、而是一个**只改一处就会红**的字面量族（对抗轮 R3 的 M1 逐条实测）。
      **改完这四处之后 `pytest -q` 必须全绿**（本 change 已按此**实跑验证**过一次：
      模拟执行下列改动 ⇒ 全绿；**不改**则至少一条红）：
      1. `src/witnessloop/constants.py` 的 `DEFAULT_GATE_REF`；
      2. `.github/workflows/gate.yml` 的 `WL_FALLBACK_REF` 字面量——fail-closed 的落点
         **与 `DEFAULT_GATE_REF` 的 ref 部分同源**（由 *三条*钉住：
         `test_resolve_constants_match_the_single_source` 比 env 字面量、
         `test_resolve_reads_the_fallback_ref_from_its_env` 比**行为**（换哨兵值 ⇒ 输出跟着变）、
         `test_resolve_script_reads_both_constants_from_the_environment` 比 `run` 里有没有**读**它——
         R7 的 U2 证明只靠第一条会被「把字面量硬编进脚本」蒙过去）。见下面 Q1 的裁定；
      3. `tests/test_gate_workflow.py::test_caller_ref_matches_this_repo` 的 `== …@v1` 断言；
      4. ⚠️ **没有第 4 处要改**，但有一条**前提**要保住：
         `tests/test_init_gate_ref.py` 的 `NEW_REF` 必须是**不可能等于出厂默认**的 ref
         （现取 `…@v9.9.9`），且 `test_new_ref_does_not_collide_with_the_factory_default`
         把这条前提钉住了。R3 的原始发现正是「`NEW_REF` 撞上新默认 ⇒ 5 条用例的前提静默塌掉」。
      ⚠️ 顺带**全仓活面**核一遍还有没有把兜底落点/当前默认写成固定 `v1` 的句子——
      **自查面必须覆盖 `src/`、`tests/`（含 docstring）、`docs/`、`README.md` 与 `.github/`**，
      不能只查文档（对抗轮 R4 的 N3：上一轮的自查只点名 `docs/` 与 `README.md`，结果漏了
      `design.md` 的 §4 R6 表、`tests/` 的 docstring、`docs/gate.md §7.1` 三处）。
      历史引文、错误信息复现那类**保留**；机制描述一律写成「兜底 ref（= `DEFAULT_GATE_REF` 的 ref 部分）」。
      **自查面还要包含 `openspec/`**（R5 实测：上一轮漏网的三处之一就在 change 文档里），
      并**用「已知会漏的形态」试一下这条 grep 真的抓得到**（R5 拿四种形态试，四种全漏——
      单一字面 grep 抓不住「兜底落点被写成固定 tag」的所有变体）。
      可用的起手式（**抓到之后逐条人判**：历史引文/错误信息复现保留，机制描述要改）：
      ```bash
      grep -rn "v1" --include=*.md --include=*.py --include=*.yml src/ tests/ docs/ README.md .github/ \
        openspec/changes/gate-ref-pins-package/
      ```
      ⚠️ 它是 `src/**` 改动 ⇒ 走本仓自己的门禁（change 证据）。**做法**：本 change **先不归档**
      （见 5.2），这一步挂在**本 change 目录**下、按既有流程重建全部 manifest。
      ⚠️ **重建 manifest 必须绑在「最后一条非证据提交」上**（R3 的 M3，见下）：
      `head_sha` 之后**只允许**出现证据文件（`reviews/*.md`、`reviews/*.manifest.json`）——
      「本 PR 自己的变更」（非证据）落在它之后**正是**判 stale 的那条规则所禁止的
      （`contract.py` 的 revision 绑定；R3 实测：改一个非证据文件 ⇒ 每份 manifest 各报一条
      `审阅的是旧 revision：… 之后又改动了非证据文件：…`）。
      ⇒ 顺序是：先落地 6.1 的四处改动 → 提交 → **再**重建 manifest → 提交证据。
      ⚠️ 重建 manifest 是**修改**不变集里的 `**/reviews/*.manifest.json` ⇒ `check` 要一条
      `protected_path_write` 解释事件**（`policy.py` 的 `INVARIANT_PROTECTED_PATHS` 含该 glob；
      「不变集 + `A` 免事件」只对**新增**成立；R3 实测确认）。这一步的事件要一并写进
      `workflow-events.jsonl`。
- [ ] 6.2 **再**建 tag **`v1.7.0`**，指向**含 6.1 改动**的最新 `main` 提交。
- [ ] 6.3 同步安装文档的字面量：**`README.md` 里把 `@v1` 当「当前值」写的每一处**都要改
      （R9 的 W4：早先只点名了 `README.md:20` 的 `uv tool install …@v1`，漏了
      「怎么钉版本 / 怎么升级」那段里的 `# ⚠️ v1.7.0 发布前请用 @v1` 与
      `# 旧的 @v1 包没有这一行`——6.2 之后它们会变成**错的建议**）。
      ⚠️ **按语义找、别按行号找**：行号会漂，用
      `grep -n "@v1" README.md docs/gate.md` 逐条人判（历史引文/错误信息复现保留）。
      它是 `docs` 面、不需要 change 证据，但**必须与 6.2 同一个提交**，否则 tag 里的安装指引是旧的。
- [ ] 6.4 完成 3.5 的本仓自身迁移（caller + 台账 + 解释事件）。
- [ ] 6.5 **发布说明**里写清这是一次**全局**行为变化（design §4 R2），且**要点名两类仓**
      （R2 的 L6：原稿只说了一类，把全局面说小了）：
      ① 把 `uses:` 指到含新 `gate.yml` 的 ref 的仓——**在它们动手的那一刻**切换；
      ② `uses:` 写成**分支形态**（如 `@main`）的仓——**在本 PR 合并那一刻**就零动作切换了包来源。
      回退路径：指回旧 ref，或显式 `with: witnessloop-ref:`。
- [ ] 6.6 ⚠️ **不动 `v1` tag**（它是别人依赖的发布物）。
- [ ] 6.7 **验收命令**（可复算；对抗轮 R3 的 M2：`--dry-run` **打不出 caller 的内容**
      ——它只列文件名，所以要看内容必须真落盘到一个 scratch 目录）：
      ```bash
      rm -rf /tmp/wl-v17 && mkdir -p /tmp/wl-v17
      uvx --from "git+https://github.com/Xingkai98/witnessloop@v1.7.0" \
        witnessloop init --root /tmp/wl-v17
      grep -h 'uses:' /tmp/wl-v17/.github/workflows/witnessloop.yml   # -h：不带行号前缀
      ```
      ⇒ 那一行 SHALL 逐字是
      `    uses: Xingkai98/witnessloop/.github/workflows/gate.yml@v1.7.0`。
      在此之前，README 里那条 `@v1.7.0` 的 recipe 都会指向一个**还不存在**的 ref。
      附带的两条自查：`uvx …@v1.7.0 witnessloop check --root /tmp/wl-v17 --base main --head HEAD`
      的输出里 SHALL 有 `本包来源（自报，尽力而为）：requested_revision=v1.7.0`（Q4 的能力在
      真 CI 之外的第一个可见处）；`git show v1.7.0:src/witnessloop/constants.py | grep DEFAULT_GATE_REF`
      SHALL 含 `@v1.7.0`（R2 的 L1：**被 tag 的提交自己必须已经是新值**）。
