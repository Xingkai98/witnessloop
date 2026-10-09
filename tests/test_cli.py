"""A 组：骨架与分发。

覆盖 A2（子命令路由；未实现/未知子命令给出明确报错，不静默）。
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from witnessloop import __version__
from witnessloop.cli import build_parser, main


def test_version_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_subcommand_prints_help_and_fails(capsys):
    assert main([]) == 2
    err = capsys.readouterr().err
    assert "init" in err and "check" in err


def test_unknown_subcommand_is_a_loud_error(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["gate"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice" in err
    # 未知动词不静默：非零退出且报错提到该动词。
    assert "gate" in err


@pytest.mark.parametrize("command", ["init", "uninit", "check"])
def test_each_verb_is_routed_with_help(command, capsys):
    with pytest.raises(SystemExit) as exc:
        main([command, "--help"])
    assert exc.value.code == 0
    assert command in capsys.readouterr().out


def test_only_the_three_verbs_exist():
    parser = build_parser()
    sub = next(a for a in parser._actions if a.dest == "command")
    assert set(sub.choices) == {"init", "uninit", "check"}


def test_console_script_is_installed():
    """`uv run witnessloop --version` 必须能跑（A1 的可分发验收）。"""
    proc = subprocess.run(
        [sys.executable, "-m", "witnessloop", "--version"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert __version__ in proc.stdout
