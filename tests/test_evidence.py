"""A 组：`evidence.grill_evidence_findings`（change grill-evidence-gate / D1）。

判据是**块级**的（对抗验证实测：本仓 dogfood 的 `来源:` 全在**续行**，行级口径 0 命中）。
"""

from __future__ import annotations

import itertools
import random
import re
import time
from pathlib import Path

import pytest

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


# =====================================================================================
# change `confirm-gate-fail-closed`：`## Open Questions` 判据从 fail-open 改 fail-closed
#
# 判据面三处（design 的 D1/D2/D4 候选集合、D8 逐份校验、D9 跳代码围栏）。
# 本文件覆盖**纯函数**层；`D8` 的接线用例在 `tests/test_check_grill_evidence.py`。
# =====================================================================================

REPO_ROOT = Path(__file__).resolve().parents[1]

#: 接入方非逐字报告的**冻结副本**（C3 的 fixture）——见 `test_the_adopters_non_verbatim_report_passes`。
ADOPTER_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "adopter-grill-design-nonverbatim.md"
)

#: 占位答复（抽出正文 3 字，命中 `_UNCONFIRMED_STRONG` 的 `待拍板`）。
_PLACEHOLDER_CONFIRMATION = "- **Q1**: 用户答复：待拍板；确认时间: t"
#: 实质答复（同一前缀，抽出正文 21 字 ⇒ 越过 `_UNCONFIRMED_MAX_ANSWER_LEN = 20`）。
_SUBSTANTIVE_CONFIRMATION = "- **Q1**: 用户答复：甲；确认时间: t"


def _doc(
    *,
    decisions: tuple[str, ...] = (D1, D2, D3),
    open_title: str | None = "Open Questions",
    open_body: str = "（无）",
    confirmations: tuple[str, ...] = ("（无）",),
    extra: tuple[tuple[str, str], ...] = (),
) -> str:
    """拼一份决策记录；`extra` 插入额外的**整行标题 + 正文**（H3 也照写）。

    `open_title=None` ⇒ 压根不产出 Open Questions 类小节。
    """
    parts = [
        "# Grill: x 设计追问", "", "## Reviewer", "- run id: `r`", "",
        "## Confirmed Decisions", "", *decisions, "",
        "## Code-Resolved Questions", "- 无", "",
    ]
    if open_title is not None:
        parts += [f"## {open_title}", "", *open_body.splitlines(), ""]
    for title, body in extra:
        parts += [title, "", *body.splitlines(), ""]
    parts += ["## User Confirmation", "", *confirmations]
    return "\n".join(parts) + "\n"


def _messages(findings: list) -> list[str]:
    return [f.message for f in findings]


def _read_repo_report(change_id: str, rel: str) -> str:
    """读本仓一份**已落库**的报告（change 可能已归档到 `archive/<date>-<id>/`）。"""
    root = REPO_ROOT / "openspec" / "changes"
    for candidate in sorted(root.rglob(rel)):
        if any(change_id in part for part in candidate.parts):
            return candidate.read_text(encoding="utf-8")
    raise AssertionError(f"本仓找不到 change `{change_id}` 的 {rel}")


# ---------------------------------------------------------------- A 组：候选集合（D2/D3/D6）

#: `design.md §D2` 那张判定表的**每一行** + M3/M-E 的四条细则与两条已知副作用。
CANDIDATE_TITLES = (
    ("Open Questions", True),
    ("Open Questions（收敛后）", True),
    ("Open Questions（**只有这一条必须用户拍板**）", True),
    ("Design-Level Open Questions（已并入 design 的 Q1–Q6）", True),
    ("Remaining Open Questions", True),
    ("Open Questions (remaining)", True),           # M3 ①：半角括号同样剥
    ("Open Questions（A）（B）", True),              # M3 ③：连续尾括号全剥
    ("Open Questions（）", True),                   # M-E ④：空括号同样剥
    ("Open Questions ()", True),
    ("Non-Open Questions", True),                   # (b) 的前缀比直觉宽 ⇒ 多收一节（接受）
    ("未解决 Open Questions", True),
    ("逐条对抗（针对上游 Confirmed Decisions / 证伪清单 / 风险 / Open Questions）", False),
    ("Open Questions 汇总", False),                  # 短语不是**结尾**
    ("Open Questions（a（b）c）", False),             # M-E ④：嵌套括号不算限定语
    ("Open Questions (a(b)c)", False),
    ("Open questions", False),                      # M3 ②：大小写敏感
    ("open questions", False),
    ("Open  Questions", False),                     # 双空格（已知副作用）
    ("Open Questions：", False),                     # 尾部全角冒号（已知副作用）
    ("Code-Resolved Questions", False),             # `Question` 单数（R2 的钉子）
    ("`Open Questions`", False),                    # 标题行带反引号（声明 6）
)


