"""#1：`reviews/` 下的每个报告都必须被某份 manifest 绑定（无孤儿报告）。

在此之前 `check` 只保证「**至少有一份** manifest 且每份都合规」——先把
`grill-review.md` 绑上、把 `grill-adversarial.md` 晾在一边，门禁照样绿，
那份对抗验证报告就能随便漂移而无人发现。

**只做文件名交叉引用**（`report_path` 解析后的相对路径 vs `reviews/**/*.md`），
**不解析报告正文**——那是另一个 issue 的范畴，有假阳性面。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all, git
from helpers import change_dir, check, commit_content, write_artifact, write_review

CHANGE = "add-retry"
REVIEWS = f"openspec/changes/{CHANGE}/reviews"
GRILL_REPORT = "reviews/grill-review.md"
ADVERSARIAL_REPORT = "reviews/grill-adversarial.md"


def _reports_dir(repo: Path) -> Path:
    return change_dir(repo, CHANGE) / "reviews"


def _write_adversarial_report(repo: Path, body: str = "PASS\n\n对抗验证通过。\n") -> Path:
    """只写报告、**不**给 manifest——用来造孤儿。"""
    return write_artifact(repo, f"{REVIEWS}/grill-adversarial.md", body)


# ---------------------------------------------------------------- 孤儿 / 全绑


def test_orphan_report_is_rejected(gated: Path, cli):
    """只绑 grill-review.md，把 grill-adversarial.md 晾着 → 必须拦下并点名。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")  # 绑 reviews/grill-review.md
    _write_adversarial_report(gated)  # 孤儿
    commit_all(gated, "证据：只绑了一份报告")

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL
    assert "孤儿报告" in err
    assert "grill-adversarial.md" in err
    # 被绑定的那份不该被误报
    assert "grill-review.md 未被任何 manifest 绑定" not in err


def test_all_reports_bound_passes(gated: Path, cli):
    """两个报告各一份 manifest → 通过。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    write_review(
        gated, CHANGE, stage="grill-adversarial", report_rel=ADVERSARIAL_REPORT
    )
    commit_all(gated, "证据：两份报告都绑了")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_reports_nested_deeper_are_also_checked(gated: Path, cli):
    """`reviews/**/*.md`——子目录里的报告同样要绑。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    write_artifact(gated, f"{REVIEWS}/sub/deep-review.md", "PASS\n")
    commit_all(gated, "证据")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "孤儿报告" in err
    assert "sub/deep-review.md" in err


def test_no_reports_at_all_is_not_an_orphan_problem(gated: Path, cli):
    """边界：`reviews/` 下没有 `.md` 报告时不报孤儿。

    （manifest 缺报告另有 `_check_hashes` 的「报告不存在」在管。）
    """
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    _reports_dir(gated).joinpath("grill-review.md").unlink()
    commit_all(gated, "报告丢了")

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL  # 缺报告本身就要拦
    assert "报告不存在" in err
    assert "孤儿报告" not in err


def test_extra_non_markdown_files_are_not_orphans(gated: Path, cli):
    """只对 `.md` 报告做交叉引用；`reviews/` 下的其它东西不管。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    write_artifact(gated, f"{REVIEWS}/notes.json", '{"note": 1}\n')
    commit_all(gated, "证据")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_two_manifests_binding_the_same_report_is_not_an_error(gated: Path, cli):
    """保持简单：多份 manifest 指向同一报告不额外报错（仍只要求无孤儿）。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    write_review(
        gated, CHANGE, stage="grill-copy", report_rel=GRILL_REPORT
    )
    commit_all(gated, "证据")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


# ---------------------------------------------------------------- round-trip


def _build(cli, repo: Path, stage: str, report: str):
    return cli(
        "manifest", "build", "--root", str(repo), "--change", CHANGE,
        "--stage", stage, "--report", report, "--base", "main",
    )


def test_round_trip_then_orphan_when_a_manifest_is_removed(repo: Path, cli):
    """真实 CLI：两份报告各 build 一次 → check 绿；删掉一份 manifest → 孤儿。"""
    cli("init", "--root", str(repo))
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    commit_content(repo, CHANGE)

    directory = _reports_dir(repo)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "grill-review.md").write_text("PASS\n", encoding="utf-8")
    (directory / "grill-adversarial.md").write_text("PASS\n", encoding="utf-8")

    for stage, report in (("grill", GRILL_REPORT), ("grill-adversarial", ADVERSARIAL_REPORT)):
        code, _, err = _build(cli, repo, stage, report)
        assert code == C.EXIT_PASS, err

    commit_all(repo, "证据")
    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, err

    # 删掉对抗那份 manifest → 它的报告变成孤儿
    (directory / "grill-adversarial.manifest.json").unlink()
    commit_all(repo, "删掉一份 manifest")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "孤儿报告" in err
    assert "grill-adversarial.md" in err
