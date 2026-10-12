# Proposal: events-readpoint-fix（事件文件读点：崩溃 → 干净的红）

> 状态：草稿（待 grill + 对抗验证 + 用户确认）。
> 关联 issue：witnessloop **#12**。

## 背景

issue #9 / change `guard-crash-exit` 修掉了 **`guard`/`check` 可达**的「证据文件读不出 ⇒ **崩溃**（而非确定性结论）」
那类缺陷（policy / review manifest / 报告三个读点）。当时把 **`events.py` 的读点列为非目标**（`check`-only、
不同 artifact、无 `guard` 路径）⇒ 另立 **#12**。

**实测（grill 在真 git 仓上复核 · ⚠️ 已订正原稿的错误前提）**：`events.py:51`

```python
for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
```

**完全没有 try** ⇒ 非法 UTF-8 的 `workflow-events.jsonl` ⇒ `UnicodeDecodeError` 冒泡；
而 `checkcmd.py:167` 只捕 `witnessloop.events.EventError`（消息「事件文件无法解析」）。

⚠️ **原稿写「`check` 崩溃成 traceback」——与实测不符**：change `guard-crash-exit` 的**进程入口兜底**
（`entry.py:35-41`）把它接住了，今天真实形态是**一行**：

```
witnessloop：内部错误（UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff …）
EXIT=1        ← 没有 Traceback
```

⇒ **真正的缺陷是两条（这才是本 change 的价值）**：
1. **把仓的问题报成工具故障**——`内部错误` 会让读者以为 **witnessloop 坏了**，而不是「**你的 events 文件坏了**」；
2. **解码分支不点名文件**（`OSError` 分支的 message 自带路径，解码分支不带）。

**影响**：退 **1** = 「未通过」⇒ **fail-closed 方向正确**，**不是**误拦 ⇒ 属**可用性 / 可诊断性**缺陷。
另：这个读点是**全局的、与 diff 无关的**（`checkcmd.py:100` 无条件调 `_protected_writes`；**空 diff 也走这条路**）
⇒ 坏 events 文件会让该仓**每一次** `check` 都到不了 `_report`（**连其它 finding 一条都不打印**）。

**顺带实测发现同类更广**（立项时逐点核）：

> **族边界**＝「`read_text` **文本**读点、落在 `check`/`init`/`uninit` 主路径」（原稿没定义，grill 要求补——见 design §2.5）。

| 读点 | 现状 | 后果 |
|---|---|---|
| `events.py:51` | **无 try** | `check` 报「内部错误」（本 issue 主体） |
| `initcmd.py:118`、`:216`、`uninitcmd.py:77` | **无 try** | `init`/`uninit` 报「内部错误」 |
| `initcmd.py:63`（`--policy`）、`:131`、**`:201`** | 有 try，但 `except json.JSONDecodeError`，**同时漏 `OSError` 与 `UnicodeDecodeError`** | 同上 |
| `uninitcmd.py:30` | `except json.JSONDecodeError`，**连 `OSError` 都漏** | 同上 |
| ⚠️ **族外**：`initcmd.py:215`、`uninitcmd.py:59`（`read_bytes`）、`contract.py:373/386`（`sha256_tree`） | 无 try | **不同族**（无解码语义；`OSError` 的 message 自带文件名）。⚠️ 但 `contract.py:373/386` 在 **`check` 主路径**上、**早于** 正文守卫 ⇒「报告存在但不可读」仍报「内部错误」（**已知未覆盖**） |

⇒ ⚠️ **原稿把 `initcmd.py:201` 归入「无 try」是分类错**（它 `:200-204` 有 try）——grill 实测纠正。

## 目标

把「事件文件读不出」从**崩溃**改成**干净的 finding**：

- `events.load_events_file`（`load_all` 经它）在**读不出**（解码失败 / 权限等 OSError）时 SHALL 抛 **`EventError`**
  （**与既有的「不是合法 JSON」同一错误类型、同一出路**）——`checkcmd._protected_writes` 既有的
  `except events_mod.EventError` 会把它变成**一行点名文件的 finding**，而**不是** `witnessloop：内部错误`。
- **（依 Q1）** 同族读点一并收口（见上表族内清单）。

## 非目标

- **不做抽象层**（如共用 `read_text_utf8` helper）：见 design D3（本仓风格：三行相似代码好过一个过早的抽象）。
- 不改 `check` 的**退出码语义**（仍非 0 = 未通过）。
- 不引入签名 / 防伪造。
- **改动范围**（`events.py` only，还是连 `initcmd`/`uninitcmd` 一起）见 design 的 **Open Question Q1**。

## 验收

- **单测**：`load_events_file` 遇非法 UTF-8 ⇒ 抛 `EventError`（非 `UnicodeDecodeError`）。
- **端到端**：一个含非法 UTF-8 事件的仓 ⇒ `check` 的 stderr **含**「事件文件无法解析」**且不含 `witnessloop：内部错误`**
  ——⚠️ **这才是可判定的断言**：原稿的「不抛异常 / 非 0 / 不含 Traceback」**今天就已经全绿**（grill 实测），钉不住任何东西。
- **回归**：合法的 events 文件行为不变（`check` 用它判受保护写入豁免，既有用例全绿）。

## 测试策略

TDD。判定面很小（一个读点 + 一个既有 catch），用例密集在「同一失败模式的不同成因」（解码失败 / 权限）与「回归」上。
