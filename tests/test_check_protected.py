"""D5：受保护路径的写入必须带结构化解释事件（reason/approved_by 非空）。"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all, git
from helpers import (
    check,
    commit_content,
    commit_evidence,
    write_change,
    write_event,
    write_review,
)

SPEC = "openspec/specs/retry/spec.md"


def _write_spec(repo: Path, body: str = "# canonical spec: retry\n") -> None:
    path = repo / SPEC
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _full_change(repo: Path, change_id: str) -> None:
    write_change(repo, change_id)
    write_review(repo, change_id)


def test_protected_write_without_event_is_rejected(gated: Path, cli):
    _write_spec(gated)
    commit_all(gated, "直接改受保护 spec，没有解释")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err
    assert SPEC in err


def test_protected_write_with_valid_event_passes(gated: Path, cli):
    """也就是 F2 负例 (a)：手写一行放行事件 → 门禁**不拦**（防漂移不防伪造）。"""
    commit_content(gated, "sync-retry-spec", spec_writes=((SPEC, "# canonical\n"),))
    commit_evidence(gated, "sync-retry-spec", events=(SPEC,))

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_event_with_blank_reason_does_not_count(gated: Path, cli):
    _full_change(gated, "c")
    write_event(gated, "c", SPEC, reason="   ")
    _write_spec(gated)
    commit_all(gated, "reason 是空白")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err


def test_event_with_blank_approver_does_not_count(gated: Path, cli):
    _full_change(gated, "c")
    write_event(gated, "c", SPEC, approved_by="")
    _write_spec(gated)
    commit_all(gated, "approved_by 是空的")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err


def test_event_for_a_different_path_does_not_count(gated: Path, cli):
    _full_change(gated, "c")
    write_event(gated, "c", "openspec/specs/other/spec.md")
    _write_spec(gated)
    commit_all(gated, "事件指向别处")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err


def test_event_with_unknown_type_does_not_count(gated: Path, cli):
    _full_change(gated, "c")
    write_event(gated, "c", SPEC, event_type="i_am_a_waiver")
    _write_spec(gated)
    commit_all(gated, "拿别的 event_type 蒙混")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err


def test_deleting_a_protected_spec_needs_an_event(repo: Path, cli):
    _write_spec(repo, "# baseline spec\n")
    cli("init", "--root", str(repo))
    commit_all(repo, "main：已有受保护 spec")
    git(repo, "checkout", "-q", "-b", "feature")

    (repo / SPEC).unlink()
    commit_all(repo, "删掉受保护 spec")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err


def test_renaming_a_protected_file_out_of_the_area_is_rejected(repo: Path, cli):
    """改名外逃：`git mv` 受保护文件到保护区外 == 删除，必须解释。

    回归 I-1：`_protected_writes` 原先只看新路径，改名后新路径不受保护 → 放行。
    注意 `git diff --name-status` 对改名给 `R<score> old new`，old_path 才是关键。
    """
    _write_spec(repo, "# baseline spec\n")
    cli("init", "--root", str(repo))
    commit_all(repo, "main：已有受保护 spec")
    git(repo, "checkout", "-q", "-b", "feature")

    (repo / "src").mkdir()
    git(repo, "mv", SPEC, "src/moved-spec.md")
    commit_all(repo, "改名外逃")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL, "改名把受保护文件移出保护区却被放行"
    assert SPEC in err
    assert "受保护路径被写入" in err


def test_renaming_with_an_event_is_allowed(repo: Path, cli):
    """给了针对**旧路径**的解释事件，改名外逃应该放行。"""
    _write_spec(repo, "# baseline spec\n")
    cli("init", "--root", str(repo))
    commit_all(repo, "main：已有受保护 spec")
    git(repo, "checkout", "-q", "-b", "feature")

    write_change(repo, "move-retry-spec")
    (repo / "src").mkdir()
    git(repo, "mv", SPEC, "src/moved-spec.md")
    commit_all(repo, "内容：把 spec 改名搬走")
    write_review(repo, "move-retry-spec")
    write_event(repo, "move-retry-spec", SPEC)  # 解释的是**旧路径**
    commit_all(repo, "证据")

    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, err


def test_writes_outside_protected_paths_need_no_event(gated: Path, cli):
    commit_content(gated, "c", spec_writes=(("src/app.py", "x = 1\n"),))
    commit_evidence(gated, "c")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_repo_policy_can_add_protected_paths(repo: Path, cli, read_json):
    """repo-agnostic 参数化：policy 可加自己的受保护路径。"""
    cli("init", "--root", str(repo))
    policy_path = repo / C.POLICY_PATH
    doc = read_json(policy_path)
    doc["protected_paths"].append("infra/**")
    policy_path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    commit_all(repo, "加一条自己的受保护路径")
    git(repo, "checkout", "-q", "-b", "feature")

    (repo / "infra").mkdir()
    (repo / "infra" / "main.tf").write_text("# infra\n", encoding="utf-8")
    commit_all(repo, "改 infra 却没有解释")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "infra/main.tf" in err
