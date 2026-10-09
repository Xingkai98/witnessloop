# witnessloop 交互层适配器（Claude Code plugin）

把 `grill` 与 `review-loop` 两个流程接到 Claude Code 的命令入口上。

## 物理分离

```
templates/grill.md          ← 算法与 prompt 文本（host 中立，无 host 专有语法）
templates/review-loop.md
plugin/commands/grill.md          ← 只接线：读模板、传参数、调 manifest build
plugin/commands/review-loop.md
```

**适配器只引用模板，不复制正文。** 换 host 时只重写 `plugin/` 这一层，
模板原样复用。`tests/test_plugin.py` 用「去空白后共同段长度」把这条钉住了
（复制一段模板正文进适配器会让测试变红）。

适配器里**不得**出现模板正文，模板里**不得**出现 host 专有语法
（`.claude` 路径、slash 命令、特定工具名）——两边各有一组测试拦着。

## 安装（git / 本地）

设计上**不上 marketplace**（design §4）：早期命令面会变，且「自动更新 = 远端代码
在你 agent 里执行」。直接指向本仓目录即可：

```bash
claude --plugin-dir /path/to/witnessloop/plugin
```

或把本仓 clone 到本地后长期指向该路径。升级 = `git pull`。

## 这两个命令做什么

- `grill <change-id>`：独立零记忆审阅者读 design，逐轮追问，产出决策记录，
  **停轮**等你确认 Open Questions。确认写齐之前不得进入实现。
- `review-loop <change-id> [stage]`：独立零记忆审阅者审实现，
  判 `PASS` / `CHANGES_REQUESTED`，不通过则修并补回归测试，**轮数封顶**，
  收尾写报告并跑 `witnessloop manifest build` 落 manifest。

## 环境变量

| 变量 | 作用 |
|---|---|
| `WITNESSLOOP_RUN_ID` | **当前 run** 的 id。审阅者与作者是不同的 run，各自环境里这个值应当不同 |
| `WITNESSLOOP_REVIEWER_RUN_ID` / `WITNESSLOOP_AUTHOR_RUN_ID` | 角色专用，优先级高于上面那个（同一进程里要同时给两个角色时用） |
| `WITNESSLOOP_TEMPLATES_DIR` | 覆盖模板目录 |

**run id 怎么来**：环境优先、生成兜底。三个变量都没设时，`witnessloop manifest build`
会生成 `<stage>-<role>-<UTC 时间戳>-<短随机>`——`role` 编进 id，所以两个角色**必然不同**，
不会撞上「`reviewer_run_id == author_run_id`」那道校验。给了显式 id，重建才幂等。

**模板目录为什么要能覆盖**：适配器默认用 `${CLAUDE_PLUGIN_ROOT}/../templates`
（即本仓 `plugin/` 旁边的 `templates/`）。如果你只把 `plugin/` 拷到别处、
脱离本仓，模板就找不到了——这时设 `WITNESSLOOP_TEMPLATES_DIR` 指回模板目录即可。
解析规则的可执行实现见 `src/witnessloop/agentenv.py`。

## 只读、无状态

交互层对 change 状态**只读**，**不得持有自己的状态文件**——状态一律以
`reviews/*.manifest.json`（门禁的权威证据）为准。这两个命令不会写 `.cache`、
`state.json` 之类的东西；`plugin/` 目录里只有四个文件——plugin manifest、
两条命令、以及**本 README**（`tests/test_plugin.py::test_plugin_file_inventory_is_exactly_expected`
把这份清单钉死了：多出任何文件都会变红）。

## 能力边界

`reviewer_run_id` / `author_run_id` 是自由文本：本工具**防漂移、不防蓄意伪造**。
真正的锚是远端 branch protection + required check。
