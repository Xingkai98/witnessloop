"""gate.yml（reusable workflow）与本仓常量的一致性。

`init` 写的 caller 引用 ``<REPO_SLUG>/.github/workflows/gate.yml@v1``——
本文件保证那个引用指向一个真实存在、可被 workflow_call 的薄文件。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / ".github/workflows/gate.yml"


def test_gate_workflow_exists():
    assert GATE.is_file()


def test_gate_workflow_is_reusable_and_thin():
    text = GATE.read_text(encoding="utf-8")
    assert "workflow_call" in text  # 必须可被 caller 引用
    # 薄：真正的门禁逻辑在 CLI 里，workflow 只负责把 CLI 跑起来
    assert "witnessloop check" in text
    assert "fetch-depth: 0" in text  # 浅克隆会让 merge-base 求不出来


def test_caller_ref_matches_this_repo():
    text = GATE.read_text(encoding="utf-8")
    assert C.REPO_SLUG in text
    assert C.DEFAULT_GATE_REF == f"{C.REPO_SLUG}/.github/workflows/gate.yml@v1"
