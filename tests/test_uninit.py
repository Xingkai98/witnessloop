"""C 组：`witnessloop uninit`。

覆盖 C1 依 init-manifest 精确删除 / C2 文件被改过则拒绝删除并报 diff / C3 幂等。
"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C
from witnessloop.hashing import sha256_file

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


def _forge_manifest(repo: Path, entries: list[dict]) -> None:
    """伪造一份台账——manifest 是**提交进仓**的，agent/PR 可写。"""
    (repo / ".witnessloop").mkdir(parents=True, exist_ok=True)
    (repo / C.INIT_MANIFEST_PATH).write_text(
        json.dumps({"schema": C.SCHEMA_INIT_MANIFEST, "created_files": entries}),
        encoding="utf-8",
    )


def test_uninit_refuses_paths_outside_the_repo(repo: Path, cli):
    """回归 I-2：台账里 `path:"../secret.txt"` 曾被真删（exit 0）。"""
    outside = repo.parent / "secret.txt"
    outside.write_text("仓外的文件，不该被删\n", encoding="utf-8")
    _forge_manifest(
        repo, [{"path": "../secret.txt", "sha256": sha256_file(outside)}]
    )

    code, _, err = cli("uninit", "--root", str(repo))

    assert code == C.EXIT_FAIL
    assert outside.exists(), "uninit 删掉了仓根之外的文件"
    assert "越界" in err
    assert "整批未删除" in err


def test_uninit_refuses_absolute_paths_without_crashing(repo: Path, cli):
    """回归 I-2：绝对路径曾在 `path.relative_to(root)` 抛未捕获 ValueError。"""
    outside = repo.parent / "abs-secret.txt"
    outside.write_text("同样不该被删\n", encoding="utf-8")
    _forge_manifest(
        repo, [{"path": str(outside), "sha256": sha256_file(outside)}]
    )

    code, _, err = cli("uninit", "--root", str(repo))

    assert code == C.EXIT_FAIL, "绝对路径没有安全拒绝（可能崩溃或误删）"
    assert outside.exists()
    assert "越界" in err
    assert "Traceback" not in err


def test_uninit_refuses_escaping_entry_even_without_sha(repo: Path, cli):
    """没有 sha256 的越界条目同样必须拒绝（否则 expected 为空就跳过校验直接删）。"""
    outside = repo.parent / "no-sha.txt"
    outside.write_text("不该被删\n", encoding="utf-8")
    _forge_manifest(repo, [{"path": "../no-sha.txt"}])

    code, _, err = cli("uninit", "--root", str(repo))

    assert code == C.EXIT_FAIL
    assert outside.exists()
    assert "越界" in err


def test_uninit_still_removes_legitimate_files_with_forged_manifest(repo: Path, cli):
    """越界条目出现时整批拒绝，但正常台账仍照删（不是一律拒绝）。"""
    _init(repo, cli)
    entries = json.loads((repo / C.INIT_MANIFEST_PATH).read_text(encoding="utf-8"))[
        "created_files"
    ]
    (repo / C.INIT_MANIFEST_PATH).write_text(
        json.dumps(
            {
                "schema": C.SCHEMA_INIT_MANIFEST,
                "gate_ref": C.DEFAULT_GATE_REF,
                "created_files": entries,
            }
        ),
        encoding="utf-8",
    )
    code, _, err = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_PASS, err
    assert not (repo / C.INIT_MANIFEST_PATH).exists()


def test_uninit_skips_already_missing_file(repo: Path, cli):
    """文件已被人工删掉 ≠ 被改过：回滚其余文件，不报错。"""
    _init(repo, cli)
    (repo / C.POLICY_PATH).unlink()
    code, _, err = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_PASS, err
    assert not (repo / C.INIT_MANIFEST_PATH).exists()
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
