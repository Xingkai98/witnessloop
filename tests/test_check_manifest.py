"""D3：review manifest 存在且 hash 绑定；D4：reviewer_run_id != author_run_id。"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C
from witnessloop.hashing import sha256_tree

from conftest import commit_all
from helpers import check, change_dir, write_change, write_review


def _stage(gated: Path, change_id: str = "add-x") -> Path:
    write_change(gated, change_id)
    return change_dir(gated, change_id)


def test_missing_manifest_is_reported(gated: Path, cli):
    _stage(gated)
    commit_all(gated, "只有报告框，没有证据")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "缺少 review manifest" in err


def test_missing_required_field_is_reported(gated: Path, cli):
    directory = _stage(gated)
    write_review(gated, "add-x")
    manifest_path = directory / "reviews" / "building.manifest.json"
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    del doc["base_sha"]
    manifest_path.write_text(json.dumps(doc), encoding="utf-8")
    commit_all(gated, "缺 base_sha")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "缺字段" in err and "base_sha" in err


def test_reviewer_equal_to_author_is_rejected(gated: Path, cli):
    """D4：同一个 run 既写又审 → 必须拦下（挡「忘了另开 run」）。"""
    _stage(gated)
    write_review(
        gated, "add-x", reviewer_run_id="same-run", author_run_id="same-run"
    )
    commit_all(gated, "自审自过")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "reviewer_run_id == author_run_id" in err


def test_report_hash_mismatch_is_rejected(gated: Path, cli):
    _stage(gated)
    write_review(gated, "add-x")
    # 报告写完后再改内容 —— manifest 的 report_hash 就对不上了。
    (change_dir(gated, "add-x") / "reviews" / "building-review.md").write_text(
        "PASS（事后改的）\n", encoding="utf-8"
    )
    commit_all(gated, "漂移的报告")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "report_hash 不匹配" in err


def test_tasks_hash_drift_is_rejected(gated: Path, cli):
    """F3 的同构负例：证据与 artifact 漂移 → 报错而非双绿。"""
    _stage(gated)
    write_review(gated, "add-x")
    (change_dir(gated, "add-x") / "tasks.md").write_text(
        "# tasks\n\n- [x] 审阅后又改了 tasks\n", encoding="utf-8"
    )
    commit_all(gated, "tasks 漂移")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "tasks_hash 不匹配" in err


def test_spec_hash_drift_is_rejected(gated: Path, cli):
    _stage(gated)
    write_review(gated, "add-x")
    (change_dir(gated, "add-x") / "specs" / "retry" / "spec.md").write_text(
        "# spec: retry（改了）\n", encoding="utf-8"
    )
    commit_all(gated, "specs 漂移")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "spec_hash 不匹配" in err


def test_manifest_matching_current_bytes_passes(gated: Path, cli):
    directory = _stage(gated)
    write_review(gated, "add-x")
    manifest = json.loads(
        (directory / "reviews" / "building.manifest.json").read_text(encoding="utf-8")
    )
    # 证据确实绑定了真实字节
    assert manifest["tasks_hash"] == sha256_tree(directory / "tasks.md")
    assert manifest["spec_hash"] == sha256_tree(directory / "specs")
    commit_all(gated, "完整证据")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_missing_report_file_is_rejected(gated: Path, cli):
    directory = _stage(gated)
    write_review(gated, "add-x")
    (directory / "reviews" / "building-review.md").unlink()
    commit_all(gated, "报告丢了")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "报告不存在" in err


def test_report_path_escaping_change_dir_is_rejected(gated: Path, cli):
    _stage(gated)
    write_review(gated, "add-x", report_path="../../../README.md")
    commit_all(gated, "试图指向仓外")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "逃逸出 change 目录" in err


def test_change_id_mismatch_is_rejected(gated: Path, cli):
    _stage(gated)
    write_review(gated, "add-x", doc_overrides={"change_id": "some-other-change"})
    commit_all(gated, "张冠李戴")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "与目录不符" in err


def test_multiple_stage_manifests_are_all_validated(gated: Path, cli):
    _stage(gated)
    write_review(gated, "add-x", stage="building")
    write_review(gated, "add-x", stage="grill")
    # 把 grill 那份弄坏
    path = change_dir(gated, "add-x") / "reviews" / "grill.manifest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["report_hash"] = "deadbeef"
    path.write_text(json.dumps(doc), encoding="utf-8")
    commit_all(gated, "两个阶段")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "grill.manifest.json" in err


def test_diff_hash_is_informational(gated: Path, cli):
    """diff_hash 是 informational（design §5.3）：在位即可，不校验内容。"""
    write_change(gated, "add-x")
    write_review(gated, "add-x", diff_hash="完全对不上的值")
    commit_all(gated, "diff_hash 乱填")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err
