"""C 组：`witnessloop guard`（change grill-evidence-gate / D3–D5）。

本地守卫：写代码前缺 grill 证据就拦。判定与 `check` 共用 `evidence.py`。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import witnessloop
from witnessloop import constants as C

from conftest import commit_all, git
from helpers import commit_content, write_review

CHANGE = "add-x"

#: `guard` 的「拦住」= EXIT_FAIL(1)——**不是** 2（2 = argparse 用法错误；见 Issue 3 修复）。
BLOCKED = C.EXIT_FAIL
REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD_SH = REPO_ROOT / "plugin" / "hooks" / "guard.sh"


def _guard(cli, repo: Path, *paths: str, change: str | None = None):
    argv = ["guard", "--root", str(repo)]
    for path in paths:
        argv += ["--path", path]
    if change:
        argv += ["--change", change]
    return cli(*argv)


def _onboarded_on_branch(repo: Path, cli, branch: str) -> None:
    assert cli("init", "--root", str(repo))[0] == C.EXIT_PASS
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", branch)


def test_blocks_a_code_write_without_grill_evidence(repo: Path, cli):
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)  # change 目录在，但 reviews/ 里没有 grill 证据

    code, _, err = _guard(cli, repo, "src/x.py")
    assert code == BLOCKED
    assert "grill 证据不完备" in err


def test_allows_a_code_write_when_grill_evidence_is_complete(repo: Path, cli):
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)
    write_review(repo, CHANGE, stage="grill")  # 合格的 grill 决策记录 + manifest

    code, _, _ = _guard(cli, repo, "src/x.py")
    assert code == C.EXIT_PASS


def test_documentation_writes_are_exempt(repo: Path, cli):
    """豁免文档是**死锁防线**：否则永远产不出证据。"""
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)

    code, _, err = _guard(cli, repo, f"openspec/changes/{CHANGE}/design.md")
    assert code == C.EXIT_PASS
    assert "豁免" in err


def test_branch_segment_that_is_not_an_existing_change_fails_open(repo: Path, cli):
    """`fix/login-timeout` 的首段不是 change 目录 → 按「推不出」处理，**不拦**。"""
    _onboarded_on_branch(repo, cli, "fix/login-timeout")
    commit_content(repo, CHANGE)

    code, _, err = _guard(cli, repo, "src/auth.py")
    assert code == C.EXIT_PASS
    assert "推不出" in err


def test_explicit_change_overrides_the_branch(repo: Path, cli):
    _onboarded_on_branch(repo, cli, "feature")  # 分支推不出任何 change
    commit_content(repo, CHANGE)

    code, _, _ = _guard(cli, repo, "src/x.py", change=CHANGE)
    assert code == BLOCKED


def test_change_env_overrides_the_branch(repo: Path, cli, monkeypatch):
    """C6：`WITNESSLOOP_CHANGE` 优先于分支名（分支推不出，靠 env 命中 change）。"""
    _onboarded_on_branch(repo, cli, "feature")
    commit_content(repo, CHANGE)
    monkeypatch.setenv("WITNESSLOOP_CHANGE", CHANGE)

    code, _, _ = _guard(cli, repo, "src/x.py")
    assert code == BLOCKED


def test_paths_outside_require_change_for_are_exempt(repo: Path, cli):
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)

    code, _, _ = _guard(cli, repo, "tests/test_x.py", "docs/x.md")
    assert code == C.EXIT_PASS


def test_not_onboarded_does_not_block(repo: Path, cli):
    code, _, err = _guard(cli, repo, "src/x.py")
    assert code == C.EXIT_NOT_ONBOARDED
    assert "未接入" in err


def test_skip_env_is_an_escape_hatch(repo: Path, cli, monkeypatch):
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)
    monkeypatch.setenv("WITNESSLOOP_SKIP_GUARD", "1")

    code, _, err = _guard(cli, repo, "src/x.py")
    assert code == C.EXIT_PASS
    assert "已跳过" in err


def test_no_paths_means_nothing_to_guard(repo: Path, cli):
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)

    code, _, _ = _guard(cli, repo)
    assert code == C.EXIT_PASS


# --------------------------------------------- shim 的退出码映射（回归审阅 Issue 3）


def _run_shim(tmp_path: Path, *, cli_exit: int | None, file_path: str = "src/x.py") -> int:
    """把一个假 `witnessloop` 放到 PATH 首位，跑 shim，返回它的退出码。

    ``cli_exit=None`` 表示 PATH 上**没有** witnessloop（模拟「没装 CLI」）。
    """
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    if cli_exit is not None:
        fake = fake_bin / "witnessloop"
        fake.write_text(f"#!/bin/sh\nexit {cli_exit}\n", encoding="utf-8")
        fake.chmod(0o755)
    payload = json.dumps({"tool_input": {"file_path": file_path}, "cwd": str(tmp_path)})
    proc = subprocess.run(
        [shutil.which("bash") or "/bin/bash", str(GUARD_SH)],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"},
    )
    return proc.returncode


def test_shim_maps_guard_block_to_the_hosts_block_code(tmp_path: Path):
    assert _run_shim(tmp_path, cli_exit=C.EXIT_FAIL) == 2


def test_shim_does_not_treat_a_stale_cli_usage_error_as_block(tmp_path: Path):
    """回归审阅 Issue 3：旧版 CLI 不认识 `guard` ⇒ argparse 退 **2**。

    直传会被 CC 当成 block ⇒ **每个 Write/Edit 全被拦**；映射后必须放行。
    """
    assert _run_shim(tmp_path, cli_exit=C.EXIT_USAGE) == 0


def test_shim_allows_when_the_cli_is_missing(tmp_path: Path):
    """二进制不在 PATH（没装 CLI）→ 非 0/1 退出 → 放行（fail-open；R8）。"""
    assert _run_shim(tmp_path, cli_exit=None) == 0


def test_shim_allows_when_the_event_has_no_file_path(tmp_path: Path):
    assert _run_shim(tmp_path, cli_exit=C.EXIT_FAIL, file_path="") == 0


def test_shim_allows_the_internal_error_code(tmp_path: Path):
    """issue #9 / D2：`guard` 崩溃走 `EXIT_INTERNAL`(4) ⇒ shim **放行**（不自造 block）。"""
    assert _run_shim(tmp_path, cli_exit=C.EXIT_INTERNAL) == 0


