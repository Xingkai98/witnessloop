"""P3/P4：适配器与 findings 合并去重。"""

from __future__ import annotations

from witnessloop.review import adapters as A


def test_severity_rank_orders_blocker_highest():
    assert A.severity_rank("blocker") > A.severity_rank("high")
    assert A.severity_rank("medium") > A.severity_rank("low")
    assert A.severity_rank("low") > A.severity_rank("nit")


def test_parse_review_output_extracts_json_from_fenced_text():
    text = (
        '前置说明\n```json\n{"verdict": "CHANGES_REQUESTED", '
        '"findings": [{"where": "a:1", "severity": "high"}]}\n```'
    )
    findings, verdict, err = A.parse_review_output(text)
    assert err is None
    assert verdict == "CHANGES_REQUESTED"
    assert findings == [{"where": "a:1", "severity": "high"}]


def test_parse_review_output_accepts_issues_alias():
    findings, verdict, err = A.parse_review_output(
        '{"issues": [{"where": "b:2", "severity": "medium"}]}'
    )
    assert err is None
    assert findings == [{"where": "b:2", "severity": "medium"}]
    assert verdict == "PASS"


def test_parse_review_output_normalizes_severity():
    findings, _, err = A.parse_review_output(
        '{"findings": [{"where": "x:1", "severity": " HIGH "}]}'
    )
    assert err is None
    assert findings[0]["severity"] == "high"


def test_parse_review_output_rejects_non_object_finding():
    _, _, err = A.parse_review_output('{"findings": ["发现严重问题"]}')
    assert err is not None


def test_parse_review_output_rejects_missing_or_unknown_severity():
    _, _, err = A.parse_review_output('{"findings": [{"where": "x:1"}]}')
    assert err is not None
    _, _, err = A.parse_review_output(
        '{"findings": [{"where": "x:1", "severity": "critical"}]}'
    )
    assert err is not None


def test_parse_review_output_rejects_illegal_explicit_verdict():
    _, _, err = A.parse_review_output('{"verdict": "FAIL", "findings": []}')
    assert err is not None


def test_parse_review_output_rejects_top_level_array():
    _, _, err = A.parse_review_output('[{"findings": []}]')
    assert err is not None
    assert A.extract_single_json('[{"fixes": []}]') is None


def test_parse_review_output_allows_prose_brackets():
    text = '以下按 [P1][P2] 分组：\n{"findings": []}'
    findings, _, err = A.parse_review_output(text)
    assert err is None
    assert findings == []


def test_parse_review_output_rejects_multiple_json_objects():
    text = (
        '{"findings": []} '
        '{"findings": [{"where": "x:1", "severity": "high"}]}'
    )
    _, _, err = A.parse_review_output(text)
    assert err is not None


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


def test_merge_findings_keeps_findings_without_where():
    """没有 where 的 medium+ 不能被静默丢成 PASS；用合成 where 保留。"""
    from witnessloop.review import orchestrator as O

    merged = O._merge_findings([[{"severity": "high", "what": "no where"}]])
    assert len(merged) == 1
    assert merged[0]["where"].startswith("<missing-where>")
    assert merged[0]["what"] == "no where"


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


def test_cost_usd_knows_gpt_6_1_sol():
    """gpt-6.1-sol 必须进价格表；否则未知模型恒 0，预算止损静默失效。"""
    usage = {"input_tokens": 1000, "output_tokens": 500}
    cost = A.cost_usd("gpt-6.1-sol", usage)
    assert cost == 1000 / 1e6 * 5.0 + 500 / 1e6 * 30.0


def test_build_adapter_uses_shared_auth_resolution(monkeypatch):
    """显式 opt-in 时，预检与构造适配器共用 ANTHROPIC_* 兜底。"""
    monkeypatch.delenv("WITNESSLOOP_MISSING_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-host-token")
    adapter = A.build_adapter(
        "claude",
        role={
            "adapter": "claude",
            "base_url": "https://example.invalid",
            "auth_env": "WITNESSLOOP_MISSING_KEY",
            "allow_host_auth_fallback": True,
        },
    )
    assert adapter.auth_token == "sk-host-token"


