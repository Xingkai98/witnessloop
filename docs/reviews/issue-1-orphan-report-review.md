# 独立审阅：#1「无孤儿报告」门禁（`fix/orphan-report-binding/2026-10-10`）

Verdict: **CHANGES_REQUESTED**

核心规则（`reviews/**/*.md` 每个报告都要被某份 manifest 绑定）在**目标 case 上确实生效**，
且经得起一次变异核验。但「**任何一个 manifest 解析不出 `report_path` → 孤儿判定整体跳过**」
这条收尾判断**不成立，构成一条真实的整体绕过**（1 份特制 manifest + 1 个怪名文件即可让
未绑定的对抗报告绿着通过）。另有一类**假阳性**：合法（`manifest build` 自己接受）的非规范
路径会让被正确绑定的报告被误报为孤儿。二者叠加，判 CHANGES_REQUESTED。

以下所有结论均**实测复现**，不看自述。

---

## 0. 复现环境

- 审阅对象：`git diff main...fix/orphan-report-binding/2026-10-10`（7 文件 / +277 行）。
- CLI：`uv run --project /home/happy/witnessloop witnessloop …`（确为分支代码——新规则在
  真实仓上生效才可能复现下面结果）。
- 全量测试：`export PATH=/home/happy/.local/bin:$PATH && uv run pytest -q` → **299 passed**。
- 造场景：`/tmp/wlharness.sh`（真 git 仓 + 真 `init` + 真 `check`），报告/manifest 用真
  CLI `manifest build` 产，仅有必要时手写 manifest（agent 可写 JSON，等价输入面）。
- **只读约束**：原始 `/home/happy/wl-test` 未改（`git status` 无本次引入的改动）；
  需要 checkout 的动作一律在 `/tmp` 的副本里做；工作树 `git status` 全程 clean。

---

## 1. 逐项核验表

| # | 核验项 | 方法（实跑） | 结果 |
|---|---|---|---|
| a | 目标 case 能抓（acid test 判红） | 见 §2 | ✅ 正确判红并点名 |
| b | 张冠李戴（manifest 绑别的报告） | 见 §3.1 | ✅ fail-closed，红 |
| c | 前导 `./` 变体 | `/tmp/case-var-dotSlash` | ✅ 正常，绿 |
| d | 内部 `./`、`//`、`..` 变体 | `/tmp/case-var-*` | ❌ **假阳性**（§3.3） |
| e | 大小写变体 | 未单独造（Linux 大小写敏感，与 d 同类：`normalize` 不折叠大小写） | ⚠️ 同 d 机制 |
| f | 报告放子目录 | 测试 `test_reports_nested_deeper_are_also_checked`（299 全绿） | ✅ 覆盖 |
| g | 非 `.md` 扩展名 | 测试 `test_extra_non_markdown_files_are_not_orphans` | ✅ 忽略（设计如此） |
| h | 报告是符号链接 | `/tmp/case-symlink` | ⚠️ **假阳性**（§3.5） |
| i | 多份 manifest 指同一报告 | `/tmp/case-multi` | ✅ 允许，绿（文档已声明） |
| j | 一份 manifest 指多报告 | schema `report_path` 是单字符串 | ✅ 结构上不可能 |
| k | 作者那条判断（None ⇒ 该 manifest 已败） | 见 §4 | ❌ **被证伪——可绕过** |
| l | 回归：M3 acid test 的 `wl-test` change | 见 §2 | ✅ 新规则下**判红**（正是 #1 要抓的） |
| m | 回归：既有合法 change 不被误判 | 299 passed | ✅ 除 d/h 类边缘输入外无回归 |
| n | 测试是否真保护 | 变异 5 条，见 §5 | ⚠️ 核心规则保护到位；**跳过逻辑/None 分支/路径规范化零覆盖** |

---

## 2. 目标 case 判红（✅ 规则本身有效）

原始 `/home/happy/wl-test` 在 `acid/f1` 分支上的 change `add-greeting`，其 `reviews/` 有
`grill-adversarial.md` 但**没有** `grill-adversarial.manifest.json`——正是 #1 描述的形状。
在**副本**（`/tmp/wltest-copy`，`git checkout acid/f1`，原件未动）上跑：

