"""P4：`review run` 编排器——并发审 / 合并去重 / fixer / 收敛 / 停滞 / 止损。"""

from __future__ import annotations

import json

from witnessloop import constants as C
from witnessloop.review import orchestrator as O

from conftest import commit_all
from helpers import write_change

FINDING = {"where": "src/x.py:1", "severity": "medium", "what": "问题", "suggestion": "改法"}


def _scenario(*rounds) -> str:
    """``{round: findings, ...}`` 的 JSON 字符串。"""
    return json.dumps({str(i + 1): list(f) for i, f in enumerate(rounds)})


def _mock_run(cli, repo, change="add-x", **extra):
    args = ["review", "run", "--root", str(repo), "--change", change, "--adapter", "mock"]
    for key, value in extra.items():
        flag = "--" + key.replace("_", "-")
        args.append(flag)
        if value is not None:
            args.append(str(value))
    return cli(*args)


def test_run_converges_with_mock_scenario(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    code, out, err = _mock_run(
        cli, gated, mock_scenario=_scenario([FINDING], [])
    )
    assert code == C.EXIT_PASS, err
    # 两轮：第一轮有 medium ⇒ 不收敛；第二轮空 ⇒ 收敛。
    rounds_dir = gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR
    manifests = sorted(rounds_dir.glob("round-*.json"))
    assert len(manifests) == 2


def test_run_records_actors_and_config_hash(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    code, _, err = _mock_run(cli, gated, mock_scenario=_scenario([], []))
    assert code == C.EXIT_PASS, err
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    roles = {a["role"] for a in manifest["actors"]}
    assert {"reviewerA", "reviewerB"} <= roles
    # 三元组 + 模型名
    for actor in manifest["actors"]:
        assert actor["adapter"] in ("claude", "codex", "mock")
        assert actor["model"]
        assert actor["run_id"]
    config = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_CONFIG_FILENAME).read_text()
    )
    from witnessloop.review import roles as roles_mod

    assert manifest["config_hash"] == roles_mod.config_hash(config)


def test_run_requires_onboarded_repo(repo, cli):
    """未接入 ⇒ EXIT_NOT_ONBOARDED(3)。"""
    code, _, err = cli("review", "run", "--root", str(repo), "--change", "add-x")
    assert code == C.EXIT_NOT_ONBOARDED


