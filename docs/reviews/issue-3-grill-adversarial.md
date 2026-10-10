# 对抗验证报告：issue #3 设计 grill 结论复核

> 设计阶段对抗验证 loop（`templates/grill.md` §5）。**独立零记忆审阅者**（与 grilling pass 的
> 审阅者、设计作者均不共享上下文），**默认待验证结论有错**、逐条尝试证伪；能实测的就去实测
> （自建临时仓 `/tmp/wl-grill/brepo` 跑 `manifest build`）。
> READ-ONLY：未修改 witnessloop 任何实现文件、未动 git。

## Reviewer
- run id（对抗验证）: `51044ff3-7dcb-48c5-baac-1b043dd89733`
  （其兜底形态恒为 `grill-adversarial-reviewer-run-id-determinism-d70f2f99`——三轮同值，恰好实证
  Q3「兜底 id 是目标指纹、不区分两次 run」）
- 时间: 2026-10-10T11:09Z（R1）/ 11:12Z（R2）/ 11:13Z（R3）

## Verdict（轮次）
**3 轮均 `CHANGES_REQUESTED`，达到默认封顶（3）**。逐轮把「必须修改」逐条落回
`issue-3-grill.md`；R3 收尾时只剩**一句 Code-Resolved 措辞**（消息名张冠李戴）待修，已按 R3 指定
的准确表述改好——**不涉及任何设计决策**。若需第 4 轮复核该句，交人判断（见末节）。

| 轮 | 时间 | 结论 | 必须修改 |
|---|---|---|---|
| R1 | 11:09Z | CHANGES_REQUESTED | 4 条：footgun 定位错、`cli.py` 过时串、R1 夸大、D4 口径矛盾 |
| R2 | 11:12Z | CHANGES_REQUESTED | 1 条：`change_id` 含 `/` 的 Code-Resolved **归因错误**（+3 次要） |
| R3 | 11:13Z | CHANGES_REQUESTED | 1 条：round-2 重写**新引入**的措辞错误（消息名） |

---

## R1：逐条对抗（对 grilling pass 结论）

| # | 待验证结论 | 裁定 | 硬证据（文件:行号 / 实测） |
|---|---|---|---|
| CD1 | 保留两级 env 覆盖、优先级不变，只改兜底 | 成立 | `agentenv.py:66-70` 确为角色专用在前；`agentenv.py:36-38` 拼 `WITNESSLOOP_<ROLE>_RUN_ID` |
| CD2 | `role` 编进 id → 兜底路径 `reviewer≠author` 恒成立 | **成立，理由夸大** | 形态由 `agentenv.py:50-55` 保证；`contract.py:254` 相等即拒。**但**「这正是『忘了另开 run』的症状」错——role 编入后默认路径 D4 **永不触发**，同一 run 既写又审也直接过门禁 |
| CD3 | 不删 run id、不改绑真实 run | 成立 | `docs/design.md:140`「强制 reviewer ≠ author」；host 无注入点 `docs/design.md:91` |
| CD4 | 锚不含 `base_sha`，只取 `change_id + head` | **成立，益处被高估** | 代码确如此（`manifestcmd.py:103`）。**但**排除 base 只保「id 稳定」，**没**保「manifest 字节可复现」——实测 base 漂移仍改 `base_sha`/`diff_hash` |
| CD5 | 旧非确定性 manifest 兼容 | 成立 | `contract.py:238-244`（仅非空）+ `:254`（仅不相等）；`constants.py:61-70` 无格式项；旧 id 非空且两角色不同 → 照过 |
| CR1–CR7 | 各 Code-Resolved 条目 | **全部成立** | `check` 不判错确定性 id；兜底 id 是唯一非确定源（自带 base 例外）；输出流 stdout/stderr 分流、CI 不跑 build（`gate.yml:59`/`ci.yml:24-40`）；无 `--head`、`head_sha=rev_parse(HEAD)`（`cli.py:72-99`、`manifestcmd.py:93-95`）；锚取 head（`agentenv.py:41-47`）；优先级顺序（`agentenv.py:36-38,66-70`） |
| Q1 | 锚取 `change_id + head[:8]`，建议 ≥12 位 | **成立，但 R1 后果描述不实** | 字符串实测一致；**但**「两份 manifest 共用同一 id」**不可达**（同 `(change,stage)` 唯一路径会覆盖） |
| Q2 | 「同 (change,stage,role,revision) 字节一致」在 base 会动时为假 | **成立（本报告最硬的一条，实测证实）** | 仅让 `main` 前进一次：两次 id 相同、manifest 字节 **DIFFERENT**，差异仅 `base_sha`/`diff_hash` |
| Q3 | 确定性把身份字段退化为「目标指纹」 | 成立 | 两个真正独立的 run 审同一 revision 得同 id；与 CD2 的 rationale 互斥 → 须统一口径 |
| Q4 | 打印形态 +「照着 export」误导，点 `grill.md`/`review-loop.md` | **部分证伪** | 实测自撞机制成立（`exit=1`）；**但定位错**：「照着 export」只在 `plugin/commands/grill.md:56` 与 `plugin/README.md:54-55`，**`review-loop.md` 无此句** |
| R1–R6 | 各风险条目 | R2/R4/R5/R6 成立；**R1 夸大**；R3 成立但清单错 | R2 实测：现有幂等测试钉固定 `main`、老用例显式传 id，盖不住 base 漂移 |

