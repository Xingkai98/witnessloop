"""gate.yml（reusable workflow）与本仓常量的一致性。

`init` 写的 caller 引用 ``<REPO_SLUG>/.github/workflows/gate.yml@<ref>``——
本文件保证那个引用指向一个真实存在、可被 workflow_call 的薄文件。

后半段是 change adopter-test-gate 的 C 组：门禁里新增的**测试执行点**那一步。
断言一律**解析 YAML 后看位置与取值**（grep 子串钉不住「这行在哪个 step 里」）。
"""

from __future__ import annotations

import os
import subprocess
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
    # 命令从**文件**读出（重定向 + 变量）后交给 sh；哨兵只以 env 变量的形式出现
    # （不手抄字面量）。
    assert '< "$WL_TESTS_FILE"' in run and "CMD=" in run and 'sh -c "$CMD"' in run
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


# --- 行为级：把 `run:` 原文交给真 `sh` 跑一遍（不是文本断言） -------------------
#
# 审阅 R1 的 I1：上面那几条**文本**断言钉不住语义回归。实测两个逃逸变异
# （保留 `case` 只删它内部的 `exit 0`；把 `sh -c "$CMD"` 挪到守卫之前）当时都
# **477 passed**——而它们会让未接线仓的门禁真的去执行哨兵（`sh: Syntax error`、exit 2）。
# 这一段就是本 change 的核心机制（「测试失败 ⇒ job 失败」），必须有行为级的钉子。
#
# 做法与审阅者手工做的一致：从 `gate.yml` 解析出该 step 的 `run:`，在临时目录里交真 `sh`，
# env 照抄该 step 的 `env:`。

def _run_tests_step(tmp_path: Path, files: dict[str, str]) -> subprocess.CompletedProcess:
    step = _adopter_tests_step()
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return subprocess.run(
        ["sh", "-c", step["run"]],
        cwd=tmp_path,
        env=dict(os.environ, **step["env"]),
        capture_output=True,
        text=True,
    )


def test_step_skips_a_missing_file_with_a_notice(tmp_path: Path):
    result = _run_tests_step(tmp_path, {})

    assert result.returncode == 0, result.stderr
    assert "::notice::" in result.stdout


def test_step_skips_the_sentinel_instead_of_running_it(tmp_path: Path):
    """**M2b/M2c 的杀手**：哨兵态必须 exit 0 **且**打印 notice。

    少了 `exit 0`（或把 `sh -c "$CMD"` 挪到守卫之前），哨兵就会落到 `sh -c`：
    `sh: Syntax error: end of file unexpected`、exit 2 ⇒ 未接线仓的门禁红在一条
    与「没接线」毫无相似之处的语法错误上。
    """
    result = _run_tests_step(
        tmp_path, {C.ADOPTER_TESTS_PATH: C.ADOPTER_TESTS_SENTINEL + "\n"}
    )

    assert result.returncode == 0, result.stderr
    assert "::notice::" in result.stdout
    assert "Syntax error" not in result.stderr


def test_step_is_silent_but_green_on_an_empty_file(tmp_path: Path):
    """空文件 ⇒ exit 0 且**无** notice——这一态只能由 `check` 判（spec 明写）。

    把它钉住，免得有人以为门禁会给「空」兜底。
    """
    result = _run_tests_step(tmp_path, {C.ADOPTER_TESTS_PATH: "   \n\n"})

    assert result.returncode == 0, result.stderr
    assert "::notice::" not in result.stdout


def test_step_runs_a_wired_command(tmp_path: Path):
    result = _run_tests_step(
        tmp_path, {C.ADOPTER_TESTS_PATH: "printf wired > marker\n"}
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "marker").read_text(encoding="utf-8") == "wired"


def test_step_propagates_the_command_exit_code(tmp_path: Path):
    """「测试失败 = 合不了」的全部机制：命令的退出码必须冒到 step（进而 job）。"""
    result = _run_tests_step(tmp_path, {C.ADOPTER_TESTS_PATH: "exit 7\n"})

    assert result.returncode == 7


def test_step_strips_a_trailing_crlf(tmp_path: Path):
    """CRLF（审阅 R1 的 I3）：`check` 的 `strip()` 本来就吃 `\\r`，但 `$(cat)` 只吃 `\\n`
    ⇒ 命令尾会带一个 `\\r`，Windows 编辑器改过该文件的接入方会看到一条与「接线」无关的红
    （`pytest: error: unrecognized arguments: …`、exit 4）。⇒ 门禁侧先 `tr -d '\\r'`。

    判别方式是**留下痕迹的文件名**：带 `\\r` 时命令是 `printf x > marker\\r`，留下的是
    `marker\\r` 而不是 `marker`。
    """
    result = _run_tests_step(
        tmp_path, {C.ADOPTER_TESTS_PATH: "printf x > marker\r\n"}
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "marker").is_file(), "命令尾带了 \\r（换行没被归一）"
    assert not (tmp_path / "marker\r").exists()


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


