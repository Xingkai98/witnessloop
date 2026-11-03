"""issue #45：零变更区间不得被判为「通过」。

`check --base HEAD --head HEAD` 原先打印「0 个变更文件」后直接「通过 ✓」并退 0——
「没有任何东西被校验」被当成了「校验通过」。新语义：

* 默认：无操作、非通过、退出码 ``EXIT_EMPTY``（可区分于真失败的 1）；
* 显式 ``--allow-empty``：退 0，并在输出里写明「已按该 flag 显式放行」。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all
from helpers import check, write_artifact


def test_zero_diff_is_not_a_pass_by_default(gated: Path, cli):
    code, out, err = cli(
        "check", "--root", str(gated), "--base", "HEAD", "--head", "HEAD"
    )

    text = out + err
    assert code == C.EXIT_EMPTY
    assert code != 0
    assert code != C.EXIT_FAIL, "零变更应当有可区分的退出码，而不是混同于真失败"
    assert "无变更" in text
    assert "非通过" in text
    # 精确成功行必须缺席（「非通过」里含「通过」二字，不能只查子串）。
    assert "check：通过 ✓" not in text
    # 既有摘要子串保持不变，避免破坏下游日志断言。
    assert "0 个变更文件" in text
    assert "0 个 change 目录" in text


def test_allow_empty_explicitly_passes_without_claiming_validation(gated: Path, cli):
    code, out, err = cli(
        "check",
        "--root",
        str(gated),
        "--base",
        "HEAD",
        "--head",
        "HEAD",
        "--allow-empty",
    )

    text = out + err
    assert code == C.EXIT_PASS
    assert "无变更" in text
    assert "--allow-empty" in text
    assert "显式放行" in text
    assert "check：通过 ✓" not in text, "放行不等于校验通过，不得冒充成功行"
    assert "本次没有校验任何内容" in text


def test_allow_empty_does_not_change_a_nonempty_failure(gated: Path, cli):
    """`--allow-empty` 只影响空区间；有变更时既有判定原样生效。"""
    write_artifact(gated, "src/app.py", "print('hi')\n")
    commit_all(gated, "改了代码，没挂 change")

    code, _, err = check(gated, cli, "--allow-empty")

    assert code == C.EXIT_FAIL
    assert "没有任何 change 目录" in err