```
$ uv run --project /home/happy/witnessloop witnessloop check \
    --root /tmp/wltest-copy --base main --head HEAD
check：未通过 ✗（1 项）
  1. openspec/changes/add-greeting/reviews/grill-adversarial.md：孤儿报告：reviews/grill-adversarial.md 未被任何 manifest 绑定（…）
EXIT=1
```

结论：**规则命中了它要抓的漏洞**，报错路径/信息准确。

---

## 3. 发现的绕过 / 假阳性

### 3.1 张冠李戴：fail-closed ✅（这不是漏洞）

`grill.manifest.json` 的 `report_path` 指向 `reviews/building-review.md`（hash 同步改成
building 的），另有 `building.manifest.json` 也指 building：

```
check：未通过 ✗（2 项）
  1. …/reviews/grill-adversarial.md：孤儿报告：…未被任何 manifest 绑定
  2. …/reviews/grill-review.md：孤儿报告：…未被任何 manifest 绑定
EXIT=1
```

两份该绑的报告都被点名——方向正确。

### 3.2 【HIGH · 绕过】`bindings_reliable` 的整体跳过可被单份 manifest 触发

`contract.py:150` 只有 `if bindings_reliable:` 才跑 `_check_orphan_reports`。只要**任意一份**
manifest 让 `_bound_report()` 返回 `None`，**全部**孤儿判定被跳过。作者的辩护是「那份 manifest
自己已经被 `_validate_one` 报错了」——**存在反例**（见 §4）。

根因：`_bound_report`（`contract.py:155`）与 `_check_hashes`（`contract.py:339`）对
`report_path` **不同口径**：

- `_check_hashes` 用**原始**字符串 `(directory / doc["report_path"]).resolve()`；
- `_bound_report` 先 `pathutil.normalize(raw)`（`paths.py:13`，把 `\` → `/`）再
  `is_within(...)` 判是否逃逸，**逃逸就返回 `None`**。

在 Linux 上反斜杠是**普通文件名字符**，于是两边分道扬镳。

**复现**（`/tmp/case-backslash3`）：`reviews/` 下放一个**文件名含反斜杠**的文件
`..\..\etc\x.md`，再放一份清单 `zzz.manifest.json`，其 `report_path = "reviews/..\..\etc\x.md"`、
`report_hash` = 那个怪名文件的 hash、其余字段全合法；另有一份正常 manifest 绑 `grill-review.md`；
`reviews/grill-adversarial.md` **未绑定**（就是要藏的目标）：

```
$ uv run --project /home/happy/witnessloop witnessloop check --root /tmp/case-backslash3 --base main --head HEAD
check：通过 ✓
EXIT=0
```

`_check_hashes` 认反斜杠为字面文件名 → 找到怪名文件、hash 对得上 → **零 finding**；
`_bound_report` 把 `\`→`/` 后变成 `reviews/../../etc/x.md`（逃逸）→ 返回 `None` →
`bindings_reliable=False` → **孤儿判定整体跳过** → 未绑定的 `grill-adversarial.md` 绿着通过。

即：#1 想堵的「对抗报告不绑也能漂移」被一句话（一份特制 manifest）整体关掉。

### 3.3 【MEDIUM · 假阳性】非规范但可解析的 `report_path` 误报孤儿

`_bound_report` 返回的是 **`normalize` 后未折叠**的字符串，而 `_check_orphan_reports`
（`contract.py:191`）用 `report.relative_to(directory).as_posix()` **规范**路径比对。
凡 `normalize` 不折叠的写法（内部 `./`、`//`、`..`）都会**匹配不上**，导致被正确绑定的报告
被误报孤儿——且 `manifest build` **自己接受**这些写法（返回 0）：

```
tag                    build   check_exit   孤儿误报
canonical              0       0            no
dotSlash (./reviews/…) 0       0            no
interiorDot            0       1            YES   # reviews/./grill-review.md
doubleSlash            0       1            YES   # reviews//grill-review.md
interiorDotDot         0       1            YES   # reviews/../reviews/grill-review.md
```

例（`/tmp/case-dotdot`）：