def test_bad_pass_rule_is_usage_error(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    code, _, err = cli(
        "review", "run", "--root", str(gated), "--change", "add-x",
        "--adapter", "mock", "--pass-rule", "nope",
    )
    assert code == C.EXIT_USAGE
    assert "pass_rule" in err


def test_bad_mock_scenario_is_usage_error(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    code, _, err = cli(
        "review", "run", "--root", str(gated), "--change", "add-x",
        "--adapter", "mock", "--mock-scenario", "not-json",
    )
    assert code == C.EXIT_USAGE
    assert "mock-scenario" in err


def test_non_finite_budget_is_usage_error(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    for raw in ("nan", "inf", "0", "-1"):
        code, _, err = cli(
            "review", "run", "--root", str(gated), "--change", "add-x",
            "--adapter", "mock", "--budget", raw,
        )
        assert code == C.EXIT_USAGE, raw
        assert "budget" in err


def test_bad_mock_scenario_content_is_usage_error(gated, cli):
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    for raw in ('{"1": null}', '{"1": ["bad"]}', '{"1": [{"severity": "bogus"}]}'):
        code, _, err = cli(
            "review", "run", "--root", str(gated), "--change", "add-x",
            "--adapter", "mock", "--mock-scenario", raw,
        )
        assert code == C.EXIT_USAGE, raw
        assert "mock-scenario" in err


def test_context_reads_docs_from_revision_not_worktree(gated):
    """git 模式的 change 文档必须来自被审 revision，不能混入未提交修改。"""
    from witnessloop import policy as policy_mod
    from witnessloop.review import revision as R

    write_change(gated, "add-x")
    commit_all(gated, "内容")
    tasks = gated / "openspec/changes/add-x/tasks.md"
    tasks.write_text("UNCOMMITTED-MARKER", encoding="utf-8")
    context = O._build_context(
        gated, "add-x", R.resolve_revision(gated, "git"), policy_mod.load_policy(gated)
    )
    assert "UNCOMMITTED-MARKER" not in context


def test_invalid_base_fails_before_review(gated, cli):
    """diff 取不到时不能继续跑并产出绑定当前提交的 PASS 产物。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    code, _, err = _mock_run(
        cli, gated, base="no-such-ref", mock_scenario=_scenario([], [])
    )
    assert code == C.EXIT_FAIL
    assert "diff" in err
    rounds_dir = gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR
    assert not list(rounds_dir.glob("round-*.json")) if rounds_dir.is_dir() else True


def test_run_requires_existing_change(gated, cli):
    code, _, err = cli(
        "review", "run", "--root", str(gated), "--change", "nope", "--adapter", "mock"
    )
    assert code == C.EXIT_FAIL


def test_stall_escalates_to_judge(gated, cli):
    """同一 finding 连续 2 轮重报 ⇒ 升级 judge，不继续磨。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    # 两轮都报同一个 medium finding ⇒ 第 2 轮触发停滞升级。
    code, _, err = _mock_run(
        cli, gated, mock_scenario=_scenario([FINDING], [FINDING]), stall_rounds=2
    )
    assert code == C.EXIT_FAIL  # judge 裁定 BLOCKED
    manifests = sorted((gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR).glob("round-*.json"))
    last = json.loads(manifests[-1].read_text())
    assert last["judge"] is not None
    assert last["judge"]["verdict"] == "BLOCKED"
    assert len(manifests) == 2  # 没有继续磨第三轮


def test_fixer_failure_blocks_run(gated, cli, monkeypatch):
    """fixer 失败后不能继续下一轮并让空 findings 收口为 PASS。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    monkeypatch.setattr(
        O, "_run_fixer", lambda *args, **kwargs: ({"fixes": [], "error": "boom"}, 0.0)
    )
    code, _, _ = _mock_run(
        cli, gated, mock_scenario=_scenario([FINDING], []), max_rounds=2
    )
    assert code == C.EXIT_FAIL
    rounds_dir = gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR
    assert len(list(rounds_dir.glob("round-*.json"))) == 1
    last = json.loads(
        (rounds_dir / "round-0001.json").read_text()
    )
    assert last["verdict"] == "BLOCKED"
    summary = json.loads((gated / C.REVIEW_OUTPUT_DIR / "summary.json").read_text())
    assert summary["final_verdict"] == "BLOCKED"
    assert "fixer 失败" in summary["final_note"]


def test_judge_pass_does_not_cover_unstalled_findings(gated, cli, monkeypatch):
    """judge 只复核 stalled 子集；它判 PASS 不能把未送审的 blocking finding 放行。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    a = {"where": "src/a.py:1", "severity": "medium", "what": "停滞问题"}
    b = {"where": "src/b.py:1", "severity": "high", "what": "首次出现"}
    monkeypatch.setattr(
        O, "_run_judge", lambda *args, **kwargs: ({"verdict": "PASS", "rulings": []}, 0.0)
    )
    code, _, _ = _mock_run(
        cli, gated, mock_scenario=_scenario([a], [a, b]), stall_rounds=2
    )
    assert code == C.EXIT_FAIL
    manifests = sorted(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR).glob("round-*.json")
    )
    last = json.loads(manifests[-1].read_text())
    assert "未复核" in last["note"]
    assert last["verdict"] == "BLOCKED"
    summary = json.loads((gated / C.REVIEW_OUTPUT_DIR / "summary.json").read_text())
    assert summary["final_verdict"] == "BLOCKED"


def test_cost_stop_hits_budget(gated, cli, monkeypatch):
    """成本止损：累计成本超预算 ⇒ BLOCKED。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    # mock 成本为 0；用 fake reviewer 给每路 10 USD，预算 5 强制首轮超支。
    monkeypatch.setattr(O, "_call_reviewer", _fake_reviewer_with_cost(FINDING, 10.0))
    code, _, err = _mock_run(
        cli, gated, mock_scenario=_scenario([], []), budget=5
    )
    assert code == C.EXIT_FAIL
    manifests = sorted((gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR).glob("round-*.json"))
    assert len(manifests) == 1
    last = json.loads(manifests[-1].read_text())
    assert last["verdict"] == "BLOCKED"
    assert "成本止损" in last["note"]


def test_no_keys_blocks_instead_of_mock_pass(gated, cli, monkeypatch):
    """连 deepseek 回落 key 都没有时，不得用 mock 的零 findings 冒充 PASS。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    for name in (
        "WITNESSLOOP_CODEX_KEY",
        "WITNESSLOOP_GLM_KEY",
        "WITNESSLOOP_DEEPSEEK_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    code, _, _ = cli("review", "run", "--root", str(gated), "--change", "add-x")
    assert code == C.EXIT_FAIL
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    assert manifest["verdict"] == "BLOCKED"
    assert "mock 冒充审阅" in manifest["note"]


def test_budget_stops_before_next_round_after_fixer(gated, cli, monkeypatch):
    """fixer 把累计成本推过预算后，不得再发起下一轮 reviewer 调用。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    monkeypatch.setattr(
        O, "_run_fixer", lambda *args, **kwargs: ({"fixes": []}, 10.0)
    )
    code, _, _ = _mock_run(
        cli, gated, mock_scenario=_scenario([FINDING], []), budget=5
    )
    assert code == C.EXIT_FAIL
    rounds_dir = gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR
    assert len(list(rounds_dir.glob("round-*.json"))) == 1
    summary = json.loads((gated / C.REVIEW_OUTPUT_DIR / "summary.json").read_text())
    assert "成本止损" in summary["final_note"]


def test_budget_stops_before_judge(gated, cli, monkeypatch):
    """已超预算时不再调用 judge（预算检查前移到停滞分支之前）。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    monkeypatch.setattr(O, "_call_reviewer", _fake_reviewer_with_cost(FINDING, 10.0))
    code, _, _ = _mock_run(
        cli,
        gated,
        mock_scenario=_scenario([], []),
        stall_rounds=2,
        budget=5,
    )
    assert code == C.EXIT_FAIL
    manifests = sorted(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR).glob("round-*.json")
    )
    assert len(manifests) == 1
    last = json.loads(manifests[-1].read_text())
    assert last["judge"] is None
    assert last["verdict"] == "BLOCKED"
    assert "成本止损" in last["note"]


def test_max_rounds_syncs_last_manifest_verdict(gated, cli):
    """达到 max_rounds 时最后一轮 manifest 也要记 BLOCKED。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    code, _, _ = _mock_run(cli, gated, mock_scenario=_scenario([FINDING]), max_rounds=1)
    assert code == C.EXIT_FAIL
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    assert manifest["verdict"] == "BLOCKED"


def test_missing_where_does_not_converge(gated, cli):
    """没有 where 的 medium finding 也要阻塞收敛，不能静默变成 PASS。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    scenario = json.dumps({"1": [{"severity": "medium", "what": "没有定位"}]})
    code, _, _ = _mock_run(cli, gated, mock_scenario=scenario, max_rounds=1)
    assert code == C.EXIT_FAIL
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    assert manifest["findings"][0]["where"].startswith("<missing-where>")


def test_merge_dedups_across_two_reviewers(gated, cli):
    """两路 reviewer 报同一条 where ⇒ 合并后只留一条（去重按 where）。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    # 两路 reviewer 拿到同一份 scenario ⇒ 报同一条 where；第 2 轮空 ⇒ 收敛。
    scenario = json.dumps({"1": [dict(FINDING, severity="high")]})
    code, _, err = _mock_run(cli, gated, mock_scenario=scenario)
    assert code == C.EXIT_PASS, err
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    findings = [f for f in manifest["findings"] if f["where"] == FINDING["where"]]
    assert len(findings) == 1


def _fake_reviewer_with_cost(finding, cost):
    from witnessloop.review import adapters as A

    def fake(role_name, role_cfg, request, **kwargs):
        actor = O.Actor(
            role=role_name, adapter="mock", model="mock", run_id=f"{role_name}-mock"
        )
        return (
            actor,
            A.ReviewResult(
                model="mock", findings=[dict(finding)], verdict="CHANGES_REQUESTED"
            ),
            cost,
        )

    return fake


def _fake_reviewer_with_verdict(verdict):
    from witnessloop.review import adapters as A

    def fake(role_name, role_cfg, request, **kwargs):
        actor = O.Actor(
            role=role_name, adapter="mock", model="mock", run_id=f"{role_name}-mock"
        )
        return actor, A.ReviewResult(model="mock", findings=[], verdict=verdict), 0.0

    return fake


def test_reviewer_blocked_verdict_blocks(gated, cli, monkeypatch):
    """reviewer 明确 BLOCKED 时不能被空 findings 判 PASS。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    monkeypatch.setattr(O, "_call_reviewer", _fake_reviewer_with_verdict("BLOCKED"))
    code, _, _ = _mock_run(cli, gated, mock_scenario=_scenario([], []))
    assert code == C.EXIT_FAIL
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    assert manifest["verdict"] == "BLOCKED"
    assert "BLOCKED" in manifest["note"]


def test_reviewer_changes_requested_without_findings_blocks_pass(gated, cli, monkeypatch):
    """reviewer 说 CHANGES_REQUESTED 但没给 findings 时也要阻塞。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    monkeypatch.setattr(
        O, "_call_reviewer", _fake_reviewer_with_verdict("CHANGES_REQUESTED")
    )
    code, _, _ = _mock_run(cli, gated, mock_scenario=_scenario([], []), max_rounds=1)
    assert code == C.EXIT_FAIL
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    # 达到 max_rounds 后最后一轮 verdict 同步为最终 BLOCKED；合成项仍须在。
    assert manifest["verdict"] == "BLOCKED"
    assert any(
        f["where"].startswith("<reviewer-verdict:") for f in manifest["findings"]
    )


def test_reviewer_failure_blocks_instead_of_passing(gated, cli, monkeypatch):
    """reviewer 输出无法解析 ⇒ 空 findings 也绝不能判 PASS。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")

    from witnessloop.review import adapters as A

    def fake_call(role_name, role_cfg, request, **kwargs):
        actor = O.Actor(
            role=role_name, adapter="mock", model="mock", run_id=f"{role_name}-mock"
        )
        result = A.ReviewResult(
            model="mock",
            findings=[],
            verdict="PASS",
            error="输出里没有可解析的 JSON 对象",
            error_kind="parse",
        )
        return actor, result, 0.0

    monkeypatch.setattr(O, "_call_reviewer", fake_call)
    code, _, _ = _mock_run(cli, gated, mock_scenario=_scenario([], []))
    assert code == C.EXIT_FAIL
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    assert manifest["verdict"] == "BLOCKED"
    assert "reviewer 失败" in manifest["note"]


def test_final_report_does_not_call_mock_degradation_same_source(tmp_path):
    """mock 降级不能被写成「同源双审」。"""
    from types import SimpleNamespace

    manifests = [
        {
            "actors": [
                {"role": "reviewerA", "model": "mock", "degraded_from": "gpt-6.1-sol"},
                {"role": "reviewerB", "model": "mock", "degraded_from": "glm-5.3"},
            ]
        }
    ]
    path = O._write_final_report(
        tmp_path,
        revision=SimpleNamespace(mode="digest", value="x"),
        config_hash="h",
        resolved={},
        warnings=[],
        round_manifests=manifests,
        final_verdict="BLOCKED",
        final_note="reviewer 失败",
        cumulative_cost=0.0,
    )
    doc = json.loads(path.read_text())
    assert "mock 降级" in doc["degraded_note"]
    assert "同源双审" not in doc["degraded_note"]


def test_rerun_clears_stale_rounds(gated, cli):
    """第二次 run 不能把第一次的旧 round 混进报告。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    rounds_dir = gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR
    assert _mock_run(cli, gated, mock_scenario=_scenario([FINDING], []))[0] == C.EXIT_PASS
    assert (rounds_dir / "round-0002.json").is_file()
    assert _mock_run(cli, gated, mock_scenario=_scenario([], []))[0] == C.EXIT_PASS
    assert not (rounds_dir / "round-0002.json").exists()
    assert sorted(p.name for p in rounds_dir.glob("round-*.json")) == ["round-0001.json"]


class _FailingAdapter:
    def run(self, request, *, model):
        from witnessloop.review import adapters as A

        return A.ReviewResult(model=model, error="boom", error_kind="auth")


class _RawAdapter:
    def __init__(self, raw):
        self.raw = raw

    def run(self, request, *, model):
        from witnessloop.review import adapters as A

        return A.ReviewResult(
            model=model,
            raw=self.raw,
            error="JSON 里没有 findings 数组",
            error_kind="parse",
        )


class _RawOkAdapter:
    def __init__(self, raw):
        self.raw = raw

    def run(self, request, *, model):
        from witnessloop.review import adapters as A

        return A.ReviewResult(model=model, raw=self.raw)


def _fixer_cfg():
    return {"adapter": "claude", "model": "m", "base_url": "u", "auth_env": "X"}


def test_fixer_invalid_fix_items_are_recorded(monkeypatch):
    from witnessloop.review import adapters as A

    monkeypatch.setattr(
        O.A,
        "build_adapter",
        lambda *args, **kwargs: _RawOkAdapter('{"fixes": [null, "bad", {}]}'),
    )
    record, _ = O._run_fixer(
        [FINDING], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["fixes"] == []
    assert record["error"]


def test_fixer_mixed_valid_and_invalid_items_is_error(monkeypatch):
    from witnessloop.review import adapters as A

    raw = '{"fixes": [{"where": "x", "action": "a"}, null]}'
    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: _RawOkAdapter(raw))
    record, _ = O._run_fixer(
        [FINDING], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["error"]
    assert "条目非法" in record["error"]


def test_fixer_missing_fixes_is_recorded(monkeypatch):
    from witnessloop.review import adapters as A

    monkeypatch.setattr(
        O.A, "build_adapter", lambda *args, **kwargs: _RawOkAdapter('{"findings": []}')
    )
    record, _ = O._run_fixer(
        [FINDING], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["fixes"] == []
    assert "没有有效 fixes" in record["error"]


def test_judge_invalid_verdict_is_blocked(monkeypatch):
    from witnessloop.review import adapters as A

    raw = '{"findings": [], "verdict": "BOGUS"}'
    monkeypatch.setattr(
        O.A, "build_adapter", lambda *args, **kwargs: _RawOkAdapter(raw)
    )
    record, _ = O._run_judge(
        ["x:1"], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["verdict"] == "BLOCKED"
    assert "verdict 非法" in record["error"]


def test_fixer_rejects_multiple_json_objects(monkeypatch):
    from witnessloop.review import adapters as A

    raw = (
        '{"fixes": [{"where": "x", "action": "a"}]} '
        '{"fixes": []}'
    )
    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: _RawAdapter(raw))
    record, _ = O._run_fixer(
        [FINDING], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["fixes"] == []
    assert record["error"]


def test_judge_rejects_multiple_json_objects(monkeypatch):
    from witnessloop.review import adapters as A

    raw = (
        '{"verdict": "PASS", "rulings": '
        '[{"where": "x:1", "ruling": "false-positive"}]} '
        '{"verdict": "BLOCKED", "rulings": [{"where": "x:1", "ruling": "real"}]}'
    )
    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: _RawAdapter(raw))
    record, _ = O._run_judge(
        ["x:1"], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["verdict"] == "BLOCKED"
    assert record["error"]


def test_fixer_valid_raw_is_not_marked_parse_error(monkeypatch):
    """fixer 的合法输出是 fixes；reviewer 解析器的 parse error 不应误伤。"""
    monkeypatch.setattr(
        O.A,
        "build_adapter",
        lambda *args, **kwargs: _RawAdapter('{"fixes": [{"where": "x", "action": "a"}]}'),
    )
    from witnessloop.review import adapters as A

    record, _ = O._run_fixer(
        [FINDING], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["fixes"] == [{"where": "x", "action": "a"}]
    assert "error" not in record


def test_judge_context_includes_findings_and_diff(monkeypatch):
    from witnessloop.review import adapters as A

    captured: dict = {}

    class Capture:
        def run(self, request, *, model):
            captured["context"] = request.context
            return A.ReviewResult(
                model=model,
                raw='{"verdict": "BLOCKED", "rulings": [{"where": "x:1", "ruling": "uncertain"}]}',
            )

    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: Capture())
    O._run_judge(
        ["x:1"],
        _fixer_cfg(),
        A.ReviewRequest(prompt="", context="DIFF-CONTEXT"),
        None,
        None,
        None,
        merged=[
            {
                "where": "x:1",
                "severity": "medium",
                "what": "具体问题",
                "suggestion": "改法",
            }
        ],
    )
    assert "具体问题" in captured["context"]
    assert "DIFF-CONTEXT" in captured["context"]


def test_judge_pass_requires_full_rulings(monkeypatch):
    from witnessloop.review import adapters as A

    monkeypatch.setattr(
        O.A, "build_adapter", lambda *args, **kwargs: _RawAdapter('{"verdict": "PASS"}')
    )
    record, _ = O._run_judge(
        ["x:1"], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["verdict"] == "BLOCKED"
    assert "没有 rulings" in record["error"]


def test_judge_pass_with_real_ruling_is_blocked(monkeypatch):
    from witnessloop.review import adapters as A

    raw = '{"verdict": "PASS", "rulings": [{"where": "x:1", "ruling": "real"}]}'
    monkeypatch.setattr(
        O.A, "build_adapter", lambda *args, **kwargs: _RawAdapter(raw)
    )
    record, _ = O._run_judge(
        ["x:1"], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["verdict"] == "BLOCKED"
    assert "非 false-positive" in record["error"]


def test_judge_duplicate_ruling_cannot_mask_real(monkeypatch):
    from witnessloop.review import adapters as A

    raw = (
        '{"verdict": "PASS", "rulings": ['
        '{"where": "x:1", "ruling": "real"},'
        '{"where": "x:1", "ruling": "false-positive"}]}'
    )
    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: _RawAdapter(raw))
    record, _ = O._run_judge(
        ["x:1"], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["verdict"] == "BLOCKED"


def test_judge_pass_with_false_positive_is_pass(monkeypatch):
    from witnessloop.review import adapters as A

    raw = (
        '{"verdict": "PASS", "rulings": '
        '[{"where": "x:1", "ruling": "false-positive"}]}'
    )
    monkeypatch.setattr(
        O.A, "build_adapter", lambda *args, **kwargs: _RawAdapter(raw)
    )
    record, _ = O._run_judge(
        ["x:1"], _fixer_cfg(), A.ReviewRequest(prompt="", context=""), None, None, None
    )
    assert record["verdict"] == "PASS"
    assert "error" not in record


def test_fixer_error_is_recorded(monkeypatch):
    from witnessloop.review import adapters as A

    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: _FailingAdapter())
    record, _ = O._run_fixer(
        [FINDING],
        {"adapter": "claude", "model": "m", "base_url": "u", "auth_env": "X"},
        A.ReviewRequest(prompt="", context=""),
        None,
        None,
        None,
    )
    assert record["error"] == "boom"
    assert record["error_kind"] == "auth"


def test_judge_error_is_recorded(monkeypatch):
    from witnessloop.review import adapters as A

    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: _FailingAdapter())
    record, _ = O._run_judge(
        ["src/x.py:1"],
        {"adapter": "claude", "model": "m", "base_url": "u", "auth_env": "X"},
        A.ReviewRequest(prompt="", context=""),
        None,
        None,
        None,
    )
    assert record["verdict"] == "BLOCKED"
    assert record["error"] == "boom"


def test_auth_missing_does_not_fallback_without_budget(monkeypatch):
    """缺 key 分支同样要遵守剩余预算：预算已尽时不再发 fallback。"""
    from types import SimpleNamespace

    from witnessloop.review import adapters as A

    for name in (
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "WITNESSLOOP_MISSING_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("WITNESSLOOP_DEEPSEEK_KEY", "sk-deepseek")
    calls: list[str] = []

    class Fake:
        def run(self, request, *, model):
            calls.append(model)
            return A.ReviewResult(model=model, findings=[], verdict="PASS")

    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: Fake())
    actor, result, cost = O._call_reviewer(
        "reviewerA",
        {
            "adapter": "claude",
            "model": "m",
            "base_url": "https://example.invalid",
            "auth_env": "WITNESSLOOP_MISSING_KEY",
        },
        A.ReviewRequest(prompt="", context=""),
        scenario=None,
        adapter_override=None,
        revision=SimpleNamespace(value="abcdef123456", mode="git"),
        budget_left=0.0,
    )
    assert calls == []
    assert result.error
    assert cost == 0.0


def test_no_fallback_when_budget_already_exceeded(monkeypatch):
    """首次请求成本已超剩余预算时，不再发起 fallback 付费调用。"""
    from types import SimpleNamespace

    from witnessloop.review import adapters as A

    monkeypatch.setenv("WITNESSLOOP_CODEX_KEY", "sk-codex")
    monkeypatch.setenv("WITNESSLOOP_DEEPSEEK_KEY", "sk-deepseek")
    calls: list[str] = []

    class Fake:
        def run(self, request, *, model):
            calls.append(model)
            return A.ReviewResult(
                model=model,
                error="HTTP 524",
                error_kind="other",
                usage={"input_tokens": 1_000_000, "output_tokens": 0},
            )

    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: Fake())
    actor, result, cost = O._call_reviewer(
        "reviewerA",
        {
            "adapter": "codex",
            "model": "gpt-6.1-sol",
            "base_url": "https://example.invalid",
            "auth_env": "WITNESSLOOP_CODEX_KEY",
        },
        A.ReviewRequest(prompt="", context=""),
        scenario=None,
        adapter_override=None,
        revision=SimpleNamespace(value="abcdef123456", mode="git"),
        budget_left=0.0,
    )
    assert calls == ["gpt-6.1-sol"]
    assert actor.degraded_from is None
    assert result.error_kind == "other"


def test_runtime_other_error_falls_back(monkeypatch):
    """5xx / 超时（error_kind=other）也要回落一次。"""
    from types import SimpleNamespace

    from witnessloop.review import adapters as A

    monkeypatch.setenv("WITNESSLOOP_CODEX_KEY", "sk-codex")
    monkeypatch.setenv("WITNESSLOOP_DEEPSEEK_KEY", "sk-deepseek")
    calls: list[str] = []

    class Fake:
        def run(self, request, *, model):
            calls.append(model)
            if len(calls) == 1:
                return A.ReviewResult(model=model, error="HTTP 524", error_kind="other")
            return A.ReviewResult(model=model, findings=[], verdict="PASS")

    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: Fake())
    actor, result, _ = O._call_reviewer(
        "reviewerA",
        {
            "adapter": "codex",
            "model": "sol",
            "base_url": "https://example.invalid",
            "auth_env": "WITNESSLOOP_CODEX_KEY",
        },
        A.ReviewRequest(prompt="", context=""),
        scenario=None,
        adapter_override=None,
        revision=SimpleNamespace(value="abcdef123456", mode="git"),
    )
    assert calls == ["sol", "deepseek-flash"]
    assert actor.degraded_from == "sol"
    assert result.error is None


def test_fallback_is_attempted_only_once(monkeypatch):
    """先缺 key 回落、回落请求又失败时，不能把回落目标再回落一次。"""
    from types import SimpleNamespace

    from witnessloop.review import adapters as A

    for name in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("WITNESSLOOP_DEEPSEEK_KEY", "sk-deepseek")
    monkeypatch.delenv("WITNESSLOOP_MISSING_KEY", raising=False)
    calls: list[str] = []

    class Fake:
        def run(self, request, *, model):
            calls.append(model)
            return A.ReviewResult(model=model, error="boom", error_kind="auth")

    monkeypatch.setattr(O.A, "build_adapter", lambda *args, **kwargs: Fake())
    actor, result, _ = O._call_reviewer(
        "reviewerA",
        {
            "adapter": "claude",
            "model": "m",
            "base_url": "https://example.invalid",
            "auth_env": "WITNESSLOOP_MISSING_KEY",
        },
        A.ReviewRequest(prompt="", context=""),
        scenario=None,
        adapter_override=None,
        revision=SimpleNamespace(value="abcdef123456", mode="git"),
    )
    assert calls == ["deepseek-flash"]
    assert result.error == "boom"
    assert actor.degraded_from == "m"


def test_prioritize_diff_puts_code_before_docs():
    """diff 截断时先保留代码/测试，不能让 docs 吃掉预算。"""
    code = (
        "diff --git a/src/x.py b/src/x.py\n--- a/src/x.py\n+++ b/src/x.py\n"
        "@@ -1 +1 @@\n+code\n"
    )
    docs = (
        "diff --git a/docs/x.md b/docs/x.md\n--- a/docs/x.md\n+++ b/docs/x.md\n"
        "@@ -1 +1 @@\n+doc\n"
    )
    out = O._prioritize_diff(docs + code, limit=len(code) + 30)
    assert out.index("src/x.py") < out.index("docs/x.md")
    assert "已截断" in out


def test_run_digest_mode_in_git_repo(gated, cli):
    """显式 --mode digest：即使有 .git 也走 digest 锚。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    code, _, err = _mock_run(cli, gated, mode="digest", mock_scenario=_scenario([], []))
    assert code == C.EXIT_PASS, err
    manifest = json.loads(
        (gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR / "round-0001.json").read_text()
    )
    assert manifest["revision"]["mode"] == "digest"
