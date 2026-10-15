"""B1 负向 / B2 / B3：`check` 侧的 grill 证据正文校验（回归审阅 Issue 1 补齐）。

`tests/test_evidence.py` 覆盖**纯函数**层；本文件覆盖 `check` 的**接线**层——
「正文不合格 / stage 缺失 / stage 拼错」三种情形都必须**真红**且可诊断。
"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all
from helpers import VALID_GRILL_REPORT, check, commit_content, write_review

CHANGE = "add-x"


def test_check_red_when_the_grill_report_body_is_incomplete(gated: Path, cli):
    """B1 负向：正文不合格（空壳）**即使被 manifest 绑上**，`check` 也必须红。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill", report_body="PASS\n\n看着不错。\n")
    commit_all(gated, "证据")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "Confirmed Decisions" in err


def test_check_red_when_the_stage_field_is_missing(gated: Path, cli):
    """B2：`stage` 已纳入必填字段——缺它就红。"""
    commit_content(gated, CHANGE)
    manifest = write_review(gated, CHANGE, stage="grill")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    del doc["stage"]
    manifest.write_text(json.dumps(doc), encoding="utf-8")
    commit_all(gated, "证据：manifest 缺 stage")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "缺字段" in err and "stage" in err


def test_check_names_the_existing_stage_so_a_typo_is_diagnosable(gated: Path, cli):
    """B3 / spec Scenario「stage 拼错可诊断」：`stage=grills` ⇒ 红且**点名现有 stage**。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grills")
    commit_all(gated, "证据：stage 拼错")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "现有 stage：grills" in err


def test_check_names_a_byte_bad_manifest_and_does_not_crash(gated: Path, cli):
    """C8（R2 N1）：`check` 的 manifest 读点在 `contract.py`（`checkcmd.py:75` 先于 `:78` 的 `evidence`）。

    字节坏必须**干净红**（与 JSON 坏同归）且**点名该文件**——不能是崩溃（入口兜底会把崩溃也变成非 0，
    所以只断言退出码不够：必须断言**是那条 finding**、且**不是**入口的「内部错误」）。
    """
    commit_content(gated, CHANGE)
    manifest = write_review(gated, CHANGE, stage="grill")
    manifest.write_bytes(b'{"stage": "grill", "broken": "\xff\xfe"}')
    commit_all(gated, "证据：manifest 字节坏")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "manifest 无法解析" in err
    assert "grill.manifest.json" in err
    assert "内部错误" not in err  # 崩到入口兜底 = 不算「同归」，用例须排除


def test_check_stays_fail_closed_on_an_undecodable_report(gated: Path, cli):
    """spec「崩溃兜底不改变 `check` 的退出码语义」：报告读不出 ⇒ **干净红**（非 0 且不是崩到入口）。

    ⚠️ 审阅 R1 指出原版是**弱测试**：只断言 `code != EXIT_PASS`，而那个非 0 可能来自
    `contract._check_hashes` 的 hash 不匹配（改了报告却没重建 manifest）或**入口兜底**——
    两种都**走不到** `evidence.py` 的报告读点。故这里**先按坏字节重建 manifest**（让 `report_hash`
    与坏字节一致、越过 hash 检查），真正打到读点，再断言**是那条 finding**、且**不是**入口的「内部错误」。
    """
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    report = gated / "openspec" / "changes" / CHANGE / "reviews" / "grill-review.md"
    report.write_bytes(b"# Grill\n\xff\xfe")
    build_code, _, build_err = cli(
        "manifest",
        "build",
        "--root",
        str(gated),
        "--base",
        "main",
        "--change",
        CHANGE,
        "--stage",
        "grill",
        "--report",
        "reviews/grill-review.md",
        "--reviewer-run-id",
        "run-reviewer-1",
        "--author-run-id",
        "run-author-1",
    )
    assert build_code == C.EXIT_PASS, build_err
    commit_all(gated, "证据：坏报告 + 按坏字节重建 manifest")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "报告无法解码" in err
    assert "内部错误" not in err  # 崩到入口兜底 = 不是「干净的红」，用例须排除


# ---------------------------------------------------------------- D8：逐份校验（不只 matching[0]）

#: 一份**不合格**的报告——**标题逐字**（`## Open Questions`）+ 只 1 条 Confirmed Decision
#: + 缺 `## User Confirmation` + `Q1`/`Q2` 未确认 ⇒ 恰好 **4 条** finding。
#: ⚠️ fixture MUST 是「标题逐字」的那一份（对抗轮 M-A）：拿**标题非逐字**的报告当 fixture，
#: 它在**今天的代码**下本来就少掉 Open Questions 那部分（fail-open）⇒ 用例会**因为错误的
#: 理由通过**，钉不住 D8。
BAD_GRILL_REPORT = (
    "# Grill: x 设计追问\n"
    "\n"
    "## Confirmed Decisions\n"
    "\n"
    "- **决策（D1）**：甲。\n"
    "  理由：因为甲；来源: `r`\n"
    "\n"
    "## Open Questions\n"
    "\n"
    "- **Q1** 甲还是乙？\n"
    "- **Q2** 丙还是丁？\n"
)


def _write_change(tmp_path: Path, entries: tuple[tuple[str, str, str, object], ...]) -> Path:
    """造一个 change 目录：`(manifest 文件名, stage, 报告相对路径, 报告正文)`。

    正文给 `bytes` 就是**字节坏**的（用来构造「读不出」那一份）。
    """
    change = tmp_path / "openspec" / "changes" / "add-x"
    (change / "reviews").mkdir(parents=True)
    for manifest_name, stage, report_rel, body in entries:
        report = change / report_rel
        report.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            report.write_bytes(body)
        else:
            report.write_text(body, encoding="utf-8")
        (change / "reviews" / manifest_name).write_text(
            json.dumps({"stage": stage, "report_path": report_rel}, ensure_ascii=False),
            encoding="utf-8",
        )
    return change


def _pairs(findings) -> list[tuple[str, str]]:
    return [(f.path, f.message) for f in findings]


def test_a_decoy_manifest_does_not_disable_the_body_judgement(tmp_path: Path):
    """B7 / F9 / X8（D8 的钉子 · M2）：诱饵 manifest **不得**让真报告的判据消失。

    造法：`aaa.manifest.json` → 三节逐字齐全的**合规诱饵**（排序在前）、
    `zzz.manifest.json` → `BAD_GRILL_REPORT`。
    ⇒ 必须逐条报出那 **4 条**，且与「**没有诱饵**」时**逐条相同**；
    诊断（`label` 里带相对报告路径）能定位到**是哪一份**不合格。
    ⚠️ 实现前：诱饵在场 **0 条**、不在场 **4 条**（`design.md §1.1.1` 实测）。
    """
    from witnessloop import evidence

    without_decoy = evidence.grill_evidence_findings_in_change(
        _write_change(
            tmp_path / "without",
            (("zzz.manifest.json", "grill", "reviews/zzz-real.md", BAD_GRILL_REPORT),),
        )
    )
    with_decoy = evidence.grill_evidence_findings_in_change(
        _write_change(
            tmp_path / "with",
            (
                ("aaa.manifest.json", "grill", "reviews/aaa-decoy.md", VALID_GRILL_REPORT),
                ("zzz.manifest.json", "grill", "reviews/zzz-real.md", BAD_GRILL_REPORT),
            ),
        )
    )

    assert [m for _, m in _pairs(without_decoy)] == [
        "`## Confirmed Decisions` 只有 1 条，少于硬门槛 3 条",
        "缺少 `## User Confirmation` 小节",
        "Open Question Q1 未经用户确认（`## User Confirmation` 里没有 Q1）",
        "Open Question Q2 未经用户确认（`## User Confirmation` 里没有 Q2）",
    ]
    assert _pairs(with_decoy) == _pairs(without_decoy)
    assert all(path == "add-x/reviews/zzz-real.md" for path, _ in _pairs(with_decoy))


def test_multiple_compliant_manifests_are_not_an_error(tmp_path: Path):
    """B8 / F10（D8 的对照）：**两份都合格** ⇒ 0 条（逐份 ≠「多份即红」）。"""
    from witnessloop import evidence

    findings = evidence.grill_evidence_findings_in_change(
        _write_change(
            tmp_path,
            (
                ("aaa.manifest.json", "grill", "reviews/aaa.md", VALID_GRILL_REPORT),
                ("zzz.manifest.json", "grill", "reviews/zzz.md", VALID_GRILL_REPORT),
            ),
        )
    )
    assert findings == []


def test_an_unreadable_report_does_not_stop_the_others(tmp_path: Path):
    """B8（spec Scenario「一份读不出不影响其余份」）：该份报「无法核验」，另一份照常判定。"""
    from witnessloop import evidence

    findings = evidence.grill_evidence_findings_in_change(
        _write_change(
            tmp_path,
            (
                ("aaa.manifest.json", "grill", "reviews/aaa.md", b"# Grill\n\xff\xfe"),
                ("zzz.manifest.json", "grill", "reviews/zzz.md", BAD_GRILL_REPORT),
            ),
        )
    )
    assert _pairs(findings)[0] == (
        "add-x/reviews/aaa.md",
        "报告无法解码（UnicodeDecodeError）：无法核验该 stage 的证据",
    )
    assert [m for _, m in _pairs(findings)[1:]] == [
        "`## Confirmed Decisions` 只有 1 条，少于硬门槛 3 条",
        "缺少 `## User Confirmation` 小节",
        "Open Question Q1 未经用户确认（`## User Confirmation` 里没有 Q1）",
        "Open Question Q2 未经用户确认（`## User Confirmation` 里没有 Q2）",
    ]


def test_a_real_record_bound_to_another_stage_is_accepted(tmp_path: Path):
    """B10 / F11（M-B 的边界钉子 · 护栏）：真记录绑 `building`、`stage=grill` 绑合格 stub ⇒ 0 条。

    **刻意接受**（今天与 D8 之后都一样）：`stage=grill` 只有 stub 一个 manifest ⇒ 逐份 =
    只校验 stub。本用例守的是 **spec 边界声明 11**，免得将来有人把它当 bug「修」掉却不改声明。
    """
    from witnessloop import evidence

    findings = evidence.grill_evidence_findings_in_change(
        _write_change(
            tmp_path,
            (
                ("building.manifest.json", "building", "reviews/building-review.md", BAD_GRILL_REPORT),
                ("grill.manifest.json", "grill", "reviews/grill-stub.md", VALID_GRILL_REPORT),
            ),
        )
    )
    assert findings == []
