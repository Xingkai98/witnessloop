# 独立审阅 R2：#1「无孤儿报告」门禁修复复核（`fix/orphan-report-binding/2026-10-10`）

Verdict: **PASS**

全新零记忆复核。R1 判 CHANGES_REQUESTED 的**两条**（HIGH 整体绕过 §3.2/§3.2′、MEDIUM 非规范路径假阳性 §3.3）
均已**独立复现**确认真修好；两条 LOW（目录名 `.md`、符号链接）也随之消失。我另造 **8 类新绕过/假阳性尝试**
（路径变体、绝对路径、反斜杠、大小写族、符号链接、子目录、多 manifest 同报告、`report_path` 指目录、非 `.md` 报告、
坏 JSON、跳逸 manifest、隐藏文件、symlink 目录）——**无一能关掉/骗过孤儿判定，也无一假阳性**。核心不变式
（`resolve_report_path` 单点解析、逐 manifest 处理）经**变异测试**证明有测试钉住。全量 **308 passed**。

> 复核方式：全部自跑真 CLI（`uv run --project /home/happy/witnessloop witnessloop …`，确为分支代码）+ 自建临时
> git 仓（`/tmp/wlharness2.sh`：真 `init` + 真 `check`）。**未改源码**：变异经「原地改 → 跑 → `git checkout` 还原」
> 并 `md5sum` 复核（见 §5）。工作树全程 `git status` clean。

---

## 0. 复现环境与核对基线

- 复核对象：`git diff main...HEAD`（9 文件 / +732−9；其中 `src/witnessloop/contract.py` +83、`manifestcmd.py` +9、
  `tests/test_orphan_reports.py` +320 新文件）。
- 全量测试：`export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q` → **308 passed**（与修复自述一致；
  R1 时基线 299，`tests/test_orphan_reports.py` 由 7 项增至 16 项 = 该文件净增 **9 项**，即"补 9 条测试"）。
- 外部目标回归仓 `/home/happy/wl-test`（`acid/f1`）用 `git clone` 到 `/tmp` 复核，**原件未动**
  （`git -C /home/happy/wl-test branch --show-current` = `main`，未新增/修改）。

---

## 1. R1 两项的独立复现结论（命令 + 退出码）

### 1.1 R1 §3.2【HIGH · 整体绕过】→ ✅ 已修

构造（`/tmp/r2-case-32`，真 CLI）：`reviews/` 下放文件名含反斜杠的诱饵 `..\..\etc\x.md`（Linux 上合法），
用**真 `manifest build`** 产一份指向它的合法 manifest（`build` exit 0，零 finding），另有正常 manifest 绑
`grill-review.md`，而 `reviews/grill-adversarial.md` **未绑定**（要抓的目标）：

```
$ witnessloop manifest build … --stage zzz --report 'reviews/..\..\etc\x.md' --base main   # BUILD_ZZZ_EXIT=0
  （zzz.manifest.json 落盘 report_path='reviews/..\..\etc\x.md'，_check_hashes 零 finding）
$ witnessloop check --root /tmp/r2-case-32 --base main --head HEAD
check：未通过 ✗（1 项）
  1. openspec/changes/add-retry/reviews/grill-adversarial.md：孤儿报告：reviews/grill-adversarial.md 未被任何 manifest 绑定（…）
CHECK_EXIT=1
```

**结论**：旧版 `bindings_reliable` 的「一份特制 manifest 关掉整条规则」已不复存在。`resolve_report_path` 对反斜杠
不再 `normalize` 成 `/`（Linux 反斜杠是字面文件名字符），`_bound_report` 返回的是**诱饵自身的解析路径**（非 `None`），
孤儿判定**照常执行**并点名未绑定报告。exit 1 ✓。

### 1.2 R1 §3.2′【HIGH · 假绑定 + 真漂移】→ ✅ 已修

构造（`/tmp/r2-case-32p`）：诱饵为直接位于 change 目录、文件名含反斜杠的 `reviews\grill-review.md`；
`manifest build --report 'reviews\grill-review.md'` 绑它（`build` exit 0，`report_path='reviews\\grill-review.md'`）。
随后把**真** `reviews/grill-review.md` 改成未审内容并提交（属证据豁免，不触发区间漂移）：

