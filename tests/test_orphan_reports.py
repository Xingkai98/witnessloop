"""#1：`reviews/` 下的每个报告都必须被某份 manifest 绑定（无孤儿报告）。

在此之前 `check` 只保证「**至少有一份** manifest 且每份都合规」——先把
`grill-review.md` 绑上、把 `grill-adversarial.md` 晾在一边，门禁照样绿，
那份对抗验证报告就能随便漂移而无人发现。

**只做文件名交叉引用**（`report_path` 解析后的相对路径 vs `reviews/**/*.md`），
**不解析报告正文**——那是另一个 issue 的范畴，有假阳性面。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from witnessloop import constants as C
from witnessloop.hashing import sha256_tree

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


# ------------------------------------------------- 回归：整体跳过 / 路径口径


def _hand_write_manifest(
    repo: Path, stage: str, *, report_path: str, report_hash: str
) -> Path:
    """手写一份 manifest（agent 可写 JSON，等价输入面）。"""
    import json

    from helpers import head_sha, default_base_sha

    doc = {
        "schema": C.SCHEMA_REVIEW_MANIFEST,
        "change_id": CHANGE,
        "stage": stage,
        "reviewer_run_id": f"run-{stage}-reviewer",
        "author_run_id": f"run-{stage}-author",
        "base_sha": default_base_sha(repo),
        "head_sha": head_sha(repo),
        "tasks_hash": sha256_tree(change_dir(repo, CHANGE) / "tasks.md"),
        "spec_hash": sha256_tree(change_dir(repo, CHANGE) / "specs"),
        "diff_hash": "informational",
        "report_hash": report_hash,
        "report_path": report_path,
    }
    path = _reports_dir(repo) / f"{stage}.manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_backslash_decoy_manifest_does_not_disable_the_orphan_rule(gated: Path, cli):
    """回归审阅 §3.2：一份特制 manifest **不能**让整条孤儿规则被跳过。

    构造：`reviews/` 下放一个**文件名含反斜杠**的文件（Linux 上 `\\` 是普通字符），
    再用一份**合法** manifest 指向它——`_check_hashes` 零 finding。
    旧的 `bindings_reliable` 是「全有全无」，于是孤儿判定被整体关掉，
    未绑定的 `grill-adversarial.md` 绿着通过。
    """
    decoy_rel = "reviews/..\\..\\etc\\x.md"
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")  # 绑 grill-review.md
    _write_adversarial_report(gated)  # 孤儿：要抓的目标
    write_review(gated, CHANGE, stage="zzz", report_rel=decoy_rel)  # 诱饵，合法
    commit_all(gated, "证据")

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL, "一份特制 manifest 把整条孤儿规则关掉了"
    assert "孤儿报告" in err
    assert "grill-adversarial.md" in err


def test_broken_report_path_does_not_disable_the_orphan_rule(gated: Path, cli):
    """回归审阅 §4：`_bound_report()=None` **不等于**「该 manifest 已败」。

    只要有一份 manifest 解析不出绑定，孤儿判定就**整体跳过**——这让「解析不出绑定」
    成了关掉规则的开关。改后：某份 manifest 无法贡献绑定，只影响它自己；
    孤儿判定照常对其余报告执行（宁多报不漏报）。
    """
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    _write_adversarial_report(gated)  # 孤儿：要抓的目标
    # 一份 report_path 逃逸的 manifest（它自己会被 _check_hashes 报逃逸）
    _hand_write_manifest(
        gated, "broken", report_path="../../../etc/hosts", report_hash="deadbeef"
    )
    commit_all(gated, "证据")

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL
    assert "孤儿报告" in err
    assert "grill-adversarial.md" in err


@pytest.mark.parametrize(
    "variant",
    [
        "reviews/./grill-review.md",
        "reviews//grill-review.md",
        "reviews/../reviews/grill-review.md",
        "./reviews/grill-review.md",
    ],
)
def test_build_then_check_agree_on_noncanonical_report_paths(repo: Path, cli, variant):
    """回归审阅 §3.3：`manifest build` 接受的写法，`check` 不能反手判孤儿。

    这正是 `manifestcmd` 注释里要避免的「build 报成功、check 立刻拒」自相矛盾——
    而且多打一个 `./` 是**正常用户可踩**的输入，不是恶意。
    """
    cli("init", "--root", str(repo))
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    commit_content(repo, CHANGE)
    _reports_dir(repo).mkdir(parents=True, exist_ok=True)
    (_reports_dir(repo) / "grill-review.md").write_text("PASS\n", encoding="utf-8")

    code, _, err = _build(cli, repo, "grill", variant)
    assert code == C.EXIT_PASS, f"build 接受了 {variant!r}，却：{err}"

    commit_all(repo, "证据")
    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, f"build 说 OK、check 却拒（{variant!r}）：{err}"


def test_build_stores_a_canonical_report_path(repo: Path, cli):
    """build 落盘时就把 `report_path` 规范化，别把口径分歧写进证据。"""
    cli("init", "--root", str(repo))
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    commit_content(repo, CHANGE)
    _reports_dir(repo).mkdir(parents=True, exist_ok=True)
    (_reports_dir(repo) / "grill-review.md").write_text("PASS\n", encoding="utf-8")

    assert _build(cli, repo, "grill", "reviews/../reviews/./grill-review.md")[0] == C.EXIT_PASS

    import json

    doc = json.loads(
        (_reports_dir(repo) / "grill.manifest.json").read_text(encoding="utf-8")
    )
    assert doc["report_path"] == "reviews/grill-review.md"


# ------------------------------------------------- 回归：目录 / 符号链接假阳性


def test_directory_named_like_a_report_is_not_an_orphan(gated: Path, cli):
    """回归审阅 §3.4：`rglob('*.md')` 也会匹配**目录**，那不算报告。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    (reviews_root := _reports_dir(gated) / "notes.md").mkdir(parents=True, exist_ok=True)
    (reviews_root / "inner.txt").write_text("x\n", encoding="utf-8")
    commit_all(gated, "证据")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_symlinked_report_is_not_an_orphan(gated: Path, cli):
    """回归审阅 §3.5：链接与其目标在 `rglob` 里是两个名字。

    只绑**链接**时，目标不能因为「没有 manifest 点名它」被误报孤儿——两者解析到
    同一个文件，按**解析后**的路径比对就不会误判。
    """
    _reports_dir(gated).mkdir(parents=True, exist_ok=True)
    (_reports_dir(gated) / "grill-review.md").write_text("PASS\n", encoding="utf-8")
    commit_content(gated, CHANGE)

    (link := _reports_dir(gated) / "alias.md").symlink_to("grill-review.md")
    assert link.is_file()
    write_review(gated, CHANGE, stage="alias", report_rel="reviews/alias.md")
    commit_all(gated, "证据：只绑链接")

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
