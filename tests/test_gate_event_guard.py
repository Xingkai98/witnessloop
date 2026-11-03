"""issue #48：reusable gate 只接受 ``pull_request`` 事件。

`push` / `schedule` 下 ``github.base_ref`` 为空，base 可能不可解析或与 head 相同；
#45 起零变更是 ``EXIT_EMPTY(5)``（无操作、非通过），不是通过。gate 必须在跑
``check`` 之前给出**决定性**提示，而不是让使用者去猜一条隐晦的红。

测试分三层：

1. **脚本单测**：直接 ``sh scripts/gate-event-guard.sh``，只读 ``GITHUB_EVENT_NAME``；
2. **YAML 接线**：守卫 checkout / 守卫 step 的位置、取值与 adopter tests 的 ``if``；
3. **行为级**：把守卫 step 的 ``run:`` 原文交给真 ``sh``（伪造检出目录），
   断言放行 / 拒绝 / 清理 / 退出码透传。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from witnessloop import constants as C

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / ".github/workflows/gate.yml"
SCRIPT = REPO_ROOT / "scripts/gate-event-guard.sh"
DOCS = (REPO_ROOT / "docs/gate.md", REPO_ROOT / "README.md")

_NON_PR_EVENTS = ["push", "schedule", "pull_request_target", ""]

#: 用户要求文案说清的三件事（用稳定的关键词，不钉整句）。
_REQUIRED_HINTS = ("pull_request", "零变更", "EXIT_EMPTY", "--allow-empty", "不要")


# ---------------------------------------------------------------- 脚本单测

def _run_script(event: str | None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("GITHUB_EVENT_NAME", None)
    if event is not None:
        env["GITHUB_EVENT_NAME"] = event
    return subprocess.run(
        ["sh", str(SCRIPT)], env=env, capture_output=True, text=True
    )


def test_guard_script_exists_and_is_testable():
    assert SCRIPT.is_file(), "issue #48 要求守卫逻辑住在可单测的 scripts/ 脚本里"
    assert SCRIPT.read_text(encoding="utf-8").startswith("#!/bin/sh")


def test_pull_request_is_allowed():
    result = _run_script("pull_request")

    assert result.returncode == 0, result.stderr
    assert "::error::" not in result.stderr


@pytest.mark.parametrize("event", _NON_PR_EVENTS)
def test_non_pr_events_are_rejected_with_actionable_hints(event: str):
    result = _run_script(event)

    assert result.returncode != 0
    for needle in _REQUIRED_HINTS:
        assert needle in result.stderr, f"缺少提示 {needle!r}：\n{result.stderr}"
    assert "PR 区间" in result.stderr or "目标分支" in result.stderr
    if event:
        assert event in result.stderr, "应点名当前事件"


def test_unset_event_is_rejected():
    result = _run_script(None)

    assert result.returncode != 0
    assert "GITHUB_EVENT_NAME" in result.stderr
    assert "无法判断" in result.stderr or "为空" in result.stderr


# ---------------------------------------------------------------- YAML 接线

def _steps() -> list[dict]:
    return yaml.safe_load(GATE.read_text(encoding="utf-8"))["jobs"]["check"]["steps"]


def _step_by_name(name: str) -> dict:
    matches = [s for s in _steps() if s.get("name") == name]
    assert len(matches) == 1, f"gate.yml 里名为 {name!r} 的 step 应恰好一个"
    return matches[0]


def _guard_checkout_step() -> dict:
    matches = [
        s
        for s in _steps()
        if str(s.get("uses", "")).startswith("actions/checkout")
        and s.get("with", {}).get("path") == ".witnessloop-gate"
    ]
    assert len(matches) == 1, "守卫脚本的 checkout step 应恰好一个"
    return matches[0]


def _caller_checkout_step() -> dict:
    matches = [
        s
        for s in _steps()
        if str(s.get("uses", "")).startswith("actions/checkout")
        and s.get("with", {}).get("path") is None
    ]
    assert len(matches) == 1, "caller 的 checkout step 应恰好一个（无 path）"
    return matches[0]


def test_guard_checkout_and_step_run_before_the_caller_checkout_and_check():
    steps = _steps()
    names = [s.get("name") for s in steps]

    guard_index = names.index("gate event guard")
    checkout_index = steps.index(_guard_checkout_step())
    caller_index = steps.index(_caller_checkout_step())
    check_index = names.index("witnessloop check")

    assert checkout_index < guard_index < caller_index < check_index
    # 包来源自报行仍由第一个 step 产出（既有契约）。
    assert steps[0].get("id") == "wl-ref"


def test_guard_checkout_uses_the_resolved_ref_from_this_repo():
    step = _guard_checkout_step()
    with_ = step["with"]

    assert with_["repository"] == C.REPO_SLUG
    assert with_["ref"] == "${{ steps.wl-ref.outputs.ref }}"
    assert with_["path"] == ".witnessloop-gate"
    assert with_["fetch-depth"] == 1
    assert with_["persist-credentials"] is False


def test_guard_step_binds_the_event_name_and_calls_the_script():
    step = _step_by_name("gate event guard")

    assert step["env"]["GITHUB_EVENT_NAME"] == "${{ github.event_name }}"
    assert step["env"]["WL_REF"] == "${{ steps.wl-ref.outputs.ref }}"
    assert "scripts/gate-event-guard.sh" in step["run"]
    assert "${{" not in step["run"], "run 里不得做解析期插值"
    assert "rm -rf .witnessloop-gate" in step["run"], "守卫后应清理临时检出"


def test_adopter_tests_only_skip_when_the_guard_failed():
    """守卫**失败** ⇒ 不再跑测试；守卫成功 / 被跳过（更早的步骤失败）⇒ 维持旧行为。

    用 ``!= 'failure'`` 而不是 ``== 'success'``：`check` 失败时守卫仍是 success ⇒
    测试照常跑（既有语义）；而更早的步骤失败导致守卫 skipped 时，也不额外改变
    adopter tests 的旧行为。
    """
    step = next(s for s in _steps() if "witnessloop-tests" in str(s.get("env", {}).values()))

    assert "steps.wl-event-guard.outcome != 'failure'" in step["if"]
    assert "!cancelled()" in step["if"]


# ---------------------------------------------------------------- 行为级

def _run_guard_step(tmp_path: Path, event: str) -> subprocess.CompletedProcess:
    step = _step_by_name("gate event guard")
    target = tmp_path / ".witnessloop-gate/scripts/gate-event-guard.sh"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    env = dict(os.environ)
    for key, value in step.get("env", {}).items():
        env[str(key)] = str(value)
    env["GITHUB_EVENT_NAME"] = event
    return subprocess.run(
        ["sh", "-c", step["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_yaml_guard_step_allows_pull_request_and_cleans_up(tmp_path: Path):
    result = _run_guard_step(tmp_path, "pull_request")

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / ".witnessloop-gate").exists()


def test_yaml_guard_step_rejects_push_and_propagates_the_exit_code(tmp_path: Path):
    result = _run_guard_step(tmp_path, "push")

    assert result.returncode != 0
    assert "::error::" in result.stderr
    assert "零变更" in result.stderr
    assert not (tmp_path / ".witnessloop-gate").exists(), "失败路径也必须清理临时目录"


def test_yaml_guard_step_fails_closed_when_the_script_is_missing(tmp_path: Path):
    """显式 `witnessloop-ref` 指到没有该脚本的旧 ref 时：响亮 fail-closed，不跳过守卫。"""
    step = _step_by_name("gate event guard")
    env = dict(os.environ)
    for key, value in step.get("env", {}).items():
        env[str(key)] = str(value)
    env["GITHUB_EVENT_NAME"] = "pull_request"
    # 故意不创建 .witnessloop-gate/scripts/gate-event-guard.sh

    result = subprocess.run(
        ["sh", "-c", step["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "无法取得守卫脚本" in result.stderr
    assert not (tmp_path / ".witnessloop-gate").exists()


# ---------------------------------------------------------------- 文档

def test_docs_explain_why_non_pr_triggers_are_rejected():
    for path in DOCS:
        text = path.read_text(encoding="utf-8")
        assert "pull_request" in text, f"{path} 未说明只接受 pull_request"
        assert "--allow-empty" in text, f"{path} 未说明正确的零变更放行方式"
        assert "零变更" in text, f"{path} 未解释零变更不是通过"