```
$ witnessloop check --root /tmp/r2-case-32p --base main --head HEAD
check：未通过 ✗（1 项）
  1. openspec/changes/add-retry/reviews/grill-review.md：孤儿报告：reviews/grill-review.md 未被任何 manifest 绑定（…）
CHECK_EXIT=1
```

**结论**：旧版 `normalize` 会把 `reviews\grill-review.md` 折叠成真名，令真报告"看似被绑"；新实现不折叠，真报告的
**解析路径** ≠ 诱饵的解析路径 → 真报告被判定**未绑定 → 孤儿** → 漂移被拦。exit 1 ✓。

### 1.3 R1 §3.3【MEDIUM · 非规范路径假阳性】→ ✅ 已修

对 `manifest build` 的 9 种 `--report` 写法各造一仓，跑 `build` 后 `check`（`/tmp/r2-m-*`）：

| `--report` 写法 | build | check | 孤儿误报 | 落盘 `report_path` |
|---|---|---|---|---|
| `reviews/grill-review.md`（规范） | 0 | 0 | no | `reviews/grill-review.md` |
| `reviews/./grill-review.md` | 0 | 0 | no | `reviews/grill-review.md` |
| `reviews//grill-review.md` | 0 | 0 | no | `reviews/grill-review.md` |
| `reviews/../reviews/grill-review.md` | 0 | 0 | no | `reviews/grill-review.md` |
| `./reviews/grill-review.md` | 0 | 0 | no | `reviews/grill-review.md` |
| `reviews/sub/../grill-review.md` | 0 | 0 | no | `reviews/grill-review.md` |
| 绝对路径（指向本仓内报告） | 0 | 0 | no | `reviews/grill-review.md` |
| `/etc/hosts`（绝对、仓外） | 1 | 1 | no | —（逃逸，拒） |
| `../../../etc/hosts`（相对逃逸） | 1 | 1 | no | —（逃逸，拒） |

**结论**：`build` 落盘**规范化**路径（`manifestcmd.py:73` 取 `resolve()` 后的 `relative_to(directory).as_posix()`），
`check` 与 `build` 共用同一 `resolve_report_path` → **口径一致，不再有"build 说 OK、check 反手判孤儿"**。R1 的
`dotSlash/interiorDot/doubleSlash/interiorDotDot` 假阳性全部消失。

### 1.4 R1 §3.4 / §3.5【LOW · 目录名/符号链接】→ ✅ 一并消失

- 目录 `reviews/notes.md/`：`_check_orphan_reports` 加 `report.is_file()` 过滤 → 不算报告，`check` 绿。
- `reviews/alias.md -> grill-review.md` 只绑链接：两侧都按 `resolve()` 后路径比对，链接与目标解析到同一条目 →
  只算一个报告、`bound` 命中 → 绿。

### 1.5 目标回归（R1 §2）→ ✅ 仍判红

`/tmp/wltest-copy`（clone 自 `wl-test` 的 `acid/f1`）：

```
$ witnessloop check --root /tmp/wltest-copy --base main --head HEAD
check：未通过 ✗（1 项）
  1. openspec/changes/add-greeting/reviews/grill-adversarial.md：孤儿报告：reviews/grill-adversarial.md 未被任何 manifest 绑定（…）
EXIT=1
```

规则命中的正是 #1 要抓的"绑一份、晾一份"。

---

## 2. 新绕过 / 假阳性尝试（全部失败 = 修复稳）

全部在 `/tmp/r2-b*`、`/tmp/r2-symdir` 用真 CLI 实跑。**期望**：能动"未绑定报告"就判红且点名；合法输入则应绿。

