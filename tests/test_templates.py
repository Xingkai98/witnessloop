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
    # host 侧的适配器目录名——模板自述「不含任何 host 专有语法」，
    # 就不该点名某个 host 的目录（回归 M2 §4-4）。
    "plugin/",
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


# ------------------------------------------- 保真度：grill 的多轮 frontier 循环


def test_grill_runs_a_multi_round_frontier_loop():
    """G1：不是「列一遍决策点」的单趟，而是每轮抛整条 frontier、等答复、重算。"""
    text = GRILL.read_text(encoding="utf-8")
    assert "frontier" in text  # 术语要在，且下面几条把它定义清楚
    # ③ 抛完停下等用户答复
    assert "停" in text and "等" in text
    # ④ 答复后重算 frontier
    assert "重算" in text or "重新计算" in text
    # ⑤ 完成条件 = frontier 为空
    assert "为空" in text
    # ⑥ 事实派去查、不问用户
    assert "事实" in text


def test_grill_puts_every_frontier_question_to_the_user_with_a_recommendation():
    """② 整条 frontier 一次性抛出：编号 + 每条附推荐答案。"""
    text = GRILL.read_text(encoding="utf-8")
    assert "推荐答案" in text
    assert "编号" in text or "Q1" in text


def test_grill_deferrs_questions_that_depend_on_open_ones():
    """④ 依赖本轮未决问题的问归下一轮，不在同一轮里猜答案。"""
    text = GRILL.read_text(encoding="utf-8")
    assert "下一轮" in text


def test_grill_resolves_code_answerable_questions_itself():
    """G4：能由代码/规格判定的问题带 `文件:行号` 证据自行定案，不停轮。"""
    text = GRILL.read_text(encoding="utf-8")
    assert "Code-Resolved" in text
    assert "行号" in text


def test_grill_integrates_must_fixes_back_into_the_design():
    """G2：必须修改项要整合回 design.md，并更新 Pre-Implementation Review。"""
    text = GRILL.read_text(encoding="utf-8")
    assert "Pre-Implementation Review" in text
    assert "必须修改" in text


def test_grill_runs_an_adversarial_verification_before_stopping():
    """G3：grill 产出后、停轮前，另起独立审阅者默认设计有错、逐条证伪。"""
    text = GRILL.read_text(encoding="utf-8")
    assert "grill-adversarial" in text
    assert "证伪" in text
    assert "实测" in text or "复现" in text


def test_grill_evidence_has_a_hard_format_threshold():
    """G5：Confirmed Decisions ≥3 条，每条附 `来源: <run id>`。"""
    text = GRILL.read_text(encoding="utf-8")
    assert "3 条" in text
    assert "来源:" in text


def test_grill_report_has_reviewer_and_risk_sections():
    """G6：报告结构补 `## Reviewer` 与 `## 风险`。"""
    text = GRILL.read_text(encoding="utf-8")
    assert "## Reviewer" in text
    assert "## 风险" in text


def test_grill_covers_the_seven_dimensions():
    """G7：需求对齐 / 实现细节 / 依赖 / 风险 / 测试策略 / 文档影响 / 触发与门禁。"""
    text = GRILL.read_text(encoding="utf-8")
    for dimension in (
        "需求对齐",
        "实现细节",
        "依赖",
        "测试策略",
        "文档影响",
        "触发与门禁",
    ):
        assert dimension in text, f"grill 缺维度：{dimension}"


# ------------------------------------------- 保真度：review-loop 的三态与维度


def test_review_loop_verdict_has_three_states():
    """R1：verdict 是三态——BLOCKED 要停下来报告，不自行修复。"""
    text = REVIEW_LOOP.read_text(encoding="utf-8")
    assert "BLOCKED" in text
    assert "不自行修复" in text or "不自己修" in text


def test_review_loop_covers_the_review_dimensions():
    """R2：逐项任务验证 + Spec 对齐 / 安全 / CI 完整性等。"""
    text = REVIEW_LOOP.read_text(encoding="utf-8")
    assert "任务逐项验证" in text
    assert "Spec 对齐" in text
    assert "CI 完整性" in text
    assert "读代码" in text  # 「真实存在」不是看文件名


def test_review_loop_is_batch_aware():
    """R3：tasks.md 标「后续批」的 `[ ]` 不算缺陷，别假报 CHANGES_REQUESTED。"""
    text = REVIEW_LOOP.read_text(encoding="utf-8")
    assert "后续批" in text


def test_review_loop_syncs_change_docs_and_commits_the_fix():
    """R4：修复要同步更新 change 文档并提交。"""
    text = REVIEW_LOOP.read_text(encoding="utf-8")
    assert "审阅修复" in text
    assert "提交" in text


def test_review_loop_establishes_a_review_baseline():
    """R5：审阅前先定基线；分支落后就 rebase 再审。"""
    text = REVIEW_LOOP.read_text(encoding="utf-8")
    assert "merge-base" in text
    assert "rebase" in text


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


@pytest.mark.parametrize("template", [GRILL, REVIEW_LOOP], ids=["grill", "review-loop"])
def test_templates_explain_how_to_get_run_ids(template: Path):
    """「怎么取 run id」是 host 无关的策略，必须写在模板里而不是各适配器各编一套。"""
    text = template.read_text(encoding="utf-8")
    assert "WITNESSLOOP_RUN_ID" in text  # 环境优先
    assert "兜底" in text or "取不到" in text  # 生成兜底
    assert "reviewer_run_id" in text and "author_run_id" in text


def test_review_loop_template_ties_reviewer_identity_and_manifest():
    text = REVIEW_LOOP.read_text(encoding="utf-8")
    # reviewer ≠ author
    assert "reviewer_run_id" in text and "author_run_id" in text
    # 收尾调 manifest build
    assert "manifest build" in text
