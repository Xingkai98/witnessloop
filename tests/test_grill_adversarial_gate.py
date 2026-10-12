"""G 组：`grill-adversarial` 门禁（change grill-adversarial-gate / issue #16）。

把「设计阶段的对抗验证轮」从**自觉**变成 `check` 的**机械门**：本次 diff 触及
`policy.require_change_for`（= 落了实现）⇒ 被触及的 change **必须**有一份
`stage=grill-adversarial` 的审阅证据（manifest + 其绑定的报告）。

**触发面 = 乙（Q1 定案）**：与 `building` 门禁**共用同一条 `code_hits` 判定**——
不是「每个 change 都要求」（甲被否：它的触发面没有「不触发」分支，「只动 change 目录」的场景
只能被**空正文报告**满足 ⇒ 门形同虚设）。

**判据（Q2 定案 = 甲）**：只要求证据**存在**（`verify_body=False`）——不解析 verdict 文本、
不校验报告正文，**空文件亦合格**（spec 边界声明 4）。这条上限被下面的
`test_empty_report_body_is_accepted` 钉住，防止「存在即合格」被无声升级成「有内容才合格」。

边界：**不改 `guard`**（Q3 定案：接受缺口）；纯文档 / 纯 change 目录改动 ⇒ 不要求（乙的**主要理由**）。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all, git
from helpers import check, commit_content, write_artifact, write_review

CHANGE = "add-x"
OTHER = "b-doc"

#: 「改了受管控代码」的最小注入：往 `src/` 写一个文件（`require_change_for` 默认含 `src/**`）。
CODE_WRITE = (("src/app.py", "value = 1\n"),)

STAGE = C.DEFAULT_GRILL_ADVERSARIAL_STAGE


def _green(result) -> None:
    code, _, err = result
    assert code == C.EXIT_PASS, f"期望通过，实际 exit={code}\n{err}"


# ---------------------------------------------------------------- 触发 / 不触发


def test_red_when_code_changed_without_adversarial_evidence(gated: Path, cli):
    """核心：改了代码、跑过 grill 与 review-loop，但**没跑设计对抗轮** ⇒ `check` 必须红。"""
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="building")
    commit_all(gated, "内容 + grill + building 证据")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert f"stage={STAGE}" in err
    assert f"changes/{CHANGE}" in err


def test_green_when_adversarial_evidence_present(gated: Path, cli):
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="building")
    write_review(gated, CHANGE, stage=STAGE)
    commit_all(gated, "内容 + 三份证据")

    _green(check(gated, cli))


def test_not_required_when_only_the_change_dir_changed(gated: Path, cli):
    """提案期 / 纯文档改动：**不**触及 `require_change_for` ⇒ 不要求对抗轮证据。

    这是**选乙的主要理由**：否则每个 in-flight change（设计还没写完）都会被红。
    """
    commit_content(gated, CHANGE)  # 只动 change 目录，不写 src/
    write_review(gated, CHANGE, stage="grill")
    commit_all(gated, "提案期 + grill 证据")

    _green(check(gated, cli))


def test_stage_typo_is_diagnosable(gated: Path, cli):
    """`--stage grill-adversariall` ⇒ 红且**点名现有 stage**（拼错可诊断，口径同 grill/building 两条）。"""
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="building")
    write_review(gated, CHANGE, stage="grill-adversariall")
    commit_all(gated, "内容 + 拼错的 stage")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert f"stage={STAGE}" in err
    assert "现有 stage：" in err


# ---------------------------------------------------------------- 多 change 同 PR（刻意的行为）


def test_every_change_in_a_code_pr_must_have_adversarial_evidence(gated: Path, cli):
    """与 building 门禁**同一条边界**：本 PR 落了实现 ⇒ 本 PR 触及的**每个** change 都要对抗轮证据。

    这是**刻意的**（「一个 PR 推进一个 change」前提）：`OTHER` 自身无实现，但因本 PR 落了代码，
    它也被要求——要免除就把 change 拆到单独 PR。**不提供**豁免名单。
    """
    commit_content(gated, "impl-a", spec_writes=(("src/a.py", "x = 1\n"),))
    write_review(gated, "impl-a", stage="grill")
    write_review(gated, "impl-a", stage="building")
    write_review(gated, "impl-a", stage=STAGE)

    commit_content(gated, OTHER)  # 纯文档 change
    write_review(gated, OTHER, stage="grill")
    commit_all(gated, "两个 change")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    # 断言**整句**（两段独立子串可被两个不同 finding 各自满足——review-loop R1 的 N-6①）
    assert f"changes/{OTHER}：无 stage={STAGE}" in err
    # 有实现的那个**不该**被点名（它有对抗轮证据）
    assert f"changes/impl-a：无 stage={STAGE}" not in err


# ---------------------------------------------------------------- 审阅须在最终 revision 之后（回归）


def test_changing_the_design_after_the_adversarial_round_is_stale(gated: Path, cli):
    """**这半已有**（`contract._check_git_span`）：对抗轮之后再改 `design.md` ⇒ 判 stale。

    ⚠️ 这条同时钉住 R-new-2 的**边界**：`design.md` 的**内容**没有被任何 manifest 哈希绑定
    （`HASHED_ARTIFACTS` 只有 `tasks.md` / `specs`），所以「改动落在 manifest 的 `head_sha`
    **之后**」才是它唯一能被发现的时机——本用例正是那个时机。
    """
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="building")
    write_review(gated, CHANGE, stage=STAGE)
    commit_all(gated, "内容 + 三份证据")

    _green(check(gated, cli))

    write_artifact(
        gated,
        f"openspec/changes/{CHANGE}/design.md",
        "# Design: add-x\n\n对抗轮之后又改了一行（收敛被认为结束了，其实没有）。\n",
    )
    commit_all(gated, "对抗轮之后改 design")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "审阅的是旧 revision" in err


# ---------------------------------------------------------------- 诚实边界（Q2 甲）：空报告也合格


def test_empty_report_body_is_accepted(gated: Path, cli):
    """**已知上限，故意钉住**：`verify_body=False` ⇒ 零字节报告 + 合法 manifest 也判合格。

    spec 边界声明 4 与 README 都承诺了这条；没有用例钉它，将来「顺手补个正文校验」会**无声**
    变成行为变更（且本仓的对外表述会立刻说谎）。
    """
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="building")
    write_review(gated, CHANGE, stage=STAGE, report_body="")
    commit_all(gated, "内容 + 一份**空**的对抗报告")

    _green(check(gated, cli))


def test_report_whose_verdict_is_changes_requested_is_accepted(gated: Path, cli):
    """spec 的 Scenario「结论是 `CHANGES_REQUESTED` 也能通过」的**字面**用例。

    逻辑上已被上面那条空正文用例**严格覆盖**（正文一个字节都不读 ⇒ 三种写法不可区分），
    但让 Scenario 与用例一一对应更省事（review-loop R1 的 N-5①）。
    """
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="building")
    write_review(
        gated,
        CHANGE,
        stage=STAGE,
        report_body="# 对抗验证\n\n## Verdict\n**CHANGES_REQUESTED**\n\n三轮封顶，交人判断。\n",
    )
    commit_all(gated, "内容 + 结论为 CHANGES_REQUESTED 的对抗报告")

    _green(check(gated, cli))


# ---------------------------------------------------------------- 参数化轴（覆写必须被钉住）


def test_adversarial_stage_is_configurable(repo: Path, cli, read_json):
    """`policy.evidence.grill_adversarial_stage` **可覆写**——文档承诺的轴必须有测试钉住
    （`building` 那条曾因缺这条用例被变异检查逃逸）。"""
    import json

    cli("init", "--root", str(repo))
    policy_path = repo / C.POLICY_PATH
    doc = read_json(policy_path)
    doc["evidence"]["grill_adversarial_stage"] = "design-adversarial"
    policy_path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    commit_all(repo, "把 grill_adversarial_stage 换成 design-adversarial")
    git(repo, "checkout", "-q", "-b", "feature")

    commit_content(repo, CHANGE, spec_writes=CODE_WRITE)
    write_review(repo, CHANGE, stage="grill")
    write_review(repo, CHANGE, stage="building")
    write_review(repo, CHANGE, stage=STAGE)  # 只有默认 stage 的证据 ⇒ 应红
    commit_all(repo, "内容 + 三份证据（用默认 stage）")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "stage=design-adversarial" in err  # 点名的是**配置**的那个 stage

    write_review(repo, CHANGE, stage="design-adversarial")  # 补配置 stage 的证据 ⇒ 转绿
    commit_all(repo, "补 stage=design-adversarial 的证据")
    code, _, err = check(repo, cli)
    assert code == C.EXIT_PASS, err


# ---------------------------------------------------------------- 共用同一实现（不写第二份）


def test_plain_report_without_grill_sections_is_accepted(repo: Path, cli):
    """对抗轮的 manifest 绑一份**没有** grill 式小节的普通报告也应通过——
    `verify_body=False` 不得把 grill 专有的正文判据泄漏过来（共用助手、两种深度）。"""
    from witnessloop import evidence

    commit_content(repo, CHANGE, spec_writes=CODE_WRITE)
    write_review(
        repo,
        CHANGE,
        stage=STAGE,
        report_body="# 对抗验证\n\n## Verdict\n**PASS**\n\n（没有 Confirmed Decisions 等小节）\n",
    )

    findings = evidence.stage_manifest_findings_in_change(
        repo / "openspec" / "changes" / CHANGE,
        stage=STAGE,
        reason="（对抗轮的理由）",
    )
    assert findings == []


def test_plain_report_passes_through_the_cli_too(gated: Path, cli):
    """把上一条从「helper 的默认值」升级成**接线**用例：同样一份没有 grill 式小节的报告，
    走完整 `check` 也应绿。

    Why：只调 helper 的那条在「把 `verify_body` 传成 `True`」的变异下**不红**（review-loop R1 的
    M3 实测）——真正拦住「grill 正文判据泄漏到对抗轮」的是走 CLI 的用例。
    """
    commit_content(gated, CHANGE, spec_writes=CODE_WRITE)
    write_review(gated, CHANGE, stage="grill")
    write_review(gated, CHANGE, stage="building")
    write_review(
        gated,
        CHANGE,
        stage=STAGE,
        report_body="# 对抗验证\n\n## Verdict\n**PASS**\n\n（没有 `## Confirmed Decisions` 等小节）\n",
    )
    commit_all(gated, "内容 + 无 grill 式小节的对抗报告")

    _green(check(gated, cli))
