"""``events.covers`` 的单元语义（D5 的匹配规则）。

reviewer R2 §3-4：`covers` 里「拒绝通配」那一行本被等价比较掩盖——删掉它
146 个测试全绿，属「冗余且无测试钉住」。这里把该规则**定向**钉死：
事件里的 `artifact_path` 必须是具体路径，含通配一律不算数。
"""

from __future__ import annotations

import pytest

from witnessloop import events
from witnessloop import constants as C

TYPES = C.DEFAULT_PROTECTED_EVENT_TYPES


def _event(artifact_path: str, **overrides) -> events.Event:
    fields = {
        "event_type": "protected_path_write",
        "artifact_path": artifact_path,
        "reason": "受保护 spec 同步，人类已确认",
        "approved_by": "user:kai",
    }
    fields.update(overrides)
    return events.Event(**fields)


@pytest.mark.parametrize(
    "pattern",
    [
        "**",
        "openspec/specs/**",
        "openspec/specs/*.md",
        "openspec/specs/?.md",
    ],
)
def test_wildcard_event_never_covers(pattern):
    """一行通配不能豁免任何路径（含它字面上「能匹配」的那些）。"""
    assert events.covers(_event(pattern), "openspec/specs/a.md", TYPES) is False


def test_literal_wildcard_in_a_filename_still_needs_a_concrete_name():
    """即便目标文件名**字面**含 `*`，也不接受用通配去点它（fail-closed）。

    这一条是定向的：删掉「拒绝通配」那行后，等值比较会让它变绿——
    即该防线确实被这个测试钉住，不是冗余。
    """
    assert events.covers(_event("a/*.md"), "a/*.md", TYPES) is False


def test_exact_path_is_covered():
    assert events.covers(_event("a/b.md"), "a/b.md", TYPES) is True


def test_path_is_normalized_before_comparison():
    assert events.covers(_event("a/b.md"), "./a/b.md", TYPES) is True
    assert events.covers(_event("./a/b.md"), "a/b.md", TYPES) is True


def test_a_different_path_is_not_covered():
    assert events.covers(_event("a/b.md"), "a/c.md", TYPES) is False
    # 前缀/子串都不算
    assert events.covers(_event("a/b.md"), "a/b.md.bak", TYPES) is False


@pytest.mark.parametrize(
    "field,value",
    [("reason", ""), ("reason", "   "), ("approved_by", ""), ("approved_by", "  ")],
)
def test_blank_explanation_fields_never_cover(field, value):
    assert events.covers(_event("a/b.md", **{field: value}), "a/b.md", TYPES) is False


def test_unknown_event_type_never_covers():
    assert (
        events.covers(_event("a/b.md", event_type="i_am_a_waiver"), "a/b.md", TYPES)
        is False
    )
