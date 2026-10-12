# Proposal: events-readpoint-fix（事件文件读点：崩溃 → 干净的红）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#12**。

## 背景

issue #9 / change `guard-crash-exit` 修掉了 **`guard`/`check` 可达**的「证据文件读不出 ⇒ **崩溃**（而非确定性结论）」
那类缺陷（policy / review manifest / 报告三个读点）。当时把 **`events.py` 的读点列为非目标**（`check`-only、
不同 artifact、无 `guard` 路径）⇒ 另立 **#12**。

**实测（本 change 立项时复核）**：`events.py:51`

```python
for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
```

**完全没有 try** ⇒ 一个**非法 UTF-8** 的 `workflow-events.jsonl` ⇒ `UnicodeDecodeError` 冒泡；
而 `checkcmd.py:166-168` 只捕 `witnessloop.events.EventError`（消息「事件文件无法解析」）⇒ **`check` 崩溃**（traceback）。
（函数级复现：`events.load_events_file(<含 0xff 的 events 文件>)` ⇒ `UnicodeDecodeError`。）

**影响**：`check` 崩溃退 **1** = 「未通过」⇒ **fail-closed 方向正确**，**不是**误拦；只是**报错难看**
（一大段 traceback 而非一行可诊断的 finding）——即**可用性**缺陷，不是正确性缺陷。

**顺带实测发现同类更广**（立项时逐点核）：

| 读点 | 现有守卫 | 后果 |
|---|---|---|
| `events.py:51` | **无 try** | `check` 崩（本 issue 主体） |
| `initcmd.py:63`（`--policy`）、`initcmd.py:131`（init 台账） | `except (OSError, json.JSONDecodeError)`，**漏 `UnicodeDecodeError`** | `init` 崩 |
| `uninitcmd.py:30`（init 台账） | `except json.JSONDecodeError`，**连 `OSError` 都漏** | `uninit` 崩 |
| `initcmd.py:118/201/216`、`uninitcmd.py:77` | **无 try**（相对路径比对 / 渲染 diff） | 崩 |

⇒ 这是**同一族**「读不出 ⇒ 崩」的剩余成员；前三个属 `check` / `init` / `uninit` 的主路径。

## 目标

把「事件文件读不出」从**崩溃**改成**干净的 finding**：

- `events.load_events_file`（`load_all` 经它）在**读不出**（解码失败 / 权限等 OSError）时 SHALL 抛 **`EventError`**
  （**与既有的「不是合法 JSON」同一错误类型、同一出路**）——`checkcmd._protected_writes` 既有的
  `except events_mod.EventError` 会把它变成**一行可诊断的 finding**（`check` 干净的红，非 0）。

## 非目标

- **不做抽象层**（如共用 `read_text_utf8` helper）：见 design D3（本仓风格：三行相似代码好过一个过早的抽象）。
- 不改 `check` 的**退出码语义**（仍非 0 = 未通过）。
- 不引入签名 / 防伪造。
- **改动范围**（`events.py` only，还是连 `initcmd`/`uninitcmd` 一起）见 design 的 **Open Question Q1**。

## 验收

- **单测**：`load_events_file` 遇非法 UTF-8 ⇒ 抛 `EventError`（非 `UnicodeDecodeError`）。
- **端到端**：一个含非法 UTF-8 事件的仓 ⇒ `check` **不抛异常**、**非 0**、且 stderr 是「事件文件无法解析」那条 finding（无 traceback）。
- **回归**：合法的 events 文件行为不变（`check` 用它判受保护写入豁免，既有用例全绿）。

## 测试策略

TDD。判定面很小（一个读点 + 一个既有 catch），用例密集在「同一失败模式的不同成因」（解码失败 / 权限）与「回归」上。
