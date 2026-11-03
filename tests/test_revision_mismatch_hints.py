"""issue #46：revision 不匹配要区分「后代」与「旁支 / 不可达」并给可执行提示。

旧实现只报「head_sha=… 不是本次被检 revision … 的祖先——审阅的是别的 revision」，
不告诉使用者下一步该跑什么。新实现：

* 证据 revision 是**后代** ⇒ 提示改用包含它的区间（`--base … --head HEAD` /
  `--head <证据 sha>`）；
* 旁支 / 不可达 ⇒ 提示在交付 revision 上重跑 `manifest build`，并附复核命令。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all, git
from helpers import commit_content, commit_evidence, write_artifact


def test_descendant_evidence_suggests_an_interval_that_contains_it(gated: Path, cli):
    """证据产生在更晚的 revision（C2）上，而本次只检查到 C1。"""
    content = commit_content(gated, "add-x")
    write_artifact(gated, "src/app.py", "x = 1\n")
    later = commit_all(gated, "内容：第二笔")
    commit_evidence(gated, "add-x", head_sha=later)

    code, _out, err = cli(
        "check", "--root", str(gated), "--base", "main", "--head", content
    )

    assert code == C.EXIT_FAIL
    assert "祖先" in err
    assert "后代" in err
    assert "witnessloop check --base main --head HEAD" in err
    assert f"witnessloop check --base main --head {later}" in err
    assert "manifest build" not in err, "后代情形不该让人重建证据；区间选对即可"


def test_side_branch_evidence_suggests_rebuilding_on_the_delivered_revision(
    gated: Path, cli
):
    """manifest 的 head_sha 指向一条与交付历史互不可达的旁支提交。"""
    commit_content(gated, "add-x")
    git(gated, "checkout", "-q", "main")
    write_artifact(gated, "unrelated.txt", "x\n")
    unrelated = commit_all(gated, "主干上的无关提交")
    git(gated, "checkout", "-q", "feature")
    commit_evidence(gated, "add-x", head_sha=unrelated)

    code, _out, err = cli(
        "check", "--root", str(gated), "--base", "main", "--head", "HEAD"
    )

    assert code == C.EXIT_FAIL
    assert "祖先" in err
    assert "旁支" in err or "不可达" in err
    assert "manifest build" in err
    assert "--change add-x" in err
    assert "--stage building" in err
    assert "--report reviews/building-review.md" in err
    assert "witnessloop check --base main --head HEAD" in err
