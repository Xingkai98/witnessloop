"""D 组：`building` 门禁（change building-review-gate / issue #13）。

把「实现后独立审阅」从**自觉**变成 `check` 的**机械门**：本次 diff 触及 `policy.require_change_for`
（= 落了实现）⇒ 被触及的 change **必须**有一份 `stage=building` 的审阅证据。

**另一半已有**：`contract._check_git_span` 的 revision 绑定保证「审阅之后再改代码 ⇒ 判 stale」
（B7 把它钉成回归）。

边界：**不改 `guard`**（写码前不可能有实现后审阅 ⇒ 强加会自锁）；**纯文档 / 纯 change 目录改动不要求**（B5）。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all
from helpers import check, commit_content, write_review

CHANGE = "add-x"
OTHER = "b-doc"

#: 「改了受管控代码」的最小注入：往 `src/` 写一个文件（`require_change_for` 默认含 `src/**`）。
CODE_WRITE = (("src/app.py", "value = 1\n"),)


def _green(result) -> None:
    code, _, err = result
    assert code == C.EXIT_PASS, f"期望通过，实际 exit={code}\n{err}"


# ---------------------------------------------------------------- 触发 / 不触发


def test_red_when_code_changed_without_building_evidence(gated: Path, cli):
    """核心：改了代码但只跑了 grill ⇒ `check` 必须红，且点名缺 `stage=building`。"""
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")  # 只有 grill 证据
    commit_all(gated, "内容 + grill 证据")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "stage=building" in err
    assert f"changes/{CHANGE}" in err


def test_green_when_building_evidence_present(gated: Path, cli):
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="grill-adversarial")  # 设计环的另一半（issue #16）
    write_review(gated, CHANGE, stage="building")
    commit_all(gated, "内容 + 三份证据")

    _green(check(gated, cli))


def test_not_required_when_only_the_change_dir_changed(gated: Path, cli):
    """提案期 / 纯文档改动：**不**触及 `require_change_for` ⇒ 不要求 building 证据（不误伤 in-flight change）。"""
    commit_content(gated, CHANGE)  # 只动 change 目录，不写 src/
    write_review(gated, CHANGE, stage="grill")
    commit_all(gated, "提案期 + grill 证据")

    _green(check(gated, cli))


def test_stage_typo_is_diagnosable(gated: Path, cli):
    """`--stage buildings` ⇒ 红且**点名现有 stage**（拼错可诊断，口径同 grill 那条）。"""
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="buildings")
    commit_all(gated, "内容 + 拼错的 stage")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "现有 stage：grill, buildings" in err or "buildings" in err


# ---------------------------------------------------------------- 多 change 同 PR（刻意的行为）


def test_every_change_in_a_code_pr_must_have_building_evidence(gated: Path, cli):
    """**多 change 同 PR**：本 PR 触及代码 ⇒ 本 PR 触及的**每个** change 都要 building 证据。

    这是**刻意的**（设计的「一个 PR 推进一个 change」前提）：`OTHER` 自身无实现，但因本 PR 落了代码，
    它也被要求——要免除就把 change 拆到单独 PR。**不提供**豁免名单。
    """
    commit_content(gated, "impl-a", spec_writes=(("src/a.py", "x = 1\n"),))
    write_review(gated, "impl-a", stage="grill")
    write_review(gated, "impl-a", stage="building")

    commit_content(gated, OTHER)  # 纯文档 change
    write_review(gated, OTHER, stage="grill")
    commit_all(gated, "两个 change")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert f"changes/{OTHER}" in err and "stage=building" in err
    # 有实现的那个**不该**被点名（它有 building 证据）
    assert f"changes/impl-a：无 stage=building" not in err


# ---------------------------------------------------------------- 审阅须在最终实现之后（回归）


def test_code_change_after_the_review_is_stale(gated: Path, cli):
    """**这半已有**（`contract._check_git_span`）：审阅之后再改代码 ⇒ 判 stale。

    本用例把它钉成回归——building 门禁成立的一半靠它。
    """
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="grill-adversarial")  # 设计环的另一半（issue #16）
    write_review(gated, CHANGE, stage="building")
    commit_all(gated, "内容 + 证据")

    _green(check(gated, cli))

    commit_content(gated, CHANGE, spec_writes=(("src/app.py", "value = 2\n"),))  # commit_content 自带提交

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "审阅的是旧 revision" in err


# ---------------------------------------------------------------- 共用助手（一处实现、两种深度）


def test_shared_helper_requires_only_existence_for_building(repo: Path, cli, tmp_path: Path):
    """`stage_manifest_findings_in_change(verify_body=False)` 只要求**存在**——
    building 的 manifest 绑一份**没有** grill 式小节的普通报告也应通过（不泄漏 grill 的正文判据）。"""
    from witnessloop import evidence

    commit_content(repo, CHANGE, spec_writes=CODE_WRITE)
    write_review(repo, CHANGE, stage="building", report_body="PASS\n\n常规审阅报告，没有 grill 式小节。\n")

    findings = evidence.stage_manifest_findings_in_change(
        repo / "openspec" / "changes" / CHANGE,
        stage="building",
        reason="（building 的理由）",
    )
    assert findings == []


def test_shared_helper_reports_missing_stage_with_the_given_reason(repo: Path, cli):
    from witnessloop import evidence

    commit_content(repo, CHANGE, spec_writes=CODE_WRITE)
    write_review(repo, CHANGE, stage="grill")

    findings = evidence.stage_manifest_findings_in_change(
        repo / "openspec" / "changes" / CHANGE,
        stage="building",
        reason="（building 的理由）",
    )
    assert len(findings) == 1
    assert "stage=building" in findings[0].message
    assert "（building 的理由）" in findings[0].message
    assert "现有 stage：grill" in findings[0].message


# ---------------------------------------------------------------- 参数化轴（补审阅发现的覆盖缺口）


def test_building_stage_is_configurable(repo: Path, cli, read_json):
    """`policy.evidence.building_stage` **可覆写**（文档承诺的轴必须有测试钉住——
    审阅的变异检查 M11「让覆写失效、恒用默认」曾**全绿逃逸**）。"""
    import json

    from conftest import git

    cli("init", "--root", str(repo))
    policy_path = repo / C.POLICY_PATH
    doc = read_json(policy_path)
    doc["evidence"]["building_stage"] = "review"
    policy_path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    commit_all(repo, "把 building_stage 换成 review")
    git(repo, "checkout", "-q", "-b", "feature")

    commit_content(repo, CHANGE, spec_writes=CODE_WRITE)
    write_review(repo, CHANGE, stage="grill")
    write_review(repo, CHANGE, stage="grill-adversarial")
    write_review(repo, CHANGE, stage="building")  # 只有默认 stage 的证据 ⇒ 应红
    commit_all(repo, "内容 + grill + adversarial + building 证据")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "stage=review" in err  # 点名的是**配置**的那个 stage

    write_review(repo, CHANGE, stage="review")  # 补上配置 stage 的证据 ⇒ 转绿
    commit_all(repo, "补 stage=review 的证据")
    code, _, err = check(repo, cli)
    assert code == C.EXIT_PASS, err
