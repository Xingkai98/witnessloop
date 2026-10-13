"""A 组：`check` 对「测试执行点」的机械判定（change adopter-test-gate / design D4）。

四态：**缺失 / 空（含纯空白）/ 含未替换哨兵 / 已接线**——外加「策略显式 opt-out ⇒ 不判」。
判据**零依赖**：只看「文件存在」与「字符串包含」，不解析 YAML、**不执行命令**（A5）。

背景（grill v2 实测）：只判「存在 + 无哨兵」时，**空文件**会让 `check` 判绿 **且** 门禁
`sh -c ""` 退 0 ⇒ 双重绿、零测试——正是 issue #4 的形态外加一枚绿勾。故第 ② 条判据不可省。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from witnessloop import constants as C
from witnessloop import policy as policy_mod

from conftest import WIRED_TEST_COMMAND, commit_all, git
from helpers import check

TESTS = C.ADOPTER_TESTS_PATH


def _write_tests(repo: Path, content: str | None) -> None:
    """在 feature 分支上改写命令文件（``None`` ⇒ 删掉）并提交。"""
    path = repo / TESTS
    if content is None:
        path.unlink()
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    commit_all(repo, "测试执行点")


# ---------------------------------------------------------------- 四态

def test_wired_execution_point_passes(gated: Path, cli):
    """已接线 ⇒ 绿（这一条同时是另外三条的对照：判据不是「一律红」）。"""
    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err
    assert "通过" in out
    assert (gated / TESTS).read_text(encoding="utf-8") == WIRED_TEST_COMMAND + "\n"


def test_missing_execution_point_is_rejected(gated: Path, cli):
    _write_tests(gated, None)

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL
    assert TESTS in err  # 文案点名**路径**
    assert "不存在" in err  # 与点名「原因」


@pytest.mark.parametrize("body", ["", "   \n", "\n\t \n"])
def test_empty_execution_point_is_rejected(gated: Path, cli, body: str):
    """空 / 纯空白 ⇒ 红（第三条判据；否则空文件双重绿）。"""
    _write_tests(gated, body)

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL
    assert TESTS in err
    assert "为空" in err


def test_unreplaced_sentinel_is_rejected(gated: Path, cli):
    _write_tests(gated, C.ADOPTER_TESTS_SENTINEL + "\n")

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL
    assert TESTS in err
    assert "哨兵" in err


def test_sentinel_anywhere_in_the_file_is_rejected(gated: Path, cli):
    """口径是**子串**：哨兵藏在一行中间同样算「未接线」。

    门禁那一步用 `case "$CMD" in *"$SENTINEL"*)`（也是子串）——两侧必须同口径，
    否则会出现「check 判绿、门禁静默跳过」的分裂（对抗轮 N5）。
    """
    _write_tests(gated, f"uv run pytest -q  # {C.ADOPTER_TESTS_SENTINEL} 待替换\n")

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL
    assert "哨兵" in err


# ---------------------------------------------------------------- 策略语义（A2）

def test_default_policy_doc_does_not_materialize_the_tests_key():
    """出厂 doc **不物化** `tests` 键（对抗轮 X2）。

    物化的话，**已接入仓**跑 plain `init` 会因「本次期望 ≠ 磁盘」exit 1
    （`initcmd.py` 的冲突分支）——`init` 是唯一升级入口，不能对它坏掉。
    """
    assert "tests" not in policy_mod.default_policy_doc()


def test_policy_default_is_declared_and_only_disabled_opts_out():
    """缺省 ⇒ 声明；**唯一**的 opt-out 字面是布尔 `tests.disabled: true`。"""
    assert policy_mod.Policy.from_doc({}).tests_disabled is False
    assert policy_mod.Policy.from_doc({"tests": {}}).tests_disabled is False
    assert policy_mod.Policy.from_doc({"tests": {"disabled": False}}).tests_disabled is False
    # `from_doc` 沿既有惯例用 `or DEFAULT`（falsy 即回落）⇒ 空串/null 都会被读成「声明」；
    # 所以 opt-out 只认**布尔真**，不认任何 falsy 值。
    assert policy_mod.Policy.from_doc({"tests": {"disabled": ""}}).tests_disabled is False
    assert policy_mod.Policy.from_doc({"tests": {"disabled": None}}).tests_disabled is False
    assert policy_mod.Policy.from_doc({"tests": {"disabled": True}}).tests_disabled is True


@pytest.mark.parametrize("value", [1, "true", "yes", [1], {"a": 1}])
def test_truthy_but_non_boolean_disabled_is_not_an_opt_out(value):
    """**真值但非布尔** ⇒ 仍读成「声明」（审阅 R1 的 I2）。

    上面那条只覆盖了 falsy 输入 ⇒ 把 `is True` 换成 `bool(...)` 当时**全绿逃逸**。
    差异恰好出现在这一组：`1` / `"true"` / `"yes"` 都是真值，但 spec 说唯一 opt-out
    字面是**布尔** `true` ⇒ 它们必须继续判（判成 opt-out 就是违约：没有执行点还放行）。
    """
    assert (
        policy_mod.Policy.from_doc({"tests": {"disabled": value}}).tests_disabled
        is False
    )


def test_truthy_but_non_boolean_disabled_still_gets_judged(repo: Path, cli, tmp_path):
    """同一条的端到端面：`{"disabled": 1}` 的仓仍被要求「执行点已接线」。

    用 `init --policy <seed>` 一次写成（status `A` ⇒ 免解释事件），然后 `check`：
    `init` 不认这个字面（`--no-tests` 才是显式 opt-out）⇒ 落的是**哨兵** ⇒ 判红。
    """
    seed = tmp_path / "seed-policy.json"
    doc = policy_mod.default_policy_doc()
    doc["tests"] = {"disabled": 1}
    seed.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    code, _, err = cli("init", "--root", str(repo), "--policy", str(seed))
    assert code == C.EXIT_PASS, err
    assert (repo / TESTS).read_text(encoding="utf-8") == (
        C.ADOPTER_TESTS_SENTINEL + "\n"
    )
    commit_all(repo, "接入（policy 里写了非布尔的 disabled）")
    git(repo, "checkout", "-q", "-b", "feature")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "哨兵" in err  # 只有布尔 true 才是 opt-out


def test_non_object_tests_section_is_a_policy_error():
    with pytest.raises(policy_mod.PolicyError):
        policy_mod.Policy.from_doc({"tests": "yes"})


def test_opt_out_policy_is_not_judged(repo: Path, cli):
    """`init --no-tests`（= 策略里 `tests.disabled: true`）⇒ 不因缺执行点而红。"""
    code, _, err = cli("init", "--root", str(repo), "--no-tests")
    assert code == C.EXIT_PASS, err
    assert not (repo / TESTS).exists()
    commit_all(repo, "接入（显式 opt-out）")
    git(repo, "checkout", "-q", "-b", "feature")

    code, out, err = check(repo, cli)

    assert code == C.EXIT_PASS, err
    assert "通过" in out


# ---------------------------------------------------------------- 改命令 = 普通 commit

def test_editing_the_command_is_a_plain_commit(gated: Path, cli):
    """spec 的 Scenario「改命令不撞台账」：接入方直接改写命令并提交 ⇒ `check` 仍判绿。

    「绿」在这里同时证明**两件事**：台账判定不受影响（文件不在台账里），
    以及**不需要解释事件**（`.github/**` 既不在 `protected_paths`、也不在
    `require_change_for`）——否则受保护写入那块会给出 finding，`check` 必红。
    """
    _write_tests(gated, "uv run pytest -x -q --cov\n")

    code, out, err = check(gated, cli)

    assert code == C.EXIT_PASS, err
    assert "通过" in out


# ---------------------------------------------------------------- A5：不执行命令

def test_check_does_not_execute_the_command(gated: Path, cli, tmp_path: Path):
    """边界（R3）：`check` 只看文件与字符串，**绝不执行**命令。

    用「一跑就会留下痕迹」的命令证明它没跑（痕迹落在仓外，免得污染 `git status`）。
    """
    marker = tmp_path / "check-must-not-run-this.marker"
    _write_tests(gated, f"touch {marker}\n")

    code, _, err = check(gated, cli)

    assert code == C.EXIT_PASS, err
    assert not marker.exists(), "check 执行了命令文件里的命令"
