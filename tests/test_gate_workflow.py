"""gate.yml（reusable workflow）与本仓常量的一致性。

`init` 写的 caller 引用 ``<REPO_SLUG>/.github/workflows/gate.yml@v1``——
本文件保证那个引用指向一个真实存在、可被 workflow_call 的薄文件。
"""

from __future__ import annotations

from pathlib import Path

import yaml

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


def test_gate_pins_the_pr_head_for_checkout():
    """钉住 gate.yml 的 `ref:` 表达式——被检 head 必须是 PR 自己的 head。

    reviewer R3 §4-2：原先只 grep 子串，把这行删掉（或被改回默认检出
    test-merge commit）测试都不会红。这里解析 YAML，断言它落在
    **checkout 步骤的 `with.ref`** 这个具体位置、且是那个具体值。
    """
    doc = yaml.safe_load(GATE.read_text(encoding="utf-8"))
    steps = doc["jobs"]["check"]["steps"]
    checkout = next(
        s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")
    )
    assert checkout["with"]["ref"] == (
        "${{ github.event.pull_request.head.sha || github.sha }}"
    )
    # 浅克隆会让 merge-base 求不出来，而 check 对求不出的 base 是 fail-closed
    assert checkout["with"]["fetch-depth"] == 0


def test_caller_ref_matches_this_repo():
    text = GATE.read_text(encoding="utf-8")
    assert C.REPO_SLUG in text
    assert C.DEFAULT_GATE_REF == f"{C.REPO_SLUG}/.github/workflows/gate.yml@v1"
