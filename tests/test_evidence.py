"""A 组：`evidence.grill_evidence_findings`（change grill-evidence-gate / D1）。

判据是**块级**的（对抗验证实测：本仓 dogfood 的 `来源:` 全在**续行**，行级口径 0 命中）。
"""

from __future__ import annotations

from witnessloop import evidence


def _report(
    decisions: list[str],
    open_questions: list[str] | None = None,
    confirmations: list[str] | None = None,
) -> str:
    """拼一份决策记录。`decisions` 每条是一个**多行** bullet 块。"""
    parts = ["# Grill: x 设计追问", "", "## Reviewer", "- run id: `r`", "",
             "## Confirmed Decisions", ""]
    parts += decisions
    parts += ["", "## Open Questions", ""]
    parts += (open_questions or []) or ["（无）"]
    parts += ["", "## 风险", "- 无", "", "## User Confirmation", ""]
    parts += (confirmations or []) or ["（无）"]
    return "\n".join(parts) + "\n"


#: 三条合格决策：bullet 首行**不带** `来源:`，`来源:` 在**续行**（本仓 dogfood 的真实形态）。
D1 = "- **决策（D1）**：内容一。\n  理由：因为甲；来源: `r`"
D2 = "- **决策（D2）**：内容二。\n  理由：因为乙；来源: `r`"
D3 = "- **决策（D3）**：内容三。\n  理由：因为丙；来源: `r`"


def test_qualified_report_has_no_findings():
    text = _report([D1, D2, D3], ["- **Q1** 问题？"], ["- **Q1**: 用户答复：按推荐；确认时间: 2026-10-11"])
    assert evidence.grill_evidence_findings(text) == []


def test_fewer_than_three_decisions_is_flagged():
    findings = evidence.grill_evidence_findings(_report([D1, D2]))
    assert findings, "少于 3 条 Confirmed Decisions 必须报"
    assert any("3" in f.message for f in findings)


def test_source_only_on_continuation_line_counts():
    # 行级口径会漏判——这正是本仓 dogfood 的形态。
    text = _report([D1, D2, D3])
    assert evidence.grill_evidence_findings(text) == []


def test_missing_source_on_a_decision_is_flagged():
    no_src = "- **决策（D4）**：内容四。\n  理由：因为丁。"  # 块内无 `来源:`
    findings = evidence.grill_evidence_findings(_report([D1, D2, D3, no_src]))
    assert any("来源" in f.message for f in findings)


def test_plain_decision_prefix_also_counts():
    # 模板写法 `- **决策**：`（决策与 ** 相邻）也要算——移植陷阱的护栏。
    plain = [
        "- **决策**：A。\n  来源: `r`",
        "- **决策**：B。\n  来源: `r`",
        "- **决策**：C。\n  来源: `r`",
    ]
    findings = evidence.grill_evidence_findings(_report(plain, ["- **Q1** 问题？"],
                                                        ["- **Q1**: 用户答复：是；确认时间: 2026-10-11"]))
    assert findings == []


def test_open_question_without_confirmation_is_flagged():
    text = _report([D1, D2, D3], ["- **Q1** 未决？", "- **Q2** 也未决？"],
                   ["- **Q1**: 用户答复：是；确认时间: 2026-10-11"])
    findings = evidence.grill_evidence_findings(text)
    assert any("Q2" in f.message for f in findings)


def test_placeholder_confirmation_is_not_a_real_confirmation():
    text = _report([D1, D2, D3], ["- **Q1** 问题？"],
                   ["- **Q1**: 用户答复：待确认；确认时间: 2026-10-11"])
    findings = evidence.grill_evidence_findings(text)
    assert any("Q1" in f.message for f in findings)


def test_long_answer_containing_a_placeholder_token_is_accepted():
    # 启发式：短答复（≤20 字）才查「强占位」；长答复一律视为实质内容。
    long_answer = "用户答复：不采用「待确认」这种写法，改为一律在停轮时逐条给出具体例子后再拍板；确认时间: 2026-10-11"
    text = _report([D1, D2, D3], ["- **Q1** 问题？"], ["- **Q1**: " + long_answer])
    findings = evidence.grill_evidence_findings(text)
    assert findings == []


def test_missing_sections_are_flagged():
    findings = evidence.grill_evidence_findings("# 光秃秃\n\n没有小节。\n")
    assert findings, "缺 ## Confirmed Decisions / ## User Confirmation 必须报"
