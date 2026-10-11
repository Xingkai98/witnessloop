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
def gated(repo: Path, cli) -> Path:
    """已接入 witnessloop（init 已提交到 main）的仓，且切到 feature 分支。

    门禁生效的最小基线：check 拿它当 base 才有意义。
    """
    from witnessloop.constants import EXIT_PASS

    code, _, err = cli("init", "--root", str(repo))
    assert code == EXIT_PASS, err
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    return repo


@pytest.fixture
def read_json():
    def _read(path: str | Path) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    return _read


#: 会**污染**测试的宿主环境变量。
#:
#: CI 在 `pull_request` 事件下会设 `GITHUB_BASE_REF`，而测试仓是**无 remote 的 tmp 仓**
#: ——`gitutil.resolve_base` 一旦据此返回 `origin/<base>`，`rev-parse` 必然失败。
#: 首次 PR 实测：`test_manifest_build.py` 14 条一起红（此前从没走过 PR，故从未暴露）。
#: 测试必须对宿主环境免疫；**某条环境语义**由测试自己 `monkeypatch.setenv` 精确构造。
_AMBIENT_ENV = (
    "GITHUB_BASE_REF",
    "WITNESSLOOP_BASE_REF",
    "WITNESSLOOP_HEAD_REF",
    "WITNESSLOOP_RUN_ID",
    "WITNESSLOOP_REVIEWER_RUN_ID",
    "WITNESSLOOP_AUTHOR_RUN_ID",
    "WITNESSLOOP_TEMPLATES_DIR",
)


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    for name in _AMBIENT_ENV:
        monkeypatch.delenv(name, raising=False)
