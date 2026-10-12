"""E 组：进程入口兜底（change guard-crash-exit / D3）。

issue #9：`guard` 崩溃退 **1** 而 1 是宿主的 block 码（`plugin/hooks/guard.sh` 把 1 → CC 的 2）
⇒ 崩溃 = 误拦。兜底放在**进程入口**（而非 `cli.main`），因为 `cli.py` **自身**的模块级 import
失败发生在任何 try 之外（真实 console script = `from witnessloop.cli import main; sys.exit(main())`）。

不变量：入口只对 **`guard`** verb 的未预期异常退 `EXIT_INTERNAL`；其余 verb 退 **1**（`check` = 未通过 = fail-closed）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import witnessloop
from witnessloop import constants as C
from witnessloop import entry

#: 与 `constants.EXIT_INTERNAL` 必须同值（入口不可 import witnessloop ⇒ 用字面量）。
LITERAL_INTERNAL = 4

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "witnessloop"


def test_production_wiring_points_at_the_entry_guard():
    """**接线是承重的**（审阅发现）：把 `pyproject` 的 console script 回退成 `witnessloop.cli:main`
    会**静默拆掉 issue #9 的修复本体**——而 fixture 与其它用例都直接 import `entry`，
    整套 suite 仍会全绿（CI 冒烟只验 `--version`，也照过）。故用文本断言把接线钉住。
    """
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'witnessloop = "witnessloop.entry:main"' in pyproject
    assert "witnessloop.cli:main" not in pyproject

    main_py = (SRC / "__main__.py").read_text(encoding="utf-8")
    assert "from witnessloop.entry import main" in main_py


def test_test_harness_goes_through_the_real_entry():
    """测试脚手架也必须走真实入口——否则 B 组用例验的不是生产路径。"""
    conftest = (REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "from witnessloop.entry import main" in conftest


def test_entry_internal_code_matches_the_documented_constant():
    assert entry._EXIT_INTERNAL == C.EXIT_INTERNAL == LITERAL_INTERNAL
    assert C.EXIT_INTERNAL != C.EXIT_FAIL


def _boom(*_args, **_kwargs):
    raise RuntimeError("boom")


def test_guard_crash_through_the_entry_is_fail_open(monkeypatch):
    monkeypatch.setattr("witnessloop.cli.main", _boom)
    code = entry.main(["guard", "--root", ".", "--path", "src/x.py"])
    assert code == C.EXIT_INTERNAL
    assert code != C.EXIT_FAIL  # 关键：绝不是宿主的 block 码


def test_non_guard_crash_still_fails_closed(monkeypatch):
    """同一入口、verb 不是 `guard` ⇒ 退 1（`check` = 未通过），**不是** 4。"""
    monkeypatch.setattr("witnessloop.cli.main", _boom)
    assert entry.main(["check", "--root", "."]) == C.EXIT_FAIL


def test_entry_closes_the_broken_cli_import_hole(monkeypatch):
    """`cli.py` **自身** import 失败（安装破损）也必须 fail-open —— 这是 D3 前移入口的理由。"""
    monkeypatch.setitem(sys.modules, "witnessloop.cli", None)
    monkeypatch.delattr(witnessloop, "cli", raising=False)
    code = entry.main(["guard", "--root", ".", "--path", "src/x.py"])
    assert code == C.EXIT_INTERNAL
    assert code != C.EXIT_FAIL


def test_entry_does_not_swallow_systemexit(monkeypatch, capsys):
    """「`SystemExit` 照常传播」是承重性质：`--help`/`--version` 为 0、用法错误为 2。"""
    with pytest.raises(SystemExit) as help_exit:
        entry.main(["--help"])
    assert help_exit.value.code == 0
    capsys.readouterr()

    with pytest.raises(SystemExit) as version_exit:
        entry.main(["--version"])
    assert version_exit.value.code == 0

    with pytest.raises(SystemExit) as bogus_exit:
        entry.main(["bogus"])
    assert bogus_exit.value.code == C.EXIT_USAGE


def test_broken_import_of_a_non_guard_verb_fails_closed(monkeypatch):
    """安装破损 + 非 guard verb ⇒ 仍退 1（不能把「4」泛化到所有动词）。"""
    monkeypatch.setitem(sys.modules, "witnessloop.cli", None)
    monkeypatch.delattr(witnessloop, "cli", raising=False)
    assert entry.main(["check", "--root", "."]) == C.EXIT_FAIL
