"""B1 负向 / B2 / B3：`check` 侧的 grill 证据正文校验（回归审阅 Issue 1 补齐）。

`tests/test_evidence.py` 覆盖**纯函数**层；本文件覆盖 `check` 的**接线**层——
「正文不合格 / stage 缺失 / stage 拼错」三种情形都必须**真红**且可诊断。
"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all
from helpers import check, commit_content, write_review

CHANGE = "add-x"


def test_check_red_when_the_grill_report_body_is_incomplete(gated: Path, cli):
    """B1 负向：正文不合格（空壳）**即使被 manifest 绑上**，`check` 也必须红。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill", report_body="PASS\n\n看着不错。\n")
    commit_all(gated, "证据")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "Confirmed Decisions" in err


def test_check_red_when_the_stage_field_is_missing(gated: Path, cli):
    """B2：`stage` 已纳入必填字段——缺它就红。"""
    commit_content(gated, CHANGE)
    manifest = write_review(gated, CHANGE, stage="grill")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    del doc["stage"]
    manifest.write_text(json.dumps(doc), encoding="utf-8")
    commit_all(gated, "证据：manifest 缺 stage")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "缺字段" in err and "stage" in err


def test_check_names_the_existing_stage_so_a_typo_is_diagnosable(gated: Path, cli):
    """B3 / spec Scenario「stage 拼错可诊断」：`stage=grills` ⇒ 红且**点名现有 stage**。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grills")
    commit_all(gated, "证据：stage 拼错")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "现有 stage：grills" in err


def test_check_names_a_byte_bad_manifest_and_does_not_crash(gated: Path, cli):
    """C8（R2 N1）：`check` 的 manifest 读点在 `contract.py`（`checkcmd.py:75` 先于 `:78` 的 `evidence`）。

    字节坏必须**干净红**（与 JSON 坏同归）且**点名该文件**——不能是崩溃（入口兜底会把崩溃也变成非 0，
    所以只断言退出码不够：必须断言**是那条 finding**、且**不是**入口的「内部错误」）。
    """
    commit_content(gated, CHANGE)
    manifest = write_review(gated, CHANGE, stage="grill")
    manifest.write_bytes(b'{"stage": "grill", "broken": "\xff\xfe"}')
    commit_all(gated, "证据：manifest 字节坏")

    code, _, err = check(gated, cli)
    assert code == C.EXIT_FAIL
    assert "manifest 无法解析" in err
    assert "grill.manifest.json" in err
    assert "内部错误" not in err  # 崩到入口兜底 = 不算「同归」，用例须排除


def test_check_stays_fail_closed_on_an_undecodable_report(gated: Path, cli):
    """spec「崩溃兜底不改变 `check` 的退出码语义」：报告读不出 ⇒ 仍**非 0**（CI 锚 fail-closed）。"""
    commit_content(gated, CHANGE)
    write_review(gated, CHANGE, stage="grill")
    (gated / "openspec" / "changes" / CHANGE / "reviews" / "grill-review.md").write_bytes(
        b"# Grill\n\xff\xfe"
    )
    commit_all(gated, "证据：报告字节坏")

    code, _, _ = check(gated, cli)
    assert code != C.EXIT_PASS
