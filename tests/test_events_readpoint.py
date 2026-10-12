"""E 组：读点归一（change events-readpoint-fix / issue #12）。

`read_text` 文本读点读不出（**非法 UTF-8**）时，**不得**表现成工具故障（`witnessloop：内部错误`），
而应给**一行点名文件**的确定性诊断。

⚠️ **配方纪律**（对抗验证实测）：`check` 那一族用「**目录冒充**」造 `OSError`（与 uid 无关）；
而 `init`/`uninit` 路径上「目录」会先在**族外**的 `read_bytes` 处失败 ⇒ 那两条**必须用非法 UTF-8**。

⚠️ **断言纪律**：「不抛异常 / 非 0 / 不含 Traceback」**今天就已经全绿**（`entry.py` 的入口兜底接住了）
⇒ 钉不住任何东西。可判定的断言是 **stderr 不含 `witnessloop：内部错误`**（今天为假、修后为真）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from witnessloop import constants as C
from witnessloop.events import EventError, load_events_file

from conftest import commit_all
from helpers import check, commit_content

CHANGE = "add-x"
#: 工具故障那一行的前缀——**可判定断言**就钉它（今天有、修后无）。
INTERNAL_ERROR = "witnessloop：内部错误"


def _events_path(tmp_path: Path) -> Path:
    return tmp_path / "workflow-events.jsonl"


# ---------------------------------------------------------------- 单元：events.py 的读点


def test_illegal_utf8_becomes_an_event_error(tmp_path: Path):
    path = _events_path(tmp_path)
    path.write_bytes(b'{"event_type": "protected_path_write", "x": "\xff\xfe"}\n')

    with pytest.raises(EventError) as exc:
        load_events_file(path)
    assert "无法解码" in str(exc.value)
    assert str(path) in str(exc.value)  # 点名文件


def test_unreadable_file_becomes_an_event_error(tmp_path: Path):
    """**目录冒充**：与 uid 无关（`chmod 000` 在 root 下会假绿，R6）。"""
    path = _events_path(tmp_path)
    path.mkdir()

    with pytest.raises(EventError) as exc:
        load_events_file(path)
    assert "无法读取" in str(exc.value)  # 与「无法解码」分得开
    assert str(path) in str(exc.value)


def test_valid_events_still_parse(tmp_path: Path):
    """回归：合法文件行为不变（含**行级**的 JSON 语法错误文案）。"""
    path = _events_path(tmp_path)
    path.write_text(
        '{"event_type": "protected_path_write", "artifact_path": "a/b.md",'
        ' "reason": "r", "approved_by": "u"}\n',
        encoding="utf-8",
    )
    events = load_events_file(path)
    assert len(events) == 1 and events[0].artifact_path == "a/b.md"

    path.write_text("{ 不是 JSON\n", encoding="utf-8")
    with pytest.raises(EventError) as exc:
        load_events_file(path)
    assert "不是合法 JSON" in str(exc.value)  # 既有行级文案不变


# ---------------------------------------------------------------- 端到端：check


def test_check_reports_a_clean_finding_for_an_undecodable_events_file(gated: Path, cli):
    """**可判定**：修复前 stderr 是 `witnessloop：内部错误（UnicodeDecodeError…）`；修复后是一行 finding。"""
    commit_content(gated, CHANGE)  # 只要有个 change 目录即可（这个读点与 diff 无关）
    (gated / "openspec" / "changes" / CHANGE / "workflow-events.jsonl").write_bytes(
        b'{"event_type": "protected_path_write", "x": "\xff\xfe"}\n'
    )
    commit_all(gated, "坏 events 文件")

    code, _, err = check(gated, cli)
    assert code != C.EXIT_PASS
    assert "事件文件无法解析" in err
    assert INTERNAL_ERROR not in err  # ← 今天为假、修后为真


# ---------------------------------------------------------------- 端到端：init / uninit
# ⚠️ 这两条**必须用非法 UTF-8**（目录会先在族外 read_bytes 处失败，用例会永远红）


def test_init_reports_a_clean_error_for_an_undecodable_landed_file(gated: Path, cli):
    """已接入的仓里 `policy.json` 是非法 UTF-8（在本地目录内即可，不必提交）⇒ 干净报错、不报工具故障。"""
    (gated / C.POLICY_PATH).write_bytes(b'{"schema": "\xff\xfe"}')

    code, _, err = cli("init", "--root", str(gated))
    assert code == C.EXIT_FAIL
    assert INTERNAL_ERROR not in err
    assert "policy.json" in err


def test_uninit_reports_a_clean_error_for_an_undecodable_ledger(repo: Path, cli):
    cli("init", "--root", str(repo))
    commit_all(repo, "接入 witnessloop")
    (repo / C.INIT_MANIFEST_PATH).write_bytes(b'{"gate_ref": "\xff\xfe"}')

    code, _, err = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_FAIL
    assert INTERNAL_ERROR not in err
    assert "init-manifest.json" in err
