"""D1：无 policy 时必须报「未接入」并非零退出——不得静默通过（F4）。"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all
from helpers import check, commit_content, commit_evidence, write_change


def test_check_without_policy_is_not_onboarded(repo: Path, cli):
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    commit_all(repo, "加代码，没接入")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_NOT_ONBOARDED
    assert code != 0  # fail-closed：不静默通过
    assert "未接入" in err
    assert C.POLICY_PATH in err


def test_check_with_broken_policy_is_loud(repo: Path, cli):
    (repo / C.POLICY_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo / C.POLICY_PATH).write_text("{ not json", encoding="utf-8")
    commit_all(repo, "坏 policy")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "policy 非法" in err


def test_check_with_unresolvable_base_is_fail_closed(gated: Path, cli):
    write_change(gated, "add-x")
    commit_all(gated, "change")
    code, _, err = cli(
        "check", "--root", str(gated), "--base", "no-such-ref", "--head", "HEAD"
    )
    assert code == C.EXIT_FAIL
    assert "base ref" in err


def test_bootstrap_pr_adding_init_files_passes(repo: Path, cli):
    """接入 PR 自己不能被自己的门禁拦下（受保护写入的鸡生蛋）。"""
    code, _, err = cli("init", "--root", str(repo))
    assert code == C.EXIT_PASS, err
    commit_all(repo, "接入 witnessloop")

    code, out, err = cli("check", "--root", str(repo), "--base", "HEAD~1", "--head", "HEAD")
    assert code == C.EXIT_PASS, err


def test_modifying_policy_file_needs_an_explanation_event(gated: Path, cli):
    """豁免只对「新增」生效：改动 .witnessloop/** 仍需解释事件。"""
    policy_path = gated / C.POLICY_PATH
    policy_path.write_text(
        policy_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    commit_all(gated, "偷改 policy")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert C.POLICY_PATH in err


def test_git_refs_default_from_env(gated: Path, cli, monkeypatch):
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    monkeypatch.setenv("WITNESSLOOP_BASE_REF", "main")
    code, out, _ = cli("check", "--root", str(gated))
    assert code == C.EXIT_PASS
    assert "main...HEAD" in out
