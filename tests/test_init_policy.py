"""B6：`witnessloop init --policy <file>`（change dogfood-bootstrap / D2）。

覆盖 tasks A1–A6：指定内容落盘 + 台账一致 / 幂等 / `uninit` 往返 /
非法输入拒且不写 / `--dry-run` / **已接入后给不同 policy 必须报冲突（R2）**。
"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C
from witnessloop import policy as policy_mod
from witnessloop.hashing import sha256_file

from conftest import git

# 与出厂默认的差异点：require_change_for 多出 templates/** 与 plugin/**（本仓自举所需）。
CUSTOM_DOC = {
    "schema": C.SCHEMA_POLICY,
    "changes_root": "openspec/changes",
    "protected_paths": ["openspec/specs/**", ".witnessloop/**"],
    "require_change_for": ["src/**", "templates/**", "plugin/**"],
    "required_artifacts": list(C.DEFAULT_REQUIRED_ARTIFACTS),
    "evidence": {
        "review_manifest_glob": "reviews/*.manifest.json",
        "events_file": "workflow-events.jsonl",
        "protected_write_event_types": ["protected_path_write"],
    },
}


def _seed(tmp_path: Path, doc) -> Path:
    p = tmp_path / "seed-policy.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def test_init_policy_uses_given_content(repo: Path, cli, read_json, tmp_path):
    seed = _seed(tmp_path, CUSTOM_DOC)
    code, _, err = cli("init", "--root", str(repo), "--policy", str(seed))
    assert code == C.EXIT_PASS, err
    assert read_json(repo / C.POLICY_PATH) == CUSTOM_DOC


def test_init_policy_ledger_hash_matches(repo: Path, cli, read_json, tmp_path):
    seed = _seed(tmp_path, CUSTOM_DOC)
    cli("init", "--root", str(repo), "--policy", str(seed))
    manifest = read_json(repo / C.INIT_MANIFEST_PATH)
    by_path = {e["path"]: e for e in manifest["created_files"]}
    assert by_path[C.POLICY_PATH]["sha256"] == sha256_file(repo / C.POLICY_PATH)


def test_init_policy_idempotent(repo: Path, cli, tmp_path):
    seed = _seed(tmp_path, CUSTOM_DOC)
    cli("init", "--root", str(repo), "--policy", str(seed))
    snapshot = (repo / C.POLICY_PATH).read_bytes()
    code, out, _ = cli("init", "--root", str(repo), "--policy", str(seed))
    assert code == C.EXIT_PASS
    assert "幂等" in out
    assert (repo / C.POLICY_PATH).read_bytes() == snapshot


def test_uninit_after_policy_round_trip(repo: Path, cli, tmp_path):
    seed = _seed(tmp_path, CUSTOM_DOC)
    cli("init", "--root", str(repo), "--policy", str(seed))
    code, _, err = cli("uninit", "--root", str(repo))
    assert code == C.EXIT_PASS, err
    assert not (repo / C.POLICY_PATH).exists()
    assert not (repo / C.INIT_MANIFEST_PATH).exists()
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()


def test_init_policy_missing_file_writes_nothing(repo: Path, cli, tmp_path):
    code, _, _ = cli(
        "init", "--root", str(repo), "--policy", str(tmp_path / "nope.json")
    )
    assert code == C.EXIT_FAIL
    assert not (repo / C.POLICY_PATH).exists()
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
    assert not (repo / C.INIT_MANIFEST_PATH).exists()


def test_init_policy_invalid_json_writes_nothing(repo: Path, cli, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    code, _, _ = cli("init", "--root", str(repo), "--policy", str(bad))
    assert code == C.EXIT_FAIL
    assert not (repo / C.POLICY_PATH).exists()


def test_init_policy_non_object_writes_nothing(repo: Path, cli, tmp_path):
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")
    code, _, _ = cli("init", "--root", str(repo), "--policy", str(arr))
    assert code == C.EXIT_FAIL
    assert not (repo / C.POLICY_PATH).exists()


def test_init_policy_outside_repo_is_allowed(repo: Path, cli, read_json, tmp_path):
    # Q5：seed 不入库 ⇒ --policy 允许指向仓外路径（tmp_path 就在仓外）。
    seed = _seed(tmp_path, CUSTOM_DOC)
    code, _, err = cli("init", "--root", str(repo), "--policy", str(seed))
    assert code == C.EXIT_PASS, err
    assert read_json(repo / C.POLICY_PATH) == CUSTOM_DOC


def test_init_policy_dry_run_writes_nothing(repo: Path, cli, tmp_path):
    seed = _seed(tmp_path, CUSTOM_DOC)
    code, out, _ = cli(
        "init", "--root", str(repo), "--policy", str(seed), "--dry-run"
    )
    assert code == C.EXIT_PASS
    assert "[dry-run]" in out
    assert not (repo / C.POLICY_PATH).exists()
    assert git(repo, "status", "--porcelain").strip() == ""


def test_init_policy_after_initialized_with_different_policy_conflicts(
    repo: Path, cli, tmp_path
):
    # R2：已接入后再给**不同** policy 必须报冲突，**不得**静默 no-op。
    cli("init", "--root", str(repo))  # 先落出厂默认 policy
    seed = _seed(tmp_path, CUSTOM_DOC)  # 与默认不同
    code, _, err = cli("init", "--root", str(repo), "--policy", str(seed))
    assert code == C.EXIT_FAIL
    assert "冲突" in err
    # 原 policy 未被改动，仍是出厂默认。
    assert json.loads((repo / C.POLICY_PATH).read_text(encoding="utf-8")) == (
        policy_mod.default_policy_doc()
    )


def test_init_policy_after_initialized_same_policy_is_idempotent(
    repo: Path, cli, tmp_path
):
    # 对照：同 policy 重跑仍是「幂等」，不误报冲突。
    seed = _seed(tmp_path, CUSTOM_DOC)
    cli("init", "--root", str(repo), "--policy", str(seed))
    code, out, _ = cli("init", "--root", str(repo), "--policy", str(seed))
    assert code == C.EXIT_PASS
    assert "幂等" in out


def test_rerun_without_gate_ref_after_custom_is_idempotent(repo: Path, cli, read_json):
    # 回归审阅 I3：曾以非默认 --gate-ref 接入的仓，之后**不带**该 flag 重跑 init
    # 不得误判「冲突」——gate_ref 缺省应沿用台账里的值。
    custom = "acme/wl/.github/workflows/gate.yml@v9"
    cli("init", "--root", str(repo), "--gate-ref", custom)
    code, out, _ = cli("init", "--root", str(repo))
    assert code == C.EXIT_PASS
    assert "幂等" in out
    assert read_json(repo / C.INIT_MANIFEST_PATH)["gate_ref"] == custom


def test_rerun_with_explicit_different_gate_ref_rewrites_the_caller(repo: Path, cli):
    """⚠️ **语义已反转**（change `gate-ref-pins-package` / Q2 裁定 (a)）。

    原先断言「显式传**不同**的 --gate-ref ⇒ 冲突退 1」（与 `--policy` 同语义）。
    现在 `--gate-ref` 是**唯一**的换 ref 入口，而「只增不改」会让它永远撞冲突 ⇒
    接入方没有可用的升级动作。裁定改为：**对已接入的仓**，显式 `--gate-ref` ⇒
    重写 caller **+ 同步台账**（`sha256` 与 `gate_ref`），其余文件照旧只增不改。

    ⚠️ `--policy` 那条**没有**反转（`test_init_policy_after_initialized_with_different_policy_conflicts`
    仍断言冲突）：policy 是**接入方自己的**内容，caller 是**工具生成的产物**——
    前者不能让工具擅自覆盖，后者必须能跟着 ref 走。两条都保留，正是这个分别的钉子。

    作用域/台账同步/幂等/uninit 的完整覆盖在 `tests/test_init_gate_ref.py`。
    """
    cli("init", "--root", str(repo))
    new_ref = "acme/wl/.github/workflows/gate.yml@v9"

    code, _, err = cli("init", "--root", str(repo), "--gate-ref", new_ref)

    assert code == C.EXIT_PASS, err
    assert f"uses: {new_ref}" in (repo / C.GATE_WORKFLOW_PATH).read_text(encoding="utf-8")
