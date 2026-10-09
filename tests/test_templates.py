"""E1：host 中立模板。

模板承载 `grill` / `review-loop` 的**算法与 prompt 文本**，必须不含任何 host 专有
语法——否则「模板与适配器物理分离」就是名义上的（design §5.2 / §9 风险 6）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "templates"

GRILL = TEMPLATES / "grill.md"
REVIEW_LOOP = TEMPLATES / "review-loop.md"

#: host 专有 token——模板里出现任何一个，「host 中立」就不成立。
FORBIDDEN_TOKENS = (
    "claude",
    ".claude-plugin",
    "subagent_type",
    "plugin.json",
    "allowed-tools",
    "frontmatter",
)

#: 以 `/` 开头的行 = slash command 语法（`/grill`、`/review-loop`…）。
SLASH_COMMAND_LINE = re.compile(r"(?m)^\s*/[a-z]", re.IGNORECASE)


@pytest.fixture(params=[GRILL, REVIEW_LOOP], ids=["grill", "review-loop"])
def template(request) -> Path:
    return request.param


def test_templates_exist(template: Path):
    assert template.is_file(), f"缺少模板：{template}"
    assert len(template.read_text(encoding="utf-8")) > 500, "模板太短，像是占位"


def test_templates_are_host_neutral(template: Path):
    text = template.read_text(encoding="utf-8").lower()
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"{template.name} 含 host 专有 token：{token}"
    assert not SLASH_COMMAND_LINE.search(
        template.read_text(encoding="utf-8")
    ), f"{template.name} 含 slash command 语法"


def test_templates_say_where_evidence_goes(template: Path):
    """模板要讲清产出哪种证据文件——回路的产物是 reviews/ 下的报告。"""
    text = template.read_text(encoding="utf-8")
    assert "reviews/" in text
    assert "manifest" in text.lower()


# ---------------------------------------------------------------- grill 算法


def test_grill_template_covers_the_algorithm():
    text = GRILL.read_text(encoding="utf-8")
    # 独立零记忆审阅者
    assert "零记忆" in text
    # 产物：已定决策 + 待定问题（每条配具体例子 + 推荐答案）
    assert "Confirmed Decisions" in text
    assert "Open Questions" in text
    assert "推荐" in text
    assert "例子" in text or "场景" in text
    # 停轮交给用户确认
    assert "停轮" in text
    assert "User Confirmation" in text


def test_grill_template_blocks_implementation_without_confirmation():
    text = GRILL.read_text(encoding="utf-8")
    assert "不得进入实现" in text or "缺证据不得进入实现" in text


# ---------------------------------------------------------- review-loop 算法


def test_review_loop_template_covers_the_algorithm():
    text = REVIEW_LOOP.read_text(encoding="utf-8")
    assert "零记忆" in text
    assert "PASS" in text
    assert "CHANGES_REQUESTED" in text
    # 修复要补回归测试
    assert "回归测试" in text
    # 有界轮数封顶
    assert "轮" in text and "封顶" in text


def test_review_loop_template_ties_reviewer_identity_and_manifest():
    text = REVIEW_LOOP.read_text(encoding="utf-8")
    # reviewer ≠ author
    assert "reviewer_run_id" in text and "author_run_id" in text
    # 收尾调 manifest build
    assert "manifest build" in text
