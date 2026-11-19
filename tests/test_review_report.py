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


def test_report_renders_fixer_error():
    from witnessloop.review import report as R

    md = R._render_markdown(
        {
            "config": {},
            "config_digest": "x",
            "rounds": [
                {
                    "round": 1,
                    "actors": [],
                    "findings": [],
                    "fixer": {"error": "boom"},
                }
            ],
            "final_verdict": "BLOCKED",
        }
    )
    assert "fixer 错误：boom" in md


def test_report_renders_degraded_note():
    """两路都回落时的「同源双审」不能只留在 summary.json。"""
    from witnessloop.review import report as R

    md = R._render_markdown(
        {
            "config": {"roles": {}},
            "config_digest": "x",
            "rounds": [],
            "final_verdict": "PASS",
            "degraded_note": "本轮为同源双审",
        }
    )
    assert "同源双审" in md


def test_non_object_config_is_red(gated, cli):
    """合法 JSON 但不是对象（如 []）不能被当成有效 config 放行。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    assert _run_loop(cli, gated, mock_scenario=json.dumps({"1": []}))[0] == C.EXIT_PASS
    config_path = gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_CONFIG_FILENAME
    # 用非空数组：`config or {}` 会放过空数组，但 [1] 会暴露渲染路径的 .get 崩溃。
    config_path.write_text("[1]", encoding="utf-8")
    code, _, err = _report(cli, gated)
    assert code == C.EXIT_FAIL
    assert "证据缺件" in err
    assert "不是 JSON 对象" in err


def test_malformed_manifest_types_are_red(gated, cli):
    """篡改 actors/findings 类型时受控判红，不能崩溃。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    assert _run_loop(cli, gated, mock_scenario=json.dumps({"1": []}))[0] == C.EXIT_PASS
    doc = _round_manifest(gated)
    doc["actors"] = "not-a-list"
    doc["findings"] = {"where": "x"}
    _write_round_manifest(gated, doc)
    code, _, err = _report(cli, gated)
    assert code == C.EXIT_FAIL
    assert "类型非法" in err


def test_non_integer_round_is_red(gated, cli):
    """round 字段不是整数时不能抛 ValueError 崩掉。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    assert _run_loop(cli, gated, mock_scenario=json.dumps({"1": []}))[0] == C.EXIT_PASS
    doc = _round_manifest(gated)
    doc["round"] = "one"
    _write_round_manifest(gated, doc)
    code, _, err = _report(cli, gated)
    assert code == C.EXIT_FAIL
    assert "round 字段不是整数" in err


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
