"""D3：review manifest 存在且 hash 绑定；D4：reviewer_run_id != author_run_id。"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C
from witnessloop.hashing import sha256_tree

from conftest import commit_all, git
from helpers import (
    change_dir,
    check,
    commit_content,
    commit_evidence,
    write_artifact,
    write_change,
    write_event,
    write_review,
)


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
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    directory = change_dir(gated, "add-x")
    manifest = json.loads(
        (directory / "reviews" / "building.manifest.json").read_text(encoding="utf-8")
    )
    # 证据确实绑定了真实字节
    assert manifest["tasks_hash"] == sha256_tree(directory / "tasks.md")
    assert manifest["spec_hash"] == sha256_tree(directory / "specs")

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


def test_head_sha_must_resolve_to_a_real_commit(gated: Path, cli):
    """回归 I-3：以前乱填 head_sha（如全 1）也绿。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x", head_sha="1" * 40)

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "head_sha" in err
    assert "不是本仓的提交" in err


def test_base_sha_must_resolve_to_a_real_commit(gated: Path, cli):
    """回归 I-3：以前乱填 base_sha（如全 0）也绿。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x", base_sha="0" * 40)

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "base_sha" in err
    assert "不是本仓的提交" in err


def test_sha_fields_must_look_like_shas(gated: Path, cli):
    """回归 R2 3-6：字段名叫 *_sha，就不该接受 `main` / `HEAD~3` 这类符号 ref。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x", base_sha="main")  # 能解析，但不是 sha

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "base_sha" in err
    assert "40 位" in err


def test_head_sha_symbolic_ref_is_rejected(gated: Path, cli):
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x", head_sha="HEAD~1")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "head_sha" in err
    assert "40 位" in err


def test_code_committed_after_review_is_stale(gated: Path, cli):
    """回归 I-3：审阅之后又推一个只改 src/ 的提交 —— 必须报「审阅的是旧 revision」。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    write_artifact(gated, "src/later.py", "x = 1\n")
    commit_all(gated, "审阅之后又改代码")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "旧 revision" in err
    assert "src/later.py" in err


def test_head_sha_must_be_an_ancestor_of_the_checked_head(gated: Path, cli):
    """head_sha 指向一个真实存在、但不在本次被检历史里的提交。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    # 在主干上另造一个提交：它真实存在，但不是 feature HEAD 的祖先。
    git(gated, "checkout", "-q", "main")
    write_artifact(gated, "unrelated.txt", "x\n")
    unrelated = commit_all(gated, "无关提交")
    git(gated, "checkout", "-q", "feature")

    manifest = change_dir(gated, "add-x") / "reviews" / "building.manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    doc["head_sha"] = unrelated
    manifest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    commit_all(gated, "篡改 head_sha")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "祖先" in err


def _advance_base_and_merge(repo: Path) -> None:
    """模拟活跃仓的常态：分支开出后 base 前进了，PR 再 merge 回主干。

    这正是 `pull_request` 事件下 `actions/checkout` 检出的 test-merge commit 形态。
    """
    git(repo, "checkout", "-q", "main")
    write_artifact(repo, "src/other.py", "y = 2\n")  # 只在 base 侧改，与 PR 无关
    commit_all(repo, "base 前进")
    git(repo, "checkout", "-q", "feature")
    git(repo, "merge", "--no-ff", "--no-edit", "-m", "merge main", "main")


def test_base_advanced_then_merged_does_not_false_positive(gated: Path, cli):
    """回归 R2 3-1：被检 head 是 merge commit 时，**base 侧**的文件不能被判 stale。

    原先 `head_sha..checked_head`（两点）会把 merge 进来的 base 侧改动算进 delta，
    于是活跃仓里每个「跟上主干」的 PR 都被误拦——门禁在主部署形态下直接失效。
    """
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    _advance_base_and_merge(gated)

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, f"base 侧前进被误判成 stale：{err}"
    assert "旧 revision" not in err


def test_base_advanced_without_merge_does_not_false_positive(gated: Path, cli):
    """对照组：base 前进但 PR head 不是 merge commit（未 merge）→ 也应通过。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    git(gated, "checkout", "-q", "main")
    write_artifact(gated, "src/other.py", "y = 2\n")
    commit_all(gated, "base 前进")
    git(gated, "checkout", "-q", "feature")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_real_stale_change_survives_the_merge_commit_fix(gated: Path, cli):
    """真阳性不能被修没：merge 之后再改自己 PR 的源码 → 仍报 stale。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    _advance_base_and_merge(gated)
    write_artifact(gated, "src/app.py", "z = 3\n")  # PR 自己的实现代码
    commit_all(gated, "审阅后又改实现")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "旧 revision" in err
    assert "src/app.py" in err


def test_evidence_committed_after_content_passes(gated: Path, cli):
    """正确约定：内容一个提交，证据紧接着一个提交 → 绿。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_single_commit_pr_is_rejected(gated: Path, cli):
    """已文档化的限制（gate.md §3.1）：内容与证据同处**一个**提交 → 恒判 stale。

    写 manifest 时 HEAD 还停在改动前的提交上，`head_sha` 只能等于那个更早的
    revision，于是从它到被检 head 之间全是内容文件。这是自指带来的固有约束。

    把限制钉成契约：哪天它变绿了，说明绑定机制变了，gate.md §3.1 必须同步改。
    """
    write_change(gated, "add-x")
    write_review(gated, "add-x")  # head_sha = 本次提交的父提交
    commit_all(gated, "内容与证据同一个提交")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "旧 revision" in err


def test_reviews_dir_outside_the_change_is_not_evidence(gated: Path, cli):
    """回归 R2 3-3：`**/reviews/**` 太宽——审阅后往任意 reviews 目录塞内容即可绕开 stale。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    write_artifact(gated, "src/reviews/sneaky.py", "x = 1\n")
    commit_all(gated, "审阅后把非证据塞进 reviews 目录")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "旧 revision" in err
    assert "src/reviews/sneaky.py" in err


def test_events_file_outside_the_change_is_not_evidence(gated: Path, cli):
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    write_artifact(gated, "src/workflow-events.jsonl", '{"a":1}\n')
    commit_all(gated, "审阅后塞一个同名事件文件")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "旧 revision" in err


def test_evidence_only_delta_does_not_count_as_stale(gated: Path, cli):
    """审阅后再补一条解释事件（属证据）→ 不算 stale。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x")
    write_event(gated, "add-x", "openspec/specs/whatever.md")
    commit_all(gated, "补证据")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_diff_hash_is_informational(gated: Path, cli):
    """diff_hash 是 informational（design §5.3）：在位即可，不校验内容。"""
    commit_content(gated, "add-x")
    commit_evidence(gated, "add-x", diff_hash="完全对不上的值")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err