**R1 必须修改（已落回）**：(1) 修正 Q4/R3 文案定位（→`plugin/README.md:54-55` + `grill.md:56`）；
(2) `cli.py:86-87`「给了才幂等」现为假，须改并纳入漂移守卫；(3) 重述 R1（去不可达失败模式）；
(4) 统一 D4 口径（兜底路径结构性恒真、不再等于「挡忘开 run」）。

## R2：落实核对 + 新发现

- **R1 的 4 条必须修改：全部落实、无改错**（(a)(c)(d) 逐字对上；(b) 记为待实现决策，现状与描述一致）。
- **新发现（必须修）**：`change_id` 含 `/` 的 Code-Resolved 归因错——原文称「会在 `validate_change_dir`
  契约层被拒」，**实测为假**：建好 `openspec/changes/a/b/`（必需件齐备）后
  `manifest build --change "a/b"` **`exit=0` 放行**，写出 `reviewer_run_id='building-reviewer-a/b-<head8>'`。
  真正拦在 `check` 侧 `changed_change_ids` 的 `split("/")` 取首段。→ 已改述（含 R7）。
- 次要：CD 加编号（CD6/CD7 引用不再脆弱）、`foo-0123` 示例写全、header 措辞限定 —— 均已落实。

## R3：落实核对 + 剩余必须修改

- **R2 的必须修改 + 3 次要：全部落实**；CD6/CD7 编号引用、`/` 归因核心均正确。
- **新发现（必须修）**：R2 重写**新引入**一处措辞错误——把「缺少必需件」误说成目录**不存在**时的报错。
  实测：目录**不存在** → `validate_change_dir` 报「**change 目录不存在**」（`contract.py:93-94`）；
  目录**存在但缺件** → 报「**缺少必需件**」（`contract.py:97-99`）。→ 已按 R3 指定表述改好。
- 除这一句外，逐条复核 8 条 Code-Resolved、Q1–Q4、R1–R8、CD1–CD9：行号可核、结论与实测一致，
  **无**新的事实错误/行号错/夸大/遗漏。

---

## 对抗验证的净效果（被证伪 / 被修正的结论）

1. **Q4/R3 的 footgun 定位错** → 从 `review-loop.md` 改为真正含该文案的 `plugin/README.md:54-55`；
   否则实现者会去改一个不含该句的文件，同时漏掉真正含它的 README。
2. **`cli.py:86-87`「给了才幂等」现为假** —— 这是 round-1 之前**无人认领**的 user-facing 错误串，
   且 `tests/test_docs.py` 的漂移守卫盖不到它。
3. **R1 夸大** → 「id 丧失 revision 区分力」，而非「两份 manifest 共存共用同一 id」（不可达）。
4. **CD2 的 rationale 与 Q3 自相矛盾** → 统一为「兜底路径 `reviewer≠author` 结构性恒真、D4 名存实亡」。
5. **`change_id` 含 `/` 的 Code-Resolved 归因错**（R2）→ 改为「build 实测放行、真正拦在 `check` 侧」。
6. **「缺少必需件」消息名张冠李戴**（R3）→ 按代码的两个分支改准。

## Code-Resolved 复核（答案）

- **`check` 不判错确定性 id / 旧 manifest 兼容** → 真代码可判，结论正确（`contract.py:238-260`；`constants.py:61-70`）。
- **兜底 id 是唯一非确定源** → 真代码可判、结论正确，自带 `base_sha`/`diff_hash` 例外（正是 Q2）。
- **build 输出流** → 真代码可判、结论正确（`manifestcmd.py:29,141-144`；CI 不跑 build）。
- **`/` 与「照着 export」** → 机制可由代码判定且**实测**成立；其中「照着 export」的**文档定位**属
  「代码可判 + 需人工核对」，grill-pass 首轮挂错了 md 行，已由对抗验证纠正。
- **build 取 head / 锚取 head / 优先级顺序 / `-` 无歧义 / `head_sha` None 不可达 / 空·空白 env** →
  均真代码可判、结论正确。
- **总评**：Code-Resolved 段**没有一条是把「需要人取舍」冒充为「代码可判」**；唯一反复的是其**措辞**，
  两轮各修正一处（`/` 归因、消息名），核心结论始终成立。

## 最后一条（封顶交人）

R3 收尾只剩一句 Code-Resolved 措辞（`issue-3-grill.md` 中 `/` 条的报错消息名），已按 R3 指定的准确
表述改好；**它不影响任何 Confirmed Decision / Open Question / 风险**。对抗验证已到轮数封顶（3），
该句之外无未决项；是否需人工再审该句，交用户判断。
