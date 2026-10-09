"""D2：change 目录契约（OpenSpec 形状：proposal/design/tasks/specs + reviews）。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from witnessloop import constants as C

from conftest import commit_all, git
from helpers import (
    change_dir,
    check,
    commit_content,
    commit_evidence,
    write_change,
    write_review,
)


def test_complete_change_passes(gated: Path, cli):
    commit_content(gated, "add-retry-policy")
    commit_evidence(gated, "add-retry-policy")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err
    assert "通过" in out


@pytest.mark.parametrize("missing", ["proposal.md", "design.md", "tasks.md"])
def test_missing_artifact_is_reported(gated: Path, cli, missing):
    kept = tuple(a for a in ("proposal.md", "design.md", "tasks.md") if a != missing)
    commit_content(gated, "add-x", artifacts=kept)
    commit_evidence(gated, "add-x")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert f"缺少必需件 {missing}" in err


def test_missing_specs_dir_is_reported(gated: Path, cli):
    commit_content(gated, "add-x", specs=False)
    commit_evidence(gated, "add-x")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "缺少必需件 specs" in err


def test_missing_reviews_dir_is_reported(gated: Path, cli):
    commit_content(gated, "add-x", reviews=False)

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "缺少必需件 reviews" in err


def test_touched_but_absent_change_dir_is_reported(repo: Path, cli):
    """base 树里有 change 目录，head 把它删了 → 目录不存在，报错。"""
    cli("init", "--root", str(repo))
    write_change(repo, "add-x")
    write_review(repo, "add-x")
    commit_all(repo, "main 上一个完整的 change")

    git(repo, "checkout", "-q", "-b", "feature")
    shutil.rmtree(change_dir(repo, "add-x"))
    commit_all(repo, "删掉 change 目录")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "change 目录不存在" in err


def test_change_outside_changes_root_is_ignored(gated: Path, cli):
    """非 change 目录的文件不参与**契约**校验。

    用 `docs/` 而不是 `src/`：后者命中 `require_change_for`，会被另一条规则
    （改了代码必须挂 change）拦下，掩盖本条要验证的「契约校验与它无关」。
    """
    (gated / "docs").mkdir(exist_ok=True)
    (gated / "docs" / "notes.md").write_text("# 笔记\n", encoding="utf-8")
    commit_all(gated, "普通文档改动")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err
    assert "0 个 change 目录" in out
