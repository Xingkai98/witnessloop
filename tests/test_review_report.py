"""P4：`review report --md` 读回 + 四条负样本验证。"""

from __future__ import annotations

import json

from witnessloop import constants as C

from conftest import commit_all
from helpers import write_change

FINDING = {"where": "src/x.py:1", "severity": "medium", "what": "问题", "suggestion": "改法"}


def _run_loop(cli, repo, **extra):
    args = ["review", "run", "--root", str(repo), "--change", "add-x", "--adapter", "mock"]
    for key, value in extra.items():
        args.append("--" + key.replace("_", "-"))
        if value is not None:
            args.append(str(value))
    return cli(*args)


def _report(cli, repo, **extra):
    args = ["review", "report", "--root", str(repo)]
    for key, value in extra.items():
        args.append("--" + key.replace("_", "-"))
        if value is not None:
            args.append(str(value))
    return cli(*args)


def _round_manifest(repo, n=1) -> dict:
    path = repo / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / f"round-{n:04d}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _write_round_manifest(repo, doc, n=1):
    path = repo / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / f"round-{n:04d}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_report_reads_back_actors_and_config_hash(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    assert _run_loop(cli, gated, mock_scenario=json.dumps({"1": []}))[0] == C.EXIT_PASS
    code, out, err = _report(cli, gated)
    assert code == C.EXIT_PASS, err
    assert "reviewerA" in out and "reviewerB" in out
    assert "config_hash" in out
    assert "验证通过" in err


def test_tampered_manifest_is_red(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    assert _run_loop(cli, gated, mock_scenario=json.dumps({"1": []}))[0] == C.EXIT_PASS
    doc = _round_manifest(gated)
    doc["config_hash"] = "deadbeef"
    _write_round_manifest(gated, doc)
    code, out, err = _report(cli, gated)
    assert code == C.EXIT_FAIL
    assert "篡改 manifest" in err


def test_missing_evidence_is_red(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    assert _run_loop(cli, gated, mock_scenario=json.dumps({"1": []}))[0] == C.EXIT_PASS
    (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_CONFIG_FILENAME).unlink()
    code, _, err = _report(cli, gated)
    assert code == C.EXIT_FAIL
    assert "证据缺件" in err


def test_same_actor_twice_is_red(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    assert _run_loop(cli, gated, mock_scenario=json.dumps({"1": []}))[0] == C.EXIT_PASS
    doc = _round_manifest(gated)
    reviewers = [a for a in doc["actors"] if a["role"].startswith("reviewer")]
    reviewers[1]["run_id"] = reviewers[0]["run_id"]
    _write_round_manifest(gated, doc)
    code, _, err = _report(cli, gated)
    assert code == C.EXIT_FAIL
    assert "两路同一 actor" in err


def test_positive_control_missed_is_red(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    # 正控指向一个从未被报出的 where；loop 收敛（PASS）⇒ 漏报。
    code, _, _ = _run_loop(
        cli, gated,
        mock_scenario=json.dumps({"1": []}),
        positive_control="src/x.py:999",
    )
    assert code == C.EXIT_PASS
    code, _, err = _report(cli, gated)
    assert code == C.EXIT_FAIL
    assert "正控漏报" in err


def test_positive_control_found_is_green(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    # 正控指向第一轮真实报出的 where ⇒ 不漏报，绿。
    code, _, _ = _run_loop(
        cli, gated,
        mock_scenario=json.dumps({"1": [FINDING], "2": []}),
        positive_control=FINDING["where"],
    )
    assert code == C.EXIT_PASS
    code, _, err = _report(cli, gated)
    assert code == C.EXIT_PASS, err