# --------------------------------------------- 崩溃兜底（issue #9 / D1+D3）
# 真崩溃用**真正未预期**的异常触发；可归一的解码失败走下面的读点用例。


def test_guard_survives_an_arbitrary_internal_error(repo: Path, cli, monkeypatch):
    """B1：判定过程中抛未预期异常 ⇒ 经**进程入口**退 `EXIT_INTERNAL`（非 1）。"""
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)
    write_review(repo, CHANGE, stage="grill")

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "witnessloop.evidence.grill_evidence_findings_in_change", boom
    )
    code, _, err = _guard(cli, repo, "src/x.py")
    assert code == C.EXIT_INTERNAL
    assert code != BLOCKED  # 关键：崩溃**绝不能**被当成「拦」
    assert "内部错误" in err


def test_guard_survives_a_broken_submodule_import(repo: Path, cli, monkeypatch):
    """B2：`from witnessloop import guardcmd` 抛 ImportError ⇒ 同一兜底接住。

    只设 `sys.modules[...]=None` **不够**——整份 suite 里 `guardcmd` 早已是 `witnessloop` 的**属性**，
    `from ... import` 会走 `getattr` 而不抛（R3 M4 实测）⇒ 必须同时 `delattr`。
    """
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)
    monkeypatch.setitem(sys.modules, "witnessloop.guardcmd", None)
    monkeypatch.delattr(witnessloop, "guardcmd", raising=False)

    code, _, err = _guard(cli, repo, "src/x.py")
    assert code == C.EXIT_INTERNAL
    assert "内部错误" in err


# --------------------------------------------- 读点归一（D4/D5 · Q1 裁定=甲案）


def test_policy_decode_failure_is_not_a_block(repo: Path, cli):
    """D5：policy 读不出 ⇒ 与「policy 非法」同归 ⇒ **放行**（连受管控范围都读不出 ⇒ 不执行）。"""
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)
    (repo / ".witnessloop" / "policy.json").write_bytes(b'{"schema": "\xff\xfe"}')

    code, _, err = _guard(cli, repo, "src/x.py")
    assert code == C.EXIT_PASS
    assert "policy" in err


def test_byte_bad_manifest_matches_json_bad_manifest(repo: Path, cli):
    """D4-2：**字节坏** manifest 必须与 **JSON 坏** manifest **逐字同归**（不得一半拦一半放）。

    断言**两案输出相等**（而非钉某个字符串）——这才钉得住「同归」。
    """
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)
    write_review(repo, CHANGE, stage="grill")
    manifest = repo / "openspec" / "changes" / CHANGE / "reviews" / "grill.manifest.json"

    manifest.write_bytes(b'{"stage": "grill", "broken": "\xff\xfe"}')
    byte_code, _, byte_err = _guard(cli, repo, "src/x.py")

    manifest.write_text("{ not json", encoding="utf-8")
    json_code, _, json_err = _guard(cli, repo, "src/x.py")

    assert byte_code == json_code == BLOCKED
    assert byte_err == json_err


def test_report_decode_failure_blocks_with_a_clear_message(repo: Path, cli):
    """D4-3（甲案）：报告正文读不出 ⇒ 确定性 verdict（**拦** + 点名报告），**不是**崩溃。"""
    _onboarded_on_branch(repo, cli, f"{CHANGE}/2026-10-11")
    commit_content(repo, CHANGE)
    write_review(repo, CHANGE, stage="grill")
    (repo / "openspec" / "changes" / CHANGE / "reviews" / "grill-review.md").write_bytes(
        b"# Grill\n\xff\xfe"
    )

    code, _, err = _guard(cli, repo, "src/x.py")
    assert code == BLOCKED
    assert "报告无法解码" in err
    assert "Traceback" not in err
