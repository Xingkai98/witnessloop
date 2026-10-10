# 独立审阅：issue #3（run id 确定性）实现

Verdict: **CHANGES_REQUESTED**

被测对象：分支 `fix/run-id-determinism/2026-10-10`（head `dbf1134`），对比 `main`。
基线：`uv run pytest -q` → **325 passed**（与声明一致）。
本审阅为**全新零记忆**：独立读代码、独立跑真 CLI、独立做变异，未采信任何自述。

核心结论：**Q1 / Q2 / Q4 / ① 都真的照定稿落地了，且有能被变异变红的测试保护**（见下）。
**Q3 只落了一半**——`docs/design.md`、`docs/gate.md`、`plugin/*`、`agentenv.py` 的口径已统一，
但 **`templates/review-loop.md:17`（用户可见模板）与 `src/witnessloop/manifestcmd.py:125`（用户可见报错）
仍写着已被否定的「挡『忘了另开 run』」**，与同一文件/同一代码里新写的「结构性恒真、只挡显式喂同值」**自相矛盾**。
另外 **CD8 要求加的那道文档守卫，抓不到 CD8 点名的那句话**（「给了才幂等」）——守卫挂上了，但没挂在目标上。
两处都是小改，因此判 CHANGES_REQUESTED 而非 BLOCKED。

---

## 1. 逐条核验表（含实测命令 / 结果）

所有真 CLI 实测在 scratch 仓（`/tmp/wl-scratch/repo{,2}`）跑，无 `WITNESSLOOP_*` 环境变量：

```
git init -b main; git commit 初始化
uv run --project <repo> witnessloop init --root <R>; git commit 接入
git checkout -b feature; git commit 内容(add-retry: proposal/design/tasks/specs/reviews)
printf 'PASS\n' > openspec/changes/add-retry/reviews/building-review.md   # 报告未提交
```

| # | 定稿要点 | 实现落点 | 实测（命令 → 结果） | 判定 |
|---|---|---|---|---|
| Q1 | anchor = `change_id` + `head_sha` 短摘要，**≥12 位** | `agentenv.py:41`（`ANCHOR_DIGEST_LEN = 12`）、`:49-55`（`default_run_anchor`） | `manifest build --base main` → `reviewer_run_id=building-reviewer-add-retry-4b071dafb925`；摘要 `4b071dafb925` **恰 12 位**，取自 `head_sha=4b071da…` | ✅ |
| Q2 | 幂等键含 base；「逐字节可复现」仅限固定 base+revision；补反向断言 | `agentenv.py:9-23` 文档；`manifestcmd.py:111-114` 注释；`cli.py:72-76` help；`tests/test_manifest_build.py:215-273` | 固定 base 连跑两次 → **`cmp` 字节一致 ✅**；改 `--base main~1` → **字节不同 ✅**（`base_sha` `96a318a…`→`c19274c…`、`diff_hash` 随之变） | ✅ |
| Q3 | 接受「目标指纹」降级；兜底路径 `reviewer≠author` **结构性恒真**；只挡显式喂同值；**文档口径统一** | `design.md:93-101,109,142`、`gate.md:108-110`、`agentenv.py:11-22`、`plugin/README.md:52-58`、`plugin/commands/{grill,review-loop}.md`、`templates/*.md`（部分） | 主文档已统一；但 **`templates/review-loop.md:17` 与 `manifestcmd.py:125` 残留旧口径**（见 Issue 1/2） | ⚠️ 部分 |
| Q4 | 保留 stdout 打印实际 id；改掉「照着 export/填」文案 | `manifestcmd.py:153-156`（stdout 打印）；`plugin/README.md`、`plugin/commands/grill.md`（review-loop.md 一并改） | `manifest build` stdout 打印 `reviewer_run_id=… author_run_id=…`；旧文案「给了显式 id，重建才幂等」「设了才幂等」已消失 | ✅ |
| ① | `manifest build` 拒绝含 `/`（或 `\`）的 change id，fail-closed、不写文件 | `manifestcmd.py:54-58` | 造出**契约合法**的嵌套目录 `changes/foo/bar/` 后 `--change foo/bar` → `change='foo/bar' 不能含 '/' … 没有写出任何文件。`，`exit=1`，**未落盘**；`--change 'a\b'` 同拒 | ✅ |
| ①-副作用 | 单段 `..` 仍由 containment 守卫拦（不被新校验顶掉） | `manifestcmd.py:64-68`；测试 `:373-394` | `--change ..` → `change='..' 逃逸出 openspec/changes/…`，`exit=1` | ✅ |
| ①-对照 | 正常单段照常 | — | `--change add-retry` → `exit=0`，正常写出 | ✅ |
| 口径自洽 | run id 生成 / build 的 change_id / check 的 `split("/",1)[0]` 三者自洽 | `agentenv.py`、`manifestcmd.py:54`、`contract.py:82-85,248` | build 现在**只放行单段** change_id；`check` 取首段 == 整段，`manifest.change_id` 与目录段一致 → 不再有「build 过 / check 挂」的口径分歧。round-trip（**兜底 id、零 export**）→ `check：通过 ✓` | ✅ |
| CD5 | 旧的非确定性 manifest 保持兼容，不新增形态校验 | `contract.py:238-260`（仍只判「非空」+「不相等」） | 读码确认无正则/前缀/长度校验；兜底 id round-trip 绿 | ✅ |

---

## 2. Issues

### Issue 1（中）—— Q3 口径未完全统一：用户可见模板 `templates/review-loop.md:17` 仍是旧说法

`templates/review-loop.md` 同一次提交里，**第 132-134 行**已改成新口径
（「兜底路径下两角色 id 结构性不同，只挡显式喂同值，**不**等于『挡忘了另开 run』」），
但**第 17 行**（`## 参与者` 段）**仍保留**：