def test_build_adapter_does_not_reuse_host_token_by_default(monkeypatch):
    """普通 reviewer 角色不得把宿主 Anthropic token 发往别的 base_url。"""
    monkeypatch.delenv("WITNESSLOOP_MISSING_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-host-token")
    adapter = A.build_adapter(
        "codex",
        role={
            "adapter": "codex",
            "base_url": "https://heyroute.ai/v1",
            "auth_env": "WITNESSLOOP_MISSING_KEY",
        },
    )
    assert adapter.auth_token == ""


def test_parse_error_marks_adapter_result_as_parse_failure(monkeypatch):
    """畸形输出不能是「零 findings 的 PASS」；必须带 error_kind 供回落/阻断。"""
    monkeypatch.setattr(
        A,
        "_http_json",
        lambda *args, **kwargs: {
            "content": [{"type": "text", "text": "没有 JSON"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
    )
    adapter = A.ClaudeAdapter("https://example.invalid", "sk-x")
    result = adapter.run(A.ReviewRequest(prompt="", context=""), model="mock")
    assert result.error is not None
    assert result.error_kind == "parse"
    assert result.verdict == "PASS"  # 解析函数自己的占位 verdict …
    assert result.findings == []


def test_claude_adapter_rejects_non_array_content(monkeypatch):
    monkeypatch.setattr(A, "_http_json", lambda *args, **kwargs: {"content": 1})
    result = A.ClaudeAdapter("https://example.invalid", "sk-x").run(
        A.ReviewRequest(prompt="", context=""), model="m"
    )
    assert result.error_kind == "other"


def test_cost_usd_tolerates_bad_usage():
    assert A.cost_usd("deepseek-flash", {"input_tokens": "bad", "output_tokens": None}) == 0


def test_claude_adapter_tolerates_non_object_usage(monkeypatch):
    monkeypatch.setattr(
        A,
        "_http_json",
        lambda *args, **kwargs: {
            "content": [{"type": "text", "text": '{"findings": []}'}],
            "usage": [1],
        },
    )
    result = A.ClaudeAdapter("https://example.invalid", "sk-x").run(
        A.ReviewRequest(prompt="", context=""), model="m"
    )
    assert result.error is None
    assert result.usage is None


def test_codex_adapter_tolerates_non_object_usage(monkeypatch):
    monkeypatch.setattr(
        A,
        "_http_json",
        lambda *args, **kwargs: {
            "choices": [{"message": {"content": '{"findings": []}'}}],
            "usage": 1,
        },
    )
    result = A.CodexAdapter("https://example.invalid", "sk-x").run(
        A.ReviewRequest(prompt="", context=""), model="m"
    )
    assert result.error is None
    assert result.usage is None


def test_redirect_is_refused():
    """重定向不能把 Authorization / x-api-key 转发到其它主机。"""
    import pytest

    with pytest.raises(A.AdapterError, match="拒绝重定向"):
        A._NoRedirect().redirect_request(
            None, None, 302, "Found", {}, "https://evil.example"
        )


def test_http_timeout_is_adapter_error(monkeypatch):
    """socket timeout 必须归一成 AdapterError，而不是让 CLI 崩成内部错误。"""

    class FakeOpener:
        def open(self, *args, **kwargs):
            raise TimeoutError("timed out")

    monkeypatch.setattr(A, "_OPENER", FakeOpener())
    result = A.ClaudeAdapter("https://example.invalid", "sk-x").run(
        A.ReviewRequest(prompt="", context=""), model="m"
    )
    assert result.error_kind == "other"
    assert "超时" in result.error


def test_claude_adapter_rejects_non_object_response(monkeypatch):
    monkeypatch.setattr(A, "_http_json", lambda *args, **kwargs: [])
    result = A.ClaudeAdapter("https://example.invalid", "sk-x").run(
        A.ReviewRequest(prompt="", context=""), model="m"
    )
    assert result.error_kind == "other"


def test_codex_adapter_handles_non_string_content(monkeypatch):
    monkeypatch.setattr(
        A,
        "_http_json",
        lambda *args, **kwargs: {
            "choices": [{"message": {"content": ["x"]}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
    )
    result = A.CodexAdapter("https://example.invalid", "sk-x").run(
        A.ReviewRequest(prompt="", context=""), model="m"
    )
    assert result.error is not None
    assert result.error_kind == "parse"


def test_classify_auth_error():
    assert A._classify(401, "unauthorized") == "auth"
    assert A._classify(402, "insufficient balance") == "balance"
    assert A._classify(404, "model_not_found") == "model_not_found"
    assert A._classify(500, "boom") == "other"
