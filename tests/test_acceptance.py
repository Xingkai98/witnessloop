"""F 组：design §7 的 acid test 负例（在 M1 门禁层范围内可跑的部分）。

F1 端到端绿 · F2 手写放行事件不拦（防漂移不防伪造）· F3 证据漂移报错 ·
F4 不接入报「未接入」· F5 init→uninit 往返。
F3 在 M1 里的同构形态是「artifact 与 manifest 漂移」（交互层要到 M2 才存在）。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all, git
from helpers import (
    change_dir,
    check,
    commit_content,
    commit_evidence,
    write_change,
    write_event,
    write_review,
)

SPEC = "openspec/specs/retry/spec.md"


def _write_spec(repo: Path) -> None:
    path = repo / SPEC
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# canonical spec: retry\n", encoding="utf-8")


def test_f1_end_to_end_green(repo: Path, cli):
    """init → change → grill → 实现 → review-loop 通过 → check 绿。"""
    assert cli("init", "--root", str(repo))[0] == C.EXIT_PASS
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "add-retry-policy")

    change_id = "add-retry-policy"
    commit_content(repo, change_id, spec_writes=((SPEC, "# canonical spec: retry\n"),))
    # 设计对抗阶段 + 实现审阅阶段都通过；spec delta 落地带解释事件。
    commit_evidence(
        repo, change_id, stages=("grill", "building"), events=(SPEC,)
    )

    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, err
    assert "通过" in out


def test_f2_handwritten_allow_event_is_not_blocked(repo: Path, cli):
    """负例 (a)：手写一行放行事件提交 → **不拦**。

    这是 design §2 明写的诚实边界：默认只防漂移、不防蓄意伪造。
    本测试把这个边界**钉成契约**——若哪天它开始报错，说明话术要同步改。
    """
    assert cli("init", "--root", str(repo))[0] == C.EXIT_PASS
    commit_all(repo, "接入")
    git(repo, "checkout", "-q", "-b", "sneaky")

    commit_content(repo, "sneaky", spec_writes=((SPEC, "# canonical spec: retry\n"),))
    # agent 自己手写一行「人类批准」——没有任何外部锚能证伪它。
    write_review(repo, "sneaky")
    write_event(repo, "sneaky", SPEC, approved_by="user:totally-real-human")
    commit_all(repo, "自称已获批")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_PASS, err


def test_f3_evidence_drift_fails_loudly(gated: Path, cli):
    """负例 (b)：证据与 artifact 漂移 → 报错，而不是双绿。"""
    write_change(gated, "add-x")
    write_review(gated, "add-x")
    (change_dir(gated, "add-x") / "tasks.md").write_text(
        "# tasks\n\n- [x] manifest 之后再改的\n", encoding="utf-8"
    )
    commit_all(gated, "漂移")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "tasks_hash 不匹配" in err
    assert "通过" not in out


def test_f4_no_init_reports_not_onboarded(repo: Path, cli):
    """负例 (c)：不跑 init → 报「未接入」，不是静默通过。"""
    code, _, err = check(repo, cli)
    assert code == C.EXIT_NOT_ONBOARDED
    assert "未接入" in err


def test_f5_init_uninit_round_trip(repo: Path, cli):
    """负例 (d)：init → uninit 回滚往返，工作树回到原点。"""
    before = git(repo, "status", "--porcelain")
    assert cli("init", "--root", str(repo))[0] == C.EXIT_PASS
    assert git(repo, "status", "--porcelain") != before

    assert cli("uninit", "--root", str(repo))[0] == C.EXIT_PASS
    assert git(repo, "status", "--porcelain") == before