@pytest.mark.parametrize("title,expected", CANDIDATE_TITLES, ids=[t for t, _ in CANDIDATE_TITLES])
def test_open_question_title_judgement(title: str, expected: bool):
    """A1：候选判定逐行对齐 §D2 的判定表。"""
    got = evidence._open_question_sections({title: ""})
    assert (title in got) is expected, f"{title!r} 的候选判定应为 {expected}，实测 {got}"


def test_a_hyphen_dense_title_is_judged_in_linear_time():
    """审阅 Issue 1（**阻塞**）：候选判定必须**线性**——不得指数回溯。

    规范形态 `^(?:\\S+[- ])*Open Questions$` 的 `\\S+` 与 `[- ]` **字符集相交**
    （`-` 既是词内合法字符、又是分隔符）⇒ 2^(连字符数) 条回溯路径。实测（修前）：
    45 字标题 0.34 s、53 字 **6.5 s**、101 字**等于挂住**；`check` / `guard` 共用这条路径
    ⇒ 一份报告即可把门禁挂住（与 `guard-crash-exit` 的「不许崩到入口兜底」同类）。

    阈值 0.05 s：线性实现是**微秒级**（留 ~10⁴ 倍余量给慢机器），
    而 20 002 字的输入即便退化成**平方**也会 ~0.5 s ⇒ 这条用例同时排除两种退化。
    ⚠️ 输入**以分隔符结尾**（`x-x-…-x-`）：否则新实现的「末位必须是分隔符」会提前返回，
    整段前缀根本没被扫到——那样的用例证明不了什么。
    """
    for hyphens in (26, 10_000):
        title = "-".join(["x"] * (hyphens + 1)) + "-"
        start = time.perf_counter()
        evidence._is_open_questions_title(title)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.05, (
            f"{len(title)} 字、{hyphens} 个连字符的标题耗时 {elapsed:.4f}s"
            "——判定退化成指数/平方回溯了（候选判定对**每个** H2 标题都跑）"
        )


def test_a_long_run_of_trailing_qualifiers_is_stripped_in_linear_time():
    """同一类缺陷的另一条路径（**本轮的实测发现**）：剥尾括号也不得是 O(n²)。

    修前实测：`Open Questions` + `（a）` × 20 000 ⇒ **19.3 s**（每剥一层都从左往右重搜一遍）。
    """
    title = "Open Questions" + "（a）" * 10_000
    start = time.perf_counter()
    evidence._is_open_questions_title(title)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.05, f"剥尾括号退化成 O(n²) 了：{elapsed:.4f}s"


#: spec.md:38-39 / `design.md §D2` 的**规范形态** —— 实现改成线性扫描后，用它当 oracle
#: 逐输入核对等价性（⚠️ 输入刻意短：这个 oracle 自己就是会指数回溯的那一个）。
_SPEC_BRACKET_TAIL_RE = re.compile(r"[（(]([^（）()]*)[）)]$")
_SPEC_TAIL_RE = re.compile(r"^(?:\S+[- ])*Open Questions$")


def _oracle_is_candidate(title: str) -> bool:
    """按**规范正则**（逐字照抄 spec）判候选——只作等价性 oracle，不进生产路径。"""
    if title == "Open Questions":
        return True
    remaining = title
    while True:
        match = _SPEC_BRACKET_TAIL_RE.search(remaining)
        if match is None:
            break
        remaining = remaining[: match.start()].rstrip()
    return bool(_SPEC_TAIL_RE.match(remaining))


#: 尾括号项的各种形态（全角/半角/空/嵌套/带空格/单独的括号…）。
_BRACKET_GROUPS = ("（a）", "（）", "(a)", "（a（b）c）", " (a)", "（）（）", "（", "）", "a）", "（ ）")


def _short_prefix_inputs() -> list[str]:
    """短前缀**穷举**（含连字符 / 空格 / 制表符）⇒ 附上尾短语。"""
    inputs: list[str] = []
    for length in range(5):
        for alphabet in (("a", "-", " "), ("a", "-", " ", "\t")):
            for combo in itertools.product(alphabet, repeat=length):
                inputs.append("".join(combo) + "Open Questions")
    return inputs