```
$ witnessloop manifest build … --report 'reviews/../reviews/grill-review.md' …
manifest build：已写入 openspec/changes/add-retry/reviews/grill.manifest.json（未 commit）
BUILD_EXIT=0
$ witnessloop check --root /tmp/case-dotdot --base main --head HEAD
check：未通过 ✗（1 项）
  1. …/reviews/grill-review.md：孤儿报告：reviews/grill-review.md 未被任何 manifest 绑定
```

`manifest build` 说 OK、`check` 立刻判孤儿——正是 `manifestcmd.py:60` 注释里明确要避免的
「build 报成功、check 立刻拒」自相矛盾。审核者只要 `--report` 里多打一个 `./`，合法的 change
就红。这不是恶意输入，是**正常用户可踩**的假阳性。

（大小写变体同源：`normalize` 不折叠大小写，`Reviews/x.md` 与 `reviews/x.md` 同样匹配不上，
且在 `_check_hashes` 侧还会先报「报告不存在」。）

### 3.4 【LOW · 假阳性】目录名以 `.md` 结尾被当成「报告」

`reviews.rglob("*.md")` 也匹配**目录**。`reviews/notes.md/` 是目录时：

```
check：未通过 ✗（1 项）
  1. …/reviews/notes.md：孤儿报告：reviews/notes.md 未被任何 manifest 绑定
```

把非报告（目录）报成孤儿报告。文档声明「只对 `.md` 报告做交叉引用」，但这里把目录也算成了报告。

### 3.5 【LOW · 假阳性】符号链接报告

`reviews/alias.md -> grill-review.md`，manifest 绑 `reviews/alias.md`（hash 跟链，`_check_hashes`
接受），但真正目标 `grill-review.md` 被误报孤儿（`/tmp/case-symlink`，EXIT=1）。链接与目标在
`rglob` 里是两个名字，`bound` 只有一个，必然误报其一。

---

## 4. 作者那条判断的核验：❌ 被证伪

> 作者理由：「manifest 解析不出 `report_path`（坏/缺字段/逃逸）时，孤儿判定整体跳过——
> 那份 manifest 自己已败（fail-closed），再扣孤儿是误指；故不构成绕过。」

**不成立。** 存在一份 manifest：`_bound_report()` 返回 `None` **且** `_validate_one()`
**零 finding**——即「解析不出绑定」与「该 manifest 已失败」**不等价**：

- `_bound_report` 的 `None` 条件 = `is_within(directory / normalize(raw))` 为假；
- `_validate_one` 的失败条件 = 缺字段 / `report_path` **原始**串 `resolve()` 逃逸 / 文件不存在 /
  hash 不匹配 / 区间漂移。

§3.2 的构造正好落在两条判据的缝隙里：`normalize(raw)` 逃逸（→ `None`）但**原始** `raw` 是一个
存在的字面文件名、hash 匹配（→ 零 finding）。因此「跳过」不是「重复扣分」，而是把一个**本该报红
的未绑定报告**放行。§3.2 / §3.2′（下）都是它的实测后果。

**§3.2′【HIGH · 绕过】** 同一缝隙还能造「假绑定 + 真漂移」：manifest 的
`report_path = "reviews\grill-review.md"`（反斜杠），`report_hash` 绑的是**另一个**诱饵文件；
于是孤儿检查认为**真** `reviews/grill-review.md` 已被绑定（`normalize` 折叠成真名），而
`_check_hashes` 校验的是诱饵。随后把真报告改成未审内容提交（它在 `reviews/` 下，属证据豁免，
不触发区间漂移判定），其字节**从不被校验**：

```
$ uv run … check --root /tmp/case-fakebind --base main --head HEAD
check：通过 ✓
EXIT=0     # 而 reviews/grill-review.md 已被改成 "REAL report DRIFTED (unreviewed content)"
```

这正是 #1 要消灭的「报告可漂移而门禁不管」，只是换了条缝进来。

---

## 5. 变异证据（测试是否真保护）

在**副本** `/tmp/wl-mut` 上做变异；注意坑：直接 `uv run --project /tmp/wl-mut pytest` 会因
`witnessloop` 的 editable 安装**回落到 `/home/happy/witnessloop/src`**（我第一轮就被它骗到，
变异全绿）。**必须**加 `PYTHONPATH=/tmp/wl-mut/src` 才能让变异真正生效——已在
`test_zzdebug` 里确认 `MODULE: /tmp/wl-mut/src/...`。

