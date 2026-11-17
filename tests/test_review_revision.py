"""P1：revision 锚点（GitRevision / DigestRevision / mode auto）。"""

from __future__ import annotations

import pytest

from witnessloop.review import revision as R

from conftest import commit_all, git
from helpers import write_artifact


def test_detect_mode_is_git_when_repo_exists(repo):
    assert R.detect_mode(repo) == "git"


def test_detect_mode_is_digest_without_git(tmp_path):
    (tmp_path / "a.txt").write_text("x\n", encoding="utf-8")
    assert R.detect_mode(tmp_path) == "digest"


def test_resolve_git_revision_is_head_sha(repo):
    rev = R.resolve_revision(repo)
    assert rev.mode == "git"
    assert rev.value == git(repo, "rev-parse", "HEAD").strip()


def test_resolve_digest_revision_without_git(tmp_path):
    (tmp_path / "a.txt").write_text("x\n", encoding="utf-8")
    rev = R.resolve_revision(tmp_path)
    assert rev.mode == "digest"
    assert len(rev.value) == 64


def test_resolve_explicit_git_in_git_repo(repo):
    rev = R.resolve_revision(repo, mode="git")
    assert rev.mode == "git"


def test_resolve_explicit_digest_in_git_repo(repo):
    """显式 ``--mode digest`` 时，即使有 .git 也走 Digest。"""
    rev = R.resolve_revision(repo, mode="digest")
    assert rev.mode == "digest"
    assert len(rev.value) == 64


def test_resolve_unknown_mode_is_rejected(repo):
    with pytest.raises(ValueError):
        R.resolve_revision(repo, mode="bogus")


def test_git_ancestry(repo):
    first = git(repo, "rev-parse", "HEAD").strip()
    write_artifact(repo, "src/x.py", "x = 1\n")
    second = commit_all(repo, "第二个提交")
    ancestor = R.Revision("git", first)
    descendant = R.Revision("git", second)
    assert ancestor.is_ancestor(repo, descendant)
    assert not descendant.is_ancestor(repo, ancestor)
    assert descendant.is_ancestor(repo, descendant)  # 相等也算


def test_digest_ignores_output_dir(tmp_path):
    """Digest 必须排除自己的输出目录——否则每写一轮 manifest 就改掉自己的锚。"""
    from witnessloop import constants as C

    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    before = R.worktree_digest(tmp_path)
    out = tmp_path / C.REVIEW_OUTPUT_DIR / "rounds"
    out.mkdir(parents=True)
    (out / "round-0001.json").write_text('{"x": 1}\n', encoding="utf-8")
    after = R.worktree_digest(tmp_path)
    assert before == after


def test_digest_ignores_git_dir(tmp_path):
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    before = R.worktree_digest(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    assert R.worktree_digest(tmp_path) == before


def test_digest_changes_with_content(tmp_path):
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    before = R.worktree_digest(tmp_path)
    (tmp_path / "a.txt").write_text("world\n", encoding="utf-8")
    assert R.worktree_digest(tmp_path) != before