def _bracket_tail_inputs() -> list[str]:
    """尾括号项：单独出现 + 与各种前缀组合。"""
    inputs: list[str] = []
    for count in range(4):
        for group in _BRACKET_GROUPS:
            inputs.append("Open Questions" + group * count)
    for prefix in ("", "Design-Level ", "Remaining ", "Non-Open ", "a--b ", "x ", "  ", "- "):
        for group in _BRACKET_GROUPS:
            inputs.append(prefix + "Open Questions" + group)
    return inputs


def _whitespace_variant_inputs() -> list[str]:
    """各种「空白」——`\\s` 与 `str.isspace()` 的定义**并不完全一致**（如 `\\x1c`），
    而本判定的规范是正则 ⇒ 这些输入就是「口径跟引擎走」的钉子。"""
    inputs: list[str] = []
    for space in ("\t", "\n", "\xa0", "　", "\x1c", "\x85", " "):
        inputs += [f"a{space}b Open Questions", f"a{space}Open Questions",
                   f"a {space}b Open Questions", f"{space}Open Questions",
                   f"Open Questions{space}（a）", f"a-{space}b Open Questions"]
    return inputs


def _random_inputs() -> list[str]:
    """随机长输入（⚠️ 连字符 ≤ 6：oracle 自己就是会指数回溯的那一个）。"""
    rng = random.Random(20261015)
    inputs: list[str] = []
    while len(inputs) < 400:
        body = "".join(rng.choice("a- ()\t（）　\xa0") for _ in range(rng.randint(0, 20)))
        if body.count("-") <= 6:
            inputs.append(body + "Open Questions")
    return inputs


def _assert_equivalent(titles: list[str]) -> None:
    """逐个核对线性实现与**规范正则**的判定——不一致就报出**具体输入**。"""
    bad = [
        (title, evidence._is_open_questions_title(title), _oracle_is_candidate(title))
        for title in titles
        if evidence._is_open_questions_title(title) != _oracle_is_candidate(title)
    ]
    assert not bad, "线性实现与 spec 的规范正则不一致（输入 / 实现 / oracle）：" + repr(bad[:5])


#: 等价性核对的四组输入（合计 1 000+ 条；每组的规模由下一条用例守住）。
_EQUIVALENCE_FAMILIES = {
    "短前缀穷举": _short_prefix_inputs(),
    "尾括号形态": _bracket_tail_inputs(),
    "空白口径": _whitespace_variant_inputs(),
    "随机长输入": _random_inputs(),
}


def test_the_equivalence_corpus_is_large_enough():
    """输入集**不许被改小**——这条用例的价值正来自覆盖面（下面是当时实测的规模）。"""
    sizes = {name: len(items) for name, items in _EQUIVALENCE_FAMILIES.items()}
    assert sum(sizes.values()) > 1000, f"等价性输入集被改小了：{sizes}"


@pytest.mark.parametrize("titles", _EQUIVALENCE_FAMILIES.values(), ids=list(_EQUIVALENCE_FAMILIES))
def test_candidate_judgement_matches_the_spec_regex(titles: list[str]):
    """审阅 Issue 1 的「**证明语义没变**」：线性实现与 spec 的规范正则**逐输入等价**。

    oracle 是**规范正则本身**（逐字照抄 spec 的 `^(?:\\S+[- ])*Open Questions$` 与
    D2 的尾括号剥离）⇒ 把「改法等价」变成机械核对，而不是我的口述。
    """
    _assert_equivalent(titles)


def test_candidate_titles_are_sorted_and_only_candidates():
    """A2：候选来自 `dict` 的 key ⇒ **必须排序后**返回（F7 的确定性钉子）。"""
    sections = {
        "Open Questions 汇总": "",       # 非候选
        "Remaining Open Questions": "",
        "Open Questions": "",
        "Design-Level Open Questions（x）": "",
        "## 风险": "",
    }
    assert evidence._open_question_sections(sections) == [
        "Design-Level Open Questions（x）",
        "Open Questions",
        "Remaining Open Questions",
    ]


