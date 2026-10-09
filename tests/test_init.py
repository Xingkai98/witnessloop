"""B 组：`witnessloop init`。

覆盖 B1 policy.json / B2 init-manifest.json / B3 caller workflow /
B4 幂等+只增不改+不 auto-commit / B5 --dry-run。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C
from witnessloop.hashing import sha256_file
from witnessloop.policy import INVARIANT_PROTECTED_PATHS

from conftest import commit_all, git


def test_init_creates_three_files(repo: Path, cli):
    code, out, _ = cli("init", "--root", str(repo))
    assert code == C.EXIT_PASS
    assert (repo / C.POLICY_PATH).is_file()
    assert (repo / C.INIT_MANIFEST_PATH).is_file()
    assert (repo / C.GATE_WORKFLOW_PATH).is_file()
    assert "已接入" in out


def test_policy_schema_has_three_sections(repo: Path, cli, read_json):
    cli("init", "--root", str(repo))
    policy = read_json(repo / C.POLICY_PATH)
    assert policy["schema"] == C.SCHEMA_POLICY
    # tasks.md B1 要求的 schema：protected_paths[] + required_artifacts[] + evidence
    assert isinstance(policy["protected_paths"], list) and policy["protected_paths"]
    assert policy["required_artifacts"] == list(C.DEFAULT_REQUIRED_ARTIFACTS)
    assert set(policy["evidence"]) >= {
        "review_manifest_glob",
        "events_file",
        "protected_write_event_types",
    }


def test_caller_workflow_is_thin_and_pins_gate_ref(repo: Path, cli):
    cli("init", "--root", str(repo))
    workflow = (repo / C.GATE_WORKFLOW_PATH).read_text(encoding="utf-8")
    assert f"uses: {C.DEFAULT_GATE_REF}" in workflow
    assert "pull_request" in workflow
    # 极薄：不内联门禁逻辑。
    assert "witnessloop check" not in workflow


def test_gate_ref_override(repo: Path, cli):
    cli("init", "--root", str(repo), "--gate-ref", "acme/wl/.github/workflows/gate.yml@v9")
    workflow = (repo / C.GATE_WORKFLOW_PATH).read_text(encoding="utf-8")
    assert "uses: acme/wl/.github/workflows/gate.yml@v9" in workflow


def test_init_manifest_ledger_and_base_ref(repo: Path, cli, read_json):
    before = git(repo, "rev-parse", "HEAD").strip()
    cli("init", "--root", str(repo))
    manifest = read_json(repo / C.INIT_MANIFEST_PATH)

    assert manifest["schema"] == C.SCHEMA_INIT_MANIFEST
    # B2：init 前 base ref
    assert manifest["base_ref"] == "main"
    assert manifest["base_sha"] == before

    by_path = {e["path"]: e for e in manifest["created_files"]}
    assert set(by_path) == {C.POLICY_PATH, C.GATE_WORKFLOW_PATH, C.INIT_MANIFEST_PATH}
    # 台账如实记录两个文件的 hash
    assert by_path[C.POLICY_PATH]["sha256"] == sha256_file(repo / C.POLICY_PATH)
    assert by_path[C.GATE_WORKFLOW_PATH]["sha256"] == sha256_file(
        repo / C.GATE_WORKFLOW_PATH
    )
    # 自引用条目
    assert by_path[C.INIT_MANIFEST_PATH]["self"] is True


def test_policy_protects_witnessloop_own_inputs_nominally(repo: Path, cli, read_json):
    cli("init", "--root", str(repo))
    policy = read_json(repo / C.POLICY_PATH)
    assert ".witnessloop/**" in policy["protected_paths"]
    # 不变集本身不写进 policy（它是不可移除的常量，不是 policy 的一部分）
    assert not (set(INVARIANT_PROTECTED_PATHS) & set(policy["protected_paths"]))


def test_init_does_not_auto_commit(repo: Path, cli):
    head_before = git(repo, "rev-parse", "HEAD").strip()
    cli("init", "--root", str(repo))
    assert git(repo, "rev-parse", "HEAD").strip() == head_before
    status = git(repo, "status", "--porcelain")
    assert "?? .witnessloop/" in status
    assert "?? .github/" in status


def test_init_is_idempotent(repo: Path, cli):
    cli("init", "--root", str(repo))
    snapshot = {
        p: (repo / p).read_bytes()
        for p in (C.POLICY_PATH, C.GATE_WORKFLOW_PATH, C.INIT_MANIFEST_PATH)
    }
    code, out, _ = cli("init", "--root", str(repo))
    assert code == C.EXIT_PASS
    assert "幂等" in out
    for p, content in snapshot.items():
        assert (repo / p).read_bytes() == content, f"{p} 被重复 init 改动了"


def test_init_add_only_conflict_reports_diff_and_refuses(repo: Path, cli):
    # 预先放一个内容不同的 policy.json —— 只增不改，必须拒绝覆盖。
    (repo / C.POLICY_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo / C.POLICY_PATH).write_text('{"schema": "custom"}\n', encoding="utf-8")

    code, _, err = cli("init", "--root", str(repo))
    assert code == C.EXIT_FAIL
    assert "冲突" in err
    assert "--- a/.witnessloop/policy.json" in err  # 报了 diff
    # 原文件未被覆盖
    assert (repo / C.POLICY_PATH).read_text(encoding="utf-8") == '{"schema": "custom"}\n'
    # 其他文件也不落盘（冲突时整体不写）
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
    assert not (repo / C.INIT_MANIFEST_PATH).exists()


def test_init_dry_run_writes_nothing(repo: Path, cli):
    code, out, _ = cli("init", "--root", str(repo), "--dry-run")
    assert code == C.EXIT_PASS
    assert "[dry-run]" in out
    assert C.POLICY_PATH in out
    assert not (repo / C.POLICY_PATH).exists()
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
    assert not (repo / C.INIT_MANIFEST_PATH).exists()
    assert git(repo, "status", "--porcelain").strip() == ""


def test_init_after_drifted_file_is_loud(repo: Path, cli):
    cli("init", "--root", str(repo))
    (repo / C.POLICY_PATH).write_text('{"schema": "tampered"}\n', encoding="utf-8")
    code, _, err = cli("init", "--root", str(repo))
    assert code == C.EXIT_FAIL
    assert "被改动过" in err
