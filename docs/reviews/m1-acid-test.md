# M1 acid test 记录（真实仓 + 真实 CI）

> 2026-10-09。测试仓：`Xingkai98/wl-test`（一次性、私有）。审阅对象：`witnessloop@v1`（tag `v1` → `v1.0.0`，commit `85c9b42`）。
> 目的：验证**本地测不到**的东西——`@v1` tag 能否解析 · reusable workflow 能否跑 · CI 里能否装包 · `check` 在真 runner 上行为 · 门禁能否真拦。

## 结论

**门禁在真 GitHub Actions 上拦下了「只改 `src/`、无 change 目录」的 PR**，报错精确到文件与规则：

```
check：未通过 ✗（1 项）
check：基线 origin/main...HEAD，1 个变更文件，0 个 change 目录
  1. src/app.py：src/app.py 属于必须挂 change 的路径（policy.require_change_for），
     但本次 diff 里没有任何 change 目录（openspec/changes/<id>/）。
     补一个 change 目录，或把该路径从 policy.require_change_for 里移除。
```

`uvx --from git+https://github.com/Xingkai98/witnessloop@v1` 安装成功；job 步骤：checkout ✓ → setup-uv ✓ → **witnessloop check ✗**。

## 过程中揪出的两个设计缺陷（均已处置）

### ① reusable workflow 访问级别 = `none`
`GET /repos/Xingkai98/witnessloop/actions/permissions/access` → `{"access_level":"none"}`。
私有仓的 reusable workflow 默认 `none`，最多只能开到「同 owner」（`user`）。
表现：caller run **0 个 job**、`This run likely failed because of a workflow file issue`。

### ② CI 装私有包需要凭据
放开 access 后，job 真跑了，但装在第一步失败：
```
error: Failed to resolve `--with` requirement
  cause: failed to fetch branch or tag `v1`
  cause: ... git fetch ... (exit status: 128)
         fatal: could not read Username for 'https://github.com': terminal prompts disabled
```
job token 属于 caller 仓（wl-test），读不到私有 witnessloop。

### 处置
两处根因同一：**witnessloop 是私有仓**。改为**公开**后全部通过。
→ 结论写进 `docs/design.md` §4.1：**v1 假设 witnessloop 公开**；私有接入需额外 token，不在 v1 范围。

## 尚未验证（留待 M2）

- **「有证据 → 通过」**：需要一个合法 review manifest（`head_sha` = 最后非证据 revision、`reviewer ≠ author`、四个 hash 绑真实字节）。手工构造极繁——**这正是 M2（CC plugin 产出证据）要解决的**。M3 完整 acid test 待 M2。
- **真「挡住合并」**：本次 gate 跑红，但未把该 job 设成 required check（需 branch protection）。CI 层面已验证会红；merge 阻断属平台配置。