def test_sections_keeps_merging_same_titled_sections():
    """A4（回归护栏）：`setdefault` 的**合并**语义未动（D6/CQ3）。

    改成覆盖式会让「要求变少」⇒ 开新洞；本仓两份真实报告（各两个 `## User Confirmation`）
    今天就依赖它。⚠️ 这两条**实现前也绿**——它钉的是「别顺手改掉既有语义」。
    """
    text = (
        "## Open Questions\n- **Q1** 甲？\n\n"
        "## User Confirmation\n- **Q1**: 用户答复：甲；确认时间: t\n\n"
        "## Open Questions\n- **Q2** 乙？\n\n"
        "## User Confirmation\n- **Q2**: 用户答复：乙；确认时间: t\n"
    )
    sections = evidence._sections(text)
    assert set(sections) == {"Open Questions", "User Confirmation"}
    assert evidence._open_question_indexes(sections["Open Questions"]) == {1, 2}
    assert set(evidence._confirmations(sections["User Confirmation"])) == {1, 2}


def test_code_resolved_questions_is_never_a_candidate():
    """A3 / X6（R2 的钉子）：`## Code-Resolved Questions` **不是**候选。

    本仓 6 份真实报告的该小节正文里**满是** Q1–Q4 ⇒ 一旦误判成候选就是**假红一大片**。
    """
    text = _doc(
        open_body="（无）",
        extra=(("## Code-Resolved Questions", "- **Q1** 甲？\n- **Q2** 乙？\n- **Q3** 丙？\n- **Q4** 丁？"),),
    )
    assert evidence.grill_evidence_findings(text) == []


# ---------------------------------------------------------------- B 组：正文判据（D1/D4）

def test_missing_open_questions_section_is_flagged_without_a_hint():
    """B1 / F3：**完全没有** Open Questions 类标题 ⇒ 1 条，与缺 `## User Confirmation` 同形。"""
    findings = evidence.grill_evidence_findings(_doc(open_title=None))
    assert _messages(findings) == ["缺少 `## Open Questions` 小节"]


def test_a_title_without_the_phrase_is_not_a_candidate():
    """B2 / X1（issue 的招牌攻击）：标题**完全不含** `Open Question` 字样 ⇒ 红（今天绿）。

    因为标题不含该子串，D4 的附加提示**不出现**——文案不制造「它差一点就对」的错觉。
    """
    text = _doc(open_title="悬而未决的疑问", open_body="- **Q1** 真的问题？")
    assert _messages(evidence.grill_evidence_findings(text)) == ["缺少 `## Open Questions` 小节"]


def test_a_near_miss_title_is_flagged_and_listed():
    """B3 / F1：含短语但**不合 D2** 的标题 ⇒ 红，且诊断**列出它**（响亮报错，不是静默）。"""
    text = _doc(open_title="Open Questions 汇总", open_body="- **Q1** 真的问题？")
    findings = evidence.grill_evidence_findings(text)
    assert len(findings) == 1
    assert findings[0].message.startswith("缺少 `## Open Questions` 小节")
    assert "Open Questions 汇总" in findings[0].message


def test_the_hint_lists_every_title_containing_the_phrase():
    """F6：含该字样的标题**全部、去重、排序**列出（含语义无关的那个）。"""
    text = _doc(
        open_title="逐条对抗（针对上游 Confirmed Decisions / 风险 / Open Questions）",
        open_body="- 无",
        extra=(("## Open Questions 汇总", "- 无"),),
    )
    findings = evidence.grill_evidence_findings(text)
    assert len(findings) == 1
    assert (
        "`Open Questions 汇总`、`逐条对抗（针对上游 Confirmed Decisions / 风险 / Open Questions）`"
        in findings[0].message
    )


def test_the_two_known_title_side_effects_differ_in_whether_the_hint_appears():
    """A1 末句（`design.md §2.5` / `spec.md` 声明 6 的两条已知副作用）。

    「非候选」这一半由 `CANDIDATE_TITLES` 钉住；这里钉**另一半**——
    **有无附加提示不同**：提示用的子串是 `Open Question`（大小写敏感、且要求**连续**），
    ⇒ `Open  Questions`（双空格）**不**含它 ⇒ 通用文案、**无**提示；
    尾部全角冒号的 `Open Questions：` **含**它 ⇒ **有**提示。
    （逐字/近义那两条**是**候选，不走这一档。）
    """
    no_hint = _doc(open_title="Open  Questions", open_body="- **Q1** 真的问题？")
    assert _messages(evidence.grill_evidence_findings(no_hint)) == ["缺少 `## Open Questions` 小节"]

    with_hint = _doc(open_title="Open Questions：", open_body="- **Q1** 真的问题？")
    messages = _messages(evidence.grill_evidence_findings(with_hint))
    assert len(messages) == 1
    assert "检测到含" in messages[0] and "Open Questions：" in messages[0]


