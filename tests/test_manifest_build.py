"""`witnessloop manifest build`：让审阅回路闭合。

关键验收是 **round-trip**：`init` → 内容提交 → `manifest build` → 证据提交 →
`witnessloop check` 通过。build 必须复用 `check` 同一套哈希实现，否则两边会漂移。
"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C
from witnessloop.hashing import sha256_tree

from conftest import commit_all, git
from helpers import (
    change_dir,
    check,
    commit_content,
    commit_evidence,
    head_sha,
    write_artifact,
)

CHANGE = "add-retry"
REPORT = "reviews/building-review.md"


def _build(cli, repo: Path, *extra: str, **kwargs):
    argv = [
        "manifest",
        "build",
        "--root",
        str(repo),
        "--change",
        kwargs.get("change", CHANGE),
        "--stage",
        kwargs.get("stage", "building"),
        "--report",
        kwargs.get("report", REPORT),
        "--reviewer-run-id",
        kwargs.get("reviewer", "run-reviewer-1"),
        "--author-run-id",
        kwargs.get("author", "run-author-1"),
        *extra,
    ]
    return cli(*argv)


def _ready_to_build(repo: Path, cli) -> Path:
    """init + 内容提交 + 一份写好的报告（尚未提交）——build 就绪态。"""
    cli("init", "--root", str(repo))
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    commit_content(repo, CHANGE)
    directory = change_dir(repo, CHANGE)
    (directory / "reviews").mkdir(parents=True, exist_ok=True)
    (directory / REPORT).write_text("PASS\n\n审阅通过。\n", encoding="utf-8")
    return directory


# ---------------------------------------------------------------- round-trip


def test_round_trip_build_then_check_is_green(repo: Path, cli):
    """核心验收：build 产出的 manifest，check 必须认。"""
    _ready_to_build(repo, cli)

    code, out, err = _build(cli, repo)
    assert code == C.EXIT_PASS, err
    assert (change_dir(repo, CHANGE) / "reviews" / "building.manifest.json").is_file()

    commit_all(repo, "证据提交")
    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, err
    assert "通过" in out


def test_round_trip_with_a_protected_spec_write(repo: Path, cli):
    """完整回路：改了受保护 spec（带解释事件）+ build → check 绿。"""
    cli("init", "--root", str(repo))
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    commit_content(
        repo,
        CHANGE,
        spec_writes=(("openspec/specs/retry/spec.md", "# canonical\n"),),
    )
    directory = change_dir(repo, CHANGE)
    (directory / "reviews").mkdir(parents=True, exist_ok=True)
    (directory / REPORT).write_text("PASS\n", encoding="utf-8")
    assert _build(cli, repo)[0] == C.EXIT_PASS

    commit_evidence(repo, CHANGE, events=("openspec/specs/retry/spec.md",))

    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, err


# ---------------------------------------------------------------- 字段与取值


def test_manifest_matches_the_documented_contract(repo: Path, cli):
    """字段名严格对齐 docs/gate.md §3。"""
    directory = _ready_to_build(repo, cli)
    assert _build(cli, repo)[0] == C.EXIT_PASS
    doc = json.loads((directory / "reviews" / "building.manifest.json").read_text("utf-8"))

    assert set(doc) == {
        "schema",
        "change_id",
        "stage",
        "reviewer_run_id",
        "author_run_id",
        "base_sha",
        "head_sha",
        "tasks_hash",
        "spec_hash",
        "diff_hash",
        "report_hash",
        "report_path",
    }
    assert doc["schema"] == C.SCHEMA_REVIEW_MANIFEST
    assert doc["change_id"] == CHANGE
    assert doc["stage"] == "building"
    assert doc["report_path"] == REPORT
    assert not (set(C.REVIEW_MANIFEST_REQUIRED_FIELDS) - set(doc))


def test_hashes_use_the_same_implementation_as_check(repo: Path, cli):
    """build 的 hash 必须等于 check 侧期望的字节哈希（同一函数、同一张表）。"""
    directory = _ready_to_build(repo, cli)
    assert _build(cli, repo)[0] == C.EXIT_PASS
    doc = json.loads((directory / "reviews" / "building.manifest.json").read_text("utf-8"))

    for field, artifact in C.HASHED_ARTIFACTS:
        assert doc[field] == sha256_tree(directory / artifact), field
    assert doc["report_hash"] == sha256_tree(directory / REPORT)


def test_head_sha_is_the_current_head(repo: Path, cli):
    """约定（gate.md §3.1）：内容提交后、证据提交前跑 build。"""
    directory = _ready_to_build(repo, cli)
    assert _build(cli, repo)[0] == C.EXIT_PASS
    doc = json.loads((directory / "reviews" / "building.manifest.json").read_text("utf-8"))
    assert doc["head_sha"] == head_sha(repo)


def test_base_sha_follows_the_given_base(repo: Path, cli):
    directory = _ready_to_build(repo, cli)
    expected = git(repo, "rev-parse", "main").strip()

    assert _build(cli, repo, "--base", "main")[0] == C.EXIT_PASS

    doc = json.loads((directory / "reviews" / "building.manifest.json").read_text("utf-8"))
    assert doc["base_sha"] == expected


# ---------------------------------------------------------------- 负例


def test_reviewer_equal_to_author_is_rejected(repo: Path, cli):
    directory = _ready_to_build(repo, cli)

    code, _, err = _build(cli, repo, reviewer="same-run", author="same-run")

    assert code == C.EXIT_FAIL
    assert "reviewer" in err and "author" in err
    # 不合格就不许写出去——否则 check 才拦，反馈太晚
    assert not (directory / "reviews" / "building.manifest.json").exists()


def test_change_id_escaping_the_changes_root_is_rejected(repo: Path, cli):
    """回归 M2 §4-1：`--change` 与 `--report` 是同一类 agent 输入，必须同款守卫。

    没有这道守卫时 `--change "../../../evil"` 会把 manifest **写到仓外**（实测 exit 0）。
    """
    _ready_to_build(repo, cli)
    outside = repo.parent / "evilwl_changes"  # 仓外
    (outside / "reviews").mkdir(parents=True, exist_ok=True)

    code, _, err = _build(cli, repo, change="../../../evilwl_changes")

    assert code == C.EXIT_FAIL
    assert "逃逸" in err  # 因越界被拒，而不是因其它校验碰巧失败
    assert not (outside / "reviews" / "building.manifest.json").exists()


def test_absolute_change_id_is_rejected(repo: Path, cli):
    """绝对路径也不行（pathlib 会让它直接顶掉前面的相对段）。"""
    _ready_to_build(repo, cli)
    outside = repo.parent / "evilwl_abs"
    (outside / "reviews").mkdir(parents=True, exist_ok=True)

    code, _, err = _build(cli, repo, change=str(outside))

    assert code == C.EXIT_FAIL
    assert "逃逸" in err  # 因为越界被拒，而不是因为「报告不存在」之类的巧合
    assert not (outside / "reviews" / "building.manifest.json").exists()


def test_missing_required_artifacts_is_rejected(repo: Path, cli):
    """回归 M2 §4-2：build 绿灯 / check 红灯的自相矛盾。

    build 只校验 HASHED_ARTIFACTS（tasks/specs），不校验 required_artifacts，
    于是缺 proposal/design 时也能「报成功」，紧接着被 check 拒。
    """
    directory = _ready_to_build(repo, cli)
    (directory / "proposal.md").unlink()
    (directory / "design.md").unlink()

    code, _, err = _build(cli, repo)

    assert code == C.EXIT_FAIL
    assert "proposal.md" in err
    assert not (directory / "reviews" / "building.manifest.json").exists()


def test_report_path_escaping_the_change_dir_is_rejected(repo: Path, cli):
    _ready_to_build(repo, cli)
    code, _, err = _build(cli, repo, "--report", "../../../etc/passwd")
    assert code == C.EXIT_FAIL
    assert "逃逸" in err or "change 目录" in err


def test_report_outside_reviews_is_rejected(repo: Path, cli):
    """gate.md §3 的布局约定：报告必须在 reviews/ 下，否则 check 会报像误报的 stale。

    在 build 时就拦下，把这个坑变成一条清楚的即时错误。
    """
    _ready_to_build(repo, cli)
    write_artifact(repo, f"openspec/changes/{CHANGE}/my-report.md", "PASS\n")

    code, _, err = _build(cli, repo, "--report", "my-report.md")

    assert code == C.EXIT_FAIL
    assert "reviews/" in err


def test_missing_report_is_rejected(repo: Path, cli):
    _ready_to_build(repo, cli)
    (change_dir(repo, CHANGE) / REPORT).unlink()

    code, _, err = _build(cli, repo, "--report", "reviews/nope.md")

    assert code == C.EXIT_FAIL
    assert "报告" in err


def test_missing_tasks_is_rejected(repo: Path, cli):
    directory = _ready_to_build(repo, cli)
    (directory / "tasks.md").unlink()

    code, _, err = _build(cli, repo)

    assert code == C.EXIT_FAIL
    assert "tasks.md" in err


def test_unknown_change_is_rejected(repo: Path, cli):
    _ready_to_build(repo, cli)
    code, _, err = cli(
        "manifest", "build", "--root", str(repo), "--change", "no-such-change",
        "--stage", "building", "--report", REPORT,
        "--reviewer-run-id", "r", "--author-run-id", "a",
    )
    assert code == C.EXIT_FAIL
    assert "no-such-change" in err


def test_unonboarded_repo_is_rejected(repo: Path, cli):
    """没跑 init 的仓没有 policy，定位不到 changes_root——fail-closed。"""
    commit_content(repo, CHANGE)
    code, _, err = _build(cli, repo)
    assert code == C.EXIT_NOT_ONBOARDED
    assert "未接入" in err


# ---------------------------------------------------------------- 幂等 / 不 auto-commit


def test_rebuild_is_idempotent(repo: Path, cli):
    directory = _ready_to_build(repo, cli)
    manifest = directory / "reviews" / "building.manifest.json"

    assert _build(cli, repo)[0] == C.EXIT_PASS
    first = json.loads(manifest.read_text("utf-8"))
    assert _build(cli, repo)[0] == C.EXIT_PASS
    second = json.loads(manifest.read_text("utf-8"))

    assert first == second  # 同输入 → 同输出，覆盖同一个文件


def test_build_does_not_auto_commit(repo: Path, cli):
    _ready_to_build(repo, cli)
    before = head_sha(repo)

    assert _build(cli, repo)[0] == C.EXIT_PASS

    assert head_sha(repo) == before
    assert "?? openspec/changes/" in git(repo, "status", "--porcelain")
