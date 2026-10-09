"""② 归档豁免：把 change 从 active move 进 `archive/` 不该要人手写解释事件。

OpenSpec 的归档就是一次 `git mv`。归档后的 change 不再是「活着的证据」，
但它的 `reviews/*.manifest.json` 在不变集里，改名会被判成「修改受保护路径」，
于是每次归档都得手写一条解释事件。

豁免必须**窄**：只有「active → archive 的纯改名」才算归档；
删/改证据文件仍要解释。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all, git
from helpers import change_dir, check, commit_content, commit_evidence

CHANGE = "add-retry"
ARCHIVE_REL = "openspec/changes/archive"


def _repo_with_a_complete_change(repo: Path, cli) -> Path:
    """在 main 上放一个完整、有证据的 change，然后切到 feature 分支。"""
    cli("init", "--root", str(repo))
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE)
    git(repo, "checkout", "-q", "-b", "archive-it")
    return repo


def _archive(repo: Path) -> None:
    (repo / ARCHIVE_REL).mkdir(parents=True, exist_ok=True)
    git(repo, "mv", f"openspec/changes/{CHANGE}", f"{ARCHIVE_REL}/{CHANGE}")
    commit_all(repo, "归档 change")


def test_archiving_a_change_passes_without_events(repo: Path, cli):
    _repo_with_a_complete_change(repo, cli)
    _archive(repo)

    code, out, err = check(repo, cli)

    assert code == C.EXIT_PASS, err
    assert "受保护路径被写入" not in err


def test_archived_change_is_no_longer_validated_as_active(repo: Path, cli):
    """归档后 active 目录不存在，不能因此报「change 目录不存在」。"""
    _repo_with_a_complete_change(repo, cli)
    _archive(repo)

    code, _, err = check(repo, cli)
    assert "change 目录不存在" not in err
    assert "缺少必需件" not in err
    assert code == C.EXIT_PASS, err


def test_deleting_an_evidence_file_still_needs_an_event(repo: Path, cli):
    """豁免面要窄：直接删掉 manifest 仍须解释事件。"""
    _repo_with_a_complete_change(repo, cli)
    (change_dir(repo, CHANGE) / "reviews" / "building.manifest.json").unlink()
    commit_all(repo, "把证据删了")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err


def test_modifying_a_file_inside_archive_still_needs_an_event(repo: Path, cli):
    """archive/ 不是法外之地：里面的 manifest 被改，仍须解释事件。"""
    _repo_with_a_complete_change(repo, cli)
    _archive(repo)

    archived = repo / ARCHIVE_REL / CHANGE / "reviews" / "building.manifest.json"
    archived.write_text(
        archived.read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    commit_all(repo, "偷改归档里的 manifest")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err


def test_renaming_within_the_active_change_still_needs_events(repo: Path, cli):
    """active 目录内的改名不是归档，仍须解释事件（改名 manifest 尤其如此）。"""
    _repo_with_a_complete_change(repo, cli)
    reviews = change_dir(repo, CHANGE) / "reviews"
    git(
        repo,
        "mv",
        str(reviews / "building.manifest.json"),
        str(reviews / "other.manifest.json"),
    )
    commit_all(repo, "active 里改名 manifest")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err


def test_archiving_a_protected_spec_still_needs_an_event(repo: Path, cli):
    """把受保护 spec 挪进 archive 不是「归档 change」，不在豁免范围内。"""
    cli("init", "--root", str(repo))
    (repo / "openspec/specs/retry").mkdir(parents=True, exist_ok=True)
    (repo / "openspec/specs/retry/spec.md").write_text("# spec\n", encoding="utf-8")
    commit_all(repo, "main 上有受保护 spec")
    git(repo, "checkout", "-q", "-b", "move-spec")

    (repo / ARCHIVE_REL).mkdir(parents=True, exist_ok=True)
    git(repo, "mv", "openspec/specs/retry/spec.md", f"{ARCHIVE_REL}/spec.md")
    commit_all(repo, "把 spec 挪进 archive")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "openspec/specs/retry/spec.md" in err