def test_the_hint_names_the_substring_that_is_actually_filtered_on():
    """实现审阅 issue 4：提示里的字样必须与**实际筛选口径**一致（单数 `Open Question`）。

    一个含 `Open Question` 而**不含** `Open Questions` 的标题会被列出 ⇒
    文案若写复数就是在陈述一件不成立的事。
    """
    text = _doc(open_title="Open Question Archive", open_body="- 无")
    messages = _messages(evidence.grill_evidence_findings(text))
    assert len(messages) == 1
    assert "Open Question Archive" in messages[0]
    assert "含 `Open Question` 字样" in messages[0]
    assert "含 `Open Questions` 字样" not in messages[0]


def test_an_empty_shell_plus_a_synonym_hiding_a_real_question():
    """B4 / F2 / X2（§1.5 的洞）：逐字小节留空 + 真问题搬进**近义**小节 ⇒ 红（今天绿）。"""
    text = _doc(
        open_body="（无）",
        extra=(("## Design-Level Open Questions（已并入 design 的 Q1–Q6）", "- **Q1** 真的问题？"),),
    )
    findings = evidence.grill_evidence_findings(text)
    assert len(findings) == 1
    assert "Open Question Q1 未经用户确认" in findings[0].message


def test_the_union_of_candidates_requires_the_synonym_sections_numbers():
    """C2（D3 的**变异钉子**）：逐字小节装 Q1、近义小节装 Q5，只确认 Q1 ⇒ 红。

    「只取逐字那个」这一变异下本条**必须**红——这是「并集 vs 取一个」的唯一信号。
    """
    text = _doc(
        open_body="- **Q1** 甲？",
        extra=(("## Remaining Open Questions", "- **Q5** 乙？"),),
        confirmations=("- **Q1**: 用户答复：甲；确认时间: t",),
    )
    findings = evidence.grill_evidence_findings(text)
    assert len(findings) == 1
    assert "Q5" in findings[0].message


def test_two_same_titled_sections_are_unioned():
    """B6 / X7：同名小节两次、Q 不同 ⇒ **两个都要确认**；只确认一节 ⇒ 红。"""
    text = (
        "## Confirmed Decisions\n\n" + "\n\n".join((D1, D2, D3)) + "\n\n"
        "## Open Questions\n\n- **Q1** 甲？\n\n"
        "## Open Questions\n\n- **Q2** 乙？\n\n"
        "## User Confirmation\n\n- **Q1**: 用户答复：甲；确认时间: t\n"
    )
    findings = evidence.grill_evidence_findings(text)
    assert len(findings) == 1
    assert "Q2" in findings[0].message


def test_q_numbers_outside_the_candidate_sections_are_not_judged():
    """B9 / X9（M4 ②）：决策块里的 `Q<n>` 引用**不产生**任何要求。"""
    decisions = (
        D1 + "\n  见 Q7 与 Q9",
        D2 + "\n  见 Q9",
        D3,
    )
    text = _doc(
        decisions=decisions,
        open_body="- **Q1** 甲？",
        confirmations=("- **Q1**: 用户答复：甲；确认时间: t",),
    )
    assert evidence.grill_evidence_findings(text) == []


def test_an_empty_verbatim_section_is_accepted():
    """CQ1 / 声明 1（§8.1 的 G4）：逐字小节**存在但为空** ⇒ 空真通过（与今天一致）。

    「必须显式写 `（无）`」这类判据**没有安全收益**（作者照样能写 `（无）`）⇒ 本就该通过；
    空行与 `（无）` 两种写法都钉一遍。
    """
    for body in ("（无）", "", "  "):
        assert evidence.grill_evidence_findings(_doc(open_body=body)) == [], repr(body)


def test_questions_not_written_as_qn_are_not_judged():
    """B11 ① / X10：候选小节**内**、但**不写成 `Q<n>`** 的问题不判（声明 1/3 的收窄措辞）。"""
    text = _doc(open_body="- **问题**：这个门禁要不要收紧？\n\n待定：A 还是 B？")
    assert evidence.grill_evidence_findings(text) == []