# ---------------------------------------------------------------------------
# D 组：(B′) 包 ref 的解析 step（用户 2026-10-16 裁定 Q1；design §2 D1）
#
# 机制：`init` 写的 caller 只钉 workflow 文件、**钉不住包**（`gate.yml` 的
# `inputs.witnessloop-ref` 恒为默认值）。修法 (B′)：包 ref 的**缺省**取自
# `job.workflow_sha`（= 被复用的那个 workflow 文件自己的 commit）——
# 跨仓真 CI 探针实证（run 38853369550），`github.workflow_sha` 是**接入方自己**的，
# 用它会在 witnessloop 仓取一个不存在的 commit（全量硬红）。
#
# 这一段是**行为级**的：把 gate.yml 里那个 step 的 `run:` 原文交真 `sh` 跑，
# env 照抄该 step 的 `env:`——文本断言钉不住解析优先级。
# ---------------------------------------------------------------------------

_RESOLVE_ENV_KEYS = {
    "WL_INPUT_REF",
    "WL_WORKFLOW_REPOSITORY",
    "WL_WORKFLOW_SHA",
    "WL_WORKFLOW_REF",
    "WL_REPO_SLUG",
    "WL_FALLBACK_REF",
}


def _fallback_ref() -> str:
    """fail-closed 的落点——**从 gate.yml 自己读**，不在测试里硬编 `"v1"`。

    ⚠️ 硬编的代价实测过（对抗轮 R3 的 M1）：`DEFAULT_GATE_REF` 换 tag 时
    （本 change 的 post-merge 步骤）这些断言会一起红，而红的理由与被测行为无关。
    """
    return str(_resolve_step()["env"]["WL_FALLBACK_REF"])


def _resolve_step() -> dict:
    matches = [s for s in _steps() if s.get("id") == "wl-ref"]
    assert len(matches) == 1, (
        f"gate.yml 里解析 witnessloop 包 ref 的 step 应恰好一个（按 id 找），实得 {len(matches)}"
    )
    return matches[0]


