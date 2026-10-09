"""C 组：`witnessloop uninit`。

覆盖 C1 依 init-manifest 精确删除 / C2 文件被改过则拒绝删除并报 diff / C3 幂等。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import git


def _init(repo: Path, cli) -> None:
    code, _, err = cli("init", "--root", str(repo))
    assert code == C.EXIT_PASS, err


def test_uninit_removes_exactly_what_init_created(repo: Path, cli):
    _init(repo, cli)
    assert (repo / ".witnessloop").is_dir()
    assert (repo / ".github/workflows").is_dir()

    code, out, _ = cli("uninit", "--root", str(repo))

    assert code == C.EXIT_PASS
    assert not (repo / C.POLICY_PATH).exists()
    assert not (repo / C.INIT_MANIFEST_PATH).exists()
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
    # 空目录被收干净
    assert not (repo / ".witnessloop").exists()
    assert not (repo / ".github").exists()
    assert C.POLICY_PATH in out


def test_uninit_round_trip_leaves_repo_clean(repo: Path, cli):
    """F5 的前半：init → uninit 往返后工作树回到 init 前。"""
    before = git(repo, "status", "--porcelain")
    _init(repo, cli)
    assert git(repo, "status", "--porcelain") != before  # init 确实动了树

    code, _, _ = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_PASS
    assert git(repo, "status", "--porcelain") == before


def test_uninit_is_idempotent(repo: Path, cli):
    _init(repo, cli)
    assert cli("uninit", "--root", str(repo))[0] == C.EXIT_PASS
    code, out, _ = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_PASS  # 重复 uninit 安全
    assert "未接入" in out or "已回滚" in out


def test_uninit_never_ran_is_a_noop(repo: Path, cli):
    code, _, _ = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_PASS
    assert git(repo, "status", "--porcelain").strip() == ""


def test_uninit_refuses_when_file_was_modified(repo: Path, cli):
    _init(repo, cli)
    (repo / C.POLICY_PATH).write_text('{"schema": "custom-tuned"}\n', encoding="utf-8")

    code, _, err = cli("uninit", "--root", str(repo))

    assert code == C.EXIT_FAIL
    assert "被改动过" in err
    assert "拒绝删除" in err
    assert "--- a/.witnessloop/policy.json" in err  # 报 diff
    # 拒绝时整批都不删（原子回滚，避免半删状态）
    assert (repo / C.POLICY_PATH).exists()
    assert (repo / C.INIT_MANIFEST_PATH).exists()
    assert (repo / C.GATE_WORKFLOW_PATH).exists()


def test_uninit_refuses_when_workflow_was_modified(repo: Path, cli):
    _init(repo, cli)
    (repo / C.GATE_WORKFLOW_PATH).write_text("# 手改过了\n", encoding="utf-8")
    code, _, err = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_FAIL
    assert C.GATE_WORKFLOW_PATH in err


def test_uninit_skips_already_missing_file(repo: Path, cli):
    """文件已被人工删掉 ≠ 被改过：回滚其余文件，不报错。"""
    _init(repo, cli)
    (repo / C.POLICY_PATH).unlink()
    code, _, err = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_PASS, err
    assert not (repo / C.INIT_MANIFEST_PATH).exists()
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