def test_a_fullwidth_digit_is_still_matched():
    """X10 的反例：`\\bQ(\\d+)\\b` 的 `\\d` 在 `str` 模式匹配 Unicode 数字 ⇒ **不是漏判**。"""
    findings = evidence.grill_evidence_findings(_doc(open_body="- **Q１** 全角数字的问题？"))
    assert len(findings) == 1
    assert "Open Question Q1 未经用户确认" in findings[0].message


def test_a_third_level_heading_is_not_a_candidate_and_gets_no_hint():
    """B11 ② / F12（X4 的边界钉子）：`### Open Questions`（H3）⇒ 候选为空 ⇒ 红。

    且**断言附加提示不出现**——提示源是 `_sections()` 的 key，**只含 H2**（已知盲区）。
    """
    text = _doc(open_title=None, extra=(("### Open Questions", "- **Q1** 藏在 H3 里？"),))
    assert _messages(evidence.grill_evidence_findings(text)) == ["缺少 `## Open Questions` 小节"]


def test_the_placeholder_length_threshold_is_what_separates_these_two():
    """B13 / X12（声明 12 的边界钉子）：两句**只差长度**（同一前缀 `待拍板`）。

    ⚠️ 不许拿 `用户说待确认，稍后补上`（11 字）当第 ② 个输入——它绿是因为 `待确认` 只做
    **整串相等**、把它原样截短照样绿 ⇒ 用例会**因为错误的理由通过**。
    """
    short = _doc(
        open_body="- **Q1** 甲？",
        confirmations=("- **Q1**: 用户答复：待拍板；确认时间: t",),
    )
    long = _doc(
        open_body="- **Q1** 甲？",
        confirmations=("- **Q1**: 用户答复：待拍板，具体细节我会在下周的评审会议上确认；确认时间: t",),
    )
    assert any("占位文本" in m for m in _messages(evidence.grill_evidence_findings(short)))
    assert evidence.grill_evidence_findings(long) == []


def test_the_last_confirmation_line_for_a_number_wins():
    """B17 ① / X16（声明 15 的边界钉子）：占位在前、实质在后 ⇒ 末行赢 ⇒ 绿。"""
    text = _doc(
        open_body="- **Q1** 甲？",
        confirmations=(_PLACEHOLDER_CONFIRMATION, _SUBSTANTIVE_CONFIRMATION),
    )
    assert evidence.grill_evidence_findings(text) == []


def test_swapping_the_two_confirmation_lines_flips_the_verdict():
    """B17 ② / X16：**对调** ⇒ 1 条——**刻意接受**的顺序相关性（今天已如此）。"""
    text = _doc(
        open_body="- **Q1** 甲？",
        confirmations=(_SUBSTANTIVE_CONFIRMATION, _PLACEHOLDER_CONFIRMATION),
    )
    findings = evidence.grill_evidence_findings(text)
    assert len(findings) == 1
    assert "占位文本" in findings[0].message


def test_two_confirmation_sections_merge_and_the_last_line_still_wins():
    """B17 ③ / X16：两条 `## User Confirmation` 合并后**仍按末行**。"""
    head = _doc(open_body="- **Q1** 甲？", confirmations=(_PLACEHOLDER_CONFIRMATION,))
    assert evidence.grill_evidence_findings(
        head + "\n## User Confirmation\n\n" + _SUBSTANTIVE_CONFIRMATION + "\n"
    ) == []

    head = _doc(open_body="- **Q1** 甲？", confirmations=(_SUBSTANTIVE_CONFIRMATION,))
    findings = evidence.grill_evidence_findings(
        head + "\n## User Confirmation\n\n" + _PLACEHOLDER_CONFIRMATION + "\n"
    )
    assert len(findings) == 1
    assert "占位文本" in findings[0].message


# ---------------------------------------------------------------- D9：代码围栏

def test_a_fenced_user_confirmation_is_not_a_real_confirmation():
    """B12 ① / F13（D9 的钉子）：唯一的 `## User Confirmation` 写在围栏**里**。

    实现前 **0 条（假绿）**——围栏那段被当成真小节；实现后 **2 条**。
    """
    text = (
        "## Confirmed Decisions\n\n" + "\n\n".join((D1, D2, D3)) + "\n\n"
        "## Open Questions\n\n- **Q1** 真的问题？\n\n"
        "```markdown\n"
        "## User Confirmation\n"
        "- **Q1**: 用户答复：甲；确认时间: t\n"
        "```\n"
    )
    messages = _messages(evidence.grill_evidence_findings(text))
    assert len(messages) == 2
    assert "缺少 `## User Confirmation` 小节" in messages
    assert any("Q1 未经用户确认" in m for m in messages)