| # | 尝试 | 期望 | 实测 | 结论 |
|---|---|---|---|---|
| B1 | 坏 manifest（`report_path` 逃逸）+ 真孤儿 | 孤儿仍报 | 2 项：`逃逸出 change 目录` + 孤儿点名 `grill-adversarial.md`，exit 1 | ✅ 规则未被该 manifest 关掉 |
| B2 | 坏 JSON manifest + 真孤儿 | 孤儿仍报 | 2 项：`manifest 无法解析` + 孤儿点名，exit 1 | ✅ |
| B3 | `report_path` 指向**目录** `reviews/notes.md/` + 真孤儿 | 拒 + 孤儿报 | 2 项：`报告不存在：reviews/notes.md` + 孤儿点名，exit 1 | ✅ |
| B4 | 隐藏报告 `reviews/.hidden.md` 未绑定 | 应被抓 | 孤儿点名 `reviews/.hidden.md`，exit 1 | ✅ `rglob("*.md")` 命中小写开头点文件 |
| B5 | 绑非 `.md`（`reviews/notes.txt`）+ 真孤儿 `.md` | 孤儿仍报 | 孤儿点名，exit 1 | ✅ |
| B6 | 多 manifest 绑**同一**报告 | 允许、绿 | `check：通过 ✓` exit 0 | ✅ 符合文档声明 |
| B7 | 子目录报告 `reviews/sub/deep.md` 被绑 | 绿 | `check：通过 ✓` exit 0 | ✅ `reviews/**` 覆盖任意深度 |
| B8 | 符号链接报告只绑链接（`alias.md->grill-review.md`） | 绿 | `check：通过 ✓` exit 0 | ✅ 解析后去重 |
| B9 | `reviews/` 下**符号链接目录** `linked/`（指向仓外，内含未审 `.md`） | 观察 | 该 `.md` 未被 `rglob` 遍历；但**被"旧 revision"规则抓到**（`outside/secret.md` 改动非证据）exit 1 | ⚠️ 见 §4-1（INFO，非绕过） |

**路径变体/大小写族**：`./`、`//`、`..`、`sub/..`、前导 `./`、绝对（仓内/仓外）、反斜杠（§1.1/§1.2 已覆盖）。
**结论：无新增可绕过路径。**

---

## 3. 逐条核验表（对 R1 停轮项的核对）

| R1 项 | 修复声明 | 我的独立核验 | 结果 |
|---|---|---|---|
| ① 整体跳过（HIGH） | 删掉 `bindings_reliable`，改逐 manifest | `grep bindings_reliable src/` → **零命中**；`validate_review_manifests` 无条件 `findings.extend(_check_orphan_reports(…))`；B1/B2/§3.2/§3.2′ 实测均判红 | ✅ |
| ② 单点解析 | 新增 `contract.resolve_report_path()`，三处共用 | `grep resolve_report_path`：`manifestcmd.py:69`（build）、`contract.py:181`（`_bound_report`）、`contract.py:357`（`_check_hashes`）——**同函数**；无第二处 `report_path` 解析 | ✅ |
| ③ 非规范路径假阳性（MEDIUM） | build 落盘规范化 + check 同口径 | §1.3 表：9 种写法 build/check 全一致 | ✅ |
| ④ 目录名 `.md`、符号链接（LOW） | `is_file()` 过滤 + 按 `resolve()` 比对 | §1.4 实测绿 | ✅ |
| ⑤ 补 9 条测试 | 文件 7→16 项 | `test_orphan_reports.py` 13 函数 / 16 项；净增 9 项；全量 299→308 | ✅ |

---

## 4. 新发现的问题

**无阻塞/高/中问题。** 仅两条记录性观察：

1. **【INFO】`rglob` 不遍历符号链接目录，但其内容被"旧 revision"兜底**（B9）：`reviews/linked -> {仓外目录}` 内的
   `.md` 不被 `reviews/**` 扫描，因此**不参与孤儿判定**。但：(a) 目标通常在 git 之外，不是可随提交漂移的仓内 artifact；
   (b) 我的构造中同一次改动的仓外文件被 `_check_git_span` 的"审阅的是旧 revision"判红。故**不构成 #1 语义下的漂移绕过**，
   仅记录。若要更严，可对 `reviews/` 下的符号链接目录显式拒绝或在文档写明"不跟随"。
2. **【INFO】`resolve_report_path` 对非字符串 `report_path` 做 `str()` 强转**：数字/布尔等会被转成字符串再解析，
   落到"报告不存在"（fail-closed，受控）。与 `_check_git_span` 对 `*_sha` 的 `isinstance` 守卫风格略异，但结果安全。

