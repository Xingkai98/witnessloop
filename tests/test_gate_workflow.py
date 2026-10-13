"""gate.yml（reusable workflow）与本仓常量的一致性。

`init` 写的 caller 引用 ``<REPO_SLUG>/.github/workflows/gate.yml@v1``——
本文件保证那个引用指向一个真实存在、可被 workflow_call 的薄文件。

后半段是 change adopter-test-gate 的 C 组：门禁里新增的**测试执行点**那一步。
断言一律**解析 YAML 后看位置与取值**（grep 子串钉不住「这行在哪个 step 里」）。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from witnessloop import constants as C
from witnessloop import initcmd, policy as policy_mod

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


# ---------------------------------------------------------------------------
# C 组：门禁里的**测试执行点**步骤（change adopter-test-gate / design D1、D2、D5）
# ---------------------------------------------------------------------------

def _gate_doc() -> dict:
    return yaml.safe_load(GATE.read_text(encoding="utf-8"))


def _steps() -> list[dict]:
    return _gate_doc()["jobs"]["check"]["steps"]


def _adopter_tests_step(steps: list[dict] | None = None) -> dict:
    steps = _steps() if steps is None else steps
    matches = [s for s in steps if "witnessloop-tests" in str(s.get("env", {}).values())]
    assert len(matches) == 1, (
        f"gate.yml 里读命令文件的步骤应恰好一个，实得 {len(matches)}"
    )
    return matches[0]


def test_adopter_tests_step_is_in_the_same_job_as_check():
    """D1 甲：测试与 `check` **同一个 job** ⇒ 复用已 required 的 `gate / check`。"""
    step = _adopter_tests_step()
    assert step in _steps()
    names = [s.get("name") for s in _steps()]
    assert "witnessloop check" in names


def test_adopter_tests_step_reads_the_file_at_runtime_not_by_interpolation():
    """D5/CRQ-10：**路径**经 `env:` 传、命令在 `run:` 里运行时读。

    `${{ }}` 插值发生在**解析期** ⇒ 对文件内容做插值等于把接入方内容当 workflow 源码。
    """
    step = _adopter_tests_step()
    run = step["run"]

    assert step["env"]["WL_TESTS_FILE"] == C.ADOPTER_TESTS_PATH
    assert "${{" not in run, "run 里不得出现 ${{ }} 插值"
    # 命令从**变量**读出后交给 sh；哨兵只以 env 变量的形式出现（不手抄字面量）
    assert "cat" in run and "sh -c" in run
    assert C.ADOPTER_TESTS_SENTINEL not in run


def test_adopter_tests_step_skips_when_missing_or_unwired():
    """C1：文件**缺失 _或_ 内容含哨兵** ⇒ 跳过。

    原稿只写了「缺失 ⇒ 跳过」——哨兵会被 `sh` 当命令执行，症状是 `sh: Syntax error`
    而不是清晰文案（实测 exit 2）。
    """
    run = _adopter_tests_step()["run"]

    assert '-f "$WL_TESTS_FILE"' in run  # 缺失
    assert '"$WL_TESTS_SENTINEL"' in run  # 未接线（子串口径，与 check 一致）
    assert "exit 0" in run


def test_adopter_tests_step_runs_after_check_with_bang_cancelled():
    """C3/D2：`check` 在前；测试步骤 `if: ${{ !cancelled() }}`。

    理由（不是原稿那个被实测证伪的「`always()` 掩蔽失败」）：① 门禁红时最需要测试反馈；
    ② run 被取消时不必再跑一遍测试。
    """
    steps = _steps()
    names = [s.get("name") for s in steps]
    check_index = names.index("witnessloop check")
    tests_step = _adopter_tests_step(steps)
    tests_index = steps.index(tests_step)

    assert check_index < tests_index
    assert tests_step["if"] == "${{ !cancelled() }}"


def test_gate_job_name_is_unchanged():
    """C5：接入方已把 `gate / check` 勾成 required ⇒ 改名 = 静默失效。"""
    assert list(_gate_doc()["jobs"]) == ["check"]
    # `gate / check` 的前半来自 caller 里的 job 名，同样是契约。
    assert "\n  gate:\n" in initcmd.caller_workflow(C.DEFAULT_GATE_REF)


def test_path_and_sentinel_are_single_sourced():
    """X3：**三处同源**——`constants` / `gate.yml` 字面量 / policy 的默认路径。

    口径分裂的后果是「`check` 判红、门禁却静默跳过」（或反过来）。
    路径刻意**不是**策略旋钮：出厂 policy doc 不物化 `tests` 键、缺省语义 = 声明
    ⇒ 两侧判的都是 `constants` 里那一个常量。
    """
    env = _adopter_tests_step()["env"]

    assert env["WL_TESTS_FILE"] == C.ADOPTER_TESTS_PATH
    assert env["WL_TESTS_SENTINEL"] == C.ADOPTER_TESTS_SENTINEL

    assert "tests" not in policy_mod.default_policy_doc()
    assert (
        policy_mod.Policy.from_doc(policy_mod.default_policy_doc()).tests_disabled
        is False
    )