def test_removing_the_fence_is_the_only_difference():
    """B12 ③ / X11：把围栏**拿掉**（写成普通小节）⇒ 变绿——围栏是唯一的差别。"""
    fenced = (
        "## Confirmed Decisions\n\n" + "\n\n".join((D1, D2, D3)) + "\n\n"
        "## Open Questions\n\n- **Q1** 真的问题？\n\n"
        "```markdown\n## User Confirmation\n- **Q1**: 用户答复：甲；确认时间: t\n```\n"
    )
    unfenced = fenced.replace("```markdown\n", "").replace("```\n", "")
    assert evidence.grill_evidence_findings(fenced) != []
    assert evidence.grill_evidence_findings(unfenced) == []


def test_a_question_inside_a_fence_is_not_judged():
    """B14 / X13（D9 的**对称代价** · 声明 13）：围栏里的 `- **Q2**` 不进判据。

    实现前 **1 条（红）**、实现后 **0 条（绿）**——**刻意接受**，用例守的是边界声明 13。
    """
    text = _doc(
        open_body="- **Q1** 甲？\n\n```text\n- **Q2** 我把真问题围起来\n```",
        confirmations=("- **Q1**: 用户答复：甲；确认时间: t",),
    )
    assert evidence.grill_evidence_findings(text) == []


def test_a_fenced_source_line_is_not_counted():
    """B15 ① / X14（声明 14 的钉子 · R4 主动构造）：`来源:` 写进围栏 ⇒ **多报**一条。

    实现前 **0 条**、实现后 **1 条**「第 1 条 Confirmed Decision 缺 `来源:`」——
    D9 读法 (i) 的另一侧代价，**刻意接受**。
    """
    fenced_source = "- **决策（D1）**：甲。\n  ```yaml\n  来源: `r`\n  ```"
    text = _doc(decisions=(fenced_source, D2, D3))
    messages = _messages(evidence.grill_evidence_findings(text))
    assert messages == ["第 1 条 Confirmed Decision 缺 `来源:`"]


def test_a_whole_fenced_decision_bullet_is_not_counted():
    """B15 ② / X14：整条决策 bullet 写进围栏 ⇒ **多报**「只有 2 条」。"""
    text = _doc(decisions=(D1, D2, "```text\n" + D3 + "\n```"))
    messages = _messages(evidence.grill_evidence_findings(text))
    assert len(messages) == 1
    assert "只有 2 条" in messages[0] and "少于硬门槛 3 条" in messages[0]


def test_a_longer_fence_is_not_closed_by_a_shorter_line():
    """B12 ② / F14：```` ```` ``（4 个）开启、内部一行 ` ``` `（3 个）**不**结束围栏。"""
    text = "````\n```\n## Open Questions\n- **Q1** x\n````\n\n## 风险\n- 无\n"
    assert set(evidence._sections(text)) == {"风险"}


def test_an_unclosed_fence_swallows_the_rest_of_the_file():
    """B12 ② / F14：**未闭合** ⇒ 从开始标记到文件末尾全算围栏内。"""
    text = "## 风险\n- 无\n\n```\n## Open Questions\n- **Q1** 真的问题？\n"
    sections = evidence._sections(text)
    assert set(sections) == {"风险"}
    assert sections["风险"].strip() == "- 无"


def test_a_closing_fence_must_have_nothing_but_whitespace_after_it():
    """B12 ② / F14：结束标记**其后只剩空白** ⇒ `` ``` extra `` 不结束围栏。"""
    text = "```\n## Open Questions\n- **Q1** x\n``` extra\n\n## 风险\n- 无\n"
    assert evidence._sections(text) == {}


def test_tilde_fences_work_the_same_way():
    """B12 ② / F14：`~~~` 围栏同样生效。"""
    text = "~~~\n## Open Questions\n- **Q1** x\n~~~\n\n## 风险\n- 无\n"
    assert set(evidence._sections(text)) == {"风险"}