```
- **审阅者 run**：**必须另起**。强制 `reviewer_run_id != author_run_id`
  （挡「忘了另开 run」，不挡蓄意伪造）。        # templates/review-loop.md:17
```

同一文件里第 17 行与第 134 行**直接打架**。CD6 的原话就是「**别一处说『挡忘开 run』、
一处承认它不证独立性**」；Q3 用户答复要求「文档说穿它不证独立性」。这是**用户可见**的 host 中立模板，
审阅者会照它执行，属 Q3 的漏网。

**复现**：`sed -n '17p;132,134p' templates/review-loop.md`
**修法**：把第 17-18 行改成「强制 `reviewer ≠ author`——兜底路径下**结构性恒真**、只挡显式喂同值；
要真身份须设 `WITNESSLOOP_RUN_ID`」。（`templates/grill.md` 的 `## 参与者` 段无此句，无需改。）

### Issue 2（中低）—— Q3 口径未完全统一：用户可见报错 `src/witnessloop/manifestcmd.py:125`

```
"reviewer_run_id 与 author_run_id 相同：审阅者必须独立于作者"
"（挡「忘了另开 run」）。没有写出任何文件。"      # manifestcmd.py:123-126
```

兜底改动后，兜底路径两角色 id **结构性不同**，这条分支**只会在显式把同一值喂给两角色时触发**
（实测：`WITNESSLOOP_RUN_ID=shared-run manifest build …` → 命中此分支、`exit=1`）。
即它挡的是「只设共享变量」，而报错却告诉用户「你忘（了）另开 run」——正是 CD6 点名要废弃的措辞。

**复现**：`WITNESSLOOP_RUN_ID=shared-run uv run … witnessloop manifest build --change add-retry --stage s …`
**修法**：措辞与 `agentenv.py:18-21` 对齐（如「只有在显式把同一个值喂给两个角色时才会命中；
要独立身份请用角色专用变量分别设」）。

### Issue 3（低）—— 陈旧注释 `src/witnessloop/contract.py:253`

`# D4：强制 reviewer ≠ author（挡「忘了另开 run」，不挡蓄意伪造）。` 与新的口径不一致。
非用户可见，但同属 Q3「口径统一」的漂移面。**修法**：同步措辞。

### Issue 4（中）—— CD8 要求的文档守卫抓不到 CD8 点名的那句话

CD8 原文：`cli.py:87` 的「…→ 生成）。给了才幂等」**现已为假**，须改，**并把 `cli.py` 纳入
`test_docs.py` 的漂移守卫**。实现的确把 `src/witnessloop/cli.py` 加进了 `RUN_ID_DOCS`（✅），
但守卫的判据是（`tests/test_docs.py:63`）：

```python
STALE_FALLBACK_CLAIMS = ("短随机", "UTC 时间戳", "-<utc>-<随机>")
...
assert stale not in text and "确定性" in text
```

**它不含「给了才幂等」**。讽刺的是，紧挨着的注释（`:58`）恰以「给了才幂等」为反例——
但判据里没有它。

**变异实测**（就地改坏 → 跑守卫 → 还原）：