| 变异 | 内容 | `tests/test_orphan_reports.py` |
|---|---|---|
| 基线 | 未变异 | 7 passed |
| MU1 | `_check_orphan_reports` 直接 `return []`（关掉规则） | **3 failed** ✅ 保护到位 |
| MU2 | 成员判断取反（`in`→`not in`） | **6 failed** ✅ 保护到位 |
| MU3 | 去掉 `if bindings_reliable:`（永远跑孤儿检查） | 7 passed ❌ **无测试钉住跳过逻辑** |
| MU4 | `_bound_report` 去掉逃逸守卫（不返回 `None`） | 7 passed ❌ **`None` 分支零覆盖** |
| MU5 | `_bound_report` 改成 resolve 规范化（假阳性候选修法） | 7 passed ❌ **路径规范化零覆盖** |

解读：**核心规则**（能抓孤儿）有测试保护；但**跳过这条**（MU3）、`_bound_report` 的
`None` 分支（MU4）、以及 `normalize`/resolve 口径不一致（MU5）——**全部零覆盖**。
换句话说，§3.2 的绕过路径与 §3.3 的假阳性路径**没有任何测试会拦**，改好改坏都不会变红。

---

## 6. 回归（#4 专项）

- **目标回归**：M3 acid test 的 `wl-test` change（只有 `grill.manifest.json` +
  `building.manifest.json`，无 `grill-adversarial.manifest.json`）在**新规则下判红**——见 §2，
  这就是 #1 要抓的，✅。
- **既有全量**：299 passed，无既有合法 change 被新规则判红（除 §3.3 / §3.5 那几类边缘输入——
  它们不在既有测试集里）。
- ⚠️ 提醒：§3.3 意味着「用非规范 `--report` 跑过 `manifest build` 的合法 change，升级后会突然判红」。

---

## 7. 停轮问题（阻塞项）

1. **【必须修】整体跳过不可接受**：`bindings_reliable` 是「全有全无」，一份特制 manifest 即可
   关掉整条规则（§3.2 / §3.2′）。可行方向：
   - 让 `_bound_report` 的 `None` 判据**与** `_validate_one` 的失败判据**同口径**（同一处
     resolve/is_within 逻辑、同一份 `report_path` 取值），消灭两条判据的缝隙；**并/或**
   - 不再用「任何一个 None 就整体跳过」，而是逐 manifest 处理：无法解析的 manifest 只令**它自己**
     的绑定缺失，孤儿判定照常对其余报告执行（宁多报，不漏报，符合 fail-closed 精神）。
2. **【应修】非规范路径假阳性**（§3.3）：`manifest build` 与 `check` 对 `report_path` 规范化
   要一致——统一 `resolve()` 成 change 目录内 posix 相对路径后再做交叉引用（MU5 即是此候选，
   当前无测试）。
3. **【建议】补测试**：至少覆盖 MU3（跳过逻辑）、MU4（`None` 分支）、MU5（非规范路径）三条
   盲区，否则这次修的洞下次会被同一处缝隙原样绕过。
4. **【次要】** 目录名以 `.md` 结尾、符号链接目标被误报（§3.4 / §3.5）：`rglob` 加 `is_file()`
   过滤、或对链接取真实路径，可一并消除。

---

## 附：复现清单（可逐一重跑）

- 目标 case：`/tmp/wltest-copy`（`acid/f1`）→ `check` 判红，点名 `grill-adversarial.md`。
- 张冠李戴：`/tmp/case-misbind` → 判红，两份都点名。
- 假阳性：`/tmp/case-var-{interiorDot,doubleSlash,interiorDotDot}` → `build=0 / check=1`。
- 绕过（整体跳过）：`/tmp/case-backslash3` → `check：通过 ✓（EXIT=0）`，而
  `reviews/grill-adversarial.md` 未绑定。
- 绕过（假绑定 + 真漂移）：`/tmp/case-fakebind` → `check：通过 ✓（EXIT=0）`，而
  `reviews/grill-review.md` 已被改。
- 假阳性（目录/链接）：`/tmp/case-dirmd`、`/tmp/case-symlink`。
- 变异：`/tmp/wl-mut`，务必带 `PYTHONPATH=/tmp/wl-mut/src`。