def test_an_indented_fence_still_opens():
    """spec 写死「**去首尾空白后**以 ≥3 个连续反引号开头」——刻意**不**采用 CommonMark 的
    「最多 3 空格缩进」上限（实现者 SHALL NOT 顺手收窄）。"""
    text = "    ```\n## Open Questions\n- **Q1** x\n    ```\n\n## 风险\n- 无\n"
    assert set(evidence._sections(text)) == {"风险"}


# ---------------------------------------------------------------- B16：候选规则「多收」

def test_a_prefix_widened_title_becomes_a_candidate():
    """B16 / X15（声明 6 的边界钉子 · R5 主动构造）：`Non-Open Questions` 被 (b) 多收。

    实现前 **0 条**、实现后 **1 条**——**刻意接受**（(b) 的前缀比直觉宽）。
    """
    for title in ("## Non-Open Questions", "## 未解决 Open Questions"):
        text = _doc(open_body="（无）", extra=((title, "- **Q9** 这其实不是 Open Question 小节"),))
        findings = evidence.grill_evidence_findings(text)
        assert len(findings) == 1, title
        assert "Q9 未经用户确认" in findings[0].message, title


def test_similar_but_non_candidate_titles_do_not_require_confirmation():
    """B16 / X15 的另一半：**多收**的边界 ≠「凡像的都要确认」。

    `Open Questions 汇总`（短语不在结尾）与 `悬而未决的疑问`（不含短语）都**不是**候选
    ⇒ 它们正文里的 `Q9` 不产生任何要求。
    """
    for title in ("## Open Questions 汇总", "## 悬而未决的疑问"):
        text = _doc(open_body="（无）", extra=((title, "- **Q9** 这不在候选小节里"),))
        assert evidence.grill_evidence_findings(text) == [], title


# ---------------------------------------------------------------- C 组：不误伤（回归护栏）

def test_the_repos_own_two_candidate_titles_do_not_produce_findings():
    """C1 / F4（护栏）：本仓 `archive-awareness` 的真实报告 ⇒ **0 条**。

    `:61` 非逐字 + `:110` 逐字两处候选并存，两节的 Q 都在 `## User Confirmation` 里有确认
    ⇒「取并集」不把本仓自己的历史报告判红。
    """
    text = _read_repo_report("archive-awareness", "reviews/grill-design.md")
    assert evidence.grill_evidence_findings(text) == []


def test_the_adopters_non_verbatim_report_passes():
    """C3 / F5（护栏）：接入方那 1 份非逐字报告（`Design-Level Open Questions（…）`）的真实内容。

    ⇒ **0 条**（它的 Q1/Q2/Q6 都有实质确认）——「收紧必伤存量」在 ③ 下不成立的机械证明。
    这条用例**不是花瓶**：把候选判定退回「只认逐字」它就会红（变异 M1）。

    ⚠️ fixture 是**冻结副本** `tests/fixtures/adopter-grill-design-nonverbatim.md`
    （逐字节取自接入方检出 `/home/happy/wl-review-a/…`，`sha256 7a520c3e…`）。
    实现审阅 issue 3：原先直接读那条**绝对路径**，CI 上没有该检出 ⇒ 这条钉子在 CI 上**恒 skip**，
    而本仓自己的书面标准否掉「能静默消失的守卫」（`tests/test_confirm_gate_docs.py` 的
    `_change_dir` 就是为此写成 fail 不 skip）。
    ⚠️ 副本放在 `tests/fixtures/`：放进本 change 的 `reviews/` 会触发**孤儿报告**红。
    """
    text = ADOPTER_FIXTURE.read_text(encoding="utf-8")
    assert "Design-Level Open Questions（已并入 design 的 Q1–Q6）" in text
    assert evidence.grill_evidence_findings(text) == []


def test_candidate_set_and_findings_are_deterministic():
    """C4 / F7：同一输入连续调用两次 ⇒ 候选集合与 finding **逐条相同**（含顺序）。

    候选来自 `dict` 的 key ⇒ 不排序就会依赖插入序；这里用**反转插入序**的 dict 再跑一遍。
    """
    text = _doc(
        open_body="- **Q1** 甲？",
        extra=(("## Design-Level Open Questions（x）", "- **Q5** 乙？"),),
    )
    first = evidence.grill_evidence_findings(text)
    second = evidence.grill_evidence_findings(text)
    assert [(f.path, f.message) for f in first] == [(f.path, f.message) for f in second]

    sections = evidence._sections(text)
    assert evidence._open_question_sections(sections) == evidence._open_question_sections(
        dict(reversed(list(sections.items())))
    )