| 变异 | 命令 | 期望 | 实测 |
|---|---|---|---|
| **A** 往 `cli.py` 重新塞回 `# 给了才幂等` | `pytest -q tests/test_docs.py::test_docs_promise_a_deterministic_fallback` | 变红 | **7 passed —— 未抓到 ❌** |
| B 往 `cli.py` 重新塞回 `# …<UTC 时间戳>-<短随机>` | 同上 | 变红 | 1 failed ✅ |

即：守卫**不是空转**（它能抓旧措辞），但**抓不到 CD8 真正要防的那一类假说法**——任何「X 才幂等」
「重复 build 会得到不同 id」式的新假话都能静默留存。**修法**：把 `STALE_FALLBACK_CLAIMS` 扩到
能覆盖该类的判据（如加入 `"给了才幂等"` / `"才幂等"`），或改成「出现 `幂等` 时必须同时出现
`固定 base 与 revision`」的正向约束。

### Issue 5（nit）—— `docs/design.md:79` 仍是无条件「幂等」

§5.1 的 `manifest build` 摘要行仍写「幂等、不 auto-commit」。CD9 要求把「逐字节可复现」限定为
「固定 base 与 revision 时」；§5.2（`:97`）已限定，但 §5.1 这句仍是旧的无条件口径。
概括性摘要，影响小，建议顺手带上限定词。

---

## 3. 变异证据（关键实现「改坏 → 变红」）

隔离方式：**原地变异 → 跑指定测试 → `git checkout -- <file>` 还原**；每轮结束 `git status` 干净。
（未用 `uv run --project <副本>`——那会回落原仓代码，测不到变异。）

| 变异 | 文件 | 目标测试 | 结果 |
|---|---|---|---|
| A 塞回「给了才幂等」 | `cli.py` | `test_docs_promise_a_deterministic_fallback` | **7 passed（未抓到）← Issue 4** |
| B 塞回「短随机」 | `cli.py` | 同上 | 1 failed ✅ |
| C `ANCHOR_DIGEST_LEN` 12→8 | `agentenv.py` | `test_agentenv.py` +`test_manifest_build.py` | 2 failed ✅（`test_default_anchor_uses_at_least_twelve…` 等） |
| D' `generate_run_id` 加随机后缀 | `agentenv.py` | `test_same_input_gives_the_same_id`、`test_rebuild_without_explicit_ids_is_byte_identical`、`test_generated_ids_are_deterministic_across_builds` | 3 failed ✅ |
| E 关掉 ①（`if False`） | `manifestcmd.py` | `test_nested_change_id_is_rejected` 等 3 条 | 3 failed ✅ |
| F anchor 丢掉 `head`（只用 change） | `agentenv.py` | `test_default_anchor_carries_change_and_revision` 等 | 2 failed ✅ |
| G 关掉 containment 守卫 | `manifestcmd.py` | `test_dotdot_change_id_is_still_caught_by_the_containment_guard` | 1 failed ✅ |
| H 让 build 忽略 `--base`（base 不进键） | `manifestcmd.py` | `test_base_drift_does_change_the_bytes` | 1 failed ✅（反向断言真的在守 base） |

结论：确定性（D'）、摘要长度（C）、锚含 revision（F）、① 校验（E）、containment（G）、
幂等键含 base（H）**六条关键性质都有能被变异变红的测试**；唯一的守卫缺口是 Issue 4。

---

## 4. 停轮问题

无**需人拍板**的停轮问题。Issue 1、2、4 是对**已确认决策（Q3 / CD8）的落地补全**，不需要新决策——
按上面「修法」直接改即可；Issue 3、5 为顺手清理。

## 5. 未覆盖 / 边界备注（非阻塞）

- `--change "."` 与空串 `--change ""` 会绕过 ①（无 `/`）与 containment（解析回 changes_root 自身），
  但被 `validate_change_dir` 以「缺少必需件」拒掉——除非 `changes_root` 自身恰好具备全部必需件
  （实际不可能）。**低风险**，无须处理。
- `head_sha` 为 `None` 时 `default_run_anchor` 会 `TypeError`（grill Code-Resolved 已记），
  当前由 `manifestcmd.py:104-105` 提前 `_fail` 挡住、不可达。导出为公共 API 时须注明前置条件。
- `manage`/`check` 对 run id 仍**无任何形态校验**（CD5 有意保留）：旧时间戳 id 兼容；日后若加形态校验
  须配迁移（grill R5），本 change 未触碰，符合定稿。

## 6. Reviewer

- 分支: `fix/run-id-determinism/2026-10-10`（head `dbf1134`）
- 时间: 2026-10-10
- 方式: 全新零记忆；读码 + scratch 真仓跑 CLI + 变异
