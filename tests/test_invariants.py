"""D6：不变集——witnessloop 自身的输入恒受保护，repo policy 移除不掉。

这是「agent 改一行 policy 就能让门禁对自己失效」的唯一防线。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from witnessloop import constants as C
from witnessloop.policy import INVARIANT_PROTECTED_PATHS

from conftest import commit_all, git
from helpers import (
    change_dir,
    check,
    commit_content,
    commit_evidence,
    write_change,
    write_event,
    write_review,
)


def test_invariant_set_is_capped():
    """~5 条常量封顶（grill Q3 / 对抗验证要封顶，防止「只为堆保护」）。"""
    assert len(INVARIANT_PROTECTED_PATHS) <= 5
    assert C.POLICY_PATH in INVARIANT_PROTECTED_PATHS
    assert C.INIT_MANIFEST_PATH in INVARIANT_PROTECTED_PATHS


def _emptied_policy(repo: Path, read_json) -> None:
    """把 repo policy 的受保护路径清空——模拟「agent 想关掉门禁」。"""
    doc = read_json(repo / C.POLICY_PATH)
    doc["protected_paths"] = []
    (repo / C.POLICY_PATH).write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_policy_file_stays_protected_even_if_repo_policy_forgets(repo, cli, read_json):
    cli("init", "--root", str(repo))
    _emptied_policy(repo, read_json)
    commit_all(repo, "main：清空受保护路径")
    git(repo, "checkout", "-q", "-b", "feature")

    policy_path = repo / C.POLICY_PATH
    doc = read_json(policy_path)
    doc["changes_root"] = "somewhere/else"
    policy_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    commit_all(repo, "改 policy 却没解释")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert C.POLICY_PATH in err
    assert "受保护路径被写入" in err


def test_review_manifest_stays_protected_even_if_repo_policy_forgets(
    repo, cli, read_json
):
    cli("init", "--root", str(repo))
    _emptied_policy(repo, read_json)
    write_change(repo, "add-x")
    write_review(repo, "add-x")
    commit_all(repo, "main：一个完整 change")
    git(repo, "checkout", "-q", "-b", "feature")

    manifest = change_dir(repo, "add-x") / "reviews" / "building.manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    doc["diff_hash"] = "事后偷偷改的"
    manifest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    commit_all(repo, "偷偷改证据")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "building.manifest.json" in err
    assert "受保护路径被写入" in err


def test_events_file_stays_protected_even_if_repo_policy_forgets(repo, cli, read_json):
    cli("init", "--root", str(repo))
    _emptied_policy(repo, read_json)
    write_change(repo, "add-x")
    write_review(repo, "add-x")
    write_event(repo, "add-x", "openspec/specs/whatever.md")
    commit_all(repo, "main：有事件文件的 change")
    git(repo, "checkout", "-q", "-b", "feature")

    events_file = change_dir(repo, "add-x") / C.DEFAULT_EVENTS_FILE
    events_file.write_text(
        events_file.read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    commit_all(repo, "偷偷动事件文件")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert C.DEFAULT_EVENTS_FILE in err


def test_adding_new_evidence_needs_no_event(repo, cli, read_json):
    """不变集只对「修改/删除」要解释——新增证据本体是正常工作流。"""
    cli("init", "--root", str(repo))
    _emptied_policy(repo, read_json)
    commit_all(repo, "main：清空受保护路径")
    git(repo, "checkout", "-q", "-b", "feature")

    commit_content(repo, "add-x")
    commit_evidence(repo, "add-x")  # 新增 manifest，不需要解释事件

    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, err


@pytest.mark.parametrize(
    "path,expected",
    [
        # 不变集只覆盖 witnessloop 自身输入；openspec/specs/** 是 repo policy
        # 的默认保护项，不是不变集。
        (".witnessloop/policy.json", True),
        (".witnessloop/init-manifest.json", True),
        ("openspec/changes/x/reviews/b.manifest.json", True),
        ("openspec/changes/x/workflow-events.jsonl", True),
        ("openspec/specs/a/spec.md", False),
        ("src/app.py", False),
    ],
)
def test_matching_semantics(path, expected):
    from witnessloop import paths

    assert paths.matches_any(path, INVARIANT_PROTECTED_PATHS) is expected