def _run_resolve(tmp_path: Path, **overrides: str) -> tuple[str, str]:
    """把解析 step 交真 `sh` 跑一遍 → `(解析出的 ref, stdout)`。"""
    step = _resolve_step()
    env = dict(os.environ)
    # 两个「常量」从 YAML 里取（由 test_resolve_step_binds_the_right_contexts 钉其值）
    env["WL_REPO_SLUG"] = str(step["env"]["WL_REPO_SLUG"])
    env["WL_FALLBACK_REF"] = str(step["env"]["WL_FALLBACK_REF"])
    env.update(
        {
            "WL_INPUT_REF": "",
            "WL_WORKFLOW_REPOSITORY": "",
            "WL_WORKFLOW_SHA": "",
            "WL_WORKFLOW_REF": "",
        }
    )
    env.update(overrides)
    out_path = tmp_path / "github_output"
    out_path.write_text("", encoding="utf-8")
    env["GITHUB_OUTPUT"] = str(out_path)
    proc = subprocess.run(
        ["sh", "-c", step["run"]], env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    ref = ""
    for line in out_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("ref="):
            ref = line[len("ref=") :]
    return ref, proc.stdout


def test_resolve_step_is_the_first_step():
    """D3：后面的步骤（含失败的）之后也要能在日志里看见本次用的 ref。"""
    assert _steps()[0].get("id") == "wl-ref"


def test_resolve_step_binds_the_right_contexts():
    """(B′) 的基石：**`job.*`** 而不是 `github.*`。

    探针实测 `github.workflow_ref` / `github.workflow_sha` 指 **caller**（接入方自己的），
    只有 `job.workflow_*` 指被复用的那个文件。绑错了 ⇒ `uvx` 去 witnessloop 仓取一个
    不存在的 ref ⇒ 全量硬红。这条断言就是防那个绑错。
    """
    step = _resolve_step()
    env = step["env"]

    assert env["WL_INPUT_REF"] == "${{ inputs.witnessloop-ref }}"
    assert env["WL_WORKFLOW_REPOSITORY"] == "${{ job.workflow_repository }}"
    assert env["WL_WORKFLOW_SHA"] == "${{ job.workflow_sha }}"
    assert env["WL_WORKFLOW_REF"] == "${{ job.workflow_ref }}"
    assert set(env) == _RESOLVE_ENV_KEYS
    # run 里不得出现 ${{ }} 插值（与 adopter tests 那一步同口径：解析期插值 = 把外来的
    # 字符串当 workflow 源码）。同时也保证测试能把 run 原文直接交 sh 跑。
    assert "${{" not in step["run"]


def test_resolve_constants_match_the_single_source():
    """接受判据（REPO_SLUG）与 fail-closed 的**兜底 ref** 必须与 `constants.py` 同源。"""
    env = _resolve_step()["env"]

    assert env["WL_REPO_SLUG"] == C.REPO_SLUG
    assert env["WL_FALLBACK_REF"] == C.DEFAULT_GATE_REF.rsplit("@", 1)[1]


def test_resolve_prefers_the_reusable_workflows_own_sha(tmp_path: Path):
    sha = "6e2ec4dc7955d6d155987a667040b126acab983b"
    ref, out = _run_resolve(
        tmp_path,
        WL_WORKFLOW_REPOSITORY=C.REPO_SLUG,
        WL_WORKFLOW_SHA=sha,
        WL_WORKFLOW_REF=f"{C.REPO_SLUG}/.github/workflows/gate.yml@refs/heads/main",
    )

    assert ref == sha
    assert "::notice::" in out
    assert "::warning::" not in out
    assert sha in out  # 日志里直接可读（D3）


def test_resolve_lets_an_explicit_with_override_win(tmp_path: Path):
    """显式 `with: witnessloop-ref:` 仍可覆盖（(A) 降级为「显式覆盖」手段后仍要能用）。"""
    ref, out = _run_resolve(
        tmp_path,
        WL_INPUT_REF="v2",
        WL_WORKFLOW_REPOSITORY=C.REPO_SLUG,
        WL_WORKFLOW_SHA="deadbeef" * 5,
    )

    assert ref == "v2"
    assert "::notice::" in out


def test_resolve_lets_an_explicit_override_win_even_on_an_unusable_job_context(tmp_path: Path):
    """显式意图优先：`job.*` 取不到（GHES）也不该让显式传值失效。"""
    ref, _ = _run_resolve(tmp_path, WL_INPUT_REF="v3")

    assert ref == "v3"


def test_resolve_fails_closed_on_a_foreign_repository(tmp_path: Path):
    """接受判据：`job.workflow_repository` 必须等于 `REPO_SLUG`。

    否则会拿**别人的** reusable workflow 的 sha 去 witnessloop 仓取包（装不到）。
    """
    ref, out = _run_resolve(
        tmp_path,
        WL_WORKFLOW_REPOSITORY="someone/fork",
        WL_WORKFLOW_SHA="deadbeef" * 5,
    )

    assert ref == C.DEFAULT_GATE_REF.rsplit("@", 1)[1]
    assert "::warning::" in out


def test_resolve_fails_closed_when_the_job_context_is_unavailable(tmp_path: Path):
    """GHES（`job.*` 不可用 ⇒ 全空）⇒ 退兜底 ref，但**不静默**（有 warning）。

    design §4 R6 如实登记：GHES 接入方的包 ref 会停在这份 gate.yml 的**兜底 ref**
    （= `DEFAULT_GATE_REF` 的 ref 部分，与接入方自己的 `uses:` ref 无关），
    区别只在日志里有 warning。
    """
    ref, out = _run_resolve(tmp_path)

    assert ref == _fallback_ref()
    assert "::warning::" in out


def test_resolve_falls_back_to_the_ref_part_of_job_workflow_ref(tmp_path: Path):
    head = _run_resolve(
        tmp_path,
        WL_WORKFLOW_REPOSITORY=C.REPO_SLUG,
        WL_WORKFLOW_REF=f"{C.REPO_SLUG}/.github/workflows/gate.yml@refs/heads/main",
    )
    tag = _run_resolve(
        tmp_path,
        WL_WORKFLOW_REPOSITORY=C.REPO_SLUG,
        WL_WORKFLOW_REF=f"{C.REPO_SLUG}/.github/workflows/gate.yml@refs/tags/v1.7.0",
    )

    assert head[0] == "main"
    assert tag[0] == "v1.7.0"
    assert "::warning::" not in head[1]
    assert "::warning::" not in tag[1]


def test_resolve_fails_closed_on_malformed_workflow_refs(tmp_path: Path):
    """spec 点名的四个畸形样本（前两个 + 缺 @）⇒ 退兜底 ref 且打 warning。"""
    for malformed in (
        f"{C.REPO_SLUG}/.github/workflows/gate.yml",  # 缺 @
        f"{C.REPO_SLUG}/.github/workflows/gate.yml@",  # @ 后为空
        f"{C.REPO_SLUG}/.github/workflows/gate.yml@refs/pull/30/merge",  # PR 合并 ref
    ):
        ref, out = _run_resolve(
            tmp_path,
            WL_WORKFLOW_REPOSITORY=C.REPO_SLUG,
            WL_WORKFLOW_REF=malformed,
        )
        assert ref == _fallback_ref(), malformed
        assert "::warning::" in out, malformed


def test_resolve_never_leaves_the_ref_empty(tmp_path: Path):
    """ref 为空会把 `uvx --from git+…@` 变成装**默认分支**（静默跑错版本）⇒ 任何输入下都不得为空。"""
    for overrides in (
        {},
        {"WL_WORKFLOW_REPOSITORY": C.REPO_SLUG},
        {"WL_WORKFLOW_SHA": "x"},
        {"WL_INPUT_REF": " "},
    ):
        ref, _ = _run_resolve(tmp_path, **overrides)
        assert ref, overrides


def test_witnessloop_ref_input_default_is_empty():
    """(B′) 的**中央机制**：input 的 `default` 必须是**空串**（= 自动），不是 `"v1"`。

    改回 `"v1"` 会让解析规则① 对**每个**没传 `with:` 的接入方命中（`WL_INPUT_REF` 非空），
    包 ref 就又是 `v1`——症状与今天的缺陷**一模一样**，还会多打一句「来源：调用方显式传入」
    的**误导**日志，而其余测试**全绿**（实测：对抗轮 R2 的 A3）。
    ⇒ 这条断言钉的就是那次静默回归。
    """
    doc = _gate_doc()
    call = doc.get("on") or doc.get(True)  # pyyaml 把裸 `on` 解析成布尔 True
    spec = call["workflow_call"]["inputs"]["witnessloop-ref"]

    assert spec["default"] == "", "input 的 default 非空 ⇒ 自动推导被短路，(B′) 退化成原缺陷"
    assert spec["required"] is False


def test_resolve_survives_undefined_env_vars(tmp_path: Path):
    """`set -eu` 下**未定义**（不只是空）的变量会让脚本当场退出 ⇒ 必须一律 `${VAR:-}` 读。

    真实 GitHub 侧 `${{ }}` 取不到时会渲染成空串（env 仍然存在），但脚本不该把
    「门禁能跑起来」押在那个行为上：解析器宁可 fail-closed 退兜底 ref 并告警。
    （对抗轮 R2 的审题脚本自己就踩过这条：漏一个 env 键 ⇒ `unbound variable`。）
    """
    step = _resolve_step()
    env = dict(os.environ, WL_REPO_SLUG=step["env"]["WL_REPO_SLUG"],
               WL_FALLBACK_REF=step["env"]["WL_FALLBACK_REF"])
    for key in ("WL_INPUT_REF", "WL_WORKFLOW_REPOSITORY", "WL_WORKFLOW_SHA", "WL_WORKFLOW_REF"):
        env.pop(key, None)
    out_path = tmp_path / "github_output"
    out_path.write_text("", encoding="utf-8")
    env["GITHUB_OUTPUT"] = str(out_path)

    proc = subprocess.run(
        ["sh", "-c", step["run"]], env=env, capture_output=True, text=True
    )

    assert proc.returncode == 0, proc.stderr
    assert "unbound variable" not in proc.stderr
    assert "ref=v1" in out_path.read_text(encoding="utf-8")
    assert "::warning::" in proc.stdout


def test_repository_mismatch_does_not_fall_through_to_workflow_ref(tmp_path: Path):
    """判定顺序的钉子（对抗轮 R6 实测暴露的文档/实现错位）：**repository 不匹配 ⇒ 直接 fail-closed**，
    **不**再去试 `job.workflow_ref`。

    差别是可观测的：若错误地继续走兜底分支，`refs/heads/main` 会被当成包 ref（`ref=v1` 之外的
    另一个值）；正确行为是退兜底 ref（`v1`）。
    """
    ref, out = _run_resolve(
        tmp_path,
        WL_WORKFLOW_REPOSITORY="someone/fork",
        WL_WORKFLOW_REF=f"{C.REPO_SLUG}/.github/workflows/gate.yml@refs/heads/main",
    )

    assert ref == _fallback_ref()
    assert ref != "main"
    assert "::warning::" in out
