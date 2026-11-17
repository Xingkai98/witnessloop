"""P3/P4：适配器与 findings 合并去重。"""

from __future__ import annotations

from witnessloop.review import adapters as A


def test_severity_rank_orders_blocker_highest():
    assert A.severity_rank("blocker") > A.severity_rank("high")
    assert A.severity_rank("medium") > A.severity_rank("low")
    assert A.severity_rank("low") > A.severity_rank("nit")


def test_parse_review_output_extracts_json_from_fenced_text():
    text = '前置说明\n```json\n{"verdict": "CHANGES_REQUESTED", "findings": [{"where": "a:1"}]}\n```'
    findings, verdict, err = A.parse_review_output(text)
    assert err is None
    assert verdict == "CHANGES_REQUESTED"
    assert findings == [{"where": "a:1"}]


def test_parse_review_output_accepts_issues_alias():
    findings, verdict, err = A.parse_review_output('{"issues": [{"where": "b:2"}]}')
    assert err is None
    assert findings == [{"where": "b:2"}]
    assert verdict == "PASS"


def test_parse_review_output_reports_error_when_no_json():
    _, _, err = A.parse_review_output("没有 JSON")
    assert err is not None


def test_merge_findings_dedups_by_where_keeping_higher_severity():
    from witnessloop.review import orchestrator as O

    batches = [
        [{"where": "a:1", "severity": "medium", "what": "m"}],
        [{"where": "a:1", "severity": "high", "what": "h"}, {"where": "b:2", "severity": "low"}],
    ]
    merged = O._merge_findings(batches)
    by_where = {f["where"]: f for f in merged}
    assert by_where["a:1"]["severity"] == "high"
    assert "b:2" in by_where


def test_merge_findings_drops_findings_without_where():
    from witnessloop.review import orchestrator as O

    merged = O._merge_findings([[{"severity": "high", "what": "no where"}]])
    assert merged == []


def test_pass_rule_medium_plus_zero():
    from witnessloop.review import orchestrator as O

    assert O._pass_rule_satisfied([], "medium_plus_zero")
    assert O._pass_rule_satisfied([{"severity": "low"}], "medium_plus_zero")
    assert O._pass_rule_satisfied([{"severity": "nit"}], "medium_plus_zero")
    assert not O._pass_rule_satisfied([{"severity": "medium"}], "medium_plus_zero")
    assert not O._pass_rule_satisfied([{"severity": "blocker"}], "medium_plus_zero")


def test_mock_adapter_returns_scenario_by_round():
    scenario = {1: [{"where": "x:1", "severity": "high"}], 2: []}
    adapter = A.MockAdapter(scenario=scenario)
    r1 = adapter.run(A.ReviewRequest(prompt="", context="", round=1), model="mock")
    r2 = adapter.run(A.ReviewRequest(prompt="", context="", round=2), model="mock")
    assert len(r1.findings) == 1
    assert r1.verdict == "CHANGES_REQUESTED"
    assert r2.findings == []
    assert r2.verdict == "PASS"


def test_cost_usd_zero_without_usage():
    assert A.cost_usd("gpt-6.1-terra", None) == 0.0


def test_cost_usd_computed_from_usage():
    usage = {"input_tokens": 1000, "output_tokens": 500}
    cost = A.cost_usd("deepseek-flash", usage)
    assert cost == 1000 / 1e6 * 0.07 + 500 / 1e6 * 0.28


def test_classify_auth_error():
    assert A._classify(401, "unauthorized") == "auth"
    assert A._classify(402, "insufficient balance") == "balance"
    assert A._classify(404, "model_not_found") == "model_not_found"
    assert A._classify(500, "boom") == "other"
