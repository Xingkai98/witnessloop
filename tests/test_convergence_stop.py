"""convergence-based-stop：审阅闭环的轮次口径（issue #24）。

用户 2026-10-17 拍板：一轮 = 一个非空 medium+ 批次的闭环；验证期只做修复确认，
新问题进下一批；最多 20 轮，超限 ⇒ BLOCKED + 建议推倒重开；medium+ 全修，
low/nit 登记不修须写理由；出口只有 PASS / BLOCKED + 成因 / 超限 BLOCKED。
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "templates"
PLUGIN = REPO_ROOT / "plugin"
CHANGE = REPO_ROOT / "openspec/changes/convergence-based-stop"

REVIEW_LOOP = TEMPLATES / "review-loop.md"
GRILL = TEMPLATES / "grill.md"
ADAPTER_REVIEW_LOOP = PLUGIN / "commands/review-loop.md"
SPEC = CHANGE / "specs/review-termination/spec.md"

#: 反断言的**显式 allowlist**：只扫这些；不做「全仓减排除」（design §4.4）。
NORMATIVE = (
    REVIEW_LOOP,
    GRILL,
    ADAPTER_REVIEW_LOOP,
    PLUGIN / "commands/grill.md",
    PLUGIN / "README.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs/design.md",
    REPO_ROOT / "docs/gate.md",
    REPO_ROOT / "tests/test_templates.py",
    REPO_ROOT / "tests/test_plugin.py",
    SPEC,
)

#: 旧轮次口径的**短语**（用户 2026-10-17 拍板后不再使用）。
OLD_PHRASES = (
    "3 轮封顶",
    "三轮封顶",
    "有界轮数",
    "轮数封顶",
    "N 轮封顶",
    "或封顶",
    "**封顶**",
)

#: 含「封顶」但与本规则无关的行：必须同一行含「常量」或「路径深度」。
BARE_CAP_ALLOWED = ("常量", "路径深度")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", NORMATIVE, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_normative_surfaces_drop_the_old_round_cap(path: Path):
    text = _read(path)
    rel = path.relative_to(REPO_ROOT)
    for phrase in OLD_PHRASES:
        assert phrase not in text, f"{rel} 仍含旧口径 {phrase!r}"
    for lineno, line in enumerate(text.splitlines(), 1):
        if "封顶" in line:
            assert any(word in line for word in BARE_CAP_ALLOWED), (
                f"{rel}:{lineno} 含裸「封顶」：{line.strip()!r}；"
                "与本规则无关的行必须同行含「常量」或「路径深度」"
            )


def test_review_loop_template_defines_a_medium_plus_batch_round():
    text = _read(REVIEW_LOOP)
    assert "medium" in text
    assert "批次" in text
    assert "冻结" in text
    assert "20" in text
    assert "建议推倒重开" in text or "revise the design" in text


def test_review_loop_template_verification_only_and_deferred():
    text = _read(REVIEW_LOOP)
    assert "验证" in text
    assert "deferred" in text or "下一批" in text
    assert "不得" in text and ("当场" in text or "只做修复验证" in text)


def test_review_loop_template_severity_disposition():
    text = _read(REVIEW_LOOP)
    assert "medium" in text and "必须" in text
    assert "low" in text and "nit" in text
    assert "登记不修" in text and "理由" in text
    assert "冻结" in text


def test_review_loop_template_has_three_exits_and_no_cr_exit():
    text = _read(REVIEW_LOOP)
    assert "PASS" in text and "BLOCKED" in text and "成因" in text
    assert "不是出口" in text
    assert "CHANGES_REQUESTED" in text


def test_review_loop_template_routes_round_20_unclosed_to_the_cap_exit():
    text = _read(REVIEW_LOOP)
    assert "第 20 轮" in text
    assert "超上限" in text
    assert "建议推倒重开" in text or "revise the design" in text


def test_grill_template_adversarial_loop_uses_the_batch_model():
    text = _read(GRILL)
    assert "批次" in text
    assert "20" in text
    assert "建议推倒重开" in text or "revise the design" in text
    assert "frontier" in text
    assert "豁免" in text


def test_plugin_review_loop_adapter_wires_the_batch_model():
    text = _read(ADAPTER_REVIEW_LOOP)
    assert "批次" in text
    assert "20" in text
    assert "deferred" in text or "下一批" in text
    assert "建议推倒重开" in text or "revise the design" in text
    assert "不是出口" in text


def test_plugin_review_loop_adapter_runs_all_template_steps():
    text = _read(ADAPTER_REVIEW_LOOP)
    assert "步骤 1–6" not in text
    assert "1–8" in text or "1-8" in text


def test_spec_requirements_cover_the_new_model():
    text = _read(SPEC)
    for needle in (
        "medium+",
        "批次",
        "deferred",
        "20",
        "建议推倒重开",
        "severity",
        "收口确认",
        "frontier",
        "SHALL NOT 解析",
    ):
        assert needle in text, f"spec 缺 {needle!r}"
    for phrase in OLD_PHRASES:
        assert phrase not in text
