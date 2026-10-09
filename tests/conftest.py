"""共享测试脚手架：临时 git 仓 + CLI 调用器。

witnessloop 的 3 个动词都作用于真实 git 仓，所以测试在 tmp 里建真仓，
而不是 mock git——init/uninit/check 的正确性一半在 git 语义上。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from witnessloop.cli import main


def git(repo: str | Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败：{proc.stderr}")
    return proc.stdout


def commit_all(repo: str | Path, message: str = "commit") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """一个已 commit 一次的普通 git 仓（main 分支）。"""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "witnessloop test")
    git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    commit_all(root, "初始化")
    return root


@pytest.fixture
def cli(capsys):
    """在进程内跑 CLI，返回 (退出码, stdout, stderr)。"""

    def _run(*argv: str) -> tuple[int, str, str]:
        code = main(list(argv))
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return _run


@pytest.fixture
def read_json():
    def _read(path: str | Path) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    return _read
