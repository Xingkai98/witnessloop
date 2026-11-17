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


def test_cost_stop_hits_budget(gated, cli):
    """成本止损：累计成本超预算 ⇒ BLOCKED。"""
    write_change(gated, "add-x")
    commit_all(gated, "内容")
    # mock 成本为 0，所以用 --adapter 覆盖成 mock 但把预算设成 -1，强制首轮超预算。
    code, _, err = _mock_run(
        cli, gated, mock_scenario=_scenario([FINDING], []), budget=-1
    )
    assert code == C.EXIT_FAIL
    manifests = sorted((gated / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR).glob("round-*.json"))
    assert len(manifests) == 1
    assert "成本止损" in json.loads(manifests[-1].read_text())["note"]


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