**"逐 manifest 化"是否引入新假阳性/假阴性**：实测 B6/B7/B8（合法多绑、子目录、符号链接）全绿，§1.3 全部变体全绿 →
**无新假阳性**；B1–B5、§3.2/§3.2′（坏 manifest 并存、孤儿、诱饵）全部仍判红 → **无新假阴性**。`resolve_report_path`
的逃逸判定与 `_check_hashes` **完全一致**（同函数、同返回值语义；`None`→"逃逸"，非 `None` 但 `not is_file()`→"报告不存在"）。

---

## 5. 变异证据（测试是否真保护）

**方法**：原地改 `src/witnessloop/contract.py`（及 `manifestcmd.py`），跑
`uv run pytest -q tests/test_orphan_reports.py tests/test_check_manifest.py tests/test_manifest_build.py tests/test_check_contract.py`
（基线 **82 passed**），随即从 `/tmp/*.bak` 还原并用 `md5sum` 复核（`contract.py` = `05e664c1…`，工作树 clean）。
**未用 `uv run --project <副本>`**（会回落原仓代码，R1 已踩坑）。

| 变异 | 内容 | 结果 | 钉住它的测试 |
|---|---|---|---|
| M1 | `_check_orphan_reports` 直接 `return []`（关规则） | **5 failed** | orphan 主用例、子目录、backslash、broken、round-trip |
| M2 | 成员判断取反（`in`→`not in`） | **24 failed** | 大面积 |
| M3 | 恢复"整体跳过"（任一 manifest 无绑定则不跑孤儿） | **1 failed** | `test_broken_report_path_does_not_disable_the_orphan_rule` |
| M4 | `build` 存**原始**（未规范化）`report_path` | **1 failed** | `test_build_stores_a_canonical_report_path` |
| M5 | `resolve_report_path` 去掉逃逸守卫（永不返回 `None`） | **2 failed** | `test_check_manifest::…escaping…`、`test_manifest_build::…escaping…` |
| M6 | `resolve_report_path` 重新 `normalize`（R1 旧口径） | **0 failed** | 无（**已验证为良性**，见下） |
| M7 | `resolve_report_path` 不做 `resolve()` | **3 failed** | variant[`../..`]、canonical、symlink |
| M8 | 孤儿侧比较不 `resolve()`（`report.resolve()`→`report`） | **1 failed** | `test_symlinked_report_is_not_an_orphan` |

**M6 说明**：M6 把反斜杠重新当分隔符，看似能复活 R1 口径分歧，但新架构下 `build`/`_check_hashes`/孤儿绑定**同一函数**，
`normalize` 会**两侧一致**地应用，故不产生单边分歧。我**实跑 M6** 复核：§3.2（诱饵 `build` 因 normalize→逃逸被拒，
孤儿仍判红 exit 1）、§3.2′（`report_hash 不匹配` 判红 exit 1）——**两条绕过均未复活**。故 M6 全绿属合理，非"盲区"。

对照 R1 §5 的三条盲区：**MU3（跳过逻辑）** ↔ M3 已能被 `test_broken_report_path` 判红；**MU4（`None` 分支）** ↔ M5 判红；
**MU5（路径规范化）** ↔ M4/M7/M8 判红。**R1 的测试盲区已被补齐。**

---

## 6. 回归

- **目标**：`acl/f1`（外仓 clone）判红点名未绑定报告 —— §1.5 ✅
- **全量**：`uv run pytest -q` → **308 passed**（全程 clean，无既有合法 change 被新规则判红）
- **文档/模板/适配器一致**：`docs/gate.md §3`、`templates/grill.md`、`plugin/commands/grill.md` 均写明"每个审阅报告各配
  一份 manifest / 各跑一次 build"，并各有一条测试（`test_grill_template_requires_one_manifest_per_report`、
  `test_grill_adapter_builds_one_manifest_per_report`）钉住 —— ✅

---

## 7. 判定

R1 的 **HIGH 绕过（§3.2 / §3.2′）**与 **MEDIUM 假阳性（§3.3）**均**独立复现确认已修**，两条 LOW 亦消失；
`report_path` 解析已收敛为**单点**（build / hash 校验 / 孤儿绑定三处共用），**整体跳过被删除**改逐 manifest，
补测试覆盖了 R1 指出的三条盲区。8 类新绕过/假阳性尝试无一得手，变异测试证明关键不变式有测试钉住。
仅两条 INFO 级观察，不阻塞。

**Verdict: PASS**
